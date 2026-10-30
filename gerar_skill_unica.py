"""Monta a skill em arquivo único (para o chat de validação da Controladoria).

SKILL.md + as 4 referências como seções + doc/skill-unica/regras-do-programa.md
(o que o bot faz no código) + doc/skill-unica/arquivo-para-o-robo.md (formato do .txt
da página de envio). Gera também o .zip para subir no chat.

uso: python gerar_skill_unica.py
"""
import re
import sys
import zipfile
from pathlib import Path

from bot.skill import REFERENCIAS

ORIGEM = Path("doc/analise-intimacoes-controladoria")
DESTINO = Path("doc/skill-unica")
REGRAS_PROGRAMA = DESTINO / "regras-do-programa.md"
ARQUIVO_ROBO = DESTINO / "arquivo-para-o-robo.md"


def _apontar(texto, titulos):
    """Troca "references/x.md" por "seção "Referência — Título" (mais abaixo)"."""
    for nome, titulo in titulos.items():
        secao = f"seção \"Referência — {titulo}\" (mais abaixo)"
        for antigo in (f"`references/{nome}`", f"references/{nome}", f"`{nome}`", nome):
            texto = texto.replace(antigo, secao)
    texto = texto.replace("a regra obrigatória do SKILL.md", "a regra obrigatória da parte principal desta skill")
    return texto.replace("a regra do SKILL.md", "a regra da parte principal desta skill")


def _rebaixar(texto):
    """Título da referência vira "## Referência — ..." e os demais títulos descem um nível
    (fora dos blocos de código)."""
    saida, cerca = [], False
    for linha in texto.splitlines():
        if linha.lstrip().startswith("```"):
            cerca = not cerca
        elif not cerca and re.match(r"#{1,5} ", linha):
            linha = "## Referência — " + linha[2:] if linha.startswith("# ") else "#" + linha
        saida.append(linha)
    texto = "\n".join(saida)
    return texto.replace("Use este arquivo", "Use esta seção").replace("neste arquivo", "nesta seção")


def gerar():
    skill = (ORIGEM / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"\A(---\n.*?\n---\n)(.*)\Z", skill, flags=re.S)
    cabecalho, corpo = m.group(1).strip(), m.group(2).strip()
    refs = {nome: (ORIGEM / "references" / nome).read_text(encoding="utf-8").strip() for nome in REFERENCIAS}
    titulos = {nome: re.match(r"# (.+)", texto).group(1).strip() for nome, texto in refs.items()}

    partes = [cabecalho, "", _apontar(corpo, titulos)]
    partes += [p for nome in REFERENCIAS for p in ("", _rebaixar(_apontar(refs[nome], titulos)))]
    partes += [p for extra in (REGRAS_PROGRAMA, ARQUIVO_ROBO) for p in ("", extra.read_text(encoding="utf-8").strip())]
    partes.append("")

    pasta = DESTINO / "analise-intimacoes-controladoria"
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / "SKILL.md"
    arquivo.write_text("\n".join(partes), encoding="utf-8")
    pacote = DESTINO / "analise-intimacoes-controladoria.zip"
    with zipfile.ZipFile(pacote, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(arquivo, "analise-intimacoes-controladoria/SKILL.md")
    return arquivo, pacote


if __name__ == "__main__":
    arquivo, pacote = gerar()
    print(f"{arquivo} e {pacote} gerados")
    sys.exit(0)
