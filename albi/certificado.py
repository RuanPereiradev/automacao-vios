"""Albi — site com certificado vencido (cópia do bot/navegador.py; o Albi não importa nada de bot/).

Se o Chrome mostrar "Sua conexão não é particular" porque o certificado do site VENCEU
(net::ERR_CERT_DATE_INVALID), clica em "Avançadas" > "Ir para ... (não seguro)", como a pessoa faria.
Só passa nesse caso e só no endereço esperado: qualquer outro erro de certificado (emissor desconhecido,
nome errado — o que aparece num ataque) continua bloqueando.
"""
_JS_AVISO = ("var d = window.loadTimeDataRaw; return d && d.type === 'SSL' ? "
             "[d.errorCode || '', d.subject || '', d.expirationDate || ''] : null;")


def passar_aviso_certificado(driver, url, espera=15, nome="Sonar"):
    """Passa pelo aviso do Chrome de certificado VENCIDO do site. True se passou."""
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
        log.error("O Chrome bloqueou o %s por %s (%s): não passo, só passo certificado vencido", nome, codigo, assunto)
        return False
    if urlparse(driver.current_url).hostname != urlparse(url).hostname:
        log.error("Aviso de certificado em %s, que não é o %s: não passo", urlparse(driver.current_url).hostname, nome)
        return False
    log.warning("%s com o certificado vencido (%s, venceu em %s): cliquei em Avançadas > Ir para %s (não "
                "seguro). Avise o %s para renovar.", nome, assunto, venceu, urlparse(url).hostname, nome)
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
