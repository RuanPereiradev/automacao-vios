import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from bot import config, revisao
from bot.lancamento import ler_responsaveis
from bot.login import fazer_login
from bot.navegador import criar_driver
from bot.web import criar_app
from main import configurar_log

BANCO = Path("saida/revisao.db")


def main(*args):
    configurar_log()
    log = logging.getLogger("revisao")
    args = list(args)
    porta = 5000
    if "--porta" in args:
        i = args.index("--porta")
        porta = int(args[i + 1])
        del args[i:i + 2]
    atualizar = "--atualizar-responsaveis" in args
    args = [a for a in args if a != "--atualizar-responsaveis"]
    load_dotenv(".env", override=True)

    con = revisao.conectar(BANCO)
    for arquivo in args:
        novas, existentes = revisao.importar(con, arquivo)
        log.info("%s: %d CI(s) nova(s), %d já estavam no banco", arquivo, novas, existentes)

    if atualizar and not atualizar_responsaveis(con, log):
        return 1

    log.info("Página de revisão em http://127.0.0.1:%d (Ctrl+C para parar)", porta)
    # só na própria máquina: a página ainda não tem login
    criar_app(BANCO).run(host="127.0.0.1", port=porta)
    return 0


def atualizar_responsaveis(con, log):
    """Entra no VIOS, abre o formulário de lançamento de uma CI (sem preencher nada)
    e salva a lista de pessoas do campo Responsáveis."""
    link = next((c["analise"].get("link_lancar") for c in revisao.listar(con) if c["analise"].get("link_lancar")), None)
    if not link:
        log.error("Nenhuma CI com link de lançamento no banco: importe uma análise antes.")
        return False
    cfg = config.carregar(".env")
    driver = criar_driver(cfg.headless, False)
    try:
        fazer_login(driver, cfg)
        pessoas = ler_responsaveis(driver, link, cfg.timeout)
    finally:
        driver.quit()
    arquivo = BANCO.parent / revisao.ARQUIVO_RESPONSAVEIS
    arquivo.write_text(json.dumps(pessoas, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("%d responsáveis salvos em %s", len(pessoas), arquivo)
    return True


if __name__ == "__main__":
    # uso: python revisar.py [saida/analise_X.json ...] [--atualizar-responsaveis] [--porta 5000]
    sys.exit(main(*sys.argv[1:]))
