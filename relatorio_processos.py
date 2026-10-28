import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from bot import config
from bot.login import fazer_login
from bot.navegacao import ir_ate_tabela
from bot.navegador import criar_driver
from bot.processos_grupo import _normal, grupos_disponiveis, ler_processos, montar_txt, nome_arquivo, pesquisar_grupo
from main import PASTA_LOGS, configurar_log


def main(*args):
    configurar_log()
    log = logging.getLogger("relatorio")
    args = list(args)
    # --grupo "3A FRIOS|AÇO GRANJA" ou --grupo todos (sem --grupo: PROCESSOS_GRUPOS do .env)
    grupos_txt = None
    if "--grupo" in args:
        i = args.index("--grupo")
        grupos_txt = args[i + 1]
        del args[i:i + 2]
    caminho_env = args[0] if args else ".env.usuario2"
    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        return 1
    grupos_txt = grupos_txt or os.getenv("PROCESSOS_GRUPOS", "")
    pedidos = [g.strip() for g in grupos_txt.split("|") if g.strip()]
    if not pedidos:
        log.error("Informe os grupos: --grupo \"3A FRIOS\" ou PROCESSOS_GRUPOS no %s", caminho_env)
        return 1
    pasta = Path(os.getenv("RELATORIO_PASTA", "").strip() or cfg.pasta_saida / "relatorios") / f"{datetime.now():%Y-%m-%d}"

    driver = criar_driver(cfg.headless, cfg.manter_aberto)
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        disponiveis = grupos_disponiveis(driver, cfg.timeout)
        log.info("%d grupos no filtro Grupo Cliente", len(disponiveis))
        if [p.lower() for p in pedidos] == ["todos"]:
            pedidos = list(disponiveis)
        # sem acento e sem diferença de maiúsculas: "pao mix" acha "PÃO MIX"
        por_nome = {_normal(nome): nome for nome in disponiveis}

        feitos, falhas = 0, 0
        for pedido in pedidos:
            grupo = por_nome.get(_normal(pedido))
            if not grupo:
                log.error("Grupo '%s' não existe no filtro Grupo Cliente", pedido)
                falhas += 1
                continue
            try:
                pesquisar_grupo(driver, disponiveis[grupo], cfg.timeout)
                itens, erros = ler_processos(driver, cfg.timeout)
                pasta.mkdir(parents=True, exist_ok=True)
                arquivo = pasta / nome_arquivo(grupo)
                arquivo.write_text(montar_txt(grupo, itens), encoding="utf-8")
                log.info("%s: %d processos, %d com erro -> %s", grupo, len(itens), erros, arquivo)
                feitos += 1
            except Exception:
                screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
                driver.save_screenshot(str(screenshot))
                log.exception("Falha no grupo %s (screenshot em %s)", grupo, screenshot)
                falhas += 1
        log.info("Concluído: %d grupo(s) salvos, %d com falha", feitos, falhas)
        return 0 if not falhas else 1
    except Exception:
        screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
        driver.save_screenshot(str(screenshot))
        log.exception("Falha na execução (screenshot em %s)", screenshot)
        return 1
    finally:
        if cfg.manter_aberto:
            log.info("MANTER_ABERTO=true: navegador continua aberto")
        else:
            driver.quit()


if __name__ == "__main__":
    # uso: python relatorio_processos.py [caminho/do/.env] [--grupo "3A FRIOS"|todos]
    sys.exit(main(*sys.argv[1:]))
