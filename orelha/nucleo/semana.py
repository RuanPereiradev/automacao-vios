"""Atrasadas da semana, dia a dia: orelha/saida/<AAAA-MM-DD>/semana.html.

Feita pela função prazos, com a mesma leitura do VIOS (não lê de novo). Uma página só, sem JavaScript,
no estilo do relatório do dia (nucleo/relatorio.py):
  - a semana começa na segunda-feira da semana de ontem (na segunda-feira, mostra a semana passada
    inteira e hoje); cada dia é um grupo fechado com o total de tarefas que venciam nele e continuam
    abertas, e uma barra do tamanho do dia; clica no dia e abrem as tarefas. Sábado e domingo só
    aparecem se tiverem tarefa. Hoje mostra as que vencem hoje (ainda dá para fazer);
  - "Antes desta semana": as atrasadas mais antigas, nos mesmos grupos do relatório do dia;
  - "Por responsável": quantas de cada pessoa venceram nesta semana e quantas são de antes.
"""
import html as html_mod
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from nucleo import relatorio

DIAS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
SEM_RESPONSAVEL = "Sem responsável identificado"


def _e(texto):
    return html_mod.escape(str(texto if texto is not None else ""), quote=True)


def inicio_da_semana(hoje):
    """Segunda-feira da semana de ontem: na segunda, a semana passada; nos outros dias, a atual."""
    ontem = hoje - timedelta(days=1)
    return ontem - timedelta(days=ontem.weekday())


def responsaveis(item):
    """Todos os responsáveis, do detalhe do item ("responsável: Ana, Bruno · para conclusão ..." -> [Ana, Bruno])."""
    primeiro = (item.detalhe or "").split(" · ")[0]
    if not primeiro.startswith("responsável: "):
        return [SEM_RESPONSAVEL]
    saida = []
    for nome in re.split(r"[,;/]| e ", primeiro[len("responsável: "):]):
        nome = nome.strip()
        if nome and nome not in saida:
            saida.append(nome)
    return saida or [SEM_RESPONSAVEL]


def responsavel(item):
    """Primeiro responsável, do detalhe do item ("responsável: Ana, Bruno · para conclusão ...")."""
    return responsaveis(item)[0]


def separar(itens, hoje):
    """(dias, hoje_itens, antes): dias = [(data, [atrasadas que venciam nela])] de segunda a ontem;
    hoje_itens = as que vencem hoje; antes = atrasadas de antes da semana, na ordem do placar."""
    inicio = inicio_da_semana(hoje)
    atrasadas = [i for i in itens if i.nivel != "info" and i.dia is not None]
    dias = []
    d = inicio
    while d < hoje:
        dias.append((d, [i for i in atrasadas if i.dia == d]))
        d += timedelta(days=1)
    hoje_itens = [i for i in itens if i.nivel == "info"]
    antes = [i for i in atrasadas if i.dia < inicio]
    return dias, hoje_itens, antes


