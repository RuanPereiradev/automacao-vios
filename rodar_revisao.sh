#!/usr/bin/env bash
# Abre a página de revisão (http://127.0.0.1:5000), importando as análises informadas:
# ./rodar_revisao.sh [saida/analise_X.json ...] [--porta 5000]
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python revisar.py "$@"
