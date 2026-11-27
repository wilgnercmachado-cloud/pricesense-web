"""Administração: acessos, permissões e mapeamento de clusters."""
from __future__ import annotations

import streamlit as st

from core import reports, auth, db, presenca
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
            novas = c2.multiselect("Permissões", auth.TODAS_PERMISSOES, default=atuais, key=f"perm_{u['usuario']}", format_func=auth.nome_exibido,
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
        s1, s2, _ = st.columns([1.3, 1.6, 1.6], vertical_alignment="center")
        setores = st.session_state.get("_setores_lista", [])
        setor_atual = u.get("setor") or None
        setor = s1.selectbox("Setor", sorted(set(setores) | ({setor_atual} if setor_atual else set())), index=None if not setor_atual else
                             sorted(set(setores) | {setor_atual}).index(setor_atual), accept_new_options=True, placeholder="Setor (digite para criar)",
                             key=f"set_{u['usuario']}", label_visibility="collapsed")
        from views.regular import estados_atuacao
        opcoes = ["TODOS"] + estados_atuacao()
        atuais = [x for x in reports.estados_do_usuario(u.get("estado")) if x in opcoes]
        escolha = s2.multiselect("Estados", opcoes, default=atuais, placeholder="Estados", format_func=lambda x: "Todos (Brasil)" if x == "TODOS" else x,
                                 key=f"uf_{u['usuario']}", label_visibility="collapsed")
        if "TODOS" in escolha and len(escolha) > 1:
            escolha = ["TODOS"]                         # Todos (Brasil) já inclui qualquer estado
        estado = ";".join(escolha) or None
        if (setor or None) != setor_atual or estado != (";".join(atuais) or None):
            try:
                db.atualizar_usuario(u["usuario"], {"setor": setor or None, "estado": estado})
                rot = "Todos (Brasil)" if escolha == ["TODOS"] else (", ".join(escolha) or "-")
                st.toast(f"{u.get('nome') or u['usuario']}: setor {setor or '-'}, estados {rot}.", icon=":material/badge:")
            except Exception as exc:
                st.error(f"Não foi possível salvar: {exc}. Crie as colunas setor e estado em usuarios (supabase/migrations.sql).")
        with c4.popover("Ações", width="stretch"):
            if st.button("Redefinir senha", key=f"rst_{u['usuario']}", width="stretch"):
                temp = auth.senha_temporaria()
                db.atualizar_usuario(u["usuario"], {"senha": auth.gerar_hash(temp)})
                st.session_state._senha_temp = (u.get("nome") or u["usuario"], temp)
                st.rerun()
            if not eu and st.button("Bloquear acesso", key=f"bloq_{u['usuario']}", width="stretch"):
                db.atualizar_usuario(u["usuario"], {"status": "Rejeitado", "is_admin": False})
                st.rerun()


def _painel_trafego() -> None:
    """Consumo do dia da cota de tráfego do Supabase (plano gratuito: 5 GB por mês, cerca de 160 MB por dia)."""
    from core import db, trafego
    if db.modo_local():
        return
    r = trafego.resumo()
    pct = min(r["mb"] / r["limite"], 1.0) if r["limite"] else 0
    with st.expander(f"Tráfego do banco hoje: {r['mb']:.1f} MB de {r['limite']} MB"
                     + (" · modo econômico ligado" if trafego.economia() else ""),
                     icon=":material/speed:", expanded=trafego.economia()):
        st.progress(pct)
        st.caption(f"Medido pelo servidor desde {r['desde']}. Passando de {r['limite']} MB no dia, o site entra em modo "
                   "econômico até a meia-noite: o ao vivo pausa e o chat e o sininho atualizam com menos frequência. "
                   "Os relatórios são entregues pelo próprio site: o Supabase manda cada versão no máximo uma vez. Confira o total do mês no Supabase, "
                   "em Organização > Uso (Saída e Saída em cache, 5 GB cada).")
        if r["itens"]:
            st.dataframe({"Origem": [k for k, _ in r["itens"]], "MB hoje": [round(v, 2) for _, v in r["itens"]]},
                         hide_index=True, width="stretch")


def _aba_concorrentes() -> None:
    """Configuração da pesquisa: que lojas concorrentes cada filial pesquisa, por estado (vem da base GMAT, sem Supabase)."""
    import html as _h
    from core import associacoes as asc
    from core import mercado as mc
    if not st.toggle("Mostrar as associações", key="adm_assoc_ver",
                     help="Carrega a base de pesquisa (Competitividade Pricing GMAT) já guardada no servidor."):
        st.caption("Mostra, por estado e filial, quais lojas concorrentes estão associadas, quantas coletas cada uma teve "
                   "no período e o dia da última coleta.")
        return
    fonte = mc.base_padrao()
    if fonte is None:
        ui.vazio("Base de pesquisa não encontrada", "Publique o relatório Competitividade Pricing GMAT na biblioteca.")
        return
    df, meta, rel = fonte
    versao = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    t = asc.tabela(versao, df, meta)
    if t.empty:
        ui.vazio("Sem associações na base", "O relatório publicado não trouxe o bloco de concorrentes por filial.")
        return
    permitidos = auth.estados_permitidos()
    if permitidos is not None:
        t = t[t["Estado"].map(auth.sigla_estado).isin(permitidos)]
    c1, c2, c3 = st.columns([1.2, 1.6, 1])
    ests = c1.multiselect("Estado", sorted(t["Estado"].unique()), placeholder="Todos", key="adm_assoc_uf")
    busca = c2.text_input("Buscar filial, bandeira ou concorrente", key="adm_assoc_busca", placeholder="Ex.: 544, Assaí, Atakarejo").strip().lower()
    visao = c3.segmented_control("Ver", ["Por filial", "Lista completa"], default="Por filial", required=True, key="adm_assoc_visao")
    v = t[t["Estado"].isin(ests)] if ests else t
    if busca:
        v = v[v["Filial"].str.lower().str.contains(busca, regex=False) | v["Bandeira"].str.lower().str.contains(busca, regex=False)
              | v["Concorrente"].str.lower().str.contains(busca, regex=False)]
    sem = asc.filiais_sem_concorrente(versao, df, t)
    if ests:
        sem = sem[sem["Estado"].isin(ests)]
    if permitidos is not None:
        sem = sem[sem["Estado"].map(auth.sigla_estado).isin(permitidos)]
    parados = v[v["Coletas no período"] == 0]["Concorrente"].nunique()
    ui.indicadores([
        ("Filiais com concorrentes", v["Filial"].nunique(), "loja" if "loja" in ui._ICONES else "mapa", "primary"),
        ("Lojas concorrentes", v["Concorrente"].nunique(), "pessoas", "primary"),
        ("Bandeiras", v.loc[v["Bandeira"] != "-", "Bandeira"].nunique(), "escudo", "neutro"),
        ("Filiais sem concorrente", len(sem), "alerta" if "alerta" in ui._ICONES else "relogio", "alerta" if len(sem) else "neutro"),
        ("Concorrentes sem coleta no período", parados, "relogio", "aviso" if parados else "neutro"),
    ])
    if visao == "Lista completa":
        st.dataframe(v, hide_index=True, width="stretch", height=520,
                     column_config={"Coletas no período": st.column_config.NumberColumn(format="%d")})
        st.download_button("Baixar a lista (CSV)", v.to_csv(index=False, sep=";").encode("utf-8-sig"),
                           file_name="concorrentes_por_filial.csv", mime="text/csv", icon=":material/download:")
    else:
        blocos = []
        for (uf, fil), g in list(v.groupby(["Estado", "Filial"], sort=True))[:300]:
            chips = []
            for (band,), gb in g.groupby(["Bandeira"], sort=True):
                lojas = "".join(
                    f"<span class='ps-as-loja{' off' if n == 0 else ''}' title='{_h.escape(str(n))} coletas · última: {_h.escape(u)}'>"
                    f"{_h.escape(c)}<small>{n} · {_h.escape(u)}</small></span>"
                    for c, n, u in zip(gb["Concorrente"], gb["Coletas no período"], gb["Última coleta"]))
                chips.append(f"<div class='ps-as-band'><b>{_h.escape(band)}</b><div>{lojas}</div></div>")
            blocos.append(f"<div class='ps-as-fil'><div class='ps-as-cab'><span>{_h.escape(fil)}</span><em>{_h.escape(uf)}</em>"
                          f"<i>{g['Concorrente'].nunique()} concorrentes</i></div>{''.join(chips)}</div>")
        st.html("<style>.ps-as-grade{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px}"
                ".ps-as-fil{border:1px solid var(--ps-line);border-radius:14px;padding:12px 14px;background:var(--ps-surface-solid)}"
                ".ps-as-cab{display:flex;align-items:baseline;gap:8px;margin-bottom:8px}.ps-as-cab span{font-weight:600;color:var(--ps-ink)}"
                ".ps-as-cab em{font-style:normal;font-size:.75rem;color:var(--ps-muted)}.ps-as-cab i{margin-left:auto;font-style:normal;font-size:.75rem;color:var(--ps-primary)}"
                ".ps-as-band{margin-top:6px}.ps-as-band b{display:block;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ps-muted);margin-bottom:4px}"
                ".ps-as-band div{display:flex;flex-wrap:wrap;gap:6px}.ps-as-loja{display:inline-flex;flex-direction:column;padding:5px 9px;border-radius:9px;"
                "border:1px solid var(--ps-line);background:var(--ps-raised);font-size:.82rem;color:var(--ps-ink);line-height:1.25}"
                ".ps-as-loja small{font-size:.7rem;color:var(--ps-muted)}.ps-as-loja.off{border-color:var(--ps-down);color:var(--ps-down)}</style>"
                f"<div class='ps-as-grade'>{''.join(blocos)}</div>")
        if v["Filial"].nunique() > 300:
            st.caption("Mostrando as 300 primeiras filiais. Use o filtro de estado ou a busca para ver as demais.")
    if len(sem):
        with st.expander(f"Filiais sem concorrente associado ({len(sem)})", icon=":material/warning:"):
            st.dataframe(sem, hide_index=True, width="stretch")


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
    st.session_state._setores_lista = sorted({str(u.get("setor")).strip() for u in usuarios if u.get("setor")})
    ativos = sorted([u for u in usuarios if u.get("status") == "Aprovado"],
                    key=lambda u: (not presenca.resumo(u)["online"], not u.get("is_admin"), (u.get("nome") or "").lower()))
    online = sum(1 for u in ativos if presenca.resumo(u)["online"])
    bloqueados = [u for u in usuarios if u.get("status") not in ("Pendente", "Aprovado")]
    pedidos_cluster = db.listar_solicitacoes_cluster()
    from core import aprovacoes as ap
    uploads = ap.pendentes()

    ui.indicadores([
        ("Aguardando aprovação", len(pendentes), "relogio", "aviso" if pendentes else "neutro"),
        ("Usuários ativos", len(ativos), "pessoas", "primary"),
        ("Online agora", online, "sinal", "ok"),
        ("Clusters para mapear", len(pedidos_cluster), "mapa", "alerta" if pedidos_cluster else "neutro"),
        ("Uploads para aprovar", len(uploads), "enviar", "aviso" if uploads else "neutro"),
    ])

    _painel_trafego()
    abas = st.tabs([f"Solicitações ({len(pendentes)})", f"Usuários ({len(ativos)})",
                    f"Clusters ({len(pedidos_cluster)})", f"Bloqueados ({len(bloqueados)})", f"Uploads ({len(uploads)})",
                    "Concorrentes por filial"])

    with abas[5]:
        _aba_concorrentes()

    with abas[4]:
        if not uploads:
            ui.vazio("Nenhum upload aguardando", "Regras do Profimetrics e bases PROP% enviadas por usuários aparecem aqui antes de ir para o Supabase.")
        for u in uploads:
            with st.container(border=True, key=f"psc_up_{u['id']}"):
                c1, c2, c3 = st.columns([3, 0.8, 0.8], vertical_alignment="center")
                res = ", ".join(f"{ui.numero(v)} {k}" if isinstance(v, (int, float)) else f"{k}: {v}" for k, v in (u.get("resumo") or {}).items())
                c1.html(f"<b>{ui.esc(ap.TIPOS.get(u['tipo'], u['tipo']))}</b><br><span style='color:var(--ps-muted);font-size:.86rem'>"
                        f"{ui.esc(u.get('usuario'))} enviou {ui.esc(u.get('nome_arquivo') or '')}"
                        f"{' em ' + ui.esc(str(u.get('criado_em'))[:16].replace('T', ' ')) if u.get('criado_em') else ''}"
                        f"{': ' + ui.esc(res) if res else ''}</span>")
                editados = None
                if u.get("tipo") == "margens":                      # o administrador pode editar as margens antes de aprovar
                    import json as _json
                    import pandas as _pd
                    try:
                        ped = _json.loads(ap.conteudo(u))
                        st.caption(f"Escopo: {ped.get('escopo')} · origem: {ped.get('origem')}" + (f" · observação: {ped.get('obs')}" if ped.get("obs") else "")
                                   + ". Edite as margens antes de aprovar, se precisar; o solicitante recebe o aviso com as modificações.")
                        tab = _pd.DataFrame([{"Produto": i["produto"], "Objetiva atual": i.get("obj_atual"), "Mínima atual": i.get("min_atual"),
                                              "Máxima atual": i.get("max_atual"), "Nova objetiva": i["obj"], "Nova mínima": i["min"], "Nova máxima": i["max"]}
                                             for i in ped["itens"]])
                        ed = st.data_editor(tab, key=f"up_ed_{u['id']}", hide_index=True, width="stretch",
                                            disabled=["Produto", "Objetiva atual", "Mínima atual", "Máxima atual"],
                                            column_config={c: st.column_config.NumberColumn(c, format="%.1f%%") for c in tab.columns if c != "Produto"})
                        editados = [{"produto": r["Produto"], "codigo": (ped["itens"][k].get("codigo") if k < len(ped["itens"]) else None),
                                     "obj": float(r["Nova objetiva"]), "min": float(r["Nova mínima"]), "max": float(r["Nova máxima"])}
                                    for k, (_, r) in enumerate(ed.iterrows())]
                    except Exception as exc:
                        st.error(f"Não foi possível abrir o pedido: {exc}", icon=":material/error:")
                if c2.button("Aprovar", type="primary", key=f"up_ok_{u['id']}", width="stretch"):
                    try:
                        barra = st.progress(0.0, text="Gravando no Supabase")
                        msg = ap.aprovar(u, st.session_state.get("usuario_login", ""), progresso=lambda x: barra.progress(x, text="Gravando no Supabase"),
                                         itens_editados=editados)
                        st.toast(f"Aprovado e gravado: {msg}.", icon=":material/check_circle:")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Não foi possível gravar: {exc}", icon=":material/error:")
                if c3.button("Recusar", key=f"up_no_{u['id']}", width="stretch"):
                    ap.recusar(u, st.session_state.get("usuario_login", ""))
                    st.rerun()

    with abas[0]:
        if not pendentes:
            ui.vazio("Nenhuma solicitação pendente", "Novos pedidos de acesso aparecem aqui.")
        for u in pendentes:
            with st.container(border=True, key=f"psc_pend_{u['usuario']}"):
                c1, c2, c3, c4 = st.columns([1.6, 1.8, 0.8, 0.8], vertical_alignment="center")
                c1.html(f"<b>{ui.esc(u.get('nome') or '')}</b><br><span style='color:var(--ps-muted);font-size:.86rem'>"
                        f"{ui.esc(u['usuario'])}, matrícula {ui.esc(u.get('matricula') or '-')}, {ui.esc(u.get('cargo') or 'sem cargo')}</span>")
                perms = c2.multiselect("Liberar", auth.TODAS_PERMISSOES, default=["Preço Bot"], key=f"apr_perm_{u['usuario']}", format_func=auth.nome_exibido,
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
