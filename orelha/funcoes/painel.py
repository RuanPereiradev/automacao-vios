"""Painel semanal de peças e audiências (PDF no visual do modelo "2026_PAINEL_SEMANAL" do escritório).

Roda à parte do relatório do dia (`--funcoes painel`, uma vez por semana) e gera, em
saida/<AAAA-MM-DD>/, o painel-semanal.html e o painel-semanal.pdf (desenho: nucleo/painel.py, igual ao
PDF de 19/07/2026: faixa azul-marinho em cada página). Não entra no relatório do dia (RELATORIO_DIARIO = False).

Quem entra (desde 23/11/2026): ORELHA_PAINEL_RESPONSAVEIS = os advogados do painel ("Joana Dotto, Tamira
Loiola, ..."; vazio = todo mundo). Cada nome casa com o nome completo do VIOS quando todas as palavras dele
estão no nome completo ("Francisco Barbosa" = "FRANCISCO JOHNYS VASCONCELOS BARBOSA") e aparece no painel
como está escrito na lista. Tarefa só de gente fora da lista (ou sem responsável) fica de fora; numa tarefa
com vários responsáveis, ficam só os da lista. Regra de atribuição: audiência CÍVEL com dois ou mais nomes
de ORELHA_PAINEL_GRUPO_CIVEL (o "grupo" do VIOS) vai só para ORELHA_PAINEL_GRUPO_CIVEL_PARA.

Fila = tarefas NÃO concluídas da equipe toda, de todos os tipos (desde 23/11/2026; antes só peças e
audiências), com data para conclusão (ou, sem ela, a limite) até hoje + ORELHA_PAINEL_DIAS_FILA dias
(padrão 7), lidas da lista de tarefas do VIOS (a mesma leitura dos prazos, só por GET). Categorias: peça
(tipo começa com ORELHA_PAINEL_TERMOS_PECA, padrão "MINUTAR"), audiência (começa com
ORELHA_PAINEL_TERMOS_AUDIENCIA, padrão "AUDIÊNCIA") e "outra" (o resto). ORELHA_PAINEL_OUTRAS=nao volta
a deixar só peças e audiências. Tarefas canceladas ficam de fora. Tarefa com mais de um responsável
conta na carga de cada um.

Situação (dias até o prazo; negativo = vencida): VENCIDA (já passou), URGENTE (hoje a 2 dias),
ATENÇÃO (3 a 7), PRÓXIMA (8 a 14), NO PRAZO (15 ou mais).

Comparação entre semanas: a cada execução completa a função grava historico/painel-<data>.json com a
fila lida. Na semana seguinte compara com o registro mais recente que tenha 5 dias ou mais:
  - NÃO FEITAS = estavam na fila anterior e continuam abertas; NOVAS = não estavam;
  - RESOLVIDAS = estavam na fila anterior e não aparecem mais abertas (o Orelha só enxerga as abertas,
    então concluídas e canceladas se confundem); taxa = resolvidas / fila anterior.
Sem registro anterior (1ª edição), o painel avisa e lista a fila inteira. Leitura incompleta (página
que não abriu, limite de páginas) não grava registro, para não distorcer a semana seguinte.

Os nomes da equipe aparecem no PDF (interno) e nunca nos eventos da vila (numeros só leva contagens).
"""
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from funcoes import agenda, prazos
from nucleo import painel as desenho
from nucleo import simulado, vios
from nucleo.modelos import Secao

TITULO = "Painel semanal (tarefas da equipe)"
PRECISA_VIOS = True
RELATORIO_DIARIO = False  # tem o próprio PDF; não entra no relatorio.html do dia

log = logging.getLogger("orelha")

SEM_RESPONSAVEL = "Sem responsável"
DIAS_FILA = 7  # a semana do painel: do dia do pedido até 7 dias depois (até 09/11/2026 eram 14)
DIAS_AGENDA = 7
URGENTE_ALTO = 15
TAXA_BOA = 70
TAXA_ATENCAO = 60
SEMANAS_NA_TABELA = 3
DIAS_MIN_BASE = 5    # registro mais novo que isso não serve de base (ex.: uma execução de teste no meio da semana)
DIAS_MAX_BASE = 35   # mais velho que isso a comparação deixa de ser "da semana anterior"
MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}
_RE_PXE = re.compile(r"pxe_id=(\d+)")
_RE_CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
_RE_NUMERO_FIM = re.compile(r"((?:NR|CI)\s*\d+|\d[\d.\-/]{5,}\d)\s*$", re.I)
TIPOS_TODAS = "todas"              # fila com todos os tipos de tarefa (desde 23/11/2026)
TIPOS_PECAS = "pecas_audiencias"   # só peças e audiências; registros sem o campo "tipos" são deste


