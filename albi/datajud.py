"""Albi — movimentações de cada processo na API pública do DataJud (CNJ), sem inteligência artificial.

A planilha do Sonar só traz o cadastro do processo. Para contar a história do processo na mensagem
da CAC (contestação, audiências, sentença, recurso, trânsito em julgado, cumprimento, arquivamento),
o Albi consulta o número de cada processo na API pública do DataJud
(https://datajud-wiki.cnj.jus.br/api-publica/), que é gratuita e devolve as movimentações com os
códigos da Tabela Processual Unificada (TPU) do CNJ. As frases saem de regras fixas sobre esses
códigos: nada é inventado e nada é mandado para IA. Só o número do processo sai do computador
(nunca CPF nem nome).

Limites (ditos na mensagem): o DataJud não traz o texto das petições nem das decisões (os fatos
narrados e os fundamentos não aparecem), não traz a data marcada das audiências, não mostra
processos em segredo de justiça e pode estar alguns dias atrasado em relação ao tribunal.

Cada processo encontrado fica em <pasta da execução>/datajud/<número>.json: gerar o relatório de
novo não consulta outra vez. Configuração opcional no albi/.env:
  DATAJUD=false          desliga a consulta (a mensagem sai só com o cadastro do Sonar)
  DATAJUD_CHAVE=...      chave pública do CNJ, se o CNJ trocar a que vem no código
  DATAJUD_PRAZO=150      segundos, no total, para consultar todos os processos

uso (dentro de albi/), para conferir um processo:
  .venv/bin/python datajud.py 0001234-56.2026.5.07.0024
"""
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

URL = "https://api-publica.datajud.cnj.jus.br/api_publica_{}/_search"
# chave pública publicada pelo CNJ na página da API pública (não é senha; o CNJ pode trocá-la)
CHAVE_PUBLICA = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
PRAZO_PADRAO = 150
TENTATIVAS = 3
ESPERA_REQ = 40  # segundos por requisição
# código do tribunal (TR do número CNJ) -> UF, na ordem do CNJ (vale para a Justiça Estadual e a Eleitoral)
UF = {"01": "ac", "02": "al", "03": "ap", "04": "am", "05": "ba", "06": "ce", "07": "dft", "08": "es", "09": "go",
      "10": "ma", "11": "mt", "12": "ms", "13": "mg", "14": "pa", "15": "pb", "16": "pr", "17": "pe", "18": "pi",
      "19": "rj", "20": "rn", "21": "rs", "22": "ro", "23": "rr", "24": "sc", "25": "se", "26": "sp", "27": "to"}
TJM = {"13": "tjmmg", "21": "tjmrs", "26": "tjmsp"}


def _env():
    """DATAJUD_* do albi/.env (o relatório roda sem o python-dotenv); o ambiente tem preferência."""
    cfg = {}
    arq = Path(__file__).resolve().parent / ".env"
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*(DATAJUD\w*)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    for k, v in os.environ.items():
        if k.startswith("DATAJUD"):
            cfg[k] = v
    return cfg


def _norm(t):
    t = unicodedata.normalize("NFKD", t or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip().upper()


def digitos(numero):
    return re.sub(r"\D", "", numero or "")


def indice(numero):
    """Número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) -> nome do índice do tribunal na API (tjce, trt7, trf5...)."""
    d = digitos(numero)
    if len(d) != 20:
        return None
    j, tr = d[13], d[14:16]
    if j == "8":
        return "tj" + UF[tr] if tr in UF else None
    if j == "5":
        return "tst" if tr == "00" else f"trt{int(tr)}"
    if j == "4":
        return f"trf{int(tr)}" if tr != "00" else None
    if j == "6":
        return "tse" if tr == "00" else ("tre-" + UF[tr].replace("dft", "df") if tr in UF else None)
    if j == "9":
        return TJM.get(tr)
    if j == "3":
        return "stj"
    if j == "7":
        return "stm"
    return None


# ---------------- consulta ----------------
def _post(url, chave, corpo):
    req = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"Authorization": f"APIKey {chave}", "Content-Type": "application/json",
                                          "User-Agent": "albi-relatorio/1.0"})
    with urllib.request.urlopen(req, timeout=ESPERA_REQ) as r:
        return json.loads(r.read().decode("utf-8"))


