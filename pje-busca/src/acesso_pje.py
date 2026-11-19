"""Login no PJe do TRT7 pelo Presto, no Chrome que já está aberto no Mac (AppleScript).

Reaproveita o que já funciona no Albi (albi/presto.py, função login, e albi/chrome_mac.py, copiado
para src/chrome_mac.py). Não usa Selenium: o perfil copiado pede confirmação da conta Google
(ver o docstring de chrome_mac.py).

Fluxo: console do Presto (PRESTO_EMAIL/PRESTO_SENHA) > Sites > TRT 07 1g > login do TRT7 > clica em
"Login via Presto" (se houver) > espera o quadro do Presto >
escolhe a credencial (PRESTO_CREDENCIAL) > preenche o PIN (PRESTO_PIN) > espera sair da tela de login.

Se a página mostrar captcha, PARA e devolve "captcha": não tenta resolver (o captcha é pela pessoa,
na janela do Chrome). Nunca grava nem imprime o PIN.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

import chrome_mac as CM

AQUI = Path(__file__).resolve().parent.parent
LOGS = AQUI / "logs" / "acesso"
TRT7_LOGIN = "https://pje.trt7.jus.br/primeirograu/login.seam"
CONSOLE = "https://console.presto.oystr.com.br/"
SITE_TRT7 = "Pje TRT 07 1g"  # nome do TRT7 na página Sites do console do Presto
PADRAO_CAPTCHA = re.compile(r"captcha|recaptcha|não sou (um )?robô|nao sou (um )?robo", re.I)


class AcessoErro(Exception):
    pass


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


def _logado(w, t):
    """URL da aba se ela já saiu das telas de login; senão ""."""
    u = CM.url(w, t)
    return u if u.startswith("http") and not re.search(r"login\.seam|/auth/|sso\.|/login|authenticate", u, re.I) else ""


def _salvar(pasta, nome, cap):
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / f"{nome}.html").write_text(cap.get("html", ""), encoding="utf-8")
    (pasta / f"{nome}.txt").write_text(cap.get("texto", ""), encoding="utf-8")
    CM.print_tela(pasta / f"{nome}.png")


def _pede_pin(quadro):
    """O quadro do Presto mostra o campo do PIN? Devolve o quadro (ou None)."""
    if quadro and quadro.get("ok") and any(i.get("visivel") and i.get("type") == "password"
                                           for i in quadro.get("inputs", [])):
        return quadro
    return None


def _estado_console(w, t, maximo):
    """Espera o console do Presto mostrar o login ou a lista de sites (o site carrega aos poucos)."""
    ultimo = {}

    def pronto():
        ultimo.update(CM.console_estado(w, t))
        return ultimo.get("estado") in ("login", "sites")
    _esperar(pronto, maximo)
    return ultimo


def _entrar_console(w, t, cfg, destino):
    """Login do console do Presto com PRESTO_EMAIL/PRESTO_SENHA do .env. Aceita 1 tela (e-mail e senha) ou
    2 (e-mail, Continuar, senha). Se o JavaScript não pegar, digita com o teclado de verdade. Senha nunca impressa."""
    email, senha = cfg.get("PRESTO_EMAIL", ""), cfg.get("PRESTO_SENHA", "")
    if not (email and senha):
        raise AcessoErro("o console do Presto pediu login, mas PRESTO_EMAIL/PRESTO_SENHA não estão no pje-busca/.env")
    _salvar(destino, "0_console_login", CM.capturar(w, t))
    print("Console do Presto pediu login; entrando com o e-mail do .env...")
    for _ in range(3):  # no máximo: e-mail, senha e mais uma tentativa
        antes = CM.console_estado(w, t)
        r = CM.console_login(w, t, email, senha)
        if not r.get("ok"):
            raise AcessoErro("login do console: " + r.get("erro", "?"))
        _esperar(lambda: (lambda e: e.get("estado") == "sites" or e.get("estado") != "login"
                          or (e.get("senha") and not antes.get("senha")))(CM.console_estado(w, t)), 15, passo=1.5)
        agora = CM.console_estado(w, t)
        if agora.get("estado") != "login":
            return
        if agora.get("senha") and not antes.get("senha"):
            continue  # passou do e-mail para a senha
        break  # mesma tela: o JavaScript não pegou
    print("O preenchimento por JavaScript não entrou; digitando com o teclado de verdade...")
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
    if not agora.get("senha"):  # login em 2 etapas
        if _esperar(lambda: CM.console_estado(w, t).get("senha"), 15):
            onde = CM.console_onde(w, t, "senha")
            if onde.get("ok"):
                CM.clicar_tela(onde["x"], onde["y"])
                time.sleep(0.4)
                CM.digitar_tela(senha)
    if not _esperar(lambda: CM.console_estado(w, t).get("estado") != "login", 30, passo=2):
        _salvar(destino, "0_console_login_depois", CM.capturar(w, t))
        raise AcessoErro("o console do Presto continua na tela de login (senha errada, 2FA ou captcha?)")


def _abrir_pelo_console(cfg, destino):
    """Console do Presto > Sites > TRT 07 1g: é assim que a extensão entra no tribunal.
    Devolve (janela, aba) do TRT7, com o login do tribunal aberto."""
    sites = CONSOLE.rstrip("/") + "/sites"
    print("Abrindo o console do Presto (Sites)...")
    w, t = CM.abrir_aba(sites)
    CM.esperar(w, t, folga=3)
    estado = _estado_console(w, t, 25)
    if estado.get("estado") == "carregando":
        _salvar(destino, "0_console", CM.capturar(w, t))
        raise AcessoErro(f"o console do Presto não carregou em 25 s ({estado.get('url')})")
    if estado.get("estado") == "login":
        _entrar_console(w, t, cfg, destino)
        if "/sites" not in CM.url(w, t):
            CM.ir(w, t, sites)
            CM.esperar(w, t, folga=3)
        estado = _estado_console(w, t, 25)
        if estado.get("estado") != "sites":
            _salvar(destino, "0_console_depois_login", CM.capturar(w, t))
            raise AcessoErro(f"entrei no console, mas a lista de sites não apareceu ({estado.get('url')})")
    else:
        print("Console do Presto: já estava logado.")
    CM.console_site(w, t, SITE_TRT7)  # digita no filtro
    achou = _esperar(lambda: CM.console_site(w, t, SITE_TRT7).get("ok") and CM.console_site(w, t, SITE_TRT7), 20)
    _salvar(destino, "0_console_sites", CM.capturar(w, t))
    if not achou:
        r = CM.console_site(w, t, SITE_TRT7)
        raise AcessoErro(f"{r.get('erro')}; parecidos: {', '.join(r.get('parecidos', [])) or 'nenhum'}")
    antes = {(a[0], a[1]) for a in CM.todas_abas()}
    r = CM.console_site(w, t, SITE_TRT7, clicar=True)
    print(f"Console: cliquei em {r.get('nome')}")
    time.sleep(5)
    if "presto.oystr" in CM.url(w, t):
        # o console abriu o tribunal numa aba nova: só conta aba http fora do console
        novas = [a for a in CM.todas_abas() if (a[0], a[1]) not in antes and a[2].startswith("http")
                 and "presto.oystr" not in a[2] and a[0] < 2 ** 31 and a[1] < 2 ** 31]
        if novas:
            w, t = novas[-1][0], novas[-1][1]
        else:  # o clique não saiu do console: abre o login do TRT7 nesta aba
            link = r.get("link") or ""
            CM.ir(w, t, link if link.startswith("http") else TRT7_LOGIN)
    CM.esperar(w, t)
    return w, t


def entrar_trt7(cfg, destino=None):
    """Entra no PJe do TRT7 pelo Presto. Devolve (janela, aba, url_final).

    cfg: dicionário com PRESTO_CREDENCIAL (opcional, parte do nome) e PRESTO_PIN.
    Lança AcessoErro se não entrar (o motivo vem na mensagem; as capturas ficam em destino).
    """
    if not CM.disponivel():
        raise AcessoErro("o acesso ao PJe só funciona no Mac (AppleScript do Chrome)")
    if CM.acessibilidade_ok() is False:
        raise AcessoErro(CM.SEM_ACESSIBILIDADE)
    destino = destino or LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    w, t = _abrir_pelo_console(cfg, destino)
    CM.esperar(w, t)
    ja = _logado(w, t)
    if ja:
        return w, t, ja
    cap = CM.capturar(w, t)
    _salvar(destino, "1_login", cap)
    if PADRAO_CAPTCHA.search(cap.get("texto", "") or ""):
        raise AcessoErro("captcha na página de login: resolva na janela do Chrome e rode de novo")

    # TRT7 (PJe-JT): botão "Login via Presto" leva ao SSO, onde aparece o quadro do Presto.
    # O botão pode demorar a aparecer depois que a página carrega: espera até 20 s.
    def botao_ou_quadro():
        if CM.presto(w, t).get("ok"):
            return "quadro"
        if CM.botao_login_presto(w, t).get("ok"):
            return "botao"
        return ""
    tela = _esperar(botao_ou_quadro, 20, passo=1.0)
    print("Tela do TRT7:", tela or "sem botão \"Login via Presto\" nem quadro em 20 s")
    if tela == "botao":
        r = CM.botao_login_presto(w, t, clicar=True)
        print(f"Cliquei em \"{r.get('texto') or 'Login via Presto'}\"; indo para o SSO...")
        antes = CM.url(w, t)
        _esperar(lambda: CM.url(w, t) != antes, 20)
        CM.esperar(w, t)

    # o quadro aparece vazio e as credenciais chegam depois
    quadro = _esperar(lambda: (lambda q: q.get("ok") and q.get("creds") and q)(CM.presto(w, t)), 45, passo=1.5)
    if not quadro:
        ja = _logado(w, t)
        if ja:
            return w, t, ja
        raise AcessoErro("o quadro do Presto não apareceu em 45 s")

    termo = cfg.get("PRESTO_CREDENCIAL", "")
    r = CM.presto_credencial(w, t, termo)
    if not r.get("ok"):
        raise AcessoErro(f"não consegui escolher a credencial: {r.get('erro')}")

    quadro2 = _esperar(lambda: _pede_pin(CM.presto(w, t)), 8)
    if not quadro2:
        # a extensão pode ignorar clique feito por JavaScript: clica com o mouse de verdade
        CM.para_frente(w, t)
        onde = CM.presto_onde(w, t, "credencial", termo)
        if onde.get("ok"):
            CM.clicar_tela(onde["x"], onde["y"])
        quadro2 = _esperar(lambda: _pede_pin(CM.presto(w, t)), 10)
    if not _pede_pin(quadro2):
        raise AcessoErro("o Presto não mostrou o campo do PIN depois da credencial")

    pin = cfg.get("PRESTO_PIN", "")
    if not pin:
        raise AcessoErro("o Presto pediu o PIN, mas PRESTO_PIN não está no .env")
    r = CM.presto_pin(w, t, pin)
    if not r.get("ok"):
        raise AcessoErro(f"não consegui preencher o PIN: {r.get('erro')}")

    final = _esperar(lambda: _logado(w, t), 60, passo=2)
    CM.esperar(w, t, maximo=20, folga=2)
    _salvar(destino, "2_final", CM.capturar(w, t))
    if not final:
        raise AcessoErro("continua na tela de login depois de 60 s (veja as capturas em " + str(destino) + ")")
    return w, t, final


def config_presto(arquivo=AQUI / ".env"):
    """PRESTO_* do pje-busca/.env (sem python-dotenv); o ambiente tem preferência."""
    import os
    cfg = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(PRESTO_\w+)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    cfg.update({k: v for k, v in os.environ.items() if k.startswith("PRESTO_")})
    return cfg


if __name__ == "__main__":
    cfg = config_presto()
    try:
        _, _, url = entrar_trt7(cfg)
        print("Entrou:", url)
    except AcessoErro as e:
        print("Não entrou:", e)
        raise SystemExit(1)
