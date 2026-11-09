"""Tarefas atrasadas da equipe: placar das tarefas não concluídas com prazo vencido, por responsável.

  - "vence hoje" (nível "info", grupo próprio no topo): a data para conclusão ou a limite é hoje e
    a tarefa ainda não está atrasada — ainda dá para fazer hoje; NÃO conta como atrasada;
  - atrasada = a data para conclusão já passou (sem ela, a limite). Por idade do atraso:
    "atencao" até ORELHA_PRAZOS_DIAS_GRAVE dias (padrão 7) e "grave" com mais que isso.
  (Na 1ª rodada real, 04/11/2026, "limite vencida ou hoje" virou quase tudo grave: o limite costuma
  ser 1 dia depois da conclusão; e as que vencem hoje entravam como atrasadas.)
Grupo = o dia do vencimento (data para conclusão; sem ela, a limite): cada dia da última semana num
grupo ("Quinta-feira, 05/11 · ontem"), depois de 8 a 35 dias atrás por semana, depois por mês e por ano.
No relatório os grupos vêm fechados (clica e abre). A contagem por responsável vai no quadro do fim da
seção. Também gera semana.html (nucleo/semana.py): a semana dia a dia, com a mesma leitura.
numeros = {"atrasadas", "graves", "por_responsavel", ...}. Tendência: grava
historico/prazos-<AAAA-MM-DD>.json com as contagens e compara com o registro de 7 dias antes.

Leitura padrão (ORELHA_PRAZOS_FONTE=lista), vista ao vivo em 04/11/2026: a LISTA DE TAREFAS do VIOS
(`?pag=sys/processos/pxe-lista.php`), aberta por GET com os filtros no endereço — é para ela que
apontam as tarefas agrupadas do calendário. Sem responsável no filtro ela traz a equipe toda (16
responsáveis vistos). Duas leituras: pesq[tp_data]=data_prevista até ontem (atrasadas) e
pesq[tp_data]=data_limite até hoje (graves), com pesq[flag_conclusao]=0. A tabela #tarefas-lista
tem células com data-id "tarefas-lista_linha_<n>_<coluna>": datas ("Para conclusão: DD/MM/AAAA ...
Limite: DD/MM/AAAA"), tip (tipo da tarefa), envolvidos ("Responsável do processo: ...
Responsável(eis): ..."), e o link da tarefa (processos/pxe.php?pxe_id=). A tela mostra no máximo
1000 linhas: com isso, a seção avisa.

Leitura antiga (ORELHA_PRAZOS_FONTE=calendario): o calendário do VIOS, pela mesma leitura da agenda (funcoes/agenda.py:
ler_calendario, copiada da ideia do Zangão), com o filtro de ORELHA_PRAZOS_FILTROS (Concluída = Não,
sem responsável = equipe toda) e os meses anteriores (ORELHA_PRAZOS_MESES_ANTERIORES). Tarefa atrasada
sem responsável ou sem data limite na leitura do calendário: abre a ficha da tarefa (GET, com o
bloqueio de envios total) e lê "Responsáveis", "Para conclusão" e "Limite" do texto, até
ORELHA_PRAZOS_ABRIR_TAREFAS fichas por execução.

A CONFERIR NA TELA REAL: o painel do calendário mostra um responsável por vez; como pegar a equipe
toda (nomes dos campos do filtro) e onde ficam responsável e data limite não foi confirmado. A seção
avisa quando a leitura veio sem filtro de equipe ou sem responsável.
Nomes da equipe aparecem no relatório (interno), nunca nos eventos da vila (numeros_seguros tira
por_responsavel) nem em fixtures/testes (fictícios).
"""
import logging
import re
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import unquote, urljoin

from funcoes import agenda
from nucleo import semana, simulado, vios
from nucleo.modelos import Item, Secao

TITULO = "Tarefas atrasadas da equipe"
PRECISA_VIOS = True

log = logging.getLogger("orelha")

SEM_RESPONSAVEL = "Sem responsável identificado"
DIAS_TENDENCIA = 7


