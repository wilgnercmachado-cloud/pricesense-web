"""Relatórios: publicar e gerenciar relatórios HTML."""
from __future__ import annotations

import streamlit as st

from core import auth, db, reports, state
from ui import components as ui

NOVA = "Nova categoria"


def _usuarios_aprovados() -> list[str]:
    try:
        return sorted(u["usuario"] for u in db.listar_usuarios() if u.get("status") == "Aprovado")
    except Exception:
        return []


def _formulario(rel: dict | None) -> None:
    editando = rel is not None
    sufixo = rel["id"] if editando else "novo"
    login, admin = st.session_state.usuario_login, auth.eh_admin()

    with st.container(border=True, key=f"psc_pub_form_{sufixo[:8]}"):
        esq, dir_ = st.columns([1.15, 1], gap="large")
        with esq:
            ui.secao("Sobre o relatório")
            titulo = st.text_input("Título", value=rel.get("titulo", "") if editando else "", max_chars=120, key=f"pub_tit_{sufixo}")
            descricao = st.text_area("Descrição", value=(rel.get("descricao") or "") if editando else "", height=96, max_chars=600,
                                     placeholder="O que o relatório mostra e para quem ele é útil.", key=f"pub_desc_{sufixo}")
            existentes = reports.categorias()
            atual = (rel.get("categoria") or "Geral") if editando else None
            opcoes = sorted(set(existentes + ([atual] if atual else []) + ["Geral"])) + [NOVA]
            c1, c2 = st.columns(2)
            escolha = c1.selectbox("Categoria", opcoes, index=opcoes.index(atual) if atual in opcoes else opcoes.index("Geral"),
                                   key=f"pub_cat_{sufixo}")
            categoria = c2.text_input("Nome da nova categoria", key=f"pub_catnova_{sufixo}") if escolha == NOVA else escolha
            tags_txt = st.text_input("Tags", value=", ".join(rel.get("tags") or []) if editando else "",
                                     placeholder="Separe por vírgula: hortifruti, Bahia, semanal", key=f"pub_tags_{sufixo}")

        with dir_:
            ui.secao("Quem pode ver")
            vis_atual = (rel.get("visibilidade") or "Todos") if editando else "Todos"
            visibilidade = st.radio("Visibilidade", reports.VISIBILIDADES, index=reports.VISIBILIDADES.index(vis_atual),
                                    format_func=reports.ROTULO_VISIBILIDADE.get, label_visibility="collapsed", key=f"pub_vis_{sufixo}")
            permitidos: list[str] = []
            if visibilidade == "Selecionados":
                permitidos = st.multiselect("Pessoas com acesso", _usuarios_aprovados(),
                                            default=[u for u in (rel.get("usuarios_permitidos") or []) if u in _usuarios_aprovados()] if editando else [],
                                            key=f"pub_users_{sufixo}")
            destaque = False
            if admin:
                destaque = st.toggle("Destacar no topo da biblioteca", value=bool(rel.get("destaque")) if editando else False,
                                     key=f"pub_dest_{sufixo}")

            ui.secao("Arquivo" if not editando else "Substituir arquivo",
                     None if not editando else f"Versão atual: {rel.get('versao') or 1}. Envie um novo HTML só se quiser trocar o conteúdo.")
            fonte = st.segmented_control("Origem", ["Enviar arquivo", "Colar código"], default="Enviar arquivo", required=True,
                                         key=f"pub_fonte_{sufixo}", label_visibility="collapsed")
            conteudo: bytes | None = None
            if fonte == "Enviar arquivo":
                arq = st.file_uploader(f"Arquivo HTML (até {reports.TAMANHO_MAXIMO_MB} MB)", type=["html", "htm"], key=f"pub_arq_{sufixo}")
                if arq:
                    conteudo = arq.getvalue()
            else:
                codigo = st.text_area("Código HTML", height=150, placeholder="<!doctype html>…", key=f"pub_cod_{sufixo}")
                if codigo.strip():
                    conteudo = codigo.encode("utf-8")

    if conteudo:
        mb = len(conteudo) / 1024 / 1024
        if st.toggle(f"Pré-visualizar ({f'{mb:.1f}'.replace('.', ',')} MB)", key=f"pub_prev_{sufixo}"):
            with st.spinner("Compactando para a pré-visualização"):
                gz = reports.compactar(conteudo)
            ui.relatorio_html(gz, 560)

    erros = []
    if not titulo.strip():
        erros.append("o título")
    if not (categoria or "").strip():
        erros.append("a categoria")
    if not editando and not conteudo:
        erros.append("o arquivo HTML")
    if visibilidade == "Selecionados" and not permitidos:
        erros.append("ao menos uma pessoa com acesso")

    c1, c2, _ = st.columns([1, 1, 2])
    rotulo = "Salvar alterações" if editando else "Publicar relatório"
    clicou = c1.button(rotulo, type="primary", width="stretch", icon=":material/publish:", key=f"pub_ok_{sufixo}")
    if editando and c2.button("Cancelar edição", width="stretch", key="pub_cancelar"):
        st.query_params.clear()
        st.rerun()
    if clicou and erros:
        st.error("Para publicar, falta " + ", ".join(erros) + ".", icon=":material/error:")
    elif clicou:
        meta = {
            "titulo": titulo.strip(), "descricao": descricao.strip(), "categoria": categoria.strip(),
            "tags": [t.strip() for t in tags_txt.split(",") if t.strip()][:12],
            "visibilidade": visibilidade, "usuarios_permitidos": permitidos,
            "destaque": destaque if admin else bool(rel.get("destaque")) if editando else False,
        }
        try:
            with st.spinner("Compactando e enviando o arquivo. Relatórios grandes levam alguns segundos."):
                if editando:
                    reports.atualizar(rel, meta, conteudo)
                    rid = rel["id"]
                else:
                    rid = reports.publicar(meta, conteudo, login, st.session_state.usuario_logado)
        except reports.ErroRelatorio as exc:
            st.error(str(exc), icon=":material/error:")
            return
        st.toast("Alterações salvas." if editando else "Relatório publicado.", icon=":material/check_circle:")
        st.switch_page(state.paginas()["biblioteca"], query_params={"r": rid})


