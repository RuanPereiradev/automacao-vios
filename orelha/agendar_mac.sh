#!/usr/bin/env bash
# Agenda o Orelha no Mac (launchd), no horário do orelha/.env: o relatório do dia (ORELHA_HORARIO,
# padrão "seg-sex 07:30") e os processos parados (ORELHA_HORARIO_PARADOS, padrão "sab 08:00").
# O Mac tem que ficar com o usuário logado (o Chrome precisa da sessão), como no servidor_mac.sh.
# Se o Mac estiver dormindo na hora marcada, o launchd roda quando ele acordar.
# uso: ./agendar_mac.sh instalar   (cria os dois agendamentos; rodar de novo depois de mudar o horário)
#      ./agendar_mac.sh agora      (roda o relatório do dia agora, pelo agendamento, para testar)
#      ./agendar_mac.sh parar      (tira os dois agendamentos)
#      ./agendar_mac.sh status     (mostra se estão instalados e o resultado da última vez)
#      ./agendar_mac.sh log        (acompanha o log do agendamento; Ctrl+C sai)
cd "$(dirname "$0")" || exit 1
PASTA=$(pwd)
DOMINIO="gui/$(id -u)"
DIA="br.automacao-vios.orelha"
PARADOS="br.automacao-vios.orelha-parados"
LOG="$PASTA/logs/launchd.log"

if [ "$(uname)" != "Darwin" ]; then
    echo "Este script é só para o Mac. No Linux, use o cron (ver orelha/README.md, seção Agendar)."
    exit 1
fi

valor() { grep -E "^$1=" .env 2>/dev/null | tail -n 1 | cut -d= -f2- | sed -e "s/^['\"]//" -e "s/['\"]$//"; }

# "seg-sex 07:30; sab 09:00" -> dicionários do StartCalendarInterval (Weekday: 1 = segunda ... 6 = sábado, 0 = domingo)
intervalos() {
    .venv/bin/python - "$1" <<'PY'
import sys, unicodedata
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
def norm(t): return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
saida = []
for item in [i.strip() for i in sys.argv[1].split(";") if i.strip()]:
    try:
        dias_txt, hm = item.rsplit(None, 1)
        h, m = (int(x) for x in hm.split(":"))
        assert 0 <= h < 24 and 0 <= m < 60
    except Exception:
        sys.exit(f"horário inválido {item!r} (ex.: seg-sex 07:30)")
    dias = set()
    for parte in norm(dias_txt).replace(" ", "").split(","):
        if "-" in parte:
            a, b = parte.split("-", 1)
            if a not in DIAS or b not in DIAS: sys.exit(f"dia desconhecido em {item!r} (use {', '.join(DIAS)})")
            i, j = DIAS.index(a), DIAS.index(b)
            dias.update(k % 7 for k in range(i, (j if j >= i else j + 7) + 1))
        elif parte in DIAS:
            dias.add(DIAS.index(parte))
        else:
            sys.exit(f"dia desconhecido em {item!r} (use {', '.join(DIAS)})")
    for d in sorted(dias):
        saida.append(f"        <dict><key>Weekday</key><integer>{(d + 1) % 7}</integer>"
                     f"<key>Hour</key><integer>{h}</integer><key>Minute</key><integer>{m}</integer></dict>")
if not saida: sys.exit("horário vazio")
print("\n".join(saida))
PY
}

plist() {  # rótulo, intervalos, argumentos extras do rodar.sh
    local args="" a
    for a in $3; do args="$args        <string>$a</string>
"; done
    cat > "$HOME/Library/LaunchAgents/$1.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$1</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>$PASTA/rodar.sh</string>
$args    </array>
    <key>WorkingDirectory</key><string>$PASTA</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUTF8</key><string>1</string>
    </dict>
    <key>StartCalendarInterval</key>
    <array>
$2
    </array>
    <key>StandardOutPath</key><string>$LOG</string>
    <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
EOF
    plutil -lint "$HOME/Library/LaunchAgents/$1.plist" >/dev/null || { echo "Arquivo do agendamento inválido: $1"; exit 1; }
}

