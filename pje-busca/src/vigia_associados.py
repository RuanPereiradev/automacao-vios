"""Vigia, nível 3: "Processos associados" no Acervo Geral do PJe do TRT7 (rede de segurança do DJEN).

Quando o juiz reconhece que um cumprimento de sentença pertence a um processo principal, o PJe mostra o cumprimento
como "Processo associado" na linha do principal no Acervo Geral (botão com ícone de corrente, aria-label "Processos
associados"). Conferido em 23/11/2026: o principal 0002754-04.2025.5.07.0038 mostra o CumPrSe 0001368-02.2026.5.07.0038.

Como lê (24/11/2026, conferido no PJe real): o Acervo Geral tem o filtro "Processos com Associação" (botão da barra do
título). Com ele ligado a lista mostra só os processos do acervo que têm associação (60 de 358 nesse dia). Para cada
linha: clica em "Processos associados" (abre uma janela só de consulta), lê a tabela "Processo Associado · Órgão
Julgador" (paginação de 5 em 5, botão "Próximo") e fecha com Esc. Depois desliga o filtro e percorre o acervo inteiro e
a aba "Arquivados" (100 por página) só para saber onde está cada processo do VIOS: no acervo, ARQUIVADO no PJe (ainda
ativo no VIOS: atualizar o VIOS; ex. 0000029-50.2026.5.07.0024, arquivado em 09/11/2026) ou fora dos dois (2º grau/TST
ou a sociedade do login não está no processo).
A pesquisa pelo número no campo do acervo NÃO serve: a lista deixa de atualizar depois de algumas buscas.
Não abre documento, não peticiona, não assina, não altera nada no PJe.

Alertas:
- A 1ª rodada completa é BASE: guarda o que já existe (auditoria, sem alerta).
- Depois, associado NOVO de um processo que já estava no acervo = alerta. Um processo que acabou de entrar no acervo
  vira base só dele. Nível do associado novo:
    VERMELHO  principal está no VIOS (cliente nosso no polo passivo) e o associado não está no VIOS;
    AMARELO   associado fora do VIOS, mas o principal também está fora da lista do VIOS (antigo, arquivado, outra
              área: o teste de 24/11 mostrou que a maioria dos processos com associação do acervo é assim);
    INFO      o associado já está no VIOS.
"""
import json
import re
import time
from datetime import date

ACERVO = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/acervo-geral"
ARQUIVADOS = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/arquivados"
MAX_PAGINAS = 100  # 100 por página (listas grandes): até 10.000 processos
POR_PAGINA = "100"  # opções do PJe: 10, 20, 50, 75, 100

ESQUEMA_ASSOC = """
CREATE TABLE IF NOT EXISTS assoc_principais (
  numero TEXT PRIMARY KEY, situacao TEXT, qtd INTEGER, verificado_em TEXT, base_feita INTEGER, erro TEXT);
CREATE TABLE IF NOT EXISTS assoc_associados (
  principal TEXT, associado TEXT, orgao TEXT, visto_em TEXT, novo INTEGER, nivel TEXT,
  PRIMARY KEY (principal, associado));
CREATE TABLE IF NOT EXISTS assoc_acervo (
  numero TEXT PRIMARY KEY, primeira_vez TEXT, ultima_vez TEXT);
CREATE TABLE IF NOT EXISTS assoc_rodadas (
  data TEXT PRIMARY KEY, acervo INTEGER, verificados INTEGER, com_associados INTEGER, fora_acervo INTEGER,
  erros INTEGER, novos INTEGER, vermelhos INTEGER, completa INTEGER, base INTEGER, arquivados INTEGER);
CREATE TABLE IF NOT EXISTS assoc_fora (
  numero TEXT PRIMARY KEY, grupo TEXT, orgao TEXT, classe TEXT, ultima TEXT, escritorio INTEGER, publicacoes INTEGER,
  verificado_em TEXT);
CREATE TABLE IF NOT EXISTS assoc_arquivados (
  numero TEXT PRIMARY KEY, primeira_vez TEXT, ultima_vez TEXT);
"""

# ---------------- JavaScript da página do Acervo Geral ----------------
_FORA_DO_DIALOGO = "function fora(e) { return !e.closest('mat-dialog-container, .cdk-overlay-pane'); }"
_CNJ = r"/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/"

