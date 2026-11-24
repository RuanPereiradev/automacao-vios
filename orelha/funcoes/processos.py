"""Processos da área: TODOS os processos de uma área do VIOS (padrão: Previdenciária, id 4), ativos e
encerrados, numa planilha (CSV que abre no Excel) e num JSON. Só leitura: pesquisas GET na lista de
processos (processos-lista.php), buscadas de dentro da página, sem desenhar a tela.

Visto ao vivo em 17/11/2026: a lista devolve no máximo 500 processos por pesquisa, mesmo pedindo
pesq[limit]=9999999. Quando vem cheia, a leitura é por período de cadastro (um ano por vez,
dividindo ao meio o período que vier cheio), como na função parados.

Tarefas: duas pesquisas a mais nos ativos, com o filtro nativo "Com ou sem tipo de tarefa? = Sem"
(Abertas e Todas), marcam cada ativo como "com tarefa aberta", "sem tarefa aberta" ou "nenhuma tarefa".

Não entra no relatório do dia (RELATORIO_DIARIO = False). Gera em saida/<AAAA-MM-DD>/:
    processos-<área>.csv   separado por ";", UTF-8 com BOM (acentos certos no Excel), em blocos:
                           ATIVOS, ENCERRADOS e ATIVOS SEM TAREFA ABERTA
    processos-<área>.json  os mesmos dados, para outros bots
Os arquivos têm nomes de clientes: ficam em orelha/saida/, fora do git.

.env:
    ORELHA_PROCESSOS_AREAS        ids das áreas, separados por vírgula (padrão 4 = Previdenciária)
    ORELHA_PROCESSOS_SITUACOES    ativos,encerrados (padrão: os dois)
    ORELHA_PROCESSOS_DESDE        primeiro dia de cadastro lido ano a ano (padrão 01/01/2000)
    ORELHA_PROCESSOS_MAX_PAGINAS  teto de pesquisas por execução (padrão 300)
    ORELHA_PROCESSOS_TIMEOUT      segundos por pesquisa (padrão 180)
    ORELHA_PROCESSOS_TAREFAS      true (padrão) = marca os ativos sem tarefa aberta e lista no 3º bloco
"""
import csv
import json
import logging
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from nucleo import simulado, vios
from nucleo.modelos import Item, Secao

log = logging.getLogger("orelha.processos")

TITULO = "Processos da área"
PRECISA_VIOS = True
RELATORIO_DIARIO = False  # gera a própria planilha; não entra no relatorio.html do dia

URL_LISTA = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
URL_FICHA = "?pag=sys/processos/processos-vis.php&processos_id={ci}"
TABELA = "processos-lista"
VAZIA = f'<table id="{TABELA}"><tbody></tbody></table>'
LIMITE = 500            # a lista devolve no máximo 500 por pesquisa
INICIO_ANTIGO = date(1900, 1, 1)
SITUACOES = {"ativos": "ativo", "encerrados": "encerrado"}
# filtro nativo da lista: "Com ou sem tipo de tarefa? = Sem" + "Tipo de tarefa = Abertas | Todas"
SEM_TAREFA_ABERTA = "&pesq[com_ou_sem_tipo_tarefa]=sem&pesq[flag_status_tipo_tarefa]=abertas"
SEM_TAREFA_NENHUMA = "&pesq[com_ou_sem_tipo_tarefa]=sem&pesq[flag_status_tipo_tarefa]=todos"
TAREFA_ABERTA, SEM_ABERTA, NENHUMA = "com tarefa aberta", "sem tarefa aberta", "nenhuma tarefa"

# (chave no JSON, cabeçalho da planilha, coluna do data-id na lista do VIOS)
COLUNAS = [
    ("ci", "CI", "processos_id"),
    ("numero", "Número", "nro_proc_html"),
    ("situacao", "Ativo/Encerrado", None),
    ("tarefas", "Tarefas", None),
    ("situacao_vios", "Situação do processo", "processos_situacao_nome"),
    ("area", "Área", "pr_areas_nome"),
    ("tipo", "Processo", "pr_processos_nome"),
    ("acao", "Ação", "processos_acoes_nome"),
    ("cliente", "Cliente", "clientes_nome"),
    ("parte_ativa", "Parte ativa", "ativahtml"),
    ("parte_passiva", "Parte passiva", "passivahtml"),
    ("terceiros", "Terceiro(s)", "terceirohtml"),
    ("advogado", "Advogado responsável", "advogado_nome"),
    ("auxiliares", "Aux.", "advogados_auxiliares_abr"),
    ("orgao", "Órgão", "orgaos_nome"),
    ("uf", "UF", "orgaos_uf"),
    ("vara", "Vara/Câmara", "vara"),
    ("data_acao", "Data da ação/distribuição", "data_acao"),
    ("data_encerramento", "Data do encerramento", "data_encerrado"),
    ("motivo_encerramento", "Motivo do encerramento", "motivo_encerramento_desc"),
    ("valor_acao", "Valor da ação", "valor_acao"),
    ("ultima_edicao", "Última edição", "data_atualizacao"),
    ("pasta", "Pasta interna", "pasta"),
    ("objeto", "Objeto", "objeto"),
    ("observacoes", "Observações", "obs_proc"),
    ("link", "Link no VIOS", None),
]


