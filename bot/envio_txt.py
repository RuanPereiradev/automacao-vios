"""Lê o arquivo .txt com as tarefas já ajustadas (análise feita no chat) e monta o que o
lançamento precisa, sem chamar a IA.

Formato (um bloco por tarefa, separados por uma linha só com ---; tarefas da mesma CI
seguidas viram uma CI com várias tarefas):

    CI: 42484
    PROCESSO: 0000123-45.2026.8.06.0001
    TAREFA: MINUTAR PETIÇÃO (EXECUÇÃO) 2026
    DATA: 29/10/2026
    HORA:
    RESPONSÁVEIS: automático
    DESCRIÇÃO:
    PRAZO FATAL: 29/10/2026
    MINUTAR PETIÇÃO ...
    ---
"""
import re
from datetime import date, datetime

from bot.analise import COM_HORARIO, FORA_DA_DESCRICAO, numero_processo
from bot.lancamento import APELIDOS, _normalizar

SEPARADOR = re.compile(r"^\s*-{3,}\s*$")
CAMPO = re.compile(r"^\s*([A-Za-zÀ-ú ]+?)\s*:\s?(.*)$")
CAMPOS = {"CI": "ci", "PROCESSO": "processo", "NUMERO DO PROCESSO": "processo", "N DO PROCESSO": "processo",
          "TAREFA": "nome", "DATA": "data", "HORA": "hora", "HORARIO": "hora",
          "RESPONSAVEIS": "responsaveis", "DESCRICAO": "descricao"}
AUTOMATICO = {"", "AUTOMATICO", "AUTOMATICO PELO VIOS"}
LINK_LANCAR = "index.php?pag=sys/publicacoes/int-lanca.php&imp_pub_id={ci}"


def _blocos(texto):
    """Linhas de cada bloco (ignora blocos vazios), com o número da 1ª linha."""
    atual, inicio = [], 1
    for n, linha in enumerate(texto.replace("\r\n", "\n").split("\n"), 1):
        if SEPARADOR.match(linha):
            if any(l.strip() for l in atual):
                yield inicio, atual
            atual, inicio = [], n + 1
        else:
            atual.append(linha)
    if any(l.strip() for l in atual):
        yield inicio, atual


def _ler_bloco(linhas):
    """Campos do bloco. Tudo depois de DESCRIÇÃO: é a descrição (inclusive "PRAZO FATAL: ...")."""
    campos, desconhecidos = {}, []
    for i, linha in enumerate(linhas):
        m = CAMPO.match(linha)
        chave = CAMPOS.get(_normalizar(m.group(1))) if m else None
        if chave == "descricao":
            primeira = m.group(2).strip()
            campos["descricao"] = "\n".join(([primeira] if primeira else []) + linhas[i + 1:]).strip()
            break
        if chave:
            campos[chave] = m.group(2).strip()
        elif linha.strip():
            desconhecidos.append(linha.strip())
    return campos, desconhecidos


