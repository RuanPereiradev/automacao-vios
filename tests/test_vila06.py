"""Vila 06 (bot do Previdenciário): proxy do estado, lista fechada de vídeos e rotas do Flask."""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import vila06  # noqa: E402

BRUTO = {
    "versao": 1, "agora": "2026-11-13T18:00:00Z", "horario": "fechado", "conexao": "conectado", "modo": "producao",
    "hoje": {"respondidas": 7, "encaminhadas": 2, "naoEntendidas": 1}, "comEquipe": 1, "ultimo": 42,
    "eventos": [{"n": 41, "tipo": "respondeu", "em": "2026-11-13T17:59:00Z"},
                {"n": 42, "tipo": "outro", "em": "x"},
                {"n": 43, "tipo": "encaminhou", "em": "2026-11-13T18:00:00Z", "numero": "5588999990000"}],
    "segredo": "não deveria passar",
}


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Estado(unittest.TestCase):
    def conf(self, **extra):
        c = {"url": "https://192.168.0.20:3000", "token": "t" * 32, "certificado": "", "clipes": Path("/nao/existe")}
        c.update(extra)
        return c

    def test_limpar_so_passa_campos_conhecidos(self):
        d = vila06.limpar(BRUTO)
        self.assertEqual(d["horario"], "fechado")
        self.assertEqual(d["hoje"], {"respondidas": 7, "encaminhadas": 2, "naoEntendidas": 1})
        self.assertEqual([e["n"] for e in d["eventos"]], [41, 43])
        texto = json.dumps(d)
        self.assertNotIn("segredo", texto)
        self.assertNotIn("5588999990000", texto)

    def test_limpar_corrige_tipos_estranhos(self):
        d = vila06.limpar({"hoje": {"respondidas": "9", "encaminhadas": -3}, "comEquipe": True, "conexao": "x"})
        self.assertEqual(d["hoje"], {"respondidas": 0, "encaminhadas": 0, "naoEntendidas": 0})
        self.assertEqual(d["comEquipe"], 0)
        self.assertEqual(d["conexao"], "reconectando")

    def test_pede_ao_bot_com_token_e_desde(self):
        visto = {}

        def abrir(pedido, timeout, context):
            visto["url"], visto["auth"] = pedido.full_url, pedido.get_header("Authorization")
            return Resposta(json.dumps(BRUTO).encode())
        d = vila06.estado(self.conf(), 40, abrir=abrir)
        self.assertEqual(visto["url"], "https://192.168.0.20:3000/vila/estado?desde=40")
        self.assertEqual(visto["auth"], "Bearer " + "t" * 32)
        self.assertEqual(d["fonte"], "bot")

    def test_bot_fora_do_ar_e_token_recusado(self):
        def caiu(*a, **k):
            raise urllib.error.URLError("recusado")

        def recusado(*a, **k):
            raise urllib.error.HTTPError("u", 401, "x", {}, None)
        self.assertEqual(vila06.estado(self.conf(), 5, abrir=caiu)["erro"], "bot fora do ar")
        d = vila06.estado(self.conf(), 5, abrir=recusado)
        self.assertEqual((d["fonte"], d["erro"], d["ultimo"]), ("erro", "token recusado", 5))

    def test_sem_url_e_simulado(self):
        d = vila06.estado(self.conf(url=""))
        self.assertEqual(d["fonte"], "simulado")
        self.assertEqual(d["eventos"], [])
        d2 = vila06.simulado(desde=d["ultimo"] - 2, agora=(d["ultimo"]) * 20 + 1)
        self.assertEqual([e["n"] for e in d2["eventos"]], [d["ultimo"] - 1, d["ultimo"]])


