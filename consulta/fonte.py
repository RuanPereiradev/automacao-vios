"""De onde vem o HTML das telas: o VIOS de verdade (Selenium) ou fixtures (memória/pasta).

Interface das fontes (o coletor só usa estes quatro métodos):
    lista_processos(cpf_texto) -> html     lista de processos ativos do CPF
    lista_pessoas(cpf_texto)   -> html     busca de pessoas pelo CPF
    form_pessoa(pessoa_id)     -> html     formulário act=edit, lido por GET sem enviar
    ficha(ci) -> (LeituraFicha, [textos de segredo])

Só leitura: GET de dentro da página já aberta (buscar_get) e abrir a ficha (que o Vue monta). Nada é
clicado nem enviado.
"""
import logging
import re
import time
from pathlib import Path
from types import SimpleNamespace

from consulta import leitura as lei
from consulta.erros import ConsultaErro, SessaoPerdida
from consulta.leitura import textos_de_segredo
from funcoes import parados
from nucleo import simulado, vios

log = logging.getLogger("consulta")

PAUSA_APOS_LOGIN_FALHO = 300  # s
_TELA_LOGIN = re.compile(r"""name=["']form\[senha\]["']""", re.I)
# só os textos que falam de segredo/sigilo voltam do navegador (o resto da ficha nem sai dele)
JS_SEGREDO = """
const saida = [];
document.querySelectorAll('.vj-bloco-info-text-area p, .vj-badge').forEach(e => {
    const t = (e.textContent || '').replace(/\\s+/g, ' ').trim();
    if (/segredo|sigilo/i.test(t)) saida.push(t.slice(0, 200));
});
return saida;
"""


