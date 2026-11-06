"""Albi — entra nos tribunais pelo Presto e procura cada processo do último relatório (Mac).

  .venv/bin/python presto.py processos [pasta do resultado] [--tribunal tjce1] [--max N] [--conferir]

1. Acha o processos.csv do último relatório do Albi (o mais novo em albi/saida/*/ e em
   saida/albi/*/, que é onde a página /albi guarda) ou usa a pasta dada.
2. Pelo número CNJ de cada processo (J.TR e a origem) e pela instância do Sonar, diz o tribunal:
   TJCE (8.06), TRT7 (5.07), JFCE (4.05, origem 81xx) e TRF5 (4.05, o resto). Os outros tribunais
   ainda não têm login no Presto aqui e ficam listados como "fora".
3. Para cada tribunal: abre o login no Chrome aberto, entra pelo quadro do Presto (presto.login)
   e, na mesma aba, procura cada processo na consulta do tribunal (PJe: tela "Consultar processos";
   TRT7: detalhe do processo). Salva HTML, texto, elementos e print de cada um e escreve
   resumo.txt / resumo.json em <pasta do resultado>/presto/<data_hora>/.

Ainda não baixa os autos: as capturas mostram onde fica o link do processo e dos documentos,
para o passo seguinte. Nunca aperta nada além de "Pesquisar".
"""
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ONDE_PROCURAR = (AQUI / "saida", AQUI.parent / "saida" / "albi")
# consulta de processos de quem está logado (PJe 1.x); no TRT7, o detalhe do processo (PJe-JT)
CONSULTA = {
    "tjce1": "https://pje.tjce.jus.br/pje1grau/Processo/ConsultaProcesso/listView.seam",
    "tjce2": "https://pje.tjce.jus.br/pje2grau/Processo/ConsultaProcesso/listView.seam",
    "jfce": "https://pje.jfce.jus.br/pje/Processo/ConsultaProcesso/listView.seam",
    "trf5": "https://pje1g.trf5.jus.br/pje/Processo/ConsultaProcesso/listView.seam",
    "trf5-2": "https://pje2g.trf5.jus.br/pje/Processo/ConsultaProcesso/listView.seam",
    "trt7": "https://pje.trt7.jus.br/consultaprocessual/detalhe-processo/{numero}/1",
    "trt7-2": "https://pje.trt7.jus.br/consultaprocessual/detalhe-processo/{numero}/2",
}
NOMES = {"tjce1": "TJCE 1º grau", "tjce2": "TJCE 2º grau", "trt7": "TRT7 1º grau", "trt7-2": "TRT7 2º grau",
         "jfce": "JFCE", "trf5": "TRF5 1º grau", "trf5-2": "TRF5 2º grau"}
RAMO = {"1": "STF", "2": "CNJ", "3": "STJ", "4": "Federal", "5": "Trabalho", "6": "Eleitoral", "7": "Militar União",
        "8": "Estadual", "9": "Militar Estadual"}
ESPERA_RESULTADO = 30  # segundos esperando a lista de resultados da consulta


def digitos(v):
    return re.sub(r"\D", "", v or "")


def cnj(numero):
    d = digitos(numero)
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}" if len(d) == 20 else (numero or "").strip()


def segundo_grau(instancia):
    i = (instancia or "").strip().lower()
    return bool(re.match(r"2", i) or re.search(r"\b2\s*[ºªo°]|segund|recurs|turma", i))


def tribunal(numero, instancia=""):
    """(chave do Presto ou None, descrição) pelo número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO)."""
    d = digitos(numero)
    if len(d) != 20:
        return None, "número fora do padrão CNJ"
    j, tr, org = d[13], d[14:16], d[16:]
    dois = segundo_grau(instancia) or org == "0000"
    if j == "8" and tr == "06":
        return ("tjce2" if dois else "tjce1"), ""
    if j == "5" and tr == "07":
        return ("trt7-2" if dois else "trt7"), ""
    if j == "4" and tr == "05":
        if dois:
            return "trf5-2", ""
        return ("jfce" if org.startswith("81") else "trf5"), ""
    return None, f"Justiça {RAMO.get(j, j)}, tribunal {tr} (J.TR {j}.{tr}): sem login no Presto aqui ainda"