# ---------------------------------------------------------------- interpretação (puras)
def tarefas_abertas(eventos, data_do_calendario="conclusao"):
    """Só as tarefas não concluídas, uma por link. A data em que o calendário põe a tarefa é a data
    para conclusão (ou a data limite, com data_do_calendario="limite", conforme o "Tipo de Prazo"
    do filtro) quando a propriedade/tooltip não traz a data."""
    vistas, saida = set(), []
    for ev in eventos:
        if ev.categoria != "tarefa" or ev.concluida:
            continue
        chave = ev.link or (agenda.dobrar(ev.titulo), ev.dia)
        if chave in vistas:
            continue
        vistas.add(chave)
        if data_do_calendario == "limite":
            ev.limite = ev.limite or ev.dia
        else:
            ev.conclusao = ev.conclusao or ev.dia
        saida.append(ev)
    return saida


def precisa_ficha(ev, hoje):
    """A tarefa pode estar atrasada e falta responsável ou data limite: vale abrir a ficha.
    (Se a conclusão é depois de hoje, a limite também é: não está atrasada.)"""
    referencia = ev.conclusao or ev.limite
    return bool(ev.link) and referencia is not None and referencia <= hoje and not (ev.responsavel and ev.limite)


def completar(ev, campos):
    """Junta à tarefa o que a ficha trouxe (sem sobrescrever o que o calendário já tinha)."""
    ev.responsavel = ev.responsavel or campos.get("responsavel", "")
    ev.limite = ev.limite or campos.get("limite")
    ev.conclusao = ev.conclusao or campos.get("conclusao")
    ev.tipo = ev.tipo or campos.get("tipo", "")
    if campos.get("concluida_em"):
        ev.concluida = True
    return ev


def _dias(n):
    return "1 dia" if n == 1 else f"{n} dias"


def responsavel_principal(texto):
    """Primeiro nome da lista de responsáveis ("Ana Fictícia, Bruno Fictício" -> "Ana Fictícia")."""
    partes = [p.strip() for p in re.split(r"[,;/]| e ", texto or "") if p.strip()]
    return partes[0] if partes else ""


VENCE_HOJE = "Vencem hoje"
DIAS_GRAVE = 7
DIAS_SEMANA = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")


def referencia(ev):
    """O dia em que a tarefa venceu: a data para conclusão; sem ela, a limite."""
    return ev.conclusao or ev.limite


def grupo_do_dia(ref, hoje):
    """(ordem, rótulo) do grupo de uma atrasada pelo dia do vencimento, do mais recente para o mais antigo:
    cada dia até 7 dias atrás; de 8 a 35 dias, uma faixa de 7 dias; depois o mês (até 12 meses) e o ano."""
    d = (hoje - ref).days
    if d <= 7:
        return (0, d), f"{DIAS_SEMANA[ref.weekday()]}, {ref:%d/%m}" + (" · ontem" if d == 1 else f" · há {d} dias")
    if d <= 35:
        k = (d - 8) // 7
        mais_novo, mais_velho = hoje - timedelta(days=8 + 7 * k), hoje - timedelta(days=14 + 7 * k)
        return (1, k), f"De {mais_velho:%d/%m} a {mais_novo:%d/%m} · há {8 + 7 * k} a {14 + 7 * k} dias"
    if (hoje.year * 12 + hoje.month) - (ref.year * 12 + ref.month) < 12:
        return (2, -(ref.year * 12 + ref.month)), f"{MESES[ref.month - 1].capitalize()} de {ref.year}"
    return (3, -ref.year), f"Ano de {ref.year}"


def classificar(ev, hoje, dias_grave=DIAS_GRAVE):
    """(situação, dias de atraso): ("atrasada", n>0) | ("hoje", 0) | (None, 0) se ainda não vence.
    Atraso conta da data para conclusão; sem ela, da limite."""
    referencia = ev.conclusao or ev.limite
    if referencia is not None and referencia < hoje:
        return "atrasada", (hoje - referencia).days
    if (ev.conclusao is not None and ev.conclusao == hoje) or (ev.limite is not None and ev.limite == hoje):
        return "hoje", 0
    return None, 0