@st.dialog("Excluir relatório")
def _confirmar_exclusao(rel: dict) -> None:
    st.write(f"**{rel.get('titulo')}** será removido da biblioteca e o arquivo será apagado. Isso não pode ser desfeito.")
    c1, c2 = st.columns(2)
    if c1.button("Excluir", type="primary", width="stretch"):
        try:
            reports.excluir(rel)
            st.toast("Relatório excluído.", icon=":material/delete:")
        except Exception as exc:
            st.error(f"Não foi possível excluir: {exc}")
            return
        st.rerun()
    if c2.button("Cancelar", width="stretch"):
        st.rerun()


def _gerenciar() -> None:
    login, admin = st.session_state.usuario_login, auth.eh_admin()
    meus = [r for r in reports.listar() if reports.pode_editar(r, login, admin)]
    if not meus:
        ui.vazio("Você ainda não publicou relatórios", "Use a aba Novo relatório para enviar o primeiro.")
        return
    st.caption("Administradores veem todos os relatórios." if admin else "Relatórios publicados por você.")
    with st.container(border=True, key="psc_pub_lista"):
        for rel in meus:
            c1, c2, c3, c4 = st.columns([3, 1.1, 0.8, 0.8], vertical_alignment="center")
            c1.markdown(f"**{rel.get('titulo')}**  \n<span style='color:var(--ps-muted);font-size:.85rem'>"
                        f"{ui.esc(rel.get('categoria') or 'Geral')}, versão {rel.get('versao') or 1}, "
                        f"{ui.data_curta(rel.get('atualizado_em'))}</span>", unsafe_allow_html=True)
            c2.caption(f"{ui.numero(rel.get('visualizacoes'))} visualizações")
            if c3.button("Editar", key=f"ger_ed_{rel['id']}", width="stretch"):
                st.query_params["editar"] = rel["id"]
                st.rerun()
            if c4.button("Excluir", key=f"ger_ex_{rel['id']}", width="stretch"):
                _confirmar_exclusao(rel)


def render() -> None:
    if not auth.pode_publicar():
        ui.cabecalho("Publicar relatório")
        ui.vazio("Sem permissão para publicar", "Peça a um administrador a permissão Publicar Relatórios.")
        return

    editar_id = st.query_params.get("editar")
    rel = reports.buscar(editar_id) if editar_id else None
    if rel and not reports.pode_editar(rel, st.session_state.usuario_login, auth.eh_admin()):
        rel = None

    if rel:
        ui.cabecalho("Editar relatório", rel.get("titulo"))
        _formulario(rel)
        return

    ui.cabecalho("Publicar relatório", "Envie um arquivo HTML para a biblioteca: gerado em Python ou Plotly, Excel salvo como página da web ou feito à mão.")
    aba_novo, aba_gerenciar = st.tabs(["Novo relatório", "Gerenciar publicados"])
    with aba_novo:
        _formulario(None)
    with aba_gerenciar:
        _gerenciar()
