import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.navegador import clicar, esperar, preencher

log = logging.getLogger(__name__)


class LoginErro(Exception):
    pass


def fazer_login(driver, cfg):
    log.info("Abrindo %s", cfg.url)
    driver.get(cfg.url)

    preencher(driver, cfg.campo_usuario, cfg.usuario, cfg.timeout)
    campo_senha = preencher(driver, cfg.campo_senha, cfg.senha, cfg.timeout)
    url_login = driver.current_url
    if cfg.botao_login:
        clicar(driver, cfg.botao_login, cfg.timeout)
    else:
        campo_senha.send_keys(Keys.ENTER)

    try:
        if cfg.login_sucesso:
            esperar(driver, cfg.login_sucesso, cfg.timeout)
        else:
            WebDriverWait(driver, cfg.timeout).until(EC.url_changes(url_login))
    except TimeoutException:
        raise LoginErro(
            f"Login não confirmado em {cfg.timeout}s "
            "(usuário/senha errados ou LOGIN_SUCESSO incorreto)"
        )
    log.info("Login OK como %s", cfg.usuario)
