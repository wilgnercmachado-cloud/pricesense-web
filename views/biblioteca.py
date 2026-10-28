"""Relatórios: biblioteca e visualizador de relatórios HTML."""
from __future__ import annotations

import streamlit as st

from core import auth, reports, state
from ui import components as ui
from ui import theme

ALTURAS = {"Compacta": 640, "Padrão": 860, "Alta": 1200}


def _cartao(rel: dict, prefixo: str) -> None:
    cor = theme.cor_categoria(rel.get("categoria") or "Geral")
    destaque = "<span class='ps-chip promo'>Em destaque</span>" if rel.get("destaque") else ""
    tags = "".join(f"<span class='ps-chip'>{ui.esc(t)}</span>" for t in (rel.get("tags") or [])[:4])
    vis = rel.get("visibilidade") or "Todos"
    restrito = f"<span>{ui.esc(reports.ROTULO_VISIBILIDADE.get(vis, vis))}</span>" if vis != "Todos" else ""
    with st.container(border=True, key=f"psc_{prefixo}_{rel['id']}"):
        st.html(f"""
<div class='ps-rep-cat'><i style='background:{cor}'></i>{ui.esc(rel.get('categoria') or 'Geral')}{('&nbsp;&nbsp;' + destaque) if destaque else ''}</div>
<div class='ps-rep-title'>{ui.esc(rel.get('titulo', ''))}</div>
<div class='ps-rep-desc'>{ui.esc(rel.get('descricao') or 'Sem descrição.')}</div>
{f"<div class='ps-rep-tags'>{tags}</div>" if tags else ''}
<div class='ps-rep-meta'><span>{ui.esc(rel.get('autor_nome') or rel.get('autor_usuario') or '')}</span>
<span>{ui.data_curta(rel.get('atualizado_em') or rel.get('criado_em'))}</span>
<span>{ui.numero(rel.get('visualizacoes'))} visualizações</span>{restrito}</div>""")
        if st.button("Abrir relatório", key=f"abrir_{prefixo}_{rel['id']}", width="stretch", icon=":material/open_in_full:"):
            st.query_params["r"] = rel["id"]
            st.rerun()


def _visualizador(rel: dict) -> None:
    login, admin = st.session_state.usuario_login, auth.eh_admin()
    if st.button("Voltar para a biblioteca", type="tertiary", icon=":material/arrow_back:", key="rel_voltar"):
        st.query_params.clear()
        st.rerun()

    reports.registrar_visualizacao(rel)
    cor = theme.cor_categoria(rel.get("categoria") or "Geral")
    st.html(f"""
<div class='ps-viewer-head'>
  <div class='ps-rep-cat'><i style='background:{cor}'></i>{ui.esc(rel.get('categoria') or 'Geral')}</div>
  <h2>{ui.esc(rel.get('titulo', ''))}</h2>
  {f"<p>{ui.esc(rel['descricao'])}</p>" if rel.get('descricao') else ''}
  <div class='ps-rep-meta'><span>Publicado por {ui.esc(rel.get('autor_nome') or rel.get('autor_usuario') or '')}</span>
  <span>Atualizado em {ui.data_curta(rel.get('atualizado_em') or rel.get('criado_em'))}</span>
  <span>Versão {rel.get('versao') or 1}</span><span>{ui.tamanho_legivel(rel.get('tamanho_bytes'))}</span></div>
</div>""")

    try:
        with st.spinner("Baixando o relatório"):
            gz = reports.baixar_compactado(rel["arquivo_path"], str(rel.get("atualizado_em") or rel.get("versao")))
    except Exception as exc:
        st.error(f"Não foi possível baixar o arquivo do relatório: {exc}", icon=":material/error:")
        return

    c1, _, c3, c4 = st.columns([1.3, 1, 1, 1], vertical_alignment="bottom")
    altura = c1.segmented_control("Altura", list(ALTURAS), default="Padrão", required=True, key="rel_altura")
    with c3:
        ui.botao_copiar(rotulo="Copiar link", feito="Link copiado", link_param=("r", rel["id"]))
    with c4:
        if reports.pode_editar(rel, login, admin) and auth.pode_publicar():
            if st.button("Editar", width="stretch", icon=":material/edit:", key="rel_editar"):
                st.switch_page(state.paginas()["publicar"], query_params={"editar": rel["id"]})

    st.html("<div style='height:6px'></div>")
    nome = "".join(c for c in (rel.get("titulo") or "relatorio") if c.isalnum() or c in " -_").strip()[:60] or "relatorio"
    ui.relatorio_html(gz, ALTURAS[altura], nome_arquivo=f"{nome}.html")


def render() -> None:
    login, admin = st.session_state.usuario_login, auth.eh_admin()
    alvo = st.query_params.get("r")
    if alvo:
        rel = reports.buscar(alvo)
        if rel and reports.pode_ver(rel, login, admin):
            ui.cabecalho("Relatórios")
            _visualizador(rel)
            return
        st.query_params.clear()
        st.toast("Relatório não encontrado ou sem permissão de acesso.", icon=":material/lock:")

    ui.cabecalho("Relatórios", "Análises publicadas pela equipe de pricing. Abra, baixe ou compartilhe o link.")
    todos = reports.visiveis(login, admin)
    if not todos:
        texto = ("Publique o primeiro em Relatórios > Publicar: basta enviar o arquivo HTML."
                 if auth.pode_publicar() else "Quando a equipe publicar um relatório para você, ele aparece aqui.")
        ui.vazio("A biblioteca está vazia", texto)
        return

    c1, c2, c3 = st.columns([2, 1.2, 0.9], vertical_alignment="bottom")
    busca = c1.text_input("Buscar", placeholder="Título, descrição ou tag", key="rel_busca", icon=":material/search:")
    cats = sorted({r.get("categoria") or "Geral" for r in todos})
    cat = c2.selectbox("Categoria", ["Todas"] + cats, key="rel_cat")
    ordem = c3.selectbox("Ordenar", ["Mais recentes", "Mais vistos", "Título"], key="rel_ordem")

    lista = todos
    if cat != "Todas":
        lista = [r for r in lista if (r.get("categoria") or "Geral") == cat]
    if busca.strip():
        termo = busca.strip().lower()
        lista = [r for r in lista if termo in " ".join([r.get("titulo") or "", r.get("descricao") or "",
                                                         " ".join(r.get("tags") or [])]).lower()]
    if ordem == "Mais vistos":
        lista = sorted(lista, key=lambda r: r.get("visualizacoes") or 0, reverse=True)
    elif ordem == "Título":
        lista = sorted(lista, key=lambda r: (r.get("titulo") or "").lower())

    destaques = [r for r in lista if r.get("destaque")] if not busca.strip() and cat == "Todas" else []
    if destaques:
        ui.secao("Em destaque")
        cols = st.columns(min(3, len(destaques)))
        for i, rel in enumerate(destaques[:3]):
            with cols[i]:
                _cartao(rel, "dest")

    if destaques:
        ja_mostrados = {r["id"] for r in destaques[:3]}
        lista = [r for r in lista if r["id"] not in ja_mostrados]
    ui.secao("Todos os relatórios" if not busca.strip() else "Resultados", f"{len(lista)} relatório(s).")
    if not lista:
        if not destaques:
            ui.vazio("Nada encontrado", "Tente outro termo ou mude a categoria.")
        return
    for inicio in range(0, len(lista), 3):
        cols = st.columns(3)
        for col, rel in zip(cols, lista[inicio:inicio + 3]):
            with col:
                _cartao(rel, "all")
