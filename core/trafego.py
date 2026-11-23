"""Medidor do tráfego que sai do Supabase pelo servidor do site, com freio automático.

O plano gratuito do Supabase permite 5 GB de saída por mês (cerca de 160 MB por dia). Toda leitura feita pelo
servidor passa por aqui (core/db.py embrulha o cliente): o tamanho do que voltou é somado por tabela/arquivo.
Passando do limite do dia, o site entra em modo econômico até a meia-noite: o ao vivo pausa e o chat e o sininho
conferem com menos frequência. A tela Administração mostra o consumo do dia.

Não entra na conta: os relatórios que o navegador baixa direto do Storage (esses ficam guardados no navegador e só
são baixados uma vez por versão). Por isso o limite diário fica abaixo dos ~160 MB.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import threading
import time

try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:
    FUSO = dt.timezone(dt.timedelta(hours=-3))

LIMITE_DIA_MB = 120                 # acima disso, modo econômico até o fim do dia
COTA_MES_GB = 5
_ARQ = os.path.join(tempfile.gettempdir(), "pricesense_trafego.json")
_TRAVA = threading.Lock()
_estado: dict = {}
_gravado = 0.0


def _hoje() -> str:
    return dt.datetime.now(FUSO).date().isoformat()


def _carregar() -> dict:
    global _estado
    if _estado.get("dia") == _hoje():
        return _estado
    try:
        with open(_ARQ, encoding="utf-8") as f:
            guardado = json.load(f)
        if guardado.get("dia") == _hoje():
            _estado = guardado
            return _estado
    except (OSError, ValueError):
        pass
    _estado = {"dia": _hoje(), "desde": dt.datetime.now(FUSO).strftime("%H:%M"), "total": 0, "itens": {}}
    return _estado


def _salvar() -> None:
    global _gravado
    if time.time() - _gravado < 20:
        return
    _gravado = time.time()
    try:
        tmp = _ARQ + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_estado, f)
        os.replace(tmp, _ARQ)
    except OSError:
        pass


def somar(rotulo: str, n_bytes: int) -> None:
    if n_bytes <= 0:
        return
    with _TRAVA:
        e = _carregar()
        e["total"] = int(e.get("total", 0)) + int(n_bytes)
        e["itens"][rotulo] = int(e["itens"].get(rotulo, 0)) + int(n_bytes)
        _salvar()


def medir_resposta(rotulo: str, resposta) -> None:
    dados = getattr(resposta, "data", None)
    if not dados:
        somar(rotulo, 200)                  # cabeçalhos da resposta
        return
    try:
        n = len(json.dumps(dados, default=str, ensure_ascii=False).encode("utf-8"))
    except Exception:
        n = 0
    somar(rotulo, n + 200)


def hoje_mb() -> float:
    with _TRAVA:
        return _carregar().get("total", 0) / 1024 / 1024


def economia() -> bool:
    """True quando o site passou do limite do dia: modo econômico até a meia-noite."""
    return hoje_mb() >= LIMITE_DIA_MB


def resumo(top: int = 8) -> dict:
    with _TRAVA:
        e = _carregar()
        itens = sorted(e.get("itens", {}).items(), key=lambda x: -x[1])[:top]
        return {"dia": e["dia"], "desde": e.get("desde", ""), "mb": e.get("total", 0) / 1024 / 1024,
                "itens": [(k, v / 1024 / 1024) for k, v in itens], "limite": LIMITE_DIA_MB}


class Rastreado:
    """Embrulha o cliente do Supabase: tudo funciona igual, e o tamanho de cada resposta é somado."""

    def __init__(self, alvo, rotulo: str = ""):
        object.__setattr__(self, "_alvo", alvo)
        object.__setattr__(self, "_rotulo", rotulo)

    def __getattr__(self, nome):
        attr = getattr(self._alvo, nome)
        if nome == "storage":
            return Rastreado(attr, "arquivo")
        if not callable(attr):
            return attr
        rotulo = self._rotulo

        def chamar(*a, **k):
            r = attr(*a, **k)
            if nome == "execute":
                medir_resposta(rotulo or "banco", r)
                return r
            if nome == "download" and isinstance(r, (bytes, bytearray)):
                somar(f"arquivo: {str(a[0] if a else '').split('/')[0]}", len(r))
                return r
            if nome in ("table", "from_") and a:
                prefixo = "arquivo" if rotulo == "arquivo" else ""
                return Rastreado(r, f"{prefixo}{': ' if prefixo else ''}{a[0]}")
            if nome == "rpc" and a:
                return Rastreado(r, f"função {a[0]}")
            if hasattr(r, "execute"):
                return Rastreado(r, rotulo)
            if nome == "list":
                medir_resposta(rotulo, type("R", (), {"data": r})())
            return r

        return chamar
