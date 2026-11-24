"""Vigia, verificação pelo DJEN (Diário de Justiça Eletrônico Nacional, CNJ): processo novo contra o cliente.

Fonte pública, sem login e sem CAPTCHA:
  https://comunicaapi.pje.jus.br/api/v1/comunicacao?nomeParte=<nome>&siglaTribunal=TRT7&itensPorPagina=100&pagina=N
  resposta {status, message, count, items[]}; cada item tem numeroprocessocommascara, nomeClasse,
  data_disponibilizacao, tipoComunicacao, nomeOrgao (conferido em 23/11/2026 com a MM COMERCIO: o CumPrSe
  0001368-02.2026.5.07.0038 aparece como "Lista de distribuição" em 31/07/2026, 2 dias depois da autuação).

Níveis de alerta (prioridade do projeto):
  VERMELHO  processo desconhecido com classe de cumprimento de sentença / execução contra o cliente;
  AMARELO   qualquer outro processo desconhecido (o escritório não está nele: o advogado confere);
  (o nível 3, "processos associados" do principal no PJe, fica em outro comando).
"Desconhecido" = não está na lista do VIOS (vigia vios) nem já foi avisado pelo DJEN antes.
A 1ª rodada vira base: não alerta, mas lista UMA vez os processos do DJEN que não estão no VIOS (auditoria).
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from vigia_estado import normalizar, numero_cnj, tribunal

API = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"
POR_PAGINA = 100
MAX_PAGINAS = 10
# "AÇÃO DE CUMPRIMENTO" (sindicato cobrando a convenção) NÃO é cumprimento de sentença: fica amarelo
CLASSES_VERMELHAS = re.compile(r"CUMPRIMENTO\s+(PROVIS|DE\s+SENTEN)|EXECU|EXPROV|LIQUIDA", re.I)
# palavras que não identificam a empresa (para comparar o nome do VIOS com o do tribunal)
GENERICAS = {"LTDA", "ME", "EPP", "EIRELI", "SA", "S/A", "DE", "DA", "DO", "DAS", "DOS", "E", "CIA", "COMERCIO",
             "SUPERMERCADO", "MERCANTIL", "COMERCIAL", "DISTRIBUIDORA", "SERVICOS", "ADMINISTRATIVOS", "INDUSTRIA",
             "MUNICIPIO", "ASSOCIACAO", "TRANSPORTE", "TRANSPORTES", "MATRIZ", "FILIAL", "BAIXADA"}

ESQUEMA_DJEN = """
CREATE TABLE IF NOT EXISTS djen_processos (
  numero TEXT PRIMARY KEY, empresa TEXT, classe TEXT, orgao TEXT, primeira_publicacao TEXT, tipo TEXT,
  visto_em TEXT, nivel TEXT);
CREATE TABLE IF NOT EXISTS djen_nomes (
  empresa TEXT, nome TEXT, origem TEXT, PRIMARY KEY (empresa, nome));
CREATE TABLE IF NOT EXISTS djen_empresas (
  empresa TEXT PRIMARY KEY, calibrado_em TEXT, base_feita INTEGER);
CREATE TABLE IF NOT EXISTS djen_rodadas (
  data TEXT PRIMARY KEY, empresas INTEGER, publicacoes INTEGER, vermelhos INTEGER, amarelos INTEGER,
  sem_publicacao INTEGER, erros INTEGER, base INTEGER);
