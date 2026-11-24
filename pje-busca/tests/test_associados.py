"""Nível 3 (processos associados no PJe): comparação com a base, alertas e a leitura da tela com um PJe falso."""
import json
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
FORA = "0000777-77.2025.5.07.0029"  # do VIOS, mas não está no acervo do login


def linhas_vios():
    return [{"ci": "27466", "numero": f"CNJ: {P1}", "cliente": "MM COMERCIO DE CALCADOS LTDA (MATRIZ)",
             "ativa": "Autor: ALINE CRISTINA MACEDO VIEIRA"},
            {"ci": "21045", "numero": f"Cliente DIAMANTECNJ: {P2}", "cliente": "DFA REPRESENTACOES LTDA (MATRIZ)",
             "ativa": "Autor: ROBSON RODRIGUES TEIXEIRA"},
            {"ci": "7", "numero": f"CNJ: {FORA}", "cliente": "OUTRA LTDA", "ativa": "Autor: X"},
            {"ci": "1", "numero": "CNJ: 0000001-11.2026.8.06.0001", "cliente": "OUTRA LTDA", "ativa": "Autor: X"}]


def lido(principais, acervo=(P1, P2), erro=""):
    return {"principais": {n: {"situacao": "ok", "associados": [{"numero": a, "orgao": "2ª Vara do Trabalho de Sobral"}
                                                               for a in assoc], "erro": ""}
                           for n, assoc in principais.items()},
            "acervo": list(acervo) if acervo is not None else None, "total_assoc": len(principais), "erro": erro}


