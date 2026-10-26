import logging
import sys
from pathlib import Path

from bot.analise import analisar_arquivo, recalcular, relatorio_md
from main import configurar_log


def main(*args):
    configurar_log()
    log = logging.getLogger("analise")
    refazer = "--recalcular" in args
    args = [a for a in args if a != "--recalcular"]
    # --ci 42431[,42432]: analisa só essas CIs
    cis = None
    if "--ci" in args:
        i = args.index("--ci")
        cis = [c.strip() for c in args[i + 1].split(",") if c.strip()]
        del args[i:i + 2]
    arquivo = Path(args[0]) if args else None
    caminho_env = args[1] if len(args) > 1 else ".env"
    if not arquivo:
        capturas = sorted(Path("saida").glob("intimacoes_*.json"), key=lambda p: p.stat().st_mtime)
        if not capturas:
            log.error("Nenhum saida/intimacoes_*.json encontrado. Rode o bot antes.")
            return 1
        arquivo = capturas[-1]
    try:
        if refazer:
            # refaz datas, conferências e relatório com as respostas da IA já salvas (sem custo)
            saida = arquivo.with_name(arquivo.name.replace("intimacoes_", "analise_", 1))
            resultados, agente = recalcular(arquivo, saida, caminho_env)
            saida.write_text(__import__("json").dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
            relatorio = saida.with_suffix(".md")
            relatorio.write_text(relatorio_md(resultados, agente, arquivo), encoding="utf-8")
            total, erros = len(resultados), sum(1 for r in resultados if r.get("erro"))
        else:
            relatorio, total, erros = analisar_arquivo(arquivo, caminho_env, cis=cis)
    except Exception:
        log.exception("Falha na análise")
        return 1
    log.info("Concluído: %d intimações analisadas, %d com erro -> %s", total, erros, relatorio)
    return 0 if not erros else 1


if __name__ == "__main__":
    # uso: python analisar.py [--recalcular] [--ci 42431,42432] [saida/intimacoes_AAAA-MM-DD.json] [caminho/do/.env]
    sys.exit(main(*sys.argv[1:]))
