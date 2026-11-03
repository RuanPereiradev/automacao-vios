"""Eventos do Bumblebee (Zangão) para a vila dos bots.

A vila só assiste: os eventos vão por POST ao servidor do Ultron (VILA_URL), que guarda e
serve para a vila. Nada daqui afeta o bot:
- só biblioteca padrão (urllib.request), timeout curto (VILA_TIMEOUT, padrão 2 s);
- qualquer erro (rede, 401, 500, timeout) vira um aviso de uma linha no log, sem a senha;
- depois de 3 falhas seguidas, para de tentar até o fim da execução (avisa uma vez);
- evento não enviado vai para <saída>/vila_pendentes.jsonl;
- VILA_URL vazia = vila desligada (nada é enviado nem gravado).

Dados mínimos: nunca vai texto/título da tarefa, nome de cliente, número CNJ, órgão julgador,
valor da causa, nome do arquivo do comprovante nem conteúdo do PDF. Dos campos preenchidos vai
só o nome ("cnj", "orgao", "valor"). `_limpar` garante isso em todo evento.
"""
import base64
import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib import request
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

log = logging.getLogger(__name__)

BOT = "zangao"
PENDENTES = "vila_pendentes.jsonl"
FALHAS_MAX = 3
TIMEOUT_PADRAO = 2.0

# chaves que nunca podem ir num evento (dados de cliente / do processo / do comprovante)
PROIBIDAS = {"texto", "titulo", "tarefa", "link", "link_tarefa", "link_processo", "cliente", "nome",
             "cnj", "orgao", "valor", "valores", "processo_cnj", "comprovante", "arquivo", "pdf", "conteudo"}
CNJ_TEXTO = re.compile(r"\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}")
CAMPOS = ("cnj", "orgao", "valor")  # únicos valores aceitos em "campos"


class Vila:
    def __init__(self, url="", senha="", usuario=BOT, pasta_saida="saida", timeout=TIMEOUT_PADRAO, envio=None):
        self.url = (url or "").strip()
        self._auth = "Basic " + base64.b64encode(f"{usuario}:{senha}".encode()).decode() if senha else None
        self._senha = senha or ""
        self.pasta = Path(pasta_saida)
        self.timeout = timeout
        self.envio = envio or f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
        self.falhas = 0
        self.desistiu = False
        self.emitidos = []  # o que saiu nesta execução (enviado ou pendente)
        self._tarefa = {}  # tarefa em andamento: tarefa_id, processo_id e extras do fim

    @property
    def ligada(self):
        return bool(self.url)

    def emitir(self, tipo, **dados):
        """Monta e envia um evento. Nunca levanta exceção."""
        if not self.ligada:
            return None
        try:
            evento = _limpar({"bot": BOT, "envio": self.envio, "tipo": tipo,
                              "ts": datetime.now().isoformat(timespec="seconds"), **dados})
            self.emitidos.append(evento)
            if self.desistiu or not self._enviar(evento):
                self._pendente(evento)
            return evento
        except Exception as e:  # pragma: no cover - proteção final
            log.warning("Vila: evento %s descartado (%s)", tipo, self._sem_senha(e.__class__.__name__))
            return None

    def _enviar(self, evento):
        corpo = json.dumps(evento, ensure_ascii=False).encode("utf-8")
        req = request.Request(self.url, data=corpo, method="POST",
                              headers={"Content-Type": "application/json; charset=utf-8"})
        if self._auth:
            req.add_header("Authorization", self._auth)
        try:
            with request.urlopen(req, timeout=self.timeout) as r:
                r.read()
            self.falhas = 0
            return True
        except Exception as e:
            if hasattr(e, "close"):  # HTTPError (401, 500) guarda a resposta aberta
                e.close()
            self.falhas += 1
            log.warning("Vila: evento %s não enviado (%s)", evento["tipo"], self._descrever(e))
            if self.falhas >= FALHAS_MAX:
                self.desistiu = True
                log.warning("Vila: %d falhas seguidas, não tento mais nesta execução (eventos em %s)",
                            FALHAS_MAX, self.pasta / PENDENTES)
            return False

    def _descrever(self, e):
        codigo = getattr(e, "code", None)
        if codigo:
            return f"HTTP {codigo}"
        motivo = getattr(e, "reason", None) or e
        nome = "timeout" if "timed out" in str(motivo).lower() or isinstance(motivo, TimeoutError) \
            else motivo.__class__.__name__
        return self._sem_senha(nome)

    def _sem_senha(self, texto):
        return texto.replace(self._senha, "***") if self._senha else texto

    def _pendente(self, evento):
        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            with open(self.pasta / PENDENTES, "a", encoding="utf-8") as f:
                f.write(json.dumps(evento, ensure_ascii=False) + "\n")
        except Exception as e:
            log.warning("Vila: não consegui guardar o evento pendente (%s)", e.__class__.__name__)

    # --- tarefa em andamento (para os módulos que não conhecem a tarefa) ---
    def tarefa(self, tarefa_id, processo_id=None):
        self._tarefa = {"tarefa_id": tarefa_id, "processo_id": processo_id}

    def processo(self, processo_id):
        if self._tarefa:
            self._tarefa["processo_id"] = processo_id

    def extra(self, **dados):
        """Campos que vão no evento de fim da tarefa (ex.: campos, orgao_novo)."""
        if self._tarefa:
            self._tarefa.setdefault("extra", {}).update(dados)

    def etapa(self, etapa, fim=False, **dados):
        if not self._tarefa:
            return None
        base = {"tarefa_id": self._tarefa.get("tarefa_id"), "processo_id": self._tarefa.get("processo_id")}
        if fim:
            dados = {**self._tarefa.get("extra", {}), **dados}
            self._tarefa = {}
        return self.emitir("tarefa", **base, etapa=etapa, **dados)


