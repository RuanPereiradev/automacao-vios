"""Carrega a skill da Controladoria (SKILL.md + referências) para usar como prompt."""
import re
from pathlib import Path

REFERENCIAS = [
    "pop-fluxo-intimacoes.md",
    "roteamento-interno.md",
    "tarefas-vios.md",
    "regras-prazos-recursos.md",
    "validacao-lancamento.md",
]

# respostas permitidas além das tarefas da lista oficial
ESPECIAIS = [
    "PENDENTE – CONFIRMAR OPÇÕES DISPONÍVEIS NO VIOS",
    "NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA",
]


def carregar_texto(pasta):
    """SKILL.md sem o cabeçalho YAML, seguido das referências na ordem da skill."""
    pasta = Path(pasta)
    skill = (pasta / "SKILL.md").read_text(encoding="utf-8")
    skill = re.sub(r"\A---\n.*?\n---\n", "", skill, flags=re.S)
    partes = [skill.strip()]
    for nome in REFERENCIAS:
        texto = (pasta / "references" / nome).read_text(encoding="utf-8").strip()
        partes.append(f"<referencia arquivo=\"references/{nome}\">\n{texto}\n</referencia>")
    return "\n\n".join(partes)


# tarefas que já existem no VIOS e ainda não estão na skill (o VIOS dividiu a de laudo em 10/11/2026)
NOVAS_NO_VIOS = ["MINUTAR RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026", "MINUTAR PETIÇÃO INTERMEDIÁRIA (PREVIDENCIÁRIO)"]


def tarefas_oficiais(pasta):
    """Nomes da 1ª coluna das tabelas de references/tarefas-vios.md."""
    texto = (Path(pasta) / "references" / "tarefas-vios.md").read_text(encoding="utf-8")
    nomes = []
    for linha in texto.splitlines():
        if not linha.startswith("| ") or linha.startswith("| Tarefa VIOS") or linha.startswith("| ---"):
            continue
        nome = linha.split("|")[1].strip()
        if nome and nome not in nomes:
            nomes.append(nome)
    for nome in NOVAS_NO_VIOS:
        if nome not in nomes:
            nomes.append(nome)
    return nomes
