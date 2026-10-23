import json

import anthropic

from bot.ia import IAErro


class AnthropicIA:
    """Anthropic Messages API com saída estruturada (output_config.format).

    A chave vem de ANTHROPIC_API_KEY. No Python 3.8 o SDK fica numa versão que
    ainda não tem output_config nem fallbacks como argumentos, por isso eles vão
    em extra_body/extra_headers. O prompt da skill fica em cache (cache_control).
    """

    def __init__(self, modelo, esforco=""):
        # 3 min por chamada, até 2 novas tentativas (o padrão do SDK é esperar 10 min)
        self.client = anthropic.Anthropic(timeout=180, max_retries=2)
        self.modelo = modelo
        self.esforco = esforco

    def responder(self, sistema, usuario, schema):
        output_config = {"format": {"type": "json_schema", "schema": schema}}
        if self.esforco:
            output_config["effort"] = self.esforco
        r = self.client.messages.create(
            model=self.modelo,
            max_tokens=16000,
            system=[{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": usuario}],
            # se o modelo recusar, a própria API tenta outro modelo
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": output_config, "fallbacks": "default"},
        )
        if r.stop_reason == "refusal":
            raise IAErro("Anthropic recusou a análise (stop_reason=refusal)")
        if r.stop_reason == "max_tokens":
            raise IAErro("Resposta cortada por max_tokens")
        texto = next((b.text for b in r.content if b.type == "text"), "")
        if not texto:
            raise IAErro("Anthropic não devolveu texto")
        u = r.usage
        dados = json.loads(texto)
        dados["_uso"] = {
            "entrada": u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0),
            "entrada_cache": u.cache_read_input_tokens or 0,
            "saida": u.output_tokens,
        }
        return dados
