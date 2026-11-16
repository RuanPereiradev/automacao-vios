import unittest
from datetime import date

from consulta import PASTA, fases
from consulta.fases import DESCONHECIDA, IGNORAR
from consulta.tests.html import ficha, previ, tarefa
from funcoes import parados

HOJE = date(2026, 11, 16)
MAPA = fases.carregar_mapa()


def ler(*linhas, info=None):
    return parados.ler_tarefas_html(ficha(list(linhas), info=info))


def decidir(*linhas, segredo=False, info=None):
    return fases.decidir(ler(*linhas, info=info), HOJE, MAPA, segredo)


class TestTipoBase(unittest.TestCase):
    def test_tira_parenteses_cidade_e_ano(self):
        casos = {
            "ACOMPANHAR MOB (PREVIDENCIÁRIO)- SOBRAL 2026": "ACOMPANHAR MOB",
            "ACOMPANHAR MOB (PREVIDENCIÁRIO) - CAMOCIM 2026": "ACOMPANHAR MOB",
            "AUDIÊNCIA (PREVIDENCIÁRIO) TIANGUÁ 2026": "AUDIENCIA",
            "PRESTAÇÃO DE CONTAS (FINANCEIRO) (PREVIDENCIÁRIO)- EMPRESA 2026": "PRESTACAO DE CONTAS",
            "ELABORAR SUBSTABELECIMENTO (/B2C) (PREVIDENCIÁRIO)- JIJOCA 2026": "ELABORAR SUBSTABELECIMENTO",
            "DESPACHAR PROCESSO (CÍVEL) 2026": "DESPACHAR PROCESSO",
            "ACOMPANHAMENTO (COMERCIAL)- PROCESSO 2026": "ACOMPANHAMENTO",
            "RECEBIMENTO CÍVEL JUDICIAL (FINANCEIRO) 2026": "RECEBIMENTO CIVEL JUDICIAL",
            "CADASTRAR CONTRATO (B2B) 2026": "CADASTRAR CONTRATO",
            "ANALISAR PROCESSO": "ANALISAR PROCESSO",
        }
        for nome, base in casos.items():
            with self.subTest(nome=nome):
                self.assertEqual(fases.tipo_base(nome), base)

    def test_vale_para_todas_as_areas(self):
        self.assertEqual(MAPA.codigo("AUDIÊNCIA UNA (TRABALHISTA) 2026"), "aguardando_audiencia")
        self.assertEqual(MAPA.codigo("ANALISAR EXIGÊNCIA (PREVIDENCIÁRIO)- SOBRAL 2026"), "exigencia_inss")
        self.assertEqual(MAPA.codigo("TIPO QUE NINGUEM CADASTROU (CÍVEL) 2026"), DESCONHECIDA)


EXEMPLOS_REAIS = {
    "DESPACHAR PROCESSO (CÍVEL) 2026": IGNORAR,
    "ACOMPANHAMENTO (COMERCIAL)- PROCESSO 2026": IGNORAR,
    "MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES (CÍVEL) 2026": "em_recurso",
    "PROTOCOLAR EMBARGOS DE DECLARAÇÃO/RECURSO/CONTRARRAZÕES (CÍVEL) 2026": "em_recurso",
    "RECEBIMENTO CÍVEL JUDICIAL (FINANCEIRO) 2026": IGNORAR,
    "CADASTRAR CONTRATO (B2B) 2026": IGNORAR,
}


