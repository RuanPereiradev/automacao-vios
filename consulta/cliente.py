"""Cliente HTTP do bot (CONTRATO.md, seção 2). Só biblioteca padrão. Só o Mac chama o bot (saída).

Nunca escreve corpo, cabeçalho ou assinatura em log.
"""
import json
import logging
import time
import urllib.error
import urllib.request

from consulta.cripto import assinar

log = logging.getLogger("consulta")

CAMINHO_PENDENTES = "/consulta/pendentes"
CAMINHO_RESULTADO = "/consulta/resultado"


class BotErro(Exception):
    """Falha ao falar com o bot (rede, 401, 404, 5xx). A mensagem não tem dado do cliente."""


def corpo_json(dados):
    """JSON compacto: o MESMO texto é assinado e enviado."""
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":"))


class ClienteBot:
    def __init__(self, base_url, segredo, timeout=15, agora_ms=None, abrir=None):
        self.base = base_url.rstrip("/")
        self.segredo = segredo
        self.timeout = timeout
        self._agora_ms = agora_ms or (lambda: int(time.time() * 1000))
        self._abrir = abrir or urllib.request.urlopen  # trocável nos testes

    def cabecalhos(self, metodo, caminho, corpo=""):
        ts = str(self._agora_ms())
        return {"X-Consulta-Timestamp": ts,
                "X-Consulta-Assinatura": assinar(self.segredo, ts, metodo, caminho, corpo)}

    def _chamar(self, metodo, caminho, corpo=""):
        cab = self.cabecalhos(metodo, caminho, corpo)
        dados = corpo.encode("utf-8") if metodo == "POST" else None
        if dados is not None:
            cab["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(self.base + caminho, data=dados, headers=cab, method=metodo)
        try:
            with self._abrir(req, timeout=self.timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise BotErro(f"sem conexão com o bot ({e.__class__.__name__})") from None

    def pendentes(self):
        """GET /consulta/pendentes -> [{"id", "cpfCifrado"}] (até 5)."""
        status, corpo = self._chamar("GET", CAMINHO_PENDENTES)
        if status == 401:
            raise BotErro("o bot recusou a assinatura (401): confira CONSULTA_SEGREDO e o relógio")
        if status == 404:
            raise BotErro("rota desligada no bot (404): CONSULTA_PROCESSO não está ligada")
        if status != 200:
            raise BotErro(f"o bot respondeu {status} em /consulta/pendentes")
        try:
            pedidos = json.loads(corpo.decode("utf-8")).get("pedidos", [])
            return [{"id": str(p["id"]), "cpfCifrado": str(p["cpfCifrado"])} for p in pedidos]
        except (ValueError, KeyError, TypeError, AttributeError):
            raise BotErro("resposta de /consulta/pendentes fora do formato") from None

    def enviar_resultado(self, resultado):
        """POST /consulta/resultado. True se aceito; False se 410 (pedido expirado)."""
        status, _ = self._chamar("POST", CAMINHO_RESULTADO, corpo_json(resultado))
        if status == 200:
            return True
        if status == 410:
            return False
        if status == 401:
            raise BotErro("o bot recusou a assinatura (401) ao enviar o resultado")
        if status == 422:
            raise BotErro("o bot recusou o formato do resultado (422)")
        raise BotErro(f"o bot respondeu {status} em /consulta/resultado")
