"""Albi — primeiro passo para baixar os autos pelo Presto (Oystr), sem precisar do DevTools.

O Presto guarda o login do escritório nos tribunais e entra nos portais pela extensão do Chrome.
O plano do escritório (Padrão) não tem a API de robôs da Oystr; então o bot vai usar a própria
extensão, num perfil do Chrome só dele. Este script prepara esse perfil e "fotografa" o que a
extensão mostra, para montar os passos do bot (entrar no PJe, buscar o processo, baixar os autos).

  .venv/bin/python presto.py preparar
      Abre um Chrome NORMAL (sem automação) com o perfil do bot (albi/perfil_presto/). Nele:
      instale a extensão do Presto, entre na sua conta do Presto e feche a janela. Só uma vez.

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


def chrome():
    """Caminho do Chrome instalado (Mac ou Linux)."""
    candidatos = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if platform.system() == "Darwin" else []
    candidatos += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]
    for c in candidatos:
        if c and Path(c).exists():
            return c
    raise SystemExit("Não achei o Google Chrome instalado.")


def preparar():
    PERFIL.mkdir(exist_ok=True)
    print(f"Abrindo o Chrome com o perfil do bot ({PERFIL}).\n"
          "  1. Instale a extensão do Presto (pelo console do Presto ou pela Chrome Web Store);\n"
          "  2. entre na sua conta do Presto pela extensão;\n"
          "  3. confira que ela abre o PJe logado;\n"
          "  4. feche a janela do Chrome.")
    subprocess.run([chrome(), f"--user-data-dir={PERFIL}", "--no-first-run", CONSOLE])
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
        raise SystemExit("Rode primeiro: .venv/bin/python presto.py preparar")
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
    opcoes.add_argument(f"--user-data-dir={PERFIL}")
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
    finally:
        driver.quit()
    return 0


def main(*args):
    if not args or args[0] not in ("preparar", "explorar"):
        print(__doc__)
        return 2
    if args[0] == "preparar":
        preparar()
        return 0
    return explorar(list(args[1:]))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
