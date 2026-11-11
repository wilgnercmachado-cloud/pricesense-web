"""Proporcionais: produtos filhos precificados a partir do produto PAI (ex.: pacote 2,5 kg = 250% do PAI).

As proporções ficam na própria dim_produto (colunas id_pai e proporcao) e a base completa no Storage.
Cada envio SOMA à base: substitui a relação dos produtos enviados e mantém o que não foi enviado.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd
import streamlit as st

from core import db


class ErroProporcao(ValueError):
    pass


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def ler_planilha(arquivo) -> pd.DataFrame:
    bruto = None
    for motor in ("calamine", "openpyxl"):
        try:
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            cab = pd.read_excel(arquivo, sheet_name=0, engine=motor, nrows=0)
            usar = [c for c in cab.columns if _norm(c) in ("idproduto", "idpai", "proporcao")]
            if hasattr(arquivo, "seek"):
                arquivo.seek(0)
            bruto = pd.read_excel(arquivo, sheet_name=0, engine=motor, usecols=usar or None)   # só as 3 colunas: leitura bem mais rápida
            break
        except ImportError:
            continue
        except Exception as exc:
            raise ErroProporcao(f"Não foi possível ler a planilha: {exc}") from exc
    if bruto is None:
        raise ErroProporcao("Não foi possível ler a planilha.")
    mapa = {_norm(c): c for c in bruto.columns}
    faltam = [c for c in ("idproduto", "idpai", "proporcao") if c not in mapa]
    if faltam:
        raise ErroProporcao("A planilha precisa das colunas ID_PRODUTO, ID_PAI e Proporcao (como a base PROP%).")
    df = pd.DataFrame({"id_produto": pd.to_numeric(bruto[mapa["idproduto"]], errors="coerce"),
                       "id_pai": pd.to_numeric(bruto[mapa["idpai"]], errors="coerce"),
                       "proporcao": pd.to_numeric(bruto[mapa["proporcao"]], errors="coerce")})
    df = df.dropna()
    df = df[(df["proporcao"] > 0) & (df["id_produto"] != df["id_pai"])]   # 100% (similares) também: definem quem é PAI
    df = df.astype({"id_produto": "int64", "id_pai": "int64"})
    return df.drop_duplicates("id_produto", keep="last").reset_index(drop=True)


def salvar(df: pd.DataFrame, progresso=None) -> dict:
    """Cruza com a dim_produto e grava só id_pai e proporcao nos produtos que já existem nela.

    Nenhuma outra coluna da dim_produto é tocada e nenhum produto novo é criado. Usa a função
    atualizar_proporcoes do Supabase (uma chamada por lote); sem ela, atualiza produto a produto.
    """
    # a base completa fica guardada no Storage: é ela que define PAI e similares na precificação,
    # inclusive dos produtos que ainda não existem na dim_produto.
    # Um envio SOMA à base: o produto enviado substitui a relação que já existia; o que não veio continua.
    import gzip as _gz
    novo = df[["id_produto", "id_pai", "proporcao"]].drop_duplicates("id_produto", keep="last")
    antes = _base_atual_completa()
    mantidos = antes[~antes["id_produto"].isin(novo["id_produto"])] if len(antes) else antes
    completo = pd.concat([mantidos, novo], ignore_index=True).drop_duplicates("id_produto", keep="last")
    db.sb().storage.from_("relatorios").upload(ARQUIVO, _gz.compress(completo.to_csv(index=False).encode(), 6),
                                               {"content-type": "application/gzip", "upsert": "true"})
    # no banco, só os produtos enviados mudam (a função só mexe em quem já existe na dim_produto)
    registros = [{"id_produto": int(a), "id_pai": int(b), "proporcao": float(c)}
                 for a, b, c in zip(novo["id_produto"], novo["id_pai"], novo["proporcao"])]
    salvas = 0
    try:
        from concurrent.futures import ThreadPoolExecutor
        lotes = [registros[i:i + 5000] for i in range(0, len(registros), 5000)]
        def lote(l):
            r = db.sb().rpc("atualizar_proporcoes", {"dados": l}).execute()
            return int(r.data or 0) if isinstance(r.data, (int, float)) else len(l)
        with ThreadPoolExecutor(max_workers=4) as ex:              # lotes grandes em paralelo
            for n, q in enumerate(ex.map(lote, lotes), 1):
                salvas += q
                if progresso:
                    progresso(n / len(lotes))
    except Exception:
        salvas = len(registros)
        # sem a função no banco: UPDATE produto a produto (mais lento, mesmo resultado)
        from concurrent.futures import ThreadPoolExecutor
        def um(r):
            db.sb().table("dim_produto").update({"id_pai": r["id_pai"], "proporcao": r["proporcao"]}).eq("id_produto", r["id_produto"]).execute()
        with ThreadPoolExecutor(max_workers=8) as ex:
            for n, _ in enumerate(ex.map(um, registros), 1):
                if progresso and n % 50 == 0:
                    progresso(n / len(registros))
    carregar.clear()
    return {"salvas": salvas, "fora_da_dim": max(0, len(novo) - salvas), "enviadas": int(len(novo)),
            "substituidas": int(len(antes) - len(mantidos)) if len(antes) else 0, "mantidas": int(len(mantidos)), "total": int(len(completo))}


def _base_atual_completa() -> pd.DataFrame:
    """Base PROP% que já está gravada (arquivo do Storage), somada às relações que existem na dim_produto e não estão no
    arquivo (assim, um arquivo que tenha ficado incompleto é recomposto pelo banco). Sem cache: lida na hora do envio."""
    import gzip as _gz
    import io as _io
    arq = pd.DataFrame(columns=["id_produto", "id_pai", "proporcao"])
    try:
        arq = pd.read_csv(_io.BytesIO(_gz.decompress(db.sb().storage.from_("relatorios").download(ARQUIVO))))[["id_produto", "id_pai", "proporcao"]]
    except Exception:
        pass
    linhas, pagina = [], 0
    try:
        while True:
            lote = (db.sb().table("dim_produto").select("id_produto, id_pai, proporcao").gt("proporcao", 0).order("id_produto")
                    .range(pagina * 1000, pagina * 1000 + 999).execute().data or [])
            linhas.extend(lote)
            if len(lote) < 1000:
                break
            pagina += 1
    except Exception:
        pass
    dim = pd.DataFrame(linhas, columns=["id_produto", "id_pai", "proporcao"]).dropna()
    base = pd.concat([dim[~dim["id_produto"].isin(arq["id_produto"])], arq], ignore_index=True) if len(dim) else arq
    if not len(base):
        return pd.DataFrame(columns=["id_produto", "id_pai", "proporcao"])
    base = base.dropna().astype({"id_produto": "int64", "id_pai": "int64", "proporcao": "float64"})
    return base[base["id_produto"] != base["id_pai"]].drop_duplicates("id_produto", keep="last")


ARQUIVO = "config/proporcoes.csv.gz"


@st.cache_data(ttl=600, show_spinner=False)
def carregar() -> pd.DataFrame:
    """Relações PAI x filho da base PROP%: do arquivo completo no Storage; sem ele, da dim_produto."""
    try:
        import gzip as _gz, io as _io
        df = pd.read_csv(_io.BytesIO(_gz.decompress(db.sb().storage.from_("relatorios").download(ARQUIVO))))
        if len(df):
            return df.astype({"id_produto": "int64", "id_pai": "int64", "proporcao": "float64"}).assign(nome="")
    except Exception:
        pass
    linhas, pagina = [], 0
    try:
        while True:
            resp = (db.sb().table("dim_produto").select("*").gt("proporcao", 0).order("id_produto")
                    .range(pagina * 1000, pagina * 1000 + 999).execute())
            lote = resp.data or []
            linhas.extend(lote)
            if len(lote) < 1000:
                break
            pagina += 1
    except Exception:
        return pd.DataFrame(columns=["id_produto", "id_pai", "proporcao"])
    bruto = pd.DataFrame(linhas)
    if bruto.empty:
        return pd.DataFrame(columns=["id_produto", "id_pai", "proporcao", "nome"])
    # descrição do produto filho, se a dim_produto tiver (descricao, produto, nome...)
    cand = [c for c in bruto.columns if c not in ("id_produto", "id_pai", "proporcao") and bruto[c].dtype == object
            and any(t in _norm(c) for t in ("descri", "produto", "nome"))]
    df = pd.DataFrame({"id_produto": bruto["id_produto"], "id_pai": bruto.get("id_pai"), "proporcao": bruto.get("proporcao"),
                       "nome": bruto[cand[0]].astype(str) if cand else ""}).dropna(subset=["id_produto", "id_pai", "proporcao"])
    return df.astype({"id_produto": "int64", "id_pai": "int64", "proporcao": "float64"})