def _ids(texto):
    ids = [p.strip() for p in str(texto).split(",") if p.strip()]
    ruins = [p for p in ids if not p.isdigit()]
    if ruins or not ids:
        raise ValueError(f"ORELHA_PROCESSOS_AREAS: use ids numéricos separados por vírgula (veio {texto!r})")
    return ids


def _situacoes(texto):
    lista = [p.strip().lower() for p in str(texto).split(",") if p.strip()]
    ruins = [p for p in lista if p not in SITUACOES]
    if ruins or not lista:
        raise ValueError(f"ORELHA_PROCESSOS_SITUACOES: use {', '.join(SITUACOES)} (veio {texto!r})")
    return lista


def url_pesquisa(areas, filtro, inicio=None, fim=None, limite=LIMITE, extra=""):
    """Lista de processos das `areas` com o filtro "ativos" ou "encerrados"; com período, só os
    cadastrados de `inicio` a `fim`. Só GET."""
    url = URL_LISTA + "&pesq[processos_etapas_id]=TODAS"
    url += "".join(f"&pesq[pr_areas_id][]={a}" for a in areas)
    url += f"&pesq[filtros_multi][]={filtro}" + extra
    if inicio is not None:
        url += f"&pesq[tp_data]=data_cadastro&pesq[idata]={vios.br(inicio)}&pesq[fdata]={vios.br(fim)}"
    return url + f"&pesq[limit]={limite}&Pesq=Pesquisar"


def processos_do_html(html, situacao, base=""):
    """Pura: HTML da lista de processos -> [dict] com as chaves de COLUNAS. Pula linha sem CI."""
    saida = []
    for ln in vios.ler_tabela_html(html, id_tabela=TABELA):
        ci = vios.digitos(ln.get("processos_id"))
        if not ci:
            continue
        p = {}
        for chave, _, data_id in COLUNAS:
            if data_id:
                p[chave] = vios.limpar(ln.get(data_id))
        p["ci"] = ci
        p["cliente"] = re.sub(r"\s*\(\s*\d*\s*\)\s*$", "", p["cliente"])
        for chave in ("data_acao", "data_encerramento", "ultima_edicao"):
            if p[chave].startswith("00/00/0000"):
                p[chave] = ""
        p["situacao"] = situacao
        p["tarefas"] = ""
        p["link"] = urljoin(base, URL_FICHA.format(ci=ci)) if base else ""
        saida.append(p)
    return saida


def juntar(listas):
    """Pura: junta as leituras sem repetir CI (a primeira vence) e ordena por cliente e número."""
    vistos, saida = set(), []
    for lista in listas:
        for p in lista:
            if p["ci"] not in vistos:
                vistos.add(p["ci"])
                saida.append(p)
    return sorted(saida, key=lambda p: (vios.normalizar(p["cliente"]), p["numero"], p["ci"]))


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", vios.normalizar(texto).lower()).strip("-") or "area"


def nome_da_area(processos, areas):
    nomes = sorted({p["area"] for p in processos if p["area"]})
    return " + ".join(nomes) if nomes else "área " + ", ".join(areas)


def blocos(processos):
    """Pura: [(título, [processos])] na ordem da planilha: ativos, encerrados e ativos sem tarefa aberta
    (os sem nenhuma tarefa primeiro). Bloco vazio fica de fora."""
    ativos = [p for p in processos if p["situacao"] == "ativo"]
    encerrados = [p for p in processos if p["situacao"] == "encerrado"]
    sem = sorted((p for p in ativos if p["tarefas"] in (SEM_ABERTA, NENHUMA)), key=lambda p: p["tarefas"] != NENHUMA)
    nenhuma = sum(1 for p in sem if p["tarefas"] == NENHUMA)
    saida = [(f"ATIVOS: {len(ativos)} processos", ativos), (f"ENCERRADOS: {len(encerrados)} processos", encerrados)]
    if any(p["tarefas"] for p in ativos):
        saida.append((f"ATIVOS SEM TAREFA ABERTA: {len(sem)} processos ({nenhuma} sem nenhuma tarefa)", sem))
    return [(titulo, lista) for titulo, lista in saida if lista]


