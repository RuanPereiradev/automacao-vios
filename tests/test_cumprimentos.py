"""Aba Cumprimentos de sentença: leitura do banco do vigia (pje-busca), conferência da equipe e rotas do Flask.
Dados fictícios (números de processo e empresas inventados)."""
import base64
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import cumprimentos as C  # noqa: E402

ESQUEMA = """
CREATE TABLE empresas (chave TEXT PRIMARY KEY, nome TEXT, cnpj TEXT, cnpj_situacao TEXT, primeira_vez TEXT, ultima_vez TEXT);
CREATE TABLE processos (chave TEXT PRIMARY KEY, numero TEXT, ci TEXT, empresa TEXT, tribunal TEXT, orgao TEXT, advogado TEXT,
  auxiliares TEXT, autor TEXT, primeira_vez TEXT, ultima_vez TEXT, ativo INTEGER);
CREATE TABLE djen_processos (numero TEXT PRIMARY KEY, empresa TEXT, classe TEXT, orgao TEXT, primeira_publicacao TEXT,
  tipo TEXT, visto_em TEXT, nivel TEXT);
CREATE TABLE djen_rodadas (data TEXT PRIMARY KEY, empresas INTEGER, publicacoes INTEGER, vermelhos INTEGER,
  amarelos INTEGER, sem_publicacao INTEGER, erros INTEGER, base INTEGER);
"""
A = "0000001-11.2026.5.07.0038"  # cumprimento provisório recente
B = "0000002-22.2024.5.07.0024"  # cumprimento provisório antigo
S = "0000003-33.2025.5.07.0029"  # ação de cumprimento (sindicato)
O = "0000004-44.2026.5.07.0024"  # ação trabalhista comum


def montar(pasta):
    (pasta / "dados").mkdir()
    (pasta / "saida").mkdir()
    (pasta / "vigia.py").write_text("print('vigia')\n", encoding="utf-8")
    db = sqlite3.connect(pasta / "dados" / "vigia.sqlite")
    db.executescript(ESQUEMA)
    db.executemany("INSERT INTO empresas VALUES (?, ?, ?, '', '', '')", [
        ("EMPRESA X", "EMPRESA X", ""), ("EMPRESA Y", "EMPRESA Y", ""),
        ("SEM NOME LTDA (MATRIZ)", "SEM NOME LTDA (MATRIZ)", "12345678000190"), ("QUIETA LTDA", "QUIETA LTDA", "")])
    db.execute("INSERT INTO processos VALUES ('k', 'n', '1', 'EMPRESA X', '5.07', '', '', '', '', '', '', 1)")
    db.execute("INSERT INTO processos VALUES ('k2', 'n2', '2', 'SEM NOME LTDA (MATRIZ)', '5.07', '', '', '', '', '', '', 1)")
    db.executemany("INSERT INTO djen_processos VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        (A, "EMPRESA X", "CUMPRIMENTO PROVISóRIO DE SENTENçA", "2ª Vara do Trabalho de Sobral", "2026-11-20",
         "Lista de distribuição", "2026-11-24", "VERMELHO"),
        (B, "EMPRESA Y", "CUMPRIMENTO PROVISóRIO DE SENTENçA", "1ª Vara do Trabalho de Sobral", "2024-12-12",
         "Intimação", "2026-11-24", "VERMELHO"),
        (S, "EMPRESA X", "AçãO DE CUMPRIMENTO", "Única Vara do Trabalho de Tianguá", "2025-04-22",
         "Lista de distribuição", "2026-11-24", "AMARELO"),
        (O, "EMPRESA Y", "AçãO TRABALHISTA - RITO ORDINáRIO", "1ª Vara do Trabalho de Sobral", "2026-11-06",
         "Lista de distribuição", "2026-11-24", "AMARELO")])
    db.execute("INSERT INTO djen_rodadas VALUES ('2026-11-24', 2, 50, 0, 0, 0, 0, 1)")
    db.commit()
    db.close()
    (pasta / "saida" / "djen_2026-11-24.txt").write_text(
        "VIGIA DJEN · 2026-11-24\n\nSem nenhuma publicação no DJEN com este nome (3) — conferir o nome:\n"
        "  - QUIETA LTDA\n  - SEM NOME LTDA\n  - FORA DA LISTA LTDA\n\nERROS (0)\n", encoding="utf-8")


