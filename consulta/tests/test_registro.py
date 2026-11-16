import logging
import unittest

from consulta import registro


class TestFiltro(unittest.TestCase):
    def test_mascara_cpf_telefone_hmac_e_parametros(self):
        casos = [
            "erro em 390.533.447-05 e 39053344705",
            "GET ?pag=x&pesq[cpfcnpj]=390.533.447-05&Pesq=Pesquisar falhou",
            "telefone (88) 99284-3164 e +55 88 99284-3164",
            "hash " + "ab" * 32,
            "processos_id=9101",
        ]
        for c in casos:
            with self.subTest(c=c):
                saida = registro.limpar_texto(c)
                for proibido in ("390.533", "39053344705", "99284", "abab", "9101"):
                    self.assertNotIn(proibido, saida)

    def test_filtro_no_handler(self):
        rec = logging.LogRecord("consulta", logging.WARNING, "x", 1, "falhou %s", ("39053344705",), (ValueError, ValueError("39053344705"), None))
        registro.FiltroPrivacidade().filter(rec)
        self.assertNotIn("39053344705", rec.getMessage())
        self.assertIsNone(rec.exc_info)

    def test_texto_comum_passa(self):
        self.assertEqual(registro.limpar_texto("pedido abc-123: ok em 0.4 s"), "pedido abc-123: ok em 0.4 s")


if __name__ == "__main__":
    unittest.main()
