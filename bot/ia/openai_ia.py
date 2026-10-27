import io
import json

from openai import OpenAI

from bot.ia import IAErro


class OpenAIIA:
    """OpenAI Responses API com Structured Outputs (json_schema strict).

    A chave vem de OPENAI_API_KEY. O prompt da skill é sempre o mesmo, então a
    OpenAI reaproveita o cache entre as intimações (prompt_cache_key ajuda).

    Também faz análise em lote (Batch API, metade do preço): enviar_lote() manda
    todos os pedidos num arquivo JSONL, status() acompanha e resultados() lê as
    respostas quando o lote termina (prazo da OpenAI: até 24 h, em geral minutos).
    """

    suporta_lote = True

    def __init__(self, modelo, esforco=""):
        # 3 min por chamada, até 2 novas tentativas (o padrão do SDK é esperar 10 min)
        self.client = OpenAI(timeout=180, max_retries=2)
        self.modelo = modelo
        self.esforco = esforco

    def _corpo(self, sistema, usuario, schema, pesquisar=False):
        corpo = {
            "model": self.modelo,
            "instructions": sistema,
            "input": usuario,
            "text": {"format": {"type": "json_schema", "name": "analise_intimacao", "schema": schema, "strict": True}},
            "prompt_cache_key": "pesquisa-feriados" if pesquisar else "analise-intimacoes",
        }
        if self.esforco:
            corpo["reasoning"] = {"effort": self.esforco}
        if pesquisar:
            # pesquisa barata: poucas buscas e só o trecho relevante das páginas (o grosso do custo)
            corpo["tools"] = [{"type": "web_search", "search_context_size": "low",
                               "user_location": {"type": "approximate", "country": "BR"}}]
            corpo["max_tool_calls"] = 6
        return corpo

    def responder(self, sistema, usuario, schema, pesquisar=False):
        """pesquisar=True libera a pesquisa na web (ferramenta web_search)."""
        r = self.client.responses.create(**self._corpo(sistema, usuario, schema, pesquisar))
        if r.status != "completed" or not r.output_text:
            raise IAErro(f"OpenAI não completou a resposta (status={r.status}, detalhes={r.incomplete_details})")
        uso = r.usage
        cache = getattr(getattr(uso, "input_tokens_details", None), "cached_tokens", 0) if uso else 0
        dados = json.loads(r.output_text)
        dados["_uso"] = {"entrada": uso.input_tokens, "entrada_cache": cache, "saida": uso.output_tokens} if uso else {}
        return dados

    # ---- lote (Batch API) ----

    def enviar_lote(self, sistema, pedidos, schema, descricao=""):
        """pedidos = [(id, texto do usuário)]. Devolve o id do lote na OpenAI."""
        linhas = [
            json.dumps({"custom_id": pid, "method": "POST", "url": "/v1/responses",
                        "body": self._corpo(sistema, usuario, schema)}, ensure_ascii=False)
            for pid, usuario in pedidos
        ]
        arquivo = io.BytesIO(("\n".join(linhas) + "\n").encode("utf-8"))
        arquivo.name = "lote.jsonl"
        enviado = self.client.files.create(file=arquivo, purpose="batch")
        lote = self.client.batches.create(input_file_id=enviado.id, endpoint="/v1/responses",
                                          completion_window="24h", metadata={"descricao": descricao[:500]})
        return lote.id

    def status(self, lote_id):
        """Devolve (status, concluídos, com erro, total). Status final: completed, failed, expired, cancelled."""
        b = self.client.batches.retrieve(lote_id)
        c = b.request_counts
        if b.status == "failed" and b.errors and b.errors.data:
            raise IAErro("Lote recusado pela OpenAI: " + "; ".join(f"{e.code}: {e.message}" for e in b.errors.data))
        return b.status, (c.completed if c else 0), (c.failed if c else 0), (c.total if c else 0)

    def cancelar(self, lote_id):
        self.client.batches.cancel(lote_id)

    def resultados(self, lote_id):
        """{id: dados} das respostas prontas; pedido com falha vira IAErro no lugar dos dados.
        Funciona também em lote cancelado ou expirado (devolve só o que ficou pronto)."""
        b = self.client.batches.retrieve(lote_id)
        saida = {}
        for arquivo_id in (b.output_file_id, b.error_file_id):
            if not arquivo_id:
                continue
            for linha in self.client.files.content(arquivo_id).text.splitlines():
                if linha.strip():
                    item = json.loads(linha)
                    saida[item["custom_id"]] = _ler_item(item)
        return saida


def _ler_item(item):
    """Uma linha do arquivo de saída/erros do lote -> dados ou IAErro."""
    if item.get("error"):
        return IAErro(f"{item['error'].get('code')}: {item['error'].get('message')}")
    resposta = item.get("response") or {}
    corpo = resposta.get("body") or {}
    if resposta.get("status_code") != 200:
        erro = corpo.get("error") or {}
        return IAErro(f"HTTP {resposta.get('status_code')} {erro.get('code', '')}: {erro.get('message', corpo)}")
    if corpo.get("status") != "completed":
        return IAErro(f"OpenAI não completou a resposta (status={corpo.get('status')}, detalhes={corpo.get('incomplete_details')})")
    texto = "".join(
        c.get("text", "")
        for o in corpo.get("output", []) if o.get("type") == "message"
        for c in o.get("content", []) if c.get("type") == "output_text"
    )
    if not texto:
        return IAErro("OpenAI não devolveu texto")
    dados = json.loads(texto)
    uso = corpo.get("usage") or {}
    dados["_uso"] = {"entrada": uso.get("input_tokens", 0),
                     "entrada_cache": (uso.get("input_tokens_details") or {}).get("cached_tokens", 0),
                     "saida": uso.get("output_tokens", 0)}
    return dados
