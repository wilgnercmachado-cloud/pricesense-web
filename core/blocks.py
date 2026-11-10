"""BLOCK do comercial na PriceMetrics: o comprador trava um item (filial + produto) cujo novo preço sugerido ficou abaixo do custo.

Regras combinadas com o usuário:
- motivo obrigatório: Falta de investimento, Possível erro de pesquisa ou Outros (com observação obrigatória);
- dura pelo menos 3 dias e até o preço vencedor que motivou o block sair da análise;
- quem deu o block e o administrador podem retirá-lo a qualquer momento;
- no Pricing o item fica travado: só aceita preço manual pelo menos 2% diferente do preço vencedor do block.
"""
from __future__ import annotations

import datetime as dt
import uuid

import pandas as pd
import streamlit as st

from core import db

TABELA = "blocks_comercial"
MOTIVOS = ["Falta de investimento", "Possível erro de pesquisa", "Outros"]
DIAS_MINIMOS = 3


@st.cache_data(ttl=60, show_spinner=False)
def ativos() -> list[dict]:
    try:
        return db.sb().table(TABELA).select("*").eq("ativo", True).execute().data or []
    except Exception:
        return []


def criar(filial: int, produto: int, estado: str, motivo: str, observacao: str, usuario: str, preco_vencedor: float, concorrente: str,
          data_pesquisa: str) -> dict:
    if motivo not in MOTIVOS:
        raise ValueError("Escolha o motivo do BLOCK.")
    if motivo == "Outros" and not (observacao or "").strip():
        raise ValueError("Em \"Outros\", descreva o motivo na observação.")
    reg = {"id": str(uuid.uuid4()), "filial": int(filial), "produto": int(produto), "estado": estado, "motivo": motivo,
           "observacao": (observacao or "").strip(), "usuario": usuario, "preco_vencedor": float(preco_vencedor),
           "concorrente": concorrente, "data_pesquisa": data_pesquisa, "ativo": True,
           "criado_em": dt.datetime.now(dt.timezone.utc).isoformat()}
    db.sb().table(TABELA).insert(reg).execute()
    ativos.clear()
    return reg


def remover(ident: str, usuario: str, motivo: str = "retirado") -> None:
    db.sb().table(TABELA).update({"ativo": False, "removido_por": usuario, "removido_em": dt.datetime.now(dt.timezone.utc).isoformat(),
                                  "fim_motivo": motivo}).eq("id", ident).execute()
    ativos.clear()


def expirar(blocks: list[dict], df: pd.DataFrame) -> list[dict]:
    """Encerra os blocks com 3 dias ou mais cujo preço vencedor já saiu da análise (outro preço ou outro concorrente)."""
    if not blocks or df is None or not len(df):
        return blocks
    agora = dt.datetime.now(dt.timezone.utc)
    cod = lambda s: pd.to_numeric(s.astype(str).str.split(" - ").str[0].str.strip(), errors="coerce")
    alvo = {(int(b["filial"]), int(b["produto"])) for b in blocks}
    fc, pc = cod(df["Filial"]), cod(df["Produto"])
    m = pd.Series([(f, p) in alvo for f, p in zip(fc.fillna(-1).astype(int), pc.fillna(-1).astype(int))], index=df.index)
    atual = {(int(f), int(p)): (float(mk), str(c)) for f, p, mk, c in zip(fc[m], pc[m], df.loc[m, "mk"], df.loc[m, "Concorrente menor"])}
    ficam = []
    for b in blocks:
        try:
            idade = agora - dt.datetime.fromisoformat(str(b["criado_em"]).replace("Z", "+00:00"))
        except Exception:
            idade = dt.timedelta(0)
        hoje = atual.get((int(b["filial"]), int(b["produto"])))
        saiu = hoje is None or abs(hoje[0] - float(b["preco_vencedor"] or 0)) > 0.004 or hoje[1] != str(b.get("concorrente") or "")
        if idade >= dt.timedelta(days=DIAS_MINIMOS) and saiu:
            try:
                remover(b["id"], "regra", "preço vencedor saiu da análise após 3 dias")
            except Exception:
                pass
            continue
        ficam.append(b)
    return ficam
