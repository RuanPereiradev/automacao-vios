"""Testes do relatorio_processos.py com driver falso (sem Selenium real e sem VIOS)."""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import relatorio_processos as rp

URL_LOGIN = "https://vios.exemplo/entrar.php?"
URL_LISTA = "https://vios.exemplo/?pag=sys/processos/processos-lista.php"
CAMPO_USUARIO = ("css selector", "input[name='form[usuario]']")
CAMPO_SENHA = ("css selector", "input[name='form[senha]']")

ITENS = [{"cliente": "EMPRESA FICTICIA", "ci": "1", "parte_ativa": [], "parte_passiva": []}]


def ficha_ok(ci):
    return {"ok": True, "erro": "", "campos": {"Cidade / UF": "Cidade Ficticia / CE"},
            "cidade_uf": "Cidade Ficticia / CE", "fase": "Conhecimento", "data_distribuicao": "",
            "valor_acao": "", "justica": "", "sistema": "", "tarefas": [], "comentarios": [], "arquivos": []}


class DriverFalso:
    """Imita o pouco do Selenium que o relatório usa."""

    def __init__(self):
        self.current_url = URL_LISTA
        self.campos_login = False
        self.prints = []

    def cair_sessao(self, pela_url=True):
        if pela_url:
            self.current_url = URL_LOGIN
        else:
            self.campos_login = True

    def voltar_logado(self):
        self.current_url = URL_LISTA
        self.campos_login = False

    def find_elements(self, by, valor):
        if self.campos_login and (by, valor) in (CAMPO_USUARIO, CAMPO_SENHA):
            return [object()]
        return []

    def save_screenshot(self, caminho):
        self.prints.append(caminho)
        return True

    def quit(self):
        pass


def cfg_falso(pasta_saida):
    return SimpleNamespace(
        campo_usuario=CAMPO_USUARIO,
        campo_senha=CAMPO_SENHA,
        timeout=1,
        pasta_saida=Path(pasta_saida),
        headless=True,
        manter_aberto=False,
    )


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="relatorio teste ")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = cfg_falso(os.path.join(self.tmp, "saida_usuario2"))
        self.driver = DriverFalso()
        self.pasta = Path(self.tmp) / "2026-11-03"
        self.pasta.mkdir()
        # fazer_login falso: volta para a tela logada
        self.login = self._patch("fazer_login", side_effect=lambda d, c: d.voltar_logado())
        self.ir_ate_tabela = self._patch("ir_ate_tabela")
        self.pesquisar = self._patch("pesquisar_grupo")
        self.ler = self._patch("ler_processos", return_value=(list(ITENS), 0))
        # ficha falsa (o módulo real abre o navegador)
        self.ficha = self._patch("ler_ficha", side_effect=lambda d, ci, t: ficha_ok(ci))
        self._patch("ficha_indisponivel", return_value="")

    def _patch(self, nome, **kw):
        p = mock.patch.object(rp, nome, **kw)
        m = p.start()
        self.addCleanup(p.stop)
        return m


class TestTelaDeLogin(Base):
    def test_logado(self):
        self.assertFalse(rp.na_tela_de_login(self.driver, self.cfg))

    def test_url_entrar_php(self):
        self.driver.cair_sessao(pela_url=True)
        self.assertTrue(rp.na_tela_de_login(self.driver, self.cfg))

    def test_campos_de_login_na_tela(self):
        self.driver.cair_sessao(pela_url=False)
        self.assertTrue(rp.na_tela_de_login(self.driver, self.cfg))

    def test_navegador_quebrado_nao_e_login(self):
        driver = mock.Mock()
        type(driver).current_url = mock.PropertyMock(side_effect=RuntimeError("morto"))
        self.assertFalse(rp.na_tela_de_login(driver, self.cfg))


