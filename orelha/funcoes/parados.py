"""Processos parados — processos ativos sem nenhuma tarefa aberta (função 4 do Orelha).

O que faz: percorre a lista de processos ATIVOS do VIOS, abre a ficha de cada um e lê a tabela de
Tarefas. "Parado" = nenhuma tarefa sem "Concluída em" que não esteja cancelada. Só lê: nunca clica
em Editar/Apagar/Processar da lista nem em nada da ficha.

Telas (mapa em `git show developer:doc/vios-mapa-processos.md`, código de referência em
`developer:relatorio_processos.py`, `bot/processos_grupo.py` e `bot/processo_ficha.py`, copiados
aqui na ideia, sem importar nada de bot/):
  - lista `?pag=sys/processos/processos-lista.php&menu_lateral=true`: o filtro é um formulário
    (pesq[limit], pesq[clientes_grupos_id], pesq[filtros_multi][] com "ativos"); o Orelha marca o
    form com data-orelha-pesquisa="1" (a exceção documentada do bloqueio de envios) e envia pelo
    botão #Pesq. Com pesq[limit]=9999999 a lista vem inteira (sem paginação); se um dia houver
    paginação, ORELHA_PARADOS_PROXIMA_PAGINA diz qual é o botão "próxima".
    Linhas `tr[id^='processos-lista_linha_']` com `data-processos_id` (= CI) e células
    `td[data-id='processos-lista_linha_<n>_<coluna>']`.
  - ficha `?pag=sys/processos/processos-vis.php&processos_id=<CI>` (Vue): tabela DataTables cujo
    thead tem "Tipo de tarefa" (o thead aparece duplicado: cabeçalho fixo + corpo). Colunas por
    POSIÇÃO: 1 = CI da tarefa, 2 = tipo (com o selo "CANCELADA" quando há), 5 = datas
    ("Para conclusão ... Limite ... Concluída em: ...").

Lenta (uma ficha por processo): no máximo ORELHA_PARADOS_MAX (padrão 300) fichas por execução. Onde
parou fica em historico/parados-progresso.json; a próxima execução continua dali (ordem de CI) e,
quando chega ao fim da lista, o ciclo fecha e o seguinte recomeça do começo. Ficha que não abriu é
tentada de novo uma vez na execução seguinte. O que ficou de fora vai para o log e para os avisos.

Níveis: "grave" = parado e sem nenhuma tarefa concluída (ou só canceladas) ou com a última
conclusão há mais de ORELHA_PARADOS_DIAS_GRAVE dias (padrão 90); "atencao" = os outros parados.
Ficha que não deu para ler, ou com a tabela de tarefas incompleta (paginada), NÃO vira "parado":
vai para os avisos (melhor não acusar sem certeza).

Separação: a leitura (Selenium) fica nas classes LeitorVios/LeitorSimulado; a interpretação
(ler_lista_html, ler_tarefas_html, avaliar, planejar, atualizar_progresso, montar_secao) é pura e
testada com orelha/fixtures/parados/ (dados 100% fictícios).
"""
import logging
import re
import time
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from nucleo import simulado, vios
from nucleo.modelos import Item, Secao

log = logging.getLogger("orelha")

TITULO = "Processos parados"
PRECISA_VIOS = True

URL_LISTA = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
URL_FICHA = "?pag=sys/processos/processos-vis.php&processos_id={ci}"
PREFIXO_LINHA = "processos-lista_linha_"
LIMITE_LISTA = "9999999"   # opção "sem limite" de pesq[limit] (não há teto de 500)
GRUPO_TODOS = "0"          # valor do TODOS no filtro Grupo Cliente
PROGRESSO = "parados-progresso.json"
VERSAO_PROGRESSO = 1
COLUNAS_TAREFA = {"ci": 1, "tipo": 2, "datas": 5}
AGRUPAMENTOS = ("area", "cliente", "advogado", "nenhum")
MODOS_XHR = ("auto", "sim", "nao")
SALVAR_A_CADA = 25         # grava o progresso a cada N fichas (se o processo morrer, perde pouco)
MAX_PAGINAS = 500
MAX_CIS_NO_AVISO = 20
RANQUE_NIVEL = {"grave": 0, "atencao": 1, "info": 2}


class SessaoCaiu(vios.ViosErro):
    """A tela de login apareceu no meio das fichas. Não dá para entrar de novo (o bloqueio de
    envios barra o formulário de login): para a leitura e guarda o progresso."""


# ---------------------------------------------------------------- configuração
def _agrupamento(texto):
    t = vios.normalizar(texto).lower()
    if t not in AGRUPAMENTOS:
        raise ValueError(f"use {', '.join(AGRUPAMENTOS)}")
    return t


def _modo_xhr(texto):
    t = vios.normalizar(texto).lower()
    if t not in MODOS_XHR:
        raise ValueError(f"use {', '.join(MODOS_XHR)}")
    return t


def ler_colunas(texto):
    """"ci=1,tipo=2,datas=5" -> {"ci": 1, "tipo": 2, "datas": 5} (posições a partir de 0).
    Nome que faltar fica com o padrão."""
    saida = dict(COLUNAS_TAREFA)
    for parte in str(texto).split(","):
        if not parte.strip():
            continue
        nome, sep, pos = parte.partition("=")
        nome = nome.strip().lower()
        if not sep or nome not in COLUNAS_TAREFA or not pos.strip().isdigit():
            raise ValueError("use ci=1,tipo=2,datas=5")
        saida[nome] = int(pos.strip())
    return saida


@dataclass
class Opcoes:
    maximo: int = 300                 # fichas por execução (0 = sem limite)
    dias_grave: int = 90
    agrupar: str = "area"
    minutos: int = 0                  # tempo máximo lendo fichas (0 = sem limite)
    grupo_cliente: str = GRUPO_TODOS
    limite_lista: str = LIMITE_LISTA
    url_lista: str = URL_LISTA
    url_ficha: str = URL_FICHA
    prefixo_linha: str = PREFIXO_LINHA
    campo_limite: tuple = None
    botao_pesquisa: str = "#Pesq"
    proxima_pagina: tuple = None
    colunas: dict = field(default_factory=lambda: dict(COLUNAS_TAREFA))
    timeout_lista: int = 180
    tempo_ficha: int = 20
    liberar_xhr: str = "nao"               # "auto" e "sim" só depois de conferir na tela real


