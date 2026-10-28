"""Pesquisa de Mercado: leitura da rotina 1067, enriquecimento e modelos analíticos.

As regras de filtro (tipos, faixas de margem, anomalias) seguem a versão original.
"""
from __future__ import annotations

import io
import zipfile
from typing import Callable

import numpy as np
import pandas as pd

VAR, ATAC = 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.'
TIPOS_MODA = 'REGULAR|PROMOCAO|PROMOÇÃO|PONTO EXTRA'

MAPA_COLUNAS = {
    'CUSTOMEDIO': 'CustoMedio', 'CUSTO MEDIO': 'CustoMedio',
    'VLR. VAREJO PDV': 'Vlr. Varejo PDV', 'VLR. ATACADO PDV': 'Vlr. Atacado PDV',
    'VLR. VAREJO CONC.': VAR, 'VLR. VAREJO CONC': VAR, 'VLR.VARE.CONC': VAR, 'VLR.VARE.CONC.': VAR,
    'VLR. ATACADO CONC.': ATAC, 'VLR. ATACADO CONC': ATAC, 'VLR.ATAC.CONC': ATAC, 'VLR.ATAC.CONC.': ATAC,
    'TIPO': 'Tipo', 'TIPO PRECO': 'Tipo', 'TIPO PREÇO': 'Tipo',
}
OBRIGATORIAS = ['FILIAL', 'FILIALCONCORRENTE', 'PESQUISADATA', 'CustoMedio', 'Vlr. Varejo PDV',
                'Vlr. Atacado PDV', VAR, ATAC, 'PRODUTO', 'Tipo']


# ---------------------------------------------------------------- leitura
def ler_arquivo(upload) -> pd.DataFrame:
    nome = upload.name.lower()
    if nome.endswith('.zip'):
        with zipfile.ZipFile(upload) as z:
            alvo = next((n for n in z.namelist() if n.lower().endswith(('.csv', '.xlsx', '.xls'))), None)
            if not alvo:
                raise ValueError("O ZIP não contém nenhuma planilha CSV ou Excel.")
            conteudo = io.BytesIO(z.read(alvo))
            if alvo.lower().endswith('.csv'):
                return pd.read_csv(conteudo, sep='|', encoding='latin1', dtype=str)
            return pd.read_excel(conteudo, dtype=str)
    if nome.endswith('.csv'):
        return pd.read_csv(upload, sep='|', encoding='latin1', dtype=str)
    return pd.read_excel(upload, dtype=str)


def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df.rename(columns=MAPA_COLUNAS)


