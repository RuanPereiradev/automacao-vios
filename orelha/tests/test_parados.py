"""Testes da função "parados" (processos ativos sem tarefa aberta). Só dados fictícios."""
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from funcoes import parados as p
from nucleo import config, simulado, vios
from nucleo.modelos import Contexto, Secao

PASTA = Path(__file__).resolve().parent.parent
FIXTURES = PASTA / "fixtures"
HOJE = date(2026, 11, 4)
BASE = "https://exemplo.vios.com.br/"


def fixture(nome):
    return simulado.substituir((FIXTURES / "parados" / nome).read_text(encoding="utf-8"), HOJE)


def tarefas_html(*linhas, info=""):
    cab = "".join(f"<th>{c}</th>" for c in ("", "CI", "Tipo de tarefa", "Descrição", "Comentários", "Datas",
                                             "Envolvidos", "Ações"))
    return (f'<div class="dataTables_wrapper"><table><thead><tr>{cab}</tr></thead><tbody>{"".join(linhas)}'
            f'</tbody></table><div class="dataTables_info">{info}</div></div>')


def linha(ci, tipo, datas, selo=""):
    selo = f'<span class="vj-badge">{selo}</span>' if selo else ""
    return (f"<tr><td></td><td>{ci}</td><td>{selo}<span>{tipo}</span></td><td>desc</td><td></td>"
            f"<td>{datas}</td><td>Responsáveis: Pessoa Fictícia</td><td></td></tr>")


