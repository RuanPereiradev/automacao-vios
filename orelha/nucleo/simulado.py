"""Modo --simulado: as funções leem orelha/fixtures/<chave>/ em vez do VIOS (sem navegador, sem senha).

Fixtures são 100% fictícias (repo público). Para o simulado fazer sentido em qualquer dia, o texto
da fixture pode ter datas relativas ao dia da execução (ctx.hoje, ou --data):
    {{HOJE}}       -> 04/11/2026        {{HOJE+1}} / {{HOJE-7}}  -> dias depois/antes, DD/MM/AAAA
    {{ISO:HOJE}}   -> 2026-11-04        {{ISO:HOJE-3}}           -> o mesmo, AAAA-MM-DD
Nos testes, prefira data fixa (substituir(texto, date(2026, 11, 4))).

Uso numa função:
    if ctx.simulado:
        html = simulado.ler(ctx, "calendario.html")
    else:
        html = vios.html(ctx, TABELA)
    itens = interpretar(html, ctx.hoje)
"""
import re
from datetime import timedelta
from pathlib import Path

MARCA = re.compile(r"\{\{(ISO:)?HOJE(?:([+-])(\d+))?\}\}")


def substituir(texto, hoje):
    def troca(m):
        dias = int(m.group(3) or 0) * (-1 if m.group(2) == "-" else 1)
        dia = hoje + timedelta(days=dias)
        return dia.isoformat() if m.group(1) else dia.strftime("%d/%m/%Y")
    return MARCA.sub(troca, texto)


def caminho(ctx, nome, chave=None):
    """orelha/fixtures/<chave>/<nome> (chave padrão = a função que está rodando)."""
    return Path(ctx.fixtures) / (chave or ctx.chave) / nome


def ler(ctx, nome, chave=None, datas=True):
    """Texto da fixture (UTF-8), com as marcas {{HOJE...}} trocadas pela data de ctx.hoje.
    Levanta FileNotFoundError com o caminho, se a fixture não existe."""
    texto = caminho(ctx, nome, chave).read_text(encoding="utf-8")
    return substituir(texto, ctx.hoje) if datas else texto


def listar(ctx, padrao="*", chave=None):
    """Arquivos da pasta de fixtures da função, em ordem de nome (sem o .gitkeep)."""
    pasta = Path(ctx.fixtures) / (chave or ctx.chave)
    return sorted(p for p in pasta.glob(padrao) if p.is_file() and p.name != ".gitkeep")