class TestNovoLogin(Base):
    def test_sessao_caiu_antes_do_grupo(self):
        self.driver.cair_sessao()
        with self.assertLogs("relatorio", "WARNING") as logs:
            arquivo = rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(self.login.call_count, 1)
        self.assertEqual(self.ir_ate_tabela.call_count, 1)
        self.assertEqual(self.pesquisar.call_count, 1)
        self.assertTrue(arquivo.exists())
        self.assertIn("login de novo", "\n".join(logs.output))

    def test_falha_com_tela_de_login_faz_novo_login_e_tenta_de_novo(self):
        def pesquisar(driver, valor, timeout, **kw):
            if self.pesquisar.call_count == 1:
                driver.cair_sessao()
                raise TimeoutError("filtro não apareceu")

        self.pesquisar.side_effect = pesquisar
        with self.assertLogs("relatorio", "WARNING") as logs:
            arquivo = rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(self.login.call_count, 1)
        self.assertEqual(self.pesquisar.call_count, 2)
        self.assertTrue(arquivo.exists())
        self.assertIn("nova tentativa", "\n".join(logs.output))

    def test_lista_vazia_por_sessao_caida_tenta_de_novo(self):
        def ler(driver, timeout):
            if self.ler.call_count == 1:
                driver.cair_sessao(pela_url=False)
                return [], 0
            return list(ITENS), 0

        self.ler.side_effect = ler
        with self.assertLogs("relatorio", "WARNING"):
            arquivo = rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(self.login.call_count, 1)
        self.assertIn("EMPRESA FICTICIA", arquivo.read_text(encoding="utf-8"))

    def test_no_maximo_uma_nova_tentativa(self):
        def pesquisar(driver, valor, timeout, **kw):
            driver.cair_sessao()
            raise TimeoutError("sessão caiu de novo")

        self.pesquisar.side_effect = pesquisar
        with self.assertLogs("relatorio", "WARNING"):
            with self.assertRaises(TimeoutError):
                rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(self.pesquisar.call_count, 2)
        self.assertEqual(self.login.call_count, 1)
        self.assertFalse((self.pasta / "3A FRIOS.txt").exists())

    def test_falha_sem_tela_de_login_nao_tenta_de_novo(self):
        self.pesquisar.side_effect = RuntimeError("botão Pesquisar não encontrado")
        with self.assertRaises(RuntimeError):
            rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(self.pesquisar.call_count, 1)
        self.login.assert_not_called()


CHAVES_CONTRATO = {
    "grupo", "ci", "numero", "parte_ativa", "parte_passiva", "cliente", "polo_cliente", "area",
    "tipo_processo", "acao", "orgao", "uf", "vara", "tipo_vara", "data_acao", "valor_acao", "objeto",
    "obs_proc", "posicao", "situacao", "ficha",
}


def item(ci, cliente="EMPRESA FICTICIA", polo="Parte Passiva"):
    return {"ci": ci, "cliente": cliente, "polo_cliente": polo, "numero": f"CNJ: 000000{ci}-00.2026.8.06.0001",
            "parte_ativa": ["Autor: FULANO FICTICIO"], "parte_passiva": ["Réu: " + cliente],
            "data_acao": "01/02/2026", "valor_acao": "1.000,00", "obs_proc": "OBS SECRETA FICTICIA"}


