"""Relatório mensal de processos em PDF, no timbrado do escritório (bot/timbrado/).

Sai junto com a planilha: <GRUPO>.pdf ao lado de <GRUPO>.xlsx, com as mesmas linhas
(montar_linha) — capa com os números do mês, a página "Resumo do mês" escrita pela IA
(uma chamada por grupo) e uma ficha por processo. As posições do cabeçalho, do rodapé, da
marca d'água e as margens são as do Timbrado_RFeitosa_Advogados_COM_MARCADOR.docx.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bot.relatorio_planilha import CONDENACOES

PASTA = Path(__file__).parent / "timbrado"
VINHO = colors.HexColor("#6b1414")
DOURADO = colors.HexColor("#d9b648")
CINZA = colors.HexColor("#5f5f5f")
LINHA = colors.HexColor("#e6dcc0")
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]

# timbrado (do .docx): imagens com a largura da página; margens em pontos (twips / 20)
LARGURA, ALTURA = A4
FAIXA = 1440180 / 12700  # altura do cabeçalho e do rodapé
MARGENS = {"topMargin": 2608 / 20, "bottomMargin": 2268 / 20, "leftMargin": 1701 / 20, "rightMargin": 1134 / 20}

# Garamond, como no timbrado; sem ela no computador, Times (também com serifa)
FONTES = {
    "normal": ["C:/Windows/Fonts/GARA.TTF", "/Library/Fonts/Garamond.ttf",
               "/Applications/Microsoft Word.app/Contents/Resources/DFonts/Garamond.ttf"],
    "negrito": ["C:/Windows/Fonts/GARABD.TTF", "/Library/Fonts/Garamond Bold.ttf",
                "/Applications/Microsoft Word.app/Contents/Resources/DFonts/Garamond Bold.ttf"],
    "italico": ["C:/Windows/Fonts/GARAIT.TTF", "/Library/Fonts/Garamond Italic.ttf",
                "/Applications/Microsoft Word.app/Contents/Resources/DFonts/Garamond Italic.ttf"],
}
RESERVA = {"normal": "Times-Roman", "negrito": "Times-Bold", "italico": "Times-Italic"}

# --- "Resumo do mês" pela IA (uma chamada por grupo) ---
SISTEMA_MES = """Você recebe as fichas dos processos de UM grupo de empresas (cliente do escritório
de advocacia) no mês: tipo, polo, motivação, resultado da decisão e o resumo de cada caso.
Escreva a página "Resumo do mês" de um relatório em PDF que vai para o cliente (leigo).
Responda só com o JSON pedido.

Regras:
- paragrafos: 2 a 4 parágrafos curtos, linguagem simples, sem juridiquês. Diga quantos
  processos há, de que tipo, os motivos mais comuns, como estão as decisões (condenações,
  pedidos improcedentes, acordos, sem decisão) e o que ainda depende do cliente (documentos
  faltando), se houver.
- Use só os números e fatos das fichas; não invente nem use conhecimento externo.
- Não cite nomes de pessoas, CPF, números de processo, links ou nomes de funcionários do escritório.
- Escreva só fatos: NUNCA opiniões, avaliações ou estratégias internas do escritório, nem
  recomendações ao cliente (ex.: "não vale a pena recorrer", "chances de êxito", "tese defensiva").
