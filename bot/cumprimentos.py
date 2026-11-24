"""Cumprimentos de sentença: a aba da Vila dos Bots com os alertas do vigia do pje-busca.

O vigia (pasta pje-busca/ deste repositório ou PJE_BUSCA_PASTA) consulta todo dia a API pública do DJEN pelo nome
de cada empresa da lista do VIOS (área Trabalhista, cliente no polo passivo) e grava em dados/vigia.sqlite os
processos do TRT7 contra o cliente que NÃO estão no VIOS. Esta aba:
- só LÊ esse banco (sqlite em modo somente leitura): nada do pje-busca é importado e nada no banco é alterado;
- mostra em destaque os cumprimentos de sentença / execuções (nível VERMELHO do vigia) e, à parte, as ações de
  cumprimento (sindicato cobrando convenção coletiva, que não são cumprimento de sentença);
- guarda a conferência da equipe (quem viu, o que foi feito) num JSON ao lado do banco, fora do git:
  dados/cumprimentos_conferencia.json;
- lista as empresas SEM nenhuma publicação no DJEN (o nome no tribunal pode ser outro): a equipe confere e, se for
  o caso, informa o nome certo em dados/nomes_conferidos.json, que o vigia passa a usar na busca seguinte;
- nível 3: mostra os "Processos associados" NOVOS que o vigia leu no PJe (vigia.py associados) — associado que não
  está no VIOS é alerta vermelho, com a mesma conferência da equipe; o botão "Verificar associados no PJe" abre
  `vigia.py associados` (usa o Chrome do Mac e o login pelo Presto; leva uns 10 a 15 minutos);
- o botão "Verificar agora" abre `vigia.py djen` em segundo plano (só a API pública do DJEN: sem login, sem
  CAPTCHA, sem senha), com ambiente limpo, uma execução por vez.
"""
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import unicodedata
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger(__name__)

PASTA_PADRAO = Path(__file__).resolve().parent.parent / "pje-busca"
SCRIPT = "vigia.py"
BANCO = Path("dados") / "vigia.sqlite"
CONFERENCIA = Path("dados") / "cumprimentos_conferencia.json"
NOMES = Path("dados") / "nomes_conferidos.json"  # lido pelo vigia (vigia_djen.nomes_conferidos)
EXECUCAO = Path("logs") / ".vila_djen.json"  # execução em andamento (pid, início)
LOG = Path("logs") / "djen_vila.log"  # saída de cada verificação disparada pela vila
COMANDOS = {"djen": "Verificação no DJEN", "associados": "Processos associados no PJe"}
# ação de cumprimento (art. 872 da CLT: sindicato cobrando a convenção) não é cumprimento de sentença
ACAO_CUMPRIMENTO = re.compile(r"^\s*A[ÇC][ÃA]O\s+DE\s+CUMPRIMENTO\b", re.I)
SITUACOES = {
    "pendente": "Pendente de conferência",
    "providencia": "Providência em curso (habilitação/defesa)",
    "habilitado": "Escritório já atua no processo",
    "nao_cliente": "Não é do escritório / falso alerta",
}
SITUACOES_NOME = {
    "pendente": "Pendente de conferência",
    "nome_corrigido": "Nome corrigido: o robô passa a buscar também por ele",
    "nome_certo": "Nome está certo (sem processo no TRT7)",
}
# processos do VIOS fora do acervo e dos arquivados do PJe, classificados pelo DJEN (vigia_associados.GRUPOS_FORA)
GRUPOS_FORA = {
    "sem_escritorio": ("Habilitação a conferir", "1º grau, sem advogado do escritório nas publicações do DJEN: "
                       "conferir se o escritório está habilitado no PJe (senão as intimações não chegam pelo painel)."),
    "so_pessoal": ("Sociedade fora do processo", "1º grau, com advogado do escritório nas publicações, mas fora do "
                   "acervo da sociedade: incluir a sociedade no processo."),
    "sem_publicacao": ("Sem publicação no DJEN", "Conferir no PJe onde está o processo."),
    "segundo_grau": ("2º grau / TST", "Recurso, TST ou ação originária do TRT: o acervo do 1º grau não mostra; "
                     "o DJEN acompanha."),
}
NUMERO_CNJ = re.compile(r"^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$")
DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# só o necessário: nenhuma variável do Ultron (senha da página, chaves) vai para o vigia
AMBIENTE = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TMPDIR", "LANG", "LC_ALL",
            "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA")
