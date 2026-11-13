"""Regras da skill de 13/11/2026: responsáveis, filial da perícia médica e DATA em feriado."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import envio_txt, lancamento, prazos, responsaveis as r  # noqa: E402

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

    def test_carlos_so_no_trabalhista_vai_para_o_johnys(self):
        item = {"auxiliares": "CARL"}
        self.assertEqual(r.do_processo(item, PESSOAS, trabalhista=True)[0], ["FRANCISCO JOHNYS VASCONCELOS BARBOSA"])
        self.assertEqual(r.do_processo(item, PESSOAS, trabalhista=False)[0], [])

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

    def test_filial_pela_cidade_quando_o_teor_nao_diz(self):
        item = {"auxiliares": "SUH", "texto": "Perícia designada.", "cidade": "JIJOCA DE JERICOACOARA/CE"}
        self.assertEqual(r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)[0], ["GUIVIA VASCONCELOS"])

    def test_filial_ausente_ou_ambigua_bloqueia(self):
        for item in ({"texto": "Perícia em Fortaleza.", "cidade": "FORTALEZA/CE"},
                     {"texto": "Perícia em Sobral ou Camocim.", "cidade": "SOBRAL/CE"}):
            nomes, bloqueio, _ = r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)
            self.assertEqual((nomes, bloqueio), ([], r.MSG_FILIAL))

    def test_nunca_suhiane_na_pericia_medica(self):
        item = {"auxiliares": "SUH", "texto": "Perícia em Sobral.", "cidade": "SOBRAL/CE"}
        self.assertNotIn("SUHIANE DE MARIA GOMES SILVA", r.da_tarefa(item, {"nome": self.NOME}, PESSOAS)[0])


class Feriado(unittest.TestCase):
    TABELA = prazos.Tabela("doc/feriados-brasil-2026-2027.md", "doc/feriados.txt")

    def test_exemplo_da_skill_02_11_vai_para_30_10(self):
        self.assertEqual(prazos.antecipar(date(2026, 11, 2), date(2026, 10, 28), self.TABELA)[:2],
                         (date(2026, 10, 30), "Finados"))

    def test_dia_normal_nao_muda(self):
        self.assertEqual(prazos.antecipar(date(2026, 11, 4), date(2026, 11, 2), self.TABELA)[:2], (date(2026, 11, 4), ""))

    def test_nao_volta_no_tempo(self):
        dia, feriado, aviso = prazos.antecipar(date(2026, 11, 2), date(2026, 11, 2), self.TABELA)
        self.assertEqual((dia, feriado), (date(2026, 11, 2), ""))
        self.assertIn("urgência", aviso)

    def test_feriado_estadual_so_com_o_local_do_escritorio(self):
        magna = date(2026, 3, 25)  # Data Magna do Ceará
        self.assertEqual(prazos.antecipar(magna, date(2026, 3, 20), self.TABELA, [])[0], magna)
        self.assertEqual(prazos.antecipar(magna, date(2026, 3, 20), self.TABELA, [("", "CE")])[0], date(2026, 3, 24))
        self.assertEqual(prazos.antecipar(magna, date(2026, 3, 20), self.TABELA, [("", "SP")])[0], magna)


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

    def test_pericia_medica_exige_o_responsavel_da_filial(self):
        t = "PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026"
        self.assertTrue(any("filial" in p for p in self.problemas(t, "SUHIANE DE MARIA GOMES SILVA")))
        self.assertFalse(any("filial" in p for p in self.problemas(t, "JOÃO JÂNIO")))


if __name__ == "__main__":
    unittest.main()
