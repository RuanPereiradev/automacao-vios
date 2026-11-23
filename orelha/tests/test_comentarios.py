"""Testes da função "comentarios" (comentários dos últimos N dias de uma lista de processos). Só dados fictícios."""
import csv
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from funcoes import comentarios as c
from nucleo import config, simulado
from nucleo.modelos import Contexto

PASTA = Path(__file__).resolve().parent.parent
FIXTURES = PASTA / "fixtures"
HOJE = date(2026, 11, 23)
BASE = "https://exemplo.vios.com.br/"


def fixture(nome):
    return simulado.substituir((FIXTURES / "comentarios" / nome).read_text(encoding="utf-8"), HOJE)


class TestLista(unittest.TestCase):
    def test_ignora_vazias_comentarios_e_repetidos(self):
        texto = "# cabeçalho\n0000001-11.2026.4.05.8103\n\n  IPL nº 2021.0000001 \n00000011120264058103\n"
        self.assertEqual(c.ler_lista(texto), ["0000001-11.2026.4.05.8103", "IPL nº 2021.0000001"])

    def test_termo_de_busca(self):
        self.assertEqual(c.termo_de_busca("00000011120264058103"), "0000001-11.2026.4.05.8103")
        self.assertEqual(c.termo_de_busca("IPL nº 2021.0000001"), "2021.0000001")


class TestCadastros(unittest.TestCase):
    def setUp(self):
        self.html = fixture("busca.html")

    def test_acha_cnj_no_meio_de_cnj_e_outros(self):
        achados = c.cadastros_do_numero(self.html, "0000001-11.2026.4.05.8103", BASE)
        self.assertEqual([a["ci"] for a in achados], ["920001"])
        self.assertTrue(achados[0]["link"].endswith("processos_id=920001"))

    def test_numero_com_dois_cadastros_le_os_dois(self):
        achados = c.cadastros_do_numero(self.html, "0000002-22.2020.8.06.0001")
        self.assertEqual([a["ci"] for a in achados], ["920002", "920003"])

    def test_numero_em_outros_nao_confunde_com_o_principal(self):
        # 0000003-33.2021.8.06.0000 aparece como "Outros" do CI 920002: também é o mesmo processo
        self.assertEqual([a["ci"] for a in c.cadastros_do_numero(self.html, "0000003-33.2021.8.06.0000")], ["920002"])

    def test_numero_nao_cnj(self):
        self.assertEqual([a["ci"] for a in c.cadastros_do_numero(self.html, "IPL nº 2021.0000001")], ["920004"])

    def test_nao_achado(self):
        self.assertEqual(c.cadastros_do_numero(self.html, "0000009-99.2019.8.06.0001"), [])


class TestQuadro(unittest.TestCase):
    def test_le_data_usuario_e_texto_com_quebras(self):
        lidos = c.comentarios_do_html(fixture("ficha-920001.html"))
        self.assertEqual([x["data_br"] for x in lidos], ["21/11/2026", "24/10/2026", "26/07/2026"])
        self.assertEqual(lidos[0]["hora"], "01:47")
        self.assertEqual(lidos[0]["usuario"], "ANA FICTÍCIA")
        self.assertEqual(lidos[2]["texto"], "Comentário antigo.\nSegundo parágrafo.")
        self.assertNotIn("Editar", " ".join(x["texto"] for x in lidos))

    def test_lista_e_nbsp(self):
        lidos = c.comentarios_do_html(fixture("ficha-920004.html"))
        self.assertEqual(lidos[0]["texto"], "Inquérito relatado.\nPrimeiro\nSegundo")

    def test_tabela_vazia(self):
        self.assertEqual(c.comentarios_do_html(fixture("ficha-920003.html")), [])

    def test_periodo_inclui_as_pontas(self):
        lidos = [{"data": date(2026, 8, 25)}, {"data": date(2026, 8, 24)}, {"data": HOJE}]
        self.assertEqual(c.no_periodo(lidos, HOJE, 90), [{"data": date(2026, 8, 25)}, {"data": HOJE}])


class TestResultado(unittest.TestCase):
    def test_sem_recente_guarda_a_data_do_ultimo(self):
        cad = {"ci": "920002", "numero": "CNJ: x", "cliente": "JOÃO FICTÍCIO"}
        r = c.resultado_do_cadastro("n", cad, c.comentarios_do_html(fixture("ficha-920002.html")), HOJE, 90)
        self.assertEqual((r["resultado"], r["ultimo_fora"], r["comentarios"]), (c.SEM_RECENTE, "07/05/2026", []))

    def test_contagem_por_numero_pedido(self):
        rs = [c.resultado_do_cadastro("a", {"ci": "1"}, [], HOJE, 90),
              c.resultado_do_cadastro("a", {"ci": "2"}, c.comentarios_do_html(fixture("ficha-920004.html")), HOJE, 90),
              c.resultado_sem_cadastro("b", c.NAO_ACHADO), c.resultado_sem_cadastro("d", c.ERRO, "x")]
        conta = c.contar(rs)
        self.assertEqual((conta["processos_pedidos"], conta["cadastros"], conta["com_comentario"],
                          conta["nao_encontrados"], conta["erros"], conta["comentarios"]), (3, 2, 1, 1, 1, 1))


class TestSimulado(unittest.TestCase):
    def test_execucao_completa_grava_csv_e_json(self):
        pasta = Path(tempfile.mkdtemp())
        env = pasta / ".env"
        env.write_text("SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n", encoding="utf-8")
        cfg = config.carregar(env, exigir_login=False, ambiente={})
        ctx = Contexto(driver=None, cfg=cfg, hoje=HOJE, simulado=True, fixtures=FIXTURES, saida=pasta / "saida",
                       chave="comentarios")
        secao = c.executar(ctx)
        self.assertEqual(secao.numeros["processos_pedidos"], 4)
        self.assertEqual(secao.numeros["com_comentario"], 2)
        self.assertEqual(secao.numeros["comentarios"], 3)
        self.assertEqual(secao.numeros["nao_encontrados"], 1)
        arq = pasta / "saida" / "comentarios-90dias.csv"
        with arq.open(encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        self.assertEqual(linhas[0], c.CABECALHO)
        self.assertEqual(len(linhas), 1 + 6)
        self.assertEqual(oct(os.stat(arq).st_mode & 0o777), "0o600")
        dados = json.loads((pasta / "saida" / "comentarios-90dias.json").read_text(encoding="utf-8"))
        self.assertEqual(dados["dias"], 90)


if __name__ == "__main__":
    unittest.main()
