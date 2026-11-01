"""Base da mesa de precificação (lógica da consulta Power Query de precificação).

Python prepara a base (curva ABC por filial, preço de mercado, regras do Profimetrics,
histórico da concorrência). As regras de preço rodam no navegador, para recalcular na hora.
"""
from __future__ import annotations

import base64
import gzip
import json

import numpy as np
import pandas as pd


def curva_abc(df: pd.DataFrame) -> pd.Series:
    """Curva por filial pela venda: acumulado até 80% = A, até 95% = B, resto (e sem venda) = C."""
    venda = df["venda"].astype(np.float64).clip(lower=0)
    ordem = df.assign(_v=venda).sort_values(["Filial", "_v"], ascending=[True, False])
    tot = ordem.groupby("Filial", observed=True)["_v"].transform("sum").replace(0, 1)
    acum = ordem.groupby("Filial", observed=True)["_v"].cumsum() / tot
    curva = np.where(ordem["_v"] <= 0, "C", np.where(acum <= 0.80, "A", np.where(acum <= 0.95, "B", "C")))
    return pd.Series(curva, index=ordem.index).reindex(df.index)


def base(df: pd.DataFrame, so_cesta: bool = True, ignorar_acoes: bool = False, regras: pd.DataFrame | None = None,
         com_pesquisa: bool = True) -> pd.DataFrame:
    """com_pesquisa=True: só itens com pesquisa direta (menor preço). False: os sem pesquisa, que vão para o objetivo."""
    b = df[df["cu"] > 0.09]
    if so_cesta and "Cesta" in b:
        b = b[b["Cesta"].astype(str) == "CESTA"]
    b = b.assign(Curva=curva_abc(b))
    if ignorar_acoes:
        b = b[~b["em_acao"] & (b["Classificação"].astype(str) != "TRAVADO - VENCIMENTO")]
    b = b[b["mk"] > 0] if com_pesquisa else b[~(b["mk"] > 0)]
    vmk = np.where(b["mk"] > 0, b["mk"], np.where(b["mo"] > 0, b["mo"], np.nan))
    amk = np.where(b["amk"] > 0, b["amk"], np.where(b["ma"] > 0, b["ma"], np.nan))
    b = b.assign(vmk=vmk, amk_ref=amk, origem=np.where(b["mk"] > 0, 0, 1))
    if regras is not None and len(b):
        from core import profimetrics
        r = profimetrics.regras_por_item(_codigo(b["Filial"]), _codigo(b["Produto"]), regras)
        b = b.assign(pf_obj=r["mrg_obj"].to_numpy(), pf_min=r["mrg_min"].to_numpy(), pf_max=r["mrg_max"].to_numpy(),
                     pf_merch=r["merch"].to_numpy())
    return b


def _codigo(s: pd.Series) -> pd.Series:
    return s.astype(str).str.split(" - ").str[0].str.strip()


def _historico(b: pd.DataFrame, hist: dict | None, filiais: list, produtos: list, ufs: list) -> dict:
    """Histórico do estado (concorrentes e nosso preço por dia) dos produtos da mesa + concorrentes de cada filial."""
    vazio = {"hT": [], "hK": [], "hE": [], "dp": [], "du": [], "dk": [], "dt": [], "dv": [], "da": [], "dtp": [],
             "op": [], "ou": [], "ot": [], "ov": [], "oa": [], "oo": [], "hOG": [], "fk": [[] for _ in filiais]}
    necessarios = {"dP", "dU", "dK", "dT", "dV", "dA", "oP", "oU", "oT", "oV", "oA", "fil_conc_f", "fil_conc_k", "K", "T", "U"}
    if not hist or not len(b) or not necessarios.issubset(hist):
        return vazio
    # códigos originais -> índices da mesa
    p_map = pd.Series(pd.Categorical(b["Produto"].astype(str), categories=produtos).codes, index=b["_p"].to_numpy()).groupby(level=0).first()
    f_map = pd.Series(pd.Categorical(b["Filial"].astype(str), categories=filiais).codes, index=b["_f"].to_numpy()).groupby(level=0).first()
    u_map = {k: ufs.index(u) for k, u in enumerate(hist["U"]) if u in ufs}
    if not u_map:
        return vazio
    dP, dU = hist["dP"], hist["dU"]
    m = np.isin(dP, p_map.index.to_numpy()) & np.isin(dU, np.array(list(u_map), dtype=dU.dtype))
    oP, oU = hist["oP"], hist["oU"]
    mo = np.isin(oP, p_map.index.to_numpy()) & np.isin(oU, np.array(list(u_map), dtype=oU.dtype)) & (hist["oT"] != 255)
    k_usados, k_comp = np.unique(hist["dK"][m], return_inverse=True)
    k_pos = {int(k): n for n, k in enumerate(k_usados)}
    um = np.vectorize(lambda x: u_map.get(int(x), 0), otypes=[np.int32])
    fk = [[] for _ in filiais]
    ff, kk = hist["fil_conc_f"], hist["fil_conc_k"]
    for f_cod, k in zip(ff[np.isin(ff, f_map.index.to_numpy())], kk[np.isin(ff, f_map.index.to_numpy())]):
        if int(k) in k_pos:
            fk[int(f_map[f_cod])].append(k_pos[int(k)])
    nomes = lambda lista, idx: [str(lista[x]) if x < len(lista) else "" for x in idx]
    return {"hT": list(hist["T"]), "hK": nomes(hist["K"], k_usados), "hE": nomes(hist.get("KE", []), k_usados),
            "dp": p_map.reindex(dP[m]).astype(int).tolist(), "du": um(dU[m]).tolist() if m.any() else [],
            "dk": k_comp.astype(int).tolist(), "dt": hist["dT"][m].astype(int).tolist(),
            "dv": hist["dV"][m].astype(int).tolist(), "da": hist["dA"][m].astype(int).tolist(),
            "dtp": hist["dTp"][m].astype(int).tolist() if "dTp" in hist else [0] * int(m.sum()),
            "oo": hist["oO"][mo].astype(int).tolist() if "oO" in hist else [0] * int(mo.sum()), "hOG": list(hist.get("OG", [])),
            "op": p_map.reindex(oP[mo]).astype(int).tolist(), "ou": um(oU[mo]).tolist() if mo.any() else [],
            "ot": hist["oT"][mo].astype(int).tolist(), "ov": hist["oV"][mo].astype(int).tolist(), "oa": hist["oA"][mo].astype(int).tolist(),
            "fk": fk}


