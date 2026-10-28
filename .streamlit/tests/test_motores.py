"""Testes de regressão: lógica nova x trechos da versão original."""
import random
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import preco_bot as pb  # noqa: E402
from core import promo_engine as pe  # noqa: E402
from core import market_engine as me  # noqa: E402


def original_gerar(texto, filiais, formato, id_classificacao, cod_op, dt_inicio, dt_fim, aplicar_similar, somente_piso):
    linhas = texto.strip().split('\n'); dados_importacao = []
    for filial in filiais:
        id_fil = filial.split(" - ")[0]
        for linha in linhas:
            partes = [p.strip() for p in linha.split('\t')] if '\t' in linha else linha.split()
            if not partes or partes == [""]: continue
            cod = partes[0]
            try:
                var_bruto = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
                atac_bruto = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else var_bruto
                novo_var = pb.arredondar_varejo(var_bruto) if var_bruto > 0 else 0.0
                novo_atac = pb.arredondar_atacado(atac_bruto, novo_var) if atac_bruto > 0 else 0.0
                str_var = f"{novo_var:.2f}".replace('.', ',') if novo_var > 0 else ""
                str_atac = f"{novo_atac:.2f}".replace('.', ',') if novo_atac > 0 else ""
                if id_classificacao == "14": dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac})
                elif id_classificacao == "0":
                    if cod_op == "2": dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod})
                    else: dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Fixo": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar})
                elif formato == "COMERCIAL":
                    if cod_op == "2":
                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod})
                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod})
                    else: dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "ID Classificação": id_classificacao, "Somente Piso de Loja": somente_piso})
                elif formato == "PRICE":
                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
            except: pass
    return dados_importacao


def test_preco_bot():
    random.seed(1)
    linhas = []
    for i in range(400):
        v = round(random.uniform(0.5, 90), 2)
        a = round(v * random.uniform(0.8, 1.0), 2)
        linhas.append(f"{1000+i}\t{str(v).replace('.', ',')}\t{str(a).replace('.', ',')}")
    linhas += ["555\tabc\t1", "777 12,30", "888\t5,00", ""]
    texto = "\n".join(linhas)
    filiais = ["501 - A", "502 - B"]
    n = 0
    for formato in ["PRICE", "COMERCIAL"]:
        for idc in ["0", "14", "1", "5"]:
            for op in ["1", "2"]:
                args = (texto, filiais, formato, idc, op, date(2026, 10, 27), date(2026, 10, 30), "NAO", "SIM")
                novo, ignoradas = pb.gerar_importacao(*args)
                assert novo == original_gerar(*args), (formato, idc, op)
                assert ignoradas == ["555\tabc\t1"]
                n += 1
    print(f"Preço Bot: {n} combinações idênticas à versão original")


def test_promo():
    rows = []
    for camp, ini, fim, preco in [("Encarte A", "2026-10-20", "2026-10-26", "9,99"), ("Encarte B", "2026-10-25", "2026-10-31", "8,49")]:
        for prod in [1001, 1002, 1003]:
            rows.append({"CLUSTER/LOJA": "CL_SALVADOR", "SEQPRODUTO": prod, "PRECO_PROMOCIONAL": preco, "INICIO": ini, "FIM": fim})
    df_a = pd.DataFrame([r for r in rows if r["PRECO_PROMOCIONAL"] == "9,99"]); df_a["ARQUIVO ORIGEM"] = "Encarte A"
    df_b = pd.DataFrame([r for r in rows if r["PRECO_PROMOCIONAL"] == "8,49"] + [{"CLUSTER/LOJA": "CL_X", "SEQPRODUTO": 2000, "PRECO_PROMOCIONAL": "R$ 3,99", "INICIO": "2026-11-01", "FIM": "2026-11-02"}]); df_b["ARQUIVO ORIGEM"] = "Encarte B"
    # preço divergente na mesma campanha
    extra = pd.DataFrame([{"CLUSTER/LOJA": "CL_SALVADOR", "SEQPRODUTO": 1009, "PRECO_PROMOCIONAL": p, "INICIO": "2026-11-05", "FIM": "2026-11-06", "ARQUIVO ORIGEM": "Encarte C"} for p in ("1,00", "2,00")])
    clusters = pd.DataFrame({"CLUSTER": ["CL_SALVADOR", "CL_SALVADOR"], "ID FILIAL": [500, 501]})
    res = pe.processar([df_a, df_b, extra], clusters, {"500": "500 - Paralela BA", "501": "501 - Feira BA"})
    df = res["df"]
    assert res["clusters_fora"] == ["CL_X"], res["clusters_fora"]
    assert set(df.loc[df["SEQPRODUTO"] == 1001, "Status Sistema"]) == {"CRÍTICO - CONFLITOS DE DATAS"}
    assert set(df.loc[df["SEQPRODUTO"] == 1009, "Status Sistema"]) == {"CRÍTICO - ERRO DE PREÇO"}
    assert set(df.loc[df["SEQPRODUTO"] == 2000, "Status Sistema"]) == {"VÁLIDO"}
    assert set(df["ID FILIAL"].astype(str)) == {"500", "501", "CL_X"}, set(df["ID FILIAL"].astype(str))
    txt = pe.texto_importacao(df[df["SEQPRODUTO"] == 2000], True)
    assert txt.splitlines() == ["CL_X\t1\t1\t7\t2000\t3,99\t01/11/2026\t02/11/2026", "CL_X\t2\t1\t7\t2000\t3,99\t01/11/2026\t02/11/2026"], txt
    a = pd.Series(["01/11/2026", None]); b = pd.Series(["01/11/2026", None], dtype=object)
    assert not pe.linhas_diferentes(a, b).any()
    print("Pricing Promo: conflitos de data, erro de preço, clusters e exportação OK")


