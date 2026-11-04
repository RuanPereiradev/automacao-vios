"""Agenda de hoje e amanhã: compromissos, audiências, perícias e reuniões de hoje e amanhã, e os
feriados até o fim da semana (domingo).

Este módulo também tem a LEITURA DO CALENDÁRIO do VIOS, usada pela função prazos (funcoes/prazos.py).
A ideia vem do Zangão (branch bot-edita-vios, bot/calendario.py): abrir
`?pag=sys/agenda/calendario.php&menu_lateral=true`, esperar as tarefas (`.fc-event`, que chegam por
POST depois do load) e ler texto e link de cada uma. Copiado, não importado.

Somente leitura: o main.py liga o bloqueio de envios antes do login. O calendário busca as
tarefas por XHR POST, que o bloqueio "total" barra; por isso a leitura inteira roda dentro de
`navegador.pesquisa_liberada(driver)`, que deixa passar só XHR/fetch (formulário e sendBeacon
continuam barrados; o filtro opcional é enviado por vios.enviar_pesquisa, a exceção documentada no
navegador.py). Os únicos cliques são nos botões de mês anterior/próximo e de visão (Dia/Semana/Mês),
todos conferidos por vios.clicar.

Leitura (Selenium, fina) x interpretação (pura, testada com orelha/fixtures/agenda e /prazos):
  - ler_calendario(ctx, ...)  abre, filtra (opcional), navega os meses e devolve o bruto de cada mês:
                              os eventos da API do FullCalendar (se a instância estiver acessível) e o
                              HTML do calendário;
  - eventos_da_api / eventos_do_html / montar_eventos / campos_do_texto  interpretação;
  - montar_agenda(eventos, hoje)  os itens da seção.

A CONFERIR NA TELA REAL: versão do FullCalendar (3 ou 4+), onde ficam responsável e data limite
(propriedades do evento, tooltip ou só na ficha da tarefa), como os feriados aparecem, nomes dos
campos do filtro (ORELHA_*_FILTROS) e se o Pesquisar recarrega a página.
"""
import json
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from html.parser import HTMLParser

from nucleo import simulado, vios
from nucleo.modelos import Item, Secao

TITULO = "Agenda de hoje e amanhã"
PRECISA_VIOS = True

log = logging.getLogger("orelha")

URL_CALENDARIO = "?pag=sys/agenda/calendario.php&menu_lateral=true"
# tarefas cujo tipo/título tem um destes termos entram na agenda (sem diferença de acento)
TERMOS = ["AUDIÊNCIA", "PERÍCIA", "REUNIÃO", "SUSTENTAÇÃO", "OITIVA", "DILIGÊNCIA"]
TERMOS_ATENCAO = ["AUDIÊNCIA", "PERÍCIA"]  # de hoje = nível "atencao"
LINKS_TAREFA = ["pxe.php", "pxe_id", "pxe-lista.php"]  # link de tarefa do VIOS (o Zangão abre pxe.php&pxe_id=...;
# com "Agrupar" ligado, o calendário junta as tarefas do dia por tipo num link para pxe-lista.php)
LINKS_FERIADO = ["cal_feriados"]  # feriado do calendário abre ?pag=sys/agenda/cal_feriados.php (visto em 04/11/2026)
MARCAS_FERIADO = ["feriado"]  # classe/propriedade/tooltip que marca feriado
# feriados nacionais pelo nome (o calendário mostra, ex.: "Finados"), já sem acento e em maiúsculas
FERIADOS = ["CONFRATERNIZACAO UNIVERSAL", "ANO NOVO", "CARNAVAL", "QUARTA-FEIRA DE CINZAS",
            "SEXTA-FEIRA SANTA", "PAIXAO DE CRISTO", "TIRADENTES", "DIA DO TRABALHO", "DIA DO TRABALHADOR",
            "CORPUS CHRISTI", "INDEPENDENCIA DO BRASIL", "NOSSA SENHORA APARECIDA", "FINADOS",
            "PROCLAMACAO DA REPUBLICA", "CONSCIENCIA NEGRA", "NATAL"]
DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
CAMPOS = ("responsavel", "limite", "conclusao", "concluida", "tipo")  # ORELHA_CALENDARIO_CAMPOS


# ---------------------------------------------------------------- texto (puras)
def dobrar(texto):
    """Maiúsculas e sem acento, com o MESMO tamanho do texto (para achar no texto dobrado e
    recortar no original)."""
    saida = []
    for c in texto or "":
        base = unicodedata.normalize("NFKD", c).encode("ascii", "ignore").decode()
        saida.append((base or c).upper()[:1] or c)
    return "".join(saida)


def _hora(texto):
    """"14:00", "9h30" -> "09:30"; "14h" -> "14:00"; "" se não tem."""
    h = vios.hora(texto)
    if h:
        return h
    m = re.search(r"\b([01]?\d|2[0-3])\s*h\b", texto or "", re.IGNORECASE)
    return f"{int(m.group(1)):02d}:00" if m else ""


def _sem_hora(titulo):
    """Tira a hora do começo do título ("14:00 AUDIÊNCIA" -> "AUDIÊNCIA")."""
    return vios.limpar(re.sub(r"^\s*(?:[01]?\d|2[0-3])(?:[:h][0-5]\d|\s*h)\s*(?:[-–·]\s*)?", "", titulo or ""))


