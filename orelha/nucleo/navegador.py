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


def criar_driver(headless=True, manter_aberto=False, pasta_downloads=None):
    """Chrome (o Selenium Manager baixa o chromedriver compatível)."""
    opcoes = webdriver.ChromeOptions()
    if headless:
        opcoes.add_argument("--headless=new")
    if manter_aberto:
        opcoes.add_experimental_option("detach", True)
    opcoes.add_argument("--window-size=1920,1080")
    if pasta_downloads:
        opcoes.add_experimental_option("prefs", {"download.default_directory": str(pasta_downloads),
                                                 "download.prompt_for_download": False})
    return webdriver.Chrome(options=opcoes)


# --- VIOS com certificado vencido ---
# Se o Chrome mostrar "Sua conexão não é particular" porque o certificado do VIOS VENCEU
# (net::ERR_CERT_DATE_INVALID), clica em "Avançadas" > "Ir para ... (não seguro)", como a pessoa faria.
# Só passa nesse caso e só no endereço do VIOS: qualquer outro erro de certificado (emissor desconhecido,
# nome errado — o que aparece num ataque) continua bloqueando o login.
_JS_AVISO = ("var d = window.loadTimeDataRaw; return d && d.type === 'SSL' ? "
             "[d.errorCode || '', d.subject || '', d.expirationDate || ''] : null;")


def passar_aviso_certificado(driver, url, espera=15):
    """Passa pelo aviso do Chrome de certificado VENCIDO do VIOS. True se passou."""
    import logging
    import time
    from urllib.parse import urlparse

    from selenium.webdriver.common.by import By

    log = logging.getLogger("orelha")  # o logger do Orelha (vai para o orelha.log)
    try:
        aviso = driver.execute_script(_JS_AVISO)
    except Exception:  # noqa: BLE001 — página normal ou ainda carregando: não há aviso
        return False
    if not isinstance(aviso, list) or len(aviso) != 3:
        return False
    codigo, assunto, venceu = aviso
    if codigo != "net::ERR_CERT_DATE_INVALID":
        log.error("O Chrome bloqueou o VIOS por %s (%s): não passo, só passo certificado vencido", codigo, assunto)
        return False
    if urlparse(driver.current_url).hostname != urlparse(url).hostname:
        log.error("Aviso de certificado em %s, que não é o VIOS: não passo", urlparse(driver.current_url).hostname)
        return False
    log.warning("VIOS com o certificado vencido (%s, venceu em %s): cliquei em Avançadas > Ir para %s (não "
                "seguro). Avise o VIOS para renovar.", assunto, venceu, urlparse(url).hostname)
    driver.find_element(By.ID, "details-button").click()
    driver.find_element(By.ID, "proceed-link").click()
    fim = time.monotonic() + espera
    while time.monotonic() < fim:
        time.sleep(0.5)
        try:
            if not driver.execute_script(_JS_AVISO):
                return True
        except Exception:  # noqa: BLE001 — página trocando
            pass
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
