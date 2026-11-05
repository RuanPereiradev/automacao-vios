"""Orelha (relatório do dia, só lendo o VIOS) visto pelo Sam: o horário e o arquivo dos relatórios.

O Orelha roda sozinho pelo agendamento (cron ou launchd) na pasta orelha/ deste repositório (ou em
ORELHA_PASTA). O Sam não roda o Orelha: só lê o que está na pasta dele, sem importar nada de lá:
- o horário do agendamento (ORELHA_HORARIO e ORELHA_HORARIO_PARADOS do orelha/.env), para a vila e a
  página avisarem quando o relatório roda, quando sai o próximo e se o de hoje ainda não saiu;
- os relatórios já feitos (orelha/saida/<AAAA-MM-DD>/), para a página /orelha guardar e abrir cada um.

O /orelha/status (que vai para a vila) leva só datas e contagens. O texto dos relatórios (nomes de
clientes e da equipe) só aparece na página /orelha e nos arquivos, atrás da senha das páginas.

Formato do horário: "<dias> <HH:MM>", e mais de um separado por ";". Dias: seg, ter, qua, qui, sex,
sab, dom, com faixa ("seg-sex") ou lista ("seg,qua,sex"). Ex.: "seg-sex 07:30".
"""
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import dotenv_values

ENV = ".env"
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "orelha"
HORARIO_PADRAO = "seg-sex 07:30"
PARADOS_PADRAO = "sab 08:00"
ARQUIVOS = {"relatorio.html": "text/html", "relatorio.pdf": "application/pdf"}
DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
NOMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
ATRASO = timedelta(minutes=45)  # depois disto, o relatório da hora marcada já devia ter saído
_PASTA_DIA = re.compile(r"^(simulado-)?(\d{4}-\d{2}-\d{2})$")


class HorarioErro(ValueError):
    pass


def pasta(valor=None):
    """Pasta do Orelha: ORELHA_PASTA do .env do Sam ou a pasta orelha/ deste repositório."""
    valor = os.path.expanduser((valor if valor is not None else os.getenv("ORELHA_PASTA", "")).strip())
    return Path(valor) if valor else PASTA_PADRAO


def configurado(pasta):
    return bool(pasta) and (Path(pasta) / "main.py").exists()


def _env(pasta):
    arquivo = Path(pasta) / ENV
    return dotenv_values(arquivo) if arquivo.exists() else {}


def pasta_saida(pasta):
    """ORELHA_SAIDA do orelha/.env (relativa a orelha/), padrão orelha/saida."""
    valor = os.path.expanduser((_env(pasta).get("ORELHA_SAIDA") or "").strip() or "saida")
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else Path(pasta) / caminho


# --- horário -------------------------------------------------------------------------------------

def _sem_acento(texto):
    return texto.lower().replace("á", "a").replace("ç", "c").replace("é", "e")


def _dias(texto):
    dias = set()
    for parte in _sem_acento(texto).split(","):
        parte = parte.strip()[:3] if "-" not in parte else parte.strip()
        if "-" in parte:
            a, b = (p.strip()[:3] for p in parte.split("-", 1))
            if a not in DIAS or b not in DIAS:
                raise HorarioErro(f"dia desconhecido em {texto!r} (use {', '.join(DIAS)})")
            i, j = DIAS.index(a), DIAS.index(b)
            dias.update(DIAS.index(DIAS[k % 7]) for k in range(i, (j if j >= i else j + 7) + 1))
        elif parte in DIAS:
            dias.add(DIAS.index(parte))
        else:
            raise HorarioErro(f"dia desconhecido em {texto!r} (use {', '.join(DIAS)})")
    return dias


