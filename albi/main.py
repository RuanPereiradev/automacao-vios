"""Albi — bot do Sonar (Leme Forense). Separado do Ultron e do Zangão: tem .venv, .env, logs/ e
saida/ próprios dentro de albi/ e não importa nada do bot/.

Entra no Sonar (encerrando a outra sessão se cair em /login-conflito) e, para cada CPF/CNPJ do
.txt, preenche Pesquisa de Processos > Nova Pesquisa até o passo 2 ("Pedido", com o valor).
NUNCA clica em "Confirmar Pedido": por enquanto ele só preenche.

.txt (modelo em modelo_pedidos.txt): um bloco por empresa e uma pessoa por linha, CPF/CNPJ e
nome separados por ";". O Identificador Projeto do Sonar fica "Empresa · Nome".
    EMPRESA: Empresa A
    123.456.789-09 ; Maria da Silva
    987.654.321-00 ; João Souza
    ---
    EMPRESA: Empresa B
    111.444.777-35 ; Ana Lima
Linha vazia, começando com # ou só com --- é ignorada. Sem EMPRESA:, vale tudo como uma lista só.

uso (dentro de albi/):
  ./rodar.sh                               só entra e abre a tela de novo pedido (confere o .env)
  ./rodar.sh --arquivo pedidos.txt         preenche um pedido por linha (sem confirmar)
  ./rodar.sh --arquivo pedidos.txt --eventos   idem, e escreve os eventos da vila na saída padrão
                                           (é assim que o Ultron roda o Albi pela página /albi)
  ./rodar.sh [caminho/do/.env] ...         outro .env
"""
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
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
             "identificador": " · ".join(x for x in (empresa, nome) if x), "problema": None}
        if not docs:
            p["doc"] = re.sub(r"\D", "", linha)
            p["problema"] = ('o CPF/CNPJ está misturado com letras (separe o nome com ";")' if p["doc"]
                             else "não achei o CPF/CNPJ na linha")
        elif len(numeros) not in (11, 14):
            p["problema"] = f"tem {len(numeros)} números (CPF tem 11 e CNPJ tem 14)"
        elif not documento_valido(numeros):
            p["problema"] = f"{tipo_doc(numeros)} inválido (dígito verificador não confere)"
        elif numeros in vistos:
            p["problema"] = f"repetido (já está na linha {vistos[numeros]})"
        else:
            vistos[numeros] = n
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


def rodar_pedidos(driver, cfg, pedidos):
    """Entra no Sonar e preenche cada pedido válido, um por vez. Se a sessão cair no meio (outra
    pessoa entrou com o mesmo login, ou o Sonar deslogou), entra de novo e tenta a linha mais uma
    vez; erro numa linha não para as outras. Devolve as contagens."""
    validos = [p for p in pedidos if not p["problema"]]
    k = {"prontos": 0, "erros": 0, "invalidos": len(pedidos) - len(validos)}
    for p in pedidos:
        if p["problema"]:
            log.warning("Linha %d (%s): %s", p["linha"], mascarar(p["doc"]), p["problema"])
            evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), etapa="invalido",
                   motivo=p["problema"])
    evento("fase", fase="entrando_sonar")
    entrar(driver, cfg)
    log.info("Login OK: %s", driver.current_url)
    evento("fase", fase="preenchendo")
    for i, p in enumerate(validos, 1):
        doc = mascarar(p["doc"])
        log.info("Pedido %d de %d (linha %d, empresa %d, %s): preenchendo", i, len(validos), p["linha"], p["grupo"], doc)
        evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=doc, etapa="preenchendo", i=i, de=len(validos))
        erro = None
        for tentativa in (1, 2):
            try:
                r = preencher_pedido(driver, cfg, p["doc"], p["identificador"])
                erro = None
                break
            except Exception as e:
                erro = e
                if tentativa == 2:
                    break
                try:
                    if pagina(driver).startswith("/login"):
                        log.warning("Linha %d: a sessão do Sonar caiu; entrando de novo", p["linha"])
                        entrar(driver, cfg)
                    else:
                        log.warning("Linha %d: %s; tentando de novo", p["linha"], mensagem(e))
                except Exception as e2:
                    erro = e2
                    break
        if erro is not None:
            k["erros"] += 1
            print_ = LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}_linha{p['linha']}.png"
            try:
                driver.save_screenshot(str(print_))
            except Exception:
                pass
            log.error("Linha %d (%s): %s (print em %s)", p["linha"], doc, mensagem(erro), print_)
            evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=doc, etapa="erro", motivo=mensagem(erro))
            continue
        k["prontos"] += 1
        log.info("Linha %d (%s): pronto no passo 2, sem confirmar · %s · resumo: %s", p["linha"], doc,
                 r["valor"] or "valor não lido", "; ".join(r["itens"]) or "—")
        evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=doc, etapa="pronto", valor=r["valor"],
               itens=len(r["itens"]))
    return k


