"""Adaptador do Gemini (nucleo/ia/gemini_ia.py) com a API simulada: corpo, leitura, uso e novas tentativas."""
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nucleo import ia  # noqa: E402
from nucleo.ia import gemini_ia as G  # noqa: E402

SCHEMA = {"type": "object", "properties": {"resumo_caso": {"type": "string"}}, "required": ["resumo_caso"],
          "additionalProperties": False}
OK = {"candidates": [{"content": {"parts": [{"text": "pensando...", "thought": True},
                                            {"text": json.dumps({"resumo_caso": "Horas extras."})}]},
                      "finishReason": "STOP"}],
      "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20, "thoughtsTokenCount": 300}}


class Resposta(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def erro_http(codigo, status):
    corpo = json.dumps({"error": {"status": status, "message": "x"}}).encode()
    return urllib.error.HTTPError("u", codigo, "e", {}, io.BytesIO(corpo))


class Gemini(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "chave-de-teste"})
        p.start()
        self.addCleanup(p.stop)

    def test_criar_e_sem_chave(self):
        self.assertIsInstance(ia.criar("gemini", "gemini-3.6-flash"), G.GeminiIA)
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(ia.IAErro, "GEMINI_API_KEY"):
                ia.criar("gemini", "gemini-3.6-flash")

    def test_responder(self):
        vistos = []

        def abrir(req, timeout):
            vistos.append(req)
            return Resposta(json.dumps(OK).encode())
        with mock.patch.object(G.urllib.request, "urlopen", abrir):
            r = G.GeminiIA("gemini-3.6-flash", "low").responder("sistema", "processo", SCHEMA)
        self.assertEqual(r["resumo_caso"], "Horas extras.")
        self.assertEqual(r["_uso"], {"entrada": 100, "entrada_cache": 0, "saida": 320, "buscas": 0})
        req = vistos[0]
        self.assertIn("gemini-3.6-flash:generateContent", req.full_url)
        self.assertNotIn("chave-de-teste", req.full_url)                      # a chave vai no cabeçalho
        self.assertEqual(req.get_header("X-goog-api-key"), "chave-de-teste")
        corpo = json.loads(req.data)
        self.assertEqual(corpo["generationConfig"]["responseJsonSchema"], SCHEMA)
        self.assertEqual(corpo["generationConfig"]["thinkingConfig"], {"thinkingLevel": "low"})

    def test_tenta_de_novo_com_503(self):
        respostas = [erro_http(503, "UNAVAILABLE"), Resposta(json.dumps(OK).encode())]

        def abrir(req, timeout):
            r = respostas.pop(0)
            if isinstance(r, Exception):
                raise r
            return r
        with mock.patch.object(G.urllib.request, "urlopen", abrir), mock.patch.object(G.time, "sleep"):
            r = G.GeminiIA("gemini-3.6-flash").responder("s", "u", SCHEMA)
        self.assertEqual(r["resumo_caso"], "Horas extras.")

    def test_erro_sem_nova_tentativa_e_motivo(self):
        def abrir(req, timeout):
            raise erro_http(400, "INVALID_ARGUMENT")
        with mock.patch.object(G.urllib.request, "urlopen", abrir):
            with self.assertRaisesRegex(ia.IAErro, "INVALID_ARGUMENT"):
                G.GeminiIA("gemini-3.6-flash").responder("s", "u", SCHEMA)

    def test_cortada_e_bloqueada(self):
        with self.assertRaisesRegex(ia.IAErro, "max_tokens"):
            G._ler_resposta({"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]})
        with self.assertRaisesRegex(ia.IAErro, "recusou"):
            G._ler_resposta({"promptFeedback": {"blockReason": "SAFETY"}})


if __name__ == "__main__":
    unittest.main()
