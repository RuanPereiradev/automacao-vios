"""Testes do relatório para o cliente (bot/relatorio_cliente.py e relatorio_cliente.py).

Usam dados inventados, um provedor de IA FALSO (nada vai para a OpenAI nem para a Anthropic)
e um gerar_pdf FALSO (o PDF de verdade é testado em test_pdf_relatorio.py).
"""
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import relatorio_cliente as entrada
from bot import campos_relatorio, custo
from bot import relatorio_cliente as rc


def registros(grupo, n=2):
    return [{
        "grupo": grupo, "ci": str(100 + i), "numero": f"000000{i}-11.2026.8.06.0001",
        "parte_ativa": [f"Autor: PESSOA TESTE {i}"], "parte_passiva": ["Contrário: EMPRESA FICTICIA LTDA"],
        "cliente": "EMPRESA FICTICIA LTDA", "polo_cliente": "Parte Passiva", "area": "Cível",
        "tipo_processo": "CÍVEL", "acao": "Indenização", "orgao": "Comarca Teste", "uf": "CE", "vara": "",
        "tipo_vara": "", "data_acao": "05/01/2026", "valor_acao": "1.000,00", "objeto": "cobrança",
        "obs_proc": "INTERNO", "posicao": "réu (o cliente está sendo processado)",
        "ficha": {"ok": True, "erro": "", "campos": {}, "cidade_uf": "Cidade Teste / CE", "fase": "",
                  "data_distribuicao": "", "valor_acao": "", "justica": "", "sistema": "",
                  "tarefas": [], "comentarios": [], "arquivos": []},
    } for i in range(1, n + 1)]


# variáveis de IA isoladas do .env de quem roda os testes
ENV = {"LLM_PROVEDOR": "openai", "LLM_MODELO": "gpt-5.6", "LLM_ESFORCO": "low", "LLM_LIMITE_US": "",
       "LLM_PRECOS": "", "RELATORIO_CLIENTE_PROMPT": "", "RELATORIO_PASTA": "", "SAIDA_PASTA": "",
       "RELATORIO_IA": "", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}


class IAFalsa:
    """Imita responder() dos provedores: um item por processo recebido."""

    def __init__(self, erro=None):
        self.chamadas = []
        self.erro = erro

    def responder(self, sistema, usuario, schema, pesquisar=False):
        self.chamadas.append({"sistema": sistema, "usuario": usuario, "schema": schema})
        if self.erro:
            raise self.erro
        itens = [{"id_extracao": p["id_extracao"], "resumo": "Resumo da IA", "pendencia": "Nada",
                  "financeira": "não identificada"} for p in json.loads(usuario)["processos"]]
        return {"processos": itens, "_uso": {"entrada": 1000, "entrada_cache": 0, "saida": 300}}


class AuthenticationError(Exception):
    """Mesmo nome da exceção dos SDKs (chave recusada)."""


class Base(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.pasta, ignore_errors=True)
        env = mock.patch.dict(os.environ, ENV)
        env.start()
        self.addCleanup(env.stop)
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        # gerar_pdf falso: grava um arquivo qualquer e guarda os argumentos
        self.pdfs = []
        falso = types.ModuleType("bot.pdf_relatorio")
        falso.gerar_pdf = self._gerar_pdf
        modulos = mock.patch.dict(sys.modules, {"bot.pdf_relatorio": falso})
        modulos.start()
        self.addCleanup(modulos.stop)

    def _gerar_pdf(self, caminho, grupo, linhas, gerado_em, observacoes=None, encerrados=0):
        self.pdfs.append({"caminho": Path(caminho), "grupo": grupo, "linhas": linhas, "gerado_em": gerado_em,
                          "observacoes": list(observacoes or []), "encerrados": encerrados})
        Path(caminho).write_bytes(b"%PDF-falso")
        return Path(caminho)

    def json(self, grupo, pasta=None, n=2):
        arquivo = (pasta or self.pasta) / f"{grupo}.json"
        arquivo.write_text(json.dumps(registros(grupo, n), ensure_ascii=False), encoding="utf-8")
        return arquivo


