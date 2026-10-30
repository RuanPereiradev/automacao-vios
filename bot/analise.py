"""Agente de análise: decide as tarefas VIOS de cada intimação usando a skill da Controladoria.

Divisão de trabalho:
- IA (com a skill como instruções): lê a intimação, classifica, escolhe as tarefas
  da lista oficial, diz quantos dias de prazo e escreve os resumos;
- código: calcula as datas (dias úteis, feriados, D-2, prioridades), confere as
  regras fixas da skill e monta o relatório para revisão humana.
Nada é lançado no VIOS aqui.
"""
import json
import logging
import os
import re
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from bot import custo, duplicidade, feriados_web, ia, prazos, skill
from bot.custo import LimiteGasto
from bot.ia import IAErro

log = logging.getLogger(__name__)

MODELO_PADRAO = {"openai": "gpt-5.6", "anthropic": "claude-opus-5-5"}

SITUACOES = ["CABE", "NAO_CABE", "NAO_HOUVE_ABERTURA_DE_PRAZO", "PENDENTE_CONFIRMAR_CABIMENTO"]
TEXTO_SITUACAO = {
    "NAO_CABE": "NÃO CABE",
    "NAO_HOUVE_ABERTURA_DE_PRAZO": "NÃO HOUVE ABERTURA DE PRAZO",
    "PENDENTE_CONFIRMAR_CABIMENTO": "PENDENTE – CONFIRMAR CABIMENTO",
}
TIPOS_DATA = ["D-2", "PRIORIDADE_RPV", "PRIORIDADE_EMENDA_SUHIANE", "MESMO_DIA", "DIA_SEGUINTE", "DATA_INFORMADA", "SEM_DATA"]
PENDENTE = "PENDENTE – NÃO CONSTA NO DOCUMENTO"
CNJ = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
# tarefas com horário: data exata do ato (sem D-2) e horário no campo Horário do VIOS
COM_HORARIO = ("AUDIÊNCIA", "PERÍCIA TÉCNICA", "PERÍCIA MÉDICA", "SUSTENTAÇÃO ORAL", "SUSTENTACÃO ORAL")
HORA = re.compile(r"\b([01]?\d|2[0-3]) *(?::|H) *([0-5]\d)\b", re.I)
# eproc: "O ato refere-se ao seguinte evento: Evento 23 - 22/10/2026 - PETICAO" (sem o teor do evento)
SO_EVENTO = re.compile(r"refere-se ao seguinte evento: *(Evento \d+[^|]*)", re.I)
# linhas que não vão na descrição da tarefa (responsável vai no campo Responsáveis; revisão de 29/10).
# "PRIORIDADE RPV" voltou a ir na descrição com a skill de 30/10
FORA_DA_DESCRICAO = re.compile(r"^\s*(RESPONSÁVEL A MARCAR NA TAREFA|ADVOGADA? AUXILIAR)\b", re.I)
# sentença e acórdão sempre geram ANALISAR (o advogado decide se recorre)
ATOS_DE_ANALISE = {"SENTENÇA", "ACÓRDÃO"}

# Triagem (LLM_MODELO_SIMPLES): intimação que cita um destes atos vai direto para o
# modelo principal; as outras passam antes pelo modelo barato (texto sem acento)
IMPORTANTES = re.compile(r"\b(SENTENCA|ACORDAO|DECISAO|AUDIENCIA|RPV|REQUISICAO DE PEQUENO VALOR|PRECATORIO"
                         r"|TUTELA|LIMINAR|EMBARGOS|APELACAO|RECURSO)\b")
# nome da classe do processo ("Classe: Recurso Inominado", "Cumprimento de Sentença") não conta
NEUTROS = re.compile(r"\bCUMPRIMENTO D[AE] SENTENCA\b|\bCLASSE: *(RECURSO|APELACAO|AGRAVO|EMBARGOS)( \w+){0,3}")
# resposta do modelo barato com um destes atos é refeita pelo modelo principal
ATOS_IMPORTANTES = {"SENTENÇA", "ACÓRDÃO", "DECISÃO", "AUDIÊNCIA", "RPV/PRECATÓRIO", "PROPOSTA DE ACORDO"}

