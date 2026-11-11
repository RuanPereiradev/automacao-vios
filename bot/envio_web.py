"""Página de envio: a pessoa sobe o .txt com as tarefas já ajustadas (análise feita no chat),
confere o que vai ser gravado e o robô lança no VIOS. Não usa a IA (sem gasto de tokens)."""
import hmac
import io
import json
import logging
import os
import re
import threading
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

from flask import (Flask, Response, abort, jsonify, redirect, render_template, request, send_file,
                   send_from_directory, url_for)

from bot import albi, conferencia, config, duplicidade, envio_txt, eventos, jarvis, orelha, skill, zangao
from bot.lancamento import REGISTRO, RESULTADOS, lancar, ler_intimacao
from bot.login import fazer_login
from bot.navegador import criar_driver

log = logging.getLogger(__name__)
# dá para editar e enviar de novo (o que já foi gravado fica como "Já lançada")
EDITAVEIS = ("conferir", "testado", "falhou", "concluido")
# linha do log do lançamento quando uma tarefa entra no quadro do VIOS ("CI 42484 tarefa 1: ...")
TAREFA_ADICIONADA = re.compile(r"^CI \S+ tarefa \d+:")
FINAIS = ("gravada", "testada", "pulada", "duplicada", "erro")
# 1ª linha "MODO: TESTE": o arquivo só pode ser testado (o botão de gravar some e o servidor recusa)
MODO_TESTE = re.compile(r"\A\s*MODO\s*:\s*TESTE\s*(\r?\n|\Z)", re.I)
ARQUIVO_VILA = Path(__file__).parent / "vila" / "vila.html"  # HTML único da vila (servido em /vila)
# vila do Sam: a Fortaleza do Dragão (servida em /vila/sam, no topo das páginas do Sam)
ARQUIVO_FORTALEZA = Path(__file__).parent / "vila" / "fortaleza.html"
PASTA_ENVIOS = "envios"  # dentro da pasta de saída: um .json por envio (histórico que não some)
DATAS = ("criado", "inicio", "fim", "editado")


def salvar_envio(pasta, envio_id, envio):
    """Grava o envio em <saída>/envios/<id>.json (escrita atômica: nunca fica pela metade)."""
    pasta = Path(pasta) / PASTA_ENVIOS
    pasta.mkdir(parents=True, exist_ok=True)
    dados = {k: (v.isoformat() if k in DATAS and v else v) for k, v in envio.items()}
    tmp = pasta / f".{envio_id}.tmp"
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(pasta / f"{envio_id}.json")


def carregar_envios(pasta):
    """Envios gravados em disco. Um envio que estava em andamento quando a página parou fica
    como "falhou" (o que foi gravado no VIOS está no lancamentos.json)."""
    envios = {}
    for arquivo in sorted((Path(pasta) / PASTA_ENVIOS).glob("*.json")):
        try:
            envio = json.loads(arquivo.read_text(encoding="utf-8"))
        except ValueError:
            log.warning("Histórico de envio ilegível: %s", arquivo)
            continue
        for k in DATAS:
            if envio.get(k):
                envio[k] = datetime.fromisoformat(envio[k])
        if envio.get("estado") == "enviando":
            envio["estado"] = "falhou"
            envio["falha"] = "a página foi reiniciada no meio do envio; confira no VIOS as CIs sem resultado"
            for c in envio["cis"]:
                if c.get("resultado") in ("lançando", "conferindo"):
                    c["resultado"] = "erro"
            salvar_envio(pasta, arquivo.stem, envio)
            evento_fim(pasta, arquivo.stem, envio)
        envios[arquivo.stem] = envio
    return envios


def _status_conferencia(c):
    return "problema" if c["problemas"] else ("lancada" if c["ja_lancada"] else "pronta")


def evento_conferido(pasta, envio_id, envio):
    """Evento "conferido" (contrato da vila): contagens por CI e uma linha por CI (só CI e tarefa)."""
    situacoes = [_status_conferencia(c) for c in envio["cis"]]
    cis = []
    for c, s in zip(envio["cis"], situacoes):
        item = {"ci": c["ci"], "tarefa": " + ".join(t["nome"] for t in c["tarefas"]), "status": s}
        if s == "problema":
            item["motivo"] = c["problemas"][0]
        cis.append(item)
    eventos.emitir(pasta, envio_id, "conferido", prontas=situacoes.count("pronta"),
                   com_problema=situacoes.count("problema"), ja_lancadas=situacoes.count("lancada"), cis=cis)


def evento_fim(pasta, envio_id, envio):
    """Evento "envio_fim": resultado e contagens por CI."""
    fila = set(envio.get("fila", []))
    r = [c.get("resultado") for c in envio["cis"] if c["ci"] in fila]
    dados = {"resultado": {"concluido": "concluido", "testado": "testado"}.get(envio["estado"], "parou"),
             "contagens": {"gravadas": r.count("gravada"), "testadas": r.count("testada"), "erros": r.count("erro"),
                           "ja_tinha": r.count("pulada"), "duplicatas": r.count("duplicada")}}
    if dados["resultado"] == "parou":
        dados["motivo"] = envio.get("falha", "")
    eventos.emitir(pasta, envio_id, "envio_fim", **dados)


def _editavel(envio):
    """Envio reconstruído do log é só registro (não tem a descrição das tarefas): não reenvia."""
    return envio["estado"] in EDITAVEIS and not envio.get("reconstruido")


def resumo_envio(envio):
    """Contagem por resultado, para o histórico."""
    r = [c.get("resultado") for c in envio["cis"]]
    return {"gravadas": r.count("gravada"), "testadas": r.count("testada"), "erros": r.count("erro"),
            "puladas": r.count("pulada") + r.count("duplicada"), "cis": len(r),
            "tarefas": sum(len(c["tarefas"]) for c in envio["cis"])}