def gerar_pesquisa(n=1200, seed=3):
    rng = np.random.default_rng(seed)
    concs = ["900 - ATACADAO PARALELA", "901 - ASSAI IGUATEMI", "902 - GBARBOSA CENTRO", "903 - ATAKAREJO LAURO"]
    tipos = ["REGULAR", "PROMOCAO", "PONTO EXTRA", "VALIDADE"]
    linhas = []
    for i in range(n):
        prod = 1000 + int(rng.integers(0, 8))
        base = 5 + (prod - 1000) * 3.1
        var = round(base * rng.choice([0.95, 1.0, 1.0, 1.05, 0.9]), 2)
        linhas.append({"FILIAL": rng.choice(["500 - PARALELA", "501 - FEIRA"]), "FILIALCONCORRENTE": rng.choice(concs),
                       "PESQUISADATA": f"{int(rng.integers(1, 28)):02d}/10/2026", "CUSTOMEDIO": str(round(base * 0.78, 2)).replace(".", ","),
                       "VLR. VAREJO PDV": str(round(base * 1.02, 2)).replace(".", ","), "VLR. ATACADO PDV": str(round(base * 0.97, 2)).replace(".", ","),
                       "VLR. VAREJO CONC.": str(var).replace(".", ","), "VLR. ATACADO CONC.": str(round(var * 0.95, 2)).replace(".", ",") if i % 5 else "0",
                       "PRODUTO": f"{prod} - PRODUTO {prod}", "TIPO": rng.choice(tipos)})
    linhas.append({**linhas[0], "FILIAL": "TOTAL"})
    return pd.DataFrame(linhas).astype(str)


def test_mercado():
    df = me.padronizar_colunas(gerar_pesquisa())
    def produtos(cods): return [{"id_produto": c, "id_fornecedor": 10 + c % 3, "categoria_comercial": "MERCEARIA"} for c in cods if c < 1006]
    def forns(ids): return [{"id_fornecedor": i, "nome_grupo_empresarial": f"GRUPO {i}"} for i in ids]
    df, stats = me.enriquecer(df, produtos, forns)
    assert stats["classificadas"] > 0 and stats["classificadas"] < len(df)
    df = me.preparar(df, pd.DataFrame())
    assert not df["FILIAL"].str.contains("TOTAL").any()
    f = me.aplicar_filtros(df, {"produto": "Todos", "filial": "Todas", "categoria": "Todas", "grupo": "Todos", "concorrentes": [], "tipos": [], "periodo": None})
    k = me.indicadores(f)
    assert k["moda_var"] > 0 and k["qtd_moda"] > 0 and k["min"] <= k["max"]
    for m in me.MODELOS:
        tab, msg = me.extrair(m, f)
        assert tab is not None and len(tab) > 0, (m, msg)
        assert tab[["Filial", "Produto"]].duplicated().sum() == 0, m
    assert len(me.serie_menor_preco(f)) > 0
    assert me.formatar_brl(1234.5) == "R$ 1.234,50"
    print(f"Pesquisa: {len(df)} linhas, {len(f)} após filtros, 4 modelos gerados sem duplicidade")


if __name__ == "__main__":
    test_preco_bot(); test_promo(); test_mercado()
