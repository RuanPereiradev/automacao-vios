"""Agenda e leitura do calendário (funcoes/agenda.py). Dados 100% fictícios."""
import tempfile
import unittest
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest import mock

from funcoes import agenda
from nucleo import config, simulado
from nucleo.modelos import Contexto, Secao

PASTA = Path(__file__).resolve().parent.parent
HOJE = date(2026, 11, 4)  # quarta-feira
BASE = "https://exemplo.vios.com.br/"


def fixture(chave, nome, hoje=HOJE):
    return simulado.substituir((PASTA / "fixtures" / chave / nome).read_text(encoding="utf-8"), hoje)


def cfg(linhas=""):
    pasta = Path(tempfile.mkdtemp())
    env = pasta / ".env"
    env.write_text("SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n" + linhas, encoding="utf-8")
    return config.carregar(env, exigir_login=False, ambiente={})


def contexto(hoje=HOJE, simulado_=True, linhas="", driver=None, fonte="calendario"):
    pasta = Path(tempfile.mkdtemp())
    eventos = []
    linhas = (f"ORELHA_AGENDA_TAREFAS_FONTE={fonte}\n" if fonte else "") + linhas
    ctx = Contexto(driver=driver, cfg=cfg(linhas), hoje=hoje, emitir=lambda tipo, **d: eventos.append((tipo, d)),
                   simulado=simulado_, fixtures=PASTA / "fixtures", saida=pasta / "dia",
                   historico=pasta / "historico", chave="agenda")
    return ctx, eventos


class TestTexto(unittest.TestCase):
    def test_dobrar_mantem_tamanho(self):
        for t in ("Responsáveis: Ana Fictícia", "AUDIÊNCIA · ção", "ß"):
            self.assertEqual(len(agenda.dobrar(t)), len(t))
        self.assertEqual(agenda.dobrar("Perícia"), "PERICIA")

    def test_hora(self):
        self.assertEqual(agenda._hora("14:00"), "14:00")
        self.assertEqual(agenda._hora("9h30"), "09:30")
        self.assertEqual(agenda._hora("14h"), "14:00")
        self.assertEqual(agenda._hora("dia todo"), "")
        self.assertEqual(agenda._sem_hora("14:00 AUDIÊNCIA UNA"), "AUDIÊNCIA UNA")
        self.assertEqual(agenda._sem_hora("9h - REUNIÃO"), "REUNIÃO")
        self.assertEqual(agenda._sem_hora("2026 PLANEJAMENTO"), "2026 PLANEJAMENTO")

    def test_texto_de_html(self):
        self.assertEqual(agenda.texto_de_html("<p>Um <b>dois</b></p><script>x()</script><div>três</div>"),
                         "Um dois\ntrês")
        self.assertEqual(agenda.texto_de_html("sem tags"), "sem tags")

    def test_campos_do_texto(self):
        c = agenda.campos_do_texto("Responsáveis: Ana Fictícia, Bruno Fictício · Para conclusão 01/11/2026 "
                                   "Limite 03/11/2026")
        self.assertEqual(c, {"responsavel": "Ana Fictícia, Bruno Fictício", "conclusao": date(2026, 11, 1),
                             "limite": date(2026, 11, 3)})
        c = agenda.campos_do_texto("Responsável: Carla Fictícia<br>Data limite: 05/11/2026<br>Concluída em: 02/11/2026")
        self.assertEqual(c["responsavel"], "Carla Fictícia")
        self.assertEqual(c["limite"], date(2026, 11, 5))
        self.assertEqual(c["concluida_em"], date(2026, 11, 2))
        c = agenda.campos_do_texto("Tipo de tarefa: ANALISAR PROCESSO\nResponsável: Davi Fictício Concluiu a tarefa: X")
        self.assertEqual((c["tipo"], c["responsavel"]), ("ANALISAR PROCESSO", "Davi Fictício"))
        self.assertEqual(agenda.campos_do_texto("nada aqui"), {})

    def test_campos_das_props(self):
        c = agenda.campos_das_props({"responsavel_id": "123", "responsavel_nome": "Ana Fictícia",
                                     "data_limite": "2026-11-03", "data_prevista": "01/11/2026",
                                     "concluida": "N", "tipo_prazo": "conclusao", "tipo_tarefa": "RECURSO"})
        self.assertEqual(c["responsavel"], "Ana Fictícia")
        self.assertEqual(c["limite"], date(2026, 11, 3))
        self.assertEqual(c["conclusao"], date(2026, 11, 1))
        self.assertIs(c["concluida"], False)
        self.assertEqual(c["tipo"], "RECURSO")
        # "data_conclusao" = a "Data para conclusão" da tela; "concluida_em" = já concluída
        self.assertEqual(agenda.campos_das_props({"data_conclusao": "2026-11-02"}), {"conclusao": date(2026, 11, 2)})
        self.assertEqual(agenda.campos_das_props({"concluida_em": "2026-11-02"}), {"concluida_em": date(2026, 11, 2)})
        self.assertIs(agenda.campos_das_props({"situacao": "CANCELADA"})["concluida"], True)
        # mapa explícito (ORELHA_CALENDARIO_CAMPOS) vence a adivinhação
        c = agenda.campos_das_props({"x1": "Eva Fictícia", "x2": "2026-11-09"}, {"responsavel": "x1", "limite": "x2"})
        self.assertEqual((c["responsavel"], c["limite"]), ("Eva Fictícia", date(2026, 11, 9)))
        # descrição com tooltip dentro da propriedade
        self.assertEqual(agenda.campos_das_props({"descricao": "<b>Responsável:</b> Ana Fictícia"})["responsavel"],
                         "Ana Fictícia")


