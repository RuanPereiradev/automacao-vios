"""Painel semanal de peças e audiências (PDF no papel timbrado do escritório).

Roda à parte do relatório do dia (`--funcoes painel`, uma vez por semana) e gera, em
saida/<AAAA-MM-DD>/, o painel-semanal.html e o painel-semanal.pdf (modelo: "2026_PAINEL_SEMANAL";
moldura: papel timbrado, nucleo/timbrado.py). Não entra no relatório do dia (RELATORIO_DIARIO = False).

Fila = tarefas NÃO concluídas da equipe toda, de peças (tipo começa com ORELHA_PAINEL_TERMOS_PECA,
padrão "MINUTAR") e audiências (começa com ORELHA_PAINEL_TERMOS_AUDIENCIA, padrão "AUDIÊNCIA"), com data
para conclusão (ou, sem ela, a limite) até hoje + ORELHA_PAINEL_DIAS_FILA dias (padrão 7), lidas da
lista de tarefas do VIOS (a mesma leitura dos prazos, só por GET). Tarefas canceladas ficam de fora.

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

TITULO = "Painel semanal (peças e audiências)"
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


@dataclass
class Entrada:
    """Uma tarefa da fila do painel."""
    chave: str
    categoria: str       # "peca" | "audiencia"
    responsavel: str
    processo: str
    tarefa: str
    prazo: date
    dias: int            # até o prazo; negativo = vencida
    hora: str = ""
    link: str = ""


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


def categoria(tarefa, termos_peca, termos_audiencia):
    """"audiencia", "peca" ou "" (outros tipos de tarefa não entram no painel). Conta só se o TIPO
    COMEÇA com o termo ("INFORMAR AUDIÊNCIA" é tarefa sobre a audiência, não a audiência)."""
    texto = re.sub(r"^C:\s*", "", agenda.dobrar(tarefa.tipo or tarefa.titulo).strip())
    for nome, termos in (("audiencia", termos_audiencia), ("peca", termos_peca)):
        if any(t and texto.startswith(agenda.dobrar(t)) for t in termos):
            return nome
    return ""


def _chave(t):
    m = _RE_PXE.search(t.link or "")
    return m.group(1) if m else (t.link or f"{t.processo}|{t.tipo}|{t.responsavel}|{t.conclusao}")


def periodo(ctx, dias_fila=DIAS_FILA):
    """(de, ate) do painel: o escolhido na página /orelha (--painel-de/--painel-ate) ou, sem escolha, de hoje
    até hoje + dias_fila. Só o fim escolhido: começa hoje. Só o início: vai até início + dias_fila."""
    de = getattr(ctx, "painel_de", None) or ctx.hoje
    ate = getattr(ctx, "painel_ate", None) or de + timedelta(days=dias_fila)
    return de, max(ate, de)


def montar_fila(tarefas, hoje, termos_peca, termos_audiencia, dias_fila=DIAS_FILA, de=None, ate=None):
    """[TarefaLista] -> ([Entrada], ignoradas). Sem repetir a mesma tarefa; fora as concluídas, as
    canceladas, as sem data, as de outros tipos e as com prazo fora do período. Período = de `de` (padrão
    hoje) até `ate` (padrão hoje + dias_fila); as vencidas que continuam abertas (prazo antes de hoje)
    entram sempre: são as "não feitas" da comparação."""
    de = de or hoje
    ate = ate or hoje + timedelta(days=dias_fila)
    vistas, fila, ignoradas = set(), [], {"sem_data": 0}
    for t in tarefas:
        cat = categoria(t, termos_peca, termos_audiencia)
        if not cat or t.concluida or "CANCELAD" in agenda.dobrar(f"{t.etiqueta} {t.tipo}"):
            continue
        prazo = t.conclusao or t.limite
        if prazo is None:
            ignoradas["sem_data"] += 1
            continue
        dias = (prazo - hoje).days
        chave = _chave(t)
        if prazo > ate or (hoje <= prazo < de) or chave in vistas:
            continue
        vistas.add(chave)
        dono = nome_proprio(prazos.responsavel_principal(t.responsavel)) or SEM_RESPONSAVEL
        fila.append(Entrada(chave=chave, categoria=cat, responsavel=dono, processo=t.processo, tarefa=t.tipo or t.titulo,
                            prazo=prazo, dias=dias, hora=t.hora, link=t.link))
    fila.sort(key=lambda e: (e.dias, agenda.dobrar(e.responsavel), agenda.dobrar(e.tarefa)))
    return fila, ignoradas


def carga(fila, urgente_alto=URGENTE_ALTO):
    """Peças, audiências, total, vencidas e urgentes (prazo em até 7 dias, vencidas incluídas) por advogado.
    Mais carregado primeiro; "sem responsável" por último. `destaque` = urgentes >= urgente_alto."""
    por = {}
    for e in fila:
        c = por.setdefault(e.responsavel, {"nome": e.responsavel, "pecas": 0, "audiencias": 0, "total": 0,
                                           "vencidas": 0, "urgente": 0})
        c["pecas" if e.categoria == "peca" else "audiencias"] += 1
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


def comparar(fila, base, hoje, boa=TAXA_BOA, atencao=TAXA_ATENCAO):
    """Fila de hoje contra o registro anterior -> dict: nao_feitas, novas (chaves) e semana (a linha da
    tabela de taxas: semana, fila_inicial, resolvidas, taxa, leitura)."""
    antes = set(base.get("fila") or [])
    agora = {e.chave for e in fila}
    resolvidas = len(antes - agora)
    taxa = resolvidas / len(antes) if antes else None
    inicio = date.fromisoformat(base["data"])
    return {"nao_feitas": agora & antes, "novas": agora - antes,
            "semana": {"semana": f"{inicio:%d/%m}–{hoje:%d/%m}", "fila_inicial": len(antes), "resolvidas": resolvidas,
                       "taxa": taxa, "leitura": leitura(taxa, boa, atencao), "aproximada": False}}


# ---------------------------------------------------------------- histórico
def nome_registro(dia, simulado_=False):
    return f"painel-{'simulado-' if simulado_ else ''}{dia.isoformat()}.json"


def ler_base(ctx):
    """Registro mais recente com DIAS_MIN_BASE a DIAS_MAX_BASE dias de idade (None se não há). No
    simulado, sem registro usa a fixture historico-anterior.json (como os prazos)."""
    base = _base_do_historico(ctx)
    if base is None and ctx.simulado:
        try:
            base = json.loads(simulado.ler(ctx, "historico-anterior.json"))
        except (OSError, ValueError):
            base = None
    return base


def _base_do_historico(ctx):
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
        if isinstance(registro, dict) and registro.get("data") and isinstance(registro.get("fila"), list):
            return registro
    return None


def registro(fila, hoje, semanas):
    """O que vai para historico/painel-<data>.json (fica só na máquina: orelha/saida/ é ignorada pelo git)."""
    return {"data": hoje.isoformat(), "total": len(fila), "fila": [e.chave for e in fila],
            "semanas": semanas[-12:]}


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


def montar_dados(ctx, fila, ignoradas, leitura_avisos, cfg_painel):
    """Tudo o que o desenho precisa + o resumo. Devolve (dados, comparacao, semanas)."""
    hoje = ctx.hoje
    de, ate = periodo(ctx, cfg_painel.get("dias_fila", DIAS_FILA))
    escolhido = bool(getattr(ctx, "painel_de", None) or getattr(ctx, "painel_ate", None))
    agenda_periodo = (de, ate) if escolhido else ()
    base = ler_base(ctx)
    comp = comparar(fila, base, hoje, cfg_painel["boa"], cfg_painel["atencao"]) if base else None
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
        itens = [e for e in fila if e.chave in comp["nao_feitas"]]
        n = len(itens)
        titulo = (f"NÃO FEITAS — {n} tarefa{'s' if n != 1 else ''} que permaneceram da semana anterior"
                  if n else "NÃO FEITAS — nenhuma tarefa permaneceu da semana anterior")
    else:
        itens = fila
        titulo = f"FILA ABERTA — {_plural(len(fila), 'tarefa', 'tarefas')} de peças e audiências (sem semana anterior para comparar)"
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
        "carga": cargas, "agenda": agenda_audiencias(fila, hoje, cfg_painel["dias_agenda"], *agenda_periodo),
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
                  "atencao": cfg.valor("ORELHA_PAINEL_TAXA_ATENCAO", TAXA_ATENCAO, float)}
    termos_peca = cfg.valor("ORELHA_PAINEL_TERMOS_PECA", "MINUTAR", "lista")
    termos_audiencia = cfg.valor("ORELHA_PAINEL_TERMOS_AUDIENCIA", "AUDIÊNCIA", "lista")

    leitura_avisos = []
    de, ate = periodo(ctx, cfg_painel["dias_fila"])
    log.info("Painel: período de %s a %s", f"{de:%d/%m/%Y}", f"{ate:%d/%m/%Y}")
    tarefas = _ler(ctx, cfg_painel["dias_fila"], leitura_avisos, ate)
    fila, ignoradas = montar_fila(tarefas, ctx.hoje, termos_peca, termos_audiencia, cfg_painel["dias_fila"], de, ate)
    dados, comp, semanas = montar_dados(ctx, fila, ignoradas, leitura_avisos, cfg_painel)

    completa = not leitura_avisos and bool(fila)
    if completa and de != ctx.hoje:
        # a comparação semana a semana parte de hoje: um período que começa em outro dia não vira base
        completa = False
        dados["avisos"].append(f"período escolhido começa em {de:%d/%m}, não hoje: este painel não entra na "
                               "comparação com a semana seguinte")
    elif completa:
        try:
            ctx.gravar_historico(nome_registro(ctx.hoje, ctx.simulado), registro(fila, ctx.hoje, semanas))
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
