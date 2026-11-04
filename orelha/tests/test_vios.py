import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest import mock

from nucleo import vios

TABELA = """
<html><body>
<table id="outra"><tr><td>ignorar</td></tr></table>
<table id="tarefas" class="geratabela">
  <thead><tr><th>Tipo</th><th>Responsável</th><th>Data para conclusão</th><th>Concluída em</th></tr></thead>
  <tbody>
    <tr id="tarefas_linha_1" class="par">
      <td data-id="tarefas_linha_1_tipo">AUDIÊNCIA&nbsp;UNA <br>(TRABALHISTA)</td>
      <td data-id="tarefas_linha_1_resp"><a href="index.php?pag=sys/x&amp;id=123">Pessoa Fictícia</a></td>
      <td data-id="tarefas_linha_1_data">05/11/2026 14:00</td>
      <td data-id="tarefas_linha_1_concl"><span title="Apagada"></span></td>
    </tr>
    <tr id="tarefas_linha_2">
      <td>PERÍCIA</td>
      <td><table><tr><td>aninhada</td></tr></table></td>
      <td>31/02/2026</td><td>01/11/2026</td>
    </tr>
    <tr><td></td></tr>
  </tbody>
</table>
</body></html>
"""


class TestTexto(unittest.TestCase):
    def test_normalizar_limpar(self):
        self.assertEqual(vios.normalizar("  Perícia   médica "), "PERICIA MEDICA")
        self.assertEqual(vios.limpar(" a\xa0 b\n c "), "a b c")
        self.assertEqual(vios.digitos("12.345-6"), "123456")
        self.assertTrue(vios.contem("Audiência de instrução", "AUDIENCIA", "PERICIA"))
        self.assertFalse(vios.contem("Reunião", "AUDIÊNCIA"))

    def test_datas(self):
        self.assertEqual(vios.data_br("prazo 4/11/2026 e 05/11/2026"), date(2026, 11, 4))
        self.assertEqual(vios.datas_br("31/02/2026 01/03/2026"), [date(2026, 3, 1)])
        self.assertIsNone(vios.data_br("sem data"))
        self.assertEqual(vios.hora("às 9h30"), "09:30")
        self.assertEqual(vios.hora("14:00 Audiência"), "14:00")
        self.assertEqual(vios.hora("nada"), "")
        self.assertEqual(vios.data_hora_br("04/11/2026 14:05"), datetime(2026, 11, 4, 14, 5))
        self.assertEqual(vios.data_hora_br("04/11/2026"), datetime(2026, 11, 4))
        self.assertEqual(vios.br(date(2026, 1, 2)), "02/01/2026")
        self.assertEqual(vios.br(None), "")

    def test_ids_cnj_urls(self):
        self.assertEqual(vios.ids_numericos("https://x/?pag=a&processos_id=4567&n=1"), {"4567"})
        self.assertEqual(vios.cnjs("0000001-23.2026.8.06.0001 e 0000001-23.2026.8.06.0001"),
                         ["0000001-23.2026.8.06.0001"])
        cfg = SimpleNamespace(vios_base="https://exemplo.vios.com.br/")
        self.assertEqual(vios.url_absoluta(cfg, "?pag=sys/agenda/calendario.php"),
                         "https://exemplo.vios.com.br/?pag=sys/agenda/calendario.php")
        self.assertEqual(vios.url_absoluta(cfg, "/index.php?pag=x"), "https://exemplo.vios.com.br/index.php?pag=x")
        self.assertEqual(vios.url_absoluta(cfg, "https://a/b"), "https://a/b")
        self.assertEqual(vios.url_proibida("https://x/?pag=int-lanca.php&a=1", ["int-lanca.php"]), "int-lanca.php")
        self.assertEqual(vios.url_proibida("https://x/?ACT=DEL", ["act=del"]), "act=del")
        self.assertEqual(vios.url_proibida("https://x/?pag=lista", ["act=del"]), "")
        self.assertEqual(vios.clique_proibido("Marcar como lido", ["MARCAR COMO LIDO"]), "MARCAR COMO LIDO")
        self.assertEqual(vios.clique_proibido("Pesquisar", ["SALVAR"]), "")