_trava = threading.Lock()


class CumprimentosErro(Exception):
    pass


def pasta(valor=None):
    """Pasta do pje-busca: PJE_BUSCA_PASTA do .env do Sam ou a pasta pje-busca/ deste repositório."""
    valor = os.path.expanduser((valor if valor is not None else os.getenv("PJE_BUSCA_PASTA", "")).strip())
    return Path(valor) if valor else PASTA_PADRAO


def configurado(pasta):
    """O vigia está instalado e já tem banco (rodou `vigia.py vios` ao menos uma vez)."""
    return bool(pasta) and (Path(pasta) / SCRIPT).exists() and (Path(pasta) / BANCO).exists()


def _conectar(pasta):
    caminho = (Path(pasta) / BANCO).resolve()
    db = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


def _tabela(db, nome):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nome,)).fetchone() is not None


def data_br(iso):
    return f"{iso[8:10]}/{iso[5:7]}/{iso[:4]}" if iso and DATA.match(iso[:10]) else (iso or "-")


def _dias(iso, hoje):
    try:
        return (hoje - date.fromisoformat(iso[:10])).days
    except (TypeError, ValueError):
        return None


def _nome_busca(nome):
    """Igual ao vigia_djen.nome_busca: tira "(MATRIZ)", "(FILIAL ...)", ": PRESTADORA" e espaços."""
    n = re.sub(r"\([^)]*\)", " ", nome or "").split(":")[0]
    return re.sub(r"\s+", " ", n).strip(" -")


def _normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).upper().split())


def _cnpj(c):
    c = re.sub(r"\D", "", c or "")
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else ""


def _ler_json(arquivo):
    try:
        dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def _gravar_json(arquivo, dados):
    temporario = Path(arquivo).with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    os.chmod(temporario, 0o600)
    os.replace(temporario, arquivo)


def nomes_conferidos(pasta):
    """{empresa: {"situacao", "nomes", "quem", "obs", "quando", "historico"}}."""
    return _ler_json(Path(pasta) / NOMES)


def _sem_publicacao_do_relatorio(pasta, chaves):
    """Antes da 1ª rodada com djen_consultas: lê a lista "Sem nenhuma publicação" do último relatório."""
    lista = relatorios(pasta)
    arquivo = relatorio(pasta, lista[0]["data"]) if lista else None
    if not arquivo:
        return None, []
    por_nome = {_normalizar(_nome_busca(c)): c for c in chaves}
    saida, dentro = [], False
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        if linha.startswith("Sem nenhuma publicação"):
            dentro = True
        elif dentro and linha.startswith("  - "):
            nomes = [n.strip() for n in linha[4:].split(" / ") if n.strip()]
            chave = por_nome.get(_normalizar(nomes[0])) if nomes else None
            if chave:
                saida.append((chave, nomes))
        elif dentro:
            break
    return lista[0]["data"], saida


