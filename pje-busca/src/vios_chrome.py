"""Leitura do VIOS pelo Chrome aberto no Mac (AppleScript), só GET, para o vigia (vigia.py).

Usa a sessão do VIOS de uma aba do Chrome. As pesquisas são feitas com fetch() dentro da aba (a tela não muda)
e só as colunas necessárias voltam para o Python. Se a sessão caiu, abre uma aba nova no entrar.php e entra com
VIOS_USUARIO/VIOS_SENHA do pje-busca/.env (campos form[usuario]/form[senha]); a aba aberta pelo bot é fechada no
fim. Nunca imprime nem grava a senha. Nunca clica em Salvar/Apagar: só lê listas e formulários.

Lista (conferida em 23/11/2026): Processos > Área 3 (Trabalhista) + cliente na Parte Passiva (P) + ativos.
A tela devolve no máximo 500 linhas: com 500 a lista é tratada como incompleta (vigia_estado não marca saídas).
"""
import json
import re
import time
from urllib.parse import quote

import chrome_mac as CM

VIOS = "https://roneely.vios.com.br/"
LISTA = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
ID_MAX = 2 ** 31  # ids de aba do Chrome passam de 1 bilhão (ver testar_processos.py)
TETO_TELA = 500


class ViosErro(Exception):
    pass


def url_lista(area="3", tipo_parte="P", advogados=(), limite="9999999"):
    """Endereço (relativo) da lista de processos ativos com os filtros do vigia."""
    partes = ["/" + LISTA, f"pesq[pr_areas_id][]={quote(str(area))}"]  # "/": não depende da página da aba
    if tipo_parte:
        partes.append(f"pesq[tipos_partes_id]={quote(str(tipo_parte))}")
    partes += [f"pesq[advogados_id][]={quote(str(a))}" for a in advogados if str(a).strip()]
    partes += ["pesq[filtros_multi][]=ativos", f"pesq[limit]={limite}", "Pesq=Pesquisar"]
    return "&".join(partes)


# ---------------------------------------------------------------- JavaScript (roda dentro da aba do VIOS)
# colunas da lista (final do data-id "processos-lista_linha_<n>_<coluna>") -> campo
COLUNAS = {
    "ci": "processos_id", "cliente": "clientes_nome", "ativa": "ativahtml", "passiva": "passivahtml",
    "numero": "nro_proc_html", "advogado": "advogado_nome", "auxiliares": "advogados_auxiliares_abr",
    "orgao": "orgaos_nome", "uf": "orgaos_uf", "vara": "vara", "acao": "processos_acoes_nome",
    "data_acao": "data_acao", "area": "pr_areas_nome",
}

# Sessão expirada: o VIOS responde 200 com só '<meta HTTP-EQUIV="Refresh" CONTENT="0; URL = ./entrar.php">'
# (sem redirecionar e sem formulário). Conta também o redirecionamento e o formulário de login.
_JS_SAIU = r"""function _vigiaTexto(r) {
  // o VIOS manda as páginas em Windows-1252 (ISO-8859-1): r.text() trocava os acentos por "\ufffd"
  return r.arrayBuffer().then(function(b) {
    try { return new TextDecoder('utf-8', {fatal: true}).decode(b); }
    catch (e) { return new TextDecoder('windows-1252').decode(b); }
  });
}
function _vigiaSaiu(url, h) {
  return /entrar\.php/i.test(url) || /http-equiv\s*=\s*["']?refresh[^>]*entrar\.php/i.test(h)
      || /name=["']form\[senha\]["']/i.test(h);
}
"""

_JS_LISTA = _JS_SAIU + r"""
fetch(%(url)s, {credentials: 'same-origin'}).then(function(r) {
  return _vigiaTexto(r).then(function(h) { return [r.url, h]; });
}).then(function(x) {
  var d = new DOMParser().parseFromString(x[1], 'text/html');
  if (_vigiaSaiu(x[0], x[1])) {
    window[%(chave)s] = JSON.stringify({ok: false, login: true}); return;
  }
  var cols = %(cols)s, linhas = [];
  [].forEach.call(d.querySelectorAll("tr[id^='processos-lista_linha_']"), function(tr) {
    var cel = {};
    [].forEach.call(tr.querySelectorAll('td[data-id]'), function(td) {
      var k = td.getAttribute('data-id').split('_linha_')[1];
      if (k) cel[k.replace(/^\d+_/, '')] = td;
    });
    var o = {};
    for (var campo in cols) {
      var td = cel[cols[campo]];
      o[campo] = td ? td.textContent.replace(/\s+/g, ' ').trim() : '';
    }
    o.ci = o.ci || tr.getAttribute('data-processos_id') || '';
    var v = cel['sinal_vinculo_processo'], el = v && v.querySelector('[title], [data-original-title]');
    o.vinculo = el ? (el.getAttribute('title') || el.getAttribute('data-original-title') || '').trim() : '';
    linhas.push(o);
  });
  var tot = d.querySelector('.geratabela_total_quantidade_original');
  window[%(chave)s] = JSON.stringify({ok: true, total: tot ? tot.textContent.replace(/\D/g, '') : '', linhas: linhas});
}).catch(function(e) { window[%(chave)s] = JSON.stringify({ok: false, erro: String(e)}); });
"""

