"""Pesquisa de feriados e suspensões de prazo na internet (IA com web_search).

Antes da análise, junta os tribunais e cidades do lote, pergunta à IA (com
pesquisa na web) quais dias o expediente ou os prazos ficam suspensos no período
dos prazos e grava o resultado em doc/feriados.txt, com o link da fonte.

Regra combinada com a Controladoria (27/10/2026): contar o máximo de feriados
possível, mas sem confirmação a data fica adiantada para não perder prazo.
- fonte oficial (.jus.br; para feriado municipal também .gov.br/.leg.br) e
  suspensão confirmada -> conta no prazo;
- fonte não oficial ou suspensão incerta -> linha com AVISO (não estende o prazo);
- a IA diz que não suspende prazos -> não grava.

Cada (ramo, UF, cidade) pesquisado fica em saida/feriados_pesquisa.json e só é
pesquisado de novo depois de DIAS_VALIDADE (1 vez por mês) ou se o período pedido
for além do já pesquisado. Cada pesquisa cobre DIAS_PESQUISA dias, para o mês
inteiro de publicações caber nela com folga para os prazos.
"""
import json
import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from bot import custo, prazos

log = logging.getLogger(__name__)

DIAS_PERIODO = 60      # prazos de até ~30 dias úteis a partir da publicação
DIAS_PESQUISA = 95     # período pesquisado: 1 mês de publicações + DIAS_PERIODO
DIAS_VALIDADE = 30     # pesquisa refeita 1 vez por mês (custo: ~US$ 0,30 por tribunal)
CACHE = "feriados_pesquisa.json"

SISTEMA = """
Você pesquisa na internet feriados e suspensões de expediente/prazos processuais
para uma controladoria jurídica brasileira. Use a ferramenta de pesquisa.

Para o tribunal e o período informados, procure:
- feriados e pontos facultativos transferidos ou decretados pelo tribunal
  (portarias, resoluções, atos da presidência, calendário oficial do ano);
- suspensões de expediente ou de prazos (inclusive por problema no sistema,
  quando já publicadas);
- feriados municipais das cidades informadas, quando valem para o fórum/vara
  local (para Justiça Federal, só se a seção/subseção suspendeu o expediente).

Não liste feriados nacionais (01/01, Sexta-feira Santa, 21/04, 01/05, 07/09,
12/10, 02/11, 15/11, 20/11, 25/12), nem os da Lei 5.010/66 na Justiça Federal,
nem sábados e domingos: o programa já conhece.

Para cada data:
- `data`: DD/MM/AAAA, dentro do período;
- `descricao`: curta, com o ato (ex.: "Dia do Servidor transferido — Portaria 123/2026");
- `abrangencia`: "TRIBUNAL" se vale para o tribunal inteiro, ou o nome da cidade
  (exatamente como informado) se vale só ali;
- `suspende_prazos`: "SIM" só se o ato oficial do ano disser que não há
  expediente forense ou que os prazos ficam suspensos/prorrogados (prazo que
  vence no dia passa para o próximo dia útil); "NAO" se há expediente normal ou
  é ponto facultativo sem efeito nos prazos; "INCERTO" se não achou o ato
  oficial do ano ou ele não deixa claro o efeito nos prazos. Na dúvida,
  "INCERTO": contar um dia que não é feriado pode fazer perder prazo;
- `fonte_url`: o link da página onde confirmou (preferir site/diário oficial do
  tribunal ou da prefeitura). "" se não houver.

Não invente: sem fonte, use "INCERTO". Se não achar nada, devolva a lista vazia.
""".strip()


def _schema(cidades):
    texto = {"type": "string"}
    item = {
        "type": "object",
        "properties": {
            "data": texto,
            "descricao": texto,
            "abrangencia": {"type": "string", "enum": ["TRIBUNAL"] + cidades},
            "suspende_prazos": {"type": "string", "enum": ["SIM", "NAO", "INCERTO"]},
            "fonte_url": texto,
        },
        "required": ["data", "descricao", "abrangencia", "suspende_prazos", "fonte_url"],
        "additionalProperties": False,
    }
    return {"type": "object", "properties": {"datas": {"type": "array", "items": item}},
            "required": ["datas"], "additionalProperties": False}


def tribunal(item, cal):
    """Nome do tribunal pelo número CNJ (J.TR) e pela UF."""
    cnj = re.search(r"\d{7}-\d{2}\.\d{4}\.(\d)\.(\d{2})\.\d{4}", item.get("numeros", ""))
    tr = int(cnj.group(2)) if cnj else 0
    if cal.federal:
        return f"Justiça Federal — Seção Judiciária do {cal.uf}" + (f" (TRF da {tr}ª Região)" if tr else "")
    if cal.trabalho:
        return f"Tribunal Regional do Trabalho da {tr}ª Região" if tr else f"Justiça do Trabalho no {cal.uf}"
    return f"Tribunal de Justiça do Estado — {cal.uf} (TJ{cal.uf})"


def _oficial(url, municipal):
    host = urlsplit(url).hostname or ""
    if host.endswith(".jus.br"):
        return True
    return municipal and (host.endswith(".gov.br") or host.endswith(".leg.br"))


def _limpar(texto):
    # ";" separa colunas e "#" abre comentário em doc/feriados.txt
    return " ".join(texto.replace(";", ",").replace("#", "").split())


