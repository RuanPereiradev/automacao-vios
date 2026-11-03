import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from bot import config
from bot.login import fazer_login
from bot.navegacao import ir_ate_tabela
from bot.navegador import criar_driver
from bot.processos_grupo import (
    VALOR_TODOS,
    _normal,
    grupos_disponiveis,
    ler_processos,
    montar_json,
    montar_txt,
    nome_arquivo,
    nome_json,
    pesquisar_grupo,
)
from main import PASTA_LOGS, configurar_log

log = logging.getLogger("relatorio")

# grupo extra com os processos que não apareceram em nenhum grupo (--sem-grupo)
SEM_GRUPO = "SEM GRUPO CLIENTE"
# ficha não lida porque a rodada foi com --sem-ficha
FICHA_DESLIGADA = {"ok": False, "erro": "ficha não lida (--sem-ficha)"}
# novos logins seguidos na leitura das fichas de um grupo antes de desistir do grupo
MAX_LOGINS_FICHAS = 3


@dataclass
class Opcoes:
    ficha: bool = True  # abre a ficha de cada processo (--sem-ficha desliga)
    sem_grupo: bool = False  # gera o grupo SEM GRUPO CLIENTE (só com --grupo todos)
    encerrados: bool = False  # inclui os processos encerrados na pesquisa

    @property
    def situacao(self):
        return "processos ativos e encerrados" if self.encerrados else "processos ativos"


class PastaErro(Exception):
    pass


class SessaoCaiu(Exception):
    pass


def pasta_relatorios(cfg):
    """Pasta base dos .txt. Com RELATORIO_PASTA, ela tem que existir (ex.: Google Drive montado)."""
    texto = os.getenv("RELATORIO_PASTA", "").strip().strip("\"'").strip()
    if not texto:
        # padrão: <SAIDA_PASTA>/relatorios, criada se faltar
        base = cfg.pasta_saida / "relatorios"
        base.mkdir(parents=True, exist_ok=True)
        return base
    # aceita "~/..." e variáveis ($HOME, %USERPROFILE%); espaços no caminho não atrapalham
    base = Path(os.path.expandvars(os.path.expanduser(texto)))
    if not base.is_dir():
        raise PastaErro(
            f"RELATORIO_PASTA não existe ou não é uma pasta: {base}. "
            "O Google Drive está aberto e sincronizando? Nada foi feito no VIOS."
        )
    return base


def na_tela_de_login(driver, cfg):
    """True se o navegador voltou para a tela de login (sessão do VIOS caiu)."""
    try:
        if "entrar.php" in (driver.current_url or "").lower():
            return True
        campos = [c for c in (cfg.campo_usuario, cfg.campo_senha) if c]
        return bool(campos) and all(driver.find_elements(*c) for c in campos)
    except Exception:
        # navegador fechado ou travado: não é caso de novo login
        return False


def novo_login(driver, cfg):
    fazer_login(driver, cfg)
    ir_ate_tabela(driver, cfg)


def ler_ficha(driver, ci, timeout):
    """Ficha do processo (bot/processo_ficha.py, contrato 2).

    Importa aqui dentro: com --sem-ficha o robô roda mesmo sem esse módulo.
    """
    from bot.processo_ficha import ler_ficha as _ler

    return _ler(driver, ci, timeout)


def ficha_indisponivel():
    """Mensagem de erro se o módulo da ficha não carrega; "" se está tudo certo."""
    try:
        from bot import processo_ficha  # noqa: F401
    except Exception as e:
        return f"módulo da ficha (bot/processo_ficha.py) não carregou: {e}"
    return ""


def _msg(e):
    return getattr(e, "msg", None) or str(e) or type(e).__name__


def _uma_ficha(driver, ci, timeout):
    """Lê uma ficha. Nunca levanta erro: falha vira {"ok": False, "erro": ...}."""
    try:
        ficha = ler_ficha(driver, ci, timeout)
    except Exception as e:
        return {"ok": False, "erro": _msg(e)}
    if not isinstance(ficha, dict):
        return {"ok": False, "erro": f"resposta inválida da ficha: {type(ficha).__name__}"}
    return ficha


