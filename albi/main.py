"""Albi — bot do Sonar (Leme Forense). Separado do Ultron e do Zangão: tem .venv, .env, logs/ e
saida/ próprios dentro de albi/ e não importa nada do bot/.

Por enquanto: entra no Sonar (encerrando a outra sessão se cair em /login-conflito) e abre
Pesquisa de Processos > novo pedido. As próximas etapas entram em main(), depois disso.

uso (dentro de albi/): ./rodar.sh   ou   .venv/bin/python main.py [caminho/do/.env]
"""
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PASTA = Path(__file__).resolve().parent
LOGS = PASTA / "logs"
log = logging.getLogger("albi")
OBRIGATORIAS = ("SONAR_URL", "SONAR_CPF_CNPJ", "SONAR_EMAIL", "SONAR_SENHA")
PADROES = {
    "LOGIN_CAMPO_CPF_CNPJ": "css:#loginform input[id=input-cpf-cnpj]",
    "LOGIN_CAMPO_EMAIL": "css:#loginform input[id=loginform-username]",
    "LOGIN_CAMPO_SENHA": "css:#loginform input[id=loginform-password]",
    "LOGIN_BOTAO": "css:#loginform [id=btn-login]",
    "CONFLITO_BOTAO": "xpath://button[@type='submit'][contains(normalize-space(.), 'Encerrar a outra sess')]",
}
CAMINHO_NOVO_PEDIDO = "/modulos/pesquisa-processos/novo-pedido"


class AlbiErro(Exception):
    pass


def configurar_log():
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(LOGS / "albi.log", encoding="utf-8")])


def seletor(texto):
    """css:<seletor> ou xpath:<expressão> -> (By, valor)."""
    tipo, _, valor = texto.partition(":")
    if tipo == "css":
        return By.CSS_SELECTOR, valor
    if tipo == "xpath":
        return By.XPATH, valor
    raise AlbiErro(f"seletor inválido (use css: ou xpath:): {texto}")


def carregar(caminho_env):
    if not Path(caminho_env).exists():
        raise AlbiErro(f"não achei {caminho_env}: copie o .env.example para .env e preencha")
    load_dotenv(caminho_env, override=True)
    faltando = [k for k in OBRIGATORIAS if not os.getenv(k, "").strip()]
    if faltando:
        raise AlbiErro(f"preencha no {caminho_env}: {', '.join(faltando)}")
    cpf = re.sub(r"\D", "", os.getenv("SONAR_CPF_CNPJ"))
    if len(cpf) not in (11, 14):
        raise AlbiErro("SONAR_CPF_CNPJ tem que ter 11 números (CPF) ou 14 (CNPJ)")
    return {
        "url": os.getenv("SONAR_URL").strip(), "cpf": cpf, "email": os.getenv("SONAR_EMAIL").strip(),
        "senha": os.getenv("SONAR_SENHA"),  # sem strip: espaço pode fazer parte da senha
        **{k.lower(): seletor(os.getenv(k, "").strip() or v) for k, v in PADROES.items()},
        "headless": os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "sim"),
        "timeout": int(os.getenv("TIMEOUT", "20").strip() or 20),
    }


def pagina(driver):
    """Caminho da URL atual, sem barra no fim: /login, /login-conflito, /modulos/..."""
    return urlparse(driver.current_url).path.rstrip("/") or "/"


def enviar_login(driver, cfg, espera):
    """Preenche CPF/CNPJ, e-mail e senha e clica em Entrar."""
    for chave, valor in (("login_campo_cpf_cnpj", cfg["cpf"]), ("login_campo_email", cfg["email"]),
                         ("login_campo_senha", cfg["senha"])):
        campo = espera.until(EC.visibility_of_element_located(cfg[chave]))
        campo.clear()
        campo.send_keys(valor)
    espera.until(EC.element_to_be_clickable(cfg["login_botao"])).click()
    try:
        # sai da tela de login: entrou ou caiu na tela de conflito
        espera.until(lambda d: pagina(d) != "/login")
    except TimeoutException:
        # continua na tela de login: mostra a mensagem do Sonar (sem repetir os dados digitados)
        avisos = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, "#loginform .invalid-feedback, "
                  "#loginform .help-block, .alert") if e.text.strip()]
        raise AlbiErro("login não confirmado" + (": " + " | ".join(avisos) if avisos else
                                                   f" em {cfg['timeout']}s (confira CPF/CNPJ, e-mail e senha)"))


def entrar(driver, cfg):
    """Entra no Sonar. Se cair em /login-conflito (já tem sessão aberta em outro lugar), clica em
    "Encerrar a outra sessão" e, se voltar para a tela de login, entra de novo."""
    espera = WebDriverWait(driver, cfg["timeout"])
    driver.get(cfg["url"])
    enviar_login(driver, cfg, espera)
    if pagina(driver) == "/login-conflito":
        log.info("Tela de conflito: encerrando a outra sessão")
        espera.until(EC.element_to_be_clickable(cfg["conflito_botao"])).click()
        espera.until(lambda d: pagina(d) != "/login-conflito")
        if pagina(driver) == "/login":
            log.info("Voltou para a tela de login: entrando de novo")
            enviar_login(driver, cfg, espera)
    if pagina(driver).startswith("/login"):
        raise AlbiErro(f"login não confirmado: ficou em {driver.current_url}")


def abrir_novo_pedido(driver, cfg):
    """Vai direto para a tela de novo pedido da Pesquisa de Processos."""
    url = urljoin(cfg["url"], CAMINHO_NOVO_PEDIDO)
    driver.get(url)
    espera = WebDriverWait(driver, cfg["timeout"])
    try:
        espera.until(lambda d: d.execute_script("return document.readyState") == "complete"
                     and pagina(d) == CAMINHO_NOVO_PEDIDO)
    except TimeoutException:
        raise AlbiErro(f"não abriu a tela de novo pedido: ficou em {driver.current_url}")


def main(*args):
    configurar_log()
    caminho_env = args[0] if args else str(PASTA / ".env")
    try:
        cfg = carregar(caminho_env)
    except AlbiErro as e:
        log.error("Configuração: %s", e)
        return 2
    log.info("Entrando no Sonar com CPF/CNPJ final %s e e-mail %s", cfg["cpf"][-2:], cfg["email"])
    opcoes = webdriver.ChromeOptions()
    if cfg["headless"]:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1600,1000")
    driver = webdriver.Chrome(options=opcoes)
    try:
        entrar(driver, cfg)
        log.info("Login OK: %s", driver.current_url)
        abrir_novo_pedido(driver, cfg)
        log.info("Tela de novo pedido aberta: %s", driver.current_url)
        # próximas etapas do Albi entram aqui
        return 0
    except Exception as e:
        print_ = LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
        try:
            driver.save_screenshot(str(print_))
        except Exception:
            pass
        log.error("Falhou: %s (print em %s)", e, print_)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
