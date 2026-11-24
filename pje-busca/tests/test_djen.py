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


if __name__ == "__main__":
    unittest.main()
