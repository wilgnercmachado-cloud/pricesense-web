"""Início: painel de inteligência de mercado (cara de bolsa) com atalhos para as ferramentas e os relatórios."""
from __future__ import annotations

import hashlib
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import auth, mercado as mc, profimetrics as pf, reports, state
from ui import theme

RAIZ = Path(__file__).resolve().parent.parent
_HOME = components.declare_component("home_metrics", path=str(RAIZ / "ui" / "metrics_comp"))
DESCR = {"preco_bot": ("Preço Bot", "sell", "Cole preços, aplique a régua e gere a importação"),
         "promo": ("Metrics Promo", "campaign", "Valide encartes, conflitos e o calendário de campanhas"),
         "pesquisa": ("Pesquisa de Mercado", "query_stats", "30 dias de coletas, ranking e tendência por estado"),
         "regular": ("PriceMetrics", "price_change", "Precificação regular com Optimus, aceite e importação"),
         "biblioteca": ("Relatórios", "library_books", "Biblioteca de relatórios de mercado")}


def _tokens() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:1500px !important;padding:3.6rem 1rem 1rem 1rem !important}</style>")
    paginas = st.session_state.get("_pages", {})
    painel, base = None, ""
    try:
        with st.spinner("Atualizando o painel de mercado"):
            fonte = mc.base_padrao()
            if fonte:
                df, meta, rel = fonte
                regras, pf_meta = pf.carregar()
                versao = f"{rel.get('id')}:{rel.get('atualizado_em')}:{pf_meta.get('atualizado_em')}:{pf_meta.get('linhas')}:{(meta.get('p1067') or {}).get('em')}"
                painel = mc.painel_estados(versao, df, meta, regras)
                base = f"Base {rel.get('titulo')} de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}."
    except Exception:
        painel = None
    ferramentas = [[k, *DESCR[k][:1], DESCR[k][1], DESCR[k][2]] for k in ("regular", "promo", "pesquisa", "preco_bot", "biblioteca") if k in paginas]
    ferramentas = [[k, t, i, d] for k, t, i, d in ferramentas]
    try:
        rels = reports.visiveis(st.session_state.usuario_login, auth.eh_admin())[:6]
    except Exception:
        rels = []
    relatorios = [[r["id"], r.get("titulo") or "", str(r.get("categoria") or "")] for r in rels]
    chave = hashlib.md5(f"{base}|{len(relatorios)}|{len(ferramentas)}".encode()).hexdigest()[:10]
    ret = _HOME(app="home", chave=chave, tokens=_tokens(), fonte=theme.FONTE_URL, painel=painel or {"estados": [], "serie": {}, "dias": []},
                ferramentas=ferramentas, relatorios=relatorios, base=base, saudacao=f"Olá, {state.primeiro_nome()}", key="home_metrics", default=None)
    if isinstance(ret, dict) and ret.get("ts") != st.session_state.get("_home_ts"):
        st.session_state._home_ts = ret.get("ts")
        if ret.get("acao") == "ir" and ret.get("pagina") in paginas:
            st.switch_page(paginas[ret["pagina"]])
        if ret.get("acao") == "relatorio" and "biblioteca" in paginas:
            st.switch_page(paginas["biblioteca"], query_params={"r": ret.get("id")})
