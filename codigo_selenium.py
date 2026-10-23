from selenium import webdriver
import time

navegador = webdriver.Chrome()

# acessar site do google
navegador.get("https://www.google.com")
navegador.maximize_window()

botao_verde = navegador.find_element("class name", "botao-verde")

botao_verde.click()

time.sleep(3)