"""Albi (bot do Sonar, pasta albi/) disparado pela página /albi do Ultron.

A pessoa solta o .txt (um CPF/CNPJ por linha) na página; o Ultron guarda o arquivo em
<saída>/albi/<id>.txt e abre o Albi como processo separado, com o .venv e o .env dele:
`main.py --arquivo <txt> --eventos`. O Albi escreve cada evento numa linha "@evento {json}" na
saída padrão; o Ultron lê e grava em <saída>/eventos.jsonl com bot "albi" (a Vila 03 anima).

O .txt vem organizado por empresa ("EMPRESA: ..." e, embaixo, "CPF ; nome", uma pessoa por
linha; modelo em albi/modelo_pedidos.txt). Por enquanto o Albi só PREENCHE a Nova Pesquisa até o passo 2 ("Pedido", com o valor) e nunca
clica em "Confirmar Pedido". Uma execução por vez (duas derrubariam a sessão uma da outra).
Nos eventos vai só o tipo e o final do documento ("CNPJ final 77"); o .txt inteiro fica em
<saída>/albi/ e aparece só na página /albi (que tem a mesma senha da página do Ultron).
"""
import json
import logging
import os
import re
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path

from bot import eventos

log = logging.getLogger(__name__)

PASTA_PADRAO = Path(__file__).resolve().parent.parent / "albi"
PASTA_ENVIOS = "albi"  # dentro da pasta de saída do Ultron: <id>.txt e <id>.json
ARQUIVO = ".ultron_execucao.json"  # na pasta saida/ do Albi: execução em andamento (pid, id, início)
LOG = "execucoes_ultron.log"  # na pasta logs/ do Albi: o log de cada execução disparada pela página
MAX_LINHAS = 500
# só o necessário: nenhuma variável do Ultron (senha da página, chaves de API) vai para o Albi
AMBIENTE = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL", "DISPLAY", "XAUTHORITY")
_trava = threading.Lock()

ETAPAS = {"fila": ["s-ja", "Na fila"], "preenchendo": ["s-andamento", "Preenchendo…"],
          "pronto": ["s-ok", "Pronto no passo 2 (não confirmado)"], "erro": ["s-erro", "Erro"],
          "invalido": ["s-erro", "Linha inválida"]}
RESULTADOS = {"concluido": ["s-ok", "Concluído"], "parou": ["s-erro", "Parou"],
              "rodando": ["s-andamento", "Rodando…"], "interrompida": ["s-erro", "Interrompida"]}
TEXTOS = {"etapas": ETAPAS, "resultados": RESULTADOS}


class AlbiErro(Exception):
    pass


def pasta(valor=None):
    """ALBI_PASTA do .env do Ultron, ou a pasta albi/ deste repositório."""
    valor = (valor if valor is not None else os.getenv("ALBI_PASTA", "")).strip()
    return Path(os.path.expanduser(valor)) if valor else PASTA_PADRAO


def _python(p):
    return Path(p) / ".venv" / "bin" / "python"


def configurado(p):
    p = Path(p)
    return _python(p).exists() and (p / "main.py").exists() and (p / ".env").exists()


def _vivo(pid):
    """O processo existe e é o main.py do Albi (não um pid reaproveitado)."""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:
        return True
    return "main.py" in cmd


