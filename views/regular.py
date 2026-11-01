"""Pricing Regular: mesa de precificação sobre a base do relatório Competitividade Pricing GMAT."""
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

RAIZ = Path(__file__).resolve().parent.parent
MESA = RAIZ / "ui" / "mesa.html"
XLSX = RAIZ / "assets" / "vendor" / "xlsx.mini.min.js"
FILTROS = ["Estado", "Diretor regional", "Filial", "Departamento", "Comprador", "Categoria"]
PADRAO = {"cesta": True, "sem_acoes": False, "pesquisa": "Com pesquisa", **{f: [] for f in FILTROS}}
LIMITE = 120_000


@st.cache_resource(show_spinner=False, max_entries=2)
def _base_publicada(caminho: str, partes: int, versao: str) -> tuple[pd.DataFrame, dict]:
    return gr.ler_de_gzip_ou_html(reports.baixar_conteudo({"arquivo_path": caminho, "partes": partes}))


def _relatorio_padrao() -> dict | None:
    """Sempre o Competitividade Pricing GMAT mais recente da biblioteca."""
    todos = sorted(reports.listar(), key=lambda r: r.get("atualizado_em") or "", reverse=True)
    titulo = lambda r: (r.get("titulo") or "").lower()
    return (next((r for r in todos if "competitividade pricing gmat" in titulo(r)), None)
            or next((r for r in todos if "gmat" in titulo(r)), None))


def _fonte() -> tuple[pd.DataFrame, dict, dict] | None:
    rel = _relatorio_padrao()
    if rel is None:
        ui.vazio("Base não encontrada", "Publique o relatório Competitividade Pricing GMAT na biblioteca de relatórios. "
                                        "A mesa usa sempre a versão mais recente dele.")
        return None
    try:
        with st.spinner("Lendo a base do Competitividade Pricing GMAT (alguns segundos na primeira vez)"):
            df, meta = _base_publicada(rel["arquivo_path"], int(rel.get("partes") or 1), str(rel.get("atualizado_em")))
        return df, meta, rel
    except gr.ErroLeitura as exc:
        st.error(str(exc), icon=":material/error:")
    except Exception as exc:
        st.error(f"Não foi possível ler o relatório: {exc}", icon=":material/error:")
    return None


def _filtros(df: pd.DataFrame) -> dict:
    """Filtros recolhidos num botão, como no relatório: abre, escolhe e aplica."""
    atual = st.session_state.setdefault("reg_filtros", dict(PADRAO))
    ativos = sum(bool(atual[f]) for f in FILTROS) + (atual["pesquisa"] != "Com pesquisa") + (not atual["cesta"]) + atual["sem_acoes"]
    with st.popover(f"Filtros{f' ({ativos})' if ativos else ''}", icon=":material/filter_list:"):
        with st.form("reg_form_filtros", border=False):
            pesquisa = st.segmented_control("Itens", ["Com pesquisa", "Sem pesquisa"], default=atual["pesquisa"], required=True,
                                            help="Sem pesquisa: o varejo vai para a margem objetiva e o atacado sai do objetivo com a base de redução.")
            c1, c2 = st.columns(2)
            sel = {}
            for n, col in enumerate(FILTROS):
                opcoes = sorted(str(v) for v in pd.unique(df[col]) if pd.notna(v))
                sel[col] = (c1 if n % 2 == 0 else c2).multiselect(col, opcoes, default=[v for v in atual[col] if v in opcoes], placeholder="Todos")
            c3, c4 = st.columns(2)
            cesta = c3.toggle("Só cesta", value=atual["cesta"])
            sem_acoes = c4.toggle("Sem itens em ação", value=atual["sem_acoes"],
                                  help="Tira encarte, mídia, vencimento e travados. Desligado, eles entram e caem na regra de corte.")
            c5, c6 = st.columns(2)
            aplicar = c5.form_submit_button("Aplicar", type="primary", width="stretch", icon=":material/check:")
            limpar = c6.form_submit_button("Limpar", width="stretch", icon=":material/filter_alt_off:")
        if aplicar:
            st.session_state.reg_filtros = {**sel, "cesta": cesta, "sem_acoes": sem_acoes, "pesquisa": pesquisa}
            st.rerun()
        if limpar:
            st.session_state.reg_filtros = dict(PADRAO)
            st.rerun()
    return st.session_state.reg_filtros


