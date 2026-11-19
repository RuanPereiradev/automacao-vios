"""Abre processos do TRT7 depois do login pelo Presto e salva o que a tela mostra (só Mac).

  cd pje-busca && python3 testar_processos.py 0001368-02.2026.5.07.0038 0002754-04.2025.5.07.0038

Faz o login (console do Presto > Sites > TRT7 > Login via Presto) e, na mesma aba, abre a tela de
detalhe de cada processo do TRT7 pelo número. Não baixa autos e não clica em nada além do login.
Salva print, HTML, texto e a lista de elementos de cada tela em logs/processos/<data_hora>/<número>/.
"""
import re
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "src"))

import acesso_pje as A  # noqa: E402
import chrome_mac as CM  # noqa: E402

DETALHE = "https://pje.trt7.jus.br/consultaprocessual/detalhe-processo/{numero}/1"
LOGS = AQUI / "logs" / "processos"


def so_digitos(v):
    return re.sub(r"\D", "", v or "")


def main(numeros):
    if not numeros:
        print("Passe os números: python3 testar_processos.py <número> [<número> ...]")
        return 2
    cfg = A.config_presto()
    if not cfg.get("PRESTO_PIN"):
        print("Falta PRESTO_PIN no pje-busca/.env")
        return 2
    pasta = LOGS / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    try:
        w, t, url = A.entrar_trt7(cfg, destino=pasta / "login")
    except A.AcessoErro as e:
        print("NÃO ENTROU:", e)
        return 1
    print("Login ok:", url)
    for numero in numeros:
        dig = so_digitos(numero)
        if len(dig) != 20:
            print(f"{numero}: número CNJ com {len(dig)} dígitos (esperado 20); pulei")
            continue
        destino = pasta / numero
        CM.ir(w, t, DETALHE.format(numero=dig))
        CM.esperar(w, t, maximo=45, folga=3)
        time.sleep(3)
        cap = CM.capturar(w, t)
        A._salvar(destino, "detalhe", cap)
        atual = CM.url(w, t)
        if not A._logado(w, t):
            print(f"{numero}: a tela mandou para o login ({atual}); veja {destino}")
            continue
        titulo = " ".join((cap.get("titulo") or "").split())[:100]
        print(f"{numero}: {titulo} · {len(cap.get('elementos', []))} elementos · {destino}")
    print("Capturas em:", pasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
