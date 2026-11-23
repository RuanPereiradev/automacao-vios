"""Relatório de conferência do envio automático (tela /automatico do Sam), com foco nos prazos.

Para cada intimação analisada: o que a IA leu, as datas calculadas, a conta de cada prazo refeita
por fora (a partir dos dias que a IA leu no texto), a tarefa da análise ao lado da gravada no VIOS
e os pontos de atenção para a pessoa que confere.

O "dia de envio" é o dia em que as tarefas foram gravadas (ou barradas) no VIOS: lancamentos.json
e automatico_resultados.json guardam o "quando" de cada CI. Uma análise do dia inteiro
(saida/analise_<dia>.json) entra no dia de envio da maioria das CIs dela; sem nenhum envio, no dia
em que a análise foi feita.
"""
import json
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from bot import prazos

DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def data(texto):
    try:
        return datetime.strptime(texto or "", "%d/%m/%Y").date()
    except ValueError:
        return None


def br(dia):
    return f"{dia:%d/%m/%Y}" if dia else ""


def semana(texto):
    """"ter" para "10/11/2026"; vazio se não for data."""
    dia = data(texto)
    return DIAS_SEMANA[dia.weekday()] if dia else ""


def curto(nome):
    """Nome da tarefa sem a área e o ano, para a tabela: "ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO"."""
    return re.sub(r"\s*\((TRABALHISTA|EXECUÇÃO|CÍVEL|PREVIDENCIÁRIO)\)\s*(\d{4})?\s*$", "",
                  re.sub(r"\s+\d{4}$", "", nome or ""))


# ---- dias de envio ---------------------------------------------------------------------------

def dias_de_envio(pasta_saida, registro, anotados):
    """{dia de envio (AAAA-MM-DD): {"analises": [dias das análises], "enviado": bool}}, do envio mais novo
    para o mais antigo. "enviado" falso: nenhuma CI dessas análises chegou a ser lançada (o dia é o da análise)."""
    por_dia, enviados = {}, set()
    for arquivo in Path(pasta_saida).glob("analise_*.json"):
        if "_ci-" in arquivo.name:  # análise de CIs avulsas: as CIs já estão na análise do dia
            continue
        try:
            analises = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        quandos = Counter()
        for a in analises:
            quando = (registro.get(a.get("ci"), {}) or anotados.get(a.get("ci"), {})).get("quando", "")
            dia = data(quando[:10])
            if dia:
                quandos[dia] += 1
        dia_envio = quandos.most_common(1)[0][0] if quandos else date.fromtimestamp(arquivo.stat().st_mtime)
        por_dia.setdefault(dia_envio.isoformat(), []).append(arquivo.stem[len("analise_"):])
        if quandos:
            enviados.add(dia_envio.isoformat())
    return {d: {"analises": sorted(por_dia[d]), "enviado": d in enviados} for d in sorted(por_dia, reverse=True)}


# ---- conta independente dos prazos -----------------------------------------------------------
# Mesma regra da contagem simplificada (bot/prazos.py), escrita de novo de propósito: o prazo
# começa no 1º dia útil após a publicação, só sábado e domingo ficam de fora.

def _util(dia):
    return dia.weekday() < 5


def _proximo_util(dia):
    dia += timedelta(days=1)
    while not _util(dia):
        dia += timedelta(days=1)
    return dia


def _fatal(publicacao, dias, corridos=False):
    dia, contados = _proximo_util(publicacao), 0
    while True:
        if corridos or _util(dia):
            contados += 1
            if contados == dias:
                break
        dia += timedelta(days=1)
    while not _util(dia):
        dia += timedelta(days=1)
    return dia


def _menos2(dia):
    for _ in range(2):
        dia -= timedelta(days=1)
        while not _util(dia):
            dia -= timedelta(days=1)
    return dia


def _feriados(*anos):
    todos = {}
    for ano in anos:
        todos.update(prazos.nacionais(ano))
    return todos


def usa_simplificada(a):
    """A análise contou os prazos pela contagem simplificada? As de antes de 10/11/2026 usavam o calendário
    de feriados de cada tribunal ("Justiça Federal — SOBRAL/CE"): a conta refeita aqui não vale para elas."""
    return (a.get("calendario") or "").startswith(prazos.AVISO_SIMPLIFICADA.split(";")[0])


def conferir_contas(a):
    """[(bateu?, texto)] da conta refeita: prazo principal, D-2, embargos e recurso.
    Só para análise feita pela contagem simplificada (a mesma regra da conta daqui)."""
    publicacao = data(a.get("publicacao"))
    ia = a.get("ia") or {}
    contas = []
    if not publicacao or not usa_simplificada(a):
        return contas
    pr = ia.get("prazo") or {}
    if pr.get("dias"):
        corridos = pr.get("contagem") == "CORRIDOS"
        fatal = _fatal(publicacao, pr["dias"], corridos)
        ok = br(fatal) == a.get("prazo_fatal")
        contas.append((ok, f"Prazo de {pr['dias']} dias {'corridos' if corridos else 'úteis'} a partir da publicação "
                           f"({a['publicacao']}): fatal {br(fatal)}, D-2 {br(_menos2(fatal))}"
                           + ("" if ok else f" — a análise diz {a.get('prazo_fatal') or 'sem data'}")))
        if ok and a.get("prazo_d2") != br(_menos2(fatal)):
            contas.append((False, f"D-2 da análise ({a.get('prazo_d2')}) diferente do conferido ({br(_menos2(fatal))})"))
    for chave, rotulo in (("embargos", "Embargos"), ("recurso", "Recurso")):
        info = ia.get(chave) or {}
        if data(a.get(chave)) and info.get("dias"):
            fatal = _fatal(publicacao, info["dias"])
            ok = br(_menos2(fatal)) == a[chave]
            nome = f" ({a['recurso_nome']})" if chave == "recurso" and a.get("recurso_nome") else ""
            contas.append((ok, f"{rotulo}{nome}: {info['dias']} dias úteis → fatal {br(fatal)}, "
                               f"linha da observação em D-2 = {br(_menos2(fatal))}"
                               + ("" if ok else f" — a análise diz {a[chave]}")))
    return contas


