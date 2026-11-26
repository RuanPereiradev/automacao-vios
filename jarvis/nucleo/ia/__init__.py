"""Escolhe o provedor de IA pelo .env (LLM_PROVEDOR=openai|anthropic|gemini).

Cada provedor expõe responder(sistema, usuario, schema, pesquisar=False) -> dict, sempre com
saída JSON validada pelo schema. Para trocar de provedor basta mudar o .env.
"""


class IAErro(Exception):
    pass


def criar(provedor, modelo, esforco=""):
    provedor = provedor.strip().lower()
    if provedor == "openai":
        from nucleo.ia.openai_ia import OpenAIIA
        return OpenAIIA(modelo, esforco)
    if provedor == "anthropic":
        from nucleo.ia.anthropic_ia import AnthropicIA
        return AnthropicIA(modelo, esforco)
    if provedor == "fila":
        from nucleo.ia.fila_ia import FilaIA
        return FilaIA(modelo, esforco)
    if provedor == "gemini":
        from nucleo.ia.gemini_ia import GeminiIA
        return GeminiIA(modelo, esforco)
    raise IAErro(f"LLM_PROVEDOR inválido: '{provedor}' (use openai, anthropic, gemini ou fila)")
