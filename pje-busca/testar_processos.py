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
    var abrir = li.querySelector('a.tl-documento[id^="abrirdoc_"]');
    out.push({href: a.getAttribute('href'), aria: a.getAttribute('aria-label') || '',
              abrir: abrir ? abrir.id : '', curto: abrir ? abrir.id.replace('abrirdoc_', '') : '',
              hora: hora ? hora.getAttribute('aria-label') : '', quem: quem ? quem.getAttribute('aria-label') : '',
              partes: partes});
  });
  return JSON.stringify(out);
})()"""

# clica no link "abrirdoc_<id>" da linha: o PJe mostra o documento no painel da direita (mesma página)
JS_CLICAR_DOC = r"""(function(id){
  var a = document.getElementById(id);
  if (!a) return JSON.stringify({ok: false, erro: 'link ' + id + ' não achado'});
  a.click();
  return JSON.stringify({ok: true});
})(%s)"""

# endereço do PDF que o visualizador está mostrando agora (o PJe troca o blob a cada documento clicado)
JS_SRC_VISUALIZADOR = r"""(function(){
  var o = document.querySelector('object[data*="viewer.html"], iframe[src*="viewer.html"], embed[src*="viewer.html"]');
  return o ? (o.getAttribute('data') || o.getAttribute('src') || '') : '';
})()"""

# Lê o texto de todas as páginas do PDF aberto no painel da direita.
# O visualizador do PJe (assets/pdf/web/viewer.html, num <object>) é um pdf.js que NÃO expõe PDFViewerApplication;
# por isso lê a camada de texto (.textLayer) que ele desenha: rola até cada página, espera ela renderizar e ordena
# os trechos pela posição na folha (o pdf.js grava negrito/sublinhado fora da ordem de leitura).
# Devolve na hora {ok, paginas} e deixa o resultado em window.__pjeTexto (lido por JS_LER_TEXTO).
# srcAntes: o blob que estava aberto antes do clique (espera o visualizador trocar de documento).
JS_INICIAR_TEXTO = r"""(function(srcAntes){
  function res(o) { return JSON.stringify(o); }
  function blob(u) { var m = /blob:[^#&]+/.exec(decodeURIComponent(u || '')); return m ? m[0] : (u || '').split('#')[0]; }
  window.__pjeTexto = null; window.__pjeProgresso = 0;
  if (document.visibilityState === 'hidden')
    return res({ok: false, motivo: 'oculta', erro: 'a aba está em segundo plano (o Chrome não desenha o PDF)'});
  var o = document.querySelector('object[data*="viewer.html"], iframe[src*="viewer.html"], embed[src*="viewer.html"]');
  if (!o) return res({ok: false, motivo: 'sem_visualizador', erro: 'a página não tem o visualizador de PDF'});
  var src = o.getAttribute('data') || o.getAttribute('src') || '';
  if (srcAntes && src === srcAntes) return res({ok: false, motivo: 'carregando', erro: 'o visualizador ainda mostra o documento anterior'});
  var d;
  try { d = o.contentWindow.document; } catch (e) { return res({ok: false, motivo: 'carregando', erro: 'visualizador inacessível: ' + e}); }
  if (!d || d.readyState !== 'complete' || blob(d.location.href) !== blob(src))
    return res({ok: false, motivo: 'carregando', erro: 'o visualizador ainda está abrindo o documento'});
  var pags = [].slice.call(d.querySelectorAll('#viewer .page'));
  if (!pags.length) return res({ok: false, motivo: 'carregando', erro: 'o PDF ainda não abriu no visualizador'});

  function texto(tl) {
    // Ordena os trechos pela posição que o pdf.js grava no style (left/top/font-size). Não usa a caixa na tela:
    // no viewer do PJe os trechos dentro de <span class="markedContent"> não ficam posicionados (CSS ".textLayer > span")
    // e a caixa deles junta linhas distantes (cabeçalho + rodapé + corpo numa linha só).
    if (!tl) return '';
    var W = tl.clientWidth || 1, H = tl.clientHeight || 1;
    function med(st, prop, ref) {
      var m = new RegExp('(?:^|;)\\s*' + prop + ':\\s*(-?[\\d.]+)(px|%%)?').exec(st);
      if (!m) return null;
      var v = parseFloat(m[1]);
      return m[2] === '%%' ? v * ref / 100 : v;
    }
    var itens = [];
    [].forEach.call(tl.querySelectorAll('span'), function(sp) {
      if (sp.children.length || sp.classList.contains('markedContent')) return;
      var txt = sp.textContent;
      if (!txt) return;
      var st = sp.getAttribute('style') || '', r = sp.getBoundingClientRect();
      var l = med(st, 'left', W), t = med(st, 'top', H), fs = med(st, 'font-size', H) || r.height || 10;
      var sx = /scaleX\(([-\d.]+)\)/.exec(st);
      sx = sx ? parseFloat(sx[1]) : 1;
      if (l === null || t === null) { var b = tl.getBoundingClientRect(); l = r.left - b.left; t = r.top - b.top; sx = 1; }
      itens.push({l: l, t: t, fs: fs, w: r.width * sx, s: txt});
    });
    itens.sort(function(a, b) { return a.t - b.t || a.l - b.l; });
    var linhas = [];
    itens.forEach(function(i) {
      var L = linhas[linhas.length - 1];
      if (L && Math.abs(i.t - L.t) <= Math.max(1, 0.5 * Math.min(i.fs, L.fs))) L.itens.push(i);
      else linhas.push({t: i.t, fs: i.fs, itens: [i]});
    });
    return linhas.map(function(L) {
      L.itens.sort(function(a, b) { return a.l - b.l; });
      var out = '', fim = null;
      L.itens.forEach(function(i) {
        if (fim !== null && i.l - fim > i.fs * 0.15 && !/\s$/.test(out) && !/^\s/.test(i.s)) out += ' ';
        out += i.s; fim = i.l + i.w;
      });
      return out.replace(/\s+$/, '');
    }).filter(function(x) { return x.trim(); }).join('\n');
  }
  function esperar(p, ate) {  // página renderizada e camada de texto completa (ou vazia: PDF digitalizado)
    return new Promise(function(fim) {
      var carregouEm = 0, ultimo = -1, igual = 0;
      (function tenta() {
        var tl = p.querySelector('.textLayer'), n = tl ? tl.querySelectorAll('span').length : 0;
        var carregou = p.getAttribute('data-loaded') === 'true' && !!tl;
        if (carregou && !carregouEm) carregouEm = Date.now();
        if (carregou && tl.querySelector('.endOfContent') && n > 0) return fim(tl);
        if (carregou && n > 0) { igual = (n === ultimo) ? igual + 1 : 0; ultimo = n; if (igual >= 2) return fim(tl); }
        if (carregouEm && n === 0 && Date.now() - carregouEm > 4000) return fim(tl);  // página sem texto
        if (Date.now() > ate) return fim(tl);
        setTimeout(tenta, 250);
      })();
    });
  }
  var out = [], k = 0;
  (function proxima() {
    if (k >= pags.length) {
      var vazias = out.filter(function(x) { return !x.texto.trim(); }).length;
      window.__pjeTexto = res({ok: true, paginas: out, sem_texto: vazias});
      return;
    }
    var p = pags[k];
    try { p.scrollIntoView({block: 'start'}); } catch (e) {}
    esperar(p, Date.now() + 20000).then(function(tl) {
      out.push({pagina: k + 1, texto: texto(tl)});
      k++; window.__pjeProgresso = k;
      setTimeout(proxima, 100);
    }).catch(function(e) { window.__pjeTexto = res({ok: false, erro: 'leitura da página ' + (k + 1) + ': ' + e}); });
  })();
  return res({ok: true, paginas: pags.length});
})(%s)"""

# documento que o PJe mostra em HTML (sem visualizador de PDF): texto do painel do documento
JS_TEXTO_HTML = r"""(function(){
  var fr = [].filter.call(document.querySelectorAll('iframe'), function(f) {
    try { return f.contentDocument && f.contentDocument.body && !/viewer\.html/.test(f.src || ''); } catch (e) { return false; }
  });
  for (var i = 0; i < fr.length; i++) {
    var t = (fr[i].contentDocument.body.innerText || '').trim();
    if (t.length > 50) return JSON.stringify({ok: true, texto: t});
  }
  var cab = document.querySelector('.cabecalho-esquerda');
  for (var el = cab; el && el !== document.body; el = el.parentElement) {
    if (el.querySelector('pje-timeline, li[id^="doc_"]')) break;
    var txt = (el.innerText || '').trim();
    if (txt.length > (cab.innerText || '').length + 200) return JSON.stringify({ok: true, texto: txt});
  }
  return JSON.stringify({ok: false, erro: 'documento sem PDF e sem texto no painel'});
})()"""

JS_LER_TEXTO = "(function(){ return window.__pjeTexto || ''; })()"

# diagnóstico quando a linha do tempo não aparece: quantos elementos o script está vendo
JS_DIAGNOSTICO = r"""(function(){
  return JSON.stringify({url: location.pathname, li_doc: document.querySelectorAll('li[id^="doc_"]').length,
    links_documento: document.querySelectorAll('a[href*="/documento/"]').length,
    links_conteudo: document.querySelectorAll('a[href$="/conteudo"]').length,
    tem_timeline: !!document.querySelector('.pje-timeline'), titulo: document.title});
})()"""

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


def _atalho_d():
    """Control+Option+D (atalho do botão Detalhes do Processo). Precisa da Acessibilidade."""
    import subprocess
    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "d" using {control down, option down}'],
                   capture_output=True, timeout=20)


def _abriu(w, t, antes, url_antes):
    """O clique abriu os detalhes? (aba nova de site, ou a mesma aba saiu da lista do acervo)."""
    novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes and a[2].startswith("http")
             and "presto.oystr" not in a[2]]
    return bool(novas) or (CM.url(w, t) != url_antes and "/processo/" in CM.url(w, t))


ID_MAX = 2 ** 31  # ids de aba do Chrome no AppleScript passam de 1 bilhão (2**29 descartava a aba de detalhes)


def _aba_detalhes(antes, numero):
    """(janela, aba, nova?) da aba /pjekz/processo/<id>/detalhe deste número. Prefere a que o clique acabou de abrir;
    confere pelo título ("Detalhes do processo 1368-02.2026.5.07.0038") ou pelo cabeçalho da página."""
    alvo = formatar(numero)
    cands = [a for a in CM.todas_abas() if re.search(r"/pjekz/processo/\d+/detalhe", a[2])
             and a[0] < ID_MAX and a[1] < ID_MAX]
    cands.sort(key=lambda a: ((a[0], a[1]) in antes, -a[1]))  # novas primeiro; entre elas, a mais recente
    for wj, tj, _ in cands:
        try:
            topo = CM.js(wj, tj, "document.title + ' ' + (document.body ? document.body.innerText.slice(0, 800) : '')")
        except CM.ChromeMacErro:
            continue
        if alvo in topo or alvo.lstrip("0") in topo:
            return wj, tj, (wj, tj) not in antes
    return None


def _ler_na_linha(w, t, item):
    """Clica na linha do tempo, espera o painel da direita trocar para o documento e lê o texto do PDF."""
    cab = json.loads(CM.js(w, t, JS_CABECALHO))
    ja_aberto = cab.get("titulo", "").startswith("Id " + item["curto"])  # o 1º documento já vem aberto
    src_antes = "" if ja_aberto else CM.js(w, t, JS_SRC_VISUALIZADOR)
    if not ja_aberto:
        r = json.loads(CM.js(w, t, JS_CLICAR_DOC % json.dumps(item["abrir"])))
        if not r.get("ok"):
            return {}, {"ok": False, "erro": r.get("erro", "linha sem link de documento")}
        fim = time.monotonic() + 40
        while time.monotonic() < fim:  # o painel troca para o documento clicado
            cab = json.loads(CM.js(w, t, JS_CABECALHO))
            if cab.get("titulo", "").startswith("Id " + item["curto"]):
                break
            time.sleep(1.5)
        else:
            return cab, {"ok": False, "erro": f"o painel não mostrou o documento {item['curto']}"}
    ini, sem_visualizador = {}, None
    fim = time.monotonic() + 60
    while time.monotonic() < fim:  # o visualizador troca o blob e abre o PDF novo
        ini = json.loads(CM.js(w, t, JS_INICIAR_TEXTO % json.dumps(src_antes)))
        if ini.get("ok"):
            break
        if ini.get("motivo") == "oculta":  # aba em segundo plano: o pdf.js só desenha a página visível
            CM.para_frente(w, t)
            continue
        if ini.get("motivo") == "sem_visualizador":  # documento em HTML: lê o texto do painel
            sem_visualizador = sem_visualizador or time.monotonic()
            if time.monotonic() - sem_visualizador > 12:
                h = json.loads(CM.js(w, t, JS_TEXTO_HTML))
                if h.get("ok"):
                    return cab, {"ok": True, "via": "html", "paginas": [{"pagina": 1, "texto": h["texto"]}]}
                return cab, {"ok": False, "erro": h.get("erro")}
        else:
            sem_visualizador = None
        time.sleep(2)
    if not ini.get("ok"):
        return cab, {"ok": False, "erro": ini.get("erro", "sem visualizador")}
    fim = time.monotonic() + 60 + 15 * int(ini.get("paginas") or 1)  # ~15 s por página no pior caso
    while time.monotonic() < fim:
        if CM.js(w, t, "document.visibilityState") == "hidden":  # alguém tirou o Chrome da frente no meio da leitura
            CM.para_frente(w, t)
        v = CM.js(w, t, JS_LER_TEXTO)
        if v:
            return cab, json.loads(v)
        time.sleep(1.5)
    return cab, {"ok": False, "erro": "tempo esgotado lendo o texto"}


def _sem_camada(texto):
    """O PDF abriu, mas nenhuma página tem texto (documento digitalizado: precisaria de OCR)."""
    return bool(texto and texto.get("ok") and texto.get("paginas")
                and texto.get("sem_texto", 0) >= len(texto["paginas"]))


def _status(texto):
    if not (texto and texto.get("ok")):
        return f"SEM TEXTO ({(texto or {}).get('erro', 'não lido')})"
    if _sem_camada(texto):
        return "PDF SEM CAMADA DE TEXTO (digitalizado)"
    return f"texto lido ({len(texto['paginas'])} pág.{', HTML' if texto.get('via') == 'html' else ''})"


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
        lido = _status(r["texto"])
        linhas.append(f"{r['n']:>3}. {r['hora'] or '-'} | {r['quem'] or '-'} | "
                      f"{' - '.join(r['partes']) or '-'} | ID {doc} | {lido}")
    for r in registros:
        linhas += ["", "=" * 60, f"{r['n']}. {r['hora'] or '-'} | {r['quem'] or '-'}",
                   f"Documento: {r['cabecalho'].get('titulo') or ' - '.join(r['partes'])}",
                   *[f"  {d}" for d in r["cabecalho"].get("detalhes", [])], "-" * 60]
        texto = r["texto"]
        if _sem_camada(texto):
            linhas.append("(PDF sem camada de texto: documento digitalizado; precisa de OCR para ler)")
        elif texto and texto.get("ok"):
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
    CM.para_frente(w, t)  # o PDF só é desenhado (e ganha camada de texto) com a aba visível
    print(f"  {numero}: lendo a linha do tempo de {url_detalhe} ...", flush=True)
    lista = json.loads(CM.js(w, t, JS_LISTA_MOVIMENTACOES))
    print(f"  {numero}: {len(lista)} movimentações com documento", flush=True)
    if not lista:
        diag = json.loads(CM.js(w, t, JS_DIAGNOSTICO))
        A._salvar(LOGS / "diagnostico" / numero, "detalhe_sem_lista", CM.capturar(w, t))
        print(f"  {numero}: nenhuma movimentação achada. Na página: {diag}", flush=True)
    registros = []
    for n, item in enumerate(lista, 1):
        print(f"    {n}/{len(lista)} abrindo: {item['aria'][:70]} ...", flush=True)
        cab, texto = _ler_na_linha(w, t, item)
        registros.append({"n": n, **item, "cabecalho": cab, "texto": texto})
        status = _status(texto)
        print(f"    {n}/{len(lista)} {item['aria'][:70]}: {status}", flush=True)
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
    w0, t0 = w, t  # aba do acervo: cada número começa nela
    for numero in numeros:
        dig = so_digitos(numero)
        if len(dig) != 20:
            print(f"{numero}: número CNJ com {len(dig)} dígitos (esperado 20); pulei")
            continue
        destino = pasta / numero
        w, t = w0, t0
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
        print(f"  {numero}: botão achado ({k.get('aria')}) em x={k['x']} y={k['y']}; URL antes: {url_antes}", flush=True)
        CM.para_frente(w, t)
        CM.clicar_tela(k["x"], k["y"])  # clique de mouse de verdade no ícone KZ
        time.sleep(6)
        if not _abriu(w, t, antes, url_antes):
            # o clique não navegou: foca o botão por JavaScript e aperta Enter
            CM.js(w, t, JS_FOCAR_KZ % json.dumps(formatar(numero)))
            CM.para_frente(w, t)
            _apertar_enter()
            time.sleep(6)
            print(f"  {numero}: o clique de mouse não abriu; tentei Enter no botão", flush=True)
        if not _abriu(w, t, antes, url_antes):
            # último recurso: a tecla de atalho do botão (accesskey="d" no PJe = Control+Option+D no Chrome do Mac)
            CM.para_frente(w, t)
            _atalho_d()
            time.sleep(6)
            print(f"  {numero}: tentei o atalho Control+Option+D")
        aba = _aba_detalhes(antes, numero)
        nova = False
        if aba:  # o PJe abriu os detalhes numa aba nova (o normal): segue nela
            w, t, nova = aba
            print(f"  {numero}: detalhes na aba {t}{' (nova)' if nova else ' (já estava aberta)'}", flush=True)
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
        if nova:  # fecha a aba de detalhes que o bot abriu (não acumula abas a cada rodada)
            try:
                CM.fechar_aba(w, t)
            except CM.ChromeMacErro:
                pass
    print("Capturas em:", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
