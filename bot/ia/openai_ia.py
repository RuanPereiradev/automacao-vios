import json

from openai import OpenAI

from bot.ia import IAErro


class OpenAIIA:
    """OpenAI Responses API com Structured Outputs (json_schema strict).

    A chave vem de OPENAI_API_KEY. O prompt da skill é sempre o mesmo, então a
    OpenAI reaproveita o cache entre as intimações (prompt_cache_key ajuda).
    """

    def __init__(self, modelo, esforco=""):
        # 3 min por chamada, até 2 novas tentativas (o padrão do SDK é esperar 10 min)
        self.client = OpenAI(timeout=180, max_retries=2)
        self.modelo = modelo
        self.esforco = esforco

    def responder(self, sistema, usuario, schema):
        extra = {"reasoning": {"effort": self.esforco}} if self.esforco else {}
        r = self.client.responses.create(
            model=self.modelo,
            instructions=sistema,
            input=usuario,
            text={"format": {"type": "json_schema", "name": "analise_intimacao", "schema": schema, "strict": True}},
            prompt_cache_key="analise-intimacoes",
            **extra,
        )
        if r.status != "completed" or not r.output_text:
            raise IAErro(f"OpenAI não completou a resposta (status={r.status}, detalhes={r.incomplete_details})")
        uso = r.usage
        cache = getattr(getattr(uso, "input_tokens_details", None), "cached_tokens", 0) if uso else 0
        dados = json.loads(r.output_text)
        dados["_uso"] = {"entrada": uso.input_tokens, "entrada_cache": cache, "saida": uso.output_tokens} if uso else {}
        return dados
