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

Nome conferido pela equipe: na aba Cumprimentos da Vila dos Bots, quem confere uma empresa SEM publicação pode
informar o nome dela no tribunal. A vila grava em dados/nomes_conferidos.json ({empresa: {"nomes": [...]}}) e o
vigia passa a buscar também por esse nome (origem "manual" em djen_nomes; a 1ª busca com ele vira auditoria).
O resultado de cada empresa na última rodada (quantas publicações, com quais nomes) fica em djen_consultas.

Processo principal de cada cumprimento/execução (VERMELHO), para saber se é cliente nosso: lê as publicações do
próprio cumprimento (até 100) e procura na lista do VIOS (tabela processos), nesta ordem:
  1. número de processo citado no texto da publicação que está no VIOS ("citado na publicação");
  2. processo do VIOS com o MESMO exequente (polo ativo da publicação = Autor no VIOS), de preferência na mesma vara
     (o cumprimento é distribuído por dependência à vara do principal).
Confirmado em 24/11/2026: 0001772-66.2024.5.07.0024 cita 0000064-49.2022.5.07.0024 (VIOS CI 21045, mesmo exequente);
0001226-95.2026.5.07.0038 não cita o número, mas o exequente é o autor do 0000743-70.2023.5.07.0038 (VIOS CI 21042,
mesma vara); 0001368-02.2026.5.07.0038 -> 0002754-04.2025.5.07.0038 (mesmo exequente, mesma vara).
Resultado em djen_principais (refeito a cada rodada enquanto o principal não for achado no VIOS).
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

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
CREATE TABLE IF NOT EXISTS djen_consultas (
  empresa TEXT PRIMARY KEY, data TEXT, publicacoes INTEGER, nomes TEXT);
CREATE TABLE IF NOT EXISTS djen_principais (
  numero TEXT PRIMARY KEY, principal TEXT, ci TEXT, empresa TEXT, advogado TEXT, como TEXT, exequente TEXT,
  verificado_em TEXT);
CREATE TABLE IF NOT EXISTS djen_andamentos (
  numero TEXT, chave TEXT, data TEXT, tipo TEXT, documento TEXT, orgao TEXT, destinatarios TEXT, texto TEXT,
  visto_em TEXT, PRIMARY KEY (numero, chave));
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


def consultar_numero(numero, abrir=None, itens=5):
    """Publicações de um processo pelo número (só dígitos), para ler os destinatários e o polo de cada um."""
    abrir = abrir or _abrir
    q = urllib.parse.urlencode({"numeroProcesso": re.sub(r"\D", "", numero), "itensPorPagina": int(itens), "pagina": 1})
    return abrir(f"{API}?{q}").get("items") or []


CNJ_TEXTO = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")
PREFIXO_AUTOR = re.compile(r"^\s*(AUTOR|AUTORA|CLIENTE|RECLAMANTE|REQUERENTE|EXEQUENTE)\s*:\s*", re.I)


def _autores(texto):
    """Campo "Autor" do VIOS ("Autor: FULANO / BELTRANO", "Cliente: FULANO") -> nomes normalizados."""
    return {normalizar(PREFIXO_AUTOR.sub("", a)) for a in re.split(r"\s*/\s*|\s*;\s*", texto or "") if a.strip()}


