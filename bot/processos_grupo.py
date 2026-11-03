"""Lista de processos por Grupo Cliente (processos-lista.php) -> um .txt por grupo.

Só LÊ o VIOS: preenche o filtro "Grupo Cliente" e clica em Pesquisar. Nunca
usa os botões Apagar/Editar nem o "Processar" (ações em lote) da tela.
O .txt é a base para outra IA escrever um relatório para o cliente leigo.
O registro de cada processo (registro()) vai para o <GRUPO>.json, base do PDF.
Colunas e seletores: doc/vios-mapa-processos.md.
"""
import logging
import re
import unicodedata
from datetime import datetime

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.extracao import _limpar

log = logging.getLogger(__name__)

URL_LISTA = "https://roneely.vios.com.br/?pag=sys/processos/processos-lista.php&menu_lateral=true"
FILTRO_GRUPO = "pesq[clientes_grupos_id]"
# valor do "TODOS" no filtro Grupo Cliente (grupos_disponiveis pula "" e "0")
VALOR_TODOS = "0"
# a tela mostra 30 por padrão; 9999999 é a opção "sem limite" do pesq[limit]
LIMITE = "9999999"

LINHAS = (By.CSS_SELECTOR, "tr[id^='processos-lista_linha_']")

# coluna do VIOS (final do data-id da célula) -> campo
COLUNAS = {
    "processos_id": "ci",
    "pr_areas_nome": "area",
    "pr_processos_nome": "tipo_processo",
    "contratos_vis": "contrato",
    "processos_acoes_nome": "acao",
    "orgaos_uf": "uf",
    "orgaos_nome": "orgao",
    "vara": "vara",
    "tipo_vara": "tipo_vara",
    "advogado_nome": "advogado",
    "clientes_nome": "cliente",
    "cliente_escritorio": "polo_cliente",
    "data_acao": "data_acao",
    "valor_acao": "valor_acao",
    "objeto": "objeto",
    "obs_proc": "obs_proc",
}

# o VIOS mostra estes textos quando o campo está vazio
VAZIOS_VIOS = {"00/00/0000", "0,00", "R$ 0,00", "R$0,00"}
_DATA = re.compile(r"\d{2}/\d{2}/\d{4}")

# lê todas as linhas da lista numa chamada só (com 9999999 a lista pode ter milhares).
# Devolve o texto cru de cada célula; a limpeza é feita no Python (_item_de_bruto).
JS_LER_LINHAS = """
const saida = [];
for (const tr of document.querySelectorAll("tr[id^='processos-lista_linha_']")) {
  try {
    const celulas = {};
    let badges = [], vinculo = "";
    for (const td of tr.querySelectorAll("td[data-id]")) {
      // data-id = "processos-lista_linha_<n>_<coluna>"
      const id = td.getAttribute("data-id") || "";
      const i = id.indexOf("_linha_");
      if (i < 0) continue;
      const resto = id.slice(i + 7);
      const j = resto.indexOf("_");
      if (j < 0) continue;
      const col = resto.slice(j + 1);
      celulas[col] = td.innerText || "";
      if (col === "nro_proc_html") {
        badges = Array.from(td.querySelectorAll(".vj-badge")).map(b => b.innerText || "");
      }
      if (col === "sinal_vinculo_processo") {
        for (const el of td.querySelectorAll("[title], [data-original-title]")) {
          const t = (el.getAttribute("title") || el.getAttribute("data-original-title") || "").trim();
          if (t) { vinculo = t; break; }
        }
      }
    }
    saida.push({ci_linha: tr.getAttribute("data-processos_id") || "", celulas: celulas,
                 badges: badges, vinculo: vinculo});
  } catch (e) {
    saida.push({erro: String((e && e.message) || e)});
  }
}
return saida;
"""

VINCULO = {
    "PROCESSO PRINCIPAL": "processo principal",
    "APENSO": "apenso (processo ligado a outro processo principal)",
}


def _vazio_vios(texto):
    return "" if texto in VAZIOS_VIOS else texto


