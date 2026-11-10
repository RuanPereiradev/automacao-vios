"""Lança no VIOS as tarefas sugeridas pela análise (tela "Lançar Intimação", int-lanca.php).

Para cada tarefa da análise o bot abre o link "Lançar Intimação" da CI, escolhe a
tarefa, define a data para conclusão (e o horário, em audiência/perícia/sustentação), escreve a descrição em Observação e clica
em Adicionar. Sem confirmar=True ele só preenche e tira um print (modo teste).
"""
import html
import json
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from bot.navegador import POLL

from bot import duplicidade, skill

log = logging.getLogger(__name__)

SELECT_TAREFA = (By.ID, "processos_etapas_id")
REGISTRO = "lancamentos.json"  # CIs já lançadas (evita lançar duas vezes)

# nomes da skill com erro de digitação -> nome da tarefa no VIOS (conforme a própria skill)
APELIDOS = {
    "MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)": "MINUTAR PETIÇÃO (EXECUÇÃO) 2026",
    "SUSTENTAÇÃO ORAL PPREVIDENCIÁRIO) 2026": "SUSTENTAÇÃO ORAL (PREVIDENCIÁRIO) 2026",
}


class LancamentoErro(Exception):
    pass


def _normalizar(texto):
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", " ", sem_acento.upper()).strip()


def achar_opcao(nome, opcoes):
    """Acha o value da tarefa no <select> do VIOS. opcoes = {texto: value}.
    Aceita o nome da skill igual ao do VIOS (sem diferença de acento/espaço) ou o
    nome do VIOS entre parênteses, ex.: 'MINUTAR PETIÇÃO EXECUÇÃO 2026 (MINUTAR PETIÇÃO (EXECUÇÃO) 2026)'."""
    por_nome = {_normalizar(t): v for t, v in opcoes.items()}
    candidatos = [nome] + ([APELIDOS[nome]] if nome in APELIDOS else [])
    m = re.search(r"\((.+\d{4})\)\s*$", nome)
    if m:
        candidatos.append(m.group(1))
    for c in candidatos:
        valor = por_nome.get(_normalizar(c))
        if valor:
            return valor
    return None


def _data_valida(texto):
    try:
        datetime.strptime(texto or "", "%d/%m/%Y")
        return True
    except ValueError:
        return False


def _data_conclusao(tarefa, hoje):
    """Data da tarefa calculada na análise; sem data (ex.: ciência), hoje.
    Tarefa do mesmo dia (análise, verificar viabilidade) é sempre para o dia do lançamento."""
    if tarefa.get("tipo_data") == "MESMO_DIA" and not tarefa.get("data_editada"):
        return hoje
    try:
        return datetime.strptime(tarefa["data_tarefa"], "%d/%m/%Y").date()
    except (KeyError, ValueError):
        return hoje


# linhas de prazo que vão em vermelho (com a data): "PRAZO FATAL...", "PRAZO PARA/DE EMBARGOS:" e "PRAZO PARA/DE RECURSO:"
PRAZO_VERMELHO = re.compile(r"\s*PRAZO\s+(FATAL|(PARA|DE)\s+(EMBARGOS|RECURSO))\b", re.I)


# Corte das 12h (skill da Controladoria): CIÊNCIA e ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO lançadas depois das
# 12:00 (ou no fim de semana) com data de hoje vão para o próximo dia de segunda a sexta (contagem simplificada:
# feriado não pula). Só a data da tarefa muda: PRAZO PARA EMBARGOS/RECURSO e PRAZO FATAL da descrição ficam.
CORTE_HORA = (12, 0)
CORTE_TAREFAS = ("CIÊNCIA", "ANALISAR SENTENÇA")
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")


def _proximo_dia_semana(dia):
    dia += timedelta(days=1)
    while dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia


def _prazos_da_descricao(descricao):
    """Datas das linhas de prazo (PRAZO FATAL..., PRAZO PARA EMBARGOS/RECURSO) da descrição."""
    datas = []
    for linha in (descricao or "").splitlines():
        if PRAZO_VERMELHO.match(linha):
            for d in re.findall(r"\d{2}/\d{2}/\d{4}", linha):
                try:
                    datas.append(datetime.strptime(d, "%d/%m/%Y").date())
                except ValueError:
                    pass
    return datas


