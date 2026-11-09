"""Painel semanal (peças + audiências): desenha o HTML no papel timbrado e imprime o PDF.

Quem junta e calcula os números é funcoes/painel.py; aqui só se desenha. O modelo visual do conteúdo é
o "2026_PAINEL_SEMANAL" do escritório (resumo executivo, taxa de resolução, carga por advogado, agenda
de audiências e a lista de tarefas com a situação em cores), e a moldura é o papel timbrado
(nucleo/timbrado.py). O HTML sai autocontido; o PDF é o mesmo HTML impresso pelo Chrome.

`dados` (dict montado por funcoes/painel.py):
  inicio, fim      date    período da semana (inicio = dia da leitura; fim = inicio + ORELHA_PAINEL_DIAS_FILA)
  gerado_em        datetime
  cartoes          [(número ou "—", rótulo, classe)]    resumo executivo
  semanas          [{"semana", "fila_inicial", "resolvidas", "taxa" (float ou None), "leitura", "aproximada"}]
  nota_semanas     str     nota abaixo da tabela de taxas ("" = sem nota)
  tendencia        str     "61,3% → 71,1%" ("" = sem)
  carga            [{"nome", "pecas", "audiencias", "total", "vencidas", "urgente", "destaque"}]
  agenda           [{"data", "hora", "advogado", "tipo", "processo"}]
  dias_agenda      int
  lista_titulo     str     título da lista de tarefas
  lista            [{"processo", "faixa", "situacao", "responsavel", "tarefa"}]
  avisos           [str]
"""
import html as html_mod
from pathlib import Path

from nucleo import relatorio, timbrado

LEGENDA = ("VENCIDA/URGENTE = vermelho · ATENÇÃO 3-7d = amarelo · PRÓXIMA 8-14d = laranja · "
           "NO PRAZO 15+d = verde")

CSS = """
:root { --vinho:#5c1210; --vinho-esc:#2f0807; --ouro:#c9a227; --tinta:#1f1a1a; --suave:#6b6361; --linha:#e3dcda;
        --vermelho:#b3261e; --verm-f:#f6c9c9; --amarelo:#8a5a00; --amar-f:#fdeeba; --laranja:#b25000; --lar-f:#fde0c8;
        --verde:#2e7d32; --verde-f:#dcefdc; --azul:#2f5f8a; --azul-f:#e6eef7; }
body { font: 8.5pt/1.35 "Segoe UI", -apple-system, Roboto, Helvetica, Arial, sans-serif; color: var(--tinta); }
h1 { font-size: 17pt; margin: 0 0 1mm; color: var(--vinho); line-height: 1.15; }
.sub { color: var(--suave); font-size: 7.5pt; margin: 0 0 4mm; padding-bottom: 2mm; border-bottom: 0.5mm solid var(--ouro); }
h2 { font-size: 8pt; text-transform: uppercase; letter-spacing: .04em; color: var(--vinho); margin: 6mm 0 2mm;
     break-after: avoid; }
h2.vermelho { color: var(--vermelho); }
.cartoes { display: flex; gap: 1.5mm; margin: 0 0 1mm; }
.cartao { flex: 1; text-align: center; border: 0.2mm solid var(--linha); border-radius: 1mm; padding: 2mm 1mm 1.5mm; }
.cartao b { display: block; font-size: 18pt; line-height: 1.1; }
.cartao span { display: block; font-size: 6pt; letter-spacing: .05em; text-transform: uppercase; color: var(--suave); }
.cartao.neutro b { color: #555; } .cartao.ruim { background: var(--verm-f); } .cartao.ruim b { color: var(--vermelho); }
.cartao.info { background: var(--azul-f); } .cartao.info b { color: var(--azul); }
table.t { width: 100%; border-collapse: collapse; margin: 0 0 1.5mm; }
table.t th { background: var(--vinho); color: #fff; font-weight: 600; font-size: 7pt; padding: 1.4mm 1.5mm; text-align: center;
             border: 0.2mm solid var(--vinho-esc); }
table.t td { padding: 1.1mm 1.5mm; border: 0.2mm solid var(--linha); vertical-align: middle; font-size: 7.5pt; }
table.t tbody tr:nth-child(even) td { background: #faf7f6; }
table.t tr { break-inside: avoid; }
table.t thead { display: table-header-group; }
.c { text-align: center; } .num { font-family: Consolas, "Courier New", monospace; font-size: 7pt; white-space: nowrap; }
.ci { font-style: italic; color: var(--suave); }
.forte { font-weight: 700; }
.alto { color: var(--vermelho); font-weight: 700; }
td.zero { color: #999; text-align: center; }
td.vencida, td.urgente { background: var(--verm-f) !important; color: var(--vermelho); font-weight: 700; text-align: center; }
td.atencao { background: var(--amar-f) !important; color: var(--amarelo); font-weight: 700; text-align: center; }
td.proxima { background: var(--lar-f) !important; color: var(--laranja); font-weight: 700; text-align: center; }
td.no_prazo { background: var(--verde-f) !important; color: var(--verde); font-weight: 700; text-align: center; }
td.carga-vencida { background: var(--verm-f) !important; color: var(--vermelho); font-weight: 700; text-align: center; }
td.carga-urgente { background: var(--amar-f) !important; color: var(--amarelo); font-weight: 700; text-align: center; }
td.boa { color: var(--verde); font-weight: 700; } td.atencao-l { color: var(--amarelo); font-weight: 700; }
td.baixa { color: var(--vermelho); font-weight: 700; } td.sem { color: #999; }
.caixa { border: 0.2mm solid var(--linha); border-left: 1mm solid var(--vinho); border-radius: 1mm; padding: 2mm 3mm; margin: 0 0 2mm;
         font-size: 7.5pt; background: #fbf9f8; }
.nota { font-size: 6.8pt; color: var(--suave); font-style: italic; margin: 0 0 2mm; }
.legenda { font-size: 6.5pt; color: var(--suave); text-align: center; margin: 1mm 0 0; }
.aviso { font-size: 7pt; color: #6b4000; margin: 1mm 0; }
.quadro { width: 3mm; height: 3mm; border: 0.3mm solid #444; display: inline-block; vertical-align: middle; }
"""


