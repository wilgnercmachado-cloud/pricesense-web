"""Pesquisa 1067: a coleta mais recente (D0) somada à base do HTML (que chega em D+1).

Só a pesquisa entra: filial, produto, concorrente, data, tipo e preços do concorrente. O arquivo fica no Supabase
e vale para todos os usuários enquanto o HTML for o mesmo; com HTML novo, é descartado.
"""
from __future__ import annotations

import datetime as dt
import gzip
import io
import json
import re
import unicodedata
import zipfile

import numpy as np
import pandas as pd
import streamlit as st

from core import db

PASTA = "pesquisa1067"          # um arquivo por usuário; a base usa a soma de todos os enviados para o mesmo HTML
BUCKET = "relatorios"
OBRIGATORIAS = {"filial": "FILIAL", "produto": "PRODUTO", "pesquisadata": "PESQUISADATA", "tipo": "Tipo", "customedio": "CustoMedio",
                "vlrvarejopdv": "Vlr. Varejo PDV", "vlratacadopdv": "Vlr. Atacado PDV", "vlrvareconc": "Vlr.Vare.Conc",
                "vlratacconc": "Vlr.Atac.Conc.", "filialconcorrente": "FILIALCONCORRENTE"}
USADAS = ("filial", "produto", "pesquisadata", "tipo", "vlrvareconc", "vlratacconc", "filialconcorrente")
# código do tipo na 1067 -> tipo da base (0 regular, 1 promoção, 2 encarte, 3 mídia, 4 ponto extra, 5 validade, 6 outros)
TIPO_1067 = {"1": 0, "5": 1, "2": 2, "4": 3, "6": 4, "3": 5}


class Erro1067(ValueError):
    pass


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _codigo(v) -> int | None:
    m = re.match(r"\s*(\d+)", str(v))
    return int(m.group(1)) if m else None


def _tipo(v) -> int:
    t = str(v).strip()
    m = re.match(r"\s*(\d+)", t)
    if m:
        return TIPO_1067.get(m.group(1), 6)
    n = _norm(t)
    for chave, cod in (("regular", 0), ("promoc", 1), ("encarte", 2), ("midia", 3), ("pontoextra", 4), ("validade", 5), ("vencimento", 5)):
        if chave in n:
            return cod
    return 6


def _dia(v) -> int:
    t = str(v).strip()[:10]
    for f in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(t, f).date().toordinal()
        except ValueError:
            pass
    try:
        return (dt.date(1899, 12, 30) + dt.timedelta(days=int(float(t)))).toordinal()    # data serial do Excel
    except Exception:
        return 0


def _cent(v) -> int:
    t = str(v).strip()
    if not t or t.lower() == "nan":
        return 0
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return int(round(float(t) * 100))
    except ValueError:
        return 0


def _conferir(cabecalho: list[str], nome: str) -> dict:
    mapa = {_norm(c): i for i, c in enumerate(cabecalho)}
    faltam = [orig for k, orig in OBRIGATORIAS.items() if k not in mapa]
    if faltam:
        raise Erro1067(f"{nome}: faltam as colunas obrigatórias {', '.join(faltam)}. O arquivo não foi carregado.")
    return {k: mapa[k] for k in USADAS}


def _ler_texto(bruto: bytes, nome: str, saida: dict) -> int:
    """CSV lido em fluxo (arquivos grandes), juntando linhas quebradas no meio de um campo."""
    try:
        texto = bruto.decode("utf-8")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    linhas = iter(texto.splitlines())
    cab = next(linhas, "")
    sep = max(("|", ";", ",", "\t"), key=cab.count)
    cols = cab.split(sep)
    ix = _conferir(cols, nome)
    n_sep, n = len(cols) - 1, 0
    buf = ""
    for linha in linhas:
        buf = (buf + " " + linha) if buf else linha
        if buf.count(sep) < n_sep:
            continue                                   # campo com quebra de linha: junta com a próxima
        c = buf.split(sep); buf = ""
        _guardar(saida, c[ix["filial"]], c[ix["produto"]], c[ix["filialconcorrente"]], c[ix["pesquisadata"]], c[ix["tipo"]],
                 c[ix["vlrvareconc"]], c[ix["vlratacconc"]])
        n += 1
    return n


