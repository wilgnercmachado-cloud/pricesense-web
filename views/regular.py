"""Pricing Regular: mesa de precificação sobre a base do relatório Pricing GMAT3."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import gmat_reader as gr
from core import precificacao as pr
from core import profimetrics as pf
from core import reports
from ui import components as ui
from ui import theme

MESA = Path(__file__).resolve().parent.parent / "ui" / "mesa.html"
FILTROS = ["Estado", "Diretor regional", "Filial", "Departamento", "Comprador", "Categoria"]
LIMITE = 120_000


@st.cache_resource(show_spinner=False, max_entries=2)
def _base_publicada(caminho: str, partes: int, versao: str) -> tuple[pd.DataFrame, dict]:
    return gr.ler_de_gzip_ou_html(reports.baixar_conteudo({"arquivo_path": caminho, "partes": partes}))


@st.cache_resource(show_spinner=False, max_entries=2)
def _base_enviada(nome: str, tamanho: int, _conteudo: bytes) -> tuple[pd.DataFrame, dict]:
    return gr.ler_de_gzip_ou_html(_conteudo)


def _fonte() -> tuple[pd.DataFrame, dict] | None:
    candidatos = [r for r in reports.listar() if str(r.get("arquivo_path", "")).endswith((".gz", ".html"))]
    recentes = sorted(candidatos, key=lambda r: r.get("atualizado_em") or "", reverse=True)
    opcoes = {r["id"]: r for r in sorted(recentes, key=lambda r: "gmat" not in (r.get("titulo") or "").lower())}
    carregado = st.session_state.get("reg_carregado")
    with st.expander("Base de preços" + (f": {opcoes[carregado].get('titulo')}" if carregado in opcoes else ""),
                     expanded=carregado is None, icon=":material/database:"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        escolha = c1.selectbox("Relatório Pricing GMAT3 publicado na biblioteca", ["__upload__"] + list(opcoes),
                               index=1 if opcoes else 0, key="reg_fonte",
                               format_func=lambda k: "Enviar o HTML do relatório" if k == "__upload__" else
                               f"{opcoes[k].get('titulo')}  ({ui.data_curta(opcoes[k].get('atualizado_em'))})")
        if escolha == "__upload__":
            arq = st.file_uploader("HTML do relatório Pricing GMAT3", type=["html", "htm"], key="reg_html")
            if not arq:
                return None
            with st.spinner("Lendo a base do relatório"):
                return _base_enviada(arq.name, arq.size, arq.getvalue())
        if carregado != escolha:
            if not c2.button("Carregar base", type="primary", width="stretch", icon=":material/database:", key="reg_carregar"):
                return None
            st.session_state.reg_carregado = escolha
            st.rerun()
        rel = opcoes[escolha]
    try:
        with st.spinner("Baixando e lendo a base do relatório (alguns segundos na primeira vez)"):
            return _base_publicada(rel["arquivo_path"], int(rel.get("partes") or 1), str(rel.get("atualizado_em")))
    except gr.ErroLeitura as exc:
        st.error(str(exc), icon=":material/error:")
    except Exception as exc:
        st.error(f"Não foi possível ler esse relatório: {exc}", icon=":material/error:")
    return None


def _recorte(df: pd.DataFrame) -> tuple[pd.DataFrame, bool, bool]:
    with st.container(border=True, key="psc_reg_recorte"):
        cols = st.columns(len(FILTROS) + 2, vertical_alignment="bottom")
        mask = np.ones(len(df), dtype=bool)
        for n, col in enumerate(FILTROS):
            opcoes = sorted(str(v) for v in pd.unique(df[col].to_numpy()[mask]) if pd.notna(v))
            sel = cols[n].multiselect(col, opcoes, placeholder="Todos", key=f"reg_f_{col}")
            if sel:
                mask &= df[col].isin(sel).to_numpy()
        cesta = cols[-2].toggle("Só cesta", value=True, key="reg_cesta", help="Como na consulta de precificação: itens da cesta.")
        acoes = cols[-1].toggle("Sem ações", value=False, key="reg_sem_acao",
                                help="Tira da mesa encarte, mídia, vencimento e itens travados. Desligado, eles entram e caem na regra de corte.")
    return df[mask], cesta, acoes


def _tokens_css() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"


def _profimetrics() -> pd.DataFrame:
    regras, meta = pf.carregar()
    titulo = (f"Regras de margem (Profimetrics): {ui.numero(meta['linhas'])} regras, {meta['zonas']} zonas, atualizadas em {meta['atualizado_em']}"
              if meta else "Regras de margem (Profimetrics): nenhuma regra salva")
    with st.expander(titulo, icon=":material/tune:", expanded=False):
        st.caption("Envie a planilha Detalhes Produtos do Profimetrics. As regras ficam salvas no Supabase até o próximo envio: "
                   "o que vier no arquivo novo substitui a regra do mesmo produto na mesma zona, e o resto é mantido. "
                   "Cada filial puxa a regra da sua zona de preço (tabela filiais do Supabase).")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        arq = c1.file_uploader("Planilha Profimetrics (XLSX)", type=["xlsx", "xls"], key="reg_pf")
        if c2.button("Salvar no Supabase", type="primary", width="stretch", icon=":material/cloud_upload:", disabled=arq is None, key="reg_pf_salvar"):
            try:
                with st.spinner("Lendo a planilha e mesclando com as regras salvas"):
                    novo = pf.ler_planilha(arq)
                    r = pf.salvar(novo, st.session_state.get("usuario_logado", ""))
                st.toast(f"Regras salvas: {ui.numero(r['novas'])} novas, {ui.numero(r['substituidas'])} substituídas, "
                         f"{ui.numero(r['mantidas'])} mantidas. Total {ui.numero(r['total'])}.", icon=":material/check_circle:")
                st.rerun()
            except pf.ErroProfimetrics as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível salvar no Supabase: {exc}", icon=":material/error:")
    return regras


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding-left:1.4rem !important;"
            "padding-right:1.4rem !important}</style>")
    ui.cabecalho("Pricing Regular", "Mesa de precificação: cada filial contra o mercado, com as regras da consulta de precificação.")
    fonte = _fonte()
    if fonte is None:
        ui.vazio("Escolha a base", "Selecione o relatório Pricing GMAT3 publicado na biblioteca e clique em Carregar base, "
                                   "ou envie o HTML do relatório. Nada é alterado no ERP: o resultado é um arquivo de importação.")
        return
    df_all, meta = fonte
    regras = _profimetrics()
    recorte, so_cesta, sem_acao = _recorte(df_all)
    b = pr.base(recorte, so_cesta=so_cesta, ignorar_acoes=sem_acao, regras=regras)
    if b.empty:
        ui.vazio("Nada para precificar no recorte", "Amplie os filtros: são considerados itens com custo e com preço de mercado (pesquisa ou moda).")
        return
    if len(b) > LIMITE:
        st.warning(f"O recorte tem {ui.numero(len(b))} itens. Para a mesa responder na hora, escolha estado, diretor ou filiais "
                   f"até {ui.numero(LIMITE)} itens.", icon=":material/filter_alt:")
        return
    st.caption(f"Base de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}.")
    dados = pr.payload(b)
    chave = hashlib.md5((dados[:4000] + dados[-4000:] + str(len(dados))).encode()).hexdigest()[:12]
    html = (MESA.read_text(encoding="utf-8").replace("__FONTE__", theme.FONTE_URL).replace("__TOKENS__", _tokens_css())
            .replace("__CHAVE__", chave).replace("__DATA__", dados))
    components.html(html, height=1320, scrolling=False)
