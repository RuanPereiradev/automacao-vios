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

# Rodadas agendadas do vigia do pje-busca (alerta só na aba Cumprimentos): seg a sex,
# manhã 7h40 = vigia.py vios + djen + monitor; madrugada 3h20 = vigia.py associados + monitor-tribunal (PJe pelo
# Loy Trust, Chrome do Mac). O monitor sem carteira importada (vigia.py monitor-importar) não faz nada.
# Se o Mac estiver dormindo na hora, o launchd roda quando ele acordar.
VIGIA_ETAPAS="manha madrugada"
vigia_hora() { case "$1" in manha) echo "7 40" ;; madrugada) echo "3 20" ;; esac; }

vigia_plist() {
    local etapa=$1 rotulo="br.automacao-vios.vigia-$1" h m dias="" programa
    read -r h m <<< "$(vigia_hora "$etapa")"
    if [ "$etapa" = madrugada ]; then
        # login no PJe pelo Presto = clique e digitação de verdade (Acessibilidade): roda dentro do Terminal, que já
        # tem essa permissão, em vez de dar a permissão ao Python
        programa="        <string>/usr/bin/open</string>
        <string>-g</string>
        <string>-a</string>
        <string>Terminal</string>
        <string>$PASTA/pje-busca/agenda_madrugada.command</string>"
    else
        programa="        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>$PASTA/.venv/bin/python</string>
        <string>$PASTA/pje-busca/vigia.py</string>
        <string>agenda</string>
        <string>$etapa</string>"
    fi
    for d in 1 2 3 4 5; do
        dias="$dias        <dict><key>Weekday</key><integer>$d</integer><key>Hour</key><integer>$h</integer><key>Minute</key><integer>$m</integer></dict>
"
    done
    cat > "$HOME/Library/LaunchAgents/$rotulo.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$rotulo</string>
    <key>ProgramArguments</key>
    <array>
$programa
    </array>
    <key>WorkingDirectory</key><string>$PASTA/pje-busca</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUTF8</key><string>1</string>
    </dict>
    <key>StartCalendarInterval</key>
    <array>
$dias    </array>
    <key>StandardOutPath</key><string>$PASTA/pje-busca/logs/agenda.log</string>
    <key>StandardErrorPath</key><string>$PASTA/pje-busca/logs/agenda.log</string>
</dict>
</plist>
EOF
    plutil -lint "$HOME/Library/LaunchAgents/$rotulo.plist" >/dev/null || { echo "Arquivo inválido: $rotulo.plist"; return 1; }
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
    vigia)
        case "$2" in
            instalar)
                [ -x .venv/bin/python ] || { echo "Rode ./instalar.sh primeiro."; exit 1; }
                [ -f pje-busca/.env ] || { echo "Falta o pje-busca/.env (PRESTO_* e VIOS_*)."; exit 1; }
                chmod +x pje-busca/agenda_madrugada.command
                if grep -qE '^VIGIA_ACESSO=presto' pje-busca/.env; then grep -qE '^PRESTO_PIN=.+' pje-busca/.env || echo "AVISO: sem PRESTO_PIN no pje-busca/.env a rodada da madrugada não entra no PJe."; else echo "Login no PJe pelo Loy Trust: a extensão precisa estar com sessão aberta no Chrome do Mac."; fi
                mkdir -p pje-busca/logs "$HOME/Library/LaunchAgents"
                for e in $VIGIA_ETAPAS; do
                    vigia_plist "$e" || exit 1
                    launchctl bootout "$DOMINIO/br.automacao-vios.vigia-$e" 2>/dev/null
                    for _ in 1 2 3 4 5; do
                        launchctl print "$DOMINIO/br.automacao-vios.vigia-$e" >/dev/null 2>&1 || break
                        sleep 1
                    done
                    launchctl bootstrap "$DOMINIO" "$HOME/Library/LaunchAgents/br.automacao-vios.vigia-$e.plist" || exit 1
                done
                echo "Agenda do vigia ligada (seg a sex): VIOS + DJEN + monitor às 7h40; associados + monitor no PJe às 3h20."
                echo "Alerta: só na aba Cumprimentos da vila. Log: ./servidor_mac.sh vigia log"
                echo "A rodada da madrugada abre uma janela do Terminal e precisa da tela do Mac DESBLOQUEADA: ./servidor_mac.sh vigia tela"
                echo "Teste agora, com você no Mac (o macOS pode pedir permissão para o Python controlar o Chrome):"
                echo "  ./servidor_mac.sh vigia agora manha   |   ./servidor_mac.sh vigia agora madrugada"
                ;;
            parar)
                for e in $VIGIA_ETAPAS; do
                    launchctl bootout "$DOMINIO/br.automacao-vios.vigia-$e" 2>/dev/null
                    rm -f "$HOME/Library/LaunchAgents/br.automacao-vios.vigia-$e.plist"
                done
                echo "Agenda do vigia desligada (o botão da aba continua funcionando)."
                ;;
            agora)
                [[ " $VIGIA_ETAPAS " == *" $3 "* ]] || { echo "uso: ./servidor_mac.sh vigia agora manha | madrugada"; exit 1; }
                if launchctl kickstart "$DOMINIO/br.automacao-vios.vigia-$3"; then
                    echo "Rodada '$3' iniciada em segundo plano. Acompanhe: ./servidor_mac.sh vigia log"
                else
                    echo "Agenda não instalada (./servidor_mac.sh vigia instalar)."
                fi
                ;;
            log)
                tail -n 50 -f pje-busca/logs/agenda.log
                ;;
            tela)
                # a rodada da madrugada precisa da sessão do Mac desbloqueada: com a tela bloqueada o quadro do
                # Presto não aparece (25/11/2026). O robô não destrava a tela (não digita a senha do Mac).
                if [ "$3" = "liberar" ]; then
                    echo "Desligando o bloqueio automático da tela (o macOS pede a senha do Mac uma vez):"
                    sysadminctl -screenLock off -password - || exit 1
                    defaults -currentHost write com.apple.screensaver idleTime -int 0
                    echo "Impedindo o Mac de dormir (a tela pode apagar; a rodada liga a tela antes de entrar no PJe):"
                    sudo pmset -a sleep 0 disksleep 0 || exit 1
                    echo "Pronto. Para voltar ao bloqueio: ./servidor_mac.sh vigia tela bloquear"
                elif [ "$3" = "bloquear" ]; then
                    sysadminctl -screenLock immediate -password - || exit 1
                    echo "Bloqueio automático da tela ligado de novo (a rodada da madrugada não vai entrar no PJe)."
                else
                    echo "Bloqueio da tela: $(sysadminctl -screenLock status 2>&1 | sed 's/.*\] //')"
                    echo "Descanso de tela: $(defaults -currentHost read com.apple.screensaver idleTime 2>/dev/null || echo padrão) s (0 = nunca)"
                    pmset -g | grep -E '^ *(sleep|displaysleep) ' | sed 's/^ */Energia: /'
                    if ioreg -n Root -d1 | grep -q '"CGSSessionScreenIsLocked"=Yes'; then
                        echo "Agora: tela BLOQUEADA"
                    else
                        echo "Agora: tela desbloqueada"
                    fi
                    echo "Para a rodada da madrugada: bloqueio da tela desligado e 'sleep 0'. Ajustar: ./servidor_mac.sh vigia tela liberar"
                fi
                ;;
            status|"")
                for e in $VIGIA_ETAPAS; do
                    if launchctl print "$DOMINIO/br.automacao-vios.vigia-$e" >/dev/null 2>&1; then
                        echo "vigia-$e: agendado ($(vigia_hora "$e" | tr ' ' 'h')) · $(launchctl print "$DOMINIO/br.automacao-vios.vigia-$e" | grep -E '^[[:space:]]*(state|last exit code) =' | tr -s ' ' | tr '\n' ' ')"
                    else
                        echo "vigia-$e: não instalado (./servidor_mac.sh vigia instalar)"
                    fi
                done
                [ -f pje-busca/logs/agenda_ultima.json ] && echo "última rodada: $(cat pje-busca/logs/agenda_ultima.json)"
                ;;
            *) echo "uso: ./servidor_mac.sh vigia instalar | parar | status | log | tela [liberar|bloquear] | agora manha|madrugada"; exit 1 ;;
        esac
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
        echo
        echo "== Agenda do vigia (pje-busca)"
        "$0" vigia status
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
        echo "     ./servidor_mac.sh vigia instalar | parar | status | log | agora manha|madrugada"
        echo "     ./servidor_mac.sh tudo            (status dos serviços e da agenda do vigia)"
        echo "     ./servidor_mac.sh atualizar-tudo  (bot primeiro, depois este repositório e o coletor)"
        exit 1
        ;;
esac
