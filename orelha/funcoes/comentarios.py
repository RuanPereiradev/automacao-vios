"""Comentários dos processos: para uma LISTA de números de processo, os comentários do quadro
"Comentários" da ficha do processo (processos-vis.php) feitos nos últimos N dias (padrão 90).
Só leitura: a busca do número é GET (buscada de dentro da página) e a ficha é aberta como a lupa.

Visto ao vivo em 23/11/2026: o quadro é a tabela #tabela_v5_processo_vis_tabela_coment (desenhada
pelo Vue depois que a página abre), com as colunas "Data / Usuário" ("21/11/2026 01:47 - NOME") e
"Comentário", do mais novo para o mais antigo, todas as linhas na tela (sem paginação). Entram
também as observações de conclusão de tarefa que o VIOS copia para lá.

A lista vem de um arquivo de texto, um número por linha (linhas vazias e com # são ignoradas).
Número CNJ é buscado com a máscara; outro número (ex.: IPL nº 2021.0000001) é buscado como veio,
sem o texto antes do primeiro dígito. Um número com vários cadastros (vários clientes) lê todos.

Não entra no relatório do dia (RELATORIO_DIARIO = False). Gera em saida/<AAAA-MM-DD>/:
    comentarios-<N>dias.csv   separado por ";", UTF-8 com BOM, uma linha por comentário; processo
                              sem comentário no período (ou não achado) vira uma linha só, dizendo isso
    comentarios-<N>dias.json  os mesmos dados
Os arquivos têm nomes de clientes e textos internos: ficam em orelha/saida/, fora do git.

.env:
    ORELHA_COMENTARIOS_LISTA    arquivo com os números (padrão entrada/comentarios.txt, a partir de orelha/)
    ORELHA_COMENTARIOS_DIAS     quantos dias para trás (padrão 90; conta o dia de hoje e o 90º dia)
    ORELHA_COMENTARIOS_TIMEOUT  segundos para a ficha desenhar o quadro (padrão 40)
"""
import csv
import json
import logging
import re
import time
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin

from funcoes import processos as lista_processos
from nucleo import simulado, vios
from nucleo.modelos import Item, Secao

log = logging.getLogger("orelha.comentarios")

TITULO = "Comentários dos processos"
PRECISA_VIOS = True
RELATORIO_DIARIO = False

DIAS = 90
LISTA_PADRAO = "entrada/comentarios.txt"
TABELA = "tabela_v5_processo_vis_tabela_coment"
URL_BUSCA = ("?pag=sys/processos/processos-lista.php&menu_lateral=true&pesq[filtros][]=todos"
             "&campo_pesquisa_selecionado=nro_proc&pesq[busca]={numero}&Pesq=Pesquisar")
URL_FICHA = "?pag=sys/processos/processos-vis.php&processos_id={ci}"
DATA_USUARIO = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})(?:\s+(\d{2}:\d{2}))?\s*-?\s*(.*)$", re.S)

OK, SEM_RECENTE, SEM_NENHUM, NAO_ACHADO, ERRO = (
    "com comentário no período", "sem comentário no período", "nenhum comentário", "não encontrado no VIOS",
    "não deu para ler")

CABECALHO = ["Número", "CI", "Cliente", "Situação do processo", "Resultado", "Data", "Hora", "Usuário",
             "Comentário", "Último comentário (fora do período)", "Link no VIOS"]


# ---------------------------------------------------------------- lista (puras)
def ler_lista(texto):
    """Números do arquivo, na ordem, sem repetir. Ignora linha vazia e linha que começa com #."""
    vistos, saida = set(), []
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        chave = vios.digitos(linha) or linha
        if chave not in vistos:
            vistos.add(chave)
            saida.append(linha)
    return saida


def termo_de_busca(numero):
    """CNJ (20 dígitos) com a máscara; outro número sem o texto antes do 1º dígito ("IPL nº 2021.0000001"
    -> "2021.0000001")."""
    d = vios.digitos(numero)
    if len(d) == 20:
        return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"
    m = re.search(r"\d.*$", numero.strip())
    return m.group(0).strip() if m else numero.strip()


