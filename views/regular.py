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

from core import auth, db
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
PADRAO = {"cesta": True, "pesquisa": "Com pesquisa", **{f: [] for f in FILTROS}}   # padrão: com pesquisa e só cesta, todos os estados
LIMITE = 400_000


@st.cache_resource(show_spinner=False, max_entries=1)
def _base_publicada(caminho: str, partes: int, versao: str, leitor: str = "") -> tuple[pd.DataFrame, dict]:
    """Base do relatório. Na primeira leitura de cada HTML o resultado fica salvo pronto no Storage:
    depois de um reinício do servidor, a base volta em ~1 s e com pouca memória, sem reler o HTML (que pesa)."""
    import gc
    import pickle
    import re as _re
    pronto = f"cache_base/{_re.sub(r'[^A-Za-z0-9_.-]', '_', caminho)}_{_re.sub(r'[^0-9]', '', versao)}_{_re.sub(r'[^0-9A-Za-z]', '', leitor)}.pkl.gz"
    try:
        df, meta = pickle.loads(gzip.decompress(db.sb().storage.from_("relatorios").download(pronto)))
        return df, meta
    except Exception:
        pass
    df, meta = gr.ler_de_gzip_ou_html(reports.baixar_conteudo({"arquivo_path": caminho, "partes": partes}))
    gc.collect()
    try:
        gz = gzip.compress(pickle.dumps((df, meta), protocol=5), 3)
        if len(gz) < 45 * 1024 * 1024:
            db.sb().storage.from_("relatorios").upload(pronto, gz, {"content-type": "application/gzip", "upsert": "true"})
            antigos = [f"cache_base/{x['name']}" for x in (db.sb().storage.from_("relatorios").list("cache_base") or [])
                       if f"cache_base/{x.get('name')}" != pronto]
            if antigos:
                db.sb().storage.from_("relatorios").remove(antigos)          # só a base atual fica guardada
        del gz
    except Exception:
        pass
    gc.collect()
    return df, meta


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
    hist = _hist_com_1067(_meta.get("hist"), ext, _df, _meta.get("atualizado"))
    gr.aplicar_moda(df, hist)                             # moda refeita com as coletas da 1067
    return df, dict(_meta, recorte=recorte, hist=hist,
                    p1067={**_pacote["meta"], "na_base": int(len(ext["p"])), "fora_da_base": ext["fora_da_base"]})


def _hist_com_1067(h: dict | None, ext: dict, df: pd.DataFrame, upd) -> dict | None:
    """Histórico do gráfico de concorrência com as coletas da 1067 somadas (mesma regra: na mesma data e concorrente, vale a 1067)."""
    import datetime as _dt
    if not h or not len(ext["p"]) or "dP" not in h:
        return h
    h = dict(h)
    K = list(h["K"]) + list(ext.get("K_novos", []))
    KE = list(h.get("KE", [])) + [""] * len(ext.get("K_novos", []))
    # dia: rótulo dd/mm do histórico; datas novas entram no fim
    T = list(h["T"])
    ords = gr._ordinais(T, upd)
    pos = {int(o): n for n, o in enumerate(ords)}
    ultimo = int(ords.max()) if len(ords) else 0
    novos = sorted(int(o) for o in set(ext["dia"].tolist()) if int(o) not in pos and int(o) > ultimo)
    for o in novos:
        pos[o] = len(T); T.append(_dt.date.fromordinal(o).strftime("%d/%m"))
    t_idx = np.array([pos.get(int(o), -1) for o in ext["dia"]])
    # estado de cada coleta pela filial
    uf_f = pd.Series(df["Estado"].astype(str).to_numpy(), index=df["_f"].to_numpy()).groupby(level=0).first()
    u_pos = {u: n for n, u in enumerate(h["U"])}
    u_idx = np.array([u_pos.get(uf_f.get(int(f), ""), -1) for f in ext["f"]])
    ok = (t_idx >= 0) & (u_idx >= 0)
    nP, nK, nT = ext["p"][ok].astype(h["dP"].dtype), ext["k"][ok].astype(np.int64), t_idx[ok]
    chave = lambda p, k, t: (p.astype(np.int64) * 100000 + k) * 1000 + t
    fica = ~np.isin(chave(h["dP"], h["dK"].astype(np.int64), h["dT"].astype(np.int64)), chave(nP, nK, nT))
    junta = lambda velho, novo: np.concatenate([np.asarray(velho)[fica], novo.astype(np.asarray(velho).dtype)])
    h.update({"dP": junta(h["dP"], nP), "dU": junta(h["dU"], u_idx[ok]), "dK": junta(h["dK"], nK), "dT": junta(h["dT"], nT),
              "dV": junta(h["dV"], ext["v"][ok]), "dA": junta(h["dA"], ext["a"][ok])})
    if "dTp" in h:
        h["dTp"] = np.concatenate([np.asarray(h["dTp"])[fica], ext["t"][ok].astype(np.asarray(h["dTp"]).dtype)])
    pares = set(zip(np.asarray(h["fil_conc_f"]).tolist(), np.asarray(h["fil_conc_k"]).tolist()))
    pares |= set(zip(ext["f"].tolist(), ext["k"].tolist()))
    pf_, pk_ = zip(*sorted(pares)) if pares else ((), ())
    h.update({"fil_conc_f": np.asarray(pf_, dtype=np.int32), "fil_conc_k": np.asarray(pk_, dtype=np.int32), "K": K, "KE": KE, "T": T})
    return h


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


