"""Testes do monitor de processos (src/monitor.py): python3 -m unittest discover -s tests (dentro de pje-busca/).
Sem rede e sem Chrome: o DJEN, o DataJud e o PJe são de mentira."""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import monitor as M  # noqa: E402

CAB = ('"Vínculo";"CI";"Área";"Pasta Interna";"Pasta Cliente";"Data do encerramento";"Data da Ação / Distribuição";'
       '"Contrato do cliente";"Processo";"Situação do Processo";"Ação";"Etiquetas";"Número";"UF";'
       '"Comarcas / Tribunais / Órgãos Adm.";"Complemento Órgão";"Órgão Julgador (Vara/Camara)";'
       '"Tipo de órgão julgador (vara/camara)";"Advogado responsável";"Aux.";"Parte ativa";"Parte passiva";'
       '"Terceiro(s)";"Cliente";"Polo do cliente";"Observações (síntese do processo)";"Última edição";"Valor da ação";'
       '"Valor da ação atualizado";"Objeto";"Motivo de Encerramento";"Vida útil"')


def linha(vinculo, ci, numero, vara, cliente, acao="RECLAMAÇÃO TRABALHISTA"):
    return (f'"{vinculo}";="{ci}";"Trabalhista";"";"";"";"15/04/2004";"";"TRABALHISTA";"ATIVO";"{acao}";"";'
            f'"{numero}";"CE";"{vara}";"";="0";="0";"RONEELY FEITOSA";"TAMI";"Autor: {cliente}";"Réu: MUNICÍPIO";"";'
            f'"{cliente}";"Parte Ativa";"";"20/10/2024";"1,00";"1,00";"";"";"1 ano";')


CSV = "\n".join([
    CAB,
    linha("PROCESSO PRINCIPAL", "1", "CNJ: 0000921-40.2009.8.06.0053", "2ª Vara da Comarca de Camocim/CE", "EXPEDITO"),
    linha("APENSO", "2", "CNJ: 0000921-40.2009.8.06.0053", "2ª Vara da Comarca de Camocim/CE", "EXPEDITO APENSO"),
    linha("PROCESSO PRINCIPAL", "3", "CNJ: 0001877-04.2019.5.07.0029", "Vara Única do Trabalho de Tianguá/CE", "MARCELO"),
    linha("PROCESSO PRINCIPAL", "4", "1.° Grau: 0014029-09.2026.4.05.81032.° Grau: 3002030-75.2024.8.06.0000", "19ª Vara Federal- Sobral/CE", "PEDRO"),
    linha("PROCESSO PRINCIPAL", "5", "CNJ: 0002403-31.2022.8.06.0000", "Vara Única da Comarca de Uruoca/CE", "ANA"),
    linha("PROCESSO PRINCIPAL", "6", "CNJ: 1002875-16.2019.4.01.4002Outros: 3000758-75.2026.8.06.0000", "JEF Parnaíba", "FRANCISCO"),
    linha("PROCESSO PRINCIPAL", "7", "Outros: NR Nº 594257039", "INSS", "SEM CNJ"),
    '"Total: 861";;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;',
]).encode("latin-1")