class TestLeituraHtml(unittest.TestCase):
    def test_grade_do_mes(self):
        brutos, mais = agenda.eventos_do_html(fixture("agenda", "calendario.html"), BASE)
        self.assertEqual(mais, 2)
        titulos = [b["titulo"] for b in brutos]
        self.assertEqual(len(brutos), 11)
        self.assertNotIn("AUDIÊNCIA REPETIDA DO POPOVER", titulos)
        aud = brutos[1]
        self.assertEqual((aud["dia"], aud["hora"], aud["titulo"]), (HOJE, "09:00", "AUDIÊNCIA UNA (TRABALHISTA) 2026"))
        self.assertEqual(aud["href"], "https://exemplo.vios.com.br/?pag=sys/processos/pxe.php&pxe_id=900001"
                                      "&pag_retorno=sys/agenda/calendario.php")
        self.assertEqual(aud["dica"], "Responsável: Ana Fictícia\nLimite: 04/11/2026")
        self.assertEqual(brutos[0]["titulo"], "Finados")
        self.assertEqual(brutos[0]["dia"], date(2026, 11, 2))
        self.assertEqual(brutos[3]["hora"], "")  # DAY OFF, dia todo

    def test_visao_lista(self):
        brutos, mais = agenda.eventos_do_html(fixture("prazos", "calendario.html"), BASE)
        self.assertEqual(mais, 0)
        self.assertEqual([(b["dia"], b["hora"]) for b in brutos],
                         [(date(2026, 11, 1), ""), (date(2026, 11, 1), ""), (date(2026, 11, 3), "09:30"), (HOJE, "")])
        self.assertEqual(brutos[0]["titulo"], "ANALISAR PROCESSO (CÍVEL) 2026")
        self.assertTrue(brutos[0]["href"].endswith("pxe_id=900201"))

    def test_html_vazio_ou_quebrado(self):
        self.assertEqual(agenda.eventos_do_html("", BASE), ([], 0))
        brutos, _ = agenda.eventos_do_html('<td data-date="2026-11-04"><a class="fc-event" href="?x=1">10:00 Reunião', BASE)
        self.assertEqual([(b["dia"], b["hora"], b["titulo"]) for b in brutos], [(HOJE, "10:00", "Reunião")])


