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
import logging
import os
import re
import subprocess
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import dotenv_values

log = logging.getLogger("ultron")
ENV = ".env"
PASTA_PADRAO = Path(__file__).resolve().parent.parent / "orelha"
HORARIO_PADRAO = "seg-sex 07:30"
PARADOS_PADRAO = "sab 08:00"
ARQUIVOS = {"relatorio.html": "text/html", "relatorio.pdf": "application/pdf",
            "painel-semanal.html": "text/html", "painel-semanal.pdf": "application/pdf",
            "semana.html": "text/html"}
PAINEL_ARQUIVO = "painel-rodando.json"  # orelha/saida/: quem está gerando o painel agora
PAINEL_LOG = "painel_sam.log"
_trava = threading.Lock()
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
    numeros = {}
    for s in dados.get("secoes") or []:
        if s.get("chave") and isinstance(s.get("numeros"), dict):
            numeros[s["chave"]] = s["numeros"]
        por = s.get("por_nivel") or {}
        graves += int(por.get("grave") or 0)
        atencao += int(por.get("atencao") or 0)
    return {"gerado_em": dados.get("gerado_em"), "graves": graves, "atencao": atencao,
            "erros": [str(e) for e in dados.get("erros") or []], "numeros": numeros,
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
                      "semana": (item / "semana.html").exists(),
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


def _n(numeros, secao, campo):
    """Contagem inteira (>= 0) de numeros[secao][campo]; ausente ou inválido = 0."""
    try:
        return max(0, int((numeros.get(secao) or {}).get(campo) or 0))
    except (AttributeError, TypeError, ValueError):
        return 0


def cena(relatorio):
    """Contrato "cena" da Vila 05: só datas e CONTAGENS do relatório real mais recente (nunca nomes,
    nunca por_responsavel/por_area). None sem relatório real."""
    if not relatorio:
        return None
    n = relatorio.get("numeros") or {}
    return {"data": relatorio["data"].isoformat(), "gerado_em": relatorio.get("gerado_em"),
            "atrasadas": _n(n, "prazos", "atrasadas"), "graves": _n(n, "prazos", "graves"),
            "vencem_hoje": _n(n, "prazos", "vencem_hoje"),
            "intimacoes": _n(n, "intimacoes", "esquecidas"), "intimacoes_graves": _n(n, "intimacoes", "graves"),
            "parados": _n(n, "parados", "parados"), "parados_graves": _n(n, "parados", "graves"),
            "audiencias_hoje": _n(n, "agenda", "audiencias_hoje"), "pericias_hoje": _n(n, "agenda", "pericias_hoje"),
            "erros": len(relatorio.get("erros") or []),
            "funcoes": [str(f) for f in relatorio.get("funcoes") or []]}


# --- situação (vai para a vila: só datas e contagens) --------------------------------------------

def status(pasta, agora=None):
    agora = agora or datetime.now()
    info = {"configurado": configurado(pasta), "horario": "", "horario_texto": "", "parados_texto": "",
            "proximo": None, "proximo_texto": "", "atrasado": False, "atrasado_texto": "",
            "total": 0, "ultimo": None, "aviso": "", "erro_horario": "", "cena": None}
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

    info["cena"] = cena(reais[0] if reais else None)

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


# --- painel semanal (botão da página /orelha) -----------------------------------------------------
# O painel (peças + audiências, PDF no papel timbrado) não roda por agendamento: a colaboradora aperta o
# botão quando quer. O Sam abre o Orelha com `--funcoes painel` (mesma .venv e .env do Orelha, só leitura
# do VIOS) e a página mostra quando termina. Só funciona se o Orelha estiver neste mesmo computador.

class PainelErro(Exception):
    pass


def _python(pasta):
    for caminho in (Path(pasta) / ".venv" / "bin" / "python", Path(pasta) / ".venv" / "Scripts" / "python.exe"):
        if caminho.exists():
            return caminho
    return Path(pasta) / ".venv" / "bin" / "python"


def _painel_pronto(pasta):
    return _python(pasta).exists() and (Path(pasta) / "main.py").exists() and (Path(pasta) / ".env").exists()


def _vivo(pid):
    """O processo existe e é o main.py do Orelha (não um pid reaproveitado)."""
    if pid <= 0:
        return False
    if os.name == "nt":  # no Windows os.kill(pid, 0) ENCERRA o processo: pergunta ao tasklist
        try:
            saida = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True,
                                   timeout=10).stdout
        except Exception:
            return True
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
    return "main.py" in cmd or not cmd.strip()