def placar(tarefas, hoje, dias_grave=DIAS_GRAVE):
    """Tarefas -> (itens, numeros). Primeiro o grupo "Vencem hoje" (nível info); depois as atrasadas
    por responsável: "grave" = atrasada há mais de `dias_grave` dias, "atencao" = até isso. Grupos de
    atrasadas em ordem de mais graves, depois de mais atrasadas; "sem responsável" por último. Dentro
    do grupo: graves primeiro, mais antiga primeiro."""
    linhas, hoje_itens = [], []
    for ev in tarefas:
        if ev.concluida:
            continue
        situacao, atraso = classificar(ev, hoje, dias_grave)
        if situacao is None:
            continue
        dono = responsavel_principal(ev.responsavel) or SEM_RESPONSAVEL
        partes = []
        if ev.conclusao:
            d = (hoje - ev.conclusao).days
            partes.append(f"para conclusão {vios.br(ev.conclusao)}"
                          + (f" (há {_dias(d)})" if d > 0 else " (hoje)" if d == 0 else ""))
        if ev.limite:
            d = (hoje - ev.limite).days
            partes.append(f"limite {vios.br(ev.limite)}"
                          + (f" (venceu há {_dias(d)})" if d > 0 else " (hoje)" if d == 0 else ""))
        else:
            partes.append("data limite não lida")
        partes.insert(0, f"responsável: {ev.responsavel or SEM_RESPONSAVEL}")
        if ev.tipo and agenda.dobrar(ev.tipo) not in agenda.dobrar(ev.titulo):
            partes.append(ev.tipo)
        if getattr(ev, "etiqueta", ""):
            partes.append(f"etiqueta no VIOS: {ev.etiqueta}")
        link = ev.link if ev.link.startswith(("http://", "https://")) else ""
        if situacao == "hoje":
            hoje_itens.append((agenda.dobrar(dono), agenda.dobrar(ev.titulo),
                               Item(titulo=ev.titulo, detalhe=" · ".join(partes), nivel="info", link=link,
                                    grupo=VENCE_HOJE, dia=hoje)))
            continue
        grave = atraso > dias_grave
        ordem, rotulo = grupo_do_dia(referencia(ev), hoje)
        item = Item(titulo=ev.titulo, detalhe=" · ".join(partes), nivel="grave" if grave else "atencao",
                    link=link, grupo=rotulo, dia=referencia(ev))
        linhas.append((dono, grave, -atraso, agenda.dobrar(ev.titulo), item, ordem, referencia(ev)))

    por = {}
    for dono, grave, *_ in linhas:
        c = por.setdefault(dono, {"atrasadas": 0, "graves": 0})
        c["atrasadas"] += 1
        c["graves"] += int(grave)
    ordem = sorted(por, key=lambda d: (d == SEM_RESPONSAVEL, -por[d]["graves"], -por[d]["atrasadas"], agenda.dobrar(d)))
    # grupos do dia mais recente para o mais antigo; dentro, mais atrasada primeiro, depois responsável e título
    linhas.sort(key=lambda x: (x[5], x[2], x[0] == SEM_RESPONSAVEL, agenda.dobrar(x[0]), x[3]))
    hoje_itens.sort(key=lambda x: (x[0], x[1]))
    atrasadas = [x[4] for x in linhas]
    numeros = {"atrasadas": len(atrasadas), "graves": sum(1 for i in atrasadas if i.nivel == "grave"),
               "vencem_hoje": len(hoje_itens), "dias_grave": dias_grave,
               "destaque": len(atrasadas),  # número grande do cartão: só as atrasadas (não as que vencem hoje)
               "pessoas_com_atraso": len([d for d in por if d != SEM_RESPONSAVEL]),
               "sem_responsavel": por.get(SEM_RESPONSAVEL, {}).get("atrasadas", 0),
               "sem_data_limite": sum(1 for i in atrasadas if "data limite não lida" in i.detalhe),
               "por_responsavel": {d: dict(por[d]) for d in ordem}}
    return [x[2] for x in hoje_itens] + atrasadas, numeros


def quadro_responsaveis(numeros, dias_grave=DIAS_GRAVE):
    """Tabela do fim da seção: atrasadas por responsável (quem tem mais graves primeiro)."""
    por = numeros.get("por_responsavel") or {}
    return {"titulo": "Atrasadas por responsável",
            "colunas": ["Responsável", "Atrasadas", f"Há mais de {dias_grave} dias"],
            "linhas": [[d, c["atrasadas"], c["graves"]] for d, c in por.items()]}


def registro(numeros, hoje):
    """O que vai para historico/prazos-<data>.json (fica só na máquina: orelha/saida/ é ignorada pelo git)."""
    return {"data": hoje.isoformat(), "atrasadas": numeros.get("atrasadas", 0), "graves": numeros.get("graves", 0),
            "vencem_hoje": numeros.get("vencem_hoje", 0), "criterio": f"grave = atraso > {numeros.get('dias_grave', DIAS_GRAVE)} dias",
            "por_responsavel": numeros.get("por_responsavel", {})}


