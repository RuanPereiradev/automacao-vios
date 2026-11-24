"""Vigia, nível 3: "Processos associados" de cada processo principal no PJe do TRT7 (rede de segurança do DJEN).

Quando o juiz reconhece que um cumprimento de sentença pertence a um processo principal, o PJe mostra o cumprimento
como "Processo associado" na linha do principal no Acervo Geral (botão com ícone de corrente, aria-label "Processos
associados"). Conferido em 23/11/2026: o principal 0002754-04.2025.5.07.0038 mostra o CumPrSe 0001368-02.2026.5.07.0038.

Rotina diária (python3 vigia.py associados), formato "Balanceado": TODOS os processos ativos do TRT7 da lista do VIOS
(tabela processos). Para cada um, no Acervo Geral: pesquisa o número (campo do acervo), espera a linha do processo,
clica no botão "Processos associados" (só abre uma janela de consulta), lê a lista (paginação, se houver) e fecha com
Esc. Não abre documento, não peticiona, não assina, não altera nada no PJe.

Base: a 1ª leitura de cada principal só guarda os associados que já existem (auditoria, sem alerta). Depois, associado
NOVO = alerta. VERMELHO se o associado não está no VIOS (o escritório pode não estar nele); se já está no VIOS ou já foi
avisado pelo DJEN, fica registrado como informação.

Sem o botão na linha = o processo não tem associados (o PJe só mostra o ícone quando há associação).
Processo que não aparece no Acervo Geral (o advogado do login não está nele) fica como "fora do acervo".
Login pelo Presto (src/acesso_pje.py); se a sessão cair, tenta entrar de novo UMA vez e, se não der, para.
"""
import json
import re
import time
from datetime import date

from vigia_estado import CNJ, normalizar  # noqa: F401  (CNJ usado nos testes)

ACERVO = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/acervo-geral"

ESQUEMA_ASSOC = """
CREATE TABLE IF NOT EXISTS assoc_principais (
  numero TEXT PRIMARY KEY, situacao TEXT, qtd INTEGER, verificado_em TEXT, base_feita INTEGER, erro TEXT);
CREATE TABLE IF NOT EXISTS assoc_associados (
  principal TEXT, associado TEXT, orgao TEXT, visto_em TEXT, novo INTEGER, nivel TEXT,
  PRIMARY KEY (principal, associado));
CREATE TABLE IF NOT EXISTS assoc_rodadas (
  data TEXT PRIMARY KEY, verificados INTEGER, com_associados INTEGER, fora_acervo INTEGER, erros INTEGER,
  novos INTEGER, vermelhos INTEGER, completa INTEGER);
"""

# ---------------- JavaScript da página do Acervo Geral ----------------
# situação da linha do processo pesquisado: existe? tem o botão "Processos associados"? (e clica, se pedido)
JS_LINHA = r"""(function(numero, clicar){
  function visivel(e) { var r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  var det = [].filter.call(document.querySelectorAll('button[aria-label]'), function(b) {
    return visivel(b) && /^Detalhes do Processo/i.test(b.getAttribute('aria-label') || '') &&
           (b.getAttribute('aria-label') || '').indexOf(numero) >= 0;
  })[0];
  if (!det) {
    var txt = (document.body.innerText || '');
    return JSON.stringify({linha: false, vazio: /nenhum (registro|processo|resultado)/i.test(txt),
                           carregando: !!document.querySelector('mat-progress-bar, mat-spinner, .loading')});
  }
  var linha = det.closest('tr, mat-row, [role=row]') || det.parentElement;
  var b = linha.querySelector('button[aria-label="Processos associados"], pje-processo-associado button');
  if (b && clicar) { b.scrollIntoView({block: 'center'}); b.click(); }
  return JSON.stringify({linha: true, botao: !!b, clicou: !!(b && clicar)});
})(%s, %s)"""