def ler_horario(texto):
    """'seg-sex 07:30; sab 09:00' -> [({0,1,2,3,4}, 7, 30), ({5}, 9, 0)]. Vazio -> []."""
    regras = []
    for item in (texto or "").split(";"):
        item = item.strip()
        if not item:
            continue
        m = re.match(r"^(.+?)\s+(\d{1,2})(?:[:h](\d{2})|h)$", item)
        if not m:
            raise HorarioErro(f"horário inválido {item!r} (ex.: seg-sex 07:30)")
        h, mi = int(m.group(2)), int(m.group(3) or 0)
        if h > 23 or mi > 59:
            raise HorarioErro(f"hora inválida em {item!r}")
        regras.append((_dias(m.group(1)), h, mi))
    return regras


def hora(h, mi):
    return f"{h}h{mi:02d}" if mi else f"{h}h"


def descrever(regras):
    """[({0..4}, 7, 30)] -> 'de segunda a sexta às 7h30'."""
    partes = []
    for dias, h, mi in regras:
        d = sorted(dias)
        if len(d) == 7:
            quando = "todo dia"
        elif len(d) > 2 and d == list(range(d[0], d[-1] + 1)):
            quando = f"de {NOMES[d[0]]} a {NOMES[d[-1]]}"
        elif len(d) == 1:
            quando = ("aos " if d[0] >= 5 else "às ") + NOMES[d[0]] + "s"
        else:
            quando = ", ".join(NOMES[x] for x in d[:-1]) + " e " + NOMES[d[-1]]
        partes.append(f"{quando} às {hora(h, mi)}")
    return "; ".join(partes)


def _vezes(regras, inicio, fim):
    """Horários marcados de inicio a fim (datetimes), em ordem."""
    saida, dia = [], inicio.date()
    while dia <= fim.date():
        for dias, h, mi in regras:
            quando = datetime(dia.year, dia.month, dia.day, h, mi)
            if dia.weekday() in dias and inicio <= quando <= fim:
                saida.append(quando)
        dia += timedelta(days=1)
    return sorted(saida)


def proxima(regras, agora):
    vezes = _vezes(regras, agora + timedelta(seconds=1), agora + timedelta(days=8))
    return vezes[0] if vezes else None


def anterior(regras, agora):
    vezes = _vezes(regras, agora - timedelta(days=8), agora)
    return vezes[-1] if vezes else None


def quando(momento, agora):
    """'hoje às 7h30', 'amanhã (sexta) às 7h30' ou 'segunda, 10/11, às 7h30'."""
    dias = (momento.date() - agora.date()).days
    h = hora(momento.hour, momento.minute)
    if dias == 0:
        return f"hoje às {h}"
    if dias == 1:
        return f"amanhã ({NOMES[momento.weekday()]}) às {h}"
    return f"{NOMES[momento.weekday()]}, {momento:%d/%m}, às {h}"


# --- arquivo dos relatórios ----------------------------------------------------------------------

