"""Testes do PDF do relatório por Grupo Cliente (bot/pdf_relatorio.py).

Dados FICTÍCIOS. O pypdf não está instalado: o texto é conferido abrindo os fluxos do PDF
(zlib) e lendo as strings dos operadores de texto (Helvetica padrão = Windows-1252).
"""
import base64
import os
import re
import shutil
import stat
import sys
import tempfile
import types
import unittest
import zlib
from datetime import datetime
from pathlib import Path

# contrato 3: se bot/campos_relatorio ainda não existir, usa um COLUNAS idêntico só no teste
COLUNAS_CONTRATO = [
    ("id_extracao", "ID da extração"),
    ("numero", "Número do processo"),
    ("parte_ativa", "Parte ativa"),
    ("parte_passiva", "Parte passiva"),
    ("tipo_processo", "Tipo de processo"),
    ("orgao", "Órgão"),
    ("data_distribuicao", "Data da distribuição"),
    ("valor_acao", "Valor da ação"),
    ("cidade_uf", "Cidade/UF"),
    ("ultima_movimentacao", "Última movimentação"),
    ("resumo", "Resumo do caso"),
    ("pendencia", "PENDÊNCIA"),
    ("financeira", "Financeira"),
]
try:
    from bot.campos_relatorio import COLUNAS
except ImportError:
    COLUNAS = COLUNAS_CONTRATO
    falso = types.ModuleType("bot.campos_relatorio")
    falso.COLUNAS = COLUNAS
    sys.modules["bot.campos_relatorio"] = falso

from bot import pdf_relatorio as pr  # noqa: E402

GERADO = datetime(2026, 11, 3, 14, 5)
LONGO = ("Ação de cobrança movida pela empresa fictícia contra o cliente, com pedido de pagamento "
         "de R$ 12.345,67 – valores em discussão; audiência de conciliação nº 2 marcada. ") * 6


def linha(i, resumo=LONGO):
    cidades = ["Sobral/CE", "Fortaleza/CE", "Juazeiro do Norte/CE", ""]
    tipos = ["Trabalhista", "Cível", "Juizado Especial Cível"]
    return {
        "id_extracao": str(i),
        "numero": f"{i:07d}-11.2026.8.06.0001",
        "parte_ativa": f"Fulano de Tal Fictício {i}",
        "parte_passiva": "Comércio Imaginário & Filhos <Ltda>",
        "tipo_processo": tipos[i % 3],
        "orgao": "TJCE",
        "data_distribuicao": "15/03/2025",
        "valor_acao": "R$ 50.000,00",
        "cidade_uf": cidades[i % 4],
        "ultima_movimentacao": "02/11/2026 – Conclusos para decisão\nsegunda linha",
        "resumo": resumo,
        "pendencia": "Juntar procuração → prazo ≥ 5 dias ✓ 😀",
        "financeira": "Honorários: 20% (vinte por cento) — parcela 3ª",
    }


def _desescapar(s):
    s = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8)]), s)
    trocas = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"(": b"(", b")": b")", b"\\": b"\\"}
    return re.sub(rb"\\(.)", lambda m: trocas.get(m.group(1), m.group(1)), s, flags=re.S)


