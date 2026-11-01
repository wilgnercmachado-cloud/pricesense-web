"""Proporcionais: produtos filhos precificados a partir do produto PAI (ex.: pacote 2,5 kg = 250% do PAI).

As proporções ficam na própria dim_produto (colunas id_pai e proporcao). Só interessam as
diferentes de 100; cada novo envio substitui a proporção do mesmo produto.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd
import streamlit as st

from core import db


class ErroProporcao(ValueError):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ler_planilha(arquivo) -> pd.DataFrame:
    bruto = None
    for motor in ("calamine", "openpyxl"):
        try:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            bruto = pd.read_excel(arquivo, sheet_name=0, engine=motor)
            break
        except ImportError:
            continue
        except Exception as exc:
            raise ErroProporcao(f"Não foi possível ler a planilha: {exc}") from exc
    if bruto is None:
        raise ErroProporcao("Não foi possível ler a planilha.")
    mapa = {_norm(c): c for c in bruto.columns}
    faltam = [c for c in ("idproduto", "idpai", "proporcao") if c not in mapa]
    if faltam:
        raise ErroProporcao("A planilha precisa das colunas ID_PRODUTO, ID_PAI e Proporcao (como a base PROP%).")
    df = pd.DataFrame({"id_produto": pd.to_numeric(bruto[mapa["idproduto"]], errors="coerce"),
                       "id_pai": pd.to_numeric(bruto[mapa["idpai"]], errors="coerce"),
                       "proporcao": pd.to_numeric(bruto[mapa["proporcao"]], errors="coerce")})
    df = df.dropna()
    df = df[(df["proporcao"] != 100) & (df["proporcao"] > 0) & (df["id_produto"] != df["id_pai"])]
    df = df.astype({"id_produto": "int64", "id_pai": "int64"})
    return df.drop_duplicates("id_produto", keep="last").reset_index(drop=True)


def salvar(df: pd.DataFrame) -> dict:
    """Atualiza id_pai e proporcao na dim_produto (só produtos que já existem nela)."""
    ids = df["id_produto"].tolist()
    existentes: set[int] = set()
    for i in range(0, len(ids), 300):
        resp = db.sb().table("dim_produto").select("id_produto").in_("id_produto", ids[i:i + 300]).execute()
        existentes.update(int(r["id_produto"]) for r in (resp.data or []))
    validos = df[df["id_produto"].isin(existentes)]
    registros = [{"id_produto": int(r.id_produto), "id_pai": int(r.id_pai), "proporcao": float(r.proporcao)} for r in validos.itertuples()]
    for i in range(0, len(registros), 500):
        db.sb().table("dim_produto").upsert(registros[i:i + 500], on_conflict="id_produto").execute()
    carregar.clear()
    return {"salvas": len(registros), "fora_da_dim": len(df) - len(registros)}


@st.cache_data(ttl=600, show_spinner=False)
def carregar() -> pd.DataFrame:
    linhas, pagina = [], 0
    try:
        while True:
            resp = (db.sb().table("dim_produto").select("id_produto, id_pai, proporcao").gt("proporcao", 0)
                    .range(pagina * 1000, pagina * 1000 + 999).execute())
            lote = resp.data or []
            linhas.extend(lote)
            if len(lote) < 1000:
                break
            pagina += 1
    except Exception:
        return pd.DataFrame(columns=["id_produto", "id_pai", "proporcao"])
    df = pd.DataFrame(linhas, columns=["id_produto", "id_pai", "proporcao"]).dropna()
    df = df[df["proporcao"] != 100]
    return df.astype({"id_produto": "int64", "id_pai": "int64", "proporcao": "float64"})
