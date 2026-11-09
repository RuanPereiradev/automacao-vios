import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import main
from nucleo import vios
from nucleo.modelos import Item, Secao


def modulo(executar, precisa=True, titulo="Teste"):
    return SimpleNamespace(executar=executar, PRECISA_VIOS=precisa, TITULO=titulo)


class TestMain(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.env = self.pasta / ".env"
        self.env.write_text(f"ORELHA_SAIDA={self.pasta / 'saida'}\nORELHA_LOGS={self.pasta / 'logs'}\n"
                            "VILA_URL=\nSISTEMA_USUARIO=\nSISTEMA_SENHA=\n", encoding="utf-8")

    def rodar(self, *args):
        saida, erro = io.StringIO(), io.StringIO()
        with redirect_stdout(saida), redirect_stderr(erro):
            codigo = main.main(["--env", str(self.env), "--data", "2026-11-04", *args])
        self.log = erro.getvalue()
        return codigo, saida.getvalue()

    def eventos(self, stdout):
        return [json.loads(l[len("@evento "):]) for l in stdout.splitlines() if l.startswith("@evento ")]

    def dia(self, simulado=True):
        # o simulado grava em saida/simulado-<data>/, para não sobrescrever o relatório real do dia
        return self.pasta / "saida" / ("simulado-2026-11-04" if simulado else "2026-11-04")

    def test_simulado_com_esbocos(self):
        codigo, stdout = self.rodar("--simulado", "--sem-pdf", "--eventos",
                                    "--funcoes", "agenda,prazos,intimacoes,parados,planilhas")
        self.assertEqual(codigo, 0, self.log)
        resumo = json.loads((self.dia() / "resumo.json").read_text(encoding="utf-8"))
        self.assertEqual([s["chave"] for s in resumo["secoes"]],
                         ["agenda", "prazos", "intimacoes", "parados", "planilhas"])
        self.assertTrue(resumo["simulado"])
        self.assertTrue((self.dia() / "relatorio.html").exists())
        self.assertFalse((self.dia() / "relatorio.pdf").exists())
        evs = self.eventos(stdout)
        tipos = [e["tipo"] for e in evs]
        self.assertEqual(tipos[0], "execucao_iniciada")
        self.assertEqual(tipos[-1], "execucao_fim")
        self.assertIn({"fase": "gerando_relatorio"}, [{"fase": e.get("fase")} for e in evs if e["tipo"] == "fase"])
        self.assertTrue(all(e["bot"] == "orelha" for e in evs))
        self.assertEqual(evs[-1]["resultado"], "concluido")
        self.assertEqual(set(evs[-1]["contagens"]), {"agenda", "prazos", "intimacoes", "parados", "planilhas"})
        # os mesmos eventos ficam no registro local do dia
        local = (self.dia() / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(local), len(evs))

    def test_padrao_sem_parados_e_sem_stdout(self):
        codigo, stdout = self.rodar("--simulado", "--sem-pdf")
        self.assertEqual(codigo, 0)
        self.assertEqual(stdout, "")
        resumo = json.loads((self.dia() / "resumo.json").read_text(encoding="utf-8"))
        self.assertEqual([s["chave"] for s in resumo["secoes"]], ["agenda", "prazos", "intimacoes", "planilhas"])

    def test_funcao_que_falha_nao_derruba_as_outras(self):
        def quebra(ctx):
            raise RuntimeError("tabela sumiu\ndetalhes do selenium")

        def ok(ctx):
            self.assertTrue(ctx.simulado)
            self.assertIsNone(ctx.driver)
            self.assertEqual(ctx.chave, "prazos")
            self.assertEqual(ctx.saida, self.dia())
            self.assertEqual(ctx.historico, self.pasta / "saida" / "historico")
            ctx.emitir("fase", fase="lendo_calendario")
            return Secao("prazos", "Prazos", "1 grave", [Item("PRAZO", nivel="grave", grupo="Pessoa Fictícia")],
                         {"graves": 1, "por_responsavel": {"Pessoa Fictícia": 1}})

        with mock.patch.dict(main.REGISTRO, {"agenda": modulo(quebra), "prazos": modulo(ok)}):
            codigo, stdout = self.rodar("--simulado", "--sem-pdf", "--eventos", "--funcoes", "agenda,prazos")
        self.assertEqual(codigo, 1)
        resumo = json.loads((self.dia() / "resumo.json").read_text(encoding="utf-8"))
        self.assertEqual(resumo["erros"], ["agenda"])
        self.assertEqual(resumo["secoes"][0]["erro"], "tabela sumiu")
        evs = self.eventos(stdout)
        self.assertIn({"tipo": "achado", "funcao": "prazos", "nivel": "grave", "contagem": 1},
                      [{k: e.get(k) for k in ("tipo", "funcao", "nivel", "contagem")} for e in evs])
        fim = evs[-1]
        self.assertEqual((fim["resultado"], fim["erros"]), ("com_erros", ["agenda"]))
        self.assertEqual(fim["contagens"]["prazos"], {"total": 1, "graves": 1, "atencao": 0})
        self.assertNotIn("Pessoa Fictícia", stdout)  # nome da equipe nunca vai para a vila

    def test_resultado_fora_do_formato(self):
        with mock.patch.dict(main.REGISTRO, {"agenda": modulo(lambda ctx: "texto")}):
            codigo, _ = self.rodar("--simulado", "--sem-pdf", "--funcoes", "agenda")
        self.assertEqual(codigo, 1)

    def test_funcao_desconhecida(self):
        codigo, _ = self.rodar("--simulado", "--funcoes", "agenda,xpto")
        self.assertEqual(codigo, 2)
        self.assertIn("xpto", self.log)

    def test_data_invalida(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main.main(["--env", str(self.env), "--data", "04/11/2026", "--simulado"]), 2)

    def test_sem_senha_fora_do_simulado(self):
        with mock.patch.object(main.navegador, "criar_driver") as criar:
            codigo, _ = self.rodar("--sem-pdf", "--funcoes", "agenda")
        self.assertEqual(codigo, 2)
        criar.assert_not_called()

    def test_sem_vios_nao_abre_navegador(self):
        sec = Secao("planilhas", "P", "Nenhuma planilha nova", [], {})
        with mock.patch.dict(main.REGISTRO, {"planilhas": modulo(lambda ctx: sec, precisa=lambda ctx: False)}), \
                mock.patch.object(main.navegador, "criar_driver") as criar:
            codigo, _ = self.rodar("--sem-pdf", "--funcoes", "planilhas")
        self.assertEqual(codigo, 0)
        criar.assert_not_called()


class TestMainComVios(unittest.TestCase):
    """Fluxo real com o navegador falso: login -> bloqueio -> confere -> funções."""

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.env = self.pasta / ".env"
        self.env.write_text(f"ORELHA_SAIDA={self.pasta / 'saida'}\nORELHA_LOGS={self.pasta / 'logs'}\nVILA_URL=\n"
                            "SISTEMA_USUARIO=usuario.ficticio\nSISTEMA_SENHA=senha-ficticia-123\n", encoding="utf-8")
        self.driver = mock.MagicMock()
        self.driver.current_url = "https://exemplo.vios.com.br/index.php"
        self.chamadas = []

    def rodar(self, bloqueado=True, executar=None, bloquear=None, gerar=None):
        executar = executar or (lambda ctx: self.chamadas.append(("funcao", ctx.driver)) or
                                Secao("agenda", "A", "ok", [], {}))
        bloquear = bloquear or (lambda d, **k: self.chamadas.append(("bloquear", k)))
        extra = [mock.patch.object(main.relatorio, "gerar", side_effect=gerar)] if gerar else []
        erro = io.StringIO()
        with mock.patch.dict(main.REGISTRO, {"agenda": modulo(executar)}), \
                mock.patch.object(main.navegador, "criar_driver", return_value=self.driver), \
                mock.patch.object(main.vios, "entrar",
                                  side_effect=lambda ctx, **k: self.chamadas.append(("entrar", k))), \
                mock.patch.object(main.navegador, "bloquear_envios", side_effect=bloquear), \
                mock.patch.object(main.vios, "_envios_bloqueados", return_value=bloqueado), \
                mock.patch.object(main.vios, "esperar_ajax"), \
                redirect_stderr(erro), redirect_stdout(io.StringIO()):
            for x in extra:
                x.start()
            try:
                codigo = main.main(["--env", str(self.env), "--data", "2026-11-04", "--sem-pdf", "--funcoes", "agenda"])
            finally:
                for x in extra:
                    x.stop()
        self.log = erro.getvalue()
        return codigo

    def eventos(self):
        return [json.loads(l) for l in (self.pasta / "saida" / "2026-11-04" / "eventos.jsonl")
                .read_text(encoding="utf-8").splitlines()]

    def test_ordem_bloqueio_login_funcao(self):
        self.assertEqual(self.rodar(), 0, self.log)
        self.assertEqual([c[0] for c in self.chamadas], ["bloquear", "entrar", "funcao"])
        # o form de login é marcado (o bloqueio já está ligado) e o modo pesquisa recebe as listas
        self.assertEqual(self.chamadas[1][1], {"marcar_formulario": True})
        self.assertIn("int-lanca.php", self.chamadas[0][1]["proibidos"])
        self.assertEqual(self.chamadas[0][1]["permitidos"], [])
        self.assertIs(self.chamadas[-1][1], self.driver)
        self.driver.get.assert_called_once_with("https://exemplo.vios.com.br/index.php")
        self.driver.quit.assert_called_once()
        self.assertNotIn("senha-ficticia-123", self.log)

    def test_bloqueio_depois_do_login_se_pedido(self):
        self.env.write_text(self.env.read_text(encoding="utf-8") + "ORELHA_BLOQUEIO_NO_LOGIN=false\n"
                            "ORELHA_XHR_PERMITIDO=eventos.php\n", encoding="utf-8")
        self.assertEqual(self.rodar(), 0, self.log)
        self.assertEqual([c[0] for c in self.chamadas], ["entrar", "bloquear", "funcao"])
        self.assertEqual(self.chamadas[0][1], {"marcar_formulario": False})
        self.assertEqual(self.chamadas[1][1]["permitidos"], ["eventos.php"])

    def test_bloqueio_que_nao_liga_para_com_relatorio(self):
        def falha(d, **k):
            raise RuntimeError("cdp indisponível")
        self.assertEqual(self.rodar(bloquear=falha), 1)
        self.assertNotIn("funcao", [c[0] for c in self.chamadas])
        resumo = json.loads((self.pasta / "saida" / "2026-11-04" / "resumo.json").read_text(encoding="utf-8"))
        self.assertIn("bloqueio de envios", resumo["secoes"][0]["erro"])
        self.assertEqual((self.eventos()[-1]["resultado"], self.eventos()[-1]["motivo"]), ("parou", "bloqueio_inativo"))
        self.driver.quit.assert_called_once()

    def test_relatorio_que_falha_ainda_fecha_a_execucao(self):
        def falha(*a, **k):
            raise OSError("disco cheio")
        self.assertEqual(self.rodar(gerar=falha), 1)
        fim = self.eventos()[-1]
        self.assertEqual((fim["tipo"], fim["resultado"]), ("execucao_fim", "com_erros"))
        self.assertIn("relatorio", fim["erros"])

    def test_para_se_bloqueio_inativo(self):
        self.assertEqual(self.rodar(bloqueado=False), 1)
        self.assertNotIn("funcao", [c[0] for c in self.chamadas])
        resumo = json.loads((self.pasta / "saida" / "2026-11-04" / "resumo.json").read_text(encoding="utf-8"))
        self.assertIn("bloqueio de envios inativo", resumo["secoes"][0]["erro"])
        self.driver.quit.assert_called_once()

    def test_bloqueio_caindo_no_meio_para_tudo(self):
        def cai(ctx):
            raise vios.BloqueioInativo("bloqueio de envios inativo em X: execução interrompida")
        self.assertEqual(self.rodar(executar=cai), 1)
        evs = self.eventos()
        self.assertEqual((evs[-1]["resultado"], evs[-1]["motivo"]), ("parou", "bloqueio_inativo"))

    def test_login_falhou(self):
        with mock.patch.dict(main.REGISTRO, {"agenda": modulo(lambda ctx: None)}), \
                mock.patch.object(main.navegador, "criar_driver", return_value=self.driver), \
                mock.patch.object(main.vios, "entrar", side_effect=vios.LoginErro("login não confirmado")), \
                mock.patch.object(main.navegador, "bloquear_envios") as bloquear, \
                redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            codigo = main.main(["--env", str(self.env), "--data", "2026-11-04", "--sem-pdf", "--funcoes", "agenda"])
        self.assertEqual(codigo, 1)
        bloquear.assert_called_once()  # ligado antes do login
        fim = self.eventos()[-1]
        self.assertEqual((fim["resultado"], fim["motivo"]), ("parou", "login_falhou"))

    def _login(self, efeitos):
        with mock.patch.dict(main.REGISTRO, {"agenda": modulo(lambda ctx: Secao("agenda", "A", "ok", [], {}))}), \
                mock.patch.object(main.navegador, "criar_driver", return_value=self.driver), \
                mock.patch.object(main.vios, "entrar", side_effect=efeitos) as entrar, \
                mock.patch.object(main.navegador, "bloquear_envios"), \
                mock.patch.object(main.vios, "_envios_bloqueados", return_value=True), \
                mock.patch.object(main.vios, "esperar_ajax"), \
                mock.patch.object(main, "ESPERAS_LOGIN", (0, 0, 0)), \
                redirect_stderr(io.StringIO()) as erro, redirect_stdout(io.StringIO()):
            codigo = main.main(["--env", str(self.env), "--data", "2026-11-04", "--sem-pdf", "--funcoes", "agenda"])
        return codigo, entrar.call_count, erro.getvalue()

    def test_tela_de_login_que_nao_abre_tenta_de_novo(self):
        sem_tela = vios.LoginSemTela("a tela de login não apareceu em 30s; a página era \"\" (about:blank)")
        codigo, vezes, log = self._login([sem_tela, None])
        self.assertEqual((codigo, vezes), (0, 2), log)
        self.assertIn("tentativa 1", log)
        self.driver.save_screenshot.assert_called_once()

    def test_tela_de_login_que_nunca_abre_para_depois_de_3(self):
        codigo, vezes, log = self._login(vios.LoginSemTela("a tela de login não apareceu"))
        self.assertEqual((codigo, vezes), (1, 3))
        resumo = json.loads((self.pasta / "saida" / "2026-11-04" / "resumo.json").read_text(encoding="utf-8"))
        self.assertIn("3 tentativas", resumo["secoes"][0]["erro"])

    def test_senha_errada_nao_repete(self):
        codigo, vezes, _ = self._login(vios.LoginErro("login não confirmado em 30s (usuário/senha errados)"))
        self.assertEqual((codigo, vezes), (1, 1))


if __name__ == "__main__":
    unittest.main()