def _tipo_coleta(s: pd.Series) -> list[int]:
    """1 = regular, 2 = promoção, 3 = ponto extra, 0 = sem informação (o código vem na frente: '1-PRECO REGULAR')."""
    mapa = {"1": 1, "5": 2, "6": 3}
    return [mapa.get(str(x).strip()[:1], 0) for x in s]


def _proporcionais(b: pd.DataFrame, props: pd.DataFrame | None) -> list:
    if props is None or props.empty:
        return []
    pais = set(pd.to_numeric(_codigo(b["Produto"]), errors="coerce").dropna().astype("int64"))
    p = props[props["id_pai"].isin(pais)]
    return [[int(r.id_pai), int(r.id_produto), float(r.proporcao)] for r in p.itertuples()]


def payload(b: pd.DataFrame, hist: dict | None = None, props: pd.DataFrame | None = None) -> str:
    """Base compacta (colunas + dicionários) em JSON, compactada com gzip e em base64."""
    def dic(col):
        cat = pd.Categorical(b[col].astype(str))
        return list(cat.categories), cat.codes.astype(int).tolist()
    filiais, fi = dic("Filial")
    produtos, pi = dic("Produto")
    concs, ki = dic("Concorrente menor") if "Concorrente menor" in b else ([""], [0] * len(b))
    ufs, ui_ = dic("Estado") if "Estado" in b else ([""], [0] * len(b))
    compradores, bi = dic("Comprador") if "Comprador" in b else ([""], [0] * len(b))
    deps, di = dic("Departamento") if "Departamento" in b else ([""], [0] * len(b))
    cats, gi = dic("Categoria") if "Categoria" in b else ([""], [0] * len(b))
    tipos, ti = dic("Tipo de preço PDV") if "Tipo de preço PDV" in b else ([""], [0] * len(b))
    datas, dti = dic("Data pesquisa") if "Data pesquisa" in b else ([""], [0] * len(b))
    col = lambda nome: b[nome] if nome in b else pd.Series(np.nan, index=b.index)
    r2 = lambda s: [round(float(x), 2) if x == x else None for x in s]
    vm = b["vm"].astype(np.float64).to_numpy(); venda = b["venda"].astype(np.float64).to_numpy()
    un = np.where((venda > 0) & (vm > 0), venda / np.where(vm > 0, vm, 1), 0)
    merch = col("pf_merch").astype(float).where(col("pf_merch").notna(), col("base_red_atacado").astype(float))
    dados = {
        "filiais": filiais, "filial_cod": _codigo(pd.Series(filiais)).tolist(), "produtos": produtos,
        "produto_cod": _codigo(pd.Series(produtos)).tolist(), "concs": concs, "ufs": ufs, "tipos": tipos, "datas": datas,
        "fi": fi, "pi": pi, "ki": ki, "ui": ui_, "ti": ti, "dti": dti,
        "compradores": compradores, "bi": bi, "deps": deps, "di": di, "cats": cats, "gi": gi,
        "estoque": r2(col("estoque")), "dde": r2(col("dde")), "idade": r2(col("idade")), "mcob": r2(col("meta_cobertura")),
        "curva": ["ABC".index(c) for c in b["Curva"]], "orig": b["origem"].astype(int).tolist(),
        "cu": r2(b["cu"]), "vm": r2(b["vm"]), "am": r2(b["am"]), "vmk": r2(b["vmk"]), "amk": r2(b["amk_ref"]),
        "mo": r2(b["mo"]), "ma": r2(b["ma"]),
        "merch": [float(x) if x == x else 0.0 for x in merch],
        "pobj": r2(col("pf_obj")), "pmin": r2(col("pf_min")), "pmax": r2(col("pf_max")),
        "cesta": [1 if str(x) == "CESTA" else 0 for x in col("Cesta")],
        "dfim": [int(x) for x in col("data_fim").fillna(0)],
        "un": [round(float(x), 1) for x in un], "venda": [round(float(x)) for x in venda],
        "tcol": _tipo_coleta(col("Tipo de preço").astype(str)),
        "props": _proporcionais(b, props),
        **_historico(b, hist, filiais, produtos, ufs),
    }
    bruto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(bruto, 6)).decode("ascii")
