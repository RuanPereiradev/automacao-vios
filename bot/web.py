"""Página local de revisão: a pessoa confere, edita e valida as tarefas antes do lançamento."""
import json
import os
from datetime import date, datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from bot import prazos, revisao, skill

ROTULOS_ESTADO = {
    revisao.AGUARDANDO: "Aguardando validação",
    revisao.NA_FILA: "Na fila do robô",
    revisao.LANCANDO: "Lançando",
    revisao.LANCADA: "Lançada",
    revisao.ERRO: "Erro no lançamento",
    revisao.DESCARTADA: "Descartada",
    revisao.DUPLICADA: "Duplicada (ignorada)",
}


def _data_valida(texto):
    try:
        datetime.strptime(texto or "", "%d/%m/%Y")
        return True
    except ValueError:
        return False


def conferir(tarefas, oficiais, pessoas=()):
    """Problemas que impedem validar. Lista vazia = pode ir para a fila."""
    if not tarefas:
        return ["A CI não tem tarefa. Adicione uma tarefa ou descarte a CI."]
    problemas = []
    for n, t in enumerate(tarefas, 1):
        if t["nome"] not in oficiais:
            problemas.append(f"Tarefa {n}: escolha uma tarefa da lista oficial do VIOS.")
        sem_prazo = t.get("tipo_data") == "SEM_DATA" or t["nome"].startswith("CIÊNCIA")
        if not _data_valida(t["data_tarefa"]) and not (sem_prazo and not t["data_tarefa"]):
            problemas.append(f"Tarefa {n}: data inválida ou vazia.")
        if not t["descricao"].strip():
            problemas.append(f"Tarefa {n}: descrição vazia.")
        fora = [p for p in t["responsaveis"] if pessoas and p not in pessoas]
        if fora:
            problemas.append(f"Tarefa {n}: responsável fora da lista do VIOS: {', '.join(fora)}.")
    return problemas


def _tarefas_do_form(form):
    tarefas = []
    for t in json.loads(form.get("tarefas_json") or "[]"):
        tarefas.append({c: t.get(c, False if c == "marcar_breno" else "") for c in revisao.CAMPOS_TAREFA})
        tarefas[-1]["nome"] = tarefas[-1]["nome"].strip()
        tarefas[-1]["data_tarefa"] = tarefas[-1]["data_tarefa"].strip()
        tarefas[-1]["marcar_breno"] = bool(tarefas[-1]["marcar_breno"])
        tarefas[-1]["data_editada"] = bool(tarefas[-1]["data_editada"])
        tarefas[-1]["responsaveis"] = [p.strip() for p in t.get("responsaveis") or [] if p.strip()]
        if tarefas[-1]["responsaveis"]:
            # escolha manual: BRENO entra só se estiver na lista
            tarefas[-1]["marcar_breno"] = any(p.upper().startswith("BRENO") for p in tarefas[-1]["responsaveis"])
    return tarefas


