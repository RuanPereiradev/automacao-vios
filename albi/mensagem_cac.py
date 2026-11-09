"""Albi — mensagem no padrão da CAC (Central de Atendimento ao Cliente) para cada pessoa com processos.

Segue o modelo do escritório: abertura com a atendente ("*Beatriz Vasconcelos:* Informamos que,
após consulta aos sistemas do Poder Judiciário, foram localizados *dois processos*..."), um bloco
por processo ("*1️⃣ Autor x Réu*", "Trata-se de...", valor, situação atual) e, com mais de um
processo, um parágrafo de conclusão. Negrito no padrão do WhatsApp (*texto*).

Cada processo segue o roteiro do prompt da CAC, sem inteligência artificial (regras fixas):
  A) do que se trata (classe, número, data, vara, posição da pessoa) — planilha do Sonar;
  B) por que existe (o que é esse tipo de ação, assuntos cadastrados, valor da causa);
  C) acontecimentos com data (contestação, audiências, liminar, gratuidade, recursos) e
  D) decisões (sentença, recurso, embargos, trânsito em julgado, cumprimento, alvará) — movimentações
     oficiais da API pública do CNJ (datajud.py);
  E) situação atual (do movimento mais recente) e F) um resumo do processo.

REGRA: só o que está comprovado nos registros. O texto das petições e das decisões não está em
nenhuma das duas fontes: os fatos narrados (ex.: "trabalhava das 9h à meia-noite") e os fundamentos
não aparecem, e a ressalva final diz isso. Nunca diz que houve pagamento (alvará/requisição vêm
com a ressalva). Sem resposta do DataJud, o processo sai só com o cadastro do Sonar. Sem
"Sr./Sra.": o gênero não está nos dados (a atendente pode acrescentar ao revisar).
Escreve mensagens_cac.txt (para copiar) e mensagens_cac.json (para a página /albi).
"""
import json
import re
from pathlib import Path

import datajud as DJ
import relatorio as R

ATENDENTES = ("Beatriz Vasconcelos", "Renara Kathleem")
SEPARADOR = R.SEPARADOR
NUMEROS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
           "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove", "vinte"]
EMOJI = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
RESSALVA = ("*Ressaltamos que as informações acima se baseiam nos registros processuais disponíveis nas bases do "
            "Poder Judiciário consultadas (número, partes, classe, assunto, valor e situação), sem acesso ao conteúdo "
            "integral dos autos. Dessa forma, detalhes sobre os fatos, as decisões e eventuais pagamentos dependem da "
            "consulta direta a cada processo.*")
RESSALVA_DJ = ("*Ressaltamos que as informações acima se baseiam nos registros processuais públicos do Poder Judiciário "
               "(cadastro e movimentações oficiais de cada processo), sem acesso ao conteúdo integral dos autos. Dessa "
               "forma, os fatos narrados pelas partes, os fundamentos das decisões e eventuais pagamentos dependem da "
               "consulta direta a cada processo.*")

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


def _dj(x):
    """O andamento do DataJud deste processo (dict) ou None."""
    d = x.get("datajud")
    return d if d and not d.get("erro") else None


def _encerrado(x):
    d = _dj(x)
    return d["encerrado"] if d else x["encerrado"]


def _situacao_sonar(x):
    st = R._sem_acento(x.get("status"))
    if not st or st in R.VAZIO:
        return "A situação atual do processo não consta nos registros consultados."
    if "ARQUIV" in st:
        defin = "definitiv" if "DEFINITIV" in st else ""
        return (f"*Conforme o registro mais recente disponível, o processo encontra-se arquivado{' definitivamente' if defin else ''}*, "
                "ou seja, foi encerrado e enviado ao arquivo, sem movimentação ativa.")
    if "BAIXA" in st:
        return "*Conforme o registro mais recente disponível, o processo consta como baixado*, ou seja, encerrado no juízo em que tramitava."
    if "EXTIN" in st:
        return "*Conforme o registro mais recente disponível, o processo foi extinto*, ou seja, encerrado pela Justiça."
    if "SUSPEN" in st or "SOBREST" in st:
        return "*Conforme o registro mais recente disponível, o processo encontra-se suspenso*, aguardando a retomada da tramitação."
    if "TRAMIT" in st or "ANDAMENTO" in st or "ATIVO" in st or "NORMAL" in st:
        return "*Atualmente, o processo encontra-se em tramitação.*"
    return f"*Situação registrada no sistema: {texto(x.get('status'))}.*"


