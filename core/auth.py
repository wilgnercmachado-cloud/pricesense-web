"""Autenticação, senhas com bcrypt e permissões."""
from __future__ import annotations

import hmac
import secrets
import string

import bcrypt
import streamlit as st

from core import db

FERRAMENTAS = ["Preço Bot", "Pricing Regular", "Pricing Promo", "Pesquisa de Mercado"]
PUBLICAR_RELATORIOS = "Publicar Relatórios"
TODAS_PERMISSOES = FERRAMENTAS + [PUBLICAR_RELATORIOS]


# ---------------------------------------------------------------- senhas
def gerar_hash(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _eh_hash(valor: str) -> bool:
    return isinstance(valor, str) and valor.startswith(("$2a$", "$2b$", "$2y$"))


def conferir_senha(digitada: str, armazenada: str | None) -> bool:
    if not armazenada or not digitada:
        return False
    if _eh_hash(armazenada):
        try:
            return bcrypt.checkpw(digitada.encode("utf-8"), armazenada.encode("utf-8"))
        except ValueError:
            return False
    # Senha legada em texto puro (migrada para hash no primeiro login).
    return hmac.compare_digest(digitada, armazenada)


def senha_temporaria(tamanho: int = 10) -> str:
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


# ---------------------------------------------------------------- permissões
def normalizar_permissoes(brutas) -> list[str]:
    saida: list[str] = []
    for p in brutas or []:
        p = str(p)
        if "Publicar" in p:
            valor = PUBLICAR_RELATORIOS
        elif "Bot" in p:
            valor = "Preço Bot"
        elif "Regular" in p:
            valor = "Pricing Regular"
        elif "Promo" in p:
            valor = "Pricing Promo"
        elif "Pesquisa" in p:
            valor = "Pesquisa de Mercado"
        else:
            continue
        if valor not in saida:
            saida.append(valor)
    return saida


def eh_admin() -> bool:
    return bool(st.session_state.get("is_admin"))


def pode(permissao: str) -> bool:
    return eh_admin() or permissao in st.session_state.get("permissoes", [])


def pode_publicar() -> bool:
    return pode(PUBLICAR_RELATORIOS)


# ---------------------------------------------------------------- fluxo
def entrar(usuario: str, senha: str) -> tuple[bool, str]:
    usuario = (usuario or "").strip()
    if not usuario or not senha:
        return False, "Informe usuário e senha."
    try:
        registro = db.buscar_usuario(usuario)
    except Exception as exc:
        print(f"[PriceSense] Falha ao consultar a tabela usuarios: {exc!r}", flush=True)
        return False, "Não foi possível conectar ao banco de dados. Tente novamente em instantes."

    if not registro or not conferir_senha(senha, registro.get("senha")):
        return False, "Usuário ou senha incorretos."

    status = registro.get("status")
    if status == "Pendente":
        return False, "Seu acesso ainda está em análise. Fale com um administrador."
    if status != "Aprovado":
        return False, "Este acesso está bloqueado. Fale com um administrador."

    if not _eh_hash(registro.get("senha", "")):
        try:
            db.atualizar_usuario(usuario, {"senha": gerar_hash(senha)})
        except Exception:
            pass  # o login segue; a migração tenta de novo na próxima vez

    st.session_state.logado = True
    st.session_state.usuario_logado = registro.get("nome") or usuario
    st.session_state.usuario_login = registro["usuario"]
    st.session_state.usuario_cargo = registro.get("cargo") or ""
    st.session_state.foto_perfil = registro.get("foto_perfil") or ""
    st.session_state.is_admin = bool(registro.get("is_admin", False))
    st.session_state.permissoes = normalizar_permissoes(registro.get("permissoes"))
    return True, ""


def solicitar_acesso(nome: str, usuario: str, matricula: str, cargo: str, senha: str, confirmacao: str) -> tuple[bool, str]:
    nome, usuario = (nome or "").strip(), (usuario or "").strip()
    if not nome or not usuario or not senha:
        return False, "Preencha nome, usuário e senha."
    if len(senha) < 6:
        return False, "A senha precisa ter pelo menos 6 caracteres."
    if senha != confirmacao:
        return False, "As senhas não conferem."
    try:
        if db.buscar_usuario(usuario):
            return False, "Esse usuário já existe. Escolha outro."
        db.inserir_usuario({
            "usuario": usuario, "senha": gerar_hash(senha), "nome": nome,
            "cargo": (cargo or "").strip(), "matricula": (matricula or "").strip(),
            "status": "Pendente", "is_admin": False, "permissoes": [],
        })
    except Exception:
        return False, "Não foi possível enviar a solicitação. Tente novamente em instantes."
    return True, "Solicitação enviada. Você poderá entrar assim que um administrador aprovar."
