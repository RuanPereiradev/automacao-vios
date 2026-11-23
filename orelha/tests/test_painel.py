"""Painel semanal de peças e audiências (funcoes/painel.py, nucleo/painel.py, nucleo/timbrado.py).
Dados 100% fictícios."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import main
from funcoes import painel, prazos
from nucleo import config, timbrado
from nucleo import painel as desenho
from nucleo.modelos import Contexto

PASTA = Path(__file__).resolve().parent.parent
HOJE = date(2026, 11, 6)
BASE = "https://exemplo.vios.com.br/"


def d(n):
    return HOJE + timedelta(days=n)


def tarefa(tipo, dias=0, responsavel="ANA FICTÍCIA", n=1, processo="0000001-00.2026.8.06.0000", hora="", **kw):
    return prazos.TarefaLista(titulo=tipo, tipo=tipo, responsavel=responsavel, conclusao=d(dias), limite=d(dias + 1),
                              link=f"{BASE}?pag=sys/processos/pxe.php&pxe_id={910000 + n}", hora=hora,
                              processo=processo, **kw)


def fila_de(tarefas, **kw):
    return painel.montar_fila(tarefas, HOJE, ["MINUTAR"], ["AUDIÊNCIA"], **kw)


def contexto(linhas="", historico=True):
    pasta = Path(tempfile.mkdtemp())
    env = pasta / ".env"
    env.write_text("SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n" + linhas, encoding="utf-8")
    eventos = []
    ctx = Contexto(driver=None, cfg=config.carregar(env, exigir_login=False, ambiente={}), hoje=HOJE,
                   emitir=lambda tipo, **dd: eventos.append((tipo, dd)), simulado=True, fixtures=PASTA / "fixtures",
                   saida=pasta / "dia", historico=(pasta / "historico") if historico else None, chave="painel", pdf=False)
    return ctx, eventos


class TestRegras(unittest.TestCase):
    def test_faixas(self):
        casos = {-3: ("vencida", "VENCIDA 3d"), 0: ("urgente", "URGENTE hoje"), 1: ("urgente", "URGENTE 1d"),
                 2: ("urgente", "URGENTE 2d"), 3: ("atencao", "ATENÇÃO 3d"), 7: ("atencao", "ATENÇÃO 7d"),
                 8: ("proxima", "PRÓXIMA 8d"), 14: ("proxima", "PRÓXIMA 14d"), 15: ("no_prazo", "NO PRAZO 15d")}
        for dias, esperado in casos.items():
            self.assertEqual(painel.faixa(dias), esperado, dias)

    def test_nome_proprio(self):
        self.assertEqual(painel.nome_proprio("JOANA CLÁUDIA DOTTO"), "Joana Cláudia Dotto")
        self.assertEqual(painel.nome_proprio("MARIA DA SILVA E SOUZA"), "Maria da Silva e Souza")
        self.assertEqual(painel.nome_proprio(""), "")

    def test_tipo_audiencia(self):
        self.assertEqual(painel.tipo_audiencia("AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026"), "UNA/INSTRUÇÃO")
        self.assertEqual(painel.tipo_audiencia("AUDIÊNCIA DE CONCILIAÇÃO (TRABALHISTA) 2026"), "DE CONCILIAÇÃO")
        self.assertEqual(painel.tipo_audiencia("AUDIÊNCIA PREVIDENCIÁRIA (PREVIDENCIÁRIO) 2026"), "PREVIDENCIÁRIA")

    def test_leitura(self):
        self.assertEqual([painel.leitura(t) for t in (0.711, 0.70, 0.613, 0.60, 0.556, None)],
                         ["Boa", "Boa", "Atenção", "Atenção", "Baixa", "—"])


class TestFila(unittest.TestCase):
    def test_o_que_entra_e_o_que_fica_de_fora(self):
        tarefas = [
            tarefa("MINUTAR CONTESTAÇÃO (TRABALHISTA) 2026", -2, n=1),
            tarefa("AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026", 3, n=2, hora="09:50"),
            tarefa("C: MINUTAR PARECER 2026", 1, n=3),                       # consultoria: entra como peça
            tarefa("INFORMAR AUDIÊNCIA (CÍVEL) 2026", 1, n=4),               # sobre a audiência: "outra"
            tarefa("ANALISAR PROCESSO (CÍVEL) 2026", 1, n=5),                # outro tipo: "outra"
            tarefa("MINUTAR RECURSO 2026", 30, n=6),                         # além de 14 dias: fora
            tarefa("MINUTAR EMBARGOS 2026", 2, n=7, etiqueta="CANCELADA"),   # cancelada: fora
            tarefa("MINUTAR INICIAL 2026", 2, n=8, concluida=True),          # concluída: fora
            tarefa("MINUTAR CONTESTAÇÃO (TRABALHISTA) 2026", -2, n=1),       # repetida: uma só
        ]
        fila, ignoradas = fila_de(tarefas)
        self.assertEqual([e.chave for e in fila], ["910001", "910005", "910003", "910004", "910002"])
        self.assertEqual([e.categoria for e in fila], ["peca", "outra", "peca", "outra", "audiencia"])
        self.assertEqual(ignoradas, {"sem_data": 0})
        # ORELHA_PAINEL_OUTRAS=nao: só peças e audiências, como antes de 23/11/2026
        fila, _ = fila_de(tarefas, outras=False)
        self.assertEqual([e.chave for e in fila], ["910001", "910003", "910002"])

    def test_sem_data_e_so_limite(self):
        sem = tarefa("MINUTAR A", 0, n=1)
        sem.conclusao = sem.limite = None
        so_limite = tarefa("MINUTAR B", 0, n=2)
        so_limite.conclusao = None
        fila, ignoradas = fila_de([sem, so_limite])
        self.assertEqual(ignoradas["sem_data"], 1)
        self.assertEqual([(e.chave, e.dias) for e in fila], [("910002", 1)])  # a limite faz as vezes da conclusão

    def test_ordem_e_responsavel(self):
        fila, _ = fila_de([tarefa("MINUTAR A", 5, "BRUNO FICTÍCIO", 1), tarefa("MINUTAR B", -1, "", 2),
                           tarefa("MINUTAR C", 5, "ANA FICTÍCIA, BRUNO FICTÍCIO", 3)])
        self.assertEqual([(e.dias, e.responsavel) for e in fila],
                         [(-1, "Sem responsável"), (5, "Ana Fictícia, Bruno Fictício"), (5, "Bruno Fictício")])
        self.assertEqual(fila[1].responsaveis, ("Ana Fictícia", "Bruno Fictício"))

    def test_carga(self):
        tarefas = ([tarefa("MINUTAR X", dias, "ANA FICTÍCIA", i) for i, dias in enumerate((-1, 2, 9), 1)]
                   + [tarefa("AUDIÊNCIA A 2026", 4, "ANA FICTÍCIA", 10), tarefa("MINUTAR Y", 1, "BRUNO FICTÍCIO", 11),
                      tarefa("MINUTAR Z", 3, "", 12), tarefa("ANALISAR PROCESSO 2026", 2, "ANA FICTÍCIA, BRUNO FICTÍCIO", 13)])
        fila, _ = fila_de(tarefas)
        c = {x["nome"]: x for x in painel.carga(fila, urgente_alto=3)}
        # a MINUTAR de daqui a 9 dias fica fora da semana do painel (até 7 dias depois do pedido)
        # a tarefa com dois responsáveis conta para os dois
        self.assertEqual(c["Ana Fictícia"], {"nome": "Ana Fictícia", "pecas": 2, "audiencias": 1, "outras": 1,
                                             "total": 4, "vencidas": 1, "urgente": 4, "destaque": True})
        self.assertEqual((c["Bruno Fictício"]["pecas"], c["Bruno Fictício"]["outras"], c["Bruno Fictício"]["total"]), (1, 1, 2))
        self.assertFalse(c["Bruno Fictício"]["destaque"])
        self.assertEqual([x["nome"] for x in painel.carga(fila)], ["Ana Fictícia", "Bruno Fictício", "Sem responsável"])

    def test_periodo_escolhido(self):
        tarefas = [tarefa("MINUTAR VENCIDA", -2, n=1), tarefa("MINUTAR HOJE", 0, n=2), tarefa("MINUTAR D3", 3, n=3),
                   tarefa("MINUTAR D10", 10, n=4), tarefa("MINUTAR D20", 20, n=5)]
        # de hoje até daqui a 14 dias: a vencida (aberta) entra; a de 20 dias não
        fila, _ = fila_de(tarefas, de=HOJE, ate=d(14))
        self.assertEqual([e.tarefa for e in fila], ["MINUTAR VENCIDA", "MINUTAR HOJE", "MINUTAR D3", "MINUTAR D10"])
        # de daqui a 5 dias até daqui a 12: as de hoje e de 3 dias ficam fora; a vencida continua
        fila, _ = fila_de(tarefas, de=d(5), ate=d(12))
        self.assertEqual([e.tarefa for e in fila], ["MINUTAR VENCIDA", "MINUTAR D10"])

    def test_periodo_padrao_e_escolhido(self):
        ctx, _ = contexto()
        self.assertEqual(painel.periodo(ctx, 7), (HOJE, d(7)))
        ctx.painel_ate = d(14)
        self.assertEqual(painel.periodo(ctx, 7), (HOJE, d(14)))
        ctx.painel_de, ctx.painel_ate = d(2), None
        self.assertEqual(painel.periodo(ctx, 7), (d(2), d(9)))

    def test_agenda_no_periodo_escolhido(self):
        tarefas = [tarefa("AUDIÊNCIA UNA 2026", 3, n=1), tarefa("AUDIÊNCIA UNA 2026", 12, n=2)]
        fila, _ = fila_de(tarefas, ate=d(14))
        self.assertEqual(len(painel.agenda_audiencias(fila, HOJE, 7)), 1)
        self.assertEqual(len(painel.agenda_audiencias(fila, HOJE, 7, HOJE, d(14))), 2)

    def test_agenda(self):
        tarefas = [tarefa("AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026", 1, n=1, hora="14:00"),
                   tarefa("AUDIÊNCIA DE CONCILIAÇÃO (TRABALHISTA) 2026", 1, n=2),                 # sem hora: depois
                   tarefa("AUDIÊNCIA PREVIDENCIÁRIA (PREVIDENCIÁRIO) 2026", 0, n=3, hora="09:00"),
                   tarefa("AUDIÊNCIA ANTIGA 2026", -1, n=4), tarefa("AUDIÊNCIA LONGE 2026", 8, n=5),
                   tarefa("MINUTAR NAO E AUDIENCIA", 1, n=6)]
        fila, _ = fila_de(tarefas)
        ag = painel.agenda_audiencias(fila, HOJE, 7)
        self.assertEqual([(a["data"], a["hora"], a["tipo"]) for a in ag],
                         [("06/11", "09:00", "PREVIDENCIÁRIA"), ("07/11", "14:00", "UNA/INSTRUÇÃO"),
                          ("07/11", "--:--", "DE CONCILIAÇÃO")])


class TestComparacao(unittest.TestCase):
    def test_nao_feitas_novas_e_taxa(self):
        fila, _ = fila_de([tarefa("MINUTAR A", 1, n=n) for n in (1, 2, 3)])
        base = {"data": d(-7).isoformat(), "fila": ["910001", "910002", "999001", "999002"]}
        comp = painel.comparar(fila, base, HOJE)
        self.assertEqual(comp["nao_feitas"], {"910001", "910002"})
        self.assertEqual(comp["novas"], {"910003"})
        self.assertEqual(comp["semana"], {"semana": "30/10–06/11", "fila_inicial": 4, "resolvidas": 2, "taxa": 0.5,
                                          "leitura": "Baixa", "aproximada": False})

    def test_base_vazia_nao_divide_por_zero(self):
        comp = painel.comparar([], {"data": d(-7).isoformat(), "fila": []}, HOJE)
        self.assertIsNone(comp["semana"]["taxa"])
        self.assertEqual(comp["semana"]["leitura"], "—")

    def test_escolhe_o_registro_certo(self):
        ctx, _ = contexto()
        ctx.simulado = False

        def grava(dia, **extra):
            ctx.gravar_historico(painel.nome_registro(dia), {"data": dia.isoformat(), "fila": ["1"], "tipos": "todas",
                                                             **extra})
        grava(d(-2))    # novo demais (execução de teste no meio da semana)
        grava(d(-6), tipos=painel.TIPOS_PECAS)  # só peças e audiências: não compara com a fila de todos os tipos
        grava(d(-7), total=7)
        grava(d(-9))
        grava(d(-60))   # velho demais
        ctx.gravar_historico("painel-simulado-" + d(-6).isoformat() + ".json", {"data": d(-6).isoformat(), "fila": ["x"]})
        self.assertEqual(painel.ler_base(ctx)["data"], d(-7).isoformat())
        self.assertEqual(painel.ler_base(ctx, painel.TIPOS_PECAS)["data"], d(-6).isoformat())
        # registro de antes do campo "tipos" é de peças e audiências
        ctx.gravar_historico(painel.nome_registro(d(-5)), {"data": d(-5).isoformat(), "fila": ["1"]})
        self.assertEqual(painel.ler_base(ctx, painel.TIPOS_PECAS)["data"], d(-5).isoformat())
        self.assertEqual(painel.ler_base(ctx)["data"], d(-7).isoformat())

    def test_registro_corrompido_cai_para_o_anterior(self):
        ctx, _ = contexto()
        ctx.simulado = False
        ctx.gravar_historico(painel.nome_registro(d(-9)), {"data": d(-9).isoformat(), "fila": ["1"], "tipos": "todas"})
        (ctx.historico / painel.nome_registro(d(-7))).write_text("{quebrado", encoding="utf-8")
        self.assertEqual(painel.ler_base(ctx)["data"], d(-9).isoformat())

    def test_sem_historico(self):
        ctx, _ = contexto(historico=False)
        ctx.simulado = False
        self.assertIsNone(painel.ler_base(ctx))


class TestExecutar(unittest.TestCase):
    def test_simulado_ponta_a_ponta(self):
        ctx, _ = contexto()
        secao = painel.executar(ctx)
        self.assertEqual(secao.chave, "painel")
        self.assertEqual(secao.erro, "")
        n = secao.numeros
        self.assertEqual(n["fila"], 36)  # o que a fixture tem (todos os tipos), até 7 dias depois, sem cancelada
        self.assertEqual(n["nao_feitas"] + n["novas"], n["fila"])
        self.assertEqual(n["destaque"], n["fila"])
        html = (ctx.saida / "painel-semanal.html").read_text(encoding="utf-8")
        self.assertIn("Painel Semanal — Semana de 06/11 a 13/11/2026", html)  # do dia do pedido até 7 dias depois
        self.assertIn("NÃO FEITAS", html)
        self.assertFalse((ctx.saida / "painel-semanal.pdf").exists())  # pdf=False
        registro = json.loads((ctx.historico / painel.nome_registro(HOJE, True)).read_text(encoding="utf-8"))
        self.assertEqual(registro["total"], n["fila"])
        self.assertEqual(registro["tipos"], "todas")
        self.assertIn("<th>Outras</th>", html)
        self.assertEqual(len(registro["semanas"]), 3)

    def test_nao_expoe_nomes_nos_numeros_da_vila(self):
        ctx, _ = contexto()
        secao = painel.executar(ctx)
        self.assertEqual(secao.numeros_seguros(), secao.numeros)
        self.assertTrue(all(isinstance(v, (int, float)) for v in secao.numeros.values()))

    def test_simulado_com_periodo_escolhido(self):
        ctx, _ = contexto()
        ctx.painel_de, ctx.painel_ate = HOJE, d(14)
        painel.executar(ctx)
        html = (ctx.saida / "painel-semanal.html").read_text(encoding="utf-8")
        self.assertIn("Painel Semanal — Semana de 06/11 a 20/11/2026", html)
        self.assertIn("Agenda de audiências — 06/11 a 20/11", html)

    def test_periodo_que_nao_comeca_hoje_nao_vira_base(self):
        ctx, _ = contexto()
        ctx.painel_de, ctx.painel_ate = d(7), d(14)
        secao = painel.executar(ctx)
        self.assertFalse((ctx.historico / painel.nome_registro(HOJE, True)).exists())
        self.assertTrue(any("não entra na comparação" in a for a in secao.avisos))

    def test_primeira_edicao_lista_a_fila_toda(self):
        ctx, _ = contexto()
        with mock.patch.object(painel, "ler_base", return_value=None):
            secao = painel.executar(ctx)
        self.assertNotIn("nao_feitas", secao.numeros)
        html = (ctx.saida / "painel-semanal.html").read_text(encoding="utf-8")
        self.assertIn("FILA ABERTA", html)
        self.assertIn("primeira edição", html)
        self.assertIn("1ª edição", secao.resumo)

    def test_leitura_incompleta_nao_grava_registro(self):
        ctx, _ = contexto()
        original = painel._ler

        def lendo(ctx_, dias, avisos, ate=None):
            avisos.append("a lista de tarefas não apareceu")
            return original(ctx_, dias, avisos, ate)
        with mock.patch.object(painel, "_ler", side_effect=lendo):
            secao = painel.executar(ctx)
        self.assertFalse((ctx.historico / painel.nome_registro(HOJE, True)).exists())
        self.assertTrue(any("NÃO foi gravado" in a for a in secao.avisos))

    def test_pdf_que_falha_fica_o_html(self):
        ctx, _ = contexto()
        ctx.pdf = True
        with mock.patch.object(desenho.relatorio, "escrever_pdf", side_effect=RuntimeError("sem Chrome\nstack")):
            secao = painel.executar(ctx)
        self.assertTrue((ctx.saida / "painel-semanal.html").exists())
        self.assertTrue(any("sem Chrome" in a for a in secao.avisos))


class TestDesenho(unittest.TestCase):
    def dados(self, **extra):
        ctx, _ = contexto()
        fila, ign = fila_de([tarefa("MINUTAR <b>X</b>", -1, "ANA <I>FICTÍCIA", 1, processo="CI 384252")])
        dados, _, _ = painel.montar_dados(ctx, fila, ign, [], {"dias_agenda": 7, "urgente_alto": 15, "boa": 70, "atencao": 60})
        dados.update(extra)
        return dados

    def test_html_no_papel_timbrado_e_escapado(self):
        html = desenho.montar_html(self.dados())
        self.assertIn("data:image/png;base64,", html)
        self.assertEqual(html.count("data:image/png;base64,"), 3)  # marca d'água, cabeçalho, rodapé
        self.assertIn("&lt;b&gt;X&lt;/b&gt;", html)
        self.assertNotIn("<b>X</b>", html)
        self.assertIn('class="num ci"', html)  # CI em itálico
        self.assertNotIn("<script", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_timbrado_tem_as_margens_do_modelo(self):
        html = timbrado.pagina("T", "<p>x</p>")
        self.assertIn("height: 46mm", html)   # topo
        self.assertIn("height: 40mm", html)   # base
        self.assertIn("padding: 0 20mm 0 30mm", html)
        self.assertIn("size: A4", html)

    def test_imagens_do_timbrado_existem(self):
        for nome in timbrado.IMAGENS.values():
            self.assertTrue((timbrado.PASTA_IMAGENS / nome).is_file(), nome)


class TestMainPainel(unittest.TestCase):
    def test_painel_sozinho_nao_gera_relatorio_do_dia(self):
        pasta = Path(tempfile.mkdtemp())
        env = pasta / ".env"
        env.write_text(f"ORELHA_SAIDA={pasta / 'saida'}\nORELHA_LOGS={pasta / 'logs'}\nVILA_URL=\n", encoding="utf-8")
        codigo = main.main(["--env", str(env), "--data", "2026-11-06", "--simulado", "--sem-pdf", "--funcoes", "painel"])
        dia = pasta / "saida" / "simulado-2026-11-06"
        self.assertEqual(codigo, 0)
        self.assertTrue((dia / "painel-semanal.html").exists())
        self.assertFalse((dia / "relatorio.html").exists())

    def test_painel_nao_vem_por_padrao_e_nao_entra_no_relatorio_do_dia(self):
        from funcoes import PADRAO, REGISTRO
        self.assertIn("painel", REGISTRO)
        self.assertNotIn("painel", PADRAO)
        pasta = Path(tempfile.mkdtemp())
        env = pasta / ".env"
        env.write_text(f"ORELHA_SAIDA={pasta / 'saida'}\nORELHA_LOGS={pasta / 'logs'}\nVILA_URL=\n", encoding="utf-8")
        main.main(["--env", str(env), "--data", "2026-11-06", "--simulado", "--sem-pdf", "--funcoes", "prazos,painel"])
        dia = pasta / "saida" / "simulado-2026-11-06"
        self.assertTrue((dia / "painel-semanal.html").exists())
        self.assertNotIn("Painel semanal", (dia / "relatorio.html").read_text(encoding="utf-8"))
        self.assertEqual([s["chave"] for s in json.loads((dia / "resumo.json").read_text(encoding="utf-8"))["secoes"]],
                         ["prazos"])


if __name__ == "__main__":
    unittest.main()
