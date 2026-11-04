"""Uploads de regras (Profimetrics e base PROP%) enviados por usuários: só vão para o Supabase depois que o administrador aprova."""
from __future__ import annotations

import datetime as dt
import gzip
import io
import uuid

from core import db

TIPOS = {"profimetrics": "Regras de margem (Profimetrics)", "proporcoes": "Base PROP% (proporcionais)"}


def enviar(tipo: str, usuario: str, nome_arquivo: str, conteudo: bytes, resumo: dict) -> str:
    ident = str(uuid.uuid4())
    caminho = f"pendentes/{ident}.gz"
    db.sb().storage.from_("relatorios").upload(caminho, gzip.compress(conteudo, 6), {"content-type": "application/gzip", "upsert": "true"})
    db.sb().table("aprovacoes_upload").insert({"id": ident, "tipo": tipo, "usuario": usuario, "nome_arquivo": nome_arquivo,
                                               "caminho": caminho, "resumo": resumo, "status": "pendente"}).execute()
    return ident


def pendentes() -> list[dict]:
    try:
        return db.sb().table("aprovacoes_upload").select("*").eq("status", "pendente").order("criado_em").execute().data or []
    except Exception:
        return []


def meus(usuario: str) -> list[dict]:
    try:
        return (db.sb().table("aprovacoes_upload").select("*").eq("usuario", usuario).order("criado_em", desc=True)
                .limit(5).execute().data or [])
    except Exception:
        return []


def _decidir(ident: str, status: str, admin: str, obs: str = "") -> None:
    db.sb().table("aprovacoes_upload").update({"status": status, "decidido_por": admin, "observacao": obs,
                                               "decidido_em": dt.datetime.now(dt.timezone.utc).isoformat()}).eq("id", ident).execute()


def aprovar(pedido: dict, admin: str, progresso=None) -> str:
    """Grava no Supabase o arquivo aprovado, exatamente como o envio direto faria."""
    from core import profimetrics as pf, proporcoes as pp
    bruto = io.BytesIO(gzip.decompress(db.sb().storage.from_("relatorios").download(pedido["caminho"])))
    if pedido["tipo"] == "profimetrics":
        r = pf.salvar(pf.ler_planilha(bruto), pedido["usuario"])
        msg = f"{r['novas']} novas, {r['substituidas']} substituídas, {r['mantidas']} mantidas"
    else:
        r = pp.salvar(pp.ler_planilha(bruto), progresso=progresso)
        msg = f"{r['salvas'] + r['fora_da_dim']} relações"
    _decidir(pedido["id"], "aprovado", admin, msg)
    try:
        db.sb().storage.from_("relatorios").remove([pedido["caminho"]])
    except Exception:
        pass
    return msg


def recusar(pedido: dict, admin: str) -> None:
    _decidir(pedido["id"], "recusado", admin)
    try:
        db.sb().storage.from_("relatorios").remove([pedido["caminho"]])
    except Exception:
        pass
