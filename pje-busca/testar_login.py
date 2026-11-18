"""Teste manual do login no PJe do TRT7 pelo Presto (só Mac, com o Chrome e o Presto logados).

  cd pje-busca && python3 testar_login.py

Usa PRESTO_CREDENCIAL e PRESTO_PIN do pje-busca/.env. Não imprime o PIN.
As capturas (print, HTML e texto de cada tela) vão para logs/acesso/<data_hora>/.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "src"))

import acesso_pje as A  # noqa: E402


def main():
    cfg = A.config_presto()
    faltam = [k for k in ("PRESTO_PIN",) if not cfg.get(k)]
    if faltam:
        print("Falta no pje-busca/.env:", ", ".join(faltam), "(veja .env.example)")
        return 2
    print("Credencial do .env:", cfg.get("PRESTO_CREDENCIAL") or "(primeira da lista)")
    print("Abrindo o PJe do TRT7 pelo Presto no Chrome aberto. Deixe a janela do escritório na frente.")
    try:
        _, _, url = A.entrar_trt7(cfg)
    except A.AcessoErro as e:
        print("NÃO ENTROU:", e)
        print("Capturas em:", A.LOGS)
        return 1
    print("ENTROU:", url)
    print("Capturas em:", A.LOGS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
