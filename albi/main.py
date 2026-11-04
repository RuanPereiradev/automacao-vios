"""Albi — bot do Sonar (Leme Forense). Separado do Ultron e do Zangão: tem .venv, .env, logs/ e
saida/ próprios dentro de albi/ e não importa nada do bot/.

Entra no Sonar (encerrando a outra sessão se cair em /login-conflito) e, para cada pessoa do .txt,
faz uma Pesquisa de Processos, uma por vez:
  1. Nova Pesquisa: Identificador Projeto = nome da EMPRESA, tipo CPF/CNPJ, documento, Continuar;
  2. passo 2 ("Pedido"): confere o documento, escolhe o Sacado (SONAR_SACADO, padrão o escritório)
     e, só com --confirmar, clica em "Confirmar Pedido" (R$ 15,70 cada) e guarda o número do pedido;
  3. espera o Sonar terminar cada pedido e baixa o resultado de cada um: o PDF da página do pedido
     (todos, inclusive "não consta") e a planilha ("Baixar Resultados") de quem tem processos
     encontrados; escreve resultado.txt (empresa, CPF, nome, pedido, o que achou e os arquivos).
Sem --confirmar ele faz o 1 e o 2 e NÃO compra nada (teste). CPF já pesquisado para a mesma
empresa nos últimos 30 dias não é comprado de novo: usa o pedido anterior
(registro em saida/pedidos_confirmados.json).

.txt (modelo em modelo_pedidos.txt): um bloco por empresa e uma pessoa por linha, "CPF ; nome".
    EMPRESA: Empresa A
    123.456.789-09 ; Maria da Silva
    ---
    EMPRESA: Empresa B
    111.444.777-35 ; Ana Lima
Linha vazia, começando com # ou só com --- é ignorada. Sem EMPRESA:, vale tudo como uma lista só.

uso (dentro de albi/):
  ./rodar.sh                                  só entra e abre a tela de novo pedido (confere o .env)
  ./rodar.sh --arquivo pedidos.txt            teste: preenche até o passo 2 e não compra
  ./rodar.sh --arquivo pedidos.txt --confirmar   COMPRA as pesquisas, espera e baixa os resultados
  ./rodar.sh --arquivo pedidos.txt --baixar      NÃO compra: baixa de novo os resultados (PDF e
                                                 planilha) dos pedidos já comprados (pelo registro)
  ./rodar.sh --arquivo pedidos.txt --conferir    só lê o .txt e mostra (JSON) o que seria feito
  --saida PASTA   onde ficam resultado.txt, os PDFs e as planilhas (padrão: saida/<data_hora>/)
  --eventos       escreve os eventos da vila na saída padrão (assim o Ultron roda o Albi pela /albi)
  ./rodar.sh [caminho/do/.env] ...            outro .env
"""
import base64
import json
import logging
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PASTA = Path(__file__).resolve().parent
LOGS = PASTA / "logs"
log = logging.getLogger("albi")
OBRIGATORIAS = ("SONAR_URL", "SONAR_CPF_CNPJ", "SONAR_EMAIL", "SONAR_SENHA")
PADROES = {
    "LOGIN_CAMPO_CPF_CNPJ": "css:#loginform input[id=input-cpf-cnpj]",
    "LOGIN_CAMPO_EMAIL": "css:#loginform input[id=loginform-username]",
    "LOGIN_CAMPO_SENHA": "css:#loginform input[id=loginform-password]",
    "LOGIN_BOTAO": "css:#loginform [id=btn-login]",
    "CONFLITO_BOTAO": "xpath://button[@type='submit'][contains(normalize-space(.), 'Encerrar a outra sess')]",
}
CAMINHO_NOVO_PEDIDO = "/modulos/pesquisa-processos/novo-pedido"
# passo 2: "Documento da pesquisa" e, embaixo, o número (a barra de passos também tem
# "Documento da Pesquisa", mas seguido do "2" do próximo passo)
DOC_PASSO2 = re.compile(r"Documento da pesquisa\s*\n\s*(\d[\d./-]{10,}\d)", re.I)
PEDIDO_URL = re.compile(r"/pesquisa-processos/pedido/(\d+)")
SACADO_PADRAO = "RONEELY FEITOSA & SOCIEDADE DE ADVOGADOS"
REGISTRO = PASTA / "saida" / "pedidos_confirmados.json"  # empresa|CPF -> pedido (não comprar 2 vezes)
DIAS_REPETIDO = 30
PRECO = "R$ 15,70"  # valor por pesquisa visto no passo 2 em 04/11/2026 (o Albi lê o valor real lá)
EVENTOS = False  # --eventos: cada evento vira uma linha "@evento {json}" na saída padrão


class AlbiErro(Exception):
    pass


def configurar_log():
    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        handlers=[logging.StreamHandler(sys.stderr), logging.FileHandler(LOGS / "albi.log", encoding="utf-8")])


def seletor(texto):
    """css:<seletor> ou xpath:<expressão> -> (By, valor)."""
    tipo, _, valor = texto.partition(":")
    if tipo == "css":
        return By.CSS_SELECTOR, valor
    if tipo == "xpath":
        return By.XPATH, valor
    raise AlbiErro(f"seletor inválido (use css: ou xpath:): {texto}")


