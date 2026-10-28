"""Lista de processos por Grupo Cliente (processos-lista.php) -> um .txt por grupo.

Só LÊ o VIOS: preenche o filtro "Grupo Cliente" e clica em Pesquisar. Nunca
usa os botões Apagar/Editar nem o "Processar" (ações em lote) da tela.
O .txt é a base para outra IA escrever um relatório para o cliente leigo.
"""
import logging
import re
import unicodedata
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.extracao import _limpar

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


def posicao_cliente(item):
    """Se o cliente é quem entrou com a ação (autor) ou quem está sendo processado (réu)."""
    cliente = _normal(item.get("cliente", ""))
    if not cliente:
        return "não identificada"

    def nomes(partes):
        return {_normal(p.split(":", 1)[-1]) for p in partes}

    if cliente in nomes(item["parte_ativa"]):
        return "autor (o cliente entrou com a ação)"
    if cliente in nomes(item["parte_passiva"]):
        return "réu (o cliente está sendo processado)"
    return "não identificada (o cliente não aparece nas partes da lista)"


def _contagem(itens, campo):
    contagem = {}
    for it in itens:
        chave = it.get(campo) or "não informado"
        contagem[chave] = contagem.get(chave, 0) + 1
    return sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))


def montar_txt(grupo, itens, agora=None):
    agora = agora or datetime.now()
    for it in itens:
        it["posicao"] = posicao_cliente(it)

    def ou_nada(valor):
        return valor or "não informado"

    linhas = [
        f"RELATÓRIO DE PROCESSOS — GRUPO {grupo}",
        f"Dados do sistema VIOS em {agora:%d/%m/%Y às %H:%M} (processos ativos)",
        f"Total de processos: {len(itens)}",
        "",
        "=" * 70,
        "RESUMO",
        "=" * 70,
    ]
    for titulo, campo in (("Por empresa/pessoa do grupo", "cliente"), ("Por área", "area"), ("Posição do cliente", "posicao")):
        linhas.append(f"{titulo}:")
        linhas += [f"  - {chave}: {qtd}" for chave, qtd in _contagem(itens, campo)]
        linhas.append("")

    ordenados = sorted(itens, key=lambda it: (it.get("cliente", ""), it.get("area", ""), it.get("ci", "")))
    cliente_atual = None
    for n, it in enumerate(ordenados, 1):
        if it.get("cliente") != cliente_atual:
            cliente_atual = it.get("cliente")
            linhas += ["=" * 70, f"CLIENTE: {ou_nada(cliente_atual)}", "=" * 70, ""]
        linhas += [
            f"PROCESSO {n} de {len(itens)}",
            f"  Número do processo: {ou_nada(it.get('numero'))}",
            f"  Área: {ou_nada(it.get('area'))}",
            f"  Tipo de ação: {ou_nada(it.get('acao'))}",
            f"  Assunto (objeto): {ou_nada(it.get('objeto'))}",
            f"  Onde tramita: {ou_nada(it.get('orgao'))}" + (f" ({it['uf']})" if it.get("uf") else ""),
            f"  Quem entrou com a ação (parte ativa): {ou_nada('; '.join(it['parte_ativa']))}",
            f"  Contra quem (parte passiva): {ou_nada('; '.join(it['parte_passiva']))}",
            f"  Posição do cliente: {it['posicao']}",
            f"  Advogado responsável: {ou_nada(it.get('advogado'))}",
            f"  Vínculo: {ou_nada(it.get('vinculo'))}",
            f"  Contrato: {ou_nada(it.get('contrato'))}",
            f"  Código interno no VIOS (CI): {ou_nada(it.get('ci'))}",
            "",
        ]
    return "\n".join(linhas)


def nome_arquivo(grupo):
    # caracteres que o Windows não aceita em nome de arquivo
    return re.sub(r'[\\/:*?"<>|]', "-", grupo).strip() + ".txt"
