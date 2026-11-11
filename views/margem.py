"""Revisão de margem (Comercial e Pricing): categoria → produto, por estado ou filial, com sugestões e simulação contra a meta."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import auth, revisao as rv
from ui import components as ui
from ui import theme
from ui.components import pasta_telas as _pasta_telas

_TELA = components.declare_component("revisao_margem", path=_pasta_telas())


def _tokens() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};" + theme.extra_componente()


@st.cache_data(show_spinner=False, max_entries=6, ttl=3600)
def _pacote(chave: str, _df: pd.DataFrame, _regras: pd.DataFrame) -> dict:
    return rv.montar(_df, _regras)


def render() -> None:
    from core import profimetrics as pf
    from views.regular import base_atual
    ss = st.session_state
    fonte = base_atual()
    if fonte is None:
        ui.vazio("Base não encontrada", "Publique o relatório Competitividade Pricing GMAT na biblioteca de relatórios.")
        return
    df, meta, rel = fonte
    if "meta_venda" not in df:
        ui.vazio("Base sem meta de margem", "O relatório de competitividade publicado não trouxe o bloco de ritmo do mês (meta e mês anterior).")
        return
    sig = df["Estado"].astype(str).str.split(" - ").str[0].str.strip()
    ufs = sorted(sig.unique())
    permitidos = auth.estados_permitidos()
    if permitidos is not None:
        ufs = [u for u in ufs if u in permitidos]
    if not ufs:
        ui.vazio("Nenhum estado atribuído ao seu usuário", "Peça ao administrador para definir seus estados na Administração.")
        return
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="mg_topo"):
        uf = st.selectbox("Estado", ufs, key="mg_uf", label_visibility="collapsed")
        no_uf = df[sig == uf]
        fils = sorted(no_uf["Filial"].astype(str).unique(), key=lambda x: int(x.split(" - ")[0]) if x.split(" - ")[0].isdigit() else 0)
        sel_fil = st.multiselect("Filiais", fils, key="mg_fil", placeholder=f"Todas as filiais de {uf}", label_visibility="collapsed")
        deps = sorted(no_uf["Departamento"].astype(str).unique())
        sel_dep = st.multiselect("Departamentos", deps, key="mg_dep", placeholder="Todos os departamentos", label_visibility="collapsed")
    # filtros numa faixa própria, acima da tela (não disputam espaço com o menu do topo)
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            "[data-testid='stMainBlockContainer'] [data-testid='stVerticalBlock']{gap:.4rem}"
            ".st-key-mg_topo{gap:8px;max-width:980px}.st-key-mg_topo [data-testid='stElementContainer']{flex:1 1 0}</style>")
    recorte = no_uf
    if sel_fil:
        recorte = recorte[recorte["Filial"].astype(str).isin(sel_fil)]
    if sel_dep:
        recorte = recorte[recorte["Departamento"].astype(str).isin(sel_dep)]
    regras, pf_meta = pf.carregar()
    chave = json.dumps([str(rel.get("id")), str(rel.get("atualizado_em")), uf, sorted(sel_fil), sorted(sel_dep), str(pf_meta.get("atualizado") if isinstance(pf_meta, dict) else "")])
    with st.spinner("Montando a revisão de margem"):
        pacote = _pacote(chave, recorte, regras)
    filiais_cod = sorted({int(x.split(" - ")[0]) for x in recorte["Filial"].astype(str).unique() if x.split(" - ")[0].isdigit()})
    todas_uf = sorted({int(x.split(" - ")[0]) for x in no_uf["Filial"].astype(str).unique() if x.split(" - ")[0].isdigit()})
    escopo = f"{len(sel_fil)} filial(is) de {uf}" if sel_fil else f"estado {uf} inteiro"
    ret = _TELA(app="margem", chave=f"mg-{abs(hash(chave))}", tokens=_tokens(), fonte=theme.FONTE_URL, pacote=pacote, escopo=escopo,
                uf=uf, tem_filiais=bool(sel_fil), atualizado=str(meta.get("atualizado") or ""), key="mg_tela", default=None)
    if isinstance(ret, dict) and ret.get("ts") != ss.get("_mg_ts") and ret.get("acao") == "enviar":
        ss._mg_ts = ret.get("ts")
        itens = ret.get("itens") or []
        filiais = todas_uf if ret.get("escopo") == "estado" else filiais_cod
        txt = f"estado {uf} inteiro" if ret.get("escopo") == "estado" else escopo
        try:
            rv.pedir(ss.get("usuario_login", ""), ss.get("usuario_logado") or ss.get("usuario_login", ""), itens, filiais, txt, "Revisão de margem", ret.get("obs") or "")
            st.toast(f"Pedido de nova margem enviado ({len(itens)} produto(s), {txt}). Só entra depois da aprovação do administrador.",
                     icon=":material/send:")
        except Exception as exc:
            st.toast(f"Não foi possível enviar: {exc}", icon=":material/error:")
