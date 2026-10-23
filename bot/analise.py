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
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from bot import ia, prazos, skill

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
  contrarrazões, quesitos...). `dias` = número de dias (0 se não houver prazo);
  `contagem` = UTEIS ou CORRIDOS conforme as regras; `trecho` = frase da
  intimação onde está o prazo ("" se não houver).
- `embargos` e `recurso`: `situacao` e `dias` (0 quando não couber). Em
  `recurso.nome` diga qual recurso ("" se não couber).
- em cada tarefa, `tipo_data`:
  - `D-2`: data operacional = D-2 do prazo principal;
  - `PRIORIDADE_RPV`: RPV/precatório (dia útil seguinte à publicação);
  - `PRIORIDADE_EMENDA_SUHIANE`: emenda à inicial com auxiliar SUH;
  - `MESMO_DIA`: lançar para hoje (ex.: verificar viabilidade de sustentação);
  - `DIA_SEGUINTE`: próximo dia útil (ex.: aviso e instrução de perícia social);
  - `DATA_INFORMADA`: a data do próprio ato (audiência, perícia, sessão de
    sustentação) — preencha `data_informada` com DD/MM/AAAA;
  - `SEM_DATA`: tarefa sem prazo (ex.: ciência).
  `data_informada` fica "" nos demais casos.

Tarefas — `nome` deve ser exatamente um item da lista oficial. Em `resumo`
escreva a descrição que vai na tarefa do VIOS seguindo o modelo da tarefa, mas
SEM as linhas "PRAZO FATAL (D-2):", "PRAZO PARA EMBARGOS:", "PRAZO PARA RECURSO:",
"Responsável a marcar na tarefa:" e "DATA DA TAREFA NO VIOS" — o programa insere
essas linhas com as datas calculadas. Coloque a tarefa principal primeiro e as
complementares depois.

Use `observacoes` para observações obrigatórias da skill (cadastro, duplicidade,
audiência de réu sem contestação etc.) e `pendencias` para o que precisa ser
confirmado. Não invente dados: use "PENDENTE – NÃO CONSTA NO DOCUMENTO".
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
            "resumo": texto,
        })},
        "observacoes": lista_texto,
        "pendencias": lista_texto,
    })


