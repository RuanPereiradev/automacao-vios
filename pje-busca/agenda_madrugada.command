#!/bin/bash
# Rodada agendada da madrugada (associados e monitor no PJe). O launchd abre este arquivo no Terminal
# (./servidor_mac.sh vigia instalar), porque o login pelo Presto precisa de clique e digitação de verdade e o
# Terminal já tem a permissão de Acessibilidade do macOS. Não dar essa permissão ao Python.
cd "$(dirname "$0")" || exit 1
mkdir -p logs
# liga a tela (se estiver apagada) e não deixa apagar nem dormir durante a rodada: com a tela bloqueada o quadro
# do Presto não aparece (25/11/2026). Isto não destrava a tela: o bloqueio automático precisa estar desligado.
/usr/bin/caffeinate -u -t 3
PYTHONUTF8=1 PYTHONUNBUFFERED=1 /usr/bin/caffeinate -dims ../.venv/bin/python vigia.py agenda madrugada >> logs/agenda.log 2>&1
echo "Rodada da madrugada terminou ($(date '+%d/%m/%Y %H:%M')). Resultado na aba Cumprimentos; log: ./servidor_mac.sh vigia log"
