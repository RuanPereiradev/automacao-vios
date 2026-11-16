"""CPF, telefone e assinatura: as partes do contrato (CONTRATO.md, seções 1, 2 e 7) que não tocam o VIOS.

Nada aqui escreve em log. O CPF e os telefones só existem em memória, durante o pedido.
"""
import base64
import binascii
import hashlib
import hmac
import os
import re
import stat
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


class CriptoErro(Exception):
    """Falha ao ler a chave ou decifrar. A mensagem nunca tem dado do cliente."""


# ---------------------------------------------------------------- CPF
def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def validar_cpf(texto):
    """True se tem 11 dígitos, não são todos iguais e os dois dígitos verificadores batem."""
    d = so_digitos(texto)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10 % 11) % 10
        if digito != int(d[tamanho]):
            return False
    return True


def formatar_cpf(texto):
    d = so_digitos(texto)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}" if len(d) == 11 else d


def calcular_digitos_cpf(base9):
    """Para gerar CPF de teste válido a partir de 9 dígitos."""
    d = [int(c) for c in base9]
    for tamanho in (9, 10):
        soma = sum(d[i] * (tamanho + 1 - i) for i in range(tamanho))
        d.append((soma * 10 % 11) % 10)
    return "".join(str(x) for x in d)


# ---------------------------------------------------------------- RSA-OAEP SHA-256
def carregar_chave_privada(caminho, exigir_permissao=True):
    """Lê o PEM sem senha. Com exigir_permissao, recusa arquivo legível por outros (modo 600)."""
    caminho = Path(caminho).expanduser()
    try:
        if exigir_permissao and os.name == "posix" and stat.S_IMODE(caminho.stat().st_mode) & 0o077:
            raise CriptoErro("a chave privada precisa ser legível só por você (chmod 600)")
        return serialization.load_pem_private_key(caminho.read_bytes(), password=None)
    except CriptoErro:
        raise
    except FileNotFoundError:
        raise CriptoErro("arquivo da chave privada não encontrado") from None
    except (ValueError, TypeError, OSError):
        raise CriptoErro("não consegui ler a chave privada (PEM sem senha esperado)") from None


def _oaep():
    # o bot (Node) cifra com oaepHash sha256: o MGF1 usa o mesmo hash
    return padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def cifrar_cpf(cpf, chave_publica):
    """Só para testes e para o bot falso do modo simulado (o bot de verdade cifra em Node)."""
    return base64.b64encode(chave_publica.encrypt(so_digitos(cpf).encode("ascii"), _oaep())).decode("ascii")


def decifrar_cpf(cpf_cifrado, chave_privada):
    """base64 -> CPF só com dígitos, já validado. CriptoErro se não decifra ou se o CPF é inválido."""
    try:
        bruto = base64.b64decode(cpf_cifrado or "", validate=True)
        texto = chave_privada.decrypt(bruto, _oaep()).decode("ascii")
    except (binascii.Error, ValueError, TypeError, UnicodeDecodeError):
        raise CriptoErro("não consegui decifrar o pedido") from None
    if not validar_cpf(texto):
        raise CriptoErro("CPF do pedido inválido")
    return so_digitos(texto)


# ---------------------------------------------------------------- telefone (CONTRATO 2 e 7)
def normalizar_telefone(texto):
    """'(88) 99284-3164' -> '558892843164' (55 + DDD + últimos 8 dígitos). None se não normaliza.

    Só dígitos; tira os '0' e o '55' do começo (igual ao bot: ^0+); precisa sobrar DDD (2) + 8 ou 9 dígitos. O 55 só sai
    quando sobra tamanho de telefone com DDD (um DDD 55 sem código de país tem 10 ou 11 dígitos)."""
    d = so_digitos(texto)
    d = d.lstrip("0")
    if len(d) > 11 and d.startswith("55"):
        d = d[2:]
    if len(d) not in (10, 11):
        return None
    return "55" + d[:2] + d[-8:]


def hmac_telefone(chave, normalizado):
    """hex minúsculo de HMAC-SHA256(chave, telefone normalizado)."""
    return hmac.new(chave.encode("utf-8"), normalizado.encode("ascii"), hashlib.sha256).hexdigest()


def hashes_telefones(chave, telefones):
    """Telefones do cadastro (texto solto) -> lista de HMAC sem repetição, na ordem; descarta o que
    não normaliza."""
    saida = []
    for t in telefones:
        n = normalizar_telefone(t)
        if n:
            h = hmac_telefone(chave, n)
            if h not in saida:
                saida.append(h)
    return saida


# ---------------------------------------------------------------- assinatura das chamadas (CONTRATO 2)
def assinar(segredo, timestamp_ms, metodo, caminho, corpo=""):
    """hex de HMAC-SHA256(segredo, timestamp + "\\n" + método + "\\n" + caminho + "\\n" + corpo)."""
    mensagem = f"{timestamp_ms}\n{metodo.upper()}\n{caminho}\n{corpo}"
    return hmac.new(segredo.encode("utf-8"), mensagem.encode("utf-8"), hashlib.sha256).hexdigest()
