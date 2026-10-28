"""Biblioteca de relatórios HTML (tabela `relatorios` + bucket `relatorios` no Supabase Storage)."""
from __future__ import annotations

import codecs
import gzip
import posixpath
import uuid
from datetime import datetime, timezone

import streamlit as st

from core import db

BUCKET = "relatorios"
TAMANHO_MAXIMO_MB = 300        # HTML original (limite do upload no Streamlit)
PARTE_MB = 45                  # o Supabase gratuito aceita até 50 MB por arquivo: arquivos maiores viram partes
GZIP = b"\x1f\x8b"
VISIBILIDADES = ["Todos", "Selecionados", "Admins"]
ROTULO_VISIBILIDADE = {
    "Todos": "Toda a equipe",
    "Selecionados": "Pessoas específicas",
    "Admins": "Só administradores",
}


class ErroRelatorio(RuntimeError):
    pass


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


@st.cache_data(ttl=60, show_spinner=False)
def listar() -> list[dict]:
    try:
        return db.sb().table("relatorios").select("*").order("criado_em", desc=True).execute().data or []
    except Exception:
        return []


def limpar_cache() -> None:
    listar.clear()


def buscar(rid: str) -> dict | None:
    return next((r for r in listar() if str(r.get("id")) == str(rid)), None)


def _eh_utf8(conteudo: bytes) -> bool:
    decodificador = codecs.getincrementaldecoder("utf-8")()
    passo = 1 << 20
    try:
        for i in range(0, len(conteudo), passo):
            decodificador.decode(conteudo[i:i + passo])
        decodificador.decode(b"", final=True)
        return True
    except UnicodeDecodeError:
        return False


@st.cache_data(show_spinner=False, max_entries=2)
def compactar(conteudo: bytes) -> bytes:
    """Normaliza para UTF-8 e compacta com gzip (HTML costuma encolher de 5 a 15 vezes)."""
    if conteudo[:2] == GZIP:
        return conteudo
    if not _eh_utf8(conteudo):
        conteudo = conteudo.decode("cp1252", errors="replace").encode("utf-8")
    return gzip.compress(conteudo, compresslevel=6)


@st.cache_data(ttl=900, show_spinner=False, max_entries=6)
def baixar_compactado(caminho: str, versao: str) -> bytes:
    """Arquivo do relatório já compactado. `versao` entra só na chave do cache."""
    conteudo = db.sb().storage.from_(BUCKET).download(caminho)
    return compactar(conteudo)


def _validar_tamanho(conteudo: bytes) -> bytes:
    if len(conteudo) > TAMANHO_MAXIMO_MB * 1024 * 1024:
        raise ErroRelatorio(f"O arquivo passa de {TAMANHO_MAXIMO_MB} MB.")
    return compactar(conteudo)


def _caminhos(base: str, partes: int) -> list[str]:
    """Parte 0 usa o caminho base; as seguintes recebem o sufixo .1, .2..."""
    return [base] + [f"{base}.{i}" for i in range(1, partes)]


def _dividir(gz: bytes) -> list[bytes]:
    passo = PARTE_MB * 1024 * 1024
    return [gz[i:i + passo] for i in range(0, len(gz), passo)] or [b""]


@st.cache_data(ttl=1800, show_spinner=False, max_entries=64)
def links_assinados(base: str, partes: int, versao: str) -> list[str]:
    """Links temporários (1 h) para o navegador baixar o arquivo direto do Supabase."""
    links = []
    for caminho in _caminhos(base, partes):
        resp = db.sb().storage.from_(BUCKET).create_signed_url(caminho, 3600)
        url = resp.get("signedURL") or resp.get("signedUrl") or resp.get("signed_url")
        if url.startswith("/"):
            url = st.secrets["SUPABASE_URL"].rstrip("/") + "/storage/v1" + url
        links.append(url)
    return links


# ---------------------------------------------------------------- permissões
def pode_ver(rel: dict, login: str, admin: bool) -> bool:
    if admin or rel.get("autor_usuario") == login:
        return True
    vis = rel.get("visibilidade") or "Todos"
    if vis == "Todos":
        return True
    if vis == "Selecionados":
        return login in (rel.get("usuarios_permitidos") or [])
    return False


def pode_editar(rel: dict, login: str, admin: bool) -> bool:
    return admin or rel.get("autor_usuario") == login


def visiveis(login: str, admin: bool) -> list[dict]:
    return [r for r in listar() if pode_ver(r, login, admin)]


# ---------------------------------------------------------------- escrita
def _enviar(caminho: str, gz: bytes) -> None:
    db.sb().storage.from_(BUCKET).upload(
        caminho, gz, {"content-type": "application/gzip", "upsert": "true", "cache-control": "60"},
    )