def _data(texto):
    """"03/11/2026" ou "" (o VIOS usa 00/00/0000 para data vazia)."""
    m = _DATA.search(texto or "")
    return "" if not m or m.group() == "00/00/0000" else m.group()


def _valor(texto):
    """"50.000,00" ou "" (o VIOS usa 0,00 para valor vazio)."""
    texto = (texto or "").replace("R$", "").strip()
    return "" if re.fullmatch(r"[0.,\s]*", texto) else texto


def _normal(nome):
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(nome.upper().split())


def grupos_disponiveis(driver, timeout):
    """{nome do grupo: valor} do filtro Grupo Cliente (sem o TODOS)."""
    driver.get(URL_LISTA)
    sel = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))
    return {
        _limpar(op.get_attribute("textContent")): op.get_attribute("value")
        for op in sel.find_elements(By.TAG_NAME, "option")
        if op.get_attribute("value") not in ("", "0")
    }


def pesquisar_grupo(driver, valor, timeout, encerrados=False):
    """Abre a lista, escolhe o grupo e clica em Pesquisar (pelo JavaScript, por causa do popup de recado).

    valor: valor do grupo no filtro (VALOR_TODOS = todos os grupos).
    encerrados: False = processos ativos (padrão da tela: "ativos" + "não migrados").
    True = processos encerrados: desmarca "ativos" e marca "encerrados" em
    pesq[filtros_multi][] ("não migrados" continua). As opções marcadas combinam com E
    (ativos + encerrados = 0 processos, conferido ao vivo em 03/11/2026), por isso
    ativos e encerrados são duas pesquisas (ver _salvar_grupo no relatorio_processos.py).
    """
    driver.get(URL_LISTA)
    sel = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))
    erro = driver.execute_script(
        """
        const [sel, valor, limite, encerrados] = arguments;
        const form = sel.form;
        const botao = form.querySelector("#Pesq");
        if (!botao) return "botão Pesquisar não encontrado no formulário do filtro";
        sel.value = valor;
        // valor que não existe no select deixa o value vazio: melhor parar que pesquisar outro grupo
        if (sel.value !== valor) return "Grupo Cliente com valor " + valor + " não existe no filtro";
        const lim = form.elements["pesq[limit]"];
        // sem o campo a tela mostra só 30 processos: melhor parar que gerar relatório cortado
        if (!lim) return "campo pesq[limit] não encontrado no formulário (a lista viria cortada)";
        lim.value = limite;
        if (lim.value !== limite) return "opção " + limite + " não existe em pesq[limit] (a lista viria cortada)";
        const multi = form.elements["pesq[filtros_multi][]"];
        const opcoes = (multi && multi.options) ? Array.from(multi.options) : [];
        const ativos = opcoes.find(o => o.value === "ativos");
        const fechados = opcoes.find(o => o.value === "encerrados");
        if (encerrados) {
          // as opções combinam com E: "encerrados" só dá resultado sem "ativos"
          if (!fechados) return "opção encerrados não encontrada em pesq[filtros_multi][]";
          if (!ativos) return "opção ativos não encontrada em pesq[filtros_multi][]";
          ativos.selected = false;
          fechados.selected = true;
        } else if (ativos) {
          // garante o padrão (ativos, sem encerrados) mesmo se a tela lembrar outra pesquisa
          ativos.selected = true;
          if (fechados) fechados.selected = false;
        }
        if (multi) {
          try {
            if (window.jQuery && window.jQuery(multi).selectpicker) window.jQuery(multi).selectpicker("refresh");
          } catch (e) { /* só a parte visual */ }
        }
        form.requestSubmit(botao);  // o mesmo que clicar em Pesquisar
        return "";
        """,
        sel,
        valor,
        LIMITE,
        bool(encerrados),
    )
    if erro:
        raise RuntimeError(erro)
    WebDriverWait(driver, timeout).until(EC.staleness_of(sel))
    WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, FILTRO_GRUPO)))