def _grupos(itens, tabela):
    """{(ramo, uf, tribunal): {"cidades": {nome exibido: cidade normalizada}, "inicio": data}}"""
    grupos = {}
    for item in itens:
        pub = _data(item.get("publicacao"))
        uf, cidade, federal, trabalho = prazos.contexto(item)
        if not uf or not pub:
            continue
        cal = prazos.Calendario(tabela, uf, cidade, federal, trabalho)
        g = grupos.setdefault((cal.ramo, cal.uf, tribunal(item, cal)), {"cidades": {}, "inicio": pub})
        g["inicio"] = min(g["inicio"], pub)
        if cidade:
            g["cidades"][cidade.strip().title()] = prazos.normalizar(cidade)
    return grupos


def _data(texto):
    try:
        return datetime.strptime((texto or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def pesquisar(ia, itens, tabela, arquivo_txt, pasta_saida, hoje=None, gasto=None, modelo=""):
    """Pesquisa os grupos do lote e acrescenta as datas novas em arquivo_txt.
    Devolve o número de linhas gravadas. Erro em um grupo não para os outros.
    gasto (custo.Gasto): sem espaço no teto, o grupo não é pesquisado (fica para a próxima)."""
    hoje = hoje or date.today()
    arquivo_cache = Path(pasta_saida) / CACHE
    cache = json.loads(arquivo_cache.read_text(encoding="utf-8")) if arquivo_cache.exists() else {}
    ja = {(d, e) for d, e, _, aviso in tabela.manuais}             # qualquer linha
    contadas = {(d, e) for d, e, _, aviso in tabela.manuais if not aviso}
    novas = []

    for (ramo, uf, nome_trib), g in sorted(_grupos(itens, tabela).items()):
        inicio, fim = g["inicio"], g["inicio"] + timedelta(days=DIAS_PERIODO)
        ate = inicio + timedelta(days=DIAS_PESQUISA)
        chaves = {c: f"{ramo}|{uf}|{n}" for c, n in g["cidades"].items()}
        chaves[""] = f"{ramo}|{uf}|"

        def em_dia(chave):
            c = cache.get(chave)
            return c and (hoje - _data(c["em"])).days < DIAS_VALIDADE and _data(c["ate"]) >= fim

        if all(em_dia(k) for k in chaves.values()):
            log.info("Feriados: %s (%s) já pesquisado", nome_trib, ", ".join(g["cidades"]) or uf)
            continue
        cidades = sorted(g["cidades"])
        pergunta = (f"Tribunal: {nome_trib}\nUF: {uf}\nCidades/comarcas: {', '.join(cidades) or 'não informadas'}\n"
                    f"Período: {inicio:%d/%m/%Y} a {ate:%d/%m/%Y}\nData de hoje: {hoje:%d/%m/%Y}")
        log.info("Feriados: pesquisando %s (%s), %s a %s", nome_trib, ", ".join(cidades) or uf,
                 f"{inicio:%d/%m}", f"{ate:%d/%m}")
        if gasto and not gasto.cabe(custo.PESQUISA_ESTIMADA_US):
            log.warning("Feriados: teto de gasto atingido, %s não pesquisado (usa os feriados já cadastrados)", nome_trib)
            continue
        try:
            resposta = ia.responder(SISTEMA, pergunta, _schema(cidades), pesquisar=True)
            if gasto:
                gasto.registrar(modelo, resposta.pop("_uso", {}))
        except Exception as e:
            log.warning("Feriados: falha na pesquisa de %s: %s", nome_trib, e)
            continue

        cal = prazos.Calendario(prazos.Tabela(), uf, "", ramo == "JUSTIÇA FEDERAL", ramo == "JUSTIÇA DO TRABALHO")
        for d in resposta.get("datas", []):
            dia = _data(d["data"])
            # nacionais, Lei 5.010/66 e recesso (20/12–20/01) o calendário já conta
            if not dia or not (inicio <= dia <= ate) or dia.weekday() >= 5 or cal.feriado(dia) or cal.suspenso(dia):
                continue
            if d["suspende_prazos"] == "NAO":
                continue
            municipal = d["abrangencia"] != "TRIBUNAL"
            escopo = f"{ramo}/{d['abrangencia'].upper()}/{uf}" if municipal else f"{ramo}/{uf}"
            chave = (dia, prazos.normalizar(escopo))
            url = (d["fonte_url"] or "").split("#")[0].strip()
            confirmado = d["suspende_prazos"] == "SIM" and _oficial(url, municipal)
            if chave in contadas or (chave in ja and not confirmado):
                continue
            descricao = _limpar(d["descricao"]) + (f" (fonte: {_limpar(url)})" if url else " (sem fonte)")
            novas.append(f"{dia:%d/%m/%Y} ; {escopo} ; {descricao}" + ("" if confirmado else " ; AVISO"))
            ja.add(chave)
            if confirmado:
                contadas.add(chave)
            log.info("Feriados: %s %s — %s%s", f"{dia:%d/%m/%Y}", escopo, d["descricao"],
                     "" if confirmado else " (AVISO: não confirmado, prazo não estendido)")

        for chave in chaves.values():
            cache[chave] = {"em": f"{hoje:%d/%m/%Y}", "ate": f"{ate:%d/%m/%Y}"}

    if novas:
        texto = Path(arquivo_txt).read_text(encoding="utf-8") if Path(arquivo_txt).exists() else ""
        bloco = [f"", f"# Pesquisa automática na internet em {hoje:%d/%m/%Y} (bot/feriados_web.py) — pode editar ou apagar"]
        Path(arquivo_txt).write_text(texto.rstrip("\n") + "\n" + "\n".join(bloco + novas) + "\n", encoding="utf-8")
    arquivo_cache.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Feriados: %d data(s) nova(s) em %s", len(novas), arquivo_txt)
    return len(novas)
