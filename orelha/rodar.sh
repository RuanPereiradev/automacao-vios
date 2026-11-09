#!/usr/bin/env bash
# Roda o Orelha de qualquer pasta: usa a .venv e o .env de orelha/
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python main.py "$@"