def corte_meio_dia(tarefa, data, agora):
    """Aplica o corte das 12h. Devolve (data, motivo); motivo vazio = nada mudou.
    Nunca passa a tarefa para depois de um prazo da descrição: aí ela fica hoje (urgente)."""
    if not tarefa["nome"].startswith(CORTE_TAREFAS):
        return data, ""
    hoje = agora.date()
    fim_de_semana = hoje.weekday() >= 5
    if data != hoje or not (fim_de_semana or (agora.hour, agora.minute) > CORTE_HORA):
        return data, ""
    nova = _proximo_dia_semana(hoje)
    antes = [p for p in _prazos_da_descricao(tarefa.get("descricao")) if p < nova]
    if antes:
        return data, (f"lançada após as 12h, mas MANTIDA em {hoje:%d/%m/%Y}: o prazo {min(antes):%d/%m/%Y} da "
                      f"descrição vem antes de {nova:%d/%m/%Y} (URGENTE)")
    quando = "no fim de semana" if fim_de_semana else f"às {agora:%H:%M}"
    return nova, f"lançada {quando}: data passou de {hoje:%d/%m/%Y} para {nova:%d/%m/%Y} ({DIAS[nova.weekday()]})"


def _linha_html(linha):
    """Texto do robô em negrito; linhas de prazo ("PRAZO FATAL...", "PRAZO PARA EMBARGOS: 06/11/2026",
    "PRAZO PARA RECURSO: 20/11/2026", também com "DE") em negrito e vermelho, junto com a data.
    O teor que o VIOS acrescenta depois ("---------- Intimação: ...") não passa por aqui e fica normal."""
    if not linha.strip():
        return "<p>&nbsp;</p>"
    texto = html.escape(linha)
    if PRAZO_VERMELHO.match(linha):
        texto = f'<span style="color: #ff0000;">{texto}</span>'
    return f"<p><strong>{texto}</strong></p>"


def _html(descricao):
    return "".join(_linha_html(l) for l in descricao.splitlines())


def _esperar_ajax(driver, timeout):
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(
        lambda d: d.execute_script("return document.readyState === 'complete' && (!window.jQuery || jQuery.active === 0)")
    )


def _abrir(driver, link, timeout):
    driver.get(link)
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.presence_of_element_located(SELECT_TAREFA))
    # o editor da Observação (TinyMCE) é criado depois que a página carrega
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(
        lambda d: d.execute_script("return !!(window.tinymce && tinymce.get('fo[obs]') && tinymce.get('fo[obs]').initialized)")
    )
    _esperar_ajax(driver, timeout)


def preencher(driver, tarefa, data_conclusao, timeout):
    """Preenche o formulário já aberto. Devolve o que ficou na tela, para conferir."""
    opcoes = driver.execute_script(
        "return Object.fromEntries([...arguments[0].options].map(o => [o.text.trim(), o.value]));",
        driver.find_element(*SELECT_TAREFA),
    )
    valor = achar_opcao(tarefa["nome"], opcoes)
    if not valor:
        raise LancamentoErro(f"Tarefa '{tarefa['nome']}' não existe no VIOS")

    # tudo por JavaScript: os selects são bootstrap-select e a tela pode ter o popup de recado.
    # A tarefa vai primeiro, porque a troca pode disparar carregamentos da tela.
    driver.execute_script(
        "const $s = jQuery('#processos_etapas_id'); $s.val(arguments[0]).trigger('change');"
        "if ($s.selectpicker) $s.selectpicker('refresh');",
        valor,
    )
    _esperar_ajax(driver, timeout)

    driver.execute_script(
        """
        const [data, obs, breno, nomes, hora] = arguments;
        const $p = jQuery('#tp_prazo');
        $p.val('data').trigger('change');
        if ($p.selectpicker) $p.selectpicker('refresh');
        const campo = document.querySelector("input[name='fo[data_prevista]']");
        campo.value = data;
        jQuery(campo).trigger('change');
        // audiência, perícia, sustentação: horário do ato
        const h = document.getElementById('fo[hora_prevista]');
        if (h) { h.value = hora; jQuery(h).trigger('input').trigger('change'); }
        if (nomes.length) {
            // responsáveis escolhidos na revisão: marca exatamente essas pessoas
            const $r = jQuery('#responsaveis');
            [...$r[0].options].forEach(o => { o.selected = nomes.includes(o.text.trim().toUpperCase()); });
            $r.trigger('change'); if ($r.selectpicker) $r.selectpicker('refresh');
        } else if (breno) {
            const $r = jQuery('#responsaveis');
            const op = [...$r[0].options].find(o => o.text.trim().toUpperCase().startsWith('BRENO'));
            if (op) { op.selected = true; $r.trigger('change'); if ($r.selectpicker) $r.selectpicker('refresh'); }
        }
        const ed = tinymce.get('fo[obs]');
        ed.setContent(obs);
        ed.save();
        """,
        data_conclusao.strftime("%d/%m/%Y"),
        _html(tarefa["descricao"]),
        bool(tarefa.get("marcar_breno")),
        [n.strip().upper() for n in tarefa.get("responsaveis") or []],
        tarefa.get("hora") or "",
    )
    tela = driver.execute_script(
        """
        const sel = id => [...document.getElementById(id).selectedOptions].map(o => o.text.trim());
        return {
            tarefa: sel('processos_etapas_id')[0],
            tipo_prazo: document.getElementById('tp_prazo').value,
            data_prevista: document.querySelector("input[name='fo[data_prevista]']").value,
            hora: (document.getElementById('fo[hora_prevista]') || {value: ''}).value,
            responsaveis: sel('responsaveis'),
            texto_intimacao: document.getElementById('fo[texto_int]').checked,
            obs: tinymce.get('fo[obs]').getContent({format: 'text'}),
        };
        """
    )
    if (tarefa.get("hora") or "") != tela["hora"]:
        raise LancamentoErro(f"Horário não confere: pedido '{tarefa.get('hora') or ''}', na tela '{tela['hora']}'")
    pedidos = {_normalizar(n) for n in tarefa.get("responsaveis") or []}
    if pedidos and pedidos != {_normalizar(n) for n in tela["responsaveis"]}:
        raise LancamentoErro(f"Responsáveis não conferem: pedido {sorted(tarefa['responsaveis'])}, "
                             f"na tela {tela['responsaveis']}")
    return tela