@dataclass
class Entrada:
    """Uma tarefa da fila do painel."""
    chave: str
    categoria: str       # "peca" | "audiencia"
    responsavel: str     # nomes para mostrar ("Ana Fictícia, Bruno Fictício")
    processo: str
    tarefa: str
    prazo: date
    dias: int            # até o prazo; negativo = vencida
    hora: str = ""
    link: str = ""
    responsaveis: tuple = ()  # cada nome conta na carga (vazio = sem responsável)


# ---------------------------------------------------------------- regras (puras)
def nome_proprio(texto):
    """'JOANA CLÁUDIA DOTTO' -> 'Joana Cláudia Dotto' (de/da/do/das/dos/e em minúscula)."""
    palavras = (texto or "").lower().split()
    return " ".join(p if (i and p in MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palavras))


def faixa(dias):
    """(classe, texto) da situação: ("vencida", "VENCIDA 3d"), ("urgente", "URGENTE 1d")..."""
    if dias < 0:
        return "vencida", f"VENCIDA {-dias}d"
    if dias <= 2:
        return "urgente", "URGENTE hoje" if dias == 0 else f"URGENTE {dias}d"
    if dias <= 7:
        return "atencao", f"ATENÇÃO {dias}d"
    if dias <= 14:
        return "proxima", f"PRÓXIMA {dias}d"
    return "no_prazo", f"NO PRAZO {dias}d"


def categoria(tarefa, termos_peca, termos_audiencia, outras=True):
    """"audiencia", "peca", "outra" (os outros tipos) ou "" (com outras=False, os outros tipos não entram).
    Conta como peça/audiência só se o TIPO COMEÇA com o termo ("INFORMAR AUDIÊNCIA" é tarefa sobre a
    audiência, não a audiência: vira "outra")."""
    texto = re.sub(r"^C:\s*", "", agenda.dobrar(tarefa.tipo or tarefa.titulo).strip())
    for nome, termos in (("audiencia", termos_audiencia), ("peca", termos_peca)):
        if any(t and texto.startswith(agenda.dobrar(t)) for t in termos):
            return nome
    return "outra" if outras else ""


def casa(nome, curto):
    """True se todas as palavras de `curto` ("Francisco Barbosa") estão no nome completo `nome`
    ("FRANCISCO JOHNYS VASCONCELOS BARBOSA"). Sem acento e sem diferença de maiúsculas; ignora de/da/do."""
    palavras = set(agenda.dobrar(nome).split())
    pedidas = [p for p in agenda.dobrar(curto).split() if p.lower() not in MINUSCULAS]
    return bool(pedidas) and all(p in palavras for p in pedidas)


def nomes_da_tarefa(t, permitidos=(), grupo=(), alvo=""):
    """Nomes que a tarefa mostra e conta na carga.
    Regra de atribuição: audiência CÍVEL com 2+ nomes do `grupo` vai só para `alvo`. Com `permitidos`
    (os advogados do painel), ficam só os nomes da lista, escritos como na lista; sem lista, todos os
    nomes em nome próprio. Devolve (nomes, fora): `fora` = nomes que a lista deixou de fora."""
    brutos = prazos.responsaveis(t.responsavel)
    if (grupo and alvo and "CIVEL" in agenda.dobrar(t.tipo or t.titulo)
            and sum(1 for n in brutos if any(casa(n, g) for g in grupo)) >= 2):
        brutos = [alvo]
    if not permitidos:
        return tuple(nome_proprio(n) for n in brutos), ()
    nomes, fora = [], []
    for n in brutos:
        curto = next((p for p in permitidos if casa(n, p)), None)
        if curto is None:
            fora.append(nome_proprio(n))
        elif curto not in nomes:
            nomes.append(curto)
    return tuple(nomes), tuple(fora)


