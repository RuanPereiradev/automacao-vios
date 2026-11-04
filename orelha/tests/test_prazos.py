"""Placar de tarefas atrasadas e tendência de 7 dias (funcoes/prazos.py). Dados 100% fictícios."""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from funcoes import agenda, prazos
from nucleo import config, simulado, vios
from nucleo.modelos import Contexto

PASTA = Path(__file__).resolve().parent.parent
HOJE = date(2026, 11, 4)
BASE = "https://exemplo.vios.com.br/"


def contexto(hoje=HOJE, simulado_=True, linhas="", driver=None, historico=True, fonte="calendario"):
    pasta = Path(tempfile.mkdtemp())
    env = pasta / ".env"
    env.write_text("SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n"
                   + (f"ORELHA_PRAZOS_FONTE={fonte}\n" if fonte else "") + linhas, encoding="utf-8")
    eventos = []
    ctx = Contexto(driver=driver, cfg=config.carregar(env, exigir_login=False, ambiente={}), hoje=hoje,
                   emitir=lambda tipo, **d: eventos.append((tipo, d)), simulado=simulado_,
                   fixtures=PASTA / "fixtures", saida=pasta / "dia",
                   historico=(pasta / "historico") if historico else None, chave="prazos")
    return ctx, eventos


def tarefa(titulo, conclusao=None, limite=None, responsavel="", n=1, concluida=False):
    return agenda.Evento(titulo, dia=conclusao, categoria="tarefa", conclusao=conclusao, limite=limite,
                         responsavel=responsavel, concluida=concluida,
                         link=f"{BASE}?pag=sys/processos/pxe.php&pxe_id={900300 + n}")


def d(n):
    return HOJE + timedelta(days=n)


