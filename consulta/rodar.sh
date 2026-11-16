#!/usr/bin/env bash
# Roda o coletor de qualquer pasta, com a .venv da Orelha. uso: consulta/rodar.sh [--uma-vez] [--simulado]
cd "$(dirname "$0")/.." || exit 1
exec orelha/.venv/bin/python -m consulta "$@"
