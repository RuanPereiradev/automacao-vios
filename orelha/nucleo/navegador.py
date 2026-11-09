"""Chrome do Orelha e o bloqueio de envios (somente leitura).

Ideia copiada do Zangão (branch bot-edita-vios, bot/navegador.py: bloquear_envios /
envios_bloqueados), com uma diferença: o calendário do VIOS carrega as tarefas por POST (XHR).
O Zangão resolve lendo o calendário ANTES de ligar o bloqueio; o Orelha liga o bloqueio já no
login (ORELHA_BLOQUEIO_NO_LOGIN=true, padrão; false = logo depois do login) e, só nas pesquisas, libera XHR/fetch com `pesquisa_liberada(driver)`:

  bloqueio "total" (padrão, desde o login):
    - envio de formulário (submit, form.submit, requestSubmit, Enter/clique em botão de envio);
    - fetch/XHR que não seja GET/HEAD;
    - navigator.sendBeacon.
  bloqueio "pesquisa" (dentro de `with pesquisa_liberada(driver):`):
    - continua barrando formulário e sendBeacon;
    - deixa passar fetch/XHR POST (o calendário e os filtros buscam os dados assim), MAS:
        * nunca para endereço com trecho de ORELHA_URL_PROIBIDA (act=del, int-lanca.php...);
        * se ORELHA_XHR_PERMITIDO tiver trechos (ex.: o endpoint dos eventos do calendário), só
          para endereço que tenha um deles. Vazio = qualquer endereço não proibido (conferir na
          tela real qual é o endpoint e preencher, para o modo pesquisa ficar mais estreito).

Exceção documentada: o formulário que o PRÓPRIO Orelha marca com data-orelha-pesquisa="1"
(nucleo.vios.enviar_pesquisa, ex.: a pesquisa de intimações) é enviado. Formulário enviado pela
página por conta própria (ex.: salvar automático) continua barrado.

Toda tentativa barrada fica em window.__orelhaBarrados (ver `tentativas_barradas`) e no console.
"""
import json
from contextlib import contextmanager

from selenium import webdriver

_BLOQUEIO = """
(() => {
    if (window.__somenteLeitura) return;
    const barrados = [];
    Object.defineProperty(window, '__orelhaBarrados', {value: barrados});
    const LISTAS = __ORELHA_LISTAS__;
    const ok = m => ['GET', 'HEAD'].includes(String(m || 'GET').toUpperCase());
    const tem = (u, trechos) => trechos.some(t => String(u || '').toLowerCase().includes(t));
    // modo pesquisa: POST só para endereço não proibido e (se houver lista) permitido
    const liberado = u => window.__orelhaPesquisaLiberada === true && !tem(u, LISTAS.proibidos) &&
        (!LISTAS.permitidos.length || tem(u, LISTAS.permitidos));
    const avisar = o => { barrados.push(o); console.warn('[SOMENTE LEITURA] bloqueado: ' + o); };
    const marcado = f => !!(f && f.getAttribute && f.getAttribute('data-orelha-pesquisa') === '1');
    const fetchOrig = window.fetch;
    if (fetchOrig) window.fetch = function (entrada, opcoes) {
        const m = (opcoes && opcoes.method) || (entrada && entrada.method) || 'GET';
        const u = typeof entrada === 'string' ? entrada : (entrada && (entrada.url || entrada.href)) || '';
        if (!ok(m) && !liberado(u)) { avisar('fetch ' + m + ' ' + u); return Promise.reject(new Error('somente leitura')); }
        return fetchOrig.apply(this, arguments);
    };
    const openOrig = XMLHttpRequest.prototype.open, sendOrig = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m, u) { this.__metodo = m; this.__url = u; return openOrig.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
        if (!ok(this.__metodo) && !liberado(this.__url)) { avisar('XHR ' + this.__metodo + ' ' + this.__url); throw new Error('somente leitura'); }
        return sendOrig.apply(this, arguments);
    };
    if (navigator.sendBeacon) navigator.sendBeacon = () => { avisar('sendBeacon'); return false; };
    const submitOrig = HTMLFormElement.prototype.submit, requestOrig = HTMLFormElement.prototype.requestSubmit;
    HTMLFormElement.prototype.submit = function () {
        if (marcado(this)) return submitOrig.apply(this, arguments);
        avisar('form.submit ' + (this.action || ''));
    };
    if (requestOrig) HTMLFormElement.prototype.requestSubmit = function () {
        if (marcado(this)) return requestOrig.apply(this, arguments);
        avisar('form.requestSubmit ' + (this.action || ''));
    };
    window.addEventListener('submit', e => {
        if (marcado(e.target)) return;
        e.preventDefault(); e.stopImmediatePropagation(); avisar('submit ' + ((e.target && e.target.action) || ''));
    }, true);
    Object.defineProperty(window, '__somenteLeitura', {value: true});
})();
"""

_LIBERAR = "window.__orelhaPesquisaLiberada = true;"


