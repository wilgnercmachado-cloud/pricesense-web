"""Pesquisa de Mercado: leitura da rotina 1067 e inteligência competitiva."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from core import db
from core import market_engine as me
from ui import terminal
from ui import components as ui
from ui import theme


def _processar(arquivo) -> None:
    if st.session_state.get("arquivo_pesquisa_nome") == arquivo.name:
        return
    with st.status("Processando a pesquisa", expanded=False) as status:
        try:
            status.update(label="Lendo o arquivo")
            df = me.padronizar_colunas(me.ler_arquivo(arquivo))
            df, stats = me.enriquecer(df, db.buscar_produtos, db.buscar_fornecedores,
                                      progresso=lambda msg: status.update(label=msg))
            status.update(label="Calculando margens e concorrentes")
            df = me.preparar(df, db.dim_empresa_conc())
        except Exception as exc:
            status.update(label="Não foi possível processar o arquivo", state="error", expanded=True)
            st.error(str(exc), icon=":material/error:")
            return
        status.update(label=f"Pesquisa pronta: {ui.numero(len(df))} coletas", state="complete")
    st.session_state.df_pesq_master = df
    st.session_state.arquivo_pesquisa_nome = arquivo.name
    st.session_state.pesq_enriquecimento = stats
    st.session_state.pop("pesq_extracao", None)
    st.session_state.reset_key += 1


def _filtros(df: pd.DataFrame) -> dict:
    rk = st.session_state.reset_key
    c1, c2, c3, c4 = st.columns(4)
    produto = c1.selectbox("Produto", ["Todos"] + sorted(df['PRODUTO'].dropna().unique().tolist()), key=f"pq_prod_{rk}")
    filial = c2.selectbox("Filial (PDV)", ["Todas"] + sorted(df['FILIAL'].dropna().unique().tolist()), key=f"pq_filial_{rk}")
    categoria = c3.selectbox("Categoria comercial", ["Todas"] + sorted(df['CATEGORIA_COMERCIAL'].dropna().unique().tolist()), key=f"pq_cat_{rk}")
    grupo = c4.selectbox("Grupo empresarial", ["Todos"] + sorted(df['GRUPO_EMPRESARIAL'].dropna().unique().tolist()), key=f"pq_grupo_{rk}")

    c5, c6, c7, c8 = st.columns([1.5, 1.5, 1.5, 0.7], vertical_alignment="bottom")
    base_conc = df[df['FILIAL'] == filial] if filial != "Todas" else df
    concorrentes = c5.multiselect("Concorrentes", sorted(base_conc['FILIALCONCORRENTE'].dropna().unique().tolist()),
                                  placeholder="Todos", key=f"pq_conc_{rk}")
    tipos = c6.multiselect("Tipo de preço", sorted(df['Tipo'].dropna().unique().tolist()), placeholder="Todos", key=f"pq_tipo_{rk}")
    datas = df['PESQUISADATA_DT'].dropna()
    dmin = datas.min().date() if not datas.empty else datetime.now().date()
    dmax = datas.max().date() if not datas.empty else datetime.now().date()
    periodo = c7.date_input("Período", [dmin, dmax], min_value=dmin, max_value=dmax, format="DD/MM/YYYY", key=f"pq_per_{rk}")
    if c8.button("Limpar", icon=":material/filter_alt_off:", width="stretch", help="Limpar todos os filtros"):
        st.session_state.reset_key += 1
        st.rerun()
    return {"produto": produto, "filial": filial, "categoria": categoria, "grupo": grupo,
            "concorrentes": concorrentes, "tipos": tipos, "periodo": periodo}


def render() -> None:
    ui.cabecalho("Pesquisa de Mercado", "Moda, menor preço e histórico da concorrência a partir da rotina 1067.")

    carregado = st.session_state.get("arquivo_pesquisa_nome")
    with st.expander(f"Arquivo: {carregado}" if carregado else "Enviar a extração da rotina 1067",
                     expanded=not carregado, icon=":material/upload_file:"):
        arquivo = st.file_uploader("Extração da rotina 1067, aba pesquisa extração (ZIP, CSV com | ou Excel)",
                                   type=['zip', 'csv', 'xlsx', 'xls'], key="pesq_upload")
    if arquivo:
        _processar(arquivo)

    df = st.session_state.get("df_pesq_master")
    if df is None or df.empty:
        ui.vazio("Envie a extração da pesquisa",
                 "Extraia a rotina 1067 com pelo menos 20 dias de período: com menos coletas, o preço moda fica pouco confiável. "
                 "Os produtos são cruzados com o cadastro para trazer categoria e grupo empresarial.")
        return

    stats = st.session_state.get("pesq_enriquecimento") or {}
    if stats.get("linhas"):
        pct = 100 * stats.get("classificadas", 0) / stats["linhas"]
        st.caption(f"{st.session_state.arquivo_pesquisa_nome}: {ui.numero(stats['linhas'])} linhas, "
                   f"{f'{pct:.0f}'}% com categoria e grupo do cadastro.")

    with st.container(border=True, key="psc_pq_filtros"):
        filtros = _filtros(df)
    df_f = me.aplicar_filtros(df, filtros)

    if df_f.empty:
        ui.vazio("Nenhuma coleta no filtro", "Amplie o período ou remova algum filtro. Preços zerados e fora da curva já são descartados automaticamente.")
        return

    k = me.indicadores(df_f)
    dados = me.serie_terminal(df_f)
    modas = me.modas_por_produto(df_f)
    um_produto = df_f['PRODUTO'].nunique() == 1
    ui.letreiro(me.itens_letreiro(df_f), referencias=modas)

    def _origem(o):
        return f"<b>{ui.esc(o[0][:30])}</b> em {ui.esc(o[1])}" if o else ""

    indice = me.indice_pdv(df_f, modas)
    menor_vs_moda = 100 * (k["min"] - k["moda_var"]) / k["moda_var"] if k["moda_var"] and um_produto else None
    serie_var = [v for v in dados["series"].get("var_conc", []) if v is not None]
    serie_atac = [v for v in dados["series"].get("atac_conc", []) if v is not None]

    ui.secao("Mercado no filtro", f"{ui.numero(len(df_f))} coletas válidas")
    cards = [
        ui.etiqueta("Moda varejo", k["moda_var"], tom="primary", nota=f"{ui.numero(k['qtd_moda'])} coletas nesse preço", serie=serie_var),
        ui.etiqueta("Moda atacado", k["moda_atac"], tom="alert", serie=serie_atac),
        ui.etiqueta("Menor varejo", k["min"], tom="ok", nota=_origem(k["min_origem"]), variacao=menor_vs_moda, inverter=True),
        ui.etiqueta("Maior varejo", k["max"], nota=_origem(k["max_origem"])),
    ]
    if indice is not None:
        cards.append(ui.etiqueta("Índice de preço do PDV", indice, tipo="indice", tom="ok" if indice <= 100 else "alert",
                                 nota="Nosso varejo sobre a moda de cada produto. Abaixo de 100, estamos mais baratos.",
                                 variacao=indice - 100, inverter=True))
    ui.etiquetas(cards)

    ui.secao("Evolução do menor preço", "Passe o mouse no gráfico para ver o ranking de concorrentes de cada dia.")
    with st.container(border=True, key="psc_pq_terminal"):
        terminal.grafico(dados, moda=(k["moda_var"] or None) if um_produto else None)

    ui.secao("Posição de cada concorrente", "Quanto cada um fica, em média, acima ou abaixo da moda de cada produto.")
    with st.container(border=True, key="psc_pq_media"):
        linhas = []
        for _, r in me.indice_por_concorrente(df_f, modas).iterrows():
            dif = float(r["Dif"])
            cor = "var(--ps-down)" if dif > 0 else "var(--ps-up)"
            texto_dif = f"{'+' if dif > 0 else ''}{dif:.1f}".replace(".", ",")
            extra = (f"<em style='color:{cor}'>{texto_dif}%</em>"
                     f"<em style='color:var(--ps-faint)'>{int(r['Produtos'])} prod.</em>")
            linhas.append((str(r["Concorrente"]), float(r["Varejo"]), extra))
        ui.ranking(linhas)

    # ---------------------------------------------------------------- extrações
    ui.secao("Extrações", "Gere a planilha de inteligência competitiva sobre as coletas do filtro.")
    assinatura = (tuple(sorted((k2, str(v)) for k2, v in filtros.items())), len(df_f))
    with st.container(border=True, key="psc_pq_ext"):
        modelo = st.segmented_control("Modelo", list(me.MODELOS), default="Preço moda", required=True, key="pq_modelo")
        st.caption(me.MODELOS[modelo])
        if st.button(f"Gerar {modelo.lower()}", type="primary", icon=":material/table_view:", key="pq_gerar"):
            with st.spinner("Calculando"):
                tabela, msg = me.extrair(modelo, df_f)
            st.session_state.pesq_extracao = {"modelo": modelo, "tabela": tabela, "msg": msg, "assinatura": assinatura}

        ext = st.session_state.get("pesq_extracao")
        if ext and ext["assinatura"] == assinatura and ext["modelo"] == modelo:
            if ext["tabela"] is None:
                st.warning(ext["msg"], icon=":material/warning:")
            else:
                tabela = ext["tabela"]
                moeda = {c: st.column_config.NumberColumn(format="R$ %.2f") for c in tabela.columns
                         if any(k in c for k in ("Varejo", "Atacado", "Custo"))}
                st.dataframe(tabela, width="stretch", hide_index=True, height=min(460, 38 + 35 * len(tabela)), column_config=moeda)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as w:
                    tabela.to_excel(w, index=False)
                nome = modelo.replace(" ", "")
                st.download_button(f"Baixar {modelo.lower()} (XLSX)", data=buffer.getvalue(), icon=":material/download:",
                                   file_name=f"PriceSense_{nome}_{datetime.now():%d-%m-%Y}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif ext and ext["assinatura"] != assinatura:
            st.caption("Os filtros mudaram desde a última extração. Gere de novo para atualizar.")