def _e(texto):
    return html_mod.escape(str(texto if texto is not None else ""), quote=True)


def _pct(taxa):
    return "—" if taxa is None else f"{taxa * 100:.1f}%".replace(".", ",")


def _cartoes(dados):
    return ('<div class="cartoes">' + "".join(
        f'<div class="cartao {_e(classe)}"><b>{_e(numero)}</b><span>{_e(rotulo)}</span></div>'
        for numero, rotulo, classe in dados["cartoes"]) + "</div>")


def _semanas(dados):
    semanas = dados.get("semanas") or []
    if not semanas:
        return ('<div class="caixa">Esta é a primeira edição do painel: ainda não há uma semana anterior para comparar. '
                "A taxa de resolução aparece a partir da próxima edição.</div>")
    linhas = []
    for s in semanas:
        leitura = s.get("leitura") or "—"
        classe = {"Boa": "boa", "Atenção": "atencao-l", "Baixa": "baixa"}.get(leitura, "sem")
        taxa = _pct(s.get("taxa")) + (" *" if s.get("aproximada") else "")
        linhas.append(f'<tr><td class="c">{_e(s["semana"])}</td><td class="c">{_e(s["fila_inicial"])}</td>'
                      f'<td class="c">{_e(s["resolvidas"])}</td><td class="c">{_e(taxa)}</td>'
                      f'<td class="c {classe}">{_e(leitura)}</td></tr>')
    saida = ('<table class="t"><thead><tr><th>Semana</th><th>Fila inicial</th><th>Resolvidas</th><th>Taxa</th>'
             f'<th>Leitura</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')
    if dados.get("nota_semanas"):
        saida += f'<p class="nota">{_e(dados["nota_semanas"])}</p>'
    if dados.get("tendencia"):
        saida += f'<p class="nota" style="font-style:normal">Tendência: {_e(dados["tendencia"])}</p>'
    return saida


def _carga(dados):
    if not dados.get("carga"):
        return '<p class="nota">Nenhuma tarefa de peça ou audiência na fila.</p>'
    linhas = []
    for c in dados["carga"]:
        def n(v, classe=""):
            return (f'<td class="{classe}">{_e(v)}</td>' if v else '<td class="zero">—</td>')
        nome = f'<span class="alto">{_e(c["nome"])}</span>' if c.get("destaque") else _e(c["nome"])
        linhas.append(f'<tr><td>{nome}</td>{n(c["pecas"])}{n(c["audiencias"])}<td class="c">{_e(c["total"])}</td>'
                      f'{n(c["vencidas"], "carga-vencida")}{n(c["urgente"], "carga-urgente" if c.get("destaque") else "c")}</tr>')
    return ('<table class="t"><thead><tr><th>Advogado</th><th>Peças</th><th>Audiências</th><th>Total</th>'
            f'<th>Vencidas</th><th>Urgente ≤7d</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')


