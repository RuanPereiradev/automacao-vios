"""Relatório do dia: junta as Secoes das funções em orelha/saida/<AAAA-MM-DD>/

  relatorio.html   página única, sem JavaScript nem arquivo externo, para qualquer pessoa ler
                   (abre no navegador, imprime, vai por e-mail);
  resumo.json      números de cada função (sem o texto dos itens), para a vila e para comparar dias;
  relatorio.pdf    o mesmo HTML impresso pelo Chrome (como albi/relatorio.py); sem Chrome ou com
                   --sem-pdf, fica só o HTML.
"""
import base64
import html as html_mod
import json
import os
import re
from datetime import datetime
from pathlib import Path

from nucleo.modelos import NIVEIS, ROTULOS_NIVEL

DIAS_SEMANA = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")

CSS = """
:root { --tinta:#1d2b2a; --suave:#5d6b6a; --linha:#d9e2e0; --fundo:#f4f7f6; --papel:#ffffff;
        --marca:#a8692f; --marca-esc:#6e4420; --chapeu:#7a4b2a;
        --grave:#b3261e; --grave-f:#fdecea; --atencao:#9a5b00; --atencao-f:#fff4e0;
        --info:#2f5f8a; --info-f:#eaf2fa; --ok:#2e7d32; --ok-f:#e8f5e9; }
* { box-sizing: border-box; }
body { margin:0; background:var(--fundo); color:var(--tinta);
       font: 16px/1.5 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px 48px; }
header.topo { display:flex; gap:16px; align-items:center; padding-bottom:16px; border-bottom:3px solid var(--marca); }
.selo { flex:none; width:56px; height:56px; border-radius:16px; background:var(--marca); color:#fff;
        display:flex; align-items:center; justify-content:center; font-weight:800; font-size:28px;
        box-shadow: inset 0 -6px 0 var(--marca-esc); position:relative; }
.selo::before { content:""; position:absolute; top:-7px; left:8px; right:8px; height:10px;
                background:var(--chapeu); border-radius:6px 6px 2px 2px; }
h1 { font-size: 26px; margin: 0; line-height:1.2; }
h2 { font-size: 21px; margin: 0 0 4px; }
h3 { font-size: 15px; margin: 18px 0 6px; color: var(--suave); text-transform: uppercase; letter-spacing: .04em; }
.suave { color: var(--suave); }
.faixa { margin: 16px 0 0; padding: 10px 14px; border-radius: 10px; background: var(--atencao-f);
         color: var(--atencao); font-weight: 600; }
.cartoes { display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:12px; margin: 20px 0 8px; }
.cartao { display:block; background:var(--papel); border:1px solid var(--linha); border-radius:12px; padding:12px 14px;
          color:inherit; text-decoration:none; }
.cartao b.total { display:block; font-size: 30px; line-height:1.1; }
.cartao .nome { font-weight:600; }
.cartao.erro { border-color: var(--grave); background: var(--grave-f); }
.chips { margin-top:6px; display:flex; flex-wrap:wrap; gap:4px; }
.chip { display:inline-block; font-size: 12px; font-weight:700; padding: 1px 8px; border-radius: 999px; white-space:nowrap; }
.chip.grave { background: var(--grave-f); color: var(--grave); }
.chip.atencao { background: var(--atencao-f); color: var(--atencao); }
.chip.info { background: var(--info-f); color: var(--info); }
.chip.ok { background: var(--ok-f); color: var(--ok); }
.chip.erro { background: var(--grave); color:#fff; }
section.secao { background:var(--papel); border:1px solid var(--linha); border-radius:14px; padding:18px 18px 14px; margin-top:20px; }
.resumo { margin: 0 0 8px; font-size: 17px; }
.caixa { border-radius: 10px; padding: 10px 12px; margin: 10px 0; }
.caixa.erro { background: var(--grave-f); color: var(--grave); }
.caixa.aviso { background: var(--atencao-f); color: #6b4000; }
.caixa ul { margin: 4px 0 0; padding-left: 20px; }
ul.itens { list-style:none; margin:0; padding:0; }
ul.itens li { display:flex; gap:10px; align-items:flex-start; padding: 9px 0; border-top: 1px solid var(--linha); }
ul.itens li:first-child { border-top: 0; }
ul.itens .chip { margin-top: 3px; min-width: 76px; text-align:center; }
.item-texto { flex:1; min-width:0; overflow-wrap:anywhere; }
.item-titulo { font-weight: 600; }
.item-detalhe { color: var(--suave); font-size: 14px; }
a.abrir { flex:none; font-size: 14px; color: var(--marca-esc); font-weight:600; text-decoration:none;
          border:1px solid var(--marca); border-radius:8px; padding:2px 8px; margin-top:2px; white-space:nowrap; }
.vazio { color: var(--ok); font-weight:600; margin: 6px 0; }
details.grupo { border: 1px solid var(--linha); border-radius: 10px; margin: 8px 0; background: var(--papel); }
details.grupo > summary { list-style: none; cursor: pointer; display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px;
                          padding: 10px 12px; border-radius: 10px; }
details.grupo > summary::-webkit-details-marker { display: none; }
details.grupo > summary::before { content: "▸"; color: var(--marca-esc); font-size: 14px; width: 12px; }
details.grupo[open] > summary::before { content: "▾"; }
details.grupo > summary:hover { background: var(--fundo); }
details.grupo[open] > summary { border-bottom: 1px solid var(--linha); border-radius: 10px 10px 0 0; }
details.grupo .g-nome { font-weight: 700; }
details.grupo .g-qtd { color: var(--suave); font-size: 14px; }
details.grupo .g-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-left: auto; }
details.grupo .barra { flex-basis: 100%; height: 4px; border-radius: 4px; background: var(--fundo); overflow: hidden; }
details.grupo .barra i { display: block; height: 100%; background: var(--atencao); }
details.grupo .barra i.grave { background: var(--grave); }
details.grupo .barra i.info { background: var(--info); }
details.grupo > ul.itens, details.grupo > .dentro { padding: 0 12px 4px; }
table.quadro { width: 100%; border-collapse: collapse; font-size: 14px; }
table.quadro th, table.quadro td { text-align: left; padding: 6px 8px; border-top: 1px solid var(--linha); }
table.quadro th { color: var(--suave); font-weight: 600; }
table.quadro td.n, table.quadro th.n { text-align: right; white-space: nowrap; }
footer { margin-top: 28px; font-size: 14px; color: var(--suave); }
footer .chip { margin-right: 4px; }
@media (max-width: 560px) { ul.itens li { flex-wrap: wrap; } .item-texto { flex-basis: calc(100% - 90px); } }
@media print { body { background:#fff; font-size: 12px; } main { padding: 0; max-width:none; }
               section.secao { break-inside: auto; border-color:#bbb; } ul.itens li { break-inside: avoid; }
               a.abrir { display:none; } .cartao { border-color:#bbb; } @page { size: A4; margin: 14mm; }
               details.grupo { break-inside: avoid; } details.grupo > summary::before { content: ""; width: 0; } }
"""