def _situacao_dj(d):
    br = DJ.br
    quando = f" ({br(d['situacao_data'])})" if d.get("situacao_data") else ""
    s = d["situacao"]
    txt = {
        "arquivado_def": f"*Conforme a movimentação mais recente registrada{quando}, o processo encontra-se arquivado "
                         "definitivamente*, ou seja, foi encerrado e enviado ao arquivo, sem movimentação ativa.",
        "arquivado": f"*Conforme a movimentação mais recente registrada{quando}, o processo encontra-se arquivado*, "
                     "sem movimentação ativa.",
        "arquivado_prov": f"*Conforme a movimentação mais recente registrada{quando}, o processo encontra-se arquivado "
                          "provisoriamente*, ou seja, está parado, mas pode ser retomado a pedido da parte.",
        "baixa": f"*Conforme a movimentação mais recente registrada{quando}, o processo recebeu baixa definitiva*, ou "
                 "seja, foi encerrado no juízo em que tramitava.",
        "suspenso": f"*Conforme a movimentação mais recente registrada{quando}, o processo encontra-se suspenso*, "
                    "aguardando a retomada da tramitação.",
        "aguarda_audiencia": "*Atualmente, o processo encontra-se em andamento, aguardando a realização da audiência.*",
        "cumprimento": "*Atualmente, o processo encontra-se em fase de cumprimento de sentença*, etapa em que se busca "
                       "cumprir ou cobrar o que foi decidido. Os registros não informam se já houve pagamento.",
        "transitado": "*A decisão já é definitiva (transitou em julgado)*, mas os registros não mostram o arquivamento do "
                      "processo; por isso, não é possível afirmar que ele esteja totalmente encerrado.",
        "recurso": ("*Atualmente, o processo encontra-se em fase de recurso*: o recurso já foi julgado, mas ainda não "
                    "consta o trânsito em julgado (decisão definitiva)." if d.get("recurso") else
                    "*Atualmente, o processo encontra-se em fase de recurso*, aguardando o julgamento pelo tribunal."),
        "sentenciado": "*O processo já tem sentença, mas ainda não consta o trânsito em julgado*, ou seja, a decisão "
                       "ainda pode ser objeto de recurso.",
        "aguarda_julgamento": "*Atualmente, o processo encontra-se em andamento, concluso (enviado ao juiz) para "
                              "julgamento.*",
        "tramitando": "*Atualmente, o processo encontra-se em tramitação*, ainda sem sentença registrada.",
    }[s]
    if d.get("atualizado"):
        txt += f" Informação conforme os registros do tribunal atualizados em {br(d['atualizado'])}."
    return txt


SITUACAO_CURTA = {"arquivado_def": "arquivado definitivamente", "arquivado": "arquivado",
                  "arquivado_prov": "arquivado provisoriamente", "baixa": "baixado", "suspenso": "suspenso",
                  "aguarda_audiencia": "em andamento, aguardando audiência",
                  "cumprimento": "em fase de cumprimento de sentença", "transitado": "com decisão definitiva",
                  "recurso": "em fase de recurso", "sentenciado": "com sentença, ainda sem trânsito em julgado",
                  "aguarda_julgamento": "aguardando julgamento", "tramitando": "em tramitação, ainda sem sentença"}


def _paragrafos(eventos, abertura, por_paragrafo=4):
    """[(data, frase)] -> parágrafos "Em dd/mm/aaaa, frase." (o primeiro começa com a abertura)."""
    frases = []
    for i, (dt, f) in enumerate(eventos):
        frase = f"Em *{DJ.br(dt)}*, {f}."
        if i == 0 and abertura:
            frase = f"{abertura}, em *{DJ.br(dt)}*, {f}."
        frases.append(frase)
    return [" ".join(frases[i:i + por_paragrafo]) for i in range(0, len(frases), por_paragrafo)]