class TestFichas(Base):
    def setUp(self):
        super().setUp()
        self.ler.side_effect = lambda d, t: ([item("1"), item("2"), item("3")], 0)

    def _json(self, grupo="3A FRIOS"):
        return json.loads((self.pasta / (grupo + ".json")).read_text(encoding="utf-8"))

    def test_ficha_com_erro_nao_para_o_grupo(self):
        def ficha(driver, ci, timeout):
            if ci == "2":
                raise TimeoutError("ficha não carregou")
            if ci == "3":
                return {"ok": False, "erro": "bloco de dados não apareceu"}
            return ficha_ok(ci)

        self.ficha.side_effect = ficha
        with self.assertLogs("relatorio", "INFO") as logs:
            arquivo = rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        saida = "\n".join(logs.output)
        self.assertTrue(arquivo.exists())
        fichas = {r["ci"]: r["ficha"] for r in self._json()}
        self.assertTrue(fichas["1"]["ok"])
        self.assertEqual(fichas["2"], {"ok": False, "erro": "ficha não carregou"})
        self.assertEqual(fichas["3"]["erro"], "bloco de dados não apareceu")
        self.assertIn("ficha 2 de 3 (CI 2)", saida)
        self.assertIn("ficha do CI 2 não lida", saida)
        self.assertIn("2 fichas com erro", saida)
        self.login.assert_not_called()

    def test_sessao_cai_na_ficha_faz_login_e_repete_a_ficha(self):
        chamadas = []

        def ficha(driver, ci, timeout):
            chamadas.append(ci)
            if ci == "2" and chamadas.count("2") == 1:
                driver.cair_sessao()
                return {"ok": False, "erro": "timeout"}
            return ficha_ok(ci)

        self.ficha.side_effect = ficha
        with self.assertLogs("relatorio", "WARNING") as logs:
            rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual(chamadas, ["1", "2", "2", "3"])
        self.assertEqual(self.login.call_count, 1)
        self.assertTrue(all(r["ficha"]["ok"] for r in self._json()))
        self.assertIn("caiu na ficha do CI 2", "\n".join(logs.output))

    def test_sessao_que_nao_volta_desiste_do_grupo(self):
        self.ler.side_effect = lambda d, t: ([item(str(n)) for n in range(1, 8)], 0)

        def ficha(driver, ci, timeout):
            driver.cair_sessao()
            return {"ok": False, "erro": "timeout"}

        self.ficha.side_effect = ficha
        with self.assertLogs("relatorio", "WARNING"):
            with self.assertRaises(rp.SessaoCaiu):
                rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        # 3 logins nas fichas + 1 da nova tentativa do grupo + 3 nas fichas de novo
        self.assertEqual(self.login.call_count, 2 * rp.MAX_LOGINS_FICHAS + 1)
        self.assertFalse((self.pasta / "3A FRIOS.txt").exists())

    def test_sem_ficha_nao_abre_ficha(self):
        rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta, rp.Opcoes(ficha=False))
        self.ficha.assert_not_called()
        self.assertTrue(all(r["ficha"] == rp.FICHA_DESLIGADA for r in self._json()))

    def test_json_gravado_no_contrato(self):
        cis = set()
        rp.processar_grupo(self.driver, self.cfg, "AÇO GRANJA", "5", self.pasta, cis=cis)
        self.assertEqual(cis, {"1", "2", "3"})
        texto = (self.pasta / "AÇO GRANJA.json").read_text(encoding="utf-8")
        self.assertIn('"grupo": "AÇO GRANJA"', texto)  # ensure_ascii=False
        self.assertIn('\n  {\n    "grupo"', texto)  # indent=2
        registros = json.loads(texto)
        self.assertEqual(len(registros), 3)
        for r in registros:
            self.assertEqual(set(r), CHAVES_CONTRATO)
            self.assertEqual(r["posicao"], "réu (o cliente está sendo processado)")
            self.assertEqual(r["obs_proc"], "OBS SECRETA FICTICIA")
        self.assertTrue((self.pasta / "AÇO GRANJA.txt").exists())
        self.assertNotIn("OBS SECRETA", (self.pasta / "AÇO GRANJA.txt").read_text(encoding="utf-8"))

    def test_encerrados_vai_para_a_pesquisa_e_para_o_txt(self):
        arquivo = rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta, rp.Opcoes(encerrados=True))
        self.assertEqual(self.pesquisar.call_args.kwargs.get("encerrados"), True)
        self.assertIn("(processos ativos e encerrados)", arquivo.read_text(encoding="utf-8"))

    def test_encerrados_sao_uma_segunda_pesquisa_sem_repetir_ci(self):
        # no VIOS ativos + encerrados combinam com E (0 processos): são duas pesquisas
        listas = {False: [item("1"), item("2")], True: [item("2"), item("3")]}
        self.pesquisar.side_effect = lambda d, v, t, encerrados=False: setattr(self, "fechados", encerrados)
        self.ler.side_effect = lambda d, t: (listas[self.fechados], 0)
        cis = set()
        rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta, rp.Opcoes(encerrados=True), cis=cis)
        self.assertEqual([c.kwargs["encerrados"] for c in self.pesquisar.call_args_list], [False, True])
        registros = json.loads((self.pasta / "3A FRIOS.json").read_text(encoding="utf-8"))
        self.assertEqual({r["ci"]: r["situacao"] for r in registros}, {"1": "ativo", "2": "ativo", "3": "encerrado"})
        self.assertEqual(cis, {"1", "2", "3"})
        txt = (self.pasta / "3A FRIOS.txt").read_text(encoding="utf-8")
        self.assertIn("Por situação:", txt)
        self.assertIn("  Situação: encerrado", txt)

    def test_sem_encerrados_uma_pesquisa_so(self):
        rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta)
        self.assertEqual([c.kwargs["encerrados"] for c in self.pesquisar.call_args_list], [False])
        registros = json.loads((self.pasta / "3A FRIOS.json").read_text(encoding="utf-8"))
        self.assertEqual({r["situacao"] for r in registros}, {"ativo"})
        self.assertNotIn("Por situação:", (self.pasta / "3A FRIOS.txt").read_text(encoding="utf-8"))

    def test_linhas_puladas_vao_para_a_lista(self):
        self.ler.side_effect = lambda d, t: ([item("1"), item("2")], 2)
        puladas = []
        rp.processar_grupo(self.driver, self.cfg, "3A FRIOS", "97", self.pasta, puladas=puladas)
        self.assertEqual(puladas, [2])


