"""Testes da função planilhas (conferência das planilhas do Albi). Só dados fictícios."""
import csv
import os
import shutil
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from funcoes import planilhas
from nucleo import config, vios
from nucleo.modelos import Contexto, Secao

ORELHA = Path(__file__).resolve().parent.parent
FIXTURES = ORELHA / "fixtures"
ALBI = FIXTURES / "planilhas" / "albi"
HOJE = date(2026, 11, 4)

A = "00010011120268060001"   # o VIOS fictício tem (linha com data-processos_id)
B = "00010022220268060001"   # novo (só aparece num <script> do HTML)
C = "00010033320255070002"   # o VIOS fictício tem (CI no link da linha)
E = "00010044420268060001"   # novo (só aparece em option/textarea/value)


def cfg(texto=""):
    pasta = Path(tempfile.mkdtemp())
    env = pasta / ".env"
    env.write_text(texto, encoding="utf-8")
    return config.carregar(env, exigir_login=False, ambiente={})


class Eventos:
    def __init__(self):
        self.lista = []

    def __call__(self, tipo, **dados):
        self.lista.append((tipo, dados))


def contexto(pasta, simulado=False, albi=None, env="", modo="busca"):
    # estes testes são da busca pela tela (modo "busca"); o padrão agora é "url" (TestBuscaPorEndereco)
    env = (f"ORELHA_PLANILHAS_MODO={modo}\n" if modo and "ORELHA_PLANILHAS_MODO" not in env else "") + env
    return Contexto(driver=None if simulado else object(), cfg=cfg(env), hoje=HOJE, emitir=Eventos(),
                    simulado=simulado, fixtures=FIXTURES, saida=pasta / "saida" / HOJE.isoformat(),
                    historico=pasta / "saida" / "historico", chave="planilhas", albi_saida=albi)


def ler_csv(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f, delimiter=";"))


class TestNumeros(unittest.TestCase):
    def test_normalizar_e_formatar(self):
        self.assertEqual(planilhas.normalizar_numero("0001001-11.2026.8.06.0001"), A)
        self.assertEqual(planilhas.normalizar_numero(A), A)
        self.assertEqual(planilhas.normalizar_numero("123456"), "")
        self.assertEqual(planilhas.normalizar_numero(""), "")
        self.assertEqual(planilhas.formatar_cnj(A), "0001001-11.2026.8.06.0001")
        self.assertEqual(planilhas.formatar_cnj("123"), "123")

    def test_rotulo_pasta(self):
        self.assertEqual(planilhas.rotulo_pasta("2026-11-03_101500"), "03/11/2026 10:15")
        self.assertEqual(planilhas.rotulo_pasta("2026-11-03"), "03/11/2026")
        self.assertEqual(planilhas.rotulo_pasta("lote-x"), "lote-x")


class TestCsvAlbi(unittest.TestCase):
    def test_le_o_csv_do_albi(self):
        linhas = planilhas.ler_csv_albi((ALBI / "2026-11-03_101500" / "processos.csv").read_text(encoding="utf-8-sig"))
        self.assertEqual(len(linhas), 5)
        self.assertEqual(linhas[0]["digitos"], A)
        self.assertEqual(linhas[0]["empresa"], "Empresa Fictícia Alfa")
        self.assertEqual(linhas[0]["nome"], "Fulano Exemplo da Silva")
        self.assertEqual(linhas[0]["tribunal"], "TJCE")
        self.assertEqual(linhas[3]["situacao"], "Encerrado")
        self.assertEqual(linhas[4]["digitos"], "")  # fora do padrão CNJ
        self.assertEqual(linhas[4]["numero"], "123456")

    def test_bom_virgula_formula_e_linha_vazia(self):
        texto = "﻿Empresa,Número único,Nome\n'=Empresa Teste,0001001-11.2026.8.06.0001,X\nEmpresa Teste,,Y\n"
        linhas = planilhas.ler_csv_albi(texto)
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["empresa"], "=Empresa Teste")
        self.assertEqual(linhas[0]["digitos"], A)

    def test_sem_coluna_do_numero(self):
        with self.assertRaises(ValueError):
            planilhas.ler_csv_albi("Empresa;Nome\nX;Y\n")
        self.assertEqual(planilhas.ler_csv_albi(""), [])


