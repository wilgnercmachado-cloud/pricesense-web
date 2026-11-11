"""Precificação online (ao vivo): o analista de Pricing transmite a mesa de um ou mais estados para quem assiste.

Regras combinadas com o usuário:
- o analista inicia a precificação online dos estados; só ele transmite aqueles estados até encerrar;
- o Comercial vê ao vivo todos os novos preços do analista, com os já aceitos em destaque;
- outros analistas continuam trabalhando offline e podem assistir, como o Comercial;
- ao encerrar, os preços finais ficam congelados na visão comercial até chegar uma base nova (HTML novo);
- quem assiste navega livremente: as atualizações não mexem na rolagem nem na seleção.
"""
from __future__ import annotations

import datetime as dt
import uuid

from core import db

TABELA = "precificacao_online"
CAMPOS_META = "id, analista, analista_nome, estados, base, ativo, iniciado_em, encerrado_em, versao, atualizado_em"


def _agora() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def estados_de(s: dict) -> list[str]:
    return [x for x in str(s.get("estados") or "").split(";") if x]


def sessoes(base: str) -> list[dict]:
    """Sessões da base atual (ao vivo e encerradas), sem os dados; a mais recente primeiro."""
    try:
        d = db.sb().table(TABELA).select(CAMPOS_META).eq("base", base).execute().data or []
    except Exception:
        return []
    return sorted(d, key=lambda s: str(s.get("iniciado_em") or ""), reverse=True)


def vigentes(base: str) -> dict[str, dict]:
    """Por estado, a sessão que vale: a ao vivo, ou a última encerrada (preços congelados até a próxima base)."""
    out: dict[str, dict] = {}
    for s in sessoes(base):
        for uf in estados_de(s):
            atual = out.get(uf)
            if atual is None or (s.get("ativo") and not atual.get("ativo")):
                out[uf] = s
    return out


def minha_ativa(base: str, analista: str) -> dict | None:
    return next((s for s in sessoes(base) if s.get("ativo") and s.get("analista") == analista), None)


def iniciar(base: str, analista: str, nome: str, estados: list[str]) -> dict:
    estados = sorted({e for e in estados if e})
    if not estados:
        raise ValueError("Escolha pelo menos um estado.")
    ocupados = [(uf, s) for s in sessoes(base) if s.get("ativo") and s.get("analista") != analista for uf in estados_de(s) if uf in estados]
    if ocupados:
        uf, s = ocupados[0]
        raise ValueError(f"{uf} já está em precificação online com {s.get('analista_nome') or s.get('analista')}.")
    for s in sessoes(base):                          # uma sessão ao vivo por analista: a anterior é encerrada
        if s.get("ativo") and s.get("analista") == analista:
            encerrar(s["id"])
    reg = {"id": str(uuid.uuid4()), "analista": analista, "analista_nome": nome, "estados": ";".join(estados), "base": base,
           "ativo": True, "iniciado_em": _agora(), "versao": 0, "atualizado_em": _agora(), "dados": ""}
    db.sb().table(TABELA).insert(reg).execute()
    return reg


def encerrar(ident: str) -> None:
    db.sb().table(TABELA).update({"ativo": False, "encerrado_em": _agora()}).eq("id", ident).execute()


def publicar(ident: str, analista: str, versao: int, dados: str) -> None:
    """Grava o retrato atual da mesa do analista (compactado). Só o dono da sessão ao vivo publica."""
    db.sb().table(TABELA).update({"dados": dados, "versao": int(versao), "atualizado_em": _agora()}) \
        .eq("id", ident).eq("analista", analista).eq("ativo", True).execute()


def dados(ident: str) -> str:
    try:
        r = db.sb().table(TABELA).select("dados").eq("id", ident).execute().data or []
        return (r[0].get("dados") or "") if r else ""
    except Exception:
        return ""
