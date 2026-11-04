"""Telas do VIOS, só leitura: entrar, abrir, esperar, ler tabelas, e utilidades de texto e data.

Duas partes:
  - leitura (Selenium, fina): recebem o `ctx` (usam ctx.driver e ctx.cfg) — entrar, abrir,
    esperar, esperar_varios, esperar_ajax, esperar_ate, clicar, enviar_pesquisa, html,
    texto_pagina, links, ler_tabela;
  - interpretação (pura, testável com fixtures): ler_tabela_html, normalizar, limpar, digitos,
    contem, data_br, datas_br, data_hora_br, hora, br, ids_numericos, cnjs, url_proibida,
    clique_proibido, url_absoluta.

Proteções (além do bloqueio de envios do navegador):
  - abrir() recusa endereço com trecho de ORELHA_URL_PROIBIDA (act=del, int-lanca.php...) e, com
    o VIOS de verdade, para tudo (BloqueioInativo) se a página abriu sem o bloqueio de envios;
  - clicar() recusa botão/link cujo texto tenha termo de ORELHA_CLIQUE_PROIBIDO (Salvar, Concluir...).
Padrão de login copiado do Ultron (bot/login.py) e do Albi (albi/main.py, entrar).
"""
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse

log = logging.getLogger("orelha")

CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
CNJ_SOLTO = re.compile(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}")
DATA_BR = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
HORA = re.compile(r"\b([01]?\d|2[0-3])[:h]([0-5]\d)\b")
# telas onde o Orelha pode enviar um formulário de PESQUISA (o form.action ou a página atual tem um
# destes trechos); acrescente outras em ORELHA_PESQUISA_PERMITIDA, depois de conferir na tela real
PESQUISA_PERMITIDA = ("int-pesquisa.php", "processos-lista.php", "calendario.php")


class ViosErro(Exception):
    """Algo na tela do VIOS não saiu como esperado (elemento não apareceu etc.)."""


class LoginErro(ViosErro):
    pass


class AcessoProibido(ViosErro):
    """O Orelha ia abrir um endereço ou clicar num botão que grava/apaga: recusado."""


class BloqueioInativo(ViosErro):
    """A página abriu sem o bloqueio de envios: a execução inteira para (o main.py não engole)."""


