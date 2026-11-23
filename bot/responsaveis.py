"""Responsáveis da tarefa, pela skill da Controladoria de 18/11/2026 (pacote atualizado).

- Nunca `automático` e nunca AMANDA LEITE MENDES (ela só lança, não executa as tarefas).
- Advogado auxiliar (a intimação traz a sigla: SUH, TAMI, JOHN...; o nome completo vem da lista do VIOS,
  saida/responsaveis.json). CARL vai para JOHNYS (FRANCISCO JOHNYS VASCONCELOS BARBOSA) em todas as tarefas;
  única exceção: cliente CALTECH, para quem CARL continua com Carlos (CARLOS AUGUSTO ALVES CAMILO BRANDÃO).
  Sem auxiliar: o advogado responsável do processo, exceto RONIELLE FEITOSA (no VIOS: RONEELY FEITOSA):
  aí a tarefa não é lançada.
- PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026: o responsável da filial informada e mapeada (Camocim, Tianguá,
  Jijoca de Jericoacoara, Sobral). Sem filial mapeada, o texto `incluir responsável pela cidade identificada`
  vai no TXT e NÃO bloqueia. A filial vem só do teor da intimação, nunca da cidade do CSV.
  Na hora de lançar, o "Escritório atual" da ficha do processo no VIOS define o responsável (segunda checagem,
  bot/lancamento.py); sem filial ali, a tarefa não é lançada (o bot não consegue identificar a cidade).
"""
import json
import re
from pathlib import Path

from bot.prazos import normalizar

AMANDA = "AMANDA LEITE MENDES"
JOHNYS = "FRANCISCO JOHNYS VASCONCELOS BARBOSA"
BRENO = "BRENO SILVA MOTA"
PERICIA_MEDICA = "PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO)"  # início do nome da tarefa (vem com " 2026")

# filial -> (padrão da cidade no texto sem acento, responsável pela perícia)
FILIAIS = {
    "CAMOCIM": (r"\bCAMOCIM\b", "FRANCISCO VICTOR HORA DO NASCIMENTO"),
    "TIANGUÁ": (r"\bTIANGUA\b", "JOÃO JÂNIO"),
    "JIJOCA DE JERICOACOARA": (r"\b(JIJOCA|JERICOACOARA)\b", "GUIVIA VASCONCELOS"),
    "SOBRAL": (r"\bSOBRAL\b", "ANA LETÍCIA DA SILVA LEITAO"),
}
CARLOS = "CARLOS AUGUSTO ALVES CAMILO BRANDÃO"
CIDADE_IDENTIFICADA = "incluir responsável pela cidade identificada"  # texto exato da skill (perícia sem filial mapeada)
MSG_RONIELLE = ("NÃO LANÇAR — VERIFICAR QUEM É O ADVOGADO AUXILIAR OU O ADVOGADO RESPONSÁVEL CORRETO; "
                "PROCESSO SEM AUXILIAR E COM RONIELLE FEITOSA COMO RESPONSÁVEL.")
MSG_FILIAL = "NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL DA PERÍCIA MÉDICA JUDICIAL."


