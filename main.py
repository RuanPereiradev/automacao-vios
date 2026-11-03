"""Bot de comprovantes previdenciários — VIOS.

Só roda nos três últimos dias corridos do mês. Para cada tarefa "EDITAR OS DADOS DA AÇÃO
PROTOCOLADA (PREVIDENCIÁRIO)" do calendário: abre a tarefa, o número do processo e o
"Visualizar" do modal abrem o processo, a tarefa PROTOCOLAR INICIAL (PREVIDENCIÁRIO) leva à
galeria com o comprovante de protocolo, lê o PDF (CNJ, órgão julgador, valor da causa), o
lápis do N.° CNJ abre a edição do processo, preenche N.° CNJ, Órgão julgador (Vara/câmara)
e Valor da ação, grava e confere.
Sem --confirmar nada é gravado (simulação). --somente-leitura não preenche nem grava:
só lê e diz o que faria. Toda execução gera saida/relatorio_*.csv.

--tarefa <link> processa só a tarefa do calendário com esse link (mesmo pxe_id).

uso: python main.py [--confirmar | --somente-leitura] [--fora-da-janela] [--tarefa <link>] [caminho/do/.env]
"""
import calendar
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from bot import calendario, classificacao, comprovante, config, edicao, processo, relatorio, vila
from bot.login import LoginErro, fazer_login
from bot.navegador import bloquear_envios, criar_driver, envios_bloqueados
from bot.vios import abrir, ids_numericos

PASTA_LOGS = Path("logs")
REGISTRO = "registro.json"  # tarefas já resolvidas (nunca são editadas de novo)
DIAS_NO_FIM = 3

log = logging.getLogger("bot")


class TarefaErro(Exception):
    pass


class LeituraErro(Exception):
    """O bloqueio de envios do modo somente leitura não está ativo: a execução para."""


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


def nos_ultimos_dias(hoje):
    """True nos três últimos dias do mês (ex.: 29, 30 e 31 de outubro; 26, 27 e 28 de fevereiro)."""
    ultimo = calendar.monthrange(hoje.year, hoje.month)[1]
    return hoje.day > ultimo - DIAS_NO_FIM


def modo(hoje, confirmar, fora_da_janela, somente_leitura=False):
    """'gravar', 'simular', 'ler' ou None (não roda). Simulação é o padrão; --fora-da-janela só simula
    (ou só lê), e junto com --confirmar é recusado em qualquer dia; --somente-leitura com --confirmar
    também é recusado."""
    if confirmar and (fora_da_janela or somente_leitura):
        return None
    if not nos_ultimos_dias(hoje) and not fora_da_janela:
        return None
    if somente_leitura:
        return "ler"
    return "gravar" if confirmar else "simular"


def mesma_tarefa(link, alvo):
    """True se o link do calendário é o da tarefa pedida em --tarefa (mesmo pxe_id)."""
    def pxe(url):
        return set(parse_qs(urlparse(url).query).get("pxe_id", []))
    return bool(pxe(alvo)) and pxe(link) == pxe(alvo)


def _salvar_registro(arquivo, registro):
    """Grava num arquivo temporário e troca: o registro nunca fica pela metade."""
    tmp = arquivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, arquivo)


def _abrir(driver, url, cfg, bloqueio):
    """Abre a página; sem gravar (simulação e somente leitura) confere que o bloqueio de envios está ativo nela."""
    abrir(driver, url, cfg.timeout)
    if bloqueio and not envios_bloqueados(driver):
        raise LeituraErro(f"bloqueio de envios inativo em {driver.current_url}: execução interrompida")