# ---------------------------------------------------------------- texto e datas (puras)
def normalizar(texto):
    """Maiúsculas, sem acento e com um espaço só (para comparar textos da tela)."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().split())


def limpar(texto):
    """Um espaço só entre as palavras, sem espaço nas pontas (mantém acento e maiúsculas)."""
    return " ".join((texto or "").replace("\xa0", " ").split())


def digitos(texto):
    return re.sub(r"\D", "", texto or "")


def contem(texto, *termos):
    """True se o texto tem algum dos termos (comparação sem acento e sem diferença de maiúsculas)."""
    t = normalizar(texto)
    return any(normalizar(x) in t for x in termos if x)


def data_br(texto):
    """Primeira data DD/MM/AAAA do texto, como date (None se não tem ou é inválida)."""
    for d in datas_br(texto):
        return d
    return None


def datas_br(texto):
    """Todas as datas DD/MM/AAAA válidas do texto, na ordem."""
    saida = []
    for dia, mes, ano in DATA_BR.findall(texto or ""):
        try:
            saida.append(date(int(ano), int(mes), int(dia)))
        except ValueError:
            pass
    return saida


def hora(texto):
    """Primeira hora do texto como "HH:MM" ("14:00", "9h30" -> "09:30"); "" se não tem."""
    m = HORA.search(texto or "")
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def data_hora_br(texto):
    """Data e hora do texto ("04/11/2026 14:00") como datetime; sem hora = 00:00; None sem data."""
    d = data_br(texto)
    if not d:
        return None
    h = hora(DATA_BR.split(texto, maxsplit=1)[-1]) or "00:00"
    return datetime(d.year, d.month, d.day, int(h[:2]), int(h[3:]))


def br(dia):
    """date -> "DD/MM/AAAA" ("" para None)."""
    return dia.strftime("%d/%m/%Y") if dia else ""


def ids_numericos(url):
    """Valores numéricos (3+ dígitos) da query da URL, ex.: processos_id."""
    return {v for vs in parse_qs(urlparse(url or "").query).values() for v in vs if re.fullmatch(r"\d{3,}", v)}


def cnjs(texto):
    """Números CNJ (0000000-00.0000.0.00.0000) que aparecem no texto, sem repetir, na ordem."""
    vistos = []
    for c in CNJ.findall(texto or ""):
        if c not in vistos:
            vistos.append(c)
    return vistos


def url_absoluta(cfg, caminho):
    """"?pag=sys/..." ou "index.php?pag=..." -> endereço completo na raiz do VIOS (cfg.vios_base)."""
    if re.match(r"https?://", caminho or ""):
        return caminho
    return urljoin(cfg.vios_base, (caminho or "").lstrip("/"))


def url_proibida(url, proibidas):
    """Trecho de `proibidas` que aparece no endereço (comparação em minúsculas), ou ""."""
    u = (url or "").lower()
    for trecho in proibidas or ():
        if trecho and trecho.lower() in u:
            return trecho
    return ""


def clique_proibido(texto, proibidos):
    """Termo proibido que aparece no texto do botão/link (sem acento), ou ""."""
    t = normalizar(texto)
    for termo in proibidos or ():
        if termo and normalizar(termo) in t:
            return termo
    return ""


# ---------------------------------------------------------------- tabelas HTML (puras)
@dataclass
class Linha:
    celulas: list                 # texto de cada célula (td/th), limpo
    colunas: list = field(default_factory=list)   # cabeçalho da tabela (para get por nome)
    links: list = field(default_factory=list)     # [{"texto", "href"}] dos <a> da linha
    titulos: list = field(default_factory=list)   # atributos title de dentro da linha (ícones)
    id: str = ""
    classes: str = ""
    atributos: dict = field(default_factory=dict)  # atributos do <tr>
    por_data_id: dict = field(default_factory=dict)  # coluna do data-id da célula -> texto
    links_celula: list = field(default_factory=list)  # hrefs de cada célula, na ordem das células

    def get(self, coluna, padrao=""):
        """Texto da célula pelo nome da coluna (sem acento/maiúsculas; aceita começo do nome),
        ou pela coluna do data-id ("<tabela>_linha_<n>_<coluna>")."""
        if coluna in self.por_data_id:
            return self.por_data_id[coluna]
        alvo = normalizar(coluna)
        nomes = [normalizar(c) for c in self.colunas]
        for regra in (lambda n: n == alvo, lambda n: n.startswith(alvo)):
            for i, n in enumerate(nomes):
                if regra(n) and i < len(self.celulas):
                    return self.celulas[i]
        return padrao


@dataclass
class Tabela:
    colunas: list
    linhas: list

    def __len__(self):
        return len(self.linhas)

    def __iter__(self):
        return iter(self.linhas)


def _coluna_data_id(data_id):
    if "_linha_" in data_id:
        resto = data_id.split("_linha_", 1)[1]
        return resto.split("_", 1)[1] if "_" in resto else resto
    return data_id


class _LeitorTabela(HTMLParser):
    """Lê a tabela escolhida (a primeira, a de id=..., ou a n-ésima). Tabelas dentro de células
    entram só como texto da célula."""

    def __init__(self, id_tabela=None, indice=0):
        super().__init__(convert_charrefs=True)
        self.id_tabela, self.indice = id_tabela, indice
        self.vistas = 0          # tabelas de nível de cima já abertas
        self.profundidade = 0    # tabelas abertas (contando aninhadas)
        self.nivel_alvo = None   # profundidade da tabela escolhida
        self.terminou = False
        self.no_thead = False
        self.linhas = []         # (eh_cabecalho, Linha)
        self.linha = None
        self.celula = None       # lista de pedaços de texto
        self.celula_th = False
        self.celula_links = []
        self.celula_data_id = ""
        self.todas_th = True
        self.link = None

    def _dentro(self):
        return self.nivel_alvo is not None and not self.terminou and self.profundidade == self.nivel_alvo

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "table":
            self.profundidade += 1
            if self.nivel_alvo is None and not self.terminou:
                escolhida = (a.get("id") == self.id_tabela) if self.id_tabela else (self.vistas == self.indice)
                if not self.id_tabela:
                    self.vistas += 1
                if escolhida:
                    self.nivel_alvo = self.profundidade
            return
        if self.nivel_alvo is None or self.terminou:
            return
        if self.celula is not None and tag == "br":
            self.celula.append(" ")
        if "title" in a and self.linha is not None and a["title"].strip():
            self.linha.titulos.append(limpar(a["title"]))
        if tag == "a" and self.linha is not None:
            self.link = {"texto": [], "href": a.get("href", "")}
        if not self._dentro():
            return
        if tag == "thead":
            self.no_thead = True
        elif tag == "tr":
            self.linha = Linha(celulas=[], id=a.get("id", ""), classes=a.get("class", ""), atributos=a)
            self.todas_th = True
        elif tag in ("td", "th") and self.linha is not None:
            self.celula, self.celula_th, self.celula_links = [], tag == "th", []
            self.todas_th = self.todas_th and tag == "th"
            self.celula_data_id = a.get("data-id", "")

    def handle_endtag(self, tag):
        if tag == "table":
            if self.nivel_alvo is not None and self.profundidade == self.nivel_alvo and not self.terminou:
                self._fechar_linha()
                self.terminou = True
            self.profundidade -= 1
            return
        if self.nivel_alvo is None or self.terminou:
            return
        if tag == "a" and self.link is not None and self.linha is not None:
            href = self.link["href"]
            if href and not href.lower().startswith("javascript"):
                self.linha.links.append({"texto": limpar("".join(self.link["texto"])), "href": href})
                if self.celula is not None:
                    self.celula_links.append(href)
            self.link = None
        if not self._dentro():
            return
        if tag in ("td", "th"):
            self._fechar_celula()
        elif tag == "tr":
            self._fechar_linha()
        elif tag == "thead":
            self.no_thead = False

    def handle_data(self, dados):
        if self.celula is not None:
            self.celula.append(dados)
        if self.link is not None:
            self.link["texto"].append(dados)

    def _fechar_celula(self):
        if self.celula is None or self.linha is None:
            return
        texto = limpar("".join(self.celula))
        self.linha.celulas.append(texto)
        self.linha.links_celula.append(self.celula_links)
        if self.celula_data_id:
            self.linha.por_data_id[_coluna_data_id(self.celula_data_id)] = texto
        self.celula = None

    def _fechar_linha(self):
        self._fechar_celula()
        if self.linha is not None and any(self.linha.celulas):
            self.linhas.append((self.no_thead or self.todas_th, self.linha))
        self.linha = None


def ler_tabela_html(html, id_tabela=None, indice=0, cabecalho=True):
    """Lê uma <table> do HTML e devolve Tabela(colunas, linhas).

    id_tabela: lê a tabela com esse id; senão, a de posição `indice` (0 = a primeira).
    cabecalho=True: a primeira linha só de <th> (ou do <thead>) vira `colunas`; com
    cabecalho=False, todas as linhas são dados. Linhas vazias ficam de fora."""
    leitor = _LeitorTabela(id_tabela, indice)
    leitor.feed(html or "")
    leitor.close()
    leitor._fechar_linha()
    colunas, linhas = [], []
    for eh_cab, linha in leitor.linhas:
        if cabecalho and eh_cab and not colunas and not linhas:
            colunas = linha.celulas
            continue
        linhas.append(linha)
    for linha in linhas:
        linha.colunas = colunas
    return Tabela(colunas=colunas, linhas=linhas)


# ---------------------------------------------------------------- leitura (Selenium)
def _timeout(ctx, timeout):
    return timeout if timeout is not None else ctx.cfg.timeout


def _envios_bloqueados(driver):
    from nucleo.navegador import envios_bloqueados
    return envios_bloqueados(driver)


def _barrados(driver):
    from nucleo.navegador import tentativas_barradas
    return tentativas_barradas(driver)


def pesquisas_permitidas(cfg):
    """Trechos de endereço das telas de pesquisa (os padrões + ORELHA_PESQUISA_PERMITIDA)."""
    extra = cfg.valor("ORELHA_PESQUISA_PERMITIDA", "", "lista") if hasattr(cfg, "valor") else []
    return list(PESQUISA_PERMITIDA) + [t for t in extra or [] if t]


def conferir_formulario(acao, pagina, botao, cfg, pag_oculto=""):
    """Pura: recusa (AcessoProibido) enviar um formulário que não é de pesquisa.

    acao = form.action (o navegador já devolve o endereço da página quando o form não tem action);
    pagina = endereço da página atual (só para a mensagem); botao = texto/value/title do botão que
    vai enviar; pag_oculto = valor do campo "pag" do form, se houver (o VIOS roteia por ?pag=).
    Recusa se o action tem trecho de ORELHA_URL_PROIBIDA, se o botão tem termo de
    ORELHA_CLIQUE_PROIBIDO ou se o DESTINO do envio não é uma tela de pesquisa conhecida. O destino
    é o action; se o action não tem "pag=" e o form tem o campo "pag", vale o campo. Estar numa
    página de pesquisa não basta: um form dessa página que envia para outra tela é recusado."""
    trecho = url_proibida(acao, cfg.urls_proibidas)
    if trecho:
        raise AcessoProibido(f"pesquisa recusada: o formulário envia para endereço com '{trecho}'")
    termo = clique_proibido(botao, cfg.cliques_proibidos)
    if termo:
        raise AcessoProibido(f"pesquisa recusada: o botão do formulário tem '{termo}' ({limpar(botao)[:60]})")
    destino = acao or ""
    if "pag=" not in destino.lower() and pag_oculto:
        destino = "pag=" + pag_oculto
    trecho = url_proibida(destino, cfg.urls_proibidas)
    if trecho:
        raise AcessoProibido(f"pesquisa recusada: o formulário envia para endereço com '{trecho}'")
    permitidas = pesquisas_permitidas(cfg)
    if not url_proibida(destino, permitidas):
        raise AcessoProibido("pesquisa recusada: o formulário não envia para uma tela de pesquisa conhecida "
                             f"({', '.join(permitidas)}; acrescente em ORELHA_PESQUISA_PERMITIDA se for)")


# dados do form do campo e do botão que vai enviar (o de botaoCss ou o primeiro botão de envio,
# inclusive <button> sem type, que também envia)
_JS_FORMULARIO = """
const [campo, botaoCss] = arguments;
const form = campo.form;
if (!form) return null;
const b = (botaoCss && form.querySelector(botaoCss)) || form.querySelector('button:not([type]), button[type=submit], input[type=submit], input[type=image]');
const texto = b ? [b.innerText, b.value, b.title, b.getAttribute('aria-label')].filter(Boolean).join(' ') : '';
const pag = form.elements['pag'] && form.elements['pag'].value ? form.elements['pag'].value : '';
return {acao: form.action || '', pagina: location.href, botao: texto, pag: pag};
"""


def conferir_formulario_da_tela(ctx, campo, botao_css=None):
    """conferir_formulario com os dados do form do `campo` (WebElement) na tela. Devolve False se
    o campo não está num formulário."""
    dados = ctx.driver.execute_script(_JS_FORMULARIO, campo, botao_css or "")
    if not dados:
        return False
    conferir_formulario(dados.get("acao", ""), dados.get("pagina", ""), dados.get("botao", ""), ctx.cfg,
                        dados.get("pag", ""))
    return True


def entrar(ctx, marcar_formulario=False):
    """Login no VIOS. Levanta LoginErro. Nunca escreve a senha no log.

    marcar_formulario=True: o bloqueio de envios já está ligado (main.py liga antes do login, para
    a primeira página depois do login já abrir bloqueada); o form de login é marcado com
    data-orelha-pesquisa="1" (a mesma exceção da pesquisa) para poder ser enviado."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    cfg, driver = ctx.cfg, ctx.driver
    log.info("Abrindo o login do VIOS: %s", cfg.vios_url)
    driver.get(cfg.vios_url)
    espera = WebDriverWait(driver, cfg.timeout)
    try:
        for locator, texto in ((cfg.campo_usuario, cfg.usuario), (cfg.campo_senha, cfg.senha)):
            campo = espera.until(EC.visibility_of_element_located(locator))
            campo.clear()
            campo.send_keys(texto)
    except TimeoutException:
        raise LoginErro("a tela de login não apareceu (confira SISTEMA_URL e LOGIN_CAMPO_*)") from None
    url_login = driver.current_url
    if marcar_formulario:
        tem_form = driver.execute_script(
            "const f = arguments[0].form; if (f) f.setAttribute('data-orelha-pesquisa', '1'); return !!f;", campo)
        if not tem_form:
            log.warning("O campo de senha não está num formulário: o bloqueio pode barrar o login "
                        "(se barrar, use ORELHA_BLOQUEIO_NO_LOGIN=false)")
    if cfg.botao_login:
        espera.until(EC.element_to_be_clickable(cfg.botao_login)).click()
    else:
        campo.send_keys(Keys.ENTER)
    try:
        if cfg.login_sucesso:
            espera.until(EC.visibility_of_element_located(cfg.login_sucesso))
        else:
            espera.until(EC.url_changes(url_login))
    except TimeoutException:
        barrados = _barrados(driver) if marcar_formulario else []
        if barrados:
            log.info("Login: o bloqueio barrou %s", "; ".join(barrados[:5]))
            raise LoginErro(f"login não confirmado em {cfg.timeout}s e o bloqueio de envios barrou "
                            f"{len(barrados)} pedido(s) da tela de login (se o login do VIOS não é um "
                            "formulário comum, use ORELHA_BLOQUEIO_NO_LOGIN=false)") from None
        raise LoginErro(f"login não confirmado em {cfg.timeout}s (usuário/senha errados ou LOGIN_SUCESSO incorreto)") from None
    log.info("Login OK como %s", cfg.usuario)


