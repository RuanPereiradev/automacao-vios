import logging
import sys
from datetime import datetime
from pathlib import Path

from bot import config, duplicidade
from bot.analise import analisar_arquivo
from bot.extracao import extrair_cards, extrair_tabela, salvar_cards_txt, salvar_txt
from bot.intimacoes import extrair_intimacoes, pesquisar, salvar_json
from bot.login import fazer_login
from bot.navegacao import ir_ate_tabela
from bot.navegador import criar_driver

PASTA_LOGS = Path("logs")


def configurar_log():
    PASTA_LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(PASTA_LOGS / "bot.log", encoding="utf-8"),
        ],
    )


def main(caminho_env=".env"):
    configurar_log()
    log = logging.getLogger("bot")

    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        return 1

    driver = criar_driver(cfg.headless, cfg.manter_aberto)
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        if cfg.pesquisa_data:
            inicio, fim = pesquisar(driver, cfg)
            itens, erros = extrair_intimacoes(driver, cfg, inicio, fim)
            # 1ª conferência de duplicatas: já na leitura (a 2ª é no envio do .txt)
            for ci, d in duplicidade.marcar(itens).items():
                log.info("CI %s é cópia da CI %s (%s): não gera tarefa", ci, d["original"], d["motivo"])
            arquivo = salvar_json(itens, cfg.pasta_saida, inicio, fim)
            log.info("Concluído: %d intimações (%d cópia(s)), %d com erro -> %s",
                     len(itens), sum(1 for i in itens if i.get("duplicada_de")), erros, arquivo)
            if itens and cfg.analise_ativa:
                relatorio, total, falhas = analisar_arquivo(arquivo, caminho_env)
                log.info("Análise: %d intimações, %d com erro -> %s", total, falhas, relatorio)
        elif cfg.card:
            blocos, erros = extrair_cards(driver, cfg)
            arquivo = salvar_cards_txt(blocos, cfg.pasta_saida)
            log.info("Concluído: %d cards extraídos, %d com erro -> %s", len(blocos), erros, arquivo)
        elif cfg.tabela:
            cabecalho, linhas, erros = extrair_tabela(driver, cfg)
            arquivo = salvar_txt(cabecalho, linhas, cfg.pasta_saida)
            log.info("Concluído: %d linhas extraídas, %d com erro -> %s", len(linhas), erros, arquivo)
        else:
            log.info("Nem PESQUISA_CAMPO_DATA, CARD ou TABELA definidos no .env: nada a extrair")
        return 0
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
    # uso: python main.py [caminho/do/.env]
    sys.exit(main(*sys.argv[1:2]))
