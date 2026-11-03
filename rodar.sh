#!/usr/bin/env bash
# Roda o bot de qualquer pasta: usa a .venv e o .env deste projeto
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python main.py "$@"
