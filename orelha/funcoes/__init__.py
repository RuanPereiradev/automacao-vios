"""Funções do Orelha. Cada módulo expõe:
    TITULO        título da seção no relatório
    PRECISA_VIOS  True/False, ou uma função ctx -> bool (padrão True): o main.py só entra no VIOS
                  se alguma função escolhida precisar
    RELATORIO_DIARIO  (opcional, padrão True) False = a seção não entra no relatorio.html do dia; a
                  função gera o próprio documento (é o caso do painel semanal)
    executar(ctx) -> nucleo.modelos.Secao
"""
from funcoes import agenda, intimacoes, painel, parados, planilhas, prazos

REGISTRO = {"agenda": agenda, "prazos": prazos, "intimacoes": intimacoes,
            "parados": parados, "planilhas": planilhas, "painel": painel}

# parados é lenta e painel é semanal: só rodam com --funcoes parados / --funcoes painel (agendamento à parte)
PADRAO = ["agenda", "prazos", "intimacoes", "planilhas"]
