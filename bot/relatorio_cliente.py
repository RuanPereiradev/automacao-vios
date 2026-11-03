"""Relatório para o cliente: um PDF por Grupo Cliente com os 13 campos de cada processo.

Entrada: os <GRUPO>.json do relatorio_processos.py (saida_usuario2/relatorios/AAAA-MM-DD/<GRUPO>.json),
uma lista de processos capturados no VIOS (com a ficha de cada um).
Saída: "<GRUPO>.pdf" na mesma pasta.

Divisão de trabalho:
- código: lê o .json, monta os campos (bot/campos_relatorio.py), tira links, senhas e dados internos
  e gera o PDF (bot/pdf_relatorio.py);
- IA (opcional: --ia ou RELATORIO_IA=true): escreve resumo, pendência e financeira. Sem IA (padrão)
  nada sai da máquina e não há gasto.
Não acessa o VIOS.
"""
import importlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from bot import campos_relatorio, custo, ia
from bot.analise import MODELO_PADRAO
from bot.ia import IAErro

log = logging.getLogger(__name__)

PASTA_DIA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# nomes que o Windows não aceita como nome de arquivo
RESERVADOS = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
VERDADE = {"1", "true", "sim", "s", "yes", "y", "on"}

CHAVES = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


class ErroFatal(IAErro):
    """Erro que vale para todos os grupos (chave, modelo, créditos, prompt): para a execução."""


# ---- arquivos ----

def nome_relatorio(arquivo):
    """<pasta>/<GRUPO>.json -> <pasta>/<GRUPO>.pdf (nome aceito pelo Windows)."""
    arquivo = Path(arquivo)
    base = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "-", arquivo.stem).strip().rstrip(". ") or "grupo"
    # o Windows olha a parte antes do 1º ponto: "CON.pdf" e "CON.X.pdf" são dispositivos
    antes, ponto, resto = base.partition(".")
    if antes.rstrip().upper() in RESERVADOS:
        base = antes.rstrip() + "_" + ponto + resto
    return arquivo.with_name(base + ".pdf")


def caminho_env(nome):
    """Caminho de uma variável do .env, igual ao relatorio_processos.py.

    Tira aspas e aceita "~/...", $HOME e %USERPROFILE%. Vazio = None."""
    texto = os.getenv(nome, "").strip().strip("\"'").strip()
    if not texto:
        return None
    return Path(os.path.expandvars(os.path.expanduser(texto)))


def pasta_padrao():
    """Pasta do dia mais recente em RELATORIO_PASTA (vazio = <SAIDA_PASTA>/relatorios)."""
    raiz = caminho_env("RELATORIO_PASTA")
    if raiz is None:
        # SAIDA_PASTA lido do mesmo jeito que o bot/config.py
        raiz = Path(os.getenv("SAIDA_PASTA", "saida").strip() or "saida") / "relatorios"
    if not raiz.is_dir():
        return None
    dias = sorted(p for p in raiz.iterdir() if p.is_dir() and PASTA_DIA.match(p.name))
    return dias[-1] if dias else None


def arquivos_json(caminhos):
    """Lista os .json dos caminhos (arquivo .json, pasta, ou o .txt do grupo -> .json ao lado)."""
    arquivos = []
    for c in caminhos:
        c = Path(c)
        if c.is_dir():
            arquivos += sorted(p for p in c.glob("*.json") if p.is_file())
        elif c.suffix.lower() == ".json" and c.is_file():
            arquivos.append(c)
        elif c.suffix.lower() == ".txt" and c.with_suffix(".json").is_file():
            arquivos.append(c.with_suffix(".json"))
        else:
            log.error("Não é um .json de grupo nem uma pasta: %s", c)
    return arquivos


def precisa_gerar(arquivo, pdf, refazer=False):
    """Gera de novo se pediu --refazer, se o PDF não existe ou se o .json é mais novo."""
    return refazer or not pdf.exists() or pdf.stat().st_mtime < arquivo.stat().st_mtime


def ler_registros(arquivo):
    """Lista de processos do .json (contrato do relatorio_processos.py). Outro formato: ValueError."""
    dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    if isinstance(dados, dict) and isinstance(dados.get("processos"), list):
        dados = dados["processos"]
    if not isinstance(dados, list) or not all(isinstance(r, dict) for r in dados):
        raise ValueError("não é uma lista de processos")
    return dados


# ---- IA ----

def ia_ligada(pedido=None):
    """--ia na linha de comando ou RELATORIO_IA=true no .env. Padrão: sem IA."""
    if pedido is not None:
        return bool(pedido)
    return os.getenv("RELATORIO_IA", "").strip().lower() in VERDADE


def carregar_prompt():
    """Prompt do .env (RELATORIO_CLIENTE_PROMPT = caminho de um arquivo) ou o padrão do campos_relatorio."""
    arquivo = caminho_env("RELATORIO_CLIENTE_PROMPT")
    if arquivo is None:
        return campos_relatorio.PROMPT_IA
    if not arquivo.is_file():
        raise ErroFatal(f"RELATORIO_CLIENTE_PROMPT: arquivo não encontrado: {arquivo}")
    return arquivo.read_text(encoding="utf-8")


