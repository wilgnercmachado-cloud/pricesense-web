"""Relatórios: biblioteca segmentada por categoria, favoritos, recentes e visualizador."""
from __future__ import annotations

import streamlit as st

from core import auth, reports, state
from ui import components as ui
from ui import theme

ALTURAS = {"Compacta": 640, "Padrão": 860, "Alta": 1200}


# ---------------------------------------------------------------- ações
def _abrir(rid: str) -> None:
    st.query_params["r"] = rid


def _alternar_favorito(rid: str, valor: bool) -> None:
    try:
        reports.definir_favorito(st.session_state.usuario_login, rid, valor)
        st.toast("Adicionado aos favoritos." if valor else "Removido dos favoritos.",
                 icon=":material/bookmark_added:" if valor else ":material/bookmark_remove:")
    except reports.ErroRelatorio as exc:
        st.toast(str(exc), icon=":material/error:")


def _nome_arquivo(rel: dict) -> str:
    nome = "".join(c for c in (rel.get("titulo") or "relatorio") if c.isalnum() or c in " -_").strip()[:60]
    return f"{nome or 'relatorio'}.html"


# ---------------------------------------------------------------- linhas
def _linha(rel: dict, prefixo: str, favorito: bool, detalhe: str | None = None, compacta: bool = False) -> None:
    cor = theme.cor_categoria(rel.get("categoria") or "Geral")
    destaque = " <span class='ps-chip promo'>Em destaque</span>" if rel.get("destaque") else ""
    if compacta:
        texto = (f"<div class='ps-rel-linha'><i style='background:{cor}'></i><div>"
                 f"<b>{ui.esc(rel.get('titulo', ''))}</b><span>{ui.esc(detalhe or rel.get('categoria') or 'Geral')}</span></div></div>")
    else:
        tags = "".join(f"<span class='ps-chip'>{ui.esc(t)}</span>" for t in (rel.get("tags") or [])[:4])
        vis = rel.get("visibilidade") or "Todos"
        restrito = f"<span>{ui.esc(reports.ROTULO_VISIBILIDADE.get(vis, vis))}</span>" if vis != "Todos" else ""
        texto = (f"<div class='ps-rel-linha'><i style='background:{cor}'></i><div>"
                 f"<b>{ui.esc(rel.get('titulo', ''))}</b>{destaque}"
                 f"<p>{ui.esc(rel.get('descricao') or 'Sem descrição.')}</p>"
                 f"<div class='ps-rep-meta'><span>{ui.esc(rel.get('autor_nome') or rel.get('autor_usuario') or '')}</span>"
                 f"<span>Atualizado em {ui.data_curta(rel.get('atualizado_em') or rel.get('criado_em'))}</span>"
                 f"<span>{ui.numero(rel.get('visualizacoes'))} visualizações</span>{restrito}</div>"
                 f"{f'<div class=ps-rep-tags>{tags}</div>' if tags else ''}</div></div>")

    c1, c2, c3 = st.columns([1, 0.09, 0.2] if not compacta else [1, 0.13, 0.24], vertical_alignment="center", gap="small")
    c1.html(texto)
    c2.button("", key=f"fav{int(favorito)}_{prefixo}_{rel['id']}", type="tertiary",
              icon=":material/bookmark_added:" if favorito else ":material/bookmark_add:",
              help="Remover dos favoritos" if favorito else "Adicionar aos favoritos",
              on_click=_alternar_favorito, args=(rel["id"], not favorito))
    c3.button("Abrir", key=f"abrir_{prefixo}_{rel['id']}", width="stretch", icon=":material/visibility:",
              on_click=_abrir, args=(rel["id"],))


