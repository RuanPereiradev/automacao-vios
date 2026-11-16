"""Fase do processo a partir das tarefas da ficha (CONTRATO.md, seções 3 e 4).

Só o TIPO da tarefa e as datas entram aqui. Descrição, comentários e responsáveis nunca são lidos
(a leitura da tabela, em orelha/funcoes/parados.py, já ignora essas colunas).
"""
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from consulta import PASTA

ARQUIVO_MAPA = PASTA / "fases_vios.yaml"

FASES = (
    "triagem_documentos", "aguardando_documentos", "pedido_em_preparo", "aguardando_agendamento_inss",
    "em_analise_inss", "exigencia_inss", "aguardando_pericia_inss", "acao_em_preparo", "acao_protocolada",
    "aguardando_pericia_judicial", "aguardando_audiencia", "aguardando_decisao", "em_recurso",
    "decisao_proferida", "implantacao_beneficio", "cumprimento_pagamento", "encerramento", "desconhecida",
)
IGNORAR = "ignorar"
DESCONHECIDA = "desconhecida"
PROXIMOS = ("pericia", "audiencia")


def sem_acento(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


_PARENTESES = re.compile(r"\([^)]*\)")
_ANO = re.compile(r"\b20\d\d\b")
_APOS_TRACO = re.compile(r"\s*-\s*[A-Z ]*$")
_CIDADE = re.compile(r"\s+(CAMOCIM|JIJOCA|SOBRAL|TIANGUA|EMPRESA)$")


def tipo_base(nome):
    """'ACOMPANHAR MOB (PREVIDENCIÁRIO)- SOBRAL 2026' -> 'ACOMPANHAR MOB'.

    Tira QUALQUER parêntese (área, segmento, "(B2C)"), ano, "- CIDADE" / "- PROCESSO" no fim e a cidade
    solta no fim. Sem acento, maiúsculas, espaços únicos."""
    n = _PARENTESES.sub(" ", sem_acento(nome))
    n = _ANO.sub(" ", n)
    n = " ".join(n.split())
    n = _APOS_TRACO.sub("", n).strip()
    n = _CIDADE.sub("", n)
    return n.strip(" -:")


@dataclass
class Mapa:
    tipos: dict            # tipo-base normalizado -> código | "ignorar"
    prefixos: list         # [(prefixo normalizado, código)]
    encaminhar: frozenset
    proximo: dict          # início do tipo-base normalizado -> "pericia" | "audiencia"
    regras: list = field(default_factory=list)   # [(regex sobre o nome completo, código)]

    def codigo(self, nome_tarefa):
        """Código da fase, "ignorar" ou "desconhecida" para o nome real da tarefa no VIOS."""
        base = tipo_base(nome_tarefa)
        if not base:
            return DESCONHECIDA
        if base in self.tipos:
            return self.tipos[base]
        completo = sem_acento(nome_tarefa)
        for regex, codigo in self.regras:
            if regex.search(completo):
                return codigo
        for prefixo, codigo in self.prefixos:
            if base == prefixo or base.startswith(prefixo + " "):
                return codigo
        return DESCONHECIDA

    def tipo_proximo(self, nome_tarefa):
        base = tipo_base(nome_tarefa)
        for inicio, tipo in self.proximo.items():
            if base == inicio or base.startswith(inicio + " "):
                return tipo
        return None


class MapaErro(Exception):
    pass


def carregar_mapa(caminho=ARQUIVO_MAPA):
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or {}
    validos = set(FASES) | {IGNORAR}
    tipos = {tipo_base(k): str(v) for k, v in (dados.get("tipos") or {}).items()}
    prefixos = [(sem_acento(k), str(v)) for k, v in (dados.get("prefixos") or {}).items()]
    regras = []
    for r in dados.get("regras") or []:
        try:
            regras.append((re.compile(str(r["padrao"])), str(r["fase"])))
        except (KeyError, re.error):
            raise MapaErro("fases_vios.yaml: regra inválida") from None
    for codigo in list(tipos.values()) + [c for _, c in prefixos] + [c for _, c in regras]:
        if codigo not in validos:
            raise MapaErro(f"código de fase desconhecido em fases_vios.yaml: {codigo}")
    proximo = {tipo_base(k): str(v) for k, v in (dados.get("proximo") or {}).items()}
    if any(v not in PROXIMOS for v in proximo.values()):
        raise MapaErro("fases_vios.yaml: 'proximo' aceita só pericia ou audiencia")
    enc = frozenset(dados.get("encaminhar") or [])
    if not enc <= set(FASES):
        raise MapaErro("fases_vios.yaml: 'encaminhar' tem código desconhecido")
    return Mapa(tipos=tipos, prefixos=prefixos, encaminhar=enc, proximo=proximo, regras=regras)


@dataclass
class Decisao:
    fase: str = DESCONHECIDA
    desde: date = None
    proximo: dict = None      # {"tipo": ..., "data": date} ou None
    encaminhar: bool = True


def _chave_ci(t):
    return int(t.ci) if str(t.ci).isdigit() else 0


def _tarefa_decide(tarefas, mapa):
    """Primeira tarefa da lista (já em ordem de preferência) cujo tipo define a fase; None se só há
    tipos ignorados."""
    for t in tarefas:
        codigo = mapa.codigo(t.tipo)
        if codigo != IGNORAR:
            return t, codigo
    return None, DESCONHECIDA


def decidir(leitura, hoje, mapa, segredo=False):
    """LeituraFicha (de parados.ler_tarefas_html) -> Decisao.

    Regra: tarefa ABERTA mais recente (o passo atual; CI maior = mais nova); se não houver aberta que
    defina fase, a CONCLUÍDA mais recente (por data de conclusão, depois CI). Canceladas nunca contam;
    tipos "ignorar" são pulados. Ficha que não leu, com tabela cortada ou sem tarefa que defina a fase
    -> "desconhecida" e encaminhar."""
    if leitura is None or leitura.erro or not leitura.achou_tabela:
        return Decisao(encaminhar=True)
    tarefas = [t for t in leitura.tarefas if not t.cancelada]
    if leitura.total_informado is not None and leitura.total_informado > len(leitura.tarefas):
        return Decisao(encaminhar=True)  # a ficha mostrou só parte das tarefas

    abertas = sorted((t for t in tarefas if t.aberta), key=_chave_ci, reverse=True)
    concluidas = sorted((t for t in tarefas if t.concluida),
                        key=lambda t: (t.concluida_em or date.min, _chave_ci(t)), reverse=True)
    escolhida, fase = _tarefa_decide(abertas, mapa)
    if escolhida is None:
        escolhida, fase = _tarefa_decide(concluidas, mapa)

    if escolhida is None:
        fase, desde = DESCONHECIDA, None
    elif escolhida.concluida:
        desde = escolhida.concluida_em
    else:
        # passo atual ainda aberto: "desde" = quando terminou o passo anterior
        datas = [t.concluida_em for t in concluidas if t.concluida_em and t.concluida_em <= hoje]
        desde = max(datas) if datas else None

    return Decisao(fase=fase, desde=desde, proximo=_proximo(abertas, hoje, mapa),
                   encaminhar=bool(segredo) or fase in mapa.encaminhar or fase == DESCONHECIDA)


def _proximo(abertas, hoje, mapa):
    """Perícia ou audiência com tarefa aberta e data prevista de hoje em diante (a mais próxima).
    A data é a de "Para conclusão"; sem ela, o "Limite"."""
    melhor = None
    for t in abertas:
        tipo = mapa.tipo_proximo(t.tipo)
        data = t.para_conclusao or t.limite
        if tipo and data and data >= hoje and (melhor is None or data < melhor["data"]):
            melhor = {"tipo": tipo, "data": data}
    return melhor
