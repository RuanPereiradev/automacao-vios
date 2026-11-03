"""Os 13 campos do relatório do cliente (PDF por Grupo Cliente), a partir dos registros capturados no VIOS.

Entrada: lista de registros do <GRUPO>.json (relatorio_processos.py), cada um com a ficha do processo.
Saída: montar_linhas() -> um dict por processo com as chaves de COLUNAS (todas str), na ordem do PDF.

Tudo o que vai para o cliente passa por sanitizar(): sem links, senhas e IDs de reunião, e-mails,
telefones, nomes da equipe e textos automáticos do VIOS. obs_proc (observação interna) nunca é lido.

Com IA (opcional): resumo, pendência e financeira são escritos pela IA, uma chamada por bloco de
processos, só com os dados já sanitizados. Falha da IA: o bloco fica sem IA e vira observação.
"""
import json
import logging
import re
import unicodedata
from datetime import date, datetime

from bot.custo import CARACTERES_POR_TOKEN, LimiteGasto

log = logging.getLogger(__name__)

# ordem e títulos exatos das colunas do relatório
COLUNAS = [
    ("id_extracao", "ID da extração"),
    ("numero", "Número do processo"),
    ("parte_ativa", "Parte ativa"),
    ("parte_passiva", "Parte passiva"),
    ("tipo_processo", "Tipo de processo"),
    ("orgao", "Órgão"),
    ("data_distribuicao", "Data da distribuição"),
    ("valor_acao", "Valor da ação"),
    ("cidade_uf", "Cidade/UF"),
    ("ultima_movimentacao", "Última movimentação"),
    ("resumo", "Resumo do caso"),
    ("pendencia", "PENDÊNCIA"),
    ("financeira", "Financeira"),
]
CHAVES = [chave for chave, _ in COLUNAS]

NAO_INFORMADO = "não informado"
SEM_PENDENCIA = "Nenhuma pendência registrada"
# processo encerrado (relatorio_processos.py --encerrados): vai junto do número, no PDF
SUFIXO_ENCERRADO = " (encerrado)"
# avisos do PDF: frases fixas, sem o motivo técnico (que fica no log)
AVISO_SEM_IA = "Resumo, pendência e financeira montados só com os dados do cadastro (sem IA)."
AVISO_SEM_IA_PARCIAL = "Resumo, pendência e financeira de {n} processo(s) montados só com o cadastro."
SEM_MOVIMENTACAO = "Nenhuma movimentação registrada"
FINANCEIRA_PADRAO = "não identificada"
LIMITE_MOVIMENTACAO = 300
# processos por chamada da IA (grupo grande vai em vários blocos)
BLOCO_IA = 25
# tokens de saída estimados por bloco (para o teto LLM_LIMITE_US)
SAIDA_BASE = 300
SAIDA_POR_PROCESSO = 250

PROMPT_IA = """\
Você escreve campos de um relatório de processos judiciais para o cliente leigo de um escritório
de advocacia. Recebe, em JSON, uma lista de processos de um Grupo Cliente, tirada do sistema do
escritório (VIOS): cadastro, tarefas da equipe e comentários (já sem links, senhas e nomes da equipe).

Para CADA processo, devolva:
- resumo: 1 a 3 frases simples, sem juridiquês: do que se trata, quem processa quem e em que pé está.
- pendencia: o que falta fazer ou o que se espera agora (tarefas abertas, prazos, audiência marcada),
  com a data quando houver. Sem nada pendente nos dados: "Nenhuma pendência registrada".
- financeira: valores, acordos, pagamentos, depósitos, bloqueios ou condenações CITADOS nos textos.
  Se não houver nenhum, escreva exatamente "não identificada".

REGRAS
1. Use SOMENTE o que está nos dados. NUNCA invente andamento, decisão, valor, data, prazo ou chance de êxito.
2. Não escreva links, senhas, e-mails, telefones nem nomes de pessoas da equipe do escritório.
3. Não cite códigos internos do sistema (CI).
4. Devolva um item para cada processo recebido, com o mesmo id_extracao.

Responda só com o JSON pedido.
"""

