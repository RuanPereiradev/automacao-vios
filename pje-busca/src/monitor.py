"""Monitor de processos (carteira do DPJ): última movimentação e teor de cada processo de uma lista (CSV do VIOS).

Fontes, da mais barata para a mais completa (decisão de 26/11/2026, caminho "Balanceado"):
  1. DJEN (API pública do CNJ, sem login): publicações com o texto (teor) do ato.
     - todo dia: as publicações da(s) OAB(s) do escritório (MONITOR_OABS, padrão 23104/CE) desde a última rodada,
       ligadas aos processos da lista (1 ou 2 consultas por dia);
     - em rodízio: MONITOR_DJEN_POR_DIA processos por número (pega publicação dirigida a outro advogado).
  2. DataJud (API pública do CNJ, chave pública do CNJ): movimentos padronizados (TPU), sem teor, com alguns dias de
     atraso. Em rodízio: MONITOR_DATAJUD_POR_DIA processos por dia.
  3. Tribunal (PJe, login pelo Loy Trust, Chrome do Mac): a linha do tempo do processo ("Detalhes do processo") e o
     texto do documento da última movimentação (só leitura; autorizado pelo Dr. Roneely em 26/11/2026).
     Em rodízio de madrugada: MONITOR_TRIBUNAL_POR_NOITE processos; quem teve novidade no DJEN ou no DataJud passa na
     frente. Leitores conferidos ao vivo em 26/11/2026:
       - PJe "legado" (TJCE 1º grau, TRF5): Consulta processos > número > clique no número (abre "Detalhes" numa
         janela: o robô intercepta o endereço) > linha do tempo (#divTimeLine) > documento pelo endereço de download;
       - PJe novo (TRT7, TRT22): Acervo Geral filtrado pelo número > "Detalhes do Processo" > linha do tempo
         (pje-timeline) > clique no documento > texto do visualizador.
     O robô não peticiona, não assina, não altera nada. Captcha: para e registra o erro (nunca tenta resolver).

Sem cobertura no tribunal nesta fase (só DJEN e DataJud): TRT7 2º grau (o login do 2º grau derruba a sessão do 1º),
TRF1 e tribunais de fora do Ceará/Piauí.

Saídas (fora do git): dados/monitor.sqlite (estado), saida/monitor_AAAA-MM-DD.txt (relatório). A página /monitor da
Vila dos Bots só lê o banco.
"""
import csv
import hashlib
import io
import json
import re
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

# sem nada no fim: o VIOS cola o próximo campo no número ("...8.06.0163Outros: 189-59...",
# "1.° Grau: 0002511-05.2012.8.06.00672.° Grau: 3002030-...")
CNJ = re.compile(r"(?<!\d)(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})")
TEXTO_MAX = 8000

# Justiça estadual: código do tribunal no número CNJ (J=8) -> sigla
TJ = {"01": "TJAC", "02": "TJAL", "03": "TJAP", "04": "TJAM", "05": "TJBA", "06": "TJCE", "07": "TJDFT", "08": "TJES",
      "09": "TJGO", "10": "TJMA", "11": "TJMT", "12": "TJMS", "13": "TJMG", "14": "TJPA", "15": "TJPB", "16": "TJPR",
      "17": "TJPE", "18": "TJPI", "19": "TJRJ", "20": "TJRN", "21": "TJRS", "22": "TJRO", "23": "TJRR", "24": "TJSC",
      "25": "TJSE", "26": "TJSP", "27": "TJTO"}

# (tribunal, grau) -> (portal no Loy Trust, tipo de PJe). O endereço do PJe vem da aba que o Loy abre.
PORTAIS = {
    ("TJCE", "1"): ("TJCE(PJE) - 1º Grau", "legado"),
    ("TJCE", "2"): ("TJCE(PJE) - 2º Grau", "legado"),
    ("TRF5", "1"): ("TRF5(PJE) - 1º Grau", "legado"),
    ("TRT7", "1"): ("TRT7CE - 1º Grau", "kz"),
    ("TRT22", "1"): ("TRT22PI - 1º Grau", "kz"),
}
ORDEM_PORTAIS = [("TJCE", "1"), ("TJCE", "2"), ("TRF5", "1"), ("TRT22", "1"), ("TRT7", "1")]

DATAJUD = "https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search"
# chave PÚBLICA do DataJud, divulgada pelo CNJ para todos (não é segredo); trocar por MONITOR_DATAJUD_CHAVE se mudar
DATAJUD_CHAVE = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="

PADRAO = {"MONITOR_OABS": "23104/CE", "MONITOR_DJEN_POR_DIA": "150", "MONITOR_DATAJUD_POR_DIA": "250",
          "MONITOR_TRIBUNAL_POR_NOITE": "150", "MONITOR_PAUSA_S": "1.5", "MONITOR_PAUSA_TRIBUNAL_S": "2",
          "MONITOR_LER_TEOR": "1"}

MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6, "jul": 7, "ago": 8, "set": 9, "out": 10,
         "nov": 11, "dez": 12}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS mon_processos (
  numero TEXT PRIMARY KEY, tribunal TEXT, grau TEXT, sistema TEXT, vara TEXT, cliente TEXT, area TEXT, acao TEXT,
  situacao TEXT, polo TEXT, parte_ativa TEXT, parte_passiva TEXT, ci TEXT, ativo INTEGER DEFAULT 1,
  importado_em TEXT, saiu_em TEXT);
