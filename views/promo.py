"""Pricing Promo: validação de encartes, explosão de clusters e exportação."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from core import db, promo_engine as pe
from ui import components as ui
from ui import theme

COLS = ['ARQUIVO ORIGEM', 'FILIAL ABREV', 'SEQPRODUTO', 'PRECO_NUM', 'INICIO', 'FIM', 'ALTERADO_MANUAL', 'Status Sistema']
NOMES = {'ARQUIVO ORIGEM': 'Campanha', 'FILIAL ABREV': 'Filial', 'SEQPRODUTO': 'Produto', 'PRECO_NUM': 'Preço',
         'INICIO': 'Início', 'FIM': 'Fim', 'ALTERADO_MANUAL': 'Editado', 'Status Sistema': 'Status'}


def _carregar(arquivos) -> None:
    nomes = sorted(f.name for f in arquivos)
    if st.session_state.get("promo_arquivos") == nomes:
        return
    with st.spinner("Lendo planilhas e abrindo clusters em filiais"):
        dfs, falhas = pe.ler_planilhas(arquivos)
        if falhas:
            st.warning(f"Não foi possível ler: {', '.join(falhas)}.", icon=":material/warning:")
        if not dfs:
            return
        try:
            res = pe.processar(dfs, db.clusters(), db.mapa_lojas())
        except pe.ArquivoSemDatas:
            st.error("As planilhas não têm as colunas INICIO e FIM. Se for um arquivo da pesquisa de mercado, "
                     "envie-o na página Pesquisa de Mercado.", icon=":material/error:")
            st.stop()
    st.session_state.df_promo_processado = res["df"]
    st.session_state.clusters_desconhecidos = res["clusters_fora"]
    st.session_state.campanhas_vencidas = res["vencidas"]
    st.session_state.promo_arquivos = nomes
    st.session_state.pending_promo_edit = False
    if res["vencidas"]:
        st.toast("Há campanhas com data de fim no passado.", icon=":material/event_busy:")


@st.dialog("Data alterada")
def _confirmar_datas(idx, campanha, n_ini, n_fim, n_preco) -> None:
    st.write(f"Você mudou o período de um item da campanha **{campanha}** para **{n_ini} a {n_fim}**.")
    st.write("Aplicar o novo período à campanha inteira ou só a este item?")

    def _salvar(mascara) -> None:
        df_mem = st.session_state.df_promo_processado
        df_mem.loc[idx, 'PRECO_NUM'] = n_preco
        df_mem.loc[mascara, 'INICIO'] = n_ini
        df_mem.loc[mascara, 'FIM'] = n_fim
        df_mem.loc[mascara, 'ALTERADO_MANUAL'] = 'SIM'
        df_mem['Status Sistema'] = pe.validar_status_conflitos(df_mem)
        st.session_state.df_promo_processado = df_mem
        st.session_state.pending_promo_edit = False
        st.rerun()

    c1, c2, c3 = st.columns(3)
    df_mem = st.session_state.df_promo_processado
    if c1.button("Campanha inteira", type="primary", width="stretch"):
        _salvar(df_mem['ARQUIVO ORIGEM'] == campanha)
    if c2.button("Só este item", width="stretch"):
        _salvar(df_mem.index == idx)
    if c3.button("Desfazer", width="stretch"):
        st.session_state.pending_promo_edit = False
        st.rerun()


def _clusters_fora() -> None:
    fora = st.session_state.get("clusters_desconhecidos", [])
    if not fora:
        return
    st.error(f"{len(fora)} cluster(s) não estão mapeados para filiais: {', '.join(map(str, fora[:8]))}"
             f"{'…' if len(fora) > 8 else ''}", icon=":material/link_off:")
    with st.expander("Pedir mapeamento de cluster"):
        with st.form("form_cluster", border=False):
            c1, c2 = st.columns(2)
            cluster = c1.selectbox("Cluster", fora)
            filial = c2.text_input("ID da filial", placeholder="Ex.: 544")
            if st.form_submit_button("Enviar para o administrador", type="primary"):
                if not filial.strip():
                    st.error("Informe o ID da filial.")
                else:
                    try:
                        db.solicitar_cluster(cluster, filial.strip(), st.session_state.usuario_logado)
                        st.success("Pedido enviado. Um administrador vai revisar o mapeamento.")
                    except Exception:
                        st.warning("A tabela solicitacoes_cluster ainda não existe no Supabase. Rode supabase/migrations.sql.")


def render() -> None:
    ui.cabecalho("Pricing Promo", "Valide encartes antes de subir: abre clusters em filiais, encontra preço divergente e período sobreposto.")

    arquivos = st.file_uploader("Planilhas de encarte (XLSX, XLS ou CSV com ponto e vírgula)", accept_multiple_files=True,
                                type=['xlsx', 'xls', 'csv'], key="promo_upload")
    if arquivos:
        _carregar(arquivos)

    df = st.session_state.get("df_promo_processado")
    if df is None or df.empty:
        ui.vazio("Envie as planilhas da campanha",
                 "Cada arquivo vira uma campanha. As colunas esperadas são CLUSTER/LOJA, SEQPRODUTO, PRECO_PROMOCIONAL (ou PRECO), INICIO e FIM.")
        return

    vencidas = st.session_state.get("campanhas_vencidas", [])
    if vencidas:
        st.warning(f"Campanhas com data de fim no passado: {', '.join(vencidas)}.", icon=":material/event_busy:")
    _clusters_fora()

    # ---------------------------------------------------------------- filtros
    ui.secao("Filtros")
    with st.container(border=True, key="psc_promo_filtros"):
        c1, c2, c3 = st.columns(3)
        campanhas = ["Todas"] + sorted(df['ARQUIVO ORIGEM'].dropna().unique().tolist())
        f_camp = c1.selectbox("Campanha", campanhas, key="promo_f_camp")
        base = df if f_camp == "Todas" else df[df['ARQUIVO ORIGEM'] == f_camp]
        f_filial = c2.multiselect("Filial", sorted(base['FILIAL ABREV'].dropna().astype(str).unique().tolist()), key="promo_f_filial",
                                  placeholder="Todas")
        f_prod = c3.text_input("Produto", placeholder="Código ou parte dele", key="promo_f_prod")
        c4, c5, c6 = st.columns(3)
        f_ini = c4.selectbox("Início", ["Todas"] + sorted(base['INICIO'].dropna().unique().tolist()), key="promo_f_ini")
        f_fim = c5.selectbox("Fim", ["Todas"] + sorted(base['FIM'].dropna().unique().tolist()), key="promo_f_fim")
        status = sorted(base['Status Sistema'].dropna().unique().tolist())
        f_status = c6.multiselect("Status", status, default=status, key=f"promo_f_status_{len(status)}")

    df_f = df.copy()
    if f_camp != "Todas": df_f = df_f[df_f['ARQUIVO ORIGEM'] == f_camp]
    if f_filial: df_f = df_f[df_f['FILIAL ABREV'].isin(f_filial)]
    if f_prod and 'SEQPRODUTO' in df_f.columns: df_f = df_f[df_f['SEQPRODUTO'].astype(str).str.contains(f_prod.strip(), regex=False)]
    if f_ini != "Todas": df_f = df_f[df_f['INICIO'] == f_ini]
    if f_fim != "Todas": df_f = df_f[df_f['FIM'] == f_fim]
    if f_status: df_f = df_f[df_f['Status Sistema'].isin(f_status)]

    total = len(df_f)
    criticos = int(df_f['Status Sistema'].str.contains('CRÍTICO').sum())
    erro_preco = int((df_f['Status Sistema'] == "CRÍTICO - ERRO DE PREÇO").sum())
    erro_data = int((df_f['Status Sistema'] == "CRÍTICO - CONFLITOS DE DATAS").sum())

    ui.secao("Validação")
    ui.etiquetas([
        ui.etiqueta("Linhas no filtro", total, tipo="numero", tom="primary"),
        ui.etiqueta("Válidas", total - criticos, tipo="numero", tom="ok"),
        ui.etiqueta("Preço divergente na mesma campanha", erro_preco, tipo="numero", tom="alert" if erro_preco else "neutro"),
        ui.etiqueta("Períodos sobrepostos", erro_data, tipo="numero", tom="alert" if erro_data else "neutro"),
    ])
    st.html("<div style='height:10px'></div>")
    ui.barra_validacao(total - criticos, criticos)

    # ---------------------------------------------------------------- grade
    ui.secao("Itens", "Edite preço e datas direto na grade. Mudar a data pergunta se vale para a campanha inteira.")
    if 'SEQPRODUTO' not in df_f.columns:
        st.error("As planilhas não têm a coluna SEQPRODUTO.")
        return
    df_vis = df_f[COLS].copy().rename(columns=NOMES)
    t = theme.tokens()

    def _estilo(row):
        if 'CRÍTICO' in str(row.get('Status', '')):
            return [f'background-color: {t["alert_soft"]}; color: {t["alert"]}; font-weight: 600;'] * len(row)
        if row.get('Editado', '') == 'SIM':
            return [f'background-color: {t["warn_soft"]};'] * len(row)
        return [''] * len(row)

    st.session_state.setdefault("pending_promo_edit", False)
    editado = st.data_editor(
        df_vis.style.apply(_estilo, axis=1),
        column_config={
            "Preço": st.column_config.NumberColumn("Preço", format="R$ %.2f", min_value=0.0, step=0.01),
            "Campanha": st.column_config.TextColumn(disabled=True),
            "Filial": st.column_config.TextColumn(disabled=True),
            "Produto": st.column_config.TextColumn(disabled=True),
            "Início": st.column_config.TextColumn("Início", help="dd/mm/aaaa"),
            "Fim": st.column_config.TextColumn("Fim", help="dd/mm/aaaa"),
            "Editado": st.column_config.TextColumn(disabled=True),
            "Status": st.column_config.TextColumn(disabled=True),
        },
        width="stretch", hide_index=True, key="promo_editor",
    )

    if not st.session_state.pending_promo_edit:
        d_preco = pe.linhas_diferentes(editado['Preço'], df_vis['Preço'])
        d_ini = pe.linhas_diferentes(editado['Início'], df_vis['Início'])
        d_fim = pe.linhas_diferentes(editado['Fim'], df_vis['Fim'])
        diff = d_preco | d_ini | d_fim
        if diff.any():
            idx = diff[diff].index[0]
            if d_ini.loc[idx] or d_fim.loc[idx]:
                st.session_state.pending_promo_edit = True
                st.session_state.promo_edit_data = {
                    'idx': idx, 'campanha': df_vis.loc[idx, 'Campanha'],
                    'ini': editado.loc[idx, 'Início'], 'fim': editado.loc[idx, 'Fim'], 'preco': editado.loc[idx, 'Preço'],
                }
                st.rerun()
            else:
                df_mem = st.session_state.df_promo_processado
                for i in diff[diff].index:
                    if d_preco.loc[i]:
                        df_mem.loc[i, 'PRECO_NUM'] = editado.loc[i, 'Preço']
                    df_mem.loc[i, 'ALTERADO_MANUAL'] = 'SIM'
                df_mem['Status Sistema'] = pe.validar_status_conflitos(df_mem)
                st.session_state.df_promo_processado = df_mem
                st.rerun()

    if st.session_state.pending_promo_edit:
        d = st.session_state.promo_edit_data
        _confirmar_datas(d['idx'], d['campanha'], d['ini'], d['fim'], d['preco'])

    # ---------------------------------------------------------------- exportação
    ui.secao("Exportar")
    with st.container(border=True, key="psc_promo_export"):
        operacao = st.segmented_control("Operação", ["Aplicar preço", "Cancelar preço"], default="Aplicar preço",
                                        required=True, key="promo_op")
        c1, c2 = st.columns(2)
        with c1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_vis.to_excel(writer, index=False)
            st.download_button("Baixar auditoria (XLSX)", data=buffer.getvalue(), width="stretch", icon=":material/download:",
                               file_name=f"Auditoria_{datetime.now():%d-%m-%Y}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with c2:
            if criticos > 0:
                st.button("Copiar padrão de importação", disabled=True, width="stretch", key="promo_copy_off")
                st.caption(f"Bloqueado: {criticos} item(ns) crítico(s) no filtro. Corrija ou filtre só os válidos.")
            elif total == 0:
                st.button("Copiar padrão de importação", disabled=True, width="stretch", key="promo_copy_vazio")
            else:
                ui.botao_copiar(pe.texto_importacao(df_f, operacao == "Aplicar preço"),
                                "Copiar padrão de importação", "Padrão copiado")
