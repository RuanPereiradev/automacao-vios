"""Interpretação pura (sem navegador) das telas do VIOS que o coletor lê. Testada com HTML fictício.

Lista branca desde a leitura: cada função devolve só o que o coletor precisa (CI, área, telefones,
CPF para conferência). Nome, número CNJ, partes, valores, observações e comentários não saem daqui.
"""
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import quote

from consulta.fases import sem_acento
from nucleo import vios

URL_LISTA = "?pag=sys/processos/processos-lista.php&menu_lateral=true"
URL_PESSOAS = "?pag=sys/clientes/clientes.php"
URL_PESSOA_FORM = "?pag=sys/clientes/clientes.php&act=edit&clientes_id={id}"
PREFIXO_LINHA = "processos-lista_linha_"
LIMITE_LISTA = 30
CAMPOS_PESSOA = ("form[cpfcnpj]", "form[tel_celular]", "form[tel_residencial]", "form[tel_comercial]")
TERMOS_SEGREDO = ("SEGREDO", "SIGILO")


# ---------------------------------------------------------------- endereços (só GET)
def url_lista_processos(cpf_texto, limite=LIMITE_LISTA):
    """Lista de processos ATIVOS do CPF (`cpf_texto` já no formato que o filtro aceita)."""
    return (f"{URL_LISTA}&pesq[cpfcnpj]={quote(cpf_texto, safe='')}&pesq[filtros_multi][]=ativos"
            f"&pesq[limit]={limite}&Pesq=Pesquisar")


def url_lista_pessoas(cpf_texto):
    return f"{URL_PESSOAS}&pesq[busca]={quote(cpf_texto, safe='')}&Pesq=Pesquisar"


def url_form_pessoa(pessoa_id):
    return URL_PESSOA_FORM.format(id=int(pessoa_id))


# ---------------------------------------------------------------- área -> código fechado (seção 2)
AREAS = ("previdenciario", "trabalhista", "civel", "familia_sucessoes", "criminal", "tributario",
         "empresarial", "imobiliario", "administrativo", "ambiental", "outra")
# ordem importa: o primeiro que casa vence ("Cível Imobiliário" é imobiliário; "Previdenciário
# Administrativo" é previdenciário)
_REGRAS_AREA = (
    ("previdenciario", ("PREVIDENC", "INSS", "BENEFICIO")),
    ("trabalhista", ("TRABALH",)),
    ("tributario", ("TRIBUT", "FISCAL")),
    ("familia_sucessoes", ("FAMILIA", "SUCESS", "DIVORCIO", "INVENTARIO", "ALIMENTOS", "GUARDA")),
    ("criminal", ("CRIMIN", "PENAL")),
    ("empresarial", ("EMPRESARIAL", "SOCIETAR", "CONTRATO", "COMPLIANCE", "HOLDING", "INPI", "COMERCIAL")),
    ("imobiliario", ("IMOBILIAR",)),
    ("ambiental", ("AMBIENTAL",)),
    ("administrativo", ("ADMINISTRATIV",)),
    ("civel", ("CIVEL", "CONSUMIDOR")),
)


def area_codigo(texto):
    t = sem_acento(texto)
    for codigo, termos in _REGRAS_AREA:
        if any(x in t for x in termos):
            return codigo
    return "outra"


# ---------------------------------------------------------------- lista de processos
@dataclass
class ProcessoLista:
    ci: str
    area: str            # código fechado
    segredo: bool = False


@dataclass
class ListaProcessos:
    processos: list = field(default_factory=list)
    cpf_no_filtro: str = None   # dígitos do campo pesq[cpfcnpj] ecoado pela tela (None = não apareceu)


class _Campos(HTMLParser):
    """Valor (atributo value) dos <input> de nomes escolhidos. Só lê; guarda só o que foi pedido."""

    def __init__(self, nomes):
        super().__init__(convert_charrefs=True)
        self.nomes = set(nomes)
        self.valores = {}

    def handle_starttag(self, tag, attrs):
        if tag != "input":
            return
        a = dict(attrs)
        nome = a.get("name") or ""
        if nome in self.nomes and nome not in self.valores:
            self.valores[nome] = (a.get("value") or "").strip()


def ler_campos(html, nomes):
    """{nome: value} dos inputs com exatamente esses nomes (os ausentes não aparecem)."""
    p = _Campos(nomes)
    p.feed(html or "")
    p.close()
    return p.valores


def _tabelas(html):
    for i in range((html or "").lower().count("<table")):
        yield vios.ler_tabela_html(html, indice=i)


def _texto_tem_segredo(texto):
    t = sem_acento(texto)
    return any(x in t for x in TERMOS_SEGREDO)