class TestGerar(Base):
    def test_gera_pdf_sem_ia_por_padrao(self):
        self.json("3A TESTE")
        with mock.patch.object(rc, "criar_ia") as criar:
            self.assertEqual(rc.gerar([self.pasta]), (1, 0, 0))
        criar.assert_not_called()
        self.assertTrue((self.pasta / "3A TESTE.pdf").exists())
        pdf = self.pdfs[0]
        self.assertEqual(pdf["caminho"], self.pasta / "3A TESTE.pdf")
        self.assertEqual(pdf["grupo"], "3A TESTE")
        self.assertEqual(len(pdf["linhas"]), 2)
        self.assertEqual(list(pdf["linhas"][0]), campos_relatorio.CHAVES)
        self.assertTrue(any("sem IA" in o for o in pdf["observacoes"]))
        self.assertTrue(pdf["observacoes"][0].startswith("Dados do sistema do escritório (VIOS) em"))

    def test_conta_os_encerrados_para_a_capa(self):
        regs = registros("COM ENCERRADOS", 3)
        regs[1]["situacao"] = "encerrado"
        regs[2]["situacao"] = "ativo"
        (self.pasta / "COM ENCERRADOS.json").write_text(json.dumps(regs, ensure_ascii=False), encoding="utf-8")
        self.json("SO ATIVOS")
        self.assertEqual(rc.gerar([self.pasta]), (2, 0, 0))
        por_grupo = {p["grupo"]: p for p in self.pdfs}
        self.assertEqual(por_grupo["COM ENCERRADOS"]["encerrados"], 1)
        self.assertEqual(por_grupo["SO ATIVOS"]["encerrados"], 0)
        self.assertIn("(encerrado)", por_grupo["COM ENCERRADOS"]["linhas"][1]["numero"])

    def test_aceita_arquivo_json_e_txt_do_grupo(self):
        arquivo = self.json("PAO TESTE")
        self.json("OUTRO")
        self.assertEqual(rc.gerar([arquivo]), (1, 0, 0))
        self.assertFalse((self.pasta / "OUTRO.pdf").exists())
        # o .txt do grupo aponta para o .json ao lado
        (self.pasta / "OUTRO.txt").write_text("txt", encoding="utf-8")
        self.assertEqual(rc.gerar([self.pasta / "OUTRO.txt"]), (1, 0, 0))

    def test_grupo_vazio_gera_pdf_com_aviso(self):
        (self.pasta / "VAZIO.json").write_text("[]", encoding="utf-8")
        self.assertEqual(rc.gerar([self.pasta]), (1, 0, 0))
        self.assertEqual(self.pdfs[0]["linhas"], [])
        self.assertIn("Nenhum processo encontrado para o grupo.", self.pdfs[0]["observacoes"])

    def test_json_invalido_e_falha_do_grupo(self):
        (self.pasta / "A.json").write_text("{quebrado", encoding="utf-8")
        (self.pasta / "B.json").write_text('{"x": 1}', encoding="utf-8")
        self.json("C")
        self.assertEqual(rc.gerar([self.pasta]), (1, 0, 2))
        self.assertTrue((self.pasta / "C.pdf").exists())

    def test_nao_regrava_pdf_mais_novo_sem_refazer(self):
        self.json("A")
        rc.gerar([self.pasta])
        self.assertEqual(rc.gerar([self.pasta]), (0, 1, 0))
        self.assertEqual(len(self.pdfs), 1)
        self.assertEqual(rc.gerar([self.pasta], refazer=True), (1, 0, 0))
        self.assertEqual(len(self.pdfs), 2)

    def test_json_mais_novo_gera_de_novo(self):
        arquivo = self.json("A")
        rc.gerar([self.pasta])
        antigo = time.time() - 3600
        os.utime(rc.nome_relatorio(arquivo), (antigo, antigo))
        self.assertEqual(rc.gerar([self.pasta]), (1, 0, 0))

    def test_ia_ligada_pelo_argumento(self):
        self.json("A", n=3)
        falsa = IAFalsa()
        self.assertEqual(rc.gerar([self.pasta], usar_ia=True, cliente=falsa, gasto=custo.Gasto()), (1, 0, 0))
        self.assertEqual(len(falsa.chamadas), 1)
        self.assertEqual(falsa.chamadas[0]["sistema"], campos_relatorio.PROMPT_IA)
        self.assertNotIn("INTERNO", falsa.chamadas[0]["usuario"])
        self.assertTrue(all(l["resumo"] == "Resumo da IA" for l in self.pdfs[0]["linhas"]))

    def test_ia_ligada_pelo_env(self):
        self.json("A")
        falsa = IAFalsa()
        with mock.patch.dict(os.environ, {"RELATORIO_IA": "true"}):
            rc.gerar([self.pasta], cliente=falsa, gasto=custo.Gasto())
        self.assertEqual(len(falsa.chamadas), 1)
        # --ia ausente e RELATORIO_IA=false: não chama
        falsa2 = IAFalsa()
        with mock.patch.dict(os.environ, {"RELATORIO_IA": "false"}):
            rc.gerar([self.pasta], refazer=True, cliente=falsa2)
        self.assertEqual(falsa2.chamadas, [])

    def test_ia_falhando_gera_pdf_sem_ia(self):
        self.json("A")
        falsa = IAFalsa(erro=RuntimeError("erro de teste"))
        self.assertEqual(rc.gerar([self.pasta], usar_ia=True, cliente=falsa, gasto=custo.Gasto()), (1, 0, 0))
        obs = self.pdfs[0]["observacoes"]
        self.assertTrue(any("montados só com o cadastro" in o for o in obs))
        # o erro técnico fica no log, não no PDF do cliente
        self.assertFalse(any("erro de teste" in o or "RuntimeError" in o for o in obs))
        self.assertTrue(self.pdfs[0]["linhas"][0]["resumo"].startswith("Ação Indenização"))

    def test_chave_recusada_desliga_a_ia_nos_grupos_seguintes(self):
        for g in ("A", "B"):
            self.json(g)
        falsa = IAFalsa(erro=AuthenticationError("401"))
        self.assertEqual(rc.gerar([self.pasta], usar_ia=True, cliente=falsa, gasto=custo.Gasto()), (2, 0, 0))
        self.assertEqual(len(falsa.chamadas), 1)
        obs_a, obs_b = self.pdfs[0]["observacoes"], self.pdfs[1]["observacoes"]
        self.assertTrue(any("montados só com o cadastro" in o for o in obs_a))
        self.assertIn(campos_relatorio.AVISO_SEM_IA, obs_b)
        # nada de chave, provedor ou código de erro no PDF
        for o in obs_a + obs_b:
            for proibido in ("OPENAI_API_KEY", "Chave da API", "401", "AuthenticationError", "créditos"):
                self.assertNotIn(proibido, o)

    def test_teto_de_gasto_nao_chama_a_ia(self):
        self.json("A")
        falsa = IAFalsa()
        self.assertEqual(rc.gerar([self.pasta], usar_ia=True, cliente=falsa, gasto=custo.Gasto(limite=0.000001)),
                         (1, 0, 0))
        self.assertEqual(falsa.chamadas, [])
        obs = self.pdfs[0]["observacoes"]
        self.assertTrue(any("montados só com o cadastro" in o for o in obs))
        self.assertFalse(any("Teto" in o or "LLM_LIMITE_US" in o or "US$" in o for o in obs))

    def test_sem_chave_para_antes_de_chamar(self):
        self.json("A")
        with mock.patch("bot.ia.criar") as criar:
            with self.assertRaises(rc.ErroFatal) as ctx:
                rc.gerar([self.pasta], usar_ia=True, gasto=custo.Gasto())
        criar.assert_not_called()
        self.assertIn("OPENAI_API_KEY vazia", str(ctx.exception))
        self.assertEqual(self.pdfs, [])

    def test_nao_cria_ia_se_tudo_em_dia(self):
        self.json("A")
        rc.gerar([self.pasta])
        with mock.patch.object(rc, "criar_ia") as criar:
            self.assertEqual(rc.gerar([self.pasta], usar_ia=True, gasto=custo.Gasto()), (0, 1, 0))
        criar.assert_not_called()

    def test_cria_ia_pelo_env(self):
        self.json("A")
        falsa = IAFalsa()
        with mock.patch.dict(os.environ, {"LLM_PROVEDOR": "anthropic", "LLM_MODELO": "",
                                          "ANTHROPIC_API_KEY": "chave-falsa"}), \
                mock.patch("bot.ia.criar", return_value=falsa) as criar:
            self.assertEqual(rc.gerar([self.pasta], usar_ia=True, gasto=custo.Gasto()), (1, 0, 0))
        criar.assert_called_once_with("anthropic", "claude-opus-5-5", "low")
        self.assertEqual(len(falsa.chamadas), 1)

    def test_prompt_de_arquivo(self):
        self.json("A")
        prompt = self.pasta / "prompt.md"
        prompt.write_text("PROMPT DE TESTE", encoding="utf-8")
        falsa = IAFalsa()
        with mock.patch.dict(os.environ, {"RELATORIO_CLIENTE_PROMPT": str(prompt)}):
            rc.gerar([self.pasta], usar_ia=True, cliente=falsa, gasto=custo.Gasto())
        self.assertEqual(falsa.chamadas[0]["sistema"], "PROMPT DE TESTE")

    def test_prompt_de_arquivo_inexistente_para(self):
        with mock.patch.dict(os.environ, {"RELATORIO_CLIENTE_PROMPT": str(self.pasta / "nao_existe.md")}):
            with self.assertRaises(rc.ErroFatal):
                rc.gerar([self.pasta], usar_ia=True, cliente=IAFalsa(), gasto=custo.Gasto())
            # sem IA o prompt nem é lido
            self.assertEqual(rc.gerar([self.pasta]), (0, 0, 0))


