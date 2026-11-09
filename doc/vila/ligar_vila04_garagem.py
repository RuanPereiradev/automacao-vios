"""Vila 04 (Jarvis) vira a garagem do Homem de Ferro, com uma máquina por estação.

Trabalho do Kaio (commit 17103ec da branch relatorio-processos, cenário do fundo-oficina-jarvis.html),
trazido para a vila de 5 vilas como patch próprio, igual à arena (Vila 03) e ao parque (Vila 05):
- parede, túnel com luzes, janelas, telas, carros, armaduras em exposição, braços robóticos soldando e
  uma máquina para cada estação: rack com antena (Conexão VIOS), scanner de documentos (Leitura dos
  processos) e terminal com impressora (Planilhas); a parte fixa vai para o fundo e a animada só é
  desenhada com a Vila 03, 04 ou 05 na tela;
- o holograma do centro é o posto do Jarvis: acende quando ele está lá, com o Jarvis como núcleo;
- o Jarvis voa em linha reta pela garagem (sem o mapa de ladrilhos).
Os eventos, as falas e o painel do Jarvis não mudam.

uso: python3 doc/vila/ligar_vila04_garagem.py bot/vila/vila.html
(depois de todos os outros, inclusive o ligar_orelha_agenda.py, e antes do ligar_vila02_ponte.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "jgaragem(c, f, parte, jc)" in t:
    sys.exit("a Vila 04 já é a garagem do Jarvis")
if "jpatrol()" not in t or "drawParque(c, f)" not in t:
    sys.exit("rode antes o ligar_jarvis.py e o ligar_vila05_parque.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


METODOS = r"""  jalvo() {
    // posição do Jarvis (canto do sprite) em cada lugar: Conexão VIOS (o rack com antena), Leitura dos
    // processos (o holograma, que é o posto dele, ao lado do scanner) e Planilhas (o terminal com impressora)
    return { torre: [992, 130], leitura: [1112, 106], planilhas: [1236, 140] }[this.jfase()] || null;
  }
  jpatrol() {
    // o Jarvis voa em linha reta (a garagem não usa o mapa de ladrilhos)
    const j = this.j, alvo = this.jalvo();
    const ronda = [[1112, 106], [1062, 52], [1112, 40], [1162, 52]];  // o posto e o alto da garagem
    if (!alvo && j.wait > 0) { j.wait--; return; }
    const destino = alvo || ronda[j.i % ronda.length], sp = (alvo ? 1.4 : 0.7) * (this.props.speed ?? 1);
    const dx = destino[0] - j.x, dy = destino[1] - j.y, d = Math.hypot(dx, dy);
    if (d <= sp) { j.x = destino[0]; j.y = destino[1]; j.path = []; if (!alvo) { j.i++; j.wait = 160; } return; }
    j.x += dx / d * sp; j.y += dy / d * sp; j.path = [destino]; j.step += sp;
  }
  jcena() {
    // uma vez por quadro: em que lugar o Jarvis está trabalhando, o relógio dele e se o holograma acende
    const j = this.j, alvo = this.jalvo(), fase = alvo && !j.path.length && j.x === alvo[0] && j.y === alvo[1] ? this.jfase() : null;
    const ff = this.jff = (this.jff || 0) + (fase ? 3 : 1);  // 3x mais rápido trabalhando
    return this.jc = { fase, ff, acesa: Math.hypot(j.x - 1112, j.y - 106) < 6 };
  }
  jgaragem(c, f, parte, jc) {
    // garagem do Homem de Ferro (fundo-oficina-jarvis.html), cena de 320 x 180 desenhada a partir de y = 8
    const OX = 960, OY = 8, W = 320, FLOOR = 118, H = 216;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(OX + x), Math.round(OY + y), Math.round(w), Math.round(h)); };
    const CY = '#5ad8ff', CYd = '#1f6f8f', CYl = '#cfeaff';
    if (parte === 'fundo') {
      R(0, -OY, W, OY, '#2b2e33');
      // parede de concreto e viga do teto
      R(0, 0, W, FLOOR, '#3a3d42');
      for (let y = 0; y < FLOOR; y += 18) R(0, y, W, 1, '#32353a');
      for (let x = 0; x < W; x += 40) R(x + (Math.floor(x / 40) % 2) * 20, 0, 1, FLOOR, '#32353a');
      R(0, 0, 40, FLOOR, 'rgba(0,0,0,.25)'); R(W - 40, 0, 40, FLOOR, 'rgba(0,0,0,.25)');
      R(0, 0, W, 8, '#2b2e33'); R(0, 8, W, 1, '#202328');
      for (let x = 12; x < W; x += 24) R(x, 2, 2, 5, '#45494f');
      // chão em perspectiva e tapete técnico (área de montagem)
      R(0, FLOOR, W, H - FLOOR, '#2a2d33');
      for (let y = FLOOR; y < H; y++) { const t = (y - FLOOR) / (H - FLOOR); R(0, y, W, 1, t < .5 ? '#2d3036' : '#30333a'); if ((y - FLOOR) % 10 === 0) R(0, y, W, 1, '#26292f'); }
      for (let k = -3; k <= 13; k++) for (let y = FLOOR; y < H; y++) { const t = (y - FLOOR) / (H - FLOOR); R(160 + (k - 5) * 20 * (1 + t * 1.5), y, 1, 1, '#26292f'); }
      R(104, 140, 112, 36, '#1f2227'); R(106, 142, 108, 32, '#23262c');
      for (let x = 106; x < 214; x += 12) R(x, 142, 1, 32, '#2c3036');
      for (let y = 142; y < 174; y += 8) R(106, y, 108, 1, '#2c3036');
      // bancada, caixas e ferramentas
      R(44, FLOOR + 44, 40, 2, '#8c939c'); R(46, FLOOR + 46, 2, 12, '#5a616b'); R(80, FLOOR + 46, 2, 12, '#5a616b');
      [[50, '#5a616b'], [62, '#8a6a3a']].forEach(([x, col]) => R(x, FLOOR + 50, 10, 8, col));
      R(50, FLOOR + 40, 14, 4, '#b68235');
      return;
    }
    const acesa = jc && jc.acesa, fase = jc && jc.fase, ff = jc ? jc.ff : f, run = this.state.jrun || {};
    // túnel em arco ao fundo, lâmpadas do chão acendendo em sequência
    { const x0 = 122, x1 = 198, y0 = 26, y1 = FLOOR;
      R(x0, y0 + 10, x1 - x0, y1 - y0 - 10, '#1a1c20'); R(x0 + 6, y0, x1 - x0 - 12, 12, '#1a1c20'); R(x0 + 2, y0 + 4, x1 - x0 - 4, 8, '#1a1c20');
      for (let i = 0; i < 6; i++) {
        const k = i / 6, l = x0 + 8 + k * 22, r = x1 - 8 - k * 22, y = y0 + 14 + k * 6, on = (f >> 4) % 6 !== i;
        R(l, y, 1, y1 - y, '#24272c'); R(r, y, 1, y1 - y, '#24272c');
        R(l + 2, y1 - 8 - k * 20, 2, 1, on ? '#ffd47a' : '#5a4a2a'); R(r - 3, y1 - 8 - k * 20, 2, 1, on ? '#ffd47a' : '#5a4a2a');
        if (on) { R(l + 1, y1 - 7 - k * 20, 4, 2, 'rgba(255,212,122,.18)'); R(r - 4, y1 - 7 - k * 20, 4, 2, 'rgba(255,212,122,.18)'); }
      }
      R(x0 + 30, y1 - 30, 16, 30, '#121417');
      R(x0 - 3, y0 + 8, 3, y1 - y0 - 8, '#4a4e55'); R(x1, y0 + 8, 3, y1 - y0 - 8, '#4a4e55'); R(x0 - 3, y0 + 6, x1 - x0 + 6, 3, '#4a4e55'); }
    // janelas altas com céu noturno
    [[44, 14], [220, 14]].forEach(([x, y]) => {
      const w = 56, h = 44;
      R(x, y, w, h, '#1e2a3a'); R(x + 1, y + 1, w - 2, h - 2, '#2a3c55'); R(x + w / 2, y, 1, h, '#1e2a3a'); R(x, y + h / 2, w, 1, '#1e2a3a');
      for (let i = 0; i < 5; i++) if (((f >> 5) + i) % 3) R(x + 3 + (i * 7) % (w - 6), y + 3 + (i * 11) % (h - 6), 1, 1, '#dfe9f5');
    });
    // telas na parede
    const tela = (x, y, w, h, tipo) => {
      R(x - 1, y - 1, w + 2, h + 2, '#1d1e21'); R(x, y, w, h, '#0b2a3a');
      if (tipo === 0) {  // gráfico de linhas
        for (let i = 0; i < w - 2; i++) R(x + 1 + i, y + h / 2 + Math.sin((i + f * .4) * .5) * (h / 3), 1, 1, CY);
        for (let i = 0; i < 4; i++) R(x + 2, y + 2 + i * 3, 5 + ((i + (f >> 4)) % 3) * 3, 1, CYd);
      } else if (tipo === 1) {  // armadura em wireframe girando
        const cx = x + w / 2, cy = y + h / 2, sx = Math.abs(Math.cos(f * .03));
        R(cx - 2, cy - 7, 4, 3, CY); R(cx - 5 * sx - 1, cy - 4, 10 * sx + 2, 7, CYd); R(cx - 1, cy - 2, 2, 3, CYl);
        R(cx - 5 * sx - 3, cy - 3, 2, 5, CY); R(cx + 5 * sx + 1, cy - 3, 2, 5, CY); R(cx - 3, cy + 3, 2, 5, CY); R(cx + 1, cy + 3, 2, 5, CY);
      } else {  // texto rolando
        for (let i = 0; i < Math.floor(h / 3) - 1; i++) R(x + 2, y + 2 + i * 3, 4 + ((i * 7 + (f >> 3)) % (w - 8)), 1, i === ((f >> 3) % 5) ? CYl : CYd);
      }
      R(x, y + (f >> 1) % h, w, 1, 'rgba(255,255,255,.08)'); R(x - 3, y + h + 1, w + 6, 2, 'rgba(90,216,255,.08)');
    };
    tela(18, 60, 30, 20, 0); tela(60, 70, 34, 22, 2); tela(226, 70, 34, 22, 1); tela(272, 60, 30, 20, 2);
    // as máquinas das estações: cada uma trabalha quando o Jarvis está nela
    { const x = 10, y = FLOOR + 22, busy = fase === 'torre';  // rack com antena: Conexão VIOS
      R(x, y, 24, 34, '#1d1e21'); R(x + 1, y + 1, 22, 32, '#3a3f46');
      for (let r = 0; r < 5; r++) {
        R(x + 3, y + 3 + r * 6, 18, 4, '#2a2d33');
        for (let k = 0; k < 4; k++) { const on = busy ? ((ff >> 2) + r * 3 + k * 5) % 3 !== 0 : ((f >> 5) + r + k) % 4 === 0; R(x + 13 + k * 2, y + 4 + r * 6, 1, 2, on ? (k === 3 ? '#f0c46a' : '#3fd17a') : '#1d1e21'); }
        R(x + 4, y + 4 + r * 6, 6, 1, '#5a616b');
      }
      R(x + 11, y - 10, 2, 10, '#8c939c'); R(x + 10, y - 11, 4, 1, '#d4d8de');
      if (busy) { for (let k = 0; k < 3; k++) if (((ff >> 3) + k) % 3 === 0) { R(x + 8 - k * 3, y - 12 - k * 2, 1, 1, CY); R(x + 15 + k * 3, y - 12 - k * 2, 1, 1, CY); R(x + 9 - k * 3, y - 13 - k * 2, 6 + k * 6, 1, CYd); } }
      else if ((f >> 5) % 2) R(x + 11, y - 13, 2, 1, CYd);
      R(x - 2, y + 34, 28, 2, '#2a2d33'); }
    { const x = 108, y = FLOOR + 2, busy = fase === 'leitura';  // scanner de documentos: Leitura dos processos
      R(x, y + 10, 30, 10, '#1d1e21'); R(x + 1, y + 11, 28, 8, '#3a3f46'); R(x + 2, y + 12, 26, 1, '#5a616b'); R(x + 3, y + 14, 24, 4, '#1a1c20');
      R(x + 2, y, 3, 11, '#5a616b'); R(x + 25, y, 3, 11, '#5a616b'); R(x + 2, y, 26, 2, '#8c939c'); R(x + 4, y + 2, 22, 1, '#45494f');
      R(x + 6, y + 15, 7, 2, '#f6f1e6'); R(x + 7, y + 15, 1, 1, '#9aa0a8'); R(x + 9, y + 15, 2, 1, '#9aa0a8');
      if (busy) {
        const sx = x + 4 + ((ff >> 1) % 22);
        R(sx, y + 3, 1, 12, '#ff5a3c'); R(sx - 1, y + 3, 3, 12, 'rgba(255,90,60,.18)');
        R(x + 17, y + 15, 7, 2, '#f6f1e6'); R(x + 18, y + 15, 3, 1, '#9aa0a8');
        for (let k = 0; k < 3; k++) R(x + 18 + k * 2, y + 7 + ((ff >> 2) + k) % 5, 1, 1, CYl);
      } else if ((f >> 4) % 2) R(x + 14, y + 13, 2, 1, '#3fd17a');
      R(x - 2, y + 20, 34, 2, '#2a2d33'); }
    { const x = 282, y = FLOOR + 26, busy = fase === 'planilhas' && !run.fim, pronto = fase === 'planilhas' && !!run.fim;  // terminal + impressora: Planilhas
      R(x, y, 20, 14, '#1d1e21'); R(x + 1, y + 1, 18, 12, '#0b2a3a');
      for (let k = 0; k < 4; k++) R(x + 2, y + 2 + k * 3, 16, 1, CYd);
      for (let k = 0; k < 4; k++) R(x + 2 + k * 5, y + 2, 1, 11, CYd);
      if (busy) { const cell = (ff >> 2) % 12; R(x + 3 + (cell % 3) * 5, y + 3 + Math.floor(cell / 3) * 3, 4, 2, '#3fd17a'); }
      else if (pronto) { for (let k = 0; k < 12; k++) R(x + 3 + (k % 3) * 5, y + 3 + Math.floor(k / 3) * 3, 4, 2, '#3fd17a'); }  // no fim: tudo preenchido
      else if ((f >> 4) % 2) R(x + 3, y + 3, 4, 2, CYl);
      R(x + 8, y + 14, 4, 2, '#5a616b'); R(x + 5, y + 16, 10, 1, '#5a616b');
      R(x - 3, y + 18, 26, 10, '#3a3f46'); R(x - 2, y + 19, 24, 8, '#5a616b'); R(x, y + 21, 20, 1, '#1d1e21');
      R(x + 16, y + 20, 3, 1, busy ? ((ff >> 2) % 2 ? '#3fd17a' : '#1d1e21') : '#3fd17a');
      if (busy || pronto) {
        const out = pronto ? 6 : (ff >> 2) % 10; R(x + 2, y + 22, 16, Math.min(out, 6), '#f6f1e6');
        for (let k = 0; k < Math.min(out, 6); k++) if (k % 2) R(x + 4, y + 22 + k, 12, 1, '#9aa0a8');
      }
      R(x - 5, y + 28, 30, 2, '#2a2d33'); }
    // carros de coleção (cupê de perfil, 46 x 14)
    const carro = (x, y, cor, vira) => {
      const S = (dx, w, h, col, dy = 0) => R(x + (vira ? 46 - dx - w : dx), y + dy, w, h, col);
      S(10, 26, 5, cor, 0); S(7, 32, 1, cor, 5); S(2, 42, 6, cor, 6); S(0, 46, 2, cor, 10);
      S(12, 22, 4, '#1b2a3a', 1); S(14, 8, 3, '#8fc3e0', 1); S(24, 8, 3, '#8fc3e0', 1); S(0, 46, 1, 'rgba(0,0,0,.35)', 12);
      S(6, 8, 4, '#1d1e21', 11); S(32, 8, 4, '#1d1e21', 11); S(8, 4, 2, '#6b727b', 12); S(34, 4, 2, '#6b727b', 12);
      S(vira ? 1 : 44, 2, 2, (f >> 6) % 2 ? '#ffe8a3' : '#c9b06a', 7); S(vira ? 44 : 1, 2, 1, '#ff5a3c', 7); S(4, 30, 1, 'rgba(255,255,255,.25)', 7);
    };
    carro(40, FLOOR + 8, '#c8102e', false); carro(236, FLOOR + 8, '#c0c4c9', true);
    // armaduras em exposição, uma em cada canto, com os olhos e o núcleo acendendo
    const armadura = (x, y, P, luz) => {
      const S = ['....KKKKKK....', '...KAAAAAAK...', '...KAKEEKAK...', '...KAAAAAAK...', '....KKKKKK....', '.KKKAAAAAAKKK.', 'KAAKAABBAAKAAK',
        'KAAKABCCBAKAAK', 'KAAKAABBAAKAAK', 'KBBKAAAAAAKBBK', 'KBBKBAAAABKBBK', 'KAAKBBAABBKAAK', 'KAAKKBBBBKKAAK', 'KBBK.KAAK.KBBK',
        'KBBK.KAAK.KBBK', '.KK.KAAAAAK.KK', '....KBBBBK....', '....KAAAAK....', '...KBBKKBBK...', '...KAAK.KAAK..', '...KAAK.KAAK..',
        '...KBBK.KBBK..', '...KAAK.KAAK..', '...KAAK.KAAK..', '...KBBK.KBBK..', '..KAAAK.KAAAK.', '..KBBBK.KBBBK.', '..KKKKK.KKKKK.'];
      const pal = { K: '#1d1e21', A: P.a, B: P.b, E: luz ? P.olho : '#1d1e21', C: luz ? P.nucleo : P.b };
      S.forEach((r, jj) => r.split('').forEach((ch, i) => { if (ch !== '.') R(x + i, y + jj, 1, 1, pal[ch]); }));
      if (luz) { R(x + 5, y + 6, 4, 4, P.brilho); R(x + 4, y + 2, 6, 1, P.brilhoOlho); }
      R(x - 3, y + 28, 20, 3, '#3a3f46'); R(x - 1, y + 27, 16, 1, '#5a616b'); R(x - 5, y + 31, 24, 1, 'rgba(0,0,0,.35)');
      R(x + 3, y - 6, 8, 1, '#5a616b'); for (let k = 0; k < 5; k++) R(x + 3 - k, y - 5 + k, 8 + k * 2, 1, 'rgba(255,255,255,.03)');
    };
    const luz = (f >> 5) % 7 !== 0;
    armadura(14, FLOOR - 20, { a: '#b3202f', b: '#c7ccd2', olho: '#e6fbff', nucleo: '#7fe3ff', brilho: 'rgba(127,227,255,.22)', brilhoOlho: 'rgba(230,251,255,.18)' }, luz);
    armadura(292, FLOOR - 20, { a: '#4a4f57', b: '#8c939c', olho: '#ff3b2f', nucleo: '#ff8c3c', brilho: 'rgba(255,140,60,.22)', brilhoOlho: 'rgba(255,59,47,.18)' }, luz);
    // braços robóticos; o da direita solda em ciclos
    const braco = (bx, by, dir, fase0) => {
      const a1 = Math.sin(f * .02 + fase0) * .35 - 1.2, a2 = Math.sin(f * .03 + fase0) * .6 + .6, l1 = 22, l2 = 16;
      const x1 = bx + Math.cos(a1) * l1 * dir, y1 = by + Math.sin(a1) * l1, x2 = x1 + Math.cos(a1 + a2) * l2 * dir, y2 = y1 + Math.sin(a1 + a2) * l2;
      R(bx - 6, by, 12, 5, '#3a3f46'); R(bx - 4, by - 2, 8, 2, '#5a616b');
      const seg = (xa, ya, xb, yb, w, col) => { const n = Math.max(Math.abs(xb - xa), Math.abs(yb - ya)) | 0; for (let i = 0; i <= n; i++) R(xa + (xb - xa) * i / n - (w >> 1), ya + (yb - ya) * i / n - (w >> 1), w, w, col); };
      seg(bx, by, x1, y1, 4, '#8c939c'); seg(bx, by, x1, y1, 2, '#b8bec6'); seg(x1, y1, x2, y2, 3, '#6b727b'); seg(x1, y1, x2, y2, 1, '#9aa0a8');
      R(x1 - 2, y1 - 2, 4, 4, '#3a3f46'); R(x1 - 1, y1 - 1, 2, 2, '#ff5a3c'); R(x2 - 2, y2 - 1, 4, 3, '#45494f'); R(x2 + dir * 2, y2, 2, 1, '#d4d8de');
      return [x2 + dir * 3, y2];
    };
    braco(86, 128, 1, 0); const ponta = braco(236, 150, -1, 2.1);
    if ((f >> 6) % 3 === 0) {
      R(ponta[0] - 1, ponta[1] - 1, 3, 3, '#ffffff'); R(ponta[0] - 3, ponta[1] - 3, 7, 7, 'rgba(255,240,200,.25)');
      if (f % 2) this.jsolda.push({ x: ponta[0], y: ponta[1], vx: (Math.random() - .5) * 1.6, vy: -Math.random() * 1.2, l: 14 + Math.random() * 10 });
    }
    this.jsolda = this.jsolda.filter(p => p.l-- > 0);
    this.jsolda.forEach(p => { p.x += p.vx; p.y += p.vy; p.vy += .08; R(p.x, p.y, 1, 1, p.l > 8 ? '#fff1a8' : '#ff8c3c'); });
    // o posto do Jarvis: o projetor; com ele em cima, o holograma acende em volta dele (o Jarvis é o núcleo)
    const cx = 160, cy = 100;
    R(150, 136, 20, 4, '#3a3f46'); R(152, 134, 16, 2, '#5a616b'); R(158, 133, 4, 1, acesa ? CYl : '#3f6f80');
    for (let y = 134; y > cy + 10; y--) { const t = (134 - y) / (134 - cy - 10); R(cx - 2 - t * 12, y, 4 + t * 24, 1, `rgba(90,216,255,${(acesa ? 1 : .35) * (.03 + .03 * (1 - t))})`); }
    if (acesa) {
      const g = c.createRadialGradient(OX + 160, OY + 150, 2, OX + 160, OY + 150, 50);
      g.addColorStop(0, 'rgba(90,216,255,.22)'); g.addColorStop(1, 'rgba(90,216,255,0)');
      c.fillStyle = g; c.fillRect(OX + 100, OY + FLOOR, 120, H - FLOOR);
      const gira = fase === 'leitura' ? ff : f, Rr = 22 * (.85 + .15 * Math.sin(gira * .06));
      for (let i = 0; i < 260; i++) {
        const t = i / 259, phi = Math.acos(1 - 2 * t), th = t * 10 * 6.28 + gira * .02;
        const x = Rr * Math.sin(phi) * Math.cos(th), z = Rr * Math.sin(phi) * Math.sin(th), y = Rr * Math.cos(phi);
        R(cx + x, cy + y * .9, 1, 1, `rgba(120,225,255,${.25 + .75 * (z + Rr) / (2 * Rr)})`);
      }
      for (let k = 0; k < 2; k++) {
        const rr = Rr * (1.25 + k * .2), ang = gira * (k ? -.01 : .015);
        for (let i = 0; i < 40; i++) { if ((i >> 1) % 2) continue; const a = i / 40 * 6.28 + ang; R(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr * .35, 1, 1, CYl); }
      }
      if (!this.jholo) this.jholo = Array.from({ length: 90 }, (_, i) => ({ a: i / 90 * 6.28, r: .3 + Math.random() * .7, s: .01 + Math.random() * .02, f: Math.random() * 6.28 }));
      this.jholo.forEach(p => { p.a += p.s * (fase === 'leitura' ? 3 : 1); R(cx + Math.cos(p.a) * Rr * p.r * 1.6, cy + Math.sin(p.a) * Rr * p.r * .5 + Math.sin(f * .05 + p.f) * 3, 1, 1, `rgba(207,238,255,${.3 + .5 * Math.abs(Math.sin(p.a))})`); });
      [[cx - 62, cy - 26], [cx + 44, cy - 20], [cx - 54, cy + 8], [cx + 40, cy + 12]].forEach(([x, y], i) => {
        R(x, y, 18, 10, 'rgba(90,216,255,.10)'); R(x, y, 18, 1, CYd); R(x, y + 9, 18, 1, CYd);
        for (let k = 0; k < 3; k++) R(x + 2, y + 2 + k * 2, 4 + ((k * 5 + i * 3 + (gira >> 3)) % 10), 1, k === (gira >> 4) % 3 ? CYl : CYd);
        for (let k = 1; k < 10; k += 2) R(x + 9 + (cx - x - 9) * k / 10, y + 5 + (cy - y - 5) * k / 10, 1, 1, CYd);
      });
    }
    if ((f >> 3) % 23 === 0) R(0, 9, W, FLOOR - 9, 'rgba(255,255,255,.03)');  // fluorescente piscando
  }