@st.cache_data(ttl=900, show_spinner=False)
def estados_atuacao() -> list[str]:
    """Siglas dos estados em que atuamos: os mesmos da base da PriceMetrics."""
    try:
        fonte = base_atual()
        if fonte:
            return sorted({str(e).split(" - ")[0].strip() for e in fonte[0]["Estado"].astype(str).unique() if str(e).strip()})
    except Exception:
        pass
    return []


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
    """Filtros numa gaveta lateral com fundo desfocado, aplicados na hora a cada clique."""
    ss = st.session_state
    for k, v in PADRAO.items():
        ss.setdefault(f"rf_{k}", list(v) if isinstance(v, list) else v)
    # "Com pesquisa" e "Só cesta" vêm ligados ao abrir e contam como filtros ativos
    ativos = sum(bool(ss[f"rf_{c}"]) for c in FILTROS) + 1 + bool(ss.rf_cesta)
    resumo = ", ".join([ss.rf_pesquisa] + (["só cesta"] if ss.rf_cesta else []) + [f"{c.lower()} ({len(ss[f'rf_{c}'])})" for c in FILTROS if ss[f"rf_{c}"]])
    with st.popover(f"Filtros · {ativos}" if ativos else "Filtros", icon=":material/filter_list:", help="Filtros da análise"):
        ui.gaveta_topo("Filtros", resumo)
        st.segmented_control("Itens", ["Com pesquisa", "Sem pesquisa"], key="rf_pesquisa", required=True, width="stretch",
                             help="Sem pesquisa: o varejo vai para a margem objetiva e o atacado sai do objetivo com a base de redução.")
        for col in FILTROS:
            opcoes = sorted(str(v) for v in pd.unique(df[col]) if pd.notna(v) and str(v).strip())
            ss[f"rf_{col}"] = [v for v in ss[f"rf_{col}"] if v in opcoes]
            st.multiselect(col, opcoes, key=f"rf_{col}", placeholder="Todos")
        st.toggle("Só cesta", key="rf_cesta")
        if st.button("Limpar filtros", width="stretch", key="rf_limpar"):
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
    with st.container():
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


def _pedir_aprovacao(tipo: str, arquivo, validar) -> None:
    """Usuário sem perfil de administrador: confere o arquivo e manda para a fila de aprovação."""
    from core import aprovacoes as ap
    try:
        with st.spinner("Conferindo o arquivo"):
            resumo = validar(arquivo)
            arquivo.seek(0)
            ap.enviar(tipo, st.session_state.get("usuario_login", ""), getattr(arquivo, "name", tipo), arquivo.getvalue(), resumo)
        st.toast("Enviado para aprovação do administrador. Só entra na base depois de aprovado.", icon=":material/pending:")
    except (pf.ErroProfimetrics, pp.ErroProporcao) as exc:
        st.error(str(exc), icon=":material/error:")
    except Exception as exc:
        st.error(f"Não foi possível enviar para aprovação: {exc}. Confira a tabela aprovacoes_upload (supabase/migrations.sql).", icon=":material/error:")


