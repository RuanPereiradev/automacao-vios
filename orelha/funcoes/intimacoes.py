"""Intimações esquecidas: as que estão há dias sem tarefa lançada (fora as que o Ultron ainda vai tratar).

O que faz (ORELHA_SPEC, função 3):
  - pesquisa na tela "Pesquisa intimações" do VIOS (a mesma do Ultron:
    index.php?pag=sys/publicacoes/int-pesquisa.php) as intimações disponibilizadas nos últimos
    ORELHA_INTIMACOES_DIAS dias (padrão 15) com "Com Tarefa Lançada = Não";
  - deixa de fora ontem e hoje, que o Ultron ainda vai tratar. Na segunda, o Ultron trata sexta,
    sábado e domingo (regra periodo_pesquisa de bot/intimacoes.py, copiada aqui), então o Orelha
    para na quinta (ORELHA_INTIMACOES_SEGUIR_ULTRON=false = sempre só ontem e hoje);
  - cada intimação vira um Item (CI, processo, tribunal, data), "grave" se foi disponibilizada há
    mais de ORELHA_INTIMACOES_GRAVE_DIAS dias (padrão 5) e "atencao" se não; grupo = data.

Só lê: a pesquisa é enviada por nucleo.vios.enviar_pesquisa (o único formulário que o bloqueio
de envios deixa passar), nenhum botão é clicado e a tela de lançamento (int-lanca.php) nunca é
aberta. O link "Lançar Intimação" de cada linha é ignorado; o link do item é o da ficha do
processo, quando a linha tem.

Leitura (Selenium, fina): ler_vios. Interpretação (pura, testada com
orelha/fixtures/intimacoes/): periodo, interpretar, montar_secao e as auxiliares.
Copiado do Ultron (sem importar de bot/): bot/intimacoes.py (pesquisar, _ler_linha,
periodo_pesquisa, colunas do data-id) e DOCUMENTACAO.md, passos 9 a 11.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from nucleo import vios
from nucleo.modelos import Item, Secao

log = logging.getLogger("orelha")

CHAVE = "intimacoes"
TITULO = "Intimações esquecidas (sem tarefa)"
PRECISA_VIOS = True

# --- padrões (todos sobrescrevíveis no orelha/.env) ---
URL_PESQUISA = "index.php?pag=sys/publicacoes/int-pesquisa.php"
CAMPO_DATA = "css:input[name='pesq[fdata]']"     # PESQUISA_CAMPO_DATA do Ultron
LINHAS = "css:tr[id*='_linha_']"                 # só as linhas de dados têm id "<tabela>_linha_<n>"
MARCAR_TODAS = "pesq[pr_areas_id][]"            # filtro Área ("Marcar todas"), como no Ultron (passo 11)
LIMITE = 500                                     # "Mostrar": máximo de linhas da tela
DIAS = 15
GRAVE_DIAS = 5
FIXTURE = "pesquisa.html"

# nomes dos campos do formulário de pesquisa (os do Ultron)
CAMPO_INICIO, CAMPO_FIM, CAMPO_LIMITE = "pesq[idata]", "pesq[fdata]", "pesq[limit]"

# coluna do VIOS (final do data-id da célula) -> campo (as do Ultron, bot/intimacoes.py COLUNAS)
COLUNAS = {
    "imp_pub_id": "ci",
    "intimacao_numeros": "numeros",
    "pr_clientes_nome": "cliente",
    "advogado_nome": "advogado",
    "cidade_e_uf_do_processo": "cidade",
    "fornecedor": "fornecedor",
    "sdata": "datas",
}
# colunas em que o tribunal pode estar (a conferir na tela real; a do Ultron não tem tribunal)
COLUNAS_TRIBUNAL = ("tribunal", "imp_tribunal", "tribunal_sigla", "orgao", "orgao_julgador")
TRIBUNAL = re.compile(r"\b(TJ[A-Z]{2}|TRT-?\d{1,2}|TRF-?\d|TRE-?[A-Z]{2}|TJM-?[A-Z]{2}|STJ|STF|TST|TSE|STM)\b")
# código TR do número CNJ (NNNNNNN-DD.AAAA.J.TR.OOOO) -> UF, para justiça estadual e eleitoral
UF_TR = ("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SE SP TO").split()
CNJ_PARTES = re.compile(r"\d{7}-\d{2}\.\d{4}\.(\d)\.(\d{2})\.\d{4}")
DIAS_SEMANA = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")
TOTAL_RODAPE = re.compile(r"geratabela_total_quantidade_original[^>]*>\s*(?:<[^>]+>\s*)*(\d+)", re.I)


# ---------------------------------------------------------------- período (puro)
def periodo_ultron(hoje, dias_atras=1):
    """Período que o Ultron pesquisa hoje (cópia de bot/intimacoes.py, periodo_pesquisa):
    fim = hoje - dias_atras; se o fim cair no domingo, o início volta para a sexta."""
    fim = hoje - timedelta(days=dias_atras)
    inicio = fim - timedelta(days=2) if fim.weekday() == 6 else fim
    return inicio, fim


def periodo(hoje, dias=DIAS, seguir_ultron=True):
    """(inicio, fim) da pesquisa do Orelha: de hoje - dias até anteontem.

    Com seguir_ultron, o fim também fica antes do que o Ultron ainda vai tratar hoje (na segunda,
    sexta a domingo): segunda -> fim na quinta. Se inicio > fim, o período está vazio."""
    fim = hoje - timedelta(days=2)
    if seguir_ultron:
        fim = min(fim, periodo_ultron(hoje)[0] - timedelta(days=1))
    return hoje - timedelta(days=dias), fim


# ---------------------------------------------------------------- interpretação (pura)
@dataclass
class Intimacao:
    ci: str
    disponibilizacao: date = None
    publicacao: date = None
    processo: str = ""
    tribunal: str = ""
    cidade: str = ""
    cliente: str = ""
    advogado: str = ""
    link: str = ""            # ficha do processo (nunca a tela de lançamento)


@dataclass
class Leitura:
    intimacoes: list = field(default_factory=list)   # dentro do período, sem repetir CI
    linhas: int = 0                                  # linhas de dados na tabela
    fora_do_periodo: int = 0                         # ontem/hoje ou fora do pesquisado: ignoradas
    sem_data: int = 0                                # sem data de disponibilização legível
    repetidas: int = 0
    apagadas: int = 0
    erros: int = 0                                   # linhas que não deu para ler
    total_rodape: int = None                         # total que o rodapé da tela diz


def _data_rotulo(texto, rotulo):
    """Data depois de "Disponibilização:" / "Publicação:" (sem acento, sem diferença de maiúsculas)."""
    t = vios.normalizar(texto)
    m = re.search(vios.normalizar(rotulo) + r"\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", t)
    return vios.data_br(m.group(1)) if m else None


def _link_processo(linha, base, proibidas):
    """Link da ficha do processo na linha; nunca o de lançar/apagar (ORELHA_URL_PROIBIDA)."""
    candidatos = [l["href"] for l in linha.links
                  if l.get("href") and not vios.url_proibida(l["href"], proibidas)]
    for href in candidatos:
        if "processos-vis.php" in href:
            return vios.url_absoluta(base, href) if base is not None else href
    return ""


def tribunal_do_cnj(numero):
    """Sigla do tribunal pelo número CNJ (segmentos J e TR): 8.06 -> TJCE, 5.07 -> TRT7,
    4.05 -> TRF5, 6.06 -> TRECE, 5.00 -> TST, 3.00 -> STJ, 1.00 -> STF. "" se não reconhece."""
    m = CNJ_PARTES.search(numero or "")
    if not m:
        return ""
    j, tr = m.group(1), int(m.group(2))
    if tr == 0:
        return {"1": "STF", "3": "STJ", "5": "TST", "6": "TSE", "7": "STM"}.get(j, "")
    if j in ("8", "6", "9") and tr <= len(UF_TR):
        return {"8": "TJ", "6": "TRE", "9": "TJM"}[j] + UF_TR[tr - 1]
    if j == "5":
        return f"TRT{tr}"
    if j == "4":
        return f"TRF{tr}"
    return ""


def _tribunal(linha, campos, processo):
    """Tribunal: coluna própria (se a tela tiver), senão pelo número CNJ, senão sigla no
    fornecedor, senão o próprio fornecedor."""
    for coluna in COLUNAS_TRIBUNAL:
        if linha.por_data_id.get(coluna):
            return linha.por_data_id[coluna]
    sigla = tribunal_do_cnj(processo)
    if sigla:
        return sigla
    m = TRIBUNAL.search(vios.normalizar(campos.get("fornecedor", "")))
    return m.group(1).replace("-", "") if m else campos.get("fornecedor", "")


def ler_linha(linha, base=None, proibidas=()):
    """Linha da tabela (nucleo.vios.Linha) -> Intimacao. Levanta ValueError sem CI."""
    campos = {campo: linha.por_data_id.get(col, "") for col, campo in COLUNAS.items()}
    ci = vios.digitos(campos["ci"]) or vios.limpar(campos["ci"])
    if not ci:
        raise ValueError("linha sem CI")
    datas = campos["datas"]
    disp = _data_rotulo(datas, "Disponibilização")
    if disp is None and not _data_rotulo(datas, "Publicação"):
        disp = vios.data_br(datas)   # célula só com a data
    numeros = vios.cnjs(campos["numeros"])
    processo = numeros[0] if numeros else vios.limpar(campos["numeros"])
    return Intimacao(
        ci=ci,
        disponibilizacao=disp,
        publicacao=_data_rotulo(datas, "Publicação"),
        processo=processo,
        tribunal=_tribunal(linha, campos, processo),
        cidade=campos["cidade"],
        cliente=campos["cliente"],
        advogado=campos["advogado"],
        link=_link_processo(linha, base, proibidas),
    )


def total_rodape(html):
    """Total que o rodapé da tabela do VIOS diz (.geratabela_total_quantidade_original), ou None."""
    m = TOTAL_RODAPE.search(html or "")
    return int(m.group(1)) if m else None


def tabela_intimacoes(html):
    """A tabela cujas linhas têm id "<tabela>_linha_<n>" (a do resultado), ou None.
    Aceita a página inteira ou só a tabela."""
    for indice in range((html or "").lower().count("<table")):
        tabela = vios.ler_tabela_html(html, indice=indice)
        if any("_linha_" in l.id for l in tabela.linhas):
            return tabela
    return None


def interpretar(html, inicio, fim, base=None, proibidas=()):
    """HTML do resultado da pesquisa -> Leitura com as intimações de inicio a fim (inclusive),
    ordenadas da mais antiga para a mais nova (e por CI). As de fora do período (ontem e hoje,
    se a tela devolver) e as sem data de disponibilização ficam de fora e só são contadas.
    base: a Config (para link absoluto); proibidas: trechos de endereço que nunca viram link."""
    leitura = Leitura(total_rodape=total_rodape(html))
    tabela = tabela_intimacoes(html)
    if tabela is None:
        return leitura
    vistos = set()
    for n, linha in enumerate(tabela.linhas, 1):
        if "_linha_" not in linha.id:
            continue
        leitura.linhas += 1
        if any(vios.normalizar(t) == "APAGADA" for t in linha.titulos):
            leitura.apagadas += 1
            continue
        try:
            intimacao = ler_linha(linha, base, proibidas)
        except ValueError as e:
            leitura.erros += 1
            log.warning("Intimações: linha %d pulada (%s)", n, e)
            continue
        if intimacao.ci in vistos:
            leitura.repetidas += 1
            continue
        vistos.add(intimacao.ci)
        if intimacao.disponibilizacao is None:
            leitura.sem_data += 1
            log.warning("Intimações: CI %s sem data de disponibilização legível", intimacao.ci)
            continue
        if not inicio <= intimacao.disponibilizacao <= fim:
            leitura.fora_do_periodo += 1
            continue
        leitura.intimacoes.append(intimacao)
    leitura.intimacoes.sort(key=lambda i: (i.disponibilizacao, int(i.ci) if i.ci.isdigit() else 0, i.ci))
    return leitura


def _dias(n):
    return "1 dia" if n == 1 else f"{n} dias"


def _curta(dia):
    return dia.strftime("%d/%m")


def item(intimacao, hoje, grave_dias=GRAVE_DIAS):
    """Intimacao -> Item do relatório. Grave = disponibilizada há mais de grave_dias dias."""
    idade = (hoje - intimacao.disponibilizacao).days
    if vios.cnjs(intimacao.processo):
        titulo = f"CI {intimacao.ci} · processo {intimacao.processo}"
    else:
        titulo = f"CI {intimacao.ci} · {intimacao.processo or 'sem número de processo'}"
    partes = [p for p in (intimacao.tribunal, intimacao.cidade) if p]
    if intimacao.cliente:
        partes.append(f"cliente: {intimacao.cliente}")
    if intimacao.advogado:
        partes.append(f"advogado: {intimacao.advogado}")
    partes.append(f"disponibilizada em {vios.br(intimacao.disponibilizacao)}, há {_dias(idade)}, ainda sem tarefa")
    dia = intimacao.disponibilizacao
    return Item(titulo=titulo, detalhe=" · ".join(partes),
                nivel="grave" if idade > grave_dias else "atencao",
                link=intimacao.link,
                grupo=f"Disponibilizadas em {vios.br(dia)} ({DIAS_SEMANA[dia.weekday()]})")


def montar_secao(leitura, hoje, inicio, fim, grave_dias=GRAVE_DIAS, avisos=()):
    """Leitura -> Secao (itens, resumo e números para o resumo.json e a vila)."""
    itens = [item(i, hoje, grave_dias) for i in leitura.intimacoes]
    graves = sum(1 for i in itens if i.nivel == "grave")
    periodo_txt = f"de {_curta(inicio)} a {_curta(fim)}"
    if not itens:
        resumo = f"Nenhuma intimação esquecida {periodo_txt}: todas já têm tarefa."
    else:
        qtd = f"{len(itens)} intimaç{'ão' if len(itens) == 1 else 'ões'} sem tarefa {periodo_txt}"
        resumo = (f"{qtd} ({graves} com mais de {_dias(grave_dias)})." if graves
                  else f"{qtd}, todas com até {_dias(grave_dias)}.")
    avisos = list(avisos)
    if leitura.total_rodape is not None and leitura.total_rodape > leitura.linhas:
        avisos.append(f"A tela mostrou {leitura.linhas} de {leitura.total_rodape} intimações: "
                      "aumente ORELHA_INTIMACOES_LIMITE ou diminua ORELHA_INTIMACOES_DIAS.")
    if leitura.erros:
        avisos.append(f"{leitura.erros} linha(s) da tabela não deu para ler (ver o log).")
    if leitura.sem_data:
        avisos.append(f"{leitura.sem_data} intimação(ões) sem data de disponibilização legível ficaram de fora (ver o log).")
    numeros = {
        "esquecidas": len(itens),
        "graves": graves,
        "atencao": len(itens) - graves,
        "mais_antiga_dias": max(((hoje - i.disponibilizacao).days for i in leitura.intimacoes), default=0),
        "dias_pesquisados": (fim - inicio).days + 1,
        "linhas_lidas": leitura.linhas,
        "fora_do_periodo": leitura.fora_do_periodo,
        "erros_leitura": leitura.erros + leitura.sem_data,
    }
    return Secao(chave=CHAVE, titulo=TITULO, resumo=resumo, itens=itens, numeros=numeros, avisos=avisos)


def filtros_extra(texto):
    """"nome=valor|nome=valor" -> {nome: valor} (ORELHA_INTIMACOES_FILTROS_EXTRA)."""
    saida = {}
    for parte in (texto or "").split("|"):
        nome, sep, valor = parte.partition("=")
        if not sep or not nome.strip():
            raise ValueError("use nome=valor separados por |")
        saida[nome.strip()] = valor.strip()
    return saida


# ---------------------------------------------------------------- configuração
@dataclass
class Opcoes:
    dias: int = DIAS
    grave_dias: int = GRAVE_DIAS
    seguir_ultron: bool = True
    url: str = URL_PESQUISA
    campo_data: tuple = None
    linhas: tuple = None
    marcar_todas: list = field(default_factory=list)
    limite: int = LIMITE
    extras: dict = field(default_factory=dict)


def opcoes(cfg):
    o = Opcoes(
        dias=cfg.valor("ORELHA_INTIMACOES_DIAS", DIAS, int),
        grave_dias=cfg.valor("ORELHA_INTIMACOES_GRAVE_DIAS", GRAVE_DIAS, int),
        seguir_ultron=cfg.valor("ORELHA_INTIMACOES_SEGUIR_ULTRON", True, bool),
        url=cfg.valor("ORELHA_INTIMACOES_URL", URL_PESQUISA),
        campo_data=cfg.valor("ORELHA_INTIMACOES_CAMPO_DATA", CAMPO_DATA, "seletor"),
        linhas=cfg.valor("ORELHA_INTIMACOES_LINHAS", LINHAS, "seletor"),
        marcar_todas=cfg.valor("ORELHA_INTIMACOES_MARCAR_TODAS", MARCAR_TODAS, "lista", sep="|"),
        limite=cfg.valor("ORELHA_INTIMACOES_LIMITE", LIMITE, int),
        extras=cfg.valor("ORELHA_INTIMACOES_FILTROS_EXTRA", "", filtros_extra) or {},
    )
    if o.dias < 1 or o.grave_dias < 0 or o.limite < 1:
        raise ValueError("ORELHA_INTIMACOES_DIAS e ORELHA_INTIMACOES_LIMITE precisam ser maiores que zero")
    return o


# ---------------------------------------------------------------- leitura (Selenium)
def ler_vios(ctx, o, inicio, fim):
    """Abre a pesquisa de intimações, envia o período e devolve (html da página, avisos).
    Nunca clica em nada: o formulário é enviado por enviar_pesquisa (marcado como pesquisa)."""
    from nucleo.navegador import tentativas_barradas
    avisos = []
    vios.abrir(ctx, o.url)
    filtros = {CAMPO_INICIO: vios.br(inicio), CAMPO_FIM: vios.br(fim), CAMPO_LIMITE: str(o.limite), **o.extras}
    log.info("Intimações: pesquisando as sem tarefa de %s a %s", vios.br(inicio), vios.br(fim))
    r = vios.enviar_pesquisa(ctx, o.campo_data, filtros, marcar_todas=o.marcar_todas)
    faltando = list(r.get("faltando", []))
    if CAMPO_INICIO in faltando or CAMPO_FIM in faltando:
        raise vios.ViosErro("a tela de pesquisa de intimações não tem os campos de data (pesq[idata]/pesq[fdata])")
    for nome in faltando:
        log.warning("Intimações: filtro %s não encontrado na tela", nome)
        avisos.append(f"Filtro {nome} não encontrado na tela de pesquisa (confira ORELHA_INTIMACOES_*).")
    for nome, n in r.get("marcados", {}).items():
        log.info("Intimações: marcar todas em %s: %d opções", nome, n)
    linhas = vios.esperar_varios(ctx, o.linhas)
    log.info("Intimações: %d linha(s) na tabela", len(linhas))
    if not linhas:
        barrados = tentativas_barradas(ctx.driver)
        if barrados:
            avisos.append(f"O bloqueio de envios barrou {len(barrados)} pedido(s) da página: "
                          "a lista pode ter vindo vazia por isso (ver o log).")
            log.warning("Intimações: bloqueio barrou %s", barrados)
    return vios.html(ctx), avisos


# A tela de pesquisa é um formulário GET: a mesma pesquisa abre pelo endereço, sem enviar formulário
# (visto ao vivo em 04/11/2026). Sem filtro de Área: "Marcar todas" as áreas (como o Ultron faz)
# deixava de fora as intimações sem área — no teste, 2 de 5 no lugar de 5.
LIMITE_TELA = 500  # maior opção de pesq[limit] na tela
FILTROS_URL = {"pesq[tp_data]": "data", "pesq[processado]": "0", "pesq[flag_oculto]": "0",
               "pesq[tp_int]": "T", "pesq[filtros]": "todos"}


def url_pesquisa(o, inicio, fim):
    """Endereço da pesquisa de intimações SEM tarefa lançada (pesq[processado]=0), ativas, por data
    de disponibilização, de `inicio` a `fim`. Só GET."""
    filtros = {"pag": "sys/publicacoes/int-pesquisa.php", **FILTROS_URL, "pesq[idata]": vios.br(inicio),
               "pesq[fdata]": vios.br(fim), "pesq[limit]": str(min(o.limite, LIMITE_TELA)), **o.extras,
               "Pesq": "Pesquisar"}
    return "?" + "&".join(f"{k}={v}" for k, v in filtros.items())


def ler_por_url(ctx, o, inicio, fim):
    """Abre a pesquisa pelo endereço e devolve (html da página, avisos)."""
    avisos = []
    log.info("Intimações: pesquisando as sem tarefa de %s a %s", vios.br(inicio), vios.br(fim))
    vios.abrir(ctx, url_pesquisa(o, inicio, fim))
    linhas = ctx.driver.find_elements(*o.linhas)
    log.info("Intimações: %d linha(s) na tabela", len(linhas))
    if len(linhas) >= min(o.limite, LIMITE_TELA):
        avisos.append(f"A pesquisa veio com {len(linhas)} linhas, o máximo pedido: pode haver mais "
                      "(diminua ORELHA_INTIMACOES_DIAS).")
    return vios.html(ctx), avisos


def executar(ctx):
    ctx.emitir("fase", fase="lendo_intimacoes")
    o = opcoes(ctx.cfg)
    inicio, fim = periodo(ctx.hoje, o.dias, o.seguir_ultron)
    if inicio > fim:
        return Secao(chave=CHAVE, titulo=TITULO, resumo="Período vazio: nada a pesquisar.", itens=[],
                     numeros={"esquecidas": 0, "graves": 0},
                     avisos=[f"ORELHA_INTIMACOES_DIAS={o.dias} não alcança antes de {vios.br(fim + timedelta(days=1))}"
                             " (o que o Ultron ainda vai tratar)."])
    avisos = []
    if ctx.simulado:
        from nucleo import simulado
        html = simulado.ler(ctx, FIXTURE)
    else:
        if ctx.cfg.valor("ORELHA_INTIMACOES_LEITURA", "url").lower() == "formulario":
            html, avisos = ler_vios(ctx, o, inicio, fim)  # leitura antiga: envia o formulário da tela
        else:
            html, avisos = ler_por_url(ctx, o, inicio, fim)
    leitura = interpretar(html, inicio, fim, base=ctx.cfg, proibidas=ctx.cfg.urls_proibidas)
    if leitura.fora_do_periodo:
        log.info("Intimações: %d fora do período (ontem/hoje ou antes de %s) ignorada(s)",
                 leitura.fora_do_periodo, vios.br(inicio))
    return montar_secao(leitura, ctx.hoje, inicio, fim, o.grave_dias, avisos)