def _situacao_tarefas(c):
    """Situação de cada tarefa da CI durante o envio, pelo log do lançamento."""
    adicionadas = sum(1 for l in c.get("mensagens") or [] if TAREFA_ADICIONADA.match(l))
    resultado = c.get("resultado")
    situacoes = []
    for i, _ in enumerate(c["tarefas"]):
        if resultado in ("gravada", "testada"):
            s = resultado
        elif resultado in ("pulada", "duplicada"):
            s = "pulada"
        elif resultado == "erro":
            s = "adicionada" if i < adicionadas else "erro"
        elif resultado == "lançando":
            s = "adicionada" if i < adicionadas else ("criando" if i == adicionadas else "aguardando")
        else:
            s = "aguardando"
        situacoes.append(s)
    return situacoes


def status_envio(envio):
    """Andamento do envio para a página acompanhar ao vivo (sem recarregar)."""
    fila = set(envio.get("fila", []))
    cis = [c for c in envio["cis"] if c["ci"] in fila]
    return {
        "estado": envio["estado"], "fase": envio.get("fase", ""), "confirmar": envio["confirmar"],
        "total": len(cis), "concluidas": sum(1 for c in cis if c.get("resultado") in FINAIS),
        "tarefas_total": sum(len(c["tarefas"]) for c in cis),
        "tarefas_feitas": sum(s in ("gravada", "testada", "adicionada", "pulada")
                              for c in cis for s in _situacao_tarefas(c)),
        "falha": envio.get("falha", ""),
        "cis": [{"ci": c["ci"], "processo": c.get("processo", ""), "resultado": c.get("resultado", ""),
                 "ultima": (c.get("mensagens") or [""])[-1][:160],
                 "tarefas": [{"nome": t["nome"], "data": t["data_tarefa"], "hora": t["hora"], "situacao": s}
                             for t, s in zip(c["tarefas"], _situacao_tarefas(c))]}
                for c in cis],
    }


class _Coletor(logging.Handler):
    """Guarda as mensagens do lançamento de uma CI, para mostrar na página."""

    def __init__(self, ao_adicionar=None):
        super().__init__(logging.INFO)
        self.linhas = []
        self.ao_adicionar = ao_adicionar  # chamado com o nº da tarefa que entrou no quadro do VIOS

    def emit(self, record):
        msg = record.getMessage()
        if msg.startswith(("Observação:", "Quadro Tarefas")):
            return
        linha = msg.splitlines()[0]
        if record.exc_info and record.exc_info[1]:
            linha += f": {str(record.exc_info[1]).splitlines()[0]}"  # o motivo do erro
        self.linhas.append(linha)
        m = re.match(r"^CI \S+ tarefa (\d+):", msg)
        if m and self.ao_adicionar:
            self.ao_adicionar(int(m.group(1)))


def _capturas(pasta_saida):
    """{ci: intimação capturada} de todas as capturas salvas (a mais recente vale)."""
    itens = {}
    for arquivo in sorted(Path(pasta_saida).glob("intimacoes_*.json"), key=lambda a: a.stat().st_mtime):
        for item in json.loads(arquivo.read_text(encoding="utf-8")):
            if item.get("ci"):
                itens[item["ci"]] = item
    return itens


def _links_capturados(pasta_saida):
    """{ci: link "Lançar Intimação"} de todas as capturas salvas."""
    return {ci: i["link_lancar"] for ci, i in _capturas(pasta_saida).items() if i.get("link_lancar")}


def _processos_capturados(pasta_saida):
    """{ci: número do processo} das capturas salvas (campo Números do VIOS; senão, o texto)."""
    from bot.analise import numero_processo
    return {ci: numero_processo(i.get("numeros", ""), i.get("texto", "")) for ci, i in _capturas(pasta_saida).items()}


def _duplicadas(pasta_saida):
    """{ci: CI original}: cópias marcadas na captura ou na análise do bot e as que o detector
    acha nas capturas salvas (1ª conferência, na subida do .txt). Detector desligado: nenhuma."""
    if not duplicidade.ligado():
        return {}
    dup = {}
    for arquivo in Path(pasta_saida).glob("analise_*.json"):
        for r in json.loads(arquivo.read_text(encoding="utf-8")):
            if r.get("duplicada_de"):
                dup[r["ci"]] = r["duplicada_de"]
    capturas = _capturas(pasta_saida)
    dup.update({ci: i["duplicada_de"] for ci, i in capturas.items() if i.get("duplicada_de")})
    dup.update({ci: d["original"] for ci, d in duplicidade.detectar(list(capturas.values())).items()})
    return dup


def conferir_duplicatas_no_vios(driver, aptas, capturas, lancadas, timeout):
    """2ª conferência, na hora do envio: lê no VIOS o teor de cada CI do arquivo e compara
    com as outras do arquivo e com as capturas. Marca resultado/mensagens nas cópias e
    devolve as CIs que podem ser lançadas. Detector desligado: todas seguem, sem ler o VIOS."""
    if not duplicidade.ligado():
        return list(aptas)
    lidas = {}
    for c in aptas:
        c["resultado"] = "conferindo"
        try:
            i = ler_intimacao(driver, c["link_lancar"], timeout)
        except Exception as e:
            c["resultado"] = "erro"
            c["mensagens"] = [f"Não consegui ler a intimação no VIOS para conferir duplicata: {e}"]
            continue
        lidas[c["ci"]] = {"ci": c["ci"], "numeros": i["numeros"] or i["texto"], "texto": i["texto"],
                          "cliente": i["cliente"]}
    itens = {**{ci: i for ci, i in capturas.items() if ci not in lidas}, **lidas}
    dup = duplicidade.detectar(list(itens.values()))
    no_envio = set(lidas)
    seguir = []
    for c in aptas:
        if c.get("resultado") == "erro":
            continue
        d = dup.get(c["ci"])
        if not d:
            c.pop("resultado", None)
            seguir.append(c)
            continue
        original = d["original"]
        if original in lancadas or original in no_envio:
            c["resultado"] = "duplicada"
            c["mensagens"] = [f"Cópia da CI {original} ({d['motivo']}): não lançada, vale a tarefa da CI {original}"
                              + (", que já foi lançada." if original in lancadas else ", que está neste arquivo.")]
        else:
            c["resultado"] = "erro"
            c["mensagens"] = [f"Cópia da CI {original} ({d['motivo']}), que não está neste arquivo nem foi lançada: "
                              "conferir qual das duas lançar."]
        log.info("CI %s: %s", c["ci"], c["mensagens"][0])
    return seguir


