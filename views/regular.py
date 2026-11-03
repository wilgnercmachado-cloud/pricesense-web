"""Pricing Regular: mesa de precificação sobre a base do relatório Competitividade Pricing GMAT."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import db
from core import gmat_reader as gr
from core import precificacao as pr
from core import profimetrics as pf
from core import proporcoes as pp
from core import reports
from ui import components as ui
from ui import theme

RAIZ = Path(__file__).resolve().parent.parent
# Componente bidirecional: a mesa roda no navegador e devolve ao Python só a visão que o usuário salvar.
_MESA = components.declare_component("mesa_precificacao", path=str(RAIZ / "ui" / "metrics_comp"))
TELA = "pricing_regular"
FILTROS = ["Estado", "Diretor regional", "Filial", "Departamento", "Comprador", "Categoria"]
PADRAO = {"cesta": True, "sem_acoes": False, "pesquisa": "Com pesquisa", **{f: [] for f in FILTROS}}   # padrão: com pesquisa e só cesta, todos os estados
LIMITE = 400_000


@st.cache_resource(show_spinner=False, max_entries=1)
def _base_publicada(caminho: str, partes: int, versao: str, leitor: str = "") -> tuple[pd.DataFrame, dict]:
    return gr.ler_de_gzip_ou_html(reports.baixar_conteudo({"arquivo_path": caminho, "partes": partes}))


def _relatorio_padrao() -> dict | None:
    """Sempre o Competitividade Pricing GMAT mais recente da biblioteca."""
    todos = sorted(reports.listar(), key=lambda r: r.get("atualizado_em") or "", reverse=True)
    titulo = lambda r: (r.get("titulo") or "").lower()
    return (next((r for r in todos if "competitividade pricing gmat" in titulo(r)), None)
            or next((r for r in todos if "gmat" in titulo(r)), None))


@st.cache_resource(show_spinner=False, max_entries=1)
def _com_1067(base_id: str, em_1067: str, _df: pd.DataFrame, _meta: dict, _pacote: dict) -> tuple[pd.DataFrame, dict]:
    """Base do HTML somada à 1067 (sem mexer na cópia em cache do HTML)."""
    from core import pesquisa_1067 as p67
    ext = p67.para_indices(_pacote, _df, _meta["coletas"]["K"])
    df = _df.assign()                                     # cópia rasa: só as colunas do vencedor são trocadas
    recorte = gr.aplicar_vencedor(df, _meta["coletas"], ext)
    return df, dict(_meta, recorte=recorte, p1067={**_pacote["meta"], "na_base": int(len(ext["p"])), "fora_da_base": ext["fora_da_base"]})


def base_atual() -> tuple[pd.DataFrame, dict, dict] | None:
    """Base do Competitividade Pricing GMAT + a 1067 enviada para este mesmo HTML (se houver). Sem interface."""
    from core import pesquisa_1067 as p67
    rel = _relatorio_padrao()
    if rel is None:
        return None
    df, meta = _base_publicada(rel["arquivo_path"], int(rel.get("partes") or 1), str(rel.get("atualizado_em")), gr.VERSAO)
    base_id = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    pacote = p67.carregar(base_id)
    if pacote and meta.get("coletas"):
        df, meta = _com_1067(base_id, pacote["meta"]["em"], df, meta, pacote)
    return df, meta, rel


def _fonte() -> tuple[pd.DataFrame, dict, dict] | None:
    rel = _relatorio_padrao()
    if rel is None:
        ui.vazio("Base não encontrada", "Publique o relatório Competitividade Pricing GMAT na biblioteca de relatórios. "
                                        "A mesa usa sempre a versão mais recente dele.")
        return None
    try:
        with st.spinner("Lendo a base do Competitividade Pricing GMAT (alguns segundos na primeira vez)"):
            return base_atual()
    except gr.ErroLeitura as exc:
        st.error(str(exc), icon=":material/error:")
    except Exception as exc:
        st.error(f"Não foi possível ler o relatório: {exc}", icon=":material/error:")
    return None


def _filtros(df: pd.DataFrame) -> dict:
    """Filtros num botão, aplicados na hora a cada clique (sem botão Aplicar)."""
    ss = st.session_state
    for k, v in PADRAO.items():
        ss.setdefault(f"rf_{k}", list(v) if isinstance(v, list) else v)
    ativos = sum(bool(ss[f"rf_{c}"]) for c in FILTROS) + sum(ss[f"rf_{k}"] != PADRAO[k] for k in ("pesquisa", "cesta", "sem_acoes"))
    with st.popover(f"{ativos}" if ativos else "", icon=":material/filter_list:", help="Filtros da análise"):
        st.segmented_control("Itens", ["Com pesquisa", "Sem pesquisa"], key="rf_pesquisa", required=True,
                             help="Sem pesquisa: o varejo vai para a margem objetiva e o atacado sai do objetivo com a base de redução.")
        c1, c2 = st.columns(2)
        for n, col in enumerate(FILTROS):
            opcoes = sorted(str(v) for v in pd.unique(df[col]) if pd.notna(v) and str(v).strip())
            ss[f"rf_{col}"] = [v for v in ss[f"rf_{col}"] if v in opcoes]
            (c1 if n % 2 == 0 else c2).multiselect(col, opcoes, key=f"rf_{col}", placeholder="Todos")
        c3, c4 = st.columns(2)
        c3.toggle("Só cesta", key="rf_cesta")
        c4.toggle("Sem itens em ação", key="rf_sem_acoes", help="Tira encarte, mídia, vencimento e travados. Desligado, eles entram e caem na regra de corte.")
        if st.button("Limpar filtros", width="stretch", icon=":material/filter_alt_off:", key="rf_limpar"):
            for k, v in PADRAO.items():
                ss[f"rf_{k}"] = list(v) if isinstance(v, list) else v
            st.rerun()
    return {k: (list(ss[f"rf_{k}"]) if isinstance(PADRAO[k], list) else ss[f"rf_{k}"]) for k in PADRAO}


def _pesquisa_1067(rel: dict, meta: dict) -> None:
    """Upload da 1067: a pesquisa mais recente somada ao HTML (que chega em D+1)."""
    from core import pesquisa_1067 as p67
    base_id = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    atual = meta.get("p1067")
    eu = st.session_state.get("usuario_login", "")
    with st.popover(atual["dias"][-1][:5] if atual else "", icon=":material/add_chart:", help="Pesquisa mais recente (1067)"):
        st.markdown("**Pesquisa mais recente (1067)**")
        st.caption("O HTML chega no dia seguinte à pesquisa. Cada usuário envia a sua 1067: todas são somadas ao histórico deste HTML, "
                   "e na mesma filial + produto + concorrente + data vale a coleta mais recente enviada. Com HTML novo, os envios são descartados.")
        if atual:
            st.caption(f"Na base agora: {ui.numero(atual['na_base'])} coletas de {', '.join(d[:5] for d in atual['dias'])}, "
                       f"{atual['filiais']} filiais e {atual['concorrentes']} concorrentes"
                       + (f"; {ui.numero(atual['fora_da_base'])} coletas de filiais ou produtos fora do HTML ficaram de fora." if atual.get("fora_da_base") else "."))
            for e in atual.get("envios", []):
                st.caption(f"• {e['usuario']}: {ui.numero(e['linhas'])} coletas de {', '.join(d[:5] for d in e['dias'])}, "
                           f"{e['filiais']} filiais, em {str(e['em'])[:16].replace('T', ' ')}")
        st.caption("Colunas obrigatórias: " + ", ".join(p67.OBRIGATORIAS.values()) + ". Aceita CSV, XLSX ou ZIP.")
        arqs = st.file_uploader("1067", type=["csv", "txt", "xlsx", "xls", "zip"], accept_multiple_files=True, key="reg_1067", label_visibility="collapsed")
        c1, c2 = st.columns(2)
        if c1.button("Somar à base", type="primary", width="stretch", icon=":material/add_chart:", disabled=not arqs, key="reg_1067_ok"):
            try:
                with st.spinner("Lendo a 1067 e somando à base"):
                    lido = p67.ler(arqs)
                    m = p67.salvar(lido, base_id, eu)
                st.toast(f"1067 somada: {ui.numero(m['linhas'])} coletas de {', '.join(d[:5] for d in m['dias'])}.", icon=":material/check_circle:")
                st.rerun()
            except p67.Erro1067 as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível gravar a 1067: {exc}", icon=":material/error:")
        meu = any(e.get("usuario") == eu for e in (atual or {}).get("envios", []))
        if meu and c2.button("Remover a minha 1067", width="stretch", icon=":material/delete:", key="reg_1067_rm"):
            p67.remover(eu); st.rerun()


def _profimetrics() -> pd.DataFrame:
    regras, meta = pf.carregar()
    with st.popover("", icon=":material/tune:", help="Regras de margem (Profimetrics)"):
        if meta:
            st.caption(f"{ui.numero(meta['linhas'])} regras do Profimetrics, {meta['zonas']} zonas, {ui.numero(meta['produtos'])} produtos. "
                       f"Atualizadas em {meta['atualizado_em']}.")
        else:
            st.caption("Nenhuma regra salva: a mesa usa margem objetiva de 10% e máxima de 30%.")
        st.caption("Envie a planilha Detalhes Produtos do Profimetrics. Ela fica salva no Supabase até o próximo envio: "
                   "o arquivo novo substitui a regra do mesmo produto na mesma zona, e o resto é mantido.")
        arq = st.file_uploader("Planilha Profimetrics (XLSX)", type=["xlsx", "xls"], key="reg_pf", label_visibility="collapsed")
        if st.button("Salvar no Supabase", type="primary", width="stretch", icon=":material/cloud_upload:", disabled=arq is None, key="reg_pf_salvar"):
            try:
                with st.spinner("Lendo a planilha e mesclando com as regras salvas"):
                    r = pf.salvar(pf.ler_planilha(arq), st.session_state.get("usuario_logado", ""))
                st.toast(f"Regras salvas: {ui.numero(r['novas'])} novas, {ui.numero(r['substituidas'])} substituídas, "
                         f"{ui.numero(r['mantidas'])} mantidas.", icon=":material/check_circle:")
                st.rerun()
            except pf.ErroProfimetrics as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível salvar no Supabase: {exc}", icon=":material/error:")
        st.divider()
        props = pp.carregar()
        st.markdown("**Proporcionais (base PROP%)**")
        st.caption((f"{ui.numero(len(props))} produtos filhos com proporção na dim_produto. " if len(props) else "Nenhuma proporção cadastrada. ")
                   + "Envie a base com ID_PRODUTO, ID_PAI e Proporcao. Ela define o PAI de cada família (a mesa precifica só o PAI) "
                   "e os proporcionais; cada envio substitui a proporção do mesmo produto.")
        arq_p = st.file_uploader("Base PROP% (XLSX)", type=["xlsx", "xls"], key="reg_prop", label_visibility="collapsed")
        if st.button("Salvar proporções", width="stretch", icon=":material/cloud_upload:", disabled=arq_p is None, key="reg_prop_salvar"):
            try:
                barra = st.progress(0.0, text="Cruzando com a dim_produto e gravando as proporções")
                r = pp.salvar(pp.ler_planilha(arq_p), progresso=lambda x: barra.progress(x, text="Gravando as proporções"))
                barra.empty()
                st.toast(f"{ui.numero(r['salvas'])} proporções gravadas"
                         + (f"; {ui.numero(r['fora_da_dim'])} produtos não existem na dim_produto." if r["fora_da_dim"] else "."), icon=":material/check_circle:")
                st.rerun()
            except pp.ErroProporcao as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível gravar: {exc}. Confira se as colunas id_pai e proporcao existem na dim_produto "
                         "(supabase/migrations.sql).", icon=":material/error:")
    return regras


def _tokens_css() -> str:
    t = theme.tokens()
    nomes = ["canvas", "surface", "surface_solid", "field", "raised", "ink", "muted", "faint", "line", "line_strong", "primary", "primary_hover",
             "primary_soft", "up", "up_soft", "down", "amber", "amber_soft"]
    return "".join(f"--{k.replace('_', '-')}:{t[k]};" for k in nomes) + f"--shadow:{t['shadow']};"


@st.cache_resource(show_spinner=False, max_entries=4)
def _dados_mesa(filtros: str, versao: str, _df_all, _meta, _regras, _props) -> tuple[str | None, int, str]:
    """Pacote da mesa guardado por filtro + versão da base e das regras: reabrir a página não refaz o cálculo."""
    f = json.loads(filtros)
    mask = np.ones(len(_df_all), dtype=bool)
    for col in FILTROS:
        if f.get(col):
            mask &= _df_all[col].isin(f[col]).to_numpy()
    b = pr.base(_df_all[mask], so_cesta=f["cesta"], ignorar_acoes=f["sem_acoes"], regras=_regras, com_pesquisa=f["pesquisa"] == "Com pesquisa", props=_props)
    if b.empty:
        return None, 0, ""
    if len(b) > LIMITE:
        return None, len(b), ""
    dados = pr.payload(b, _meta.get("hist"), _props)
    return dados, len(b), hashlib.md5((dados[:4000] + dados[-4000:] + str(len(dados))).encode()).hexdigest()[:12]


@st.cache_resource(show_spinner=False, max_entries=1)
def _abrir_backup(caminho: str, versao: str) -> dict:
    return json.loads(gzip.decompress(db.ler_backup(caminho)))


def render() -> None:
    st.html("<style>[data-testid='stMainBlockContainer']{max-width:none !important;padding:4.1rem 1rem 0 1rem !important}"
            # filtros e regras ficam na barra do topo, ao lado dos botões de tela cheia e tema
            ".st-key-reg_topo{position:fixed !important;top:11px;right:122px;z-index:1000002;width:auto !important;gap:6px}"
            ".st-key-reg_topo [data-testid='stPopover'] > div > button,.st-key-reg_topo [data-testid='stPopover'] button{height:38px;min-height:38px;"
            "border-radius:19px;padding:0 12px;background:var(--ps-surface);border:1px solid var(--ps-line)}"
            "[data-testid='stMainBlockContainer'] [data-testid='stVerticalBlock']{gap:.4rem}</style>")
    fonte = _fonte()
    if fonte is None:
        return
    df_all, meta, rel = fonte

    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="reg_topo"):
        f = _filtros(df_all)
        _pesquisa_1067(rel, meta)
        regras = _profimetrics()
    dtfim = meta.get("com_data_fim", 0)
    info = (f"{rel.get('titulo')}: base de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}. "
            + (f"Data fim (DTFIM) em {ui.numero(dtfim)} itens." if dtfim else "DTFIM vazia nesta base.")
            + (f" Preço vencedor: nos últimos 3 dias de pesquisa de cada filial (coletas de {meta['recorte'][0]} a {meta['recorte'][-1]}), a coleta mais recente de cada concorrente associado; "
               "se nesse dia ela for encarte, mídia, validade ou outro tipo fora de regular, promoção e ponto extra, o concorrente sai." if meta.get("recorte") else "")
            + (f" Pesquisa 1067 somada: {', '.join(d[:5] for d in meta['p1067']['dias'])}." if meta.get("p1067") else ""))

    props = pp.carregar()
    _, pf_meta = pf.carregar()
    versao = "|".join([str(rel.get("id")), str(rel.get("atualizado_em")), gr.VERSAO, str((meta.get("p1067") or {}).get("em")), str(pf_meta.get("atualizado_em")), str(pf_meta.get("linhas")),
                       str(len(props)), str(float(props["proporcao"].sum()) if len(props) else 0)])
    filtros = json.dumps({k: (sorted(v) if isinstance(v, list) else v) for k, v in f.items()}, sort_keys=True, ensure_ascii=False)
    dados, n, chave = _dados_mesa(filtros, versao, df_all, meta, regras, props)
    if n == 0:
        ui.vazio("Nada para precificar com esses filtros", "Abra os filtros e amplie a seleção.")
        return
    if dados is None:
        st.warning(f"A seleção tem {ui.numero(n)} itens. Abra os filtros e escolha estado, diretor ou filiais "
                   f"para ficar abaixo de {ui.numero(LIMITE)} e a mesa responder na hora.", icon=":material/filter_alt:")
        return
    usuario = st.session_state.get("usuario_login", "")
    if "reg_visao" not in st.session_state:
        st.session_state.reg_visao = db.carregar_visao(usuario, TELA)
    base_id = f"{rel.get('id')}:{rel.get('atualizado_em')}"
    backups = db.listar_backups(usuario)
    historico, estado = None, None
    aberto = st.session_state.get("reg_backup")
    if aberto:
        try:
            with st.spinner(f"Abrindo o backup de {aberto['dia']}"):
                pacote = _abrir_backup(aberto["caminho"], aberto.get("criado_em", ""))
            dados, chave, estado = pacote["dados"], "bkp-" + aberto["dia"] + "-" + pacote.get("chave", ""), pacote.get("estado") or {}
            historico = {"dia": aberto["dia"], "criado_em": aberto.get("criado_em", ""), "resumo": aberto.get("resumo") or {},
                         "info": pacote.get("info", ""), "filtros": pacote.get("filtros") or {}}
            info = pacote.get("info", info)
        except Exception as exc:
            st.session_state.pop("reg_backup", None)
            st.error(f"Não foi possível abrir o backup: {exc}", icon=":material/error:")
    retorno = _MESA(app="price", dados=dados, chave=chave, tokens=_tokens_css(), fonte=theme.FONTE_URL, visao=st.session_state.reg_visao,
                    altura=900, info=info, usuario=usuario, base=base_id, backups=backups, historico=historico, estado=estado,
                    key="mesa_regular", default=None)
    if isinstance(retorno, dict) and retorno.get("ts") != st.session_state.get("_reg_ts") and retorno.get("acao") in ("backup", "abrir_backup", "sair_backup"):
        st.session_state._reg_ts = retorno.get("ts")
        acao = retorno["acao"]
        if acao == "backup" and not historico:
            try:
                dia = retorno.get("dia") or str(pd.Timestamp.now(tz="America/Bahia").date())
                pacote = {"dados": dados, "chave": chave, "estado": retorno.get("estado") or {}, "info": info, "filtros": f, "base": base_id}
                conteudo = gzip.compress(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")).encode(), 6)
                db.salvar_backup(usuario, dia, conteudo, retorno.get("resumo") or {})
                if not retorno.get("silencioso"):
                    st.toast(f"Backup de {dia} salvo. Ficam guardados os últimos 3 dias.", icon=":material/history:")
            except Exception:
                st.toast("Não foi possível salvar o backup: crie a tabela backups_precificacao (supabase/migrations.sql).", icon=":material/error:")
        elif acao == "abrir_backup":
            alvo = next((b for b in backups if str(b.get("dia")) == str(retorno.get("dia"))), None)
            if alvo:
                st.session_state.reg_backup = alvo
                st.rerun()
        elif acao == "sair_backup":
            st.session_state.pop("reg_backup", None)
            st.rerun()
    if isinstance(retorno, dict) and retorno.get("acao") == "salvar_visao" and retorno.get("ts") != st.session_state.get("_reg_ts"):
        st.session_state._reg_ts = retorno.get("ts")
        try:
            db.salvar_visao(usuario, TELA, retorno.get("visao") or {})
            st.session_state.reg_visao = retorno.get("visao")
            st.toast("Visão salva no seu perfil. Ela abre assim sempre que você entrar.", icon=":material/bookmark_added:")
        except Exception:
            st.toast("Não foi possível salvar a visão: crie a tabela visoes_usuario no Supabase (supabase/migrations.sql).", icon=":material/error:")
