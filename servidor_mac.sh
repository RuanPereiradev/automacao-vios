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

# Pasta do bot de WhatsApp (BOT_WHATSAPP_PASTA no .env), conferida antes de usar.
pasta_bot() {
    local p
    p=$(grep -E '^BOT_WHATSAPP_PASTA=' .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | sed "s#^~#$HOME#")
    if [ -z "$p" ]; then
        echo "Falta BOT_WHATSAPP_PASTA no .env (a pasta onde o bot-previdenciario foi clonado)." >&2
        return 1
    fi
    if [ ! -f "$p/scripts/mac/status.sh" ]; then
        echo "BOT_WHATSAPP_PASTA=$p não parece a pasta do bot (falta scripts/mac/status.sh)." >&2
        return 1
    fi
    echo "$p"
}

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
    whatsapp)
        # Bot de WhatsApp (repositório privado bot-previdenciario, clonado neste Mac). O código continua lá;
        # daqui só chamamos os scripts dele (scripts/mac/). Pasta em BOT_WHATSAPP_PASTA no .env.
        BOT=$(pasta_bot) || exit 1
        case "$2" in
            instalar|status|atualizar|desinstalar) bash "$BOT/scripts/mac/$2.sh" ;;
            log) tail -n 50 -f "$BOT/dados/logs/bot.log" ;;
            *) echo "uso: ./servidor_mac.sh whatsapp instalar | status | atualizar | log | desinstalar"; exit 1 ;;
        esac
        ;;
    coletor)
        bash consulta/servico_mac.sh "${2:-status}"
        ;;
    tudo)
        echo "== Página dos bots (envio, Vila, Orelha...)"
        "$0" status
        echo
        echo "== Coletor da consulta de processo"
        bash consulta/servico_mac.sh status
        echo
        echo "== Bot de WhatsApp"
        if BOT=$(pasta_bot); then bash "$BOT/scripts/mac/status.sh"; fi
        ;;
    atualizar-tudo)
        # Ordem obrigatória: o bot ANTES do coletor (o bot antigo recusa campo novo do coletor).
        BOT=$(pasta_bot) || exit 1
        echo "== 1/3 Bot de WhatsApp"
        bash "$BOT/scripts/mac/atualizar.sh" || { echo "Bot não atualizou; parei antes de mexer no resto."; exit 1; }
        echo "== 2/3 automacao-vios (git pull)"
        git pull --ff-only || { echo "git pull falhou; bot já atualizado, o resto ficou como estava."; exit 1; }
        echo "== 3/3 Reiniciando a página dos bots e o coletor"
        launchctl kickstart -k "$DOMINIO/$ROTULO" 2>/dev/null || echo "Página dos bots não instalada (./servidor_mac.sh instalar)."
        launchctl kickstart -k "$DOMINIO/br.automacao-vios.consulta" 2>/dev/null || echo "Coletor não instalado (./servidor_mac.sh coletor instalar)."
        echo "Pronto. Se o pull trouxe dependência nova: ./instalar.sh e ./servidor_mac.sh coletor instalar."
        echo "Conferir: ./servidor_mac.sh tudo"
        ;;
    *)
        echo "uso: ./servidor_mac.sh instalar | parar | status | log"
        echo "     ./servidor_mac.sh whatsapp instalar | status | atualizar | log | desinstalar"
        echo "     ./servidor_mac.sh coletor instalar | parar | status | log"
        echo "     ./servidor_mac.sh tudo            (status dos três serviços)"
        echo "     ./servidor_mac.sh atualizar-tudo  (bot primeiro, depois este repositório e o coletor)"
        exit 1
        ;;
esac
