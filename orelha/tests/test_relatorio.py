import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from nucleo import relatorio
from nucleo.modelos import Item, Secao

HOJE = date(2026, 11, 4)


def secoes():
    return [
        Secao("agenda", "Agenda de hoje e amanhã", "2 audiências hoje", [
            Item("AUDIÊNCIA UNA", "14:00 · responsável: Pessoa Fictícia A", "atencao",
                 "https://exemplo.vios.com.br/?pag=x&id=1", "Hoje, 04/11"),
            Item("REUNIÃO <script>alert(1)</script>", "", "info", "javascript:alert(1)", "Amanhã, 05/11"),
        ], {"hoje": 2}),
        Secao("prazos", "Tarefas atrasadas da equipe", "1 grave", [Item("PRAZO X", nivel="grave", grupo="Pessoa B")],
              {"atrasadas": 1, "graves": 1, "por_responsavel": {"Pessoa B": 1}}, avisos=["leitura sem responsável"]),
        Secao("intimacoes", "Intimações sem tarefa", "Não foi possível concluir esta parte.", [], {},
              erro="elemento não apareceu"),
        Secao("planilhas", "Conferência das planilhas do Albi", "Nenhuma planilha nova", [], {}),
    ]


class TestRelatorio(unittest.TestCase):
    def test_grupos_que_abrem_e_quadro(self):
        s = Secao("prazos", "Tarefas atrasadas", "2", [Item("A", "x", "grave", grupo="Ontem"), Item("B", "", "atencao", grupo="Ontem"),
                                                       Item("C", "", "atencao", grupo="Há 3 dias")],
                  {}, recolher=True, quadro={"titulo": "Por responsável", "colunas": ["Responsável", "Atrasadas"],
                                             "linhas": [["Pessoa <A>", 2]]})
        html = relatorio.montar_html([s], HOJE)
        self.assertEqual(html.count('<details class="grupo">'), 3)  # dois grupos e o quadro, todos fechados
        self.assertIn('<span class="g-nome">Ontem</span><span class="g-qtd">2 tarefas</span>', html)
        self.assertIn('<span class="chip grave">1 urgente</span>', html)
        self.assertIn('style="width:100%"', html)
        self.assertIn("<td>Pessoa &lt;A&gt;</td><td class=n>2</td>", html)
        self.assertNotIn("<h3>Ontem</h3>", html)
        self.assertNotIn("<script", html)

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp()) / "2026-11-04"

    def test_gera_html_e_json(self):
        info = relatorio.gerar(secoes(), self.pasta, HOJE, simulado=True, pdf=False,
                               gerado_em=datetime(2026, 11, 4, 7, 30))
        self.assertIsNone(info["pdf"])
        html = info["html"].read_text(encoding="utf-8")
        self.assertIn("Relatório do dia 04/11/2026 (quarta-feira)", html)
        self.assertIn("Modo de demonstração", html)
        self.assertIn("1 parte não foi concluída", html)
        self.assertIn("Esta parte não foi concluída.", html)
        self.assertIn("elemento não apareceu", html)
        self.assertIn("leitura sem responsável", html)
        self.assertIn("Nada a mostrar aqui hoje.", html)
        self.assertIn('href="https://exemplo.vios.com.br/?pag=x&amp;id=1"', html)
        self.assertIn("<h3>Hoje, 04/11</h3>", html)
        self.assertIn('id="prazos"', html)
        # escapado e sem link javascript
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("javascript:", html)
        # autocontido: nada externo
        self.assertNotIn("<script", html)
        self.assertNotIn("<link", html)
        self.assertNotIn("http://", html)

        resumo = json.loads(info["json"].read_text(encoding="utf-8"))
        self.assertEqual(resumo["data"], "2026-11-04")
        self.assertTrue(resumo["simulado"])
        self.assertEqual(resumo["erros"], ["intimacoes"])
        self.assertEqual([s["chave"] for s in resumo["secoes"]], ["agenda", "prazos", "intimacoes", "planilhas"])
        agenda = resumo["secoes"][0]
        self.assertEqual(agenda["total_itens"], 2)
        self.assertEqual(agenda["por_nivel"], {"grave": 0, "atencao": 1, "info": 1})
        self.assertNotIn("itens", agenda)  # o texto dos itens não vai para o resumo

    def test_sem_erro_com_grave(self):
        html = relatorio.montar_html(secoes()[:2], HOJE)
        self.assertIn("1 item urgente hoje", html)
        self.assertNotIn("Modo de demonstração", html)

    def test_nada_urgente(self):
        html = relatorio.montar_html([Secao("planilhas", "P", "Nenhuma planilha nova", [], {})], HOJE)
        self.assertIn("Nada urgente hoje.", html)
        self.assertIn("Tudo em dia", html)

    def test_pdf_falha_fica_html(self):
        with mock.patch.object(relatorio, "escrever_pdf", side_effect=RuntimeError("sem Chrome\nstack")):
            info = relatorio.gerar(secoes(), self.pasta, HOJE, pdf=True)
        self.assertEqual(info["erro_pdf"], "sem Chrome")
        self.assertTrue(info["html"].exists())

    def test_pdf_com_driver(self):
        driver = mock.MagicMock()
        driver.execute_cdp_cmd.return_value = {"data": "JVBERi0="}  # "%PDF-"
        info = relatorio.gerar(secoes(), self.pasta, HOJE, pdf=True, driver=driver)
        self.assertEqual(info["pdf"].read_bytes(), b"%PDF-")
        driver.quit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
