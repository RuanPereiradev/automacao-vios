"""Albi — mensagem no padrão da CAC (Central de Atendimento ao Cliente) para cada pessoa pesquisada.

Modelo do escritório (sem entrar em tribunal nenhum: só os registros processuais do Sonar):
  • com processos: "*Beatriz Vasconcelos:* Informamos que, após consulta aos registros processuais
    disponibilizados, foram localizados *3 (três) processos judiciais* relacionados a *NOME*, CPF nº ...,
    todos vinculados ao *TJSE*." + período e natureza + quantos arquivados/em tramitação + um bloco por
    processo ("*1️⃣ Autor x Réu*", "*Processo nº ... — TJSE*", o que é a ação, posição da pessoa, o que a
    pesquisa não traz, andamento e "*Conclusão:*");
  • sem processos: "*Beatriz Vasconcelos:* Informamos que após consulta ao sistema do Poder Judiciário, não
    localizamos *nenhum processo* em nome de *NOME*.".
Negrito no padrão do WhatsApp (*texto*). Sem inteligência artificial (regras fixas) e sem consulta ao
DataJud: o texto só afirma o que está na planilha do Sonar. Sem "Sr./Sra.": o gênero não está nos dados
(a atendente pode acrescentar ao revisar).
Escreve mensagens_cac.txt (para copiar) e mensagens_cac.json (para a página /albi).
"""
import json
import re
from pathlib import Path

import explicacao_ia
import relatorio as R

ATENDENTES = ("Beatriz Vasconcelos", "Renara Kathleem")
SEPARADOR = R.SEPARADOR
NUMEROS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
           "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove", "vinte"]