def _desfavoravel(x):
    """Sentença registrada contra a pessoa pesquisada: ré com pedido aceito, ou autora com pedido negado."""
    d = _dj(x)
    if not d or not d.get("sentenca"):
        return False
    k = d["sentenca"][1]
    return (x["polo"] == "Polo passivo" and k in ("sentenca:procedente", "sentenca:parcial")) or \
           (x["polo"] == "Polo ativo" and k == "sentenca:improcedente")


def bloco_processo(i, x, nome):
    d = _dj(x)
    ativo, passivo = R.partes(x.get("ativo")), R.partes(x.get("passivo"))
    autor = _nomes(ativo) or "Parte autora não informada"
    reu = _nomes(passivo) or "parte ré não informada"
    emoji = EMOJI[i] if i < len(EMOJI) else f"{i}."
    linhas = [f"*{emoji} {autor} x {reu}*"]
    numero = R.cnj(x.get("numero", ""))
    classe = texto(x.get("acao")) or (d and d["classe"]) or texto(x.get("ramo")) or "natureza não informada"
    ramo = texto(x.get("ramo"))
    data = R.data(x.get("distribuicao")) or (d and DJ.br(d["ajuizamento"])) or ""
    orgao = texto(x.get("orgao"), nome=True) or (d and texto(d["orgao"], nome=True)) or ""
    comarca = texto(re.split(r"\s+[-–]\s+", R._limpo(x.get("comarca")))[0], nome=True)  # "FORTALEZA - FORUM ..." -> Fortaleza
    comarca = re.sub(r"^Comarca de\s+", "", comarca, flags=re.I)
    if comarca and R._sem_acento(comarca) in R._sem_acento(orgao):  # a vara já diz a comarca
        comarca = ""
    uf = R._limpo(x.get("uf"))
    tribunal = R._limpo(x.get("tribunal"))
    onde = (f", perante {_artigo_orgao(orgao)}" if orgao else "") + \
           (f", na comarca de {comarca}{'/' + uf if uf else ''}" if comarca else (f"/{uf}" if uf and orgao else "")) + \
           (f" ({tribunal})" if tribunal else "")
    # A) do que se trata: classe, número, data, órgão e a posição da pessoa pesquisada
    polo, papel = x.get("polo"), (x.get("papel") or "")
    papel_txt = " ".join(ACENTOS.get(R._sem_acento(w), w.lower()).lower() for w in papel.split()) if papel else ""
    if polo in EXPLICA_POLO:
        contra = _nomes(passivo if polo == "Polo ativo" else ativo) if polo in ("Polo ativo", "Polo passivo") else ""
        lado = (f" e {contra} como {'parte ré' if polo == 'Polo ativo' else 'parte autora'}" if contra else "")
        quem = f"*na qual {nome} figura como {papel_txt or polo.lower()} ({EXPLICA_POLO[polo]}){lado}.*"
    else:
        quem = f"Pelos registros consultados, não foi possível confirmar a posição de *{nome}* neste processo."
    inst = R._limpo(x.get("instancia"))
    linhas.append(f"Trata-se de um processo de *{classe}*"
                  + (f" (área: {ramo})" if ramo and R._sem_acento(ramo) not in R._sem_acento(classe) else "")
                  + (f", nº {numero}" if numero else "")
                  + (f", iniciado em {data}" if data else "")
                  + onde + ", " + quem)
    # B) por que o processo existe: o que é a ação e os assuntos cadastrados pelo tribunal
    origem = []
    exp = _explica_classe(classe) or (d and _explica_classe(d["classe"]))
    if exp:
        origem.append(f"Esse tipo de processo é {exp}.")
    assuntos = (d and d["assuntos"]) or ([R._limpo(x.get("tema"))] if R._limpo(x.get("tema")) else [])
    if assuntos:
        lista = _lista([_assunto(a) for a in assuntos[:6]])
        if polo == "Polo ativo":
            origem.append(f"Conforme os assuntos cadastrados pelo tribunal, {nome} levou à Justiça questões "
                          f"relacionadas a: {lista}.")
        elif polo == "Polo passivo":
            origem.append(f"Conforme os assuntos cadastrados pelo tribunal, a ação contra {nome} trata de: {lista}.")
        else:
            origem.append(f"Conforme os assuntos cadastrados pelo tribunal, o processo trata de: {lista}.")
    v = R.valor(x.get("valor"), x.get("moeda"))
    if v:
        origem.append(f"O valor atribuído à ação foi de *{v}*, quantia correspondente aos pedidos apresentados, não "
                      "significando que esse valor já tenha sido reconhecido ou concedido pela Justiça.")
    if origem:
        linhas.append(" ".join(origem))
    extra = []
    if inst and "1" not in inst:
        extra.append(f"O registro consultado é da *{inst.lower()}*, ou seja, o processo está ou esteve em fase de recurso.")
    if R._sem_acento(x.get("segredo")) == "SIM" or (d and d["sigilo"]):
        extra.append("O processo tramita em *segredo de justiça*, o que limita o acesso às suas informações.")
    if any(k in R._sem_acento(x.get("ramo")) for k in ("CRIMIN", "PENAL")):
        extra.append("Importante: figurar em um processo criminal *não significa condenação*"
                     + ("." if d and d.get("sentenca") else "; os registros consultados não informam sentença ou resultado."))
    if extra:
        linhas.append(" ".join(extra))
    if d:
        # C) acontecimentos durante a tramitação, D) decisões, E) situação atual
        linhas += _paragrafos(d["fatos"], "Durante a tramitação")
        if d["audiencias_nao_realizadas"]:
            n = d["audiencias_nao_realizadas"]
            linhas.append(f"Ao longo do processo, {_quantos(n, 'audiência', 'audiências', feminino=True)} "
                          f"{'foi cancelada ou não chegou' if n == 1 else 'foram canceladas ou não chegaram'} a ser "
                          f"{'realizada' if n == 1 else 'realizadas'}.")
        if not d["fatos"] and not d["decisoes"]:
            linhas.append("Nos registros públicos do tribunal ainda não há movimentações relevantes além do início do processo.")
        linhas += _paragrafos(d["decisoes"], "Quanto às decisões" if d["fatos"] else "Durante a tramitação")
        linhas.append(_situacao_dj(d))
        sonar_enc = x["encerrado"]
        if R._limpo(x.get("status")) and sonar_enc != d["encerrado"]:
            linhas.append(f"Observação: no cadastro da pesquisa, o status informado é *{texto(x.get('status'))}*; a "
                          "informação acima é a mais recente registrada nas movimentações do tribunal.")
        # F) conclusão individual
        if d.get("sentenca"):
            res = f"foi registrada sentença de *{DJ.SENTENCA[d['sentenca'][1]]}*"
            if d.get("recurso"):
                res += f", e houve julgamento de recurso (*{DJ.RECURSO[d['recurso'][1]]}*)"
            if d.get("transito"):
                res += ", com trânsito em julgado"
        else:
            res = "ainda não há sentença registrada"
        papel_curto = papel_txt or {"Polo ativo": "parte autora", "Polo passivo": "parte ré"}.get(polo, "parte")
        linhas.append(f"Em resumo, neste processo {nome} figura como *{papel_curto}*; {res}; e o processo está "
                      f"*{SITUACAO_CURTA[d['situacao']]}*.")
    else:
        motivo = (" porque o processo tramita em segredo de justiça" if R._sem_acento(x.get("segredo")) == "SIM" else
                  " no momento da consulta" if (x.get("datajud") or {}).get("erro", "").startswith(("tempo", "HTTP", "es_", "{"))
                  else "")
        if x.get("datajud"):
            linhas.append(f"As movimentações deste processo não estavam disponíveis na base pública do CNJ{motivo}; por "
                          "isso, não é possível informar aqui as decisões e os acontecimentos da tramitação.")
        linhas.append(_situacao_sonar(x))
    return "\n\n".join(linhas)