class TestPlacar(unittest.TestCase):
    def test_niveis(self):
        tarefas = [
            tarefa("ATRASADA", d(-2), d(3), "Ana Fictícia", 1),
            tarefa("LIMITE VENCIDO", d(-3), d(-1), "Ana Fictícia", 2),
            tarefa("MUITO ATRASADA", d(-10), d(-9), "Ana Fictícia", 8),
            tarefa("LIMITE HOJE", d(0), d(0), "Bruno Fictício", 3),
            tarefa("NO PRAZO", d(0), d(2), "Bruno Fictício", 4),
            tarefa("FUTURA", d(2), d(5), "Bruno Fictício", 5),
            tarefa("CONCLUÍDA", d(-5), d(-4), "Carla Fictícia", 6, concluida=True),
            tarefa("SEM LIMITE", d(-8), None, "", 7),
        ]
        itens, numeros = prazos.placar(tarefas, HOJE)
        self.assertEqual([(i.grupo, i.titulo, i.nivel) for i in itens], [
            ("Vencem hoje", "LIMITE HOJE", "info"),       # vence hoje: não é atrasada
            ("Vencem hoje", "NO PRAZO", "info"),
            ("Ana Fictícia", "MUITO ATRASADA", "grave"),  # mais de 7 dias de atraso
            ("Ana Fictícia", "LIMITE VENCIDO", "atencao"),
            ("Ana Fictícia", "ATRASADA", "atencao"),
            ("Sem responsável identificado", "SEM LIMITE", "grave"),
        ])
        self.assertEqual(itens[0].detalhe, "responsável: Bruno Fictício · para conclusão 04/11/2026 (hoje) · "
                                           "limite 04/11/2026 (hoje)")
        self.assertEqual(itens[3].detalhe, "para conclusão 01/11/2026 (há 3 dias) · limite 03/11/2026 (venceu há 1 dia)")
        self.assertEqual(itens[5].detalhe, "para conclusão 27/10/2026 (há 8 dias) · data limite não lida")
        self.assertEqual((numeros["atrasadas"], numeros["graves"], numeros["vencem_hoje"]), (4, 2, 2))
        self.assertEqual(numeros["destaque"], 4)  # o cartão do relatório mostra só as atrasadas
        self.assertEqual(numeros["pessoas_com_atraso"], 1)
        self.assertEqual((numeros["sem_responsavel"], numeros["sem_data_limite"]), (1, 1))
        self.assertEqual(numeros["por_responsavel"], {
            "Ana Fictícia": {"atrasadas": 3, "graves": 1},
            "Sem responsável identificado": {"atrasadas": 1, "graves": 1}})

    def test_idade_configuravel(self):
        tarefas = [tarefa("A", d(-3), d(-2), "Ana Fictícia", 1), tarefa("B", d(-8), d(-7), "Ana Fictícia", 2)]
        _, n7 = prazos.placar(tarefas, HOJE)
        _, n2 = prazos.placar(tarefas, HOJE, dias_grave=2)
        self.assertEqual((n7["graves"], n2["graves"]), (1, 2))
        self.assertEqual(prazos.classificar(tarefa("C", d(-7), None), HOJE), ("atrasada", 7))  # 7 dias: atenção
        _, n = prazos.placar([tarefa("C", d(-7), None, "Ana Fictícia")], HOJE)
        self.assertEqual(n["graves"], 0)

    def test_ordem_dos_grupos_e_varios_responsaveis(self):
        tarefas = [tarefa("A1", d(-1), d(1), "Ana Fictícia", 1),
                   tarefa("B1", d(-9), d(-8), "Bruno Fictício, Carla Fictícia", 2)]
        itens, numeros = prazos.placar(tarefas, HOJE)
        self.assertEqual([i.grupo for i in itens], ["Bruno Fictício", "Ana Fictícia"])  # quem tem grave primeiro
        self.assertIn("responsáveis: Bruno Fictício, Carla Fictícia", itens[0].detalhe)
        self.assertEqual(prazos.responsavel_principal("Eva Fictícia e Davi Fictício"), "Eva Fictícia")
        self.assertEqual(prazos.responsavel_principal(""), "")

    def test_tarefas_abertas(self):
        evs = [tarefa("X", d(-1), None, n=1), tarefa("X", d(-1), None, n=1), tarefa("Y", d(-2), concluida=True, n=2),
               agenda.Evento("Finados", dia=d(-2), categoria="feriado"),
               agenda.Evento("Reunião", dia=d(-1), categoria="compromisso")]
        self.assertEqual([t.titulo for t in prazos.tarefas_abertas(evs)], ["X"])
        ev = agenda.Evento("Z", dia=d(-1), categoria="tarefa", link="l")
        self.assertEqual(prazos.tarefas_abertas([ev], "limite")[0].limite, d(-1))
        self.assertIsNone(ev.conclusao)

    def test_precisa_ficha(self):
        self.assertTrue(prazos.precisa_ficha(tarefa("A", d(-1)), HOJE))
        self.assertTrue(prazos.precisa_ficha(tarefa("A", d(0), None, "Ana Fictícia"), HOJE))
        self.assertFalse(prazos.precisa_ficha(tarefa("A", d(-1), d(1), "Ana Fictícia"), HOJE))
        self.assertFalse(prazos.precisa_ficha(tarefa("A", d(1)), HOJE))
        sem_link = tarefa("A", d(-1))
        sem_link.link = ""
        self.assertFalse(prazos.precisa_ficha(sem_link, HOJE))

    def test_completar(self):
        ev = prazos.completar(tarefa("A", d(-1), None, "Ana Fictícia"),
                              {"responsavel": "Outra Pessoa", "limite": d(1), "concluida_em": d(-1)})
        self.assertEqual((ev.responsavel, ev.limite, ev.concluida), ("Ana Fictícia", d(1), True))

    def test_leitura_pelo_html_com_tooltip(self):
        html = simulado.substituir((PASTA / "fixtures" / "prazos" / "calendario.html").read_text(encoding="utf-8"), HOJE)
        brutos, _ = agenda.eventos_do_html(html, BASE)
        tarefas = prazos.tarefas_abertas(agenda.montar_eventos(brutos))
        self.assertEqual([t.pxe_id for t in tarefas], ["900201", "900203", "900204"])  # a concluída sai
        itens, numeros = prazos.placar(tarefas, HOJE)
        self.assertEqual([(i.grupo, i.nivel) for i in itens],
                         [("Vencem hoje", "info"), ("Ana Fictícia", "atencao"), ("Bruno Fictício", "atencao")])
        self.assertEqual((numeros["atrasadas"], numeros["vencem_hoje"]), (2, 1))