def processar(driver, cfg, tarefa, modo_execucao, linha):
    """Uma tarefa do calendário. Preenche `linha` (relatório) conforme avança, para que uma falha
    no meio mostre até onde chegou. Devolve o que gravar no registro."""
    leitura = modo_execucao == "ler"
    bloqueio = modo_execucao != "gravar"  # simulação e somente leitura: envios bloqueados
    # 2) abre a tarefa; 3) número do processo -> "Visualizar" do modal abre o processo
    _abrir(driver, tarefa["link"], cfg, bloqueio)
    link_processo = processo.link_processo(driver, cfg)
    linha["link_processo"] = link_processo
    ids_processo = ids_numericos(link_processo)
    if not ids_processo:
        raise TarefaErro(f"o link Visualizar não tem id do processo: {link_processo}")
    linha["processo_id"] = ", ".join(sorted(ids_processo))
    vila.atual().processo(linha["processo_id"])
    vila.etapa("abrindo")
    _abrir(driver, link_processo, cfg, bloqueio)
    cnjs_processo = processo.cnj(driver, cfg)
    linha["cnj_tela_processo"] = ", ".join(sorted(cnjs_processo))
    log.info("Processo aberto: %s (N.° CNJ: %s)", link_processo, ", ".join(sorted(cnjs_processo)) or "vazio")

    # 4) tarefa PROTOCOLAR INICIAL do processo -> "Visualizar arquivo" -> comprovante na galeria
    _abrir(driver, processo.link_galeria(driver, cfg), cfg, bloqueio)
    comp = comprovante.achar(driver, cfg)
    linha["comprovante"] = comp["texto"]
    log.info("Comprovante: %s", comp["texto"])

    # 5) PDF: CNJ, órgão julgador e valor da causa
    valores = comprovante.extrair(comprovante.ler(driver, comp["href"], cfg.timeout))
    linha.update(cnj_pdf=valores["cnj"], orgao_pdf=valores["orgao"], valor_pdf=valores["valor"])
    vila.etapa("comprovante_lido")
    log.info("Dados do PDF: %s", "; ".join(f"{d.rotulo} = {valores[d.chave]}" for d in comprovante.DADOS))
    if cnjs_processo and valores["cnj"] not in cnjs_processo:
        raise comprovante.ComprovanteErro(
            f"o PDF é do processo {valores['cnj']}, mas a tela do processo mostra {', '.join(sorted(cnjs_processo))}")
    if not cnjs_processo:
        linha["ressalvas"] = "processo sem CNJ no VIOS: o comprovante não pôde ser conferido pelo CNJ"
        log.info("Processo ainda sem CNJ no VIOS: vale o único comprovante de protocolo do processo")

    # 6) volta ao processo; o lápis do N.° CNJ abre a tela de edição
    _abrir(driver, link_processo, cfg, bloqueio)
    link_edicao = processo.ir_para_edicao(driver, cfg)
    if bloqueio and not envios_bloqueados(driver):
        raise LeituraErro(f"bloqueio de envios inativo em {driver.current_url}: execução interrompida")

    if leitura:
        # 6) somente leitura: só lê a tela de edição e diz o que faria
        antes = edicao.ler(driver, link_edicao, ids_processo, cfg)
        if not envios_bloqueados(driver):
            raise LeituraErro(f"bloqueio de envios inativo em {driver.current_url}: execução interrompida")
        linha.update(cnj_edicao=antes["cnj"], orgao_edicao=antes["orgao"], valor_edicao=antes["valor"])
        if edicao.conflitos(antes, valores):
            raise edicao.EdicaoErro("campo já preenchido com outro valor (conferir manualmente): "
                                    + "; ".join(edicao.conflitos(antes, valores)))
        mudar = [d.rotulo for d in comprovante.DADOS if edicao.vazio(d, antes[d.chave])]
        linha["preencheria"] = ", ".join(mudar)
        vila.extra(campos=[d.chave for d in comprovante.DADOS if edicao.vazio(d, antes[d.chave])])
        situacao = "leitura" if mudar else "ja_estava"
    else:
        # 6) a 8) tela de edição: preenche, grava e confere
        situacao = edicao.editar(driver, link_edicao, ids_processo, valores, cfg, PASTA_LOGS,
                                 modo_execucao == "gravar")
    return {"quando": f"{datetime.now():%d/%m/%Y %H:%M}", "tarefa": tarefa["texto"], "link_tarefa": tarefa["link"],
            "processo_id": sorted(ids_processo), "processo_cnj": valores["cnj"], "link_processo": link_processo,
            "comprovante": comp["texto"], "valores": valores, "situacao": situacao}