# tira o filtro de número (se houver) e liga/desliga "Processos com Associação"
JS_FILTRO = r"""(function(ligar){
  var mudou = false;
  var tirou = false;
  [].forEach.call(document.querySelectorAll('button[aria-label^="Remover Filtro"]'), function(x) {
    if (%(cnj)s.test(x.getAttribute('aria-label') || '')) { x.click(); mudou = tirou = true; }
  });
  if (!tirou) [].forEach.call(document.querySelectorAll('mat-chip, .mat-chip'), function(c) {
    if (%(cnj)s.test(c.innerText || '')) {
      var x = c.querySelector('[matchipremove], button, mat-icon, i'); if (x) { x.click(); mudou = true; }
    }
  });
  var b = document.querySelector('button[aria-label="Processos com Associação"]');
  if (!b) return JSON.stringify({ok: false, erro: 'botão "Processos com Associação" não achado'});
  if ((b.getAttribute('aria-pressed') === 'true') !== ligar) { b.click(); mudou = true; }
  return JSON.stringify({ok: true, mudou: mudou});
})(%%s)""" % {"cnj": _CNJ}

# a página atual da lista (fora da janela de associados): números, botão de associados, "1 - 10 de 60"
JS_PAGINA = r"""(function(){
  %(fora)s
  var linhas = [], vistos = {};
  [].forEach.call(document.querySelectorAll('tbody tr, mat-row'), function(l) {
    if (!fora(l)) return;
    var m = (l.innerText || '').match(%(cnj)s);
    if (!m || vistos[m[0]]) return;
    vistos[m[0]] = 1;
    linhas.push({numero: m[0], botao: !!l.querySelector('button[aria-label="Processos associados"]')});
  });
  var pag = [].filter.call(document.querySelectorAll('pje-paginador'), fora).pop();
  var t = pag ? (pag.innerText || '').replace(/\s+/g, ' ') : '';
  var pg = t.match(/(\d+)\s*[-–]\s*(\d+)\s*de\s*(\d+)/);
  var prox = pag && [].filter.call(pag.querySelectorAll('button'), function(x) {
    return /^pr[óo]xim/i.test(x.getAttribute('aria-label') || ''); })[0];
  var filtro = document.querySelector('button[aria-label="Processos com Associação"]');
  return JSON.stringify({linhas: linhas, de: pg ? +pg[1] : null, ate: pg ? +pg[2] : null, total: pg ? +pg[3] : null,
    tem_proximo: !!(prox && !prox.disabled), vazio: /Não há processos/i.test(document.body.innerText || ''),
    filtro: filtro ? filtro.getAttribute('aria-pressed') === 'true' : null,
    dialogo: !!document.querySelector('mat-dialog-container')});
})()""" % {"fora": _FORA_DO_DIALOGO, "cnj": _CNJ}

# próxima página da lista principal (paginação)
JS_PAGINA_PROXIMA = r"""(function(){
  %(fora)s
  var pag = [].filter.call(document.querySelectorAll('pje-paginador'), fora).pop();
  var b = pag && [].filter.call(pag.querySelectorAll('button'), function(x) {
    return /^pr[óo]xim/i.test(x.getAttribute('aria-label') || ''); })[0];
  if (!b || b.disabled) return 'nao';
  b.click(); return 'ok';
})()""" % {"fora": _FORA_DO_DIALOGO}

# volta para a 1ª página (o PJe mantém a página ao ligar/desligar o filtro)
JS_PAGINA_PRIMEIRA = r"""(function(){
  %(fora)s
  var pag = [].filter.call(document.querySelectorAll('pje-paginador'), fora).pop();
  var b = pag && [].filter.call(pag.querySelectorAll('button'), function(x) {
    return /^primeir/i.test(x.getAttribute('aria-label') || ''); })[0];
  if (!b || b.disabled) return 'ja';
  b.click(); return 'ok';
})()""" % {"fora": _FORA_DO_DIALOGO}

# clica em "Processos associados" da linha do processo
JS_ABRIR = r"""(function(numero){
  %(fora)s
  var l = [].filter.call(document.querySelectorAll('tbody tr, mat-row'), function(x) {
    return fora(x) && ((x.innerText || '').match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/) || [])[0] === numero; })[0];
  if (!l) return 'sem_linha';
  var b = l.querySelector('button[aria-label="Processos associados"]');
  if (!b) return 'sem_botao';
  b.click(); return 'ok';
})(%%s)""" % {"fora": _FORA_DO_DIALOGO}