class Puras(unittest.TestCase):
    def test_tribunal_de(self):
        self.assertEqual(M.tribunal_de("0000921-40.2009.8.06.0053"), ("TJCE", "1", "legado"))
        self.assertEqual(M.tribunal_de("0002403-31.2022.8.06.0000"), ("TJCE", "2", "legado"))
        self.assertEqual(M.tribunal_de("0001877-04.2019.5.07.0029"), ("TRT7", "1", "kz"))
        self.assertEqual(M.tribunal_de("0004024-51.2023.5.07.0000"), ("TRT7", "2", "api"))  # 2º grau: só API
        self.assertEqual(M.tribunal_de("0014029-09.2026.4.05.8103"), ("TRF5", "1", "legado"))
        self.assertEqual(M.tribunal_de("1002875-16.2019.4.01.4002"), ("TRF1", "1", "api"))
        self.assertEqual(M.tribunal_de("0000123-38.2016.8.18.0046"), ("TJPI", "1", "api"))
        self.assertEqual(M.tribunal_de("0000003-81.2015.5.22.0101"), ("TRT22", "1", "kz"))

    def test_datas(self):
        self.assertEqual(M.data_iso("23 jun 2025"), "2025-06-23")
        self.assertEqual(M.data_iso("25 nov. 2026"), "2026-11-25")
        self.assertEqual(M.data_iso("07 fev 2025"), "2025-02-07")
        self.assertEqual(M.data_iso("2026-11-25T19:07:54.780Z"), "2026-11-25")
        self.assertEqual(M.data_iso("26/11/2026"), "2026-11-26")
        self.assertEqual(M.data_iso("ontem"), "")

    def test_ler_csv_do_vios(self):
        procs, sem = M.ler_csv(CSV)
        self.assertEqual(sem, 2)  # "Outros: NR..." e "Total:"
        por = {p["numero"]: p for p in procs}
        self.assertEqual(len(por), 5)  # o apenso com o mesmo número não duplica
        self.assertEqual(por["0000921-40.2009.8.06.0053"]["cliente"], "EXPEDITO")  # fica o principal
        self.assertEqual(por["0000921-40.2009.8.06.0053"]["ci"], "1")
        self.assertEqual(por["0001877-04.2019.5.07.0029"]["vara"], "Vara Única do Trabalho de Tianguá/CE")
        self.assertEqual(por["0001877-04.2019.5.07.0029"]["situacao"], "ATIVO")

    def test_csv_sem_coluna_numero(self):
        with self.assertRaises(M.MonitorErro):
            M.ler_csv(b'"a";"b"\n"1";"2"\n')

    def test_ultimo_datajud(self):
        r = {"hits": {"hits": [
            {"_source": {"grau": "G1", "orgaoJulgador": {"nome": "2ª Vara"}, "movimentos": [
                {"nome": "Conclusão", "dataHora": "2026-11-17T15:10:00.000Z"},
                {"nome": "Decisão", "dataHora": "2026-11-26T08:15:00.000Z",
                 "complementosTabelados": [{"nome": "tipo de decisão", "descricao": "outras"}]}]}},
            {"_source": {"grau": "G2", "movimentos": [{"nome": "Distribuição", "dataHora": "2025-01-02T10:00:00Z"}]}}]}}
        u = M.ultimo_datajud(r)
        self.assertEqual((u["data"], u["hora"], u["qtd"], u["grau"]), ("2026-11-26", "08:15", 3, "G1"))
        self.assertEqual(u["mov"], "Decisão (tipo de decisão: outras)")
        self.assertIsNone(M.ultimo_datajud({"hits": {"hits": []}}))

    def test_escolher_documento(self):
        itens = [{"mov": "CONCLUSOS", "docs": []}, {"mov": "DECISÃO", "docs": ["262594296 - Decisão"]}]
        it, doc = M.escolher_documento(itens)
        self.assertEqual((it["mov"], doc), ("DECISÃO", "262594296"))
        it, doc = M.escolher_documento([{"mov": "Certidão - 6f45fd1", "doc": "6f45fd1"}])
        self.assertEqual(doc, "6f45fd1")
        self.assertEqual(M.escolher_documento([{"mov": "x", "docs": []}]), (None, ""))

    def test_base_de(self):
        self.assertEqual(M.base_de("https://pje.tjce.jus.br/pje1grau/Painel/painel_usuario/advogado.seam"),
                         ("https://pje.tjce.jus.br", "https://pje.tjce.jus.br/pje1grau"))
        self.assertEqual(M.base_de("https://pje.trt7.jus.br/pjekz/painel/usuario-externo")[1],
                         "https://pje.trt7.jus.br/pjekz")


def pub(numero, data, texto, tipo="Intimação"):
    return {"numeroprocessocommascara": numero, "data_disponibilizacao": data, "tipoComunicacao": tipo,
            "nomeOrgao": "Vara", "texto": texto, "destinatarios": []}


