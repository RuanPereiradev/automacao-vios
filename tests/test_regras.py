"""Testes das regras que não dependem do VIOS: python -m unittest discover tests"""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from types import SimpleNamespace
from unittest import mock

from bot import comprovante, edicao
from bot.edicao import conflitos, igual, vazio
from bot.vios import ids_numericos
from main import _salvar_registro, mesma_tarefa, modo, nos_ultimos_dias

# texto como o pypdf extrai de um comprovante de protocolo do PJe (dados fictícios)
PDF = """Comprovante de Protocolo
Número do processo: 0001234-56.2026.4.05.8100
Órgão julgador: 15ª Vara Federal da SJCE
Última distribuição: 27/10/2026
Valor da causa: R$ 18.540,00
Classe: PROCEDIMENTO DO JUIZADO ESPECIAL CÍVEL
Assuntos: Aposentadoria por Incapacidade Permanente
"""


class JanelaTest(unittest.TestCase):
    def test_tres_ultimos_dias_corridos(self):
        self.assertEqual([d for d in range(1, 32) if nos_ultimos_dias(date(2026, 10, d))], [29, 30, 31])
        self.assertEqual([d for d in range(1, 31) if nos_ultimos_dias(date(2026, 11, d))], [28, 29, 30])
        self.assertEqual([d for d in range(1, 29) if nos_ultimos_dias(date(2027, 2, d))], [26, 27, 28])
        self.assertEqual([d for d in range(1, 30) if nos_ultimos_dias(date(2028, 2, d))], [27, 28, 29])


class ModoTest(unittest.TestCase):
    DENTRO, FORA = date(2026, 10, 30), date(2026, 10, 28)

    def test_simulacao_e_o_padrao(self):
        self.assertEqual(modo(self.DENTRO, False, False), "simular")

    def test_grava_so_com_confirmar_dentro_da_janela(self):
        self.assertEqual(modo(self.DENTRO, True, False), "gravar")
        self.assertIsNone(modo(self.FORA, True, False))

    def test_fora_da_janela_so_simula(self):
        self.assertEqual(modo(self.FORA, False, True), "simular")
        self.assertEqual(modo(self.DENTRO, False, True), "simular")
        self.assertIsNone(modo(self.FORA, False, False))

    def test_fora_da_janela_com_confirmar_nunca_grava(self):
        self.assertIsNone(modo(self.FORA, True, True))
        self.assertIsNone(modo(self.DENTRO, True, True))


class ConflitoTest(unittest.TestCase):
    PDF = {"cnj": "0001234-56.2026.4.05.8100", "orgao": "15ª Vara Federal da SJCE", "valor": "18.540,00"}

    def test_campos_vazios_ou_iguais_nao_conflitam(self):
        self.assertEqual(conflitos({"cnj": "", "orgao": "", "valor": ""}, self.PDF), [])
        self.assertEqual(conflitos({"cnj": "00012345620264058100", "orgao": "15ª VARA FEDERAL DA SJCE",
                                    "valor": "R$ 18.540,00"}, self.PDF), [])

    def test_valor_zerado_conta_como_vazio(self):
        self.assertEqual(conflitos({"cnj": "", "orgao": "", "valor": "0,00"}, self.PDF), [])
        self.assertTrue(vazio(comprovante.DADOS[2], "0,00"))
        self.assertFalse(vazio(comprovante.DADOS[2], "0,01"))
        self.assertFalse(vazio(comprovante.DADOS[0], "0"))  # só no valor

    def test_valor_diferente_bloqueia(self):
        achados = conflitos({"cnj": "", "orgao": "", "valor": "20.000,00"}, self.PDF)
        self.assertEqual(len(achados), 1)
        self.assertIn("Valor da ação", achados[0])


