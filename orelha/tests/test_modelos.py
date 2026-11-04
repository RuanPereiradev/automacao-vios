import tempfile
import unittest
from datetime import date
from pathlib import Path

from nucleo import simulado
from nucleo.modelos import Contexto, Item, Secao


class TestModelos(unittest.TestCase):
    def test_item_nivel(self):
        self.assertEqual(Item("x").nivel, "info")
        with self.assertRaises(ValueError):
            Item("x", nivel="urgente")

    def test_secao(self):
        s = Secao("prazos", "T", "r", [Item("a", nivel="grave"), Item("b", nivel="grave"), Item("c")],
                  {"atrasadas": 3, "graves": 2, "por_responsavel": {"Pessoa": 3}, "ok": True})
        self.assertEqual(s.por_nivel(), {"grave": 2, "atencao": 0, "info": 1})
        self.assertEqual(s.numeros_seguros(), {"atrasadas": 3, "graves": 2})
        self.assertEqual(s.erro, "")
        self.assertEqual(s.avisos, [])

    def test_contexto_historico(self):
        pasta = Path(tempfile.mkdtemp())
        ctx = Contexto(driver=None, cfg=None, hoje=date(2026, 11, 4), fixtures=pasta / "fx",
                       historico=pasta / "historico", chave="prazos")
        self.assertEqual(ctx.ler_historico("x.json", {"vazio": 1}), {"vazio": 1})
        ctx.gravar_historico("x.json", {"n": 2, "dia": date(2026, 11, 4)})
        self.assertEqual(ctx.ler_historico("x.json"), {"n": 2, "dia": "2026-11-04"})
        (pasta / "historico" / "ruim.json").write_text("{", encoding="utf-8")
        self.assertIsNone(ctx.ler_historico("ruim.json"))
        self.assertEqual(ctx.fixture("a.html"), pasta / "fx" / "prazos" / "a.html")
        self.assertIsNone(ctx.emitir("fase", fase="x"))


class TestSimulado(unittest.TestCase):
    def test_substituir(self):
        hoje = date(2026, 11, 4)
        self.assertEqual(simulado.substituir("{{HOJE}} {{HOJE+1}} {{HOJE-30}} {{ISO:HOJE-3}}", hoje),
                         "04/11/2026 05/11/2026 05/10/2026 2026-11-01")

    def test_ler_e_listar(self):
        pasta = Path(tempfile.mkdtemp())
        (pasta / "agenda").mkdir()
        (pasta / "agenda" / ".gitkeep").write_text("")
        (pasta / "agenda" / "cal.html").write_text("<td>{{HOJE}}</td>", encoding="utf-8")
        ctx = Contexto(driver=None, cfg=None, hoje=date(2026, 11, 4), fixtures=pasta, chave="agenda")
        self.assertEqual(simulado.ler(ctx, "cal.html"), "<td>04/11/2026</td>")
        self.assertEqual(simulado.ler(ctx, "cal.html", datas=False), "<td>{{HOJE}}</td>")
        self.assertEqual([p.name for p in simulado.listar(ctx)], ["cal.html"])
        with self.assertRaises(FileNotFoundError):
            simulado.ler(ctx, "nao.html")


if __name__ == "__main__":
    unittest.main()
