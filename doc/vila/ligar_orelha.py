"""Liga a Vila 05 ao Orelha (bot que só lê o VIOS e monta o relatório do dia, pasta orelha/).

- a vila passa de 3 para 5 vilas: a Vila 04 fica vaga (apagada, com a placa "Aguardando um bot")
  e a Vila 05 acende com as placas do Orelha: Doca 01 · Orelha, Calendário, Intimações, Torre VIOS,
  Relatório e Planilhas (com a pilha do Albi e as caixas verde, âmbar e cinza);
- o mascote é o de orelha/mascote/ficha.html (cão-robô 20×14 com chapéu fedora: BASE, PATCH,
  STAND, HAT, HATPAL e PAL copiados de lá), que anda pela Vila 05 conforme os eventos reais
  (bot: "orelha"): execucao_iniciada → fase (entrando_vios na Torre VIOS, lendo_calendario no
  Calendário, lendo_intimacoes nas Intimações, lendo_processos na Torre VIOS, lendo_planilhas
  na pilha das Planilhas, gerando_relatorio no Relatório) → achado (latido "!" quando é grave)
  → planilha (vai à Torre VIOS e solta a folha na caixa verde = ja_tem, âmbar = novo ou
  cinza = nao_achou) → execucao_fim (volta à doca);
- o painel "Relatório do dia · Orelha" mostra uma linha por função, só com contagens (os eventos
  não trazem texto de cliente, de processo nem nome de pessoa);
- parado, ele passeia e faz as animações de espera da ficha (língua de fora, rabo, duas patas,
  latir "AU AU", atrás do rabo, cochilar). No modo simulado (site publicado) o botão
  "Simular execução" mostra uma execução de exemplo, sem servidor.

uso: python3 doc/vila/ligar_orelha.py bot/vila/vila.html  (edita no lugar; rodar depois de
     ligar_zangao.py, ligar_albi.py, ligar_bumblebee.py, ligar_vila01_campo.py e ligar_vila03_arena.py,
     e antes do ligar_jarvis.py e do ligar_vila05_parque.py, que troca o fundo da Vila 05 pelo parque; rodar de novo não muda nada)"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "fhandle(ev)" in t:
    sys.exit("a vila já está com o Orelha")
if "zhandle(ev)" not in t or "get('vila')" not in t:
    sys.exit("rode antes o doc/vila/ligar_zangao.py (o Orelha usa o que ele acrescenta)")
if "ahandle(ev)" not in t or "sem_pedido" not in t:
    sys.exit("rode antes o doc/vila/ligar_albi.py (todas as etapas; o Orelha usa o que ele acrescenta)")
if "static NV = 3;" not in t:
    sys.exit("esperava a vila com 3 vilas (Ultron, Zangão, Albi); com outra quantidade, ajuste este script")

# Este patch foi escrito com os nomes antigos ("Ultron", "Zangão"). Depois dele a vila passou a mostrar
# "Sam" e "Bumblebee" (ligar_vila01_campo.py e ligar_bumblebee.py). Volta aos nomes antigos para os
# trechos baterem e, no fim, põe os novos de novo (inclusive no que o Orelha acrescenta).
import re
NOVOS = "Sam" in t or "Bumblebee" in t
if NOVOS:
    t = t.replace("página do Sam", "página Ultron")
    t = re.sub(r"\bSam\b", "Ultron", t)
    t = t.replace("Bumblebee", "Zangão")


def troca(velho, novo, vezes=1):
    global t
    assert t.count(velho) == vezes, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) 5 vilas: largura do mundo e do canvas (a 04 fica vaga, a 05 é do Orelha)
troca("width:300%;height:100%;transform:{{ worldTransform }}", "width:500%;height:100%;transform:{{ worldTransform }}")
troca('<canvas ref="{{ canvasRef }}" width="960" height="224"', '<canvas ref="{{ canvasRef }}" width="1600" height="224"')
troca("static NV = 3;", "static NV = 5;")

# 2) estado do Orelha
troca("atotal: null, avalidos: null };",
      "atotal: null, avalidos: null, fphase: 'idle', fstatus: 'Ocioso', ftext: '', ftyped: 0, ffun: [], "
      "fplan: { ja_tem: 0, novo: 0, nao_achou: 0 }, fresult: null, fsim: false, ffase: null, fpanelOpen: false, fts: null };")

# 3) o Orelha (começa na doca da Vila 05), filas e a fala inicial
troca("this.aseq = []; this.acur = null; this.aevq = [];",
      "this.aseq = []; this.acur = null; this.aevq = [];\n"
      "    this.fa = { x: 83 * 16, y: 64, dir: 'right', path: [], step: 0, wait: 180, i: 0, j: 0, bubble: null, carry: false, fx: null, progress: null, pose: null, idle: null, alvo: null };\n"
      "    this.fseq = []; this.fcur = null; this.fevq = []; this.fmock = [];")
troca("    this.asay(this.fonte() === 'servidor' ? Component.AIDLE_REAL : Component.AIDLE);\n",
      "    this.asay(this.fonte() === 'servidor' ? Component.AIDLE_REAL : Component.AIDLE);\n"
      "    this.fsay(this.fonte() === 'servidor' ? Component.FIDLE_REAL : Component.FIDLE);\n")

# 4) a Vila 05 acende (prédios, janelas, canos e luzes); a 04 continua apagada
troca("const O = v * 320, on = v <= 2;", "const O = v * 320, on = v <= 2 || v === 4;")
troca("tx < 60 ? '#f0c46a' : '#6b5a3a'", "(tx < 60 || tx >= 80) ? '#f0c46a' : '#6b5a3a'")
troca("const on = tx < 60, a = on", "const on = tx < 60 || tx >= 80, a = on")
troca("for (let v = 3; v < Component.NV; v++) if ((f >> 6) % 2)", "for (let v = 3; v < Component.NV; v++) if (v !== 4 && (f >> 6) % 2)")

# 5) placas, nome da vila e o aviso "Aguardando um bot" (só na 04)
troca("on = v <= 2, mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : 'Doca 01 · Albi';",
      "on = v <= 2 || v === 4, mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : v === 2 ? 'Doca 01 · Albi' : v === 4 ? 'Doca 01 · Orelha' : 'Doca 01 · vaga';")
troca("v === 1 ? 'Filtro previdenciário' : 'Receptor TXT', on)",
      "v === 1 ? 'Filtro previdenciário' : v === 2 ? 'Receptor TXT' : v === 4 ? 'Calendário' : 'Receptor', on)")
troca("v === 1 ? 'Captura de dados' : 'Conferência', on)",
      "v === 1 ? 'Captura de dados' : v === 2 ? 'Conferência' : v === 4 ? 'Intimações' : 'Oficina', on)")
troca("v <= 1 ? 'Torre VIOS' : 'Torre Sonar', on)", "v <= 1 || v === 4 ? 'Torre VIOS' : v === 2 ? 'Torre Sonar' : 'Torre de destino', on)")
troca("'Doca 02 · livre', on)", "v === 4 ? 'Relatório' : 'Doca 02 · livre', on)")
troca("P(o + 12.5, 6.5, 'Doca 03 · livre')", "P(o + 12.5, 6.5, v === 4 ? 'Planilhas' : 'Doca 03 · livre')")
troca("for (let v = 3; v < NV; v++) signs.push(", "for (let v = 3; v < NV; v++) if (v !== 4) signs.push(")
troca("const vNames = ['01 · Ultron', '02 · Zangão', '03 · Albi'];",
      "const vNames = ['01 · Ultron', '02 · Zangão', '03 · Albi', '04 · vaga', '05 · Orelha'];")
troca("    if (vi === 2) Object.assign(out, this.aVals());\n",
      "    if (vi === 2) Object.assign(out, this.aVals());\n    if (vi === 4) Object.assign(out, this.fVals());\n")

# 6) botão "A" na Vila 05: no simulado, simula uma execução; senão abre/fecha o painel
troca("  action() {\n",
      "  action() {\n"
      "    if (this.state.village === 4) {\n"
      "      if (this.fonte() === 'simulado' && this.flivre()) this.femitMock();\n"
      "      else if (this.state.ffun.length) this.setState(st => ({ fpanelOpen: !st.fpanelOpen }));\n"
      "      return;\n"
      "    }\n")

# 7) eventos: separa os do Orelha (e, ao abrir, anima só os dos últimos 30 s)
troca("        const ab = evs.filter(e => e.bot === 'albi');\n",
      "        const ab = evs.filter(e => e.bot === 'albi');\n        const fr = evs.filter(e => e.bot === 'orelha');\n")
troca("const iu = corte(ul), iz = corte(zg), ia = corte(ab);", "const iu = corte(ul), iz = corte(zg), ia = corte(ab), ifr = corte(fr);")
troca("this.aLoadHistory(ab.slice(0, ia));\n", "this.aLoadHistory(ab.slice(0, ia)); this.fLoadHistory(fr.slice(0, ifr));\n")
troca("          this.aevq.push.apply(this.aevq, ab.slice(ia));\n",
      "          this.aevq.push.apply(this.aevq, ab.slice(ia));\n          this.fevq.push.apply(this.fevq, fr.slice(ifr));\n")
troca("this.aevq.push.apply(this.aevq, ab); }", "this.aevq.push.apply(this.aevq, ab); this.fevq.push.apply(this.fevq, fr); }")

# 8) laço: o Orelha anda, digita a fala e alcança o estado atual com fila grande / aba escondida
troca("    if (this.acur) this.astep(); else if (this.aevq.length) this.ahandle(this.aevq.shift()); else this.apatrol();\n",
      "    if (this.acur) this.astep(); else if (this.aevq.length) this.ahandle(this.aevq.shift()); else this.apatrol();\n"
      "    if (!this.fcur && !this.fevq.length && this.fmock.length) this.fevq.push(this.fmock.shift());\n"
      "    if (this.fcur) this.fstep(); else if (this.fevq.length) this.fhandle(this.fevq.shift()); else this.fpatrol();\n"
      "    if (this.state.ftyped < this.state.ftext.length) this.setState(s => ({ ftyped: s.ftyped + 1 }));\n")
troca("    if (this.aevq.length > 30) this.aalcancar();\n",
      "    if (this.aevq.length > 30) this.aalcancar();\n    if (this.fevq.length > 30) this.falcancar();\n")
troca("if (this.aevq.length > 2) this.aalcancar(); } };",
      "if (this.aevq.length > 2) this.aalcancar(); if (this.fevq.length > 2) this.falcancar(); } };")

# 9) desenho da Vila 05 e do Orelha (antes do Ultron, que é desenhado por último)
DRAW = r"""    {
      const F = this.fa, O5 = 1280, fm = F.path.length > 0 && F.wait <= 0, ffx = F.fx, T = f >> 3, s5 = this.state;
      const P5 = Component.FPAL, teal = '#d39a5c', ct = this.fcur ? this.fcur.t : 0;
      // luz da doca e da torre (pisca rápido enquanto lê o VIOS)
      R(O5 + 63, 4, 3, 3, (f >> 5) % 2 ? teal : '#2c6c66');
      R(O5 + TX + 15, TY, 2, 2, ffx === 'vios' ? ((f >> 2) % 2 ? '#7fe7ff' : '#e6f9ff') : ((f >> 5) % 2 ? teal : '#2c6c66'));
      // Calendário: as janelas viram folhas de calendário e um dia acende por vez
      if (ffx === 'cal') {
        [132, 164, 180].forEach((wx, j) => {
          const x = O5 + wx; R(x, 36, 8, 7, '#f6f1e6'); R(x, 36, 8, 2, '#c81e14');
          for (let k = 0; k < 6; k++) R(x + 1 + (k % 3) * 2, 39 + Math.floor(k / 3) * 2, 1, 1, (Math.floor(ct / 8) + j) % 6 === k ? teal : '#9aa0a8');
        });
        for (let i = 0; i < 4; i++) R(O5 + 148 + ((ct * 3 + i * 11) % 9), 52 + ((ct + i * 5) % 8), 1, 1, i % 2 ? teal : '#ffffff');
      }
      // Intimações: a tela rola enquanto ele lê; depois fica com o ponto vermelho (grave) ou verde
      const rI = (s5.ffun || []).find(x => x.k === 'intimacoes');
      if (ffx === 'int') for (let i = 0; i < 5; i++) R(O5 + SX + 3, SY + 3 + ((i * 3 + (f >> 2)) % 11), 4 + ((i * 7 + (f >> 3)) % 16), 1, i % 3 === 0 ? teal : '#d4d8de');
      else if (rI && rI.st === 'feito') {
        for (let i = 0; i < 4; i++) R(O5 + SX + 3, SY + 3 + i * 3, 14 + (i * 5) % 7, 1, '#9aa0a8');
        R(O5 + SX + 21, SY + 3, 2, 2, rI.g ? '#ff5a3c' : '#3fd17a');
      } else if ((f >> 6) % 2) R(O5 + SX + 3, SY + 3, 2, 1, '#5a616b');
      // Planilhas: a pilha do Albi em cima e as caixas embaixo (verde = já tem, âmbar = novo, cinza = não achou)
      const PL = s5.fplan || {}, BX = { ja_tem: [O5 + 180, 114, '#5fc48a', '#2e7a4f'], novo: [O5 + 194, 114, '#f0a64b', '#9a5f1c'], nao_achou: [O5 + 208, 114, '#a9a49b', '#5a5f67'] };
      const folha = (x, y) => { R(x, y, 4, 5, '#f4ead2'); R(x, y, 4, 1, '#2f7d4f'); R(x + 1, y + 2, 2, 1, '#b9ae96'); };
      folha(O5 + 183, 87); folha(O5 + 188, 87); folha(O5 + 185, 84);
      Object.keys(BX).forEach(k => {
        const [x, y, c1, c2] = BX[k];
        R(x, y, 10, 7, c2); R(x + 1, y + 1, 8, 5, c1); R(x + 1, y + 3, 8, 1, c2);
        for (let i = 0; i < Math.min(3, PL[k] || 0); i++) R(x + 3, y - 1 - i, 4, 1, '#f4ead2');
      });
      // Relatório: a folha sai aos poucos e fica lá depois de pronta
      if (ffx === 'rel') { const h = Math.max(1, Math.round(9 * (F.progress || 0))); R(O5 + 84, 113, 7, h, '#201f1d'); R(O5 + 85, 114, 5, Math.max(0, h - 2), '#f6f1e6'); }
      else if (s5.fphase === 'done' && !(s5.fresult && s5.fresult.resultado === 'parou')) { paper(O5 + 84, 113); R(O5 + 86, 115, 3, 1, teal); }
      // o Orelha (desenho da ficha: 20×14 olhando para a direita, chapéu 9×4 por cima)
      const flip0 = F.dir === 'left', it = F.idle ? Math.floor(F.idle.t / 7) : 0, idl = !fm && F.idle && !F.pose && !ffx ? F.idle.k : null;
      let patches = [], flip = flip0, dx = 0, dy = 0, blink = !fm && (T % 40) < 2, glow = (T >> 2) % 2 === 0, hatY = -3, stand = false, fala = null, zz = false;
      if (fm) { if (Math.floor(F.step / 4) % 2) patches.push('legsB'); if (Math.floor(F.step / 6) % 2) patches.push('tailB'); }
      else if (F.pose === 'sad') { patches.push('sad'); glow = false; }
      else if (F.pose === 'jatem') { if (T % 2) patches.push('tailB'); glow = true; }
      else if (F.pose === 'bark') { if (Math.floor(T / 3) % 2) patches.push('bark'); }
      else if (['cal', 'int', 'plan', 'rel'].includes(ffx)) { patches.push('look'); if (Math.floor(T / 10) % 2) patches.push('tailB'); }
      else if (idl === 'lingua') { patches.push(Math.floor(it / 3) % 2 ? 'tongue' : 'tongue2'); if (Math.floor(it / 8) % 2) patches.push('tailB'); }
      else if (idl === 'rabo') { if (Math.floor(it / 2) % 2) patches.push('tailB'); glow = true; blink = false; }
      else if (idl === 'duaspatas') stand = true;
      else if (idl === 'latir') { const q = it % 24; if (q < 4 || (q >= 8 && q < 12)) patches.push('bark'); if (q < 20) fala = q < 8 ? 'AU' : 'AU AU'; blink = false; }
      else if (idl === 'rodar') { const q = Math.floor(it / 3) % 2; patches.push(q ? 'legsB' : 'tailB'); flip = q === 1 ? !flip0 : flip0; dx = q; dy = -q; blink = false; }
      else if (idl === 'cochilar') { patches.push('sleep'); dy = 3; hatY = -1; blink = true; glow = false; zz = true; }
      else if (Math.floor(T / 8) % 2) patches.push('tailB');
      const L = Math.round(F.x - 2), top = Math.round(F.y);
      c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(L + 3, Math.round(F.y + 14), 15, 2);
      const pix = (rws, ox, oy, w, fl) => rws.forEach((row, j) => row.forEach((ch, i) => {
        let col = P5[ch]; if (!col) return;
        if (blink && (ch === 'O' || ch === 'K')) col = P5.M;
        if (ch === 'G') col = glow ? P5.G : '#c9a24a';
        R(ox + (fl ? w - 1 - i : i), oy + j, 1, 1, col);
      }));
      const chapeu = (ox, oy, hx, hy, w, fl) => Component.FHAT.forEach((row, j) => row.split('').forEach((ch, i) => {
        const col = Component.FHATPAL[ch]; if (!col) return; const cx = hx + i; R(ox + (fl ? w - 1 - cx : cx), oy + hy + j, 1, 1, col);
      }));
      let ox = L + dx, oy = top + dy;
      if (stand) {
        const hop = Math.floor(it / 4) % 2; ox = L + 3; oy = top - 5 - hop;
        pix(Component.fmerge(Component.FSTAND, Component.FSPATCH, Math.floor(it / 3) % 2 ? ['tailB'] : []), ox, oy, 14, flip0);
        chapeu(ox, oy, 5, -3, 14, flip0);
      } else {
        pix(Component.fmerge(Component.FBASE, Component.FPATCH, patches), ox, oy, 20, flip);
        chapeu(ox, oy, 10, hatY, 20, flip);
      }
      const boca = flip ? ox - 1 : ox + 17;
      if (F.carry && !stand) { folha(boca, oy + 3); if (ffx === 'plan') for (let k = 0; k < 10; k++) R(boca + 1 + (O5 + 186 - boca - 1) * k / 10, oy + 4 + (89 - oy - 4) * k / 10, 1, 1, 'rgba(127,231,255,.5)'); }
      if (ffx === 'drop' && F.alvo && BX[F.alvo]) {
        const [bx, by] = BX[F.alvo], k = F.progress || 0;
        R(boca + (bx + 3 - boca) * k, oy + 4 + (by - 2 - oy - 4) * k - Math.sin(k * Math.PI) * 8, 3, 3, '#f4ead2');
      }
      if (ffx === 'vios' && this.fcur) { const k = (ct % 40) / 40, TXF = O5 + TX; R(TXF + 8 + (F.x + 12 - TXF - 8) * k, F.y + 4, 3, 3, '#7fe7ff'); }
      // balões da ficha: "!" (achado grave / processo novo), visto verde (já tem) e "?" (não achou / parou)
      if (F.bubble) {
        const x = flip ? ox - 4 : ox + 17, y = oy - 8;
        R(x, y, 7, 8, '#201f1d'); R(x + 1, y + 1, 5, 6, '#ffffff'); R(x + 1, y + 8, 1, 1, '#201f1d');
        if (F.bubble === '!') { R(x + 3, y + 2, 1, 3, '#c81e14'); R(x + 3, y + 6, 1, 1, '#c81e14'); }
        if (F.bubble === 'ok') [[1, 4], [2, 5], [3, 4], [4, 3], [5, 2]].forEach(([a, b]) => R(x + a, y + b, 1, 1, '#2e9b5a'));
        if (F.bubble === '?') [[2, 2], [3, 2], [4, 2], [4, 3], [3, 4], [3, 6]].forEach(([a, b]) => R(x + a, y + b, 1, 1, '#6d6a63'));
      }
      const letras = (x, y, s, col) => s.split('').forEach(ch => {
        if (ch === ' ') { x += 2; return; }
        const g = Component.FGLYPH[ch]; g.forEach((r, j) => r.split('').forEach((q, i) => { if (q === 'X') R(x + i, y + j, 1, 1, col); })); x += g[0].length + 1;
      });
      if (fala) {
        const w = fala.split('').reduce((a, ch) => a + (ch === ' ' ? 2 : Component.FGLYPH[ch][0].length + 1), -1) + 4, x = flip ? ox - w - 1 : ox + 19, y = oy - 1;
        R(x, y, w, 9, '#201f1d'); R(x + 1, y + 1, w - 2, 7, '#ffffff');
        if (flip) { R(x + w, y + 5, 1, 1, '#201f1d'); R(x + w + 1, y + 6, 1, 1, '#201f1d'); } else { R(x - 1, y + 5, 1, 1, '#201f1d'); R(x - 2, y + 6, 1, 1, '#201f1d'); }
        letras(x + 2, y + 2, fala, '#201f1d');
      }
      if (zz) [0, 1, 2].forEach(i => { const k = ((T + i * 8) % 24) / 24; letras(ox + 21 + Math.round(k * 8), oy + 2 - Math.round(k * 12), 'Z', 'rgba(200,239,233,' + (1 - k).toFixed(2) + ')'); });
      if (F.progress != null && ffx !== 'drop') { R(F.x, oy - 10, 16, 5, '#201f1d'); R(F.x + 1, oy - 9, 14, 3, '#f6f1e6'); R(F.x + 1, oy - 9, Math.round(14 * F.progress), 3, teal); }
    }