def sem_publicacao(db, pasta):
    """Empresas cuja última busca no DJEN não achou nenhuma publicação, com o que ajuda a conferir o nome."""
    if not _tabela(db, "empresas"):
        return []
    empresas = {r["chave"]: dict(r) for r in db.execute("SELECT chave, nome, cnpj FROM empresas")}
    achados, data = [], None
    if _tabela(db, "djen_consultas") and db.execute("SELECT COUNT(*) FROM djen_consultas").fetchone()[0]:
        for r in db.execute("SELECT empresa, data, nomes FROM djen_consultas WHERE publicacoes = 0 ORDER BY empresa"):
            try:
                nomes = json.loads(r["nomes"] or "[]")
            except ValueError:
                nomes = []
            achados.append((r["empresa"], nomes, r["data"]))
    else:
        data, lista = _sem_publicacao_do_relatorio(pasta, list(empresas))
        achados = [(c, n, data) for c, n in lista]
    trt7 = {}
    if _tabela(db, "processos"):
        trt7 = {r[0]: r[1] for r in db.execute(
            "SELECT empresa, COUNT(*) FROM processos WHERE tribunal = '5.07' AND ativo = 1 GROUP BY empresa")}
    conf = nomes_conferidos(pasta)
    saida = []
    for chave, nomes, quando in achados:
        if chave not in empresas:
            continue
        c = conf.get(chave) or {}
        situacao = c.get("situacao") or "pendente"
        saida.append({"empresa": chave, "nome": empresas[chave]["nome"] or chave, "cnpj": _cnpj(empresas[chave]["cnpj"]),
                      "buscados": nomes, "data_br": data_br(quando), "processos_trt7": trt7.get(chave, 0),
                      "situacao": situacao, "situacao_texto": SITUACOES_NOME.get(situacao, situacao),
                      "nomes_informados": "; ".join(c.get("nomes") or []), "quem": c.get("quem", ""),
                      "obs": c.get("obs", ""), "quando": c.get("quando", "")})
    # pendentes em cima; entre eles, quem tem processo no TRT7 no VIOS (sinal forte de nome diferente) primeiro
    saida.sort(key=lambda e: (e["situacao"] != "pendente", -e["processos_trt7"], e["empresa"]))
    return saida


def conferir_nome(pasta, empresa, situacao, quem="", obs="", nomes="", agora=None):
    """Conferência de uma empresa sem publicação. Com "nome_corrigido", os nomes informados (separados por ";")
    vão para dados/nomes_conferidos.json e o vigia passa a buscar também por eles."""
    if not configurado(pasta):
        raise CumprimentosErro("o vigia do pje-busca não está instalado neste servidor")
    if situacao not in SITUACOES_NOME:
        raise CumprimentosErro("situação inválida")
    quem, obs = (quem or "").strip()[:60], (obs or "").strip()[:500]
    lista = [re.sub(r"\s+", " ", n).strip().upper() for n in re.split(r"[;\n]", nomes or "")]
    lista = list(dict.fromkeys(n for n in lista if n))
    if any(len(n) < 3 or len(n) > 120 for n in lista) or len(lista) > 3:
        raise CumprimentosErro("informe até 3 nomes, cada um com 3 a 120 letras")
    if situacao == "nome_corrigido" and not lista:
        raise CumprimentosErro("informe o nome da empresa como está no tribunal")
    if situacao != "pendente" and not quem:
        raise CumprimentosErro("informe quem conferiu")
    db = _conectar(pasta)
    try:
        existe = _tabela(db, "empresas") and db.execute("SELECT 1 FROM empresas WHERE chave = ?", (empresa or "",)).fetchone()
    finally:
        db.close()
    if not existe:
        raise CumprimentosErro("empresa fora da lista do vigia")
    registro = {"situacao": situacao, "nomes": lista if situacao == "nome_corrigido" else [], "quem": quem, "obs": obs,
                "quando": (agora or datetime.now()).isoformat(timespec="seconds")}
    with _trava:
        tudo = nomes_conferidos(pasta)
        atual = tudo.get(empresa) or {}
        atual["historico"] = (atual.get("historico") or []) + [registro]
        atual.update(registro)
        tudo[empresa] = atual
        _gravar_json(Path(pasta) / NOMES, tudo)
    log.info("Nome da empresa conferido (%s)", situacao)
    return atual


def conferencias(pasta):
    """{numero: {"situacao", "quem", "obs", "quando", "historico": [...]}}."""
    return _ler_json(Path(pasta) / CONFERENCIA)