def _data(texto):
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def ler(texto, oficiais, pessoas=(), lancadas=(), links=None, base_url="", hoje=None, duplicadas=None, processos=None):
    """Devolve a lista de CIs: {ci, processo, link_lancar, tarefas, problemas, avisos, ja_lancada}.
    processos = {ci: número do processo capturado do VIOS}, usado quando o arquivo não traz PROCESSO.
    CI com problema não é lançada. oficiais = nomes da lista oficial; pessoas = responsáveis
    do VIOS; lancadas = CIs já gravadas (lancamentos.json); links = {ci: link capturado};
    duplicadas = {ci: CI original} das análises do bot (cópia da mesma publicação)."""
    hoje = hoje or date.today()
    por_nome = {_normalizar(n): n for n in oficiais}
    por_nome.update({_normalizar(apelido): apelido for apelido in APELIDOS})
    # o nome certo do VIOS também vale (a lista da skill tem nomes com erro de digitação)
    por_nome.update({_normalizar(certo): certo for certo in APELIDOS.values()})
    por_pessoa = {_normalizar(p): p for p in pessoas}
    links = links or {}
    duplicadas = duplicadas or {}
    processos = processos or {}
    cis = []
    for _, linhas in _blocos(texto):
        campos, desconhecidos = _ler_bloco(linhas)
        problemas, avisos = [], []
        ci = campos.get("ci", "")
        if not re.fullmatch(r"\d+", ci):
            problemas.append(f"CI ausente ou inválida ('{ci}').")
        if desconhecidos:
            problemas.append(f"Linha fora do formato antes de DESCRIÇÃO: '{desconhecidos[0][:80]}' (apague ou passe para a descrição).")

        nome = por_nome.get(_normalizar(campos.get("nome", "")))
        if not nome:
            problemas.append(f"Tarefa fora da lista oficial do VIOS: '{campos.get('nome', '')}'.")
            nome = campos.get("nome", "")

        data_txt, tipo = campos.get("data", ""), "DATA_INFORMADA"
        if not data_txt and nome.startswith("CIÊNCIA"):
            tipo = "SEM_DATA"  # ciência sem data: vai para o dia do envio
        elif not _data(data_txt):
            problemas.append(f"{nome or 'Tarefa'}: data inválida ou vazia ('{data_txt}'). Use DD/MM/AAAA.")
        else:
            dia = _data(data_txt)
            if dia < hoje:
                avisos.append(f"{nome}: data {data_txt} já passou.")
            elif dia.weekday() >= 5:
                avisos.append(f"{nome}: data {data_txt} cai no fim de semana.")

        hora = campos.get("hora", "")
        if hora and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
            problemas.append(f"{nome}: horário inválido ('{hora}'). Use HH:MM.")
        if nome.startswith(COM_HORARIO) and not hora:
            problemas.append(f"{nome}: falta o horário (vai no campo Horário do VIOS).")

        responsaveis = []
        if _normalizar(campos.get("responsaveis", "")) not in AUTOMATICO:
            for p in re.split(r"[,;]", campos["responsaveis"]):
                if not p.strip():
                    continue
                achado = por_pessoa.get(_normalizar(p))
                if pessoas and not achado:
                    problemas.append(f"{nome}: responsável fora da lista do VIOS: '{p.strip()}'.")
                responsaveis.append(achado or p.strip())

        descricao = campos.get("descricao", "")
        if not descricao:
            problemas.append(f"{nome}: descrição vazia (ou falta a linha DESCRIÇÃO:).")
        fora = [l.strip() for l in descricao.splitlines() if FORA_DA_DESCRICAO.match(l)]
        if fora:
            avisos.append(f"{nome}: a descrição tem linha que a Controladoria pediu para não usar: '{fora[0]}'.")

        tarefa = {
            "nome": nome, "data_tarefa": data_txt, "tipo_data": tipo, "data_editada": True,
            "hora": hora, "descricao": descricao, "responsaveis": responsaveis,
            "marcar_breno": not responsaveis and "MINUTAR PETIÇÃO EXECUÇÃO" in nome,
            "soltas": desconhecidos,  # linhas fora do formato: ficam visíveis até a pessoa tirar
        }
        processo_txt = campos.get("processo", "")
        processo = numero_processo(processo_txt)
        if processo_txt and not processo:
            avisos.append(f"Número do processo fora do formato ('{processo_txt}'): use 0000000-00.0000.0.00.0000.")
        if cis and cis[-1]["ci"] == ci:
            if processo and not cis[-1]["processo"]:
                cis[-1]["processo"] = processo
            cis[-1]["tarefas"].append(tarefa)
            cis[-1]["problemas"] += problemas
            cis[-1]["avisos"] += avisos
            continue
        if ci in duplicadas:
            original = duplicadas[ci]
            problemas.append(f"CI {ci} é cópia da CI {original} (mesma publicação)"
                             + (", que já foi lançada" if original in lancadas else "")
                             + ": não lançar, vale a tarefa da original. Remova esta CI.")
        if any(c["ci"] == ci for c in cis):
            problemas.append(f"CI {ci} aparece separada em mais de um lugar do arquivo: junte as tarefas.")
        cis.append({
            "ci": ci, "processo": processo, "tarefas": [tarefa], "problemas": problemas, "avisos": avisos,
            "ja_lancada": ci in lancadas,
            "link_lancar": links.get(ci) or (base_url + LINK_LANCAR.format(ci=ci) if ci else ""),
        })
    # número do processo: o do arquivo; sem ele, o da captura do VIOS; sem nenhum, aviso
    for c in cis:
        capturado = numero_processo(processos.get(c["ci"], ""))
        if not c["processo"]:
            c["processo"] = capturado
        elif capturado and capturado != c["processo"]:
            c["avisos"].append(f"Número do processo do arquivo ({c['processo']}) diferente do capturado no VIOS "
                               f"para a CI {c['ci']} ({capturado}): confira.")
        if not c["processo"] and c["ci"]:
            c["avisos"].append("Sem número do processo: não veio no arquivo (PROCESSO:) nem na captura do VIOS.")
    return cis


def gerar(cis):
    """Volta para o formato .txt (usado depois de editar na página)."""
    blocos = []
    for c in cis:
        for t in c["tarefas"]:
            linhas = [f"CI: {c['ci']}"] + ([f"PROCESSO: {c['processo']}"] if c.get("processo") else []) + [
                      f"TAREFA: {t['nome']}", f"DATA: {t['data_tarefa']}", f"HORA: {t['hora']}",
                      f"RESPONSÁVEIS: {', '.join(t['responsaveis']) or 'automático'}"]
            linhas += t.get("soltas") or []
            linhas += ["DESCRIÇÃO:", t["descricao"]]
            blocos.append("\n".join(linhas))
    return "\n---\n".join(blocos) + "\n"
