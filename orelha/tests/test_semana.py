"""Atrasadas da semana, dia a dia (nucleo/semana.py). Dados 100% fictícios."""
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from funcoes import agenda, prazos
from nucleo import semana

QUARTA = date(2026, 11, 4)
BASE = "https://exemplo.vios.com.br/"


def tarefa(titulo, dias_atras, responsavel="Ana Fictícia", n=1, hoje=QUARTA):
    dia = hoje - timedelta(days=dias_atras)
    return agenda.Evento(titulo, dia=dia, categoria="tarefa", conclusao=dia, limite=dia + timedelta(days=1),
                         responsavel=responsavel, link=f"{BASE}?pag=sys/processos/pxe.php&pxe_id={900400 + n}")


class TestSemana(unittest.TestCase):
    def test_inicio(self):
        self.assertEqual(semana.inicio_da_semana(QUARTA), date(2026, 11, 2))             # quarta: esta semana
        self.assertEqual(semana.inicio_da_semana(date(2026, 11, 2)), date(2026, 10, 26))  # segunda: a passada
        self.assertEqual(semana.inicio_da_semana(date(2026, 11, 8)), date(2026, 11, 2))   # domingo: esta

    def test_separar_e_html(self):
        tarefas = [tarefa("SEGUNDA", 2, n=1), tarefa("TERCA A", 1, "Bruno Fictício, Carla Fictícia", 2),
                   tarefa("TERCA B", 1, "Ana Fictícia", 3), tarefa("ANTIGA", 20, "", 4), tarefa("HOJE", 0, n=5)]
        itens, numeros = prazos.placar(tarefas, QUARTA)
        dias, hoje_itens, antes = semana.separar(itens, QUARTA)
        self.assertEqual([(d, [i.titulo for i in l]) for d, l in dias],
                         [(date(2026, 11, 2), ["SEGUNDA"]), (date(2026, 11, 3), ["TERCA B", "TERCA A"])])
        self.assertEqual([i.titulo for i in hoje_itens], ["HOJE"])
        self.assertEqual([i.titulo for i in antes], ["ANTIGA"])
        self.assertEqual(semana.responsavel(dias[1][1][1]), "Bruno Fictício")
        self.assertEqual(semana.responsavel(antes[0]), "Sem responsável identificado")

        pasta = Path(tempfile.mkdtemp())
        caminho = semana.gerar(itens, numeros, QUARTA, pasta, gerado_em=datetime(2026, 11, 4, 7, 30))
        html = caminho.read_text(encoding="utf-8")
        self.assertIn("Atrasadas da semana · 02/11 a 04/11/2026", html)
        self.assertIn("3 tarefas venceram nesta semana e continuam abertas; 1 é de antes da semana e 1 vence hoje.", html)
        self.assertIn('<details class="grupo" id="dia-2026-11-03">', html)
        self.assertIn("Terça-feira, 03/11 · ontem", html)
        self.assertIn("Todas as de antes da semana", html)
        self.assertIn("<td>Bruno Fictício</td>", html)
        self.assertNotIn("<script", html)  # sem JavaScript: abre e fecha com <details>

    def test_fim_de_semana_vazio_some(self):
        sexta = date(2026, 11, 6)
        itens, numeros = prazos.placar([tarefa("QUINTA", 1, hoje=sexta)], sexta)
        html = semana.montar_html(itens, numeros, sexta)
        self.assertNotIn("Sábado", html)
        segunda = date(2026, 11, 9)  # na segunda, a semana passada inteira: o sábado sem tarefa não aparece
        itens, numeros = prazos.placar([tarefa("SEXTA", 3, hoje=segunda)], segunda)
        html = semana.montar_html(itens, numeros, segunda)
        self.assertIn("Sexta-feira, 06/11 · há 3 dias", html)
        self.assertIn("Segunda-feira, 02/11", html)
        self.assertNotIn("Sábado, 07/11", html)


if __name__ == "__main__":
    unittest.main()
