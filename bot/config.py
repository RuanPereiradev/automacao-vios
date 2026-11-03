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

# padrões do VIOS; cada um pode ser trocado no .env
PADROES = {
    "CALENDARIO_URL": "https://roneely.vios.com.br/?pag=sys/agenda/calendario.php&menu_lateral=true",
    "CALENDARIO_TAREFA": "css:.fc-event",
    "CALENDARIO_FILTRO": "PREVIDENCI",
    "CALENDARIO_TIPO": "EDITAR OS DADOS DA ACAO PROTOCOLADA",
    "PROCESSO_NUMERO": "xpath://p[.//strong//span[normalize-space()='Processo']]//a[.//i[contains(@class,'vj-icon-processo')]]",
    "PROCESSO_LINK": "xpath://div[contains(@class,'vj-panel-body')]//a[normalize-space()='Visualizar' and contains(@href,'processos-vis.php')]",
    "PROCESSO_CNJ": "xpath://p[strong/span[normalize-space()='N.° CNJ']]/span[not(contains(@class,'vj-acoes-dados'))]",
    "PROTOCOLO_TAREFA": "PROTOCOLAR INICIAL (PREVIDENCIARIO)",
    "PROTOCOLO_LINHAS": "css:#tabela_v5_processo_vis_tabela_tarefas tbody tr",
    "PROTOCOLO_ARQUIVOS": "css:a[data-tippy-content='Visualizar arquivo']",
    "COMPROVANTE_LINK": "css:.vios-file-box a.vj-arquivo-thumbnail",
    "COMPROVANTE_TEXTO": r"comprovante[\s_-]+de[\s_-]+prot(?:o)?colo",
    "EDICAO_LINK": "xpath://p[.//strong//span[normalize-space()='N.° CNJ']]//i[contains(@class,'vj-icon-edit')]",
    "EDICAO_GRAVAR": "css:#processo_gravar",
    # aviso do VIOS depois de Gravar que o bot responde com Confirmar (texto sem acento, maiúsculo)
    "EDICAO_CONFIRMAR": r"CLIENTE DO CONTRATO NAO E CATEGORIZADO COMO CLIENTE",
    "ORGAO_CADASTRAR": "css:#label_vara_id a[title^='Cadastrar']",
    "ORGAO_NOME": "css:textarea[name='form[varas_nome]']",
    "ORGAO_GRAVAR": "css:#gravar_vara",
}


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
    calendario_url: str
    calendario_tarefa: tuple  # cada tarefa do calendário
    calendario_filtro: str  # texto que a tarefa precisa ter (sem diferença de acento/maiúscula)
    calendario_tipo: str  # tipo de tarefa processado (as outras previdenciárias são ignoradas)
    processo_numero: tuple  # número do processo na tarefa (abre o modal)
    processo_link: tuple  # "Visualizar" do modal do processo
    processo_cnj: tuple  # valor do campo N.° CNJ na tela do processo
    protocolo_tarefa: str  # tarefa da tabela do processo que tem o comprovante
    protocolo_linhas: tuple  # linhas da tabela de tarefas na tela do processo
    protocolo_arquivos: tuple  # "Visualizar arquivo" na linha da tarefa
    comprovante_link: tuple  # arquivos na galeria da tarefa
    comprovante_texto: str  # regex que só o comprovante de protocolo tem no nome
    edicao_link: tuple  # lápis do N.° CNJ na tela do processo (abre a tela de edição)
    edicao_gravar: tuple
    edicao_confirmar: str  # regex do único aviso depois de Gravar que recebe Confirmar
    orgao_cadastrar: tuple  # "+" do campo Órgão julgador (abre o modal de cadastro)
    orgao_nome: tuple  # nome do órgão no modal de cadastro
    orgao_gravar: tuple  # Gravar do modal de cadastro (só com --confirmar)
    campos: dict  # chave do dado -> seletor do campo; None = acha pelo rótulo na tela
    pasta_saida: Path
    headless: bool
    timeout: int
    manter_aberto: bool


def carregar(caminho_env=".env"):
    load_dotenv(caminho_env, override=True)

    faltando = [nome for nome in OBRIGATORIAS if not os.getenv(nome, "").strip()]
    if faltando:
        raise ConfigErro(f"Variáveis faltando no {caminho_env}: {', '.join(faltando)}")

    def valor(nome):
        return os.getenv(nome, "").strip() or PADROES.get(nome, "")

    def seletor(nome):
        texto = valor(nome)
        return parse_seletor(texto, nome) if texto else None

    return Config(
        url=os.environ["SISTEMA_URL"].strip(),
        usuario=os.environ["SISTEMA_USUARIO"].strip(),
        senha=os.environ["SISTEMA_SENHA"],
        campo_usuario=seletor("LOGIN_CAMPO_USUARIO"),
        campo_senha=seletor("LOGIN_CAMPO_SENHA"),
        botao_login=seletor("LOGIN_BOTAO"),
        login_sucesso=seletor("LOGIN_SUCESSO"),
        calendario_url=valor("CALENDARIO_URL"),
        calendario_tarefa=seletor("CALENDARIO_TAREFA"),
        calendario_filtro=valor("CALENDARIO_FILTRO"),
        calendario_tipo=valor("CALENDARIO_TIPO"),
        processo_numero=seletor("PROCESSO_NUMERO"),
        processo_link=seletor("PROCESSO_LINK"),
        processo_cnj=seletor("PROCESSO_CNJ"),
        protocolo_tarefa=valor("PROTOCOLO_TAREFA"),
        protocolo_linhas=seletor("PROTOCOLO_LINHAS"),
        protocolo_arquivos=seletor("PROTOCOLO_ARQUIVOS"),
        comprovante_link=seletor("COMPROVANTE_LINK"),
        comprovante_texto=valor("COMPROVANTE_TEXTO"),
        edicao_link=seletor("EDICAO_LINK"),
        edicao_gravar=seletor("EDICAO_GRAVAR"),
        edicao_confirmar=valor("EDICAO_CONFIRMAR"),
        orgao_cadastrar=seletor("ORGAO_CADASTRAR"),
        orgao_nome=seletor("ORGAO_NOME"),
        orgao_gravar=seletor("ORGAO_GRAVAR"),
        campos={chave: seletor(f"CAMPO_{chave.upper()}") for chave in ("cnj", "orgao", "valor")},
        pasta_saida=Path(os.getenv("SAIDA_PASTA", "saida").strip() or "saida"),
        headless=_bool(os.getenv("HEADLESS", "false")),
        timeout=int(os.getenv("TIMEOUT", "20")),
        manter_aberto=_bool(os.getenv("MANTER_ABERTO", "false")),
    )
