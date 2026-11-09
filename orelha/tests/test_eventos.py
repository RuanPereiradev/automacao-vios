import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from urllib.error import HTTPError, URLError

from nucleo import eventos


class TestEventos(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())

    def test_stdout_e_local(self):
        saida = io.StringIO()
        ev = eventos.Eventos(pasta=self.pasta, stdout=True, envio="teste_1", saida_padrao=saida)
        ev.emitir("fase", fase="lendo_calendario")
        linha = saida.getvalue().strip()
        self.assertTrue(linha.startswith("@evento "))
        dados = json.loads(linha[len("@evento "):])
        self.assertEqual((dados["bot"], dados["envio"], dados["tipo"], dados["fase"]),
                         ("orelha", "teste_1", "fase", "lendo_calendario"))
        self.assertIn("ts", dados)
        local = (self.pasta / eventos.LOCAL).read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(local[0])["fase"], "lendo_calendario")

    def test_sem_stdout_por_padrao(self):
        saida = io.StringIO()
        eventos.Eventos(pasta=self.pasta, saida_padrao=saida).emitir("fase", fase="x")
        self.assertEqual(saida.getvalue(), "")

    def test_limpa_dados_de_cliente(self):
        ev = eventos.Eventos(pasta=self.pasta)
        e = ev.emitir("achado", funcao="prazos", nivel="grave", contagem=2, nome="Fulano de Tal",
                      por_responsavel={"Fulano": 3}, extra={"cliente": "X", "ok": 1},
                      obs="processo 0001234-56.2026.8.06.0001 ok")
        self.assertNotIn("nome", e)
        self.assertNotIn("por_responsavel", e)
        self.assertEqual(e["extra"], {"ok": 1})
        self.assertEqual(e["obs"], "processo [removido] ok")
        self.assertEqual(e["contagem"], 2)

    def test_post_falha_nunca_levanta_e_desiste(self):
        ev = eventos.Eventos(url="http://127.0.0.1:9/eventos", senha="s3nh4", pasta=self.pasta, timeout=0.1)
        with mock.patch.object(eventos.request, "urlopen", side_effect=URLError("recusada")) as abrir:
            for _ in range(5):
                self.assertIsNotNone(ev.emitir("fase", fase="x"))
        self.assertEqual(abrir.call_count, eventos.FALHAS_MAX)
        self.assertTrue(ev.desistiu)
        pend = (self.pasta / eventos.PENDENTES).read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(pend), 5)

    def test_post_http_erro(self):
        ev = eventos.Eventos(url="http://x/eventos", pasta=self.pasta)
        erro = HTTPError("http://x/eventos", 401, "nao", {}, io.BytesIO(b""))
        with mock.patch.object(eventos.request, "urlopen", side_effect=erro):
            ev.emitir("fase", fase="x")
        self.assertEqual(ev.falhas, 1)

    def test_post_ok_com_autenticacao(self):
        ev = eventos.Eventos(url="http://x/eventos", senha="abc", usuario="orelha", pasta=self.pasta)
        resposta = mock.MagicMock()
        resposta.__enter__.return_value.read.return_value = b"{}"
        with mock.patch.object(eventos.request, "urlopen", return_value=resposta) as abrir:
            ev.emitir("execucao_iniciada", simulado=True)
        req = abrir.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertTrue(req.get_header("Authorization").startswith("Basic "))
        self.assertEqual(json.loads(req.data)["bot"], "orelha")
        self.assertFalse((self.pasta / eventos.PENDENTES).exists())

    def test_emitir_nunca_levanta(self):
        ev = eventos.Eventos(pasta=self.pasta)
        self.assertIsNotNone(ev.emitir("x", ruim=object()))  # objeto vira texto (default=str)
        with mock.patch.object(eventos.json, "dumps", side_effect=TypeError("x")):
            self.assertIsNone(ev.emitir("x"))

    def test_iniciar_modulo(self):
        cfg = SimpleNamespace(vila_url="", vila_senha="", vila_usuario="orelha", vila_timeout=2.0)
        ev = eventos.iniciar(cfg, pasta=self.pasta)
        self.assertIs(eventos.atual(), ev)
        eventos.emitir("fase", fase="x")
        self.assertEqual(ev.emitidos[-1]["tipo"], "fase")


if __name__ == "__main__":
    unittest.main()
