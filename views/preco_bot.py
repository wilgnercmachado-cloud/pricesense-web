"""Preço Bot: geração do arquivo de importação de preços para o ERP."""
from __future__ import annotations

import io
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from core import db
from core import preco_bot as pb
from ui import components as ui


def _lojas() -> list[str]:
    estados = st.multiselect("Estado", db.estados(), placeholder="Escolha um ou mais estados", key="pb_estados")
    diretores = st.multiselect(
        "Diretor regional (opcional)", db.diretores(tuple(estados)), disabled=not estados,
        placeholder="Todos os diretores" if estados else "Escolha um estado primeiro", key="pb_diretores")
    opcoes = db.filiais(tuple(estados), tuple(diretores))
    c1, c2 = st.columns([1, 0.32], vertical_alignment="bottom")
    with c2:
        todas = st.toggle("Todas", disabled=not opcoes, key="pb_todas", help="Seleciona todas as filiais do filtro")
    with c1:
        filiais = st.multiselect(
            "Filiais", opcoes, default=opcoes if todas else None, disabled=not estados or todas,
            placeholder="Escolha as filiais" if estados else "Escolha um estado primeiro", key=f"pb_filiais_{todas}")
    return opcoes if todas else filiais


def render() -> None:
    ui.cabecalho("Preço Bot", "Cole os preços, aplique as regras de arredondamento e gere o arquivo de importação do ERP.")

    esq, dir_ = st.columns([1, 1], gap="medium")
    with esq, st.container(border=True, key="psc_pb_lojas"):
        ui.secao("Lojas")
        filiais = _lojas()
        if filiais:
            st.caption(f"{len(filiais)} filial(is) selecionada(s).")

    with dir_, st.container(border=True, key="psc_pb_campanha"):
        ui.secao("Campanha")
        formato = st.segmented_control("Formato da régua", ["PRICE", "COMERCIAL"], default="PRICE", required=True, key="pb_formato")
        midias = db.tipos_midia()
        if formato == "COMERCIAL":
            midias = [m for m in midias if m.split(" - ")[0].strip() not in ["1", "2", "10", "21"]]
        if not midias:
            st.warning("Não foi possível carregar os tipos de mídia. Verifique a tabela tipo_ofertas.", icon=":material/warning:")
        c1, c2 = st.columns(2)
        tipo_midia = c1.selectbox("Tipo de mídia", midias, key="pb_midia")
        tipo_op = c2.selectbox("Operação", ["1 - Aplicar Preço", "2 - Cancelar Preço"], key="pb_op")
        c3, c4 = st.columns(2)
        aplicar_similar = c3.selectbox("Aplicar similar", ["NAO", "SIM"], key="pb_similar")
        if formato == "COMERCIAL":
            somente_piso = c4.selectbox("Somente piso de loja", ["NAO", "SIM"], key="pb_piso")
        else:
            c4.selectbox("Somente piso de loja", ["NAO"], disabled=True, key="pb_piso_off", help="Disponível no formato COMERCIAL")
            somente_piso = "NAO"
        c5, c6 = st.columns(2)
        dt_inicio = c5.date_input("Início", value=datetime.now(), format="DD/MM/YYYY", key="pb_ini")
        dt_fim = c6.date_input("Fim", value=datetime.now() + timedelta(days=3), format="DD/MM/YYYY", key="pb_fim")

    id_classificacao = tipo_midia.split(" - ")[0].strip() if tipo_midia else ""
    cod_op = tipo_op.split(" - ")[0].strip()
    cancelamento = pb.eh_cancelamento(formato, id_classificacao, cod_op)

    with st.container(border=True, key="psc_pb_precos"):
        ui.secao("Preços",
                 "Cancelamento: cole só os códigos dos produtos, um por linha." if cancelamento else
                 "Uma linha por produto: código, preço de varejo e preço de atacado, separados por TAB. "
                 "Sem atacado, o varejo é repetido.")
        ui.habilitar_tab_em_textarea()
        texto = st.text_area("Preços colados", height=190, label_visibility="collapsed", key="pb_texto",
                             placeholder="12345\t9,93\t9,49\n67890\t24,10\t22,90")

        checagem = pb.validar_colagem(texto) if texto.strip() and not cancelamento else \
            {"erro_atacado": False, "alerta_margem": False, "itens_erro": [], "linhas": 0}
        if checagem["erro_atacado"]:
            st.error(f"Atacado maior que varejo em: {', '.join(checagem['itens_erro'])}. Corrija essas linhas para gerar.",
                     icon=":material/block:")
        confirmar = True
        if checagem["alerta_margem"] and not checagem["erro_atacado"]:
            st.warning("Há produtos com diferença de 10% ou mais entre varejo e atacado.", icon=":material/warning:")
            confirmar = st.checkbox("Conferi as diferenças e quero seguir.", key="pb_conf")

        pronto = bool(filiais) and bool(texto.strip()) and confirmar and not checagem["erro_atacado"]
        if not filiais:
            st.caption("Escolha ao menos uma filial para gerar.")
        if st.button("Gerar preços", type="primary", width="stretch", disabled=not pronto, icon=":material/bolt:"):
            with st.spinner("Aplicando regras de arredondamento"):
                dados, ignoradas = pb.gerar_importacao(texto, filiais, formato, id_classificacao, cod_op,
                                                       dt_inicio, dt_fim, aplicar_similar, somente_piso)
            st.session_state.pb_resultado = {"dados": dados, "ignoradas": ignoradas, "filiais": len(filiais),
                                             "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M")}

    res = st.session_state.get("pb_resultado")
    if not res:
        return
    ui.secao("Resultado", f"Gerado em {res['gerado_em']}.")
    if res["ignoradas"]:
        st.warning(f"{len(res['ignoradas'])} linha(s) não puderam ser lidas e ficaram de fora: "
                   f"{'; '.join(res['ignoradas'][:5])}", icon=":material/warning:")
    if not res["dados"]:
        ui.vazio("Nenhuma linha gerada", "Confira se os preços estão no formato código, varejo e atacado.")
        return

    df = pd.DataFrame(res["dados"])
    produtos = df["Código do Produto"].nunique()
    ui.etiquetas([
        ui.etiqueta("Linhas no arquivo", len(df), tipo="numero", tom="primary"),
        ui.etiqueta("Produtos", produtos, tipo="numero"),
        ui.etiqueta("Filiais", res["filiais"], tipo="numero"),
    ])
    st.html("<div style='height:10px'></div>")
    st.dataframe(df, width="stretch", hide_index=True, height=min(420, 38 + 35 * len(df)))

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Importacao")
    c1, c2, _ = st.columns([1, 1, 1.2])
    with c1:
        st.download_button("Baixar XLSX", data=buffer.getvalue(), type="primary", width="stretch", icon=":material/download:",
                           file_name=f"pricesense_importacao_{datetime.now():%d-%m-%Y}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with c2:
        ui.botao_copiar(df.to_csv(index=False, header=False, sep="\t"), "Copiar base bruta", "Base copiada")
