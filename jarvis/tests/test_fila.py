"""IA em duas etapas (nucleo/ia/fila_ia.py): 1ª rodada grava o pedido; com a resposta escrita, a 2ª usa."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import ia  # noqa: E402
from nucleo.custo import Gasto  # noqa: E402
from nucleo.ia.fila_ia import FilaIA  # noqa: E402

SCHEMA = {"type": "object", "properties": {"resumo_caso": {"type": "string"}}, "required": ["resumo_caso"]}


class Fila(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.dict(os.environ, {"IA_FILA_PASTA": str(Path(self.tmp.name) / "fila")})
        p.start()
        self.addCleanup(p.stop)

    def test_pedido_depois_resposta(self):
        f = ia.criar("fila", "fila")
        texto = "Processo: 0001234-56.2025.5.07.0024\nCliente: X\n\nTAREFAS..."
        with self.assertRaisesRegex(ia.IAErro, "pendente na fila"):
            f.responder("SISTEMA", texto, SCHEMA)
        pedidos = list((f.pasta / "pedidos").glob("*.json"))
        self.assertEqual(len(pedidos), 1)
        p = json.loads(pedidos[0].read_text(encoding="utf-8"))
        self.assertEqual((p["usuario"], p["schema"]), (texto, SCHEMA))
        self.assertIn("|Processo: 0001234-56.2025.5.07.0024 #", p["chave"])
        self.assertEqual((f.pasta / "sistemas" / (p["sistema"] + ".txt")).read_text(encoding="utf-8"), "SISTEMA")
        (f.pasta / "respostas.json").write_text(json.dumps({p["chave"]: {"resumo_caso": "Horas extras."}}),
                                                encoding="utf-8")
        # 2ª rodada: o texto mudou (tarefa nova no VIOS), a 1ª linha não: usa a resposta
        r = f.responder("SISTEMA", texto + "\nTarefa nova", SCHEMA)
        self.assertEqual(r, {"resumo_caso": "Horas extras.", "_uso": {}})

    def test_resposta_incompleta_e_varios_arquivos(self):
        f = FilaIA()
        k = FilaIA.chave("S", "CI: 42\nresto")
        (f.pasta / "respostas").mkdir()
        (f.pasta / "respostas" / "lote1.json").write_text(json.dumps({k: {}}), encoding="utf-8")
        with self.assertRaisesRegex(ia.IAErro, "sem os campos"):
            f.responder("S", "CI: 42\nresto", SCHEMA)
        (f.pasta / "respostas" / "lote2.json").write_text(json.dumps({k: {"resumo_caso": "ok"}}), encoding="utf-8")
        self.assertEqual(f.responder("S", "CI: 42\noutro", SCHEMA)["resumo_caso"], "ok")

    def test_processo_sem_numero_ou_repetido(self):
        # dois processos sem número não podem dividir a mesma resposta
        a = FilaIA.chave("S", "Processo: \nCliente: X\nPolo do cliente: Parte Passiva\nParte ativa: Autor: Ana")
        b = FilaIA.chave("S", "Processo: \nCliente: X\nPolo do cliente: Parte Passiva\nParte ativa: Autor: Bia")
        self.assertNotEqual(a, b)
        # mesmo número digitado em dois processos diferentes
        self.assertNotEqual(FilaIA.chave("S", "Processo: 123\nCliente: X\nParte ativa: Autor: Ana"),
                            FilaIA.chave("S", "Processo: 123\nCliente: X\nParte ativa: Autor: Bia"))
        self.assertEqual(a, FilaIA.chave("S", "Processo: \nCliente: X\nPolo do cliente: Parte Passiva\n"
                                              "Parte ativa: Autor: Ana\n\nTAREFAS novas"))
        self.assertEqual(FilaIA.chave("S", "Grupo: LD URBANISMO\nProcessos: 3"), FilaIA.chave("S", "Grupo: LD URBANISMO\nx"))

    def test_sem_custo(self):
        self.assertEqual(Gasto(5).preco("fila (análise escrita pelo Claude no chat)"), (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
