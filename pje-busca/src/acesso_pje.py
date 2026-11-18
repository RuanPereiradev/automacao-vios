"""Login no PJe do TRT7 pelo Presto, no Chrome que já está aberto no Mac (AppleScript).

Reaproveita o que já funciona no Albi (albi/presto.py, função login, e albi/chrome_mac.py, copiado
para src/chrome_mac.py). Não usa Selenium: o perfil copiado pede confirmação da conta Google
(ver o docstring de chrome_mac.py).

Fluxo: abre o login do TRT7 > clica em "Login via Presto" (se houver) > espera o quadro do Presto >
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
    w, t = CM.abrir_aba(TRT7_LOGIN)
    CM.esperar(w, t)
    ja = _logado(w, t)
    if ja:
        return w, t, ja
    cap = CM.capturar(w, t)
    _salvar(destino, "1_login", cap)
    if PADRAO_CAPTCHA.search(cap.get("texto", "") or ""):
        raise AcessoErro("captcha na página de login: resolva na janela do Chrome e rode de novo")

    # TRT7 (PJe-JT): botão "Login via Presto" leva ao SSO, onde aparece o quadro do Presto
    if not CM.presto(w, t).get("ok") and CM.botao_login_presto(w, t).get("ok"):
        CM.botao_login_presto(w, t, clicar=True)
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
