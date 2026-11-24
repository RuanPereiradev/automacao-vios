"""Relatório mensal de processos por Grupo Cliente -> uma planilha .xlsx por grupo.

Para cada grupo: pesquisa a lista de processos, abre a tela de cada processo (a
lupa), lê o cadastro e as tarefas, pede à IA as colunas de texto e salva
<RELATORIO_PASTA>/AAAA-MM/<GRUPO>.xlsx + <GRUPO>.pdf no timbrado (com o "Resumo do mês" da IA) e
<GRUPO>.json com os dados lidos. Com --limite (teste),
salva em AAAA-MM/teste/, sem tocar na planilha do mês. O andamento vai para a vila (bot/vila_aviso.py).
"""
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from nucleo import config, ia
from nucleo.custo import Gasto, LimiteGasto
from nucleo.login import fazer_login
from nucleo.navegacao import ir_ate_tabela
from nucleo.navegador import criar_driver
from nucleo.processos_detalhe import ler_processo
from nucleo.processos_grupo import _normal, grupos_disponiveis, ler_processos, nome_arquivo, pesquisar_grupo
from nucleo.vila_aviso import Vila
from nucleo.relatorio_pdf import SCHEMA_MES, SISTEMA_MES, salvar_pdf, texto_mes
from nucleo.relatorio_planilha import SEM_TAREFAS, SISTEMA, SCHEMA, montar_linha, salvar_xlsx, texto_para_ia
from nucleo.registro import PASTA_LOGS, configurar_log

MODELO_PADRAO = "claude-sonnet-5-5"
# modelo de cada provedor quando LLM_MODELO está vazio
MODELOS_PADRAO = {"anthropic": MODELO_PADRAO, "openai": "gpt-5.6", "gemini": "gemini-3.6-flash"}


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


def resumo_mes(agente, gasto, modelo, grupo, linhas, log):
    """Página "Resumo do mês" do PDF: uma chamada à IA por grupo. Erro = PDF sem essa página."""
    texto = texto_mes(grupo, linhas)
    try:
        gasto.conferir(gasto.estimar(modelo, SISTEMA_MES, texto), f"resumo do mês de {grupo}")
        resposta = agente.responder(SISTEMA_MES, texto, SCHEMA_MES)
        gasto.registrar(modelo, resposta.pop("_uso", {}))
        return [p.strip() for p in resposta["paragrafos"] if p.strip()]
    except Exception as e:
        log.error("%s: resumo do mês pela IA falhou (o PDF sai sem essa página): %s", grupo, e)
        return []


