"""Modo --simulado: fixtures no lugar do VIOS e um bot falso em memória no lugar do bot de verdade.

Tudo fictício (repo público): CPFs de teste válidos, nomes e telefones inventados. O bot falso cifra os
CPFs como o bot de verdade (RSA-OAEP SHA-256), recebe os resultados, confere o formato do contrato e
confere o que cada cenário deveria devolver.
"""
import uuid

from cryptography.hazmat.primitives.asymmetric import rsa

from consulta import PASTA
from consulta.cripto import cifrar_cpf, hmac_telefone, normalizar_telefone
from consulta.montagem import validar_resultado

PASTA_FIXTURES = PASTA / "fixtures"
CHAVE_TELEFONE = "chave-de-teste"

CPF_DOIS_PROCESSOS = "39053344705"   # 2 processos: um previdenciário, um cível sem mapa
CPF_SEM_PROCESSO = "52998224725"     # nenhum processo
CPF_DIVERGENTE = "11144477735"       # processo achado, mas o cadastro tem outro CPF
TELEFONE_DO_CADASTRO = "558800000001"  # normalizado do celular fictício do cadastro de CPF_DOIS_PROCESSOS


def gerar_chaves(bits=2048):
    privada = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    return privada, privada.public_key()


class BotFalso:
    """Mesma interface do ClienteBot (pendentes / enviar_resultado)."""

    def __init__(self, chave_publica, cenarios=None):
        self.cenarios = cenarios or [
            (CPF_DOIS_PROCESSOS, "ok"), (CPF_SEM_PROCESSO, "nao_encontrado"), (CPF_DIVERGENTE, "erro"),
            ("12345678900", "erro"),   # CPF inválido: o coletor não consulta o VIOS
        ]
        self.pedidos = {}
        for cpf, esperado in self.cenarios:
            self.pedidos[str(uuid.uuid4())] = {"cpfCifrado": cifrar_cpf(cpf, chave_publica),
                                               "esperado": esperado, "cpf": cpf}
        self._entregues = set()
        self.resultados = {}
        self.problemas = []

    def pendentes(self):
        saida = []
        for pid, p in self.pedidos.items():
            if pid not in self._entregues and len(saida) < 5:
                self._entregues.add(pid)
                saida.append({"id": pid, "cpfCifrado": p["cpfCifrado"]})
        return saida

    def enviar_resultado(self, resultado):
        try:
            validar_resultado(resultado)
        except ValueError as e:
            self.problemas.append(f"resultado fora do contrato ({e})")
            return False
        if resultado["id"] not in self.pedidos:
            self.problemas.append("resultado de pedido desconhecido")
            return False
        self.resultados[resultado["id"]] = resultado
        return True

    def conferir(self):
        """Lista de problemas (vazia = o simulado se comportou como esperado). Nunca devolve CPF."""
        problemas = list(self.problemas)
        for pid, p in self.pedidos.items():
            r = self.resultados.get(pid)
            if r is None:
                problemas.append(f"cenário sem resultado ({p['esperado']})")
            elif r["status"] != p["esperado"]:
                problemas.append(f"cenário {p['esperado']}: veio {r['status']}")
            elif p["cpf"] == CPF_DOIS_PROCESSOS:
                esperado = hmac_telefone(CHAVE_TELEFONE, normalizar_telefone("(88) 90000-0001"))
                if esperado not in r["telefones"]:
                    problemas.append("o telefone do cadastro não veio no resultado")
                if len(r["processos"]) != 2:
                    problemas.append("esperava 2 processos")
                elif [p["atualizacao"] for p in r["processos"]] != [True, False]:
                    problemas.append("atualizacao esperada: [true, false]")
        return problemas

    def resumo(self):
        contagem = {}
        for r in self.resultados.values():
            contagem[r["status"]] = contagem.get(r["status"], 0) + 1
        return contagem
