"""Preenche N.° CNJ, Órgão julgador e Valor da ação na tela de edição do
processo, grava e confere relendo a tela.

Proteções: a tela de edição tem que ser do mesmo processo aberto pelo "Visualizar";
campo já preenchido com outro valor nunca é sobrescrito (o caso inteiro é pulado);
só os três campos são tocados; sem confirmar=True nada é gravado.
"""
import logging
import re
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot import vila
from bot.comprovante import DADOS
from bot.vios import abrir, digitos, esperar_ajax, ids_numericos, normalizar

log = logging.getLogger(__name__)


_ORGAO = next(d for d in DADOS if d.chave == "orgao")


class EdicaoErro(Exception):
    """Problema antes de gravar: nada foi alterado no VIOS."""


class ConferenciaErro(Exception):
    """O botão Gravar foi clicado, mas a releitura não confirmou os valores: conferir à mão."""


def _campo(driver, dado, cfg):
    """O campo do dado: pelo seletor do .env (CAMPO_CNJ...) ou pelo rótulo na tela. Tem que ser um só."""
    if cfg.campos.get(dado.chave):
        achados = driver.find_elements(*cfg.campos[dado.chave])
    else:
        achados = driver.execute_script(
            """
            const norm = t => (t || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '')
                .toUpperCase().replace(/[^A-Z0-9]+/g, ' ').trim();
            const alvo = norm(arguments[0]);
            const achados = [];
            for (const l of document.querySelectorAll('label')) {
                if (norm(l.innerText || l.textContent) !== alvo) continue;
                let c = l.htmlFor ? document.getElementById(l.htmlFor) : null;
                if (!c) c = l.querySelector('input, select, textarea');
                if (!c) {
                    const grupo = l.closest('.form-group') || l.parentElement;
                    c = grupo && grupo.querySelector("input:not([type=hidden]), select, textarea");
                }
                if (c && !achados.includes(c)) achados.push(c);
            }
            return achados;
            """,
            dado.rotulo,
        )
    if len(achados) != 1:
        raise EdicaoErro(f"campo '{dado.rotulo}': esperado 1 na tela de edição, achei {len(achados)}")
    return achados[0]


def _ler(driver, campo):
    return driver.execute_script(
        """
        const c = arguments[0];
        if (c.tagName === 'SELECT') return [...c.selectedOptions].map(o => o.value ? o.text.trim() : '').join(', ');
        return (c.value || '').trim();
        """,
        campo,
    )


def _preencher(driver, campo, valor):
    """Escreve por JavaScript; em <select> escolhe a opção com o mesmo texto. O texto da opção é
    normalizado como `normalizar` (NFKD e só ASCII: "31ª" vira "31A"), senão nunca bate."""
    ok = driver.execute_script(
        """
        const [c, valor, alvo] = arguments;
        const norm = t => t.normalize('NFKD').replace(/[^\\x00-\\x7f]/g, '').toUpperCase().replace(/\\s+/g, ' ').trim();
        if (c.tagName === 'SELECT') {
            const op = [...c.options].find(o => norm(o.text) === alvo);
            if (!op) return false;
            c.value = op.value;
        } else {
            c.value = valor;
        }
        c.dispatchEvent(new Event('input', {bubbles: true}));
        c.dispatchEvent(new Event('change', {bubbles: true}));
        if (window.jQuery) { jQuery(c).trigger('change'); if (jQuery(c).selectpicker) jQuery(c).selectpicker('refresh'); }
        return true;
        """,
        campo,
        valor,
        normalizar(valor),
    )
    if not ok:
        raise EdicaoErro(f"opção '{valor}' não existe no campo")


def _tem_opcao(driver, campo, valor):
    """True se o campo não é lista ou se a lista já tem a opção com o mesmo texto."""
    return driver.execute_script(
        """
        const [c, alvo] = arguments;
        const norm = t => t.normalize('NFKD').replace(/[^\\x00-\\x7f]/g, '').toUpperCase().replace(/\\s+/g, ' ').trim();
        return c.tagName !== 'SELECT' || [...c.options].some(o => norm(o.text) === alvo);
        """,
        campo,
        normalizar(valor),
    )


def _um_visivel(driver, cfg, seletor, onde):
    try:
        achados = WebDriverWait(driver, cfg.timeout).until(
            lambda d: [e for e in d.find_elements(*seletor) if e.is_displayed()])
    except TimeoutException:
        raise EdicaoErro(f"{onde} não apareceu: nada gravado")
    if len(achados) != 1:
        raise EdicaoErro(f"esperado 1 {onde}, achei {len(achados)}: nada gravado")
    return achados[0]


