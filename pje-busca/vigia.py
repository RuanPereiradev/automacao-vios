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
  python3 vigia.py andamentos                     # só as publicações (DJEN) dos cumprimentos fora do VIOS, para a aba
  python3 vigia.py associados                     # nível 3: "Processos associados" de cada principal no PJe (Mac)
  python3 vigia.py associados --paginas 1 --sem-cobertura          # teste: só a 1ª página do filtro, sem gravar
  python3 vigia.py associados --simular                            # tudo, sem gravar
  python3 vigia.py fora                           # onde estão (pelo DJEN) os processos do VIOS fora do acervo do PJe
  python3 vigia.py monitor-importar lista.csv      # monitor: carrega a carteira (CSV de processos exportado do VIOS)
  python3 vigia.py monitor                        # monitor: DJEN (OAB + rodízio por número) e DataJud (rodízio)
  python3 vigia.py monitor --tudo                 # monitor: todos os processos por número (base inicial, ~1 h)
  python3 vigia.py monitor-tribunal               # monitor: rodízio no PJe pelo Loy (última movimentação + teor)
  python3 vigia.py monitor-tribunal --so 0000921-40.2009.8.06.0053   # teste: só esse processo
  python3 vigia.py monitor-tribunal --limite 10 --sem-teor          # teste: 10 processos, sem abrir documento
  python3 vigia.py agenda manha                   # rodada agendada: vios, djen e monitor (launchd: ./servidor_mac.sh vigia)
  python3 vigia.py agenda madrugada               # rodada agendada: associados e monitor-tribunal no PJe

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
    """VIOS_*, VIGIA_* e MONITOR_* do pje-busca/.env (sem python-dotenv); o ambiente tem preferência."""
    cfg = {}
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\s*((?:VIOS|VIGIA|MONITOR)_\w+)\s*=\s*(.*?)\s*$", linha)
            if m:
                cfg[m.group(1)] = m.group(2).strip("'\"")
    cfg.update({k: v for k, v in os.environ.items() if k.startswith(("VIOS_", "VIGIA_", "MONITOR_"))})
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
    """DJEN: para cada empresa da base do vigia, busca as publicações no TRT7 e nos outros TRTs em que ela tem
    processo no VIOS, e avisa processo desconhecido."""
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
                       consulta_principal=lambda n: VD.consultar_numero(n, itens=100),
                       consulta_outro=None if cfg.get("VIGIA_DJEN_OUTROS_TRTS", "1") == "0" else
                       (lambda nome, sigla: VD.consultar(nome, sigla, pausa=pausa)), principal=tribunal_sigla)
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


def cmd_andamentos(_args):
    """Só as publicações (DJEN) dos cumprimentos/execuções fora do VIOS, para a aba Cumprimentos (rápido)."""
    import vigia_djen as VD
    cfg = config()
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        ed = VD.EstadoDjen(est)
        res = VD.atualizar_andamentos(ed, date.today().isoformat(), lambda n: VD.consultar_numero(n, itens=100),
                                      pausa=float(cfg.get("VIGIA_DJEN_PAUSA_S") or 1.5))
    finally:
        est.fechar()
    for r in res:
        print(f"{r['numero']}: {r['andamentos']} andamento(s)" + (f" · ERRO: {r['erro']}" if r["erro"] else ""))
    return 0 if all(not r["erro"] for r in res) else 1