def main(*args):
    configurar_log()
    args = list(args)
    alvo = None
    if "--tarefa" in args:
        i = args.index("--tarefa")
        if i + 1 >= len(args) or not mesma_tarefa(args[i + 1], args[i + 1]):
            log.error("--tarefa precisa do link da tarefa (com pxe_id=...)")
            return 1
        alvo = args[i + 1]
        del args[i:i + 2]
    confirmar = "--confirmar" in args
    fora_da_janela = "--fora-da-janela" in args
    somente_leitura = "--somente-leitura" in args
    args = [a for a in args if a not in ("--confirmar", "--fora-da-janela", "--somente-leitura")]
    caminho_env = args[0] if args else ".env"

    hoje = date.today()
    if confirmar and fora_da_janela:
        log.error("--fora-da-janela só permite simulação: não use junto com --confirmar")
        return 1
    if confirmar and somente_leitura:
        log.error("--somente-leitura não grava: não use junto com --confirmar")
        return 1
    modo_execucao = modo(hoje, confirmar, fora_da_janela, somente_leitura)
    vila.iniciar(caminho_env)
    if modo_execucao is None:
        log.info("Hoje (%s) não é um dos %d últimos dias corridos do mês: nada a fazer", f"{hoje:%d/%m/%Y}", DIAS_NO_FIM)
        vila.emitir("execucao_fim", resultado="fora_do_dia")
        return 0
    gravar = modo_execucao == "gravar"
    leitura = modo_execucao == "ler"
    if fora_da_janela:
        log.warning("--fora-da-janela: rodando só em %s", "SOMENTE LEITURA" if leitura else "SIMULAÇÃO")

    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        vila.emitir("execucao_fim", resultado="parou", motivo="config_invalida")
        return 1

    cfg.pasta_saida.mkdir(exist_ok=True)
    arquivo_reg = cfg.pasta_saida / REGISTRO
    registro = json.loads(arquivo_reg.read_text(encoding="utf-8")) if arquivo_reg.exists() else {}
    log.info("Início — %s", {"gravar": "GRAVANDO no VIOS", "simular": "SIMULAÇÃO (não grava)",
                             "ler": "SOMENTE LEITURA (não preenche nem grava)"}[modo_execucao])

    resumo = {"gravado": 0, "ja_estava": 0, "teste": 0, "leitura": 0, "ja_registrada": 0, "ignorada": 0,
              "ambigua": 0, "pulada": 0, "conferir": 0, "erro": 0}
    inicio = {"modo": {"gravar": "gravar", "simular": "teste", "ler": "leitura"}[modo_execucao],
              "fora_da_janela": fora_da_janela}
    vila.emitir("execucao_iniciada", **inicio, **({"tarefa_unica": True} if alvo else {}))
    fim = {}  # motivo da parada (vazio = terminou)
    try:
        driver = criar_driver(cfg.headless, cfg.manter_aberto)
    except Exception:
        log.exception("Não consegui abrir o navegador")
        vila.emitir("execucao_fim", resultado="parou", motivo="navegador_falhou", contagens=resumo)
        return 1
    try:
        return _executar(driver, cfg, modo_execucao, alvo, registro, arquivo_reg, resumo, fim)
    finally:
        # sempre o último evento da execução, inclusive quando falhou no meio
        resultado = {"gravar": "concluido", "simular": "testado", "ler": "lido"}[modo_execucao]
        vila.emitir("execucao_fim", **({"resultado": "parou", "motivo": fim["motivo"]} if fim
                                       else {"resultado": resultado}), contagens=resumo)


def _evento_fim_tarefa(situacao):
    vila.etapa({"gravado": "gravada", "ja_estava": "ja_estava", "teste": "testada", "leitura": "lida"}[situacao], fim=True)


