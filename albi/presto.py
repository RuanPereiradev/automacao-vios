"""Albi — primeiro passo para baixar os autos pelo Presto (Oystr), sem precisar do DevTools.

O Presto guarda o login do escritório nos tribunais e entra nos portais pela extensão do Chrome.
O plano do escritório (Padrão) não tem a API de robôs da Oystr; então o bot vai usar a própria
extensão, num perfil do Chrome só dele. Este script prepara esse perfil e "fotografa" o que a
extensão mostra, para montar os passos do bot (entrar no PJe, buscar o processo, baixar os autos).

  .venv/bin/python presto.py copiar
      Copia o perfil do Chrome que você já usa (com o Presto instalado e logado) para o perfil do
      bot (albi/perfil_presto/). Mostra os perfis do Chrome para escolher. O Chrome precisa estar
      fechado (Cmd+Q) só durante a cópia. É o jeito de "usar o perfil que já está aberto": o Chrome
      não deixa automação no perfil principal nem dois Chromes no mesmo perfil, então o bot usa uma
      cópia. Se um dia o Presto sair da conta no bot, é só copiar de novo.

  .venv/bin/python presto.py preparar
      (alternativa ao copiar) Abre um Chrome NORMAL (sem automação) com o perfil do bot (albi/perfil_presto/). Nele:
      instale a extensão do Presto e entre na sua conta do Presto; depois tecle Enter no Terminal
      (o script fecha o Chrome salvando o perfil; no Mac, fechar a janela não encerra o Chrome).
      Só uma vez. Rode de dentro da pasta albi/.

  .venv/bin/python presto.py explorar [URL do tribunal ...]
      Abre o mesmo perfil pelo Selenium, acha a extensão do Presto, abre o pop-up dela numa aba
      (chrome-extension://<id>/<popup>) e salva print, HTML, texto e a lista de botões/campos/links.
      Com URLs (ex.: a tela de login do PJe do TRT7), abre cada uma, espera o Presto agir e salva o
      mesmo. Tudo vai para albi/logs/presto/<data_hora>/ (fora do git: pode ter nomes de clientes).

Nada aqui lê ou grava senha: o login fica dentro do Presto. A pasta perfil_presto/ tem a sessão
do Presto e fica fora do git.
"""
import json
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PERFIL = AQUI / "perfil_presto"
LOGS = AQUI / "logs" / "presto"
CONSOLE = "https://console.presto.oystr.com.br/"
QUAL = PERFIL / "perfil_bot.txt"  # nome da pasta do perfil copiado ("Default", "Profile 1"...)
# o que não precisa ir na cópia: caches (grandes e refeitos sozinhos) e as abas da última sessão
SEM_COPIAR = ("Cache", "Code Cache", "GPUCache", "DawnGraphiteCache", "DawnWebGPUCache", "GrShaderCache",
              "ShaderCache", "Sessions", "Current Session", "Current Tabs", "Last Session", "Last Tabs",
              "SingletonLock", "SingletonSocket", "SingletonCookie", "LOCK")


def chrome():
    """Caminho do Chrome instalado (Mac ou Linux)."""
    candidatos = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if platform.system() == "Darwin" else []
    candidatos += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise SystemExit("Não achei o Google Chrome instalado.")


