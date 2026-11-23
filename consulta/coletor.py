"""Uma consulta, do pedido cifrado ao JSON do resultado (CONTRATO.md, seção 3).

Log: só id do pedido, status e tempos. Exceção desconhecida entra no log só pelo NOME da classe (a
mensagem do Selenium pode trazer o endereço com o CPF).
"""
import logging
import time
from dataclasses import dataclass
from datetime import date

from consulta import fases, leitura as lei, montagem
from consulta.cripto import CriptoErro, decifrar_cpf, formatar_cpf, hashes_telefones
from consulta.erros import ConsultaErro, SessaoPerdida
from consulta.fases import DESCONHECIDA
from nucleo import vios

log = logging.getLogger("consulta")


@dataclass
class Opcoes:
    chave_telefone: str
    formato_cpf: str = "mascara"       # como o CPF vai nos filtros do VIOS: "mascara" (000.000.000-00) ou "digitos"
    exigir_eco_cpf: bool = True        # a lista tem que mostrar pesq[cpfcnpj] com o CPF pedido
    max_pessoas: int = 5               # cadastros abertos por CPF; mais que isso = erro
    limite_lista: int = lei.LIMITE_LISTA


def _cpf_no_filtro(cpf, op):
    return formatar_cpf(cpf) if op.formato_cpf == "mascara" else cpf


def consultar(cpf, fonte, op, hoje, mapa, pedido_id, agora=None):
    """CPF (só dígitos, validado) -> dict do resultado. Levanta ConsultaErro (vira status "erro") e
    SessaoPerdida (o laço entra de novo no VIOS e repete)."""
    cpf_f = _cpf_no_filtro(cpf, op)

    # 2. processos ativos do CPF
    lista = lei.ler_lista_processos(fonte.lista_processos(cpf_f))
    if lista.cpf_no_filtro is None and op.exigir_eco_cpf:
        raise ConsultaErro("a lista de processos não mostrou o filtro de CPF aplicado (tela mudou?)")
    if lista.cpf_no_filtro is not None and lista.cpf_no_filtro != cpf:
        raise ConsultaErro("a lista de processos veio com outro CPF no filtro")
    if len(lista.processos) >= op.limite_lista:
        raise ConsultaErro("a lista veio cheia (o filtro de CPF pode não ter sido aplicado)")
    if not lista.processos:
        return montagem.montar_resultado(pedido_id, "nao_encontrado", agora=agora)

    # 3. pessoa e telefones (formulário lido sem enviar)
    ids = lei.ler_ids_pessoas(fonte.lista_pessoas(cpf_f))
    if not ids:
        return montagem.montar_resultado(pedido_id, "nao_encontrado", agora=agora)
    if len(ids) > op.max_pessoas:
        raise ConsultaErro("cadastros demais para o mesmo CPF")
    telefones = []
    for pessoa_id in ids:
        cadastro = lei.ler_form_pessoa(fonte.form_pessoa(pessoa_id))
        if cadastro.cpf != cpf:
            raise ConsultaErro("o CPF do cadastro não confere com o pedido")
        telefones += cadastro.telefones
    hashes = hashes_telefones(op.chave_telefone, telefones)

    # 4. fase de cada processo
    processos, lidas = [], 0
    for n, p in enumerate(lista.processos, 1):
        try:
            leit, textos = fonte.ficha(p.ci)
        except SessaoPerdida:
            raise
        except vios.BloqueioInativo:
            raise
        except Exception as e:  # noqa: BLE001 — uma ficha ruim não derruba as outras
            log.warning("ficha %d do pedido %s não lida (%s)", n, pedido_id, e.__class__.__name__)
            leit, textos = None, []
        if leit is not None and not leit.erro and leit.achou_tabela:
            lidas += 1
        d = fases.decidir(leit, hoje, mapa, segredo=p.segredo or lei.tem_segredo(textos))
        processos.append(montagem.montar_processo(n, p.area, d.fase, d.desde, d.proximo, d.encaminhar,
                                                    d.atualizacao))
    if not lidas:
        raise ConsultaErro("nenhuma ficha de processo foi lida (a tela mudou?)")
    return montagem.montar_resultado(pedido_id, "ok", processos, hashes, agora=agora)


def processar_pedido(pedido, chave_privada, fonte, op, mapa, hoje=None, agora=None):
    """Pedido do bot ({"id", "cpfCifrado"}) -> dict do resultado, sempre no contrato. Só SessaoPerdida
    e BloqueioInativo sobem (o laço decide); qualquer outra falha vira status "erro"."""
    inicio = time.monotonic()
    pid = pedido["id"]
    hoje = hoje or date.today()
    try:
        cpf = decifrar_cpf(pedido["cpfCifrado"], chave_privada)
        resultado = consultar(cpf, fonte, op, hoje, mapa, pid, agora)
    except (SessaoPerdida, vios.BloqueioInativo):
        raise
    except (CriptoErro, ConsultaErro) as e:
        log.warning("pedido %s: erro (%s)", pid, e)
        resultado = montagem.montar_resultado(pid, "erro", agora=agora)
    except Exception as e:  # noqa: BLE001
        log.warning("pedido %s: erro inesperado (%s)", pid, e.__class__.__name__)
        resultado = montagem.montar_resultado(pid, "erro", agora=agora)
    log.info("pedido %s: %s em %.1f s", pid, resultado["status"], time.monotonic() - inicio)
    return resultado
