"""Concorrentes associados a cada filial (configuração da pesquisa), a partir da base do Competitividade Pricing GMAT.

A associação vem do próprio relatório (bloco data4: quais lojas concorrentes cada filial pesquisa). Para cada par
filial x loja concorrente mostramos a bandeira, quantas coletas a loja teve no estado no período e o dia da última.
Nada vem do Supabase: tudo sai da base que o servidor já tem carregada.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_resource(show_spinner=False, max_entries=2)
def tabela(versao: str, _df: pd.DataFrame, _meta: dict) -> pd.DataFrame:
    h = _meta.get("hist") or {}
    colunas = ["Estado", "Filial", "Bandeira", "Concorrente", "Coletas no período", "Última coleta"]
    if not {"fil_conc_f", "fil_conc_k", "K"}.issubset(h):
        return pd.DataFrame(columns=colunas)
    fil = _df[["_f", "Filial", "Estado"]].drop_duplicates("_f")
    fil = pd.DataFrame({"f": fil["_f"].astype(int).to_numpy(), "Filial": fil["Filial"].astype(str).to_numpy(),
                        "Estado": fil["Estado"].astype(str).to_numpy()})
    pares = pd.DataFrame({"f": np.asarray(h["fil_conc_f"]).astype(int), "k": np.asarray(h["fil_conc_k"]).astype(int)})
    t = pares.merge(fil, on="f", how="inner")
    nomes, bandeiras = list(h.get("K") or []), list(h.get("KE") or [])
    t["Concorrente"] = [str(nomes[k]) if 0 <= k < len(nomes) else f"Concorrente {k}" for k in t["k"]]
    t["Bandeira"] = [str(bandeiras[k]) if 0 <= k < len(bandeiras) and str(bandeiras[k]).strip() else "-" for k in t["k"]]
    # coletas e última coleta da loja concorrente no estado da filial (histórico do período)
    dias = list(h.get("T") or [])
    ufs = list(h.get("U") or [])
    if {"dU", "dK", "dT"}.issubset(h) and len(h["dK"]):
        c = pd.DataFrame({"u": np.asarray(h["dU"]).astype(int), "k": np.asarray(h["dK"]).astype(int), "t": np.asarray(h["dT"]).astype(int)})
        g = c.groupby(["u", "k"]).agg(n=("t", "size"), ult=("t", "max")).reset_index()
        g["Estado"] = [ufs[u] if 0 <= u < len(ufs) else "" for u in g["u"]]
        t = t.merge(g[["Estado", "k", "n", "ult"]], on=["Estado", "k"], how="left")
    else:
        t["n"], t["ult"] = 0, -1
    t["Coletas no período"] = t["n"].fillna(0).astype(int)
    t["Última coleta"] = [str(dias[int(x)]) if pd.notna(x) and 0 <= int(x) < len(dias) else "sem coleta" for x in t["ult"]]
    t = t.sort_values(["Estado", "Filial", "Bandeira", "Concorrente"], key=lambda s: s.str.lower() if s.dtype == object else s)
    return t[colunas].reset_index(drop=True)


def filiais_sem_concorrente(versao: str, _df: pd.DataFrame, assoc: pd.DataFrame) -> pd.DataFrame:
    todas = _df[["Estado", "Filial"]].astype(str).drop_duplicates()
    com = set(assoc["Filial"]) if len(assoc) else set()
    return todas[~todas["Filial"].isin(com)].sort_values(["Estado", "Filial"]).reset_index(drop=True)