EMOJI = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# o Sonar manda tudo em maiúsculas e sem acento: devolve o acento das palavras mais comuns
ACENTOS = {
    "ACAO": "ação", "ACOES": "ações", "EXECUCAO": "execução", "EXECUCOES": "execuções", "CIVEL": "cível", "CIVIL": "civil",
    "SUCESSOES": "sucessões", "FAMILIA": "família", "TRIBUTARIO": "tributário", "REVISAO": "revisão",
    "CLAUSULAS": "cláusulas", "ALIENACAO": "alienação", "FIDUCIARIA": "fiduciária", "APREENSAO": "apreensão",
    "COBRANCA": "cobrança", "INVENTARIO": "inventário", "HABILITACAO": "habilitação", "CREDITO": "crédito",
    "PRECATORIA": "precatória", "REGULAMENTACAO": "regulamentação", "CRIANCA": "criança", "INFANCIA": "infância",
    "FORUM": "fórum", "CLOVIS": "Clóvis", "BEVILAQUA": "Beviláqua", "TRAMITACAO": "tramitação",
    "INDENIZACAO": "indenização", "RECLAMACAO": "reclamação", "PREVIDENCIARIO": "previdenciário",
    "PREVIDENCIARIA": "previdenciária", "BENEFICIO": "benefício", "AUXILIO": "auxílio", "DOENCA": "doença",
    "PENSAO": "pensão", "DIVORCIO": "divórcio", "UNIAO": "união", "ESTAVEL": "estável", "SENTENCA": "sentença",
    "JUIZO": "juízo", "UNICA": "única", "JUSTICA": "justiça", "PUBLICA": "pública", "ORDINARIO": "ordinário",
    "SUMARIO": "sumário", "TITULO": "título", "MONITORIA": "monitória", "CONDOMINIO": "condomínio",
    "CONDOMINIOS": "condomínios", "EDIFICIO": "edifício", "CITACAO": "citação", "DIVIDA": "dívida",
    "PRESTACAO": "prestação", "SERVICOS": "serviços", "SERVICO": "serviço", "INTERPRETACAO": "interpretação",
    "RELACOES": "relações", "ADMINISTRACAO": "administração", "MUNICIPIO": "município", "TRANSITO": "trânsito",
    "CEARA": "Ceará", "DISTRIBUICAO": "distribuição", "SAO": "São", "JOAO": "João", "AGUA": "água", "ATOS": "atos", "MINISTERIO": "Ministério", "PUBLICO": "público", "CAFE": "café", "ORGAO": "órgão",
    "UNIVERSITARIO": "universitário", "ASSISTENCIA": "assistência", "ANTECIPACAO": "antecipação", "TUTELA": "tutela", "PROCESSUAIS": "processuais",
    "COMERCIO": "comércio", "ELETRICA": "elétrica", "ENERGIA": "energia", "TELEFONIA": "telefonia",
    "BANCARIO": "bancário", "BANCARIOS": "bancários", "CONTRATACAO": "contratação", "CONTRIBUICAO": "contribuição",
    "CONTRIBUICOES": "contribuições", "RESCISAO": "rescisão", "RESCISORIAS": "rescisórias", "RESCISORIA": "rescisória",
    "SALARIO": "salário", "SALARIOS": "salários", "INDENIZATORIA": "indenizatória", "OBRIGACAO": "obrigação",
    "OBRIGACOES": "obrigações", "POSSESSORIA": "possessória", "USUCAPIAO": "usucapião", "VEICULO": "veículo",
    "VEICULOS": "veículos", "ACIDENTE": "acidente", "TRAFEGO": "tráfego", "CRIME": "crime", "CRIMES": "crimes",
    "LESAO": "lesão", "CORPORAL": "corporal", "AMEACA": "ameaça", "VIOLENCIA": "violência", "DOMESTICA": "doméstica",
    "INQUERITO": "inquérito", "POLICIAL": "policial", "TERMO": "termo", "CIRCUNSTANCIADO": "circunstanciado",
    "PROCEDIMENTO": "procedimento", "ESPECIAL": "especial", "JUIZADO": "juizado", "COMUM": "comum",
    "TRABALHO": "trabalho", "INSTANCIA": "instância", "REGIAO": "região", "DISTRITO": "distrito",
    "ADOLESCENTE": "adolescente", "PATERNIDADE": "paternidade", "INVESTIGACAO": "investigação",
    "MATERNIDADE": "maternidade", "ALIMENTOS": "alimentos", "EXONERACAO": "exoneração", "OFICIO": "ofício",
    "PROPRIEDADE": "propriedade", "POSSE": "posse", "LOCACAO": "locação", "IMOVEL": "imóvel", "IMOVEIS": "imóveis",
    "URBANO": "urbano", "CONSUMIDOR": "consumidor", "FORNECEDOR": "fornecedor", "DANO": "dano", "DANOS": "danos",
    "MORAL": "moral", "MORAIS": "morais", "MATERIAL": "material", "MATERIAIS": "materiais", "REU": "réu",
    "REUS": "réus", "EXEQUENTE": "exequente", "EXECUTADO": "executado", "EXECUTADA": "executada",
    "CUSTODIA": "custódia", "AUDIENCIA": "audiência", "PECULIO": "pecúlio", "COMARCA": "comarca",
    "PROVISORIO": "provisório", "PROVISORIA": "provisória", "DECISAO": "decisão", "DECISOES": "decisões",
    "CONSORCIO": "consórcio", "CONSORCIOS": "consórcios", "DEFINITIVO": "definitivo", "DEFINITIVA": "definitiva",
    "JURIDICA": "jurídica", "JURIDICO": "jurídico", "ADMINISTRADORA": "administradora", "FINANCIAMENTO": "financiamento",
    "ESPECIAIS": "especiais", "CRIMINAL": "criminal", "FAZENDA": "fazenda", "ORDINARIO": "ordinário",
}
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "em", "a", "o", "na", "no", "nas", "nos", "por", "para", "com", "ou"}
SIGLAS = {"LTDA", "S/A", "SA", "S.A.", "ME", "EPP", "EIRELI", "CNPJ", "CPF", "INSS", "TJ", "TRT", "TRF", "TST", "STJ",
          "STF", "AMC", "BV", "MEI", "UF", "CE", "SP", "RJ", "MG", "PE", "PI", "MA", "RN", "PB", "BA", "AL", "SE", "PA",
          "AM", "DF", "GO", "MT", "MS", "PR", "SC", "RS", "ES", "TO", "RO", "AC", "AP", "RR", "CVT", "SEJUD", "II", "III", "IV"}