def esperar_ajax(ctx, timeout=None):
    """Espera a página terminar de carregar e o jQuery não ter requisição pendente."""
    from selenium.webdriver.support.ui import WebDriverWait
    WebDriverWait(ctx.driver, _timeout(ctx, timeout)).until(
        lambda d: d.execute_script("return document.readyState === 'complete' && (!window.jQuery || jQuery.active === 0)"))


def abrir(ctx, url, timeout=None, exigir_bloqueio=True):
    """Abre a página (endereço completo ou "?pag=sys/..." relativo à raiz do VIOS) e espera carregar.
    Recusa endereço proibido (AcessoProibido). Com exigir_bloqueio, para tudo (BloqueioInativo)
    se a página abriu sem o bloqueio de envios. Devolve o endereço aberto."""
    alvo = url_absoluta(ctx.cfg, url)
    trecho = url_proibida(alvo, ctx.cfg.urls_proibidas)
    if trecho:
        raise AcessoProibido(f"endereço recusado (tem '{trecho}', ação que grava/apaga): {alvo}")
    ctx.driver.get(alvo)
    esperar_ajax(ctx, timeout)
    if exigir_bloqueio and not _envios_bloqueados(ctx.driver):
        raise BloqueioInativo(f"bloqueio de envios inativo em {ctx.driver.current_url}: execução interrompida")
    return alvo


