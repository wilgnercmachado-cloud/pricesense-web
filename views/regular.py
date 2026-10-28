"""Pricing Regular (em migração)."""
from __future__ import annotations

from ui import components as ui


def render() -> None:
    ui.cabecalho("Pricing Regular", "Análises competitivas de preço regular.")
    ui.vazio("Este módulo está em migração",
             "As análises de preço regular estão sendo trazidas para a nova plataforma. "
             "Enquanto isso, use a Pesquisa de Mercado para consultar moda e menor preço da concorrência.")
