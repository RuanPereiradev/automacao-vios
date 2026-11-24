"""Estado do vigia VIOS → PJe (só biblioteca padrão): o que já foi visto no VIOS e a comparação diária.

Guarda em dados/vigia.sqlite (fora do git):
  empresas  (chave, nome, cnpj, cnpj_situacao, primeira_vez, ultima_vez)
  processos (chave, numero, ci, empresa, tribunal, orgao, advogado, auxiliares, autor,
             primeira_vez, ultima_vez, ativo)
  rodadas   (data, linhas, completa, base, empresas_novas, processos_novos, sairam)
Funções puras (normalizar, numero_cnj, tribunal, comparar, relatorio) testadas em tests/test_vigia.py.

Regras:
- 1ª rodada = BASE: grava tudo e não lista nada como "novo" (senão o primeiro relatório teria 161 empresas novas).
- Lista incompleta (500 linhas = teto da tela, ou total do rodapé diferente): grava o que veio, mas NÃO marca
  saídas (um processo fora da lista pode só não ter cabido).
- Processo que sai da lista fica ativo=0; volta a ativo=1 se reaparecer. A fila do PJe (próxima fase) usa os
  processos do TRT7 vistos nos últimos DIAS_FILA dias.
"""
import re
import sqlite3
import unicodedata
from datetime import date, timedelta
from pathlib import Path

CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
DIAS_FILA = 30

ESQUEMA = """
CREATE TABLE IF NOT EXISTS empresas (
  chave TEXT PRIMARY KEY, nome TEXT, cnpj TEXT, cnpj_situacao TEXT, primeira_vez TEXT, ultima_vez TEXT);
CREATE TABLE IF NOT EXISTS processos (
  chave TEXT PRIMARY KEY, numero TEXT, ci TEXT, empresa TEXT, tribunal TEXT, orgao TEXT, advogado TEXT,
  auxiliares TEXT, autor TEXT, primeira_vez TEXT, ultima_vez TEXT, ativo INTEGER);
CREATE TABLE IF NOT EXISTS rodadas (
  data TEXT PRIMARY KEY, linhas INTEGER, completa INTEGER, base INTEGER, empresas_novas INTEGER,
  processos_novos INTEGER, sairam INTEGER);
"""


def normalizar(texto):
    """Sem acento, maiúsculo, um espaço só."""
    t = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


def numero_cnj(texto):
    m = CNJ.search(texto or "")
    return m.group(0) if m else ""


def tribunal(numero):
    """'5.07' (TRT7), '8.06' (TJCE)... a partir do número CNJ; '' sem número."""
    m = re.search(r"\.\d{4}\.(\d)\.(\d{2})\.\d{4}$", numero or "")
    return f"{m.group(1)}.{m.group(2)}" if m else ""


def eh_trt7(numero):
    return tribunal(numero) == "5.07"


def _autor(ativa):
    """Polo ativo sem o rótulo "Autor:" (para mostrar de onde pode vir uma execução)."""
    return re.sub(r"^\s*(autor|reclamante|requerente|exequente)\s*:\s*", "", ativa or "", flags=re.I).strip()


def preparar(linhas):
    """Linhas cruas do VIOS -> {chave_processo: registro}. Um processo com 2 clientes vira 1 registro."""
    out = {}
    for l in linhas:
        numero = numero_cnj(l.get("numero"))
        chave = numero or ("CI:" + str(l.get("ci") or "").strip())
        if chave == "CI:":
            continue
        empresa = normalizar(l.get("cliente"))
        reg = out.setdefault(chave, {
            "chave": chave, "numero": numero, "ci": str(l.get("ci") or ""), "empresa": empresa,
            "empresa_nome": (l.get("cliente") or "").strip(), "tribunal": tribunal(numero),
            "orgao": (l.get("orgao") or "").strip(), "advogado": (l.get("advogado") or "").strip(),
            "auxiliares": (l.get("auxiliares") or "").strip(), "autor": _autor(l.get("ativa")),
            "empresas": set()})
        if empresa:
            reg["empresas"].add(empresa)
    return out


