"""Base da mesa de precificação (mesma lógica da consulta Power Query de precificação).

Python prepara a base (curva ABC por filial, preço de mercado com hierarquia pesquisa → moda,
base L7 do atacado). As regras de preço rodam no navegador, para recalcular na hora a cada ajuste.
"""
from __future__ import annotations

import base64
import gzip
import json

import numpy as np
import pandas as pd

FILIAIS_85 = (551, 278, 549, 282)   # filiais com mínimo de 85% do custo (demais: 89%)


def curva_abc(df: pd.DataFrame) -> pd.Series:
    """Curva por filial pela venda: acumulado até 80% = A, até 95% = B, resto (e sem venda) = C."""
    venda = df["venda"].astype(np.float64).clip(lower=0)
    ordem = df.assign(_v=venda).sort_values(["Filial", "_v"], ascending=[True, False])
    tot = ordem.groupby("Filial", observed=True)["_v"].transform("sum").replace(0, 1)
    acum = ordem.groupby("Filial", observed=True)["_v"].cumsum() / tot
    curva = np.where(ordem["_v"] <= 0, "C", np.where(acum <= 0.80, "A", np.where(acum <= 0.95, "B", "C")))
    return pd.Series(curva, index=ordem.index).reindex(df.index)


def base(df: pd.DataFrame, so_cesta: bool = True, ignorar_acoes: bool = False, regras: pd.DataFrame | None = None) -> pd.DataFrame:
    b = df[df["cu"] > 0.09]
    if so_cesta and "Cesta" in b:
        b = b[b["Cesta"].astype(str) == "CESTA"]
    b = b.assign(Curva=curva_abc(b))
    if ignorar_acoes:
        b = b[~b["em_acao"] & (b["Classificação"].astype(str) != "TRAVADO - VENCIMENTO")]
    vmk = np.where(b["mk"] > 0, b["mk"], np.where(b["mo"] > 0, b["mo"], np.nan))
    amk = np.where(b["amk"] > 0, b["amk"], np.where(b["ma"] > 0, b["ma"], np.nan))
    b = b.assign(vmk=vmk, amk_ref=amk, origem=np.where(b["mk"] > 0, 0, 1))
    b = b[~np.isnan(b["vmk"])]
    if regras is not None and len(b):
        from core import profimetrics
        r = profimetrics.regras_por_item(_codigo(b["Filial"]), _codigo(b["Produto"]), regras)
        b = b.assign(pf_obj=r["mrg_obj"].to_numpy(), pf_min=r["mrg_min"].to_numpy(), pf_max=r["mrg_max"].to_numpy(),
                     pf_merch=r["merch"].to_numpy())
    return b


def _codigo(s: pd.Series) -> pd.Series:
    return s.astype(str).str.split(" - ").str[0].str.strip()


def payload(b: pd.DataFrame) -> str:
    """Base compacta (colunas + dicionários) em JSON, compactada com gzip e em base64."""
    def dic(col):
        cat = pd.Categorical(b[col].astype(str))
        return list(cat.categories), cat.codes.astype(int).tolist()
    filiais, fi = dic("Filial")
    produtos, pi = dic("Produto")
    concs, ki = dic("Concorrente menor") if "Concorrente menor" in b else ([""], [0] * len(b))
    deps, di = dic("Departamento")
    r2 = lambda s: [round(float(x), 2) if x == x else None for x in s]
    vm = b["vm"].astype(np.float64).to_numpy(); venda = b["venda"].astype(np.float64).to_numpy()
    un = np.where((venda > 0) & (vm > 0), venda / np.where(vm > 0, vm, 1), 0)
    cod_f = _codigo(pd.Series(filiais)).tolist()
    tipos, ti = dic("Tipo de preço PDV") if "Tipo de preço PDV" in b else ([""], [0] * len(b))
    datas, dti = dic("Data pesquisa") if "Data pesquisa" in b else ([""], [0] * len(b))
    col = lambda nome: b[nome] if nome in b else pd.Series(np.nan, index=b.index)
    nn = lambda s: [None if x != x else round(float(x), 2) for x in s]
    merch_html = col("base_red_atacado").astype(float)
    merch = col("pf_merch").astype(float).where(col("pf_merch").notna(), merch_html)
    dados = {
        "filiais": filiais, "filial_cod": cod_f, "produtos": produtos, "produto_cod": _codigo(pd.Series(produtos)).tolist(),
        "concs": concs, "deps": deps,
        "fi": fi, "pi": pi, "ki": ki, "di": di,
        "curva": ["ABC".index(c) for c in b["Curva"]],
        "orig": b["origem"].astype(int).tolist(),
        "cu": r2(b["cu"]), "vm": r2(b["vm"]), "am": r2(b["am"]), "vmk": r2(b["vmk"]), "amk": r2(b["amk_ref"]),
        "mo": r2(b["mo"]), "ma": r2(b["ma"]),
        "merch": [float(x) if x == x else 0.0 for x in merch],
        "pobj": nn(col("pf_obj")), "pmin": nn(col("pf_min")), "pmax": nn(col("pf_max")),
        "cesta": [1 if str(x) == "CESTA" else 0 for x in col("Cesta")],
        "tipos": tipos, "ti": ti, "datas": datas, "dti": dti,
        "dfim": [int(x) for x in col("data_fim").fillna(0)],
        "un": [round(float(x), 1) for x in un], "venda": [round(float(x)) for x in venda],
        "esp": [int(c) if c.isdigit() and int(c) in FILIAIS_85 else 0 for c in cod_f],
    }
    bruto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(bruto, 6)).decode("ascii")