# CNPJ pelo cadastro de pessoas: busca o nome (sem "(MATRIZ)"/"(FILIAL)"), abre até 6 cadastros achados e devolve
# só os dígitos do form[cpfcnpj] e se o form[clientes_nome] é igual ao nome procurado.
_JS_CNPJ = _JS_SAIU + r"""
(function() {
  function norm(t) { return (t || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/\s+/g, ' ').trim(); }
  var nome = %(nome)s, busca = nome.replace(/\s*\((MATRIZ|FILIAL)\)\s*$/i, '');
  fetch('/?pag=sys/clientes/clientes.php&pesq[busca]=' + encodeURIComponent(busca) + '&Pesq=Pesquisar',
        {credentials: 'same-origin'}).then(function(r) { return _vigiaTexto(r).then(function(h) { return [r.url, h]; }); })
    .then(function(x) {
    if (_vigiaSaiu(x[0], x[1])) { window[%(chave)s] = JSON.stringify({ok: false, login: true}); return; }
    var h = x[1], ids = [], re = /clientes-vis\.php[^"'<>\s]*?clientes_id=(\d+)/gi, m;
    h = h.replace(/&amp;/g, '&');
    while ((m = re.exec(h))) if (ids.indexOf(m[1]) < 0) ids.push(m[1]);
    return Promise.all(ids.slice(0, 6).map(function(id) {
      return fetch('/?pag=sys/clientes/clientes.php&act=edit&clientes_id=' + id, {credentials: 'same-origin'})
        .then(function(r) { return _vigiaTexto(r); }).then(function(h2) {
          var d = new DOMParser().parseFromString(h2, 'text/html');
          var c = d.querySelector("input[name='form[cpfcnpj]']"), n = d.querySelector("input[name='form[clientes_nome]']");
          return {doc: c ? c.value.replace(/\D/g, '') : '', igual: n ? norm(n.value) === norm(busca) || norm(n.value) === norm(nome) : false};
        });
    })).then(function(cads) { window[%(chave)s] = JSON.stringify({ok: true, achados: ids.length, cadastros: cads}); });
  }).catch(function(e) { window[%(chave)s] = JSON.stringify({ok: false, erro: String(e)}); });
})();
"""

_JS_LOGIN = r"""(function(u, s) {
  var iu = document.querySelector("input[name='form[usuario]']"), is = document.querySelector("input[name='form[senha]']");
  if (!iu || !is) return JSON.stringify({ok: false, erro: 'campos de login do VIOS não achados'});
  var set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  [[iu, u], [is, s]].forEach(function(p) {
    set.call(p[0], p[1]);
    ['input', 'change'].forEach(function(n) { p[0].dispatchEvent(new Event(n, {bubbles: true})); });
  });
  var f = is.form, b = f && f.querySelector("button[type=submit], input[type=submit]");
  if (b) b.click(); else if (f) { if (f.requestSubmit) f.requestSubmit(); else f.submit(); }
  else return JSON.stringify({ok: false, erro: 'formulário de login do VIOS não achado'});
  return JSON.stringify({ok: true});
})(%s, %s)"""


def _js_async(w, t, corpo, chave, maximo=240):
    """Roda `corpo` (que grava o resultado em window[chave]) e espera o resultado."""
    k = json.dumps(chave)
    CM.js(w, t, "(function(){window[%s]=null;" % k + corpo + "; return 'ok';})()")
    fim = time.monotonic() + maximo
    while time.monotonic() < fim:
        v = CM.js(w, t, "(function(){var v=window[%s]; if(v) window[%s]=null; return v||'';})()" % (k, k))
        if v:
            return json.loads(v)
        time.sleep(1.5)
    raise ViosErro(f"o VIOS não respondeu em {maximo} s")