def _profimetrics() -> pd.DataFrame:
    regras, meta = pf.carregar()
    rotulo = f"Regras de margem ({ui.numero(meta['linhas'])})" if meta else "Regras de margem"
    with st.popover(rotulo, icon=":material/tune:"):
        if meta:
            st.caption(f"{ui.numero(meta['linhas'])} regras do Profimetrics, {meta['zonas']} zonas, {ui.numero(meta['produtos'])} produtos. "
                       f"Atualizadas em {meta['atualizado_em']}.")
        else:
            st.caption("Nenhuma regra salva: a mesa usa margem objetiva de 10% e máxima de 30%.")
        st.caption("Envie a planilha Detalhes Produtos do Profimetrics. Ela fica salva no Supabase até o próximo envio: "
                   "o arquivo novo substitui a regra do mesmo produto na mesma zona, e o resto é mantido.")
        arq = st.file_uploader("Planilha Profimetrics (XLSX)", type=["xlsx", "xls"], key="reg_pf", label_visibility="collapsed")
        if st.button("Salvar no Supabase", type="primary", width="stretch", icon=":material/cloud_upload:", disabled=arq is None, key="reg_pf_salvar"):
            try:
                with st.spinner("Lendo a planilha e mesclando com as regras salvas"):
                    r = pf.salvar(pf.ler_planilha(arq), st.session_state.get("usuario_logado", ""))
                st.toast(f"Regras salvas: {ui.numero(r['novas'])} novas, {ui.numero(r['substituidas'])} substituídas, "
                         f"{ui.numero(r['mantidas'])} mantidas.", icon=":material/check_circle:")
                st.rerun()
            except pf.ErroProfimetrics as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível salvar no Supabase: {exc}", icon=":material/error:")
    return regras


def _tokens_css() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"


def _xlsx_js() -> str:
    try:
        return "<script>" + XLSX.read_text(encoding="utf-8").replace("</script", "<\\/script") + "</script>"
    except OSError:
        return '<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.mini.min.js"></script>'


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding-left:1.4rem !important;"
            "padding-right:1.4rem !important;padding-top:4.6rem !important}"
            ".ps-head h1{font-size:1.9rem !important}</style>")
    ui.cabecalho("Pricing Regular")
    fonte = _fonte()
    if fonte is None:
        return
    df_all, meta, rel = fonte

    with st.container(horizontal=True, vertical_alignment="center", gap="small"):
        f = _filtros(df_all)
        regras = _profimetrics()
        st.caption(f"{rel.get('titulo')}: base de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}")

    mask = np.ones(len(df_all), dtype=bool)
    for col in FILTROS:
        if f[col]:
            mask &= df_all[col].isin(f[col]).to_numpy()
    b = pr.base(df_all[mask], so_cesta=f["cesta"], ignorar_acoes=f["sem_acoes"], regras=regras,
                com_pesquisa=f["pesquisa"] == "Com pesquisa")
    if b.empty:
        ui.vazio("Nada para precificar com esses filtros", "Abra os filtros e amplie a seleção.")
        return
    if len(b) > LIMITE:
        st.warning(f"A seleção tem {ui.numero(len(b))} itens. Abra os filtros e escolha estado, diretor ou filiais "
                   f"para ficar abaixo de {ui.numero(LIMITE)} e a mesa responder na hora.", icon=":material/filter_alt:")
        return
    dados = pr.payload(b, meta.get("hist"))
    chave = hashlib.md5((dados[:4000] + dados[-4000:] + str(len(dados))).encode()).hexdigest()[:12]
    html = (MESA.read_text(encoding="utf-8").replace("__FONTE__", theme.FONTE_URL).replace("__TOKENS__", _tokens_css())
            .replace("__CHAVE__", chave).replace("__XLSX__", _xlsx_js()).replace("__DATA__", dados))
    components.html(html, height=1340, scrolling=False)
