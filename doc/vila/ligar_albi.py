"""Liga a Vila 03 ao Albi (bot do Sonar): a vila acende, ganha as placas do Albi e o mascote dele
(o mesmo desenho de albi/mascote/mascote-gordo-de-pe.html, 22×19 pixels, com o piscar, o
achatar e a fivela que brilha), que anda pela vila conforme os eventos reais (bot: "albi"):
arquivo_subido (Receptor TXT) → execucao_iniciada (Conferência das linhas) → fase (Torre Sonar)
→ pedido (Torre Sonar, uma linha por vez) → execucao_fim (volta à doca).
O painel "Pesquisa de processos" mostra cada linha só pelo número da linha e o final do
documento ("CNPJ final 77"). No modo simulado (site publicado), o Albi só passeia pela vila.

uso: python3 doc/vila/ligar_albi.py bot/vila/vila.html  (edita no lugar; rodar DEPOIS do
     ligar_zangao.py; se já estiver aplicado, avisa e não muda nada)"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "ahandle(ev)" in t:
    sys.exit("a vila já está com o Albi")
if "zhandle(ev)" not in t or "get('vila')" not in t:
    sys.exit("rode antes o doc/vila/ligar_zangao.py (o Albi usa o que ele acrescenta)")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) estado do Albi
troca("zsrv: null, zconf: 0, zpedido: false };",
      "zsrv: null, zconf: 0, zpedido: false, aphase: 'idle', astatus: 'Ocioso', atext: '', atyped: 0, apedidos: [], "
      "apanelOpen: false, aresult: null, afile: null, atotal: null, avalidos: null };")

# 2) o robô do Albi (começa na doca da Vila 03), filas e a fala inicial
troca("this.zseq = []; this.zcur = null; this.zevq = [];",
      "this.zseq = []; this.zcur = null; this.zevq = [];\n"
      "    this.a = { x: 43 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 160, i: 0, bubble: null, carry: false, fx: null, progress: null };\n"
      "    this.aseq = []; this.acur = null; this.aevq = [];")
troca("    this.zsay(this.fonte() === 'servidor' ? Component.ZIDLE_REAL : Component.ZIDLE);\n",
      "    this.zsay(this.fonte() === 'servidor' ? Component.ZIDLE_REAL : Component.ZIDLE);\n"
      "    this.asay(this.fonte() === 'servidor' ? Component.AIDLE_REAL : Component.AIDLE);\n")

# 3) a Vila 03 acende (prédios, janelas, canos e luzes como nas outras)
troca("const O = v * 320, on = v <= 1;", "const O = v * 320, on = v <= 2;")
troca("if ((tx + ty) % 3 === 0) R(X + 7, Y + 7, 2, 2, tx < 40 ? '#f0c46a' : '#6b5a3a');",
      "if ((tx + ty) % 3 === 0) R(X + 7, Y + 7, 2, 2, tx < 60 ? '#f0c46a' : '#6b5a3a');")
troca("const on = tx < 40, a = on ? '#b68235' : '#6b5a3a'", "const on = tx < 60, a = on ? '#b68235' : '#6b5a3a'")
troca("for (let v = 1; v < Component.NV; v++) if ((f >> 6) % 2) R(v * 320 + 14 * 16 + 37, SY + 3, 2, 1, '#5a616b');",
      "for (let v = 3; v < Component.NV; v++) if ((f >> 6) % 2) R(v * 320 + 14 * 16 + 37, SY + 3, 2, 1, '#5a616b');")

# 4) placas, nome da vila e o aviso "Aguardando um bot" some
troca("const o = v * 20, on = v <= 1, mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : 'Doca 01 · vaga';",
      "const o = v * 20, on = v <= 2, mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : 'Doca 01 · Albi';")
troca("v === 1 ? 'Filtro previdenciário' : 'Receptor', on)", "v === 1 ? 'Filtro previdenciário' : 'Receptor TXT', on)")
troca("v === 1 ? 'Captura de dados' : 'Oficina', on)", "v === 1 ? 'Captura de dados' : 'Conferência', on)")
troca("v <= 1 ? 'Torre VIOS' : 'Torre de destino', on)", "v <= 1 ? 'Torre VIOS' : 'Torre Sonar', on)")
troca("for (let v = 2; v < NV; v++) signs.push(", "for (let v = 3; v < NV; v++) signs.push(")
troca("const vNames = ['01 · Ultron', '02 · Zangão', '03 · vaga'];", "const vNames = ['01 · Ultron', '02 · Zangão', '03 · Albi'];")
troca("    if (vi === 1) Object.assign(out, this.zVals());\n",
      "    if (vi === 1) Object.assign(out, this.zVals());\n    if (vi === 2) Object.assign(out, this.aVals());\n")

# 5) botão "A" na Vila 03: abre/fecha o painel
troca("  action() {\n    if (this.state.village === 1) {",
      "  action() {\n"
      "    if (this.state.village === 2) { if (this.state.apedidos.length) this.setState(st => ({ apanelOpen: !st.apanelOpen })); return; }\n"
      "    if (this.state.village === 1) {")

# 6) eventos: separa os do Albi (e, ao abrir, anima só os dos últimos 30 s)
troca("        const zg = evs.filter(e => e.bot === 'zangao');\n",
      "        const zg = evs.filter(e => e.bot === 'zangao');\n        const ab = evs.filter(e => e.bot === 'albi');\n")
troca("          const iu = corte(ul), iz = corte(zg);\n", "          const iu = corte(ul), iz = corte(zg), ia = corte(ab);\n")
troca("          this.loadHistory(ul.slice(0, iu)); this.zLoadHistory(zg.slice(0, iz));\n",
      "          this.loadHistory(ul.slice(0, iu)); this.zLoadHistory(zg.slice(0, iz)); this.aLoadHistory(ab.slice(0, ia));\n"
      "          this.aevq.push.apply(this.aevq, ab.slice(ia));\n")
troca("        else { this.evq.push.apply(this.evq, ul); this.zevq.push.apply(this.zevq, zg); }",
      "        else { this.evq.push.apply(this.evq, ul); this.zevq.push.apply(this.zevq, zg); this.aevq.push.apply(this.aevq, ab); }")

# 7) laço: o Albi anda, digita a fala e alcança o estado atual com fila grande / aba escondida
troca("    if (this.zcur) this.zstep(); else if (this.zevq.length) this.zhandle(this.zevq.shift()); else this.patrol();\n",
      "    if (this.zcur) this.zstep(); else if (this.zevq.length) this.zhandle(this.zevq.shift()); else this.patrol();\n"
      "    if (this.acur) this.astep(); else if (this.aevq.length) this.ahandle(this.aevq.shift()); else this.apatrol();\n"
      "    if (this.state.atyped < this.state.atext.length) this.setState(s => ({ atyped: s.atyped + 1 }));\n")
troca("    if (this.zevq.length > 30) this.zalcancar();\n",
      "    if (this.zevq.length > 30) this.zalcancar();\n    if (this.aevq.length > 30) this.aalcancar();\n")
troca("if (this.zevq.length > 2) this.zalcancar(); } };",
      "if (this.zevq.length > 2) this.zalcancar(); if (this.aevq.length > 2) this.aalcancar(); } };")

# 8) desenho do Albi (antes do Ultron, que é desenhado por último)
DRAW = r"""    {
      const a = this.a, O3 = 640, am = a.path.length > 0 && a.wait <= 0, afx = a.fx;
      R(O3 + 63, 4, 3, 3, (f >> 5) % 2 ? '#f29bbf' : '#6b3a52');
      R(O3 + TX + 15, TY, 2, 2, (afx === 'send' || afx === 'pull') ? ((f >> 2) % 2 ? '#f29bbf' : '#fff1c9') : ((f >> 5) % 2 ? '#f29bbf' : '#6b3a52'));
      if (afx === 'check') for (let i = 0; i < 5; i++) R(O3 + SX + 3, SY + 3 + ((i * 3 + (f >> 2)) % 11), 4 + ((i * 7 + (f >> 3)) % 16), 1, i % 3 === 0 ? '#f29bbf' : '#d4d8de');
      else if (['preenchendo', 'done'].includes(this.state.aphase)) {
        for (let i = 0; i < 4; i++) R(O3 + SX + 3, SY + 3 + i * 3, 14 + (i * 5) % 7, 1, '#9aa0a8');
        R(O3 + SX + 21, SY + 3, 2, 2, this.state.apedidos.some(p => p.etapa === 'erro' || p.etapa === 'invalido') ? '#ff5a3c' : '#3fd17a');
      }
      // igual ao mascote original: pisca, a fivela brilha e ele "achata" parado; andando, pula
      const hop = am ? (Math.floor(a.step / 6) % 2 ? -1 : 0) : ((f >> 4) % 2 ? 1 : 0), blink = !am && f % 240 < 12, glow = (f >> 5) % 2;
      const AP = Component.APAL, ax = a.x - 3, ay = a.y - 5 + hop;
      c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(Math.round(a.x + 1), Math.round(a.y + 14), 14, 2);
      Component.ASPR.forEach((row, j) => row.split('').forEach((ch, i) => {
        if (ch === '.') return;
        let col = AP[ch];
        if (ch === 'K' && blink && j < 5) col = AP.P;
        if (ch === 'O' && glow) col = '#f0c46a';
        R(ax + i, ay + j, 1, 1, col);
      }));
      if (a.carry) paper(a.x + 5, ay - 10);
      if (a.bubble === '!') { R(a.x + 4, ay - 13, 9, 11, '#201f1d'); R(a.x + 5, ay - 12, 7, 9, '#ffffff'); R(a.x + 8, ay - 11, 1, 5, '#c81e14'); R(a.x + 8, ay - 5, 1, 1, '#c81e14'); }
      if (a.progress != null) {
        R(a.x, ay - 7, 16, 5, '#201f1d'); R(a.x + 1, ay - 6, 14, 3, '#f6f1e6'); R(a.x + 1, ay - 6, Math.round(14 * a.progress), 3, '#f29bbf');
        const ac = this.acur, t0 = ac ? ac.t : 0, TXA = O3 + TX;
        if (afx === 'read') for (let i = 0; i < 4; i++) R(O3 + 148 + ((t0 * 3 + i * 11) % 9), 52 + ((t0 + i * 5) % 8), 1, 1, i % 2 ? '#f29bbf' : '#ffffff');
        if (afx === 'check') for (let i = 0; i < 3; i++) { const k = ((t0 + i * 18) % 54) / 54; R(a.x + 8 + (O3 + SX + 13 - a.x - 8) * k, ay + 6 + (SY + 7 - ay - 6) * k - Math.sin(k * Math.PI) * 8, 2, 2, '#f29bbf'); }
        if ((afx === 'send' || afx === 'pull') && ac) {
          const k = (t0 % 40) / 40;
          if (afx === 'send') R(a.x + 12 + (TXA + 8 - a.x - 12) * k, a.y + 4, 3, 3, '#f29bbf');
          else R(TXA + 8 + (a.x + 12 - TXA - 8) * k, a.y + 4, 3, 3, '#cfeaff');
        }
      }
    }