"""
SCHEMA_MES = {
    "type": "object",
    "properties": {"paragrafos": {"type": "array", "items": {"type": "string"}}},
    "required": ["paragrafos"],
    "additionalProperties": False,
}
MAX_MES = 60000  # caracteres das fichas mandadas à IA


def _ok(valor):
    """Texto que pode ir para o cliente (sem vazio e sem a marca de erro da IA)."""
    return valor not in (None, "") and not str(valor).startswith("ERRO NA IA")


def texto_mes(grupo, linhas):
    fichas = []
    for l in linhas:
        partes = [f"Tipo: {l['Tipo de processo'] or 'não informado'}", f"Polo do cliente: {l['Polo do cliente'] or '-'}"]
        for campo in ("Motivação do processo", "Justificativa da condenação", "Pendência — documentos faltando",
                      "Resumo do caso"):
            if _ok(l[campo]):
                partes.append(f"{campo}: {l[campo]}")
        if l.get("_condenacao"):
            partes.append(f"Resultado da decisão: {l['_condenacao']}")
        fichas.append(" | ".join(partes))
    texto = f"Grupo: {grupo}\nProcessos: {len(linhas)}\n\n" + "\n".join(f"- {f}" for f in fichas)
    return texto[:MAX_MES]


# --- PDF ---
def _fontes():
    nomes = {}
    for tipo, caminhos in FONTES.items():
        achou = next((c for c in caminhos if Path(c).exists()), None)
        if achou:
            nome = f"Garamond-{tipo}"
            if nome not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(nome, achou))
            nomes[tipo] = nome
        else:
            nomes[tipo] = RESERVA[tipo]
    return nomes


def _estilos(f):
    base = ParagraphStyle("base", fontName=f["normal"], fontSize=11, leading=14.5, textColor=colors.HexColor("#222222"))
    return {
        "base": base,
        "titulo": ParagraphStyle("titulo", parent=base, fontName=f["negrito"], fontSize=22, leading=26, textColor=VINHO),
        "sub": ParagraphStyle("sub", parent=base, fontSize=14, leading=18, textColor=CINZA),
        "h2": ParagraphStyle("h2", parent=base, fontName=f["negrito"], fontSize=15, leading=19, textColor=VINHO,
                             spaceBefore=6, spaceAfter=6),
        "ficha": ParagraphStyle("ficha", parent=base, fontName=f["negrito"], fontSize=12.5, leading=16, textColor=VINHO),
        "rotulo": ParagraphStyle("rotulo", parent=base, fontName=f["negrito"], fontSize=9.5, leading=12, textColor=CINZA),
        "valor": ParagraphStyle("valor", parent=base, fontSize=10.5, leading=13.5),
        "texto": ParagraphStyle("texto", parent=base, alignment=4, spaceAfter=8),  # justificado
        "nota": ParagraphStyle("nota", parent=base, fontName=f["italico"], fontSize=10, textColor=CINZA),
    }


def _p(texto, estilo):
    return Paragraph(escape(str(texto)).replace("\n", "<br/>"), estilo)


def _dinheiro(v):
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _desenhar_timbrado(canvas, doc, rodape_texto, fonte):
    canvas.saveState()
    canvas.drawImage(str(PASTA / "marca_dagua.png"), 0, 0, LARGURA, ALTURA, mask="auto")
    canvas.drawImage(str(PASTA / "cabecalho.png"), 0, ALTURA - FAIXA, LARGURA, FAIXA, mask="auto")
    canvas.drawImage(str(PASTA / "rodape.png"), 0, 0, LARGURA, FAIXA, mask="auto")
    canvas.setFont(fonte, 8.5)
    canvas.setFillColor(CINZA)
    y = FAIXA + 6
    canvas.drawString(MARGENS["leftMargin"], y, rodape_texto)
    canvas.drawRightString(LARGURA - MARGENS["rightMargin"], y, f"Página {doc.page}")
    canvas.restoreState()


def _tabela_contagem(titulo, contagem, e):
    dados = [[_p(titulo, e["rotulo"]), _p("Qtd.", e["rotulo"])]]
    dados += [[_p(nome, e["valor"]), _p(qtd, e["valor"])] for nome, qtd in contagem]
    t = Table(dados, colWidths=[None, 1.6 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, DOURADO), ("LINEBELOW", (0, 1), (-1, -1), 0.3, LINHA),
                           ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def _ficha(l, e, largura):
    numero = l["Número do processo"] or "número não informado"
    cabeca = _p(f"CI {l['CI']} · {numero}", e["ficha"])
    data = l["Data da distribuição"]
    cadastro = [
        ("Cliente", l["Cliente"]), ("Polo do cliente", l["Polo do cliente"]),
        ("Parte ativa", l["Parte ativa"]), ("Parte passiva", l["Parte passiva"]),
        ("Tipo de processo", l["Tipo de processo"]), ("Órgão", l["Órgão"]),
        ("Data da distribuição", data.strftime("%d/%m/%Y") if isinstance(data, datetime) else data),
        ("Valor da ação", _dinheiro(l["Valor da ação"]) if l["Valor da ação"] is not None else "não informado"),
        ("Cidade/UF", l["Cidade/UF"]),
    ]
    cadastro = [(r, v) for r, v in cadastro if _ok(v)]
    meio = (len(cadastro) + 1) // 2
    linhas_tab = []
    for i in range(meio):
        linha = []
        for r, v in (cadastro[i], cadastro[i + meio] if i + meio < len(cadastro) else ("", "")):
            linha.append([_p(r, e["rotulo"]), _p(v, e["valor"])] if r else "")
        linhas_tab.append(linha)
    tab = Table(linhas_tab, colWidths=[largura / 2] * 2, hAlign="LEFT", splitByRow=1)
    tab.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    textos = []
    for rotulo, campo in (("Resumo do caso", "Resumo do caso"), ("Motivação do processo", "Motivação do processo"),
                          ("Financeira", "Financeira"), ("Justificativa da condenação", "Justificativa da condenação"),
                          ("Documentos faltando", "Pendência — documentos faltando")):
        if _ok(l[campo]):
            textos += [_p(rotulo, e["rotulo"]), _p(l[campo], e["texto"])]
    regua = Table([[""]], colWidths=[largura], rowHeights=[2])
    regua.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1, DOURADO)]))
    # o título da ficha nunca fica sozinho no pé da página; o resto pode continuar na seguinte
    return [CondPageBreak(3.5 * cm), KeepTogether([cabeca, regua]), tab, *textos, Spacer(1, 10)]


def salvar_pdf(arquivo, grupo, linhas, info, paragrafos_mes):
    """info: {gerado_em, ...}; paragrafos_mes: lista de parágrafos da IA (vazia = sem a página da IA)."""
    f = _fontes()
    e = _estilos(f)
    gerado = info["gerado_em"]
    mes = f"{MESES[gerado.month - 1].capitalize()} de {gerado.year}"
    rodape_texto = f"Relatório de processos · {grupo} · {mes}"
    doc = SimpleDocTemplate(str(arquivo), pagesize=A4, title=f"Relatório de processos — {grupo} — {mes}",
                            author="RFeitosa Advogados Associados", **MARGENS)
    largura = doc.width
    corpo = [_p("Relatório mensal de processos", e["titulo"]), Spacer(1, 4), _p(f"{grupo} · {mes}", e["sub"]),
             Spacer(1, 2), _p(f"Atualizado em {gerado:%d/%m/%Y}", e["nota"]), Spacer(1, 14)]

    # números do mês (os mesmos da aba Resumo da planilha)
    soma = sum(l["Valor da ação"] or 0 for l in linhas)
    sem_valor = sum(1 for l in linhas if l["Valor da ação"] is None)
    destaque = Table([[_p("Processos no relatório", e["rotulo"]), _p("Soma dos valores das ações", e["rotulo"])],
                      [_p(len(linhas), e["titulo"]), _p(_dinheiro(soma), e["titulo"])]],
                     colWidths=[largura / 2] * 2, hAlign="LEFT")
    destaque.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.2, DOURADO), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    corpo += [_p("Números do mês", e["h2"]), destaque]
    if sem_valor:
        corpo.append(_p(f"{sem_valor} processo(s) sem valor da ação no cadastro: a soma considera só os demais.", e["nota"]))
    corpo.append(Spacer(1, 10))
    resultado = Counter(l.get("_condenacao") or "não informado" for l in linhas)
    ordem = [(c, resultado[c]) for c in CONDENACOES if resultado[c]] + \
            [(c, q) for c, q in resultado.items() if c not in CONDENACOES]
    tabelas = [
        _tabela_contagem("Por resultado da decisão", ordem, e),
        _tabela_contagem("Por tipo de processo", Counter(l["Tipo de processo"] or "não informado" for l in linhas).most_common(), e),
        _tabela_contagem("Por motivação", Counter((l["Motivação do processo"] or "não informado").split(" — ")[0]
                                                  for l in linhas).most_common(), e),
        _tabela_contagem("Por polo do cliente", Counter(l["Polo do cliente"] or "não informado" for l in linhas).most_common(), e),
    ]
    grade = Table([[tabelas[0], tabelas[1]], [tabelas[2], tabelas[3]]], colWidths=[largura / 2 - 6, largura / 2 - 6],
                  hAlign="LEFT")
    grade.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12)]))
    corpo.append(grade)

    if paragrafos_mes:
        corpo += [PageBreak(), _p("Resumo do mês", e["h2"])] + [_p(p, e["texto"]) for p in paragrafos_mes]

    corpo += [PageBreak(), _p("Processos", e["h2"])]
    for l in linhas:
        corpo += _ficha(l, e, largura)

    pagina = lambda canvas, d: _desenhar_timbrado(canvas, d, rodape_texto, f["normal"])
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    doc.build(corpo, onFirstPage=pagina, onLaterPages=pagina)
