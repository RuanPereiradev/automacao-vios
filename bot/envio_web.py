"""Página de envio: a pessoa sobe o .txt com as tarefas já ajustadas (análise feita no chat),
confere o que vai ser gravado e o robô lança no VIOS. Não usa a IA (sem gasto de tokens)."""
import hmac
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, Response, abort, redirect, render_template, request, url_for

from bot import config, duplicidade, envio_txt, skill
from bot.lancamento import REGISTRO, lancar, ler_intimacao
from bot.login import fazer_login
from bot.navegador import criar_driver

log = logging.getLogger(__name__)
# dá para editar e enviar de novo (o que já foi gravado fica como "Já lançada")
EDITAVEIS = ("conferir", "testado", "falhou", "concluido")


class _Coletor(logging.Handler):
    """Guarda as mensagens do lançamento de uma CI, para mostrar na página."""

    def __init__(self):
        super().__init__(logging.INFO)
        self.linhas = []

    def emit(self, record):
        msg = record.getMessage()
        if not msg.startswith(("Observação:", "Quadro Tarefas")):
            self.linhas.append(msg.splitlines()[0])


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


def _duplicadas(pasta_saida):
    """{ci: CI original}: cópias marcadas na captura ou na análise do bot e as que o detector
    acha nas capturas salvas (1ª conferência, na subida do .txt)."""
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
    devolve as CIs que podem ser lançadas."""
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
            cis.append({"ci": form[f"g{g}_ci"].strip(), "tarefas": tarefas})
        g += 1
    return cis


def criar_app(caminho_env=".env", pasta_skill=None, senha=""):
    """senha: exigida (usuário qualquer) quando a página fica aberta na rede."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.before_request
    def exigir_senha():
        if not senha:
            return None
        auth = request.authorization
        if auth and hmac.compare_digest((auth.password or "").encode(), senha.encode()):
            return None
        return Response("Senha necessária.", 401, {"WWW-Authenticate": 'Basic realm="Envio ao VIOS", charset="UTF-8"'})

    cfg = config.carregar(caminho_env)
    oficiais = skill.tarefas_oficiais(pasta_skill or "doc/analise-intimacoes-controladoria")
    partes = urlsplit(cfg.url)
    base_url = f"{partes.scheme}://{partes.netloc}/"
    pasta_saida = Path(cfg.pasta_saida)
    arquivo_pessoas = pasta_saida / "responsaveis.json"
    envios = {}  # id -> {arquivo, cis, estado, confirmar, ...}
    trava = threading.Lock()  # um envio por vez (um navegador só)

    def lancadas():
        arquivo = pasta_saida / REGISTRO
        return json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}

    def pessoas():
        return json.loads(arquivo_pessoas.read_text(encoding="utf-8")) if arquivo_pessoas.exists() else []

    def conferir(texto):
        """Lê o .txt e confere cada CI (a mesma conferência na subida e depois de editar)."""
        return envio_txt.ler(texto, oficiais, pessoas(), lancadas(), _links_capturados(pasta_saida), base_url,
                             duplicadas=_duplicadas(pasta_saida))

    @app.route("/")
    def inicio():
        recentes = sorted(envios.items(), key=lambda e: e[1]["criado"], reverse=True)[:10]
        return render_template("envio.html", tela="inicio", recentes=recentes, ocupado=trava.locked())

    @app.route("/ler", methods=["POST"])
    def ler():
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            return render_template("envio.html", tela="inicio", erro="Escolha o arquivo .txt.", recentes=[], ocupado=trava.locked())
        bruto = arquivo.read()
        try:
            texto = bruto.decode("utf-8-sig")
        except UnicodeDecodeError:
            texto = bruto.decode("cp1252")  # salvo pelo Bloco de Notas antigo
        cis = conferir(texto)
        if not cis:
            return render_template("envio.html", tela="inicio", recentes=[], ocupado=trava.locked(),
                                   erro="Nenhum bloco encontrado. Confira o formato (CI:, TAREFA:, DATA:, ..., DESCRIÇÃO:).")
        envio_id = uuid.uuid4().hex[:8]
        envios[envio_id] = {"arquivo": arquivo.filename, "cis": cis, "estado": "conferir",
                            "criado": datetime.now(), "confirmar": False}
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
                               editavel=envio["estado"] in EDITAVEIS, oficiais=oficiais, pessoas=pessoas(),
                               texto=envio_txt.gerar(envio["cis"]))

    @app.route("/envio/<envio_id>/salvar", methods=["POST"])
    def salvar(envio_id):
        """Edição na página: refaz o .txt com os campos (ou com o texto colado) e confere de novo."""
        envio = envios.get(envio_id) or abort(404)
        if envio["estado"] not in EDITAVEIS:
            return redirect(url_for("ver", envio_id=envio_id))
        texto = request.form["texto"] if request.form.get("modo") == "texto" else envio_txt.gerar(_cis_do_form(request.form))
        envio["cis"] = conferir(texto)
        envio["estado"] = "conferir"  # mudou: o teste anterior não vale mais
        envio["editado"] = datetime.now()
        return redirect(url_for("ver", envio_id=envio_id))

    @app.route("/envio/<envio_id>/enviar", methods=["POST"])
    def enviar(envio_id):
        envio = envios.get(envio_id) or abort(404)
        if envio["estado"] not in EDITAVEIS:
            return redirect(url_for("ver", envio_id=envio_id))
        if not trava.acquire(blocking=False):
            return redirect(url_for("ver", envio_id=envio_id))
        envio["confirmar"] = bool(request.form.get("confirmar"))
        envio["estado"] = "enviando"
        envio["inicio"] = datetime.now()
        for c in envio["cis"]:
            c.pop("resultado", None)
            c.pop("mensagens", None)
        threading.Thread(target=_rodar, args=(envio,), daemon=True).start()
        return redirect(url_for("ver", envio_id=envio_id))

    def _rodar(envio):
        """Entra no VIOS uma vez e lança CI por CI (as que não têm problema)."""
        driver = None
        try:
            aptas = [c for c in envio["cis"] if not c["problemas"] and not c["ja_lancada"]]
            log.info("Envio do arquivo %s: %d CI(s) — %s", envio["arquivo"], len(aptas),
                     "GRAVANDO no VIOS" if envio["confirmar"] else "MODO TESTE (não grava)")
            driver = criar_driver(cfg.headless, False)
            fazer_login(driver, cfg)
            aptas = conferir_duplicatas_no_vios(driver, aptas, _capturas(pasta_saida), lancadas(), cfg.timeout)
            for c in aptas:
                c["resultado"] = "lançando"
                coletor = _Coletor()
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
            envio["estado"] = "concluido" if envio["confirmar"] else "testado"
        except Exception as e:
            log.exception("Falha no envio do arquivo %s", envio["arquivo"])
            envio["estado"] = "falhou"
            envio["falha"] = str(e)
        finally:
            envio["fim"] = datetime.now()
            if driver:
                driver.quit()
            trava.release()

    return app
