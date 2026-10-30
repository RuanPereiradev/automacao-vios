"""Banco da revisão humana: guarda cada CI analisada, as tarefas editadas e o estado.

Estados: aguardando → na_fila (validada, espera o robô) → lancando → lancada | erro.
Também: descartada (não gera tarefa) e duplicada (cópia de outra CI, ignorada).
Uma CI com erro pode ser editada e validada de novo.
"""
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

from bot import prazos

AGUARDANDO, NA_FILA, LANCANDO, LANCADA, ERRO, DESCARTADA, DUPLICADA = (
    "aguardando", "na_fila", "lancando", "lancada", "erro", "descartada", "duplicada",
)
EDITAVEIS = (AGUARDANDO, ERRO)

TABELA = """
CREATE TABLE IF NOT EXISTS cis (
    ci TEXT PRIMARY KEY,
    origem TEXT NOT NULL,          -- arquivo analise_*.json de onde veio
    analise TEXT NOT NULL,         -- resultado da análise (JSON), sem edição
    intimacao TEXT NOT NULL,       -- captura original (JSON), para mostrar o teor
    tarefas TEXT NOT NULL,         -- tarefas como estão agora (editadas ou não)
    estado TEXT NOT NULL,
    editado_em TEXT,
    validado_por TEXT,
    validado_em TEXT,
    mensagem TEXT,                 -- resultado do lançamento ou motivo do erro
    importado_em TEXT NOT NULL
)
"""

CAMPOS_TAREFA = ("nome", "data_tarefa", "hora", "descricao", "marcar_breno", "tipo_data", "rotulo_data", "finalidade",
                 "data_editada", "responsaveis")
ARQUIVO_RESPONSAVEIS = "responsaveis.json"  # pessoas do campo Responsáveis do VIOS


def _agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def conectar(caminho):
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.execute(TABELA)
    return con


def importar(con, arquivo_analise):
    """Traz as CIs de uma análise para o banco. CI que já está no banco mantém tarefas,
    edição e validação; só a análise e a captura são atualizadas (ex.: duplicidade
    detectada depois). Duplicata entra como "duplicada". Devolve (novas, ja_existiam)."""
    arquivo_analise = Path(arquivo_analise)
    resultados = json.loads(arquivo_analise.read_text(encoding="utf-8"))
    captura = arquivo_analise.with_name(arquivo_analise.name.replace("analise_", "intimacoes_", 1))
    intimacoes = {}
    if captura.exists():
        intimacoes = {i.get("ci"): i for i in json.loads(captura.read_text(encoding="utf-8"))}

    novas, existentes = 0, 0
    for r in resultados:
        ci = r.get("ci")
        if not ci:
            continue
        analise = {k: v for k, v in r.items() if k != "ia"}
        estado = DUPLICADA if r.get("duplicada_de") else AGUARDANDO
        existente = con.execute("SELECT estado, editado_em FROM cis WHERE ci = ?", (ci,)).fetchone()
        if existente:
            con.execute("UPDATE cis SET analise = ?, intimacao = ? WHERE ci = ?",
                        (json.dumps(analise, ensure_ascii=False), json.dumps(intimacoes.get(ci, {}), ensure_ascii=False), ci))
            # sem revisão humana ainda: a duplicidade da análise nova vale
            if existente["estado"] in (AGUARDANDO, DUPLICADA) and not existente["editado_em"]:
                con.execute("UPDATE cis SET estado = ? WHERE ci = ?", (estado, ci))
            existentes += 1
            continue
        tarefas = [{c: t.get(c, "") for c in CAMPOS_TAREFA} for t in r.get("tarefas", [])]
        for t in tarefas:
            t["responsaveis"] = responsaveis_padrao(t, intimacoes.get(ci, {}))
        con.execute(
            "INSERT INTO cis (ci, origem, analise, intimacao, tarefas, estado, importado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ci, str(arquivo_analise), json.dumps(analise, ensure_ascii=False),
             json.dumps(intimacoes.get(ci, {}), ensure_ascii=False),
             json.dumps(tarefas, ensure_ascii=False), estado, _agora()),
        )
        novas += 1
    con.commit()
    return novas, existentes


