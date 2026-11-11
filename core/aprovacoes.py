"""Uploads de regras (Profimetrics e base PROP%) enviados por usuários: só vão para o Supabase depois que o administrador aprova."""
from __future__ import annotations

import datetime as dt
import gzip
import io
import uuid

from core import db

TIPOS = {"profimetrics": "Regras de margem (Profimetrics)", "proporcoes": "Base PROP% (proporcionais)", "trava": "Trava mínima (acordo)", "parametros": "Formação de preço (curvas e delta)",
         "margens": "Nova margem objetiva, mínima e máxima"}


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


def conteudo(pedido: dict) -> bytes:
    return gzip.decompress(db.sb().storage.from_("relatorios").download(pedido["caminho"]))


def aprovar(pedido: dict, admin: str, progresso=None, itens_editados: list[dict] | None = None) -> str:
    """Grava no Supabase o arquivo aprovado, exatamente como o envio direto faria."""
    from core import profimetrics as pf, proporcoes as pp
    bruto = io.BytesIO(gzip.decompress(db.sb().storage.from_("relatorios").download(pedido["caminho"])))
    if pedido["tipo"] == "profimetrics":
        r = pf.salvar(pf.ler_planilha(bruto), pedido["usuario"])
        msg = f"{r['novas']} novas, {r['substituidas']} substituídas, {r['mantidas']} mantidas"
    elif pedido["tipo"] == "margens":
        import json
        from core import notificacoes as nt, revisao as rv
        p = json.loads(bruto.getvalue())
        itens = itens_editados if itens_editados is not None else p["itens"]
        msg = rv.aplicar(p, itens, admin)
        orig = {i["produto"]: i for i in p["itens"]}
        mud = []
        for it in itens:
            o = orig.get(it["produto"], {})
            dif = [f"{rot} {o.get(k)}% → {it[k]}%" for k, rot in (("obj", "objetiva"), ("min", "mínima"), ("max", "máxima"))
                   if o.get(k) is not None and abs(float(o.get(k)) - float(it[k])) > 1e-6]
            if dif:
                mud.append(f"{it['produto']}: " + ", ".join(dif))
        texto = (f"{admin} aprovou o seu pedido de nova margem ({p.get('escopo')})"
                 + (" com as seguintes modificações: " + "; ".join(mud[:8]) + (f" e mais {len(mud) - 8}" if len(mud) > 8 else "") + "." if mud else ", sem alterações."))
        try:
            nt.enviar([pedido["usuario"]], "margem_aprovada", "Nova margem aprovada" + (" com modificações" if mud else ""), texto)
        except Exception:
            pass
    elif pedido["tipo"] == "parametros":
        from core import parametros as pm
        msg = pm.aplicar_pedido(bruto.getvalue(), admin)
    elif pedido["tipo"] == "trava":
        from core import trava as tv
        bruto.name = pedido.get("nome_arquivo") or "trava.xlsx"
        r = tv.salvar(tv.ler_planilha(bruto), pedido["usuario"])
        msg = f"{r['linhas']} travas mínimas"
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
    if pedido.get("tipo") == "margens":
        try:
            from core import notificacoes as nt
            nt.enviar([pedido["usuario"]], "margem_recusada", "Pedido de nova margem recusado", f"{admin} recusou o seu pedido: {pedido.get('nome_arquivo')}.")
        except Exception:
            pass
    try:
        db.sb().storage.from_("relatorios").remove([pedido["caminho"]])
    except Exception:
        pass
