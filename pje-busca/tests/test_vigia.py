"""Testes do vigia (parte 1): python3 -m unittest discover -s tests  (dentro de pje-busca/)."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import vigia_estado as VE  # noqa: E402
from vios_chrome import escolher_cnpj, url_lista  # noqa: E402


def linha(numero, cliente, ci="1", ativa="Autor: FULANO", orgao="2ª VT Sobral"):
    return {"ci": ci, "numero": " CNJ: " + numero if numero else "", "cliente": cliente, "ativa": ativa,
            "passiva": "Contrário: " + cliente, "advogado": "ADV", "auxiliares": "JOHN", "orgao": orgao}


A = linha("0001368-02.2026.5.07.0038", "MM COMERCIO DE CALCADOS LTDA (MATRIZ)", ci="10")
B = linha("0002754-04.2025.5.07.0038", "MM COMERCIO DE CALCADOS LTDA (MATRIZ)", ci="11")
C = linha("0001111-22.2025.8.06.0167", "EMPRESA X LTDA", ci="12")


class Puras(unittest.TestCase):
    def test_numero_e_tribunal(self):
        self.assertEqual(VE.numero_cnj(" CNJ: 0001368-02.2026.5.07.0038 "), "0001368-02.2026.5.07.0038")
        self.assertEqual(VE.tribunal("0001368-02.2026.5.07.0038"), "5.07")
        self.assertTrue(VE.eh_trt7("0001368-02.2026.5.07.0038"))
        self.assertEqual(VE.tribunal("0001111-22.2025.8.06.0167"), "8.06")
        self.assertEqual(VE.numero_cnj("Outros: 123"), "")

    def test_normalizar(self):
        self.assertEqual(VE.normalizar("  Comércio   São João "), "COMERCIO SAO JOAO")

    def test_preparar_sem_cnj_usa_ci_e_junta_clientes(self):
        p = VE.preparar([linha("", "A LTDA", ci="77"), A, dict(A, cliente="OUTRA LTDA")])
        self.assertIn("CI:77", p)
        self.assertEqual(p["0001368-02.2026.5.07.0038"]["empresas"], {"MM COMERCIO DE CALCADOS LTDA (MATRIZ)", "OUTRA LTDA"})
        self.assertEqual(p["0001368-02.2026.5.07.0038"]["autor"], "FULANO")

    def test_comparar(self):
        hoje = VE.preparar([A, C])
        r = VE.comparar({"MM COMERCIO DE CALCADOS LTDA (MATRIZ)"}, {"0002754-04.2025.5.07.0038", A["numero"][6:]}, hoje, True)
        self.assertEqual(list(r["empresas_novas"]), ["EMPRESA X LTDA"])
        self.assertEqual(r["processos_novos"], ["0001111-22.2025.8.06.0167"])
        self.assertEqual(r["sairam"], ["0002754-04.2025.5.07.0038"])
        r2 = VE.comparar(set(), {"0002754-04.2025.5.07.0038"}, hoje, completa=False)
        self.assertEqual(r2["sairam"], [])  # lista incompleta não marca saídas

    def test_escolher_cnpj(self):
        self.assertEqual(escolher_cnpj([{"doc": "09352289000182", "igual": True}]), ("ok", "09352289000182"))
        self.assertEqual(escolher_cnpj([{"doc": "09352289000182", "igual": True}, {"doc": "11111111000111", "igual": False}]),
                         ("ok", "09352289000182"))
        self.assertEqual(escolher_cnpj([{"doc": "09352289000182", "igual": False}, {"doc": "11111111000111", "igual": False}]),
                         ("varios", "09352289000182,11111111000111"))
        self.assertEqual(escolher_cnpj([{"doc": "12345678901", "igual": True}]), ("pf", ""))
        self.assertEqual(escolher_cnpj([]), ("nao_achado", ""))

    def test_url_lista(self):
        u = url_lista()
        for parte in ("pesq[pr_areas_id][]=3", "pesq[tipos_partes_id]=P", "pesq[filtros_multi][]=ativos",
                      "pesq[limit]=9999999", "Pesq=Pesquisar"):
            self.assertIn(parte, u)
        self.assertIn("pesq[advogados_id][]=7", url_lista(advogados=["7", " "]))
        self.assertNotIn("advogados", url_lista(advogados=[" "]))


class EstadoSqlite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.est = VE.Estado(Path(self.tmp.name) / "v.sqlite")

    def tearDown(self):
        self.est.fechar()
        self.tmp.cleanup()

    def test_base_depois_novos_e_saidas(self):
        r1 = self.est.aplicar([A, B], True, hoje=date(2026, 11, 23))
        self.assertTrue(r1["base"])
        self.assertIn("PRIMEIRA RODADA", VE.relatorio(r1))
        r2 = self.est.aplicar([A, C], True, hoje=date(2026, 11, 24))
        self.assertFalse(r2["base"])
        self.assertEqual(list(r2["empresas_novas"]), ["EMPRESA X LTDA"])
        self.assertEqual(r2["processos_novos"], ["0001111-22.2025.8.06.0167"])
        self.assertEqual(r2["sairam"], ["0002754-04.2025.5.07.0038"])
        self.assertEqual(self.est.resumo()["processos_ativos"], 2)
        r3 = self.est.aplicar([A, B, C], True, hoje=date(2026, 11, 25))
        self.assertEqual(r3["voltaram"], ["0002754-04.2025.5.07.0038"])
        self.assertEqual(r3["processos_novos"], [])
        txt = VE.relatorio(r3)
        self.assertIn("VOLTARAM", txt)

    def test_simular_nao_grava(self):
        self.est.aplicar([A], True, hoje=date(2026, 11, 23), simular=True)
        self.assertTrue(self.est.eh_base())
        self.assertEqual(self.est.resumo()["processos_ativos"], 0)

    def test_incompleta_nao_marca_saida(self):
        self.est.aplicar([A, B], True, hoje=date(2026, 11, 23))
        r = self.est.aplicar([A], False, hoje=date(2026, 11, 24))
        self.assertEqual(r["sairam"], [])
        self.assertEqual(self.est.resumo()["processos_ativos"], 2)

    def test_cnpj_e_fila(self):
        self.est.aplicar([A, B, C], True, hoje=date(2026, 11, 23))
        pend = self.est.sem_cnpj(10)
        self.assertEqual(len(pend), 2)
        self.est.gravar_cnpj("MM COMERCIO DE CALCADOS LTDA (MATRIZ)", "ok", "09352289000182")
        self.assertEqual(len(self.est.sem_cnpj(10)), 1)
        self.assertEqual(self.est.cnpjs(["MM COMERCIO DE CALCADOS LTDA (MATRIZ)"]),
                         {"MM COMERCIO DE CALCADOS LTDA (MATRIZ)": ("09352289000182", "ok")})
        fila = self.est.fila_pje(hoje=date(2026, 11, 23))
        self.assertEqual([p["numero"] for p in fila], ["0001368-02.2026.5.07.0038", "0002754-04.2025.5.07.0038"])

    def test_relatorio_mostra_trt7_e_cnpj(self):
        self.est.aplicar([A], True, hoje=date(2026, 11, 23))
        r = self.est.aplicar([A, C, linha("0009999-11.2026.5.07.0024", "NOVA LTDA", ci="13")], True, hoje=date(2026, 11, 24))
        txt = VE.relatorio(r, {"NOVA LTDA": ("12345678000199", "ok")})
        self.assertIn("NOVA LTDA · CNPJ 12345678000199", txt)
        self.assertIn("← TRT7: entra na fila do PJe", txt)


if __name__ == "__main__":
    unittest.main()
