"""Rodadas agendadas do vigia (launchd no Mac mini: ./servidor_mac.sh vigia instalar).

  manha      vigia.py vios, vigia.py djen e vigia.py monitor (cada passo roda mesmo se o anterior falhar: o djen
             usa a última lista do VIOS; o monitor só usa as APIs do DJEN e do DataJud)
  madrugada  vigia.py associados e vigia.py monitor-tribunal (PJe pelo Loy Trust, com o Chrome do Mac)
O monitor sem carteira importada (vigia.py monitor-importar) não faz nada e não conta como falha.

O alerta fica só na aba Cumprimentos da vila (decisão de 24/11/2026): nada é enviado para fora.
Usa a mesma trava do botão da aba (logs/.vila_djen.json): uma execução por vez. Se o botão estiver rodando, a rodada
agendada espera até 1 hora e depois desiste, registrando o motivo. O resultado da última rodada agendada fica em
logs/agenda_ultima.json (a aba mostra).
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ETAPAS = {"manha": ["vios", "djen", "monitor"], "madrugada": ["associados", "monitor-tribunal"]}
TEXTOS = {"manha": "VIOS + DJEN + monitor", "madrugada": "associados + monitor no PJe"}
TRAVA = Path("logs") / ".vila_djen.json"   # a mesma de bot/cumprimentos.py (EXECUCAO)
ULTIMA = Path("logs") / "agenda_ultima.json"
SCRIPT = "vigia.py"


def _vivo(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:  # noqa: BLE001
        return True
    return SCRIPT in cmd


def ocupado(pasta, vivo=_vivo):
    """Comando da trava, se outra execução do vigia está rodando; senão None."""
    try:
        atual = json.loads((Path(pasta) / TRAVA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pid = int(atual.get("pid") or 0)
    if pid and pid != os.getpid() and vivo(pid):
        return atual.get("comando") or "djen"
    return None


def _executar(pasta):
    def run(comando):
        # sem buffer: o log da agenda mostra o andamento de cada passo enquanto ele roda
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        return subprocess.run([sys.executable, str(Path(pasta) / SCRIPT), comando], cwd=pasta, env=env,
                              stdin=subprocess.DEVNULL).returncode
    return run


def rodar(pasta, etapa, executar=None, esperar_max=3600, passo=60, dormir=time.sleep, agora=datetime.now,
          vivo=_vivo, aviso=print):
    """Roda os passos da etapa com a trava. Devolve 0 (tudo ok), 1 (algum passo falhou) ou 3 (não rodou: ocupado)."""
    pasta = Path(pasta)
    if etapa not in ETAPAS:
        raise ValueError(f"etapa inválida: {etapa} (use {' ou '.join(ETAPAS)})")
    executar = executar or _executar(pasta)
    (pasta / "logs").mkdir(exist_ok=True)
    inicio = agora().isoformat(timespec="seconds")
    esperou = 0
    while (outro := ocupado(pasta, vivo)):
        if esperou >= esperar_max:
            aviso(f"Outra verificação ({outro}) continua rodando depois de {esperou // 60} min: rodada {etapa} não feita.")
            _registrar(pasta, etapa, inicio, agora, [], f"não rodou: '{outro}' estava rodando")
            return 3
        aviso(f"Outra verificação ({outro}) está rodando; esperando...")
        dormir(passo)
        esperou += passo
    trava = pasta / TRAVA
    trava.write_text(json.dumps({"pid": os.getpid(), "inicio": inicio, "comando": f"agenda-{etapa}"}), encoding="utf-8")
    passos = []
    try:
        for comando in ETAPAS[etapa]:
            aviso(f"===== {agora():%d/%m/%Y %H:%M} · rodada agendada ({etapa}) · vigia {comando} =====")
            try:
                codigo = executar(comando)
            except Exception as e:  # noqa: BLE001 — um passo que quebra não impede o próximo
                aviso(f"vigia {comando} quebrou: {e}")
                codigo = -1
            passos.append({"comando": comando, "codigo": codigo})
    finally:
        try:
            if json.loads(trava.read_text(encoding="utf-8")).get("pid") == os.getpid():
                trava.unlink()
        except (OSError, ValueError):
            pass
        _registrar(pasta, etapa, inicio, agora, passos, "")
    return 0 if all(p["codigo"] == 0 for p in passos) else 1


def _registrar(pasta, etapa, inicio, agora, passos, motivo):
    dados = {"etapa": etapa, "texto": TEXTOS[etapa], "inicio": inicio, "fim": agora().isoformat(timespec="seconds"),
             "passos": passos, "ok": bool(passos) and all(p["codigo"] == 0 for p in passos), "motivo": motivo}
    (Path(pasta) / ULTIMA).write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def ultima(pasta):
    """Última rodada agendada (para a aba), ou None."""
    try:
        return json.loads((Path(pasta) / ULTIMA).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
