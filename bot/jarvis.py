"""Jarvis (relatório mensal de processos por Grupo Cliente, branch relatorio-processos) disparado pelo Ultron.

Como o Zangão: o Jarvis fica instalado numa pasta própria (JARVIS_PASTA, com .venv e .env.usuario2
dele) no mesmo computador do Ultron. A vila pede para rodar (POST /jarvis/rodar) e o Ultron abre o
`relatorio_processos.py` em segundo plano, como processo separado. O andamento chega à vila pelos
eventos que o próprio Jarvis manda (POST /eventos, bot "jarvis").

- mes: todos os grupos do PROCESSOS_GRUPOS do .env do Jarvis -> as planilhas do mês;
- teste: só os 2 primeiros processos de cada grupo (--limite 2), salvos em AAAA-MM/teste/;
- só leitura no VIOS; uma execução por vez. As planilhas ficam na pasta do Jarvis e a página
  /jarvis lista e baixa cada uma.
"""
import json
import logging
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values

log = logging.getLogger(__name__)

ENV = ".env.usuario2"
SCRIPT = "relatorio_processos.py"
MODOS = {"mes": [], "teste": ["--limite", "2"]}
ARQUIVO = ".vila_execucao.json"  # na pasta logs/ do Jarvis: execução em andamento (pid, modo, início)
LOG = "execucoes_vila.log"  # na pasta logs/ do Jarvis: saída de cada execução disparada pela vila
# só o necessário: nenhuma variável do Ultron (senha da página, chaves de API) vai para o Jarvis
AMBIENTE = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL",
            # Windows (para testar no PC): o Selenium precisa destas para achar o Chrome
            "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
            "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "PROGRAMDATA")
_trava = threading.Lock()


class JarvisErro(Exception):
    pass


def _python(pasta):
    pasta = Path(pasta)
    windows = pasta / ".venv" / "Scripts" / "python.exe"
    return windows if windows.exists() else pasta / ".venv" / "bin" / "python"


def configurado(pasta):
    return bool(pasta) and _python(pasta).exists() and (Path(pasta) / SCRIPT).exists() \
        and (Path(pasta) / ENV).exists()


def _vivo(pid):
    """O processo existe e é o relatorio_processos.py (não um pid reaproveitado)."""
    if not pid:
        return False
    if os.name == "nt":
        saida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in saida
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:
        return True
    return SCRIPT in cmd


def _ler(pasta):
    try:
        return json.loads((Path(pasta) / "logs" / ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status(pasta):
    """{"configurado", "rodando", "modo", "inicio", "grupos"}."""
    info = {"configurado": configurado(pasta), "rodando": False, "modo": None, "inicio": None, "grupos": 0}
    if info["configurado"]:
        grupos = dotenv_values(Path(pasta) / ENV).get("PROCESSOS_GRUPOS") or ""
        info["grupos"] = len([g for g in grupos.split("|") if g.strip()])
        atual = _ler(pasta)
        if atual and _vivo(int(atual.get("pid", 0))):
            info.update(rodando=True, modo=atual.get("modo"), inicio=atual.get("inicio"))
    return info


def pasta_relatorios(pasta):
    """Onde o Jarvis salva as planilhas: RELATORIO_PASTA ou <SAIDA_PASTA>/relatorios (do .env dele)."""
    env = dotenv_values(Path(pasta) / ENV)
    destino = (env.get("RELATORIO_PASTA") or "").strip()
    if destino:
        return Path(os.path.expanduser(destino))
    return Path(pasta) / ((env.get("SAIDA_PASTA") or "").strip() or "saida") / "relatorios"


def planilhas(pasta):
    """[{"mes": "2026-11", "teste": False, "arquivo": "CASA DO CELULAR.xlsx", "tamanho": ..., "gerada": ...}],
    da mais nova para a mais antiga."""
    if not configurado(pasta):
        return []
    raiz, lista = pasta_relatorios(pasta), []
    for xlsx in raiz.glob("*/*.xlsx"):
        lista.append((xlsx, xlsx.parent.name, False))
    for xlsx in raiz.glob("*/teste/*.xlsx"):
        lista.append((xlsx, xlsx.parent.parent.name, True))
    saida = [{"mes": mes, "teste": teste, "arquivo": x.name, "tamanho": x.stat().st_size,
              "gerada": datetime.fromtimestamp(x.stat().st_mtime).strftime("%d/%m/%Y %H:%M")}
             for x, mes, teste in lista]
    return sorted(saida, key=lambda p: (p["mes"], not p["teste"], p["arquivo"]), reverse=True)


def planilha(pasta, mes, nome, teste=False):
    """Caminho de uma planilha listada em planilhas() (None se não existe: nada fora da pasta)."""
    for p in planilhas(pasta):
        if p["mes"] == mes and p["arquivo"] == nome and p["teste"] == teste:
            raiz = pasta_relatorios(pasta) / mes
            return (raiz / "teste" / nome) if teste else (raiz / nome)
    return None


def rodar(pasta, modo):
    """Abre o Jarvis em segundo plano. Devolve o status; levanta JarvisErro se não pode rodar."""
    if modo not in MODOS:
        raise JarvisErro("modo inválido")
    if not configurado(pasta):
        raise JarvisErro("o Jarvis não está instalado neste servidor (JARVIS_PASTA)")
    with _trava:
        if status(pasta)["rodando"]:
            raise JarvisErro("o Jarvis já está rodando")
        pasta = Path(pasta)
        (pasta / "logs").mkdir(exist_ok=True)
        ambiente = {k: os.environ[k] for k in AMBIENTE if k in os.environ}
        ambiente["PYTHONUTF8"] = "1"
        inicio = datetime.now().isoformat(timespec="seconds")
        saida = open(pasta / "logs" / LOG, "a", encoding="utf-8")
        saida.write(f"\n===== {inicio} · modo {modo} (pela vila) =====\n")
        saida.flush()
        extra = {"start_new_session": True} if os.name != "nt" else {}  # sobrevive a um reinício da página
        proc = subprocess.Popen([str(_python(pasta)), SCRIPT, ENV, *MODOS[modo]], cwd=pasta, env=ambiente,
                                stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT, **extra)
        saida.close()
        arquivo = pasta / "logs" / ARQUIVO
        arquivo.write_text(json.dumps({"pid": proc.pid, "modo": modo, "inicio": inicio}), encoding="utf-8")
        log.info("Jarvis iniciado pela vila: modo %s, pid %d", modo, proc.pid)

        def esperar():
            codigo = proc.wait()  # recolhe o processo (sem isso ele ficaria "zumbi" e pareceria vivo)
            log.info("Jarvis terminou (modo %s, código %s)", modo, codigo)
            try:
                if (_ler(pasta) or {}).get("pid") == proc.pid:
                    arquivo.unlink()
            except OSError:
                pass

        threading.Thread(target=esperar, daemon=True).start()
    return status(pasta)
