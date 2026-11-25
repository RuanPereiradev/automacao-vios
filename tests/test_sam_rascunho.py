"""Sam: tarefas previdenciárias renomeadas no VIOS (25/11/2026) e o envio como rascunho (recarregar a página
confere de novo; a edição é guardada sozinha)."""
import base64
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LAUDO = "MINUTAR IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026"
REPLICA = "MINUTAR RÉPLICA/ PETIÇÃO INTERMEDIÁRIA (PREVIDENCIÁRIO)"
TXT = """CI: 43223
PROCESSO: 0027653-28.2026.4.05.8100
TAREFA: {nome}
DATA: 14/12/2026
HORA:
RESPONSÁVEIS: SUHIANE DE MARIA GOMES SILVA
DESCRIÇÃO:
PRAZO FATAL D -2: 14/12/2026
MINUTAR MANIFESTAÇÃO SOBRE O LAUDO PERICIAL
"""


def _modulos():
    try:
        from bot import envio_txt, skill
        from bot.lancamento import achar_opcao
    except ImportError as e:  # Selenium fora deste Python
        raise unittest.SkipTest(str(e))
    return envio_txt, skill, achar_opcao


class Tarefas(unittest.TestCase):
    def test_nomes_novos_do_vios(self):
        envio_txt, skill, _ = _modulos()
        oficiais = skill.tarefas_oficiais("doc/analise-intimacoes-controladoria")
        self.assertIn(LAUDO, oficiais)
        self.assertIn(REPLICA, oficiais)
        for nome in (LAUDO, REPLICA, "MINUTAR RÉPLICA/PETIÇÃO INTERMEDIÁRIA (PREVIDENCIÁRIO)"):
            with self.subTest(nome=nome):
                c = envio_txt.ler(TXT.format(nome=nome), oficiais, hoje=date(2026, 11, 25))[0]
                self.assertEqual(c["problemas"], [])

    def test_nomes_antigos_continuam_e_vao_para_os_novos(self):
        envio_txt, skill, achar_opcao = _modulos()
        oficiais = skill.tarefas_oficiais("doc/analise-intimacoes-controladoria")
        opcoes = {LAUDO: "1", REPLICA: "2"}
        self.assertEqual(achar_opcao("MINUTAR RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026", opcoes), "1")
        self.assertEqual(achar_opcao("MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026", opcoes), "1")
        self.assertEqual(achar_opcao("MINUTAR PETIÇÃO INTERMEDIÁRIA (PREVIDENCIÁRIO)", opcoes), "2")
        c = envio_txt.ler(TXT.format(nome="MINUTAR RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026"), oficiais,
                          hoje=date(2026, 11, 25))[0]
        self.assertEqual(c["problemas"], [])


class Rascunho(unittest.TestCase):
    def setUp(self):
        try:
            from bot import envio_web
        except ImportError as e:  # Flask/Selenium fora deste Python
            self.skipTest(str(e))
        self.envio_web = envio_web
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        raiz = Path(self._tmp.name)
        self.saida = raiz / "saida"
        env = raiz / ".env"
        env.write_text("SISTEMA_URL=https://vios.exemplo/\nSISTEMA_USUARIO=u\nSISTEMA_SENHA=s\n"
                       "LOGIN_CAMPO_USUARIO=css:#u\nLOGIN_CAMPO_SENHA=css:#s\n"
                       f"SAIDA_PASTA={self.saida}\n", encoding="utf-8")
        self.env = str(env)
        self.auth = {"Authorization": "Basic " + base64.b64encode(b"x:s").decode()}

    def _app(self):
        return self.envio_web.criar_app(self.env, senha="s").test_client()

    def test_recarregar_confere_de_novo_sem_subir_o_txt(self):
        # envio gravado antes da atualização, com a tarefa marcada como fora da lista
        envio = {"arquivo": "a.txt", "estado": "conferir", "criado": datetime(2026, 11, 25, 14), "confirmar": False,
                 "cis": [{"ci": "43223", "processo": "0027653-28.2026.4.05.8100", "link_lancar": "", "ja_lancada": False,
                          "problemas": [f"Tarefa fora da lista oficial do VIOS: '{LAUDO}'."], "avisos": [],
                          "tarefas": [{"nome": LAUDO, "tipo_data": "DATA_INFORMADA", "data_tarefa": "14/12/2026",
                                       "hora": "", "responsaveis": ["SUHIANE DE MARIA GOMES SILVA"],
                                       "descricao": "PRAZO FATAL D -2: 14/12/2026\nMINUTAR MANIFESTAÇÃO"}]}]}
        self.envio_web.salvar_envio(self.saida, "e1", envio)
        app = self._app()
        r = app.get("/envio/e1", headers=self.auth)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("fora da lista oficial".encode(), r.data)
        gravado = json.loads((self.saida / "envios" / "e1.json").read_text(encoding="utf-8"))
        self.assertEqual(gravado["cis"][0]["problemas"], [])

    def test_rascunho_guarda_a_edicao(self):
        app = self._app()
        r = app.post("/ler", headers=self.auth, data={"arquivo": (__import__("io").BytesIO(
            TXT.format(nome="TAREFA QUE NAO EXISTE").encode()), "a.txt")}, content_type="multipart/form-data")
        envio_id = r.headers["Location"].rsplit("/", 1)[-1]
        campos = {"g0_ci": "43223", "g0_processo": "0027653-28.2026.4.05.8100", "g0_t0_nome": LAUDO,
                  "g0_t0_data": "14/12/2026", "g0_t0_hora": "", "g0_t0_responsaveis": "SUHIANE DE MARIA GOMES SILVA",
                  "g0_t0_descricao": "PRAZO FATAL D -2: 14/12/2026\nMINUTAR MANIFESTAÇÃO"}
        r = app.post(f"/envio/{envio_id}/rascunho", headers=self.auth, data=campos)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["problemas"], 0)
        # o servidor reinicia (atualização): recarregar a página mostra o rascunho, sem subir o .txt
        r = self._app().get(f"/envio/{envio_id}", headers=self.auth)
        self.assertIn(LAUDO.encode(), r.data)
        self.assertNotIn(b"TAREFA QUE NAO EXISTE", r.data)


if __name__ == "__main__":
    unittest.main()
