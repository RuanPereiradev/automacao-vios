"""Orelha — assistente da equipe que SÓ LÊ o VIOS e entrega o relatório do dia.

Funções (orelha/funcoes/): agenda, prazos, intimacoes, parados, planilhas, painel. Cada uma roda isolada:
se falhar, vira uma seção com o erro e as outras continuam. Separado do Ultron, do Zangão e do
Albi: tem .venv, .env, logs/ e saida/ próprios dentro de orelha/ e não importa nada de bot/ nem albi/.

Somente leitura: liga o bloqueio de envios (nucleo/navegador.py) ANTES de abrir o login (o form
de login é marcado pelo Orelha e passa; a primeira página depois do login já abre bloqueada) e,
se a página não abrir com o bloqueio ativo, para tudo (nenhuma função roda).
ORELHA_BLOQUEIO_NO_LOGIN=false volta a ligar o bloqueio logo depois do login, como o Zangão.

uso: python main.py [--funcoes agenda,prazos,intimacoes,parados,planilhas,painel] [--simulado]
                    [--painel-de AAAA-MM-DD] [--painel-ate AAAA-MM-DD]   (período do painel semanal)
                    [--data AAAA-MM-DD] [--sem-pdf] [--eventos] [--albi-saida PASTA] [--env ARQUIVO]
  padrão: todas menos parados e painel (ORELHA_FUNCOES no .env)
  painel       painel semanal em PDF no papel timbrado (painel-semanal.pdf); não entra no relatório do dia
  --simulado   sem navegador nem senha: lê orelha/fixtures/ (dados fictícios)
  --data       dia do relatório (padrão: hoje)
  --sem-pdf    só relatorio.html e resumo.json
  --eventos    cada evento da vila vira uma linha "@evento {json}" na saída padrão
  --albi-saida pasta dos resultados do Albi (padrão ORELHA_ALBI_SAIDA ou ../albi/saida)
Saída: saida/<AAAA-MM-DD>/relatorio.html, resumo.json, relatorio.pdf (e painel-semanal.html/.pdf). Código 1 se alguma
função deu erro (ou a execução parou), 2 se a linha de comando/configuração está errada.
"""
import argparse
import logging
import sys
import time
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

PASTA = Path(__file__).resolve().parent
if str(PASTA) not in sys.path:
    sys.path.insert(0, str(PASTA))

from funcoes import PADRAO, REGISTRO  # noqa: E402
from nucleo import config, eventos, navegador, relatorio, vios  # noqa: E402
from nucleo.modelos import Contexto, Secao  # noqa: E402

log = logging.getLogger("orelha")
# espera (s) antes de cada tentativa de login: a tela pode não abrir por internet que ainda não voltou
# (Mac acordando), VIOS lento ou fora do ar por um momento. Senha errada não é repetida.
ESPERAS_LOGIN = (0, 60, 180)
FORMATO_LOG = "%(asctime)s [%(levelname)s] %(message)s"


class ParadaErro(Exception):
    """A execução não pode continuar (navegador, login ou bloqueio de envios)."""

    def __init__(self, mensagem, motivo):
        super().__init__(mensagem)
        self.motivo = motivo


def configurar_log(pasta_logs=None):
    """Log na saída de erro (a saída padrão fica para os @evento) e em logs/orelha.log."""
    log.handlers.clear()
    log.setLevel(logging.INFO)
    log.propagate = False
    tela = logging.StreamHandler(sys.stderr)
    tela.setFormatter(logging.Formatter(FORMATO_LOG))
    log.addHandler(tela)
    if pasta_logs:
        try:
            Path(pasta_logs).mkdir(parents=True, exist_ok=True)
            arquivo = logging.FileHandler(Path(pasta_logs) / "orelha.log", encoding="utf-8")
            arquivo.setFormatter(logging.Formatter(FORMATO_LOG))
            log.addHandler(arquivo)
        except OSError as e:
            log.warning("Sem log em arquivo (%s)", e.__class__.__name__)


def mensagem(e):
    """Primeira linha do erro, sem o stacktrace do Selenium."""
    texto = getattr(e, "msg", None) or str(e) or e.__class__.__name__
    return texto.strip().splitlines()[0][:300]


