"""Leitura do relatório "Pricing GMAT3" (HTML publicado) para uma tabela de precificação.

O HTML guarda os dados em blocos <script id="dataN" type="application/json"> com
base64 + gzip. Cada bloco descompactado é: 4 bytes (tamanho do cabeçalho, little-endian),
o cabeçalho em JSON (dicionários e "layout" das colunas) e as colunas em binário.
A senha do HTML é só uma tela no navegador: os dados não são criptografados.
"""
from __future__ import annotations

import base64
import gzip
import json
import re
import struct

import numpy as np
import pandas as pd

_DTYPE = {"u1": "<u1", "u2": "<u2", "i1": "<i1", "i4": "<i4", "f4": "<f4"}
_CENTAVOS = ["cu", "vm", "am", "mk", "amk", "mk2", "mo", "ma"]
_DICIONARIOS = {"F": "Filial", "C": "Classificação", "B": "Comprador", "D": "Departamento", "S": "Seção",
                "G": "Categoria", "P": "Produto", "T": "Tipo de preço", "R": "Motivo", "GE": "Grupo empresarial",
                "SE": "Setor", "X": "Cesta"}
_BLOQUEIO = re.compile(r"VENCIMENTO|ENCARTE|MIDIA")


class ErroLeitura(ValueError):
    pass


def _bloco(html: bytes, nome: str) -> tuple[dict, bytes]:
    m = re.search(rb'<script id="' + nome.encode() + rb'" type="application/json">\s*([^<]+?)\s*</script>', html)
    if m and m.group(1).startswith(b"URL:"):
        raise ErroLeitura("Este HTML é a versão leve, que busca a base num link externo. Publique o HTML completo "
                          "(botão \"Baixar HTML completo\" dentro do relatório).")
    if not m:
        raise ErroLeitura(f"O arquivo não tem o bloco de dados '{nome}'. Confira se é o relatório Pricing GMAT3.")
    bruto = gzip.decompress(base64.b64decode(m.group(1)))
    tam = struct.unpack("<I", bruto[:4])[0]
    base = 4 + tam + (4 - tam % 4) % 4  # as colunas começam alinhadas em 4 bytes
    return json.loads(bruto[4:4 + tam]), bruto[base:]


def _colunas(cab: dict, corpo: bytes, n: int) -> dict[str, np.ndarray]:
    out = {}
    for nome, tipo, inicio, qtd in cab["layout"]:
        if qtd == n and tipo in _DTYPE:
            out[nome] = np.frombuffer(corpo, dtype=_DTYPE[tipo], count=qtd, offset=inicio)
    return out


def _data_fim(col: dict, dic: dict, n: int) -> np.ndarray:
    """Aceita os formatos que a DTFIM pode ter no HTML: dias desde 2020, série do Excel ou índice de um dicionário de datas."""
    bruto = None
    for nome in ("df", "DF", "dtfim", "DTFIM", "dfim"):
        if nome in col:
            bruto = col[nome].astype(np.int64)
            chave = nome
            break
    if bruto is None:
        return np.zeros(n, np.int32)
    lista = dic.get(chave) or dic.get(chave.lower())
    if lista:                                            # índice para datas em texto (dd/mm/aaaa)
        dias = []
        for t in lista:
            try:
                d = pd.to_datetime(str(t), dayfirst=True, errors="coerce")
                dias.append(0 if pd.isna(d) else int((d - pd.Timestamp("2020-01-01")).days) + 1)
            except Exception:
                dias.append(0)
        dias = np.asarray(dias + [0], dtype=np.int64)
        return dias[np.clip(bruto, 0, len(dias) - 1)].astype(np.int32)
    out = bruto.copy()
    serie = out > 30000                                  # série do Excel (dias desde 30/12/1899)
    out[serie] = out[serie] - 43830
    out[(out < 0) | (out == 65535)] = 0
    return out.astype(np.int32)


