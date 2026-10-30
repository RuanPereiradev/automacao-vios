#!/usr/bin/env bash
# Lança no VIOS as tarefas da análise: ./rodar_lancamento.sh --ci 42431 [--confirmar]
# sem --confirmar só preenche o formulário e tira print (modo teste)
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python lancar.py "$@"
