import json

import anthropic

from bot.ia import IAErro


class AnthropicIA:
    """Anthropic Messages API com saída estruturada (output_config.format).

    A chave vem de ANTHROPIC_API_KEY. No Python 3.8 o SDK fica numa versão que
    ainda não tem output_config nem fallbacks como argumentos, por isso eles vão
    em extra_body/extra_headers. O prompt da skill fica em cache (cache_control).

    Também faz análise em lote (Message Batches API, metade do preço), com a
    mesma interface da OpenAI: enviar_lote(), status(), cancelar(), resultados().
    No lote não há fallbacks (a API recusa): CI recusada vira erro e é refeita
    uma a uma, com fallback.
    """

    suporta_lote = True

    def __init__(self, modelo, esforco=""):
        # 3 min por chamada, até 2 novas tentativas (o padrão do SDK é esperar 10 min)
        self.client = anthropic.Anthropic(timeout=180, max_retries=2)
        self.modelo = modelo
        self.esforco = esforco

    def _corpo(self, sistema, usuario, schema, pesquisar=False):
        output_config = {"format": {"type": "json_schema", "schema": schema}}
        if self.esforco:
            output_config["effort"] = self.esforco
        corpo = {
            "model": self.modelo,
            "max_tokens": 16000,
            "system": [{"type": "text", "text": sistema, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": usuario}],
            "output_config": output_config,
        }
        if pesquisar:
            # a versão nova da busca (filtro dinâmico) não existe no Haiku
            tipo = "web_search_20250305" if "haiku" in self.modelo else "web_search_20260209"
            corpo["tools"] = [{"type": tipo, "name": "web_search", "max_uses": 6,
                               "user_location": {"type": "approximate", "country": "BR"}}]
        return corpo

    def responder(self, sistema, usuario, schema, pesquisar=False):
        """pesquisar=True libera a pesquisa na web (ferramenta web_search do servidor)."""
        corpo = self._corpo(sistema, usuario, schema, pesquisar)
        extra = {"output_config": corpo.pop("output_config")}
        cabecalhos = {}
        if "haiku" not in self.modelo:
            # se o modelo recusar, a própria API tenta outro modelo (o Haiku não tem esse recurso)
            extra["fallbacks"] = "default"
            cabecalhos["anthropic-beta"] = "server-side-fallback-2026-07-01"
        r = self.client.messages.create(**corpo, extra_headers=cabecalhos, extra_body=extra)
        return _ler_mensagem(r)

    # ---- lote (Message Batches API) ----

    def enviar_lote(self, sistema, pedidos, schema, descricao=""):
        """pedidos = [(id, texto do usuário)]. Devolve o id do lote na Anthropic."""
        lote = self.client.messages.batches.create(
            requests=[{"custom_id": pid, "params": self._corpo(sistema, usuario, schema)} for pid, usuario in pedidos])
        return lote.id

    def status(self, lote_id):
        """Devolve (status, concluídos, com erro, total) com os nomes de status da OpenAI
        ("completed" quando o lote termina), para o resto do programa não mudar."""
        b = self.client.messages.batches.retrieve(lote_id)
        c = b.request_counts
        falhas = c.errored + c.canceled + c.expired
        total = c.processing + c.succeeded + falhas
        return ("completed" if b.processing_status == "ended" else "in_progress"), c.succeeded, falhas, total

    def cancelar(self, lote_id):
        self.client.messages.batches.cancel(lote_id)

    def resultados(self, lote_id):
        """{id: dados} do lote terminado; pedido com falha vira IAErro no lugar dos dados."""
        saida = {}
        for item in self.client.messages.batches.results(lote_id):
            r = item.result
            if r.type == "succeeded":
                try:
                    saida[item.custom_id] = _ler_mensagem(r.message)
                except (IAErro, ValueError) as e:
                    saida[item.custom_id] = IAErro(str(e))
            elif r.type == "errored":
                erro = getattr(r.error, "error", r.error)
                saida[item.custom_id] = IAErro(f"{getattr(erro, 'type', '')}: {getattr(erro, 'message', erro)}")
            else:
                saida[item.custom_id] = IAErro(f"pedido do lote {r.type}")  # canceled / expired
        return saida


def _ler_mensagem(r):
    """Resposta da Messages API -> dados do JSON + _uso."""
    if r.stop_reason == "refusal":
        raise IAErro("Anthropic recusou a análise (stop_reason=refusal)")
    if r.stop_reason == "max_tokens":
        raise IAErro("Resposta cortada por max_tokens")
    # com pesquisa a resposta vem em vários blocos; o JSON é o último texto
    texto = next((b.text for b in reversed(r.content) if b.type == "text"), "")
    if not texto:
        raise IAErro("Anthropic não devolveu texto")
    u = r.usage
    dados = json.loads(texto)
    dados["_uso"] = {
        "entrada": u.input_tokens + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0),
        "entrada_cache": u.cache_read_input_tokens or 0,
        "saida": u.output_tokens,
        "buscas": getattr(getattr(u, "server_tool_use", None), "web_search_requests", 0) or 0,
    }
    return dados