# "Linhas por página" da lista principal: abre o seletor (passo 1) e escolhe a opção (passo 2)
JS_TAMANHO_ABRIR = r"""(function(){
  %(fora)s
  var pag = [].filter.call(document.querySelectorAll('pje-paginador'), fora).pop();
  var sels = pag ? pag.querySelectorAll('mat-select') : [];
  var s = sels[sels.length - 1];
  if (!s) return 'sem';
  if ((s.innerText || '').trim() === %%(n)s) return 'ja';
  s.click(); return 'ok';
})()""" % {"fora": _FORA_DO_DIALOGO}

JS_TAMANHO_ESCOLHER = r"""(function(n){
  var o = [].filter.call(document.querySelectorAll('mat-option'), function(x) { return (x.innerText || '').trim() === n; })[0];
  if (!o) return 'sem';
  o.click(); return 'ok';
})(%s)"""

_CAIXA = ("[].slice.call(document.querySelectorAll('mat-dialog-container')).filter(function(c) {"
          " return /associad|rg[ãa]o julgador/i.test(c.innerText || ''); }).pop()")

# lê a janela "Processos associados": linhas com número e órgão, paginação "1 - 5 de 7"
JS_LER = r"""(function(principal){
  var cnj = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g;
  var cx = %(caixa)s;
  if (!cx) return JSON.stringify({aberta: false});
  var itens = [];
  [].forEach.call(cx.querySelectorAll('tbody tr, mat-row, [role=row]'), function(l) {
    var t = (l.innerText || '').replace(/\s+/g, ' ').trim();
    var ns = (t.match(cnj) || []).filter(function(n) { return n !== principal; });
    if (ns.length) itens.push({numero: ns[0], orgao: t.replace(cnj, '').replace(/\s+/g, ' ').trim()});
  });
  var texto = (cx.innerText || '').replace(/\s+/g, ' ').trim();
  var pg = texto.match(/(\d+)\s*[-–]\s*(\d+)\s*de\s*(\d+)/);
  var prox = [].filter.call(cx.querySelectorAll('button'), function(x) {
    return /^pr[óo]xim|next/i.test(x.getAttribute('aria-label') || ''); })[0];
  return JSON.stringify({aberta: true, itens: itens, texto: texto.slice(0, 400), de: pg ? +pg[1] : null,
                         ate: pg ? +pg[2] : null, total: pg ? +pg[3] : null, tem_proxima: !!(prox && !prox.disabled)});
})(%%s)""" % {"caixa": _CAIXA}

# próxima página DENTRO da janela de associados
JS_PROXIMA = r"""(function(){
  var cx = %(caixa)s;
  var b = cx && [].filter.call(cx.querySelectorAll('button'), function(x) {
    return /^pr[óo]xim|next/i.test(x.getAttribute('aria-label') || ''); })[0];
  if (!b || b.disabled) return 'nao';
  b.click(); return 'ok';
})()""" % {"caixa": _CAIXA}

# fecha a janela: Esc (funciona no PJe); "forte" também clica no "Fechar" (link com tooltip "Fechar")
JS_FECHAR = r"""(function(forte){
  if (!document.querySelector('mat-dialog-container')) return 'fechada';
  var alvo = document.activeElement || document.body;
  ['keydown', 'keyup'].forEach(function(n) {
    alvo.dispatchEvent(new KeyboardEvent(n, {key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true}));
  });
  if (forte) {
    var x = document.querySelector('mat-dialog-container [mattooltip="Fechar"]');
    if (x) x.click();
  }
  return 'esc';
})(%s)"""


class LeituraErro(Exception):
    pass


def _esperar(cond, maximo, passo=0.7):
    fim, v = time.monotonic() + maximo, None
    while time.monotonic() < fim:
        try:
            v = cond()
            if v:
                return v
        except Exception:  # noqa: BLE001
            pass
        time.sleep(passo)
    return v


def _pagina(js):
    return json.loads(js(JS_PAGINA))


def _assinatura(p):
    return (p.get("de"), p.get("total"), tuple(l["numero"] for l in p.get("linhas") or []))


