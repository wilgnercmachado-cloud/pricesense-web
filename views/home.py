"""Página inicial: atalhos para as ferramentas e últimos relatórios."""
from __future__ import annotations

import streamlit as st

from core import auth, db, reports, state
from ui import components as ui
from ui import theme

FERRAMENTAS = [
    ("pesquisa", "Pesquisa de Mercado", "Moda, menor preço e histórico da concorrência a partir da rotina 1067.", "query_stats"),
    ("promo", "Pricing Promo", "Valida encartes, abre clusters em filiais e aponta conflitos de preço e de data.", "campaign"),
    ("preco_bot", "Preço Bot", "Arredonda preços pelas regras de gôndola e monta o arquivo de importação do ERP.", "sell"),
    ("regular", "Pricing Regular", "Análises competitivas de preço regular. Em migração para a nova plataforma.", "price_change"),
]


def _resumo_pesquisa() -> None:
    """Se uma pesquisa foi carregada nesta sessão, mostra o retrato do mercado logo no início."""
    df = st.session_state.get("df_pesq_master")
    if df is None or df.empty:
        return
    from core import market_engine as me
    base = me.filtro_qualidade(df)
    if base.empty:
        return
    k = me.indicadores(base)
    serie = base.groupby("PESQUISADATA_DT")[me.VAR].min().sort_index().tolist()
    ui.secao("Mercado na última pesquisa", st.session_state.get("arquivo_pesquisa_nome", ""))
    ui.etiquetas([
        ui.etiqueta("Moda varejo", k["moda_var"], tom="primary", serie=serie),
        ui.etiqueta("Moda atacado", k["moda_atac"], tom="alert"),
        ui.etiqueta("Menor varejo", k["min"], tom="ok"),
        ui.etiqueta("Coletas", len(base), tipo="numero"),
    ])


def render() -> None:
    ui.cabecalho(f"Olá, {state.primeiro_nome()}",
                 extra_html=f"<p class='ps-clock'><i class='ps-live'></i>{ui.data_extenso()}</p>")
    _resumo_pesquisa()
    paginas = state.paginas()

    disponiveis = [f for f in FERRAMENTAS if f[0] in paginas]
    ui.secao("Ferramentas")
    if not disponiveis:
        ui.vazio("Nenhuma ferramenta liberada", "Peça a um administrador para liberar as ferramentas que você usa no dia a dia.")
    else:
        colunas = st.columns(min(len(disponiveis), 4))
        for col, (chave, nome, desc, icone) in zip(colunas, disponiveis):
            with col, st.container(border=True, key=f"psc_tool_{chave}"):
                st.html(f"<div class='ps-tool'><div class='ic'><span class='ms'>{icone}</span></div>"
                        f"<h3>{ui.esc(nome)}</h3><p>{ui.esc(desc)}</p></div>")
                st.page_link(paginas[chave], label="Abrir", icon=":material/arrow_outward:")

    esq, dir_ = st.columns([1.6, 1], gap="large")
    with esq:
        ui.secao("Relatórios recentes", "Os últimos publicados para você.")
        lista = reports.visiveis(st.session_state.usuario_login, auth.eh_admin())[:6]
        if not lista:
            texto = ("Publique o primeiro relatório em Relatórios > Publicar."
                     if auth.pode_publicar() else "Quando a equipe publicar um relatório, ele aparece aqui.")
            ui.vazio("Nenhum relatório ainda", texto)
        else:
            with st.container(border=True, key="psc_recentes"):
                for rel in lista:
                    c1, c2 = st.columns([1, 0.22], vertical_alignment="center")
                    cor = theme.cor_categoria(rel.get("categoria") or "Geral")
                    c1.html(f"<div class='ps-list-row'><i style='background:{cor}'></i>"
                            f"<div><b>{ui.esc(rel.get('titulo', ''))}</b><br><span>{ui.esc(rel.get('categoria') or 'Geral')}, "
                            f"publicado em {ui.data_curta(rel.get('criado_em'))}</span></div><span></span></div>")
                    if c2.button("Abrir", key=f"home_rel_{rel['id']}", width="stretch", type="tertiary", icon=":material/open_in_new:"):
                        st.switch_page(paginas["biblioteca"], query_params={"r": rel["id"]})

    with dir_:
        if auth.eh_admin():
            ui.secao("Administração")
            try:
                pendentes = sum(1 for u in db.listar_usuarios() if u.get("status") == "Pendente")
            except Exception:
                pendentes = 0
            clusters = len(db.listar_solicitacoes_cluster())
            ui.etiquetas([
                ui.etiqueta("Acessos aguardando aprovação", pendentes, tipo="numero", tom="promo" if pendentes else "neutro"),
                ui.etiqueta("Clusters para mapear", clusters, tipo="numero", tom="alert" if clusters else "neutro"),
            ])
            st.page_link(paginas["admin"], label="Ir para Administração", icon=":material/admin_panel_settings:")
        else:
            ui.secao("Seu acesso")
            perms = st.session_state.get("permissoes", [])
            chips = "".join(f"<span class='ps-chip'>{ui.esc(p)}</span> " for p in perms) or "<span class='ps-chip'>Somente relatórios</span>"
            st.html(f"<div style='display:flex;flex-wrap:wrap;gap:8px'>{chips}</div>")
            st.caption("Precisa de outra ferramenta? Fale com um administrador.")