class TestPastaRelatorios(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="relatorio teste ")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cfg = cfg_falso(os.path.join(self.tmp, "saida_usuario2"))

    def _env(self, **valores):
        p = mock.patch.dict(os.environ, valores)
        p.start()
        self.addCleanup(p.stop)

    def test_vazio_usa_padrao_e_cria(self):
        self._env(RELATORIO_PASTA="")
        base = rp.pasta_relatorios(self.cfg)
        self.assertEqual(base, self.cfg.pasta_saida / "relatorios")
        self.assertTrue(base.is_dir())

    def test_til_vira_pasta_do_usuario(self):
        drive = Path(self.tmp) / "Google Drive" / "Meu Drive" / "Relatórios VIOS"
        drive.mkdir(parents=True)
        # HOME no Linux/Mac, USERPROFILE no Windows
        self._env(HOME=self.tmp, USERPROFILE=self.tmp,
                  RELATORIO_PASTA="~/Google Drive/Meu Drive/Relatórios VIOS")
        self.assertEqual(rp.pasta_relatorios(self.cfg), drive)

    def test_caminho_absoluto_com_espacos(self):
        drive = Path(self.tmp) / "Meu Drive" / "Clientes VIOS"
        drive.mkdir(parents=True)
        self._env(RELATORIO_PASTA=f'"{drive}"')
        self.assertEqual(rp.pasta_relatorios(self.cfg), drive)

    def test_pasta_inexistente_da_erro_e_nao_cria(self):
        faltando = Path(self.tmp) / "Drive não montado" / "Relatórios"
        self._env(RELATORIO_PASTA=str(faltando))
        with self.assertRaises(rp.PastaErro):
            rp.pasta_relatorios(self.cfg)
        self.assertFalse(faltando.exists())
        self.assertFalse(faltando.parent.exists())


