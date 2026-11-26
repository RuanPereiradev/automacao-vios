"""Página /monitor (bot/monitor.py): leitura do banco do monitor do pje-busca, "Visto" da equipe e rotas do Flask.
Dados fictícios (números de processo e nomes inventados)."""
import base64
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pje-busca" / "src"))
from bot import monitor as W  # noqa: E402

_spec = importlib.util.spec_from_file_location("monitor_pje", RAIZ / "pje-busca" / "src" / "monitor.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

A = "0000001-11.2009.8.06.0053"  # TJCE, com novidade no tribunal
B = "0000002-22.2015.5.07.0029"  # TRT7, parado
C = "0000003-33.2019.4.01.4002"  # TRF1, só API, nunca movimentou
D = "0000004-44.2026.4.05.8103"  # TRF5, erro no tribunal


def montar(pasta):
    (pasta / "dados").mkdir(parents=True)
    (pasta / "vigia.py").write_text("print('vigia')\n", encoding="utf-8")
    est = M.Estado(pasta / "dados" / "monitor.sqlite")
    procs = [{"numero": n, "tribunal": M.tribunal_de(n)[0], "grau": M.tribunal_de(n)[1],
              "sistema": M.tribunal_de(n)[2], "vara": v, "cliente": c, "acao": "AÇÃO", "situacao": "ATIVO", "ci": "9"}
             for n, v, c in [(A, "2ª Vara de Camocim", "FULANO DE TAL"), (B, "VT Tianguá", "BELTRANO"),
                             (C, "JEF Parnaíba", "CICRANO"), (D, "19ª Vara Federal", "DEUSDEDIT")]]
    est.importar(procs, date(2026, 11, 1))
    est.gravar_tribunal(A, {"ok": True, "itens": [{"data": "2026-11-20", "mov": "CONCLUSOS", "docs": []}]}, "2026-11-20")
    est.gravar_tribunal(A, {"ok": True, "itens": [{"data": "2026-11-26", "hora": "08:15", "mov": "DECISÃO",
                                                   "docs": ["262594296 - Decisão"]}],
                            "teor": "Homologo os cálculos. " * 100, "teor_de": "262594296 - Decisão (2026-11-26)"},
                       "2026-11-26")
    est.gravar_djen(B, [{"data": "2025-01-10", "tipo": "Intimação", "orgao": "VT", "texto": "Arquivem-se.",
                         "documento": ""}], "2026-11-26")
    est.gravar_tribunal(D, {"ok": False, "erro": "não encontrado no PJe"}, "2026-11-26")
    est.rodada("2026-11-26T07:40:00", "api", {"djen": 4, "datajud": 4, "oab_publicacoes": 9, "erros": 0})
    est.fechar()


class Painel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name)
        montar(self.pasta)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sem_banco(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(W.painel(d)["configurado"])
            self.assertFalse(W.resumo(d)["configurado"])

    def test_abas(self):
        p = W.painel(self.pasta, hoje=date(2026, 11, 26))
        self.assertEqual(p["total"], 4)
        self.assertEqual([i["numero"] for i in p["novidades"]], [A])
        self.assertEqual(p["pendentes"], 1)
        self.assertEqual([i["numero"] for i in p["parados"]], [B])
        self.assertEqual([i["numero"] for i in p["erros"]], [D])
        self.assertEqual(p["sem_movimento"], 2)  # C (só API, nada lido) e D (erro)
        a = next(i for i in p["itens"] if i["numero"] == A)
        self.assertEqual((a["ultima"]["fonte"], a["ultima"]["data_br"], a["dias"]), ("tribunal", "26/11/2026", 0))
        self.assertTrue(a["trib"]["teor_cortado"])
        self.assertEqual(p["rodadas"]["api"]["data_br"], "26/11/2026")
        trf1 = next(t for t in p["por_tribunal"] if t["tribunal"].startswith("TRF1"))
        self.assertTrue(trf1["so_api"])

    def test_visto_vale_para_a_movimentacao_vista(self):
        W.conferir(self.pasta, A, "Dra. Fulana", "tarefa criada", agora=datetime(2026, 11, 26, 10, 0))
        p = W.painel(self.pasta, hoje=date(2026, 11, 26))
        self.assertEqual(p["pendentes"], 0)
        self.assertTrue(p["novidades"][0]["visto"])
        # o processo anda de novo: volta a ser novidade
        est = M.Estado(self.pasta / "dados" / "monitor.sqlite")
        est.gravar_tribunal(A, {"ok": True, "itens": [{"data": "2026-11-27", "mov": "EXPEDIÇÃO DE RPV", "docs": []}]},
                            "2026-11-27")
        est.fechar()
        self.assertEqual(W.painel(self.pasta, hoje=date(2026, 11, 27))["pendentes"], 1)
        W.conferir(self.pasta, A, "", desfazer=True)

    def test_conferir_valida(self):
        with self.assertRaises(W.MonitorErro):
            W.conferir(self.pasta, A, "")
        with self.assertRaises(W.MonitorErro):
            W.conferir(self.pasta, "123", "x")
        with self.assertRaises(W.MonitorErro):
            W.conferir(self.pasta, "0009999-99.2026.8.06.0001", "x")

    def test_processo(self):
        i = W.processo(self.pasta, A)
        self.assertFalse(i["trib"]["teor_cortado"])
        self.assertEqual(len(i["movimentos"]), 2)
        self.assertIsNone(W.processo(self.pasta, "0009999-99.2026.8.06.0001"))
        self.assertIsNone(W.processo(self.pasta, "../../etc"))


class Rotas(unittest.TestCase):
    def setUp(self):
        try:
            from bot import envio_web
        except ImportError as e:  # Flask/Selenium fora deste Python
            self.skipTest(str(e))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        raiz = Path(self._tmp.name)
        self.pasta = raiz / "pje-busca"
        self.pasta.mkdir()
        montar(self.pasta)
        env = raiz / ".env"
        env.write_text("SISTEMA_URL=https://vios.exemplo/\nSISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n"
                       "LOGIN_CAMPO_USUARIO=css:#u\nLOGIN_CAMPO_SENHA=css:#s\n"
                       f"SAIDA_PASTA={raiz / 'saida'}\n", encoding="utf-8")
        ambiente = mock.patch.dict(os.environ, {"PJE_BUSCA_PASTA": str(self.pasta)})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.app = envio_web.criar_app(str(env), senha="senha-da-vila").test_client()
        self.auth = {"Authorization": "Basic " + base64.b64encode(b"x:senha-da-vila").decode()}

    def test_pede_senha(self):
        self.assertEqual(self.app.get("/monitor").status_code, 401)

    def test_pagina_processo_e_cartao(self):
        r = self.app.get("/monitor", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        for n in (A, B, C, D):
            self.assertIn(n.encode(), r.data)
        self.assertIn("1 processo(s) com movimentação nova".encode(), r.data)
        r = self.app.get(f"/monitor/processo/{A}", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Homologo os cálculos".encode(), r.data)
        self.assertEqual(self.app.get("/monitor/processo/0009999-99.2026.8.06.0001", headers=self.auth).status_code, 404)
        r = self.app.get("/", headers=self.auth)
        self.assertIn("Abrir Monitor".encode(), r.data)

    def test_visto_pela_pagina(self):
        r = self.app.post("/monitor/conferir", headers=self.auth, json={"numero": A, "quem": "Dr. Beltrano"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(W.conferencias(self.pasta)[A]["quem"], "Dr. Beltrano")
        r = self.app.post("/monitor/conferir", headers=self.auth, json={"numero": A})
        self.assertEqual(r.status_code, 400)
        r = self.app.post("/monitor/conferir", headers=dict(self.auth, Origin="https://outro.site"),
                          json={"numero": A, "quem": "x"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
