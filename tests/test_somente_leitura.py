"""Testes do modo somente leitura, da classificação das tarefas e do relatório.
Não acessam o VIOS nem abrem navegador: as telas são substituídas por dublês (mock).

DADOS FICTÍCIOS: os títulos de tarefa abaixo foram escritos para o teste e NÃO vêm do
VIOS; o comprovante usado é o mesmo PDF fictício de test_regras.py (texto montado à mão,
não é documento real). Nenhum teste lê comprovante ou processo real.
"""
import csv
import inspect
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import main
from bot import classificacao, comprovante, config, edicao, processo, relatorio
from bot.classificacao import AMBIGUA, IGNORADA, PREVIDENCIARIA
from bot.vios import CNJ

try:
    from test_regras import PDF as PDF_FICTICIO
except ImportError:
    from tests.test_regras import PDF as PDF_FICTICIO

# títulos FICTÍCIOS de tarefa -> classe esperada
TITULOS_FICTICIOS = [
    ("Prazo - PREVIDENCIÁRIO - Aposentadoria por idade", PREVIDENCIARIA),
    ("previdenciario: protocolo inicial", PREVIDENCIARIA),
    ("Previdenciário - aposentadoria do trabalhador rural", PREVIDENCIARIA),
    ("Audiência - revisão de previdência privada", IGNORADA),
    ("Ação contra fundo de previdência complementar", IGNORADA),
    ("PREVIDENCIÁRIO - resgate PGBL", IGNORADA),
    ("Cível: indenização por danos morais", IGNORADA),
    ("Reunião interna", IGNORADA),
    ("Trabalhista - reflexos previdenciários", AMBIGUA),
    ("Previdenciário / Cível - prazo", AMBIGUA),
    ("Previdenciário - acidente de trabalho", AMBIGUA),
    ("INSS - BPC/LOAS - protocolo", AMBIGUA),
    ("Auxílio-doença (INSS)", AMBIGUA),
]

VALORES_FICTICIOS = comprovante.extrair(PDF_FICTICIO)
VAZIO = {"cnj": "", "orgao": "", "valor": ""}


class ClassificacaoTest(unittest.TestCase):
    def test_titulos_ficticios(self):
        for titulo, esperada in TITULOS_FICTICIOS:
            with self.subTest(titulo=titulo):
                classe, motivo = classificacao.classificar(titulo)
                self.assertEqual(classe, esperada, motivo)
                self.assertTrue(motivo)

    def test_termo_do_filtro_vem_do_env(self):
        self.assertEqual(classificacao.classificar("PREV SOCIAL - prazo", "PREV SOCIAL")[0], PREVIDENCIARIA)


class ModoLeituraTest(unittest.TestCase):
    DENTRO, FORA = date(2026, 10, 30), date(2026, 10, 28)

    def test_somente_leitura(self):
        self.assertEqual(main.modo(self.DENTRO, False, False, True), "ler")
        self.assertEqual(main.modo(self.FORA, False, True, True), "ler")
        self.assertIsNone(main.modo(self.FORA, False, False, True))

    def test_somente_leitura_com_confirmar_nunca_grava(self):
        self.assertIsNone(main.modo(self.DENTRO, True, False, True))
        self.assertIsNone(main.modo(self.FORA, True, True, True))


class EdicaoLeituraTest(unittest.TestCase):
    def test_ler_nao_preenche_nem_clica(self):
        driver = mock.Mock(current_url="https://vios.invalido/?pag=editar&processos_id=98765")
        cfg = SimpleNamespace(timeout=1, campos={})
        with mock.patch.object(edicao, "abrir"), mock.patch.object(edicao, "WebDriverWait"), \
                mock.patch.object(edicao, "_campo", side_effect=lambda d, dado, c: dado.chave), \
                mock.patch.object(edicao, "_ler", side_effect=lambda d, chave: {"cnj": "", "orgao": "X", "valor": ""}[chave]), \
                mock.patch.object(edicao, "_preencher", side_effect=AssertionError("preencheu")):
            self.assertEqual(edicao.ler(driver, "url", {"98765"}, cfg), {"cnj": "", "orgao": "X", "valor": ""})
        driver.execute_script.assert_not_called()
        driver.find_elements.assert_not_called()

    def test_ler_recusa_outro_processo(self):
        driver = mock.Mock(current_url="https://vios.invalido/?pag=editar&processos_id=11111")
        with mock.patch.object(edicao, "abrir"), mock.patch.object(edicao, "WebDriverWait"):
            with self.assertRaisesRegex(edicao.EdicaoErro, "não é do processo aberto"):
                edicao.ler(driver, "url", {"98765"}, SimpleNamespace(timeout=1))

    def test_codigo_de_ler_nao_tem_preencher_nem_gravar(self):
        fonte = inspect.getsource(edicao.ler).split('"""')[-1]
        for proibido in ("_preencher", "click", "edicao_gravar", "dispatchEvent", "send_keys", "submit"):
            self.assertNotIn(proibido, fonte)


