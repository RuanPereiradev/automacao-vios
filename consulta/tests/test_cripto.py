import base64
import os
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from consulta import cripto

CPF_VALIDO = "39053344705"


class TestCpf(unittest.TestCase):
    def test_validar(self):
        for ok in (CPF_VALIDO, "390.533.447-05", "52998224725", "11144477735"):
            self.assertTrue(cripto.validar_cpf(ok), ok)
        for ruim in ("39053344706", "11111111111", "1234567890", "", "abc", "390533447051"):
            self.assertFalse(cripto.validar_cpf(ruim), ruim)

    def test_formatar_e_gerar(self):
        self.assertEqual(cripto.formatar_cpf(CPF_VALIDO), "390.533.447-05")
        self.assertEqual(cripto.calcular_digitos_cpf("390533447"), CPF_VALIDO)


class TestTelefone(unittest.TestCase):
    VETORES = {
        "(88) 99284-3164": "558892843164",
        "5588992843164": "558892843164",
        "088 9284-3164": "558892843164",
        "+55 (85) 3256-1234": "558532561234",
        "99284-3164": None,
    }

    def test_vetores_da_secao_7(self):
        for entrada, esperado in self.VETORES.items():
            with self.subTest(entrada=entrada):
                self.assertEqual(cripto.normalizar_telefone(entrada), esperado)

    def test_outros_casos(self):
        self.assertIsNone(cripto.normalizar_telefone(""))
        self.assertIsNone(cripto.normalizar_telefone(None))
        self.assertIsNone(cripto.normalizar_telefone("123"))
        # DDD 55 sem código de país não perde o 55
        self.assertEqual(cripto.normalizar_telefone("(55) 99999-1234"), "555599991234")
        self.assertEqual(cripto.normalizar_telefone("55 55 99999-1234"), "555599991234")

    def test_hmac_vetor_fixo(self):
        # o mesmo valor está fixado no teste do bot: se um lado mudar, os dois quebram
        self.assertEqual(cripto.hmac_telefone("chave-de-teste", "558892843164"),
                         "94bdc963b883de1e47a116117229a68d184a334b6c6cc65a62b803832b4f5ae2")

    def test_hashes_descarta_e_nao_repete(self):
        hs = cripto.hashes_telefones("chave-de-teste", ["(88) 99284-3164", "5588992843164", "99284-3164", ""])
        self.assertEqual(hs, ["94bdc963b883de1e47a116117229a68d184a334b6c6cc65a62b803832b4f5ae2"])


class TestAssinatura(unittest.TestCase):
    def test_get_vazio(self):
        self.assertEqual(cripto.assinar("segredo-de-teste", "1700000000000", "GET", "/consulta/pendentes", ""),
                         "7e5fed99c34a267c4d44ed98e546ab88efa3ee1540665602d10d5c66120dc9f5")

    def test_post_com_corpo(self):
        self.assertEqual(
            cripto.assinar("segredo-de-teste", "1700000000000", "post", "/consulta/resultado", '{"id":"abc"}'),
            "303dc69a937292fddf8947e42b9114bc22045d3b7618b65786425a6e18fda3e7")

    def test_muda_com_qualquer_parte(self):
        base = cripto.assinar("s", "1", "GET", "/a", "")
        for outra in (cripto.assinar("t", "1", "GET", "/a", ""), cripto.assinar("s", "2", "GET", "/a", ""),
                      cripto.assinar("s", "1", "POST", "/a", ""), cripto.assinar("s", "1", "GET", "/b", ""),
                      cripto.assinar("s", "1", "GET", "/a", "x")):
            self.assertNotEqual(base, outra)


class TestRsa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def test_ida_e_volta(self):
        cifrado = cripto.cifrar_cpf("390.533.447-05", self.privada.public_key())
        self.assertNotIn(CPF_VALIDO, cifrado)
        self.assertEqual(cripto.decifrar_cpf(cifrado, self.privada), CPF_VALIDO)

    def test_oaep_sha256_padrao_do_node(self):
        # Node: publicEncrypt({oaepHash: "sha256"}) usa SHA-256 também no MGF1, sem label
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        cifrado = self.privada.public_key().encrypt(
            CPF_VALIDO.encode(), padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
        self.assertEqual(cripto.decifrar_cpf(base64.b64encode(cifrado).decode(), self.privada), CPF_VALIDO)

    def test_lixo_e_chave_errada(self):
        with self.assertRaises(cripto.CriptoErro):
            cripto.decifrar_cpf("isto não é base64!", self.privada)
        with self.assertRaises(cripto.CriptoErro):
            cripto.decifrar_cpf(base64.b64encode(b"x" * 256).decode(), self.privada)
        outra = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cifrado = cripto.cifrar_cpf(CPF_VALIDO, outra.public_key())
        with self.assertRaises(cripto.CriptoErro):
            cripto.decifrar_cpf(cifrado, self.privada)

    def test_cpf_invalido_depois_de_decifrar(self):
        cifrado = cripto.cifrar_cpf("12345678900", self.privada.public_key())
        with self.assertRaises(cripto.CriptoErro):
            cripto.decifrar_cpf(cifrado, self.privada)

    def test_chave_do_arquivo_exige_600(self):
        pem = self.privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption())
        with tempfile.TemporaryDirectory() as d:
            arq = Path(d) / "privada.pem"
            arq.write_bytes(pem)
            os.chmod(arq, 0o644)
            with self.assertRaises(cripto.CriptoErro):
                cripto.carregar_chave_privada(arq)
            os.chmod(arq, 0o600)
            chave = cripto.carregar_chave_privada(arq)
            cifrado = cripto.cifrar_cpf(CPF_VALIDO, chave.public_key())
            self.assertEqual(cripto.decifrar_cpf(cifrado, chave), CPF_VALIDO)
            with self.assertRaises(cripto.CriptoErro):
                cripto.carregar_chave_privada(Path(d) / "nao-existe.pem")


if __name__ == "__main__":
    unittest.main()