def _limpar(evento):
    """Tira chaves proibidas e qualquer texto no formato CNJ (proteção extra; o fluxo já não manda)."""
    limpo = {}
    for chave, valor in evento.items():
        if chave in PROIBIDAS:
            log.warning("Vila: campo '%s' retirado do evento %s (dado de cliente)", chave, evento.get("tipo"))
            continue
        if chave == "campos":
            valor = [c for c in valor if c in CAMPOS]
        limpo[chave] = _sem_cnj(valor)
    return limpo


def _sem_cnj(valor):
    if isinstance(valor, str):
        return CNJ_TEXTO.sub("[removido]", valor)
    if isinstance(valor, dict):
        return _limpar(valor)
    if isinstance(valor, list):
        return [_sem_cnj(v) for v in valor]
    return valor


def pxe_id(link):
    """tarefa_id da vila = pxe_id do link da tarefa (nunca o texto da tarefa)."""
    ids = parse_qs(urlparse(link or "").query).get("pxe_id", [])
    return ids[0] if ids else None


# --- instância da execução (main.py inicia; os módulos só chamam emitir/etapa) ---
_atual = Vila()


def iniciar(caminho_env=".env", envio=None):
    """Lê VILA_URL, VILA_USUARIO, VILA_SENHA, VILA_TIMEOUT e SAIDA_PASTA do .env. Nunca levanta exceção."""
    global _atual
    try:
        load_dotenv(caminho_env, override=True)
        try:
            timeout = float(os.getenv("VILA_TIMEOUT", "").strip() or TIMEOUT_PADRAO)
        except ValueError:
            timeout = TIMEOUT_PADRAO
        _atual = Vila(os.getenv("VILA_URL", ""), os.getenv("VILA_SENHA", ""),
                      os.getenv("VILA_USUARIO", "").strip() or BOT,
                      os.getenv("SAIDA_PASTA", "").strip() or "saida", timeout, envio)
        if _atual.ligada:
            log.info("Vila ligada: eventos do envio %s", _atual.envio)
    except Exception as e:
        log.warning("Vila desligada: configuração inválida (%s)", e.__class__.__name__)
        _atual = Vila()
    return _atual


def atual():
    return _atual


def emitir(tipo, **dados):
    return _atual.emitir(tipo, **dados)


def etapa(nome, fim=False, **dados):
    return _atual.etapa(nome, fim, **dados)


def extra(**dados):
    _atual.extra(**dados)


# --- códigos curtos (nunca o texto da tarefa ou da exceção) ---
def motivo_classificacao(classe, motivo):
    """Código do motivo da classificação (bot/classificacao.py)."""
    m = motivo or ""
    if "não é tarefa" in m:
        return "outro_tipo"
    if "previdência privada" in m:
        return "previdencia_privada"
    if "outra área" in m and not m.startswith("sem "):
        return "outra_area"
    if m.startswith("sem ") and ", mas com " in m:
        return "sinal_sem_previdenci"
    if m.startswith("sem "):
        return "sem_sinal_previdenciario"
    return None


# (texto da exceção, código), na ordem em que são testados
_MOTIVOS = [
    ("comprovante de protocolo, achei 0", "sem_comprovante"),
    ("comprovante de protocolo, achei", "mais_de_um_comprovante"),
    ("PDF sem texto", "pdf_sem_texto"),
    ("não consegui baixar o comprovante", "comprovante_nao_baixou"),
    ("não devolveu um PDF", "comprovante_nao_e_pdf"),
    ("mais de um valor no PDF", "dado_duplicado_no_pdf"),
    ("não encontrado no PDF", "dado_ausente_no_pdf"),
    ("o PDF é do processo", "cnj_diferente_do_processo"),
    ("campo já preenchido com outro valor", "campo_com_outro_valor"),
    ("não é do processo aberto", "processo_diferente_na_edicao"),
    ("não existe no campo", "orgao_nao_apareceu"),
    ("a opção não apareceu na lista", "orgao_nao_apareceu"),
    ("aviso que o bot não responde", "aviso_inesperado"),
    ("continuou mostrando avisos", "aviso_inesperado"),
    ("conferência depois de gravar falhou", "releitura_divergente"),
    ("não consegui reler a tela", "releitura_falhou"),
    ("abriu outra janela", "outra_janela"),
    ("não tem id do processo", "sem_id_do_processo"),
    ("bloqueio de envios inativo", "bloqueio_inativo"),
    ("e a tela mostra", "preenchimento_divergente"),
    ("esperado 1", "elemento_nao_unico"),
    ("não apareceu", "elemento_nao_apareceu"),
    ("não abriu a tela de edição", "elemento_nao_apareceu"),
]


def motivo_erro(erro):
    texto = str(erro)
    for trecho, codigo in _MOTIVOS:
        if trecho in texto:
            return codigo
    return "excecao"
