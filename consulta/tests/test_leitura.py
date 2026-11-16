import unittest

from consulta import leitura
from consulta.tests import html as h


class TestUrls(unittest.TestCase):
    def test_lista_de_processos_so_get_e_ativos(self):
        u = leitura.url_lista_processos("390.533.447-05")
        self.assertIn("processos-lista.php", u)
        self.assertIn("pesq[cpfcnpj]=390.533.447-05", u)
        self.assertIn("pesq[filtros_multi][]=ativos", u)
        self.assertIn("pesq[limit]=30", u)
        self.assertNotIn("act=", u)

    def test_pessoas_e_formulario(self):
        self.assertIn("pesq[busca]=39053344705", leitura.url_lista_pessoas("39053344705"))
        u = leitura.url_form_pessoa("701")
        self.assertTrue(u.endswith("act=edit&clientes_id=701"))
        with self.assertRaises(ValueError):
            leitura.url_form_pessoa("701; act=del")


class TestArea(unittest.TestCase):
    def test_codigos_fechados(self):
        casos = {"Previdenciário": "previdenciario", "Previdenciário Administrativo": "previdenciario",
                 "Cível Consumidor": "civel", "Cível Imobiliário": "imobiliario", "Trabalhista": "trabalhista",
                 "Família e Sucessões": "familia_sucessoes", "Criminal": "criminal", "Tributário": "tributario",
                 "Empresarial / Societário": "empresarial", "Contratos": "empresarial", "Ambiental": "ambiental",
                 "Direito Administrativo": "administrativo", "Marcas e INPI": "empresarial", "Coisa Nova": "outra",
                 "": "outra"}
        for texto, codigo in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(leitura.area_codigo(texto), codigo)
                self.assertIn(codigo, leitura.AREAS)


class TestLista(unittest.TestCase):
    def test_ci_area_e_eco_do_filtro(self):
        r = leitura.ler_lista_processos(h.lista("390.533.447-05", [h.linha_lista(1, "9101"), h.linha_lista(2, "9102", "Trabalhista"),
                                                                   h.linha_lista(3, "9101")]))
        self.assertEqual([(p.ci, p.area) for p in r.processos], [("9101", "previdenciario"), ("9102", "trabalhista")])
        self.assertEqual(r.cpf_no_filtro, "39053344705")

    def test_sem_eco(self):
        r = leitura.ler_lista_processos(h.lista("", [h.linha_lista(1, "9101")], eco=False))
        self.assertIsNone(r.cpf_no_filtro)

    def test_so_ci_e_area_saem(self):
        r = leitura.ler_lista_processos(h.lista("1", [h.linha_lista(1, "9101")]))
        self.assertEqual(set(vars(r.processos[0])), {"ci", "area", "segredo"})

    def test_segredo_na_linha(self):
        r = leitura.ler_lista_processos(h.lista("1", [h.linha_lista(1, "9101", extra="Segredo de Justiça"),
                                                      h.linha_lista(2, "9102")]))
        self.assertEqual([p.segredo for p in r.processos], [True, False])

    def test_lista_vazia(self):
        self.assertEqual(leitura.ler_lista_processos(h.lista("1", [])).processos, [])
        self.assertEqual(leitura.ler_lista_processos("").processos, [])


class TestPessoas(unittest.TestCase):
    def test_ids_dos_links_com_id(self):
        html = h.pessoas(701, 702, 701) + '<a href="?pag=sys/clientes/clientes-vis.php">sem id</a>'
        self.assertEqual(leitura.ler_ids_pessoas(html), ["701", "702"])
        self.assertEqual(leitura.ler_ids_pessoas(""), [])

    def test_formulario_so_os_quatro_campos(self):
        c = leitura.ler_form_pessoa(h.formulario("390.533.447-05", "(88) 90000-0001", "(88) 3000-0002", ""))
        self.assertEqual(c.cpf, "39053344705")
        self.assertEqual(c.telefones, ["(88) 90000-0001", "(88) 3000-0002"])

    def test_contatos_extras_nao_entram(self):
        html = h.formulario("390.533.447-05", "(88) 90000-0001")
        c = leitura.ler_form_pessoa(html)
        self.assertNotIn("(88) 90000-0999", c.telefones)
        self.assertNotIn("CONTATO-EXTRA", str(vars(c)))
        self.assertNotIn("NOME-DO-CLIENTE", str(vars(c)))

    def test_formulario_sem_campos(self):
        c = leitura.ler_form_pessoa("<html></html>")
        self.assertEqual((c.cpf, c.telefones), ("", []))


class TestSegredo(unittest.TestCase):
    def ficha(self, bloco):
        return h.ficha([], blocos=bloco)

    def test_rotulo_com_valor_sim(self):
        textos = leitura.textos_de_segredo(self.ficha(
            "<p><strong><span>Segredo de justiça</span>: </strong> <span>Sim</span></p>"))
        self.assertEqual(len(textos), 1)
        self.assertTrue(leitura.tem_segredo(textos))

    def test_rotulo_com_nao_nao_conta(self):
        textos = leitura.textos_de_segredo(self.ficha(
            "<p><strong>Segredo de justiça:</strong> Não</p>"))
        self.assertEqual(len(textos), 1)
        self.assertFalse(leitura.tem_segredo(textos))

    def test_sigilo_no_valor_e_selo(self):
        self.assertTrue(leitura.tem_segredo(leitura.textos_de_segredo(self.ficha(
            "<p><strong>Complemento</strong>: Tramita em sigilo</p>"))))
        self.assertTrue(leitura.tem_segredo(leitura.textos_de_segredo(
            '<div><span class="vj-badge">SEGREDO DE JUSTIÇA</span></div>')))

    def test_ficha_normal_nao_tem(self):
        self.assertEqual(leitura.textos_de_segredo(h.ficha([h.tarefa("1", h.previ("AUDIÊNCIA"), "")])), [])
        self.assertFalse(leitura.tem_segredo([]))

    def test_comentario_de_tarefa_fora_dos_blocos_nao_conta(self):
        html = h.ficha([h.tarefa("1", h.previ("AUDIÊNCIA"), "", comentario="processo em segredo de justiça")])
        self.assertEqual(leitura.textos_de_segredo(html), [])


if __name__ == "__main__":
    unittest.main()
