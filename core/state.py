"""Estado de sessão do PriceSense."""
from __future__ import annotations

import streamlit as st

_AUTH_DEFAULTS = {
    "logado": False,
    "usuario_logado": "",
    "usuario_login": "",
    "usuario_cargo": "",
    "foto_perfil": "",
    "is_admin": False,
    "permissoes": [],
}

_DEFAULTS = {
    "tema": "Light",
    "modo_login": "login",
    "reset_key": 0,
    **_AUTH_DEFAULTS,
}

# Chaves de trabalho que não devem sobreviver a uma troca de usuário.
_DADOS_DE_TRABALHO = (
    "df_promo_processado", "promo_arquivos", "linhas_alteradas", "clusters_desconhecidos",
    "campanhas_vencidas", "pending_promo_edit", "promo_edit_data",
    "df_pesq_master", "arquivo_pesquisa_nome", "pesq_enriquecimento", "pesq_extracao",
    "pb_resultado", "pending_report", "_pages",
)


def init_state() -> None:
    for chave, valor in _DEFAULTS.items():
        if chave not in st.session_state:
            st.session_state[chave] = list(valor) if isinstance(valor, list) else valor


def primeiro_nome() -> str:
    nome = (st.session_state.get("usuario_logado") or "").strip()
    return nome.split()[0] if nome else "Usuário"


def encerrar_sessao() -> None:
    for chave, valor in _AUTH_DEFAULTS.items():
        st.session_state[chave] = list(valor) if isinstance(valor, list) else valor
    for chave in _DADOS_DE_TRABALHO:
        st.session_state.pop(chave, None)
    st.session_state.modo_login = "login"


def paginas() -> dict:
    """Páginas registradas na execução atual (st.Page), por apelido."""
    return st.session_state.get("_pages", {})
