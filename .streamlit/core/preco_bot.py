"""Regras do Preço Bot: arredondamento psicológico e montagem do arquivo de importação.

A lógica de arredondamento é idêntica à versão original (validada em tests/).
"""
from __future__ import annotations

from datetime import date

import numpy as np


def arredondar_varejo(preco):
    if preco <= 0: return 0.0
    preco_arred = round(preco, 2); base_inteira = int(np.floor(preco_arred)); validos = []
    faixa = 'A' if preco_arred <= 10.99 else ('B' if preco_arred <= 19.99 else ('C' if preco_arred <= 40.00 else 'D'))
    for c in range(100):
        p = c // 10; u = c % 10; is_valid = False
        if faixa == 'A': is_valid = (u in [5, 8, 9])
        elif faixa == 'B': is_valid = (1 <= p <= 9) and (u in [5, 8, 9])
        elif faixa == 'C': is_valid = (3 <= p <= 9) and (p in [5, 9]) if u == 0 else (3 <= p <= 9) and (u in [0, 5, 8, 9])
        else: is_valid = (3 <= p <= 9) and (p in [5, 9]) if u == 0 else (3 <= p <= 9) and (u == 9)
        if is_valid: validos.append(c / 100.0)
    candidatos = [round((base_inteira - 1) + v, 2) for v in validos] + [round(base_inteira + v, 2) for v in validos] + [round((base_inteira + 1) + v, 2) for v in validos]
    if round(preco_arred, 2) in candidatos: return round(preco_arred, 2)
    candidatos.sort(key=lambda x: abs(x - preco_arred))
    return round(candidatos[0], 2) if candidatos else round(preco_arred, 2)


def arredondar_atacado(preco_atacado, varejo_finalizado):
    if preco_atacado <= 0: return 0.0
    varejo_finalizado = round(varejo_finalizado, 2); preco_arred = round(preco_atacado, 2)
    ultimo_digito_varejo = int(round(varejo_finalizado * 100)) % 10
    faixa = 'A' if preco_arred <= 10.99 else ('B' if preco_arred <= 19.99 else ('C' if preco_arred <= 40.00 else 'D'))
    base_inteira = int(np.floor(preco_arred)); validos = []
    for c in range(100):
        p = c // 10; u = c % 10
        if u == ultimo_digito_varejo:
            is_valid = False
            if faixa == 'A': is_valid = True
            elif faixa == 'B': is_valid = (1 <= p <= 9)
            elif faixa in ['C', 'D'] and (3 <= p <= 9): is_valid = True if u != 0 else (p in [5, 9])
            if is_valid: validos.append(c / 100.0)
    candidatos = [round((base_inteira - 1) + v, 2) for v in validos] + [round(base_inteira + v, 2) for v in validos] + [round((base_inteira + 1) + v, 2) for v in validos]
    proximo = round(preco_arred, 2) if round(preco_arred, 2) in candidatos else (round(sorted(candidatos, key=lambda x: abs(x - preco_arred))[0], 2) if candidatos else round(preco_arred, 2))
    return round(varejo_finalizado if proximo >= varejo_finalizado else proximo, 2)


# ---------------------------------------------------------------- colagem
def _partes(linha: str) -> list[str]:
    return [p.strip() for p in linha.split('\t')] if '\t' in linha else linha.split()


def eh_cancelamento(formato: str, id_classificacao: str, cod_op: str) -> bool:
    return (formato == "COMERCIAL" and cod_op == "2") or (id_classificacao == "0" and cod_op == "2")


def validar_colagem(texto: str) -> dict:
    """Bloqueio de atacado > varejo e alerta de diferença >= 10%."""
    erro_atacado, alerta_margem, itens_erro, linhas = False, False, [], 0
    for linha in texto.strip().split('\n'):
        partes = _partes(linha)
        if not partes or partes == [""]:
            continue
        linhas += 1
        try:
            cod = partes[0]
            v_val = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
            a_val = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else v_val
            if a_val > v_val:
                erro_atacado = True
                if len(itens_erro) < 5:
                    itens_erro.append(cod)
            elif v_val > 0 and abs(v_val - a_val) / v_val >= 0.10:
                alerta_margem = True
        except Exception:
            pass
    return {"erro_atacado": erro_atacado, "alerta_margem": alerta_margem, "itens_erro": itens_erro, "linhas": linhas}


def gerar_importacao(texto: str, filiais: list[str], formato: str, id_classificacao: str, cod_op: str,
                     dt_inicio: date, dt_fim: date, aplicar_similar: str, somente_piso: str) -> tuple[list[dict], list[str]]:
    """Retorna (linhas de importação, linhas de entrada ignoradas por erro de leitura)."""
    linhas = texto.strip().split('\n')
    dados: list[dict] = []
    ignoradas: list[str] = []
    ini, fim = dt_inicio.strftime("%d/%m/%Y"), dt_fim.strftime("%d/%m/%Y")
    for n_filial, filial in enumerate(filiais):
        id_fil = filial.split(" - ")[0]
        for linha in linhas:
            partes = _partes(linha)
            if not partes or partes == [""]:
                continue
            cod = partes[0]
            try:
                var_bruto = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
                atac_bruto = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else var_bruto
                novo_var = arredondar_varejo(var_bruto) if var_bruto > 0 else 0.0
                novo_atac = arredondar_atacado(atac_bruto, novo_var) if atac_bruto > 0 else 0.0
                str_var = f"{novo_var:.2f}".replace('.', ',') if novo_var > 0 else ""
                str_atac = f"{novo_atac:.2f}".replace('.', ',') if novo_atac > 0 else ""

                if id_classificacao == "14":
                    dados.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac})
                elif id_classificacao == "0":
                    if cod_op == "2":
                        dados.append({"Código da Filial": id_fil, "Código do Produto": cod})
                    else:
                        dados.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Fixo": str_var, "Data Início": ini, "Data Fim": fim, "Similar": aplicar_similar})
                elif formato == "COMERCIAL":
                    if cod_op == "2":
                        dados.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod})
                        dados.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod})
                    else:
                        dados.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac, "Data Início": ini, "Data Fim": fim, "Similar": aplicar_similar, "ID Classificação": id_classificacao, "Somente Piso de Loja": somente_piso})
                elif formato == "PRICE":
                    dados.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_var, "Data Início": ini, "Data Fim": fim, "Similar": aplicar_similar, "Tipo Operação": cod_op})
                    dados.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_atac, "Data Início": ini, "Data Fim": fim, "Similar": aplicar_similar, "Tipo Operação": cod_op})
            except Exception:
                if n_filial == 0:
                    ignoradas.append(linha.strip())
    return dados, ignoradas
