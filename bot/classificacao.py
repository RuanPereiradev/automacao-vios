"""Classifica as tarefas do calendário: previdenciária (processa), ignorada ou ambígua.

O termo do CALENDARIO_FILTRO (padrão PREVIDENCI) é necessário, mas não basta:
- previdência privada/complementar é matéria cível: ignorada;
- termo de outra área junto (cível, trabalhista...): ambígua, não é processada;
- sinal previdenciário sem o termo (INSS, BPC/LOAS...): ambígua, não é processada.
Ambígua sempre vai para o relatório para conferência manual.
"""
import re

from bot.vios import normalizar

PREVIDENCIARIA, IGNORADA, AMBIGUA = "previdenciaria", "ignorada", "ambigua"

# previdência privada/complementar (LC 109/2001): não é previdência social
PRIVADA = [
    (r"\bPREVIDENCIA\S*\s+(?:PRIVADA|COMPLEMENTAR)", "previdência privada/complementar"),
    (r"\bPRIVAD[AO]S?\b", "termo 'privada'"),
    (r"\bCOMPLEMENTAR\b", "termo 'complementar'"),
    (r"\bFUNDOS?\s+DE\s+PENSAO\b", "fundo de pensão"),
    (r"\bENTIDADE\s+(?:FECHADA|ABERTA)\b", "entidade de previdência complementar"),
    (r"\b(?:PGBL|VGBL|PREVI|PETROS|FUNCEF|POSTALIS)\b", "plano ou fundo de previdência complementar"),
]

# outra área do direito no mesmo texto: pode não ser previdenciária
OUTRA_AREA = [
    (r"\bCIVE[LI]S?\b|\bCIVI[LS]\b", "cível"),
    # "trabalhador rural" é previdenciário: só os termos da área trabalhista
    (r"\bTRABALHISTA|\b(?:JUSTICA|DIREITO|ACIDENTES?)\s+D[EO]\s+TRABALHO\b", "trabalhista/acidente de trabalho"),
    (r"\bFAMILIA\b", "família"),
    (r"\bCRIMINA[LI]S?\b|\bPENA[LI]S?\b", "criminal"),
    (r"\bTRIBUTARI", "tributária"),
    (r"\bCONSUMIDOR", "consumidor"),
    (r"\bBANCARI", "bancária"),
    (r"\bEMPRESARIA", "empresarial"),
]

# indicam previdência social, mas sem regra confirmada para processar sem o termo do filtro
SINAIS = [
    (r"\bINSS\b", "INSS"),
    (r"\bBPC\b|\bLOAS\b", "BPC/LOAS"),
    (r"\bAPOSENTADORIA", "aposentadoria"),
    (r"\bAUXILIO\W*(?:DOENCA|ACIDENTE|RECLUSAO|INCAPACIDADE)", "auxílio"),
    (r"\bPENSAO\s+POR\s+MORTE\b", "pensão por morte"),
    (r"\bSALARIO\W*MATERNIDADE\b", "salário-maternidade"),
    (r"\bBENEFICIO\s+POR\s+INCAPACIDADE\b", "benefício por incapacidade"),
]


def _achados(regras, texto):
    return [motivo for regex, motivo in regras if re.search(regex, texto)]


def classificar(texto, termo="PREVIDENCI", tipo=""):
    """(classe, motivo) da tarefa. Só a classe PREVIDENCIARIA é processada. Com `tipo`, a
    previdenciária que não é desse tipo de tarefa vira ignorada."""
    classe, motivo = _classificar(texto, termo)
    if classe == PREVIDENCIARIA and tipo and normalizar(tipo) not in normalizar(texto):
        return IGNORADA, f"previdenciária, mas não é tarefa '{tipo}'"
    return classe, motivo


def _classificar(texto, termo):
    t = normalizar(texto)
    tem_termo = normalizar(termo) in t
    privada = _achados(PRIVADA, t)
    if privada:
        return IGNORADA, "previdência privada/complementar (matéria cível): " + ", ".join(privada)
    outras = _achados(OUTRA_AREA, t)
    sinais = _achados(SINAIS, t)
    if not tem_termo:
        if sinais:
            return AMBIGUA, (f"sem '{termo}', mas com {', '.join(sinais)}"
                             + (f" e termo de outra área ({', '.join(outras)})" if outras else "")
                             + ": conferir manualmente")
        return IGNORADA, f"sem '{termo}' no texto da tarefa"
    if outras:
        return AMBIGUA, f"'{termo}' junto com termo de outra área ({', '.join(outras)}): conferir manualmente"
    return PREVIDENCIARIA, f"contém '{termo}' e nenhum termo de exclusão"