def _bruto_da_linha(tr):
    """Mesmo resultado do JS_LER_LINHAS, lendo elemento por elemento (mais lento; reserva)."""
    celulas = {}
    for td in tr.find_elements(By.CSS_SELECTOR, "td[data-id]"):
        # data-id = "processos-lista_linha_<n>_<coluna>"
        celulas[td.get_attribute("data-id").split("_linha_", 1)[1].split("_", 1)[1]] = td
    badges = []
    if "nro_proc_html" in celulas:
        badges = [b.get_attribute("innerText") or "" for b in celulas["nro_proc_html"].find_elements(By.CSS_SELECTOR, ".vj-badge")]
    vinculo = ""
    sinal = celulas.get("sinal_vinculo_processo")
    if sinal is not None:
        # o tooltip do bootstrap move o title para data-original-title
        for el in sinal.find_elements(By.CSS_SELECTOR, "[title], [data-original-title]"):
            vinculo = (el.get_attribute("title") or el.get_attribute("data-original-title") or "").strip()
            if vinculo:
                break
    return {
        "ci_linha": tr.get_attribute("data-processos_id") or "",
        "celulas": {col: td.get_attribute("innerText") or "" for col, td in celulas.items()},
        "badges": badges,
        "vinculo": vinculo,
    }


def _item_de_bruto(bruto):
    """Texto cru das células -> item do processo (campos do contrato 1 sem a ficha)."""
    if bruto.get("erro"):
        raise RuntimeError(bruto["erro"])
    celulas = bruto.get("celulas") or {}
    item = {campo: _vazio_vios(_limpar(celulas.get(col) or "")) for col, campo in COLUNAS.items()}
    item["ci"] = item["ci"] or _limpar(bruto.get("ci_linha") or "")
    item["data_acao"] = _data(item["data_acao"])
    item["valor_acao"] = _valor(item["valor_acao"])

    # Número: etiquetas (ex.: "Cliente OURO") + "CNJ: 0000..." ou "Outros: ..."
    texto = _limpar(celulas.get("nro_proc_html") or "")
    for e in bruto.get("badges") or []:
        e = _limpar(e)
        if e:
            texto = texto.replace(e, "", 1)
    item["numero"] = " ".join(texto.split())

    # partes vêm uma por linha (<br>): "Autor: FULANO"
    def linhas(col):
        return [_limpar(t) for t in (celulas.get(col) or "").split("\n") if t.strip()]

    item["parte_ativa"] = linhas("ativahtml")
    item["parte_passiva"] = linhas("passivahtml")
    vinculo = (bruto.get("vinculo") or "").strip()
    item["vinculo"] = VINCULO.get(vinculo.upper(), vinculo.lower())
    return item


def _ler_linha(tr):
    return _item_de_bruto(_bruto_da_linha(tr))


def _brutos(driver, trs):
    """Linhas cruas pelo JS (uma chamada). Se o JS falhar, lê elemento por elemento."""
    try:
        brutos = driver.execute_script(JS_LER_LINHAS)
        if isinstance(brutos, list):
            return brutos
        log.warning("Leitura rápida da lista devolveu %r: lendo linha por linha", type(brutos).__name__)
    except Exception as e:
        log.warning("Leitura rápida da lista falhou (%s): lendo linha por linha", getattr(e, "msg", None) or e)
    saida = []
    for tr in trs:
        try:
            saida.append(_bruto_da_linha(tr))
        except Exception as e:
            saida.append({"erro": getattr(e, "msg", None) or str(e) or type(e).__name__})
    return saida