def _ler_planilha(bruto: bytes, nome: str, saida: dict) -> int:
    df = None
    for motor in ("calamine", "openpyxl"):
        try:
            cab = pd.read_excel(io.BytesIO(bruto), nrows=0, engine=motor)
            ix = _conferir(list(cab.columns), nome)
            usar = [cab.columns[ix[k]] for k in USADAS]
            df = pd.read_excel(io.BytesIO(bruto), usecols=usar, dtype=str, engine=motor)
            break
        except ImportError:
            continue
    if df is None:
        raise Erro1067(f"{nome}: não foi possível ler a planilha.")
    m = {_norm(c): c for c in df.columns}
    for r in zip(*(df[m[k]] for k in ("filial", "produto", "filialconcorrente", "pesquisadata", "tipo", "vlrvareconc", "vlratacconc"))):
        _guardar(saida, *r)
    return len(df)


def _guardar(s: dict, fil, prod, conc, data, tipo, vv, va) -> None:
    f, p, k = _codigo(fil), _codigo(prod), _codigo(conc)
    if f is None or p is None or k is None:
        return
    s["f"].append(f); s["p"].append(p); s["k"].append(k); s["dia"].append(_dia(data)); s["t"].append(_tipo(tipo))
    s["v"].append(_cent(vv)); s["a"].append(_cent(va))
    if k not in s["nomes"]:
        s["nomes"][k] = re.sub(r"\s+", " ", str(conc)).strip()


def ler(arquivos) -> dict:
    """Lê CSV, XLSX ou ZIP (com CSV/XLSX dentro). Recusa o arquivo se faltar coluna obrigatória."""
    saida = {"f": [], "p": [], "k": [], "dia": [], "t": [], "v": [], "a": [], "nomes": {}}
    lidos = []
    for arq in arquivos:
        bruto = arq.getvalue() if hasattr(arq, "getvalue") else open(arq, "rb").read()
        nome = getattr(arq, "name", str(arq))
        itens = []
        if nome.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(bruto)) as z:
                itens = [(n, z.read(n)) for n in z.namelist() if n.lower().endswith((".csv", ".txt", ".xlsx", ".xls"))]
            if not itens:
                raise Erro1067(f"{nome}: o ZIP não tem CSV nem XLSX.")
        else:
            itens = [(nome, bruto)]
        for n, b in itens:
            q = _ler_planilha(b, n, saida) if n.lower().endswith((".xlsx", ".xls")) else _ler_texto(b, n, saida)
            lidos.append(n.split("/")[-1])
    if not saida["f"]:
        raise Erro1067("Nenhuma coleta válida encontrada no arquivo.")
    tab = pd.DataFrame({k: saida[k] for k in ("f", "p", "k", "dia", "t", "v", "a")})
    tab = tab[(tab["dia"] > 0) & (tab["v"] > 0)]
    dias = sorted(set(tab["dia"]))
    return {"tab": tab, "nomes": saida["nomes"], "arquivos": lidos,
            "dias": [dt.date.fromordinal(int(x)).strftime("%d/%m/%Y") for x in dias]}


def _caminho(usuario: str) -> str:
    return f"{PASTA}/{re.sub(r'[^a-z0-9_.-]', '_', (usuario or 'anon').lower())}.json.gz"


def salvar(lido: dict, base: str, usuario: str) -> dict:
    t = lido["tab"]
    meta = {"base": base, "usuario": usuario, "em": dt.datetime.now(dt.timezone.utc).isoformat(), "linhas": int(len(t)),
            "dias": lido["dias"], "arquivos": lido["arquivos"], "concorrentes": int(t["k"].nunique()), "filiais": int(t["f"].nunique())}
    pacote = {"meta": meta, "nomes": {str(k): v for k, v in lido["nomes"].items()}, **{c: t[c].astype(int).tolist() for c in t.columns}}
    db.sb().storage.from_(BUCKET).upload(_caminho(usuario), gzip.compress(json.dumps(pacote, separators=(",", ":")).encode(), 6),
                                         {"content-type": "application/gzip", "upsert": "true", "cache-control": "60"})
    carregar.clear()
    return meta


