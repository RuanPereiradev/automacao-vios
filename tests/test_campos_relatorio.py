"""Testes dos 13 campos do relatório do cliente (bot/campos_relatorio.py).

Dados inventados. A IA é FALSA: nada é enviado para a OpenAI nem para a Anthropic.
"""
import json
import logging
import unittest
from datetime import date

from bot import campos_relatorio as cr
from bot import custo

HOJE = date(2026, 11, 3)

TITULOS = ["ID da extração", "Número do processo", "Parte ativa", "Parte passiva", "Tipo de processo", "Órgão",
           "Data da distribuição", "Valor da ação", "Cidade/UF", "Última movimentação",
           "Resumo do caso", "PENDÊNCIA", "Financeira"]


def tarefa(ci, tipo, situacao="", descricao="", comentarios="", para="", limite="", concluida=""):
    return {"ci": str(ci), "situacao": situacao, "tipo": tipo, "descricao": descricao, "comentarios": comentarios,
            "para_conclusao": para, "limite": limite, "concluida_em": concluida}


def ficha(tarefas=(), comentarios=(), ok=True, **extra):
    base = {"ok": ok, "erro": "" if ok else "tempo esgotado", "campos": {}, "cidade_uf": "Cidade Teste / CE",
            "fase": "Conhecimento", "data_distribuicao": "", "valor_acao": "", "justica": "Estadual",
            "sistema": "PJe", "tarefas": list(tarefas), "comentarios": list(comentarios), "arquivos": []}
    base.update(extra)
    return base


def registro(ci="101", numero="0000001-11.2026.8.06.0001", ativa=("Autor: FULANO DE TESTE",),
             passiva=("Contrário: EMPRESA FICTICIA LTDA",), cliente="EMPRESA FICTICIA LTDA", fic=None, **extra):
    base = {"grupo": "GRUPO TESTE", "ci": ci, "numero": numero, "parte_ativa": list(ativa),
            "parte_passiva": list(passiva), "cliente": cliente, "polo_cliente": "Parte Passiva",
            "area": "Cível Consumidor", "tipo_processo": "CÍVEL", "acao": "Indenização", "orgao": "Comarca Teste",
            "uf": "CE", "vara": "1ª Vara Cível", "tipo_vara": "Vara", "data_acao": "05/01/2026",
            "valor_acao": "50.000,00", "objeto": "cobrança indevida", "obs_proc": "FASE X - LINK DO CHAT: segredo-interno",
            "posicao": "réu (o cliente está sendo processado)", "ficha": fic if fic is not None else ficha()}
    base.update(extra)
    return base


class IAFalsa:
    """Imita responder() dos provedores: devolve um item por processo recebido."""

    def __init__(self, falhar=None, resposta=None):
        self.chamadas = []
        self.falhar = falhar
        self.resposta = resposta

    def responder(self, sistema, usuario, schema, pesquisar=False):
        self.chamadas.append({"sistema": sistema, "usuario": usuario, "schema": schema})
        if self.falhar:
            raise self.falhar
        dados = json.loads(usuario)
        if self.resposta is not None:
            return self.resposta(dados)
        itens = [{"id_extracao": p["id_extracao"], "resumo": f"Resumo IA {p['id_extracao']}",
                  "pendencia": "Aguardando audiência", "financeira": "não identificada"} for p in dados["processos"]]
        return {"processos": itens, "_uso": {"entrada": 1000, "entrada_cache": 0, "saida": 300}}


