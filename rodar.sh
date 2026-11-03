#!/usr/bin/env bash
# Roda o bot de qualquer pasta: usa a .venv e o .env deste projeto
# ./rodar.sh (modo teste)  |  ./rodar.sh --confirmar (grava no VIOS)
cd "$(dirname "$(readlink -f "$0")")" || exit 1
exec .venv/bin/python main.py "$@"
