"""Sugestão de preço do comprador (visão Comercial) para o Pricing.

Regras combinadas com o usuário:
- qualquer item; o comprador informa varejo e atacado (o atacado começa igual ao varejo) e um motivo da lista + observação
  (obrigatória em "Outros"); fora da mínima ou da máxima, o comprador confirma que sugere fora dos parâmetros;
- o Pricing aceita direto (individual ou todas), ou rejeita com motivo obrigatório; o comprador é avisado;
- a sugestão vale no dia: no dia seguinte a pendente expira e o comprador recebe o preço aplicado e a regra de negócio.
"""
from __future__ import annotations

import datetime as dt
import uuid

import streamlit as st

from core import db, notificacoes as nt
from core import reports

TABELA = "sugestoes_preco"
MOTIVOS = ["Negociação com fornecedor", "Acordo comercial", "Erro de pesquisa", "Estratégia da categoria", "Outros"]
FUSO = dt.timezone(dt.timedelta(hours=-3))
brl = lambda v: ("R$ " + f"{float(v):,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")


def hoje() -> str:
    return dt.datetime.now(FUSO).date().isoformat()


@st.cache_data(ttl=20, show_spinner=False)
def do_dia() -> list[dict]:
    try:
        return db.sb().table(TABELA).select("*").eq("dia", hoje()).execute().data or []
    except Exception:
        return []


def _analistas(estado: str) -> list[str]:
    """Analistas de Pricing (setor PRICE) do estado da sugestão."""
    sig = str(estado or "").split(" - ")[0].strip().upper()
    out = []
    for u in db.listar_usuarios():
        if str(u.get("status")) != "Aprovado":
            continue
        setor = str(u.get("setor") or "").strip().upper()
        if not (setor.startswith("PRICE") or setor == "PRICING"):
            continue
        ests = reports.estados_do_usuario(u.get("estado"))
        if "TODOS" in ests or sig in ests:
            out.append(u["usuario"])
    return out


def criar(reg: dict, usuario: str) -> dict:
    if reg.get("motivo") not in MOTIVOS:
        raise ValueError("Escolha o motivo da sugestão.")
    if reg["motivo"] == "Outros" and not str(reg.get("observacao") or "").strip():
        raise ValueError("Em \"Outros\", descreva o motivo na observação.")
    linha = {"id": str(uuid.uuid4()), "dia": hoje(), "status": "pendente", "usuario": usuario,
             "criado_em": dt.datetime.now(dt.timezone.utc).isoformat(),
             **{k: reg.get(k) for k in ("filial", "produto", "estado", "varejo", "atacado", "motivo", "observacao", "fora_parametros",
                                        "produto_nome", "filial_nome", "preco_vencedor", "novo_sugerido")}}
    # uma sugestão pendente por filial + produto no dia: a nova substitui a anterior
    db.sb().table(TABELA).update({"status": "substituida"}).eq("dia", linha["dia"]).eq("filial", linha["filial"]).eq("produto", linha["produto"]) \
        .eq("status", "pendente").execute()
    db.sb().table(TABELA).insert(linha).execute()
    do_dia.clear()
    nt.enviar(_analistas(linha["estado"]), "sugestao", "Nova sugestão do comprador",
              f"{usuario} sugeriu {brl(linha['varejo'])} (atacado {brl(linha['atacado'])}) para {linha.get('produto_nome')} em "
              f"{linha.get('filial_nome')}: {linha['motivo']}{' - ' + linha['observacao'] if linha.get('observacao') else ''}.")
    return linha


def aceitar(ids: list[str], analista: str) -> int:
    alvo = [s for s in do_dia() if s["id"] in set(ids) and s["status"] == "pendente"]
    agora = dt.datetime.now(dt.timezone.utc).isoformat()
    for s in alvo:
        db.sb().table(TABELA).update({"status": "aceita", "decidido_por": analista, "decidido_em": agora}).eq("id", s["id"]).execute()
        nt.enviar([s["usuario"]], "sugestao_aceita", "Sugestão aceita",
                  f"{analista} aceitou sua sugestão de {brl(s['varejo'])} para {s.get('produto_nome')} em {s.get('filial_nome')}.")
    do_dia.clear()
    return len(alvo)


