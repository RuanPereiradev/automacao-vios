"""Testes da leitura da lista de processos (bot/processos_grupo.py) com driver falso.

Só dados fictícios. Não acessa o VIOS.
"""
import unittest

from selenium.common.exceptions import StaleElementReferenceException

from bot import processos_grupo as pg

CHAVES_CONTRATO = {
    "grupo", "ci", "numero", "parte_ativa", "parte_passiva", "cliente", "polo_cliente", "area",
    "tipo_processo", "acao", "orgao", "uf", "vara", "tipo_vara", "data_acao", "valor_acao", "objeto",
    "obs_proc", "posicao", "situacao", "ficha",
}


def bruto(ci="101", **celulas):
    """Linha crua como o JS_LER_LINHAS devolve."""
    base = {
        "processos_id": ci,
        "nro_proc_html": "Cliente OURO\nCNJ: 0000001-00.2026.8.06.0001",
        "ativahtml": "Autor: FULANO FICTICIO\nAutor: BELTRANA FICTICIA",
        "passivahtml": "Réu: EMPRESA FICTICIA LTDA",
        "clientes_nome": "EMPRESA FICTICIA LTDA",
        "cliente_escritorio": "Parte Passiva",
        "pr_areas_nome": "Cível Consumidor",
        "pr_processos_nome": "CÍVEL",
        "processos_acoes_nome": "Ação de cobrança",
        "orgaos_nome": "Juizado Especial Cível",
        "orgaos_uf": "CE",
        "vara": "1ª Vara",
        "tipo_vara": "Juizado",
        "data_acao": "15/03/2025",
        "valor_acao": "50.000,00",
        "objeto": "Cobrança indevida",
        "obs_proc": "FASE: INICIAL LINK DO CHAT: https://chat.exemplo/x",
        "advogado_nome": "ADVOGADO FICTICIO",
    }
    base.update(celulas)
    return {"ci_linha": ci, "celulas": base, "badges": ["Cliente OURO"], "vinculo": "PROCESSO PRINCIPAL"}


class Elemento:
    """Elemento falso: atributos + filhos por seletor."""

    def __init__(self, atributos=None, filhos=None, stale=False):
        self.atributos = atributos or {}
        self.filhos = filhos or {}
        self.stale = stale

    def get_attribute(self, nome):
        return self.atributos.get(nome)

    def find_elements(self, by, valor):
        return list(self.filhos.get(valor, []))

    def is_enabled(self):
        if self.stale:
            raise StaleElementReferenceException("página recarregou")
        return True


class DriverLista:
    """Imita o pouco do Selenium que ler_processos/pesquisar_grupo usam."""

    def __init__(self, brutos=None, rodape=None, trs=None, js_falha=False, resposta_pesquisa=""):
        self.brutos = brutos or []
        self.trs = trs if trs is not None else [Elemento() for _ in self.brutos]
        self.rodape = rodape
        self.js_falha = js_falha
        self.resposta_pesquisa = resposta_pesquisa
        self.scripts = []
        self.urls = []
        self.select = Elemento()

    def get(self, url):
        self.urls.append(url)

    def find_element(self, by, valor):
        return self.select

    def find_elements(self, by, valor):
        if valor == pg.LINHAS[1]:
            return list(self.trs)
        if valor == ".geratabela_total_quantidade_original" and self.rodape is not None:
            return [Elemento({"textContent": self.rodape})]
        return []

    def execute_script(self, js, *args):
        self.scripts.append((js, args))
        if js is pg.JS_LER_LINHAS:
            if self.js_falha:
                raise RuntimeError("javascript error")
            return self.brutos
        # pesquisar_grupo: depois do submit, o select antigo some
        self.select.stale = True
        novo = Elemento()
        self.select = novo
        return self.resposta_pesquisa


