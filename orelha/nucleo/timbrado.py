"""Papel timbrado do escritório (R. Feitosa Advogados) para os PDFs do Orelha.

Reproduz o modelo Word "Timbrado_RFeitosa_Advogados_COM_MARCADOR.docx": A4, marca d'água do "RF" na
página inteira, faixa vinho com a logo no alto e rodapé com os endereços. As três imagens estão em
orelha/assets/timbrado/ (extraídas do .docx) e entram na página em base64: o HTML continua um arquivo
só, sem nada externo (como o relatório do dia).

As margens são as do modelo (topo 46 mm, base 40 mm, esquerda 30 mm, direita 20 mm). O Chrome repete
o cabeçalho e o rodapé em todas as páginas (elementos fixos) e o conteúdo corre dentro de uma tabela
cujo <thead> e <tfoot> são só espaçadores: assim cada página reserva o espaço do timbrado, e não só a 1ª.
"""
import base64
import html as html_mod
from pathlib import Path

PASTA_IMAGENS = Path(__file__).resolve().parent.parent / "assets" / "timbrado"
IMAGENS = {"marca": "marca-dagua.png", "cabecalho": "cabecalho.png", "rodape": "rodape.png"}

# margens do modelo, em mm
TOPO, BASE, ESQUERDA, DIREITA = 46, 40, 30, 20

CSS_TIMBRADO = f"""
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
.timbre {{ position: fixed; left: 0; width: 210mm; z-index: 0; }}
.timbre img {{ display: block; width: 100%; }}
.timbre.marca {{ top: 0; height: 297mm; }}
.timbre.marca img {{ height: 297mm; }}
.timbre.cabecalho {{ top: 0; height: 40mm; }}
.timbre.rodape {{ bottom: 0; height: 40mm; }}
table.folha {{ width: 210mm; border-collapse: collapse; position: relative; z-index: 1; }}
table.folha > thead > tr > td {{ height: {TOPO}mm; padding: 0; }}
table.folha > tfoot > tr > td {{ height: {BASE}mm; padding: 0; }}
table.folha > tbody > tr > td {{ padding: 0 {DIREITA}mm 0 {ESQUERDA}mm; vertical-align: top; }}
"""


def _data_uri(nome):
    dados = (PASTA_IMAGENS / IMAGENS[nome]).read_bytes()
    return "data:image/png;base64," + base64.b64encode(dados).decode("ascii")


def pagina(titulo, corpo, css=""):
    """HTML completo de um documento no papel timbrado. `corpo` é o HTML do conteúdo (já escapado);
    `css` é o estilo do conteúdo. Levanta OSError se faltar alguma imagem do timbrado."""
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        f"<title>{html_mod.escape(titulo)}</title><style>{CSS_TIMBRADO}{css}</style></head><body>"
        f'<div class="timbre marca"><img alt="" src="{_data_uri("marca")}"></div>'
        f'<div class="timbre cabecalho"><img alt="" src="{_data_uri("cabecalho")}"></div>'
        f'<div class="timbre rodape"><img alt="" src="{_data_uri("rodape")}"></div>'
        '<table class="folha"><thead><tr><td></td></tr></thead><tfoot><tr><td></td></tr></tfoot>'
        f"<tbody><tr><td>{corpo}</td></tr></tbody></table></body></html>"
    )
