import json
import logging
import unittest
from datetime import date, datetime, timezone, timedelta

from cryptography.hazmat.primitives.asymmetric import rsa

from consulta import coletor, cripto, fases, montagem
from consulta.erros import ConsultaErro, SessaoPerdida
from consulta.fonte import FonteMemoria
from consulta.tests import html as h

HOJE = date(2026, 11, 16)
AGORA = datetime(2026, 11, 16, 14, 3, 0, tzinfo=timezone(timedelta(hours=-3)))
CPF = "39053344705"
CHAVE = "chave-de-teste"
MAPA = fases.carregar_mapa()
PRIVADA = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OP = coletor.Opcoes(chave_telefone=CHAVE)
CONTAMINACAO = ("NOME-DO-CLIENTE", "0000000-00.2099", "COMENTARIO-SECRETO", "DESCRICAO-SECRETA", "99.999,99",
                "OBS-INTERNA", "PESSOA-DA-EQUIPE", "CONTATO-EXTRA", "90000-0999", "Cidade Fictícia")


def fonte(processos=(("9101", "Previdenciário"),), cpf=CPF, telefones=("(88) 90000-0001",), cpf_cadastro=None,
          fichas=None, eco=True, **kw):
    linhas = [h.linha_lista(n, ci, area) for n, (ci, area) in enumerate(processos, 1)]
    fichas = fichas if fichas is not None else {
        ci: h.ficha([h.tarefa("100", h.previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026")])
        for ci, _ in processos}
    return FonteMemoria(
        listas={cpf: h.lista(cripto.formatar_cpf(cpf), linhas, eco=eco)} if processos else {},
        pessoas={cpf: h.pessoas(701)},
        formularios={"701": h.formulario(cripto.formatar_cpf(cpf_cadastro or cpf), *telefones)},
        fichas=fichas, **kw)


def consultar(f, op=OP, cpf=CPF):
    return coletor.consultar(cpf, f, op, HOJE, MAPA, "id-1", AGORA)


class TestListaBranca(unittest.TestCase):
    def test_nada_contaminado_sai_no_json(self):
        f = fonte(processos=(("9101", "Previdenciário"), ("9102", "Cível Consumidor")),
                  telefones=("(88) 90000-0001", "(88) 3000-0002", "(88) 90000-0003"))
        r = consultar(f)
        montagem.validar_resultado(r)
        texto = json.dumps(r, ensure_ascii=False)
        for sujeira in CONTAMINACAO + (CPF, "390.533.447-05", "9101", "9102", "88", "90000"):
            self.assertNotIn(sujeira, texto, sujeira)
        self.assertEqual(set(r), {"id", "status", "lidoEm", "telefones", "processos"})
        for p in r["processos"]:
            self.assertEqual(set(p), set(montagem.CAMPOS_PROCESSO))
        self.assertEqual([p["ref"] for p in r["processos"]], ["P1", "P2"])

    def test_resultado_ok_completo(self):
        r = consultar(fonte())
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["lidoEm"], "2026-11-16T14:03:00-03:00")
        self.assertEqual(r["telefones"], [cripto.hmac_telefone(CHAVE, "558800000001")])
        p = r["processos"][0]
        self.assertEqual((p["area"], p["situacao"], p["fase"], p["encaminhar"]),
                         ("previdenciario", "ativo", "exigencia_inss", False))
        self.assertIsNone(p["desde"])
        self.assertIsNone(p["proximo"])

    def test_contatos_extras_nao_entram_nos_telefones(self):
        r = consultar(fonte(telefones=("(88) 90000-0001",)))
        self.assertNotIn(cripto.hmac_telefone(CHAVE, "558800000999"), r["telefones"])
        self.assertEqual(len(r["telefones"]), 1)

    def test_todos_os_telefones_do_cadastro_normalizados(self):
        r = consultar(fonte(telefones=("(88) 99284-3164", "(88) 3256-1234", "sem número")))
        self.assertEqual(r["telefones"], [cripto.hmac_telefone(CHAVE, "558892843164"),
                                          cripto.hmac_telefone(CHAVE, "558832561234")])

    def test_proximo_e_desde(self):
        ficha = h.ficha([
            h.tarefa("300", h.previ("PERÍCIA MÉDICA JUDICIAL"), "Para conclusão 25/11/2026"),
            h.tarefa("200", h.previ("INSTRUÇÃO PERÍCIA MÉDICA JUDICIAL"), "Concluída em: 02/11/2026")])
        r = consultar(fonte(fichas={"9101": ficha}))
        p = r["processos"][0]
        self.assertEqual((p["fase"], p["desde"], p["proximo"]),
                         ("aguardando_pericia_judicial", "2026-11-02", {"tipo": "pericia", "data": "2026-11-25"}))

    def test_nao_ok_nunca_leva_dados(self):
        for status in ("erro", "nao_encontrado"):
            r = montagem.montar_resultado("x", status, [{"lixo": 1}], ["a" * 64], AGORA)
            self.assertEqual((r["telefones"], r["processos"]), ([], []))


class TestEstados(unittest.TestCase):
    def test_nenhum_processo_nao_encontrado(self):
        r = consultar(fonte(processos=()))
        self.assertEqual((r["status"], r["telefones"], r["processos"]), ("nao_encontrado", [], []))

    def test_sem_cadastro_nao_encontrado(self):
        f = fonte()
        f.pessoas.clear()
        self.assertEqual(consultar(f)["status"], "nao_encontrado")

    def test_cpf_divergente_no_cadastro_e_erro(self):
        with self.assertRaises(ConsultaErro):
            consultar(fonte(cpf_cadastro="52998224725"))

    def test_cpf_sem_digitos_no_cadastro_e_erro(self):
        f = fonte()
        f.formularios["701"] = "<html></html>"
        with self.assertRaises(ConsultaErro):
            consultar(f)

    def test_filtro_nao_confirmado_e_erro(self):
        with self.assertRaises(ConsultaErro):
            consultar(fonte(eco=False))
        # com a trava desligada (depois de conferir a tela real) segue
        self.assertEqual(consultar(fonte(eco=False), coletor.Opcoes(CHAVE, exigir_eco_cpf=False))["status"], "ok")

    def test_filtro_com_outro_cpf_e_erro(self):
        f = fonte()
        f.listas[CPF] = h.lista("529.982.247-25", [h.linha_lista(1, "9101")])
        with self.assertRaises(ConsultaErro):
            consultar(f)

    def test_lista_cheia_e_erro(self):
        procs = tuple((str(9000 + i), "Cível") for i in range(30))
        with self.assertRaises(ConsultaErro):
            consultar(fonte(processos=procs))

    def test_cadastros_demais(self):
        f = fonte()
        f.pessoas[CPF] = h.pessoas(*range(701, 710))
        with self.assertRaises(ConsultaErro):
            consultar(f)

    def test_mais_de_um_cadastro_junta_os_telefones(self):
        f = fonte()
        f.pessoas[CPF] = h.pessoas(701, 702)
        f.formularios["702"] = h.formulario("390.533.447-05", "(88) 90000-0002")
        r = consultar(f)
        self.assertEqual(len(r["telefones"]), 2)

    def test_ficha_que_nao_leu_vira_desconhecida_e_encaminha(self):
        f = fonte(processos=(("9101", "Previdenciário"), ("9102", "Previdenciário")),
                  fichas={"9101": h.ficha([h.tarefa("1", h.previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026")])})
        r = consultar(f)
        self.assertEqual([p["fase"] for p in r["processos"]], ["exigencia_inss", "desconhecida"])
        self.assertEqual([p["encaminhar"] for p in r["processos"]], [False, True])

    def test_nenhuma_ficha_lida_e_erro(self):
        with self.assertRaises(ConsultaErro):
            consultar(fonte(fichas={}))

    def test_segredo_encaminha(self):
        ficha = h.ficha([h.tarefa("1", h.previ("ANALISAR EXIGÊNCIA"), "Para conclusão 20/11/2026")],
                        blocos="<p><strong>Segredo de justiça:</strong> Sim</p>")
        p = consultar(fonte(fichas={"9101": ficha}))["processos"][0]
        self.assertEqual((p["fase"], p["encaminhar"]), ("exigencia_inss", True))

    def test_so_le_o_que_o_contrato_manda(self):
        f = fonte()
        consultar(f)
        self.assertEqual([a[0] for a in f.acessos], ["lista_processos", "lista_pessoas", "form_pessoa", "ficha"])


class TestProcessarPedido(unittest.TestCase):
    def pedido(self, cpf=CPF, pid="abc"):
        return {"id": pid, "cpfCifrado": cripto.cifrar_cpf(cpf, PRIVADA.public_key())}

    def test_ok(self):
        r = coletor.processar_pedido(self.pedido(), PRIVADA, fonte(), OP, MAPA, HOJE, AGORA)
        self.assertEqual((r["id"], r["status"]), ("abc", "ok"))
        montagem.validar_resultado(r)

    def test_cpf_invalido_nem_consulta_o_vios(self):
        f = fonte()
        r = coletor.processar_pedido(self.pedido("12345678900"), PRIVADA, f, OP, MAPA, HOJE, AGORA)
        self.assertEqual(r["status"], "erro")
        self.assertEqual(f.acessos, [])

    def test_pedido_ilegivel_e_erro(self):
        r = coletor.processar_pedido({"id": "z", "cpfCifrado": "lixo"}, PRIVADA, fonte(), OP, MAPA, HOJE, AGORA)
        self.assertEqual((r["id"], r["status"]), ("z", "erro"))

    def test_excecao_qualquer_vira_erro_e_sessao_perdida_sobe(self):
        class Quebra(FonteMemoria):
            def lista_processos(self, c):
                raise RuntimeError("falha " + c)

        class Caiu(FonteMemoria):
            def lista_processos(self, c):
                raise SessaoPerdida("caiu")

        r = coletor.processar_pedido(self.pedido(), PRIVADA, Quebra(), OP, MAPA, HOJE, AGORA)
        self.assertEqual(r["status"], "erro")
        with self.assertRaises(SessaoPerdida):
            coletor.processar_pedido(self.pedido(), PRIVADA, Caiu(), OP, MAPA, HOJE, AGORA)


class TestLogsLimpos(unittest.TestCase):
    """Nenhum log do coletor (nem o da Orelha) pode ter CPF, telefone, nome ou CI."""

    def test_nenhum_log_tem_dado_do_cliente(self):
        class Captura(logging.Handler):
            def __init__(self):
                super().__init__(logging.DEBUG)
                self.linhas = []

            def emit(self, record):
                self.linhas.append(record.getMessage())

        cap = Captura()
        loggers = [logging.getLogger(n) for n in ("consulta", "orelha")]
        antes = [(lg.level, lg.propagate) for lg in loggers]
        for lg in loggers:
            lg.setLevel(logging.DEBUG)
            lg.addHandler(cap)
        try:
            class Quebra(FonteMemoria):
                def ficha(self, ci):
                    raise RuntimeError(f"falha na ficha {ci} do CPF {CPF}")

            procs = (("9101", "Previdenciário"), ("9102", "Cível"))
            ped = lambda pid: {"id": pid, "cpfCifrado": cripto.cifrar_cpf(CPF, PRIVADA.public_key())}  # noqa: E731
            coletor.processar_pedido(ped("p1"), PRIVADA, fonte(processos=procs), OP, MAPA, HOJE, AGORA)
            coletor.processar_pedido(ped("p2"), PRIVADA, fonte(cpf_cadastro="52998224725"), OP, MAPA, HOJE, AGORA)
            coletor.processar_pedido(ped("p3"), PRIVADA, fonte(processos=()), OP, MAPA, HOJE, AGORA)
            coletor.processar_pedido({"id": "p4", "cpfCifrado": "lixo"}, PRIVADA, fonte(), OP, MAPA, HOJE, AGORA)
            q = fonte(processos=procs)
            q.fichas = None
            coletor.processar_pedido(ped("p5"), PRIVADA, q, OP, MAPA, HOJE, AGORA)
        finally:
            for lg, (nivel, prop) in zip(loggers, antes):
                lg.removeHandler(cap)
                lg.setLevel(nivel)
                lg.propagate = prop
        self.assertTrue(cap.linhas)
        tudo = "\n".join(cap.linhas)
        for proibido in (CPF, "390.533.447-05", "9101", "9102", "90000", "NOME-DO-CLIENTE", "0000000-00",
                         cripto.hmac_telefone(CHAVE, "558800000001")):
            self.assertNotIn(proibido, tudo, proibido)
        self.assertIn("p1: ok", tudo)


if __name__ == "__main__":
    unittest.main()
