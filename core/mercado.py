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


# ================================================================ Market Metrics (tela nova)
TIPO_ENCARTE = 2                 # tipo de preço da coleta: 0 regular, 1 promoção, 2 encarte, 3 mídia, 4 ponto extra...
LIMITE_LINHAS_FILIAL = 150_000   # acima disso, as linhas por filial não vão para a tela (peça menos estados)


def _metricas(D: pd.DataFrame, chaves: list[str]) -> pd.DataFrame:
    """Para cada grupo (produto, ou produto x estado): coletas, concorrentes, menor recente, menor histórico, moda,
    frequência da moda e preço de encarte. Preços em centavos; k = índice do concorrente; t = índice do dia."""
    g = D.groupby(chaves, sort=False)
    out = pd.DataFrame({"col": g.size(), "nk": g["k"].nunique()})
    # menor recente: entre as coletas mais recentes de cada concorrente, a mais barata
    tl = D.groupby(chaves + ["k"], sort=False)["t"].transform("max")
    R = D[D["t"] == tl]
    i = R.groupby(chaves, sort=False)["v"].idxmin()
    r = R.loc[i.values, chaves + ["v", "k", "t"]].set_index(chaves)
    out[["rv", "rk", "rt"]] = r[["v", "k", "t"]]
    ra = R[R["a"] > 0].groupby(chaves, sort=False)["a"].min()
    out["ra"] = ra
    # menor histórico do período
    i = D.groupby(chaves, sort=False)["v"].idxmin()
    h = D.loc[i.values, chaves + ["v", "k", "t"]].set_index(chaves)
    out[["hv", "hk", "ht"]] = h[["v", "k", "t"]]
    out["ha"] = D[D["a"] > 0].groupby(chaves, sort=False)["a"].min()
    # moda do varejo (empate: o menor preço) e frequência = dias distintos (por concorrente) com o preço moda
    c = D.groupby(chaves + ["v"], sort=False).size().rename("n").reset_index().sort_values(chaves + ["n", "v"], ascending=[True] * len(chaves) + [False, True])
    mv = c.drop_duplicates(chaves).set_index(chaves)["v"]
    out["mv"] = mv
    j = D.merge(mv.rename("_m").reset_index(), on=chaves)
    out["fq"] = j[j["v"] == j["_m"]].drop_duplicates(chaves + ["k", "t"]).groupby(chaves, sort=False).size()
    A = D[D["a"] > 0]
    if len(A):
        c = A.groupby(chaves + ["a"], sort=False).size().rename("n").reset_index().sort_values(chaves + ["n", "a"], ascending=[True] * len(chaves) + [False, True])
        out["ma"] = c.drop_duplicates(chaves).set_index(chaves)["a"]
    else:
        out["ma"] = np.nan
    # encarte: o menor preço de encarte do período
    E = D[D["tp"] == TIPO_ENCARTE]
    if len(E):
        i = E.groupby(chaves, sort=False)["v"].idxmin()
        e = E.loc[i.values, chaves + ["v", "k", "t"]].set_index(chaves)
        out[["ev", "ek", "et"]] = e[["v", "k", "t"]]
    else:
        out[["ev", "ek", "et"]] = np.nan
    return out


def _lista(s, inteiro=True):
    """Série -> lista JSON (vazio = -1)."""
    a = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    return [int(x) if x == x else -1 for x in a] if inteiro else [round(float(x), 2) if x == x else -1 for x in a]


