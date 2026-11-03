"""Relatório de processos completo numa execução: captura no VIOS e PDF do cliente.

1. relatorio_processos.py: entra no VIOS e salva o <GRUPO>.txt e o <GRUPO>.json de cada grupo;
2. relatorio_cliente.py: gera o <GRUPO>.pdf de cada .json da pasta do dia mais recente.

É o que o rodar_usuario2.sh e o rodar_usuario2.bat chamam. Uso:
  python rodar_relatorio.py [.env.usuario2] [--grupo "3A FRIOS"|todos] [--sem-ficha] [--sem-grupo]
                            [--encerrados] [--ia] [--refazer]
--ia e --refazer vão só para o PDF; o resto vai só para a captura.
O PDF roda mesmo se a captura falhar em algum grupo (os grupos salvos viram PDF).
Sai com 0 se os dois passos deram certo e 1 se algum falhou (para o Agendador de Tarefas / cron).
"""
import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
ENV_PADRAO = ".env.usuario2"
SO_PDF = ("--ia", "--refazer")


def dividir(args):
    """(env, argumentos da captura, argumentos do PDF)."""
    args = list(args)
    env = ENV_PADRAO
    # o .env é o 1º argumento quando não é uma opção (o valor do --grupo vem sempre depois dele)
    if args and not args[0].startswith("-"):
        env = args.pop(0)
    captura = [a for a in args if a not in SO_PDF]
    pdf = [a for a in args if a in SO_PDF]
    return env, captura, pdf


def rodar(script, *args):
    """Roda um passo com o mesmo Python (o da .venv) e devolve o código de saída."""
    try:
        return subprocess.run([sys.executable, str(PASTA / script), *args], cwd=str(PASTA)).returncode
    except OSError as e:
        print(f"Não consegui rodar {script}: {e}", file=sys.stderr)
        return 1


def main(*args):
    env, captura, pdf = dividir(args)
    print("== 1/2 Captura no VIOS (relatorio_processos.py) ==", flush=True)
    codigo_captura = rodar("relatorio_processos.py", env, *captura)
    if codigo_captura:
        print("Captura terminou com falha: veja o log. Gerando o PDF dos grupos que foram salvos.",
              file=sys.stderr, flush=True)
    print("== 2/2 PDF do cliente (relatorio_cliente.py) ==", flush=True)
    codigo_pdf = rodar("relatorio_cliente.py", env, *pdf)
    if codigo_pdf:
        print("PDF terminou com falha: veja o log.", file=sys.stderr, flush=True)
    ok = codigo_captura == 0 and codigo_pdf == 0
    print("Concluído: tudo certo." if ok else
          f"Concluído com falha (captura: {codigo_captura}, PDF: {codigo_pdf}).", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