class TestApi(unittest.TestCase):
    def test_eventos_da_api(self):
        dados = {"versao": "3", "eventos": [
            {"titulo": "CUMPRIR DILIGÊNCIA", "inicio": "2026-11-03T15:00", "dia_inteiro": False,
             "href": "?pag=sys/processos/pxe.php&pxe_id=1", "classes": "a b", "exibicao": "", "props": {"r": 1}},
            {"titulo": "14:00 Reunião", "inicio": "2026-11-04", "dia_inteiro": True, "href": "", "props": {}},
            "lixo"]}
        b = agenda.eventos_da_api(dados, BASE)
        self.assertEqual(len(b), 2)
        self.assertEqual((b[0]["dia"], b[0]["hora"], b[0]["classes"]), (date(2026, 11, 3), "15:00", "a b"))
        self.assertEqual(b[0]["href"], BASE + "?pag=sys/processos/pxe.php&pxe_id=1")
        self.assertEqual((b[1]["titulo"], b[1]["hora"]), ("Reunião", "14:00"))
        self.assertEqual(agenda.eventos_da_api(None), [])

    def test_lotes_preferem_api(self):
        api = {"versao": "4+", "eventos": [{"titulo": "X", "inicio": "2026-11-04", "dia_inteiro": True}]}
        html = fixture("agenda", "calendario.html")
        brutos, avisos = agenda.brutos_dos_lotes([{"api": api, "html": html}], BASE)
        self.assertEqual([b["titulo"] for b in brutos], ["X"])
        self.assertEqual(avisos, [])
        brutos, avisos = agenda.brutos_dos_lotes([{"api": {"versao": "", "eventos": []}, "html": html}], BASE)
        self.assertEqual(len(brutos), 11)
        self.assertTrue(any("+ mais" in a for a in avisos))


class TestMontar(unittest.TestCase):
    def eventos(self):
        brutos, _ = agenda.eventos_do_html(fixture("agenda", "calendario.html"), BASE)
        return agenda.montar_eventos(brutos)

    def test_categorias(self):
        cat = {e.titulo: e.categoria for e in self.eventos()}
        self.assertEqual(cat["Finados"], "feriado")
        self.assertEqual(cat["Dia do Padroeiro (municipal fictício)"], "feriado")
        self.assertEqual(cat["AUDIÊNCIA UNA (TRABALHISTA) 2026"], "tarefa")
        self.assertEqual(cat["Reunião com a Construtora Exemplo"], "compromisso")
        self.assertEqual(cat["Aniversário - Davi Fictício"], "aniversario")
        aud = next(e for e in self.eventos() if e.pxe_id == "900001")
        self.assertEqual((aud.responsavel, aud.limite), ("Ana Fictícia", HOJE))

    def test_sem_repetir_e_concluida(self):
        b = {"titulo": "TAREFA", "dia": HOJE, "hora": "", "href": BASE + "?pag=sys/processos/pxe.php&pxe_id=7",
             "classes": "fc-event tarefa-concluida", "dica": "", "props": {}}
        eventos = agenda.montar_eventos([b, dict(b), dict(b, classes="fc-event nao-concluida", dia=date(2026, 11, 5))])
        self.assertEqual(len(eventos), 2)
        self.assertTrue(eventos[0].concluida)
        self.assertFalse(eventos[1].concluida)
        self.assertEqual(agenda.montar_eventos([dict(b, titulo="  ")]), [])

    def test_feriado_pelo_nome(self):
        b = {"titulo": "Proclamação da República", "dia": date(2026, 11, 15), "hora": "", "href": "", "classes": ""}
        self.assertEqual(agenda.montar_eventos([b])[0].categoria, "feriado")
        self.assertEqual(agenda.montar_eventos([dict(b, titulo="NATALIA FICTÍCIA - ligar")])[0].categoria, "compromisso")

    def test_agenda(self):
        itens, numeros, resumo = agenda.montar_agenda(self.eventos(), HOJE)
        self.assertEqual([(i.grupo, i.titulo, i.nivel) for i in itens], [
            ("Hoje · quarta-feira, 04/11", "DAY OFF - Bruno Fictício", "info"),
            ("Hoje · quarta-feira, 04/11", "AUDIÊNCIA UNA (TRABALHISTA) 2026", "atencao"),
            ("Hoje · quarta-feira, 04/11", "Reunião com a Construtora Exemplo", "info"),
            ("Amanhã · quinta-feira, 05/11", "PERÍCIA MÉDICA (PREVIDENCIÁRIO) 2026", "info"),
            ("Amanhã · quinta-feira, 05/11", "SUSTENTAÇÃO ORAL (CÍVEL) 2026", "info"),
            ("Sexta-feira, 06/11", "Dia do Padroeiro (municipal fictício)", "info"),
        ])
        self.assertEqual(itens[1].detalhe, "09:00 · responsável: Ana Fictícia")
        self.assertTrue(itens[1].link.startswith("https://"))
        self.assertEqual(itens[0].detalhe, "dia todo")
        self.assertEqual(itens[0].link, "")
        self.assertEqual(numeros, {"hoje": 3, "amanha": 2, "feriados": 1, "audiencias_hoje": 1, "pericias_hoje": 0,
                                   "audiencias_amanha": 0, "pericias_amanha": 1})
        self.assertEqual(resumo, "Hoje: 1 audiência, 1 reunião e 1 compromisso. Amanhã: 1 perícia e 1 sustentação. "
                                 "Feriado até domingo: Dia do Padroeiro (municipal fictício) (sexta-feira, 06/11).")

    def test_opcoes(self):
        _, numeros, _ = agenda.montar_agenda(self.eventos(), HOJE, aniversarios=True)
        self.assertEqual(numeros["amanha"], 3)
        ev = [agenda.Evento("ANALISAR PROCESSO", dia=HOJE, hora="10:00", categoria="tarefa")]
        self.assertEqual(agenda.montar_agenda(ev, HOJE)[0], [])
        self.assertEqual(len(agenda.montar_agenda(ev, HOJE, tarefas_com_hora=True)[0]), 1)
        itens, _, resumo = agenda.montar_agenda([], HOJE)
        self.assertEqual((itens, resumo), ([], "Hoje: nada marcado. Amanhã: nada marcado."))

    def test_domingo_ve_feriado_de_amanha(self):
        domingo = date(2026, 11, 8)
        ev = [agenda.Evento("Feriado fictício", dia=date(2026, 11, 9), categoria="feriado"),
              agenda.Evento("Feriado depois", dia=date(2026, 11, 10), categoria="feriado")]
        itens, numeros, _ = agenda.montar_agenda(ev, domingo)
        self.assertEqual([i.titulo for i in itens], ["Feriado fictício"])
        self.assertEqual(itens[0].grupo, "Amanhã · segunda-feira, 09/11")

    def test_concluida_nao_e_atencao(self):
        ev = [agenda.Evento("AUDIÊNCIA X", dia=HOJE, hora="09:00", categoria="tarefa", concluida=True)]
        itens, _, _ = agenda.montar_agenda(ev, HOJE)
        self.assertEqual((itens[0].nivel, itens[0].detalhe), ("info", "09:00 · concluída"))


