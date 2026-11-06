"""Formação do novo preço por usuário: formato (Mercado − 0,01 ou Curva de venda), percentuais por curva e delta seguro.

Os parâmetros valem por estado inteiro ou por filiais de um estado (a filial tem prioridade sobre o estado).
Administrador grava direto; os demais usuários enviam o pedido e o administrador aprova.
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import streamlit as st

from core import db

TABELA = "parametros_preco"
PADRAO = {"curva_a": 100.0, "curva_b": 100.0, "curva_c": 100.0, "delta_acima": 25.0, "delta_abaixo": 15.0}
CAMPOS = list(PADRAO)


@st.cache_data(ttl=300, show_spinner=False)
def carregar(usuario: str) -> pd.DataFrame:
    try:
        d = db.sb().table(TABELA).select("*").eq("usuario", usuario).execute().data or []
    except Exception:
        d = []
    return pd.DataFrame(d, columns=["usuario", "estado", "filial", *CAMPOS, "atualizado_em", "atualizado_por"])


def salvar(usuario: str, estado: str, filiais: list[str], valores: dict, por: str) -> int:
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    alvos = filiais or [""]                                    # vazio = o estado inteiro
    linhas = [{"usuario": usuario, "estado": estado, "filial": str(f), **{k: float(valores[k]) for k in CAMPOS},
               "atualizado_em": agora, "atualizado_por": por} for f in alvos]
    db.sb().table(TABELA).upsert(linhas, on_conflict="usuario,estado,filial").execute()
    carregar.clear()
    return len(linhas)


def remover(usuario: str, estado: str, filial: str) -> None:
    db.sb().table(TABELA).delete().eq("usuario", usuario).eq("estado", estado).eq("filial", filial).execute()
    carregar.clear()


def pedir(usuario: str, estado: str, filiais: list[str], valores: dict) -> None:
    from core import aprovacoes as ap
    corpo = json.dumps({"usuario": usuario, "estado": estado, "filiais": filiais, "valores": valores}).encode()
    resumo = {"estado": estado, "filiais": len(filiais) or "todas", **{k: valores[k] for k in CAMPOS}}
    ap.enviar("parametros", usuario, f"Formação de preço {estado}", corpo, resumo)


def aplicar_pedido(conteudo: bytes, admin: str) -> str:
    p = json.loads(conteudo)
    n = salvar(p["usuario"], p["estado"], p.get("filiais") or [], p["valores"], admin)
    return f"{n} escopo(s) de {p['estado']} para {p['usuario']}"


def por_linha(b: pd.DataFrame, params: pd.DataFrame) -> dict:
    """Parâmetros de cada linha da mesa: filial > estado > padrão. Devolve o % da curva da linha (None sem parâmetro) e os deltas."""
    n = len(b)
    if not n:
        return {"cp": [], "dla": [], "dlb": []}
    est = b["Estado"].astype(str).str.split(" - ").str[0].str.strip().to_numpy()
    fil = b["Filial"].astype(str).str.split(" - ").str[0].str.strip().to_numpy()
    curva = b["Curva"].astype(str).to_numpy() if "Curva" in b else np.array(["C"] * n)
    cp = np.full(n, np.nan); dla = np.full(n, PADRAO["delta_acima"]); dlb = np.full(n, PADRAO["delta_abaixo"])
    if params is not None and len(params):
        for nivel in ("estado", "filial"):                    # estado primeiro; a filial sobrescreve
            sub = params[(params["filial"].astype(str) == "") if nivel == "estado" else (params["filial"].astype(str) != "")]
            for _, r in sub.iterrows():
                m = (est == str(r["estado"])) if nivel == "estado" else ((est == str(r["estado"])) & (fil == str(r["filial"])))
                if not m.any():
                    continue
                pct = np.where(curva == "A", r["curva_a"], np.where(curva == "B", r["curva_b"], r["curva_c"]))
                cp[m] = pct[m]; dla[m] = float(r["delta_acima"]); dlb[m] = float(r["delta_abaixo"])
    r2 = lambda a: [round(float(x), 2) if x == x else None for x in a]
    return {"cp": r2(cp), "dla": r2(dla), "dlb": r2(dlb)}
