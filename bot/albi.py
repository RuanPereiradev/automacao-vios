"""Albi (bot do Sonar, pasta albi/) disparado pela página /albi do Ultron.

1.º passo (soltou o .txt): o Ultron guarda o arquivo em <saída>/albi/<id>.txt e roda
`main.py --conferir` (sem navegador): quem é válido, quem já foi pesquisado e o total em R$.
2.º passo (clicou em "Só testar" ou confirmou duas vezes): abre o Albi como processo separado,
com o .venv e o .env dele: `main.py --arquivo <txt> --eventos --saida <saída>/albi/<id>/`
(+ `--confirmar` para comprar). O Albi escreve cada evento numa linha "@evento {json}" na saída
padrão; o Ultron grava em <saída>/eventos.jsonl com bot "albi" (a Vila 03 anima). resultado.txt
e as planilhas ficam em <saída>/albi/<id>/ (a página oferece para baixar, ou tudo em .zip).
Uma execução por vez (duas derrubariam a sessão uma da outra). Nos eventos vai só o tipo e o
final do documento ("CPF final 06") e o número da empresa, nunca nomes.
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
          "pronto": ["s-ok", "Teste: pronto no passo 2 (não comprado)"], "erro": ["s-erro", "Erro (não comprado)"],
          "invalido": ["s-erro", "Linha inválida"], "confirmado": ["s-andamento", "Confirmado · aguardando o Sonar"],
          "ja_pesquisado": ["s-ja", "Já pesquisado (não comprou de novo)"],
          "encontrados": ["s-aviso", "Processos encontrados"], "nao_consta": ["s-ok", "Não consta processo"],
          "sem_resultado": ["s-erro", "Sem resultado ainda"], "conferir": ["s-erro", "Conferir no Sonar"],
          "sem_pedido": ["s-erro", "Sem pedido no registro"]}
MODOS = {"teste": "Teste (não compra)", "confirmar": "Confirmado (compra)", "preencher": "Teste (não compra)",
         "baixar": "Baixar de novo (não compra)"}
RESULTADOS = {"concluido": ["s-ok", "Concluído"], "parou": ["s-erro", "Parou"],
              "rodando": ["s-andamento", "Rodando…"], "interrompida": ["s-erro", "Interrompida"]}
TEXTOS = {"etapas": ETAPAS, "resultados": RESULTADOS, "modos": MODOS}


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


def _pasta_envio(pasta_saida):
    return Path(pasta_saida) / PASTA_ENVIOS


def _ambiente():
    ambiente = {k: os.environ[k] for k in AMBIENTE if k in os.environ}
    ambiente["PYTHONUTF8"] = "1"
    return ambiente


def receber(p, pasta_saida, texto, nome_arquivo):
    """1.º passo (soltou o .txt): guarda o arquivo e pede ao Albi a conferência (sem navegador):
    quem é válido, quem já foi pesquisado e quantos vão ser comprados. Devolve o id."""
    p = Path(p)
    if not configurado(p):
        raise AlbiErro(f"o Albi não está instalado em {p} (falta .venv, main.py ou .env; veja albi/README.md)")
    uteis = ler_linhas(texto)
    if not uteis:
        raise AlbiErro("o arquivo não tem nenhuma linha com CPF/CNPJ (veja o modelo)")
    if len(uteis) > MAX_LINHAS:
        raise AlbiErro(f"o arquivo tem {len(uteis)} linhas; o máximo por vez é {MAX_LINHAS}")
    envio_id = f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
    pasta = _pasta_envio(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    txt = pasta / f"{envio_id}.txt"
    txt.write_text(texto, encoding="utf-8")
    try:
        r = subprocess.run([str(_python(p)), "main.py", "--arquivo", str(txt.resolve()), "--conferir"], cwd=p,
                           env=_ambiente(), capture_output=True, text=True, encoding="utf-8", timeout=60)
        conferencia = json.loads(r.stdout)
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        raise AlbiErro(f"o Albi não conseguiu conferir o arquivo: {e}")
    if conferencia.get("erro"):
        raise AlbiErro(conferencia["erro"])
    meta = {"arquivo": nome_arquivo, "criado": datetime.now().isoformat(timespec="seconds"),
            # linha do arquivo -> texto e empresa (a página mostra como foi digitado, agrupado por empresa)
            "linhas": {str(n): l for n, (_, l) in uteis.items()}, "empresas": {str(n): e for n, (e, _) in uteis.items()},
            "conferencia": conferencia, "iniciado": None}
    (pasta / f"{envio_id}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return envio_id


def conferencia(pasta_saida, envio_id):
    """O que foi guardado no 1.º passo ({} se o id não existe)."""
    return _meta(pasta_saida, envio_id)


def pasta_resultado(pasta_saida, envio_id):
    """Onde o Albi escreve resultado.txt e as planilhas desta execução."""
    return _pasta_envio(pasta_saida) / envio_id


def iniciar(p, pasta_saida, envio_id, modo):
    """2.º passo: roda o Albi em segundo plano. modo "teste" (preenche e não compra),
    "confirmar" (COMPRA as pesquisas, espera e baixa os resultados) ou "baixar" (num arquivo já
    confirmado: NÃO compra, só baixa de novo o PDF e a planilha de cada pedido). Levanta AlbiErro."""
    p = Path(p)
    if modo not in ("teste", "confirmar", "baixar"):
        raise AlbiErro("modo inválido")
    meta = _meta(pasta_saida, envio_id)
    txt = _pasta_envio(pasta_saida) / f"{envio_id}.txt"
    if not meta or not txt.exists():
        raise AlbiErro("arquivo não encontrado: solte o .txt de novo")
    if modo == "confirmar" and meta.get("iniciado") == "confirmar":
        raise AlbiErro("este arquivo já foi confirmado; para pesquisar de novo, solte o .txt outra vez")
    if modo == "baixar" and meta.get("iniciado") != "confirmar":
        raise AlbiErro("só dá para baixar de novo os resultados de um arquivo que já foi confirmado")
    if not configurado(p):
        raise AlbiErro(f"o Albi não está instalado em {p}")
    with _trava:
        if status(p)["rodando"]:
            raise AlbiErro("o Albi já está rodando; espere terminar")
        if modo != "baixar":  # "baixar" não apaga a marca de "confirmar" (que impede comprar de novo)
            meta["iniciado"] = modo
        (_pasta_envio(pasta_saida) / f"{envio_id}.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        nome_arquivo, uteis = meta.get("arquivo"), meta.get("linhas") or {}
        inicio = datetime.now().isoformat(timespec="seconds")
        eventos.emitir(pasta_saida, envio_id, "arquivo_subido", bot="albi", arquivo=nome_arquivo, linhas=len(uteis), modo=modo)
        (p / "logs").mkdir(exist_ok=True)
        (p / "saida").mkdir(exist_ok=True)
        saida_log = open(p / "logs" / LOG, "a", encoding="utf-8")
        saida_log.write(f"\n===== {inicio} · {nome_arquivo} ({len(uteis)} linha(s)) · {modo} · id {envio_id} =====\n")
        saida_log.flush()
        cmd = [str(_python(p)), "main.py", "--arquivo", str(txt.resolve()), "--eventos",
               "--saida", str(pasta_resultado(pasta_saida, envio_id).resolve())]
        if modo in ("confirmar", "baixar"):
            cmd.append("--" + modo)
        try:
            proc = subprocess.Popen(cmd, cwd=p, env=_ambiente(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=saida_log, text=True, encoding="utf-8", errors="replace",
                                    start_new_session=True)
        except OSError as e:
            saida_log.close()
            eventos.emitir(pasta_saida, envio_id, "execucao_fim", bot="albi", resultado="parou",
                           motivo=f"não consegui abrir o Albi: {e}")
            raise AlbiErro(f"não consegui abrir o Albi: {e}")
        saida_log.close()
        arquivo = p / "saida" / ARQUIVO
        arquivo.write_text(json.dumps({"pid": proc.pid, "id": envio_id, "inicio": inicio, "modo": modo}), encoding="utf-8")
        log.info("Albi iniciado pela página: %s (%d linha(s)), modo %s, pid %d", nome_arquivo, len(uteis), modo, proc.pid)

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
                    for k in ("n", "bot", "envio"):
                        ev.pop(k, None)
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


def gerar_relatorio(p, pasta_saida, envio_id):
    """Roda o albi/relatorio.py na pasta desta execução (lê o resultado.txt e as planilhas já
    baixadas; não entra no Sonar): relatorio.html, relatorio.pdf e processos.csv. Levanta AlbiErro."""
    p = Path(p)
    base = pasta_resultado(pasta_saida, envio_id)
    if not (base / "resultado.txt").exists():
        raise AlbiErro("esta execução ainda não tem resultado.txt")
    if not configurado(p) or not (p / "relatorio.py").exists():
        raise AlbiErro(f"o Albi não está instalado (ou está desatualizado) em {p}")
    try:
        r = subprocess.run([str(_python(p)), "relatorio.py", str(base.resolve())], cwd=p, env=_ambiente(),
                           stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=360)  # inclui a consulta ao DataJud (até ~150 s)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise AlbiErro(f"o relatório não foi gerado: {e}")
    if r.returncode != 0 or not (base / "relatorio.html").exists():
        raise AlbiErro("o relatório não foi gerado: " + ((r.stderr or r.stdout).strip().splitlines() or ["erro"])[-1])
    log.info("Relatório do Albi gerado (id %s): %s", envio_id, r.stdout.strip().splitlines()[0] if r.stdout.strip() else "")
    return r.stdout.strip()


SEPARADOR = "=" * 48  # o mesmo do albi/relatorio.py, entre as mensagens de empresas diferentes


def mensagens(pasta_saida, envio_id):
    """mensagem.txt (escrito pelo relatorio.py) -> [{"empresa", "texto"}], uma por empresa; None se não existe."""
    arq = pasta_resultado(pasta_saida, envio_id) / "mensagem.txt"
    if not arq.is_file():
        return None
    out = []
    for bloco in arq.read_text(encoding="utf-8").split(f"\n{SEPARADOR}\n"):
        texto = bloco.strip()
        if texto:
            m = re.match(r"Olá, equipe (.+?)!", texto)
            out.append({"empresa": m.group(1) if m else "", "texto": texto})
    return out


def mensagens_cac(pasta_saida, envio_id):
    """mensagens_cac.json (escrito pelo albi/mensagem_cac.py): {"atendentes", "mensagens"}; None se não existe."""
    arq = pasta_resultado(pasta_saida, envio_id) / "mensagens_cac.json"
    try:
        return json.loads(arq.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def mensagens_por_dia(pasta_saida):
    """As mensagens da CAC de todas as execuções, por dia da execução: {"AAAA-MM-DD": [mensagem, ...]}.
    Cada mensagem: id (da execução), hora, arquivo, empresa, nome, pedido, processos, texto. Quem foi
    pesquisado de novo no mesmo dia fica só com a mensagem da execução mais recente. Dias do mais novo
    para o mais antigo; dentro do dia, por empresa e nome. Também devolve os nomes das atendentes."""
    dias, atendentes = {}, []
    for e in execucoes(pasta_saida):  # da mais nova para a mais antiga
        cac = mensagens_cac(pasta_saida, e["id"])
        if not cac or not e.get("inicio"):
            continue
        atendentes = atendentes or list(cac.get("atendentes") or [])
        dia = e["inicio"][:10]
        vistos = {(m["empresa"], m["nome"], m["pedido"]) for m in dias.get(dia, [])}
        for m in cac.get("mensagens", []):
            if (m["empresa"], m["nome"], m["pedido"]) in vistos:
                continue
            dias.setdefault(dia, []).append({"id": e["id"], "hora": e["inicio"][11:16], "arquivo": e.get("arquivo"),
                                             "empresa": m["empresa"], "nome": m["nome"], "pedido": m["pedido"],
                                             "processos": m["processos"], "texto": m["texto"]})
    for lista in dias.values():
        lista.sort(key=lambda m: (m["empresa"].lower(), m["nome"].lower()))
    return dict(sorted(dias.items(), reverse=True)), atendentes


def arquivos(pasta_saida, envio_id):
    """resultado.txt e planilhas desta execução (caminhos relativos à pasta do resultado)."""
    base = pasta_resultado(pasta_saida, envio_id)
    if not base.is_dir():
        return []
    return sorted(str(f.relative_to(base)) for f in base.rglob("*") if f.is_file() and not any(
        parte.startswith(".") for parte in f.relative_to(base).parts))


# --- execuções, montadas dos eventos (bot: "albi" em saida/eventos.jsonl) ---
def _execucao(evs, meta):
    e = {"id": None, "inicio": None, "modo": None, "arquivo": meta.get("arquivo"), "total": None, "validos": None,
         "empresas": None, "fase": None, "pedidos": [], "fim": None, "baixando": False}
    linhas = meta.get("linhas") or {}
    empresas = meta.get("empresas") or {}
    por_linha = {}

    def pedido(n):
        if n not in por_linha:
            por_linha[n] = {"linha": n, "doc": None, "texto": linhas.get(str(n)), "empresa": empresas.get(str(n), ""),
                            "grupo": None, "etapa": "fila", "valor": None, "motivo": None, "pedido": None,
                            "resultado": None, "baixado": False}
            e["pedidos"].append(por_linha[n])
        return por_linha[n]

    for ev in evs:
        e["id"] = e["id"] or ev.get("envio")
        e["inicio"] = e["inicio"] or ev.get("ts")
        tipo = ev.get("tipo")
        if tipo == "arquivo_subido":
            e["arquivo"] = e["arquivo"] or ev.get("arquivo")
            if ev.get("modo") == "baixar":  # baixar de novo: mesma execução (e pasta); recomeça a contagem
                e.update(baixando=True, fim=None, fase=None)
                for p in e["pedidos"]:
                    if p["etapa"] != "invalido":
                        p.update(etapa="fila", baixado=False, motivo=None)
            else:
                e["modo"] = ev.get("modo") or e.get("modo")
        elif tipo == "execucao_iniciada":
            e.update(total=ev.get("total"), validos=ev.get("validos"), empresas=ev.get("empresas"))
            if ev.get("modo") and ev["modo"] != "baixar":
                e["modo"] = "confirmar" if ev["modo"] == "confirmar" else "teste"
        elif tipo == "fase":
            e["fase"] = ev.get("fase")
        elif tipo == "pedido" and isinstance(ev.get("linha"), int):
            p = pedido(ev["linha"])
            p.update(doc=ev.get("doc") or p["doc"], etapa=ev.get("etapa") or p["etapa"], grupo=ev.get("grupo") or p["grupo"])
            if ev.get("valor"):
                p["valor"] = ev["valor"]
            if ev.get("motivo"):
                p["motivo"] = ev["motivo"]
            for k in ("pedido", "resultado"):
                if ev.get(k):
                    p[k] = ev[k]
            if ev.get("baixado"):
                p["baixado"] = True
        elif tipo == "execucao_fim":
            e["fim"] = {"resultado": ev.get("resultado"), "motivo": ev.get("motivo"),
                        "contagens": ev.get("contagens") or {}, "ts": ev.get("ts")}
    # linhas que ainda não apareceram em evento (o Albi não chegou nelas)
    for n in sorted(int(k) for k in linhas):
        pedido(n)
    e["pedidos"].sort(key=lambda p: p["linha"])
    alvo = [p for p in e["pedidos"] if p["etapa"] != "invalido"]
    e["alvo"] = len(alvo)
    finais = ("pronto", "erro", "ja_pesquisado", "encontrados", "nao_consta", "sem_resultado", "conferir", "sem_pedido")
    e["feitos"] = sum(1 for p in alvo if p["etapa"] in finais)
    return e


def execucoes(pasta_saida):
    """Execuções do Albi (da mais nova para a mais antiga)."""
    grupos = {}
    for ev in eventos.ler(pasta_saida, 0, limite=10 ** 9)["eventos"]:
        if ev.get("bot") == "albi" and ev.get("envio"):
            grupos.setdefault(ev["envio"], []).append(ev)
    lista = []
    for envio_id, evs in grupos.items():
        e = _execucao(evs, _meta(pasta_saida, envio_id))
        e["arquivos"] = arquivos(pasta_saida, envio_id)
        lista.append(e)
    return sorted(lista, key=lambda e: e["inicio"] or "", reverse=True)


SEM_EMPRESA = "Sem empresa"


def _chave_empresa(nome):
    return re.sub(r"\s+", " ", (nome or SEM_EMPRESA).strip()).lower()


def clientes(pasta_saida):
    """Os clientes (empresas) que pediram pesquisas, do mais recente para o mais antigo. De cada um:
    nome, pedidos (cada execução com pessoas dele, do mais novo para o mais antigo) e totais.
    Pedido: id, inicio, arquivo, modo, fim, relatorio (tem o relatório?), pessoas (as linhas dele na
    execução) e mensagens (as mensagens da CAC dele nessa execução, com o parágrafo do Gemini)."""
    por_empresa = {}
    for e in execucoes(pasta_saida):  # da mais nova para a mais antiga
        cac = mensagens_cac(pasta_saida, e["id"]) or {}
        msgs = {}
        for m in cac.get("mensagens", []):
            msgs.setdefault(_chave_empresa(m.get("empresa")), []).append(m)
        pessoas = {}
        for p in e["pedidos"]:
            pessoas.setdefault(p["empresa"] or SEM_EMPRESA, []).append(p)
        for nome, ps in pessoas.items():
            c = por_empresa.setdefault(_chave_empresa(nome), {"nome": nome, "pedidos": []})
            c["pedidos"].append({"id": e["id"], "inicio": e["inicio"], "arquivo": e["arquivo"], "modo": e["modo"],
                                 "fim": e["fim"], "relatorio": "relatorio.html" in e["arquivos"],
                                 "resultado_txt": "resultado.txt" in e["arquivos"], "pessoas": ps,
                                 "mensagens": sorted(msgs.get(_chave_empresa(nome), []), key=lambda m: m["nome"].lower())})
    lista = []
    for c in por_empresa.values():
        ms = [m for pd in c["pedidos"] for m in pd["mensagens"]]
        c.update(total_pessoas=sum(len(pd["pessoas"]) for pd in c["pedidos"]), mensagens=len(ms),
                 com_processos=sum(1 for m in ms if m["processos"]), ultimo=c["pedidos"][0]["inicio"] or "")
        lista.append(c)
    return sorted(lista, key=lambda c: c["ultimo"], reverse=True)


def andamento(p, pasta_saida):
    """Para a página do Albi (a cada 1,5 s): status do processo + a execução mais recente."""
    info = status(p)
    lista = execucoes(pasta_saida)
    atual = lista[0] if lista else None
    if atual and not atual["fim"] and not (info["rodando"] and info["id"] == atual["id"]):
        atual["interrompida"] = True  # sem execucao_fim e o processo não está rodando aqui
    info["execucao"] = atual
    return info
