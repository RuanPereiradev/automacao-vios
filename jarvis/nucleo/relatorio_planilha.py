"""Planilha mensal de processos por grupo (formato da planilha "Processos Casa do celular").

Cada processo vira uma linha da aba Processos:
- dados do cadastro (lupa -> Dados do Processo) e da lista, sem IA;
- resumo do caso, motivação, financeira, justificativa da condenação e documentos
  faltando, pela IA lendo as tarefas.

O texto das tarefas tem CPF, links, senhas de audiência e nomes da equipe: ele só
vai para a IA (depois de limpo) e nunca é copiado para a planilha.
"""
import logging
import re
from collections import Counter
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

log = logging.getLogger(__name__)

# lista fixa para dar para filtrar e contar; "Outros" quando nenhuma serve
MOTIVACOES = [
    "Financiamento / bloqueio do aparelho",
    "Defeito do produto / garantia",
    "Cobrança indevida / negativação",
    "Oferta ou contrato descumprido",
    "Atendimento / dano moral",
    "Trabalhista",
    "Outros",
]

# situação da decisão; só "Condenação" leva a justificativa escrita
CONDENACOES = [
    "Condenação",
    "Sem condenação (pedidos improcedentes)",
    "Acordo",
    "Sem decisão até o momento",
]

COLUNAS = [
    ("CI", 9),
    ("Número do processo", 27),
    ("Cliente", 30),
    ("Polo do cliente", 14),
    ("Parte ativa", 30),
    ("Parte passiva", 30),
    ("Tipo de processo", 14),
    ("Órgão", 32),
    ("Data da distribuição", 14),
    ("Valor da ação", 14),
    ("Cidade/UF", 20),
    ("Resumo do caso", 70),
    ("Motivação do processo", 40),
    ("Financeira", 30),
    ("Justificativa da condenação", 55),
    ("Pendência — documentos faltando", 45),
]
NOMES = [nome for nome, _ in COLUNAS]

# "Processo" vazio no VIOS: o tipo sai da "Área", como a equipe cadastra os demais processos
# (Cível Consumidor e Administrativo -> CÍVEL etc.); o processo continua em "Cadastro incompleto"
AREA_TIPO = {"CÍVEL CONSUMIDOR": "CÍVEL", "ADMINISTRATIVO": "CÍVEL", "CONTRATOS": "CÍVEL",
             "TRABALHISTA": "TRABALHISTA", "TRIBUTÁRIO": "TRIBUTÁRIO"}

# campos do cadastro que o relatório usa; vazio = cadastro incompleto
CADASTRO = {
    "Número do processo": "N.° CNJ",
    "Tipo de processo": "Processo",
    "Data da distribuição": "Data da ação / Distribuição",
    "Valor da ação": "Valor da ação",
    "Cidade/UF": "Cidade / UF",
    "Órgão": "Comarcas / Tribunais / Órgãos adm.",
}

