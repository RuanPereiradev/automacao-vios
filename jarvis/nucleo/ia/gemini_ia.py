import json
import os
import time
import urllib.error
import urllib.request

from nucleo.ia import IAErro

API = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
ESPERAS = (5, 15, 30, 60)  # segundos entre novas tentativas quando o Gemini está sobrecarregado (503/429/500)


class GeminiIA:
    """Google Gemini (API generateContent) com saída JSON validada pelo schema (responseJsonSchema).

    A chave vem de GEMINI_API_KEY (vai no cabeçalho x-goog-api-key, nunca na URL nem no log). Usa só a
    biblioteca padrão do Python (urllib): não precisa instalar nada. Sem análise em lote (suporta_lote=False):
    cada processo é uma chamada. LLM_ESFORCO (low/medium/high) vira o thinkingLevel do modelo.
    Conferido em 24/11/2026 com a chave do escritório: models.list ok; os modelos Flash respondiam 503
    (alta demanda) em alguns horários, por isso as novas tentativas com espera.
    """

    suporta_lote = False

    def __init__(self, modelo, esforco=""):
        self.chave = os.getenv("GEMINI_API_KEY", "").strip()
        if not self.chave:
            raise IAErro("GEMINI_API_KEY não está no .env do Jarvis (api_key)")
        self.modelo = modelo
        self.esforco = esforco

    def _corpo(self, sistema, usuario, schema, pesquisar=False):
        config = {"responseMimeType": "application/json", "responseJsonSchema": schema, "maxOutputTokens": 16000}
        if self.esforco:
            config["thinkingConfig"] = {"thinkingLevel": self.esforco}
        corpo = {
            "systemInstruction": {"parts": [{"text": sistema}]},
            "contents": [{"role": "user", "parts": [{"text": usuario}]}],
            "generationConfig": config,
        }
        if pesquisar:
            corpo["tools"] = [{"google_search": {}}]
        return corpo

    def _chamar(self, corpo):
        dados = json.dumps(corpo).encode("utf-8")
        ultimo = None
        for espera in ESPERAS + (None,):
            req = urllib.request.Request(API.format(modelo=self.modelo), data=dados, method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": self.chave})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                try:
                    erro = json.loads(e.read().decode("utf-8")).get("error", {})
                except ValueError:
                    erro = {}
                ultimo = IAErro(f"Gemini {e.code} {erro.get('status', '')}: {erro.get('message', '')[:200]}")
                if e.code not in (429, 500, 503) or espera is None:
                    raise ultimo
            except (urllib.error.URLError, TimeoutError) as e:
                ultimo = IAErro(f"Gemini sem resposta (timeout): {e}")
                if espera is None:
                    raise ultimo
            time.sleep(espera)
        raise ultimo

    def responder(self, sistema, usuario, schema, pesquisar=False):
        return _ler_resposta(self._chamar(self._corpo(sistema, usuario, schema, pesquisar)))


def _ler_resposta(r):
    """Resposta do generateContent -> dados do JSON + _uso."""
    if (r.get("promptFeedback") or {}).get("blockReason"):
        raise IAErro(f"Gemini recusou a análise ({r['promptFeedback']['blockReason']})")
    cands = r.get("candidates") or []
    if not cands:
        raise IAErro("Gemini não devolveu resposta")
    c = cands[0]
    fim = c.get("finishReason", "")
    if fim == "MAX_TOKENS":
        raise IAErro("Resposta cortada por max_tokens")
    if fim in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"):
        raise IAErro(f"Gemini recusou a análise (finishReason={fim})")
    texto = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts", []) if not p.get("thought"))
    if not texto:
        raise IAErro("Gemini não devolveu texto")
    dados = json.loads(texto)
    u = r.get("usageMetadata") or {}
    dados["_uso"] = {
        "entrada": u.get("promptTokenCount", 0),
        "entrada_cache": u.get("cachedContentTokenCount", 0),
        # o "pensamento" do modelo é cobrado como saída
        "saida": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0),
        "buscas": 0,
    }
    return dados