class RegistroTest(unittest.TestCase):
    def test_salva_e_relê(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "registro.json"
            _salvar_registro(arquivo, {"https://x/?id=123": {"situacao": "gravado", "processo_id": ["98765"]}})
            self.assertEqual(json.loads(arquivo.read_text(encoding="utf-8"))["https://x/?id=123"]["processo_id"], ["98765"])
            self.assertFalse(arquivo.with_suffix(".tmp").exists())


class ExtracaoTest(unittest.TestCase):
    def test_tres_dados(self):
        self.assertEqual(comprovante.extrair(PDF), {
            "cnj": "0001234-56.2026.4.05.8100",
            "orgao": "15ª Vara Federal da SJCE",
            "valor": "18.540,00",
        })

    def test_linhas_juntas_no_pdf(self):
        texto = PDF.replace("SJCE\nÚltima", "SJCE Última")
        self.assertEqual(comprovante.extrair(texto)["orgao"], "15ª Vara Federal da SJCE")

    def test_dois_cnj_diferentes_bloqueia(self):
        with self.assertRaisesRegex(comprovante.ComprovanteErro, "mais de um valor"):
            comprovante.extrair(PDF + "Processo referência: 0009999-11.2025.4.05.8100\n")

    def test_dado_faltando_bloqueia(self):
        with self.assertRaisesRegex(comprovante.ComprovanteErro, "Valor da ação: não encontrado"):
            comprovante.extrair(PDF.replace("Valor da causa", "Valor"))


class ConferenciaTest(unittest.TestCase):
    def test_id_do_processo_na_url(self):
        url = "https://roneely.vios.com.br/index.php?pag=sys/processos/ver.php&processos_id=98765&menu_lateral=true"
        self.assertEqual(ids_numericos(url), {"98765"})
        self.assertEqual(ids_numericos("https://roneely.vios.com.br/?pag=x&aba=1"), set())

    def test_filtro_de_uma_tarefa(self):
        alvo = "https://roneely.vios.com.br/?pag=sys/processos/pxe.php&pxe_id=409949&pag_retorno=sys/agenda/calendario.php"
        self.assertTrue(mesma_tarefa("https://roneely.vios.com.br/?pag=sys/processos/pxe.php&pxe_id=409949", alvo))
        self.assertFalse(mesma_tarefa("https://roneely.vios.com.br/?pag=sys/processos/pxe.php&pxe_id=4099490", alvo))
        self.assertFalse(mesma_tarefa("https://roneely.vios.com.br/?pag=x", "https://roneely.vios.com.br/?pag=x"))

    def test_comparacao(self):
        cnj, orgao, valor = comprovante.DADOS
        self.assertTrue(igual(valor, "R$ 18.540,00", "18.540,00"))
        self.assertFalse(igual(valor, "18.540,01", "18.540,00"))
        self.assertTrue(igual(cnj, "00012345620264058100", "0001234-56.2026.4.05.8100"))
        self.assertTrue(igual(orgao, "15ª VARA FEDERAL DA SJCE", "15ª Vara Federal da SJCE"))



class CadastroOrgaoTest(unittest.TestCase):
    CFG = SimpleNamespace(timeout=1, orgao_cadastrar=("css", "+"), orgao_nome=("css", "nome"), orgao_gravar=("css", "gravar"))

    def driver(self, botoes_mais=1):
        caixa = mock.Mock(is_displayed=mock.Mock(return_value=True))
        achados = {"+": [mock.Mock()] * botoes_mais, "nome": [caixa]}
        driver = mock.Mock()
        driver.find_elements.side_effect = lambda _by, sel: (
            achados[sel] if sel in achados else self.fail("procurou o Gravar do cadastro na simulação"))
        return driver

    def test_simulacao_so_escreve_o_nome(self):
        driver = self.driver()
        edicao._cadastrar_orgao(driver, "31ª Vara Federal CE", self.CFG, confirmar=False)
        scripts = [c.args[0] for c in driver.execute_script.call_args_list]
        self.assertEqual(sum("click()" in s for s in scripts), 1)  # só o "+", que abre o modal
        self.assertIn("31ª Vara Federal CE", driver.execute_script.call_args_list[-1].args)

    def test_mais_de_um_botao_de_cadastro_pula(self):
        with self.assertRaisesRegex(edicao.EdicaoErro, "2 botões"):
            edicao._cadastrar_orgao(self.driver(botoes_mais=2), "31ª Vara Federal CE", self.CFG, confirmar=False)



class AvisoDepoisDeGravarTest(unittest.TestCase):
    CFG = SimpleNamespace(timeout=1, edicao_confirmar=r"CLIENTE DO CONTRATO NAO E CATEGORIZADO COMO CLIENTE")

    def rodar(self, texto):
        botao = mock.Mock(is_displayed=mock.Mock(return_value=True))
        aviso = mock.Mock(is_displayed=mock.Mock(side_effect=[True, True, False]),
                          get_attribute=mock.Mock(return_value=texto))
        aviso.find_elements.return_value = [botao]
        gravar = mock.Mock(is_enabled=mock.Mock(return_value=True))
        driver = mock.Mock(find_elements=mock.Mock(return_value=[aviso]))
        with mock.patch.object(edicao.EC, "staleness_of", side_effect=[lambda d: False, lambda d: True]):
            edicao._responder_avisos(driver, gravar, self.CFG)
        return driver

    def test_aviso_de_cliente_recebe_confirmar(self):
        driver = self.rodar("O Cliente do contrato não é categorizado como cliente! Deseja incluir FULANA na categoria cliente?")
        self.assertEqual(sum("click()" in c.args[0] for c in driver.execute_script.call_args_list), 1)

    def test_aviso_desconhecido_nao_recebe_clique(self):
        with self.assertRaisesRegex(edicao.ConferenciaErro, "não responde"):
            self.rodar("Deseja excluir o processo?")


if __name__ == "__main__":
    unittest.main()