def _esperar_lista(js, antes=None, maximo=25):
    """Espera a lista carregar (com linhas ou "Não há processos") e, se `antes` foi dado, MUDAR em relação a ele."""
    def pronta():
        p = _pagina(js)
        if not (p["linhas"] or p["vazio"]):
            return None
        if antes is not None and _assinatura(p) == antes:
            return None
        return p
    p = _esperar(pronta, maximo)
    if not p:
        raise LeituraErro("a lista do Acervo Geral não carregou (ou não mudou) em %d s" % maximo)
    time.sleep(1.0)  # deixa terminar de desenhar e confere de novo
    return _pagina(js)


def _filtro(js, ligar):
    antes = _assinatura(_pagina(js))
    r = json.loads(js(JS_FILTRO % ("true" if ligar else "false")))
    if not r.get("ok"):
        raise LeituraErro(r.get("erro") or "não consegui mexer no filtro")
    if r.get("mudou"):
        try:
            return _esperar_lista(js, antes)
        except LeituraErro:
            pass  # o resultado pode ser igual ao de antes: segue com o que estiver na tela
    p = _esperar_lista(js)
    if p.get("filtro") is not None and p["filtro"] != ligar:
        raise LeituraErro("o filtro \"Processos com Associação\" não ficou %s" % ("ligado" if ligar else "desligado"))
    return p


def _tamanho(js, n=POR_PAGINA):
    """Põe a lista principal com n linhas por página (paginação). Sem o seletor, segue com o que houver."""
    antes = _assinatura(_pagina(js))
    r = js(JS_TAMANHO_ABRIR.replace("%(n)s", json.dumps(n)))
    if r != "ok":
        return
    if _esperar(lambda: js(JS_TAMANHO_ESCOLHER % json.dumps(n)) == "ok", 5):
        try:
            _esperar_lista(js, antes)
        except LeituraErro:
            _esperar_lista(js)


def percorrer(js, cada_linha=None, max_paginas=MAX_PAGINAS):
    """Percorre as páginas da lista atual. Devolve (números vistos, total informado pela página)."""
    vistos, total = [], None
    p = _esperar_lista(js)
    if (p.get("de") or 0) > 1 or (p.get("vazio") and not p["linhas"]):  # começa da 1ª página
        antes = _assinatura(p)
        if js(JS_PAGINA_PRIMEIRA) == "ok":
            p = _esperar_lista(js, antes)
    for _ in range(max_paginas):
        total = p.get("total") if p.get("total") is not None else total
        for linha in p["linhas"]:
            if linha["numero"] not in vistos:
                vistos.append(linha["numero"])
                if cada_linha:
                    cada_linha(linha)
        if not p.get("tem_proximo") or (p.get("ate") and p.get("total") and p["ate"] >= p["total"]):
            break
        antes = _assinatura(p)
        if js(JS_PAGINA_PROXIMA) != "ok":
            break
        p = _esperar_lista(js, antes)
    return vistos, total


def ler_associados(js, numero):
    """Abre a janela de associados da linha, lê todas as páginas e fecha. {"situacao", "associados", "erro"}."""
    js(JS_FECHAR % "true")
    r = js(JS_ABRIR % json.dumps(numero))
    if r == "sem_botao":
        return {"situacao": "ok", "associados": [], "erro": ""}
    if r != "ok":
        return {"situacao": "erro", "associados": [], "erro": "linha do processo não achada na lista"}
    vistos, paginas, ultimo = {}, 0, None
    while True:
        def lida():
            x = json.loads(js(JS_LER % json.dumps(numero)))
            return x if x.get("aberta") and (x.get("itens") or x.get("total") == 0) else None
        ultimo = _esperar(lida, 12)
        if not ultimo:
            js(JS_FECHAR % "true")
            return {"situacao": "erro", "associados": list(vistos.values()), "erro": "a janela de associados não abriu"}
        for i in ultimo["itens"]:
            vistos.setdefault(i["numero"], i)
        paginas += 1
        if not ultimo.get("tem_proxima") or paginas >= 20 or (ultimo.get("total") and len(vistos) >= ultimo["total"]):
            break
        primeira = ultimo["itens"][0]["numero"] if ultimo["itens"] else None
        if js(JS_PROXIMA) != "ok":
            break
        _esperar(lambda: (lambda x: x if x.get("itens") and x["itens"][0]["numero"] != primeira else None)(
            json.loads(js(JS_LER % json.dumps(numero)))), 8)
    js(JS_FECHAR % "false")
    if not _esperar(lambda: js(JS_FECHAR % "false") == "fechada", 5):
        js(JS_FECHAR % "true")
        _esperar(lambda: js(JS_FECHAR % "false") == "fechada", 5)
    total = ultimo.get("total")
    if total and len(vistos) < total:
        return {"situacao": "erro", "associados": list(vistos.values()), "erro": f"li {len(vistos)} de {total} associados"}
    return {"situacao": "ok", "associados": list(vistos.values()), "erro": ""}


