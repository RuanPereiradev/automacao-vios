"""Abre um processo do TRT7 pelo acervo do PJe e lê o texto de cada movimentação (só Mac).

  cd pje-busca && python3 testar_processos.py 0001368-02.2026.5.07.0038 0002754-04.2025.5.07.0038

Faz o login (console do Presto > Sites > TRT7 > Login via Presto), pesquisa cada número no acervo geral,
clica no botão "Detalhes do Processo" e, na página de detalhes, abre o documento de cada movimentação
da linha do tempo (um por um), lendo o texto do PDF pelo visualizador do PJe (pdf.js).

Saídas:
  saida/<número>.txt                   o TXT do processo (movimentações e texto de cada documento)
  logs/processos/<data_hora>/<número>/ capturas de tela e HTML (fora do git)
Não baixa autos e não clica em nada além da pesquisa e dos links de documento.
"""
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "src"))

import acesso_pje as A  # noqa: E402
import chrome_mac as CM  # noqa: E402

ACERVO = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/acervo-geral"
LOGS = AQUI / "logs" / "processos"
SAIDA = AQUI / "saida"

# digita o número no campo "Entre com o número do processo para consulta" e aperta Enter (Angular: dispara os eventos)
JS_PESQUISAR = r"""(function(numero){
  var i = document.getElementById('inputNumeroProcesso')
       || document.querySelector('input[aria-label*="número do processo" i]');
  if (!i) return JSON.stringify({ok: false, erro: 'campo do número não achado'});
  var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  i.focus(); setter.call(i, numero);
  ['input', 'keyup', 'change'].forEach(function(n) { i.dispatchEvent(new Event(n, {bubbles: true})); });
  ['keydown', 'keyup'].forEach(function(n) {
    i.dispatchEvent(new KeyboardEvent(n, {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
  });
  return JSON.stringify({ok: true, valor: i.value});
})(%s)"""

# onde fica o botão "Detalhes do Processo <classe> <número>" (role=link), em coordenadas da tela
JS_ONDE_KZ = r"""(function(numero){
  var botoes = [].filter.call(document.querySelectorAll('button[aria-label]'), function(b) {
    var r = b.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && /^Detalhes do Processo/i.test(b.getAttribute('aria-label') || '');
  });
  var alvo = botoes.filter(function(b) { return (b.getAttribute('aria-label') || '').indexOf(numero) >= 0; })[0];
  if (!alvo) return JSON.stringify({ok: false, erro: 'botão Detalhes do Processo não achado para ' + numero,
                                    botoes: botoes.map(function(b) { return b.getAttribute('aria-label'); })});
  var el = alvo.querySelector('img') || alvo;
  el.scrollIntoView({block: 'center'});
  var r = el.getBoundingClientRect();
  return JSON.stringify({ok: true, aria: alvo.getAttribute('aria-label'),
                         x: Math.round(window.screenX + r.left + r.width / 2),
                         y: Math.round(window.screenY + (window.outerHeight - window.innerHeight) + r.top + r.height / 2)});
})(%s)"""

# foca o botão "Detalhes do Processo <número>" (para o Enter)
JS_FOCAR_KZ = r"""(function(numero){
  var b = [].filter.call(document.querySelectorAll('button[aria-label]'), function(x) {
    return (x.getAttribute('aria-label') || '').indexOf(numero) >= 0 && /^Detalhes do Processo/i.test(x.getAttribute('aria-label'));
  })[0];
  if (!b) return JSON.stringify({ok: false});
  b.focus();
  return JSON.stringify({ok: true});
})(%s)"""

# movimentações da página de detalhes: cada <li> da linha do tempo com o link do documento
JS_LISTA_MOVIMENTACOES = r"""(function(){
  var out = [];
  [].forEach.call(document.querySelectorAll('li[id^="doc_"]'), function(li) {
    var a = li.querySelector('a[target="_blank"][href*="/documento/"][href$="/conteudo"]');
    if (!a) return;
    var hora = li.querySelector('.tl-item-hora');
    var quem = li.querySelector('div[name="tipoItemTimeline"]');
    var titulo = li.querySelector('a.tl-documento[href*="/detalhe"]');
    var partes = titulo ? [].map.call(titulo.querySelectorAll('span'), function(s) { return s.textContent.trim(); })
                             .filter(function(s) { return s; }) : [];
    out.push({href: a.getAttribute('href'), aria: a.getAttribute('aria-label') || '',
              hora: hora ? hora.getAttribute('aria-label') : '', quem: quem ? quem.getAttribute('aria-label') : '',
              partes: partes});
  });
  return JSON.stringify(out);
})()"""

