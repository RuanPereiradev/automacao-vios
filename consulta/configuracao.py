"""Configuração do coletor: consulta/.env (variáveis da seção 6 do contrato + as do VIOS no formato da
Orelha). O valor de uma variável nunca vai para mensagem de erro."""
from dataclasses import dataclass, field
from pathlib import Path

from consulta import PASTA
from consulta.coletor import Opcoes
from consulta.cripto import carregar_chave_privada
from nucleo import config as cfg_orelha
from nucleo.config import ConfigErro

ENV_PADRAO = PASTA / ".env"
OBRIGATORIAS = ("CONSULTA_BOT_URL", "CONSULTA_SEGREDO", "CONSULTA_CHAVE_TELEFONE", "CONSULTA_CHAVE_PRIVADA")


@dataclass
class ConfigColetor:
    vios: object                       # nucleo.config.Config (login, navegador, proteções)
    bot_url: str = ""
    segredo: str = field(default="", repr=False)
    chave_privada: Path = None
    intervalo: float = 5.0
    timeout_http: int = 15
    certificado: Path = None          # CONSULTA_CERTIFICADO: PEM do certificado próprio do bot (Mac)
    pasta_logs: Path = PASTA / "logs"
    opcoes: Opcoes = None


def carregar(caminho_env=None, simulado=False, ambiente=None):
    caminho = Path(caminho_env or ENV_PADRAO)
    vios_cfg = cfg_orelha.carregar(caminho, exigir_login=not simulado, ambiente=ambiente)
    v = vios_cfg.valor
    if not simulado:
        faltando = [n for n in OBRIGATORIAS if not (vios_cfg.bruto(n) or "").strip()]
        if faltando:
            raise ConfigErro(f"preencha no {caminho.name}: {', '.join(faltando)}")
    formato = v("CONSULTA_CPF_FORMATO", "mascara").lower()
    if formato not in ("mascara", "digitos"):
        raise ConfigErro("CONSULTA_CPF_FORMATO: use mascara ou digitos")
    intervalo = v("CONSULTA_INTERVALO", 5, float)
    if intervalo <= 0:
        raise ConfigErro("CONSULTA_INTERVALO: use um número maior que zero")
    chave = v("CONSULTA_CHAVE_PRIVADA", "", str)
    chave_path = Path(chave).expanduser() if chave else None
    if chave_path and not chave_path.is_absolute():
        chave_path = (PASTA / chave_path).resolve()
    return ConfigColetor(
        vios=vios_cfg,
        bot_url=v("CONSULTA_BOT_URL", "", str),
        segredo=vios_cfg.bruto("CONSULTA_SEGREDO") or "",
        chave_privada=chave_path,
        intervalo=intervalo,
        timeout_http=v("CONSULTA_TIMEOUT_HTTP", 15, int),
        certificado=Path(v("CONSULTA_CERTIFICADO", "", str)).expanduser() if v("CONSULTA_CERTIFICADO", "", str) else None,
        pasta_logs=Path(v("CONSULTA_LOGS", str(PASTA / "logs"), str)),
        opcoes=Opcoes(chave_telefone=vios_cfg.bruto("CONSULTA_CHAVE_TELEFONE") or "",
                      formato_cpf=formato, exigir_eco_cpf=v("CONSULTA_EXIGIR_ECO_CPF", True, bool)),
    )


def abrir_chave_privada(c):
    return carregar_chave_privada(c.chave_privada)
