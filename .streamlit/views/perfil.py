"""Meu perfil: nome, senha e foto."""
from __future__ import annotations

import base64
import io

import streamlit as st
from PIL import Image

from core import auth, db
from ui import components as ui


def render() -> None:
    ui.cabecalho("Meu perfil", "Atualize como você aparece na plataforma e troque sua senha.")
    esq, dir_ = st.columns([1.3, 1], gap="large")

    with esq, st.container(border=True, key="psc_perfil_dados"):
        ui.secao("Dados")
        with st.form("form_perfil", border=False):
            nome = st.text_input("Nome de exibição", value=st.session_state.usuario_logado)
            foto = st.file_uploader("Foto (PNG ou JPG)", type=["png", "jpg", "jpeg"])
            salvar = st.form_submit_button("Salvar dados", type="primary")
        if salvar:
            campos = {}
            if nome.strip() and nome.strip() != st.session_state.usuario_logado:
                campos["nome"] = nome.strip()
            if foto:
                try:
                    img = Image.open(foto).convert("RGB")
                    img.thumbnail((240, 240))
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    campos["foto_perfil"] = base64.b64encode(buf.getvalue()).decode("utf-8")
                except Exception as exc:
                    st.error(f"Não foi possível ler a imagem: {exc}")
            if campos:
                try:
                    db.atualizar_usuario(st.session_state.usuario_login, campos)
                    st.session_state.usuario_logado = campos.get("nome", st.session_state.usuario_logado)
                    st.session_state.foto_perfil = campos.get("foto_perfil", st.session_state.foto_perfil)
                    st.toast("Perfil atualizado.", icon=":material/check_circle:")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível salvar: {exc}")

    with dir_, st.container(border=True, key="psc_perfil_senha"):
        ui.secao("Senha")
        with st.form("form_senha", border=False, clear_on_submit=True):
            atual = st.text_input("Senha atual", type="password")
            nova = st.text_input("Nova senha", type="password", help="Mínimo de 6 caracteres.")
            conf = st.text_input("Confirmar nova senha", type="password")
            trocar = st.form_submit_button("Trocar senha")
        if trocar:
            registro = db.buscar_usuario(st.session_state.usuario_login)
            if not registro or not auth.conferir_senha(atual, registro.get("senha")):
                st.error("A senha atual está incorreta.")
            elif len(nova) < 6:
                st.error("A nova senha precisa ter pelo menos 6 caracteres.")
            elif nova != conf:
                st.error("As senhas novas não conferem.")
            else:
                db.atualizar_usuario(st.session_state.usuario_login, {"senha": auth.gerar_hash(nova)})
                st.success("Senha trocada.")
