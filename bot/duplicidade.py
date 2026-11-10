"""Duplicatas: a mesma publicação capturada em mais de uma CI do mesmo processo.

No VIOS é comum o mesmo ato vir duas vezes, uma para cada parte (ex.: uma endereçada
ao reclamante e outra ao nosso cliente). O texto é praticamente igual: muda o
destinatário, o link e o código da comunicação.

Regra (skill, references/roteamento-interno.md): a CI mais completa é a original e
a outra é ignorada (não gera tarefa). Ordem para escolher a original:
1. a endereçada ao cliente (as palavras que só ela tem batem com o nome do cliente);
2. a de texto mais completo (mais palavras);
3. a de número de CI menor.
"""
import difflib
import os
import re
import unicodedata

CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
MAX_PALAVRAS_DIFERENTES = 10  # acima disso é outro ato do mesmo processo, não duplicata
IGNORAR_NO_NOME = {"LTDA", "ME", "EPP", "SA", "DE", "DA", "DO", "DOS", "DAS", "E", "MATRIZ", "FILIAL"}


def _normalizar(texto):
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().upper()


def teor(texto):
    """Só o teor: tira o cabeçalho de datas ("Data da Disponibilização..." na captura,
    "Disponibilização:..." na tela de lançamento) e o que vem depois do comunicacao_id
    (Comarca, Diário, Esfera na tela de lançamento)."""
    texto = texto or ""
    inicio = re.search(r"Publica[cç][aã]o\s+Processo", texto, re.I)
    if inicio:
        texto = texto[inicio.start():]
    fim = re.search(r"comunicacao_id:\s*\d+\s*\|?", texto)
    return texto[:fim.end()] if fim else texto


def palavras(texto):
    """Palavras do teor sem links, números e códigos (que mudam entre as cópias)."""
    texto = re.sub(r"https?://\S+", " ", _normalizar(teor(texto)))
    texto = re.sub(r"\S*\d\S*", " ", texto)
    return re.findall(r"[A-Z]+", texto)


def comparar(texto_a, texto_b):
    """(semelhança 0-1, palavras diferentes, só em A, só em B)."""
    a, b = palavras(texto_a), palavras(texto_b)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    so_a, so_b, diferentes = [], [], 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            diferentes += max(i2 - i1, j2 - j1)
            so_a += a[i1:i2]
            so_b += b[j1:j2]
    return sm.ratio(), diferentes, so_a, so_b


def _do_cliente(trecho, cliente):
    """Quantas palavras do trecho batem com o nome do cliente (inclui iniciais: D.D.E.L.L.)."""
    nome = re.sub(r"\(.*?\)|:.*$", " ", _normalizar(cliente))  # tira "(MATRIZ)" e ": PRESTADORA"
    tokens = re.findall(r"[A-Z]+", nome)
    pontos = sum(1 for p in trecho if len(p) > 1 and p in tokens and p not in IGNORAR_NO_NOME)
    letras = "".join(p for p in trecho if len(p) == 1)
    if len(letras) >= 3 and letras in "".join(t[0] for t in tokens):
        pontos += len(letras)
    return pontos


def ligado():
    """DUPLICIDADE_ATIVA no .env. Desligado por padrão desde 10/11/2026: a Controladoria já tira
    as duplicadas no VIOS (tela de intimações), e o detector marcava como cópia CIs que não eram."""
    return os.getenv("DUPLICIDADE_ATIVA", "false").strip().lower() in ("true", "1", "sim")


def detectar(itens):
    """itens = capturas do VIOS. Devolve {ci_duplicada: {...}} com a original de cada uma.
    Com o detector desligado (DUPLICIDADE_ATIVA=false, padrão), devolve {}: nada é cópia."""
    if not ligado():
        return {}
    por_processo = {}
    for i in itens:
        achado = CNJ.search(i.get("numeros", ""))
        if achado and i.get("texto"):
            por_processo.setdefault(achado.group(), []).append(i)

    resultado = {}
    for grupo in por_processo.values():
        grupo = sorted(grupo, key=lambda i: int(i["ci"]))
        for n, a in enumerate(grupo):
            for b in grupo[n + 1:]:
                if a["ci"] in resultado or b["ci"] in resultado:
                    continue
                semelhanca, diferentes, so_a, so_b = comparar(a["texto"], b["texto"])
                if diferentes > MAX_PALAVRAS_DIFERENTES:
                    continue
                pa, pb = _do_cliente(so_a, a.get("cliente", "")), _do_cliente(so_b, b.get("cliente", ""))
                if pa != pb:
                    original, copia = (a, b) if pa > pb else (b, a)
                    motivo = "endereçada ao cliente"
                elif len(palavras(a["texto"])) != len(palavras(b["texto"])):
                    original, copia = (a, b) if len(palavras(a["texto"])) > len(palavras(b["texto"])) else (b, a)
                    motivo = "texto mais completo"
                else:
                    original, copia, motivo = a, b, "mesmo texto; mantida a CI de número menor"
                trecho_orig, trecho_copia = (so_a, so_b) if original is a else (so_b, so_a)
                resultado[copia["ci"]] = {
                    "original": original["ci"],
                    "motivo": motivo,
                    "semelhanca": round(semelhanca, 3),
                    "so_na_original": " ".join(trecho_orig),
                    "so_nesta": " ".join(trecho_copia),
                }
    # duplicata de duplicata aponta para a original de verdade
    for d in resultado.values():
        while d["original"] in resultado:
            d["original"] = resultado[d["original"]]["original"]
    return resultado


def marcar(itens):
    """Marca nas capturas a cópia (duplicada_de = CI original). Devolve o resultado de detectar()."""
    duplicadas = detectar(itens)
    for i in itens:
        d = duplicadas.get(i.get("ci"))
        if d:
            i["duplicada_de"] = d["original"]
            i["duplicidade_motivo"] = d["motivo"]
        else:
            i.pop("duplicada_de", None)
            i.pop("duplicidade_motivo", None)
    return duplicadas
