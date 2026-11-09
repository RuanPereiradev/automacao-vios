from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# de quanto em quanto tempo as esperas olham a tela de novo (o padrão do Selenium é 0,5 s)
POLL = 0.1


def criar_driver(headless=False, manter_aberto=False, rapido=True):
    # O Selenium Manager baixa o chromedriver compatível automaticamente
    import os
    options = webdriver.ChromeOptions()
    if certificado_vencido_aceito(os.getenv("SISTEMA_URL", "").strip(), os.getenv("VIOS_CERTIFICADO_VENCIDO", "")):
        options.accept_insecure_certs = True
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