def carregar(caminho_env):
    if not Path(caminho_env).exists():
        raise AlbiErro(f"não achei {caminho_env}: copie o .env.example para .env e preencha")
    load_dotenv(caminho_env, override=True)
    faltando = [k for k in OBRIGATORIAS if not os.getenv(k, "").strip()]
    if faltando:
        raise AlbiErro(f"preencha no {caminho_env}: {', '.join(faltando)}")
    cpf = re.sub(r"\D", "", os.getenv("SONAR_CPF_CNPJ"))
    if len(cpf) not in (11, 14):
        raise AlbiErro("SONAR_CPF_CNPJ tem que ter 11 números (CPF) ou 14 (CNPJ)")
    return {
        "url": os.getenv("SONAR_URL").strip(), "cpf": cpf, "email": os.getenv("SONAR_EMAIL").strip(),
        "senha": os.getenv("SONAR_SENHA"),  # sem strip: espaço pode fazer parte da senha
        **{k.lower(): seletor(os.getenv(k, "").strip() or v) for k, v in PADROES.items()},
        "headless": os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "sim"),
        "timeout": int(os.getenv("TIMEOUT", "20").strip() or 20),
        "sacado": os.getenv("SONAR_SACADO", "").strip() or SACADO_PADRAO,
        # quanto tempo esperar o Sonar terminar os pedidos antes de desistir (minutos)
        "espera_min": int(os.getenv("SONAR_ESPERA_MIN", "120").strip() or 120),
    }


def pagina(driver):
    """Caminho da URL atual, sem barra no fim: /login, /login-conflito, /modulos/..."""
    return urlparse(driver.current_url).path.rstrip("/") or "/"


def enviar_login(driver, cfg, espera):
    """Preenche CPF/CNPJ, e-mail e senha e clica em Entrar."""
    for chave, valor in (("login_campo_cpf_cnpj", cfg["cpf"]), ("login_campo_email", cfg["email"]),
                         ("login_campo_senha", cfg["senha"])):
        campo = espera.until(EC.visibility_of_element_located(cfg[chave]))
        campo.clear()
        campo.send_keys(valor)
    espera.until(EC.element_to_be_clickable(cfg["login_botao"])).click()
    try:
        # sai da tela de login: entrou ou caiu na tela de conflito
        espera.until(lambda d: pagina(d) != "/login")
    except TimeoutException:
        # continua na tela de login: mostra a mensagem do Sonar (sem repetir os dados digitados)
        avisos = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, "#loginform .invalid-feedback, "
                  "#loginform .help-block, .alert") if e.text.strip()]
        raise AlbiErro("login não confirmado" + (": " + " | ".join(avisos) if avisos else
                                                   f" em {cfg['timeout']}s (confira CPF/CNPJ, e-mail e senha)"))


def entrar(driver, cfg):
    """Entra no Sonar. Se cair em /login-conflito (já tem sessão aberta em outro lugar), clica em
    "Encerrar a outra sessão" e, se voltar para a tela de login, entra de novo."""
    espera = WebDriverWait(driver, cfg["timeout"])
    driver.get(cfg["url"])
    enviar_login(driver, cfg, espera)
    if pagina(driver) == "/login-conflito":
        log.info("Tela de conflito: encerrando a outra sessão")
        espera.until(EC.element_to_be_clickable(cfg["conflito_botao"])).click()
        espera.until(lambda d: pagina(d) != "/login-conflito")
        if pagina(driver) == "/login":
            log.info("Voltou para a tela de login: entrando de novo")
            enviar_login(driver, cfg, espera)
    if pagina(driver).startswith("/login"):
        raise AlbiErro(f"login não confirmado: ficou em {driver.current_url}")


def abrir_novo_pedido(driver, cfg):
    """Vai direto para a tela de novo pedido da Pesquisa de Processos."""
    url = urljoin(cfg["url"], CAMINHO_NOVO_PEDIDO)
    driver.get(url)
    espera = WebDriverWait(driver, cfg["timeout"])
    try:
        espera.until(lambda d: d.execute_script("return document.readyState") == "complete"
                     and pagina(d) == CAMINHO_NOVO_PEDIDO)
    except TimeoutException:
        raise AlbiErro(f"não abriu a tela de novo pedido: ficou em {driver.current_url}")


# ---------------- .txt de pedidos ----------------
def documento_valido(numeros):
    """CPF (11) ou CNPJ (14) com os dígitos verificadores certos."""
    if len(numeros) not in (11, 14) or len(set(numeros)) == 1:
        return False
    d = [int(c) for c in numeros]
    if len(d) == 11:
        for n in (9, 10):
            dv = sum(d[i] * (n + 1 - i) for i in range(n)) * 10 % 11 % 10
            if dv != d[n]:
                return False
        return True
    for n, pesos in ((12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]), (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])):
        resto = sum(a * b for a, b in zip(d, pesos)) % 11
        if (0 if resto < 2 else 11 - resto) != d[n]:
            return False
    return True


def tipo_doc(numeros):
    return "CPF" if len(numeros) == 11 else "CNPJ"


def mascarar(numeros):
    """Só o tipo e os 2 últimos números (para log e eventos da vila)."""
    return f"{tipo_doc(numeros) if len(numeros) in (11, 14) else 'documento'} final {numeros[-2:]}"


EMPRESA = re.compile(r"\A\s*EMPRESA\s*:\s*(.*?)\s*\Z", re.I)
SO_DOCUMENTO = re.compile(r"\A[\d.\-/\s]+\Z")  # números com pontuação (sem letras)


def eh_separador(linha):
    return set(linha) <= set("-=_") and len(linha) >= 3


