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


def enviar(canal: str, autor: dict, texto: str, todos_estados: list[str]) -> None:
    texto = (texto or "").strip()
    if not texto:
        return
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    db.sb().table(MSG).insert({"id": str(uuid.uuid4()), "canal": canal, "autor": autor["usuario"], "autor_nome": autor.get("nome") or autor["usuario"],
                               "texto": texto[:2000], "criado_em": agora}).execute()
    marcar_lido(autor["usuario"], canal)
    nome = autor.get("nome") or autor["usuario"]
    trecho = texto if len(texto) <= 160 else texto[:157] + "..."
    if canal.startswith("dm:"):
        outro = [u for u in canal[3:].split("|") if u != autor["usuario"]]
        nt.enviar(outro, "chat", f"Mensagem privada de {nome}", trecho)
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
    nt.enviar(alvo, "chat", f"{nome} marcou você no Público {uf}", trecho)
