"""Albi — explicação de uma classe processual em linguagem simples, pelo Gemini (chave gratuita).

Só é usada quando a classe não está no dicionário fixo de mensagem_cac.py (EXPLICA_CLASSE).
Privacidade: a API recebe APENAS o nome da classe ("Execução de alimentos"); nunca nome, CPF, número
de processo ou partes. A resposta fica em explicacoes_classe.json (uma chamada por classe, para sempre):
o texto é o mesmo em todas as mensagens e pode ser revisado/editado nesse arquivo.
No albi/.env: GEMINI_API_KEY (vazia = desligado) e, se quiser, GEMINI_MODEL. Sem chave, sem internet ou
com qualquer erro, devolve "" e a mensagem sai sem esse parágrafo. Só biblioteca padrão.
"""
import json
import os
import re
import time
import unicodedata
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CACHE = AQUI / "explicacoes_classe.json"
# "-latest" acompanha o modelo atual do Google; os outros entram se o primeiro estiver sobrecarregado
MODELOS = ("gemini-flash-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
PROMPT = ("Explique em UMA frase curta, em português do Brasil e em linguagem simples para um leigo, o que é o "
          "tipo de processo judicial \"{classe}\". Responda só com a frase, começando por um substantivo em "
          "minúsculas e sem ponto final (como \"a cobrança judicial de pensão alimentícia não paga\"). Não cite "
          "pessoas, valores nem resultados, não diga que alguém ganhou, perdeu ou foi condenado, e se não "
          "souber o que é, responda exatamente: DESCONHECIDO")


def _env():
    cfg = {}
    arq = AQUI / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(GEMINI\w*)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("GEMINI")})
    return cfg


def _chave(classe):
    t = unicodedata.normalize("NFKD", classe or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip().upper()


def _ler():
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _chamar(prompt, cfg):
    """Texto do Gemini para o prompt ("" se falhar). Tenta os modelos em ordem; resposta cortada não vale."""
    chave = cfg.get("GEMINI_API_KEY", "").strip()
    if not chave:
        return ""
    corpo = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}}).encode()
    escolhido = cfg.get("GEMINI_MODEL", "").strip()
    for modelo in ((escolhido,) if escolhido else MODELOS):
        try:
            req = urllib.request.Request(URL.format(modelo), data=corpo, method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": chave})
            with urllib.request.urlopen(req, timeout=40) as r:
                dados = json.load(r)
            cand = dados["candidates"][0]
            if cand.get("finishReason") != "STOP":
                continue
            return "".join(p.get("text", "") for p in cand["content"]["parts"]).strip().strip('"')
        except Exception:  # sobrecarga (503), cota, internet: tenta o próximo modelo
            time.sleep(1)
    return ""


def _com_cache(k, prompt, valido):
    cache = _ler()
    if k in cache:
        return cache[k]
    txt = _chamar(prompt, _env())
    if not valido(txt):
        return ""
    cache[k] = txt
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return txt


def explicar(classe):
    """Frase explicando a classe ("a cobrança judicial de ..."), do cache ou do Gemini; "" se não houver."""
    k = _chave(classe)
    if not k:
        return ""

    def valido(t):
        t = t.rstrip(".")
        return (15 <= len(t) <= 300 and "\n" not in t and "DESCONHECIDO" not in t.upper()
                and len(t.split()) >= 4 and t[0].islower())
    txt = _com_cache(k, PROMPT.format(classe=classe.replace('"', "")), valido)
    return txt.rstrip(".")


PROMPT_PARAGRAFO = (
    "Você escreve um trecho de mensagem de um escritório de advocacia para um cliente leigo, em português do "
    "Brasil, em linguagem simples e formal. Dados do processo: tipo = \"{classe}\"; posição da pessoa "
    "pesquisada = \"{papel}\"; situação nos registros = \"{situacao}\".\n"
    "Escreva UM parágrafo de 2 a 4 frases que explique: (1) o que é esse tipo de processo; (2) o que significa a "
    "pessoa estar nessa posição (por exemplo, quem é exequente busca receber, não está sendo cobrado; quem é "
    "réu ou requerido é a parte contra quem o pedido foi feito, o que não significa condenação); (3) o que "
    "significa essa situação em termos simples.\n"
    "Regras: use só o que os dados acima permitem; NÃO invente fatos, valores, datas, nomes nem resultados; "
    "NÃO diga que alguém ganhou, perdeu, pagou, foi condenado ou absolvido; use \"a pessoa pesquisada\" no lugar "
    "de nomes; sem listas, sem markdown, sem asteriscos, sem títulos. Responda só com o parágrafo.")


def paragrafo(classe, papel, situacao):
    """Parágrafo explicativo do processo, gerado pelo Gemini a partir de (classe, posição, situação) e guardado
    no cache: a mesma combinação sempre dá o mesmo texto. "" se não houver chave ou se a resposta não servir."""
    k = f"P|{_chave(classe)}|{_chave(papel)}|{_chave(situacao)}"
    prompt = PROMPT_PARAGRAFO.format(classe=classe.replace('"', ""), papel=papel.replace('"', ""),
                                     situacao=situacao.replace('"', ""))

    def valido(t):
        return (80 <= len(t) <= 900 and "\n" not in t and "*" not in t and "#" not in t and t.endswith(".")
                and not re.search(r"\b(condenad[oa]|ganhou|perdeu|pagou)\b", t, re.I))
    return _com_cache(k, prompt, valido)


if __name__ == "__main__":
    import sys
    print(explicar(" ".join(sys.argv[1:])) or "(sem explicação: confira GEMINI_API_KEY)")
