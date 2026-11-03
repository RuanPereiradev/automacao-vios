"""Testes do bot/processo_ficha.py com driver falso (sem Selenium real e sem VIOS).

O bot/js/ficha.js também é testado num DOM sintético com Node + jsdom, se
houver jsdom na máquina. O jsdom é procurado em JSDOM_DIR (pasta do pacote,
ex.: JSDOM_DIR=/caminho/node_modules/jsdom), depois em node_modules deste
projeto e de projetos ao lado. Sem Node ou sem jsdom, esses testes são pulados.
Todos os nomes e números aqui são inventados.
"""
import glob
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from selenium.common.exceptions import JavascriptException, WebDriverException

from bot import processo_ficha as pf
from bot.processos_grupo import URL_LISTA

RAIZ = Path(__file__).resolve().parent.parent

FICHA_JS = {
    "campos": {
        "N.° CNJ": "0000001-11.2026.8.06.0001",
        "Cidade / UF": "Cidade Inventada / CE",
        "Fase": "Recursal",
        "Data da ação / Distribuição": "10/02/2026",
        "Valor da ação": "R$ 12.345,67",
        "Justiça": "Estadual",
        "Sistema do tribunal": "PJe",
        "Parte passiva": "Contrário: EMPRESA FICTICIA LTDA; Contrário: OUTRA FICTICIA SA",
    },
    "tarefas": [
        {
            "ci": "900", "situacao": "", "tipo": "ANALISAR PROCESSO (CÍVEL) 2026",
            "descricao": "Ver   andamento", "comentarios": "Aguardando julgamento.",
            "para_conclusao": "01/03/2026", "limite": "05/03/2026", "concluida_em": "",
        },
        {"ci": "899", "situacao": "CANCELADA", "tipo": "AUDIÊNCIA", "descricao": None},
    ],
    "comentarios": [{"data": "02/03/2026 10:00", "autor": "FULANO DE TAL", "texto": "Tudo certo."}],
    "arquivos": [{"data": "01/03/2026", "pasta": "Geral", "tipo": "PDF", "descricao": "Petição", "arquivo": "peticao.pdf"}],
}


class DriverFalso:
    """Imita o pouco do Selenium que a ficha usa."""

    def __init__(self, resultado=None, blocos=True, tarefas=True, url_depois=None, login_ao_abrir=False,
                 rotulos=False):
        self.resultado = FICHA_JS if resultado is None else resultado
        self.blocos = blocos
        self.rotulos = rotulos
        self.tarefas = tarefas
        self.url_depois = url_depois
        self.login_ao_abrir = login_ao_abrir
        self.current_url = "about:blank"
        self.campo_senha = False
        self.abertas = []
        self.scripts = []
        self.esperas = []

    def get(self, url):
        self.abertas.append(url)
        self.current_url = self.url_depois or url
        if self.login_ao_abrir:
            self.campo_senha = True

    def find_elements(self, by, valor):
        self.esperas.append((by, valor))
        if (by, valor) == pf.CAMPO_SENHA:
            return [object()] if self.campo_senha else []
        if (by, valor) == pf.BLOCOS:
            return [object()] if self.blocos else []
        if (by, valor) == pf.ROTULOS:
            return [object()] if (self.blocos or self.rotulos) else []
        if (by, valor) == pf.TAREFAS:
            return [object()] if self.tarefas else []
        return []

    def execute_script(self, script, *args):
        self.scripts.append(script)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


class TestUrl(unittest.TestCase):
    def test_mesmo_dominio_da_lista(self):
        url = pf.url_ficha(" 123 ")
        self.assertTrue(url.startswith(URL_LISTA.split("?", 1)[0] + "?"))
        self.assertTrue(url.endswith("pag=sys/processos/processos-vis.php&processos_id=123"))

    def test_ci_invalido(self):
        for ci in ("", None, "12a", "1&pag=x"):
            with self.assertRaises(ValueError):
                pf.url_ficha(ci)

    def test_ci_invalido_vira_ficha_com_erro(self):
        driver = DriverFalso()
        ficha = pf.ler_ficha(driver, "abc", 1)
        self.assertFalse(ficha["ok"])
        self.assertEqual(driver.abertas, [])