class Painel(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pasta = Path(self._tmp.name)
        montar(self.pasta)

    def test_sem_vigia(self):
        vazia = self.pasta / "nada"
        vazia.mkdir()
        self.assertFalse(C.configurado(vazia))
        self.assertEqual(C.painel(vazia)["vermelhos"], [])
        self.assertFalse(C.resumo(vazia)["configurado"])

    def test_separa_cumprimentos_acoes_e_outros(self):
        p = C.painel(self.pasta, hoje=date(2026, 11, 24))
        self.assertEqual([i["numero"] for i in p["vermelhos"]], [A, B])  # o mais recente em cima
        self.assertEqual([i["numero"] for i in p["acoes"]], [S])
        self.assertEqual(p["outros"], 1)
        self.assertEqual((p["pendentes"], p["maior_espera"]), (2, (date(2026, 11, 24) - date(2024, 12, 12)).days))
        a = p["vermelhos"][0]
        self.assertEqual(a["classe"], "CUMPRIMENTO PROVISÓRIO DE SENTENÇA")
        self.assertEqual((a["primeira_br"], a["dias"], a["situacao"]), ("20/11/2026", 4, "pendente"))
        self.assertEqual((p["empresas"], p["processos_vios"]), (4, 2))
        self.assertEqual(p["rodada"]["data_br"], "24/11/2026")
        self.assertEqual(p["relatorios"], [{"data": "2026-11-24", "data_br": "24/11/2026", "tipo": "djen"}])

    def test_processo_principal(self):
        db = sqlite3.connect(self.pasta / "dados" / "vigia.sqlite")
        db.execute("CREATE TABLE djen_principais (numero TEXT PRIMARY KEY, principal TEXT, ci TEXT, empresa TEXT, "
                   "advogado TEXT, como TEXT, exequente TEXT, verificado_em TEXT)")
        db.execute("INSERT INTO djen_principais VALUES (?, '0000009-99.2025.5.07.0038', '123', 'EMPRESA X', 'ADV', "
                   "'mesmo exequente e mesma vara', 'FULANO', '2026-11-24')", (A,))
        db.execute("INSERT INTO djen_principais VALUES (?, NULL, '', '', '', 'nenhum processo do VIOS com o mesmo exequente', "
                   "'BELTRANO', '2026-11-24')", (B,))
        db.commit()
        db.close()
        v = {i["numero"]: i for i in C.painel(self.pasta)["vermelhos"]}
        self.assertEqual((v[A]["principal"], v[A]["principal_ci"]), ("0000009-99.2025.5.07.0038", "123"))
        self.assertEqual((v[B]["principal"], v[B]["principal_ci"], v[B]["principal_verificado"]), ("", "", True))

    def _associados(self):
        db = sqlite3.connect(self.pasta / "dados" / "vigia.sqlite")
        db.executescript("""
CREATE TABLE assoc_principais (numero TEXT PRIMARY KEY, situacao TEXT, qtd INTEGER, verificado_em TEXT,
  base_feita INTEGER, erro TEXT);
CREATE TABLE assoc_associados (principal TEXT, associado TEXT, orgao TEXT, visto_em TEXT, novo INTEGER, nivel TEXT,
  PRIMARY KEY (principal, associado));
CREATE TABLE assoc_rodadas (data TEXT PRIMARY KEY, acervo INTEGER, verificados INTEGER, com_associados INTEGER,
  fora_acervo INTEGER, erros INTEGER, novos INTEGER, vermelhos INTEGER, completa INTEGER, base INTEGER);""")
        db.execute("INSERT INTO assoc_principais VALUES ('n', 'ok', 2, '2026-11-25', 1, '')")
        db.execute("INSERT INTO assoc_principais VALUES ('x', 'fora_do_acervo', 0, '2026-11-25', 0, '')")
        db.executemany("INSERT INTO assoc_associados VALUES ('n', ?, '2ª Vara', ?, ?, ?)", [
            ("0000010-10.2026.5.07.0038", "2026-11-25", 1, "VERMELHO"),   # novo, fora do VIOS
            ("n2", "2026-11-25", 1, "INFO"),                                # novo, já no VIOS
            ("0000012-12.2026.5.07.0038", "2026-11-25", 1, "AMARELO"),     # novo, principal fora do VIOS
            ("0000011-11.2026.5.07.0038", "2026-11-24", 0, "BASE")])        # base: não aparece
        db.execute("INSERT INTO assoc_rodadas VALUES ('2026-11-25', 358, 1, 1, 1, 0, 2, 1, 1, 0)")
        db.commit()
        db.close()
        (self.pasta / "saida" / "associados_2026-11-25.txt").write_text("VIGIA · ASSOCIADOS\n", encoding="utf-8")

    def test_nivel3_associados_novos(self):
        self._associados()
        a = C.painel(self.pasta, hoje=date(2026, 11, 26))["assoc"]
        self.assertEqual([(i["numero"], i["vermelho"], i["amarelo"]) for i in a["alertas"]],
                         [("0000010-10.2026.5.07.0038", True, False), ("0000012-12.2026.5.07.0038", False, True),
                          ("n2", False, False)])
        self.assertEqual((a["pendentes"], a["principais"], a["fora_acervo"]), (1, 1, 1))
        self.assertEqual(a["alertas"][0]["principal_ci"], "1")          # o principal 'n' está no VIOS (CI 1)
        self.assertEqual(a["rodada"]["data_br"], "25/11/2026")
        self.assertEqual(C.resumo(self.pasta)["assoc_pendentes"], 1)
        C.conferir(self.pasta, "0000010-10.2026.5.07.0038", "habilitado", "Dra. Fulana")   # conferência vale para o associado
        self.assertEqual(C.painel(self.pasta)["assoc"]["pendentes"], 0)
        self.assertTrue(C.relatorio(self.pasta, "2026-11-25", "associados"))
        self.assertIsNone(C.relatorio(self.pasta, "2026-11-25", "../x"))

    def test_rodar_associados(self):
        with mock.patch.object(C.subprocess, "Popen") as popen, mock.patch.object(C.threading, "Thread"):
            popen.return_value.pid = 4243
            C.rodar(self.pasta, python="python3", comando="associados")
        self.assertEqual(popen.call_args[0][0], ["python3", "vigia.py", "associados"])
        self.assertEqual(json.loads((self.pasta / C.EXECUCAO).read_text())["comando"], "associados")
        with self.assertRaisesRegex(C.CumprimentosErro, "inválida"):
            C.rodar(self.pasta, comando="rm")

    def test_banco_so_leitura(self):
        db = C._conectar(self.pasta)
        with self.assertRaises(sqlite3.OperationalError):
            db.execute("DELETE FROM djen_processos")
        db.close()

    def test_conferir_grava_historico_e_tira_dos_pendentes(self):
        C.conferir(self.pasta, A, "providencia", "Dra. Fulana", "habilitação pedida", agora=datetime(2026, 11, 24, 9, 30))
        C.conferir(self.pasta, A, "habilitado", "Dra. Fulana", "", agora=datetime(2026, 11, 25, 8, 0))
        conf = C.conferencias(self.pasta)[A]
        self.assertEqual(conf["situacao"], "habilitado")
        self.assertEqual([h["situacao"] for h in conf["historico"]], ["providencia", "habilitado"])
        self.assertEqual(oct((self.pasta / C.CONFERENCIA).stat().st_mode & 0o777), "0o600")
        p = C.painel(self.pasta, hoje=date(2026, 11, 25))
        self.assertEqual([i["numero"] for i in p["vermelhos"]], [B, A])  # conferido vai para baixo
        self.assertEqual(p["pendentes"], 1)

    def test_conferir_recusa(self):
        for args, erro in (((A, "inventada", "x"), "situação"), (("123", "habilitado", "x"), "número"),
                           (("9999999-99.2026.5.07.0038", "habilitado", "x"), "fora da lista"),
                           ((A, "habilitado", ""), "quem")):
            with self.subTest(args=args):
                with self.assertRaisesRegex(C.CumprimentosErro, erro):
                    C.conferir(self.pasta, *args)

    def test_relatorio_so_da_pasta_saida(self):
        self.assertTrue(C.relatorio(self.pasta, "2026-11-24"))
        self.assertIsNone(C.relatorio(self.pasta, "2026-11-23"))
        self.assertIsNone(C.relatorio(self.pasta, "../../etc/passwd"))

    def test_rodar_sem_vigia_recusa(self):
        vazia = self.pasta / "nada"
        vazia.mkdir()
        with self.assertRaisesRegex(C.CumprimentosErro, "não está instalado"):
            C.rodar(vazia)

    def test_rodar_ambiente_limpo(self):
        with mock.patch.dict(os.environ, {"ENVIO_SENHA": "segredo", "ANTHROPIC_API_KEY": "chave"}), \
                mock.patch.object(C.subprocess, "Popen") as popen, mock.patch.object(C.threading, "Thread"):
            popen.return_value.pid = 4242
            C.rodar(self.pasta, python="python3")
        args, kw = popen.call_args
        self.assertEqual(args[0], ["python3", "vigia.py", "djen"])
        self.assertNotIn("ENVIO_SENHA", kw["env"])
        self.assertNotIn("ANTHROPIC_API_KEY", kw["env"])
        self.assertEqual(json.loads((self.pasta / C.EXECUCAO).read_text())["pid"], 4242)

    def test_sem_publicacao_pelo_relatorio(self):
        p = C.painel(self.pasta)
        sem = p["sem_publicacao"]
        self.assertEqual([e["empresa"] for e in sem], ["SEM NOME LTDA (MATRIZ)", "QUIETA LTDA"])  # com processo no TRT7 primeiro
        self.assertEqual((sem[0]["processos_trt7"], sem[0]["cnpj"]), (1, "12.345.678/0001-90"))
        self.assertEqual(p["sem_pub_pendentes"], 2)

    def test_sem_publicacao_pela_tabela_da_rodada(self):
        db = sqlite3.connect(self.pasta / "dados" / "vigia.sqlite")
        db.execute("CREATE TABLE djen_consultas (empresa TEXT PRIMARY KEY, data TEXT, publicacoes INTEGER, nomes TEXT)")
        db.executemany("INSERT INTO djen_consultas VALUES (?, '2026-11-25', ?, ?)", [
            ("QUIETA LTDA", 0, '["QUIETA LTDA", "QUIETA COMERCIO LTDA"]'), ("EMPRESA X", 7, '["EMPRESA X"]')])
        db.commit()
        db.close()
        sem = C.painel(self.pasta)["sem_publicacao"]
        self.assertEqual([(e["empresa"], e["buscados"], e["data_br"]) for e in sem],
                         [("QUIETA LTDA", ["QUIETA LTDA", "QUIETA COMERCIO LTDA"], "25/11/2026")])

    def test_conferir_nome(self):
        empresa = "SEM NOME LTDA (MATRIZ)"
        C.conferir_nome(self.pasta, empresa, "nome_corrigido", "Dra. Fulana", "visto no PJe",
                        " sem nome comercio   eireli ; SEM NOME LTDA - EPP")
        dados = json.loads((self.pasta / C.NOMES).read_text(encoding="utf-8"))
        self.assertEqual(dados[empresa]["nomes"], ["SEM NOME COMERCIO EIRELI", "SEM NOME LTDA - EPP"])
        self.assertEqual(oct((self.pasta / C.NOMES).stat().st_mode & 0o777), "0o600")
        sem = C.painel(self.pasta)["sem_publicacao"]
        self.assertEqual([e["empresa"] for e in sem], ["QUIETA LTDA", empresa])  # conferida vai para baixo
        self.assertEqual(sem[1]["nomes_informados"], "SEM NOME COMERCIO EIRELI; SEM NOME LTDA - EPP")
        C.conferir_nome(self.pasta, empresa, "nome_certo", "Dra. Fulana")
        dados = json.loads((self.pasta / C.NOMES).read_text(encoding="utf-8"))
        self.assertEqual((dados[empresa]["nomes"], len(dados[empresa]["historico"])), ([], 2))

    def test_conferir_nome_recusa(self):
        for args, erro in ((("QUIETA LTDA", "x", "a"), "situação"), (("NAO EXISTE", "nome_certo", "a"), "fora da lista"),
                           (("QUIETA LTDA", "nome_corrigido", "a", "", ""), "nome da empresa"),
                           (("QUIETA LTDA", "nome_corrigido", "a", "", "AB"), "3 a 120"),
                           (("QUIETA LTDA", "nome_corrigido", "a", "", "AAA;BBB;CCC;DDD"), "até 3"),
                           (("QUIETA LTDA", "nome_certo", ""), "quem")):
            with self.subTest(args=args):
                with self.assertRaisesRegex(C.CumprimentosErro, erro):
                    C.conferir_nome(self.pasta, *args)


class Rotas(unittest.TestCase):
    def setUp(self):
        try:
            from bot import envio_web
        except ImportError as e:  # Flask/Selenium fora deste Python
            self.skipTest(str(e))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        raiz = Path(self._tmp.name)
        self.pasta = raiz / "pje-busca"
        self.pasta.mkdir()
        montar(self.pasta)
        env = raiz / ".env"
        env.write_text("SISTEMA_URL=https://vios.exemplo/\nSISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n"
                       "LOGIN_CAMPO_USUARIO=css:#u\nLOGIN_CAMPO_SENHA=css:#s\n"
                       f"SAIDA_PASTA={raiz / 'saida'}\n", encoding="utf-8")
        ambiente = mock.patch.dict(os.environ, {"PJE_BUSCA_PASTA": str(self.pasta)})
        ambiente.start()
        self.addCleanup(ambiente.stop)
        self.app = envio_web.criar_app(str(env), senha="senha-da-vila").test_client()
        self.auth = {"Authorization": "Basic " + base64.b64encode(b"x:senha-da-vila").decode()}

    def test_pede_senha(self):
        self.assertEqual(self.app.get("/cumprimentos").status_code, 401)

    def test_pagina_e_cartao_da_vila(self):
        r = self.app.get("/cumprimentos", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertIn(A.encode(), r.data)
        self.assertIn(S.encode(), r.data)
        self.assertNotIn(O.encode(), r.data)
        r = self.app.get("/", headers=self.auth)
        self.assertIn("Abrir Cumprimentos".encode(), r.data)
        self.assertIn("2 pendente(s)".encode(), r.data)

    def test_conferir_pela_pagina(self):
        r = self.app.post("/cumprimentos/conferir", headers=self.auth,
                          json={"numero": A, "situacao": "habilitado", "quem": "Dr. Beltrano", "obs": "ok"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(C.conferencias(self.pasta)[A]["quem"], "Dr. Beltrano")
        r = self.app.post("/cumprimentos/conferir", headers=self.auth, json={"numero": A, "situacao": "x"})
        self.assertEqual(r.status_code, 400)
        # sem JSON (formulário de outro site) é recusado
        r = self.app.post("/cumprimentos/conferir", headers=self.auth, data={"numero": A})
        self.assertEqual(r.status_code, 403)

    def test_pagina_mostra_principal(self):
        db = sqlite3.connect(self.pasta / "dados" / "vigia.sqlite")
        db.execute("CREATE TABLE djen_principais (numero TEXT PRIMARY KEY, principal TEXT, ci TEXT, empresa TEXT, "
                   "advogado TEXT, como TEXT, exequente TEXT, verificado_em TEXT)")
        db.execute("INSERT INTO djen_principais VALUES (?, '0000009-99.2025.5.07.0038', '123', 'EMPRESA X', 'ADV', "
                   "'citado na publicação', 'FULANO', '2026-11-24')", (A,))
        db.commit()
        db.close()
        r = self.app.get("/cumprimentos", headers=self.auth)
        self.assertIn("Cliente nosso:".encode(), r.data)
        self.assertIn(b"0000009-99.2025.5.07.0038", r.data)
        self.assertIn("ainda não verificado".encode(), r.data)   # o B ainda não tem linha

    def test_conferir_nome_pela_pagina(self):
        r = self.app.get("/cumprimentos", headers=self.auth)
        self.assertIn(b"Empresas sem nenhuma publica", r.data)
        self.assertIn(b"SEM NOME LTDA (MATRIZ)", r.data)
        r = self.app.post("/cumprimentos/nome", headers=self.auth, json={"empresa": "QUIETA LTDA", "situacao": "nome_corrigido",
                                                                        "nomes": "QUIETA COMERCIO LTDA", "quem": "Dr. B"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(C.nomes_conferidos(self.pasta)["QUIETA LTDA"]["nomes"], ["QUIETA COMERCIO LTDA"])
        r = self.app.post("/cumprimentos/nome", headers=self.auth, json={"empresa": "QUIETA LTDA", "situacao": "nome_corrigido"})
        self.assertEqual(r.status_code, 400)

    def test_relatorio(self):
        r = self.app.get("/cumprimentos/relatorio/2026-11-24", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        r.close()
        self.assertEqual(self.app.get("/cumprimentos/relatorio/..%2F.env", headers=self.auth).status_code, 404)


if __name__ == "__main__":
    unittest.main()
