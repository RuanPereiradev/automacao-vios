"""Testes do rodar_relatorio.py (captura + PDF numa execução), sem abrir o VIOS."""
import unittest
from unittest import mock

import rodar_relatorio as rr


class TestDividir(unittest.TestCase):
    def test_padrao(self):
        self.assertEqual(rr.dividir([]), (".env.usuario2", [], []))

    def test_ia_e_refazer_so_no_pdf(self):
        env, captura, pdf = rr.dividir([".env.usuario2", "--grupo", "PAO MIX", "--ia", "--encerrados", "--refazer"])
        self.assertEqual(env, ".env.usuario2")
        self.assertEqual(captura, ["--grupo", "PAO MIX", "--encerrados"])
        self.assertEqual(pdf, ["--ia", "--refazer"])

    def test_sem_env_o_valor_do_grupo_nao_vira_env(self):
        env, captura, _ = rr.dividir(["--grupo", "todos", "--sem-grupo"])
        self.assertEqual(env, ".env.usuario2")
        self.assertEqual(captura, ["--grupo", "todos", "--sem-grupo"])


class TestMain(unittest.TestCase):
    def _rodar(self, codigos, *args):
        chamadas = []

        def rodar(script, *a):
            chamadas.append((script, a))
            return codigos[script]

        with mock.patch.object(rr, "rodar", side_effect=rodar), mock.patch("builtins.print"):
            return rr.main(*args), chamadas

    def test_tudo_certo(self):
        codigo, chamadas = self._rodar({"relatorio_processos.py": 0, "relatorio_cliente.py": 0},
                                       ".env.usuario2", "--grupo", "3A FRIOS", "--ia")
        self.assertEqual(codigo, 0)
        self.assertEqual(chamadas, [("relatorio_processos.py", (".env.usuario2", "--grupo", "3A FRIOS")),
                                    ("relatorio_cliente.py", (".env.usuario2", "--ia"))])

    def test_captura_falhou_pdf_roda_e_sai_com_1(self):
        codigo, chamadas = self._rodar({"relatorio_processos.py": 1, "relatorio_cliente.py": 0})
        self.assertEqual(codigo, 1)
        self.assertEqual([c[0] for c in chamadas], ["relatorio_processos.py", "relatorio_cliente.py"])

    def test_pdf_falhou_sai_com_1(self):
        codigo, _ = self._rodar({"relatorio_processos.py": 0, "relatorio_cliente.py": 1})
        self.assertEqual(codigo, 1)

    def test_rodar_usa_o_mesmo_python(self):
        with mock.patch.object(rr.subprocess, "run") as run:
            run.return_value.returncode = 3
            self.assertEqual(rr.rodar("relatorio_cliente.py", ".env.usuario2"), 3)
        comando = run.call_args.args[0]
        self.assertEqual(comando[0], rr.sys.executable)
        self.assertTrue(comando[1].endswith("relatorio_cliente.py"))


if __name__ == "__main__":
    unittest.main()