class TestConfig(unittest.TestCase):
    def test_padroes(self):
        c = agenda.Calendario.do_cfg(cfg())
        self.assertEqual(c.url, agenda.URL_CALENDARIO)
        self.assertEqual(c.evento, ("css selector", ".fc-event"))
        self.assertIsNone(c.filtro_campo)
        self.assertIsNone(c.visao)
        self.assertEqual(c.campos, {})
        self.assertEqual(agenda.filtros_do_cfg(cfg(), "AGENDA"), ({}, []))

    def test_valores(self):
        c = cfg("ORELHA_CALENDARIO_CAMPOS=responsavel=resp; limite=dt_lim\nORELHA_CALENDARIO_VISAO=css:.fc-timeGridWeek-button\n"
                "ORELHA_PRAZOS_FILTROS=pesq[concluida]=N; pesq[responsavel]=\nORELHA_PRAZOS_MARCAR_TODAS=pesq[resp][]\n")
        cal = agenda.Calendario.do_cfg(c)
        self.assertEqual(cal.campos, {"responsavel": "resp", "limite": "dt_lim"})
        self.assertEqual(cal.visao, ("css selector", ".fc-timeGridWeek-button"))
        self.assertEqual(agenda.filtros_do_cfg(c, "PRAZOS"),
                         ({"pesq[concluida]": "N", "pesq[responsavel]": ""}, ["pesq[resp][]"]))

    def test_invalidos(self):
        with self.assertRaises(config.ConfigErro) as e:
            agenda.Calendario.do_cfg(cfg("ORELHA_CALENDARIO_CAMPOS=pessoa=x\n"))
        self.assertIn("ORELHA_CALENDARIO_CAMPOS", str(e.exception))
        with self.assertRaises(config.ConfigErro):
            agenda.filtros_do_cfg(cfg("ORELHA_AGENDA_FILTROS=sem igual\n"), "AGENDA")


