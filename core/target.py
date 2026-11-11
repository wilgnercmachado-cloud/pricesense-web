"""Preço target (preço flat do fornecedor) por filial e produto.

Regras combinadas com o usuário:
- arquivo com ID filial | ID Produto | Varejo; Pricing e Comercial sobem, o administrador sempre aprova antes de valer;
- vale 35 dias a partir da aprovação (importação); depois perde a vigência, a menos que chegue um novo envio;
- flag "pode seguir o mercado se for menor", marcada por hierarquia comprador → categoria → fornecedor
  (marcar um nível marca tudo abaixo; basta o item estar debaixo de um nível marcado);
- flag desmarcada: o motor recomenda programar o target (tipo de oferta 11 - comercial), atacado = varejo com a base de
  redução; quando o PDV já está no target com tipo PROMOCAO COMERCIAL (11) ou APP (10), fica sem recomendação até os 35 dias;
- flag marcada: o target vira o preço máximo de varejo para o motor e para o Optimus.
"""
from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata
import uuid

import numpy as np
import pandas as pd
import streamlit as st

from core import db

TABELA, FLAGS = "precos_target", "target_flags"
VIGENCIA_DIAS = 35
FUSO = dt.timezone(dt.timedelta(hours=-3))


class ErroTarget(ValueError):
    pass


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _num(v) -> float:
    t = str(v).strip().replace("R$", "").replace(" ", "")
    if not t or t.lower() == "nan":
        return float("nan")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return float("nan")


def ler_planilha(arquivo) -> pd.DataFrame:
    nome = str(getattr(arquivo, "name", arquivo)).lower()
    if nome.endswith((".csv", ".txt")):
        bruto = arquivo.getvalue() if hasattr(arquivo, "getvalue") else open(arquivo, "rb").read()
        try:
            texto = bruto.decode("utf-8")
        except UnicodeDecodeError:
            texto = bruto.decode("latin-1")
        sep = max((";", "|", ",", "\t"), key=texto.splitlines()[0].count)
        df = pd.read_csv(io.StringIO(texto), sep=sep, dtype=str)
    else:
        df = pd.read_excel(arquivo, sheet_name=0, dtype=str)
    mapa = {_norm(c): c for c in df.columns}
    alvo = {"filial": ("idfilial", "filial", "codfilial"), "produto": ("idproduto", "produto", "codproduto"),
            "varejo": ("varejo", "preco", "precovarejo", "precotarget", "target")}
    achadas = {}
    for k, nomes in alvo.items():
        for n in nomes:
            if n in mapa:
                achadas[k] = mapa[n]; break
    faltam = [r for r, k in (("ID filial", "filial"), ("ID Produto", "produto"), ("Varejo", "varejo")) if k not in achadas]
    if faltam:
        raise ErroTarget(f"Faltam as colunas {', '.join(faltam)}. O arquivo deve ter: ID filial | ID Produto | Varejo.")
    cod = lambda s: pd.to_numeric(s.astype(str).str.extract(r"(\d+)")[0], errors="coerce")
    out = pd.DataFrame({"filial": cod(df[achadas["filial"]]), "produto": cod(df[achadas["produto"]]), "varejo": df[achadas["varejo"]].map(_num)})
    out = out.dropna()
    out = out[out["varejo"] > 0].astype({"filial": "int64", "produto": "int64"}).drop_duplicates(["filial", "produto"], keep="last")
    if out.empty:
        raise ErroTarget("Nenhuma linha válida: confira os códigos de filial e produto e o preço de varejo.")
    return out


def salvar(df: pd.DataFrame, enviado_por: str, aprovado_por: str) -> dict:
    """Grava (substitui o target da mesma filial + produto). A vigência conta a partir de agora (aprovação)."""
    agora = dt.datetime.now(dt.timezone.utc)
    ate = (agora.astimezone(FUSO).date() + dt.timedelta(days=VIGENCIA_DIAS)).isoformat()
    lote = str(uuid.uuid4())[:8]
    regs = [{"filial": int(f), "produto": int(p), "varejo": round(float(v), 2), "importado_em": agora.isoformat(), "vigencia_ate": ate,
             "lote": lote, "enviado_por": enviado_por, "aprovado_por": aprovado_por}
            for f, p, v in zip(df["filial"], df["produto"], df["varejo"])]
    for k in range(0, len(regs), 2000):
        db.sb().table(TABELA).upsert(regs[k:k + 2000], on_conflict="filial,produto").execute()
    vigentes.clear()
    return {"linhas": len(regs), "ate": ate}


@st.cache_data(ttl=120, show_spinner=False)
def vigentes() -> pd.DataFrame:
    """Targets dentro da vigência (até a data, inclusive)."""
    hoje = dt.datetime.now(FUSO).date().isoformat()
    linhas, pagina = [], 0
    try:
        while True:
            r = (db.sb().table(TABELA).select("filial, produto, varejo, importado_em, vigencia_ate, lote")
                 .gte("vigencia_ate", hoje).order("filial").order("produto").range(pagina * 1000, pagina * 1000 + 999).execute())
            d = r.data or []
            linhas += d
            if len(d) < 1000:
                break
            pagina += 1
    except Exception:
        pass
    return pd.DataFrame(linhas, columns=["filial", "produto", "varejo", "importado_em", "vigencia_ate", "lote"])


def versao() -> str:
    v = vigentes()
    return f"{len(v)}:{v['importado_em'].max() if len(v) else ''}:{flags_versao()}"


