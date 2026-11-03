"""Relatório CSV de cada execução (abre no Excel): uma linha por tarefa do calendário,
com classificação, decisão, motivo e os dados lidos. Cada execução cria um arquivo novo."""
import csv
from datetime import datetime

COLUNAS = [
    ("modo", "Modo"),
    ("tarefa", "Tarefa"),
    ("link_tarefa", "Link da tarefa"),
    ("classificacao", "Classificação"),
    ("decisao", "Decisão"),
    ("motivo", "Motivo / dúvida"),
    ("ressalvas", "Ressalvas"),
    ("processo_id", "Id do processo"),
    ("link_processo", "Link do processo"),
    ("cnj_tela_processo", "CNJ na tela do processo"),
    ("comprovante", "Comprovante"),
    ("cnj_pdf", "CNJ (PDF)"),
    ("orgao_pdf", "Órgão julgador (PDF)"),
    ("valor_pdf", "Valor da causa (PDF)"),
    ("cnj_edicao", "N.° CNJ (VIOS)"),
    ("orgao_edicao", "Órgão julgador (VIOS)"),
    ("valor_edicao", "Valor da ação (VIOS)"),
    ("preencheria", "Campos vazios que seriam preenchidos"),
]


def _celula(valor):
    """Texto da célula; começo com = + - @ vira texto para o Excel não tratar como fórmula."""
    texto = " ".join(str(valor if valor is not None else "").split())
    return "'" + texto if texto[:1] in ("=", "+", "-", "@") else texto


def escrever(pasta, linhas, quando=None):
    """Cria saida/relatorio_AAAA-MM-DD_HHMMSS.csv (separador ';', UTF-8 com BOM). Nunca sobrescreve."""
    pasta.mkdir(exist_ok=True)
    arquivo = pasta / f"relatorio_{(quando or datetime.now()):%Y-%m-%d_%H%M%S}.csv"
    with open(arquivo, "x", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([titulo for _, titulo in COLUNAS])
        for linha in linhas:
            w.writerow([_celula(linha.get(chave)) for chave, _ in COLUNAS])
    return arquivo