def _palavra(p, primeira, nome):
    """Uma palavra em maiúsculas do Sonar -> com acento e caixa certa."""
    base = R._sem_acento(p)
    if base in SIGLAS or re.fullmatch(r"[A-Z]{1,3}-[A-Z]{1,3}|\d+[ªº°]?", base) or "/" in base and len(base) <= 4:
        return p
    if base in ACENTOS:
        w = ACENTOS[base]
    else:
        w = p.lower()
    if nome or primeira:
        return w if (w in MINUSCULAS and not primeira) else w[:1].upper() + w[1:]
    return w if w[:1].islower() or w[:1].isdigit() else w  # nomes próprios do dicionário (Ceará, João) ficam


def texto(v, nome=False):
    """"EXECUCAO FISCAL" -> "Execução fiscal"; com nome=True -> "Condomínio Village Água Fria"."""
    v = R._limpo(v)
    if not v or v != v.upper():
        return v
    partes = re.split(r"(\s+|[-–,()])", v)  # sem "/": "S/A" fica uma palavra só
    out, primeira = [], True
    for p in partes:
        if not p or re.fullmatch(r"\s+|[-–,()]", p):
            out.append(p)
            continue
        out.append(_palavra(p, primeira, nome))
        primeira = False
    return "".join(out)


def _quantos(n, um, varios, feminino=False):
    if n <= 20:
        w = "uma" if (n == 1 and feminino) else "duas" if (n == 2 and feminino) else NUMEROS[n]
        return f"{w} {um if n == 1 else varios}"
    return f"{n} {varios}"


def _artigo_orgao(orgao):
    """"4ª Vara..." -> "a 4ª Vara..."; "5º Juizado" -> "o 5º Juizado"."""
    b = R._sem_acento(orgao)
    if re.match(r"\d+\s*ª", orgao) or b.startswith(("VARA", "TURMA", "CAMARA", "SECAO", "UNIDADE", "SECRETARIA", "CENTRAL")):
        return "a " + orgao
    if re.match(r"\d+\s*[º°]", orgao) or b.startswith(("JUIZADO", "JUIZO", "TRIBUNAL", "FORO", "FORUM", "NUCLEO", "CEJUSC")):
        return "o " + orgao
    return "o juízo " + orgao


def _nomes(lista, maximo=2):
    nomes = [texto(n, nome=True) for _, n, _ in lista]
    if not nomes:
        return ""
    return " e ".join(nomes[:maximo]) if len(nomes) <= maximo else ", ".join(nomes[:maximo]) + f" e outros ({len(nomes) - maximo})"


EXPLICA_POLO = {"Polo passivo": "parte contra quem a ação foi proposta", "Polo ativo": "parte que iniciou a ação",
                "Outra parte": "parte interessada no processo, sem ser autora nem ré",
                "Advogado(a)": "advogado(a) que atua no processo, e não como parte"}