"""
CENAS_VELHAS = r"""
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
CENAS_NOVAS = r"""
      const ox = j.x + 8, oy = j.y + jb + 4, run = this.state.jrun || {};
      if (fase === 'torre') {
        // Conexão VIOS: sinais saem do núcleo para a antena do rack
        const sx = 960 + 22, sy = 8 + 129;
        for (let i = 0; i < 3; i++) { const k = ((ff + i * 14) % 42) / 42; R(ox + (sx - ox) * k, oy + (sy - oy) * k - Math.sin(k * Math.PI) * 6, 2, 2, i % 2 ? '#e6fbff' : '#7fe3ff'); }
      } else if (fase === 'leitura') {
        // Leitura dos processos: as folhas lidas saem do scanner e entram girando no núcleo (no holograma)
        for (let i = 0; i < 4; i++) {
          const k = ((ff + i * 11) % 44) / 44, ang = k * Math.PI * 3, raio = (1 - k) * 5, x0 = 960 + 128, y0 = 8 + 134;
          const x = x0 + (ox - x0) * k + Math.cos(ang) * raio, y = y0 + (oy - y0) * k + Math.sin(ang) * raio - Math.sin(k * Math.PI) * 8;
          R(x - 2, y - 2, 4, k > 0.8 ? 3 : 5, '#f6f1e6');  // a folha encolhe ao entrar no núcleo
          if (k < 0.8) { R(x - 1, y - 1, 2, 1, '#9aa0a8'); R(x - 1, y + 1, 2, 1, '#9aa0a8'); }
        }
        if (run.total) { const prog = Math.min(1, (run.feito || 0) / run.total); R(ox - 9, oy - 34, 18, 4, '#201f1d'); R(ox - 8, oy - 33, 16, 2, '#1a4f5c'); R(ox - 8, oy - 33, Math.round(16 * prog), 2, '#7fe3ff'); }
      } else if (fase === 'planilhas' && !run.fim) {
        // Planilhas: os dados vão do núcleo para o terminal, que preenche a planilha e imprime
        const sx = 960 + 292, sy = 8 + 151;
        for (let i = 0; i < 3; i++) { const k = ((ff + i * 12) % 36) / 36; R(ox + (sx - ox) * k, oy + (sy - oy) * k - Math.sin(k * Math.PI) * 5, 2, 2, '#7fe3ff'); }
      }"""