class TestTendencia(unittest.TestCase):
    def test_puras(self):
        self.assertEqual(prazos.comparar({"atrasadas": 7, "graves": 4}, {"atrasadas": 5, "graves": 6}),
                         {"atrasadas": 2, "graves": -2})
        self.assertIsNone(prazos.comparar({"atrasadas": 1}, None))
        self.assertIsNone(prazos.comparar({"atrasadas": 1}, {"atrasadas": "x", "graves": 1}))
        self.assertEqual(prazos.nome_registro(HOJE), "prazos-2026-11-04.json")
        self.assertEqual(prazos.nome_registro(HOJE, True), "prazos-simulado-2026-11-04.json")
        r = prazos.registro({"atrasadas": 3, "graves": 1, "por_responsavel": {"Ana Fictícia": {"atrasadas": 3}}}, HOJE)
        self.assertEqual(r["data"], "2026-11-04")

    def test_resumo(self):
        self.assertEqual(prazos.montar_resumo({"atrasadas": 0}), "Nenhuma tarefa atrasada.")
        self.assertEqual(prazos.montar_resumo({"atrasadas": 0, "vencem_hoje": 3}), "Nenhuma tarefa atrasada. 3 vencem hoje.")
        self.assertEqual(prazos.montar_resumo({"atrasadas": 1, "graves": 1, "pessoas_com_atraso": 1, "vencem_hoje": 1}),
                         "1 tarefa atrasada, 1 há mais de 7 dias, com 1 responsável. 1 vence hoje.")
        self.assertEqual(prazos.montar_resumo({"atrasadas": 3, "graves": 0, "pessoas_com_atraso": 2},
                                              {"atrasadas": -1, "graves": 0}, {"atrasadas": 4, "graves": 0}),
                         "3 tarefas atrasadas, 0 há mais de 7 dias, com 2 responsáveis. "
                         "Há 7 dias eram 4 atrasadas (-1), 0 delas há mais de 7 dias (0).")

    def test_grava_e_compara_com_7_dias_antes(self):
        ctx, _ = contexto(simulado_=False)
        ctx.gravar_historico("prazos-2026-10-28.json", {"data": "2026-10-28", "atrasadas": 10, "graves": 1})
        ctx.gravar_historico("prazos-2026-10-29.json", {"data": "2026-10-29", "atrasadas": 99, "graves": 99})
        variacao, anterior, avisos = prazos.tendencia(ctx, {"atrasadas": 7, "graves": 3, "por_responsavel": {}})
        self.assertEqual(variacao, {"atrasadas": -3, "graves": 2})
        self.assertEqual(anterior["atrasadas"], 10)
        self.assertEqual(avisos, [])
        self.assertEqual(ctx.ler_historico("prazos-2026-11-04.json")["atrasadas"], 7)
        # sem registro de 7 dias antes: não compara (e não pega a fixture fora do simulado)
        ctx, _ = contexto(simulado_=False)
        self.assertEqual(prazos.tendencia(ctx, {"atrasadas": 1, "graves": 0})[:2], (None, None))

    def test_sem_pasta_de_historico(self):
        ctx, _ = contexto(historico=False)
        variacao, anterior, avisos = prazos.tendencia(ctx, {"atrasadas": 1})
        self.assertIsNone(variacao)
        self.assertTrue(avisos)


class TestFichas(unittest.TestCase):
    def test_limite_e_falhas(self):
        ctx, _ = contexto(simulado_=False, driver=object())
        tarefas = [tarefa(f"T{n}", d(-1), None, "", n) for n in range(4)]

        def texto(c, ev, area):
            if ev.titulo == "T1":
                raise vios.ViosErro("não abriu")
            return "Responsáveis: Eva Fictícia\nLimite 01/11/2026"

        with mock.patch.object(prazos, "_texto_ficha", side_effect=texto):
            lidas, fora, falhas = prazos.ler_fichas(ctx, tarefas, 3)
        self.assertEqual((lidas, fora, falhas), (2, 1, 1))
        self.assertEqual((tarefas[0].responsavel, tarefas[0].limite), ("Eva Fictícia", date(2026, 11, 1)))
        self.assertEqual(tarefas[3].responsavel, "")

    def test_bloqueio_inativo_para_tudo(self):
        ctx, _ = contexto(simulado_=False, driver=object())
        with mock.patch.object(prazos, "_texto_ficha", side_effect=vios.BloqueioInativo("sem bloqueio")):
            with self.assertRaises(vios.BloqueioInativo):
                prazos.ler_fichas(ctx, [tarefa("T", d(-1))], 5)

    def test_ficha_real_abre_por_get(self):
        ctx, _ = contexto(simulado_=False, driver=object())
        ev = tarefa("T", d(-1))
        with mock.patch.object(prazos.vios, "abrir") as abrir, \
                mock.patch.object(prazos.vios, "texto_pagina", return_value="Responsável: Ana Fictícia"):
            self.assertEqual(prazos._texto_ficha(ctx, ev, None), "Responsável: Ana Fictícia")
        abrir.assert_called_once_with(ctx, ev.link)

    def test_zero_fichas(self):
        ctx, _ = contexto(simulado_=False, driver=object())
        with mock.patch.object(prazos, "_texto_ficha") as texto:
            self.assertEqual(prazos.ler_fichas(ctx, [tarefa("T", d(-1))], 0), (0, 1, 0))
        texto.assert_not_called()