class ProcessarLeituraTest(unittest.TestCase):
    """processar() em somente leitura com as telas trocadas por dublês."""
    TAREFA = {"texto": "EDITAR OS DADOS DA AÇÃO PROTOCOLADA (PREVIDENCIÁRIO) (fictícia)", "link": "https://vios.invalido/?tarefa=1"}
    PROCESSO = "https://vios.invalido/?pag=ver&processos_id=98765"
    EDICAO = "https://vios.invalido/?pag=editar&processos_id=98765&act=edit"

    def rodar(self, tela_processo, campos_edicao, bloqueado=True, modo="ler"):
        linha = {}
        cfg = SimpleNamespace(timeout=1)
        with mock.patch.object(main, "abrir"), \
                mock.patch.object(main, "envios_bloqueados", return_value=bloqueado), \
                mock.patch.object(processo, "link_processo", return_value=self.PROCESSO), \
                mock.patch.object(processo, "cnj", return_value=set(CNJ.findall(tela_processo))), \
                mock.patch.object(processo, "link_galeria", return_value="https://vios.invalido/?pag=galeria&pxe_id=1"), \
                mock.patch.object(processo, "ir_para_edicao", return_value=self.EDICAO), \
                mock.patch.object(comprovante, "achar", return_value={"texto": "Comprovante de protocolo (FICTÍCIO)", "href": "x"}), \
                mock.patch.object(comprovante, "ler", return_value=PDF_FICTICIO), \
                mock.patch.object(edicao, "ler", return_value=campos_edicao) as ler, \
                mock.patch.object(edicao, "editar", side_effect=AssertionError("editar chamado")):
            try:
                feito = main.processar(mock.Mock(current_url="u"), cfg, self.TAREFA, modo, linha)
            except Exception as e:
                return None, linha, e, ler
        return feito, linha, None, ler

    def test_le_e_diz_o_que_faria(self):
        feito, linha, erro, _ = self.rodar("Processo 0001234-56.2026.4.05.8100", VAZIO)
        self.assertIsNone(erro)
        self.assertEqual(feito["situacao"], "leitura")
        self.assertEqual(linha["cnj_pdf"], "0001234-56.2026.4.05.8100")
        self.assertEqual(linha["processo_id"], "98765")
        self.assertIn("N.° CNJ", linha["preencheria"])
        self.assertNotIn("ressalvas", linha)

    def test_processo_sem_cnj_vira_ressalva(self):
        _, linha, erro, _ = self.rodar("", VAZIO)
        self.assertIsNone(erro)
        self.assertIn("sem CNJ", linha["ressalvas"])

    def test_cnj_de_outro_processo_bloqueia(self):
        _, linha, erro, ler = self.rodar("Processo 0009999-11.2025.4.05.8100", VAZIO)
        self.assertIsInstance(erro, comprovante.ComprovanteErro)
        self.assertEqual(linha["cnj_pdf"], "0001234-56.2026.4.05.8100")  # o relatório mostra até onde chegou
        ler.assert_not_called()

    def test_campo_com_outro_valor_e_conflito(self):
        _, linha, erro, _ = self.rodar("", dict(VAZIO, valor="20.000,00"))
        self.assertIsInstance(erro, edicao.EdicaoErro)
        self.assertEqual(linha["valor_edicao"], "20.000,00")

    def test_ja_estava(self):
        feito, _, erro, _ = self.rodar("", dict(VALORES_FICTICIOS))
        self.assertIsNone(erro)
        self.assertEqual(feito["situacao"], "ja_estava")

    def test_sem_bloqueio_de_envios_para_tudo(self):
        _, _, erro, ler = self.rodar("", VAZIO, bloqueado=False)
        self.assertIsInstance(erro, main.LeituraErro)
        ler.assert_not_called()

    def test_simulacao_tambem_exige_bloqueio(self):
        _, _, erro, _ = self.rodar("", VAZIO, bloqueado=False, modo="simular")
        self.assertIsInstance(erro, main.LeituraErro)

    def test_valor_zerado_no_vios_e_preenchido(self):
        feito, linha, erro, _ = self.rodar("", dict(VAZIO, valor="0,00"))
        self.assertIsNone(erro)
        self.assertEqual(feito["situacao"], "leitura")
        self.assertIn("Valor da ação", linha["preencheria"])


