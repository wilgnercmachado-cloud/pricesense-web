"""Pesquisa de Mercado: leitura da rotina 1067 e inteligência competitiva."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from core import db
from core import market_engine as me
from ui import charts
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

    st.html("<div style='height:6px'></div>")
    ui.letreiro(me.itens_letreiro(df_f))

    k = me.indicadores(df_f)

    def _origem(o):
        return f"<b>{ui.esc(o[0][:34])}</b><br>{ui.esc(o[1])}" if o else ""

    ui.secao("Mercado no filtro", f"{ui.numero(len(df_f))} coletas válidas.")
    ui.etiquetas([
        ui.etiqueta("Moda varejo", k["moda_var"], tom="primary"),
        ui.etiqueta("Moda atacado", k["moda_atac"], tom="alert"),
        ui.etiqueta("Coletas no preço moda", k["qtd_moda"], tipo="numero"),
        ui.etiqueta("Menor varejo", k["min"], tom="promo", nota=_origem(k["min_origem"])),
        ui.etiqueta("Maior varejo", k["max"], nota=_origem(k["max_origem"])),
    ])

    t = theme.tokens()
    esq, dir_ = st.columns([2, 1], gap="medium")
    with esq, st.container(border=True, key="psc_pq_graf"):
        serie = me.serie_menor_preco(df_f)
        aba_conc, aba_pdv = st.tabs(["Concorrência", "Nosso PDV"])
        with aba_conc:
            st.plotly_chart(charts.menor_preco(serie, [(me.VAR, "Varejo concorrente", t["varejo"], -34, True),
                                                       (me.ATAC, "Atacado concorrente", t["atacado"], 34, False)]),
                            width="stretch", config={"displayModeBar": False}, key="pq_chart_conc")
        with aba_pdv:
            st.plotly_chart(charts.menor_preco(serie, [("Vlr. Varejo PDV", "Varejo PDV", t["varejo"], -34, False),
                                                       ("Vlr. Atacado PDV", "Atacado PDV", t["atacado"], 34, False)]),
                            width="stretch", config={"displayModeBar": False}, key="pq_chart_pdv")
        st.caption("Menor preço registrado em cada dia do período.")
    with dir_, st.container(border=True, key="psc_pq_media"):
        st.html("<div class='ps-sec' style='margin-top:.2rem'><h2>Preço médio por concorrente</h2></div>")
        medias = me.media_por_empresa(df_f)
        st.dataframe(medias, hide_index=True, width="stretch", height=min(380, 38 + 35 * len(medias)),
                     column_config={"Varejo": st.column_config.NumberColumn(format="R$ %.2f"),
                                    "Atacado": st.column_config.NumberColumn(format="R$ %.2f")})

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