class Base(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestColunas(Base):
    def test_titulos_exatos_e_ordem(self):
        self.assertEqual([t for _, t in cr.COLUNAS], TITULOS)
        self.assertEqual(cr.CHAVES[0], "id_extracao")
        self.assertEqual(cr.CHAVES[-1], "financeira")

    def test_13_campos_sempre_presentes_e_na_ordem(self):
        regs = [registro(), {"grupo": "GRUPO TESTE"}, registro(ci="103", fic={"ok": False, "erro": "falhou"})]
        for linha in cr.montar_linhas(regs, hoje=HOJE):
            self.assertEqual(list(linha), cr.CHAVES)
            for valor in linha.values():
                self.assertIsInstance(valor, str)
                self.assertTrue(valor.strip())

    def test_registro_completo(self):
        tarefas = [tarefa(9, "ANALISAR PROCESSO", comentarios="Processo aguardando sentença.", para="20/10/2026",
                          concluida="21/10/2026"),
                   tarefa(10, "AUDIÊNCIA", descricao="Audiência de conciliação", para="10/12/2026")]
        linha = cr.montar_linhas([registro(fic=ficha(tarefas))], hoje=HOJE)[0]
        self.assertEqual(linha["id_extracao"], "1")
        self.assertEqual(linha["numero"], "0000001-11.2026.8.06.0001")
        self.assertEqual(linha["parte_ativa"], "FULANO DE TESTE")
        self.assertEqual(linha["parte_passiva"], "EMPRESA FICTICIA LTDA")
        self.assertEqual(linha["tipo_processo"], "CÍVEL")
        self.assertEqual(linha["orgao"], "Comarca Teste - 1ª Vara Cível")
        self.assertEqual(linha["data_distribuicao"], "05/01/2026")
        self.assertEqual(linha["valor_acao"], "R$ 50.000,00")
        self.assertEqual(linha["cidade_uf"], "Cidade Teste / CE")
        self.assertEqual(linha["ultima_movimentacao"],
                         "21/10/2026 - ANALISAR PROCESSO - Processo aguardando sentença.")
        self.assertEqual(linha["pendencia"], "AUDIÊNCIA até 10/12/2026")
        self.assertEqual(linha["financeira"], "não identificada")
        self.assertEqual(linha["resumo"], "Ação Indenização sobre cobrança indevida, movida por FULANO DE TESTE "
                                          "contra EMPRESA FICTICIA LTDA, em Cidade Teste / CE.")

    def test_obs_proc_nunca_entra(self):
        regs = [registro()]
        ia = IAFalsa()
        linhas = cr.montar_linhas(regs, ia=ia, hoje=HOJE)
        self.assertNotIn("segredo-interno", json.dumps(linhas, ensure_ascii=False))
        self.assertNotIn("segredo-interno", ia.chamadas[0]["usuario"])
        self.assertNotIn("FASE X", ia.chamadas[0]["usuario"])

    def test_ordena_por_cliente_parte_ativa_e_numero(self):
        regs = [registro(ci="1", cliente="ZETA", numero="3"),
                registro(ci="2", cliente="ALFA", ativa=["Autor: MARIO"], numero="2"),
                registro(ci="3", cliente="ALFA", ativa=["Autor: ANA"], numero="9"),
                registro(ci="4", cliente="ALFA", ativa=["Autor: ANA"], numero="1")]
        linhas = cr.montar_linhas(regs, hoje=HOJE)
        self.assertEqual([l["numero"] for l in linhas], ["1", "9", "2", "3"])
        self.assertEqual([l["id_extracao"] for l in linhas], ["1", "2", "3", "4"])

    def test_vazios_do_vios_viram_nao_informado(self):
        reg = registro(data_acao="00/00/0000", valor_acao="0,00", tipo_processo="", orgao="", vara="", numero="",
                       ativa=(), passiva=(), fic=ficha(cidade_uf=""))
        linha = cr.montar_linhas([reg], hoje=HOJE)[0]
        for chave in ("data_distribuicao", "valor_acao", "orgao", "numero", "parte_ativa", "parte_passiva", "cidade_uf"):
            self.assertEqual(linha[chave], "não informado", chave)
        self.assertEqual(linha["tipo_processo"], "Cível Consumidor")  # cai para a área

    def test_dados_da_ficha_quando_a_lista_nao_tem(self):
        fic = ficha(cidade_uf="", data_distribuicao="2026-02-03", valor_acao="1.234,56",
                    campos={"Cidade / UF": "Outra Cidade / PI", "Parte ativa": "Autor: PESSOA A Autor: PESSOA B"})
        reg = registro(data_acao="", valor_acao="", ativa=(), fic=fic)
        linha = cr.montar_linhas([reg], hoje=HOJE)[0]
        self.assertEqual(linha["data_distribuicao"], "03/02/2026")
        self.assertEqual(linha["valor_acao"], "R$ 1.234,56")
        self.assertEqual(linha["cidade_uf"], "Outra Cidade / PI")
        self.assertEqual(linha["parte_ativa"], "PESSOA A, PESSOA B")

    def test_encerrado_no_numero(self):
        linhas = cr.montar_linhas([registro(ci="1", situacao="encerrado"), registro(ci="2", numero="2", situacao="ativo"),
                                   registro(ci="3", numero="3")], hoje=HOJE)
        self.assertEqual(linhas[0]["numero"], "0000001-11.2026.8.06.0001 (encerrado)")
        self.assertEqual([l["numero"] for l in linhas[1:]], ["2", "3"])
        self.assertTrue(cr.encerrado({"situacao": " Encerrado "}))
        self.assertFalse(cr.encerrado({}))

    def test_situacao_vai_para_a_ia(self):
        ia = IAFalsa()
        cr.montar_linhas([registro(situacao="encerrado")], ia=ia, hoje=HOJE)
        dados = json.loads(ia.chamadas[0]["usuario"])["processos"][0]
        self.assertEqual(dados["situacao"], "encerrado")

    def test_sem_valor_provisionado(self):
        # decisão do usuário (03/11/2026): o campo saiu, mesmo se o registro trouxer o valor
        obs = []
        linha = cr.montar_linhas([registro(valor_provisionado="7.000,00")], observacoes=obs, hoje=HOJE)[0]
        self.assertNotIn("valor_provisionado", linha)
        self.assertFalse(any("provisionado" in o.lower() for o in obs))

    def test_ficha_nao_lida(self):
        obs = []
        linha = cr.montar_linhas([registro(fic={"ok": False, "erro": "tempo"})], observacoes=obs, hoje=HOJE)[0]
        self.assertEqual(linha["ultima_movimentacao"], "não informado")
        self.assertEqual(linha["pendencia"], "não informado")
        self.assertEqual(linha["cidade_uf"], "não informado")
        self.assertTrue(any("Ficha de 1 processo" in o for o in obs))
        self.assertTrue(any("sem IA" in o for o in obs))


class TestPartes(Base):
    def test_tira_rotulos(self):
        self.assertEqual(cr.nomes_partes(["Autor: FULANO", "Autora: BELTRANA", "Reclamante: CICLANO"]),
                         "FULANO, BELTRANA, CICLANO")
        self.assertEqual(cr.nomes_partes("Contrário: EMPRESA A LTDA Contrário: EMPRESA B S/A"),
                         "EMPRESA A LTDA, EMPRESA B S/A")
        self.assertEqual(cr.nomes_partes(["Requerido(a): PESSOA X", "PESSOA X"]), "PESSOA X")
        self.assertEqual(cr.nomes_partes([]), "")


class TestSanitizar(Base):
    def test_zoom_com_senha_e_id(self):
        texto = ("Audiência dia 10/11/2026 às 9h. Link do zoom: https://us02web.zoom.us/j/8123456789?pwd=abcXYZ "
                 "ID da reunião: 812 345 6789 SENHA: 4f7Kq")
        limpo = cr.sanitizar(texto)
        self.assertEqual(limpo, "Audiência dia 10/11/2026 às 9h.")

    def test_lifesize_sem_http(self):
        limpo = cr.sanitizar("Sala lifesize: call.lifesizecloud.com/1234567 extensão 1234567 pwd=998877")
        for proibido in ("lifesizecloud", "1234567", "998877"):
            self.assertNotIn(proibido, limpo)

    def test_link_do_chat(self):
        limpo = cr.sanitizar("CONHECIMENTO - LINK DO CHAT: https://chat.exemplo.com/sala/123 fim")
        self.assertNotIn("LINK DO CHAT", limpo)
        self.assertNotIn("chat.exemplo", limpo)
        self.assertIn("fim", limpo)

    def test_email_e_telefone(self):
        limpo = cr.sanitizar("Falar com contato@escritorio-teste.adv.br, (85) 98765-4321, 85 3333-4444 "
                             "ou whatsapp 85 9 9876 5432. Valor R$ 1.000,00 no processo 0000001-11.2026.8.06.0001.")
        for proibido in ("@", "98765", "3333-4444", "9876 5432"):
            self.assertNotIn(proibido, limpo)
        self.assertIn("R$ 1.000,00", limpo)
        self.assertIn("0000001-11.2026.8.06.0001", limpo)

    def test_textos_automaticos_e_equipe(self):
        texto = ("Contestação protocolada.\nResponsáveis: PESSOA DA EQUIPE\n"
                 "Descrição do tipo da tarefa de origem: Analisar o processo e cadastrar prazos internos")
        self.assertEqual(cr.sanitizar(texto), "Contestação protocolada.")
        self.assertEqual(cr.sanitizar("Tarefa encerrada ao enviar o(s) arquivo(s): peticao.pdf"), "")
        self.assertEqual(cr.sanitizar("Revisado por Joana Exemplo Dias.", ["JOANA EXEMPLO DIAS"]), "Revisado por [equipe].")

    def test_frase_comum_fica(self):
        texto = "A senha foi enviada ao cliente e a extensão do dano será discutida."
        self.assertEqual(cr.sanitizar(texto), texto)

    def test_telefone_sem_mascara(self):
        self.assertEqual(cr.sanitizar("Contato do cliente: 85988887777"), "Contato do cliente")
        self.assertEqual(cr.sanitizar("Ligar 85 988887777 amanhã"), "Ligar amanhã")
        self.assertEqual(cr.sanitizar("Fixo (85)3333-4444 e cel 98765-4321."), "Fixo e.")
        # número de processo, datas e valores ficam
        texto = "Processo 00000011120268060001 de 03/11/2026, valor R$ 1.234.567,89, protocolo 2026.0001234."
        self.assertEqual(cr.sanitizar(texto), texto)

    def test_link_curto_e_senha_sem_dois_pontos(self):
        limpo = cr.sanitizar("Formulário em forms.gle/abcXyz e bit.ly/3abcXYZ. Senha 445566 enviada.")
        for proibido in ("forms.gle", "bit.ly", "abcXyz", "445566"):
            self.assertNotIn(proibido, limpo)
        self.assertIn("enviada", limpo)

    def test_sem_falso_positivo(self):
        for texto in ("Período 2019-2021 discutido no recurso.", "Contrário: Lojas Exemplo.com S/A.",
                      "Datas 10/2019-2021 citadas."):
            self.assertEqual(cr.sanitizar(texto), texto)


class TestTarefas(Base):
    def test_ultima_movimentacao_ignora_cancelada(self):
        tarefas = [tarefa(30, "AUDIÊNCIA", situacao="CANCELADA", descricao="cancelada", concluida="01/11/2026"),
                   tarefa(20, "PETICIONAR", descricao="Petição de juntada", concluida="15/10/2026"),
                   tarefa(10, "ANALISAR PROCESSO", comentarios="Antiga", concluida="01/09/2026")]
        self.assertEqual(cr.ultima_movimentacao(tarefas, HOJE), "15/10/2026 - PETICIONAR - Petição de juntada")

    def test_tarefa_aberta_nao_e_movimentacao(self):
        # aberta com prazo futuro ou vencido vai para a PENDÊNCIA; movimentação é só tarefa concluída
        tarefas = [tarefa(40, "AUDIÊNCIA", descricao="Audiência", para="20/11/2026"),
                   tarefa(39, "PRAZO", descricao="Manifestação", para="02/11/2026"),
                   tarefa(20, "PETICIONAR", comentarios="Ok", concluida="20/09/2026", para="19/09/2026")]
        self.assertEqual(cr.ultima_movimentacao(tarefas, HOJE), "20/09/2026 - PETICIONAR - Ok")
        self.assertEqual(cr.pendencia_sem_ia(tarefas), "PRAZO até 02/11/2026; AUDIÊNCIA até 20/11/2026")
        self.assertEqual(cr.ultima_movimentacao(tarefas[:2], HOJE), "Nenhuma movimentação registrada")

    def test_empate_de_data_vale_a_mais_nova(self):
        tarefas = [tarefa(7, "A", descricao="primeira", concluida="01/11/2026"),
                   tarefa(8, "B", descricao="segunda", concluida="01/11/2026")]
        self.assertEqual(cr.ultima_movimentacao(tarefas, HOJE), "01/11/2026 - B - segunda")

    def test_comentario_vale_mais_que_descricao_e_sai_limpo(self):
        t = tarefa(5, "ANALISAR PROCESSO", descricao="Ver https://pje.exemplo.jus.br",
                   comentarios="Processo na Turma Recursal. Link: https://x.exemplo.com SENHA: 123",
                   concluida="02/11/2026")
        self.assertEqual(cr.ultima_movimentacao([t], HOJE),
                         "02/11/2026 - ANALISAR PROCESSO - Processo na Turma Recursal.")

    def test_corta_em_300_caracteres(self):
        t = tarefa(5, "ANALISAR", comentarios="palavra " * 100, concluida="02/11/2026")
        texto = cr.ultima_movimentacao([t], HOJE)
        self.assertLessEqual(len(texto), 300)
        self.assertTrue(texto.endswith("..."))

    def test_sem_tarefas(self):
        self.assertEqual(cr.ultima_movimentacao([], HOJE), "Nenhuma movimentação registrada")
        self.assertEqual(cr.ultima_movimentacao([tarefa(1, "X", situacao="CANCELADA")], HOJE),
                         "Nenhuma movimentação registrada")

    def test_pendencia(self):
        tarefas = [tarefa(3, "AUDIÊNCIA", para="20/11/2026"),
                   tarefa(2, "PRAZO", limite="10/11/2026"),
                   tarefa(4, "RECURSO", situacao="CANCELADA", para="05/11/2026"),
                   tarefa(1, "ANALISAR", concluida="01/10/2026", para="30/09/2026")]
        self.assertEqual(cr.pendencia_sem_ia(tarefas), "PRAZO até 10/11/2026; AUDIÊNCIA até 20/11/2026")
        self.assertEqual(cr.pendencia_sem_ia([tarefas[3]]), "Nenhuma pendência registrada")


class TestIA(Base):
    def test_ia_em_blocos(self):
        regs = [registro(ci=str(i), numero=f"{i:07d}-11.2026.8.06.0001") for i in range(1, 8)]
        ia = IAFalsa()
        obs = []
        gasto = custo.Gasto()
        linhas = cr.montar_linhas(regs, ia=ia, gasto=gasto, modelo="gpt-5.6", bloco=3, observacoes=obs, hoje=HOJE)
        self.assertEqual(len(ia.chamadas), 3)
        self.assertEqual([len(json.loads(c["usuario"])["processos"]) for c in ia.chamadas], [3, 3, 1])
        self.assertEqual(ia.chamadas[0]["schema"], cr.SCHEMA_IA)
        self.assertEqual(ia.chamadas[0]["sistema"], cr.PROMPT_IA)
        self.assertEqual([l["resumo"] for l in linhas], [f"Resumo IA {i}" for i in range(1, 8)])
        self.assertTrue(all(l["pendencia"] == "Aguardando audiência" for l in linhas))
        self.assertGreater(gasto.total, 0)
        self.assertFalse(any("sem IA" in o for o in obs))

    def test_ia_recebe_dados_sanitizados(self):
        t = tarefa(1, "AUDIÊNCIA", descricao="zoom https://zoom.us/j/1 SENHA: abc", comentarios="tel (85) 98765-4321",
                   concluida="01/11/2026")
        fic = ficha([t], comentarios=[{"data": "01/11/2026 10:00", "autor": "PESSOA DA EQUIPE",
                                       "texto": "Cliente avisado por fulano@exemplo.com"}])
        ia = IAFalsa()
        cr.montar_linhas([registro(fic=fic)], ia=ia, hoje=HOJE)
        enviado = ia.chamadas[0]["usuario"]
        for proibido in ("zoom.us", "abc", "98765", "@exemplo", "PESSOA DA EQUIPE", '"ci"', "101"):
            self.assertNotIn(proibido, enviado)

    def test_resposta_da_ia_tambem_e_sanitizada(self):
        def resposta(dados):
            return {"processos": [{"id_extracao": 1, "resumo": "Ver https://site.exemplo.com",
                                   "pendencia": "", "financeira": ""}]}
        linha = cr.montar_linhas([registro()], ia=IAFalsa(resposta=resposta), hoje=HOJE)[0]
        self.assertEqual(linha["resumo"], "Ver")
        self.assertEqual(linha["financeira"], "não identificada")
        self.assertEqual(linha["pendencia"], "Nenhuma pendência registrada")

    def test_ia_falhando_cai_no_modo_sem_ia(self):
        obs, erros = [], []
        ia = IAFalsa(falhar=RuntimeError("erro de teste"))
        regs = [registro(ci=str(i), numero=str(i)) for i in range(1, 5)]
        linhas = cr.montar_linhas(regs, ia=ia, bloco=2, observacoes=obs, hoje=HOJE, ao_falhar=erros.append)
        # parou no 1º bloco: o resto também sai sem IA
        self.assertEqual(len(ia.chamadas), 1)
        self.assertEqual(len(erros), 1)
        self.assertTrue(all(l["resumo"].startswith("Ação Indenização") for l in linhas))
        self.assertTrue(all(l["financeira"] == "não identificada" for l in linhas))
        self.assertIn(cr.AVISO_SEM_IA_PARCIAL.format(n=4), obs)
        self.assertFalse(any("erro de teste" in o or "RuntimeError" in o for o in obs))

    def test_erro_da_api_nao_vai_para_o_pdf(self):
        obs = []
        erro = RuntimeError("Error code: 401 - Incorrect API key provided: sk-proj-abc********wxyz")
        cr.montar_linhas([registro()], ia=IAFalsa(falhar=erro), observacoes=obs, hoje=HOJE)
        self.assertIn(cr.AVISO_SEM_IA_PARCIAL.format(n=1), obs)
        for o in obs:
            for proibido in ("sk-proj", "401", "API key", "Error"):
                self.assertNotIn(proibido, o)

    def test_teto_de_gasto_nao_chama_a_ia(self):
        obs = []
        ia = IAFalsa()
        linhas = cr.montar_linhas([registro()], ia=ia, gasto=custo.Gasto(limite=0.000001), modelo="gpt-5.6",
                                  observacoes=obs, hoje=HOJE)
        self.assertEqual(ia.chamadas, [])
        self.assertTrue(linhas[0]["resumo"].startswith("Ação"))
        self.assertIn(cr.AVISO_SEM_IA_PARCIAL.format(n=1), obs)
        self.assertFalse(any("Teto" in o or "LLM_LIMITE_US" in o or "US$" in o for o in obs))

    def test_processo_faltando_na_resposta(self):
        def resposta(dados):
            return {"processos": [{"id_extracao": 2, "resumo": "Só o 2", "pendencia": "x", "financeira": "y"}]}
        obs = []
        regs = [registro(ci="1", numero="1"), registro(ci="2", numero="2")]
        linhas = cr.montar_linhas(regs, ia=IAFalsa(resposta=resposta), observacoes=obs, hoje=HOJE)
        self.assertTrue(linhas[0]["resumo"].startswith("Ação"))
        self.assertEqual(linhas[1]["resumo"], "Só o 2")
        self.assertTrue(any("não devolveu" in o and "1" in o for o in obs))


if __name__ == "__main__":
    unittest.main()
