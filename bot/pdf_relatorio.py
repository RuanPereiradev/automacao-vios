"""PDF do relatório de processos por Grupo Cliente (um arquivo por grupo).

Entrada: as linhas de bot/campos_relatorio.montar_linhas (13 campos por processo, todos str).
Saída: PDF A4 retrato, para o cliente leigo:
- capa: título, data/hora de geração, total de processos e resumo por Tipo de processo e por Cidade/UF;
- um bloco por processo, com os 13 campos na ordem e com os títulos de COLUNAS;
- observações no fim (se houver);
- rodapé em toda página: aviso ao cliente e "Página X de Y".

Usa só as fontes padrão do PDF (Helvetica). Elas cobrem o português (Windows-1252);
o que fica fora disso (emoji, setas, "?" de conversão) é trocado por equivalente ou removido.
Não acessa o VIOS nem a IA.
"""
import logging
import os
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from bot.campos_relatorio import COLUNAS

log = logging.getLogger(__name__)

AVISO = ("Relatório gerado a partir dos dados cadastrados no sistema do escritório. "
         "Dúvidas sobre o andamento: falar com o advogado responsável.")
VAZIO = "Não informado"

# cores (tons sóbrios, imprimem bem em preto e branco)
AZUL = colors.HexColor("#1F3A5F")
CINZA_FUNDO = colors.HexColor("#F2F4F7")
CINZA_LINHA = colors.HexColor("#C9CED6")
CINZA_TEXTO = colors.HexColor("#5B6470")

MARGEM_X = 18 * mm
MARGEM_TOPO = 18 * mm
MARGEM_BAIXO = 24 * mm  # espaço do rodapé
LARGURA_UTIL = A4[0] - 2 * MARGEM_X
LARGURA_ROTULO = 44 * mm

# nomes que o Windows não aceita como nome de arquivo
RESERVADOS = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}

# troca de caracteres que a Helvetica padrão não tem
TROCAS = {
    "→": "->", "←": "<-", "↔": "<->", "⇒": "=>",
    "≤": "<=", "≥": ">=", "≠": "<>", "≈": "~",
    "−": "-", "‐": "-", "‑": "-", "‒": "-", "―": "—",
    "✓": "OK", "✔": "OK", "✅": "OK", "✗": "X", "✘": "X", "❌": "X",
    "●": "•", "▪": "•", "■": "•", "◦": "•", "‣": "•",
    "′": "'", "″": '"', "‟": '"', "‛": "'",
    "№": "nº", "⅓": "1/3", "⅔": "2/3",
    " ": " ", " ": " ", " ": " ", " ": " ", " ": " ", " ": " ",
    " ": "\n", " ": "\n",
    "​": "", "‌": "", "‍": "", "⁠": "", "﻿": "", "�": "", "️": "",
}


def _cabe(c):
    try:
        c.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def limpar(texto):
    """Deixa o texto só com caracteres que a Helvetica padrão desenha (Windows-1252)."""
    if texto is None:
        return ""
    texto = unicodedata.normalize("NFC", str(texto)).replace("\r\n", "\n").replace("\r", "\n")
    saida = []
    for c in texto:
        c = TROCAS.get(c, c)
        if len(c) != 1:
            saida.append(c)
        elif c in "\n\t":
            saida.append(c)
        elif unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co"):
            # controle, formatação invisível e restos de codificação quebrada
            continue
        elif _cabe(c):
            saida.append(c)
        else:
            # ex. "ﬁ" -> "fi", letras com acento de outro alfabeto -> letra base
            base = "".join(x for x in unicodedata.normalize("NFKD", c)
                           if _cabe(x) and unicodedata.category(x) != "Mn")
            saida.append(base)
    return "".join(saida).replace("\t", "    ")


def _p(texto):
    """Texto para Paragraph: limpa, escapa &, <, > e mantém as quebras de linha."""
    linhas = limpar(texto).strip().split("\n")
    return "<br/>".join(escape(linha) for linha in linhas)


def nome_arquivo(grupo):
    """Nome de PDF que o Windows aceita, a partir do nome do grupo."""
    nome = limpar(grupo)
    nome = re.sub(r'[\\/:*?"<>|\n]', "-", nome)
    nome = re.sub(r"\s+", " ", nome).strip().rstrip(". ")
    if not nome:
        nome = "relatorio"
    if nome.split(".")[0].upper() in RESERVADOS:
        nome = "_" + nome
    return nome[:150] + ".pdf"


