"""Testes da função intimacoes (intimações esquecidas). Dados 100% fictícios."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from funcoes import intimacoes as m
from nucleo import config, simulado, vios
from nucleo.modelos import Contexto, Secao

PASTA = Path(__file__).resolve().parent.parent
FIXTURES = PASTA / "fixtures"
QUARTA = date(2026, 11, 4)     # quarta-feira
SEGUNDA = date(2026, 11, 2)
DOMINGO = date(2026, 11, 1)


def cfg(**variaveis):
    return config.carregar(Path(tempfile.mkdtemp()) / ".env", exigir_login=False, ambiente=variaveis)


def contexto(hoje=QUARTA, simulado_=True, driver=None, **variaveis):
    eventos = []
    ctx = Contexto(driver=driver, cfg=cfg(**variaveis), hoje=hoje, simulado=simulado_, fixtures=FIXTURES,
                   chave="intimacoes", emitir=lambda tipo, **dados: eventos.append((tipo, dados)))
    return ctx, eventos


def fixture(hoje=QUARTA):
    return simulado.substituir((FIXTURES / "intimacoes" / m.FIXTURE).read_text(encoding="utf-8"), hoje)


def linha_html(ci="900100", datas="Disponibilização: 28/10/2026", numeros="0000101-11.2026.8.06.0001", extra=""):
    return (f'<table><tr id="t_linha_0"><td data-id="t_linha_0_imp_pub_id">{ci}</td>'
            f'<td data-id="t_linha_0_sdata">{datas}</td>'
            f'<td data-id="t_linha_0_intimacao_numeros">{numeros}</td>{extra}</tr></table>')


class TestPeriodo(unittest.TestCase):
    def test_periodo_ultron_copiado(self):
        self.assertEqual(m.periodo_ultron(QUARTA), (date(2026, 11, 3), date(2026, 11, 3)))
        self.assertEqual(m.periodo_ultron(SEGUNDA), (date(2026, 10, 30), date(2026, 11, 1)))
        self.assertEqual(m.periodo_ultron(DOMINGO), (date(2026, 10, 31), date(2026, 10, 31)))

    def test_exclui_ontem_e_hoje(self):
        inicio, fim = m.periodo(QUARTA)
        self.assertEqual(inicio, date(2026, 10, 20))   # 15 dias antes
        self.assertEqual(fim, date(2026, 11, 2))       # anteontem
        self.assertEqual(m.periodo(QUARTA, 7)[0], date(2026, 10, 28))

    def test_segunda_deixa_o_fim_de_semana_para_o_ultron(self):
        self.assertEqual(m.periodo(SEGUNDA)[1], date(2026, 10, 29))  # quinta
        self.assertEqual(m.periodo(SEGUNDA, seguir_ultron=False)[1], date(2026, 10, 31))
        self.assertEqual(m.periodo(DOMINGO)[1], date(2026, 10, 30))  # o Ultron trata o sábado

    def test_periodo_nunca_alcanca_ontem(self):
        for dia in range(1, 31):
            hoje = date(2026, 11, dia)
            self.assertLessEqual(m.periodo(hoje)[1], date.fromordinal(hoje.toordinal() - 2))


class TestInterpretar(unittest.TestCase):
    def setUp(self):
        self.cfg = cfg()
        self.inicio, self.fim = m.periodo(QUARTA)
        self.leitura = m.interpretar(fixture(), self.inicio, self.fim, base=self.cfg,
                                     proibidas=self.cfg.urls_proibidas)

    def test_contagens(self):
        le = self.leitura
        self.assertEqual(le.linhas, 10)
        self.assertEqual(le.fora_do_periodo, 3)      # ontem, hoje e antes do período
        self.assertEqual(le.repetidas, 1)
        self.assertEqual(le.apagadas, 1)
        self.assertEqual(le.erros, 0)
        self.assertEqual(le.total_rodape, 10)
        self.assertEqual([i.ci for i in le.intimacoes], ["900009", "900005", "900004", "900007", "900003"])

    def test_ontem_e_hoje_ficam_de_fora(self):
        cis = {i.ci for i in self.leitura.intimacoes}
        self.assertNotIn("900001", cis)
        self.assertNotIn("900002", cis)
        self.assertNotIn("900006", cis)   # antes do período
        self.assertNotIn("900008", cis)   # apagada

    def test_campos(self):
        i = self.leitura.intimacoes[0]
        self.assertEqual(i.disponibilizacao, date(2026, 10, 23))
        self.assertEqual(i.processo, "0000303-33.2026.4.05.8100")
        self.assertEqual(i.tribunal, "TRF5")
        self.assertEqual(i.cidade, "Fortaleza/CE")
        sem_cnj = self.leitura.intimacoes[1]
        self.assertEqual(sem_cnj.processo, "Processo administrativo 12/2026")
        self.assertEqual(sem_cnj.tribunal, "TRF5")     # pela sigla no fornecedor
        self.assertEqual(sem_cnj.link, "")

    def test_link_nunca_e_o_de_lancar(self):
        for i in self.leitura.intimacoes:
            self.assertNotIn("int-lanca", i.link)
            self.assertNotIn("act=del", i.link)
        self.assertTrue(self.leitura.intimacoes[0].link.startswith(self.cfg.vios_base))
        self.assertIn("processos-vis.php", self.leitura.intimacoes[0].link)

    def test_linha_so_com_link_de_lancar_fica_sem_link(self):
        html = linha_html(extra='<td><a href="index.php?pag=sys/publicacoes/int-lanca.php&amp;id=1">'
                                'Lançar</a></td>')
        le = m.interpretar(html, date(2026, 10, 1), date(2026, 11, 2), proibidas=self.cfg.urls_proibidas)
        self.assertEqual(le.intimacoes[0].link, "")

    def test_sem_tabela_e_sem_ci(self):
        vazia = m.interpretar("<html><p>Nenhum registro</p></html>", self.inicio, self.fim)
        self.assertEqual((vazia.linhas, vazia.intimacoes, vazia.total_rodape), (0, [], None))
        sem_ci = m.interpretar(linha_html(ci=""), self.inicio, self.fim)
        self.assertEqual((sem_ci.linhas, sem_ci.erros), (1, 1))

    def test_datas(self):
        so_data = m.interpretar(linha_html(datas="28/10/2026"), self.inicio, self.fim)
        self.assertEqual(so_data.intimacoes[0].disponibilizacao, date(2026, 10, 28))
        so_publicacao = m.interpretar(linha_html(datas="Publicação: 28/10/2026"), self.inicio, self.fim)
        self.assertEqual((so_publicacao.sem_data, so_publicacao.intimacoes), (1, []))
        sem_acento = m.interpretar(linha_html(datas="DISPONIBILIZACAO 27/10/2026 PUBLICACAO 28/10/2026"),
                                   self.inicio, self.fim)
        self.assertEqual(sem_acento.intimacoes[0].disponibilizacao, date(2026, 10, 27))
        self.assertEqual(sem_acento.intimacoes[0].publicacao, date(2026, 10, 28))

    def test_tribunal_do_cnj(self):
        casos = {"0000001-23.2026.8.06.0001": "TJCE", "0000001-23.2026.8.26.0100": "TJSP",
                 "0000001-23.2026.5.07.0003": "TRT7", "0000001-23.2026.4.05.8100": "TRF5",
                 "0000001-23.2026.6.06.0001": "TRECE", "0000001-23.2026.5.00.0000": "TST",
                 "0000001-23.2026.3.00.0000": "STJ", "0000001-23.2026.8.99.0001": "", "sem número": ""}
        for numero, sigla in casos.items():
            self.assertEqual(m.tribunal_do_cnj(numero), sigla, numero)
        coluna = linha_html(extra='<td data-id="t_linha_0_tribunal">Tribunal Fictício</td>')
        self.assertEqual(m.interpretar(coluna, self.inicio, self.fim).intimacoes[0].tribunal, "Tribunal Fictício")

    def test_total_rodape(self):
        self.assertEqual(m.total_rodape('<span class="geratabela_total_quantidade_original"> 37 </span>'), 37)
        self.assertEqual(m.total_rodape('<div class="geratabela_total_quantidade_original"><b>8</b></div>'), 8)
        self.assertIsNone(m.total_rodape("<p>nada</p>"))


class TestSecao(unittest.TestCase):
    def setUp(self):
        self.inicio, self.fim = m.periodo(QUARTA)
        self.leitura = m.interpretar(fixture(), self.inicio, self.fim, base=cfg())

    def test_niveis_e_grupos(self):
        s = m.montar_secao(self.leitura, QUARTA, self.inicio, self.fim)
        self.assertEqual([i.nivel for i in s.itens], ["grave", "grave", "grave", "atencao", "atencao"])
        self.assertEqual(s.itens[3].detalhe.count("há 5 dias"), 1)   # exatamente 5 dias = atenção
        self.assertEqual(s.itens[0].grupo, "Disponibilizadas em 23/10/2026 (sexta)")
        self.assertEqual(s.itens[0].titulo, "CI 900009 · processo 0000303-33.2026.4.05.8100")
        self.assertEqual(s.itens[1].titulo, "CI 900005 · Processo administrativo 12/2026")
        self.assertIn("TRF5", s.itens[0].detalhe)
        self.assertEqual(s.resumo, "5 intimações sem tarefa de 20/10 a 02/11 (3 com mais de 5 dias).")
        self.assertEqual(s.numeros["esquecidas"], 5)
        self.assertEqual(s.numeros["graves"], 3)
        self.assertEqual(s.numeros["mais_antiga_dias"], 12)
        self.assertEqual(s.numeros["dias_pesquisados"], 14)
        self.assertEqual(s.numeros_seguros(), s.numeros)   # tudo pode ir para a vila
        self.assertEqual(s.avisos, [])

    def test_limiar_configuravel(self):
        s = m.montar_secao(self.leitura, QUARTA, self.inicio, self.fim, grave_dias=10)
        self.assertEqual(s.por_nivel()["grave"], 1)
        s = m.montar_secao(self.leitura, QUARTA, self.inicio, self.fim, grave_dias=20)
        self.assertTrue(s.resumo.endswith(", todas com até 20 dias."))

    def test_vazia_e_avisos(self):
        le = m.Leitura(linhas=500, total_rodape=620, erros=2, sem_data=1)
        s = m.montar_secao(le, QUARTA, self.inicio, self.fim, avisos=["da leitura"])
        self.assertEqual(s.resumo, "Nenhuma intimação esquecida de 20/10 a 02/11: todas já têm tarefa.")
        self.assertEqual(s.itens, [])
        self.assertEqual(s.avisos[0], "da leitura")
        self.assertTrue(any("500 de 620" in a for a in s.avisos))
        self.assertTrue(any("2 linha(s)" in a for a in s.avisos))
        self.assertEqual(s.numeros["erros_leitura"], 3)

    def test_uma_intimacao(self):
        le = m.interpretar(linha_html(datas="Disponibilização: 30/10/2026"), self.inicio, self.fim)
        s = m.montar_secao(le, QUARTA, self.inicio, self.fim)
        self.assertEqual(s.resumo, "1 intimação sem tarefa de 20/10 a 02/11, todas com até 5 dias.")
        self.assertIn("há 5 dias", s.itens[0].detalhe)


class TestOpcoes(unittest.TestCase):
    def test_padroes(self):
        o = m.opcoes(cfg())
        self.assertEqual((o.dias, o.grave_dias, o.limite, o.seguir_ultron), (15, 5, 500, True))
        self.assertEqual(o.url, "index.php?pag=sys/publicacoes/int-pesquisa.php")
        self.assertEqual(o.campo_data[1], "input[name='pesq[fdata]']")
        self.assertEqual(o.marcar_todas, ["pesq[pr_areas_id][]"])
        self.assertEqual(o.extras, {})

    def test_url_padrao_nao_e_proibida_e_lancamento_e(self):
        c = cfg()
        self.assertEqual(vios.url_proibida(vios.url_absoluta(c, m.URL_PESQUISA), c.urls_proibidas), "")
        self.assertTrue(vios.url_proibida("index.php?pag=sys/publicacoes/int-lanca.php", c.urls_proibidas))

    def test_env(self):
        o = m.opcoes(cfg(ORELHA_INTIMACOES_DIAS="7", ORELHA_INTIMACOES_GRAVE_DIAS="3",
                         ORELHA_INTIMACOES_MARCAR_TODAS="pesq[pr_areas_id][]|pesq[advogados_id][]",
                         ORELHA_INTIMACOES_FILTROS_EXTRA="pesq[tarefa]=N | pesq[x]=1",
                         ORELHA_INTIMACOES_SEGUIR_ULTRON="false"))
        self.assertEqual((o.dias, o.grave_dias, o.seguir_ultron), (7, 3, False))
        self.assertEqual(o.marcar_todas, ["pesq[pr_areas_id][]", "pesq[advogados_id][]"])
        self.assertEqual(o.extras, {"pesq[tarefa]": "N", "pesq[x]": "1"})

    def test_invalidos(self):
        with self.assertRaises(config.ConfigErro):
            m.opcoes(cfg(ORELHA_INTIMACOES_DIAS="quinze"))
        with self.assertRaises(config.ConfigErro):
            m.opcoes(cfg(ORELHA_INTIMACOES_FILTROS_EXTRA="sem igual"))
        with self.assertRaises(ValueError):
            m.opcoes(cfg(ORELHA_INTIMACOES_DIAS="0"))


class TestExecutarSimulado(unittest.TestCase):
    def test_simulado(self):
        ctx, eventos = contexto()
        s = m.executar(ctx)
        self.assertIsInstance(s, Secao)
        self.assertEqual((s.chave, s.erro), ("intimacoes", ""))
        self.assertEqual(len(s.itens), 5)
        self.assertEqual(eventos, [("fase", {"fase": "lendo_intimacoes"})])

    def test_simulado_em_qualquer_dia(self):
        ctx, _ = contexto(hoje=date(2027, 3, 10))   # quarta: as datas da fixture são relativas
        self.assertEqual(len(m.executar(ctx).itens), 5)
        ctx, _ = contexto(hoje=date(2027, 3, 8))    # segunda: a de HOJE-3 (sexta) é do Ultron
        self.assertEqual(len(m.executar(ctx).itens), 4)

    def test_dias_configuravel(self):
        ctx, _ = contexto(ORELHA_INTIMACOES_DIAS="7")
        s = m.executar(ctx)
        self.assertEqual(len(s.itens), 3)
        self.assertEqual(s.numeros["dias_pesquisados"], 6)

    def test_periodo_vazio(self):
        ctx, _ = contexto(hoje=SEGUNDA, ORELHA_INTIMACOES_DIAS="3")
        s = m.executar(ctx)
        self.assertEqual((s.itens, s.erro), ([], ""))
        self.assertIn("Período vazio", s.resumo)
        self.assertTrue(s.avisos)


class TestLeituraVios(unittest.TestCase):
    """A leitura com o VIOS, com as telas trocadas por mocks (nada roda contra o VIOS real)."""

    def setUp(self):
        self.ctx, self.eventos = contexto(simulado_=False, driver=mock.Mock(name="driver"),
                                          ORELHA_INTIMACOES_LEITURA="formulario")  # leitura antiga
        self.o = m.opcoes(self.ctx.cfg)
        self.html = fixture()

    def rodar(self, faltando=(), linhas=("tr",), barrados=()):
        with mock.patch.object(m.vios, "abrir") as abrir, \
                mock.patch.object(m.vios, "enviar_pesquisa",
                                  return_value={"faltando": list(faltando), "marcados": {"pesq[pr_areas_id][]": 16}}) as enviar, \
                mock.patch.object(m.vios, "esperar_varios", return_value=list(linhas)), \
                mock.patch.object(m.vios, "html", return_value=self.html), \
                mock.patch.object(m.vios, "clicar") as clicar, \
                mock.patch("nucleo.navegador.tentativas_barradas", return_value=list(barrados)):
            secao = m.executar(self.ctx)
        self.abrir, self.enviar, self.clicar = abrir, enviar, clicar
        return secao

    def test_pesquisa_so_le(self):
        s = self.rodar()
        self.assertEqual(len(s.itens), 5)
        self.abrir.assert_called_once_with(self.ctx, "index.php?pag=sys/publicacoes/int-pesquisa.php")
        self.clicar.assert_not_called()
        args, kwargs = self.enviar.call_args
        self.assertEqual(args[1], self.o.campo_data)
        self.assertEqual(args[2], {"pesq[idata]": "20/10/2026", "pesq[fdata]": "02/11/2026", "pesq[limit]": "500"})
        self.assertEqual(kwargs["marcar_todas"], ["pesq[pr_areas_id][]"])
        for chamada in self.abrir.call_args_list:
            self.assertNotIn("int-lanca", chamada.args[1])
        self.assertEqual(self.eventos, [("fase", {"fase": "lendo_intimacoes"})])

    def test_filtros_extra(self):
        self.ctx.cfg._env["ORELHA_INTIMACOES_FILTROS_EXTRA"] = "pesq[com_tarefa]=N"
        self.rodar()
        self.assertEqual(self.enviar.call_args[0][2]["pesq[com_tarefa]"], "N")

    def test_sem_campo_de_data_e_erro(self):
        with self.assertRaises(vios.ViosErro):
            self.rodar(faltando=["pesq[idata]"])

    def test_filtro_que_falta_vira_aviso(self):
        s = self.rodar(faltando=["pesq[pr_areas_id][]"])
        self.assertTrue(any("pesq[pr_areas_id][]" in a for a in s.avisos))

    def test_lista_vazia_com_bloqueio_barrando(self):
        self.html = "<html><p>Nenhum registro encontrado</p></html>"
        s = self.rodar(linhas=(), barrados=["XHR POST sys/x"])
        self.assertEqual(s.itens, [])
        self.assertTrue(any("barrou 1" in a for a in s.avisos))
        self.assertFalse(any("sys/x" in a for a in s.avisos))

    def test_bloqueio_inativo_sobe(self):
        with mock.patch.object(m.vios, "abrir", side_effect=vios.BloqueioInativo("inativo")):
            with self.assertRaises(vios.BloqueioInativo):
                m.executar(self.ctx)


if __name__ == "__main__":
    unittest.main()


class TestLeituraPorEndereco(unittest.TestCase):
    """Padrão: a pesquisa abre pelo endereço (formulário GET), sem filtro de Área."""

    def test_url(self):
        o = m.opcoes(cfg())
        url = m.url_pesquisa(o, date(2026, 10, 20), date(2026, 11, 2))
        self.assertTrue(url.startswith("?pag=sys/publicacoes/int-pesquisa.php&"))
        for trecho in ("pesq[processado]=0", "pesq[flag_oculto]=0", "pesq[tp_data]=data", "pesq[idata]=20/10/2026",
                       "pesq[fdata]=02/11/2026", "pesq[limit]=500", "Pesq=Pesquisar"):
            self.assertIn(trecho, url)
        self.assertNotIn("pr_areas_id", url)   # marcar todas as áreas deixava de fora as sem área
        self.assertNotIn("int-lanca", url)

    def test_executar_abre_o_endereco_e_nao_envia_formulario(self):
        ctx, _ = contexto(simulado_=False, driver=mock.Mock(name="driver"))
        ctx.driver.find_elements.return_value = ["tr"] * 5
        with mock.patch.object(m.vios, "abrir") as abrir, mock.patch.object(m.vios, "html", return_value=fixture()), \
                mock.patch.object(m.vios, "enviar_pesquisa") as enviar, mock.patch.object(m.vios, "clicar") as clicar:
            s = m.executar(ctx)
        enviar.assert_not_called()
        clicar.assert_not_called()
        self.assertIn("pesq[processado]=0", abrir.call_args.args[1])
        self.assertEqual(len(s.itens), 5)

    def test_lista_cheia_avisa(self):
        ctx, _ = contexto(simulado_=False, driver=mock.Mock(name="driver"), ORELHA_INTIMACOES_LIMITE="3")
        ctx.driver.find_elements.return_value = ["tr"] * 3
        with mock.patch.object(m.vios, "abrir"), mock.patch.object(m.vios, "html", return_value=fixture()):
            s = m.executar(ctx)
        self.assertTrue(any("máximo pedido" in a for a in s.avisos))
