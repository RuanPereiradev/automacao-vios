"""Funções do Orelha. Cada módulo expõe:
    TITULO        título da seção no relatório
    PRECISA_VIOS  True/False, ou uma função ctx -> bool (padrão True): o main.py só entra no VIOS
                  se alguma função escolhida precisar
    RELATORIO_DIARIO  (opcional, padrão True) False = a seção não entra no relatorio.html do dia; a
                  função gera o próprio documento (é o caso do painel semanal)
    executar(ctx) -> nucleo.modelos.Secao
"""
from funcoes import agenda, comentarios, intimacoes, painel, parados, planilhas, prazos, processos

REGISTRO = {"agenda": agenda, "prazos": prazos, "intimacoes": intimacoes,
            "parados": parados, "planilhas": planilhas, "painel": painel,
            "processos": processos, "comentarios": comentarios}

# parados é lenta, painel é semanal, processos e comentarios são exportações: só rodam quando pedidas
# (--funcoes parados / painel / processos / comentarios)
PADRAO = ["agenda", "prazos", "intimacoes", "planilhas"]
