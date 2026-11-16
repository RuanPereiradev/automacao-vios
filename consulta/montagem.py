"""Montagem do JSON de resultado por LISTA BRANCA (CONTRATO.md, seção 2).

Só os campos do contrato saem daqui. Cada função recebe valores já reduzidos (código de fase, código
de área, datas) e monta o dicionário campo a campo; nada é copiado de um objeto do VIOS por inteiro.
`validar_resultado` confere o formato (usada pelo bot falso e pelos testes): campo extra em qualquer
nível é erro, como no zod estrito do bot.
"""
import re
from datetime import date, datetime

from consulta.fases import FASES, PROXIMOS
from consulta.leitura import AREAS

STATUS = ("ok", "nao_encontrado", "erro")
CAMPOS_RESULTADO = ("id", "status", "lidoEm", "telefones", "processos")
CAMPOS_PROCESSO = ("ref", "area", "situacao", "fase", "desde", "proximo", "encaminhar")
_ISO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HEX = re.compile(r"^[0-9a-f]{64}$")
_REF = re.compile(r"^P\d+$")


def agora_iso(agora=None):
    """'2026-11-16T14:03:00-03:00' (horário local do Mac, sem fração)."""
    a = agora or datetime.now().astimezone()
    return a.replace(microsecond=0).isoformat()


def montar_processo(n, area, fase, desde, proximo, encaminhar):
    """Um processo do contrato. `n` começa em 1 -> ref "P1"."""
    return {
        "ref": f"P{n}",
        "area": area,
        "situacao": "ativo",
        "fase": fase,
        "desde": desde.isoformat() if isinstance(desde, date) else None,
        "proximo": ({"tipo": proximo["tipo"], "data": proximo["data"].isoformat()} if proximo else None),
        "encaminhar": bool(encaminhar),
    }


def montar_resultado(pedido_id, status, processos=(), telefones=(), agora=None):
    """Resultado completo. erro e nao_encontrado saem sempre sem telefones e sem processos."""
    ok = status == "ok"
    return {
        "id": str(pedido_id),
        "status": status,
        "lidoEm": agora_iso(agora),
        "telefones": list(telefones) if ok else [],
        "processos": [dict(p) for p in processos] if ok else [],
    }


def validar_resultado(r):
    """Levanta ValueError se `r` não está exatamente no contrato (campo a mais, valor fora da lista)."""
    def exigir(cond, msg):
        if not cond:
            raise ValueError(msg)

    exigir(isinstance(r, dict) and set(r) == set(CAMPOS_RESULTADO), "campos do resultado fora do contrato")
    exigir(isinstance(r["id"], str) and r["id"], "id")
    exigir(r["status"] in STATUS, "status")
    exigir(isinstance(r["lidoEm"], str) and re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$",
                                                      r["lidoEm"]), "lidoEm")
    exigir(isinstance(r["telefones"], list) and all(isinstance(t, str) and _HEX.match(t) for t in r["telefones"]),
           "telefones (hex de 64 caracteres)")
    exigir(isinstance(r["processos"], list), "processos")
    if r["status"] != "ok":
        exigir(not r["telefones"] and not r["processos"], "nao_encontrado/erro sem dados")
    for p in r["processos"]:
        exigir(isinstance(p, dict) and set(p) == set(CAMPOS_PROCESSO), "campos do processo fora do contrato")
        exigir(_REF.match(p["ref"]), "ref")
        exigir(p["area"] in AREAS, "area")
        exigir(p["situacao"] in ("ativo", "encerrado"), "situacao")
        exigir(p["fase"] in FASES, "fase")
        exigir(p["desde"] is None or _ISO_DATA.match(p["desde"]), "desde")
        prox = p["proximo"]
        exigir(prox is None or (isinstance(prox, dict) and set(prox) == {"tipo", "data"}
                                and prox["tipo"] in PROXIMOS and _ISO_DATA.match(prox["data"])), "proximo")
        exigir(isinstance(p["encaminhar"], bool), "encaminhar")
    return r