def _destino(caminho, grupo):
    caminho = Path(caminho)
    if caminho.is_dir() or caminho.suffix.lower() != ".pdf":
        caminho = caminho / nome_arquivo(grupo)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return caminho


def _estilos():
    base = dict(fontName="Helvetica", fontSize=9.5, leading=12.5, alignment=TA_LEFT, textColor=colors.black)
    return {
        "titulo": ParagraphStyle("titulo", **{**base, "fontName": "Helvetica-Bold", "fontSize": 17,
                                              "leading": 21, "textColor": AZUL, "spaceAfter": 4}),
        "sub": ParagraphStyle("sub", **{**base, "fontSize": 10, "leading": 14, "textColor": CINZA_TEXTO}),
        "secao": ParagraphStyle("secao", **{**base, "fontName": "Helvetica-Bold", "fontSize": 12,
                                            "leading": 15, "textColor": AZUL, "spaceBefore": 8, "spaceAfter": 4,
                                            "keepWithNext": 1}),
        "bloco": ParagraphStyle("bloco", **{**base, "fontName": "Helvetica-Bold", "fontSize": 10.5,
                                            "leading": 13, "textColor": colors.white}),
        "rotulo": ParagraphStyle("rotulo", **{**base, "fontName": "Helvetica-Bold", "fontSize": 8.5,
                                              "leading": 11, "textColor": AZUL}),
        "valor": ParagraphStyle("valor", **base),
        "vazio": ParagraphStyle("vazio", **{**base, "fontName": "Helvetica-Oblique", "textColor": CINZA_TEXTO}),
        "texto": ParagraphStyle("texto", **base),
    }


def _valor(linha, chave):
    v = linha.get(chave) if isinstance(linha, dict) else None
    return "" if v is None else limpar(v).strip()