# lê a janela "Processos associados": linhas com número e órgão, paginação "1 - 10 de 23"
JS_LER = r"""(function(principal){
  var cnj = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g;
  var caixas = [].slice.call(document.querySelectorAll('mat-dialog-container, .cdk-overlay-pane, [role=dialog]'))
    .filter(function(c) { return !c.querySelector('mat-tooltip-component, .mat-tooltip') && /associad|rg[ãa]o julgador/i.test(c.innerText || ''); });
  if (!caixas.length) return JSON.stringify({aberta: false});
  var cx = caixas[caixas.length - 1];
  var itens = [];
  [].forEach.call(cx.querySelectorAll('tr, mat-row, [role=row]'), function(l) {
    var t = (l.innerText || '').replace(/\s+/g, ' ').trim();
    var ns = (t.match(cnj) || []).filter(function(n) { return n !== principal; });
    if (ns.length) itens.push({numero: ns[0], orgao: t.replace(cnj, '').replace(/\s+/g, ' ').trim()});
  });
  var texto = (cx.innerText || '').replace(/\s+/g, ' ').trim();
  if (!itens.length) (texto.match(cnj) || []).forEach(function(n) {
    if (n !== principal && !itens.some(function(i) { return i.numero === n; })) itens.push({numero: n, orgao: ''});
  });
  var pg = texto.match(/(\d+)\s*[-–]\s*(\d+)\s*de\s*(\d+)/);
  var prox = cx.querySelector('button[aria-label*="próxima" i], button[aria-label*="next" i], .mat-paginator-navigation-next');
  return JSON.stringify({aberta: true, itens: itens, texto: texto.slice(0, 600),
                         de: pg ? +pg[2] : null, total: pg ? +pg[3] : null,
                         tem_proxima: !!(prox && !prox.disabled && prox.getAttribute('aria-disabled') !== 'true')});
})(%s)"""

# vai para a próxima página da lista de associados (paginação: permitido)
JS_PROXIMA = r"""(function(){
  var cx = [].slice.call(document.querySelectorAll('mat-dialog-container, .cdk-overlay-pane, [role=dialog]'))
    .filter(function(c) { return !c.querySelector('mat-tooltip-component, .mat-tooltip') && /associad|rg[ãa]o julgador/i.test(c.innerText || ''); }).pop();
  var b = cx && cx.querySelector('button[aria-label*="próxima" i], button[aria-label*="next" i], .mat-paginator-navigation-next');
  if (!b || b.disabled) return 'nao';
  b.click(); return 'ok';
})()"""

# fecha a janela: Esc; se não fechar, botão Fechar/X ou clique no fundo escuro
JS_FECHAR = r"""(function(forte){
  function aberta() { return [].some.call(document.querySelectorAll('mat-dialog-container, .cdk-overlay-pane, [role=dialog]'),
    function(c) { return !c.querySelector('mat-tooltip-component, .mat-tooltip') && /associad|rg[ãa]o julgador/i.test(c.innerText || ''); }); }
  if (!aberta()) return 'fechada';
  var alvo = document.activeElement || document.body;
  ['keydown', 'keyup'].forEach(function(n) {
    alvo.dispatchEvent(new KeyboardEvent(n, {key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true}));
  });
  if (forte) {
    var cx = [].slice.call(document.querySelectorAll('mat-dialog-container, .cdk-overlay-pane, [role=dialog]'))
      .filter(function(c) { return !c.querySelector('mat-tooltip-component, .mat-tooltip') && /associad|rg[ãa]o julgador/i.test(c.innerText || ''); }).pop();
    var x = cx && [].filter.call(cx.querySelectorAll('button'), function(b) {
      return /fechar|close/i.test((b.getAttribute('aria-label') || '') + ' ' + (b.innerText || '') + ' ' + (b.getAttribute('mattooltip') || ''));
    })[0];
    if (x) x.click();
    else { var fundo = document.querySelector('.cdk-overlay-backdrop'); if (fundo) fundo.click(); }
  }
  return 'esc';
})(%s)"""


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


def ler_no_pje(w, t, numero, js, pesquisar, maximo_busca=25):
    """Lê os associados de um principal na aba do Acervo Geral.

    js(codigo) roda JavaScript na aba; pesquisar(numero) digita o número no campo do acervo e aperta Enter.
    Devolve {"situacao": "ok" | "fora_do_acervo" | "erro", "associados": [{numero, orgao}], "erro": str}."""
    q = json.dumps
    js(JS_FECHAR % "true")  # nada aberto de antes
    pesquisar(numero)
    linha = _esperar(lambda: (lambda r: r if r.get("linha") or (r.get("vazio") and not r.get("carregando")) else None)(
        json.loads(js(JS_LINHA % (q(numero), "false")))), maximo_busca)
    if not linha or not linha.get("linha"):
        return {"situacao": "fora_do_acervo", "associados": [], "erro": ""}
    if not linha.get("botao"):
        return {"situacao": "ok", "associados": [], "erro": ""}
    json.loads(js(JS_LINHA % (q(numero), "true")))
    vistos, paginas = {}, 0
    while True:
        r = _esperar(lambda: (lambda x: x if x.get("aberta") else None)(json.loads(js(JS_LER % q(numero)))), 12)
        if not r:
            return {"situacao": "erro", "associados": [], "erro": "a janela de processos associados não abriu"}
        # a lista pode chegar depois da janela: espera um pouco se ainda vazia
        if not r.get("itens"):
            r2 = _esperar(lambda: (lambda x: x if x.get("itens") else None)(json.loads(js(JS_LER % q(numero)))), 6)
            r = r2 or r
        for i in r.get("itens") or []:
            vistos.setdefault(i["numero"], i)
        paginas += 1
        if not r.get("tem_proxima") or paginas >= 10 or (r.get("total") and len(vistos) >= r["total"]):
            break
        if js(JS_PROXIMA) != "ok":
            break
        time.sleep(2)
    js(JS_FECHAR % "false")
    if not _esperar(lambda: js(JS_FECHAR % "false") == "fechada", 4):
        js(JS_FECHAR % "true")
    total = r.get("total")
    if total and len(vistos) < total:
        return {"situacao": "erro", "associados": list(vistos.values()),
                "erro": f"li {len(vistos)} de {total} associados"}
    return {"situacao": "ok", "associados": list(vistos.values()), "erro": ""}


