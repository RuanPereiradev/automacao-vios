#!/usr/bin/env bash
# Roda o Jarvis de qualquer pasta: usa a .venv e o .env de jarvis/
# ex.: ./rodar.sh --grupo "CASA DO CELULAR" --limite 2   (sem --grupo: PROCESSOS_GRUPOS do .env)
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python relatorio_processos.py .env "$@"