def achar_principal(numero, itens, vios):
    """Processo principal de um cumprimento/execução na lista do VIOS.

    itens: publicações do próprio cumprimento no DJEN; vios: [{numero, ci, empresa, orgao, autor, advogado}].
    Devolve {"principal", "ci", "empresa", "advogado", "como", "exequente"} (principal None se nada bate)."""
    citados, exequentes = [], []
    for i in itens:
        for n in CNJ_TEXTO.findall(i.get("texto") or ""):
            if n != numero and n not in citados:
                citados.append(n)
        for d in i.get("destinatarios") or []:
            nome = (d.get("nome") or "").strip()
            if (d.get("polo") or "").upper() == "A" and nome and nome not in exequentes:
                exequentes.append(nome)
    alvo = {normalizar(e) for e in exequentes}
    vara = numero[-4:]
    candidatos = [v for v in vios if v.get("numero") and v["numero"] != numero]

    def saida(v, como):
        return {"principal": v["numero"], "ci": v.get("ci") or "", "empresa": v.get("empresa") or "",
                "advogado": v.get("advogado") or "", "como": como, "exequente": " / ".join(exequentes)}

    por_numero = {v["numero"]: v for v in candidatos}
    for n in citados:
        if n in por_numero:
            v = por_numero[n]
            mesmo = bool(alvo & _autores(v.get("autor")))
            return saida(v, "citado na publicação" + (" e mesmo exequente" if mesmo else ""))
    mesmos = [v for v in candidatos if alvo & _autores(v.get("autor"))]
    mesmos.sort(key=lambda v: (v["numero"][-4:] != vara, v["numero"]))
    if mesmos:
        v = mesmos[0]
        como = "mesmo exequente" + (" e mesma vara" if v["numero"][-4:] == vara else " (vara diferente)")
        if len(mesmos) > 1:
            como += f"; outros com o mesmo exequente: {', '.join(x['numero'] for x in mesmos[1:4])}"
        return saida(v, como)
    como = ("citado na publicação, mas não está no VIOS: " + ", ".join(citados[:3])) if citados else \
        "nenhum processo do VIOS com o mesmo exequente"
    return {"principal": citados[0] if citados else None, "ci": "", "empresa": "", "advogado": "", "como": como,
            "exequente": " / ".join(exequentes)}


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

    def gravar_manuais(self, empresa, nomes):
        """Nomes informados pela equipe (aba Cumprimentos). Nome novo => a próxima busca da empresa vira auditoria."""
        novos = 0
        for n in nomes:
            novos += self.db.execute("INSERT OR IGNORE INTO djen_nomes VALUES (?, ?, 'manual')", (empresa, n)).rowcount
        if novos:
            self.db.execute("INSERT INTO djen_empresas VALUES (?, NULL, 0) ON CONFLICT(empresa) DO UPDATE SET base_feita = 0",
                            (empresa,))
        return novos

    def processos_vios(self):
        return [dict(zip(("numero", "ci", "empresa", "orgao", "autor", "advogado"), r)) for r in self.db.execute(
            "SELECT numero, ci, empresa, orgao, autor, advogado FROM processos WHERE numero != ''")]

    def sem_principal(self):
        """Cumprimentos/execuções (VERMELHO) ainda sem principal achado no VIOS."""
        return [r[0] for r in self.db.execute(
            "SELECT p.numero FROM djen_processos p LEFT JOIN djen_principais x ON x.numero = p.numero "
            "WHERE p.nivel = 'VERMELHO' AND (x.numero IS NULL OR x.ci IS NULL OR x.ci = '') ORDER BY p.numero")]

    def gravar_principal(self, numero, r, hoje):
        self.db.execute("INSERT OR REPLACE INTO djen_principais VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (numero, r["principal"], r["ci"], r["empresa"], r["advogado"], r["como"], r["exequente"], hoje))

    def alertas(self):
        """Cumprimentos/execuções (VERMELHO) fora do VIOS: os que a aba mostra com os andamentos."""
        return [r[0] for r in self.db.execute("SELECT numero FROM djen_processos WHERE nivel = 'VERMELHO' ORDER BY numero")]

    def gravar_andamentos(self, numero, andamentos, hoje):
        for x in andamentos:
            self.db.execute("INSERT INTO djen_andamentos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(numero, chave) "
                            "DO UPDATE SET destinatarios = excluded.destinatarios, visto_em = excluded.visto_em",
                            (numero, x["chave"], x["data"], x["tipo"], x["documento"], x["orgao"],
                             x["destinatarios"], x["texto"], hoje))

    def gravar_consulta(self, empresa, hoje, publicacoes, nomes):
        self.db.execute("INSERT OR REPLACE INTO djen_consultas VALUES (?, ?, ?, ?)",
                        (empresa, hoje, int(publicacoes), json.dumps(nomes, ensure_ascii=False)))

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


def nomes_conferidos(caminho):
    """dados/nomes_conferidos.json (gravado pela aba Cumprimentos da vila) -> {empresa: [nomes]}."""
    try:
        dados = json.loads(Path(caminho).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out = {}
    for empresa, c in (dados.items() if isinstance(dados, dict) else []):
        nomes = [re.sub(r"\s+", " ", str(n)).strip() for n in ((c or {}).get("nomes") or [])]
        nomes = [n for n in nomes if 3 <= len(n) <= 120]
        if nomes:
            out[empresa] = nomes[:3]
    return out


def rodar(estado, hoje=None, so=None, consulta=consultar, consulta_numero=consultar_numero, pausa=1.5,
          simular=False, aviso=print, dias_calibrar=30, manuais=None, consulta_principal=None, consulta_andamentos=None):
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
            extra = (manuais or {}).get(chave) or []
            if extra and not simular and ed.gravar_manuais(chave, extra):
                base_feita = False
                res.setdefault("manuais", []).append((chave, extra))
            nomes = list(dict.fromkeys([nome_busca(nome_vios)] + ed.nomes(chave) + (extra if simular else [])))
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
        if not simular:
            ed.gravar_consulta(chave, hoje, len(itens), nomes)
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
    if not simular:
        res["principais"] = ligar_principais(ed, hoje, consulta_principal or consulta_numero, pausa)
        res["andamentos"] = atualizar_andamentos(ed, hoje, consulta_andamentos or consulta_principal or consulta_numero,
                                                 pausa)
    if not simular and not so:
        ed.fechar_rodada(hoje, res, base_global)
    elif not simular:
        estado.db.commit()
    return res


def ligar_principais(ed, hoje, consulta, pausa=1.5):
    """Para cada cumprimento/execução ainda sem principal no VIOS: lê as publicações dele e procura o principal."""
    vios, saida = ed.processos_vios(), []
    for numero in ed.sem_principal():
        try:
            r = achar_principal(numero, consulta(numero), vios)
        except Exception as erro:  # noqa: BLE001 — um erro não para os outros
            r = {"principal": None, "ci": "", "empresa": "", "advogado": "", "como": f"erro ao consultar: {erro}",
                 "exequente": ""}
        ed.gravar_principal(numero, r, hoje)
        saida.append(dict(r, numero=numero))
        time.sleep(pausa)
    ed.db.commit()
    return saida


FIM_INTIMADOS = re.compile(r"\s*Intimado\(s\)\s*/\s*Citado\(s\).*$", re.S | re.I)
TEXTO_MAX = 8000


def _texto_limpo(html):
    """Texto da publicação sem HTML, sem espaços repetidos e sem o rodapé "Intimado(s) / Citado(s) - ..."."""
    import html as H
    t = H.unescape(re.sub(r"<[^>]+>", " ", html or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return FIM_INTIMADOS.sub("", t).strip()


def andamentos(itens):
    """Publicações de um processo -> andamentos sem repetição (a mesma decisão intimada a cada parte vira uma só,
    com os destinatários juntos), do mais recente para o mais antigo. Só o que a publicação já traz (público)."""
    import hashlib
    por = {}
    for i in itens:
        texto = _texto_limpo(i.get("texto"))
        data = (i.get("data_disponibilizacao") or i.get("datadisponibilizacao") or "")[:10]
        chave = hashlib.sha1(f"{data}|{texto}".encode("utf-8")).hexdigest()[:16]
        dest = [f"{(d.get('nome') or '').strip()} ({(d.get('polo') or '').upper()})" for d in i.get("destinatarios") or []
                if (d.get("nome") or "").strip()]
        x = por.setdefault(chave, {"chave": chave, "data": data, "tipo": (i.get("tipoComunicacao") or "").strip(),
                                   "documento": (i.get("tipoDocumento") or "").strip(),
                                   "orgao": (i.get("nomeOrgao") or "").strip(), "dest": [], "texto": texto[:TEXTO_MAX]})
        for d in dest:
            if d not in x["dest"]:
                x["dest"].append(d)
    out = [dict(x, destinatarios="; ".join(x.pop("dest"))) for x in por.values()]
    out.sort(key=lambda x: x["data"], reverse=True)
    return out


def atualizar_andamentos(ed, hoje, consulta, pausa=1.5):
    """Para cada cumprimento/execução fora do VIOS (VERMELHO): grava as publicações dele no DJEN (djen_andamentos),
    para a aba Cumprimentos mostrar o que já aconteceu no processo, mesmo sem o escritório habilitado."""
    saida = []
    for numero in ed.alertas():
        try:
            lista = andamentos(consulta(numero))
            ed.gravar_andamentos(numero, lista, hoje)
            saida.append({"numero": numero, "andamentos": len(lista), "erro": ""})
        except Exception as erro:  # noqa: BLE001 — um erro não para os outros
            saida.append({"numero": numero, "andamentos": 0, "erro": str(erro)})
        time.sleep(pausa)
    ed.db.commit()
    return saida


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
    if res.get("principais"):
        L += ["", f"PROCESSO PRINCIPAL dos cumprimentos/execuções ({len(res['principais'])})"]
        for r in res["principais"]:
            if r["ci"]:
                L.append(f"  - {r['numero']} -> principal {r['principal']} · NO VIOS (CI {r['ci']}, {r['empresa']}, "
                         f"adv. {r['advogado'] or '-'}) · {r['como']} · exequente: {r['exequente'] or '-'}")
            else:
                L.append(f"  - {r['numero']} -> principal NÃO achado no VIOS · {r['como']} · exequente: {r['exequente'] or '-'}")
    if res.get("manuais"):
        L += ["", f"NOMES CONFERIDOS pela equipe (aba Cumprimentos) ({len(res['manuais'])})"]
        L += [f"  - {e}: {', '.join(ns)}" for e, ns in res["manuais"]]
    if res.get("autor"):
        L += ["", f"Publicações ignoradas porque o cliente é o AUTOR (polo ativo): {res['autor']}"]
    if res["sem_publicacao"]:
        L += ["", f"Sem nenhuma publicação no DJEN com este nome ({len(res['sem_publicacao'])}) — conferir o nome:"]
        L += [f"  - {n}" for n in res["sem_publicacao"]]
    if res["erros"]:
        L += ["", f"ERROS ({len(res['erros'])})"] + [f"  - {e}: {m}" for e, m in res["erros"]]
    return "\n".join(L) + "\n"