def opcoes(cfg):
    """Lê as variáveis ORELHA_PARADOS_* do orelha/.env (ConfigErro com o nome, se inválida)."""
    v = cfg.valor
    url_ficha = v("ORELHA_PARADOS_URL_FICHA", URL_FICHA)
    if "{ci}" not in url_ficha:
        from nucleo.config import ConfigErro
        raise ConfigErro("ORELHA_PARADOS_URL_FICHA: o endereço precisa ter {ci}")
    op = Opcoes(
        maximo=max(0, v("ORELHA_PARADOS_MAX", 300, int)),
        dias_grave=max(0, v("ORELHA_PARADOS_DIAS_GRAVE", 90, int)),
        agrupar=v("ORELHA_PARADOS_AGRUPAR", "area", _agrupamento),
        minutos=max(0, v("ORELHA_PARADOS_MINUTOS", 0, int)),
        grupo_cliente=v("ORELHA_PARADOS_GRUPO_CLIENTE", GRUPO_TODOS),
        limite_lista=v("ORELHA_PARADOS_LIMITE_LISTA", LIMITE_LISTA),
        url_lista=v("ORELHA_PARADOS_URL_LISTA", URL_LISTA),
        url_ficha=url_ficha,
        prefixo_linha=v("ORELHA_PARADOS_PREFIXO_LINHA", PREFIXO_LINHA),
        campo_limite=v("ORELHA_PARADOS_CAMPO_LIMITE", "css:[name='pesq[limit]']", "seletor"),
        botao_pesquisa=v("ORELHA_PARADOS_BOTAO_PESQUISA", "#Pesq"),
        proxima_pagina=v("ORELHA_PARADOS_PROXIMA_PAGINA", "", "seletor"),
        colunas=v("ORELHA_PARADOS_COLUNAS_TAREFA", "ci=1,tipo=2,datas=5", ler_colunas),
        timeout_lista=max(1, v("ORELHA_PARADOS_TIMEOUT_LISTA", 180, int)),
        tempo_ficha=max(1, v("ORELHA_PARADOS_TEMPO_FICHA", getattr(cfg, "timeout", 20) or 20, int)),
        liberar_xhr=v("ORELHA_PARADOS_LIBERAR_XHR", "nao", _modo_xhr),
    )
    return op


# ---------------------------------------------------------------- modelos internos
@dataclass
class Processo:
    ci: int
    numero: str = ""
    cliente: str = ""
    area: str = ""
    acao: str = ""
    advogado: str = ""
    link: str = ""


@dataclass
class Tarefa:
    ci: str = ""
    tipo: str = ""
    cancelada: bool = False
    concluida: bool = False
    concluida_em: Optional[date] = None
    para_conclusao: Optional[date] = None
    limite: Optional[date] = None

    @property
    def aberta(self):
        return not self.cancelada and not self.concluida


@dataclass
class LeituraFicha:
    achou_tabela: bool                # a tabela de Tarefas apareceu (mesmo vazia)
    tarefas: list = field(default_factory=list)
    total_informado: Optional[int] = None   # "Mostrando 1 a 10 de N registros"
    erro: str = ""


@dataclass
class Avaliacao:
    situacao: str                     # "parado" | "com_tarefa" | "nao_lido" | "incompleto"
    nivel: str = "info"
    ultima: Optional[Tarefa] = None   # última tarefa concluída (não cancelada), se houver
    motivo: str = ""
    tarefas: int = 0
    canceladas: int = 0


# ---------------------------------------------------------------- interpretação (pura)
def _tabelas(html):
    """Todas as tabelas do HTML (inclusive as de dentro de outras), na ordem do documento."""
    for i in range((html or "").lower().count("<table")):
        yield vios.ler_tabela_html(html, indice=i)


def _numero(texto):
    """Número do processo da célula nro_proc_html: o CNJ, se houver; senão o que vem depois de
    "CNJ:"/"Outros:" (as etiquetas .vj-badge ficam antes)."""
    achados = vios.cnjs(texto)
    if achados:
        return achados[0]
    t = vios.limpar(texto)
    m = re.search(r"(?:CNJ|Outros)\s*:\s*(.+)$", t, re.I)
    return vios.limpar(m.group(1)) if m else t


def _celula(linha, coluna_data_id, *nomes):
    if linha.por_data_id.get(coluna_data_id):
        return vios.limpar(linha.por_data_id[coluna_data_id])
    for nome in nomes:
        valor = linha.get(nome, "")
        if valor:
            return vios.limpar(valor)
    return ""


def url_da_ficha(base, ci, modelo=URL_FICHA):
    return urljoin(base or "", modelo.format(ci=ci).lstrip("/"))


def ler_lista_html(html, base="", prefixo=PREFIXO_LINHA, modelo_ficha=URL_FICHA):
    """Lista de processos (HTML da tabela ou da página) -> ([Processo], [avisos]).

    Lê a primeira tabela que tem linhas com id começando por `prefixo`. Linha sem CI numérico
    fica de fora (com aviso); CI repetido entra uma vez só."""
    processos, avisos, vistos = [], [], set()
    for tabela in _tabelas(html):
        linhas = [l for l in tabela.linhas if (l.id or "").startswith(prefixo)]
        if not linhas:
            continue
        sem_ci = 0
        for linha in linhas:
            ci_txt = vios.digitos(linha.atributos.get("data-processos_id", "")) or \
                vios.digitos(_celula(linha, "processos_id", "CI"))
            if not ci_txt:
                sem_ci += 1
                continue
            ci = int(ci_txt)
            if ci in vistos:
                continue
            vistos.add(ci)
            link = next((l["href"] for l in linha.links if "processos-vis.php" in l["href"]), "")
            processos.append(Processo(
                ci=ci,
                numero=_numero(_celula(linha, "nro_proc_html", "Número", "Processo")),
                cliente=_celula(linha, "clientes_nome", "Cliente"),
                area=_celula(linha, "pr_areas_nome", "Área"),
                acao=_celula(linha, "processos_acoes_nome", "Ação"),
                advogado=_celula(linha, "advogado_nome", "Advogado"),
                link=urljoin(base or "", link) if link else url_da_ficha(base, ci, modelo_ficha),
            ))
        if sem_ci:
            avisos.append(f"{sem_ci} linha(s) da lista sem CI ficaram de fora")
        break
    return processos, avisos


_SELOS = re.compile(r"^\s*(CANCELADA|CONCLU[IÍ]DA|ATRASADA|PENDENTE|EM ANDAMENTO)\s*(/\s*)?", re.I)
_TOTAL = (re.compile(r"\bDE\s+([\d.]+)\s+REGISTROS?\b"), re.compile(r"\bOF\s+([\d.,]+)\s+ENTRIES\b"))
_ROTULOS_DATA = ("PARA CONCLUSAO", "LIMITE", "CONCLUIDA EM")


def total_informado(texto):
    """N de "Mostrando 1 a 10 de N registros" (DataTables), ou None."""
    t = vios.normalizar(re.sub(r"<[^>]+>", " ", texto or ""))
    for regex in _TOTAL:
        m = regex.search(t)
        if m:
            return int(vios.digitos(m.group(1)) or 0)
    return None


def _data_apos(texto_norm, rotulo):
    m = re.search(rotulo + r"\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})", texto_norm)
    return vios.data_br(m.group(1)) if m else None