def esperar(ctx, locator, timeout=None, visivel=True):
    """Espera um elemento e o devolve. Levanta ViosErro se não aparecer."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    condicao = EC.visibility_of_element_located if visivel else EC.presence_of_element_located
    try:
        return WebDriverWait(ctx.driver, _timeout(ctx, timeout)).until(condicao(locator))
    except TimeoutException:
        raise ViosErro(f"elemento não apareceu em {_timeout(ctx, timeout)}s: {locator[1]}") from None


def esperar_varios(ctx, locator, timeout=None):
    """Espera aparecer pelo menos um elemento e devolve todos; lista vazia se nenhum apareceu."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    try:
        WebDriverWait(ctx.driver, _timeout(ctx, timeout)).until(lambda d: d.find_elements(*locator))
    except TimeoutException:
        return []
    return ctx.driver.find_elements(*locator)


def esperar_ate(ctx, condicao, timeout=None, mensagem="a tela não ficou pronta"):
    """Espera condicao(driver) ser verdadeira e devolve o valor. Levanta ViosErro(mensagem)."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    try:
        return WebDriverWait(ctx.driver, _timeout(ctx, timeout)).until(condicao)
    except TimeoutException:
        raise ViosErro(f"{mensagem} em {_timeout(ctx, timeout)}s") from None


def clicar(ctx, alvo, timeout=None):
    """Clica num botão/link de abrir/pesquisar/filtrar. `alvo` = locator (By, valor) ou WebElement.
    Recusa (AcessoProibido) se o texto, value ou title tiver termo de ORELHA_CLIQUE_PROIBIDO
    ou se o link levar a endereço proibido. Clica por JavaScript (não toca no popup de Recado)."""
    elemento = esperar(ctx, alvo, timeout) if isinstance(alvo, tuple) else alvo
    texto, href = ctx.driver.execute_script(
        "const e = arguments[0]; const a = e.closest('a');"
        "return [[e.innerText, e.value, e.title, e.getAttribute('aria-label')].filter(Boolean).join(' '),"
        " a ? a.href : ''];", elemento)
    termo = clique_proibido(texto, ctx.cfg.cliques_proibidos)
    if termo:
        raise AcessoProibido(f"clique recusado: o botão tem '{termo}' ({limpar(texto)[:60]})")
    trecho = url_proibida(href, ctx.cfg.urls_proibidas)
    if trecho:
        raise AcessoProibido(f"clique recusado: o link tem '{trecho}'")
    ctx.driver.execute_script("arguments[0].click();", elemento)
    return elemento


def enviar_pesquisa(ctx, campo, filtros, marcar_todas=(), timeout=None, esperar_recarregar=True):
    """Preenche e envia um formulário de PESQUISA (como o Ultron faz em bot/intimacoes.py).

    campo: locator de um campo do formulário (o form é o dele). filtros: {nome do campo: valor}
    (campos que não existem no form são ignorados e devolvidos em "faltando"). marcar_todas: nomes
    de <select multiple> em que selecionar todas as opções. O form é marcado com
    data-orelha-pesquisa="1" (a única exceção ao bloqueio de envios de formulário), mas só depois de
    conferir_formulario: action sem endereço proibido, botão sem termo proibido e tela de pesquisa
    conhecida (PESQUISA_PERMITIDA + ORELHA_PESQUISA_PERMITIDA).
    Devolve {"faltando": [...], "marcados": {nome: n}}."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    el = esperar(ctx, campo, timeout, visivel=False)
    if not conferir_formulario_da_tela(ctx, el):
        raise ViosErro("o campo da pesquisa não está dentro de um formulário")
    resultado = ctx.driver.execute_script(
        """
        const [campo, filtros, marcarTodas] = arguments;
        const form = campo.form;
        if (!form) return null;
        const faltando = [], marcados = {};
        for (const [nome, valor] of Object.entries(filtros)) {
            const el = form.elements[nome];
            if (!el) { faltando.push(nome); continue; }
            el.value = valor;
            if (el.dispatchEvent) el.dispatchEvent(new Event('change', {bubbles: true}));
        }
        for (const nome of marcarTodas) {
            const sel = form.elements[nome];
            if (!sel || !sel.options) { faltando.push(nome); continue; }
            for (const op of sel.options) op.selected = true;
            marcados[nome] = sel.selectedOptions.length;
        }
        form.setAttribute('data-orelha-pesquisa', '1');
        const botao = form.querySelector('button:not([type]), button[type=submit], input[type=submit], input[type=image]');
        if (form.requestSubmit) form.requestSubmit(botao || undefined); else form.submit();
        return {faltando, marcados};
        """, el, dict(filtros), list(marcar_todas))
    if resultado is None:
        raise ViosErro("o campo da pesquisa não está dentro de um formulário")
    if esperar_recarregar:
        try:
            WebDriverWait(ctx.driver, _timeout(ctx, timeout)).until(EC.staleness_of(el))
        except TimeoutException:
            raise ViosErro("a pesquisa não recarregou a página (bloqueio barrou? ver tentativas_barradas)") from None
        esperar_ajax(ctx, timeout)
        if not _envios_bloqueados(ctx.driver):
            raise BloqueioInativo(f"bloqueio de envios inativo em {ctx.driver.current_url}: execução interrompida")
    return resultado


