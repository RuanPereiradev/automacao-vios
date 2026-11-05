"""Lista de processos por Grupo Cliente (processos-lista.php).

Só LÊ o VIOS: preenche o filtro "Grupo Cliente" e clica em Pesquisar. Nunca
usa os botões Apagar/Editar nem o "Processar" (ações em lote) da tela.
Cada linha dá o CI, que abre a tela do processo (bot/processos_detalhe.py).
"""
import logging
import re
import unicodedata

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from nucleo.extracao import _limpar

log = logging.getLogger(__name__)

URL_LISTA = "https://roneely.vios.com.br/?pag=sys/processos/processos-lista.php&menu_lateral=true"
FILTRO_GRUPO = "pesq[clientes_grupos_id]"
# a tela mostra 30 por padrão; 500 é o máximo que ela exibe sem CSV
LIMITE = "500"

LINHAS = (By.CSS_SELECTOR, "tr[id^='processos-lista_linha_']")

# coluna do VIOS (final do data-id da célula) -> campo
COLUNAS = {
    "processos_id": "ci",
    "pr_areas_nome": "area",
    "contratos_vis": "contrato",
    "processos_acoes_nome": "acao",
    "orgaos_uf": "uf",
    "orgaos_nome": "orgao",
    "advogado_nome": "advogado",
    "clientes_nome": "cliente",
    "objeto": "objeto",
}

VINCULO = {
    "PROCESSO PRINCIPAL": "processo principal",
    "APENSO": "apenso (processo ligado a outro processo principal)",
}


def _texto(el):
    return _limpar(el.get_attribute("innerText"))


def _linhas(el):
    # partes vêm uma por linha (<br>): "Autor: FULANO"
    return [_limpar(t) for t in el.get_attribute("innerText").split("\n") if t.strip()]


def _normal(nome):
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(nome.upper().split())


def grupos_disponiveis(driver, timeout):
    """{nome do grupo: valor} do filtro Grupo Cliente (sem o TODOS)."""
    driver.get(URL_LISTA)
    sel = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))
    return {
        _limpar(op.get_attribute("textContent")): op.get_attribute("value")
        for op in sel.find_elements(By.TAG_NAME, "option")
        if op.get_attribute("value") not in ("", "0")
    }


def pesquisar_grupo(driver, valor, timeout):
    """Abre a lista, escolhe o grupo e clica em Pesquisar (pelo JavaScript, por causa do popup de recado)."""
    driver.get(URL_LISTA)
    sel = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))
    erro = driver.execute_script(
        """
        const [sel, valor, limite] = arguments;
        const form = sel.form;
        const botao = form.querySelector("#Pesq");
        if (!botao) return "botão Pesquisar não encontrado no formulário do filtro";
        sel.value = valor;
        if (form.elements["pesq[limit]"]) form.elements["pesq[limit]"].value = limite;
        form.requestSubmit(botao);  // o mesmo que clicar em Pesquisar
        return "";
        """,
        sel,
        valor,
        LIMITE,
    )
    if erro:
        raise RuntimeError(erro)
    WebDriverWait(driver, timeout).until(EC.staleness_of(sel))
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))


def _ler_linha(tr):
    # data-id = "processos-lista_linha_<n>_<coluna>"
    celulas = {
        td.get_attribute("data-id").split("_linha_", 1)[1].split("_", 1)[1]: td
        for td in tr.find_elements(By.CSS_SELECTOR, "td[data-id]")
    }
    item = {campo: _texto(celulas[col]) for col, campo in COLUNAS.items() if col in celulas}
    item["ci"] = item.get("ci") or tr.get_attribute("data-processos_id") or ""

    # Número: etiquetas (ex.: "Cliente OURO") + "CNJ: 0000..." ou "Outros: ..."
    numero = celulas.get("nro_proc_html")
    if numero is not None:
        etiquetas = [_texto(b) for b in numero.find_elements(By.CSS_SELECTOR, ".vj-badge")]
        texto = _texto(numero)
        for e in etiquetas:
            texto = texto.replace(e, "", 1)
        item["numero"] = texto.strip()

    item["parte_ativa"] = _linhas(celulas["ativahtml"]) if "ativahtml" in celulas else []
    item["parte_passiva"] = _linhas(celulas["passivahtml"]) if "passivahtml" in celulas else []

    # o tooltip do bootstrap move o title para data-original-title
    sinal = celulas.get("sinal_vinculo_processo")
    vinculo = ""
    if sinal is not None:
        for el in sinal.find_elements(By.CSS_SELECTOR, "[title], [data-original-title]"):
            vinculo = (el.get_attribute("title") or el.get_attribute("data-original-title") or "").strip()
            if vinculo:
                break
    item["vinculo"] = VINCULO.get(vinculo.upper(), vinculo.lower())
    return item


def ler_processos(driver, timeout):
    """Lê a tabela de resultado e devolve (itens, qtd_erros)."""
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(LINHAS))
    except TimeoutException:
        return [], 0
    trs = driver.find_elements(*LINHAS)

    total = driver.find_elements(By.CSS_SELECTOR, ".geratabela_total_quantidade_original")
    if total:
        n = re.search(r"\d+", total[0].get_attribute("textContent"))
        if n and int(n.group()) != len(trs):
            log.warning("Rodapé diz %s processos, mas há %d linhas na página", n.group(), len(trs))

    itens, erros = [], 0
    for n, tr in enumerate(trs, 1):
        try:
            itens.append(_ler_linha(tr))
        except Exception as e:
            erros += 1
            log.warning("Linha %d pulada: %s", n, getattr(e, "msg", None) or e)
    return itens, erros


def nome_arquivo(grupo, extensao=".xlsx"):
    # caracteres que o Windows não aceita em nome de arquivo
    return re.sub(r'[\\/:*?"<>|]', "-", grupo).strip() + extensao