class ComConfig(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.env = self.pasta / ".env"
        self.escrever_env()
        self.eventos = []

    def escrever_env(self, **variaveis):
        texto = "SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n"
        variaveis.setdefault("ORELHA_PARADOS_FONTE", "fichas")  # estes testes são da leitura antiga (ficha por ficha)
        texto += "".join(f"{k}={v}\n" for k, v in variaveis.items() if v is not None)
        self.env.write_text(texto, encoding="utf-8")
        self.cfg = config.carregar(self.env, exigir_login=False, ambiente={})

    def ctx(self, simulado_=False):
        return Contexto(driver=None, cfg=self.cfg, hoje=HOJE, simulado=simulado_, fixtures=FIXTURES,
                        saida=self.pasta / "saida" / HOJE.isoformat(), historico=self.pasta / "historico",
                        chave="parados", emitir=lambda tipo, **d: self.eventos.append((tipo, d)))

    def progresso(self):
        return json.loads((self.pasta / "historico" / p.PROGRESSO).read_text(encoding="utf-8"))


class TestLista(unittest.TestCase):
    def test_lista_ficticia(self):
        procs, avisos = p.ler_lista_html(fixture("lista.html"), BASE)
        self.assertEqual([x.ci for x in procs], list(range(9101, 9109)))
        self.assertEqual(avisos, [])
        primeiro = procs[0]
        # a etiqueta (vj-badge) não entra no número
        self.assertEqual(primeiro.numero, "0009101-11.2099.8.06.0001")
        self.assertEqual(primeiro.area, "Cível Consumidor")
        self.assertEqual(primeiro.cliente, "Cliente Fictício Alfa Ltda")
        self.assertEqual(primeiro.link, BASE + "?pag=sys/processos/processos-vis.php&processos_id=9101")
        # número que não é CNJ ("Outros: ...")
        self.assertEqual(procs[5].numero, "0099/2099")
        # nunca o link de Apagar/Editar
        self.assertTrue(all("act=del" not in x.link and "processos-cad" not in x.link for x in procs))

    def test_linha_sem_ci_e_repetida(self):
        html = ("<table><tr id='processos-lista_linha_1' data-processos_id='77'>"
                "<td data-id='processos-lista_linha_1_pr_areas_nome'>Trabalhista</td></tr>"
                "<tr id='processos-lista_linha_2' data-processos_id='77'><td>x</td></tr>"
                "<tr id='processos-lista_linha_3'><td data-id='processos-lista_linha_3_clientes_nome'>Y</td></tr>"
                "<tr id='outra'><td>z</td></tr></table>")
        procs, avisos = p.ler_lista_html(html, BASE)
        self.assertEqual([x.ci for x in procs], [77])
        self.assertEqual(procs[0].area, "Trabalhista")
        # sem link de Visualizar: monta o endereço da ficha
        self.assertIn("processos_id=77", procs[0].link)
        self.assertEqual(len(avisos), 1)

    def test_lista_vazia(self):
        self.assertEqual(p.ler_lista_html("<table><tr><td>Nenhum registro</td></tr></table>"), ([], []))


class TestTarefas(unittest.TestCase):
    def leitura(self, ci):
        return p.ler_tarefas_html(fixture(f"ficha-{ci}.html"))

    def test_fichas_ficticias(self):
        esperado = {9101: ("com_tarefa", "info"), 9102: ("parado", "atencao"), 9103: ("parado", "grave"),
                    9104: ("parado", "grave"), 9105: ("com_tarefa", "info"), 9106: ("parado", "atencao"),
                    9107: ("nao_lido", "info"), 9108: ("incompleto", "info")}
        for ci, (situacao, nivel) in esperado.items():
            with self.subTest(ci=ci):
                av = p.avaliar(self.leitura(ci), HOJE, 90)
                self.assertEqual((av.situacao, av.nivel), (situacao, nivel))

    def test_campos_da_tarefa(self):
        aberta, concluida = self.leitura(9101).tarefas
        self.assertEqual(aberta.ci, "55012")
        self.assertEqual(aberta.tipo, "ANALISAR PROCESSO (CÍVEL) 2026")
        self.assertEqual(aberta.para_conclusao, date(2026, 11, 9))
        self.assertEqual(aberta.limite, date(2026, 11, 14))
        self.assertIsNone(aberta.concluida_em)
        self.assertTrue(aberta.aberta)
        self.assertEqual(concluida.concluida_em, date(2026, 10, 5))

    def test_cancelada_nao_conta_como_aberta(self):
        cancelada = self.leitura(9103).tarefas[0]
        self.assertTrue(cancelada.cancelada)
        self.assertEqual(cancelada.tipo, "AUDIÊNCIA UNA (TRABALHISTA) 2026")
        self.assertFalse(cancelada.aberta)

    def test_cabecalho_duplicado_e_tabela_na_descricao(self):
        leitura = self.leitura(9105)
        self.assertTrue(leitura.achou_tabela)
        self.assertEqual([t.ci for t in leitura.tarefas], ["55052", "55051"])
        # a tabela colada na descrição não desloca as colunas
        self.assertEqual(leitura.tarefas[1].concluida_em, date(2026, 10, 21))

    def test_nenhum_registro_e_tabela_ausente(self):
        vazia = self.leitura(9104)
        self.assertTrue(vazia.achou_tabela)
        self.assertEqual(vazia.tarefas, [])
        self.assertFalse(self.leitura(9107).achou_tabela)
        self.assertFalse(p.ler_tarefas_html("").achou_tabela)

    def test_carregando_nao_e_ficha_vazia(self):
        html = tarefas_html('<tr><td colspan="8">Carregando...</td></tr>')
        leitura = p.ler_tarefas_html(html)
        self.assertFalse(leitura.achou_tabela)
        self.assertEqual(p.avaliar(leitura, HOJE).situacao, "nao_lido")

    def test_tabela_paginada_nao_vira_parado(self):
        leitura = self.leitura(9108)
        self.assertEqual(leitura.total_informado, 12)
        av = p.avaliar(leitura, HOJE)
        self.assertEqual(av.situacao, "incompleto")
        self.assertIn("2 de 12", av.motivo)
        # com o texto do DataTables passado à parte (leitura do VIOS)
        html = tarefas_html(linha("1", "X", "Concluída em: 01/11/2026"))
        self.assertEqual(p.ler_tarefas_html(html, info="Mostrando 1 a 1 de 3 registros").total_informado, 3)
        self.assertIsNone(p.ler_tarefas_html(html, info="").total_informado)

    def test_colunas_fora_do_lugar_procura_na_linha(self):
        html = tarefas_html("<tr><td>1</td><td>ANALISAR</td><td>Concluída em: 01/10/2026</td></tr>")
        t = p.ler_tarefas_html(html).tarefas[0]
        self.assertEqual(t.concluida_em, date(2026, 10, 1))

    def test_data_vazia_do_vios_e_aberta(self):
        html = tarefas_html(linha("1", "PRAZO", "Para conclusão 10/11/2026 Concluída em: 00/00/0000"))
        self.assertTrue(p.ler_tarefas_html(html).tarefas[0].aberta)

    def test_niveis(self):
        def av(*linhas_, dias=90):
            return p.avaliar(p.ler_tarefas_html(tarefas_html(*linhas_)), HOJE, dias)
        recente = linha("2", "MANIFESTAÇÃO", "Concluída em: 01/11/2026")
        antiga = linha("1", "ANALISAR", "Concluída em: 01/01/2026")
        self.assertEqual(av(recente, antiga).nivel, "atencao")
        self.assertEqual(av(recente, antiga).ultima.ci, "2")
        self.assertEqual(av(antiga).nivel, "grave")
        self.assertEqual(av(antiga, dias=400).nivel, "atencao")
        so_cancelada = av(linha("3", "AUDIÊNCIA", "Para conclusão 01/11/2026", selo="CANCELADA"))
        self.assertEqual((so_cancelada.situacao, so_cancelada.nivel), ("parado", "grave"))
        self.assertIn("cancelada", p.descrever(so_cancelada, HOJE))


class TestRetomada(unittest.TestCase):
    def test_ciclo_em_lotes(self):
        lote, fora, prog = p.planejar([5, 1, 3, 2, 4], None, 3, HOJE)
        self.assertEqual((lote, fora), ([1, 2, 3], [4, 5]))
        prog, de_novo = p.atualizar_progresso(prog, lote, lote, [], [2], [1, 3], fora, datetime(2026, 11, 4, 9))
        self.assertEqual(prog["ultimo_ci"], 3)
        self.assertFalse(prog["ciclo_completo"])
        self.assertEqual(prog["parados_no_ciclo"], [2])
        lote, fora, prog = p.planejar([1, 2, 3, 4, 5], prog, 3, HOJE)
        self.assertEqual((lote, fora), ([4, 5], []))
        prog, _ = p.atualizar_progresso(prog, lote, lote, [], [5], [4], fora, datetime(2026, 11, 11, 9))
        self.assertTrue(prog["ciclo_completo"])
        self.assertEqual(prog["lidos_no_ciclo"], 5)
        self.assertEqual(prog["parados_no_ciclo"], [2, 5])
        # ciclo completo: recomeça do começo
        lote, fora, prog = p.planejar([1, 2, 3, 4, 5, 6], prog, 3, date(2026, 11, 18))
        self.assertEqual(lote, [1, 2, 3])
        self.assertEqual(prog["ciclo_inicio"], "2026-11-18")
        self.assertEqual(prog["parados_no_ciclo"], [])

    def test_ficha_que_falhou_e_tentada_uma_vez(self):
        lote, fora, prog = p.planejar([1, 2, 3], None, 0, HOJE)
        prog, _ = p.atualizar_progresso(prog, lote, lote, [2], [], [1, 3], fora, datetime(2026, 11, 4))
        self.assertEqual(prog["pendentes"], [2])
        self.assertFalse(prog["ciclo_completo"])
        lote, fora, prog = p.planejar([1, 2, 3, 4], prog, 0, HOJE)
        self.assertEqual(lote, [2, 4])  # pendente primeiro, depois o que é novo
        prog, de_novo = p.atualizar_progresso(prog, lote, lote, [2], [], [4], fora, datetime(2026, 11, 5))
        self.assertEqual(de_novo, [2])
        self.assertEqual(prog["pendentes"], [])
        self.assertTrue(prog["ciclo_completo"])

    def test_interrompido_continua_de_onde_parou(self):
        lote, fora, prog = p.planejar([10, 20, 30], None, 0, HOJE)
        prog, _ = p.atualizar_progresso(prog, lote, [10], [], [], [10], fora, datetime(2026, 11, 4))
        self.assertEqual(prog["ultimo_ci"], 10)
        self.assertFalse(prog["ciclo_completo"])
        self.assertEqual(p.planejar([10, 20, 30], prog, 0, HOJE)[0], [20, 30])

    def test_progresso_invalido_e_processo_que_saiu_da_lista(self):
        with self.assertLogs("orelha", "WARNING"):
            lote, _, prog = p.planejar([1, 2], {"versao": 99}, 0, HOJE)
        self.assertEqual(lote, [1, 2])
        antigo = {**p.novo_ciclo(HOJE), "ultimo_ci": 1, "pendentes": [9]}
        lote, _, prog = p.planejar([1, 2], antigo, 0, HOJE)
        self.assertEqual(lote, [2])
        self.assertEqual(prog["pendentes"], [])

    def test_progresso_no_fim_sem_ciclo_completo_recomeca(self):
        antigo = {**p.novo_ciclo(HOJE), "ultimo_ci": 50}
        lote, _, prog = p.planejar([1, 2], antigo, 0, HOJE)
        self.assertEqual(lote, [1, 2])
        self.assertEqual(prog["ultimo_ci"], 0)


class TestOpcoes(ComConfig):
    def test_padroes(self):
        op = p.opcoes(self.cfg)
        self.assertEqual((op.maximo, op.dias_grave, op.agrupar, op.liberar_xhr), (300, 90, "area", "nao"))
        self.assertEqual(op.colunas, {"ci": 1, "tipo": 2, "datas": 5})
        self.assertIsNone(op.proxima_pagina)
        self.assertEqual(op.limite_lista, "9999999")

    def test_valores_e_erros(self):
        self.escrever_env(ORELHA_PARADOS_MAX="50", ORELHA_PARADOS_AGRUPAR="Cliente",
                          ORELHA_PARADOS_COLUNAS_TAREFA="datas=6", ORELHA_PARADOS_PROXIMA_PAGINA="css:a.proxima")
        op = p.opcoes(self.cfg)
        self.assertEqual((op.maximo, op.agrupar), (50, "cliente"))
        self.assertEqual(op.colunas, {"ci": 1, "tipo": 2, "datas": 6})
        self.assertEqual(op.proxima_pagina[1], "a.proxima")
        for nome, valor in (("ORELHA_PARADOS_AGRUPAR", "empresa"), ("ORELHA_PARADOS_COLUNAS_TAREFA", "tipo=x"),
                            ("ORELHA_PARADOS_LIBERAR_XHR", "talvez"), ("ORELHA_PARADOS_MAX", "muitos"),
                            ("ORELHA_PARADOS_URL_FICHA", "?pag=sys/processos/processos-vis.php")):
            with self.subTest(nome=nome):
                self.escrever_env(**{nome: valor})
                with self.assertRaises(config.ConfigErro) as e:
                    p.opcoes(self.cfg)
                self.assertIn(nome, str(e.exception))


class TestSimulado(ComConfig):
    def test_executar_simulado(self):
        secao = p.executar(self.ctx(simulado_=True))
        self.assertIsInstance(secao, Secao)
        self.assertEqual(secao.chave, "parados")
        self.assertEqual(secao.erro, "")
        titulos = [i.titulo for i in secao.itens]
        # por área (na ordem alfabética), urgentes primeiro, mais antigo primeiro
        self.assertEqual(titulos, ["0009102-22.2099.8.06.0001", "0099/2099",
                                   "0009104-44.2099.5.07.0002", "0009103-33.2099.5.07.0002"])
        self.assertEqual([i.grupo for i in secao.itens],
                         ["Cível Consumidor", "Previdenciário", "Trabalhista", "Trabalhista"])
        self.assertEqual([i.nivel for i in secao.itens], ["atencao", "atencao", "grave", "grave"])
        self.assertTrue(all(i.link.startswith("https://exemplo.vios.com.br/?pag=sys/processos/processos-vis.php")
                            for i in secao.itens))
        self.assertIn("CI 9104", secao.itens[2].detalhe)
        self.assertIn("nenhuma tarefa", secao.itens[2].detalhe)
        self.assertIn("há 120 dias", secao.itens[3].detalhe)
        n = secao.numeros
        self.assertEqual((n["processos_ativos"], n["conferidos"], n["parados"], n["graves"]), (8, 7, 4, 2))
        self.assertEqual((n["fichas_nao_lidas"], n["nao_confirmados"], n["faltam_no_ciclo"]), (1, 1, 0))
        avisos = " ".join(secao.avisos)
        self.assertIn("9107", avisos)
        self.assertIn("CI 9108", avisos)
        self.assertIn("4 processos parados entre 7 conferidos", secao.resumo)
        # simulado não mexe no progresso de verdade
        self.assertFalse((self.pasta / "historico").exists())
        # eventos: só a fase (o main emite os achados), nada de dado de cliente
        self.assertEqual(self.eventos, [("fase", {"fase": "lendo_processos"})])

    def test_agrupar_por_cliente(self):
        self.escrever_env(ORELHA_PARADOS_AGRUPAR="cliente")
        secao = p.executar(self.ctx(simulado_=True))
        self.assertIn("Cliente Fictício Gama", [i.grupo for i in secao.itens])

    def test_numeros_seguros_para_a_vila(self):
        secao = p.executar(self.ctx(simulado_=True))
        self.assertEqual(secao.numeros_seguros(), secao.numeros)


class LeitorFalso:
    """Fichas de mentira: {ci: LeituraFicha | Exception}."""

    def __init__(self, respostas):
        self.respostas, self.lidas, self.fechado = respostas, [], False
        self.liberado = False

    def ficha(self, proc):
        self.lidas.append(proc.ci)
        r = self.respostas.get(proc.ci, p.LeituraFicha(True, []))
        if isinstance(r, BaseException):
            raise r
        return r

    def fechar(self):
        self.fechado = True


def aberta():
    return p.LeituraFicha(True, [p.Tarefa(ci="1", tipo="PRAZO")])


class TestConferir(ComConfig):
    def processos(self, *cis):
        return [p.Processo(ci=c, numero=f"Processo fictício {c}", area="Cível") for c in cis]

    def test_limite_retomada_e_log_do_que_ficou_de_fora(self):
        self.escrever_env(ORELHA_PARADOS_MAX="2")
        op = p.opcoes(self.cfg)
        procs = self.processos(3, 1, 2)
        leitor = LeitorFalso({1: aberta()})
        with self.assertLogs("orelha", "INFO") as logs:
            secao = p.conferir(self.ctx(), op, procs, [], leitor)
        self.assertEqual(leitor.lidas, [1, 2])
        self.assertTrue(leitor.fechado)
        self.assertTrue(any("ficam para as próximas execuções" in l and "CI 3" in l for l in logs.output))
        self.assertEqual([i.titulo for i in secao.itens], ["Processo fictício 2"])
        self.assertEqual(secao.numeros["faltam_no_ciclo"], 1)
        self.assertIn("faltam 1", secao.resumo)
        self.assertTrue(any("ORELHA_PARADOS_MAX" in a for a in secao.avisos))
        prog = self.progresso()
        self.assertEqual((prog["ultimo_ci"], prog["parados_no_ciclo"], prog["ciclo_completo"]), (2, [2], False))
        # segunda execução: continua do CI 3 e fecha o ciclo
        leitor = LeitorFalso({})
        secao = p.conferir(self.ctx(), op, procs, [], leitor)
        self.assertEqual(leitor.lidas, [3])
        self.assertTrue(self.progresso()["ciclo_completo"])
        self.assertIn("ciclo completo: 2 parados em 3 processos", secao.resumo)

    def test_ficha_com_erro_vira_aviso_e_pendente(self):
        op = p.opcoes(self.cfg)
        leitor = LeitorFalso({1: RuntimeError("elemento sumiu\nstack do selenium"), 2: aberta()})
        secao = p.conferir(self.ctx(), op, self.processos(1, 2), [], leitor)
        self.assertEqual(secao.erro, "")
        self.assertEqual(secao.itens, [])
        self.assertTrue(any("CI 1" in a and "será tentada de novo" in a for a in secao.avisos))
        self.assertTrue(any("elemento sumiu" in a and "stack" not in a for a in secao.avisos))
        self.assertEqual(self.progresso()["pendentes"], [1])

    def test_nenhuma_ficha_lida_e_erro(self):
        op = p.opcoes(self.cfg)
        leitor = LeitorFalso({1: p.LeituraFicha(False, erro="a ficha não carregou"),
                              2: p.LeituraFicha(False, erro="a ficha não carregou")})
        secao = p.conferir(self.ctx(), op, self.processos(1, 2), [], leitor)
        self.assertIn("nenhuma ficha foi lida", secao.erro)

    def test_sessao_caiu_guarda_o_que_leu(self):
        op = p.opcoes(self.cfg)
        leitor = LeitorFalso({2: p.SessaoCaiu("a sessão do VIOS caiu")})
        secao = p.conferir(self.ctx(), op, self.processos(1, 2, 3), [], leitor)
        self.assertEqual(leitor.lidas, [1, 2])
        self.assertIn("a sessão do VIOS caiu depois de 1 ficha", secao.erro)
        self.assertEqual(len(secao.itens), 1)
        prog = self.progresso()
        self.assertEqual((prog["ultimo_ci"], prog["pendentes"]), (1, []))

    def test_bloqueio_inativo_sobe_e_guarda_progresso(self):
        op = p.opcoes(self.cfg)
        leitor = LeitorFalso({2: vios.BloqueioInativo("bloqueio de envios inativo")})
        with self.assertRaises(vios.BloqueioInativo):
            p.conferir(self.ctx(), op, self.processos(1, 2, 3), [], leitor)
        self.assertTrue(leitor.fechado)
        self.assertEqual(self.progresso()["ultimo_ci"], 1)

    def test_tempo_maximo(self):
        self.escrever_env(ORELHA_PARADOS_MINUTOS="1")
        op = p.opcoes(self.cfg)
        relogio = iter([0, 10, 100, 100])
        with mock.patch.object(p.time, "monotonic", lambda: next(relogio)):
            secao = p.conferir(self.ctx(), op, self.processos(1, 2, 3), [], LeitorFalso({}))
        self.assertEqual(secao.numeros["conferidos"], 1)
        self.assertTrue(any("ORELHA_PARADOS_MINUTOS" in a for a in secao.avisos))
        self.assertEqual(secao.erro, "")
        self.assertEqual(self.progresso()["ultimo_ci"], 1)

    def test_progresso_gravado_durante_a_leitura(self):
        op = p.opcoes(self.cfg)
        ctx = self.ctx()
        gravacoes = []
        original = ctx.gravar_historico
        ctx.gravar_historico = lambda nome, dados: (gravacoes.append(dados["ultimo_ci"]), original(nome, dados))[1]
        p.conferir(ctx, op, self.processos(*range(1, p.SALVAR_A_CADA + 3)), [], LeitorFalso({}))
        self.assertEqual(gravacoes, [p.SALVAR_A_CADA, p.SALVAR_A_CADA + 2])


class TestLeitorVios(ComConfig):
    """Só o que dá para conferir sem navegador: proteções antes de tocar no VIOS."""

    def test_pesquisa_recusa_formulario_que_nao_e_de_pesquisa(self):
        lista = "https://exemplo.vios.com.br/?pag=sys/processos/processos-lista.php"
        casos = {"endereço proibido": {"acao": "https://exemplo.vios.com.br/?act=del", "pagina": lista,
                                       "botao": "Pesquisar"},
                 "botão que grava": {"acao": lista, "pagina": lista, "botao": "Salvar"},
                 "tela desconhecida": {"acao": "https://exemplo.vios.com.br/?pag=sys/outra/tela.php",
                                       "pagina": "https://exemplo.vios.com.br/?pag=sys/outra/tela.php",
                                       "botao": "Pesquisar"}}
        for nome, dados in casos.items():
            with self.subTest(nome):
                ctx = self.ctx()
                ctx.driver = mock.Mock()
                ctx.driver.execute_script.return_value = dados
                leitor = p.LeitorVios(ctx, p.opcoes(self.cfg))
                with mock.patch.object(vios, "esperar", return_value=object()):
                    with self.assertRaises(vios.AcessoProibido):
                        leitor._pesquisar()
                # o JS da pesquisa nem rodou (só a leitura do form)
                self.assertEqual(ctx.driver.execute_script.call_count, 1)

    def test_tela_de_login(self):
        ctx = self.ctx()
        leitor = p.LeitorVios(ctx, p.opcoes(self.cfg))
        driver = mock.Mock(current_url="https://exemplo.vios.com.br/entrar.php?")
        self.assertTrue(leitor._na_tela_de_login(driver))
        driver = mock.Mock(current_url="https://exemplo.vios.com.br/?pag=x")
        driver.find_elements.return_value = []
        self.assertFalse(leitor._na_tela_de_login(driver))

    def test_ficha_que_cai_no_login_levanta_sessao_caiu(self):
        ctx = self.ctx()
        ctx.driver = mock.Mock(current_url="https://exemplo.vios.com.br/entrar.php?")
        leitor = p.LeitorVios(ctx, p.opcoes(self.cfg))
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar_ate", side_effect=vios.ViosErro("x")):
            with self.assertRaises(p.SessaoCaiu):
                leitor.ficha(p.Processo(ci=1))


if __name__ == "__main__":
    unittest.main()


class TestFiltroSemTarefa(ComConfig):
    """Padrão: o filtro nativo do VIOS (processos ativos sem tarefa aberta), por GET."""

    def test_url_so_get(self):
        url = p.url_sem_tarefa()
        for trecho in ("pesq[filtros_multi][]=ativos", "pesq[com_ou_sem_tipo_tarefa]=sem",
                       "pesq[flag_status_tipo_tarefa]=abertas", "pesq[limit]=500", "Pesq=Pesquisar"):
            self.assertIn(trecho, url)
        self.assertIn("pesq[tp_data]=data_cadastro&pesq[idata]=01/01/2026&pesq[fdata]=31/12/2026",
                      p.url_sem_tarefa(date(2026, 1, 1), date(2026, 12, 31)))

    def test_simulado(self):
        self.escrever_env(ORELHA_PARADOS_FONTE=None)
        s = p.executar(self.ctx(simulado_=True))
        self.assertEqual(s.erro, "")
        self.assertEqual([(i.grupo, i.nivel, i.titulo) for i in s.itens], [
            ("Trabalhista", "grave", "0000101-11.2026.8.06.0001"),   # 120 dias sem edição
            ("Trabalhista", "atencao", "CI 900403"),                 # sem número: vai o CI
            ("Cível Consumidor", "grave", "0000104-44.2024.5.07.0001"),
            ("Previdenciária", "atencao", "0000102-22.2025.4.05.8100"),
        ])
        self.assertIn("EMPRESA EXEMPLO LTDA · advogado: ANA FICTÍCIA · última edição", s.itens[0].detalhe)
        self.assertEqual((s.numeros["parados"], s.numeros["graves"]), (4, 2))
        self.assertTrue(s.itens[0].link.endswith("processos_id=900401"))

    def test_mais_de_500_le_por_ano_e_divide(self):
        self.escrever_env(ORELHA_PARADOS_FONTE=None, ORELHA_PARADOS_DESDE="01/01/2025")
        cheio = [p.Parado(ci=str(i)) for i in range(p.LIMITE_FILTRO)]
        chamadas = []

        def ler(ctx, a=None, b=None):
            chamadas.append((a, b))
            return "x"
        respostas = iter([cheio, cheio, [p.Parado(ci="a")], [p.Parado(ci="b")], [p.Parado(ci="c")]])
        ctx = self.ctx()
        ctx.driver = object()
        with mock.patch.object(p, "ler_sem_tarefa", side_effect=ler), mock.patch.object(p.vios, "abrir"), \
                mock.patch.object(p, "parados_do_html", side_effect=lambda h, base: next(respostas)):
            s = p.executar(ctx)
        self.assertEqual(chamadas[0], (None, None))
        self.assertEqual(chamadas[1], (date(2025, 1, 1), date(2025, 12, 31)))   # 2025 veio cheio: divide
        self.assertEqual(chamadas[2][0], date(2025, 1, 1))
        self.assertEqual(chamadas[-1], (date(2026, 1, 1), HOJE))
        self.assertEqual(s.numeros["parados"], 3)


class TestBuscaSemDesenhar(ComConfig):
    def _ctx(self, resposta):
        ctx = self.ctx()
        ctx.driver = mock.Mock()
        ctx.driver.execute_async_script.return_value = resposta
        return ctx

    def test_devolve_html_com_tabela(self):
        ctx = self._ctx('<title>Vios - Processos</title><table id="processos-lista"></table>')
        self.assertIn('id="processos-lista"', p.ler_sem_tarefa(ctx))
        url = ctx.driver.execute_async_script.call_args.args[1]
        self.assertTrue(url.startswith("https://exemplo.vios.com.br/") and "com_ou_sem_tipo_tarefa]=sem" in url)
        self.assertIn("method: 'GET'", ctx.driver.execute_async_script.call_args.args[0])

    def test_sem_tabela(self):
        self.assertEqual(p.ler_sem_tarefa(self._ctx("<title>Vios Jurídico - Processos</title>")), p.VAZIA_FILTRO)
        self.assertEqual(p.ler_sem_tarefa(self._ctx("<title>Login</title>")), "")
        with self.assertRaises(p.vios.ViosErro):
            p.ler_sem_tarefa(self._ctx("ERRO_ORELHA: TypeError"))