def mensagem_pessoa(p, atendente=ATENDENTES[0]):
    ps, nome = p["processos"], (p["nome"] or R.formatar_doc(p["doc"])).strip()
    n = len(ps)
    verbo = "foi localizado" if n == 1 else "foram localizados"
    rel = "relacionado" if n == 1 else "relacionados"
    partes = [f"*{atendente}:* Informamos que, após consulta aos sistemas do Poder Judiciário, {verbo} "
              f"*{_quantos(n, 'processo', 'processos')}* {rel} a *{nome}.*"]
    for i, x in enumerate(ps, 1):
        partes.append(bloco_processo(i, x, nome))
    com_dj = [x for x in ps if _dj(x)]
    if n > 1:
        andam = sum(1 for x in ps if not _encerrado(x))
        enc = n - andam
        pol = {}
        for x in ps:
            pol[x["polo"]] = pol.get(x["polo"], 0) + 1
        posicoes = []
        for k, t in (("Polo passivo", "como parte ré (polo passivo)"), ("Polo ativo", "como autor(a)"),
                     ("Outra parte", "como outra parte interessada"), ("Advogado(a)", "como advogado(a)"),
                     ("Não identificado", "sem posição confirmada nos registros")):
            if pol.get(k):
                posicoes.append(f"{_quantos(pol[k], 'processo', 'processos')} {t}")
        naturezas = sorted({texto(x.get("ramo")).lower() for x in ps if R._limpo(x.get("ramo"))})
        concl = (f"Em resumo, foram localizados *{_quantos(n, 'processo', 'processos')}* relacionados a *{nome}*"
                 + (f", nas áreas de {_lista(naturezas)}" if naturezas else "")
                 + ". " + (f"{nome} figura em {_lista(posicoes)}. " if posicoes else "")
                 + "Pelos registros mais recentes, "
                 + ("*todos estão em andamento*. " if not enc else "*todos constam como encerrados ou arquivados*. "
                    if not andam else f"*{NUMEROS[andam] if andam <= 20 else andam} {'está' if andam == 1 else 'estão'} "
                    f"em andamento* e *{NUMEROS[enc] if enc <= 20 else enc} {'consta' if enc == 1 else 'constam'} como "
                    f"{'encerrado ou arquivado' if enc == 1 else 'encerrados ou arquivados'}*. "))
        contra = [x for x in ps if _desfavoravel(x)]
        if contra:
            quais = _lista([(texto(x.get("acao")) or "processo") + " nº " + R.cnj(x.get("numero", "")) for x in contra])
            concl += (f"Há sentença registrada desfavorável a {nome} em *{_quantos(len(contra), 'processo', 'processos')}* "
                      f"({quais}), "
                      "conforme descrito acima.")
        elif len(com_dj) == n:
            concl += "Nos registros consultados, não foi identificada sentença desfavorável a " + nome + "."
        else:
            concl += ("Para os processos sem movimentações disponíveis, não é possível afirmar, com base nos registros, "
                      "se houve condenação ou resultado desfavorável.")
        partes.append(concl)
    partes.append(RESSALVA_DJ if com_dj else RESSALVA)
    return "\n\n".join(partes)


