"""Pricing Promo: leitura de encartes, explosão de clusters e validação de conflitos."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd


class ArquivoSemDatas(ValueError):
    """Planilha sem as colunas INICIO e FIM."""


def validar_status_conflitos(df_alvo: pd.DataFrame) -> pd.Series:
    df_temp = df_alvo.copy()
    df_temp['DT_I_MATH'] = pd.to_datetime(df_temp['INICIO'], format='%d/%m/%Y', errors='coerce')
    df_temp['DT_F_MATH'] = pd.to_datetime(df_temp['FIM'], format='%d/%m/%Y', errors='coerce')
    df_temp = df_temp.sort_values(by=['ID FILIAL', 'SEQPRODUTO', 'DT_I_MATH'])

    # Erro de preço: mesmo produto, mesma campanha, mesma filial e período com preços diferentes.
    # Sem coluna CAMPANHA, cada arquivo enviado é tratado como uma campanha.
    col_campanha = 'CAMPANHA' if 'CAMPANHA' in df_temp.columns else 'ARQUIVO ORIGEM'
    df_temp['QTD_PRECOS'] = df_temp.groupby(['ID FILIAL', 'SEQPRODUTO', col_campanha, 'INICIO', 'FIM'])['PRECO_NUM'].transform('nunique')

    # Conflito de datas: períodos que se cruzam para o mesmo produto e filial.
    df_temp['FIM_MAX_ANT'] = df_temp.groupby(['ID FILIAL', 'SEQPRODUTO'])['DT_F_MATH'].transform(lambda x: x.shift().cummax())
    df_temp['SOU_INVASOR'] = df_temp['DT_I_MATH'] <= df_temp['FIM_MAX_ANT']
    df_temp['INI_PROXIMO'] = df_temp.groupby(['ID FILIAL', 'SEQPRODUTO'])['DT_I_MATH'].shift(-1)
    df_temp['FUI_INVADIDO'] = df_temp['DT_F_MATH'] >= df_temp['INI_PROXIMO']
    df_temp['TEM_CONFLITO_DATA'] = df_temp['SOU_INVASOR'] | df_temp['FUI_INVADIDO']

    def definir_status(r):
        if r['QTD_PRECOS'] > 1: return "CRÍTICO - ERRO DE PREÇO"
        if r['TEM_CONFLITO_DATA']: return "CRÍTICO - CONFLITOS DE DATAS"
        return "VÁLIDO"

    df_temp['Status Sistema'] = df_temp.apply(definir_status, axis=1)
    return df_temp.sort_index()['Status Sistema']


def ler_planilhas(arquivos) -> tuple[list[pd.DataFrame], list[str]]:
    dfs, falhas = [], []
    for arq in arquivos:
        try:
            nome = arq.name
            df_temp = pd.read_csv(arq, sep=';', encoding='latin1') if nome.lower().endswith('.csv') else pd.read_excel(arq)
            df_temp['ARQUIVO ORIGEM'] = os.path.splitext(nome)[0]
            dfs.append(df_temp)
        except Exception:
            falhas.append(arq.name)
    return dfs, falhas


def _normalizar_id(v):
    """544.0 -> 544 (o merge com NaN transforma IDs inteiros em float)."""
    if isinstance(v, float):
        if np.isnan(v):
            return None
        if v.is_integer():
            return int(v)
    return v


def _limpar_preco(p) -> float:
    try:
        return float(str(p).upper().replace('R$', '').replace(' ', '').replace(',', '.'))
    except Exception:
        return 0.0


def processar(dfs: list[pd.DataFrame], df_clusters: pd.DataFrame, mapa_lojas: dict) -> dict:
    df_bruto = pd.concat(dfs, ignore_index=True)
    df_bruto.rename(columns=lambda x: str(x).strip().upper(), inplace=True)

    if 'INICIO' not in df_bruto.columns or 'FIM' not in df_bruto.columns:
        raise ArquivoSemDatas()

    for col_data in ['INICIO', 'FIM']:
        df_bruto[col_data] = pd.to_datetime(df_bruto[col_data].astype(str).str[:10], errors='coerce').dt.strftime('%d/%m/%Y')

    if 'PRECO_PROMOCIONAL' in df_bruto.columns:
        df_bruto['PRECO_NUM'] = df_bruto['PRECO_PROMOCIONAL'].apply(_limpar_preco)
    elif 'PRECO' in df_bruto.columns:
        df_bruto['PRECO_NUM'] = df_bruto['PRECO'].apply(_limpar_preco)
    else:
        df_bruto['PRECO_NUM'] = 0.0

    if 'CLUSTER/LOJA' in df_bruto.columns and not df_clusters.empty:
        df_explodido = df_bruto.merge(df_clusters, left_on='CLUSTER/LOJA', right_on='CLUSTER', how='left')
        ids = pd.Series([_normalizar_id(v) for v in df_explodido['ID FILIAL']], index=df_explodido.index, dtype=object)
        df_explodido['ID FILIAL'] = pd.Series(
            [i if i is not None else c for i, c in zip(ids, df_explodido['CLUSTER/LOJA'])], index=df_explodido.index, dtype=object)
        clusters_fora = df_explodido[df_explodido['ID FILIAL'] == df_explodido['CLUSTER/LOJA']]['CLUSTER/LOJA'].unique().tolist()
    else:
        df_explodido = df_bruto.copy()
        df_explodido['ID FILIAL'] = df_explodido['CLUSTER/LOJA'] if 'CLUSTER/LOJA' in df_explodido.columns else 'DESCONHECIDO'
        clusters_fora = []

    df_explodido['FILIAL ABREV'] = df_explodido['ID FILIAL'].astype(str).map(mapa_lojas).fillna(df_explodido['ID FILIAL'].astype(str))

    if 'SEQPRODUTO' in df_explodido.columns:
        df_limpo = df_explodido.drop_duplicates(subset=['ID FILIAL', 'SEQPRODUTO', 'PRECO_NUM', 'INICIO', 'FIM']).copy()
        df_limpo['Status Sistema'] = validar_status_conflitos(df_limpo)
    else:
        df_limpo = df_explodido.copy()
        df_limpo['Status Sistema'] = "VÁLIDO"

    df_limpo['ALTERADO_MANUAL'] = 'NÃO'
    d_inicio = pd.to_datetime(df_limpo['INICIO'], format='%d/%m/%Y', errors='coerce')
    d_fim = pd.to_datetime(df_limpo['FIM'], format='%d/%m/%Y', errors='coerce')
    df_limpo['MIDIA'] = np.where((d_fim - d_inicio).dt.days < 4, 1, 2)

    hoje = pd.Timestamp.today().normalize().date()
    fim_dt = pd.to_datetime(df_limpo['FIM'], format='%d/%m/%Y', errors='coerce').dt.date
    vencidas = df_limpo[fim_dt < hoje]['ARQUIVO ORIGEM'].unique().tolist()

    return {"df": df_limpo, "clusters_fora": clusters_fora, "vencidas": vencidas}


def linhas_diferentes(a: pd.Series, b: pd.Series) -> pd.Series:
    """Comparação célula a célula que ignora diferenças de dtype e trata NaN == NaN."""
    a_obj = a.astype(object).where(a.notna(), None)
    b_obj = b.astype(object).where(b.notna(), None)
    return pd.Series([x != y for x, y in zip(a_obj, b_obj)], index=a.index, dtype=bool)


def texto_importacao(df_filtrado: pd.DataFrame, aplicar: bool) -> str:
    df_export = df_filtrado.drop_duplicates(subset=['ID FILIAL', 'SEQPRODUTO', 'PRECO_NUM', 'INICIO', 'FIM']).copy()
    # Mídia recalculada (período inclusivo): 4 dias ou mais = 2, abaixo disso = 1.
    d_ini = pd.to_datetime(df_export['INICIO'], format='%d/%m/%Y', errors='coerce')
    d_fim = pd.to_datetime(df_export['FIM'], format='%d/%m/%Y', errors='coerce')
    df_export['MIDIA_CALCULADA'] = np.where((d_fim - d_ini).dt.days + 1 >= 4, 2, 1)

    if aplicar:
        df_varejo = pd.DataFrame({
            'Filial': df_export['ID FILIAL'], 'Tipo_Preco': "1", 'Tipo_Midia': df_export['MIDIA_CALCULADA'],
            'Motivo_Midia': 7, 'Produto': df_export['SEQPRODUTO'],
            'Preco': df_export['PRECO_NUM'].apply(lambda x: f"{x:.2f}".replace('.', ',')),
            'Inicio': df_export['INICIO'], 'Fim': df_export['FIM'],
        })
    else:
        df_varejo = pd.DataFrame({
            'Filial': df_export['ID FILIAL'], 'Tipo_Preco': "1",
            'Tipo_Midia': df_export['MIDIA_CALCULADA'], 'Produto': df_export['SEQPRODUTO'],
        })
    df_atacado = df_varejo.copy()
    df_atacado['Tipo_Preco'] = "2"
    df_final = pd.concat([df_varejo, df_atacado]).sort_values(by=['Filial', 'Produto', 'Tipo_Preco'])
    return df_final.to_csv(sep='\t', index=False, header=False)
