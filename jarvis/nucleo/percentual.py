"""Percentual ganho: quanto o cliente poderia ter perdido × quanto pagou (regras da controladoria, 23/11/2026).

Por processo:
- poderia perder = valor que o AUTOR pediu ("Valor da ação" do cadastro; vazio -> o valor que a IA acha
  nos comentários);
- pagou = só condenação e acordo (custas e honorários NÃO entram);
- economia = pedido - pago.

Entram no índice só os processos em que o cliente é RÉU (polo passivo) e que já têm o valor definido:
encerrados ou pagos, com sentença/decisão de valor conhecido, ou acordo (o total do acordo, mesmo em
parcelas). Sem decisão: fora do índice, mostrados à parte ("em discussão"). Universo: todos os processos
do grupo, ativos e encerrados (relatório de comentários do VIOS, nucleo/comentarios.py).

Os valores vêm do texto (comentários das tarefas), pela IA, com o trecho de origem para conferência.
Processo encerrado não muda: o resultado fica guardado (cache) e não é lido de novo nos meses seguintes.
"""
import json
import logging
import re
from datetime import datetime

from nucleo.relatorio_planilha import _valor, limpar, motivo_erro

log = logging.getLogger(__name__)

SITUACOES = [
    "Improcedente ou extinto sem pagamento",
    "Condenação com valor definido",
    "Acordo",
    "Sem decisão",
    "Indefinido",
]
NO_INDICE = SITUACOES[:3]

# status de cada processo na aba de conferência
ST_INDICE = "No índice"
ST_DISCUSSAO = "Em discussão (sem decisão)"
ST_SEM_VALOR = "Sem valor registrado no VIOS"
ST_AUTOR = "Cliente é autor (fora do índice)"
ST_SEM_POLO = "Polo do cliente não informado"
ST_ERRO = "Erro na IA"