"""
troca("    const eyes = { vermelho:", DRAW + "    const eyes = { vermelho:")

# 10) dados do desenho, falas, eventos e painel do Orelha
FCODE = r"""
  static FIDLE = 'Sou o Orelha, o cão leitor. Só leio o VIOS: agenda de hoje e amanhã, tarefas atrasadas da equipe, intimações esquecidas, processos parados e as planilhas que o Albi traz. No fim entrego o relatório do dia. Aperte "Simular execução" para me ver trabalhando.';
  static FIDLE_REAL = 'Sou o Orelha. Entro no VIOS só para ler e monto o relatório do dia (agenda, prazos, intimações, processos parados e planilhas do Albi). Quando eu rodar, você me vê farejando aqui.';
  // desenho copiado de orelha/mascote/ficha.html (BASE, PATCH, STAND, SPATCH, HAT, HATPAL, PAL e as letras do balão)
  static FBASE = [
    '............PP......', '..........SLLLLS....', 'c.........SOOOPCc...', 'P.........SOKOCWWN..', '.P........SOOOCWWd..', '.P.........dCCCCd...', '..P.LLLLLLLCCCCd....', '..PPPPPPPPPPCCCd....', '..PPPPPPPPPPCCd.....', '..PPPPPPPPPCCCd.....', '..dddddddddddd......', '...Cd......Cd.......', '...Cd......Cd.......', '..ddd.....ddd.......'];
  static FPATCH = {
    legsB: { 11: '...Cd......Cd.......', 12: '....Cd....Cd........', 13: '...ddd...ddd........' },
    tailB: { 2: '..c.......SOOOPCc...', 3: '..P.......SOKOCWWN..', 4: '..P.......SOOOCWWd..', 5: '..P........dCCCCd...', 6: '...PLLLLLLLCCCCd....' },
    look: { 3: 'P.........SOOOCWWN..', 4: '.P........SOOKCWWd..' },
    bark: { 4: '.P........SOOOCWW...', 5: '.P.........dCCCCdd..' },
    tongue: { 5: '.P.........dCCCTT...', 6: '..P.LLLLLLLCCCCdT...' },
    tongue2: { 5: '.P.........dCCCTT...' },
    sleep: { 11: '....................', 12: '....................', 13: '....................' },
    sad: { 0: '....................', 11: '..ddd......Cd.......', 12: '..ddd......Cd.......', 13: '..ddd.....ddd.......' }
  };
  static FSTAND = [
    '.......PP.....', '.....SLLLLS...', '.....SOOOPCc..', '.....SOKOCWWN.', '.....SOOOCWWd.', '......dCCCCd..', '.....LLCCCd...', '....PPPCCCdCCC', '....PPPCCCd.cd', '....PPPCCCd...', '....PPPCCCd...', '....PPPPCCd...', 'c...PPPPPPd...', 'P...PPPPPPd...', '.P..dPPPPdd...', '..PPdddddd....', '....Cd..Cd....', '....Cd..Cd....', '...ddd.ddd....'];
  static FSPATCH = { tailB: { 12: '..c.PPPPPPd...', 13: '..P.PPPPPPd...', 14: '..P.dPPPPdd...', 15: '...Pdddddd....' } };
  static FHAT = ['..hHHHH..', '.hHHHHHH.', '.bbbbbbb.', 'BBBBBBBBB'];
  static FHATPAL = { H: '#8b5a2b', h: '#6e4420', b: '#3b2614', B: '#a0693a' };
  static FPAL = { P: '#40362f', S: '#251f1b', C: '#c98a4b', c: '#e2ad72', d: '#8f5a2c', W: '#bdb6aa', O: '#e6f9ff', K: '#0f1f1d', N: '#0d0c0b', T: '#ff7a9a', t: '#d9506f', M: '#40362f', L: '#66584c', D: '#251f1b', A: '#40362f', G: '#40362f' };
  static FGLYPH = { A: ['.X.', 'X.X', 'XXX', 'X.X', 'X.X'], U: ['X.X', 'X.X', 'X.X', 'X.X', 'XXX'], Z: ['XXXX', '..X.', '.X..', 'XXXX'] };
  static FIDLES = ['lingua', 'rabo', 'duaspatas', 'latir', 'rodar', 'cochilar'];
  static FTITULO = { agenda: 'Agenda de hoje e amanhã', prazos: 'Tarefas atrasadas', intimacoes: 'Intimações esquecidas', parados: 'Processos parados', planilhas: 'Planilhas do Albi' };
  static FCURTO = { agenda: 'agenda', prazos: 'prazos', intimacoes: 'intimações', parados: 'processos parados', planilhas: 'planilhas' };
  static FCAND = { lendo_calendario: ['agenda', 'prazos'], lendo_intimacoes: ['intimacoes'], lendo_processos: ['parados'], lendo_planilhas: ['planilhas'] };
  static FMOTIVO = { navegador_falhou: 'o navegador não abriu', login_falhou: 'não consegui entrar no VIOS',
    bloqueio_inativo: 'o bloqueio de envios não ficou ativo (por segurança, não li nada)', config_invalida: 'falta configurar o orelha/.env' };
  static fmerge(base, set, patches) {
    return base.map((row, y) => {
      const r = row.split('');
      patches.forEach(p => { const pr = set[p] && set[p][y]; if (!pr) return; pr.split('').forEach((ch, x) => { if (ch !== row[x]) r[x] = ch; }); });
      return r;
    });
  }
  fsay(t) { this.setState({ ftext: t, ftyped: 0 }); }
  fst(t) { if (this.state.fstatus !== t) this.setState({ fstatus: t }); }
  fpressa() { const q = this.fevq ? this.fevq.length : 0; return q > 40 ? 6 : q > 12 ? 3 : 1; }
  fN(k) { return Math.max(1, Math.round(k / (this.props.speed ?? 1) / this.fpressa())); }
  flivre() { const fp = this.state.fphase; return (fp === 'idle' || fp === 'done') && !this.fcur && !this.fevq.length && !this.fmock.length; }
  frun(steps) { this.fseq = steps; this.fnext(); }
  fnext() {
    const s = this.fseq.shift(), F = this.fa;
    this.fcur = s ? { ...s, t: 0 } : null;
    if (!s) return;
    if (s.type === 'call') { s.fn(); this.fnext(); }
    else if (s.type === 'walk') F.path = this.bfs([Math.round(F.x / 16), Math.round(F.y / 16)], s.to);
    else if (s.type === 'act') { F.fx = s.fx; F.progress = 0; s.start && s.start(); }
  }
  fanda(sp) {
    // um passo no caminho; o desenho é de lado, então só vira para a esquerda ou a direita
    const F = this.fa, [tx, ty] = F.path[0], px = tx * 16, py = ty * 16, dx = px - F.x, dy = py - F.y;
    if (Math.abs(dx) > 0.01) F.dir = dx > 0 ? 'right' : 'left';
    const m = Math.min(sp, Math.abs(dx) + Math.abs(dy));
    if (Math.abs(dx) > 0.01) F.x += Math.sign(dx) * Math.min(m, Math.abs(dx)); else F.y += Math.sign(dy) * Math.min(m, Math.abs(dy));
    F.step += m;
    if (Math.abs(px - F.x) < 0.02 && Math.abs(py - F.y) < 0.02) { F.x = px; F.y = py; F.path.shift(); return true; }
    return false;
  }
  fstep() {
    const c = this.fcur, F = this.fa;
    if (c.type === 'wait') { if (++c.t >= c.n) this.fnext(); return; }
    if (c.type === 'act') { c.t++; F.progress = c.t / c.n; if (c.t >= c.n) { F.progress = null; F.fx = null; c.end && c.end(); this.fnext(); } return; }
    if (!F.path.length) { if (c.face) F.dir = c.face; this.fnext(); return; }
    this.fanda(1.1 * (this.props.speed ?? 1) * this.fpressa());
  }
  fpatrol() {
    // passeio pela Vila 05; em cada parada, uma animação de espera da ficha
    const F = this.fa, O = 80, pts = [[O + 9, 4], [O + 12, 8], [O + 10, 12], [O + 4, 9], [O + 3, 4]];
    if (F.wait > 0) { F.wait--; if (F.idle) { F.idle.t++; if (F.wait <= 0) F.idle = null; } return; }
    if (!F.path.length) { F.path = this.bfs([Math.round(F.x / 16), Math.round(F.y / 16)], pts[F.i++ % pts.length]); if (!F.path.length) F.wait = 120; return; }
    if (this.fanda(0.7 * (this.props.speed ?? 1)) && !F.path.length) {
      const k = Component.FIDLES[F.j++ % Component.FIDLES.length];
      F.idle = { k, t: 0 }; F.wait = k === 'cochilar' ? 420 : 280;
    }
  }
  fqual(fase) {
    // qual função está lendo nesta fase (o calendário serve à agenda e aos prazos, nessa ordem)
    const c = Component.FCAND[fase], L = this.state.ffun;
    if (!c) return null;
    const r = L.find(x => c.includes(x.k) && x.st === 'fila') || L.find(x => c.includes(x.k) && x.st === 'lendo');
    return r ? r.k : c[0];
  }
  ftotais(r) {
    const k = (r && r.contagens) || {}, tot = { g: 0, a: 0 };
    Object.keys(k).forEach(x => { const c = k[x]; if (c && typeof c === 'object') { tot.g += Number(c.graves) || 0; tot.a += Number(c.atencao) || 0; } });
    return tot;
  }
  ferros(r) { return (r && Array.isArray(r.erros) ? r.erros : []).map(x => Component.FCURTO[x] || String(x)); }
  flogTexto(r) {
    if (!r || !r.resultado) return 'sem resultado';
    if (r.resultado === 'parou') return 'parou: ' + (Component.FMOTIVO[r.motivo] || r.motivo || 'erro');
    const t = this.ftotais(r), e = this.ferros(r);
    return 'relatório do dia · ' + t.g + ' grave(s) · ' + t.a + ' de atenção' + (e.length ? ' · erro em ' + e.join(', ') : '');
  }
  ffimTexto(r) {
    if (r.resultado === 'parou') return 'Parei: ' + (Component.FMOTIVO[r.motivo] || r.motivo || 'erro') + '. O relatório saiu assim mesmo, com o motivo em cada seção.';
    const t = this.ftotais(r), e = this.ferros(r);
    return 'Pronto! Relatório do dia gerado: ' + t.g + ' achado(s) grave(s) e ' + t.a + ' ponto(s) de atenção.' + (e.length ? ' Deu erro em: ' + e.join(', ') + ' (o motivo está no relatório).' : '');
  }
  freduce(ev) {
    if (ev.__ffeito) return;
    ev.__ffeito = true;
    this.setState(s => {
      const fts = ev.ts || s.fts;
      if (ev.tipo === 'execucao_iniciada') {
        const fun = (Array.isArray(ev.funcoes) ? ev.funcoes : []).map(k => ({ k: String(k), st: 'fila', g: 0, a: 0, i: 0, tot: null }));
        return { fphase: 'entrando', ffun: fun, fplan: { ja_tem: 0, novo: 0, nao_achou: 0 }, fresult: null, fsim: !!ev.simulado, ffase: null, fpanelOpen: false, fts };
      }
      const L = s.ffun.map(x => ({ ...x }));
      const achar = k => { let r = L.find(x => x.k === k); if (!r) { r = { k, st: 'fila', g: 0, a: 0, i: 0, tot: null }; L.push(r); } return r; };
      const fechar = ate => { for (const r of L) { if (r === ate) break; if (r.st === 'lendo' || r.st === 'fila') r.st = 'feito'; } };
      if (ev.tipo === 'fase') {
        const c = Component.FCAND[ev.fase];
        const fphase = { entrando_vios: 'entrando', lendo_calendario: 'lendo', lendo_intimacoes: 'lendo', lendo_processos: 'lendo', lendo_planilhas: 'planilhas', gerando_relatorio: 'relatorio' }[ev.fase] || s.fphase;
        if (c) { const r = L.find(x => c.includes(x.k) && x.st === 'fila') || L.find(x => c.includes(x.k) && x.st === 'lendo') || achar(c[0]); fechar(r); r.st = 'lendo'; }
        if (ev.fase === 'gerando_relatorio') fechar(null);
        return { fphase: fphase === 'idle' ? 'entrando' : fphase, ffase: ev.fase, ffun: L, fts };
      }
      if (ev.tipo === 'achado') {
        const r = achar(String(ev.funcao || '?')), n = Number(ev.contagem) || 0;
        fechar(r); if (r.st !== 'erro') r.st = 'feito';
        if (ev.nivel === 'grave') r.g = n; else if (ev.nivel === 'atencao') r.a = n; else r.i = n;
        return { ffun: L, fts };
      }
      if (ev.tipo === 'planilha') {
        const P = { ...s.fplan }, k = ['ja_tem', 'novo', 'nao_achou'].includes(ev.resultado) ? ev.resultado : 'nao_achou';
        P[k] = (P[k] || 0) + Math.max(1, Number(ev.contagem) || 1);
        const r = achar('planilhas'); if (r.st === 'fila') { fechar(r); r.st = 'lendo'; }
        return { fplan: P, ffun: L, fts, fphase: s.fphase === 'idle' || s.fphase === 'done' ? s.fphase : 'planilhas' };
      }
      if (ev.tipo === 'execucao_fim') {
        const k = ev.contagens && typeof ev.contagens === 'object' ? ev.contagens : {}, erros = Array.isArray(ev.erros) ? ev.erros : [], parou = ev.resultado === 'parou';
        Object.keys(k).forEach(x => achar(x));
        L.forEach(r => {
          const c = k[r.k];
          if (c && typeof c === 'object') { r.tot = Number(c.total) || 0; r.g = Number(c.graves) || 0; r.a = Number(c.atencao) || 0; r.i = Math.max(0, r.tot - r.g - r.a); }
          r.st = erros.includes(r.k) ? (parou ? 'parou' : 'erro') : (parou && r.st !== 'feito' ? 'parou' : 'feito');
        });
        const res = { resultado: ev.resultado, motivo: ev.motivo, contagens: k, erros };
        return { fphase: 'done', fresult: res, ffun: L, fts,
          log: [{ time: this.ztime(ev), text: 'Orelha · ' + (s.fsim ? 'simulado · ' : '') + this.flogTexto(res) }].concat(s.log).slice(0, 8) };
      }
      return null;
    });
  }
  fhandle(ev) {
    this.fatual = ev;
    const F = this.fa, N = k => this.fN(k), O = 80, HOME = [O + 3, 4], CAL = [O + 9, 4], INT = [O + 15, 4], TOR = [O + 14, 10], PLA = [O + 12, 8], REL = [O + 5, 8], S = [];
    const C = Component.FCURTO;
    F.path = []; F.wait = 0; F.idle = null; F.pose = null; F.bubble = null; F.alvo = null;
    if (ev.tipo === 'execucao_iniciada') {
      const lista = (Array.isArray(ev.funcoes) ? ev.funcoes : []).map(k => C[k] || String(k)).join(', ');
      S.push({ type: 'call', fn: () => { this.freduce(ev); F.carry = false; F.bubble = '!'; this.fst('Começando');
          this.fsay((ev.simulado ? 'Simulado, com dados de exemplo: ' : 'Bom dia! ') + 'vou montar o relatório de hoje' + (lista ? ' (' + lista + ')' : '') + '. Só leio o VIOS, não gravo nada.'); } },
        { type: 'wait', n: N(60) }, { type: 'call', fn: () => { F.bubble = null; } });
    } else if (ev.tipo === 'fase') {
      const k = this.fqual(ev.fase);
      const P = {
        entrando_vios: [TOR, 'vios', 70, 'Entrando no VIOS', 'Entrando no VIOS. O bloqueio de envios fica ligado: daqui em diante eu só leio.'],
        lendo_calendario: [CAL, 'cal', 90, 'Lendo o calendário', k === 'prazos' ? 'Farejando o calendário da equipe: tarefas não concluídas com prazo vencido…'
          : 'Lendo o calendário: audiências, perícias e reuniões de hoje e amanhã, e os feriados da semana…'],
        lendo_intimacoes: [INT, 'int', 90, 'Lendo intimações', 'Procurando intimações sem tarefa lançada (as de ontem e de hoje ficam para o Ultron)…'],
        lendo_processos: [TOR, 'vios', 110, 'Lendo processos', 'Abrindo os processos ativos, um por um, para achar os que estão sem nenhuma tarefa aberta…'],
        lendo_planilhas: [PLA, 'plan', 80, 'Lendo planilhas', 'Pegando as planilhas que o Albi trouxe do Sonar para conferir no VIOS…'],
        gerando_relatorio: [REL, 'rel', 90, 'Escrevendo o relatório', 'Juntando tudo no relatório do dia…'] }[ev.fase];
      if (P) S.push({ type: 'call', fn: () => { if (ev.fase !== 'lendo_planilhas') F.carry = false; this.fst('A caminho'); } },
        { type: 'walk', to: P[0], face: 'right' },
        { type: 'act', n: N(P[2]), fx: P[1], start: () => { this.freduce(ev); this.fst(P[3]); this.fsay(P[4]); }, end: () => { if (ev.fase === 'lendo_planilhas') F.carry = true; } });
      else S.push({ type: 'call', fn: () => { this.freduce(ev); this.fst('Trabalhando'); } });
    } else if (ev.tipo === 'achado') {
      const n = Number(ev.contagem) || 0, nome = C[ev.funcao] || String(ev.funcao || '');
      if (ev.nivel === 'grave') S.push({ type: 'call', fn: () => { this.freduce(ev); F.bubble = '!'; F.pose = 'bark'; this.fst('Achado grave');
          this.fsay('AU AU! ' + n + ' achado(s) grave(s) em ' + nome + '. Vai em destaque no relatório.'); } },
        { type: 'wait', n: N(100) }, { type: 'call', fn: () => { F.bubble = null; F.pose = null; } });
      else S.push({ type: 'call', fn: () => { this.freduce(ev); this.fsay(ev.nivel === 'atencao' ? n + ' ponto(s) de atenção em ' + nome + '.' : n + ' item(ns) em ' + nome + ', sem urgência.'); } },
        { type: 'wait', n: N(ev.nivel === 'atencao' ? 45 : 25) });
    } else if (ev.tipo === 'planilha') {
      const r = ['ja_tem', 'novo', 'nao_achou'].includes(ev.resultado) ? ev.resultado : 'nao_achou';
      const de = ev.total ?? ev.de, q = ev.indice != null ? ' ' + ev.indice + (de ? ' de ' + de : '') : '';
      const oque = Number(ev.contagem) > 1 ? ev.contagem + ' processos da planilha' : 'processo' + q + ' da planilha';
      S.push({ type: 'call', fn: () => { F.carry = true; this.fst('Conferindo' + q); } },
        { type: 'walk', to: TOR, face: 'right' },
        { type: 'act', n: N(40), fx: 'vios', start: () => this.fsay('Procurando no VIOS o ' + oque + '…') },
        { type: 'walk', to: PLA, face: 'right' },
        { type: 'act', n: N(35), fx: 'drop',
          start: () => { F.alvo = r; F.carry = false; F.pose = r === 'ja_tem' ? 'jatem' : r === 'novo' ? 'bark' : 'sad'; F.bubble = r === 'ja_tem' ? 'ok' : r === 'novo' ? '!' : '?';
            this.fsay({ ja_tem: 'Esse eu já li: já está no VIOS. Vai para a caixa verde.', novo: 'Esse aqui é novo! Falta cadastrar no VIOS: caixa âmbar.',
              nao_achou: 'Não consegui conferir este no VIOS: fica para conferir à mão.' }[r]); },
          end: () => this.freduce(ev) },
        { type: 'wait', n: N(25) }, { type: 'call', fn: () => { F.bubble = null; F.pose = null; F.alvo = null; F.carry = true; } });
    } else if (ev.tipo === 'execucao_fim') {
      const p = ev.resultado === 'parou';
      S.push({ type: 'call', fn: () => { this.freduce(ev); F.carry = false; F.pose = p ? 'sad' : null; F.bubble = p ? '?' : null;
          this.fsay(this.ffimTexto(ev)); this.fst(p ? 'Parou' : ev.resultado === 'com_erros' ? 'Com erros' : 'Concluído'); this.setState({ fpanelOpen: true }); } },
        { type: 'wait', n: N(130) }, { type: 'call', fn: () => { F.bubble = null; F.pose = null; this.fst('Voltando à doca'); } },
        { type: 'walk', to: HOME, face: 'right' }, { type: 'call', fn: () => { this.fst('Ocioso'); F.wait = 200; } });
    } else this.freduce(ev);
    if (S.length) this.frun(S);
  }
  fLoadHistory(evs) {
    evs.forEach(e => this.freduce(e));
    setTimeout(() => this.fposicionar(), 0);
  }
  fposicionar() {
    const s = this.state, fp = s.fphase, F = this.fa, O = 80;
    F.fx = null; F.progress = null; F.carry = false; F.bubble = null; F.pose = null; F.idle = null; F.alvo = null; F.wait = 0; F.path = [];
    // execução sem o evento de fim há mais de 3 h: o Orelha caiu no meio; não fica "trabalhando" para sempre
    const velho = !!s.fts && Date.now() - new Date(s.fts).getTime() > 3 * 3600 * 1000;
    const em = fp !== 'idle' && fp !== 'done' && !velho;
    const pos = !em ? [O + 3, 4] : fp === 'entrando' ? [O + 14, 10] : fp === 'planilhas' ? [O + 12, 8] : fp === 'relatorio' ? [O + 5, 8]
      : s.ffase === 'lendo_intimacoes' ? [O + 15, 4] : s.ffase === 'lendo_processos' ? [O + 14, 10] : [O + 9, 4];
    F.x = pos[0] * 16; F.y = pos[1] * 16; F.dir = 'right';
    if (fp === 'idle') return;
    if (fp === 'done') {
      const r = s.fresult || {};
      this.fst(r.resultado === 'parou' ? 'Parou' : 'Ocioso');
      this.fsay('Última execução' + (s.fsim ? ' (simulada)' : '') + ': ' + this.flogTexto(r) + '.');
      return;
    }
    if (velho) { this.fst('Ocioso'); this.fsay('A última execução não chegou ao fim (não recebi o evento de fim). Veja o log do Orelha.'); return; }
    F.wait = 1e9; F.carry = fp === 'planilhas';  // no meio de uma execução: fica no posto até chegar o próximo evento
    this.fst('Trabalhando'); this.fsay('Execução em andamento' + (s.fsim ? ' (simulada)' : '') + '. Acompanhando o próximo passo…');
  }
  falcancar() {
    const q = this.fevq.splice(0);
    if (this.fatual) this.freduce(this.fatual);
    q.forEach(e => this.freduce(e));
    this.fseq = []; this.fcur = null;
    setTimeout(() => this.fposicionar(), 0);
  }
  femitMock() {
    // execução de exemplo (site publicado): os mesmos eventos que o orelha/main.py manda, só com contagens
    if (!this.flivre()) return;
    const envio = 'sim-' + Date.now(), L = [], ev = o => L.push(Object.assign({ bot: 'orelha', envio }, o));
    ev({ tipo: 'execucao_iniciada', funcoes: ['agenda', 'prazos', 'intimacoes', 'planilhas'], simulado: true });
    ev({ tipo: 'fase', fase: 'entrando_vios' });
    ev({ tipo: 'fase', fase: 'lendo_calendario' });
    ev({ tipo: 'achado', funcao: 'agenda', nivel: 'atencao', contagem: 2 });
    ev({ tipo: 'achado', funcao: 'agenda', nivel: 'info', contagem: 3 });
    ev({ tipo: 'fase', fase: 'lendo_calendario' });
    ev({ tipo: 'achado', funcao: 'prazos', nivel: 'grave', contagem: 1 });
    ev({ tipo: 'achado', funcao: 'prazos', nivel: 'atencao', contagem: 4 });
    ev({ tipo: 'fase', fase: 'lendo_intimacoes' });
    ev({ tipo: 'achado', funcao: 'intimacoes', nivel: 'grave', contagem: 2 });
    ev({ tipo: 'fase', fase: 'lendo_planilhas' });
    const R = ['ja_tem', 'novo', 'ja_tem', 'nao_achou', 'ja_tem'];
    R.forEach((r, i) => ev({ tipo: 'planilha', resultado: r, indice: i + 1, total: R.length }));
    ev({ tipo: 'achado', funcao: 'planilhas', nivel: 'atencao', contagem: 2 });
    ev({ tipo: 'achado', funcao: 'planilhas', nivel: 'info', contagem: 3 });
    ev({ tipo: 'fase', fase: 'gerando_relatorio' });
    ev({ tipo: 'execucao_fim', resultado: 'concluido', erros: [], contagens: { agenda: { total: 5, graves: 0, atencao: 2 },
      prazos: { total: 5, graves: 1, atencao: 4, atrasadas: 5 }, intimacoes: { total: 2, graves: 2, atencao: 0 }, planilhas: { total: 5, graves: 0, atencao: 2 } } });
    this.fmock = L;
  }
  fVals() {
    const s = this.state, fp = s.fphase, L = s.ffun, r = s.fresult || {}, PL = s.fplan || {}, off = this.fonte() === 'servidor' && s.conn === 'offline';
    const idx = { idle: 0, entrando: 0, lendo: 1, planilhas: 2, relatorio: 3, done: 4 }[fp] ?? 0;
    const names = [s.fsim ? 'Dados de exemplo' : 'Entrar no VIOS', 'Ler o VIOS', 'Planilhas do Albi', 'Relatório do dia'];
    const steps = names.map((t, i) => ({ n: '0' + (i + 1), t,
      line: i < idx ? '#b68235' : i === idx ? '#d39a5c' : 'rgba(182,130,53,.22)',
      color: i <= idx ? 'var(--color-neutral-100)' : 'var(--color-neutral-300)' }));
    const T = Component.FTITULO;
    const rows = L.map((x, i) => {
      const tag = x.st === 'fila' ? ['Na fila', '#a9a49b'] : x.st === 'lendo' ? ['Lendo…', '#e3c08a'] : x.st === 'erro' ? ['Erro', '#ff7a66'] : x.st === 'parou' ? ['Não rodou', '#8a857c']
        : x.g ? [x.g + ' grave(s)', '#ff7a66'] : x.a ? [x.a + ' de atenção', '#f0a64b'] : ['Nada urgente', '#9cc98a'];
      const partes = [];
      if (x.g) partes.push(x.g + ' grave(s)');
      if (x.a) partes.push(x.a + ' de atenção');
      if (x.i) partes.push(x.i + ' informativo(s)');
      let task = partes.join(' · ') || (x.st === 'feito' ? 'Nada a apontar' : x.st === 'lendo' ? 'Farejando…' : '');
      if (x.k === 'planilhas' && (PL.ja_tem || PL.novo || PL.nao_achou))
        task = (PL.ja_tem || 0) + ' já no VIOS · ' + (PL.novo || 0) + ' novo(s) · ' + (PL.nao_achou || 0) + ' sem conferir';
      return { n: String(i + 1).padStart(2, '0'), proc: T[x.k] || x.k, task, meta: x.tot != null ? x.tot + ' item(ns) no relatório' : '',
        tag: tag[0], col: tag[1], hasIssue: x.st === 'erro', issueMsg: x.st === 'erro' ? 'A função deu erro; o motivo está no relatório do dia (a vila não recebe texto).' : '',
        issueCol: '#ff7a66', hasFix: false, fixLabel: '', applyFix: () => {} };
    });
    const cur = L.find(x => x.st === 'lendo');
    let summary = 'Nenhuma execução ainda';
    if (fp === 'done') { const t = this.ftotais(r), e = this.ferros(r);
      summary = r.resultado === 'parou' ? 'Parou: ' + (Component.FMOTIVO[r.motivo] || r.motivo || 'erro') : t.g + ' grave(s) · ' + t.a + ' de atenção' + (e.length ? ' · erro em ' + e.join(', ') : ''); }
    else if (fp === 'entrando') summary = s.fsim ? 'Começando…' : 'Entrando no VIOS…';
    else if (fp === 'relatorio') summary = 'Escrevendo o relatório…';
    else if (cur) summary = 'Lendo: ' + (T[cur.k] || cur.k);
    if (s.fsim && fp !== 'idle') summary = 'Simulado · ' + summary;
    const simBtn = this.fonte() === 'simulado' && this.flivre(), painel = s.fpanelOpen ? 'Fechar painel' : 'Abrir painel';
    return {
      panelTitle: 'Relatório do dia · Orelha', tabALabel: 'Funções', showSend: false,
      steps, rows, summary,
      sendHint: 'O Orelha só lê o VIOS. O relatório completo fica no computador que roda o Orelha (orelha/saida, pasta do dia).',
      panelOpen: s.fpanelOpen, togglePanel: () => this.setState(st => ({ fpanelOpen: !st.fpanelOpen })),
      hudStatus: 'Orelha · ' + s.fstatus, dotColor: off ? '#5a5f67' : '#d39a5c',
      hudStep: off ? 'Sem conexão' : idx < 4 ? 'Etapa ' + (idx + 1) + '/4' : 'Finalizado',
      speaker: 'Orelha', dialogShown: s.ftext.slice(0, s.ftyped), moreOpacity: s.ftyped >= s.ftext.length ? 1 : 0,
      showAction: simBtn || !!L.length, actionLabel: simBtn ? 'Simular execução' : painel, action: () => this.action(),
      showAction2: false, actionLabel2: '', action2: () => {}, action2Bg: '#2c6c66',
      showPainel: simBtn && !!L.length, painelLabel: painel, painel: () => this.setState(st => ({ fpanelOpen: !st.fpanelOpen }))
    };
  }
  zVals() {"""
troca("\n  zVals() {", FCODE)

if NOVOS:
    t = t.replace("página Ultron", "página do Sam").replace("Ultron", "Sam").replace("Zangão", "Bumblebee")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 05 ligada ao Orelha em", caminho)