class TestTabela(unittest.TestCase):
    def test_por_id(self):
        t = vios.ler_tabela_html(TABELA, id_tabela="tarefas")
        self.assertEqual(t.colunas, ["Tipo", "Responsável", "Data para conclusão", "Concluída em"])
        self.assertEqual(len(t), 2)
        a, b = t.linhas
        self.assertEqual(a.celulas[0], "AUDIÊNCIA UNA (TRABALHISTA)")
        self.assertEqual(a.get("responsavel"), "Pessoa Fictícia")
        self.assertEqual(a.get("Data para"), "05/11/2026 14:00")
        self.assertEqual(a.get("tipo"), "AUDIÊNCIA UNA (TRABALHISTA)")
        self.assertEqual(a.get("concl"), "")
        self.assertEqual(a.id, "tarefas_linha_1")
        self.assertEqual(a.classes, "par")
        self.assertIn("Apagada", a.titulos)
        self.assertEqual(a.links, [{"texto": "Pessoa Fictícia", "href": "index.php?pag=sys/x&id=123"}])
        self.assertEqual(a.links_celula[1], ["index.php?pag=sys/x&id=123"])
        self.assertEqual(b.celulas, ["PERÍCIA", "aninhada", "31/02/2026", "01/11/2026"])
        self.assertEqual(b.get("Concluída em"), "01/11/2026")
        self.assertEqual(b.get("nao existe", "-"), "-")

    def test_por_indice_e_sem_cabecalho(self):
        self.assertEqual(vios.ler_tabela_html(TABELA).linhas[0].celulas, ["ignorar"])
        self.assertEqual(len(vios.ler_tabela_html(TABELA, indice=1)), 2)
        t = vios.ler_tabela_html(TABELA, id_tabela="tarefas", cabecalho=False)
        self.assertEqual(t.colunas, [])
        self.assertEqual(len(t), 3)
        self.assertEqual(len(vios.ler_tabela_html("<p>sem tabela</p>")), 0)

    def test_cabecalho_th_sem_thead(self):
        t = vios.ler_tabela_html("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>")
        self.assertEqual(t.colunas, ["A", "B"])
        self.assertEqual(t.linhas[0].get("b"), "2")


class TestLeituraComDriverFalso(unittest.TestCase):
    def ctx(self, bloqueado=True):
        cfg = SimpleNamespace(vios_base="https://exemplo.vios.com.br/", timeout=1,
                              urls_proibidas=["act=del", "int-lanca.php"], cliques_proibidos=["SALVAR"])
        driver = mock.MagicMock()
        driver.current_url = "https://exemplo.vios.com.br/x"
        driver.execute_script.side_effect = lambda js, *a: bloqueado if "__somenteLeitura" in js else True
        return SimpleNamespace(cfg=cfg, driver=driver)

    def test_abrir_recusa_url_proibida(self):
        ctx = self.ctx()
        with self.assertRaises(vios.AcessoProibido):
            vios.abrir(ctx, "?pag=sys/publicacoes/int-lanca.php&id=1")
        ctx.driver.get.assert_not_called()

    def test_abrir_exige_bloqueio(self):
        ctx = self.ctx(bloqueado=False)
        with self.assertRaises(vios.BloqueioInativo):
            vios.abrir(ctx, "?pag=sys/agenda/calendario.php")
        ctx.driver.get.assert_called_once_with("https://exemplo.vios.com.br/?pag=sys/agenda/calendario.php")
        self.assertEqual(vios.abrir(self.ctx(), "?pag=a"), "https://exemplo.vios.com.br/?pag=a")

    def test_clicar_recusa_salvar(self):
        ctx = self.ctx()
        ctx.driver.execute_script.side_effect = lambda js, *a: ["Salvar tarefa", ""] if "closest" in js else None
        elemento = mock.MagicMock()
        with self.assertRaises(vios.AcessoProibido):
            vios.clicar(ctx, elemento)
        ctx.driver.execute_script.side_effect = lambda js, *a: ["Pesquisar", ""] if "closest" in js else None
        vios.clicar(ctx, elemento)
        self.assertEqual(ctx.driver.execute_script.call_args[0][0], "arguments[0].click();")