# ---------------------------------------------------------------- flags (comprador → categoria → fornecedor)
@st.cache_data(ttl=60, show_spinner=False)
def flags() -> dict[tuple[str, str], bool]:
    try:
        d = db.sb().table(FLAGS).select("*").execute().data or []
    except Exception:
        d = []
    return {(r["nivel"], r["valor"]): bool(r.get("marcado")) for r in d}


def flags_versao() -> str:
    f = flags()
    return str(sorted(k for k, v in f.items() if v))


def marcar(nivel: str, valor: str, marcado: bool, usuario: str) -> None:
    db.sb().table(FLAGS).upsert({"nivel": nivel, "valor": valor, "marcado": bool(marcado), "atualizado_por": usuario,
                                 "atualizado_em": dt.datetime.now(dt.timezone.utc).isoformat()}, on_conflict="nivel,valor").execute()
    flags.clear()


@st.cache_data(ttl=3600, show_spinner=False)
def fornecedores(produtos: tuple[int, ...]) -> dict[int, str]:
    """Fornecedor de cada produto: dim_produto.id_fornecedor → dim_fornecedor.nome_grupo_empresarial."""
    out: dict[int, str] = {}
    if not produtos:
        return out
    dp = db.buscar_produtos(list(produtos))
    ids = sorted({int(x["id_fornecedor"]) for x in dp if str(x.get("id_fornecedor") or "").strip().lstrip("-").isdigit()})
    nomes = {int(x["id_fornecedor"]): str(x.get("nome_grupo_empresarial") or "") for x in db.buscar_fornecedores(ids)} if ids else {}
    for x in dp:
        try:
            fid = int(x.get("id_fornecedor"))
        except (TypeError, ValueError):
            continue
        out[int(x["id_produto"])] = f"{fid} - {nomes.get(fid) or 'sem nome'}"
    return out


def _cod(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s.astype(str).str.split(" - ").str[0].str.strip(), errors="coerce").fillna(-1).astype("int64").to_numpy()


def arvore(df: pd.DataFrame) -> pd.DataFrame:
    """Itens com target vigente na base (filial + produto), com comprador, categoria e fornecedor."""
    t = vigentes()
    if t.empty or df is None or not len(df):
        return pd.DataFrame(columns=["comprador", "categoria", "fornecedor", "produto", "filial"])
    chave = pd.MultiIndex.from_arrays([t["filial"].astype("int64"), t["produto"].astype("int64")])
    fc, pc = _cod(df["Filial"]), _cod(df["Produto"])
    m = pd.MultiIndex.from_arrays([fc, pc]).isin(chave)
    sub = df.loc[m]
    if sub.empty:
        return pd.DataFrame(columns=["comprador", "categoria", "fornecedor", "produto", "filial"])
    pcod = _cod(sub["Produto"])
    forn = fornecedores(tuple(sorted(set(int(x) for x in pcod))))
    reserva = sub["Grupo empresarial"].astype(str).to_numpy() if "Grupo empresarial" in sub else np.array(["(sem fornecedor)"] * len(sub))
    return pd.DataFrame({"comprador": sub["Comprador"].astype(str).to_numpy(), "categoria": sub["Categoria"].astype(str).to_numpy(),
                         "fornecedor": [forn.get(int(p)) or r for p, r in zip(pcod, reserva)],
                         "produto": sub["Produto"].astype(str).to_numpy(), "filial": sub["Filial"].astype(str).to_numpy()})


def por_linha(b: pd.DataFrame) -> dict:
    """Para cada linha da mesa: target (ou None), se pode seguir o mercado (flag) e a data fim da vigência."""
    n = len(b)
    vazio = {"tgt": [None] * n, "tgf": [0] * n, "tga": [None] * n}
    t = vigentes()
    if t.empty or not n:
        return vazio
    idx = pd.MultiIndex.from_arrays([t["filial"].astype("int64"), t["produto"].astype("int64")])
    s_v = pd.Series(t["varejo"].astype(float).to_numpy(), index=idx)
    s_a = pd.Series(t["vigencia_ate"].astype(str).to_numpy(), index=idx)
    s_v = s_v[~s_v.index.duplicated(keep="last")]; s_a = s_a[~s_a.index.duplicated(keep="last")]
    chave = pd.MultiIndex.from_arrays([_cod(b["Filial"]), _cod(b["Produto"])])
    v = s_v.reindex(chave).to_numpy(); ate = s_a.reindex(chave).to_numpy()
    tem = np.isfinite(v)
    if not tem.any():
        return vazio
    fl = {k: x for k, x in flags().items() if x}
    flag = np.zeros(n, dtype=int)
    if fl:
        comp = b["Comprador"].astype(str).to_numpy(); cat = b["Categoria"].astype(str).to_numpy()
        pc = _cod(b["Produto"])
        forn = fornecedores(tuple(sorted(set(int(x) for x in pc[tem]))))
        reserva = b["Grupo empresarial"].astype(str).to_numpy() if "Grupo empresarial" in b else None
        for i in np.where(tem)[0]:
            f_ = forn.get(int(pc[i])) or (reserva[i] if reserva is not None else "")
            if fl.get(("comprador", comp[i])) or fl.get(("categoria", f"{comp[i]}|{cat[i]}")) or fl.get(("fornecedor", f"{comp[i]}|{cat[i]}|{f_}")):
                flag[i] = 1
    fmt = lambda d: f"{d[8:10]}/{d[5:7]}" if isinstance(d, str) and len(d) >= 10 else None
    return {"tgt": [round(float(x), 2) if np.isfinite(x) else None for x in v], "tgf": flag.tolist(),
            "tga": [fmt(a) if ok else None for a, ok in zip(ate, tem)]}