def cadastros_do_numero(html, numero, base=""):
    """Pura: HTML da busca -> cadastros (dicts da lista de processos) cujo número bate com o pedido
    (mesmos dígitos; para número não CNJ, os dígitos do pedido dentro do número do cadastro)."""
    alvo = vios.digitos(numero)
    achados = []
    for p in lista_processos.processos_do_html(html, "", base):
        # a coluna traz "CNJ: <número> Outros: <número> ..." (às vezes com etiqueta de cliente antes)
        if len(alvo) == 20:
            bate = alvo in {vios.digitos(c) for c in vios.cnjs(p["numero"])}
        else:
            bate = bool(alvo) and alvo in vios.digitos(p["numero"])
        if bate and p["ci"] not in {a["ci"] for a in achados}:
            achados.append(p)
    return achados


# ---------------------------------------------------------------- quadro de comentários (puras)
class _LeitorComentarios(HTMLParser):
    """Linhas do <tbody> da tabela de comentários -> [[texto da célula, ...]], com <br>, <p> e <li>
    virando quebra de linha."""
    QUEBRA = {"br", "p", "li", "div", "ul", "ol"}
    IGNORAR = {"script", "style", "button"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.no_corpo = 0
        self.linhas, self.linha, self.celula = [], None, None
        self.ignorando = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORAR:
            self.ignorando += 1
        elif tag == "tbody":
            self.no_corpo += 1
        elif tag == "tr" and self.no_corpo:
            self.linha = []
        elif tag == "td" and self.linha is not None:
            self.celula = []
        elif tag in self.QUEBRA and self.celula is not None:
            self.celula.append("\n")

    def handle_endtag(self, tag):
        if tag in self.IGNORAR:
            self.ignorando = max(0, self.ignorando - 1)
        elif tag == "tbody":
            self.no_corpo = max(0, self.no_corpo - 1)
        elif tag == "td" and self.celula is not None and self.linha is not None:
            self.linha.append(_texto("".join(self.celula)))
            self.celula = None
        elif tag == "tr" and self.linha is not None:
            self.linhas.append(self.linha)
            self.linha = None
        elif tag in self.QUEBRA and self.celula is not None:
            self.celula.append("\n")

    def handle_data(self, dados):
        if self.celula is not None and not self.ignorando:
            self.celula.append(dados)


def _texto(t):
    t = t.replace(" ", " ")
    linhas = [re.sub(r"[ \t]+", " ", ln).strip() for ln in t.splitlines()]
    return re.sub(r"\n{2,}", "\n", "\n".join(ln for ln in linhas if ln)).strip()


def comentarios_do_html(html):
    """Pura: HTML da tabela de comentários -> [{"data": date, "data_br", "hora", "usuario", "texto"}],
    na ordem da tela. Linha sem data na 1ª coluna (ex.: "Nenhum registro") fica de fora."""
    leitor = _LeitorComentarios()
    leitor.feed(html or "")
    leitor.close()
    saida = []
    for cel in leitor.linhas:
        if len(cel) < 2:
            continue
        m = DATA_USUARIO.match(cel[0].replace("\n", " "))
        if not m:
            continue
        try:
            dia = datetime.strptime(m.group(1), "%d/%m/%Y").date()
        except ValueError:
            continue
        saida.append({"data": dia, "data_br": m.group(1), "hora": m.group(2) or "",
                      "usuario": m.group(3).strip(), "texto": cel[1]})
    saida.sort(key=lambda c: (c["data"], c["hora"]), reverse=True)
    return saida


def no_periodo(comentarios, hoje, dias):
    """Os comentários de (hoje - dias) até hoje, inclusive."""
    inicio = hoje - timedelta(days=dias)
    return [c for c in comentarios if inicio <= c["data"] <= hoje]


# ---------------------------------------------------------------- resultado (puras)
def resultado_do_cadastro(numero, cadastro, comentarios, hoje, dias):
    recentes = no_periodo(comentarios, hoje, dias)
    if recentes:
        situacao = OK
    elif comentarios:
        situacao = SEM_RECENTE
    else:
        situacao = SEM_NENHUM
    return {"numero_pedido": numero, "numero": numero, "numero_vios": cadastro.get("numero", ""), "ci": cadastro.get("ci", ""),
            "cliente": cadastro.get("cliente", ""), "situacao_vios": cadastro.get("situacao_vios", ""),
            "link": cadastro.get("link", ""), "resultado": situacao,
            "comentarios": [_publico(c) for c in recentes],
            "ultimo_fora": comentarios[0]["data_br"] if (comentarios and not recentes) else "",
            "erro": ""}


def resultado_sem_cadastro(numero, resultado, erro=""):
    return {"numero_pedido": numero, "numero": numero, "numero_vios": "", "ci": "", "cliente": "", "situacao_vios": "", "link": "",
            "resultado": resultado, "comentarios": [], "ultimo_fora": "", "erro": erro}


def _publico(c):
    return {"data": c["data_br"], "hora": c["hora"], "usuario": c["usuario"], "texto": c["texto"]}


def linhas_da_planilha(resultados):
    linhas = []
    for r in resultados:
        base = [r["numero"], r["ci"], r["cliente"], r["situacao_vios"]]
        if r["comentarios"]:
            for c in r["comentarios"]:
                linhas.append(base + [r["resultado"], c["data"], c["hora"], c["usuario"], c["texto"], "", r["link"]])
        else:
            resultado = r["resultado"] + (f": {r['erro']}" if r["erro"] else "")
            linhas.append(base + [resultado, "", "", "", "", r["ultimo_fora"], r["link"]])
    return linhas


def contar(resultados):
    """Contagem por número pedido (um número com vários cadastros conta uma vez): com comentário se
    algum cadastro tem; senão erro, se algum deu erro; senão não encontrado ou sem comentário."""
    por_numero = {}
    for r in resultados:
        por_numero.setdefault(r["numero_pedido"], []).append(r)
    conta = {"processos_pedidos": len(por_numero), "cadastros": sum(1 for r in resultados if r["ci"]),
             "com_comentario": 0, "sem_comentario_no_periodo": 0, "nao_encontrados": 0, "erros": 0,
             "comentarios": sum(len(r["comentarios"]) for r in resultados)}
    for lista in por_numero.values():
        estados = {r["resultado"] for r in lista}
        if OK in estados:
            conta["com_comentario"] += 1
        elif ERRO in estados:
            conta["erros"] += 1
        elif estados == {NAO_ACHADO}:
            conta["nao_encontrados"] += 1
        else:
            conta["sem_comentario_no_periodo"] += 1
    return conta


def gravar(resultados, pasta, dias, quando):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"comentarios-{dias}dias"
    caminho_csv, caminho_json = pasta / f"{nome}.csv", pasta / f"{nome}.json"
    with caminho_csv.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(CABECALHO)
        escritor.writerows(linhas_da_planilha(resultados))
    caminho_json.write_text(json.dumps({"gerado_em": quando.isoformat(timespec="seconds"), "dias": dias,
                                        "processos": resultados}, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in (caminho_csv, caminho_json):
        c.chmod(0o600)  # tem nomes de clientes e textos internos
    return caminho_csv, caminho_json


# ---------------------------------------------------------------- VIOS
_JS_TABELA = "const t = document.getElementById(arguments[0]); return t ? t.outerHTML : null;"


def ler_ficha(ctx, ci, timeout):
    """Abre a ficha do processo e devolve o HTML da tabela de comentários (espera o Vue desenhar e o
    número de linhas parar de mudar). Levanta ViosErro se o quadro não aparecer."""
    vios.abrir(ctx, URL_FICHA.format(ci=ci))
    fim = time.time() + timeout
    anterior, html = None, None
    while time.time() < fim:
        html = ctx.driver.execute_script(_JS_TABELA, TABELA)
        if html is not None:
            n = html.count("<tr")
            if n == anterior:
                return html
            anterior = n
        time.sleep(1.5)
    if html is not None:
        return html
    raise vios.ViosErro(f"o quadro de comentários não apareceu na ficha do CI {ci}")


def buscar_cadastros(ctx, numero):
    html = vios.buscar_get(ctx, URL_BUSCA.format(numero=quote(termo_de_busca(numero), safe="")))
    titulo = re.search(r"<title>([^<]*)</title>", html, re.I)
    if not (titulo and "Processos" in titulo.group(1)):
        raise vios.ViosErro("a busca não devolveu a tela de Processos")
    return cadastros_do_numero(html, numero, ctx.cfg.vios_base)


def _lista(ctx):
    if ctx.simulado:
        return ler_lista(simulado.ler(ctx, "lista.txt"))
    caminho = ctx.cfg.valor("ORELHA_COMENTARIOS_LISTA", LISTA_PADRAO, "caminho")
    if not Path(caminho).is_file():
        raise vios.ViosErro(f"lista de processos não encontrada: {caminho} (um número por linha; "
                            "ver ORELHA_COMENTARIOS_LISTA)")
    return ler_lista(Path(caminho).read_text(encoding="utf-8-sig"))


def executar(ctx):
    cfg = ctx.cfg
    dias = cfg.valor("ORELHA_COMENTARIOS_DIAS", DIAS, int)
    timeout = cfg.valor("ORELHA_COMENTARIOS_TIMEOUT", 40, int)
    numeros = _lista(ctx)
    ctx.emitir("fase", fase="lendo_comentarios")
    resultados, avisos = [], []
    if not ctx.simulado and numeros:
        vios.abrir(ctx, lista_processos.URL_LISTA)  # o fetch da busca roda de dentro de uma página do VIOS
    for i, numero in enumerate(numeros, 1):
        log.info("Comentários: %d/%d %s", i, len(numeros), numero)
        try:
            if ctx.simulado:
                cadastros = cadastros_do_numero(simulado.ler(ctx, "busca.html"), numero, cfg.vios_base)
            else:
                cadastros = buscar_cadastros(ctx, numero)
        except vios.BloqueioInativo:
            raise
        except Exception as e:  # noqa: BLE001 — um número com problema não para os outros
            log.warning("Comentários: busca de %s falhou: %s", numero, e)
            resultados.append(resultado_sem_cadastro(numero, ERRO, f"busca falhou ({str(e).splitlines()[0][:120]})"))
            continue
        if not cadastros:
            resultados.append(resultado_sem_cadastro(numero, NAO_ACHADO))
            continue
        for cad in cadastros:
            try:
                if ctx.simulado:
                    html = simulado.ler(ctx, f"ficha-{cad['ci']}.html")
                else:
                    html = ler_ficha(ctx, cad["ci"], timeout)
                resultados.append(resultado_do_cadastro(numero, cad, comentarios_do_html(html), ctx.hoje, dias))
            except vios.BloqueioInativo:
                raise
            except Exception as e:  # noqa: BLE001
                log.warning("Comentários: ficha do CI %s falhou: %s", cad["ci"], e)
                r = resultado_do_cadastro(numero, cad, [], ctx.hoje, dias)
                r.update(resultado=ERRO, erro=f"ficha não abriu ({str(e).splitlines()[0][:120]})")
                resultados.append(r)
        if len(cadastros) > 1:
            avisos.append(f"{numero}: {len(cadastros)} cadastros no VIOS (todos lidos)")
    conta = contar(resultados)
    caminho_csv, _ = gravar(resultados, ctx.saida, dias, datetime.now())
    log.info("Comentários: planilha em %s", caminho_csv)
    resumo = (f"{conta['processos_pedidos']} processos pedidos: {conta['com_comentario']} com comentário nos "
              f"últimos {dias} dias ({conta['comentarios']} comentários), {conta['sem_comentario_no_periodo']} sem, "
              f"{conta['nao_encontrados']} não encontrados, {conta['erros']} com erro. Planilha: {caminho_csv.name}")
    itens = []
    for r in resultados:
        if r["comentarios"]:
            ult = r["comentarios"][0]
            itens.append(Item(titulo=r["numero"], detalhe=f"{len(r['comentarios'])} comentário(s); último em "
                              f"{ult['data']} por {ult['usuario']}", link=r["link"], grupo=OK))
        else:
            detalhe = r["erro"] or (f"último comentário em {r['ultimo_fora']}" if r["ultimo_fora"] else "")
            nivel = "atencao" if r["resultado"] in (NAO_ACHADO, ERRO) else "info"
            itens.append(Item(titulo=r["numero"], detalhe=detalhe, nivel=nivel, link=r["link"], grupo=r["resultado"]))
    return Secao(chave="comentarios", titulo=TITULO, resumo=resumo, itens=itens, numeros=conta, avisos=avisos,
                 recolher=True)