class TestLerProcessos(unittest.TestCase):
    def test_colunas_novas(self):
        itens, erros = pg.ler_processos(DriverLista([bruto()], rodape="Total (1)"), 1)
        self.assertEqual(erros, 0)
        it = itens[0]
        self.assertEqual(it["ci"], "101")
        self.assertEqual(it["numero"], "CNJ: 0000001-00.2026.8.06.0001")
        self.assertEqual(it["parte_ativa"], ["Autor: FULANO FICTICIO", "Autor: BELTRANA FICTICIA"])
        self.assertEqual(it["parte_passiva"], ["Réu: EMPRESA FICTICIA LTDA"])
        self.assertEqual(it["polo_cliente"], "Parte Passiva")
        self.assertEqual(it["tipo_processo"], "CÍVEL")
        self.assertEqual(it["vara"], "1ª Vara")
        self.assertEqual(it["tipo_vara"], "Juizado")
        self.assertEqual(it["uf"], "CE")
        self.assertEqual(it["data_acao"], "15/03/2025")
        self.assertEqual(it["valor_acao"], "50.000,00")
        self.assertEqual(it["obs_proc"], "FASE: INICIAL LINK DO CHAT: https://chat.exemplo/x")
        self.assertEqual(it["vinculo"], "processo principal")

    def test_vazios_do_vios_viram_texto_vazio(self):
        b = bruto(data_acao="00/00/0000", valor_acao="0,00", objeto="", pr_processos_nome="0,00")
        it = pg.ler_processos(DriverLista([b]), 1)[0][0]
        self.assertEqual(it["data_acao"], "")
        self.assertEqual(it["valor_acao"], "")
        self.assertEqual(it["objeto"], "")
        self.assertEqual(it["tipo_processo"], "")
        b = bruto(valor_acao="R$ 0,00", data_acao="")
        it = pg.ler_processos(DriverLista([b]), 1)[0][0]
        self.assertEqual(it["valor_acao"], "")
        self.assertEqual(it["data_acao"], "")

    def test_valor_com_rs_e_data_com_hora(self):
        it = pg.ler_processos(DriverLista([bruto(valor_acao="R$ 1.234,56", data_acao="02/01/2026 00:00")]), 1)[0][0]
        self.assertEqual(it["valor_acao"], "1.234,56")
        self.assertEqual(it["data_acao"], "02/01/2026")

    def test_coluna_faltando_vira_vazio(self):
        b = bruto()
        for col in ("cliente_escritorio", "vara", "obs_proc", "data_acao"):
            del b["celulas"][col]
        it = pg.ler_processos(DriverLista([b]), 1)[0][0]
        for campo in ("polo_cliente", "vara", "obs_proc", "data_acao"):
            self.assertEqual(it[campo], "", campo)

    def test_ci_da_linha_quando_falta_a_coluna(self):
        b = bruto(ci="77")
        del b["celulas"]["processos_id"]
        self.assertEqual(pg.ler_processos(DriverLista([b]), 1)[0][0]["ci"], "77")

    def test_rodape_diferente_avisa_leitura_incompleta(self):
        with self.assertLogs("bot.processos_grupo", "WARNING") as logs:
            itens, _ = pg.ler_processos(DriverLista([bruto("1"), bruto("2")], rodape="Total (3)"), 1)
        self.assertEqual(len(itens), 2)
        self.assertIn("leitura incompleta", "\n".join(logs.output))

    def test_linha_com_erro_nao_para_a_lista(self):
        with self.assertLogs("bot.processos_grupo", "WARNING"):
            itens, erros = pg.ler_processos(DriverLista([bruto("1"), {"erro": "célula sumiu"}, bruto("3")]), 1)
        self.assertEqual([it["ci"] for it in itens], ["1", "3"])
        self.assertEqual(erros, 1)

    def test_js_falhou_le_linha_por_linha(self):
        def td(col, texto, filhos=None):
            return Elemento({"data-id": "processos-lista_linha_0_" + col, "innerText": texto}, filhos)

        badge = Elemento({"innerText": "Cliente OURO"})
        tds = [
            td("processos_id", "55"),
            td("nro_proc_html", "Cliente OURO\nCNJ: 0000002-00.2026.8.06.0001", {".vj-badge": [badge]}),
            td("ativahtml", "Autor: FULANO FICTICIO"),
            td("passivahtml", "Réu: EMPRESA FICTICIA"),
            td("cliente_escritorio", "Parte Ativa"),
            td("data_acao", "00/00/0000"),
            td("valor_acao", "10.000,00"),
        ]
        tr = Elemento({"data-processos_id": "55"}, {"td[data-id]": tds})
        driver = DriverLista([], trs=[tr], js_falha=True)
        with self.assertLogs("bot.processos_grupo", "WARNING") as logs:
            itens, erros = pg.ler_processos(driver, 1)
        self.assertIn("linha por linha", "\n".join(logs.output))
        self.assertEqual(erros, 0)
        it = itens[0]
        self.assertEqual(it["ci"], "55")
        self.assertEqual(it["numero"], "CNJ: 0000002-00.2026.8.06.0001")
        self.assertEqual(it["polo_cliente"], "Parte Ativa")
        self.assertEqual(it["data_acao"], "")
        self.assertEqual(it["valor_acao"], "10.000,00")


class TestPesquisarGrupo(unittest.TestCase):
    def test_limite_sem_teto(self):
        self.assertEqual(pg.LIMITE, "9999999")
        driver = DriverLista()
        pg.pesquisar_grupo(driver, "97", 1)
        js, args = driver.scripts[-1]
        self.assertEqual(args[1:], ("97", "9999999", False))
        self.assertIn("pesq[limit]", js)
        # só leitura: nunca usa amostragem nem Processar
        self.assertNotIn("amostragem", js)

    def test_encerrados_marca_a_opcao(self):
        driver = DriverLista()
        pg.pesquisar_grupo(driver, pg.VALOR_TODOS, 1, encerrados=True)
        js, args = driver.scripts[-1]
        self.assertEqual(args[1:], ("0", "9999999", True))
        self.assertIn("pesq[filtros_multi][]", js)
        self.assertIn('"encerrados"', js)
        # as opções combinam com E: a pesquisa de encerrados desmarca "ativos"
        self.assertIn("ativos.selected = false", js)

    def test_sem_campo_de_limite_para(self):
        driver = DriverLista()
        pg.pesquisar_grupo(driver, "97", 1)
        self.assertIn("if (!lim) return", driver.scripts[-1][0])
        driver = DriverLista(resposta_pesquisa="campo pesq[limit] não encontrado no formulário (a lista viria cortada)")
        with self.assertRaises(RuntimeError):
            pg.pesquisar_grupo(driver, "97", 1)

    def test_erro_do_formulario_para(self):
        driver = DriverLista(resposta_pesquisa="opção 9999999 não existe em pesq[limit] (a lista viria cortada)")
        with self.assertRaises(RuntimeError):
            pg.pesquisar_grupo(driver, "97", 1)


