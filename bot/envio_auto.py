"""Envio automático com um clique (botão da página do Sam).

Faz o fluxo do dia inteiro, sem a pessoa subir .txt:
  1. captura as intimações de ontem sem tarefa no VIOS (main.capturar);
  2. analisa com a IA e a skill da Controladoria (analise.analisar_arquivo);
  3. lança as tarefas no VIOS CI por CI (lancamento.lancar, com as mesmas travas do envio normal) e
     confere cada uma na Conferência do VIOS.

Cada passo vira evento da vila (bot "ultron", saida/eventos.jsonl): a Fortaleza do Dragão anima
captura, análise, travas e criação de tarefas. O andamento também fica em
saida/automatico_execucao.json (a página lê por GET /automatico/andamento).
Roda numa thread do Flask, com a mesma trava dos outros envios (um navegador por vez).
"""
import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path

from bot import eventos, skill
from bot.analise import analisar_arquivo
from bot.lancamento import REGISTRO, RESULTADOS, lancar
from bot.login import fazer_login
from bot.navegacao import ir_ate_tabela
from bot.navegador import criar_driver

log = logging.getLogger(__name__)

ARQUIVO = "automatico_execucao.json"  # na pasta de saída: andamento da última execução
FASES = {"capturando": "Capturando as intimações no VIOS", "analisando": "A IA está analisando",
         "lancando": "Criando as tarefas no VIOS"}
_trava = threading.Lock()  # protege o dicionário de andamento
_atual = {}