def _ci(linha):
    if not linha:
        return None
    d = dict(linha)
    for campo in ("analise", "intimacao", "tarefas"):
        d[campo] = json.loads(d[campo])
    return d


def datas_relativas(ci, tabela, hoje):
    """A análise é da véspera: refaz as datas que dependem do dia (MESMO_DIA = hoje,
    DIA_SEGUINTE = próximo dia útil). Data editada à mão fica como está.
    Guarda a data original em "data_analise" quando muda."""
    cal = prazos.Calendario(tabela, *prazos.contexto(ci["intimacao"]))
    for t in ci["tarefas"]:
        if t.get("data_editada"):
            continue
        if t.get("tipo_data") == "MESMO_DIA":
            nova = hoje
        elif t.get("tipo_data") == "DIA_SEGUINTE":
            nova = cal.proximo_util(hoje)
        else:
            continue
        nova = nova.strftime("%d/%m/%Y")
        if nova != t["data_tarefa"]:
            t["data_analise"], t["data_tarefa"] = t["data_tarefa"], nova
    return ci


def _normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", sem_acento.upper()).strip()


def responsaveis_padrao(tarefa, intimacao):
    """Lista vazia = automático: o robô não mexe no campo e o VIOS marca sozinho
    (em geral o auxiliar da intimação; em algumas tarefas, como Ciência, outra pessoa).
    Lista preenchida = a pessoa escolheu outros responsáveis na revisão."""
    return []


def completar_responsaveis(ci):
    """CI importada antes desta versão: tarefas sem a lista de responsáveis ficam no automático."""
    for t in ci["tarefas"]:
        if not isinstance(t.get("responsaveis"), list):
            t["responsaveis"] = responsaveis_padrao(t, ci["intimacao"])
    return ci


def pessoa_da_sigla(sigla, pessoas):
    """Sigla do auxiliar no VIOS (SUH, TAMI, JOHN...) -> nome completo no campo Responsáveis.
    Casa quando um dos nomes da pessoa começa com a sigla e só uma pessoa casa."""
    sigla = _normalizar(sigla)
    if not sigla:
        return None
    achados = [p for p in pessoas if any(n.startswith(sigla) for n in _normalizar(p).split())]
    return achados[0] if len(achados) == 1 else None


def auxiliares(ci, pessoas):
    """Auxiliares da intimação: [{sigla, nome}] (nome vazio quando a sigla não casa com ninguém)."""
    lista = []
    for sigla in re.split(r"[/,;]", ci["intimacao"].get("auxiliares", "")):
        if sigla.strip():
            lista.append({"sigla": sigla.strip(), "nome": pessoa_da_sigla(sigla, pessoas) or ""})
    return lista


def sugestoes(ci, pessoas):
    """Pessoas para adicionar com um clique quando a escolha é manual: os auxiliares e o advogado."""
    lista = [{"nome": a["nome"], "origem": f"auxiliar {a['sigla']}"} for a in auxiliares(ci, pessoas) if a["nome"]]
    if ci["intimacao"].get("advogado"):
        lista.append({"nome": ci["intimacao"]["advogado"], "origem": "advogado do processo"})
    return lista


def listar(con):
    linhas = con.execute("SELECT * FROM cis ORDER BY CAST(ci AS INTEGER)").fetchall()
    return [_ci(l) for l in linhas]


def obter(con, ci):
    return _ci(con.execute("SELECT * FROM cis WHERE ci = ?", (ci,)).fetchone())


def salvar_tarefas(con, ci, tarefas):
    con.execute("UPDATE cis SET tarefas = ?, editado_em = ? WHERE ci = ?",
                (json.dumps(tarefas, ensure_ascii=False), _agora(), ci))
    con.commit()


def mudar_estado(con, ci, estado, por=None, mensagem=None):
    if estado == NA_FILA:
        con.execute("UPDATE cis SET estado = ?, validado_por = ?, validado_em = ?, mensagem = NULL WHERE ci = ?",
                    (estado, por, _agora(), ci))
    else:
        con.execute("UPDATE cis SET estado = ?, mensagem = ? WHERE ci = ?", (estado, mensagem, ci))
    con.commit()
