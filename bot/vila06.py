"""Vila 06 · bot do Previdenciário (bot-previdenciario, RN28): a cena só assiste.

O servidor da vila (este Flask) pergunta ao bot `GET /vila/estado` com o token e repassa à página só o que a
cena usa: horário, conexão, contagens do dia e eventos novos (n, tipo, horário). O token nunca vai ao navegador.

.env deste repositório:
- VILA06_URL          endereço do bot (ex.: https://192.168.0.20:3000). Vazio = modo simulado.
- VILA06_TOKEN        o mesmo VILA_TOKEN do .env do bot (24+ caracteres).
- VILA06_CERTIFICADO  certificado próprio do bot (RN22.4) para conferir o HTTPS; vazio = autoridades públicas.
- VILA06_CLIPES       pasta dos vídeos da cena (fora do git); padrão: <pasta de saída>/vila06_clipes.
                      Os sons (voz das falas, música, ambiente e efeitos) ficam em <VILA06_CLIPES>/sons/, gerados por
                      doc/vila/gerar_sons_vila06.py.
"""
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

# vídeos da cena: só estes nomes são servidos (nada de caminho vindo do navegador)
CLIPES = ("plantao", "fora", "chegou", "respondendo", "equipe")
# retratos da caixa de diálogo (uma imagem por expressão), na mesma pasta dos vídeos, também fora do git
RETRATOS = ("neutro", "alerta", "firme", "sereno")
# sons da cena, em <pasta dos vídeos>/sons/<nome>.mp3: música, ambiente, efeitos e a voz de cada fala
SONS = ("musica", "ambiente", "sfx-gancho", "sfx-gas", "sfx-corte", "sfx-esquiva", "sfx-pouso", "sfx-vapor",
        "sfx-passo", "sfx-canhao", "sfx-sino")
FALA = re.compile(r"fala-[0-9a-f]{8}")  # fala-<hash FNV-1a do texto>, o mesmo cálculo da página
MAX_SONS = 300
TIPOS = ("respondeu", "encaminhou", "nao_entendeu")
CONEXOES = ("conectado", "reconectando", "desconectado")
TEMPO_LIMITE = 4  # segundos


def configuracao(pasta_saida):
    clipes = os.path.expanduser(os.getenv("VILA06_CLIPES", "").strip()) or str(Path(pasta_saida) / "vila06_clipes")
    return {
        "url": os.getenv("VILA06_URL", "").strip().rstrip("/"),
        "token": os.getenv("VILA06_TOKEN", "").strip(),
        "certificado": os.path.expanduser(os.getenv("VILA06_CERTIFICADO", "").strip()),
        "clipes": Path(clipes),
    }


def caminho_clipe(pasta, nome):
    """Arquivo do clipe, ou None se o nome não é da lista ou o vídeo não foi instalado."""
    if nome not in CLIPES:
        return None
    arq = Path(pasta) / f"{nome}.mp4"
    return arq if arq.is_file() else None


def clipes_instalados(pasta):
    return [n for n in CLIPES if caminho_clipe(pasta, n)]


def caminho_retrato(pasta, nome):
    """retrato-<nome>.png da pasta dos vídeos, ou None (nome fora da lista ou imagem não instalada)."""
    if nome not in RETRATOS:
        return None
    arq = Path(pasta) / f"retrato-{nome}.png"
    return arq if arq.is_file() else None


def retratos_instalados(pasta):
    return [n for n in RETRATOS if caminho_retrato(pasta, n)]


def caminho_som(pasta, nome):
    """sons/<nome>.mp3 da pasta dos vídeos, ou None (nome fora da lista/padrão ou som não instalado)."""
    if nome not in SONS and not FALA.fullmatch(nome or ""):
        return None
    arq = Path(pasta) / "sons" / f"{nome}.mp3"
    return arq if arq.is_file() else None


