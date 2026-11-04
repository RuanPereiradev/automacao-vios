"""Eventos do Orelha para a vila dos bots (bot = "orelha").

Cada evento pode ir para três lugares, e nada daqui afeta o Orelha (emitir nunca levanta):
  - stdout, uma linha "@evento {json}" (só com --eventos; como o Albi, para quem roda o Orelha
    lendo a saída padrão);
  - POST em VILA_URL (servidor do Ultron, rota /eventos), se VILA_URL estiver preenchida — cliente
    copiado do Zangão (branch bot-edita-vios, bot/vila.py): só biblioteca padrão, timeout curto,
    depois de 3 falhas seguidas para de tentar e guarda em <saída>/vila_pendentes.jsonl;
  - <saída do dia>/eventos.jsonl (registro local da execução).

Dados mínimos (doc/vila/contrato-eventos.md): só fases e contagens. Nunca nome de cliente, de
pessoa da equipe, número de processo, texto de tarefa/intimação nem link. `limpar` retira as
chaves proibidas e qualquer texto com cara de número CNJ de todo evento.

Uso nas funções:  ctx.emitir("fase", fase="lendo_calendario")
"""
import base64
import json
import logging
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from urllib import request

log = logging.getLogger("orelha")

BOT = "orelha"
PENDENTES = "vila_pendentes.jsonl"
LOCAL = "eventos.jsonl"
FALHAS_MAX = 3

# chaves que nunca vão num evento (dados de cliente, da equipe ou do processo)
PROIBIDAS = {"texto", "titulo", "detalhe", "tarefa", "link", "link_tarefa", "link_processo", "cliente",
             "nome", "nomes", "cnj", "numero", "numeros_processo", "processo", "orgao", "valor", "valores",
             "responsavel", "responsaveis", "por_responsavel", "pessoa", "pessoas", "advogado", "empresa",
             "empresas", "cpf", "cnpj", "documento", "arquivo", "pdf", "conteudo", "itens", "senha"}
CNJ_TEXTO = re.compile(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}")


def limpar(valor, tipo=""):
    """Tira chaves proibidas (em qualquer nível) e texto no formato CNJ."""
    if isinstance(valor, dict):
        saida = {}
        for k, v in valor.items():
            if k in PROIBIDAS:
                log.warning("Vila: campo '%s' retirado do evento %s (dado de cliente/equipe)", k, tipo)
                continue
            saida[k] = limpar(v, tipo)
        return saida
    if isinstance(valor, (list, tuple)):
        return [limpar(v, tipo) for v in valor]
    if isinstance(valor, str):
        return CNJ_TEXTO.sub("[removido]", valor)
    return valor


class Eventos:
    def __init__(self, url="", senha="", usuario=BOT, pasta=None, timeout=2.0, envio=None, stdout=False,
                 saida_padrao=None):
        self.url = (url or "").strip()
        self._senha = senha or ""
        self._auth = "Basic " + base64.b64encode(f"{usuario}:{senha}".encode()).decode() if senha else None
        self.pasta = Path(pasta) if pasta else None
        self.timeout = timeout
        self.envio = envio or f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
        self.stdout = stdout
        self._saida = saida_padrao  # para testes; None = sys.stdout na hora de escrever
        self.falhas = 0
        self.desistiu = False
        self.emitidos = []

    def emitir(self, tipo, **dados):
        """Monta o evento e manda para os destinos ligados. Devolve o evento (ou None). Nunca levanta."""
        try:
            evento = limpar({"bot": BOT, "envio": self.envio, "tipo": tipo,
                             "ts": datetime.now().isoformat(timespec="seconds"), **dados}, tipo)
            self.emitidos.append(evento)
            linha = json.dumps(evento, ensure_ascii=False, default=str)
        except Exception as e:
            log.warning("Vila: evento %s descartado (%s)", tipo, e.__class__.__name__)
            return None
        if self.stdout:
            try:
                print("@evento " + linha, file=self._saida or sys.stdout, flush=True)
            except (OSError, ValueError):
                pass  # quem lia a saída fechou: o Orelha continua
        self._gravar(LOCAL, linha)
        if self.url:
            try:
                if self.desistiu or not self._enviar(linha, tipo):
                    self._gravar(PENDENTES, linha)
            except Exception as e:  # proteção final
                log.warning("Vila: evento %s não enviado (%s)", tipo, self._sem_senha(e.__class__.__name__))
        return evento

    def _enviar(self, linha, tipo):
        req = request.Request(self.url, data=linha.encode("utf-8"), method="POST",
                              headers={"Content-Type": "application/json; charset=utf-8"})
        if self._auth:
            req.add_header("Authorization", self._auth)
        try:
            with request.urlopen(req, timeout=self.timeout) as r:
                r.read()
            self.falhas = 0
            return True
        except Exception as e:
            if hasattr(e, "close"):  # HTTPError guarda a resposta aberta
                try:
                    e.close()
                except Exception:
                    pass
            self.falhas += 1
            log.warning("Vila: evento %s não enviado (%s)", tipo, self._descrever(e))
            if self.falhas >= FALHAS_MAX:
                self.desistiu = True
                log.warning("Vila: %d falhas seguidas, não tento mais nesta execução", FALHAS_MAX)
            return False

    def _descrever(self, e):
        codigo = getattr(e, "code", None)
        if codigo:
            return f"HTTP {codigo}"
        motivo = getattr(e, "reason", None) or e
        if isinstance(motivo, str):
            return self._sem_senha(motivo[:80])
        nome = "timeout" if "timed out" in str(motivo).lower() or isinstance(motivo, TimeoutError) \
            else motivo.__class__.__name__
        return self._sem_senha(nome)

    def _sem_senha(self, texto):
        return texto.replace(self._senha, "***") if self._senha else texto

    def _gravar(self, nome, linha):
        if not self.pasta:
            return
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            with open(self.pasta / nome, "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception as e:
            log.warning("Vila: não consegui gravar %s (%s)", nome, e.__class__.__name__)


_atual = Eventos()


def iniciar(cfg=None, pasta=None, stdout=False, envio=None):
    """Instância da execução (o main.py chama uma vez). Nunca levanta: configuração ruim = só local."""
    global _atual
    try:
        _atual = Eventos(getattr(cfg, "vila_url", ""), getattr(cfg, "vila_senha", ""),
                         getattr(cfg, "vila_usuario", BOT) or BOT, pasta, getattr(cfg, "vila_timeout", 2.0),
                         envio, stdout)
        if _atual.url:
            log.info("Vila ligada: eventos do envio %s", _atual.envio)
    except Exception as e:
        log.warning("Vila desligada: configuração inválida (%s)", e.__class__.__name__)
        _atual = Eventos(pasta=pasta, stdout=stdout)
    return _atual


def atual():
    return _atual


def emitir(tipo, **dados):
    """emitir("fase", fase="lendo_calendario") — nunca levanta."""
    return _atual.emitir(tipo, **dados)
