import logging

from bot.navegador import clicar

log = logging.getLogger(__name__)


def ir_ate_tabela(driver, cfg):
    for i, passo in enumerate(cfg.passos, 1):
        log.info("Passo %d/%d: clicando em %s", i, len(cfg.passos), passo[1])
        clicar(driver, passo, cfg.timeout)

    if cfg.url_final:
        log.info("Indo para %s", cfg.url_final)
        driver.get(cfg.url_final)
