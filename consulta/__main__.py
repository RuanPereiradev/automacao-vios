"""python -m consulta [--uma-vez] [--simulado] [--env ARQUIVO]

Coletor da consulta de processo (RN26): a cada CONSULTA_INTERVALO s busca os pedidos no bot, lê o VIOS
só por leitura e devolve a ficha mínima. Códigos de saída: 0 ok, 1 bot inacessível (--uma-vez) ou
simulado com divergência, 2 configuração, 3 bloqueio de envios inativo (nada é lido).
"""
import argparse
import logging
import signal
import sys
import threading
from datetime import date

from consulta import configuracao, fases, laco, registro
from consulta.cliente import ClienteBot
from consulta.cripto import CriptoErro
from nucleo import vios
from nucleo.config import ConfigErro

log = logging.getLogger("consulta")


def argumentos(argv):
    p = argparse.ArgumentParser(prog="python -m consulta", description="Coletor da consulta de processo.")
    p.add_argument("--uma-vez", action="store_true", help="roda um ciclo (busca, processa, devolve) e sai")
    p.add_argument("--simulado", action="store_true",
                   help="fixtures no lugar do VIOS e um bot falso em memória (sem senha, sem rede)")
    p.add_argument("--env", help="arquivo .env (padrão: consulta/.env)")
    return p.parse_args(argv)


def _simulado(args):
    from consulta import coletor, simulado
    from consulta.fonte import FonteSimulada
    privada, publica = simulado.gerar_chaves()
    bot = simulado.BotFalso(publica)
    hoje = date.today()
    fonte = FonteSimulada(simulado.PASTA_FIXTURES, hoje)
    op = coletor.Opcoes(chave_telefone=simulado.CHAVE_TELEFONE)
    mapa = fases.carregar_mapa()
    processar = lambda ped: laco.processar_com_relogin(ped, privada, fonte, op, mapa, hoje)  # noqa: E731
    laco.laco(bot, processar, 0.1, uma_vez=True)
    problemas = bot.conferir()
    log.info("simulado: %s", ", ".join(f"{k}={v}" for k, v in sorted(bot.resumo().items())))
    for p in problemas:
        log.error("simulado: %s", p)
    return 1 if problemas else 0


def main(argv=None):
    args = argumentos(sys.argv[1:] if argv is None else list(argv))
    registro.configurar()
    if args.simulado:
        return _simulado(args)
    try:
        c = configuracao.carregar(args.env)
        registro.configurar(c.pasta_logs)
        chave = configuracao.abrir_chave_privada(c)
        mapa = fases.carregar_mapa()
    except (ConfigErro, CriptoErro, fases.MapaErro, OSError) as e:
        log.error("Configuração: %s", e)
        return 2

    from consulta.fonte import FonteVios
    fonte = FonteVios(c.vios)
    bot = ClienteBot(c.bot_url, c.segredo, c.timeout_http, certificado=c.certificado)
    parar = threading.Event()
    for sinal in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sinal, lambda *_: parar.set())
    processar = lambda ped: laco.processar_com_relogin(ped, chave, fonte, c.opcoes, mapa)  # noqa: E731
    log.info("Coletor ligado (intervalo %s s)%s", c.intervalo, ", um ciclo" if args.uma_vez else "")
    try:
        return laco.laco(bot, processar, c.intervalo, uma_vez=args.uma_vez, parar=parar)
    except vios.BloqueioInativo:
        log.error("Bloqueio de envios inativo: parei sem ler nada")
        return 3
    finally:
        fonte.fechar()


if __name__ == "__main__":
    sys.exit(main())
