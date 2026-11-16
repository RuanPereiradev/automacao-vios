"""Log do coletor: arquivo + tela, com um filtro que apaga o que não pode aparecer.

Os módulos já não escrevem CPF, telefone, nome nem CI (só id do pedido, status e tempos). O filtro é a
segunda trava: mascara sequências com cara de CPF, telefone ou HMAC, caso um erro de biblioteca traga
o endereço consultado na mensagem.
"""
import logging
import re
import sys
from pathlib import Path

FORMATO = "%(asctime)s [%(levelname)s] %(message)s"
_CPF = re.compile(r"\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}")
_NUMERO_LONGO = re.compile(r"(?<![\w])\+?\d[\d\s().-]{8,}\d")
_HEX = re.compile(r"\b[0-9a-f]{40,}\b", re.I)
_PARAM = re.compile(r"(pesq\[[^\]]*\]|clientes_id|processos_id|form\[[^\]]*\])=[^&\s'\"]*", re.I)


def limpar_texto(texto):
    texto = _PARAM.sub(r"\1=***", texto)
    texto = _HEX.sub("***", texto)
    texto = _CPF.sub("***", texto)
    return _NUMERO_LONGO.sub("***", texto)


class FiltroPrivacidade(logging.Filter):
    def filter(self, record):
        try:
            record.msg = limpar_texto(record.getMessage())
        except Exception:  # noqa: BLE001
            record.msg = "(mensagem de log descartada)"
        record.args = None
        record.exc_info = None   # o traceback do Selenium pode ter o endereço consultado
        record.exc_text = None
        return True


def configurar(pasta_logs=None, nivel=logging.INFO):
    """Liga o log do coletor (tela e arquivo) e deixa o da Orelha só em avisos (ele cita CI)."""
    for nome in ("consulta", "orelha"):
        lg = logging.getLogger(nome)
        lg.handlers.clear()
        lg.propagate = False
    log = logging.getLogger("consulta")
    log.setLevel(nivel)
    logging.getLogger("orelha").setLevel(logging.WARNING)
    destinos = [logging.StreamHandler(sys.stderr)]
    if pasta_logs:
        try:
            Path(pasta_logs).mkdir(parents=True, exist_ok=True)
            destinos.append(logging.FileHandler(Path(pasta_logs) / "consulta.log", encoding="utf-8"))
        except OSError:
            log.warning("Sem log em arquivo")
    for h in destinos:
        h.setFormatter(logging.Formatter(FORMATO))
        h.addFilter(FiltroPrivacidade())
        log.addHandler(h)
        logging.getLogger("orelha").addHandler(h)
