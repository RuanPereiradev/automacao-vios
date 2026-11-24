"""Vigia VIOS → PJe, parte 1: foto diária do VIOS e comparação (só Mac; PJe fica para a parte 2).

  cd pje-busca && python3 vigia.py vios            # lê o VIOS, compara com o estado e grava o relatório do dia
  python3 vigia.py vios --simular                 # lê e compara, mas NÃO grava nada no estado
  python3 vigia.py vios --foto dados/vios/2026-11-23.json --simular   # sem Chrome: usa uma foto já salva
  python3 vigia.py status                         # resumo do estado (empresas, processos, CNPJs, última rodada)
  python3 vigia.py fila                           # processos do TRT7 que a parte 2 vai verificar no PJe
  python3 vigia.py djen                           # DJEN: processo novo contra o cliente (vermelho/amarelo)
  python3 vigia.py djen --simular                 # consulta e classifica, sem gravar
  python3 vigia.py djen --empresa "MM COMERCIO"   # só as empresas cujo nome contém o texto (teste)
  python3 vigia.py djen --refazer-base            # apaga só o estado do DJEN e refaz a base (auditoria completa)
  python3 vigia.py principais                     # só acha o processo principal (no VIOS) de cada cumprimento

Lista lida (PROJETO (1).md, seção 4.2): Processos > Área VIGIA_VIOS_AREA_ID (3 = Trabalhista) + cliente na parte
VIGIA_VIOS_TIPO_PARTE (P = passiva) + ativos [+ VIGIA_VIOS_ADVOGADO_ID, opcional]. Só leitura (GET), pela sessão do
VIOS no Chrome; se a sessão caiu, entra com VIOS_USUARIO/VIOS_SENHA do .env numa aba nova e a fecha no fim.

CNPJ: depois da comparação, consulta no cadastro de pessoas até VIGIA_MAX_CNPJ empresas por rodada (padrão 40),
começando pelas novas; as da base vão sendo completadas nas rodadas seguintes. CPF não é guardado.

Saídas (fora do git): dados/vios/AAAA-MM-DD.json (foto), dados/vigia.sqlite (estado), saida/vigia_AAAA-MM-DD.txt.
"""
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI / "src"))

import vigia_estado as VE  # noqa: E402

DADOS = AQUI / "dados"
SAIDA = AQUI / "saida"


def config(arquivo=AQUI / ".env"):
    """VIOS_* e VIGIA_* do pje-busca/.env (sem python-dotenv); o ambiente tem preferência."""
    cfg = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*((?:VIOS|VIGIA)_\w+)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    cfg.update({k: v for k, v in os.environ.items() if k.startswith(("VIOS_", "VIGIA_"))})
    return cfg


def _ler_vios(cfg):
    """Lê a lista no Chrome e consulta CNPJs. Devolve (lista, sessao) — a sessão fica aberta para os CNPJs."""
    import vios_chrome as VC
    s = VC.Sessao(cfg).abrir()
    advs = [a for a in (cfg.get("VIGIA_VIOS_ADVOGADO_ID") or "").split("|") if a.strip()]
    lista = s.lista(area=cfg.get("VIGIA_VIOS_AREA_ID") or "3", tipo_parte=cfg.get("VIGIA_VIOS_TIPO_PARTE", "P"),
                    advogados=advs)
    return lista, s


def cmd_vios(args):
    cfg = config()
    simular = "--simular" in args
    foto = args[args.index("--foto") + 1] if "--foto" in args else None
    hoje = date.today()
    sessao = None
    if foto:
        lista = json.loads(Path(foto).read_text(encoding="utf-8"))
    else:
        try:
            lista, sessao = _ler_vios(cfg)
        except Exception as e:  # noqa: BLE001 — qualquer falha de leitura para sem mexer no estado
            print("NÃO LEU O VIOS:", e)
            return 1
    linhas = lista.get("linhas") or []
    if not linhas:
        print("A lista do VIOS veio vazia: nada gravado (sessão? filtro?).")
        if sessao:
            sessao.fechar()
        return 1
    if not lista.get("completa"):
        print(f"Atenção: lista incompleta ({len(linhas)} linhas; rodapé: {lista.get('total')}). "
              "Saídas não serão marcadas. Se deu 500, dividir a pesquisa (VIGIA_VIOS_ADVOGADO_ID).")
    if not foto and not simular:
        (DADOS / "vios").mkdir(parents=True, exist_ok=True)
        (DADOS / "vios" / f"{hoje.isoformat()}.json").write_text(json.dumps(lista, ensure_ascii=False), encoding="utf-8")
    DADOS.mkdir(parents=True, exist_ok=True)
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        res = est.aplicar(linhas, lista.get("completa", False), hoje=hoje, simular=simular)
        # CNPJ: novas primeiro, depois as que ainda não foram consultadas (teto por rodada)
        if sessao and not simular:
            teto = int(cfg.get("VIGIA_MAX_CNPJ") or 40)
            fila = list(res["empresas_novas"]) if not res["base"] else []
            fila += [e["chave"] for e in est.sem_cnpj(teto) if e["chave"] not in fila]
            nomes = {p["empresa"]: p["empresa_nome"] for p in res["processos"].values()}
            for n, chave in enumerate(fila[:teto], 1):
                situacao, cnpj = sessao.cnpj(nomes.get(chave, chave))
                est.gravar_cnpj(chave, situacao, cnpj)
            if fila:
                print(f"CNPJ consultado para {min(len(fila), teto)} empresa(s) (teto {teto} por rodada)")
        texto = VE.relatorio(res, est.cnpjs(list(res["empresas_novas"])))
        if not simular:
            SAIDA.mkdir(parents=True, exist_ok=True)
            arq = SAIDA / f"vigia_{hoje.isoformat()}.txt"
            arq.write_text(texto, encoding="utf-8")
            print("Relatório:", arq)
        print(texto if simular else "\n".join(texto.splitlines()[:4]))
        if not res["base"]:
            print(f"Empresas novas: {len(res['empresas_novas'])} · processos novos: {len(res['processos_novos'])} · "
                  f"saíram: {len(res['sairam'])}" + (" · (simulação: nada gravado)" if simular else ""))
    finally:
        est.fechar()
        if sessao:
            sessao.fechar()
    return 0