class ComBanco(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.est = M.Estado(Path(self.tmp.name) / "monitor.sqlite")
        procs, _ = M.ler_csv(CSV)
        self.est.importar(procs, date(2026, 11, 26))

    def tearDown(self):
        self.est.fechar()
        self.tmp.cleanup()

    def test_importar_marca_quem_saiu(self):
        procs, _ = M.ler_csv(CSV)
        r = self.est.importar([p for p in procs if p["numero"] != "0001877-04.2019.5.07.0029"], date(2026, 11, 27))
        self.assertEqual(r["sairam"], ["0001877-04.2019.5.07.0029"])
        self.assertNotIn("0001877-04.2019.5.07.0029", self.est.numeros())
        r = self.est.importar(procs, date(2026, 11, 28))  # voltou
        self.assertIn("0001877-04.2019.5.07.0029", self.est.numeros())
        self.assertEqual(r["novos"], 0)

    def test_djen_base_e_novidade(self):
        n = "0000921-40.2009.8.06.0053"
        import vigia_djen as VD
        self.assertFalse(self.est.gravar_djen(n, VD.andamentos([pub(n, "2026-03-13", "DESPACHO antigo")]), "2026-11-26"))
        self.assertFalse(self.est.gravar_djen(n, VD.andamentos([pub(n, "2026-03-13", "DESPACHO antigo")]), "2026-11-27"))
        novo = VD.andamentos([pub(n, "2026-11-27", "DECISÃO nova"), pub(n, "2026-03-13", "DESPACHO antigo")])
        self.assertTrue(self.est.gravar_djen(n, novo, "2026-11-28"))
        p = self.est.processo(n)
        self.assertEqual((p["djen_data"], p["djen_texto"], p["djen_qtd"], p["prioridade"], p["novidade_fonte"]),
                         ("2026-11-27", "DECISÃO nova", 2, 1, "DJEN"))

    def test_fila_tribunal_prioridade_e_sistema(self):
        fila = [p["numero"] for p in self.est.fila_tribunal(10)]
        self.assertNotIn("1002875-16.2019.4.01.4002", fila)  # TRF1: só API
        self.assertIn("0002403-31.2022.8.06.0000", fila)  # TJCE 2º grau tem leitor
        self.est.gravar_tribunal("0000921-40.2009.8.06.0053", {"ok": True, "itens": [{"data": "2026-11-26", "mov": "A"}]},
                                 "2026-11-26")
        self.est.db.execute("UPDATE mon_estado SET prioridade = 1 WHERE numero = '0014029-09.2026.4.05.8103'")
        fila = [p["numero"] for p in self.est.fila_tribunal(10)]
        self.assertEqual(fila[0], "0014029-09.2026.4.05.8103")  # novidade primeiro
        self.assertEqual(fila[-1], "0000921-40.2009.8.06.0053")  # o já lido por último

    def test_tribunal_base_novidade_e_teor_mantido(self):
        n = "0000921-40.2009.8.06.0053"
        lido = {"ok": True, "itens": [{"data": "2026-11-26", "hora": "08:15", "mov": "DECISÃO", "docs": ["1 - Decisão"]}],
                "teor": "Homologo os cálculos", "teor_de": "1 - Decisão (2026-11-26)"}
        self.assertFalse(self.est.gravar_tribunal(n, lido, "2026-11-26"))  # 1ª leitura é a base
        self.assertFalse(self.est.gravar_tribunal(n, dict(lido, teor=None), "2026-11-27"))  # nada mudou
        self.assertEqual(self.est.processo(n)["trib_teor"], "Homologo os cálculos")  # teor mantido
        outra = {"ok": True, "itens": [{"data": "2026-11-28", "hora": "10:00", "mov": "EXPEDIÇÃO DE RPV", "docs": []}]}
        self.assertTrue(self.est.gravar_tribunal(n, outra, "2026-11-28"))
        self.assertEqual(self.est.processo(n)["novidade_fonte"], "Tribunal")
        self.assertFalse(self.est.gravar_tribunal(n, {"ok": False, "erro": "sessão caiu"}, "2026-11-29"))
        self.assertEqual(self.est.processo(n)["trib_erro"], "sessão caiu")

    def test_rodar_api(self):
        n1, n2 = "0000921-40.2009.8.06.0053", "0001877-04.2019.5.07.0029"
        chamadas = {"oab": [], "num": [], "dj": []}

        def oab(num, uf, inicio, fim, pausa=0):
            chamadas["oab"].append((num, uf, str(inicio), str(fim)))
            return [pub(n1, "2026-11-25", "DECISÃO"), pub("9999999-99.2026.8.06.0001", "2026-11-25", "outro")]

        def por_numero(n):
            chamadas["num"].append(n)
            return [pub(n, "2026-11-25", "DECISÃO")] if n == n1 else []

        def datajud(n, sigla, chave):
            chamadas["dj"].append((n, sigla))
            if n == n2:
                raise M.MonitorErro("HTTP 500")
            return {"hits": {"hits": [{"_source": {"movimentos": [{"nome": "Conclusão", "dataHora": "2026-11-20T10:00:00Z"}]}}]}}

        cfg = {"MONITOR_OABS": "23104/CE", "MONITOR_DJEN_POR_DIA": "3", "MONITOR_DATAJUD_POR_DIA": "10"}
        res = M.rodar_api(self.est, cfg, hoje=date(2026, 11, 26), djen_oab=oab, djen_numero=por_numero, datajud=datajud,
                          pausa=0, aviso=lambda m: None)
        self.assertEqual(chamadas["oab"], [("23104", "CE", "2026-11-19", "2026-11-26")])
        self.assertEqual((res["oab_publicacoes"], res["oab_processos"], res["fora_da_lista"]), (2, 1, 1))
        self.assertEqual(res["djen"], 3)  # rodízio de 3, sem repetir o que veio pela OAB
        self.assertEqual(chamadas["num"].count(n1), 1)
        self.assertEqual(len(chamadas["dj"]), 5)
        self.assertEqual((chamadas["dj"][0][1] in ("TJCE", "TRT7", "TRF5", "TRF1")), True)
        self.assertEqual(self.est.processo(n1)["djen_texto"], "DECISÃO")
        self.assertEqual(self.est.processo(n2)["dj_erro"], "HTTP 500")
        self.assertEqual(self.est.config("djen_oab_ate"), "2026-11-26")
        self.assertIn("DataJud: 4", M.relatorio(res, "api").replace("DataJud: 4", "DataJud: 4"))
        # no dia seguinte, a OAB pega desde o dia anterior à última rodada
        M.rodar_api(self.est, cfg, hoje=date(2026, 11, 27), djen_oab=oab, djen_numero=por_numero, datajud=datajud,
                    pausa=0, aviso=lambda m: None)
        self.assertEqual(chamadas["oab"][-1][2:], ("2026-11-25", "2026-11-27"))

    def test_rodar_api_carteira_vazia(self):
        with tempfile.TemporaryDirectory() as d:
            est = M.Estado(Path(d) / "x.sqlite")
            with self.assertRaises(M.MonitorErro):
                M.rodar_api(est, {}, djen_oab=lambda *a, **k: [], datajud=lambda *a: {}, pausa=0)
            est.fechar()


class PjeFalso:
    """Imita as respostas dos JavaScripts do monitor nas duas telas do PJe (legado e novo)."""

    def __init__(self, tipo, achar=True, arquivado=False, teor=True, cai=False):
        self.tipo, self.achar, self.arquivado, self.teor, self.cai = tipo, achar, arquivado, teor, cai
        self.endereco, self.idas, self.clicou_doc = "", [], None

    def ir(self, u):
        self.idas.append(u)
        self.endereco = u

    def url(self):
        return "https://pje.tjce.jus.br/pje1grau/login.seam" if self.cai else self.endereco

    def js(self, c):
        if "getElementById('fPP:searchProcessos') ? 'ok'" in c:
            return "" if self.cai else "ok"
        if c.startswith(M.JS_LEG_PESQUISAR):
            return json.dumps({"ok": True})
        if c.startswith(M.JS_LEG_RESULTADO):
            if not self.achar:
                return json.dumps({"estado": "vazio"})
            return json.dumps({"estado": "achou", "ultima": "Proferidas outras decisões"})
        if c == M.JS_POPUP:
            return "/pje1grau/Processo/ConsultaProcesso/Detalhe/x.seam?id=1" if self.tipo == "legado" else "/pjekz/processo/9/detalhe"
        if c == M.JS_LEG_TIMELINE:
            return json.dumps({"ok": True, "itens": [
                {"data": "26 nov 2026", "hora": "08:15", "mov": "PROFERIDAS OUTRAS DECISÕES", "docs": ["262594296 - Decisão"]},
                {"data": "17 nov 2026", "hora": "15:10", "mov": "CONCLUSOS", "docs": []}]})
        if c.startswith(M.JS_TEOR_BAIXAR):
            self.baixou = c
            return "ok"
        if c == M.JS_TEOR_LER:
            return json.dumps({"ok": True, "texto": "DECISÃO Homologo" if self.teor else "§PDF"})
        if c.startswith(M.JS_KZ_ACERVO):
            if "arquivados" in self.endereco:
                return json.dumps({"estado": "achou" if self.arquivado else "vazio"})
            return json.dumps({"estado": "achou" if self.achar else "vazio"})
        if c == M.JS_KZ_TIMELINE:
            return json.dumps({"ok": True, "itens": [{"data": "11 nov. 2026", "hora": "08:41",
                                                       "mov": "Certidão(Certidão de arquivamento) - 6f45fd1", "doc": "6f45fd1"}]})
        if c.startswith(M.JS_KZ_ABRIR_DOC):
            self.clicou_doc = c
            return "ok"
        if c.startswith(M.JS_KZ_LER_DOC):
            return json.dumps({"pronto": True, "texto": "CERTIDÃO apto ao arquivamento"})
        return ""


def leitor(pje, tipo, url="https://pje.tjce.jus.br/pje1grau/Painel/x.seam", **kw):
    return M.Leitor(tipo, url, js=pje.js, ir=pje.ir, url=pje.url, dormir=lambda s: None, **kw)


class Leitores(unittest.TestCase):
    def test_legado(self):
        pje = PjeFalso("legado")
        r = leitor(pje, "legado").ler("0000921-40.2009.8.06.0053")
        self.assertTrue(r["ok"])
        self.assertEqual(pje.idas[0], "https://pje.tjce.jus.br/pje1grau/Processo/ConsultaProcesso/listView.seam")
        self.assertEqual(pje.idas[1], "https://pje.tjce.jus.br/pje1grau/Processo/ConsultaProcesso/Detalhe/x.seam?id=1")
        self.assertEqual(r["itens"][0]["data"], "2026-11-26")
        self.assertEqual(r["teor"], "DECISÃO Homologo")
        self.assertIn("262594296 - Decisão (2026-11-26)", r["teor_de"])
        self.assertIn("/pje1grau/seam/resource/rest/pje-legacy/documento/download/262594296", pje.baixou)

    def test_legado_pdf_e_sem_teor(self):
        r = leitor(PjeFalso("legado", teor=False), "legado").ler("0000921-40.2009.8.06.0053")
        self.assertEqual(r["teor"], "")
        self.assertIn("PDF", r["teor_de"])
        r = leitor(PjeFalso("legado"), "legado", ler_teor=False).ler("0000921-40.2009.8.06.0053")
        self.assertIsNone(r["teor"])

    def test_legado_nao_encontrado(self):
        r = leitor(PjeFalso("legado", achar=False), "legado").ler("0000921-40.2009.8.06.0053")
        self.assertFalse(r["ok"])
        self.assertIn("não encontrado", r["erro"])

    def test_legado_sessao_caiu(self):
        pje = PjeFalso("legado", cai=True)
        lei = M.Leitor("legado", "https://pje.tjce.jus.br/pje1grau/Painel/x.seam", js=pje.js, ir=pje.ir, url=pje.url,
                       dormir=lambda s: None, relogio=iter(range(0, 10000, 5)).__next__)
        r = lei.ler("0000921-40.2009.8.06.0053")
        self.assertEqual((r["ok"], r["erro"]), (False, "sessão do PJe caiu"))
        self.assertTrue(lei.sessao_caiu())

    def test_kz_acervo_e_arquivados(self):
        url = "https://pje.trt7.jus.br/pjekz/painel/usuario-externo"
        pje = PjeFalso("kz")
        r = leitor(pje, "kz", url=url).ler("0001877-04.2019.5.07.0029")
        self.assertTrue(r["ok"])
        self.assertEqual(pje.idas[0], "https://pje.trt7.jus.br/pjekz/painel/usuario-externo/acervo-geral/0001877-04.2019.5.07.0029")
        self.assertEqual(pje.idas[1], "https://pje.trt7.jus.br/pjekz/processo/9/detalhe")
        self.assertEqual((r["teor"], r["itens"][0]["data"]), ("CERTIDÃO apto ao arquivamento", "2026-11-11"))
        pje = PjeFalso("kz", achar=False, arquivado=True)
        r = leitor(pje, "kz", url=url).ler("0002294-10.2026.5.07.0029")
        self.assertTrue(r["ok"])
        self.assertIn("/arquivados/0002294-10.2026.5.07.0029", pje.idas[1])
        r = leitor(PjeFalso("kz", achar=False), "kz", url=url).ler("0002294-10.2026.5.07.0029")
        self.assertIn("fora do Acervo Geral", r["erro"])


class RodarTribunal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.est = M.Estado(Path(self.tmp.name) / "monitor.sqlite")
        procs, _ = M.ler_csv(CSV)
        self.est.importar(procs, date(2026, 11, 26))

    def tearDown(self):
        self.est.fechar()
        self.tmp.cleanup()

    def test_um_portal_por_vez_e_fecha_as_abas(self):
        entradas, fechadas = [], []

        def entrar(portal, tipo):
            entradas.append((portal, tipo))
            pje = PjeFalso(tipo)
            url = "https://pje.trt7.jus.br/pjekz/painel" if tipo == "kz" else "https://pje.tjce.jus.br/pje1grau/Painel/x"
            return portal, leitor(pje, tipo, url=url)

        res = M.rodar_tribunal(self.est, {}, entrar, hoje=date(2026, 11, 26), pausa=0, aviso=lambda m: None,
                               fechar=fechadas.append)
        self.assertEqual([e[0] for e in entradas],
                         ["TJCE(PJE) - 1º Grau", "TJCE(PJE) - 2º Grau", "TRF5(PJE) - 1º Grau", "TRT7CE - 1º Grau"])
        self.assertEqual(fechadas, [e[0] for e in entradas])
        self.assertEqual((res["lidos"], res["fila"], len(res["erros"])), (4, 4, 0))
        self.assertEqual(self.est.processo("0001877-04.2019.5.07.0029")["trib_teor"], "CERTIDÃO apto ao arquivamento")
        self.assertIn("Lidos: 4 de 4", M.relatorio(res, "tribunal"))

    def test_login_falha_pula_o_portal(self):
        def entrar(portal, tipo):
            if portal.startswith("TJCE"):
                raise RuntimeError("o Loy Trust está sem sessão")
            return portal, leitor(PjeFalso(tipo), tipo, url="https://pje.trt7.jus.br/pjekz/painel")

        res = M.rodar_tribunal(self.est, {}, entrar, hoje=date(2026, 11, 26), pausa=0, aviso=lambda m: None)
        self.assertEqual(res["portais"]["TJCE(PJE) - 1º Grau"]["login"], "o Loy Trust está sem sessão")
        self.assertEqual(res["lidos"], 2)  # TRF5 e TRT7

    def test_so_um_processo(self):
        def entrar(portal, tipo):
            return portal, leitor(PjeFalso(tipo), tipo)
        res = M.rodar_tribunal(self.est, {}, entrar, pausa=0, aviso=lambda m: None,
                               numeros=["0000921-40.2009.8.06.0053"])
        self.assertEqual((res["fila"], res["lidos"]), (1, 1))
        with self.assertRaises(M.MonitorErro):
            M.rodar_tribunal(self.est, {}, entrar, pausa=0, aviso=lambda m: None, numeros=["1002875-16.2019.4.01.4002"])


if __name__ == "__main__":
    unittest.main()