def _tarefa(linha, colunas):
    cel = linha.celulas

    def c(nome):
        i = colunas[nome]
        return cel[i] if i < len(cel) else ""

    tipo_txt = c("tipo")
    titulos = [vios.normalizar(t) for t in linha.titulos]
    datas = vios.normalizar(c("datas"))
    if not any(r in datas for r in _ROTULOS_DATA):
        # coluna fora do lugar: procura os rótulos na linha toda
        datas = vios.normalizar(" ".join(cel))
    concluida_em = _data_apos(datas, "CONCLUIDA EM")
    # o selo (.vj-badge) vem antes do tipo: "CANCELADA ANALISAR PROCESSO ..."; só o começo conta
    # (melhor deixar de apontar um parado que acusar um processo com tarefa aberta)
    selo = vios.normalizar(tipo_txt)
    cancelada = selo.startswith("CANCELAD") or any(t.startswith(("CANCELAD", "TAREFA CANCELAD")) for t in titulos)
    concluida = concluida_em is not None or selo.startswith("CONCLUIDA") or \
        any(t.startswith("CONCLUIDA") for t in titulos)
    tipo = tipo_txt
    while _SELOS.match(tipo):
        tipo = _SELOS.sub("", tipo, count=1)
    return Tarefa(ci=vios.digitos(c("ci")), tipo=vios.limpar(tipo), cancelada=cancelada, concluida=concluida,
                  concluida_em=concluida_em, para_conclusao=_data_apos(datas, "PARA CONCLUSAO"),
                  limite=_data_apos(datas, "LIMITE"))


def _montar_leitura(linhas, colunas, total):
    tarefas = []
    for linha in linhas:
        texto = vios.normalizar(" ".join(linha.celulas))
        if len([x for x in linha.celulas if x]) <= 1:
            if "CARREGANDO" in texto or "PROCESSANDO" in texto:
                return LeituraFicha(achou_tabela=False, erro="a tabela de Tarefas ainda estava carregando")
            continue  # "Nenhum registro encontrado"
        t = _tarefa(linha, colunas)
        if t.ci or t.tipo:
            tarefas.append(t)
    return LeituraFicha(achou_tabela=True, tarefas=tarefas, total_informado=total)


def ler_tarefas_html(html, colunas=None, info=None):
    """Tabela de Tarefas da ficha (HTML da página, do .dataTables_wrapper ou só da tabela) ->
    LeituraFicha.

    O thead do DataTables aparece duplicado: uma tabela só com o cabeçalho ("Tipo de tarefa") e,
    logo depois, a tabela do corpo (com o cabeçalho vazio ou repetido). Pega a primeira tabela com
    linhas que tenha o cabeçalho de tarefas ou que venha logo depois dele sem cabeçalho próprio.
    `info`: texto "Mostrando 1 a 10 de N registros" (se None, procura no HTML depois do cabeçalho)."""
    colunas = colunas or COLUNAS_TAREFA
    html = html or ""
    if info is None:
        # o "Mostrando ... de N registros" do bloco de tarefas: do cabeçalho até o próximo bloco
        m = re.search(r"tipo\s+de\s+tarefa", html, re.I)
        info = html[m.end():] if m else ""
        prox = re.search(r"dataTables_wrapper", info)
        info = info[:prox.start()] if prox else info
    total = total_informado(info)
    cabecalho_visto = False
    for tabela in _tabelas(html):
        cab = vios.normalizar(" ".join(tabela.colunas))
        if "TIPO DE TAREFA" in cab:
            cabecalho_visto = True
            if tabela.linhas:
                return _montar_leitura(tabela.linhas, colunas, total)
            continue
        if cabecalho_visto and not cab and tabela.linhas:
            return _montar_leitura(tabela.linhas, colunas, total)
    return LeituraFicha(achou_tabela=False)


def avaliar(leitura, hoje, dias_grave=90):
    """LeituraFicha -> Avaliacao. Parado = tabela lida (e completa) sem nenhuma tarefa aberta."""
    if leitura.erro or not leitura.achou_tabela:
        return Avaliacao("nao_lido", motivo=leitura.erro or "a tabela de Tarefas não apareceu na ficha")
    tarefas = leitura.tarefas
    canceladas = sum(1 for t in tarefas if t.cancelada)
    if any(t.aberta for t in tarefas):
        return Avaliacao("com_tarefa", tarefas=len(tarefas), canceladas=canceladas)
    if leitura.total_informado is not None and leitura.total_informado > len(tarefas):
        return Avaliacao("incompleto", tarefas=len(tarefas), canceladas=canceladas,
                         motivo=f"a ficha mostrou {len(tarefas)} de {leitura.total_informado} tarefas")
    concluidas = [t for t in tarefas if t.concluida and not t.cancelada]
    com_data = [t for t in concluidas if t.concluida_em]
    ultima = max(com_data, key=lambda t: t.concluida_em) if com_data else (concluidas[0] if concluidas else None)
    if not concluidas:
        nivel = "grave"           # nenhuma tarefa, ou só canceladas
    elif ultima.concluida_em and (hoje - ultima.concluida_em).days > dias_grave:
        nivel = "grave"
    else:
        nivel = "atencao"
    return Avaliacao("parado", nivel=nivel, ultima=ultima, tarefas=len(tarefas), canceladas=canceladas)