class EstadoAssoc:
    """Tabelas do nível 3 dentro do mesmo dados/vigia.sqlite (usa a conexão do vigia_estado.Estado)."""

    def __init__(self, estado):
        self.db = estado.db
        self.db.executescript(ESQUEMA_ASSOC)

    def principais(self, numeros=None, limite=None):
        """Processos ativos do TRT7 da lista do VIOS; os nunca verificados (ou verificados há mais tempo) primeiro."""
        if numeros:
            return list(dict.fromkeys(numeros))
        sql = ("SELECT p.numero, MIN(COALESCE(a.verificado_em, '')) AS quando FROM processos p "
               "LEFT JOIN assoc_principais a ON a.numero = p.numero "
               "WHERE p.tribunal = '5.07' AND p.ativo = 1 AND p.numero != '' "
               "GROUP BY p.numero ORDER BY quando, p.numero")
        lista = [r[0] for r in self.db.execute(sql)]
        return lista[:int(limite)] if limite else lista

    def vios(self):
        return {r[0]: {"ci": r[1], "empresa": r[2]} for r in self.db.execute(
            "SELECT numero, ci, empresa FROM processos WHERE numero != ''")}

    def djen(self):
        try:
            return {r[0] for r in self.db.execute("SELECT numero FROM djen_processos")}
        except Exception:  # noqa: BLE001 — DJEN ainda não rodou
            return set()

    def base_feita(self, numero):
        r = self.db.execute("SELECT base_feita FROM assoc_principais WHERE numero = ?", (numero,)).fetchone()
        return bool(r and r[0])

    def conhecidos(self, numero):
        return {r[0] for r in self.db.execute("SELECT associado FROM assoc_associados WHERE principal = ?", (numero,))}

    def gravar(self, numero, lido, hoje, base, novos):
        ok = lido["situacao"] == "ok"
        self.db.execute(
            "INSERT INTO assoc_principais VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(numero) DO UPDATE SET "
            "situacao = excluded.situacao, qtd = excluded.qtd, verificado_em = excluded.verificado_em, "
            "base_feita = MAX(base_feita, excluded.base_feita), erro = excluded.erro",
            (numero, lido["situacao"], len(lido["associados"]), hoje, int(ok), lido.get("erro") or ""))
        niveis = {n["numero"]: n["nivel"] for n in novos}
        for a in lido["associados"]:
            self.db.execute("INSERT OR IGNORE INTO assoc_associados VALUES (?, ?, ?, ?, ?, ?)",
                            (numero, a["numero"], a.get("orgao") or "", hoje, int(not base),
                             niveis.get(a["numero"], "BASE" if base else "")))

    def fechar_rodada(self, hoje, res):
        self.db.execute("INSERT OR REPLACE INTO assoc_rodadas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (hoje, res["verificados"], res["com_associados"], len(res["fora_do_acervo"]),
                         len(res["erros"]), len(res["novos"]), sum(1 for n in res["novos"] if n["nivel"] == "VERMELHO"),
                         int(res["completa"])))
        self.db.commit()


ERROS_SEGUIDOS = 5  # tantos erros seguidos = algo quebrou (Chrome fechado, tela mudou): para em vez de insistir


