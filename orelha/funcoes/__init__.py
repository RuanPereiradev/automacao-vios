"""Funções do Orelha. Cada módulo expõe:
    TITULO        título da seção no relatório
    PRECISA_VIOS  True/False, ou uma função ctx -> bool (padrão True): o main.py só entra no VIOS
                  se alguma função escolhida precisar
    executar(ctx) -> nucleo.modelos.Secao
"""
from funcoes import agenda, intimacoes, parados, planilhas, prazos

REGISTRO = {"agenda": agenda, "prazos": prazos, "intimacoes": intimacoes,
            "parados": parados, "planilhas": planilhas}

# parados é lenta: só roda com --funcoes parados (ou no agendamento semanal)
PADRAO = ["agenda", "prazos", "intimacoes", "planilhas"]
