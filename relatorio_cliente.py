import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from bot.relatorio_cliente import ErroFatal, gerar, pasta_padrao
from main import configurar_log


def eh_env(arg):
    """True se o argumento é o arquivo de configuração (e não um .json, .txt ou pasta)."""
    caminho = Path(arg)
    if caminho.is_dir() or arg.lower().endswith((".txt", ".json")):
        return False
    return ".env" in caminho.name.lower() or caminho.is_file()


def main(*args):
    configurar_log()
    log = logging.getLogger("relatorio_cliente")
    args = list(args)
    refazer = "--refazer" in args
    # --ia liga a IA (resumo, pendência, financeira); sem ela vale RELATORIO_IA do .env (padrão: sem IA)
    usar_ia = True if "--ia" in args else None
    args = [a for a in args if a not in ("--refazer", "--ia")]
    # o .env é o arquivo com ".env" no nome (ou outro arquivo que não é .json/.txt);
    # o resto é .json (ou o .txt do grupo) ou pasta, que vira PDF
    envs = [a for a in args if eh_env(a)]
    caminhos = [a for a in args if a not in envs]
    if len(envs) > 1:
        log.error("Mais de um arquivo de configuração: %s", ", ".join(envs))
        return 1
    faltando = [c for c in caminhos if not Path(c).exists()]
    if faltando:
        log.error("Não encontrado (esperado um .json, um .txt ou uma pasta): %s", ", ".join(faltando))
        return 1
    caminho_env = envs[0] if envs else ".env.usuario2"
    if not Path(caminho_env).is_file():
        log.error("Arquivo de configuração não encontrado: %s", caminho_env)
        return 1
    load_dotenv(caminho_env, override=True)

    if not caminhos:
        pasta = pasta_padrao()
        if not pasta:
            log.error("Nenhuma pasta AAAA-MM-DD em RELATORIO_PASTA (ou <SAIDA_PASTA>/relatorios). "
                      "Rode o relatorio_processos.py antes ou informe o .json/pasta.")
            return 1
        log.info("Usando a pasta mais recente: %s", pasta)
        caminhos = [pasta]

    try:
        feitos, pulados, falhas = gerar(caminhos, refazer, usar_ia)
    except ErroFatal as e:
        log.error("Parado: %s", e)
        return 1
    except Exception:
        log.exception("Falha no relatório do cliente")
        return 1
    if not (feitos or pulados or falhas):
        log.error("Nenhum .json de grupo encontrado em: %s", ", ".join(str(c) for c in caminhos))
        return 1
    log.info("Concluído: %d relatório(s) gerado(s), %d já em dia, %d com falha", feitos, pulados, falhas)
    return 0 if not falhas else 1


if __name__ == "__main__":
    # uso: python relatorio_cliente.py [.env.usuario2] [GRUPO.json | pasta com .json] [--refazer] [--ia]
    sys.exit(main(*sys.argv[1:]))