# inicia a leitura do texto de todas as páginas do PDF (API do pdf.js dentro do visualizador do PJe)
JS_INICIAR_TEXTO = r"""(function(){
  window.__pjeTexto = null;
  var app = null;
  [].some.call(document.querySelectorAll('object, iframe, embed'), function(o) {
    try {
      var w = o.contentWindow || (o.contentDocument && o.contentDocument.defaultView);
      if (w && w.PDFViewerApplication && w.PDFViewerApplication.pdfDocument) { app = w.PDFViewerApplication; return true; }
    } catch (e) {}
    return false;
  });
  if (!app) return JSON.stringify({ok: false, erro: 'visualizador do PDF ainda não carregou'});
  var pdf = app.pdfDocument, paginas = [], p = Promise.resolve();
  for (var i = 1; i <= pdf.numPages; i++) {
    (function(k) {
      p = p.then(function() {
        return pdf.getPage(k).then(function(pg) { return pg.getTextContent(); }).then(function(tc) {
          var txt = '';
          tc.items.forEach(function(it) { txt += it.str + (it.hasEOL ? '\n' : ' '); });
          paginas.push({pagina: k, texto: txt});
        });
      });
    })(i);
  }
  p.then(function() { window.__pjeTexto = JSON.stringify({ok: true, paginas: paginas}); })
   .catch(function(e) { window.__pjeTexto = JSON.stringify({ok: false, erro: String(e)}); });
  return JSON.stringify({ok: true, paginas: pdf.numPages});
})()"""

JS_LER_TEXTO = "(function(){ return window.__pjeTexto || ''; })()"

# cabeçalho do documento aberto ("Id abfbdad - Petição Inicial", "Juntado por ... em 29/07/2026 16:33")
JS_CABECALHO = r"""(function(){
  var t = document.querySelector('.cabecalho-esquerda mat-card-title');
  var subs = [].map.call(document.querySelectorAll('.cabecalho-esquerda mat-card-subtitle'),
                         function(s) { return s.textContent.replace(/\s+/g, ' ').trim(); });
  return JSON.stringify({titulo: t ? t.textContent.replace(/\s+/g, ' ').trim() : '', detalhes: subs});
})()"""


def so_digitos(v):
    return re.sub(r"\D", "", v or "")


def formatar(numero):
    """0001368-02.2026.5.07.0038 (25 caracteres, como o campo aceita)."""
    d = so_digitos(numero)
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13:14]}.{d[14:16]}.{d[16:]}"


def _apertar_enter():
    """Enter de verdade no que está com o foco (precisa da Acessibilidade, como os outros cliques)."""
    import subprocess
    subprocess.run(["osascript", "-e", 'tell application "System Events" to key code 36'],
                   capture_output=True, timeout=20)


def _abriu(w, t, antes, url_antes):
    """O clique abriu os detalhes? (aba nova de site, ou a mesma aba saiu da lista do acervo)."""
    novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes and a[2].startswith("http")
             and "presto.oystr" not in a[2]]
    return bool(novas) or (CM.url(w, t) != url_antes and "/processo/" in CM.url(w, t))


def _ler_movimentacao(w, t, href):
    """Abre o documento da movimentação e devolve (cabeçalho, texto por página ou erro)."""
    CM.ir(w, t, href)
    CM.esperar(w, t, maximo=45, folga=2)
    ini, fim = {}, time.monotonic() + 60
    while time.monotonic() < fim:  # o visualizador demora a carregar o PDF
        ini = json.loads(CM.js(w, t, JS_INICIAR_TEXTO))
        if ini.get("ok"):
            break
        time.sleep(3)
    cab = json.loads(CM.js(w, t, JS_CABECALHO))
    if not ini.get("ok"):
        return cab, {"ok": False, "erro": ini.get("erro", "sem visualizador")}
    fim = time.monotonic() + 240  # documentos longos levam mais tempo para ler
    while time.monotonic() < fim:
        v = CM.js(w, t, JS_LER_TEXTO)
        if v:
            return cab, json.loads(v)
        time.sleep(2)
    return cab, {"ok": False, "erro": "tempo esgotado lendo o texto"}


def escrever_txt(numero, url_detalhe, registros):
    """Grava saida/<número>.txt com a tabela de movimentações e o texto de cada documento."""
    SAIDA.mkdir(parents=True, exist_ok=True)
    linhas = [
        f"PROCESSO {formatar(numero)}",
        "=" * 60,
        f"Capturado em: {datetime.now():%d/%m/%Y %H:%M}",
        f"Página de detalhes: {url_detalhe}",
        f"Movimentações com documento: {len(registros)}",
        "",
        "MOVIMENTAÇÕES (da mais nova para a mais antiga, como na tela)",
        "-" * 60,
    ]
    for r in registros:
        doc = re.search(r"ID: ([0-9a-fA-F]+)", r["aria"])
        doc = doc.group(1) if doc else "-"
        lido = "texto lido" if r["texto"] and r["texto"].get("ok") else "SEM TEXTO"
        linhas.append(f"{r['n']:>3}. {r['hora'] or '-'} | {r['quem'] or '-'} | "
                      f"{' - '.join(r['partes']) or '-'} | ID {doc} | {lido}")
    for r in registros:
        linhas += ["", "=" * 60, f"{r['n']}. {r['hora'] or '-'} | {r['quem'] or '-'}",
                   f"Documento: {r['cabecalho'].get('titulo') or ' - '.join(r['partes'])}",
                   *[f"  {d}" for d in r["cabecalho"].get("detalhes", [])], "-" * 60]
        texto = r["texto"]
        if texto and texto.get("ok"):
            for p in texto["paginas"]:
                limpo = re.sub(r"[ \t]+", " ", p["texto"])
                limpo = re.sub(r" *\n *", "\n", limpo).strip()
                linhas += [f"--- página {p['pagina']} ---", limpo, ""]
        else:
            linhas.append(f"(sem texto: {(texto or {}).get('erro', 'não lido')})")
    arq = SAIDA / f"{formatar(numero)}.txt"
    arq.write_text("\n".join(linhas), encoding="utf-8")
    return arq


