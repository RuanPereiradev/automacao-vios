"""Zangão (bot de comprovantes previdenciários, branch bot-edita-vios) disparado pelo Ultron.

O Zangão fica instalado numa pasta própria (ZANGAO_PASTA, com .venv e .env dele) no mesmo
computador do Ultron. A vila pede para rodar (POST /zangao/rodar) e o Ultron abre o Zangão em
segundo plano, como processo separado: ele continua mesmo se a página do Ultron reiniciar.
O andamento chega à vila pelos eventos que o próprio Zangão manda (POST /eventos).

- teste: `main.py --fora-da-janela` (simulação: preenche e não grava; qualquer dia);
- gravar: `main.py --confirmar`, só nos 3 últimos dias corridos do mês (o Zangão confere de novo);
- uma execução por vez: enquanto uma roda, outra é recusada.
"""
import calendar
import json
import logging
import os
import subprocess
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

MODOS = {"teste": ["--fora-da-janela"], "gravar": ["--confirmar"]}
ARQUIVO = ".vila_execucao.json"  # na pasta saida/ do Zangão: execução em andamento (pid, modo, início)
LOG = "execucoes_vila.log"  # na pasta logs/ do Zangão: saída de cada execução disparada pela vila
# só o necessário: nenhuma variável do Ultron (senha da página, chaves de API) vai para o Zangão
AMBIENTE = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL")
_trava = threading.Lock()


class ZangaoErro(Exception):
    pass


def janela(hoje=None):
    """True nos 3 últimos dias corridos do mês (mesma regra do Zangão)."""
    hoje = hoje or date.today()
    return hoje.day > calendar.monthrange(hoje.year, hoje.month)[1] - 3


def proxima_janela(hoje=None):
    """Primeiro dia da janela atual ou da próxima."""
    hoje = hoje or date.today()
    if janela(hoje):
        return hoje
    inicio = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1] - 2)
    if hoje < inicio:
        return inicio
    prox = (hoje.replace(day=1) + timedelta(days=32)).replace(day=1)
    return date(prox.year, prox.month, calendar.monthrange(prox.year, prox.month)[1] - 2)


def _python(pasta):
    return Path(pasta) / ".venv" / "bin" / "python"


def configurado(pasta):
    return bool(pasta) and _python(pasta).exists() and (Path(pasta) / "main.py").exists() \
        and (Path(pasta) / ".env").exists()


