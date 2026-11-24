"""Relatório "Processos - Comentários" do VIOS (relatorio-de-comentarios-em-processos.php).

Só LÊ: escolhe o Grupo Cliente, "Todos" (ativos E encerrados) e "Mostrar" tudo, e clica em
Pesquisar. Uma pesquisa traz todos os comentários das tarefas dos processos do grupo, cada um
com o CI do processo (no link da linha) — inclusive os encerrados, que a lista de processos do
Jarvis (só Ativos) não mostra. É a fonte do "Percentual ganho" (nucleo/percentual.py).

O nome de quem comentou não é guardado (sigilo da equipe).
"""
import logging
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

log = logging.getLogger(__name__)

URL = "https://roneely.vios.com.br/?pag=sys/relatorios/relatorio-de-comentarios-em-processos.php"
FILTRO_GRUPO = "pesq[clientes_grupos_id]"

PESQUISAR = """
const [sel, valor] = arguments;
const form = sel.form;
const escolher = (nome, texto) => {
    const s = form.elements[nome];
    if (!s) return `filtro ${nome} não encontrado`;
    const op = [...s.options].find(o => o.text.trim() === texto);
    if (!op) return `opção '${texto}' não encontrada em ${nome}`;
    s.value = op.value;
    return '';
};
sel.value = valor;
const erro = escolher('pesq[filtros]', 'Todos') || escolher('pesq[limit]', '9999999');
if (erro) return erro;
const botao = form.querySelector('#Pesq') || [...form.querySelectorAll('button')].find(b => b.textContent.trim() === 'Pesquisar');
if (!botao) return 'botão Pesquisar não encontrado';
form.requestSubmit(botao);  // o mesmo que clicar em Pesquisar
return '';
"""

# cada célula tem data-id "<tabela>_linha_<n>_<coluna>"; o CI está no link da linha (processos_id=N)
LER = """
const linhas = [];
for (const tr of document.querySelectorAll('tr[id*="_linha_"]')) {
    const c = {};
    for (const td of tr.querySelectorAll('td[data-id]')) {
        const id = td.getAttribute('data-id');
        const m = id.match(/_linha_\\d+_(.+)$/);
        if (m) c[m[1]] = td.innerText.replace(/\\u00a0/g, ' ').trim();
    }
    const ci = (tr.outerHTML.match(/processos_id[^0-9]{0,6}([0-9]+)/) || [])[1] || '';
    if ('comentarios_texto' in c) linhas.push({ci, ...c});
}
const total = document.querySelector('.geratabela_total_quantidade_original');
return {linhas, total: total ? total.textContent : ''};
"""


def _data(texto):
    try:
        return datetime.strptime(texto.strip()[:19], "%d/%m/%Y %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(texto.strip()[:10], "%d/%m/%Y")
        except ValueError:
            return None


def _partes(texto):
    return [p.strip() for p in (texto or "").split("\n") if p.strip()]


def pesquisar(driver, valor_grupo, timeout):
    """{CI: {"numero", "acao", "parte_ativa", "parte_passiva", "observacao", "comentarios": [{"data", "texto"}]}}
    com os comentários em ordem de data (o mais antigo primeiro)."""
    driver.get(URL)
    sel = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))
    erro = driver.execute_script(PESQUISAR, sel, valor_grupo)
    if erro:
        raise RuntimeError(f"relatório de comentários: {erro}")
    WebDriverWait(driver, timeout).until(EC.staleness_of(sel))
    # com milhares de comentários a tabela demora: espera o rodapé "Total (N)" ou a tabela vazia
    WebDriverWait(driver, max(timeout, 120)).until(lambda d: d.execute_script(
        "return !!document.querySelector('.geratabela_total_quantidade_original') || "
        "document.body.innerText.includes('Nenhum registro')"))
    r = driver.execute_script(LER)

    n = re.search(r"\d+", r["total"] or "")
    if n and int(n.group()) != len(r["linhas"]):
        log.warning("Comentários: rodapé diz %s, mas li %d linhas", n.group(), len(r["linhas"]))
    processos, sem_ci = {}, 0
    for l in r["linhas"]:
        if not l["ci"]:
            sem_ci += 1
            continue
        p = processos.setdefault(l["ci"], {"numero": "", "acao": "", "parte_ativa": [], "parte_passiva": [],
                                           "observacao": "", "comentarios": []})
        # número, ação, partes e observação se repetem em cada comentário do processo
        p["numero"] = p["numero"] or l.get("numeros_concat", "").replace("CNJ:", "").strip()
        p["acao"] = p["acao"] or l.get("acao", "")
        p["parte_ativa"] = p["parte_ativa"] or _partes(l.get("partes_ativas_concat"))
        p["parte_passiva"] = p["parte_passiva"] or _partes(l.get("partes_passivas_concat"))
        p["observacao"] = p["observacao"] or l.get("obs_proc", "")
        texto = l.get("comentarios_texto", "")
        if texto:
            p["comentarios"].append({"data": l.get("comentarios_data", ""), "texto": texto})
    for p in processos.values():
        p["comentarios"].sort(key=lambda c: _data(c["data"]) or datetime.min)
    if sem_ci:
        log.warning("Comentários: %d linha(s) sem o CI do processo foram puladas", sem_ci)
    log.info("Comentários: %d comentários de %d processos (ativos e encerrados)", len(r["linhas"]), len(processos))
    return processos