def ler_pedidos(texto):
    """Um pedido por linha, organizado por empresa:
        EMPRESA: Empresa A
        123.456.789-09 ; Maria da Silva
        ---
    Devolve [{"linha", "empresa", "grupo" (1, 2, ... na ordem do arquivo), "doc" (só números),
    "nome", "identificador", "problema"}]. O CPF/CNPJ pode vir antes ou depois do nome (a parte
    só com números é o documento). Sem nenhuma linha EMPRESA:, vale tudo como uma lista só.
    Linha vazia, com # no começo ou só com --- fica de fora."""
    pedidos, vistos, grupos = [], {}, {}
    empresa = ""
    for n, bruta in enumerate(texto.splitlines(), 1):
        linha = bruta.strip()
        if not linha or linha.startswith("#") or eh_separador(linha):
            continue
        m = EMPRESA.match(linha)
        if m:
            empresa = m.group(1).strip()
            continue
        partes = [x.strip() for x in linha.split(";")]
        docs = [x for x in partes if x and SO_DOCUMENTO.match(x)]
        texto_doc = docs[0] if docs else ""
        nome = " ; ".join(x for x in partes if x and x is not texto_doc)
        numeros = re.sub(r"\D", "", texto_doc)
        grupo = grupos.setdefault(empresa, len(grupos) + 1)
        p = {"linha": n, "empresa": empresa, "grupo": grupo, "doc": numeros, "nome": nome,
             "identificador": empresa, "problema": None}
        if not docs:
            p["doc"] = re.sub(r"\D", "", linha)
            p["problema"] = ('o CPF/CNPJ está misturado com letras (separe o nome com ";")' if p["doc"]
                             else "não achei o CPF/CNPJ na linha")
        elif len(numeros) not in (11, 14):
            p["problema"] = f"tem {len(numeros)} números (CPF tem 11 e CNPJ tem 14)"
        elif not documento_valido(numeros):
            p["problema"] = f"{tipo_doc(numeros)} inválido (dígito verificador não confere)"
        elif (normalizar(empresa), numeros) in vistos:
            p["problema"] = f"repetido nesta empresa (já está na linha {vistos[(normalizar(empresa), numeros)]})"
        else:
            vistos[(normalizar(empresa), numeros)] = n
        pedidos.append(p)
    return pedidos


def ler_arquivo(caminho):
    bruto = Path(caminho).read_bytes()
    try:
        return bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        return bruto.decode("cp1252")  # salvo pelo Bloco de Notas antigo


def evento(tipo, **dados):
    """Evento da vila (bot "albi"): só com --eventos. Nunca o documento inteiro nem o identificador."""
    if not EVENTOS:
        return
    try:
        print("@evento " + json.dumps({"tipo": tipo, "ts": datetime.now().isoformat(timespec="seconds"), **dados},
                                      ensure_ascii=False), flush=True)
    except (OSError, ValueError):
        pass  # quem leu os eventos (o Ultron) fechou: o Albi continua


def mensagem(e):
    """Primeira linha do erro, sem o stacktrace do Selenium."""
    texto = getattr(e, "msg", None) or str(e) or e.__class__.__name__
    return texto.strip().splitlines()[0][:200]


# ---------------- registro dos pedidos confirmados (não comprar 2 vezes) ----------------
def normalizar(texto):
    """Sem acento, maiúsculo e com um espaço só (para comparar nomes de empresa e do Sacado)."""
    t = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


def formatar(doc):
    if len(doc) == 11:
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    if len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc


def ler_registro():
    try:
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gravar_registro(reg):
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRO.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(REGISTRO)


def chave(p):
    return f"{normalizar(p['empresa'])}|{p['doc']}"


def ja_pesquisado(reg, p, agora=None):
    """Registro de um pedido desta empresa + CPF nos últimos 30 dias (ou None)."""
    r = reg.get(chave(p))
    if not r:
        return None
    try:
        quando = datetime.fromisoformat(r["quando"])
    except (KeyError, ValueError):
        return r
    return r if (agora or datetime.now()) - quando <= timedelta(days=DIAS_REPETIDO) else None


def conferir_arquivo(pedidos):
    """--conferir: o que seria feito, sem abrir o navegador (a página /albi mostra antes de comprar)."""
    reg = ler_registro()
    out = []
    for p in pedidos:
        j = None if p["problema"] else ja_pesquisado(reg, p)
        out.append({"linha": p["linha"], "empresa": p["empresa"], "nome": p["nome"], "doc": formatar(p["doc"]),
                    "problema": p["problema"], "ja": ({"pedido": j.get("pedido"), "quando": j.get("quando")} if j else None)})
    return {"pedidos": out, "preco": PRECO, "comprar": sum(1 for x in out if not x["problema"] and not x["ja"])}


# ---------------- passo 2: Sacado, confirmar e o número do pedido ----------------
def dropdown(driver, id_input):
    return driver.find_element(By.XPATH, f"//input[@id='{id_input}']/ancestor::div[contains(@class,'p-dropdown')][1]")


def escolher_sacado(driver, cfg):
    """Escolhe o Sacado (quem é cobrado) no passo 2. Sem ele o "Confirmar Pedido" fica desligado."""
    espera = WebDriverWait(driver, cfg["timeout"])
    dd = espera.until(lambda d: dropdown(d, "sacado"))
    alvo = normalizar(cfg["sacado"])
    if normalizar(dd.find_element(By.CSS_SELECTOR, ".p-dropdown-label").text) == alvo:
        return
    dd.find_element(By.CSS_SELECTOR, ".p-dropdown-trigger").click()
    itens = espera.until(lambda d: [e for e in d.find_elements(By.CSS_SELECTOR, ".p-dropdown-item") if e.is_displayed()] or False)
    item = next((e for e in itens if normalizar(e.text) == alvo), None)
    if not item:
        raise AlbiErro(f'o Sacado "{cfg["sacado"]}" não está na lista do Sonar (SONAR_SACADO no albi/.env)')
    item.click()
    espera.until(lambda d: normalizar(dropdown(d, "sacado").find_element(By.CSS_SELECTOR, ".p-dropdown-label").text) == alvo)


def botao_confirmar(driver):
    return next((b for b in driver.find_elements(By.TAG_NAME, "button")
                 if b.is_displayed() and b.text.strip() == "Confirmar Pedido"), None)


