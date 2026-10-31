"""Pricing Regular: precificação sobre a base completa do relatório Pricing GMAT3."""
from __future__ import annotations

import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from core import gmat_pricing as gp
from core import gmat_reader as gr
from core import reports
from ui import components as ui

FILTROS = [("Estado", "Estado"), ("Diretor regional", "Diretor regional"), ("Filial", "Filial"),
           ("Departamento", "Departamento"), ("Comprador", "Comprador"), ("Categoria", "Categoria"), ("Cesta", "Cesta")]
VISOES = ["Estado", "Diretor regional", "Filial", "Departamento", "Comprador", "Categoria"]
MAX_GRADE = 2000


@st.cache_resource(show_spinner=False, max_entries=2)
def _base_publicada(caminho: str, partes: int, versao: str) -> tuple[pd.DataFrame, dict]:
    rel = {"arquivo_path": caminho, "partes": partes}
    return gr.ler_de_gzip_ou_html(reports.baixar_conteudo(rel))


@st.cache_resource(show_spinner=False, max_entries=2)
def _base_enviada(nome: str, tamanho: int, _conteudo: bytes) -> tuple[pd.DataFrame, dict]:
    return gr.ler_de_gzip_ou_html(_conteudo)


def _fonte() -> tuple[pd.DataFrame, dict] | None:
    candidatos = [r for r in reports.listar() if str(r.get("arquivo_path", "")).endswith((".gz", ".html"))]
    recentes = sorted(candidatos, key=lambda r: r.get("atualizado_em") or "", reverse=True)
    preferidos = sorted(recentes, key=lambda r: "gmat" not in (r.get("titulo") or "").lower())  # GMAT primeiro, mais recente antes
    with st.container(border=True, key="psc_reg_fonte"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        opcoes = {r["id"]: r for r in preferidos}
        escolha = c1.selectbox("Base de preços (relatório publicado na biblioteca)", ["__upload__"] + list(opcoes),
                               index=1 if opcoes else 0, key="reg_fonte",
                               format_func=lambda k: "Enviar o HTML do relatório" if k == "__upload__" else
                               f"{opcoes[k].get('titulo')}  ({ui.data_curta(opcoes[k].get('atualizado_em'))})")
        if escolha == "__upload__":
            arq = st.file_uploader("HTML do relatório Pricing GMAT3", type=["html", "htm"], key="reg_html")
            if not arq:
                return None
            with st.spinner("Lendo a base do relatório"):
                return _base_enviada(arq.name, arq.size, arq.getvalue())
        rel = opcoes[escolha]
        if not st.session_state.get("reg_carregado") == escolha:
            if not c2.button("Carregar base", type="primary", width="stretch", icon=":material/database:", key="reg_carregar"):
                st.caption("A base completa tem centenas de milhares de linhas. Carregue para começar.")
                return None
            st.session_state.reg_carregado = escolha
        try:
            with st.spinner("Baixando e lendo a base do relatório (leva alguns segundos na primeira vez)"):
                return _base_publicada(rel["arquivo_path"], int(rel.get("partes") or 1), str(rel.get("atualizado_em")))
        except gr.ErroLeitura as exc:
            st.error(str(exc), icon=":material/error:")
        except Exception as exc:
            st.error(f"Não foi possível ler esse relatório: {exc}", icon=":material/error:")
        return None


def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
    with st.container(border=True, key="psc_reg_filtros"):
        cols = st.columns(4)
        mask = np.ones(len(df), dtype=bool)
        for n, (rotulo, col) in enumerate(FILTROS):
            opcoes = sorted(str(v) for v in pd.unique(df[col].to_numpy()[mask]) if pd.notna(v))
            sel = cols[n % 4].multiselect(rotulo, opcoes, placeholder="Todos", key=f"reg_f_{col}")
            if sel:
                mask &= df[col].isin(sel).to_numpy()
        busca = cols[3].text_input("Produto", placeholder="Código ou nome", key="reg_busca")
        if busca.strip():
            mask &= df["Produto"].astype(str).str.contains(busca.strip(), case=False, regex=False).to_numpy()
    return df[mask]


def _regras() -> dict:
    with st.container(border=True, key="psc_reg_regras"):
        c1, c2, c3, c4 = st.columns(4)
        centavos = c1.number_input("Abaixo do mercado (R$)", 0.0, 1.0, 0.01, 0.01, format="%.2f", key="reg_cent")
        margem_min = c2.number_input("Margem mínima (%)", -50.0, 30.0, -15.0, 1.0, format="%.0f", key="reg_mmin",
                                     help="Regra do relatório: o mercado não é acompanhado na baixa quando deixaria a margem abaixo disso.")
        zona = c3.slider("Zona neutra do IP (%)", 90, 110, (98, 101), key="reg_zona",
                         help="Regra do relatório: só sobe com IP abaixo do início e só baixa com IP acima do fim.")
        direcao = c4.segmented_control("Direção", ["Subir e baixar", "Só baixar", "Só subir"], default="Subir e baixar",
                                       required=True, key="reg_dir")
        c5, c6, c7, c8 = st.columns(4)
        abaixo = c5.segmented_control("Mercado abaixo da mínima", ["Não acompanhar", "Baixar até o piso"],
                                      default="Não acompanhar", required=True, key="reg_abx")
        arred = c6.toggle("Arredondar pela regra da companhia", value=False, key="reg_arr",
                          help="Desligado: preço exato (mercado − R$ 0,01). Ligado: aplica a régua de gôndola do Preço Bot.")
        acoes = c7.toggle("Incluir itens em ação (encarte, mídia, vencimento)", value=False, key="reg_acoes")
        cesta = c8.toggle("Não subir itens da cesta", value=False, key="reg_cesta",
                          help="Itens da cesta costumam ficar abaixo do mercado de propósito, às vezes abaixo do custo.")
    return dict(proteger_cesta=cesta, centavos=float(centavos), margem_min=margem_min / 100, piso_ip=zona[0] / 100, teto_ip=zona[1] / 100,
                direcao=direcao, abaixo_minima=abaixo, arredondar=arred, incluir_acoes=acoes)


def _status(resumo: dict) -> None:
    cores = {"Mercado igual": "var(--ps-primary)", "Mercado maior": "var(--ps-up)", "Mercado menor": "var(--ps-down)",
             "Mercado abaixo da mínima": "var(--ps-amber)", "Sem pesquisa": "var(--ps-faint)"}
    tot = max(sum(resumo["status"].values()), 1)
    barras = "".join(f"<span style='flex:{v};background:{cores[k]}'></span>" for k, v in resumo["status"].items() if v)
    leg = "".join(f"<span><i style='background:{cores[k]}'></i>{k} <b>{ui.numero(v)}</b> ({f'{100 * v / tot:.0f}'}%)</span>"
                  for k, v in resumo["status"].items())
    st.html(f"<div class='ps-split'><div class='ps-split-bar'>{barras}</div><div class='ps-split-legend'>{leg}</div></div>")


def _codigo(s: pd.Series) -> pd.Series:
    return s.astype(str).str.split(" - ").str[0].str.strip()


def render() -> None:
    ui.cabecalho("Pricing Regular", "Precificação de cada filial contra o menor preço do mercado, com as regras do relatório Pricing GMAT3.")
    fonte = _fonte()
    if fonte is None:
        ui.vazio("Escolha a base", "Selecione o relatório Pricing GMAT3 publicado na biblioteca e clique em Carregar base, "
                                   "ou envie o HTML do relatório. Nada é alterado no ERP: o resultado é um arquivo de importação.")
        return
    df_all, meta = fonte
    st.caption(f"Base de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}: "
               f"{ui.numero(meta['linhas'])} linhas, {meta['filiais']} filiais, {ui.numero(meta['produtos'])} produtos.")

    ui.secao("Recorte")
    df = _filtrar(df_all)
    if df.empty:
        ui.vazio("Nada no recorte", "Remova algum filtro.")
        return
    ui.secao("Regras de preço", "Padrão: varejo e atacado R$ 0,01 abaixo do menor preço do mercado, respeitando a margem mínima de −15%.")
    regras = _regras()
    res = gp.precificar(df, **regras)
    k = gp.resumo(df, res)

    fmt = lambda v, d=1: f"{v:.{d}f}".replace(".", ",") if v == v else "-"
    ui.secao("Resultado da rodada", f"{ui.numero(k['linhas'])} linhas, {ui.numero(k['skus'])} produtos, {k['filiais']} filiais")
    ui.etiquetas([
        ui.etiqueta("Preços que sobem", k["sobem"], tipo="numero", tom="ok"),
        ui.etiqueta("Preços que baixam", k["baixam"], tipo="numero", tom="alert"),
        ui.etiqueta("IP (nosso ÷ menor do mercado)", 100 * k["ip_novo"], tipo="indice", tom="primary",
                    nota=f"Hoje {fmt(100 * k['ip_atual'])}", variacao=100 * (k["ip_novo"] - k["ip_atual"]), inverter=True),
        ui.etiqueta("Margem ponderada", 100 * k["margem_nova"], tipo="pct", tom="promo",
                    nota=f"Hoje {fmt(100 * k['margem_atual'])}%", variacao=100 * (k["margem_nova"] - k["margem_atual"])),
        ui.etiqueta("Lucro adicional por mês", k["ganho"], tom="ok", nota="Nas subidas, pelo volume atual"),
        ui.etiqueta("Investimento por mês", k["investimento"], tom="alert", nota="Nas baixas, pelo volume atual"),
        ui.etiqueta("Travados pela margem de −15%", k["bloqueados"], tipo="numero", nota="Mercado abaixo da mínima"),
    ])
    st.html("<div style='height:10px'></div>")
    _status(k)

    d = df.join(res)
    ui.secao("Onde está o impacto")
    with st.container(border=True, key="psc_reg_visao"):
        visao = st.segmented_control("Ver por", VISOES, default="Estado", required=True, key="reg_visao")
        d["_w"] = np.where(d["un_mes"] > 0, d["un_mes"], 1.0)
        tem = (d["mk"] > 0) & (d["vm"] > 0)
        g = d.assign(_vmw=np.where(tem, d["vm"] * d["_w"], 0), _nvw=np.where(tem, d["novo_varejo"] * d["_w"], 0),
                     _mkw=np.where(tem, d["mk"] * d["_w"], 0), _sobe=d["acao"] == "Subir", _baixa=d["acao"] == "Baixar",
                     _ganho=d["impacto_mes"].clip(lower=0), _inv=(-d["impacto_mes"]).clip(lower=0))
        t = g.groupby(visao, observed=True).agg(Linhas=("Produto", "size"), Sobem=("_sobe", "sum"), Baixam=("_baixa", "sum"),
                                                 vmw=("_vmw", "sum"), nvw=("_nvw", "sum"), mkw=("_mkw", "sum"),
                                                 Ganho=("_ganho", "sum"), Investimento=("_inv", "sum")).reset_index()
        t["IP atual"] = 100 * t["vmw"] / t["mkw"].replace(0, np.nan)
        t["IP novo"] = 100 * t["nvw"] / t["mkw"].replace(0, np.nan)
        t["Saldo/mês"] = t["Ganho"] - t["Investimento"]
        t = t.drop(columns=["vmw", "nvw", "mkw"]).sort_values("Saldo/mês", ascending=False)
        st.dataframe(t, hide_index=True, width="stretch", height=min(420, 40 + 35 * len(t)),
                     column_config={"IP atual": st.column_config.NumberColumn(format="%.1f"), "IP novo": st.column_config.NumberColumn(format="%.1f"),
                                    "Ganho": st.column_config.NumberColumn("Lucro adicional/mês", format="R$ %.0f"),
                                    "Investimento": st.column_config.NumberColumn("Investimento/mês", format="R$ %.0f"),
                                    "Saldo/mês": st.column_config.NumberColumn(format="R$ %.0f")})

    ui.secao("Preços da rodada", f"Os {MAX_GRADE} itens de maior impacto; ajuste o preço final se precisar. A exportação leva todos.")
    mudam = d[d["acao"] != "Manter"].copy()
    mudam["_abs"] = mudam["impacto_mes"].abs()
    topo = mudam.nlargest(MAX_GRADE, "_abs")
    cols = ["Estado", "Filial", "Produto", "Classificação", "cu", "vm", "am", "mk", "amk", "Concorrente menor", "ip_atual",
            "acao", "motivo", "novo_varejo", "novo_atacado", "margem_atual", "margem_nova", "impacto_mes"]
    nomes = {"cu": "Custo", "vm": "Varejo atual", "am": "Atacado atual", "mk": "Menor varejo mercado", "amk": "Menor atacado mercado",
             "ip_atual": "IP atual", "acao": "Ação", "motivo": "Motivo", "novo_varejo": "Novo varejo", "novo_atacado": "Novo atacado",
             "margem_atual": "Margem atual", "margem_nova": "Nova margem", "impacto_mes": "Impacto/mês"}
    grade = topo[cols].rename(columns=nomes)
    for c in ["Margem atual", "Nova margem"]:
        grade[c] = grade[c] * 100
    grade["IP atual"] = grade["IP atual"] * 100
    moeda = st.column_config.NumberColumn(format="R$ %.2f")
    editado = st.data_editor(
        grade, hide_index=True, width="stretch", height=520, key="reg_grade",
        disabled=[c for c in grade.columns if c not in ("Novo varejo", "Novo atacado")],
        column_config={**{c: moeda for c in ["Custo", "Varejo atual", "Atacado atual", "Menor varejo mercado", "Menor atacado mercado",
                                             "Novo varejo", "Novo atacado"]},
                       "IP atual": st.column_config.NumberColumn(format="%.1f"), "Margem atual": st.column_config.NumberColumn(format="%.1f%%"),
                       "Nova margem": st.column_config.NumberColumn(format="%.1f%%"), "Impacto/mês": st.column_config.NumberColumn(format="R$ %.0f")})
    mudam.loc[editado.index, "novo_varejo"] = editado["Novo varejo"].to_numpy()
    mudam.loc[editado.index, "novo_atacado"] = editado["Novo atacado"].to_numpy()

    ui.secao("Exportar", f"{ui.numero(len(mudam))} preços mudam nesta rodada.")
    with st.container(border=True, key="psc_reg_export"):
        f2 = lambda s: s.map(lambda v: f"{v:.2f}".replace(".", ",") if pd.notna(v) and v > 0 else "")
        erp = pd.DataFrame({"Código da Filial": _codigo(mudam["Filial"]), "Código do Produto": _codigo(mudam["Produto"]),
                            "Preço Varejo": f2(mudam["novo_varejo"]), "Preço Atacado": f2(mudam["novo_atacado"])})
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("Importação ERP (TXT)", data=erp.to_csv(sep="\t", index=False, header=False).encode("utf-8"),
                               file_name=f"PriceSense_Regular_ERP_{datetime.now():%d-%m-%Y}.txt", mime="text/plain",
                               type="primary", width="stretch", icon=":material/upload:",
                               help="Layout de preço regular do Preço Bot: filial, produto, varejo e atacado.")
        with c2:
            analise = mudam.drop(columns=["_abs", "_w"], errors="ignore")
            st.download_button("Análise completa (CSV)", data=analise.to_csv(sep=";", index=False, decimal=",").encode("utf-8-sig"),
                               file_name=f"PriceSense_Regular_Analise_{datetime.now():%d-%m-%Y}.csv", mime="text/csv",
                               width="stretch", icon=":material/table_view:")
        with c3:
            if len(erp) <= 20000:
                ui.botao_copiar(erp.to_csv(sep="\t", index=False, header=False), "Copiar importação", "Importação copiada")
            else:
                st.caption("Acima de 20 mil linhas, use o arquivo TXT: copiar tanto texto trava o navegador.")