def comparar(empresas_vistas, processos_ativos, processos_hoje, completa):
    """Pura. empresas_vistas: set de chaves; processos_ativos: set de chaves ativas antes de hoje;
    processos_hoje: dict de preparar(). Devolve {empresas_novas, processos_novos, sairam}."""
    empresas_hoje = {}
    for p in processos_hoje.values():
        for e in p["empresas"]:
            empresas_hoje.setdefault(e, []).append(p["chave"])
    novas = {e: sorted(ps) for e, ps in empresas_hoje.items() if e not in empresas_vistas}
    novos = sorted(k for k in processos_hoje if k not in processos_ativos)
    sairam = sorted(processos_ativos - set(processos_hoje)) if completa else []
    return {"empresas_novas": novas, "processos_novos": novos, "sairam": sairam}


class Estado:
    def __init__(self, caminho):
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)  # status/fila antes da 1ª rodada
        self.db = sqlite3.connect(str(caminho))
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)

    def fechar(self):
        self.db.close()

    def eh_base(self):
        return self.db.execute("SELECT COUNT(*) FROM rodadas").fetchone()[0] == 0

    def aplicar(self, linhas, completa, hoje=None, simular=False):
        """Compara a lista de hoje com o estado e grava (a menos que simular=True). Devolve o resultado."""
        hoje = (hoje or date.today()).isoformat()
        base = self.eh_base()
        procs = preparar(linhas)
        vistas = {r[0] for r in self.db.execute("SELECT chave FROM empresas")}
        ativos = {r[0] for r in self.db.execute("SELECT chave FROM processos WHERE ativo = 1")}
        conhecidos = {r[0] for r in self.db.execute("SELECT chave FROM processos")}
        res = comparar(vistas, ativos, procs, completa)
        res.update(base=base, simulado=simular, completa=completa, data=hoje, linhas=len(linhas), processos=procs,
                   voltaram=[k for k in res["processos_novos"] if k in conhecidos],
                   empresas_total=len({e for p in procs.values() for e in p["empresas"]}),
                   trt7=sum(1 for p in procs.values() if p["tribunal"] == "5.07"))
        res["processos_novos"] = [k for k in res["processos_novos"] if k not in conhecidos]
        if simular:
            return res
        cur = self.db.cursor()
        for p in procs.values():
            for e in p["empresas"]:
                cur.execute("INSERT INTO empresas (chave, nome, primeira_vez, ultima_vez) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT(chave) DO UPDATE SET ultima_vez = excluded.ultima_vez",
                            (e, p["empresa_nome"] if normalizar(p["empresa_nome"]) == e else e, hoje, hoje))
            cur.execute("INSERT INTO processos (chave, numero, ci, empresa, tribunal, orgao, advogado, auxiliares, autor, "
                        "primeira_vez, ultima_vez, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1) "
                        "ON CONFLICT(chave) DO UPDATE SET ultima_vez = excluded.ultima_vez, ativo = 1, "
                        "ci = excluded.ci, empresa = excluded.empresa, orgao = excluded.orgao, "
                        "advogado = excluded.advogado, auxiliares = excluded.auxiliares, autor = excluded.autor",
                        (p["chave"], p["numero"], p["ci"], p["empresa"], p["tribunal"], p["orgao"], p["advogado"],
                         p["auxiliares"], p["autor"], hoje, hoje))
        for k in res["sairam"]:
            cur.execute("UPDATE processos SET ativo = 0 WHERE chave = ?", (k,))
        cur.execute("INSERT OR REPLACE INTO rodadas VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (hoje, len(linhas), int(completa), int(base), 0 if base else len(res["empresas_novas"]),
                     0 if base else len(res["processos_novos"]), len(res["sairam"])))
        self.db.commit()
        return res

    def sem_cnpj(self, limite):
        """Empresas ativas ainda sem consulta de CNPJ (as mais recentes primeiro)."""
        return [dict(r) for r in self.db.execute(
            "SELECT chave, nome FROM empresas WHERE cnpj_situacao IS NULL ORDER BY primeira_vez DESC, chave LIMIT ?",
            (int(limite),))]

    def gravar_cnpj(self, chave, situacao, cnpj):
        self.db.execute("UPDATE empresas SET cnpj = ?, cnpj_situacao = ? WHERE chave = ?", (cnpj or None, situacao, chave))
        self.db.commit()

    def cnpjs(self, chaves):
        if not chaves:
            return {}
        q = ",".join("?" * len(chaves))
        return {r["chave"]: (r["cnpj"], r["cnpj_situacao"])
                for r in self.db.execute(f"SELECT chave, cnpj, cnpj_situacao FROM empresas WHERE chave IN ({q})", list(chaves))}

    def fila_pje(self, hoje=None, dias=DIAS_FILA):
        """Processos do TRT7 vistos no VIOS nos últimos `dias` dias (para a próxima fase: verificação no PJe)."""
        limite = ((hoje or date.today()) - timedelta(days=dias)).isoformat()
        return [dict(r) for r in self.db.execute(
            "SELECT chave, numero, empresa, orgao, ultima_vez, ativo FROM processos "
            "WHERE tribunal = '5.07' AND ultima_vez >= ? ORDER BY numero", (limite,))]

    def resumo(self):
        q = lambda sql: self.db.execute(sql).fetchone()[0]  # noqa: E731
        ultima = self.db.execute("SELECT * FROM rodadas ORDER BY data DESC LIMIT 1").fetchone()
        return {"empresas": q("SELECT COUNT(*) FROM empresas"),
                "empresas_com_cnpj": q("SELECT COUNT(*) FROM empresas WHERE cnpj_situacao = 'ok'"),
                "empresas_sem_consulta": q("SELECT COUNT(*) FROM empresas WHERE cnpj_situacao IS NULL"),
                "processos_ativos": q("SELECT COUNT(*) FROM processos WHERE ativo = 1"),
                "trt7_ativos": q("SELECT COUNT(*) FROM processos WHERE ativo = 1 AND tribunal = '5.07'"),
                "rodadas": q("SELECT COUNT(*) FROM rodadas"),
                "ultima_rodada": dict(ultima) if ultima else None}