class TestMain(Base):
    def setUp(self):
        super().setUp()
        self.criar_driver = self._patch("criar_driver", return_value=self.driver)
        self._patch("configurar_log")
        self._patch("grupos_disponiveis", return_value={"3A FRIOS": "97", "PÃO MIX": "12", "AÇO GRANJA": "5"})
        p = mock.patch.object(rp.config, "carregar", return_value=self.cfg)
        p.start()
        self.addCleanup(p.stop)
        self.drive = Path(self.tmp) / "Meu Drive"

    def _rodar(self, relatorio_pasta, *args, **env):
        valores = {"RELATORIO_PASTA": relatorio_pasta, "PROCESSOS_FICHA": "", "PROCESSOS_SEM_GRUPO": "",
                   "PROCESSOS_ENCERRADOS": ""}
        valores.update(env)
        with mock.patch.dict(os.environ, valores):
            with self.assertLogs("relatorio", "INFO") as logs:
                codigo = rp.main(".env.teste", *args)
        return codigo, "\n".join(logs.output)

    def test_falha_de_um_grupo_nao_para_os_outros(self):
        self.drive.mkdir()

        def pesquisar(driver, valor, timeout, **kw):
            if valor == "12":
                driver.cair_sessao()
                raise TimeoutError("sessão caiu")

        self.pesquisar.side_effect = pesquisar
        codigo, saida = self._rodar(str(self.drive), "--grupo", "3A FRIOS|pao mix|aco granja")
        self.assertEqual(codigo, 1)
        pastas = list(self.drive.iterdir())
        self.assertEqual(len(pastas), 1)
        nomes = sorted(p.name for p in pastas[0].iterdir())
        self.assertEqual(nomes, ["3A FRIOS.json", "3A FRIOS.txt", "AÇO GRANJA.json", "AÇO GRANJA.txt"])
        # login inicial + 1 nova tentativa do PÃO MIX + login antes do AÇO GRANJA
        # (o PÃO MIX deixou o navegador na tela de login)
        self.assertEqual(self.login.call_count, 3)
        self.assertEqual(self.pesquisar.call_count, 4)
        self.assertIn("Falha no grupo PÃO MIX", saida)
        self.assertIn("2 grupo(s) salvos, 1 com falha", saida)
        self.assertEqual(len(self.driver.prints), 1)

    def test_screenshot_que_falha_nao_para_a_rodada(self):
        self.drive.mkdir()
        self.driver.save_screenshot = mock.Mock(side_effect=RuntimeError("sem janela"))
        def pesquisar(driver, valor, timeout, **kw):
            if valor == "97":
                raise RuntimeError("tabela não carregou")

        self.pesquisar.side_effect = pesquisar
        codigo, saida = self._rodar(str(self.drive), "--grupo", "3A FRIOS|PÃO MIX")
        self.assertEqual(codigo, 1)
        self.assertIn("sem screenshot", saida)
        self.assertIn("1 grupo(s) salvos, 1 com falha", saida)

    def test_sessao_caida_no_meio_da_rodada(self):
        self.drive.mkdir()

        def pesquisar(driver, valor, timeout, **kw):
            if valor == "97":
                driver.cair_sessao()  # cai depois do 1º grupo

        self.pesquisar.side_effect = pesquisar
        codigo, saida = self._rodar(str(self.drive), "--grupo", "todos")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.login.call_count, 2)
        self.assertIn("3 grupo(s) salvos, 0 com falha", saida)

    def test_relatorio_pasta_inexistente_sai_antes_do_vios(self):
        faltando = Path(self.tmp) / "G" / "Meu Drive"
        codigo, saida = self._rodar(str(faltando), "--grupo", "3A FRIOS")
        self.assertEqual(codigo, 1)
        self.assertIn("RELATORIO_PASTA não existe", saida)
        self.criar_driver.assert_not_called()
        self.login.assert_not_called()
        self.assertFalse(faltando.exists())
        self.assertFalse(faltando.parent.exists())

    def test_grupo_sem_nome(self):
        codigo, saida = self._rodar("", "--grupo")
        self.assertEqual(codigo, 1)
        self.assertIn("Falta o nome depois de --grupo", saida)
        self.criar_driver.assert_not_called()

    def test_sem_ficha_pela_linha_de_comando(self):
        self.drive.mkdir()
        indisponivel = self._patch("ficha_indisponivel", return_value="não carregou")
        codigo, _ = self._rodar(str(self.drive), "--grupo", "3A FRIOS", "--sem-ficha")
        self.assertEqual(codigo, 0)
        self.ficha.assert_not_called()
        indisponivel.assert_not_called()

    def test_processos_ficha_false_no_env(self):
        self.drive.mkdir()
        codigo, saida = self._rodar(str(self.drive), "--grupo", "3A FRIOS", PROCESSOS_FICHA="false")
        self.assertEqual(codigo, 0)
        self.ficha.assert_not_called()
        self.assertIn("Fichas: não", saida)

    def test_modulo_da_ficha_faltando_para_antes_do_vios(self):
        self.drive.mkdir()
        self._patch("ficha_indisponivel", return_value="módulo da ficha não carregou")
        codigo, saida = self._rodar(str(self.drive), "--grupo", "3A FRIOS")
        self.assertEqual(codigo, 1)
        self.assertIn("--sem-ficha", saida)
        self.criar_driver.assert_not_called()

    def _por_valor(self):
        """Lista falsa conforme o último grupo pesquisado ("0" = TODOS)."""
        listas = {"97": ["1"], "12": ["2", "3"], "5": [], "0": ["1", "2", "3", "4", "5"]}
        self.ultimo = None

        def pesquisar(driver, valor, timeout, **kw):
            self.ultimo = valor

        self.pesquisar.side_effect = pesquisar
        self.ler.side_effect = lambda d, t: ([item(ci) for ci in listas[self.ultimo]], 0)

    def test_sem_grupo_cliente(self):
        self.drive.mkdir()
        self._por_valor()
        codigo, saida = self._rodar(str(self.drive), "--grupo", "todos", "--sem-grupo")
        self.assertEqual(codigo, 0)
        self.assertIn("4 grupo(s) salvos, 0 com falha", saida)
        valores = [c.args[1] for c in self.pesquisar.call_args_list]
        self.assertEqual(valores[-1], rp.VALOR_TODOS)
        dia = next(self.drive.iterdir())
        registros = json.loads((dia / "SEM GRUPO CLIENTE.json").read_text(encoding="utf-8"))
        self.assertEqual([r["ci"] for r in registros], ["4", "5"])
        self.assertEqual({r["grupo"] for r in registros}, {"SEM GRUPO CLIENTE"})
        self.assertTrue((dia / "SEM GRUPO CLIENTE.txt").exists())
        # fichas só dos processos do grupo extra, não da lista inteira de TODOS
        self.assertEqual(sorted(c.args[1] for c in self.ficha.call_args_list), ["1", "2", "3", "4", "5"])

    def test_sem_grupo_pelo_env(self):
        self.drive.mkdir()
        self._por_valor()
        codigo, _ = self._rodar(str(self.drive), "--grupo", "todos", PROCESSOS_SEM_GRUPO="true")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.pesquisar.call_args_list[-1].args[1], rp.VALOR_TODOS)

    def test_sem_grupo_com_grupos_escolhidos_e_ignorado(self):
        self.drive.mkdir()
        self._por_valor()
        codigo, saida = self._rodar(str(self.drive), "--grupo", "3A FRIOS", "--sem-grupo")
        self.assertEqual(codigo, 0)
        self.assertIn("só é gerado com --grupo todos", saida)
        self.assertNotIn(rp.VALOR_TODOS, [c.args[1] for c in self.pesquisar.call_args_list])

    def test_sem_grupo_nao_gera_se_um_grupo_falhou(self):
        self.drive.mkdir()
        self._por_valor()

        def pesquisar(driver, valor, timeout, **kw):
            self.ultimo = valor
            if valor == "12":
                raise RuntimeError("tabela não carregou")

        self.pesquisar.side_effect = pesquisar
        codigo, saida = self._rodar(str(self.drive), "--grupo", "todos", "--sem-grupo")
        self.assertEqual(codigo, 1)
        self.assertIn("SEM GRUPO CLIENTE não gerado", saida)
        self.assertNotIn(rp.VALOR_TODOS, [c.args[1] for c in self.pesquisar.call_args_list])

    def test_sem_grupo_nao_gera_se_um_grupo_pulou_linha(self):
        self.drive.mkdir()
        self._por_valor()
        ler = self.ler.side_effect

        def ler_com_erro(d, t):
            itens, _ = ler(d, t)
            return itens, (1 if self.ultimo == "12" else 0)

        self.ler.side_effect = ler_com_erro
        codigo, saida = self._rodar(str(self.drive), "--grupo", "todos", "--sem-grupo")
        self.assertEqual(codigo, 1)
        self.assertIn("SEM GRUPO CLIENTE não gerado: 1 linha(s)", saida)
        self.assertNotIn(rp.VALOR_TODOS, [c.args[1] for c in self.pesquisar.call_args_list])
        dia = next(self.drive.iterdir())
        self.assertFalse((dia / "SEM GRUPO CLIENTE.txt").exists())
        self.assertTrue((dia / "PÃO MIX.txt").exists())

    def test_todos_vazio_nao_gera_sem_grupo_vazio(self):
        self.drive.mkdir()
        self._por_valor()
        ler = self.ler.side_effect
        self.ler.side_effect = lambda d, t: ([], 0) if self.ultimo == rp.VALOR_TODOS else ler(d, t)
        codigo, saida = self._rodar(str(self.drive), "--grupo", "todos", "--sem-grupo")
        self.assertEqual(codigo, 1)
        self.assertIn("lista de TODOS veio vazia", saida)
        dia = next(self.drive.iterdir())
        self.assertFalse((dia / "SEM GRUPO CLIENTE.txt").exists())

    def test_encerrados_pela_linha_de_comando_e_env(self):
        self.drive.mkdir()
        self._rodar(str(self.drive), "--grupo", "3A FRIOS", "--encerrados")
        self.assertTrue(self.pesquisar.call_args.kwargs["encerrados"])
        self._rodar(str(self.drive), "--grupo", "3A FRIOS", PROCESSOS_ENCERRADOS="true")
        self.assertTrue(self.pesquisar.call_args.kwargs["encerrados"])
        self._rodar(str(self.drive), "--grupo", "3A FRIOS")
        self.assertFalse(self.pesquisar.call_args.kwargs["encerrados"])


if __name__ == "__main__":
    unittest.main()