def ler_processos(driver, timeout):
    """Lê a tabela de resultado e devolve (itens, qtd_erros)."""
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located(LINHAS))
    except TimeoutException:
        return [], 0
    trs = driver.find_elements(*LINHAS)
    brutos = _brutos(driver, trs)

    # o rodapé "Total (N)" conta as linhas mostradas na página (não o total do filtro):
    # se não bate, a leitura da página ficou incompleta
    total = driver.find_elements(By.CSS_SELECTOR, ".geratabela_total_quantidade_original")
    if total:
        n = re.search(r"\d+", total[0].get_attribute("textContent") or "")
        if n and int(n.group()) != len(brutos):
            log.warning("Rodapé mostra %s linhas, mas %d foram lidas: leitura incompleta da página",
                        n.group(), len(brutos))

    itens, erros = [], 0
    for n, bruto in enumerate(brutos, 1):
        try:
            itens.append(_item_de_bruto(bruto))
        except Exception as e:
            erros += 1
            log.warning("Linha %d pulada: %s", n, getattr(e, "msg", None) or e)
    return itens, erros


# Sufixos societários e de porte. Não fazem parte do "nome" para comparar.
# Estes saem em qualquer lugar do nome (não são nome de gente).
SUFIXOS_QUALQUER_LUGAR = {"LTDA", "LIMITADA", "EIRELI", "EPP", "MEI", "MATRIZ", "FILIAL"}
# Estes só saem no fim, porque podem ser parte de um nome (ex.: "Sá" vira "SA").
SUFIXOS_SO_NO_FIM = {"SA", "ME", "CIA", "COMPANHIA"}
# Expressões de mais de uma palavra, também só no fim.
SUFIXOS_FRASE_NO_FIM = (
    ("SOCIEDADE", "ANONIMA"),
    ("EM", "RECUPERACAO", "JUDICIAL"),
    ("S", "A"),  # "S A" com espaço
)

_PARENTESES = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_CNPJ = re.compile(r"\d{2}\.?\d{3}\.?\d{3}\s*/?\s*\d{4}\s*-?\s*\d{2}")
_CPF = re.compile(r"\d{3}\.?\d{3}\.?\d{3}\s*-?\s*\d{2}")
_ROTULO_DOC = re.compile(r"\b(?:CPF|CNPJ)(?:\s*/\s*MF)?\b\s*(?:N[º°O]\.?)?\s*:?", re.IGNORECASE)


def _sem_sufixos(palavras):
    palavras = [p for p in palavras if p not in SUFIXOS_QUALQUER_LUGAR]
    mudou = True
    while mudou and palavras:
        mudou = False
        if palavras[-1] in SUFIXOS_SO_NO_FIM:
            palavras = palavras[:-1]
            mudou = True
            continue
        for frase in SUFIXOS_FRASE_NO_FIM:
            fim = tuple(_normal(p) for p in palavras[-len(frase):])  # "ANÔNIMA" = "ANONIMA"
            if len(palavras) > len(frase) and fim == frase:
                palavras = palavras[:-len(frase)]
                mudou = True
                break
    return palavras


def _nome_comparavel(texto, tirar_rotulo=False):
    """Nome pronto para comparar: sem rótulo, CPF/CNPJ, parênteses, pontuação e sufixos.

    Ex.: "Reclamado: 3A Frios Ltda. (CNPJ 12.345.678/0001-90)" -> "3A FRIOS".
    """
    texto = _PARENTESES.sub(" ", texto or "")
    # CPF/CNPJ sai antes do rótulo, para o ":" de "CNPJ:" não ser lido como rótulo
    texto = _ROTULO_DOC.sub(" ", texto)
    texto = _CNPJ.sub(" ", texto)
    texto = _CPF.sub(" ", texto)
    if tirar_rotulo and ":" in texto:
        # "Autor: FULANO", "Reclamado: FULANO" -> "FULANO"
        texto = texto.split(":", 1)[1]
    texto = texto.upper()
    # abreviação com ponto ou barra: "S.A." / "S/A" -> "SA", "M.E." -> "ME"
    texto = re.sub(r"\b(\w)\.", r"\1", texto)
    texto = re.sub(r"\b(\w)\s*/\s*(\w)\b", r"\1\2", texto)
    # o resto da pontuação (hífen, vírgula, &, ponto final) vira espaço
    texto = re.sub(r"[^\w]+|_", " ", texto)
    # acento sai só agora: "SÁ" (sobrenome) não é confundido com "SA" (S.A.)
    palavras = _sem_sufixos(texto.split())
    palavras = [_normal(p) for p in palavras]
    return " ".join(p for p in palavras if p)


