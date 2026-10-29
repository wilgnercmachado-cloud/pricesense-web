"""Acesso ao Supabase e dados de apoio (com cache)."""
from __future__ import annotations

import pandas as pd
import streamlit as st


class ConfigError(RuntimeError):
    """Credenciais ausentes em st.secrets."""


@st.cache_resource(show_spinner=False)
def _criar_cliente(url: str, key: str):
    from supabase import create_client
    try:
        from supabase import ClientOptions
        return create_client(url, key, options=ClientOptions(storage_client_timeout=300, postgrest_client_timeout=60))
    except Exception:
        return create_client(url, key)


def get_client():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception as exc:  # arquivo de secrets ausente ou chave faltando
        raise ConfigError("SUPABASE_URL e SUPABASE_KEY não estão configurados em st.secrets.") from exc
    return _criar_cliente(url, key)


def sb():
    return get_client()


# ---------------------------------------------------------------- lojas e mídia
@st.cache_data(ttl=3600, show_spinner=False)
def estados() -> list[str]:
    try:
        dados = sb().table("lojas").select("estado").execute().data
        return sorted({r["estado"] for r in dados if r.get("estado")})
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def diretores(estados_sel: tuple[str, ...]) -> list[str]:
    if not estados_sel:
        return []
    try:
        dados = sb().table("lojas").select("diretor").in_("estado", list(estados_sel)).execute().data
        return sorted({r["diretor"] for r in dados if r.get("diretor")})
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def filiais(estados_sel: tuple[str, ...], diretores_sel: tuple[str, ...]) -> list[str]:
    if not estados_sel:
        return []
    try:
        query = sb().table("lojas").select("filial").in_("estado", list(estados_sel))
        if diretores_sel:
            query = query.in_("diretor", list(diretores_sel))
        return sorted({r["filial"] for r in query.execute().data if r.get("filial")})
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def tipos_midia() -> list[str]:
    try:
        dados = sb().table("tipo_ofertas").select("tipo_preço").execute().data
        return sorted({r["tipo_preço"] for r in dados if r.get("tipo_preço")})
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def clusters() -> pd.DataFrame:
    try:
        resp = sb().table("filial-cluster").select("*").execute()
        if resp.data:
            return pd.DataFrame(resp.data)
    except Exception:
        pass
    return pd.DataFrame(columns=["CLUSTER", "ID FILIAL"])


@st.cache_data(ttl=600, show_spinner=False)
def mapa_lojas() -> dict[str, str]:
    try:
        dados = sb().table("lojas").select("filial").execute().data
        return {str(r["filial"]).split("-")[0].strip(): str(r["filial"]) for r in dados}
    except Exception:
        return {}


@st.cache_data(ttl=3600, show_spinner=False)
def dim_empresa_conc() -> pd.DataFrame:
    try:
        return pd.DataFrame(sb().table("dim_empresa_concorrente").select("*").execute().data)
    except Exception:
        return pd.DataFrame()


def buscar_produtos(codigos: list[int]) -> list[dict]:
    dados: list[dict] = []
    for i in range(0, len(codigos), 300):
        lote = codigos[i:i + 300]
        try:
            resp = (sb().table("dim_produto")
                    .select("id_produto, id_fornecedor, categoria_comercial")
                    .in_("id_produto", lote).execute())
            if resp.data:
                dados.extend(resp.data)
        except Exception:
            pass
    return dados


def buscar_fornecedores(ids: list[int]) -> list[dict]:
    dados: list[dict] = []
    for i in range(0, len(ids), 300):
        lote = ids[i:i + 300]
        try:
            resp = (sb().table("dim_fornecedor")
                    .select("id_fornecedor, nome_grupo_empresarial")
                    .in_("id_fornecedor", lote).execute())
            if resp.data:
                dados.extend(resp.data)
        except Exception:
            pass
    return dados


# ---------------------------------------------------------------- usuários
def buscar_usuario(login: str) -> dict | None:
    dados = sb().table("usuarios").select("*").eq("usuario", login).execute().data
    return dados[0] if dados else None


def pendentes() -> list[dict]:
    return sb().table("usuarios").select("usuario, nome").eq("status", "Pendente").execute().data or []


def listar_usuarios() -> list[dict]:
    return sb().table("usuarios").select("*").execute().data or []


def atualizar_usuario(login: str, campos: dict) -> None:
    sb().table("usuarios").update(campos).eq("usuario", login).execute()


def inserir_usuario(registro: dict) -> None:
    sb().table("usuarios").insert(registro).execute()


# ---------------------------------------------------------------- clusters
def solicitar_cluster(cluster: str, id_filial: str, solicitante: str) -> None:
    sb().table("solicitacoes_cluster").insert({
        "cluster": cluster, "id_filial": id_filial,
        "status": "Pendente", "solicitante": solicitante,
    }).execute()


def listar_solicitacoes_cluster() -> list[dict]:
    try:
        return sb().table("solicitacoes_cluster").select("*").eq("status", "Pendente").execute().data or []
    except Exception:
        return []


def aprovar_cluster(solicitacao: dict) -> None:
    id_filial = str(solicitacao["id_filial"]).strip()
    valor_filial = int(id_filial) if id_filial.isdigit() else id_filial
    sb().table("filial-cluster").insert({"CLUSTER": solicitacao["cluster"], "ID FILIAL": valor_filial}).execute()
    sb().table("solicitacoes_cluster").update({"status": "Aprovado"}).eq("id", solicitacao["id"]).execute()
    clusters.clear()


def recusar_cluster(solicitacao: dict) -> None:
    sb().table("solicitacoes_cluster").update({"status": "Recusado"}).eq("id", solicitacao["id"]).execute()