"""


class DjenErro(Exception):
    pass


def nome_busca(nome):
    """Nome do VIOS -> nome para pesquisar no DJEN: tira "(MATRIZ)", "(FILIAL ...)", ": PRESTADORA" e espaços."""
    n = re.sub(r"\([^)]*\)", " ", nome or "")
    n = n.split(":")[0]
    n = re.sub(r"\s+", " ", n).strip(" -")
    return n


def palavras(nome):
    """Palavras que identificam a empresa (sem sufixos, genéricas e letras soltas)."""
    return [w for w in re.split(r"[^A-Z0-9]+", normalizar(nome_busca(nome))) if len(w) >= 2 and w not in GENERICAS]


def parecido(nome_vios, nome_tribunal):
    """O nome do tribunal é da mesma empresa do VIOS? (1ª palavra própria igual, ou textos ≥ 75% parecidos)."""
    from difflib import SequenceMatcher
    a, b = palavras(nome_vios), palavras(nome_tribunal)
    if not a or not b:
        return False
    if a[0] == b[0] and len(a[0]) >= 3:
        return True
    return SequenceMatcher(None, " ".join(a), " ".join(b)).ratio() >= 0.75


def polo_cliente(item, nomes):
    """'P' se algum destinatário do polo passivo é o cliente, 'A' se o cliente só aparece no ativo, None se não dá
    para saber (publicação sem destinatários ou com nomes diferentes)."""
    alvo = {normalizar(nome_busca(n)) for n in nomes}
    polos = set()
    for d in item.get("destinatarios") or []:
        n = normalizar(nome_busca(d.get("nome") or ""))
        if n in alvo or any(parecido(x, n) for x in nomes):
            polos.add((d.get("polo") or "").upper())
    if "P" in polos:
        return "P"
    return "A" if "A" in polos else None


def consultar_numero(numero, abrir=None):
    """Publicações de um processo pelo número (só dígitos), para ler os destinatários e o polo de cada um."""
    abrir = abrir or _abrir
    q = urllib.parse.urlencode({"numeroProcesso": re.sub(r"\D", "", numero), "itensPorPagina": 5, "pagina": 1})
    return abrir(f"{API}?{q}").get("items") or []


def nomes_do_tribunal(nome_vios, itens):
    """Nomes do polo passivo (como estão no tribunal) que são a mesma empresa do VIOS."""
    out = []
    for i in itens:
        for d in i.get("destinatarios") or []:
            n = (d.get("nome") or "").strip()
            if (d.get("polo") or "").upper() == "P" and n and parecido(nome_vios, n) and n not in out:
                out.append(n)
    return out


def consultar(nome, tribunal_sigla="TRT7", abrir=None, pausa=1.0):
    """Todas as publicações do DJEN para o nome no tribunal. `abrir` (para testes) recebe a URL e devolve o JSON."""
    abrir = abrir or _abrir
    itens, pagina = [], 1
    while pagina <= MAX_PAGINAS:
        q = urllib.parse.urlencode({"nomeParte": nome, "siglaTribunal": tribunal_sigla,
                                    "itensPorPagina": POR_PAGINA, "pagina": pagina})
        dados = abrir(f"{API}?{q}")
        lote = dados.get("items") or []
        itens += lote
        total = dados.get("count") or 0
        if len(lote) < POR_PAGINA or len(itens) >= total:
            break
        pagina += 1
        time.sleep(pausa)
    return itens


def _abrir(url, tentativas=3):
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0 Safari/537.36"})
    for n in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < tentativas:
                time.sleep(10 * n)
                continue
            raise DjenErro(f"DJEN respondeu HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if n < tentativas:
                time.sleep(5 * n)
                continue
            raise DjenErro(f"DJEN sem resposta: {e}")
    raise DjenErro("DJEN sem resposta")


def resumir(itens):
    """Publicações -> {numero: {classe, orgao, primeira_publicacao, tipo}} (a publicação mais antiga de cada processo)."""
    out = {}
    for i in itens:
        numero = numero_cnj(i.get("numeroprocessocommascara") or i.get("numero_processo") or "")
        if not numero:
            continue
        data = (i.get("data_disponibilizacao") or i.get("datadisponibilizacao") or "")[:10]
        atual = out.get(numero)
        if atual is None or (data and data < atual["primeira_publicacao"]):
            out[numero] = {"classe": (i.get("nomeClasse") or "").strip(), "orgao": (i.get("nomeOrgao") or "").strip(),
                           "primeira_publicacao": data, "tipo": (i.get("tipoComunicacao") or "").strip()}
    return out


def classificar(numero, info, conhecidos_vios, ja_avisados):
    """None (já conhecido) | "VERMELHO" | "AMARELO"."""
    if numero in conhecidos_vios or numero in ja_avisados:
        return None
    return "VERMELHO" if CLASSES_VERMELHAS.search(info.get("classe") or "") else "AMARELO"


class EstadoDjen:
    """Tabelas do DJEN dentro do mesmo dados/vigia.sqlite do vigia (usa a conexão do vigia_estado.Estado)."""

    def __init__(self, estado):
        self.db = estado.db
        self.db.executescript(ESQUEMA_DJEN)

    def eh_base(self):
        return self.db.execute("SELECT COUNT(*) FROM djen_rodadas").fetchone()[0] == 0

    def refazer_base(self):
        """Apaga só o estado do DJEN (rodadas, avisos, nomes calibrados). A base do VIOS fica."""
        for t in ("djen_processos", "djen_rodadas", "djen_nomes", "djen_empresas"):
            self.db.execute(f"DELETE FROM {t}")
        self.db.commit()

    def conhecidos_vios(self):
        return {r[0] for r in self.db.execute("SELECT numero FROM processos WHERE numero != ''")}

    def ja_avisados(self):
        return {r[0] for r in self.db.execute("SELECT numero FROM djen_processos")}

    def empresas(self, so=None):
        sql = "SELECT chave, nome FROM empresas"
        rows = [dict(r) for r in self.db.execute(sql + " ORDER BY chave")]
        if so:
            alvo = normalizar(so)
            rows = [r for r in rows if alvo in r["chave"]]
        return rows

    def nomes(self, empresa):
        return [r[0] for r in self.db.execute("SELECT nome FROM djen_nomes WHERE empresa = ? ORDER BY nome", (empresa,))]

    def calibracao(self, empresa):
        r = self.db.execute("SELECT calibrado_em, base_feita FROM djen_empresas WHERE empresa = ?", (empresa,)).fetchone()
        return (r[0], bool(r[1])) if r else (None, False)

    def processos_trt7(self, empresa, limite=2):
        return [r[0] for r in self.db.execute(
            "SELECT numero FROM processos WHERE empresa = ? AND tribunal = '5.07' ORDER BY ultima_vez DESC, numero LIMIT ?",
            (empresa, int(limite)))]

    def gravar_nomes(self, empresa, nomes, hoje):
        novos = 0
        for n in nomes:
            novos += self.db.execute("INSERT OR IGNORE INTO djen_nomes VALUES (?, ?, 'tribunal')", (empresa, n)).rowcount
        cal = self.calibracao(empresa)
        self.db.execute("INSERT OR REPLACE INTO djen_empresas VALUES (?, ?, ?)",
                        (empresa, hoje, 0 if novos else int(cal[1])))
        return novos

    def base_feita(self, empresa, hoje):
        self.db.execute("INSERT INTO djen_empresas VALUES (?, ?, 1) ON CONFLICT(empresa) DO UPDATE SET base_feita = 1",
                        (empresa, hoje))

    def gravar(self, numero, empresa, info, hoje, nivel):
        self.db.execute("INSERT OR IGNORE INTO djen_processos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (numero, empresa, info["classe"], info["orgao"], info["primeira_publicacao"], info["tipo"],
                         hoje, nivel))

    def fechar_rodada(self, hoje, res, base):
        self.db.execute("INSERT OR REPLACE INTO djen_rodadas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (hoje, res["empresas"], res["publicacoes"], len(res["vermelhos"]), len(res["amarelos"]),
                         len(res["sem_publicacao"]), len(res["erros"]), int(base)))
        self.db.commit()


def rodar(estado, hoje=None, so=None, consulta=consultar, consulta_numero=consultar_numero, pausa=1.5,
          simular=False, aviso=print, dias_calibrar=30):
    """Consulta o DJEN para cada empresa do vigia e classifica. Devolve o resultado (para o relatório).

    Por empresa: (1) calibra o nome a cada `dias_calibrar` dias, lendo no DJEN os destinatários do polo passivo de
    até 2 processos do TRT7 já conhecidos (o nome no tribunal pode ser diferente do VIOS: ex. COPCEL); (2) busca por
    todos os nomes (VIOS + tribunal); (3) descarta publicação em que o cliente só aparece no polo ativo (ele é o
    autor: consignação, homologação de acordo...); (4) a 1ª busca com um nome novo vira base daquela empresa (vai
    para a auditoria, sem alerta)."""
    from datetime import date as _date, timedelta
    hoje_d = hoje or _date.today()
    hoje = hoje_d.isoformat()
    ed = EstadoDjen(estado)
    base_global = ed.eh_base() and not so
    vios, avisados = ed.conhecidos_vios(), ed.ja_avisados()
    empresas = ed.empresas(so)
    res = {"data": hoje, "base": base_global, "simulado": simular, "empresas": len(empresas), "publicacoes": 0,
           "vermelhos": [], "amarelos": [], "fora_do_vios": [], "sem_publicacao": [], "erros": [],
           "calibradas": [], "autor": 0}
    for n, e in enumerate(empresas, 1):
        chave, nome_vios = e["chave"], e["nome"] or e["chave"]
        try:
            calibrado_em, base_feita = ed.calibracao(chave)
            if not calibrado_em or calibrado_em < (hoje_d - timedelta(days=dias_calibrar)).isoformat():
                achados = []
                for numero in ed.processos_trt7(chave):
                    achados += nomes_do_tribunal(nome_vios, consulta_numero(numero))
                    time.sleep(pausa)
                if not simular:
                    if ed.gravar_nomes(chave, achados, hoje):
                        base_feita = False
                        res["calibradas"].append((chave, achados))
            nomes = list(dict.fromkeys([nome_busca(nome_vios)] + ed.nomes(chave)))
            itens, vistos = [], set()
            for nome in nomes:
                for i in consulta(nome):
                    k = i.get("id") or (i.get("numeroprocessocommascara"), i.get("data_disponibilizacao"), i.get("tipoComunicacao"))
                    if k not in vistos:
                        vistos.add(k)
                        itens.append(i)
                time.sleep(pausa)
        except Exception as erro:  # noqa: BLE001 — uma empresa com erro não para as outras
            res["erros"].append((chave, str(erro)))
            continue
        res["publicacoes"] += len(itens)
        if not itens:
            res["sem_publicacao"].append(" / ".join(nomes))
        uteis = []
        for i in itens:
            if polo_cliente(i, [nome_vios] + nomes) == "A":
                res["autor"] += 1
                continue
            uteis.append(i)
        base = base_global or not base_feita
        for numero, info in resumir(uteis).items():
            if tribunal(numero) != "5.07":
                continue
            nivel = classificar(numero, info, vios, avisados)
            if nivel is None:
                continue
            reg = {"numero": numero, "empresa": chave, "busca": nomes[0], **info}
            if base:
                res["fora_do_vios"].append(dict(reg, nivel=nivel))
            else:
                res["vermelhos" if nivel == "VERMELHO" else "amarelos"].append(reg)
            avisados.add(numero)
            if not simular:
                ed.gravar(numero, chave, info, hoje, nivel)
        if not simular and not so:
            ed.base_feita(chave, hoje)
        if n % 20 == 0:
            aviso(f"  DJEN: {n}/{len(empresas)} empresas consultadas")
    if not simular and not so:
        ed.fechar_rodada(hoje, res, base_global)
    elif not simular:
        estado.db.commit()
    return res


def relatorio(res):
    L = [f"VIGIA DJEN · {res['data']}", "=" * 60,
         f"Empresas consultadas: {res['empresas']} · publicações lidas: {res['publicacoes']} · "
         f"erros: {len(res['erros'])}" + (" · (simulação: nada gravado)" if res.get("simulado") else ""), ""]

    def linha(r):
        return (f"  • {r['numero']} · {r['classe'] or '-'} · {r['orgao'] or '-'} · 1ª publicação {r['primeira_publicacao'] or '-'}"
                f" ({r['tipo'] or '-'}) · empresa: {r['empresa']}")

    if not res["base"]:
        L += [f"🔴 VERMELHO · cumprimento de sentença / execução contra o cliente ({len(res['vermelhos'])})"]
        L += [linha(r) for r in res["vermelhos"]] or ["  (nenhum)"]
        L += ["", f"🟡 AMARELO · processo novo em que o escritório não está ({len(res['amarelos'])})"]
        L += [linha(r) for r in res["amarelos"]] or ["  (nenhum)"]
        L.append("")
    if res["fora_do_vios"]:
        titulo = ("PRIMEIRA RODADA (base): nada é alerta hoje." if res["base"] else
                  "AUDITORIA (empresas com nome recém-calibrado: primeira busca com o nome do tribunal, sem alerta).")
        L += [titulo, "Processos do TRT7 no DJEN com o cliente no polo passivo (ou sem polo informado) que NÃO estão",
              "na lista do VIOS (o escritório pode não estar neles):", ""]
        verm = [r for r in res["fora_do_vios"] if r["nivel"] == "VERMELHO"]
        amar = [r for r in res["fora_do_vios"] if r["nivel"] != "VERMELHO"]
        L += [f"CUMPRIMENTO DE SENTENÇA / EXECUÇÃO fora do VIOS ({len(verm)})"] + [linha(r) for r in verm]
        L += ["", f"OUTROS fora do VIOS ({len(amar)})"] + [linha(r) for r in amar]
    if res.get("calibradas"):
        L += ["", f"NOMES CALIBRADOS pelo tribunal ({len(res['calibradas'])})"]
        L += [f"  - {e}: {', '.join(ns)}" for e, ns in res["calibradas"]]
    if res.get("autor"):
        L += ["", f"Publicações ignoradas porque o cliente é o AUTOR (polo ativo): {res['autor']}"]
    if res["sem_publicacao"]:
        L += ["", f"Sem nenhuma publicação no DJEN com este nome ({len(res['sem_publicacao'])}) — conferir o nome:"]
        L += [f"  - {n}" for n in res["sem_publicacao"]]
    if res["erros"]:
        L += ["", f"ERROS ({len(res['erros'])})"] + [f"  - {e}: {m}" for e, m in res["erros"]]
    return "\n".join(L) + "\n"