# o que é cada classe processual, em palavras simples (a primeira que bater, na ordem)
EXPLICA_CLASSE = [
    (("RECLAMACAO TRABALHISTA", "ACAO TRABALHISTA"), "uma ação em que o trabalhador cobra, na Justiça do Trabalho, "
     "direitos que entende não terem sido pagos durante ou ao fim da relação de trabalho"),
    (("EXECUCAO FISCAL",), "a cobrança judicial de uma dívida com o poder público (impostos, taxas ou multas)"),
    (("EXECUCAO DE ALIMENTOS", "CUMPRIMENTO DE SENTENCA DE OBRIGACAO DE PRESTAR ALIMENTOS"),
     "a cobrança judicial de pensão alimentícia não paga"),
    (("EXECUCAO DE TITULO EXTRAJUDICIAL",), "a cobrança judicial de uma dívida representada em documento, como "
     "contrato, cheque ou nota promissória"),
    (("CUMPRIMENTO DE SENTENCA",), "a fase de cobrança daquilo que já foi decidido pela Justiça"),
    (("EMBARGOS A EXECUCAO",), "a defesa apresentada por quem está sendo cobrado em uma execução"),
    (("MONITORIA",), "a cobrança de uma dívida baseada em prova escrita que ainda não tem força de título executivo"),
    (("BUSCA E APREENSAO",), "o pedido do credor para retomar um bem, geralmente um veículo, dado em garantia de um "
     "financiamento"),
    (("INQUERITO POLICIAL",), "uma investigação conduzida pela polícia para apurar um fato; não é um processo contra a "
     "pessoa e não significa acusação nem condenação"),
    (("TERMO CIRCUNSTANCIADO",), "o registro de uma infração de menor potencial ofensivo, que tramita no Juizado "
     "Especial Criminal; não significa condenação"),
    (("MEDIDAS PROTETIVAS",), "um pedido de medidas de proteção previstas na Lei Maria da Penha"),
    (("ACAO PENAL",), "um processo criminal em que há acusação formal, em regra feita pelo Ministério Público; "
     "responder a uma ação penal não significa condenação"),
    (("CARTA PRECATORIA", "CARTA DE ORDEM"), "um pedido de um juízo a outro para a prática de um ato (como ouvir uma "
     "testemunha ou entregar uma comunicação); não é uma ação nova"),
    (("MANDADO DE SEGURANCA",), "uma ação contra ato de autoridade pública considerado ilegal"),
    (("DESPEJO",), "uma ação do proprietário para retomar um imóvel alugado"),
    (("USUCAPIAO",), "um pedido de reconhecimento da propriedade de um imóvel pela posse prolongada"),
    (("REINTEGRACAO DE POSSE", "MANUTENCAO DE POSSE", "INTERDITO"), "uma disputa sobre a posse de um imóvel ou bem"),
    (("INVENTARIO", "ARROLAMENTO"), "a divisão dos bens de uma pessoa falecida entre os herdeiros"),
    (("DIVORCIO",), "uma ação de divórcio"),
    (("ALIMENTOS",), "uma ação sobre pensão alimentícia"),
    (("AGRAVO", "APELACAO", "RECURSO"), "um recurso, em que o tribunal reexamina uma decisão anterior"),
    (("JUIZADO ESPECIAL",), "uma ação no Juizado Especial, destinado a causas de menor valor e complexidade"),
    (("PROCEDIMENTO COMUM", "PROCEDIMENTO ORDINARIO", "PROCEDIMENTO SUMARIO"), "uma ação em que uma parte leva à "
     "Justiça um conflito com a outra e pede uma solução"),
]
# assuntos comuns (Tabela Processual Unificada do CNJ), em palavras simples
EXPLICA_ASSUNTO = {
    "INCLUSAO INDEVIDA EM CADASTRO DE INADIMPLENTES": "inclusão do nome em cadastros de devedores, como SPC e Serasa, "
                                                       "que é contestada",
    "HORAS EXTRAS": "horas trabalhadas além da jornada",
    "INTERVALO INTRAJORNADA": "intervalo para alimentação e descanso",
    "ADICIONAL NOTURNO": "acréscimo pelo trabalho à noite",
    "VERBAS RESCISORIAS": "valores devidos no fim do contrato de trabalho",
    "RECONHECIMENTO DE RELACAO DE EMPREGO": "pedido para reconhecer o vínculo de emprego",
    "ANOTACAO NA CTPS": "registro na carteira de trabalho",
    "FGTS": "depósitos do Fundo de Garantia",
    "INDENIZACAO POR DANO MORAL": "reparação por ofensa à honra, à imagem ou ao bem-estar",
    "INDENIZACAO POR DANO MATERIAL": "reparação de prejuízo financeiro",
    "ALIENACAO FIDUCIARIA": "financiamento em que o próprio bem fica como garantia",
    "IPTU": "imposto sobre imóvel urbano",
    "IPVA": "imposto sobre veículo",
    "PENSAO POR MORTE": "benefício do INSS pago aos dependentes de quem faleceu",
    "AUXILIO-DOENCA": "benefício do INSS por incapacidade temporária para o trabalho",
    "AUXILIO POR INCAPACIDADE TEMPORARIA": "benefício do INSS por incapacidade temporária para o trabalho",
    "BENEFICIO ASSISTENCIAL": "benefício de prestação continuada (BPC/LOAS)",
    "APOSENTADORIA POR IDADE": "benefício do INSS",
    "APOSENTADORIA POR INVALIDEZ": "benefício do INSS por incapacidade permanente",
}


def _explica_classe(classe):
    c = R._sem_acento(classe)
    for chaves, txt in EXPLICA_CLASSE:
        if any(k in c for k in chaves):
            return txt
    return ""