def _executar(driver, cfg, modo_execucao, alvo, registro, arquivo_reg, resumo, fim):
    gravar = modo_execucao == "gravar"
    leitura = modo_execucao == "ler"
    linhas = []  # relatório: uma por tarefa do calendário
    try:
        vila.emitir("fase", fase="entrando_vios")
        fazer_login(driver, cfg)
        todas, fora = calendario.tarefas(driver, cfg)
        calendario.evento(todas, set(registro), (lambda link: mesma_tarefa(link, alvo)) if alvo else None)
        if not gravar:
            # depois do calendário (que carrega as tarefas por POST): nenhuma página aberta daqui
            # em diante consegue enviar formulário nem requisição que não seja GET
            bloquear_envios(driver)
            log.info("Bloqueio de envios ligado (%s)", "somente leitura" if leitura else "simulação")
        if fora:
            linhas.append({"modo": modo_execucao, "tarefa": "(calendário)", "decisao": "aviso",
                           "motivo": f"{fora} item(ns) do calendário sem link, repetido(s) ou apagado(s): "
                                     "não aparecem neste relatório, conferir CALENDARIO_TAREFA"})
        for t in todas:
            if t["classe"] != classificacao.PREVIDENCIARIA:
                log.info("%s: %s (%s)", "Ambígua, não processada" if t["classe"] == classificacao.AMBIGUA
                         else "Ignorada", t["texto"], t["motivo"])
                resumo[t["classe"]] += 1
                linhas.append({"modo": modo_execucao, "tarefa": t["texto"], "link_tarefa": t["link"],
                               "classificacao": t["classe"], "decisao": t["classe"], "motivo": t["motivo"]})
        tarefas = [t for t in todas if t["classe"] == classificacao.PREVIDENCIARIA]
        if alvo:
            tarefas = [t for t in tarefas if mesma_tarefa(t["link"], alvo)]
            if len(tarefas) != 1:
                log.error("--tarefa: esperado 1 tarefa previdenciária com esse link no calendário, achei %d: nada feito",
                          len(tarefas))
                fim["motivo"] = "tarefa_nao_encontrada"
                return 1
            log.info("--tarefa: só a tarefa %s", tarefas[0]["link"])
        vila.emitir("fase", fase="processando")
        for n, tarefa in enumerate(tarefas, 1):
            log.info("Tarefa %d/%d: %s", n, len(tarefas), tarefa["texto"])
            linha = {"modo": modo_execucao, "tarefa": tarefa["texto"], "link_tarefa": tarefa["link"],
                     "classificacao": tarefa["classe"]}
            linhas.append(linha)
            if tarefa["link"] in registro:
                log.info("Já resolvida em %s: pulando", registro[tarefa["link"]]["quando"])
                resumo["ja_registrada"] += 1
                linha.update(decisao="ja_registrada", motivo=f"já resolvida em {registro[tarefa['link']]['quando']}")
                continue
            vila.atual().tarefa(vila.pxe_id(tarefa["link"]))
            try:
                feito = processar(driver, cfg, tarefa, modo_execucao, linha)
            except (TarefaErro, processo.ProcessoErro, comprovante.ComprovanteErro, edicao.EdicaoErro) as e:
                vila.etapa("pulada", fim=True, motivo=vila.motivo_erro(e))
                log.warning("Pulada, nada gravado: %s", e)
                resumo["pulada"] += 1
                linha.update(decisao="pulada", motivo=str(e))
                continue
            except edicao.ConferenciaErro as e:
                # Gravar foi clicado: não marca como concluída; a próxima execução esbarra na
                # proteção de campo preenchido e não sobrescreve
                resumo["conferir"] += 1
                vila.etapa("conferir", fim=True, motivo=vila.motivo_erro(e))
                linha.update(decisao="conferir", motivo=f"CONFERIR NO VIOS (pode ter gravado): {e}")
                screenshot = PASTA_LOGS / f"conferir_{datetime.now():%Y-%m-%d_%H%M%S}.png"
                driver.save_screenshot(str(screenshot))
                log.error("CONFERIR NO VIOS (pode ter gravado): %s (screenshot em %s)", e, screenshot)
                continue
            except LeituraErro as e:
                vila.etapa("erro", fim=True, motivo="bloqueio_inativo")
                linha.update(decisao="erro", motivo=str(e))
                raise
            except Exception as e:
                resumo["erro"] += 1
                vila.etapa("erro", fim=True, motivo="excecao")
                linha.update(decisao="erro", motivo=f"{e.__class__.__name__}: {e}")
                screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
                driver.save_screenshot(str(screenshot))
                log.exception("Falha na tarefa, nada gravado (screenshot em %s)", screenshot)
                continue
            resumo[feito["situacao"]] += 1
            _evento_fim_tarefa(feito["situacao"])
            linha.update(decisao=feito["situacao"], motivo={
                "gravado": "gravado e conferido relendo a tela",
                "ja_estava": "os campos já estavam com os valores do comprovante",
                "teste": "simulação: campos preenchidos e não gravados",
                "leitura": "somente leitura: dados conferidos, nada preenchido",
            }[feito["situacao"]])
            # só entra no registro o que foi gravado e conferido relendo a tela, ou que a
            # releitura mostrou já estar com os valores do PDF; simulação nunca registra
            if gravar and feito["situacao"] in ("gravado", "ja_estava"):
                registro[tarefa["link"]] = feito
                _salvar_registro(arquivo_reg, registro)
                log.info("OK: %s", "gravado e conferido" if feito["situacao"] == "gravado" else "já estava correto")
        log.info("Concluído: %s", ", ".join(f"{k} {v}" for k, v in resumo.items()))
        return 1 if resumo["erro"] or resumo["conferir"] else 0
    except Exception as e:
        fim["motivo"] = ("login_falhou" if isinstance(e, LoginErro) else
                         "bloqueio_inativo" if isinstance(e, LeituraErro) else "excecao")
        screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
        driver.save_screenshot(str(screenshot))
        log.exception("Falha na execução (screenshot em %s)", screenshot)
        return 1
    finally:
        try:
            log.info("Relatório: %s", relatorio.escrever(cfg.pasta_saida, linhas))
        except Exception:
            log.exception("Não consegui escrever o relatório")
        if cfg.manter_aberto:
            log.info("MANTER_ABERTO=true: navegador continua aberto")
        else:
            driver.quit()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