# ---------------------------------------------------------------- sessão
class Sessao:
    """Aba do VIOS usada nas leituras. `aberta_pelo_bot` = fechar no fim."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.w = self.t = None
        self.aberta_pelo_bot = False

    def _aba_existente(self):
        abas = [a for a in CM.todas_abas() if "vios.com.br" in a[2] and a[0] < ID_MAX and a[1] < ID_MAX]
        abas.sort(key=lambda a: "entrar.php" in a[2])  # prefere aba já logada
        return abas[0] if abas else None

    def abrir(self):
        if not CM.disponivel():
            raise ViosErro("o vigia lê o VIOS pelo Chrome do Mac (AppleScript): só funciona no Mac")
        aba = self._aba_existente()
        if aba:
            self.w, self.t = aba[0], aba[1]
        else:
            self.w, self.t = CM.abrir_aba(VIOS + LISTA)
            self.aberta_pelo_bot = True
            CM.esperar(self.w, self.t, maximo=45, folga=2)
        return self

    def entrar(self):
        """A sessão caiu: entra numa aba nova com VIOS_USUARIO/VIOS_SENHA."""
        usuario, senha = self.cfg.get("VIOS_USUARIO", ""), self.cfg.get("VIOS_SENHA", "")
        if not usuario or not senha:
            raise ViosErro("a sessão do VIOS no Chrome caiu e faltam VIOS_USUARIO/VIOS_SENHA no pje-busca/.env "
                           "(ou entre no VIOS pelo Chrome e rode de novo)")
        if not self.aberta_pelo_bot:
            self.w, self.t = CM.abrir_aba(VIOS + "entrar.php")
            self.aberta_pelo_bot = True
        else:
            CM.ir(self.w, self.t, VIOS + "entrar.php")
        CM.esperar(self.w, self.t, maximo=45, folga=2)
        if not CM.url(self.w, self.t).startswith("http"):
            raise ViosErro("o Chrome não abriu o VIOS (aviso de certificado? abra o VIOS no Chrome uma vez e rode de novo)")
        r = json.loads(CM.js(self.w, self.t, _JS_LOGIN % (json.dumps(usuario), json.dumps(senha))))
        if not r.get("ok"):
            raise ViosErro(r.get("erro") or "não consegui preencher o login do VIOS")
        CM.esperar(self.w, self.t, maximo=45, folga=3)
        if "entrar.php" in CM.url(self.w, self.t):
            raise ViosErro("o VIOS continuou na tela de login (usuário/senha do .env?)")

    def lista(self, area="3", tipo_parte="P", advogados=()):
        """{"total": int|None, "linhas": [...], "completa": bool} da lista de processos ativos."""
        corpo = _JS_LISTA % {"url": json.dumps(url_lista(area, tipo_parte, advogados)), "chave": json.dumps("__vigiaLista"),
                             "cols": json.dumps(COLUNAS)}
        r = _js_async(self.w, self.t, corpo, "__vigiaLista")
        if r.get("login"):
            self.entrar()
            r = _js_async(self.w, self.t, corpo, "__vigiaLista")
        if not r.get("ok"):
            raise ViosErro("a lista do VIOS não veio: " + (r.get("erro") or ("continuou sem sessão depois do login"
                                                                       if r.get("login") else "?")))
        linhas = r.get("linhas") or []
        total = int(r["total"]) if (r.get("total") or "").isdigit() else None
        completa = bool(linhas) and len(linhas) < TETO_TELA and (total is None or total == len(linhas))
        return {"total": total, "linhas": linhas, "completa": completa}

    def cnpj(self, nome):
        """("ok", "<14 dígitos>") | ("pf", "") | ("varios", "cnpj1,cnpj2") | ("nao_achado", "") | ("erro", msg).
        CPF (pessoa física) não é guardado: só a marca "pf"."""
        corpo = _JS_CNPJ % {"nome": json.dumps(nome), "chave": json.dumps("__vigiaCnpj")}
        r = _js_async(self.w, self.t, corpo, "__vigiaCnpj", maximo=90)
        if r.get("login"):  # a sessão caiu no meio das consultas: entra de novo e repete esta
            self.entrar()
            r = _js_async(self.w, self.t, corpo, "__vigiaCnpj", maximo=90)
        if not r.get("ok"):
            return "erro", r.get("erro") or "?"
        return escolher_cnpj(r.get("cadastros") or [])

    def fechar(self):
        if self.aberta_pelo_bot and self.w is not None:
            try:
                CM.fechar_aba(self.w, self.t)
            except CM.ChromeMacErro:
                pass


def escolher_cnpj(cadastros):
    """Decide o CNPJ a partir dos cadastros achados ([{doc, igual}]). Prefere os de nome igual."""
    iguais = [c for c in cadastros if c.get("igual")] or cadastros
    cnpjs = sorted({c["doc"] for c in iguais if len(c.get("doc") or "") == 14})
    if len(cnpjs) == 1:
        return "ok", cnpjs[0]
    if len(cnpjs) > 1:
        return "varios", ",".join(cnpjs)
    if any(len(c.get("doc") or "") == 11 for c in iguais):
        return "pf", ""
    return "nao_achado", ""
