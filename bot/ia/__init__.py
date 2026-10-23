"""Escolhe o provedor de IA pelo .env (LLM_PROVEDOR=openai|anthropic).

Cada provedor expõe responder(sistema, usuario, schema) -> dict, sempre com
saída JSON validada pelo schema. Para trocar de provedor basta mudar o .env.
"""


class IAErro(Exception):
    pass


def criar(provedor, modelo, esforco=""):
    provedor = provedor.strip().lower()
    if provedor == "openai":
        from bot.ia.openai_ia import OpenAIIA
        return OpenAIIA(modelo, esforco)
    if provedor == "anthropic":
        from bot.ia.anthropic_ia import AnthropicIA
        return AnthropicIA(modelo, esforco)
    raise IAErro(f"LLM_PROVEDOR inválido: '{provedor}' (use openai ou anthropic)")