AUTOR = "autor (o cliente entrou com a ação)"
REU = "réu (o cliente está sendo processado)"

# coluna cliente_escritorio da lista ("Polo do cliente" na ficha)
POLOS = {
    "PARTE ATIVA": AUTOR,
    "POLO ATIVO": AUTOR,
    "ATIVO": AUTOR,
    "ATIVA": AUTOR,
    "PARTE PASSIVA": REU,
    "POLO PASSIVO": REU,
    "PASSIVO": REU,
    "PASSIVA": REU,
}


def posicao_cliente(item):
    """Se o cliente é quem entrou com a ação (autor) ou quem está sendo processado (réu).

    Primeiro vale o polo do cliente cadastrado no VIOS (polo_cliente: "Parte
    Ativa" / "Parte Passiva"). Só se ele vier vazio ou desconhecido (ex.:
    "Terceiro") o robô compara os nomes.

    Regra dos nomes: o nome do cliente tem que ser IGUAL ao nome de uma parte depois de
    limpar os dois (rótulo "Autor:", CPF/CNPJ, parênteses, pontuação, LTDA, ME,
    S/A etc.). Não aceita nome parecido nem pedaço do nome: "JOSE SILVA" não casa
    com "JOSE SILVA SANTOS", e "A AFONSO LINHARES" não casa com "ANTONIO AFONSO
    LINHARES". Na dúvida fica "não identificada", porque o relatório vai para o
    cliente e um autor/réu errado é pior que nenhum.
    """
    polo = POLOS.get(_normal(item.get("polo_cliente") or ""))
    if polo:
        return polo
    cliente = _nome_comparavel(item.get("cliente", ""))
    if not cliente:
        return "não identificada"

    def nomes(partes):
        return {_nome_comparavel(p, tirar_rotulo=True) for p in partes or []}

    autor = cliente in nomes(item.get("parte_ativa"))
    reu = cliente in nomes(item.get("parte_passiva"))
    if autor and reu:
        return "aparece como autor e como réu (conferir no VIOS)"
    if autor:
        return AUTOR
    if reu:
        return REU
    return "não identificada (o cliente não aparece nas partes da lista)"


def _contagem(itens, campo):
    contagem = {}
    for it in itens:
        chave = it.get(campo) or "não informado"
        contagem[chave] = contagem.get(chave, 0) + 1
    return sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))


def ordenar(itens):
    """Ordem do .txt e do .json: cliente, área, CI."""
    return sorted(itens, key=lambda it: (it.get("cliente", ""), it.get("area", ""), it.get("ci", "")))


def _ficha_ok(it):
    ficha = it.get("ficha")
    return ficha if isinstance(ficha, dict) and ficha.get("ok") else {}


