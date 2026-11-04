"""Configuração do Orelha: lê orelha/.env e monta a Config.

Os campos comuns (login, navegador, vila, pastas) viram atributos da Config. Qualquer outra
variável do .env é lida pelas funções com cfg.valor(nome, padrao, tipo), sem precisar mexer
neste arquivo:

    dias = ctx.cfg.valor("ORELHA_INTIMACOES_DIAS", 15, int)
    tabela = ctx.cfg.valor("ORELHA_INTIMACOES_TABELA", "css:table.geratabela", "seletor")

Seletores: "css:<seletor css>" ou "xpath:<expressão xpath>". Valor vazio no .env = padrão.
O .env vence as variáveis do ambiente (como no Ultron e no Albi, que usam override=True).
"""
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import dotenv_values
from selenium.webdriver.common.by import By

PASTA_ORELHA = Path(__file__).resolve().parent.parent
PREFIXOS = {"css": By.CSS_SELECTOR, "xpath": By.XPATH}
VERDADEIRO = {"1", "true", "sim", "s", "yes", "y", "verdadeiro"}
FALSO = {"0", "false", "nao", "não", "n", "no", "falso"}

# Padrões do VIOS (os mesmos que o Ultron usa: ver DOCUMENTACAO.md, seção Configuração)
PADROES = {
    "SISTEMA_URL": "https://roneely.vios.com.br/entrar.php?",
    "LOGIN_CAMPO_USUARIO": "css:input[name='form[usuario]']",
    "LOGIN_CAMPO_SENHA": "css:input[name='form[senha]']",
    "LOGIN_BOTAO": "",  # vazio = Enter no campo de senha
    "LOGIN_SUCESSO": "",  # vazio = espera a URL mudar
    "ORELHA_FUNCOES": "agenda,prazos,intimacoes,planilhas",
    # endereço que contém um destes trechos nunca é aberto (ações que gravam/apagam no VIOS)
    "ORELHA_URL_PROIBIDA": "act=del,act=excluir,act=apagar,act=salvar,act=gravar,act=concluir,"
                         "int-lanca.php,excluir,apagar,concluir",
    # botão/link cujo texto contém um destes termos nunca é clicado
    "ORELHA_CLIQUE_PROIBIDO": "SALVAR,GRAVAR,ENVIAR,CONCLUIR,EXCLUIR,APAGAR,LANCAR,CONFIRMAR,"
                            "MARCAR COMO LIDO,MARCAR COMO LIDA,ARQUIVAR,CANCELAR TAREFA",
}


class ConfigErro(Exception):
    pass


def parse_seletor(texto, nome):
    """'css:#id' ou 'xpath://a' -> (By, valor). Levanta ConfigErro se o formato não serve."""
    prefixo, sep, valor = (texto or "").strip().partition(":")
    if not sep or prefixo.lower() not in PREFIXOS or not valor.strip():
        raise ConfigErro(f"{nome}: seletor inválido. Use 'css:...' ou 'xpath:...'")
    return (PREFIXOS[prefixo.lower()], valor.strip())


def parse_bool(texto, nome):
    t = (texto or "").strip().lower()
    if t in VERDADEIRO:
        return True
    if t in FALSO:
        return False
    raise ConfigErro(f"{nome}: use true ou false")


def _lista(texto, sep):
    return [p.strip() for p in str(texto).split(sep) if p.strip()]


def converter(nome, texto, tipo, sep=","):
    """Converte o texto do .env para o tipo pedido. Nunca põe o valor na mensagem de erro
    (pode ser senha)."""
    if callable(tipo) and tipo not in (str, int, float, bool):
        try:
            return tipo(texto)
        except ConfigErro:
            raise
        except Exception as e:
            raise ConfigErro(f"{nome}: valor inválido ({e.__class__.__name__})") from None
    if tipo is str:
        return str(texto).strip()
    if tipo is bool:
        return texto if isinstance(texto, bool) else parse_bool(str(texto), nome)
    if tipo in (int, float):
        if isinstance(texto, (int, float)) and not isinstance(texto, bool):
            return tipo(texto)
        try:
            return tipo(str(texto).strip().replace(",", ".") if tipo is float else str(texto).strip())
        except ValueError:
            raise ConfigErro(f"{nome}: use um número{' inteiro' if tipo is int else ''}") from None
    if tipo == "seletor":
        return texto if isinstance(texto, tuple) else parse_seletor(str(texto), nome)
    if tipo == "seletores":
        if isinstance(texto, list):
            return texto
        return [parse_seletor(p, f"{nome}[{i}]") for i, p in enumerate(_lista(texto, "|"), 1)]
    if tipo == "lista":
        return list(texto) if isinstance(texto, (list, tuple)) else _lista(texto, sep)
    if tipo == "caminho":
        p = Path(str(texto).strip()).expanduser()
        return p if p.is_absolute() else (PASTA_ORELHA / p).resolve()
    if tipo == "data":
        if isinstance(texto, date):
            return texto
        t = str(texto).strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(t, formato).date()
            except ValueError:
                pass
        raise ConfigErro(f"{nome}: use AAAA-MM-DD ou DD/MM/AAAA")
    raise ConfigErro(f"{nome}: tipo desconhecido {tipo!r}")