def numero_na_tela(driver):
    m = PEDIDO_URL.search(driver.current_url)
    if m:
        return m.group(1)
    m = re.search(r"\bPedido\s*(?:n[º°o.]*\s*)?S?(\d{6,})\b", driver.find_element(By.TAG_NAME, "body").text)
    return m.group(1) if m else None


def linhas_da_home(driver, cfg):
    """Linhas da tabela "Pedidos Recentes" da página inicial: [(número, projeto)] de todas as abas."""
    driver.get(urljoin(cfg["url"], "/"))
    espera = WebDriverWait(driver, cfg["timeout"] * 2)
    espera.until(lambda d: d.find_elements(By.CSS_SELECTOR, ".p-tabview-nav li"))

    def ler_tabela():
        try:
            espera.until(lambda d: d.find_elements(By.CSS_SELECTOR, "table tbody tr td"))
        except TimeoutException:
            return []
        time.sleep(1)
        out = []
        for tr in driver.find_elements(By.CSS_SELECTOR, "table tbody tr"):
            tds = tr.find_elements(By.TAG_NAME, "td")
            if len(tds) >= 3:
                m = re.search(r"S?(\d{6,})", tds[0].text)
                if m:
                    out.append((m.group(1), tds[2].text.strip()))
        return out

    vistas = ler_tabela()  # a aba aberta
    for i in range(len(driver.find_elements(By.CSS_SELECTOR, ".p-tabview-nav li"))):
        aba = driver.find_elements(By.CSS_SELECTOR, ".p-tabview-nav li")[i]
        classe = aba.get_attribute("class") or ""
        if "p-disabled" in classe or "p-tabview-selected" in classe or not aba.text.strip():
            continue
        try:
            aba.find_element(By.TAG_NAME, "a").click()
        except Exception:
            continue
        vistas += ler_tabela()
    return vistas


def confirmar_pedido(driver, cfg, empresa, conhecidos):
    """Clica em "Confirmar Pedido" (COMPRA a pesquisa) e devolve o número do pedido.
    Depois do clique nada aqui é repetido: se der erro, levanta Confirmado (talvez comprado)."""
    espera = WebDriverWait(driver, cfg["timeout"])
    botao = espera.until(lambda d: (lambda b: b if b is not None and b.is_enabled() else False)(botao_confirmar(d)))
    botao.click()
    try:
        # algum aviso de "deseja confirmar?" depois do clique: confirma nele
        time.sleep(1.5)
        for dlg in driver.find_elements(By.CSS_SELECTOR, ".p-dialog, .p-confirm-dialog, [role=dialog], [role=alertdialog]"):
            if not dlg.is_displayed():
                continue
            ok = [b for b in dlg.find_elements(By.TAG_NAME, "button") if b.is_displayed()
                  and normalizar(b.text) in ("CONFIRMAR", "CONFIRMAR PEDIDO", "SIM", "OK")]
            if ok:
                log.info("Aviso depois de confirmar: %s", dlg.text.strip()[:120].replace("\n", " "))
                ok[0].click()
        WebDriverWait(driver, max(60, cfg["timeout"] * 3)).until(
            lambda d: "step=carrinho" not in d.current_url or numero_na_tela(d) or botao_confirmar(d) is None)
        numero = numero_na_tela(driver)
        if not numero:
            # não apareceu na tela: procura na página inicial o pedido novo com o Projeto = empresa
            for _ in range(6):
                novos = [n for n, proj in linhas_da_home(driver, cfg)
                         if normalizar(proj) == normalizar(empresa) and n not in conhecidos]
                if novos:
                    numero = max(novos, key=int)
                    break
                time.sleep(5)
        if not numero:
            raise AlbiErro("confirmei, mas não achei o número do pedido")
        return numero
    except Exception as e:
        raise Confirmado(mensagem(e))


class Confirmado(Exception):
    """Erro depois de clicar em "Confirmar Pedido": o pedido pode ter sido comprado."""


# ---------------- resultado de cada pedido ----------------
def ler_pedido(driver, cfg, numero):
    """Página do pedido: {"status", "resultado", "concluido", "pode_baixar"}."""
    url = urljoin(cfg["url"], f"/modulos/pesquisa-processos/pedido/{numero}")
    for tentativa in (1, 2):
        driver.get(url)
        try:
            WebDriverWait(driver, cfg["timeout"] * 2).until(
                lambda d: re.search(rf"Pedido {numero}\s*\n(?:\s*Pedido {numero}\s*\n)?\s*\S", d.find_element(By.TAG_NAME, "body").text))
            break
        except TimeoutException:
            if tentativa == 2:
                raise AlbiErro(f"a página do pedido S{numero} não carregou")
    time.sleep(1)
    texto = driver.find_element(By.TAG_NAME, "body").text
    m = re.search(rf"Pedido {numero}\s*\n(?:\s*Pedido {numero}\s*\n)?\s*([^\n]+)\n", texto)
    status = m.group(1).strip() if m else ""
    res = re.search(r"\nResultado\s*\n\s*([^\n]+)", texto)
    fim = re.search(r"Data de Conclus[aã]o\s*\n\s*([^\n]+)", texto)
    baixar = [b for b in driver.find_elements(By.TAG_NAME, "button") if b.text.strip() == "Baixar Resultados"]
    st = normalizar(status)
    return {"status": status, "resultado": res.group(1).strip() if res else "",
            "concluido": bool(fim and re.search(r"\d", fim.group(1))) or "ENCONTRAD" in st or "NAO CONSTA" in st,
            "encontrados": "ENCONTRAD" in st and "NAO" not in st, "pode_baixar": bool(baixar and baixar[0].is_enabled())}


