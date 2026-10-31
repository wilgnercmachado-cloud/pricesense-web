"""Regras de margem do Profimetrics (objetiva, mínima, máxima e base de redução do atacado).

A planilha "Detalhes Produtos" vem sempre no mesmo formato. As regras ficam salvas no Supabase
Storage num único arquivo; cada novo envio é mesclado pela chave (produto, zona de preço):
o que vier no arquivo novo substitui o que existia, o resto é mantido. Nunca há duas regras
para o mesmo produto na mesma zona.
"""
from __future__ import annotations

import io
import re
import unicodedata
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import streamlit as st

from core import db

CAMINHO = "config/profimetrics.csv.gz"
BUCKET = "relatorios"
COLUNAS = {"produto": "#produto", "zona": "# zona de preco", "zona_nome": "zona de preco",
           "mrg_obj": "mrg objetivo (%)", "mrg_min": "margem minima (%)", "mrg_max": "margem maxima (%)", "merch": "merch l7"}


class ErroProfimetrics(ValueError):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.strip().lower())


def ler_planilha(arquivo) -> pd.DataFrame:
    bruto = None
    for motor in ("calamine", "openpyxl"):          # calamine lê a planilha de ~180 mil linhas 4x mais rápido
        try:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            bruto = pd.read_excel(arquivo, sheet_name=0, engine=motor)
            break
        except ImportError:
            continue
        except Exception as exc:
            raise ErroProfimetrics(f"Não foi possível ler a planilha: {exc}") from exc
    if bruto is None:
        raise ErroProfimetrics("Não foi possível ler a planilha.")
    mapa = {_norm(c): c for c in bruto.columns}
    faltando = [alvo for alvo in COLUNAS.values() if alvo not in mapa]
    if faltando:
        raise ErroProfimetrics("A planilha não está no formato do Profimetrics. Faltam as colunas: " + ", ".join(faltando))
    df = pd.DataFrame({k: bruto[mapa[v]] for k, v in COLUNAS.items()})
    df["produto"] = pd.to_numeric(df["produto"], errors="coerce")
    df["zona"] = pd.to_numeric(df["zona"], errors="coerce")
    for c in ("mrg_obj", "mrg_min", "mrg_max", "merch"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["produto", "zona"])
    df["produto"] = df["produto"].astype(np.int64)
    df["zona"] = df["zona"].astype(np.int64)
    df["zona_nome"] = df["zona_nome"].astype(str).str.strip()
    return df.drop_duplicates(["produto", "zona"], keep="last").reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner=False)
def carregar(_versao: str = "") -> tuple[pd.DataFrame, dict]:
    """Regras salvas (vazio se ainda não houver)."""
    try:
        bruto = db.sb().storage.from_(BUCKET).download(CAMINHO)
    except Exception:
        return pd.DataFrame(columns=list(COLUNAS) + ["atualizado_em"]), {}
    df = pd.read_csv(io.BytesIO(bruto), compression="gzip", sep=";", dtype={"zona_nome": str})
    meta = {"linhas": len(df), "zonas": int(df["zona"].nunique()), "produtos": int(df["produto"].nunique()),
            "atualizado_em": str(df["atualizado_em"].max()) if "atualizado_em" in df and len(df) else ""}
    return df, meta


def salvar(novo: pd.DataFrame, autor: str) -> dict:
    """Mescla com as regras salvas (o arquivo novo prevalece) e grava no Storage."""
    atual, _ = carregar()
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    novo = novo.assign(atualizado_em=agora, atualizado_por=autor)
    chaves_atual = set(zip(atual["produto"], atual["zona"])) if len(atual) else set()
    chaves_novo = set(zip(novo["produto"], novo["zona"]))
    junto = pd.concat([atual, novo], ignore_index=True).drop_duplicates(["produto", "zona"], keep="last")
    conteudo = junto.to_csv(sep=";", index=False).encode("utf-8")
    import gzip
    db.sb().storage.from_(BUCKET).upload(CAMINHO, gzip.compress(conteudo, 6),
                                         {"content-type": "application/gzip", "upsert": "true", "cache-control": "60"})
    carregar.clear()
    return {"total": len(junto), "novas": len(chaves_novo - chaves_atual), "substituidas": len(chaves_novo & chaves_atual),
            "mantidas": len(chaves_atual - chaves_novo)}


# ---------------------------------------------------------------- loja x zona
def _inteiro(v) -> int | None:
    m = re.match(r"\s*(\d+)", str(v))
    return int(m.group(1)) if m else None


@st.cache_data(ttl=3600, show_spinner=False)
def mapa_filial_zona(zonas: tuple[tuple[int, str], ...]) -> dict[int, int]:
    """Filial -> zona de preço. Usa a tabela `filiais` do Supabase; completa pelo código da filial no nome da zona."""
    mapa: dict[int, int] = {}
    try:
        linhas = db.sb().table("filiais").select("*").execute().data or []
    except Exception:
        linhas = []
    if linhas:
        cols = list(linhas[0])
        zc = next((c for c in cols if "zona" in _norm(c) and ("id" in _norm(c) or "#" in c or "cod" in _norm(c))), None) \
            or next((c for c in cols if "zona" in _norm(c)), None)
        fc = next((c for c in cols if ("filial" in _norm(c) or "loja" in _norm(c)) and ("id" in _norm(c) or "cod" in _norm(c))), None) \
            or next((c for c in cols if "filial" in _norm(c) or "loja" in _norm(c)), None)
        if zc and fc:
            for r in linhas:
                f, z = _inteiro(r.get(fc)), _inteiro(r.get(zc))
                if f is not None and z is not None:
                    mapa[f] = z
    for zona, nome in zonas:                # complemento: "BA - MIX 286 VT DA CONQUISTA" -> filial 286
        for n in re.findall(r"\d{2,4}", nome):
            mapa.setdefault(int(n), int(zona))
    return mapa


def regras_por_item(filial_cod: pd.Series, produto_cod: pd.Series, regras: pd.DataFrame) -> pd.DataFrame:
    """Margens e base de redução para cada linha (filial, produto). NaN onde não houver regra."""
    vazio = pd.DataFrame({c: np.full(len(filial_cod), np.nan) for c in ("mrg_obj", "mrg_min", "mrg_max", "merch")}, index=filial_cod.index)
    if regras is None or regras.empty:
        return vazio
    zonas = tuple(sorted(set(zip(regras["zona"].astype(int), regras["zona_nome"].astype(str)))))
    mapa = mapa_filial_zona(zonas)
    zona = filial_cod.map(lambda f: mapa.get(int(f)) if str(f).isdigit() else None)
    chave = pd.DataFrame({"zona": zona, "produto": pd.to_numeric(produto_cod, errors="coerce")}, index=filial_cod.index)
    r = regras.drop_duplicates(["produto", "zona"], keep="last").set_index(["zona", "produto"])[["mrg_obj", "mrg_min", "mrg_max", "merch"]]
    idx = pd.MultiIndex.from_arrays([chave["zona"].astype("float").astype("Int64"), chave["produto"].astype("Int64")])
    out = r.reindex(idx)
    out.index = filial_cod.index
    out.loc[out["mrg_max"] <= 0, "mrg_max"] = np.nan        # margem máxima zerada não vale como teto
    return out
