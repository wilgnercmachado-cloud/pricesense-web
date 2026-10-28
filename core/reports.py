"""Biblioteca de relatórios HTML (tabela `relatorios` + bucket `relatorios` no Supabase Storage)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import streamlit as st

from core import db

BUCKET = "relatorios"
TAMANHO_MAXIMO_MB = 25
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


@st.cache_data(ttl=900, show_spinner=False, max_entries=24)
def baixar_html(caminho: str, versao: str) -> str:
    """`versao` entra só na chave do cache, para invalidar quando o arquivo muda."""
    conteudo = db.sb().storage.from_(BUCKET).download(caminho)
    for codificacao in ("utf-8", "cp1252", "latin-1"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("utf-8", errors="replace")


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
def _enviar(caminho: str, conteudo: bytes) -> None:
    db.sb().storage.from_(BUCKET).upload(
        caminho, conteudo,
        {"content-type": "text/html; charset=utf-8", "upsert": "true", "cache-control": "60"},
    )


def publicar(meta: dict, conteudo: bytes, autor_login: str, autor_nome: str) -> str:
    if len(conteudo) > TAMANHO_MAXIMO_MB * 1024 * 1024:
        raise ErroRelatorio(f"O arquivo passa de {TAMANHO_MAXIMO_MB} MB.")
    rid = str(uuid.uuid4())
    caminho = f"{datetime.now():%Y/%m}/{rid}.html"
    try:
        _enviar(caminho, conteudo)
    except Exception as exc:
        raise ErroRelatorio(f"Não foi possível enviar o arquivo para o Storage: {exc}") from exc
    registro = {
        "id": rid, **meta, "arquivo_path": caminho, "tamanho_bytes": len(conteudo),
        "autor_usuario": autor_login, "autor_nome": autor_nome, "versao": 1,
        "criado_em": _agora(), "atualizado_em": _agora(),
    }
    try:
        db.sb().table("relatorios").insert(registro).execute()
    except Exception as exc:
        try:
            db.sb().storage.from_(BUCKET).remove([caminho])
        except Exception:
            pass
        raise ErroRelatorio(f"Não foi possível registrar o relatório: {exc}") from exc
    limpar_cache()
    return rid


def atualizar(rel: dict, meta: dict, conteudo: bytes | None = None) -> None:
    campos = {**meta, "atualizado_em": _agora()}
    if conteudo is not None:
        if len(conteudo) > TAMANHO_MAXIMO_MB * 1024 * 1024:
            raise ErroRelatorio(f"O arquivo passa de {TAMANHO_MAXIMO_MB} MB.")
        try:
            _enviar(rel["arquivo_path"], conteudo)
        except Exception as exc:
            raise ErroRelatorio(f"Não foi possível enviar o novo arquivo: {exc}") from exc
        campos["tamanho_bytes"] = len(conteudo)
        campos["versao"] = int(rel.get("versao") or 1) + 1
    try:
        db.sb().table("relatorios").update(campos).eq("id", rel["id"]).execute()
    except Exception as exc:
        raise ErroRelatorio(f"Não foi possível salvar as alterações: {exc}") from exc
    limpar_cache()


def excluir(rel: dict) -> None:
    try:
        db.sb().storage.from_(BUCKET).remove([rel["arquivo_path"]])
    except Exception:
        pass
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