def ler_lista_processos(html):
    """HTML da lista de processos -> ListaProcessos(CI, área em código, segredo; sem repetir CI)."""
    saida = ListaProcessos()
    eco = ler_campos(html, ("pesq[cpfcnpj]",)).get("pesq[cpfcnpj]")
    saida.cpf_no_filtro = vios.digitos(eco) if eco is not None else None
    vistos = set()
    for tabela in _tabelas(html):
        linhas = [l for l in tabela.linhas if (l.id or "").startswith(PREFIXO_LINHA)]
        if not linhas:
            continue
        for linha in linhas:
            ci = vios.digitos(linha.atributos.get("data-processos_id", "")) or \
                vios.digitos(linha.por_data_id.get("processos_id", ""))
            if not ci or ci in vistos:
                continue
            vistos.add(ci)
            area = linha.por_data_id.get("pr_areas_nome") or linha.get("Área")
            saida.processos.append(ProcessoLista(ci=ci, area=area_codigo(area),
                                                 segredo=_texto_tem_segredo(" ".join(linha.celulas))))
        break
    return saida


# ---------------------------------------------------------------- pessoas
_LINK_PESSOA = re.compile(r"""clientes-vis\.php[^"'<>\s]*?clientes_id=(\d+)""", re.I)


def ler_ids_pessoas(html):
    """ids dos cadastros achados pela busca (links clientes-vis.php&clientes_id=N), sem repetir."""
    ids = []
    for m in _LINK_PESSOA.finditer(html or ""):
        if m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


@dataclass
class Cadastro:
    cpf: str            # só dígitos
    telefones: list     # texto como está no cadastro (3 campos, sem os contatos extras)


def ler_form_pessoa(html):
    """Formulário act=edit (lido por GET, sem enviar) -> Cadastro. Só os 4 campos form[...]: os
    clientes_x_contatos[...] são outras pessoas e nunca são lidos."""
    v = ler_campos(html, CAMPOS_PESSOA)
    telefones = [v[n] for n in CAMPOS_PESSOA[1:] if v.get(n)]
    return Cadastro(cpf=vios.digitos(v.get("form[cpfcnpj]", "")), telefones=telefones)


# ---------------------------------------------------------------- segredo de justiça na ficha
class _TextosFicha(HTMLParser):
    """Textos dos <p> dos blocos de dados da ficha e dos selos (.vj-badge) que falam de segredo/sigilo."""

    VAZIAS = ("br", "img", "input", "hr", "meta", "link")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.achados = []
        self._pilha = []     # (tag, "bloco"|"p"|"selo"|"") dos elementos abertos
        self._atual = None   # pedaços de texto do <p>/selo que está sendo lido
        self._dono = -1      # posição na pilha do elemento dono do texto

    def handle_starttag(self, tag, attrs):
        if tag in self.VAZIAS:
            return
        classes = (dict(attrs).get("class") or "").split()
        tipo = ""
        if tag == "div" and "vj-bloco-info-text-area" in classes:
            tipo = "bloco"
        elif tag == "p" and any(t == "bloco" for _, t in self._pilha):
            tipo = "p"
        elif "vj-badge" in classes:
            tipo = "selo"
        self._pilha.append((tag, tipo))
        if tipo in ("p", "selo") and self._atual is None:
            self._atual, self._dono = [], len(self._pilha) - 1

    def handle_data(self, dados):
        if self._atual is not None:
            self._atual.append(dados)

    def handle_endtag(self, tag):
        if tag in self.VAZIAS or not any(t == tag for t, _ in self._pilha):
            return
        while self._pilha:
            aberta, _ = self._pilha.pop()
            if self._atual is not None and len(self._pilha) == self._dono:
                texto = vios.limpar("".join(self._atual))
                self._atual = None
                if _texto_tem_segredo(texto):
                    self.achados.append(texto)
            if aberta == tag:
                break


def textos_de_segredo(html):
    """Textos da ficha (HTML) que falam de segredo/sigilo, para `tem_segredo`."""
    p = _TextosFicha()
    p.feed(html or "")
    p.close()
    return p.achados


def tem_segredo(textos):
    """True se algum texto indica segredo de justiça/sigilo. Rótulo "Segredo de justiça: Não" não conta;
    qualquer outro valor (ou rótulo sem valor, ou selo) conta: na dúvida, é caso de gente."""
    for texto in textos or ():
        rotulo, sep, valor = texto.partition(":")
        if sep and _texto_tem_segredo(rotulo) and sem_acento(valor).strip(" .") in ("NAO", "N", "0", "NENHUM"):
            continue
        return True
    return False