def baixar_resultado(driver, cfg, pasta_downloads, destino):
    """Clica em "Baixar Resultados" (na página do pedido aberta) e move a planilha para `destino`
    (sem extensão: fica a do arquivo baixado). Devolve o caminho final."""
    antes = set(os.listdir(pasta_downloads))
    botao = next(b for b in driver.find_elements(By.TAG_NAME, "button") if b.text.strip() == "Baixar Resultados")
    botao.click()
    fim = time.time() + max(60, cfg["timeout"] * 3)
    arquivo = None
    while time.time() < fim:
        novos = [f for f in set(os.listdir(pasta_downloads)) - antes if not f.endswith((".crdownload", ".tmp"))]
        if novos:
            arquivo = pasta_downloads / novos[0]
            tam = -1
            while arquivo.stat().st_size != tam:  # espera terminar de escrever
                tam = arquivo.stat().st_size
                time.sleep(1)
            break
        time.sleep(1)
    if not arquivo:
        raise AlbiErro("a planilha não baixou")
    final = destino.with_name(destino.name + (arquivo.suffix or ".xls"))
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(arquivo), str(final))
    return final


def salvar_pdf(driver, destino):
    """Salva a página do pedido aberta (o resultado no Sonar) em PDF: destino + ".pdf"."""
    dados = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True})
    final = destino.with_name(destino.name + ".pdf")
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(base64.b64decode(dados["data"]))
    return final


def nome_arquivo(texto):
    """Nome seguro para arquivo/pasta (mantém acentos; tira / \\ : * ? " < > |)."""
    return re.sub(r'[\\/:*?"<>|]+', "-", texto).strip(" .")[:80] or "sem nome"


def escrever_resultado(saida, pedidos, nome_txt):
    """resultado.txt: por empresa, uma linha por pessoa: CPF ; nome ; pedido ; resultado ; arquivos."""
    linhas = [f"# Resultado do Albi · {nome_txt} · {datetime.now():%d/%m/%Y %H:%M}",
              "# CPF ; nome ; pedido ; resultado ; arquivos (PDF do pedido + planilha, se tiver processos)", ""]
    empresa = None
    for p in pedidos:
        if p["empresa"] != empresa:
            if empresa is not None:
                linhas += ["---", ""]
            empresa = p["empresa"]
            linhas.append(f"EMPRESA: {empresa or '(sem empresa)'}")
        r = p.get("situacao") or ""
        partes = [formatar(p["doc"]), p["nome"] or "", f"S{p['pedido']}" if p.get("pedido") else "—", r,
                  " + ".join(p.get("arquivos") or [])]
        linhas.append(" ; ".join(partes).rstrip(" ;"))
    Path(saida).mkdir(parents=True, exist_ok=True)
    (Path(saida) / "resultado.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


# ---------------- Nova Pesquisa ----------------
def preencher_pedido(driver, cfg, doc, identificador=""):
    """Preenche o passo 1 (Identificador, Tipo CPF/CNPJ e o documento), clica em Continuar e
    confere o passo 2 ("Pedido"). Para ali: NÃO clica em "Confirmar Pedido".
    Devolve {"valor": "R$ 15,70", "itens": [...]} lido do resumo do pedido."""
    espera = WebDriverWait(driver, cfg["timeout"])
    abrir_novo_pedido(driver, cfg)
    if identificador:
        campo = espera.until(EC.visibility_of_element_located((By.ID, "acpDescricao")))
        campo.clear()
        campo.send_keys(identificador)
    # Tipo de Pesquisa: lista do PrimeReact (abre pela seta)
    tipo = espera.until(EC.visibility_of_element_located((By.XPATH, "//input[@id='tipoPesquisa']/ancestor::div[contains(@class,'p-dropdown')][1]")))
    tipo.find_element(By.CSS_SELECTOR, ".p-dropdown-trigger").click()
    item = espera.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class,'p-dropdown-item')][normalize-space(.)='CPF/CNPJ']")))
    item.click()
    espera.until(lambda d: tipo.find_element(By.CSS_SELECTOR, ".p-dropdown-label").text.strip() == "CPF/CNPJ")
    campo = espera.until(EC.visibility_of_element_located((By.ID, "cpfcnpj")))
    campo.clear()
    campo.send_keys(doc)
    if re.sub(r"\D", "", campo.get_attribute("value") or "") != doc:
        raise AlbiErro("o campo CPF/CNPJ não ficou com o documento digitado")
    driver.find_element(By.CSS_SELECTOR, "button[aria-label=Continuar]").click()
    try:
        espera.until(lambda d: "step=carrinho" in d.current_url)
    except TimeoutException:
        avisos = [e.text.strip() for e in driver.find_elements(By.CSS_SELECTOR, ".p-error, small, [class*=error]")
                  if e.is_displayed() and e.text.strip()]
        raise AlbiErro("o Sonar não passou para o passo 2" + (": " + " | ".join(dict.fromkeys(avisos)) if avisos else ""))
    # passo 2: confere o documento mostrado e lê o resumo (sem confirmar)
    texto = ""
    for _ in range(cfg["timeout"] * 2):
        texto = driver.find_element(By.TAG_NAME, "body").text
        if "TOTAL" in texto and DOC_PASSO2.search(texto):
            break
        time.sleep(0.5)
    m = DOC_PASSO2.search(texto)
    if not m:
        raise AlbiErro("não achei o documento no passo 2 (Pedido)")
    if re.sub(r"\D", "", m.group(1)) != doc:
        raise AlbiErro("o passo 2 mostra outro documento")
    resumo = texto[texto.upper().find("RESUMO DO PEDIDO"):]
    total = re.search(r"TOTAL\s*\n?\s*(R\$\s*[\d.,]+)", resumo)
    itens = re.findall(r"^(.+?)\s*\n?\s*(R\$\s*[\d.,]+)\s*$", resumo.split("TOTAL")[0], re.M)
    return {"valor": total.group(1).replace("\xa0", " ") if total else None,
            "itens": [f"{a.strip()} {b}" for a, b in itens if a.strip() and "RESUMO" not in a.upper()]}


