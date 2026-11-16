"""Erros do coletor. As mensagens nunca levam CPF, telefone, nome ou CI."""


class SessaoPerdida(Exception):
    """A sessão do VIOS/Chrome caiu (tela de login, navegador fechado). O laço entra de novo e repete."""


class ConsultaErro(Exception):
    """Não deu para concluir a consulta (status "erro" para o bot). A mensagem é segura para o log."""