def _e(texto):
    return html_mod.escape(str(texto if texto is not None else ""), quote=True)


def _link_ok(link):
    return bool(re.match(r"https?://", link or "", re.I))


def _qtd(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def _chips(por_nivel, erro=""):
    partes = []
    if erro:
        partes.append('<span class="chip erro">Não concluída</span>')
    for nivel in reversed(NIVEIS):
        if por_nivel.get(nivel):
            partes.append(f'<span class="chip {nivel}">{por_nivel[nivel]} {ROTULOS_NIVEL[nivel].lower()}</span>')
    if not partes:
        partes.append('<span class="chip ok">Tudo em dia</span>')
    return '<div class="chips">' + "".join(partes) + "</div>"


def _grupos(itens):
    """[(grupo, [itens])] na ordem em que cada grupo apareceu."""
    grupos = {}
    for item in itens:
        grupos.setdefault(item.grupo or "", []).append(item)
    return list(grupos.items())


def item_html(item):
    """Uma linha <li> da lista de itens (chip do nível, título, detalhe e "Abrir no VIOS")."""
    abrir = (f'<a class="abrir" href="{_e(item.link)}">Abrir no VIOS</a>' if _link_ok(item.link) else "")
    detalhe = f'<div class="item-detalhe">{_e(item.detalhe)}</div>' if item.detalhe else ""
    return (f'<li><span class="chip {item.nivel}">{ROTULOS_NIVEL[item.nivel]}</span>'
            f'<div class="item-texto"><div class="item-titulo">{_e(item.titulo)}</div>{detalhe}</div>{abrir}</li>')


def lista_html(itens):
    return '<ul class="itens">' + "".join(item_html(i) for i in itens) + "</ul>"


def grupo_html(nome, itens, maior=0, aberto=False, dentro_html=None, ancora=""):
    """Grupo que abre e fecha com um clique (<details>, sem JavaScript): no título, o nome, o total e
    os chips por nível; com `maior`, uma barra proporcional ao maior grupo. `dentro_html` troca a lista
    de itens por outro conteúdo (ex.: grupos dentro do grupo)."""
    por = {n: 0 for n in reversed(NIVEIS)}
    for i in itens:
        por[i.nivel] += 1
    chips = "".join(f'<span class="chip {n}">{por[n]} {ROTULOS_NIVEL[n].lower()}</span>' for n in por if por[n])
    barra = ""
    if maior:
        nivel = "grave" if por["grave"] else "atencao" if por["atencao"] else "info"
        barra = f'<span class="barra"><i class="{nivel}" style="width:{max(2, round(100 * len(itens) / maior))}%"></i></span>'
    corpo = dentro_html if dentro_html is not None else lista_html(itens)
    attrs = (" open" if aberto else "") + (' id="' + _e(ancora) + '"' if ancora else "")
    return (f'<details class="grupo"{attrs}>'
            f'<summary><span class="g-nome">{_e(nome)}</span>'
            f'<span class="g-qtd">{_qtd(len(itens), "tarefa", "tarefas") if itens else "nenhuma"}</span>'
            f'<span class="g-chips">{chips}</span>{barra}</summary>{corpo}</details>')


def quadro_html(quadro):
    """Tabela fechada no fim da seção ({"titulo", "colunas", "linhas"}); colunas numéricas à direita."""
    if not quadro or not quadro.get("linhas"):
        return ""
    colunas = quadro.get("colunas") or []
    num = [all(isinstance(l[k], (int, float)) for l in quadro["linhas"] if k < len(l)) for k in range(len(colunas))]
    cab = "".join(f'<th{" class=n" if num[k] else ""}>{_e(c)}</th>' for k, c in enumerate(colunas))
    corpo = "".join("<tr>" + "".join(f'<td{" class=n" if k < len(num) and num[k] else ""}>{_e(v)}</td>'
                                     for k, v in enumerate(l)) + "</tr>" for l in quadro["linhas"])
    return (f'<details class="grupo"><summary><span class="g-nome">{_e(quadro.get("titulo", ""))}</span>'
            f'<span class="g-qtd">{len(quadro["linhas"])}</span></summary>'
            f'<div class="dentro"><table class="quadro"><tr>{cab}</tr>{corpo}</table></div></details>')


def montar_html(secoes, hoje, simulado=False, gerado_em=None):
    gerado_em = gerado_em or datetime.now()
    titulo_dia = f"{hoje:%d/%m/%Y} ({DIAS_SEMANA[hoje.weekday()]})"
    h = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Orelha · {hoje:%d/%m/%Y}</title><style>{CSS}</style></head><body><main>']
    h.append('<header class="topo"><div class="selo" aria-hidden="true">O</div><div>'
             f'<h1>Relatório do dia {_e(titulo_dia)}</h1>'
             f'<div class="suave">Feito pelo Orelha em {gerado_em:%d/%m/%Y às %H:%M} · '
             'o Orelha só lê o VIOS: nada foi alterado lá.</div></div></header>')
    if simulado:
        h.append('<div class="faixa">Modo de demonstração: dados fictícios, não vieram do VIOS.</div>')

    erros = [s for s in secoes if s.erro]
    graves = sum(s.por_nivel()["grave"] for s in secoes)
    if erros:
        frase = (f"{_qtd(len(erros), 'parte não foi concluída', 'partes não foram concluídas')} "
                 "(ver o aviso vermelho em cada uma); o resto do relatório saiu normalmente.")
    elif graves:
        frase = f"{_qtd(graves, 'item urgente', 'itens urgentes')} hoje: comece por eles (marcados em vermelho)."
    else:
        frase = "Nada urgente hoje."
    h.append(f'<p class="resumo" style="margin-top:16px">{_e(frase)}</p>')

    h.append('<nav class="cartoes" aria-label="Resumo">')
    for s in secoes:
        por = s.por_nivel()
        h.append(f'<a class="cartao{" erro" if s.erro else ""}" href="#{_e(s.chave)}">'
                 f'<span class="nome">{_e(s.titulo)}</span>'
                 f'<b class="total">{"—" if s.erro and not s.itens else s.numeros.get("destaque", len(s.itens))}</b>'
                 f'<span class="suave">{_e(s.resumo)}</span>{_chips(por, s.erro)}</a>')
    h.append("</nav>")

    for s in secoes:
        h.append(f'<section class="secao" id="{_e(s.chave)}"><h2>{_e(s.titulo)}</h2>')
        h.append(f'<p class="resumo">{_e(s.resumo)}</p>')
        if s.erro:
            h.append('<div class="caixa erro"><b>Esta parte não foi concluída.</b> '
                     f'{_e(s.erro)}<br>As outras partes do relatório não foram afetadas.</div>')
        if s.avisos:
            h.append('<div class="caixa aviso"><b>Observações</b><ul>'
                     + "".join(f"<li>{_e(a)}</li>" for a in s.avisos) + "</ul></div>")
        if not s.itens and not s.erro:
            h.append('<p class="vazio">Nada a mostrar aqui hoje.</p>')
        grupos = _grupos(s.itens)
        if s.recolher and grupos:
            h.append('<p class="suave">Clique em cada grupo para ver as tarefas.</p>')
            maior = max(len(i) for _, i in grupos)
            for grupo, itens in grupos:
                h.append(grupo_html(grupo or "Outros", itens, maior))
        else:
            for grupo, itens in grupos:
                if grupo:
                    h.append(f"<h3>{_e(grupo)}</h3>")
                h.append(lista_html(itens))
        h.append(quadro_html(s.quadro))
        h.append("</section>")

    h.append('<footer><p><span class="chip grave">Urgente</span> resolver hoje · '
             '<span class="chip atencao">Atenção</span> olhar logo · '
             '<span class="chip info">Para saber</span> só informação.</p>'
             '<p>Os dados são uma leitura do VIOS no horário acima. Confira no VIOS antes de agir.</p></footer>')
    h.append("</main></body></html>")
    return "\n".join(h)


def montar_resumo(secoes, hoje, simulado=False, gerado_em=None):
    gerado_em = gerado_em or datetime.now()
    return {
        "data": hoje.isoformat(),
        "gerado_em": gerado_em.isoformat(timespec="seconds"),
        "simulado": bool(simulado),
        "erros": [s.chave for s in secoes if s.erro],
        "secoes": [{"chave": s.chave, "titulo": s.titulo, "resumo": s.resumo, "erro": s.erro,
                    "avisos": list(s.avisos), "total_itens": len(s.itens), "por_nivel": s.por_nivel(),
                    "numeros": s.numeros or {}} for s in secoes],
    }


def _gravar(caminho, texto):
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, caminho)