# ---- cada intimação ----------------------------------------------------------------------------

def _mesma_tarefa(nome_analise, nome_vios):
    return nome_vios.upper().startswith(nome_analise.upper()[:40])


def comparar_tarefas(a, gravadas, quando):
    """[(tarefa da análise, tarefa gravada ou None)] e as observações sobre as datas."""
    sobra = list(gravadas or [])
    pares, notas, atencao = [], [], []
    for t in a.get("tarefas", []):
        v = next((g for g in sobra if _mesma_tarefa(t.get("nome", ""), g.get("tarefa", ""))), None)
        if v:
            sobra.remove(v)
        pares.append((t, v))
        no_vios, na_analise = data(v["data"]) if v else None, data(t.get("data_tarefa"))
        nome = t.get("nome", "").split(" (")[0]
        if no_vios and na_analise and no_vios != na_analise:
            if t.get("tipo_data") == "MESMO_DIA" and no_vios == _proximo_util(na_analise):
                notas.append(f"{nome}: análise {t['data_tarefa']} → VIOS {v['data']} (corte das 12h: lançada em "
                             f"{quando}, foi para o próximo dia útil)")
            else:
                atencao.append(f"{t.get('nome')}: data no VIOS ({v['data']}) diferente da análise ({t['data_tarefa']}).")
        if v and t.get("tipo_data") == "SEM_DATA":
            notas.append(f"{nome}: sem prazo; no VIOS em {v['data']} (dia do lançamento, com o corte das 12h)")
    for g in sobra:
        pares.append(({"nome": g.get("tarefa", ""), "tipo_data": "", "data_tarefa": "", "descricao": ""}, g))
    return pares, notas, atencao


def pontos_de_atencao(a, pares, lancada):
    """O que a pessoa deve olhar: tarefa em feriado ou depois do fatal, ciência com prazo, não lançada..."""
    atencao = []
    fatal = data(a.get("prazo_fatal"))
    datas = [data(v["data"]) if v else data(t.get("data_tarefa")) for t, v in pares]
    feriados = _feriados(*{d.year for d in datas + [fatal] if d})
    pr = (a.get("ia") or {}).get("prazo") or {}
    for (t, v), alvo in zip(pares, datas):
        if alvo in feriados:
            atencao.append(f"A tarefa {t.get('nome')} está em {br(alvo)}, feriado nacional ({feriados[alvo]}).")
        if alvo and fatal and alvo > fatal:
            atencao.append(f"A tarefa {t.get('nome')} ({br(alvo)}) fica depois do prazo fatal ({a['prazo_fatal']}).")
        if t.get("nome", "").startswith("CIÊNCIA") and fatal:
            atencao.append(f"Tarefa de CIÊNCIA, mas a análise achou prazo de {pr.get('dias')} dias (fatal "
                           f"{a['prazo_fatal']}, trecho: \"{(a.get('prazo_trecho') or '')[:140]}\"). "
                           "Conferir se o prazo é do cliente.")
    alertas = a.get("alertas") or []
    if a.get("prazo_trecho") and not fatal and not any(al.startswith("Há prazo no texto") for al in alertas):
        atencao.append(f"Há prazo no texto sem data calculada: \"{a['prazo_trecho'][:160]}\".")
    if not lancada:
        proximas = [d for d in (data(a.get("prazo_d2")), data(a.get("embargos")), data(a.get("recurso"))) if d] or \
                   [d for d in (data(t.get("data_tarefa")) for t, _ in pares) if d]
        if proximas:
            p = min(proximas)
            atencao.insert(0, f"Não foi lançada. Data de prazo mais próxima: {br(p)} ({DIAS_SEMANA[p.weekday()]}). "
                              "Conferir se a Controladoria já lançou à mão.")
    atencao += ["Alerta da análise: " + al for al in alertas]
    return atencao


def feriados_no_periodo(linhas):
    """Feriados nacionais em dia de semana entre a publicação e o último vencimento do dia: pela contagem
    simplificada eles contam como dia útil (a data fica 1 dia útil antes do vencimento real)."""
    linhas = [l for l in linhas if usa_simplificada(l)]  # na contagem por tribunal o feriado já fica de fora
    inicio = [d for l in linhas if (d := data(l["publicacao"]))]
    fim = [d for l in linhas for d in (data(l["prazo_fatal"]), data(l["embargos"]), data(l["recurso"])) if d]
    if not inicio or not fim:
        return []
    de, ate = min(inicio), max(fim) + timedelta(days=10)  # o recurso guarda o D-2: o fatal vem depois
    feriados = _feriados(*range(de.year, ate.year + 1))
    return [(br(d), DIAS_SEMANA[d.weekday()], nome) for d, nome in sorted(feriados.items())
            if de < d <= ate and _util(d)]
