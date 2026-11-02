"""Preço Bot (PriceBot): cola os preços, aplica a régua da companhia e gera a importação do ERP, tudo no navegador."""
from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import db
from ui import theme

RAIZ = Path(__file__).resolve().parent.parent
_BOT = components.declare_component("price_bot", path=str(RAIZ / "ui" / "metrics_comp"))


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}</style>")
    lojas = db.lojas_completas()
    midias = db.tipos_midia()
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    tokens = "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"
    chave = hashlib.md5((str(len(lojas)) + "|".join(midias)).encode()).hexdigest()[:10]
    _BOT(app="bot", chave=chave, lojas=[list(l) for l in lojas], midias=midias, tokens=tokens, fonte=theme.FONTE_URL,
         usuario=st.session_state.get("usuario_login", ""), altura=900, key="price_bot", default=None)