def _meus_pedidos(tipo: str) -> None:
    from core import aprovacoes as ap
    for p in [x for x in ap.meus(st.session_state.get("usuario_login", "")) if x.get("tipo") == tipo][:2]:
        rot = {"pendente": "aguardando aprovação", "aprovado": "aprovado", "recusado": "recusado"}.get(p.get("status"), p.get("status"))
        st.caption(f"Seu envio {p.get('nome_arquivo')} de {str(p.get('criado_em'))[:16].replace('T', ' ')}: {rot}.")


def _data_base(rel: dict, meta: dict) -> str:
    """Data e hora da base em uso: o HTML publicado e, se houver, a última 1067 somada."""
    txt = ui.data_hora(rel.get("atualizado_em")) or str(meta.get("atualizado") or "")
    p1067 = meta.get("p1067")
    if p1067:
        txt += f" + 1067 de {ui.data_hora(p1067.get('em'))[:10]}"
    return txt


def _uploads(rel: dict, meta_base: dict) -> None:
    """Um único botão de upload: pesquisa 1067, regras de margem (Profimetrics) e base PROP%."""
    with st.popover("", icon=":material/cloud_upload:", help="Uploads: pesquisa 1067, regras de margem e proporções"):
        ui.gaveta_topo("Uploads", "Pesquisa do dia, regras de margem e proporcionais")
        aba = st.segmented_control("Upload", ["Pesquisa 1067", "Regras de margem", "Proporções", "Trava mínima (acordo)"], default="Pesquisa 1067", required=True,
                                   key="reg_up_aba", label_visibility="collapsed", width="stretch")
        if aba == "Pesquisa 1067":
            _pesquisa_1067(rel, meta_base)
        elif aba == "Trava mínima (acordo)":
            _trava()
        else:
            _profimetrics(aba)


def _modo_visao() -> str:
    """Setor PRICE: visão de Pricing. Demais setores (ou vazio): visão do Comercial. Administrador escolhe entre as duas."""
    if auth.eh_admin():
        ss = st.session_state
        ss.setdefault("reg_modo_sel", "Pricing")
        st.segmented_control("Visão", ["Pricing", "Comercial"], key="reg_modo_sel", required=True, label_visibility="collapsed")
        return "pricing" if ss.reg_modo_sel == "Pricing" else "comercial"
    setor = str(st.session_state.get("usuario_setor") or "").strip().upper()
    return "pricing" if setor.startswith("PRICE") or setor == "PRICING" else "comercial"