def texto_pdf(caminho):
    """Junta as strings dos operadores de texto (Tj/TJ) de todas as páginas."""
    bruto = Path(caminho).read_bytes()
    pedacos = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", bruto, re.S):
        cabecalho = bruto[max(0, m.start() - 200):m.start()]
        dados = m.group(1).strip()
        if b"ASCII85Decode" in cabecalho:  # o reportlab grava ASCII85 + Flate
            dados = re.sub(rb"\s", b"", dados)
            dados = base64.a85decode(dados[:-2] if dados.endswith(b"~>") else dados)
        try:
            dados = zlib.decompress(dados)
        except zlib.error:
            pass
        for s in re.findall(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", dados, re.S):
            pedacos.append(_desescapar(s).decode("cp1252"))
    return "\n".join(pedacos)


def paginas(caminho):
    return len(re.findall(rb"/Type\s*/Page[^s]", Path(caminho).read_bytes()))


class TestPdfRelatorio(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_colunas_do_contrato(self):
        self.assertEqual(COLUNAS, COLUNAS_CONTRATO)

    def test_um_processo(self):
        arq = pr.gerar_pdf(self.pasta / "um.pdf", "GRUPO TESTE", [linha(1)], GERADO,
                           observacoes=["Processo 2 sem ficha no sistema."])
        self.assertTrue(arq.exists())
        self.assertTrue(arq.read_bytes().startswith(b"%PDF"))
        txt = texto_pdf(arq)
        for _, titulo in COLUNAS:
            self.assertIn(titulo, txt, titulo)
        self.assertIn("Relatório de processos — GRUPO TESTE", txt)
        self.assertIn("Gerado em 03/11/2026 às 14:05", txt)
        self.assertIn("Total de processos: 1", txt)
        self.assertIn("ID 1 — 0000001-11.2026.8.06.0001", txt)
        n = paginas(arq)
        self.assertIn(f"Página 1 de {n}", txt)
        self.assertIn(f"Página {n} de {n}", txt)
        self.assertIn("Dúvidas sobre o andamento", txt)
        self.assertIn("Observações", txt)
        self.assertIn("Processo 2 sem ficha no sistema.", txt)
        # acentos e símbolos do português chegam intactos; & < > aparecem como texto
        # (o Paragraph corta o texto em pedaços nos "<" e ">": confere sem as quebras)
        plano = txt.replace("\n", "")
        for trecho in ("ç", "ã", "nº", "–", "R$", "3ª", "Comércio Imaginário & Filhos <Ltda>"):
            self.assertIn(trecho, plano, trecho)
        # fora do Windows-1252: trocado ou removido
        self.assertIn("Juntar procuração -> prazo >= 5 dias OK", plano)
        self.assertNotIn("😀", txt)

    def test_sessenta_processos(self):
        linhas = [linha(i) for i in range(1, 61)]
        arq = pr.gerar_pdf(self.pasta / "grande.pdf", "GRUPO GRANDE", linhas, GERADO)
        n = paginas(arq)
        self.assertGreater(n, 1)
        txt = texto_pdf(arq)
        self.assertIn("Total de processos: 60", txt)
        self.assertIn(f"Página {n} de {n}", txt)
        self.assertIn("ID 60 — 0000060-11.2026.8.06.0001", txt)
        for _, titulo in COLUNAS:
            self.assertIn(titulo, txt)
        # resumo por tipo: 20 de cada
        self.assertIn("Juizado Especial Cível", txt)
        self.assertIn("Não informado", txt)  # cidade vazia

    def test_total_com_encerrados(self):
        self.assertEqual(pr._total(10), "Total de processos: 10")
        self.assertEqual(pr._total(10, 3), "Total de processos: 10 (7 em andamento, 3 encerrados)")
        self.assertEqual(pr._total(2, 1), "Total de processos: 2 (1 em andamento, 1 encerrado)")
        self.assertEqual(pr._total(2, "x"), "Total de processos: 2")
        arq = pr.gerar_pdf(self.pasta / "enc.pdf", "GRUPO", [linha(1), linha(2)], GERADO, encerrados=1)
        self.assertIn("1 em andamento, 1 encerrado", texto_pdf(arq))

    @unittest.skipIf(os.name == "nt", "permissão Unix")
    def test_pdf_legivel_por_outros(self):
        arq = pr.gerar_pdf(self.pasta / "perm.pdf", "GRUPO", [linha(1)], GERADO)
        self.assertEqual(stat.S_IMODE(os.stat(arq).st_mode), 0o644)

    def test_resumo_maior_que_uma_pagina(self):
        enorme = "Texto fictício muito longo para o resumo do caso. " * 400
        arq = pr.gerar_pdf(self.pasta / "enorme.pdf", "G", [linha(1, resumo=enorme)], GERADO)
        self.assertGreater(paginas(arq), 1)

    def test_pasta_vira_nome_seguro(self):
        destino = self.pasta / "sub" / "dia"
        destino.mkdir(parents=True)
        arq = pr.gerar_pdf(destino, 'A/B: C*? "D" <E>|', [linha(1)], GERADO)
        self.assertEqual(arq.parent, destino)
        self.assertEqual(arq.name, "A-B- C-- -D- -E--.pdf")
        self.assertEqual(pr.nome_arquivo("CON"), "_CON.pdf")
        self.assertEqual(pr.nome_arquivo("  "), "relatorio.pdf")

    def test_cria_pasta_pai_e_sem_temporario(self):
        arq = pr.gerar_pdf(self.pasta / "nova" / "x" / "r.pdf", "G", [], GERADO)
        self.assertTrue(arq.exists())
        self.assertIn("Nenhum processo encontrado", texto_pdf(arq))
        self.assertEqual([p.name for p in arq.parent.iterdir()], ["r.pdf"])

    def test_chave_faltando_e_none(self):
        arq = pr.gerar_pdf(self.pasta / "f.pdf", "G", [{"id_extracao": "7", "numero": None}], GERADO)
        txt = texto_pdf(arq)
        self.assertIn("ID 7 — sem número", txt)
        self.assertIn("Não informado", txt)

    def test_limpar(self):
        self.assertEqual(pr.limpar("a�b​c\x07"), "abc")
        self.assertEqual(pr.limpar("ﬁm"), "fim")
        self.assertEqual(pr.limpar(None), "")
        self.assertEqual(pr.limpar("çãõº–—€R$"), "çãõº–—€R$")


if __name__ == "__main__":
    unittest.main()
