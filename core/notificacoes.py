"""Notificações por usuário (pop-up no site): sugestões do comprador, respostas do Pricing e, depois, o chat."""
from __future__ import annotations

import datetime as dt
import uuid

from core import db

TABELA = "notificacoes"


def enviar(usuarios: list[str], tipo: str, titulo: str, texto: str) -> None:
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    regs = [{"id": str(uuid.uuid4()), "usuario": u, "tipo": tipo, "titulo": titulo, "texto": texto, "lida": False, "criado_em": agora}
            for u in sorted(set(x for x in usuarios if x))]
    if regs:
        db.sb().table(TABELA).insert(regs).execute()


def nao_lidas(usuario: str, limite: int = 6) -> list[dict]:
    try:
        return (db.sb().table(TABELA).select("*").eq("usuario", usuario).eq("lida", False).order("criado_em", desc=True)
                .limit(limite).execute().data or [])
    except Exception:
        return []


def marcar_lidas(ids: list[str]) -> None:
    for i in ids:
        db.sb().table(TABELA).update({"lida": True}).eq("id", i).execute()
