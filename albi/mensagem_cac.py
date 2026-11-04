"""Albi — mensagem no padrão da CAC (Central de Atendimento ao Cliente) para cada pessoa com processos.

Segue o modelo do escritório: abertura com a atendente ("*Beatriz Vasconcelos:* Informamos que,
após consulta aos sistemas do Poder Judiciário, foram localizados *dois processos*..."), um bloco
por processo ("*1️⃣ Autor x Réu*", "Trata-se de...", valor, situação atual) e, com mais de um
processo, um parágrafo de conclusão. Negrito no padrão do WhatsApp (*texto*).

REGRA: só o que está comprovado na planilha do Sonar (número, data, vara, comarca, classe, ramo,
assunto, partes e o papel de cada uma, valor da causa e situação). O Sonar não traz os fatos, as
movimentações nem as decisões; por isso a mensagem leva a ressalva de que os autos não foram
consultados, e nunca diz que houve condenação, pagamento ou resultado. Sem "Sr./Sra.": o gênero
não está nos dados (a atendente pode acrescentar ao revisar).
Escreve mensagens_cac.txt (para copiar) e mensagens_cac.json (para a página /albi).
"""
import json
import re
from pathlib import Path

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
    "CEARA": "Ceará", "SAO": "São", "JOAO": "João", "AGUA": "água", "ATOS": "atos", "MINISTERIO": "Ministério", "PUBLICO": "público", "CAFE": "café", "ORGAO": "órgão",
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


def _situacao(x):
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


def bloco_processo(i, x, nome):
    ativo, passivo = R.partes(x.get("ativo")), R.partes(x.get("passivo"))
    autor = _nomes(ativo) or "Parte autora não informada"
    reu = _nomes(passivo) or "parte ré não informada"
    emoji = EMOJI[i] if i < len(EMOJI) else f"{i}."
    linhas = [f"*{emoji} {autor} x {reu}*"]
    numero = R.cnj(x.get("numero", ""))
    classe = texto(x.get("acao")) or texto(x.get("ramo")) or "natureza não informada"
    ramo = texto(x.get("ramo"))
    data = R.data(x.get("distribuicao"))
    orgao = texto(x.get("orgao"), nome=True)
    comarca = texto(re.split(r"\s+[-–]\s+", R._limpo(x.get("comarca")))[0], nome=True)  # "FORTALEZA - FORUM ..." -> Fortaleza
    comarca = re.sub(r"^Comarca de\s+", "", comarca, flags=re.I)
    if comarca and R._sem_acento(comarca) in R._sem_acento(orgao):  # a vara já diz a comarca
        comarca = ""
    uf = R._limpo(x.get("uf"))
    tribunal = R._limpo(x.get("tribunal"))
    onde = (f", perante {_artigo_orgao(orgao)}" if orgao else "") + \
           (f", na comarca de {comarca}{'/' + uf if uf else ''}" if comarca else (f"/{uf}" if uf and orgao else "")) + \
           (f" ({tribunal})" if tribunal else "")
    # papel da pessoa pesquisada (pelo CPF nas partes) e a outra parte
    polo, papel = x.get("polo"), (x.get("papel") or "")
    papel_txt = " ".join(ACENTOS.get(R._sem_acento(w), w.lower()).lower() for w in papel.split()) if papel else ""
    if polo in EXPLICA_POLO:
        contra = _nomes(passivo if polo == "Polo ativo" else ativo) if polo in ("Polo ativo", "Polo passivo") else ""
        lado = (f" e {contra} como {'parte ré' if polo == 'Polo ativo' else 'parte autora'}" if contra else "")
        quem = f"*na qual {nome} figura como {papel_txt or polo.lower()} ({EXPLICA_POLO[polo]}){lado}.*"
    else:
        quem = f"Pelos registros consultados, não foi possível confirmar a posição de *{nome}* neste processo."
    inst = R._limpo(x.get("instancia"))
    abre = (f"Trata-se de um processo de *{classe}*"
            + (f" (área: {ramo})" if ramo and R._sem_acento(ramo) not in R._sem_acento(classe) else "")
            + (f", nº {numero}" if numero else "")
            + (f", iniciado em {data}" if data else "")
            + onde + ", " + quem)
    linhas.append(abre)
    extra = []
    assunto = texto(x.get("tema"))
    if assunto:
        extra.append(f"Segundo os registros do Poder Judiciário, o assunto cadastrado no processo é: *{assunto}*.")
    if inst and "1" not in inst:
        extra.append(f"O registro consultado é da *{inst.lower()}*, ou seja, o processo está ou esteve em fase de recurso.")
    if R._sem_acento(x.get("segredo")) == "SIM":
        extra.append("O processo tramita em *segredo de justiça*, o que limita o acesso às suas informações.")
    if any(d in R._sem_acento(x.get("ramo")) for d in ("CRIMIN", "PENAL")):
        extra.append("Importante: figurar em um processo criminal *não significa condenação*; os registros consultados "
                     "não informam se houve denúncia, sentença ou resultado.")
    v = R.valor(x.get("valor"), x.get("moeda"))
    if v:
        extra.append(f"O valor atribuído à ação foi de *{v}*, quantia correspondente aos pedidos apresentados, não "
                     "significando que esse valor já tenha sido reconhecido ou concedido pela Justiça.")
    if extra:
        linhas.append(" ".join(extra))
    linhas.append(_situacao(x))
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
    if n > 1:
        andam = sum(1 for x in ps if not x["encerrado"])
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
                 + (f", nas áreas de {', '.join(naturezas[:-1]) + ' e ' + naturezas[-1] if len(naturezas) > 1 else naturezas[0]}" if naturezas else "")
                 + ". " + (f"{nome} figura em {', '.join(posicoes[:-1]) + ' e ' + posicoes[-1] if len(posicoes) > 1 else posicoes[0]}. " if posicoes else "")
                 + f"Pelos registros mais recentes, *{andam} {'está' if andam == 1 else 'estão'} em tramitação* e "
                   f"*{enc} {'consta' if enc == 1 else 'constam'} como encerrado(s) ou arquivado(s)*. "
                 + "Os registros consultados não trazem o teor das decisões; por isso, não é possível afirmar, com base "
                   "neles, se houve condenação ou resultado desfavorável.")
        partes.append(concl)
    partes.append(RESSALVA)
    return "\n\n".join(partes)


def gerar(pasta, pessoas, atendente=ATENDENTES[0]):
    """mensagens_cac.json (para a página) e mensagens_cac.txt: uma mensagem por pessoa com processos."""
    msgs = [{"empresa": p["empresa"], "nome": p["nome"], "pedido": p["pedido"], "processos": len(p["processos"]),
             "texto": mensagem_pessoa(p, atendente)} for p in pessoas if p["processos"]]
    pasta = Path(pasta)
    (pasta / "mensagens_cac.json").write_text(json.dumps({"atendentes": ATENDENTES, "mensagens": msgs}, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    (pasta / "mensagens_cac.txt").write_text(
        (f"\n\n{SEPARADOR}\n\n".join(f"[{m['empresa']} · {m['nome']} · pedido S{m['pedido']}]\n\n{m['texto']}" for m in msgs)
         or "Nenhuma pessoa com processos nesta pesquisa.") + "\n", encoding="utf-8")
    return msgs
