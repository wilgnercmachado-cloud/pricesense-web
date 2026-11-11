"""Revisão de margem: categoria → produto, por estados, filiais, comprador, categoria e fornecedor, com sugestões e simulação de lucro.

Regras combinadas com o usuário:
- margem do último mês (só loja) = lucro ÷ venda do mês anterior, mesmos dias (bloco "ritmo do mês" do HTML de competitividade);
  lucro realizado do mês anterior = o lucro desse mesmo bloco;
- meta de margem = meta de lucro ÷ meta de venda (do produto; sem meta do produto, a da categoria);
- margem de mercado = (moda − custo médio) ÷ moda, ponderada pelo volume, só com pesquisa consistente (moda de 3 dias ou mais,
  sem erro de pesquisa); produto com pesquisa inconsistente em mais da metade do volume usa a média de mercado da categoria;
- objetiva sugerida: produto COM pesquisa parte da margem de mercado do próprio produto; SEM pesquisa parte da média de mercado
  da categoria; nos dois casos é puxada para a meta, sem passar de 3 pontos de distância do mercado;
- máxima sugerida = objetiva + 5 pontos; mínima sugerida = 0; tudo editável;
- simulação do lucro com o volume dos últimos 30 dias (base do HTML), item a item (filial + produto):
  com pesquisa (cesta e não cesta) segue o motor da PriceMetrics: preço vencedor − 0,01 (ou a moda, se a pesquisa estiver fora do
  delta), arredondado pela régua, dentro da mínima e da máxima (cesta: piso da cesta −15% e a máxima; não cesta: a nova mínima e
  a nova máxima); sem pesquisa: preço objetivo (custo ÷ (1 − objetiva)) arredondado pela régua;
- ganho de lucro = lucro simulado − lucro realizado no mês anterior;
- diagnóstico pelo IP simulado (preço ÷ moda, ponderado pelo volume): 98,9 a 100,9 dentro da faixa; acima de 100,9 zona crítica;
  abaixo de 98,9 zona de atenção; com pesquisa inconsistente, avisa que falta consistência.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

DISTANCIA_MAX = 5.0          # pontos entre a objetiva e a máxima sugeridas
DISTANCIA_MERCADO = 3.0      # a objetiva sugerida fica no máximo 3 pontos acima ou abaixo da margem de mercado
PISO_CESTA = -15.0           # mínima da cesta (piso padrão da PriceMetrics)
DELTA_ACIMA, DELTA_ABAIXO = 0.25, 0.15     # delta seguro padrão (pesquisa x moda) do motor
FAIXA = (0.989, 1.009)
CENT = 0.01


def diagnostico(ip: float, consistente: float) -> str:
    if consistente < 0.5:
        return "Falta consistência na pesquisa"
    if not np.isfinite(ip) or ip <= 0:
        return "Sem pesquisa"
    if ip > FAIXA[1]:
        return "Zona crítica (acima do mercado)"
    if ip < FAIXA[0]:
        return "Zona de atenção (abaixo do mercado)"
    return "Dentro da faixa"


def _cod(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.split(" - ").str[0].str.strip(), errors="coerce")


# ---------------------------------------------------------------- régua de arredondamento (a mesma da PriceMetrics, final 8)
_REGRA = {"A": [5, 8, 9], "B": [5, 8, 9], "C": [0, 5, 8, 9], "D": [9]}


def _faixa(c: int) -> str:
    return "A" if c <= 1099 else "B" if c <= 1999 else "C" if c <= 4000 else "D"


def _vc() -> dict[str, list[int]]:
    vc = {}
    for f in "ABCD":
        l = []
        for c in range(100):
            p, u = c // 10, c % 10
            if f == "A":
                ok = u in _REGRA["A"]
            elif f == "B":
                ok = 1 <= p <= 9 and u in _REGRA["B"]
            elif f == "C":
                ok = (3 <= p <= 9 and p in (5, 9)) if u == 0 else (3 <= p <= 9 and u in _REGRA["C"])
            else:
                ok = (3 <= p <= 9 and p in (5, 9)) if u == 0 else (3 <= p <= 9 and u == 9)
            if ok:
                l.append(c)
        vc[f] = l
    return vc


_VC = _vc()


@lru_cache(maxsize=200_000)
def _cands(pc: int) -> tuple[int, ...]:
    f, b = _faixa(pc), pc // 100
    return tuple(bb * 100 + c for bb in (b - 1, b, b + 1) for c in _VC[f])


@lru_cache(maxsize=400_000)
def _round_varejo_c(pc: int) -> int:
    if pc <= 0:
        return 0
    l = _cands(pc)
    if not l or pc in l:
        return pc
    melhor, dist = l[0], float("inf")
    for k in l:                                   # primeiro menor em caso de empate, como na PriceMetrics
        d = abs(k - pc)
        if d < dist:
            dist, melhor = d, k
    return melhor


def round_varejo(p: float) -> float:
    return _round_varejo_c(int(round(p * 100))) / 100 if p > 0 else 0.0


@lru_cache(maxsize=400_000)
def _arred_mercado_c(a: int, r: int, m: int) -> int:
    ok = lambda c: c in _cands(c)
    if ok(a):
        v = a
    elif ok(r):
        v = r
    else:
        l = [x for x in _cands(a) if x <= a]
        v = max(l) if l else _round_varejo_c(a)
    if m and v < m:
        l = [x for x in _cands(m) if x >= m]
        v = min(l) if l else _round_varejo_c(m)
    return v


def arred_mercado(alvo: float, ref: float, mn: float) -> float:
    return _arred_mercado_c(int(round(alvo * 100)), int(round(ref * 100)), int(round(mn * 100)) if mn else 0) / 100


# ---------------------------------------------------------------- itens (filial + produto) para a simulação
def itens(df: pd.DataFrame, regras: pd.DataFrame | None) -> pd.DataFrame:
    """Uma linha por filial + produto do recorte, com o que a simulação precisa."""
    from core import profimetrics as pf
    q = df["qtd"].astype(float).clip(lower=0).to_numpy()
    cu, vm, mo = (df[c].astype(float).to_numpy() for c in ("cu", "vm", "mo"))
    mk = df["mk"].astype(float).to_numpy() if "mk" in df else np.zeros(len(df))
    pes = mk > 0
    # referência do motor: o vencedor; fora do delta seguro em relação à moda, a moda
    lim = np.where(mk - CENT < cu, DELTA_ABAIXO, DELTA_ACIMA)
    fora = pes & (mo > 0) & (np.abs(np.where(mo > 0, mk / np.where(mo > 0, mo, 1) - 1, 0)) > lim + 1e-9)
    ref = np.where(fora, mo, mk)
    consist = (df["moda_dias"].astype(float).to_numpy() >= 3) if "moda_dias" in df else (mo > 0)
    consist = consist & ~df.get("erro_pesquisa", pd.Series(False, index=df.index)).astype(bool).to_numpy()
    r = pf.regras_por_item(_cod(df["Filial"]), _cod(df["Produto"]), regras) if regras is not None and len(regras) else None
    out = pd.DataFrame({
        "produto": df["Produto"].astype(str).to_numpy(), "categoria": df["Categoria"].astype(str).to_numpy(),
        "departamento": df["Departamento"].astype(str).to_numpy(),
        "cesta": (df["Cesta"].astype(str).str.upper() == "CESTA").to_numpy() if "Cesta" in df else np.zeros(len(df), bool),
        "q": q, "cu": cu, "vm": vm, "mo": np.where(mo > 0, mo, 0.0), "ref": np.where(pes, ref, 0.0), "pes": pes, "cons": consist,
        "venda": df["venda"].astype(float).to_numpy(),
        "lucro_ant": df.get("lucro_ant", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "venda_ant": df.get("venda_ant", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "meta_lucro": df.get("meta_lucro", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "meta_venda": df.get("meta_venda", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
    })
    for c in ("mrg_obj", "mrg_min", "mrg_max"):
        out[c] = r[c].to_numpy(dtype=float) if r is not None else np.nan
    return out


def precos_simulados(it: pd.DataFrame, obj: np.ndarray, mn_pct: np.ndarray, mx_pct: np.ndarray) -> np.ndarray:
    """Preço novo de cada item com a objetiva, a mínima e a máxima (em %) do seu produto, pelo motor da PriceMetrics."""
    cu, ref, pes, ces = it["cu"].to_numpy(), it["ref"].to_numpy(), it["pes"].to_numpy(), it["cesta"].to_numpy()
    out = np.zeros(len(it))
    for k in range(len(it)):
        c = cu[k]
        if not c > 0:
            continue
        mx = c / (1 - mx_pct[k] / 100) if np.isfinite(mx_pct[k]) and mx_pct[k] < 100 else np.inf
        if pes[k]:
            umin = PISO_CESTA if ces[k] else (mn_pct[k] if np.isfinite(mn_pct[k]) else 0.0)
            mn = c / (1 - umin / 100)
            alvo = ref[k] - CENT
            if alvo > mx:
                out[k] = round_varejo(max(mx, mn))
            else:
                pf = max(alvo, mn)
                out[k] = arred_mercado(pf, ref[k], mn) if pf == alvo else round_varejo(pf)
        else:
            o = obj[k] if np.isfinite(obj[k]) and obj[k] < 100 else np.nan
            out[k] = round_varejo(c / (1 - o / 100)) if np.isfinite(o) else it["vm"].iat[k]
    return out


def _resumo(it: pd.DataFrame, p: np.ndarray) -> dict:
    q = it["q"].to_numpy()
    luc = float((q * (p - it["cu"].to_numpy())).sum()); rec = float((q * p).sum())
    m = it["mo"].to_numpy() > 0
    return {"luc": round(luc, 2), "rec": round(rec, 2), "pm": round(float((q * p)[m].sum()), 2), "mq": round(float((q * it["mo"].to_numpy())[m].sum()), 2)}


def montar(df: pd.DataFrame, regras: pd.DataFrame | None) -> dict:
    """Pacote para a tela: categorias com os produtos, as sugestões iniciais (em %) e a simulação de lucro com elas."""
    it = itens(df, regras)
    if it.empty:
        return {"categorias": [], "faixa": list(FAIXA), "distancia_max": DISTANCIA_MAX, "piso_cesta": PISO_CESTA}
    q = it["q"].to_numpy()
    # margem de mercado da categoria (itens com moda) e meta da categoria
    conf = (it["mo"].to_numpy() > 0) & it["cons"].to_numpy()          # margem de mercado só com pesquisa consistente
    w_mo = np.where(conf, it["mo"] * q, 0.0); w_cu = np.where(conf, it["cu"] * q, 0.0)
    g = pd.DataFrame({"categoria": it["categoria"], "mo": w_mo, "cu": w_cu, "ml": it["meta_lucro"], "mv": it["meta_venda"]}).groupby("categoria").sum()
    merc_cat = ((g["mo"] - g["cu"]) / g["mo"].replace(0, np.nan)).to_dict()
    meta_cat = (g["ml"] / g["mv"].where(g["mv"] > 0)).to_dict()
    # por produto
    it["w_mo"], it["w_cu"] = w_mo, w_cu
    for c in ("mrg_obj", "mrg_min", "mrg_max"):
        it[c + "_q"] = np.where(np.isfinite(it[c]), it[c] * q, 0.0); it[c + "_w"] = np.where(np.isfinite(it[c]), q, 0.0)
    it["cons_q"] = np.where(it["cons"], q, 0.0)
    gp = it.groupby("produto", sort=False)
    soma = gp[["q", "venda", "lucro_ant", "venda_ant", "meta_lucro", "meta_venda", "w_mo", "w_cu", "cons_q",
               "mrg_obj_q", "mrg_obj_w", "mrg_min_q", "mrg_min_w", "mrg_max_q", "mrg_max_w"]].sum()
    cat_p = gp["categoria"].first(); dep_p = gp["departamento"].first(); ces_p = gp["cesta"].any(); nfil = gp.size()
    cu_p = (gp.apply(lambda x: (x["cu"] * x["q"]).sum(), include_groups=False) / soma["q"].replace(0, np.nan))
    vm_p = (gp.apply(lambda x: (x["vm"] * x["q"]).sum(), include_groups=False) / soma["q"].replace(0, np.nan))
    sug = {}
    for prod in soma.index:
        s_ = soma.loc[prod]; cat = cat_p[prod]
        mm = (s_["w_mo"] - s_["w_cu"]) / s_["w_mo"] * 100 if s_["w_mo"] > 0 and s_["cons_q"] >= 0.5 * s_["q"] else np.nan
        base = mm if np.isfinite(mm) else (merc_cat.get(cat, np.nan) * 100 if np.isfinite(merc_cat.get(cat, np.nan)) else np.nan)
        meta_p = s_["meta_lucro"] / s_["meta_venda"] * 100 if s_["meta_venda"] > 0 else np.nan
        meta = meta_p if np.isfinite(meta_p) else (meta_cat.get(cat, np.nan) * 100 if np.isfinite(meta_cat.get(cat, np.nan)) else np.nan)
        if np.isfinite(base):
            alvo = meta if np.isfinite(meta) else base
            o = min(max(alvo, base - DISTANCIA_MERCADO), base + DISTANCIA_MERCADO)
            o = max(o, 0.0)                      # objetiva nunca abaixo de zero
            origem = "mercado do produto" if np.isfinite(mm) else "média de mercado da categoria"
        else:
            atual = s_["mrg_obj_q"] / s_["mrg_obj_w"] if s_["mrg_obj_w"] > 0 else np.nan
            o, origem = (atual, "sem referência de mercado: mantida a objetiva atual") if np.isfinite(atual) else (np.nan, "sem referência de mercado")
        sug[prod] = (round(float(o), 1) if np.isfinite(o) else np.nan, mm, meta, origem)
    so = it["produto"].map(lambda x: sug[x][0]).to_numpy(dtype=float)
    smin = np.zeros(len(it)); smax = so + DISTANCIA_MAX
    smax = np.where(np.isfinite(smax), smax, it["mrg_max"].to_numpy())
    preco = precos_simulados(it, so, smin, smax)
    it["p_sim"] = preco
    cats = []
    r2 = lambda v, k=2: (round(float(v), k) if v is not None and np.isfinite(v) else None)
    for cat, sub in it.groupby("categoria", sort=False):
        prods = []
        for prod, x in sub.groupby("produto", sort=False):
            s_ = soma.loc[prod]; o, mm, meta, origem = sug[prod]
            res = _resumo(x, x["p_sim"].to_numpy())
            prods.append({"nome": prod, "cod": int(str(prod).split(" - ")[0]) if str(prod).split(" - ")[0].isdigit() else None,
                          "cesta": bool(ces_p[prod]), "filiais": int(nfil[prod]), "venda": r2(s_["venda"], 0), "q": r2(s_["q"], 1),
                          "cu": r2(cu_p[prod]), "vm": r2(vm_p[prod]),
                          "mg_ant": r2(s_["lucro_ant"] / s_["venda_ant"] * 100 if s_["venda_ant"] > 0 else np.nan, 1),
                          "lucro_ant": r2(s_["lucro_ant"], 0), "meta": r2(meta, 1), "mg_merc": r2(mm, 1), "origem": origem,
                          "obj": r2(s_["mrg_obj_q"] / s_["mrg_obj_w"] if s_["mrg_obj_w"] > 0 else np.nan, 1),
                          "min": r2(s_["mrg_min_q"] / s_["mrg_min_w"] if s_["mrg_min_w"] > 0 else np.nan, 1),
                          "max": r2(s_["mrg_max_q"] / s_["mrg_max_w"] if s_["mrg_max_w"] > 0 else np.nan, 1),
                          "s_obj": r2(o, 1), "s_min": 0.0, "s_max": r2(o + DISTANCIA_MAX if np.isfinite(o) else np.nan, 1),
                          "consist": r2(s_["cons_q"] / s_["q"] if s_["q"] > 0 else 0, 3), "sim": res})
        prods.sort(key=lambda x: -(x["venda"] or 0))
        mc = merc_cat.get(cat, np.nan); mt = meta_cat.get(cat, np.nan)
        cats.append({"nome": cat, "departamento": str(sub["departamento"].iloc[0]), "meta": r2(mt * 100 if np.isfinite(mt) else np.nan, 1),
                     "mg_merc": r2(mc * 100 if np.isfinite(mc) else np.nan, 1), "produtos": prods})
    cats.sort(key=lambda c: -sum(x["venda"] or 0 for x in c["produtos"]))
    return {"categorias": cats, "faixa": list(FAIXA), "distancia_max": DISTANCIA_MAX, "piso_cesta": PISO_CESTA}


def itens_dos_produtos(it_df: pd.DataFrame, produtos: list[str]) -> dict:
    """Itens (filial + produto) de alguns produtos, para a tela refazer a simulação na hora quando o usuário edita."""
    sub = it_df[it_df["produto"].isin(set(produtos))]
    out = {}
    for prod, x in sub.groupby("produto", sort=False):
        out[prod] = {"cu": [round(float(v), 4) for v in x["cu"]], "q": [round(float(v), 3) for v in x["q"]], "ref": [round(float(v), 2) for v in x["ref"]],
                     "mo": [round(float(v), 2) for v in x["mo"]], "vm": [round(float(v), 2) for v in x["vm"]],
                     "pes": [int(v) for v in x["pes"]], "ces": [int(v) for v in x["cesta"]]}
    return out


# ---------------------------------------------------------------- pedidos de nova margem (aprovação do administrador)
def pedir(usuario: str, nome: str, itens: list[dict], filiais: list[int], escopo_txt: str, origem: str, obs: str = "") -> None:
    """Pedido de nova margem objetiva/mínima/máxima por produto, para as filiais do escopo. Só o administrador aprova."""
    import json
    from core import aprovacoes as ap, db, notificacoes as nt
    corpo = json.dumps({"usuario": usuario, "itens": itens, "filiais": [int(f) for f in filiais], "escopo": escopo_txt,
                        "origem": origem, "obs": obs}, ensure_ascii=False).encode()
    ap.enviar("margens", usuario, f"Nova margem: {len(itens)} produto(s), {escopo_txt}", corpo,
              {"produtos": len(itens), "escopo": escopo_txt, "origem": origem})
    try:
        admins = [u["usuario"] for u in db.listar_usuarios() if u.get("is_admin")]
        nt.enviar(admins, "margem", "Pedido de nova margem",
                  f"{nome} pediu nova margem para {len(itens)} produto(s) ({escopo_txt}), pela {origem}. Revise em Administração › Uploads.")
    except Exception:
        pass


def _codigo_produto(it: dict) -> int:
    """Código do produto do pedido: campo "codigo", o número antes do nome ("12345 - NOME") ou, em pedidos antigos que
    vieram só com o nome, o código achado pelo nome na base atual."""
    import re
    if str(it.get("codigo") or "").strip().isdigit():
        return int(it["codigo"])
    m = re.match(r"\s*(\d+)\s*-", str(it.get("produto") or ""))
    if m:
        return int(m.group(1))
    nome = str(it.get("produto") or "").strip().upper()
    try:
        from views.regular import base_atual
        fonte = base_atual()
        if fonte is not None:
            cats = pd.Series(fonte[0]["Produto"].astype(str).unique())
            ach = cats[cats.str.split(" - ", n=1).str[-1].str.strip().str.upper() == nome]
            if len(ach):
                return int(str(ach.iloc[0]).split(" - ")[0])
    except Exception:
        pass
    raise ValueError(f"Não encontrei o código do produto \"{it.get('produto')}\" na base atual.")


def aplicar(pedido: dict, itens: list[dict], admin: str) -> str:
    """Grava as margens aprovadas (já com as edições do administrador) nas regras do Profimetrics, nas zonas das filiais do pedido."""
    from core import profimetrics as pf
    regras, _ = pf.carregar()
    zonas_disp = tuple(sorted(set(zip(regras["zona"].astype(int), regras["zona_nome"].astype(str))))) if len(regras) else tuple()
    mapa = pf.mapa_filial_zona(zonas_disp) if zonas_disp else {}
    zonas = sorted({mapa.get(int(f)) for f in pedido.get("filiais") or [] if mapa.get(int(f)) is not None})
    if not zonas:
        raise ValueError("Não encontrei a zona de preço das filiais do pedido nas regras do Profimetrics.")
    nomes = dict(zonas_disp)
    atual = regras.drop_duplicates(["produto", "zona"], keep="last").set_index(["produto", "zona"]) if len(regras) else None
    linhas = []
    for it in itens:
        prod = _codigo_produto(it)
        for z in zonas:
            merch = float(atual.loc[(prod, z), "merch"]) if atual is not None and (prod, z) in atual.index else np.nan
            linhas.append({"produto": prod, "zona": int(z), "zona_nome": nomes.get(z, str(z)), "mrg_obj": float(it["obj"]),
                           "mrg_min": float(it["min"]), "mrg_max": float(it["max"]), "merch": merch})
    r = pf.salvar(pd.DataFrame(linhas), admin)
    return f"{len(itens)} produto(s) em {len(zonas)} zona(s): {r['novas']} novas, {r['substituidas']} atualizadas"
