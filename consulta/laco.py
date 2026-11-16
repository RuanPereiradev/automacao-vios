"""O laço do coletor: buscar pedidos no bot, processar, devolver. Sessão do VIOS reaproveitada."""
import logging
import threading

from consulta.cliente import BotErro
from consulta.coletor import processar_pedido
from consulta import montagem
from consulta.erros import SessaoPerdida

log = logging.getLogger("consulta")
ESPERA_MAXIMA = 60  # s, no máximo, entre tentativas com o bot fora do ar


def processar_com_relogin(pedido, chave_privada, fonte, op, mapa, hoje=None, agora=None):
    """processar_pedido; se a sessão do VIOS cair, entra de novo e repete UMA vez."""
    for tentativa in (1, 2):
        try:
            return processar_pedido(pedido, chave_privada, fonte, op, mapa, hoje, agora)
        except SessaoPerdida:
            log.warning("pedido %s: a sessão do VIOS caiu (tentativa %d de 2)", pedido["id"], tentativa)
            fonte.reiniciar()
    return montagem.montar_resultado(pedido["id"], "erro", agora=agora)


def ciclo(bot, processar):
    """Um ciclo: pendentes -> processar cada um -> devolver o resultado. Devolve quantos foram."""
    pedidos = bot.pendentes()
    for pedido in pedidos:
        resultado = processar(pedido)
        if not bot.enviar_resultado(resultado):
            log.info("pedido %s: o bot já não aceita (expirou)", pedido["id"])
    return len(pedidos)


def laco(bot, processar, intervalo, uma_vez=False, parar=None):
    """Repete o ciclo a cada `intervalo` s até `parar` (threading.Event) ou, com uma_vez, um ciclo só.
    Devolve 0 se o último ciclo falou com o bot, 1 se o bot estava inacessível."""
    parar = parar or threading.Event()
    falhas = 0
    while not parar.is_set():
        try:
            ciclo(bot, processar)
            falhas = 0
        except BotErro as e:
            falhas += 1
            if falhas == 1 or falhas % 10 == 0:
                log.warning("%s (falha %d seguida)", e, falhas)
            if uma_vez:
                return 1
        if uma_vez:
            return 0
        espera = min(ESPERA_MAXIMA, intervalo * (2 ** min(falhas, 6))) if falhas else intervalo
        parar.wait(espera)
    return 0
