"""Eventos do Ultron para a vila (contrato em doc/vila/contrato-eventos.md).

Cada evento é uma linha JSON em <saída>/eventos.jsonl, só com acréscimos no fim:
{"n": 131, "ts": "2026-10-31T09:41:02", "bot": "ultron", "envio": "<id>", "tipo": "...", ...}
A vila só lê (GET /eventos?desde=N). Dados mínimos: CI, nome da tarefa e contagens.
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path

try:
    import fcntl  # Mac e Linux: trava entre processos
except ImportError:  # pragma: no cover
    fcntl = None

log = logging.getLogger(__name__)
ARQUIVO = "eventos.jsonl"
LIMITE_INICIAL = 500  # no 1º acesso (desde=0), só os últimos
_trava = threading.Lock()  # Flask e a thread do Selenium escrevem no mesmo processo


def _ultimo_n(f):
    """n da última linha do arquivo (0 se vazio). Lê só o fim do arquivo."""
    f.seek(0, 2)
    tamanho = f.tell()
    f.seek(max(0, tamanho - 8192))
    for linha in reversed(f.read().splitlines()):
        try:
            return int(json.loads(linha)["n"])
        except (ValueError, KeyError, TypeError):
            continue
    return 0


def emitir(pasta, envio, tipo, bot="ultron", **dados):
    """Acrescenta um evento e devolve o n dele. Nunca derruba o envio: erro só vai para o log."""
    try:
        caminho = Path(pasta) / ARQUIVO
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with _trava, open(caminho, "a+b") as f:
            if fcntl:
                fcntl.flock(f, fcntl.LOCK_EX)
            try:
                n = _ultimo_n(f) + 1
                evento = {"n": n, "ts": datetime.now().isoformat(timespec="seconds"), "bot": bot,
                          "envio": envio, "tipo": tipo, **dados}
                f.seek(0, 2)
                f.write((json.dumps(evento, ensure_ascii=False) + "\n").encode("utf-8"))
                f.flush()
            finally:
                if fcntl:
                    fcntl.flock(f, fcntl.LOCK_UN)
        return n
    except Exception:
        log.exception("Não consegui gravar o evento %s do envio %s", tipo, envio)
        return None


def ler(pasta, desde=0, limite=LIMITE_INICIAL):
    """{"ultimo": n, "eventos": [...]} com os eventos de n > desde (desde=0: os últimos `limite`)."""
    caminho = Path(pasta) / ARQUIVO
    eventos = []
    if caminho.exists():
        for linha in caminho.read_text(encoding="utf-8").splitlines():
            try:
                eventos.append(json.loads(linha))
            except ValueError:
                continue
    ultimo = eventos[-1]["n"] if eventos else 0
    novos = [e for e in eventos if e.get("n", 0) > desde]
    if desde <= 0:
        novos = novos[-limite:]
    return {"ultimo": ultimo, "eventos": novos}
