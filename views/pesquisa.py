"""Pesquisa de Mercado (Market Metrics): o comprador consulta e extrai os preços do mercado.

Filtros como os da PriceMetrics (vários estados, comprador, departamento, categoria, cesta). Tudo sai da base que o
servidor já tem carregada (Competitividade Pricing GMAT + 1067 do dia): consultar e extrair não consome o Supabase.
"""
from __future__ import annotations

import hashlib

import streamlit as st
import streamlit.components.v1 as components

from core import auth
from core import mercado as mc
from ui import components as ui
from ui import theme

_MERCADO = components.declare_component("market_metrics_v2", path=ui.pasta_mercado())


def _tokens() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"


def _opcoes(df, coluna: str) -> list[str]:
    if coluna not in df:
        return []
    return sorted(x for x in df[coluna].astype(str).unique() if x and x.lower() not in ("nan", "none", "-"))


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            ".st-key-mk_topo{position:fixed !important;top:11px;right:168px;z-index:1000002;width:auto !important;gap:6px}"
            ".st-key-mk_topo [data-testid='stPopover'] button{height:38px;min-height:38px;border-radius:19px;padding:0 12px;"
            "background:var(--ps-surface);border:1px solid var(--ps-line)}</style>")
    try:
        with st.spinner("Lendo a base de pesquisa"):
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
    permitidos = auth.estados_permitidos()
    if permitidos is not None:
        ufs = [u for u in ufs if auth.sigla_estado(u) in permitidos]
    if not ufs:
        ui.vazio("Sem pesquisa nos seus estados", "A base não trouxe coletas dos estados em que você atua.")
        return
    f = st.session_state.setdefault("mk2_filtros", {"ufs": [ufs[0]], "comp": [], "deps": [], "cats": [], "cesta": False})
    f["ufs"] = [u for u in f["ufs"] if u in ufs] or [ufs[0]]
    base_uf = df[df["Estado"].astype(str).isin(ufs)]
    resumo = ", ".join(u.split(" - ")[0] for u in f["ufs"][:4]) + ("…" if len(f["ufs"]) > 4 else "")
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="mk_topo"):
        with st.popover(f"Filtros · {resumo}", icon=":material/filter_list:", help="Estados, comprador, departamento, categoria e cesta"):
            ui.gaveta_topo("Filtros", "Os mesmos recortes da PriceMetrics")
            with st.form("mk2_form", border=False):
                sel_ufs = st.multiselect("Estados", ufs, default=f["ufs"], placeholder="Escolha um ou mais estados")
                comp = st.multiselect("Comprador", _opcoes(base_uf, "Comprador"), default=[c for c in f["comp"] if c in _opcoes(base_uf, "Comprador")], placeholder="Todos")
                deps = st.multiselect("Departamento", _opcoes(base_uf, "Departamento"), default=[d for d in f["deps"] if d in _opcoes(base_uf, "Departamento")], placeholder="Todos")
                cats = st.multiselect("Categoria", _opcoes(base_uf, "Categoria"), default=[c for c in f["cats"] if c in _opcoes(base_uf, "Categoria")], placeholder="Todas")
                cesta = st.toggle("Só cesta", value=f["cesta"])
                a, b = st.columns(2)
                limpar = a.form_submit_button("Limpar", width="stretch", icon=":material/filter_alt_off:")
                if b.form_submit_button("Aplicar", type="primary", width="stretch", icon=":material/check:") or limpar:
                    st.session_state.mk2_filtros = ({"ufs": [ufs[0]], "comp": [], "deps": [], "cats": [], "cesta": False} if limpar else
                                                    {"ufs": sel_ufs or [ufs[0]], "comp": comp, "deps": deps, "cats": cats, "cesta": cesta})
                    st.session_state._fechar_mk = True
                    st.rerun()
    if st.session_state.pop("_fechar_mk", False):
        components.html("<script>const d=window.parent.document;setTimeout(()=>{d.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));"
                        "d.body.click();},150)</script>", height=0, width=0)
    versao = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    with st.spinner("Montando a pesquisa"):
        dados, info = mc.pacote_mercado_v2(versao, tuple(f["ufs"]), tuple(sorted(f["comp"])), tuple(sorted(f["deps"])),
                                           tuple(sorted(f["cats"])), bool(f["cesta"]), df, meta)
    chave = hashlib.md5(f"{versao}|{sorted(f.items())}".encode()).hexdigest()[:12]
    _MERCADO(dados=dados or None, vazio="Nenhuma coleta para os filtros escolhidos.", chave=chave, tokens=_tokens(),
             fonte=theme.FONTE_URL, key="market_metrics_v2", default=None)
