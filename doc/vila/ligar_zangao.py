"""Liga a Vila 02 (Zangão) ao servidor do Ultron (só no modo servidor, em /vila):
- etapa 1: anima os eventos reais do Zangão (bot: "zangao");
- etapa 2: botões para rodar o Zangão pela Vila 02: "Testar sem gravar", "Rodar e gravar no VIOS"
  (só nos 3 últimos dias, com confirmação) e "Painel", que chamam /zangao/status e
  /zangao/rodar do Ultron; o rodapé diz o que ele está fazendo;
- etapa 3 (Ultron e Zangão): aba escondida ou fila grande de eventos não fazem o robô reprisar
  tudo devagar; a vila pula direto para o estado atual;
- etapa 4: abrir direto numa vila pelo endereço (/vila?vila=2 = Vila 02 · Zangão), para embutir
  a vila nas páginas do Ultron; e, ao abrir, animar os eventos dos últimos 30 s (a página do
  Ultron recarrega logo depois de subir o .txt, e o robô tem que aparecer recebendo o arquivo).
uso: python3 doc/vila/ligar_zangao.py bot/vila/vila.html  (edita no lugar; o modo simulado continua igual;
     pode rodar de novo: aplica só a etapa que falta)"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
ETAPA1 = "zhandle(ev)" not in t  # eventos do Zangão na Vila 02
ETAPA2 = "zrodar(modo)" not in t  # botões para rodar o Zangão pela vila
ETAPA3 = "alcancar()" not in t  # pular para o estado atual (aba escondida / fila grande)
ETAPA4 = "get('vila')" not in t  # /vila?vila=N abre na vila N
if not (ETAPA1 or ETAPA2 or ETAPA3 or ETAPA4):
    sys.exit("a vila já está com tudo do Zangão")


def troca(velho, novo, etapa=1):
    global t
    if not {1: ETAPA1, 2: ETAPA2, 3: ETAPA3, 4: ETAPA4}[etapa]:
        return
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:80])
    t = t.replace(velho, novo)


# 1) estado: dados da execução real do Zangão
troca("ztasks: [], zpanelOpen: false };",
      "ztasks: [], zpanelOpen: false, zmodo: null, zfase: null, zcal: null, zresult: null };")

# 2) fala de espera do Zangão real
troca("  static ZSAMPLE = [",
      "  static ZIDLE_REAL = 'Sou o Zangão. Nos 3 últimos dias do mês entro no VIOS, leio o comprovante de protocolo das "
      "tarefas previdenciárias e preencho N.º CNJ, órgão julgador e valor da ação.';\n"
      "  static ZSAMPLE = [")

# 3) fila de eventos do Zangão e fala inicial certa para cada modo
troca("this.zseq = []; this.zcur = null;", "this.zseq = []; this.zcur = null; this.zevq = [];")
troca("    this.zsay(Component.ZIDLE);\n",
      "    this.zsay(this.fonte() === 'servidor' ? Component.ZIDLE_REAL : Component.ZIDLE);\n")

# 4) botão da Vila 02: no servidor só abre/fecha o painel (quem dispara o Zangão é o agendador)
troca("      if (zp === 'idle' || zp === 'done') this.zstart();",
      "      if (this.fonte() === 'servidor') { if (this.state.ztasks.length) this.setState(st => ({ zpanelOpen: !st.zpanelOpen })); }\n"
      "      else if (zp === 'idle' || zp === 'done') this.zstart();")

# 5) polling: separa os eventos do Zangão
troca("        if (first) { this.loadHistory(ul); first = false; } else this.evq.push.apply(this.evq, ul);",
      "        const zg = evs.filter(e => e.bot === 'zangao');\n"
      "        if (first) { this.loadHistory(ul); this.zLoadHistory(zg); first = false; }\n"
      "        else { this.evq.push.apply(this.evq, ul); this.zevq.push.apply(this.zevq, zg); }")

# 6) loop: anima o próximo evento do Zangão quando ele está livre
troca("    if (this.zcur) this.zstep(); else this.patrol();",
      "    if (this.zcur) this.zstep(); else if (this.zevq.length) this.zhandle(this.zevq.shift()); else this.patrol();")

# 7) com fila grande, o Zangão anda e trabalha mais rápido para alcançar o bot
troca("    const sp = 1.1 * (this.props.speed ?? 1), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;\n"
      "    if (Math.abs(dx) > 0.01)",
      "    const sp = 1.1 * (this.props.speed ?? 1) * this.zpressa(), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;\n"
      "    if (Math.abs(dx) > 0.01)")

# 8) reducer, animação e histórico dos eventos reais
ZCODE = r"""
  zpressa() { const q = this.zevq ? this.zevq.length : 0; return q > 40 ? 6 : q > 12 ? 3 : 1; }
  zN(k) { return Math.max(1, Math.round(k / (this.props.speed ?? 1) / this.zpressa())); }
  ztime(ev) { const d = ev.ts ? new Date(ev.ts) : new Date(); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }
  static ZMODO = { gravar: 'gravando no VIOS', teste: 'simulação (não grava)', leitura: 'somente leitura' };
  static ZMOTIVO = {
    outro_tipo: 'Não é "Editar os dados da ação protocolada"', previdencia_privada: 'Previdência privada/complementar (cível)',
    sem_sinal_previdenciario: 'Sem sinal previdenciário', outra_area: 'Previdenciária com termo de outra área: conferir à mão',
    sinal_sem_previdenci: 'Sinal previdenciário sem "previdenci": conferir à mão', ja_registrada: 'Já resolvida antes (registro)',
    fora_da_tarefa_unica: 'Fora da tarefa escolhida (--tarefa)',
    sem_comprovante: 'Sem comprovante de protocolo', mais_de_um_comprovante: 'Mais de um comprovante de protocolo',
    pdf_sem_texto: 'PDF escaneado (sem texto)', comprovante_nao_baixou: 'Não consegui baixar o comprovante',
    comprovante_nao_e_pdf: 'O link do comprovante não devolveu um PDF', dado_duplicado_no_pdf: 'Dado com dois valores no PDF',
    dado_ausente_no_pdf: 'Dado não encontrado no PDF', cnj_diferente_do_processo: 'O PDF é de outro processo',
    campo_com_outro_valor: 'Campo já preenchido com outro valor', processo_diferente_na_edicao: 'A edição não é do processo aberto',
    orgao_nao_apareceu: 'Órgão julgador não apareceu na lista', aviso_inesperado: 'Aviso do VIOS que o bot não responde',
    releitura_divergente: 'A releitura depois de gravar não confere', releitura_falhou: 'Não consegui reler a tela',
    outra_janela: 'Abriu outra janela', sem_id_do_processo: 'Sem id do processo', bloqueio_inativo: 'Bloqueio de envios inativo',
    preenchimento_divergente: 'A tela não mostra o que foi preenchido', elemento_nao_unico: 'Elemento da tela não é único',
    elemento_nao_apareceu: 'Elemento da tela não apareceu', excecao: 'Erro inesperado (ver logs/bot.log)',
    config_invalida: 'Configuração inválida (.env)', navegador_falhou: 'O navegador não abriu',
    tarefa_nao_encontrada: 'A tarefa do --tarefa não está no calendário', login_falhou: 'Login no VIOS falhou'
  };
  zmotivo(m) { return m ? (Component.ZMOTIVO[m] || m) : ''; }
  zfimTexto(ev) {
    const k = ev.contagens || {}, partes = [];
    [['gravado', 'gravadas'], ['teste', 'testadas'], ['leitura', 'lidas'], ['ja_estava', 'já estavam'], ['ja_registrada', 'já registradas'],
     ['pulada', 'puladas'], ['conferir', 'a conferir'], ['erro', 'com erro'], ['ambigua', 'ambíguas']].forEach(([c, t]) => { if (k[c]) partes.push(k[c] + ' ' + t); });
    return partes.join(' · ');
  }
  zreduce(ev) {
    this.setState(s => {
      if (ev.tipo === 'execucao_iniciada') return { zphase: 'scanning', zfase: null, ztasks: [], zcal: null, zresult: null, zmodo: ev.modo || 'teste', zpanelOpen: false };
      if (ev.tipo === 'fase') return { zfase: ev.fase, zphase: ev.fase === 'processando' ? 'capturing' : 'scanning' };
      if (ev.tipo === 'calendario') {
        const T = (ev.tarefas || []).map(x => ({ real: true, id: x.tarefa_id, classe: x.classe, decisao: x.decisao, motivo: x.motivo,
          st: x.decisao === 'processar' ? 'queue' : x.classe === 'ambigua' ? 'amb' : x.decisao === 'ja_registrada' ? 'reg' : 'skip' }));
        return { zphase: 'filtering', zcal: { total: ev.total || 0, prev: ev.previdenciarias || 0, proc: ev.processar || 0, ign: ev.ignoradas || 0, amb: ev.ambiguas || 0 }, ztasks: T };
      }
      if (ev.tipo === 'tarefa') {
        const a = s.ztasks.slice(); let i = a.findIndex(x => x.id === ev.tarefa_id);
        if (i < 0) { a.push({ real: true, id: ev.tarefa_id, classe: 'previdenciaria', decisao: 'processar' }); i = a.length - 1; }
        const st = { abrindo: 'open', comprovante_lido: 'cap', preenchendo: 'upd' }[ev.etapa] || ev.etapa;
        const pid = Array.isArray(ev.processo_id) ? ev.processo_id.join(', ') : ev.processo_id;
        a[i] = { ...a[i], st, proc: pid || a[i].proc, campos: ev.campos || a[i].campos, motivo: ev.motivo || (st === 'open' ? null : a[i].motivo),
          orgao: ev.orgao_cadastrado ? 'cadastrado' : ev.orgao_novo ? 'novo' : a[i].orgao };
        return { ztasks: a, zphase: 'capturing' };
      }
      if (ev.tipo === 'execucao_fim') {
        const lbl = { concluido: 'concluído', testado: 'simulação concluída', lido: 'leitura concluída', fora_do_dia: 'hoje não é dia de rodar', parou: 'parou' }[ev.resultado] || ev.resultado;
        const det = this.zfimTexto(ev), mot = ev.motivo ? ' · ' + this.zmotivo(ev.motivo) : '';
        const extra = ev.resultado === 'fora_do_dia' ? { ztasks: [], zcal: null, zmodo: null } : {};
        return { ...extra, zphase: 'done', zresult: { resultado: ev.resultado, motivo: ev.motivo, texto: det },
          log: [{ time: this.ztime(ev), text: 'Zangão · ' + lbl + (det ? ' · ' + det : '') + mot }].concat(s.log).slice(0, 8) };
      }
      return null;
    });
  }
  zhandle(ev) {
    const z = this.z, N = k => this.zN(k), O = 20, TOR = [O + 14, 10], FIL = [O + 9, 4], CAP = [O + 15, 4], HOME = [O + 3, 4], S = [];
    z.path = []; z.wait = 0;
    const tid = 'Tarefa ' + (ev.tarefa_id || '?');
    if (ev.tipo === 'execucao_iniciada') {
      const m = Component.ZMODO[ev.modo] || ev.modo;
      S.push({ type: 'call', fn: () => { this.zreduce(ev); z.bubble = '!'; z.dir = 'down'; this.zst('Execução iniciada'); this.zsay('Começando: ' + m + (ev.fora_da_janela ? ', fora dos 3 últimos dias' : '') + (ev.tarefa_unica ? ', uma tarefa só' : '') + '.'); } },
        { type: 'wait', n: N(40) }, { type: 'call', fn: () => { z.bubble = null; this.zst('Indo ao VIOS'); } }, { type: 'walk', to: TOR, face: 'right' });
    } else if (ev.tipo === 'fase') {
      const T = { entrando_vios: ['Entrando no VIOS…', 'Entrando no VIOS'], lendo_calendario: ['Lendo o calendário do VIOS…', 'Lendo o calendário'],
        processando: ['Indo às tarefas previdenciárias, uma por vez.', 'Processando'] }[ev.fase] || [String(ev.fase), String(ev.fase)];
      S.push({ type: 'walk', to: TOR, face: 'right' }, { type: 'act', n: N(ev.fase === 'processando' ? 30 : 80), fx: 'pull', start: () => { this.zreduce(ev); this.zsay(T[0]); this.zst(T[1]); } });
    } else if (ev.tipo === 'calendario') {
      S.push({ type: 'call', fn: () => { z.carry = true; this.zst('Indo ao filtro'); } }, { type: 'walk', to: FIL, face: 'up' },
        { type: 'act', n: N(110), fx: 'filter', start: () => { this.zst('Classificando'); this.zsay('Separando as tarefas: previdenciárias, ignoradas e ambíguas…'); },
          end: () => { this.zreduce(ev); z.carry = false; this.setState({ zpanelOpen: true });
            this.zsay((ev.total || 0) + ' tarefas no calendário: ' + (ev.processar || 0) + ' a processar, ' + (ev.ignoradas || 0) + ' ignoradas e ' + (ev.ambiguas || 0) + ' ambíguas (conferir à mão).'); } },
        { type: 'walk', to: TOR, face: 'right' });
    } else if (ev.tipo === 'tarefa') {
      const camp = (ev.campos || []).map(c => ({ cnj: 'N.º CNJ', orgao: 'órgão julgador', valor: 'valor da ação' }[c] || c)).join(', ');
      const m = { abrindo: [tid + ': abrindo a tarefa e o processo no VIOS…', 'pull', 40], comprovante_lido: [tid + ': li o comprovante de protocolo (CNJ, órgão e valor).', 'capture', 50],
        preenchendo: [tid + ': preenchendo ' + (camp || 'os campos vazios') + '…', 'send', 45], lida: [tid + ': só leitura · preencheria ' + (camp || 'nada') + '.', 'send', 35],
        gravada: [tid + ': gravada e conferida no VIOS.', null, 30], ja_estava: [tid + ': já estava com os dados do comprovante.', null, 30],
        testada: [tid + ': simulação · preenchida e não gravada.', null, 30], pulada: [tid + ' pulada: ' + this.zmotivo(ev.motivo) + '.', null, 35],
        conferir: [tid + ': CONFERIR NO VIOS · ' + this.zmotivo(ev.motivo) + '.', null, 40], erro: [tid + ' deu erro: ' + this.zmotivo(ev.motivo) + '.', null, 35] }[ev.etapa]
        || [tid + ': ' + ev.etapa, null, 30];
      if (ev.etapa === 'comprovante_lido') S.push({ type: 'walk', to: CAP, face: 'up' });
      else S.push({ type: 'walk', to: TOR, face: 'right' });
      S.push({ type: 'act', n: N(m[2]), fx: m[1], start: () => { this.zreduce(ev); this.zsay(m[0]); this.zst(tid); z.bubble = ['pulada', 'conferir', 'erro'].includes(ev.etapa) ? '!' : null; },
        end: () => { if (ev.etapa !== 'conferir') z.bubble = null; } });
    } else if (ev.tipo === 'execucao_fim') {
      const fora = ev.resultado === 'fora_do_dia', det = this.zfimTexto(ev);
      const m = { concluido: 'Pronto! Execução concluída no VIOS.', testado: 'Simulação concluída. Nada foi gravado no VIOS.', lido: 'Leitura concluída. Nada foi preenchido nem gravado.',
        fora_do_dia: 'Hoje não é dia de rodar: só trabalho nos 3 últimos dias do mês.', parou: 'Parei: ' + this.zmotivo(ev.motivo) + '.' }[ev.resultado] || 'Execução finalizada.';
      S.push({ type: 'call', fn: () => { this.zreduce(ev); z.dir = 'down'; z.bubble = ev.resultado === 'parou' ? '!' : null; this.zsay(m + (det ? ' ' + det + '.' : '')); this.zst(ev.resultado === 'parou' ? 'Parou' : fora ? 'Fora do dia' : 'Concluído'); } });
      if (!fora) S.push({ type: 'wait', n: N(110) }, { type: 'call', fn: () => { z.bubble = null; this.zst('Voltando à doca'); } }, { type: 'walk', to: HOME, face: 'down' });
      S.push({ type: 'call', fn: () => { this.zst('Ocioso'); z.wait = 200; } });
    } else this.zreduce(ev);
    if (S.length) this.zrun(S);
  }
  zLoadHistory(evs) {
    evs.forEach(e => this.zreduce(e));
    setTimeout(() => {
      const s = this.state, zp = s.zphase, z = this.z, O = 20;
      const pos = zp === 'filtering' ? [O + 9, 4] : (zp === 'scanning' || zp === 'capturing') ? [O + 14, 10] : [O + 3, 4];
      z.x = pos[0] * 16; z.y = pos[1] * 16; z.path = []; z.dir = pos[0] === O + 14 ? 'right' : 'down';
      if (zp === 'idle') return;
      if (zp === 'done') {
        const r = s.zresult || {};
        this.zst(r.resultado === 'parou' ? 'Parou' : 'Ocioso');
        this.zsay(r.resultado === 'fora_do_dia' ? 'Hoje não é dia de rodar: só trabalho nos 3 últimos dias do mês.'
          : 'Última execução: ' + ({ concluido: 'concluída', testado: 'simulação', lido: 'somente leitura', parou: 'parou · ' + this.zmotivo(r.motivo) }[r.resultado] || r.resultado) + (r.texto ? ' · ' + r.texto : '') + '.');
        return;
      }
      z.wait = 1e9;  // no meio de uma execução: fica no posto até chegar o próximo evento
      this.zst('Trabalhando'); this.zsay('Execução em andamento: ' + (Component.ZMODO[s.zmodo] || s.zmodo || '') + '. Acompanhando o próximo passo…');
    }, 0);
  }
  zVals() {"""
troca("\n  zVals() {", ZCODE)

# 9) painel da Vila 02 com as tarefas reais (o modo simulado continua com o ZSAMPLE)
troca("""    const s = this.state, zp = s.zphase, T = s.ztasks;
    const idx = { idle: 0, scanning: 0, filtering: 1, capturing: 2, updating: 3, done: 4 }[zp];""",
      """    if (this.fonte() === 'servidor') return this.zValsReal();
    const s = this.state, zp = s.zphase, T = s.ztasks;
    const idx = { idle: 0, scanning: 0, filtering: 1, capturing: 2, updating: 3, done: 4 }[zp];""")

ZREAL = r"""
  zValsReal() {
    const s = this.state, zp = s.zphase, T = s.ztasks, r = s.zresult || {}, off = s.conn === 'offline';
    const idx = zp === 'done' ? 4 : zp === 'capturing' ? 2 : zp === 'filtering' ? 1 : zp === 'scanning' ? (s.zfase === 'lendo_calendario' ? 1 : 0) : 0;
    const names = ['Entrar no VIOS', 'Ler o calendário', 'Processar tarefas', 'Resumo'];
    const steps = names.map((t, i) => ({ n: '0' + (i + 1), t,
      line: i < idx ? '#b68235' : i === idx ? '#f0c46a' : 'rgba(182,130,53,.22)',
      color: i <= idx ? 'var(--color-neutral-100)' : 'var(--color-neutral-300)' }));
    const leitura = s.zmodo === 'leitura';
    const TAG = { queue: ['Na fila', '#a9a49b'], skip: ['Ignorada', '#8a857c'], amb: ['Ambígua · conferir à mão', '#f0c46a'], reg: ['Já registrada', '#8a857c'],
      open: ['Abrindo…', '#e3c08a'], cap: ['Comprovante lido', '#e3c08a'], upd: [leitura ? 'Lendo a edição…' : 'Preenchendo…', '#e3c08a'],
      gravada: ['Gravada', '#9cc98a'], ja_estava: ['Já estava', '#8a857c'], testada: ['Testada', '#9cc98a'], lida: ['Lida', '#9cc98a'],
      pulada: ['Pulada · conferir', '#ff7a66'], conferir: ['Conferir no VIOS', '#ff7a66'], erro: ['Erro', '#ff7a66'] };
    const CLS = { previdenciaria: 'Previdenciária', ignorada: 'Ignorada', ambigua: 'Ambígua' };
    const CAMPO = { cnj: 'N.º CNJ', orgao: 'órgão julgador', valor: 'valor da ação' };
    const rows = T.map((t, i) => {
      const tc = TAG[t.st] || [String(t.st), '#a9a49b'], partes = [];
      if (t.motivo) partes.push(this.zmotivo(t.motivo));
      if (t.campos && t.campos.length) partes.push((t.st === 'lida' ? 'Preencheria: ' : t.st === 'testada' ? 'Preencheu (sem gravar): ' : 'Campos: ') + t.campos.map(c => CAMPO[c] || c).join(', '));
      else if (t.campos && ['gravada', 'testada', 'lida'].includes(t.st)) partes.push('Nenhum campo vazio');
      if (t.orgao) partes.push(t.orgao === 'cadastrado' ? 'Órgão julgador novo cadastrado' : 'Órgão julgador não está na lista (cadastro só com --confirmar)');
      const msg = partes.join('\n');
      return { n: String(i + 1).padStart(2, '0'), proc: 'Tarefa ' + (t.id || '?'), task: CLS[t.classe] || t.classe || '', meta: t.proc ? 'Processo ' + t.proc : '',
        tag: tc[0], col: tc[1], hasIssue: !!msg, issueMsg: msg, issueCol: tc[1], hasFix: false, fixLabel: '', applyFix: () => {} };
    });
    const FIM = ['gravada', 'ja_estava', 'testada', 'lida', 'pulada', 'conferir', 'erro'];
    const alvo = T.filter(t => t.decisao === 'processar').length, fin = T.filter(t => FIM.includes(t.st)).length;
    const pre = s.zmodo === 'teste' ? 'Simulação · ' : leitura ? 'Somente leitura · ' : '';
    let summary = 'Nenhuma execução ainda';
    if (r.resultado === 'fora_do_dia') summary = 'Hoje não é dia de rodar (3 últimos dias do mês)';
    else if ((zp === 'capturing' || zp === 'done') && s.zcal) summary = pre + fin + ' de ' + alvo + ' tarefas processadas';
    else if (s.zcal) summary = pre + s.zcal.total + ' no calendário · ' + s.zcal.proc + ' a processar';
    else if (zp === 'scanning') summary = pre + 'lendo o VIOS…';
    let showAction = !!T.length, actionLabel = s.zpanelOpen ? 'Fechar painel' : 'Abrir painel';
    const fimTxt = { concluido: 'Execução concluída.', testado: 'Simulação concluída: nada gravado.', lido: 'Leitura concluída: nada preenchido.',
      fora_do_dia: 'Hoje não é dia de rodar.', parou: 'Parou: ' + this.zmotivo(r.motivo) }[r.resultado];
    return {
      panelTitle: 'Comprovantes previdenciários', tabALabel: 'Tarefas', showSend: false,
      steps, rows, summary,
      sendHint: zp === 'done' && fimTxt ? fimTxt + (r.texto ? ' ' + r.texto + '.' : '') : 'O Zangão roda pelo agendador. A vila só assiste.',
      panelOpen: s.zpanelOpen, togglePanel: () => this.setState(st => ({ zpanelOpen: !st.zpanelOpen })),
      hudStatus: 'Zangão · ' + s.zstatus, dotColor: off ? '#5a5f67' : '#f2c230', hudStep: off ? 'Sem conexão' : idx < 4 ? 'Etapa ' + (idx + 1) + '/4' : 'Concluído',
      speaker: 'Zangão', dialogShown: s.ztext.slice(0, s.ztyped), moreOpacity: s.ztyped >= s.ztext.length ? 1 : 0,
      showAction, actionLabel
    };
  }
}
</script>"""
# acrescenta zValsReal no fim da classe (o template termina a classe com "\n}\n</script>")
if ETAPA1:
    fim_classe = t.rfind("\n}\n</script>")
    assert fim_classe > 0
    t = t[:fim_classe] + ZREAL + t[fim_classe + len("\n}\n</script>"):]

# ---------------- etapa 2: botões para rodar o Zangão pela vila ----------------
troca("zcal: null, zresult: null };", "zcal: null, zresult: null, zsrv: null, zconf: 0, zpedido: false };", 2)
troca("e preencho N.º CNJ, órgão julgador e valor da ação.';",
      "e preencho N.º CNJ, órgão julgador e valor da ação. Para me pôr a trabalhar, use os botões aqui embaixo.';", 2)
troca("cancelAnimationFrame(this.raf); clearInterval(this.poll);",
      "cancelAnimationFrame(this.raf); clearInterval(this.poll); clearInterval(this.zpoll); clearTimeout(this.zconfT);", 2)
troca("    tick(); this.poll = setInterval(tick, 2000);",
      "    tick(); this.poll = setInterval(tick, 2000);\n"
      "    this.zstatusTick(); this.zpoll = setInterval(() => this.zstatusTick(), 4000);", 2)
troca("      if (this.fonte() === 'servidor') { if (this.state.ztasks.length) this.setState(st => ({ zpanelOpen: !st.zpanelOpen })); }",
      "      if (this.fonte() === 'servidor') { const b = this.zbotoes(); if (b.a) b.a.fn(); }", 2)
troca("\n  zValsReal() {", r"""
  async zstatusTick() {
    try {
      const r = await fetch('/zangao/status', { credentials: 'same-origin' });
      if (r.ok) this.setState({ zsrv: await r.json() });
    } catch (e) { /* sem conexão: o topo já mostra pelo /eventos */ }
  }
  async zrodar(modo) {
    if (this.state.zpedido) return;
    clearTimeout(this.zconfT);
    this.setState({ zpedido: true, zconf: 0 });
    try {
      const r = await fetch('/zangao/rodar', { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ modo }) });
      const j = await r.json().catch(() => ({}));
      if (j && 'rodando' in j) this.setState({ zsrv: j });
      if (!r.ok) this.zsay('Não deu para rodar: ' + (j.erro || 'HTTP ' + r.status) + '.');
      else this.zsay(modo === 'gravar' ? 'Pedido recebido! Vou entrar no VIOS e gravar de verdade.' : 'Pedido recebido! Vou rodar o teste: preencho e não gravo nada.');
    } catch (e) { this.zsay('Sem conexão com o servidor. Tente de novo.'); }
    this.setState({ zpedido: false });
  }
  zbotoes() {
    const s = this.state, srv = s.zsrv, T = s.ztasks, rodando = !!(srv && srv.rodando) || s.zpedido;
    const painel = { label: s.zpanelOpen ? 'Fechar painel' : 'Abrir painel', fn: () => this.setState(st => ({ zpanelOpen: !st.zpanelOpen })) };
    const out = { a: null, b: null, p: null, rodando };
    if (!srv || !srv.configurado || rodando) { if (T.length) out.a = painel; return out; }
    out.a = { label: 'Testar sem gravar', fn: () => this.zrodar('teste') };
    if (srv.janela) {
      const conf = s.zconf > Date.now();
      out.b = { label: conf ? 'Confirmar: gravar no VIOS' : 'Rodar e gravar no VIOS', bg: conf ? '#c81e14' : '#3a2f1f',
        fn: () => {
          if (this.state.zconf > Date.now()) return this.zrodar('gravar');
          this.setState({ zconf: Date.now() + 6000 });
          this.zsay('Isto grava no VIOS de verdade. Para confirmar, clique em "Confirmar: gravar no VIOS" em até 6 segundos.');
          clearTimeout(this.zconfT); this.zconfT = setTimeout(() => this.setState({ zconf: 0 }), 6000);
        } };
    }
    if (T.length) out.p = painel;
    return out;
  }
  zValsReal() {""", 2)
troca("    let showAction = !!T.length, actionLabel = s.zpanelOpen ? 'Fechar painel' : 'Abrir painel';",
      "    const B = this.zbotoes(), srv = s.zsrv;\n"
      "    const showAction = !!B.a, actionLabel = B.a ? B.a.label : '';", 2)
troca("      sendHint: zp === 'done' && fimTxt ? fimTxt + (r.texto ? ' ' + r.texto + '.' : '') : 'O Zangão roda pelo agendador. A vila só assiste.',",
      "      sendHint: !srv ? 'Conectando ao servidor…' : !srv.configurado ? 'O Zangão não está instalado neste servidor (ZANGAO_PASTA).'\n"
      "        : B.rodando ? (srv.modo === 'gravar' ? 'Rodando e gravando no VIOS' : srv.modo === 'teste' ? 'Rodando o teste (não grava)' : 'Rodando') + (srv.inicio ? ' desde ' + srv.inicio.slice(11, 16) : '') + '.'\n"
      "        : zp === 'done' && fimTxt ? fimTxt + (r.texto ? ' ' + r.texto + '.' : '')\n"
      "        : srv.janela ? 'Hoje é dia de rodar: teste ou grave no VIOS.' : 'O teste roda em qualquer dia e não grava. Gravar no VIOS só a partir de ' + srv.proxima_janela + '.',\n"
      "      showAction2: !!B.b, actionLabel2: B.b ? B.b.label : '', action2: () => B.b && B.b.fn(), action2Bg: B.b ? B.b.bg : '#3a2f1f',\n"
      "      showPainel: !!B.p, painelLabel: B.p ? B.p.label : '', painel: () => B.p && B.p.fn(),", 2)
troca("      showAction, actionLabel, action: () => this.action()\n    };",
      "      showAction, actionLabel, action: () => this.action(),\n"
      "      showAction2: false, actionLabel2: '', action2: () => {}, action2Bg: '#3a2f1f', showPainel: false, painelLabel: '', painel: () => {}\n    };", 2)
troca("{{ actionLabel }}\n        </button>\n      </sc-if>\n",
      "{{ actionLabel }}\n        </button>\n      </sc-if>\n"
      "      <sc-if value=\"{{ showAction2 }}\" hint-placeholder-val=\"{{ false }}\">\n"
      "        <button sc-camel-on-click=\"{{ action2 }}\" style=\"all:unset;cursor:pointer;flex:none;background:{{ action2Bg }};color:#f6f1e6;border-radius:3px;padding:.65em 1.1em;font-size:clamp(11px,1.2cqw,15px);letter-spacing:.06em;white-space:nowrap;\">{{ actionLabel2 }}</button>\n"
      "      </sc-if>\n"
      "      <sc-if value=\"{{ showPainel }}\" hint-placeholder-val=\"{{ false }}\">\n"
      "        <button sc-camel-on-click=\"{{ painel }}\" style=\"all:unset;cursor:pointer;flex:none;border:1px solid #201f1d;color:#201f1d;border-radius:3px;padding:.6em .9em;font-size:clamp(11px,1.2cqw,15px);white-space:nowrap;\">{{ painelLabel }}</button>\n"
      "      </sc-if>\n", 2)

# ---------------- etapa 3: alcançar o estado atual sem reprisar tudo ----------------
# com a aba escondida o Chrome pausa as animações e consulta /eventos só 1 vez por minuto; os
# eventos se acumulam e, ao voltar, o robô reprisava o envio inteiro passo a passo (minutos).
# Cada evento é aplicado uma vez só (marca no próprio evento), então dá para aplicar o que falta
# de uma vez e pôr o robô no lugar certo.
troca("  reduce(ev) {\n    this.setState(s => {",
      "  reduce(ev) {\n    if (ev.__feito) return;\n    ev.__feito = true;\n    this.setState(s => {", 3)
troca("  zreduce(ev) {\n    this.setState(s => {",
      "  zreduce(ev) {\n    if (ev.__zfeito) return;\n    ev.__zfeito = true;\n    this.setState(s => {", 3)
troca("  handle(ev) {\n", "  handle(ev) {\n    this.atual = ev;\n", 3)
troca("  zhandle(ev) {\n", "  zhandle(ev) {\n    this.zatual = ev;\n", 3)
troca("""    evs.forEach(e => this.reduce(e));
    setTimeout(() => {
      const ph = this.state.phase, u = this.u;""", """    evs.forEach(e => this.reduce(e));
    setTimeout(() => this.posicionar(), 0);
  }
  posicionar() {
    {
      const ph = this.state.phase, u = this.u;
      u.path = []; u.fx = null; u.progress = null; u.carry = false; this.drop = null;""", 3)
troca("""      this.say({ conferindo: 'Conferindo as CIs do arquivo…', aguardando: 'Conferência pronta. Aguardando o envio na página Ultron.', enviando: 'Trabalhando na Torre VIOS…' }[ph] || Component.IDLE);
    }, 0);
  }""", """      const ult = (this.state.log.find(l => String(l.text).startsWith('Ultron · ')) || {}).text;
      this.say(ph === 'done' && ult ? 'Último envio: ' + ult.replace(/^Ultron · /, '') + '.'
        : ({ conferindo: 'Conferindo as CIs do arquivo…', aguardando: 'Conferência pronta. Aguardando o envio na página Ultron.', enviando: 'Trabalhando na Torre VIOS…' }[ph] || Component.IDLE));
    }
  }
  alcancar() {
    // aba escondida ou fila grande: aplica sem animar o que ficou para trás e põe o Ultron no lugar
    const q = this.evq.splice(0);
    if (this.atual) this.reduce(this.atual);
    q.forEach(e => this.reduce(e));
    this.seq = []; this.cur = null;
    setTimeout(() => this.posicionar(), 0);
  }
  zalcancar() {
    const q = this.zevq.splice(0);
    if (this.zatual) this.zreduce(this.zatual);
    q.forEach(e => this.zreduce(e));
    this.zseq = []; this.zcur = null;
    setTimeout(() => this.zposicionar(), 0);
  }""", 3)
troca("""    evs.forEach(e => this.zreduce(e));
    setTimeout(() => {
      const s = this.state, zp = s.zphase, z = this.z, O = 20;""", """    evs.forEach(e => this.zreduce(e));
    setTimeout(() => this.zposicionar(), 0);
  }
  zposicionar() {
    {
      const s = this.state, zp = s.zphase, z = this.z, O = 20;
      z.fx = null; z.progress = null; z.carry = false; z.bubble = null; z.wait = 0;""", 3)
troca("""      this.zst('Trabalhando'); this.zsay('Execução em andamento: ' + (Component.ZMODO[s.zmodo] || s.zmodo || '') + '. Acompanhando o próximo passo…');
    }, 0);
  }""", """      this.zst('Trabalhando'); this.zsay('Execução em andamento: ' + (Component.ZMODO[s.zmodo] || s.zmodo || '') + '. Acompanhando o próximo passo…');
    }
  }""", 3)
troca("    if (!this.cur && this.evq.length) this.handle(this.evq.shift());",
      "    if (this.evq.length > 20) this.alcancar();\n"
      "    if (this.zevq.length > 30) this.zalcancar();\n"
      "    if (!this.cur && this.evq.length) this.handle(this.evq.shift());", 3)
troca("    window.addEventListener('keydown', this.onKey);\n",
      "    window.addEventListener('keydown', this.onKey);\n"
      "    this.onVis = () => { if (!document.hidden) { if (this.evq.length > 2) this.alcancar(); if (this.zevq.length > 2) this.zalcancar(); } };\n"
      "    document.addEventListener('visibilitychange', this.onVis);\n", 3)
troca("window.removeEventListener('keydown', this.onKey); }",
      "window.removeEventListener('keydown', this.onKey); document.removeEventListener('visibilitychange', this.onVis); }", 3)

# ---------------- etapa 4: /vila?vila=N abre direto na vila N ----------------
troca("conn: 'simulado', village: 0,",
      "conn: 'simulado', village: Math.max(0, Math.min(Component.NV - 1, (parseInt(new URLSearchParams(location.search).get('vila'), 10) || 1) - 1)),", 4)
troca("        if (first) { this.loadHistory(ul); this.zLoadHistory(zg); first = false; }",
      "        if (first) {\n"
      "          // ao abrir: o que aconteceu nos últimos 30 s é animado; o resto só monta o estado\n"
      "          const recente = e => e.ts && Date.now() - new Date(e.ts).getTime() < 30000;\n"
      "          const corte = l => { const i = l.findIndex(recente); return i < 0 ? l.length : i; };\n"
      "          const iu = corte(ul), iz = corte(zg);\n"
      "          this.loadHistory(ul.slice(0, iu)); this.zLoadHistory(zg.slice(0, iz));\n"
      "          this.evq.push.apply(this.evq, ul.slice(iu)); this.zevq.push.apply(this.zevq, zg.slice(iz));\n"
      "          first = false;\n"
      "        }", 4)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("ok")