def ler_responsaveis(driver, link_lancar, timeout):
    """Pessoas do campo Responsáveis do formulário de lançamento (só lê, não preenche)."""
    _abrir(driver, link_lancar, timeout)
    return driver.execute_script(
        "return [...document.getElementById('responsaveis').options].map(o => o.text.trim()).filter(t => t);"
    )


def ler_intimacao(driver, link_lancar, timeout):
    """Teor, processo e cliente da intimação, lidos na tela de lançamento (só lê, não preenche).
    Mesmos campos da captura, para a conferência de duplicatas (bot/duplicidade.py)."""
    _abrir(driver, link_lancar, timeout)
    return driver.execute_script(
        """
        const linha = rotulo => [...document.querySelectorAll('tr')].find(tr =>
            ((tr.querySelector('td b') || {}).innerText || '').trim() === rotulo);
        const valor = rotulo => { const tr = linha(rotulo); return tr ? tr.cells[1].innerText.trim() : ''; };
        const painel = document.getElementById('vj-copy-intimacao');
        return {numeros: valor('Nro CNJ'), cliente: valor('Cliente'), texto: painel ? painel.innerText.trim() : ''};
        """
    )


def tarefas_lancadas(driver, link_lancar, timeout):
    """Tarefas já lançadas para a intimação, lidas da tela de Conferência
    (confere-intimacao-lancada.php). Cada uma: {tarefa, data, responsaveis, apagada}."""
    driver.get(link_lancar.replace("int-lanca.php", "confere-intimacao-lancada.php"))
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table")))
    _esperar_ajax(driver, timeout)
    return driver.execute_script(
        """
        // data-id = "<tabela>_linha_<n>_<coluna>"; tarefa excluída tem o ícone "Apagada"
        return [...document.querySelectorAll("tr[id*='_linha_']")].map(tr => {
            const cel = col => (tr.querySelector(`td[data-id$='_${col}']`) || {innerText: ''}).innerText.trim();
            return {tarefa: cel('processos_etapas_nome'), data: cel('data_prevista'),
                    responsaveis: cel('responsaveis'), apagada: !!tr.querySelector("[title='Apagada']")};
        }).filter(t => t.tarefa);
        """
    )


def _enviar(driver, nome_botao, timeout):
    """Clica no botão do formulário (Adicionar ou Gravar) e espera a página recarregar."""
    botao = driver.find_element(By.CSS_SELECTOR, f"button[name='{nome_botao}']")
    driver.execute_script("arguments[0].click();", botao)
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.staleness_of(botao))
    WebDriverWait(driver, timeout, poll_frequency=POLL).until(EC.presence_of_element_located(SELECT_TAREFA))
    _esperar_ajax(driver, timeout)