class TestExecutar(unittest.TestCase):
    def test_simulado(self):
        ctx, eventos = contexto()
        s = agenda.executar(ctx)
        self.assertIsInstance(s, Secao)
        self.assertEqual((s.chave, s.erro), ("agenda", ""))
        self.assertEqual(len(s.itens), 6)
        self.assertEqual(s.por_nivel()["atencao"], 1)
        self.assertEqual(eventos, [("fase", {"fase": "lendo_calendario"})])
        self.assertTrue(any("+ mais" in a for a in s.avisos))

    def test_real_vira_o_mes(self):
        ctx, _ = contexto(hoje=date(2026, 11, 30), simulado_=False, driver=object(),
                          linhas="ORELHA_AGENDA_FILTROS=pesq[x]=1\n")
        with mock.patch.object(agenda, "ler_calendario", return_value=([{"api": None, "html": ""}], ["aviso x"])) as ler:
            s = agenda.executar(ctx)
        args, kw = ler.call_args
        self.assertEqual(args[2], {"pesq[x]": "1"})
        self.assertEqual(kw["meses_depois"], 1)
        self.assertIn("aviso x", s.avisos)
        self.assertTrue(any("nenhum evento" in a for a in s.avisos))
        ctx, _ = contexto(simulado_=False, driver=object())
        with mock.patch.object(agenda, "ler_calendario", return_value=([], [])) as ler:
            agenda.executar(ctx)
        self.assertEqual(ler.call_args[1]["meses_depois"], 0)


class TestLerCalendario(unittest.TestCase):
    """A leitura com Selenium, com o navegador e o VIOS de mentira: confere a ordem das chamadas."""

    def test_libera_pesquisa_filtra_e_navega(self):
        chamadas = []

        @contextmanager
        def liberada(driver):
            chamadas.append("libera")
            yield
            chamadas.append("bloqueia")

        driver = mock.Mock()
        driver.execute_script.return_value = {"versao": "", "eventos": []}
        driver.find_elements.return_value = []
        ctx, _ = contexto(simulado_=False, driver=driver,
                          linhas="ORELHA_CALENDARIO_FILTRO_CAMPO=css:select[name='pesq[concluida]']\n")
        conf = agenda.Calendario.do_cfg(ctx.cfg)
        with mock.patch("nucleo.navegador.pesquisa_liberada", liberada), \
                mock.patch("nucleo.navegador.tentativas_barradas", return_value=["XHR POST x"]), \
                mock.patch.object(agenda.vios, "abrir", side_effect=lambda c, u, **k: chamadas.append(("abrir", u))), \
                mock.patch.object(agenda.vios, "esperar_varios", return_value=[1]), \
                mock.patch.object(agenda.vios, "esperar_ajax"), \
                mock.patch.object(agenda.vios, "esperar_ate"), \
                mock.patch.object(agenda.vios, "html", return_value="<div></div>"), \
                mock.patch.object(agenda.vios, "enviar_pesquisa",
                                  side_effect=lambda *a, **k: chamadas.append(("pesquisa", a[2])) or
                                  {"faltando": ["pesq[y]"], "marcados": {}}), \
                mock.patch.object(agenda.vios, "clicar", side_effect=lambda c, b: chamadas.append(("clicar", b[1]))), \
                mock.patch.object(agenda.time, "sleep"):
            lotes, avisos = agenda.ler_calendario(ctx, conf, {"pesq[concluida]": "N", "pesq[y]": "1"}, (),
                                                  meses_antes=2, prefixo="PRAZOS")
        self.assertEqual(chamadas, ["libera", ("abrir", agenda.URL_CALENDARIO),
                                    ("pesquisa", {"pesq[concluida]": "N", "pesq[y]": "1"}),
                                    ("clicar", ".fc-prev-button"), ("clicar", ".fc-prev-button"), "bloqueia"])
        self.assertEqual(len(lotes), 3)
        self.assertTrue(any("pesq[y]" in a for a in avisos))
        self.assertTrue(any("bloqueio de envios barrou 1" in a for a in avisos))

    def test_filtro_sem_campo_nao_envia(self):
        driver = mock.Mock()
        driver.execute_script.return_value = None
        driver.find_elements.return_value = []
        ctx, _ = contexto(simulado_=False, driver=driver)
        conf = agenda.Calendario.do_cfg(ctx.cfg)

        @contextmanager
        def liberada(driver):
            yield

        with mock.patch("nucleo.navegador.pesquisa_liberada", liberada), \
                mock.patch("nucleo.navegador.tentativas_barradas", return_value=[]), \
                mock.patch.object(agenda.vios, "abrir"), \
                mock.patch.object(agenda.vios, "esperar_varios", return_value=[]), \
                mock.patch.object(agenda.vios, "html", return_value=""), \
                mock.patch.object(agenda.vios, "enviar_pesquisa") as pesquisa:
            lotes, avisos = agenda.ler_calendario(ctx, conf, {"a": "1"}, (), prefixo="AGENDA")
        pesquisa.assert_not_called()
        self.assertEqual(len(lotes), 1)
        self.assertTrue(any("ORELHA_CALENDARIO_FILTRO_CAMPO" in a for a in avisos))