class Rodada(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.est = VE.Estado(Path(self.tmp.name) / "v.sqlite")
        self.addCleanup(self.est.fechar)
        self.est.aplicar(linhas_vios(), True, hoje=date(2026, 11, 1))

    def rodar(self, l, dia, **kw):
        return VA.rodar(self.est, l, hoje=date(2026, 11, dia), **kw)

    def test_base_depois_alerta_so_o_novo(self):
        r1 = self.rodar(lido({P1: [CPS]}), 24)
        self.assertTrue(r1["base_global"])
        self.assertEqual([x["numero"] for x in r1["base"]], [CPS])
        self.assertEqual(r1["novos"], [])
        self.assertEqual(r1["fora_do_acervo"], [FORA])
        self.assertIn("PRIMEIRA RODADA (base)", VA.relatorio(r1))
        self.assertIn("Com o principal NO VIOS (cliente nosso; conferir) (1)", VA.relatorio(r1))
        # o caso real: o principal P2 (já no acervo) ganha o 1º associado -> alerta
        r2 = self.rodar(lido({P1: [CPS], P2: [NOVO]}), 25)
        self.assertFalse(r2["base_global"])
        self.assertEqual([(x["principal"], x["numero"], x["nivel"]) for x in r2["novos"]], [(P2, NOVO, "VERMELHO")])
        self.assertEqual(r2["novos"][0]["principal_ci"], "21045")
        self.assertIn("🔴 VERMELHO · associado NOVO fora do VIOS, com o principal no VIOS (1)", VA.relatorio(r2))
        r3 = self.rodar(lido({P1: [CPS], P2: [NOVO]}), 26)
        self.assertEqual(r3["novos"], [])  # não repete o aviso
        rod = self.est.db.execute("SELECT acervo, verificados, novos, vermelhos, completa, base FROM assoc_rodadas "
                                  "WHERE data = '2026-11-25'").fetchone()
        self.assertEqual(tuple(rod), (2, 2, 1, 1, 1, 0))

    def test_arquivado_no_pje_separado_do_fora_do_acervo(self):
        l = lido({P1: [CPS]})
        l["arquivados"] = [FORA, "0000123-12.2019.5.07.0024"]
        r = self.rodar(l, 24)
        self.assertEqual((r["arquivados_vios"], r["fora_do_acervo"], r["arquivados_total"]), ([FORA], [], 2))
        self.assertIn("ATIVOS no VIOS, mas ARQUIVADOS no PJe (1)", VA.relatorio(r))
        sit = self.est.db.execute("SELECT situacao FROM assoc_principais WHERE numero = ?", (FORA,)).fetchone()[0]
        self.assertEqual(sit, "arquivado_pje")
        self.assertEqual(self.est.db.execute("SELECT arquivados FROM assoc_rodadas").fetchone()[0], 1)

    def test_coluna_arquivados_acrescentada_sem_perder_a_base(self):
        self.est.db.executescript(
            "CREATE TABLE assoc_rodadas (data TEXT PRIMARY KEY, acervo INTEGER, verificados INTEGER, com_associados INTEGER,"
            " fora_acervo INTEGER, erros INTEGER, novos INTEGER, vermelhos INTEGER, completa INTEGER, base INTEGER);"
            "INSERT INTO assoc_rodadas VALUES ('2026-11-24', 358, 60, 60, 97, 0, 0, 0, 1, 1);"
            "CREATE TABLE assoc_associados (principal TEXT, associado TEXT, orgao TEXT, visto_em TEXT, novo INTEGER,"
            " nivel TEXT, PRIMARY KEY (principal, associado));"
            f"INSERT INTO assoc_associados VALUES ('{P1}', '{CPS}', '', '2026-11-24', 0, 'BASE');")
        ea = VA.EstadoAssoc(self.est)
        self.assertFalse(ea.eh_base())                       # a base de 24/11 continua valendo
        self.assertEqual(ea.conhecidos(P1), {CPS})

    def test_processo_que_acabou_de_entrar_no_acervo_vira_base(self):
        self.rodar(lido({P1: [CPS]}, acervo=(P1,)), 24)
        r = self.rodar(lido({P1: [CPS], P2: [NOVO]}, acervo=(P1, P2)), 25)
        self.assertEqual(r["novos"], [])
        self.assertEqual([x["numero"] for x in r["base"]], [NOVO])

    def test_principal_fora_do_vios_e_amarelo(self):
        outro = "0002500-30.2012.5.07.0024"  # no acervo, mas fora da lista do VIOS
        self.rodar(lido({}, acervo=(P1, P2, outro)), 24)
        r = self.rodar(lido({outro: [NOVO]}, acervo=(P1, P2, outro)), 25)
        self.assertEqual([(x["numero"], x["nivel"]) for x in r["novos"]], [(NOVO, "AMARELO")])
        self.assertIn("🟡 AMARELO", VA.relatorio(r))
        self.assertIn("🔴 VERMELHO · associado NOVO fora do VIOS, com o principal no VIOS (0)", VA.relatorio(r))

    def test_associado_que_ja_esta_no_vios_e_informacao(self):
        self.rodar(lido({}), 24)
        r = self.rodar(lido({P1: [P2]}), 25)
        self.assertEqual([x["nivel"] for x in r["novos"]], ["INFO"])

    def test_erro_e_leitura_incompleta(self):
        l = lido({P1: [CPS]})
        l["principais"][P2] = {"situacao": "erro", "associados": [], "erro": "a janela não abriu"}
        r = self.rodar(l, 24)
        self.assertEqual(([e[0] for e in r["erros"]], r["completa"]), ([P2], False))
        r = self.rodar(lido({P1: [CPS]}, acervo=None, erro="a lista não carregou"), 25)
        self.assertFalse(r["completa"])
        self.assertIn("INCOMPLETA", VA.relatorio(r))
        # rodada incompleta não conta como base feita
        self.assertTrue(VA.EstadoAssoc(self.est).eh_base())

    def test_simular_nao_grava(self):
        self.rodar(lido({P1: [CPS]}), 24, simular=True)
        self.assertEqual(self.est.db.execute("SELECT COUNT(*) FROM assoc_associados").fetchone()[0], 0)
        self.assertEqual(self.est.db.execute("SELECT COUNT(*) FROM assoc_rodadas").fetchone()[0], 0)

    def test_esquema_antigo_recomeca(self):
        self.est.db.executescript("DROP TABLE IF EXISTS assoc_rodadas; CREATE TABLE assoc_rodadas (data TEXT, x INTEGER);"
                                  "CREATE TABLE IF NOT EXISTS assoc_principais (numero TEXT PRIMARY KEY, situacao TEXT,"
                                  " qtd INTEGER, verificado_em TEXT, base_feita INTEGER, erro TEXT);"
                                  "INSERT INTO assoc_principais VALUES ('x', 'fora_do_acervo', 0, '', 0, '');")
        ea = VA.EstadoAssoc(self.est)
        self.assertEqual(self.est.db.execute("SELECT COUNT(*) FROM assoc_principais").fetchone()[0], 0)
        self.assertTrue(ea.eh_base())


class PjeFalso:
    """Imita o Acervo Geral: filtro "Processos com Associação", páginas de 10, janela de associados de 5 em 5."""

    def __init__(self, acervo, associados, arquivados=()):
        self.acervo, self.assoc, self.arquivados_lista = list(acervo), dict(associados), list(arquivados)
        self.aba = "acervo"
        self.filtro, self.pagina, self.dialogo, self.pag_dialogo = False, 1, None, 1
        self.abertos = []

    def ir(self, url):
        self.aba, self.pagina, self.filtro = ("arquivados" if url == VA.ARQUIVADOS else "acervo"), 1, False

    def lista(self):
        base = self.arquivados_lista if self.aba == "arquivados" else self.acervo
        return [n for n in base if n in self.assoc] if self.filtro else base

    def js(self, c):
        if "mat-select" in c:
            return "ja"  # já com 100 por página
        if c.startswith("(function(ligar)"):
            ligar = c.rstrip().endswith("(true)")
            mudou = ligar != self.filtro
            self.filtro = ligar
            return json.dumps({"ok": True, "mudou": mudou})
        if "/^primeir/" in c:
            if self.pagina == 1:
                return "ja"
            self.pagina = 1
            return "ok"
        if "pje-paginador" in c and "/^pr[óo]xim/" in c and "linhas" not in c:
            if self.pagina * 10 >= len(self.lista()):
                return "nao"
            self.pagina += 1
            return "ok"
        if "linhas.push" in c:
            lst = self.lista()
            pg = lst[(self.pagina - 1) * 10:self.pagina * 10]
            return json.dumps({"linhas": [{"numero": n, "botao": n in self.assoc} for n in pg],
                               "de": (self.pagina - 1) * 10 + 1 if pg else 0, "ate": (self.pagina - 1) * 10 + len(pg),
                               "total": len(lst), "tem_proximo": self.pagina * 10 < len(lst), "vazio": not pg,
                               "filtro": self.filtro, "dialogo": bool(self.dialogo)})
        if c.startswith("(function(forte)"):
            if not self.dialogo:
                return "fechada"
            self.dialogo = None
            return "esc"
        if "b.click(); return 'ok';" in c and "Processos associados" in c and "function(numero)" in c:
            numero = json.loads(c[c.rindex("(") + 1:c.rindex(")")])
            if numero not in self.lista():
                return "sem_linha"
            if numero not in self.assoc:
                return "sem_botao"
            self.dialogo, self.pag_dialogo = numero, 1
            self.abertos.append(numero)
            return "ok"
        if "function(principal)" in c:
            if not self.dialogo:
                return json.dumps({"aberta": False})
            todos = self.assoc[self.dialogo]
            pg = todos[(self.pag_dialogo - 1) * 5:self.pag_dialogo * 5]
            return json.dumps({"aberta": True, "itens": [{"numero": n, "orgao": "Vara"} for n in pg], "texto": "",
                               "de": (self.pag_dialogo - 1) * 5 + 1, "ate": (self.pag_dialogo - 1) * 5 + len(pg),
                               "total": len(todos), "tem_proxima": self.pag_dialogo * 5 < len(todos)})
        if "/^pr[óo]xim|next/" in c and "b.click()" in c:
            if not self.dialogo or self.pag_dialogo * 5 >= len(self.assoc[self.dialogo]):
                return "nao"
            self.pag_dialogo += 1
            return "ok"
        raise AssertionError("JavaScript inesperado: " + c[:80])


class LerAcervo(unittest.TestCase):
    def test_le_filtro_paginas_janela_e_cobertura(self):
        acervo = [f"00000{i:02d}-11.2025.5.07.0024" for i in range(25)]
        muitos = [f"00010{i:02d}-22.2026.5.07.0024" for i in range(7)]  # 7 associados: 2 páginas na janela
        assoc = {acervo[3]: [CPS], acervo[14]: muitos, acervo[24]: [NOVO]}
        pje = PjeFalso(acervo, assoc)
        pje.pagina = 2  # o PJe guarda a página: tem de voltar para a 1ª
        pje.arquivados_lista = [f"00099{i:02d}-33.2020.5.07.0024" for i in range(13)]
        with mock.patch.object(VA.time, "sleep"):
            r = VA.ler_acervo(pje.js, aviso=lambda *_: None, ir=pje.ir)
        self.assertEqual(r["erro"], "")
        self.assertEqual(sorted(r["principais"]), sorted(assoc))
        self.assertEqual([a["numero"] for a in r["principais"][acervo[14]]["associados"]], muitos)
        self.assertEqual(r["acervo"], acervo)          # cobertura: o acervo inteiro (3 páginas)
        self.assertEqual(r["total_assoc"], 3)
        self.assertEqual(r["arquivados"], pje.arquivados_lista)  # aba Arquivados (2 páginas)
        self.assertFalse(pje.filtro)                   # deixa o acervo sem filtro
        self.assertIsNone(pje.dialogo)                 # nenhuma janela aberta

    def test_lista_que_nao_carrega_vira_erro(self):
        pje = PjeFalso([], {})
        with mock.patch.object(VA.time, "sleep"), mock.patch.object(VA, "_esperar", lambda cond, maximo, passo=0.7: None):
            r = VA.ler_acervo(pje.js, aviso=lambda *_: None)
        self.assertIn("não carregou", r["erro"])
        self.assertIsNone(r["acervo"])


if __name__ == "__main__":
    unittest.main()