def rejeitar(ident: str, analista: str, motivo: str) -> None:
    if not str(motivo or "").strip():
        raise ValueError("Informe o motivo da rejeição.")
    s = next((x for x in do_dia() if x["id"] == ident), None)
    if not s:
        return
    db.sb().table(TABELA).update({"status": "rejeitada", "decidido_por": analista, "motivo_rejeicao": motivo.strip(),
                                  "decidido_em": dt.datetime.now(dt.timezone.utc).isoformat()}).eq("id", ident).execute()
    do_dia.clear()
    nt.enviar([s["usuario"]], "sugestao_rejeitada", "Sugestão rejeitada",
              f"{analista} rejeitou sua sugestão de {brl(s['varejo'])} para {s.get('produto_nome')} em {s.get('filial_nome')}: {motivo.strip()}.")


def registrar_aplicados(itens: list[dict]) -> None:
    """Na exportação da importação: guarda o preço aplicado e a regra dos itens que têm sugestão no dia."""
    if not itens:
        return
    chaves = {(int(x["filial"]), int(x["produto"])): x for x in itens}
    for s in do_dia():
        x = chaves.get((int(s["filial"]), int(s["produto"])))
        if x and s["status"] in ("pendente", "aceita"):
            db.sb().table(TABELA).update({"aplicado_varejo": x.get("nv"), "aplicado_atacado": x.get("na"), "regra_aplicada": x.get("regra")}) \
                .eq("id", s["id"]).execute()
    do_dia.clear()


def expirar_antigas() -> int:
    """Pendentes de dias anteriores expiram; o comprador recebe o preço aplicado e a regra de negócio (ou o aviso de que nada foi importado)."""
    try:
        velhas = db.sb().table(TABELA).select("*").eq("status", "pendente").lt("dia", hoje()).execute().data or []
    except Exception:
        return 0
    for s in velhas:
        db.sb().table(TABELA).update({"status": "expirada", "decidido_em": dt.datetime.now(dt.timezone.utc).isoformat()}).eq("id", s["id"]).execute()
        aplic = (f"Preço aplicado: {brl(s['aplicado_varejo'])} (atacado {brl(s.get('aplicado_atacado') or s['aplicado_varejo'])}), regra de negócio: "
                 f"{s.get('regra_aplicada') or '-'}." if s.get("aplicado_varejo") else "Nenhum preço foi importado para esse item no dia.")
        nt.enviar([s["usuario"]], "sugestao_expirada", "Sugestão expirada sem retorno",
                  f"Sua sugestão de {brl(s['varejo'])} para {s.get('produto_nome')} em {s.get('filial_nome')} ({s['dia']}) expirou sem retorno. {aplic}")
    return len(velhas)


def criar_lote(itens: list[dict], usuario: str) -> int:
    """Mesma sugestão para várias filiais de um produto (visão em cascata): uma linha por filial e um só aviso por analista."""
    if not itens:
        return 0
    base = itens[0]
    if base.get("motivo") not in MOTIVOS:
        raise ValueError("Escolha o motivo da sugestão.")
    if base["motivo"] == "Outros" and not str(base.get("observacao") or "").strip():
        raise ValueError("Em \"Outros\", descreva o motivo na observação.")
    dia, agora = hoje(), dt.datetime.now(dt.timezone.utc).isoformat()
    linhas = []
    for reg in itens:
        linha = {"id": str(uuid.uuid4()), "dia": dia, "status": "pendente", "usuario": usuario, "criado_em": agora,
                 **{k: reg.get(k) for k in ("filial", "produto", "estado", "varejo", "atacado", "motivo", "observacao", "fora_parametros",
                                            "produto_nome", "filial_nome", "preco_vencedor", "novo_sugerido")}}
        db.sb().table(TABELA).update({"status": "substituida"}).eq("dia", dia).eq("filial", linha["filial"]).eq("produto", linha["produto"]) \
            .eq("status", "pendente").execute()
        linhas.append(linha)
    for k in range(0, len(linhas), 500):
        db.sb().table(TABELA).insert(linhas[k:k + 500]).execute()
    do_dia.clear()
    por_estado: dict[str, list[dict]] = {}
    for x in linhas:
        por_estado.setdefault(str(x.get("estado") or ""), []).append(x)
    for est, lst in por_estado.items():
        nt.enviar(_analistas(est), "sugestao", "Nova sugestão do comprador",
                  f"{usuario} sugeriu {brl(base['varejo'])} (atacado {brl(base['atacado'])}) para {base.get('produto_nome')} em "
                  f"{len(lst)} filial(is): {base['motivo']}{' - ' + base['observacao'] if base.get('observacao') else ''}.")
    return len(linhas)