def enriquecer(df: pd.DataFrame,
               buscar_produtos: Callable[[list[int]], list[dict]],
               buscar_fornecedores: Callable[[list[int]], list[dict]],
               progresso: Callable[[str], None] | None = None) -> tuple[pd.DataFrame, dict]:
    """Cruza o código do produto com dim_produto e dim_fornecedor."""
    stats = {"produtos": 0, "fornecedores": 0, "linhas": len(df), "classificadas": 0}
    if 'PRODUTO' not in df.columns:
        return df, stats
    df = df.copy()
    df['CHAVE_NUM'] = pd.to_numeric(df['PRODUTO'].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
    codigos = df['CHAVE_NUM'].dropna().astype(int).unique().tolist()
    stats["produtos"] = len(codigos)

    if codigos:
        if progresso: progresso(f"Buscando {len(codigos)} produtos no cadastro")
        dados_p = buscar_produtos(codigos)
        if dados_p:
            df_p = pd.DataFrame(dados_p)
            df_p['CHAVE_NUM'] = pd.to_numeric(df_p['id_produto'], errors='coerce')
            df_p['FORN_NUM'] = pd.to_numeric(df_p['id_fornecedor'], errors='coerce')
            forn = df_p['FORN_NUM'].dropna().astype(int).unique().tolist()
            stats["fornecedores"] = len(forn)
            dados_f = []
            if forn:
                if progresso: progresso(f"Buscando {len(forn)} fornecedores")
                dados_f = buscar_fornecedores(forn)
            if dados_f:
                df_f = pd.DataFrame(dados_f)
                df_f['FORN_NUM'] = pd.to_numeric(df_f['id_fornecedor'], errors='coerce')
                df_p['nome_grupo_empresarial'] = df_p['FORN_NUM'].map(dict(zip(df_f['FORN_NUM'], df_f['nome_grupo_empresarial'])))
            else:
                df_p['nome_grupo_empresarial'] = "SEM CLASSIFICAÇÃO"

            dict_cat = dict(zip(df_p['CHAVE_NUM'], df_p['categoria_comercial']))
            dict_grp = dict(zip(df_p['CHAVE_NUM'], df_p['nome_grupo_empresarial']))
            antigas = [c for c in df.columns if str(c).strip().upper() in
                       ['CATEGORIA_COMERCIAL', 'GRUPO_EMPRESARIAL', 'CATEGORIA COMERCIAL', 'GRUPO EMPRESARIAL']]
            df.drop(columns=antigas, inplace=True, errors='ignore')
            df['CATEGORIA_COMERCIAL'] = df['CHAVE_NUM'].map(dict_cat).fillna("SEM CLASSIFICAÇÃO")
            df['GRUPO_EMPRESARIAL'] = df['CHAVE_NUM'].map(dict_grp).fillna("SEM CLASSIFICAÇÃO")
            stats["classificadas"] = int((df['CATEGORIA_COMERCIAL'] != "SEM CLASSIFICAÇÃO").sum())

    df.drop(columns=['CHAVE_NUM'], inplace=True, errors='ignore')
    for col in ('CATEGORIA_COMERCIAL', 'GRUPO_EMPRESARIAL'):
        if col not in df.columns:
            df[col] = "SEM CLASSIFICAÇÃO"
    return df, stats


def _para_float(val) -> float:
    try:
        if pd.isna(val) or str(val).strip() == '':
            return 0.0
        return float(str(val).upper().replace('R$', '').replace(' ', '').replace(',', '.'))
    except Exception:
        return 0.0


def _nome_empresa(nome_filial) -> str:
    partes = str(nome_filial).split('-')
    return partes[1].strip() if len(partes) > 1 else str(nome_filial).strip()


def preparar(df: pd.DataFrame, df_dim_emp: pd.DataFrame) -> pd.DataFrame:
    faltando = [c for c in OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError("O arquivo não tem as colunas da rotina 1067. Faltam: " + ", ".join(faltando))

    df = df[~df['FILIAL'].astype(str).str.upper().str.contains('TOTAL', na=False)].copy()
    for col in ['CustoMedio', 'Vlr. Varejo PDV', 'Vlr. Atacado PDV', VAR, ATAC, 'QtdEstoque']:
        if col in df.columns:
            df[col] = df[col].apply(_para_float)

    df['PESQUISADATA_DT'] = pd.to_datetime(df['PESQUISADATA'], format='%d/%m/%Y', errors='coerce')
    df[ATAC] = np.where(df[ATAC] <= 0.09, df[VAR], df[ATAC])
    df['MargemConc'] = np.where(df[VAR] > 0, (df[VAR] - df['CustoMedio']) / df[VAR].where(df[VAR] > 0, 1), 0.0)

    if not df_dim_emp.empty and {'filial_concorrente', 'empresa'}.issubset(df_dim_emp.columns):
        mapa = dict(zip(df_dim_emp['filial_concorrente'].astype(str).str.strip(), df_dim_emp['empresa'].astype(str).str.strip()))
        df['EMPRESA_CONC'] = df['FILIALCONCORRENTE'].map(mapa).fillna(df['FILIALCONCORRENTE'].apply(_nome_empresa))
    else:
        df['EMPRESA_CONC'] = df['FILIALCONCORRENTE'].apply(_nome_empresa)
    return df


# ---------------------------------------------------------------- filtros
def filtro_qualidade(df: pd.DataFrame) -> pd.DataFrame:
    """Remove preços zerados, margens absurdas e desvios grotescos da mediana do produto."""
    df = df[df[VAR] > 0.09]
    if df.empty:
        return df
    df = df[(df['CustoMedio'] <= 0.09) | (df['MargemConc'] >= -0.60)]
    mediana = df.groupby('PRODUTO')[VAR].transform('median')
    return df[(df[VAR] >= mediana * 0.40) & (df[VAR] <= mediana * 3.0)]


def aplicar_filtros(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    out = filtro_qualidade(df)
    if f.get("produto") not in (None, "Todos"): out = out[out['PRODUTO'] == f["produto"]]
    if f.get("filial") not in (None, "Todas"): out = out[out['FILIAL'] == f["filial"]]
    if f.get("categoria") not in (None, "Todas"): out = out[out['CATEGORIA_COMERCIAL'] == f["categoria"]]
    if f.get("grupo") not in (None, "Todos"): out = out[out['GRUPO_EMPRESARIAL'] == f["grupo"]]
    if f.get("concorrentes"): out = out[out['FILIALCONCORRENTE'].isin(f["concorrentes"])]
    if f.get("tipos"): out = out[out['Tipo'].isin(f["tipos"])]
    periodo = f.get("periodo")
    if periodo and len(periodo) == 2:
        datas = out['PESQUISADATA_DT'].dt.date
        out = out[(datas >= periodo[0]) & (datas <= periodo[1])]
    return out


def _sem_validade(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df['Tipo'].astype(str).str.upper().str.contains('VALIDADE', na=False)]


def _so_tipos_moda(df: pd.DataFrame) -> pd.DataFrame:
    return df[df['Tipo'].astype(str).str.upper().str.contains(TIPOS_MODA, regex=True, na=False)]


def _faixa_margem(df: pd.DataFrame, minimo: float, maximo: float) -> pd.DataFrame:
    return df[(df['CustoMedio'] <= 0.09) | ((df['MargemConc'] >= minimo) & (df['MargemConc'] <= maximo))]


# ---------------------------------------------------------------- indicadores
def _moda(g: pd.DataFrame) -> tuple[float, float, int]:
    counts = g[VAR].value_counts()
    if counts.empty:
        return 0.0, 0.0, 0
    m_var = counts.index[0]
    atac = g[g[VAR] == m_var][ATAC].mode()
    return float(m_var), float(atac.iloc[0]) if not atac.empty else 0.0, int(counts.iloc[0])


def indicadores(df_filt: pd.DataFrame) -> dict:
    base = _faixa_margem(_so_tipos_moda(df_filt), -0.30, 0.60)
    moda_var, moda_atac, qtd = _moda(base) if not base.empty else (0.0, 0.0, 0)
    out = {"moda_var": moda_var, "moda_atac": moda_atac, "qtd_moda": qtd,
           "min": 0.0, "max": 0.0, "min_origem": None, "max_origem": None}
    if not df_filt.empty:
        for chave, idx in (("min", df_filt[VAR].idxmin()), ("max", df_filt[VAR].idxmax())):
            linha = df_filt.loc[idx]
            out[chave] = float(linha[VAR])
            out[f"{chave}_origem"] = (str(linha['FILIALCONCORRENTE']), str(linha['PESQUISADATA']))
    return out


def itens_letreiro(df_filt: pd.DataFrame) -> list[dict]:
    df_tk = _sem_validade(df_filt)
    if df_tk.empty:
        return []
    df_tk = df_tk.sort_values(by=['PESQUISADATA_DT', VAR], ascending=[False, True]).drop_duplicates(subset=['EMPRESA_CONC'], keep='first')
    return [{"empresa": str(r['EMPRESA_CONC']).upper(), "varejo": r[VAR], "atacado": r[ATAC]} for _, r in df_tk.iterrows()]


def media_por_empresa(df_filt: pd.DataFrame) -> pd.DataFrame:
    out = df_filt.groupby('EMPRESA_CONC')[[VAR, ATAC]].mean().reset_index()
    return out.rename(columns={'EMPRESA_CONC': 'Concorrente', VAR: 'Varejo', ATAC: 'Atacado'}).sort_values('Varejo')


def serie_menor_preco(df_filt: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ['Vlr. Varejo PDV', 'Vlr. Atacado PDV', VAR, ATAC] if c in df_filt.columns]
    df_plot = df_filt.groupby('PESQUISADATA_DT')[cols].min().reset_index().sort_values('PESQUISADATA_DT')
    df_plot['DATA_STR'] = df_plot['PESQUISADATA_DT'].dt.strftime('%d/%m/%Y')
    df_hov = df_filt.groupby(['PESQUISADATA_DT', 'FILIALCONCORRENTE'])[VAR].min().reset_index()
    df_hov['conc_str'] = (df_hov['FILIALCONCORRENTE'].astype(str).str[:30] + ": <b>" +
                          df_hov[VAR].apply(formatar_brl) + "</b>")
    df_hov_str = df_hov.groupby('PESQUISADATA_DT')['conc_str'].apply(lambda x: '<br>'.join(x)).reset_index(name='HOVER_CONC')
    return pd.merge(df_plot, df_hov_str, on='PESQUISADATA_DT', how='left')


def formatar_brl(valor, prefixo: bool = True) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "-"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}" if prefixo else s


# ---------------------------------------------------------------- modelos de extração
MODELOS = {
    "Preço moda": "Preço mais frequente por filial e produto. Considera só coletas Regular, Promoção e Ponto extra, com margem entre -30% e +60%.",
    "Menor preço recente": "Pega a última coleta de cada concorrente e, entre elas, a mais barata. Ignora preços de validade.",
    "Menor preço histórico": "Menor preço do período por filial e produto. Ignora preços de validade e margens fora de -50% a +60%.",
    "Mercado total": "As três visões lado a lado, com margem entre -40% e +60%.",
}

_COLS_BASE = {'FILIAL', 'GRUPO_EMPRESARIAL', 'CATEGORIA_COMERCIAL', 'PRODUTO', 'FILIALCONCORRENTE', VAR, ATAC}


def _modas_por_concorrente(df: pd.DataFrame, chaves: list[str], col_freq: str) -> pd.DataFrame:
    linhas = []
    for chave, g in df.groupby(chaves + ['FILIALCONCORRENTE']):
        m_var, m_atac, freq = _moda(g)
        linhas.append(dict(zip(chaves + ['FILIALCONCORRENTE'], chave), **{'Moda Varejo': m_var, 'Moda Atacado': m_atac, col_freq: freq}))
    modas = pd.DataFrame(linhas)
    if modas.empty:
        return modas
    idx = modas.groupby(['FILIAL', 'PRODUTO'])[col_freq].idxmax()
    return modas.loc[idx].reset_index(drop=True)


def extrair(modelo: str, df_filt: pd.DataFrame) -> tuple[pd.DataFrame | None, str]:
    """Retorna (tabela, mensagem). Tabela None quando não há dados válidos."""
    if modelo == "Preço moda":
        df = _faixa_margem(_so_tipos_moda(df_filt), -0.30, 0.60)
        if df.empty:
            return None, "Nenhuma coleta sobrou depois dos filtros de tipo e de margem (-30% a +60%)."
        out = _modas_por_concorrente(df, ['FILIAL', 'GRUPO_EMPRESARIAL', 'CATEGORIA_COMERCIAL', 'PRODUTO'], 'Frequência Máxima')
        out = out.rename(columns={'FILIAL': 'Filial', 'GRUPO_EMPRESARIAL': 'Grupo Empresarial', 'CATEGORIA_COMERCIAL': 'Categoria Comercial',
                                  'PRODUTO': 'Produto', 'FILIALCONCORRENTE': 'Concorrente Moda'})
        out = out[['Filial', 'Grupo Empresarial', 'Categoria Comercial', 'Produto', 'Moda Varejo', 'Moda Atacado', 'Frequência Máxima', 'Concorrente Moda']]
        return out.sort_values(by=['Filial', 'Produto']), ""

    if modelo == "Menor preço recente":
        df = _sem_validade(df_filt)
        if df.empty:
            return None, "Nenhuma coleta sobrou depois de remover os preços de validade."
        df = df.sort_values(by='PESQUISADATA_DT', ascending=False).drop_duplicates(subset=['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE'], keep='first')
        df = df.sort_values(by=VAR, ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
        mapa = {'FILIAL': 'Filial', 'GRUPO_EMPRESARIAL': 'Grupo Empresarial', 'CATEGORIA_COMERCIAL': 'Categoria Comercial', 'PRODUTO': 'Produto',
                'CustoMedio': 'Custo Médio', VAR: 'Menor Varejo', ATAC: 'Menor Atacado', 'MargemConc': 'Margem Mercado (%)',
                'Tipo': 'Tipo', 'PESQUISADATA': 'Data Pesquisa', 'FILIALCONCORRENTE': 'Concorrente Menor'}
        out = df.rename(columns=mapa)[list(mapa.values())]
        out['Margem Mercado (%)'] = out['Margem Mercado (%)'].apply(lambda x: round(x * 100, 2) if pd.notnull(x) else 0.0)
        return out.sort_values(by=['Filial', 'Produto']), ""

    if modelo == "Menor preço histórico":
        df = _faixa_margem(_sem_validade(df_filt), -0.50, 0.60)
        if df.empty:
            return None, "Nenhuma coleta sobrou depois de remover validade e margens fora de -50% a +60%."
        df = df.sort_values(by=VAR, ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
        mapa = {'FILIAL': 'Filial', 'GRUPO_EMPRESARIAL': 'Grupo Empresarial', 'CATEGORIA_COMERCIAL': 'Categoria Comercial', 'PRODUTO': 'Produto',
                'CustoMedio': 'Custo Médio', 'Vlr. Varejo PDV': 'Vlr. Varejo PDV', 'Vlr. Atacado PDV': 'Vlr. Atacado PDV',
                VAR: 'Menor Varejo Conc.', ATAC: 'Menor Atacado Conc.', 'Tipo': 'Tipo', 'PESQUISADATA': 'Data', 'FILIALCONCORRENTE': 'Menor Concorrente'}
        out = df.rename(columns=mapa)[list(mapa.values())]
        return out.sort_values(by=['Filial', 'Produto']), ""

    if modelo == "Mercado total":
        base = _faixa_margem(df_filt, -0.40, 0.60)
        if base.empty:
            return None, "Nenhuma coleta sobrou depois do filtro de margem (-40% a +60%)."
        rec = _sem_validade(base).sort_values(by='PESQUISADATA_DT', ascending=False).drop_duplicates(subset=['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE'], keep='first')
        rec = rec.sort_values(by=VAR, ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
        rec = rec[['FILIAL', 'GRUPO_EMPRESARIAL', 'CATEGORIA_COMERCIAL', 'PRODUTO', 'CustoMedio', VAR, ATAC, 'Tipo', 'PESQUISADATA', 'FILIALCONCORRENTE']].rename(columns={
            'GRUPO_EMPRESARIAL': 'Grupo Empresarial', 'CATEGORIA_COMERCIAL': 'Categoria Comercial', 'CustoMedio': 'Custo Médio',
            VAR: 'Menor Varejo (Recente)', ATAC: 'Menor Atacado (Recente)', 'PESQUISADATA': 'Data Pesquisa',
            'FILIALCONCORRENTE': 'Concorrente Menor (Recente)'})
        hst = _sem_validade(base).sort_values(by=VAR, ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
        hst = hst[['FILIAL', 'PRODUTO', VAR, ATAC, 'Tipo', 'FILIALCONCORRENTE']].rename(columns={
            VAR: 'Menor Varejo (Histórico)', ATAC: 'Menor Atacado (Histórico)', 'Tipo': 'Tipo (Histórico)',
            'FILIALCONCORRENTE': 'Concorrente Menor (Histórico)'})
        md = _so_tipos_moda(base)
        md = _modas_por_concorrente(md, ['FILIAL', 'PRODUTO'], 'Frequência') if not md.empty else pd.DataFrame()
        if md.empty:
            md = pd.DataFrame(columns=['FILIAL', 'PRODUTO', 'Moda Varejo', 'Moda Atacado', 'Frequência', 'Concorrente Moda'])
        else:
            md = md.rename(columns={'FILIALCONCORRENTE': 'Concorrente Moda'})
        out = pd.merge(rec, hst, on=['FILIAL', 'PRODUTO'], how='outer').merge(md, on=['FILIAL', 'PRODUTO'], how='outer')
        out = out.rename(columns={'FILIAL': 'Filial', 'PRODUTO': 'Produto'})
        ordem = ['Filial', 'Grupo Empresarial', 'Categoria Comercial', 'Produto', 'Custo Médio',
                 'Menor Varejo (Recente)', 'Menor Atacado (Recente)', 'Tipo', 'Data Pesquisa', 'Concorrente Menor (Recente)',
                 'Menor Varejo (Histórico)', 'Menor Atacado (Histórico)', 'Tipo (Histórico)', 'Concorrente Menor (Histórico)',
                 'Moda Varejo', 'Moda Atacado', 'Frequência', 'Concorrente Moda']
        out = out[[c for c in ordem if c in out.columns]]
        return out.sort_values(by=['Filial', 'Produto']), ""

    return None, "Modelo desconhecido."
