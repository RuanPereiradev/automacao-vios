#!/usr/bin/env bash
# Deixa a página de envio rodando como servidor no Mac (launchd): liga sozinha quando o usuário
# entra no Mac, volta se cair e impede o Mac de dormir enquanto roda.
# uso: ./servidor_mac.sh instalar   (liga agora e em todo login)
#      ./servidor_mac.sh parar      (desliga e tira do login)
#      ./servidor_mac.sh status     (mostra se está rodando)
#      ./servidor_mac.sh log        (acompanha o log; Ctrl+C sai)
cd "$(dirname "$0")" || exit 1
PASTA=$(pwd)
ROTULO="br.automacao-vios.envio"
PLIST="$HOME/Library/LaunchAgents/$ROTULO.plist"
LOG="$PASTA/logs/servidor.log"
DOMINIO="gui/$(id -u)"

if [ "$(uname)" != "Darwin" ]; then
    echo "Este script é só para o Mac. No Linux: ./rodar_envio.sh"
    exit 1
fi

case "$1" in
    instalar)
        [ -x .venv/bin/python ] || { echo "Rode ./instalar.sh primeiro."; exit 1; }
        [ -f .env ] || { echo "Falta o .env nesta pasta."; exit 1; }
        if ! grep -qiE '^ENVIO_REDE=(true|1|sim)' .env || ! grep -qE '^ENVIO_SENHA=.+' .env; then
            echo "AVISO: para os outros computadores abrirem, o .env precisa de ENVIO_REDE=true e ENVIO_SENHA."
        fi
        [ -f saida/lancamentos.json ] || echo "AVISO: saida/lancamentos.json não existe — copie a saida/ do computador antigo antes de enviar (evita lançar em dobro)."
        mkdir -p logs "$HOME/Library/LaunchAgents"
        cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$ROTULO</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>$PASTA/rodar_envio.sh</string>
    </array>
    <key>WorkingDirectory</key><string>$PASTA</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUTF8</key><string>1</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ThrottleInterval</key><integer>10</integer>
    <key>StandardOutPath</key><string>$LOG</string>
    <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF
        # se já estava instalado, desliga e espera o launchd soltar o serviço (senão o bootstrap
        # falha com "5: Input/output error")
        launchctl bootout "$DOMINIO/$ROTULO" 2>/dev/null
        for _ in 1 2 3 4 5 6 7 8 9 10; do
            launchctl print "$DOMINIO/$ROTULO" >/dev/null 2>&1 || break
            sleep 1
        done
        plutil -lint "$PLIST" >/dev/null || { echo "Arquivo do serviço inválido: $PLIST"; exit 1; }
        if lsof -nP -iTCP:5001 -sTCP:LISTEN >/dev/null 2>&1; then
            echo "A porta 5001 está ocupada por outro programa (um ./rodar_envio.sh aberto?):"
            lsof -nP -iTCP:5001 -sTCP:LISTEN
            echo "Feche-o (Ctrl+C na janela dele ou kill <PID>) e rode de novo."
            exit 1
        fi
        launchctl bootstrap "$DOMINIO" "$PLIST" || exit 1
        sleep 3
        IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
        echo "Servidor ligado. Nos outros computadores: http://${IP:-<IP do Mac>}:5001"
        echo "Na primeira vez o macOS pergunta se o Python pode aceitar conexões: clique em Permitir."
        echo "Log: ./servidor_mac.sh log"
        ;;
    parar)
        launchctl bootout "$DOMINIO/$ROTULO" 2>/dev/null && echo "Servidor parado." || echo "O servidor não estava rodando."
        rm -f "$PLIST"
        ;;
    status)
        if launchctl print "$DOMINIO/$ROTULO" >/dev/null 2>&1; then
            launchctl print "$DOMINIO/$ROTULO" | grep -E "^[[:space:]]*(state|pid|last exit code) ="
        else
            echo "Servidor não instalado (./servidor_mac.sh instalar)."
        fi
        ;;
    log)
        tail -n 50 -f "$LOG"
        ;;
    *)
        echo "uso: ./servidor_mac.sh instalar | parar | status | log"
        exit 1
        ;;
esac
