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