def criar_app(caminho_banco, pasta_skill=None):
    app = Flask(__name__)
    app.secret_key = os.urandom(16)
    app.config["TEMPLATES_AUTO_RELOAD"] = True  # ajuste no HTML aparece sem reiniciar
    # "ACÓRDÃO" -> "Acórdão", mantendo siglas ("RPV/PRECATÓRIO" -> "RPV/precatório")
    app.add_template_filter(lambda t: t if not t else (t[:3] + t[3:].lower() if t.startswith("RPV") else t.capitalize()), "ato")
    pasta_skill = pasta_skill or os.getenv("SKILL_PASTA", "doc/analise-intimacoes-controladoria").strip()
    oficiais = skill.tarefas_oficiais(pasta_skill)
    feriados = prazos.Tabela(
        os.getenv("FERIADOS_TABELA", "doc/feriados-brasil-2026-2027.md").strip(),
        os.getenv("FERIADOS_ARQUIVO", "doc/feriados.txt").strip(),
    )

    arquivo_pessoas = Path(caminho_banco).parent / revisao.ARQUIVO_RESPONSAVEIS

    def pessoas():
        """Lista do campo Responsáveis do VIOS (./rodar_revisao.sh --atualizar-responsaveis)."""
        if not arquivo_pessoas.exists():
            return []
        return json.loads(arquivo_pessoas.read_text(encoding="utf-8"))

    def con():
        return revisao.conectar(caminho_banco)

    @app.route("/")
    def inicio():
        cis = revisao.listar(con())
        filtro = request.args.get("filtro", revisao.AGUARDANDO)
        primeira = next((c for c in cis if c["estado"] == filtro), None) or (cis[0] if cis else None)
        if not primeira:
            return render_template("revisao.html", cis=[], atual=None, filtro=filtro, contagem={}, rotulos=ROTULOS_ESTADO)
        return redirect(url_for("ver", ci=primeira["ci"], filtro=filtro))

    @app.route("/ci/<ci>")
    def ver(ci):
        cis = revisao.listar(con())
        atual = next((c for c in cis if c["ci"] == ci), None)
        if not atual:
            flash(f"CI {ci} não encontrada.", "erro")
            return redirect(url_for("inicio"))
        revisao.completar_responsaveis(atual)
        if atual["estado"] in revisao.EDITAVEIS:
            revisao.datas_relativas(atual, feriados, date.today())
        lista_pessoas = pessoas()
        contagem = {}
        for c in cis:
            contagem[c["estado"]] = contagem.get(c["estado"], 0) + 1
        filtro = request.args.get("filtro", "todas")
        return render_template(
            "revisao.html", cis=cis, atual=atual, filtro=filtro, contagem=contagem,
            rotulos=ROTULOS_ESTADO, oficiais=oficiais, editavel=atual["estado"] in revisao.EDITAVEIS,
            proxima=_proxima(cis, ci), pessoas=lista_pessoas,
            sugestoes=revisao.sugestoes(atual, lista_pessoas),
            auxiliares=revisao.auxiliares(atual, lista_pessoas),
        )

    @app.route("/ci/<ci>", methods=["POST"])
    def acao(ci):
        banco = con()
        atual = revisao.obter(banco, ci)
        if not atual:
            flash(f"CI {ci} não encontrada.", "erro")
            return redirect(url_for("inicio"))
        acao = request.form.get("acao")
        filtro = request.form.get("filtro", "todas")

        if acao in ("salvar", "validar"):
            if atual["estado"] not in revisao.EDITAVEIS:
                flash("Esta CI não pode ser editada no estado atual. Use \"Reabrir\" antes.", "erro")
                return redirect(url_for("ver", ci=ci, filtro=filtro))
            tarefas = _tarefas_do_form(request.form)
            revisao.salvar_tarefas(banco, ci, tarefas)
            if acao == "salvar":
                flash("Alterações salvas.", "ok")
                return redirect(url_for("ver", ci=ci, filtro=filtro))
            por = request.form.get("por", "").strip()
            problemas = conferir(tarefas, oficiais, pessoas()) + ([] if por else ["Informe seu nome em \"Validado por\"."])
            if problemas:
                for p in problemas:
                    flash(p, "erro")
                return redirect(url_for("ver", ci=ci, filtro=filtro))
            revisao.mudar_estado(banco, ci, revisao.NA_FILA, por=por)
            flash(f"CI {ci} validada e colocada na fila do robô.", "ok")
            return redirect(_depois(ci, filtro))

        if acao == "descartar" and atual["estado"] in revisao.EDITAVEIS:
            revisao.mudar_estado(banco, ci, revisao.DESCARTADA, mensagem=request.form.get("motivo", "").strip() or None)
            flash(f"CI {ci} descartada: não vai gerar tarefa.", "ok")
            return redirect(_depois(ci, filtro))

        if acao == "reabrir" and atual["estado"] in (revisao.NA_FILA, revisao.DESCARTADA, revisao.DUPLICADA):
            revisao.mudar_estado(banco, ci, revisao.AGUARDANDO)
            flash(f"CI {ci} reaberta para edição.", "ok")
            return redirect(url_for("ver", ci=ci, filtro=filtro))

        flash("Ação não permitida no estado atual.", "erro")
        return redirect(url_for("ver", ci=ci, filtro=filtro))

    def _depois(ci, filtro):
        """Depois de validar/descartar, vai para a próxima CI aguardando."""
        proxima = _proxima(revisao.listar(con()), ci)
        return url_for("ver", ci=proxima["ci"], filtro=filtro) if proxima else url_for("ver", ci=ci, filtro=filtro)

    return app


def _proxima(cis, ci):
    """Próxima CI aguardando validação depois da atual (dá a volta na lista)."""
    pendentes = [c for c in cis if c["estado"] == revisao.AGUARDANDO and c["ci"] != ci]
    depois = [c for c in pendentes if int(c["ci"]) > int(ci)]
    return (depois or pendentes or [None])[0]