def _assunto(a):
    """"Horas Extras" -> "*horas extras* (horas trabalhadas além da jornada)"."""
    base = R._sem_acento(a)
    nome = " ".join(w if (w.isupper() and len(w) <= 5) else w.lower() for w in texto(a).split())
    exp = next((v for k, v in EXPLICA_ASSUNTO.items() if k == base or k in base), "")
    return f"*{nome}*" + (f" ({exp})" if exp else "")


def _lista(itens):
    itens = [i for i in itens if i]
    return ", ".join(itens[:-1]) + " e " + itens[-1] if len(itens) > 1 else (itens[0] if itens else "")


def _situacao_rotulo(x):
    """Situação do cadastro do Sonar: (rotulo curto, chave). Chaves: arq_def, arq, baixa, extinto, susp, tram, nd."""
    st = R._sem_acento(x.get("status"))
    if not st or st in R.VAZIO:
        return "situação não informada", "nd"
    if "ARQUIV" in st:
        return ("arquivamento definitivo", "arq_def") if "DEFINITIV" in st else ("arquivamento", "arq")
    if "BAIXA" in st:
        return "baixa", "baixa"
    if "EXTIN" in st:
        return "extinção", "extinto"
    if "SUSPEN" in st or "SOBREST" in st:
        return "suspensão", "susp"
    return "tramitação", "tram"


def _andamento(x):
    """Parágrafos sobre a situação processual, só com o que o cadastro informa."""
    _, k = _situacao_rotulo(x)
    if k == "arq_def":
        return ["Quanto ao andamento, a informação disponibilizada indica que o processo se encontra em situação de "
                "*ARQUIVAMENTO DEFINITIVO*.",
                "Isso significa que, segundo o registro consultado, o processo foi encerrado e encaminhado ao arquivo, não "
                "constando como uma ação em tramitação ativa nessa base."]
    if k == "arq":
        return ["Quanto ao andamento, o registro consultado indica que o processo se encontra *ARQUIVADO*.",
                "Isso significa que, segundo o registro, ele não consta como ação em tramitação ativa nessa base."]
    if k == "baixa":
        return ["Quanto ao andamento, o registro consultado indica que o processo recebeu *BAIXA*, ou seja, foi encerrado "
                "no juízo em que tramitava."]
    if k == "extinto":
        return ["Quanto ao andamento, o registro consultado indica que o processo foi *EXTINTO*, ou seja, encerrado pela "
                "Justiça."]
    if k == "susp":
        return ["Quanto ao andamento, o registro consultado indica que o processo se encontra *SUSPENSO*, aguardando a "
                "retomada da tramitação."]
    if k == "tram":
        return ["Quanto ao andamento, o registro consultado indica que o processo *consta como em tramitação* na base "
                "consultada."]
    return ["A situação atual do processo não consta nos registros consultados."]


def _papel(x):
    """Como a pessoa aparece no processo: (rótulo curto, explicação) a partir do cadastro."""
    polo, papel = x.get("polo"), (x.get("papel") or "")
    papel_txt = " ".join(ACENTOS.get(R._sem_acento(w), w.lower()).lower() for w in papel.split()) if papel else ""
    if polo == "Polo ativo":
        return papel_txt or "parte autora", "parte que iniciou a ação"
    if polo == "Polo passivo":
        return papel_txt or "parte ré", "parte contra quem a ação foi proposta"
    if polo == "Outra parte":
        return papel_txt or "outra parte interessada", "parte interessada no processo, sem ser autora nem ré"
    if polo == "Advogado(a)":
        return papel_txt or "advogado(a)", "advogado(a) que atua no processo, e não como parte"
    return "", ""


def _data_br(x):
    return R.data(x.get("distribuicao")) or ""


def _ano(x):
    m = re.search(r"(\d{4})\s*$", _data_br(x))
    return int(m.group(1)) if m else None


def _onde(x):
    comarca = texto(re.split(r"\s+[-–]\s+", R._limpo(x.get("comarca")))[0], nome=True)
    comarca = re.sub(r"^Comarca de\s+", "", comarca, flags=re.I)
    orgao = texto(x.get("orgao"), nome=True)
    if comarca and R._sem_acento(comarca) in R._sem_acento(orgao):  # a vara já diz a comarca
        comarca = ""
    uf = R._limpo(x.get("uf"))
    return comarca, uf, orgao