def _data(texto):
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError("use AAAA-MM-DD, ex.: 2026-11-04") from None


def argumentos(argv):
    p = argparse.ArgumentParser(prog="orelha", description="Orelha: relatório do dia lendo o VIOS (só leitura).")
    p.add_argument("--funcoes", help="separadas por vírgula: " + ",".join(REGISTRO))
    p.add_argument("--simulado", action="store_true", help="usa orelha/fixtures/ (sem navegador nem senha)")
    p.add_argument("--data", type=_data, help="dia do relatório, AAAA-MM-DD (padrão: hoje)")
    p.add_argument("--sem-pdf", action="store_true", help="não gera o relatorio.pdf")
    p.add_argument("--eventos", action="store_true", help='eventos da vila como "@evento {json}" na saída padrão')
    p.add_argument("--albi-saida", help="pasta dos resultados do Albi")
    p.add_argument("--env", help="arquivo .env (padrão: orelha/.env)")
    p.add_argument("--painel-de", type=_data, help="painel semanal: primeiro dia do período, AAAA-MM-DD (padrão: hoje)")
    p.add_argument("--painel-ate", type=_data,
                   help="painel semanal: último dia do período, AAAA-MM-DD (padrão: início + ORELHA_PAINEL_DIAS_FILA)")
    args = p.parse_args(argv)
    if args.painel_de and args.painel_ate and args.painel_ate < args.painel_de:
        p.error("--painel-ate não pode ser antes de --painel-de")
    return args


def escolher_funcoes(texto, padrao):
    """'agenda, prazos' -> ['agenda', 'prazos'] na ordem do REGISTRO. ValueError se tem nome errado."""
    pedidas = [f.strip().lower() for f in (texto.split(",") if isinstance(texto, str) else texto) if f.strip()]
    desconhecidas = [f for f in pedidas if f not in REGISTRO]
    if desconhecidas:
        raise ValueError(f"função desconhecida: {', '.join(desconhecidas)} (use {', '.join(REGISTRO)})")
    pedidas = pedidas or list(padrao)
    return [c for c in REGISTRO if c in pedidas]


def precisa_vios(modulo, ctx):
    regra = getattr(modulo, "PRECISA_VIOS", True)
    try:
        return bool(regra(ctx)) if callable(regra) else bool(regra)
    except Exception as e:
        log.warning("%s: não consegui saber se precisa do VIOS (%s); considero que sim", ctx.chave, mensagem(e))
        return True


def titulo(chave):
    return getattr(REGISTRO.get(chave), "TITULO", chave.capitalize())


def secao_de_erro(chave, erro):
    return Secao(chave=chave, titulo=titulo(chave), resumo="Não foi possível concluir esta parte.",
                 itens=[], numeros={}, erro=erro)


def rodar_funcao(chave, ctx):
    """Roda uma função isolada. Qualquer erro vira Secao(erro=...); só BloqueioInativo sobe
    (a execução inteira tem que parar)."""
    log.info("Função %s: começando", chave)
    try:
        secao = REGISTRO[chave].executar(ctx)
    except vios.BloqueioInativo:
        raise
    except Exception as e:
        log.exception("Função %s falhou: %s", chave, mensagem(e))
        return secao_de_erro(chave, mensagem(e))
    if not isinstance(secao, Secao):
        log.error("Função %s não devolveu uma Secao (%s)", chave, type(secao).__name__)
        return secao_de_erro(chave, "a função não devolveu o resultado no formato esperado")
    if secao.chave != chave:
        log.warning("Função %s devolveu a seção com chave %r: corrigida", chave, secao.chave)
        secao.chave = chave
    log.info("Função %s: %s%s", chave, secao.resumo, f" (erro: {secao.erro})" if secao.erro else "")
    return secao


def emitir_achados(secao):
    """Evento "achado" por nível (só contagens; nunca o texto dos itens)."""
    for nivel, n in secao.por_nivel().items():
        if n:
            eventos.emitir("achado", funcao=secao.chave, nivel=nivel, contagem=n)