def _agenda(dados):
    if not dados.get("agenda"):
        return f'<p class="nota">Nenhuma audiência nos próximos {_e(dados["dias_agenda"])} dias.</p>'
    linhas = "".join(
        f'<tr><td class="c">{_e(a["data"])}</td><td class="c">{_e(a["hora"])}</td><td>{_e(a["advogado"])}</td>'
        f'<td>{_e(a["tipo"])}</td><td class="num{" ci" if a["processo"].upper().startswith("CI") else ""}">{_e(a["processo"])}</td></tr>'
        for a in dados["agenda"])
    return ('<table class="t"><thead><tr><th>Data</th><th>Hora</th><th>Advogado</th><th>Tipo</th>'
            f'<th>Processo (nº CNJ)</th></tr></thead><tbody>{linhas}</tbody></table>'
            f'<p class="legenda">{LEGENDA}</p>')


def _lista(dados):
    if not dados.get("lista"):
        return '<p class="nota">Nenhuma tarefa nesta lista.</p>'
    linhas = "".join(
        f'<tr><td class="c"><span class="quadro"></span></td>'
        f'<td class="num{" ci" if t["processo"].upper().startswith("CI") else ""}">{_e(t["processo"] or "—")}</td>'
        f'<td class="{_e(t["faixa"])}">{_e(t["situacao"])}</td><td>{_e(t["responsavel"])}</td><td>{_e(t["tarefa"])}</td></tr>'
        for t in dados["lista"])
    return ('<table class="t"><thead><tr><th style="width:5mm"></th><th style="width:36mm">Processo (nº CNJ)</th>'
            '<th style="width:22mm">Situação</th><th style="width:27mm">Responsável</th><th>Tarefa</th></tr></thead>'
            f'<tbody>{linhas}</tbody></table><p class="legenda">{LEGENDA}</p>')


def montar_html(dados):
    inicio, fim = dados["inicio"], dados["fim"]
    periodo = f"{inicio:%d/%m} a {fim:%d/%m/%Y}"
    corpo = [f"<h1>Painel Semanal — Semana de {periodo}</h1>",
             f'<p class="sub">Peças + Audiências · feito pelo Orelha em {dados["gerado_em"]:%d/%m/%Y às %H:%M} · '
             "leitura do VIOS: nada foi alterado lá. Documento interno.</p>"]
    for aviso in dados.get("avisos") or []:
        corpo.append(f'<p class="aviso">⚠ {_e(aviso)}</p>')
    corpo += ["<h2>Resumo executivo — fila combinada</h2>", _cartoes(dados),
              "<h2>Diagnóstico comparativo — taxa de resolução semanal</h2>", _semanas(dados),
              "<h2>Carga combinada por advogado — peças + audiências</h2>", _carga(dados),
              f'<h2>Agenda de audiências — próximos {_e(dados["dias_agenda"])} dias (comparecimento obrigatório)</h2>',
              _agenda(dados),
              f'<h2 class="vermelho">{_e(dados["lista_titulo"])}</h2>', _lista(dados)]
    return timbrado.pagina(f"Painel semanal {periodo}", "\n".join(corpo), CSS)


def gerar(dados, pasta, pdf=True, driver=None, nome="painel-semanal"):
    """Escreve <nome>.html e (com pdf=True) <nome>.pdf em `pasta`.
    Devolve {"html": Path, "pdf": Path|None, "erro_pdf": str}."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    info = {"html": pasta / f"{nome}.html", "pdf": None, "erro_pdf": ""}
    relatorio._gravar(info["html"], montar_html(dados))
    if pdf:
        try:
            relatorio.escrever_pdf(info["html"], pasta / f"{nome}.pdf", driver)
            info["pdf"] = pasta / f"{nome}.pdf"
        except Exception as ex:  # sem Chrome: fica o HTML (que também imprime)
            texto = str(ex).strip()
            info["erro_pdf"] = texto.splitlines()[0][:200] if texto else type(ex).__name__
    return info
