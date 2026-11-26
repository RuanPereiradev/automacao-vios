"""Monitor de processos: a página /monitor da Vila dos Bots.

O monitor do pje-busca (vigia.py monitor-importar / monitor / monitor-tribunal; pasta pje-busca/ deste repositório ou
PJE_BUSCA_PASTA) acompanha uma carteira de processos (CSV exportado do VIOS) pelo DJEN, pelo DataJud e pelo próprio
tribunal (PJe, pelo Loy Trust), e grava em dados/monitor.sqlite a última movimentação e o teor de cada processo.
Esta página:
- só LÊ esse banco (sqlite em modo somente leitura): nada do pje-busca é importado e nada no banco é alterado;
- mostra as NOVIDADES (movimentação nova desde a leitura anterior), os processos PARADOS (sem movimentação há
  mais de 180 dias), a lista inteira com filtro e os erros de leitura no tribunal;
- guarda o "Visto" da equipe num JSON ao lado do banco, fora do git (dados/monitor_conferencia.json); o visto vale
  para a movimentação vista: se o processo andar de novo, ele volta para as novidades;
- o botão "Atualizar agora" abre `vigia.py monitor` (só as APIs públicas do DJEN e do DataJud) com a mesma trava
  dos outros botões do vigia (uma execução por vez).
"""
import json
import logging
import sqlite3
import threading
from datetime import date, datetime
from pathlib import Path

from bot import cumprimentos as C

log = logging.getLogger(__name__)

BANCO = Path("dados") / "monitor.sqlite"
CONFERENCIA = Path("dados") / "monitor_conferencia.json"
DIAS_NOVIDADE = 15  # novidade fica na aba por até 15 dias (ou até alguém marcar "Visto")
DIAS_PARADO = 180
TEOR_LISTA = 1200  # caracteres do teor mostrados na lista (o resto na página do processo)
FONTES = {"tribunal": "Tribunal (PJe)", "datajud": "DataJud (CNJ)", "djen": "DJEN (publicação)"}
_trava = threading.Lock()


class MonitorErro(Exception):
    pass


def pasta(valor=None):
    return C.pasta(valor)


def configurado(pasta):
    return bool(pasta) and (Path(pasta) / BANCO).exists()


def _conectar(pasta):
    caminho = (Path(pasta) / BANCO).resolve()
    db = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def conferencias(pasta):
    return C._ler_json(Path(pasta) / CONFERENCIA)


def _ultima(r):
    """A movimentação mais recente entre as três fontes (empate: tribunal > DataJud > DJEN)."""
    opcoes = []
    if r["trib_data"]:
        opcoes.append((r["trib_data"], 3, "tribunal", r["trib_mov"] or ""))
    if r["dj_data"]:
        opcoes.append((r["dj_data"], 2, "datajud", r["dj_mov"] or ""))
    if r["djen_data"]:
        opcoes.append((r["djen_data"], 1, "djen", f"{r['djen_tipo'] or 'Publicação'} no DJEN"))
    if not opcoes:
        return None
    data, _, fonte, texto = max(opcoes)
    return {"data": data, "data_br": C.data_br(data), "fonte": fonte, "fonte_texto": FONTES[fonte], "texto": texto}


def assinatura(r):
    """O que o "Visto" confirma: muda quando qualquer fonte traz movimentação nova."""
    return "|".join(str(r[c] or "") for c in ("trib_assinatura", "dj_data", "dj_mov", "djen_data"))


def _item(r, conf, hoje, teor_max=TEOR_LISTA):
    u = _ultima(r)
    c = conf.get(r["numero"]) or {}
    ass = assinatura(r)
    teor = r["trib_teor"] or ""
    return {
        "numero": r["numero"], "cliente": r["cliente"] or "", "tribunal": r["tribunal"] or "", "grau": r["grau"] or "",
        "sistema": r["sistema"], "vara": r["vara"] or "", "acao": r["acao"] or "", "situacao_vios": r["situacao"] or "",
        "ci": r["ci"] or "", "ultima": u, "dias": C._dias(u["data"], hoje) if u else None,
        "trib": {"data_br": C.data_br(r["trib_data"]), "hora": r["trib_hora"] or "", "mov": r["trib_mov"] or "",
                 "docs": r["trib_doc"] or "", "teor": teor[:teor_max], "teor_cortado": len(teor) > teor_max,
                 "teor_de": r["trib_teor_de"] or "", "lido_br": C.data_br(r["trib_visto_em"]),
                 "erro": r["trib_erro"] or ""},
        "dj": {"data_br": C.data_br(r["dj_data"]), "mov": r["dj_mov"] or "", "erro": r["dj_erro"] or ""},
        "djen": {"data_br": C.data_br(r["djen_data"]), "tipo": r["djen_tipo"] or "", "orgao": r["djen_orgao"] or "",
                 "texto": (r["djen_texto"] or "")[:teor_max], "texto_cortado": len(r["djen_texto"] or "") > teor_max,
                 "qtd": r["djen_qtd"] or 0},
        "novidade_em": r["novidade_em"] or "", "novidade_br": C.data_br(r["novidade_em"]),
        "novidade_fonte": r["novidade_fonte"] or "", "assinatura": ass,
        "visto": c.get("assinatura") == ass, "visto_quem": c.get("quem", ""), "visto_quando": c.get("quando", ""),
        "obs": c.get("obs", ""),
    }


