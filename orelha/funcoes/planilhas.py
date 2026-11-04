"""Conferência das planilhas do Albi: quais processos o VIOS já tem e quais são novos.

O que faz (ORELHA_SPEC, função 5):
  - acha os processos.csv que o Albi escreve (albi/relatorio.py, escrever_csv: separador ";",
    UTF-8 com BOM, uma linha por processo, colunas "Empresa", "Nome", ..., "Processo" (o "Número
    único" do Sonar já formatado como CNJ), "Tribunal", ..., "Situação", "Link") nas pastas de
    resultado do Albi: <albi/saida>/<AAAA-MM-DD_HHMMSS>/processos.csv (padrão ../albi/saida,
    ORELHA_ALBI_SAIDA ou --albi-saida; a própria pasta também vale, se tiver um processos.csv);
  - só confere as que ainda não foram conferidas: registro em historico/planilhas-conferidas.json
    (pasta -> sha256 do processos.csv; se o Albi reescrever o arquivo, ele é conferido de novo).
    Pasta cujo processos.csv é mais antigo que ORELHA_PLANILHAS_DIAS dias (padrão 30; 0 = todas)
    fica de fora, para a primeira execução não conferir o histórico inteiro do Albi;
  - para cada número (normalizado: só dígitos, 20 dígitos do CNJ) procura no VIOS:
      "ja_tem"    o VIOS já tem o processo         -> Item "info", com link da ficha se achou;
      "novo"      a busca não achou o processo     -> Item "atencao";
      "nao_achou" não deu para conferir (número fora do padrão CNJ ou a busca falhou) -> "atencao".
    Grupo = empresa. Também grava saida/<data>/planilhas-<data>.csv (processo, empresa,
    resultado, pasta) e emite um evento "planilha" por processo (só resultado/índice/total);
  - a pasta só entra no registro se todos os processos dela foram conferidos (falha de busca =
    confere de novo na próxima execução). No --simulado o registro não é lido nem gravado.
    Busca em que o bloqueio barrou algum pedido, ou em que ORELHA_PLANILHAS_BUSCA_PRONTO/RESULTADO
    não apareceu, é falha ("nao_achou"), nunca "novo". Se ORELHA_PLANILHAS_SUSPEITO (padrão 10) ou
    mais buscas deram certo e nenhuma achou o processo, o resultado é suspeito: aviso na seção e
    nenhuma pasta entra no registro.

Duas formas de procurar no VIOS (ORELHA_PLANILHAS_MODO):
  - "busca" (padrão): a busca do topo do VIOS, com a opção "Nro do Processo", um número por vez.
    NÃO MAPEADA na tela real: os seletores abaixo são palpites e ficam todos no .env. Se a busca
    abre por endereço (GET), basta ORELHA_PLANILHAS_BUSCA_URL com {numero} ou {digitos}.
  - "lista": uma pesquisa só na lista de processos (processos-lista.php, campos mapeados em
    doc/vios-mapa-processos.md da branch developer: pesq[limit]=9999999 e
    pesq[filtros_multi][]=todos) e compara com a coluna do número (nro_proc_html) de todas as
    linhas. Mais pesada numa pesquisa só, mas não depende da busca do topo.

Só lê: a busca é enviada por nucleo.vios.enviar_pesquisa (o único formulário que o bloqueio de
envios deixa passar) ou aberta por endereço com nucleo.vios.abrir; nenhum botão é clicado.

Leitura (Selenium, fina): buscar_numero, ler_lista_vios. Interpretação (pura, testada com
orelha/fixtures/planilhas/): ler_csv_albi, csvs_do_albi, pendentes, normalizar_numero,
numeros_no_html, conferir, montar_secao, escrever_csv_do_dia, registrar.
"""
import csv
import hashlib
import io
import logging
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlparse

from nucleo import simulado, vios
from nucleo.modelos import Item, Secao

log = logging.getLogger("orelha")

CHAVE = "planilhas"
TITULO = "Conferência das planilhas do Albi"
REGISTRO = "planilhas-conferidas.json"
NOME_CSV = "processos.csv"
FIXTURE_ALBI = "albi"                    # orelha/fixtures/planilhas/albi/<pasta>/processos.csv
FIXTURE_VIOS = "vios_processos.html"     # o "VIOS" do simulado: uma lista de processos fictícia

