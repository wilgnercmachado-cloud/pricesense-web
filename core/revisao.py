"""Revisão de margem: categoria → produto, por estado ou filial, com margens sugeridas e simulação contra a meta.

Regras combinadas com o usuário:
- margem do último mês (só loja) = lucro ÷ venda do mês anterior, mesmos dias (bloco "ritmo do mês" do HTML de competitividade);
- meta de margem = meta de lucro ÷ meta de venda do mesmo bloco (produto; somando, a da categoria);
- margem de mercado = (moda − custo médio) ÷ moda, ponderada pelo volume;
- objetiva sugerida = a menor margem que faz a categoria bater a meta: o novo preço (custo ÷ (1 − objetiva)) vale só nos itens
  NÃO cesta (fundo de sortimento); os da cesta ficam no preço atual; a margem resultante é ponderada pela venda (volume);
- máxima sugerida = objetiva sugerida + 5 pontos; mínima sugerida = 0; o usuário pode editar tudo;
- diagnóstico pelo IP (preço ÷ moda, ponderado pelo volume): 98,9 a 100,9 dentro da faixa; acima de 100,9 zona crítica;
  abaixo de 98,9 zona de atenção; com pesquisa inconsistente, avisa que falta consistência.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DISTANCIA_MAX = 5.0          # pontos entre a objetiva e a máxima sugeridas
FAIXA = (0.989, 1.009)


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


def produtos(df: pd.DataFrame, regras: pd.DataFrame | None) -> pd.DataFrame:
    """Uma linha por produto no recorte (estado/filial já filtrado)."""
    from core import profimetrics as pf
    q = df["qtd"].astype(float).clip(lower=0).to_numpy()
    q = np.where(q > 0, q, 1e-6)
    cu, vm, mo = (df[c].astype(float).to_numpy() for c in ("cu", "vm", "mo"))
    tem_mo = mo > 0
    consist = (df["moda_dias"].astype(float).to_numpy() >= 3) if "moda_dias" in df else tem_mo
    consist = consist & ~df.get("erro_pesquisa", pd.Series(False, index=df.index)).astype(bool).to_numpy()
    r = pf.regras_por_item(_cod(df["Filial"]), _cod(df["Produto"]), regras) if regras is not None and len(regras) else None
    base = pd.DataFrame({
        "produto": df["Produto"].astype(str).to_numpy(), "categoria": df["Categoria"].astype(str).to_numpy(),
        "departamento": df["Departamento"].astype(str).to_numpy(),
        "cesta": (df["Cesta"].astype(str).str.upper() == "CESTA").to_numpy() if "Cesta" in df else False,
        "q": q, "venda": df["venda"].astype(float).to_numpy(),
        "cuq": cu * q, "vmq": vm * q, "moq": np.where(tem_mo, mo * q, 0), "cuq_mo": np.where(tem_mo, cu * q, 0), "vmq_mo": np.where(tem_mo, vm * q, 0),
        "q_mo": np.where(tem_mo, q, 0), "q_cons": np.where(consist, q, 0),
        "lucro_ant": df.get("lucro_ant", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "venda_ant": df.get("venda_ant", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "meta_lucro": df.get("meta_lucro", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
        "meta_venda": df.get("meta_venda", pd.Series(0.0, index=df.index)).astype(float).to_numpy(),
    })
    for c in ("mrg_obj", "mrg_min", "mrg_max"):
        v = r[c].to_numpy(dtype=float) if r is not None else np.full(len(df), np.nan)
        base[c + "_q"] = np.where(np.isfinite(v), v * q, 0)
        base[c + "_w"] = np.where(np.isfinite(v), q, 0)
    g = base.groupby("produto", sort=False)
    soma = g[[c for c in base.columns if c not in ("produto", "categoria", "departamento", "cesta")]].sum()
    p = pd.DataFrame(index=soma.index)
    p["categoria"] = g["categoria"].first(); p["departamento"] = g["departamento"].first(); p["cesta"] = g["cesta"].any()
    p["filiais"] = g.size()
    p["venda"] = soma["venda"]; p["q"] = soma["q"]
    p["cu"] = soma["cuq"] / soma["q"]; p["vm"] = soma["vmq"] / soma["q"]
    p["moda"] = np.where(soma["q_mo"] > 0, soma["moq"] / soma["q_mo"].replace(0, np.nan), np.nan)
    p["mg_ant"] = np.where(soma["venda_ant"] > 0, soma["lucro_ant"] / soma["venda_ant"].replace(0, np.nan), np.nan)
    p["meta"] = np.where(soma["meta_venda"] > 0, soma["meta_lucro"] / soma["meta_venda"].replace(0, np.nan), np.nan)
    p["mg_merc"] = np.where(soma["moq"] > 0, (soma["moq"] - soma["cuq_mo"]) / soma["moq"].replace(0, np.nan), np.nan)
    p["ip_atual"] = np.where(soma["moq"] > 0, soma["vmq_mo"] / soma["moq"].replace(0, np.nan), np.nan)
    p["consist"] = soma["q_cons"] / soma["q"]
    for c in ("mrg_obj", "mrg_min", "mrg_max"):
        p[c] = np.where(soma[c + "_w"] > 0, soma[c + "_q"] / soma[c + "_w"].replace(0, np.nan), np.nan)
    # para a simulação da categoria
    p["moq"] = soma["moq"]; p["q_mo"] = soma["q_mo"]
    return p.reset_index()


def _objetiva_para_meta(p: pd.DataFrame, meta: float) -> tuple[float, str]:
    """Menor objetiva (fração) que leva a margem ponderada da categoria à meta, mexendo só no preço dos itens não cesta.
    Nunca abaixo da margem de mercado do fundo de sortimento (não há por que ficar abaixo do mercado se a meta já fecha)
    e no máximo 60%. Devolve também um aviso quando a meta já fecha ou não fecha só com o fundo de sortimento."""
    if not np.isfinite(meta):
        return np.nan, "Sem meta de margem"
    q, cu, vm, ces = p["q"].to_numpy(), p["cu"].to_numpy(), p["vm"].to_numpy(), p["cesta"].to_numpy()
    if (~ces).sum() == 0:
        return np.nan, "Só itens da cesta"

    def margem(o):
        preco = np.where(ces, vm, cu / (1 - o))
        rec = (preco * q).sum()
        return ((preco - cu) * q).sum() / rec if rec > 0 else np.nan

    nc = p[~p["cesta"]]
    moq, cuq = nc["moq"].sum(), (nc["cu"] * nc["q_mo"]).sum()
    piso = max(0.0, (moq - cuq) / moq) if moq > 0 else 0.0           # margem de mercado do fundo de sortimento
    teto = 0.60
    if margem(teto) < meta:
        return teto, "Meta fora de alcance só com o fundo de sortimento"
    lo, hi = 0.0, teto
    if margem(lo) >= meta:
        return piso, "Meta já fecha: objetiva na margem de mercado"
    for _ in range(50):
        mid = (lo + hi) / 2
        if margem(mid) >= meta:
            hi = mid
        else:
            lo = mid
    return max(hi, piso), ""


def montar(df: pd.DataFrame, regras: pd.DataFrame | None) -> dict:
    """Pacote para a tela: categorias com os produtos e as sugestões iniciais (em %)."""
    p = produtos(df, regras)
    cats = []
    for cat, sub in p.groupby("categoria", sort=False):
        sub = sub.sort_values("venda", ascending=False)
        meta_v = (sub["meta"] * sub["venda"]).sum() / sub["venda"].sum() if sub["venda"].sum() > 0 and sub["meta"].notna().any() else np.nan
        o, aviso = _objetiva_para_meta(sub, meta_v)
        o_pct = round(float(o) * 100, 1) if np.isfinite(o) else None
        prods = []
        for _, x in sub.iterrows():
            atual_obj = float(x["mrg_obj"]) if np.isfinite(x["mrg_obj"]) else None
            sug_obj = (atual_obj if x["cesta"] else o_pct) if (x["cesta"] or o_pct is not None) else atual_obj
            sug_max = round(sug_obj + DISTANCIA_MAX, 1) if sug_obj is not None else None
            r2 = lambda v, k=2: (round(float(v), k) if v is not None and np.isfinite(v) else None)
            prods.append({"nome": x["produto"], "cesta": bool(x["cesta"]), "filiais": int(x["filiais"]), "venda": r2(x["venda"], 0), "q": r2(x["q"], 2),
                          "cu": r2(x["cu"]), "vm": r2(x["vm"]), "moda": r2(x["moda"]), "mg_ant": r2(x["mg_ant"] * 100 if np.isfinite(x["mg_ant"]) else np.nan, 1),
                          "meta": r2(x["meta"] * 100 if np.isfinite(x["meta"]) else np.nan, 1), "mg_merc": r2(x["mg_merc"] * 100 if np.isfinite(x["mg_merc"]) else np.nan, 1),
                          "obj": r2(x["mrg_obj"], 1), "min": r2(x["mrg_min"], 1), "max": r2(x["mrg_max"], 1),
                          "s_obj": sug_obj, "s_min": 0.0, "s_max": sug_max, "consist": r2(x["consist"], 3), "ip_atual": r2(x["ip_atual"], 4)})
        cats.append({"nome": cat, "departamento": str(sub["departamento"].iloc[0]), "meta": round(float(meta_v) * 100, 1) if np.isfinite(meta_v) else None,
                     "s_obj": o_pct, "aviso": aviso, "produtos": prods})
    cats.sort(key=lambda c: -sum(x["venda"] or 0 for x in c["produtos"]))
    return {"categorias": cats, "faixa": list(FAIXA), "distancia_max": DISTANCIA_MAX}


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
        prod = int(str(it["produto"]).split(" - ")[0])
        for z in zonas:
            merch = float(atual.loc[(prod, z), "merch"]) if atual is not None and (prod, z) in atual.index else np.nan
            linhas.append({"produto": prod, "zona": int(z), "zona_nome": nomes.get(z, str(z)), "mrg_obj": float(it["obj"]),
                           "mrg_min": float(it["min"]), "mrg_max": float(it["max"]), "merch": merch})
    r = pf.salvar(pd.DataFrame(linhas), admin)
    return f"{len(itens)} produto(s) em {len(zonas)} zona(s): {r['novas']} novas, {r['substituidas']} atualizadas"
