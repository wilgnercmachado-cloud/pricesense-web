"""Administração: acessos, permissões e mapeamento de clusters."""
from __future__ import annotations

import streamlit as st

from core import auth, db, presenca
from ui import components as ui


def _status_html(u: dict) -> str:
    r = presenca.resumo(u)
    online = ("<span class='ps-status on'><i></i>Online agora</span>" if r["online"]
              else "<span class='ps-status'><i></i>Offline</span>")
    acessos = f"{r['acessos_hoje']} acesso{'s' if r['acessos_hoje'] != 1 else ''} hoje"
    return (f"<div class='ps-user-meta'>{online}<span>{acessos}</span><span>Último acesso: {ui.esc(r['ultimo'])}</span></div>")


def _linha_usuario(u: dict) -> None:
    eu = u["usuario"] == st.session_state.get("usuario_login")
    with st.container(border=True, key=f"psc_user_{u['usuario']}"):
        c1, c2, c3, c4 = st.columns([1.7, 2.1, 0.95, 0.7], vertical_alignment="center")
        cargo = f", {ui.esc(u['cargo'])}" if u.get("cargo") else ""
        c1.html(f"<b>{ui.esc(u.get('nome') or u['usuario'])}</b>"
                f"<div style='color:var(--ps-faint);font-size:.8rem'>{ui.esc(u['usuario'])}{cargo}</div>{_status_html(u)}")
        admin_u = bool(u.get("is_admin"))
        if admin_u:
            c2.html("<span class='ps-chip promo'>Administrador: acesso total</span>")
        else:
            atuais = auth.normalizar_permissoes(u.get("permissoes"))
            novas = c2.multiselect("Permissões", auth.TODAS_PERMISSOES, default=atuais, key=f"perm_{u['usuario']}",
                                   label_visibility="collapsed", placeholder="Somente relatórios")
            if novas != atuais:
                try:
                    db.atualizar_usuario(u["usuario"], {"permissoes": novas})
                    st.toast(f"Permissões de {u.get('nome') or u['usuario']} atualizadas.", icon=":material/check_circle:")
                except Exception as exc:
                    st.error(f"Não foi possível salvar: {exc}")
        novo_admin = c3.toggle("Administrador", value=admin_u, key=f"adm_{u['usuario']}", disabled=eu,
                               help="Você não pode remover o seu próprio acesso de administrador." if eu else
                               "Acesso total: vê todas as ferramentas, publica relatórios e aprova usuários.")
        if novo_admin != admin_u and not eu:
            db.atualizar_usuario(u["usuario"], {"is_admin": novo_admin})
            st.toast(f"{u.get('nome') or u['usuario']} {'agora é administrador' if novo_admin else 'deixou de ser administrador'}.",
                     icon=":material/admin_panel_settings:")
            st.rerun()
        with c4.popover("Ações", width="stretch"):
            if st.button("Redefinir senha", key=f"rst_{u['usuario']}", width="stretch"):
                temp = auth.senha_temporaria()
                db.atualizar_usuario(u["usuario"], {"senha": auth.gerar_hash(temp)})
                st.session_state._senha_temp = (u.get("nome") or u["usuario"], temp)
                st.rerun()
            if not eu and st.button("Bloquear acesso", key=f"bloq_{u['usuario']}", width="stretch"):
                db.atualizar_usuario(u["usuario"], {"status": "Rejeitado", "is_admin": False})
                st.rerun()


