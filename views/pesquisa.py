"""Pesquisa de Mercado (MarketMetrics): 30 dias de coletas da própria base, sem upload."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import mercado as mc
from ui import components as ui
from ui import theme

from ui.components import pasta_telas as _pasta_telas
RAIZ = Path(__file__).resolve().parent.parent
_MERCADO = components.declare_component("market_metrics", path=_pasta_telas())


def _tokens() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};" + theme.extra_componente()


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            ".st-key-mk_topo{position:fixed !important;top:11px;right:168px;z-index:1000002;width:auto !important;gap:6px}"
            ".st-key-mk_topo [data-testid='stPopover'] button{height:38px;min-height:38px;border-radius:19px;padding:0 12px;"
            "background:var(--ps-surface);border:1px solid var(--ps-line)}</style>")
    try:
        with st.spinner("Lendo os 30 dias de pesquisa da base"):
            fonte = mc.base_padrao()
    except Exception as exc:
        st.error(f"Não foi possível ler a base de pesquisa: {exc}", icon=":material/error:")
        return
    if fonte is None:
        ui.vazio("Base de pesquisa não encontrada", "Publique o relatório Competitividade Pricing GMAT na biblioteca: a pesquisa usa o histórico dele.")
        return
    df, meta, rel = fonte
    h = meta.get("hist") or {}
    ufs = [u for u in h.get("U", []) if u in set(df["Estado"].astype(str).unique())]
    if not ufs:
        ui.vazio("Sem histórico de pesquisa", "A base publicada não trouxe as coletas dos concorrentes.")
        return
    f = st.session_state.setdefault("mk_filtros", {"uf": ufs[0], "cesta": True, "deps": []})
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="mk_topo"):
        with st.popover(f"Filtros · {f['uf'].split(' - ')[0]}", icon=":material/filter_list:", help="Estado e recorte da pesquisa"):
            ui.gaveta_topo("Filtros", f"{f['uf']}{', só cesta' if f['cesta'] else ''}")
            with st.form("mk_form", border=False):
                uf = st.segmented_control("Estado", ufs, default=f["uf"] if f["uf"] in ufs else ufs[0], required=True)
                deps = st.multiselect("Departamento", sorted(df["Departamento"].astype(str).unique()), default=f["deps"], placeholder="Todos")
                cesta = st.toggle("Só cesta", value=f["cesta"])
                if st.form_submit_button("Aplicar", type="primary", width="stretch", icon=":material/check:"):
                    st.session_state.mk_filtros = {"uf": uf, "cesta": cesta, "deps": deps}
                    st.session_state._fechar_mk = True
                    st.rerun()
    if st.session_state.pop("_fechar_mk", False):
        components.html("<script>const d=window.parent.document;setTimeout(()=>{d.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));"
                        "d.body.click();},150)</script>", height=0, width=0)
    versao = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    with st.spinner("Montando o painel de mercado"):
        dados, n = mc.pacote_mercado(versao, f["uf"], f["cesta"], tuple(sorted(f["deps"])), df, meta)
    chave = hashlib.md5(f"{versao}|{f}".encode()).hexdigest()[:12]
    _MERCADO(app="market", dados=dados, chave=chave, tokens=_tokens(), fonte=theme.FONTE_URL, altura=900, key="market_metrics", default=None)
