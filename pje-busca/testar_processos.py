"""Abre processos do TRT7 depois do login pelo Presto e salva o que a tela mostra (só Mac).

  cd pje-busca && python3 testar_processos.py 0001368-02.2026.5.07.0038 0002754-04.2025.5.07.0038

Faz o login (console do Presto > Sites > TRT7 > Login via Presto) e, na mesma aba, abre o acervo geral do
PJe (painel do usuário externo), digita o número de cada processo, aperta Enter, clica de mouse no ícone KZ (botão "Detalhes do Processo" do número); os detalhes abrem em aba nova e o
script segue nela, salvando a página de detalhes (/pjekz/processo/<id>/detalhe). Não baixa autos.
Salva print, HTML, texto e a lista de elementos de cada tela em logs/processos/<data_hora>/<número>/.
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
# onde fica o ícone KZ do botão "Detalhes do Processo <classe> <número>" (role=link) na tela, em coordenadas
# da tela. O clique é de mouse de verdade (o botão do PJe não responde a click() por JavaScript). Ao clicar,
# o PJe abre os detalhes numa aba nova.
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
LOGS = AQUI / "logs" / "processos"

# link do documento "Decisão" na linha do tempo da página de detalhes (abre /pjekz/processo/<id>/documento/<id>/conteudo)
DOC_TIPO = "Decisão"
JS_LINK_DOCUMENTO = r"""(function(tipo){
  var links = [].filter.call(document.querySelectorAll('a[href*="/documento/"][href$="/conteudo"]'), function(a) {
    return (a.getAttribute('aria-label') || '').indexOf(tipo) >= 0;
  });
  if (!links.length) return JSON.stringify({ok: false, erro: 'link do documento ' + tipo + ' não achado'});
  var a = links[0];
  return JSON.stringify({ok: true, href: a.getAttribute('href'), aria: a.getAttribute('aria-label')});
})(%s)"""
# texto da camada de texto do visualizador (pdf.js): uma linha por <br>, uma página por .page
JS_TEXTO_PDF = r"""(function(){
  function docs(raiz, out) {
    out.push(raiz);
    [].forEach.call(raiz.querySelectorAll('iframe'), function(f) { try { if (f.contentDocument) docs(f.contentDocument, out); } catch (e) {} });
    return out;
  }
  var pags = [];
  docs(document, []).forEach(function(doc) {
    [].forEach.call(doc.querySelectorAll('.page[data-page-number]'), function(pg) {
      var tl = pg.querySelector('.textLayer');
      if (!tl) return;
      var txt = '';
      [].forEach.call(tl.childNodes, function(n) {
        if (n.nodeName === 'BR') txt += '\n';
        else if (n.nodeType === 1) txt += n.textContent;
      });
      pags.push({pagina: parseInt(pg.getAttribute('data-page-number'), 10), texto: txt});
    });
  });
  pags.sort(function(a, b) { return a.pagina - b.pagina; });
  return JSON.stringify({paginas: pags});
})()"""


def abrir_decisao(w, t, destino):
    """Na página de detalhes: acha o link da Decisão, abre o documento e grava o texto da camada de texto."""
    k = json.loads(CM.js(w, t, JS_LINK_DOCUMENTO % json.dumps(DOC_TIPO)))
    if not k.get("ok"):
        print("  decisão:", k.get("erro"))
        return None
    doc_id = re.search(r"ID: ([0-9a-fA-F]+)", k.get("aria") or "")
    doc_id = doc_id.group(1) if doc_id else "documento"
    href = k["href"] if k["href"].startswith("http") else "https://pje.trt7.jus.br" + k["href"]
    CM.ir(w, t, href)
    CM.esperar(w, t, maximo=45, folga=3)
    texto_paginas = []
    fim = time.monotonic() + 40  # o visualizador carrega a camada de texto aos poucos
    while time.monotonic() < fim:
        v = json.loads(CM.js(w, t, JS_TEXTO_PDF))
        texto_paginas = [p for p in v.get("paginas", []) if p["texto"].strip()]
        if texto_paginas:
            break
        time.sleep(2)
    if not texto_paginas:
        A._salvar(destino, "documento_sem_texto", CM.capturar(w, t))
        print(f"  decisão {doc_id}: a página não mostrou texto (veja {destino})")
        return None
    linhas = [f"DECISÃO - documento {doc_id} (capturada do PJe)", f"Origem: {href}", ""]
    for p in texto_paginas:
        limpo = re.sub(r"[ \t]+", " ", p["texto"])
        limpo = re.sub(r" *\n *", "\n", limpo).strip()
        linhas += [f"--- página {p['pagina']} ---", limpo, ""]
    arq = destino / f"decisao_{doc_id}.txt"
    arq.write_text("\n".join(linhas), encoding="utf-8")
    print(f"  decisão {doc_id}: {len(texto_paginas)} página(s) gravada(s) em {arq}")
    return arq




def so_digitos(v):
    return re.sub(r"\D", "", v or "")


def formatar(numero):
    """0001368-02.2026.5.07.0038 (25 caracteres, como o campo aceita)."""
    d = so_digitos(numero)
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13:14]}.{d[14:16]}.{d[16:]}"


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
        CM.para_frente(w, t)
        CM.clicar_tela(k["x"], k["y"])  # clique de mouse de verdade no ícone KZ
        time.sleep(6)
        novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes and a[2].startswith("http")
                 and "presto.oystr" not in a[2] and a[0] < 2 ** 29 and a[1] < 2 ** 29]
        if novas:  # o PJe abriu os detalhes numa aba nova: segue nela
            w, t = novas[-1][0], novas[-1][1]
        CM.esperar(w, t, maximo=45, folga=3)
        atual = CM.url(w, t)
        cap = CM.capturar(w, t)
        A._salvar(destino, "detalhe", cap)
        if not A._logado(w, t):
            print(f"{numero}: a tela mandou para o login ({atual}); veja {destino}")
            continue
        abrir_decisao(w, t, destino)
        titulo = " ".join((cap.get("titulo") or "").split())[:100]
        print(f"{numero}: {titulo} · {atual} · {len(cap.get('elementos', []))} elementos · {destino}")
    print("Capturas em:", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
