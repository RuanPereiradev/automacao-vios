"""Painel semanal (peças + audiências): desenha o HTML no visual do modelo e imprime o PDF.

Quem junta e calcula os números é funcoes/painel.py; aqui só se desenha. O visual é o do
"2026_PAINEL_SEMANAL_19JUL_RF" do escritório (desde 23/11/2026; antes saía no papel timbrado): faixa
azul-marinho com "R. FEITOSA GROUP · GESTÃO DE PRODUÇÃO JURÍDICA", o título da semana e "Pág. N" no alto de
cada página, filete dourado embaixo da faixa e a legenda das cores no rodapé de cada página. No PDF a faixa
e o rodapé são o cabeçalho/rodapé do Chrome (headerTemplate/footerTemplate do Page.printToPDF), que se
repetem e numeram as páginas; no HTML aberto na tela, a faixa aparece uma vez, no alto.

Conteúdo: caixa da regra de atribuição (se houver), resumo executivo (cartões), taxa de resolução semanal,
carga por advogado, agenda de audiências (tabela roxa) e a lista de tarefas com a situação em cores.

`dados` (dict montado por funcoes/painel.py):
  inicio, fim      date    período da semana
  gerado_em        datetime
  cartoes          [(número ou "—", rótulo, classe)]    resumo executivo
  semanas          [{"semana", "fila_inicial", "resolvidas", "taxa" (float ou None), "leitura", "aproximada"}]
  nota_semanas     str     nota abaixo da tabela de taxas ("" = sem nota)
  tendencia        str     "61,3% → 71,1%" ("" = sem)
  carga            [{"nome", "pecas", "audiencias", "outras", "total", "vencidas", "urgente", "destaque"}]
  outras           True quando a fila tem todos os tipos (coluna "Outras" na carga)
  regra            {"grupo": [primeiros nomes], "alvo": nome} ou None    caixa "Regra de atribuição"
  agenda           [{"data", "hora", "advogado", "tipo", "processo"}]
  dias_agenda      int
  agenda_titulo    str     título da agenda quando o período foi escolhido na página ("" = próximos N dias)
  lista_titulo     str     título da lista de tarefas
  lista            [{"processo", "faixa", "situacao", "responsavel", "tarefa"}]
  avisos           [str]
"""
import html as html_mod
from pathlib import Path

from nucleo import relatorio

EMPRESA = "R. FEITOSA GROUP · GESTÃO DE PRODUÇÃO JURÍDICA"
LEGENDA = ("VENCIDA/URGENTE = vermelho · ATENÇÃO 3-7d = amarelo · PRÓXIMA 8-14d = laranja · "
           "NO PRAZO 15+d = verde")

# cores do modelo
MARINHO, OURO, ROXO = "#18233f", "#c9a24a", "#5b21b6"

# margens da página (mm): no alto cabe a faixa, embaixo o rodapé com a legenda
TOPO, BASE, LADOS = 30, 14, 14

