"""PriceSense: plataforma de inteligência de preços para o varejo.

Execute com:  streamlit run portal.py
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

st.set_page_config(page_title="PriceSense", page_icon=":material/sell:", layout="wide", initial_sidebar_state="collapsed")

from core import auth, db, presenca, state  # noqa: E402
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
    presenca.registrar_saida(st.session_state.get("usuario_login", ""))
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
# (chave, permissão gravada no banco, nome exibido, ...): os nomes novos não mexem nas permissões já dadas
for chave, permissao, titulo, render, icone, url in [
    ("preco_bot", "Preço Bot", "PriceBot", preco_bot.render, ":material/sell:", "preco-bot"),
    ("promo", "Pricing Promo", "Metrics Promo", promo.render, ":material/campaign:", "pricing-promo"),
    ("pesquisa", "Pesquisa de Mercado", "Pesquisa de Mercado", pesquisa.render, ":material/query_stats:", "pesquisa-de-mercado"),
    ("regular", "Pricing Regular", "PriceMetrics", regular.render, ":material/price_change:", "pricing-regular"),
]:
    if auth.pode(permissao):
        p[chave] = st.Page(render, title=titulo, icon=icone, url_path=url)
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
# O menu da conta leva o nome da pessoa: perfil, tema e saída ficam num lugar só.
navegacao[state.primeiro_nome()] = conta
# A página de login continua registrada (oculta) para que /entrar redirecione após o login.
conta.append(st.Page(login.render, title="Entrar", url_path="entrar", visibility="hidden"))

pagina = st.navigation(navegacao, position="top")

# Botão de tema fixo no canto superior direito + menus que abrem ao passar o mouse.
with st.container(key="ps_tema"):
    escuro = theme.modo() == "Dark"
    if st.button("", icon=":material/light_mode:" if escuro else ":material/dark_mode:", type="tertiary",
                 key="ps_tema_btn", help="Modo claro" if escuro else "Modo escuro"):
        st.session_state.tema = "Light" if escuro else "Dark"
        theme.aplicar()  # grava as cores antes do rerun, para a troca ser imediata
        st.rerun()
    ui.menu_ao_passar_mouse()

presenca.pulso()

if admin_on and pagina.url_path != "admin":
    @st.fragment(run_every="30s")
    def _aviso_solicitacoes() -> None:
        """Pop-up para administradores quando chegam pedidos de acesso (verifica a cada 30 s)."""
        try:
            from core import aprovacoes as ap
            fila = db.pendentes() + [{"nome": f"{x.get('usuario')} enviou {ap.TIPOS.get(x.get('tipo'), 'um arquivo')}", "usuario": x.get("usuario"), "_up": 1}
                                     for x in ap.pendentes()]
        except Exception:
            return
        if not fila or st.session_state.get("_aviso_dispensado") == len(fila):
            return
        with st.container(key="ps_aviso"):
            nomes = ", ".join(ui.esc(u.get("nome") or u["usuario"]) for u in fila[:2]) + (f" e mais {len(fila) - 2}" if len(fila) > 2 else "")
            ups = sum(1 for u in fila if u.get("_up"))
            titulo = ("Upload aguardando aprovação" if ups == len(fila) == 1 else "Nova solicitação de acesso" if len(fila) == 1
                      else f"{len(fila)} pedidos aguardando você")
            st.html(f"<div class='ps-aviso'><i class='ps-live'></i><div><b>{titulo}</b><span>{nomes}</span></div></div>")
            c1, c2 = st.columns(2)
            if c1.button("Revisar", type="primary", width="stretch", key="aviso_ir"):
                st.switch_page(p["admin"])
            if c2.button("Depois", width="stretch", key="aviso_depois"):
                st.session_state._aviso_dispensado = len(fila)
                st.rerun(scope="fragment")

    _aviso_solicitacoes()


@st.fragment(run_every="30s")
def _notificacoes() -> None:
    """Pop-up das notificações do usuário (sugestões do comprador, respostas do Pricing...), verificado a cada 30 s."""
    from core import notificacoes as nt
    lista = nt.nao_lidas(st.session_state.get("usuario_login", ""))
    if not lista:
        return
    with st.container(key="ps_notif"):
        n = lista[0]
        extra = f" (+{len(lista) - 1})" if len(lista) > 1 else ""
        st.html(f"<div class='ps-aviso'><i class='ps-live'></i><div><b>{ui.esc(n.get('titulo') or 'Notificação')}{extra}</b>"
                f"<span>{ui.esc(n.get('texto') or '')}</span></div></div>")
        c1, c2 = st.columns(2)
        if c1.button("Ok", type="primary", width="stretch", key=f"notif_ok_{n['id']}"):
            nt.marcar_lidas([n["id"]]); st.rerun(scope="fragment")
        if len(lista) > 1 and c2.button("Ok para todas", width="stretch", key=f"notif_todas_{n['id']}"):
            nt.marcar_lidas([x["id"] for x in lista]); st.rerun(scope="fragment")


_notificacoes()


@st.fragment(run_every="15s")
def _chat() -> None:
    """Chat flutuante (canal público por estado e privados), em todas as telas."""
    from core import chat
    login = st.session_state.get("usuario_login", "")
    try:
        from views.regular import estados_atuacao
        todos = estados_atuacao()
    except Exception:
        todos = []
    eu = next((u for u in chat.usuarios() if u["usuario"] == login), None)
    if not eu:
        return
    lista = chat.canais(eu, todos)
    if not lista:
        return
    lidos, rec = chat.leituras(login), chat.recentes([c for c, _ in lista])
    nao = {}
    for m in rec:
        if m["autor"] != login and str(m["criado_em"]) > str(lidos.get(m["canal"], "")):
            nao[m["canal"]] = nao.get(m["canal"], 0) + 1
    total = sum(nao.values())
    with st.container(key="ps_chat"):
        with st.popover(f"{total}" if total else "", icon=":material/forum:", help="Chat da equipe"):
            st.html("<div class='ps-chat-top'><b>Chat</b><span>Público por estado e conversas privadas. Use @nome para marcar alguém.</span></div>")
            rotulos = {c: r + (f"  ({nao[c]})" if nao.get(c) else "") for c, r in lista}
            atual = st.session_state.get("chat_canal")
            if atual not in rotulos:
                atual = max(rotulos, key=lambda c: (nao.get(c, 0), c.startswith("uf:")))
            canal = st.selectbox("Conversa", list(rotulos), index=list(rotulos).index(atual), format_func=lambda c: rotulos[c],
                                 key="chat_sel", label_visibility="collapsed",
                                 on_change=lambda: chat.marcar_lido(login, st.session_state.chat_sel))     # abrir a conversa marca como lida
            st.session_state.chat_canal = canal
            msgs = chat.mensagens(canal)
            html = []
            for m in msgs:
                meu = m["autor"] == login
                import datetime as _dt
                try:
                    _t = _dt.datetime.fromisoformat(str(m["criado_em"]).replace("Z", "+00:00")).astimezone(_dt.timezone(_dt.timedelta(hours=-3)))
                except Exception:
                    _t = None
                hora = _t.strftime("%H:%M") if _t else str(m["criado_em"])[11:16]
                texto = ui.esc(m["texto"]).replace("\n", "<br>")
                import re as _re
                texto = _re.sub(r"(@[\wÀ-ÿ.\-]+)", r"<b class='ps-mencao'>\1</b>", texto)
                autor_ = "" if meu else "<i>" + ui.esc(m.get("autor_nome") or m["autor"]) + "</i>"
                quando = (_t.strftime("%d/%m ") if _t else "") + hora
                html.append(f"<div class='ps-msg{' eu' if meu else ''}'>{autor_}<p>{texto}</p><small>{quando}</small></div>")
            with st.container(height=330, key="ps_chat_msgs"):
                st.html("<div class='ps-msgs'>" + ("".join(html) or "<div class='ps-msg-vazio'>Nenhuma mensagem ainda. Comece a conversa.</div>") + "</div>")
            with st.form("chat_form", clear_on_submit=True, border=False):
                c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
                texto = c1.text_input("Mensagem", placeholder="Escreva... (@nome para marcar)", label_visibility="collapsed")
                if c2.form_submit_button("", icon=":material/send:", type="primary", width="stretch") and texto.strip():
                    chat.enviar(canal, eu, texto, todos)
                    st.rerun(scope="fragment")
            # a janela do chat é desenhada mesmo fechada: a conversa só conta como lida quando o usuário age nela
            if nao.get(canal) and st.button(f"Marcar {nao[canal]} mensagem(ns) como lida(s)", key="chat_lido", width="stretch", icon=":material/done_all:"):
                chat.marcar_lido(login, canal); st.rerun(scope="fragment")


_chat()

pagina.run()
