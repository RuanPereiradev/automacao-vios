"""Testes da "Posição do cliente" (autor/réu) do relatório por Grupo Cliente.

Só dados fictícios. Não acessa o VIOS.
"""
import unittest

from bot.processos_grupo import _nome_comparavel, posicao_cliente

AUTOR = "autor (o cliente entrou com a ação)"
REU = "réu (o cliente está sendo processado)"
NAO = "não identificada (o cliente não aparece nas partes da lista)"
OS_DOIS = "aparece como autor e como réu (conferir no VIOS)"


def item(cliente, ativa=(), passiva=()):
    return {"cliente": cliente, "parte_ativa": list(ativa), "parte_passiva": list(passiva)}


class TestNomeComparavel(unittest.TestCase):
    def test_pontuacao_e_espacos(self):
        self.assertEqual(_nome_comparavel("3A  Frios   Ltda."), "3A FRIOS")
        self.assertEqual(_nome_comparavel("3A FRIOS LTDA"), "3A FRIOS")

    def test_sa_em_todas_as_formas(self):
        for nome in ("ACME S/A", "ACME S.A.", "ACME SA", "ACME S A", "ACME S. A.", "ACME Sociedade Anônima"):
            self.assertEqual(_nome_comparavel(nome), "ACME", nome)

    def test_sufixos_no_meio_e_no_fim(self):
        self.assertEqual(_nome_comparavel("COMERCIO X LTDA - ME"), "COMERCIO X")
        self.assertEqual(_nome_comparavel("COMERCIO X LTDA-EPP"), "COMERCIO X")
        self.assertEqual(_nome_comparavel("COMERCIO X EIRELI ME"), "COMERCIO X")
        self.assertEqual(_nome_comparavel("COMERCIO X LTDA MATRIZ"), "COMERCIO X")
        self.assertEqual(_nome_comparavel("COMERCIO X FILIAL"), "COMERCIO X")
        self.assertEqual(_nome_comparavel("FULANO & CIA LTDA"), "FULANO")
        self.assertEqual(_nome_comparavel("JOAO SILVA MEI"), "JOAO SILVA")
        self.assertEqual(_nome_comparavel("OI S.A. - Em Recuperação Judicial"), "OI")

    def test_sobrenome_sa_com_acento_fica(self):
        # "Sá" é sobrenome, não é S.A.
        self.assertEqual(_nome_comparavel("MARIA DE SÁ"), "MARIA DE SA")

    def test_rotulo(self):
        self.assertEqual(_nome_comparavel("Reclamado: 3A Frios Ltda.", tirar_rotulo=True), "3A FRIOS")
        # sem tirar_rotulo, o nome do cliente não perde nada
        self.assertEqual(_nome_comparavel("3A FRIOS LTDA"), "3A FRIOS")

    def test_cpf_cnpj_e_parenteses(self):
        self.assertEqual(
            _nome_comparavel("Autor: 3A FRIOS LTDA (CNPJ 12.345.678/0001-90)", tirar_rotulo=True), "3A FRIOS"
        )
        self.assertEqual(
            _nome_comparavel("Réu: FULANO DE TAL - CPF: 123.456.789-00", tirar_rotulo=True), "FULANO DE TAL"
        )
        # sem rótulo: o ":" do CNPJ não pode ser lido como rótulo
        self.assertEqual(_nome_comparavel("3A FRIOS LTDA CNPJ: 12345678000190", tirar_rotulo=True), "3A FRIOS")
        self.assertEqual(_nome_comparavel("A AFONSO LINHARES (MATRIZ)"), "A AFONSO LINHARES")

    def test_acentos(self):
        self.assertEqual(_nome_comparavel("José Conceição"), "JOSE CONCEICAO")

    def test_vazio(self):
        self.assertEqual(_nome_comparavel(""), "")
        self.assertEqual(_nome_comparavel(None), "")


class TestPosicaoCliente(unittest.TestCase):
    def test_caso_confirmado_3a_frios(self):
        # antes dava "não identificada"
        self.assertEqual(posicao_cliente(item("3A FRIOS LTDA", passiva=["Reclamado: 3A Frios Ltda."])), REU)

    def test_autor(self):
        it = item("3A FRIOS LTDA", ativa=["Exequente: 3A FRIOS LTDA - ME"], passiva=["Executado: FULANO"])
        self.assertEqual(posicao_cliente(it), AUTOR)

    def test_rotulos_variados(self):
        for rotulo in ("Autor", "Requerente", "Exequente", "Reclamante", "Impetrante"):
            it = item("ACME S/A", ativa=[rotulo + ": Acme S.A."])
            self.assertEqual(posicao_cliente(it), AUTOR, rotulo)
        for rotulo in ("Réu", "Reclamado", "Requerido", "Executado"):
            it = item("ACME S/A", passiva=[rotulo + ": ACME SA"])
            self.assertEqual(posicao_cliente(it), REU, rotulo)

    def test_parte_sem_rotulo(self):
        self.assertEqual(posicao_cliente(item("ACME LTDA", passiva=["ACME LTDA."])), REU)

    def test_parenteses_com_cnpj(self):
        it = item("3A FRIOS LTDA", passiva=["Reclamado: 3A FRIOS LTDA (CNPJ: 12.345.678/0001-90)"])
        self.assertEqual(posicao_cliente(it), REU)

    def test_varias_partes_no_polo(self):
        it = item("3A FRIOS LTDA", passiva=["Reclamado: FULANO", "Reclamado: 3A Frios Ltda", "Reclamado: OUTRA SA"])
        self.assertEqual(posicao_cliente(it), REU)

    def test_os_dois_polos(self):
        it = item("ACME LTDA", ativa=["Autor: ACME LTDA"], passiva=["Réu: Acme Ltda."])
        self.assertEqual(posicao_cliente(it), OS_DOIS)

    def test_sem_falso_positivo_por_prefixo(self):
        self.assertEqual(posicao_cliente(item("JOSE SILVA", ativa=["Autor: JOSE SILVA SANTOS"])), NAO)
        self.assertEqual(posicao_cliente(item("JOSE SILVA SANTOS", ativa=["Autor: JOSE SILVA"])), NAO)
        self.assertEqual(posicao_cliente(item("3A FRIOS LTDA", passiva=["Réu: 3A FRIOS COMERCIO LTDA"])), NAO)

    def test_ci_29191_abreviacao_nao_casa(self):
        it = item("A AFONSO LINHARES (MATRIZ)", passiva=["Reclamado: ANTONIO AFONSO LINHARES"])
        self.assertEqual(posicao_cliente(it), NAO)

    def test_cliente_vazio(self):
        self.assertEqual(posicao_cliente(item("", ativa=["Autor: FULANO"])), "não identificada")
        self.assertEqual(posicao_cliente({"parte_ativa": [], "parte_passiva": []}), "não identificada")
        # cliente só com sufixo também não tem nome para comparar
        self.assertEqual(posicao_cliente(item("LTDA", ativa=["Autor: LTDA"])), "não identificada")

    def test_sem_partes(self):
        # ex.: CI 27513 (INPI), sem partes cadastradas
        self.assertEqual(posicao_cliente(item("3A FRIOS LTDA")), NAO)
        self.assertEqual(posicao_cliente({"cliente": "3A FRIOS LTDA"}), NAO)

    def test_parte_vazia_nao_casa(self):
        self.assertEqual(posicao_cliente(item("ACME", ativa=["Autor:", ""])), NAO)


if __name__ == "__main__":
    unittest.main()