def _enviar_partes(base: str, gz: bytes, progresso=None) -> int:
    pedacos = _dividir(gz)
    for i, (caminho, pedaco) in enumerate(zip(_caminhos(base, len(pedacos)), pedacos)):
        if progresso:
            progresso(i, len(pedacos))
        _enviar(caminho, pedaco)
    return len(pedacos)


def _remover(caminhos: list[str]) -> None:
    if not caminhos:
        return
    try:
        db.sb().storage.from_(BUCKET).remove(caminhos)
    except Exception:
        pass


def publicar(meta: dict, conteudo: bytes, autor_login: str, autor_nome: str, progresso=None) -> str:
    gz = _validar_tamanho(conteudo)
    rid = str(uuid.uuid4())
    caminho = f"{datetime.now():%Y/%m}/{rid}.html.gz"
    try:
        partes = _enviar_partes(caminho, gz, progresso)
    except Exception as exc:
        _remover(_caminhos(caminho, len(_dividir(gz))))
        raise ErroRelatorio(f"Não foi possível enviar o arquivo para o Storage: {exc}") from exc
    registro = {
        "id": rid, **meta, "arquivo_path": caminho, "partes": partes, "tamanho_bytes": len(conteudo),
        "autor_usuario": autor_login, "autor_nome": autor_nome, "versao": 1,
        "criado_em": _agora(), "atualizado_em": _agora(),
    }
    try:
        db.sb().table("relatorios").insert(registro).execute()
    except Exception as exc:
        _remover(_caminhos(caminho, partes))
        raise ErroRelatorio(f"Não foi possível registrar o relatório: {exc}") from exc
    limpar_cache()
    return rid


def atualizar(rel: dict, meta: dict, conteudo: bytes | None = None, progresso=None) -> None:
    campos = {**meta, "atualizado_em": _agora()}
    sobras: list[str] = []
    if conteudo is not None:
        gz = _validar_tamanho(conteudo)
        antigo, partes_antigas = rel["arquivo_path"], int(rel.get("partes") or 1)
        caminho = antigo if antigo.endswith(".gz") else posixpath.join(posixpath.dirname(antigo), f"{rel['id']}.html.gz")
        try:
            partes = _enviar_partes(caminho, gz, progresso)
        except Exception as exc:
            raise ErroRelatorio(f"Não foi possível enviar o novo arquivo: {exc}") from exc
        novos = set(_caminhos(caminho, partes))
        sobras = [c for c in _caminhos(antigo, partes_antigas) if c not in novos]
        campos["arquivo_path"] = caminho
        campos["partes"] = partes
        campos["tamanho_bytes"] = len(conteudo)
        campos["versao"] = int(rel.get("versao") or 1) + 1
    try:
        db.sb().table("relatorios").update(campos).eq("id", rel["id"]).execute()
    except Exception as exc:
        raise ErroRelatorio(f"Não foi possível salvar as alterações: {exc}") from exc
    _remover(sobras)
    links_assinados.clear()
    limpar_cache()


def excluir(rel: dict) -> None:
    _remover(_caminhos(rel["arquivo_path"], int(rel.get("partes") or 1)))
    db.sb().table("relatorios").delete().eq("id", rel["id"]).execute()
    limpar_cache()


def registrar_visualizacao(rel: dict) -> None:
    chave = f"_visto_{rel['id']}"
    if st.session_state.get(chave):
        return
    st.session_state[chave] = True
    try:
        db.sb().rpc("incrementar_visualizacao", {"rid": rel["id"]}).execute()
    except Exception:
        pass


def categorias() -> list[str]:
    return sorted({(r.get("categoria") or "Geral") for r in listar()})


# ---------------------------------------------------------------- favoritos e recentes (por usuário)
def preferencias(login: str) -> dict[str, dict]:
    """{id do relatório: {"favorito": bool, "ultimo_acesso": iso}} do usuário. Vazio se a tabela não existir."""
    try:
        dados = db.sb().table("relatorios_usuario").select("*").eq("usuario", login).execute().data or []
    except Exception:
        return {}
    return {str(r["relatorio_id"]): r for r in dados}


def _gravar_preferencia(login: str, rid: str, campos: dict) -> None:
    db.sb().table("relatorios_usuario").upsert(
        {"usuario": login, "relatorio_id": rid, **campos}, on_conflict="usuario,relatorio_id").execute()


def marcar_acesso(login: str, rid: str) -> None:
    if st.session_state.get("_ultimo_relatorio_aberto") == rid:
        return
    st.session_state._ultimo_relatorio_aberto = rid
    try:
        _gravar_preferencia(login, rid, {"ultimo_acesso": _agora()})
    except Exception:
        pass


def definir_favorito(login: str, rid: str, favorito: bool) -> None:
    try:
        _gravar_preferencia(login, rid, {"favorito": favorito})
    except Exception as exc:
        raise ErroRelatorio("Não foi possível salvar o favorito. Confira se a tabela relatorios_usuario "
                            "existe no Supabase (supabase/migrations.sql).") from exc