"""
troca("    const eyes = { vermelho:", DRAW + "    const eyes = { vermelho:")

# 9) desenho, falas, eventos e painel do Albi
ACODE = r"""
  static AIDLE = 'Sou o Albi. Recebo um .txt com um CPF/CNPJ por linha, entro no Sonar e preencho a Nova Pesquisa de processos de cada um. Por enquanto não confirmo nenhum pedido.';
  static AIDLE_REAL = 'Sou o Albi. Solte o .txt (um CPF/CNPJ por linha) na página do Albi: eu entro no Sonar e preencho a Nova Pesquisa de cada linha até o passo Pedido. Não confirmo nada.';
  static ASPR = [
    '........HHHHHH........', '......HHPPPPPPSS......', '.....HPPPPPPPPPPS.....', '....HPPKKPPPPKKPPS....',
    '....PPPKKPPPPKKPPS....', '...HPCCPPPPPPPPCCPS...', '..HPPPPPPKPPKPPPPPPS..', '.HPPPPPPPPKKPPPPPPPPS.',
    'LMPPPPPPPPPPPPPPPPPPML', 'LMSPPPPPPPPPPPPPPPPSML', '.DGGGGGGGGOOGGGGGGGGD.', '..UUVVUUUUUUUUUUVVUUU.',
    '.UUVVUUUUUUUUUUUUVVUUU', '.UUUUUUUUUUUUUUUUUUUUU', '..UUUUUUUUUUUUUUUUUUU.', '...UUUUUU....UUUUUU...',
    '...LLLLMM....LLLLMM...', '..LLMMMMD....LMMMMDD..', '..DDDDDDD....DDDDDDD..'];
  static APAL = { P: '#f29bbf', H: '#ffc9de', S: '#c96a93', K: '#1d1e21', C: '#ff6f9a', G: '#b68235', O: '#d9a54e',
    U: '#5b3a63', V: '#7d5687', L: '#d4d8de', M: '#9aa0a8', D: '#5a5f67' };
  asay(t) { this.setState({ atext: t, atyped: 0 }); }
  ast(t) { if (this.state.astatus !== t) this.setState({ astatus: t }); }
  apressa() { const q = this.aevq ? this.aevq.length : 0; return q > 40 ? 6 : q > 12 ? 3 : 1; }
  aN(k) { return Math.max(1, Math.round(k / (this.props.speed ?? 1) / this.apressa())); }
  arun(steps) { this.aseq = steps; this.anext(); }
  anext() {
    const s = this.aseq.shift(), a = this.a;
    this.acur = s ? { ...s, t: 0 } : null;
    if (!s) return;
    if (s.type === 'call') { s.fn(); this.anext(); }
    else if (s.type === 'walk') a.path = this.bfs([Math.round(a.x / 16), Math.round(a.y / 16)], s.to);
    else if (s.type === 'act') { a.fx = s.fx; a.progress = 0; s.start && s.start(); }
  }
  astep() {
    const c = this.acur, a = this.a;
    if (c.type === 'wait') { if (++c.t >= c.n) this.anext(); return; }
    if (c.type === 'act') { c.t++; a.progress = c.t / c.n; if (c.t >= c.n) { a.progress = null; a.fx = null; c.end && c.end(); this.anext(); } return; }
    if (!a.path.length) { if (c.face) a.dir = c.face; this.anext(); return; }
    const sp = 1.1 * (this.props.speed ?? 1) * this.apressa(), [tx, ty] = a.path[0], px = tx * 16, py = ty * 16, dx = px - a.x, dy = py - a.y;
    if (Math.abs(dx) > 0.01) a.dir = dx > 0 ? 'right' : 'left'; else if (Math.abs(dy) > 0.01) a.dir = dy > 0 ? 'down' : 'up';
    const m = Math.min(sp, Math.abs(dx) + Math.abs(dy));
    if (Math.abs(dx) > 0.01) a.x += Math.sign(dx) * Math.min(m, Math.abs(dx)); else a.y += Math.sign(dy) * Math.min(m, Math.abs(dy));
    a.step += m;
    if (Math.abs(px - a.x) < 0.02 && Math.abs(py - a.y) < 0.02) { a.x = px; a.y = py; a.path.shift(); }
  }
  apatrol() {
    const a = this.a, pts = [[49, 4], [53, 8], [46, 10], [43, 4]];
    if (a.wait > 0) { a.wait--; return; }
    if (!a.path.length) { a.path = this.bfs([Math.round(a.x / 16), Math.round(a.y / 16)], pts[a.i++ % pts.length]); if (!a.path.length) a.wait = 120; return; }
    const sp = 0.7 * (this.props.speed ?? 1), [tx, ty] = a.path[0], px = tx * 16, py = ty * 16, dx = px - a.x, dy = py - a.y;
    if (dx) a.dir = dx > 0 ? 'right' : 'left'; else if (dy) a.dir = dy > 0 ? 'down' : 'up';
    const m = Math.min(sp, Math.abs(dx) + Math.abs(dy));
    if (dx) a.x += Math.sign(dx) * m; else a.y += Math.sign(dy) * m;
    a.step += m;
    if (Math.abs(px - a.x) < 0.01 && Math.abs(py - a.y) < 0.01) { a.x = px; a.y = py; a.path.shift(); if (!a.path.length) { a.wait = 170; a.dir = 'down'; } }
  }
  afimTexto(r) {
    const k = (r && r.contagens) || {}, p = [];
    [['prontos', 'pronto(s) no passo Pedido'], ['erros', 'com erro'], ['invalidos', 'linha(s) inválida(s)']].forEach(([c, t]) => { if (k[c]) p.push(k[c] + ' ' + t); });
    return p.join(' · ');
  }
  areduce(ev) {
    if (ev.__afeito) return;
    ev.__afeito = true;
    this.setState(s => {
      if (ev.tipo === 'arquivo_subido') return { aphase: 'recebendo', apedidos: [], aresult: null, afile: ev.arquivo || null, atotal: ev.linhas ?? null, avalidos: null, apanelOpen: false };
      if (ev.tipo === 'execucao_iniciada') return { aphase: 'conferindo', atotal: ev.total ?? s.atotal, avalidos: ev.validos ?? null };
      if (ev.tipo === 'fase') return { aphase: ev.fase === 'preenchendo' ? 'preenchendo' : 'entrando' };
      if (ev.tipo === 'pedido') {
        const P = s.apedidos.slice(), i = P.findIndex(p => p.linha === ev.linha);
        const p = { ...(i >= 0 ? P[i] : { linha: ev.linha }), doc: ev.doc || (i >= 0 ? P[i].doc : ''), etapa: ev.etapa,
          valor: ev.valor || (i >= 0 ? P[i].valor : null), motivo: ev.motivo || (ev.etapa === 'preenchendo' ? null : (i >= 0 ? P[i].motivo : null)) };
        if (i >= 0) P[i] = p; else P.push(p);
        P.sort((x, y) => x.linha - y.linha);
        return { apedidos: P };
      }
      if (ev.tipo === 'execucao_fim') {
        const r = { resultado: ev.resultado, motivo: ev.motivo, contagens: ev.contagens || {} }, det = this.afimTexto(r);
        return { aphase: 'done', aresult: r,
          log: [{ time: this.ztime(ev), text: 'Albi · ' + (ev.resultado === 'parou' ? 'parou' + (ev.motivo ? ': ' + ev.motivo : '') : 'preencheu no Sonar, sem confirmar') + (det ? ' · ' + det : '') }].concat(s.log).slice(0, 8) };
      }
      return null;
    });
  }
  ahandle(ev) {
    this.aatual = ev;
    const a = this.a, N = k => this.aN(k), O = 40, HOME = [O + 3, 4], REC = [O + 9, 4], OFI = [O + 15, 4], TOR = [O + 14, 10], S = [];
    a.path = []; a.wait = 0;
    const lin = 'Linha ' + (ev.linha ?? '?') + (ev.doc ? ' (' + ev.doc + ')' : '');
    if (ev.tipo === 'arquivo_subido') {
      S.push({ type: 'call', fn: () => { this.areduce(ev); a.bubble = '!'; a.dir = 'down'; this.ast('Arquivo recebido'); this.asay('Recebi ' + (ev.arquivo || 'um arquivo') + (ev.linhas ? ' com ' + ev.linhas + ' linha(s)' : '') + '. Indo buscar no Receptor TXT.'); } },
        { type: 'wait', n: N(30) }, { type: 'call', fn: () => { a.bubble = null; } }, { type: 'walk', to: REC, face: 'up' },
        { type: 'act', n: N(60), fx: 'read', start: () => this.ast('Lendo o arquivo'), end: () => { a.carry = true; } });
    } else if (ev.tipo === 'execucao_iniciada') {
      S.push({ type: 'call', fn: () => { a.carry = true; this.ast('Indo à conferência'); } }, { type: 'walk', to: OFI, face: 'up' },
        { type: 'act', n: N(80), fx: 'check', start: () => { this.ast('Conferindo as linhas'); this.asay('Conferindo cada CPF/CNPJ: quantidade de números, dígito verificador e repetidos…'); },
          end: () => { this.areduce(ev); a.carry = false; const inv = (ev.total || 0) - (ev.validos || 0);
            this.asay((ev.validos || 0) + ' de ' + (ev.total || 0) + ' linha(s) válidas' + (inv ? '; ' + inv + ' inválida(s) ficam de fora (veja o painel).' : '.'));
            if (inv) this.setState({ apanelOpen: true }); } });
    } else if (ev.tipo === 'fase') {
      if (ev.fase === 'entrando_sonar') S.push({ type: 'walk', to: TOR, face: 'right' },
        { type: 'act', n: N(70), fx: 'pull', start: () => { this.areduce(ev); this.ast('Entrando no Sonar'); this.asay('Entrando no Sonar (se tiver outra sessão aberta com o mesmo login, eu encerro)…'); } });
      else S.push({ type: 'call', fn: () => { this.areduce(ev); this.ast('No Sonar'); this.asay('Dentro do Sonar. Vou preencher a Nova Pesquisa de uma linha por vez, sem confirmar.'); } });
    } else if (ev.tipo === 'pedido') {
      if (ev.etapa === 'invalido') this.areduce(ev);
      else if (ev.etapa === 'preenchendo') S.push({ type: 'walk', to: TOR, face: 'right' },
        { type: 'act', n: N(55), fx: 'send', start: () => { this.areduce(ev); a.bubble = null; this.ast('Linha ' + ev.linha); this.asay(lin + ': preenchendo a Nova Pesquisa (CPF/CNPJ) e indo ao passo Pedido…'); } });
      else S.push({ type: 'call', fn: () => { this.areduce(ev); a.bubble = ev.etapa === 'erro' ? '!' : null;
        this.asay(ev.etapa === 'pronto' ? lin + ': pronto no passo Pedido' + (ev.valor ? ' · ' + ev.valor : '') + '. Não confirmei.' : lin + ' deu erro: ' + (ev.motivo || 'sem detalhe') + '.'); } },
        { type: 'wait', n: N(ev.etapa === 'erro' ? 50 : 25) });
    } else if (ev.tipo === 'execucao_fim') {
      const r = { contagens: ev.contagens || {} }, det = this.afimTexto(r);
      S.push({ type: 'call', fn: () => { this.areduce(ev); a.carry = false; a.dir = 'down'; a.bubble = ev.resultado === 'parou' ? '!' : null;
        this.asay(ev.resultado === 'parou' ? 'Parei: ' + (ev.motivo || 'erro') + '.' : 'Pronto! Preenchi tudo no Sonar e não confirmei nenhum pedido.' + (det ? ' ' + det + '.' : ''));
        this.ast(ev.resultado === 'parou' ? 'Parou' : 'Concluído'); if (this.state.apedidos.length) this.setState({ apanelOpen: true }); } },
        { type: 'wait', n: N(110) }, { type: 'call', fn: () => { a.bubble = null; this.ast('Voltando à doca'); } }, { type: 'walk', to: HOME, face: 'down' },
        { type: 'call', fn: () => { this.ast('Ocioso'); a.wait = 220; } });
    } else this.areduce(ev);
    if (S.length) this.arun(S);
  }
  aLoadHistory(evs) {
    evs.forEach(e => this.areduce(e));
    setTimeout(() => this.aposicionar(), 0);
  }
  aposicionar() {
    const s = this.state, ap = s.aphase, a = this.a, O = 40;
    a.fx = null; a.progress = null; a.carry = false; a.bubble = null; a.wait = 0; a.path = [];
    const pos = ap === 'recebendo' ? [O + 9, 4] : ap === 'conferindo' ? [O + 15, 4] : (ap === 'entrando' || ap === 'preenchendo') ? [O + 14, 10] : [O + 3, 4];
    a.x = pos[0] * 16; a.y = pos[1] * 16; a.dir = pos[0] === O + 14 ? 'right' : 'down';
    if (ap === 'idle') return;
    if (ap === 'done') {
      const r = s.aresult || {}, det = this.afimTexto(r);
      this.ast(r.resultado === 'parou' ? 'Parou' : 'Ocioso');
      this.asay(r.resultado === 'parou' ? 'Última execução parou: ' + (r.motivo || 'erro') + '.' : 'Última execução: preenchi no Sonar e não confirmei' + (det ? ' · ' + det : '') + '.');
      return;
    }
    a.wait = 1e9;  // no meio de uma execução: fica no posto até chegar o próximo evento
    this.ast('Trabalhando'); this.asay('Execução em andamento' + (s.afile ? ' (' + s.afile + ')' : '') + '. Acompanhando o próximo passo…');
  }
  aalcancar() {
    const q = this.aevq.splice(0);
    if (this.aatual) this.areduce(this.aatual);
    q.forEach(e => this.areduce(e));
    this.aseq = []; this.acur = null;
    setTimeout(() => this.aposicionar(), 0);
  }
  aVals() {
    const s = this.state, ap = s.aphase, P = s.apedidos, r = s.aresult || {}, off = this.fonte() === 'servidor' && s.conn === 'offline';
    const idx = { idle: 0, recebendo: 0, conferindo: 1, entrando: 2, preenchendo: 3, done: 4 }[ap] ?? 0;
    const names = ['Arquivo subido', 'Conferir linhas', 'Entrar no Sonar', 'Preencher pedidos'];
    const steps = names.map((t, i) => ({ n: '0' + (i + 1), t,
      line: i < idx ? '#b68235' : i === idx ? '#f29bbf' : 'rgba(182,130,53,.22)',
      color: i <= idx ? 'var(--color-neutral-100)' : 'var(--color-neutral-300)' }));
    const TAG = { preenchendo: ['Preenchendo…', '#e3c08a'], pronto: ['Pronto · não confirmado', '#9cc98a'], erro: ['Erro', '#ff7a66'], invalido: ['Linha inválida', '#ff7a66'] };
    const rows = P.map(p => {
      const tc = TAG[p.etapa] || [String(p.etapa || 'Na fila'), '#a9a49b'];
      return { n: String(p.linha).padStart(2, '0'), proc: 'Linha ' + p.linha, task: p.doc || '', meta: p.valor ? 'Valor no Sonar: ' + p.valor : '',
        tag: tc[0], col: tc[1], hasIssue: !!p.motivo, issueMsg: p.motivo || '', issueCol: tc[1], hasFix: false, fixLabel: '', applyFix: () => {} };
    });
    const validos = P.filter(p => p.etapa !== 'invalido').length, fin = P.filter(p => p.etapa === 'pronto' || p.etapa === 'erro').length;
    let summary = 'Nenhuma execução ainda';
    if (ap === 'done') summary = r.resultado === 'parou' ? 'Parou' + (r.motivo ? ': ' + r.motivo : '') : (this.afimTexto(r) || 'Concluído');
    else if (ap === 'preenchendo') summary = fin + ' de ' + (s.avalidos ?? validos) + ' linha(s) preenchida(s)';
    else if (ap !== 'idle') summary = (s.afile || 'Arquivo') + (s.atotal ? ' · ' + s.atotal + ' linha(s)' : '');
    let naPagina = false;
    try { naPagina = window.top.location.pathname.startsWith('/albi'); } catch (e) { /* vila fora do servidor */ }
    const pagina = this.fonte() === 'servidor' && !naPagina;
    return {
      panelTitle: 'Pesquisa de processos · Sonar', tabALabel: 'Linhas', showSend: false,
      steps, rows, summary,
      sendHint: 'O Albi só preenche até o passo Pedido: não confirma nenhum pedido.',
      panelOpen: s.apanelOpen, togglePanel: () => this.setState(st => ({ apanelOpen: !st.apanelOpen })),
      hudStatus: 'Albi · ' + s.astatus, dotColor: off ? '#5a5f67' : '#f29bbf',
      hudStep: off ? 'Sem conexão' : idx < 4 ? 'Etapa ' + (idx + 1) + '/4' : 'Finalizado',
      speaker: 'Albi', dialogShown: s.atext.slice(0, s.atyped), moreOpacity: s.atyped >= s.atext.length ? 1 : 0,
      showAction: !!P.length, actionLabel: s.apanelOpen ? 'Fechar painel' : 'Abrir painel', action: () => this.action(),
      showAction2: pagina, actionLabel2: 'Página do Albi', action2: () => { window.top.location.href = '/albi'; }, action2Bg: '#c96a93',
      showPainel: false, painelLabel: '', painel: () => {}
    };
  }
  zVals() {"""
troca("\n  zVals() {", ACODE)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 03 ligada ao Albi em", caminho)