def _ler(pasta_saida):
    try:
        return json.loads((Path(pasta_saida) / ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def andamento(pasta_saida):
    """Andamento da execução atual ou da última (dicionário vazio se nunca rodou)."""
    with _trava:
        return dict(_atual) if _atual else _ler(pasta_saida)


def _atualizar(pasta_saida, **campos):
    with _trava:
        _atual.update(campos)
        try:
            (Path(pasta_saida) / ARQUIVO).write_text(json.dumps(_atual, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            log.exception("Não consegui gravar o andamento do envio automático")


class _Coletor(logging.Handler):
    """Escuta o log do lançamento: avisa quando cada tarefa entra no quadro do VIOS ("CI 42484 tarefa 1: ...")."""

    def __init__(self, ao_adicionar):
        super().__init__(logging.INFO)
        self.linhas = []
        self.ao_adicionar = ao_adicionar

    def emit(self, record):
        msg = record.getMessage()
        if msg.startswith(("Observação:", "Quadro Tarefas")):
            return
        linha = msg.splitlines()[0]
        if record.exc_info and record.exc_info[1]:
            linha += f": {str(record.exc_info[1]).splitlines()[0]}"
        self.linhas.append(linha)
        m = re.match(r"^CI \S+ tarefa (\d+):", msg)
        if m:
            self.ao_adicionar(int(m.group(1)))


def _situacao(r, registro):
    """('pronta' | 'problema' | 'lancada', motivo) de uma CI analisada, antes de lançar."""
    if r["ci"] in registro:
        return "lancada", ""
    if r.get("erro"):
        return "problema", "A análise da IA deu erro"
    if r.get("duplicada_de"):
        return "problema", f"Cópia da CI {r['duplicada_de']}"
    if r.get("bloqueios"):
        return "problema", r["bloqueios"][0]
    if not r.get("tarefas"):
        return "problema", "Sem tarefa"
    if any(t["nome"] in skill.ESPECIAIS for t in r["tarefas"]):
        return "problema", "Pede conferência humana"
    if not r.get("link_lancar"):
        return "problema", "Sem o link Lançar Intimação"
    return "pronta", ""


def _evento_conferido(pasta_saida, envio_id, resultados, registro):
    cis, contagem = [], {"pronta": 0, "problema": 0, "lancada": 0}
    for r in resultados:
        if not r.get("ci"):
            continue
        s, motivo = _situacao(r, registro)
        contagem[s] += 1
        item = {"ci": r["ci"], "tarefa": " + ".join(t["nome"] for t in r.get("tarefas") or []), "status": s}
        if motivo:
            item["motivo"] = motivo
        cis.append(item)
    eventos.emitir(pasta_saida, envio_id, "conferido", prontas=contagem["pronta"], com_problema=contagem["problema"],
                   ja_lancadas=contagem["lancada"], cis=cis)
    return contagem


def _driver(cfg):
    driver = criar_driver(cfg.headless, False, cfg.navegador_rapido)
    try:
        fazer_login(driver, cfg)
    except Exception:
        driver.quit()
        raise
    return driver


def _capturar(cfg):
    """Entra no VIOS e captura as intimações. Devolve (arquivo, itens)."""
    from main import capturar  # main.py fica na raiz do projeto (o mesmo import do lancar.py)
    driver = _driver(cfg)
    try:
        ir_ate_tabela(driver, cfg)
        arquivo, itens, _ = capturar(driver, cfg)
        return arquivo, itens
    finally:
        driver.quit()


def rodar(cfg, caminho_env, pasta_saida, confirmar, liberar):
    """Executa o fluxo inteiro (chamar numa thread). `liberar` solta a trava de um-envio-por-vez no fim."""
    envio_id = "auto_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    emitir = lambda tipo, **d: eventos.emitir(pasta_saida, envio_id, tipo, **d)
    conta = {"gravadas": 0, "testadas": 0, "erros": 0, "ja_tinha": 0, "duplicatas": 0}
    modo = "gravar" if confirmar else "teste"
    with _trava:
        _atual.clear()
    _atualizar(pasta_saida, id=envio_id, estado="rodando", modo=modo, fase="capturando",
               inicio=f"{datetime.now():%Y-%m-%d %H:%M:%S}", fim=None, motivo="", intimacoes=None, analisadas=None,
               total_cis=0, feitas_cis=0, **conta)
    resultado, motivo = "concluido" if confirmar else "testado", ""
    try:
        emitir("envio_iniciado", modo=modo, automatico=True)
        # 1) captura
        emitir("fase", fase="capturando")
        arquivo, itens = _capturar(cfg)
        emitir("arquivo_subido", arquivo=arquivo.name, intimacoes=len(itens), automatico=True)
        _atualizar(pasta_saida, intimacoes=len(itens))
        if not itens:
            log.info("Envio automático: nenhuma intimação nova, nada a fazer")
            _atualizar(pasta_saida, motivo="Nenhuma intimação nova sem tarefa no período.")
            return
        # 2) análise com IA (no navegador não há nada aberto: a análise em lote pode levar um tempo)
        _atualizar(pasta_saida, fase="analisando")
        emitir("fase", fase="analisando")
        _, total, falhas = analisar_arquivo(arquivo, caminho_env)
        analise = arquivo.parent / arquivo.name.replace("intimacoes_", "analise_", 1)
        resultados = json.loads(analise.read_text(encoding="utf-8"))
        _atualizar(pasta_saida, analisadas=total)
        reg = Path(pasta_saida) / REGISTRO
        registro = json.loads(reg.read_text(encoding="utf-8")) if reg.exists() else {}
        contagem = _evento_conferido(pasta_saida, envio_id, resultados, registro)
        _atualizar(pasta_saida, total_cis=len(resultados), prontas=contagem["pronta"],
                   com_problema=contagem["problema"])
        # 3) lançamento CI por CI, com as mesmas travas do envio de .txt
        _atualizar(pasta_saida, fase="lancando")
        emitir("fase", fase="entrando_vios")
        driver = _driver(cfg)
        try:
            emitir("fase", fase="criando_tarefas")
            for n, r in enumerate(resultados, 1):
                ci = r.get("ci")
                if not ci:
                    continue
                no_quadro = set()

                def ao_adicionar(i, r=r, no_quadro=no_quadro):
                    if 1 <= i <= len(r["tarefas"]) and i not in no_quadro:
                        no_quadro.add(i)
                        emitir("ci", ci=r["ci"], tarefa=r["tarefas"][i - 1]["nome"], etapa="no_quadro")
                coletor = _Coletor(ao_adicionar)
                logging.getLogger("bot.lancamento").addHandler(coletor)
                try:
                    lancar(driver, [r], [ci], pasta_saida, Path("logs"), cfg.timeout, confirmar=confirmar)
                except Exception as e:
                    coletor.linhas.append(str(e))
                finally:
                    logging.getLogger("bot.lancamento").removeHandler(coletor)
                _resultado_da_ci(pasta_saida, emitir, r, confirmar, no_quadro, coletor.linhas, conta)
                _atualizar(pasta_saida, feitas_cis=n, **conta)
        finally:
            driver.quit()
    except Exception as e:
        log.exception("Falha no envio automático")
        resultado, motivo = "parou", str(e) or e.__class__.__name__
    finally:
        _atualizar(pasta_saida, estado=resultado, ultima=andamento(pasta_saida).get("fase") or "lancando", fase="", fim=f"{datetime.now():%Y-%m-%d %H:%M:%S}",
                   motivo=motivo or andamento(pasta_saida).get("motivo", ""), **conta)
        dados = {"resultado": resultado, "contagens": conta}
        if motivo:
            dados["motivo"] = motivo[:300]
        emitir("envio_fim", **dados)
        liberar()


def _resultado_da_ci(pasta_saida, emitir, r, confirmar, no_quadro, linhas, conta):
    """Depois de lançar uma CI: lê o que o lançamento anotou e conta/emite o resultado de cada tarefa."""
    ci = r["ci"]
    anotado = {}
    try:
        anotado = json.loads((Path(pasta_saida) / RESULTADOS).read_text(encoding="utf-8")).get(ci, {})
    except (OSError, ValueError):
        pass
    # "já foi lançada ... pulando": o lançamento nem anota resultado, e o anotado antes seria de outra execução
    if any("já foi lançada" in l for l in linhas):
        estado = "ja_no_vios"
    else:
        estado = anotado.get("estado") if confirmar else None
    nomes = [t["nome"] for t in r.get("tarefas") or []]
    if estado == "gravada":
        conta["gravadas"] += len(nomes)
        for i, nome in enumerate(nomes, 1):
            emitir("ci", ci=ci, tarefa=nome, etapa="gravada", tarefa_num=f"{ci}-{i}")
    elif estado == "ja_no_vios":
        conta["ja_tinha"] += 1
        emitir("ci", ci=ci, tarefa=nomes[0] if nomes else "", etapa="ja_tinha")
    elif estado == "duplicada":
        conta["duplicatas"] += 1
        emitir("ci", ci=ci, etapa="duplicata")
    elif not confirmar and len(no_quadro) == len(nomes) and nomes:
        conta["testadas"] += len(nomes)  # ensaio: a tarefa parou no quadro, nada foi gravado
    elif not confirmar and any("já tem tarefa no VIOS" in l for l in linhas):
        conta["ja_tinha"] += 1
        emitir("ci", ci=ci, etapa="ja_tinha")
    else:
        conta["erros"] += 1
        motivo = anotado.get("mensagem") or (linhas[-1] if linhas else "não deu para lançar")
        emitir("ci", ci=ci, tarefa=nomes[0] if nomes else "", etapa="erro", motivo=str(motivo)[:200])