def cmd_associados(args):
    """Nível 3: entra no PJe pelo Loy Trust (ou pelo Presto) e, no Acervo Geral, lê os "Processos associados" (filtro "Processos com
    Associação") e a lista do acervo inteiro (para saber o que do VIOS está fora dele)."""
    import acesso_pje as A
    import chrome_mac as CM
    import vigia_associados as VA
    simular = "--simular" in args
    paginas = int(args[args.index("--paginas") + 1]) if "--paginas" in args else VA.MAX_PAGINAS
    cobertura = "--sem-cobertura" not in args
    cfg = A.config_presto()
    if A.acesso(cfg) == "presto" and not cfg.get("PRESTO_PIN"):
        print("Falta PRESTO_PIN no pje-busca/.env (VIGIA_ACESSO=presto)")
        return 2
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        if est.eh_base():
            print("Rode primeiro: python3 vigia.py vios (a lista de processos vem do VIOS).")
            return 1
        pasta = AQUI / "logs" / "associados" / datetime.now().strftime("%Y-%m-%d_%H%M%S")
        try:
            w, t, _ = A.entrar_trt7(cfg, destino=pasta / "login")
            CM.ir(w, t, VA.ACERVO)
            CM.esperar(w, t, maximo=45, folga=3)
            if not A._logado(w, t):
                raise A.AcessoErro(f"o Acervo Geral mandou para o login ({CM.url(w, t)})")
            CM.para_frente(w, t)  # a janela de associados só termina de abrir com a aba visível
        except (A.AcessoErro, CM.ChromeMacErro) as e:
            print("NÃO ENTROU no PJe:", e)
            return 1
        print("Login ok; lendo os processos com associação no Acervo Geral...", flush=True)
        def ir(url):
            CM.ir(w, t, url)
            CM.esperar(w, t, maximo=45, folga=3)

        lido = VA.ler_acervo(lambda c: CM.js(w, t, c), cobertura=cobertura, max_paginas=paginas,
                             aviso=lambda m: print(m, flush=True), ir=ir)
        if lido["erro"]:
            try:
                A._salvar(pasta, "erro", CM.capturar(w, t))
            except Exception:  # noqa: BLE001
                pass
        parcial = paginas < VA.MAX_PAGINAS or not cobertura
        import vigia_djen as VD
        # regra segura: classe de cada associado novo fora do VIOS pelo DJEN (na dúvida, continua alerta)
        res = VA.rodar(est, lido, simular=simular or parcial, consulta=lambda n: VD.consultar_numero(n, itens=100),
                       pausa=float(config().get("VIGIA_DJEN_PAUSA_S") or 1.5))
        fora = []
        if not res["simulado"] and res["fora_do_acervo"]:
            print("Classificando pelo DJEN os processos fora do acervo e dos arquivados...", flush=True)
            fora = _classificar_fora(est)
    finally:
        est.fechar()
    texto = VA.relatorio(res) + VA.relatorio_fora(fora)
    if not res["simulado"]:
        SAIDA.mkdir(parents=True, exist_ok=True)
        arq = SAIDA / f"associados_{res['data']}.txt"
        arq.write_text(texto, encoding="utf-8")
        print("Relatório:", arq)
    elif parcial and not simular:
        print("(teste parcial: --paginas/--sem-cobertura não grava nada)")
    print(texto)
    return 0 if res["completa"] else 1


def _classificar_fora(est):
    import vigia_associados as VA
    import vigia_djen as VD
    cfg = config()
    return VA.ligar_fora(est, lambda n: VD.consultar_numero(n, itens=100),
                         padrao_escritorio=cfg.get("VIGIA_ESCRITORIO_ADVOGADOS") or VA.ESCRITORIO_PADRAO,
                         pausa=float(cfg.get("VIGIA_DJEN_PAUSA_S") or 1.5), aviso=print)


def cmd_fora(_args):
    """Só classifica pelo DJEN (sem PJe) os processos do VIOS que a última rodada de associados deu como fora do
    acervo e dos arquivados: 2º grau/TST, sem o escritório nas publicações (habilitação), só no nome pessoal."""
    import vigia_associados as VA
    est = VE.Estado(DADOS / "vigia.sqlite")
    try:
        lista = _classificar_fora(est)
    finally:
        est.fechar()
    print(VA.relatorio_fora(lista) or "Nenhum processo fora do acervo e dos arquivados (rode antes: vigia.py associados).")
    return 0


def cmd_agenda(args):
    """Rodada agendada (launchd): manha = vios + djen; madrugada = associados. Mesma trava do botão da aba."""
    import vigia_agenda as AG
    if not args or args[0] not in AG.ETAPAS:
        print("uso: python3 vigia.py agenda manha | madrugada")
        return 2
    return AG.rodar(AQUI, args[0], aviso=lambda m: print(m, flush=True))


MONITOR_BANCO = DADOS / "monitor.sqlite"


