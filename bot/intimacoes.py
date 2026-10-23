import json
import logging
import re
from datetime import date, datetime, timedelta

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.extracao import _limpar
log = logging.getLogger(__name__)

# máximo de linhas que a tela do VIOS lista (o padrão da tela é 50)
LIMITE = "500"

# só as linhas de dados têm id "<tabela>_linha_<n>"
LINHAS = (By.CSS_SELECTOR, "tr[id*='_linha_']")

# coluna do VIOS (final do data-id da célula) -> campo no JSON
COLUNAS = {
    "imp_pub_id": "ci",
    "intimacao_numeros": "numeros",
    "pr_clientes_nome": "cliente",
    "advogado_nome": "advogado",
    "advogados_auxiliares_abr": "auxiliares",
    "oab_origem": "oab",
    "cidade_e_uf_do_processo": "cidade",
    "fornecedor": "fornecedor",
    "descricao": "informacoes_extras",
}


def periodo_pesquisa(dias_atras, hoje=None):
    """Devolve (inicio, fim): fim = hoje - dias_atras; se fim cair no domingo,
    o início volta para a sexta (na segunda pega sexta, sábado e domingo)."""
    fim = (hoje or date.today()) - timedelta(days=dias_atras)
    inicio = fim - timedelta(days=2) if fim.weekday() == 6 else fim
    return inicio, fim


def _br(dia):
    return dia.strftime("%d/%m/%Y")


def pesquisar(driver, cfg):
    """Pesquisa as intimações disponibilizadas no período e devolve (inicio, fim)."""
    inicio, fim = periodo_pesquisa(cfg.dias_atras)
    log.info("Pesquisando intimações de %s a %s", _br(inicio), _br(fim))
    campo = WebDriverWait(driver, cfg.timeout).until(EC.presence_of_element_located(cfg.pesquisa_data))

    # Preenche e envia por JavaScript: depois do login o VIOS abre um popup de
    # recado por cima da tela, e o bot não deve mexer nele. Os demais filtros
    # ficam no padrão da tela (ex.: "Com Tarefa Lançada" = Não).
    # "Marcar todas" = selecionar todas as opções do <select multiple>.
    filtros = {"pesq[idata]": _br(inicio), "pesq[fdata]": _br(fim), "pesq[limit]": LIMITE}
    marcados = driver.execute_script(
        """
        const [campo, filtros, marcarTodas] = arguments;
        const form = campo.form;
        for (const [nome, valor] of Object.entries(filtros)) form.elements[nome].value = valor;
        const marcados = {};
        for (const nome of marcarTodas) {
            const sel = form.elements[nome];
            if (!sel) continue;
            for (const op of sel.options) op.selected = true;
            marcados[nome] = sel.selectedOptions.length;
        }
        form.requestSubmit(form.querySelector("[type=submit]"));
        return marcados;
        """,
        campo,
        filtros,
        cfg.marcar_todas,
    )
    for nome in cfg.marcar_todas:
        if nome in marcados:
            log.info("Marcar todas em %s: %d opções", nome, marcados[nome])
        else:
            log.warning("Filtro %s não encontrado na tela", nome)
    WebDriverWait(driver, cfg.timeout).until(EC.staleness_of(campo))
    return inicio, fim


def _texto(el):
    return _limpar(el.get_attribute("innerText"))


def _ler_linha(tr):
    # data-id = "<tabela>_linha_<n>_<coluna>"
    celulas = {
        td.get_attribute("data-id").split("_linha_", 1)[1].split("_", 1)[1]: td
        for td in tr.find_elements(By.CSS_SELECTOR, "td[data-id]")
    }
    item = {campo: _texto(celulas[col]) for col, campo in COLUNAS.items() if col in celulas}

    datas = _texto(celulas["sdata"])
    for campo, rotulo in (("disponibilizacao", "Disponibilização"), ("publicacao", "Publicação")):
        m = re.search(rotulo + r":\s*(\d{2}/\d{2}/\d{4})", datas)
        item[campo] = m.group(1) if m else ""

    sinal = celulas["d_sinal"].find_elements(By.CSS_SELECTOR, "[title]")
    item["situacao"] = sinal[0].get_attribute("title") if sinal else ""

    # a célula Texto começa com as etiquetas de sugestão de tarefa
    td = celulas["texto"]
    sugestoes = [_texto(b) for b in td.find_elements(By.CSS_SELECTOR, ".vj-badge")]
    texto = _texto(td)
    for s in sugestoes:
        texto = texto.replace(s, "", 1)
    item["sugestoes_tarefa"] = sugestoes
    item["texto"] = texto.strip()
    if not item["texto"]:
        raise ValueError("texto vazio")

    m = re.search(r"comunicacao_id:\s*(\d+)", texto)
    item["comunicacao_id"] = m.group(1) if m else ""

    lancar = tr.find_elements(By.CSS_SELECTOR, "a[href*='int-lanca.php']:not([href*='act=del'])")
    item["link_lancar"] = lancar[0].get_attribute("href") if lancar else ""
    return item


def extrair_intimacoes(driver, cfg, inicio, fim):
    """Lê a tabela de resultado e devolve (itens, qtd_erros)."""
    try:
        WebDriverWait(driver, cfg.timeout).until(EC.presence_of_all_elements_located(LINHAS))
    except TimeoutException:
        log.info("Nenhuma intimação encontrada de %s a %s", _br(inicio), _br(fim))
        return [], 0

    trs = driver.find_elements(*LINHAS)
    log.info("%d intimações na tabela", len(trs))

    total = driver.find_elements(By.CSS_SELECTOR, ".geratabela_total_quantidade_original")
    if total:
        n = re.search(r"\d+", total[0].get_attribute("textContent"))
        if n and int(n.group()) != len(trs):
            log.warning("Rodapé diz %s intimações, mas há %d linhas na página", n.group(), len(trs))

    itens, erros = [], 0
    for n, tr in enumerate(trs, 1):
        try:
            item = _ler_linha(tr)
            try:
                fora = not inicio <= datetime.strptime(item["disponibilizacao"], "%d/%m/%Y").date() <= fim
            except ValueError:
                fora = True
            if fora:
                log.warning("Linha %d (CI %s) tem disponibilização '%s', fora do período", n, item.get("ci"), item["disponibilizacao"])
            itens.append(item)
        except Exception as e:
            erros += 1
            log.warning("Linha %d pulada: %s", n, getattr(e, "msg", None) or e)

    return itens, erros


def salvar_json(itens, pasta, inicio, fim):
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{inicio:%Y-%m-%d}" if inicio == fim else f"{inicio:%Y-%m-%d}_a_{fim:%Y-%m-%d}"
    arquivo = pasta / f"intimacoes_{nome}.json"
    with arquivo.open("w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)
    return arquivo