def relatorio(res, cnpjs=None):
    """Texto do relatório do dia (saida/vigia_AAAA-MM-DD.txt)."""
    cnpjs = cnpjs or {}
    procs = res["processos"]
    L = [f"VIGIA VIOS → PJe · {res['data']}", "=" * 60,
         f"Lista do VIOS: {res['linhas']} linha(s), {len(procs)} processo(s), {res['empresas_total']} empresa(s), "
         f"{res['trt7']} no TRT7" + ("" if res["completa"] else "  [LISTA INCOMPLETA: saídas não marcadas]"), ""]
    if res["base"]:
        if res.get("simulado"):
            L += ["SIMULAÇÃO da primeira rodada: nada foi gravado. Rode sem --simular para criar a base.", ""]
        else:
            L += ["PRIMEIRA RODADA: base criada. Nada é listado como novo hoje; a partir da próxima rodada o vigia",
                  "mostra só empresas e processos que aparecerem depois de hoje.", ""]
        return "\n".join(L) + "\n"

    def doc(e):
        c, s = cnpjs.get(e, (None, None))
        return {"ok": f"CNPJ {c}", "varios": f"vários CNPJs: {c}", "pf": "pessoa física",
                "nao_achado": "CNPJ não achado no cadastro", "erro": "CNPJ: erro na consulta"}.get(s, "CNPJ a consultar")

    L.append(f"EMPRESAS NOVAS ({len(res['empresas_novas'])})")
    for e, ps in sorted(res["empresas_novas"].items()):
        L.append(f"  • {e} · {doc(e)}")
        for k in ps:
            p = procs[k]
            L.append(f"      {p['numero'] or k} · {p['orgao'] or '-'} · autor: {p['autor'] or '-'}"
                     f"{'  ← TRT7' if p['tribunal'] == '5.07' else ''}")
    L += ["", f"PROCESSOS NOVOS ({len(res['processos_novos'])})"]
    for k in res["processos_novos"]:
        p = procs[k]
        L.append(f"  • {p['numero'] or k} · {p['empresa']} · {p['orgao'] or '-'} · autor: {p['autor'] or '-'} · "
                 f"adv.: {p['advogado'] or '-'}{' (' + p['auxiliares'] + ')' if p['auxiliares'] else ''}"
                 f"{'  ← TRT7: entra na fila do PJe' if p['tribunal'] == '5.07' else ''}")
    if res.get("voltaram"):
        L += ["", f"VOLTARAM À LISTA ({len(res['voltaram'])})"] + [f"  • {k}" for k in res["voltaram"]]
    L += ["", f"SAÍRAM DA LISTA (arquivados/encerrados/mudou cadastro) ({len(res['sairam'])})"]
    L += [f"  • {k}" for k in res["sairam"]]
    return "\n".join(L) + "\n"