# --- padrões (todos sobrescrevíveis no orelha/.env) ---
MODO = "url"   # padrão desde 04/11/2026: a busca do topo pelo endereço (formulário GET), sem abrir telas
MAXIMO = 300
DIAS = 30
# com pelo menos tantas buscas e NENHUM processo achado no VIOS, o resultado é suspeito (a busca
# provavelmente não filtrou nada): as pastas não entram no registro e voltam na próxima execução
SUSPEITO = 10
FICHA = "?pag=sys/processos/processos-vis.php&processos_id={id}"
# busca do topo (não mapeada: conferir na tela real)
BUSCA_PAGINA = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
BUSCA_CAMPO = "css:input[name*='busca' i], input[id*='busca' i]"
BUSCA_OPCAO = "Nro do Processo"
# lista de processos (mapeada em 03/11/2026)
LISTA_URL = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
LISTA_CAMPO = "css:[name='pesq[limit]']"
LISTA_LINHAS = "css:tr[id^='processos-lista_linha_']"
LISTA_FILTRO = "todos"

RESULTADOS = ("ja_tem", "novo", "nao_achou")
NIVEL = {"ja_tem": "info", "novo": "atencao", "nao_achou": "atencao"}
TEXTO = {"ja_tem": "Já está no VIOS", "novo": "Novo: não achei no VIOS",
         "nao_achou": "Não deu para conferir"}
ORDEM = {"novo": 0, "nao_achou": 1, "ja_tem": 2}

# número CNJ com ou sem pontuação, sem pegar pedaço de um número maior
NUMERO = re.compile(r"(?<!\d)\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}(?!\d)")
PASTA_DATA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:_(\d{2})(\d{2}))?")


# ---------------------------------------------------------------- números (puras)
def normalizar_numero(texto):
    """Só os dígitos, se forem os 20 do CNJ; "" se não for um número CNJ."""
    d = vios.digitos(texto)
    return d if len(d) == 20 else ""


def formatar_cnj(digitos):
    """20 dígitos -> 0000000-00.0000.0.00.0000 (outro texto volta como veio)."""
    d = vios.digitos(digitos)
    if len(d) != 20:
        return digitos or ""
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"


# ---------------------------------------------------------------- CSV do Albi (puras)
def _celula_albi(v):
    """Desfaz a proteção do Albi contra fórmula no Excel ("'" antes de = + - @)."""
    v = (v or "").strip()
    return v[1:] if v[:1] == "'" and v[1:2] in ("=", "+", "-", "@") else v


def _indice(cabecalho, *nomes):
    alvo = [vios.normalizar(n) for n in nomes]
    cab = [vios.normalizar(c) for c in cabecalho]
    for n in alvo:
        if n in cab:
            return cab.index(n)
    return None


def ler_csv_albi(texto):
    """Texto do processos.csv do Albi -> [{numero, digitos, empresa, nome, tribunal, situacao}].

    Aceita BOM, separador ";" (o do Albi) ou "," e a coluna do número com o nome "Processo"
    (Albi) ou "Número único" (planilha do Sonar). Linha sem número fica de fora."""
    texto = (texto or "").lstrip("﻿")
    if not texto.strip():
        return []
    primeira = texto.splitlines()[0]
    sep = ";" if primeira.count(";") >= primeira.count(",") else ","
    leitor = csv.reader(io.StringIO(texto), delimiter=sep)
    cabecalho = next(leitor, [])
    col = {"numero": _indice(cabecalho, "Processo", "Número único", "Numero", "Número do processo"),
           "empresa": _indice(cabecalho, "Empresa"), "nome": _indice(cabecalho, "Nome"),
           "tribunal": _indice(cabecalho, "Tribunal"), "situacao": _indice(cabecalho, "Situação")}
    if col["numero"] is None:
        raise ValueError("processos.csv sem a coluna do número do processo (\"Processo\")")
    linhas = []
    for celulas in leitor:
        def campo(nome):
            i = col[nome]
            return _celula_albi(celulas[i]) if i is not None and i < len(celulas) else ""
        numero = campo("numero")
        if not numero:
            continue
        linhas.append({"numero": numero, "digitos": normalizar_numero(numero), "empresa": campo("empresa"),
                       "nome": campo("nome"), "tribunal": campo("tribunal"), "situacao": campo("situacao")})
    return linhas