ADENDO = """
# MODO AUTOMÁTICO — instruções do programa que usa esta skill

Você está sendo chamado por um programa, UMA intimação por vez, e deve responder
somente no JSON do schema. Ignore os modelos de texto de resposta da skill: o
programa monta o relatório final a partir do JSON. Todas as regras de decisão da
skill continuam valendo.

Campos de entrada: `ci`, `auxiliares` (auxiliar da planilha), `cliente`,
`advogado`, `numeros`, `publicacao` e `disponibilizacao` (datas),
`informacoes_extras` (comarca, diário, esfera), `cidade`, `situacao`,
`sugestoes_tarefa` (sugestões automáticas do VIOS — apenas indício, nunca
decisão) e `texto` (teor integral). A data de hoje vem em `data_analise`.

Datas — NÃO calcule datas de prazo. O programa calcula prazo fatal, D-2,
próximo dia útil e prazos de embargos/recurso com calendário de feriados.
Você informa apenas:
- `prazo`: o prazo principal da providência (manifestação, emenda, pagamento,
  contrarrazões, quesitos...). `dias` = número de dias; se o ato não disser,
  use o prazo previsto em lei da skill (0 só se não houver prazo nem na lei);
  `contagem` = UTEIS ou CORRIDOS conforme as regras; `trecho` = frase da
  intimação onde está o prazo ("" se não houver).
- `embargos` e `recurso`: `situacao` e `dias` (0 quando não couber). Em
  `recurso.nome` diga qual recurso ("" se não couber). Quando o ato não
  informar os dias, use o prazo previsto em lei da skill, também se o
  cabimento estiver pendente. Se couber ou puder caber embargos ou recurso,
  `dias` nunca fica 0: o advogado decide se recorre e precisa da data.
- em cada tarefa, `tipo_data`:
  - `D-2`: data operacional = D-2 do prazo principal;
  - `PRIORIDADE_RPV`: RPV/precatório (dia útil seguinte à publicação);
  - `PRIORIDADE_EMENDA_SUHIANE`: emenda à inicial com auxiliar SUH;
  - `MESMO_DIA`: lançar para hoje (ex.: verificar viabilidade de sustentação e
    toda tarefa ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO — a análise fica para o mesmo
    dia; as datas de embargos e recurso vão só na descrição);
  - `DIA_SEGUINTE`: próximo dia útil (ex.: aviso e instrução de perícia social);
  - `DATA_INFORMADA`: a data do próprio ato (audiência, perícia, sessão de
    sustentação) — preencha `data_informada` com DD/MM/AAAA. Tarefa com horário
    (audiência, perícia, sustentação oral) NUNCA vai para o D-2: fica na data
    exata em que o ato acontece. Na sessão virtual, a data é o 1º dia da
    sessão (não o prazo de envio da sustentação gravada);
  - `SEM_DATA`: tarefa sem prazo (ex.: ciência).
  `data_informada` fica "" nos demais casos.
- `hora_informada`: horário do ato em HH:MM (audiência, perícia, sustentação
  oral; na sessão virtual, o horário de início), que o programa coloca no campo
  Horário do VIOS. "" quando a tarefa não tem horário.

Tarefas — `nome` deve ser exatamente um item da lista oficial. Em `resumo`
escreva a descrição que vai na tarefa do VIOS seguindo o modelo da tarefa, mas
SEM as linhas "PRAZO FATAL (D-2):", "PRAZO PARA EMBARGOS:", "PRAZO PARA RECURSO:",
"PRAZO FATAL:" e "DATA DA TAREFA NO VIOS" — o programa insere essas linhas com
as datas calculadas. Também não escreva "Responsável a marcar na tarefa:",
"Advogada auxiliar:" nem "PRIORIDADE RPV/PRECATÓRIO": responsáveis vão no campo
Responsáveis do VIOS. Audiência: exatamente o padrão da skill (AUDIÊNCIA [TIPO],
DATA, HORA, FORMATO, LINK/LOCAL, ID da reunião, SENHA), uma informação por linha,
sem parágrafos nem OBS. Coloque a tarefa principal primeiro e as complementares
depois.

Use `observacoes` para observações obrigatórias da skill (cadastro, duplicidade,
audiência de réu sem contestação etc.) e `pendencias` para o que precisa ser
confirmado. Não invente dados: use "PENDENTE – NÃO CONSTA NO DOCUMENTO".

`faltam_dados`: informações que a tarefa EXIGE e que não estão na intimação,
obrigando a consultar o PJe antes de lançar — ex.: audiência sem tipo, data,
horário, formato, local ou link/ID/senha (se virtual); perícia sem data,
horário ou local; data do ato que não consta. Se a lista não estiver vazia, o
programa NÃO lança a CI no VIOS. Deixe vazia quando a tarefa puder ser lançada
com o que a intimação traz (pendências de conferência não entram aqui).
Intimação que só indica um evento do processo, sem o teor (ex.: "O ato
refere-se ao seguinte evento: Evento 23 - PETIÇÃO"), não permite saber a
tarefa: coloque em `faltam_dados` o teor do evento (conferir no sistema) e
não use CIÊNCIA por falta de informação.

Área — conferir pelo departamento e também pelo auxiliar responsável: se o
auxiliar for só TAMI (Tamira, Departamento de Execução), a tarefa é de
Execução. Com auxiliar de outra área (JOAQ, JOAN, LILI, SUH, CARL, JOHN), não
use tarefa de Execução: o programa não lança a CI, por precisar confirmar o
departamento.
""".strip()


def schema(nomes_tarefas):
    texto = {"type": "string"}
    inteiro = {"type": "integer"}
    lista_texto = {"type": "array", "items": texto}

    def objeto(props):
        return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}

    return objeto({
        "cliente": texto,
        "posicao_cliente": texto,
        "do_que_se_trata": texto,
        "ato": {"type": "string", "enum": [
            "DISTRIBUIÇÃO", "DESPACHO", "DECISÃO", "SENTENÇA", "ACÓRDÃO", "AUDIÊNCIA", "PERÍCIA",
            "LAUDO", "PROPOSTA DE ACORDO", "CÁLCULOS", "RPV/PRECATÓRIO", "GUIAS", "DEPÓSITO JUDICIAL", "OUTRO",
        ]},
        "area": {"type": "string", "enum": ["CÍVEL", "TRABALHISTA", "PREVIDENCIÁRIO", "EXECUÇÃO", "PENDENTE"]},
        "prazo": objeto({"dias": inteiro, "contagem": {"type": "string", "enum": ["UTEIS", "CORRIDOS"]}, "trecho": texto}),
        "embargos": objeto({"situacao": {"type": "string", "enum": SITUACOES}, "dias": inteiro}),
        "recurso": objeto({"situacao": {"type": "string", "enum": SITUACOES}, "nome": texto, "dias": inteiro}),
        "cabe_recurso": texto,
        "tarefas": {"type": "array", "items": objeto({
            "nome": {"type": "string", "enum": nomes_tarefas + skill.ESPECIAIS},
            "finalidade": texto,
            "tipo_data": {"type": "string", "enum": TIPOS_DATA},
            "data_informada": texto,
            "hora_informada": texto,
            "resumo": texto,
        })},
        "observacoes": lista_texto,
        "pendencias": lista_texto,
        "faltam_dados": lista_texto,
    })