# tela "Envio automático": o que aconteceu com cada CI (rótulo e classe do selo)
RESULTADO_ROTULO = {
    "gravada": ("s-ok", "Lançada no VIOS"), "bloqueada": ("s-erro", "Não lançada — falta informação"),
    "erro": ("s-erro", "Não lançada — erro"), "duplicada": ("s-ja", "Duplicada (não lançada)"),
    "ja_no_vios": ("s-ja", "Já tinha tarefa no VIOS"), "conferencia": ("s-erro", "Não lançada — conferência humana"),
    "retirada": ("s-erro", "Não lançada — tirada da lista"), "aguardando": ("s-andamento", "Ainda não enviada"),
}


def _registros_automatico(pasta_saida):
    """(lancamentos.json, automatico_resultados.json)."""
    pasta = Path(pasta_saida)
    ler = lambda a: json.loads(a.read_text(encoding="utf-8")) if a.exists() else {}
    return ler(pasta / REGISTRO), ler(pasta / RESULTADOS)


def montar_automatico(pasta_saida, dias_analise):
    """Relatório de conferência das análises pedidas (bot/conferencia.py): uma linha por intimação,
    da captura à tarefa gravada no VIOS, com os prazos conferidos. Não lançadas primeiro, depois as
    lançadas, cada grupo pela data mais próxima."""
    pasta = Path(pasta_saida)
    capturas = _capturas(pasta)
    registro, anotados = _registros_automatico(pasta)
    linhas = []
    for dia in dias_analise:
        for a in json.loads((pasta / f"analise_{dia}.json").read_text(encoding="utf-8")):
            ci = a.get("ci", "")
            item = capturas.get(ci, {})
            link = a.get("link_lancar") or item.get("link_lancar", "")
            if ci in registro:
                estado, mensagem, quando = "gravada", "", registro[ci].get("quando", "")
            elif ci in anotados:
                estado, mensagem, quando = anotados[ci]["estado"], anotados[ci].get("mensagem", ""), anotados[ci].get("quando", "")
            elif a.get("duplicada_de") and duplicidade.ligado():
                estado, mensagem, quando = "duplicada", f"Cópia da CI {a['duplicada_de']}: vale a tarefa da original.", ""
            elif a.get("bloqueios"):
                estado, mensagem, quando = "bloqueada", "; ".join(a["bloqueios"]), ""
            else:
                estado, mensagem, quando = "aguardando", "", ""
            classe, rotulo = RESULTADO_ROTULO.get(estado, ("s-ja", estado))
            lancada = estado == "gravada"
            gravadas = registro.get(ci, {}).get("tarefas", []) if lancada else []
            pares, notas, atencao_datas = conferencia.comparar_tarefas(a, gravadas, quando)
            ia = a.get("ia") or {}
            contas = conferencia.conferir_contas(a)
            datas = [d for d in (conferencia.data(a.get("prazo_d2")), conferencia.data(a.get("embargos")),
                                 *(conferencia.data(v["data"] if v else t.get("data_tarefa")) for t, v in pares)) if d]
            linhas.append({
                "ci": ci, "processo": a.get("processo", ""), "cliente": a.get("cliente") or item.get("cliente", ""),
                "posicao": a.get("posicao_cliente", ""), "auxiliar": a.get("auxiliar", ""),
                "disponibilizacao": a.get("disponibilizacao", ""), "publicacao": a.get("publicacao", ""),
                "teor": item.get("texto", ""), "ato": a.get("ato", ""), "area": a.get("area", ""),
                "do_que_se_trata": a.get("do_que_se_trata", ""), "pendencias": a.get("pendencias", []),
                "alertas": a.get("alertas", []), "bloqueios": a.get("bloqueios", []), "modelo": a.get("modelo", ""),
                "custo": a.get("custo_us") or 0, "estado": estado, "lancada": lancada,
                "classe": classe, "rotulo": rotulo, "mensagem": mensagem, "quando": quando,
                "pares": pares, "gravadas": gravadas,
                "prazo_fatal": a.get("prazo_fatal", ""), "prazo_d2": a.get("prazo_d2", ""),
                "prazo_trecho": a.get("prazo_trecho", ""), "prazo": ia.get("prazo") or {},
                "embargos": a.get("embargos", ""), "embargos_dias": (ia.get("embargos") or {}).get("dias"),
                "recurso": a.get("recurso", ""), "recurso_nome": a.get("recurso_nome", ""),
                "recurso_dias": (ia.get("recurso") or {}).get("dias"),
                "cabe_recurso": a.get("cabe_recurso", ""), "calendario": a.get("calendario", ""),
                "contas": [(True, n) for n in notas] + contas,  # notas do corte das 12h + conta refeita
                "contas_ok": [ok for ok, _ in contas],
                "atencao": atencao_datas + conferencia.pontos_de_atencao(a, pares, lancada),
                "proxima": min(datas) if datas else date.max,
                "link_lancar": link,
                "link_conferencia": link.replace("int-lanca.php", "confere-intimacao-lancada.php") if link else "",
            })
    linhas.sort(key=lambda l: (l["lancada"], l["proxima"], l["ci"]))
    return linhas


def _cis_do_form(form):
    """CIs e tarefas da tela de edição. Campos: g{n}_ci e g{n}_t{m}_{campo}; tarefa marcada
    para remover sai; linhas fora do formato (soltas) continuam até a pessoa apagar."""
    cis, g = [], 0
    while f"g{g}_ci" in form:
        tarefas, m = [], 0
        while f"g{g}_t{m}_nome" in form:
            campo = lambda nome: form.get(f"g{g}_t{m}_{nome}", "").strip()
            if not form.get(f"g{g}_t{m}_remover"):
                resp = campo("responsaveis")
                tarefas.append({
                    "nome": campo("nome"), "data_tarefa": campo("data"), "hora": campo("hora"),
                    "responsaveis": [] if envio_txt._normalizar(resp) in envio_txt.AUTOMATICO else [resp],
                    "descricao": form.get(f"g{g}_t{m}_descricao", "").replace("\r\n", "\n").strip(),
                    "soltas": [l for l in campo("soltas").splitlines() if l.strip()],
                })
            m += 1
        if tarefas:
            cis.append({"ci": form[f"g{g}_ci"].strip(), "processo": form.get(f"g{g}_processo", "").strip(), "tarefas": tarefas})
        g += 1
    return cis