# 1) a parte fixa da garagem vai para o fundo (no lugar dos prédios da vila genérica)
troca("    for (let v = 0; v < Component.NV; v++) {\n      const O = v * 320, on = v <= 4;\n",
      "    for (let v = 0; v < Component.NV; v++) {\n      if (v === 3) { this.jgaragem(c, 0, 'fundo'); continue; }\n      const O = v * 320, on = v <= 4;\n")
# 2) a parte animada, logo depois do fundo, só com a Vila 03, 04 ou 05 na tela
troca("    c.drawImage(this.bg, 0, 0);\n",
      "    c.drawImage(this.bg, 0, 0);\n    const jc = this.jcena(); if (this.state.village >= 2) this.jgaragem(c, f, 'vivo', jc);\n")
# 3) placas próprias
troca("      if (v === 2) { // arena do Albi\n",
      "      if (v === 3) { plaques.push(P(63.5, 7.5, 'Conexão VIOS'), P(70, 4.1, 'Leitura dos processos'), P(77.9, 9.1, 'Planilhas')); continue; }\n"
      "      if (v === 2) { // arena do Albi\n")
# 4) começa no posto (holograma); faíscas da solda
troca("    this.j = { x: 63 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 90, i: 0 };\n",
      "    this.j = { x: 1112, y: 106, dir: 'down', path: [], step: 0, wait: 90, i: 0 }; this.jholo = null; this.jsolda = [];\n")
# 5) lugares, voo em linha reta, a cena de cada quadro e o desenho da garagem
a = t.index("  jalvo() {"); b = t.index("  jdinheiro(v)")
assert t.count("  jalvo() {") == 1 and a < b
t = t[:a] + METODOS + t[b:]
# 6) no desenho do Jarvis: fase e relógio vêm de jcena(); sai a luz da torre genérica
troca("""      const alvo = this.jalvo(), fase = alvo && !j.path.length && Math.round(j.x / 16) === alvo[0] && Math.round(j.y / 16) === alvo[1] ? this.jfase() : null;
      const ff = this.jff = (this.jff || 0) + (fase ? 3 : 1);  // relógio do Jarvis: 3x mais rápido trabalhando
      R(960 + 63, 4, 3, 3, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      R(960 + TX + 15, TY, 2, 2, fase === 'torre' ? ((f >> 2) % 2 ? '#e6fbff' : '#7fe3ff') : (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
""", "      const { fase, ff } = this.jc;  // calculados em jcena(), antes da garagem\n")
# 7) o que cada máquina faz com o Jarvis nela
troca(CENAS_VELHAS, CENAS_NOVAS)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print(f"Vila 04 virou a garagem do Jarvis em {caminho}")
