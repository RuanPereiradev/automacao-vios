"""Chrome protegido + login no VIOS, só leitura (mesma ordem do orelha/main.py, entrar_no_vios).

O bloqueio de envios é ligado ANTES do login (o form de login é marcado pela Orelha e passa) e conferido
na primeira página aberta depois dele. Sem bloqueio ativo nada é lido (BloqueioInativo).
"""
import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from nucleo import navegador, vios

log = logging.getLogger("consulta")
# espera (s) antes de cada tentativa de login; senha errada não é repetida
ESPERAS_LOGIN = (0, 30, 90)


@dataclass
class Ctx:
    """O mínimo que nucleo.vios e funcoes.parados esperam de um contexto."""
    driver: Any
    cfg: Any
    hoje: date = None
    chave: str = "consulta"


def fechar(ctx):
    try:
        if ctx is not None and ctx.driver is not None:
            ctx.driver.quit()
    except Exception:  # noqa: BLE001 — fechar nunca atrapalha
        pass


def abrir(cfg, esperas=ESPERAS_LOGIN, criar_driver=navegador.criar_driver, dormir=time.sleep):
    """Abre o Chrome, liga o bloqueio, entra no VIOS e confere o bloqueio. Devolve o Ctx."""
    driver = criar_driver(cfg.headless, False)
    ctx = Ctx(driver=driver, cfg=cfg, hoje=date.today())
    try:
        navegador.bloquear_envios(driver, permitidos=cfg.valor("ORELHA_XHR_PERMITIDO", "", "lista"),
                                  proibidos=cfg.urls_proibidas)
        for n, espera in enumerate(esperas, 1):
            if espera:
                log.warning("Login no VIOS: nova tentativa em %d s (%d de %d)", espera, n, len(esperas))
                dormir(espera)
            try:
                vios.entrar(ctx, marcar_formulario=True)
                break
            except vios.LoginTelaErro:
                if n == len(esperas):
                    raise
        vios.abrir(ctx, driver.current_url)  # recarrega já com o bloqueio e confere (BloqueioInativo)
    except BaseException:
        fechar(ctx)
        raise
    log.info("Sessão do VIOS aberta, somente leitura")
    return ctx
