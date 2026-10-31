"""Pricing Regular: motor de precificação sobre a pesquisa de mercado."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import market_engine as me
from core import pricing_engine as pe
from ui import components as ui
from ui import theme

COR_ACAO = {"Subir": "up", "Baixar": "down", "Manter": "faint"}


def _fonte() -> pd.DataFrame | None:
    df = st.session_state.get("df_pesq_master")
    if df is not None and not df.empty:
        st.caption(f"Usando a pesquisa {st.session_state.get('arquivo_pesquisa_nome', '')} "
                   f"({ui.numero(len(df))} coletas). Para trocar, envie outra extração na Pesquisa de Mercado.")
        return df
    from views.pesquisa import _processar
    arquivo = st.file_uploader("Extração da rotina 1067 (ZIP, CSV com | ou Excel)", type=['zip', 'csv', 'xlsx', 'xls'], key="reg_upload")
    if arquivo:
        _processar(arquivo)
        st.rerun()
    ui.vazio("Envie a pesquisa de mercado",
             "O motor usa a extração da rotina 1067: preço atual do PDV, custo, moda e menor preço da concorrência. "
             "Se você já carregou a pesquisa na página Pesquisa de Mercado, ela é usada aqui automaticamente.")
    return None


def _matriz(res: pd.DataFrame, margem_min: float) -> go.Figure:
    t = theme.tokens()
    fig = go.Figure()
    for acao, chave in COR_ACAO.items():
        d = res[res['Ação'] == acao]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d['Índice atual'], y=d['Margem atual %'], mode='markers', name=acao,
            marker=dict(size=11, color=t[chave], opacity=.85, line=dict(width=1, color=t['surface_solid'])),
            customdata=d[['Produto', 'Filial', 'Varejo atual', 'Varejo sugerido']].values,
            hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>Índice %{x:.1f} | Margem %{y:.1f}%<br>"
                          "R$ %{customdata[2]:,.2f} para R$ %{customdata[3]:,.2f}<extra></extra>"))
    fig.add_vline(x=100, line=dict(color=t['faint'], dash='dot', width=1))
    fig.add_hline(y=margem_min, line=dict(color=t['amber'], dash='dot', width=1))
    for x, y, txt in [(.02, .98, "Barato e margem alta: espaço para subir"), (.98, .98, "Caro e margem alta: baixar"),
                      (.02, .04, "Barato e margem baixa: subir com cuidado"), (.98, .04, "Caro e margem baixa: rever custo")]:
        fig.add_annotation(xref="paper", yref="paper", x=x, y=y, text=txt, showarrow=False,
                           xanchor="left" if x < .5 else "right", font=dict(size=11, color=t['faint']))
    layout = theme.plotly_layout(380)
    layout.update(hovermode="closest", legend=dict(orientation="h", y=1.08, x=0, font=dict(color=t['ink'])),
                  xaxis=dict(title="Índice de preço (100 = moda do mercado)", gridcolor=t['line_hex'], zeroline=False, color=t['muted']),
                  yaxis=dict(title="Margem atual (%)", gridcolor=t['line_hex'], zeroline=False, color=t['muted']),
                  hoverlabel=dict(bgcolor=t['surface_solid'], bordercolor=t['line_hex'], font=dict(color=t['ink'])))
    fig.update_layout(**layout)
    return fig


def render() -> None:
    ui.cabecalho("Pricing Regular", "Motor de precificação: cruza preço atual, custo e mercado e sugere o novo preço já nas regras de gôndola.")
    df = _fonte()
    if df is None:
        return
    base_df = me.filtro_qualidade(df)

    with st.container(border=True, key="psc_reg_filtros"):
        c1, c2, c3, c4 = st.columns(4)
        filial = c1.selectbox("Filial", ["Todas"] + sorted(base_df['FILIAL'].dropna().unique()), key="reg_filial")
        cat = c2.selectbox("Categoria", ["Todas"] + sorted(base_df['CATEGORIA_COMERCIAL'].dropna().unique()), key="reg_cat")
        grupo = c3.selectbox("Grupo empresarial", ["Todos"] + sorted(base_df['GRUPO_EMPRESARIAL'].dropna().unique()), key="reg_grupo")
        busca = c4.text_input("Produto", placeholder="Código ou nome", key="reg_busca")
    f = base_df
    if filial != "Todas": f = f[f['FILIAL'] == filial]
    if cat != "Todas": f = f[f['CATEGORIA_COMERCIAL'] == cat]
    if grupo != "Todos": f = f[f['GRUPO_EMPRESARIAL'] == grupo]
    if busca.strip(): f = f[f['PRODUTO'].astype(str).str.contains(busca.strip(), case=False, regex=False)]

    base = pe.base_precificacao(f) if not f.empty else pd.DataFrame()
    if base.empty:
        ui.vazio("Nenhum produto com preço do PDV no filtro", "Amplie os filtros ou confira se a extração traz Vlr. Varejo PDV e CustoMedio.")
        return

    ui.secao("Estratégia", "Defina a regra; o motor respeita a margem mínima e o limite de variação de cada rodada.")
    with st.container(border=True, key="psc_reg_estrategia"):
        estrategia = st.segmented_control("Estratégia", list(pe.ESTRATEGIAS), default="Seguir a moda", required=True, key="reg_estr")
        st.caption(pe.ESTRATEGIAS[estrategia])
        c1, c2, c3, c4 = st.columns(4)
        padrao = 97 if estrategia == "Abaixo da moda" else 100
        indice = c1.slider("Índice alvo", 85, 115, padrao, key=f"reg_ind_{estrategia}", help="100 = igual à referência; 97 = 3% abaixo.")
        margem_min = c2.slider("Margem mínima (%)", 0, 50, 15, key="reg_mmin")
        var_max = c3.slider("Variação máxima por rodada (%)", 1, 30, 10, key="reg_vmax")
        gap = c4.slider("Atacado abaixo do varejo (%)", 0, 20, 5, key="reg_gap", help="Usado quando o mercado não informa a relação atacado/varejo.")

    res = pe.precificar(base, estrategia, indice, margem_min, var_max, gap)
    k = pe.impacto(res)
    fmt = lambda v: f"{v:.1f}".replace(".", ",") if v is not None else "-"
    ui.secao("Impacto da rodada", f"{ui.numero(k['itens'])} itens precificados")
    ui.etiquetas([
        ui.etiqueta("Sobem", k["sobem"], tipo="numero", tom="ok"),
        ui.etiqueta("Baixam", k["descem"], tipo="numero", tom="alert"),
        ui.etiqueta("Margem média", k["margem_nova"] or 0, tipo="pct", tom="primary",
                    nota=f"Hoje {fmt(k['margem_atual'])}%",
                    variacao=(k["margem_nova"] - k["margem_atual"]) if k["margem_nova"] is not None and k["margem_atual"] is not None else None),
        ui.etiqueta("Índice de preço", k["indice_novo"] or 0, tipo="indice", tom="promo", nota=f"Hoje {fmt(k['indice_atual'])}",
                    variacao=(k["indice_novo"] - k["indice_atual"]) if k["indice_novo"] and k["indice_atual"] else None, inverter=True),
        ui.etiqueta("Travados pela regra", k["travados"], tipo="numero", nota="Margem mínima ou limite de variação"),
    ])

    ui.secao("Matriz de oportunidade", "Cada ponto é um produto: quanto ele está caro em relação ao mercado e quanto ele rende.")
    with st.container(border=True, key="psc_reg_matriz"):
        st.plotly_chart(_matriz(res, margem_min), width="stretch", config={"displayModeBar": False}, key="reg_matriz")

    ui.secao("Preços sugeridos", "Ajuste o varejo e o atacado final direto na grade antes de exportar.")
    res["Varejo final"], res["Atacado final"] = res["Varejo sugerido"], res["Atacado sugerido"]
    moeda = st.column_config.NumberColumn(format="R$ %.2f")
    pct = st.column_config.NumberColumn(format="%.1f%%")
    cols = ['Filial', 'Produto', 'Custo', 'Varejo atual', 'Margem atual %', 'Moda varejo', 'Menor varejo', 'Índice atual',
            'Ação', 'Motivo', 'Varejo final', 'Atacado final', 'Margem nova %', 'Variação %']
    editado = st.data_editor(
        res[cols], hide_index=True, width="stretch", height=min(520, 40 + 35 * len(res)), key="reg_grade",
        disabled=[c for c in cols if c not in ("Varejo final", "Atacado final")],
        column_config={"Custo": moeda, "Varejo atual": moeda, "Moda varejo": moeda, "Menor varejo": moeda,
                       "Varejo final": st.column_config.NumberColumn("Varejo final", format="R$ %.2f", min_value=0.0, step=0.01),
                       "Atacado final": st.column_config.NumberColumn("Atacado final", format="R$ %.2f", min_value=0.0, step=0.01),
                       "Margem atual %": pct, "Margem nova %": pct, "Variação %": pct,
                       "Índice atual": st.column_config.NumberColumn(format="%.1f")})

    ui.secao("Exportar")
    with st.container(border=True, key="psc_reg_export"):
        mudar = editado[(editado["Varejo final"] - editado["Varejo atual"]).abs() >= 0.01]
        c1, c2 = st.columns(2)
        with c1:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                editado.to_excel(w, index=False, sheet_name="Precificacao")
            st.download_button("Baixar análise completa (XLSX)", data=buf.getvalue(), width="stretch", icon=":material/download:",
                               file_name=f"PriceSense_PricingRegular_{datetime.now():%d-%m-%Y}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with c2:
            if editado['Filial'].nunique() > 1:
                st.button("Copiar para o Preço Bot", disabled=True, width="stretch", key="reg_copy_off")
                st.caption("Escolha uma filial no filtro para copiar: o Preço Bot aplica a mesma lista às filiais que você selecionar lá.")
            elif mudar.empty:
                st.button("Copiar para o Preço Bot", disabled=True, width="stretch", key="reg_copy_vazio")
                st.caption("Nenhum preço muda com essa estratégia.")
            else:
                codigos = mudar['Produto'].astype(str).str.extract(r'(\d+)')[0]
                f2 = lambda v: f"{v:.2f}".replace(".", ",")
                texto = "\n".join(f"{c}\t{f2(v)}\t{f2(a)}" for c, v, a in zip(codigos, mudar['Varejo final'], mudar['Atacado final']))
                ui.botao_copiar(texto, f"Copiar {len(mudar)} preços para o Preço Bot", "Copiado: cole no Preço Bot")