def montar_txt(grupo, itens, agora=None, situacao="processos ativos"):
    agora = agora or datetime.now()
    for it in itens:
        it["posicao"] = posicao_cliente(it)

    def ou_nada(valor):
        return valor or "não informado"

    linhas = [
        f"RELATÓRIO DE PROCESSOS — GRUPO {grupo}",
        f"Dados do sistema VIOS em {agora:%d/%m/%Y às %H:%M} ({situacao})",
        f"Total de processos: {len(itens)}",
        "",
        "=" * 70,
        "RESUMO",
        "=" * 70,
    ]
    resumos = [("Por empresa/pessoa do grupo", "cliente"), ("Por área", "area"), ("Posição do cliente", "posicao")]
    if any(it.get("situacao") == "encerrado" for it in itens):
        resumos.insert(0, ("Por situação", "situacao"))
    for titulo, campo in resumos:
        linhas.append(f"{titulo}:")
        linhas += [f"  - {chave}: {qtd}" for chave, qtd in _contagem(itens, campo)]
        linhas.append("")

    ordenados = ordenar(itens)
    cliente_atual = None
    for n, it in enumerate(ordenados, 1):
        if it.get("cliente") != cliente_atual:
            cliente_atual = it.get("cliente")
            linhas += ["=" * 70, f"CLIENTE: {ou_nada(cliente_atual)}", "=" * 70, ""]
        linhas += [
            f"PROCESSO {n} de {len(itens)}",
            f"  Número do processo: {ou_nada(it.get('numero'))}",
            f"  Situação: {it.get('situacao') or 'ativo'}",
            f"  Área: {ou_nada(it.get('area'))}",
            f"  Tipo de processo: {ou_nada(it.get('tipo_processo'))}",
            f"  Tipo de ação: {ou_nada(it.get('acao'))}",
            f"  Assunto (objeto): {ou_nada(it.get('objeto'))}",
            f"  Data da distribuição: {ou_nada(it.get('data_acao'))}",
            f"  Valor da ação: {('R$ ' + it['valor_acao']) if it.get('valor_acao') else 'não informado'}",
            f"  Onde tramita: {ou_nada(it.get('orgao'))}" + (f" ({it['uf']})" if it.get("uf") else ""),
            f"  Vara: {ou_nada(' - '.join(v for v in (it.get('vara'), it.get('tipo_vara')) if v))}",
            f"  Cidade / UF: {ou_nada(_ficha_ok(it).get('cidade_uf'))}",
            f"  Fase: {ou_nada(_ficha_ok(it).get('fase'))}",
            f"  Quem entrou com a ação (parte ativa): {ou_nada('; '.join(it['parte_ativa']))}",
            f"  Contra quem (parte passiva): {ou_nada('; '.join(it['parte_passiva']))}",
            f"  Posição do cliente: {it['posicao']}",
            f"  Advogado responsável: {ou_nada(it.get('advogado'))}",
            f"  Vínculo: {ou_nada(it.get('vinculo'))}",
            f"  Contrato: {ou_nada(it.get('contrato'))}",
            f"  Código interno no VIOS (CI): {ou_nada(it.get('ci'))}",
            "",
        ]
    return "\n".join(linhas)


def nome_arquivo(grupo):
    # caracteres que o Windows não aceita em nome de arquivo
    return re.sub(r'[\\/:*?"<>|]', "-", grupo).strip() + ".txt"


def nome_json(grupo):
    """<GRUPO>.json, ao lado do <GRUPO>.txt."""
    return nome_arquivo(grupo)[:-len(".txt")] + ".json"


SEM_FICHA = {"ok": False, "erro": "ficha não lida"}


def registro(grupo, it):
    """Registro do processo no <GRUPO>.json (contrato 1). obs_proc é interno: não vai para o cliente."""
    return {
        "grupo": grupo,
        "ci": it.get("ci") or "",
        "numero": it.get("numero") or "",
        "parte_ativa": list(it.get("parte_ativa") or []),
        "parte_passiva": list(it.get("parte_passiva") or []),
        "cliente": it.get("cliente") or "",
        "polo_cliente": it.get("polo_cliente") or "",
        "area": it.get("area") or "",
        "tipo_processo": it.get("tipo_processo") or "",
        "acao": it.get("acao") or "",
        "orgao": it.get("orgao") or "",
        "uf": it.get("uf") or "",
        "vara": it.get("vara") or "",
        "tipo_vara": it.get("tipo_vara") or "",
        "data_acao": _data(it.get("data_acao") or ""),
        "valor_acao": _valor(it.get("valor_acao") or ""),
        "objeto": it.get("objeto") or "",
        "obs_proc": it.get("obs_proc") or "",
        "posicao": it.get("posicao") or posicao_cliente(it),
        # "ativo" ou "encerrado" (encerrados só com --encerrados)
        "situacao": it.get("situacao") or "ativo",
        "ficha": it.get("ficha") if isinstance(it.get("ficha"), dict) else dict(SEM_FICHA),
    }


def montar_json(grupo, itens):
    """Lista de registros (contrato 1), na mesma ordem do .txt."""
    return [registro(grupo, it) for it in ordenar(itens)]