def _estoque(html: bytes, n: int) -> dict:
    """Bloco data7 (alinhado às linhas da base): estoque R$, DDE, idade, meta de cobertura, baixo giro."""
    try:
        cab, corpo = _bloco(html, "data7")
    except Exception:
        return {}
    col = {nome: np.frombuffer(corpo, dtype=_DTYPE[t], count=q, offset=o) for nome, t, o, q in cab["layout"] if t in _DTYPE and q == n}
    conv_i4 = lambda a: np.where(a < 0, np.nan, a).astype(np.float32)
    conv_u2 = lambda a: np.where(a == 65535, np.nan, a).astype(np.float32)
    out = {}
    if "eVE" in col: out["estoque"] = conv_i4(col["eVE"].astype(np.int64))
    if "eDD" in col: out["dde"] = conv_u2(col["eDD"])
    if "eDE" in col: out["idade"] = conv_u2(col["eDE"])
    if "eMC" in col: out["meta_cobertura"] = conv_u2(col["eMC"])
    if "eEX" in col: out["baixo_giro"] = conv_i4(col["eEX"].astype(np.int64))
    return out


def _array_js(js: str, inicio_padrao: str) -> bytes | None:
    """Arrays auxiliares embutidos no JavaScript do relatório (base de redução e tipo de preço do PDV)."""
    i = js.find(inicio_padrao)
    if i < 0:
        return None
    m = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", js[i:i + 4_000_000])
    if not m:
        return None
    dados = base64.b64decode(m.group(1))
    return gzip.decompress(dados) if dados[:2] == b"\x1f\x8b" else dados


def ler_relatorio(html: bytes) -> tuple[pd.DataFrame, dict]:
    """Retorna (tabela filial x produto, metadados)."""
    cab, corpo = _bloco(html, "data")
    n, dic = int(cab["n"]), cab["dic"]
    col = _colunas(cab, corpo, n)

    df = pd.DataFrame({rotulo: pd.Categorical.from_codes(col[k].astype(np.int32), categories=pd.Index(dic[k]).astype(str)
                                                         if len(set(dic[k])) == len(dic[k]) else pd.Index(range(len(dic[k]))))
                       for k, rotulo in _DICIONARIOS.items() if k in col and k in dic})
    for k in _CENTAVOS:
        if k in col:
            df[k] = (col[k].astype(np.float64) / 100).astype(np.float32)
    df["_p"] = col["P"].astype(np.int32)       # códigos originais, para cruzar com o histórico
    df["_f"] = col["F"].astype(np.int16)
    df["venda"] = col["ve"].astype(np.float32) if "ve" in col else np.float32(0)
    df["qtd"] = (col["qt"].astype(np.float32) / 100) if "qt" in col else np.float32(0)
    df["erro_pesquisa"] = col["E"].astype(bool) if "E" in col else False
    df["pesquisado"] = col["Q"].astype(bool) if "Q" in col else True
    df["freq_moda"] = col["fq"] if "fq" in col else 0
    # data fim do preço vigente no PDV (DTFIM da 1082): dias desde 01/01/2020 (1 = 01/01/2020; 0 = sem data fim)
    df["data_fim"] = _data_fim(col, dic, n)
    if "K" in col:
        k_ = np.asarray(dic["K"], dtype=object)
        df["Concorrente menor"] = pd.Categorical(k_[np.minimum(col["K"], len(k_) - 1)])
    if "K2" in col:
        df["Concorrente secundário"] = pd.Categorical(np.asarray(dic["K"], dtype=object)[np.minimum(col["K2"], len(dic["K"]) - 1)])
    if "dt" in col and "dt" in dic:
        df["Data pesquisa"] = pd.Categorical(np.asarray(dic["dt"], dtype=object)[col["dt"]])

    # Hierarquia da filial (estado, diretores, cidade, bandeira)
    fm = cab.get("fm", {})
    codigos_f = col["F"]
    for chave, rotulo in [("UF", "Estado"), ("DR", "Diretor executivo"), ("RG", "Diretor regional"),
                          ("SR", "Supervisor regional"), ("CID", "Cidade"), ("BD", "Bandeira")]:
        if chave in fm:
            df[rotulo] = pd.Categorical(np.asarray(fm[chave], dtype=object)[codigos_f])

    js = html[html.rfind(b"<script>"):].decode("utf-8", errors="ignore")
    # Base de redução do atacado por produto (% sobre o varejo; 255 = sem base)
    bred = _array_js(js, "const BRED=")
    if bred is not None and len(bred) >= len(dic["P"]):
        b = np.frombuffer(bred, dtype=np.uint8)[col["P"]]
        df["base_red_atacado"] = np.where(b == 255, np.nan, b / 2).astype(np.float32)
    # Tipo de preço vigente no PDV (para bloquear itens em encarte, mídia ou vencimento)
    ogn_m = re.search(r"const OGN=(\[[^\]]*\])", js)
    j = js.find("r.OG=OGR")
    og = _array_js(js[max(0, j - 3_000_000):j], "atob(") if j > 0 else None
    if ogn_m and og is not None and len(og) >= n:
        ogn = json.loads(ogn_m.group(1))
        idx = np.frombuffer(og, dtype=np.uint8)[:n]
        nomes = np.asarray(ogn + [""] * (256 - len(ogn)), dtype=object)
        df["Tipo de preço PDV"] = pd.Categorical(np.where(idx == 255, "", nomes[np.minimum(idx, 255)]))
    else:
        df["Tipo de preço PDV"] = ""

    for k, v in _estoque(html, n).items():
        df[k] = v

    motivo_bloq = df["Motivo"].astype(str).str.contains(_BLOQUEIO) if "Motivo" in df else False
    pdv_bloq = df["Tipo de preço PDV"].astype(str).str.contains(_BLOQUEIO)
    df["em_acao"] = (motivo_bloq | pdv_bloq).to_numpy()

    meta = {"atualizado": cab.get("upd"), "periodo": cab.get("hist"), "linhas": n,
            "filiais": len(dic.get("F", [])), "produtos": len(dic.get("P", [])), "hist": _historico(html, dic.get("hU")),
            "com_data_fim": int((df["data_fim"] > 0).sum())}
    return df, meta


