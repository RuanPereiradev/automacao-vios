"""Põe o Jarvis (relatório mensal de processos, segundo usuário do VIOS) na Vila 04:
- a vila passa de 3 para 4 vilas; a Vila 04 acende (cores, placas e torre) e ganha o nome Jarvis;
- o Jarvis (núcleo de IA: esfera azul em espiral, com anéis e o centro pulsando; ou o mascote carmesim com propulsores) faz a ronda na Vila 04 e se apresenta no diálogo;
- no servidor (/vila): botões "Escolher grupos e gerar" e "Planilhas", que abrem a página /jarvis do Ultron
  (lá a pessoa marca os grupos e gera); /jarvis/status a cada 4 s; os eventos do bot "jarvis" mostram o andamento
  (grupo, processo X de Y e gasto) e o Jarvis vai à Leitura dos processos e às Planilhas enquanto trabalha.
Na vila de 5 vilas (01 Sam, 02 Bumblebee, 03 Albi, 04 vaga, 05 Orelha), ele acende a Vila 04, que estava
vaga, em vez de criar uma vila nova.
uso: python3 doc/vila/ligar_jarvis.py bot/vila/vila.html [nucleo|propulsor]  (edita no lugar; rodar POR ÚLTIMO,
     depois de todos os outros ligar_*.py; rodar de novo não muda nada)"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "jpatrol()" in t:
    sys.exit("a vila já está com o Jarvis")


def troca(velho, novo, vezes=1):
    global t
    assert t.count(velho) == vezes, ("trecho não encontrado (ou repetido)", velho[:80])
    t = t.replace(velho, novo)


CINCO = "static NV = 5;" in t  # vila atual: a Vila 04 já existe (vaga) e só acende
if CINCO:
    # 1-2) a Vila 04 vaga acende com as placas do Jarvis (a vila já tem 5 vilas, do ligar_orelha.py)
    troca("const O = v * 320, on = v <= 2 || v === 4;", "const O = v * 320, on = v <= 4;")
    troca("(tx < 60 || tx >= 80) ? '#f0c46a' : '#6b5a3a'", "'#f0c46a'")
    troca("const on = tx < 60 || tx >= 80, a = on", "const on = true, a = on")
    troca("for (let v = 3; v < Component.NV; v++) if (v !== 4 && (f >> 6) % 2)", "for (let v = 3; v < Component.NV; v++) if (v !== 3 && v !== 4 && (f >> 6) % 2)")
    troca("on = v <= 2 || v === 4, mine", "on = v <= 4, mine")
    troca("v === 4 ? 'Doca 01 · Orelha' : 'Doca 01 · vaga'", "v === 3 ? 'Doca 01 · Jarvis' : v === 4 ? 'Doca 01 · Orelha' : 'Doca 01 · vaga'")
    troca("v === 4 ? 'Calendário' : 'Receptor'", "v === 3 ? 'Leitura dos processos' : v === 4 ? 'Calendário' : 'Receptor'")
    troca("v === 4 ? 'Intimações' : 'Oficina'", "v === 3 ? 'Planilhas' : v === 4 ? 'Intimações' : 'Oficina'")
    troca("v <= 1 || v === 4 ? 'Torre VIOS'", "v <= 1 || v >= 3 ? 'Torre VIOS'")
    troca("if (v !== 4) signs.push(", "if (v !== 3 && v !== 4) signs.push(")
    troca("'04 · vaga'", "'04 · Jarvis'")

# 1) 4 vilas: largura do mundo e do canvas
if not CINCO:
  troca("width:300%;height:100%;transform:{{ worldTransform }}", "width:400%;height:100%;transform:{{ worldTransform }}")
  troca('<canvas ref="{{ canvasRef }}" width="960" height="224"', '<canvas ref="{{ canvasRef }}" width="1280" height="224"')
  troca("static NV = 3;", "static NV = 4;")

  # 2) a Vila 04 acesa (fundo, prédios, placas e torre)
  troca("on = v <= 1", "on = v <= 1 || v === 3", vezes=2)
  troca("tx < 40", "(tx < 40 || tx >= 60)", vezes=2)
  troca("mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : 'Doca 01 · vaga';",
        "mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : v === 3 ? 'Doca 01 · Jarvis' : 'Doca 01 · vaga';")
  troca("v === 1 ? 'Filtro previdenciário' : 'Receptor'", "v === 1 ? 'Filtro previdenciário' : v === 3 ? 'Leitura dos processos' : 'Receptor'")
  troca("v === 1 ? 'Captura de dados' : 'Oficina'", "v === 1 ? 'Captura de dados' : v === 3 ? 'Planilhas' : 'Oficina'")
  troca("v <= 1 ? 'Torre VIOS'", "on ? 'Torre VIOS'")
  troca("'03 · vaga'];", "'03 · vaga', '04 · Jarvis'];")
  troca("for (let v = 2; v < NV; v++) signs.push(", "for (let v = 2; v < NV; v++) if (v !== 3) signs.push(")

# 3) o Jarvis: sprite (o mascote), ronda e fala
troca("  static ZSPR = (() => {", r"""  static JIDLE = 'Sou o Jarvis. Uma vez por mês entro no VIOS só para ler: abro cada processo dos grupos clientes e monto a planilha do relatório mensal de cada grupo.';
  static JSPR = ['..HHHHHHHHHHHH..', '..HRRRRRRRRRRS..', '..RKKKKKKKKKKS..', '..RKBEKKKKEBKS..', '..RRRRRRRRRRRS..', 'RRRRRRRCCRRRRRSS', 'BRRRRRCWWCRRRRSB',
    '..RRRRRCCRRRRS..', '..RRGRRRRRRGRS..', '..SSSSSSSSSSSS..', '...G.G....G.G...', '...Y.Y....Y.Y...', '...F.F....F.F...', '...Q.Q....Q.Q...'];
  static ZSPR = (() => {""")
troca("    this.zseq = []; this.zcur = null; this.zevq = [];\n",
      "    this.zseq = []; this.zcur = null; this.zevq = [];\n"
      "    this.j = { x: 63 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 90, i: 0 };\n"
      "    this.setState({ jtext: Component.JIDLE, jtyped: 0, jsrv: null, jrun: null });\n")
troca("  update() {\n", "  update() {\n    this.jpatrol();\n"
      "    if ((this.state.jtyped || 0) < (this.state.jtext || '').length) this.setState(s => ({ jtyped: (s.jtyped || 0) + 1 }));\n")
# eventos do Jarvis: só montam o estado (sem fila de animação); status do servidor a cada 4 s
troca("        const zg = evs.filter(e => e.bot === 'zangao');\n",
      "        const zg = evs.filter(e => e.bot === 'zangao');\n"
      "        evs.filter(e => e.bot === 'jarvis').forEach(e => this.jreduce(e));\n")
troca("    this.zstatusTick(); this.zpoll = setInterval(() => this.zstatusTick(), 4000);\n",
      "    this.zstatusTick(); this.zpoll = setInterval(() => this.zstatusTick(), 4000);\n"
      "    this.jstatusTick(); this.jpoll = setInterval(() => this.jstatusTick(), 4000);\n")
troca("clearInterval(this.zpoll);", "clearInterval(this.zpoll); clearInterval(this.jpoll);")
# tecla A / Enter na Vila 04 = botão principal do Jarvis
troca("  action() {\n", "  action() {\n    if (this.state.village === 3) { const b = this.jbotoes(); if (b.a) b.a.fn(); return; }\n")
troca("  patrol() {", r"""  jfase() {
    const r = this.state.jrun, srv = this.state.jsrv;
    if (!r) return null;
    if (r.planilhasAte && Date.now() < r.planilhasAte) return 'planilhas';  // fica um pouco nas Planilhas
    if (r.fim || !(srv && srv.rodando)) return null;
    return r.etapa === 'entrando' ? 'torre' : r.etapa === 'salvando' ? 'planilhas' : 'leitura';
  }
  jalvo() {
    // Torre VIOS (entrando no VIOS), Leitura dos processos (lendo cada processo) e Planilhas (salvando)
    return { torre: [74, 10], leitura: [69, 4], planilhas: [75, 4] }[this.jfase()] || null;
  }
  jpatrol() {
    const j = this.j, pts = [[69, 4], [73, 8], [66, 10], [63, 4]], alvo = this.jalvo();
    if (alvo) {
      const at = [Math.round(j.x / 16), Math.round(j.y / 16)];
      if (!j.path.length && (at[0] !== alvo[0] || at[1] !== alvo[1])) j.path = this.bfs(at, alvo);
      if (!j.path.length) return;
    } else {
      if (j.wait > 0) { j.wait--; return; }
      if (!j.path.length) { j.path = this.bfs([Math.round(j.x / 16), Math.round(j.y / 16)], pts[j.i++ % pts.length]); if (!j.path.length) j.wait = 120; return; }
    }
    const sp = (alvo ? 1.4 : 0.9) * (this.props.speed ?? 1), [tx, ty] = j.path[0], px = tx * 16, py = ty * 16, dx = px - j.x, dy = py - j.y;
    const m = Math.min(sp, Math.abs(dx) + Math.abs(dy));
    if (dx) j.x += Math.sign(dx) * m; else j.y += Math.sign(dy) * m;
    j.step += m;
    if (Math.abs(px - j.x) < 0.01 && Math.abs(py - j.y) < 0.01) { j.x = px; j.y = py; j.path.shift(); if (!j.path.length) j.wait = 160; }
  }
  jdinheiro(v) { return 'US$ ' + Number(v || 0).toFixed(2).replace('.', ','); }
  jreduce(ev) {
    this.setState(s => {
      let r = s.jrun;
      if (ev.tipo === 'execucao_iniciada' || !r || r.id !== ev.envio)
        r = { id: ev.envio, grupos: ev.grupos || 0, teste: !!ev.teste, grupo: 0, feito: 0, total: 0, gasto: 0, etapa: 'entrando', fim: null };
      else r = { ...r };
      if (ev.tipo === 'grupo') Object.assign(r, { grupo: ev.grupo, grupos: ev.grupos || r.grupos, feito: 0, total: ev.processos || 0, etapa: 'lendo' });
      else if (ev.tipo === 'processo') Object.assign(r, { grupo: ev.grupo, grupos: ev.grupos || r.grupos, feito: ev.feito, total: ev.total, gasto: ev.gasto, etapa: 'lendo' });
      const recente = ev.ts && Date.now() - new Date(ev.ts).getTime() < 30000;
      if (ev.tipo === 'grupo_fim') { r.etapa = 'salvando'; if (recente) r.planilhasAte = Date.now() + 7000; }
      else if (ev.tipo === 'execucao_fim') {
        r.fim = { resultado: ev.resultado, planilhas: ev.planilhas || 0, falhas: ev.falhas || 0, motivo: ev.motivo }; r.gasto = ev.gasto ?? r.gasto;
        if (recente && ev.resultado !== 'parou') r.planilhasAte = Date.now() + 9000;
      }
      return { jrun: r };
    });
    setTimeout(() => this.jfalar(), 0);
  }
  jfalar() {
    const s = this.state, r = s.jrun, srv = s.jsrv;
    let txt = Component.JIDLE;
    if (srv && !srv.configurado) txt += ' Ainda não estou instalado neste servidor (falta JARVIS_PASTA).';
    else if (r && !r.fim && srv && srv.rodando) {
      const pre = r.teste ? 'Teste · ' : '';
      txt = r.etapa === 'entrando' ? pre + 'Entrando no VIOS, só para ler…'
        : r.etapa === 'salvando' ? pre + 'Grupo ' + r.grupo + ' de ' + r.grupos + ' lido: salvando a planilha.'
        : pre + 'Grupo ' + r.grupo + ' de ' + r.grupos + ': processo ' + r.feito + ' de ' + r.total + ' · gasto ' + this.jdinheiro(r.gasto) + '.';
    } else if (srv && srv.rodando && !(r && r.fim)) txt = 'Começando o relatório…';
    else if (r && r.fim) {
      const f = r.fim, g = ' Gasto com a IA: ' + this.jdinheiro(r.gasto) + '.';
      txt = f.resultado === 'concluido' ? (r.teste ? 'Teste concluído (2 processos por grupo): ' + f.planilhas + ' planilha(s) na pasta teste.' : 'Pronto! ' + f.planilhas + ' planilha(s) do mês gerada(s). Baixe em "Planilhas".') + g
        : f.resultado === 'com_falha' ? 'Terminei, mas ' + f.falhas + ' grupo(s) tiveram falha (veja o log do Jarvis). ' + f.planilhas + ' planilha(s) salva(s).' + g
        : 'Parei por um erro. Veja logs/execucoes_vila.log na pasta do Jarvis.' + g;
    } else if (r && srv && !srv.rodando) txt = 'A última execução foi interrompida antes do fim. Pode gerar de novo.';
    if (txt !== s.jtext) this.setState({ jtext: txt, jtyped: 0 });
  }
  async jstatusTick() {
    try {
      const r = await fetch('/jarvis/status', { credentials: 'same-origin' });
      if (r.ok) { this.setState({ jsrv: await r.json() }); setTimeout(() => this.jfalar(), 0); }
    } catch (e) { /* sem conexão: o topo já mostra pelo /eventos */ }
  }
  jbotoes() {
    const srv = this.state.jsrv, out = { a: null, p: null };
    if (this.fonte() !== 'servidor' || !srv || !srv.configurado) return out;
    const abrir = () => window.open('/jarvis', '_blank');  // escolher os grupos e baixar as planilhas
    out.p = { label: 'Planilhas', fn: abrir };
    if (!srv.rodando) out.a = { label: 'Escolher grupos e gerar', fn: abrir };
    return out;
  }
  jVals() {
    const s = this.state, txt = s.jtext || '', srv = s.jsrv, r = s.jrun, B = this.jbotoes(), off = s.conn === 'offline';
    const rodando = !!(srv && srv.rodando);
    const out = { hudStatus: 'Jarvis · ' + (rodando ? 'Trabalhando' : 'Ocioso'), dotColor: off ? '#5a5f67' : '#7fe3ff',
      hudStep: off && this.fonte() === 'servidor' ? 'Sem conexão' : rodando && r && r.grupo ? 'Grupo ' + r.grupo + '/' + r.grupos : 'Relatório mensal', speaker: 'Jarvis',
      dialogShown: txt.slice(0, s.jtyped || 0), moreOpacity: (s.jtyped || 0) >= txt.length ? 1 : 0 };
    if (this.fonte() === 'servidor') Object.assign(out, {
      showAction: !!B.a, actionLabel: B.a ? B.a.label : '',
      showAction2: false,
      showPainel: !!B.p, painelLabel: B.p ? B.p.label : '', painel: () => B.p && B.p.fn() });
    return out;
  }
  patrol() {""")
DESENHO = {
    # armadura carmesim e dourada com propulsores (o fogo pisca)
    "propulsor": r"""      const pisca = f % 220 < 5, chama = (f >> 2) % 2;
      const JP = { R: '#b3202f', H: '#e0525c', S: '#6e1019', G: '#c99a3a', Y: '#f0c46a', K: '#1d1e21', E: pisca ? '#1d1e21' : '#7fe3ff', B: pisca ? '#1d1e21' : '#e6fbff',
        C: '#7fe3ff', W: '#ffffff', F: chama ? '#ffd23f' : '#ff7a1a', Q: chama ? '#ff7a1a' : null };
      Component.JSPR.forEach((row, y) => row.split('').forEach((ch, x) => { if (ch !== '.' && JP[ch]) R(j.x + x, j.y + jb + y - 2, 1, 1, JP[ch]); }));""",
    # núcleo de IA: esfera em espiral girando, dois anéis tracejados e o centro pulsando
    "nucleo": r"""      const cx = j.x + 8, cy = j.y + jb + 4, rot = ff * 0.025, rr = 6.5 + 0.4 * Math.sin(ff * 0.06), ct = Math.cos(0.42), sn = Math.sin(0.42);
      const halo = c.createRadialGradient(cx, cy, 0, cx, cy, rr * 1.9);
      halo.addColorStop(0, 'rgba(120,200,255,.35)'); halo.addColorStop(1, 'rgba(30,90,160,0)');
      c.fillStyle = halo; c.fillRect(cx - rr * 2, cy - rr * 2, rr * 4, rr * 4);
      for (let i = 0; i < 70; i++) {
        const t0 = i / 69, ph = Math.acos(1 - 2 * t0), th = t0 * 10 * Math.PI * 2;
        const x = rr * Math.sin(ph) * Math.cos(th), y = rr * Math.cos(ph), z = rr * Math.sin(ph) * Math.sin(th);
        const x1 = x * Math.cos(rot) - z * Math.sin(rot), z1 = x * Math.sin(rot) + z * Math.cos(rot), y2 = y * ct - z1 * sn, z2 = y * sn + z1 * ct;
        R(cx + x1, cy + y2, 1, 1, z2 < 0 ? ((i + (ff >> 3)) % 7 ? '#5ab4ff' : '#e6fbff') : '#1f4f86');
      }
      [[1.45, 0.32, 0.03, '#7fc8ff'], [1.2, -0.5, -0.045, '#cfeaff']].forEach(([k, inc, vel, cor]) => {
        for (let s = 0; s < 40; s++) {
          if ((s >> 2) % 2) continue;
          const a = s / 40 * Math.PI * 2 + ff * vel, x = rr * k * Math.cos(a), z = rr * k * Math.sin(a);
          R(cx + x, cy + z * inc, 1, 1, z < 0 ? cor : '#2f6fae');
        }
      });
      const p = 0.85 + 0.15 * Math.sin(ff * 0.06) + (fase ? 0.15 : 0);
      const nucleo = c.createRadialGradient(cx, cy, 0, cx, cy, 4 * p);
      nucleo.addColorStop(0, 'rgba(255,255,255,1)'); nucleo.addColorStop(0.35, 'rgba(170,235,255,.85)'); nucleo.addColorStop(1, 'rgba(60,150,255,0)');
      c.fillStyle = nucleo; c.fillRect(cx - 5, cy - 5, 10, 10);
      R(cx - 1, cy - 1, 2, 2, '#ffffff');""",
}
MASCOTE = sys.argv[2] if len(sys.argv) > 2 else "nucleo"
JCENAS = r"""
      const ox = j.x + 8, oy = j.y + jb + 4, run = this.state.jrun || {};
      if (fase === 'torre') {
        // Torre VIOS: entrando no VIOS. Sinais sobem do núcleo até o topo da torre e ondas saem dela
        const topo = [960 + TX + 16, TY + 1];
        for (let i = 0; i < 3; i++) { const k = ((ff + i * 14) % 42) / 42; R(ox + (topo[0] - ox) * k, oy + (topo[1] - oy) * k - Math.sin(k * Math.PI) * 6, 2, 2, i % 2 ? '#e6fbff' : '#7fe3ff'); }
        for (let w = 0; w < 2; w++) {
          const raio = ((ff + w * 24) % 48) / 48 * 14;
          for (let a = 0; a < 12; a++) { const ang = Math.PI * (1.1 + a / 11 * 0.8); R(topo[0] + Math.cos(ang) * raio, topo[1] + Math.sin(ang) * raio, 1, 1, raio < 9 ? '#7fe3ff' : '#2f6fae'); }
        }
      } else if (fase === 'leitura') {
        // Leitura dos processos: a porta acende e as folhas de cada processo saem girando para dentro do núcleo
        const px = 960 + 9 * 16, py = 16 + 48 - 16;
        R(px + 3, py, 10, 15, (ff >> 3) % 2 ? 'rgba(127,227,255,.35)' : 'rgba(127,227,255,.2)');
        for (let i = 0; i < 4; i++) {
          const k = ((ff + i * 11) % 44) / 44, ang = k * Math.PI * 3, raio = (1 - k) * 5;
          const x = px + 6 + (ox - px - 6) * k + Math.cos(ang) * raio, y = py + 4 + (oy - py - 4) * k + Math.sin(ang) * raio;
          R(x - 2, y - 2, 4, k > 0.8 ? 3 : 5, '#f6f1e6');  // a folha encolhe ao entrar no núcleo
          if (k < 0.8) { R(x - 1, y - 1, 2, 1, '#9aa0a8'); R(x - 1, y + 1, 2, 1, '#9aa0a8'); }
        }
        if (run.total) { const prog = Math.min(1, (run.feito || 0) / run.total); R(ox - 9, oy - 14, 18, 4, '#201f1d'); R(ox - 8, oy - 13, 16, 2, '#1a4f5c'); R(ox - 8, oy - 13, Math.round(16 * prog), 2, '#7fe3ff'); }
      } else if (fase === 'planilhas') {
        // Planilhas: o núcleo manda os dados para a tela e a planilha vai sendo preenchida, célula por célula
        const tx = 960 + 14 * 16 + 35, ty = 16 + 19, pronto = !!run.fim;
        R(tx, ty, 26, 14, '#0d1a26');
        for (let col = 0; col < 3; col++) R(tx + 1 + col * 8, ty + 1, 7, 2, '#c99a3a');
        const n = pronto ? 12 : Math.floor(ff / 6) % 13;
        for (let c2 = 0; c2 < 12; c2++) { const lin = Math.floor(c2 / 3), col = c2 % 3; R(tx + 1 + col * 8, ty + 4 + lin * 2.5, 7, 2, c2 < n ? (c2 === n - 1 && !pronto ? '#e6fbff' : '#3fb8c8') : '#1f2d3a'); }
        if (pronto) { const vx = tx + 9, vy = ty + 5; [[0, 2], [1, 3], [2, 4], [3, 3], [4, 2], [5, 1], [6, 0]].forEach(([dx, dy]) => R(vx + dx, vy + dy, 2, 2, '#3fd17a')); }
        else for (let i = 0; i < 3; i++) { const k = ((ff + i * 12) % 36) / 36; R(ox + (tx + 13 - ox) * k, oy + (ty + 14 - oy) * k - Math.sin(k * Math.PI) * 5, 2, 2, '#7fe3ff'); }
      }"""
assert MASCOTE in DESENHO, f"mascote '{MASCOTE}' não existe: {', '.join(DESENHO)}"
troca("    const eyes = {", r"""    { const j = this.j, voando = j.path.length > 0 && j.wait <= 0, jb = voando ? -2 : (f >> 4) % 2 ? -3 : -2;
      const alvo = this.jalvo(), fase = alvo && !j.path.length && Math.round(j.x / 16) === alvo[0] && Math.round(j.y / 16) === alvo[1] ? this.jfase() : null;
      const ff = this.jff = (this.jff || 0) + (fase ? 3 : 1);  // relógio do Jarvis: 3x mais rápido trabalhando
      R(960 + 63, 4, 3, 3, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      R(960 + TX + 15, TY, 2, 2, fase === 'torre' ? ((f >> 2) % 2 ? '#e6fbff' : '#7fe3ff') : (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      c.fillStyle = 'rgba(0,0,0,.22)'; c.fillRect(Math.round(j.x + 4), Math.round(j.y + 15), 8, 2);
""" + DESENHO[MASCOTE] + JCENAS + """ }
    const eyes = {""")

# 4) painel da Vila 04
troca("    if (vi === 1) Object.assign(out, this.zVals());", "    if (vi === 1) Object.assign(out, this.zVals());\n    if (vi === 3) Object.assign(out, this.jVals());")

# nomes na tela da vila atual (o texto do Jarvis foi escrito com os antigos)
t = t.replace("página do Ultron", "página do Sam")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Jarvis na Vila 04")