def html(ctx, locator=None):
    """outerHTML do elemento (ou da página inteira, sem locator), para as funções puras lerem."""
    if locator is None:
        return ctx.driver.execute_script("return document.documentElement.outerHTML")
    return esperar(ctx, locator, visivel=False).get_attribute("outerHTML")


def texto_pagina(ctx):
    return ctx.driver.execute_script("return document.body ? document.body.innerText : ''") or ""


def links(ctx, locator):
    """Links dos elementos (o próprio <a> ou o primeiro <a> dentro dele): [{texto, href}], sem
    repetir. Linha com o ícone "Apagada" fica de fora (como no Zangão)."""
    vistos, saida = set(), []
    for el in ctx.driver.find_elements(*locator):
        item = ctx.driver.execute_script(
            """
            const e = arguments[0];
            const a = e.matches('a[href]') ? e : e.querySelector('a[href]');
            const linha = e.closest('tr');
            return {texto: (e.innerText || e.textContent || '').trim(), href: a ? a.href : '',
                    apagado: !!(linha && linha.querySelector("[title='Apagada']"))};
            """, el)
        if item["apagado"] or not item["href"] or item["href"].startswith("javascript"):
            continue
        if item["href"] not in vistos:
            vistos.add(item["href"])
            saida.append({"texto": limpar(item["texto"]), "href": item["href"]})
    return saida