# ---------------- qual relatório ----------------
def ultimo_relatorio():
    achados = [c for base in ONDE_PROCURAR if base.is_dir() for c in base.glob("*/processos.csv")]
    return max(achados, key=lambda c: c.stat().st_mtime).parent if achados else None


def ler_processos(pasta):
    """Processos do processos.csv (um por número; as pessoas do mesmo processo ficam juntas)."""
    arq = Path(pasta) / "processos.csv"
    if not arq.exists():
        raise SystemExit(f"Não achei {arq}. Gere o relatório antes (botão \"Gerar relatório\" ou relatorio.py).")
    por_numero = {}
    with open(arq, encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            num = cnj(linha.get("Processo", ""))
            if not num:
                continue
            p = por_numero.setdefault(num, {"numero": num, "instancia": linha.get("Instância", ""),
                                            "tribunal_sonar": linha.get("Tribunal", ""), "pessoas": [],
                                            "empresas": [], "situacao": linha.get("Situação", "")})
            nome, emp = (linha.get("Nome") or "").strip(), (linha.get("Empresa") or "").strip()
            if nome and nome not in p["pessoas"]:
                p["pessoas"].append(nome)
            if emp and emp not in p["empresas"]:
                p["empresas"].append(emp)
    for p in por_numero.values():
        p["chave"], p["motivo"] = tribunal(p["numero"], p["instancia"])
    return list(por_numero.values())


def dividir(processos):
    """{chave: [processos]} na ordem do TRIBUNAIS do presto.py, e a lista dos que ficam de fora."""
    grupos = {}
    for p in processos:
        if p["chave"]:
            grupos.setdefault(p["chave"], []).append(p)
    ordem = list(CONSULTA)
    return dict(sorted(grupos.items(), key=lambda kv: ordem.index(kv[0]))), [p for p in processos if not p["chave"]]


# ---------------- JavaScript da consulta ----------------
# preenche o número na tela "Consultar processos" do PJe (campo único com máscara ou os campos
# separados: sequencial, dígito, ano, ramo, tribunal, órgão) e clica em Pesquisar
JS_CONSULTAR = r"""(function(numero){
  var d = numero.replace(/\D/g, '');
  if (d.length !== 20) return JSON.stringify({ok: false, erro: 'número sem 20 dígitos'});
  var p = {seq: d.slice(0, 7), dv: d.slice(7, 9), ano: d.slice(9, 13), j: d.slice(13, 14), tr: d.slice(14, 16), org: d.slice(16)};
  var fmt = p.seq + '-' + p.dv + '.' + p.ano + '.' + p.j + '.' + p.tr + '.' + p.org;
  function docs(raiz, out) {
    out.push(raiz);
    [].forEach.call(raiz.querySelectorAll('iframe,frame'), function(f) { try { if (f.contentDocument) docs(f.contentDocument, out); } catch (e) {} });
    return out;
  }
  function vis(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }
  function por(el, v) {
    var setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    el.focus(); setter.call(el, v);
    ['input', 'keyup', 'change', 'blur'].forEach(function(n) { el.dispatchEvent(new Event(n, {bubbles: true})); });
  }
  var todos = [];
  docs(document, []).forEach(function(doc) {
    [].forEach.call(doc.querySelectorAll('input'), function(i) {
      if (vis(i) && /^(text|tel|number|search|)$/i.test(i.type || '')) todos.push(i);
    });
  });
  var doNum = todos.filter(function(i) { return /num(ero)?_?processo|processoreferencia|numproc/i.test((i.id || '') + ' ' + (i.name || '')); });
  var campos = [];
  var partes = [['seq', /sequencial/i], ['dv', /digito|verificador/i], ['j', /ramo/i], ['tr', /respectivo|tribunal/i],
                ['org', /orgao|origem/i], ['ano', /ano/i]];
  var usados = [];
  partes.forEach(function(par) {
    var c = doNum.filter(function(i) { return usados.indexOf(i) < 0 && par[1].test((i.id || '') + ' ' + (i.name || '')); })[0];
    if (!c) return;
    usados.push(c);
    if (c.readOnly || c.disabled) { campos.push(par[0] + '(fixo)'); return; }
    por(c, p[par[0]]); campos.push(par[0]);
  });
  if (campos.indexOf('seq') < 0) {
    var unico = doNum[0] || todos.filter(function(i) { return /\d{7}-\d{2}|N{7}|0{7}-/i.test(i.placeholder || ''); })[0];
    if (!unico) return JSON.stringify({ok: false, erro: 'não achei o campo do número do processo', campos_vistos: todos.length});
    por(unico, fmt); campos = ['único:' + (unico.id || unico.name)];
  }
  var botoes = [];
  docs(document, []).forEach(function(doc) {
    [].forEach.call(doc.querySelectorAll('input[type=submit],input[type=button],button,a'), function(b) {
      var t = ((b.innerText || b.value || '') + ' ' + (b.id || '') + ' ' + (b.title || '')).trim();
      if (vis(b) && /pesquisar|searchprocesso|buscar|consultar/i.test(t) && !/limpar|avan[cç]ad/i.test(t)) botoes.push([b, t]);
    });
  });
  if (!botoes.length) return JSON.stringify({ok: false, erro: 'não achei o botão Pesquisar', campos: campos});
  // o menu do PJe também tem "Pesquisar": primeiro o botão do formulário (id searchProcessos), depois botões, links por último
  function nota(b) { return (/search|pesquisar/i.test(b[0].id || '') ? 0 : 2) + (b[0].tagName === 'A' ? 1 : 0); }
  botoes.sort(function(a, b) { return nota(a) - nota(b); });
  botoes[0][0].click();
  return JSON.stringify({ok: true, campos: campos, botao: botoes[0][1].slice(0, 60)});
})"""

# o que a página mostra do processo: se o número aparece, os links dele, "nenhum resultado", captcha
JS_RESULTADO = r"""(function(numero){
  var d = numero.replace(/\D/g, '');
  var fmt = d.slice(0, 7) + '-' + d.slice(7, 9) + '.' + d.slice(9, 13) + '.' + d.slice(13, 14) + '.' + d.slice(14, 16) + '.' + d.slice(16);
  var texto = '', links = [], captcha = false;
  function anda(doc) {
    texto += '\n' + (doc.body ? doc.body.innerText : '');
    if (doc.querySelector('iframe[src*="captcha"], .g-recaptcha, [class*="captcha"], img[src*="captcha"]')) captcha = true;
    [].forEach.call(doc.querySelectorAll('a, [onclick]'), function(a) {
      var t = (a.innerText || a.title || '').trim();
      if (t.indexOf(fmt) >= 0 || t.indexOf(d.slice(0, 7) + '-') >= 0)
        links.push({texto: t.slice(0, 120), href: (a.getAttribute('href') || '').slice(0, 300),
                    onclick: (a.getAttribute('onclick') || '').slice(0, 400), title: a.title || '', id: a.id || ''});
    });
    [].forEach.call(doc.querySelectorAll('iframe,frame'), function(f) { try { if (f.contentDocument) anda(f.contentDocument); } catch (e) {} });
  }
  anda(document);
  var achou = texto.indexOf(fmt) >= 0 || texto.replace(/\D/g, ' ').indexOf(d) >= 0;
  var vazio = /nenhum (registro|processo|resultado)|n[aã]o (foram )?encontrad|sem resultado|0 resultados/i.test(texto);
  if (/captcha|n[aã]o sou um rob[oô]/i.test(texto)) captcha = true;
  var i = texto.indexOf(fmt);
  return JSON.stringify({achou: achou, vazio: vazio && !achou, captcha: captcha, links: links.slice(0, 10),
                         trecho: (i >= 0 ? texto.slice(Math.max(0, i - 200), i + 800) : texto.slice(0, 600)).trim()});
})"""


# ---------------- no Chrome aberto ----------------
def _nome_arquivo(i, numero):
    return f"{i:02d}_{digitos(numero)}"


def consultar(CM, w, t, chave, proc, destino, cfg):
    """Procura um processo na aba (já logada). Devolve o registro do resumo."""
    import presto
    url = CONSULTA[chave]
    reg = {"numero": proc["numero"], "tribunal": NOMES[chave], "pessoas": proc["pessoas"], "empresas": proc["empresas"]}
    alvo = url.format(numero=proc["numero"]) if "{numero}" in url else url
    CM.ir(w, t, alvo)
    CM.esperar(w, t, maximo=45, folga=3)
    if not presto.logado(w, t):  # a sessão caiu ou o tribunal mandou para o login: entra de novo uma vez
        print("  a consulta mandou para o login; entrando de novo pelo Presto...")
        if not presto.login(w, t, cfg, destino, prefixo=f"{chave}_relogin_"):
            reg.update(resultado="não entrou", detalhe="a sessão caiu e o login de novo não deu certo")
            return reg
        CM.ir(w, t, alvo)
        CM.esperar(w, t, maximo=45, folga=3)
    if "{numero}" not in url:
        r = json.loads(CM.js(w, t, f"{JS_CONSULTAR}({json.dumps(proc['numero'])})"))
        reg["consulta"] = r
        if not r.get("ok"):
            reg.update(resultado="sem formulário", detalhe=r.get("erro", ""))
            return reg
        time.sleep(4)  # a lista do PJe vem por AJAX; antes disso a tela pode mostrar "0 resultados"
    def pronto():
        v = json.loads(CM.js(w, t, f"{JS_RESULTADO}({json.dumps(proc['numero'])})"))
        return v if (v["achou"] or v["vazio"] or v["captcha"]) else None
    v = presto._esperar(pronto, ESPERA_RESULTADO, passo=2) or json.loads(
        CM.js(w, t, f"{JS_RESULTADO}({json.dumps(proc['numero'])})"))
    reg["pagina"] = v
    reg["resultado"] = ("achou" if v["achou"] else "captcha" if v["captcha"] else
                        "não encontrado" if v["vazio"] else "sem resposta")
    reg["links"] = v["links"]
    return reg


def rodar(pasta, processos, so=None, maximo=None):
    import chrome_mac as CM
    import presto
    if not CM.disponivel():
        print("O comando 'processos' só funciona no Mac (usa o AppleScript do Chrome). "
              "Aqui dá para usar --conferir.")
        return 2
    cfg = presto.config_presto()
    grupos, fora = dividir(processos)
    if so:
        grupos = {k: v for k, v in grupos.items() if k == so}
    destino = Path(pasta) / "presto" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino.mkdir(parents=True, exist_ok=True)
    resumo = [{"numero": p["numero"], "tribunal": "", "pessoas": p["pessoas"], "empresas": p["empresas"],
               "resultado": "fora", "detalhe": p["motivo"]} for p in fora] if not so else []
    contador = 0
    try:
        for chave, procs in grupos.items():
            if maximo is not None and contador >= maximo:
                break
            print(f"\n== {NOMES[chave]}: {len(procs)} processo(s) ==")
            w, t = CM.abrir_aba(presto.TRIBUNAIS[chave])
            pasta_trib = destino / chave
            pasta_trib.mkdir(exist_ok=True)
            if not presto.login(w, t, cfg, pasta_trib, prefixo="login_"):
                for p in procs:
                    resumo.append({"numero": p["numero"], "tribunal": NOMES[chave], "pessoas": p["pessoas"],
                                   "empresas": p["empresas"], "resultado": "não entrou",
                                   "detalhe": "login pelo Presto não deu certo (veja login_*)"})
                continue
            for p in procs:
                if maximo is not None and contador >= maximo:
                    break
                contador += 1
                nome = _nome_arquivo(contador, p["numero"])
                try:
                    reg = consultar(CM, w, t, chave, p, pasta_trib, cfg)
                except CM.ChromeMacErro as e:
                    reg = {"numero": p["numero"], "tribunal": NOMES[chave], "pessoas": p["pessoas"],
                           "empresas": p["empresas"], "resultado": "erro", "detalhe": str(e)}
                try:
                    presto._salvar_captura(pasta_trib, nome, CM.capturar(w, t))
                    reg["captura"] = str((pasta_trib / nome).relative_to(destino))
                except CM.ChromeMacErro:
                    pass
                resumo.append(reg)
                print(f"  {p['numero']}: {reg['resultado']}"
                      + (f" ({reg.get('detalhe')})" if reg.get("detalhe") else "")
                      + (f" · {len(reg.get('links', []))} link(s) do processo" if reg.get("links") else ""))
                _escrever_resumo(destino, resumo)
    except CM.ChromeMacErro as e:
        print("Parou:", e)
        _escrever_resumo(destino, resumo)
        return 1
    _escrever_resumo(destino, resumo)
    contagem = {}
    for r in resumo:
        contagem[r["resultado"]] = contagem.get(r["resultado"], 0) + 1
    print("\nResumo:", ", ".join(f"{k}: {v}" for k, v in contagem.items()))
    print("Capturas e resumo em", destino)
    return 0


def _escrever_resumo(destino, resumo):
    (destino / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    linhas = ["processo ; tribunal ; resultado ; pessoas ; detalhe"]
    for r in resumo:
        linhas.append(" ; ".join([r["numero"], r.get("tribunal", ""), r["resultado"], ", ".join(r.get("pessoas", [])),
                                  r.get("detalhe", "") or (r.get("links") or [{}])[0].get("texto", "")]))
    (destino / "resumo.txt").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def conferir(pasta, processos):
    grupos, fora = dividir(processos)
    print(f"Relatório: {pasta}")
    print(f"{len(processos)} processo(s) diferente(s); {sum(len(v) for v in grupos.values())} com login no Presto, "
          f"{len(fora)} fora.")
    for chave, procs in grupos.items():
        print(f"\n{NOMES[chave]} ({len(procs)}):")
        for p in procs:
            print(f"  {p['numero']}  {', '.join(p['pessoas'])}  [{p['tribunal_sonar'] or '-'}]")
    if fora:
        print(f"\nFora ({len(fora)}):")
        for p in fora:
            print(f"  {p['numero']}  {', '.join(p['pessoas'])}  [{p['tribunal_sonar'] or '-'}]  {p['motivo']}")


def main(*args):
    args = list(args)
    so = maximo = None
    so_conferir = "--conferir" in args
    args = [a for a in args if a != "--conferir"]
    if "--tribunal" in args:
        i = args.index("--tribunal")
        so = (args[i + 1:i + 2] or [""])[0].lower()
        del args[i:i + 2]
        if so not in CONSULTA:
            print(f"Tribunal desconhecido: {so}. Use {', '.join(CONSULTA)}.")
            return 2
    if "--max" in args:
        i = args.index("--max")
        try:
            maximo = int(args[i + 1])
        except (IndexError, ValueError):
            print("--max precisa de um número")
            return 2
        del args[i:i + 2]
    pasta = Path(args[0]) if args else ultimo_relatorio()
    if not pasta:
        print("Não achei nenhum relatório do Albi (processos.csv) em " + " nem em ".join(map(str, ONDE_PROCURAR)))
        return 2
    processos = ler_processos(pasta)
    if not processos:
        print(f"O relatório {pasta} não tem processos.")
        return 0
    if so_conferir:
        conferir(pasta, processos)
        return 0
    print(f"Relatório: {pasta} ({len(processos)} processo(s)). Deixe na frente a janela do Chrome do escritório.")
    return rodar(pasta, processos, so, maximo)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