class TestHtmlVios(unittest.TestCase):
    def setUp(self):
        self.html = (FIXTURES / "planilhas" / "vios_processos.html").read_text(encoding="utf-8")

    def test_acha_os_numeros_das_linhas_com_o_ci(self):
        achados = planilhas.numeros_no_html(self.html, "https://vios.exemplo.invalid/")
        self.assertEqual(achados[A], "https://vios.exemplo.invalid/?pag=sys/processos/processos-vis.php&processos_id=900001")
        self.assertEqual(achados[C], "https://vios.exemplo.invalid/?pag=sys/processos/processos-vis.php&processos_id=900002")
        self.assertIn("00099999920248060001", achados)

    def test_ignora_script_option_textarea_e_valor_do_campo(self):
        achados = planilhas.numeros_no_html(self.html, "https://vios.exemplo.invalid/")
        self.assertNotIn(B, achados)
        self.assertNotIn(E, achados)

    def test_numero_fora_de_linha_usa_o_ci_da_pagina(self):
        html = "<h1>Processo 0001001-11.2026.8.06.0001</h1>"
        url = "https://vios.exemplo.invalid/index.php?pag=sys/processos/processos-vis.php&processos_id=123456"
        achados = planilhas.numeros_no_html(html, "https://vios.exemplo.invalid/", url)
        self.assertTrue(achados[A].endswith("processos_id=123456"))
        self.assertEqual(planilhas.numeros_no_html(html), {A: ""})

    def test_nao_pega_pedaco_de_numero_maior(self):
        self.assertEqual(planilhas.numeros_no_html("<p>9" + A + "</p>"), {})
        self.assertEqual(planilhas.numeros_no_html(""), {})


def linha(numero, empresa="Empresa Teste", nome="Pessoa Teste", pasta="2026-11-03_101500"):
    return {"numero": numero, "digitos": planilhas.normalizar_numero(numero), "empresa": empresa, "nome": nome,
            "tribunal": "TJCE", "situacao": "Em andamento", "pasta": pasta}