def pasta_chrome():
    """Pasta de dados do Chrome do usuário (onde ficam os perfis)."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    return Path.home() / ".config" / "google-chrome"


def perfis_chrome(base=None):
    """[(pasta, nome, conta)] dos perfis do Chrome do usuário, pelo "Local State"."""
    base = base or pasta_chrome()
    try:
        cache = json.loads((base / "Local State").read_text(encoding="utf-8"))["profile"]["info_cache"]
    except (OSError, ValueError, KeyError):
        cache = {}
    out = [(d, i.get("name") or d, i.get("user_name") or "") for d, i in cache.items() if (base / d).is_dir()]
    return sorted(out, key=lambda t: (t[0] != "Default", t[0]))


def chrome_aberto():
    """True se o Chrome normal está aberto (no Mac, o app "Google Chrome")."""
    if platform.system() == "Darwin":
        r = subprocess.run(["pgrep", "-x", "Google Chrome"], capture_output=True)
    else:
        r = subprocess.run(["pgrep", "-x", "chrome"], capture_output=True)
    return r.returncode == 0


def args_perfil():
    """Argumentos do Chrome para abrir o perfil do bot (e a pasta do perfil copiado, se houver)."""
    a = [f"--user-data-dir={PERFIL}"]
    if QUAL.exists():
        a.append(f"--profile-directory={QUAL.read_text(encoding='utf-8').strip()}")
    return a


def copiar(base=None, escolha=None):
    base = base or pasta_chrome()
    perfis = perfis_chrome(base)
    if not perfis:
        raise SystemExit(f"Não achei perfis do Chrome em {base}.")
    print("Perfis do Chrome neste computador:")
    for i, (d, nome, conta) in enumerate(perfis, 1):
        print(f"  {i}. {nome}{' · ' + conta if conta else ''}  (pasta {d})")
    if escolha is None:
        escolha = input("Número do perfil que tem o Presto logado [1]: ").strip() or "1"
    try:
        d, nome, _ = perfis[int(escolha) - 1]
    except (ValueError, IndexError):
        raise SystemExit("Número inválido.")
    while base == pasta_chrome() and chrome_aberto():
        input("O Chrome está aberto. Feche-o (Cmd+Q no Mac; fechar a janela não basta) e tecle Enter... ")
    if PERFIL.exists():
        shutil.rmtree(PERFIL)
    PERFIL.mkdir()
    print(f"Copiando o perfil \"{nome}\" para {PERFIL} (sem os caches)...")
    shutil.copytree(base / d, PERFIL / d, ignore=shutil.ignore_patterns(*SEM_COPIAR), symlinks=True)
    if (base / "Local State").exists():
        shutil.copy2(base / "Local State", PERFIL / "Local State")
    QUAL.write_text(d, encoding="utf-8")
    print("Pronto: pode abrir o seu Chrome de novo.")
    ext = achar_extensao()
    print("Extensão do Presto encontrada no perfil do bot." if ext else
          "ATENÇÃO: não achei a extensão do Presto nesse perfil. Escolha outro perfil ou use 'preparar'.")
    return 0 if ext else 1


def preparar():
    PERFIL.mkdir(exist_ok=True)
    print(f"Abrindo o Chrome com o perfil do bot ({PERFIL}).\n"
          "  1. Instale a extensão do Presto (Chrome Web Store: procure \"Presto\" da Oystr);\n"
          "  2. entre na sua conta do Presto pela extensão;\n"
          "  3. confira que ela abre o PJe logado;\n"
          "  4. volte AQUI no Terminal e tecle Enter (não precisa fechar o Chrome nem usar Ctrl+C).")
    # os avisos internos do Chrome (GoogleUpdater, Crashpad...) não interessam: vão para o lixo
    proc = subprocess.Popen([chrome(), *args_perfil(), "--no-first-run", CONSOLE],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    try:
        input("\nQuando terminar, tecle Enter aqui... ")
    except (KeyboardInterrupt, EOFError):
        print()
    # no Mac, fechar a janela não encerra o Chrome; o terminate fecha salvando o perfil
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("Chrome do bot fechado.")
    ext = achar_extensao()
    print("Extensão do Presto encontrada no perfil." if ext else
          "ATENÇÃO: não achei a extensão do Presto no perfil. Rode 'preparar' de novo e instale.")


def _texto_msg(ext_dir, valor):
    """Nomes "__MSG_x__" do manifest -> texto do _locales (pt_BR, pt, en)."""
    m = re.fullmatch(r"__MSG_(\w+)__", valor or "")
    if not m:
        return valor or ""
    for loc in ("pt_BR", "pt", "en", "en_US"):
        arq = ext_dir / "_locales" / loc / "messages.json"
        if arq.exists():
            try:
                msgs = {k.lower(): v for k, v in json.loads(arq.read_text(encoding="utf-8")).items()}
                return msgs.get(m.group(1).lower(), {}).get("message", valor)
            except ValueError:
                pass
    return valor


def extensoes():
    """[(id, pasta da versão, manifest)] de todas as extensões instaladas no perfil do bot."""
    out = []
    for perfil in sorted(PERFIL.glob("*/Extensions")):
        for ext in sorted(perfil.iterdir()):
            versoes = sorted(p for p in ext.iterdir() if (p / "manifest.json").exists()) if ext.is_dir() else []
            if versoes:
                try:
                    man = json.loads((versoes[-1] / "manifest.json").read_text(encoding="utf-8-sig"))
                except ValueError:
                    continue
                out.append((ext.name, versoes[-1], man))
    return out


def achar_extensao():
    for eid, pasta, man in extensoes():
        tudo = " ".join([_texto_msg(pasta, man.get("name")), _texto_msg(pasta, man.get("description")),
                         str(man.get("homepage_url", "")), json.dumps(man.get("host_permissions", []))]).lower()
        if "presto" in tudo or "oystr" in tudo:
            return eid, pasta, man
    return None


def resumo_manifest(eid, pasta, man):
    acao = man.get("action") or man.get("browser_action") or {}
    return {
        "id": eid, "nome": _texto_msg(pasta, man.get("name")), "versao": man.get("version"),
        "popup": acao.get("default_popup"), "manifest_version": man.get("manifest_version"),
        "permissoes": man.get("permissions"), "sites": man.get("host_permissions"),
        "scripts_nas_paginas": [{"sites": c.get("matches"), "js": c.get("js")} for c in man.get("content_scripts", [])],
        "paginas_acessiveis": man.get("web_accessible_resources"),
        "fundo": man.get("background"),
    }


def _capturar(driver, pasta, nome):
    """Print, HTML, texto e a lista de elementos clicáveis/campos da aba atual."""
    from selenium.webdriver.common.by import By
    pasta.mkdir(parents=True, exist_ok=True)
    driver.save_screenshot(str(pasta / f"{nome}.png"))
    (pasta / f"{nome}.html").write_text(driver.page_source, encoding="utf-8")
    try:
        (pasta / f"{nome}.txt").write_text(driver.find_element(By.TAG_NAME, "body").text, encoding="utf-8")
    except Exception:
        pass
    itens = []
    for el in driver.find_elements(By.CSS_SELECTOR, "a, button, input, select, textarea, [role=button], [onclick], iframe"):
        try:
            itens.append({k: v for k, v in {
                "tag": el.tag_name, "texto": (el.text or "").strip()[:80], "id": el.get_attribute("id"),
                "name": el.get_attribute("name"), "type": el.get_attribute("type"),
                "class": (el.get_attribute("class") or "")[:80], "href": el.get_attribute("href"),
                "title": el.get_attribute("title"), "placeholder": el.get_attribute("placeholder"),
                "visivel": el.is_displayed()}.items() if v not in (None, "")})
        except Exception:
            continue
    (pasta / f"{nome}_elementos.json").write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {nome}: {driver.current_url} · {len(itens)} elementos · {pasta / (nome + '.png')}")


def explorar(urls):
    from selenium import webdriver
    if not PERFIL.exists():
        raise SystemExit("Rode primeiro: .venv/bin/python presto.py copiar")
    ext = achar_extensao()
    destino = LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=True)
    todas = [resumo_manifest(*e) for e in extensoes()]
    (destino / "extensoes.json").write_text(json.dumps(todas, ensure_ascii=False, indent=1), encoding="utf-8")
    if not ext:
        print("Não achei a extensão do Presto no perfil (lista em", destino / "extensoes.json", ")")
        return 1
    info = resumo_manifest(*ext)
    (destino / "presto_manifest.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Presto: id {info['id']}, versão {info['versao']}, pop-up {info['popup']}")
    opcoes = webdriver.ChromeOptions()
    for a in args_perfil():
        opcoes.add_argument(a)
    opcoes.add_argument("--window-size=1400,950")
    # o chromedriver liga essas opções por padrão; a extensão precisa estar ativa
    opcoes.add_experimental_option("excludeSwitches", ["disable-extensions", "disable-component-extensions-with-background-pages"])
    driver = webdriver.Chrome(options=opcoes)
    try:
        time.sleep(4)  # a extensão carrega e restaura a sessão do Presto
        if info["popup"]:
            driver.get(f"chrome-extension://{info['id']}/{info['popup'].lstrip('/')}")
            time.sleep(4)
            _capturar(driver, destino, "popup")
        for i, url in enumerate(urls, 1):
            driver.switch_to.new_window("tab")
            aba = driver.current_window_handle
            antes = set(driver.window_handles)
            driver.get(url)
            time.sleep(10)  # tempo para o Presto preencher/entrar
            _capturar(driver, destino, f"site{i}")
            for j, h in enumerate(h for h in driver.window_handles if h not in antes):  # o Presto pode abrir outra aba
                driver.switch_to.window(h)
                _capturar(driver, destino, f"site{i}_nova{j + 1}")
            driver.switch_to.window(aba)
        print("Capturas em", destino)
        input("Confira a janela do Chrome se quiser e tecle Enter para fechar... ") if sys.stdin.isatty() else None
    except Exception as e:
        from selenium.common.exceptions import WebDriverException
        if not isinstance(e, WebDriverException):
            raise
        print(f"O Chrome do bot fechou ou parou de responder no meio ({str(e).splitlines()[0]}).\n"
              f"O que foi capturado até aí está em {destino}. Se o Presto aparecer desativado no perfil "
              "copiado, use 'preparar' para instalar a extensão direto no perfil do bot.")
        return 1
    finally:
        driver.quit()
    return 0


def main(*args):
    if not args or args[0] not in ("copiar", "preparar", "explorar"):
        print(__doc__)
        return 2
    if args[0] == "copiar":
        return copiar()
    if args[0] == "preparar":
        preparar()
        return 0
    return explorar(list(args[1:]))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
