"""Caminho no VIOS da tarefa de edição até a galeria do comprovante e a tela de edição.

Tarefa -> número do processo (abre um modal) -> "Visualizar" do modal -> tela do processo ->
linha PROTOCOLAR INICIAL (PREVIDENCIÁRIO) da tabela de tarefas -> "Visualizar arquivo" (galeria).
Na tela do processo, o lápis do N.° CNJ leva à tela de edição.

Os dois cliques (número do processo e lápis) são feitos por JavaScript, no elemento exato e
só quando existe um único: os dois só abrem o modal / a tela de edição. Em cada passo tem que
haver exatamente um item; nenhum ou mais de um = ProcessoErro (tarefa pulada, nada alterado).
"""
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from bot.vios import CNJ, esperar_ajax, normalizar


class ProcessoErro(Exception):
    pass


def _esperar(driver, cfg, condicao, erro):
    try:
        return WebDriverWait(driver, cfg.timeout).until(condicao)
    except TimeoutException:
        raise ProcessoErro(erro)


def _um(achados, onde):
    if len(achados) != 1:
        raise ProcessoErro(f"esperado 1 {onde}, achei {len(achados)}")
    return achados[0]


def link_processo(driver, cfg):
    """Na tarefa: clica no número do processo e devolve o link do único "Visualizar" do modal."""
    numero = _um(_esperar(driver, cfg, lambda d: d.find_elements(*cfg.processo_numero),
                          "número do processo não apareceu na tarefa"), "número do processo na tarefa")
    driver.execute_script("arguments[0].click();", numero)
    visiveis = _esperar(driver, cfg, lambda d: [e for e in d.find_elements(*cfg.processo_link) if e.is_displayed()],
                        "o modal do processo não mostrou o 'Visualizar'")
    return _um(visiveis, "'Visualizar' no modal do processo").get_attribute("href")


def cnj(driver, cfg):
    """CNJs do campo N.° CNJ da tela do processo (vazio enquanto a edição não foi feita)."""
    campo = _um(_esperar(driver, cfg, lambda d: d.find_elements(*cfg.processo_cnj),
                         "campo N.° CNJ não apareceu na tela do processo"), "campo N.° CNJ na tela do processo")
    return set(CNJ.findall(campo.get_attribute("textContent") or ""))


def link_galeria(driver, cfg):
    """Na tela do processo: link "Visualizar arquivo" da única tarefa PROTOCOLAR INICIAL (PREVIDENCIÁRIO)."""
    linhas = _esperar(driver, cfg, lambda d: d.find_elements(*cfg.protocolo_linhas),
                      "tabela de tarefas não apareceu na tela do processo")
    alvo = normalizar(cfg.protocolo_tarefa)
    achadas = []
    for linha in linhas:
        dados = driver.execute_script(
            """
            const tr = arguments[0];
            const tipo = tr.querySelector('td:nth-child(3) span');
            return {tipo: tipo ? tipo.textContent : '', apagado: !!tr.querySelector("[title='Apagada']")};
            """,
            linha,
        )
        if not dados["apagado"] and normalizar(dados["tipo"]).startswith(alvo):
            achadas.append(linha)
    linha = _um(achadas, f"tarefa '{cfg.protocolo_tarefa}' no processo")
    hrefs = {a.get_attribute("href") for a in linha.find_elements(*cfg.protocolo_arquivos)} - {None, ""}
    return _um(sorted(hrefs), f"'Visualizar arquivo' na tarefa '{cfg.protocolo_tarefa}'")


def ir_para_edicao(driver, cfg):
    """Na tela do processo: clica no lápis do N.° CNJ e devolve o endereço da tela de edição."""
    lapis = _um(_esperar(driver, cfg, lambda d: d.find_elements(*cfg.edicao_link),
                         "lápis do N.° CNJ não apareceu na tela do processo"), "lápis do N.° CNJ")
    janelas, antes = len(driver.window_handles), driver.current_url
    driver.execute_script("arguments[0].click();", lapis)
    _esperar(driver, cfg, lambda d: d.current_url != antes or len(d.window_handles) != janelas,
             "o lápis do N.° CNJ não abriu a tela de edição")
    if len(driver.window_handles) != janelas:
        raise ProcessoErro("o lápis do N.° CNJ abriu outra janela: tela de edição não usada")
    esperar_ajax(driver, cfg.timeout)
    return driver.current_url
