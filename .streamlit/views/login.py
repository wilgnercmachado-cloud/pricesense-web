"""Tela de entrada e solicitação de acesso."""
from __future__ import annotations

import streamlit as st

from core import auth, state
from ui import components as ui


def _reel(digito: int, atraso: float) -> str:
    numeros = "".join(f"<span>{n}</span>" for n in range(10))
    return f"<span class='ps-roll'><span class='ps-reel' style='--to:{digito};--d:{atraso}s'>{numeros}</span></span>"


def _hero() -> str:
    # Etiqueta de encarte: varejo R$ 9,98 rola até o valor; atacado logo abaixo.
    preco = (f"<div class='ps-hero-price' role='img' aria-label='Varejo R$ 9,98'>"
             f"<span class='cur'>R$</span>{_reel(9, .15)}"
             f"<span class='dec'>,{_reel(9, .35)}{_reel(8, .55)}</span></div>")
    barras = "".join(f"<i style='height:{h}px'></i>" for h in (34, 34, 22, 34, 28, 34, 22, 22, 34, 30, 34, 22, 34, 26, 34))
    return f"""
<div class='ps-hero'>
  <div class='ps-hero-brand'>{ui.marca_html()}</div>
  <div class='ps-hero-tag'>
    <div class='ps-hero-desc'>Preço de gôndola, encarte e concorrência na mesma mesa.</div>
    {preco}
    <div class='ps-hero-foot'>
      <div class='atac'>Atacado<strong>R$ 9,48</strong></div>
      <div class='bars' aria-hidden='true'>{barras}</div>
    </div>
  </div>
  <p class='ps-hero-copy'>Gere arquivos de importação para o ERP, valide encartes antes de subir,
  leia a pesquisa de mercado e publique relatórios para a equipe.</p>
</div>"""


def _depois_de_entrar() -> None:
    paginas = state.paginas()
    pendente = st.session_state.pop("pending_report", None)
    if pendente and "biblioteca" in paginas:
        st.switch_page(paginas["biblioteca"], query_params={"r": pendente})
    if "inicio" in paginas:
        st.switch_page(paginas["inicio"])


def _form_entrar() -> None:
    st.html("<h2>Entrar</h2><p class='sub'>Use o usuário e a senha cadastrados.</p>")
    with st.form("form_login", border=False):
        usuario = st.text_input("Usuário", autocomplete="username")
        senha = st.text_input("Senha", type="password", autocomplete="current-password")
        enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
    if enviar:
        ok, msg = auth.entrar(usuario, senha)
        if ok:
            st.rerun()
        st.error(msg, icon=":material/error:")
    st.divider()
    st.caption("Ainda não tem acesso?")
    if st.button("Solicitar acesso", width="stretch", key="ir_cadastro"):
        st.session_state.modo_login = "cadastro"
        st.rerun()


def _form_cadastro() -> None:
    st.html("<h2>Solicitar acesso</h2><p class='sub'>Um administrador aprova o cadastro e libera as ferramentas.</p>")
    with st.form("form_cadastro", border=False):
        nome = st.text_input("Nome completo")
        c1, c2 = st.columns(2)
        usuario = c1.text_input("Usuário")
        matricula = c2.text_input("Matrícula")
        cargo = st.text_input("Cargo")
        c3, c4 = st.columns(2)
        senha = c3.text_input("Senha", type="password", help="Mínimo de 6 caracteres.")
        senha2 = c4.text_input("Confirmar senha", type="password")
        enviar = st.form_submit_button("Enviar solicitação", type="primary", width="stretch")
    if enviar:
        ok, msg = auth.solicitar_acesso(nome, usuario, matricula, cargo, senha, senha2)
        if ok:
            st.session_state.modo_login = "login"
            st.session_state._flash_login = msg
            st.rerun()
        st.error(msg, icon=":material/error:")
    if st.button("Voltar para o login", type="tertiary", icon=":material/arrow_back:", key="voltar_login"):
        st.session_state.modo_login = "login"
        st.rerun()


def render() -> None:
    if st.session_state.get("logado"):
        _depois_de_entrar()
        return

    st.html("<style>header[data-testid='stHeader']{display:none}"
            "[data-testid='stMainBlockContainer']{padding-top:7vh}</style>")
    esq, _, dir_ = st.columns([1.25, 0.12, 0.9], vertical_alignment="center")
    with esq:
        st.html(_hero())
    with dir_:
        with st.container(border=True, key="psc_login"):
            aviso = st.session_state.pop("_flash_login", None)
            if aviso:
                st.success(aviso, icon=":material/check_circle:")
            if st.session_state.get("modo_login") == "cadastro":
                _form_cadastro()
            else:
                _form_entrar()
