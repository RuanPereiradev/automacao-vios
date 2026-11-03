import logging
import os
import sys

from dotenv import load_dotenv

from bot.envio_web import criar_app
from main import configurar_log


def main(*args):
    configurar_log()
    log = logging.getLogger("envio")
    args = list(args)
    porta = 5001
    if "--porta" in args:
        i = args.index("--porta")
        porta = int(args[i + 1])
        del args[i:i + 2]
    rede = "--rede" in args
    args = [a for a in args if a != "--rede"]
    caminho_env = args[0] if args else ".env"
    load_dotenv(caminho_env, override=True)
    # --rede (ou ENVIO_REDE=true): aberta para os outros computadores da rede, com senha
    rede = rede or os.getenv("ENVIO_REDE", "false").strip().lower() in ("true", "1", "sim")
    senha = os.getenv("ENVIO_SENHA", "").strip()
    if rede and not senha:
        log.error("Para abrir na rede, defina ENVIO_SENHA no %s (a página grava no VIOS).", caminho_env)
        return 1
    host = "0.0.0.0" if rede else "127.0.0.1"
    log.info("Página de envio em http://%s:%d%s (Ctrl+C para parar)",
             "<IP desta máquina>" if rede else "127.0.0.1", porta, " — com senha" if senha else "")
    criar_app(caminho_env, senha=senha).run(host=host, port=porta, threaded=True)
    return 0


if __name__ == "__main__":
    # uso: python enviar.py [caminho/do/.env] [--rede] [--porta 5001]
    sys.exit(main(*sys.argv[1:]))
