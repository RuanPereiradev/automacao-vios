"""Vila 07 · Abismo: a cena (bot/vila/abismo.html), a rota /vila/abismo e a aba na vila."""
import base64
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

CENA = RAIZ / "bot" / "vila" / "abismo.html"
VILA = RAIZ / "bot" / "vila" / "vila.html"


class Cena(unittest.TestCase):
    def setUp(self):
        self.html = CENA.read_text(encoding="utf-8")

    def test_tres_classes_e_mapas(self):
        for g in ("g-mago", "g-arq", "g-bar"):
            self.assertIn(f'class="g {g}"', self.html)
        mapas = json.loads(re.search(r"const MAPAS = (\{.*?\});", self.html).group(1))
        usados = set(re.findall(r'data-m="(\w+)"', self.html))
        self.assertTrue(usados)
        self.assertEqual(usados - set(mapas), set())  # todo sprite tem mapa
        for nome, linhas in mapas.items():
            self.assertEqual(len({len(l) for l in linhas}), 1, nome)  # grade retangular

    def test_toda_animacao_definida(self):
        usadas = set(re.findall(r"animation:([\w-]+) ", self.html))
        definidas = set(re.findall(r"@keyframes ([\w-]+)\{", self.html))
        self.assertEqual(usadas - definidas, set())

    def test_sem_dependencia_externa(self):
        # só as fontes do Google; nada de script ou imagem de fora
        self.assertNotRegex(self.html, r'<script[^>]+src=')
        self.assertNotIn("<img", self.html)


class Aba(unittest.TestCase):
    def test_aba_07_ligada(self):
        linhas = VILA.read_text(encoding="utf-8").split("\n")
        t = json.loads(next(l for l in linhas if l.startswith('"<!DOCTYPE html>')))
        self.assertIn("<!--V7:ABISMO-->", t)
        self.assertIn("'07 · Abismo'", t)
        self.assertIn('src="/vila/abismo"', t)
        self.assertIn("abismo: vi === 6,", t)


class Rota(unittest.TestCase):
    def setUp(self):
        try:
            from bot import envio_web
        except ImportError as e:  # Flask/Selenium fora deste Python
            self.skipTest(str(e))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        raiz = Path(self._tmp.name)
        env = raiz / ".env"
        env.write_text("SISTEMA_URL=https://vios.exemplo/\nSISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n"
                       "LOGIN_CAMPO_USUARIO=css:#u\nLOGIN_CAMPO_SENHA=css:#s\n"
                       f"SAIDA_PASTA={raiz / 'saida'}\n", encoding="utf-8")
        self.app = envio_web.criar_app(str(env), senha="senha-da-vila").test_client()
        self.auth = {"Authorization": "Basic " + base64.b64encode(b"x:senha-da-vila").decode()}

    def test_pede_senha(self):
        self.assertEqual(self.app.get("/vila/abismo").status_code, 401)

    def test_serve_a_cena(self):
        r = self.app.get("/vila/abismo", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn("text/html", r.headers["Content-Type"])
        self.assertIn("VILA 07 · ABISMO".encode(), r.data)


if __name__ == "__main__":
    unittest.main()
