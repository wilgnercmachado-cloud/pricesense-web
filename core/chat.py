"""Chat do PriceSense: um canal público por estado (todos os usuários do estado) e conversas privadas.

Regras combinadas com o usuário:
- botão flutuante em todas as telas, abrindo o chat por cima;
- privado só entre usuários do mesmo estado; o administrador conversa com todos;
- pop-up só quando alguém marca (@nome) ou manda mensagem privada; no público, só o contador no botão.
"""
from __future__ import annotations

import datetime as dt
import re
import unicodedata
import uuid

import streamlit as st

from core import db, notificacoes as nt, reports

MSG, LEIT = "chat_mensagens", "chat_leituras"


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()


@st.cache_data(ttl=120, show_spinner=False)
def usuarios() -> list[dict]:
    return [u for u in db.listar_usuarios() if str(u.get("status")) == "Aprovado"]


def estados_de(u: dict, todos: list[str]) -> set[str]:
    if u.get("is_admin"):
        return set(todos)
    e = reports.estados_do_usuario(u.get("estado"))
    return set(todos) if "TODOS" in e else set(e)


def canais(eu: dict, todos_estados: list[str]) -> list[tuple[str, str]]:
    """(canal, rótulo): públicos dos meus estados e privados com quem posso conversar."""
    meus = estados_de(eu, todos_estados)
    out = [(f"uf:{uf}", f"# Público {uf}") for uf in sorted(meus)]
    for u in usuarios():
        if u["usuario"] == eu["usuario"]:
            continue
        if eu.get("is_admin") or u.get("is_admin") or meus & estados_de(u, todos_estados):
            out.append((dm(eu["usuario"], u["usuario"]), f"@ {u.get('nome') or u['usuario']}"))
    return out


def dm(a: str, b: str) -> str:
    return "dm:" + "|".join(sorted([a, b]))


def mensagens(canal: str, limite: int = 80) -> list[dict]:
    try:
        d = db.sb().table(MSG).select("*").eq("canal", canal).order("criado_em", desc=True).limit(limite).execute().data or []
    except Exception:
        return []
    return list(reversed(d))


def recentes(canais_: list[str], limite: int = 400) -> list[dict]:
    try:
        return db.sb().table(MSG).select("canal, autor, criado_em").in_("canal", canais_).order("criado_em", desc=True).limit(limite).execute().data or []
    except Exception:
        return []


def leituras(usuario: str) -> dict:
    try:
        return {r["canal"]: r["lido_em"] for r in (db.sb().table(LEIT).select("*").eq("usuario", usuario).execute().data or [])}
    except Exception:
        return {}


def marcar_lido(usuario: str, canal: str) -> None:
    try:
        db.sb().table(LEIT).upsert({"usuario": usuario, "canal": canal, "lido_em": dt.datetime.now(dt.timezone.utc).isoformat()},
                                   on_conflict="usuario,canal").execute()
    except Exception:
        pass


def preparar_imagem(bruto: bytes) -> str:
    """Print anexado: reduzido (até 1280 px) e em JPEG, guardado junto da mensagem como data URL (~100 KB)."""
    import base64
    import io
    from PIL import Image
    img = Image.open(io.BytesIO(bruto))
    img = img.convert("RGB")
    img.thumbnail((1280, 1280))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=78, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()


TIPOS_ACEITOS = ("png", "jpg", "jpeg", "webp", "gif", "txt", "csv", "xlsx", "xls", "zip", "pdf", "docx")
LIMITE_ARQUIVO = 15 * 1024 * 1024


def _miniatura(bruto: bytes) -> str | None:
    try:
        import base64
        import io
        from PIL import Image
        img = Image.open(io.BytesIO(bruto)).convert("RGB")
        img.thumbnail((900, 900))
        out = io.BytesIO(); img.save(out, "JPEG", quality=72, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()
    except Exception:
        return None


def baixar(caminho: str) -> bytes:
    """Arquivo do chat no tamanho original (guardado compactado no Storage)."""
    import gzip
    return gzip.decompress(db.sb().storage.from_("relatorios").download(caminho))


def enviar(canal: str, autor: dict, texto: str, todos_estados: list[str], anexo: bytes | None = None,
           arquivos: list[dict] | None = None) -> None:
    """arquivos: [{nome, tipo, bytes}] — prints, textos, Excel, CSV, ZIP. Cada um fica no Storage no tamanho original;
    imagens ganham também uma miniatura para aparecer na conversa."""
    import gzip
    texto = (texto or "").strip()
    arquivos = list(arquivos or [])
    if anexo:
        arquivos.append({"nome": "print.png", "tipo": "image/png", "bytes": anexo})
    if not texto and not arquivos:
        return
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    ident = str(uuid.uuid4())
    reg = {"id": ident, "canal": canal, "autor": autor["usuario"], "autor_nome": autor.get("nome") or autor["usuario"],
           "texto": texto[:2000], "criado_em": agora}
    salvos = []
    for n, a_ in enumerate(arquivos):
        bruto = a_["bytes"]
        if len(bruto) > LIMITE_ARQUIVO:
            raise ValueError(f"{a_['nome']} passa de 15 MB")
        nome = re.sub(r"[^\w.\- ]", "_", str(a_.get("nome") or f"arquivo_{n}"))[:120]
        caminho = f"chat/{ident}/{n}_{nome}.gz"
        db.sb().storage.from_("relatorios").upload(caminho, gzip.compress(bruto, 6), {"content-type": "application/gzip", "upsert": "true"})
        item = {"nome": nome, "tipo": a_.get("tipo") or "", "tamanho": len(bruto), "caminho": caminho}
        if str(item["tipo"]).startswith("image/") or nome.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
            item["previa"] = _miniatura(bruto)
        salvos.append(item)
    if salvos:
        reg["arquivos"] = salvos
        texto = texto or ("[" + ", ".join(x["nome"] for x in salvos) + "]")
    db.sb().table(MSG).insert(reg).execute()
    marcar_lido(autor["usuario"], canal)
    nome = autor.get("nome") or autor["usuario"]
    trecho = texto if len(texto) <= 160 else texto[:157] + "..."
    if canal.startswith("dm:"):
        outro = [u for u in canal[3:].split("|") if u != autor["usuario"]]
        try:
            nt.enviar(outro, "chat", f"Mensagem privada de {nome}", trecho)
        except Exception:
            pass                                   # sem a tabela de notificações, a mensagem continua gravada
        return
    # público: avisa quem foi marcado com @login ou @primeiro nome (e que participa do estado)
    uf = canal[3:]
    marcados = {_sem_acento(m) for m in re.findall(r"@([\wÀ-ÿ.\-]+)", texto)}
    if not marcados:
        return
    alvo = []
    for u in usuarios():
        if u["usuario"] == autor["usuario"] or uf not in estados_de(u, todos_estados):
            continue
        chaves = {_sem_acento(u["usuario"]), _sem_acento(str(u.get("nome") or "").split(" ")[0])}
        if chaves & marcados:
            alvo.append(u["usuario"])
    try:
        nt.enviar(alvo, "chat", f"{nome} marcou você no Público {uf}", trecho)
    except Exception:
        pass