ESTADOS = {"AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
           "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
           "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
           "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
           "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
           "SE": "Sergipe", "TO": "Tocantins"}


ARTIGO_ESTADO = {"AC": "do", "AP": "do", "AM": "do", "BA": "da", "CE": "do", "DF": "do", "ES": "do", "MA": "do",
                 "PA": "do", "PB": "da", "PR": "do", "PI": "do", "RJ": "do", "RN": "do", "RS": "do", "TO": "do"}


def de_estado(uf):
    """"CE" -> "do Ceará"; "SE" -> "de Sergipe"; "PB" -> "da Paraíba"."""
    nome = ESTADOS.get(R._limpo(uf).upper())
    return f"{ARTIGO_ESTADO.get(R._limpo(uf).upper(), 'de')} {nome}" if nome else ""


def tribunal_completo(sigla):
    """"TJSE" -> "Tribunal de Justiça do Estado de Sergipe"; sigla desconhecida volta como está."""
    t = R._sem_acento(sigla).replace(" ", "").replace("-", "")
    m = re.fullmatch(r"TJ([A-Z]{2})", t)
    if m and m.group(1) == "DF" or t == "TJDFT":
        return "Tribunal de Justiça do Distrito Federal e dos Territórios"
    if m and m.group(1) in ESTADOS:
        return f"Tribunal de Justiça do Estado {de_estado(m.group(1))}"
    m = re.fullmatch(r"TRF(\d)", t)
    if m:
        return f"Tribunal Regional Federal da {m.group(1)}ª Região"
    m = re.fullmatch(r"TRT(\d+)", t)
    if m:
        return f"Tribunal Regional do Trabalho da {m.group(1)}ª Região"
    return R._limpo(sigla)


def _nome_tribunal(sigla):
    c = tribunal_completo(sigla)
    return f"{c} ({sigla})" if c and c != sigla else sigla


def _papel_parte(lista, padrao):
    """Papel (requerido, executado...) da primeira parte da lista, com acento e em minúsculas."""
    if lista and lista[0][0]:
        return " ".join(ACENTOS.get(R._sem_acento(w), w.lower()).lower() for w in lista[0][0].split())
    return padrao