CSS = f"""
@page {{ size: A4; margin: {TOPO}mm {LADOS}mm {BASE}mm; }}
* {{ box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
html, body {{ margin: 0; padding: 0; background: #fff; }}
body {{ font: 8pt/1.35 Helvetica, Arial, "Liberation Sans", sans-serif; color: #1d1d1f; }}
.faixa {{ background: {MARINHO}; color: #fff; padding: 5mm {LADOS}mm 4mm; border-bottom: 1.2mm solid {OURO}; }}
.faixa .empresa {{ color: {OURO}; font-size: 7pt; font-weight: 700; letter-spacing: .03em; }}
.faixa .linha {{ display: flex; justify-content: space-between; align-items: baseline; margin-top: 3mm; }}
.faixa .titulo {{ font-size: 14pt; font-weight: 700; }}
.faixa .pag {{ color: #a9b0c2; font-size: 8pt; }}
.rodape-tela {{ background: #f1f2f4; color: #6b6f78; font-size: 6.5pt; text-align: center; padding: 3mm; margin-top: 8mm; }}
.conteudo {{ padding: 0; }}
@media screen {{ .conteudo {{ max-width: 182mm; margin: 6mm auto; }} }}
@media print {{ .so-tela {{ display: none; }} }}
h2 {{ font-size: 7pt; font-weight: 700; text-transform: uppercase; letter-spacing: .02em; color: #5f6470;
      margin: 5mm 0 3mm; break-after: avoid; }}
h2.azul {{ color: #2a62b0; }} h2.roxo {{ color: {ROXO}; }} h2.vermelho {{ color: #c62828; }}
hr.ouro {{ border: 0; border-top: 0.3mm solid {OURO}; margin: 6mm 0 0; }}
.regra {{ border: 0.3mm solid {ROXO}; background: #f3f0fc; padding: 2.5mm 3mm; font-size: 7.5pt; margin: 0 0 2mm; }}
.cartoes {{ display: flex; gap: 0.6mm; margin: 0 0 2mm; }}
.cartao {{ flex: 1; text-align: center; padding: 2mm 1mm 2.5mm; background: #f1f2f4; }}
.cartao b {{ display: block; font-size: 19pt; line-height: 1.2; color: #6b6f78; }}
.cartao span {{ display: block; font-size: 6.5pt; text-transform: uppercase; color: #6b6f78; margin-top: 1.5mm; }}
.cartao.ruim {{ background: #f5c9cf; }} .cartao.ruim b {{ color: #c62828; }}
.cartao.info {{ background: #e8effa; }} .cartao.info b {{ color: #2a62b0; }}
table.t {{ border-collapse: collapse; margin: 0 auto 2mm; }}
table.t th {{ background: {MARINHO}; color: #fff; font-weight: 700; font-size: 7pt; padding: 2mm 2mm; text-align: center;
              border: 0.2mm solid {MARINHO}; }}
table.t td {{ padding: 1.6mm 2mm; border: 0.2mm solid #e2e4e8; vertical-align: middle; font-size: 7.5pt; }}
table.t tbody tr:nth-child(even) td {{ background: #f4f5f7; }}
table.t tr {{ break-inside: avoid; }}
table.t thead {{ display: table-header-group; }}
table.semanas {{ width: 60%; }} table.carga {{ width: 74%; }} table.agenda {{ width: 66%; }} table.lista {{ width: 100%; table-layout: fixed; }}
table.semanas th:first-child, table.semanas td:first-child {{ text-align: left; }}
table.agenda th {{ background: {ROXO}; border-color: {ROXO}; text-align: left; }}
table.agenda td {{ font-size: 7pt; }}
table.agenda tbody tr:nth-child(even) td {{ background: #f3f0fc; }}
table.agenda td.forte {{ font-weight: 700; background: #fbf7e9 !important; }}
.c {{ text-align: center; }}
.num {{ font-family: "Courier New", Courier, monospace; font-size: 6.8pt; white-space: nowrap; }}
.ci {{ font-family: Helvetica, Arial, sans-serif; font-style: italic; color: #6b6f78; }}
.alto {{ color: #c62828; font-weight: 700; }}
td.zero {{ text-align: center; }}
td.vencida, td.urgente {{ background: #f5c9cf !important; color: #c62828; font-weight: 700; text-align: center; white-space: nowrap; }}
td.atencao {{ background: #fdf0c4 !important; color: #8a6100; font-weight: 700; text-align: center; white-space: nowrap; }}
td.proxima {{ background: #fde3cc !important; color: #c25a00; font-weight: 700; text-align: center; white-space: nowrap; }}
td.no_prazo {{ background: #dcefdc !important; color: #2e7d32; font-weight: 700; text-align: center; white-space: nowrap; }}
td.carga-vencida {{ background: #f5c9cf !important; color: #c62828; font-weight: 700; text-align: center; }}
td.carga-urgente {{ background: #fdf0c4 !important; color: #8a6100; font-weight: 700; text-align: center; }}
td.boa {{ color: #2e7d32; font-weight: 700; }} td.atencao-l {{ color: #8a6100; font-weight: 700; }}
td.baixa {{ color: #c62828; font-weight: 700; }} td.sem {{ color: #999; }}
td.taxa-aprox {{ font-style: italic; color: #6b6f78; }}
.nota {{ font-size: 6.8pt; color: #7a7e87; font-style: italic; margin: 1mm 0 2mm; }}
.texto {{ font-size: 7.5pt; margin: 2mm 0; }}
.aviso {{ font-size: 7pt; color: #7a4a00; margin: 1mm 0; }}
.feito {{ font-size: 6.5pt; color: #8a8e97; margin-top: 5mm; }}
"""