def numero_processo(texto):
    """Só o número do processo, como no modelo. A coluna do VIOS traz "CLIENTE ; número" (ex.: "CASA DO
    CELULAR - ASSESSORIA M ... ; 5026820-28.2026.8.08.0012" ou "SEM LAÇADOR 0002577-33.2026.5.07.0029"):
    fica o CNJ; sem CNJ, o que vem depois do último ";" ou o número do fim ("NR 1722086917"); sem número, "—"."""
    t = (texto or "").strip()
    m = _RE_CNJ.search(t)
    if m:
        return m.group(0)
    if ";" in t:
        return t.rsplit(";", 1)[1].strip() or "—"
    m = _RE_NUMERO_FIM.search(t)
    if m:
        return m.group(1)
    return t if re.search(r"\d", t) else "—"  # só nome (ex.: "HOLDING PATRIMONIAL"): não é número de processo


def _chave(t):
    m = _RE_PXE.search(t.link or "")
    return m.group(1) if m else (t.link or f"{t.processo}|{t.tipo}|{t.responsavel}|{t.conclusao}")


def periodo(ctx, dias_fila=DIAS_FILA):
    """(de, ate) do painel: o escolhido na página /orelha (--painel-de/--painel-ate) ou, sem escolha, de hoje
    até hoje + dias_fila. Só o fim escolhido: começa hoje. Só o início: vai até início + dias_fila."""
    de = getattr(ctx, "painel_de", None) or ctx.hoje
    ate = getattr(ctx, "painel_ate", None) or de + timedelta(days=dias_fila)
    return de, max(ate, de)


def montar_fila(tarefas, hoje, termos_peca, termos_audiencia, dias_fila=DIAS_FILA, de=None, ate=None, outras=True,
                permitidos=(), grupo=(), alvo=""):
    """[TarefaLista] -> ([Entrada], ignoradas). Sem repetir a mesma tarefa; fora as concluídas, as
    canceladas, as sem data, as de outros tipos e as com prazo fora do período. Período = de `de` (padrão
    hoje) até `ate` (padrão hoje + dias_fila), com as duas pontas: é o mesmo filtro da lista do VIOS
    (Para conclusão de `de` até `ate`). Desde 23/11/2026 as vencidas de antes de `de` NÃO entram mais
    (antes entravam sempre e o painel mostrava tarefas de 260 dias atrás); para a comparação com a semana
    anterior, executar() monta à parte a lista de todas as abertas. `permitidos`, `grupo` e `alvo`: ver
    nomes_da_tarefa(); tarefa sem nenhum nome da lista conta em ignoradas["fora_da_lista"]."""
    de = de or hoje
    ate = ate or hoje + timedelta(days=dias_fila)
    vistas, fila, ignoradas = set(), [], {"sem_data": 0, "fora_da_lista": 0, "nomes_fora": {}}
    for t in tarefas:
        cat = categoria(t, termos_peca, termos_audiencia, outras)
        if not cat or t.concluida or "CANCELAD" in agenda.dobrar(f"{t.etiqueta} {t.tipo}"):
            continue
        prazo = t.conclusao or t.limite
        if prazo is None:
            ignoradas["sem_data"] += 1
            continue
        dias = (prazo - hoje).days
        chave = _chave(t)
        if not (de <= prazo <= ate) or chave in vistas:
            continue
        vistas.add(chave)
        nomes, fora = nomes_da_tarefa(t, permitidos, grupo, alvo)
        if permitidos and not nomes:
            ignoradas["fora_da_lista"] += 1
            for n in fora or (SEM_RESPONSAVEL,):
                ignoradas["nomes_fora"][n] = ignoradas["nomes_fora"].get(n, 0) + 1
            continue
        fila.append(Entrada(chave=chave, categoria=cat, responsavel=", ".join(nomes) or SEM_RESPONSAVEL,
                            processo=numero_processo(t.processo), tarefa=t.tipo or t.titulo, prazo=prazo, dias=dias, hora=t.hora,
                            link=t.link, responsaveis=nomes))
    fila.sort(key=lambda e: (e.dias, agenda.dobrar(e.responsavel), agenda.dobrar(e.tarefa)))
    return fila, ignoradas