def _ler_atual(p):
    try:
        return json.loads((Path(p) / "saida" / ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status(p):
    """{"configurado", "rodando", "id", "inicio"}."""
    info = {"configurado": configurado(p), "rodando": False, "id": None, "inicio": None}
    atual = _ler_atual(p)
    if atual and _vivo(int(atual.get("pid", 0))):
        info.update(rodando=True, id=atual.get("id"), inicio=atual.get("inicio"))
    return info


EMPRESA = re.compile(r"\A\s*EMPRESA\s*:\s*(.*?)\s*\Z", re.I)


def ler_linhas(texto):
    """{n.º da linha: (empresa, texto)} das linhas de pedido, como o Albi lê: sem as vazias, as que
    começam com #, as só com --- e as "EMPRESA: ..." (que dizem a empresa das linhas de baixo)."""
    linhas, empresa = {}, ""
    for n, bruta in enumerate(texto.splitlines(), 1):
        l = bruta.strip()
        if not l or l.startswith("#") or (len(l) >= 3 and set(l) <= set("-=_")):
            continue
        m = EMPRESA.match(l)
        if m:
            empresa = m.group(1)
            continue
        linhas[n] = (empresa, l)
    return linhas


def _meta(pasta_saida, envio_id):
    try:
        return json.loads((Path(pasta_saida) / PASTA_ENVIOS / f"{envio_id}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def rodar(p, pasta_saida, texto, nome_arquivo):
    """Guarda o .txt e abre o Albi em segundo plano. Devolve o id da execução.
    Levanta AlbiErro se não pode rodar."""
    p = Path(p)
    if not configurado(p):
        raise AlbiErro(f"o Albi não está instalado em {p} (falta .venv, main.py ou .env; veja albi/README.md)")
    uteis = ler_linhas(texto)
    if not uteis:
        raise AlbiErro("o arquivo não tem nenhuma linha com CPF/CNPJ (veja o modelo)")
    if len(uteis) > MAX_LINHAS:
        raise AlbiErro(f"o arquivo tem {len(uteis)} linhas; o máximo por vez é {MAX_LINHAS}")
    with _trava:
        if status(p)["rodando"]:
            raise AlbiErro("o Albi já está rodando; espere terminar")
        envio_id = f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
        pasta_envios = Path(pasta_saida) / PASTA_ENVIOS
        pasta_envios.mkdir(parents=True, exist_ok=True)
        txt = pasta_envios / f"{envio_id}.txt"
        txt.write_text(texto, encoding="utf-8")
        inicio = datetime.now().isoformat(timespec="seconds")
        # linha do arquivo -> texto e empresa (a página mostra como foi digitado, agrupado por empresa)
        (pasta_envios / f"{envio_id}.json").write_text(json.dumps({
            "arquivo": nome_arquivo, "criado": inicio, "linhas": {str(n): l for n, (_, l) in uteis.items()},
            "empresas": {str(n): e for n, (e, _) in uteis.items()}}, ensure_ascii=False), encoding="utf-8")
        eventos.emitir(pasta_saida, envio_id, "arquivo_subido", bot="albi", arquivo=nome_arquivo, linhas=len(uteis))

        (p / "logs").mkdir(exist_ok=True)
        (p / "saida").mkdir(exist_ok=True)
        ambiente = {k: os.environ[k] for k in AMBIENTE if k in os.environ}
        ambiente["PYTHONUTF8"] = "1"
        saida_log = open(p / "logs" / LOG, "a", encoding="utf-8")
        saida_log.write(f"\n===== {inicio} · {nome_arquivo} ({len(uteis)} linha(s)) · id {envio_id} =====\n")
        saida_log.flush()
        try:
            proc = subprocess.Popen([str(_python(p)), "main.py", "--arquivo", str(txt.resolve()), "--eventos"],
                                    cwd=p, env=ambiente, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=saida_log, text=True, encoding="utf-8", errors="replace",
                                    start_new_session=True)
        except OSError as e:
            saida_log.close()
            eventos.emitir(pasta_saida, envio_id, "execucao_fim", bot="albi", resultado="parou",
                           motivo=f"não consegui abrir o Albi: {e}")
            raise AlbiErro(f"não consegui abrir o Albi: {e}")
        saida_log.close()
        arquivo = p / "saida" / ARQUIVO
        arquivo.write_text(json.dumps({"pid": proc.pid, "id": envio_id, "inicio": inicio}), encoding="utf-8")
        log.info("Albi iniciado pela página: %s (%d linha(s)), pid %d", nome_arquivo, len(uteis), proc.pid)

        def acompanhar():
            fim = False
            try:
                for linha in proc.stdout:
                    if not linha.startswith("@evento "):
                        continue
                    try:
                        ev = json.loads(linha[len("@evento "):])
                        tipo = ev.pop("tipo")
                    except (ValueError, KeyError, AttributeError):
                        log.warning("Evento ilegível do Albi: %r", linha[:200])
                        continue
                    ev.pop("n", None)
                    ev.pop("bot", None)
                    ev.pop("envio", None)
                    fim = fim or tipo == "execucao_fim"
                    eventos.emitir(pasta_saida, envio_id, tipo, bot="albi", **ev)
            finally:
                codigo = proc.wait()  # recolhe o processo (sem isso ele ficaria "zumbi" e pareceria vivo)
                log.info("Albi terminou (id %s, código %s)", envio_id, codigo)
                if not fim:
                    eventos.emitir(pasta_saida, envio_id, "execucao_fim", bot="albi", resultado="parou",
                                   motivo=f"o Albi fechou sem terminar (código {codigo}; veja albi/logs/{LOG})")
                try:
                    if (_ler_atual(p) or {}).get("pid") == proc.pid:
                        arquivo.unlink()
                except OSError:
                    pass

        threading.Thread(target=acompanhar, daemon=True).start()
    return envio_id


# --- execuções, montadas dos eventos (bot: "albi" em saida/eventos.jsonl) ---
def _execucao(evs, meta):
    e = {"id": None, "inicio": None, "arquivo": meta.get("arquivo"), "total": None, "validos": None,
         "empresas": None, "fase": None, "pedidos": [], "fim": None}
    linhas = meta.get("linhas") or {}
    empresas = meta.get("empresas") or {}
    por_linha = {}

    def pedido(n):
        if n not in por_linha:
            por_linha[n] = {"linha": n, "doc": None, "texto": linhas.get(str(n)), "empresa": empresas.get(str(n), ""),
                            "grupo": None, "etapa": "fila", "valor": None, "motivo": None}
            e["pedidos"].append(por_linha[n])
        return por_linha[n]

    for ev in evs:
        e["id"] = e["id"] or ev.get("envio")
        e["inicio"] = e["inicio"] or ev.get("ts")
        tipo = ev.get("tipo")
        if tipo == "arquivo_subido":
            e["arquivo"] = e["arquivo"] or ev.get("arquivo")
        elif tipo == "execucao_iniciada":
            e.update(total=ev.get("total"), validos=ev.get("validos"), empresas=ev.get("empresas"))
        elif tipo == "fase":
            e["fase"] = ev.get("fase")
        elif tipo == "pedido" and isinstance(ev.get("linha"), int):
            p = pedido(ev["linha"])
            p.update(doc=ev.get("doc") or p["doc"], etapa=ev.get("etapa") or p["etapa"], grupo=ev.get("grupo") or p["grupo"])
            if ev.get("valor"):
                p["valor"] = ev["valor"]
            if ev.get("motivo"):
                p["motivo"] = ev["motivo"]
        elif tipo == "execucao_fim":
            e["fim"] = {"resultado": ev.get("resultado"), "motivo": ev.get("motivo"),
                        "contagens": ev.get("contagens") or {}, "ts": ev.get("ts")}
    # linhas que ainda não apareceram em evento (o Albi não chegou nelas)
    for n in sorted(int(k) for k in linhas):
        pedido(n)
    e["pedidos"].sort(key=lambda p: p["linha"])
    alvo = [p for p in e["pedidos"] if p["etapa"] != "invalido"]
    e["alvo"] = len(alvo)
    e["feitos"] = sum(1 for p in alvo if p["etapa"] in ("pronto", "erro"))
    return e


def execucoes(pasta_saida):
    """Execuções do Albi (da mais nova para a mais antiga)."""
    grupos = {}
    for ev in eventos.ler(pasta_saida, 0, limite=10 ** 9)["eventos"]:
        if ev.get("bot") == "albi" and ev.get("envio"):
            grupos.setdefault(ev["envio"], []).append(ev)
    lista = [_execucao(evs, _meta(pasta_saida, envio_id)) for envio_id, evs in grupos.items()]
    return sorted(lista, key=lambda e: e["inicio"] or "", reverse=True)


def andamento(p, pasta_saida):
    """Para a página do Albi (a cada 1,5 s): status do processo + a execução mais recente."""
    info = status(p)
    lista = execucoes(pasta_saida)
    atual = lista[0] if lista else None
    if atual and not atual["fim"] and not (info["rodando"] and info["id"] == atual["id"]):
        atual["interrompida"] = True  # sem execucao_fim e o processo não está rodando aqui
    info["execucao"] = atual
    return info