def preencher_com_retentativa(driver, cfg, p):
    """Passo 1 e 2 (sem confirmar). Se a sessão cair ou der erro, entra de novo e tenta mais uma vez."""
    for tentativa in (1, 2):
        try:
            r = preencher_pedido(driver, cfg, p["doc"], p["identificador"])
            escolher_sacado(driver, cfg)
            return r
        except Exception as e:
            if tentativa == 2:
                raise
            if pagina(driver).startswith("/login"):
                log.warning("Linha %d: a sessão do Sonar caiu; entrando de novo", p["linha"])
                entrar(driver, cfg)
            else:
                log.warning("Linha %d: %s; tentando de novo", p["linha"], mensagem(e))


def print_erro(driver, p):
    print_ = LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}_linha{p['linha']}.png"
    try:
        driver.save_screenshot(str(print_))
    except Exception:
        pass
    return print_


def rodar_pedidos(driver, cfg, pedidos, confirmar=False, saida=None, nome_txt="pedidos.txt"):
    """Faz cada pessoa válida, uma por vez. Sem confirmar: só preenche até o passo 2 (teste).
    Confirmando: compra, guarda o número, espera os resultados e baixa as planilhas."""
    validos = [p for p in pedidos if not p["problema"]]
    if not confirmar:
        k = {"prontos": 0, "erros": 0, "invalidos": len(pedidos) - len(validos)}
    else:
        k = {"confirmados": 0, "ja_pesquisados": 0, "encontrados": 0, "nao_consta": 0, "pdfs": 0, "baixados": 0,
             "sem_resultado": 0, "conferir": 0, "erros": 0, "invalidos": len(pedidos) - len(validos)}
    for p in pedidos:
        p["situacao"] = "linha inválida: " + p["problema"] if p["problema"] else ""
        if p["problema"]:
            log.warning("Linha %d (%s): %s", p["linha"], mascarar(p["doc"]), p["problema"])
            evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), etapa="invalido",
                   motivo=p["problema"])
    escrever = (lambda: escrever_resultado(saida, pedidos, nome_txt)) if (confirmar and saida) else (lambda: None)
    escrever()
    evento("fase", fase="entrando_sonar")
    entrar(driver, cfg)
    log.info("Login OK: %s", driver.current_url)
    evento("fase", fase="confirmando" if confirmar else "preenchendo")
    reg = ler_registro() if confirmar else {}
    conhecidos = {r.get("pedido") for r in reg.values() if r.get("pedido")}
    seguidos = 0  # erros seguidos depois de clicar em Confirmar: 3 = para tudo (algo mudou no Sonar)
    for i, p in enumerate(validos, 1):
        doc = mascarar(p["doc"])
        ev = dict(linha=p["linha"], grupo=p["grupo"], doc=doc)
        if confirmar:
            j = ja_pesquisado(reg, p)
            if j:
                k["ja_pesquisados"] += 1
                p["pedido"] = j.get("pedido")
                p["situacao"] = "já pesquisado em " + j.get("quando", "")[:10] + (" (sem número: conferir no Sonar)" if not p["pedido"] else "")
                log.info("Linha %d (%s): já pesquisado para esta empresa (pedido %s): não compra de novo", p["linha"], doc, p["pedido"])
                evento("pedido", etapa="ja_pesquisado", pedido=p["pedido"], **ev)
                escrever()
                continue
        log.info("Pessoa %d de %d (linha %d, empresa %d, %s): preenchendo", i, len(validos), p["linha"], p["grupo"], doc)
        evento("pedido", etapa="preenchendo", i=i, de=len(validos), **ev)
        try:
            r = preencher_com_retentativa(driver, cfg, p)
        except Exception as e:
            k["erros"] += 1
            p["situacao"] = "erro (não comprado): " + mensagem(e)
            log.error("Linha %d (%s): %s (print em %s)", p["linha"], doc, mensagem(e), print_erro(driver, p))
            evento("pedido", etapa="erro", motivo=mensagem(e), **ev)
            escrever()
            continue
        if not confirmar:
            b = botao_confirmar(driver)
            if not (b and b.is_enabled()):
                k["erros"] += 1
                log.error("Linha %d (%s): escolhi o Sacado, mas o Confirmar Pedido não ligou", p["linha"], doc)
                evento("pedido", etapa="erro", motivo="escolhi o Sacado, mas o Confirmar Pedido não ligou", **ev)
                continue
            k["prontos"] += 1
            log.info("Linha %d (%s): pronto no passo 2 com o Sacado e o Confirmar liberado (NÃO cliquei) · %s",
                     p["linha"], doc, r["valor"] or "valor não lido")
            evento("pedido", etapa="pronto", valor=r["valor"], itens=len(r["itens"]), **ev)
            continue
        # daqui em diante compra: anota ANTES de clicar (se cair no meio, não compra de novo)
        reg[chave(p)] = {"pedido": None, "quando": datetime.now().isoformat(timespec="seconds"),
                         "empresa": p["empresa"], "nome": p["nome"]}
        gravar_registro(reg)
        try:
            numero = confirmar_pedido(driver, cfg, p["empresa"], conhecidos)
        except Confirmado as e:
            seguidos += 1
            k["conferir"] += 1
            p["situacao"] = "CONFERIR NO SONAR: cliquei em Confirmar e deu erro (" + str(e) + ")"
            log.error("Linha %d (%s): depois de confirmar: %s (print em %s)", p["linha"], doc, e, print_erro(driver, p))
            evento("pedido", etapa="conferir", motivo="pode ter sido comprado: " + str(e), **ev)
            escrever()
            if seguidos >= 3:
                raise AlbiErro("3 erros seguidos depois de confirmar: parei para não comprar errado (confira no Sonar)")
            continue
        except Exception as e:  # antes do clique (botão não ligou): nada foi comprado
            reg.pop(chave(p), None)
            gravar_registro(reg)
            k["erros"] += 1
            p["situacao"] = "erro (não comprado): " + mensagem(e)
            log.error("Linha %d (%s): %s (print em %s)", p["linha"], doc, mensagem(e), print_erro(driver, p))
            evento("pedido", etapa="erro", motivo=mensagem(e), **ev)
            escrever()
            continue
        seguidos = 0
        conhecidos.add(numero)
        reg[chave(p)]["pedido"] = numero
        gravar_registro(reg)
        k["confirmados"] += 1
        p["pedido"] = numero
        p["situacao"] = "confirmado, aguardando o Sonar"
        log.info("Linha %d (%s): CONFIRMADO · pedido S%s · %s", p["linha"], doc, numero, r["valor"] or PRECO)
        evento("pedido", etapa="confirmado", pedido=numero, valor=r["valor"], **ev)
        escrever()
    if confirmar:
        aguardar_e_baixar(driver, cfg, [p for p in validos if p.get("pedido")], saida, k, escrever)
    return k