class TestConferir(unittest.TestCase):
    def test_resultados_e_juncao(self):
        linhas = [linha(A), linha(B, nome="Pessoa Um"), linha(B, nome="Pessoa Dois"), linha("123"),
                  linha(C), linha(B, empresa="Outra Empresa Teste")]
        conf = planilhas.conferir(linhas, {A: "https://x.invalid/ficha", "999": ""}, {C: "a busca falhou: tempo"})
        por = {(x["empresa"], x["numero"]): x for x in conf}
        self.assertEqual(len(conf), 5)
        self.assertEqual(por[("Empresa Teste", A)]["resultado"], "ja_tem")
        self.assertEqual(por[("Empresa Teste", A)]["link"], "https://x.invalid/ficha")
        self.assertEqual(por[("Empresa Teste", B)]["resultado"], "novo")
        self.assertEqual(por[("Empresa Teste", B)]["nomes"], ["Pessoa Um", "Pessoa Dois"])
        self.assertEqual(por[("Empresa Teste", "123")]["resultado"], "nao_achou")
        self.assertIn("CNJ", por[("Empresa Teste", "123")]["motivo"])
        self.assertEqual(por[("Empresa Teste", C)]["resultado"], "nao_achou")
        self.assertEqual(por[("Outra Empresa Teste", B)]["resultado"], "novo")

    def test_montar_secao(self):
        conf = planilhas.conferir([linha(A, empresa="Zeta Teste"), linha(B, empresa="Zeta Teste"), linha(C, empresa="Alfa Teste"),
                                   linha("123", empresa="")], {A: "https://x.invalid/ficha", C: ""})
        secao = planilhas.montar_secao(conf, 1)
        self.assertIsInstance(secao, Secao)
        self.assertEqual(secao.chave, "planilhas")
        self.assertEqual([i.grupo for i in secao.itens], ["Alfa Teste", "Zeta Teste", "Zeta Teste", "(sem empresa)"])
        self.assertEqual([i.nivel for i in secao.itens], ["info", "atencao", "info", "atencao"])
        self.assertEqual(secao.itens[1].titulo, "0001002-22.2026.8.06.0001")
        self.assertEqual(secao.itens[2].link, "https://x.invalid/ficha")
        self.assertIn("parte: Pessoa Teste", secao.itens[0].detalhe)
        self.assertIn("planilha do Albi de 03/11/2026 10:15", secao.itens[0].detalhe)
        self.assertEqual(secao.numeros, {"pastas": 1, "total": 4, "ja_tem": 2, "novos": 1, "nao_achou": 1})
        self.assertEqual(secao.numeros_seguros(), secao.numeros)
        self.assertIn("1 planilha nova do Albi, 4 processos: 1 novo", secao.resumo)
        self.assertIn("1 sem conferir", secao.resumo)

    def test_secao_vazia(self):
        secao = planilhas.montar_secao([], 0)
        self.assertEqual(secao.resumo, "Nenhuma planilha nova do Albi.")
        self.assertEqual(secao.itens, [])

    def test_csv_do_dia(self):
        pasta = Path(tempfile.mkdtemp())
        conf = planilhas.conferir([linha(A, empresa="=Empresa"), linha(B)], {A: ""})
        caminho = planilhas.escrever_csv_do_dia(pasta / "dia" / "planilhas-2026-11-04.csv", conf)
        self.assertTrue(caminho.read_bytes().startswith(b"\xef\xbb\xbf"))
        linhas = ler_csv(caminho)
        self.assertEqual(linhas[0], ["Processo", "Empresa", "Resultado", "Explicação", "Pasta do Albi"])
        self.assertEqual(linhas[1][:3], ["0001001-11.2026.8.06.0001", "'=Empresa", "ja_tem"])
        self.assertEqual(linhas[2][2], "novo")
        self.assertEqual(linhas[2][4], "2026-11-03_101500")


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp()) / "albi_saida"
        shutil.copytree(ALBI, self.raiz)

    def test_pendentes_e_registro(self):
        csvs = planilhas.csvs_do_albi(self.raiz)
        self.assertEqual([c.parent.name for c in csvs], ["2026-11-03_101500", "2026-11-04_083000"])
        pend = planilhas.pendentes(csvs, {}, HOJE)
        self.assertEqual(len(pend), 2)
        conf = planilhas.conferir([linha(A, pasta="2026-11-03_101500"), linha(B, pasta="2026-11-04_083000")], {},
                                  {B: "a busca falhou"})
        reg, adiadas = planilhas.registrar({"outra": 1}, pend, conf, HOJE)
        self.assertEqual(adiadas, ["2026-11-04_083000"])
        self.assertEqual(reg["outra"], 1)
        self.assertEqual(len(reg["pastas"]), 1)
        self.assertEqual(planilhas.pendentes(csvs, reg, HOJE), [pend[1]])
        # o Albi reescreveu o CSV: confere de novo
        with open(csvs[0], "a", encoding="utf-8") as f:
            f.write("Empresa Teste;X;;;0001004-44.2026.8.06.0001\n")
        self.assertEqual(len(planilhas.pendentes(csvs, reg, HOJE)), 2)

    def test_dias_e_raiz_com_csv(self):
        csvs = planilhas.csvs_do_albi(self.raiz)
        antigo = time.mktime((2026, 9, 1, 12, 0, 0, 0, 0, -1))
        os.utime(csvs[0], (antigo, antigo))
        self.assertEqual(len(planilhas.pendentes(csvs, {}, HOJE, dias=30)), len(csvs) - 1)
        self.assertEqual(len(planilhas.pendentes(csvs, {}, HOJE, dias=0)), len(csvs))
        self.assertEqual(planilhas.csvs_do_albi(self.raiz / "2026-11-03_101500"),
                         [self.raiz / "2026-11-03_101500" / "processos.csv"])
        self.assertEqual(planilhas.csvs_do_albi(self.raiz / "nao-existe"), [])
        self.assertEqual(planilhas.csvs_do_albi(None), [])

    def test_registro_corrompido(self):
        csvs = planilhas.csvs_do_albi(self.raiz)
        self.assertEqual(len(planilhas.pendentes(csvs, [1, 2], HOJE)), 2)
        self.assertEqual(len(planilhas.pendentes(csvs, {"pastas": {str(csvs[0].parent.resolve()): "x"}}, HOJE)), 2)


