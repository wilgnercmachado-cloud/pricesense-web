"""Trava mínima (acordo): margem mínima por filial e produto, acima da regra da cesta e do Profimetrics.

Arquivo: ID filial | ID Produto | Margem Mínima (em %, ex.: 10 = 10%).
Na precificação, o varejo nunca fica abaixo dessa margem; quando o preço bate nela, o atacado sai do varejo com a base de redução.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata

import pandas as pd
import streamlit as st

from core import db

TABELA = "trava_minima"


class ErroTrava(ValueError):
    pass


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _num(v) -> float:
    t = str(v).strip().replace("%", "").replace(" ", "")
    if not t or t.lower() == "nan":
        return float("nan")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return float("nan")


def ler_planilha(arquivo) -> pd.DataFrame:
    nome = str(getattr(arquivo, "name", arquivo)).lower()
    if nome.endswith((".csv", ".txt")):
        bruto = arquivo.getvalue() if hasattr(arquivo, "getvalue") else open(arquivo, "rb").read()
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            texto = bruto.decode("latin-1")
        sep = max((";", "|", ",", "\t"), key=texto.splitlines()[0].count)
        df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str)
    else:
        df = pd.read_excel(arquivo, sheet_name=0, dtype=str)
    mapa = {_norm(c): c for c in df.columns}
    cols = {"filial": ("idfilial", "filial", "codfilial"), "produto": ("idproduto", "produto", "codproduto"),
            "margem": ("margemminima", "margemmin", "margem")}
    achadas = {}
    for alvo, nomes in cols.items():
        for n in nomes:
            if n in mapa:
                achadas[alvo] = mapa[n]; break
    faltam = [r for r, a in (("ID filial", "filial"), ("ID Produto", "produto"), ("Margem Mínima", "margem")) if a not in achadas]
    if faltam:
        raise ErroTrava(f"Faltam as colunas {', '.join(faltam)}. O arquivo deve ter: ID filial | ID Produto | Margem Mínima.")
    cod = lambda s: pd.to_numeric(s.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    out = pd.DataFrame({"filial": cod(df[achadas["filial"]]), "produto": cod(df[achadas["produto"]]),
                        "margem_min": df[achadas["margem"]].map(_num)})
    out = out.dropna().astype({"filial": "int64", "produto": "int64"})
    out = out.drop_duplicates(["filial", "produto"], keep="last")
    if out.empty:
        raise ErroTrava("Nenhuma linha válida: confira os códigos de filial e produto e a margem mínima.")
    return out


def salvar(df: pd.DataFrame, usuario: str) -> dict:
    """Grava (substitui a margem da mesma filial + produto; o que não veio no arquivo continua)."""
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    regs = [{"filial": int(f), "produto": int(p), "margem_min": float(m), "atualizado_em": agora, "atualizado_por": usuario}
            for f, p, m in zip(df["filial"], df["produto"], df["margem_min"])]
    from concurrent.futures import ThreadPoolExecutor
    lotes = [regs[i:i + 2000] for i in range(0, len(regs), 2000)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda l: db.sb().table(TABELA).upsert(l, on_conflict="filial,produto").execute(), lotes))
    carregar.clear()
    return {"linhas": len(regs)}


def limpar() -> None:
    db.sb().table(TABELA).delete().gt("filial", -1).execute()
    carregar.clear()


@st.cache_data(ttl=600, show_spinner=False)
def carregar() -> pd.DataFrame:
    linhas, pagina = [], 0
    try:
        while True:
            r = (db.sb().table(TABELA).select("filial, produto, margem_min, atualizado_em, atualizado_por").order("filial").order("produto")
                 .range(pagina * 1000, pagina * 1000 + 999).execute())
            dados = r.data or []
            linhas += dados
            if len(dados) < 1000:
                break
            pagina += 1
    except Exception:
        return pd.DataFrame(columns=["filial", "produto", "margem_min"])
    return pd.DataFrame(linhas, columns=["filial", "produto", "margem_min", "atualizado_em", "atualizado_por"])
