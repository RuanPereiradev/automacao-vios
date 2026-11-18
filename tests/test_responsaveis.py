"""Regras da skill de 18/11/2026: responsáveis (CARL/CALTECH), perícia médica por filial e envio do TXT."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import envio_txt, lancamento, responsaveis as r  # noqa: E402

PESSOAS = ["AMANDA LEITE MENDES", "ANA LETÍCIA DA SILVA LEITAO", "BRENO SILVA MOTA",
           "CARLOS AUGUSTO ALVES CAMILO BRANDÃO", "CARLOS EDUARDO RODRIGUES SILVA",
           "FRANCISCO JOHNYS VASCONCELOS BARBOSA", "FRANCISCO VICTOR HORA DO NASCIMENTO", "GUIVIA VASCONCELOS",
           "IANNA BRENA MARIANO SILVA", "JOANA CLÁUDIA DOTTO", "JOÃO JÂNIO", "JOAQUIM JOSÉ DO NASCIMENTO NETO",
           "LILIAN YNARYA DE ARAÚJO NASCIMENTO", "RONEELY FEITOSA", "SUHIANE DE MARIA GOMES SILVA", "TAMIRA LOIOLA"]


class Auxiliar(unittest.TestCase):
    def test_siglas_viram_nomes(self):
        for sigla, nome in {"SUH": "SUHIANE DE MARIA GOMES SILVA", "TAMI": "TAMIRA LOIOLA", "JOAN": "JOANA CLÁUDIA DOTTO",
                            "JOHN": "FRANCISCO JOHNYS VASCONCELOS BARBOSA", "IANN": "IANNA BRENA MARIANO SILVA",
                            "JOAQ": "JOAQUIM JOSÉ DO NASCIMENTO NETO", "LILI": "LILIAN YNARYA DE ARAÚJO NASCIMENTO"}.items():
            self.assertEqual(r.nome_do_auxiliar(sigla, PESSOAS), nome, sigla)

    def test_sigla_ambigua_ou_curta_nao_adivinha(self):
        self.assertIsNone(r.nome_do_auxiliar("CARL", PESSOAS))
        self.assertIsNone(r.nome_do_auxiliar("JO", PESSOAS))

    def test_auxiliar_vence(self):
        nomes, bloqueio, _ = r.do_processo({"auxiliares": "TAMI / SUH", "advogado": "RONEELY FEITOSA"}, PESSOAS)
        self.assertEqual((nomes, bloqueio), (["TAMIRA LOIOLA", "SUHIANE DE MARIA GOMES SILVA"], ""))

    def test_sem_auxiliar_usa_o_advogado_responsavel(self):
        nomes, bloqueio, _ = r.do_processo({"auxiliares": "", "advogado": "Francisco Johnys Vasconcelos Barbosa"}, PESSOAS)
        self.assertEqual((nomes, bloqueio), (["FRANCISCO JOHNYS VASCONCELOS BARBOSA"], ""))

    def test_sem_auxiliar_e_ronielle_bloqueia(self):
        for adv in ("RONEELY FEITOSA", "Ronielle Feitosa"):
            nomes, bloqueio, _ = r.do_processo({"auxiliares": "", "advogado": adv}, PESSOAS)
            self.assertEqual((nomes, bloqueio), ([], r.MSG_RONIELLE))

    def test_carl_vai_para_o_johnys_em_qualquer_area(self):
        self.assertEqual(r.do_processo({"auxiliares": "CARL", "cliente": "ACME LTDA"}, PESSOAS)[0],
                         ["FRANCISCO JOHNYS VASCONCELOS BARBOSA"])

    def test_carl_do_caltech_fica_com_carlos(self):
        self.assertEqual(r.do_processo({"auxiliares": "CARL", "cliente": "CALTECH SERVIÇOS"}, PESSOAS)[0],
                         ["CARLOS AUGUSTO ALVES CAMILO BRANDÃO"])

    def test_sem_lista_do_vios_bloqueia(self):
        self.assertTrue(r.do_processo({"auxiliares": "SUH"}, [])[1])

    def test_breno_na_peticao_da_execucao(self):
        t = {"nome": "MINUTAR PETIÇÃO EXECUÇÃO 2026", "marcar_breno": True}
        self.assertEqual(r.da_tarefa({"auxiliares": "TAMI"}, t, PESSOAS)[0], ["TAMIRA LOIOLA", "BRENO SILVA MOTA"])


class Pericia(unittest.TestCase):
    NOME = "PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026"

    def test_filial_pelo_teor(self):
        item = {"auxiliares": "SUH", "texto": "Perícia médica na cidade de Tianguá, às 9h.", "cidade": "FORTALEZA/CE"}
        self.assertEqual(r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)[0], ["JOÃO JÂNIO"])

    def test_cidade_do_csv_nao_define_a_filial(self):
        item = {"auxiliares": "SUH", "texto": "Perícia designada.", "cidade": "JIJOCA DE JERICOACOARA/CE"}
        self.assertEqual(r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)[0], [r.CIDADE_IDENTIFICADA])

    def test_filial_ausente_ou_ambigua_usa_o_texto_sem_bloquear(self):
        for item in ({"texto": "Perícia em Fortaleza.", "cidade": "FORTALEZA/CE"},
                     {"texto": "Perícia em Sobral ou Camocim.", "cidade": "SOBRAL/CE"}):
            nomes, bloqueio, _ = r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)
            self.assertEqual((nomes, bloqueio), ([r.CIDADE_IDENTIFICADA], ""))

    def test_nunca_suhiane_na_pericia_medica(self):
        item = {"auxiliares": "SUH", "texto": "Perícia em Sobral.", "cidade": "SOBRAL/CE"}
        self.assertNotIn("SUHIANE DE MARIA GOMES SILVA", r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)[0])

    def test_escritorio_atual_define_a_filial(self):
        for escritorio, nome in (("Roneely Feitosa - Sobral", "ANA LETÍCIA DA SILVA LEITAO"),
                                 ("Roneely Feitosa - Camocim", "FRANCISCO VICTOR HORA DO NASCIMENTO"),
                                 ("Roneely Feitosa - Tianguá", "JOÃO JÂNIO"),
                                 ("Roneely Feitosa - Jijoca de Jericoacoara", "GUIVIA VASCONCELOS")):
            nomes, bloqueio, _ = r.da_pericia_pelo_escritorio(escritorio, PESSOAS)
            self.assertEqual((nomes, bloqueio), ([nome], ""), escritorio)

    def test_escritorio_sem_filial_bloqueia_no_lancamento(self):
        for escritorio in ("Roneely Feitosa - Fortaleza", "", None):
            nomes, bloqueio, _ = r.da_pericia_pelo_escritorio(escritorio, PESSOAS)
            self.assertEqual(nomes, [])
            self.assertIn(r.MSG_FILIAL, bloqueio)

    def test_segunda_checagem_troca_o_responsavel_e_tira_o_bloqueio_da_analise(self):
        import tempfile, json
        res = {"ci": "1", "link_lancar": "x", "alertas": [],
               "bloqueios": [f"{self.NOME}: {r.MSG_FILIAL}", "Falta no documento: horário"],
               "tarefas": [{"nome": self.NOME, "responsaveis": ["ANA LETÍCIA DA SILVA LEITAO"]},
                           {"nome": "OUTRA 2026", "responsaveis": ["TAMIRA LOIOLA"]}]}
        original = lancamento.ler_escritorio
        with tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / "responsaveis.json").write_text(json.dumps(PESSOAS), encoding="utf-8")
            try:
                lancamento.ler_escritorio = lambda *a: "Roneely Feitosa - Camocim"
                lancamento.conferir_pericia(None, res, pasta, 1)
                self.assertEqual(res["tarefas"][0]["responsaveis"], ["FRANCISCO VICTOR HORA DO NASCIMENTO"])
                self.assertEqual(res["tarefas"][1]["responsaveis"], ["TAMIRA LOIOLA"])
                self.assertEqual(res["bloqueios"], ["Falta no documento: horário"])
                lancamento.ler_escritorio = lambda *a: "Roneely Feitosa - Fortaleza"
                lancamento.conferir_pericia(None, res, pasta, 1)
                self.assertTrue(any(r.MSG_FILIAL in b for b in res["bloqueios"]))
                # sem perícia médica: nem abre o VIOS
                lancamento.ler_escritorio = lambda *a: self.fail("não devia ler o escritório")
                lancamento.conferir_pericia(None, {"tarefas": [{"nome": "OUTRA 2026"}]}, pasta, 1)
            finally:
                lancamento.ler_escritorio = original


class TravaDoTxt(unittest.TestCase):
    def bloco(self, tarefa, resp):
        return (f"CI: 1\nPROCESSO: 0000123-45.2026.8.06.0001\nTAREFA: {tarefa}\nDATA: 20/11/2026\nHORA: 09:00\n"
                f"RESPONSÁVEIS: {resp}\nDESCRIÇÃO:\nteste\n")

    def problemas(self, tarefa, resp):
        res = envio_txt.ler(self.bloco(tarefa, resp), [tarefa], PESSOAS, {}, {}, "https://x/", hoje=date(2026, 11, 13))
        c = res[0] if isinstance(res, tuple) else res
        c = c[0] if isinstance(c, list) else c
        return c["problemas"]

    def test_ronielle_sozinho_barra(self):
        self.assertTrue(any("RONIELLE" in p for p in self.problemas("CIÊNCIA (CÍVEL) 2026", "RONEELY FEITOSA")))

    def test_pericia_medica_exige_o_responsavel_da_filial_ou_o_texto_da_skill(self):
        t = "PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026"
        self.assertTrue(any("filial" in p for p in self.problemas(t, "SUHIANE DE MARIA GOMES SILVA")))
        self.assertFalse(any("filial" in p for p in self.problemas(t, "JOÃO JÂNIO")))
        self.assertFalse(any("filial" in p for p in self.problemas(t, r.CIDADE_IDENTIFICADA)))


if __name__ == "__main__":
    unittest.main()