def _vivo(pid):
    """O processo existe e é o main.py do Zangão (não um pid reaproveitado)."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    try:
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:
        return True
    return "main.py" in cmd


def _ler(pasta):
    try:
        return json.loads((Path(pasta) / "saida" / ARQUIVO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status(pasta):
    """{"configurado", "rodando", "modo", "inicio", "janela", "proxima_janela"}."""
    hoje = date.today()
    info = {"configurado": bool(pasta) and configurado(pasta), "rodando": False, "modo": None, "inicio": None,
            "janela": janela(hoje), "proxima_janela": proxima_janela(hoje).strftime("%d/%m/%Y")}
    atual = _ler(pasta) if pasta else None
    if atual and _vivo(int(atual.get("pid", 0))):
        info.update(rodando=True, modo=atual.get("modo"), inicio=atual.get("inicio"))
    return info


# --- execuções, montadas dos eventos que o Zangão manda (bot: "zangao" em saida/eventos.jsonl) ---
MOTIVOS = {
    "outro_tipo": 'Não é "Editar os dados da ação protocolada"', "previdencia_privada": "Previdência privada/complementar (cível)",
    "sem_sinal_previdenciario": "Sem sinal previdenciário", "outra_area": "Previdenciária com termo de outra área: conferir à mão",
    "sinal_sem_previdenci": 'Sinal previdenciário sem "previdenci": conferir à mão', "ja_registrada": "Já resolvida antes (registro)",
    "fora_da_tarefa_unica": "Fora da tarefa escolhida (--tarefa)", "sem_comprovante": "Sem comprovante de protocolo",
    "mais_de_um_comprovante": "Mais de um comprovante de protocolo", "pdf_sem_texto": "PDF escaneado (sem texto)",
    "comprovante_nao_baixou": "Não consegui baixar o comprovante", "comprovante_nao_e_pdf": "O link do comprovante não devolveu um PDF",
    "dado_duplicado_no_pdf": "Dado com dois valores no PDF", "dado_ausente_no_pdf": "Dado não encontrado no PDF",
    "cnj_diferente_do_processo": "O PDF é de outro processo", "campo_com_outro_valor": "Campo já preenchido com outro valor",
    "processo_diferente_na_edicao": "A edição não é do processo aberto", "orgao_nao_apareceu": "Órgão julgador não apareceu na lista",
    "aviso_inesperado": "Aviso do VIOS que o bot não responde", "releitura_divergente": "A releitura depois de gravar não confere",
    "releitura_falhou": "Não consegui reler a tela", "outra_janela": "Abriu outra janela", "sem_id_do_processo": "Sem id do processo",
    "bloqueio_inativo": "Bloqueio de envios inativo", "preenchimento_divergente": "A tela não mostra o que foi preenchido",
    "elemento_nao_unico": "Elemento da tela não é único", "elemento_nao_apareceu": "Elemento da tela não apareceu",
    "excecao": "Erro inesperado (ver logs/bot.log do Zangão)", "config_invalida": "Configuração inválida (.env do Zangão)",
    "navegador_falhou": "O navegador não abriu", "tarefa_nao_encontrada": "A tarefa do --tarefa não está no calendário",
    "login_falhou": "Login no VIOS falhou",
}
ETAPA_SITUACAO = {"abrindo": "abrindo", "comprovante_lido": "comprovante", "preenchendo": "preenchendo"}
# situação de cada tarefa -> [classe do selo, texto]; resultado da execução -> [classe, texto]
SITUACOES = {
    "fila": ["s-ja", "Na fila"], "ignorada": ["s-ja", "Ignorada"], "ambigua": ["s-aviso", "Ambígua · conferir à mão"],
    "registrada": ["s-ja", "Já registrada"], "abrindo": ["s-andamento", "Abrindo…"], "comprovante": ["s-andamento", "Comprovante lido"],
    "preenchendo": ["s-andamento", "Preenchendo…"], "gravada": ["s-ok", "Gravada"], "ja_estava": ["s-ja", "Já estava"],
    "testada": ["s-ok", "Testada (não gravou)"], "lida": ["s-ok", "Lida"], "pulada": ["s-erro", "Pulada · conferir"],
    "conferir": ["s-erro", "Conferir no VIOS"], "erro": ["s-erro", "Erro"],
}
RESULTADOS = {
    "concluido": ["s-ok", "Concluído"], "testado": ["s-andamento", "Testado (não gravou)"],
    "lido": ["s-andamento", "Lido (não preencheu)"], "fora_do_dia": ["s-ja", "Não era dia"], "parou": ["s-erro", "Parou"],
    "rodando": ["s-andamento", "Rodando…"], "interrompida": ["s-erro", "Interrompida"],
}
MODOS_TEXTO = {"gravar": "Gravar no VIOS", "teste": "Teste (não grava)", "leitura": "Somente leitura"}
TEXTOS = {"motivos": MOTIVOS, "situacoes": SITUACOES, "resultados": RESULTADOS, "modos": MODOS_TEXTO}
FINAIS = ("gravada", "ja_estava", "testada", "lida", "pulada", "conferir", "erro")


def _execucao(eventos_da_execucao):
    """Resumo de uma execução: modo, fase, calendário, uma linha por tarefa e o fim."""
    e = {"id": None, "inicio": None, "ultimo": None, "modo": None, "fora_da_janela": False, "tarefa_unica": False,
         "fase": None, "calendario": None, "tarefas": [], "fim": None}
    por_id = {}
    for ev in eventos_da_execucao:
        e["id"] = e["id"] or ev.get("envio")
        e["inicio"] = e["inicio"] or ev.get("ts")
        e["ultimo"] = ev.get("ts")
        tipo = ev.get("tipo")
        if tipo == "execucao_iniciada":
            e.update(modo=ev.get("modo"), fora_da_janela=bool(ev.get("fora_da_janela")), tarefa_unica=bool(ev.get("tarefa_unica")))
        elif tipo == "fase":
            e["fase"] = ev.get("fase")
        elif tipo == "calendario":
            e["calendario"] = {k: ev.get(k, 0) for k in ("total", "previdenciarias", "processar", "ignoradas", "ambiguas")}
            e["tarefas"], por_id = [], {}
            for t in ev.get("tarefas") or []:
                linha = {"id": t.get("tarefa_id"), "classe": t.get("classe"), "decisao": t.get("decisao"),
                         "motivo": t.get("motivo"), "processo": None, "campos": None, "orgao": None,
                         "situacao": "fila" if t.get("decisao") == "processar" else
                                     "ambigua" if t.get("classe") == "ambigua" else
                                     "registrada" if t.get("decisao") == "ja_registrada" else "ignorada"}
                e["tarefas"].append(linha)
                if linha["id"]:
                    por_id[linha["id"]] = linha
        elif tipo == "tarefa":
            linha = por_id.get(ev.get("tarefa_id"))
            if linha is None:
                linha = {"id": ev.get("tarefa_id"), "classe": "previdenciaria", "decisao": "processar", "motivo": None,
                         "processo": None, "campos": None, "orgao": None, "situacao": "fila"}
                e["tarefas"].append(linha)
                if linha["id"]:
                    por_id[linha["id"]] = linha
            etapa = ev.get("etapa")
            linha["situacao"] = ETAPA_SITUACAO.get(etapa, etapa)
            pid = ev.get("processo_id")
            if pid:
                linha["processo"] = ", ".join(map(str, pid)) if isinstance(pid, list) else str(pid)
            if ev.get("campos") is not None:
                linha["campos"] = ev.get("campos")
            if ev.get("motivo"):
                linha["motivo"] = ev.get("motivo")
            if ev.get("orgao_cadastrado"):
                linha["orgao"] = "cadastrado"
            elif ev.get("orgao_novo"):
                linha["orgao"] = "novo"
        elif tipo == "execucao_fim":
            e["fim"] = {"resultado": ev.get("resultado"), "motivo": ev.get("motivo"),
                        "contagens": ev.get("contagens") or {}, "ts": ev.get("ts")}
    alvo = [t for t in e["tarefas"] if t["decisao"] == "processar"]
    e["alvo"] = len(alvo)
    e["feitas"] = sum(1 for t in alvo if t["situacao"] in FINAIS)
    return e


def execucoes(pasta_saida):
    """Execuções do Zangão (da mais nova para a mais antiga), montadas de saida/eventos.jsonl."""
    from bot import eventos  # aqui para o módulo não depender do Flask nem dos eventos ao importar
    grupos = {}
    for ev in eventos.ler(pasta_saida, 0, limite=10 ** 9)["eventos"]:
        if ev.get("bot") == "zangao" and ev.get("envio"):
            grupos.setdefault(ev["envio"], []).append(ev)
    lista = [_execucao(evs) for evs in grupos.values()]
    return sorted(lista, key=lambda e: e["inicio"] or "", reverse=True)


def andamento(pasta, pasta_saida):
    """Para a página do Zangão (a cada 1,5 s): status do processo + a execução mais recente."""
    info = status(pasta)
    lista = execucoes(pasta_saida)
    atual = lista[0] if lista else None
    if atual and not atual["fim"] and not info["rodando"]:
        atual["interrompida"] = True  # sem execucao_fim e o processo não está rodando aqui
    info["execucao"] = atual
    return info


def rodar(pasta, modo):
    """Abre o Zangão em segundo plano. Devolve o status; levanta ZangaoErro se não pode rodar."""
    if modo not in MODOS:
        raise ZangaoErro("modo inválido")
    if not configurado(pasta):
        raise ZangaoErro("o Zangão não está instalado neste servidor (ZANGAO_PASTA)")
    if modo == "gravar" and not janela():
        raise ZangaoErro("gravar só nos 3 últimos dias do mês (a partir de "
                         f"{proxima_janela():%d/%m/%Y}); fora disso, use o teste")
    with _trava:
        if status(pasta)["rodando"]:
            raise ZangaoErro("o Zangão já está rodando")
        pasta = Path(pasta)
        (pasta / "logs").mkdir(exist_ok=True)
        (pasta / "saida").mkdir(exist_ok=True)
        ambiente = {k: os.environ[k] for k in AMBIENTE if k in os.environ}
        ambiente["PYTHONUTF8"] = "1"
        inicio = datetime.now().isoformat(timespec="seconds")
        saida = open(pasta / "logs" / LOG, "a", encoding="utf-8")
        saida.write(f"\n===== {inicio} · modo {modo} (pela vila) =====\n")
        saida.flush()
        proc = subprocess.Popen([str(_python(pasta)), "main.py", *MODOS[modo]], cwd=pasta, env=ambiente,
                                stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT,
                                start_new_session=True)  # sobrevive a um reinício da página
        saida.close()
        arquivo = pasta / "saida" / ARQUIVO
        arquivo.write_text(json.dumps({"pid": proc.pid, "modo": modo, "inicio": inicio}), encoding="utf-8")
        log.info("Zangão iniciado pela vila: modo %s, pid %d", modo, proc.pid)

        def esperar():
            codigo = proc.wait()  # recolhe o processo (sem isso ele ficaria "zumbi" e pareceria vivo)
            log.info("Zangão terminou (modo %s, código %s)", modo, codigo)
            try:
                if (_ler(pasta) or {}).get("pid") == proc.pid:
                    arquivo.unlink()
            except OSError:
                pass

        threading.Thread(target=esperar, daemon=True).start()
    return status(pasta)