def escrever_pdf(html_caminho, pdf_caminho, driver=None, opcoes=None):
    """Imprime o relatorio.html em PDF pelo Chrome (o do Orelha, se já estiver aberto). `opcoes` entram no
    Page.printToPDF (ex.: o painel semanal passa headerTemplate/footerTemplate para repetir a faixa do
    modelo e o número da página em todas as páginas)."""
    proprio = driver is None
    if proprio:
        from selenium import webdriver
        o = webdriver.ChromeOptions()
        o.add_argument("--headless=new")
        driver = webdriver.Chrome(options=o)
    try:
        driver.get(Path(html_caminho).resolve().as_uri())
        dados = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True,
                                                            **(opcoes or {})})
        Path(pdf_caminho).write_bytes(base64.b64decode(dados["data"]))
    finally:
        if proprio:
            driver.quit()


def gerar(secoes, pasta, hoje, simulado=False, pdf=True, driver=None, gerado_em=None):
    """Escreve relatorio.html, resumo.json e (com pdf=True) relatorio.pdf em `pasta`.
    Devolve {"html": Path, "json": Path, "pdf": Path|None, "erro_pdf": str}."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    gerado_em = gerado_em or datetime.now()
    info = {"html": pasta / "relatorio.html", "json": pasta / "resumo.json", "pdf": None, "erro_pdf": ""}
    _gravar(info["html"], montar_html(secoes, hoje, simulado, gerado_em))
    _gravar(info["json"], json.dumps(montar_resumo(secoes, hoje, simulado, gerado_em), ensure_ascii=False,
                                     indent=2, default=str))
    if pdf:
        try:
            escrever_pdf(info["html"], pasta / "relatorio.pdf", driver)
            info["pdf"] = pasta / "relatorio.pdf"
        except Exception as ex:  # sem Chrome: fica o HTML (que também imprime)
            texto = str(ex).strip()
            info["erro_pdf"] = texto.splitlines()[0][:200] if texto else type(ex).__name__
    return info
