"""Albi — primeiro passo para baixar os autos pelo Presto (Oystr), sem precisar do DevTools.

O Presto guarda o login do escritório nos tribunais e entra nos portais pela extensão do Chrome.
O plano do escritório (Padrão) não tem a API de robôs da Oystr; então o bot vai usar a própria
extensão, num perfil do Chrome só dele. Este script prepara esse perfil e "fotografa" o que a
extensão mostra, para montar os passos do bot (entrar no PJe, buscar o processo, baixar os autos).

  .venv/bin/python presto.py entrar [tribunal ou URL] [--direto]  (Mac; o caminho atual)
      No Chrome já aberto, abre o console do Presto, entra nele (PRESTO_EMAIL/PRESTO_SENHA do
      albi/.env, se pedir), vai em Sites, procura o tribunal na lista e clica nele: é assim que a
      extensão faz o login (--direto pula o console e abre a URL do login). Depois, abre o login do tribunal (tjce1, tjce2, trt7, trt7-2, jfce, trf5,
      trf5-2 ou uma URL; padrão tjce1), espera o quadro "Credenciais Disponíveis" que o Presto põe
      na página, clica na credencial (PRESTO_CREDENCIAL no albi/.env, padrão a primeira) e, se o
      quadro pedir senha/PIN, preenche com PRESTO_PIN do albi/.env e confirma. Salva o que viu em
      cada etapa em albi/logs/presto/<data_hora>/ e diz se entrou. O PIN nunca é impresso nem salvo.

  .venv/bin/python presto.py liberar-chrome [--sim]               (Mac; uma vez)
      Liga no Chrome a opção "Permitir JavaScript de Apple Events" (que o bot precisa) sem procurar
      no menu: fecha o Chrome (pergunta antes; --sim não pergunta), marca a opção no arquivo
      Preferences de cada perfil (guarda uma cópia Preferences.albi-bak) e abre o Chrome de novo.

  .venv/bin/python presto.py processos [pasta do resultado] [--tribunal tjce1] [--max N] [--conferir]
      (Mac) Pega o processos.csv do último relatório do Albi (ou da pasta dada), vê pelo número de
      cada processo em qual tribunal ele está, entra em cada tribunal pelo Presto (como o "entrar")
      e procura cada processo na consulta do tribunal. Guarda o que viu de cada um e um resumo em
      <pasta do resultado>/presto/<data_hora>/. --conferir só mostra a divisão por tribunal (sem
      Chrome; roda em qualquer computador). Ainda não baixa os autos.

  .venv/bin/python presto.py aberto [URL ...]          (Mac; exploração)
      Usa o Chrome QUE JÁ ESTÁ ABERTO (perfil do escritório, Presto logado), pelo AppleScript
      (chrome_mac.py): abre cada URL numa aba nova da janela da frente, salva HTML, texto, a lista
      de botões/campos/links e um print da tela; procura um botão/link que mencione "Presto" (o
      "login via Presto" do tribunal), clica e captura de novo a aba e as abas que se abrirem.
      Sem URL: console do Presto e login do PJe do TRT7. Deixe a janela do perfil do escritório na
      frente. Uma vez: no Chrome, Visualizar > Desenvolvedor > "Permitir JavaScript de Apple
      Events"; no macOS, permitir o Terminal controlar o Google Chrome.

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
TRT7 = "https://pje.trt7.jus.br/primeirograu/login.seam"
# logins dos tribunais (da página Sites do console do Presto); "entrar" aceita a chave ou uma URL
TRIBUNAIS = {
    "tjce1": "https://pje.tjce.jus.br/pje1grau/login.seam",
    "tjce2": "https://pje.tjce.jus.br/pje2grau/login.seam",
    "trt7": "https://pje.trt7.jus.br/primeirograu/login.seam",
    "trt7-2": "https://pje.trt7.jus.br/segundograu/login.seam",
    "jfce": "https://pje.jfce.jus.br/pje/login.seam",
    "trf5": "https://pje1g.trf5.jus.br/pje/",
    "trf5-2": "https://pje2g.trf5.jus.br/pje/",
}

# nome de cada tribunal na página Sites do console do Presto (é por lá que a extensão entra)
SITES = {
    "tjce1": "TJCE 1º Grau - PJe",
    "tjce2": "TJCE 2º Grau - PJe",
    "trt7": "Pje TRT 07 1g",
    "trt7-2": "Pje TRT 07 2g",
    "jfce": "JFCE - PJe",
    "trf5": "TRF5 1º Grau - PJe",
    "trf5-2": "TRF5 2º Grau - PJe",
}


def config_presto():
    """PRESTO_* do albi/.env (sem python-dotenv); o ambiente tem preferência."""
    import os
    cfg = {}
    arq = AQUI / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(PRESTO_\w+)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("PRESTO_")})
    return cfg
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


def fechar_chrome():
    """Pergunta e fecha o Chrome normal do jeito certo (no Mac, como o menu Chrome > Sair; as abas voltam ao
    abrir de novo). True se ele fechou."""
    print("\nO seu Chrome está aberto, e o perfil só pode ser copiado com ele fechado (leva cerca de 1 minuto).\n"
          "No Mac, fechar a janela não fecha o Chrome: ele continua rodando no Dock.")
    try:
        r = input("Posso fechar o Chrome agora? As abas voltam quando você abrir de novo. [S/n] ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        return False
    if r not in ("", "s", "sim", "y"):
        return False
    if platform.system() == "Darwin":
        subprocess.run(["osascript", "-e", 'quit app "Google Chrome"'], capture_output=True)
    else:
        subprocess.run(["pkill", "-TERM", "-x", "chrome"], capture_output=True)
    for i in range(40):  # até 40 s para o Chrome terminar de fechar e salvar o perfil
        if i == 10 and platform.system() == "Darwin":
            # o "quit" pelo AppleScript depende de o macOS deixar o Terminal controlar o Chrome (a
            # permissão aparece numa janela na primeira vez); sem ela, pede o fechamento pelo sistema,
            # que também fecha o Chrome salvando o perfil
            subprocess.run(["pkill", "-TERM", "-x", "Google Chrome"], capture_output=True)
        if not chrome_aberto():
            time.sleep(2)  # folga para soltar os arquivos do perfil
            print("Chrome fechado.")
            return True
        time.sleep(1)
    print("O Chrome não fechou (pode haver uma janela perguntando algo, como \"Sair do Chrome?\"). Responda a ela.")
    return False


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
    if base == pasta_chrome() and chrome_aberto():
        if not fechar_chrome():
            raise SystemExit("O Chrome continua aberto; a cópia não foi feita. Feche o Chrome (menu Chrome > Sair) "
                             "e rode o 'copiar' de novo.")
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


def _salvar_captura(pasta, nome, cap):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.html").write_text(cap.get("html", ""), encoding="utf-8")
    (pasta / f"{nome}.txt").write_text(cap.get("texto", ""), encoding="utf-8")
    (pasta / f"{nome}_elementos.json").write_text(json.dumps(cap.get("elementos", []), ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    import chrome_mac as CM
    foto = CM.print_tela(pasta / f"{nome}.png")
    print(f"  {nome}: {cap.get('titulo', '')} · {cap.get('url', '')} · {len(cap.get('elementos', []))} elementos"
          + ("" if foto else " (sem print: permita \"Gravação de Tela\" para o Terminal)"))


def aberto(urls, termo="presto"):
    """Explora pelo Chrome já aberto no Mac (AppleScript): abre, captura, acha o botão do Presto, clica, captura."""
    import chrome_mac as CM
    if not CM.disponivel():
        print("O comando 'aberto' só funciona no Mac (usa o AppleScript do Chrome).")
        return 2
    destino = LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    print("Usando o Chrome já aberto (janela da frente). Deixe na frente a janela do perfil do escritório.")
    try:
        for i, u in enumerate(urls or [CONSOLE, TRT7], 1):
            w, t = CM.abrir_aba(u)
            CM.esperar(w, t)
            antes = {a[0] for a in CM.abas(w)}
            _salvar_captura(destino, f"site{i}", CM.capturar(w, t))
            r = CM.achar(w, t, termo)
            (destino / f"site{i}_achados_{termo}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                                                   encoding="utf-8")
            if not r["achados"]:
                print(f"  nenhum botão/link com \"{termo}\" visível nesta página")
                continue
            a = r["achados"][0]
            print(f"  achei: <{a['tag']}> \"{a.get('texto') or a.get('title') or a.get('alt') or a.get('id', '')}\" "
                  f"({len(r['achados'])} candidato(s)); clicando...")
            CM.achar(w, t, termo, clicar=True)
            time.sleep(10)  # o Presto age: preenche o login, abre o pop-up ou outra aba
            CM.esperar(w, t, maximo=30, folga=2)
            _salvar_captura(destino, f"site{i}_depois", CM.capturar(w, t))
            for j, (tid, tu, tt) in enumerate((a for a in CM.abas(w) if a[0] not in antes), 1):
                CM.esperar(w, tid, maximo=30, folga=2)
                _salvar_captura(destino, f"site{i}_nova{j}", CM.capturar(w, tid))
    except CM.ChromeMacErro as e:
        print("Parou:", e)
        return 1
    print("Capturas em", destino, "(as abas ficaram abertas no Chrome para você conferir)")
    return 0


def _esperar(cond, maximo, passo=1.0):
    """Repete cond() até dar algo verdadeiro (devolve) ou acabar o tempo (devolve o último valor)."""
    fim, v = time.monotonic() + maximo, None
    while time.monotonic() < fim:
        try:
            v = cond()
            if v:
                return v
        except Exception:
            pass
        time.sleep(passo)
    return v


def logado(w, t):
    """URL da aba se ela já saiu das telas de login (login.seam / sso / auth); senão ""."""
    import chrome_mac as CM
    u = CM.url(w, t)
    return u if u.startswith("http") and not re.search(r"login\.seam|/auth/|sso\.|/login", u) else ""


def _pede_pin(quadro):
    """O quadro do Presto está mostrando o campo do PIN? Devolve o quadro (ou None)."""
    if quadro and quadro.get("ok") and any(i.get("visivel") and i.get("type") == "password"
                                           for i in quadro.get("inputs", [])):
        return quadro
    return None


def _clique_real(CM, w, t, qual, termo=""):
    """Clique do mouse de verdade no link da credencial ou no campo do PIN do quadro. True se clicou."""
    if CM.acessibilidade_ok() is False:
        print("  " + CM.SEM_ACESSIBILIDADE)
        return False
    CM.para_frente(w, t)
    onde = CM.presto_onde(w, t, qual, termo)
    if not onde.get("ok"):
        print("  não achei onde clicar:", onde.get("erro"))
        return False
    CM.clicar_tela(onde["x"], onde["y"])
    time.sleep(0.5)
    return True


def login(w, t, cfg, destino, prefixo=""):
    """Na aba (já aberta no login do tribunal), entra pelo quadro do Presto: credencial + PIN do .env.
    Se a aba já estiver logada (sessão de antes), não faz nada. Devolve a URL final ("" = não entrou)."""
    import chrome_mac as CM
    CM.esperar(w, t)
    ja = logado(w, t)
    if ja:
        print("Já estava logado:", ja)
        return ja
    quadro = _esperar(lambda: CM.presto(w, t).get("ok") and CM.presto(w, t), 30)
    _salvar_captura(destino, f"{prefixo}1_login", CM.capturar(w, t))
    if not quadro:
        ja = logado(w, t)  # o tribunal pode ter levado direto para o painel
        if ja:
            print("Já estava logado:", ja)
            return ja
        print("O quadro do Presto não apareceu na página em 30 s. Confira se o Presto está ativo nessa "
              "janela e se a página é a de login do tribunal.")
        return ""
    (destino / f"{prefixo}1_quadro.json").write_text(json.dumps(quadro, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Quadro do Presto:", ", ".join(quadro["creds"]) or "(sem credenciais)")
    termo = cfg.get("PRESTO_CREDENCIAL", "")
    r = CM.presto_credencial(w, t, termo)
    if not r.get("ok"):
        print("Não consegui escolher a credencial:", r.get("erro"))
        return ""
    print("Credencial escolhida:", r["nome"])
    quadro2 = _esperar(lambda: _pede_pin(CM.presto(w, t)), 8)
    if not quadro2:
        # a extensão pode ignorar clique feito por JavaScript: clica com o mouse de verdade
        print("O clique por JavaScript não abriu o campo do PIN; clicando com o mouse no número...")
        _clique_real(CM, w, t, "credencial", termo)
        quadro2 = _esperar(lambda: _pede_pin(CM.presto(w, t)), 10)
    quadro2 = quadro2 or CM.presto(w, t)
    (destino / f"{prefixo}2_quadro_depois.json").write_text(json.dumps(quadro2, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    _salvar_captura(destino, f"{prefixo}2_depois_credencial", CM.capturar(w, t))
    if _pede_pin(quadro2):
        pin = cfg.get("PRESTO_PIN", "")
        if not pin:
            print("O Presto pediu a senha/PIN, mas PRESTO_PIN não está no albi/.env. Preencha e rode de novo.")
            return ""
        r = CM.presto_pin(w, t, pin)
        print("PIN preenchido; confirmei em:", r.get("botao") if r.get("ok") else r.get("erro"))
        if not _esperar(lambda: logado(w, t), 12, passo=2) and _pede_pin(CM.presto(w, t)):
            print("O PIN por JavaScript não entrou; digitando o PIN com o teclado de verdade...")
            if _clique_real(CM, w, t, "pin"):
                CM.digitar_tela(pin)
    elif quadro2.get("ok"):
        print("Depois da credencial o quadro continua sem campo de PIN:", quadro2.get("texto", "")[:200])
        print("Se o app onde o bot roda (Terminal ou Visual Studio Code) não está em Ajustes do Sistema > Privacidade e Segurança > Acessibilidade, "
              "ligue-o (o clique de verdade precisa disso) e rode de novo.")
    final = _esperar(lambda: logado(w, t), 60, passo=2)
    CM.esperar(w, t, maximo=20, folga=2)
    _salvar_captura(destino, f"{prefixo}3_final", CM.capturar(w, t))
    print(("Entrou: " + final) if final else "Continua na tela de login depois de 60 s (veja as capturas).")
    return final or ""


def _estado_console(CM, w, t, maximo):
    """Espera o console do Presto mostrar o login ou a lista de sites (o site carrega aos poucos)."""
    ultimo = {}

    def pronto():
        ultimo.update(CM.console_estado(w, t))
        return ultimo.get("estado") in ("login", "sites")
    _esperar(pronto, maximo)
    return ultimo


def _entrar_console(CM, w, t, cfg, destino):
    """Login do console do Presto com PRESTO_EMAIL/PRESTO_SENHA do albi/.env. Aceita login em 1 tela
    (e-mail + senha) ou em 2 (e-mail, Continuar, senha). Se o preenchimento por JavaScript não pegar,
    clica nos campos e digita com o teclado de verdade. A senha nunca é impressa nem salva."""
    email, senha = cfg.get("PRESTO_EMAIL", ""), cfg.get("PRESTO_SENHA", "")
    if not (email and senha):
        raise CM.ChromeMacErro("o console do Presto pediu login, mas PRESTO_EMAIL/PRESTO_SENHA não estão no albi/.env")
    _salvar_captura(destino, "0_console_login", CM.capturar(w, t))
    print("Console do Presto pediu login; entrando com o e-mail do albi/.env...")
    for _ in range(3):  # no máximo: e-mail, senha e mais uma tentativa
        antes = CM.console_estado(w, t)
        r = CM.console_login(w, t, email, senha)
        if not r.get("ok"):
            raise CM.ChromeMacErro("login do console: " + r.get("erro", "?"))
        print(f"  preenchi {r['etapa'].replace('+', ' e ')}; confirmei em {r.get('botao')}")
        # espera sair do login ou mudar de etapa (apareceu o campo de senha)
        _esperar(lambda: (lambda e: e.get("estado") == "sites" or e.get("estado") != "login"
                          or (e.get("senha") and not antes.get("senha")))(CM.console_estado(w, t)), 15, passo=1.5)
        agora = CM.console_estado(w, t)
        if agora.get("estado") != "login":
            return
        if agora.get("senha") and not antes.get("senha"):
            continue  # passou do e-mail para a senha: preenche de novo
        break  # mesma tela: o JavaScript não pegou
    print("  o preenchimento por JavaScript não entrou; digitando com o teclado de verdade...")
    CM.para_frente(w, t)
    agora = CM.console_estado(w, t)
    for qual, texto in (("email", email), ("senha", senha)):
        if (qual == "email" and not agora.get("email")) or (qual == "senha" and not agora.get("senha")):
            continue
        onde = CM.console_onde(w, t, qual)
        if onde.get("ok"):
            CM.clicar_tela(onde["x"], onde["y"])
            time.sleep(0.4)
            CM.digitar_tela(texto, enter=(qual == "senha" or not agora.get("senha")))
            time.sleep(1)
    if not agora.get("senha"):  # login em 2 etapas: depois do e-mail vem a senha
        if _esperar(lambda: CM.console_estado(w, t).get("senha"), 15):
            onde = CM.console_onde(w, t, "senha")
            if onde.get("ok"):
                CM.clicar_tela(onde["x"], onde["y"])
                time.sleep(0.4)
                CM.digitar_tela(senha)
    if not _esperar(lambda: CM.console_estado(w, t).get("estado") != "login", 30, passo=2):
        _salvar_captura(destino, "0_console_login_depois", CM.capturar(w, t))
        raise CM.ChromeMacErro("o console do Presto continua na tela de login (senha errada, código de 2 fatores "
                               "ou captcha?). Veja o print 0_console_login_depois nas capturas")


def abrir_tribunal(cfg, chave, destino, direto=False):
    """Abre o login do tribunal do jeito que o Presto age: console do Presto > Sites > clique no site.
    Entra no console com PRESTO_EMAIL/PRESTO_SENHA se ele pedir. Devolve (janela, aba) do tribunal.
    direto=True (ou tribunal sem nome em SITES) abre a URL do login direto, como antes."""
    import chrome_mac as CM
    if direto or chave not in SITES:
        w, t = CM.abrir_aba(TRIBUNAIS[chave])
        return w, t
    sites = CONSOLE.rstrip("/") + "/sites"
    print(f"Abrindo o console do Presto (Sites) para entrar em {SITES[chave]}...")
    w, t = CM.abrir_aba(sites)
    CM.esperar(w, t, folga=3)
    estado = _estado_console(CM, w, t, 25)
    if estado.get("estado") == "carregando":
        _salvar_captura(destino, "0_console", CM.capturar(w, t))
        raise CM.ChromeMacErro(f"o console do Presto não mostrou nem o login nem a lista de sites em 25 s ({estado.get('url')})")
    if estado["estado"] == "login":
        _entrar_console(CM, w, t, cfg, destino)
        if "/sites" not in CM.url(w, t):
            CM.ir(w, t, sites)
            CM.esperar(w, t, folga=3)
        estado = _estado_console(CM, w, t, 25)
        if estado.get("estado") != "sites":
            _salvar_captura(destino, "0_console_depois_login", CM.capturar(w, t))
            raise CM.ChromeMacErro(f"entrei no console, mas a lista de sites não apareceu ({estado.get('url')})")
    else:
        print("Console do Presto: já estava logado.")
    CM.console_site(w, t, SITES[chave])  # digita no filtro
    achou = _esperar(lambda: CM.console_site(w, t, SITES[chave]).get("ok") and CM.console_site(w, t, SITES[chave]), 20)
    _salvar_captura(destino, "0_console_sites", CM.capturar(w, t))
    if not achou:
        r = CM.console_site(w, t, SITES[chave])
        raise CM.ChromeMacErro(f"{r.get('erro')}; parecidos: {', '.join(r.get('parecidos', [])) or 'nenhum'}")
    antes = {(a[0], a[1]) for a in CM.todas_abas()}
    r = CM.console_site(w, t, SITES[chave], clicar=True)
    print(f"Console: cliquei em {r['nome']} ({r.get('link') or r.get('dominio')})")
    time.sleep(5)
    novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes]
    if novas:  # o console abriu o tribunal numa aba nova (nesta janela ou numa janela nova)
        w, t = novas[-1][0], novas[-1][1]
        print("O tribunal abriu numa aba nova:", novas[-1][2][:90])
    elif "presto.oystr" in CM.url(w, t):  # o clique não saiu do console: abre o login nesta aba
        print("O clique não abriu o tribunal; abrindo o login do tribunal nesta aba.")
        CM.ir(w, t, r.get("link") if (r.get("link") or "").startswith("http") else TRIBUNAIS[chave])
    CM.esperar(w, t)
    return w, t


def entrar(alvo="tjce1", direto=False):
    """Entra no tribunal pelo Presto no Chrome aberto (Mac): credencial do quadro + PIN do .env."""
    import chrome_mac as CM
    if not CM.disponivel():
        print("O comando 'entrar' só funciona no Mac (usa o AppleScript do Chrome).")
        return 2
    cfg = config_presto()
    url = TRIBUNAIS.get(alvo.lower(), alvo)
    if not url.startswith("http"):
        print(f"Tribunal desconhecido: {alvo}. Use {', '.join(TRIBUNAIS)} ou uma URL.")
        return 2
    destino = LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    if CM.acessibilidade_ok() is False:
        print("Atenção: " + CM.SEM_ACESSIBILIDADE + " Sem isso o bot não consegue clicar no número da credencial.")
    try:
        if alvo.lower() in TRIBUNAIS:
            w, t = abrir_tribunal(cfg, alvo.lower(), destino, direto)
        else:
            print(f"Abrindo {url} no Chrome aberto...")
            w, t = CM.abrir_aba(url)
        final = login(w, t, cfg, destino)
    except CM.ChromeMacErro as e:
        print("Parou:", e)
        return 1
    print("Capturas em", destino)
    return 0 if final else 1


def main(*args):
    if args and args[0] == "processos":
        import presto_processos
        return presto_processos.main(*args[1:])
    if args and args[0] == "liberar-chrome":
        import chrome_mac
        return chrome_mac.liberar(perguntar="--sim" not in args)
    if args and args[0] == "entrar":
        resto = [a for a in args[1:] if a != "--direto"]
        return entrar(*(resto[:1] or ["tjce1"]), direto="--direto" in args)
    if not args or args[0] not in ("aberto", "copiar", "preparar", "explorar"):
        print(__doc__)
        return 2
    if args[0] == "aberto":
        return aberto(list(args[1:]))
    if args[0] == "copiar":
        return copiar()
    if args[0] == "preparar":
        preparar()
        return 0
    return explorar(list(args[1:]))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