class TestArquivos(Base):
    def test_nome_seguro_no_windows(self):
        pasta = Path("x")
        self.assertEqual(rc.nome_relatorio(pasta / "3A TESTE.json").name, "3A TESTE.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / 'A:B*C?"D<E>F|G.json').name, "A-B-C--D-E-F-G.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "CON.json").name, "CON_.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "CON.X.json").name, "CON_.X.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "lpt1 .ABC.json").name, "lpt1_.ABC.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "CONSTRUTORA.A.json").name, "CONSTRUTORA.A.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "GRUPO S.A..json").name, "GRUPO S.A.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "PÃO TESTE.json").name, "PÃO TESTE.pdf")
        self.assertEqual(rc.nome_relatorio(pasta / "A.json").parent, pasta)

    def test_pasta_padrao_pega_o_dia_mais_recente(self):
        raiz = self.pasta / "relatorios"
        for nome in ("2026-10-28", "2026-11-02", "2026-10-30", "outra"):
            (raiz / nome).mkdir(parents=True)
        with mock.patch.dict(os.environ, {"RELATORIO_PASTA": str(raiz)}):
            self.assertEqual(rc.pasta_padrao(), raiz / "2026-11-02")
        with mock.patch.dict(os.environ, {"SAIDA_PASTA": str(self.pasta)}):
            self.assertEqual(rc.pasta_padrao(), raiz / "2026-11-02")
        with mock.patch.dict(os.environ, {"RELATORIO_PASTA": str(self.pasta / "vazia")}):
            self.assertIsNone(rc.pasta_padrao())

    def test_pasta_padrao_aceita_til_variavel_e_aspas(self):
        # mesmo jeito do relatorio_processos.pasta_relatorios
        dia = self.pasta / "Drive" / "Rel" / "2026-11-03"
        dia.mkdir(parents=True)
        casa = {"HOME": str(self.pasta), "USERPROFILE": str(self.pasta)}
        for valor in ("~/Drive/Rel", "$HOME/Drive/Rel", '"~/Drive/Rel"', " '$HOME/Drive/Rel' "):
            with mock.patch.dict(os.environ, dict(casa, RELATORIO_PASTA=valor)):
                self.assertEqual(rc.pasta_padrao(), dia, valor)

    def test_prompt_com_til(self):
        (self.pasta / "prompt.md").write_text("PROMPT DO TIL", encoding="utf-8")
        with mock.patch.dict(os.environ, {"HOME": str(self.pasta), "USERPROFILE": str(self.pasta),
                                          "RELATORIO_CLIENTE_PROMPT": '"~/prompt.md"'}):
            self.assertEqual(rc.carregar_prompt(), "PROMPT DO TIL")

    def test_ia_ligada(self):
        self.assertFalse(rc.ia_ligada())
        self.assertTrue(rc.ia_ligada(True))
        for valor, esperado in (("true", True), ("SIM", True), ("1", True), ("false", False), ("", False)):
            with mock.patch.dict(os.environ, {"RELATORIO_IA": valor}):
                self.assertEqual(rc.ia_ligada(), esperado, valor)


class TestEntrada(Base):
    def setUp(self):
        super().setUp()
        log = mock.patch.object(entrada, "configurar_log")  # não escreve no logs/bot.log real
        log.start()
        self.addCleanup(log.stop)
        self.env = self.pasta / ".env.teste"
        self.env.write_text("LLM_PROVEDOR=openai\nLLM_MODELO=gpt-5.6\n", encoding="utf-8")

    def test_cli_gera_o_pdf(self):
        arquivo = self.json("A")
        with mock.patch.object(rc, "criar_ia") as criar:
            self.assertEqual(entrada.main(str(self.env), str(arquivo)), 0)
        criar.assert_not_called()
        self.assertTrue((self.pasta / "A.pdf").exists())
        self.assertEqual(self.pdfs[0]["grupo"], "A")

    def test_sem_caminho_usa_a_pasta_mais_recente(self):
        raiz = self.pasta / "relatorios"
        velha, nova = raiz / "2026-10-28", raiz / "2026-11-02"
        velha.mkdir(parents=True)
        nova.mkdir(parents=True)
        self.json("A", velha)
        self.json("B", nova)
        with mock.patch.dict(os.environ, {"RELATORIO_PASTA": str(raiz)}):
            self.assertEqual(entrada.main(str(self.env)), 0)
        self.assertTrue((nova / "B.pdf").exists())
        self.assertFalse((velha / "A.pdf").exists())

    def test_refazer_pela_linha_de_comando(self):
        arquivo = self.json("A")
        self.assertEqual(entrada.main(str(self.env), str(arquivo)), 0)
        self.assertEqual(entrada.main(str(self.env), str(arquivo)), 0)
        self.assertEqual(len(self.pdfs), 1)
        self.assertEqual(entrada.main(str(self.env), str(self.pasta), "--refazer"), 0)
        self.assertEqual(len(self.pdfs), 2)

    def test_ia_pela_linha_de_comando(self):
        self.json("A")
        falsa = IAFalsa()
        with mock.patch.object(rc, "criar_ia", return_value=falsa):
            self.assertEqual(entrada.main(str(self.env), str(self.pasta), "--ia"), 0)
        self.assertEqual(len(falsa.chamadas), 1)

    def test_ia_sem_chave_devolve_1(self):
        self.json("A")
        # o .env.teste não tem chave: para sem chamar a IA nem gerar PDF
        self.assertEqual(entrada.main(str(self.env), str(self.pasta), "--ia"), 1)
        self.assertEqual(self.pdfs, [])

    def test_falha_de_grupo_devolve_1(self):
        (self.pasta / "A.json").write_text("{quebrado", encoding="utf-8")
        self.assertEqual(entrada.main(str(self.env), str(self.pasta)), 1)

    def test_env_inexistente_devolve_1(self):
        self.assertEqual(entrada.main(str(self.pasta / "nao_existe.env"), str(self.pasta)), 1)

    def test_sem_caminho_e_til_no_env(self):
        dia = self.pasta / "Drive" / "2026-11-03"
        dia.mkdir(parents=True)
        self.json("A", dia)
        self.env.write_text("LLM_PROVEDOR=openai\nRELATORIO_PASTA=~/Drive\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"HOME": str(self.pasta), "USERPROFILE": str(self.pasta)}):
            self.assertEqual(entrada.main(str(self.env)), 0)
        self.assertTrue((dia / "A.pdf").exists())

    def test_json_inexistente_devolve_1(self):
        with self.assertLogs("relatorio_cliente", "ERROR") as logs:
            logging.disable(logging.NOTSET)
            self.assertEqual(entrada.main(str(self.env), str(self.pasta / "nao_existe.json")), 1)
        self.assertIn("Não encontrado", "\n".join(logs.output))
        self.assertEqual(self.pdfs, [])

    def test_pasta_inexistente_diz_que_nao_existe(self):
        pasta = str(self.pasta / "2026-11-99")
        for args in ((str(self.env), pasta), (pasta,)):
            with self.assertLogs("relatorio_cliente", "ERROR") as logs:
                logging.disable(logging.NOTSET)
                self.assertEqual(entrada.main(*args), 1)
            texto = "\n".join(logs.output)
            self.assertIn("Não encontrado (esperado um .json, um .txt ou uma pasta)", texto)
            self.assertNotIn("configuração", texto)

    def test_pasta_sem_json_devolve_1(self):
        vazia = self.pasta / "vazia"
        vazia.mkdir()
        (vazia / "A.txt").write_text("só o txt", encoding="utf-8")
        self.assertEqual(entrada.main(str(self.env), str(vazia)), 1)
        self.assertEqual(self.pdfs, [])


if __name__ == "__main__":
    unittest.main()
