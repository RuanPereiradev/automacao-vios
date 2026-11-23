import io
import json
import unittest
import urllib.error

from consulta import cripto
from consulta.cliente import BotErro, ClienteBot, corpo_json


class RespostaFalsa:
    def __init__(self, status=200, corpo=b""):
        self.status, self._corpo = status, corpo

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._corpo


class Abridor:
    """Troca o urlopen: guarda a requisição e devolve respostas prontas (ou levanta)."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.requisicoes = []

    def __call__(self, req, timeout=None):
        self.requisicoes.append(req)
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def cliente(abridor):
    return ClienteBot("https://bot.exemplo.invalid/", "segredo-de-teste", agora_ms=lambda: 1700000000000, abrir=abridor)


class TestCliente(unittest.TestCase):
    def test_get_pendentes_assinado(self):
        corpo = json.dumps({"pedidos": [{"id": "a", "cpfCifrado": "Zm9v"}]}).encode()
        ab = Abridor(RespostaFalsa(200, corpo))
        self.assertEqual(cliente(ab).pendentes(), [{"id": "a", "cpfCifrado": "Zm9v"}])
        req = ab.requisicoes[0]
        self.assertEqual(req.full_url, "https://bot.exemplo.invalid/consulta/pendentes")
        self.assertEqual(req.get_method(), "GET")
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("X-consulta-timestamp"), "1700000000000")
        self.assertEqual(req.get_header("X-consulta-assinatura"),
                         "7e5fed99c34a267c4d44ed98e546ab88efa3ee1540665602d10d5c66120dc9f5")

    def test_post_resultado_assina_o_corpo_enviado(self):
        ab = Abridor(RespostaFalsa(200, b'{"ok":true}'))
        resultado = {"id": "abc", "status": "erro", "telefones": [], "processos": [], "lidoEm": "x"}
        self.assertTrue(cliente(ab).enviar_resultado(resultado))
        req = ab.requisicoes[0]
        corpo = req.data.decode("utf-8")
        self.assertEqual(corpo, corpo_json(resultado))
        self.assertNotIn(" ", corpo.replace('"lidoEm":"x"', ""))   # JSON compacto
        self.assertEqual(req.get_header("X-consulta-assinatura"),
                         cripto.assinar("segredo-de-teste", "1700000000000", "POST", "/consulta/resultado", corpo))
        self.assertEqual(req.get_method(), "POST")

    def test_corpo_com_acento_assina_utf8(self):
        self.assertEqual(corpo_json({"a": "ç"}), '{"a":"ç"}')

    def test_410_nao_e_erro(self):
        ab = Abridor(urllib.error.HTTPError("u", 410, "gone", {}, io.BytesIO(b"")))
        self.assertFalse(cliente(ab).enviar_resultado({"id": "a"}))

    def test_erros_do_bot(self):
        for status, trecho in ((401, "assinatura"), (404, "desligada"), (500, "500")):
            with self.subTest(status=status):
                ab = Abridor(urllib.error.HTTPError("u", status, "x", {}, io.BytesIO(b"")))
                with self.assertRaises(BotErro) as cm:
                    cliente(ab).pendentes()
                self.assertIn(trecho, str(cm.exception))

    def test_422_e_rede_fora(self):
        with self.assertRaises(BotErro):
            cliente(Abridor(urllib.error.HTTPError("u", 422, "x", {}, io.BytesIO(b"")))).enviar_resultado({"id": "a"})
        with self.assertRaises(BotErro) as cm:
            cliente(Abridor(urllib.error.URLError("sem rede https://bot.exemplo.invalid"))).pendentes()
        self.assertNotIn("exemplo", str(cm.exception))

    def test_resposta_fora_do_formato(self):
        with self.assertRaises(BotErro):
            cliente(Abridor(RespostaFalsa(200, b"nao e json"))).pendentes()
        with self.assertRaises(BotErro):
            cliente(Abridor(RespostaFalsa(200, b'{"pedidos":[{"id":"a"}]}'))).pendentes()
        self.assertEqual(cliente(Abridor(RespostaFalsa(200, b'{"pedidos":[]}'))).pendentes(), [])


if __name__ == "__main__":
    unittest.main()


class TestCertificadoProprio(unittest.TestCase):
    """CONSULTA_CERTIFICADO: no Mac o bot usa certificado próprio; o cliente confia só nele."""

    def test_certificado_inexistente_falha_ao_montar(self):
        from consulta.cliente import ClienteBot
        with self.assertRaises((FileNotFoundError, OSError)):
            ClienteBot("https://localhost:3000", "s", certificado="/nao/existe/certificado.pem")

    def test_sem_certificado_usa_validacao_padrao(self):
        from consulta.cliente import ClienteBot
        ClienteBot("https://exemplo.invalid", "s")  # não levanta
