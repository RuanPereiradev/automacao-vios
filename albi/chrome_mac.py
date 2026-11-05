"""Albi — controla o Google Chrome que JÁ ESTÁ ABERTO no Mac, pelo AppleScript (só macOS).

Por que não Selenium: o Chrome não deixa automação no perfil principal, e um perfil novo/copiado
pede para confirmar a identidade da conta Google. O Chrome do Mac aceita comandos AppleScript:
abrir aba, saber se terminou de carregar, rodar JavaScript na página (ler, clicar) e listar abas.
Tudo acontece no Chrome aberto, com o perfil e a extensão do Presto que já estão lá.

Precisa, uma vez:
  1. no Chrome: menu Visualizar > Desenvolvedor > "Permitir JavaScript de Apple Events";
  2. no macOS: quando aparecer "Terminal quer controlar Google Chrome", clicar em Permitir
     (ou Ajustes do Sistema > Privacidade e Segurança > Automação > Terminal > Google Chrome).
"""
import json
import platform
import subprocess
import time

JS_DESLIGADO = ("O Chrome está com o JavaScript por AppleScript desligado. No Chrome: menu Visualizar > "
                "Desenvolvedor > \"Permitir JavaScript de Apple Events\" (marcar) e rode de novo.")
SEM_PERMISSAO = ("O macOS não deixou o Terminal controlar o Chrome. Ajustes do Sistema > Privacidade e "
                 "Segurança > Automação > Terminal: ligue \"Google Chrome\" e rode de novo.")


class ChromeMacErro(Exception):
    pass


def disponivel():
    return platform.system() == "Darwin"


def _osa(linhas, *args, timeout=90):
    """Roda AppleScript (linhas) com argumentos (item N of argv) e devolve o texto do resultado."""
    cmd = ["osascript"]
    for l in linhas:
        cmd += ["-e", l]
    cmd += [str(a) for a in args]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ChromeMacErro("o Chrome não respondeu a tempo (pode haver uma janela de permissão aberta)")
    if r.returncode != 0:
        err = r.stderr.strip()
        if "JavaScript" in err and ("AppleScript" in err or "Apple Events" in err or "Apple" in err):
            raise ChromeMacErro(JS_DESLIGADO)
        if "-1743" in err or "Not authorized" in err or "autoriza" in err:
            raise ChromeMacErro(SEM_PERMISSAO)
        if "-600" in err or "-609" in err:
            raise ChromeMacErro("o Google Chrome não está aberto")
        raise ChromeMacErro(err or f"osascript saiu com código {r.returncode}")
    return r.stdout.rstrip("\n")


def abrir_aba(url):
    """Abre uma aba nova na janela da frente do Chrome. Devolve (id da janela, id da aba)."""
    s = _osa(['on run argv',
              'tell application "Google Chrome"',
              'if (count of windows) = 0 then error "o Chrome está aberto, mas sem nenhuma janela"',
              'set w to front window',
              'set t to make new tab at end of tabs of w with properties {URL:(item 1 of argv)}',
              'return ((id of w) as text) & "," & ((id of t) as text)',
              'end tell', 'end run'], url)
    w, t = s.split(",")
    return int(w), int(t)


_ABA = 'tab id ((item 2 of argv) as integer) of window id ((item 1 of argv) as integer)'


def carregando(w, t):
    return _osa(['on run argv', 'tell application "Google Chrome"', f'return loading of {_ABA}', 'end tell',
                 'end run'], w, t) == "true"


def esperar(w, t, maximo=45, folga=3):
    """Espera a aba terminar de carregar (e mais `folga` segundos para os scripts da página)."""
    fim = time.monotonic() + maximo
    while time.monotonic() < fim:
        try:
            if not carregando(w, t):
                break
        except ChromeMacErro:
            pass
        time.sleep(1)
    time.sleep(folga)


def js(w, t, codigo):
    """Roda JavaScript na aba e devolve o resultado como texto (use JSON.stringify para objetos)."""
    return _osa(['on run argv', 'tell application "Google Chrome"',
                 f'return execute {_ABA} javascript (item 3 of argv)', 'end tell', 'end run'], w, t, codigo)


def abas(w):
    """[(id, url, título)] das abas da janela."""
    # separadores criados fora do "tell": lá dentro, "tab" é a aba do Chrome, não a tabulação
    s = _osa(['on run argv', 'set sep to character id 9', 'set fim to character id 10', 'set saida to ""',
              'tell application "Google Chrome"',
              'repeat with t in tabs of window id ((item 1 of argv) as integer)',
              'set saida to saida & ((id of t) as text) & sep & (URL of t) & sep & (title of t) & fim',
              'end repeat', 'end tell', 'return saida', 'end run'], w)
    out = []
    for linha in s.splitlines():
        p = linha.split("\t")
        if len(p) >= 3 and p[0].isdigit():
            out.append((int(p[0]), p[1], p[2]))
    return out


