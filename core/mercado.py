"""Inteligência de mercado a partir da base do Competitividade Pricing GMAT (sem upload).

Usado pela tela inicial (painel por estado) e pela Pesquisa de Mercado (MarketMetrics).
"""
from __future__ import annotations

import base64
import gzip
import json

import numpy as np
import pandas as pd
import streamlit as st


PAINEIS: dict = {}          # painel da tela inicial já calculado, por versão (abre o início sem esperar)


def base_padrao():
    """(df, meta, relatório) do Competitividade Pricing GMAT mais recente, ou None."""
    from views import regular
    return regular.base_atual()          # HTML + 1067 do dia, quando houver


def _gz(obj) -> str:
    return base64.b64encode(gzip.compress(json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode(), 6)).decode()


@st.cache_resource(show_spinner=False, max_entries=4)
def painel_estados(versao: str, _df: pd.DataFrame, _meta: dict, _regras: pd.DataFrame | None) -> dict:
    """Indicadores por estado: IP, oportunidade de captura de margem, investimento abaixo do custo e margens fora das regras."""
    from core import profimetrics as pf
    df = _df[(_df["cu"] > 0.09) & (_df["vm"] > 0)]
    def cod(s):                                   # código pela categoria (rápido em 478 mil linhas)
        if hasattr(s, "cat"):
            cats = pd.Series(s.cat.categories.astype(str)).str.split(" - ").str[0].str.strip().to_numpy()
            return pd.Series(cats[s.cat.codes.to_numpy()], index=s.index)
        return s.astype(str).str.split(" - ").str[0].str.strip()
    r = pf.regras_por_item(cod(df["Filial"]), cod(df["Produto"]), _regras) if _regras is not None and len(_regras) else None
    cu, vm, mk = df["cu"].to_numpy(float), df["vm"].to_numpy(float), df["mk"].to_numpy(float)
    venda = df["venda"].to_numpy(float)
    un = np.where(vm > 0, venda / np.where(vm > 0, vm, 1), 0)
    cesta = (df["Cesta"].astype(str) == "CESTA").to_numpy() if "Cesta" in df else np.zeros(len(df), bool)
    mmax = np.where(np.isnan(r["mrg_max"].to_numpy()), 30.0, r["mrg_max"].to_numpy()) if r is not None else np.full(len(df), 30.0)
    mmin_pf = r["mrg_min"].to_numpy() if r is not None else np.full(len(df), np.nan)
    mmin = np.where(cesta, -15.0, np.where(np.isnan(mmin_pf), 0.0, mmin_pf))
    marg = (vm - cu) / vm * 100
    tem_mk = mk > 0
    ip = np.where(tem_mk, vm / np.where(tem_mk, mk, 1), np.nan)
    opor = np.where(tem_mk & (vm < mk - 0.01), (mk - 0.01 - vm) * un, 0)          # margem que dá para capturar sem passar do mercado
    inv = np.where(vm < cu, (cu - vm) * un, 0)                                    # investimento: venda abaixo do custo
    est = df["Estado"].astype(str).to_numpy()
    linhas = []
    for e in sorted(set(est)):
        m = est == e
        w = np.where(un[m] > 0, un[m], 1)
        ipm = np.nansum(vm[m][tem_mk[m]] * w[tem_mk[m]]) / max(1e-9, np.nansum(mk[m][tem_mk[m]] * w[tem_mk[m]]))
        mg = np.nansum((vm[m] - cu[m]) * un[m]) / max(1e-9, np.nansum(vm[m] * un[m]))
        linhas.append({"uf": e, "itens": int(m.sum()), "ip": round(float(ipm), 4), "margem": round(float(mg), 4), "venda": round(float(venda[m].sum())),
                       "acima_mercado": int(np.nansum((ip[m] > 1.009))), "abaixo_mercado": int(np.nansum(ip[m] < 0.99)),
                       "opor_cesta": round(float(opor[m & cesta].sum())), "opor_nao": round(float(opor[m & ~cesta].sum())),
                       "inv_cesta": round(float(inv[m & cesta].sum())), "inv_nao": round(float(inv[m & ~cesta].sum())),
                       "acima_max": int((marg[m] > mmax[m]).sum()), "abaixo_min": int((marg[m] < mmin[m]).sum()),
                       "sem_pesquisa": int((~tem_mk[m]).sum())})
    # série diária do IP por estado (nosso preço médio ÷ menor preço do mercado, no histórico de 30 dias)
    serie = {}
    h = _meta.get("hist")
    if h and {"dP", "dU", "dT", "dV", "oP", "oU", "oT", "oV"}.issubset(h):
        d = pd.DataFrame({"p": h["dP"], "u": h["dU"], "t": h["dT"], "v": h["dV"]})
        d = d[d["v"] > 0].groupby(["u", "t", "p"], as_index=False)["v"].min()
        o = pd.DataFrame({"p": h["oP"], "u": h["oU"], "t": h["oT"], "v": h["oV"]})
        o = o[o["v"] > 0].groupby(["u", "t", "p"], as_index=False)["v"].mean()
        j = d.merge(o, on=["u", "t", "p"], suffixes=("_m", "_n"))
        g = j.groupby(["u", "t"]).agg(n=("v_n", "sum"), m=("v_m", "sum"), q=("p", "size")).reset_index()
        for u, sub in g.groupby("u"):
            nome = h["U"][int(u)] if int(u) < len(h["U"]) else str(u)
            serie[nome] = [[int(t), round(float(n / m), 4), int(q)] for t, n, m, q in zip(sub["t"], sub["n"], sub["m"], sub["q"])]
    return {"estados": linhas, "serie": serie, "dias": list(h.get("T", [])) if h else []}


