#!/usr/bin/env bash
# Prepara o Jarvis num computador (Mac ou Linux): cria jarvis/.venv e instala as dependências.
# uso: ./instalar.sh   (procura python3.12, depois python3)   |   PYTHON=/caminho/python3 ./instalar.sh
cd "$(dirname "$0")" || exit 1
PYTHON=${PYTHON:-$(command -v python3.12 || command -v python3)}
[ -n "$PYTHON" ] || { echo "Python não encontrado. No Mac: brew install python@3.12"; exit 1; }
VERSAO=$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')
"$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 9))' || { echo "O Jarvis precisa de Python 3.9 ou mais novo (achei $VERSAO)"; exit 1; }
if [ -d .venv ]; then
    VENV_VERSAO=$(sed -n 's/^version[_info]* *= *\([0-9]*\.[0-9]*\).*/\1/p' .venv/pyvenv.cfg 2>/dev/null | head -n 1)
    if [ "$VENV_VERSAO" != "$VERSAO" ] || ! .venv/bin/python -c 'import sys' 2>/dev/null; then
        echo "A .venv existente não é deste computador/Python: recriando"; rm -rf .venv
    fi
fi
[ -d .venv ] || "$PYTHON" -m venv .venv || exit 1
.venv/bin/python -m pip install --upgrade pip -q || exit 1
.venv/bin/python -m pip install -r requirements.txt || exit 1
chmod +x rodar.sh
mkdir -p saida logs
[ -f .env ] || { cp .env.example .env; echo "AVISO: jarvis/.env criado do .env.example — preencha o usuário, a senha do VIOS e a chave da IA."; }
echo "Pronto. Teste com: ./rodar.sh --grupo \"NOME DO GRUPO\" --limite 2"