def _item(r, conf, hoje, principais=None):
    c = conf.get(r["numero"]) or {}
    x = (principais or {}).get(r["numero"])
    situacao = c.get("situacao") or "pendente"
    return {"numero": r["numero"], "empresa": r["empresa"] or "-", "classe": (r["classe"] or "-").upper(),
            "orgao": r["orgao"] or "-", "primeira_publicacao": r["primeira_publicacao"] or "",
            "primeira_br": data_br(r["primeira_publicacao"]), "dias": _dias(r["primeira_publicacao"], hoje),
            "tipo": r["tipo"] or "-", "visto_br": data_br(r["visto_em"]), "situacao": situacao,
            "situacao_texto": SITUACOES.get(situacao, situacao), "quem": c.get("quem", ""), "obs": c.get("obs", ""),
            "quando": c.get("quando", ""),
            # processo principal achado pelo vigia (djen_principais): no VIOS = cliente nosso
            "principal": (x["principal"] or "") if x else "", "principal_ci": (x["ci"] or "") if x else "",
            "principal_empresa": (x["empresa"] or "") if x else "", "principal_advogado": (x["advogado"] or "") if x else "",
            "principal_como": (x["como"] or "") if x else "", "exequente": (x["exequente"] or "") if x else "",
            "principal_verificado": x is not None}


def _associados(db, conf, hoje):
    """Nível 3: associados novos (depois da base) e a última rodada no PJe."""
    out = {"rodada": None, "alertas": [], "pendentes": 0, "principais": 0, "fora_acervo": 0, "arquivados_vios": [],
           "base_conferir": [], "fora": [], "fora_contagem": {}}
    if not _tabela(db, "assoc_associados"):
        return out
    r = db.execute("SELECT * FROM assoc_rodadas ORDER BY data DESC LIMIT 1").fetchone() \
        if _tabela(db, "assoc_rodadas") else None
    if r:
        out["rodada"] = dict(r, data_br=data_br(r["data"]), dias=_dias(r["data"], hoje))
    if _tabela(db, "assoc_principais"):
        out["principais"] = db.execute("SELECT COUNT(*) FROM assoc_principais WHERE situacao = 'ok'").fetchone()[0]
        out["fora_acervo"] = db.execute(
            "SELECT COUNT(*) FROM assoc_principais WHERE situacao = 'fora_do_acervo'").fetchone()[0]
    vios = {}
    if _tabela(db, "processos"):
        vios = {x["numero"]: x for x in db.execute("SELECT numero, ci, empresa, advogado FROM processos")}
    if _tabela(db, "assoc_principais"):
        # ativos no VIOS, mas arquivados no PJe: a equipe atualiza o VIOS
        for x in db.execute("SELECT numero, verificado_em FROM assoc_principais WHERE situacao = 'arquivado_pje' "
                            "ORDER BY numero"):
            p = vios.get(x["numero"]) or {}
            out["arquivados_vios"].append({"numero": x["numero"], "ci": p["ci"] if p else "",
                                           "empresa": p["empresa"] if p else "", "advogado": p["advogado"] if p else "",
                                           "visto_br": data_br(x["verificado_em"])})
    djen = {x[0] for x in db.execute("SELECT numero FROM djen_processos")} if _tabela(db, "djen_processos") else set()
    for a in db.execute("SELECT * FROM assoc_associados WHERE novo = 1 ORDER BY visto_em DESC, associado"):
        c = conf.get(a["associado"]) or {}
        situacao = c.get("situacao") or "pendente"
        p = vios.get(a["principal"]) or {}
        out["alertas"].append({
            "numero": a["associado"], "orgao": a["orgao"] or "-", "principal": a["principal"],
            "principal_ci": p["ci"] if p else "", "empresa": p["empresa"] if p else "",
            "advogado": p["advogado"] if p else "", "visto_br": data_br(a["visto_em"]),
            "dias": _dias(a["visto_em"], hoje), "vermelho": a["nivel"] == "VERMELHO", "amarelo": a["nivel"] == "AMARELO",
            "no_vios": a["associado"] in vios, "no_djen": a["associado"] in djen, "situacao": situacao,
            "situacao_texto": SITUACOES.get(situacao, situacao), "quem": c.get("quem", ""), "obs": c.get("obs", ""),
            "quando": c.get("quando", "")})
    out["alertas"].sort(key=lambda i: (i["situacao"] != "pendente", not i["vermelho"], not i["amarelo"], i["dias"] or 0))
    # base: associados que já existiam, de principais do VIOS, que não estão no VIOS (conferir uma vez)
    for a in db.execute("SELECT * FROM assoc_associados WHERE novo = 0 ORDER BY principal, associado"):
        if a["principal"] not in vios or a["associado"] in vios:
            continue
        c = conf.get(a["associado"]) or {}
        situacao = c.get("situacao") or "pendente"
        p = vios[a["principal"]]
        out["base_conferir"].append({
            "numero": a["associado"], "orgao": a["orgao"] or "-", "principal": a["principal"], "principal_ci": p["ci"],
            "empresa": p["empresa"], "advogado": p["advogado"], "no_djen": a["associado"] in djen,
            "situacao": situacao, "situacao_texto": SITUACOES.get(situacao, situacao), "quem": c.get("quem", ""),
            "obs": c.get("obs", ""), "quando": c.get("quando", "")})
    out["base_conferir"].sort(key=lambda i: (i["situacao"] != "pendente", i["principal"]))
    # processos do VIOS fora do acervo e dos arquivados, classificados pelo DJEN (vigia.py fora / associados)
    if _tabela(db, "assoc_fora"):
        ordem = list(GRUPOS_FORA)
        for f in db.execute("SELECT * FROM assoc_fora"):
            c = conf.get(f["numero"]) or {}
            situacao = c.get("situacao") or "pendente"
            p = vios.get(f["numero"]) or {}
            out["fora"].append({
                "numero": f["numero"], "grupo": f["grupo"], "grupo_titulo": GRUPOS_FORA.get(f["grupo"], (f["grupo"], ""))[0],
                "orgao": f["orgao"] or "-", "classe": (f["classe"] or "-").upper(), "ultima_br": data_br(f["ultima"]),
                "ci": p["ci"] if p else "", "empresa": p["empresa"] if p else "", "advogado": p["advogado"] if p else "",
                "situacao": situacao, "situacao_texto": SITUACOES.get(situacao, situacao), "quem": c.get("quem", ""),
                "obs": c.get("obs", ""), "quando": c.get("quando", "")})
        out["fora"].sort(key=lambda i: (ordem.index(i["grupo"]) if i["grupo"] in ordem else 9,
                                        i["situacao"] != "pendente", i["numero"]))
        for i in out["fora"]:
            out["fora_contagem"][i["grupo"]] = out["fora_contagem"].get(i["grupo"], 0) + 1
    out["pendentes"] = sum(1 for i in out["alertas"] if i["situacao"] == "pendente" and i["vermelho"])
    return out


