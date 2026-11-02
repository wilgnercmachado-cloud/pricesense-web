"""Pricing Promo: PromoMetrics, painel de análise de encartes (validação, conflitos, competitividade e importação)."""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import db, promo_engine as pe
from ui import components as ui
from ui import theme

RAIZ = Path(__file__).resolve().parent.parent
_PROMO = components.declare_component("promo_metrics", path=str(RAIZ / "ui" / "promo_comp"))


def _carregar(arquivos) -> None:
    nomes = sorted(f.name for f in arquivos)
    if st.session_state.get("promo_arquivos") == nomes:
        return
    with st.spinner("Lendo planilhas e abrindo clusters em filiais"):
        dfs, falhas = pe.ler_planilhas(arquivos)
        if falhas:
            st.warning(f"Não foi possível ler: {', '.join(falhas)}.", icon=":material/warning:")
        if not dfs:
            return
        try:
            res = pe.processar(dfs, db.clusters(), db.mapa_lojas())
        except pe.ArquivoSemDatas:
            st.error("As planilhas não têm as colunas INICIO e FIM. Se for um arquivo da pesquisa de mercado, "
                     "envie-o na página Pesquisa de Mercado.", icon=":material/error:")
            st.stop()
    st.session_state.df_promo_processado = res["df"]
    st.session_state.clusters_desconhecidos = res["clusters_fora"]
    st.session_state.campanhas_vencidas = res["vencidas"]
    st.session_state.promo_arquivos = nomes


def _clusters_fora() -> None:
    fora = st.session_state.get("clusters_desconhecidos", [])
    if not fora:
        return
    with st.popover(str(len(fora)), icon=":material/link_off:", help="Clusters sem filial mapeada"):
        st.caption(f"{len(fora)} cluster(s) não estão mapeados para filiais: {', '.join(map(str, fora[:12]))}{'…' if len(fora) > 12 else ''}")
        with st.form("form_cluster", border=False):
            cluster = st.selectbox("Cluster", fora)
            filial = st.text_input("ID da filial", placeholder="Ex.: 544")
            if st.form_submit_button("Pedir mapeamento ao administrador", type="primary", width="stretch"):
                if not filial.strip():
                    st.error("Informe o ID da filial.")
                else:
                    try:
                        db.solicitar_cluster(cluster, filial.strip(), st.session_state.usuario_logado)
                        st.success("Pedido enviado. Um administrador vai revisar o mapeamento.")
                    except Exception:
                        st.warning("A tabela solicitacoes_cluster ainda não existe no Supabase. Rode supabase/migrations.sql.")


def _col(df: pd.DataFrame, *nomes: str):
    norm = {re.sub(r"[^A-Z]", "", str(c).upper()): c for c in df.columns}
    for n in nomes:
        c = norm.get(re.sub(r"[^A-Z]", "", n.upper()))
        if c is not None:
            return c
    return None


def _cod(v) -> str:
    m = re.match(r"\s*(\d+)", str(v))
    return m.group(1) if m else str(v).strip()


@st.cache_data(show_spinner=False, max_entries=4)
def _referencias(chaves: tuple[str, ...], versao: str) -> dict:
    """Custo, preços atuais, mercado e volume da base do Competitividade Pricing GMAT para cada filial|produto da campanha."""
    try:
        from views import regular
        rel = regular._relatorio_padrao()
        if rel is None:
            return {}
        df, _ = regular._base_publicada(rel["arquivo_path"], int(rel.get("partes") or 1), str(rel.get("atualizado_em")), regular.gr.VERSAO)
    except Exception:
        return {}
    prods = {k.split("|")[1] for k in chaves}
    cats_p = df["Produto"].cat.categories
    pcod = pd.Series([_cod(c) for c in cats_p])
    df = df[df["Produto"].cat.codes.isin(np.where(pcod.isin(prods))[0])]
    if df.empty:
        return {}
    fcod = df["Filial"].astype(str).map(_cod)
    pc = df["Produto"].astype(str).map(_cod)
    chave = fcod + "|" + pc
    df = df.assign(chave_ps=chave.to_numpy())
    df = df[df["chave_ps"].isin(set(chaves))]
    vm = df["vm"].astype(float)
    un = np.where((df["venda"] > 0) & (vm > 0), df["venda"] / vm.where(vm > 0, 1), 0)
    out = {}
    for r, u in zip(df.itertuples(index=False), un):
        out[r.chave_ps] = [round(float(r.cu), 2), round(float(r.vm), 2), round(float(r.am), 2), round(float(r.mk), 2) if r.mk > 0 else 0,
                     str(getattr(r, "Comprador", "")), str(getattr(r, "Categoria", "")), str(r.Produto), round(float(u), 1)]
    return out