def _rodadas(db):
    out = {}
    for tipo in ("api", "tribunal"):
        r = db.execute("SELECT * FROM mon_rodadas WHERE tipo = ? ORDER BY inicio DESC LIMIT 1", (tipo,)).fetchone()
        if r:
            try:
                resumo = json.loads(r["resumo"] or "{}")
            except ValueError:
                resumo = {}
            out[tipo] = {"data_br": C.data_br(r["inicio"][:10]), "hora": r["inicio"][11:16], "resumo": resumo}
    return out


def painel(pasta, hoje=None):
    """Tudo o que a página mostra (só leitura do banco do monitor)."""
    hoje = hoje or date.today()
    info = {"configurado": configurado(pasta), "itens": [], "novidades": [], "parados": [], "erros": [],
            "por_tribunal": [], "rodadas": {}, "total": 0, "sem_movimento": 0}
    if not info["configurado"]:
        return info
    conf = conferencias(pasta)
    db = _conectar(pasta)
    try:
        linhas = db.execute("SELECT p.*, e.* FROM mon_processos p JOIN mon_estado e USING (numero) "
                            "WHERE p.ativo = 1 ORDER BY p.numero").fetchall()
        info["rodadas"] = _rodadas(db)
    finally:
        db.close()
    itens = [_item(r, conf, hoje) for r in linhas]
    info["itens"], info["total"] = itens, len(itens)
    for i in itens:
        dias_nov = C._dias(i["novidade_em"], hoje) if i["novidade_em"] else None
        if dias_nov is not None and dias_nov <= DIAS_NOVIDADE:
            info["novidades"].append(i)
        if i["dias"] is not None and i["dias"] > DIAS_PARADO:
            info["parados"].append(i)
        if i["ultima"] is None:
            info["sem_movimento"] += 1
        if i["trib"]["erro"]:
            info["erros"].append(i)
    info["novidades"].sort(key=lambda i: i["novidade_em"], reverse=True)
    info["novidades"].sort(key=lambda i: i["visto"])  # não vistos em cima, mais recentes primeiro
    info["parados"].sort(key=lambda i: -(i["dias"] or 0))
    contagem = {}
    for i in itens:
        t = contagem.setdefault(f"{i['tribunal']} {i['grau']}º", {"tribunal": f"{i['tribunal']} {i['grau']}º grau",
                                                                  "total": 0, "lidos": 0, "so_api": i["sistema"] == "api"})
        t["total"] += 1
        t["lidos"] += 1 if i["trib"]["lido_br"] != "-" and not i["trib"]["erro"] else 0
    info["por_tribunal"] = sorted(contagem.values(), key=lambda t: -t["total"])
    info["pendentes"] = sum(1 for i in info["novidades"] if not i["visto"])
    return info


def processo(pasta, numero, hoje=None):
    """Um processo, com o teor inteiro e o histórico das três fontes (página do processo)."""
    if not configurado(pasta) or not C.NUMERO_CNJ.match(numero or ""):
        return None
    db = _conectar(pasta)
    try:
        r = db.execute("SELECT p.*, e.* FROM mon_processos p JOIN mon_estado e USING (numero) WHERE numero = ?",
                       (numero,)).fetchone()
        if not r:
            return None
        movs = [dict(m) for m in db.execute(
            "SELECT fonte, data, descricao, documento, teor FROM mon_movimentos WHERE numero = ? "
            "ORDER BY data DESC, fonte LIMIT 120", (numero,))]
    finally:
        db.close()
    item = _item(r, conferencias(pasta), hoje or date.today(), teor_max=10 ** 6)
    for m in movs:
        m["data_br"] = C.data_br(m["data"][:10]) + (m["data"][10:16] if len(m["data"]) > 10 else "")
        m["fonte_texto"] = FONTES.get(m["fonte"], m["fonte"])
    item["movimentos"] = movs
    return item


def conferir(pasta, numero, quem, obs="", desfazer=False, agora=None):
    """"Visto" da equipe na movimentação atual do processo (volta para as novidades se andar de novo)."""
    if not configurado(pasta):
        raise MonitorErro("o monitor ainda não tem carteira neste servidor")
    numero = (numero or "").strip()
    if not C.NUMERO_CNJ.match(numero):
        raise MonitorErro("número de processo inválido")
    quem, obs = (quem or "").strip()[:60], (obs or "").strip()[:500]
    if not desfazer and not quem:
        raise MonitorErro("informe quem viu")
    db = _conectar(pasta)
    try:
        r = db.execute("SELECT * FROM mon_estado WHERE numero = ?", (numero,)).fetchone()
    finally:
        db.close()
    if not r:
        raise MonitorErro("processo fora da carteira do monitor")
    quando = (agora or datetime.now()).isoformat(timespec="seconds")
    with _trava:
        tudo = conferencias(pasta)
        atual = tudo.get(numero) or {"historico": []}
        registro = {"assinatura": "" if desfazer else assinatura(r), "quem": quem, "obs": obs, "quando": quando}
        atual["historico"] = (atual.get("historico") or [])[-30:] + [dict(registro, desfazer=desfazer)]
        atual.update(registro)
        tudo[numero] = atual
        C._gravar_json(Path(pasta) / CONFERENCIA, tudo)
    return atual


def resumo(pasta):
    """Para o cartão da Vila dos Bots: só contagens."""
    try:
        p = painel(pasta)
    except sqlite3.Error:
        log.exception("Não consegui ler o banco do monitor")
        return {"configurado": False}
    api = p["rodadas"].get("api")
    return {"configurado": p["configurado"], "total": p["total"], "pendentes": p.get("pendentes", 0),
            "ultima": api["data_br"] if api else None}