# cabeçalho e rodapé do Chrome: estilos inline (o Chrome não usa o CSS da página neles)
_BASE_TEMPLATE = ("<style>html,body{margin:0;padding:0;}*{-webkit-print-color-adjust:exact;print-color-adjust:exact;}"
                  "</style>")


def _e(texto):
    return html_mod.escape(str(texto if texto is not None else ""), quote=True)


def _pct(taxa):
    return "—" if taxa is None else f"{taxa * 100:.1f}%".replace(".", ",")


def _periodo(dados):
    return f'{dados["inicio"]:%d/%m} a {dados["fim"]:%d/%m/%Y}'


def _escopo(dados):
    return "Peças + Audiências + Outras" if dados.get("outras") else "Peças + Audiências"


def cabecalho_pdf(dados):
    """headerTemplate do Chrome: a faixa do modelo com "Pág. N" em cada página."""
    return (_BASE_TEMPLATE +
            f'<div style="width:100%;height:{TOPO - 6}mm;background:{MARINHO};border-bottom:1.2mm solid {OURO};'
            f'padding:5mm {LADOS}mm 0;box-sizing:border-box;font-family:Helvetica,Arial,sans-serif;'
            'margin-top:-1px;">'
            f'<div style="color:{OURO};font-size:7pt;font-weight:700;letter-spacing:.03em;">{_e(EMPRESA)}</div>'
            '<div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:3.5mm;">'
            f'<span style="color:#fff;font-size:14pt;font-weight:700;">Painel Semanal — Semana de {_e(_periodo(dados))}</span>'
            f'<span style="color:#a9b0c2;font-size:8pt;">{_e(_escopo(dados))} &nbsp;·&nbsp; Pág. <span class="pageNumber"></span></span>'
            "</div></div>")


def rodape_pdf():
    """footerTemplate do Chrome: a legenda das cores numa faixa cinza em cada página."""
    return (_BASE_TEMPLATE +
            f'<div style="width:100%;height:{BASE - 4}mm;background:#f1f2f4;color:#6b6f78;font-size:6.5pt;'
            'font-family:Helvetica,Arial,sans-serif;text-align:center;box-sizing:border-box;padding-top:3.5mm;'
            f'margin-bottom:-1px;">{_e(LEGENDA)}</div>')


def _cartoes(dados):
    return ('<div class="cartoes">' + "".join(
        f'<div class="cartao {_e(classe)}"><b>{_e(numero)}</b><span>{_e(rotulo)}</span></div>'
        for numero, rotulo, classe in dados["cartoes"]) + "</div>")