class TestExecutar(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.raiz = self.pasta / "albi_saida"
        shutil.copytree(ALBI, self.raiz)
        for c in self.raiz.glob("*/processos.csv"):
            os.utime(c, None)  # agora: dentro de ORELHA_PLANILHAS_DIAS

    def test_simulado(self):
        ctx = contexto(self.pasta, simulado=True)
        secao = planilhas.executar(ctx)
        self.assertEqual(secao.erro, "")
        self.assertEqual(secao.numeros, {"pastas": 2, "total": 5, "ja_tem": 2, "novos": 2, "nao_achou": 1})
        self.assertIn("Simulado", " ".join(secao.avisos))
        tipos = [t for t, _ in ctx.emitir.lista]
        self.assertEqual(ctx.emitir.lista[0], ("fase", {"fase": "lendo_planilhas"}))
        planilha = [d for t, d in ctx.emitir.lista if t == "planilha"]
        self.assertEqual(len(planilha), 5)  # A, B, C, E e o número fora do padrão (A da 2ª empresa não repete)
        self.assertEqual([d["indice"] for d in planilha], [1, 2, 3, 4, 5])
        self.assertTrue(all(set(d) == {"resultado", "indice", "total"} and d["total"] == 5 for d in planilha))
        self.assertNotIn("achado", tipos)
        self.assertTrue((ctx.saida / "planilhas-2026-11-04.csv").exists())
        self.assertFalse((ctx.historico / planilhas.REGISTRO).exists())
        novos = {i.titulo for i in secao.itens if i.nivel == "atencao" and "Novo" in i.detalhe}
        self.assertEqual(novos, {"0001002-22.2026.8.06.0001", "0001004-44.2026.8.06.0001"})

    def test_vios_registra_e_nao_confere_duas_vezes(self):
        ctx = contexto(self.pasta, albi=self.raiz)
        self.assertTrue(planilhas.PRECISA_VIOS(ctx))
        procurados = []

        def busca(ctx_, c, d):
            procurados.append(d)
            return {A: "https://x.invalid/ficha"} if d == A else {}
        with mock.patch.object(planilhas, "buscar_numero", side_effect=busca):
            secao = planilhas.executar(ctx)
        self.assertEqual(sorted(procurados), sorted([A, B, C, E]))  # cada número uma vez
        self.assertEqual(secao.numeros["ja_tem"], 1)  # A das duas pastas é um item só (mesma empresa)
        self.assertEqual(secao.numeros["novos"], 3)
        reg = ctx.ler_historico(planilhas.REGISTRO)
        self.assertEqual(len(reg["pastas"]), 2)
        self.assertFalse(planilhas.PRECISA_VIOS(ctx))
        with mock.patch.object(planilhas, "buscar_numero", side_effect=AssertionError("não devia buscar")):
            secao = planilhas.executar(ctx)
        self.assertEqual(secao.resumo, "Nenhuma planilha nova do Albi.")

    def test_busca_que_falha_fica_para_a_proxima(self):
        ctx = contexto(self.pasta, albi=self.raiz)

        def busca(ctx_, c, d):
            if d == E:
                raise vios.ViosErro("elemento não apareceu em 20s: x\nmais detalhes")
            return {}
        with mock.patch.object(planilhas, "buscar_numero", side_effect=busca), self.assertLogs("orelha", "WARNING"):
            secao = planilhas.executar(ctx)
        falhou = [i for i in secao.itens if i.titulo == "0001004-44.2026.8.06.0001"][0]
        self.assertIn("a busca falhou: elemento não apareceu", falhou.detalhe)
        self.assertNotIn("mais detalhes", falhou.detalhe)
        self.assertIn("conferidas de novo", " ".join(secao.avisos))
        reg = ctx.ler_historico(planilhas.REGISTRO)
        self.assertEqual([Path(p).name for p in reg["pastas"]], ["2026-11-03_101500"])
        self.assertTrue(planilhas.PRECISA_VIOS(ctx))

    def test_nenhum_achado_em_muitas_buscas_nao_registra(self):
        ctx = contexto(self.pasta, albi=self.raiz, env="ORELHA_PLANILHAS_SUSPEITO=3\n")
        with mock.patch.object(planilhas, "buscar_numero", return_value={}), self.assertLogs("orelha", "WARNING"):
            secao = planilhas.executar(ctx)
        self.assertEqual(secao.numeros["novos"], 4)
        self.assertIn("resultado suspeito", " ".join(secao.avisos))
        self.assertFalse((ctx.historico / planilhas.REGISTRO).exists())
        self.assertTrue(planilhas.PRECISA_VIOS(ctx))
        # com um achado, o resultado não é suspeito e as pastas entram no registro
        with mock.patch.object(planilhas, "buscar_numero", side_effect=lambda c_, c, d: {A: ""} if d == A else {}):
            planilhas.executar(ctx)
        self.assertFalse(planilhas.PRECISA_VIOS(ctx))

    def test_bloqueio_inativo_sobe(self):
        ctx = contexto(self.pasta, albi=self.raiz)
        with mock.patch.object(planilhas, "buscar_numero", side_effect=vios.BloqueioInativo("parou")):
            with self.assertRaises(vios.BloqueioInativo):
                planilhas.executar(ctx)
        self.assertFalse((ctx.historico / planilhas.REGISTRO).exists())

    def test_modo_lista(self):
        ctx = contexto(self.pasta, albi=self.raiz, env="ORELHA_PLANILHAS_MODO=lista\n")
        with mock.patch.object(planilhas, "ler_lista_vios", return_value={A: "", C: ""}) as lista, \
                mock.patch.object(planilhas, "buscar_numero", side_effect=AssertionError("não devia buscar")):
            secao = planilhas.executar(ctx)
        lista.assert_called_once()
        self.assertEqual(secao.numeros["ja_tem"], 2)

    def test_limite_por_execucao(self):
        ctx = contexto(self.pasta, albi=self.raiz, env="ORELHA_PLANILHAS_MAX=3\n")
        with mock.patch.object(planilhas, "buscar_numero", return_value={}):
            secao = planilhas.executar(ctx)
        self.assertEqual(secao.numeros["pastas"], 1)
        self.assertIn("ORELHA_PLANILHAS_MAX", " ".join(secao.avisos))
        self.assertTrue(planilhas.PRECISA_VIOS(ctx))  # a 2ª pasta ficou para a próxima

    def test_sem_pasta_do_albi(self):
        ctx = contexto(self.pasta, albi=self.pasta / "nao-existe")
        self.assertFalse(planilhas.PRECISA_VIOS(ctx))
        secao = planilhas.executar(ctx)
        self.assertEqual(secao.resumo, "Nenhuma planilha nova do Albi.")
        self.assertEqual(secao.numeros["total"], 0)

    def test_config_invalida(self):
        ctx = contexto(self.pasta, albi=self.raiz, env="ORELHA_PLANILHAS_MODO=outro\n")
        with self.assertRaises(config.ConfigErro):
            planilhas.executar(ctx)


class TestLeituraVios(unittest.TestCase):
    """A parte Selenium, com o navegador trocado por um falso (nada abre de verdade)."""

    def test_busca_por_endereco(self):
        ctx = contexto(Path(tempfile.mkdtemp()), env="ORELHA_PLANILHAS_BUSCA_URL=?pag=sys/busca.php&q={numero}&d={digitos}\n")
        ctx.driver = mock.Mock(current_url="https://vios.exemplo.invalid/index.php?pag=sys/processos/processos-vis.php&processos_id=777")
        c = planilhas._config(ctx.cfg)
        with mock.patch.object(vios, "abrir") as abrir, \
                mock.patch.object(vios, "html", return_value="<h1>0001001-11.2026.8.06.0001</h1>"):
            achados = planilhas.buscar_numero(ctx, c, A)
        abrir.assert_called_once_with(ctx, "?pag=sys/busca.php&q=0001001-11.2026.8.06.0001&d=" + A)
        self.assertTrue(achados[A].endswith("processos_id=777"))

    def test_busca_pelo_formulario_do_topo(self):
        ctx = contexto(Path(tempfile.mkdtemp()), env="ORELHA_PLANILHAS_BUSCA_FORMATO=digitos\n")
        campo = mock.Mock()
        campo.get_attribute.side_effect = lambda n: "busca_texto" if n == "name" else ""
        ctx.driver = mock.Mock(current_url="https://vios.exemplo.invalid/index.php?pag=sys/x.php")
        ctx.driver.execute_script.return_value = {"nome": "busca_tipo", "valor": "nro"}
        c = planilhas._config(ctx.cfg)
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar", return_value=campo), \
                mock.patch.object(vios, "enviar_pesquisa") as enviar, mock.patch.object(vios, "html", return_value=""), \
                mock.patch.object(planilhas, "_barrados", return_value=[]):
            self.assertEqual(planilhas.buscar_numero(ctx, c, A), {})
        enviar.assert_called_once()
        self.assertEqual(enviar.call_args.args[2], {"busca_texto": A, "busca_tipo": "nro"})
        # sem a opção "Nro do Processo" na tela: erro claro (vira "não deu para conferir")
        ctx.driver.execute_script.return_value = None
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar", return_value=campo):
            with self.assertRaises(vios.ViosErro):
                planilhas.buscar_numero(ctx, c, A)

    def test_busca_com_pedido_barrado_ou_sem_resultado_nao_vira_novo(self):
        ctx = contexto(Path(tempfile.mkdtemp()), env="ORELHA_PLANILHAS_BUSCA_URL=?pag=sys/busca.php&q={numero}\n")
        ctx.driver = mock.Mock(current_url="https://vios.exemplo.invalid/index.php?pag=sys/busca.php")
        c = planilhas._config(ctx.cfg)
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "html", return_value="<p>nada</p>"), \
                mock.patch.object(planilhas, "_barrados", return_value=["XHR POST sys/busca/resultado.php"]):
            with self.assertRaisesRegex(vios.ViosErro, "barrou 1 pedido"):
                planilhas.buscar_numero(ctx, c, A)
        ctx = contexto(Path(tempfile.mkdtemp()), env="ORELHA_PLANILHAS_BUSCA_URL=?pag=sys/busca.php&q={numero}\n"
                                                    "ORELHA_PLANILHAS_BUSCA_RESULTADO=css:#resultado\n")
        ctx.driver = mock.Mock(current_url="https://vios.exemplo.invalid/index.php?pag=sys/busca.php")
        c = planilhas._config(ctx.cfg)
        with mock.patch.object(vios, "abrir"), mock.patch.object(vios, "esperar_varios", return_value=[]), \
                mock.patch.object(planilhas, "_barrados", return_value=[]):
            with self.assertRaisesRegex(vios.ViosErro, "área de resultado"):
                planilhas.buscar_numero(ctx, c, A)