def painel(pasta, hoje=None):
    """Tudo o que a página mostra. Só leitura do banco do vigia."""
    hoje = hoje or date.today()
    info = {"configurado": configurado(pasta), "rodada": None, "vermelhos": [], "acoes": [], "outros": 0,
            "empresas": 0, "processos_vios": 0, "pendentes": 0, "maior_espera": None, "relatorios": [],
            "sem_publicacao": [], "sem_pub_pendentes": 0,
            "assoc": {"rodada": None, "alertas": [], "pendentes": 0, "principais": 0, "fora_acervo": 0,
                      "arquivados_vios": [], "base_conferir": [], "fora": [], "fora_contagem": {}}}
    if not info["configurado"]:
        return info
    conf = conferencias(pasta)
    db = _conectar(pasta)
    try:
        if _tabela(db, "empresas"):
            info["empresas"] = db.execute("SELECT COUNT(*) FROM empresas").fetchone()[0]
        if _tabela(db, "processos"):
            info["processos_vios"] = db.execute("SELECT COUNT(*) FROM processos WHERE ativo = 1").fetchone()[0]
        if _tabela(db, "djen_rodadas"):
            r = db.execute("SELECT * FROM djen_rodadas ORDER BY data DESC LIMIT 1").fetchone()
            if r:
                info["rodada"] = dict(r, data_br=data_br(r["data"]), dias=_dias(r["data"], hoje))
        principais = {}
        if _tabela(db, "djen_principais"):
            principais = {r["numero"]: r for r in db.execute("SELECT * FROM djen_principais")}
        if _tabela(db, "djen_processos"):
            for r in db.execute("SELECT * FROM djen_processos ORDER BY primeira_publicacao DESC, numero"):
                if r["nivel"] == "VERMELHO":
                    info["vermelhos"].append(_item(r, conf, hoje, principais))
                elif ACAO_CUMPRIMENTO.search(r["classe"] or ""):
                    info["acoes"].append(_item(r, conf, hoje))
                else:
                    info["outros"] += 1
        info["sem_publicacao"] = sem_publicacao(db, pasta)
        info["assoc"] = _associados(db, conf, hoje)
    finally:
        db.close()
    # pendentes primeiro; dentro de cada grupo, a publicação mais recente em cima
    info["vermelhos"].sort(key=lambda i: (i["situacao"] != "pendente", i["dias"] is None, i["dias"] or 0))
    pend = [i for i in info["vermelhos"] if i["situacao"] == "pendente"]
    info["pendentes"] = len(pend)
    info["maior_espera"] = max((i["dias"] for i in pend if i["dias"] is not None), default=None)
    info["relatorios"] = relatorios(pasta)[:10]
    info["relatorios_assoc"] = relatorios(pasta, "associados")[:10]
    info["sem_pub_pendentes"] = sum(1 for e in info["sem_publicacao"] if e["situacao"] == "pendente")
    return info


