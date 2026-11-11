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


@st.cache_resource(show_spinner=False, max_entries=4, ttl=3600)
def _itens(chave: str, _df: pd.DataFrame, _regras: pd.DataFrame) -> pd.DataFrame:
    return rv.itens(_df, _regras)


_RELE_HTML = r"""<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">
<script>
/* revisão de margem: leva os pedidos de itens da tela para o Python e devolve os itens para a simulação na hora */
const enviar = (type, extra) => window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, extra || {}), '*');
enviar('streamlit:componentReady', { apiVersion: 1 }); enviar('streamlit:setFrameHeight', { height: 0 });
let ultimo = 0;
setInterval(() => { try { const r = window.parent.__psMgReq; if (r && r.ts > ultimo) { ultimo = r.ts; enviar('streamlit:setComponentValue', { value: r, dataType: 'json' }); } } catch (e) {} }, 400);
window.addEventListener('message', e => { const d = e.data; if (!d || d.type !== 'streamlit:render') return; const r = (d.args || {}).resposta;
  if (!r || !r.itens) return; try { const P = window.parent; P.__psMgResp = r; P.dispatchEvent(new P.CustomEvent('ps-mg')); } catch (e) {} });
</script></body></html>"""


def _rele():
    import tempfile
    from pathlib import Path as _P
    pasta = _P(tempfile.gettempdir()) / "pricesense_mg_rele"
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / "index.html"
    if not arq.exists() or arq.read_text(encoding="utf-8") != _RELE_HTML:
        arq.write_text(_RELE_HTML, encoding="utf-8")
    return components.declare_component("margem_rele", path=str(pasta))


try:
    _RELE = _rele()
except Exception:
    _RELE = None


@st.fragment(run_every="2s")
def _rele_itens(chave: str, recorte: pd.DataFrame, regras: pd.DataFrame) -> None:
    """Quando o usuário edita uma sugestão, a tela pede os itens (filial + produto) daquele produto para refazer a simulação."""
    if _RELE is None:
        return
    ss = st.session_state
    resp = ss.get("_mg_resp") if ss.get("_mg_resp_chave") == chave else None
    pedido = _RELE(resposta=resp, key="mg_rele", default=None)
    if isinstance(pedido, dict) and pedido.get("ts") != ss.get("_mg_req_ts") and pedido.get("produtos"):
        ss._mg_req_ts = pedido.get("ts")
        it = _itens(chave, recorte, regras)
        ss._mg_resp = {"ts": pedido["ts"], "itens": rv.itens_dos_produtos(it, list(pedido["produtos"])[:400])}
        ss._mg_resp_chave = chave
        st.rerun(scope="fragment")


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
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            "[data-testid='stMainBlockContainer'] [data-testid='stVerticalBlock']{gap:.4rem}"
            ".st-key-mg_topo{gap:8px}.st-key-mg_topo [data-testid='stElementContainer']{flex:1 1 0;min-width:0}</style>")
    # filtros: um, vários ou todos os estados; filiais; departamento; comprador; categoria; fornecedor
    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="mg_topo"):
        if "mg_ufs" not in ss:
            ss.mg_ufs = ufs[:1]
        sel_uf = st.multiselect("Estados", ufs, key="mg_ufs", placeholder="Todos os estados", label_visibility="collapsed")
        ufs_ok = sel_uf or ufs
        no_uf = df[sig.isin(ufs_ok)]
        fils = sorted(no_uf["Filial"].astype(str).unique(), key=lambda x: int(x.split(" - ")[0]) if x.split(" - ")[0].isdigit() else 0)
        sel_fil = st.multiselect("Filiais", fils, key="mg_fil", placeholder="Todas as filiais", label_visibility="collapsed")
        base_f = no_uf[no_uf["Filial"].astype(str).isin(sel_fil)] if sel_fil else no_uf
        opc = lambda col: sorted(base_f[col].astype(str).unique()) if col in base_f else []
        sel_dep = st.multiselect("Departamentos", opc("Departamento"), key="mg_dep", placeholder="Todos os departamentos", label_visibility="collapsed")
        sel_comp = st.multiselect("Compradores", opc("Comprador"), key="mg_comp", placeholder="Todos os compradores", label_visibility="collapsed")
        sel_cat = st.multiselect("Categorias", opc("Categoria"), key="mg_cat", placeholder="Todas as categorias", label_visibility="collapsed")
        sel_forn = st.multiselect("Fornecedores", opc("Grupo empresarial"), key="mg_forn", placeholder="Todos os fornecedores", label_visibility="collapsed")
    recorte = base_f
    for col, sel in (("Departamento", sel_dep), ("Comprador", sel_comp), ("Categoria", sel_cat), ("Grupo empresarial", sel_forn)):
        if sel and col in recorte:
            recorte = recorte[recorte[col].astype(str).isin(sel)]
    regras, pf_meta = pf.carregar()
    chave = json.dumps([str(rel.get("id")), str(rel.get("atualizado_em")), sorted(ufs_ok), sorted(sel_fil), sorted(sel_dep), sorted(sel_comp),
                        sorted(sel_cat), sorted(sel_forn), str(pf_meta.get("atualizado") if isinstance(pf_meta, dict) else "")])
    if recorte.empty:
        ui.vazio("Nada neste recorte", "Ajuste os filtros de estado, filial, comprador, categoria ou fornecedor.")
        return
    with st.spinner("Montando a revisão de margem"):
        pacote = _pacote(chave, recorte, regras)
    filiais_cod = sorted({int(x.split(" - ")[0]) for x in recorte["Filial"].astype(str).unique() if x.split(" - ")[0].isdigit()})
    todas_uf = sorted({int(x.split(" - ")[0]) for x in no_uf["Filial"].astype(str).unique() if x.split(" - ")[0].isdigit()})
    txt_uf = ", ".join(ufs_ok) if len(ufs_ok) <= 6 else f"{len(ufs_ok)} estados"
    escopo = f"{len(sel_fil)} filial(is) de {txt_uf}" if sel_fil else (f"estado {txt_uf} inteiro" if len(ufs_ok) == 1 else f"estados {txt_uf} inteiros")
    ret = _TELA(app="margem", chave=f"mg-{abs(hash(chave))}", tokens=_tokens(), fonte=theme.FONTE_URL, pacote=pacote, escopo=escopo,
                uf=txt_uf, tem_filiais=bool(sel_fil), atualizado=str(meta.get("atualizado") or ""), key="mg_tela", default=None)
    _rele_itens(chave, recorte, regras)
    if isinstance(ret, dict) and ret.get("ts") != ss.get("_mg_ts") and ret.get("acao") == "enviar":
        ss._mg_ts = ret.get("ts")
        itens = ret.get("itens") or []
        filiais = todas_uf if ret.get("escopo") == "estado" else filiais_cod
        txt = (f"estado {txt_uf} inteiro" if len(ufs_ok) == 1 else f"estados {txt_uf} inteiros") if ret.get("escopo") == "estado" else escopo
        try:
            rv.pedir(ss.get("usuario_login", ""), ss.get("usuario_logado") or ss.get("usuario_login", ""), itens, filiais, txt, "Revisão de margem", ret.get("obs") or "")
            st.toast(f"Pedido de nova margem enviado ({len(itens)} produto(s), {txt}). Só entra depois da aprovação do administrador.",
                     icon=":material/send:")
        except Exception as exc:
            st.toast(f"Não foi possível enviar: {exc}", icon=":material/error:")