if __name__ == "__main__":
    unittest.main()


class TestBuscaPorEndereco(unittest.TestCase):
    """Padrão: a busca do topo pelo endereço (formulário GET), um número por vez, sem abrir telas."""

    def ctx(self):
        return contexto(Path(tempfile.mkdtemp()), modo="")

    def test_endereco(self):
        url = planilhas.URL_BUSCA_NUMERO.format(numero=planilhas.formatar_cnj("00001019020268060001"))
        for trecho in ("campo_pesquisa_selecionado=nro_proc", "pesq[filtros][]=todos", "Pesq=Pesquisar",
                       "pesq[busca]=0000101-90.2026.8.06.0001"):
            self.assertIn(trecho, url)

    def test_achou_e_nao_achou(self):
        ctx = self.ctx()
        com = ('<title>Vios Jurídico - Processos</title><table id="processos-lista"><tbody>'
               '<tr id="processos-lista_linha_0"><td data-id="processos-lista_linha_0_processos_id">'
               '<a href="?pag=sys/processos/processos-vis.php&amp;processos_id=77">77</a></td>'
               '<td data-id="processos-lista_linha_0_nro_proc_html">0000101-90.2026.8.06.0001</td></tr></tbody></table>')
        with mock.patch.object(planilhas.vios, "buscar_get", return_value=com):
            self.assertIn("00001019020268060001", planilhas.buscar_numero_url(ctx, "00001019020268060001"))
        with mock.patch.object(planilhas.vios, "buscar_get", return_value="<title>Vios Jurídico - Processos</title>"):
            self.assertEqual(planilhas.buscar_numero_url(ctx, "00001019020268060001"), {})
        with mock.patch.object(planilhas.vios, "buscar_get", return_value="<title>Login</title>"):
            with self.assertRaises(planilhas.vios.ViosErro):   # sessão caída: nunca vira "novo"
                planilhas.buscar_numero_url(ctx, "00001019020268060001")

    def test_padrao_e_url(self):
        self.assertEqual(planilhas._config(self.ctx().cfg)["modo"], "url")
