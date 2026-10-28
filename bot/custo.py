"""Custo das chamadas de IA e teto de gasto por execução (LLM_LIMITE_US).

O custo é calculado pelos tokens que a API devolve em cada resposta, com a
tabela PRECOS (US$ por milhão de tokens). Antes de cada chamada (ou de cada
lote) o bot estima o custo: se passar do teto, a chamada não é feita e a CI
fica com erro (não é lançada no VIOS).

Os preços são de referência e podem mudar: conferir em openai.com/api/pricing
e, se precisar, corrigir pelo .env em LLM_PRECOS (ex.: "gpt-5.6=5/30,gpt-5.6-luna=1/6").
Modelo fora da tabela usa o preço mais alto, para o teto nunca ficar folgado.
"""
import logging
import os

from bot.ia import IAErro

log = logging.getLogger(__name__)

# trecho do nome do modelo -> (entrada, saída) em US$ por milhão de tokens; o 1º que casar vale
PRECOS = [
    ("luna", (1.0, 6.0)),
    ("terra", (2.5, 15.0)),
    ("gpt-5.6", (5.0, 30.0)),
    ("claude-opus-5-5", (4.0, 20.0)),
    ("claude-sonnet-5-5", (2.0, 10.0)),
    ("claude-haiku-5-5", (0.10, 0.50)),
    ("claude-haiku", (1.0, 5.0)),
    ("claude-sonnet", (3.0, 15.0)),
    ("claude-opus", (5.0, 25.0)),
]
PRECO_MAXIMO = (5.0, 30.0)
FATOR_CACHE = 0.1        # token de entrada em cache custa ~10% do normal
FATOR_LOTE = 0.5         # Batch API: metade do preço
BUSCA_US = 0.01          # cada pesquisa na web (US$ 10 por 1.000)
CARACTERES_POR_TOKEN = 3.2
SAIDA_ESTIMADA = 2000    # tokens de saída por intimação (média até 10/2026: ~1.000; maior: ~2.000)
PESQUISA_ESTIMADA_US = 0.30  # uma pesquisa de feriados (um tribunal)


class LimiteGasto(IAErro):
    pass


def _precos_env():
    precos = {}
    for par in os.getenv("LLM_PRECOS", "").split(","):
        if "=" in par and "/" in par:
            modelo, valores = par.split("=", 1)
            entrada, saida = valores.split("/", 1)
            precos[modelo.strip().lower()] = (float(entrada), float(saida))
    return precos


class Gasto:
    """Soma o gasto da execução e confere o teto (0 = sem teto)."""

    def __init__(self, limite=0.0):
        self.limite = limite
        self.total = 0.0       # gasto já confirmado pelas respostas
        self.reservado = 0.0   # estimativa dos lotes enviados e ainda sem resposta
        self.precos = _precos_env()
        self._avisados = set()

    @classmethod
    def do_env(cls):
        texto = os.getenv("LLM_LIMITE_US", "").strip().replace(",", ".")
        return cls(float(texto) if texto else 0.0)

    def preco(self, modelo):
        nome = (modelo or "").lower()
        if nome in self.precos:
            return self.precos[nome]
        for trecho, preco in PRECOS:
            if trecho in nome:
                return preco
        if nome not in self._avisados:
            self._avisados.add(nome)
            log.warning("Custo: modelo '%s' fora da tabela, usando o preço mais alto (LLM_PRECOS corrige)", modelo)
        return PRECO_MAXIMO

    def custo(self, modelo, uso, lote=False):
        entrada, saida = self.preco(modelo)
        cache = uso.get("entrada_cache", 0)
        valor = ((uso.get("entrada", 0) - cache) * entrada + cache * entrada * FATOR_CACHE
                 + uso.get("saida", 0) * saida) / 1e6
        return valor * (FATOR_LOTE if lote else 1) + uso.get("buscas", 0) * BUSCA_US

    def estimar(self, modelo, sistema, usuario, lote=False):
        """Estimativa de uma análise: instruções (skill) em cache, intimação a preço cheio."""
        fixo, variavel = len(sistema) / CARACTERES_POR_TOKEN, len(usuario) / CARACTERES_POR_TOKEN
        uso = {"entrada": fixo + variavel, "entrada_cache": fixo, "saida": SAIDA_ESTIMADA}
        return self.custo(modelo, uso, lote)

    def cabe(self, valor):
        return not self.limite or self.total + self.reservado + valor <= self.limite

    def conferir(self, valor, o_que="chamada"):
        if not self.cabe(valor):
            raise LimiteGasto(f"Teto de gasto atingido (LLM_LIMITE_US={self.limite:g}; gasto até agora "
                              f"US$ {self.total + self.reservado:.2f}): {o_que} não feita")

    def registrar(self, modelo, uso, lote=False):
        valor = self.custo(modelo, uso or {}, lote)
        self.total += valor
        return valor

    def resumo(self):
        teto = f" (teto US$ {self.limite:.2f})" if self.limite else ""
        return f"US$ {self.total:.2f}{teto}"