def criar_app(caminho_env=".env", pasta_skill=None, senha=""):
    """senha: exigida (usuário qualquer) quando a página fica aberta na rede."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.before_request
    def barrar_outro_site():
        """POST só da própria página (CSRF): o navegador guarda a senha e a mandaria junto num POST
        disparado por outro site aberto nele. O navegador sempre manda Origin (ou Referer) num
        POST; se vier de outro endereço, recusa. Sem Origin/Referer (ex.: o Zangão, por
        urllib, em POST /eventos) passa para a senha decidir."""
        if request.method != "POST":
            return None
        origem = request.headers.get("Origin") or request.headers.get("Referer")
        if origem and urlsplit(origem).netloc != urlsplit(request.host_url).netloc:
            log.warning("POST %s recusado: veio de outro site (%s)", request.path, urlsplit(origem).netloc)
            return Response("Pedido recusado: veio de outro site.", 403)
        return None

    @app.before_request
    def exigir_senha():
        if not senha:
            return None
        auth = request.authorization
        if auth and hmac.compare_digest((auth.password or "").encode(), senha.encode()):
            return None
        return Response("Senha necessária.", 401, {"WWW-Authenticate": 'Basic realm="Vila dos Bots", charset="UTF-8"'})

    cfg = config.carregar(caminho_env)
    oficiais = skill.tarefas_oficiais(pasta_skill or "doc/analise-intimacoes-controladoria")
    partes = urlsplit(cfg.url)
    base_url = f"{partes.scheme}://{partes.netloc}/"
    pasta_saida = Path(cfg.pasta_saida)
    # Zangão instalado neste computador (pasta com .venv e .env dele); vazio = sem botões na vila
    pasta_zangao = os.path.expanduser(os.getenv("ZANGAO_PASTA", "").strip())
    pasta_albi = albi.pasta()  # Albi (bot do Sonar): ALBI_PASTA ou a pasta albi/ deste repositório
    # Jarvis (relatório mensal de processos): JARVIS_PASTA ou a pasta jarvis/ deste repositório
    pasta_jarvis = jarvis.pasta()
    # Orelha (relatório do dia): ORELHA_PASTA ou a pasta orelha/ deste repositório; o Sam só lê o horário e os relatórios
    pasta_orelha = orelha.pasta()
    arquivo_pessoas = pasta_saida / "responsaveis.json"
    envios = carregar_envios(pasta_saida)  # id -> {arquivo, cis, estado, confirmar, ...}
    trava = threading.Lock()  # um envio por vez (um navegador só)

    def lancadas():
        arquivo = pasta_saida / REGISTRO
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}

    def pessoas():
        return json.loads(arquivo_pessoas.read_text(encoding="utf-8")) if arquivo_pessoas.exists() else []

    def conferir(texto):
        """Lê o .txt e confere cada CI (a mesma conferência na subida e depois de editar)."""
        return envio_txt.ler(texto, oficiais, pessoas(), lancadas(), _links_capturados(pasta_saida), base_url,
                             duplicadas=_duplicadas(pasta_saida), processos=_processos_capturados(pasta_saida))

    @app.route("/")
    def vila_dos_bots():
        """Entrada do sistema: a Vila dos Bots (neutra, sem nenhum bot fixo) com um cartão para cada bot."""
        return render_template("vila_dos_bots.html", albi_pronto=albi.configurado(pasta_albi),
                               jarvis_pronto=jarvis.configurado(pasta_jarvis), zangao_pronto=bool(pasta_zangao),
                               orelha_info=orelha.status(pasta_orelha))

    @app.route("/sam")
    def inicio():
        """Página do Sam (envio de tarefas ao VIOS)."""
        recentes = sorted(envios.items(), key=lambda e: e[1]["criado"], reverse=True)[:8]
        # cartão "Envio automático": os últimos dias de envio, o mais novo com os números
        automaticos = []
        for n, (dia, envio) in enumerate(list(_dias_envio().items())[:6]):
            item = {"dia": dia, "enviado": envio["enviado"]}
            if n == 0:
                try:
                    linhas = montar_automatico(pasta_saida, envio["analises"])
                except (OSError, ValueError, KeyError):
                    log.exception("Envio automático de %s: não deu para montar o resumo", dia)
                    linhas = []
                item.update(total=len(linhas), lancadas=sum(l["lancada"] for l in linhas),
                            atencao=sum(1 for l in linhas if l["atencao"]))
            automaticos.append(item)
        return render_template("envio.html", tela="inicio", recentes=recentes, resumo=resumo_envio,
                               total_envios=len(envios), total_lancadas=len(lancadas()), ocupado=trava.locked(),
                               automaticos=automaticos)

    @app.route("/historico")
    def historico():
        """Todos os envios (saida/envios/) e todas as CIs gravadas no VIOS (lancamentos.json)."""
        todos = sorted(envios.items(), key=lambda e: e[1]["criado"], reverse=True)
        registro = lancadas()
        def quando(item):
            try:
                return datetime.strptime(item[1]["quando"], "%d/%m/%Y %H:%M")
            except (KeyError, ValueError):
                return datetime.min
        gravadas = sorted(registro.items(), key=quando, reverse=True)
        return render_template("envio.html", tela="historico", envios_todos=todos, resumo=resumo_envio,
                               gravadas=gravadas, total_tarefas=sum(len(r.get("tarefas", [])) for r in registro.values()),
                               ocupado=trava.locked())

    def _dias_envio():
        return conferencia.dias_de_envio(pasta_saida, *_registros_automatico(pasta_saida))

    @app.route("/automatico")
    @app.route("/automatico/<dia>")
    def automatico(dia=None):
        """Envio automático: relatório de conferência de um dia de envio (o dia em que as tarefas foram
        gravadas no VIOS): cada intimação -> análise da IA -> prazos conferidos -> o que foi lançado."""
        dias = _dias_envio()
        if not dias:
            return render_template("automatico.html", dias={}, dia="", linhas=[], ocupado=trava.locked())
        if dia not in dias:
            if dia:
                abort(404)
            dia = next(iter(dias))
        linhas = montar_automatico(pasta_saida, dias[dia]["analises"])
        contas = [ok for l in linhas for ok in l["contas_ok"]]
        return render_template("automatico.html", dias=dias, dia=dia, linhas=linhas, ocupado=trava.locked(),
                               lancadas=sum(l["lancada"] for l in linhas),
                               tarefas=sum(len(l["gravadas"]) for l in linhas),
                               custo=sum(l["custo"] for l in linhas),
                               modelos=sorted({l["modelo"] for l in linhas if l["modelo"]}),
                               contas=len(contas), contas_ok=sum(contas),
                               com_atencao=sum(1 for l in linhas if l["atencao"]),
                               feriados=conferencia.feriados_no_periodo(linhas),
                               simplificadas=sum(conferencia.usa_simplificada(l) for l in linhas),
                               gerado=datetime.now(), cf=conferencia)

    @app.route("/ler", methods=["POST"])
    def ler():
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            return redirect(url_for("inicio"))
        bruto = arquivo.read()
        try:
            texto = bruto.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = bruto.decode("cp1252")  # salvo pelo Bloco de Notas antigo
        so_teste = bool(MODO_TESTE.match(texto))
        texto = MODO_TESTE.sub("", texto, count=1)
        cis = conferir(texto)
        if not cis:
            return render_template("envio.html", tela="inicio", recentes=[], resumo=resumo_envio, ocupado=trava.locked(),
                                   total_envios=len(envios), total_lancadas=len(lancadas()),
                                   erro="Nenhum bloco encontrado. Confira o formato (CI:, TAREFA:, DATA:, ..., DESCRIÇÃO:).")
        envio_id = f"{datetime.now():%Y-%m-%d_%H%M%S}_{uuid.uuid4().hex[:4]}"  # nome do arquivo no histórico
        envios[envio_id] = {"arquivo": arquivo.filename, "cis": cis, "estado": "conferir",
                            "criado": datetime.now(), "confirmar": False, "texto_original": texto,
                            "so_teste": so_teste}
        salvar_envio(pasta_saida, envio_id, envios[envio_id])
        eventos.emitir(pasta_saida, envio_id, "arquivo_subido", arquivo=arquivo.filename)
        evento_conferido(pasta_saida, envio_id, envios[envio_id])
        return redirect(url_for("ver", envio_id=envio_id))

    @app.route("/envio/<envio_id>")
    def ver(envio_id):
        envio = envios.get(envio_id) or abort(404)
        aptas = [c for c in envio["cis"] if not c["problemas"] and not c["ja_lancada"]]
        capturadas = _capturas(pasta_saida)
        nao_capturadas = [c["ci"] for c in envio["cis"] if c["ci"] not in capturadas]
        return render_template("envio.html", tela="envio", envio_id=envio_id, envio=envio, aptas=aptas,
                               nao_capturadas=nao_capturadas,
                               ocupado=trava.locked() and envio["estado"] != "enviando",
                               editavel=_editavel(envio), oficiais=oficiais, pessoas=pessoas(), agora=datetime.now(),
                               texto=envio_txt.gerar(envio["cis"]))

    @app.route("/envio/<envio_id>/salvar", methods=["POST"])
    def salvar(envio_id):
        """Edição na página: refaz o .txt com os campos (ou com o texto colado) e confere de novo."""
        envio = envios.get(envio_id) or abort(404)
        if not _editavel(envio):
            return redirect(url_for("ver", envio_id=envio_id))
        texto = request.form["texto"] if request.form.get("modo") == "texto" else envio_txt.gerar(_cis_do_form(request.form))
        envio["cis"] = conferir(texto)
        envio["estado"] = "conferir"  # mudou: o teste anterior não vale mais
        envio["editado"] = datetime.now()
        salvar_envio(pasta_saida, envio_id, envio)
        evento_conferido(pasta_saida, envio_id, envio)  # editou: a vila recebe a conferência nova
        return redirect(url_for("ver", envio_id=envio_id))

    @app.route("/envio/<envio_id>/enviar", methods=["POST"])
    def enviar(envio_id):
        envio = envios.get(envio_id) or abort(404)
        if not _editavel(envio):
            return redirect(url_for("ver", envio_id=envio_id))
        if not trava.acquire(blocking=False):
            return redirect(url_for("ver", envio_id=envio_id))
        envio["confirmar"] = bool(request.form.get("confirmar")) and not envio.get("so_teste")
        envio["estado"] = "enviando"
        envio["fase"] = "login"
        envio["inicio"] = datetime.now()
        envio.pop("falha", None)
        for c in envio["cis"]:
            c.pop("resultado", None)
            c.pop("mensagens", None)
        envio["fila"] = [c["ci"] for c in envio["cis"] if not c["problemas"] and not c["ja_lancada"]]
        salvar_envio(pasta_saida, envio_id, envio)
        eventos.emitir(pasta_saida, envio_id, "envio_iniciado", modo="gravar" if envio["confirmar"] else "teste")
        threading.Thread(target=_rodar, args=(envio_id, envio), daemon=True).start()
        return redirect(url_for("ver", envio_id=envio_id))

    @app.route("/envio/<envio_id>/status")
    def status(envio_id):
        return jsonify(status_envio(envios.get(envio_id) or abort(404)))

    @app.route("/eventos")
    def lista_eventos():
        """Eventos para a vila: GET /eventos?desde=N devolve os de n > N (contrato em doc/vila/)."""
        return jsonify(eventos.ler(pasta_saida, request.args.get("desde", 0, type=int)))

    @app.route("/eventos", methods=["POST"])
    def recebe_evento():
        """Evento de outro bot (hoje só o Zangão) para a vila; mesma senha da página."""
        try:
            n = eventos.receber(pasta_saida, request.get_data(cache=False))
        except eventos.EventoInvalido as e:
            log.warning("Evento recusado de %s: %s", request.remote_addr, e)
            return jsonify(erro=str(e)), 400
        except OSError:
            return jsonify(erro="não consegui gravar o evento"), 500
        return jsonify(n=n)

    def _mesma_origem():
        """Pedido feito pela própria página (JSON e, se vier, Origin igual): barra outro site que
        tente usar a senha guardada no navegador para disparar o Zangão."""
        origem = request.headers.get("Origin")
        return request.is_json and (not origem or origem.rstrip("/") == request.host_url.rstrip("/"))

    @app.context_processor
    def menu():
        return {"zangao_ligado": bool(pasta_zangao), "albi_ligado": albi.configurado(pasta_albi),
                "jarvis_ligado": jarvis.configurado(pasta_jarvis)}

    @app.route("/albi")
    def albi_pagina():
        """Página do Albi: solta o .txt (um CPF/CNPJ por linha) e ele preenche no Sonar, sem confirmar."""
        return render_template("albi.html", tela="inicio", textos=albi.TEXTOS, erro=request.args.get("erro"),
                               max_linhas=albi.MAX_LINHAS)

    @app.route("/albi/enviar", methods=["POST"])
    def albi_enviar():
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            return redirect(url_for("albi_pagina"))
        bruto = arquivo.read()
        try:
            texto = bruto.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = bruto.decode("cp1252")  # salvo pelo Bloco de Notas antigo
        try:
            envio_id = albi.receber(pasta_albi, pasta_saida, texto, Path(arquivo.filename).name)
        except albi.AlbiErro as e:
            return redirect(url_for("albi_pagina", erro=str(e)))
        return redirect(url_for("albi_conferir", envio_id=envio_id))

    def _id_albi(envio_id):
        if not re.fullmatch(r"[\w-]{1,64}", envio_id):
            abort(404)
        return envio_id

    @app.route("/albi/conferir/<envio_id>")
    def albi_conferir(envio_id):
        """Antes de comprar: quem vai ser pesquisado, quem fica de fora e o total em R$."""
        meta = albi.conferencia(pasta_saida, _id_albi(envio_id)) or abort(404)
        return render_template("albi.html", tela="conferir", envio_id=envio_id, meta=meta, textos=albi.TEXTOS,
                               ocupado=albi.status(pasta_albi)["rodando"])

    @app.route("/albi/rodar/<envio_id>", methods=["POST"])
    def albi_rodar(envio_id):
        """Roda o Albi: modo "teste" (preenche e não compra), "confirmar" (compra) ou "baixar"
        (arquivo já confirmado: só baixa de novo os resultados, não compra)."""
        modo = request.form.get("modo")
        if modo == "confirmar" and request.form.get("certeza") != "sim":
            return redirect(url_for("albi_conferir", envio_id=envio_id))
        try:
            albi.iniciar(pasta_albi, pasta_saida, _id_albi(envio_id), modo)
        except albi.AlbiErro as e:
            return redirect(url_for("albi_pagina", erro=str(e)))
        log.info("Albi disparado pela página (%s, modo %s) por %s", envio_id, modo, request.remote_addr)
        return redirect(url_for("albi_pagina"))

    @app.route("/albi/arquivo/<envio_id>/<path:nome>")
    def albi_arquivo(envio_id, nome):
        """resultado.txt ou uma planilha baixada do Sonar."""
        # caminho completo: com SAIDA_PASTA relativa (ex.: "saida"), o Flask procuraria dentro de bot/
        return send_from_directory(albi.pasta_resultado(pasta_saida, _id_albi(envio_id)).resolve(), nome, as_attachment=True)

    @app.route("/albi/relatorio/<envio_id>", methods=["POST"])
    def albi_relatorio(envio_id):
        """Gera o relatório dos processos com o que já foi baixado (não entra no Sonar) e abre."""
        try:
            albi.gerar_relatorio(pasta_albi, pasta_saida, _id_albi(envio_id))
        except albi.AlbiErro as e:
            return redirect(url_for("albi_pagina", erro=str(e)))
        return redirect(url_for("albi_ver", envio_id=envio_id))

    @app.route("/albi/resumo/<envio_id>", methods=["GET", "POST"])
    def albi_resumo(envio_id):
        """"Capturar resumo": a mensagem para a empresa (do relatório; gera antes, se ainda não tiver)."""
        envio_id = _id_albi(envio_id)
        if request.method == "POST":
            if albi.mensagens(pasta_saida, envio_id) is None or albi.mensagens_cac(pasta_saida, envio_id) is None:
                try:
                    albi.gerar_relatorio(pasta_albi, pasta_saida, envio_id)
                except albi.AlbiErro as e:
                    return redirect(url_for("albi_pagina", erro=str(e)))
            return redirect(url_for("albi_resumo", envio_id=envio_id))
        msgs = albi.mensagens(pasta_saida, envio_id)
        if msgs is None:
            return redirect(url_for("albi_pagina", erro="esta execução ainda não tem o resumo: clique em \"Capturar resumo\""))
        return render_template("albi.html", tela="resumo", envio_id=envio_id, mensagens=msgs, textos=albi.TEXTOS,
                               cac=albi.mensagens_cac(pasta_saida, envio_id) or {"atendentes": [], "mensagens": []},
                               arquivos=albi.arquivos(pasta_saida, envio_id))

    @app.route("/albi/ver/<envio_id>")
    def albi_ver(envio_id):
        """relatorio.html na tela (não baixa). Sem scripts: CSP só deixa o estilo da própria página."""
        base = albi.pasta_resultado(pasta_saida, _id_albi(envio_id)).resolve()
        if not (base / "relatorio.html").is_file():
            abort(404)
        r = send_from_directory(base, "relatorio.html")
        r.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
        r.headers["Cache-Control"] = "no-store"
        return r

    @app.route("/albi/zip/<envio_id>")
    def albi_zip(envio_id):
        """Tudo desta execução num .zip (resultado.txt e as planilhas, por empresa)."""
        base = albi.pasta_resultado(pasta_saida, _id_albi(envio_id))
        nomes = albi.arquivos(pasta_saida, envio_id) or abort(404)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for nome in nomes:
                z.write(base / nome, nome)
        return Response(buf.getvalue(), 200, {"Content-Type": "application/zip",
                        "Content-Disposition": f'attachment; filename="albi_{envio_id}.zip"'})

    @app.route("/albi/modelo")
    def albi_modelo():
        """O modelo do .txt do Albi (albi/modelo_pedidos.txt), para baixar e preencher."""
        modelo = albi.PASTA_PADRAO / "modelo_pedidos.txt"
        if not modelo.exists():
            abort(404)
        return Response(modelo.read_bytes(), 200, {"Content-Type": "text/plain; charset=utf-8",
                        "Content-Disposition": 'attachment; filename="modelo_albi.txt"'})

    @app.route("/albi/andamento")
    def albi_andamento():
        return jsonify(albi.andamento(pasta_albi, pasta_saida))

    @app.route("/albi/historico")
    def albi_historico():
        return render_template("albi.html", tela="historico", execucoes=albi.execucoes(pasta_saida), textos=albi.TEXTOS)

    @app.route("/albi/execucao/<execucao_id>")
    def albi_execucao(execucao_id):
        e = next((e for e in albi.execucoes(pasta_saida) if e["id"] == execucao_id), None) or abort(404)
        return render_template("albi.html", tela="execucao", e=e, textos=albi.TEXTOS)

    @app.route("/zangao")
    def zangao_pagina():
        """Página do Zangão, como a do Ultron: cena, botões de rodar e andamento ao vivo."""
        return render_template("zangao.html", tela="inicio", textos=zangao.TEXTOS)

    @app.route("/zangao/historico")
    def zangao_historico():
        return render_template("zangao.html", tela="historico", execucoes=zangao.execucoes(pasta_saida),
                               textos=zangao.TEXTOS)

    @app.route("/zangao/execucao/<execucao_id>")
    def zangao_execucao(execucao_id):
        e = next((e for e in zangao.execucoes(pasta_saida) if e["id"] == execucao_id), None) or abort(404)
        return render_template("zangao.html", tela="execucao", e=e, textos=zangao.TEXTOS)

    @app.route("/zangao/andamento")
    def zangao_andamento():
        return jsonify(zangao.andamento(pasta_zangao, pasta_saida))

    @app.route("/zangao/status")
    def zangao_status():
        return jsonify(zangao.status(pasta_zangao))

    @app.route("/zangao/rodar", methods=["POST"])
    def zangao_rodar():
        """Roda o Zangão em segundo plano: {"modo": "teste"} (simula) ou {"modo": "gravar"}."""
        if not _mesma_origem():
            return jsonify(erro="pedido recusado"), 403
        modo = (request.get_json(silent=True) or {}).get("modo")
        try:
            info = zangao.rodar(pasta_zangao, modo)
        except zangao.ZangaoErro as e:
            return jsonify(erro=str(e), **zangao.status(pasta_zangao)), 409
        log.info("Zangão disparado pela vila (%s) por %s", modo, request.remote_addr)
        return jsonify(info)

    @app.route("/jarvis")
    def jarvis_pagina():
        """Planilhas do relatório mensal geradas pelo Jarvis, para baixar."""
        return render_template("jarvis.html", info=jarvis.status(pasta_jarvis), planilhas=jarvis.planilhas(pasta_jarvis))

    @app.route("/jarvis/planilha/<mes>/<nome>")
    def jarvis_planilha(mes, nome):
        teste = request.args.get("teste") == "1"
        arquivo = jarvis.planilha(pasta_jarvis, mes, nome, teste) or abort(404)
        return send_file(arquivo, as_attachment=True, download_name=(f"TESTE {nome}" if teste else nome))

    @app.route("/jarvis/status")
    def jarvis_status():
        return jsonify(jarvis.status(pasta_jarvis))

    @app.route("/jarvis/rodar", methods=["POST"])
    def jarvis_rodar():
        """Roda o Jarvis em segundo plano com os grupos escolhidos na página /jarvis:
        {"modo": "mes" | "teste", "grupos": ["CASA DO CELULAR", ...]}."""
        if not _mesma_origem():
            return jsonify(erro="pedido recusado"), 403
        pedido = request.get_json(silent=True) or {}
        modo, escolhidos = pedido.get("modo"), pedido.get("grupos")
        try:
            info = jarvis.rodar(pasta_jarvis, modo, escolhidos)
        except jarvis.JarvisErro as e:
            return jsonify(erro=str(e), **jarvis.status(pasta_jarvis)), 409
        log.info("Jarvis disparado (%s, %d grupo(s)) por %s", modo, len(escolhidos), request.remote_addr)
        return jsonify(info)

    @app.route("/orelha")
    def orelha_pagina():
        """Arquivo do Orelha: quando o relatório roda e todos os relatórios do dia já feitos."""
        todos = orelha.relatorios(pasta_orelha)
        return render_template("orelha.html", info=orelha.status(pasta_orelha), pasta=pasta_orelha,
                               reais=[r for r in todos if not r["simulado"]],
                               simulados=[r for r in todos if r["simulado"]],
                               painel=orelha.painel_status(pasta_orelha),
                               paineis=[p for p in orelha.paineis(pasta_orelha) if not p["simulado"]])

    @app.route("/orelha/relatorio/<dia>/<nome>")
    def orelha_relatorio(dia, nome):
        """Abre o relatório guardado (HTML ou PDF) ou baixa a planilha .csv daquele dia."""
        arquivo = orelha.arquivo(pasta_orelha, dia, nome) or abort(404)
        if nome.endswith(".csv"):
            return send_file(arquivo, as_attachment=True, download_name=nome)
        return send_file(arquivo, mimetype=orelha.ARQUIVOS[nome])

    @app.route("/orelha/painel/rodar", methods=["POST"])
    def orelha_painel_rodar():
        """Botão "Gerar painel semanal": abre o Orelha em segundo plano só com o painel (PDF no papel timbrado)."""
        if not _mesma_origem():
            return jsonify(erro="pedido recusado"), 403
        # período escolhido na página (campos "De" e "Até", AAAA-MM-DD); vazio = o padrão do Orelha
        dados = request.get_json(silent=True) or {}
        try:
            de, ate = (date.fromisoformat(dados[k]) if dados.get(k) else None for k in ("de", "ate"))
        except (TypeError, ValueError):
            return jsonify(erro="data inválida", **orelha.painel_status(pasta_orelha)), 400
        if de and ate and (ate - de).days > 120:
            return jsonify(erro="escolha um período de até 120 dias", **orelha.painel_status(pasta_orelha)), 400
        try:
            info = orelha.rodar_painel(pasta_orelha, de, ate)
        except orelha.PainelErro as e:
            return jsonify(erro=str(e), **orelha.painel_status(pasta_orelha)), 409
        log.info("Painel semanal do Orelha disparado por %s", request.remote_addr)
        return jsonify(info)

    @app.route("/orelha/painel/status")
    def orelha_painel_status():
        """Se o painel está sendo gerado e qual é o último pronto (a página consulta enquanto espera)."""
        return jsonify(orelha.painel_status(pasta_orelha))

    @app.route("/orelha/status")
    def orelha_status():
        """Para a vila: horário, próximo relatório, se o de hoje atrasou e quantos estão guardados
        (só datas e contagens)."""
        return jsonify(orelha.status(pasta_orelha))

    @app.route("/vila")
    def vila():
        """A vila (HTML único e estático, só assiste aos eventos)."""
        if not ARQUIVO_VILA.exists():
            return Response("<!doctype html><meta charset=utf-8><body style='background:#0a0c11;color:#e6e9ef;"
                            "font:16px system-ui;padding:40px'><h1>A vila ainda não foi instalada</h1><p>Coloque o "
                            f"arquivo em <code>{ARQUIVO_VILA}</code>. Os eventos já estão em "
                            "<a style='color:#ff5a3c' href='/eventos'>/eventos</a>.</p>", 404,
                            {"Content-Type": "text/html; charset=utf-8"})
        return Response(ARQUIVO_VILA.read_bytes(), 200, {"Content-Type": "text/html; charset=utf-8",
                                                         "Cache-Control": "no-cache"})

    @app.route("/vila/sam")
    def vila_sam():
        """A vila do Sam: a Fortaleza do Dragão (HTML único, só assiste aos eventos do Sam em /eventos)."""
        return Response(ARQUIVO_FORTALEZA.read_bytes(), 200, {"Content-Type": "text/html; charset=utf-8",
                                                              "Cache-Control": "no-cache"})

    def _rodar(envio_id, envio):
        """Entra no VIOS uma vez e lança CI por CI (as que não têm problema)."""
        driver = None
        try:
            aptas = [c for c in envio["cis"] if not c["problemas"] and not c["ja_lancada"]]
            log.info("Envio do arquivo %s: %d CI(s) — %s", envio["arquivo"], len(aptas),
                     "GRAVANDO no VIOS" if envio["confirmar"] else "MODO TESTE (não grava)")
            emitir = lambda tipo, **d: eventos.emitir(pasta_saida, envio_id, tipo, **d)
            emitir("fase", fase="entrando_vios")
            driver = criar_driver(cfg.headless, False, cfg.navegador_rapido)
            fazer_login(driver, cfg)
            envio["fase"] = "duplicatas"
            emitir("fase", fase="conferindo_duplicatas")
            seguir = conferir_duplicatas_no_vios(driver, aptas, _capturas(pasta_saida), lancadas(), cfg.timeout)
            for c in aptas:
                if c not in seguir:  # cópia (não lançada) ou erro ao conferir
                    for t in c["tarefas"]:
                        emitir("ci", ci=c["ci"], tarefa=t["nome"],
                               etapa="duplicata" if c.get("resultado") == "duplicada" else "erro",
                               **({"motivo": c["mensagens"][0]} if c.get("mensagens") else {}))
            aptas = seguir
            envio["fase"] = "lancando"
            emitir("fase", fase="criando_tarefas")
            for c in aptas:
                c["resultado"] = "lançando"
                no_quadro = set()

                def ao_adicionar(i, c=c, no_quadro=no_quadro):
                    if 1 <= i <= len(c["tarefas"]):
                        no_quadro.add(i)
                        emitir("ci", ci=c["ci"], tarefa=c["tarefas"][i - 1]["nome"], etapa="no_quadro")
                coletor = _Coletor(ao_adicionar)
                c["mensagens"] = coletor.linhas  # a página acompanha as linhas enquanto lança
                logging.getLogger("bot.lancamento").addHandler(coletor)
                try:
                    feitas, erros = lancar(driver, [c], [c["ci"]], pasta_saida, Path("logs"), cfg.timeout,
                                           confirmar=envio["confirmar"])
                except Exception as e:
                    feitas, erros = 0, 1
                    coletor.linhas.append(str(e))
                finally:
                    logging.getLogger("bot.lancamento").removeHandler(coletor)
                c["mensagens"] = coletor.linhas
                if erros:
                    c["resultado"] = "erro"
                elif any("já tem tarefa no VIOS" in l or "já foi lançada" in l for l in coletor.linhas):
                    c["resultado"] = "pulada"
                elif not envio["confirmar"]:
                    c["resultado"] = "testada"
                else:
                    c["resultado"] = "gravada"
                    c["ja_lancada"] = True
                salvar_envio(pasta_saida, envio_id, envio)  # cada CI fica registrada assim que termina
                # vila: resultado de cada tarefa (no teste, a tarefa para em "no_quadro")
                for i, t in enumerate(c["tarefas"], 1):
                    if c["resultado"] == "gravada":
                        emitir("ci", ci=c["ci"], tarefa=t["nome"], etapa="gravada", tarefa_num=f"{c['ci']}-{i}")
                    elif c["resultado"] == "pulada":
                        emitir("ci", ci=c["ci"], tarefa=t["nome"], etapa="ja_tinha")
                    elif c["resultado"] == "erro":
                        emitir("ci", ci=c["ci"], tarefa=t["nome"], etapa="erro",
                               motivo=(coletor.linhas or ["erro ao lançar"])[-1][:200])
            envio["estado"] = "concluido" if envio["confirmar"] else "testado"
        except Exception as e:
            log.exception("Falha no envio do arquivo %s", envio["arquivo"])
            envio["estado"] = "falhou"
            envio["falha"] = str(e)
        finally:
            envio["fase"] = ""
            envio["fim"] = datetime.now()
            try:
                salvar_envio(pasta_saida, envio_id, envio)
            except Exception:
                log.exception("Não consegui gravar o histórico do envio %s", envio_id)
            evento_fim(pasta_saida, envio_id, envio)
            if driver:
                driver.quit()
            trava.release()

    return app
