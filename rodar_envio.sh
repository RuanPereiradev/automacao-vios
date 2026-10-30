#!/usr/bin/env bash
# Página para subir o .txt com as tarefas já ajustadas e lançar no VIOS: ./rodar_envio.sh
# abre em http://127.0.0.1:5001
cd "$(dirname "$(readlink -f "$0")")" || exit 1
exec .venv/bin/python enviar.py "$@"