def remover(usuario: str) -> None:
    try:
        db.sb().storage.from_(BUCKET).remove([_caminho(usuario)])
    finally:
        carregar.clear()


@st.cache_data(ttl=120, show_spinner=False)
def carregar(base: str) -> dict | None:
    """Soma as 1067 de todos os usuários enviadas para este HTML. Na mesma filial + produto + concorrente + data,
    vale o envio mais recente. Envios feitos para um HTML anterior são ignorados."""
    try:
        nomes = [x["name"] for x in (db.sb().storage.from_(BUCKET).list(PASTA) or []) if str(x.get("name", "")).endswith(".json.gz")]
    except Exception:
        return None
    pacotes = []
    for n in nomes:
        try:
            pc = json.loads(gzip.decompress(db.sb().storage.from_(BUCKET).download(f"{PASTA}/{n}")))
            if pc.get("meta", {}).get("base") == base:
                pacotes.append(pc)
        except Exception:
            continue
    if not pacotes:
        return None
    pacotes.sort(key=lambda pc: pc["meta"]["em"])
    tab = pd.concat([pd.DataFrame({c: pc[c] for c in ("f", "p", "k", "dia", "t", "v", "a")}).assign(_o=n) for n, pc in enumerate(pacotes)], ignore_index=True)
    ult = tab.groupby(["f", "p", "k", "dia"])["_o"].transform("max")
    tab = tab[tab["_o"] == ult].drop(columns="_o")                                   # envio mais recente vence no confronto
    nomes_k = {}
    for pc in pacotes:
        nomes_k.update(pc.get("nomes", {}))
    envios = [pc["meta"] for pc in pacotes]
    dias = sorted({d for m in envios for d in m["dias"]}, key=lambda d: dt.datetime.strptime(d, "%d/%m/%Y"))
    meta = {"base": base, "em": max(m["em"] for m in envios), "envios": envios, "dias": dias, "linhas": int(len(tab)),
            "filiais": int(tab["f"].nunique()), "concorrentes": int(tab["k"].nunique())}
    return {"meta": meta, "nomes": nomes_k, **{c: tab[c].astype(int).tolist() for c in tab.columns}}


def para_indices(pacote: dict, df: pd.DataFrame, nomes_k: list[str]) -> dict:
    """Converte códigos da 1067 nos índices da base (produto, filial, concorrente). Concorrente novo ganha índice próprio."""
    cod = lambda cats: {_codigo(c): i for i, c in enumerate(cats) if _codigo(c) is not None}
    mp, mf = cod(df["Produto"].cat.categories), cod(df["Filial"].cat.categories)
    mk = {}
    for i, nome in enumerate(nomes_k):
        c = _codigo(nome)
        if c is not None and c not in mk:
            mk[c] = i
    novos = []
    for c in sorted(set(pacote["k"])):
        if c not in mk:
            mk[c] = len(nomes_k) + len(novos)
            novos.append(pacote["nomes"].get(str(c), str(c)))
    p = np.array([mp.get(x, -1) for x in pacote["p"]]); f = np.array([mf.get(x, -1) for x in pacote["f"]])
    ok = (p >= 0) & (f >= 0)
    k = np.array([mk[x] for x in pacote["k"]])
    arr = lambda c: np.asarray(pacote[c])[ok]
    return {"p": p[ok].astype(np.int32), "f": f[ok].astype(np.int32), "k": k[ok].astype(np.int32), "t": arr("t").astype(np.int16),
            "dia": arr("dia").astype(np.int64), "v": arr("v").astype(np.int64), "a": arr("a").astype(np.int64), "K_novos": novos,
            "fora_da_base": int((~ok).sum())}