def render() -> None:
    if not auth.eh_admin():
        ui.cabecalho("Administração")
        ui.vazio("Área restrita", "Só administradores acessam esta página.")
        return
    ui.cabecalho("Administração", "Aprove acessos, ajuste permissões e revise pedidos de mapeamento de cluster.")
    try:
        usuarios = db.listar_usuarios()
    except Exception as exc:
        st.error(f"Não foi possível carregar os usuários: {exc}")
        return

    pendentes = [u for u in usuarios if u.get("status") == "Pendente"]
    ativos = sorted([u for u in usuarios if u.get("status") == "Aprovado"],
                    key=lambda u: (not presenca.resumo(u)["online"], not u.get("is_admin"), (u.get("nome") or "").lower()))
    online = sum(1 for u in ativos if presenca.resumo(u)["online"])
    bloqueados = [u for u in usuarios if u.get("status") not in ("Pendente", "Aprovado")]
    pedidos_cluster = db.listar_solicitacoes_cluster()

    ui.etiquetas([
        ui.etiqueta("Aguardando aprovação", len(pendentes), tipo="numero", tom="promo" if pendentes else "neutro"),
        ui.etiqueta("Usuários ativos", len(ativos), tipo="numero", tom="primary"),
        ui.etiqueta("Online agora", online, tipo="numero", tom="ok"),
        ui.etiqueta("Clusters para mapear", len(pedidos_cluster), tipo="numero", tom="alert" if pedidos_cluster else "neutro"),
    ])

    abas = st.tabs([f"Solicitações ({len(pendentes)})", f"Usuários ({len(ativos)})",
                    f"Clusters ({len(pedidos_cluster)})", f"Bloqueados ({len(bloqueados)})"])

    with abas[0]:
        if not pendentes:
            ui.vazio("Nenhuma solicitação pendente", "Novos pedidos de acesso aparecem aqui.")
        for u in pendentes:
            with st.container(border=True, key=f"psc_pend_{u['usuario']}"):
                c1, c2, c3, c4 = st.columns([1.6, 1.8, 0.8, 0.8], vertical_alignment="center")
                c1.html(f"<b>{ui.esc(u.get('nome') or '')}</b><br><span style='color:var(--ps-muted);font-size:.86rem'>"
                        f"{ui.esc(u['usuario'])}, matrícula {ui.esc(u.get('matricula') or '-')}, {ui.esc(u.get('cargo') or 'sem cargo')}</span>")
                perms = c2.multiselect("Liberar", auth.TODAS_PERMISSOES, default=["Preço Bot"], key=f"apr_perm_{u['usuario']}",
                                       label_visibility="collapsed")
                if c3.button("Aprovar", type="primary", key=f"apr_{u['usuario']}", width="stretch"):
                    db.atualizar_usuario(u["usuario"], {"status": "Aprovado", "permissoes": perms})
                    st.rerun()
                if c4.button("Recusar", key=f"rej_{u['usuario']}", width="stretch"):
                    db.atualizar_usuario(u["usuario"], {"status": "Rejeitado"})
                    st.rerun()

    with abas[1]:
        aviso = st.session_state.pop("_senha_temp", None)
        if aviso:
            st.success(f"Senha temporária de {aviso[0]}: `{aviso[1]}`. Envie à pessoa e peça para trocar em Meu perfil. "
                       "Ela não será mostrada de novo.", icon=":material/key:")
        busca = st.text_input("Buscar usuário", placeholder="Nome ou login", key="adm_busca", icon=":material/search:")
        termo = busca.strip().lower()
        for u in ativos:
            if termo and termo not in f"{u.get('nome', '')} {u['usuario']}".lower():
                continue
            _linha_usuario(u)

    with abas[2]:
        if not pedidos_cluster:
            ui.vazio("Nenhum pedido de cluster", "Quando alguém pedir o mapeamento de um cluster no Pricing Promo, o pedido aparece aqui.")
        for p in pedidos_cluster:
            with st.container(border=True, key=f"psc_cl_{p.get('id')}"):
                c1, c2, c3 = st.columns([3, 0.8, 0.8], vertical_alignment="center")
                c1.html(f"<b>{ui.esc(str(p.get('cluster')))}</b> para a filial <b>{ui.esc(str(p.get('id_filial')))}</b><br>"
                        f"<span style='color:var(--ps-muted);font-size:.86rem'>Pedido de {ui.esc(str(p.get('solicitante') or '-'))}</span>")
                if c2.button("Mapear", type="primary", key=f"cl_ok_{p.get('id')}", width="stretch"):
                    try:
                        db.aprovar_cluster(p)
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Não foi possível gravar em filial-cluster: {exc}")
                if c3.button("Recusar", key=f"cl_no_{p.get('id')}", width="stretch"):
                    db.recusar_cluster(p)
                    st.rerun()

    with abas[3]:
        if not bloqueados:
            ui.vazio("Ninguém bloqueado", "Acessos recusados ou bloqueados aparecem aqui e podem ser reativados.")
        for u in bloqueados:
            with st.container(border=True, key=f"psc_bloq_{u['usuario']}"):
                c1, c2 = st.columns([4, 1], vertical_alignment="center")
                c1.html(f"<b>{ui.esc(u.get('nome') or u['usuario'])}</b><br><span style='color:var(--ps-muted);font-size:.86rem'>{ui.esc(u['usuario'])}</span>")
                if c2.button("Reativar", key=f"reat_{u['usuario']}", width="stretch"):
                    db.atualizar_usuario(u["usuario"], {"status": "Aprovado"})
                    st.rerun()