def ler_tabela(ctx, locator, timeout=None, cabecalho=True):
    """Espera a tabela e a lê com ler_tabela_html (a mesma leitura dos testes com fixture)."""
    el = esperar(ctx, locator, timeout, visivel=False)
    return ler_tabela_html(el.get_attribute("outerHTML"), cabecalho=cabecalho)


# ---------------------------------------------------------------- GET sem desenhar a página
_JS_BUSCAR_GET = """
const [url, cb] = [arguments[0], arguments[arguments.length - 1]];
fetch(url, {method: 'GET', credentials: 'same-origin'})
  .then(async r => {
    // páginas do VIOS vêm em ISO-8859-1/windows-1252 (r.text() trocava os acentos por "?")
    const bytes = await r.arrayBuffer();
    const tipo = (r.headers.get('content-type') || '').match(/charset=([\\w-]+)/i);
    let charset = tipo ? tipo[1] : '';
    if (!charset) {
      const cab = new TextDecoder('ascii').decode(bytes.slice(0, 4096));
      const m = cab.match(/charset=["']?([\\w-]+)/i);
      charset = m ? m[1] : 'windows-1252';
    }
    try { return new TextDecoder(charset).decode(bytes); } catch (e) { return new TextDecoder('windows-1252').decode(bytes); }
  })
  .then(cb).catch(e => cb('ERRO_ORELHA: ' + e));
"""


def buscar_get(ctx, url, timeout=180):
    """HTML de uma página do VIOS por GET, buscada de dentro da página aberta (mesma sessão), SEM
    desenhar: telas com centenas de linhas travavam o Chrome do bot (> 120 s). Só GET; recusa
    endereço proibido. Precisa de uma página do VIOS já aberta no navegador."""
    alvo = url_absoluta(ctx.cfg, url)
    trecho = url_proibida(alvo, ctx.cfg.urls_proibidas)
    if trecho:
        raise AcessoProibido(f"endereço recusado (tem '{trecho}'): {alvo}")
    ctx.driver.set_script_timeout(timeout)
    html = ctx.driver.execute_async_script(_JS_BUSCAR_GET, alvo) or ""
    if html.startswith("ERRO_ORELHA"):
        raise ViosErro(html)
    return html

