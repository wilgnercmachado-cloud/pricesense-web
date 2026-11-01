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


def _historico(b: pd.DataFrame, hist: dict | None) -> dict:
    """Linhas do histórico (concorrente x dia) só dos pares filial x produto da mesa."""
    if not hist or not len(b):
        return {"hi": [], "hk": [], "hd": [], "hv": [], "ha": [], "hK": [], "hT": []}
    chave_b = b["_p"].to_numpy(np.int64) * 1000 + b["_f"].to_numpy(np.int64)
    pos = pd.Series(np.arange(len(b)), index=chave_b)
    pos = pos[~pos.index.duplicated()]
    chave_h = hist["p"].astype(np.int64) * 1000 + hist["f"].astype(np.int64)
    m = np.isin(chave_h, pos.index.to_numpy())
    idx = pos.reindex(chave_h[m]).to_numpy()
    k = hist["k"][m]
    ks, kinv = np.unique(k, return_inverse=True)
    nomes = [str(hist["K"][x]) if x < len(hist["K"]) else "" for x in ks]
    return {"hi": idx.astype(int).tolist(), "hk": kinv.astype(int).tolist(), "hd": hist["d"][m].astype(int).tolist(),
            "hv": hist["v"][m].astype(int).tolist(), "ha": hist["a"][m].astype(int).tolist(), "hK": nomes, "hT": list(hist["T"])}


def payload(b: pd.DataFrame, hist: dict | None = None) -> str:
    """Base compacta (colunas + dicionários) em JSON, compactada com gzip e em base64."""
    def dic(col):
        cat = pd.Categorical(b[col].astype(str))
        return list(cat.categories), cat.codes.astype(int).tolist()
    filiais, fi = dic("Filial")
    produtos, pi = dic("Produto")
    concs, ki = dic("Concorrente menor") if "Concorrente menor" in b else ([""], [0] * len(b))
    ufs, ui_ = dic("Estado") if "Estado" in b else ([""], [0] * len(b))
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
        "curva": ["ABC".index(c) for c in b["Curva"]], "orig": b["origem"].astype(int).tolist(),
        "cu": r2(b["cu"]), "vm": r2(b["vm"]), "am": r2(b["am"]), "vmk": r2(b["vmk"]), "amk": r2(b["amk_ref"]),
        "mo": r2(b["mo"]), "ma": r2(b["ma"]),
        "merch": [float(x) if x == x else 0.0 for x in merch],
        "pobj": r2(col("pf_obj")), "pmin": r2(col("pf_min")), "pmax": r2(col("pf_max")),
        "cesta": [1 if str(x) == "CESTA" else 0 for x in col("Cesta")],
        "dfim": [int(x) for x in col("data_fim").fillna(0)],
        "un": [round(float(x), 1) for x in un], "venda": [round(float(x)) for x in venda],
        **_historico(b, hist),
    }
    bruto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(bruto, 6)).decode("ascii")