def _semanas(dados):
    semanas = dados.get("semanas") or []
    if not semanas:
        return ('<p class="texto">Esta é a primeira edição do painel com este conjunto de tarefas: ainda não há uma '
                "semana anterior para comparar. A taxa de resolução aparece a partir da próxima edição.</p>")
    linhas = []
    for s in semanas:
        leitura = s.get("leitura") or "—"
        classe = {"Boa": "boa", "Atenção": "atencao-l", "Baixa": "baixa"}.get(leitura, "sem")
        taxa = _pct(s.get("taxa")) + (" *" if s.get("aproximada") else "")
        linhas.append(f'<tr><td>{_e(s["semana"])}</td><td class="c">{_e(s["fila_inicial"])}</td>'
                      f'<td class="c">{_e(s["resolvidas"])}</td>'
                      f'<td class="c{" taxa-aprox" if s.get("aproximada") else ""}">{_e(taxa)}</td>'
                      f'<td class="c {classe}">{_e(leitura)}</td></tr>')
    saida = ('<table class="t semanas"><thead><tr><th>Semana</th><th>Fila inicial</th><th>Resolvidas</th><th>Taxa</th>'
             f'<th>Leitura</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')
    if dados.get("nota_semanas"):
        saida += f'<p class="nota">{_e(dados["nota_semanas"])}</p>'
    if dados.get("tendencia"):
        saida += f'<p class="texto">Tendência: {_e(dados["tendencia"])}</p>'
    return saida


def _carga(dados):
    if not dados.get("carga"):
        return '<p class="nota">Nenhuma tarefa na fila.</p>'
    outras = dados.get("outras")
    linhas = []
    for c in dados["carga"]:
        def n(v, classe="c"):
            return f'<td class="{classe}">{_e(v)}</td>' if v else '<td class="zero">—</td>'
        nome = f'<span class="alto">{_e(c["nome"])}</span>' if c.get("destaque") else _e(c["nome"])
        linhas.append(f'<tr><td>{nome}</td>{n(c["pecas"])}{n(c["audiencias"])}'
                      + (n(c.get("outras", 0)) if outras else "") + f'<td class="c">{_e(c["total"])}</td>'
                      f'{n(c["vencidas"], "carga-vencida")}{n(c["urgente"], "carga-urgente" if c.get("destaque") else "c")}</tr>')
    return ('<table class="t carga"><thead><tr><th>Advogado</th><th>Peças</th><th>Audiências</th>'
            + ("<th>Outras</th>" if outras else "") + "<th>Total</th>"
            f'<th>Vencidas</th><th>Urgente ≤7d</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')


def _titulo_agenda(dados):
    """Período escolhido na página: "Agenda de audiências — 09/11 a 23/11 (...)"; sem escolha: próximos N dias."""
    return dados.get("agenda_titulo") or (f'Agenda de audiências — próximos {dados["dias_agenda"]} dias '
                                          "(comparecimento obrigatório)")


def _processo(texto):
    texto = texto or "—"
    return f'<td class="num{" ci" if texto.upper().startswith("CI") else ""}">{_e(texto)}</td>'


def _agenda(dados):
    if not dados.get("agenda"):
        if dados.get("agenda_titulo"):
            return f'<p class="nota">Nenhuma audiência de {dados["inicio"]:%d/%m} a {dados["fim"]:%d/%m}.</p>'
        return f'<p class="nota">Nenhuma audiência nos próximos {_e(dados["dias_agenda"])} dias.</p>'
    fortes = {c["nome"] for c in dados.get("carga") or [] if c.get("destaque")}
    linhas = "".join(
        f'<tr><td class="c">{_e(a["data"])}</td><td class="c">{_e(a["hora"])}</td>'
        f'<td class="{"forte" if a["advogado"] in fortes else ""}">{_e(a["advogado"])}</td>'
        f'<td>{_e(a["tipo"])}</td>{_processo(a["processo"])}</tr>'
        for a in dados["agenda"])
    return ('<table class="t agenda"><thead><tr><th>Data</th><th>Hora</th><th>Advogado</th><th>Tipo</th>'
            f'<th>Processo (nº CNJ)</th></tr></thead><tbody>{linhas}</tbody></table>')


