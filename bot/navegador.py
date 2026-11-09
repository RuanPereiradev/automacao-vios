from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# de quanto em quanto tempo as esperas olham a tela de novo (o padrão do Selenium é 0,5 s)
POLL = 0.1


def criar_driver(headless=False, manter_aberto=False, rapido=True):
    # O Selenium Manager baixa o chromedriver compatível automaticamente
    options = webdriver.ChromeOptions()
    if rapido:
        # NAVEGADOR_RAPIDO: o driver.get não espera recursos que o robô não usa; as esperas do robô
        # continuam (página completa, jQuery parado, editor pronto). As imagens continuam: sem elas
        # o VIOS não desenha os botões "Texto intimação" e "Concluir tarefa?" e o print perde a prova.
        options.page_load_strategy = "eager"
    if headless:
        options.add_argument("--headless=new")
    if manter_aberto:
        # o Chrome não fecha quando o script termina
        options.add_experimental_option("detach", True)
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


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

    log = logging.getLogger(__name__)
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


def esperar(driver, locator, timeout):
    return WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.visibility_of_element_located(locator))


def clicar(driver, locator, timeout):
    elemento = WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.element_to_be_clickable(locator))
    elemento.click()
    return elemento


def preencher(driver, locator, texto, timeout):
    elemento = esperar(driver, locator, timeout)
    elemento.clear()
    elemento.send_keys(texto)
    return elemento