ligar() {  # tira o antigo (se houver), espera o launchd soltar e liga o novo
    launchctl bootout "$DOMINIO/$1" 2>/dev/null
    for _ in 1 2 3 4 5 6 7 8 9 10; do launchctl print "$DOMINIO/$1" >/dev/null 2>&1 || break; sleep 1; done
    launchctl bootstrap "$DOMINIO" "$HOME/Library/LaunchAgents/$1.plist" || exit 1
}

case "$1" in
    instalar)
        [ -x .venv/bin/python ] || { echo "Rode ./instalar.sh primeiro."; exit 1; }
        [ -f .env ] || { echo "Falta o orelha/.env (o ./instalar.sh cria)."; exit 1; }
        if [ -z "$(valor SISTEMA_USUARIO)" ] || [ -z "$(valor SISTEMA_SENHA)" ]; then
            echo "Preencha SISTEMA_USUARIO e SISTEMA_SENHA no orelha/.env antes de agendar."
            echo "Para usar o mesmo login do Sam: grep -E '^SISTEMA_(USUARIO|SENHA)=' ../.env >> .env"
            exit 1
        fi
        HD=$(valor ORELHA_HORARIO); HD=${HD:-seg-sex 07:30}
        HP=$(valor ORELHA_HORARIO_PARADOS); HP=${HP:-sab 08:00}
        I_DIA=$(intervalos "$HD") || { echo "Corrija ORELHA_HORARIO no orelha/.env (ex.: seg-sex 07:30)."; exit 1; }
        I_PAR=$(intervalos "$HP") || { echo "Corrija ORELHA_HORARIO_PARADOS no orelha/.env (ex.: sab 08:00)."; exit 1; }
        case "$(valor HEADLESS | tr 'A-Z' 'a-z')" in true|1|sim) ;; *) echo "AVISO: HEADLESS não é true no orelha/.env: o Chrome vai abrir uma janela no Mac a cada relatório." ;; esac
        [ -n "$(valor VILA_URL)" ] || echo "AVISO: VILA_URL vazio no orelha/.env: o relatório sai, mas a Vila 05 não acompanha."
        mkdir -p logs "$HOME/Library/LaunchAgents"
        plist "$DIA" "$I_DIA" ""
        plist "$PARADOS" "$I_PAR" "--funcoes parados --sem-pdf"
        ligar "$DIA"; ligar "$PARADOS"
        echo "Orelha agendado: relatório do dia em \"$HD\" e processos parados em \"$HP\"."
        echo "O Mac precisa ficar com o usuário logado. Para testar agora: ./agendar_mac.sh agora"
        ;;
    agora)
        launchctl print "$DOMINIO/$DIA" >/dev/null 2>&1 || { echo "Não agendado ainda: ./agendar_mac.sh instalar"; exit 1; }
        launchctl kickstart "$DOMINIO/$DIA" && echo "Rodando o relatório do dia. Acompanhe: ./agendar_mac.sh log"
        ;;
    parar)
        for r in "$DIA" "$PARADOS"; do
            launchctl bootout "$DOMINIO/$r" 2>/dev/null; rm -f "$HOME/Library/LaunchAgents/$r.plist"
        done
        echo "Agendamentos do Orelha removidos."
        ;;
    status)
        for r in "$DIA" "$PARADOS"; do
            if launchctl print "$DOMINIO/$r" >/dev/null 2>&1; then
                echo "$r: instalado"; launchctl print "$DOMINIO/$r" | grep -E "^[[:space:]]*(state|last exit code|runs) =" | sed 's/^/  /'
            else
                echo "$r: não instalado (./agendar_mac.sh instalar)"
            fi
        done
        ;;
    log)
        mkdir -p logs; touch "$LOG"; tail -n 50 -f "$LOG"
        ;;
    *)
        echo "uso: ./agendar_mac.sh instalar | agora | parar | status | log"
        exit 1
        ;;
esac