def contagens(secoes):
    saida = {}
    for s in secoes:
        por = s.por_nivel()
        saida[s.chave] = {"total": len(s.itens), "graves": por["grave"], "atencao": por["atencao"],
                          **s.numeros_seguros()}
    return saida


def ligar_bloqueio(ctx):
    """Registra o bloqueio de envios no Chrome. Qualquer erro (ex.: o comando CDP falhou) vira
    ParadaErro: sem bloqueio, nenhuma função roda."""
    cfg = ctx.cfg
    try:
        navegador.bloquear_envios(ctx.driver, permitidos=cfg.valor("ORELHA_XHR_PERMITIDO", "", "lista"),
                                  proibidos=cfg.urls_proibidas)
    except Exception as e:
        raise ParadaErro(f"não consegui ligar o bloqueio de envios: {mensagem(e)}", "bloqueio_inativo") from None


def _print_da_falha(ctx, n):
    """Print da tela do login que falhou, em logs/login_falhou_<data_hora>_<n>.png (só a tela de login)."""
    try:
        pasta = Path(ctx.cfg.valor("ORELHA_LOGS", "logs", "caminho"))
        pasta.mkdir(parents=True, exist_ok=True)
        arq = pasta / f"login_falhou_{datetime.now():%Y-%m-%d_%H%M%S}_{n}.png"
        if ctx.driver.save_screenshot(str(arq)):
            log.info("Print da tela em %s", arq)
    except Exception:  # noqa: BLE001 — o print é só ajuda
        pass


def entrar_no_vios(ctx):
    """Navegador + bloqueio de envios + login + bloqueio conferido. Devolve o driver; levanta ParadaErro."""
    cfg = ctx.cfg
    try:
        no_login = cfg.valor("ORELHA_BLOQUEIO_NO_LOGIN", True, bool)
    except config.ConfigErro as e:
        raise ParadaErro(str(e), "config_invalida") from None
    try:
        ctx.driver = navegador.criar_driver(cfg.headless, cfg.manter_aberto)
    except Exception as e:
        raise ParadaErro(f"o navegador não abriu: {mensagem(e)}", "navegador_falhou") from None
    eventos.emitir("fase", fase="entrando_vios")
    # somente leitura: daqui em diante nenhuma página envia formulário nem POST (ver navegador.py);
    # ligado antes do login, para a página que abre depois dele já vir bloqueada
    if no_login:
        ligar_bloqueio(ctx)
    for n, espera in enumerate(ESPERAS_LOGIN, 1):
        if espera:
            log.warning("Tentando entrar no VIOS de novo em %d s (tentativa %d de %d)", espera, n, len(ESPERAS_LOGIN))
            time.sleep(espera)
        try:
            vios.entrar(ctx, marcar_formulario=no_login)
            break
        except vios.LoginTelaErro as e:
            log.warning("Login no VIOS, tentativa %d: %s", n, mensagem(e))
            _print_da_falha(ctx, n)
            if n == len(ESPERAS_LOGIN):
                raise ParadaErro(f"não entrei no VIOS ({n} tentativas): {mensagem(e)}", "login_falhou") from None
        except Exception as e:
            raise ParadaErro(f"não entrei no VIOS: {mensagem(e)}", "login_falhou") from None
    if not no_login:
        ligar_bloqueio(ctx)
    try:
        vios.abrir(ctx, ctx.driver.current_url)  # recarrega já com o bloqueio e confere
    except vios.BloqueioInativo as e:
        raise ParadaErro(str(e), "bloqueio_inativo") from None
    except Exception as e:
        raise ParadaErro(f"não consegui conferir o bloqueio de envios: {mensagem(e)}", "bloqueio_inativo") from None
    log.info("Bloqueio de envios ligado e conferido (somente leitura)")
    return ctx.driver


