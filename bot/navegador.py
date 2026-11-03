from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def criar_driver(headless=False, manter_aberto=False):
    # O Selenium Manager baixa o chromedriver compatível automaticamente
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    if manter_aberto:
        # o Chrome não fecha quando o script termina
        options.add_experimental_option("detach", True)
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


# Somente leitura: carregado antes dos scripts de cada página nova. Bloqueia envio de
# formulário e requisição que não seja GET/HEAD (fetch, XHR, sendBeacon), inclusive os
# disparados pela própria página (ex.: salvar automático).
_BLOQUEIO = """
(() => {
    if (window.__somenteLeitura) return;
    const ok = m => ['GET', 'HEAD'].includes(String(m || 'GET').toUpperCase());
    const avisar = o => console.warn('[SOMENTE LEITURA] bloqueado: ' + o);
    const fetchOrig = window.fetch;
    window.fetch = function (entrada, opcoes) {
        const m = (opcoes && opcoes.method) || (entrada && entrada.method) || 'GET';
        if (!ok(m)) { avisar('fetch ' + m); return Promise.reject(new Error('somente leitura')); }
        return fetchOrig.apply(this, arguments);
    };
    const openOrig = XMLHttpRequest.prototype.open, sendOrig = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (m) { this.__metodo = m; return openOrig.apply(this, arguments); };
    XMLHttpRequest.prototype.send = function () {
        if (!ok(this.__metodo)) { avisar('XHR ' + this.__metodo); throw new Error('somente leitura'); }
        return sendOrig.apply(this, arguments);
    };
    if (navigator.sendBeacon) navigator.sendBeacon = () => { avisar('sendBeacon'); return false; };
    HTMLFormElement.prototype.submit = function () { avisar('form.submit'); };
    HTMLFormElement.prototype.requestSubmit = function () { avisar('form.requestSubmit'); };
    window.addEventListener('submit', e => { e.preventDefault(); e.stopImmediatePropagation(); avisar('submit'); }, true);
    Object.defineProperty(window, '__somenteLeitura', {value: true});
})();
"""


def bloquear_envios(driver):
    """Liga o bloqueio de envios para todas as páginas abertas daqui em diante (depois do login)."""
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": _BLOQUEIO})


def envios_bloqueados(driver):
    """True se o bloqueio está ativo na página atual."""
    return driver.execute_script("return window.__somenteLeitura === true") is True


def esperar(driver, locator, timeout):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))


def clicar(driver, locator, timeout):
    elemento = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
    elemento.click()
    return elemento


def preencher(driver, locator, texto, timeout):
    elemento = esperar(driver, locator, timeout)
    elemento.clear()
    elemento.send_keys(texto)
    return elemento