def _painel_atual(pasta):
    try:
        return json.loads((pasta_saida(pasta) / PAINEL_ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def paineis(pasta):
    """Painéis semanais já gerados, do mais novo para o mais antigo: [{"pasta", "data", "simulado",
    "html", "pdf", "gerado_em"}]."""
    base = pasta_saida(pasta)
    if not base.is_dir():
        return []
    saida = []
    for item in base.iterdir():
        m = _PASTA_DIA.match(item.name)
        if not m or not item.is_dir() or not (item / "painel-semanal.html").exists():
            continue
        try:
            dia = date.fromisoformat(m.group(2))
        except ValueError:
            continue
        html = item / "painel-semanal.html"
        saida.append({"pasta": item.name, "data": dia, "simulado": bool(m.group(1)), "html": True,
                      "pdf": (item / "painel-semanal.pdf").exists(),
                      "gerado_em": datetime.fromtimestamp(html.stat().st_mtime).isoformat(timespec="seconds")})
    return sorted(saida, key=lambda r: (r["data"], r["gerado_em"]), reverse=True)


def painel_status(pasta):
    """{"configurado", "rodando", "inicio", "ultimo"} (ultimo = o painel real mais novo ou None)."""
    info = {"configurado": configurado(pasta) and _painel_pronto(pasta), "rodando": False, "inicio": None,
            "ultimo": None}
    atual = _painel_atual(pasta)
    if atual and _vivo(int(atual.get("pid", 0))):
        info.update(rodando=True, inicio=atual.get("inicio"))
    reais = [p for p in paineis(pasta) if not p["simulado"]]
    if reais:
        u = reais[0]
        info["ultimo"] = {"pasta": u["pasta"], "data": u["data"].isoformat(), "gerado_em": u["gerado_em"], "pdf": u["pdf"]}
    return info


def rodar_painel(pasta, de=None, ate=None):
    """Abre o Orelha em segundo plano só com o painel semanal. de/ate (date) = período escolhido na página
    (None = o padrão do Orelha: de hoje até hoje + ORELHA_PAINEL_DIAS_FILA). Devolve o status; levanta PainelErro."""
    if de and ate and ate < de:
        raise PainelErro("a data final não pode ser antes da inicial")
    if not configurado(pasta):
        raise PainelErro("o Orelha não está neste servidor (ORELHA_PASTA)")
    if not _painel_pronto(pasta):
        raise PainelErro("o Orelha não está instalado aqui (falta .venv ou .env em orelha/)")
    pasta = Path(pasta)
    with _trava:
        if painel_status(pasta)["rodando"]:
            raise PainelErro("o painel já está sendo gerado; espere terminar")
        saida = pasta_saida(pasta)
        (pasta / "logs").mkdir(exist_ok=True)
        saida.mkdir(parents=True, exist_ok=True)
        ambiente = {k: os.environ[k] for k in ("PATH", "HOME", "USER", "LANG", "LC_ALL", "SYSTEMROOT", "TEMP", "TMP",
                                               "USERPROFILE", "LOCALAPPDATA") if k in os.environ}
        ambiente["PYTHONUTF8"] = "1"
        inicio = datetime.now().isoformat(timespec="seconds")
        arq_log = open(pasta / "logs" / PAINEL_LOG, "a", encoding="utf-8")
        periodo = f" · de {de:%d/%m/%Y}" if de else ""
        periodo += f" até {ate:%d/%m/%Y}" if ate else ""
        arq_log.write(f"\n===== {inicio} · painel semanal (pelo botão){periodo} =====\n")
        arq_log.flush()
        try:
            comando = [str(_python(pasta)), "main.py", "--funcoes", "painel"]
            if de:
                comando += ["--painel-de", de.isoformat()]
            if ate:
                comando += ["--painel-ate", ate.isoformat()]
            proc = subprocess.Popen(comando, cwd=pasta, env=ambiente,
                                    stdin=subprocess.DEVNULL, stdout=arq_log, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as e:
            raise PainelErro(f"não consegui abrir o Orelha: {e}")
        finally:
            arq_log.close()
        arquivo = saida / PAINEL_ARQUIVO
        arquivo.write_text(json.dumps({"pid": proc.pid, "inicio": inicio}), encoding="utf-8")
        log.info("Painel semanal do Orelha iniciado pelo botão, pid %d", proc.pid)

        def esperar():
            codigo = proc.wait()  # recolhe o processo (sem isso ele ficaria "zumbi" e pareceria vivo)
            log.info("Painel semanal do Orelha terminou (código %s)", codigo)
            try:
                if (_painel_atual(pasta) or {}).get("pid") == proc.pid:
                    arquivo.unlink()
            except OSError:
                pass

        threading.Thread(target=esperar, daemon=True).start()
    return painel_status(pasta)