def provedor_do_env():
    """(provedor, modelo, esforço) do .env já carregado."""
    provedor = os.getenv("LLM_PROVEDOR", "openai").strip().lower() or "openai"
    modelo = os.getenv("LLM_MODELO", "").strip() or MODELO_PADRAO.get(provedor, "")
    esforco = os.getenv("LLM_ESFORCO", "low").strip()
    return provedor, modelo, esforco


def criar_ia(provedor, modelo, esforco):
    """Cria o cliente da IA. Sem chave no .env: para com mensagem clara."""
    chave = CHAVES.get(provedor)
    if chave and not os.getenv(chave, "").strip():
        raise ErroFatal(f"{chave} vazia no .env: preencher a chave da API ({provedor}) ou rodar sem --ia")
    try:
        return ia.criar(provedor, modelo, esforco)
    except IAErro as e:
        raise ErroFatal(str(e)) from e


def _erro_fatal(provedor, e):
    """Mesma regra do bot/analise.py: chave, modelo ou créditos valem para todos os grupos."""
    nome = type(e).__name__
    if nome in ("AuthenticationError", "PermissionDeniedError"):
        raise ErroFatal(f"Chave da API recusada ({provedor}): conferir {CHAVES.get(provedor, 'a chave')} no .env") from e
    if nome == "NotFoundError":
        raise ErroFatal(f"Modelo não encontrado ({provedor}): conferir LLM_MODELO no .env") from e
    if any(m in str(e).lower() for m in ("insufficient_quota", "credit_balance", "credit balance",
                                         "billing_hard_limit", "billing hard limit")):
        raise ErroFatal(f"Sem créditos na API da IA ({provedor}): adicionar créditos e rodar de novo") from e


# ---- PDF ----

def _gerar_pdf(*args, **kwargs):
    # import na hora: o PDF é outro módulo (e nos testes é trocado por um falso)
    return importlib.import_module("bot.pdf_relatorio").gerar_pdf(*args, **kwargs)


def escrever(arquivo, cliente=None, modelo="", gasto=None, prompt=None, ao_falhar=None):
    """Gera o PDF de um .json. Devolve (caminho do PDF, número de processos, observações)."""
    registros = ler_registros(arquivo)
    grupo = next((str(r.get("grupo")).strip() for r in registros if str(r.get("grupo") or "").strip()), arquivo.stem)
    capturado = datetime.fromtimestamp(arquivo.stat().st_mtime)
    observacoes = [f"Dados do sistema do escritório (VIOS) em {capturado:%d/%m/%Y às %H:%M}."]
    if not registros:
        observacoes.append("Nenhum processo encontrado para o grupo.")
    linhas = campos_relatorio.montar_linhas(registros, ia=cliente, gasto=gasto, modelo=modelo, prompt=prompt,
                                            observacoes=observacoes, ao_falhar=ao_falhar)
    extra = {}
    encerrados = sum(1 for r in registros if campos_relatorio.encerrado(r))
    if encerrados:
        # capa do PDF: "Total de processos: N (X em andamento, Y encerrados)"
        extra["encerrados"] = encerrados
    pdf = _gerar_pdf(nome_relatorio(arquivo), grupo, linhas, datetime.now(), observacoes, **extra)
    return Path(pdf or nome_relatorio(arquivo)), len(linhas), observacoes


def gerar(caminhos, refazer=False, usar_ia=None, cliente=None, gasto=None):
    """Gera o PDF de cada .json. Devolve (feitos, pulados, falhas).

    usar_ia: True/False (--ia); None = RELATORIO_IA do .env. Sem IA é o padrão.
    cliente = provedor de IA já criado (nos testes, um falso); vazio = cria pelo .env só se
    houver algum grupo para gerar. Erro num grupo: loga e segue.
    Falha da IA: o grupo sai sem IA; erro de chave/créditos desliga a IA para os grupos seguintes.
    O motivo do erro fica só no log: o PDF vai para o cliente e recebe só um aviso neutro.
    """
    usar_ia = ia_ligada(usar_ia)
    provedor, modelo, esforco = provedor_do_env()
    prompt = None
    if usar_ia:
        gasto = gasto or custo.Gasto.do_env()
        prompt = carregar_prompt()
    fatal = []

    def ao_falhar(e):
        try:
            _erro_fatal(provedor, e)
        except ErroFatal as erro:
            fatal.append(str(erro))

    feitos, pulados, falhas = 0, 0, 0
    for arquivo in arquivos_json(caminhos):
        pdf = nome_relatorio(arquivo)
        if not precisa_gerar(arquivo, pdf, refazer):
            log.info("%s: relatório já existe e está em dia (--refazer gera de novo)", pdf.name)
            pulados += 1
            continue
        if usar_ia and cliente is None:
            cliente = criar_ia(provedor, modelo, esforco)
            log.info("IA: %s / %s", provedor, modelo)
        try:
            pdf, total, observacoes = escrever(arquivo, cliente if usar_ia else None, modelo, gasto, prompt,
                                               ao_falhar)
        except Exception:
            log.exception("%s: falha ao gerar o relatório", arquivo.name)
            falhas += 1
            continue
        if fatal and usar_ia:
            # os próximos PDFs saem sem IA, com o aviso neutro do campos_relatorio
            log.error("IA desligada para o resto da execução: %s", fatal[-1])
            usar_ia = False
        log.info("%s -> %s (%d processos)", arquivo.name, pdf, total)
        feitos += 1
    if gasto is not None:
        log.info("Gasto estimado com a IA: %s", gasto.resumo())
    return feitos, pulados, falhas
