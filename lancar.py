import json
import logging
import sys
from pathlib import Path

from bot import config
from bot.lancamento import lancar
from bot.login import fazer_login
from bot.navegador import criar_driver
from main import PASTA_LOGS, configurar_log


def main(*args):
    configurar_log()
    log = logging.getLogger("lancar")
    args = list(args)
    confirmar = "--confirmar" in args
    args = [a for a in args if a != "--confirmar"]
    if "--ci" not in args:
        log.error("Informe as CIs: python lancar.py --ci 42431[,42432]|todas [saida/analise_X.json] [--confirmar]")
        return 1
    i = args.index("--ci")
    cis = [c.strip() for c in args[i + 1].split(",") if c.strip()]
    del args[i:i + 2]
    caminho_env = args[1] if len(args) > 1 else ".env"
    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        return 1

    if args:
        arquivo = Path(args[0])
    else:
        # a análise mais recente que tenha alguma das CIs
        analises = sorted(cfg.pasta_saida.glob("analise_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        arquivo = next((a for a in analises if cis == ["todas"] or any(r.get("ci") in cis for r in json.loads(a.read_text(encoding="utf-8")))), None)
        if not arquivo:
            log.error("Nenhuma análise com a(s) CI(s) %s. Rode ./rodar_analise.sh --ci ... antes.", ", ".join(cis))
            return 1
    resultados = json.loads(arquivo.read_text(encoding="utf-8"))
    log.info("Lançando CI(s) %s de %s — %s", ", ".join(cis), arquivo, "GRAVANDO no VIOS" if confirmar else "MODO TESTE (não grava)")

    driver = criar_driver(cfg.headless, cfg.manter_aberto)
    try:
        fazer_login(driver, cfg)
        lancadas, erros = lancar(driver, resultados, cis, cfg.pasta_saida, PASTA_LOGS, cfg.timeout, confirmar)
        log.info("Concluído: %d tarefa(s) lançada(s), %d erro(s)", lancadas, erros)
        return 0 if not erros else 1
    except Exception:
        log.exception("Falha no lançamento")
        return 1
    finally:
        if not cfg.manter_aberto:
            driver.quit()


if __name__ == "__main__":
    # uso: python lancar.py --ci 42431[,42432]|todas [saida/analise_X.json] [caminho/do/.env] [--confirmar]
    sys.exit(main(*sys.argv[1:]))