def consultar(numero, chave=None, limite=None):
    """{"ok": True, "registros": [_source...]} (um registro por grau: G1, G2, JE...) ou {"ok": False, "erro"}."""
    idx, d = indice(numero), digitos(numero)
    if not idx:
        return {"ok": False, "erro": "tribunal fora da API pública do DataJud"}
    chave = chave or CHAVE_PUBLICA
    erro = ""
    for t in range(TENTATIVAS):
        if limite and time.monotonic() > limite:
            return {"ok": False, "erro": "tempo esgotado"}
        try:
            r = _post(URL.format(idx), chave, {"size": 20, "query": {"match": {"numeroProcesso": d}}})
            if "hits" in r:
                regs = [h["_source"] for h in r["hits"]["hits"] if digitos(h["_source"].get("numeroProcesso")) == d]
                return {"ok": True, "indice": idx, "registros": regs, "consultado": datetime.now().isoformat(timespec="seconds")}
            erro = str(r.get("error", r))[:200]  # "es_rejected_execution_exception": servidor ocupado
        except urllib.error.HTTPError as e:
            erro = f"HTTP {e.code}"
            if e.code in (401, 403):
                return {"ok": False, "erro": f"{erro}: chave do DataJud recusada (veja DATAJUD_CHAVE)"}
        except (urllib.error.URLError, OSError, ValueError) as e:
            erro = str(getattr(e, "reason", e))[:200]
        time.sleep(2 + 3 * t)
    return {"ok": False, "erro": erro or "sem resposta"}


def enriquecer(pasta, pessoas, log=print):
    """Põe x["datajud"] = andamento(...) em cada processo (ou {"erro": ...}). Nunca levanta erro."""
    cfg = _env()
    if cfg.get("DATAJUD", "").strip().lower() in ("false", "0", "nao", "não", "desligado"):
        return {"consultados": 0, "desligado": True}
    procs = [x for p in pessoas for x in p.get("processos", []) if len(digitos(x.get("numero"))) == 20]
    if not procs:
        return {"consultados": 0}
    cache = Path(pasta) / "datajud"
    cache.mkdir(exist_ok=True)
    try:
        prazo = int(cfg.get("DATAJUD_PRAZO") or PRAZO_PADRAO)
    except ValueError:
        prazo = PRAZO_PADRAO
    limite = time.monotonic() + prazo
    chave = (cfg.get("DATAJUD_CHAVE") or "").strip() or None
    numeros = sorted({digitos(x["numero"]) for x in procs})
    res = {}

    def um(d):
        arq = cache / f"{d}.json"
        if arq.exists():
            try:
                return d, json.loads(arq.read_text(encoding="utf-8"))
            except ValueError:
                pass
        r = consultar(d, chave, limite)
        if r["ok"] and r["registros"]:  # "não encontrado" não fica guardado: pode aparecer depois
            arq.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        return d, r

    with ThreadPoolExecutor(max_workers=4) as ex:
        for d, r in ex.map(um, numeros):
            res[d] = r
    falhas = 0
    for x in procs:
        r = res.get(digitos(x["numero"])) or {"ok": False, "erro": "não consultado"}
        if r["ok"] and r["registros"]:
            x["datajud"] = andamento(r["registros"])
        else:
            x["datajud"] = {"erro": r.get("erro") or "processo não encontrado na base pública do CNJ"}
            falhas += r["ok"] is False
    if falhas:
        log(f"DataJud: {falhas} processo(s) sem resposta da API (a mensagem deles sai só com o cadastro do Sonar)")
    return {"consultados": len(numeros), "falhas": falhas}