def criar_driver(headless=True, manter_aberto=False, pasta_downloads=None, aceitar_certificado=False):
    """Chrome (o Selenium Manager baixa o chromedriver compatível). aceitar_certificado=True: o VIOS está com
    o certificado vencido e a impressão digital conferiu (certificado_vencido_aceito)."""
    opcoes = webdriver.ChromeOptions()
    if aceitar_certificado:
        opcoes.accept_insecure_certs = True
    if headless:
        opcoes.add_argument("--headless=new")
    if manter_aberto:
        opcoes.add_experimental_option("detach", True)
    opcoes.add_argument("--window-size=1920,1080")
    if pasta_downloads:
        opcoes.add_experimental_option("prefs", {"download.default_directory": str(pasta_downloads),
                                                 "download.prompt_for_download": False})
    return webdriver.Chrome(options=opcoes)


# --- VIOS com certificado vencido (VIOS_CERTIFICADO_VENCIDO no .env) ---
# Aceita SÓ o certificado cuja impressão digital SHA-256 está no .env: se o VIOS mostrar outro (renovado ou
# falso), o Chrome confere normalmente. Tirar a linha do .env quando o VIOS renovar.
def _impressao_do_servidor(url, timeout=10):
    import hashlib
    import socket
    import ssl
    from urllib.parse import urlparse
    u = urlparse(url)
    contexto = ssl.create_default_context()
    contexto.check_hostname = False
    contexto.verify_mode = ssl.CERT_NONE  # só para LER o certificado e comparar com o do .env
    with socket.create_connection((u.hostname, u.port or 443), timeout) as s, \
            contexto.wrap_socket(s, server_hostname=u.hostname) as t:
        return hashlib.sha256(t.getpeercert(binary_form=True)).hexdigest()


def certificado_vencido_aceito(url, impressao):
    """True só se `impressao` (VIOS_CERTIFICADO_VENCIDO) for a do certificado que o VIOS mostra agora."""
    import logging
    import re
    log = logging.getLogger(__name__)
    alvo = re.sub(r"[^0-9a-f]", "", (impressao or "").lower())
    if not alvo or not (url or "").startswith("https://"):
        return False
    try:
        atual = _impressao_do_servidor(url)
    except OSError as e:
        log.warning("VIOS_CERTIFICADO_VENCIDO: não consegui ler o certificado do VIOS (%s); o Chrome confere "
                    "normalmente", e.__class__.__name__)
        return False
    if atual == alvo:
        log.warning("VIOS com certificado vencido: aceito só este (a impressão digital confere com "
                    "VIOS_CERTIFICADO_VENCIDO). Tire a linha do .env quando o VIOS renovar.")
        return True
    log.warning("VIOS_CERTIFICADO_VENCIDO está no .env, mas o VIOS mostra outro certificado: o Chrome confere "
                "normalmente (se o VIOS renovou, tire a linha do .env)")
    return False


def script_bloqueio(permitidos=(), proibidos=()):
    """O JS do bloqueio com as listas do modo pesquisa (trechos de endereço, em minúsculas)."""
    listas = {"permitidos": [t.strip().lower() for t in permitidos or () if t and t.strip()],
              "proibidos": [t.strip().lower() for t in proibidos or () if t and t.strip()]}
    return _BLOQUEIO.replace("__ORELHA_LISTAS__", json.dumps(listas))


def bloquear_envios(driver, permitidos=(), proibidos=()):
    """Liga o bloqueio para todas as páginas abertas daqui em diante (o main.py chama antes do
    login; o form de login é marcado pelo Orelha). Vale a partir da próxima página aberta: abra uma
    página e confira com envios_bloqueados.

    permitidos (ORELHA_XHR_PERMITIDO) e proibidos (ORELHA_URL_PROIBIDA) limitam o XHR/fetch POST que o
    modo pesquisa deixa passar."""
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                           {"source": script_bloqueio(permitidos, proibidos)})


def envios_bloqueados(driver):
    """True se o bloqueio está ativo na página atual (nos dois níveis)."""
    return driver.execute_script("return window.__somenteLeitura === true") is True


def nivel_bloqueio(driver):
    """'total', 'pesquisa' ou None (sem bloqueio) na página atual."""
    if not envios_bloqueados(driver):
        return None
    liberada = driver.execute_script("return window.__orelhaPesquisaLiberada === true") is True
    return "pesquisa" if liberada else "total"


def tentativas_barradas(driver):
    """O que o bloqueio barrou na página atual, ex.: ['XHR POST sys/agenda/...']."""
    try:
        return list(driver.execute_script("return (window.__orelhaBarrados || []).slice()") or [])
    except Exception:
        return []


@contextmanager
def pesquisa_liberada(driver):
    """Libera fetch/XHR POST nas páginas abertas dentro do bloco (e na atual); formulário e
    sendBeacon continuam barrados. Use só para abrir/pesquisar/filtrar, nunca para gravar:

        with pesquisa_liberada(ctx.driver):
            vios.abrir(ctx, URL_CALENDARIO)
            ...
    """
    ident = driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": _LIBERAR})
    driver.execute_script(_LIBERAR)
    try:
        yield
    finally:
        try:
            driver.execute_cdp_cmd("Page.removeScriptToEvaluateOnNewDocument",
                                   {"identifier": (ident or {}).get("identifier", "")})
        finally:
            driver.execute_script("window.__orelhaPesquisaLiberada = false;")