CREATE TABLE IF NOT EXISTS mon_estado (
  numero TEXT PRIMARY KEY,
  djen_data TEXT, djen_tipo TEXT, djen_orgao TEXT, djen_texto TEXT, djen_qtd INTEGER, djen_visto_em TEXT, djen_erro TEXT,
  dj_data TEXT, dj_mov TEXT, dj_qtd INTEGER, dj_visto_em TEXT, dj_erro TEXT,
  trib_data TEXT, trib_hora TEXT, trib_mov TEXT, trib_doc TEXT, trib_teor TEXT, trib_teor_de TEXT,
  trib_assinatura TEXT, trib_visto_em TEXT, trib_erro TEXT,
  novidade_em TEXT, novidade_fonte TEXT, prioridade INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS mon_movimentos (
  numero TEXT, fonte TEXT, data TEXT, descricao TEXT, documento TEXT, teor TEXT, visto_em TEXT,
  PRIMARY KEY (numero, fonte, data, descricao));
CREATE TABLE IF NOT EXISTS mon_rodadas (inicio TEXT, fim TEXT, tipo TEXT, resumo TEXT);
CREATE TABLE IF NOT EXISTS mon_config (chave TEXT PRIMARY KEY, valor TEXT);
"""


class MonitorErro(Exception):
    pass


# ---------------------------------------------------------------- funções puras

def tribunal_de(numero):
    """(sigla, grau, sistema) a partir do número CNJ. grau '2' quando a origem é 0000 (tribunal); sistema 'legado'/'kz'
    quando o robô lê no PJe, 'api' quando só DJEN e DataJud."""
    m = CNJ.search(numero or "")
    if not m:
        return "", "", "api"
    j, tr, origem = m.group(4), m.group(5), m.group(6)
    if j == "8":
        sigla = TJ.get(tr, f"TJ{tr}")
    elif j == "5":
        sigla = "TST" if tr == "00" else f"TRT{int(tr)}"
    elif j == "4":
        sigla = f"TRF{int(tr)}"
    else:
        sigla = f"J{j}.{tr}"
    grau = "2" if origem == "0000" else "1"
    sistema = PORTAIS.get((sigla, grau), ("", "api"))[1]
    return sigla, grau, sistema


def alias_datajud(sigla):
    return sigla.lower() if sigla else ""


def data_iso(texto):
    """'23 jun 2025', '25 nov. 2026', '2026-11-25T19:07:54Z', '25/11/2026' -> '2025-06-23'; '' se não der."""
    t = (texto or "").strip().lower()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return m.group(0)[:10]
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"^(\d{1,2})\s+([a-zç]{3})[a-zç]*\.?\s+(\d{4})", t)
    if m and m.group(2) in MESES:
        return f"{int(m.group(3)):04d}-{MESES[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return ""


def _limpo(v):
    """Valor de célula do CSV do VIOS: tira o ="..." do Excel e os espaços."""
    v = (v or "").strip()
    m = re.match(r'^="?(.*?)"?$', v)
    return (m.group(1) if m else v).strip()


def ler_csv(conteudo):
    """CSV exportado do VIOS (lista de processos; ';', latin-1) -> [processo] únicos pelo número CNJ.
    Linhas sem número CNJ (administrativos, "Total:", "Média:") ficam de fora. Devolve (processos, sem_cnj)."""
    if isinstance(conteudo, bytes):
        try:
            texto = conteudo.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = conteudo.decode("latin-1")
    else:
        texto = conteudo
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    if not linhas:
        return [], 0
    cab = [_limpo(c) for c in linhas[0]]
    col = {nome: i for i, nome in enumerate(cab)}
    if "Número" not in col:
        raise MonitorErro("o CSV não tem a coluna 'Número' (é a lista de processos exportada do VIOS?)")

    def v(linha, nome):
        i = col.get(nome)
        return _limpo(linha[i]) if i is not None and i < len(linha) else ""

    vistos, sem = {}, 0
    for linha in linhas[1:]:
        m = CNJ.search(v(linha, "Número"))
        if not m:
            sem += 1
            continue
        numero = m.group(0)
        sigla, grau, sistema = tribunal_de(numero)
        p = {"numero": numero, "tribunal": sigla, "grau": grau, "sistema": sistema,
             "vara": v(linha, "Comarcas / Tribunais / Órgãos Adm."), "cliente": v(linha, "Cliente"),
             "area": v(linha, "Área"), "acao": v(linha, "Ação"), "situacao": v(linha, "Situação do Processo"),
             "polo": v(linha, "Polo do cliente"), "parte_ativa": v(linha, "Parte ativa"),
             "parte_passiva": v(linha, "Parte passiva"), "ci": v(linha, "CI"), "vinculo": v(linha, "Vínculo")}
        atual = vistos.get(numero)
        # o mesmo número pode vir como principal e como apenso: fica o principal
        if atual is None or (atual["vinculo"] != "PROCESSO PRINCIPAL" and p["vinculo"] == "PROCESSO PRINCIPAL"):
            vistos[numero] = p
    return list(vistos.values()), sem


def ultimo_djen(itens):
    """Publicações do DJEN de um processo -> (andamentos sem repetição, mais recente primeiro)."""
    import vigia_djen as VD
    return VD.andamentos(itens)


def ultimo_datajud(resposta):
    """Resposta do DataJud -> {data, hora, mov, qtd, grau, orgao} do movimento mais recente (de todos os graus)."""
    hits = ((resposta or {}).get("hits") or {}).get("hits") or []
    movs = []
    for h in hits:
        s = h.get("_source") or {}
        for mv in s.get("movimentos") or []:
            comp = "; ".join(f"{c.get('nome')}: {c.get('descricao') or c.get('valor')}".strip(": ")
                             for c in mv.get("complementosTabelados") or [] if c.get("nome") or c.get("descricao"))
            movs.append({"dataHora": mv.get("dataHora") or "", "nome": (mv.get("nome") or "").strip(),
                         "comp": comp, "grau": s.get("grau") or "",
                         "orgao": ((s.get("orgaoJulgador") or {}).get("nome") or "").strip()})
    if not movs:
        return None
    movs.sort(key=lambda x: x["dataHora"], reverse=True)
    u = movs[0]
    return {"data": u["dataHora"][:10], "hora": u["dataHora"][11:16], "qtd": len(movs), "grau": u["grau"],
            "orgao": u["orgao"], "mov": u["nome"] + (f" ({u['comp']})" if u["comp"] else ""), "todos": movs[:20]}


def assinatura(*partes):
    return hashlib.sha1("|".join(str(p or "") for p in partes).encode("utf-8")).hexdigest()[:16]


def id_documento(doc):
    """'161436200 - Petição (Outras)' -> '161436200'; '6306d45' -> '6306d45'."""
    m = re.match(r"^\s*([0-9a-f]{6,})\b", doc or "", re.I)
    return m.group(1) if m else ""


def escolher_documento(itens):
    """Documento para o teor: o da última movimentação; se ela não tem documento, o mais recente entre as 5 primeiras.
    Devolve (item, id) ou (None, '')."""
    for it in itens[:5]:
        for doc in it.get("docs") or ([it["doc"]] if it.get("doc") else []):
            i = id_documento(doc)
            if i:
                return it, i
    return None, ""


# ---------------------------------------------------------------- estado

class Estado:
    def __init__(self, caminho):
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(caminho), timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(ESQUEMA)

    def fechar(self):
        self.db.commit()
        self.db.close()

    def config(self, chave, padrao=""):
        r = self.db.execute("SELECT valor FROM mon_config WHERE chave = ?", (chave,)).fetchone()
        return r[0] if r else padrao

    def gravar_config(self, chave, valor):
        self.db.execute("INSERT INTO mon_config VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                        (chave, str(valor)))

    def importar(self, processos, hoje, completa=True):
        """Grava a carteira. Com completa=True, quem não veio na lista nova sai (ativo=0), mas o histórico fica."""
        hoje = str(hoje)
        antes = {r[0] for r in self.db.execute("SELECT numero FROM mon_processos WHERE ativo = 1")}
        novos = 0
        for p in processos:
            existe = self.db.execute("SELECT 1 FROM mon_processos WHERE numero = ?", (p["numero"],)).fetchone()
            campos = ("tribunal", "grau", "sistema", "vara", "cliente", "area", "acao", "situacao", "polo",
                      "parte_ativa", "parte_passiva", "ci")
            if existe:
                self.db.execute(f"UPDATE mon_processos SET {', '.join(c + ' = ?' for c in campos)}, ativo = 1, "
                                "saiu_em = NULL WHERE numero = ?", [p.get(c, "") for c in campos] + [p["numero"]])
            else:
                novos += 1
                self.db.execute(f"INSERT INTO mon_processos (numero, {', '.join(campos)}, ativo, importado_em) "
                                f"VALUES (?, {', '.join('?' for _ in campos)}, 1, ?)",
                                [p["numero"]] + [p.get(c, "") for c in campos] + [hoje])
            self.db.execute("INSERT OR IGNORE INTO mon_estado (numero) VALUES (?)", (p["numero"],))
        sairam = []
        if completa:
            atuais = {p["numero"] for p in processos}
            sairam = sorted(antes - atuais)
            for n in sairam:
                self.db.execute("UPDATE mon_processos SET ativo = 0, saiu_em = ? WHERE numero = ?", (hoje, n))
        self.db.commit()
        return {"total": len(processos), "novos": novos, "sairam": sairam}

    def numeros(self):
        return {r[0] for r in self.db.execute("SELECT numero FROM mon_processos WHERE ativo = 1")}

    def processo(self, numero):
        r = self.db.execute("SELECT p.*, e.* FROM mon_processos p JOIN mon_estado e USING (numero) WHERE numero = ?",
                            (numero,)).fetchone()
        return dict(r) if r else None

    def fila(self, campo, limite):
        """Rodízio: nunca vistos primeiro, depois os vistos há mais tempo."""
        return [r[0] for r in self.db.execute(
            f"SELECT p.numero FROM mon_processos p JOIN mon_estado e USING (numero) WHERE p.ativo = 1 "
            f"ORDER BY ({campo} IS NOT NULL), {campo}, p.numero LIMIT ?", (int(limite),))]

    def fila_tribunal(self, limite):
        """Rodízio do tribunal: com novidade (prioridade) primeiro, depois nunca lidos, depois os lidos há mais tempo.
        Só processos com leitor no PJe (sistema legado/kz)."""
        return [dict(r) for r in self.db.execute(
            "SELECT p.numero, p.tribunal, p.grau, p.sistema FROM mon_processos p JOIN mon_estado e USING (numero) "
            "WHERE p.ativo = 1 AND p.sistema IN ('legado', 'kz') "
            "ORDER BY e.prioridade DESC, (e.trib_visto_em IS NOT NULL), e.trib_visto_em, p.numero LIMIT ?",
            (int(limite),))]

    def _novidade(self, numero, hoje, fonte):
        self.db.execute("UPDATE mon_estado SET novidade_em = ?, novidade_fonte = ?, prioridade = 1 WHERE numero = ?",
                        (str(hoje), fonte, numero))

    def gravar_djen(self, numero, andamentos, hoje, erro=""):
        """Publicações do processo (já sem repetição). Novidade se a mais recente é mais nova que a já vista."""
        hoje = str(hoje)
        if erro:
            self.db.execute("UPDATE mon_estado SET djen_erro = ?, djen_visto_em = ? WHERE numero = ?",
                            (erro[:300], hoje, numero))
            return False
        atual = self.db.execute("SELECT djen_data, djen_visto_em FROM mon_estado WHERE numero = ?", (numero,)).fetchone()
        for a in andamentos:
            self.db.execute("INSERT OR IGNORE INTO mon_movimentos VALUES (?, 'djen', ?, ?, ?, ?, ?)",
                            (numero, a["data"], f"{a['tipo']}: {a['texto'][:120]}", a.get("documento", ""),
                             a["texto"][:TEXTO_MAX], hoje))
        novo = False
        if andamentos:
            u = andamentos[0]
            antes = atual["djen_data"] if atual else None
            # novidade só depois da 1ª leitura (a 1ª é a base) e se a publicação é mais nova
            novo = bool(atual and atual["djen_visto_em"] and (not antes or u["data"] > antes))
            if not antes or u["data"] >= antes:
                self.db.execute("UPDATE mon_estado SET djen_data = ?, djen_tipo = ?, djen_orgao = ?, djen_texto = ? "
                                "WHERE numero = ?", (u["data"], u["tipo"], u["orgao"], u["texto"][:TEXTO_MAX], numero))
        qtd = self.db.execute("SELECT COUNT(*) FROM mon_movimentos WHERE numero = ? AND fonte = 'djen'",
                              (numero,)).fetchone()[0]
        self.db.execute("UPDATE mon_estado SET djen_qtd = ?, djen_visto_em = ?, djen_erro = '' WHERE numero = ?",
                        (qtd, hoje, numero))
        if novo:
            self._novidade(numero, hoje, "DJEN")
        return novo

    def gravar_datajud(self, numero, ultimo, hoje, erro=""):
        hoje = str(hoje)
        if erro:
            self.db.execute("UPDATE mon_estado SET dj_erro = ?, dj_visto_em = ? WHERE numero = ?", (erro[:300], hoje, numero))
            return False
        atual = self.db.execute("SELECT dj_data, dj_mov, dj_visto_em FROM mon_estado WHERE numero = ?",
                                (numero,)).fetchone()
        novo = False
        if ultimo:
            novo = bool(atual and atual["dj_visto_em"] and
                        (ultimo["data"], ultimo["mov"]) != (atual["dj_data"], atual["dj_mov"]) and
                        ultimo["data"] >= (atual["dj_data"] or ""))
            self.db.execute("UPDATE mon_estado SET dj_data = ?, dj_mov = ?, dj_qtd = ? WHERE numero = ?",
                            (ultimo["data"], ultimo["mov"][:500], ultimo["qtd"], numero))
            for mv in ultimo.get("todos") or []:
                self.db.execute("INSERT OR IGNORE INTO mon_movimentos VALUES (?, 'datajud', ?, ?, '', '', ?)",
                                (numero, mv["dataHora"][:16].replace("T", " "),
                                 mv["nome"] + (f" ({mv['comp']})" if mv["comp"] else ""), hoje))
        self.db.execute("UPDATE mon_estado SET dj_visto_em = ?, dj_erro = '' WHERE numero = ?", (hoje, numero))
        if novo:
            self._novidade(numero, hoje, "DataJud")
        return novo

    def gravar_tribunal(self, numero, lido, hoje):
        """Leitura do PJe: {ok, erro, itens:[{data, hora, mov, docs/doc}], teor, teor_de}."""
        hoje = str(hoje)
        if not lido.get("ok"):
            self.db.execute("UPDATE mon_estado SET trib_erro = ?, trib_visto_em = ?, prioridade = 0 WHERE numero = ?",
                            ((lido.get("erro") or "erro")[:300], hoje, numero))
            return False
        itens = lido.get("itens") or []
        atual = self.db.execute("SELECT trib_assinatura, trib_visto_em, trib_teor, trib_teor_de FROM mon_estado "
                                "WHERE numero = ?", (numero,)).fetchone()
        u = itens[0] if itens else {}
        docs = u.get("docs") or ([u["doc"]] if u.get("doc") else [])
        mov = u.get("mov") or (docs[0] if docs else "")
        ass = assinatura(u.get("data"), u.get("hora"), mov, "|".join(docs))
        novo = bool(atual and atual["trib_visto_em"] and atual["trib_assinatura"] and atual["trib_assinatura"] != ass)
        teor = lido.get("teor")
        teor_de = lido.get("teor_de") or ""
        if teor is None and atual and atual["trib_assinatura"] == ass:
            teor, teor_de = atual["trib_teor"], atual["trib_teor_de"]  # mesma movimentação: mantém o teor já lido
        self.db.execute("UPDATE mon_estado SET trib_data = ?, trib_hora = ?, trib_mov = ?, trib_doc = ?, trib_teor = ?, "
                        "trib_teor_de = ?, trib_assinatura = ?, trib_visto_em = ?, trib_erro = '', prioridade = 0 "
                        "WHERE numero = ?", (u.get("data", ""), u.get("hora", ""), mov[:500], "; ".join(docs)[:500],
                                             (teor or "")[:TEXTO_MAX], teor_de[:300], ass, hoje, numero))
        for it in itens[:30]:
            d = it.get("docs") or ([it["doc"]] if it.get("doc") else [])
            self.db.execute("INSERT OR IGNORE INTO mon_movimentos VALUES (?, 'tribunal', ?, ?, ?, '', ?)",
                            (numero, f"{it.get('data', '')} {it.get('hora', '')}".strip(),
                             (it.get("mov") or (d[0] if d else ""))[:500], "; ".join(d)[:500], hoje))
        if novo:
            self._novidade(numero, hoje, "Tribunal")
        return novo

    def rodada(self, inicio, tipo, resumo):
        self.db.execute("INSERT INTO mon_rodadas VALUES (?, ?, ?, ?)",
                        (inicio, datetime.now().isoformat(timespec="seconds"), tipo,
                         json.dumps(resumo, ensure_ascii=False)))
        self.db.commit()


# ---------------------------------------------------------------- DJEN e DataJud

def djen_por_oab(oab, uf, inicio, fim, abrir=None, pausa=1.0, max_paginas=30):
    """Publicações da OAB no período (todas as páginas, até max_paginas de 100)."""
    import urllib.parse
    import vigia_djen as VD
    abrir = abrir or VD._abrir
    itens, pagina = [], 1
    while pagina <= max_paginas:
        q = urllib.parse.urlencode({"numeroOab": oab, "ufOab": uf, "dataDisponibilizacaoInicio": str(inicio),
                                    "dataDisponibilizacaoFim": str(fim), "itensPorPagina": 100, "pagina": pagina})
        dados = abrir(f"{VD.API}?{q}")
        lote = dados.get("items") or []
        itens += lote
        if len(lote) < 100 or len(itens) >= (dados.get("count") or 0):
            break
        pagina += 1
        time.sleep(pausa)
    return itens


def _numero_item(item):
    m = CNJ.search(item.get("numeroprocessocommascara") or "")
    if m:
        return m.group(0)
    d = re.sub(r"\D", "", item.get("numero_processo") or "")
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:20]}" if len(d) == 20 else ""


def consultar_datajud(numero, sigla, chave=DATAJUD_CHAVE, abrir=None):
    """Consulta o DataJud pelo número (só dígitos). `abrir(url, corpo, cabecalhos)` existe para os testes."""
    url = DATAJUD.format(alias=alias_datajud(sigla))
    corpo = json.dumps({"query": {"match": {"numeroProcesso": re.sub(r"\D", "", numero)}}}).encode("utf-8")
    cab = {"Authorization": f"APIKey {chave}", "Content-Type": "application/json"}
    if abrir:
        return abrir(url, corpo, cab)
    req = urllib.request.Request(url, data=corpo, headers=cab, method="POST")
    for n in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < 3:
                time.sleep(10 * n)
                continue
            raise MonitorErro(f"DataJud respondeu HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if n < 3:
                time.sleep(5 * n)
                continue
            raise MonitorErro(f"DataJud sem resposta: {e}")
    raise MonitorErro("DataJud sem resposta")


def rodar_api(est, cfg, hoje=None, tudo=False, djen_oab=djen_por_oab, djen_numero=None, datajud=consultar_datajud,
              pausa=None, aviso=print):
    """Rodada diária sem login: DJEN pela OAB (desde a última vez), DJEN e DataJud por número em rodízio.
    Com tudo=True, consulta todos os processos por número (base inicial)."""
    import vigia_djen as VD
    hoje = hoje or date.today()
    djen_numero = djen_numero or (lambda n: VD.consultar_numero(n, itens=100))
    pausa = float(cfg.get("MONITOR_PAUSA_S", PADRAO["MONITOR_PAUSA_S"])) if pausa is None else pausa
    inicio = datetime.now().isoformat(timespec="seconds")
    res = {"data": str(hoje), "oab_publicacoes": 0, "oab_processos": 0, "djen": 0, "datajud": 0, "novidades": [],
           "erros": [], "fora_da_lista": 0}
    numeros = est.numeros()
    if not numeros:
        raise MonitorErro("a carteira está vazia: rode antes  python3 vigia.py monitor-importar <arquivo.csv>")

    # 1) DJEN pela OAB, desde a última rodada (no máximo 30 dias para trás)
    ultima = est.config("djen_oab_ate")
    desde = date.fromisoformat(ultima) - timedelta(days=1) if ultima else hoje - timedelta(days=7)
    desde = max(desde, hoje - timedelta(days=30))
    por_processo = {}
    for oab in [o.strip() for o in (cfg.get("MONITOR_OABS") or PADRAO["MONITOR_OABS"]).split(";") if o.strip()]:
        num, _, uf = oab.partition("/")
        try:
            itens = djen_oab(re.sub(r"\D", "", num), (uf or "CE").upper(), desde, hoje, pausa=pausa)
        except Exception as e:  # noqa: BLE001
            res["erros"].append(f"DJEN OAB {oab}: {e}")
            continue
        res["oab_publicacoes"] += len(itens)
        for it in itens:
            n = _numero_item(it)
            if n in numeros:
                por_processo.setdefault(n, []).append(it)
            elif n:
                res["fora_da_lista"] += 1
        time.sleep(pausa)
    vistos_oab = set()
    for n, itens in por_processo.items():
        # a OAB traz só as publicações do período: completa com a busca pelo número (para a lista ficar inteira)
        try:
            itens = djen_numero(n)
        except Exception:  # noqa: BLE001 — fica com o que a OAB trouxe
            pass
        if est.gravar_djen(n, VD.andamentos(itens), hoje):
            res["novidades"].append((n, "DJEN"))
        vistos_oab.add(n)
        time.sleep(pausa)
    res["oab_processos"] = len(por_processo)
    if not res["erros"]:
        est.gravar_config("djen_oab_ate", str(hoje))
    est.db.commit()

    # 2) DJEN por número, em rodízio (pega publicação dirigida a outro advogado)
    limite = len(numeros) if tudo else int(cfg.get("MONITOR_DJEN_POR_DIA") or PADRAO["MONITOR_DJEN_POR_DIA"])
    fila = [n for n in est.fila("e.djen_visto_em", limite + len(vistos_oab)) if n not in vistos_oab][:limite]
    for k, n in enumerate(fila, 1):
        try:
            if est.gravar_djen(n, VD.andamentos(djen_numero(n)), hoje):
                res["novidades"].append((n, "DJEN"))
            res["djen"] += 1
        except Exception as e:  # noqa: BLE001
            est.gravar_djen(n, [], hoje, erro=str(e))
            res["erros"].append(f"DJEN {n}: {e}")
        if k % 50 == 0:
            est.db.commit()
            aviso(f"DJEN por número: {k}/{len(fila)}")
        time.sleep(pausa)
    est.db.commit()

    # 3) DataJud, em rodízio
    chave = cfg.get("MONITOR_DATAJUD_CHAVE") or DATAJUD_CHAVE
    limite = len(numeros) if tudo else int(cfg.get("MONITOR_DATAJUD_POR_DIA") or PADRAO["MONITOR_DATAJUD_POR_DIA"])
    erros_seguidos = 0
    for k, n in enumerate(est.fila("e.dj_visto_em", limite), 1):
        sigla = tribunal_de(n)[0]
        try:
            u = ultimo_datajud(datajud(n, sigla, chave))
            if est.gravar_datajud(n, u, hoje):
                res["novidades"].append((n, "DataJud"))
            res["datajud"] += 1
            erros_seguidos = 0
        except Exception as e:  # noqa: BLE001
            est.gravar_datajud(n, None, hoje, erro=str(e))
            res["erros"].append(f"DataJud {n}: {e}")
            erros_seguidos += 1
            if erros_seguidos >= 10:
                res["erros"].append("DataJud: 10 erros seguidos, parei o DataJud nesta rodada")
                break
        if k % 50 == 0:
            est.db.commit()
            aviso(f"DataJud: {k}/{limite}")
        time.sleep(pausa)
    est.rodada(inicio, "api", {k: (len(v) if isinstance(v, list) else v) for k, v in res.items()})
    return res


# ---------------------------------------------------------------- leitura no PJe (Chrome do Mac)

# intercepta o window.open da página (o PJe abre "Detalhes do processo" numa janela nova): o endereço fica num
# atributo do <html>. Roda no "mundo" da página por um <script>, porque o JavaScript do AppleScript roda isolado.
_GANCHO = (r"""var _de=document.documentElement; if(!_de.getAttribute('data-monitor-gancho')){var _s=document.createElement('script');"""
           r"""_s.textContent="window.open=function(u){document.documentElement.setAttribute('data-monitor-popup',String(u));return null;};";"""
           r"""_de.appendChild(_s); _de.setAttribute('data-monitor-gancho','1');}""")

JS_POPUP = "document.documentElement.getAttribute('data-monitor-popup') || ''"

JS_LEG_PESQUISAR = r"""(function(n){
  var m = n.match(/^(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})$/);
  if (!m) return JSON.stringify({ok: false, erro: 'número inválido'});
  var campos = [['numeroSequencial', m[1]], ['numeroDigitoVerificador', m[2]], ['Ano', m[3]], ['ramoJustica', m[4]],
                ['respectivoTribunal', m[5]], ['NumeroOrgaoJustica', m[6]]];
  for (var i = 0; i < campos.length; i++) {
    var e = document.getElementById('fPP:numeroProcesso:' + campos[i][0]);
    if (!e) { if (i === 3 || i === 4) continue; return JSON.stringify({ok: false, erro: 'campo ' + campos[i][0] + ' não encontrado (a tela de consulta mudou?)'}); }
    if (e.readOnly || e.disabled) continue;
    e.value = campos[i][1];
    e.dispatchEvent(new Event('change', {bubbles: true})); e.dispatchEvent(new Event('blur', {bubbles: true}));
  }
  """ + _GANCHO + r"""
  _de.removeAttribute('data-monitor-popup');
  var b = document.getElementById('fPP:searchProcessos');
  if (!b) return JSON.stringify({ok: false, erro: 'botão Pesquisar não encontrado'});
  b.click();
  return JSON.stringify({ok: true});
})"""

JS_LEG_RESULTADO = r"""(function(n, clicar){
  var a = null;
  var links = document.querySelectorAll('table a');
  for (var i = 0; i < links.length && !a; i++) if ((links[i].innerText || '').trim() === n) a = links[i];
  if (a) {
    var tr = a.closest('tr'), cel = tr ? Array.prototype.map.call(tr.cells, function(c){return (c.innerText || '').trim();}) : [];
    if (clicar) a.click();
    return JSON.stringify({estado: 'achou', ultima: cel.length ? cel[cel.length - 1] : '', linha: cel.join(' | ').slice(0, 600)});
  }
  var t = document.body ? document.body.innerText : '';
  if (/captcha|não sou (um )?robô/i.test(t)) return JSON.stringify({estado: 'captcha'});
  if (/\b(nenhum|0) (processo|resultado|registro)|Foram encontrados:\s*0\b|não retornou/i.test(t)) return JSON.stringify({estado: 'vazio'});
  return JSON.stringify({estado: 'esperando'});
})"""

JS_LEG_TIMELINE = r"""(function(){
  var el = document.getElementById('divTimeLine:eventosTimeLineElement');
  if (!el) return JSON.stringify({ok: false, esperando: true});
  var data = '', itens = [];
  Array.prototype.forEach.call(el.children, function(c){
    var cl = c.className || '';
    if (/\bdata\b/.test(cl)) { var d = c.querySelector('.data-interna'); if (d && d.innerText.trim()) data = d.innerText.trim(); return; }
    if (!/\binterno\b/.test(cl)) return;
    var mov = c.querySelector('.texto-movimento');
    var docs = Array.prototype.map.call(c.querySelectorAll('.anexos a span'), function(s){return s.innerText.trim();})
      .filter(function(x){return x;});
    var h = (c.innerText || '').match(/\b(\d{2}:\d{2})\b/);
    itens.push({data: data, hora: h ? h[1] : '', mov: mov ? mov.innerText.replace(/\s+/g, ' ').trim() : '', docs: docs});
  });
  return JSON.stringify({ok: true, itens: itens.slice(0, 30)});
})()"""

# baixa o documento (mesma sessão) e guarda o texto num atributo do <html>; PDF fica marcado (o teor vem do DJEN)
JS_TEOR_BAIXAR = r"""(function(u){
  var de = document.documentElement; de.setAttribute('data-monitor-teor', '');
  fetch(u, {credentials: 'same-origin'}).then(function(r){
    if (!r.ok) throw new Error('HTTP ' + r.status);
    var ct = r.headers.get('content-type') || '';
    if (/pdf|octet-stream/i.test(ct)) return '§PDF';
    return r.text().then(function(h){
      var d = new DOMParser().parseFromString(h, 'text/html');
      Array.prototype.forEach.call(d.querySelectorAll('script,style'), function(x){x.remove();});
      return ((d.body ? d.body.textContent : h) || '').replace(/\s+/g, ' ').trim();
    });
  }).then(function(t){ de.setAttribute('data-monitor-teor', JSON.stringify({ok: true, texto: t.slice(0, 8000)})); })
    .catch(function(e){ de.setAttribute('data-monitor-teor', JSON.stringify({ok: false, erro: String(e).slice(0, 200)})); });
  return 'ok';
})"""

JS_TEOR_LER = "document.documentElement.getAttribute('data-monitor-teor') || ''"

JS_KZ_ACERVO = r"""(function(n){
  """ + _GANCHO + r"""
  var linhas = Array.prototype.filter.call(document.querySelectorAll('tbody tr, mat-row'), function(r){
    return (r.innerText || '').indexOf(n) >= 0;});
  if (!linhas.length) {
    var t = document.body ? document.body.innerText : '';
    var pag = document.querySelector('pje-paginador');
    var vazio = /Nenhum (registro|processo)|Não há processos|não foram encontrados/i.test(t) ||
                (pag && /\b0\s*-\s*0 de 0\b|de 0\s*$/.test((pag.innerText || '').trim()));
    return JSON.stringify({estado: vazio ? 'vazio' : 'esperando'});
  }
  // Acervo: aria-label "Detalhes do Processo ..."; Arquivados: botão sem rótulo com o ícone KZ (tooltip) e accesskey "d"
  var b = Array.prototype.find.call(linhas[0].querySelectorAll('button'), function(x){
    return /^Detalhes do Processo/i.test(x.getAttribute('aria-label') || '') ||
           !!x.querySelector('[mattooltip="Detalhes do Processo"]') || x.getAttribute('accesskey') === 'd';});
  if (!b) return JSON.stringify({estado: 'sem_botao'});
  _de.removeAttribute('data-monitor-popup');
  b.click();
  return JSON.stringify({estado: 'achou'});
})"""

JS_KZ_TIMELINE = r"""(function(){
  var lis = document.querySelectorAll('pje-timeline li.tl-item-container');
  if (!lis.length) return JSON.stringify({ok: false, esperando: true});
  var data = '', itens = [];
  Array.prototype.forEach.call(lis, function(li){
    var t = li.querySelector('h3.tl-data time'); if (t && t.innerText.trim()) data = t.innerText.trim();
    var card = li.querySelector('mat-card, .tl-item-desc');
    var txt = card ? card.innerText.replace(/\s+/g, ' ').trim() : '';
    var a = li.querySelector('a.tl-documento'); var id = a ? (a.id || '').replace('abrirdoc_', '') : '';
    var h = txt.match(/\b(\d{2}:\d{2})\s*$/);
    itens.push({data: data, hora: h ? h[1] : '', mov: h ? txt.slice(0, h.index).trim() : txt, doc: id});
  });
  return JSON.stringify({ok: true, itens: itens.slice(0, 30)});
})()"""

JS_KZ_ABRIR_DOC = r"""(function(id){ var a = document.getElementById('abrirdoc_' + id); if (!a) return 'sem'; a.click(); return 'ok'; })"""

JS_KZ_LER_DOC = r"""(function(id){
  var h = document.querySelector('pje-cabecalho-documento');
  if (!h || (h.innerText || '').indexOf('Id ' + id) < 0) return JSON.stringify({pronto: false});
  var t = '';
  try {
    var o = document.querySelector('pje-historico-scroll-documento object, pje-historico-scroll-documento iframe');
    var d = o && o.contentDocument, v = d && (d.querySelector('#viewer') || d.body);
    t = v ? (v.innerText || '').replace(/\s+/g, ' ').trim() : '';
  } catch (e) {}
  if (!t) { var hd = document.querySelector('pje-historico-scroll-documento'); t = hd ? (hd.innerText || '').replace(/\s+/g, ' ').trim() : ''; }
  return JSON.stringify({pronto: t.length > 40, texto: t.slice(0, 8000)});
})"""

SAIU_DA_SESSAO = re.compile(r"login\.seam|/auth/|sso\.|/login|authenticate|acesso-negado", re.I)


def _esperar(cond, maximo, passo=1.0, dormir=time.sleep, relogio=time.monotonic):
    fim, v = relogio() + maximo, None
    while relogio() < fim:
        try:
            v = cond()
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass
        dormir(passo)
    return v


def base_de(url):
    """'https://pje.tjce.jus.br/pje1grau/Painel/...' -> ('https://pje.tjce.jus.br', 'https://pje.tjce.jus.br/pje1grau')."""
    m = re.match(r"^(https://[^/]+)(/[^/?#]+)", url or "")
    if not m:
        raise MonitorErro(f"endereço do PJe inesperado: {url}")
    return m.group(1), m.group(1) + m.group(2)


class Leitor:
    """Lê um processo no PJe já logado, numa aba. `js(código)`, `ir(url)`, `url()` e `frente()` vêm do chrome_mac;
    nos testes, de um Chrome de mentira."""

    def __init__(self, tipo, url_logado, js, ir, url, frente=lambda: None, ler_teor=True, dormir=time.sleep,
                 relogio=time.monotonic):
        self.tipo, self.js, self.ir, self.url_atual, self.frente = tipo, js, ir, url, frente
        self.host, self.base = base_de(url_logado)
        self.ler_teor, self.dormir, self.relogio = ler_teor, dormir, relogio

    def _j(self, codigo):
        s = self.js(codigo)
        try:
            return json.loads(s) if s else {}
        except ValueError:
            return {}

    def _esperar(self, cond, maximo, passo=1.0):
        return _esperar(cond, maximo, passo, self.dormir, self.relogio)

    def sessao_caiu(self):
        return bool(SAIU_DA_SESSAO.search(self.url_atual() or ""))

    def ler(self, numero):
        try:
            return self._ler_legado(numero) if self.tipo == "legado" else self._ler_kz(numero)
        except MonitorErro as e:
            return {"ok": False, "erro": str(e)}

    def _resultado(self, ler, maximo=25):
        """Espera a lista responder. "vazio" só vale confirmado 3 s depois (a lista pode ainda estar carregando)."""
        def cond():
            x = ler()
            if x.get("estado") in (None, "esperando"):
                return None
            if x.get("estado") == "vazio":
                self.dormir(3)
                y = ler()
                return y if y.get("estado") != "esperando" else None
            return x
        return self._esperar(cond, maximo)

    def _popup(self, maximo=15):
        u = self._esperar(lambda: self.js(JS_POPUP), maximo, 0.7)
        if not u:
            raise MonitorErro("os Detalhes do processo não abriram")
        return u if u.startswith("http") else self.host + u

    # PJe "legado" (TJCE, TRF5)
    def _ler_legado(self, numero):
        self.ir(self.base + "/Processo/ConsultaProcesso/listView.seam")
        if not self._esperar(lambda: self.js("document.getElementById('fPP:searchProcessos') ? 'ok' : ''"), 30):
            if self.sessao_caiu():
                raise MonitorErro("sessão do PJe caiu")
            raise MonitorErro("a tela de consulta não abriu")
        r = self._j(f"{JS_LEG_PESQUISAR}({json.dumps(numero)})")
        if not r.get("ok"):
            raise MonitorErro(r.get("erro") or "não consegui pesquisar")
        self.dormir(2)
        res = self._resultado(lambda: self._j(f"{JS_LEG_RESULTADO}({json.dumps(numero)}, false)"))
        estado = (res or {}).get("estado")
        if estado == "captcha":
            raise MonitorErro("captcha na consulta: o robô não resolve (parei este processo)")
        if estado == "vazio":
            raise MonitorErro("não encontrado no PJe (pode estar em outro sistema, como o e-SAJ, ou em segredo)")
        if estado != "achou":
            raise MonitorErro("a pesquisa não respondeu em 25 s")
        ultima_lista = res.get("ultima", "")
        self._j(f"{JS_LEG_RESULTADO}({json.dumps(numero)}, true)")
        self.ir(self._popup())
        tl = self._esperar(lambda: (lambda x: x if x.get("ok") else None)(self._j(JS_LEG_TIMELINE)), 30)
        if not tl:
            raise MonitorErro("a linha do tempo do processo não carregou")
        itens = [dict(i, data=data_iso(i.get("data"))) for i in tl.get("itens") or []]
        out = {"ok": True, "itens": itens, "ultima_lista": ultima_lista, "teor": None, "teor_de": ""}
        if self.ler_teor:
            it, doc = escolher_documento(itens)
            if doc:
                out["teor"], out["teor_de"] = self._teor_legado(it, doc)
        return out

    def _teor_legado(self, item, doc):
        nome = next((d for d in item.get("docs") or [] if d.startswith(doc)), doc)
        de = f"{nome} ({item.get('data', '')})"
        self.js(f"{JS_TEOR_BAIXAR}({json.dumps(self.base + '/seam/resource/rest/pje-legacy/documento/download/' + doc)})")
        r = self._esperar(lambda: (lambda s: json.loads(s) if s else None)(self.js(JS_TEOR_LER)), 30, 0.7)
        if not r:
            return "", de + " · o documento não carregou em 30 s"
        if not r.get("ok"):
            return "", de + f" · não consegui ler ({r.get('erro')})"
        if r.get("texto") == "§PDF":
            return "", de + " · documento em PDF (abrir no PJe; o teor do ato publicado vem do DJEN)"
        return r.get("texto", ""), de

    # PJe novo (TRT)
    def _ler_kz(self, numero):
        self.ir(f"{self.base}/painel/usuario-externo/acervo-geral/{numero}")
        res = self._resultado(lambda: self._j(f"{JS_KZ_ACERVO}({json.dumps(numero)})"))
        if not res or res.get("estado") != "achou":
            if self.sessao_caiu():
                raise MonitorErro("sessão do PJe caiu")
            # arquivado: a lista de arquivados aceita o mesmo filtro pelo número
            self.ir(f"{self.base}/painel/usuario-externo/arquivados/{numero}")
            res = self._resultado(lambda: self._j(f"{JS_KZ_ACERVO}({json.dumps(numero)})"))
            if not res or res.get("estado") != "achou":
                raise MonitorErro("fora do Acervo Geral e dos Arquivados deste login (escritório habilitado?)")
        self.ir(self._popup())
        tl = self._esperar(lambda: (lambda x: x if x.get("ok") else None)(self._j(JS_KZ_TIMELINE)), 30)
        if not tl:
            raise MonitorErro("a linha do tempo do processo não carregou")
        itens = [dict(i, data=data_iso(i.get("data"))) for i in tl.get("itens") or []]
        out = {"ok": True, "itens": itens, "teor": None, "teor_de": ""}
        if self.ler_teor:
            it, doc = escolher_documento(itens)
            if doc:
                out["teor"], out["teor_de"] = self._teor_kz(it, doc)
        return out

    def _teor_kz(self, item, doc):
        de = f"{item.get('mov') or doc} ({item.get('data', '')})"
        self.frente()  # o visualizador de PDF só desenha o texto com a aba visível
        if self.js(f"{JS_KZ_ABRIR_DOC}({json.dumps(doc)})") != "ok":
            return "", de + " · documento não encontrado na linha do tempo"
        r = self._esperar(lambda: (lambda x: x if x.get("pronto") else None)(
            self._j(f"{JS_KZ_LER_DOC}({json.dumps(doc)})")), 30, 1.0)
        if not r:
            return "", de + " · o documento não carregou em 30 s"
        return r.get("texto", ""), de


def rodar_tribunal(est, cfg, entrar, hoje=None, limite=None, pausa=None, aviso=print, fechar=lambda aba: None,
                   numeros=None):
    """Rodízio da madrugada no PJe. `entrar(portal, tipo) -> (aba, leitor)` (ver vigia.py); `fechar(aba)`.
    Um portal por vez; se a sessão cai, entra de novo uma vez; dois erros de login no mesmo portal: pula o portal.
    Com `numeros`, lê só esses (teste de um processo), sem rodízio."""
    hoje = hoje or date.today()
    limite = int(limite or cfg.get("MONITOR_TRIBUNAL_POR_NOITE") or PADRAO["MONITOR_TRIBUNAL_POR_NOITE"])
    pausa = float(cfg.get("MONITOR_PAUSA_TRIBUNAL_S", PADRAO["MONITOR_PAUSA_TRIBUNAL_S"])) if pausa is None else pausa
    inicio = datetime.now().isoformat(timespec="seconds")
    if numeros:
        fila = []
        for n in numeros:
            p = est.processo(n)
            if not p:
                raise MonitorErro(f"{n} não está na carteira do monitor")
            if p["sistema"] not in ("legado", "kz"):
                raise MonitorErro(f"{n} ({p['tribunal']}, {p['grau']}º grau) não tem leitura no tribunal nesta fase")
            fila.append({"numero": n, "tribunal": p["tribunal"], "grau": p["grau"], "sistema": p["sistema"]})
    else:
        fila = est.fila_tribunal(limite)
    grupos = {}
    for p in fila:
        grupos.setdefault((p["tribunal"], p["grau"]), []).append(p["numero"])
    res = {"data": str(hoje), "lidos": 0, "erros": [], "novidades": [], "portais": {}, "fila": len(fila)}
    for chave in [c for c in ORDEM_PORTAIS if c in grupos] + [c for c in grupos if c not in ORDEM_PORTAIS]:
        portal = PORTAIS.get(chave, ("", ""))[0]
        numeros = grupos[chave]
        info = res["portais"].setdefault(portal or str(chave), {"fila": len(numeros), "lidos": 0, "erros": 0, "login": ""})
        aviso(f"{portal}: {len(numeros)} processo(s)")
        leitor, aba, tentativas = None, None, 0
        for n in numeros:
            if leitor is None:
                if tentativas >= 2:
                    break
                tentativas += 1
                try:
                    aba, leitor = entrar(portal, PORTAIS[chave][1])
                    info["login"] = "ok"
                except Exception as e:  # noqa: BLE001
                    info["login"] = str(e)[:200]
                    res["erros"].append(f"{portal}: não entrou ({e})")
                    aviso(f"{portal}: não entrou ({e})")
                    leitor = None
                    continue
            lido = leitor.ler(n)
            if not lido.get("ok") and leitor.sessao_caiu():
                aviso(f"{portal}: a sessão caiu; entrando de novo")
                fechar(aba)
                leitor = None
                if tentativas < 2:
                    tentativas += 1
                    try:
                        aba, leitor = entrar(portal, PORTAIS[chave][1])
                        lido = leitor.ler(n)
                    except Exception as e:  # noqa: BLE001
                        res["erros"].append(f"{portal}: não entrou de novo ({e})")
                        leitor = None
            if est.gravar_tribunal(n, lido, hoje):
                res["novidades"].append((n, "Tribunal"))
            if lido.get("ok"):
                res["lidos"] += 1
                info["lidos"] += 1
            else:
                info["erros"] += 1
                res["erros"].append(f"{n}: {lido.get('erro')}")
            est.db.commit()
            if leitor is None and tentativas >= 2:
                break
            time.sleep(pausa)
        if aba is not None:
            fechar(aba)
    est.rodada(inicio, "tribunal", {k: (len(v) if isinstance(v, list) else v) for k, v in res.items()})
    return res


def relatorio(res, tipo="api"):
    if tipo == "api":
        linhas = [f"Monitor (DJEN + DataJud) · {res['data']}",
                  f"DJEN pela OAB: {res['oab_publicacoes']} publicação(ões), {res['oab_processos']} processo(s) da lista "
                  f"({res['fora_da_lista']} de fora da lista)",
                  f"DJEN por número: {res['djen']} · DataJud: {res['datajud']}"]
    else:
        linhas = [f"Monitor no tribunal (PJe) · {res['data']}", f"Lidos: {res['lidos']} de {res['fila']}"]
        for portal, i in res["portais"].items():
            linhas.append(f"  {portal}: {i['lidos']}/{i['fila']} lidos, {i['erros']} erro(s)"
                          + (f" · login: {i['login']}" if i["login"] not in ("", "ok") else ""))
    linhas.append(f"Novidades: {len(res['novidades'])}")
    for n, fonte in res["novidades"]:
        linhas.append(f"  {n} ({fonte})")
    if res["erros"]:
        linhas.append(f"Erros ({len(res['erros'])}):")
        linhas += [f"  {e}" for e in res["erros"][:60]]
        if len(res["erros"]) > 60:
            linhas.append(f"  ... e mais {len(res['erros']) - 60}")
    return "\n".join(linhas) + "\n"
