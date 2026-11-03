"""Relatório mensal de processos por Grupo Cliente -> uma planilha .xlsx por grupo.

Para cada grupo: pesquisa a lista de processos, abre a tela de cada processo (a
lupa), lê o cadastro e as tarefas, pede à IA as colunas de texto e salva
<RELATORIO_PASTA>/AAAA-MM/<GRUPO>.xlsx (+ <GRUPO>.json com os dados lidos).
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from bot import config, ia
from bot.custo import Gasto, LimiteGasto
from bot.login import fazer_login
from bot.navegacao import ir_ate_tabela
from bot.navegador import criar_driver
from bot.processos_detalhe import ler_processo
from bot.processos_grupo import _normal, grupos_disponiveis, ler_processos, nome_arquivo, pesquisar_grupo
from bot.relatorio_planilha import SEM_TAREFAS, SISTEMA, SCHEMA, montar_linha, salvar_xlsx, texto_para_ia
from main import PASTA_LOGS, configurar_log

MODELO_PADRAO = "claude-sonnet-5-5"


def _opcao(args, nome):
    if nome not in args:
        return None
    i = args.index(nome)
    valor = args[i + 1]
    del args[i:i + 2]
    return valor


def analisar(agente, gasto, modelo, item, proc, log):
    texto = texto_para_ia(item, proc)
    try:
        gasto.conferir(gasto.estimar(modelo, SISTEMA, texto), f"análise do CI {item['ci']}")
        resposta = agente.responder(SISTEMA, texto, SCHEMA)
        gasto.registrar(modelo, resposta.pop("_uso", {}))
        return resposta
    except LimiteGasto as e:
        log.error("CI %s: %s", item["ci"], e)
        return {"erro": str(e)}
    except Exception as e:
        log.error("CI %s: erro na IA: %s", item["ci"], e)
        return {"erro": str(e)}


def gerar_grupo(driver, cfg, grupo, valor, pasta, agente, gasto, modelo, limite, log):
    pesquisar_grupo(driver, valor, cfg.timeout)
    itens, erros = ler_processos(driver, cfg.timeout)
    log.info("%s: %d processos na lista (%d linhas com erro)", grupo, len(itens), erros)
    if limite:
        itens = itens[:limite]
        log.info("%s: só os %d primeiros (--limite)", grupo, len(itens))

    linhas, brutos, erros_ia = [], [], 0
    for n, item in enumerate(itens, 1):
        try:
            proc = ler_processo(driver, item["ci"], cfg.timeout)
        except Exception as e:
            screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
            driver.save_screenshot(str(screenshot))
            log.error("CI %s: não consegui ler a tela do processo (%s; screenshot em %s)", item["ci"], e, screenshot)
            proc = {"dados": {}, "tarefas": [], "erro": str(e)}
        resposta = analisar(agente, gasto, modelo, item, proc, log) if proc["tarefas"] else dict(SEM_TAREFAS)
        erros_ia += "erro" in resposta
        linhas.append(montar_linha(item, proc, resposta))
        brutos.append({"lista": item, "processo": proc, "ia": resposta})
        log.info("%s: %d/%d CI %s — %d tarefas — gasto %s", grupo, n, len(itens), item["ci"],
                 len(proc["tarefas"]), gasto.resumo())

    arquivo = pasta / nome_arquivo(grupo)
    salvar_xlsx(arquivo, grupo, linhas, {
        "gerado_em": datetime.now(), "modelo": modelo, "gasto": gasto.resumo(), "erros_ia": erros_ia})
    arquivo.with_suffix(".json").write_text(json.dumps(brutos, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("%s: %d processos, %d com erro na IA -> %s", grupo, len(linhas), erros_ia, arquivo)
    return erros_ia


def main(*args):
    configurar_log()
    log = logging.getLogger("relatorio")
    args = list(args)
    # --grupo "CASA DO CELULAR|CASA DO CELULAR MG/SP" (sem --grupo: PROCESSOS_GRUPOS do .env)
    grupos_txt = _opcao(args, "--grupo")
    # --limite N: só os N primeiros processos de cada grupo (para testar)
    limite = int(_opcao(args, "--limite") or 0)
    caminho_env = args[0] if args else ".env.usuario2"
    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        return 1
    pedidos = [g.strip() for g in (grupos_txt or os.getenv("PROCESSOS_GRUPOS", "")).split("|") if g.strip()]
    if not pedidos:
        log.error("Informe os grupos: --grupo \"CASA DO CELULAR\" ou PROCESSOS_GRUPOS no %s", caminho_env)
        return 1
    modelo = os.getenv("LLM_MODELO", "").strip() or MODELO_PADRAO
    try:
        agente = ia.criar(os.getenv("LLM_PROVEDOR", "anthropic"), modelo, os.getenv("LLM_ESFORCO", "").strip())
    except ia.IAErro as e:
        log.error(e)
        return 1
    gasto = Gasto.do_env()
    pasta = Path(os.getenv("RELATORIO_PASTA", "").strip() or cfg.pasta_saida / "relatorios") / f"{datetime.now():%Y-%m}"

    driver = criar_driver(cfg.headless, cfg.manter_aberto, cfg.navegador_rapido)
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        disponiveis = grupos_disponiveis(driver, cfg.timeout)
        # sem acento e sem diferença de maiúsculas: "casa do celular mg/sp" acha "CASA DO CELULAR MG/SP"
        por_nome = {_normal(nome): nome for nome in disponiveis}
        if [_normal(p) for p in pedidos] == ["TODOS"]:
            pedidos = list(disponiveis)

        feitos, falhas = 0, 0
        for pedido in pedidos:
            grupo = por_nome.get(_normal(pedido))
            if not grupo:
                log.error("Grupo '%s' não existe no filtro Grupo Cliente", pedido)
                falhas += 1
                continue
            try:
                erros_ia = gerar_grupo(driver, cfg, grupo, disponiveis[grupo], pasta, agente, gasto, modelo, limite, log)
                feitos += 1
                falhas += bool(erros_ia)
            except Exception:
                screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
                driver.save_screenshot(str(screenshot))
                log.exception("Falha no grupo %s (screenshot em %s)", grupo, screenshot)
                falhas += 1
        log.info("Concluído: %d grupo(s) salvos, %d com falha — gasto com IA %s", feitos, falhas, gasto.resumo())
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
    # uso: python relatorio_processos.py [caminho/do/.env] [--grupo "CASA DO CELULAR"|todos] [--limite N]
    sys.exit(main(*sys.argv[1:]))