def _tabela_contagem(titulo_coluna, contagem, est):
    dados = [[Paragraph(_p(titulo_coluna), est["rotulo"]), Paragraph("Processos", est["rotulo"])]]
    for nome, qtd in sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        dados.append([Paragraph(_p(nome), est["valor"]), Paragraph(str(qtd), est["valor"])])
    t = Table(dados, colWidths=[LARGURA_UTIL - 30 * mm, 30 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CINZA_FUNDO),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, CINZA_LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _total(n, encerrados=0):
    """"Total de processos: 10" ou, com encerrados, "Total de processos: 10 (7 em andamento, 3 encerrados)"."""
    texto = f"Total de processos: {n}"
    try:
        encerrados = max(0, min(int(encerrados or 0), n))
    except (TypeError, ValueError):
        encerrados = 0
    if encerrados:
        texto += f" ({n - encerrados} em andamento, {encerrados} encerrado{'s' if encerrados > 1 else ''})"
    return texto


def _contar(linhas, chave):
    return Counter(_valor(l, chave) or VAZIO for l in linhas)


def _bloco(linha, est):
    """Um processo: faixa com "ID <n> — <número>" e os 13 campos (título | valor)."""
    ident = _valor(linha, "id_extracao") or "?"
    numero = _valor(linha, "numero") or "sem número"
    faixa = Table([[Paragraph(_p(f"ID {ident} — {numero}"), est["bloco"])]], colWidths=[LARGURA_UTIL])
    faixa.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    dados = []
    for chave, titulo in COLUNAS:
        v = _valor(linha, chave)
        celula = Paragraph(_p(v), est["valor"]) if v else Paragraph(VAZIO, est["vazio"])
        dados.append([Paragraph(_p(titulo), est["rotulo"]), celula])
    # splitInRow: um texto maior que a página (resumo muito longo) quebra dentro da linha
    campos = Table(dados, colWidths=[LARGURA_ROTULO, LARGURA_UTIL - LARGURA_ROTULO], splitInRow=1)
    campos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), CINZA_FUNDO),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, CINZA_LINHA),
        ("BOX", (0, 0), (-1, -1), 0.6, CINZA_LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return KeepTogether([faixa, campos, Spacer(1, 7 * mm)])


def _canvas_numerado(grupo):
    """Canvas que guarda as páginas para escrever "Página X de Y" no fim."""
    cabecalho = limpar(f"Relatório de processos — {grupo}")
    aviso = simpleSplit(limpar(AVISO), "Helvetica", 7.5, LARGURA_UTIL)

    class CanvasNumerado(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas = []

        def showPage(self):
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                self._rodape(total)
                super().showPage()
            super().save()

        def _rodape(self, total):
            largura, _ = A4
            self.saveState()
            self.setStrokeColor(CINZA_LINHA)
            self.setLineWidth(0.5)
            y = MARGEM_BAIXO - 8 * mm
            self.line(MARGEM_X, y + 4 * mm, largura - MARGEM_X, y + 4 * mm)
            self.setFont("Helvetica", 7.5)
            self.setFillColor(CINZA_TEXTO)
            for i, texto in enumerate(aviso):
                self.drawString(MARGEM_X, y - i * 9, texto)
            self.setFont("Helvetica-Bold", 8)
            self.drawRightString(largura - MARGEM_X, y - len(aviso) * 9 - 2,
                                 f"Página {self._pageNumber} de {total}")
            if self._pageNumber > 1:
                self.setFont("Helvetica", 7.5)
                self.drawString(MARGEM_X, A4[1] - MARGEM_TOPO + 5 * mm, cabecalho[:120])
            self.restoreState()

    return CanvasNumerado


def gerar_pdf(caminho, grupo, linhas, gerado_em, observacoes=None, encerrados=0):
    """Gera o PDF do grupo e devolve o caminho do arquivo.

    caminho: arquivo .pdf ou pasta (aí o nome sai do grupo, seguro para o Windows).
    linhas: dicts de montar_linhas; chave faltando vira "Não informado".
    encerrados: quantos processos são encerrados (aparece no total da capa).
    """
    grupo = limpar(grupo).strip() or "Sem grupo"
    linhas = list(linhas or [])
    destino = _destino(caminho, grupo)
    est = _estilos()

    titulo = f"Relatório de processos — {grupo}"
    historia = [
        Paragraph(_p(titulo), est["titulo"]),
        Paragraph(_p(f"Gerado em {gerado_em:%d/%m/%Y} às {gerado_em:%H:%M}"), est["sub"]),
        Paragraph(_p(_total(len(linhas), encerrados)), est["sub"]),
        Spacer(1, 5 * mm),
    ]
    if linhas:
        historia += [
            Paragraph("Resumo por Tipo de processo", est["secao"]),
            _tabela_contagem("Tipo de processo", _contar(linhas, "tipo_processo"), est),
            Spacer(1, 3 * mm),
            Paragraph("Resumo por Cidade/UF", est["secao"]),
            _tabela_contagem("Cidade/UF", _contar(linhas, "cidade_uf"), est),
            Spacer(1, 4 * mm),
            Paragraph("Processos", est["secao"]),
        ]
        historia += [_bloco(l, est) for l in linhas]
    else:
        historia.append(Paragraph("Nenhum processo encontrado para este grupo.", est["texto"]))

    obs = [limpar(o).strip() for o in (observacoes or []) if o is not None and limpar(o).strip()]
    if obs:
        historia.append(Paragraph("Observações", est["secao"]))
        for o in obs:
            historia.append(Paragraph(_p(o), est["texto"], bulletText="•"))
            historia.append(Spacer(1, 1.5 * mm))

    # grava num temporário e troca no fim: erro no meio não deixa PDF pela metade
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".pdf", dir=str(destino.parent))
    os.close(fd)
    try:
        doc = SimpleDocTemplate(tmp, pagesize=A4, leftMargin=MARGEM_X, rightMargin=MARGEM_X,
                                topMargin=MARGEM_TOPO, bottomMargin=MARGEM_BAIXO,
                                title=limpar(titulo), author="Escritório", subject="Relatório de processos",
                                creator="automacao-vios")
        doc.build(historia, canvasmaker=_canvas_numerado(grupo))
        # mkstemp cria com 0600: o PDF vai para o cliente (Drive, outra conta), fica 0644 como os .txt
        os.chmod(tmp, 0o644)
        os.replace(tmp, str(destino))
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    log.info("PDF gerado: %s (%d processo(s))", destino, len(linhas))
    return destino