def resumo(pasta):
    """Para o cartão da Vila dos Bots: só contagens e a data da última verificação."""
    try:
        p = painel(pasta)
    except sqlite3.Error:
        log.exception("Não consegui ler o banco do vigia")
        return {"configurado": False}
    pend = lambda lst: sum(1 for i in lst if i["situacao"] == "pendente")  # noqa: E731
    return {"configurado": p["configurado"], "pendentes": p["pendentes"], "total": len(p["vermelhos"]),
            "ultima": p["rodada"]["data_br"] if p["rodada"] else None, "sem_pub_pendentes": p["sem_pub_pendentes"],
            "assoc_pendentes": p["assoc"]["pendentes"], "base_pendentes": pend(p["assoc"]["base_conferir"]),
            "habilitacao_pendentes": pend([i for i in p["assoc"]["fora"] if i["grupo"] == "sem_escritorio"]),
            "assoc_ultima": p["assoc"]["rodada"]["data_br"] if p["assoc"]["rodada"] else None}


def conferir(pasta, numero, situacao, quem="", obs="", agora=None):
    """Grava a conferência de um processo da lista (cumprimento ou ação de cumprimento). Guarda o histórico."""
    if not configurado(pasta):
        raise CumprimentosErro("o vigia do pje-busca não está instalado neste servidor")
    numero = (numero or "").strip()
    if not NUMERO_CNJ.match(numero):
        raise CumprimentosErro("número de processo inválido")
    if situacao not in SITUACOES:
        raise CumprimentosErro("situação inválida")
    quem, obs = (quem or "").strip()[:60], (obs or "").strip()[:500]
    if situacao != "pendente" and not quem:
        raise CumprimentosErro("informe quem conferiu")
    db = _conectar(pasta)
    try:
        existe = (_tabela(db, "djen_processos") and db.execute(
            "SELECT 1 FROM djen_processos WHERE numero = ?", (numero,)).fetchone()) or \
            (_tabela(db, "assoc_associados") and db.execute(
                "SELECT 1 FROM assoc_associados WHERE associado = ?", (numero,)).fetchone()) or \
            (_tabela(db, "assoc_fora") and db.execute("SELECT 1 FROM assoc_fora WHERE numero = ?", (numero,)).fetchone())
    finally:
        db.close()
    if not existe:
        raise CumprimentosErro("processo fora da lista do vigia")
    quando = (agora or datetime.now()).isoformat(timespec="seconds")
    with _trava:
        tudo = conferencias(pasta)
        atual = tudo.get(numero) or {"historico": []}
        registro = {"situacao": situacao, "quem": quem, "obs": obs, "quando": quando}
        atual["historico"] = (atual.get("historico") or []) + [registro]
        atual.update(registro)
        tudo[numero] = atual
        _gravar_json(Path(pasta) / CONFERENCIA, tudo)
    log.info("Cumprimento %s marcado como %s", numero, situacao)
    return atual