def _qtd(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _dias(n):
    return "hoje" if n == 0 else ("há 1 dia" if n == 1 else f"há {n} dias")


def descrever(av, hoje):
    """Frase do detalhe do item parado."""
    if av.ultima and av.ultima.concluida_em:
        tipo = f" ({av.ultima.tipo})" if av.ultima.tipo else ""
        return (f"sem tarefa aberta; a última foi concluída em {vios.br(av.ultima.concluida_em)}{tipo}, "
                f"{_dias((hoje - av.ultima.concluida_em).days)}")
    if av.ultima:
        return "sem tarefa aberta (a data da última conclusão não aparece na ficha)"
    if av.canceladas:
        return f"sem tarefa aberta: só {_qtd(av.canceladas, 'tarefa cancelada', 'tarefas canceladas')}"
    return "nenhuma tarefa cadastrada na ficha"


def _grupo(proc, agrupar):
    if agrupar == "cliente":
        return proc.cliente or "Sem cliente"
    if agrupar == "advogado":
        return proc.advogado or "Sem advogado"
    if agrupar == "nenhum":
        return ""
    return proc.area or "Sem área"


def item_parado(proc, av, hoje, agrupar="area"):
    partes = [f"CI {proc.ci}"]
    partes += [p for p in (proc.cliente, proc.acao) if p]
    partes.append(descrever(av, hoje))
    if proc.advogado and agrupar != "advogado":
        partes.append(f"advogado: {proc.advogado}")
    return Item(titulo=proc.numero or f"Processo CI {proc.ci}", detalhe=" · ".join(partes), nivel=av.nivel,
                link=proc.link, grupo=_grupo(proc, agrupar))


def ordenar_itens(itens_e_datas):
    """[(Item, data da última conclusão ou None)] -> [Item] por grupo, gravidade e mais antigo primeiro
    (o relatório agrupa na ordem em que os grupos aparecem)."""
    def chave(par):
        item, ultima = par
        return (vios.normalizar(item.grupo), RANQUE_NIVEL[item.nivel], ultima or date.min, item.titulo)
    return [item for item, _ in sorted(itens_e_datas, key=chave)]


# ---------------------------------------------------------------- retomada (pura)
def novo_ciclo(hoje):
    return {"versao": VERSAO_PROGRESSO, "ciclo_inicio": hoje.isoformat(), "ultimo_ci": 0, "pendentes": [],
            "lidos_no_ciclo": 0, "parados_no_ciclo": [], "ciclo_completo": False, "atualizado": ""}


def _progresso_valido(dados):
    if not isinstance(dados, dict) or dados.get("versao") != VERSAO_PROGRESSO:
        return None
    try:
        return {**dados,
                "ultimo_ci": int(dados.get("ultimo_ci") or 0),
                "pendentes": sorted({int(c) for c in dados.get("pendentes") or []}),
                "lidos_no_ciclo": int(dados.get("lidos_no_ciclo") or 0),
                "parados_no_ciclo": sorted({int(c) for c in dados.get("parados_no_ciclo") or []}),
                "ciclo_completo": bool(dados.get("ciclo_completo"))}
    except (TypeError, ValueError):
        return None


def planejar(cis, progresso, maximo, hoje):
    """Quais fichas ler agora. Devolve (lote, fora, progresso de partida).

    Ordem: primeiro as fichas que falharam na execução anterior (uma nova tentativa), depois os
    CIs maiores que `ultimo_ci`, crescentes. Sem progresso, ciclo completo ou nada a ler: ciclo novo."""
    ordenados = sorted(set(cis))
    prog = _progresso_valido(progresso)
    if prog is None and progresso is not None:
        log.warning("Parados: %s inválido ou de outra versão; começando um ciclo novo", PROGRESSO)
    for tentativa in (1, 2):
        if prog is None or prog["ciclo_completo"] or tentativa == 2:
            prog = novo_ciclo(hoje)
        ativos = set(ordenados)
        pendentes = [c for c in prog["pendentes"] if c in ativos]
        fila = pendentes + [c for c in ordenados if c > prog["ultimo_ci"] and c not in pendentes]
        if fila or not ordenados:
            break
    prog["pendentes"] = [c for c in prog["pendentes"] if c in set(ordenados)]
    if maximo and maximo > 0:
        return fila[:maximo], fila[maximo:], prog
    return fila, [], prog


def atualizar_progresso(prog, lote, feitos, falhas, parados, nao_parados, fora, agora):
    """Progresso depois da leitura. Devolve (progresso novo, CIs que falharam pela 2ª vez).

    feitos: CIs cujas fichas foram tentadas (na ordem); falhas: as que não deu para ler; parados /
    nao_parados: resultado das lidas; fora: os que nem entraram no lote."""
    antigos = set(prog["pendentes"])
    feitos_set, falhas_set = set(feitos), set(falhas)
    novo = dict(prog)
    da_fila = [c for c in feitos if c not in antigos]
    if da_fila:
        novo["ultimo_ci"] = max(prog["ultimo_ci"], max(da_fila))
    de_novo = sorted(c for c in falhas_set if c in antigos)
    novo["pendentes"] = sorted({c for c in antigos if c not in feitos_set} |
                               {c for c in falhas_set if c not in antigos})
    novo["lidos_no_ciclo"] = prog["lidos_no_ciclo"] + len(feitos_set - falhas_set)
    novo["parados_no_ciclo"] = sorted((set(prog["parados_no_ciclo"]) - set(nao_parados)) | set(parados))
    restantes = [c for c in lote if c not in feitos_set] + list(fora)
    novo["ciclo_completo"] = not restantes and not novo["pendentes"]
    novo["atualizado"] = agora.isoformat(timespec="seconds")
    return novo, de_novo


def _faixa(cis):
    cis = sorted(cis)
    if not cis:
        return ""
    lista = ", ".join(str(c) for c in cis[:MAX_CIS_NO_AVISO])
    return lista + (f" e mais {len(cis) - MAX_CIS_NO_AVISO}" if len(cis) > MAX_CIS_NO_AVISO else "")


# ---------------------------------------------------------------- leitura: simulado
class LeitorSimulado:
    """Lê orelha/fixtures/parados/lista.html e ficha-<CI>.html (dados fictícios)."""

    liberado = False

    def __init__(self, ctx, op):
        self.ctx, self.op = ctx, op

    def lista(self):
        html = simulado.ler(self.ctx, "lista.html")
        return ler_lista_html(html, self.ctx.cfg.vios_base, self.op.prefixo_linha, self.op.url_ficha)

    def ficha(self, proc):
        try:
            html = simulado.ler(self.ctx, f"ficha-{proc.ci}.html")
        except FileNotFoundError:
            return LeituraFicha(False, erro="ficha fictícia não encontrada")
        leitura = ler_tarefas_html(html, self.op.colunas)
        if not leitura.achou_tabela and not leitura.erro:
            ficha_ok = "vj-bloco-info-text-area" in html
            leitura.erro = "a tabela de Tarefas não apareceu na ficha" if ficha_ok else "a ficha não carregou"
        return leitura

    def fechar(self):
        pass


# ---------------------------------------------------------------- leitura: VIOS (Selenium, fina)
JS_PESQUISA = """
const [campo, limite, grupo, botaoCss] = arguments;
const form = campo.form;
if (!form) return "o campo pesq[limit] não está num formulário";
campo.value = limite;
// sem a opção a tela mostra só 30 processos: melhor parar que conferir uma lista cortada
if (campo.value !== limite) return "a opção " + limite + " não existe em pesq[limit] (a lista viria cortada)";
const sel = form.elements["pesq[clientes_grupos_id]"];
if (sel) {
    sel.value = grupo;
    if (sel.value !== grupo) return "Grupo Cliente com valor " + grupo + " não existe no filtro";
} else if (grupo !== "0") {
    return "filtro Grupo Cliente não encontrado no formulário";
}
const multi = form.elements["pesq[filtros_multi][]"];
const opcoes = (multi && multi.options) ? Array.from(multi.options) : [];
const ativos = opcoes.find(o => o.value === "ativos");
if (!ativos) return "opção 'ativos' não encontrada em pesq[filtros_multi][] (a lista poderia trazer encerrados)";
ativos.selected = true;
// as opções combinam com E (ver doc/vios-mapa-processos.md): tira as que misturam encerrados
for (const o of opcoes) if (["encerrados", "ativos_e_encerrados", "todos"].includes(o.value)) o.selected = false;
try { if (window.jQuery && window.jQuery(multi).selectpicker) window.jQuery(multi).selectpicker("refresh"); } catch (e) {}
form.setAttribute("data-orelha-pesquisa", "1");
const botao = (botaoCss && form.querySelector(botaoCss)) || form.querySelector("[type=submit]");
try { form.requestSubmit(botao || undefined); } catch (e) { form.requestSubmit(); }
return "";
"""

JS_TABELA_LISTA = """
const tr = document.querySelector("tr[id^='" + arguments[0] + "']");
return tr ? tr.closest("table").outerHTML : "";
"""

# "tarefas" = tabela de Tarefas com dado (linha ou "Nenhum registro"); "ficha" = ficha carregou,
# tarefas ainda não; "" = nada
JS_ESTADO_FICHA = """
for (const w of document.querySelectorAll('.dataTables_wrapper')) {
    const cab = Array.from(w.querySelectorAll('thead')).map(t => t.textContent).join(' ');
    if (!/tipo de tarefa/i.test(cab)) continue;
    for (const tr of w.querySelectorAll('tbody tr')) {
        if (tr.cells.length > 1 || /nenhum registro/i.test(tr.textContent)) return 'tarefas';
    }
}
return document.querySelector('.vj-bloco-info-text-area') ? 'ficha' : '';
"""

# HTML da tabela de Tarefas. Se o DataTables paginou na tela, pega TODAS as linhas pela API dele
# (só leitura: rows().nodes() não muda a página nem chama o servidor).
JS_TAREFAS = """
let w = null;
for (const x of document.querySelectorAll('.dataTables_wrapper')) {
    const cab = Array.from(x.querySelectorAll('thead')).map(t => t.textContent).join(' ');
    if (/tipo de tarefa/i.test(cab)) { w = x; break; }
}
const ficha = !!document.querySelector('.vj-bloco-info-text-area');
if (!w) return {ficha: ficha, html: '', info: null};
let html = w.outerHTML;
const infoEl = w.querySelector('.dataTables_info');
let info = infoEl ? infoEl.textContent : '';
try {
    const tabelas = Array.from(w.querySelectorAll('table')).filter(t => !t.parentElement.closest('table'));
    const corpo = tabelas.find(t => t.tBodies.length && t.tBodies[0].rows.length);
    const $ = window.jQuery;
    if (corpo && $ && $.fn.dataTable && $.fn.dataTable.isDataTable(corpo)) {
        const nos = $(corpo).DataTable().rows().nodes().toArray();
        if (nos.length > corpo.tBodies[0].rows.length) {
            const cab = tabelas.find(t => t.tHead && /tipo de tarefa/i.test(t.tHead.textContent));
            html = '<table>' + (cab ? cab.tHead.outerHTML : '') + '<tbody>' +
                   nos.map(n => n.outerHTML).join('') + '</tbody></table>';
            info = '';  // já são todas as linhas
        }
    }
} catch (e) { /* fica o que está na tela; a conferência do total avisa se faltar */ }
return {ficha: ficha, html: html, info: info};
"""


class LeitorVios:
    """Lista e fichas no VIOS de verdade. Só abre páginas, envia a pesquisa da lista (form
    marcado pelo Orelha) e lê o DOM; nunca clica em ação da linha nem da ficha."""

    def __init__(self, ctx, op):
        self.ctx, self.op = ctx, op
        self.pilha = ExitStack()
        self.liberado = False
        if op.liberar_xhr == "sim":
            self._liberar()

    # -- bloqueio
    def _liberar(self):
        """Libera XHR/fetch POST (formulário e sendBeacon continuam barrados), como o calendário.
        Só se a ficha (Vue) precisar buscar os dados por POST: ORELHA_PARADOS_LIBERAR_XHR."""
        from nucleo.navegador import pesquisa_liberada
        self.pilha.enter_context(pesquisa_liberada(self.ctx.driver))
        self.liberado = True

    def _xhr_barrado(self):
        from nucleo.navegador import tentativas_barradas
        return any(t.startswith(("XHR", "fetch")) for t in tentativas_barradas(self.ctx.driver))

    def _pode_liberar(self):
        if self.op.liberar_xhr != "auto" or self.liberado:
            return False
        return self._xhr_barrado()

    def _conferir_bloqueio(self):
        from nucleo.navegador import envios_bloqueados
        if not envios_bloqueados(self.ctx.driver):
            raise vios.BloqueioInativo(f"bloqueio de envios inativo em {self.ctx.driver.current_url}: "
                                       "execução interrompida")

    def fechar(self):
        self.pilha.close()

    def _na_tela_de_login(self, driver):
        try:
            if "entrar.php" in (driver.current_url or "").lower():
                return True
            campo = self.ctx.cfg.campo_senha
            return bool(campo) and bool(driver.find_elements(*campo))
        except Exception:
            return False

    # -- lista
    def _pesquisar(self):
        from selenium.webdriver.support import expected_conditions as EC
        ctx, op = self.ctx, self.op
        campo = vios.esperar(ctx, op.campo_limite, visivel=False)
        # mesmas proteções de vios.enviar_pesquisa: action, texto do botão e tela de pesquisa
        if not vios.conferir_formulario_da_tela(ctx, campo, op.botao_pesquisa):
            raise vios.ViosErro("o campo pesq[limit] não está num formulário")
        erro =ctx.driver.execute_script(JS_PESQUISA, campo, op.limite_lista, op.grupo_cliente, op.botao_pesquisa)
        if erro:
            raise vios.ViosErro(erro)
        vios.esperar_ate(ctx, EC.staleness_of(campo), op.timeout_lista,
                         "a pesquisa da lista de processos não recarregou a página")
        vios.esperar_ajax(ctx, op.timeout_lista)
        self._conferir_bloqueio()

    def _ler_pagina(self):
        html = self.ctx.driver.execute_script(JS_TABELA_LISTA, self.op.prefixo_linha) or ""
        return ler_lista_html(html, self.ctx.cfg.vios_base, self.op.prefixo_linha, self.op.url_ficha)

    def lista(self):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        ctx, op = self.ctx, self.op
        log.info("Parados: abrindo a lista de processos ativos (pode demorar: vem a lista inteira)")
        vios.abrir(ctx, op.url_lista, timeout=op.timeout_lista)
        self._pesquisar()
        linhas = (By.CSS_SELECTOR, f"tr[id^='{op.prefixo_linha}']")
        vios.esperar_varios(ctx, linhas)
        processos, avisos = self._ler_pagina()
        vistos = {p.ci for p in processos}
        if op.proxima_pagina:
            for _ in range(MAX_PAGINAS):
                botao = next((b for b in ctx.driver.find_elements(*op.proxima_pagina)
                              if b.is_displayed() and "disabled" not in (b.get_attribute("class") or "")), None)
                if botao is None:
                    break
                primeira = ctx.driver.find_elements(*linhas)[:1]
                vios.clicar(ctx, botao)
                if primeira:
                    vios.esperar_ate(ctx, EC.staleness_of(primeira[0]), op.timeout_lista,
                                     "a próxima página da lista não carregou")
                vios.esperar_ajax(ctx, op.timeout_lista)
                self._conferir_bloqueio()
                novos, av = self._ler_pagina()
                novos = [p for p in novos if p.ci not in vistos]
                if not novos:
                    break
                vistos.update(p.ci for p in novos)
                processos += novos
                avisos += av
        if not processos:
            raise vios.ViosErro("a lista de processos ativos veio vazia (os filtros ou a tela mudaram?)")
        log.info("Parados: %d processo(s) ativo(s) na lista", len(processos))
        return processos, avisos

    # -- ficha
    def _esperar_tarefas(self):
        ctx = self.ctx

        def pronta(driver):
            if self._na_tela_de_login(driver):
                return "login"
            return "tarefas" if driver.execute_script(JS_ESTADO_FICHA) == "tarefas" else False

        try:
            return vios.esperar_ate(ctx, pronta, self.op.tempo_ficha, "a tabela de Tarefas não apareceu")
        except vios.ViosErro:
            if self._na_tela_de_login(ctx.driver):
                return "login"
            return ctx.driver.execute_script(JS_ESTADO_FICHA) or ""

    def ficha(self, proc):
        from selenium.common.exceptions import TimeoutException
        ctx = self.ctx
        url = self.op.url_ficha.format(ci=proc.ci)
        for tentativa in (1, 2):
            try:
                vios.abrir(ctx, url, timeout=self.op.tempo_ficha)
            except TimeoutException:
                # a página não terminou de carregar (jQuery ocupado): confere o bloqueio e segue
                self._conferir_bloqueio()
            estado = self._esperar_tarefas()
            if estado == "login":
                raise SessaoCaiu("a sessão do VIOS caiu (a tela de login apareceu)")
            if estado != "tarefas" and tentativa == 1 and self._pode_liberar():
                log.warning("Parados: a ficha do CI %s buscou dados por POST e o bloqueio barrou; liberando "
                            "XHR/fetch (formulário continua barrado) e tentando de novo", proc.ci)
                self._liberar()
                continue
            break
        bruto = ctx.driver.execute_script(JS_TAREFAS) or {}
        leitura = ler_tarefas_html(bruto.get("html") or "", self.op.colunas, info=bruto.get("info"))
        if not leitura.achou_tabela and not leitura.erro:
            leitura.erro = ("a tabela de Tarefas não apareceu na ficha" if bruto.get("ficha")
                            else "a ficha não carregou")
            if not self.liberado and self._xhr_barrado():
                # padrão "nao": não libera sozinho; o operador decide depois de conferir na tela real
                leitura.erro += (" (o bloqueio barrou XHR/fetch POST da ficha; se a ficha só carrega assim, "
                                 "conferir na tela real e usar ORELHA_PARADOS_LIBERAR_XHR=auto)")
        return leitura


# ---------------------------------------------------------------- execução
def _mensagem(e):
    texto = getattr(e, "msg", None) or str(e) or e.__class__.__name__
    return texto.strip().splitlines()[0][:200]


def conferir(ctx, op, processos, avisos_lista, leitor, persistir=True):
    """Lê as fichas do lote (com o limite e a retomada) e monta a Secao."""
    hoje = ctx.hoje
    por_ci = {p.ci: p for p in processos}
    progresso = ctx.ler_historico(PROGRESSO) if persistir else None
    lote, fora, prog = planejar(list(por_ci), progresso, op.maximo, hoje)
    log.info("Parados: %d processo(s) ativo(s); %s nesta execução (ciclo começado em %s, já conferidos %d)",
             len(por_ci), _qtd(len(lote), "ficha", "fichas"), prog["ciclo_inicio"], prog["lidos_no_ciclo"])
    if fora:
        log.info("Parados: %s ficam para as próximas execuções (limite ORELHA_PARADOS_MAX=%d): CI %s",
                 _qtd(len(fora), "processo", "processos"), op.maximo, _faixa(fora))
        log.debug("Parados: CIs que ficaram de fora: %s", ", ".join(map(str, fora)))

    feitos, falhas, parados, nao_parados = [], [], [], []
    erros_ficha, incompletos, itens = {}, {}, []
    interrompido, por_tempo = "", False
    inicio = time.monotonic()

    def salvar():
        if not persistir:
            return None
        novo, de_novo = atualizar_progresso(prog, lote, feitos, falhas, parados, nao_parados, fora, datetime.now())
        try:
            ctx.gravar_historico(PROGRESSO, novo)
        except OSError as e:
            log.error("Parados: não consegui gravar %s (%s)", PROGRESSO, e.__class__.__name__)
        return novo, de_novo

    resultado = None
    try:
        for n, ci in enumerate(lote, 1):
            if op.minutos and time.monotonic() - inicio > op.minutos * 60:
                por_tempo = True
                log.warning("Parados: tempo máximo (ORELHA_PARADOS_MINUTOS=%d) atingido na ficha %d de %d",
                            op.minutos, n, len(lote))
                break
            proc = por_ci[ci]
            log.info("Parados: ficha %d de %d (CI %s)", n, len(lote), ci)
            try:
                leitura = leitor.ficha(proc)
            except vios.BloqueioInativo:
                raise
            except SessaoCaiu as e:
                interrompido = _mensagem(e)
                log.error("Parados: %s na ficha %d de %d; o resto fica para a próxima execução", interrompido,
                          n, len(lote))
                break
            except Exception as e:
                leitura = LeituraFicha(False, erro=_mensagem(e))
            feitos.append(ci)
            av = avaliar(leitura, hoje, op.dias_grave)
            if av.situacao == "nao_lido":
                falhas.append(ci)
                erros_ficha[ci] = av.motivo
                log.warning("Parados: ficha do CI %s não lida: %s", ci, av.motivo)
            elif av.situacao == "incompleto":
                incompletos[ci] = av.motivo
                nao_parados.append(ci)
                log.warning("Parados: CI %s não confirmado: %s", ci, av.motivo)
            elif av.situacao == "parado":
                parados.append(ci)
                itens.append((item_parado(proc, av, hoje, op.agrupar),
                              av.ultima.concluida_em if av.ultima else None))
            else:
                nao_parados.append(ci)
            if persistir and n % SALVAR_A_CADA == 0:
                salvar()
    finally:
        resultado = salvar()
        leitor.fechar()

    novo, de_novo = resultado if resultado else atualizar_progresso(
        prog, lote, feitos, falhas, parados, nao_parados, fora, datetime.now())
    return montar_secao(op, por_ci, lote, fora, feitos, falhas, itens, erros_ficha, incompletos, de_novo,
                        novo, avisos_lista, interrompido, por_tempo, getattr(leitor, "liberado", False),
                        persistir)


def montar_secao(op, por_ci, lote, fora, feitos, falhas, itens, erros_ficha, incompletos, de_novo, novo,
                 avisos_lista, interrompido, por_tempo, liberado, persistir):
    lidos = len(feitos) - len(falhas)
    itens_ordenados = ordenar_itens(itens)
    graves = sum(1 for i in itens_ordenados if i.nivel == "grave")
    restantes = len([c for c in lote if c not in set(feitos)]) + len(fora)
    avisos = list(avisos_lista)

    if restantes:
        avisos.append(f"{_qtd(restantes, 'processo ativo ainda não foi conferido', 'processos ativos ainda não foram conferidos')} "
                      f"neste ciclo (até {op.maximo or 'todas as'} fichas por execução, ORELHA_PARADOS_MAX): "
                      "a próxima execução continua de onde esta parou.")
    if por_tempo:
        avisos.append(f"A leitura parou pelo tempo máximo (ORELHA_PARADOS_MINUTOS={op.minutos}).")
    if erros_ficha:
        novas = [c for c in erros_ficha if c not in de_novo]
        if novas:
            depois = ""
            if persistir:
                depois = ": " + ("será tentada" if len(novas) == 1 else "serão tentadas") + " de novo na próxima execução"
            avisos.append(f"{_qtd(len(novas), 'ficha não foi lida', 'fichas não foram lidas')} "
                          f"(CI {_faixa(novas)}){depois}.")
        motivos = sorted(set(erros_ficha.values()))
        avisos.append("Motivo: " + "; ".join(motivos[:3]) + ("; ..." if len(motivos) > 3 else ""))
    if de_novo:
        avisos.append(f"Ficha não lida pela segunda vez (CI {_faixa(de_novo)}): fica para o próximo ciclo.")
    for ci, motivo in sorted(incompletos.items()):
        avisos.append(f"CI {ci}: não deu para confirmar se está parado ({motivo}).")
    if liberado:
        avisos.append("As fichas foram lidas com as consultas XHR liberadas (ORELHA_PARADOS_LIBERAR_XHR); "
                      "envio de formulário continuou barrado.")
    if not persistir:
        avisos.append("Simulado: o progresso (retomada) não é gravado.")

    if restantes:
        resumo = (f"{_qtd(len(itens_ordenados), 'processo parado', 'processos parados')} entre "
                  f"{_qtd(lidos, 'conferido', 'conferidos')} nesta execução; faltam {restantes} para fechar o ciclo")
    else:
        no_ciclo = len(novo["parados_no_ciclo"])
        resumo = (f"{_qtd(len(itens_ordenados), 'processo parado', 'processos parados')} entre "
                  f"{_qtd(lidos, 'conferido', 'conferidos')}")
        if novo["ciclo_completo"] and novo["lidos_no_ciclo"] > lidos:
            resumo += f"; ciclo completo: {_qtd(no_ciclo, 'parado', 'parados')} em {novo['lidos_no_ciclo']} processos"
    if graves:
        resumo += f" ({_qtd(graves, 'urgente', 'urgentes')})"
    resumo += "."

    erro = ""
    if interrompido:
        erro = (f"{interrompido} depois de {_qtd(len(feitos), 'ficha', 'fichas')}; o que foi lido está abaixo e "
                "o resto fica para a próxima execução")
    elif feitos and lidos == 0:
        erro = f"nenhuma ficha foi lida ({next(iter(sorted(set(erros_ficha.values()))), 'sem detalhe')})"

    numeros = {"processos_ativos": len(por_ci), "conferidos": lidos, "parados": len(itens_ordenados),
               "graves": graves, "fichas_nao_lidas": len(falhas), "nao_confirmados": len(incompletos),
               "faltam_no_ciclo": restantes, "parados_no_ciclo": len(novo["parados_no_ciclo"])}
    return Secao(chave="parados", titulo=TITULO, resumo=resumo, itens=itens_ordenados, numeros=numeros,
                 erro=erro, avisos=avisos)


# ---------------------------------------------------------------- filtro nativo do VIOS (padrão)
# Visto ao vivo em 04/11/2026: a lista de processos (formulário GET) tem o filtro "Com ou sem tipo de
# tarefa?" = Sem + "Tipo de tarefa" = Abertas + Todas: devolve os processos SEM nenhuma tarefa
# aberta — exatamente os parados, sem abrir ficha por ficha (a leitura antiga abria todas as fichas
# e a lista inteira de ativos estourou o tempo de 120 s). Conferido: com/sem são disjuntos.
URL_SEM_TAREFA = ("?pag=sys/processos/processos-lista.php&menu_lateral=true&pesq[filtros_multi][]=ativos"
                  "&pesq[com_ou_sem_tipo_tarefa]=sem&pesq[flag_status_tipo_tarefa]=abertas"
                  "&pesq[processos_etapas_id]=TODAS")
LIMITE_FILTRO = 500   # a tela devolve no máximo 500 linhas por pesquisa (pedindo 1000, vieram 500)
TABELA_FILTRO = "processos-lista"
VAZIA_FILTRO = f'<table id="{TABELA_FILTRO}"><tbody></tbody></table>'
DIAS_GRAVE_FILTRO = 60


@dataclass
class Parado:
    ci: str
    numero: str = ""
    area: str = ""
    cliente: str = ""
    advogado: str = ""
    atualizado: Optional[date] = None   # "Última edição" do processo
    link: str = ""


def url_sem_tarefa(inicio=None, fim=None, limite=LIMITE_FILTRO):
    """Processos ativos sem tarefa aberta; com período, só os cadastrados de `inicio` a `fim`. Só GET."""
    url = URL_SEM_TAREFA
    if inicio is not None:
        url += f"&pesq[tp_data]=data_cadastro&pesq[idata]={vios.br(inicio)}&pesq[fdata]={vios.br(fim)}"
    return url + f"&pesq[limit]={limite}&Pesq=Pesquisar"


def parados_do_html(html, base=""):
    """Pura: HTML da lista de processos -> [Parado], pelas colunas do data-id
    (processos_id, nro_proc_html, pr_areas_nome, clientes_nome, advogado_nome, data_atualizacao)."""
    saida = []
    for ln in vios.ler_tabela_html(html, id_tabela=TABELA_FILTRO):
        ci = vios.digitos(ln.get("processos_id"))
        if not ci:
            continue
        cliente = re.sub(r"\s*\(\s*\d*\s*\)\s*$", "", vios.limpar(ln.get("clientes_nome")))
        saida.append(Parado(ci=ci, numero=vios.limpar(ln.get("nro_proc_html")), area=vios.limpar(ln.get("pr_areas_nome")),
                            cliente=cliente, advogado=vios.limpar(ln.get("advogado_nome")),
                            atualizado=vios.data_br(ln.get("data_atualizacao")),
                            link=urljoin(base, URL_FICHA.format(ci=ci)) if base else ""))
    return saida


def ler_sem_tarefa(ctx, inicio=None, fim=None):
    """Busca a pesquisa por GET (fetch de dentro da página do VIOS, sem desenhar: com 500 linhas o
    Chrome do bot travava mais de 120 s para desenhar a tela) e devolve o HTML. VAZIA_FILTRO se a
    tela de Processos veio sem a tabela (nenhum resultado); "" se não é a tela de Processos."""
    html = vios.buscar_get(ctx, url_sem_tarefa(inicio, fim), ctx.cfg.valor("ORELHA_PARADOS_TIMEOUT", 180, int))
    if f'id="{TABELA_FILTRO}"' in html:
        return html
    titulo = re.search(r"<title>([^<]*)</title>", html, re.I)
    return VAZIA_FILTRO if titulo and "Processos" in titulo.group(1) else ""


def ler_periodo_filtro(ctx, inicio, fim, contador, maximo, avisos):
    """Lê os cadastrados de `inicio` a `fim`; se vier cheio (500), divide o período ao meio."""
    if contador[0] >= maximo:
        return None
    contador[0] += 1
    html = ler_sem_tarefa(ctx, inicio, fim)
    if not html:
        avisos.append(f"a lista de processos não apareceu ({vios.br(inicio)} a {vios.br(fim)})")
        return []
    lidos = parados_do_html(html, ctx.cfg.vios_base)
    if len(lidos) < LIMITE_FILTRO:
        return lidos
    if inicio >= fim:
        avisos.append(f"o dia {vios.br(inicio)} tem {LIMITE_FILTRO} processos ou mais: pode faltar algum")
        return lidos
    meio = inicio + timedelta(days=(fim - inicio).days // 2)
    saida = []
    for a, b in ((inicio, meio), (meio + timedelta(days=1), fim)):
        parte = ler_periodo_filtro(ctx, a, b, contador, maximo, avisos)
        if parte is None:
            return None
        saida += parte
    return saida


def montar_parados(parados, hoje, dias_grave=DIAS_GRAVE_FILTRO):
    """Pura: [Parado] -> (itens, numeros, resumo). Grupo = área; "grave" = sem edição há mais de
    `dias_grave` dias; dentro da área, os mais antigos primeiro."""
    vistos, unicos = set(), []
    for x in parados:
        if x.ci not in vistos:
            vistos.add(x.ci)
            unicos.append(x)
    linhas = []
    for x in unicos:
        dias = (hoje - x.atualizado).days if x.atualizado else None
        grave = dias is None or dias > dias_grave
        partes = [x.cliente] if x.cliente else []
        if x.advogado:
            partes.append(f"advogado: {x.advogado}")
        partes.append(f"última edição {vios.br(x.atualizado)} (há {dias} dias)" if x.atualizado else "última edição não lida")
        titulo = x.numero or f"CI {x.ci}"
        area = x.area or "Sem área"
        linhas.append((area, not grave, -(dias or 10 ** 6), titulo,
                       Item(titulo=titulo, detalhe=" · ".join(partes), nivel="grave" if grave else "atencao",
                            link=x.link, grupo=area)))
    por_area = {}
    for area, *_ in linhas:
        por_area[area] = por_area.get(area, 0) + 1
    ordem = {a: i for i, a in enumerate(sorted(por_area, key=lambda a: (-por_area[a], a)))}
    linhas.sort(key=lambda l: (ordem[l[0]], l[1], l[2], l[3]))
    itens = [l[4] for l in linhas]
    graves = sum(1 for i in itens if i.nivel == "grave")
    numeros = {"parados": len(itens), "graves": graves, "atencao": len(itens) - graves,
               "dias_grave": dias_grave, "por_area": por_area}
    if not itens:
        resumo = "Nenhum processo ativo sem tarefa aberta."
    else:
        resumo = (f"{len(itens)} {'processo ativo' if len(itens) == 1 else 'processos ativos'} sem nenhuma tarefa "
                  f"aberta; {graves} sem edição há mais de {dias_grave} dias.")
    return itens, numeros, resumo


def _executar_filtro(ctx):
    cfg = ctx.cfg
    dias_grave = cfg.valor("ORELHA_PARADOS_DIAS_GRAVE", DIAS_GRAVE_FILTRO, int)
    maximo = cfg.valor("ORELHA_PARADOS_MAX_PAGINAS", 60, int)
    ctx.emitir("fase", fase="lendo_processos")
    avisos = []
    if ctx.simulado:
        parados = parados_do_html(simulado.ler(ctx, "sem_tarefa.html"), cfg.vios_base)
    else:
        contador = [1]
        vios.abrir(ctx, URL_LISTA)  # o fetch roda de dentro de uma página do VIOS (mesma sessão)
        html = ler_sem_tarefa(ctx)
        parados = parados_do_html(html, cfg.vios_base) if html else []
        if not html:
            avisos.append("a lista de processos não apareceu: conferir a tela processos-lista.php")
        elif len(parados) >= LIMITE_FILTRO:
            # mais de 500: lê por período de cadastro (um ano por vez, dividindo o que vier cheio)
            parados = []
            desde = vios.data_br(cfg.valor("ORELHA_PARADOS_DESDE", "01/01/2000")) or date(2000, 1, 1)
            for ano in range(desde.year, ctx.hoje.year + 1):
                a, b = max(desde, date(ano, 1, 1)), min(ctx.hoje, date(ano, 12, 31))
                parte = ler_periodo_filtro(ctx, a, b, contador, maximo, avisos)
                if parte is None:
                    avisos.append(f"parei no limite de {maximo} páginas (ORELHA_PARADOS_MAX_PAGINAS): "
                                  "a lista pode estar incompleta")
                    break
                parados += parte
        log.info("Parados: %d página(s) da lista de processos lidas", contador[0])
    itens, numeros, resumo = montar_parados(parados, ctx.hoje, dias_grave)
    return Secao(chave="parados", titulo=TITULO, resumo=resumo, itens=itens, numeros=numeros, avisos=avisos)


def executar(ctx):
    if ctx.cfg.valor("ORELHA_PARADOS_FONTE", "filtro").lower() != "fichas":
        return _executar_filtro(ctx)
    op = opcoes(ctx.cfg)
    ctx.emitir("fase", fase="lendo_processos")
    leitor = LeitorSimulado(ctx, op) if ctx.simulado else LeitorVios(ctx, op)
    try:
        processos, avisos = leitor.lista()
    except BaseException:
        leitor.fechar()
        raise
    return conferir(ctx, op, processos, avisos, leitor, persistir=not ctx.simulado)