class TipoDeTarefaTest(unittest.TestCase):
    TIPO = "EDITAR OS DADOS DA ACAO PROTOCOLADA"

    def test_so_a_tarefa_de_edicao_e_processada(self):
        self.assertEqual(classificacao.classificar("EDITAR OS DADOS DA AÇÃO PROTOCOLADA (PREVIDENCIÁRIO) 2026",
                                                   "PREVIDENCI", self.TIPO)[0], PREVIDENCIARIA)
        classe, motivo = classificacao.classificar("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026", "PREVIDENCI", self.TIPO)
        self.assertEqual(classe, IGNORADA)
        self.assertIn("não é tarefa", motivo)

    def test_tipo_nao_libera_outra_area(self):
        self.assertEqual(classificacao.classificar("EDITAR OS DADOS DA AÇÃO PROTOCOLADA (CÍVEL) 2026",
                                                   "PREVIDENCI", self.TIPO)[0], IGNORADA)


class GaleriaTest(unittest.TestCase):
    def test_nome_do_comprovante(self):
        regex = config.PADROES["COMPROVANTE_TEXTO"]
        for nome in ("Comprovante_de_Protcolo_-__0001234-56.2026.4.05.8100.pdf", "Comprovante de protocolo.pdf"):
            self.assertRegex(nome.lower(), regex)
        self.assertNotRegex("Procuração.pdf".lower(), regex)

    def _linha(self, tipo, hrefs, apagado=False):
        tr = mock.Mock()
        tr.find_elements.return_value = [mock.Mock(**{"get_attribute.return_value": h}) for h in hrefs]
        tr.dados = {"tipo": tipo, "apagado": apagado}
        return tr

    def _galeria(self, linhas):
        driver = mock.Mock()
        driver.find_elements.return_value = linhas
        driver.execute_script.side_effect = lambda js, tr: tr.dados
        cfg = SimpleNamespace(timeout=1, protocolo_linhas=("css selector", "tr"), protocolo_arquivos=("css selector", "a"),
                              protocolo_tarefa="PROTOCOLAR INICIAL (PREVIDENCIARIO)")
        return processo.link_galeria(driver, cfg)

    def test_uma_tarefa_de_protocolo(self):
        linhas = [self._linha("MINUTAR INICIAL (PREVIDENCIÁRIO) 2026", ["m"]),
                  self._linha("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026", ["g", "g"]),  # botão repetido na linha
                  self._linha("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026", ["x"], apagado=True)]
        self.assertEqual(self._galeria(linhas), "g")

    def test_duas_tarefas_de_protocolo_bloqueia(self):
        linhas = [self._linha("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026", ["g1"]),
                  self._linha("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026", ["g2"])]
        with self.assertRaisesRegex(processo.ProcessoErro, "achei 2"):
            self._galeria(linhas)


class RelatorioTest(unittest.TestCase):
    def test_escreve_e_nunca_sobrescreve(self):
        quando = datetime(2026, 10, 28, 12, 0, 0)
        linhas = [{"modo": "ler", "tarefa": "=HYPERLINK(\"x\") (fictícia)", "decisao": "ambigua", "motivo": "teste"},
                  {"modo": "ler", "tarefa": "Prazo - PREVIDENCIÁRIO (fictícia)", "decisao": "leitura",
                   "cnj_pdf": VALORES_FICTICIOS["cnj"], "valor_pdf": VALORES_FICTICIOS["valor"]}]
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = relatorio.escrever(Path(pasta), linhas, quando)
            with open(arquivo, encoding="utf-8-sig", newline="") as f:
                tabela = list(csv.reader(f, delimiter=";"))
            self.assertEqual(tabela[0], [titulo for _, titulo in relatorio.COLUNAS])
            self.assertTrue(tabela[1][1].startswith("'="))
            self.assertIn("0001234-56.2026.4.05.8100", tabela[2])
            with self.assertRaises(FileExistsError):
                relatorio.escrever(Path(pasta), linhas, quando)


if __name__ == "__main__":
    unittest.main()
