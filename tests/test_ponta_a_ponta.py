"""Ponta a ponta, sem VIOS e sem IA: lista -> fichas -> <GRUPO>.json -> PDF.

Roda o relatorio_processos.main de verdade (pesquisa, leitura da lista, ficha pelo
bot/processo_ficha.py) contra um navegador FALSO que imita as telas do VIOS. Depois
roda o relatorio_cliente.main sem IA na mesma pasta e confere o PDF.

Só login, criar_driver, config e log são trocados. Dados todos inventados.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By

import relatorio_cliente as rc
import relatorio_processos as rp
from bot import processo_ficha as pf
from bot import processos_grupo as pg
from bot.campos_relatorio import COLUNAS
from tests.test_pdf_relatorio import texto_pdf

TITULOS = [
    "ID da extração", "Número do processo", "Parte ativa", "Parte passiva", "Tipo de processo", "Órgão",
    "Data da distribuição", "Valor da ação", "Cidade/UF", "Última movimentação",
    "Resumo do caso", "PENDÊNCIA", "Financeira",
]
# nada disso pode chegar ao cliente (PDF ou linhas do relatório)
PROIBIDOS = ["http", "zoom", "445566", "98765432100", "LINK DO CHAT", "chat.exemplo", "sigilosa",
             "suporte@exemplo", "ADVOGADA FICTICIA"]

GRUPOS = {"GRUPO ALFA FICTICIO": "11", "GRUPO BETA FICTICIO": "22"}

OBS_INTERNA = "Observação interna sigilosa. LINK DO CHAT: https://chat.exemplo.com/interno/xyz"


def celulas(ci, numero, autor, reu, cliente, polo, objeto, obs=""):
    return {
        "processos_id": ci,
        "nro_proc_html": "Cliente OURO\nCNJ: " + numero,
        "ativahtml": "Autor: " + autor,
        "passivahtml": "Réu: " + reu,
        "clientes_nome": cliente,
        "cliente_escritorio": polo,
        "pr_areas_nome": "Cível",
        "pr_processos_nome": "CÍVEL",
        "processos_acoes_nome": "Ação de Cobrança",
        "orgaos_nome": "Comarca Inventada",
        "orgaos_uf": "CE",
        "vara": "1ª Vara Cível",
        "tipo_vara": "Cível",
        "advogado_nome": "ADVOGADA FICTICIA SOUZA",
        "data_acao": "15/03/2025 00:00",
        "valor_acao": "R$ 50.000,00",
        "objeto": objeto,
        "obs_proc": obs,
    }


# lista de cada grupo: CI -> células cruas da linha
PROCESSOS = {
    "11": [
        celulas("101", "0001234-56.2025.8.06.0001", "LOJA ALFA FICTICIA LTDA", "FULANO DE TAL INVENTADO",
                "LOJA ALFA FICTICIA LTDA", "Parte Ativa", "cobrança de duplicatas", OBS_INTERNA),
        celulas("102", "0005678-90.2025.8.06.0001", "CICLANO INVENTADO", "LOJA ALFA FICTICIA LTDA",
                "LOJA ALFA FICTICIA LTDA", "Parte Passiva", "indenização"),
    ],
    "22": [
        celulas("201", "0009999-11.2024.8.06.0002", "MERCADO BETA FICTICIO", "BELTRANO INVENTADO",
                "MERCADO BETA FICTICIO", "Parte Ativa", "cheque sem fundo"),
    ],
}
# CI 102: a ficha não carrega (só os rótulos aparecem)
FICHA_FALHA = "102"


def ficha_js(ci):
    """O que o bot/js/ficha.js devolveria na ficha do CI."""
    campos = {
        "N.° CNJ": "",
        "Polo do cliente": "Parte Ativa",
        "Cidade / UF": "Cidade Inventada / CE",
        "Fase": "Conhecimento",
        "Data da ação / Distribuição": "15/03/2025",
        "Valor da ação": "R$ 50.000,00",
        "Advogado responsável": "ADVOGADA FICTICIA SOUZA",
    }
    tarefas = []
    if ci == "101":
        tarefas = [
            # cancelada, com data mais nova: não pode virar a última movimentação
            {"ci": "9001", "situacao": "CANCELADA", "tipo": "AUDIÊNCIA CANCELADA FICTICIA",
             "descricao": "Remarcada", "comentarios": "", "para_conclusao": "10/09/2025", "limite": "",
             "concluida_em": "12/10/2025"},
            # concluída com link de reunião, senha e link do chat no texto
            {"ci": "9002", "situacao": "", "tipo": "AUDIÊNCIA DE CONCILIAÇÃO",
             "descricao": "Audiência por vídeo. Link: https://zoom.us/j/98765432100 Senha: 445566",
             "comentarios": ("Audiência realizada, sem acordo. Sala zoom.us/j/98765432100 senha 445566. "
                             "LINK DO CHAT: https://chat.exemplo.com/sala/abc. Dúvidas: suporte@exemplo.com"),
             "para_conclusao": "01/10/2025", "limite": "", "concluida_em": "02/10/2025"},
            # aberta: vai para a PENDÊNCIA
            {"ci": "9003", "situacao": "", "tipo": "MANIFESTAÇÃO SOBRE LAUDO",
             "descricao": "Ver https://zoom.us/j/111", "comentarios": "", "para_conclusao": "20/11/2030",
             "limite": "25/11/2030", "concluida_em": ""},
        ]
    return {
        "campos": campos,
        "cidade_uf": campos["Cidade / UF"],
        "fase": campos["Fase"],
        "data_distribuicao": campos["Data da ação / Distribuição"],
        "valor_acao": campos["Valor da ação"],
        "justica": "Estadual",
        "sistema": "PJe",
        "tarefas": tarefas,
        "comentarios": [{"data": "01/09/2025 10:00", "autor": "ADVOGADA FICTICIA SOUZA",
                         "texto": "Cliente avisado pelo telefone (85) 98888-7777"}],
        "arquivos": [{"data": "01/09/2025", "pasta": "Geral", "tipo": "PDF", "descricao": "Inicial",
                      "arquivo": "inicial.pdf"}],
    }


class Elemento:
    def __init__(self, atributos=None, filhos=None):
        self.atributos = atributos or {}
        self.filhos = filhos or []
        self.velho = False

    def get_attribute(self, nome):
        return self.atributos.get(nome)

    def find_elements(self, by, valor):
        return list(self.filhos) if (by, valor) == (By.TAG_NAME, "option") else []

    def is_enabled(self):
        # staleness_of: depois do Pesquisar a página é outra
        if self.velho:
            raise StaleElementReferenceException("página recarregada")
        return True


class NavegadorVIOS:
    """Imita as telas do VIOS que o robô usa: lista de processos e ficha (processos-vis.php).

    Só leitura, como o robô: o "Pesquisar" troca a página; nada é gravado.
    """

    def __init__(self, processos=None, ficha_falha=FICHA_FALHA):
        self.processos = processos or PROCESSOS
        self.ficha_falha = ficha_falha
        self.current_url = "about:blank"
        self.pagina = None
        self.select = None
        self.resultado = None  # valor do grupo pesquisado
        self.ci = None
        self.urls = []
        self.scripts = []

    # ---- navegação ----
    def get(self, url):
        self.urls.append(url)
        self.current_url = url
        if self.select is not None:
            self.select.velho = True
        self.select = None
        self.resultado = None
        if "processos-lista.php" in url:
            self.pagina = "lista"
            self._novo_select()
        elif "processos-vis.php" in url:
            self.pagina = "ficha"
            self.ci = re.search(r"processos_id=(\d+)", url).group(1)
        else:
            self.pagina = None

    def _novo_select(self):
        opcoes = [Elemento({"value": "", "textContent": ""}), Elemento({"value": "0", "textContent": "TODOS"})]
        opcoes += [Elemento({"value": v, "textContent": " %s " % n}) for n, v in GRUPOS.items()]
        self.select = Elemento({"name": pg.FILTRO_GRUPO}, opcoes)

    # ---- busca de elementos ----
    def find_element(self, by, valor):
        achados = self.find_elements(by, valor)
        if not achados:
            raise NoSuchElementException(f"{by}={valor}")
        return achados[0]

    def find_elements(self, by, valor):
        loc = (by, valor)
        if self.pagina == "lista":
            if loc == (By.NAME, pg.FILTRO_GRUPO):
                return [self.select]
            if loc == pg.LINHAS:
                return [object() for _ in self._linhas()]
            if loc == (By.CSS_SELECTOR, ".geratabela_total_quantidade_original"):
                return [Elemento({"textContent": "Total (%d)" % len(self._linhas())})] if self.resultado else []
        if self.pagina == "ficha":
            ok = self.ci != self.ficha_falha
            if loc == pf.BLOCOS:
                return [object()] if ok else []
            if loc == pf.ROTULOS:
                return [object()]
            if loc == pf.TAREFAS:
                return [object()] if ok else []
        # campos de login (rp.na_tela_de_login e processo_ficha.CAMPO_SENHA): sessão sempre ativa
        return []

    def _linhas(self):
        if self.resultado is None:
            return []
        if self.resultado == pg.VALOR_TODOS:
            return [c for lista in self.processos.values() for c in lista]
        return self.processos.get(self.resultado, [])

    # ---- JavaScript ----
    def execute_script(self, script, *args):
        self.scripts.append(script)
        if "pesq[limit]" in script:
            sel, valor, limite, encerrados = args
            assert sel is self.select, "Pesquisar com select de outra página"
            assert limite == pg.LIMITE
            if valor not in [o.get_attribute("value") for o in sel.filhos]:
                return "Grupo Cliente com valor %s não existe no filtro" % valor
            # requestSubmit: a página recarrega com o resultado
            self.select.velho = True
            self._novo_select()
            self.resultado = valor
            return ""
        if script == pg.JS_LER_LINHAS:
            return [{"ci_linha": c["processos_id"], "celulas": dict(c), "badges": ["Cliente OURO"], "vinculo": ""}
                    for c in self._linhas()]
        if script == pf.script_ficha():
            assert self.pagina == "ficha"
            return ficha_js(self.ci)
        raise AssertionError("script inesperado: " + script[:80])

    def save_screenshot(self, caminho):
        return False

    def quit(self):
        pass


def cfg_falso(pasta):
    return SimpleNamespace(
        campo_usuario=(By.CSS_SELECTOR, "input[name='form[usuario]']"),
        campo_senha=(By.CSS_SELECTOR, "input[name='form[senha]']"),
        timeout=1,
        pasta_saida=Path(pasta),
        headless=True,
        manter_aberto=False,
    )


class TestPontaAPonta(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ponta a ponta "))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.base = self.tmp / "relatorios"
        self.base.mkdir()
        self.env = self.tmp / ".env.teste"
        # .env falso, sem senha nem chave: só o que o relatorio_cliente lê
        self.env.write_text("RELATORIO_PASTA=%s\nRELATORIO_IA=false\n" % self.base, encoding="utf-8")
        self.driver = NavegadorVIOS()
        for alvo, nome, kw in (
            (rp, "criar_driver", {"return_value": self.driver}),
            (rp, "fazer_login", {}),
            (rp, "ir_ate_tabela", {}),
            (rp, "configurar_log", {}),
            (rc, "configurar_log", {}),
            (rp.config, "carregar", {"return_value": cfg_falso(self.tmp / "saida")}),
        ):
            p = mock.patch.object(alvo, nome, **kw)
            p.start()
            self.addCleanup(p.stop)
        # o load_dotenv do relatorio_cliente mexe no os.environ: volta tudo no fim
        p = mock.patch.dict(os.environ, {"RELATORIO_PASTA": str(self.base), "PROCESSOS_FICHA": "",
                                         "PROCESSOS_SEM_GRUPO": "", "PROCESSOS_ENCERRADOS": "",
                                         "PROCESSOS_GRUPOS": "", "RELATORIO_IA": "",
                                         "RELATORIO_CLIENTE_PROMPT": ""})
        p.start()
        self.addCleanup(p.stop)

    def _capturar(self, *args):
        with self.assertLogs("relatorio", "INFO") as logs:
            codigo = rp.main(str(self.env), "--grupo", "todos", *args)
        return codigo, "\n".join(logs.output)

    def _pasta_do_dia(self):
        dias = [p for p in self.base.iterdir() if p.is_dir()]
        self.assertEqual(len(dias), 1)
        return dias[0]

    def _texto(self, pdf):
        texto = texto_pdf(pdf)
        if shutil.which("pdftotext"):
            saida = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, check=True)
            texto += "\n" + saida.stdout.decode("utf-8", "replace")
        return texto

    def _sem_proibidos(self, texto, onde):
        junto = re.sub(r"\s+", "", texto).lower()
        for proibido in PROIBIDOS:
            self.assertNotIn(proibido.lower(), texto.lower(), f"{proibido!r} apareceu em {onde}")
            self.assertNotIn(re.sub(r"\s+", "", proibido).lower(), junto, f"{proibido!r} apareceu em {onde}")

    def test_lista_ficha_json_pdf(self):
        codigo, log = self._capturar()
        self.assertEqual(codigo, 0, log)
        self.assertIn("ficha do CI 102 não lida", log)
        # só leitura: nenhuma página de edição, exclusão ou processamento
        for url in self.driver.urls:
            self.assertRegex(url, r"processos-(lista|vis)\.php")
            self.assertNotRegex(url.lower(), r"edit|apagar|excluir|processar|amostragem")

        pasta = self._pasta_do_dia()
        for grupo in GRUPOS:
            self.assertTrue((pasta / (grupo + ".txt")).is_file())
            self.assertTrue((pasta / (grupo + ".json")).is_file())

        # contrato 1
        alfa = json.loads((pasta / "GRUPO ALFA FICTICIO.json").read_text(encoding="utf-8"))
        self.assertEqual([r["ci"] for r in alfa], ["101", "102"])
        chaves = {"grupo", "ci", "numero", "parte_ativa", "parte_passiva", "cliente", "polo_cliente", "area",
                  "tipo_processo", "acao", "orgao", "uf", "vara", "tipo_vara", "data_acao", "valor_acao",
                  "objeto", "obs_proc", "posicao", "situacao", "ficha"}
        for r in alfa:
            self.assertEqual(set(r), chaves)
            self.assertEqual(r["grupo"], "GRUPO ALFA FICTICIO")
            self.assertEqual(r["data_acao"], "15/03/2025")
            self.assertEqual(r["valor_acao"], "50.000,00")
            self.assertEqual(r["tipo_processo"], "CÍVEL")
            self.assertNotIn("Cliente OURO", r["numero"])
        r101, r102 = alfa
        self.assertEqual(r101["obs_proc"], OBS_INTERNA)
        self.assertEqual(r101["polo_cliente"], "Parte Ativa")
        self.assertEqual(r102["posicao"], pg.REU)
        # contrato 2: ficha lida e ficha com erro
        self.assertTrue(r101["ficha"]["ok"])
        self.assertEqual(r101["ficha"]["cidade_uf"], "Cidade Inventada / CE")
        self.assertEqual(r101["ficha"]["valor_acao"], "50.000,00")
        self.assertEqual([t["situacao"] for t in r101["ficha"]["tarefas"]], ["CANCELADA", "", ""])
        self.assertFalse(r102["ficha"]["ok"])
        self.assertIn("rótulos", r102["ficha"]["erro"])
        # obs_proc nunca vai para o .txt
        txt = (pasta / "GRUPO ALFA FICTICIO.txt").read_text(encoding="utf-8")
        self.assertNotIn("sigilosa", txt)
        self.assertNotIn("LINK DO CHAT", txt)

        # etapa 2: PDF sem IA, pela pasta do dia mais recente (RELATORIO_PASTA do .env)
        with self.assertLogs("relatorio_cliente", "INFO") as logs:
            self.assertEqual(rc.main(str(self.env)), 0, "\n".join(logs.output))
        pdfs = sorted(p.name for p in pasta.glob("*.pdf"))
        self.assertEqual(pdfs, ["GRUPO ALFA FICTICIO.pdf", "GRUPO BETA FICTICIO.pdf"])

        texto = self._texto(pasta / "GRUPO ALFA FICTICIO.pdf")
        corrido = " ".join(texto.split())
        self.assertEqual([t for _, t in COLUNAS], TITULOS)
        # a capa também cita "Tipo de processo" e "Cidade/UF": a ordem é conferida no bloco do processo
        pos = corrido.index("ID da extração")
        for titulo in TITULOS:
            self.assertIn(titulo, corrido)
            achou = corrido.find(titulo, pos)
            self.assertGreaterEqual(achou, 0, f"título {titulo!r} fora da ordem")
            pos = achou + len(titulo)
        self.assertIn("GRUPO ALFA FICTICIO", corrido)
        self.assertIn("0001234-56.2025.8.06.0001", corrido)
        self.assertIn("02/10/2025", corrido)  # última movimentação: a concluída, não a cancelada
        self.assertIn("MANIFESTAÇÃO SOBRE LAUDO", corrido)  # pendência
        self.assertIn("não foi lida", corrido)  # observação da ficha com erro
        self.assertNotIn("AUDIÊNCIA CANCELADA", corrido)
        self._sem_proibidos(texto, "PDF do grupo ALFA")
        self._sem_proibidos(self._texto(pasta / "GRUPO BETA FICTICIO.pdf"), "PDF do grupo BETA")

    def test_linhas_do_relatorio_sem_dado_interno(self):
        self.assertEqual(self._capturar()[0], 0)
        from bot.campos_relatorio import montar_linhas

        pasta = self._pasta_do_dia()
        registros = json.loads((pasta / "GRUPO ALFA FICTICIO.json").read_text(encoding="utf-8"))
        linhas = montar_linhas(registros, ia=None)
        self.assertEqual(len(linhas), 2)
        for linha in linhas:
            self.assertEqual(list(linha), [c for c, _ in COLUNAS])
            self.assertTrue(all(isinstance(v, str) for v in linha.values()))
            self._sem_proibidos(json.dumps(linha, ensure_ascii=False), "linhas do relatório")
        por_numero = {linha["numero"]: linha for linha in linhas}
        l101 = por_numero["0001234-56.2025.8.06.0001"]
        self.assertTrue(l101["ultima_movimentacao"].startswith("02/10/2025 - AUDIÊNCIA DE CONCILIAÇÃO"))
        self.assertIn("sem acordo", l101["ultima_movimentacao"])
        self.assertEqual(l101["pendencia"], "MANIFESTAÇÃO SOBRE LAUDO até 20/11/2030")
        self.assertEqual(l101["cidade_uf"], "Cidade Inventada / CE")
        self.assertEqual(l101["parte_ativa"], "LOJA ALFA FICTICIA LTDA")
        self.assertEqual(l101["valor_acao"], "R$ 50.000,00")
        l102 = por_numero["0005678-90.2025.8.06.0001"]
        self.assertEqual(l102["ultima_movimentacao"], "não informado")

    def test_sem_grupo_cliente(self):
        processos = dict(PROCESSOS)
        processos["99"] = [celulas("301", "0007777-00.2025.8.06.0003", "SEM GRUPO INVENTADO", "OUTRO INVENTADO",
                                   "SEM GRUPO INVENTADO", "Parte Ativa", "aluguel")]
        # o grupo "99" não está no filtro: o CI 301 só aparece no TODOS
        self.driver.processos = processos
        codigo, log = self._capturar("--sem-grupo", "--sem-ficha")
        self.assertEqual(codigo, 0, log)
        pasta = self._pasta_do_dia()
        sem = json.loads((pasta / "SEM GRUPO CLIENTE.json").read_text(encoding="utf-8"))
        self.assertEqual([r["ci"] for r in sem], ["301"])
        self.assertFalse(sem[0]["ficha"]["ok"])
        with self.assertLogs("relatorio_cliente", "INFO"):
            self.assertEqual(rc.main(str(self.env), str(pasta)), 0)
        self.assertTrue((pasta / "SEM GRUPO CLIENTE.pdf").is_file())


if __name__ == "__main__":
    unittest.main()
