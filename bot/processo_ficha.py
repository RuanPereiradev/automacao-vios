"""Ficha do processo no VIOS (processos-vis.php) -> dict com campos, tarefas, comentários e arquivos.

Só LÊ o VIOS: abre a ficha pelo endereço de "Visualizar" e lê a página.
Não clica em nada (nem Editar, Apagar ou Processar) e não envia formulário.

A página é montada por JavaScript (Vue): o robô espera os blocos de dados
aparecerem e roda bot/js/ficha.js, o mesmo script que dá para testar no
console do navegador.
"""
import logging
import re
import unicodedata
from pathlib import Path

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from bot.processos_grupo import URL_LISTA

log = logging.getLogger(__name__)

ARQUIVO_JS = Path(__file__).resolve().parent / "js" / "ficha.js"

# mesmo endereço da lista, trocando só a página: ?pag=sys/processos/processos-vis.php&processos_id=<CI>
URL_FICHA = URL_LISTA.split("?", 1)[0] + "?pag=sys/processos/processos-vis.php&processos_id={ci}"


def _classe(nome):
    return f"contains(concat(' ', normalize-space(@class), ' '), ' {nome} ')"


# rótulos dos blocos de dados (o Vue pode montar os rótulos antes de chegar o dado)
ROTULOS = (By.CSS_SELECTOR, ".vj-bloco-info-text-area p strong")
# <p> dos blocos com ao menos um valor: texto fora do rótulo e fora de .vj-acoes-dados
BLOCOS = (
    By.XPATH,
    f"//*[{_classe('vj-bloco-info-text-area')}]//p[strong]"
    f"[.//text()[normalize-space()][not(ancestor::strong)][not(ancestor::*[{_classe('vj-acoes-dados')}])]]",
)
# tabela de tarefas (DataTables cujo cabeçalho tem "Tipo de tarefa") já com dado:
# linha de tarefa (mais de uma célula) ou o aviso "Nenhum registro". "Carregando..." não conta.
TAREFAS = (
    By.XPATH,
    f"//div[{_classe('dataTables_wrapper')}]"
    "[.//thead[contains(normalize-space(.), 'Tipo de tarefa')]]"
    "//tbody/tr[count(td) > 1 or contains(normalize-space(.), 'Nenhum registro')]",
)
CAMPO_SENHA = (By.CSS_SELECTOR, "input[name='form[senha]']")

# a ficha pode não ter tarefas: espera pouco e segue
TEMPO_TAREFAS = 3

# rótulo do VIOS -> campo normalizado
NORMALIZADOS = {
    "cidade_uf": "Cidade / UF",
    "fase": "Fase",
    "data_distribuicao": "Data da ação / Distribuição",
    "valor_acao": "Valor da ação",
    "justica": "Justiça",
    "sistema": "Sistema do tribunal",
}
CAMPOS_TAREFA = ("ci", "situacao", "tipo", "descricao", "comentarios", "para_conclusao", "limite", "concluida_em")
CAMPOS_COMENTARIO = ("data", "autor", "texto")
CAMPOS_ARQUIVO = ("data", "pasta", "tipo", "descricao", "arquivo")

# o VIOS mostra campo vazio assim
VAZIOS = {"00/00/0000", "0,00", "R$ 0,00", "R$0,00", "-"}


class SessaoExpirada(Exception):
    """A tela de login apareceu: quem chama faz novo login e tenta de novo."""


_JS = None


def script_ficha():
    """Conteúdo de bot/js/ficha.js pronto para o execute_script."""
    global _JS
    if _JS is None:
        js = ARQUIVO_JS.read_text(encoding="utf-8").strip().rstrip(";")
        # entre parênteses e com quebra de linha: comentário no fim do arquivo não engole o ")"
        _JS = "return (\n" + js + "\n);"
    return _JS


def url_ficha(ci):
    ci = str(ci or "").strip()
    if not re.fullmatch(r"\d+", ci):
        raise ValueError(f"CI inválido para abrir a ficha: {ci!r}")
    return URL_FICHA.format(ci=ci)


def na_tela_de_login(driver):
    try:
        if "entrar.php" in (driver.current_url or "").lower():
            return True
        return bool(driver.find_elements(*CAMPO_SENHA))
    except Exception:
        # navegador fechado ou travado: não é caso de novo login
        return False


def _limpar(texto):
    if texto is None:
        return ""
    return " ".join(str(texto).split())


def _vazio(texto):
    texto = _limpar(texto)
    # "/" sozinho: Cidade e UF vazias ("<span></span> / <span></span>")
    if texto in VAZIOS or re.fullmatch(r"[\s/-]*", texto):
        return ""
    return texto


def _valor(texto):
    # "R$ 50.000,00" -> "50.000,00"
    texto = _vazio(texto)
    texto = re.sub(r"^R\$\s*", "", texto)
    return "" if texto in VAZIOS else texto


def _chave(rotulo):
    rotulo = unicodedata.normalize("NFKD", rotulo or "").encode("ascii", "ignore").decode()
    return "".join(rotulo.lower().split())


def _campo(campos, rotulo):
    alvo = _chave(rotulo)
    for r, v in campos.items():
        if _chave(r) == alvo:
            return v
    return ""