SISTEMA = f"""Você recebe UM processo do escritório de advocacia (sistema VIOS) em que o cliente do
escritório é o RÉU: o cadastro e os comentários que a equipe registrou nas tarefas, em ordem de data.
Extraia os valores para um índice financeiro. Responda só com o JSON pedido.

Campos:
- situacao: desta lista: {", ".join(SITUACOES)}.
  "Improcedente ou extinto sem pagamento" = os pedidos do autor foram negados, o processo foi extinto ou
  arquivado e o cliente NÃO pagou nada (nem condenação nem acordo).
  "Condenação com valor definido" = sentença, acórdão ou decisão administrativa condenou o cliente a pagar
  um valor conhecido (mesmo que em parte, mesmo que ainda caiba recurso: use a decisão mais recente).
  "Acordo" = o cliente fez acordo com o autor (pago ou em parcelas).
  "Sem decisão" = ainda não há decisão nem acordo.
  "Indefinido" = há decisão ou encerramento, mas não dá para saber o resultado pelos comentários.
- valor_pedido: o valor TOTAL que o autor pediu na ação (soma dos pedidos: danos morais, materiais,
  devolução, multa pedida etc.), só números com ponto decimal (ex.: "15000.00"). "" se não aparecer.
- trecho_pedido: o trecho do comentário de onde tirou o valor pedido (até 200 caracteres). "" se vazio.
- valor_pago: o valor que o cliente pagou ou foi condenado a pagar: SÓ condenação e acordo. NÃO some
  custas processuais, honorários advocatícios/sucumbenciais, depósito recursal nem guias de recurso.
  Condenação com várias parcelas (ex.: devolução + danos morais): some. Acordo em parcelas: o total do
  acordo. "0.00" quando a situação for "Improcedente ou extinto sem pagamento". "" se não aparecer.
- trecho_pago: o trecho do comentário de onde tirou o valor pago (até 200 caracteres). "" se vazio.

Regras:
- Use só o que está no texto; não invente nem estime valores.
- Valores em reais, sem "R$", sem separador de milhar (ex.: "1800.00").
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "situacao": {"type": "string", "enum": SITUACOES},
        "valor_pedido": {"type": "string"},
        "trecho_pedido": {"type": "string"},
        "valor_pago": {"type": "string"},
        "trecho_pago": {"type": "string"},
    },
    "required": ["situacao", "valor_pedido", "trecho_pedido", "valor_pago", "trecho_pago"],
    "additionalProperties": False,
}

MAX_COMENTARIO = 3000
INICIO, FIM = 12000, 28000  # o pedido costuma estar no começo e o resultado no fim


def _numero(texto):
    """'15000.00' (formato pedido à IA) ou 'R$ 15.000,00' (cadastro) -> float; vazio/erro -> None."""
    t = (texto or "").strip()
    if not t:
        return None
    if re.fullmatch(r"-?\d+(\.\d+)?", t):
        return float(t)
    return _valor(t)


def eh_reu(polo):
    return "passiv" in (polo or "").lower()


def eh_autor(polo):
    return "ativ" in (polo or "").lower()


def texto_para_ia(ci, cadastro, coment):
    """cadastro = Dados do Processo (lupa); coment = processo do relatório de comentários."""
    linhas = [f"CI: {ci}"]
    for rotulo in ("N.° CNJ", "Área", "Ação", "Fase", "Valor da ação", "Polo do cliente", "Cidade / UF"):
        if cadastro.get(rotulo):
            linhas.append(f"{rotulo}: {cadastro[rotulo]}")
    if coment.get("observacao"):
        linhas.append(f"Observação do processo: {limpar(coment['observacao'])}")
    linhas.append("\nCOMENTÁRIOS (do mais antigo para o mais novo):")
    for c in coment.get("comentarios", []):
        texto = limpar(c["texto"])[:MAX_COMENTARIO]
        if texto:
            linhas.append(f"\n[{c['data'][:10]}] {texto}")
    texto = "\n".join(linhas)
    if len(texto) > INICIO + FIM:
        texto = texto[:INICIO] + "\n[...]\n" + texto[-FIM:]
    return texto


def classificar(ci, cadastro, coment, ia, ativo):
    """Linha da aba de conferência: valores, origem e status do processo no índice."""
    polo = cadastro.get("Polo do cliente", "")
    linha = {
        "CI": int(ci) if str(ci).isdigit() else ci,
        "Número do processo": (cadastro.get("N.° CNJ") or coment.get("numero", "")).replace("CNJ:", "").strip(),
        "Andamento": "Ativo" if ativo else "Encerrado",
        "Polo do cliente": polo,
        "Situação": "", "Valor pedido": None, "Origem do pedido": "", "Valor pago": None, "Origem do pago": "",
        "Economia": None, "Status no índice": "",
    }
    if eh_autor(polo):
        linha["Status no índice"] = ST_AUTOR
        return linha
    if not eh_reu(polo):
        linha["Status no índice"] = ST_SEM_POLO
        return linha
    if not ia or ia.get("erro"):
        linha["Status no índice"] = ST_ERRO
        linha["Situação"] = f"ERRO NA IA: conferir ({motivo_erro((ia or {}).get('erro', 'sem resposta'))})"
        return linha

    pedido_cadastro = _numero(cadastro.get("Valor da ação", ""))
    pedido_ia = _numero(ia["valor_pedido"])
    if pedido_cadastro:
        pedido, origem = pedido_cadastro, "Cadastro (Valor da ação)"
    elif pedido_ia:
        pedido, origem = pedido_ia, f"Comentários: {ia['trecho_pedido']}"
    else:
        pedido, origem = None, ""
    situacao = ia["situacao"]
    pago = 0.0 if situacao == SITUACOES[0] else _numero(ia["valor_pago"])
    linha.update({"Situação": situacao, "Valor pedido": pedido, "Origem do pedido": origem, "Valor pago": pago,
                  "Origem do pago": ia["trecho_pago"] if situacao != SITUACOES[0] else ""})
    if situacao in NO_INDICE and pedido and pago is not None:
        linha["Economia"] = pedido - pago
        linha["Status no índice"] = ST_INDICE
    elif situacao == "Sem decisão":
        linha["Status no índice"] = ST_DISCUSSAO
    else:
        linha["Status no índice"] = ST_SEM_VALOR
    return linha


def resumo(linhas):
    """Os números do quadro "Percentual ganho"."""
    dentro = [l for l in linhas if l["Status no índice"] == ST_INDICE]
    perder = sum(l["Valor pedido"] for l in dentro)
    pagou = sum(l["Valor pago"] for l in dentro)
    discussao = [l for l in linhas if l["Status no índice"] == ST_DISCUSSAO]
    return {
        "processos": len(linhas),
        "no_indice": len(dentro),
        "poderia_perder": perder,
        "pagou": pagou,
        "economia": perder - pagou,
        "percentual": (perder - pagou) / perder if perder else None,
        "em_discussao": len(discussao),
        "em_discussao_pedido": sum(l["Valor pedido"] or 0 for l in discussao),
        "sem_valor": sum(1 for l in linhas if l["Status no índice"] in (ST_SEM_VALOR, ST_ERRO)),
        "cliente_autor": sum(1 for l in linhas if l["Status no índice"] == ST_AUTOR),
        "sem_polo": sum(1 for l in linhas if l["Status no índice"] == ST_SEM_POLO),
    }


# --- cache dos encerrados ---
def ler_cache(arquivo):
    try:
        return json.loads(arquivo.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as e:
        log.warning("Cache do percentual ilegível (%s): começa do zero", e)
        return {}


def gravar_cache(arquivo, cache):
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def guardar(cache, ci, cadastro, ia):
    """Só processo encerrado, com cadastro lido e sem erro na IA (erro é refeito no mês seguinte).
    ia=None: processo que não vai para a IA (cliente autor ou polo vazio) — guarda só o cadastro."""
    if cadastro and (ia is None or not ia.get("erro")):
        cache[str(ci)] = {"cadastro": cadastro, "ia": ia, "lido_em": f"{datetime.now():%Y-%m-%d}"}