def bloco_processo(i, x, nome):
    """Um processo, sempre na mesma ordem e com as mesmas frases; só mudam os campos."""
    ativo, passivo = R.partes(x.get("ativo")), R.partes(x.get("passivo"))
    autor = _nomes(ativo) or "Parte autora não informada"
    reu = _nomes(passivo) or "parte ré não informada"
    emoji = EMOJI[i] if i < len(EMOJI) else f"{i}."
    numero = R.cnj(x.get("numero", ""))
    tribunal = R._limpo(x.get("tribunal"))
    classe = texto(x.get("acao")) or texto(x.get("ramo")) or "natureza não informada"
    data = _data_br(x)
    comarca, uf, _ = _onde(x)
    linhas = [f"*{emoji} {autor} x {reu}*"]
    linhas.append(f"*Processo nº {numero or 'não informado'}" + (f" — {tribunal}" if tribunal else "") + "*")
    local = (f", na Comarca de *{comarca}{', Estado ' + (de_estado(uf) or 'de ' + uf) if uf else ''}*" if comarca else
             (f", no Estado *{de_estado(uf) or 'de ' + uf}*" if uf else ""))
    linhas.append(f"Trata-se de um processo de *{classe}*" + (f", distribuído em *{data}*" if data else "") + local
                  + (f", perante o {tribunal_completo(tribunal)}" if tribunal else "") + ".")
    rotulo, expl = _papel(x)
    if rotulo:
        polo = x.get("polo")
        outro = _nomes(passivo if polo == "Polo ativo" else ativo) if polo in ("Polo ativo", "Polo passivo") else ""
        outro_papel = _papel_parte(passivo if polo == "Polo ativo" else ativo,
                                   "parte ré" if polo == "Polo ativo" else "parte autora")
        varios = len(passivo if polo == "Polo ativo" else ativo) > 1
        if varios and not outro_papel.endswith("s"):
            outro_papel += "es" if outro_papel.endswith(("r", "z")) else "s"
        contra = f", enquanto *{outro} {'figuram' if varios else 'figura'} como {outro_papel}*" if outro else ""
        linhas.append(f"Nesse processo, *{nome} figura como {rotulo}*{contra}.")
    else:
        linhas.append(f"Pelos registros consultados, não foi possível confirmar a posição de *{nome}* neste processo.")
    sit_rotulo, _ = _situacao_rotulo(x)
    ia = explicacao_ia.paragrafo(classe, rotulo, sit_rotulo) if rotulo else ""
    if ia:  # parágrafo do Gemini (sem dados pessoais); no lugar da explicação fixa
        linhas.append(ia)
    else:
        exp = _explica_classe(classe) or explicacao_ia.explicar(classe)
        if exp:
            linhas.append(f"Esse tipo de processo é {exp}.")
        if "EXEQUENTE" in R._sem_acento(rotulo):
            linhas.append("É importante esclarecer que *figurar como exequente não significa estar sendo cobrado por uma "
                          "dívida*. Pelo contrário, nessa posição processual, a pessoa atua buscando o cumprimento da "
                          "obrigação por parte de quem deve cumpri-la.")
    linhas.append("A pesquisa registra a existência do processo e identifica as partes envolvidas, mas não apresenta o "
                  "conteúdo da petição inicial, os valores eventualmente solicitados, as provas produzidas ou a "
                  "fundamentação das decisões judiciais.")
    linhas += _andamento(x)
    linhas.append("Entretanto, não foram disponibilizados a sentença ou os demais documentos necessários para identificar "
                  "o resultado do pedido ou o motivo específico do andamento atual.")
    _, k = _situacao_rotulo(x)
    fim = {"arq_def": "o registro disponível aponta seu *arquivamento definitivo*",
           "arq": "o registro disponível aponta que ele está *arquivado*",
           "baixa": "o registro disponível aponta que ele recebeu *baixa*",
           "extinto": "o registro disponível aponta que ele foi *extinto*",
           "susp": "o registro disponível aponta que ele está *suspenso*",
           "tram": "o registro disponível aponta que ele *consta como em tramitação*",
           "nd": "a situação atual não consta nos registros disponíveis"}[k]
    verbo = "participou" if k in ("arq_def", "arq", "baixa", "extinto") else "participa"
    posicao = (f"{verbo} desse processo na condição de *{rotulo}* em processo de *{classe}*" if rotulo
               else "consta nos registros desse processo")
    linhas.append(f"*Conclusão:* {nome} {posicao}, e {fim}. Não há, na documentação apresentada, informação que "
                  "permita afirmar a existência de condenação contra o pesquisado.")
    return "\n\n".join(linhas)


def _tribunais(ps):
    nomes = []
    for x in ps:
        t = R._limpo(x.get("tribunal"))
        if t and t not in nomes:
            nomes.append(t)
    return nomes


def _abertura(p, ps, nome, atendente):
    n = len(ps)
    doc = R.formatar_doc(p["doc"]) if p.get("doc") else ""
    rot = "CPF" if len(R.so_digitos(p.get("doc"))) <= 11 else "CNPJ"
    verbo = "foi localizado" if n == 1 else "foram localizados"
    rel = "relacionado" if n == 1 else "relacionados"
    qtd = f"{n} ({NUMEROS[n]}) {'processo judicial' if n == 1 else 'processos judiciais'}" if n <= 20 else f"{n} processos judiciais"
    trib = _tribunais(ps)
    if len(trib) == 1:
        onde = f", {'vinculado' if n == 1 else 'todos vinculados'} ao *{_nome_tribunal(trib[0])}*"
    elif trib:
        onde = f", vinculados aos tribunais *{_lista(trib)}*"
    else:
        onde = ""
    return (f"*{atendente}:* Informamos que, após consulta aos registros processuais disponibilizados, {verbo} "
            f"*{qtd}* {rel} a *{nome}*" + (f", {rot} nº {doc}" if doc else "") + onde + ".")