class TestScript(unittest.TestCase):
    def test_script_e_um_return_de_expressao(self):
        js = pf.script_ficha()
        self.assertTrue(js.startswith("return (\n"))
        self.assertTrue(js.endswith("\n);"))
        self.assertIn("vj-bloco-info-text-area", js)

    def test_script_so_le(self):
        # nada de clicar, enviar formulário ou buscar coisa na rede
        js = pf.ARQUIVO_JS.read_text(encoding="utf-8")
        for proibido in (".click(", "fetch(", "XMLHttpRequest", ".submit(", "requestSubmit", "innerHTML =",
                         ".remove(", "removeChild", "appendChild", "location"):
            self.assertNotIn(proibido, js)


class TestLerFicha(unittest.TestCase):
    def test_ficha_completa(self):
        driver = DriverFalso()
        ficha = pf.ler_ficha(driver, "123", 1)
        self.assertTrue(ficha["ok"], ficha["erro"])
        self.assertEqual(ficha["erro"], "")
        self.assertEqual(driver.abertas, [pf.url_ficha("123")])
        self.assertEqual(len(driver.scripts), 1)
        self.assertEqual(ficha["cidade_uf"], "Cidade Inventada / CE")
        self.assertEqual(ficha["fase"], "Recursal")
        self.assertEqual(ficha["data_distribuicao"], "10/02/2026")
        self.assertEqual(ficha["valor_acao"], "12.345,67")
        self.assertEqual(ficha["justica"], "Estadual")
        self.assertEqual(ficha["sistema"], "PJe")
        self.assertEqual(ficha["campos"]["N.° CNJ"], "0000001-11.2026.8.06.0001")

    def test_tarefas_com_todas_as_chaves(self):
        ficha = pf.ler_ficha(DriverFalso(), "123", 1)
        self.assertEqual(len(ficha["tarefas"]), 2)
        for t in ficha["tarefas"]:
            self.assertEqual(set(t), set(pf.CAMPOS_TAREFA))
            self.assertTrue(all(isinstance(v, str) for v in t.values()))
        self.assertEqual(ficha["tarefas"][0]["descricao"], "Ver andamento")
        self.assertEqual(ficha["tarefas"][1]["situacao"], "CANCELADA")
        self.assertEqual(ficha["tarefas"][1]["descricao"], "")
        self.assertEqual(ficha["comentarios"][0]["autor"], "FULANO DE TAL")
        self.assertEqual(ficha["arquivos"][0]["arquivo"], "peticao.pdf")

    def test_normalizados_vindos_so_dos_campos(self):
        # script antigo ou parcial: só "campos" -> o Python acha pelos rótulos
        resultado = {"campos": {"Cidade/UF": "Vila Exemplo / PI", "Valor da ação": "0,00",
                                "Data da ação / Distribuição": "00/00/0000"}}
        ficha = pf.ler_ficha(DriverFalso(resultado), "5", 1)
        self.assertTrue(ficha["ok"])
        self.assertEqual(ficha["cidade_uf"], "Vila Exemplo / PI")
        self.assertEqual(ficha["valor_acao"], "")
        self.assertEqual(ficha["data_distribuicao"], "")
        self.assertEqual(ficha["tarefas"], [])
        self.assertEqual(ficha["comentarios"], [])
        self.assertEqual(ficha["arquivos"], [])

    def test_sem_tarefas_nao_trava(self):
        driver = DriverFalso(dict(FICHA_JS, tarefas=[]), tarefas=False)
        ficha = pf.ler_ficha(driver, "123", 0.3)
        self.assertTrue(ficha["ok"])
        self.assertEqual(ficha["tarefas"], [])
        self.assertIn(pf.TAREFAS, driver.esperas)

    def test_tipos_estranhos_do_script(self):
        resultado = {"campos": {"Fase": None, "Área": 3}, "tarefas": "x", "comentarios": [1, None],
                     "arquivos": None}
        ficha = pf.ler_ficha(DriverFalso(resultado), "1", 1)
        self.assertEqual(ficha["campos"], {"Fase": "", "Área": "3"})
        self.assertEqual(ficha["tarefas"], [])
        self.assertEqual(ficha["comentarios"], [])
        self.assertEqual(ficha["arquivos"], [])

    def test_ficha_sem_campos_nao_e_ok(self):
        ficha = pf.ler_ficha(DriverFalso({"campos": {}}), "1", 1)
        self.assertFalse(ficha["ok"])
        self.assertIn("sem campos", ficha["erro"])

    def test_erro_de_js_vira_ficha_com_erro(self):
        driver = DriverFalso(JavascriptException("ReferenceError: x is not defined"))
        ficha = pf.ler_ficha(driver, "123", 1)
        self.assertFalse(ficha["ok"])
        self.assertIn("ReferenceError", ficha["erro"])
        self.assertEqual(set(ficha), set(pf.ficha_vazia("").keys()))

    def test_erro_de_programa_nao_e_engolido(self):
        with self.assertRaises(ZeroDivisionError):
            pf.ler_ficha(DriverFalso(ZeroDivisionError("bug")), "123", 1)

    def test_script_devolve_nada(self):
        ficha = pf.ler_ficha(DriverFalso(resultado=[]), "123", 1)
        self.assertFalse(ficha["ok"])
        self.assertIn("esperado um objeto", ficha["erro"])

    def test_blocos_nao_aparecem(self):
        driver = DriverFalso(blocos=False)
        ficha = pf.ler_ficha(driver, "123", 0.3)
        self.assertFalse(ficha["ok"])
        self.assertIn("não carregou", ficha["erro"])
        self.assertEqual(driver.scripts, [])

    def test_so_rotulos_na_tela(self):
        # o Vue montou os rótulos, mas o dado não chegou
        driver = DriverFalso(blocos=False, rotulos=True)
        ficha = pf.ler_ficha(driver, "123", 0.3)
        self.assertFalse(ficha["ok"])
        self.assertIn("rótulos", ficha["erro"])
        self.assertEqual(driver.scripts, [])

    def test_ficha_so_com_rotulos_vazios_nao_e_ok(self):
        ficha = pf.ler_ficha(DriverFalso({"campos": {"N.° CNJ": "", "Cliente": " "}}), "1", 1)
        self.assertFalse(ficha["ok"])
        self.assertIn("sem nenhum valor", ficha["erro"])

    def test_cidade_e_uf_vazias(self):
        resultado = {"campos": {"Cliente": "EMPRESA FICTICIA", "Cidade / UF": "/"}, "cidade_uf": " / "}
        ficha = pf.ler_ficha(DriverFalso(resultado), "1", 1)
        self.assertTrue(ficha["ok"])
        self.assertEqual(ficha["cidade_uf"], "")
        self.assertEqual(ficha["campos"]["Cidade / UF"], "/")  # campos fica como veio

    def test_get_falha(self):
        class Quebrado(DriverFalso):
            def get(self, url):
                raise WebDriverException("net::ERR_INTERNET_DISCONNECTED")

        ficha = pf.ler_ficha(Quebrado(), "123", 1)
        self.assertFalse(ficha["ok"])
        self.assertIn("ERR_INTERNET", ficha["erro"])