def capturar_movimentacoes(w, t, numero):
    """Na página de detalhes: abre cada documento da linha do tempo, lê o texto e volta para a lista."""
    url_detalhe = CM.url(w, t).split("#")[0]
    lista = json.loads(CM.js(w, t, JS_LISTA_MOVIMENTACOES))
    print(f"  {numero}: {len(lista)} movimentações com documento")
    registros = []
    for n, item in enumerate(lista, 1):
        href = item["href"] if item["href"].startswith("http") else "https://pje.trt7.jus.br" + item["href"]
        cab, texto = _ler_movimentacao(w, t, href)
        registros.append({"n": n, **item, "cabecalho": cab, "texto": texto})
        status = "texto lido" if texto.get("ok") else f"SEM TEXTO ({texto.get('erro')})"
        print(f"    {n}/{len(lista)} {item['aria'][:70]}: {status}")
        CM.ir(w, t, url_detalhe)  # volta para a linha do tempo para o próximo
        CM.esperar(w, t, maximo=45, folga=3)
        time.sleep(2)
    arq = escrever_txt(numero, url_detalhe, registros)
    print(f"  {numero}: TXT gravado em {arq}")
    return arq


def main(numeros):
    if not numeros:
        print("Passe os números: python3 testar_processos.py <número> [<número> ...]")
        return 2
    cfg = A.config_presto()
    if not cfg.get("PRESTO_PIN"):
        print("Falta PRESTO_PIN no pje-busca/.env")
        return 2
    pasta = LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    try:
        w, t, url = A.entrar_trt7(cfg, destino=pasta / "login")
    except A.AcessoErro as e:
        print("NÃO ENTROU:", e)
        return 1
    print("Login ok:", url)
    for numero in numeros:
        dig = so_digitos(numero)
        if len(dig) != 20:
            print(f"{numero}: número CNJ com {len(dig)} dígitos (esperado 20); pulei")
            continue
        destino = pasta / numero
        CM.ir(w, t, ACERVO)
        CM.esperar(w, t, maximo=45, folga=3)
        if not A._logado(w, t):
            print(f"{numero}: o acervo mandou para o login ({CM.url(w, t)}); veja {destino}")
            continue
        r = json.loads(CM.js(w, t, JS_PESQUISAR % json.dumps(formatar(numero))))
        if not r.get("ok"):
            A._salvar(destino, "acervo_sem_campo", CM.capturar(w, t))
            print(f"{numero}: {r.get('erro')}; veja {destino}")
            continue
        time.sleep(8)  # a lista de resultados vem depois do Enter
        A._salvar(destino, "resultado", CM.capturar(w, t))
        k = json.loads(CM.js(w, t, JS_ONDE_KZ % json.dumps(formatar(numero))))
        if not k.get("ok"):
            print(f"{numero}: {k.get('erro')}; botões vistos: {k.get('botoes')}; veja {destino}")
            continue
        antes = {(a[0], a[1]) for a in CM.todas_abas()}
        url_antes = CM.url(w, t)
        CM.para_frente(w, t)
        CM.clicar_tela(k["x"], k["y"])  # clique de mouse de verdade no ícone KZ
        time.sleep(6)
        if not _abriu(w, t, antes, url_antes):
            # o clique não navegou: foca o botão por JavaScript e aperta Enter
            CM.js(w, t, JS_FOCAR_KZ % json.dumps(formatar(numero)))
            CM.para_frente(w, t)
            _apertar_enter()
            time.sleep(6)
            print(f"  {numero}: o clique de mouse não abriu; tentei Enter no botão")
        novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes and a[2].startswith("http")
                 and "presto.oystr" not in a[2] and a[0] < 2 ** 29 and a[1] < 2 ** 29]
        if novas:  # o PJe abriu os detalhes numa aba nova: segue nela
            w, t = novas[-1][0], novas[-1][1]
        CM.esperar(w, t, maximo=45, folga=3)
        atual = CM.url(w, t)
        A._salvar(destino, "detalhe", CM.capturar(w, t))
        if not A._logado(w, t):
            print(f"{numero}: a tela mandou para o login ({atual}); veja {destino}")
            continue
        if "/processo/" not in atual:
            print(f"{numero}: NÃO abriu os detalhes (ainda em {atual}); veja {destino}")
            continue
        capturar_movimentacoes(w, t, numero)
    print("Capturas em:", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
