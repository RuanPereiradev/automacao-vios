#!/usr/bin/env bash
# Roda o Albi de qualquer pasta: usa a .venv e o .env de albi/
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python main.py "$@"