def _ler_fichas(driver, cfg, grupo, itens):
    """Abre a ficha de cada processo e guarda em item["ficha"]. Devolve quantas falharam.

    Erro numa ficha: registra, loga e segue. Sessão caída: novo login e mais uma
    tentativa daquela ficha. Mais de MAX_LOGINS_FICHAS logins no grupo: SessaoCaiu.
    """
    logins, falhas = 0, 0
    for n, it in enumerate(itens, 1):
        ci = it.get("ci") or ""
        log.info("%s: ficha %d de %d (CI %s)", grupo, n, len(itens), ci or "?")
        if not ci:
            it["ficha"] = {"ok": False, "erro": "processo sem CI na lista"}
            falhas += 1
            continue
        for _tentativa in range(2):
            if na_tela_de_login(driver, cfg):
                if logins >= MAX_LOGINS_FICHAS:
                    raise SessaoCaiu(f"sessão caiu {logins + 1} vezes nas fichas do grupo {grupo}")
                logins += 1
                log.warning("Sessão do VIOS caiu na ficha do CI %s: fazendo login de novo", ci)
                novo_login(driver, cfg)
            ficha = _uma_ficha(driver, ci, cfg.timeout)
            # falhou por causa da sessão: tenta a mesma ficha depois do login
            if ficha.get("ok") or not na_tela_de_login(driver, cfg):
                break
        it["ficha"] = ficha
        if not ficha.get("ok"):
            falhas += 1
            log.warning("%s: ficha do CI %s não lida: %s", grupo, ci, ficha.get("erro") or "sem detalhe")
    return falhas


def _pesquisar_e_ler(driver, cfg, grupo, valor, opcoes):
    """Processos do grupo, cada um com "situacao" ("ativo"/"encerrado"). Devolve (itens, linhas puladas).

    No VIOS as opções de pesq[filtros_multi][] combinam com E: ativos e encerrados
    juntos dão 0 processos. Com --encerrados são duas pesquisas (ativos, depois
    encerrados), juntadas sem repetir CI.
    """
    situacoes = ["ativo", "encerrado"] if opcoes.encerrados else ["ativo"]
    itens, erros, vistos = [], 0, set()
    for situacao in situacoes:
        pesquisar_grupo(driver, valor, cfg.timeout, encerrados=situacao == "encerrado")
        lidos, pulados = ler_processos(driver, cfg.timeout)
        if not lidos and na_tela_de_login(driver, cfg):
            # a lista veio vazia porque a sessão caiu no meio da leitura
            raise SessaoCaiu(f"tela de login apareceu ao ler o grupo {grupo}")
        erros += pulados
        repetidos = 0
        for it in lidos:
            ci = it.get("ci") or ""
            if ci and ci in vistos:
                repetidos += 1
                continue
            if ci:
                vistos.add(ci)
            it["situacao"] = situacao
            itens.append(it)
        if opcoes.encerrados:
            log.info("%s: %d processo(s) %s(s)%s", grupo, len(lidos) - repetidos, situacao,
                     f" ({repetidos} repetido(s) ignorado(s))" if repetidos else "")
    return itens, erros