def gerar_grupo(driver, cfg, grupo, valor, pasta, agente, gasto, modelo, limite, log, vila, ordem, grupos):
    pesquisar_grupo(driver, valor, cfg.timeout)
    itens, erros = ler_processos(driver, cfg.timeout)
    log.info("%s: %d processos na lista (%d linhas com erro)", grupo, len(itens), erros)
    if limite:
        itens = itens[:limite]
        log.info("%s: só os %d primeiros (--limite)", grupo, len(itens))
    vila.emitir("grupo", grupo=ordem, grupos=grupos, processos=len(itens))

    linhas, brutos, erros_ia = [], [], 0
    gasto_antes = gasto.total  # o gasto da execução é acumulado: o do grupo é a diferença
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
        vila.emitir("processo", grupo=ordem, grupos=grupos, feito=n, total=len(itens), gasto=round(gasto.total, 2))

    arquivo = pasta / nome_arquivo(grupo)
    # "Resumo do mês" do PDF (uma chamada à IA) antes de fechar o gasto do grupo, para ele entrar na conta
    paragrafos = resumo_mes(agente, gasto, modelo, grupo, linhas, log) if linhas else []
    do_grupo = gasto.total - gasto_antes
    salvar_xlsx(arquivo, grupo, linhas, {
        "gerado_em": datetime.now(), "modelo": modelo, "erros_ia": erros_ia,
        "gasto": f"US$ {do_grupo:.2f} neste grupo ({len(linhas)} processos)"
                 + (f"; US$ {gasto.total:.2f} na execução até aqui" if gasto_antes else "")})
    arquivo.with_suffix(".json").write_text(json.dumps(brutos, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        salvar_pdf(arquivo.with_suffix(".pdf"), grupo, linhas, {"gerado_em": datetime.now()}, paragrafos)
        log.info("%s: PDF -> %s", grupo, arquivo.with_suffix(".pdf"))
    except Exception:
        log.exception("%s: não consegui gerar o PDF (a planilha foi salva)", grupo)
    log.info("%s: %d processos, %d com erro na IA, gasto do grupo US$ %.2f -> %s", grupo, len(linhas), erros_ia,
             do_grupo, arquivo)
    vila.emitir("grupo_fim", grupo=ordem, grupos=grupos, processos=len(linhas), erros_ia=erros_ia)
    return erros_ia


def juntar_grupos(atuais, vios):
    """Lista do PROCESSOS_GRUPOS com os grupos do VIOS: mantém os atuais (na ordem) e põe no fim os que
    faltam, na ordem do filtro. Devolve (lista nova, novos, atuais que não existem mais no VIOS)."""
    ja = {_normal(g) for g in atuais}
    novos = [g for g in vios if _normal(g) not in ja and _normal(g) != "TODOS"]
    sumiram = [g for g in atuais if _normal(g) not in {_normal(v) for v in vios}]
    return list(atuais) + novos, novos, sumiram


def gravar_grupos(caminho_env, grupos):
    """Troca a linha PROCESSOS_GRUPOS= do .env (ou acrescenta no fim); o resto do arquivo fica igual.
    Se houver mais de uma linha PROCESSOS_GRUPOS=, fica só a primeira (com a lista nova): o .env vale a
    ÚLTIMA, e uma linha velha repetida no fim escondia os grupos gravados."""
    arq = Path(caminho_env)
    linhas = arq.read_text(encoding="utf-8").splitlines() if arq.exists() else []
    nova = "PROCESSOS_GRUPOS=" + "|".join(grupos)
    saida, gravou = [], False
    for linha in linhas:
        if linha.strip().startswith("PROCESSOS_GRUPOS="):
            if not gravou:
                saida.append(nova)
                gravou = True
            continue
        saida.append(linha)
    if not gravou:
        saida.append(nova)
    arq.write_text("\n".join(saida) + "\n", encoding="utf-8")


def listar_grupos(cfg, caminho_env, salvar, log):
    """Entra no VIOS, lê o filtro Grupo Cliente e mostra os grupos (com --salvar, põe os que faltam no .env)."""
    driver = criar_driver(cfg.headless, cfg.manter_aberto, cfg.navegador_rapido)
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        vios = list(grupos_disponiveis(driver, cfg.timeout))
    finally:
        if not cfg.manter_aberto:
            driver.quit()
    atuais = [g.strip() for g in os.getenv("PROCESSOS_GRUPOS", "").split("|") if g.strip()]
    lista, novos, sumiram = juntar_grupos(atuais, vios)
    print(f"Grupos no filtro Grupo Cliente do VIOS ({len(vios)}):")
    for g in vios:
        print(("  [já na lista] " if g not in novos else "  [novo]       ") + g)
    if sumiram:
        print("No PROCESSOS_GRUPOS mas não existem mais no VIOS:", ", ".join(sumiram))
    if not salvar:
        print(f"{len(novos)} grupo(s) novo(s). Para pôr na página /jarvis: --grupos --salvar")
        return 0
    repetidas = sum(1 for l in Path(caminho_env).read_text(encoding="utf-8").splitlines()
                    if l.strip().startswith("PROCESSOS_GRUPOS=")) if Path(caminho_env).exists() else 0
    if novos or repetidas > 1:
        gravar_grupos(caminho_env, lista)
        log.info("PROCESSOS_GRUPOS de %s agora tem %d grupos (%d novos)", caminho_env, len(lista), len(novos))
    else:
        print("Nada novo: o PROCESSOS_GRUPOS já tem todos os grupos do VIOS.")
    return 0


def main(*args):
    configurar_log()
    log = logging.getLogger("relatorio")
    args = list(args)
    # --grupos: só lista os grupos do VIOS; --grupos --salvar: põe os que faltam no PROCESSOS_GRUPOS do .env
    so_grupos, salvar = "--grupos" in args, "--salvar" in args
    args = [a for a in args if a not in ("--grupos", "--salvar")]
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
    if so_grupos:
        return listar_grupos(cfg, caminho_env, salvar, log)
    pedidos = [g.strip() for g in (grupos_txt or os.getenv("PROCESSOS_GRUPOS", "")).split("|") if g.strip()]
    if not pedidos:
        log.error("Informe os grupos: --grupo \"CASA DO CELULAR\" ou PROCESSOS_GRUPOS no %s", caminho_env)
        return 1
    provedor = os.getenv("LLM_PROVEDOR", "anthropic").strip().lower() or "anthropic"
    modelo = os.getenv("LLM_MODELO", "").strip() or MODELOS_PADRAO.get(provedor, MODELO_PADRAO)
    try:
        agente = ia.criar(provedor, modelo, os.getenv("LLM_ESFORCO", "").strip())
    except ia.IAErro as e:
        log.error(e)
        return 1
    gasto = Gasto.do_env()
    log.info("Execução iniciada: %d grupo(s), modelo %s", len(pedidos), modelo)  # o gastos.py separa as execuções por aqui
    pasta = Path(os.getenv("RELATORIO_PASTA", "").strip() or cfg.pasta_saida / "relatorios") / f"{datetime.now():%Y-%m}"
    if limite:
        pasta = pasta / "teste"  # teste com poucos processos não substitui a planilha do mês
    vila = Vila.do_env()
    vila.emitir("execucao_iniciada", grupos=len(pedidos), teste=bool(limite))
    vila.emitir("fase", fase="entrando_vios")

    try:
        driver = criar_driver(cfg.headless, cfg.manter_aberto, cfg.navegador_rapido)
    except Exception:
        log.exception("O navegador não abriu")
        vila.emitir("execucao_fim", resultado="parou", motivo="navegador", gasto=0)
        return 1
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        disponiveis = grupos_disponiveis(driver, cfg.timeout)
        # sem acento e sem diferença de maiúsculas: "casa do celular mg/sp" acha "CASA DO CELULAR MG/SP"
        por_nome = {_normal(nome): nome for nome in disponiveis}
        if [_normal(p) for p in pedidos] == ["TODOS"]:
            pedidos = list(disponiveis)

        feitos, falhas = 0, 0
        for ordem, pedido in enumerate(pedidos, 1):
            grupo = por_nome.get(_normal(pedido))
            if not grupo:
                log.error("Grupo '%s' não existe no filtro Grupo Cliente", pedido)
                falhas += 1
                continue
            try:
                erros_ia = gerar_grupo(driver, cfg, grupo, disponiveis[grupo], pasta, agente, gasto, modelo, limite, log,
                                       vila, ordem, len(pedidos))
                feitos += 1
                falhas += bool(erros_ia)
            except Exception:
                screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
                driver.save_screenshot(str(screenshot))
                log.exception("Falha no grupo %s (screenshot em %s)", grupo, screenshot)
                falhas += 1
        log.info("Concluído: %d grupo(s) salvos, %d com falha — gasto com IA %s", feitos, falhas, gasto.resumo())
        vila.emitir("execucao_fim", resultado="concluido" if not falhas else "com_falha", planilhas=feitos,
                    falhas=falhas, gasto=round(gasto.total, 2))
        return 0 if not falhas else 1
    except Exception:
        screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
        driver.save_screenshot(str(screenshot))
        log.exception("Falha na execução (screenshot em %s)", screenshot)
        vila.emitir("execucao_fim", resultado="parou", motivo="erro", gasto=round(gasto.total, 2))
        return 1
    finally:
        if cfg.manter_aberto:
            log.info("MANTER_ABERTO=true: navegador continua aberto")
        else:
            driver.quit()


if __name__ == "__main__":
    # uso: python relatorio_processos.py [caminho/do/.env] [--grupo "CASA DO CELULAR"|todos] [--limite N]
    #      python relatorio_processos.py [caminho/do/.env] --grupos [--salvar]  (grupos do VIOS -> PROCESSOS_GRUPOS)
    sys.exit(main(*sys.argv[1:]))
