"""Gráficos Plotly no padrão visual do PriceSense."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from core.market_engine import formatar_brl
from ui import theme


def menor_preco(df_plot: pd.DataFrame, series: list[tuple[str, str, str, int, bool]]) -> go.Figure:
    """series: (coluna, rótulo, cor, deslocamento da etiqueta de mínimo, mostra detalhe por concorrente)."""
    t = theme.tokens()
    fig = go.Figure()
    com_rotulos = len(df_plot) <= 12
    for coluna, rotulo, cor, desloc, detalhe in series:
        if coluna not in df_plot.columns or df_plot[coluna].isnull().all():
            continue
        custom = df_plot['HOVER_CONC'] if detalhe and 'HOVER_CONC' in df_plot.columns else [''] * len(df_plot)
        hover = ("R$ %{y:,.2f}<br><span style='font-size:12px'>Menor preço por concorrente</span><br>%{customdata}<extra></extra>"
                 if detalhe else "R$ %{y:,.2f}<extra></extra>")
        fig.add_trace(go.Scatter(
            x=df_plot['DATA_STR'], y=df_plot[coluna], mode='lines+markers+text' if com_rotulos else 'lines+markers', name=rotulo,
            line=dict(color=cor, width=2.5, shape='spline', smoothing=0.6),
            marker=dict(size=7, color=t['surface'], line=dict(width=2, color=cor)),
            text=[formatar_brl(v, prefixo=False) for v in df_plot[coluna]],
            textposition="top center" if desloc < 0 else "bottom center",
            textfont=dict(color=cor, size=11),
            customdata=custom, hovertemplate=hover,
        ))
        minimo = df_plot[coluna].min()
        data_min = df_plot[df_plot[coluna] == minimo].iloc[0]['DATA_STR']
        fig.add_annotation(
            x=data_min, y=minimo, text=f"Mínimo {formatar_brl(minimo)}",
            showarrow=True, arrowhead=0, arrowwidth=1.5, arrowcolor=cor, ax=0, ay=desloc,
            font=dict(color="#FFFFFF", size=11), bgcolor=cor, borderpad=4, opacity=0.96,
        )
    layout = theme.plotly_layout(340)
    layout["yaxis"]["tickformat"] = ",.2f"
    layout["xaxis"]["nticks"] = 10
    fig.update_layout(**layout)
    return fig