def _lista(dados):
    if not dados.get("lista"):
        return '<p class="nota">Nenhuma tarefa nesta lista.</p>'
    linhas = "".join(
        f'<tr><td class="c">■</td>{_processo(t["processo"])}'
        f'<td class="{_e(t["faixa"])}">{_e(t["situacao"])}</td><td>{_e(t["responsavel"])}</td><td>{_e(t["tarefa"])}</td></tr>'
        for t in dados["lista"])
    return ('<table class="t lista"><thead><tr><th style="width:6mm">■</th><th style="width:44mm">Processo (nº CNJ)</th>'
            '<th style="width:23mm">Situação</th><th style="width:30mm">Responsável</th><th>Tarefa</th></tr></thead>'
            f'<tbody>{linhas}</tbody></table>')


def _regra(dados):
    regra = dados.get("regra")
    if not regra:
        return ""
    grupo = " · ".join(_e(n) for n in regra["grupo"])
    return (f'<div class="regra"><b>REGRA DE ATRIBUIÇÃO:</b> audiências cíveis com etiqueta de grupo no Vios ({grupo}) '
            f'atribuídas a <b>{_e(regra["alvo"])}</b>, por decisão do gestor.</div>')


def montar_html(dados):
    periodo = _periodo(dados)
    faixa = (f'<div class="faixa so-tela"><div class="empresa">{_e(EMPRESA)}</div><div class="linha">'
             f'<span class="titulo">Painel Semanal — Semana de {_e(periodo)}</span>'
             f'<span class="pag">{_e(_escopo(dados))}</span></div></div>')
    carga_titulo = ("Carga por advogado · peças, audiências e outras tarefas" if dados.get("outras")
                    else "Carga combinada por advogado · peças + audiências")
    corpo = [_regra(dados)]
    corpo += [f'<p class="aviso">⚠ {_e(a)}</p>' for a in dados.get("avisos") or []]
    corpo += ["<h2>Resumo executivo — fila combinada</h2>", _cartoes(dados),
              '<h2 class="azul">Diagnóstico comparativo — taxa de resolução semanal</h2>', _semanas(dados),
              '<hr class="ouro">',
              f"<h2>{_e(carga_titulo)}</h2>", _carga(dados),
              '<p class="nota" style="text-align:center">Tarefa com mais de um advogado conta na carga de cada um.</p>',
              '<hr class="ouro">',
              f'<h2 class="roxo">{_e(_titulo_agenda(dados))}</h2>', _agenda(dados),
              f'<h2 class="vermelho" style="break-before:page">{_e(dados["lista_titulo"])}</h2>', _lista(dados),
              f'<p class="feito">Feito pelo Orelha em {dados["gerado_em"]:%d/%m/%Y às %H:%M} · leitura do VIOS: nada foi '
              "alterado lá. Documento interno.</p>"]
    return ('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
            f"<title>Painel semanal {_e(periodo)}</title><style>{CSS}</style></head><body>"
            f'{faixa}<div class="conteudo">{"".join(corpo)}</div>'
            f'<div class="rodape-tela so-tela">{_e(LEGENDA)}</div></body></html>')


def gerar(dados, pasta, pdf=True, driver=None, nome="painel-semanal"):
    """Escreve <nome>.html e (com pdf=True) <nome>.pdf em `pasta`.
    Devolve {"html": Path, "pdf": Path|None, "erro_pdf": str}."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    info = {"html": pasta / f"{nome}.html", "pdf": None, "erro_pdf": ""}
    relatorio._gravar(info["html"], montar_html(dados))
    if pdf:
        try:
            relatorio.escrever_pdf(info["html"], pasta / f"{nome}.pdf", driver,
                                   {"displayHeaderFooter": True, "headerTemplate": cabecalho_pdf(dados),
                                    "footerTemplate": rodape_pdf()})
            info["pdf"] = pasta / f"{nome}.pdf"
        except Exception as ex:  # sem Chrome: fica o HTML (que também imprime)
            texto = str(ex).strip()
            info["erro_pdf"] = texto.splitlines()[0][:200] if texto else type(ex).__name__
    return info
