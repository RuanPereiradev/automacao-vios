"""Coletor da consulta de processo pelo WhatsApp (RN26): lê o VIOS só por leitura e responde ao bot.

Reaproveita o núcleo da Orelha (orelha/nucleo: navegador protegido, login, buscar_get) e a leitura da
tabela de tarefas da ficha (orelha/funcoes/parados.py). A pasta orelha/ é só importada, nunca alterada.
Especificação: consulta/CONTRATO.md.
"""
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
PASTA_ORELHA = PASTA.parent / "orelha"
if str(PASTA_ORELHA) not in sys.path:
    sys.path.insert(0, str(PASTA_ORELHA))