def gravar(processos, pasta, area, areas, quando):
    """Grava processos-<área>.csv (em blocos, ver blocos()) e .json em `pasta`. Devolve (csv, json)."""
    pasta.mkdir(parents=True, exist_ok=True)
    base = pasta / f"processos-{_slug(area)}"
    caminho_csv, caminho_json = base.with_suffix(".csv"), base.with_suffix(".json")
    cabecalho = [cab for _, cab, _ in COLUNAS]
    with open(caminho_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        for i, (titulo, lista) in enumerate(blocos(processos)):
            if i:
                w.writerow([])
                w.writerow([])
            w.writerow([titulo])
            w.writerow(cabecalho)
            for p in lista:
                w.writerow([p.get(chave, "") for chave, _, _ in COLUNAS])
    contagem = contar(processos)
    caminho_json.write_text(json.dumps({
        "gerado_em": quando.isoformat(timespec="seconds"), "area": area, "areas_id": list(areas),
        **contagem, "processos": processos}, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in (caminho_csv, caminho_json):
        c.chmod(0o600)  # tem nomes de clientes
    return caminho_csv, caminho_json


def marcar_tarefas(processos, sem_aberta, sem_nenhuma):
    """Pura: marca cada ativo pelo conjunto de CIs das pesquisas "sem tarefa" (abertas / todas)."""
    for p in processos:
        if p["situacao"] == "ativo":
            p["tarefas"] = NENHUMA if p["ci"] in sem_nenhuma else SEM_ABERTA if p["ci"] in sem_aberta else TAREFA_ABERTA


def contar(processos):
    ativos = sum(1 for p in processos if p["situacao"] == "ativo")
    sem = sum(1 for p in processos if p["tarefas"] in (SEM_ABERTA, NENHUMA))
    nenhuma = sum(1 for p in processos if p["tarefas"] == NENHUMA)
    return {"total": len(processos), "ativos": ativos, "encerrados": len(processos) - ativos,
            "ativos_sem_tarefa_aberta": sem, "ativos_sem_nenhuma_tarefa": nenhuma}


def ler_pesquisa(ctx, url):
    """HTML da pesquisa; VAZIA se a tela de Processos veio sem tabela (0 resultados); "" se não é a
    tela de Processos."""
    html = vios.buscar_get(ctx, url, ctx.cfg.valor("ORELHA_PROCESSOS_TIMEOUT", 180, int))
    if f'id="{TABELA}"' in html:
        return html
    titulo = re.search(r"<title>([^<]*)</title>", html, re.I)
    return VAZIA if titulo and "Processos" in titulo.group(1) else ""


class Leitor:
    """Lê uma situação inteira (ativos ou encerrados), dividindo por período quando vem cheio."""

    def __init__(self, ctx, areas, maximo, avisos):
        self.ctx, self.areas, self.maximo, self.avisos = ctx, areas, maximo, avisos
        self.paginas = 0

    def pesquisar(self, filtro, inicio=None, fim=None, extra=""):
        if self.paginas >= self.maximo:
            return None
        self.paginas += 1
        html = ler_pesquisa(self.ctx, url_pesquisa(self.areas, filtro, inicio, fim, extra=extra))
        if not html:
            trecho = f" ({vios.br(inicio)} a {vios.br(fim)})" if inicio else ""
            raise vios.ViosErro(f"a lista de processos não apareceu{trecho}: conferir processos-lista.php")
        return processos_do_html(html, SITUACOES[filtro], self.ctx.cfg.vios_base)

    def periodo(self, filtro, inicio, fim, extra=""):
        lidos = self.pesquisar(filtro, inicio, fim, extra)
        if lidos is None or len(lidos) < LIMITE:
            return lidos
        if inicio >= fim:
            self.avisos.append(f"{filtro}: o dia {vios.br(inicio)} tem {LIMITE} processos ou mais; pode faltar algum")
            return lidos
        meio = inicio + timedelta(days=(fim - inicio).days // 2)
        saida = []
        for a, b in ((inicio, meio), (meio + timedelta(days=1), fim)):
            parte = self.periodo(filtro, a, b, extra)
            if parte is None:
                return None
            saida += parte
        return saida

    def situacao(self, filtro, desde, hoje, extra=""):
        lidos = self.pesquisar(filtro, extra=extra)
        if lidos is None or len(lidos) < LIMITE:
            return lidos or []
        log.info("Processos (%s): mais de %d, lendo por período de cadastro", filtro, LIMITE)
        janelas = [(INICIO_ANTIGO, desde - timedelta(days=1))] if desde > INICIO_ANTIGO else []
        janelas += [(max(desde, date(ano, 1, 1)), min(hoje, date(ano, 12, 31))) for ano in range(desde.year, hoje.year + 1)]
        saida = []
        for a, b in janelas:
            parte = self.periodo(filtro, a, b, extra)
            if parte is None:
                self.avisos.append(f"parei no limite de {self.maximo} pesquisas (ORELHA_PROCESSOS_MAX_PAGINAS): "
                                   "a planilha pode estar incompleta")
                break
            saida += parte
        else:
            # o que não tem data de cadastro não cai em nenhum período: confere pela contagem sem filtro de data
            if len(juntar([saida])) < LIMITE:
                self.avisos.append(f"{filtro}: a pesquisa sem período veio cheia, mas os períodos somaram menos "
                                   f"de {LIMITE}; pode haver processo sem data de cadastro")
        return saida


def executar(ctx):
    cfg = ctx.cfg
    areas = cfg.valor("ORELHA_PROCESSOS_AREAS", "4", _ids)
    filtros = cfg.valor("ORELHA_PROCESSOS_SITUACOES", "ativos,encerrados", _situacoes)
    desde = cfg.valor("ORELHA_PROCESSOS_DESDE", "01/01/2000", "data")
    maximo = cfg.valor("ORELHA_PROCESSOS_MAX_PAGINAS", 300, int)
    tarefas = cfg.valor("ORELHA_PROCESSOS_TAREFAS", True, bool) and "ativos" in filtros
    ctx.emitir("fase", fase="lendo_processos")
    avisos, leituras = [], []
    sem_aberta, sem_nenhuma = set(), set()
    if ctx.simulado:
        for filtro in filtros:
            leituras.append(processos_do_html(simulado.ler(ctx, f"{filtro}.html"), SITUACOES[filtro], cfg.vios_base))
        if tarefas:
            sem_aberta = {p["ci"] for p in processos_do_html(simulado.ler(ctx, "ativos-sem-tarefa-aberta.html"), "")}
            sem_nenhuma = {p["ci"] for p in processos_do_html(simulado.ler(ctx, "ativos-sem-nenhuma-tarefa.html"), "")}
    else:
        vios.abrir(ctx, URL_LISTA)  # o fetch roda de dentro de uma página do VIOS (mesma sessão)
        leitor = Leitor(ctx, areas, maximo, avisos)
        for filtro in filtros:
            leituras.append(leitor.situacao(filtro, desde, ctx.hoje))
        if tarefas:
            sem_aberta = {p["ci"] for p in leitor.situacao("ativos", desde, ctx.hoje, SEM_TAREFA_ABERTA)}
            sem_nenhuma = {p["ci"] for p in leitor.situacao("ativos", desde, ctx.hoje, SEM_TAREFA_NENHUMA)}
        log.info("Processos: %d pesquisa(s) na lista de processos", leitor.paginas)
    processos = juntar(leituras)
    if tarefas:
        marcar_tarefas(processos, sem_aberta, sem_nenhuma)
    area = nome_da_area(processos, areas)
    numeros = contar(processos)
    caminho_csv, _ = gravar(processos, ctx.saida, area, areas, datetime.now())
    log.info("Processos: planilha em %s", caminho_csv)
    for aviso in avisos:
        log.warning("Processos: %s", aviso)
    partes = [f"{numeros['ativos']} ativos" if "ativos" in filtros else "",
              f"{numeros['encerrados']} encerrados" if "encerrados" in filtros else ""]
    if tarefas:
        partes.append(f"{numeros['ativos_sem_tarefa_aberta']} ativos sem tarefa aberta")
    resumo = (f"{numeros['total']} processos da área {area} ({', '.join(p for p in partes if p)}). "
              f"Planilha: {caminho_csv.name}")
    itens = [Item(titulo=t, detalhe=f"{n} processo(s)", grupo="Por ação")
             for t, n in sorted(_por_acao(processos).items(), key=lambda x: (-x[1], x[0]))]
    return Secao(chave="processos", titulo=TITULO, resumo=resumo, itens=itens, numeros=numeros, avisos=avisos,
                 recolher=True)


def _por_acao(processos):
    conta = {}
    for p in processos:
        chave = p["acao"] or "Sem ação informada"
        conta[chave] = conta.get(chave, 0) + 1
    return conta