TIPOS_RELATORIO = ("djen", "associados")


def relatorios(pasta, tipo="djen"):
    """Relatórios guardados pelo vigia (saida/<tipo>_AAAA-MM-DD.txt), do mais novo ao mais antigo."""
    saida, prefixo = Path(pasta) / "saida", f"{tipo}_"
    datas = [x.stem[len(prefixo):] for x in saida.glob(f"{prefixo}*.txt") if DATA.match(x.stem[len(prefixo):])]
    return [{"data": d, "data_br": data_br(d), "tipo": tipo} for d in sorted(datas, reverse=True)]


def relatorio(pasta, data, tipo="djen"):
    """Caminho do relatório daquele dia (None se não existe; nada fora da pasta saida/)."""
    if not DATA.match(data or "") or tipo not in TIPOS_RELATORIO:
        return None
    arquivo = Path(pasta) / "saida" / f"{tipo}_{data}.txt"
    return arquivo if arquivo.is_file() else None


def _vivo(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        cmd = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True,
                             timeout=5).stdout
    except Exception:
        return True
    return SCRIPT in cmd


def status(pasta):
    """{"configurado", "rodando", "inicio", "comando", "comando_texto"}."""
    info = {"configurado": configurado(pasta), "rodando": False, "inicio": None, "comando": None, "comando_texto": ""}
    try:
        atual = json.loads((Path(pasta) / EXECUCAO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        atual = None
    if atual and _vivo(int(atual.get("pid", 0))):
        comando = atual.get("comando") or "djen"
        info.update(rodando=True, inicio=atual.get("inicio"), comando=comando, comando_texto=COMANDOS.get(comando, comando))
    return info


def rodar(pasta, python=None, comando="djen"):
    """Abre `vigia.py djen` (ou `vigia.py associados`) em segundo plano, uma execução por vez. Devolve o status;
    levanta CumprimentosErro se não pode rodar."""
    if comando not in COMANDOS:
        raise CumprimentosErro("verificação inválida")
    if not configurado(pasta):
        raise CumprimentosErro("o vigia do pje-busca não está instalado neste servidor (rode antes: "
                               "cd pje-busca && python3 vigia.py vios)")
    with _trava:
        if status(pasta)["rodando"]:
            raise CumprimentosErro("a verificação já está rodando")
        pasta = Path(pasta)
        (pasta / "logs").mkdir(exist_ok=True)
        ambiente = {k: os.environ[k] for k in AMBIENTE if k in os.environ}
        ambiente["PYTHONUTF8"] = "1"
        inicio = datetime.now().isoformat(timespec="seconds")
        saida = open(pasta / LOG, "a", encoding="utf-8")
        saida.write(f"\n===== {inicio} · vigia {comando} (pela vila) =====\n")
        saida.flush()
        extra = {"start_new_session": True} if os.name != "nt" else {}
        # o vigia só usa a biblioteca padrão do Python: serve o mesmo Python do servidor
        proc = subprocess.Popen([python or sys.executable, SCRIPT, comando], cwd=pasta, env=ambiente,
                                stdin=subprocess.DEVNULL, stdout=saida, stderr=subprocess.STDOUT, **extra)
        saida.close()
        arquivo = pasta / EXECUCAO
        arquivo.write_text(json.dumps({"pid": proc.pid, "inicio": inicio, "comando": comando}), encoding="utf-8")
        log.info("Vigia %s iniciado pela vila, pid %d", comando, proc.pid)

        def esperar():
            codigo = proc.wait()
            log.info("Vigia %s terminou (código %s)", comando, codigo)
            try:
                if json.loads(arquivo.read_text(encoding="utf-8")).get("pid") == proc.pid:
                    arquivo.unlink()
            except (OSError, ValueError):
                pass

        threading.Thread(target=esperar, daemon=True).start()
    return status(pasta)
