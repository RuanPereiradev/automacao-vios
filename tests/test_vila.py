"""Testes dos eventos para a vila (bot/vila.py). Não acessam o VIOS nem a rede: o servidor do
Ultron é trocado por um servidor HTTP falso local (http.server numa thread) e as telas do VIOS
por dublês, como em test_somente_leitura.py.

DADOS FICTÍCIOS: títulos de tarefa, links e o PDF (de test_regras.py) foram escritos para o teste.
"""
import base64
from contextlib import ExitStack
import json
import os
import re
import tempfile
import threading
import time
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import main
from bot import calendario, classificacao, comprovante, edicao, processo, vila

try:
    from test_regras import PDF as PDF_FICTICIO
except ImportError:
    from tests.test_regras import PDF as PDF_FICTICIO

SENHA = "senha-de-teste-123"
CNJ_FORMATO = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
VALORES_FICTICIOS = comprovante.extrair(PDF_FICTICIO)


class ServidorFalso:
    """Servidor do Ultron de mentira: guarda o que recebe e responde `status` (ou demora `atraso` s)."""

    def __init__(self, status=200, atraso=0):
        self.status, self.atraso, self.recebidos = status, atraso, []
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                corpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                dono.recebidos.append({"caminho": self.path, "auth": self.headers.get("Authorization"),
                                       "tipo": self.headers.get("Content-Type"), "corpo": json.loads(corpo)})
                if dono.atraso:
                    time.sleep(dono.atraso)
                try:
                    self.send_response(dono.status)
                    self.end_headers()
                    self.wfile.write(b"{}")
                except OSError:
                    pass

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/eventos"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def eventos(self):
        return [r["corpo"] for r in self.recebidos]

    def fechar(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class EnvioTest(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)

    def servidor(self, **kw):
        s = ServidorFalso(**kw)
        self.addCleanup(s.fechar)
        return s

    def vila(self, url, timeout=0.5):
        return vila.Vila(url, SENHA, "zangao", self.pasta.name, timeout, envio="2026-11-03_101500_ab12")

    def pendentes(self):
        arquivo = Path(self.pasta.name) / vila.PENDENTES
        return [json.loads(l) for l in arquivo.read_text(encoding="utf-8").splitlines()] if arquivo.exists() else []

    def test_200_corpo_e_autenticacao(self):
        s = self.servidor()
        v = self.vila(s.url)
        v.emitir("fase", fase="entrando_vios")
        r = s.recebidos[0]
        self.assertEqual(r["caminho"], "/eventos")
        self.assertTrue(r["tipo"].startswith("application/json"))
        self.assertEqual(r["auth"], "Basic " + base64.b64encode(f"zangao:{SENHA}".encode()).decode())
        e = r["corpo"]
        self.assertEqual((e["bot"], e["envio"], e["tipo"], e["fase"]), ("zangao", "2026-11-03_101500_ab12", "fase", "entrando_vios"))
        self.assertRegex(e["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
        self.assertEqual(self.pendentes(), [])

    def _falha(self, s, timeout=0.5):
        """O bot continua, para de tentar depois de 3 falhas, avisa uma vez e guarda os pendentes."""
        v = self.vila(s.url if isinstance(s, ServidorFalso) else s, timeout)
        with self.assertLogs("bot.vila", "WARNING") as logs:
            for i in range(6):
                self.assertIsNotNone(v.emitir("fase", fase=f"f{i}"))  # nunca levanta exceção
        if isinstance(s, ServidorFalso):
            self.assertEqual(len(s.recebidos), 3)  # depois de 3 falhas não tenta mais
        self.assertTrue(v.desistiu)
        self.assertEqual(sum("não tento mais" in l for l in logs.output), 1)
        self.assertTrue(all("\n" not in l.split(":", 2)[-1] for l in logs.output))  # uma linha só
        self.assertFalse(any(SENHA in l for l in logs.output))
        self.assertEqual([e["fase"] for e in self.pendentes()], [f"f{i}" for i in range(6)])
        return logs.output

    def test_401(self):
        self.assertTrue(any("HTTP 401" in l for l in self._falha(self.servidor(status=401))))

    def test_500(self):
        self.assertTrue(any("HTTP 500" in l for l in self._falha(self.servidor(status=500))))

    def test_demora_mais_que_o_timeout(self):
        inicio = time.monotonic()
        logs = self._falha(self.servidor(atraso=1.5), timeout=0.3)
        self.assertLess(time.monotonic() - inicio, 3)  # 3 timeouts de 0,3 s, não 6 × 1,5 s
        self.assertTrue(any("timeout" in l for l in logs))

    def test_servidor_fora_do_ar(self):
        s = ServidorFalso()
        url = s.url
        s.fechar()
        self._falha(url)

    def test_sucesso_zera_as_falhas(self):
        s = self.servidor(status=500)
        v = self.vila(s.url)
        with self.assertLogs("bot.vila", "WARNING"):
            v.emitir("a")
            v.emitir("b")
            s.status = 200
            v.emitir("c")
            s.status = 500
            v.emitir("d")
            v.emitir("e")
        self.assertFalse(v.desistiu)

    def test_sem_url_a_vila_fica_desligada(self):
        v = self.vila("")
        self.assertIsNone(v.emitir("fase", fase="x"))
        self.assertEqual(self.pendentes(), [])


class DadosMinimosTest(unittest.TestCase):
    def test_chaves_proibidas_e_cnj_saem(self):
        with self.assertLogs("bot.vila", "WARNING"):
            e = vila._limpar({"tipo": "tarefa", "cnj": VALORES_FICTICIOS["cnj"], "orgao": "x", "valor": "1,00",
                              "texto": "t", "comprovante": "c.pdf", "motivo": "ver 0001234-56.2026.4.05.8100",
                              "campos": ["cnj", "orgao", "valor", "0001234-56.2026.4.05.8100"]})
        self.assertEqual(set(e), {"tipo", "motivo", "campos"})
        self.assertEqual(e["campos"], ["cnj", "orgao", "valor"])
        self.assertNotRegex(json.dumps(e), CNJ_FORMATO)

    def test_codigos_da_classificacao(self):
        casos = {"EDITAR OS DADOS DA AÇÃO PROTOCOLADA (PREVIDENCIÁRIO)": None,
                 "PROTOCOLAR INICIAL (PREVIDENCIÁRIO)": "outro_tipo",
                 "Ação contra fundo de previdência complementar": "previdencia_privada",
                 "Reunião interna": "sem_sinal_previdenciario",
                 "Previdenciário / Cível - prazo": "outra_area",
                 "INSS - BPC/LOAS - protocolo": "sinal_sem_previdenci",
                 "INSS - cível": "sinal_sem_previdenci"}
        for titulo, codigo in casos.items():
            with self.subTest(titulo=titulo):
                classe, motivo = classificacao.classificar(titulo, "PREVIDENCI", "EDITAR OS DADOS DA ACAO PROTOCOLADA")
                self.assertEqual(vila.motivo_classificacao(classe, motivo), codigo)

    def test_codigos_dos_erros(self):
        casos = [(comprovante.ComprovanteErro("esperado 1 comprovante de protocolo, achei 0 (nenhum)"), "sem_comprovante"),
                 (comprovante.ComprovanteErro("esperado 1 comprovante de protocolo, achei 2 (a; b)"), "mais_de_um_comprovante"),
                 (comprovante.ComprovanteErro("PDF sem texto (escaneado?): conferir manualmente"), "pdf_sem_texto"),
                 (comprovante.ComprovanteErro("Valor da ação: não encontrado no PDF"), "dado_ausente_no_pdf"),
                 (comprovante.ComprovanteErro("N.° CNJ: mais de um valor no PDF (a; b)"), "dado_duplicado_no_pdf"),
                 (comprovante.ComprovanteErro("o PDF é do processo X, mas a tela do processo mostra Y"), "cnj_diferente_do_processo"),
                 (edicao.EdicaoErro("campo já preenchido com outro valor, nada alterado"), "campo_com_outro_valor"),
                 (edicao.EdicaoErro("a tela de edição (u) não é do processo aberto: nada alterado"), "processo_diferente_na_edicao"),
                 (edicao.ConferenciaErro("depois de Gravar o VIOS mostrou um aviso que o bot não responde: 'x'"), "aviso_inesperado"),
                 (processo.ProcessoErro("esperado 1 lápis do N.° CNJ, achei 2"), "elemento_nao_unico"),
                 (RuntimeError("qualquer coisa"), "excecao")]
        for erro, codigo in casos:
            with self.subTest(erro=str(erro)):
                self.assertEqual(vila.motivo_erro(erro), codigo)


def _chaves(valor):
    if isinstance(valor, dict):
        return set(valor) | set().union(*(_chaves(v) for v in valor.values()))
    if isinstance(valor, list):
        return set().union(set(), *(_chaves(v) for v in valor))
    return set()


class ExecucaoSimuladaTest(unittest.TestCase):
    """main.main() em simulação com o VIOS trocado por dublês e a vila apontando para o servidor falso."""
    TIPO = "EDITAR OS DADOS DA AÇÃO PROTOCOLADA (PREVIDENCIÁRIO)"
    CALENDARIO = [  # (texto fictício, pxe_id)
        (f"{TIPO} - fictícia A", "88123"),
        (f"{TIPO} - fictícia B", "88125"),
        (f"{TIPO} - fictícia já registrada", "88126"),
        ("PROTOCOLAR INICIAL (PREVIDENCIÁRIO) - fictícia", "88124"),
        ("Revisão de previdência privada - fictícia", "88130"),
        ("Previdenciário / Cível - fictícia", "88131"),
    ]
    PROCESSO = "https://vios.invalido/?pag=ver&processos_id=40211"
    EDICAO = "https://vios.invalido/?pag=editar&processos_id=40211&act=edit"

    def link(self, pxe):
        return f"https://vios.invalido/?pag=tarefa&pxe_id={pxe}"

    def rodar(self, *args, hoje=date(2026, 10, 30), login=None):
        s = ServidorFalso()
        self.addCleanup(s.fechar)
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        saida = Path(pasta.name) / "saida"
        saida.mkdir()
        (saida / main.REGISTRO).write_text(json.dumps({self.link("88126"): {"quando": "29/10/2026 10:00"}}), encoding="utf-8")
        env = Path(pasta.name) / ".env"
        env.write_text(f"VILA_URL={s.url}\nVILA_SENHA={SENHA}\nSAIDA_PASTA={saida}\n", encoding="utf-8")
        cfg = SimpleNamespace(timeout=1, headless=True, manter_aberto=False, pasta_saida=saida,
                              calendario_url="u", calendario_tarefa=("css selector", ".fc-event"),
                              calendario_filtro="PREVIDENCI", calendario_tipo="EDITAR OS DADOS DA ACAO PROTOCOLADA")
        elementos = [mock.Mock(**{"get_attribute.return_value": t}) for t, _ in self.CALENDARIO]
        driver = mock.Mock(current_url=self.EDICAO, **{"find_elements.return_value": elementos})
        achados = [{"texto": "Comprovante (FICTÍCIO).pdf", "href": "x"},
                   comprovante.ComprovanteErro("esperado 1 comprovante de protocolo, achei 0 (nenhum)")]
        datas = mock.Mock(wraps=date, **{"today.return_value": hoje})
        with ExitStack() as pilha:
            pilha.enter_context(mock.patch.dict(os.environ))
            pilha.enter_context(mock.patch.object(main, "configurar_log"))
            pilha.enter_context(mock.patch.object(main, "date", datas))
            pilha.enter_context(mock.patch.object(main.config, "carregar", return_value=cfg))
            pilha.enter_context(mock.patch.object(main, "criar_driver", return_value=driver))
            pilha.enter_context(mock.patch.object(main, "fazer_login", side_effect=login))
            pilha.enter_context(mock.patch.object(main, "bloquear_envios"))
            pilha.enter_context(mock.patch.object(main, "abrir"))
            pilha.enter_context(mock.patch.object(main, "envios_bloqueados", return_value=True))
            pilha.enter_context(mock.patch.object(calendario, "abrir"))
            pilha.enter_context(mock.patch.object(calendario, "WebDriverWait"))
            pilha.enter_context(mock.patch.object(calendario, "links", return_value=[{"texto": t, "href": self.link(p)} for t, p in self.CALENDARIO]))
            pilha.enter_context(mock.patch.object(processo, "link_processo", return_value=self.PROCESSO))
            pilha.enter_context(mock.patch.object(processo, "cnj", return_value=set()))
            pilha.enter_context(mock.patch.object(processo, "link_galeria", return_value="g"))
            pilha.enter_context(mock.patch.object(processo, "ir_para_edicao", return_value=self.EDICAO))
            pilha.enter_context(mock.patch.object(comprovante, "achar", side_effect=achados))
            pilha.enter_context(mock.patch.object(comprovante, "ler", return_value=PDF_FICTICIO))
            pilha.enter_context(mock.patch.object(edicao, "_ir"))
            pilha.enter_context(mock.patch.object(edicao, "WebDriverWait"))
            pilha.enter_context(mock.patch.object(edicao, "_campo"))
            pilha.enter_context(mock.patch.object(edicao, "_preencher"))
            pilha.enter_context(mock.patch.object(edicao, "_tem_opcao", return_value=True))
            pilha.enter_context(mock.patch.object(edicao, "_ler_todos", side_effect=[{"cnj": "", "orgao": "", "valor": ""}, VALORES_FICTICIOS]))
            pilha.enter_context(mock.patch.object(main.relatorio, "escrever", return_value="relatorio.csv"))
            codigo = main.main(*args, str(env))
        self.assertEqual(s.eventos(), vila.atual().emitidos)  # tudo chegou ao servidor
        return codigo, s.eventos()

    def test_sequencia_da_simulacao(self):
        _, eventos = self.rodar()
        tipos = [e["tipo"] for e in eventos]
        self.assertEqual(tipos[0], "execucao_iniciada")
        self.assertEqual(tipos[-1], "execucao_fim")
        self.assertEqual(tipos.count("execucao_fim"), 1)
        self.assertEqual(eventos[0]["modo"], "teste")
        self.assertIs(eventos[0]["fora_da_janela"], False)
        self.assertEqual([e["fase"] for e in eventos if e["tipo"] == "fase"], ["entrando_vios", "lendo_calendario", "processando"])
        self.assertLess(tipos.index("calendario"), tipos.index("tarefa"))
        self.assertEqual(tipos[:5], ["execucao_iniciada", "fase", "fase", "calendario", "fase"])
        self.assertTrue({e["envio"] for e in eventos} == {eventos[0]["envio"]} and {e["bot"] for e in eventos} == {"zangao"})

        cal = next(e for e in eventos if e["tipo"] == "calendario")
        self.assertEqual((cal["total"], cal["previdenciarias"], cal["processar"], cal["ignoradas"], cal["ambiguas"]), (6, 4, 2, 1, 1))
        por_id = {t["tarefa_id"]: t for t in cal["tarefas"]}
        self.assertEqual(por_id["88123"]["decisao"], "processar")
        self.assertEqual(por_id["88126"]["decisao"], "ja_registrada")
        self.assertEqual((por_id["88124"]["decisao"], por_id["88124"]["motivo"]), ("ignorada", "outro_tipo"))
        self.assertEqual(por_id["88130"]["motivo"], "previdencia_privada")
        self.assertEqual((por_id["88131"]["classe"], por_id["88131"]["motivo"]), ("ambigua", "outra_area"))

        etapas = [(e["tarefa_id"], e["etapa"]) for e in eventos if e["tipo"] == "tarefa"]
        self.assertEqual(etapas, [("88123", "abrindo"), ("88123", "comprovante_lido"), ("88123", "preenchendo"),
                                  ("88123", "testada"), ("88125", "abrindo"), ("88125", "pulada")])
        tarefas = [e for e in eventos if e["tipo"] == "tarefa"]
        self.assertEqual(tarefas[0]["processo_id"], "40211")
        self.assertEqual(tarefas[2]["campos"], ["cnj", "orgao", "valor"])
        self.assertEqual(tarefas[-1]["motivo"], "sem_comprovante")

        fim = eventos[-1]
        self.assertEqual(fim["resultado"], "testado")
        self.assertEqual({k: v for k, v in fim["contagens"].items() if v},
                         {"teste": 1, "pulada": 1, "ja_registrada": 1, "ignorada": 2, "ambigua": 1})

    def test_dados_minimos_em_todos_os_eventos(self):
        _, eventos = self.rodar()
        texto = json.dumps(eventos, ensure_ascii=False)
        self.assertFalse(_chaves(eventos) & vila.PROIBIDAS)
        self.assertNotRegex(texto, CNJ_FORMATO)
        for proibido in [VALORES_FICTICIOS["orgao"], VALORES_FICTICIOS["valor"], "FICTÍCIO", "fictícia", "vios.invalido"]:
            self.assertNotIn(proibido, texto)

    def test_login_falhou_termina_em_execucao_fim(self):
        codigo, eventos = self.rodar(login=main.LoginErro("login não confirmado"))
        self.assertEqual(codigo, 1)
        self.assertEqual([e["tipo"] for e in eventos], ["execucao_iniciada", "fase", "execucao_fim"])
        self.assertEqual((eventos[-1]["resultado"], eventos[-1]["motivo"]), ("parou", "login_falhou"))

    def test_fora_do_dia_so_um_evento(self):
        codigo, eventos = self.rodar(hoje=date(2026, 10, 28))
        self.assertEqual(codigo, 0)
        self.assertEqual([(e["tipo"], e["resultado"]) for e in eventos], [("execucao_fim", "fora_do_dia")])

    def test_tarefa_unica(self):
        _, eventos = self.rodar("--tarefa", self.link("88123"))
        self.assertIs(eventos[0]["tarefa_unica"], True)
        cal = next(e for e in eventos if e["tipo"] == "calendario")
        self.assertEqual(cal["processar"], 1)
        self.assertEqual({e["tarefa_id"] for e in eventos if e["tipo"] == "tarefa"}, {"88123"})


if __name__ == "__main__":
    unittest.main()