# ---------------- leitura das movimentações ----------------
def _quando(v):
    """"2026-04-09T13:07:58.000Z" ou "20260409000000" -> datetime (horário de Brasília)."""
    v = (v or "").strip()
    try:
        if re.fullmatch(r"\d{14}", v):
            return datetime.strptime(v, "%Y%m%d%H%M%S")
        dt = datetime.strptime(v[:19], "%Y-%m-%dT%H:%M:%S")
        if v.endswith("Z") and (dt.hour or dt.minute):  # hora UTC -> Brasília (meia-noite é só data)
            dt -= timedelta(hours=3)
        return dt
    except ValueError:
        return None


def br(dt):
    return dt.strftime("%d/%m/%Y") if dt else ""


def _movimentos(registros):
    """Movimentos de todos os graus, sem repetição, em ordem de data: (dt, codigo, NOME, {descricao: nome}, grau)."""
    vistos, out = set(), []
    for reg in registros:
        for m in reg.get("movimentos") or []:
            dt = _quando(m.get("dataHora"))
            if not dt:
                continue
            comp = {(c.get("descricao") or ""): (c.get("nome") or "").strip() for c in m.get("complementosTabelados") or []}
            chave = (m.get("codigo"), m.get("dataHora"), tuple(sorted(comp.items())))
            if chave in vistos:
                continue
            vistos.add(chave)
            out.append((dt, m.get("codigo"), _norm(m.get("nome")), comp, reg.get("grau") or ""))
    out.sort(key=lambda m: m[0])
    return out