def _tarefas_adicionadas(driver):
    """Quadro "Tarefas" da tela de lançamento: as tarefas adicionadas e ainda não gravadas."""
    return driver.execute_script(
        """
        const bloco = [...document.querySelectorAll('.ibox')]
            .find(b => ((b.querySelector('.ibox-title') || {}).innerText || '').trim() === 'Tarefas');
        if (!bloco) return [];
        return [...bloco.querySelectorAll("tr[id*='_linha_']")].map(tr => tr.id + ' | ' + tr.innerText.replace(/\\s+/g, ' ').trim());
        """
    )


def _print_formulario(driver, arquivo):
    """Print só do formulário. O popup de recado é escondido apenas na tela (não é marcado como lido)."""
    driver.execute_script(
        "document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.style.visibility = 'hidden');"
        "document.getElementById('vj-bloco-form').scrollIntoView();"
    )
    driver.find_element(By.ID, "vj-bloco-form").screenshot(str(arquivo))


def _registro(pasta):
    arquivo = Path(pasta) / REGISTRO
    dados = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    return arquivo, dados


RESULTADOS = "automatico_resultados.json"  # resultado de cada CI no lançamento (tela /automatico)


def anotar_resultado(pasta_saida, ci, estado, mensagem=""):
    """Guarda o que aconteceu com a CI no lançamento: gravada, bloqueada, duplicada, ja_no_vios,
    conferencia (pede humano), erro ou retirada (tirada da lista antes de lançar)."""
    arquivo = Path(pasta_saida) / RESULTADOS
    dados = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {}
    dados[ci] = {"estado": estado, "mensagem": mensagem, "quando": f"{datetime.now():%d/%m/%Y %H:%M}"}
    arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def lancar(driver, resultados, cis, pasta_saida, pasta_logs, timeout, confirmar=False, hoje=None):
    """Lança as tarefas das CIs pedidas. Devolve (lancadas, erros).
    Gravando (confirmar=True), anota o resultado de cada CI em saida/automatico_resultados.json."""
    hoje = hoje or date.today()
    arquivo_reg, registro = _registro(pasta_saida)

    def anotar(ci, estado, mensagem=""):
        if confirmar:
            anotar_resultado(pasta_saida, ci, estado, mensagem)
    if cis == ["todas"]:
        cis = [r["ci"] for r in resultados if r.get("ci")]
    escolhidos = [r for r in resultados if r.get("ci") in cis]
    faltando = set(cis) - {r["ci"] for r in escolhidos}
    if faltando:
        raise LancamentoErro(f"CI(s) sem análise: {', '.join(sorted(faltando))}")

    lancadas, erros = 0, 0
    for r in escolhidos:
        ci = r["ci"]
        if r.get("erro"):
            log.error("CI %s: análise com erro, nada lançado", ci)
            anotar(ci, "erro", "A análise da IA deu erro: nada lançado.")
            erros += 1
            continue
        if r.get("duplicada_de") and duplicidade.ligado():
            log.info("CI %s: duplicada da CI %s, ignorada (vale a tarefa da original)", ci, r["duplicada_de"])
            anotar(ci, "duplicada", f"Cópia da CI {r['duplicada_de']}: vale a tarefa da original.")
            continue
        if confirmar and ci in registro:
            log.warning("CI %s já foi lançada em %s: pulando", ci, registro[ci]["quando"])
            continue
        if not r.get("link_lancar"):
            log.error("CI %s: sem link 'Lançar Intimação'", ci)
            anotar(ci, "erro", "Sem o link 'Lançar Intimação' do VIOS.")
            erros += 1
            continue
        if r.get("bloqueios"):
            log.warning("CI %s: falta informação, nada lançado (conferir no PJe e lançar manualmente): %s",
                        ci, "; ".join(r["bloqueios"]))
            anotar(ci, "bloqueada", "; ".join(r["bloqueios"]))
            erros += 1
            continue
        especiais = [t["nome"] for t in r["tarefas"] if t["nome"] in skill.ESPECIAIS]
        if especiais or not r["tarefas"]:
            log.warning("CI %s: análise pede conferência humana (%s): nada lançado", ci, "; ".join(especiais) or "sem tarefa")
            anotar(ci, "conferencia", "A análise pede conferência humana: " + ("; ".join(especiais) or "sem tarefa"))
            erros += 1
            continue
        # só tarefa sem prazo (ciência) pode ficar sem data; prazo "PENDENTE" não vira a data de hoje
        sem_data = [t["nome"] for t in r["tarefas"] if not _data_valida(t["data_tarefa"]) and t["tipo_data"] != "SEM_DATA"]
        if sem_data:
            log.warning("CI %s: data não calculada para %s: nada lançado (conferir manualmente)", ci, "; ".join(sem_data))
            anotar(ci, "bloqueada", "Data não calculada para " + "; ".join(sem_data))
            erros += 1
            continue

        ja = [t for t in tarefas_lancadas(driver, r["link_lancar"], timeout) if not t["apagada"]]
        if ja:
            log.warning("CI %s já tem tarefa no VIOS (%s): nada lançado",
                        ci, "; ".join(f"{t['tarefa']} {t['data']}" for t in ja))
            anotar(ci, "ja_no_vios", "Já tinha tarefa no VIOS: " + "; ".join(f"{t['tarefa']} {t['data']}" for t in ja))
            continue

        # 1) Adicionar cada tarefa: vai para o quadro "Tarefas" (provisório, só nesta sessão)
        # 2) Gravar: efetiva o lançamento de todas
        adicionadas = []
        try:
            _abrir(driver, r["link_lancar"], timeout)
            sobra = _tarefas_adicionadas(driver)
            if sobra:
                raise LancamentoErro(f"quadro Tarefas já tem {len(sobra)} linha(s) antes de adicionar: {sobra}")
            for n, t in enumerate(r["tarefas"], 1):
                data, motivo = corte_meio_dia(t, _data_conclusao(t, hoje), datetime.now())
                if motivo:
                    log.info("CI %s tarefa %d (%s): corte das 12h: %s", ci, n, t["nome"], motivo)
                tela = preencher(driver, t, data, timeout)
                log.info("CI %s tarefa %d: %s | prazo %s %s %s | responsáveis %s | texto da intimação: %s",
                         ci, n, tela["tarefa"], tela["tipo_prazo"], tela["data_prevista"], tela["hora"],
                         ", ".join(tela["responsaveis"]), "sim" if tela["texto_intimacao"] else "não")
                log.info("Observação:\n%s", tela["obs"])
                _print_formulario(driver, Path(pasta_logs) / f"lancamento_ci{ci}_{n}_{datetime.now():%H%M%S}.png")
                _enviar(driver, "Adicionar", timeout)
                adicionadas.append(tela)

            quadro = _tarefas_adicionadas(driver)
            if len(quadro) != len(adicionadas):
                raise LancamentoErro(f"quadro Tarefas tem {len(quadro)} linha(s), esperado {len(adicionadas)}: {quadro}")
            log.info("Quadro Tarefas (antes de gravar):\n%s", "\n".join(q[:200] for q in quadro))
            print_ = Path(pasta_logs) / f"lancamento_ci{ci}_quadro_{datetime.now():%H%M%S}.png"
            driver.execute_script("document.querySelectorAll('.modal, .modal-backdrop').forEach(e => e.style.visibility = 'hidden');")
            driver.save_screenshot(str(print_))
            if not confirmar:
                log.info("MODO TESTE: tarefas adicionadas ao quadro e NÃO gravadas (print em %s)", print_)
                continue

            _enviar(driver, "Gravar", timeout)
            # confirma pela tela de Conferência: cada tarefa tem que aparecer lá, não apagada
            gravadas = [t for t in tarefas_lancadas(driver, r["link_lancar"], timeout) if not t["apagada"]]
            for tela in adicionadas:
                if not any(g["tarefa"] == tela["tarefa"] and g["data"] == tela["data_prevista"] for g in gravadas):
                    raise LancamentoErro(f"{tela['tarefa']} não apareceu na Conferência do VIOS (lá: {gravadas})")
            log.info("CI %s: %d tarefa(s) gravada(s) e conferida(s) no VIOS", ci, len(adicionadas))
            lancadas += len(adicionadas)
            registro[ci] = {
                "quando": f"{datetime.now():%d/%m/%Y %H:%M}",
                "tarefas": [{"tarefa": t["tarefa"], "data": t["data_prevista"], "responsaveis": t["responsaveis"]}
                            for t in adicionadas],
            }
            arquivo_reg.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
            anotar(ci, "gravada")
        except Exception as e:
            erros += 1
            log.exception("CI %s: falha ao lançar", ci)
            anotar(ci, "erro", str(e))
            driver.save_screenshot(str(Path(pasta_logs) / f"erro_lancamento_ci{ci}_{datetime.now():%H%M%S}.png"))
    return lancadas, erros
