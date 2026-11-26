"""Testes da verificação pelo DJEN: python3 -m unittest discover -s tests (dentro de pje-busca/)."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import vigia_djen as VD  # noqa: E402
import vigia_estado as VE  # noqa: E402

# publicações reais (resumidas) da MM COMERCIO no DJEN, 23/11/2026
PUB = [
    {"numeroprocessocommascara": "0002754-04.2025.5.07.0038", "nomeClasse": "RECURSO ORDINÁRIO TRABALHISTA",
     "data_disponibilizacao": "2026-11-13", "tipoComunicacao": "Intimação", "nomeOrgao": "1ª Turma"},
    {"numeroprocessocommascara": "0001368-02.2026.5.07.0038", "nomeClasse": "CUMPRIMENTO PROVISÓRIO DE SENTENÇA",
     "data_disponibilizacao": "2026-09-24", "tipoComunicacao": "Intimação", "nomeOrgao": "2ª Vara do Trabalho de Sobral"},
    {"numeroprocessocommascara": "0001368-02.2026.5.07.0038", "nomeClasse": "CUMPRIMENTO PROVISÓRIO DE SENTENÇA",
     "data_disponibilizacao": "2026-07-31", "tipoComunicacao": "Lista de distribuição",
     "nomeOrgao": "2ª Vara do Trabalho de Sobral"},
    {"numeroprocessocommascara": "0002754-04.2025.5.07.0038", "nomeClasse": "AÇÃO TRABALHISTA - RITO ORDINÁRIO",
     "data_disponibilizacao": "2025-11-24", "tipoComunicacao": "Lista de distribuição",
     "nomeOrgao": "2ª Vara do Trabalho de Sobral"},
]
NOVA = {"numeroprocessocommascara": "0009999-11.2026.5.07.0038", "nomeClasse": "AÇÃO TRABALHISTA - RITO SUMARÍSSIMO",
        "data_disponibilizacao": "2026-11-20", "tipoComunicacao": "Lista de distribuição", "nomeOrgao": "2ª VT Sobral"}


class Puras(unittest.TestCase):
    def test_nome_busca(self):
        self.assertEqual(VD.nome_busca("MM COMERCIO DE CALCADOS LTDA (MATRIZ)"), "MM COMERCIO DE CALCADOS LTDA")
        self.assertEqual(VD.nome_busca("M G MEDEIROS SERVICOS ADMINISTRATIVOS LTDA (MATRIZ): PRESTADORA"),
                         "M G MEDEIROS SERVICOS ADMINISTRATIVOS LTDA")
        self.assertEqual(VD.nome_busca("ROMEU BOZZO JUNIOR - ME ( CLIENTE EMPRESA )"), "ROMEU BOZZO JUNIOR - ME")

    def test_resumir_pega_a_primeira_publicacao(self):
        r = VD.resumir(PUB)
        self.assertEqual(r["0001368-02.2026.5.07.0038"]["primeira_publicacao"], "2026-07-31")
        self.assertEqual(r["0001368-02.2026.5.07.0038"]["tipo"], "Lista de distribuição")
        self.assertEqual(r["0002754-04.2025.5.07.0038"]["classe"], "AÇÃO TRABALHISTA - RITO ORDINÁRIO")

    def test_classificar(self):
        r = VD.resumir(PUB)
        self.assertEqual(VD.classificar("0001368-02.2026.5.07.0038", r["0001368-02.2026.5.07.0038"], set(), set()),
                         "VERMELHO")
        self.assertIsNone(VD.classificar("0002754-04.2025.5.07.0038", r["0002754-04.2025.5.07.0038"],
                                         {"0002754-04.2025.5.07.0038"}, set()))
        self.assertEqual(VD.classificar("x", {"classe": "AÇÃO TRABALHISTA - RITO SUMARÍSSIMO"}, set(), set()), "AMARELO")
        self.assertEqual(VD.classificar("x", {"classe": "EXECUÇÃO DE TÍTULO EXTRAJUDICIAL"}, set(), set()), "VERMELHO")
        # ação de cumprimento (sindicato x convenção coletiva) não é cumprimento de sentença
        self.assertEqual(VD.classificar("x", {"classe": "AçãO DE CUMPRIMENTO"}, set(), set()), "AMARELO")
        self.assertEqual(VD.classificar("x", {"classe": "CUMPRIMENTO DE SENTENÇA"}, set(), set()), "VERMELHO")

    def test_nome_do_tribunal_e_polo(self):
        itens = [{"destinatarios": [{"nome": "COPCEL - COMERCIO DE PO E CERA DE CARNAUBA LTDA - EPP", "polo": "P"},
                                    {"nome": "FRANCISCO GLADSTONE COSTA DE AGUIAR", "polo": "A"}]}]
        vios = "COPCEL - TRANSPORTE & COMERCIO DE GRAO LTDA (MATRIZ)"
        self.assertEqual(VD.nomes_do_tribunal(vios, itens), ["COPCEL - COMERCIO DE PO E CERA DE CARNAUBA LTDA - EPP"])
        self.assertEqual(VD.polo_cliente(itens[0], [vios]), "P")
        consig = {"destinatarios": [{"nome": "CRISTIANO VIEIRA DE ARAUJO", "polo": "A"},
                                    {"nome": "MARIA DA SILVA", "polo": "P"}]}
        self.assertEqual(VD.polo_cliente(consig, ["CRISTIANO VIEIRA DE ARAUJO (MATRIZ)"]), "A")
        self.assertIsNone(VD.polo_cliente({"destinatarios": []}, [vios]))
        self.assertFalse(VD.parecido("SUPERMERCADO DOIS IRMAOS IPU LTDA", "SUPERMERCADO PAULO BELO LTDA"))

    def test_consultar_pagina(self):
        paginas = {1: {"count": 150, "items": [PUB[0]] * 100}, 2: {"count": 150, "items": [PUB[1]] * 50}}
        vistos = []

        def abrir(url):
            vistos.append(url)
            return paginas[int(url.split("pagina=")[1])]
        itens = VD.consultar("MM COMERCIO", abrir=abrir, pausa=0)
        self.assertEqual(len(itens), 150)
        self.assertIn("nomeParte=MM+COMERCIO", vistos[0])
        self.assertIn("siglaTribunal=TRT7", vistos[0])


class Rodada(unittest.TestCase):
    """Caso real: antes do bloqueio o VIOS só tinha o principal 0002754; o DJEN já mostrava o CumPrSe 0001368."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.est = VE.Estado(Path(self.tmp.name) / "v.sqlite")
        principal = {"ci": "1", "numero": "CNJ: 0002754-04.2025.5.07.0038",
                     "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)", "ativa": "Autor: ALINE"}
        self.est.aplicar([principal], True, hoje=date(2026, 7, 1))

    def tearDown(self):
        self.est.fechar()
        self.tmp.cleanup()

    def test_base_lista_fora_do_vios_e_depois_alerta_so_o_novo(self):
        r1 = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=lambda n: PUB, pausa=0)
        self.assertTrue(r1["base"])
        self.assertEqual([x["numero"] for x in r1["fora_do_vios"]], ["0001368-02.2026.5.07.0038"])
        self.assertIn("CUMPRIMENTO DE SENTENÇA / EXECUÇÃO fora do VIOS (1)", VD.relatorio(r1))
        r2 = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 11, 21), consulta=lambda n: PUB + [NOVA], pausa=0)
        self.assertFalse(r2["base"])
        self.assertEqual(r2["vermelhos"], [])
        self.assertEqual([x["numero"] for x in r2["amarelos"]], ["0009999-11.2026.5.07.0038"])

    def test_cumprimento_novo_depois_da_base_e_vermelho(self):
        VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [PUB[0], PUB[3]], pausa=0)  # base sem o CumPrSe
        r = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 31), consulta=lambda n: PUB, pausa=0)
        self.assertEqual([x["numero"] for x in r["vermelhos"]], ["0001368-02.2026.5.07.0038"])
        txt = VD.relatorio(r)
        self.assertIn("🔴 VERMELHO", txt)
        self.assertIn("1ª publicação 2026-07-31 (Lista de distribuição)", txt)
        r3 = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=lambda n: PUB, pausa=0)
        self.assertEqual(r3["vermelhos"], [])  # não repete o aviso

    def test_cliente_autor_e_ignorado(self):
        VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [], pausa=0)
        consig = dict(NOVA, nomeClasse="CONSIGNAÇÃO EM PAGAMENTO",
                      destinatarios=[{"nome": "MM COMERCIO DE CALCADOS LTDA", "polo": "A"}])
        r = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=lambda n: [consig], pausa=0)
        self.assertEqual(r["amarelos"], [])
        self.assertEqual(r["autor"], 1)

    def test_calibracao_com_nome_novo_vira_auditoria(self):
        VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [], pausa=0)
        nome_trib = "MM COMERCIO DE CALCADOS EIRELI"
        dest = [{"destinatarios": [{"nome": nome_trib, "polo": "P"}]}]
        consultas = []

        def busca(nome):
            consultas.append(nome)
            return [PUB[2]] if nome == nome_trib else []
        r = VD.rodar(self.est, consulta_numero=lambda n: dest, hoje=date(2026, 8, 15), consulta=busca, pausa=0)
        self.assertIn(nome_trib, consultas)
        self.assertEqual(r["calibradas"], [("MM COMERCIO DE CALCADOS LTDA (MATRIZ)", [nome_trib])])
        self.assertEqual(r["vermelhos"], [])                       # 1ª busca com o nome novo: auditoria
        self.assertEqual([x["numero"] for x in r["fora_do_vios"]], ["0001368-02.2026.5.07.0038"])
        self.assertIn("AUDITORIA", VD.relatorio(r))
        r2 = VD.rodar(self.est, consulta_numero=lambda n: dest, hoje=date(2026, 8, 16), consulta=lambda n: [NOVA] if n == nome_trib else [], pausa=0)
        self.assertEqual([x["numero"] for x in r2["amarelos"]], ["0009999-11.2026.5.07.0038"])  # depois, alerta normal

    def test_erro_e_sem_publicacao(self):
        def falha(nome):
            raise VD.DjenErro("HTTP 503")
        r = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=falha, pausa=0, simular=True)
        self.assertEqual(len(r["erros"]), 1)
        r = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=lambda n: [], pausa=0, simular=True)
        self.assertEqual(r["sem_publicacao"], ["MM COMERCIO DE CALCADOS LTDA"])

    def test_nome_conferido_pela_equipe_vira_busca_e_auditoria(self):
        chave = "MM COMERCIO DE CALCADOS LTDA (MATRIZ)"
        VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [], pausa=0)
        linha = self.est.db.execute("SELECT data, publicacoes, nomes FROM djen_consultas WHERE empresa = ?", (chave,)).fetchone()
        self.assertEqual((linha[0], linha[1]), ("2026-07-02", 0))           # sem publicação fica registrado
        correto = "MM CALCADOS EIRELI"
        arq = Path(self.tmp.name) / "nomes_conferidos.json"
        arq.write_text('{"%s": {"situacao": "nome_corrigido", "nomes": ["  MM CALCADOS   EIRELI "]}}' % chave, encoding="utf-8")
        manuais = VD.nomes_conferidos(arq)
        self.assertEqual(manuais, {chave: [correto]})
        consultas = []

        def busca(nome):
            consultas.append(nome)
            return [PUB[2]] if nome == correto else []
        r = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 3), consulta=busca, pausa=0, manuais=manuais)
        self.assertIn(correto, consultas)
        self.assertEqual(r["vermelhos"], [])                                 # 1ª busca com o nome novo: auditoria
        self.assertEqual([x["numero"] for x in r["fora_do_vios"]], ["0001368-02.2026.5.07.0038"])
        self.assertIn("NOMES CONFERIDOS pela equipe", VD.relatorio(r))
        self.assertEqual(self.est.db.execute("SELECT publicacoes FROM djen_consultas WHERE empresa = ?", (chave,)).fetchone()[0], 1)
        r2 = VD.rodar(self.est, consulta_numero=lambda n: [], hoje=date(2026, 7, 4), consulta=lambda n: [NOVA] if n == correto else [],
                      pausa=0, manuais=manuais)
        self.assertEqual([x["numero"] for x in r2["amarelos"]], ["0009999-11.2026.5.07.0038"])  # depois, alerta normal

    def test_nomes_conferidos_arquivo_ruim(self):
        arq = Path(self.tmp.name) / "x.json"
        self.assertEqual(VD.nomes_conferidos(arq), {})
        arq.write_text("não é json", encoding="utf-8")
        self.assertEqual(VD.nomes_conferidos(arq), {})
        arq.write_text('{"A": {"nomes": ["ab", "OK NOME"]}, "B": {"situacao": "sem_processo"}}', encoding="utf-8")
        self.assertEqual(VD.nomes_conferidos(arq), {"A": ["OK NOME"]})