def _classificar(dt, cod, nome, original, grau):
    """Um movimento -> (tipo, chave_de_repeticao, frase) ou None. tipo: "fato" (andamento), "decisao" ou "status".
    original: os complementos como vieram (com acento, para a frase); comp: os mesmos sem acento (para comparar)."""
    comp = {k: _norm(v) for k, v in original.items()}
    tp, td = comp.get("tipo_de_peticao", ""), comp.get("tipo_de_documento", "")
    # ---- petições
    if cod == 85 or nome == "PETICAO":
        if "CONTESTACAO" in tp:
            return "fato", "contestacao", "a parte ré apresentou sua *defesa (contestação)*"
        if "REPLICA" in tp or "IMPUGNACAO A CONTESTACAO" in tp:
            return "fato", "replica", "a parte autora se manifestou sobre a defesa apresentada (réplica)"
        if "EMBARGOS DE DECLARACAO" in tp:
            return "fato", "embargos", ("foram apresentados *embargos de declaração* (pedido para que o juiz esclareça "
                                        "ou corrija a decisão)")
        if "CONTRA" in tp and "RAZ" in tp:
            return "fato", "contrarrazoes", "a outra parte respondeu ao recurso (contrarrazões)"
        if any(r in tp for r in ("APELACAO", "RECURSO", "AGRAVO")):
            return "fato", "pet_recurso:" + tp, (f"foi apresentado recurso (*{original['tipo_de_peticao']}*), pedindo que o tribunal "
                                              "reexamine a decisão")
        if "CUMPRIMENTO DE SENTENCA" in tp or tp.startswith("EXECUCAO"):
            return "fato", "pede_cumprimento", ("foi pedido o *cumprimento da sentença*, ou seja, a cobrança daquilo que "
                                                "foi decidido")
        if "ACORDO" in tp:
            return "fato", "proposta_acordo", "foi apresentada ao juízo uma proposta de acordo entre as partes"
        return None
    # ---- documentos expedidos
    if cod == 60 or nome == "EXPEDICAO DE DOCUMENTO":
        if "ALVARA" in td:
            return "decisao", "alvara", ("foi expedido *alvará*, autorização para retirada de valores depositados no "
                                         "processo (o que, por si só, não comprova que o valor foi recebido)")
        if "PRECATORIO" in td or "REQUISICAO DE PEQUENO VALOR" in td or td == "RPV":
            return "decisao", "requisicao", ("foi expedida requisição de pagamento (precatório/RPV), o que não "
                                             "significa que o pagamento já tenha sido feito")
        if "CITACAO" in td:
            return "fato", "citacao", ("foi expedida a *citação*, comunicação oficial para que a parte ré tome "
                                       "conhecimento da ação e apresente defesa")
        if "NOTIFICACAO" in td:
            return "fato", "notificacao", "foram expedidas notificações às partes"
        return None
    # ---- audiências
    if cod == 970 or nome.startswith("AUDIENCIA"):
        tipo = original.get("tipo_de_audiencia", "").lower() or re.sub(r"^AUDIENCIA\s*(DE\s*)?", "", nome).lower()
        sit = comp.get("situacao_da_audiencia", "") or nome
        sem_de = ("UNA", "INICIAL", "PRELIMINAR", "ADMONITORIA", "INAUGURAL")  # "audiência una", não "de una"
        de = "" if not tipo or _norm(tipo) == "AUDIENCIA" else (f" *{tipo}*" if _norm(tipo) in sem_de else f" de *{tipo}*")
        if "NAO" in sit and "REALIZ" in sit or "CANCEL" in sit:
            return "status", "aud_nao", ""
        if "REALIZ" in sit:
            return "fato", f"aud_realizada:{_norm(tipo)}", f"foi realizada audiência{de}"
        if "DESIGN" in sit or "REDESIGN" in sit or "MARCAD" in sit:
            return "status", "aud_designada", f"foi marcada audiência{de}"
        return None
    # ---- decisões no curso do processo
    if "GRATUIDADE" in nome or "ASSISTENCIA JUDICIARIA" in nome:
        if "NAO" in nome or "INDEFER" in nome or "REVOG" in nome:
            return "fato", "gratuidade_nao", "a Justiça *negou o pedido de gratuidade da justiça* feito por uma das partes"
        return "fato", "gratuidade", ("a Justiça concedeu a uma das partes o benefício da *gratuidade da justiça* "
                                      "(dispensa do pagamento das custas do processo)")
    if cod == 332 or "TUTELA" in nome or "LIMINAR" in nome:
        if "NAO CONCEDIDA" in nome or "INDEFER" in nome or "REVOG" in nome:
            return "fato", "tutela_nao", "a Justiça *negou o pedido de decisão urgente* (liminar/tutela de urgência)"
        return "fato", "tutela", ("a Justiça concedeu uma *decisão provisória e urgente* (liminar/tutela de urgência), "
                                  "que vale até o julgamento final")
    # ---- julgamento do pedido (sentença) e do recurso
    if cod == 221 or nome == "PROCEDENCIA EM PARTE":
        return "decisao", "sentenca:parcial", ("foi registrada *sentença de procedência parcial*: a Justiça aceitou parte "
                                               "dos pedidos da parte autora e negou os demais")
    if cod == 219 or nome == "PROCEDENCIA":
        return "decisao", "sentenca:procedente", ("foi registrada *sentença de procedência*: a Justiça reconheceu o "
                                                  "direito pedido pela parte autora")
    if cod == 220 or nome == "IMPROCEDENCIA":
        return "decisao", "sentenca:improcedente", ("foi registrada *sentença de improcedência*: a Justiça negou os "
                                                    "pedidos da parte autora")
    if "HOMOLOGACAO DE TRANSACAO" in nome or "HOMOLOGACAO DE ACORDO" in nome:
        return "decisao", "sentenca:acordo", "a Justiça *homologou (aprovou) um acordo* feito entre as partes"
    if "EMBARGOS DE DECLARACAO" in nome:
        r = "rejeitados" if "NAO ACOLHIMENTO" in nome or "REJEI" in nome else (
            "acolhidos em parte" if "EM PARTE" in nome else "acolhidos")
        return "decisao", "julg_embargos", f"os embargos de declaração foram *{r}*"
    if "NAO-PROVIMENTO" in nome or "NAO PROVIMENTO" in nome:
        return "decisao", "recurso:negado", "o tribunal *negou o recurso* (não provimento), mantendo a decisão anterior"
    if "PROVIMENTO EM PARTE" in nome:
        return "decisao", "recurso:parcial", "o tribunal *aceitou o recurso em parte*, alterando parcialmente a decisão anterior"
    if "PROVIMENTO" in nome:
        return "decisao", "recurso:provido", "o tribunal *aceitou o recurso* (provimento), alterando a decisão anterior"
    if "NAO CONHECIMENTO" in nome or "NAO-CONHECIMENTO" in nome:
        return "decisao", "recurso:nao_conhecido", ("o tribunal *não analisou o recurso* (não conhecimento), por falta de "
                                                    "requisito formal")
    if "RECURSO PREJUDICADO" in nome:
        return "decisao", "recurso:prejudicado", "o recurso foi considerado *prejudicado* (perdeu o objeto)"
    if "EXTINCAO DA EXECUCAO" in nome or "EXTINCAO DO CUMPRIMENTO" in nome:
        return "decisao", "extinta_execucao", ("foi declarada a *extinção da execução/cumprimento de sentença*, ou seja, "
                                               "a fase de cobrança foi encerrada (o motivo, se pagamento ou outro, não "
                                               "consta nos registros)")
    if "PRESCRICAO" in nome or "DECADENCIA" in nome:
        return "decisao", "sentenca:prescricao", ("o processo foi encerrado pelo reconhecimento de *prescrição/decadência*, "
                                                  "ou seja, a perda do prazo legal para exigir o direito")
    if "DESISTENCIA" in nome:
        return "decisao", "sentenca:desistencia", ("o processo foi *extinto por desistência* da parte autora, sem que a "
                                                   "Justiça analisasse o pedido")
    if any(k in nome for k in ("ABANDONO", "PRESSUPOSTOS", "INDEFERIMENTO DA PETICAO", "LITISPENDENCIA", "COISA JULGADA",
                               "PEREMPCAO", "ILEGITIMIDADE", "INTERESSE PROCESSUAL", "AUSENCIA DO AUTOR")):
        return "decisao", "sentenca:sem_merito", (f"o processo foi *extinto sem análise do pedido* (motivo registrado: "
                                                  f"{nome.lower()})")
    if cod == 11375 or "INEXISTENCIA DE BENS" in nome:
        return "decisao", "sem_bens", "foi registrado que *não foram encontrados bens* para penhora"
    if "PENHORA" in nome or "BLOQUEIO" in nome or "ARRESTO" in nome:
        return "decisao", "penhora", "foi determinado o *bloqueio ou a penhora* de bens ou valores para garantir o pagamento"
    if cod == 848 or "TRANSITO EM JULGADO" in nome:
        return "decisao", "transito", ("ocorreu o *trânsito em julgado*, ou seja, a decisão se tornou definitiva e não "
                                       "cabe mais recurso")
    if cod == 14739 or "EVOLUCAO DA CLASSE" in nome or "RETIFICACAO DE CLASSE" in nome:
        return "status", "evolucao_classe", ""
    if cod == 123 or nome == "REMESSA":
        if "GRAU DE RECURSO" in comp.get("motivo_da_remessa", ""):
            return "fato", "remessa_recurso", "o processo foi enviado ao tribunal para o julgamento do recurso"
        return None
    # ---- situação (arquivo, baixa, suspensão)
    if cod == 893 or "DESARQUIV" in nome or cod == 849 or "REATIVACAO" in nome:
        return "status", "desarquivado", "o processo foi desarquivado e voltou a tramitar"
    if cod == 246 or (nome == "DEFINITIVO") or ("ARQUIV" in nome and "DEFINITIV" in nome):
        return "status", "arquivado_def", "o processo foi *arquivado definitivamente*"
    if nome == "PROVISORIO" or ("ARQUIV" in nome and "PROVIS" in nome):
        return "status", "arquivado_prov", "o processo foi *arquivado provisoriamente* (pode ser retomado)"
    if "ARQUIV" in nome:
        return "status", "arquivado", "o processo foi *arquivado*"
    if "BAIXA DEFINITIVA" in nome:
        return "status", "baixa", "o processo recebeu *baixa definitiva*"
    if ("SUSPENS" in nome or "SOBREST" in nome) and "EFEITO" not in nome:
        return "status", "suspenso", "o processo foi *suspenso*"
    if "CONCLUS" in nome and "JULGAMENTO" in comp.get("tipo_de_conclusao", ""):
        return "status", "concluso_julgamento", ""
    return None