def main(argv=None):
    try:
        args = argumentos(sys.argv[1:] if argv is None else list(argv))
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    configurar_log()
    try:
        cfg = config.carregar(args.env, exigir_login=False)
        configurar_log(cfg.valor("ORELHA_LOGS", "logs", "caminho"))
        funcoes = escolher_funcoes(args.funcoes or "", cfg.funcoes_padrao or PADRAO)
    except (config.ConfigErro, ValueError) as e:
        log.error("Configuração: %s", e)
        return 2

    hoje = args.data or date.today()
    # o simulado grava à parte, para não sobrescrever o relatório real do dia
    saida = cfg.pasta_saida / (f"simulado-{hoje.isoformat()}" if args.simulado else hoje.isoformat())
    eventos.iniciar(cfg, pasta=saida, stdout=args.eventos)
    base = Contexto(driver=None, cfg=cfg, hoje=hoje, emitir=eventos.emitir, simulado=args.simulado,
                    fixtures=PASTA / "fixtures", saida=saida, historico=cfg.pasta_saida / "historico",
                    albi_saida=Path(args.albi_saida).expanduser().resolve() if args.albi_saida else cfg.albi_saida,
                    pdf=not args.sem_pdf, painel_de=args.painel_de, painel_ate=args.painel_ate)
    log.info("Orelha: %s, funções %s%s", f"{hoje:%d/%m/%Y}", ", ".join(funcoes),
             " (SIMULADO: fixtures, sem VIOS)" if args.simulado else "")
    eventos.emitir("execucao_iniciada", funcoes=funcoes, simulado=args.simulado, data=hoje.isoformat())

    secoes, parada, falha_relatorio = [], None, ""
    try:
        precisam = [] if args.simulado else [c for c in funcoes if precisa_vios(REGISTRO[c], replace(base, chave=c))]
        if precisam:
            if not cfg.usuario or not cfg.senha:
                log.error("Configuração: preencha SISTEMA_USUARIO e SISTEMA_SENHA no %s (ou use --simulado)",
                          cfg.caminho_env.name)
                eventos.emitir("execucao_fim", resultado="parou", motivo="config_invalida", contagens={}, erros=[])
                return 2
            try:
                entrar_no_vios(base)
            except ParadaErro as e:
                log.error("Execução interrompida: %s", e)
                parada = e
        for chave in funcoes:
            if parada:
                secoes.append(secao_de_erro(chave, f"não rodou: {parada}"))
                continue
            try:
                secao = rodar_funcao(chave, replace(base, chave=chave))
            except vios.BloqueioInativo as e:
                log.error("Execução interrompida: %s", e)
                parada = ParadaErro(str(e), "bloqueio_inativo")
                secao = secao_de_erro(chave, f"interrompida: {e}")
            secoes.append(secao)
            emitir_achados(secao)

        eventos.emitir("fase", fase="gerando_relatorio")
        # o painel semanal tem o próprio PDF: ele não entra (nem sobrescreve) o relatório do dia
        diarias = [s for s in secoes if getattr(REGISTRO[s.chave], "RELATORIO_DIARIO", True)]
        try:
            if not diarias:
                log.info("Só funções com documento próprio: o relatório do dia não foi gerado")
                info = None
            else:
                info = relatorio.gerar(diarias, saida, hoje, simulado=args.simulado, pdf=not args.sem_pdf,
                                       driver=base.driver)
        except Exception as e:
            # sem relatório não tem o que entregar, mas a vila precisa saber que acabou
            log.exception("Relatório não gerado: %s", mensagem(e))
            falha_relatorio = mensagem(e)
        else:
            if info is not None:
                log.info("Relatório: %s", info["html"])
                if info["pdf"]:
                    log.info("PDF: %s", info["pdf"])
                elif not args.sem_pdf:
                    log.warning("PDF não gerado (%s): fica o HTML, que também imprime", info["erro_pdf"])
    finally:
        if base.driver is not None and not cfg.manter_aberto:
            try:
                base.driver.quit()
            except Exception:
                pass

    erros = [s.chave for s in secoes if s.erro] + (["relatorio"] if falha_relatorio else [])
    fim = {"resultado": "parou", "motivo": parada.motivo} if parada else \
        {"resultado": "com_erros" if erros else "concluido"}
    eventos.emitir("execucao_fim", **fim, contagens=contagens(secoes), erros=erros)
    if erros:
        log.warning("Terminou com erro em: %s", ", ".join(erros))
    return 1 if (erros or parada) else 0


if __name__ == "__main__":
    sys.exit(main())