def carga(fila, urgente_alto=URGENTE_ALTO):
    """Peças, audiências, outras, total, vencidas e urgentes (prazo em até 7 dias, vencidas incluídas) por
    responsável. Tarefa com mais de um responsável conta para cada um. Mais carregado primeiro; "sem
    responsável" por último. `destaque` = urgentes >= urgente_alto."""
    por = {}
    coluna = {"peca": "pecas", "audiencia": "audiencias"}
    for e in fila:
        for nome in (e.responsaveis or (e.responsavel,)):
            c = por.setdefault(nome, {"nome": nome, "pecas": 0, "audiencias": 0, "outras": 0, "total": 0,
                                      "vencidas": 0, "urgente": 0})
            c[coluna.get(e.categoria, "outras")] += 1
            c["total"] += 1
            c["vencidas"] += int(e.dias < 0)
            c["urgente"] += int(e.dias <= 7)
    linhas = sorted(por.values(), key=lambda c: (c["nome"] == SEM_RESPONSAVEL, -c["total"], agenda.dobrar(c["nome"])))
    for c in linhas:
        c["destaque"] = c["urgente"] >= urgente_alto
    return linhas


def tipo_audiencia(tarefa):
    """'AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026' -> 'UNA/INSTRUÇÃO'."""
    t = re.sub(r"\s*\([^)]*\)\s*\d{4}\s*$", "", tarefa or "")
    t = re.sub(r"\s*\d{4}\s*$", "", t)
    t = re.sub(r"^AUDI[ÊE]NCIA\s+", "", t, flags=re.I).strip()
    return t or (tarefa or "")


def agenda_audiencias(fila, hoje, dias=DIAS_AGENDA, de=None, ate=None):
    """Audiências com data de hoje até hoje + dias (ou de `de` até `ate`, o período escolhido), em ordem de
    data e hora."""
    inicio, fim = (de or hoje), (ate or hoje + timedelta(days=dias))
    escolhidas = sorted((e for e in fila if e.categoria == "audiencia" and inicio <= e.prazo <= fim),
                        key=lambda e: (e.prazo, e.hora or "99:99", agenda.dobrar(e.responsavel)))
    return [{"data": f"{e.prazo:%d/%m}", "hora": e.hora or "--:--", "advogado": e.responsavel,
             "tipo": tipo_audiencia(e.tarefa), "processo": e.processo or "—"} for e in escolhidas]


def leitura(taxa, boa=TAXA_BOA, atencao=TAXA_ATENCAO):
    """Taxa (0 a 1) -> "Boa" | "Atenção" | "Baixa" ("—" sem taxa)."""
    if taxa is None:
        return "—"
    pct = taxa * 100
    return "Boa" if pct >= boa else "Atenção" if pct >= atencao else "Baixa"


def _pct(taxa):
    return f"{taxa * 100:.1f}%".replace(".", ",")


def comparar(fila, base, hoje, boa=TAXA_BOA, atencao=TAXA_ATENCAO, abertas=None):
    """Fila de hoje contra o registro anterior -> dict: nao_feitas, novas (chaves) e semana (a linha da
    tabela de taxas: semana, fila_inicial, resolvidas, taxa, leitura). `abertas` = todas as tarefas abertas
    lidas (de qualquer data; padrão: a fila): uma tarefa da semana anterior que venceu e continua aberta é
    "não feita", mesmo fora do período do painel."""
    antes = set(base.get("fila") or [])
    agora = {e.chave for e in (fila if abertas is None else abertas)}
    resolvidas = len(antes - agora)
    taxa = resolvidas / len(antes) if antes else None
    inicio = date.fromisoformat(base["data"])
    return {"nao_feitas": agora & antes, "novas": {e.chave for e in fila} - antes,
            "semana": {"semana": f"{inicio:%d/%m}–{hoje:%d/%m}", "fila_inicial": len(antes), "resolvidas": resolvidas,
                       "taxa": taxa, "leitura": leitura(taxa, boa, atencao), "aproximada": False}}


# ---------------------------------------------------------------- histórico
def nome_registro(dia, simulado_=False):
    return f"painel-{'simulado-' if simulado_ else ''}{dia.isoformat()}.json"


def ler_base(ctx, tipos=TIPOS_TODAS, pessoas=()):
    """Registro mais recente com DIAS_MIN_BASE a DIAS_MAX_BASE dias de idade e com o mesmo conjunto de
    tipos (None se não há). No simulado, sem registro usa a fixture historico-anterior.json (como os prazos)."""
    base = _base_do_historico(ctx, tipos, pessoas)
    if base is None and ctx.simulado:
        try:
            base = json.loads(simulado.ler(ctx, "historico-anterior.json"))
        except (OSError, ValueError):
            base = None
    return base