@st.cache_resource(show_spinner=False, max_entries=6)
def pacote_mercado_v2(versao: str, ufs: tuple[str, ...], compradores: tuple[str, ...], deps: tuple[str, ...], cats: tuple[str, ...],
                      so_cesta: bool, _df: pd.DataFrame, _meta: dict) -> tuple[str, dict]:
    """Dados da Market Metrics: produtos -> estados -> filiais, cartões e séries por bandeira. Tudo da base já carregada
    no servidor (nada do Supabase). Menor preço, moda e encarte usam o mesmo corte de erro do preço vencedor (margem de
    mercado entre -40% e +60%; atacado maior que o varejo sai); o gráfico mostra a pesquisa como veio."""
    h = _meta.get("hist")
    if not h or not ufs:
        return "", {"produtos": 0}
    b = _df[_df["Estado"].astype(str).isin(ufs)]
    if compradores and "Comprador" in b:
        b = b[b["Comprador"].astype(str).isin(compradores)]
    if deps:
        b = b[b["Departamento"].astype(str).isin(deps)]
    if cats and "Categoria" in b:
        b = b[b["Categoria"].astype(str).isin(cats)]
    if so_cesta and "Cesta" in b:
        b = b[b["Cesta"].astype(str) == "CESTA"]
    U = list(h["U"])
    uis = [U.index(u) for u in ufs if u in U]
    if b.empty or not uis:
        return "", {"produtos": 0}
    col = lambda c: b[c].astype(str) if c in b else pd.Series([""] * len(b), index=b.index)
    w = np.where(b["vm"] > 0, b["venda"] / b["vm"].where(b["vm"] > 0, 1), 0)
    prod = (b.assign(_w=w, _comp=col("Comprador"), _cat=col("Categoria"), _ces=col("Cesta"))
              .groupby("_p", observed=True)
              .agg(nome=("Produto", "first"), dep=("Departamento", "first"), cat=("_cat", "first"), comp=("_comp", "first"),
                   cesta=("_ces", "first"), vm=("vm", "median"), cu=("cu", "median"), venda=("venda", "sum"), fil=("Filial", "nunique"))
              .reset_index())
    P = prod["_p"].to_numpy()
    # coletas do período nos estados escolhidos
    m = np.isin(np.asarray(h["dU"]), uis) & np.isin(np.asarray(h["dP"]), P)
    D = pd.DataFrame({"p": np.asarray(h["dP"])[m].astype(np.int64), "u": np.asarray(h["dU"])[m].astype(np.int64),
                      "k": np.asarray(h["dK"])[m].astype(np.int64), "t": np.asarray(h["dT"])[m].astype(np.int64),
                      "v": np.asarray(h["dV"])[m].astype(np.int64), "a": np.asarray(h["dA"])[m].astype(np.int64),
                      "tp": np.asarray(h["dTp"])[m].astype(np.int64) if "dTp" in h else 0})
    D = D[D["v"] > 0]
    bruto = D
    # corte de erro (igual ao preço vencedor), com o custo do produto no estado
    cu = (b.groupby(["_p", "Estado"], observed=True)["cu"].median().reset_index())
    cu["u"] = [U.index(x) if x in U else -1 for x in cu["Estado"].astype(str)]
    D = D.merge(cu.rename(columns={"_p": "p"})[["p", "u", "cu"]], on=["p", "u"], how="left")
    v, cuv, a = D["v"].to_numpy(float) / 100, D["cu"].fillna(0).to_numpy(float), D["a"].to_numpy(float) / 100
    margem = np.where(v > 0, (v - cuv) / np.where(v > 0, v, 1), 0)
    ok = ((cuv <= 0.09) | ((margem >= -0.40 - 1e-9) & (margem <= 0.60 + 1e-9))) & ~((a > 0) & (a > v + 1e-9))
    D = D[ok].drop(columns=["cu"])
    if D.empty:
        return "", {"produtos": len(prod)}
    mp = _metricas(D, ["p"]).reindex(P)
    me = _metricas(D, ["p", "u"]).reset_index()
    pos = {int(p): i for i, p in enumerate(P)}
    K = [str(x) for x in h.get("K", [])]
    KE = [str(x) if str(x).strip() else K[i] for i, x in enumerate(h.get("KE", []))] if h.get("KE") else K
    # bandeiras (gráficos) e nosso preço por dia
    bruto = bruto.assign(bd=[KE[k] if 0 <= k < len(KE) else "?" for k in bruto["k"]])
    bands = list(bruto.groupby("bd").size().sort_values(ascending=False).index)
    bpos = {x: i for i, x in enumerate(bands)}
    s = bruto.groupby(["p", "bd", "t"], sort=False)["v"].min().reset_index()
    o = pd.DataFrame()
    if {"oP", "oU", "oT", "oV"}.issubset(h) and len(h["oP"]):
        mo = np.isin(np.asarray(h["oU"]), uis) & np.isin(np.asarray(h["oP"]), P) & (np.asarray(h["oT"]) != 255)
        o = pd.DataFrame({"p": np.asarray(h["oP"])[mo], "t": np.asarray(h["oT"])[mo], "v": np.asarray(h["oV"])[mo]})
        o = o[o["v"] > 0].groupby(["p", "t"])["v"].mean().round().reset_index()
    # filiais
    fil_cols = {"Filial": "Filial", "Estado": "Estado", "mk": "mk", "amk": "amk", "mo": "mo", "ma": "ma", "vm": "vm",
                "Concorrente menor": "conc", "Data pesquisa": "data"}
    linhas_fil = len(b)
    F = None
    if linhas_fil <= LIMITE_LINHAS_FILIAL:
        F = b[["_p"] + [c for c in fil_cols if c in b]].copy()
    dados = {
        "ufs": list(ufs), "T": [str(x) for x in h.get("T", [])], "K": K, "B": bands,
        "p": {"nome": [str(x) for x in prod["nome"]], "dep": [str(x) for x in prod["dep"]], "cat": [str(x) for x in prod["cat"]],
              "comp": [str(x) for x in prod["comp"]], "cesta": [1 if str(x) == "CESTA" else 0 for x in prod["cesta"]],
              "vm": _lista(prod["vm"], False), "cu": _lista(prod["cu"], False), "venda": _lista(prod["venda"]), "fil": _lista(prod["fil"])},
        "m": {c: _lista(mp[c]) for c in ["col", "nk", "rv", "ra", "rk", "rt", "hv", "ha", "hk", "ht", "mv", "ma", "fq", "ev", "ek", "et"]},
        "e": {"p": [pos[int(x)] for x in me["p"]], "u": [U[int(x)] for x in me["u"]],
              **{c: _lista(me[c]) for c in ["col", "nk", "rv", "ra", "rk", "rt", "hv", "ha", "hk", "ht", "mv", "ma", "fq", "ev", "ek", "et"]}},
        "s": {"p": [pos[int(x)] for x in s["p"]], "b": [bpos[x] for x in s["bd"]], "t": _lista(s["t"]), "v": _lista(s["v"])},
        "o": {"p": [pos[int(x)] for x in o["p"]] if len(o) else [], "t": _lista(o["t"]) if len(o) else [], "v": _lista(o["v"]) if len(o) else []},
        "f": None if F is None else {
            "p": [pos.get(int(x), -1) for x in F["_p"]], "fil": [str(x) for x in F["Filial"]], "uf": [str(x) for x in F["Estado"]],
            "mk": _lista(F["mk"], False) if "mk" in F else [], "amk": _lista(F["amk"], False) if "amk" in F else [],
            "mo": _lista(F["mo"], False) if "mo" in F else [], "ma": _lista(F["ma"], False) if "ma" in F else [],
            "vm": _lista(F["vm"], False) if "vm" in F else [],
            "conc": [str(x) for x in F["Concorrente menor"]] if "Concorrente menor" in F else [],
            "data": [str(x) for x in F["Data pesquisa"]] if "Data pesquisa" in F else []},
        "f_excesso": F is None,
    }
    return _gz(dados), {"produtos": len(prod), "coletas": int(len(bruto)), "filiais": int(b["Filial"].nunique()), "linhas_fil": linhas_fil}
