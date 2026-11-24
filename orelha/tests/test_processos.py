"""Testes da função "processos" (todos os processos de uma área). Só dados fictícios."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from funcoes import processos as p
from nucleo import config, simulado, vios
from nucleo.modelos import Contexto

PASTA = Path(__file__).resolve().parent.parent
FIXTURES = PASTA / "fixtures"
HOJE = date(2026, 11, 17)
BASE = "https://exemplo.vios.com.br/"


def fixture(nome):
    return simulado.substituir((FIXTURES / "processos" / nome).read_text(encoding="utf-8"), HOJE)


def lista_html(cis):
    linhas = "".join(f'<tr><td data-id="processos-lista_linha_{i}_processos_id">{ci}</td>'
                     f'<td data-id="processos-lista_linha_{i}_clientes_nome">C{ci}</td></tr>' for i, ci in enumerate(cis))
    return f'<table id="processos-lista"><thead><tr><th>CI</th></tr></thead><tbody>{linhas}</tbody></table>'


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.env = self.pasta / ".env"
        self.escrever_env()

    def escrever_env(self, **variaveis):
        texto = "SISTEMA_URL=https://exemplo.vios.com.br/entrar.php?\n"
        texto += "".join(f"{k}={v}\n" for k, v in variaveis.items())
        self.env.write_text(texto, encoding="utf-8")
        self.cfg = config.carregar(self.env, exigir_login=False, ambiente={})

    def ctx(self, simulado_=False):
        return Contexto(driver=None, cfg=self.cfg, hoje=HOJE, simulado=simulado_, fixtures=FIXTURES,
                        saida=self.pasta / "saida", historico=self.pasta / "historico", chave="processos")


class TestLeitura(unittest.TestCase):
    def test_lista_ficticia(self):
        procs = p.processos_do_html(fixture("ativos.html"), "ativo", BASE)
        self.assertEqual([x["ci"] for x in procs], ["910001", "910002", "910003"])  # a linha de total fica de fora
        x = procs[0]
        self.assertEqual(x["numero"], "0000001-11.2026.4.05.8103")
        self.assertEqual(x["cliente"], "MARIA FICTÍCIA")  # sem o "(12)" do fim
        self.assertEqual(x["parte_passiva"], "INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS")
        self.assertEqual(x["situacao"], "ativo")
        self.assertEqual(x["link"], BASE + "?pag=sys/processos/processos-vis.php&processos_id=910001")
        self.assertEqual(procs[1]["data_acao"], "")  # 00/00/0000 vira vazio
        self.assertEqual(procs[2]["cliente"], "ANTÔNIA MODELO")
        self.assertEqual(set(x), {c for c, _, _ in p.COLUNAS})

    def test_juntar_sem_repetir_e_ordenado(self):
        ativos = p.processos_do_html(fixture("ativos.html"), "ativo")
        encerrados = p.processos_do_html(fixture("encerrados.html"), "encerrado")
        todos = p.juntar([ativos, encerrados])
        self.assertEqual(len(todos), 4)
        self.assertEqual([x["cliente"] for x in todos],
                         ["ANTÔNIA MODELO", "BENEDITO TESTE", "JOSÉ EXEMPLO", "MARIA FICTÍCIA"])
        self.assertEqual(next(x for x in todos if x["ci"] == "910002")["situacao"], "ativo")  # a 1ª leitura vence
        self.assertEqual(p.contar(todos)["ativos"], 3)
        p.marcar_tarefas(todos, {"910001", "910003"}, {"910003"})
        tarefas = {x["ci"]: x["tarefas"] for x in todos}
        self.assertEqual(tarefas, {"910001": "sem tarefa aberta", "910002": "com tarefa aberta",
                                   "910003": "nenhuma tarefa", "910004": ""})
        self.assertEqual([t for t, _ in p.blocos(todos)],
                         ["ATIVOS: 3 processos", "ENCERRADOS: 1 processos",
                          "ATIVOS SEM TAREFA ABERTA: 2 processos (1 sem nenhuma tarefa)"])

    def test_url_so_get_com_area_e_periodo(self):
        url = p.url_pesquisa(["4"], "encerrados", date(2026, 1, 1), date(2026, 6, 30))
        self.assertIn("pesq[pr_areas_id][]=4", url)
        self.assertIn("pesq[filtros_multi][]=encerrados", url)
        self.assertIn("pesq[tp_data]=data_cadastro&pesq[idata]=01/01/2026&pesq[fdata]=30/06/2026", url)
        self.assertTrue(url.startswith("?pag=sys/processos/processos-lista.php"))
        self.assertNotIn("act=", url)


class TestExecutar(Base):
    def test_simulado_grava_csv_e_json(self):
        secao = p.executar(self.ctx(simulado_=True))
        self.assertEqual(secao.numeros, {"total": 4, "ativos": 3, "encerrados": 1,
                                         "ativos_sem_tarefa_aberta": 2, "ativos_sem_nenhuma_tarefa": 1})
        self.assertIn("4 processos da área Previdenciária (3 ativos, 1 encerrados, 2 ativos sem tarefa aberta)", secao.resumo)
        arq = self.pasta / "saida" / "processos-previdenciaria.csv"
        with open(arq, encoding="utf-8-sig", newline="") as f:
            linhas = list(csv.reader(f, delimiter=";"))
        # três blocos, cada um com título e cabeçalho, separados por duas linhas vazias
        self.assertEqual(linhas[0], ["ATIVOS: 3 processos"])
        self.assertEqual(linhas[1][:4], ["CI", "Número", "Ativo/Encerrado", "Tarefas"])
        self.assertEqual([l[0] for l in linhas[2:5]], ["910003", "910002", "910001"])
        self.assertEqual(linhas[5:7], [[], []])
        self.assertEqual(linhas[7], ["ENCERRADOS: 1 processos"])
        self.assertEqual(linhas[9][0], "910004")
        self.assertEqual(linhas[12], ["ATIVOS SEM TAREFA ABERTA: 2 processos (1 sem nenhuma tarefa)"])
        self.assertEqual([(l[0], l[3]) for l in linhas[14:16]],
                         [("910003", "nenhuma tarefa"), ("910001", "sem tarefa aberta")])
        self.assertEqual(len(linhas), 16)
        self.assertIn("2 ativos sem tarefa aberta", secao.resumo)
        self.assertEqual(secao.numeros["ativos_sem_nenhuma_tarefa"], 1)
        dados = json.loads((self.pasta / "saida" / "processos-previdenciaria.json").read_text(encoding="utf-8"))
        self.assertEqual(dados["total"], 4)
        self.assertEqual(dados["areas_id"], ["4"])
        self.assertEqual(oct(arq.stat().st_mode & 0o777), "0o600")
        # resumo por ação: a mais comum primeiro
        self.assertEqual(secao.itens[0].titulo, "APOSENTADORIA IDADE RURAL")

    def test_sem_tarefas(self):
        self.escrever_env(ORELHA_PROCESSOS_TAREFAS="false")
        secao = p.executar(self.ctx(simulado_=True))
        self.assertEqual(secao.numeros["ativos_sem_tarefa_aberta"], 0)
        arq = self.pasta / "saida" / "processos-previdenciaria.csv"
        with open(arq, encoding="utf-8-sig", newline="") as f:
            titulos = [l[0] for l in csv.reader(f, delimiter=";") if len(l) == 1]
        self.assertEqual(titulos, ["ATIVOS: 3 processos", "ENCERRADOS: 1 processos"])

    def test_url_sem_tarefa(self):
        url = p.url_pesquisa(["4"], "ativos", extra=p.SEM_TAREFA_ABERTA)
        self.assertIn("pesq[com_ou_sem_tipo_tarefa]=sem&pesq[flag_status_tipo_tarefa]=abertas", url)

    def test_so_ativos(self):
        self.escrever_env(ORELHA_PROCESSOS_SITUACOES="ativos")
        secao = p.executar(self.ctx(simulado_=True))
        self.assertEqual(secao.numeros["total"], 3)
        self.assertNotIn("encerrados", secao.resumo)

    def test_config_invalida(self):
        for nome, valor in (("ORELHA_PROCESSOS_AREAS", "prev"), ("ORELHA_PROCESSOS_SITUACOES", "todos")):
            self.escrever_env(**{nome: valor})
            with self.assertRaises(config.ConfigErro):
                p.executar(self.ctx(simulado_=True))

    def test_lista_cheia_divide_por_periodo(self):
        """Sem período veio cheia (500): lê por ano; o ano cheio é dividido ao meio."""
        self.escrever_env(ORELHA_PROCESSOS_DESDE="01/01/2025", ORELHA_PROCESSOS_SITUACOES="ativos",
                          ORELHA_PROCESSOS_TAREFAS="false")
        cheia = list(range(1, p.LIMITE + 1))
        respostas = {
            None: cheia,
            (date(1900, 1, 1), date(2024, 12, 31)): [9001],
            (date(2025, 1, 1), date(2025, 12, 31)): cheia,           # cheia: divide
            (date(2025, 1, 1), date(2025, 7, 2)): list(range(1, 300)),
            (date(2025, 7, 3), date(2025, 12, 31)): list(range(300, 501)),
            (date(2026, 1, 1), HOJE): [7001, 7002],
        }
        pedidos = []

        def ler(ctx, url):
            chave = None
            if "pesq[idata]=" in url:
                ini = url.split("pesq[idata]=")[1].split("&")[0]
                fim = url.split("pesq[fdata]=")[1].split("&")[0]
                chave = (vios.data_br(ini), vios.data_br(fim))
            pedidos.append(chave)
            return lista_html(respostas[chave])

        with mock.patch.object(p, "ler_pesquisa", side_effect=ler), mock.patch.object(p.vios, "abrir"):
            secao = p.executar(self.ctx())
        self.assertEqual(secao.numeros["total"], 1 + 500 + 2)
        self.assertEqual(len(pedidos), 6)
        self.assertEqual(secao.avisos, [])

    def test_tela_errada_e_erro(self):
        with mock.patch.object(p.vios, "buscar_get", return_value="<html><title>Login</title></html>"), \
                mock.patch.object(p.vios, "abrir"):
            with self.assertRaises(vios.ViosErro):
                p.executar(self.ctx())

    def test_tela_de_processos_sem_tabela_e_zero(self):
        with mock.patch.object(p.vios, "buscar_get", return_value="<html><title>Processos</title></html>"), \
                mock.patch.object(p.vios, "abrir"):
            secao = p.executar(self.ctx())
        self.assertEqual(secao.numeros["total"], 0)


if __name__ == "__main__":
    unittest.main()