def rodar(estado, ler, hoje=None, numeros=None, limite=None, simular=False, aviso=print, pausa=1.0, parar=None):
    """Lê os associados de cada principal com ler(numero) e compara com o que já foi visto.

    ler: função numero -> {"situacao", "associados", "erro"} (no Mac: ler_no_pje; nos testes: falso).
    parar: função () -> motivo (str) para interromper (ex.: sessão do PJe caiu e não voltou)."""
    hoje = (hoje or date.today()).isoformat()
    ea = EstadoAssoc(estado)
    lista = ea.principais(numeros, limite)
    vios, djen = ea.vios(), ea.djen()
    res = {"data": hoje, "simulado": simular, "total": len(lista), "verificados": 0, "com_associados": 0,
           "novos": [], "base": [], "fora_do_acervo": [], "erros": [], "completa": True, "interrompido": ""}
    seguidos = 0
    for n, numero in enumerate(lista, 1):
        motivo = parar() if parar else ""
        if not motivo and seguidos >= ERROS_SEGUIDOS:
            motivo = f"{seguidos} erros seguidos (a tela do PJe pode ter mudado ou o Chrome fechou)"
        if motivo:
            res["interrompido"], res["completa"] = motivo, False
            break
        try:
            lido = ler(numero)
        except Exception as erro:  # noqa: BLE001 — um processo com erro não para os outros
            lido = {"situacao": "erro", "associados": [], "erro": str(erro)}
        if lido["situacao"] == "fora_do_acervo":
            res["fora_do_acervo"].append(numero)
        elif lido["situacao"] == "erro":
            res["erros"].append((numero, lido.get("erro") or "erro"))
        else:
            res["verificados"] += 1
        seguidos = seguidos + 1 if lido["situacao"] == "erro" else 0
        if lido["situacao"] != "ok":  # fora do acervo ou erro: nada a comparar
            if not simular and lido["situacao"] == "fora_do_acervo":
                ea.gravar(numero, lido, hoje, True, [])
                ea.db.commit()
            time.sleep(pausa)
            continue
        if lido["associados"]:
            res["com_associados"] += 1
        base = not ea.base_feita(numero)
        conhecidos = ea.conhecidos(numero)
        novos = []
        for a in lido["associados"]:
            if a["numero"] in conhecidos:
                continue
            info = vios.get(a["numero"])
            reg = {"principal": numero, "numero": a["numero"], "orgao": a.get("orgao") or "",
                   "principal_ci": (vios.get(numero) or {}).get("ci", ""),
                   "empresa": (vios.get(numero) or {}).get("empresa", ""),
                   "no_vios": bool(info), "no_djen": a["numero"] in djen}
            if base:
                res["base"].append(reg)
            else:
                reg["nivel"] = "INFO" if info else "VERMELHO"
                novos.append(reg)
        res["novos"] += novos
        if not simular:
            ea.gravar(numero, lido, hoje, base, novos)
            ea.db.commit()
        if n % 20 == 0:
            aviso(f"  associados: {n}/{len(lista)} principais lidos")
        time.sleep(pausa)
    if res["erros"] or res["interrompido"]:
        res["completa"] = False
    if not simular and not numeros and not limite:
        ea.fechar_rodada(hoje, res)
    elif not simular:
        ea.db.commit()
    return res


def relatorio(res):
    L = [f"VIGIA · PROCESSOS ASSOCIADOS NO PJe · {res['data']}", "=" * 60,
         f"Principais: {res['total']} · lidos: {res['verificados']} · com associados: {res['com_associados']} · "
         f"fora do acervo: {len(res['fora_do_acervo'])} · erros: {len(res['erros'])}"
         + (" · (simulação: nada gravado)" if res.get("simulado") else ""), ""]
    if res.get("interrompido"):
        L += [f"INTERROMPIDO: {res['interrompido']}", ""]

    def linha(r):
        onde = "no VIOS" if r["no_vios"] else "NÃO está no VIOS"
        return (f"  • {r['numero']} ({r['orgao'] or '-'}) associado ao principal {r['principal']}"
                f" (CI {r['principal_ci'] or '-'}, {r['empresa'] or '-'}) · {onde}"
                + (" · já avisado pelo DJEN" if r["no_djen"] else ""))

    verm = [r for r in res["novos"] if r["nivel"] == "VERMELHO"]
    info = [r for r in res["novos"] if r["nivel"] != "VERMELHO"]
    L += [f"🔴 VERMELHO · associado NOVO fora do VIOS ({len(verm)})"] + ([linha(r) for r in verm] or ["  (nenhum)"])
    L += ["", f"Associado novo que já está no VIOS ({len(info)})"] + ([linha(r) for r in info] or ["  (nenhum)"])
    if res["base"]:
        L += ["", f"BASE (1ª leitura destes principais: associados que já existiam, sem alerta) ({len(res['base'])})"]
        L += [linha(r) for r in res["base"]]
    if res["fora_do_acervo"]:
        L += ["", f"Fora do Acervo Geral do login ({len(res['fora_do_acervo'])}) — o advogado do login não está nele:"]
        L += [f"  - {n}" for n in res["fora_do_acervo"]]
    if res["erros"]:
        L += ["", f"ERROS ({len(res['erros'])})"] + [f"  - {n}: {e}" for n, e in res["erros"]]
    return "\n".join(L) + "\n"