class Agente:
    def __init__(self, provedor, modelo, esforco, pasta_skill, tabela_feriados,
                 modelo_simples="", modelo_feriados="", gasto=None):
        self.ia = ia.criar(provedor, modelo, esforco)
        self.provedor, self.modelo = provedor, modelo
        # triagem: modelo barato para as intimações simples (vazio ou igual ao principal = desligada)
        self.modelo_simples = modelo_simples if modelo_simples and modelo_simples != modelo else ""
        self.ia_simples = ia.criar(provedor, self.modelo_simples, esforco) if self.modelo_simples else None
        self.modelo_feriados = modelo_feriados or modelo
        self.ia_feriados = ia.criar(provedor, self.modelo_feriados, esforco) if self.modelo_feriados != modelo else self.ia
        self.gasto = gasto or custo.Gasto()
        self.nomes = skill.tarefas_oficiais(pasta_skill)
        self.sistema = skill.carregar_texto(pasta_skill) + "\n\n" + ADENDO
        self.schema = schema(self.nomes)
        self.tabela = tabela_feriados

    @classmethod
    def do_env(cls, caminho_env=".env"):
        load_dotenv(caminho_env, override=True)
        provedor = os.getenv("LLM_PROVEDOR", "openai").strip().lower() or "openai"
        modelo = os.getenv("LLM_MODELO", "").strip() or MODELO_PADRAO.get(provedor, "")
        return cls(
            provedor,
            modelo,
            os.getenv("LLM_ESFORCO", "medium").strip(),
            os.getenv("SKILL_PASTA", "doc/analise-intimacoes-controladoria").strip(),
            _tabela_do_env(),
            os.getenv("LLM_MODELO_SIMPLES", "").strip(),
            os.getenv("LLM_MODELO_FERIADOS", "").strip(),
            custo.Gasto.do_env(),
        )

    def entrada(self, item, hoje):
        """Texto enviado à IA para uma intimação."""
        dados = {k: item.get(k, "") for k in (
            "ci", "auxiliares", "cliente", "advogado", "numeros", "publicacao", "disponibilizacao",
            "informacoes_extras", "cidade", "situacao", "sugestoes_tarefa", "texto",
        )}
        dados["data_analise"] = hoje.strftime("%d/%m/%Y")
        return json.dumps(dados, ensure_ascii=False, indent=1)

    def triagem(self, item):
        """Motivo para ir direto ao modelo principal ("" = começa pelo modelo barato)."""
        if not self.ia_simples:
            return "principal"
        # só o teor: as sugestões do VIOS quase sempre trazem "ANALISAR SENTENÇA..."
        texto = prazos.normalizar(item.get("texto", ""))
        m = IMPORTANTES.search(NEUTROS.sub(" ", texto))
        return f"texto cita {m.group(1)}" if m else ""

    def analisar(self, item, hoje=None):
        """Com triagem: intimação simples vai ao modelo barato; se a resposta mostrar que
        não era simples (reanalise()), é refeita pelo modelo principal."""
        hoje = hoje or date.today()
        motivo = self.triagem(item)
        if not motivo:
            r = self._chamar(self.ia_simples, self.modelo_simples, item, hoje)
            motivo = reanalise(r)
            if not motivo:
                return _marcar(r, self.modelo_simples, "simples")
            try:
                novo = self._chamar(self.ia, self.modelo, item, hoje)
            except LimiteGasto as e:
                return _marcar(r, self.modelo_simples, f"simples; precisava de reanálise ({motivo})", str(e))
            return _marcar(novo, self.modelo, f"reanalisada: {motivo}", custo_antes=r["custo_us"])
        return _marcar(self._chamar(self.ia, self.modelo, item, hoje), self.modelo,
                       "" if motivo == "principal" else motivo)

    def _chamar(self, cliente, modelo, item, hoje):
        entrada = self.entrada(item, hoje)
        self.gasto.conferir(self.gasto.estimar(modelo, self.sistema, entrada), f"análise da CI {item.get('ci')}")
        resposta = cliente.responder(self.sistema, entrada, self.schema)
        valor = self.gasto.registrar(modelo, resposta.get("_uso"))
        r = self._completar(item, resposta, hoje)
        r["custo_us"] = round(valor, 4)
        return r

    # ---- datas e regras fixas (código, não IA) ----

    def _fatal(self, publicacao, dias, corridos):
        if not publicacao or dias <= 0:
            return None
        return self.cal.prazo_fatal(publicacao, dias, corridos)

    def _meio(self, meio, publicacao, corridos):
        """Devolve (texto da linha, D-2, fatal) para embargos/recurso.
        Cabimento pendente também leva data: o advogado decide se recorre e precisa dela."""
        if meio["situacao"] not in ("CABE", "PENDENTE_CONFIRMAR_CABIMENTO"):
            return TEXTO_SITUACAO[meio["situacao"]], None, None
        fatal = self._fatal(publicacao, meio["dias"], corridos)
        if not fatal:
            return PENDENTE, None, None
        d2 = self.cal.d2(fatal)
        return _br(d2), d2, fatal

    def _completar(self, item, r, hoje):
        alertas = []
        # calendário próprio do processo (federal ou não, UF, cidade)
        self.cal = prazos.Calendario(self.tabela, *prazos.contexto(item))
        publicacao = _data(item.get("publicacao"))
        if not publicacao:
            alertas.append("Sem data de publicação: prazos não calculados.")
        corridos = r["prazo"]["contagem"] == "CORRIDOS"
        fatal = self._fatal(publicacao, r["prazo"]["dias"], corridos)
        d2 = self.cal.d2(fatal) if fatal else None
        if r["prazo"]["trecho"] and not fatal:
            alertas.append(f"Há prazo no texto (\"{r['prazo']['trecho']}\"), mas sem dias para calcular a data.")

        embargos, _, embargos_fatal = self._meio(r["embargos"], publicacao, corridos)
        recurso, _, recurso_fatal = self._meio(r["recurso"], publicacao, corridos)
        tarefas = []
        for t in r["tarefas"]:
            rotulo, data_tarefa = "", ""
            tipo = t["tipo_data"]
            if tipo == "D-2":
                rotulo, data_tarefa = "PRAZO FATAL (D-2)", _br(d2) if d2 else PENDENTE
            elif tipo in ("PRIORIDADE_RPV", "PRIORIDADE_EMENDA_SUHIANE"):
                rotulo = "PRAZO FATAL"
                data_tarefa = _br(self.cal.proximo_util(publicacao)) if publicacao else PENDENTE
            elif tipo == "MESMO_DIA":
                data_tarefa = _br(hoje)
            elif tipo == "DIA_SEGUINTE":
                data_tarefa = _br(self.cal.proximo_util(hoje))
            elif tipo == "DATA_INFORMADA":
                data_tarefa = t["data_informada"] if _data(t["data_informada"]) else PENDENTE
            if t["nome"].startswith("ANALISAR SENTENÇA"):
                # a análise fica para o mesmo dia; embargos e recurso (D-2) vão na descrição
                tipo, rotulo, data_tarefa = "MESMO_DIA", "", _br(hoje)
            hora = ""
            if t["nome"].startswith(COM_HORARIO):
                # data exata do ato, nunca D-2
                if tipo == "D-2":
                    tipo, rotulo = "DATA_INFORMADA", ""
                    data_tarefa = t["data_informada"] if _data(t["data_informada"]) else PENDENTE
                hora = _hora(t.get("hora_informada", "")) or _hora_do_resumo(t["resumo"])
            tarefas.append({
                "nome": t["nome"], "finalidade": t["finalidade"], "tipo_data": tipo,
                "data_tarefa": data_tarefa, "hora": hora, "rotulo_data": rotulo, "resumo": _limpar_resumo(t["resumo"]),
                "marcar_breno": "MINUTAR PETIÇÃO EXECUÇÃO" in t["nome"],
            })

        alertas += self._conferir(item, tarefas, d2)
        considerados, avisos_cal = self._feriados_do_periodo(publicacao, [fatal, embargos_fatal, recurso_fatal], alertas)

        # motivos para NÃO lançar no VIOS (falta informação que só o PJe ou a Controladoria têm)
        bloqueios = [f"Falta no documento: {f}" for f in r.get("faltam_dados", [])]
        bloqueios += self._conferir_area(item, tarefas)
        evento = SO_EVENTO.search(item.get("texto", ""))
        if evento:
            bloqueios.append(f"A intimação só indica o {evento.group(1).strip()}, sem o teor: "
                             "conferir o evento no sistema para definir a tarefa.")
        for t in tarefas:
            if t["nome"].startswith(COM_HORARIO) and t["tipo_data"] == "DATA_INFORMADA" and not t["hora"]:
                bloqueios.append(f"Falta o horário de {t['nome']} (vai no campo Horário do VIOS).")
        if r["ato"] in ATOS_DE_ANALISE and not any(t["nome"].startswith("ANALISAR SENTENÇA") for t in tarefas):
            bloqueios.append(f"{r['ato'].capitalize()} sem a tarefa ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO: "
                             "o advogado é quem decide se cabe recurso.")
        if any(t["nome"].startswith("ANALISAR SENTENÇA") for t in tarefas):
            for nome, texto in (("embargos", embargos), ("recurso", recurso)):
                if texto == PENDENTE:
                    bloqueios.append(f"Cabe {nome}, mas sem prazo para calcular a data.")

        for t in tarefas:
            t["descricao"] = _descricao(t, r["embargos"]["situacao"], r["recurso"]["situacao"], embargos, recurso, d2)

        return {
            "ci": item.get("ci", ""),
            "processo": _processo(item),
            "cliente": r["cliente"] or item.get("cliente", ""),
            "posicao_cliente": r["posicao_cliente"],
            "auxiliar": item.get("auxiliares", ""),
            "disponibilizacao": item.get("disponibilizacao", ""),
            "publicacao": item.get("publicacao", ""),
            "ato": r["ato"],
            "area": r["area"],
            "do_que_se_trata": r["do_que_se_trata"],
            "tarefas": tarefas,
            "prazo_fatal": _br(fatal) if fatal else ("" if not r["prazo"]["dias"] else PENDENTE),
            "prazo_d2": _br(d2) if d2 else "",
            "prazo_trecho": r["prazo"]["trecho"],
            "embargos": embargos,
            "recurso": recurso,
            "recurso_nome": r["recurso"]["nome"],
            "cabe_recurso": r["cabe_recurso"],
            "calendario": self.cal.descricao(),
            "feriados_considerados": considerados,
            "avisos_calendario": avisos_cal,
            "observacoes": list(r["observacoes"]),  # cópia: a duplicidade acrescenta avisos aqui, não na resposta da IA
            "pendencias": list(r["pendencias"]),
            "alertas": alertas,
            "bloqueios": bloqueios,
            "link_lancar": item.get("link_lancar", ""),
            "uso": r.pop("_uso", {}),
            "ia": r,  # resposta original da IA, para recalcular datas sem nova chamada
        }

    def _feriados_do_periodo(self, publicacao, fatais, alertas):
        """Lista feriados que entraram na contagem e avisa sobre os incertos (sem mudar a data)."""
        fatais = [f for f in fatais if f]
        if not publicacao or not fatais:
            return [], []
        considerados, avisos = self.cal.no_periodo(publicacao, max(fatais))
        considerados = [f"{_br(d)} {n}" for d, n in considerados]
        avisos = [f"{_br(d)} {n}" for d, n in avisos]
        for a in avisos:
            alertas.append(f"Dia não contado como feriado no prazo: {a}. Se o tribunal suspendeu o expediente, "
                           "os prazos vencem depois — conferir a portaria e cadastrar em doc/feriados.txt.")
        if not self.cal.federal and (self.cal.cidade, self.cal.uf) not in self.tabela.cidades() and not any(
            e == f"{self.cal.cidade}/{self.cal.uf}" for _, e, _, _ in self.tabela.manuais
        ):
            alertas.append(f"Feriados municipais de {self.cal.cidade}/{self.cal.uf} não cadastrados "
                           "(doc/feriados.txt): conferir se há feriado local no prazo.")
        return considerados, avisos

    def _conferir_area(self, item, tarefas):
        """Área da tarefa × auxiliar responsável (departamento). Divergência = não lançar.
        Com mais de um auxiliar (ex.: "TAMI / SUH") só a IA decide."""
        aux = [a.strip().upper() for a in re.split(r"[/,;]", item.get("auxiliares", "")) if a.strip()]
        if len(aux) != 1:
            return []
        aux, nomes = aux[0], [t["nome"] for t in tarefas]
        exec_ = any("EXECUÇÃO" in n or "EXECUCÃO" in n for n in nomes)
        outra = any(a in n for n in nomes for a in ("(CÍVEL)", "(TRABALHISTA)", "PREVIDENCI"))
        if aux == "TAMI" and outra and not exec_:
            return ["Auxiliar TAMI (Execução), mas a tarefa é de outra área: confirmar o departamento."]
        if aux in ("JOAQ", "JOAN", "LILI", "SUH", "CARL", "JOHN") and exec_:
            return [f"Tarefa de Execução com auxiliar {aux}: confirmar se o processo já foi transferido para a Execução (Tamira)."]
        if aux == "SUH" and any("(CÍVEL)" in n for n in nomes):
            return ["Auxiliar SUH: a tarefa deveria ser Trabalhista — Reclamante ou Previdenciário."]
        return []

    def _conferir(self, item, tarefas, d2):
        """Regras fixas da skill conferidas pelo código. Só alerta; não muda a decisão da IA,
        exceto a data da instrução de perícia social (tem que ser a mesma do aviso)."""
        alertas = []
        nomes = [t["nome"] for t in tarefas]

        for n in nomes:
            if n in skill.ESPECIAIS:
                alertas.append(f"Tarefa não definida: {n}")
        if not tarefas:
            alertas.append("Nenhuma tarefa indicada.")

        def tem(trecho):
            return any(trecho in n for n in nomes)

        if tem("PERÍCIA SOCIAL"):
            instr = [t for t in tarefas if t["nome"].startswith("INSTRUÇÃO PERÍCIA SOCIAL")]
            aviso = [t for t in tarefas if "PERÍCIA SOCIAL" in t["nome"] and not t["nome"].startswith("INSTRUÇÃO")]
            if not instr:
                alertas.append("Perícia social sem a tarefa INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026.")
            elif aviso:
                for t in instr:
                    t["data_tarefa"] = aviso[0]["data_tarefa"]
        if tem("VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL") and not any(
            n.startswith("SUSTENTAÇÃO ORAL") or n.startswith("SUSTENTACÃO ORAL") for n in nomes
        ):
            alertas.append("Verificar viabilidade de sustentação sem a tarefa SUSTENTAÇÃO ORAL.")
        if tem("PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO)") and not tem("IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO)"):
            alertas.append("Perícia médica previdenciária sem a tarefa de quesitos/assistente técnico.")

        if d2:
            for t in tarefas:
                ato = _data(t["data_tarefa"]) if t["tipo_data"] == "DATA_INFORMADA" else None
                if ato and ato <= d2:
                    alertas.append(f"O ato de {t['data_tarefa']} é antes do D-2 ({_br(d2)}): antecipar a data da tarefa.")
        return alertas