# publicações reais (resumidas) dos cumprimentos da DFA no DJEN, conferidas em 24/11/2026
CPS_CITA = [{"texto": "CumPrSe 0001772-66.2024.5.07.0024 REQUERENTE: ROBSON RODRIGUES TEIXEIRA ... autos principais "
                      "0000064-49.2022.5.07.0024",
             "destinatarios": [{"nome": "ROBSON RODRIGUES TEIXEIRA", "polo": "A"},
                               {"nome": "DFA REPRESENTACOES LTDA - EPP", "polo": "P"}]}]
CPS_SEM_NUMERO = [{"texto": "CumPrSe 0001226-95.2026.5.07.0038 REQUERENTE: ANTONIO KELSON FERREIRA CARVALHO",
                   "destinatarios": [{"nome": "ANTONIO KELSON FERREIRA CARVALHO", "polo": "A"},
                                     {"nome": "DFA DISTRIBUICAO E LOGISTICA LTDA", "polo": "P"}]}]
VIOS = [{"numero": "0000064-49.2022.5.07.0024", "ci": "21045", "empresa": "DFA REPRESENTACOES LTDA (MATRIZ)",
         "autor": "ROBSON RODRIGUES TEIXEIRA", "advogado": "ADV 1"},
        {"numero": "0000743-70.2023.5.07.0038", "ci": "21042", "empresa": "DFA DISTRIBUICAO E LOGISTICA LTDA (MATRIZ)",
         "autor": "Autor: ANTONIO KELSON FERREIRA CARVALHO", "advogado": "ADV 1"},
        {"numero": "0009000-10.2024.5.07.0024", "ci": "9", "empresa": "OUTRA", "autor": "ANTONIO KELSON FERREIRA CARVALHO",
         "advogado": ""}]