def montar_html(itens, numeros, hoje, simulado=False, gerado_em=None):
    gerado_em = gerado_em or datetime.now()
    inicio = inicio_da_semana(hoje)
    dias, hoje_itens, antes = separar(itens, hoje)
    da_semana = [i for _, lista in dias for i in lista]
    graves = sum(1 for i in da_semana if i.nivel == "grave")
    h = ['<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Orelha · semana de {inicio:%d/%m}</title><style>{relatorio.CSS}</style></head><body><main>']
    h.append('<header class="topo"><div class="selo" aria-hidden="true">O</div><div>'
             f'<h1>Atrasadas da semana · {inicio:%d/%m} a {hoje:%d/%m/%Y}</h1>'
             f'<div class="suave">Feito pelo Orelha em {gerado_em:%d/%m/%Y às %H:%M} · '
             'o Orelha só lê o VIOS: nada foi alterado lá.</div></div></header>')
    if simulado:
        h.append('<div class="faixa">Modo de demonstração: dados fictícios, não vieram do VIOS.</div>')
    frase = (f"{relatorio._qtd(len(da_semana), 'tarefa venceu', 'tarefas venceram')} nesta semana e "
             f"{'continua aberta' if len(da_semana) == 1 else 'continuam abertas'}")
    if graves:
        frase += f" ({graves} há mais de {numeros.get('dias_grave', 7)} dias)"
    frase += f"; {relatorio._qtd(len(antes), 'é', 'são')} de antes da semana"
    frase += f" e {relatorio._qtd(len(hoje_itens), 'vence', 'vencem')} hoje."
    h.append(f'<p class="resumo" style="margin-top:16px">{_e(frase)}</p>')

    h.append('<section class="secao"><h2>Dia a dia</h2>'
             '<p class="suave">Cada dia mostra as tarefas que venciam nele e ainda não foram concluídas. '
             'Clique no dia para ver as tarefas.</p>')
    maior = max([len(lista) for _, lista in dias] + [len(hoje_itens), 1])
    for dia, lista in dias:
        if dia.weekday() >= 5 and not lista:
            continue
        atras = (hoje - dia).days
        rotulo = f"{DIAS[dia.weekday()]}, {dia:%d/%m}" + (" · ontem" if atras == 1 else f" · há {atras} dias")
        h.append(relatorio.grupo_html(rotulo, lista, maior, ancora=f"dia-{dia.isoformat()}"))
    h.append(relatorio.grupo_html(f"Hoje, {DIAS[hoje.weekday()].lower()} {hoje:%d/%m} · vencem hoje (ainda dá tempo)",
                                  hoje_itens, maior, ancora="hoje"))
    h.append("</section>")

    h.append('<section class="secao"><h2>Antes desta semana</h2>')
    if antes:
        grupos = relatorio._grupos(antes)
        maior_antes = max(len(i) for _, i in grupos)
        dentro = '<div class="dentro">' + "".join(relatorio.grupo_html(g, i, maior_antes) for g, i in grupos) + "</div>"
        h.append(f'<p class="suave">Tarefas que venceram antes de {inicio:%d/%m} e continuam abertas.</p>')
        h.append(relatorio.grupo_html("Todas as de antes da semana", antes, dentro_html=dentro))
    else:
        h.append('<p class="vazio">Nenhuma tarefa atrasada de antes da semana.</p>')
    h.append("</section>")

    # tarefa com vários responsáveis conta para cada um deles
    por = {}
    for i in da_semana:
        for nome in responsaveis(i):
            por.setdefault(nome, [0, 0])[0] += 1
    for i in antes:
        for nome in responsaveis(i):
            por.setdefault(nome, [0, 0])[1] += 1
    linhas = sorted(([n, a, b, a + b] for n, (a, b) in por.items()),
                    key=lambda l: (l[0] == SEM_RESPONSAVEL, -l[1], -l[3], l[0]))
    h.append('<section class="secao"><h2>Por responsável</h2>')
    if linhas:
        h.append(relatorio.quadro_html({"titulo": "Atrasadas por responsável (tarefa com mais de um responsável conta para cada um)",
                                         "colunas": ["Responsável", "Desta semana", "De antes", "Total"],
                                         "linhas": linhas}))
    else:
        h.append('<p class="vazio">Ninguém com tarefa atrasada.</p>')
    h.append("</section>")
    h.append('<footer><p><span class="chip grave">Urgente</span> atrasada há mais de '
             f'{numeros.get("dias_grave", 7)} dias · <span class="chip atencao">Atenção</span> atrasada há menos · '
             '<span class="chip info">Para saber</span> vence hoje.</p>'
             '<p>Os dados são uma leitura do VIOS no horário acima. Confira no VIOS antes de agir.</p></footer>')
    h.append("</main></body></html>")
    return "\n".join(h)


def gerar(itens, numeros, hoje, pasta, simulado=False, gerado_em=None):
    """Escreve semana.html em `pasta` e devolve o caminho."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / "semana.html"
    tmp = caminho.with_name(caminho.name + ".tmp")
    tmp.write_text(montar_html(itens, numeros, hoje, simulado, gerado_em), encoding="utf-8")
    os.replace(tmp, caminho)
    return caminho