def _lista(itens, chaves):
    if not isinstance(itens, list):
        return []
    saida = []
    for it in itens:
        if isinstance(it, dict):
            saida.append({k: _limpar(it.get(k)) for k in chaves})
    return saida


def _montar(bruto):
    """Resultado do ficha.js -> dict do contrato (tipos garantidos, campos vazios = "")."""
    campos = bruto.get("campos")
    campos = {_limpar(k): _limpar(v) for k, v in campos.items()} if isinstance(campos, dict) else {}

    ficha = {"ok": True, "erro": "", "campos": campos}
    for nome, rotulo in NORMALIZADOS.items():
        ficha[nome] = _vazio(_limpar(bruto.get(nome)) or _campo(campos, rotulo))
    ficha["valor_acao"] = _valor(ficha["valor_acao"])

    ficha["tarefas"] = _lista(bruto.get("tarefas"), CAMPOS_TAREFA)
    ficha["comentarios"] = _lista(bruto.get("comentarios"), CAMPOS_COMENTARIO)
    ficha["arquivos"] = _lista(bruto.get("arquivos"), CAMPOS_ARQUIVO)
    for t in ficha["tarefas"]:
        for k in ("para_conclusao", "limite", "concluida_em"):
            t[k] = _vazio(t[k])

    if not campos:
        ficha["ok"] = False
        ficha["erro"] = "ficha sem campos (a página não carregou os dados?)"
    elif not any(campos.values()):
        ficha["ok"] = False
        ficha["erro"] = "ficha só com rótulos, sem nenhum valor (a página não carregou os dados?)"
    return ficha


def ficha_vazia(erro):
    """Ficha com erro, no mesmo formato da ficha lida."""
    ficha = {"ok": False, "erro": erro, "campos": {}}
    ficha.update({nome: "" for nome in NORMALIZADOS})
    ficha.update({"tarefas": [], "comentarios": [], "arquivos": []})
    return ficha


def _blocos_ou_login(driver):
    if na_tela_de_login(driver):
        return "login"
    return bool(driver.find_elements(*BLOCOS))


def ler_ficha(driver, ci, timeout):
    """Abre a ficha do processo <ci> e devolve o dict da ficha.

    Levanta SessaoExpirada se cair na tela de login. Outros problemas
    (página não carregou, erro no script) voltam como {"ok": False, "erro": ...}.
    """
    try:
        url = url_ficha(ci)
    except ValueError as e:
        return ficha_vazia(str(e))

    try:
        driver.get(url)
    except WebDriverException as e:
        if na_tela_de_login(driver):
            raise SessaoExpirada(f"tela de login ao abrir a ficha do CI {ci}")
        return ficha_vazia(f"não abriu a ficha: {getattr(e, 'msg', None) or e}")

    if na_tela_de_login(driver):
        raise SessaoExpirada(f"tela de login ao abrir a ficha do CI {ci}")

    try:
        estado = WebDriverWait(driver, timeout).until(_blocos_ou_login)
    except TimeoutException:
        if na_tela_de_login(driver):
            raise SessaoExpirada(f"tela de login ao abrir a ficha do CI {ci}")
        try:
            so_rotulos = bool(driver.find_elements(*ROTULOS))
        except WebDriverException:
            so_rotulos = False
        if so_rotulos:
            return ficha_vazia(f"a ficha mostrou os rótulos, mas nenhum valor em {timeout}s")
        return ficha_vazia(f"a ficha não carregou em {timeout}s")
    except WebDriverException as e:
        return ficha_vazia(f"erro ao esperar a ficha: {getattr(e, 'msg', None) or e}")
    if estado == "login":
        raise SessaoExpirada(f"tela de login ao abrir a ficha do CI {ci}")

    # tarefas carregam depois; ficha sem tarefas não pode travar o robô
    try:
        WebDriverWait(driver, min(timeout, TEMPO_TAREFAS), poll_frequency=0.2).until(
            lambda d: d.find_elements(*TAREFAS)
        )
    except TimeoutException:
        log.debug("CI %s: tabela de tarefas não apareceu (segue sem esperar)", ci)
    except WebDriverException as e:
        log.debug("CI %s: erro ao esperar as tarefas: %s", ci, getattr(e, "msg", None) or e)

    try:
        bruto = driver.execute_script(script_ficha())
    except WebDriverException as e:
        if na_tela_de_login(driver):
            raise SessaoExpirada(f"tela de login ao ler a ficha do CI {ci}")
        return ficha_vazia(f"erro no script da ficha: {getattr(e, 'msg', None) or e}")
    if not isinstance(bruto, dict):
        return ficha_vazia(f"script da ficha devolveu {type(bruto).__name__}, esperado um objeto")

    ficha = _montar(bruto)
    if not ficha["ok"] and na_tela_de_login(driver):
        raise SessaoExpirada(f"tela de login ao ler a ficha do CI {ci}")
    log.debug(
        "CI %s: %d campos, %d tarefas, %d comentários, %d arquivos",
        ci, len(ficha["campos"]), len(ficha["tarefas"]), len(ficha["comentarios"]), len(ficha["arquivos"]),
    )
    return ficha