def comparar(atual, anterior):
    """Diferença das contagens de hoje para o registro anterior: {"atrasadas": +n, "graves": +n},
    ou None se não há registro (ou ele não serve)."""
    if not isinstance(anterior, dict):
        return None
    try:
        return {k: int(atual.get(k, 0)) - int(anterior[k]) for k in ("atrasadas", "graves")}
    except (KeyError, TypeError, ValueError):
        return None


def nome_registro(dia, simulado_=False):
    return f"prazos-{'simulado-' if simulado_ else ''}{dia.isoformat()}.json"


def _sinal(n):
    return f"+{n}" if n > 0 else str(n)


def montar_resumo(numeros, variacao=None, anterior=None):
    n, g = numeros.get("atrasadas", 0), numeros.get("graves", 0)
    dias = numeros.get("dias_grave", DIAS_GRAVE)
    if not n:
        frase = "Nenhuma tarefa atrasada."
    else:
        r = numeros.get("pessoas_com_atraso", 0)
        frase = (f"{n} {'tarefa atrasada' if n == 1 else 'tarefas atrasadas'}, "
                 f"{g} há mais de {dias} dias"
                 + (f", com {r} {'responsável' if r == 1 else 'responsáveis'}" if r else "") + ".")
    h = numeros.get("vencem_hoje", 0)
    if h:
        frase += f" {h} {'vence' if h == 1 else 'vencem'} hoje."
    if variacao is not None and anterior:
        frase += (f" Há {DIAS_TENDENCIA} dias eram {anterior.get('atrasadas', 0)} atrasadas "
                  f"({_sinal(variacao['atrasadas'])}), {anterior.get('graves', 0)} delas há mais de {dias} dias "
                  f"({_sinal(variacao['graves'])}).")
    return frase


# ---------------------------------------------------------------- tendência
def tendencia(ctx, numeros):
    """Grava o registro de hoje e compara com o de 7 dias antes. No simulado usa nomes
    prazos-simulado-* (não mistura com o histórico de verdade) e, se não houver registro, a fixture
    historico-anterior.json. Devolve (variacao, anterior, avisos)."""
    avisos = []
    if ctx.historico is None:
        return None, None, ["sem pasta de histórico: tendência de 7 dias não calculada"]
    antes = ctx.hoje - timedelta(days=DIAS_TENDENCIA)
    anterior = ctx.ler_historico(nome_registro(antes, ctx.simulado))
    if anterior is None and ctx.simulado:
        try:
            import json
            anterior = json.loads(simulado.ler(ctx, "historico-anterior.json"))
        except (OSError, ValueError):
            anterior = None
    try:
        ctx.gravar_historico(nome_registro(ctx.hoje, ctx.simulado), registro(numeros, ctx.hoje))
    except OSError as e:
        avisos.append(f"não consegui gravar o histórico de hoje ({e.__class__.__name__}): a tendência de "
                      "amanhã em diante fica sem este dia")
    variacao = comparar(numeros, anterior)
    if variacao is None:
        log.info("Prazos: sem registro de %s para comparar", vios.br(antes))
    return variacao, anterior, avisos


# ---------------------------------------------------------------- leitura das fichas
def _texto_ficha(ctx, ev, area):
    if ctx.simulado:
        try:
            return agenda.texto_de_html(simulado.ler(ctx, f"tarefa-{ev.pxe_id}.html"))
        except OSError:
            return ""
    vios.abrir(ctx, ev.link)  # GET, com o bloqueio total (sem liberar POST)
    if area:
        return vios.esperar(ctx, area, visivel=False).get_attribute("innerText") or ""
    return vios.texto_pagina(ctx)


def ler_fichas(ctx, tarefas, maximo, area=None):
    """Abre a ficha das tarefas que podem estar atrasadas e estão sem responsável/data limite.
    Devolve (fichas lidas, que ficaram de fora pelo limite, que falharam)."""
    candidatas = [ev for ev in tarefas if precisa_ficha(ev, ctx.hoje)]
    lidas = falhas = 0
    for ev in candidatas[:max(0, maximo)]:
        try:
            texto = _texto_ficha(ctx, ev, area)
        except vios.BloqueioInativo:
            raise
        except Exception as e:
            falhas += 1
            log.warning("Prazos: não li a ficha da tarefa %s (%s)", ev.pxe_id or "?", e.__class__.__name__)
            continue
        if texto:
            completar(ev, agenda.campos_do_texto(texto))
            lidas += 1
    return lidas, max(0, len(candidatas) - max(0, maximo)), falhas


