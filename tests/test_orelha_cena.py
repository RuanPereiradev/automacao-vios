"""Contrato "cena" de bot/orelha.status(): só datas e contagens do relatório real mais recente."""
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import orelha  # noqa: E402

CHAVES = {"data", "gerado_em", "atrasadas", "graves", "vencem_hoje", "intimacoes", "intimacoes_graves",
          "parados", "parados_graves", "audiencias_hoje", "pericias_hoje", "erros", "funcoes"}
NOME = "Fulano de Tal Ficticio"


def resumo(secoes, erros=()):
    return {"gerado_em": "2026-11-05T07:30:00", "secoes": secoes, "erros": list(erros)}


COMPLETO = resumo([
    {"chave": "prazos", "por_nivel": {"grave": 2}, "numeros": {
        "atrasadas": 9, "graves": 3, "vencem_hoje": 4, "por_responsavel": {NOME: 5}, "por_area": {"Area Secreta": 2}}},
    {"chave": "intimacoes", "numeros": {"esquecidas": 6, "graves": 1, "por_responsavel": {NOME: 1}}},
    {"chave": "parados", "numeros": {"parados": 7, "graves": 2}},
    {"chave": "agenda", "numeros": {"audiencias_hoje": 2, "pericias_hoje": 1}},
], erros=["falha x"])


class CenaTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        (self.pasta / "main.py").write_text("", encoding="utf-8")

    def dia(self, nome, dados):
        d = self.pasta / "saida" / nome
        d.mkdir(parents=True)
        (d / "relatorio.html").write_text("<html></html>", encoding="utf-8")
        (d / "resumo.json").write_text(json.dumps(dados), encoding="utf-8")

    def status(self):
        return orelha.status(self.pasta, agora=datetime(2026, 11, 5, 10, 0))

    def test_sem_relatorio_cena_nula(self):
        self.assertIsNone(self.status()["cena"])

    def test_nao_configurado_cena_nula(self):
        self.assertIsNone(orelha.status(self.pasta / "nao-existe")["cena"])

    def test_relatorio_real_contagens(self):
        self.dia("2026-11-05", COMPLETO)
        c = self.status()["cena"]
        self.assertEqual(set(c), CHAVES)
        self.assertEqual(c, {
            "data": "2026-11-05", "gerado_em": "2026-11-05T07:30:00", "atrasadas": 9, "graves": 3,
            "vencem_hoje": 4, "intimacoes": 6, "intimacoes_graves": 1, "parados": 7, "parados_graves": 2,
            "audiencias_hoje": 2, "pericias_hoje": 1, "erros": 1, "funcoes": ["prazos", "intimacoes", "parados", "agenda"]})

    def test_simulado_ignorado(self):
        self.dia("simulado-2026-11-05", COMPLETO)
        self.assertIsNone(self.status()["cena"])

    def test_usa_o_real_mais_recente(self):
        self.dia("2026-11-03", resumo([{"chave": "prazos", "numeros": {"atrasadas": 1}}]))
        self.dia("2026-11-04", resumo([{"chave": "prazos", "numeros": {"atrasadas": 2}}]))
        self.dia("simulado-2026-11-05", COMPLETO)
        c = self.status()["cena"]
        self.assertEqual((c["data"], c["atrasadas"]), ("2026-11-04", 2))

    def test_secao_ausente_vira_zero(self):
        self.dia("2026-11-05", resumo([{"chave": "prazos", "numeros": {"atrasadas": 4}}]))
        c = self.status()["cena"]
        self.assertEqual(c["atrasadas"], 4)
        for k in ("graves", "vencem_hoje", "intimacoes", "intimacoes_graves", "parados", "parados_graves",
                  "audiencias_hoje", "pericias_hoje", "erros"):
            self.assertEqual(c[k], 0, k)
        self.assertEqual(c["funcoes"], ["prazos"])

    def test_numeros_invalidos_viram_zero(self):
        self.dia("2026-11-05", resumo([{"chave": "prazos", "numeros": {"atrasadas": "x", "graves": None}},
                                       {"chave": "parados", "numeros": []}]))
        c = self.status()["cena"]
        self.assertEqual((c["atrasadas"], c["graves"], c["parados"]), (0, 0, 0))

    def test_sem_nomes_no_json(self):
        self.dia("2026-11-05", COMPLETO)
        texto = json.dumps(self.status()["cena"], ensure_ascii=False)
        self.assertNotIn(NOME, texto)
        self.assertNotIn("Area Secreta", texto)
        self.assertNotIn("por_responsavel", texto)
        self.assertNotIn("por_area", texto)


if __name__ == "__main__":
    unittest.main()