# ---------------------------------------------------------------- biblioteca
def _biblioteca(todos: list[dict], prefs: dict) -> None:
    por_id = {str(r["id"]): r for r in todos}
    favoritos_ids = {rid for rid, p in prefs.items() if p.get("favorito") and rid in por_id}

    def _altura_painel(n: int) -> int:
        return min(360, max(96, 34 + 66 * max(n, len(favoritos_ids), 1)))

    recentes = sorted((p for rid, p in prefs.items() if p.get("ultimo_acesso") and rid in por_id),
                      key=lambda p: p["ultimo_acesso"], reverse=True)[:5]
    esq, dir_ = st.columns(2, gap="medium")
    with esq:
        ui.secao("Recentes", "Relatórios que você abriu por último.")
        with st.container(border=True, key="psc_rel_recentes", height=_altura_painel(len(recentes))):
            if not recentes:
                st.caption("Os relatórios que você abrir vão aparecer aqui.")
            for p in recentes:
                rel = por_id[str(p["relatorio_id"])]
                _linha(rel, "rec", rel["id"] in favoritos_ids, f"Aberto em {ui.data_curta(p['ultimo_acesso'])}", compacta=True)
    favs = sorted((por_id[rid] for rid in favoritos_ids), key=lambda r: (r.get("titulo") or "").lower())
    with dir_:
        ui.secao("Favoritos", "Use o marcador ao lado de um relatório para fixá-lo aqui.")
        with st.container(border=True, key="psc_rel_favoritos", height=_altura_painel(max(len(favs), len(recentes)))):
            if not favs:
                st.caption("Você ainda não marcou nenhum relatório como favorito.")
            for rel in favs:
                _linha(rel, "fav", True, rel.get("categoria") or "Geral", compacta=True)

    ui.secao("Todos os relatórios", "Agrupados por categoria. Use os filtros para encontrar um relatório específico.")
    rk = st.session_state.get("rel_filtro_rk", 0)
    with st.container(border=True, key="psc_rel_filtros"):
        c1, c2, c3, c4 = st.columns([1.6, 1, 1, 0.5], vertical_alignment="bottom")
        busca = c1.text_input("Relatório", placeholder="Nome ou descrição", key=f"rel_busca_{rk}", icon=":material/search:")
        cats = sorted({r.get("categoria") or "Geral" for r in todos})
        cat = c2.selectbox("Categoria", ["Todas"] + cats, key=f"rel_cat_{rk}")
        tags = sorted({t for r in todos for t in (r.get("tags") or [])}, key=str.lower)
        tag = c3.selectbox("Tag", ["Todas"] + tags, key=f"rel_tag_{rk}")
        if c4.button("Limpar", icon=":material/filter_alt_off:", width="stretch", key="rel_limpar"):
            st.session_state.rel_filtro_rk = rk + 1
            st.rerun()

    lista = todos
    termo = busca.strip().lower()
    if termo:
        lista = [r for r in lista if termo in f"{r.get('titulo') or ''} {r.get('descricao') or ''}".lower()]
    if cat != "Todas":
        lista = [r for r in lista if (r.get("categoria") or "Geral") == cat]
    if tag != "Todas":
        lista = [r for r in lista if tag in (r.get("tags") or [])]
    filtrando = bool(termo) or cat != "Todas" or tag != "Todas"

    if not lista:
        ui.vazio("Nenhum relatório encontrado", "Tente outro nome ou limpe os filtros.")
        return

    grupos: dict[str, list[dict]] = {}
    for r in lista:
        grupos.setdefault(r.get("categoria") or "Geral", []).append(r)
    for categoria in sorted(grupos, key=str.lower):
        itens = sorted(grupos[categoria], key=lambda r: (not r.get("destaque"), (r.get("titulo") or "").lower()))
        n = len(itens)
        with st.expander(f"**{categoria}** &nbsp; :blue-badge[{n} relatório{'s' if n > 1 else ''}]", expanded=filtrando):
            for i, rel in enumerate(itens):
                if i:
                    st.html("<div class='ps-rel-sep'></div>")
                _linha(rel, "all", rel["id"] in favoritos_ids)