SENTENCA = {"sentenca:parcial": "procedência parcial (a Justiça aceitou parte dos pedidos)",
            "sentenca:procedente": "procedência (a Justiça reconheceu o direito pedido)",
            "sentenca:improcedente": "improcedência (a Justiça negou os pedidos)",
            "sentenca:acordo": "acordo entre as partes, homologado pela Justiça",
            "sentenca:prescricao": "extinção por prescrição/decadência",
            "sentenca:desistencia": "extinção por desistência da parte autora",
            "sentenca:sem_merito": "extinção sem análise do pedido"}
RECURSO = {"recurso:negado": "recurso negado", "recurso:parcial": "recurso aceito em parte",
           "recurso:provido": "recurso aceito", "recurso:nao_conhecido": "recurso não analisado (não conhecido)",
           "recurso:prejudicado": "recurso prejudicado"}


def andamento(registros):
    """Movimentações do DataJud -> o que a mensagem precisa:
    classe, assuntos, ajuizamento, atualizado, sigilo, fatos [(dt, frase)], decisoes [(dt, frase)],
    sentenca, recurso, transito, cumprimento, situacao (chave), situacao_data, audiencia_pendente, encerrado."""
    movs = _movimentos(registros)
    principal = next((r for r in registros if r.get("grau") in ("G1", "JE")), registros[0])
    assuntos = []
    for r in registros:
        for a in r.get("assuntos") or []:
            for item in (a if isinstance(a, list) else [a]):
                n = (item or {}).get("nome") if isinstance(item, dict) else None
                if n and n not in assuntos:
                    assuntos.append(n)
    atual = max((_quando(r.get("dataHoraUltimaAtualizacao")) for r in registros), default=None, key=lambda d: d or datetime.min)
    classe_atual = (max(registros, key=lambda r: r.get("dataHoraUltimaAtualizacao") or "").get("classe") or {}).get("nome", "")
    out = {"classe": (principal.get("classe") or {}).get("nome", ""), "classe_atual": classe_atual, "assuntos": assuntos,
           "ajuizamento": _quando(principal.get("dataAjuizamento")), "atualizado": atual,
           "orgao": (principal.get("orgaoJulgador") or {}).get("nome", ""),
           "sigilo": max(int(r.get("nivelSigilo") or 0) for r in registros),
           "graus": sorted({r.get("grau") or "" for r in registros}), "movimentos": len(movs),
           "fatos": [], "decisoes": [], "sentenca": None, "recurso": None, "transito": None, "cumprimento": None,
           "situacao": "", "situacao_data": None, "audiencia_pendente": None, "audiencias_nao_realizadas": 0}
    vistos = set()
    ultimo_status = None
    ultima_sentenca = None
    aud_designada = None
    for dt, cod, nome, comp, grau in movs:
        c = _classificar(dt, cod, nome, comp, grau)
        if not c:
            continue
        tipo, chave, frase = c
        # audiências: guarda a última marcação; resultado posterior apaga a pendência
        if chave == "aud_designada":
            aud_designada = (dt, frase)
            continue
        if chave == "aud_nao":
            out["audiencias_nao_realizadas"] += 1
            aud_designada = None
            continue
        if chave.startswith("aud_realizada"):
            aud_designada = None
        if chave == "evolucao_classe":
            if "CUMPRIMENTO" in _norm(classe_atual) or "EXECUC" in _norm(classe_atual):
                chave, tipo = "cumprimento", "decisao"
                frase = ("o processo passou para a fase de *cumprimento de sentença*, que é a etapa de cobrança "
                         "daquilo que foi decidido")
            else:
                continue
        if chave == "pede_cumprimento" and out["cumprimento"] is None:
            out["cumprimento"] = dt
        if chave == "cumprimento":
            out["cumprimento"] = out["cumprimento"] or dt
        if chave.startswith("sentenca:"):
            ultima_sentenca = dt
            aud_designada = None
            if out["sentenca"] is None:
                out["sentenca"] = (dt, chave)
        if chave.startswith("recurso:"):
            out["recurso"] = (dt, chave)
        if chave == "transito":
            out["transito"] = out["transito"] or dt
        if tipo == "status":
            if chave in ("arquivado_def", "arquivado_prov", "arquivado", "baixa", "suspenso", "desarquivado", "concluso_julgamento"):
                ultimo_status = (dt, chave)
            # arquivamento/desarquivamento entram no relato só na primeira vez
            if not frase or chave in vistos:
                continue
        elif chave in vistos:  # cada tipo de acontecimento é contado uma vez (o TJCE repete a mesma sentença)
            continue
        vistos.add(chave)
        alvo = out["decisoes"] if tipo == "decisao" else out["fatos"]
        alvo.append((dt, frase))
    if aud_designada and (not ultima_sentenca or aud_designada[0] > ultima_sentenca):
        out["audiencia_pendente"] = aud_designada[0]
        out["fatos"].append((aud_designada[0], aud_designada[1] + " (a data marcada para a audiência não aparece "
                                                                  "nos registros públicos consultados)"))
        out["fatos"].sort(key=lambda f: f[0])
    # situação atual: o registro mais recente que diz o estado do processo
    st = ultimo_status[1] if ultimo_status else ""
    out["situacao_data"] = ultimo_status[0] if ultimo_status else None
    if st in ("arquivado_def", "arquivado_prov", "arquivado", "baixa", "suspenso"):
        out["situacao"] = st
    elif out["audiencia_pendente"]:
        out["situacao"] = "aguarda_audiencia"
    elif out["cumprimento"] and (not out["sentenca"] or out["cumprimento"] >= out["sentenca"][0]):
        out["situacao"] = "cumprimento"
    elif out["sentenca"] and out["transito"] and out["transito"] >= out["sentenca"][0]:
        out["situacao"] = "transitado"
    elif out["sentenca"] and (out["recurso"] or any("recurso" in f for _, f in out["fatos"] if _ >= out["sentenca"][0])):
        out["situacao"] = "recurso"
    elif out["sentenca"]:
        out["situacao"] = "sentenciado"
    elif st == "concluso_julgamento":
        out["situacao"] = "aguarda_julgamento"
    else:
        out["situacao"] = "tramitando"
    out["encerrado"] = out["situacao"] in ("arquivado_def", "arquivado", "baixa")
    return out


def main(*args):
    if not args:
        print(__doc__)
        return 2
    cfg = _env()
    r = consultar(args[0], (cfg.get("DATAJUD_CHAVE") or "").strip() or None)
    if not r["ok"]:
        print("Erro:", r["erro"], file=sys.stderr)
        return 1
    if not r["registros"]:
        print("Processo não encontrado na base pública do CNJ.")
        return 1
    a = andamento(r["registros"])
    print(f"{a['classe']} · {a['orgao']} · ajuizado em {br(a['ajuizamento'])} · atualizado em {br(a['atualizado'])}")
    print("Assuntos:", ", ".join(a["assuntos"]) or "—")
    for titulo, lista in (("Andamento", a["fatos"]), ("Decisões", a["decisoes"])):
        print(f"\n{titulo}:")
        for dt, f in lista:
            print(f"  {br(dt)}  {f}")
    print("\nSituação:", a["situacao"], br(a["situacao_data"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