class Principal(unittest.TestCase):
    def test_citado_na_publicacao(self):
        r = VD.achar_principal("0001772-66.2024.5.07.0024", CPS_CITA, VIOS)
        self.assertEqual((r["principal"], r["ci"]), ("0000064-49.2022.5.07.0024", "21045"))
        self.assertEqual(r["como"], "citado na publicação e mesmo exequente")

    def test_mesmo_exequente_prefere_mesma_vara(self):
        r = VD.achar_principal("0001226-95.2026.5.07.0038", CPS_SEM_NUMERO, VIOS)
        self.assertEqual((r["principal"], r["ci"]), ("0000743-70.2023.5.07.0038", "21042"))
        self.assertTrue(r["como"].startswith("mesmo exequente e mesma vara"))
        self.assertIn("0009000-10.2024.5.07.0024", r["como"])        # avisa que há outro com o mesmo exequente
        self.assertEqual(r["exequente"], "ANTONIO KELSON FERREIRA CARVALHO")

    def test_nao_achado(self):
        r = VD.achar_principal("0001226-95.2026.5.07.0038", CPS_SEM_NUMERO, VIOS[:1])
        self.assertEqual((r["principal"], r["ci"]), (None, ""))
        r = VD.achar_principal("0001772-66.2024.5.07.0024", CPS_CITA, [])
        self.assertEqual(r["principal"], "0000064-49.2022.5.07.0024")
        self.assertIn("não está no VIOS", r["como"])

    def test_rodada_liga_o_principal_do_cumprimento(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        est = VE.Estado(Path(tmp.name) / "v.sqlite")
        self.addCleanup(est.fechar)
        principal = {"ci": "27466", "numero": "CNJ: 0002754-04.2025.5.07.0038",
                     "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)", "ativa": "Autor: ALINE CRISTINA MACEDO VIEIRA"}
        est.aplicar([principal], True, hoje=date(2026, 7, 1))
        VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [PUB[0], PUB[3]], pausa=0)
        pubs_cps = [{"texto": "CumPrSe 0001368-02.2026.5.07.0038 REQUERENTE: ALINE CRISTINA MACEDO VIEIRA",
                     "destinatarios": [{"nome": "ALINE CRISTINA MACEDO VIEIRA", "polo": "A"}]}]
        r = VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 7, 31), consulta=lambda n: PUB, pausa=0,
                     consulta_principal=lambda n: pubs_cps if n == "0001368-02.2026.5.07.0038" else [])
        self.assertEqual([(x["numero"], x["principal"], x["ci"]) for x in r["principais"]],
                         [("0001368-02.2026.5.07.0038", "0002754-04.2025.5.07.0038", "27466")])
        self.assertIn("NO VIOS (CI 27466", VD.relatorio(r))
        r2 = VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 8, 1), consulta=lambda n: PUB, pausa=0,
                      consulta_principal=lambda n: self.fail("não deveria consultar de novo"),
                      consulta_andamentos=lambda n: [])
        self.assertEqual(r2["principais"], [])                        # já achado: não consulta de novo


    def test_siglas_dos_trts(self):
        self.assertEqual((VD.sigla_trt("5.22"), VD.sigla_trt("5.07"), VD.sigla_trt("5.00"), VD.sigla_trt("8.06")),
                         ("TRT22", "TRT7", "", ""))
        self.assertEqual((VD.codigo_trt("TRT7"), VD.codigo_trt("trt22"), VD.codigo_trt("TST")), ("5.07", "5.22", ""))

    def test_outros_trts_base_e_depois_alerta(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        est = VE.Estado(Path(tmp.name) / "v.sqlite")
        self.addCleanup(est.fechar)
        linhas = [{"ci": "1", "numero": "CNJ: 0002754-04.2025.5.07.0038", "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)"},
                  {"ci": "2", "numero": "CNJ: 0000100-10.2025.5.22.0101", "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)"}]
        est.aplicar(linhas, True, hoje=date(2026, 7, 1))
        antigo_pi = {"numeroprocessocommascara": "0000500-50.2024.5.22.0101", "nomeClasse": "CUMPRIMENTO DE SENTENÇA",
                     "data_disponibilizacao": "2024-05-02", "tipoComunicacao": "Intimação", "nomeOrgao": "1ª VT Teresina"}
        novo_pi = dict(antigo_pi, numeroprocessocommascara="0000777-77.2026.5.22.0101", data_disponibilizacao="2026-12-01")
        outro_ramo = dict(antigo_pi, numeroprocessocommascara="0000888-88.2026.8.06.0074")
        buscas = []

        def outro(nome, sigla, lista):
            buscas.append(sigla)
            return lista
        VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 7, 2), consulta=lambda n: [], pausa=0)
        # ^ base geral só no TRT7 (como era antes); abaixo, a 1ª busca no TRT22
        r = VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 7, 3), consulta=lambda n: [], pausa=0,
                     consulta_outro=lambda n, s: outro(n, s, [antigo_pi, outro_ramo]),
                     consulta_principal=lambda n: [], consulta_andamentos=lambda n: [])
        self.assertEqual(set(buscas), {"TRT22"})                                  # só o TRT em que tem processo
        self.assertEqual(r["vermelhos"], [])                                       # 1ª busca no TRT22 = base
        self.assertEqual([x["numero"] for x in r["fora_do_vios"]], ["0000500-50.2024.5.22.0101"])  # sem o TJCE
        r2 = VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 12, 2), consulta=lambda n: [], pausa=0,
                      consulta_outro=lambda n, s: outro(n, s, [antigo_pi, novo_pi]),
                      consulta_principal=lambda n: [], consulta_andamentos=lambda n: [])
        self.assertEqual([x["numero"] for x in r2["vermelhos"]], ["0000777-77.2026.5.22.0101"])
        r3 = VD.rodar(est, consulta_numero=lambda n: [], hoje=date(2026, 12, 3), consulta=lambda n: [], pausa=0,
                      consulta_principal=lambda n: [], consulta_andamentos=lambda n: [])   # sem consulta_outro: só TRT7
        self.assertEqual(r3["vermelhos"], [])

    def test_andamentos_sem_repeticao_e_gravados(self):
        pub = lambda dest, polo, extra="": {  # noqa: E731
            "data_disponibilizacao": "2026-11-16", "tipoComunicacao": "Intimação", "tipoDocumento": "Notificação",
            "nomeOrgao": "2ª Vara do Trabalho de Sobral",
            "texto": "<p>DESPACHO homologo os cálculos.</p> Intimado(s) / Citado(s) - " + dest + extra,
            "destinatarios": [{"nome": dest, "polo": polo}]}
        itens = [pub("EXEQUENTE X", "A"), pub("EMPRESA Y", "P"),
                 {"data_disponibilizacao": "2026-07-06", "tipoComunicacao": "Lista de distribuição",
                  "texto": "Processo distribuído", "destinatarios": []}]
        a = VD.andamentos(itens)
        self.assertEqual([x["data"] for x in a], ["2026-11-16", "2026-07-06"])   # mesma decisão vira uma só
        self.assertEqual(a[0]["texto"], "DESPACHO homologo os cálculos.")
        self.assertEqual(a[0]["destinatarios"], "EXEQUENTE X (A); EMPRESA Y (P)")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        est = VE.Estado(Path(tmp.name) / "v.sqlite")
        self.addCleanup(est.fechar)
        ed = VD.EstadoDjen(est)
        ed.gravar("0001226-95.2026.5.07.0038", "DFA", {"classe": "CUMPRIMENTO PROVISÓRIO DE SENTENÇA", "orgao": "",
                  "primeira_publicacao": "2026-07-06", "tipo": ""}, "2026-11-24", "VERMELHO")
        r = VD.atualizar_andamentos(ed, "2026-11-26", lambda n: itens, pausa=0)
        self.assertEqual(r, [{"numero": "0001226-95.2026.5.07.0038", "andamentos": 2, "erro": ""}])
        VD.atualizar_andamentos(ed, "2026-11-27", lambda n: itens, pausa=0)   # de novo: não duplica
        self.assertEqual(est.db.execute("SELECT COUNT(*) FROM djen_andamentos").fetchone()[0], 2)
        r = VD.atualizar_andamentos(ed, "2026-11-27", lambda n: (_ for _ in ()).throw(OSError("fora do ar")), pausa=0)
        self.assertEqual(r[0]["erro"], "fora do ar")


if __name__ == "__main__":
    unittest.main()
