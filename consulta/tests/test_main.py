import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from consulta import __main__ as principal
from consulta import configuracao, fonte as modulo_fonte
from consulta.erros import ConsultaErro, SessaoPerdida
from nucleo import vios
from nucleo.config import ConfigErro


class TestSimulado(unittest.TestCase):
    def test_simulado_uma_vez_sai_com_zero(self):
        self.assertEqual(principal.main(["--simulado", "--uma-vez"]), 0)

    def test_argumentos(self):
        a = principal.argumentos(["--uma-vez", "--simulado", "--env", "x"])
        self.assertTrue(a.uma_vez and a.simulado)
        self.assertEqual(a.env, "x")


class TestConfiguracao(unittest.TestCase):
    def env(self, texto):
        d = tempfile.mkdtemp()
        p = Path(d) / ".env"
        p.write_text(texto, encoding="utf-8")
        return p

    def test_obrigatorias_faltando(self):
        p = self.env("SISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n")
        with self.assertRaises(ConfigErro) as cm:
            configuracao.carregar(p, ambiente={})
        self.assertIn("CONSULTA_BOT_URL", str(cm.exception))
        self.assertNotIn("SENHA=s", str(cm.exception))

    def test_ok_com_padroes(self):
        p = self.env("SISTEMA_USUARIO=u\nSISTEMA_SENHA=s\nCONSULTA_BOT_URL=https://bot.invalid\nCONSULTA_SEGREDO=x\n"
                     "CONSULTA_CHAVE_TELEFONE=k\nCONSULTA_CHAVE_PRIVADA=/tmp/chave.pem\n")
        c = configuracao.carregar(p, ambiente={})
        self.assertEqual((c.bot_url, c.intervalo, c.opcoes.formato_cpf, c.opcoes.exigir_eco_cpf),
                         ("https://bot.invalid", 5.0, "mascara", True))
        self.assertEqual(c.opcoes.chave_telefone, "k")
        self.assertNotIn("CONSULTA_SEGREDO", repr(c))

    def test_valores_invalidos(self):
        base = ("SISTEMA_USUARIO=u\nSISTEMA_SENHA=s\nCONSULTA_BOT_URL=b\nCONSULTA_SEGREDO=x\n"
                "CONSULTA_CHAVE_TELEFONE=k\nCONSULTA_CHAVE_PRIVADA=/tmp/c.pem\n")
        for extra in ("CONSULTA_CPF_FORMATO=outro\n", "CONSULTA_INTERVALO=0\n", "CONSULTA_INTERVALO=abc\n"):
            with self.subTest(extra=extra), self.assertRaises(ConfigErro):
                configuracao.carregar(self.env(base + extra), ambiente={})

    def test_simulado_dispensa_tudo(self):
        c = configuracao.carregar(self.env(""), simulado=True, ambiente={})
        self.assertEqual(c.bot_url, "")


class FakeCfg:
    headless = True
    timeout = 5
    vios_base = "https://exemplo.invalid/"
    urls_proibidas = ["act=del"]
    campo_senha = None

    def valor(self, nome, padrao=None, tipo=str, sep=","):
        return padrao


class TestFonteVios(unittest.TestCase):
    def fonte(self, abrir_sessao):
        return modulo_fonte.FonteVios(FakeCfg(), abrir_sessao=abrir_sessao)

    def test_tela_de_login_vira_sessao_perdida(self):
        f = self.fonte(lambda cfg: SimpleNamespace(driver=object(), cfg=cfg))
        with mock.patch.object(vios, "buscar_get", return_value="<form><input name='form[senha]'></form>"):
            with self.assertRaises(SessaoPerdida):
                f.lista_processos("390.533.447-05")

    def test_busca_normal_e_reaproveita_a_sessao(self):
        abertas = []

        def abrir(cfg):
            abertas.append(1)
            return SimpleNamespace(driver=object(), cfg=cfg)

        f = self.fonte(abrir)
        with mock.patch.object(vios, "buscar_get", return_value="<html>ok</html>") as bg:
            f.lista_processos("390.533.447-05")
            f.form_pessoa("701")
        self.assertEqual(len(abertas), 1)
        urls = [c.args[1] for c in bg.call_args_list]
        self.assertIn("pesq[cpfcnpj]=390.533.447-05", urls[0])
        self.assertTrue(urls[1].endswith("act=edit&clientes_id=701"))
        f.reiniciar()
        with mock.patch.object(vios, "buscar_get", return_value="<html>ok</html>"), \
                mock.patch("consulta.sessao.fechar"):
            f.reiniciar()
            f.lista_pessoas("1")
        self.assertEqual(len(abertas), 2)

    def test_login_que_falha_nao_e_repetido_de_imediato(self):
        chamadas = []

        def abrir(cfg):
            chamadas.append(1)
            raise RuntimeError("senha errada para u1 e CPF 39053344705")

        f = self.fonte(abrir)
        for _ in range(3):
            with self.assertRaises(ConsultaErro) as cm:
                f.lista_processos("390.533.447-05")
            self.assertNotIn("39053344705", str(cm.exception))
        self.assertEqual(len(chamadas), 1)

    def test_bloqueio_inativo_sobe(self):
        def abrir(cfg):
            raise vios.BloqueioInativo("sem bloqueio")

        with self.assertRaises(vios.BloqueioInativo):
            self.fonte(abrir).lista_processos("1")

    def test_endereco_proibido_nunca_e_buscado(self):
        # a mesma trava da Orelha vale para o GET do coletor
        f = self.fonte(lambda cfg: SimpleNamespace(driver=object(), cfg=cfg))
        with self.assertRaises(Exception):
            vios.buscar_get(SimpleNamespace(cfg=FakeCfg(), driver=object()), "?pag=x&act=del&id=1")


if __name__ == "__main__":
    unittest.main()


class TestFecharFonte(unittest.TestCase):
    def test_fecha_o_leitor_antes_do_driver_e_engole_erro(self):
        ordem = []
        f = modulo_fonte.FonteVios(FakeCfg(), abrir_sessao=lambda cfg: SimpleNamespace(driver=object(), cfg=cfg))
        f.ctx = SimpleNamespace(driver=object())

        class Leitor:
            def fechar(self):
                ordem.append("leitor")
                raise ConnectionRefusedError("driver já fechado")

        f.leitor = Leitor()
        with mock.patch("consulta.sessao.fechar", side_effect=lambda ctx: ordem.append("driver")):
            f.fechar()
            f.fechar()   # segunda vez não faz nada nem quebra
        self.assertEqual(ordem, ["leitor", "driver", "driver"])
        self.assertIsNone(f.ctx)
        self.assertIsNone(f.leitor)
