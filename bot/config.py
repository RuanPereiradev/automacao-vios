import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from selenium.webdriver.common.by import By

PREFIXOS = {"css": By.CSS_SELECTOR, "xpath": By.XPATH}

OBRIGATORIAS = [
    "SISTEMA_URL",
    "SISTEMA_USUARIO",
    "SISTEMA_SENHA",
    "LOGIN_CAMPO_USUARIO",
    "LOGIN_CAMPO_SENHA",
]


class ConfigErro(Exception):
    pass


def parse_seletor(texto, nome):
    """Converte 'css:#id' ou 'xpath://a' em (By, valor)."""
    prefixo, sep, valor = texto.strip().partition(":")
    if not sep or prefixo.lower() not in PREFIXOS or not valor.strip():
        raise ConfigErro(f"{nome}: seletor inválido '{texto}'. Use 'css:...' ou 'xpath:...'")
    return (PREFIXOS[prefixo.lower()], valor.strip())


def _bool(texto):
    return texto.strip().lower() in ("1", "true", "sim", "yes")


@dataclass
class Config:
    url: str
    usuario: str
    senha: str = field(repr=False)  # nunca aparece em print/log
    campo_usuario: tuple
    campo_senha: tuple
    botao_login: object  # None = Enter no campo de senha
    login_sucesso: object  # None = espera a URL mudar
    passos: list
    url_final: str
    tabela: object  # None = não extrai tabela
    card: object  # None = não extrai cards
    card_cabecalho: object
    card_texto: object
    pesquisa_data: object  # None = não pesquisa por data
    dias_atras: int
    analise_ativa: bool  # analisa as intimações com IA depois de capturar
    marcar_todas: list  # nomes dos filtros em que clicar "Marcar todas"
    tem_cabecalho: bool
    pasta_saida: Path
    headless: bool
    timeout: int
    manter_aberto: bool


def carregar(caminho_env=".env"):
    load_dotenv(caminho_env, override=True)

    faltando = [nome for nome in OBRIGATORIAS if not os.getenv(nome, "").strip()]
    if faltando:
        raise ConfigErro(f"Variáveis faltando no {caminho_env}: {', '.join(faltando)}")

    def seletor(nome):
        texto = os.getenv(nome, "").strip()
        return parse_seletor(texto, nome) if texto else None

    passos_txt = os.getenv("NAVEGACAO_PASSOS", "")
    passos = [
        parse_seletor(p, f"NAVEGACAO_PASSOS[{i}]")
        for i, p in enumerate(passos_txt.split("|"), 1)
        if p.strip()
    ]

    return Config(
        url=os.environ["SISTEMA_URL"].strip(),
        usuario=os.environ["SISTEMA_USUARIO"],
        senha=os.environ["SISTEMA_SENHA"],
        campo_usuario=seletor("LOGIN_CAMPO_USUARIO"),
        campo_senha=seletor("LOGIN_CAMPO_SENHA"),
        botao_login=seletor("LOGIN_BOTAO"),
        login_sucesso=seletor("LOGIN_SUCESSO"),
        passos=passos,
        url_final=os.getenv("NAVEGACAO_URL_FINAL", "").strip(),
        tabela=seletor("TABELA"),
        card=seletor("CARD"),
        card_cabecalho=seletor("CARD_CABECALHO"),
        card_texto=seletor("CARD_TEXTO"),
        pesquisa_data=seletor("PESQUISA_CAMPO_DATA"),
        dias_atras=int(os.getenv("PESQUISA_DIAS_ATRAS", "1")),
        analise_ativa=_bool(os.getenv("ANALISE_ATIVA", "false")),
        marcar_todas=[n.strip() for n in os.getenv("PESQUISA_MARCAR_TODAS", "").split("|") if n.strip()],
        tem_cabecalho=_bool(os.getenv("TABELA_TEM_CABECALHO", "true")),
        pasta_saida=Path(os.getenv("SAIDA_PASTA", "saida").strip() or "saida"),
        headless=_bool(os.getenv("HEADLESS", "false")),
        timeout=int(os.getenv("TIMEOUT", "20")),
        manter_aberto=_bool(os.getenv("MANTER_ABERTO", "false")),
    )