class Agente:
    def __init__(self, provedor, modelo, esforco, pasta_skill, tabela_feriados):
        self.ia = ia.criar(provedor, modelo, esforco)
        self.provedor, self.modelo = provedor, modelo
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
        )

    def analisar(self, item, hoje=None):
        hoje = hoje or date.today()
        entrada = {k: item.get(k, "") for k in (
            "ci", "auxiliares", "cliente", "advogado", "numeros", "publicacao", "disponibilizacao",
            "informacoes_extras", "cidade", "situacao", "sugestoes_tarefa", "texto",
        )}
        entrada["data_analise"] = hoje.strftime("%d/%m/%Y")
        resposta = self.ia.responder(self.sistema, json.dumps(entrada, ensure_ascii=False, indent=1), self.schema)
        return self._completar(item, resposta, hoje)

    # ---- datas e regras fixas (código, não IA) ----

    def _fatal(self, publicacao, dias, corridos):
        if not publicacao or dias <= 0:
            return None
        return self.cal.prazo_fatal(publicacao, dias, corridos)

    def _meio(self, meio, publicacao, corridos):
        """Devolve (texto da linha, D-2, fatal) para embargos/recurso."""
        if meio["situacao"] != "CABE":
            return TEXTO_SITUACAO[meio["situacao"]], None, None
        fatal = self._fatal(publicacao, meio["dias"], corridos)
        if not fatal:
            return "PENDENTE – CONFIRMAR CABIMENTO", None, None
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

        embargos, embargos_d2, embargos_fatal = self._meio(r["embargos"], publicacao, corridos)
        recurso, recurso_d2, recurso_fatal = self._meio(r["recurso"], publicacao, corridos)
        # tarefa de análise vai para o D-2 mais cedo entre embargos, recurso e prazo principal
        datas_analise = [d for d in (embargos_d2, recurso_d2, d2) if d]

        tarefas = []
        for t in r["tarefas"]:
            rotulo, data_tarefa = "", ""
            tipo = t["tipo_data"]
            if tipo == "D-2":
                rotulo, data_tarefa = "PRAZO FATAL (D-2)", _br(d2) if d2 else PENDENTE
            elif tipo in ("PRIORIDADE_RPV", "PRIORIDADE_EMENDA_SUHIANE"):
                rotulo = "DATA DA TAREFA NO VIOS — " + ("PRIORIDADE RPV" if tipo == "PRIORIDADE_RPV" else "PRIORIDADE EMENDA/SUHIANE")
                data_tarefa = _br(self.cal.proximo_util(publicacao)) if publicacao else PENDENTE
            elif tipo == "MESMO_DIA":
                data_tarefa = _br(hoje)
            elif tipo == "DIA_SEGUINTE":
                data_tarefa = _br(self.cal.proximo_util(hoje))
            elif tipo == "DATA_INFORMADA":
                data_tarefa = t["data_informada"] if _data(t["data_informada"]) else PENDENTE
            if t["nome"].startswith("ANALISAR SENTENÇA") and datas_analise:
                data_tarefa = _br(min(datas_analise))
            tarefas.append({
                "nome": t["nome"], "finalidade": t["finalidade"], "tipo_data": tipo,
                "data_tarefa": data_tarefa, "rotulo_data": rotulo, "resumo": t["resumo"].strip(),
                "marcar_breno": "MINUTAR PETIÇÃO EXECUÇÃO" in t["nome"],
            })

        alertas += self._conferir(item, tarefas, d2)
        considerados, avisos_cal = self._feriados_do_periodo(publicacao, [fatal, embargos_fatal, recurso_fatal], alertas)

        for t in tarefas:
            t["descricao"] = _descricao(t, embargos, recurso, d2)

        return {
            "ci": item.get("ci", ""),
            "processo": _processo(item),
            "cliente": r["cliente"] or item.get("cliente", ""),
            "posicao_cliente": r["posicao_cliente"],
            "auxiliar": item.get("auxiliares", ""),
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
            "observacoes": r["observacoes"],
            "pendencias": r["pendencias"],
            "alertas": alertas,
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
            e == f"{self.cal.cidade}/{self.cal.uf}" for _, e, _ in self.tabela.manuais
        ):
            alertas.append(f"Feriados municipais de {self.cal.cidade}/{self.cal.uf} não cadastrados "
                           "(doc/feriados.txt): conferir se há feriado local no prazo.")
        return considerados, avisos

    def _conferir(self, item, tarefas, d2):
        """Regras fixas da skill conferidas pelo código. Só alerta; não muda a decisão da IA,
        exceto a data da instrução de perícia social (tem que ser a mesma do aviso)."""
        alertas = []
        nomes = [t["nome"] for t in tarefas]
        aux = item.get("auxiliares", "").upper()

        for n in nomes:
            if n in skill.ESPECIAIS:
                alertas.append(f"Tarefa não definida: {n}")
        if not tarefas:
            alertas.append("Nenhuma tarefa indicada.")

        def tem(trecho):
            return any(trecho in n for n in nomes)

        exec_ = tem("(EXECUÇÃO)") or tem("(EXECUCÃO)") or tem("EXECUÇÃO 2026")
        if "SUH" in aux and (tem("(CÍVEL)") or exec_):
            alertas.append("Auxiliar SUH: a tarefa deveria ser Trabalhista — Reclamante ou Previdenciário. Revisar.")
        if any(a in aux for a in ("JOAQ", "JOAN", "LILI")) and exec_:
            alertas.append(f"Tarefa de Execução com auxiliar {aux}: confirmar a transferência do processo para a Tamira.")
        if "TAMI" in aux and (tem("(CÍVEL)") or tem("(TRABALHISTA)") or tem("PREVIDENCI")):
            alertas.append("OBSERVAÇÃO DE CADASTRO: a tarefa não é de Execução, mas o processo aparece com a Tamira. Confirmar o auxiliar.")

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


def _processo(item):
    achados = CNJ.findall(item.get("numeros", ""))
    return achados[0] if achados else PENDENTE


def _descricao(t, embargos, recurso, d2):
    linhas = []
    if t["marcar_breno"]:
        linhas.append("Responsável a marcar na tarefa: BRENO")
    if t["nome"].startswith("ANALISAR SENTENÇA"):
        linhas += [f"PRAZO PARA EMBARGOS: {embargos}", f"PRAZO PARA RECURSO: {recurso}"]
        if d2:
            linhas.append(f"PRAZO FATAL (D-2): {_br(d2)}")
    elif t["rotulo_data"]:
        linhas.append(f"{t['rotulo_data']}: {t['data_tarefa']}")
    linhas.append(t["resumo"])
    return "\n".join(linhas)


def _duplicidades(resultados):
    por_processo = {}
    for r in resultados:
        if r.get("processo") and r["processo"] != PENDENTE:
            por_processo.setdefault(r["processo"], []).append(r["ci"])
    for r in resultados:
        outras = [ci for ci in por_processo.get(r.get("processo"), []) if ci != r["ci"]]
        if outras:
            r["alertas"].append(f"Mesmo processo da(s) CI(s) {', '.join(outras)}: conferir duplicidade antes de lançar.")


