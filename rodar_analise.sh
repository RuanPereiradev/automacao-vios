#!/usr/bin/env bash
# Analisa a última captura (ou o arquivo informado) com a IA: ./rodar_analise.sh [saida/intimacoes_X.json]
cd "$(dirname "$(readlink -f "$0")")" || exit 1
exec .venv/bin/python analisar.py "$@"