class TestFormularioDePesquisa(unittest.TestCase):
    """conferir_formulario: só envia formulário de pesquisa de tela conhecida."""

    def cfg(self, extra=""):
        valores = {"ORELHA_PESQUISA_PERMITIDA": extra}
        return SimpleNamespace(urls_proibidas=["act=del", "int-lanca.php"], cliques_proibidos=["SALVAR", "CONCLUIR"],
                               valor=lambda nome, padrao=None, tipo=str: [t for t in valores.get(nome, "").split(",") if t])

    def test_aceita_tela_de_pesquisa(self):
        base = "https://exemplo.vios.com.br/index.php?pag=sys/"
        vios.conferir_formulario(base + "publicacoes/int-pesquisa.php", "", "Pesquisar", self.cfg())
        # action sem "pag=" (ex.: index.php) com o campo oculto pag de uma tela de pesquisa
        vios.conferir_formulario("https://exemplo.vios.com.br/index.php", "", "Pesquisar", self.cfg(),
                                 pag_oculto="sys/agenda/calendario.php")

    def test_recusa(self):
        base = "https://exemplo.vios.com.br/index.php?pag=sys/"
        casos = [(base + "publicacoes/int-lanca.php", base + "publicacoes/int-pesquisa.php", "Pesquisar"),
                 (base + "agenda/calendario.php", base + "agenda/calendario.php", "Concluir tarefa"),
                 (base + "tarefas/editar.php", base + "tarefas/editar.php", "Filtrar"),
                 # estar numa tela de pesquisa não basta: o destino do envio é que conta
                 (base + "busca/qualquer.php", base + "processos/processos-lista.php&menu_lateral=true", "Ok"),
                 (base + "agenda/salvar.php", base + "agenda/calendario.php", "")]
        for acao, pagina, botao in casos:
            with self.subTest(botao=botao):
                with self.assertRaises(vios.AcessoProibido):
                    vios.conferir_formulario(acao, pagina, botao, self.cfg())
        # tela nova só depois de entrar em ORELHA_PESQUISA_PERMITIDA
        vios.conferir_formulario(base + "tarefas/editar.php", "", "Filtrar", self.cfg("tarefas/editar.php"))
        # campo oculto pag que leva a outra tela também é recusado
        with self.assertRaises(vios.AcessoProibido):
            vios.conferir_formulario("https://exemplo.vios.com.br/index.php", "", "", self.cfg(),
                                     pag_oculto="sys/agenda/salvar.php")

    def test_enviar_pesquisa_nao_envia_form_recusado(self):
        ctx = SimpleNamespace(cfg=self.cfg(), driver=mock.MagicMock())
        ctx.driver.execute_script.return_value = {"acao": "https://exemplo.vios.com.br/?pag=sys/x/gravar.php",
                                                  "pagina": "https://exemplo.vios.com.br/?pag=sys/x/gravar.php",
                                                  "botao": "Pesquisar"}
        with mock.patch.object(vios, "esperar", return_value=object()):
            with self.assertRaises(vios.AcessoProibido):
                vios.enviar_pesquisa(ctx, ("css selector", "input"), {"a": "1"})
        self.assertEqual(ctx.driver.execute_script.call_count, 1)  # o JS que preenche e envia não rodou


if __name__ == "__main__":
    unittest.main()
