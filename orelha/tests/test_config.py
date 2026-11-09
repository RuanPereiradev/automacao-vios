import tempfile
import unittest
from datetime import date
from pathlib import Path

from selenium.webdriver.common.by import By

from nucleo import config


def carregar(texto="", exigir_login=False, ambiente=None):
    pasta = Path(tempfile.mkdtemp())
    env = pasta / ".env"
    env.write_text(texto, encoding="utf-8")
    return config.carregar(env, exigir_login=exigir_login, ambiente=ambiente or {})


class TestCarregar(unittest.TestCase):
    def test_padroes_sem_arquivo(self):
        cfg = config.carregar(Path(tempfile.mkdtemp()) / "nao-existe.env", exigir_login=False, ambiente={})
        self.assertEqual(cfg.vios_base, "https://roneely.vios.com.br/")
        self.assertEqual(cfg.campo_usuario, (By.CSS_SELECTOR, "input[name='form[usuario]']"))
        self.assertIsNone(cfg.botao_login)
        self.assertIsNone(cfg.login_sucesso)
        self.assertTrue(cfg.headless)
        self.assertEqual(cfg.timeout, 20)
        self.assertEqual(cfg.funcoes_padrao, ["agenda", "prazos", "intimacoes", "planilhas"])
        self.assertIn("act=del", cfg.urls_proibidas)
        self.assertIn("SALVAR", cfg.cliques_proibidos)
        self.assertEqual(cfg.vila_url, "")
        self.assertEqual(cfg.pasta_saida, config.PASTA_ORELHA / "saida")

    def test_exige_login(self):
        with self.assertRaises(config.ConfigErro) as c:
            carregar("SISTEMA_USUARIO=fulano\n", exigir_login=True)
        self.assertIn("SISTEMA_SENHA", str(c.exception))
        cfg = carregar("SISTEMA_USUARIO=fulano\nSISTEMA_SENHA= segredo \n", exigir_login=True)
        self.assertEqual(cfg.usuario, "fulano")

    def test_senha_fora_do_repr(self):
        cfg = carregar("SISTEMA_USUARIO=fulano\nSISTEMA_SENHA=segredo123\nVILA_SENHA=outra456\n")
        self.assertNotIn("segredo123", repr(cfg))
        self.assertNotIn("outra456", repr(cfg))

    def test_arquivo_vence_ambiente(self):
        cfg = carregar("TIMEOUT=7\n", ambiente={"TIMEOUT": "99", "HEADLESS": "false"})
        self.assertEqual(cfg.timeout, 7)
        self.assertFalse(cfg.headless)

    def test_vila_url_ganha_eventos(self):
        self.assertEqual(carregar("VILA_URL=http://10.0.0.1:5001\n").vila_url, "http://10.0.0.1:5001/eventos")
        self.assertEqual(carregar("VILA_URL=http://10.0.0.1:5001/eventos/\n").vila_url, "http://10.0.0.1:5001/eventos")

    def test_base_derivada_e_sobrescrita(self):
        self.assertEqual(carregar("SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?x=1\n").vios_base,
                         "https://exemplo.vios.com.br/")
        self.assertEqual(carregar("ORELHA_VIOS_BASE=https://outro.exemplo/\n").vios_base, "https://outro.exemplo/")
        with self.assertRaises(config.ConfigErro):
            carregar("SISTEMA_URL=exemplo.vios.com.br\n")

    def test_seletor_invalido(self):
        with self.assertRaises(config.ConfigErro) as c:
            carregar("LOGIN_CAMPO_USUARIO=#usuario\n")
        self.assertIn("LOGIN_CAMPO_USUARIO", str(c.exception))

    def test_caminhos_relativos_a_orelha(self):
        cfg = carregar("ORELHA_SAIDA=outra_saida\nORELHA_ALBI_SAIDA=/tmp/albi\n")
        self.assertEqual(cfg.pasta_saida, (config.PASTA_ORELHA / "outra_saida").resolve())
        self.assertEqual(cfg.albi_saida, Path("/tmp/albi"))


class TestEnvExample(unittest.TestCase):
    def test_env_example_carrega(self):
        cfg = config.carregar(config.PASTA_ORELHA / ".env.example", exigir_login=False, ambiente={})
        self.assertEqual(cfg.vios_url, config.PADROES["SISTEMA_URL"])
        self.assertEqual(cfg.vila_usuario, "orelha")
        self.assertEqual(cfg.vila_url, "")
        self.assertIn("int-lanca.php", cfg.urls_proibidas)
        self.assertIn("MARCAR COMO LIDO", cfg.cliques_proibidos)


class TestValor(unittest.TestCase):
    def setUp(self):
        self.cfg = carregar(
            "ORELHA_N=15\nORELHA_F=2,5\nORELHA_B=sim\nORELHA_B2=Não\nORELHA_VAZIO=\nORELHA_LISTA= a, b ,,c\n"
            "ORELHA_SEL=xpath://a[@id='x']\nORELHA_SELS=css:#a|xpath://b\nORELHA_DATA=04/11/2026\n"
            "ORELHA_RUIM=abc\nORELHA_TEXTO=  oi  \n")

    def test_tipos(self):
        v = self.cfg.valor
        self.assertEqual(v("ORELHA_N", 1, int), 15)
        self.assertEqual(v("ORELHA_F", 0.0, float), 2.5)
        self.assertIs(v("ORELHA_B", False, bool), True)
        self.assertIs(v("ORELHA_B2", True, bool), False)
        self.assertEqual(v("ORELHA_LISTA", "", "lista"), ["a", "b", "c"])
        self.assertEqual(v("ORELHA_SEL", None, "seletor"), (By.XPATH, "//a[@id='x']"))
        self.assertEqual(v("ORELHA_SELS", "", "seletores"), [(By.CSS_SELECTOR, "#a"), (By.XPATH, "//b")])
        self.assertEqual(v("ORELHA_DATA", None, "data"), date(2026, 11, 4))
        self.assertEqual(v("ORELHA_TEXTO"), "oi")
        self.assertEqual(v("ORELHA_N", 0, lambda t: int(t) * 2), 30)

    def test_padroes(self):
        v = self.cfg.valor
        self.assertEqual(v("ORELHA_VAZIO", 15, int), 15)
        self.assertEqual(v("ORELHA_NAO_EXISTE", "7", int), 7)
        self.assertIsNone(v("ORELHA_NAO_EXISTE"))
        self.assertIsNone(v("ORELHA_NAO_EXISTE", "", "seletor"))
        self.assertEqual(v("ORELHA_NAO_EXISTE", "", "lista"), [])
        self.assertEqual(v("ORELHA_NAO_EXISTE", "css:.x", "seletor"), (By.CSS_SELECTOR, ".x"))
        self.assertEqual(self.cfg.seletor("ORELHA_NAO_EXISTE", "css:.y"), (By.CSS_SELECTOR, ".y"))
        self.assertEqual(v("ORELHA_NAO_EXISTE", "x|y", "lista", sep="|"), ["x", "y"])

    def test_invalido_sem_mostrar_valor(self):
        for tipo in (int, float, bool, "data", "seletor"):
            with self.assertRaises(config.ConfigErro) as c:
                self.cfg.valor("ORELHA_RUIM", None, tipo)
            self.assertIn("ORELHA_RUIM", str(c.exception))
            self.assertNotIn("abc", str(c.exception))

    def test_bruto(self):
        self.assertEqual(self.cfg.bruto("ORELHA_N"), "15")
        self.assertIsNone(self.cfg.bruto("ORELHA_NAO_EXISTE"))


if __name__ == "__main__":
    unittest.main()