def _cadastrar_orgao(driver, nome, cfg, confirmar):
    """O órgão do PDF não está na lista: abre o "+" do campo (modal "Cadastrar Órgão Julgador")
    e escreve o nome. Sem confirmar para aí (nada é cadastrado). Com confirmar, grava o
    cadastro e espera a opção aparecer na lista."""
    botoes = driver.find_elements(*cfg.orgao_cadastrar)
    if len(botoes) != 1:
        raise EdicaoErro(f"órgão '{nome}' não está na lista e achei {len(botoes)} botões '+' de cadastro: nada gravado")
    driver.execute_script("arguments[0].click();", botoes[0])
    caixa = _um_visivel(driver, cfg, cfg.orgao_nome, "campo de nome no cadastro do órgão julgador")
    driver.execute_script(
        """
        const [c, v] = arguments;
        c.value = v;
        c.dispatchEvent(new Event('input', {bubbles: true}));
        c.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        caixa,
        nome,
    )
    log.info("Órgão julgador '%s' não está na lista: nome escrito no cadastro", nome)
    if not confirmar:
        return
    gravar = _um_visivel(driver, cfg, cfg.orgao_gravar, "botão Gravar do cadastro do órgão julgador")
    driver.execute_script("arguments[0].click();", gravar)
    try:
        WebDriverWait(driver, cfg.timeout).until(
            lambda d: _tem_opcao(d, _campo(d, _ORGAO, cfg), nome))
    except TimeoutException:
        raise EdicaoErro(f"cliquei em Gravar no cadastro do órgão '{nome}' e a opção não apareceu na lista: "
                         "processo não alterado, conferir se o órgão foi cadastrado")
    log.info("Órgão julgador '%s' cadastrado", nome)


def _responder_avisos(driver, gravar, cfg):
    """Depois do Gravar: espera a página sair da tela de edição. Se o VIOS abrir o aviso conhecido
    (SweetAlert, ex.: "O Cliente do contrato não é categorizado como cliente!"), clica no único
    Confirmar visível. Qualquer outro aviso não é respondido: ConferenciaErro com o texto dele."""
    for _ in range(3):
        def saiu_ou_aviso(d):
            if EC.staleness_of(gravar)(d):
                return "saiu"
            avisos = [a for a in d.find_elements(By.CSS_SELECTOR, ".swal2-popup") if a.is_displayed()]
            return avisos[0] if avisos else False
        r = WebDriverWait(driver, cfg.timeout).until(saiu_ou_aviso)
        if r == "saiu":
            return
        texto = " ".join((r.get_attribute("textContent") or "").split())
        if not re.search(cfg.edicao_confirmar, normalizar(texto)):
            raise ConferenciaErro(f"depois de Gravar o VIOS mostrou um aviso que o bot não responde: '{texto}'")
        confirmar = [b for b in r.find_elements(By.CSS_SELECTOR, ".swal2-confirm") if b.is_displayed()]
        if len(confirmar) != 1:
            raise ConferenciaErro(f"aviso '{texto}': esperado 1 botão Confirmar, achei {len(confirmar)}")
        log.info("Aviso do VIOS depois de Gravar: '%s' -> Confirmar", texto)
        driver.execute_script("arguments[0].click();", confirmar[0])
        WebDriverWait(driver, cfg.timeout).until(lambda d: _fechado(r))
    raise ConferenciaErro("depois de Gravar o VIOS continuou mostrando avisos")


def _fechado(el):
    try:
        return not el.is_displayed()
    except StaleElementReferenceException:
        return True


def igual(dado, a, b):
    if dado.so_digitos:
        return digitos(a) == digitos(b)
    return normalizar(a) == normalizar(b)


def vazio(dado, valor):
    """Campo sem valor. No valor da ação, o VIOS mostra '0,00' quando não há valor: conta como vazio."""
    if dado.chave == "valor":
        return not digitos(valor).strip("0")
    return not valor


def conflitos(antes, valores):
    """Campos que já têm valor diferente do PDF. Qualquer um deles impede gravar a tarefa."""
    return [f"{d.rotulo}: na tela '{antes[d.chave]}', no PDF '{valores[d.chave]}'" for d in DADOS
            if not vazio(d, antes[d.chave]) and not igual(d, antes[d.chave], valores[d.chave])]


def _ler_todos(driver, cfg):
    return {d.chave: _ler(driver, _campo(driver, d, cfg)) for d in DADOS}


def _ir(driver, url, cfg):
    """O lápis do N.° CNJ já deixa o navegador na tela de edição: só abre se estiver em outra página."""
    if driver.current_url != url:
        abrir(driver, url, cfg.timeout)


def ler(driver, url, ids_processo, cfg):
    """Somente leitura: abre a tela de edição e devolve o que os três campos mostram.
    Nunca preenche, não dispara eventos e não clica em nada."""
    _ir(driver, url, cfg)
    WebDriverWait(driver, cfg.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form")))
    if not ids_processo & ids_numericos(driver.current_url):
        raise EdicaoErro(f"a tela de edição ({driver.current_url}) não é do processo aberto")
    return _ler_todos(driver, cfg)


def editar(driver, url, ids_processo, valores, cfg, pasta_logs, confirmar):
    """Devolve 'gravado', 'ja_estava' ou 'teste'. Qualquer divergência levanta EdicaoErro."""
    _ir(driver, url, cfg)
    WebDriverWait(driver, cfg.timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form")))
    if not ids_processo & ids_numericos(driver.current_url):
        raise EdicaoErro(f"a tela de edição ({driver.current_url}) não é do processo aberto: nada alterado")

    antes = _ler_todos(driver, cfg)
    if conflitos(antes, valores):
        raise EdicaoErro("campo já preenchido com outro valor, nada alterado (conferir manualmente): "
                         + "; ".join(conflitos(antes, valores)))
    mudar = [d for d in DADOS if vazio(d, antes[d.chave])]
    if not mudar:
        log.info("Os três campos já estavam com os valores do comprovante")
        return "ja_estava"

    # órgão fora da lista: cadastra primeiro (na simulação só escreve o nome no modal), antes de
    # tocar nos outros campos
    a_cadastrar = _ORGAO in mudar and not _tem_opcao(driver, _campo(driver, _ORGAO, cfg), valores["orgao"])
    if a_cadastrar:
        _cadastrar_orgao(driver, valores["orgao"], cfg, confirmar)
        if not confirmar:
            mudar = [d for d in mudar if d is not _ORGAO]
            driver.save_screenshot(str(Path(pasta_logs) / f"orgao_{digitos(valores['cnj'])}_{datetime.now():%H%M%S}.png"))
            driver.execute_script("document.querySelectorAll('.modal').forEach(m => window.jQuery ? jQuery(m).modal('hide') : m.style.display = 'none');")

    # vila: só os nomes dos campos (nunca os valores)
    vila.extra(campos=[d.chave for d in mudar],
               **({"orgao_cadastrado" if confirmar else "orgao_novo": True} if a_cadastrar else {}))
    vila.etapa("preenchendo", campos=[d.chave for d in mudar])
    for d in mudar:
        _preencher(driver, _campo(driver, d, cfg), valores[d.chave])
    tela = _ler_todos(driver, cfg)
    for d in mudar:
        if not igual(d, tela[d.chave], valores[d.chave]):
            raise EdicaoErro(f"{d.rotulo}: preenchi '{valores[d.chave]}' e a tela mostra '{tela[d.chave]}'")
    log.info("Preenchido: %s", "; ".join(f"{d.rotulo} = {tela[d.chave]}" for d in mudar))

    driver.execute_script("document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.style.visibility = 'hidden');")
    driver.save_screenshot(str(Path(pasta_logs) / f"edicao_{digitos(valores['cnj'])}_{datetime.now():%H%M%S}.png"))
    if not confirmar:
        if a_cadastrar:
            log.info("SIMULAÇÃO: órgão '%s' seria cadastrado e escolhido na lista", valores["orgao"])
        log.info("SIMULAÇÃO: campos preenchidos e NÃO gravados")
        return "teste"

    botoes = driver.find_elements(*cfg.edicao_gravar)
    if len(botoes) != 1:
        raise EdicaoErro(f"esperado 1 botão Gravar, achei {len(botoes)}: nada gravado")
    driver.execute_script("arguments[0].click();", botoes[0])
    # daqui em diante pode ter gravado: qualquer falha vira ConferenciaErro (conferir à mão)
    try:
        _responder_avisos(driver, botoes[0], cfg)
        esperar_ajax(driver, cfg.timeout)
        # confirma relendo a tela de edição do zero
        abrir(driver, url, cfg.timeout)
        depois = _ler_todos(driver, cfg)
    except Exception as e:
        raise ConferenciaErro(f"não consegui reler a tela depois de gravar ({e.__class__.__name__}: {e})") from e
    errados = [f"{d.rotulo}: esperado '{valores[d.chave]}', gravado '{depois[d.chave]}'" for d in DADOS
               if not igual(d, depois[d.chave], valores[d.chave])]
    if errados:
        raise ConferenciaErro("conferência depois de gravar falhou: " + "; ".join(errados))
    return "gravado"