def gerar(pasta, pessoas, atendente=ATENDENTES[0], datajud=True):
    """mensagens_cac.json (para a página) e mensagens_cac.txt: uma mensagem por pessoa com processos.
    Com datajud=True, antes busca as movimentações de cada processo na API pública do CNJ (datajud.py)."""
    if datajud:
        try:
            DJ.enriquecer(pasta, pessoas)
        except Exception as e:  # a mensagem nunca deixa de sair por causa do DataJud
            print(f"DataJud: consulta não feita ({e})")
    msgs = [{"empresa": p["empresa"], "nome": p["nome"], "pedido": p["pedido"], "processos": len(p["processos"]),
             "texto": mensagem_pessoa(p, atendente)} for p in pessoas if p["processos"]]
    pasta = Path(pasta)
    (pasta / "mensagens_cac.json").write_text(json.dumps({"atendentes": ATENDENTES, "mensagens": msgs}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    (pasta / "mensagens_cac.txt").write_text(
        (f"\n\n{SEPARADOR}\n\n".join(f"[{m['empresa']} · {m['nome']} · pedido S{m['pedido']}]\n\n{m['texto']}" for m in msgs)
         or "Nenhuma pessoa com processos nesta pesquisa.") + "\n", encoding="utf-8")
    return msgs