class TestPoloDoVios(unittest.TestCase):
    def test_polo_passiva_vale_mais_que_os_nomes(self):
        it = {"cliente": "ACME LTDA", "polo_cliente": "Parte Passiva", "parte_ativa": ["Autor: ACME LTDA"]}
        self.assertEqual(pg.posicao_cliente(it), pg.REU)

    def test_polo_ativa(self):
        it = {"cliente": "ACME LTDA", "polo_cliente": "PARTE ATIVA", "parte_passiva": []}
        self.assertEqual(pg.posicao_cliente(it), pg.AUTOR)

    def test_polo_vazio_ou_desconhecido_compara_nomes(self):
        for polo in ("", "Terceiro", None):
            it = {"cliente": "ACME LTDA", "polo_cliente": polo, "parte_ativa": ["Autor: Acme Ltda."]}
            self.assertEqual(pg.posicao_cliente(it), pg.AUTOR, polo)
        it = {"cliente": "ACME LTDA", "polo_cliente": "Terceiro", "parte_ativa": ["Autor: OUTRA"]}
        self.assertIn("não identificada", pg.posicao_cliente(it))


class TestRegistroJson(unittest.TestCase):
    def _item(self, **kw):
        it = pg._item_de_bruto(bruto())
        it.update(kw)
        return it

    def test_chaves_do_contrato(self):
        ficha = {"ok": True, "erro": "", "cidade_uf": "Cidade Ficticia / CE"}
        reg = pg.registro("GRUPO FICTICIO", self._item(ficha=ficha))
        self.assertEqual(set(reg), CHAVES_CONTRATO)
        self.assertEqual(reg["grupo"], "GRUPO FICTICIO")
        self.assertEqual(reg["posicao"], pg.REU)
        self.assertEqual(reg["ficha"], ficha)
        for chave, valor in reg.items():
            if chave in ("parte_ativa", "parte_passiva"):
                self.assertIsInstance(valor, list)
            elif chave != "ficha":
                self.assertIsInstance(valor, str, chave)

    def test_sem_ficha_vira_ok_false(self):
        reg = pg.registro("G", {"ci": "1"})
        self.assertEqual(reg["ficha"]["ok"], False)
        self.assertEqual(reg["data_acao"], "")
        self.assertEqual(reg["parte_ativa"], [])

    def test_mesma_ordem_do_txt(self):
        itens = [self._item(ci="2", cliente="B"), self._item(ci="1", cliente="A")]
        self.assertEqual([r["ci"] for r in pg.montar_json("G", itens)], ["1", "2"])

    def test_nome_json(self):
        self.assertEqual(pg.nome_json("A/B: C"), "A-B- C.json")


class TestTxt(unittest.TestCase):
    def test_campos_novos_no_txt_e_obs_interna_fora(self):
        it = pg._item_de_bruto(bruto())
        it["ficha"] = {"ok": True, "cidade_uf": "Cidade Ficticia / CE", "fase": "Recursal"}
        txt = pg.montar_txt("GRUPO FICTICIO", [it], situacao="processos ativos e encerrados")
        self.assertIn("(processos ativos e encerrados)", txt)
        self.assertIn("Tipo de processo: CÍVEL", txt)
        self.assertIn("Data da distribuição: 15/03/2025", txt)
        self.assertIn("Valor da ação: R$ 50.000,00", txt)
        self.assertIn("Vara: 1ª Vara - Juizado", txt)
        self.assertIn("Cidade / UF: Cidade Ficticia / CE", txt)
        self.assertIn("Fase: Recursal", txt)
        self.assertIn("Posição do cliente: " + pg.REU, txt)
        self.assertNotIn("LINK DO CHAT", txt)

    def test_ficha_com_erro_nao_aparece(self):
        it = pg._item_de_bruto(bruto(valor_acao="0,00"))
        it["ficha"] = {"ok": False, "erro": "timeout", "cidade_uf": "X"}
        txt = pg.montar_txt("G", [it])
        self.assertIn("Cidade / UF: não informado", txt)
        self.assertIn("Valor da ação: não informado", txt)
        self.assertIn("(processos ativos)", txt)


if __name__ == "__main__":
    unittest.main()
