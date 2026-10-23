import logging
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.navegador import esperar

log = logging.getLogger(__name__)


def _limpar(texto):
    # TAB e quebra de linha quebrariam o formato do .txt
    return " ".join(texto.split())


def extrair_tabela(driver, cfg):
    """Lê a tabela e devolve (cabecalho, linhas, qtd_erros)."""
    tabela = esperar(driver, cfg.tabela, cfg.timeout)

    cabecalho = []
    if cfg.tem_cabecalho:
        cabecalho = [_limpar(th.text) for th in tabela.find_elements(By.CSS_SELECTOR, "thead th")]
        if not cabecalho:  # tabela sem <thead>: usa a primeira linha com <th>
            cabecalho = [_limpar(th.text) for th in tabela.find_elements(By.CSS_SELECTOR, "tr th")]

    linhas, erros = [], 0
    trs = [tr for tr in tabela.find_elements(By.CSS_SELECTOR, "tr") if tr.find_elements(By.TAG_NAME, "td")]
    for n, tr in enumerate(trs, 1):
        try:
            celulas = [_limpar(td.text) for td in tr.find_elements(By.TAG_NAME, "td")]
            if cabecalho and len(celulas) != len(cabecalho):
                raise ValueError(f"{len(celulas)} colunas, esperado {len(cabecalho)}")
            linhas.append(celulas)
        except Exception as e:
            erros += 1
            log.warning("Linha %d pulada: %s", n, e)

    return cabecalho, linhas, erros


def salvar_txt(cabecalho, linhas, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"dados_{datetime.now():%Y-%m-%d_%H%M%S}.txt"
    with arquivo.open("w", encoding="utf-8") as f:
        if cabecalho:
            f.write("\t".join(cabecalho) + "\n")
        for linha in linhas:
            f.write("\t".join(linha) + "\n")
    return arquivo


def _carregar_todos(driver, locator, timeout):
    """Espera os cards e rola até o fim, caso a página carregue mais ao rolar."""
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(locator))
    except TimeoutException:
        return []
    anterior = -1
    cards = driver.find_elements(*locator)
    while len(cards) != anterior:
        anterior = len(cards)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        try:
            WebDriverWait(driver, 3).until(lambda d: len(d.find_elements(*locator)) > anterior)
        except TimeoutException:
            pass
        cards = driver.find_elements(*locator)
    return cards


def extrair_cards(driver, cfg):
    """Lê cada card e devolve (blocos, qtd_erros); cada bloco é (cabecalho, texto)."""
    cards = _carregar_todos(driver, cfg.card, cfg.timeout)
    log.info("%d cards encontrados", len(cards))

    blocos, erros = [], 0
    for n, card in enumerate(cards, 1):
        try:
            cabecalho = ""
            if cfg.card_cabecalho:
                el = card.find_element(*cfg.card_cabecalho)
                linhas = (_limpar(l) for l in el.get_attribute("innerText").splitlines())
                cabecalho = "\n".join(l for l in linhas if l)
            el = card.find_element(*cfg.card_texto) if cfg.card_texto else card
            texto = _limpar(el.get_attribute("innerText"))
            if not texto:
                raise ValueError("texto vazio")
            blocos.append((cabecalho, texto))
        except Exception as e:
            erros += 1
            log.warning("Card %d pulado: %s", n, getattr(e, "msg", None) or e)

    return blocos, erros


def salvar_cards_txt(blocos, pasta):
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"intimacoes_{datetime.now():%Y-%m-%d_%H%M%S}.txt"
    with arquivo.open("w", encoding="utf-8") as f:
        for n, (cabecalho, texto) in enumerate(blocos, 1):
            f.write(f"===== {n}/{len(blocos)} =====\n")
            if cabecalho:
                f.write(cabecalho + "\n\n")
            f.write(texto + "\n\n")
    return arquivo
