"""Eventos do Ultron para a vila (contrato em doc/vila/contrato-eventos.md).

Cada evento é uma linha JSON em <saída>/eventos.jsonl, só com acréscimos no fim:
{"n": 131, "ts": "2026-10-31T09:41:02", "bot": "ultron", "envio": "<id>", "tipo": "...", ...}
A vila só lê (GET /eventos?desde=N). Dados mínimos: CI, nome da tarefa e contagens.
"""
import json
import logging
import re
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


# bots de fora que podem mandar eventos por POST /eventos (o "ultron" só escreve daqui de dentro)
BOTS_EXTERNOS = {"zangao"}
TAMANHO_MAX = 64 * 1024  # bytes do corpo de um evento recebido
# nunca guardar em evento de bot de fora (dados de cliente / do processo / do comprovante)
PROIBIDAS = {"texto", "titulo", "tarefa", "link", "link_tarefa", "link_processo", "cliente", "nome",
             "cnj", "orgao", "valor", "valores", "processo_cnj", "comprovante", "arquivo", "pdf", "conteudo"}
CNJ_TEXTO = re.compile(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}")
TS = re.compile(r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\Z")
CAMPO = re.compile(r"\A[A-Za-z0-9_.:-]{1,64}\Z")  # bot, envio e tipo


class EventoInvalido(ValueError):
    pass


def _limpar(valor):
    """Tira chaves proibidas e qualquer texto no formato CNJ (o Zangão já não manda; é garantia)."""
    if isinstance(valor, dict):
        return {k: _limpar(v) for k, v in valor.items() if k not in PROIBIDAS}
    if isinstance(valor, list):
        return [_limpar(v) for v in valor]
    if isinstance(valor, str):
        return CNJ_TEXTO.sub("[removido]", valor)
    return valor


def receber(pasta, corpo):
    """Evento de um bot de fora (POST /eventos). Valida, limpa e grava; devolve o n.
    Levanta EventoInvalido se o corpo não serve."""
    if len(corpo) > TAMANHO_MAX:
        raise EventoInvalido("evento grande demais")
    try:
        evento = json.loads(corpo.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise EventoInvalido("corpo não é JSON")
    if not isinstance(evento, dict):
        raise EventoInvalido("o evento tem que ser um objeto JSON")
    bot, envio, tipo = evento.pop("bot", None), evento.pop("envio", None), evento.pop("tipo", None)
    if bot not in BOTS_EXTERNOS:
        raise EventoInvalido(f"bot não aceito: {bot!r}")
    for nome, valor in (("envio", envio), ("tipo", tipo)):
        if not isinstance(valor, str) or not CAMPO.match(valor):
            raise EventoInvalido(f"{nome} inválido")
    evento.pop("n", None)  # o n é sempre daqui
    ts = evento.pop("ts", None)
    dados = _limpar(evento)
    if isinstance(ts, str) and TS.match(ts):
        dados["ts"] = ts  # horário em que aconteceu no bot (não o da chegada)
    n = emitir(pasta, envio, tipo, bot=bot, **dados)
    if n is None:
        raise OSError("não consegui gravar o evento")
    return n


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