def _historico(html: bytes, ufs: list | None = None) -> dict | None:
    """Histórico de preços (25 dias), como no gráfico "Histórico de preço do mercado" do relatório.

    data5: coletas por produto x estado x concorrente x dia (dV/dA) e o nosso preço por produto x estado x dia (oV/oA).
    data4: coletas por produto x filial x concorrente; usado para saber quais concorrentes são da filial.
    """
    try:
        c4, b4 = _bloco(html, "data4")
        c5, b5 = _bloco(html, "data5")
    except Exception:
        return None
    a4 = {n: np.frombuffer(b4, dtype=_DTYPE[t], count=q, offset=o) for n, t, o, q in c4["layout"] if t in _DTYPE}
    a5 = {n: np.frombuffer(b5, dtype=_DTYPE[t], count=q, offset=o) for n, t, o, q in c5["layout"] if t in _DTYPE}
    if not {"dP", "dU", "dK", "dT", "dV"}.issubset(a5) or not {"mF", "mK"}.issubset(a4):
        return None
    pares = np.unique(a4["mF"].astype(np.int64) * 100000 + a4["mK"].astype(np.int64))
    return {
        "dP": a5["dP"].astype(np.int32), "dU": a5["dU"].astype(np.int16), "dK": a5["dK"].astype(np.int32),
        "dT": a5["dT"].astype(np.int16), "dV": a5["dV"].astype(np.int32), "dA": a5.get("dA", a5["dV"]).astype(np.int32),
        "dTp": a5["dTp"].astype(np.int16) if "dTp" in a5 else np.zeros(len(a5["dP"]), np.int16),
        "oO": a5["oO"].astype(np.int16) if "oO" in a5 else np.zeros(len(a5.get("oP", [])), np.int16), "OG": c4.get("OG", []),
        "oP": a5["oP"].astype(np.int32) if "oP" in a5 else np.zeros(0, np.int32),
        "oU": a5["oU"].astype(np.int16) if "oU" in a5 else np.zeros(0, np.int16),
        "oT": a5["oT"].astype(np.int16) if "oT" in a5 else np.zeros(0, np.int16),
        "oV": a5["oV"].astype(np.int32) if "oV" in a5 else np.zeros(0, np.int32),
        "oA": a5["oA"].astype(np.int32) if "oA" in a5 else np.zeros(0, np.int32),
        "fil_conc_f": (pares // 100000).astype(np.int32), "fil_conc_k": (pares % 100000).astype(np.int32),
        "K": c4.get("K", []), "KE": c4.get("KE", []), "T": c4.get("T", []), "U": list(ufs or []),
    }


def ler_de_gzip_ou_html(conteudo: bytes) -> tuple[pd.DataFrame, dict]:
    if conteudo[:2] == b"\x1f\x8b":
        conteudo = gzip.decompress(conteudo)
    return ler_relatorio(conteudo)
