"""Andamento do Jarvis (relatório mensal de processos) para a vila do Ultron.

Cada evento vai por POST /eventos ao Ultron (VILA_URL, com a senha VILA_SENHA), no formato de
doc/vila/contrato-eventos.md, com bot "jarvis". Só contagens: nunca nome de grupo, de cliente ou
número de processo. VILA_URL vazio = vila desligada. Se o Ultron estiver fora do ar, o relatório
segue normalmente: o aviso só vai para o log (uma vez).
"""
import base64
import json
import logging
import os
import urllib.request
from datetime import datetime

log = logging.getLogger(__name__)


class Vila:
    def __init__(self, url, senha, execucao):
        self.url, self.senha, self.execucao = url, senha, execucao
        self.avisou = False

    @classmethod
    def do_env(cls):
        return cls(os.getenv("VILA_URL", "").strip(), os.getenv("VILA_SENHA", "").strip(),
                   datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

    def emitir(self, tipo, **dados):
        if not self.url:
            return
        corpo = {"bot": "jarvis", "envio": self.execucao, "tipo": tipo,
                 "ts": datetime.now().isoformat(timespec="seconds"), **dados}
        pedido = urllib.request.Request(self.url, data=json.dumps(corpo).encode("utf-8"), method="POST",
                                        headers={"Content-Type": "application/json"})
        if self.senha:
            chave = base64.b64encode(f"jarvis:{self.senha}".encode()).decode()
            pedido.add_header("Authorization", "Basic " + chave)
        try:
            urllib.request.urlopen(pedido, timeout=5).close()
        except Exception as e:
            if not self.avisou:
                log.warning("Não consegui mandar o andamento para a vila (%s): %s", self.url, e)
                self.avisou = True