@dataclass
class Config:
    caminho_env: Path
    vios_url: str  # página de login (SISTEMA_URL)
    vios_base: str  # raiz do VIOS, ex.: https://<escritorio>.vios.com.br/
    usuario: str
    senha: str = field(repr=False)  # nunca aparece em print/log
    campo_usuario: tuple = None
    campo_senha: tuple = None
    botao_login: object = None  # None = Enter no campo de senha
    login_sucesso: object = None  # None = espera a URL mudar
    headless: bool = True
    timeout: int = 20
    manter_aberto: bool = False
    pasta_saida: Path = PASTA_ORELHA / "saida"
    albi_saida: Path = PASTA_ORELHA.parent / "albi" / "saida"
    funcoes_padrao: list = field(default_factory=list)
    urls_proibidas: list = field(default_factory=list)
    cliques_proibidos: list = field(default_factory=list)
    vila_url: str = ""
    vila_usuario: str = "orelha"
    vila_senha: str = field(default="", repr=False)
    vila_timeout: float = 2.0
    _env: dict = field(default_factory=dict, repr=False)

    def bruto(self, nome):
        """Texto da variável como está no .env/ambiente (None se não existe)."""
        return self._env.get(nome)

    def valor(self, nome, padrao=None, tipo=str, sep=","):
        """Lê qualquer variável do orelha/.env.

        tipo: str | int | float | bool | "seletor" ((By, valor)) | "seletores" (lista separada por "|")
              | "lista" (separada por `sep`, padrão ",") | "caminho" (Path; relativo = a partir de orelha/)
              | "data" (date; AAAA-MM-DD ou DD/MM/AAAA) | uma função texto -> valor.
        Variável ausente ou vazia = padrao (convertido para o tipo, se for texto; None fica None).
        Valor inválido = ConfigErro com o nome da variável (sem o valor)."""
        texto = self._env.get(nome)
        if texto is None or not str(texto).strip():
            if padrao is None:
                return None
            if isinstance(padrao, str) and not padrao.strip():
                return [] if tipo in ("lista", "seletores") else (None if tipo == "seletor" else "")
            return converter(nome, padrao, tipo, sep)
        return converter(nome, texto, tipo, sep)

    def seletor(self, nome, padrao=None):
        """Atalho para cfg.valor(nome, padrao, "seletor")."""
        return self.valor(nome, padrao, "seletor")


def ler_ambiente(caminho_env, ambiente=None):
    """Variáveis do ambiente + as do arquivo .env (o arquivo vence). Arquivo ausente = só o ambiente."""
    valores = dict(os.environ if ambiente is None else ambiente)
    caminho = Path(caminho_env)
    if caminho.exists():
        valores.update({k: v for k, v in dotenv_values(caminho).items() if v is not None})
    return valores


def _base(url):
    p = urlparse(url)
    if not p.scheme or not p.netloc:
        raise ConfigErro("SISTEMA_URL: use o endereço completo, com https://")
    return f"{p.scheme}://{p.netloc}/"


def carregar(caminho_env=None, exigir_login=True, ambiente=None):
    """Lê o .env e devolve a Config. exigir_login=False (modo simulado) aceita usuário e senha vazios."""
    caminho_env = Path(caminho_env or PASTA_ORELHA / ".env")
    env = ler_ambiente(caminho_env, ambiente)
    provisoria = Config(caminho_env=caminho_env, vios_url="", vios_base="", usuario="", senha="", _env=env)

    def v(nome, tipo=str, padrao=None):
        return provisoria.valor(nome, PADROES.get(nome, padrao) if padrao is None else padrao, tipo)

    usuario = (env.get("SISTEMA_USUARIO") or "").strip()
    senha = env.get("SISTEMA_SENHA") or ""  # sem strip: espaço pode fazer parte da senha
    if exigir_login:
        faltando = [n for n, x in (("SISTEMA_USUARIO", usuario), ("SISTEMA_SENHA", senha)) if not x]
        if faltando:
            raise ConfigErro(f"preencha no {caminho_env.name}: {', '.join(faltando)}")
    vios_url = v("SISTEMA_URL")
    vila_url = v("VILA_URL", padrao="").rstrip("/")
    if vila_url and not vila_url.endswith("/eventos"):
        vila_url += "/eventos"
    return Config(
        caminho_env=caminho_env,
        vios_url=vios_url,
        vios_base=v("ORELHA_VIOS_BASE", padrao="") or _base(vios_url),
        usuario=usuario,
        senha=senha,
        campo_usuario=v("LOGIN_CAMPO_USUARIO", "seletor"),
        campo_senha=v("LOGIN_CAMPO_SENHA", "seletor"),
        botao_login=v("LOGIN_BOTAO", "seletor"),
        login_sucesso=v("LOGIN_SUCESSO", "seletor"),
        headless=v("HEADLESS", bool, "true"),
        timeout=v("TIMEOUT", int, "20"),
        manter_aberto=v("MANTER_ABERTO", bool, "false"),
        pasta_saida=v("ORELHA_SAIDA", "caminho", "saida"),
        albi_saida=v("ORELHA_ALBI_SAIDA", "caminho", "../albi/saida"),
        funcoes_padrao=v("ORELHA_FUNCOES", "lista"),
        urls_proibidas=v("ORELHA_URL_PROIBIDA", "lista"),
        cliques_proibidos=v("ORELHA_CLIQUE_PROIBIDO", "lista"),
        vila_url=vila_url,
        vila_usuario=v("VILA_USUARIO", padrao="orelha") or "orelha",
        vila_senha=env.get("VILA_SENHA") or "",
        vila_timeout=v("VILA_TIMEOUT", float, "2"),
        _env=env,
    )
