"""Tarefas do calendário do VIOS, classificadas (bot/classificacao.py)."""
import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from bot import classificacao, vila
from bot.vios import abrir, links, normalizar

log = logging.getLogger(__name__)


def tarefas(driver, cfg):
    """Abre o calendário e devolve todas as tarefas com link, cada uma com a classificação:
    ([{texto, link, classe, motivo}], quantos itens do calendário ficaram de fora por não ter link,
    estar repetidos ou apagados). Só a classe previdenciária é processada."""
    vila.emitir("fase", fase="lendo_calendario")
    log.info("Abrindo o calendário: %s", cfg.calendario_url)
    abrir(driver, cfg.calendario_url, cfg.timeout)
    # as tarefas chegam depois da página carregar (o calendário as busca por POST)
    try:
        WebDriverWait(driver, cfg.timeout).until(lambda d: d.find_elements(*cfg.calendario_tarefa))
    except TimeoutException:
        log.warning("Nenhuma tarefa apareceu no calendário em %ds", cfg.timeout)
    filtro = normalizar(cfg.calendario_filtro)
    elementos = driver.find_elements(*cfg.calendario_tarefa)
    com_termo = sum(filtro in normalizar(e.get_attribute("textContent")) for e in elementos)
    saida = []
    for t in links(driver, cfg.calendario_tarefa):
        texto = " ".join(t["texto"].split())
        classe, motivo = classificacao.classificar(texto, cfg.calendario_filtro, cfg.calendario_tipo)
        saida.append({"texto": texto, "link": t["href"], "classe": classe, "motivo": motivo})
    contagem = {c: sum(t["classe"] == c for t in saida)
                for c in (classificacao.PREVIDENCIARIA, classificacao.AMBIGUA, classificacao.IGNORADA)}
    log.info("Calendário: %d item(ns), %d com '%s', %d com link: %d previdenciária(s), %d ambígua(s), %d ignorada(s)",
             len(elementos), com_termo, cfg.calendario_filtro, len(saida), *contagem.values())
    fora = len(elementos) - len(saida)
    if fora:
        log.warning("%d item(ns) do calendário sem link, repetido(s) ou apagado(s): conferir CALENDARIO_TAREFA", fora)
    return saida, fora


def evento(todas, registradas=(), alvo=None):
    """Evento "calendario" da vila: contagens e uma linha por tarefa (só pxe_id, classe e códigos;
    nunca o texto da tarefa). registradas = links já em saida/registro.json; alvo = filtro do
    --tarefa (função link -> bool) ou None."""
    linhas, contagem = [], {"previdenciarias": 0, "processar": 0, "ignoradas": 0, "ambiguas": 0}
    for t in todas:
        motivo = vila.motivo_classificacao(t["classe"], t["motivo"])
        linha = {"tarefa_id": vila.pxe_id(t["link"])}
        if t["classe"] == classificacao.PREVIDENCIARIA or motivo == "outro_tipo":
            contagem["previdenciarias"] += 1
            linha["classe"] = classificacao.PREVIDENCIARIA
            if motivo == "outro_tipo":
                linha.update(decisao="ignorada", motivo=motivo)
            elif t["link"] in registradas:
                linha.update(decisao="ja_registrada", motivo="ja_registrada")
            elif alvo and not alvo(t["link"]):
                linha.update(decisao="ignorada", motivo="fora_da_tarefa_unica")
            else:
                linha["decisao"] = "processar"
                contagem["processar"] += 1
        else:
            linha.update(classe=t["classe"], motivo=motivo)
            contagem["ignoradas" if t["classe"] == classificacao.IGNORADA else "ambiguas"] += 1
        linhas.append(linha)
    return vila.emitir("calendario", total=len(todas), **contagem, tarefas=linhas)