def ler_acervo(js, cobertura=True, max_paginas=MAX_PAGINAS, aviso=print, ir=None):
    """Lê no PJe (aba do Acervo Geral já aberta e logada):
    {"principais": {numero: {"situacao", "associados", "erro"}}, "acervo": [números] ou None,
     "arquivados": [números] ou None, "total_assoc", "erro"}.
    ir(url): leva a aba para outro endereço e espera carregar (para a aba "Arquivados"); sem ir, não lê os arquivados."""
    out = {"principais": {}, "acervo": None, "arquivados": None, "total_assoc": None, "erro": ""}
    try:
        _filtro(js, True)

        def cada(linha):
            r = ler_associados(js, linha["numero"])
            out["principais"][linha["numero"]] = r
            aviso(f"  {linha['numero']}: {r['situacao']}, {len(r['associados'])} associado(s)"
                  + (f" ({r['erro']})" if r.get("erro") else ""))
        _, out["total_assoc"] = percorrer(js, cada, max_paginas)
        if cobertura:
            aviso("  lendo a lista do acervo inteiro (para saber o que está fora dele)...")
            _filtro(js, False)
            _tamanho(js)
            out["acervo"], _ = percorrer(js, None, max_paginas)
            if ir:
                aviso("  lendo a aba Arquivados (processos arquivados no PJe)...")
                ir(ARQUIVADOS)
                _filtro(js, False)
                _tamanho(js)
                out["arquivados"], _ = percorrer(js, None, max_paginas)
    except LeituraErro as e:
        out["erro"] = str(e)
    finally:
        try:
            js(JS_FECHAR % "true")
            json.loads(js(JS_FILTRO % "false"))  # deixa o acervo como estava (sem filtro)
        except Exception:  # noqa: BLE001
            pass
    return out