def _payload(df: pd.DataFrame) -> tuple[str, str]:
    c_desc = _col(df, "DESCRICAO", "DESCRIÇÃO", "DESC PRODUTO", "DESCRICAO PRODUTO", "NOME PRODUTO", "PRODUTO")
    c_of = _col(df, "TIPO OFERTA", "TIPO DE OFERTA", "TIPO_OFERTA", "OFERTA")
    camp = pd.Categorical(df["ARQUIVO ORIGEM"].astype(str))
    fil = df["ID FILIAL"].map(_cod)
    prod = df["SEQPRODUTO"].map(_cod) if "SEQPRODUTO" in df else pd.Series([""] * len(df))
    chaves = tuple(sorted(set(fil + "|" + prod)))
    rel_versao = ""
    try:
        from views import regular
        r = regular._relatorio_padrao()
        rel_versao = f"{r.get('id')}:{r.get('atualizado_em')}" if r else ""
    except Exception:
        pass
    with st.spinner("Cruzando a campanha com custo, preço atual e mercado"):
        ref = _referencias(chaves, rel_versao)
    iso = lambda s: pd.to_datetime(s, format="%d/%m/%Y", errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    filn = df["FILIAL ABREV"].astype(str)
    desc = df[c_desc].astype(str) if c_desc and c_desc != "SEQPRODUTO" else pd.Series([""] * len(df), index=df.index)
    refs = [ref.get(f"{a}|{b}") for a, b in zip(fil, prod)]
    dados = {
        "campanhas": list(camp.categories), "ci": camp.codes.astype(int).tolist(),
        "fil": fil.tolist(), "filn": filn.tolist(), "prod": prod.tolist(),
        "desc": [d if d and d.lower() != "nan" else (r[6] if r else "") for d, r in zip(desc.tolist(), refs)],
        "preco": [round(float(x), 2) for x in df["PRECO_NUM"]], "ini": iso(df["INICIO"]).tolist(), "fim": iso(df["FIM"]).tolist(),
        "oferta": [str(x) if str(x) not in ("nan", "None") else "" for x in (df[c_of] if c_of else [""] * len(df))],
        "ref": [r[:6] + [r[7]] if r else None for r in refs],
        "tem_ref": bool(ref),
    }
    bruto = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode()
    texto = base64.b64encode(gzip.compress(bruto, 6)).decode()
    chave = hashlib.md5(("|".join(st.session_state.get("promo_arquivos", [])) + str(len(df))).encode()).hexdigest()[:12]
    return texto, chave


def _tipos_oferta() -> list[str]:
    try:
        return [str(x) for x in db.tipos_midia()]
    except Exception:
        return []


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            ".st-key-promo_topo{position:fixed !important;top:11px;right:122px;z-index:1000002;width:auto !important;gap:6px}"
            ".st-key-promo_topo [data-testid='stPopover'] button{height:38px;min-height:38px;border-radius:19px;padding:0 12px;"
            "background:var(--ps-surface);border:1px solid var(--ps-line)}"
            "[data-testid='stMainBlockContainer'] [data-testid='stVerticalBlock']{gap:.4rem}</style>")
    df = st.session_state.get("df_promo_processado")
    if df is None:
        ui.cabecalho("Pricing Promo", "Envie as planilhas do encarte: o PromoMetrics abre os clusters, valida preço e período "
                                      "e cruza cada item com custo, preço atual e mercado.")
        arquivos = st.file_uploader("Planilhas de encarte (XLSX, XLS ou CSV com ponto e vírgula)", accept_multiple_files=True,
                                    type=["xlsx", "xls", "csv"], key="promo_up_inicial")
        if arquivos:
            _carregar(arquivos)
            st.rerun()
        return

    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="promo_topo"):
        with st.popover(str(len(st.session_state.get("promo_arquivos", []))), icon=":material/upload_file:", help="Planilhas da campanha"):
            st.caption("Planilhas carregadas: " + ", ".join(st.session_state.get("promo_arquivos", [])))
            arquivos = st.file_uploader("Trocar ou somar planilhas", accept_multiple_files=True, type=["xlsx", "xls", "csv"], key="promo_up")
            if arquivos and st.button("Carregar estas planilhas", type="primary", width="stretch", icon=":material/upload:"):
                st.session_state.pop("promo_arquivos", None)
                _carregar(arquivos)
                st.rerun()
        _clusters_fora()

    if "SEQPRODUTO" not in df.columns:
        st.error("As planilhas não têm a coluna SEQPRODUTO.", icon=":material/error:")
        return
    dados, chave = _payload(df)
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    tokens = "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"
    _PROMO(dados=dados, chave=chave, tokens=tokens, fonte=theme.FONTE_URL, usuario=st.session_state.get("usuario_login", ""),
           tipos=_tipos_oferta(), altura=900, key="promo_metrics", default=None)