@st.cache_resource(show_spinner=False, max_entries=6)
def pacote_mercado(versao: str, uf: str, so_cesta: bool, deps: tuple[str, ...], _df: pd.DataFrame, _meta: dict) -> tuple[str, int]:
    """Histórico de 30 dias do estado (coletas por concorrente e nosso preço) com os dados atuais de cada produto."""
    h = _meta.get("hist")
    if not h:
        return "", 0
    b = _df[_df["Estado"].astype(str) == uf]
    if so_cesta and "Cesta" in b:
        b = b[b["Cesta"].astype(str) == "CESTA"]
    if deps:
        b = b[b["Departamento"].astype(str).isin(deps)]
    if b.empty or uf not in h["U"]:
        return "", 0
    ui = h["U"].index(uf)
    w = np.where(b["vm"] > 0, b["venda"] / b["vm"].where(b["vm"] > 0, 1), 0)
    prod = (b.assign(_w=w).groupby("_p", observed=True)
              .agg(nome=("Produto", "first"), dep=("Departamento", "first"), cat=("Categoria", "first"), vm=("vm", "median"), cu=("cu", "median"),
                   venda=("venda", "sum"), un=("_w", "sum"), filiais=("Filial", "nunique"), cesta=("Cesta", "first")).reset_index())
    pos = {int(p): k for k, p in enumerate(prod["_p"])}
    m = (h["dU"] == ui) & np.isin(h["dP"], prod["_p"].to_numpy())
    mo = (h["oU"] == ui) & np.isin(h["oP"], prod["_p"].to_numpy()) & (h["oT"] != 255)
    ks, kinv = np.unique(h["dK"][m], return_inverse=True)
    mapa = np.vectorize(lambda x: pos[int(x)], otypes=[np.int32])
    dados = {
        "uf": uf, "T": list(h["T"]), "K": [str(h["K"][x]) for x in ks], "KE": [str(h["KE"][x]) if x < len(h.get("KE", [])) else "" for x in ks],
        "prod": [str(x) for x in prod["nome"]], "dep": [str(x) for x in prod["dep"]], "cat": [str(x) for x in prod["cat"]],
        "vm": [round(float(x), 2) for x in prod["vm"]], "cu": [round(float(x), 2) for x in prod["cu"]], "venda": [round(float(x)) for x in prod["venda"]],
        "un": [round(float(x), 1) for x in prod["un"]], "fil": [int(x) for x in prod["filiais"]], "cesta": [1 if str(x) == "CESTA" else 0 for x in prod["cesta"]],
        "dp": mapa(h["dP"][m]).tolist() if m.any() else [], "dk": kinv.astype(int).tolist(), "dt": h["dT"][m].astype(int).tolist(),
        "dv": h["dV"][m].astype(int).tolist(), "da": h["dA"][m].astype(int).tolist(), "dtp": h["dTp"][m].astype(int).tolist() if "dTp" in h else [],
        "op": mapa(h["oP"][mo]).tolist() if mo.any() else [], "ot": h["oT"][mo].astype(int).tolist(), "ov": h["oV"][mo].astype(int).tolist(), "oa": h["oA"][mo].astype(int).tolist(),
    }
    return _gz(dados), int(m.sum())