def sons_instalados(pasta):
    pasta_sons = Path(pasta) / "sons"
    if not pasta_sons.is_dir():
        return []
    return sorted(p.stem for p in pasta_sons.glob("*.mp3") if caminho_som(pasta, p.stem))[:MAX_SONS]


def _inteiro(v, minimo=0):
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= minimo else minimo


def limpar(bruto):
    """Repassa só os campos conhecidos, com tipo conferido (o que vier a mais do bot não chega à página)."""
    hoje = bruto.get("hoje") if isinstance(bruto.get("hoje"), dict) else {}
    eventos = []
    for e in bruto.get("eventos") or []:
        if isinstance(e, dict) and e.get("tipo") in TIPOS and isinstance(e.get("n"), int):
            eventos.append({"n": e["n"], "tipo": e["tipo"], "em": str(e.get("em", ""))[:30]})
    return {
        "fonte": "bot",
        "horario": "fechado" if bruto.get("horario") == "fechado" else "aberto",
        "conexao": bruto.get("conexao") if bruto.get("conexao") in CONEXOES else "reconectando",
        "modo": bruto.get("modo") if bruto.get("modo") in ("teste", "producao", "aprendizado") else "teste",
        "hoje": {k: _inteiro(hoje.get(k)) for k in ("respondidas", "encaminhadas", "naoEntendidas")},
        "comEquipe": _inteiro(bruto.get("comEquipe")),
        "ultimo": _inteiro(bruto.get("ultimo")),
        "eventos": eventos[:50],
    }


def simulado(desde=None, agora=None):
    """Sem VILA06_URL: um evento a cada 20 s (respondeu, respondeu, encaminhou, não entendeu...), para ver a cena."""
    agora = time.time() if agora is None else agora
    ultimo = int(agora // 20)
    ciclo = ("respondeu", "respondeu", "encaminhou", "respondeu", "nao_entendeu")
    eventos = []
    if desde and 0 < desde < ultimo:
        for n in range(max(desde + 1, ultimo - 5), ultimo + 1):
            eventos.append({"n": n, "tipo": ciclo[n % len(ciclo)], "em": ""})
    hora = time.localtime(agora).tm_hour
    feitos = ultimo % 37
    return {
        "fonte": "simulado",
        "horario": "aberto" if 8 <= hora < 18 else "fechado",
        "conexao": "conectado",
        "modo": "teste",
        "hoje": {"respondidas": 12 + feitos, "encaminhadas": 3 + feitos // 4, "naoEntendidas": 1 + feitos // 9},
        "comEquipe": feitos % 3,
        "ultimo": ultimo,
        "eventos": eventos,
    }


def estado(conf, desde=None, abrir=urllib.request.urlopen):
    """Estado para a página. Sem URL ou token = simulado; bot fora do ar ou token recusado = fonte "erro"."""
    if not conf["url"] or not conf["token"]:
        return simulado(desde)
    url = conf["url"] + "/vila/estado" + (f"?desde={int(desde)}" if desde else "")
    pedido = urllib.request.Request(url, headers={"Authorization": "Bearer " + conf["token"], "Accept": "application/json"})
    contexto = None
    if url.startswith("https://"):
        contexto = ssl.create_default_context(cafile=conf["certificado"] or None)
        if conf["certificado"]:
            contexto.check_hostname = False  # certificado próprio, emitido para o IP da rede interna (RN22.4)
    try:
        with abrir(pedido, timeout=TEMPO_LIMITE, context=contexto) as r:
            return limpar(json.loads(r.read(200_000).decode("utf-8")))
    except (urllib.error.URLError, OSError, ValueError) as e:
        motivo = "token recusado" if isinstance(e, urllib.error.HTTPError) and e.code in (401, 429) else "bot fora do ar"
        return {"fonte": "erro", "erro": motivo, "horario": "aberto", "conexao": "desconectado", "modo": "teste",
                "hoje": {"respondidas": 0, "encaminhadas": 0, "naoEntendidas": 0}, "comEquipe": 0,
                "ultimo": int(desde or 0), "eventos": []}