class TestSessaoExpirada(unittest.TestCase):
    def test_url_de_login(self):
        driver = DriverFalso(url_depois="https://vios.exemplo/entrar.php?volta=1")
        with self.assertRaises(pf.SessaoExpirada):
            pf.ler_ficha(driver, "123", 1)
        self.assertEqual(driver.scripts, [])

    def test_campo_de_senha_na_tela(self):
        driver = DriverFalso(login_ao_abrir=True)
        with self.assertRaises(pf.SessaoExpirada):
            pf.ler_ficha(driver, "123", 1)

    def test_login_aparece_durante_a_espera(self):
        class LoginDepois(DriverFalso):
            def find_elements(self, by, valor):
                if (by, valor) == pf.BLOCOS:
                    self.campo_senha = True  # o VIOS redirecionou enquanto esperava
                return super().find_elements(by, valor)

        with self.assertRaises(pf.SessaoExpirada):
            pf.ler_ficha(LoginDepois(blocos=False), "123", 1)

    def test_navegador_quebrado_nao_e_login(self):
        class Morto:
            @property
            def current_url(self):
                raise RuntimeError("morto")

        self.assertFalse(pf.na_tela_de_login(Morto()))


# ---------------------------------------------------------------------------
# ficha.js num DOM sintético (Node + jsdom)
# ---------------------------------------------------------------------------