class TestMapaCobreOCatalogo(unittest.TestCase):
    def tipos(self, arquivo):
        return [l.strip() for l in (PASTA / arquivo).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]

    def test_exemplos_reais_de_uma_ficha_civel(self):
        for nome, esperado in EXEMPLOS_REAIS.items():
            with self.subTest(nome=nome):
                self.assertEqual(MAPA.codigo(nome), esperado)

    def test_todos_os_551_tipos_resolvem(self):
        from collections import Counter
        tipos = self.tipos("tipos-todos.txt")
        self.assertEqual(len(tipos), 551)
        validos = set(fases.FASES) | {IGNORAR}
        contagem = Counter(MAPA.codigo(t) for t in tipos)
        self.assertLessEqual(set(contagem), validos)
        print("\ntipos por código:", dict(contagem.most_common()))
        # a maioria tem de ter destino claro; desconhecida é a exceção
        self.assertLess(contagem[DESCONHECIDA] / len(tipos), 0.05)

    def test_catalogo_do_previdenciario_continua_resolvendo(self):
        tipos = self.tipos("tipos-previdenciario.txt")
        self.assertGreater(len(tipos), 100)
        for base in tipos:
            nome_real = f"{base} (PREVIDENCIÁRIO)- SOBRAL 2026"
            with self.subTest(base=base):
                self.assertIn(MAPA.codigo(nome_real), set(fases.FASES) | {IGNORAR})
                # tem entrada explícita no mapa (exata, prefixo ou regra), não só o "não achei"
                base_n = fases.tipo_base(base)
                explicito = base_n in MAPA.tipos or any(base_n.startswith(p + " ") for p, _ in MAPA.prefixos) \
                    or any(r.search(fases.sem_acento(nome_real)) for r, _ in MAPA.regras)
                self.assertTrue(explicito, f"{base} não está no mapa")

    def test_comunicacao_interna_e_ignorada(self):
        for base in ("AVISAR AUDIÊNCIA", "RETORNO AO CLIENTE MOB", "LEMBRAR AUDIÊNCIA", "INFORMAR AUDIÊNCIA",
                     "PROSPECT", "PLANEJAMENTO", "RECEBIMENTO (FINANCEIRO)", "PRESTAÇÃO DE CONTAS (FINANCEIRO)"):
            with self.subTest(base=base):
                self.assertEqual(MAPA.codigo(previ(base)), IGNORAR)

    def test_codigos_do_yaml_sao_da_lista_fechada(self):
        usados = set(MAPA.tipos.values()) | {c for _, c in MAPA.prefixos} | {c for _, c in MAPA.regras}
        self.assertLessEqual(usados, set(fases.FASES) | {IGNORAR})

    def test_yaml_com_codigo_inventado_ou_regex_ruim_e_recusado(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / "m.yaml"
            arq.write_text('tipos:\n  "X": fase_que_nao_existe\n', encoding="utf-8")
            with self.assertRaises(fases.MapaErro):
                fases.carregar_mapa(arq)
            arq.write_text('regras:\n  - {padrao: "(", fase: ignorar}\n', encoding="utf-8")
            with self.assertRaises(fases.MapaErro):
                fases.carregar_mapa(arq)


class TestDecisao(unittest.TestCase):
    def test_aberta_tem_prioridade_sobre_concluida(self):
        d = decidir(
            tarefa("200", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026"),
            tarefa("300", previ("PROTOCOLAR INICIAL"), "Concluída em: 15/11/2026"),  # mais nova, mas fechada
        )
        self.assertEqual(d.fase, "exigencia_inss")
        # "desde": quando terminou o passo anterior
        self.assertEqual(d.desde, date(2026, 11, 15))

    def test_entre_abertas_vale_a_mais_recente(self):
        d = decidir(tarefa("100", previ("ACOMPANHAR MOB"), "Para conclusão 20/11/2026"),
                    tarefa("101", previ("ANALISAR DOCUMENTOS"), "Para conclusão 20/11/2026"))
        self.assertEqual(d.fase, "triagem_documentos")

    def test_sem_aberta_usa_a_concluida_mais_recente(self):
        d = decidir(
            tarefa("10", previ("ANALISAR DOCUMENTOS"), "Concluída em: 01/10/2026"),
            tarefa("11", previ("PROTOCOLAR INICIAL"), "Concluída em: 20/10/2026"),
            tarefa("12", previ("MINUTAR INICIAL"), "Concluída em: 10/10/2026"),
        )
        self.assertEqual((d.fase, d.desde), ("acao_protocolada", date(2026, 10, 20)))

    def test_cancelada_e_ignorada(self):
        d = decidir(
            tarefa("50", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026", selo="CANCELADA"),
            tarefa("49", previ("PROTOCOLAR INICIAL"), "Concluída em: 20/10/2026"),
        )
        self.assertEqual(d.fase, "acao_protocolada")
        so_cancelada = decidir(tarefa("50", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026", selo="CANCELADA"))
        self.assertEqual((so_cancelada.fase, so_cancelada.encaminhar), (DESCONHECIDA, True))

    def test_tipos_ignorar_sao_pulados(self):
        d = decidir(
            tarefa("90", previ("AVISAR AUDIÊNCIA"), "Para conclusão 20/11/2026"),
            tarefa("89", previ("LEMBRAR AUDIÊNCIA"), "Para conclusão 20/11/2026"),
            tarefa("88", previ("AUDIÊNCIA"), "Para conclusão 25/11/2026"),
        )
        self.assertEqual(d.fase, "aguardando_audiencia")
        # só comunicação: usa a concluída
        d2 = decidir(tarefa("90", previ("AVISAR PERÍCIA MÉDICA JUDICIAL"), "Para conclusão 20/11/2026"),
                     tarefa("80", previ("PERÍCIA MÉDICA JUDICIAL"), "Concluída em: 01/11/2026"))
        self.assertEqual(d2.fase, "aguardando_pericia_judicial")
        # só comunicação e nada mais: desconhecida
        d3 = decidir(tarefa("90", previ("AVISAR AUDIÊNCIA"), "Para conclusão 20/11/2026"))
        self.assertEqual(d3.fase, DESCONHECIDA)

    def test_tipo_fora_do_mapa_e_desconhecida_e_encaminha(self):
        d = decidir(tarefa("1", previ("TIPO QUE NINGUEM CADASTROU"), "Para conclusão 20/11/2026"),
                    tarefa("0", previ("PROTOCOLAR INICIAL"), "Concluída em: 20/10/2026"))
        self.assertEqual((d.fase, d.encaminhar), (DESCONHECIDA, True))

    def test_tipo_ambiguo_do_yaml_e_desconhecida(self):
        d = decidir(tarefa("1", previ("ACOMPANHAR RESULTADO DE PERICIA"), "Para conclusão 20/11/2026"))
        self.assertEqual((d.fase, d.encaminhar), (DESCONHECIDA, True))

    def test_encaminha_nas_fases_sensiveis_e_so_nelas(self):
        casos = {"AVISAR X": None, "ANALISAR DECISÃO ADMINISTRATIVA": True, "REQUERER DOCUMENTOS": True,
                 "ACOMPANHAR TRÂNSITO EM JULGADO E ENCERRAR A PASTA": True, "ANALISAR EXIGÊNCIA": False,
                 "AUDIÊNCIA": False, "IMPLANTAÇÃO JUDICIAL": False}
        for tipo, esperado in casos.items():
            if esperado is None:
                continue
            with self.subTest(tipo=tipo):
                self.assertEqual(decidir(tarefa("1", previ(tipo), "Para conclusão 20/11/2026")).encaminhar, esperado)

    def test_segredo_encaminha(self):
        linha = tarefa("1", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026")
        self.assertFalse(decidir(linha).encaminhar)
        d = decidir(linha, segredo=True)
        self.assertEqual((d.fase, d.encaminhar), ("exigencia_inss", True))

    def test_proximo_de_pericia_e_audiencia(self):
        d = decidir(
            tarefa("5", previ("PERÍCIA MÉDICA/SOCIAL NO INSS"), "Para conclusão 25/11/2026 Limite 26/11/2026"),
            tarefa("4", previ("AUDIÊNCIA"), "Para conclusão 20/11/2026"),
            tarefa("3", previ("AUDIÊNCIA"), "Para conclusão 10/11/2026"),             # passada
            tarefa("2", previ("AUDIÊNCIA"), "Para conclusão 30/11/2026", selo="CANCELADA"),
            tarefa("1", previ("PERÍCIA MÉDICA JUDICIAL"), "Concluída em: 20/11/2026"),  # fechada
        )
        self.assertEqual(d.proximo, {"tipo": "audiencia", "data": date(2026, 11, 20)})
        so_pericia = decidir(tarefa("5", previ("PERÍCIA MÉDICA JUDICIAL"), "Limite 25/11/2026"))
        self.assertEqual(so_pericia.proximo, {"tipo": "pericia", "data": date(2026, 11, 25)})
        hoje_mesmo = decidir(tarefa("5", previ("AUDIÊNCIA"), "Para conclusão 16/11/2026"))
        self.assertEqual(hoje_mesmo.proximo["data"], HOJE)
        self.assertIsNone(decidir(tarefa("5", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 25/11/2026")).proximo)

    def test_ficha_ilegivel_ou_cortada_nao_chuta(self):
        self.assertEqual(fases.decidir(None, HOJE, MAPA), fases.Decisao())
        sem_tabela = parados.ler_tarefas_html("<html><body>nada</body></html>")
        self.assertEqual(fases.decidir(sem_tabela, HOJE, MAPA).fase, DESCONHECIDA)
        cortada = decidir(tarefa("1", previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026"),
                          info="Mostrando 1 a 1 de 7 registros")
        self.assertEqual((cortada.fase, cortada.encaminhar), (DESCONHECIDA, True))

    def test_ficha_sem_tarefas(self):
        d = decidir()
        self.assertEqual((d.fase, d.desde, d.proximo, d.encaminhar), (DESCONHECIDA, None, None, True))


if __name__ == "__main__":
    unittest.main()
