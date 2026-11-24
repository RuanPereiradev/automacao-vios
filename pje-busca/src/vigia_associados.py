"""Vigia, nível 3: "Processos associados" no Acervo Geral do PJe do TRT7 (rede de segurança do DJEN).

Quando o juiz reconhece que um cumprimento de sentença pertence a um processo principal, o PJe mostra o cumprimento
como "Processo associado" na linha do principal no Acervo Geral (botão com ícone de corrente, aria-label "Processos
associados"). Conferido em 23/11/2026: o principal 0002754-04.2025.5.07.0038 mostra o CumPrSe 0001368-02.2026.5.07.0038.

Como lê (24/11/2026, conferido no PJe real): o Acervo Geral tem o filtro "Processos com Associação" (botão da barra do
título). Com ele ligado a lista mostra só os processos do acervo que têm associação (60 de 358 nesse dia). Para cada
linha: clica em "Processos associados" (abre uma janela só de consulta), lê a tabela "Processo Associado · Órgão
Julgador" (paginação de 5 em 5, botão "Próximo") e fecha com Esc. Depois desliga o filtro e percorre o acervo inteiro
só para saber quais processos do VIOS estão nele ("fora do acervo" = o advogado do login não está no processo).
A pesquisa pelo número no campo do acervo NÃO serve: a lista deixa de atualizar depois de algumas buscas.
Não abre documento, não peticiona, não assina, não altera nada no PJe.

Alertas:
- A 1ª rodada completa é BASE: guarda o que já existe (auditoria, sem alerta).
- Depois, associado NOVO de um processo que já estava no acervo = alerta. VERMELHO se o associado não está no VIOS;
  se já está no VIOS, fica como informação. (Um processo que acabou de entrar no acervo vira base só dele.)
"""
import json
import time
from datetime import date

ACERVO = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/acervo-geral"
MAX_PAGINAS = 100  # 10 por página: até 1.000 processos no acervo

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
  erros INTEGER, novos INTEGER, vermelhos INTEGER, completa INTEGER, base INTEGER);
"""

# ---------------- JavaScript da página do Acervo Geral ----------------
_FORA_DO_DIALOGO = "function fora(e) { return !e.closest('mat-dialog-container, .cdk-overlay-pane'); }"
_CNJ = r"/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/"

# tira o filtro de número (se houver) e liga/desliga "Processos com Associação"
JS_FILTRO = r"""(function(ligar){
  var mudou = false;
  [].forEach.call(document.querySelectorAll('mat-chip, .mat-chip'), function(c) {
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
  var linhas = [];
  [].forEach.call(document.querySelectorAll('button[aria-label^="Detalhes do Processo"]'), function(b) {
    if (!fora(b)) return;
    var m = (b.getAttribute('aria-label') || '').match(%(cnj)s);
    if (!m) return;
    var l = b.closest('tr, mat-row, [role=row]') || b.parentElement;
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
  var det = [].filter.call(document.querySelectorAll('button[aria-label^="Detalhes do Processo"]'), function(b) {
    return fora(b) && (b.getAttribute('aria-label') || '').indexOf(numero) >= 0; })[0];
  if (!det) return 'sem_linha';
  var l = det.closest('tr, mat-row, [role=row]') || det.parentElement;
  var b = l.querySelector('button[aria-label="Processos associados"]');
  if (!b) return 'sem_botao';
  b.click(); return 'ok';
})(%%s)""" % {"fora": _FORA_DO_DIALOGO}

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


def ler_acervo(js, cobertura=True, max_paginas=MAX_PAGINAS, aviso=print):
    """Lê no PJe (aba do Acervo Geral já aberta e logada):
    {"principais": {numero: {"situacao", "associados", "erro"}}, "acervo": [números] ou None, "total_assoc", "erro"}."""
    out = {"principais": {}, "acervo": None, "total_assoc": None, "erro": ""}
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
            out["acervo"], _ = percorrer(js, None, max_paginas)
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

    def gravar_principal(self, numero, situacao, qtd, hoje, erro=""):
        self.db.execute("INSERT OR REPLACE INTO assoc_principais VALUES (?, ?, ?, ?, 1, ?)",
                        (numero, situacao, qtd, hoje, erro))

    def gravar_associado(self, principal, a, hoje, novo, nivel):
        self.db.execute("INSERT OR IGNORE INTO assoc_associados VALUES (?, ?, ?, ?, ?, ?)",
                        (principal, a["numero"], a.get("orgao") or "", hoje, int(novo), nivel))

    def fechar_rodada(self, hoje, res):
        self.db.execute("INSERT OR REPLACE INTO assoc_rodadas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (hoje, res["acervo"], res["verificados"], res["com_associados"], len(res["fora_do_acervo"]),
                         len(res["erros"]), len(res["novos"]),
                         sum(1 for n in res["novos"] if n["nivel"] == "VERMELHO"), int(res["completa"]),
                         int(res["base_global"])))
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
           "fora_do_acervo": [], "erros": [], "completa": not lido.get("erro"), "interrompido": lido.get("erro", "")}
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
                reg["nivel"] = "INFO" if info else "VERMELHO"
                res["novos"].append(reg)
            if not simular:
                ea.gravar_associado(numero, a, hoje, not base, reg["nivel"])
        if not simular:
            ea.gravar_principal(numero, "ok", len(r["associados"]), hoje)
    if acervo is not None:
        no_acervo = set(acervo)
        res["fora_do_acervo"] = [n for n in ea.vios_trt7_ativos() if n not in no_acervo]
        if not simular:
            ea.gravar_acervo(acervo, hoje)
            for n in res["fora_do_acervo"]:
                ea.gravar_principal(n, "fora_do_acervo", 0, hoje)
    else:
        res["completa"] = False
    if res["erros"]:
        res["completa"] = False
    if not simular:
        ea.fechar_rodada(hoje, res)
    return res


def relatorio(res):
    L = [f"VIGIA · PROCESSOS ASSOCIADOS NO PJe · {res['data']}", "=" * 60,
         f"Acervo Geral: {res['acervo'] or '-'} processos · com associação: {res['total_assoc'] if res['total_assoc'] is not None else '-'}"
         f" · lidos: {res['verificados']} · erros: {len(res['erros'])} · processos do VIOS fora do acervo: "
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
    info = [r for r in res["novos"] if r["nivel"] != "VERMELHO"]
    if not res.get("base_global"):
        L += [f"🔴 VERMELHO · associado NOVO fora do VIOS ({len(verm)})"] + ([linha(r) for r in verm] or ["  (nenhum)"])
        L += ["", f"Associado novo que já está no VIOS ({len(info)})"] + ([linha(r) for r in info] or ["  (nenhum)"]) + [""]
    if res["base"]:
        fora = [r for r in res["base"] if not r["no_vios"]]
        L += [f"BASE: associados que já existiam ({len(res['base'])}); destes, fora do VIOS ({len(fora)}):"]
        L += [linha(r) for r in fora] or ["  (nenhum)"]
        L.append("")
    if res["fora_do_acervo"]:
        L += [f"Processos do TRT7 do VIOS fora do Acervo Geral do login ({len(res['fora_do_acervo'])}) — sem a proteção do nível 3:"]
        L += [f"  - {n}" for n in res["fora_do_acervo"]]
        L.append("")
    if res["erros"]:
        L += [f"ERROS ({len(res['erros'])})"] + [f"  - {n}: {e}" for n, e in res["erros"]]
    return "\n".join(L) + "\n"