def _achar_jsdom():
    candidatos = []
    if os.getenv("JSDOM_DIR"):
        candidatos.append(os.getenv("JSDOM_DIR"))
    candidatos += sorted(glob.glob(str(RAIZ / "node_modules" / "jsdom")))
    candidatos += sorted(glob.glob(str(RAIZ.parent / "*" / "node_modules" / "jsdom")))
    for c in candidatos:
        if (Path(c) / "package.json").exists():
            return str(Path(c).resolve())
    return None


NODE = shutil.which("node")
JSDOM = _achar_jsdom() if NODE else None

# roda o MESMO texto que o Python manda ao execute_script, como corpo de função
RODAR = r"""
const fs = require("fs");
const { JSDOM } = require(process.argv[1]);
const html = fs.readFileSync(process.argv[2], "utf8");
const script = fs.readFileSync(process.argv[3], "utf8");
const dom = new JSDOM(html, { runScripts: "outside-only" });
dom.window.__script = script;
const r = dom.window.eval("(new Function(window.__script))()");
process.stdout.write(JSON.stringify(r));
"""

# conta os nós que um XPath acha (confere os seletores de espera do Python)
CONTAR_XPATH = r"""
const fs = require("fs");
const { JSDOM } = require(process.argv[1]);
const dom = new JSDOM(fs.readFileSync(process.argv[2], "utf8"));
const doc = dom.window.document;
const r = doc.evaluate(process.argv[3], doc, null, 7, null);
process.stdout.write(String(r.snapshotLength));
"""

LINHA_TAREFA = """
<tr>
  <td><i class="vj-icon-check"></i></td>
  <td>{ci}</td>
  <td>{badge}<span>{tipo}</span></td>
  <td><div class="limite-texto">{descricao}</div> <a href="javascript:void(0)">mais</a></td>
  <td>{comentarios}</td>
  <td>{datas}</td>
  <td>Responsáveis: FULANO Concluiu a tarefa: BELTRANO</td>
  <td><a title="Editar">e</a></td>
</tr>"""

CAB_TAREFAS = """<thead><tr><th></th><th>CI</th><th>Tipo de tarefa</th><th>Descrição</th><th>Comentários</th>
<th>Datas</th><th>Envolvidos</th><th>Ações</th></tr></thead>"""