# ---------------------------------------------------------------- função
# ---------------------------------------------------------------- lista de tarefas (pxe-lista.php)
LISTA_PAG = "sys/processos/pxe-lista.php"
LISTA_TABELA = "tarefas-lista"
LISTA_MAXIMO = 1000  # a tela avisa: "Essa lista exibirá até 1000 registros"; com pesq[limit] maior
# (ex.: 9999999) o VIOS recusa ("O limite de pesquisa em tabela é ...") e a página vem sem tabela
_RE_CONCLUSAO = re.compile(r"Para\s+conclus[aã]o:\s*(\d{2}/\d{2}/\d{4})(?:\s*\(\s*(\d{1,2}:\d{2})?)?", re.I)
_RE_LIMITE = re.compile(r"Limite:\s*(\d{2}/\d{2}/\d{4})", re.I)
_RE_RESPONSAVEIS = re.compile(
    r"Respons[aá]vel\(eis\):\s*(.*?)\s*(?=Auxiliar|Coordenador|Concluiu|Respons[aá]vel do processo|Usu[aá]rio|$)", re.I)
_RE_LINK_TAREFA = re.compile(r"processos/pxe\.php\b.*\bpxe_id=\d+")


@dataclass
class TarefaLista:
    """Uma linha da lista de tarefas, no formato que placar() usa."""
    titulo: str
    tipo: str = ""
    responsavel: str = ""
    conclusao: date = None
    limite: date = None
    link: str = ""
    concluida: bool = False
    hora: str = ""   # "15:50" quando a data para conclusão vem com faixa de horário "(15:50 - 23:59)"
    etiqueta: str = ""  # etiqueta da tarefa no VIOS (ex.: "Urgente", "Reaberta")
    processo: str = ""  # texto da coluna "nro_proc" (número CNJ, ou "CI nnn" quando não há processo); só o painel usa


def url_lista(tp_data, inicio, fim, limite=LISTA_MAXIMO):
    """Endereço (relativo à raiz do VIOS) da lista de tarefas NÃO concluídas cuja data `tp_data`
    (data_prevista = para conclusão, data_limite = limite) está entre `inicio` e `fim`. Só GET."""
    filtros = [("pag", LISTA_PAG), ("pesq[flag_conclusao]", "0"), ("pesq[tp_data]", tp_data),
               ("pesq[idata]", vios.br(inicio)), ("pesq[fdata]", vios.br(fim)), ("pesq[limit]", str(limite)),
               ("Pesq", "Pesquisar")]
    return "?" + "&".join(f"{k}={v}" for k, v in filtros)


_RE_BR = re.compile(r"<br\s*/?>", re.I)


def responsaveis_da_celula(texto):
    """'Responsável do processo: X ; ; Responsável(eis): A ; B' -> 'A, B' (só os da tarefa).
    Na tela, cada nome vem numa linha (<br>); tarefas_da_lista troca o <br> por " ; "."""
    m = _RE_RESPONSAVEIS.search(vios.limpar(texto))
    if not m:
        return ""
    nomes = [n.strip(" ,") for n in m.group(1).split(";")]
    return ", ".join(n for n in nomes if n)


