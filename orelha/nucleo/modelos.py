"""Contrato entre o núcleo e as funções do Orelha (ver ORELHA_SPEC, "Contrato entre núcleo e funções").

Cada funcoes/<chave>.py expõe executar(ctx) -> Secao. O main.py monta um Contexto por função
(com ctx.chave preenchido) e transforma qualquer exceção em Secao(erro=...).
"""
import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

NIVEIS = ("info", "atencao", "grave")
# rótulos para quem lê o relatório (leigo)
ROTULOS_NIVEL = {"grave": "Urgente", "atencao": "Atenção", "info": "Para saber"}


@dataclass
class Item:
    titulo: str              # linha principal (ex.: "AUDIÊNCIA UNA (TRABALHISTA) 2026")
    detalhe: str = ""        # complemento (ex.: "14:00 · responsável: Fulano")
    nivel: str = "info"      # "info" | "atencao" | "grave"
    link: str = ""           # link para abrir no VIOS, se houver
    grupo: str = ""          # agrupamento na seção (ex.: responsável, empresa, dia)

    def __post_init__(self):
        if self.nivel not in NIVEIS:
            raise ValueError(f"nível inválido {self.nivel!r} (use {', '.join(NIVEIS)})")


@dataclass
class Secao:
    chave: str               # "agenda" | "prazos" | "intimacoes" | "parados" | "planilhas"
    titulo: str              # "Agenda de hoje e amanhã" etc.
    resumo: str              # uma frase com os números ("3 audiências hoje, 1 perícia amanhã")
    itens: list[Item]
    numeros: dict            # contagens para o resumo.json e a vila (ex.: {"graves": 2})
    erro: str = ""           # se a função falhou: mensagem curta; o relatório sai mesmo assim
    avisos: list[str] = field(default_factory=list)

    def por_nivel(self):
        """{"grave": n, "atencao": n, "info": n}."""
        contagem = {n: 0 for n in reversed(NIVEIS)}
        for item in self.itens:
            contagem[item.nivel] += 1
        return contagem

    def numeros_seguros(self):
        """Só os números de `numeros` (sem dicionários/listas, que podem ter nome de pessoa):
        é o que pode ir para a vila."""
        return {k: v for k, v in (self.numeros or {}).items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)}


def _sem_evento(tipo, **dados):
    return None


@dataclass
class Contexto:
    driver: Any                      # Selenium WebDriver logado no VIOS; None no simulado
    cfg: Any                         # nucleo.config.Config
    hoje: date
    emitir: Callable = _sem_evento   # nucleo.eventos.emitir(tipo, **dados)
    simulado: bool = False
    fixtures: Path = None            # orelha/fixtures/ (raiz; a da função é ctx.pasta_fixtures)
    saida: Path = None               # orelha/saida/<AAAA-MM-DD>/
    historico: Path = None           # orelha/saida/historico/
    chave: str = ""                  # função que está rodando (preenchido pelo main.py)
    albi_saida: Path = None          # pasta dos resultados do Albi (--albi-saida ou ORELHA_ALBI_SAIDA)
    pdf: bool = True                 # False com --sem-pdf (funções que geram o próprio PDF, como o painel)

    @property
    def pasta_fixtures(self):
        """orelha/fixtures/<chave>/"""
        return Path(self.fixtures) / self.chave

    def fixture(self, nome):
        """Caminho de um arquivo em orelha/fixtures/<chave>/."""
        return self.pasta_fixtures / nome

    def ler_historico(self, nome, padrao=None):
        """JSON de orelha/saida/historico/<nome> (padrao se não existe ou está corrompido)."""
        caminho = Path(self.historico) / nome
        try:
            return json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return padrao

    def gravar_historico(self, nome, dados):
        """Grava JSON em orelha/saida/historico/<nome> sem nunca deixar o arquivo pela metade."""
        caminho = Path(self.historico) / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        tmp = caminho.with_name(caminho.name + ".tmp")
        tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, caminho)
        return caminho