HTML_FICHA = """<!doctype html><html><body>
<div id="app">
 <div class="vj-bloco-info-text-area">
  <p><strong><span>N.° CNJ</span>: </strong> <span>0000001-11.2026.8.06.0001</span>
     <span class="vj-acoes-dados"><a title="Copiar">copiar</a></span></p>
  <p><strong><span>Área</span>: </strong> <span>Cível   Consumidor</span></p>
  <p><strong><span>Data da ação / Distribuição</span>: </strong> <span>10/02/2026</span></p>
 </div>
 <div class="vj-bloco-info-text-area">
  <p><strong><span>Cliente</span>: </strong> <a href="#"><i class="vj-icon-user"></i> EMPRESA FICTICIA LTDA</a></p>
  <p><strong><span>Parte ativa</span>: </strong> <span>Autor: <a href="#"><i class="vj-icon-user"></i> JOAO INVENTADO</a></span></p>
  <p><strong><span>Parte passiva</span>: </strong>
     <span>Contrário: <a href="#"><i class="vj-icon-user"></i> EMPRESA FICTICIA LTDA</a></span>
     <span>Contrário: <a href="#"><i class="vj-icon-user"></i> OUTRA FICTICIA SA</a></span>
     <span class="vj-acoes-dados"><a>+</a></span></p>
  <p><strong><span>Terceiros</span>: </strong> Interessado: <a href="#"><i class="vj-icon-user"></i> FULANA A</a>
     Interessado: <a href="#"><i class="vj-icon-user"></i> FULANA B</a></p>
  <p><strong><span>Processo</span>: </strong> <span>CÍVEL</span></p>
  <p><strong><span>Fase</span>: </strong> <span>Recursal</span></p>
  <p><strong><span>Cidade / UF</span>: </strong> <span>Cidade Inventada / CE</span> <span class="vj-acoes-dados">x</span></p>
 </div>
 <div class="vj-bloco-info-text-area">
  <p><strong><span>Justiça</span>: </strong> <span>Estadual</span></p>
  <p><strong><span>Sistema do tribunal</span>: </strong> <span>PJe</span></p>
  <p><strong><span>Valor da ação</span>: </strong> <span>R$ 12.345,67</span></p>
  <p><strong><span>Valor da ação atualizado</span>: </strong> <span></span></p>
 </div>

 <div class="card"><div class="card-header"><h5>Tarefas (2)</h5></div><div class="card-body">
  <div class="dataTables_wrapper">
   <div class="dataTables_scrollHead"><table>""" + CAB_TAREFAS + """</table></div>
   <div class="dataTables_scrollBody"><table>""" + CAB_TAREFAS + """<tbody>
""" + LINHA_TAREFA.format(
    ci="902", badge="", tipo="ANALISAR PROCESSO (CÍVEL) 2026",
    descricao="Verificar a situação do processo.<br>Texto que a tela esconde depois do corte.",
    comentarios="O processo encontra-se na Turma Recursal, aguardando julgamento.",
    datas="Para conclusão 01/03/2026 Limite 05/03/2026 Concluída em: 04/03/2026",
) + LINHA_TAREFA.format(
    ci="901", badge='<span class="vj-badge">CANCELADA</span> ', tipo="AUDIÊNCIA",
    descricao="Audiência <b>virtual</b>", comentarios="",
    datas="Para conclusão 20/02/2026 Limite 21/02/2026",
) + """
   </tbody></table></div>
  </div>
 </div></div>

 <div class="card"><div class="card-header"><h5>Arquivos</h5></div><div class="card-body">
  <table><thead><tr><th>Data</th><th>Pasta</th><th>Tipo</th><th>Descrição</th><th>Arquivo</th>
   <th>Responsável</th><th>Tamanho</th><th>Ações</th></tr></thead>
   <tbody><tr><td>01/03/2026</td><td>Geral</td><td>PDF</td><td>Petição inicial</td><td><a href="#">peticao.pdf</a></td>
   <td>FULANO</td><td>1,2 MB</td><td><a title="Apagar">x</a></td></tr></tbody></table>
 </div></div>

 <div class="card"><div class="card-header"><h5>Comentários</h5></div><div class="card-body">
  <div class="comentario"><div><small>02/03/2026 10:00 - FULANO DE TAL</small></div>
   <div>Cliente avisado por telefone.</div><div>Retornar na semana que vem.</div></div>
  <div class="comentario"><div><small>01/03/2026 09:15 - SISTEMA</small></div>
   <div>Tarefa encerrada ao enviar o(s) arquivo(s): peticao.pdf</div></div>
 </div></div>

 <div class="card"><div class="card-header"><h5>Recados</h5></div><div class="card-body">
  <div>05/03/2026 08:00 - NAO E COMENTARIO</div><div>recado interno</div>
 </div></div>
</div></body></html>"""

HTML_SEM_TAREFAS = """<!doctype html><html><body>
 <div class="vj-bloco-info-text-area">
  <p><strong><span>Cidade / UF</span>: </strong> <span>Vila Exemplo / PI</span></p>
  <p><strong><span>Valor da ação</span>: </strong> <span>0,00</span></p>
 </div>
 <h5>Tarefas</h5>
 <div class="dataTables_wrapper"><table>""" + CAB_TAREFAS + """<tbody>
  <tr class="odd"><td valign="top" colspan="8" class="dataTables_empty">Nenhum registro encontrado</td></tr>
 </tbody></table></div>
 <h5>Comentários</h5>
 <div>Nenhum comentário.</div>
</body></html>"""


