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