class TestExecutar(unittest.TestCase):
    def test_simulado(self):
        ctx, eventos = contexto()
        s = prazos.executar(ctx)
        self.assertEqual((s.chave, s.erro), ("prazos", ""))
        self.assertEqual(eventos, [("fase", {"fase": "lendo_calendario"})])
        self.assertEqual([(i.grupo, i.nivel) for i in s.itens], [
            ("Vencem hoje", "info"),                                   # a da Carla vence hoje: não é atrasada
            ("Bruno Fictício", "grave"), ("Bruno Fictício", "atencao"),   # grave = mais de 7 dias de atraso
            ("Ana Fictícia", "atencao"), ("Ana Fictícia", "atencao"),
            ("Eva Fictícia", "atencao"),                               # Eva veio da ficha da tarefa
            ("Sem responsável identificado", "atencao")])
        n = s.numeros
        self.assertEqual((n["atrasadas"], n["graves"], n["vencem_hoje"], n["lidas"]), (6, 1, 1, 8))
        self.assertEqual((n["variacao_7d_atrasadas"], n["variacao_7d_graves"]), (1, -1))  # fixture: 5 e 2
        self.assertIn("Há 7 dias eram 5 atrasadas (+1)", s.resumo)
        self.assertNotIn("por_responsavel", s.numeros_seguros())
        self.assertTrue(any("sem responsável" in a for a in s.avisos))
        # meses lidos (padrão 2 anteriores): o que vence antes de 01/09/2026 fica de fora, com aviso
        self.assertTrue(any("antes de 01/09/2026 não entram no placar" in a for a in s.avisos))
        gravado = ctx.ler_historico("prazos-simulado-2026-11-04.json")
        self.assertEqual((gravado["atrasadas"], gravado["graves"], gravado["vencem_hoje"]), (6, 1, 1))
        self.assertIsNone(ctx.ler_historico("prazos-2026-11-04.json"))  # o histórico de verdade fica limpo
        # nada de nome de pessoa nos eventos da função
        self.assertNotIn("Fictíci", json.dumps(eventos, ensure_ascii=False))

    def test_real_sem_filtro_avisa(self):
        ctx, _ = contexto(simulado_=False, driver=object(), linhas="ORELHA_PRAZOS_MESES_ANTERIORES=1\n")
        with mock.patch.object(agenda, "ler_calendario", return_value=([], [])) as ler, \
                mock.patch.object(prazos, "_texto_ficha") as ficha:
            s = prazos.executar(ctx)
        self.assertEqual(ler.call_args[1]["meses_antes"], 1)
        self.assertEqual(ler.call_args[1]["prefixo"], "PRAZOS")
        ficha.assert_not_called()
        self.assertTrue(any("filtro da equipe" in a for a in s.avisos))
        self.assertTrue(any("nenhuma tarefa aberta" in a for a in s.avisos))
        self.assertEqual(s.resumo, "Nenhuma tarefa atrasada.")

    def test_real_com_api(self):
        ctx, _ = contexto(simulado_=False, driver=object(),
                          linhas="ORELHA_PRAZOS_FILTROS=pesq[concluida]=N\nORELHA_PRAZOS_ABRIR_TAREFAS=0\n")
        api = json.loads(simulado.substituir((PASTA / "fixtures" / "prazos" / "eventos.json").read_text(encoding="utf-8"), HOJE))
        with mock.patch.object(agenda, "ler_calendario", return_value=([{"api": api, "html": ""}], [])):
            s = prazos.executar(ctx)
        self.assertFalse(any("filtro da equipe" in a for a in s.avisos))
        self.assertEqual(s.numeros["sem_responsavel"], 2)  # sem abrir fichas
        self.assertTrue(any("ficaram sem conferir a ficha" in a for a in s.avisos))
        self.assertTrue(s.itens[0].link.startswith("https://exemplo.vios.com.br/?pag=sys/processos/pxe.php"))


