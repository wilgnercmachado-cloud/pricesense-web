"""Precificação sobre a base do relatório Pricing GMAT3.

Regras trazidas do próprio relatório:
- Índice de preço (IP) = nosso varejo ÷ menor preço do mercado.
- "Mercado abaixo da mínima": margem no preço do mercado ((menor − custo) ÷ menor) abaixo de −15%.
  O relatório não acompanha esses itens na baixa.
- Zona neutra do simulador: só sobe se IP < 98% e só baixa se IP > 101%.
- Não mexe em itens com ação vigente (encarte, mídia, vencimento) nem em erro de pesquisa.
- "TRAVADO - VENCIMENTO" fica de fora; "EM AÇÃO PROMOCIONAL" não recebe baixa.
- Atacado sem preço de mercado: usa a base de redução do produto ou a proporção atual atacado/varejo.
Regra pedida para o Pricing Regular: novo varejo e novo atacado R$ 0,01 abaixo do menor preço do mercado.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.preco_bot import arredondar_atacado

STATUS = ["Mercado igual", "Mercado maior", "Mercado menor", "Mercado abaixo da mínima", "Sem pesquisa"]


def status_mercado(df: pd.DataFrame, margem_min: float = -0.15, tolerancia: float = 0.05) -> np.ndarray:
    mk, vm, cu = df["mk"].to_numpy(np.float64), df["vm"].to_numpy(np.float64), df["cu"].to_numpy(np.float64)
    tem = (mk > 0) & (vm > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = (mk - cu) / mk
    out = np.full(len(df), 4, dtype=np.int8)
    out[tem & (np.abs(mk - vm) <= tolerancia + 1e-9)] = 0
    out[tem & (mk > vm) & ~(np.abs(mk - vm) <= tolerancia + 1e-9)] = 1
    out[tem & (mk < vm) & ~(np.abs(mk - vm) <= tolerancia + 1e-9)] = 2
    out[tem & (g < margem_min)] = 3
    return out


# ---------------------------------------------------------------- arredondamento da companhia (vetorizado)
def _validos(faixa: str) -> np.ndarray:
    v = []
    for c in range(100):
        p, u = c // 10, c % 10
        if faixa == "A": ok = u in (5, 8, 9)
        elif faixa == "B": ok = 1 <= p <= 9 and u in (5, 8, 9)
        elif faixa == "C": ok = 3 <= p <= 9 and (p in (5, 9) if u == 0 else u in (0, 5, 8, 9))
        else: ok = 3 <= p <= 9 and (p in (5, 9) if u == 0 else u == 9)
        if ok: v.append(c)
    return np.array(v)


_VALIDOS = {f: _validos(f) for f in "ABCD"}


def arredondar_varejo_vetor(p: np.ndarray) -> np.ndarray:
    """Mesmo resultado de preco_bot.arredondar_varejo (inclusive nos empates), para arrays inteiros."""
    p = np.round(np.asarray(p, dtype=np.float64), 2)
    out = p.copy()
    faixa = np.where(p <= 10.99, "A", np.where(p <= 19.99, "B", np.where(p <= 40.00, "C", "D")))
    for f, val in _VALIDOS.items():
        m = (faixa == f) & (p > 0)
        if not m.any():
            continue
        base = np.floor(p[m])[:, None]
        frac = val / 100.0
        cands = np.round(np.concatenate([(base - 1) + frac, base + frac, (base + 1) + frac], axis=1), 2)
        dist = np.abs(cands - p[m][:, None])
        exato = (cands == p[m][:, None]).any(axis=1)
        escolha = cands[np.arange(len(cands)), dist.argmin(axis=1)]
        out[m] = np.where(exato, p[m], escolha)
    return out


# ---------------------------------------------------------------- motor
def precificar(df: pd.DataFrame, centavos: float = 0.01, margem_min: float = -0.15, piso_ip: float = 0.98,
               teto_ip: float = 1.01, direcao: str = "Subir e baixar", abaixo_minima: str = "Não acompanhar",
               arredondar: bool = False, incluir_acoes: bool = False, excluir_erros: bool = True,
               proteger_cesta: bool = False) -> pd.DataFrame:
    cu = df["cu"].to_numpy(np.float64); vm = df["vm"].to_numpy(np.float64); am = df["am"].to_numpy(np.float64)
    mk = df["mk"].to_numpy(np.float64); amk = df["amk"].to_numpy(np.float64)
    classe = df["Classificação"].astype(str).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        ip = np.where((vm > 0) & (mk > 0), vm / mk, np.nan)
        un = np.where((df["venda"].to_numpy() > 0) & (vm > 0), df["venda"].to_numpy() / vm, 0.0)
    st_ = status_mercado(df, margem_min)

    elegivel = (mk > 0) & (vm > 0) & (classe != "TRAVADO - VENCIMENTO")
    motivo = np.full(len(df), "", dtype=object)
    motivo[~((mk > 0) & (vm > 0))] = "Sem pesquisa"
    motivo[(classe == "TRAVADO - VENCIMENTO") & elegivel] = "Travado (vencimento)"
    if excluir_erros:
        m = df["erro_pesquisa"].to_numpy() & elegivel; motivo[m] = "Erro de pesquisa"; elegivel &= ~m
    if not incluir_acoes:
        m = df["em_acao"].to_numpy() & elegivel; motivo[m] = "Em ação (encarte, mídia ou vencimento)"; elegivel &= ~m
    motivo[(classe == "TRAVADO - VENCIMENTO")] = "Travado (vencimento)"

    alvo = np.round(mk - centavos, 2)
    piso_margem = np.where(cu > 0, cu / (1 - margem_min), 0.0)          # preço com margem = mínima (ex.: −15%)
    sobe = elegivel & (ip < piso_ip) & (alvo > vm)
    desce = elegivel & (ip > teto_ip) & (alvo < vm) & (classe != "EM AÇÃO PROMOCIONAL")
    motivo[elegivel & (ip > teto_ip) & (classe == "EM AÇÃO PROMOCIONAL")] = "Em ação promocional (sem baixa)"
    if proteger_cesta and "Cesta" in df:
        cesta = (df["Cesta"].astype(str) == "CESTA").to_numpy()
        motivo[sobe & cesta] = "Cesta protegida (sem alta)"
        sobe &= ~cesta
    if direcao == "Só baixar": sobe[:] = False
    if direcao == "Só subir": desce[:] = False

    abaixo = (cu > 0) & (alvo < piso_margem)
    if abaixo_minima == "Não acompanhar":
        bloq = desce & abaixo
        motivo[bloq] = "Mercado abaixo da mínima (−15%)"
        desce &= ~bloq
    else:  # baixa só até o piso de margem
        alvo = np.where(desce & abaixo, np.ceil(piso_margem * 100) / 100, alvo)
        desce &= alvo < vm
        motivo[desce & abaixo] = "Limitado ao piso de margem"

    muda = sobe | desce
    novo = np.where(muda, alvo, vm)
    if arredondar and muda.any():
        r = arredondar_varejo_vetor(novo[muda])
        alvo_m, vm_m = alvo[muda], vm[muda]
        sobe_m = sobe[muda]
        # o arredondamento não pode inverter a direção nem furar a margem mínima
        r = np.where(sobe_m & (r <= vm_m), alvo_m, r)
        r = np.where(~sobe_m & (r >= vm_m), alvo_m, r)
        r = np.where(r < piso_margem[muda], np.ceil(piso_margem[muda] * 100) / 100, r)
        novo[muda] = r
    motivo[sobe & (motivo == "")] = "Abaixo do mercado: sobe para mercado − R$ 0,01"
    motivo[desce & (motivo == "")] = "Acima do mercado: baixa para mercado − R$ 0,01"
    motivo[(motivo == "") & elegivel] = "Na zona neutra"

    # atacado
    bred = df["base_red_atacado"].to_numpy(np.float64) if "base_red_atacado" in df else np.full(len(df), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        at_base = np.where(amk > 0, np.round(amk - centavos, 2),
                           np.where(~np.isnan(bred), novo * (1 - bred / 100), np.where((am > 0) & (vm > 0), am * novo / vm, np.nan)))
    at_base = np.where(np.isnan(at_base), np.nan, np.minimum(at_base, novo))
    at_base = np.where(~np.isnan(at_base) & (cu > 0) & (at_base < piso_margem), np.ceil(piso_margem * 100) / 100, at_base)
    at_novo = np.where(muda, at_base, np.where(am > 0, am, np.nan))
    if arredondar:
        idx = np.where(muda & ~np.isnan(at_novo))[0]
        at_novo[idx] = [arredondar_atacado(float(a), float(v)) for a, v in zip(at_novo[idx], novo[idx])]
    at_novo = np.round(at_novo, 2)

    with np.errstate(divide="ignore", invalid="ignore"):
        out = pd.DataFrame({
            "status": pd.Categorical.from_codes(st_, STATUS),
            "ip_atual": ip, "ip_novo": np.where(mk > 0, novo / mk, np.nan),
            "novo_varejo": np.round(novo, 2), "novo_atacado": at_novo,
            "margem_atual": np.where((vm > 0) & (cu > 0), (vm - cu) / vm, np.nan),
            "margem_nova": np.where((novo > 0) & (cu > 0), (novo - cu) / novo, np.nan),
            "un_mes": un, "impacto_mes": (novo - vm) * un,
            "acao": np.where(sobe, "Subir", np.where(desce, "Baixar", "Manter")),
            "motivo": motivo,
        }, index=df.index)
    return out


def resumo(df: pd.DataFrame, res: pd.DataFrame) -> dict:
    un = res["un_mes"].to_numpy(); vm = df["vm"].to_numpy(np.float64); mk = df["mk"].to_numpy(np.float64)
    cu = df["cu"].to_numpy(np.float64); nv = res["novo_varejo"].to_numpy()
    w = np.where(un > 0, un, 1.0)
    pes = (mk > 0) & (vm > 0)
    def ip(p): return float((p[pes] * w[pes]).sum() / (mk[pes] * w[pes]).sum()) if pes.any() else np.nan
    cv = (cu > 0) & (un > 0) & (vm > 0)
    def mg(p): return float(((p[cv] - cu[cv]) * un[cv]).sum() / (p[cv] * un[cv]).sum()) if cv.any() else np.nan
    imp = res["impacto_mes"].to_numpy()
    return {"linhas": len(df), "skus": int(df["Produto"].nunique()), "filiais": int(df["Filial"].nunique()),
            "sobem": int((res["acao"] == "Subir").sum()), "baixam": int((res["acao"] == "Baixar").sum()),
            "bloqueados": int((res["motivo"] == "Mercado abaixo da mínima (−15%)").sum()),
            "ip_atual": ip(vm), "ip_novo": ip(nv), "margem_atual": mg(vm), "margem_nova": mg(nv),
            "ganho": float(imp[imp > 0].sum()), "investimento": float(-imp[imp < 0].sum()),
            "status": res["status"].value_counts().reindex(STATUS, fill_value=0).to_dict()}