class EstadoAssoc:
    """Tabelas do nível 3 dentro do mesmo dados/vigia.sqlite (usa a conexão do vigia_estado.Estado)."""

    def __init__(self, estado):
        self.db = estado.db
        cols = [r[1] for r in self.db.execute("PRAGMA table_info(assoc_rodadas)")]
        if cols and "acervo" not in cols:  # esquema do 1º teste (busca pelo número): recomeça a base
            self.db.executescript("DROP TABLE IF EXISTS assoc_rodadas; DROP TABLE IF EXISTS assoc_principais; "
                                  "DROP TABLE IF EXISTS assoc_associados;")
        elif cols and "arquivados" not in cols:  # rodada de 24/11 sem a aba Arquivados: só acrescenta a coluna
            self.db.execute("ALTER TABLE assoc_rodadas ADD COLUMN arquivados INTEGER")
        self.db.executescript(ESQUEMA_ASSOC)

    def eh_base(self):
        return self.db.execute("SELECT COUNT(*) FROM assoc_rodadas WHERE completa = 1").fetchone()[0] == 0

    def no_acervo(self):
        return {r[0] for r in self.db.execute("SELECT numero FROM assoc_acervo")}

    def vios(self):
        return {r[0]: {"ci": r[1], "empresa": r[2]} for r in self.db.execute(
            "SELECT numero, ci, empresa FROM processos WHERE numero != ''")}

    def vios_trt7_ativos(self):
        return sorted({r[0] for r in self.db.execute(
            "SELECT numero FROM processos WHERE tribunal = '5.07' AND ativo = 1 AND numero != ''")})

    def djen(self):
        try:
            return {r[0] for r in self.db.execute("SELECT numero FROM djen_processos")}
        except Exception:  # noqa: BLE001 — DJEN ainda não rodou
            return set()

    def conhecidos(self, numero):
        return {r[0] for r in self.db.execute("SELECT associado FROM assoc_associados WHERE principal = ?", (numero,))}

    def gravar_acervo(self, numeros, hoje):
        for n in numeros:
            self.db.execute("INSERT INTO assoc_acervo VALUES (?, ?, ?) ON CONFLICT(numero) DO UPDATE SET ultima_vez = ?",
                            (n, hoje, hoje, hoje))

    def gravar_arquivados(self, numeros, hoje):
        for n in numeros:
            self.db.execute("INSERT INTO assoc_arquivados VALUES (?, ?, ?) ON CONFLICT(numero) DO UPDATE SET ultima_vez = ?",
                            (n, hoje, hoje, hoje))

    def gravar_principal(self, numero, situacao, qtd, hoje, erro=""):
        self.db.execute("INSERT OR REPLACE INTO assoc_principais VALUES (?, ?, ?, ?, 1, ?)",
                        (numero, situacao, qtd, hoje, erro))

    def gravar_associado(self, principal, a, hoje, novo, nivel):
        self.db.execute("INSERT OR IGNORE INTO assoc_associados VALUES (?, ?, ?, ?, ?, ?)",
                        (principal, a["numero"], a.get("orgao") or "", hoje, int(novo), nivel))

    def fechar_rodada(self, hoje, res):
        self.db.execute("INSERT OR REPLACE INTO assoc_rodadas (data, acervo, verificados, com_associados, fora_acervo, "
                        "erros, novos, vermelhos, completa, base, arquivados) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (hoje, res["acervo"], res["verificados"], res["com_associados"], len(res["fora_do_acervo"]),
                         len(res["erros"]), len(res["novos"]),
                         sum(1 for n in res["novos"] if n["nivel"] == "VERMELHO"), int(res["completa"]),
                         int(res["base_global"]), len(res["arquivados_vios"])))
        self.db.commit()


def rodar(estado, lido, hoje=None, simular=False):
    """Compara o que foi lido no PJe (saída de ler_acervo) com o que já foi visto e grava."""
    hoje = (hoje or date.today()).isoformat()
    ea = EstadoAssoc(estado)
    base_global = ea.eh_base()
    acervo_antes = ea.no_acervo()
    vios, djen = ea.vios(), ea.djen()
    acervo = lido.get("acervo")
    res = {"data": hoje, "simulado": simular, "base_global": base_global, "acervo": len(acervo) if acervo else 0,
           "total_assoc": lido.get("total_assoc"), "verificados": 0, "com_associados": 0, "novos": [], "base": [],
           "fora_do_acervo": [], "arquivados_vios": [], "arquivados_total": len(lido["arquivados"]) if lido.get("arquivados") else 0,
           "erros": [], "completa": not lido.get("erro"), "interrompido": lido.get("erro", "")}
    for numero, r in lido.get("principais", {}).items():
        if r["situacao"] != "ok":
            res["erros"].append((numero, r.get("erro") or "erro"))
            continue
        res["verificados"] += 1
        if r["associados"]:
            res["com_associados"] += 1
        # base deste processo: 1ª rodada de todas ou processo que acabou de entrar no acervo
        base = base_global or (bool(acervo_antes) and numero not in acervo_antes)
        conhecidos = ea.conhecidos(numero)
        p = vios.get(numero) or {}
        for a in r["associados"]:
            if a["numero"] in conhecidos:
                continue
            info = vios.get(a["numero"])
            reg = {"principal": numero, "numero": a["numero"], "orgao": a.get("orgao") or "",
                   "principal_ci": p.get("ci", ""), "empresa": p.get("empresa", ""), "principal_no_vios": bool(p),
                   "no_vios": bool(info), "no_djen": a["numero"] in djen}
            if base:
                reg["nivel"] = "BASE"
                res["base"].append(reg)
            else:
                reg["nivel"] = "INFO" if info else ("VERMELHO" if p else "AMARELO")
                res["novos"].append(reg)
            if not simular:
                ea.gravar_associado(numero, a, hoje, not base, reg["nivel"])
        if not simular:
            ea.gravar_principal(numero, "ok", len(r["associados"]), hoje)
    if acervo is not None:
        no_acervo, arquivados = set(acervo), set(lido.get("arquivados") or [])
        fora = [n for n in ea.vios_trt7_ativos() if n not in no_acervo]
        res["arquivados_vios"] = [n for n in fora if n in arquivados]
        res["fora_do_acervo"] = [n for n in fora if n not in arquivados]
        if not simular:
            ea.gravar_acervo(acervo, hoje)
            if lido.get("arquivados"):
                ea.gravar_arquivados(lido["arquivados"], hoje)
            for n in res["fora_do_acervo"]:
                ea.gravar_principal(n, "fora_do_acervo", 0, hoje)
            for n in res["arquivados_vios"]:
                ea.gravar_principal(n, "arquivado_pje", 0, hoje)
    else:
        res["completa"] = False
    if res["erros"]:
        res["completa"] = False
    if not simular:
        ea.fechar_rodada(hoje, res)
    return res


