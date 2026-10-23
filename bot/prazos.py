"""Calendário de dias úteis por local do processo e cálculo de prazos (fatal, D-2, próximo dia útil).

Fontes de feriados:
- nacionais: calculados no código (fixos + Sexta-feira Santa) e a tabela doc/feriados-brasil-*.md;
- Justiça Federal: Lei 5.010/66, art. 62 (Carnaval, quarta e quinta da Semana Santa, 11/08, 01 e 02/11, 08/12);
- estaduais e municipais (capitais): tabela doc/feriados-brasil-*.md;
- manuais: doc/feriados.txt ("DD/MM/AAAA ; ESCOPO ; descrição").

Regra conservadora: só estende prazo o feriado que certamente vale para o processo.
O resto (pontos facultativos, feriado local em processo federal, cidade sem
cadastro) vira aviso para conferir — nunca empurra a data para depois.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

FIXOS = {
    (1, 1): "Confraternização Universal", (21, 4): "Tiradentes", (1, 5): "Dia do Trabalho",
    (7, 9): "Independência", (12, 10): "N. Sra. Aparecida", (2, 11): "Finados",
    (15, 11): "Proclamação da República", (20, 11): "Consciência Negra", (25, 12): "Natal",
}


def normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().split())


def pascoa(ano):
    # algoritmo de Meeus/Jones/Butcher
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


def nacionais(ano):
    datas = {date(ano, m, d): nome for (d, m), nome in FIXOS.items()}
    datas[pascoa(ano) - timedelta(days=2)] = "Sexta-feira Santa"
    return datas


def justica_federal(ano):
    """Lei 5.010/66, art. 62 (o recesso de 20/12 a 06/01 já é coberto pela suspensão do CPC)."""
    p = pascoa(ano)
    return {
        p - timedelta(days=48): "Carnaval (Lei 5.010/66)",
        p - timedelta(days=47): "Carnaval (Lei 5.010/66)",
        p - timedelta(days=4): "Quarta-feira Santa (Lei 5.010/66)",
        p - timedelta(days=3): "Quinta-feira Santa (Lei 5.010/66)",
        date(ano, 8, 11): "Dia da Justiça (Lei 5.010/66)",
        date(ano, 11, 1): "Todos os Santos (Lei 5.010/66)",
        date(ano, 12, 8): "N. Sra. da Conceição (Lei 5.010/66)",
    }


class Tabela:
    """Feriados lidos dos arquivos: tabela markdown + lista manual."""

    def __init__(self, arquivo_md=None, arquivo_txt=None):
        self.nacionais, self.facultativos = {}, {}
        self.estaduais, self.municipais = {}, {}  # UF -> {data: nome}; (CIDADE, UF) -> {data: nome}
        self.manuais = []  # (data, ESCOPO normalizado, nome)
        self.anos = set()
        if arquivo_md and Path(arquivo_md).exists():
            self._ler_md(Path(arquivo_md).read_text(encoding="utf-8"))
        if arquivo_txt and Path(arquivo_txt).exists():
            self._ler_txt(Path(arquivo_txt).read_text(encoding="utf-8"))

    def _ler_md(self, texto):
        secao, anos = "", []
        for linha in texto.splitlines():
            if linha.startswith("## "):
                secao, anos = normalizar(linha), []
                continue
            if not linha.startswith("|") or linha.startswith("|---"):
                continue
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            achados = [re.fullmatch(r"\d{4}", c) for c in celulas]
            if any(achados):  # cabeçalho: descobre as colunas de ano
                anos = [(i, int(c)) for i, c in enumerate(celulas) if re.fullmatch(r"\d{4}", c)]
                self.anos.update(a for _, a in anos)
                continue
            for i, ano in anos:
                m = re.search(r"(\d{2})/(\d{2})", celulas[i]) if i < len(celulas) else None
                if not m:
                    continue
                dia = date(ano, int(m.group(2)), int(m.group(1)))
                # "pontos facultativos" antes: o título dessa seção também diz "não são feriados nacionais"
                if "PONTOS FACULTATIVOS" in secao:
                    self.facultativos[dia] = celulas[0]
                elif "FERIADOS NACIONAIS" in secao:
                    self.nacionais[dia] = celulas[0]
                elif "ESTADUAIS" in secao:
                    self.estaduais.setdefault(celulas[0].upper(), {})[dia] = celulas[1]
                elif "MUNICIPAIS" in secao:
                    cap = re.match(r"(.+?)\s*\((\w{2})\)", celulas[0])
                    if cap:
                        chave = (normalizar(cap.group(1)), cap.group(2).upper())
                        self.municipais.setdefault(chave, {})[dia] = celulas[1]

    def _ler_txt(self, texto):
        for linha in texto.splitlines():
            partes = [p.strip() for p in linha.split("#", 1)[0].split(";")]
            if not partes[0]:
                continue
            dia = datetime.strptime(partes[0], "%d/%m/%Y").date()
            escopo = normalizar(partes[1]) if len(partes) > 1 and partes[1] else "TODOS"
            nome = partes[2] if len(partes) > 2 else "feriado manual"
            self.manuais.append((dia, escopo, nome))

    def cidades(self):
        return set(self.municipais)


class Calendario:
    """Calendário de um processo: federal ou não, UF e cidade."""

    def __init__(self, tabela=None, uf="", cidade="", federal=False):
        self.tabela = tabela or Tabela()
        self.uf, self.cidade, self.federal = uf.upper(), normalizar(cidade), federal
        self.feriados, self.avisos = {}, {}  # data -> nome
        self._anos = set()

    def descricao(self):
        local = f"{self.cidade}/{self.uf}" if self.cidade else (self.uf or "local não informado")
        return ("Justiça Federal" if self.federal else "Justiça Estadual/Trabalho") + f" — {local}"

    def _carregar(self, ano):
        if ano in self._anos:
            return
        self._anos.add(ano)
        t = self.tabela
        conta = dict(nacionais(ano))
        conta.update({d: n for d, n in t.nacionais.items() if d.year == ano})
        aviso = {d: f"ponto facultativo: {n}" for d, n in t.facultativos.items() if d.year == ano}
        estaduais = {d: n for d, n in t.estaduais.get(self.uf, {}).items() if d.year == ano}
        municipais = {d: n for d, n in t.municipais.get((self.cidade, self.uf), {}).items() if d.year == ano}
        if self.federal:
            conta.update(justica_federal(ano))
            aviso.update({d: f"feriado estadual ({self.uf}) em processo federal: {n}" for d, n in estaduais.items()})
            aviso.update({d: f"feriado municipal em processo federal: {n}" for d, n in municipais.items()})
        else:
            conta.update({d: f"{n} ({self.uf})" for d, n in estaduais.items()})
            conta.update({d: f"{n} ({self.cidade.title()})" for d, n in municipais.items()})
        for dia, escopo, nome in t.manuais:
            if dia.year != ano:
                continue
            vale = (
                escopo == "TODOS"
                or (escopo == "JUSTICA FEDERAL" and self.federal)
                or (escopo in ("JUSTICA ESTADUAL", "ESTADUAL") and not self.federal)
                or escopo == self.uf
                or escopo == f"{self.cidade}/{self.uf}"
            )
            if vale:
                conta[dia] = f"{nome} (manual)"
        for d in conta:
            aviso.pop(d, None)
        self.feriados.update(conta)
        self.avisos.update(aviso)

    def feriado(self, dia):
        self._carregar(dia.year)
        return self.feriados.get(dia)

    def util(self, dia):
        return dia.weekday() < 5 and not self.feriado(dia)

    def suspenso(self, dia):
        # recesso forense (CPC art. 220): prazos não correm de 20/12 a 20/01
        return (dia.month == 12 and dia.day >= 20) or (dia.month == 1 and dia.day <= 20)

    def proximo_util(self, dia):
        dia += timedelta(days=1)
        while not self.util(dia):
            dia += timedelta(days=1)
        return dia

    def menos_uteis(self, dia, n):
        for _ in range(n):
            dia -= timedelta(days=1)
            while not self.util(dia):
                dia -= timedelta(days=1)
        return dia

    def prazo_fatal(self, publicacao, dias, corridos=False):
        """Prazo começa no 1º dia útil após a publicação (CPC art. 224)."""
        dia = self.proximo_util(publicacao)
        contados = 0
        while True:
            if not self.suspenso(dia) and (corridos or self.util(dia)):
                contados += 1
                if contados == dias:
                    break
            dia += timedelta(days=1)
        # prazo que vence em dia não útil vai para o próximo dia útil
        while not self.util(dia) or self.suspenso(dia):
            dia += timedelta(days=1)
        return dia

    def d2(self, fatal):
        return self.menos_uteis(fatal, 2)

    def no_periodo(self, inicio, fim):
        """(feriados considerados, avisos) em dias de semana entre inicio e fim."""
        considerados, avisos = [], []
        dia = inicio
        while dia <= fim:
            self._carregar(dia.year)
            if dia.weekday() < 5:
                if dia in self.feriados:
                    considerados.append((dia, self.feriados[dia]))
                elif dia in self.avisos:
                    avisos.append((dia, self.avisos[dia]))
            dia += timedelta(days=1)
        return considerados, avisos


def contexto(item):
    """Extrai (uf, cidade, federal) de uma intimação capturada do VIOS."""
    cidade, _, uf = item.get("cidade", "").rpartition("/")
    federal = "JUSTICA FEDERAL" in normalizar(item.get("informacoes_extras", ""))
    return uf.strip(), cidade.strip(), federal