def _panorama(ps, nome):
    """Período, natureza e quantos estão encerrados ou em tramitação (só com o cadastro)."""
    n = len(ps)
    out = []
    anos = sorted(a for a in (_ano(x) for x in ps) if a)
    naturezas = sorted({texto(x.get("ramo")).lower() for x in ps if R._limpo(x.get("ramo"))})
    if anos or naturezas:
        per = ""
        if anos:
            per = (f"iniciados {'em' if anos[0] == anos[-1] else 'entre os anos de'} "
                   f"*{anos[0]}{'' if anos[0] == anos[-1] else ' e ' + str(anos[-1])}*")
        nat = f"relacionados à área de {_lista(naturezas)}" if naturezas else ""
        out.append(f"Os registros identificados referem-se a processos {_lista([t for t in (per, nat) if t])}."
                   if n > 1 else f"O registro identificado refere-se a um processo {_lista([t for t in (per.replace('iniciados', 'iniciado'), nat.replace('relacionados', 'relacionado')) if t])}.")
    if n > 1:
        cont = {}
        for x in ps:
            r, k = _situacao_rotulo(x)
            cont[k] = cont.get(k, 0) + 1
        desc = []
        for k, t_um, t_var in (("arq_def", "registro de arquivamento definitivo", "registro de arquivamento definitivo"),
                               ("arq", "registro de arquivamento", "registro de arquivamento"),
                               ("baixa", "registro de baixa", "registro de baixa"),
                               ("extinto", "registro de extinção", "registro de extinção"),
                               ("susp", "registro de suspensão", "registro de suspensão"),
                               ("tram", "consta como em tramitação na base consultada", "constam como em tramitação na base consultada"),
                               ("nd", "está sem situação informada", "estão sem situação informada")):
            c = cont.get(k, 0)
            if c:
                nome_n = "todos" if c == n else NUMEROS[c] if c <= 20 else str(c)
                verbo = (("apresenta " if t_um.startswith("registro") else "") if c == 1 else
                         ("apresentam " if t_var.startswith("registro") else ""))
                desc.append(f"*{nome_n} {verbo}{t_um if c == 1 else t_var}*")
        out.append(f"Dos {NUMEROS[n] if n <= 20 else n} processos encontrados, {_lista(desc)}. "
                   "A seguir, apresentamos as informações individualizadas.")
    return out


def mensagem_pessoa(p, atendente=ATENDENTES[0]):
    ps, nome = p["processos"], (p["nome"] or R.formatar_doc(p["doc"])).strip()
    if not ps:
        return (f"*{atendente}:* Informamos que após consulta ao sistema do Poder Judiciário, não localizamos "
                f"*nenhum processo* em nome de *{nome}*.")
    partes = [_abertura(p, ps, nome, atendente)] + _panorama(ps, nome)
    for i, x in enumerate(ps, 1):
        partes.append(bloco_processo(i, x, nome))
    return "\n\n".join(partes)


def _sem_processo_confirmado(p):
    """Pessoa que o Sonar respondeu "não consta" (e não houve falha ao ler a planilha)."""
    return not p["processos"] and not p["aviso"] and "NAO CONSTA" in R._sem_acento(p["situacao"])


def gerar(pasta, pessoas, atendente=ATENDENTES[0], datajud=False):
    """mensagens_cac.json (para a página) e mensagens_cac.txt: uma mensagem por pessoa com processos ou com
    "não consta processo" confirmado. O parâmetro datajud ficou só por compatibilidade: o modelo atual não
    consulta tribunal nem API nenhuma."""
    msgs = [{"empresa": p["empresa"], "nome": p["nome"], "pedido": p["pedido"], "processos": len(p["processos"]),
             "texto": mensagem_pessoa(p, atendente)} for p in pessoas if p["processos"] or _sem_processo_confirmado(p)]
    pasta = Path(pasta)
    (pasta / "mensagens_cac.json").write_text(json.dumps({"atendentes": ATENDENTES, "mensagens": msgs}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    (pasta / "mensagens_cac.txt").write_text(
        (f"\n\n{SEPARADOR}\n\n".join(f"[{m['empresa']} · {m['nome']} · pedido S{m['pedido']}]\n\n{m['texto']}" for m in msgs)
         or "Nenhuma pessoa nesta pesquisa.") + "\n", encoding="utf-8")
    return msgs