class Clipes(unittest.TestCase):
    def test_lista_fechada(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "plantao.mp4").write_bytes(b"x")
            (Path(t) / "outro.mp4").write_bytes(b"x")
            self.assertEqual(vila06.clipes_instalados(t), ["plantao"])
            self.assertIsNone(vila06.caminho_clipe(t, "outro"))
            self.assertIsNone(vila06.caminho_clipe(t, "../plantao"))
            self.assertIsNone(vila06.caminho_clipe(t, "fora"))

    def test_retratos_lista_fechada(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "retrato-neutro.png").write_bytes(b"x")
            (Path(t) / "retrato-outro.png").write_bytes(b"x")
            self.assertEqual(vila06.retratos_instalados(t), ["neutro"])
            self.assertIsNone(vila06.caminho_retrato(t, "outro"))
            self.assertIsNone(vila06.caminho_retrato(t, "../neutro"))

    def test_sons_lista_fechada(self):
        with tempfile.TemporaryDirectory() as t:
            sons = Path(t) / "sons"
            sons.mkdir()
            for nome in ("musica", "sfx-corte", "fala-0a1b2c3d", "fala-xyz", "outro", "fala-0A1B2C3D"):
                (sons / f"{nome}.mp3").write_bytes(b"x")
            self.assertEqual(vila06.sons_instalados(t), ["fala-0a1b2c3d", "musica", "sfx-corte"])
            self.assertIsNone(vila06.caminho_som(t, "outro"))
            self.assertIsNone(vila06.caminho_som(t, "../sons/musica"))
            self.assertIsNone(vila06.caminho_som(t, "ambiente"))  # da lista, mas não instalado
            self.assertEqual(vila06.sons_instalados(Path(t) / "nao-existe"), [])

    def test_hash_das_falas_bate_com_a_pagina(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "doc" / "vila"))
        import gerar_sons_vila06 as g
        self.assertEqual(g.fnv1a("Tudo calmo por aqui."), "319a2958")  # o mesmo valor de hashFala() na página
        falas = g.falas()
        self.assertIn("Tudo calmo por aqui.", falas)
        self.assertFalse([f for f in falas if "{" in f], "fala com número não tem voz gravada")


class Rotas(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        pasta = Path(self._tmp.name)
        self.clipes = pasta / "clipes"
        self.clipes.mkdir()
        (self.clipes / "respondendo.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 64)
        env = pasta / ".env"
        env.write_text("SISTEMA_URL=https://vios.exemplo/\nSISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n"
                       "LOGIN_CAMPO_USUARIO=css:#u\nLOGIN_CAMPO_SENHA=css:#s\n"
                       f"SAIDA_PASTA={pasta / 'saida'}\nVILA06_URL=\nVILA06_TOKEN=\nVILA06_CLIPES={self.clipes}\n",
                       encoding="utf-8")
        ambiente = mock.patch.dict(os.environ, {}, clear=False)
        ambiente.start()
        self.addCleanup(ambiente.stop)
        from bot import envio_web
        self.app = envio_web.criar_app(str(env), senha="senha-da-vila").test_client()
        self.auth = {"Authorization": "Basic " + __import__("base64").b64encode(b"x:senha-da-vila").decode()}

    def test_pede_senha(self):
        self.assertEqual(self.app.get("/vila/previdenciario/estado").status_code, 401)

    def test_pagina_estado_e_clipes(self):
        r = self.app.get("/vila/previdenciario", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Vila 06", r.data)
        e = self.app.get("/vila/previdenciario/estado", headers=self.auth).get_json()
        self.assertEqual(e["fonte"], "simulado")
        self.assertEqual(e["clipes"], ["respondendo"])
        r = self.app.get("/vila/previdenciario/clipes/respondendo.mp4", headers=self.auth)
        self.assertEqual((r.status_code, r.mimetype), (200, "video/mp4"))
        r.close()
        self.assertEqual(self.app.get("/vila/previdenciario/clipes/plantao.mp4", headers=self.auth).status_code, 404)
        self.assertEqual(e["retratos"], [])
        self.assertEqual(self.app.get("/vila/previdenciario/retratos/neutro.png", headers=self.auth).status_code, 404)
        self.assertEqual(self.app.get("/vila/previdenciario/clipes/..%2F.env.mp4", headers=self.auth).status_code, 404)

    def test_sons(self):
        (self.clipes / "sons").mkdir()
        (self.clipes / "sons" / "sfx-corte.mp3").write_bytes(b"ID3" + b"0" * 64)
        e = self.app.get("/vila/previdenciario/estado", headers=self.auth).get_json()
        self.assertEqual(e["sons"], ["sfx-corte"])
        r = self.app.get("/vila/previdenciario/sons/sfx-corte.mp3", headers=self.auth)
        self.assertEqual((r.status_code, r.mimetype), (200, "audio/mpeg"))
        r.close()
        self.assertEqual(self.app.get("/vila/previdenciario/sons/musica.mp3", headers=self.auth).status_code, 404)
        self.assertEqual(self.app.get("/vila/previdenciario/sons/..%2F..%2F.env.mp3", headers=self.auth).status_code, 404)
        self.assertEqual(self.app.get("/vila/previdenciario/sons/sfx-corte.mp3").status_code, 401)


if __name__ == "__main__":
    unittest.main()