def _salvar_grupo(driver, cfg, grupo, valor, pasta, opcoes, excluir=None):
    itens, erros = _pesquisar_e_ler(driver, cfg, grupo, valor, opcoes)
    if excluir is not None:
        # SEM GRUPO CLIENTE: só os CIs que não apareceram em nenhum grupo
        if not itens and excluir:
            # os grupos tinham processos: TODOS vazio é erro de leitura, não "nenhum sem grupo"
            raise RuntimeError(f"lista de TODOS veio vazia ao montar o {grupo}")
        lidos = len(itens)
        itens = [it for it in itens if it.get("ci") not in excluir]
        log.info("%s: %d processos na lista de TODOS, %d sem grupo", grupo, lidos, len(itens))
    fichas_erro = 0
    if opcoes.ficha:
        fichas_erro = _ler_fichas(driver, cfg, grupo, itens)
    else:
        for it in itens:
            it["ficha"] = dict(FICHA_DESLIGADA)
    # sem parents: se a pasta base sumiu (Drive desmontado), falha em vez de criar outra
    pasta.mkdir(exist_ok=True)
    arquivo = pasta / nome_arquivo(grupo)
    arquivo.write_text(montar_txt(grupo, itens, situacao=opcoes.situacao), encoding="utf-8")
    (pasta / nome_json(grupo)).write_text(
        json.dumps(montar_json(grupo, itens), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log.info("%s: %d processos, %d com erro na lista, %d fichas com erro -> %s",
             grupo, len(itens), erros, fichas_erro, arquivo)
    return arquivo, itens, erros


def processar_grupo(driver, cfg, grupo, valor, pasta, opcoes=None, excluir=None, cis=None, puladas=None):
    """Gera o .txt e o .json de um grupo. Se a sessão cair, faz novo login e tenta o grupo mais 1 vez.

    excluir: CIs a deixar de fora (grupo SEM GRUPO CLIENTE).
    cis: conjunto que recebe os CIs do grupo salvo (para o SEM GRUPO CLIENTE).
    puladas: lista que recebe quantas linhas da lista não puderam ser lidas no grupo salvo.
    """
    opcoes = opcoes or Opcoes()
    if na_tela_de_login(driver, cfg):
        log.warning("Sessão do VIOS caiu antes do grupo %s: fazendo login de novo", grupo)
        novo_login(driver, cfg)
    try:
        arquivo, itens, erros = _salvar_grupo(driver, cfg, grupo, valor, pasta, opcoes, excluir)
    except Exception as e:
        if not na_tela_de_login(driver, cfg):
            raise
        log.warning("Grupo %s falhou e o VIOS voltou para a tela de login (%s)", grupo, e)
        arquivo = None
    if arquivo is None:
        log.warning("Novo login e nova tentativa (a última) do grupo %s", grupo)
        novo_login(driver, cfg)
        arquivo, itens, erros = _salvar_grupo(driver, cfg, grupo, valor, pasta, opcoes, excluir)
    if cis is not None:
        cis.update(it.get("ci") for it in itens if it.get("ci"))
    if puladas is not None:
        puladas.append(erros)
    return arquivo


def _print_erro(driver):
    screenshot = PASTA_LOGS / f"erro_{datetime.now():%Y-%m-%d_%H%M%S}.png"
    try:
        driver.save_screenshot(str(screenshot))
    except Exception:
        return "sem screenshot: navegador não respondeu"
    return f"screenshot em {screenshot}"


def _env_bool(nome, padrao):
    texto = os.getenv(nome, "").strip().lower()
    if not texto:
        return padrao
    return texto in ("1", "true", "sim", "yes")


def _tirar_flag(args, flag):
    if flag in args:
        args.remove(flag)
        return True
    return False


def main(*args):
    configurar_log()
    args = list(args)
    sem_ficha = _tirar_flag(args, "--sem-ficha")
    sem_grupo = _tirar_flag(args, "--sem-grupo")
    encerrados = _tirar_flag(args, "--encerrados")
    # --grupo "3A FRIOS|AÇO GRANJA" ou --grupo todos (sem --grupo: PROCESSOS_GRUPOS do .env)
    grupos_txt = None
    if "--grupo" in args:
        i = args.index("--grupo")
        if i + 1 >= len(args):
            log.error("Falta o nome depois de --grupo (ex.: --grupo \"3A FRIOS\" ou --grupo todos)")
            return 1
        grupos_txt = args[i + 1]
        del args[i:i + 2]
    caminho_env = args[0] if args else ".env.usuario2"
    try:
        cfg = config.carregar(caminho_env)
    except config.ConfigErro as e:
        log.error(e)
        return 1
    grupos_txt = grupos_txt or os.getenv("PROCESSOS_GRUPOS", "")
    pedidos = [g.strip() for g in grupos_txt.split("|") if g.strip()]
    if not pedidos:
        log.error("Informe os grupos: --grupo \"3A FRIOS\" ou PROCESSOS_GRUPOS no %s", caminho_env)
        return 1
    # linha de comando vale mais que o .env
    opcoes = Opcoes(
        ficha=not sem_ficha and _env_bool("PROCESSOS_FICHA", True),
        sem_grupo=sem_grupo or _env_bool("PROCESSOS_SEM_GRUPO", False),
        encerrados=encerrados or _env_bool("PROCESSOS_ENCERRADOS", False),
    )
    todos = [p.lower() for p in pedidos] == ["todos"]
    if opcoes.sem_grupo and not todos:
        log.warning("%s só é gerado com --grupo todos: ignorado nesta rodada", SEM_GRUPO)
        opcoes.sem_grupo = False
    if opcoes.ficha:
        erro = ficha_indisponivel()
        if erro:
            log.error("%s. Rode com --sem-ficha (ou PROCESSOS_FICHA=false) para gerar só a lista", erro)
            return 1
    log.info("Fichas: %s | encerrados: %s | %s: %s", "sim" if opcoes.ficha else "não",
             "sim" if opcoes.encerrados else "não", SEM_GRUPO, "sim" if opcoes.sem_grupo else "não")
    # confere a pasta antes de abrir o navegador
    try:
        base = pasta_relatorios(cfg)
    except (PastaErro, OSError) as e:
        log.error(e)
        return 1
    pasta = base / f"{datetime.now():%Y-%m-%d}"
    log.info("Relatórios em %s", pasta)

    driver = criar_driver(cfg.headless, cfg.manter_aberto)
    try:
        fazer_login(driver, cfg)
        ir_ate_tabela(driver, cfg)
        disponiveis = grupos_disponiveis(driver, cfg.timeout)
        log.info("%d grupos no filtro Grupo Cliente", len(disponiveis))
        if todos:
            pedidos = list(disponiveis)
        # sem acento e sem diferença de maiúsculas: "pao mix" acha "PÃO MIX"
        por_nome = {_normal(nome): nome for nome in disponiveis}

        feitos, falhas = 0, 0
        cis = set()  # CIs que apareceram em algum grupo nesta rodada
        puladas = []  # linhas da lista que não foram lidas, por grupo salvo
        for pedido in pedidos:
            grupo = por_nome.get(_normal(pedido))
            if not grupo:
                log.error("Grupo '%s' não existe no filtro Grupo Cliente", pedido)
                falhas += 1
                continue
            try:
                processar_grupo(driver, cfg, grupo, disponiveis[grupo], pasta, opcoes, cis=cis, puladas=puladas)
                feitos += 1
            except Exception:
                log.exception("Falha no grupo %s (%s)", grupo, _print_erro(driver))
                falhas += 1
        if opcoes.sem_grupo:
            if falhas:
                # com grupo faltando, os processos dele iriam parar no SEM GRUPO CLIENTE
                log.error("%s não gerado: %d grupo(s) falharam e a lista ficaria errada", SEM_GRUPO, falhas)
                falhas += 1
            elif sum(puladas):
                # linha pulada num grupo: o processo dela iria parar, errado, no SEM GRUPO CLIENTE
                log.error("%s não gerado: %d linha(s) da lista não foram lidas nos grupos e a lista ficaria errada",
                          SEM_GRUPO, sum(puladas))
                falhas += 1
            else:
                try:
                    processar_grupo(driver, cfg, SEM_GRUPO, VALOR_TODOS, pasta, opcoes, excluir=cis)
                    feitos += 1
                except Exception:
                    log.exception("Falha no grupo %s (%s)", SEM_GRUPO, _print_erro(driver))
                    falhas += 1
        log.info("Concluído: %d grupo(s) salvos, %d com falha", feitos, falhas)
        return 0 if not falhas else 1
    except Exception:
        log.exception("Falha na execução (%s)", _print_erro(driver))
        return 1
    finally:
        if cfg.manter_aberto:
            log.info("MANTER_ABERTO=true: navegador continua aberto")
        else:
            driver.quit()


if __name__ == "__main__":
    # uso: python relatorio_processos.py [caminho/do/.env] [--grupo "3A FRIOS"|todos]
    #      [--sem-ficha] [--sem-grupo] [--encerrados]
    sys.exit(main(*sys.argv[1:]))