SCHEMA_IA = {
    "type": "object",
    "properties": {
        "processos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id_extracao": {"type": "integer"},
                    "resumo": {"type": "string"},
                    "pendencia": {"type": "string"},
                    "financeira": {"type": "string"},
                },
                "required": ["id_extracao", "resumo", "pendencia", "financeira"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["processos"],
    "additionalProperties": False,
}


# ---- sanitização (o texto vai para o cliente) ----

_I = re.IGNORECASE
# trechos automáticos do VIOS: saem inteiros
_TIPO_ORIGEM = re.compile(r"Descri[çc][ãa]o do tipo da tarefa de origem\s*:.*", _I | re.S)
_ENCERRADA_ARQUIVO = re.compile(r"Tarefa encerrada ao enviar o\(?s?\)? arquivo\(?s?\)?\s*:[^\n]*", _I)
_EQUIPE = re.compile(r"\b(?:Respons[áa]veis?|Concluiu a tarefa|Envolvidos)\s*:[^\n]*", _I)
_LINK_CHAT = re.compile(r"LINK\s+DO\s+CHAT\s*:?\s*\S*", _I)
_URL = re.compile(r"(?:https?://|www\.)\S+", _I)
# domínio solto, sem http (ex.: zoom.us/j/123, call.lifesizecloud.com/456, pje.tjce.jus.br, bit.ly/3ab)
_DOMINIO = re.compile(
    r"\b((?:[a-z0-9-]+\.)+)(com|net|org|us|io|me|app|link|gov|jus|adv|ly|gle|gl|co|to|br)(?:\.br)?\b(/\S*)?", _I)
# serviços de reunião, chat e link curto: sai mesmo sem caminho ("zoom.us", "bit.ly")
_HOST_LINK = re.compile(r"(?:^|\.)(?:zoom|lifesize\w*|teams|meet|webex|whereby|jitsi|bit|forms|wa|chat)\.$", _I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# ID, senha e código de reunião: rótulo + valor ("ID da reunião: 123 456 7890", "SENHA: ab12", "pwd=xyz").
# senha/código só com ":" ou "=" depois, para não cortar frase comum ("a senha foi enviada")
_REUNIAO_ID = re.compile(
    r"\b(?:id\s+da\s+(?:reuni[ãa]o|sala|confer[êe]ncia)|meeting\s+id)\s*[:=]?\s*[^\s,;]+(?:[ \t]+\d+)*"
    r"|\bextens[ãa]o\s*[:=]?\s*\d{3,}", _I)
_SENHA = re.compile(
    r"\b(?:senha(?:\s+de\s+acesso|\s+da\s+(?:reuni[ãa]o|sala|audi[êe]ncia))?|passcode|password|pwd"
    r"|c[óo]digo\s+de\s+acesso)\s*[:=]\s*[^\s,;]+"
    # "senha 445566": sem ":" só sai se vier número logo depois
    r"|\bsenha\s+(?:[ée]\s+)?\d{3,}\b", _I)
# "Link do zoom:", "link da audiência:" (o link já saiu)
_ROTULO_LINK = re.compile(r"\blink\b[^:\n]{0,40}:", _I)
# telefone: "(85) 98765-4321", "3333-4444", "+55 85987654321", "whatsapp 85 9 9876 5432" e o número
# solto com DDD ("85988887777", também tira CPF sem máscara). Não pega período de anos ("2019-2021")
# nem número colado em ponto, barra ou hífen (processo CNJ, datas)
_TELEFONE = re.compile(
    r"(?:\+\s?55\s*)?(?:\(\s?\d{2}\s?\)\s*|(?<![\d/.-])\d{2}\s+)?(?<![\d/.])(?:9\s?)?"
    r"(?!(?:19|20)\d{2}-(?:19|20)\d{2}\b)\d{4}-\d{4}\b(?![.\d/-])"
    r"|\(\s?\d{2}\s?\)\s*9?\d{8}\b"
    r"|\+\s?55\s*\d{10,11}\b"
    r"|(?<![\d/.,-])\b\d{2}\s?\d{8,9}\b(?![.,/-]?\d)"
    r"|\b(?:whats(?:app)?|zap|tel(?:efone)?|fone|cel(?:ular)?)\s*[:.]?\s*[\d()\s+-]{8,}\d", _I)


def _tirar_dominio(m):
    """Domínio solto sai se tiver caminho, subdomínio (2+ partes) ou for de reunião/link curto.

    "Americanas.com S/A" fica (nome de empresa); "zoom.us/j/1" e "pje.tjce.jus.br" saem."""
    nomes, caminho = m.group(1), m.group(3)
    if caminho or nomes.count(".") >= 2 or _HOST_LINK.search(nomes):
        return " "
    return m.group(0)


def sanitizar(texto, nomes_equipe=()):
    """Tira do texto o que não pode ir para o cliente. Devolve o texto limpo (pode ficar vazio)."""
    texto = str(texto or "")
    for regra in (_TIPO_ORIGEM, _ENCERRADA_ARQUIVO, _EQUIPE, _LINK_CHAT, _URL, _EMAIL):
        texto = regra.sub(" ", texto)
    texto = _DOMINIO.sub(_tirar_dominio, texto)
    for regra in (_REUNIAO_ID, _SENHA, _TELEFONE, _ROTULO_LINK):
        texto = regra.sub(" ", texto)
    for nome in nomes_equipe:
        nome = " ".join(str(nome or "").split())
        # só nome com 2 palavras ou mais: um primeiro nome solto pode ser o nome de uma parte
        if len(nome.split()) >= 2:
            texto = re.sub(r"(?<!\w)" + re.escape(nome) + r"(?!\w)", "[equipe]", texto, flags=_I)
    return _arrumar(texto)


def _arrumar(texto):
    """Espaços e pontuação que sobram depois dos cortes."""
    texto = re.sub(r"[ \t\r\f\v]+", " ", texto)
    texto = re.sub(r"\s*\n\s*", "\n", texto)
    texto = re.sub(r"\(\s*\)|\[\s*\]", " ", texto)
    texto = re.sub(r" +([,.;:!?])", r"\1", texto)
    texto = re.sub(r"([,;:])(?:\s*[,;:])+", r"\1", texto)
    texto = re.sub(r"[,;:]+\s*([.!?])", r"\1", texto)
    texto = re.sub(r"\n{2,}", "\n", texto)
    texto = re.sub(r" {2,}", " ", texto)
    return texto.strip(" \n-–—:;,|")


def _uma_linha(texto):
    return " ".join(str(texto or "").split())


def cortar(texto, limite=LIMITE_MOVIMENTACAO):
    """Corta no limite, sem quebrar palavra, com "..." no fim."""
    texto = _uma_linha(texto)
    if len(texto) <= limite:
        return texto
    corte = texto[:limite - 3].rsplit(" ", 1)[0] or texto[:limite - 3]
    return corte.rstrip(" ,;:-") + "..."


# ---- campos simples ----

_DATA_BR = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATA_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def data_br(texto):
    """Primeira data do texto em DD/MM/AAAA ("" se não houver ou se for 00/00/0000)."""
    texto = str(texto or "")
    m = _DATA_BR.search(texto)
    if m:
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = _DATA_ISO.search(texto)
        if not m:
            return ""
        ano, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(ano, mes, dia).strftime("%d/%m/%Y")
    except ValueError:
        return ""


def _para_data(texto):
    br = data_br(texto)
    return datetime.strptime(br, "%d/%m/%Y").date() if br else None


def valor_br(texto):
    """'50.000,00' -> 'R$ 50.000,00'. Vazio ou zero -> ''."""
    texto = _uma_linha(texto).replace("R$", "").strip()
    if not texto or not re.search(r"\d", texto) or not re.search(r"[1-9]", texto):
        return ""
    return "R$ " + texto


# rótulos de parte que aparecem colados no nome (lista: "Autor: X"; ficha: "Contrário: A Contrário: B")
_ROTULOS_PARTE = (
    "Autora?", "Réu", "Ré", "Reu", "Contrári[oa]", "Contrario", "Reclamante", "Reclamad[oa]", "Requerente",
    "Requerid[oa]", "Exequente", "Executad[oa]", "Embargante", "Embargad[oa]", "Impetrante", "Impetrad[oa]",
    "Apelante", "Apelad[oa]", "Agravante", "Agravad[oa]", "Recorrente", "Recorrid[oa]", "Interessad[oa]",
    "Terceir[oa]", "Promovente", "Promovid[oa]", "Denunciante", "Denunciad[oa]", "Querelante", "Querelad[oa]",
    "Litisconsorte", "Assistente", "Parte", "Cliente", "Credor[a]?", "Devedor[a]?", "Paciente", "Vítima",
    "Investigad[oa]", "Acusad[oa]", "Notificante", "Notificad[oa]", "Representante", "Representad[oa]",
)
_ROTULO_PARTE = re.compile(r"(?:^|(?<=\s))(?:%s)(?:\(a\))?\s*:\s*" % "|".join(_ROTULOS_PARTE), _I)
# rótulo genérico no começo ("Polo ativo: X"), só letras
_ROTULO_INICIO = re.compile(r"^[^\W\d_][^\W\d_ ()/.]*(?:\s+[^\W\d_()/.]+){0,3}\s*:\s*")


def nomes_partes(partes):
    """Lista de partes (ou texto da ficha) -> 'NOME A, NOME B', sem rótulos e sem repetir."""
    if isinstance(partes, str):
        partes = [partes]
    nomes = []
    for parte in partes or []:
        for pedaco in _ROTULO_PARTE.split(_uma_linha(parte)):
            pedaco = _ROTULO_INICIO.sub("", pedaco.strip()).strip(" ,;")
            if pedaco and pedaco.casefold() not in [n.casefold() for n in nomes]:
                nomes.append(pedaco)
    return ", ".join(nomes)


def _campo_ficha(ficha, *rotulos):
    campos = ficha.get("campos") or {}
    for rotulo in rotulos:
        valor = _uma_linha(campos.get(rotulo, ""))
        if valor:
            return valor
    return ""


def encerrado(reg):
    """True se o registro veio da pesquisa de encerrados (chave "situacao" do .json)."""
    return isinstance(reg, dict) and str(reg.get("situacao") or "").strip().lower() == "encerrado"


def _numero(reg, ficha):
    numero = _uma_linha(reg.get("numero")) or _campo_ficha(ficha, "N.° CNJ", "N.º CNJ", "Nº CNJ")
    numero = re.sub(r"^CNJ\s*:\s*", "", numero, flags=_I)
    numero = numero or NAO_INFORMADO
    return numero + SUFIXO_ENCERRADO if encerrado(reg) else numero


def _orgao(reg, ficha):
    orgao = _uma_linha(reg.get("orgao")) or _campo_ficha(ficha, "Comarcas / Tribunais / Órgãos adm.")
    vara = _uma_linha(reg.get("vara")) or _campo_ficha(ficha, "Órgão julgador (Vara/camara)")
    if orgao and vara and vara.casefold() not in orgao.casefold():
        return f"{orgao} - {vara}"
    return orgao or vara or NAO_INFORMADO


# ---- tarefas: última movimentação e pendência ----

def _cancelada(tarefa):
    return "CANCELAD" in _uma_linha(tarefa.get("situacao")).upper()


def _ci_num(tarefa):
    m = re.search(r"\d+", str(tarefa.get("ci") or ""))
    return int(m.group()) if m else 0


def ultima_movimentacao(tarefas, hoje=None, nomes_equipe=()):
    """A tarefa CONCLUÍDA e não cancelada mais recente: "DD/MM/AAAA - TIPO - texto".

    Regra: só tarefa com "Concluída em" é movimentação (algo que de fato aconteceu); a data é a
    da conclusão. Tarefa aberta (com prazo vencido ou futuro) não conta: vai para a PENDÊNCIA.
    Empate de data: CI maior (mais nova). Nenhuma concluída: "Nenhuma movimentação registrada".
    Texto: os comentários da tarefa (conclusão da equipe) ou, sem eles, a descrição.
    """
    hoje = hoje or date.today()
    concluidas = [(d, _ci_num(t), t) for t in tarefas or [] if not _cancelada(t)
                  for d in [_para_data(t.get("concluida_em"))] if d and d <= hoje]
    if not concluidas:
        return SEM_MOVIMENTACAO
    quando, _, tarefa = max(concluidas, key=lambda x: (x[0], x[1]))
    data_txt = quando.strftime("%d/%m/%Y")
    tipo = sanitizar(_uma_linha(tarefa.get("tipo")), nomes_equipe)
    texto = sanitizar(tarefa.get("comentarios"), nomes_equipe) or sanitizar(tarefa.get("descricao"), nomes_equipe)
    partes = [p for p in (data_txt, tipo, _uma_linha(texto)) if p]
    return cortar(" - ".join(partes)) if partes else SEM_MOVIMENTACAO


def tarefas_abertas(tarefas):
    """Tarefas sem "Concluída em" e não canceladas, da data mais próxima para a mais distante."""
    abertas = [t for t in tarefas or [] if not _cancelada(t) and not data_br(t.get("concluida_em"))]

    def chave(t):
        d = _para_data(t.get("para_conclusao")) or _para_data(t.get("limite"))
        return (d is None, d or date.min, _ci_num(t))
    return sorted(abertas, key=chave)


def pendencia_sem_ia(tarefas, nomes_equipe=()):
    """'TIPO até DD/MM/AAAA; OUTRO TIPO até ...' ou 'Nenhuma pendência registrada'."""
    itens = []
    for t in tarefas_abertas(tarefas):
        tipo = sanitizar(_uma_linha(t.get("tipo")), nomes_equipe) or "Tarefa"
        prazo = data_br(t.get("para_conclusao")) or data_br(t.get("limite"))
        item = f"{tipo} até {prazo}" if prazo else tipo
        if item not in itens:
            itens.append(item)
    return "; ".join(itens) if itens else SEM_PENDENCIA


def resumo_sem_ia(reg, linha, nomes_equipe=()):
    """Resumo só com o cadastro, sem inventar: "Ação X sobre Y, movida por A contra B, em C/UF." """
    acao = sanitizar(_uma_linha(reg.get("acao")), nomes_equipe)
    objeto = sanitizar(_uma_linha(reg.get("objeto")), nomes_equipe)
    if acao:
        frase = acao if re.match(r"(?i)a[çc][ãa]o\b", acao) else f"Ação {acao}"
    else:
        frase = "Processo"
    if objeto:
        frase += f" sobre {objeto}"
    if linha["parte_ativa"] != NAO_INFORMADO:
        frase += f", movida por {linha['parte_ativa']}"
    if linha["parte_passiva"] != NAO_INFORMADO:
        frase += f" contra {linha['parte_passiva']}"
    if linha["cidade_uf"] != NAO_INFORMADO:
        frase += f", em {linha['cidade_uf']}"
    return frase.rstrip(" .,") + "."


# ---- montagem ----

def _chave_ordem(reg):
    def norm(texto):
        texto = unicodedata.normalize("NFKD", _uma_linha(texto)).encode("ascii", "ignore").decode()
        return texto.casefold()
    return (norm(reg.get("cliente")), norm(nomes_partes(reg.get("parte_ativa"))), norm(reg.get("numero")))


def _ficha(reg):
    ficha = reg.get("ficha")
    return ficha if isinstance(ficha, dict) else {}


def nomes_da_equipe(reg):
    """Nomes da equipe do escritório que aparecem na ficha (saem dos textos que vão ao cliente)."""
    ficha = _ficha(reg)
    nomes = [reg.get("advogado", ""), _campo_ficha(ficha, "Advogado responsável")]
    nomes += re.split(r"[,;/]", _campo_ficha(ficha, "Auxiliares"))
    nomes += [c.get("autor", "") for c in ficha.get("comentarios") or [] if isinstance(c, dict)]
    vistos, saida = set(), []
    for nome in nomes:
        nome = _uma_linha(nome)
        if nome and nome.casefold() not in vistos:
            vistos.add(nome.casefold())
            saida.append(nome)
    # nome mais longo primeiro: "MARIA SILVA SANTOS" sai antes de "MARIA SILVA"
    return sorted(saida, key=len, reverse=True)


def _linha_sem_ia(n, reg, hoje):
    ficha = _ficha(reg)
    lida = bool(ficha.get("ok"))
    equipe = nomes_da_equipe(reg)
    tarefas = ficha.get("tarefas") or []
    linha = {
        "id_extracao": str(n),
        "numero": _numero(reg, ficha),
        "parte_ativa": nomes_partes(reg.get("parte_ativa")) or nomes_partes(_campo_ficha(ficha, "Parte ativa")) or NAO_INFORMADO,
        "parte_passiva": nomes_partes(reg.get("parte_passiva")) or nomes_partes(_campo_ficha(ficha, "Parte passiva")) or NAO_INFORMADO,
        "tipo_processo": (_uma_linha(reg.get("tipo_processo")) or _uma_linha(reg.get("area"))
                          or _campo_ficha(ficha, "Processo") or NAO_INFORMADO),
        "orgao": _orgao(reg, ficha),
        "data_distribuicao": (data_br(reg.get("data_acao")) or data_br(ficha.get("data_distribuicao"))
                              or data_br(_campo_ficha(ficha, "Data da ação / Distribuição")) or NAO_INFORMADO),
        "valor_acao": (valor_br(reg.get("valor_acao")) or valor_br(ficha.get("valor_acao"))
                       or valor_br(_campo_ficha(ficha, "Valor da ação")) or NAO_INFORMADO),
        "cidade_uf": _uma_linha(ficha.get("cidade_uf")) or _campo_ficha(ficha, "Cidade / UF") or NAO_INFORMADO,
        "ultima_movimentacao": ultima_movimentacao(tarefas, hoje, equipe) if lida else NAO_INFORMADO,
        "pendencia": pendencia_sem_ia(tarefas, equipe) if lida else NAO_INFORMADO,
        "financeira": FINANCEIRA_PADRAO,
    }
    linha["resumo"] = resumo_sem_ia(reg, linha, equipe)
    return {chave: linha[chave] for chave in CHAVES}


def dados_para_ia(n, reg, linha, hoje=None):
    """Dados de um processo para a IA: só o que já foi sanitizado (nada de obs_proc, CI ou equipe)."""
    ficha = _ficha(reg)
    equipe = nomes_da_equipe(reg)
    tarefas = []
    for t in sorted([t for t in ficha.get("tarefas") or [] if not _cancelada(t)], key=_ci_num, reverse=True)[:15]:
        tarefas.append({
            "tipo": sanitizar(_uma_linha(t.get("tipo")), equipe),
            "situacao": "concluída" if data_br(t.get("concluida_em")) else "aberta",
            "para_conclusao": data_br(t.get("para_conclusao")),
            "concluida_em": data_br(t.get("concluida_em")),
            "descricao": cortar(sanitizar(t.get("descricao"), equipe), 600),
            "comentarios": cortar(sanitizar(t.get("comentarios"), equipe), 600),
        })
    comentarios = []
    for c in (ficha.get("comentarios") or [])[:10]:
        texto = cortar(sanitizar(c.get("texto"), equipe), 600) if isinstance(c, dict) else ""
        if texto:
            comentarios.append({"data": data_br(c.get("data")), "texto": texto})
    return {
        "id_extracao": n,
        "numero": linha["numero"],
        "acao": sanitizar(_uma_linha(reg.get("acao")), equipe),
        "objeto": sanitizar(_uma_linha(reg.get("objeto")), equipe),
        "tipo_processo": linha["tipo_processo"],
        "situacao": "encerrado" if encerrado(reg) else "ativo",
        "parte_ativa": linha["parte_ativa"],
        "parte_passiva": linha["parte_passiva"],
        "orgao": linha["orgao"],
        "cidade_uf": linha["cidade_uf"],
        "data_distribuicao": linha["data_distribuicao"],
        "valor_acao": linha["valor_acao"],
        "fase": sanitizar(_uma_linha(ficha.get("fase")), equipe),
        "ultima_movimentacao": linha["ultima_movimentacao"],
        "tarefas": tarefas,
        "comentarios": comentarios,
        "data_de_hoje": (hoje or date.today()).strftime("%d/%m/%Y"),
    }


def _estimar(gasto, modelo, sistema, usuario, processos):
    entrada = (len(sistema) + len(usuario)) / CARACTERES_POR_TOKEN
    saida = SAIDA_BASE + SAIDA_POR_PROCESSO * processos
    return gasto.custo(modelo, {"entrada": entrada, "entrada_cache": 0, "saida": saida})


def _texto_ia(valor, equipe=()):
    return cortar(sanitizar(valor, equipe), 1200)


def _aplicar_ia(ia, blocos, linhas_por_id, regs_por_id, gasto, modelo, prompt, hoje, observacoes, ao_falhar):
    """Chama a IA bloco a bloco. Devolve quantos processos ficaram com texto da IA."""
    com_ia = 0
    for i, ids in enumerate(blocos, 1):
        dados = [dados_para_ia(n, regs_por_id[n], linhas_por_id[n], hoje) for n in ids]
        usuario = json.dumps({"processos": dados}, ensure_ascii=False, indent=1)
        try:
            if gasto is not None:
                gasto.conferir(_estimar(gasto, modelo, prompt, usuario, len(ids)), f"bloco {i} do relatório")
            resposta = ia.responder(prompt, usuario, SCHEMA_IA)
            if gasto is not None:
                gasto.registrar(modelo, resposta.get("_uso"))
            itens = resposta.get("processos")
            if not isinstance(itens, list):
                raise ValueError("resposta da IA sem a lista 'processos'")
        except Exception as e:
            # o motivo técnico (chave, créditos, teto) fica só no log: o PDF vai para o cliente
            motivo = str(e) if isinstance(e, LimiteGasto) else f"{type(e).__name__}: {e}"
            log.warning("IA falhou no bloco %d de %d (%s): resto do grupo sem IA", i, len(blocos), motivo)
            restantes = sum(len(b) for b in blocos[i - 1:])
            observacoes.append(AVISO_SEM_IA_PARCIAL.format(n=restantes))
            if ao_falhar is not None:
                ao_falhar(e)
            # erro de chave, créditos ou teto se repetiria nos outros blocos: o resto vai sem IA
            break
        recebidos = {}
        for item in itens:
            if isinstance(item, dict):
                try:
                    recebidos[int(item.get("id_extracao"))] = item
                except (TypeError, ValueError):
                    continue
        faltando = [n for n in ids if n not in recebidos]
        if faltando:
            observacoes.append("A IA não devolveu o texto do(s) processo(s) "
                               + ", ".join(str(n) for n in faltando) + ": ficaram com o texto do cadastro.")
        for n in ids:
            item = recebidos.get(n)
            if not item:
                continue
            equipe = nomes_da_equipe(regs_por_id[n])
            linha = linhas_por_id[n]
            resumo = _texto_ia(item.get("resumo"), equipe)
            pendencia = _texto_ia(item.get("pendencia"), equipe)
            financeira = _texto_ia(item.get("financeira"), equipe)
            if resumo:
                linha["resumo"] = resumo
            if pendencia:
                linha["pendencia"] = pendencia
            linha["financeira"] = financeira or FINANCEIRA_PADRAO
            com_ia += 1
    return com_ia


def montar_linhas(registros, ia=None, gasto=None, modelo="", prompt=None, observacoes=None,
                  hoje=None, bloco=BLOCO_IA, ao_falhar=None):
    """Um dict por processo com as chaves de COLUNAS (todas str), ordenado por cliente, parte ativa e número.

    ia = provedor de bot/ia (responder(sistema, usuario, schema)); None = sem IA (não envia nada).
    gasto = bot.custo.Gasto (teto LLM_LIMITE_US); modelo = nome do modelo, para o custo.
    observacoes = lista que recebe os avisos para o PDF (falha da IA, fichas não lidas).
    ao_falhar = função chamada com a exceção quando a IA falha (o grupo segue sem IA).
    """
    if observacoes is None:
        observacoes = []
    hoje = hoje or date.today()
    ordenados = sorted([r for r in registros or [] if isinstance(r, dict)], key=_chave_ordem)
    linhas = [_linha_sem_ia(n, reg, hoje) for n, reg in enumerate(ordenados, 1)]

    sem_ficha = sum(1 for r in ordenados if not _ficha(r).get("ok"))
    if sem_ficha:
        observacoes.append(f"Ficha de {sem_ficha} processo(s) não foi lida: última movimentação e "
                           "pendência ficaram \"não informado\".")

    com_ia = 0
    if ia is not None and linhas:
        ids = list(range(1, len(linhas) + 1))
        tamanho = max(1, int(bloco or BLOCO_IA))
        blocos = [ids[i:i + tamanho] for i in range(0, len(ids), tamanho)]
        com_ia = _aplicar_ia(ia, blocos, dict(zip(ids, linhas)), dict(zip(ids, ordenados)),
                             gasto, modelo, prompt or PROMPT_IA, hoje, observacoes, ao_falhar)
    if linhas and ia is None:
        observacoes.append(AVISO_SEM_IA)
    return linhas
