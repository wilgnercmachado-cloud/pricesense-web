"""PriceSense: plataforma de inteligência de preços para o varejo.

Execute com:  streamlit run portal.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="PriceSense", page_icon=":material/sell:", layout="wide", initial_sidebar_state="collapsed")

from core import auth, db, state  # noqa: E402
from ui import components as ui  # noqa: E402
from ui import theme  # noqa: E402
from views import admin, biblioteca, home, login, perfil, pesquisa, preco_bot, promo, publicar, regular  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"

state.init_state()
theme.aplicar()

# Link direto para relatório aberto antes do login: guarda para depois.
if not st.session_state.logado and st.query_params.get("r"):
    st.session_state.pending_report = st.query_params.get("r")

try:
    db.get_client()
except db.ConfigError:
    ui.cabecalho("Configuração pendente", "O PriceSense não encontrou as credenciais do banco de dados.")
    st.code('# .streamlit/secrets.toml\nSUPABASE_URL = "https://SEU-PROJETO.supabase.co"\nSUPABASE_KEY = "sua-chave"', language="toml")
    st.caption("No Streamlit Community Cloud: Settings > Secrets. Localmente: crie o arquivo .streamlit/secrets.toml.")
    st.stop()


def _sair() -> None:
    state.encerrar_sessao()
    st.query_params.clear()
    st.rerun()


pagina_login = st.Page(login.render, title="Entrar", icon=":material/login:", url_path="entrar", default=not st.session_state.logado)

if not st.session_state.logado:
    st.navigation([pagina_login], position="hidden").run()
    st.stop()

modo_logo = "dark" if theme.modo() == "Dark" else "light"
st.logo(str(ASSETS / f"logo_{modo_logo}.svg"), size="large")

admin_on = auth.eh_admin()
p: dict[str, st.Page] = {"inicio": st.Page(home.render, title="Início", icon=":material/storefront:", url_path="inicio", default=True)}

ferramentas = []
for chave, permissao, render, icone, url in [
    ("preco_bot", "Preço Bot", preco_bot.render, ":material/sell:", "preco-bot"),
    ("promo", "Pricing Promo", promo.render, ":material/campaign:", "pricing-promo"),
    ("pesquisa", "Pesquisa de Mercado", pesquisa.render, ":material/query_stats:", "pesquisa-de-mercado"),
    ("regular", "Pricing Regular", regular.render, ":material/price_change:", "pricing-regular"),
]:
    if auth.pode(permissao):
        p[chave] = st.Page(render, title=permissao, icon=icone, url_path=url)
        ferramentas.append(p[chave])

p["biblioteca"] = st.Page(biblioteca.render, title="Biblioteca", icon=":material/library_books:", url_path="relatorios")
secao_relatorios = [p["biblioteca"]]
if auth.pode_publicar():
    p["publicar"] = st.Page(publicar.render, title="Publicar", icon=":material/upload_file:", url_path="publicar")
    secao_relatorios.append(p["publicar"])

p["perfil"] = st.Page(perfil.render, title="Meu perfil", icon=":material/person:", url_path="perfil")
conta = [p["perfil"]]
if admin_on:
    p["admin"] = st.Page(admin.render, title="Administração", icon=":material/admin_panel_settings:", url_path="admin")
    conta.append(p["admin"])
p["sair"] = st.Page(_sair, title="Sair", icon=":material/logout:", url_path="sair")
conta.append(p["sair"])

st.session_state._pages = p

navegacao = {"": [p["inicio"]]}
if ferramentas:
    navegacao["Ferramentas"] = ferramentas
navegacao["Relatórios"] = secao_relatorios
navegacao["Conta"] = conta
# A página de login continua registrada (oculta) para que /entrar redirecione após o login.
navegacao["Conta"].append(st.Page(login.render, title="Entrar", url_path="entrar", visibility="hidden"))

st.navigation(navegacao, position="top").run()