def main(*args):
    global EVENTOS
    configurar_log()
    args = list(args)
    arquivo = None
    if "--arquivo" in args:
        i = args.index("--arquivo")
        arquivo = args[i + 1] if i + 1 < len(args) else ""
        del args[i:i + 2]
    EVENTOS = "--eventos" in args
    args = [a for a in args if a != "--eventos"]
    caminho_env = args[0] if args else str(PASTA / ".env")
    pedidos = None
    try:
        cfg = carregar(caminho_env)
        if arquivo is not None:
            if not arquivo or not Path(arquivo).exists():
                raise AlbiErro(f"não achei o arquivo de pedidos: {arquivo or '(vazio)'}")
            pedidos = ler_pedidos(ler_arquivo(arquivo))
            if not pedidos:
                raise AlbiErro("o arquivo não tem nenhuma linha com CPF/CNPJ")
    except AlbiErro as e:
        log.error("Configuração: %s", e)
        evento("execucao_fim", resultado="parou", motivo=str(e))
        return 2
    if pedidos is not None:
        validos = sum(1 for p in pedidos if not p["problema"])
        empresas = len({p["grupo"] for p in pedidos})
        log.info("Arquivo %s: %d linha(s) em %d empresa(s), %d válida(s). Só preenche: NÃO confirma nenhum pedido.",
                 Path(arquivo).name, len(pedidos), empresas, validos)
        evento("execucao_iniciada", modo="preencher", total=len(pedidos), validos=validos, empresas=empresas)
        if not validos:
            for p in pedidos:
                evento("pedido", linha=p["linha"], grupo=p["grupo"], doc=mascarar(p["doc"]), etapa="invalido",
                       motivo=p["problema"])
            evento("execucao_fim", resultado="parou", motivo="nenhuma linha com CPF/CNPJ válido",
                   contagens={"prontos": 0, "erros": 0, "invalidos": len(pedidos)})
            log.error("Nenhuma linha com CPF/CNPJ válido: nada a fazer")
            return 2
    log.info("Entrando no Sonar com CPF/CNPJ final %s e e-mail %s", cfg["cpf"][-2:], cfg["email"])
    opcoes = webdriver.ChromeOptions()
    if cfg["headless"]:
        opcoes.add_argument("--headless=new")
    opcoes.add_argument("--window-size=1600,1000")
    try:
        driver = webdriver.Chrome(options=opcoes)
    except Exception as e:
        log.error("O navegador não abriu: %s", mensagem(e))
        evento("execucao_fim", resultado="parou", motivo="o navegador não abriu")
        return 1
    try:
        if pedidos is not None:
            k = rodar_pedidos(driver, cfg, pedidos)
            log.info("Fim: %d pronto(s) no passo 2 (sem confirmar), %d com erro, %d linha(s) inválida(s)",
                     k["prontos"], k["erros"], k["invalidos"])
            evento("execucao_fim", resultado="concluido", contagens=k)
            return 0 if not k["erros"] else 1
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
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