# ---------------- processos do VIOS fora do acervo e dos arquivados: onde estão (pelo DJEN) ----------------
GRUPOS_FORA = {
    "sem_escritorio": "1º grau, sem advogado do escritório nas publicações: conferir a habilitação no PJe",
    "so_pessoal": "1º grau, com advogado do escritório, mas fora do acervo da sociedade: incluir a sociedade",
    "segundo_grau": "2º grau, TST ou ação originária do TRT (o acervo do 1º grau não mostra; o DJEN acompanha)",
    "sem_publicacao": "Sem publicação no DJEN: conferir no PJe",
}
ESCRITORIO_PADRAO = r"FEITOSA"  # advogados do escritório nas publicações do DJEN (VIGIA_ESCRITORIO_ADVOGADOS)


def classificar_fora(numero, itens, padrao_escritorio=ESCRITORIO_PADRAO):
    """Publicações do DJEN de um processo -> {grupo, orgao, classe, ultima, escritorio, publicacoes}."""
    itens = sorted(itens or [], key=lambda i: i.get("data_disponibilizacao") or "", reverse=True)
    rx = re.compile(padrao_escritorio or ESCRITORIO_PADRAO, re.I)
    escritorio = any(rx.search((a.get("advogado") or {}).get("nome") or "") or
                     rx.search(str((a.get("advogado") or {}).get("numero_oab") or ""))
                     for i in itens for a in (i.get("destinatarioadvogados") or []))
    u = itens[0] if itens else {}
    orgao = (u.get("nomeOrgao") or "").strip()
    if numero.endswith(".5.07.0000") or (orgao and not re.search(r"\bVara\b", orgao, re.I)):
        grupo = "segundo_grau"
    elif not itens:
        grupo = "sem_publicacao"
    else:
        grupo = "so_pessoal" if escritorio else "sem_escritorio"
    return {"numero": numero, "grupo": grupo, "orgao": orgao, "classe": (u.get("nomeClasse") or "").strip(),
            "ultima": (u.get("data_disponibilizacao") or "")[:10], "escritorio": escritorio, "publicacoes": len(itens)}


def ligar_fora(estado, consulta, hoje=None, padrao_escritorio=ESCRITORIO_PADRAO, pausa=1.5, aviso=print):
    """Classifica pelo DJEN os processos do VIOS que a última rodada deu como fora do acervo e dos arquivados."""
    hoje = (hoje or date.today()).isoformat()
    ea = EstadoAssoc(estado)
    numeros = [r[0] for r in ea.db.execute("SELECT numero FROM assoc_principais WHERE situacao = 'fora_do_acervo' "
                                           "ORDER BY numero")]
    saida = []
    for n in numeros:
        try:
            r = classificar_fora(n, consulta(n), padrao_escritorio)
        except Exception as erro:  # noqa: BLE001
            aviso(f"  {n}: erro no DJEN ({erro})")
            continue
        saida.append(r)
        time.sleep(pausa)
    ea.db.execute("DELETE FROM assoc_fora")
    for r in saida:
        ea.db.execute("INSERT INTO assoc_fora VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (r["numero"], r["grupo"], r["orgao"], r["classe"], r["ultima"], int(r["escritorio"]),
                       r["publicacoes"], hoje))
    ea.db.commit()
    return saida


