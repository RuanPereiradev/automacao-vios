#!/usr/bin/env bash
# Relatório de processos por Grupo Cliente com o segundo usuário do VIOS (.env.usuario2):
# captura no VIOS (.txt e .json) e PDF do cliente numa execução só (rodar_relatorio.py).
# Linux e Mac, de qualquer pasta: ./rodar_usuario2.sh   ou   ./rodar_usuario2.sh --grupo "PAO MIX"
# Opções da captura: --grupo, --sem-ficha, --sem-grupo, --encerrados. Do PDF: --ia, --refazer.
# Os arquivos ficam em saida_usuario2/relatorios/(data) ou na RELATORIO_PASTA do .env.usuario2.
# Sai com 0 se os dois passos deram certo e 1 se algum falhou (para o cron).

# vai para a pasta do script (sem readlink -f, que não existe no macOS)
script="$0"
while [ -L "$script" ]; do
  alvo="$(readlink "$script")"
  case "$alvo" in
    /*) script="$alvo" ;;
    *) script="$(dirname "$script")/$alvo" ;;
  esac
done
cd "$(dirname "$script")" || exit 1

if [ ! -x .venv/bin/python ]; then
  echo "Não achei .venv/bin/python. Crie a .venv: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi
exec .venv/bin/python rodar_relatorio.py .env.usuario2 "$@"