if __name__ == "__main__":
    unittest.main()


class TestListaDeTarefas(unittest.TestCase):
    """Fonte padrão: a lista de tarefas do VIOS (pxe-lista.php), lida por GET."""

    def test_url_so_get_e_filtros(self):
        url = prazos.url_lista("data_limite", date(2000, 1, 1), HOJE)
        self.assertTrue(url.startswith("?pag=sys/processos/pxe-lista.php&"))
        for trecho in ("pesq[flag_conclusao]=0", "pesq[tp_data]=data_limite", "pesq[idata]=01/01/2000",
                       "pesq[fdata]=04/11/2026", "pesq[limit]=1000"):
            self.assertIn(trecho, url)
        self.assertNotIn("9999999", url)  # o VIOS recusa limite acima de 1000 (página sem tabela)
        self.assertNotIn("usuarios_id", url)  # sem responsável = equipe toda

    def test_janelas(self):
        js = prazos.janelas(date(2000, 1, 1), HOJE - timedelta(days=1), HOJE)
        self.assertEqual(js[0], (date(2000, 1, 1), HOJE - timedelta(days=366)))
        self.assertEqual(js[1][0], HOJE - timedelta(days=365))
        self.assertEqual(js[-1][1], HOJE - timedelta(days=1))
        for (a, b), (c, _) in zip(js, js[1:]):
            self.assertEqual(c, b + timedelta(days=1))  # sem buraco nem sobreposição
        self.assertTrue(all((b - a).days <= 30 for a, b in js[1:]))

    def test_responsaveis_da_celula(self):
        self.assertEqual(prazos.responsaveis_da_celula(
            "Responsável do processo: CHEFE FICTÍCIO Responsável(eis): ANA FICTÍCIA, BRUNO FICTÍCIO"),
            "ANA FICTÍCIA, BRUNO FICTÍCIO")
        self.assertEqual(prazos.responsaveis_da_celula("Responsável do processo: CHEFE FICTÍCIO"), "")
        # como fica depois de trocar os <br> da tela por " ; "
        self.assertEqual(prazos.responsaveis_da_celula(
            "Responsável do processo: CHEFE FICTÍCIO ; ; Responsável(eis): ANA FICTÍCIA ; BRUNO FICTÍCIO"),
            "ANA FICTÍCIA, BRUNO FICTÍCIO")

    def test_dois_responsaveis_na_tela_nao_grudam(self):
        ctx, _ = contexto(fonte="")
        t = prazos.tarefas_da_lista(simulado.ler(ctx, "lista.html"))[4]
        self.assertEqual(t.responsavel, "BRUNO FICTÍCIO, DANIEL FICTÍCIO")
        self.assertEqual(prazos.responsavel_principal(t.responsavel), "BRUNO FICTÍCIO")

    def test_le_a_fixture(self):
        ctx, _ = contexto(fonte="")
        html = simulado.ler(ctx, "lista.html")
        tarefas = prazos.tarefas_da_lista(html, "https://exemplo.vios.com.br/")
        self.assertEqual(len(tarefas), 7)
        t = tarefas[1]
        self.assertEqual((t.titulo, t.responsavel), ("MINUTAR CONTESTAÇÃO (TRABALHISTA) 2026", "BRUNO FICTÍCIO"))
        self.assertEqual((t.conclusao, t.limite), (HOJE - timedelta(days=2), HOJE))
        self.assertEqual(t.link, "https://exemplo.vios.com.br/?pag=sys/processos/pxe.php&pxe_id=900202")
        self.assertIsNone(tarefas[5].limite)

    def test_juntar_sem_repetir(self):
        a = prazos.TarefaLista("X", link="https://e/?pag=sys/processos/pxe.php&pxe_id=1")
        b = prazos.TarefaLista("Y", link="https://e/?pag=sys/processos/pxe.php&pxe_id=2")
        self.assertEqual(len(prazos.juntar_listas([[a, b], [a]])), 2)

    def test_simulado_lista(self):
        ctx, eventos = contexto(fonte="")
        s = prazos.executar(ctx)
        self.assertEqual((s.chave, s.erro), ("prazos", ""))
        n = s.numeros
        self.assertEqual((n["atrasadas"], n["graves"], n["vencem_hoje"], n["lidas"]), (6, 1, 1, 7))
        self.assertEqual(n["pessoas_com_atraso"], 4)
        self.assertEqual([(i.grupo, i.titulo) for i in s.itens if i.nivel == "grave"],
                         [("BRUNO FICTÍCIO", "PROTOCOLAR INICIAL (PREVIDENCIÁRIO) 2026")])  # 10 dias de atraso
        self.assertEqual(s.itens[0].grupo, "Vencem hoje")
        self.assertFalse(any("não entram no placar" in a for a in s.avisos))
        self.assertNotIn("FICTÍCI", json.dumps(eventos, ensure_ascii=False).upper())

    def test_real_le_por_janelas_e_nao_repete(self):
        ctx, _ = contexto(simulado_=False, driver=object(), fonte="")
        html = simulado.ler(ctx, "lista.html")
        with mock.patch.object(prazos, "ler_lista", return_value=html) as ler:
            s = prazos.executar(ctx)
        chamadas = [c.args for c in ler.call_args_list]
        self.assertEqual([c[1] for c in chamadas[:-2]], ["data_prevista"] * (len(chamadas) - 2))
        self.assertEqual(chamadas[-3][3], HOJE - timedelta(days=1))
        self.assertEqual((chamadas[-2][1], chamadas[-2][3]), ("data_limite", HOJE))
        self.assertEqual(chamadas[-1][1:], ("data_prevista", HOJE, HOJE))
        self.assertEqual((s.numeros["atrasadas"], s.numeros["vencem_hoje"]), (6, 1))  # sem repetir entre leituras

    def test_lista_cheia_divide_o_periodo(self):
        ctx, _ = contexto(simulado_=False, driver=object(), fonte="")
        cheia = [prazos.TarefaLista("T", link=f"l{i}") for i in range(prazos.LISTA_MAXIMO)]
        pequena = [prazos.TarefaLista("U", link="u1")]
        periodos = []

        def ler(ctx_, tp, a, b):
            periodos.append((a, b))
            return "x"
        with mock.patch.object(prazos, "ler_lista", side_effect=ler), \
                mock.patch.object(prazos, "tarefas_da_lista",
                                  side_effect=lambda h, base: cheia if len(periodos) == 1 else pequena):
            avisos = []
            r = prazos.ler_periodo(ctx, "data_prevista", date(2026, 10, 1), date(2026, 10, 31), [0], 60, avisos)
        self.assertEqual(periodos, [(date(2026, 10, 1), date(2026, 10, 31)), (date(2026, 10, 1), date(2026, 10, 16)),
                                    (date(2026, 10, 17), date(2026, 10, 31))])
        self.assertEqual(len(r), 2)

    def test_limite_de_paginas_avisa(self):
        ctx, _ = contexto(simulado_=False, driver=object(), fonte="", linhas="ORELHA_PRAZOS_MAX_PAGINAS=2\n")
        with mock.patch.object(prazos, "ler_lista", return_value="<table></table>"):
            s = prazos.executar(ctx)
        self.assertTrue(any("limite de 2 páginas" in a for a in s.avisos))



class TestLerListaSemTabela(unittest.TestCase):
    def _ctx(self, estado):
        ctx, _ = contexto(simulado_=False, driver=mock.MagicMock(), fonte="")
        ctx.driver.execute_script.return_value = estado
        return ctx

    def test_sem_resultado_e_lista_vazia(self):
        ctx = self._ctx({"titulo": "Vios Jurídico - Tarefas", "limite": False})
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar", side_effect=vios.ViosErro("x")):
            self.assertEqual(prazos.ler_lista(ctx, "data_prevista", HOJE, HOJE), prazos.VAZIA)
        self.assertEqual(prazos.tarefas_da_lista(prazos.VAZIA), [])

    def test_limite_recusado_ou_outra_tela_avisa(self):
        for estado in ({"titulo": "", "limite": True}, {"titulo": "Vios Jurídico - Login", "limite": False}):
            ctx = self._ctx(estado)
            with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar", side_effect=vios.ViosErro("x")):
                self.assertEqual(prazos.ler_lista(ctx, "data_prevista", HOJE, HOJE), "")