# ---------------------------------------------------------------- visualizador
def _visualizador(rel: dict, prefs: dict) -> None:
    login, admin = st.session_state.usuario_login, auth.eh_admin()
    reports.registrar_visualizacao(rel)
    reports.marcar_acesso(login, rel["id"])
    favorito = bool(prefs.get(str(rel["id"]), {}).get("favorito"))
    foco = st.session_state.get("rel_foco") == rel["id"]

    try:
        links = reports.links_assinados(rel["arquivo_path"], int(rel.get("partes") or 1),
                                        str(rel.get("atualizado_em") or rel.get("versao")))
    except Exception as exc:
        st.error(f"Não foi possível localizar o arquivo do relatório: {exc}", icon=":material/error:")
        return
    arquivo = _nome_arquivo(rel) if admin else None

    if foco:
        # Modo foco: some a navegação do app e o relatório ocupa a janela inteira.
        st.html("<style>header[data-testid='stHeader']{display:none}"
                "[data-testid='stMainBlockContainer']{padding:.6rem 1rem 0 !important;max-width:none !important}"
                ".st-key-rel_quadro [data-testid='stIFrame']{height:calc(100vh - 74px) !important}</style>")
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            if st.button("Sair do modo foco", icon=":material/close_fullscreen:", key="rel_foco_sair"):
                st.session_state.pop("rel_foco", None)
                st.rerun()
            st.html(f"<div class='ps-foco-titulo'>{ui.esc(rel.get('titulo', ''))}</div>")
        with st.container(key="rel_quadro"):
            ui.relatorio_html(links=links, altura=860, nome_arquivo=arquivo)
        return

    ui.cabecalho("Relatórios")
    if st.button("Voltar para a biblioteca", type="tertiary", icon=":material/arrow_back:", key="rel_voltar"):
        st.query_params.clear()
        st.rerun()
    cor = theme.cor_categoria(rel.get("categoria") or "Geral")
    st.html(f"""
<div class='ps-viewer-head'>
  <div class='ps-rep-cat'><i style='background:{cor}'></i>{ui.esc(rel.get('categoria') or 'Geral')}</div>
  <h2>{ui.esc(rel.get('titulo', ''))}</h2>
  {f"<p>{ui.esc(rel['descricao'])}</p>" if rel.get('descricao') else ''}
  <div class='ps-rep-meta'><span>Publicado por {ui.esc(rel.get('autor_nome') or rel.get('autor_usuario') or '')}</span>
  <span>Atualizado em {ui.data_curta(rel.get('atualizado_em') or rel.get('criado_em'))}</span>
  <span>Versão {rel.get('versao') or 1}</span></div>
</div>""")

    with st.container(horizontal=True, vertical_alignment="bottom", gap="small", key="rel_acoes"):
        altura = st.segmented_control("Altura", list(ALTURAS), default="Padrão", required=True, key="rel_altura")
        if st.button("Expandir tela", icon=":material/open_in_full:", type="primary", key="rel_foco_entrar"):
            st.session_state.rel_foco = rel["id"]
            st.rerun()
        st.button("Remover dos favoritos" if favorito else "Favoritar", key="rel_fav",
                  icon=":material/bookmark_added:" if favorito else ":material/bookmark_add:",
                  on_click=_alternar_favorito, args=(rel["id"], not favorito))
        with st.container(width=150):
            ui.botao_copiar(rotulo="Copiar link", feito="Link copiado", link_param=("r", rel["id"]))
        if reports.pode_editar(rel, login, admin) and auth.pode_publicar():
            if st.button("Editar", icon=":material/edit:", key="rel_editar"):
                st.switch_page(state.paginas()["publicar"], query_params={"editar": rel["id"]})

    ui.relatorio_html(links=links, altura=ALTURAS[altura], nome_arquivo=arquivo)


def render() -> None:
    login, admin = st.session_state.usuario_login, auth.eh_admin()
    prefs = reports.preferencias(login)
    alvo = st.query_params.get("r")
    if alvo:
        rel = reports.buscar(alvo)
        if rel and reports.pode_ver(rel, login, admin):
            _visualizador(rel, prefs)
            return
        st.query_params.clear()
        st.toast("Relatório não encontrado ou sem permissão de acesso.", icon=":material/lock:")
    st.session_state.pop("rel_foco", None)

    ui.cabecalho("Relatórios", "Análises publicadas pela equipe de pricing.")
    todos = reports.visiveis(login, admin)
    if not todos:
        texto = ("Publique o primeiro em Relatórios > Publicar: basta enviar o arquivo HTML."
                 if auth.pode_publicar() else "Quando a equipe publicar um relatório para você, ele aparece aqui.")
        ui.vazio("A biblioteca está vazia", texto)
        return
    _biblioteca(todos, prefs)
