"""Presença e acessos: último acesso, acessos no dia e quem está online."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import streamlit as st

from core import db

try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # sem base de fusos no servidor
    FUSO = timezone(timedelta(hours=-3))

ONLINE_MINUTOS = 5
PULSO_SEGUNDOS = 60


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _ler(iso) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def hoje() -> str:
    return datetime.now(FUSO).date().isoformat()


def registrar_login(registro: dict) -> None:
    n = (int(registro.get("acessos_dia") or 0) + 1) if str(registro.get("acessos_data") or "")[:10] == hoje() else 1
    agora = _agora().isoformat()
    try:
        db.atualizar_usuario(registro["usuario"], {"ultimo_acesso": agora, "ultima_atividade": agora,
                                                   "acessos_dia": n, "acessos_data": hoje()})
    except Exception:
        pass  # colunas de presença ainda não criadas (supabase/migrations.sql)
    st.session_state._pulso = time.time()


def pulso() -> None:
    """Marca o usuário como ativo, no máximo uma vez por minuto."""
    login = st.session_state.get("usuario_login")
    if not login or time.time() - st.session_state.get("_pulso", 0) < PULSO_SEGUNDOS:
        return
    st.session_state._pulso = time.time()
    try:
        db.atualizar_usuario(login, {"ultima_atividade": _agora().isoformat()})
    except Exception:
        pass


def registrar_saida(login: str) -> None:
    try:
        db.atualizar_usuario(login, {"ultima_atividade": None})
    except Exception:
        pass


def resumo(u: dict) -> dict:
    atividade = _ler(u.get("ultima_atividade"))
    ultimo = _ler(u.get("ultimo_acesso"))
    online = bool(atividade and _agora() - atividade < timedelta(minutes=ONLINE_MINUTOS))
    acessos = int(u.get("acessos_dia") or 0) if str(u.get("acessos_data") or "")[:10] == hoje() else 0
    texto = ultimo.astimezone(FUSO).strftime("%d/%m/%Y %H:%M") if ultimo else "Nunca acessou"
    return {"online": online, "acessos_hoje": acessos, "ultimo": texto}