if __name__ == "__main__":
    unittest.main()


class TestAgendaDaEquipe(unittest.TestCase):
    """Padrão: as tarefas da agenda vêm da lista de tarefas (equipe toda); do calendário ficam
    compromissos e feriados."""

    def test_termo_no_comeco_do_tipo(self):
        ev = lambda tipo: agenda.Evento(tipo, categoria="tarefa", tipo=tipo, props={"fonte": "lista"})
        self.assertEqual(agenda.termo_de(ev("AUDIÊNCIA UNA (CÍVEL) 2026"), agenda.TERMOS), "AUDIÊNCIA")
        self.assertEqual(agenda.termo_de(ev("INFORMAR AUDIÊNCIA (CÍVEL) 2026"), agenda.TERMOS), "")
        self.assertEqual(agenda.termo_de(ev("LEMBRAR AUDIÊNCIA (CÍVEL) 2026"), agenda.TERMOS), "")
        self.assertEqual(agenda.termo_de(ev("CIÊNCIA (CÍVEL) 2026"), agenda.TERMOS), "")
        self.assertEqual(agenda.termo_de(ev("C: AUDIÊNCIA DECON 2026"), agenda.TERMOS), "AUDIÊNCIA")
        # compromisso do calendário continua pelo termo em qualquer lugar
        self.assertEqual(agenda.termo_de(agenda.Evento("Reunião de Fechamento"), agenda.TERMOS), "REUNIÃO")

    def test_simulado_equipe(self):
        ctx, _ = contexto(fonte="")
        s = agenda.executar(ctx)
        self.assertEqual(s.erro, "")
        tarefas = [(i.grupo.split(" · ")[0], i.titulo, i.detalhe.split(" · ")[0], i.nivel) for i in s.itens
                   if "pxe_id=9003" in i.link]
        self.assertEqual(tarefas, [
            ("Hoje", "AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026", "09:00", "atencao"),
            ("Amanhã", "REUNIÃO COM O CLIENTE 2026", "dia todo", "info"),   # "dia todo" vem antes das com hora
            ("Amanhã", "PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026", "08:00", "info"),
            ("Amanhã", "SUSTENTAÇÃO ORAL (CÍVEL) 2026", "14:00", "info"),
        ])
        sust = next(i for i in s.itens if "900306" in i.link)
        self.assertEqual(sust.titulo, "SUSTENTAÇÃO ORAL (CÍVEL) 2026")  # a etiqueta não gruda no tipo
        self.assertIn("etiqueta no VIOS: Urgente", sust.detalhe)
        pericia = next(i for i in s.itens if "900304" in i.link)
        self.assertIn("responsável: CARLA FICTÍCIA, DANIEL FICTÍCIO", pericia.detalhe)
        # do calendário (fixture do usuário logado): só compromissos e feriados; as tarefas dele saem
        self.assertFalse(any("pxe_id=9001" in i.link or "pxe-lista" in i.link for i in s.itens))

    def test_real_le_hoje_e_amanha_da_lista(self):
        ctx, _ = contexto(simulado_=False, driver=object(), fonte="")
        from funcoes import prazos
        html = simulado.ler(ctx, "lista.html")
        with mock.patch.object(agenda, "ler_calendario", return_value=([], [])), \
                mock.patch.object(prazos, "ler_lista", return_value=html) as ler:
            s = agenda.executar(ctx)
        self.assertEqual(ler.call_args.args[1:], ("data_prevista", HOJE, date(2026, 11, 5)))
        self.assertEqual(sum(1 for i in s.itens if "pxe_id=9003" in i.link), 4)