def _base_do_historico(ctx, tipos=TIPOS_TODAS, pessoas=()):
    if ctx.historico is None:
        return None
    padrao = re.compile(r"^painel-" + ("simulado-" if ctx.simulado else "") + r"(\d{4}-\d{2}-\d{2})\.json$")
    candidatos = []
    try:
        arquivos = list(ctx.historico.iterdir())
    except OSError:
        return None
    for a in arquivos:
        m = padrao.match(a.name)
        if m:
            dia = date.fromisoformat(m.group(1))
            if DIAS_MIN_BASE <= (ctx.hoje - dia).days <= DIAS_MAX_BASE:
                candidatos.append((dia, a.name))
    for _, nome in sorted(candidatos, reverse=True):
        registro = ctx.ler_historico(nome)
        if (isinstance(registro, dict) and registro.get("data") and isinstance(registro.get("fila"), list)
                and registro.get("tipos", TIPOS_PECAS) == tipos
                and sorted(registro.get("pessoas") or []) == sorted(pessoas)):
            return registro
    return None


def registro(fila, hoje, semanas, tipos=TIPOS_TODAS, pessoas=()):
    """O que vai para historico/painel-<data>.json (fica só na máquina: orelha/saida/ é ignorada pelo git).
    `tipos` e `pessoas` (ORELHA_PAINEL_RESPONSAVEIS; vazio = todos) dizem que tarefas entraram na fila: só se
    compara com registro do mesmo conjunto."""
    return {"data": hoje.isoformat(), "total": len(fila), "fila": [e.chave for e in fila],
            "semanas": semanas[-12:], "tipos": tipos, "pessoas": sorted(pessoas)}


# ---------------------------------------------------------------- leitura
def _ler(ctx, dias_fila, avisos, ate=None):
    """TarefaLista das tarefas abertas com data para conclusão até `ate` (padrão hoje + dias_fila)."""
    cfg = ctx.cfg
    ctx.emitir("fase", fase="lendo_calendario")
    if ctx.simulado:
        return prazos.tarefas_da_lista(simulado.ler(ctx, "lista.html"), cfg.vios_base)
    desde = vios.data_br(cfg.valor("ORELHA_PRAZOS_DESDE", "01/01/2000")) or date(2000, 1, 1)
    maximo = cfg.valor("ORELHA_PRAZOS_MAX_PAGINAS", 60, int)
    fim = ate or ctx.hoje + timedelta(days=dias_fila)
    contador, listas = [0], []
    for a, b in prazos.janelas(desde, fim, ctx.hoje):
        parte = prazos.ler_periodo(ctx, "data_prevista", a, b, contador, maximo, avisos)
        if parte is None:
            avisos.append(f"parei no limite de {maximo} páginas da lista de tarefas (ORELHA_PRAZOS_MAX_PAGINAS): "
                          "o painel pode estar incompleto")
            break
        listas.append(parte)
    log.info("Painel: %d página(s) da lista de tarefas lidas", contador[0])
    return prazos.juntar_listas(listas)


