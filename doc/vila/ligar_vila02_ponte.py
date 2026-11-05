"""Vila 02 (Bumblebee) vira a batalha na ponte, vista de cima (doc/vila/zangao-transforma_att.html).

O fundo da vila genérica (prédios cinza, lotes e torre de metal) é trocado por uma ponte sobre a água:
- água com ondas e o reflexo do fogo; pista de asfalto com faixas tracejadas e a dupla amarela no meio,
  guard-rail, cabos e quatro pilares das torres da ponte (a luz vermelha pisca);
- os postos viram coisas da ponte, nos mesmos lugares (os eventos, as falas e o painel não mudam):
  **Doca 01 · Bumblebee** = garagem listrada com a vaga marcada no asfalto (a luz da doca pisca);
  **Filtro previdenciário** = cabine de pedágio com cancela, que sobe quando ele filtra ou passa;
  **Captura de dados** = pórtico sobre a pista com o painel de mensagens (a tela da captura);
  **Torre VIOS** = antena no pilar da direita (a luz da ponta pisca rápido quando ele manda/puxa);
- o Bumblebee: parado é o robô de frente; para andar, as peças voam e encaixam no carro visto de cima,
  que gira para o lado em que ele vai (anda em L, como antes); ao virar, sai uma onda de choque;
- em volta, a batalha: dois duelos de robôs (chegam como carros, viram robôs, trocam socos e tiros,
  explodem e vão embora como carros), trânsito nas faixas, carcaças pegando fogo, explosões de vez em
  quando longe do Bumblebee, destroços, fumaça e brasas. A parte animada só é desenhada com a Vila 01,
  02 ou 03 na tela. Sem tremer a tela (a vila é uma só).
O Bumblebee anda só na pista (linhas 4 a 11 da Vila 02), sem passar pela base da antena.

uso: python3 doc/vila/ligar_vila02_ponte.py bot/vila/vila.html
(depois de todos os outros, inclusive o ligar_vila04_garagem.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "drawPonte(c, f, parte)" in t:
    sys.exit("a Vila 02 já é a ponte")
if "BROBOT" not in t or "jgaragem(c, f, parte, jc)" not in t:
    sys.exit("rode antes o ligar_bumblebee.py e o ligar_vila04_garagem.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) carro visto de cima e onde cada peça do robô encaixa nele (iguais ao zangao-transforma_att.html)
troca("  static BPARTS = [", r"""  static BCART = [
    '....KKKK............KKKK......', '..KKYYYYYYYYYYYYYYYYYYYYYYKK..', '.KYYYYYYYBBBBYYYYYYBBBBYYYYYHK',
    'KYYYYYYYBBBBBYYYYYYBBBBBYYYYYK', 'KKKKKKKKBBBBBKKKKKKBBBBBKKKKKK', 'KYYYYYYYBBBBBYYYYYYBBBBBYYYYYK',
    'KYYYYYYYBBBBBYYYYYYBBBBBYYYYYK', 'KKKKKKKKBBBBBKKKKKKBBBBBKKKKKK', 'KYYYYYYYBBBBBYYYYYYBBBBBYYYYYK',
    '.KYYYYYYYBBBBYYYYYYBBBBYYYYYHK', '..KKYYYYYYYYYYYYYYYYYYYYYYKK..', '....KKKK............KKKK......'
  ];
  // peças do robô -> posição no carro (relativa ao centro, frente para a direita); rot = voltas; d = atraso
  static BPARTST = [
    { rx: 7, ry: 0, rw: 10, rh: 8, dx: 6, dy: 0, rot: .5, d: 0 }, { rx: 6, ry: 8, rw: 12, rh: 9, dx: -1, dy: 0, rot: 0, d: .08 },
    { rx: 0, ry: 8, rw: 4, rh: 5, dx: -3, dy: -4, rot: 1, d: .12 }, { rx: 20, ry: 8, rw: 4, rh: 5, dx: -3, dy: 4, rot: 1, d: .12 },
    { rx: 2, ry: 13, rw: 4, rh: 6, dx: -11, dy: -3, rot: .5, d: .18 }, { rx: 18, ry: 13, rw: 4, rh: 6, dx: -11, dy: 3, rot: .5, d: .18 },
    { rx: 7, ry: 17, rw: 5, rh: 9, dx: 10, dy: -3, rot: .25, d: .26 }, { rx: 13, ry: 17, rw: 5, rh: 9, dx: 10, dy: 3, rot: .25, d: .26 }
  ];
  // robôs e carros da batalha (vista de cima)
  static PNROBO = ['.....KKKKKK.....', '....KAAAAAAK....', '....KAKEEKAK....', '....KAAAAAAK....', '.....KKKKKK.....', '..KKKKBBBBKKKK..',
    '.KAAKBBBBBBKAAK.', '.KAAKBBCCBBKAAK.', '.KAAKBBBBBBKAAK.', '.KAAKKBBBBKKAAK.', '.KAK.KAAAAK.KAK.', '.KKK.KAAAAK.KKK.',
    '.....KKKKKK.....', '.....KAKKAK.....', '.....KAKKAK.....', '.....KAKKAK.....', '....KKAKKAKK....', '....KKKKKKKK....'];
  static PNCARRO = ['...KKK.........KKK....', '.KKAAAAAAAAAAAAAAAAKK.', 'KAAAAAWWWWAAAAWWAAAAHK', 'KAAAAWWWWWAAAAWWWAAAAK',
    'KAAAAWWWWWAAAAWWWAAAAK', 'KAAAAAWWWWAAAAWWAAAAHK', '.KKAAAAAAAAAAAAAAAAKK.', '...KKK.........KKK....'];
  static BPARTS = [""")

# 2) para onde o carro aponta: a direção do próximo passo (calculada antes de andar, para o carro já
#    se formar virado para o lado certo)
troca("      if (z.dir === 'left') z.hd = -1; else if (z.dir === 'right') z.hd = 1; }",
      "      if (z.dir === 'left') z.hd = -1; else if (z.dir === 'right') z.hd = 1;\n"
      "      if (z.path.length) { const ddx = z.path[0][0] * 16 - z.x, ddy = z.path[0][1] * 16 - z.y;\n"
      "        if (Math.abs(ddx) > 0.01) z.face = ddx > 0 ? 0 : Math.PI; else if (Math.abs(ddy) > 0.01) z.face = ddy > 0 ? Math.PI / 2 : -Math.PI / 2; } }")

# 3) desenho do Bumblebee: robô de frente, transformação para o carro visto de cima, carro girando
a = t.index("      const RB = Component.BROBOT, CB = Component.BCAR, k = z.m || 0, flip = z.hd < 0")
b = t.index("      const zx = z.x, zy = topo + 4;", a)
t = t[:a] + r"""      const RB = Component.BROBOT, CT = Component.BCART, k = z.m || 0, face = z.face || 0, cx = Math.round(z.x + 8), G = Math.round(z.y + 15);
      const blit = (rows, x, y, pal) => { rows.forEach((r, j) => { for (let i = 0; i < r.length; i++) { const ch = r[i]; if (ch !== '.') R(x + i, y + j, 1, 1, pal[ch]); } }); };
      const blitRot = (rows, x, y, ang, pal, alpha) => {
        const w = rows[0].length, h = rows.length; c.save(); c.translate(Math.round(x), Math.round(y)); c.rotate(ang); c.globalAlpha = alpha;
        rows.forEach((r, j) => { for (let i = 0; i < w; i++) { const ch = r[i]; if (ch === '.') continue; c.fillStyle = pal[ch]; c.fillRect(i - (w >> 1), j - (h >> 1), 1, 1); } });
        c.restore();
      };
      const gira = (x, y, ang) => [Math.round(x * Math.cos(ang) - y * Math.sin(ang)), Math.round(x * Math.sin(ang) + y * Math.cos(ang))];
      const sombra = w => { c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.ellipse(cx, G, w, w * .35, 0, 0, 6.283); c.fill(); };
      const carro = k >= 0.9, meio = k > 0.04 && !carro;
      if ((k > .5) !== !!z.virou) { z.virou = k > .5; z.pulso = 1; }  // onda de choque ao virar carro ou robô
      if (z.pulso > 0) {
        const rp = (1 - z.pulso) * 40 + 4; c.strokeStyle = 'rgba(207,234,255,' + (z.pulso * .7) + ')'; c.lineWidth = 1;
        c.beginPath(); c.ellipse(cx, G - 3, rp, rp * .45, 0, 0, 6.283); c.stroke(); z.pulso -= .035;
      }
      let topo;
      if (meio) { // peças voam do robô para o carro (ou de volta), em arco e girando de 90 em 90°
        const ease = q => q < .5 ? 4 * q * q * q : 1 - Math.pow(-2 * q + 2, 3) / 2;
        sombra(10);
        blitRot(CT, cx, G - 6, face, BP, Math.max(0, (k - .5) * 2));
        Component.BPARTST.forEach(p => {
          const q = ease(Math.max(0, Math.min(1, (k - p.d) / (.9 - p.d))));
          const ox = cx - 12 + p.rx + p.rw / 2, oy = G - 26 + p.ry + p.rh / 2, [ddx, ddy] = gira(p.dx, p.dy, face), dx = cx + ddx, dy = G - 6 + ddy;
          c.save(); c.translate(Math.round(ox + (dx - ox) * q), Math.round(oy + (dy - oy) * q - Math.sin(q * Math.PI) * 8));
          c.rotate(Math.round(p.rot * 4 * q) * Math.PI / 2); c.globalAlpha = 1 - Math.max(0, (q - .85) / .15);
          const hw = p.rw >> 1, hh = p.rh >> 1;
          for (let j = 0; j < p.rh; j++) for (let i = 0; i < p.rw; i++) { const ch = RB[p.ry + j][p.rx + i]; if (ch === '.') continue; c.fillStyle = ZP[ch]; c.fillRect(i - hw, j - hh, 1, 1); }
          c.restore();
        });
        topo = G - 26 + Math.round(14 * k);
      } else if (carro) {
        const sv = Math.abs(Math.sin(face)) > .5;
        c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(cx - (sv ? 6 : 15) + 1, G - 6 - (sv ? 15 : 6) + 2, sv ? 12 : 30, sv ? 30 : 12);
        c.save(); c.translate(cx, G - 6); c.rotate(face);
        const fa = c.createLinearGradient(15, 0, 34, 0); fa.addColorStop(0, 'rgba(255,241,168,.4)'); fa.addColorStop(1, 'rgba(255,241,168,0)');
        c.fillStyle = fa; c.beginPath(); c.moveTo(14, -5); c.lineTo(34, -9); c.lineTo(34, 9); c.lineTo(14, 5); c.fill();  // faróis
        if (zm) for (let i = 0; i < 4; i++) { c.fillStyle = 'rgba(207,234,255,.3)'; c.fillRect(-18 - i * 5 - (f % 5), -4 + i * 2 + (i > 1 ? 1 : 0), 4, 1); }  // rastro
        c.restore();
        blitRot(CT, cx, G - 6, face, BP, 1);
        topo = G - 6 - (sv ? 15 : 6);
      } else {
        sombra(9);
        blit(RB, cx - 12, G - 26 + zb, ZP);
        if ((f >> 4) % 2) { R(cx - 13, G - 19 + zb, 1, 1, BP.L); R(cx + 12, G - 19 + zb, 1, 1, BP.L); }  // asas-porta
        if (!zbl) { c.fillStyle = 'rgba(61,139,255,.35)'; c.fillRect(cx - 3, G - 23 + zb, 7, 3); }  // brilho dos olhos
        topo = G - 26 + zb;
      }
""" + t[b:]

# 4) luzes dos postos nos lugares novos: a da doca (garagem) e a da Torre VIOS (ponta da antena)
troca("    R(320 + 63, 4, 3, 3, (f >> 5) % 2 ? '#f2c230' : '#6b5520');",
      "    R(320 + 55, 45, 3, 2, (f >> 5) % 2 ? '#f2c230' : '#6b5520');")
troca("    R(320 + TX + 15, TY, 2, 2, (zfx === 'send' || zfx === 'pull')",
      "    R(320 + 255, 135, 2, 2, (zfx === 'send' || zfx === 'pull')")
# os sinais para a torre vão até a antena
troca("const zc = this.zcur, t0 = zc ? zc.t : 0, TXZ = 320 + TX;", "const zc = this.zcur, t0 = zc ? zc.t : 0, TXZ = 320 + 248;")

# 5) fundo: a ponte no lugar dos prédios da Vila 02
troca("      if (v === 3) { this.jgaragem(c, 0, 'fundo'); continue; }\n",
      "      if (v === 3) { this.jgaragem(c, 0, 'fundo'); continue; }\n      if (v === 1) { this.paintPonte(c); continue; }\n")
# 6) a parte animada: água, cancela, carcaças, trânsito e duelos por baixo do Bumblebee;
#    tiros, explosões, destroços, fumaça e brasas por cima
troca("    c.drawImage(this.bg, 0, 0);\n",
      "    c.drawImage(this.bg, 0, 0);\n    if (this.state.village <= 2) this.drawPonte(c, f, 'baixo');\n")
troca("    {\n      const a = this.a, O3 = 640,",
      "    if (this.state.village <= 2) this.drawPonte(c, f, 'cima');\n    {\n      const a = this.a, O3 = 640,")

# 7) onde ele anda: só a pista (linhas 4–11 da Vila 02 = colunas 20–39), sem a base da antena
troca("    for (let y = 0; y < 14; y++) for (let x = 40; x < 60; x++) this.blocked[y][x] = !(y >= 8 && y <= 10 && x >= 43 && x <= 56);",
      "    for (let y = 0; y < 14; y++) for (let x = 40; x < 60; x++) this.blocked[y][x] = !(y >= 8 && y <= 10 && x >= 43 && x <= 56);\n"
      "    // Vila 02 = ponte: o Bumblebee anda só na pista (linhas 4–11), sem passar pela base da antena\n"
      "    for (let y = 0; y < 14; y++) for (let x = 20; x < 40; x++) this.blocked[y][x] = !(y >= 4 && y <= 11) || (x === 35 && y >= 9);")

# 8) placas
troca("      if (v === 2) { // arena do Albi\n",
      "      if (v === 1) { plaques.push(P(23.5, 1.4, 'Doca 01 · Bumblebee'), P(29.5, 1.4, 'Filtro previdenciário'), P(37, 1.0, 'Captura de dados'), P(36, 7.8, 'Torre VIOS')); continue; }\n"
      "      if (v === 2) { // arena do Albi\n")

# 9) o desenho da ponte
troca("  paintArena(c) {", r"""  paintPonte(c) {
    // ponte vista de cima (Vila 02, x local 0–319 + 320): pista de y = 40 a 200, água em volta
    const O = 320, W = 320, H = 224, DT = 40, DB = 200;
    c.save(); c.beginPath(); c.rect(O, 0, W, H); c.clip();  // ponte: recorte
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    const rr = s => { s = Math.sin(s * 127.1) * 43758.5453; return s - Math.floor(s); };
    R(0, 0, W, H, '#13222e');
    // asfalto, faixas tracejadas e a dupla amarela
    R(0, DT, W, DB - DT, '#34363c');
    for (let i = 0; i < 170; i++) R(rr(i) * W, DT + 4 + rr(i + 40) * (DB - DT - 8), 1, 1, i % 3 ? '#3c3f46' : '#2b2d32');
    for (let x = 0; x < W; x += 16) { R(x, 98, 8, 1, '#d9d0c0'); R(x, 160, 8, 1, '#d9d0c0'); }
    R(0, 120, W, 1, '#e8b923'); R(0, 123, W, 1, '#e8b923');
    // bordas, guard-rail e cabos
    R(0, DT, W, 3, '#5a616b'); R(0, DT + 3, W, 1, '#8c939c'); R(0, DB - 4, W, 1, '#8c939c'); R(0, DB - 3, W, 3, '#5a616b');
    for (let x = 2; x < W; x += 8) { R(x, DT + 1, 1, 1, '#2b2e36'); R(x, DB - 2, 1, 1, '#2b2e36'); }
    R(0, DT - 2, W, 1, '#6b727b'); R(0, DB + 1, W, 1, '#6b727b');
    // sombra das vigas das torres atravessando a pista e os pilares (vistos de cima)
    [64, 248].forEach(x => { c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(O + x - 2, DT, 18, DB - DT); });
    [64, 248].forEach(x => [DT - 11, DB - 1].forEach(y => { R(x, y, 16, 12, '#2b2e36'); R(x + 1, y + 1, 14, 10, '#4a4f57'); R(x + 1, y + 1, 14, 1, '#6b727b'); R(x + 5, y + 3, 6, 6, '#1d1e21'); }));
    // Doca 01 · Bumblebee: garagem listrada (a luz pisca em cima) e a vaga marcada no asfalto
    R(40, 43, 32, 15, '#1d1e21'); R(41, 44, 30, 13, '#3a3f46'); R(43, 47, 26, 6, '#2b2e36'); R(44, 48, 24, 1, '#5a616b');
    for (let i = 0; i < 30; i += 6) R(41 + i, 54, 3, 3, '#e8b923');
    const vaga = (x, y, w, h) => { R(x, y, w, 1, '#e8b923'); R(x, y + h - 1, w, 1, '#e8b923'); R(x, y, 1, h, '#e8b923'); R(x + w - 1, y, 1, h, '#e8b923'); };
    vaga(38, 60, 36, 26); for (let i = 0; i < 4; i++) R(40 + i * 9, 82, 5, 2, '#b68235');
    // Filtro previdenciário: cabine de pedágio com a ilha (a cancela é desenhada a cada quadro)
    R(140, 42, 24, 16, '#1d1e21'); R(141, 43, 22, 14, '#8c939c'); R(141, 43, 22, 2, '#d4d8de'); R(144, 47, 16, 7, '#2b2e36'); R(145, 48, 14, 1, '#5a6c80');
    R(142, 58, 20, 3, '#5a616b'); R(142, 58, 20, 1, '#8c939c'); for (let x = 143; x < 161; x += 4) R(x, 60, 2, 1, '#e8b923');
    R(165, 54, 5, 5, '#1d1e21'); R(166, 55, 3, 3, '#5a616b');
    // Captura de dados: pórtico sobre a pista, com o painel de mensagens em cima
    c.fillStyle = 'rgba(0,0,0,.3)'; c.fillRect(O + 275, DT, 5, DB - DT);
    R(270, DT - 6, 5, DB - DT + 10, '#5a616b'); R(271, DT - 6, 1, DB - DT + 10, '#8c939c');
    for (let y = DT; y < DB; y += 8) R(270, y, 5, 1, '#3a3f46');
    R(267, DT - 9, 11, 4, '#3a3f46'); R(267, DB + 3, 11, 4, '#3a3f46');
    R(256, 32, 32, 20, '#2a2d33'); R(257, 33, 30, 18, '#3a3f46'); R(258, 34, 28, 16, '#1d1e21');
    // Torre VIOS: antena treliçada no pilar de baixo, à direita (a luz da ponta é desenhada a cada quadro)
    R(249, 198, 14, 8, '#2a2d33');
    for (let y = 146; y < 200; y++) {
      const q = (y - 146) / 54, l = Math.round(255 - 1 - 5 * q), r = Math.round(256 + 1 + 5 * q);
      R(l, y, 1, 1, '#9aa0a8'); R(r, y, 1, 1, '#9aa0a8'); if ((y - 146) % 6 === 0) R(l, y, r - l + 1, 1, '#6b727b');
    }
    R(255, 136, 2, 12, '#d4d8de'); R(249, 146, 14, 2, '#d4d8de'); R(251, 148, 10, 1, '#9aa0a8');
    c.restore();
  }
  drawPonte(c, f, parte) {
    const O = 320, W = 320, H = 224, DT = 40, DB = 200, z = this.z;
    const P = this.ponte || (this.ponte = { fumaca: [], destrocos: [], explosoes: [], tiros: [], marcas: [], cancela: 0,
      brasas: Array.from({ length: 30 }, (_, i) => { const s = q => { q = Math.sin(q * 127.1) * 43758.5453; return q - Math.floor(q); }; return { x: s(i) * W, y: s(i + 9) * H, s: .1 + s(i + 3) * .3, p: s(i + 5) * 6 }; }) });
    c.save(); c.beginPath(); c.rect(O, 0, W, H); c.clip();
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    const rr = s => { s = Math.sin(s * 127.1) * 43758.5453; return s - Math.floor(s); };
    const PAL = Component.BPAL, BASE = { K: '#1d1e21', W: '#8fc3e0', H: '#fff1a8' };
    const NPAL = [
      Object.assign({ A: '#9aa0a8', B: '#5a616b', C: '#5ad8ff', E: '#5ad8ff' }, BASE), Object.assign({ A: '#3a3f46', B: '#7a1a2a', C: '#ff3b2f', E: '#ff3b2f' }, BASE),
      Object.assign({ A: '#3f8f4a', B: '#b68235', C: '#fff1a8', E: '#7fe3ff' }, BASE), Object.assign({ A: '#4a2a5a', B: '#2b2e36', C: '#c86bff', E: '#c86bff' }, BASE)];
    const blit = (rows, x, y, pal) => rows.forEach((r, j) => { for (let i = 0; i < r.length; i++) { const ch = r[i]; if (ch !== '.') R(x + i, y + j, 1, 1, pal[ch] || PAL[ch]); } });
    const blitRot = (rows, cx, cy, ang, pal, alpha = 1) => {
      const w = rows[0].length, h = rows.length; c.save(); c.translate(Math.round(O + cx), Math.round(cy)); c.rotate(ang); c.globalAlpha = alpha;
      rows.forEach((r, j) => { for (let i = 0; i < w; i++) { const ch = r[i]; if (ch === '.') continue; c.fillStyle = pal[ch] || PAL[ch]; c.fillRect(i - (w >> 1), j - (h >> 1), 1, 1); } });
      c.restore();
    };
    const peca = (src, r0, r1, px, py, ang, pal, alpha) => {
      c.save(); c.translate(Math.round(O + px), Math.round(py)); c.rotate(ang); c.globalAlpha = alpha;
      for (let j = r0; j < r1; j++) for (let i = 0; i < 16; i++) { const ch = src[j][i]; if (ch === '.') continue; c.fillStyle = pal[ch] || PAL[ch]; c.fillRect(i - 8, j - r0 - ((r1 - r0) >> 1), 1, 1); }
      c.restore();
    };
    const gira = (x, y, a) => [Math.round(x * Math.cos(a) - y * Math.sin(a)), Math.round(x * Math.sin(a) + y * Math.cos(a))];
    const sombra = (x, y, w) => { c.fillStyle = 'rgba(0,0,0,.35)'; c.beginPath(); c.ellipse(O + x, y, w, w * .35, 0, 0, 6.283); c.fill(); };
    const faiscas = (x, y, n, col, seed) => { for (let i = 0; i < n; i++) { const a = rr(i + seed) * 6.283, d = 1 + rr(i * 3 + seed) * 5; R(x + Math.cos(a) * d, y + Math.sin(a) * d, 1, 1, i % 2 ? '#ffffff' : col); } };
    const fumaca = (x, y, grande) => { if (P.fumaca.length < 140) P.fumaca.push({ x, y, r: grande ? 3 : 2, a: grande ? .45 : .3, vx: .18 + Math.random() * .1, vy: -.12 - Math.random() * .08 }); };
    const bum = (x, y) => {
      P.explosoes.push({ x, y, t: 0 }); P.marcas.push({ x, y, a: .6 }); if (P.marcas.length > 10) P.marcas.shift();
      for (let i = 0; i < 16; i++) P.destrocos.push({ x, y, vx: (rr(i + f) - .5) * 3, vy: (rr(i * 7 + f) - .5) * 3, z: 0, vz: 1 + rr(i + 2 * f) * 1.5, l: 36 });
    };
    const fogo = (x, y, s) => {
      for (let i = 0; i < 8 * s; i++) R(x + (rr(i + (f >> 2)) - .5) * 6 * s, y - rr(i * 3 + (f >> 2)) * 5 * s, 1, 1, i % 3 === 0 ? '#fff1a8' : i % 3 === 1 ? '#ffb15a' : '#ff5a2a');
      const g = c.createRadialGradient(O + x, y - 2, 0, O + x, y - 2, 9 * s); g.addColorStop(0, 'rgba(255,150,60,.25)'); g.addColorStop(1, 'rgba(255,150,60,0)');
      c.fillStyle = g; c.fillRect(O + x - 10 * s, y - 12 * s, 20 * s, 20 * s);
      if (f % 7 === 0) fumaca(x, y - 4, true);
    };
    if (parte === 'baixo') {
      // água: ondas e o reflexo do fogo
      for (let y = 0; y < H; y += 4) { if (y > DT - 4 && y < DB + 4) continue; for (let x = 0; x < W; x += 16) R(x + Math.round(Math.sin(f * .04 + y * .5 + x * .1) * 3), y, 5, 1, '#1f3a4a'); }
      [[40, 12], [200, 18], [130, 30], [300, 24]].forEach(([x, y], i) => { const a = .25 + .15 * Math.sin(f * .2 + i); for (let k = 0; k < 4; k++) R(x - 8 + Math.sin(f * .1 + k) * 3, y + k * 2, 16 - k * 3, 1, 'rgba(255,140,60,' + a + ')'); });
      // luz vermelha dos pilares
      if ((f >> 4) % 2) [64, 248].forEach(x => [DT - 11, DB - 1].forEach(y => R(x + 7, y + 4, 2, 2, '#ff3b2f')));
      // marcas das explosões no asfalto
      P.marcas.forEach(d => { const g = c.createRadialGradient(O + d.x, d.y, 0, O + d.x, d.y, 10); g.addColorStop(0, 'rgba(10,8,8,' + d.a + ')'); g.addColorStop(1, 'rgba(10,8,8,0)'); c.fillStyle = g; c.fillRect(O + d.x - 10, d.y - 6, 20, 12); d.a = Math.max(.25, d.a - .0004); });
      // cancela do pedágio: sobe quando ele filtra ou passa perto
      const zx = z.x + 8 - O, zy = z.y + 15, perto = z.fx === 'filter' || (Math.abs(zx - 160) < 30 && Math.abs(zy - 79) < 24);
      P.cancela += ((perto ? 1 : 0) - P.cancela) * .08;
      const L = Math.round(32 * (1 - P.cancela) + 4);
      for (let i = 0; i < L; i++) R(167, 59 + i, 2, 1, (i >> 2) % 2 ? '#f6f1e6' : '#ff3b2f');
      R(166, 55, 4, 3, perto ? '#3fd17a' : '#ff3b2f');
      // painel do pórtico parado: letreiro âmbar passando
      if (z.fx !== 'capture' && this.state.zphase !== 'updating' && this.state.zphase !== 'done')
        for (let i = 0; i < 6; i++) R(260 + ((i * 5 + (f >> 3)) % 24), 40 + (i % 2) * 4, 2, 2, (f >> 5) % 2 || i % 3 ? '#b8792a' : '#f2a23a');
      // carcaças pegando fogo
      [[26, 176, 0], [110, 70, Math.PI], [300, 108, Math.PI / 2]].forEach(([x, y, a]) => { blitRot(Component.PNCARRO, x, y, a, Object.assign({}, BASE, { A: '#2a2a2e', W: '#1d1e21', H: '#3a3f46' })); fogo(x + 2, y, 1); });
      // trânsito
      [{ y: 108, v: 1.6, o: 0, p: '#c0c4c9' }, { y: 174, v: -2.2, o: 120, p: '#1e3a8a' }, { y: 140, v: 1.1, o: 60, p: '#8c1420' }].forEach(q => {
        const x = ((f * q.v + q.o) % (W + 60) + W + 60) % (W + 60) - 30;
        c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(O + x - 10, q.y - 2, 22, 8);
        blitRot(Component.PNCARRO, x, q.y, q.v > 0 ? 0 : Math.PI, Object.assign({ A: q.p }, BASE));
      });
      // dois duelos: chegam como carros, viram robôs, brigam, explodem e vão embora como carros
      const pecas = [{ r0: 0, r1: 5, dx: 6, rot: .5 }, { r0: 5, r1: 10, dx: 0, rot: 0 }, { r0: 10, r1: 13, dx: -4, rot: .25 }, { r0: 13, r1: 18, dx: -8, rot: .5 }];
      const npc = n => {
        const { x, y, m, face, pal, soco = 0, lado = 1 } = n;
        if (m > .04 && m < .96) {
          sombra(x, y, 8); blitRot(Component.PNCARRO, x, y - 5, face, pal, Math.max(0, (m - .5) * 2));
          pecas.forEach((p, i) => {
            const ease = q => q < .5 ? 4 * q * q * q : 1 - Math.pow(-2 * q + 2, 3) / 2, q = ease(Math.max(0, Math.min(1, (m - i * .06) / (.9 - i * .06))));
            const oy = y - 18 + (p.r0 + p.r1) / 2, [ddx, ddy] = gira(p.dx, 0, face);
            peca(Component.PNROBO, p.r0, p.r1, x + ddx * q, oy + (y - 5 + ddy - oy) * q - Math.sin(q * Math.PI) * 6, Math.round(p.rot * 4 * q) * Math.PI / 2, pal, 1 - Math.max(0, (q - .85) / .15));
          });
          if (Math.abs(m - .5) < .08) faiscas(x, y - 9, 6, pal.E, f);
        } else if (m >= .96) {
          const sv = Math.abs(Math.sin(face)) > .5; c.fillStyle = 'rgba(0,0,0,.35)'; c.fillRect(O + x - (sv ? 4 : 11) + 1, y - 5 - (sv ? 11 : 4) + 2, sv ? 8 : 22, sv ? 22 : 8);
          blitRot(Component.PNCARRO, x, y - 5, face, pal);
        } else {
          sombra(x, y, 7); blit(Component.PNROBO, x - 8, y - 18, pal);
          if (soco > 0) { R(lado > 0 ? x + 7 : x - 7 - soco, y - 11, soco, 2, pal.A); R(lado > 0 ? x + 7 + soco : x - 9 - soco, y - 12, 2, 3, pal.K); }
          R(x - 2, y - 16, 4, 1, 'rgba(255,255,255,.15)');
        }
      };
      [{ y: 112, mx: 104, a: 0, b: 1, off: 0 }, { y: 182, mx: 168, a: 2, b: 3, off: 300 }].forEach(D => {
        const t = (f + D.off) % 600, A = { pal: NPAL[D.a], y: D.y, face: 0 }, B = { pal: NPAL[D.b], y: D.y, face: Math.PI }, ax = D.mx - 13, bx = D.mx + 13;
        if (t < 130) { const k = t / 130; A.x = -30 + (ax + 30) * k; B.x = W + 30 - (W + 30 - bx) * k; A.m = B.m = 1; }
        else if (t < 165) { A.x = ax; B.x = bx; A.m = B.m = 1 - (t - 130) / 35; }
        else if (t < 400) {
          A.x = ax; B.x = bx; A.m = B.m = 0; A.lado = 1; B.lado = -1;
          const s = (t - 165) % 36, vez = Math.floor((t - 165) / 36) % 2, soco = s < 14 ? Math.round(Math.sin(s / 14 * Math.PI) * 6) : 0, acerto = s > 5 && s < 10;
          if (vez === 0) { A.soco = soco; if (acerto) B.x += 2; } else { B.soco = soco; if (acerto) A.x -= 2; }
          if (acerto) faiscas(D.mx, D.y - 11, 12, vez ? B.pal.E : A.pal.E, f);
          if (s === 20 && Math.floor((t - 165) / 36) % 3 === 2) { const de = vez ? B : A; P.tiros.push({ x: de.x, y: D.y - 15, vx: vez ? -3.5 : 3.5, col: de.pal.E, l: 40 }); }
          A.y += (f >> 3) % 2; B.y += ((f >> 3) + 1) % 2;
          if (t === 390) bum(D.mx, D.y - 2);
        }
        else if (t < 435) { A.x = ax; B.x = bx; A.m = B.m = (t - 400) / 35; A.face = Math.PI; B.face = 0; }
        else if (t < 560) { const k = (t - 435) / 125; A.x = ax - (ax + 40) * k; B.x = bx + (W + 40 - bx) * k; A.m = B.m = 1; A.face = Math.PI; B.face = 0; }
        else return;
        [A, B].sort((p, q) => p.y - q.y).forEach(npc);
      });
    } else {
      // tiros
      P.tiros = P.tiros.filter(l => l.l-- > 0);
      P.tiros.forEach(l => { l.x += l.vx; R(l.x - 3, l.y, 7, 1, l.col); R(l.x - 4, l.y - 1, 9, 3, 'rgba(255,255,255,.15)'); if (l.l === 1) bum(l.x, l.y + 12); });
      // de vez em quando uma explosão na pista, longe do Bumblebee
      if (f % 170 === 60) {
        const bx = z.x + 8 - O, by = z.y + 15; let ex, ey, n = 0;
        do { ex = 20 + rr(f + n) * 280; ey = DT + 14 + rr(f * 3 + n) * (DB - DT - 24); n++; } while (Math.hypot(ex - bx, ey - by) < 40 && n < 8);
        if (Math.hypot(ex - bx, ey - by) >= 40) bum(ex, ey);
      }
      P.explosoes = P.explosoes.filter(e => e.t < 26);
      P.explosoes.forEach(e => {
        e.t++; const r = Math.min(15, e.t * 1.5), a = 1 - e.t / 26, g = c.createRadialGradient(O + e.x, e.y - 3, 0, O + e.x, e.y - 3, r);
        g.addColorStop(0, 'rgba(255,250,220,' + a + ')'); g.addColorStop(.45, 'rgba(255,160,60,' + a + ')'); g.addColorStop(1, 'rgba(200,60,30,0)');
        c.fillStyle = g; c.fillRect(O + e.x - r, e.y - 3 - r, r * 2, r * 2);
        if (e.t % 3 === 0) fumaca(e.x + (rr(e.t + e.x) - .5) * 8, e.y - 4, true);
      });
      P.destrocos = P.destrocos.filter(d => d.l-- > 0);
      P.destrocos.forEach(d => { d.x += d.vx * .6; d.y += d.vy * .6; d.z += d.vz; d.vz -= .12; if (d.z < 0) { d.z = 0; d.vz *= -.3; d.vx *= .6; d.vy *= .6; } R(d.x, d.y - d.z, 1, 1, d.l > 22 ? '#ffcf7a' : '#5a616b'); });
      // fumaça por cima de tudo e brasas subindo
      P.fumaca = P.fumaca.filter(s => s.a > 0);
      P.fumaca.forEach(s => { s.x += s.vx; s.y += s.vy; s.r += .05; s.a -= .003; c.fillStyle = 'rgba(40,36,42,' + s.a + ')'; c.beginPath(); c.arc(O + s.x, s.y, s.r, 0, 6.283); c.fill(); });
      P.brasas.forEach(e => { e.y -= e.s; e.x += Math.sin(f * .03 + e.p) * .2 + .1; if (e.y < 0) { e.y = H; e.x = rr(f + e.p) * W; } if ((f + e.p * 10 | 0) % 5) R(((e.x % W) + W) % W, e.y, 1, 1, e.p > 3 ? '#ffb15a' : '#ff6a2a'); });
    }
    c.restore();
  }
  paintArena(c) {""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print(f"Vila 02 virou a ponte do Bumblebee em {caminho}")