def _data_qualquer(valor):
    """date de "2026-11-04", "2026-11-04T10:00:00", "04/11/2026" ou "04/11/2026 10:00"; None se não é data."""
    if isinstance(valor, date):
        return valor
    texto = str(valor or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return vios.data_br(texto)


class _Texto(HTMLParser):
    BLOCO = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table", "section", "ul", "ol"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes, self.pular = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.pular += 1
        elif tag in self.BLOCO:
            self.partes.append("\n")
        elif tag in ("td", "th"):
            self.partes.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.pular = max(0, self.pular - 1)
        elif tag in self.BLOCO:
            self.partes.append("\n")

    def handle_data(self, dados):
        if not self.pular:
            self.partes.append(dados)


def texto_de_html(html):
    """Texto de um trecho de HTML, uma linha por bloco (como o innerText), sem script/style."""
    if "<" not in (html or ""):
        return html or ""
    leitor = _Texto()
    leitor.feed(html)
    leitor.close()
    linhas = (vios.limpar(l) for l in "".join(leitor.partes).splitlines())
    return "\n".join(l for l in linhas if l)


# rótulos da tarefa no VIOS (ficha: "Para conclusão DD/MM/AAAA Limite DD/MM/AAAA Concluída em: ...",
# "Responsáveis: ... Concluiu a tarefa: ...", ver doc/vios-mapa-processos.md da branch developer)
_DATA = r"(\d{1,2}/\d{1,2}/\d{4})"
_R_LIMITE = re.compile(r"\b(?:DATA\s+)?LIMITE\s*(?:EM)?\s*[:\-]?\s*" + _DATA)
_R_CONCLUSAO = re.compile(r"\b(?:(?:DATA\s+)?PARA\s+CONCLUSAO|DATA\s+PREVISTA|PREVISAO)\s*[:\-]?\s*" + _DATA)
_R_CONCLUIDA = re.compile(r"\bCONCLUIDA\s+EM\s*[:\-]?\s*" + _DATA)
_R_RESPONSAVEL = re.compile(r"\bRESPONSAVE(?:L|IS)(?:\s*\(\s*S\s*\))?\s*(?:OU\s+AUXILIAR(?:ES)?)?\s*:\s*")
_R_TIPO = re.compile(r"\bTIPO\s+DE\s+TAREFA\s*:\s*")
# fim do valor de um campo: o próximo rótulo (os genéricos só com ":"), ou um separador
_R_FIM_CAMPO = re.compile(r"\s(?:AUXILIAR|CONCLUIU|CONCLUIDA|(?:DATA\s+)?LIMITE|(?:DATA\s+)?PARA\s+CONCLUSAO|"
                          r"(?:DATA|TIPO|PROCESSO|CLIENTE|SITUACAO)\b[^:\n]{0,20}:)|[·|;\n]")


def _valor_ate_fim(original, dobrado, inicio):
    fim = _R_FIM_CAMPO.search(dobrado, inicio)
    valor = original[inicio:fim.start() if fim else len(original)]
    return vios.limpar(valor).strip(" ,.-:") or None


def campos_do_texto(texto):
    """Campos da tarefa num texto (tooltip do calendário ou ficha da tarefa):
    {"responsavel", "limite", "conclusao", "concluida_em", "tipo"}, só os que aparecem."""
    original = texto_de_html(texto)
    dobrado = dobrar(original)
    saida = {}
    for chave, regex in (("limite", _R_LIMITE), ("conclusao", _R_CONCLUSAO), ("concluida_em", _R_CONCLUIDA)):
        m = regex.search(dobrado)
        if m:
            d = vios.data_br(m.group(1))
            if d:
                saida[chave] = d
    for chave, regex in (("responsavel", _R_RESPONSAVEL), ("tipo", _R_TIPO)):
        m = regex.search(dobrado)
        if m:
            valor = _valor_ate_fim(original, dobrado, m.end())
            if valor:
                saida[chave] = valor
    return saida


def _simnao(valor):
    """True/False/None de "S", "Sim", "1", True, "Não", "N", "0"..."""
    if isinstance(valor, bool):
        return valor
    t = dobrar(str(valor if valor is not None else "")).strip()
    if t in ("S", "SIM", "1", "TRUE", "Y", "YES", "CONCLUIDA", "CONCLUIDO"):
        return True
    if t in ("N", "NAO", "0", "FALSE", "NO", ""):
        return False
    return None


def campos_das_props(props, mapa=None):
    """Campos da tarefa nas propriedades do evento da API do FullCalendar (extendedProps).
    `mapa` = {campo: nome da propriedade} de ORELHA_CALENDARIO_CAMPOS; sem mapa, adivinha pelo nome."""
    props = props or {}
    saida = {}

    def por(campo, valor):
        if valor in (None, ""):
            return
        if campo == "responsavel":
            texto = vios.limpar(texto_de_html(str(valor)))
            if re.search(r"[^\W\d_]", texto):  # tem letra (não é id)
                saida.setdefault("responsavel", texto)
        elif campo in ("limite", "conclusao"):
            d = _data_qualquer(valor)
            if d:
                saida.setdefault(campo, d)
        elif campo == "concluida":
            d = _data_qualquer(valor)
            if d:
                saida.setdefault("concluida_em", d)
            else:
                t = dobrar(str(valor))
                sim = _simnao(valor)
                if sim is None and ("CONCLU" in t or "CANCEL" in t):
                    sim = True
                if sim is not None:
                    saida.setdefault("concluida", sim)
        elif campo == "tipo":
            texto = vios.limpar(texto_de_html(str(valor)))
            if texto and not texto.isdigit():
                saida.setdefault("tipo", texto)

    for campo, nome in (mapa or {}).items():
        if nome in props:
            por(campo, props[nome])
    for nome, valor in props.items():
        k = dobrar(str(nome))
        if "RESPONS" in k:
            por("responsavel", valor)
        elif "LIMITE" in k:
            por("limite", valor)
        elif "PREVIST" in k or "PARA_CONCLUS" in k or "PARACONCLUS" in k:
            por("conclusao", valor)
        elif "CONCLUID" in k or "CONCLUSAO_EM" in k or "SITUACAO" in k or "STATUS" in k:
            por("concluida", valor)
        elif "CONCLUSAO" in k:  # "data de conclusão" sem "em": a tela chama de "Data para conclusão"
            por("conclusao", valor)
        elif "TIPO" in k and "PRAZO" not in k:
            por("tipo", valor)
    # texto livre (descrição/tooltip guardado na propriedade)
    for valor in props.values():
        if isinstance(valor, str) and len(valor) > 8:
            for k, v in campos_do_texto(valor).items():
                saida.setdefault(k, v)
    return saida


# ---------------------------------------------------------------- eventos (puras)
@dataclass
class Evento:
    titulo: str
    dia: date = None
    hora: str = ""
    link: str = ""
    categoria: str = "compromisso"   # "tarefa" | "compromisso" | "feriado" | "aniversario"
    tipo: str = ""
    responsavel: str = ""
    conclusao: date = None             # data para conclusão
    limite: date = None                # data limite
    concluida: bool = False
    classes: str = ""
    dica: str = ""                     # texto do tooltip
    props: dict = field(default_factory=dict)

    @property
    def pxe_id(self):
        m = re.search(r"pxe_id=(\d+)", self.link or "")
        return m.group(1) if m else ""

    def busca(self):
        """Texto dobrado (sem acento, maiúsculas) para procurar termos."""
        return dobrar(" ".join([self.titulo, self.tipo]))


def _absoluto(base, href):
    href = (href or "").strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return ""
    if re.match(r"https?://", href):
        return href
    from urllib.parse import urljoin
    return urljoin(base or "", href.lstrip("/")) if base else href


def eventos_da_api(dados, base=""):
    """Eventos devolvidos pelo JS da API do FullCalendar ({"versao", "eventos": [...]}, ou a lista)
    -> brutos normalizados {titulo, dia, hora, href, classes, dica, props}."""
    lista = dados.get("eventos", []) if isinstance(dados, dict) else (dados or [])
    saida = []
    for e in lista:
        if not isinstance(e, dict):
            continue
        inicio = str(e.get("inicio") or "")
        dia = _data_qualquer(inicio)
        resto = inicio[10:] if dia and "-" in inicio[:10] else inicio
        hora = "" if e.get("dia_inteiro") else _hora(resto.replace("T", " "))
        titulo = vios.limpar(texto_de_html(str(e.get("titulo") or "")))
        hora = hora or _hora(titulo[:6])
        saida.append({"titulo": _sem_hora(titulo), "dia": dia, "hora": hora,
                      "href": _absoluto(base, e.get("href")),
                      "classes": " ".join(x for x in (str(e.get("classes") or ""), str(e.get("exibicao") or "")) if x),
                      "dica": "", "props": dict(e.get("props") or {})})
    return saida


_ATRIBUTOS_DICA = ("title", "data-tippy-content", "data-original-title", "data-bs-original-title",
                   "data-content", "data-bs-content", "data-title", "aria-label")
_CLASSES_HORA = {"fc-event-time", "fc-time", "fc-list-event-time", "fc-list-item-time"}
_CLASSES_TITULO = {"fc-event-title", "fc-title", "fc-list-event-title", "fc-list-item-title"}
_CLASSES_MAIS = {"fc-daygrid-more-link", "fc-more", "fc-more-link", "fc-timegrid-more-link"}
_CLASSES_POPOVER = {"fc-popover", "fc-more-popover"}
_VAZIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class _LeitorCalendario(HTMLParser):
    """Lê os eventos (elementos com a classe do evento) do HTML do FullCalendar 4+/5/6: o dia vem do
    ancestral com data-date (grade de mês/semana) ou da última linha de dia da visão Lista."""

    def __init__(self, classe):
        super().__init__(convert_charrefs=True)
        self.classe = classe
        self.pilha = []          # [(tag, classes:set, attrs)]
        self.dia_lista = ""      # data-date da última linha de dia da visão Lista
        self.evento = None       # evento sendo lido
        self.nivel_evento = 0
        self.eventos = []
        self.mais = 0            # eventos escondidos em "+N mais"
        self.lendo_mais = None   # pedaços de texto do link "+N mais"
        self.nivel_mais = 0
        self.no_popover = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        classes = set(a.get("class", "").split())
        if tag not in _VAZIAS:
            self.pilha.append((tag, classes, a))
        if classes & _CLASSES_POPOVER:
            self.no_popover += 1
        if a.get("data-date") and classes & {"fc-list-day", "fc-list-heading"}:
            self.dia_lista = a["data-date"]
        if self.evento is None and self.lendo_mais is None and classes & _CLASSES_MAIS and tag not in _VAZIAS:
            self.lendo_mais, self.nivel_mais = [], len(self.pilha)
        e = self.evento
        if e is None and not self.no_popover and (self.classe in classes or classes & {"fc-bg-event", "fc-bgevent"}):
            dia = next((x[2]["data-date"] for x in reversed(self.pilha) if x[2].get("data-date")), "") \
                or self.dia_lista
            self.evento = {"href": a.get("href", "") if tag == "a" else "", "classes": a.get("class", ""),
                           "dia": dia, "texto": [], "hora": [], "titulo": [], "dica": [],
                           "em": None}
            self.nivel_evento = len(self.pilha) if tag not in _VAZIAS else 0
            e = self.evento
        if e is not None:
            if tag == "a" and not e["href"] and a.get("href"):
                e["href"] = a["href"]
            for nome in _ATRIBUTOS_DICA:
                if a.get(nome, "").strip():
                    e["dica"].append(a[nome])
            if e["em"] is None:
                if classes & _CLASSES_HORA:
                    e["em"] = ("hora", len(self.pilha))
                elif classes & _CLASSES_TITULO:
                    e["em"] = ("titulo", len(self.pilha))
            if tag == "br":
                e["texto"].append(" ")
        if tag in _VAZIAS and self.evento is not None and self.nivel_evento == 0:
            self._fechar_evento()

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VAZIAS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in _VAZIAS:
            return
        # fecha até a tag correspondente (HTML mal fechado é tolerado)
        while self.pilha:
            nivel = len(self.pilha)
            t, classes, _ = self.pilha.pop()
            e = self.evento
            if e is not None and e["em"] is not None and e["em"][1] == nivel:
                e["em"] = None
            if self.lendo_mais is not None and nivel == self.nivel_mais:
                m = re.search(r"\d+", "".join(self.lendo_mais))
                self.mais += int(m.group()) if m else 1
                self.lendo_mais = None
            if e is not None and nivel == self.nivel_evento:
                self._fechar_evento()
            if classes & _CLASSES_POPOVER:
                self.no_popover = max(0, self.no_popover - 1)
            if t == tag:
                break

    def handle_data(self, dados):
        if self.lendo_mais is not None:
            self.lendo_mais.append(dados)
        e = self.evento
        if e is None:
            return
        e["texto"].append(dados)
        if e["em"] is not None:
            e[e["em"][0]].append(dados)

    def _fechar_evento(self):
        self.eventos.append(self.evento)
        self.evento, self.nivel_evento = None, 0


def eventos_do_html(html, base="", classe="fc-event"):
    """Eventos do HTML do calendário -> (brutos normalizados, quantos ficaram escondidos em "+N mais").
    Eventos dentro do popover de "+N mais" são ignorados (repetem os da grade)."""
    leitor = _LeitorCalendario(classe)
    leitor.feed(html or "")
    leitor.close()
    if leitor.evento is not None:
        leitor._fechar_evento()
    saida = []
    for e in leitor.eventos:
        texto = vios.limpar(" ".join(e["texto"]))
        hora = _hora(" ".join(e["hora"])) if e["hora"] else _hora(texto[:6])
        titulo = vios.limpar(" ".join(e["titulo"])) or _sem_hora(texto)
        saida.append({"titulo": _sem_hora(titulo), "dia": _data_qualquer(e["dia"]), "hora": hora,
                      "href": _absoluto(base, e["href"]), "classes": e["classes"],
                      "dica": "\n".join(texto_de_html(d) for d in e["dica"]), "props": {}})
    return saida, leitor.mais


def _eh_feriado(titulo, marcas_texto, marcas):
    t = dobrar(titulo).strip(" .-")
    if "FERIADO" in t:
        return True
    if any(t == f or t.startswith(f + " ") or t.startswith(f + "-") for f in FERIADOS):
        return True
    return any(dobrar(m) in marcas_texto for m in marcas if m)


def montar_eventos(brutos, campos=None, links_tarefa=None, marcas_feriado=None):
    """Brutos (da API ou do HTML) -> [Evento], sem repetir (link/título + dia + hora), na ordem lida.
    Classifica em tarefa (link de tarefa do VIOS), feriado, aniversário ou compromisso, e junta
    responsável, data para conclusão, data limite e "concluída" das propriedades e do tooltip."""
    links_tarefa = LINKS_TAREFA if links_tarefa is None else links_tarefa
    marcas_feriado = MARCAS_FERIADO if marcas_feriado is None else marcas_feriado
    vistos, saida = set(), []
    for b in brutos:
        titulo = vios.limpar(b.get("titulo"))
        if not titulo:
            continue
        chave = (b.get("href") or dobrar(titulo), b.get("dia"), b.get("hora", ""))
        if chave in vistos:
            continue
        vistos.add(chave)
        info = campos_das_props(b.get("props"), campos)
        for k, v in campos_do_texto(b.get("dica", "")).items():
            info.setdefault(k, v)
        classes = b.get("classes", "") or ""
        marcas = dobrar(" ".join([classes, b.get("dica", ""), " ".join(f"{k} {v}" for k, v in (b.get("props") or {}).items())]))
        href = b.get("href", "")
        eh_feriado = _eh_feriado(titulo, marcas, marcas_feriado) or any(t in href for t in LINKS_FERIADO)
        if eh_feriado and not any(t in href for t in links_tarefa if t):
            categoria = "feriado"
        elif "ANIVERS" in dobrar(titulo) or "ANIVERS" in dobrar(classes):
            categoria = "aniversario"
        elif href and any(t in href for t in links_tarefa if t):
            categoria = "tarefa"
        else:
            categoria = "compromisso"
        concluida = bool(info.get("concluida")) or "concluida_em" in info \
            or any("CONCLU" in c and "NAO" not in c and "PEND" not in c for c in dobrar(classes).split())
        saida.append(Evento(titulo=titulo, dia=b.get("dia"), hora=b.get("hora", ""), link=href,
                            categoria=categoria, tipo=info.get("tipo", ""),
                            responsavel=info.get("responsavel", ""), conclusao=info.get("conclusao"),
                            limite=info.get("limite"), concluida=concluida, classes=classes,
                            dica=b.get("dica", ""), props=dict(b.get("props") or {})))
    return saida


# ---------------------------------------------------------------- agenda (pura)
def _plural(n, singular, plural=None):
    if plural is None:
        plural = singular[:-2] + "ões" if singular.endswith("ão") else singular + "s"
    return f"{n} {singular if n == 1 else plural}"


def _juntar(partes):
    partes = [p for p in partes if p]
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " e " + partes[-1]


def rotulo_dia(dia, hoje):
    """"Hoje · quarta-feira, 04/11", "Amanhã · ...", ou "sexta-feira, 06/11"."""
    nome = f"{DIAS_SEMANA[dia.weekday()]}, {dia:%d/%m}"
    if dia == hoje:
        return "Hoje · " + nome
    if dia == hoje + timedelta(days=1):
        return "Amanhã · " + nome
    return nome[:1].upper() + nome[1:]


def termo_de(evento, termos):
    """Primeiro termo de `termos` que aparece no título/tipo do evento (o termo como está na
    configuração) ou "". Tarefa vinda da lista de tarefas (props["fonte"] == "lista") só conta se o
    TIPO COMEÇA com o termo: "AUDIÊNCIA UNA (CÍVEL)" é audiência; "INFORMAR AUDIÊNCIA" e "LEMBRAR
    AUDIÊNCIA" são tarefas sobre a audiência, não o compromisso em si."""
    if (evento.props or {}).get("fonte") == "lista":
        texto = re.sub(r"^C:\s*", "", dobrar(evento.tipo or evento.titulo).strip())  # "C: ..." = consultoria
        for t in termos:
            if t and texto.startswith(dobrar(t)):
                return t
        return ""
    texto = evento.busca()
    for t in termos:
        if t and dobrar(t) in texto:
            return t
    return ""


def montar_agenda(eventos, hoje, termos=None, termos_atencao=None, tarefas_com_hora=False, aniversarios=False):
    """Eventos -> (itens, numeros, resumo) da seção.

    Entram: de hoje e amanhã, os compromissos da agenda (com ou sem hora), as tarefas cujo tipo/título
    tem um dos `termos` (com tarefas_com_hora, também qualquer tarefa com hora) e, se pedido, os
    aniversários; de hoje até domingo, os feriados. Audiência/perícia de hoje = "atencao"."""
    termos = TERMOS if termos is None else termos
    termos_atencao = TERMOS_ATENCAO if termos_atencao is None else termos_atencao
    amanha = hoje + timedelta(days=1)
    fim_semana = max(hoje + timedelta(days=6 - hoje.weekday()), amanha)
    escolhidos = []
    for ev in eventos:
        if ev.dia is None:
            continue
        if ev.categoria == "feriado":
            if hoje <= ev.dia <= fim_semana:
                escolhidos.append((ev, ""))
            continue
        if ev.dia not in (hoje, amanha):
            continue
        if ev.categoria == "aniversario" and not aniversarios:
            continue
        termo = termo_de(ev, termos)
        if ev.categoria == "tarefa" and not termo and not (tarefas_com_hora and ev.hora):
            continue
        escolhidos.append((ev, termo))
    escolhidos.sort(key=lambda x: (x[0].dia, x[0].categoria != "feriado", x[0].hora or "", dobrar(x[0].titulo)))

    atencao = {dobrar(t) for t in termos_atencao if t}
    itens, por_dia, feriados = [], {hoje: {}, amanha: {}}, []
    for ev, termo in escolhidos:
        if ev.categoria == "feriado":
            feriados.append(ev)
            itens.append(Item(titulo=ev.titulo, detalhe="Feriado", nivel="info", grupo=rotulo_dia(ev.dia, hoje)))
            continue
        tipo = termo.lower() if termo else ("aniversário" if ev.categoria == "aniversario" else "compromisso")
        por_dia[ev.dia][tipo] = por_dia[ev.dia].get(tipo, 0) + 1
        detalhe = [ev.hora or "dia todo"]
        if ev.responsavel:
            detalhe.append(f"responsável: {ev.responsavel}")
        if ev.tipo and dobrar(ev.tipo) not in dobrar(ev.titulo):
            detalhe.append(ev.tipo)
        if (ev.props or {}).get("etiqueta"):
            detalhe.append(f"etiqueta no VIOS: {ev.props['etiqueta']}")
        if ev.concluida:
            detalhe.append("concluída")
        nivel = "atencao" if ev.dia == hoje and termo and dobrar(termo) in atencao and not ev.concluida else "info"
        itens.append(Item(titulo=ev.titulo, detalhe=" · ".join(detalhe), nivel=nivel,
                          link=ev.link if ev.link.startswith(("http://", "https://")) else "",
                          grupo=rotulo_dia(ev.dia, hoje)))

    def contagem(dia, termo):
        return por_dia[dia].get(termo.lower(), 0)

    numeros = {"hoje": sum(por_dia[hoje].values()), "amanha": sum(por_dia[amanha].values()),
               "feriados": len(feriados),
               "audiencias_hoje": contagem(hoje, "AUDIÊNCIA"), "pericias_hoje": contagem(hoje, "PERÍCIA"),
               "audiencias_amanha": contagem(amanha, "AUDIÊNCIA"), "pericias_amanha": contagem(amanha, "PERÍCIA")}

    ordem = [t.lower() for t in termos if t] + ["compromisso", "aniversário"]

    def frase(dia):
        tipos = por_dia[dia]
        if not tipos:
            return "nada marcado"
        return _juntar([_plural(tipos[t], t) for t in ordem if tipos.get(t)])

    resumo = f"Hoje: {frase(hoje)}. Amanhã: {frase(amanha)}."
    if feriados:
        lista = _juntar([f"{f.titulo} ({DIAS_SEMANA[f.dia.weekday()]}, {f.dia:%d/%m})" for f in feriados])
        resumo += f" {'Feriado' if len(feriados) == 1 else 'Feriados'} até domingo: {lista}."
    return itens, numeros, resumo


# ---------------------------------------------------------------- configuração do calendário
def _pares(texto):
    """"pesq[concluida]=N; pesq[responsavel]=" -> {"pesq[concluida]": "N", "pesq[responsavel]": ""}."""
    saida = {}
    for parte in str(texto).split(";"):
        if not parte.strip():
            continue
        if "=" not in parte:
            raise ValueError("use nome=valor separados por ;")
        nome, valor = parte.split("=", 1)
        saida[nome.strip()] = valor.strip()
    return saida


def _mapa_campos(texto):
    mapa = _pares(texto)
    errados = [c for c in mapa if c not in CAMPOS]
    if errados:
        raise ValueError(f"campos aceitos: {', '.join(CAMPOS)}")
    return mapa


@dataclass
class Calendario:
    """Seletores e opções da tela do calendário (ORELHA_CALENDARIO_* no .env; vazio = padrão)."""
    url: str = URL_CALENDARIO
    evento: tuple = None
    classe_evento: str = "fc-event"
    area: tuple = None
    anterior: tuple = None
    proximo: tuple = None
    titulo_mes: tuple = None
    visao: tuple = None
    filtro_campo: tuple = None
    recarrega: bool = True
    campos: dict = field(default_factory=dict)
    links_tarefa: list = field(default_factory=lambda: list(LINKS_TAREFA))
    marcas_feriado: list = field(default_factory=lambda: list(MARCAS_FERIADO))

    @classmethod
    def do_cfg(cls, cfg):
        v = cfg.valor
        return cls(
            url=v("ORELHA_CALENDARIO_URL", URL_CALENDARIO),
            evento=v("ORELHA_CALENDARIO_TAREFA", "css:.fc-event", "seletor"),
            classe_evento=v("ORELHA_CALENDARIO_CLASSE_EVENTO", "fc-event"),
            area=v("ORELHA_CALENDARIO_AREA", "css:.fc", "seletor"),
            anterior=v("ORELHA_CALENDARIO_ANTERIOR", "css:.fc-prev-button", "seletor"),
            proximo=v("ORELHA_CALENDARIO_PROXIMO", "css:.fc-next-button", "seletor"),
            titulo_mes=v("ORELHA_CALENDARIO_TITULO", "css:.fc-toolbar-title, .fc-toolbar h2, .fc-center h2", "seletor"),
            visao=v("ORELHA_CALENDARIO_VISAO", "", "seletor"),
            filtro_campo=v("ORELHA_CALENDARIO_FILTRO_CAMPO", "", "seletor"),
            recarrega=v("ORELHA_CALENDARIO_PESQUISA_RECARREGA", True, bool),
            campos=v("ORELHA_CALENDARIO_CAMPOS", "", _mapa_campos) or {},
            links_tarefa=v("ORELHA_CALENDARIO_LINK_TAREFA", ",".join(LINKS_TAREFA), "lista"),
            marcas_feriado=v("ORELHA_CALENDARIO_FERIADO", ",".join(MARCAS_FERIADO), "lista"),
        )


def filtros_do_cfg(cfg, prefixo):
    """(filtros {nome do campo: valor}, nomes de <select multiple> para marcar todas) de
    ORELHA_<PREFIXO>_FILTROS e ORELHA_<PREFIXO>_MARCAR_TODAS."""
    filtros = cfg.valor(f"ORELHA_{prefixo}_FILTROS", "", _pares) or {}
    marcar = cfg.valor(f"ORELHA_{prefixo}_MARCAR_TODAS", "", "lista") or []
    return filtros, marcar


# ---------------------------------------------------------------- leitura (Selenium)
# Eventos pela API do FullCalendar, se a instância estiver acessível: 4+ (objeto global com
# getEvents) ou 3 (plugin jQuery, clientEvents). Traz tudo o que foi carregado, inclusive o que a
# grade esconde em "+N mais", e as propriedades extras de cada evento (só valores simples).
_JS_API = r"""
const LIMITE = 40, dois = n => String(n).padStart(2, '0'), corta = v => String(v).slice(0, 500);
const iso = (d, diaInteiro) => {
    if (!d) return '';
    if (typeof d.format === 'function' && d._isAMomentObject) {
        const temHora = typeof d.hasTime === 'function' ? d.hasTime() : !diaInteiro;
        return d.format(temHora ? 'YYYY-MM-DD[T]HH:mm' : 'YYYY-MM-DD');
    }
    const x = d instanceof Date ? d : new Date(d);
    if (isNaN(x)) return String(d).slice(0, 16);
    const dia = x.getFullYear() + '-' + dois(x.getMonth() + 1) + '-' + dois(x.getDate());
    return diaInteiro ? dia : dia + 'T' + dois(x.getHours()) + ':' + dois(x.getMinutes());
};
const simples = (o, fora) => {
    const r = {}; let n = 0;
    for (const k of Object.keys(o || {})) {
        if (n >= LIMITE) break;
        if (fora.has(k) || k.charAt(0) === '_') continue;
        let v; try { v = o[k]; } catch (e) { continue; }
        if (Array.isArray(v)) v = v.filter(x => ['string', 'number'].includes(typeof x)).join(', ');
        if (v === null || v === undefined || v === '') continue;
        if (['string', 'number', 'boolean'].includes(typeof v)) { r[k] = typeof v === 'string' ? corta(v) : v; n++; }
    }
    return r;
};
const V3 = new Set(['title', 'start', 'end', 'url', 'className', 'allDay', 'source', 'id', 'rendering', 'color',
    'backgroundColor', 'borderColor', 'textColor', 'editable', 'startEditable', 'durationEditable', 'overlap',
    'constraint', 'resourceEditable']);
let versao = '', lista = null;
for (const k of Object.keys(window)) {
    let v; try { v = window[k]; } catch (e) { continue; }
    if (v && typeof v === 'object' && typeof v.getEvents === 'function' && typeof v.getDate === 'function') {
        try {
            lista = v.getEvents().map(e => ({titulo: e.title || '', inicio: iso(e.start, e.allDay),
                dia_inteiro: !!e.allDay, href: e.url || '', classes: (e.classNames || []).join(' '),
                exibicao: e.display || '', props: simples(e.extendedProps, new Set())}));
            versao = '4+'; break;
        } catch (e) { lista = null; }
    }
}
if (!lista && window.jQuery && jQuery.fn && jQuery.fn.fullCalendar) {
    const el = jQuery('.fc').first();
    if (el.length) {
        try {
            lista = (el.fullCalendar('clientEvents') || []).map(e => ({titulo: e.title || '',
                inicio: iso(e.start, e.allDay), dia_inteiro: !!e.allDay, href: e.url || '',
                classes: [].concat(e.className || []).join(' '), exibicao: e.rendering || '', props: simples(e, V3)}));
            versao = '3';
        } catch (e) { lista = null; }
    }
}
return {versao: versao, eventos: (lista || []).slice(0, 5000)};
"""


def _coletar(ctx, conf):
    """Bruto do mês que está na tela: {"api": {...} ou None, "html": HTML do calendário}."""
    try:
        api = ctx.driver.execute_script(_JS_API)
    except Exception as e:
        log.info("Calendário: API do FullCalendar não acessível (%s)", e.__class__.__name__)
        api = None
    try:
        html = vios.html(ctx, conf.area) if conf.area else vios.html(ctx)
    except vios.ViosErro:
        html = vios.html(ctx)
    return {"api": api, "html": html}


def _titulo_mes(ctx, conf):
    if not conf.titulo_mes:
        return ""
    try:
        els = ctx.driver.find_elements(*conf.titulo_mes)
        return vios.limpar(els[0].text) if els else ""
    except Exception:
        return ""


def _trocar_mes(ctx, conf, botao):
    """Clica em mês anterior/próximo e espera o título do calendário mudar e o AJAX terminar."""
    antes = _titulo_mes(ctx, conf)
    vios.clicar(ctx, botao)
    if antes:
        vios.esperar_ate(ctx, lambda d: _titulo_mes(ctx, conf) not in ("", antes),
                         mensagem="o calendário não trocou de mês")
    else:
        time.sleep(1)
    vios.esperar_ajax(ctx)
    vios.esperar_varios(ctx, conf.evento, timeout=min(5, ctx.cfg.timeout))


def ler_calendario(ctx, conf, filtros=None, marcar_todas=(), meses_antes=0, meses_depois=0, prefixo=""):
    """Abre o calendário (dentro de pesquisa_liberada: as tarefas chegam por XHR POST), aplica o
    filtro (se configurado), lê o mês atual e os `meses_antes` anteriores / `meses_depois` seguintes.
    Devolve (lotes [{"api", "html"}], avisos)."""
    from nucleo import navegador
    avisos, lotes = [], []
    with navegador.pesquisa_liberada(ctx.driver):
        log.info("Abrindo o calendário: %s", conf.url)
        vios.abrir(ctx, conf.url)
        if not vios.esperar_varios(ctx, conf.evento):
            log.warning("Nenhuma tarefa apareceu no calendário em %ds", ctx.cfg.timeout)
        if filtros or marcar_todas:
            if not conf.filtro_campo:
                avisos.append(f"ORELHA_{prefixo}_FILTROS preenchido, mas falta ORELHA_CALENDARIO_FILTRO_CAMPO "
                              "(um campo do formulário de filtro): o filtro não foi aplicado")
            else:
                r = vios.enviar_pesquisa(ctx, conf.filtro_campo, filtros or {}, marcar_todas,
                                         esperar_recarregar=conf.recarrega)
                if r.get("faltando"):
                    avisos.append(f"campos do filtro que não existem na tela: {', '.join(r['faltando'])} "
                                  f"(conferir ORELHA_{prefixo}_FILTROS / ORELHA_{prefixo}_MARCAR_TODAS)")
                if not conf.recarrega:
                    time.sleep(1)
                    vios.esperar_ajax(ctx)
                vios.esperar_varios(ctx, conf.evento)
        if conf.visao:
            vios.clicar(ctx, conf.visao)
            vios.esperar_ajax(ctx)
            vios.esperar_varios(ctx, conf.evento, timeout=min(5, ctx.cfg.timeout))
        log.info("Calendário: lendo %s", _titulo_mes(ctx, conf) or "o mês atual")
        lotes.append(_coletar(ctx, conf))
        for _ in range(meses_antes):
            _trocar_mes(ctx, conf, conf.anterior)
            log.info("Calendário: lendo %s", _titulo_mes(ctx, conf) or "o mês anterior")
            lotes.append(_coletar(ctx, conf))
        if meses_depois:
            for _ in range(meses_antes):  # volta ao mês de partida
                _trocar_mes(ctx, conf, conf.proximo)
            for _ in range(meses_depois):
                _trocar_mes(ctx, conf, conf.proximo)
                log.info("Calendário: lendo %s", _titulo_mes(ctx, conf) or "o mês seguinte")
                lotes.append(_coletar(ctx, conf))
        barrados = navegador.tentativas_barradas(ctx.driver)
    if barrados:
        log.warning("Bloqueio de envios barrou na tela do calendário: %s", "; ".join(barrados[:5]))
        avisos.append(f"o bloqueio de envios barrou {len(barrados)} envio(s) na tela do calendário "
                      "(nada foi gravado; ver logs/orelha.log)")
    return lotes, avisos


def brutos_dos_lotes(lotes, base, classe="fc-event"):
    """Lotes da leitura -> (brutos, avisos). Usa a API do FullCalendar quando ela trouxe eventos
    (completa); senão o HTML (avisa se a grade escondeu eventos em "+N mais")."""
    brutos, avisos, escondidos, origem = [], [], 0, set()
    for lote in lotes:
        api = lote.get("api") or {}
        eventos_api = eventos_da_api(api, base) if api.get("eventos") else []
        if eventos_api:
            brutos += eventos_api
            origem.add(f"API do FullCalendar {api.get('versao', '')}".strip())
            continue
        do_html, mais = eventos_do_html(lote.get("html", ""), base, classe)
        brutos += do_html
        escondidos += mais
        origem.add("HTML da tela")
    if escondidos:
        avisos.append(f"o calendário escondeu {escondidos} evento(s) em \"+ mais\" que não foram lidos "
                      "(use a visão Semana/Lista em ORELHA_CALENDARIO_VISAO)")
    sem_dia = sum(1 for b in brutos if b.get("dia") is None)
    if sem_dia:
        avisos.append(f"{sem_dia} evento(s) do calendário sem data reconhecida (conferir a versão do calendário)")
    log.info("Calendário: %d evento(s) lido(s) (%s)", len(brutos), ", ".join(sorted(origem)) or "nada")
    return brutos, avisos


def lotes_simulados(ctx, nomes):
    """Fixtures no lugar da tela: "*.json" = resposta do JS da API; "*.html" = HTML do calendário."""
    lotes = []
    for nome in nomes:
        texto = simulado.ler(ctx, nome)
        if nome.endswith(".json"):
            lotes.append({"api": json.loads(texto), "html": ""})
        else:
            lotes.append({"api": None, "html": texto})
    return lotes


# ---------------------------------------------------------------- tarefas da equipe (lista de tarefas)
def tarefas_da_equipe(ctx, inicio, fim, avisos):
    """Tarefas NÃO concluídas da equipe toda com data para conclusão de `inicio` a `fim`, lidas da
    lista de tarefas do VIOS (a mesma leitura dos prazos), como Evento(categoria="tarefa")."""
    from funcoes import prazos  # aqui dentro: prazos importa agenda
    if ctx.simulado:
        try:
            html = simulado.ler(ctx, "lista.html")
        except FileNotFoundError:
            return []
        lidas = prazos.tarefas_da_lista(html, ctx.cfg.vios_base)
    else:
        lidas = prazos.ler_periodo(ctx, "data_prevista", inicio, fim, [0],
                                   ctx.cfg.valor("ORELHA_PRAZOS_MAX_PAGINAS", 60, int), avisos) or []
    return [Evento(titulo=t.titulo, dia=t.conclusao, hora=t.hora, link=t.link, categoria="tarefa", tipo=t.tipo,
                   responsavel=t.responsavel, conclusao=t.conclusao, limite=t.limite,
                   props={"fonte": "lista", "etiqueta": t.etiqueta})
            for t in lidas if t.conclusao is not None and inicio <= t.conclusao <= fim]


# ---------------------------------------------------------------- função
def executar(ctx):
    cfg, hoje = ctx.cfg, ctx.hoje
    conf = Calendario.do_cfg(cfg)
    termos = cfg.valor("ORELHA_AGENDA_TERMOS", ",".join(TERMOS), "lista")
    termos_atencao = cfg.valor("ORELHA_AGENDA_TERMOS_ATENCAO", ",".join(TERMOS_ATENCAO), "lista")
    com_hora = cfg.valor("ORELHA_AGENDA_TAREFAS_COM_HORA", False, bool)
    aniversarios = cfg.valor("ORELHA_AGENDA_ANIVERSARIOS", False, bool)
    amanha = hoje + timedelta(days=1)
    ate = max(hoje + timedelta(days=6 - hoje.weekday()), amanha)

    ctx.emitir("fase", fase="lendo_calendario")
    if ctx.simulado:
        lotes, avisos = lotes_simulados(ctx, ["calendario.html"]), []
    else:
        filtros, marcar = filtros_do_cfg(cfg, "AGENDA")
        depois = (ate.year - hoje.year) * 12 + ate.month - hoje.month
        lotes, avisos = ler_calendario(ctx, conf, filtros, marcar, meses_depois=depois, prefixo="AGENDA")
    brutos, mais_avisos = brutos_dos_lotes(lotes, cfg.vios_base, conf.classe_evento)
    avisos += mais_avisos
    if not brutos:
        avisos.append("nenhum evento lido no calendário (conferir ORELHA_CALENDARIO_TAREFA e o filtro)")
    eventos = montar_eventos(brutos, conf.campos, conf.links_tarefa, conf.marcas_feriado)
    if cfg.valor("ORELHA_AGENDA_TAREFAS_FONTE", "lista").lower() != "calendario":
        # o calendário abre filtrado no usuário logado e agrupa as tarefas: as da EQUIPE vêm da lista
        # de tarefas (pxe-lista.php, por GET); do calendário ficam compromissos, feriados e aniversários
        eventos = [e for e in eventos if e.categoria != "tarefa"] + tarefas_da_equipe(ctx, hoje, amanha, avisos)
    itens, numeros, resumo = montar_agenda(eventos, hoje, termos, termos_atencao, com_hora, aniversarios)
    return Secao(chave="agenda", titulo=TITULO, resumo=resumo, itens=itens, numeros=numeros, avisos=avisos)