def _formacao(df: pd.DataFrame) -> str:
    """Botão de controle da formação do novo preço: formato (por usuário), percentuais por curva e delta seguro por estado ou filial."""
    from core import parametros as pm
    ss = st.session_state
    usuario = ss.get("usuario_login", "")
    if "reg_formato" not in ss:
        ss.reg_formato = ((db.carregar_visao(usuario, "formacao_preco") or {}).get("formato")) or "Mercado − 0,01"
    params = pm.carregar(usuario)
    admin = auth.eh_admin()
    with st.popover("", icon=":material/tune:", help="Formação do novo preço: formato, curvas de venda e delta seguro"):
        ui.gaveta_topo("Formação do preço", ss.reg_formato)
        novo = st.segmented_control("Formato", ["Mercado − 0,01", "Curva de venda"], default=ss.reg_formato, required=True,
                                    key="reg_formato_sel", width="stretch",
                                    help="Mercado − 0,01: o novo preço fica 1 centavo abaixo do concorrente. Curva de venda: o novo preço fica no "
                                         "percentual da curva (A, B ou C) do item na filial em relação ao concorrente.")
        if novo != ss.reg_formato:
            ss.reg_formato = novo
            try:
                db.salvar_visao(usuario, "formacao_preco", {"formato": novo})
            except Exception:
                pass
            st.rerun()
        st.caption("Os parâmetros abaixo são seus. Valem para um estado inteiro ou para filiais do estado; a filial tem prioridade sobre o estado."
                   + ("" if admin else " Sua mudança vai para aprovação do administrador."))
        ufs = sorted({str(e).split(" - ")[0].strip() for e in df["Estado"].astype(str).unique() if str(e).strip()})
        c1, c2 = st.columns([1, 2])
        uf = c1.selectbox("Estado", ufs, key="reg_par_uf")
        fils = sorted({str(x) for x in df.loc[df["Estado"].astype(str).str.startswith(str(uf) + " "), "Filial"].astype(str).unique()},
                      key=lambda x: int(x.split(" - ")[0]) if x.split(" - ")[0].isdigit() else 0)
        escolhidas = c2.multiselect("Filiais", fils, key="reg_par_fil", placeholder="Todas as filiais do estado")
        cods = [x.split(" - ")[0].strip() for x in escolhidas]
        atual = params[(params["estado"] == uf) & (params["filial"].astype(str) == (cods[0] if len(cods) == 1 else ""))]
        base = atual.iloc[0].to_dict() if len(atual) else pm.PADRAO
        st.markdown("**Curva de venda** <span style='color:var(--ps-muted);font-size:.8rem'>% do preço do concorrente</span>", unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        va = a1.number_input("Curva A (%)", 50.0, 150.0, float(base["curva_a"]), 0.5, key=f"reg_par_a_{uf}_{'-'.join(cods)}")
        vb = a2.number_input("Curva B (%)", 50.0, 150.0, float(base["curva_b"]), 0.5, key=f"reg_par_b_{uf}_{'-'.join(cods)}")
        vc = a3.number_input("Curva C (%)", 50.0, 150.0, float(base["curva_c"]), 0.5, key=f"reg_par_c_{uf}_{'-'.join(cods)}")
        st.markdown("**Delta seguro** <span style='color:var(--ps-muted);font-size:.8rem'>distância máxima entre a pesquisa e a moda</span>", unsafe_allow_html=True)
        d1, d2 = st.columns(2)
        da = d1.number_input("Acima do custo (±%)", 1.0, 100.0, float(base["delta_acima"]), 0.5, key=f"reg_par_da_{uf}_{'-'.join(cods)}",
                             help="Quando o preço da pesquisa fica acima do custo: se ele se afastar da moda mais do que isso, o novo preço sai da moda.")
        db_ = d2.number_input("Abaixo do custo (±%)", 1.0, 100.0, float(base["delta_abaixo"]), 0.5, key=f"reg_par_db_{uf}_{'-'.join(cods)}",
                              help="Quando a pesquisa levaria o preço para baixo do custo: se ela se afastar da moda mais do que isso, o novo preço sai da moda.")
        valores = {"curva_a": va, "curva_b": vb, "curva_c": vc, "delta_acima": da, "delta_abaixo": db_}
        alvo = f"{len(cods)} filial(is) de {uf}" if cods else f"todo o estado {uf}"
        if st.button(f"Aplicar para {alvo}" if admin else f"Enviar para aprovação ({alvo})", type="primary", width="stretch",
                     icon=":material/check:" if admin else ":material/send:", key="reg_par_ok"):
            try:
                if admin:
                    pm.salvar(usuario, uf, cods, valores, usuario)
                    st.toast(f"Parâmetros aplicados para {alvo}.", icon=":material/tune:")
                    st.rerun()
                else:
                    pm.pedir(usuario, uf, cods, valores)
                    st.toast("Pedido enviado. Os parâmetros entram na sua mesa depois da aprovação do administrador.", icon=":material/pending:")
            except Exception as exc:
                st.error(f"Não foi possível gravar: {exc}. Confira a tabela parametros_preco (supabase/migrations.sql).", icon=":material/error:")
        if not admin:
            _meus_pedidos("parametros")
        if len(params):
            st.markdown("**Seus parâmetros em uso**")
            for _, r in params.sort_values(["estado", "filial"]).iterrows():
                q1, q2 = st.columns([5, 1], vertical_alignment="center")
                q1.caption(f"{r['estado']} {('filial ' + str(r['filial'])) if str(r['filial']) else '(estado inteiro)'}: "
                           f"A {r['curva_a']:g}%, B {r['curva_b']:g}%, C {r['curva_c']:g}%, delta +{r['delta_acima']:g}% / −{r['delta_abaixo']:g}%")
                if admin and q2.button("", icon=":material/delete:", key=f"reg_par_rm_{r['estado']}_{r['filial']}", help="Remover"):
                    pm.remover(usuario, r["estado"], str(r["filial"])); st.rerun()
        else:
            st.caption("Sem parâmetros próprios: curvas a 100% e delta de ±25% (acima do custo) e ±15% (abaixo do custo).")
    return "curva" if ss.reg_formato == "Curva de venda" else "mercado"


def _trava() -> None:
    """Trava mínima (acordo): margem mínima por filial e produto, acima da cesta e do Profimetrics."""
    from core import trava as tv
    atual = tv.carregar()
    st.caption("Margem mínima acordada por filial e produto. Vale acima do piso da cesta e da mínima do Profimetrics: o varejo nunca fica "
               "abaixo dela e, quando o preço bate nessa mínima, o atacado sai do varejo com a base de redução.")
    if len(atual):
        st.caption(f"Na base: {ui.numero(len(atual))} travas em {atual['filial'].nunique()} filiais e {ui.numero(atual['produto'].nunique())} produtos. "
                   f"Última atualização: {str(atual['atualizado_em'].max())[:16].replace('T', ' ')}, por {atual.sort_values('atualizado_em')['atualizado_por'].iloc[-1]}.")
    else:
        st.caption("Nenhuma trava cadastrada.")
    st.caption("Colunas: ID filial | ID Produto | Margem Mínima (em %, ex.: 10). Aceita XLSX ou CSV. Um envio substitui a trava da mesma filial e produto; as outras continuam.")
    admin = auth.eh_admin()
    if not admin:
        _meus_pedidos("trava")
    arq = st.file_uploader("Trava mínima", type=["xlsx", "xls", "csv", "txt"], key="reg_trava_arq", label_visibility="collapsed")
    if st.button("Salvar trava mínima" if admin else "Enviar trava para aprovação", type="primary", width="stretch",
                 icon=":material/lock:", disabled=arq is None, key="reg_trava_ok"):
        if not admin:
            try:
                lido = tv.ler_planilha(arq)
                arq.seek(0)
                from core import aprovacoes as ap
                ap.enviar("trava", st.session_state.get("usuario_login", ""), getattr(arq, "name", "trava"), arq.getvalue(),
                          {"travas": int(len(lido)), "filiais": int(lido["filial"].nunique())})
                st.toast("Trava enviada para aprovação do administrador. Só entra na precificação depois de aprovada.", icon=":material/pending:")
            except tv.ErroTrava as exc:
                st.error(str(exc), icon=":material/error:")
            except Exception as exc:
                st.error(f"Não foi possível enviar: {exc}", icon=":material/error:")
            return
        try:
            with st.spinner("Gravando a trava mínima"):
                r = tv.salvar(tv.ler_planilha(arq), st.session_state.get("usuario_login", ""))
            st.toast(f"{ui.numero(r['linhas'])} travas mínimas gravadas.", icon=":material/lock:")
            st.rerun()
        except tv.ErroTrava as exc:
            st.error(str(exc), icon=":material/error:")
        except Exception as exc:
            st.error(f"Não foi possível gravar: {exc}. Confira a tabela trava_minima (supabase/migrations.sql).", icon=":material/error:")
    if admin and len(atual):
        with st.popover("Apagar todas as travas", icon=":material/delete:", width="stretch"):
            st.caption("Remove todas as travas mínimas cadastradas. A precificação volta a usar a cesta e o Profimetrics.")
            if st.button("Confirmar exclusão", type="primary", key="reg_trava_rm"):
                tv.limpar(); st.rerun()


def _profimetrics(secao: str) -> None:
    regras, meta = pf.carregar()
    with st.container():
      if secao == "Regras de margem":
        if meta:
            st.caption(f"{ui.numero(meta['linhas'])} regras do Profimetrics, {meta['zonas']} zonas, {ui.numero(meta['produtos'])} produtos. "
                       f"Atualizadas em {meta['atualizado_em']}.")
        else:
            st.caption("Nenhuma regra salva: a mesa usa margem objetiva de 10% e máxima de 30%.")
        st.caption("Envie a planilha Detalhes Produtos do Profimetrics. Ela fica salva no Supabase até o próximo envio: "
                   "o arquivo novo substitui a regra do mesmo produto na mesma zona, e o resto é mantido.")
        if not auth.eh_admin():
            st.caption("Seu envio vai para aprovação do administrador e só entra na base depois de aprovado.")
            _meus_pedidos("profimetrics")
        arq = st.file_uploader("Planilha Profimetrics (XLSX)", type=["xlsx", "xls"], key="reg_pf", label_visibility="collapsed")
        admin = auth.eh_admin()
        if st.button("Salvar no Supabase" if admin else "Enviar para aprovação", type="primary", width="stretch", icon=":material/cloud_upload:",
                     disabled=arq is None, key="reg_pf_salvar"):
            if not admin:
                _pedir_aprovacao("profimetrics", arq, lambda a: {"regras": int(len(pf.ler_planilha(a)))})
                return
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
      else:
        admin = auth.eh_admin()
        props = pp.carregar()
        st.markdown("**Proporcionais (base PROP%)**")
        st.caption((f"{ui.numero(len(props))} produtos filhos na base PROP% ({ui.numero(int((props['proporcao'] == 100).sum()))} similares 100% e "
                    f"{ui.numero(int((props['proporcao'] != 100).sum()))} proporcionais). " if len(props) else "Nenhuma proporção cadastrada. ")
                   + "Envie a base com ID_PRODUTO, ID_PAI e Proporcao. Ela define o PAI de cada família (a mesa precifica só o PAI) "
                   "e os proporcionais; cada envio substitui a proporção do mesmo produto.")
        if not auth.eh_admin():
            _meus_pedidos("proporcoes")
        arq_p = st.file_uploader("Base PROP% (XLSX)", type=["xlsx", "xls"], key="reg_prop", label_visibility="collapsed")
        if st.button("Salvar proporções" if admin else "Enviar proporções para aprovação", width="stretch", icon=":material/cloud_upload:",
                     disabled=arq_p is None, key="reg_prop_salvar"):
            if not admin:
                _pedir_aprovacao("proporcoes", arq_p, lambda a: (lambda d: {"relacoes": int(len(d)), "similares": int((d["proporcao"] == 100).sum()),
                                                                             "proporcionais": int((d["proporcao"] != 100).sum())})(pp.ler_planilha(a)))
                return
            try:
                barra = st.progress(0.0, text="Cruzando com a dim_produto e gravando as proporções")
                r = pp.salvar(pp.ler_planilha(arq_p), progresso=lambda x: barra.progress(x, text="Gravando as proporções"))
                barra.empty()
                st.toast(f"Base PROP% gravada: {ui.numero(r['salvas'] + r['fora_da_dim'])} relações valem na precificação "
                         f"({ui.numero(r['salvas'])} também na dim_produto).", icon=":material/check_circle:")
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


@st.cache_resource(show_spinner=False, max_entries=3)
def _dados_mesa(filtros: str, versao: str, _df_all, _meta, _regras, _props, _travas=None, _params=None) -> tuple[str | None, int, str]:
    """Pacote da mesa guardado por filtro + versão da base e das regras: reabrir a página não refaz o cálculo."""
    f = json.loads(filtros)
    mask = np.ones(len(_df_all), dtype=bool)
    if f.get("_ufs"):
        mask &= _df_all["Estado"].astype(str).map(auth.sigla_estado).isin(f["_ufs"]).to_numpy()
    for col in FILTROS:
        if f.get(col):
            mask &= _df_all[col].isin(f[col]).to_numpy()
    b = pr.base(_df_all[mask], so_cesta=f["cesta"], ignorar_acoes=False, regras=_regras, com_pesquisa=f["pesquisa"] == "Com pesquisa", props=_props, travas=_travas)
    if b.empty:
        return None, 0, ""
    if len(b) > LIMITE:
        return None, len(b), ""
    from core import parametros as pm
    dados = pr.payload(b, _meta.get("hist"), _props, extra=pm.por_linha(b, _params))
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
    df_base = df_all                                       # base inteira (para encerrar os blocks pela regra)
    permitidos = auth.estados_permitidos()
    if permitidos is not None:
        if not permitidos:
            ui.vazio("Nenhum estado atribuído ao seu usuário", "Peça ao administrador para definir seus estados na Administração.")
            return
        cats = pd.Series(df_all["Estado"].cat.categories.astype(str)) if hasattr(df_all["Estado"], "cat") else None
        if cats is not None:
            ok = cats.map(auth.sigla_estado).isin(permitidos).to_numpy()
            df_all = df_all[ok[df_all["Estado"].cat.codes.to_numpy()]]
        else:
            df_all = df_all[df_all["Estado"].map(auth.sigla_estado).isin(permitidos)]
        if df_all.empty:
            ui.vazio("Sem lojas nos seus estados", f"A base não tem lojas de {', '.join(permitidos)}.")
            return

    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="reg_topo"):
        modo = _modo_visao()
        f = _filtros(df_all)
        if modo == "pricing":
            formato = _formacao(df_all)
            _uploads(rel, meta)
        else:
            formato = "mercado"
    regras, _ = pf.carregar()
    dtfim = meta.get("com_data_fim", 0)
    info = (f"{rel.get('titulo')}: base de {meta.get('atualizado')}, pesquisa de {' a '.join(meta.get('periodo') or [])}. "
            + (f"Data fim (DTFIM) em {ui.numero(dtfim)} itens." if dtfim else "DTFIM vazia nesta base.")
            + (f" Preço vencedor: nos últimos 3 dias de pesquisa de cada filial (coletas de {meta['recorte'][0]} a {meta['recorte'][-1]}), a coleta mais recente de cada concorrente associado; "
               "se nesse dia ela for encarte, mídia, validade ou outro tipo fora de regular, promoção e ponto extra, o concorrente sai." if meta.get("recorte") else "")
            + (f" Pesquisa 1067 somada: {', '.join(d[:5] for d in meta['p1067']['dias'])}." if meta.get("p1067") else ""))

    props = pp.carregar()
    from core import trava as tv, parametros as pm
    travas = tv.carregar()
    params = pm.carregar(st.session_state.get("usuario_login", ""))
    _, pf_meta = pf.carregar()
    versao = "|".join([str(rel.get("id")), str(rel.get("atualizado_em")), gr.VERSAO, str((meta.get("p1067") or {}).get("em")), str(pf_meta.get("atualizado_em")), str(pf_meta.get("linhas")),
                       str(len(props)), str(float(props["proporcao"].sum()) if len(props) else 0),
                       str(len(travas)), str(float(travas["margem_min"].sum()) if len(travas) else 0), str(travas["atualizado_em"].max() if len(travas) else ""),
                       st.session_state.get("usuario_login", ""), str(params.drop(columns=["atualizado_em", "atualizado_por"]).to_dict("records")) if len(params) else ""])
    filtros = json.dumps({**{k: (sorted(v) if isinstance(v, list) else v) for k, v in f.items()}, "_ufs": permitidos or []},
                         sort_keys=True, ensure_ascii=False)          # os estados do usuário entram na chave do pacote guardado
    dados, n, chave = _dados_mesa(filtros, versao, df_all, meta, regras, props, travas, params)
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
    from core import blocks as bk, sugestoes as sg
    lista_blocks = bk.expirar(bk.ativos(), df_base)
    if st.session_state.get("_sug_expira") != sg.hoje():          # pendentes de ontem expiram (uma vez por dia por sessão)
        st.session_state._sug_expira = sg.hoje()
        try:
            sg.expirar_antigas()
        except Exception:
            pass
    lista_sug = [x for x in sg.do_dia() if x.get("status") in ("pendente", "aceita", "rejeitada")]
    retorno = _MESA(app="price", dados=dados, chave=f"{chave}-{formato}-{modo}", formato=formato, modo_visao=modo, admin=auth.eh_admin(),
                    blocks=[{k: b.get(k) for k in ("id", "filial", "produto", "motivo", "observacao", "usuario", "preco_vencedor", "concorrente",
                                                    "data_pesquisa", "criado_em")} for b in lista_blocks], motivos_block=bk.MOTIVOS,
                    sugestoes=[{k: x.get(k) for k in ("id", "filial", "produto", "varejo", "atacado", "motivo", "observacao", "usuario", "criado_em",
                                                      "status", "motivo_rejeicao", "decidido_por", "fora_parametros")} for x in lista_sug],
                    motivos_sugestao=sg.MOTIVOS, tokens=_tokens_css(), fonte=theme.FONTE_URL, visao=st.session_state.reg_visao,
                    altura=900, info=info, usuario=usuario, base=base_id, atualizado=_data_base(rel, meta), backups=backups, historico=historico, estado=estado,
                    key="mesa_regular", default=None)
    if isinstance(retorno, dict) and retorno.get("ts") != st.session_state.get("_reg_ts") and retorno.get("acao") in ("sugerir", "aceitar_sug", "rejeitar_sug", "aplicados"):
        st.session_state._reg_ts = retorno.get("ts")
        try:
            a_ = retorno["acao"]
            if a_ == "sugerir":
                sg.criar(retorno, usuario)
                st.toast("Sugestão enviada ao Pricing do estado.", icon=":material/send:")
            elif a_ == "aceitar_sug":
                n_ = sg.aceitar(retorno.get("ids") or [], usuario)
                st.toast(f"{n_} sugestão(ões) do comprador aceita(s); o comprador foi avisado.", icon=":material/check_circle:")
            elif a_ == "rejeitar_sug":
                sg.rejeitar(retorno.get("id"), usuario, retorno.get("motivo", ""))
                st.toast("Sugestão rejeitada; o comprador recebeu o motivo.", icon=":material/block:")
            else:
                sg.registrar_aplicados(retorno.get("itens") or [])
        except Exception as exc:
            st.toast(f"Não foi possível gravar a sugestão: {exc}", icon=":material/error:")
    if isinstance(retorno, dict) and retorno.get("ts") != st.session_state.get("_reg_ts") and retorno.get("acao") in ("block", "desbloquear"):
        st.session_state._reg_ts = retorno.get("ts")
        try:
            if retorno["acao"] == "block":
                bk.criar(retorno["filial"], retorno["produto"], retorno.get("estado", ""), retorno.get("motivo", ""), retorno.get("observacao", ""),
                         usuario, retorno.get("preco_vencedor") or 0, retorno.get("concorrente", ""), retorno.get("data_pesquisa", ""))
                st.toast("BLOCK registrado: o item fica travado para o Pricing.", icon=":material/block:")
            else:
                alvo = next((b for b in bk.ativos() if b["id"] == retorno.get("id")
                             or (int(b["filial"]) == int(retorno.get("filial") or -1) and int(b["produto"]) == int(retorno.get("produto") or -1))), None)
                if alvo and (auth.eh_admin() or alvo.get("usuario") == usuario):
                    bk.remover(alvo["id"], usuario)
                    st.toast("BLOCK retirado.", icon=":material/lock_open:")
        except Exception as exc:
            st.toast(f"Não foi possível gravar o BLOCK: {exc}", icon=":material/error:")
    if isinstance(retorno, dict) and retorno.get("ts") != st.session_state.get("_reg_ts") and retorno.get("acao") in ("backup", "abrir_backup", "sair_backup"):
        st.session_state._reg_ts = retorno.get("ts")
        acao = retorno["acao"]
        if acao == "backup" and retorno.get("aplicados"):
            try:
                from core import sugestoes as sg_
                sg_.registrar_aplicados(retorno["aplicados"])      # preço aplicado e regra dos itens com sugestão do comprador
            except Exception:
                pass
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