@unittest.skipUnless(NODE and JSDOM, "sem node ou sem jsdom: ficha.js não testado no DOM sintético")
class TestFichaJsNoDom(unittest.TestCase):
    def rodar_js(self, html):
        with tempfile.TemporaryDirectory() as tmp:
            arq_html = Path(tmp) / "ficha.html"
            arq_js = Path(tmp) / "script.js"
            arq_html.write_text(html, encoding="utf-8")
            arq_js.write_text(pf.script_ficha(), encoding="utf-8")
            saida = subprocess.run(
                [NODE, "-e", RODAR, JSDOM, str(arq_html), str(arq_js)],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(saida.returncode, 0, saida.stderr)
        return json.loads(saida.stdout)

    def contar_xpath(self, html, xpath):
        with tempfile.TemporaryDirectory() as tmp:
            arq_html = Path(tmp) / "ficha.html"
            arq_html.write_text(html, encoding="utf-8")
            saida = subprocess.run(
                [NODE, "-e", CONTAR_XPATH, JSDOM, str(arq_html), xpath],
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(saida.returncode, 0, saida.stderr)
        return int(saida.stdout)

    def ficha(self, html):
        """ler_ficha completo, com o execute_script rodando o ficha.js de verdade."""
        teste = self

        class DriverJs(DriverFalso):
            def execute_script(self, script, *args):
                self.scripts.append(script)
                return teste.rodar_js(html)

        return pf.ler_ficha(DriverJs(), "123", 1)

    def test_campos(self):
        f = self.ficha(HTML_FICHA)
        self.assertTrue(f["ok"], f["erro"])
        c = f["campos"]
        self.assertEqual(c["N.° CNJ"], "0000001-11.2026.8.06.0001")
        self.assertEqual(c["Área"], "Cível Consumidor")
        self.assertEqual(c["Cliente"], "EMPRESA FICTICIA LTDA")
        self.assertEqual(c["Parte ativa"], "Autor: JOAO INVENTADO")
        self.assertEqual(c["Parte passiva"], "Contrário: EMPRESA FICTICIA LTDA; Contrário: OUTRA FICTICIA SA")
        # partes soltas no <p>, sem <span> em volta: o rótulo vai junto com a parte certa
        self.assertEqual(c["Terceiros"], "Interessado: FULANA A; Interessado: FULANA B")
        self.assertEqual(c["Valor da ação atualizado"], "")
        self.assertEqual(f["cidade_uf"], "Cidade Inventada / CE")
        self.assertEqual(f["fase"], "Recursal")
        self.assertEqual(f["data_distribuicao"], "10/02/2026")
        self.assertEqual(f["valor_acao"], "12.345,67")
        self.assertEqual(f["justica"], "Estadual")
        self.assertEqual(f["sistema"], "PJe")

    def test_tarefas(self):
        f = self.ficha(HTML_FICHA)
        self.assertEqual([t["ci"] for t in f["tarefas"]], ["902", "901"])
        nova, cancelada = f["tarefas"]
        self.assertEqual(nova["situacao"], "")
        self.assertEqual(nova["tipo"], "ANALISAR PROCESSO (CÍVEL) 2026")
        self.assertEqual(nova["descricao"],
                         "Verificar a situação do processo. Texto que a tela esconde depois do corte.")
        self.assertEqual(nova["comentarios"], "O processo encontra-se na Turma Recursal, aguardando julgamento.")
        self.assertEqual((nova["para_conclusao"], nova["limite"], nova["concluida_em"]),
                         ("01/03/2026", "05/03/2026", "04/03/2026"))
        self.assertEqual(cancelada["situacao"], "CANCELADA")
        self.assertEqual(cancelada["tipo"], "AUDIÊNCIA")
        self.assertEqual(cancelada["descricao"], "Audiência virtual")
        self.assertEqual(cancelada["concluida_em"], "")

    def test_comentarios_e_arquivos(self):
        f = self.ficha(HTML_FICHA)
        self.assertEqual(f["comentarios"], [
            {"data": "02/03/2026 10:00", "autor": "FULANO DE TAL",
             "texto": "Cliente avisado por telefone. Retornar na semana que vem."},
            {"data": "01/03/2026 09:15", "autor": "SISTEMA",
             "texto": "Tarefa encerrada ao enviar o(s) arquivo(s): peticao.pdf"},
        ])
        self.assertEqual(f["arquivos"], [
            {"data": "01/03/2026", "pasta": "Geral", "tipo": "PDF", "descricao": "Petição inicial",
             "arquivo": "peticao.pdf"},
        ])

    def test_sem_tarefas_sem_comentarios_sem_arquivos(self):
        f = self.ficha(HTML_SEM_TAREFAS)
        self.assertTrue(f["ok"], f["erro"])
        self.assertEqual(f["cidade_uf"], "Vila Exemplo / PI")
        self.assertEqual(f["valor_acao"], "")
        self.assertEqual(f["tarefas"], [])
        self.assertEqual(f["comentarios"], [])
        self.assertEqual(f["arquivos"], [])

    def test_pagina_vazia(self):
        f = self.ficha("<!doctype html><html><body><p>nada</p></body></html>")
        self.assertFalse(f["ok"])
        self.assertEqual(f["tarefas"], [])

    def test_variantes(self):
        # comentários em tabela "Data / Usuário | Comentário" e link "mais" dentro da descrição
        html = """<!doctype html><html><body>
         <div class="vj-bloco-info-text-area"><p><strong>Fase: </strong> Inicial</p></div>
         <div class="dataTables_wrapper"><table>""" + CAB_TAREFAS + """<tbody>
         <tr><td></td><td>7</td><td>PRAZO</td>
          <td><div class="limite-texto">Começo do texto <span>... mais</span><span style="display:none">fim escondido</span></div></td>
          <td></td><td>Para conclusão 01/01/2026 10:30 Limite 02/01/2026</td><td></td><td></td></tr>
         </tbody></table></div>
         <table><thead><tr><th>Data / Usuário</th><th>Comentário</th><th></th></tr></thead>
          <tbody><tr><td>03/01/2026 11:00<br>- CICLANO</td><td>Cliente ligou.</td><td><a title="Apagar"></a></td></tr>
          </tbody></table>
        </body></html>"""
        f = self.ficha(html)
        self.assertEqual(f["fase"], "Inicial")
        self.assertEqual(f["tarefas"][0]["descricao"], "Começo do texto fim escondido")
        self.assertEqual(f["tarefas"][0]["para_conclusao"], "01/01/2026 10:30")
        self.assertEqual(f["comentarios"], [{"data": "03/01/2026 11:00", "autor": "CICLANO", "texto": "Cliente ligou."}])

    def test_comentarios_em_aba(self):
        html = """<!doctype html><html><body>
         <div class="vj-bloco-info-text-area"><p><strong>Fase: </strong> Inicial</p></div>
         <ul class="nav"><li><a href="#aba-tarefas">Tarefas</a></li><li><a href="#aba-com">Comentários (1)</a></li></ul>
         <div id="aba-tarefas">04/01/2026 08:00 - NAO E COMENTARIO</div>
         <div id="aba-com"><div>05/01/2026 09:00 - BELTRANA</div><div>Retorno do cliente.</div></div>
        </body></html>"""
        f = self.ficha(html)
        self.assertEqual(f["comentarios"], [{"data": "05/01/2026 09:00", "autor": "BELTRANA", "texto": "Retorno do cliente."}])

    def test_tabela_dentro_da_descricao(self):
        # texto colado de e-mail/Word com <table>: as colunas não podem andar
        desc = ("Audiência por vídeo <table><thead><tr><th>Sala</th><th>Senha</th></tr></thead>"
                "<tbody><tr><td>a</td><td>b</td></tr></tbody></table> fim")
        html = HTML_FICHA.replace("Audiência <b>virtual</b>", desc)
        f = self.ficha(html)
        self.assertEqual([t["ci"] for t in f["tarefas"]], ["902", "901"])
        cancelada = f["tarefas"][1]
        self.assertEqual(cancelada["descricao"], "Audiência por vídeo Sala Senha a b fim")
        self.assertEqual(cancelada["comentarios"], "")
        self.assertEqual((cancelada["para_conclusao"], cancelada["limite"]), ("20/02/2026", "21/02/2026"))

    def test_tabela_dentro_de_arquivos_e_comentarios(self):
        html = """<!doctype html><html><body>
         <div class="vj-bloco-info-text-area"><p><strong>Fase: </strong> Inicial</p></div>
         <table><thead><tr><th>Data</th><th>Pasta</th><th>Tipo</th><th>Descrição</th><th>Arquivo</th>
          <th>Tamanho</th></tr></thead>
          <tbody><tr><td>01/03/2026</td><td>Geral</td><td>PDF</td>
           <td>Contrato <table><tr><td>x</td><td>y</td></tr></table></td><td>contrato.pdf</td><td>1 MB</td></tr></tbody></table>
         <table><thead><tr><th>Data / Usuário</th><th>Comentário</th></tr></thead>
          <tbody><tr><td>03/01/2026 11:00 - CICLANO</td><td>Ligou <table><tr><td>p</td><td>q</td></tr></table></td></tr>
          </tbody></table>
        </body></html>"""
        f = self.ficha(html)
        self.assertEqual(f["arquivos"], [{"data": "01/03/2026", "pasta": "Geral", "tipo": "PDF",
                                          "descricao": "Contrato x y", "arquivo": "contrato.pdf"}])
        self.assertEqual(f["comentarios"], [{"data": "03/01/2026 11:00", "autor": "CICLANO", "texto": "Ligou p q"}])

    def test_valor_terminado_em_dois_pontos_nao_e_partido(self):
        html = """<!doctype html><html><body><div class="vj-bloco-info-text-area">
         <p><strong><span>Complemento órgão</span>: </strong> <span>Ver obs:</span></p>
         <p><strong><span>Auxiliares</span>: </strong> <span>FULANO</span><br><span>BELTRANO</span></p>
        </div></body></html>"""
        f = self.ficha(html)
        self.assertEqual(f["campos"]["Complemento órgão"], "Ver obs:")
        self.assertEqual(f["campos"]["Auxiliares"], "FULANO; BELTRANO")

    def test_cidade_e_uf_vazias_no_dom(self):
        html = """<!doctype html><html><body><div class="vj-bloco-info-text-area">
         <p><strong><span>Cliente</span>: </strong> <span>EMPRESA FICTICIA</span></p>
         <p><strong><span>Cidade / UF</span>: </strong> <span></span> / <span></span></p>
        </div></body></html>"""
        f = self.ficha(html)
        self.assertTrue(f["ok"], f["erro"])
        self.assertEqual(f["cidade_uf"], "")

    def test_xpath_de_espera(self):
        # BLOCOS: só conta <p> com valor (fora do rótulo e de .vj-acoes-dados)
        so_rotulos = """<!doctype html><html><body><div class="vj-bloco-info-text-area">
         <p><strong><span>N.° CNJ</span>: </strong> <span></span> <span class="vj-acoes-dados">copiar</span></p>
         <p><strong><span>Cliente</span>: </strong></p></div></body></html>"""
        self.assertEqual(self.contar_xpath(so_rotulos, pf.BLOCOS[1]), 0)
        self.assertGreater(self.contar_xpath(HTML_FICHA, pf.BLOCOS[1]), 5)
        # TAREFAS: linha com tarefa ou "Nenhum registro"; "Carregando..." não conta
        self.assertEqual(self.contar_xpath(HTML_FICHA, pf.TAREFAS[1]), 2)
        self.assertEqual(self.contar_xpath(HTML_SEM_TAREFAS, pf.TAREFAS[1]), 1)
        carregando = HTML_SEM_TAREFAS.replace("Nenhum registro encontrado", "Carregando...")
        self.assertEqual(self.contar_xpath(carregando, pf.TAREFAS[1]), 0)


if __name__ == "__main__":
    unittest.main()