def cmd_monitor_importar(args):
    """Carrega a carteira do monitor a partir do CSV de processos exportado do VIOS (substitui a lista anterior:
    quem saiu da lista deixa de ser monitorado, mas o histórico fica). --acrescentar: só soma, ninguém sai."""
    import shutil
    import monitor as M
    arquivos = [a for a in args if not a.startswith("--")]
    if not arquivos or not Path(arquivos[0]).is_file():
        print("uso: python3 vigia.py monitor-importar <arquivo.csv> [--acrescentar]")
        return 2
    origem = Path(arquivos[0])
    try:
        processos, sem = M.ler_csv(origem.read_bytes())
    except M.MonitorErro as e:
        print("CSV recusado:", e)
        return 1
    if not processos:
        print("Nenhum número CNJ no CSV: nada importado.")
        return 1
    hoje = date.today()
    (DADOS / "monitor").mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, DADOS / "monitor" / f"carteira_{hoje.isoformat()}.csv")  # cópia (fora do git)
    est = M.Estado(MONITOR_BANCO)
    try:
        r = est.importar(processos, hoje, completa="--acrescentar" not in args)
    finally:
        est.fechar()
    por = {}
    for p in processos:
        chave = f"{p['tribunal']} {p['grau']}º grau" + ("" if p["sistema"] != "api" else " (só DJEN/DataJud)")
        por[chave] = por.get(chave, 0) + 1
    print(f"Carteira: {r['total']} processo(s) únicos ({r['novos']} novos; {len(r['sairam'])} saíram); "
          f"{sem} linha(s) sem número CNJ ficaram de fora.")
    for k, v in sorted(por.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    return 0


def cmd_monitor(args):
    """Monitor, parte sem login: DJEN pela OAB e por número (rodízio) e DataJud (rodízio)."""
    import monitor as M
    cfg = config()
    est = M.Estado(MONITOR_BANCO)
    try:
        if not est.numeros():
            print("Monitor: carteira vazia (rode: python3 vigia.py monitor-importar <arquivo.csv>); nada a fazer.")
            return 0
        try:
            res = M.rodar_api(est, cfg, tudo="--tudo" in args, aviso=lambda m: print(m, flush=True))
        except M.MonitorErro as e:
            print("Monitor:", e)
            return 1
    finally:
        est.fechar()
    texto = M.relatorio(res, "api")
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"monitor_{res['data']}.txt").write_text(texto, encoding="utf-8")
    print(texto)
    falhou = res["erros"] and not (res["djen"] or res["datajud"] or res["oab_publicacoes"])
    return 1 if falhou else 0


def cmd_monitor_tribunal(args):
    """Monitor, parte no tribunal: entra no PJe pelo Loy Trust (um portal por vez) e lê a última movimentação e o
    teor do documento dela, em rodízio (quem teve novidade no DJEN/DataJud primeiro). Só leitura."""
    import acesso_pje as A
    import chrome_mac as CM
    import monitor as M
    cfg = dict(config(), **A.config_presto())
    limite = int(args[args.index("--limite") + 1]) if "--limite" in args else None
    so = [args[args.index("--so") + 1]] if "--so" in args else None
    ler_teor = "--sem-teor" not in args and cfg.get("MONITOR_LER_TEOR", "1") != "0"
    pasta = AQUI / "logs" / "monitor" / datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def entrar(portal, tipo):
        cfg_portal = dict(cfg, LOY_PORTAL=portal)
        destino = pasta / re.sub(r"\W+", "_", portal).strip("_")
        w, t, url = A.entrar_loy(cfg_portal, destino=destino)  # o monitor sempre entra pelo Loy (não pelo Presto)

        def ir(u):
            CM.ir(w, t, u)
            CM.esperar(w, t, maximo=45, folga=2)
        leitor = M.Leitor(tipo, url, js=lambda c: CM.js(w, t, c), ir=ir, url=lambda: CM.url(w, t),
                          frente=lambda: CM.para_frente(w, t), ler_teor=ler_teor)
        return (w, t), leitor

    def fechar(aba):
        try:
            CM.fechar_aba(*aba)
        except CM.ChromeMacErro:
            pass

    est = M.Estado(MONITOR_BANCO)
    try:
        if not est.numeros():
            print("Monitor: carteira vazia (rode: python3 vigia.py monitor-importar <arquivo.csv>); nada a fazer.")
            return 0
        if not CM.disponivel():
            print("O monitor no tribunal só roda no Mac (Chrome com o Loy Trust).")
            return 2
        try:
            res = M.rodar_tribunal(est, cfg, entrar, limite=limite, aviso=lambda m: print(m, flush=True),
                                   fechar=fechar, numeros=so)
        except M.MonitorErro as e:
            print("Monitor:", e)
            return 1
    finally:
        est.fechar()
    texto = M.relatorio(res, "tribunal")
    SAIDA.mkdir(parents=True, exist_ok=True)
    arq = SAIDA / f"monitor-tribunal_{res['data']}.txt"
    if not so:
        arq.write_text(texto, encoding="utf-8")
    print(texto)
    return 0 if res["lidos"] or not res["fila"] else 1


def main(args):
    cmds = {"vios": cmd_vios, "status": cmd_status, "fila": cmd_fila, "djen": cmd_djen, "principais": cmd_principais,
            "andamentos": cmd_andamentos, "associados": cmd_associados, "fora": cmd_fora, "agenda": cmd_agenda,
            "monitor-importar": cmd_monitor_importar, "monitor": cmd_monitor, "monitor-tribunal": cmd_monitor_tribunal}
    if not args or args[0] not in cmds:
        print(__doc__)
        return 2
    print(f"[{datetime.now():%d/%m/%Y %H:%M}] vigia {args[0]}")
    return cmds[args[0]](args[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
