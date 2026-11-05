"""Tela do processo (a "lupa", processos-vis.php): Dados do Processo + tarefas.

Só LÊ: abre o mesmo endereço do botão da lupa e lê a página. O "Mostrar mais"
das tarefas só esconde o texto com a classe limite-texto; o robô tira essa
classe por JavaScript (sem clicar) e lê o texto inteiro.
"""
import logging
import re
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

log = logging.getLogger(__name__)

URL_LUPA = "https://roneely.vios.com.br/index.php?pag=sys/processos/processos-vis.php&processos_id={ci}"

# tabela de tarefas: a que tem o link "Visualizar Tarefas Subsequentes"
LINK_TAREFA = (By.CSS_SELECTOR, "a[href*='pxe-visualizar-subsequentes']")

LER = """
const ci = arguments[0];
// Dados do Processo: <p><strong><span>Rótulo</span>: </strong> <span>valor</span> ...</p>
// o título pode ter o número num elemento filho: pega o mais interno com esse texto
const normal = t => t.replace(/\\s+/g, ' ').trim();
const titulo = [...document.querySelectorAll('h1, h2, h3, h4, h5, .ibox-title, div, span')].reverse()
    .find(e => normal(e.textContent) === 'Dados do Processo - CI ' + ci);
const caixa = titulo ? (titulo.closest('.ibox, .card, .panel') || document) : document;
const dados = {};
for (const p of caixa.querySelectorAll('p')) {
    const st = p.firstElementChild;
    if (!st || st.tagName !== 'STRONG' || !st.querySelector('span')) continue;
    const rotulo = st.textContent.replace(/:\\s*$/, '').trim();
    const c = p.cloneNode(true);
    c.firstElementChild.remove();
    c.querySelectorAll('.vj-acoes-dados').forEach(e => e.remove());
    if (!(rotulo in dados)) dados[rotulo] = c.textContent.replace(/\\s+/g, ' ').trim();
}

// "Mostrar mais": tira a classe que corta o texto, sem clicar
document.querySelectorAll('.limite-texto').forEach(e => e.classList.remove('limite-texto'));

const link = document.querySelector("a[href*='pxe-visualizar-subsequentes']");
const tabela = link ? link.closest('table') : null;
const tarefas = [];
if (tabela) {
    const cab = [...tabela.querySelectorAll('thead th, thead td')].map(e => e.textContent.trim());
    const col = nome => cab.indexOf(nome);
    // sem o texto dos botões ("Mostrar mais"/"Esconder")
    const texto = td => {
        if (!td) return '';
        const botoes = [...td.querySelectorAll('button')];
        botoes.forEach(b => b.style.display = 'none');
        const t = td.innerText.replace(/\\u00a0/g, ' ').trim();
        botoes.forEach(b => b.style.display = '');
        return t;
    };
    for (const tr of tabela.querySelectorAll('tbody tr')) {
        const tds = [...tr.children];
        const status = tds[0] && tds[0].querySelector('[title], [data-original-title]');
        const tipo = tds[col('Tipo de tarefa')];
        const badges = tipo ? [...tipo.querySelectorAll('.vj-badge')].map(b => b.textContent.trim()) : [];
        const nome = tipo ? [...tipo.querySelectorAll(':scope span, :scope div > span')]
            .filter(s => !s.classList.contains('vj-badge')).map(s => s.textContent.trim()).filter(Boolean)[0] : '';
        tarefas.push({
            id: texto(tds[col('CI')]),
            status: status ? (status.getAttribute('title') || status.getAttribute('data-original-title') || '') : '',
            etiquetas: badges,
            tipo: nome || texto(tipo),
            descricao: texto(tds[col('Descrição')]),
            comentarios: texto(tds[col('Comentários')]),
            datas: texto(tds[col('Datas')]),
            envolvidos: texto(tds[col('Envolvidos')]),
        });
    }
}
return {achou_titulo: !!titulo, dados, tarefas};
"""


def _data(rotulo, texto):
    m = re.search(rotulo + r":?\s*(\d{2}/\d{2}/\d{4})", texto)
    return m.group(1) if m else ""


def _pessoas(texto, rotulo):
    """'Responsáveis: A\\nB\\n\\nConcluiu a tarefa: C' -> [A, B] para 'Responsáveis'."""
    m = re.search(rotulo + r":\s*(.*?)(?:\n\s*\n|\n?[A-ZÀ-Úa-zà-ú ]+ a tarefa:|$)", texto, re.S)
    if not m:
        return []
    return [p.strip() for p in m.group(1).split("\n") if p.strip()]


def _arrumar_tarefa(t):
    datas = t.pop("datas")
    envolvidos = t.pop("envolvidos")
    t["para_conclusao"] = _data("Para conclusão", datas)
    t["limite"] = _data("Limite", datas)
    t["concluida_em"] = _data("Concluída em", datas)
    t["responsaveis"] = _pessoas(envolvidos, "Responsáveis")
    concluiu = _pessoas(envolvidos, "Concluiu a tarefa")
    t["concluiu"] = concluiu[0] if concluiu else ""
    t["cancelada"] = any(e.upper() == "CANCELADA" for e in t["etiquetas"]) or t["status"].lower() == "cancelada"
    t["concluida"] = bool(t["concluida_em"]) or t["status"].lower() == "concluída"
    return t


def ler_processo(driver, ci, timeout):
    """Abre a lupa do processo e devolve {"dados": {rótulo: valor}, "tarefas": [...]}."""
    driver.get(URL_LUPA.format(ci=ci))
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return document.body.innerText.replace(/\\s+/g, ' ').includes(arguments[0])",
            f"Dados do Processo - CI {ci}"))
    # as tarefas são desenhadas depois (Vue); processo sem tarefa não tem o link
    try:
        WebDriverWait(driver, min(timeout, 10)).until(EC.presence_of_element_located(LINK_TAREFA))
        _esperar_estavel(driver)
    except TimeoutException:
        log.info("CI %s: nenhuma tarefa na tela", ci)
    r = driver.execute_script(LER, str(ci))
    if not r["achou_titulo"]:
        raise RuntimeError(f"tela do processo CI {ci} sem o bloco 'Dados do Processo'")
    return {"dados": r["dados"], "tarefas": [_arrumar_tarefa(t) for t in r["tarefas"]]}


def _esperar_estavel(driver, folga=1.0, maximo=10):
    """Espera o número de tarefas na tela parar de mudar."""
    anterior, fim = -1, time.time() + maximo
    while time.time() < fim:
        n = len(driver.find_elements(*LINK_TAREFA))
        if n == anterior:
            return
        anterior = n
        time.sleep(folga)