def baixar_de_novo(driver, cfg, pedidos, saida, nome_txt):
    """--baixar: NÃO compra nada. Pega no registro o número do pedido de cada pessoa (desta empresa)
    e baixa de novo o resultado (PDF + planilha). Quem não tem pedido no registro fica de fora."""
    k = {"encontrados": 0, "nao_consta": 0, "pdfs": 0, "baixados": 0, "sem_resultado": 0, "sem_pedido": 0,
         "invalidos": sum(1 for p in pedidos if p["problema"])}
    reg = ler_registro()
    alvo = []
    for p in pedidos:
        ev = dict(linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]))
        if p["problema"]:
            p["situacao"] = "linha inválida: " + p["problema"]
            evento("pedido", etapa="invalido", motivo=p["problema"], **ev)
            continue
        r = reg.get(chave(p)) or {}
        p["pedido"] = r.get("pedido")
        if p["pedido"]:
            alvo.append(p)
            p["situacao"] = "baixando de novo"
        else:
            k["sem_pedido"] += 1
            p["situacao"] = "sem número de pedido no registro: " + ("conferir no Sonar" if r else "não foi comprado")
            evento("pedido", etapa="sem_pedido", motivo=p["situacao"], **ev)
    escrever = lambda: escrever_resultado(saida, pedidos, nome_txt)
    escrever()
    evento("fase", fase="entrando_sonar")
    entrar(driver, cfg)
    log.info("Login OK: %s · baixando de novo %d pedido(s) (nada é comprado)", driver.current_url, len(alvo))
    aguardar_e_baixar(driver, cfg, alvo, saida, k, escrever)
    return k


def aguardar_e_baixar(driver, cfg, pedidos, saida, k, escrever):
    """Espera cada pedido terminar no Sonar e baixa o resultado de cada um: o PDF da página do pedido
    (todos, inclusive "não consta") e a planilha ("Baixar Resultados") de quem tem processos encontrados."""
    if not pedidos:
        return
    evento("fase", fase="aguardando_resultados")
    downloads = Path(saida) / ".downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": str(downloads)})
    pendentes = list(pedidos)
    limite = time.time() + cfg["espera_min"] * 60
    while pendentes:
        for p in list(pendentes):
            ev = dict(linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), pedido=p["pedido"])
            try:
                info = ler_pedido(driver, cfg, p["pedido"])
            except Exception as e:
                if pagina(driver).startswith("/login"):
                    entrar(driver, cfg)
                log.warning("Pedido S%s: não consegui ler (%s); tento de novo depois", p["pedido"], mensagem(e))
                continue
            if not info["concluido"]:
                continue
            pendentes.remove(p)
            p["situacao"] = info["status"] + (" · " + info["resultado"] if info["resultado"] else "")
            p["arquivos"] = []
            destino = Path(saida) / nome_arquivo(p["empresa"] or "sem empresa") / nome_arquivo(f"S{p['pedido']} - {p['nome'] or formatar(p['doc'])}")
            try:
                p["arquivos"].append(str(salvar_pdf(driver, destino).relative_to(saida)))
                k["pdfs"] += 1
            except Exception as e:
                p["situacao"] += " · PDF não salvou: " + mensagem(e)
                log.error("Pedido S%s: o PDF não salvou: %s", p["pedido"], mensagem(e))
            if info["encontrados"]:
                k["encontrados"] += 1
                etapa = "encontrados"
                if info["pode_baixar"]:
                    try:
                        final = baixar_resultado(driver, cfg, downloads, destino)
                        p["planilha"] = str(final.relative_to(saida))
                        p["arquivos"].append(p["planilha"])
                        k["baixados"] += 1
                    except Exception as e:
                        p["situacao"] += " · planilha não baixou: " + mensagem(e)
                        log.error("Pedido S%s: a planilha não baixou: %s", p["pedido"], mensagem(e))
            else:
                k["nao_consta"] += 1
                etapa = "nao_consta"
            log.info("Pedido S%s (linha %d): %s%s", p["pedido"], p["linha"], p["situacao"],
                     " · " + " + ".join(p["arquivos"]) if p["arquivos"] else "")
            evento("pedido", etapa=etapa, resultado=info["resultado"], baixado=bool(p["arquivos"]), **ev)
            escrever()
        if not pendentes:
            break
        if time.time() > limite:
            for p in pendentes:
                k["sem_resultado"] += 1
                p["situacao"] = f"ainda sem resultado depois de {cfg['espera_min']} min: veja no Sonar (pedido S{p['pedido']})"
                evento("pedido", etapa="sem_resultado", linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), pedido=p["pedido"])
            escrever()
            break
        log.info("Aguardando o Sonar: %d pedido(s) ainda sem resultado", len(pendentes))
        time.sleep(60)
    try:
        downloads.rmdir()
    except OSError:
        pass


