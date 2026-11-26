"""Rodadas agendadas do vigia (src/vigia_agenda.py): ordem dos passos, trava compartilhada com a aba e registro."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import vigia_agenda as AG  # noqa: E402


class Agenda(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name)
        self.feitos, self.mensagens = [], []

    def rodar(self, etapa, codigos=None, **kw):
        codigos = codigos or {}

        def executar(c):
            # durante a rodada a trava aponta para a agenda (a aba mostra "rodando" e o botão espera)
            self.trava = json.loads((self.pasta / AG.TRAVA).read_text(encoding="utf-8"))
            self.feitos.append(c)
            return codigos.get(c, 0)
        return AG.rodar(self.pasta, etapa, executar=executar, dormir=lambda s: None, aviso=self.mensagens.append, **kw)

    def test_manha_vios_depois_djen(self):
        self.assertEqual(self.rodar("manha"), 0)
        self.assertEqual(self.feitos, ["vios", "djen", "monitor"])
        self.assertEqual(self.trava["comando"], "agenda-manha")
        self.assertFalse((self.pasta / AG.TRAVA).exists())  # trava solta no fim
        u = AG.ultima(self.pasta)
        self.assertEqual((u["etapa"], u["ok"], [p["comando"] for p in u["passos"]]), ("manha", True, ["vios", "djen", "monitor"]))

    def test_djen_roda_mesmo_se_o_vios_falhar(self):
        self.assertEqual(self.rodar("manha", {"vios": 1}), 1)
        self.assertEqual(self.feitos, ["vios", "djen", "monitor"])
        self.assertFalse(AG.ultima(self.pasta)["ok"])

    def test_passo_que_quebra_nao_para_o_proximo(self):
        def executar(c):
            self.feitos.append(c)
            if c == "vios":
                raise RuntimeError("Chrome fechado")
            return 0
        r = AG.rodar(self.pasta, "manha", executar=executar, aviso=self.mensagens.append)
        self.assertEqual((r, self.feitos), (1, ["vios", "djen", "monitor"]))

    def test_madrugada_associados(self):
        self.assertEqual(self.rodar("madrugada"), 0)
        self.assertEqual(self.feitos, ["associados", "monitor-tribunal"])

    def test_espera_o_botao_da_aba_e_desiste(self):
        (self.pasta / "logs").mkdir()
        (self.pasta / AG.TRAVA).write_text(json.dumps({"pid": 999999, "comando": "associados"}), encoding="utf-8")
        r = self.rodar("manha", vivo=lambda pid: True, esperar_max=120, passo=60)
        self.assertEqual((r, self.feitos), (3, []))
        self.assertIn("associados", AG.ultima(self.pasta)["motivo"])
        self.assertTrue((self.pasta / AG.TRAVA).exists())  # a trava do botão não é mexida

    def test_espera_e_roda_quando_o_botao_termina(self):
        (self.pasta / "logs").mkdir()
        (self.pasta / AG.TRAVA).write_text(json.dumps({"pid": 999999, "comando": "djen"}), encoding="utf-8")
        respostas = iter([True, False])
        self.assertEqual(self.rodar("manha", vivo=lambda pid: next(respostas)), 0)
        self.assertEqual(self.feitos, ["vios", "djen", "monitor"])

    def test_trava_de_processo_morto_nao_segura(self):
        (self.pasta / "logs").mkdir()
        (self.pasta / AG.TRAVA).write_text(json.dumps({"pid": 999999, "comando": "djen"}), encoding="utf-8")
        self.assertEqual(self.rodar("manha", vivo=lambda pid: False), 0)

    def test_etapa_invalida(self):
        with self.assertRaises(ValueError):
            AG.rodar(self.pasta, "tarde", executar=lambda c: 0)


if __name__ == "__main__":
    unittest.main()