def tarefas_da_lista(html, base=""):
    """Pura: HTML da lista de tarefas -> [TarefaLista]. Linhas sem data nem tipo ficam de fora."""
    saida = []
    html = _RE_BR.sub(" ; ", html or "")  # nomes da coluna Envolvidos vêm um por linha
    for ln in vios.ler_tabela_html(html, id_tabela=LISTA_TABELA):
        datas = ln.get("datas")
        # célula do tipo: [etiqueta do VIOS (Urgente, Reaberta, CANCELADA...)] <br> tipo; o <br> virou " ; "
        partes = [x.strip() for x in vios.limpar(ln.get("tip")).split(";") if x.strip()]
        tipo, etiqueta = (partes[-1], " ".join(partes[:-1])) if partes else ("", "")
        if not (datas or tipo):
            continue
        mc, ml = _RE_CONCLUSAO.search(datas or ""), _RE_LIMITE.search(datas or "")
        link = next((unquote(l.get("href", "")) for l in ln.links
                     if _RE_LINK_TAREFA.search(unquote(l.get("href", "")))), "")
        saida.append(TarefaLista(titulo=tipo or "Tarefa sem tipo", tipo=tipo,
                                 responsavel=responsaveis_da_celula(ln.get("envolvidos")),
                                 conclusao=vios.data_br(mc.group(1)) if mc else None,
                                 limite=vios.data_br(ml.group(1)) if ml else None,
                                 hora=(mc.group(2) or "").zfill(5) if mc and mc.group(2) else "", etiqueta=etiqueta,
                                 processo=vios.limpar(ln.get("nro_proc")),
                                 link=urljoin(base, link) if link else ""))
    return saida


def juntar_listas(listas):
    """Junta as leituras (atrasadas + graves) sem repetir a mesma tarefa (pelo link)."""
    vistas, saida = set(), []
    for lista in listas:
        for t in lista:
            chave = t.link or (agenda.dobrar(t.titulo), t.responsavel, t.conclusao, t.limite)
            if chave in vistas:
                continue
            vistas.add(chave)
            saida.append(t)
    return saida


VAZIA = f'<table id="{LISTA_TABELA}"><tbody></tbody></table>'
_JS_SEM_TABELA = """return {titulo: document.title || '',
  limite: ((document.body && document.body.innerText) || '').toLowerCase().includes('limite de pesquisa')}"""


def ler_lista(ctx, tp_data, inicio, fim):
    """Abre a lista de tarefas por GET (com o bloqueio de envios ligado) e devolve o HTML da tabela.
    Sem resultado, a tela de Tarefas vem sem a tabela (visto em 04/11/2026): devolve VAZIA. Devolve
    "" se a página não é a de Tarefas ou se o VIOS recusou a pesquisa ("limite de pesquisa")."""
    vios.abrir(ctx, url_lista(tp_data, inicio, fim))
    try:
        return vios.esperar(ctx, ("css selector", f"#{LISTA_TABELA}"), timeout=5, visivel=False).get_attribute("outerHTML")
    except vios.ViosErro:
        pass
    estado = ctx.driver.execute_script(_JS_SEM_TABELA) or {}
    if "Tarefas" in estado.get("titulo", "") and not estado.get("limite"):
        return VAZIA
    return ""


def janelas(inicio, fim, hoje):
    """Períodos de leitura: tudo o que é mais antigo que 1 ano numa janela só e, depois, um mês por
    janela (as tarefas recentes são muitas; janela pequena = página leve e longe do limite de 1000)."""
    saida, corte = [], max(inicio, hoje - timedelta(days=365))
    if corte > inicio:
        saida.append((inicio, min(fim, corte - timedelta(days=1))))
    a = corte
    while a <= fim:
        b = min(fim, a + timedelta(days=30))
        saida.append((a, b))
        a = b + timedelta(days=1)
    return [(x, y) for x, y in saida if x <= y]