def _tabela_do_env():
    return prazos.Tabela(
        os.getenv("FERIADOS_TABELA", "doc/feriados-brasil-2026-2027.md").strip(),
        os.getenv("FERIADOS_ARQUIVO", "doc/feriados.txt").strip(),
    )


def _br(dia):
    return dia.strftime("%d/%m/%Y")


def _data(texto):
    try:
        return datetime.strptime((texto or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _datas(resultados, campo):
    """Datas distintas do campo, em ordem ("27/10/2026" ou "23/10/2026, 24/10/2026")."""
    dias = sorted({d for d in (_data(r.get(campo)) for r in resultados) if d})
    return ", ".join(_br(d) for d in dias)


def _hora(texto):
    m = HORA.search(texto or "")
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def _hora_do_resumo(resumo):
    """Respostas antigas (sem hora_informada): horário da linha "HORA:" do resumo."""
    m = re.search(r"^ *HORA:(.*)$", resumo or "", re.M | re.I)
    return _hora(m.group(1)) if m else ""


def _processo(item):
    achados = CNJ.findall(item.get("numeros", ""))
    return achados[0] if achados else PENDENTE


def _limpar_resumo(resumo):
    """Tira do texto da IA as linhas que não vão na descrição (FORA_DA_DESCRICAO)."""
    return "\n".join(l for l in resumo.strip().splitlines() if not FORA_DA_DESCRICAO.match(l)).strip()


def _descricao(t, sit_embargos, sit_recurso, embargos, recurso, d2=None):
    """Na análise (tarefa do mesmo dia): se cabe (ou pode caber) embargos ou recurso, as
    duas linhas com data em D-2; se não cabe nenhum, o PRAZO FATAL (D-2) do ato, se houver."""
    linhas = []
    if t["nome"].startswith("ANALISAR SENTENÇA"):
        if {sit_embargos, sit_recurso} & {"CABE", "PENDENTE_CONFIRMAR_CABIMENTO"}:
            linhas += [f"PRAZO PARA EMBARGOS: {embargos}", f"PRAZO PARA RECURSO: {recurso}"]
        elif d2:
            linhas.append(f"PRAZO FATAL (D-2): {_br(d2)}")
    elif t["rotulo_data"]:
        linhas.append(f"{t['rotulo_data']}: {t['data_tarefa']}")
    linhas.append(t["resumo"])
    return "\n".join(linhas)


def _duplicidades(resultados, itens):
    """Mesma publicação em mais de uma CI: a mais completa é a original e a outra é
    ignorada (duplicada_de). Mesmo processo com atos diferentes só gera alerta."""
    duplicadas = duplicidade.detectar(itens)
    por_ci = {r["ci"]: r for r in resultados}
    for ci, d in duplicadas.items():
        r, original = por_ci.get(ci), por_ci.get(d["original"])
        if not r or not original:
            continue
        r["duplicada_de"] = d["original"]
        r["duplicidade"] = d
        r.setdefault("alertas", []).append(
            f"DUPLICADA DA CI {d['original']} ({d['motivo']}). Não abrir nova tarefa: "
            "esta CI é ignorada no lançamento e vale a tarefa da CI original.")
        original.setdefault("duplicatas", []).append(ci)
    for r in resultados:
        if r.get("duplicatas"):
            r.setdefault("observacoes", []).append(
                f"CI original: a(s) CI(s) {', '.join(r['duplicatas'])} é(são) cópia(s) desta e será(ão) ignorada(s).")

    por_processo = {}
    for r in resultados:
        if r.get("processo") and r["processo"] != PENDENTE and not r.get("duplicada_de"):
            por_processo.setdefault(r["processo"], []).append(r["ci"])
    for r in resultados:
        if r.get("duplicada_de"):
            continue
        outras = [ci for ci in por_processo.get(r.get("processo"), []) if ci != r["ci"]]
        if outras:
            r["alertas"].append(f"Mesmo processo da(s) CI(s) {', '.join(outras)}, com ato diferente: "
                                "conferir se a tarefa deve ser atualizada em vez de abrir outra.")


def _erro_fatal(agente, e):
    """Erro que vale para todas as CIs (chave, modelo, créditos): para a análise."""
    if type(e).__name__ in ("AuthenticationError", "PermissionDeniedError", "NotFoundError"):
        raise e  # chave/modelo errado: não adianta tentar as outras
    if any(m in str(e).lower() for m in ("insufficient_quota", "credit_balance", "credit balance",
                                         "billing_hard_limit", "billing hard limit")):
        raise IAErro(f"Sem créditos na API da IA ({agente.provedor}): adicionar créditos e rodar de novo") from e


def _resultado_erro(item, e):
    return {"ci": item.get("ci", ""), "processo": _processo(item), "cliente": item.get("cliente", ""),
            "erro": str(e), "alertas": [f"ERRO NA ANÁLISE: {e}"]}


def reanalise(r):
    """Motivo para o modelo principal refazer a resposta do modelo barato ("" = pode ficar)."""
    ia_ = r.get("ia") or {}
    if r.get("erro"):
        return "erro no modelo barato"
    if r.get("ato") in ATOS_IMPORTANTES:
        return f"ato {r['ato']}"
    for nome in ("embargos", "recurso"):
        if (ia_.get(nome) or {}).get("situacao") in ("CABE", "PENDENTE_CONFIRMAR_CABIMENTO"):
            return f"{nome} cabe ou pode caber"
    if r.get("area") == "PENDENTE":
        return "área pendente"
    if r.get("bloqueios"):
        return "bloqueio: " + r["bloqueios"][0]
    if any(a.startswith(("Tarefa não definida", "Nenhuma tarefa", "Há prazo no texto")) for a in r.get("alertas", [])):
        return "tarefa ou prazo indefinido"
    if r.get("prazo_fatal") == PENDENTE or any(t["data_tarefa"] == PENDENTE for t in r.get("tarefas", [])):
        return "data pendente"
    return ""


def _marcar(r, modelo, triagem, bloqueio="", custo_antes=0.0):
    """Anota no resultado qual modelo analisou e por quê; bloqueio = não lançar no VIOS."""
    r["modelo"], r["triagem"] = modelo, triagem
    if custo_antes:
        r["custo_us"] = round(r.get("custo_us", 0) + custo_antes, 4)
    if bloqueio:
        r["bloqueio_triagem"] = bloqueio
        r.setdefault("bloqueios", []).append(f"Não reanalisada pelo modelo principal: {bloqueio}")
    return r


def analisar_lista(agente, itens, arquivo_lote=None):
    """Analisa as intimações. Com arquivo_lote (e provedor com lote), usa a Batch API
    (metade do preço); o que o lote não devolver é analisado uma a uma."""
    por_ci = {}
    pendentes = itens
    if arquivo_lote and getattr(agente.ia, "suporta_lote", False) and len(itens) > 1:
        por_ci = _analisar_em_lote(agente, itens, Path(arquivo_lote))
        pendentes = [i for i in itens if i.get("ci") not in por_ci]
        if pendentes:
            log.warning("Lote: %d CI(s) sem resposta, analisando uma a uma (preço normal)", len(pendentes))
    for n, item in enumerate(pendentes, 1):
        log.info("Analisando %d/%d: CI %s", n, len(pendentes), item.get("ci"))
        try:
            por_ci[item.get("ci")] = agente.analisar(item)
        except LimiteGasto as e:
            log.warning("CI %s: %s", item.get("ci"), e)
            por_ci[item.get("ci")] = _resultado_erro(item, e)
        except Exception as e:
            _erro_fatal(agente, e)
            log.exception("CI %s: falha na análise", item.get("ci"))
            por_ci[item.get("ci")] = _resultado_erro(item, e)
    resultados = [por_ci[i.get("ci")] for i in itens]  # mantém a ordem original
    _duplicidades(resultados, itens)
    return resultados


def _analisar_em_lote(agente, itens, arquivo_lote):
    """Análise pela Batch API, em até duas rodadas:
    1. intimações importantes (triagem) num lote do modelo principal e as simples num
       lote do modelo barato (sem triagem, tudo no principal);
    2. as respostas do barato que não eram simples (reanalise()) num lote do principal.
    O estado de cada lote fica em arquivo_lote (+ sufixo da etapa): se o programa cair,
    rodar de novo retoma os mesmos lotes (já pagos). Passou de LLM_LOTE_ESPERA_MIN,
    cancela e usa só o que ficou pronto. Devolve {ci: resultado}."""
    estados = []
    prazo = time.monotonic() + float(os.getenv("LLM_LOTE_ESPERA_MIN", "360")) * 60
    hoje = _hoje_do_lote(arquivo_lote) or date.today()
    por_ci, triagem = {}, {i.get("ci"): agente.triagem(i) for i in itens}

    rodada = []
    simples = [i for i in itens if not triagem[i.get("ci")]]
    if simples:
        rodada.append((agente.ia_simples, agente.modelo_simples, simples, "simples"))
    principais = [i for i in itens if triagem[i.get("ci")]]
    if principais:
        rodada.append((agente.ia, agente.modelo, principais, "principal"))
    lotes = []
    for cliente, modelo, grupo, etapa in rodada:
        grupo = _dentro_do_teto(agente, modelo, grupo, por_ci)
        if grupo:
            arquivo = arquivo_lote.with_name(f"{arquivo_lote.stem}_{etapa}.json")
            try:
                lotes.append((cliente, modelo, grupo, _enviar_lote(agente, cliente, modelo, grupo, arquivo, hoje)))
            except Exception as e:
                _erro_fatal(agente, e)  # sem créditos/chave errada: mensagem clara e para
                raise
            estados.append(arquivo)

    reanalisar = []
    for cliente, modelo, grupo, lote in lotes:
        for ci, r in _receber_lote(agente, cliente, modelo, grupo, lote, prazo, hoje).items():
            if modelo == agente.modelo_simples:
                motivo = reanalise(r)
                if motivo:
                    reanalisar.append((ci, r, motivo))
                    continue
                por_ci[ci] = _marcar(r, modelo, "simples")
            else:
                por_ci[ci] = _marcar(r, modelo, "" if triagem[ci] == "principal" else triagem[ci])
        # simples sem resposta do lote: vão direto para o principal
        for item in grupo:
            if modelo == agente.modelo_simples and item.get("ci") not in por_ci \
                    and all(item.get("ci") != ci for ci, _, _ in reanalisar):
                reanalisar.append((item.get("ci"), None, "sem resposta do modelo barato"))

    if reanalisar:
        log.info("Triagem: %d CI(s) do modelo barato vão para o modelo principal", len(reanalisar))
        itens_por_ci = {i.get("ci"): i for i in itens}
        grupo = [itens_por_ci[ci] for ci, _, _ in reanalisar]
        cabem = {i.get("ci") for i in _dentro_do_teto(agente, agente.modelo, grupo, {})}
        grupo = [i for i in grupo if i.get("ci") in cabem]
        novos = {}
        if len(grupo) > 0:
            arquivo = arquivo_lote.with_name(f"{arquivo_lote.stem}_reanalise.json")
            lote = _enviar_lote(agente, agente.ia, agente.modelo, grupo, arquivo, hoje)
            estados.append(arquivo)
            novos = _receber_lote(agente, agente.ia, agente.modelo, grupo, lote, prazo, hoje)
        for ci, antigo, motivo in reanalisar:
            if ci in novos:
                por_ci[ci] = _marcar(novos[ci], agente.modelo, f"reanalisada: {motivo}",
                                     custo_antes=(antigo or {}).get("custo_us", 0))
            elif antigo is None:
                continue  # sem resposta de nenhum modelo: analisar_lista faz uma a uma
            elif ci in cabem:
                # o lote do principal falhou para esta CI: tenta uma a uma
                try:
                    por_ci[ci] = _marcar(agente._chamar(agente.ia, agente.modelo, itens_por_ci[ci], hoje),
                                         agente.modelo, f"reanalisada: {motivo}", custo_antes=antigo.get("custo_us", 0))
                except Exception as e:
                    _erro_fatal(agente, e)
                    log.warning("CI %s: reanálise pelo modelo principal falhou (%s)", ci, e)
                    por_ci[ci] = _marcar(antigo, agente.modelo_simples, f"simples; precisava de reanálise ({motivo})", str(e))
            else:
                por_ci[ci] = _marcar(antigo, agente.modelo_simples, f"simples; precisava de reanálise ({motivo})",
                                     f"teto de gasto (LLM_LIMITE_US={agente.gasto.limite:g})")

    for arquivo in estados:
        arquivo.unlink(missing_ok=True)
    return por_ci


def _hoje_do_lote(arquivo_lote):
    """Data de análise de um lote já enviado (para retomar com as mesmas datas)."""
    for arquivo in sorted(arquivo_lote.parent.glob(f"{arquivo_lote.stem}_*.json")):
        try:
            return _data(json.loads(arquivo.read_text(encoding="utf-8")).get("hoje"))
        except (ValueError, OSError):
            continue
    return None


def _dentro_do_teto(agente, modelo, grupo, por_ci):
    """Itens do grupo que cabem no teto de gasto; os outros viram erro em por_ci (não são lançados)."""
    cabem = []
    for item in grupo:
        estimativa = agente.gasto.estimar(modelo, agente.sistema, agente.entrada(item, date.today()), lote=True)
        if agente.gasto.cabe(estimativa):
            agente.gasto.reservado += estimativa
            cabem.append(item)
        else:
            por_ci[item.get("ci")] = _resultado_erro(item, LimiteGasto(
                f"Teto de gasto atingido (LLM_LIMITE_US={agente.gasto.limite:g}): CI não analisada"))
    if len(cabem) < len(grupo):
        log.warning("Teto de gasto: %d de %d CI(s) ficaram de fora do lote (%s)", len(grupo) - len(cabem), len(grupo), modelo)
    return cabem


def _enviar_lote(agente, cliente, modelo, grupo, arquivo, hoje):
    """Envia (ou retoma, se arquivo tem um lote com as mesmas CIs e modelo) e devolve o estado."""
    cis = [i.get("ci") for i in grupo]
    estado = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    if estado.get("cis") == cis and estado.get("modelo") == modelo:
        log.info("Lote: retomando %s (%s, enviado em %s)", estado["lote_id"], modelo, estado["enviado_em"])
        return estado
    pedidos = [(i.get("ci"), agente.entrada(i, hoje)) for i in grupo]
    lote_id = cliente.enviar_lote(agente.sistema, pedidos, agente.schema, descricao=arquivo.stem)
    estado = {"lote_id": lote_id, "cis": cis, "modelo": modelo, "hoje": _br(hoje),
              "enviado_em": f"{datetime.now():%d/%m/%Y %H:%M}"}
    arquivo.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Lote: %d intimações enviadas (%s, %s), aguardando a IA", len(pedidos), modelo, lote_id)
    return estado


def _receber_lote(agente, cliente, modelo, grupo, estado, prazo, hoje):
    """Espera o lote terminar (cancela depois do prazo) e devolve {ci: resultado} do que veio."""
    lote_id = estado["lote_id"]
    intervalo = float(os.getenv("LLM_LOTE_INTERVALO_S", "60"))
    ultimo, cancelado = None, False
    while True:
        status, prontos, falhas, total = cliente.status(lote_id)
        if (status, prontos, falhas) != ultimo:
            log.info("Lote %s: %s — %d de %d prontas, %d com erro", modelo, status, prontos, total, falhas)
            ultimo = (status, prontos, falhas)
        if status in ("completed", "failed", "expired", "cancelled"):
            break
        if not cancelado and time.monotonic() > prazo:
            log.warning("Lote: passou de LLM_LOTE_ESPERA_MIN, cancelando (o que ficou pronto é aproveitado)")
            cliente.cancelar(lote_id)
            cancelado = True
        time.sleep(intervalo)

    por_ci, itens_por_ci = {}, {i.get("ci"): i for i in grupo}
    for item in grupo:  # libera a reserva: daqui em diante vale o custo real
        agente.gasto.reservado -= agente.gasto.estimar(modelo, agente.sistema, agente.entrada(item, date.today()), lote=True)
    agente.gasto.reservado = max(agente.gasto.reservado, 0.0)
    for ci, dados in cliente.resultados(lote_id).items():
        item = itens_por_ci.get(ci)
        if item is None:
            continue
        if isinstance(dados, Exception):
            _erro_fatal(agente, dados)
            log.warning("CI %s: falha no lote (%s), vai ser analisada de novo", ci, dados)
            continue
        valor = agente.gasto.registrar(modelo, dados.get("_uso"), lote=True)
        try:
            por_ci[ci] = agente._completar(item, dados, hoje)
            por_ci[ci]["custo_us"] = round(valor, 4)
        except Exception as e:
            log.exception("CI %s: falha ao completar a análise do lote", ci)
            por_ci[ci] = _resultado_erro(item, e)
    return por_ci


def relatorio_md(resultados, agente, origem):
    linhas = [
        "# Análise de intimações",
        "",
        f"- Origem: `{origem}`",
        f"- Gerado em: {datetime.now():%d/%m/%Y %H:%M} — {agente.provedor} / {agente.modelo}"
        + (f" (triagem: simples com {agente.modelo_simples})" if getattr(agente, "modelo_simples", "") else ""),
        f"- Intimações: {len(resultados)} — com alerta: {sum(1 for r in resultados if r.get('alertas'))}",
        "- **Sugestão automática: revisar antes de lançar no VIOS.**",
    ]
    disponibilizadas, publicadas = _datas(resultados, "disponibilizacao"), _datas(resultados, "publicacao")
    if disponibilizadas:
        # o nome do arquivo leva a data de disponibilização; a publicação é o 1º dia útil seguinte
        linhas.append(f"- Intimações disponibilizadas em {disponibilizadas}"
                      + (f" (publicação em {publicadas})" if publicadas else "")
                      + ". O arquivo leva a data de disponibilização; considera-se publicada no 1º dia útil "
                        "seguinte (Lei 11.419/2006, art. 4º, § 3º) e o prazo conta da publicação.")
    if getattr(agente, "gasto", None) and agente.gasto.total:
        linhas.append(f"- Gasto estimado com a IA nesta execução: {agente.gasto.resumo()}")
    linhas.append("- Datas: dias úteis com feriados nacionais, Lei 5.010/66 (Justiça Federal), estaduais e "
                  "municipais da tabela de feriados e de doc/feriados.txt, recesso 20/12–20/01. "
                  "Pontos facultativos e feriados incertos não mudam a data: viram alerta ⚠.")
    for n, r in enumerate(resultados, 1):
        linhas += ["", "---", "", f"## {n}. CI {r['ci']} — Processo {r['processo']}", ""]
        linhas.append(f"**Cliente:** {r.get('cliente', '')}")
        if r.get("duplicada_de"):
            linhas += ["", f"**DUPLICADA DA CI {r['duplicada_de']}.** Não abrir nova tarefa. "
                           "Utilizar a tarefa indicada na CI mais completa."]
        if r.get("erro"):
            linhas += ["", f"**ERRO NA ANÁLISE:** {r['erro']}"]
            continue
        disp = f" · **Disponibilização:** {r['disponibilizacao']}" if r.get("disponibilizacao") else ""
        linhas += ["", f"**Auxiliar:** {r['auxiliar']} · **Área:** {r['area']} · **Ato:** {r['ato']}"
                       f"{disp} · **Publicação:** {r['publicacao']}"]
        if r.get("modelo"):
            linhas.append(f"Modelo: {r['modelo']}" + (f" ({r['triagem']})" if r.get("triagem") else ""))
        linhas += ["", "**Do que se trata:**", r["do_que_se_trata"]]
        for i, t in enumerate(r["tarefas"], 1):
            titulo = "Tarefa no VIOS" if i == 1 else f"Tarefa complementar {i - 1}"
            data = f" — data: {t['data_tarefa']}" if t["data_tarefa"] else ""
            data += f" às {t['hora']}" if t.get("hora") else ""
            linhas += ["", f"**{titulo}:** {t['nome']}{data}"]
            if t["finalidade"]:
                linhas.append(f"Finalidade: {t['finalidade']}")
            linhas += ["```text", t["descricao"], "```"]
        linhas += ["", f"**Prazo fatal:** {r['prazo_fatal'] or 'Não há'}"]
        if r["prazo_d2"]:
            linhas.append(f"**PRAZO FATAL (D-2):** {r['prazo_d2']}")
        if r["prazo_trecho"]:
            linhas.append(f"Trecho: \"{r['prazo_trecho']}\"")
        if r.get("calendario"):
            feriados = "; ".join(r["feriados_considerados"]) or "nenhum"
            linhas.append(f"Calendário: {r['calendario']} — feriados contados no prazo: {feriados}")
        linhas += ["", "**Cabe recurso?**", r["cabe_recurso"]]
        linhas += ["", f"PRAZO PARA EMBARGOS: {r['embargos']}", f"PRAZO PARA RECURSO: {r['recurso']}"]
        if r.get("bloqueios"):
            linhas += ["", "**NÃO SERÁ LANÇADA NO VIOS — conferir no PJe e lançar manualmente:**"]
            linhas += [f"- {b}" for b in r["bloqueios"]]
        obs = r["observacoes"] + [f"PENDENTE: {p}" for p in r["pendencias"]] + [f"⚠ {a}" for a in r["alertas"]]
        if obs:
            linhas += ["", "**Observação:**"] + [f"- {o}" for o in obs]
        if r["link_lancar"]:
            linhas += ["", f"[Lançar no VIOS]({r['link_lancar']})"]
    return "\n".join(linhas) + "\n"


def recalcular(arquivo_intimacoes, arquivo_analise, caminho_env=".env", hoje=None, feriados=False):
    """Refaz datas, conferências e relatório a partir das respostas da IA já salvas (sem custo de API).
    feriados=True pesquisa antes os feriados na internet (custo pequeno de API)."""
    load_dotenv(caminho_env, override=True)
    itens = {i["ci"]: i for i in json.loads(Path(arquivo_intimacoes).read_text(encoding="utf-8"))}
    if feriados:
        pesquisar_feriados(Agente.do_env(caminho_env), list(itens.values()), Path(arquivo_analise).parent)
    agente = Agente.__new__(Agente)
    agente.provedor, agente.modelo = "recalculado", os.getenv("LLM_MODELO", "")
    agente.tabela = _tabela_do_env()
    resultados = []
    for antigo in json.loads(Path(arquivo_analise).read_text(encoding="utf-8")):
        if "ia" not in antigo:
            resultados.append(antigo)
            continue
        novo = agente._completar(itens[antigo["ci"]], dict(antigo["ia"], _uso=antigo.get("uso", {})), hoje or date.today())
        if "custo_us" in antigo:
            novo["custo_us"] = antigo["custo_us"]
        if antigo.get("modelo"):
            _marcar(novo, antigo["modelo"], antigo.get("triagem", ""), antigo.get("bloqueio_triagem", ""))
        resultados.append(novo)
    _duplicidades(resultados, list(itens.values()))
    return resultados, agente


def pesquisar_feriados(agente, itens, pasta_saida):
    """Pesquisa na internet feriados/suspensões dos tribunais do lote (FERIADOS_PESQUISA=true,
    padrão) e recarrega o calendário. Falha na pesquisa não impede a análise."""
    if os.getenv("FERIADOS_PESQUISA", "true").strip().lower() in ("false", "0", "nao", "não"):
        return
    try:
        feriados_web.pesquisar(agente.ia_feriados, itens, agente.tabela,
                               os.getenv("FERIADOS_ARQUIVO", "doc/feriados.txt").strip(), pasta_saida,
                               gasto=agente.gasto, modelo=agente.modelo_feriados)
    except Exception:
        log.exception("Pesquisa de feriados falhou; seguindo com os feriados já cadastrados")
    agente.tabela = _tabela_do_env()


def analisar_arquivo(arquivo, caminho_env=".env", pasta_saida=None, cis=None):
    """Analisa um saida/intimacoes_*.json e grava analise_*.json e analise_*.md ao lado.
    cis = lista de CIs para analisar só essas (o arquivo de saída ganha o sufixo _ci-<CIs>)."""
    arquivo = Path(arquivo)
    itens = json.loads(arquivo.read_text(encoding="utf-8"))
    if cis:
        itens = [i for i in itens if i.get("ci") in cis]
        faltando = set(cis) - {i["ci"] for i in itens}
        if faltando:
            raise ValueError(f"CI(s) não encontrada(s) em {arquivo}: {', '.join(sorted(faltando))}")
    agente = Agente.do_env(caminho_env)
    pasta = Path(pasta_saida) if pasta_saida else arquivo.parent
    pesquisar_feriados(agente, itens, pasta)
    log.info("Agente: %s / %s%s — %d intimações", agente.provedor, agente.modelo,
             f" (triagem: simples com {agente.modelo_simples})" if agente.modelo_simples else "", len(itens))
    base = arquivo.stem.replace("intimacoes_", "analise_", 1)
    # lote (Batch API, metade do preço) só na análise completa; --ci analisa na hora
    lote = None if cis or os.getenv("LLM_LOTE", "true").strip().lower() in ("false", "0", "nao", "não") \
        else pasta / f"lote_{base}.json"
    resultados = analisar_lista(agente, itens, lote)

    if cis:
        base += "_ci-" + "-".join(cis)
    saida_json, saida_md = pasta / f"{base}.json", pasta / f"{base}.md"
    saida_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    saida_md.write_text(relatorio_md(resultados, agente, arquivo), encoding="utf-8")

    uso = [r.get("uso", {}) for r in resultados]
    log.info("Tokens: entrada %d (cache %d), saída %d",
             sum(u.get("entrada", 0) for u in uso), sum(u.get("entrada_cache", 0) for u in uso), sum(u.get("saida", 0) for u in uso))
    log.info("Gasto estimado com a IA: %s", agente.gasto.resumo())
    if agente.modelo_simples:
        log.info("Triagem: %d no modelo barato, %d no principal (%d reanalisadas)",
                 sum(1 for r in resultados if r.get("modelo") == agente.modelo_simples),
                 sum(1 for r in resultados if r.get("modelo") == agente.modelo),
                 sum(1 for r in resultados if str(r.get("triagem", "")).startswith("reanalisada")))
    erros = sum(1 for r in resultados if r.get("erro"))
    return saida_md, len(resultados), erros