def analisar_lista(agente, itens):
    resultados = []
    for n, item in enumerate(itens, 1):
        log.info("Analisando %d/%d: CI %s", n, len(itens), item.get("ci"))
        try:
            resultados.append(agente.analisar(item))
        except Exception as e:
            if type(e).__name__ in ("AuthenticationError", "PermissionDeniedError", "NotFoundError"):
                raise  # chave/modelo errado: não adianta tentar as outras

            log.exception("CI %s: falha na análise", item.get("ci"))
            resultados.append({"ci": item.get("ci", ""), "processo": _processo(item), "cliente": item.get("cliente", ""),
                               "erro": str(e), "alertas": [f"ERRO NA ANÁLISE: {e}"]})
    _duplicidades(resultados)
    return resultados


def relatorio_md(resultados, agente, origem):
    linhas = [
        "# Análise de intimações",
        "",
        f"- Origem: `{origem}`",
        f"- Gerado em: {datetime.now():%d/%m/%Y %H:%M} — {agente.provedor} / {agente.modelo}",
        f"- Intimações: {len(resultados)} — com alerta: {sum(1 for r in resultados if r.get('alertas'))}",
        "- **Sugestão automática: revisar antes de lançar no VIOS.**",
    ]
    linhas.append("- Datas: dias úteis com feriados nacionais, Lei 5.010/66 (Justiça Federal), estaduais e "
                  "municipais da tabela de feriados e de doc/feriados.txt, recesso 20/12–20/01. "
                  "Pontos facultativos e feriados incertos não mudam a data: viram alerta ⚠.")
    for n, r in enumerate(resultados, 1):
        linhas += ["", "---", "", f"## {n}. CI {r['ci']} — Processo {r['processo']}", ""]
        linhas.append(f"**Cliente:** {r.get('cliente', '')}")
        if r.get("erro"):
            linhas += ["", f"**ERRO NA ANÁLISE:** {r['erro']}"]
            continue
        linhas += ["", f"**Auxiliar:** {r['auxiliar']} · **Área:** {r['area']} · **Ato:** {r['ato']} · **Publicação:** {r['publicacao']}"]
        linhas += ["", "**Do que se trata:**", r["do_que_se_trata"]]
        for i, t in enumerate(r["tarefas"], 1):
            titulo = "Tarefa no VIOS" if i == 1 else f"Tarefa complementar {i - 1}"
            data = f" — data: {t['data_tarefa']}" if t["data_tarefa"] else ""
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
        obs = r["observacoes"] + [f"PENDENTE: {p}" for p in r["pendencias"]] + [f"⚠ {a}" for a in r["alertas"]]
        if obs:
            linhas += ["", "**Observação:**"] + [f"- {o}" for o in obs]
        if r["link_lancar"]:
            linhas += ["", f"[Lançar no VIOS]({r['link_lancar']})"]
    return "\n".join(linhas) + "\n"


def recalcular(arquivo_intimacoes, arquivo_analise, caminho_env=".env", hoje=None):
    """Refaz datas, conferências e relatório a partir das respostas da IA já salvas (sem custo de API)."""
    load_dotenv(caminho_env, override=True)
    itens = {i["ci"]: i for i in json.loads(Path(arquivo_intimacoes).read_text(encoding="utf-8"))}
    agente = Agente.__new__(Agente)
    agente.provedor, agente.modelo = "recalculado", os.getenv("LLM_MODELO", "")
    agente.tabela = _tabela_do_env()
    resultados = []
    for antigo in json.loads(Path(arquivo_analise).read_text(encoding="utf-8")):
        if "ia" not in antigo:
            resultados.append(antigo)
            continue
        novo = agente._completar(itens[antigo["ci"]], dict(antigo["ia"], _uso=antigo.get("uso", {})), hoje or date.today())
        resultados.append(novo)
    _duplicidades(resultados)
    return resultados, agente


def analisar_arquivo(arquivo, caminho_env=".env", pasta_saida=None):
    """Analisa um saida/intimacoes_*.json e grava analise_*.json e analise_*.md ao lado."""
    arquivo = Path(arquivo)
    itens = json.loads(arquivo.read_text(encoding="utf-8"))
    agente = Agente.do_env(caminho_env)
    log.info("Agente: %s / %s — %d intimações", agente.provedor, agente.modelo, len(itens))
    resultados = analisar_lista(agente, itens)

    pasta = Path(pasta_saida) if pasta_saida else arquivo.parent
    base = arquivo.stem.replace("intimacoes_", "analise_", 1)
    saida_json, saida_md = pasta / f"{base}.json", pasta / f"{base}.md"
    saida_json.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    saida_md.write_text(relatorio_md(resultados, agente, arquivo), encoding="utf-8")

    uso = [r.get("uso", {}) for r in resultados]
    log.info("Tokens: entrada %d (cache %d), saída %d",
             sum(u.get("entrada", 0) for u in uso), sum(u.get("entrada_cache", 0) for u in uso), sum(u.get("saida", 0) for u in uso))
    erros = sum(1 for r in resultados if r.get("erro"))
    return saida_md, len(resultados), erros
