#!/usr/bin/env bash
# Prepara o projeto num computador novo (Mac ou Linux): cria a .venv e instala as dependências.
# uso: ./instalar.sh            (procura python3.12, depois python3)
#      PYTHON=/caminho/python3.12 ./instalar.sh
cd "$(dirname "$0")" || exit 1

# Python 3.9 a 3.12 (no 3.13 algumas versões fixadas no requirements.txt não têm pacote pronto)
PYTHON=${PYTHON:-$(command -v python3.12 || command -v python3)}
if [ -z "$PYTHON" ]; then
    echo "Python não encontrado. No Mac: brew install python@3.12 (ou o instalador do python.org)."
    exit 1
fi
VERSAO=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
case "$VERSAO" in
    3.8|3.9|3.10|3.11|3.12) ;;
    *) echo "Python $VERSAO em $PYTHON: use o 3.12 (brew install python@3.12) e rode de novo."; exit 1 ;;
esac
echo "Usando $PYTHON (Python $VERSAO)"

# .venv copiada de outro computador (ex.: do Linux) não funciona: recria
if [ -d .venv ] && ! .venv/bin/python -c 'import sys' 2>/dev/null; then
    echo "A .venv existente não funciona nesta máquina: recriando"
    rm -rf .venv
fi
[ -d .venv ] || "$PYTHON" -m venv .venv || exit 1
.venv/bin/python -m pip install --upgrade pip -q || exit 1
.venv/bin/python -m pip install -r requirements.txt || exit 1

chmod +x rodar*.sh
mkdir -p saida logs

if [ ! -f .env ]; then
    cp .env.example .env
    echo "AVISO: .env criado a partir do .env.example — copie o .env do computador antigo ou preencha."
fi
if [ "$(uname)" = "Darwin" ] && [ ! -d "/Applications/Google Chrome.app" ]; then
    echo "AVISO: Google Chrome não encontrado em /Applications. Instale o Chrome (o robô usa ele)."
fi
echo "Pronto. Teste com: ./rodar_envio.sh"