def cmd_status(_args):
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        print(json.dumps(est.resumo(), ensure_ascii=False, indent=2))
    finally:
        est.fechar()
    return 0


def cmd_fila(_args):
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        fila = est.fila_pje()
    finally:
        est.fechar()
    for p in fila:
        print(f"{p['numero']} · {p['empresa']} · {p['orgao']} · visto em {p['ultima_vez']}"
              f"{'' if p['ativo'] else ' (saiu da lista)'}")
    print(f"{len(fila)} processo(s) do TRT7 na fila do PJe")
    return 0


def cmd_djen(args):
    """DJEN: para cada empresa da base do vigia, busca as publicações no TRT7 e avisa processo desconhecido."""
    import vigia_djen as VD
    cfg = config()
    simular = "--simular" in args
    so = args[args.index("--empresa") + 1] if "--empresa" in args else None
    pausa = float(cfg.get("VIGIA_DJEN_PAUSA_S") or 1.5)
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        if est.eh_base():
            print("Rode primeiro: python3 vigia.py vios (o DJEN compara com a lista do VIOS).")
            return 1
        if "--refazer-base" in args and not simular:
            VD.EstadoDjen(est).refazer_base()
            print("Estado do DJEN apagado: esta rodada refaz a base (a lista do VIOS foi mantida).")
        tribunal_sigla = cfg.get("VIGIA_DJEN_TRIBUNAL") or "TRT7"
        res = VD.rodar(est, so=so, simular=simular, pausa=pausa,
                       consulta=lambda nome: VD.consultar(nome, tribunal_sigla, pausa=pausa),
                       consulta_numero=VD.consultar_numero,
                       manuais=VD.nomes_conferidos(DADOS / "nomes_conferidos.json"),
                       consulta_principal=lambda n: VD.consultar_numero(n, itens=100))
        texto = VD.relatorio(res)
        if not simular and not so:
            SAIDA.mkdir(parents=True, exist_ok=True)
            arq = SAIDA / f"djen_{res['data']}.txt"
            arq.write_text(texto, encoding="utf-8")
            print("Relatório:", arq)
        print(texto)
        if len(res["erros"]) == res["empresas"] and res["empresas"]:
            print("Todas as consultas deram erro: o DJEN pode estar fora do ar ou bloqueando este acesso.")
            return 1
    finally:
        est.fechar()
    return 0


def cmd_principais(_args):
    """Só a ligação cumprimento -> processo principal no VIOS (rápido: 1 consulta ao DJEN por cumprimento)."""
    import vigia_djen as VD
    cfg = config()
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        ed = VD.EstadoDjen(est)
        res = VD.ligar_principais(ed, date.today().isoformat(), lambda n: VD.consultar_numero(n, itens=100),
                                  pausa=float(cfg.get("VIGIA_DJEN_PAUSA_S") or 1.5))
    finally:
        est.fechar()
    for r in res:
        if r["ci"]:
            print(f"{r['numero']} -> principal {r['principal']} · NO VIOS (CI {r['ci']}, {r['empresa']}) · {r['como']}")
        else:
            print(f"{r['numero']} -> principal NÃO achado no VIOS · {r['como']}")
    print(f"{len(res)} cumprimento(s) verificado(s)")
    return 0


def main(args):
    cmds = {"vios": cmd_vios, "status": cmd_status, "fila": cmd_fila, "djen": cmd_djen, "principais": cmd_principais}
    if not args or args[0] not in cmds:
        print(__doc__)
        return 2
    print(f"[{datetime.now():%d/%m/%Y %H:%M}] vigia {args[0]}")
    return cmds[args[0]](args[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