def ler_periodo(ctx, tp_data, inicio, fim, contador, maximo, avisos):
    """Lê a lista de `inicio` a `fim`; se vier cheia (1000 linhas), divide o período ao meio e lê
    as duas metades. `contador` = [páginas abertas]; para em `maximo` páginas (com aviso)."""
    if contador[0] >= maximo:
        return None
    contador[0] += 1
    html = ler_lista(ctx, tp_data, inicio, fim)
    if not html:
        avisos.append(f"a lista de tarefas não apareceu ({tp_data}, {vios.br(inicio)} a {vios.br(fim)}): "
                      "conferir a tela pxe-lista.php")
        return []
    tarefas = tarefas_da_lista(html, ctx.cfg.vios_base)
    if len(tarefas) < LISTA_MAXIMO:
        return tarefas
    if inicio >= fim:
        avisos.append(f"o dia {vios.br(inicio)} tem {LISTA_MAXIMO} tarefas ou mais ({tp_data}): pode faltar alguma")
        return tarefas
    meio = inicio + timedelta(days=(fim - inicio).days // 2)
    saida = []
    for a, b in ((inicio, meio), (meio + timedelta(days=1), fim)):
        parte = ler_periodo(ctx, tp_data, a, b, contador, maximo, avisos)
        if parte is None:
            return None
        saida += parte
    return saida


def _executar_lista(ctx, avisos):
    """Fonte padrão: a lista de tarefas. Devolve as tarefas lidas.
    1) tarefas não concluídas com data para conclusão até ontem (as atrasadas, com a data limite);
    2) as com data limite nos últimos 30 dias até hoje: pega a que vence hoje e ainda não está
       atrasada pela data para conclusão (e alguma com limite antes da conclusão);
    3) as com data para conclusão hoje (vencem hoje, mesmo com o limite depois)."""
    cfg = ctx.cfg
    desde = vios.data_br(cfg.valor("ORELHA_PRAZOS_DESDE", "01/01/2000")) or date(2000, 1, 1)
    maximo = cfg.valor("ORELHA_PRAZOS_MAX_PAGINAS", 60, int)
    ctx.emitir("fase", fase="lendo_calendario")
    if ctx.simulado:
        return juntar_listas([tarefas_da_lista(simulado.ler(ctx, "lista.html"), cfg.vios_base)])
    ontem = ctx.hoje - timedelta(days=1)
    pedidos = [("data_prevista", a, b) for a, b in janelas(desde, ontem, ctx.hoje)]
    pedidos.append(("data_limite", max(desde, ctx.hoje - timedelta(days=30)), ctx.hoje))
    pedidos.append(("data_prevista", ctx.hoje, ctx.hoje))  # para conclusão hoje com limite depois: vence hoje
    contador, listas = [0], []
    for tp_data, a, b in pedidos:
        parte = ler_periodo(ctx, tp_data, a, b, contador, maximo, avisos)
        if parte is None:
            avisos.append(f"parei no limite de {maximo} páginas da lista de tarefas (ORELHA_PRAZOS_MAX_PAGINAS): "
                          "o placar pode estar incompleto")
            break
        listas.append(parte)
    log.info("Prazos: %d página(s) da lista de tarefas lidas", contador[0])
    return juntar_listas(listas)


def _primeiro_dia(hoje, meses_antes):
    """1º dia do mês mais antigo lido (o atual menos `meses_antes`)."""
    total = hoje.year * 12 + (hoje.month - 1) - meses_antes
    return date(total // 12, total % 12 + 1, 1)


def executar(ctx):
    fonte = ctx.cfg.valor("ORELHA_PRAZOS_FONTE", "lista").lower()
    if fonte != "calendario":
        avisos = []
        tarefas = _executar_lista(ctx, avisos)
        return _secao(ctx, tarefas, avisos)
    return _executar_calendario(ctx)


def _secao(ctx, tarefas, avisos):
    """Placar, avisos comuns, tendência e a Secao."""
    dias_grave = ctx.cfg.valor("ORELHA_PRAZOS_DIAS_GRAVE", DIAS_GRAVE, int)
    itens, numeros = placar(tarefas, ctx.hoje, dias_grave)
    numeros["lidas"] = len(tarefas)
    gerar_semana(ctx, itens, numeros)
    if numeros["sem_responsavel"]:
        avisos.append(f"{numeros['sem_responsavel']} tarefa(s) atrasada(s) vieram sem responsável na leitura")
    if numeros["sem_data_limite"]:
        avisos.append(f"{numeros['sem_data_limite']} tarefa(s) sem data limite na leitura: classificadas só "
                      "pela data para conclusão")
    variacao, anterior, mais = tendencia(ctx, numeros)
    avisos += mais
    if variacao is not None:
        numeros["variacao_7d_atrasadas"] = variacao["atrasadas"]
        numeros["variacao_7d_graves"] = variacao["graves"]
    return Secao(chave="prazos", titulo=TITULO, resumo=montar_resumo(numeros, variacao, anterior),
                 itens=itens, numeros=numeros, avisos=avisos, recolher=True,
                 quadro=quadro_responsaveis(numeros, dias_grave))


def gerar_semana(ctx, itens, numeros):
    """semana.html na pasta do dia (a semana dia a dia). Falhar aqui não derruba o placar."""
    if ctx.saida is None:
        return
    try:
        caminho = semana.gerar(itens, numeros, ctx.hoje, ctx.saida, simulado=ctx.simulado)
        log.info("Semana: %s", caminho)
    except Exception as e:  # noqa: BLE001 — a página da semana é um extra
        log.warning("Semana: não gerei a página (%s)", e)


def _executar_calendario(ctx):
    cfg = ctx.cfg
    conf = agenda.Calendario.do_cfg(cfg)
    meses = cfg.valor("ORELHA_PRAZOS_MESES_ANTERIORES", 2, int)
    modo = cfg.valor("ORELHA_PRAZOS_DATA_CALENDARIO", "conclusao").lower()
    if modo not in ("conclusao", "limite"):
        modo = "conclusao"
    maximo = cfg.valor("ORELHA_PRAZOS_ABRIR_TAREFAS", 30, int)
    area_ficha = cfg.valor("ORELHA_PRAZOS_FICHA_AREA", "", "seletor")

    ctx.emitir("fase", fase="lendo_calendario")
    avisos = []
    if ctx.simulado:
        lotes = agenda.lotes_simulados(ctx, ["eventos.json"])
    else:
        filtros, marcar = agenda.filtros_do_cfg(cfg, "PRAZOS")
        if not filtros and not marcar:
            avisos.append("filtro da equipe não configurado (ORELHA_PRAZOS_FILTROS / ORELHA_PRAZOS_MARCAR_TODAS): "
                          "o calendário foi lido como abre, que pode mostrar só as tarefas do usuário do Orelha")
        lotes, lidos = agenda.ler_calendario(ctx, conf, filtros, marcar, meses_antes=max(0, meses), prefixo="PRAZOS")
        avisos += lidos
    brutos, mais = agenda.brutos_dos_lotes(lotes, cfg.vios_base, conf.classe_evento)
    avisos += mais
    eventos = agenda.montar_eventos(brutos, conf.campos, conf.links_tarefa, conf.marcas_feriado)
    tarefas = tarefas_abertas(eventos, modo)
    if not tarefas:
        avisos.append("nenhuma tarefa aberta lida no calendário (conferir ORELHA_CALENDARIO_TAREFA e o filtro)")

    lidas, fora, falhas = ler_fichas(ctx, tarefas, maximo, area_ficha)
    if lidas or fora or falhas:
        log.info("Prazos: %d ficha(s) de tarefa lida(s), %d de fora pelo limite, %d com falha", lidas, fora, falhas)
    if fora:
        avisos.append(f"{fora} tarefa(s) possivelmente atrasada(s) sem responsável/data limite ficaram sem "
                      f"conferir a ficha (limite ORELHA_PRAZOS_ABRIR_TAREFAS={maximo})")
    if falhas:
        avisos.append(f"{falhas} ficha(s) de tarefa não abriram (ver logs/orelha.log)")

    dias_grave = cfg.valor("ORELHA_PRAZOS_DIAS_GRAVE", DIAS_GRAVE, int)
    itens, numeros = placar(tarefas, ctx.hoje, dias_grave)
    numeros["lidas"] = len(tarefas)
    gerar_semana(ctx, itens, numeros)
    # o calendário só traz os meses lidos: atrasada mais antiga que isso fica de fora do placar
    inicio = _primeiro_dia(ctx.hoje, max(0, meses))
    avisos.append(f"Tarefas com data para conclusão antes de {vios.br(inicio)} não entram no placar "
                  f"(são lidos o mês atual e {max(0, meses)} anterior(es): ORELHA_PRAZOS_MESES_ANTERIORES). "
                  "Para conferir, compare com o painel \"Tarefas Processuais Atrasadas\" do calendário.")
    if numeros["sem_responsavel"]:
        avisos.append(f"{numeros['sem_responsavel']} tarefa(s) atrasada(s) vieram sem responsável na leitura "
                      "(o calendário não mostrou e a ficha não foi lida ou não tinha)")
    if numeros["sem_data_limite"]:
        avisos.append(f"{numeros['sem_data_limite']} tarefa(s) sem data limite na leitura: classificadas só "
                      "pela data para conclusão")

    variacao, anterior, mais = tendencia(ctx, numeros)
    avisos += mais
    if variacao is not None:
        numeros["variacao_7d_atrasadas"] = variacao["atrasadas"]
        numeros["variacao_7d_graves"] = variacao["graves"]
    return Secao(chave="prazos", titulo=TITULO, resumo=montar_resumo(numeros, variacao, anterior),
                 itens=itens, numeros=numeros, avisos=avisos, recolher=True,
                 quadro=quadro_responsaveis(numeros, dias_grave))