def tirar(args, nome, valor=False):
    """Tira a opção `nome` de args; com valor=True, devolve o valor dela (ou None)."""
    if nome not in args:
        return None if valor else False
    i = args.index(nome)
    if not valor:
        del args[i]
        return True
    v = args[i + 1] if i + 1 < len(args) else ""
    del args[i:i + 2]
    return v


def main(*args):
    global EVENTOS
    args = list(args)
    arquivo = tirar(args, "--arquivo", True)
    saida = tirar(args, "--saida", True)
    confirmar = tirar(args, "--confirmar")
    so_baixar = tirar(args, "--baixar")
    so_conferir = tirar(args, "--conferir")
    EVENTOS = tirar(args, "--eventos")
    caminho_env = args[0] if args else str(PASTA / ".env")
    if so_conferir:  # sem log na tela nem navegador: só o JSON (o Ultron lê)
        try:
            pedidos = ler_pedidos(ler_arquivo(arquivo))
        except (OSError, TypeError) as e:
            print(json.dumps({"erro": f"não consegui ler o arquivo: {e}"}, ensure_ascii=False))
            return 2
        print(json.dumps(conferir_arquivo(pedidos), ensure_ascii=False))
        return 0
    configurar_log()
    pedidos = None
    try:
        cfg = carregar(caminho_env)
        if arquivo is not None:
            if not arquivo or not Path(arquivo).exists():
                raise AlbiErro(f"não achei o arquivo de pedidos: {arquivo or '(vazio)'}")
            pedidos = ler_pedidos(ler_arquivo(arquivo))
            if not pedidos:
                raise AlbiErro("o arquivo não tem nenhuma linha com CPF/CNPJ")
        elif confirmar or so_baixar:
            raise AlbiErro("--confirmar e --baixar precisam de --arquivo")
        if confirmar and so_baixar:
            raise AlbiErro("use --confirmar ou --baixar, não os dois")
    except AlbiErro as e:
        log.error("Configuração: %s", e)
        evento("execucao_fim", resultado="parou", motivo=str(e))
        return 2
    if pedidos is not None:
        saida = Path(saida) if saida else PASTA / "saida" / f"{datetime.now():%Y-%m-%d_%H%M%S}"
        validos = sum(1 for p in pedidos if not p["problema"])
        empresas = len({p["grupo"] for p in pedidos})
        log.info("Arquivo %s: %d linha(s) em %d empresa(s), %d válida(s). %s", Path(arquivo).name, len(pedidos),
                 empresas, validos, f"CONFIRMANDO (compra, {PRECO} cada; Sacado: {cfg['sacado']}); resultado em {saida}"
                 if confirmar else f"Só baixando de novo os resultados (NÃO compra); resultado em {saida}" if so_baixar
                 else "Teste: preenche até o passo 2 e NÃO confirma nenhum pedido.")
        evento("execucao_iniciada", modo="confirmar" if confirmar else "baixar" if so_baixar else "preencher", total=len(pedidos),
               validos=validos, empresas=empresas)
        if not validos:
            for p in pedidos:
                evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), etapa="invalido",
                       motivo=p["problema"])
            evento("execucao_fim", resultado="parou", motivo="nenhuma linha com CPF/CNPJ válido",
                   contagens={"erros": 0, "invalidos": len(pedidos)})
            log.error("Nenhuma linha com CPF/CNPJ válido: nada a fazer")
            return 2
    log.info("Entrando no Sonar com CPF/CNPJ final %s e e-mail %s", cfg["cpf"][-2:], cfg["email"])
    opcoes = webdriver.ChromeOptions()
    if cfg["headless"]:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1600,1000")
    opcoes.add_experimental_option("prefs", {"download.prompt_for_download": False,
                                             "plugins.always_open_pdf_externally": True})
    try:
        driver = webdriver.Chrome(options=opcoes)
    except Exception as e:
        log.error("O navegador não abriu: %s", mensagem(e))
        evento("execucao_fim", resultado="parou", motivo="o navegador não abriu")
        return 1
    try:
        if pedidos is not None:
            if so_baixar:
                k = baixar_de_novo(driver, cfg, pedidos, saida, Path(arquivo).name)
            else:
                k = rodar_pedidos(driver, cfg, pedidos, confirmar=confirmar, saida=saida, nome_txt=Path(arquivo).name)
            log.info("Fim: %s", ", ".join(f"{v} {c}" for c, v in k.items() if v) or "nada")
            if confirmar or so_baixar:
                log.info("Resultado em %s", Path(saida) / "resultado.txt")
            evento("execucao_fim", resultado="concluido", contagens=k)
            return 0 if not (k.get("erros") or k.get("conferir")) else 1
        entrar(driver, cfg)
        log.info("Login OK: %s", driver.current_url)
        abrir_novo_pedido(driver, cfg)
        log.info("Tela de novo pedido aberta: %s", driver.current_url)
        return 0
    except Exception as e:
        print_ = LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
        try:
            driver.save_screenshot(str(print_))
        except Exception:
            pass
        log.error("Falhou: %s (print em %s)", mensagem(e), print_)
        evento("execucao_fim", resultado="parou", motivo=mensagem(e))
        if pedidos is not None and (confirmar or so_baixar):
            try:
                escrever_resultado(saida, pedidos, Path(arquivo).name)
            except Exception:
                pass
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