# ---------------------------------------------------------------- função
def _plural(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def montar_dados(ctx, fila, ignoradas, leitura_avisos, cfg_painel, abertas=None):
    tipos = TIPOS_TODAS if cfg_painel.get("outras", True) else TIPOS_PECAS
    """Tudo o que o desenho precisa + o resumo. Devolve (dados, comparacao, semanas)."""
    hoje = ctx.hoje
    de, ate = periodo(ctx, cfg_painel.get("dias_fila", DIAS_FILA))
    escolhido = bool(getattr(ctx, "painel_de", None) or getattr(ctx, "painel_ate", None))
    agenda_periodo = (de, ate) if escolhido else ()
    base = ler_base(ctx, tipos, cfg_painel.get("permitidos") or ())
    comp = comparar(fila, base, hoje, cfg_painel["boa"], cfg_painel["atencao"], abertas) if base else None
    semanas = []
    if comp:
        semanas = [s for s in (base.get("semanas") or []) if isinstance(s, dict)
                   and {"semana", "fila_inicial", "resolvidas"} <= set(s)][-(SEMANAS_NA_TABELA - 1):] + [comp["semana"]]
    cargas = carga(fila, cfg_painel["urgente_alto"])
    vencidas = sum(1 for e in fila if e.dias < 0)
    topo = next((c for c in cargas if c["nome"] != SEM_RESPONSAVEL), None)
    cartoes = [(len(fila), "Fila total", "neutro"),
               (len(comp["nao_feitas"]) if comp else "—", "Não feitas", "ruim"),
               (len(comp["novas"]) if comp else "—", "Novas", "info"),
               (topo["total"] if topo else "—", f"Carga {topo['nome'].split()[0]}" if topo else "Maior carga", "ruim"),
               (vencidas, "Vencidas", "ruim" if vencidas else "neutro")]
    if comp:
        itens = sorted((e for e in (fila if abertas is None else abertas) if e.chave in comp["nao_feitas"]),
                       key=lambda e: (e.dias, agenda.dobrar(e.responsavel), agenda.dobrar(e.tarefa)))
        n = len(itens)
        titulo = (f"NÃO FEITAS — {n} tarefa{'s' if n != 1 else ''} que permaneceram da semana anterior"
                  if n else "NÃO FEITAS — nenhuma tarefa permaneceu da semana anterior")
    else:
        itens = fila
        conjunto = "da equipe" if tipos == TIPOS_TODAS else "de peças e audiências"
        titulo = f"FILA ABERTA — {_plural(len(fila), 'tarefa', 'tarefas')} {conjunto} (sem semana anterior para comparar)"
    avisos = list(leitura_avisos)
    if ignoradas.get("sem_data"):
        avisos.append(f"{_plural(ignoradas['sem_data'], 'tarefa', 'tarefas')} sem data para conclusão nem limite ficaram de fora")
    sem_dono = sum(1 for e in fila if e.responsavel == SEM_RESPONSAVEL)
    if sem_dono:
        avisos.append(f"{_plural(sem_dono, 'tarefa', 'tarefas')} sem responsável na leitura")
    dados = {
        # período do painel = o escolhido na página ou, sem escolha, do dia do pedido até dias_fila dias depois
        "inicio": de, "fim": ate, "gerado_em": datetime.now(), "cartoes": cartoes,
        "semanas": semanas,
        "nota_semanas": ("Resolvidas = tarefas que estavam na fila da leitura anterior e não aparecem mais abertas no VIOS "
                         "(concluídas ou canceladas: o Orelha só enxerga as abertas)." if semanas else ""),
        "tendencia": " → ".join(_pct(s["taxa"]) for s in semanas if s.get("taxa") is not None) if len(semanas) > 1 else "",
        "carga": cargas, "outras": tipos == TIPOS_TODAS,
        "regra": ({"grupo": [g.split()[0] for g in cfg_painel["grupo"]], "alvo": cfg_painel["alvo"]}
                  if cfg_painel.get("grupo") and cfg_painel.get("alvo") else None), "agenda": agenda_audiencias(fila, hoje, cfg_painel["dias_agenda"], *agenda_periodo),
        "dias_agenda": cfg_painel["dias_agenda"], "lista_titulo": titulo,
        "agenda_titulo": (f"Agenda de audiências — {de:%d/%m} a {ate:%d/%m} (comparecimento obrigatório)"
                          if escolhido else ""),
        "lista": [{"processo": e.processo, "faixa": faixa(e.dias)[0], "situacao": faixa(e.dias)[1],
                   "responsavel": e.responsavel, "tarefa": e.tarefa} for e in itens],
        "avisos": avisos}
    return dados, comp, semanas


def executar(ctx):
    cfg = ctx.cfg
    cfg_painel = {"dias_fila": cfg.valor("ORELHA_PAINEL_DIAS_FILA", DIAS_FILA, int),
                  "dias_agenda": cfg.valor("ORELHA_PAINEL_DIAS_AGENDA", DIAS_AGENDA, int),
                  "urgente_alto": cfg.valor("ORELHA_PAINEL_URGENTE_ALTO", URGENTE_ALTO, int),
                  "boa": cfg.valor("ORELHA_PAINEL_TAXA_BOA", TAXA_BOA, float),
                  "atencao": cfg.valor("ORELHA_PAINEL_TAXA_ATENCAO", TAXA_ATENCAO, float),
                  "outras": cfg.valor("ORELHA_PAINEL_OUTRAS", True, bool),
                  "permitidos": tuple(cfg.valor("ORELHA_PAINEL_RESPONSAVEIS", "", "lista")),
                  "grupo": tuple(cfg.valor("ORELHA_PAINEL_GRUPO_CIVEL", "", "lista")),
                  "alvo": cfg.valor("ORELHA_PAINEL_GRUPO_CIVEL_PARA", "", str).strip()}
    termos_peca = cfg.valor("ORELHA_PAINEL_TERMOS_PECA", "MINUTAR", "lista")
    termos_audiencia = cfg.valor("ORELHA_PAINEL_TERMOS_AUDIENCIA", "AUDIÊNCIA", "lista")

    leitura_avisos = []
    de, ate = periodo(ctx, cfg_painel["dias_fila"])
    log.info("Painel: período de %s a %s", f"{de:%d/%m/%Y}", f"{ate:%d/%m/%Y}")
    tarefas = _ler(ctx, cfg_painel["dias_fila"], leitura_avisos, ate)
    pessoas = {"permitidos": cfg_painel["permitidos"], "grupo": cfg_painel["grupo"], "alvo": cfg_painel["alvo"]}
    fila, ignoradas = montar_fila(tarefas, ctx.hoje, termos_peca, termos_audiencia, cfg_painel["dias_fila"], de, ate,
                                  cfg_painel["outras"], **pessoas)
    # todas as abertas lidas (qualquer data): só para saber o que da semana anterior continua aberto
    abertas, _ = montar_fila(tarefas, ctx.hoje, termos_peca, termos_audiencia, de=date.min, ate=date.max,
                             outras=cfg_painel["outras"], **pessoas)
    log.info("Painel: %d tarefa(s) no período, %d aberta(s) no total", len(fila), len(abertas))
    if ignoradas["fora_da_lista"]:
        # nomes só no log (não no PDF): para notar advogado novo que precise entrar em ORELHA_PAINEL_RESPONSAVEIS
        log.info("Painel: %d tarefa(s) de gente fora de ORELHA_PAINEL_RESPONSAVEIS ficaram de fora: %s",
                 ignoradas["fora_da_lista"], ", ".join(f"{n} ({q})" for n, q in sorted(
                     ignoradas["nomes_fora"].items(), key=lambda x: (-x[1], x[0]))))
    dados, comp, semanas = montar_dados(ctx, fila, ignoradas, leitura_avisos, cfg_painel, abertas)

    completa = not leitura_avisos and bool(fila)
    if completa and de != ctx.hoje:
        # a comparação semana a semana parte de hoje: um período que começa em outro dia não vira base
        completa = False
        dados["avisos"].append(f"período escolhido começa em {de:%d/%m}, não hoje: este painel não entra na "
                               "comparação com a semana seguinte")
    elif completa:
        try:
            ctx.gravar_historico(nome_registro(ctx.hoje, ctx.simulado),
                                 registro(fila, ctx.hoje, semanas, TIPOS_TODAS if cfg_painel["outras"] else TIPOS_PECAS,
                                          cfg_painel["permitidos"]))
        except OSError as e:
            dados["avisos"].append(f"não consegui gravar o registro da semana ({e.__class__.__name__}): "
                                   "a próxima edição não terá com o que comparar")
    else:
        dados["avisos"].append("leitura incompleta ou sem tarefas: o registro desta semana NÃO foi gravado, "
                               "para não distorcer a comparação da próxima")

    info = desenho.gerar(dados, ctx.saida, pdf=getattr(ctx, "pdf", True), driver=ctx.driver)
    avisos = list(dados["avisos"])
    if info["pdf"]:
        log.info("Painel semanal: %s", info["pdf"])
    elif getattr(ctx, "pdf", True):
        avisos.append(f"PDF do painel não gerado ({info['erro_pdf']}): fica o HTML, que também imprime")

    vencidas = sum(1 for e in fila if e.dias < 0)
    numeros = {"fila": len(fila), "vencidas": vencidas, "urgentes_7d": sum(1 for e in fila if e.dias <= 7),
               "audiencias_agenda": len(dados["agenda"]), "destaque": len(fila)}
    if comp:
        numeros.update({"nao_feitas": len(comp["nao_feitas"]), "novas": len(comp["novas"]),
                        "resolvidas": comp["semana"]["resolvidas"]})
    resumo = (f"Painel semanal gerado: {_plural(len(fila), 'tarefa', 'tarefas')} na fila, {vencidas} vencida"
              f"{'' if vencidas == 1 else 's'}" + (f", {numeros['novas']} nova(s) e {numeros['nao_feitas']} não feita(s)"
                                                    if comp else " (1ª edição, sem comparação)")
              + f". Arquivo: {info['pdf'].name if info['pdf'] else info['html'].name}.")
    return Secao(chave="painel", titulo=TITULO, resumo=resumo, itens=[], numeros=numeros, avisos=avisos)
