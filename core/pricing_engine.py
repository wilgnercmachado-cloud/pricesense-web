"""Pricing Regular: motor de precificação.

Cruza preço atual do PDV, custo e mercado (rotina 1067) e sugere o novo preço,
respeitando margem mínima, limite de variação por rodada e as regras de gôndola do Preço Bot.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core import market_engine as me
from core.preco_bot import arredondar_atacado, arredondar_varejo

ESTRATEGIAS = {
    "Seguir a moda": "Alinha o varejo ao preço mais praticado pelo mercado (índice alvo sobre a moda).",
    "Abaixo da moda": "Posiciona o varejo um pouco abaixo da moda, para ganhar percepção de preço.",
    "Bater o menor preço": "Usa o menor preço recente da concorrência como referência.",
    "Defender margem": "Sobe até a moda quando estamos baratos e só desce o necessário quando estamos caros.",
}


def base_precificacao(df_f: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por filial e produto com preço atual, custo, margem e referências de mercado."""
    total, _ = me.extrair("Mercado total", df_f)
    if total is None or total.empty:
        return pd.DataFrame()
    pdv = (df_f.sort_values('PESQUISADATA_DT')
           .assign(_v=lambda d: d['Vlr. Varejo PDV'].where(d['Vlr. Varejo PDV'] > 0.09),
                   _a=lambda d: d['Vlr. Atacado PDV'].where(d['Vlr. Atacado PDV'] > 0.09),
                   _c=lambda d: d['CustoMedio'].where(d['CustoMedio'] > 0.09))
           .groupby(['FILIAL', 'PRODUTO'])[['_v', '_a', '_c']].last().reset_index()
           .rename(columns={'FILIAL': 'Filial', 'PRODUTO': 'Produto', '_v': 'Varejo atual', '_a': 'Atacado atual', '_c': 'Custo'}))
    b = total.merge(pdv, on=['Filial', 'Produto'], how='left')
    b['Custo'] = b['Custo'].fillna(b.get('Custo Médio'))
    b = b.rename(columns={'Menor Varejo (Recente)': 'Menor varejo', 'Menor Atacado (Recente)': 'Menor atacado',
                          'Moda Varejo': 'Moda varejo', 'Moda Atacado': 'Moda atacado',
                          'Concorrente Menor (Recente)': 'Concorrente menor'})
    b['Margem atual %'] = np.where(b['Varejo atual'] > 0, 100 * (b['Varejo atual'] - b['Custo']) / b['Varejo atual'], np.nan)
    ref = b['Moda varejo'].where(b['Moda varejo'] > 0, b['Menor varejo'])
    b['Índice atual'] = np.where(ref > 0, 100 * b['Varejo atual'] / ref, np.nan)
    cols = ['Filial', 'Grupo Empresarial', 'Categoria Comercial', 'Produto', 'Custo', 'Varejo atual', 'Atacado atual',
            'Margem atual %', 'Moda varejo', 'Moda atacado', 'Menor varejo', 'Menor atacado', 'Concorrente menor', 'Índice atual']
    return b[[c for c in cols if c in b.columns]].dropna(subset=['Varejo atual']).reset_index(drop=True)


def precificar(base: pd.DataFrame, estrategia: str, indice_alvo: float, margem_min: float,
               variacao_max: float, gap_atacado: float) -> pd.DataFrame:
    """Calcula varejo e atacado sugeridos e o motivo de cada decisão.

    margem_min, variacao_max e gap_atacado em % (ex.: 15 = 15%).
    """
    linhas = []
    for _, r in base.iterrows():
        atual, custo = float(r['Varejo atual']), float(r['Custo']) if pd.notna(r['Custo']) else 0.0
        moda = float(r['Moda varejo']) if pd.notna(r.get('Moda varejo')) and r.get('Moda varejo') > 0 else None
        menor = float(r['Menor varejo']) if pd.notna(r.get('Menor varejo')) and r.get('Menor varejo') > 0 else None
        motivo = "Mercado"
        if estrategia == "Bater o menor preço":
            ref = menor or moda
            alvo = ref * indice_alvo / 100 if ref else atual
        elif estrategia == "Defender margem":
            ref = moda or menor
            alvo = max(atual, ref) if ref and atual < ref else (ref * indice_alvo / 100 if ref else atual)
        else:
            ref = moda or menor
            alvo = ref * indice_alvo / 100 if ref else atual
        if not ref:
            motivo = "Sem referência de mercado"

        piso = custo / (1 - margem_min / 100) if custo > 0 and margem_min < 100 else 0.0
        if alvo < piso:
            alvo, motivo = piso, "Margem mínima"
        lo, hi = atual * (1 - variacao_max / 100), atual * (1 + variacao_max / 100)
        if alvo < lo:
            alvo, motivo = lo, "Limite de variação"
        elif alvo > hi:
            alvo, motivo = hi, "Limite de variação"

        var_novo = arredondar_varejo(alvo)
        if custo > 0 and var_novo < piso:          # o arredondamento não pode furar a margem mínima
            var_novo = arredondar_varejo(piso + 0.05)
        moda_at = float(r['Moda atacado']) if pd.notna(r.get('Moda atacado')) and r.get('Moda atacado') > 0 else None
        razao = (moda_at / moda) if moda and moda_at and moda_at <= moda else (1 - gap_atacado / 100)
        atac_novo = arredondar_atacado(var_novo * razao, var_novo)

        mudou = abs(var_novo - atual) >= 0.01
        linhas.append({
            "Varejo sugerido": var_novo, "Atacado sugerido": atac_novo,
            "Margem nova %": 100 * (var_novo - custo) / var_novo if var_novo > 0 and custo > 0 else np.nan,
            "Variação %": 100 * (var_novo - atual) / atual if atual > 0 else np.nan,
            "Índice novo": 100 * var_novo / (moda or menor) if (moda or menor) else np.nan,
            "Ação": ("Subir" if var_novo > atual else "Baixar") if mudou else "Manter",
            "Motivo": motivo if mudou or motivo != "Mercado" else "Já no alvo",
        })
    return pd.concat([base.reset_index(drop=True), pd.DataFrame(linhas)], axis=1)


def impacto(res: pd.DataFrame) -> dict:
    def media(col):
        s = res[col].replace([np.inf, -np.inf], np.nan).dropna()
        return float(s.mean()) if not s.empty else None
    return {
        "itens": len(res), "sobem": int((res['Ação'] == "Subir").sum()), "descem": int((res['Ação'] == "Baixar").sum()),
        "mantem": int((res['Ação'] == "Manter").sum()),
        "margem_atual": media('Margem atual %'), "margem_nova": media('Margem nova %'),
        "indice_atual": media('Índice atual'), "indice_novo": media('Índice novo'),
        "travados": int(res['Motivo'].isin(["Margem mínima", "Limite de variação"]).sum()),
    }