def carregar(pasta_saida):
    """Lista de pessoas do VIOS (saida/responsaveis.json; ./rodar_revisao.sh --atualizar-responsaveis refaz)."""
    try:
        dados = json.loads((Path(pasta_saida) / "responsaveis.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [p for p in dados if isinstance(p, str) and p.strip()]


def eh_amanda(nome):
    return normalizar(nome) == normalizar(AMANDA)


def eh_ronielle(nome):
    """RONIELLE FEITOSA, também como está no VIOS (RONEELY FEITOSA)."""
    partes = normalizar(nome).split()
    return len(partes) >= 2 and partes[-1] == "FEITOSA" and partes[0] in ("RONIELLE", "RONEELY")


def _achar(nome, pessoas):
    """O nome como está na lista do VIOS (comparando sem acento e caixa), ou None."""
    alvo = normalizar(nome)
    return next((p for p in pessoas if normalizar(p) == alvo), None)


def nome_do_auxiliar(sigla, pessoas):
    """Nome completo de uma sigla de auxiliar (SUH -> SUHIANE DE MARIA GOMES SILVA): a sigla é o começo de
    uma palavra do nome (JOHN -> JOHNYS). Só devolve se for uma pessoa só; senão None (ex.: CARL)."""
    s = normalizar(sigla)
    if len(s) < 3:
        return None
    achados = [p for p in pessoas if any(w.startswith(s) for w in normalizar(p).split())]
    return achados[0] if len(achados) == 1 else None


def siglas(item):
    return [s.strip().upper() for s in re.split(r"[/,;]", item.get("auxiliares", "") or "") if s.strip()]


def do_processo(item, pessoas):
    """(nomes, bloqueio, alertas) de uma tarefa comum: auxiliares do processo; sem auxiliar, o advogado responsável.
    CARL vai para o Johnys, salvo cliente CALTECH (Carlos continua)."""
    if not pessoas:
        return [], ("Lista de responsáveis do VIOS indisponível (saida/responsaveis.json): "
                    "rodar ./rodar_revisao.sh --atualizar-responsaveis."), []
    nomes, sem_nome, alertas = [], [], []
    for sigla in siglas(item):
        if sigla == "CARL":
            caltech = "CALTECH" in normalizar(item.get("cliente", ""))
            nome = _achar(CARLOS if caltech else JOHNYS, pessoas) or (CARLOS if caltech else JOHNYS)
        else:
            nome = nome_do_auxiliar(sigla, pessoas)
        if not nome:
            sem_nome.append(sigla)
        elif nome not in nomes:
            nomes.append(nome)
    if sem_nome:
        alertas.append("Auxiliar sem nome completo na lista do VIOS: " + ", ".join(sem_nome) + ".")
    if not nomes and not siglas(item):
        adv = (item.get("advogado") or "").strip()
        if eh_ronielle(adv):
            return [], MSG_RONIELLE, alertas
        achado = _achar(adv, pessoas) if adv else None
        if not achado:
            return [], ("Sem auxiliar e sem advogado responsável identificado na lista do VIOS"
                        + (f" ('{adv}')" if adv else "") + ": informar o responsável."), alertas
        nomes = [achado]
        alertas.append(f"Sem auxiliar: tarefa para o advogado responsável ({achado}).")
    if not nomes:
        return [], "Auxiliar " + ", ".join(sem_nome) + " sem nome completo na lista do VIOS: informar o responsável.", alertas
    if any(eh_amanda(n) for n in nomes):
        return [], f"A tarefa não pode ficar com a {AMANDA} (ela só lança, não executa).", alertas
    return nomes, "", alertas


def filial_da_pericia(item):
    """(filial, responsável) da perícia médica judicial pela cidade citada no teor da intimação. Nunca pela cidade
    do CSV nem pelo local da perícia (skill de 18/11/2026). Mais de uma filial ou nenhuma: (None, None)."""
    achadas = [f for f, (padrao, _) in FILIAIS.items() if re.search(padrao, normalizar(item.get("texto", "") or ""))]
    if len(achadas) != 1:
        return None, None
    return achadas[0], FILIAIS[achadas[0]][1]


def da_pericia_medica(item, pessoas):
    """(nomes, bloqueio, alertas) da PERÍCIA MÉDICA JUDICIAL: o responsável da filial mapeada; sem filial,
    o texto `incluir responsável pela cidade identificada` (não bloqueia). Nunca Amanda nem Suhiane."""
    filial, nome = filial_da_pericia(item)
    if not nome:
        return [CIDADE_IDENTIFICADA], "", ["Perícia médica judicial: filial não identificada no teor; "
                                           "no TXT vai o texto `incluir responsável pela cidade identificada`."]
    achado = _achar(nome, pessoas) if pessoas else nome
    if not achado:
        return [], f"{MSG_FILIAL} ({nome} não está na lista do VIOS)", []
    return [achado], "", [f"Perícia médica judicial: responsável da filial de {filial.title()} ({achado})."]


def filial_do_escritorio(escritorio):
    """(filial, responsável) pelo "Escritório atual" da ficha do processo (ex.: "Roneely Feitosa - Sobral").
    Nenhuma ou mais de uma filial no nome do escritório: (None, None)."""
    t = normalizar(escritorio or "")
    achadas = [f for f, (padrao, _) in FILIAIS.items() if re.search(padrao, t)]
    if len(achadas) != 1:
        return None, None
    return achadas[0], FILIAIS[achadas[0]][1]


def da_pericia_pelo_escritorio(escritorio, pessoas):
    """(nomes, bloqueio, alertas) da PERÍCIA MÉDICA JUDICIAL pelo "Escritório atual" do processo no VIOS."""
    filial, nome = filial_do_escritorio(escritorio)
    if not nome:
        return [], f"{MSG_FILIAL} (Escritório atual do processo no VIOS: '{(escritorio or '').strip() or 'não encontrado'}')", []
    achado = _achar(nome, pessoas) if pessoas else nome
    if not achado:
        return [], f"{MSG_FILIAL} ({nome} não está na lista do VIOS)", []
    return [achado], "", [f"Perícia médica judicial: Escritório atual do processo no VIOS é '{escritorio.strip()}', "
                          f"responsável da filial de {filial.title()} ({achado})."]


def da_tarefa(item, tarefa, pessoas):
    """(nomes, bloqueio, alertas) de uma tarefa da análise. A petição da Execução da Tamira leva também o Breno."""
    nome = tarefa["nome"]
    if nome.startswith(PERICIA_MEDICA):
        return da_pericia_medica(item, pessoas)
    nomes, bloqueio, alertas = do_processo(item, pessoas)
    if nomes and tarefa.get("marcar_breno"):
        breno = _achar(BRENO, pessoas)
        if breno and breno not in nomes:
            nomes.append(breno)
    return nomes, bloqueio, alertas