def _resumo(pasta_dia):
    try:
        dados = json.loads((pasta_dia / "resumo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    graves = atencao = 0
    for s in dados.get("secoes") or []:
        por = s.get("por_nivel") or {}
        graves += int(por.get("grave") or 0)
        atencao += int(por.get("atencao") or 0)
    return {"gerado_em": dados.get("gerado_em"), "graves": graves, "atencao": atencao,
            "erros": [str(e) for e in dados.get("erros") or []],
            "funcoes": [s.get("chave") for s in dados.get("secoes") or [] if s.get("chave")]}


def relatorios(pasta):
    """Relatórios já feitos, do mais novo para o mais antigo: [{"pasta": "2026-11-04", "data":
    date, "simulado": False, "html": True, "pdf": True, "planilhas": "planilhas-2026-11-04.csv" | None,
    "gerado_em": "...", "graves": n, "atencao": n, "erros": [...], "funcoes": [...]}]."""
    base = pasta_saida(pasta)
    if not base.is_dir():
        return []
    saida = []
    for item in base.iterdir():
        m = _PASTA_DIA.match(item.name)
        if not m or not item.is_dir() or not (item / "relatorio.html").exists():
            continue
        try:
            dia = date.fromisoformat(m.group(2))
        except ValueError:
            continue
        csv = next(iter(sorted(item.glob("planilhas-*.csv"))), None)
        saida.append({"pasta": item.name, "data": dia, "simulado": bool(m.group(1)),
                      "html": True, "pdf": (item / "relatorio.pdf").exists(),
                      "planilhas": csv.name if csv else None, **_resumo(item)})
    return sorted(saida, key=lambda r: (r["data"], r.get("gerado_em") or ""), reverse=True)


def arquivo(pasta, nome_pasta, nome):
    """Caminho de um arquivo do relatório (só relatorio.html, relatorio.pdf ou a planilha .csv
    daquela pasta do dia), ou None."""
    if not _PASTA_DIA.match(nome_pasta or ""):
        return None
    if nome not in ARQUIVOS and not re.match(r"^planilhas-\d{4}-\d{2}-\d{2}\.csv$", nome or ""):
        return None
    caminho = pasta_saida(pasta) / nome_pasta / nome
    return caminho if caminho.is_file() else None


# --- situação (vai para a vila: só datas e contagens) --------------------------------------------

def status(pasta, agora=None):
    agora = agora or datetime.now()
    info = {"configurado": configurado(pasta), "horario": "", "horario_texto": "", "parados_texto": "",
            "proximo": None, "proximo_texto": "", "atrasado": False, "atrasado_texto": "",
            "total": 0, "ultimo": None, "aviso": "", "erro_horario": ""}
    if not info["configurado"]:
        return info
    env = _env(pasta)
    texto = (env.get("ORELHA_HORARIO") or "").strip() or HORARIO_PADRAO
    parados = (env.get("ORELHA_HORARIO_PARADOS") or "").strip() or PARADOS_PADRAO
    try:
        regras = ler_horario(texto)
    except HorarioErro as e:
        info["erro_horario"] = f"ORELHA_HORARIO: {e}"
        regras = ler_horario(HORARIO_PADRAO)
        texto = HORARIO_PADRAO
    try:
        info["parados_texto"] = descrever(ler_horario(parados)) if parados.lower() not in ("nao", "não", "-") else ""
    except HorarioErro as e:
        info["erro_horario"] = info["erro_horario"] or f"ORELHA_HORARIO_PARADOS: {e}"
    info["horario"], info["horario_texto"] = texto, descrever(regras)

    reais = [r for r in relatorios(pasta) if not r["simulado"]]
    info["total"] = len(reais)
    if reais:
        u = reais[0]
        info["ultimo"] = {"data": u["data"].isoformat(), "gerado_em": u.get("gerado_em"),
                          "graves": u.get("graves", 0), "atencao": u.get("atencao", 0), "erros": len(u.get("erros") or [])}

    prox = proxima(regras, agora)
    if prox:
        info["proximo"], info["proximo_texto"] = prox.isoformat(timespec="minutes"), quando(prox, agora)
    ant = anterior(regras, agora)
    feitos = {r["data"] for r in reais}
    if ant and agora - ant >= ATRASO and ant.date() not in feitos and ant.date() == agora.date():
        info["atrasado"] = True
        info["atrasado_texto"] = f"o relatório de hoje, das {hora(ant.hour, ant.minute)}, ainda não saiu"

    fala = f"Eu rodo {info['horario_texto']}"
    if info["parados_texto"]:
        fala += f", e os processos parados {info['parados_texto']}"
    fala += "."
    if info["atrasado"]:
        fala += f" Atenção: {info['atrasado_texto']}. Confira se o computador do Orelha estava ligado (logs/orelha.log)."
    elif prox:
        fala += f" O próximo relatório sai {info['proximo_texto']}."
    if info["total"]:
        fala += f" Tenho {info['total']} relatório(s) guardado(s) no arquivo."
    info["aviso"] = fala
    return info
