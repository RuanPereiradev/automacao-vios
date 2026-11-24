"""Nível 3 (processos associados no PJe): comparação com a base, alertas e a leitura da tela com um PJe falso."""
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import vigia_associados as VA  # noqa: E402
import vigia_estado as VE  # noqa: E402

P1 = "0002754-04.2025.5.07.0038"  # principal real (MM)
CPS = "0001368-02.2026.5.07.0038"  # cumprimento associado a ele (23/11/2026)
P2 = "0000064-49.2022.5.07.0024"
NOVO = "0009999-11.2026.5.07.0024"


def linhas():
    return [{"ci": "27466", "numero": f"CNJ: {P1}", "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)",
             "ativa": "Autor: ALINE CRISTINA MACEDO VIEIRA"},
            {"ci": "21045", "numero": f"Cliente DIAMANTECNJ: {P2}", "cliente": "DFA REPRESENTACOES LTDA (MATRIZ)",
             "ativa": "Autor: ROBSON RODRIGUES TEIXEIRA"},
            {"ci": "1", "numero": "CNJ: 0000001-11.2026.8.06.0001", "cliente": "OUTRA LTDA", "ativa": "Autor: X"}]


class Rodada(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.est = VE.Estado(Path(self.tmp.name) / "v.sqlite")
        self.addCleanup(self.est.fechar)
        self.est.aplicar(linhas(), True, hoje=date(2026, 11, 1))

    def rodar(self, respostas, dia, **kw):
        def ler(numero):
            r = respostas.get(numero, [])
            if isinstance(r, dict):
                return r
            return {"situacao": "ok", "associados": [{"numero": n, "orgao": "2ª Vara do Trabalho de Sobral"} for n in r],
                    "erro": ""}
        return VA.rodar(self.est, ler, hoje=date(2026, 11, dia), pausa=0, aviso=lambda *_: None, **kw)

    def test_so_principais_do_trt7(self):
        self.assertEqual(VA.EstadoAssoc(self.est).principais(), sorted([P1, P2]))

    def test_base_depois_alerta_so_o_novo(self):
        r1 = self.rodar({P1: [CPS]}, 24)
        self.assertEqual([x["numero"] for x in r1["base"]], [CPS])           # já existia: base, sem alerta
        self.assertEqual(r1["novos"], [])
        self.assertIn("BASE (1ª leitura", VA.relatorio(r1))
        r2 = self.rodar({P1: [CPS], P2: [NOVO]}, 25)
        self.assertEqual([(x["principal"], x["numero"], x["nivel"]) for x in r2["novos"]], [(P2, NOVO, "VERMELHO")])
        self.assertEqual(r2["novos"][0]["principal_ci"], "21045")
        self.assertIn("🔴 VERMELHO · associado NOVO fora do VIOS (1)", VA.relatorio(r2))
        r3 = self.rodar({P1: [CPS], P2: [NOVO]}, 26)
        self.assertEqual(r3["novos"], [])                                      # não repete o aviso
        rod = self.est.db.execute("SELECT verificados, com_associados, novos, vermelhos, completa FROM assoc_rodadas "
                                  "WHERE data = '2026-11-25'").fetchone()
        self.assertEqual(tuple(rod), (2, 2, 1, 1, 1))

    def test_associado_que_ja_esta_no_vios_e_informacao(self):
        self.rodar({}, 24)
        r = self.rodar({P1: [P2]}, 25)
        self.assertEqual([x["nivel"] for x in r["novos"]], ["INFO"])

    def test_fora_do_acervo_e_erro_nao_viram_base(self):
        r = self.rodar({P1: {"situacao": "fora_do_acervo", "associados": [], "erro": ""},
                        P2: {"situacao": "erro", "associados": [], "erro": "a janela não abriu"}}, 24)
        self.assertEqual((r["fora_do_acervo"], [e[0] for e in r["erros"]], r["completa"]), ([P1], [P2], False))
        r2 = self.rodar({P1: [CPS], P2: [NOVO]}, 25)
        self.assertEqual(sorted(x["numero"] for x in r2["base"]), [CPS, NOVO])  # 1ª leitura boa = base

    def test_para_com_sessao_caida_e_com_erros_seguidos(self):
        r = self.rodar({}, 24, parar=lambda: "a sessão do PJe caiu")
        self.assertEqual((r["interrompido"], r["verificados"], r["completa"]), ("a sessão do PJe caiu", 0, False))
        with mock.patch.object(VA, "ERROS_SEGUIDOS", 1):
            r = self.rodar({P1: {"situacao": "erro", "associados": [], "erro": "x"},
                            P2: {"situacao": "erro", "associados": [], "erro": "x"}}, 24)
        self.assertEqual(len(r["erros"]), 1)
        self.assertIn("erros seguidos", r["interrompido"])

    def test_simular_nao_grava(self):
        self.rodar({P1: [CPS]}, 24, simular=True)
        self.assertEqual(self.est.db.execute("SELECT COUNT(*) FROM assoc_associados").fetchone()[0], 0)


class PjeFalso:
    """Imita as respostas do JavaScript do Acervo Geral (o que importa é a ordem dos passos)."""

    def __init__(self, linha=True, botao=True, itens=(CPS,), total=None):
        self.linha, self.botao, self.itens, self.total = linha, botao, list(itens), total
        self.aberta, self.pesquisado, self.cliques = False, None, []

    def pesquisar(self, numero):
        self.pesquisado = numero

    def js(self, codigo):
        if codigo.startswith(VA.JS_FECHAR[:30]):
            if not self.aberta:
                return "fechada"
            self.aberta = False
            return "esc"
        if "Detalhes do Processo" in codigo:
            clicar = codigo.rstrip().endswith("true)")
            if not self.linha:
                return json.dumps({"linha": False, "vazio": True, "carregando": False})
            if clicar and self.botao:
                self.aberta = True
                self.cliques.append(self.pesquisado)
            return json.dumps({"linha": True, "botao": self.botao, "clicou": clicar and self.botao})
        if "tem_proxima" in codigo:
            if not self.aberta:
                return json.dumps({"aberta": False})
            total = self.total or len(self.itens)
            return json.dumps({"aberta": True, "itens": [{"numero": n, "orgao": "2ª Vara"} for n in self.itens],
                               "texto": "", "de": len(self.itens), "total": total, "tem_proxima": False})
        raise AssertionError("JavaScript inesperado: " + codigo[:60])


class LerNoPje(unittest.TestCase):
    def ler(self, pje):
        with mock.patch.object(VA.time, "sleep"):
            return VA.ler_no_pje(1, 2, P1, pje.js, pje.pesquisar, maximo_busca=1)

    def test_le_os_associados_e_fecha(self):
        pje = PjeFalso()
        r = self.ler(pje)
        self.assertEqual((r["situacao"], [a["numero"] for a in r["associados"]]), ("ok", [CPS]))
        self.assertEqual((pje.pesquisado, pje.cliques, pje.aberta), (P1, [P1], False))

    def test_sem_botao_e_zero_associados(self):
        r = self.ler(PjeFalso(botao=False))
        self.assertEqual((r["situacao"], r["associados"]), ("ok", []))

    def test_fora_do_acervo(self):
        self.assertEqual(self.ler(PjeFalso(linha=False))["situacao"], "fora_do_acervo")

    def test_lista_incompleta_e_erro(self):
        r = self.ler(PjeFalso(total=3))
        self.assertEqual(r["situacao"], "erro")
        self.assertIn("li 1 de 3", r["erro"])

    def test_javascript_bem_formado(self):
        for codigo in (VA.JS_LINHA % (json.dumps(P1), "true"), VA.JS_LER % json.dumps(P1), VA.JS_FECHAR % "true",
                       VA.JS_PROXIMA):
            self.assertNotIn("%s", codigo)
            self.assertEqual(codigo.count("("), codigo.count(")"))
        self.assertTrue(re.search(r"aria-label=\"Processos associados\"", VA.JS_LINHA))


if __name__ == "__main__":
    unittest.main()