def csvs_do_albi(raiz):
    """processos.csv das pastas de resultado do Albi (e da própria raiz), em ordem de pasta."""
    raiz = Path(raiz) if raiz else None
    if not raiz or not raiz.is_dir():
        return []
    achados = [raiz / NOME_CSV] if (raiz / NOME_CSV).is_file() else []
    achados += sorted(p for p in raiz.glob(f"*/{NOME_CSV}") if p.is_file())
    return achados


def assinatura(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def chave_pasta(caminho_csv):
    return str(Path(caminho_csv).parent.resolve())


def pendentes(csvs, registro, hoje=None, dias=0):
    """[(caminho, sha256)] dos processos.csv ainda não conferidos (ou reescritos depois da
    conferência). Com dias > 0, os modificados antes de hoje - dias ficam de fora."""
    conferidas = (registro or {}).get("pastas", {}) if isinstance(registro, dict) else {}
    limite = hoje - timedelta(days=dias) if (hoje and dias and dias > 0) else None
    saida = []
    for c in csvs:
        if limite and datetime.fromtimestamp(Path(c).stat().st_mtime).date() < limite:
            continue
        sha = assinatura(c)
        anterior = conferidas.get(chave_pasta(c))
        if isinstance(anterior, dict) and anterior.get("sha256") == sha:
            continue
        saida.append((Path(c), sha))
    return saida


def rotulo_pasta(nome):
    """'2026-11-03_101500' -> '03/11/2026 10:15' (outro nome volta como veio)."""
    m = PASTA_DATA.match(nome or "")
    if not m:
        return nome
    ano, mes, dia, h, mi = m.groups()
    return f"{dia}/{mes}/{ano}" + (f" {h}:{mi}" if h else "")


# ---------------------------------------------------------------- HTML do VIOS (puras)
class _LeitorNumeros(HTMLParser):
    """Números CNJ do texto da página, cada um com o CI (processos_id) da linha <tr> em que está:
    data-processos_id do <tr> ou processos_id= de um link da linha. Texto de script, style,
    option e textarea não conta (o campo da busca não "acha" o número que o Orelha digitou)."""
    IGNORAR = {"script", "style", "option", "textarea", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.linhas = []        # pilha de <tr> abertos: {"id", "texto": []}
        self.fora = []          # texto fora de <tr>
        self.ignorando = 0
        self.achados = []       # [(digitos, id)]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.IGNORAR:
            self.ignorando += 1
        elif tag == "tr":
            self.linhas.append({"id": (a.get("data-processos_id") or "").strip(), "texto": []})
        elif tag == "a" and self.linhas and not self.linhas[-1]["id"]:
            ids = parse_qs(urlparse(a.get("href") or "").query).get("processos_id", [])
            if ids and ids[0].isdigit():
                self.linhas[-1]["id"] = ids[0]

    def handle_endtag(self, tag):
        if tag in self.IGNORAR:
            self.ignorando = max(0, self.ignorando - 1)
        elif tag == "tr" and self.linhas:
            linha = self.linhas.pop()
            self._achar(" ".join(linha["texto"]), linha["id"])

    def handle_data(self, dados):
        if not self.ignorando:
            (self.linhas[-1]["texto"] if self.linhas else self.fora).append(dados)

    def _achar(self, texto, ident):
        for m in NUMERO.finditer(texto):
            self.achados.append((vios.digitos(m.group(0)), ident))

    def fechar(self):
        self.close()
        while self.linhas:  # <tr> sem fechamento
            linha = self.linhas.pop()
            self._achar(" ".join(linha["texto"]), linha["id"])
        self._achar(" ".join(self.fora), "")
        return self.achados


def numeros_no_html(html, base="", url_pagina=""):
    """{digitos: link da ficha no VIOS ("" se não deu para saber)} de todos os números CNJ do HTML.
    Número fora de linha de tabela (ex.: o cabeçalho da ficha) usa o processos_id de url_pagina."""
    leitor = _LeitorNumeros()
    leitor.feed(html or "")
    da_pagina = (parse_qs(urlparse(url_pagina or "").query).get("processos_id") or [""])[0]
    achados = {}
    for d, ident in leitor.fechar():
        ident = ident or (da_pagina if da_pagina.isdigit() else "")
        link = urljoin(base, FICHA.format(id=ident)) if (ident and base) else ""
        if d not in achados or (link and not achados[d]):
            achados[d] = link
    return achados


# ---------------------------------------------------------------- conferência (puras)
def conferir(linhas, encontrados, falhas=None):
    """Junta as linhas dos CSVs (com "pasta") com o que o VIOS mostrou.

    encontrados: {digitos: link} dos números que o VIOS tem; falhas: {digitos: motivo} dos que não
    deu para procurar (os que não estão em nenhum dos dois são "novo"). Uma linha por empresa +
    número (o mesmo processo de duas pessoas da mesma empresa vira um só, com os dois nomes)."""
    falhas = falhas or {}
    juntos, ordem = {}, []
    for ln in linhas:
        chave = (vios.normalizar(ln.get("empresa")), ln["digitos"] or vios.normalizar(ln["numero"]))
        if chave not in juntos:
            juntos[chave] = {"numero": ln["numero"], "digitos": ln["digitos"], "empresa": ln.get("empresa", ""),
                             "nomes": [], "tribunal": ln.get("tribunal", ""), "situacao": ln.get("situacao", ""),
                             "pastas": []}
            ordem.append(chave)
        j = juntos[chave]
        for campo, valor in (("nomes", ln.get("nome")), ("pastas", ln.get("pasta"))):
            if valor and valor not in j[campo]:
                j[campo].append(valor)
    saida = []
    for chave in ordem:
        j = juntos[chave]
        d = j["digitos"]
        if not d:
            j.update(resultado="nao_achou", motivo="número fora do padrão CNJ no CSV do Albi", link="")
        elif d in falhas:
            j.update(resultado="nao_achou", motivo=falhas[d], link="")
        elif d in encontrados:
            j.update(resultado="ja_tem", motivo="", link=encontrados[d] or "")
        else:
            j.update(resultado="novo", motivo="", link="")
        saida.append(j)
    return saida


def _qtd(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def contagens(conferidos, n_pastas):
    c = {r: sum(1 for x in conferidos if x["resultado"] == r) for r in RESULTADOS}
    return {"pastas": n_pastas, "total": len(conferidos), "ja_tem": c["ja_tem"], "novos": c["novo"],
            "nao_achou": c["nao_achou"]}


def montar_secao(conferidos, n_pastas, avisos=()):
    """Secao da função: itens por empresa (empresas em ordem alfabética; dentro, novos primeiro)."""
    numeros = contagens(conferidos, n_pastas)
    if not n_pastas:
        return Secao(chave=CHAVE, titulo=TITULO, resumo="Nenhuma planilha nova do Albi.", itens=[],
                     numeros=numeros, avisos=list(avisos))
    ordenados = sorted(conferidos, key=lambda x: (vios.normalizar(x["empresa"]) or "~", ORDEM[x["resultado"]],
                                                  x["digitos"] or x["numero"]))
    itens = []
    for x in ordenados:
        partes = [TEXTO[x["resultado"]] + (f" ({x['motivo']})" if x["motivo"] else "")]
        if x["nomes"]:
            partes.append("parte: " + ", ".join(x["nomes"]))
        partes += [v for v in (x["tribunal"], x["situacao"]) if v]
        if x["pastas"]:
            partes.append("planilha do Albi de " + ", ".join(rotulo_pasta(p) for p in x["pastas"]))
        itens.append(Item(titulo=formatar_cnj(x["digitos"]) if x["digitos"] else x["numero"],
                          detalhe=" · ".join(partes), nivel=NIVEL[x["resultado"]],
                          link=x["link"], grupo=x["empresa"] or "(sem empresa)"))
    frase = (f"{_qtd(n_pastas, 'planilha nova', 'planilhas novas')} do Albi, "
             f"{_qtd(numeros['total'], 'processo', 'processos')}: "
             f"{_qtd(numeros['novos'], 'novo', 'novos')} (fora do VIOS), {numeros['ja_tem']} já no VIOS")
    if numeros["nao_achou"]:
        frase += f", {numeros['nao_achou']} sem conferir"
    return Secao(chave=CHAVE, titulo=TITULO, resumo=frase + ".", itens=itens, numeros=numeros,
                 avisos=list(avisos))


def _celula(v):
    v = str(v or "")
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v  # não vira fórmula no Excel


def escrever_csv_do_dia(caminho, conferidos):
    """planilhas-<data>.csv no padrão do Albi (";" e BOM, para o Excel abrir com acento)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Processo", "Empresa", "Resultado", "Explicação", "Pasta do Albi"])
        for x in conferidos:
            explicacao = TEXTO[x["resultado"]] + (f" ({x['motivo']})" if x["motivo"] else "")
            w.writerow([_celula(v) for v in (formatar_cnj(x["digitos"]) if x["digitos"] else x["numero"],
                                             x["empresa"], x["resultado"], explicacao, ", ".join(x["pastas"]))])
    return caminho


def registrar(registro, pendentes_csv, conferidos, hoje):
    """Novo registro com as pastas totalmente conferidas (sem falha de busca). Devolve
    (registro, [pastas que ficaram para a próxima])."""
    reg = dict(registro) if isinstance(registro, dict) else {}
    pastas = dict(reg.get("pastas") or {})
    por_pasta = {}
    for x in conferidos:
        for p in x["pastas"]:
            por_pasta.setdefault(p, []).append(x)
    adiadas = []
    for caminho, sha in pendentes_csv:
        nome = Path(caminho).parent.name
        xs = por_pasta.get(nome, [])
        # falha de busca é passageira: a pasta volta na próxima execução. Número fora do padrão
        # CNJ não melhora tentando de novo, então não segura a pasta.
        if any(x["resultado"] == "nao_achou" and x["digitos"] for x in xs):
            adiadas.append(nome)
            continue
        c = contagens(xs, 1)
        pastas[chave_pasta(caminho)] = {"sha256": sha, "conferida_em": hoje.isoformat(), "total": c["total"],
                                        "ja_tem": c["ja_tem"], "novos": c["novos"], "nao_achou": c["nao_achou"]}
    reg["pastas"] = pastas
    return reg, adiadas


# ---------------------------------------------------------------- leitura (Selenium, fina)
def _config(cfg):
    modo = (cfg.valor("ORELHA_PLANILHAS_MODO", MODO) or MODO).lower()
    if modo not in ("url", "busca", "lista"):
        from nucleo.config import ConfigErro
        raise ConfigErro("ORELHA_PLANILHAS_MODO: use busca ou lista")
    formato = (cfg.valor("ORELHA_PLANILHAS_BUSCA_FORMATO", "cnj") or "cnj").lower()
    if formato not in ("cnj", "digitos"):
        from nucleo.config import ConfigErro
        raise ConfigErro("ORELHA_PLANILHAS_BUSCA_FORMATO: use cnj ou digitos")
    return {
        "modo": modo,
        "maximo": cfg.valor("ORELHA_PLANILHAS_MAX", MAXIMO, int),
        "dias": cfg.valor("ORELHA_PLANILHAS_DIAS", DIAS, int),
        "suspeito": max(0, cfg.valor("ORELHA_PLANILHAS_SUSPEITO", SUSPEITO, int)),
        "busca_url": cfg.valor("ORELHA_PLANILHAS_BUSCA_URL", ""),
        "busca_pagina": cfg.valor("ORELHA_PLANILHAS_BUSCA_PAGINA", BUSCA_PAGINA),
        "busca_campo": cfg.valor("ORELHA_PLANILHAS_BUSCA_CAMPO", BUSCA_CAMPO, "seletor"),
        "busca_tipo": cfg.valor("ORELHA_PLANILHAS_BUSCA_TIPO", "", "seletor"),
        "busca_opcao": cfg.valor("ORELHA_PLANILHAS_BUSCA_OPCAO", BUSCA_OPCAO),
        "busca_formato": formato,
        "busca_recarrega": cfg.valor("ORELHA_PLANILHAS_BUSCA_RECARREGA", True, bool),
        "busca_xhr": cfg.valor("ORELHA_PLANILHAS_BUSCA_XHR", False, bool),
        "busca_pronto": cfg.valor("ORELHA_PLANILHAS_BUSCA_PRONTO", "", "seletor"),
        "busca_resultado": cfg.valor("ORELHA_PLANILHAS_BUSCA_RESULTADO", "", "seletor"),
        "lista_url": cfg.valor("ORELHA_PLANILHAS_LISTA_URL", LISTA_URL),
        "lista_campo": cfg.valor("ORELHA_PLANILHAS_LISTA_CAMPO", LISTA_CAMPO, "seletor"),
        "lista_filtro": cfg.valor("ORELHA_PLANILHAS_LISTA_FILTRO", LISTA_FILTRO),
        "lista_linhas": cfg.valor("ORELHA_PLANILHAS_LISTA_LINHAS", LISTA_LINHAS, "seletor"),
    }


# acha, no formulário do campo da busca, o <select> ou o rádio da opção "Nro do Processo"
_JS_OPCAO = """
const [campo, alvo, select] = arguments;
const norm = t => (t || '').normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toUpperCase()
                          .replace(/\\s+/g, ' ').trim();
const a = norm(alvo);
const nome = el => el.name || el.id || '';
const selects = select ? [select] : Array.from((campo.form || document).querySelectorAll('select'));
for (const s of selects) {
    for (const op of s.options || []) {
        if (norm(op.text).includes(a) || norm(op.value) === a) return {nome: nome(s), valor: op.value};
    }
}
const radios = Array.from((campo.form || document).querySelectorAll('input[type=radio]'));
for (const r of radios) {
    const rotulo = (r.labels && r.labels[0] ? r.labels[0].innerText : '') + ' ' + (r.title || '');
    if (norm(rotulo).includes(a) || norm(r.value) === a) return {nome: nome(r), valor: r.value};
}
return null;
"""


def _html_resultado(ctx, c):
    if not c["busca_resultado"]:
        return vios.html(ctx)
    elementos = vios.esperar_varios(ctx, c["busca_resultado"], timeout=min(5, ctx.cfg.timeout))
    if not elementos:
        # sem a área de resultado não dá para dizer "novo": melhor "não deu para conferir"
        raise vios.ViosErro("a área de resultado não apareceu (ver ORELHA_PLANILHAS_BUSCA_RESULTADO)")
    return "\n".join(el.get_attribute("outerHTML") or "" for el in elementos)


def _barrados(ctx):
    from nucleo.navegador import tentativas_barradas
    return tentativas_barradas(ctx.driver)


def _pesquisar(ctx, c, valor):
    """Faz a busca. Devolve quantas tentativas o bloqueio já tinha barrado na página antes de
    enviar (as de depois são desta busca)."""
    if c["busca_url"]:
        vios.abrir(ctx, c["busca_url"].format(numero=quote(valor, safe=""), digitos=vios.digitos(valor)))
        return 0  # a página aberta já é o resultado: tudo o que foi barrado nela conta
    vios.abrir(ctx, c["busca_pagina"])
    campo = vios.esperar(ctx, c["busca_campo"], visivel=False)
    nome = campo.get_attribute("name") or campo.get_attribute("id")
    if not nome:
        raise vios.ViosErro("o campo da busca não tem name nem id (ver ORELHA_PLANILHAS_BUSCA_CAMPO)")
    filtros = {nome: valor}
    if c["busca_opcao"]:
        select = vios.esperar(ctx, c["busca_tipo"], visivel=False) if c["busca_tipo"] else None
        opcao = ctx.driver.execute_script(_JS_OPCAO, campo, c["busca_opcao"], select)
        if not opcao or not opcao.get("nome"):
            raise vios.ViosErro(f"a busca não tem a opção '{c['busca_opcao']}' (ver ORELHA_PLANILHAS_BUSCA_TIPO/OPCAO)")
        filtros[opcao["nome"]] = opcao["valor"]
    # recarregando, a página do resultado é nova (o que ela barrar conta); por AJAX, só o que vier
    # depois do envio
    antes = 0 if c["busca_recarrega"] else len(_barrados(ctx))
    vios.enviar_pesquisa(ctx, c["busca_campo"], filtros, esperar_recarregar=c["busca_recarrega"])
    if not c["busca_recarrega"]:
        vios.esperar_ajax(ctx)
    return antes


def _resultado(ctx, c, valor):
    antes = _pesquisar(ctx, c, valor)
    if c["busca_pronto"]:
        vios.esperar(ctx, c["busca_pronto"], visivel=False)
    html = _html_resultado(ctx, c)
    barrados = _barrados(ctx)[antes:]
    if barrados:
        # o resultado pode ter vindo por um POST barrado: a página sem o número não quer dizer "novo"
        log.info("Planilhas: o bloqueio barrou na busca: %s", "; ".join(barrados[:5]))
        raise vios.ViosErro(f"o bloqueio de envios barrou {len(barrados)} pedido(s) na tela do resultado "
                            "(se a busca usa XHR, ver ORELHA_PLANILHAS_BUSCA_XHR)")
    return html


def buscar_numero(ctx, c, digitos):
    """Procura um número na busca do VIOS e devolve {digitos: link} do que a tela mostrou.
    Levanta ViosErro (o número vira "não deu para conferir") se o bloqueio barrou algum pedido na
    tela do resultado ou se ORELHA_PLANILHAS_BUSCA_PRONTO/RESULTADO não apareceram."""
    valor = formatar_cnj(digitos) if c["busca_formato"] == "cnj" else digitos
    if c["busca_xhr"]:
        from nucleo.navegador import pesquisa_liberada
        with pesquisa_liberada(ctx.driver):
            html = _resultado(ctx, c, valor)
    else:
        html = _resultado(ctx, c, valor)
    return numeros_no_html(html, ctx.cfg.vios_base, ctx.driver.current_url)


# A busca do topo é um formulário GET (visto ao vivo em 04/11/2026): pag, pesq[filtros][]=todos,
# campo_pesquisa_selecionado=nro_proc, pesq[busca]=<número>, Pesq=Pesquisar. Achou com e sem a máscara
# do CNJ; número inexistente = tabela sem linhas. Um mesmo número pode ter vários cadastros (vários
# clientes): basta um.
URL_BUSCA_NUMERO = ("?pag=sys/processos/processos-lista.php&menu_lateral=true&pesq[filtros][]=todos"
                    "&campo_pesquisa_selecionado=nro_proc&pesq[busca]={numero}&Pesq=Pesquisar")


def buscar_numero_url(ctx, digitos):
    """{digitos: link} do que a busca pelo endereço achou (vazio = não achou). Levanta ViosErro se a
    resposta não é a tela de Processos (sessão caída, erro do VIOS): aí o número vira "não deu
    para conferir", nunca "novo"."""
    html = vios.buscar_get(ctx, URL_BUSCA_NUMERO.format(numero=formatar_cnj(digitos)))
    titulo = re.search(r"<title>([^<]*)</title>", html, re.I)
    if not (titulo and "Processos" in titulo.group(1)):
        raise vios.ViosErro("a busca não devolveu a tela de Processos")
    return numeros_no_html(html, ctx.cfg.vios_base)


def ler_lista_vios(ctx, c):
    """Uma pesquisa na lista de processos (todos, sem limite) -> {digitos: link}."""
    vios.abrir(ctx, c["lista_url"])
    vios.enviar_pesquisa(ctx, c["lista_campo"], {"pesq[limit]": "9999999", "pesq[filtros_multi][]": c["lista_filtro"]})
    linhas = vios.esperar_varios(ctx, c["lista_linhas"])
    if not linhas:
        raise vios.ViosErro("a lista de processos voltou vazia (ver ORELHA_PLANILHAS_LISTA_LINHAS/FILTRO)")
    html = "<table>" + "\n".join(el.get_attribute("outerHTML") or "" for el in linhas) + "</table>"
    return numeros_no_html(html, ctx.cfg.vios_base)


# ---------------------------------------------------------------- função
def _raiz_albi(ctx):
    return ctx.pasta_fixtures / FIXTURE_ALBI if ctx.simulado else ctx.albi_saida


def _pendentes_ctx(ctx, dias=None):
    registro = {} if ctx.simulado else ctx.ler_historico(REGISTRO, {})
    if dias is None:
        dias = ctx.cfg.valor("ORELHA_PLANILHAS_DIAS", DIAS, int)
    return registro, pendentes(csvs_do_albi(_raiz_albi(ctx)), registro, ctx.hoje, 0 if ctx.simulado else dias)


def PRECISA_VIOS(ctx):
    """Só entra no VIOS se há planilha do Albi para conferir."""
    return bool(_pendentes_ctx(ctx)[1])


def executar(ctx):
    ctx.emitir("fase", fase="lendo_planilhas")
    c = _config(ctx.cfg)
    raiz = _raiz_albi(ctx)
    if not raiz or not Path(raiz).is_dir():
        return montar_secao([], 0, [f"Pasta do Albi não encontrada: {raiz}"])
    registro, pend = _pendentes_ctx(ctx, c["dias"])
    if not pend:
        return montar_secao([], 0)

    avisos, linhas, escolhidas, unicos = [], [], [], set()
    for caminho, sha in pend:
        try:
            lidas = ler_csv_albi(caminho.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, ValueError, csv.Error) as e:
            avisos.append(f"Não consegui ler {caminho.parent.name}/{NOME_CSV}: {str(e).splitlines()[0] if str(e) else e.__class__.__name__}")
            continue
        novos = {ln["digitos"] for ln in lidas if ln["digitos"]} - unicos
        if escolhidas and c["maximo"] > 0 and len(unicos) + len(novos) > c["maximo"]:
            avisos.append(f"Limite de {c['maximo']} processos por execução (ORELHA_PLANILHAS_MAX): "
                          f"{len(pend) - len(escolhidas)} planilha(s) ficaram para a próxima")
            break
        unicos |= novos
        escolhidas.append((caminho, sha))
        linhas += [dict(ln, pasta=caminho.parent.name) for ln in lidas]
    log.info("Planilhas do Albi: %d pasta(s) para conferir, %d processo(s)", len(escolhidas), len(unicos))

    ordem = sorted(unicos)
    encontrados, falhas = {}, {}
    if ordem and ctx.simulado:
        encontrados = numeros_no_html(simulado.ler(ctx, FIXTURE_VIOS), ctx.cfg.vios_base)
    elif ordem:
        if ctx.driver is None:
            raise vios.ViosErro("sem navegador aberto no VIOS para conferir as planilhas")
        if c["modo"] == "lista":
            encontrados = ler_lista_vios(ctx, c)
        else:
            if c["modo"] == "url":
                vios.abrir(ctx, BUSCA_PAGINA)  # a busca roda de dentro de uma página do VIOS (mesma sessão)
            for i, d in enumerate(ordem, 1):
                try:
                    achados = buscar_numero_url(ctx, d) if c["modo"] == "url" else buscar_numero(ctx, c, d)
                except (vios.BloqueioInativo, vios.AcessoProibido):
                    raise
                except vios.ViosErro as e:
                    falhas[d] = f"a busca falhou: {str(e).splitlines()[0]}"
                    log.warning("Planilhas: busca %d/%d falhou: %s", i, len(ordem), str(e).splitlines()[0])
                    continue
                if d in achados:
                    encontrados[d] = achados[d]
                if i % 25 == 0:
                    log.info("Planilhas: %d/%d processos procurados", i, len(ordem))

    suspeito = (not ctx.simulado and c["modo"] in ("url", "busca") and c["suspeito"] > 0 and not encontrados
                and len(ordem) - len(falhas) >= c["suspeito"])
    conferidos = conferir(linhas, encontrados, falhas)
    total = len(ordem) + sum(1 for x in conferidos if not x["digitos"])
    vistos, indice = set(), 0
    for x in conferidos:
        if x["digitos"]:
            if x["digitos"] in vistos:
                continue  # mesmo número em duas empresas: um evento só
            vistos.add(x["digitos"])
        indice += 1
        ctx.emitir("planilha", resultado=x["resultado"], indice=indice, total=total)

    escrever_csv_do_dia(Path(ctx.saida) / f"planilhas-{ctx.hoje.isoformat()}.csv", conferidos)
    if ctx.simulado:
        avisos.append("Simulado: planilhas de exemplo; o registro das planilhas conferidas não foi alterado.")
    elif suspeito:
        avisos.append(f"Nenhum dos {len(ordem) - len(falhas)} processos procurados foi achado no VIOS: resultado "
                      "suspeito (a busca pode não ter filtrado nada). Os \"novos\" desta seção podem estar errados; "
                      "as planilhas não foram marcadas como conferidas e voltam na próxima execução. Conferir "
                      "ORELHA_PLANILHAS_BUSCA_* na tela real (ORELHA_PLANILHAS_SUSPEITO=0 desliga este aviso).")
        log.warning("Planilhas: nenhum processo achado em %d buscas: registro não gravado", len(ordem) - len(falhas))
    else:
        novo_registro, adiadas = registrar(registro, escolhidas, conferidos, ctx.hoje)
        ctx.gravar_historico(REGISTRO, novo_registro)
        if adiadas:
            avisos.append(f"{len(adiadas)} planilha(s) com busca que falhou: serão conferidas de novo na próxima execução")
    if falhas and len(falhas) == len(ordem):
        avisos.append("Nenhuma busca deu certo: confira os seletores ORELHA_PLANILHAS_BUSCA_* na tela real")
    return montar_secao(conferidos, len(escolhidas), avisos)