def relatorio_fora(lista):
    if not lista:
        return ""
    L = [f"ONDE ESTÃO os processos do VIOS fora do acervo e dos arquivados ({len(lista)}), pelo DJEN:"]
    for g, texto in GRUPOS_FORA.items():
        grupo = [r for r in lista if r["grupo"] == g]
        if grupo:
            L.append(f"  {texto} ({len(grupo)}):")
            L += [f"    - {r['numero']} · {r['orgao'] or '-'} · {r['classe'] or '-'} · última publicação {r['ultima'] or '-'}"
                  for r in grupo]
    return "\n".join(L) + "\n"


def relatorio(res):
    L = [f"VIGIA · PROCESSOS ASSOCIADOS NO PJe · {res['data']}", "=" * 60,
         f"Acervo Geral: {res['acervo'] or '-'} processos · com associação: {res['total_assoc'] if res['total_assoc'] is not None else '-'}"
         f" · lidos: {res['verificados']} · erros: {len(res['erros'])} · arquivados no PJe: {res['arquivados_total'] or '-'}"
         f" · processos do VIOS arquivados no PJe: {len(res['arquivados_vios'])} · fora do acervo e dos arquivados: "
         f"{len(res['fora_do_acervo'])}" + (" · (simulação: nada gravado)" if res.get("simulado") else ""), ""]
    if res.get("interrompido"):
        L += [f"INCOMPLETA: {res['interrompido']}", ""]
    if res.get("base_global"):
        L += ["PRIMEIRA RODADA (base): nada é alerta hoje; os associados que já existem ficam guardados.", ""]

    def linha(r):
        onde = "no VIOS" if r["no_vios"] else "NÃO está no VIOS"
        princ = f"CI {r['principal_ci']}, {r['empresa']}" if r["principal_no_vios"] else "principal fora do VIOS"
        return (f"  • {r['numero']} ({r['orgao'] or '-'}) associado a {r['principal']} ({princ}) · {onde}"
                + (" · já avisado pelo DJEN" if r["no_djen"] else ""))

    verm = [r for r in res["novos"] if r["nivel"] == "VERMELHO"]
    amar = [r for r in res["novos"] if r["nivel"] == "AMARELO"]
    info = [r for r in res["novos"] if r["nivel"] == "INFO"]
    if not res.get("base_global"):
        L += [f"🔴 VERMELHO · associado NOVO fora do VIOS, com o principal no VIOS ({len(verm)})"]
        L += [linha(r) for r in verm] or ["  (nenhum)"]
        L += ["", f"🟡 AMARELO · associado novo fora do VIOS, principal também fora da lista do VIOS ({len(amar)})"]
        L += [linha(r) for r in amar] or ["  (nenhum)"]
        L += ["", f"Associado novo que já está no VIOS ({len(info)})"] + ([linha(r) for r in info] or ["  (nenhum)"]) + [""]
    if res["base"]:
        fora = [r for r in res["base"] if not r["no_vios"]]
        cliente = [r for r in fora if r["principal_no_vios"]]
        outros = [r for r in fora if not r["principal_no_vios"]]
        L += [f"BASE: associados que já existiam ({len(res['base'])}); fora do VIOS: {len(fora)}."]
        L += [f"  Com o principal NO VIOS (cliente nosso; conferir) ({len(cliente)}):"]
        L += [linha(r) for r in cliente] or ["  (nenhum)"]
        L += [f"  Com o principal também fora do VIOS ({len(outros)}):"]
        L += [linha(r) for r in outros] or ["  (nenhum)"]
        L.append("")
    if res["arquivados_vios"]:
        L += [f"ATIVOS no VIOS, mas ARQUIVADOS no PJe ({len(res['arquivados_vios'])}) — atualizar o VIOS:"]
        L += [f"  - {n}" for n in res["arquivados_vios"]]
        L.append("")
    if res["fora_do_acervo"]:
        L += [f"Processos do TRT7 do VIOS fora do Acervo Geral e dos Arquivados do login ({len(res['fora_do_acervo'])})"
              " — 2º grau/TST ou a sociedade não está no processo; sem a proteção do nível 3 (só o DJEN):"]
        L += [f"  - {n}" for n in res["fora_do_acervo"]]
        L.append("")
    if res["erros"]:
        L += [f"ERROS ({len(res['erros'])})"] + [f"  - {n}: {e}" for n, e in res["erros"]]
    return "\n".join(L) + "\n"
