"""Jarvis — quanto a IA gastou em cada relatório, por cliente (Grupo Cliente), lendo o logs/bot.log.

Só lê o log: não entra no VIOS, não chama a IA, não gasta nada. Serve também para os relatórios antigos.
O log tem, para cada processo analisado, o gasto ACUMULADO da execução ("GRUPO: 3/40 CI 123 — 5 tarefas
— gasto US$ 0.07"); o gasto de um relatório é o acumulado no fim dele menos o de antes dele começar
(numa execução com vários grupos, o 2º começa de onde o 1º parou).

uso (dentro de jarvis/):
  .venv/bin/python gastos.py            resumo por cliente + cada relatório
  .venv/bin/python gastos.py --mes 2026-11   só os relatórios daquele mês
  .venv/bin/python gastos.py --log OUTRO.log
"""
import re
import sys
from datetime import datetime
from pathlib import Path

LOG = Path(__file__).resolve().parent / "logs" / "bot.log"
_PROC = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})\S* \[INFO\] (.+?): (\d+)/(\d+) CI \S+ — \d+ tarefas — gasto US\$ ([\d.]+)")
_FIM = re.compile(r"\[INFO\] (Concluído:|Execução iniciada:)")  # fim de uma execução ou começo de outra
PAUSA = 20 * 60  # log antigo sem "Execução iniciada": mais de 20 min sem processo = outra execução


def ler(linhas):
    """[{"grupo", "dia", "hora", "processos", "total", "gasto"}] na ordem do log (um por relatório)."""
    relatorios, atual, base, ultimo, quando = [], None, 0.0, 0.0, None
    for linha in linhas:
        if _FIM.search(linha):  # fim da execução: a próxima começa do zero
            atual, base, ultimo, quando = None, 0.0, 0.0, None
            continue
        m = _PROC.match(linha)
        if not m:
            continue
        dia, hora, grupo, n, total, acumulado = m.group(1), m.group(2), m.group(3), int(m.group(4)), int(m.group(5)), float(m.group(6))
        agora = datetime.strptime(f"{dia} {hora}", "%Y-%m-%d %H:%M")
        # execução nova que não escreveu "Concluído" (parou no meio): o acumulado voltou ou o log ficou parado
        if acumulado < ultimo or (quando and (agora - quando).total_seconds() > PAUSA):
            base = ultimo = 0.0
            atual = None
        quando = agora
        if atual is None or atual["grupo"] != grupo or n == 1:
            base = ultimo
            atual = {"grupo": grupo, "dia": dia, "hora": hora, "processos": 0, "total": total, "gasto": 0.0}
            relatorios.append(atual)
        atual["processos"] = n
        atual["gasto"] = round(acumulado - base, 4)
        ultimo = acumulado
    return relatorios


def main(*args):
    args = list(args)
    mes, log = "", LOG
    if "--mes" in args:
        mes = args[args.index("--mes") + 1]
    if "--log" in args:
        log = Path(args[args.index("--log") + 1])
    if not log.exists():
        print(f"Não achei o log {log}. Rode de dentro da pasta jarvis/.")
        return 2
    rels = [r for r in ler(log.read_text(encoding="utf-8", errors="replace").splitlines()) if r["dia"].startswith(mes)]
    if not rels:
        print("Nenhum relatório com análise da IA no log" + (f" em {mes}" if mes else "") + ".")
        return 0
    por = {}
    for r in rels:
        c = por.setdefault(r["grupo"], {"relatorios": 0, "processos": 0, "gasto": 0.0, "ultimo": ""})
        c["relatorios"] += 1
        c["processos"] += r["processos"]
        c["gasto"] += r["gasto"]
        c["ultimo"] = f'{r["dia"][8:10]}/{r["dia"][5:7]}'
    print(f"Gasto da IA por cliente{' em ' + mes if mes else ''} (log: {log}):\n")
    print(f"{'Cliente':38} {'Relat.':>6} {'Proc.':>6} {'Gasto':>10} {'Por proc.':>10}  Último")
    for nome, c in sorted(por.items(), key=lambda kv: -kv[1]["gasto"]):
        por_proc = c["gasto"] / c["processos"] if c["processos"] else 0
        print(f"{nome[:38]:38} {c['relatorios']:>6} {c['processos']:>6} {'US$ ' + format(c['gasto'], '.2f'):>10} "
              f"{'US$ ' + format(por_proc, '.3f'):>10}  {c['ultimo']}")
    total = sum(c["gasto"] for c in por.values())
    procs = sum(c["processos"] for c in por.values())
    print(f"\n{'TOTAL':38} {len(rels):>6} {procs:>6} {'US$ ' + format(total, '.2f'):>10} "
          f"{'US$ ' + format(total / procs if procs else 0, '.3f'):>10}")
    print("\nCada relatório:")
    for r in rels:
        parcial = "" if r["processos"] == r["total"] else f" (parou em {r['processos']} de {r['total']})"
        print(f"  {r['dia'][8:10]}/{r['dia'][5:7]} {r['hora']}  {r['grupo'][:38]:38} {r['processos']:>4} proc.  "
              f"US$ {r['gasto']:.2f}{parcial}")
    print("\nGasto estimado pelo Jarvis (tabela de preços do custo.py); a fatura da Anthropic é a palavra final.")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