def url(w, t):
    return _osa(['on run argv', 'tell application "Google Chrome"', f'return URL of {_ABA}', 'end tell', 'end run'],
                w, t)


# ---------------- JavaScript usado nas páginas ----------------
# percorre a página, os frames do mesmo site e os "shadow roots" abertos (onde extensões costumam pôr botões)
_PERCORRER = r"""
function _albiTodos(raiz, onde, out) {
  var els = raiz.querySelectorAll('*');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    out.push([el, onde]);
    if (el.shadowRoot) _albiTodos(el.shadowRoot, onde + '>shadow', out);
    if ((el.tagName === 'IFRAME' || el.tagName === 'FRAME')) {
      try { if (el.contentDocument) _albiTodos(el.contentDocument, onde + '>frame' + i, out); } catch (e) {}
    }
  }
  return out;
}
function _albiDescr(el, onde) {
  var r = el.getBoundingClientRect ? el.getBoundingClientRect() : {width: 0, height: 0};
  var cls = (typeof el.className === 'string') ? el.className : '';
  var d = {onde: onde, tag: el.tagName.toLowerCase(), texto: ((el.innerText || el.value || '') + '').trim().slice(0, 80),
           id: el.id || '', name: el.getAttribute('name') || '', type: el.getAttribute('type') || '', classe: cls.slice(0, 80),
           href: el.getAttribute('href') || '', title: el.getAttribute('title') || '', alt: el.getAttribute('alt') || '',
           src: (el.getAttribute('src') || '').slice(0, 150), visivel: r.width > 0 && r.height > 0};
  for (var k in d) if (d[k] === '' ) delete d[k];
  return d;
}
var _ALBI_INTERESSA = 'a,button,input,select,textarea,[role=button],[onclick],img,iframe,frame';
"""

JS_CAPTURAR = "(function(){" + _PERCORRER + r"""
  var todos = _albiTodos(document, 'topo', []), elementos = [];
  for (var i = 0; i < todos.length; i++) {
    var el = todos[i][0];
    try { if (el.matches(_ALBI_INTERESSA)) elementos.push(_albiDescr(el, todos[i][1])); } catch (e) {}
  }
  return JSON.stringify({url: location.href, titulo: document.title, elementos: elementos,
                         texto: document.body ? document.body.innerText.slice(0, 30000) : '',
                         html: document.documentElement.outerHTML});
})()"""

# procura (e, com clicar=true, clica) o primeiro elemento visível que mencione o termo
JS_ACHAR = "(function(termo, clicar){" + _PERCORRER + r"""
  var re = new RegExp(termo, 'i'), todos = _albiTodos(document, 'topo', []), achados = [];
  for (var i = 0; i < todos.length; i++) {
    var el = todos[i][0], d;
    try { if (!el.matches(_ALBI_INTERESSA + ',div,span,label')) continue; } catch (e) { continue; }
    d = _albiDescr(el, todos[i][1]);
    var alvo = [d.texto, d.title, d.alt, d.id, d.classe, d.src, d.href, el.getAttribute('aria-label') || ''].join(' ');
    if (re.test(alvo) && d.visivel && (d.texto || '').length < 60) achados.push([el, d]);
  }
  // prefere botão/link a div/span
  achados.sort(function(a, b) { return (/^(button|a|input)$/.test(b[1].tag) ? 1 : 0) - (/^(button|a|input)$/.test(a[1].tag) ? 1 : 0); });
  if (achados.length && clicar) { achados[0][0].click(); }
  return JSON.stringify({achados: achados.slice(0, 10).map(function(x) { return x[1]; }), clicou: !!(achados.length && clicar)});
})"""


def capturar(w, t):
    """{url, titulo, elementos, texto, html} da aba."""
    return json.loads(js(w, t, JS_CAPTURAR))


def achar(w, t, termo, clicar=False):
    """{"achados": [...], "clicou": bool}: elementos visíveis que mencionam o termo (regex, sem caixa)."""
    return json.loads(js(w, t, f"{JS_ACHAR}({json.dumps(termo)}, {'true' if clicar else 'false'})"))


def print_tela(caminho):
    """Print da tela inteira (o macOS pede a permissão "Gravação de Tela" para o Terminal na primeira vez)."""
    try:
        r = subprocess.run(["screencapture", "-x", str(caminho)], capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
