#!/usr/bin/env bash
# Deixa o coletor da consulta de processo LIGADO no Mac (launchd), no mesmo Mac do bot e da Orelha.
# Diferente da Orelha (horário marcado), o coletor fica sempre rodando: busca pedidos no bot a cada
# CONSULTA_INTERVALO segundos. O launchd sobe ele no login e reinicia se cair.
# O Mac tem que ficar com o usuário logado (o Chrome precisa da sessão), como a Orelha.
# uso: consulta/servico_mac.sh instalar   (instala dependências, confere o .env e liga)
#      consulta/servico_mac.sh parar      (desliga e tira do login)
#      consulta/servico_mac.sh status     (mostra se está rodando e o último código de saída)
#      consulta/servico_mac.sh log        (acompanha o log; Ctrl+C sai)
cd "$(dirname "$0")/.." || exit 1
RAIZ=$(pwd)
DOMINIO="gui/$(id -u)"
ROTULO="br.automacao-vios.consulta"
PLIST="$HOME/Library/LaunchAgents/$ROTULO.plist"
LOG="$RAIZ/consulta/logs/launchd.log"
PY="$RAIZ/orelha/.venv/bin/python"

if [ "$(uname)" != "Darwin" ]; then
    echo "Este script é só para o Mac. No Linux, rode consulta/rodar.sh (ver consulta/README.md)."
    exit 1
fi

valor() { grep -E "^$1=" consulta/.env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e "s/^['\"]//" -e "s/['\"]$//"; }

case "${1:-}" in
    instalar)
        [ -x "$PY" ] || { echo "Falta a .venv da Orelha (orelha/.venv). Instale a Orelha primeiro: orelha/instalar.sh"; exit 1; }
        "$PY" -m pip install -q -r consulta/requirements.txt || { echo "Não consegui instalar consulta/requirements.txt"; exit 1; }
        [ -f consulta/.env ] || { echo "Falta consulta/.env (copie o coletor-consulta.env da pasta levar-para-o-mac)."; exit 1; }
        chmod 600 consulta/.env
        for v in CONSULTA_BOT_URL CONSULTA_SEGREDO CONSULTA_CHAVE_TELEFONE CONSULTA_CHAVE_PRIVADA SISTEMA_USUARIO SISTEMA_SENHA; do
            [ -n "$(valor $v)" ] || { echo "Falta $v em consulta/.env"; exit 1; }
        done
        CERT=$(valor CONSULTA_CERTIFICADO)
        case "$CERT" in *"<"*) echo "Troque <PASTA DO BOT NO MAC> em CONSULTA_CERTIFICADO (consulta/.env)"; exit 1;; esac
        [ -z "$CERT" ] || [ -f "$CERT" ] || { echo "CONSULTA_CERTIFICADO não existe: $CERT (rode antes o instalador do bot)"; exit 1; }
        CHAVE=$(valor CONSULTA_CHAVE_PRIVADA); case "$CHAVE" in /*) ;; *) CHAVE="$RAIZ/consulta/$CHAVE";; esac
        [ -f "$CHAVE" ] || { echo "Chave privada não encontrada: $CHAVE"; exit 1; }
        chmod 600 "$CHAVE"
        mkdir -p consulta/logs "$HOME/Library/LaunchAgents"
        cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$ROTULO</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$RAIZ/consulta/rodar.sh</string>
    </array>
    <key>WorkingDirectory</key><string>$RAIZ</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ThrottleInterval</key><integer>30</integer>
    <key>StandardOutPath</key><string>$LOG</string>
    <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF
        plutil -lint "$PLIST" >/dev/null || { echo "Arquivo do serviço inválido: $PLIST"; exit 1; }
        launchctl bootout "$DOMINIO/$ROTULO" 2>/dev/null
        for _ in 1 2 3 4 5 6 7 8 9 10; do launchctl print "$DOMINIO/$ROTULO" >/dev/null 2>&1 || break; sleep 1; done
        launchctl bootstrap "$DOMINIO" "$PLIST" || exit 1
        echo "Coletor ligado. Acompanhe: consulta/servico_mac.sh log"
        ;;
    parar)
        launchctl bootout "$DOMINIO/$ROTULO" 2>/dev/null; rm -f "$PLIST"; echo "Coletor desligado."
        ;;
    status)
        if launchctl print "$DOMINIO/$ROTULO" >/dev/null 2>&1; then
            echo "$ROTULO: instalado"
            launchctl print "$DOMINIO/$ROTULO" | grep -E "^[[:space:]]*(state|last exit code|runs|pid) =" | sed 's/^/  /'
        else
            echo "$ROTULO: não instalado (consulta/servico_mac.sh instalar)"
        fi
        ;;
    log)
        touch "$LOG"; tail -n 40 -f "$LOG"
        ;;
    *)
        sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1
        ;;
esac
