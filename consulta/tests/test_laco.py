import threading
import unittest
from datetime import date

from cryptography.hazmat.primitives.asymmetric import rsa

from consulta import coletor, cripto, fases, laco
from consulta.cliente import BotErro
from consulta.erros import SessaoPerdida
from consulta.tests.test_coletor import AGORA, CHAVE, CPF, fonte

PRIVADA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OP = coletor.Opcoes(chave_telefone=CHAVE)
MAPA = fases.carregar_mapa()


def pedido(pid="p"):
    return {"id": pid, "cpfCifrado": cripto.cifrar_cpf(CPF, PRIVADA.public_key())}


class BotMemoria:
    def __init__(self, pedidos, falhas=0):
        self.fila, self.recebidos, self.falhas = list(pedidos), [], falhas

    def pendentes(self):
        if self.falhas:
            self.falhas -= 1
            raise BotErro("sem conexão com o bot (URLError)")
        saida, self.fila = self.fila[:5], self.fila[5:]
        return saida

    def enviar_resultado(self, r):
        self.recebidos.append(r)
        return True


class FonteQueCai(type(fonte())):
    """Cai na primeira consulta e volta depois de reiniciar()."""

    def __init__(self, *a, caidas=1, **kw):
        super().__init__(*a, **kw)
        self.caidas, self.reinicios = caidas, 0

    def lista_processos(self, c):
        if self.caidas:
            self.caidas -= 1
            raise SessaoPerdida("caiu")
        return super().lista_processos(c)

    def reiniciar(self):
        self.reinicios += 1


class TestLaco(unittest.TestCase):
    def processar(self, f):
        return lambda ped: laco.processar_com_relogin(ped, PRIVADA, f, OP, MAPA, date(2026, 11, 16), AGORA)

    def test_um_ciclo_devolve_todos(self):
        bot = BotMemoria([pedido("a"), pedido("b")])
        codigo = laco.laco(bot, self.processar(fonte()), 0, uma_vez=True)
        self.assertEqual(codigo, 0)
        self.assertEqual([(r["id"], r["status"]) for r in bot.recebidos], [("a", "ok"), ("b", "ok")])

    def test_relogin_uma_vez(self):
        base = fonte()
        f = FonteQueCai(listas=base.listas, pessoas=base.pessoas, formularios=base.formularios, fichas=base.fichas)
        bot = BotMemoria([pedido()])
        laco.laco(bot, self.processar(f), 0, uma_vez=True)
        self.assertEqual(f.reinicios, 1)
        self.assertEqual(bot.recebidos[0]["status"], "ok")

    def test_sessao_que_nao_volta_vira_erro(self):
        base = fonte()
        f = FonteQueCai(listas=base.listas, pessoas=base.pessoas, formularios=base.formularios, fichas=base.fichas,
                        caidas=99)
        bot = BotMemoria([pedido()])
        laco.laco(bot, self.processar(f), 0, uma_vez=True)
        self.assertEqual(f.reinicios, 2)
        self.assertEqual(bot.recebidos[0]["status"], "erro")

    def test_bot_fora_do_ar(self):
        self.assertEqual(laco.laco(BotMemoria([], falhas=1), self.processar(fonte()), 0, uma_vez=True), 1)

    def test_laco_continuo_sobrevive_a_falha_e_para_no_evento(self):
        bot = BotMemoria([pedido("a")], falhas=1)
        parar = threading.Event()
        original = bot.enviar_resultado

        def enviar(r):
            parar.set()
            return original(r)

        bot.enviar_resultado = enviar
        laco.laco(bot, self.processar(fonte()), 0.01, parar=parar)
        self.assertEqual(len(bot.recebidos), 1)


if __name__ == "__main__":
    unittest.main()