SISTEMA = f"""Você recebe os dados de UM processo do escritório (sistema VIOS): o cadastro e o
histórico de tarefas da equipe. Escreva os campos de uma planilha mensal que vai para o
cliente da empresa (leigo). Responda só com o JSON pedido.

Regras:
- resumo_caso: 2 a 4 frases, linguagem simples, sem juridiquês: quem processou, o que alega,
  o que pede e em que pé está, do ponto de vista do processo (decisões, audiências, prazos).
  Sem CPF, links, senhas ou nomes de funcionários do escritório. Não mencione rotinas internas
  do escritório (pagamento de correspondente, tarefas da equipe, reuniões internas, relatórios
  enviados, cadastro no sistema).
- motivacao_categoria: a que melhor descreve a causa do processo, desta lista: {", ".join(MOTIVACOES)}.
- motivacao_detalhe: no máximo 12 palavras, objetivo (ex.: "parcelas quinzenais, juros e bloqueio remoto").
- financeira: financeiras, bancos ou securitizadoras envolvidos no caso (ex.: PayJoy, Odres Cred,
  BMP), separados por "; ". Vazio se não houver.
- condenacao_situacao: o resultado da decisão mais recente (sentença, acórdão ou decisão
  administrativa) PARA O CLIENTE, desta lista: {", ".join(CONDENACOES)}.
  "Condenação" = o cliente foi condenado a pagar, devolver, trocar ou fazer algo, mesmo que em parte.
- condenacao_justificativa: só quando condenacao_situacao = "Condenação": 1 ou 2 frases simples
  com o motivo que o juiz/órgão deu para condenar e o que o cliente tem que fazer (valor, se
  houver). Ex.: "O juiz entendeu que a loja vendeu o aparelho com defeito e não resolveu no
  prazo da garantia; condenou a devolver R$ 1.800,00 e pagar R$ 2.000,00 de danos morais."
  Se o motivo não estiver nas tarefas, diga só o que foi decidido. Vazio nas outras situações.
- documentos_faltando: documentos que a equipe PEDIU (ao cliente ou a terceiros) e que, pelas
  tarefas, AINDA NÃO chegaram. Compare o que foi solicitado com o que foi recebido/analisado
  (tarefas "ANALISAR DOCUMENTOS", arquivos enviados). Lista vazia se nada falta ou se não houve pedido.
  Não invente: só o que aparece nas tarefas.
- documentos_quem_entrega: quem deve entregar os documentos faltando (ex.: "Cliente"). Vazio se a
  lista estiver vazia. Nunca o nome de um funcionário do escritório.
- Se a informação não estiver nas tarefas, deixe o campo vazio. Não use conhecimento externo.
- Em TODOS os campos, escreva só fatos do processo: o que as partes pediram, o que o juiz,
  tribunal ou órgão decidiu, prazos e audiências. NUNCA reproduza opiniões, avaliações ou
  estratégias internas do escritório, mesmo que estejam nas tarefas. Exemplos do que não pode
  aparecer: "a condenação está acima da média", "não vale a pena recorrer", "dispensada por
  economia", "tese defensiva", "chances de êxito", "reorganizar a empresa para reduzir a
  exposição a fiscalizações", recomendações feitas ao cliente.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "resumo_caso": {"type": "string"},
        "motivacao_categoria": {"type": "string", "enum": MOTIVACOES},
        "motivacao_detalhe": {"type": "string"},
        "financeira": {"type": "string"},
        "condenacao_situacao": {"type": "string", "enum": CONDENACOES},
        "condenacao_justificativa": {"type": "string"},
        "documentos_faltando": {"type": "array", "items": {"type": "string"}},
        "documentos_quem_entrega": {"type": "string"},
    },
    "required": ["resumo_caso", "motivacao_categoria", "motivacao_detalhe", "financeira",
                 "condenacao_situacao", "condenacao_justificativa",
                 "documentos_faltando", "documentos_quem_entrega"],
    "additionalProperties": False,
}

# processo sem tarefas no VIOS: não vai para a IA
SEM_TAREFAS = {
    "resumo_caso": "", "motivacao_categoria": "Outros", "motivacao_detalhe": "sem tarefas no VIOS",
    "financeira": "", "condenacao_situacao": "Sem decisão até o momento", "condenacao_justificativa": "",
    "documentos_faltando": [], "documentos_quem_entrega": "",
}

MAX_TAREFA = 6000      # caracteres por texto de tarefa enviados à IA
MAX_PROCESSO = 40000   # caracteres por processo


def _br(texto):
    try:
        return datetime.strptime(texto, "%d/%m/%Y")
    except (TypeError, ValueError):
        return None


def _valor(texto):
    """'R$ 1.234,56' -> 1234.56; vazio -> None."""
    numeros = re.sub(r"[^\d,.-]", "", texto or "")
    if not numeros:
        return None
    try:
        return float(numeros.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def limpar(texto):
    """Tira do texto da tarefa o que não deve ir para a IA nem é útil para ela."""
    # o VIOS repete o comentário depois de "[observação da conclusão]"
    partes = texto.split("[observação da conclusão]")
    if len(partes) > 1 and partes[1].strip()[:200] in partes[0]:
        texto = partes[0]
    # texto padrão do tipo de tarefa (igual em todo processo)
    texto = re.sub(r"Descrição do tipo da tarefa( de origem)?:.*?(?=\n\s*\n[A-ZÀ-Ú]|\Z)", "", texto, flags=re.S)
    texto = re.sub(r"https?://\S+", "[link]", texto)
    texto = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF]", texto)
    texto = re.sub(r"(?im)^.*\b(senha|id de acesso)\b.*$", "", texto)
    texto = re.sub(r"\n\s*\n+", "\n", texto).strip()
    return texto[:MAX_TAREFA]


def tarefas_validas(proc):
    return [t for t in proc["tarefas"] if not t["cancelada"]]


def texto_para_ia(item, proc):
    d = proc["dados"]
    campos = ["Cliente", "Polo do cliente", "Parte ativa", "Parte passiva", "Área", "Ação", "Fase",
              "Comarcas / Tribunais / Órgãos adm.", "Cidade / UF", "Terceiros"]
    linhas = [f"Processo: {item.get('numero') or d.get('N.° CNJ', '')}"]
    linhas += [f"{c}: {d.get(c, '')}" for c in campos if d.get(c)]
    linhas.append("\nTAREFAS (na ordem do VIOS):")
    for t in tarefas_validas(proc):
        situacao = f"concluída em {t['concluida_em']}" if t["concluida"] else f"em aberto, prazo {t['para_conclusao']}"
        bloco = [f"\n## {t['tipo']} ({situacao})"]
        for rotulo, campo in (("Descrição", "descricao"), ("Comentários", "comentarios")):
            texto = limpar(t[campo])
            if texto:
                bloco.append(f"{rotulo}: {texto}")
        linhas += bloco
    return "\n".join(linhas)[:MAX_PROCESSO]


def _justificativa(ia):
    if ia["condenacao_situacao"] == "Condenação":
        return ia["condenacao_justificativa"] or "Condenação (motivo não registrado no VIOS)"
    return ia["condenacao_situacao"]


def motivo_erro(erro):
    """Motivo curto do erro da IA para a célula ("teto de gasto", "sem crédito", ...). Nunca o texto do processo."""
    t = str(erro or "")
    baixo = t.lower()
    for trecho, motivo in (("teto de gasto", "teto de gasto da execução atingido (LLM_LIMITE_US)"),
                           ("credit balance", "sem crédito na conta da Anthropic"),
                           ("insufficient_quota", "sem crédito na conta da OpenAI"),
                           ("api_key", "chave da IA ausente ou inválida"), ("authentication", "chave da IA inválida"),
                           ("error code: 401", "chave da IA inválida"), ("not_found", "modelo da IA não existe (LLM_MODELO)"),
                           ("rate_limit", "limite de uso da IA por minuto (tente de novo)"), ("overloaded", "IA sobrecarregada (tente de novo)"),
                           ("timeout", "a IA demorou demais"), ("timed out", "a IA demorou demais"),
                           ("json", "resposta da IA fora do formato")):
        if trecho in baixo:
            return motivo
    return re.sub(r"\s+", " ", t)[:90] or "motivo não informado"


def montar_linha(item, proc, ia):
    """item = linha da lista de processos; proc = lupa; ia = resposta da IA (ou {"erro": ...})."""
    d = proc["dados"]
    erro = ia.get("erro")
    motivacao = "" if erro else ia["motivacao_categoria"] + (f" — {ia['motivacao_detalhe']}" if ia["motivacao_detalhe"] else "")
    faltando = [] if erro else ia["documentos_faltando"]
    docs = ""
    aviso = f"ERRO NA IA: conferir ({motivo_erro(erro)})" if erro else ""
    if erro:
        docs = aviso
    elif faltando:
        docs = "; ".join(faltando) + (f" (entrega: {ia['documentos_quem_entrega']})" if ia["documentos_quem_entrega"] else "")
    return {
        "CI": int(item["ci"]) if str(item["ci"]).isdigit() else item["ci"],
        "Número do processo": (d.get("N.° CNJ") or item.get("numero", "")).replace("CNJ:", "").strip(),
        "Cliente": d.get("Cliente") or item.get("cliente", ""),
        "Polo do cliente": d.get("Polo do cliente", ""),
        "Parte ativa": "; ".join(item.get("parte_ativa", [])) or d.get("Parte ativa", ""),
        "Parte passiva": "; ".join(item.get("parte_passiva", [])) or d.get("Parte passiva", ""),
        "Tipo de processo": (d.get("Processo") or "").upper() or AREA_TIPO.get((d.get("Área") or "").upper(), ""),
        "Órgão": d.get("Comarcas / Tribunais / Órgãos adm.") or item.get("orgao", ""),
        "Data da distribuição": _br(d.get("Data da ação / Distribuição", "")),
        "Valor da ação": _valor(d.get("Valor da ação", "")),
        "Cidade/UF": d.get("Cidade / UF", ""),
        "Resumo do caso": aviso if erro else ia["resumo_caso"],
        "Motivação do processo": motivacao,
        "Financeira": "" if erro else ia["financeira"],
        "Justificativa da condenação": aviso if erro else _justificativa(ia),
        "Pendência — documentos faltando": docs,
        # só para a aba Resumo (não vira coluna)
        "_condenacao": "" if erro else ia["condenacao_situacao"],
        "_tipo_pela_area": not (d.get("Processo") or "").strip(),
    }


def cadastro_incompleto(linha):
    faltam = [col for col in CADASTRO if linha[col] in (None, "")]
    if linha.get("_tipo_pela_area") and "Tipo de processo" not in faltam:
        faltam.insert(0, "Tipo de processo")  # preenchido pela Área, mas vazio no VIOS
    return faltam


def salvar_xlsx(arquivo, grupo, linhas, info):
    """info: {gerado_em, modelo, gasto, erros_ia}."""
    wb = Workbook()
    titulo = Font(bold=True, size=14)
    negrito = Font(bold=True, color="FFFFFF")
    fundo = PatternFill("solid", fgColor="1F4E78")
    quebra = Alignment(wrap_text=True, vertical="top")

    ws = wb.active
    ws.title = "Processos"
    ws.append(NOMES)
    for i, (_, largura) in enumerate(COLUNAS, 1):
        cel = ws.cell(row=1, column=i)
        cel.font, cel.fill, cel.alignment = negrito, fundo, quebra
        ws.column_dimensions[get_column_letter(i)].width = largura
    for linha in linhas:
        ws.append([linha[nome] for nome in NOMES])
    for row in ws.iter_rows(min_row=2):
        for cel in row:
            cel.alignment = quebra
        # minúsculo: "DD/MM/YYYY" o Excel entende, mas o Numbers (Mac) e o Google Planilhas mostram "DD/01/YYYY"
        row[NOMES.index("Data da distribuição")].number_format = "dd/mm/yyyy"
        row[NOMES.index("Valor da ação")].number_format = '"R$" #,##0.00'
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions

    # Resumo
    rs = wb.create_sheet("Resumo")
    rs["A1"] = f"RELATÓRIO DE PROCESSOS — {grupo}"
    rs["A1"].font = titulo
    ultima = max(len(linhas) + 1, 2)
    col_valor = get_column_letter(NOMES.index("Valor da ação") + 1)
    blocos = [
        ("Atualização do relatório", info["gerado_em"].strftime("%d/%m/%Y")),
        ("Processos no relatório", f"=COUNTA(Processos!A2:A{ultima})"),
        ("Soma dos valores das ações", f"=SUM(Processos!{col_valor}2:{col_valor}{ultima})"),
    ]
    r = 3
    for rotulo, valor in blocos:
        rs.cell(row=r, column=1, value=rotulo)
        rs.cell(row=r, column=2, value=valor)
        r += 1
    rs.cell(row=5, column=2).number_format = '"R$" #,##0.00'
    for titulo_bloco, coluna in (("Por tipo de processo", "Tipo de processo"),
                                 ("Por motivação", "Motivação do processo"),
                                 ("Por resultado da decisão", "_condenacao"),
                                 ("Por cliente", "Cliente"),
                                 ("Por polo do cliente", "Polo do cliente")):
        r += 1
        rs.cell(row=r, column=1, value=titulo_bloco).font = Font(bold=True)
        r += 1
        chave = (lambda v: v.split(" — ")[0]) if coluna == "Motivação do processo" else (lambda v: v)
        for valor, qtd in Counter(chave(l[coluna]) or "não informado" for l in linhas).most_common():
            rs.cell(row=r, column=1, value=valor)
            rs.cell(row=r, column=2, value=qtd)
            r += 1
    rs.column_dimensions["A"].width = 45
    rs.column_dimensions["B"].width = 18

    # Cadastro incompleto: o que a equipe precisa completar no VIOS
    ci = wb.create_sheet("Cadastro incompleto")
    ci.append(["CI", "Número do processo", "Campos vazios no VIOS"])
    for l in linhas:
        faltam = cadastro_incompleto(l)
        if faltam:
            ci.append([l["CI"], l["Número do processo"], ", ".join(faltam)])
    for col, larg in zip("ABC", (9, 28, 60)):
        ci.column_dimensions[col].width = larg
    for cel in ci[1]:
        cel.font, cel.fill = negrito, fundo

    # Metadados
    md = wb.create_sheet("Metadados")
    md.append(["Item", "Informação"])
    for item in (
        ("Grupo Cliente (VIOS)", grupo),
        ("Gerado em", info["gerado_em"].strftime("%d/%m/%Y %H:%M")),
        ("Origem", "VIOS: lista de processos (Ativos, Não migrados) + tela de cada processo (Dados do Processo e tarefas)"),
        ("Colunas pela IA", "Resumo do caso, Motivação, Financeira, Justificativa da condenação, "
                            f"Pendência — documentos faltando (modelo {info['modelo']})"),
        ("Processos com erro na IA", info["erros_ia"]),
        ("Gasto estimado com IA", info["gasto"]),  # deste grupo (a execução pode ter vários)
    ):
        md.append(list(item))
    md.column_dimensions["A"].width = 30
    md.column_dimensions["B"].width = 100
    for cel in md[1]:
        cel.font, cel.fill = negrito, fundo

    arquivo.parent.mkdir(parents=True, exist_ok=True)
    wb.save(arquivo)