class FonteVios:
    """VIOS real. Uma sessão do Chrome reaproveitada; reiniciar() fecha para entrar de novo."""

    def __init__(self, cfg, abrir_sessao=None):
        from consulta import sessao
        self.cfg = cfg
        self._abrir_sessao = abrir_sessao or sessao.abrir
        self.ctx = None
        self.leitor = None
        self.op = parados.opcoes(cfg)
        self.timeout_busca = cfg.valor("CONSULTA_TIMEOUT_BUSCA", 60, int)
        self._nao_antes = 0.0

    def _garantir(self):
        if self.ctx is None:
            if time.monotonic() < self._nao_antes:
                raise ConsultaErro("o login no VIOS falhou há pouco; nova tentativa em alguns minutos")
            try:
                self.ctx = self._abrir_sessao(self.cfg)
            except vios.BloqueioInativo:
                raise
            except Exception as e:  # noqa: BLE001 — não martela o login (conta pode travar)
                self._nao_antes = time.monotonic() + PAUSA_APOS_LOGIN_FALHO
                log.error("não consegui entrar no VIOS (%s); só tento de novo em %d min",
                          e.__class__.__name__, PAUSA_APOS_LOGIN_FALHO // 60)
                raise ConsultaErro("não consegui entrar no VIOS") from None
            self.leitor = parados.LeitorVios(self.ctx, self.op)
        return self.ctx

    def fechar(self):
        """Fecha primeiro o leitor (o "pesquisa_liberada" do XHR fala com o driver ao sair) e só depois o
        Chrome; erro de driver já fechado é engolido."""
        from consulta import sessao
        leitor, ctx = self.leitor, self.ctx
        self.ctx = self.leitor = None
        if leitor is not None:
            try:
                leitor.fechar()
            except Exception:  # noqa: BLE001 — driver já caiu: nada a desfazer
                pass
        sessao.fechar(ctx)

    reiniciar = fechar

    def _buscar(self, url):
        from selenium.common.exceptions import WebDriverException
        ctx = self._garantir()
        try:
            html = vios.buscar_get(ctx, url, self.timeout_busca)
        except WebDriverException:
            raise SessaoPerdida("navegador não respondeu") from None
        except vios.ViosErro as e:
            if str(e).startswith("ERRO_ORELHA"):
                raise SessaoPerdida("a busca por GET falhou") from None
            raise
        if _TELA_LOGIN.search(html):
            raise SessaoPerdida("a tela de login apareceu")
        return html

    def lista_processos(self, cpf_texto):
        return self._buscar(lei.url_lista_processos(cpf_texto))

    def lista_pessoas(self, cpf_texto):
        return self._buscar(lei.url_lista_pessoas(cpf_texto))

    def form_pessoa(self, pessoa_id):
        return self._buscar(lei.url_form_pessoa(pessoa_id))

    def ficha(self, ci):
        from selenium.common.exceptions import WebDriverException
        self._garantir()
        try:
            leitura = self.leitor.ficha(SimpleNamespace(ci=ci))
            textos = self.ctx.driver.execute_script(JS_SEGREDO) or []
        except parados.SessaoCaiu:
            raise SessaoPerdida("a tela de login apareceu na ficha") from None
        except WebDriverException:
            raise SessaoPerdida("navegador não respondeu na ficha") from None
        return leitura, [str(t) for t in textos]


class FonteMemoria:
    """HTML em dicionários (testes e modo simulado). Chave de lista/pessoas = CPF só com dígitos;
    formulários por id da pessoa; fichas por CI (página inteira, como o Vue deixa)."""

    def __init__(self, listas=None, pessoas=None, formularios=None, fichas=None):
        self.listas = dict(listas or {})
        self.pessoas = dict(pessoas or {})
        self.formularios = dict(formularios or {})
        self.fichas = dict(fichas or {})
        self.acessos = []   # o que foi pedido (para os testes conferirem o que o coletor lê)

    @staticmethod
    def _vazia(cpf):
        return ('<html><head><title>Processos</title></head><body><form><input name="pesq[cpfcnpj]" '
                f'value="{cpf}"></form><table class="geratabela"><thead><tr><th>CI</th></tr></thead>'
                "<tbody></tbody></table></body></html>")

    def lista_processos(self, cpf_texto):
        d = vios.digitos(cpf_texto)
        self.acessos.append(("lista_processos", d))
        return self.listas.get(d) or self._vazia(cpf_texto)

    def lista_pessoas(self, cpf_texto):
        d = vios.digitos(cpf_texto)
        self.acessos.append(("lista_pessoas", d))
        return self.pessoas.get(d, "<html><body><table></table></body></html>")

    def form_pessoa(self, pessoa_id):
        self.acessos.append(("form_pessoa", str(pessoa_id)))
        return self.formularios.get(str(pessoa_id), "<html><body></body></html>")

    def ficha(self, ci):
        self.acessos.append(("ficha", str(ci)))
        html = self.fichas.get(str(ci))
        if html is None:
            return parados.LeituraFicha(achou_tabela=False, erro="ficha não encontrada"), []
        return parados.ler_tarefas_html(html), textos_de_segredo(html)

    def fechar(self):
        pass

    reiniciar = fechar


class FonteSimulada(FonteMemoria):
    """Lê consulta/fixtures/ (dados 100% fictícios). Datas relativas: {{HOJE-5}}, {{ISO:HOJE}} (ver
    orelha/nucleo/simulado.py). Arquivos: processos-<cpf>.html, pessoas-<cpf>.html, pessoa-<id>.html,
    ficha-<ci>.html."""

    def __init__(self, pasta, hoje):
        super().__init__()
        pasta = Path(pasta)
        troca = lambda p: simulado.substituir(p.read_text(encoding="utf-8"), hoje)  # noqa: E731
        for arq in sorted(pasta.glob("*.html")):
            nome = arq.stem
            for prefixo, destino in (("processos-", self.listas), ("pessoas-", self.pessoas),
                                     ("pessoa-", self.formularios), ("ficha-", self.fichas)):
                if nome.startswith(prefixo):
                    destino[nome[len(prefixo):]] = troca(arq)
                    break
