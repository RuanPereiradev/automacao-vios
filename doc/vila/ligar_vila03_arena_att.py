"""Vila 03 (Albi) ganha a arena nova de albi/mascote/fundo-arena-albi.html (a versão com a luta).

A plataforma com as quatro torres sai; entra a cena do arquivo do usuário, adaptada à vila
(320×224 em vez de 320×180: o campo ganha 26 px, onde o Albi anda, e o lago desce até o fim, atrás
da caixa de diálogo):
- céu com sol e nuvens, montanhas, mata, campo, a casa em domo (com anexo e torre de observação),
  a árvore grande e o lago com reflexos e brilhos;
- no céu, o dragão serpenteando e os dois lutadores: chegam voando com aura, trocam socos e chutes,
  carregam e disparam os raios, que se chocam e explodem; o céu escurece, a casa e a árvore ficam em
  ruínas pegando fogo; os dois descem, carregam blocos e reconstroem a casa, a muda cresce de novo,
  eles comemoram e voltam para o céu (ciclo de 480 quadros, ~8 s);
- os postos do Albi (os eventos, as falas e o painel não mudam):
  **Doca 01 · Albi** = porta da casa em domo; **Receptor TXT** = porta do anexo (as faíscas da
  leitura saem do telhado dele); **Conferência** = a janela da torre de observação, em cima da casa
  (as linhas da conferência rolam nela; com a casa em ruínas não aparecem); **Torre Sonar** = mastro
  com antena, novo, no campo à direita (a luz da ponta pisca quando ele entra no Sonar ou pesquisa).
O Albi anda só no campo, entre a casa e o lago (linhas 6 a 8 da vila, colunas 1 a 18 da Vila 03),
sem passar pelo tronco da árvore nem pelo mastro. A parte animada só é desenhada com a Vila 02, 03
ou 04 na tela; nas outras fica a cena parada (sem o dragão e os lutadores).

uso: python3 doc/vila/ligar_vila03_arena_att.py bot/vila/vila.html
(depois de todos os outros, inclusive o ligar_vila02_ponte.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "cenaArena(c, f, estatico)" in t:
    sys.exit("a Vila 03 já é a arena nova")
if "arena: recorte" not in t or "drawPonte(c, f, parte)" not in t:
    sys.exit("rode antes o ligar_vila03_arena.py e o ligar_vila02_ponte.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


def troca_bloco(inicio, fim, novo):
    """Troca o texto de `inicio` (incluso) até `fim` (não incluso)."""
    global t
    assert t.count(inicio) == 1, ("início não encontrado (ou repetido)", inicio[:90])
    a = t.index(inicio)
    b = t.index(fim, a)
    t = t[:a] + novo + t[b:]


# 1) onde ele pode andar: o campo entre a casa e o lago (sem o tronco da árvore e o mastro)
troca("this.blocked[y][x] = !(y >= 8 && y <= 10 && x >= 43 && x <= 56);",
      "this.blocked[y][x] = !(y >= 6 && y <= 8 && x >= 41 && x <= 58) || (y === 6 && x >= 52 && x <= 54) || (y === 8 && x >= 57);")
troca("this.a = { x: 43 * 16, y: 160,", "this.a = { x: 43 * 16, y: 112,")

# 2) os postos: porta da casa, porta do anexo, embaixo da torre de observação e o mastro
troca("O = 40, HOME = [O + 3, 10], REC = [O + 4, 8], OFI = [O + 8, 8], TOR = [O + 16, 10]",
      "O = 40, HOME = [O + 6, 6], REC = [O + 2, 6], OFI = [O + 8, 7], TOR = [O + 16, 8]")
troca("""    const pos = ap === 'recebendo' ? [O + 4, 8] : ap === 'conferindo' ? [O + 8, 8] : (ap === 'entrando' || ap === 'preenchendo') ? [O + 16, 10] : [O + 3, 10];""",
      """    const pos = ap === 'recebendo' ? [O + 2, 6] : ap === 'conferindo' ? [O + 8, 7] : (ap === 'entrando' || ap === 'preenchendo') ? [O + 16, 8] : [O + 6, 6];""")
troca("pts = [[46, 9], [52, 8], [54, 10], [49, 10], [44, 9], [50, 9]]",
      "pts = [[44, 7], [50, 8], [55, 7], [48, 6], [42, 8], [52, 8]]")

# 3) efeitos do Albi nos lugares novos (a luz do Sonar fica onde estava: 281, 97 = ponta do mastro)
troca("if (afx === 'check') for (let i = 0; i < 5; i++) R(O3 + 125, 101 + ((i * 3 + (f >> 2)) % 10), 4 + ((i * 7 + (f >> 3)) % 16), 1,",
      "if (!this.arenaInteira(f)) { /* casa em ruínas: sem janela */ }\n"
      "      else if (afx === 'check') for (let i = 0; i < 5; i++) R(O3 + 123, 57 + ((i * 3 + (f >> 2)) % 5), 2 + ((i * 7 + (f >> 3)) % 9), 1,")
troca("for (let i = 0; i < 4; i++) R(O3 + 125, 101 + i * 3, 12 + (i * 5) % 5, 1, '#9aa0a8');",
      "for (let i = 0; i < 3; i++) R(O3 + 123, 57 + i * 2, 6 + (i * 5) % 4, 1, '#9aa0a8');")
troca("R(O3 + 141, 101, 2, 2,", "R(O3 + 131, 57, 2, 2,")
troca("R(O3 + 62 + ((t0 * 3 + i * 11) % 9), 66 + ((t0 + i * 5) % 8),", "R(O3 + 30 + ((t0 * 3 + i * 11) % 9), 66 + ((t0 + i * 5) % 8),")
troca("(O3 + 134 - a.x - 8) * k, ay + 6 + (106 - ay - 6) * k", "(O3 + 128 - a.x - 8) * k, ay + 6 + (59 - ay - 6) * k")

# 4) placas
troca("plaques.push(P(43.5, 11.6, 'Doca 01 · Albi'), P(44.1, 3.4, 'Receptor TXT'), P(48.4, 5.3, 'Conferência'), P(57.6, 5.0, 'Torre Sonar'));",
      "plaques.push(P(46.8, 5.0, 'Doca 01 · Albi'), P(42.3, 3.9, 'Receptor TXT'), P(48.0, 2.3, 'Conferência'), P(57.6, 5.3, 'Torre Sonar'));")

# 5) a cena: sai a plataforma (ARENA antiga, arenaBorda, paintArena e drawArena), entra a do arquivo
troca_bloco("  // arena (albi/mascote/fundo-arena-albi.html): x local 0–319 + 640; céu até y 96; plataforma de 124 a 180\n",
            "  paintPonte(c) {", "")
CENA = r"""  // arena do Albi (albi/mascote/fundo-arena-albi.html), em x local 0–319 (a Vila 03 começa em x 640).
  // A cena do arquivo é 320×180; aqui o campo ganha LY = 26 px (onde o Albi anda) e o lago vai até 224.
  // Ciclo de 480 quadros: luta no céu, raios, explosão, ruínas, reconstrução.
  static ARENA = { O: 640, LY: 26, CICLO: 480 };
  arenaInteira(f) { const k = f % Component.ARENA.CICLO; return k < 232 || k >= 440; }  // a casa está de pé (com a torre)
  paintArena(c) {
    c.save(); c.translate(Component.ARENA.O, 0); c.beginPath(); c.rect(0, 0, 320, 224); c.clip();  // arena: recorte
    this.cenaArena(c, 0, true);
    c.restore();
  }
  drawArena(c, f) {
    if (this.state.village < 1 || this.state.village > 3) return;  // só com a Vila 02, 03 ou 04 na tela
    c.save(); c.translate(Component.ARENA.O, 0); c.beginPath(); c.rect(0, 0, 320, 224); c.clip();
    this.cenaArena(c, f, false);
    c.restore();
  }
  cenaArena(c, f, estatico) {
    const W = 320, H = 224, LY = Component.ARENA.LY, CYCLE = Component.ARENA.CICLO;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h)); };
    // estado de destruição: 0 intacto … 1 destruído; reconstrução de 330 a 450
    function ruin(f) { const cyc = f % CYCLE; if (cyc < 225) return 0; if (cyc < 240) return (cyc - 225) / 15; if (cyc < 330) return 1; if (cyc < 450) return 1 - (cyc - 330) / 120; return 0; }
    function rebuild(f) { const cyc = f % CYCLE; return cyc < 330 || cyc >= 450 ? -1 : (cyc - 330) / 120; }
    function cloud(x, y, w) { R(x, y + 3, w, 5, '#ffffff'); R(x + 3, y, w - 6, 3, '#ffffff'); R(x + w * .3, y - 2, w * .3, 2, '#ffffff'); R(x + 1, y + 8, w - 2, 1, '#d8ebf7'); }
    function mountain(x, w, h, col, colShade) {
      for (let i = 0; i < h; i++) { const ww = w * ((i + 1) / h); R(x + (w - ww) / 2, 98 - h + i, ww, 1, col); R(x + (w - ww) / 2 + ww * .55, 98 - h + i, ww * .45, 1, colShade); }
    }
    function treeGrow(x, y, g, f) {
      // muda plantada que cresce: tronco sobe, copa infla
      const th = Math.round(26 * Math.min(1, g / .5)), cs = Math.max(0, (g - .3) / .7);
      R(x - 5, y - 2, 11, 2, '#5a3e22'); R(x - 2, y - th, 5, th, '#6e5230'); R(x - 1, y - th, 2, th, '#8a6a3a');
      if (g < .2) { R(x - 1, y - 6 - g * 20, 3, 2, '#58b05e'); R(x - 3, y - 5 - g * 20, 2, 1, '#3f8f4a'); R(x + 2, y - 5 - g * 20, 2, 1, '#3f8f4a'); }
      if (cs > 0) { const blobs = [[-20, -40, 20, 12], [-6, -50, 22, 12], [8, -42, 20, 12], [-26, -32, 16, 10], [12, -32, 18, 10], [-12, -36, 26, 10]]; blobs.forEach(([dx, dy, w, hh]) => { const ww = Math.round(w * cs), hh2 = Math.round(hh * cs), cx = x + dx + w / 2, cy = y + dy + hh / 2; R(cx - ww / 2, cy - hh2 / 2, ww, hh2, '#3f8f4a'); if (cs > .6) R(cx - ww / 2 + 2, cy - hh2 / 2 - 2, ww - 4, 3, '#58b05e'); }); if (cs > .9) R(x - 12, y - 54, 14, 3, '#7fd078'); }
      // regador: gotas caindo na muda no início
      if (g < .35) for (let k = 0; k < 4; k++) { const t = (f * 1.2 + k * 6) % 16; R(x - 6 + k * 3, y - 24 + t, 1, 2, '#5ad8ff'); }
    }
    function tree(x, y, f) {
      const d = ruin(f), rb = rebuild(f), sway = Math.round(Math.sin(f * .03) * 1);
      if (rb >= .5) { const g = (rb - .5) / .5; treeGrow(x, y, g, f); return; }
      if (d > .5) { // toco queimado e galhos secos
        R(x - 2, y - 14, 5, 14, '#2a2420'); R(x - 1, y - 14, 2, 14, '#3a322c'); R(x - 5, y - 2, 11, 2, '#2a2420');
        R(x - 6, y - 18, 4, 5, '#2a2420'); R(x + 3, y - 22, 3, 9, '#2a2420'); R(x - 10, y - 20, 5, 2, '#2a2420'); R(x + 5, y - 24, 6, 2, '#2a2420');
        // brasas e fumaça
        if ((f >> 2) % 2) { R(x - 4, y - 17, 1, 1, '#ff8c3c'); R(x + 4, y - 21, 1, 1, '#ffd47a'); }
        for (let p = 0; p < 4; p++) { const t = ((f * .5 + p * 9) % 30); c.fillStyle = `rgba(90,80,75,${(1 - t / 30) * .5})`; c.fillRect(x - 2 + p * 2 + Math.sin(f * .05 + p) * 2, y - 22 - t, 3, 3); }
        return;
      }
      R(x - 2, y - 26, 5, 26, '#6e5230'); R(x - 1, y - 26, 2, 26, '#8a6a3a'); R(x - 5, y - 2, 11, 2, '#5a3e22');
      R(x - 6, y - 30, 4, 6, '#6e5230'); R(x + 3, y - 32, 4, 8, '#6e5230');
      const blobs = [[-20, -40, 20, 12], [-6, -50, 22, 12], [8, -42, 20, 12], [-26, -32, 16, 10], [12, -32, 18, 10], [-12, -36, 26, 10]];
      blobs.forEach(([dx, dy, w, h], k) => { const s = k % 2 ? sway : 0; R(x + dx + s, y + dy, w, h, '#3f8f4a'); R(x + dx + 2 + s, y + dy - 2, w - 4, 3, '#58b05e'); R(x + dx + 3 + s, y + dy + h - 2, w - 6, 2, '#2e6e3a'); });
      R(x - 12, y - 54, 14, 3, '#7fd078');
    }
    function houseBuild(x, y, p, f) {
      // 0-.25 limpa escombros e levanta anexo · .25-.6 domo sobe · .6-.8 torre · .8-1 janelas e arbustos
      const e = Math.min;
      if (p < .25) { const a = 1 - p / .25; [[x - 40, 0], [x + 118, 1], [x + 130, 0], [x - 48, 1]].forEach(([bx, k]) => { c.fillStyle = `rgba(201,160,112,${a})`; c.fillRect(bx, y - 3 - k, 6 + k * 2, 3 + k); }); }
      const pa = e(1, p / .25), ah = Math.round(30 * pa);
      R(x - 30, y - ah, 26, ah, '#f2d7b0'); if (pa >= 1) { R(x - 28, y - 34, 22, 4, '#f2d7b0'); R(x - 26, y - 36, 18, 2, '#f2d7b0'); R(x - 30, y - 30, 26, 1, '#c9a070'); R(x - 22, y - 24, 10, 24, '#b8713c'); R(x - 20, y - 22, 6, 1, '#8c4f28'); R(x - 14, y - 12, 1, 2, '#e8b923'); }
      const pd = Math.max(0, e(1, (p - .25) / .35)), rows = Math.round(46 * pd);
      R(x + 2, y - 10, 106, 10, '#f4d9b2'); R(x + 2, y, 106, 1, '#c9a070');
      for (let j = 46 - rows; j < 46; j++) { const t = j / 46, w = Math.sqrt(1 - Math.pow(1 - t, 2)) * 110; R(x + 55 - w / 2, y - 46 + j, w, 1, j < 4 ? '#c8641e' : '#f4d9b2'); }
      if (pd > 0 && pd < 1) { const j = 46 - rows - 1, t = Math.max(0, j) / 46, w = Math.sqrt(1 - Math.pow(1 - t, 2)) * 110, n = Math.floor(((p - .25) / .35 * 46 % 1) * (w / 6)); for (let k = 0; k < n; k++) R(x + 55 - w / 2 + k * 6, y - 46 + j, 5, 1, '#f4d9b2'); }
      if (p > .2 && p < .85) { const ah2 = Math.round(50 * e(1, (p - .2) / .1)); [x - 4, x + 112].forEach(sx => { R(sx, y - ah2, 1, ah2, '#8a6a3a'); R(sx + 4, y - ah2, 1, ah2, '#8a6a3a'); for (let k = 0; k < ah2; k += 10) R(sx, y - k - 1, 5, 1, '#a97b43'); }); }
      const pt = Math.max(0, e(1, (p - .6) / .2)); if (pt > 0) { const th = Math.round(16 * pt); R(x + 64, y - 42 - th, 20, th, '#f4d9b2'); if (pt >= 1) { R(x + 62, y - 62, 24, 4, '#c8641e'); R(x + 68, y - 54, 12, 6, '#5ad8ff'); R(x + 68, y - 54, 12, 1, '#2f7fe0'); } }
      if (p > .8) { const pw = (p - .8) / .2; if (pw > .2) { R(x + 14, y - 22, 26, 6, '#2f7fe0'); R(x + 16, y - 21, 22, 2, '#8fd0f5'); } if (pw > .5) { R(x + 70, y - 22, 26, 6, '#2f7fe0'); R(x + 72, y - 21, 22, 2, '#8fd0f5'); } if (pw > .35) { R(x + 46, y - 14, 18, 14, '#f8e6c8'); R(x + 48, y - 12, 14, 12, '#b8713c'); } if (pw > .7) [[x - 6, 0], [x + 108, 0], [x + 118, 2]].forEach(([bx, dy]) => { R(bx, y - 6 + dy, 12, 6, '#2e6e3a'); R(bx + 2, y - 8 + dy, 8, 3, '#3f8f4a'); }); }
      for (let k = 0; k < 5; k++) { const t = ((f * .6 + k * 9) % 20); R(x + 10 + k * 22 + Math.sin(f * .1 + k) * 2, y - 2 - t, 1, 1, `rgba(244,217,178,${1 - t / 20})`); }
    }
    function house(f) {
      // casa em domo bege com janelas azuis (a porta é a Doca 01 do Albi; a janela da torre, a Conferência)
      const x = 54, y = 110, d = ruin(f), rb = rebuild(f);
      if (rb >= 0 && rb >= .15) { houseBuild(x, y, (rb - .15) / .85, f); return; }
      if (d > .5) { // ruínas: paredes quebradas, escombros e fogo
        R(x - 30, y - 14, 26, 14, '#d9c09a'); R(x - 30, y - 18, 8, 4, '#d9c09a'); R(x - 14, y - 20, 6, 6, '#d9c09a'); R(x - 22, y - 10, 10, 10, '#4a3a30');
        for (let j = 0; j < 20; j++) { const t = j / 20, w = Math.sqrt(1 - Math.pow(1 - t, 2)) * 110; R(x + 55 - w / 2, y - 20 + j, w, 1, '#d9c09a'); }
        R(x + 20, y - 18, 14, 10, '#2a2420'); R(x + 66, y - 14, 18, 8, '#2a2420'); R(x + 44, y - 20, 6, 20, '#4a3a30');
        for (let k = 0; k < 7; k++) R(x + 8 + k * 14, y - 6 - (k % 3) * 3, 2, 6 + (k % 3) * 3, '#8c7a60');
        [[x - 40, 0], [x + 118, 1], [x + 130, 0], [x - 48, 1], [x + 20, 2], [x + 96, 2]].forEach(([bx, k]) => { R(bx, y - 3 - k, 6 + k * 2, 3 + k, '#c9a070'); R(bx + 1, y - 4 - k, 3, 1, '#f4d9b2'); });
        R(x + 40, y - 4, 16, 4, '#c8641e'); R(x + 60, y - 30, 8, 10, '#d9c09a');
        const dim = rb >= 0 ? 1 - rb / .15 : 1; // fogo apagando no início da reconstrução
        if (dim > 0) for (let p = 0; p < 7; p++) { if (p / 7 > dim) continue; const fl = (f + p * 5) % 7, bx = x + 4 + p * 16; R(bx, y - 8 - fl / 2, 3, 3 + fl / 2, p % 2 ? '#ff8c3c' : '#ffd47a'); R(bx + 1, y - 9 - fl / 2, 1, 2, '#fff1a8'); }
        for (let p = 0; p < 12; p++) { const t = ((f * .5 + p * 11) % 50), bx = x + (p * 19) % 110 + Math.sin(f * .04 + p) * 4; c.fillStyle = `rgba(80,72,68,${(1 - t / 50) * .55 * dim})`; c.fillRect(bx, y - 20 - t, 4 + t / 8, 4 + t / 8); }
        return;
      }
      R(x - 30, y - 30, 26, 30, '#f2d7b0'); R(x - 28, y - 34, 22, 4, '#f2d7b0'); R(x - 26, y - 36, 18, 2, '#f2d7b0'); R(x - 30, y - 30, 26, 1, '#c9a070');
      R(x - 22, y - 24, 10, 24, '#b8713c'); R(x - 20, y - 22, 6, 1, '#8c4f28'); R(x - 14, y - 12, 1, 2, '#e8b923');
      for (let j = 0; j < 46; j++) { const t = j / 46, w = Math.sqrt(1 - Math.pow(1 - t, 2)) * 110; R(x + 55 - w / 2, y - 46 + j, w, 1, j < 4 ? '#c8641e' : '#f4d9b2'); }
      R(x + 2, y - 10, 106, 10, '#f4d9b2'); R(x + 2, y, 106, 1, '#c9a070');
      R(x + 64, y - 58, 20, 16, '#f4d9b2'); R(x + 62, y - 62, 24, 4, '#c8641e'); R(x + 68, y - 54, 12, 6, '#5ad8ff'); R(x + 68, y - 54, 12, 1, '#2f7fe0');
      R(x + 14, y - 22, 26, 6, '#2f7fe0'); R(x + 16, y - 21, 22, 2, '#8fd0f5');
      R(x + 70, y - 22, 26, 6, '#2f7fe0'); R(x + 72, y - 21, 22, 2, '#8fd0f5');
      R(x + 46, y - 14, 18, 14, '#f8e6c8'); R(x + 48, y - 12, 14, 12, '#b8713c');
      [[x - 6, 0], [x + 108, 0], [x + 118, 2]].forEach(([bx, dy]) => { R(bx, y - 6 + dy, 12, 6, '#2e6e3a'); R(bx + 2, y - 8 + dy, 8, 3, '#3f8f4a'); });
    }
    function sonar() {
      // Torre Sonar: mastro com antena no campo à direita (a luz da ponta, em 281,97, é desenhada com o Albi)
      R(273, 143, 18, 2, 'rgba(40,70,40,.35)');
      R(275, 140, 14, 3, '#5a6c80'); R(276, 139, 12, 1, '#8ea3b8');
      R(281, 101, 2, 38, '#c7d6e4'); R(282, 101, 1, 38, '#8ea3b8');
      for (let y = 110; y < 138; y += 6) R(279, y, 6, 1, '#8ea3b8');
      R(276, 104, 12, 2, '#d4d8de'); R(277, 106, 10, 1, '#8ea3b8'); R(280, 99, 4, 2, '#5a6c80');
    }
    function lake(f) {
      const T = 128 + LY;
      for (let y = T; y < H; y++) { const t = (y - T) / (180 - T); R(0, y, W, 1, t < .25 ? '#3c8ee8' : t < .6 ? '#2f7fe0' : '#2468c8'); }
      // reflexo da casa e da árvore (borrado)
      R(26, T + 2, 136, 14, 'rgba(244,217,178,.35)'); R(190, T + 2, 40, 20, 'rgba(63,143,74,.35)');
      // brilhos ondulando
      for (let k = 0; k < 40; k++) { const x = (k * 53 + f * (.3 + (k % 3) * .2)) % W, y = T + 4 + (k * 29) % 44; const on = Math.sin(f * .1 + k) > .3; if (on) R(x, y, 3 + (k % 3), 1, 'rgba(255,255,255,.55)'); }
      // margem
      R(0, T - 4, W, 4, '#b8713c'); R(0, T - 2, W, 1, '#8c4f28'); R(0, T - 5, W, 1, '#58b05e');
      for (let x = 0; x < W; x += 9) R(x, T - 2, 4, 2, '#d9a071');
      // pedras
      R(150, T - 10, 14, 6, '#c9a070'); R(152, T - 12, 10, 2, '#e8c9a0'); R(236, T - 2, 20, 6, '#c9a070'); R(238, T - 4, 16, 2, '#e8c9a0'); R(244, T + 2, 10, 4, '#b8713c');
    }
    // ---------- lutadores ----------
    const F1 = { // gi laranja, faixa azul, cabelo preto espetado
      idle: ['...K.K.K...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..OOOOOOO..', '.SOOOOOOOS.', '.SOOBBBOOS.', '..OOOOOOO..', '..OO...OO..', '..OO...OO..', '..WW...WW..', '.BBB...BBB.'],
      punch: ['...K.K.K...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..OOOOOOOSS', '.SOOOOOOOSS', '.SOOBBBOO..', '..OOOOOOO..', '..OO...OO..', '..OO...OO..', '..WW...WW..', '.BBB...BBB.'],
      kick: ['...K.K.K...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..OOOOOOO..', '.SOOOOOOOS.', '.SOOBBBOOS.', '..OOOOOOO..', '..OO..OOOOO', '..OO....BBB', '..WW.......', '.BBB.......'],
      pal: { K: '#1d1e21', S: '#f1c9a5', E: '#1d1e21', O: '#ff8c3c', B: '#1d4ea0', W: '#f2efe6' }
    };
    const F2 = { // macacão azul, luvas e botas brancas, cabelo em chama
      idle: ['...KKKKK...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..SBBBBBS..', '.WWBBBBBWW.', '.WWBBBBBWW.', '..BBBBBBB..', '..BB...BB..', '..BB...BB..', '..WW...WW..', '.WWW...WWW.'],
      punch: ['...KKKKK...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..SBBBBBSWW', '.WWBBBBBSWW', '.WWBBBBB...', '..BBBBBBB..', '..BB...BB..', '..BB...BB..', '..WW...WW..', '.WWW...WWW.'],
      kick: ['...KKKKK...', '..KKKKKKK..', '..KKSSSKK..', '...SSESS...', '...SSSSS...', '....SSS....', '..SBBBBBS..', '.WWBBBBBWW.', '.WWBBBBBWW.', '..BBBBBBB..', '..BB..BBBBB', '..BB....WWW', '..WW.......', '.WWW.......'],
      pal: { K: '#2a1a2e', S: '#f1c9a5', E: '#1d1e21', B: '#1d4ea0', W: '#f2efe6' }
    };
    function sprite(rows, x, y, pal, flip, s = 1) {
      const w = rows[0].length;
      rows.forEach((r, j) => r.split('').forEach((ch, i) => { if (ch !== '.') R(x + (flip ? w - 1 - i : i) * s, y + j * s, s, s, pal[ch]); }));
    }
    function aura(x, y, w, h, f, col) {
      // chamas de aura ao redor do corpo (contorno ondulante)
      for (let j = -3; j < h + 2; j += 2) {
        const n = Math.sin(f * .3 + j * .7), m = Math.cos(f * .25 + j * .9);
        const a = 2 + Math.round(Math.abs(n) * 3), b = 2 + Math.round(Math.abs(m) * 3);
        R(x - a, y + j, a, 2, col); R(x + w, y + j, b, 2, col);
      }
      for (let i = -2; i < w + 2; i += 3) { const t = 3 + Math.round(Math.abs(Math.sin(f * .35 + i)) * 5); R(x + i, y - t, 2, t, col); }
      R(x - 1, y - 1, w + 2, h + 2, 'rgba(255,241,168,.18)');
    }
    function beam(x0, x1, y, f, col, core, dir) {
      // raio de energia com ondulação, fluxo interno e bola pulsando na origem
      const l = Math.min(x0, x1), w = Math.abs(x1 - x0);
      for (let i = 0; i < w; i++) {
        const d = Math.abs(dir > 0 ? i : w - 1 - i);
        const wave = Math.sin(f * .25 - d * .22) * 1.2, th = 3 + Math.sin(f * .18 - d * .12) * .8 + Math.min(d, 10) * .15;
        const yy = y + wave;
        R(l + i, yy - th, 1, th * 2, col);
        R(l + i, yy - th * .45, 1, th * .9, core);
        const flow = (d - f * 3) % 7; if (flow < 1.5 && flow > -1.5) R(l + i, yy - 1, 1, 2, '#ffffff');
      }
      for (let k = 0; k < 5; k++) { const d = (f * 2 + k * 17) % Math.max(1, w), up = k % 2 ? -1 : 1; R(l + (dir > 0 ? d : w - d), y + up * (5 + (f + k) % 4), 1, 1, core); }
      const bx = dir > 0 ? x0 : x0 - 1, r = 5 + Math.sin(f * .3) * 1.5;
      const g = c.createRadialGradient(bx, y, 0, bx, y, r + 3); g.addColorStop(0, '#ffffff'); g.addColorStop(.45, core); g.addColorStop(1, 'rgba(0,0,0,0)');
      c.fillStyle = g; c.fillRect(bx - r - 3, y - r - 3, r * 2 + 6, r * 2 + 6);
    }
    function dragon(f) {
      // dragão serpentino: a cabeça percorre um caminho e o corpo segue em onda
      const T = f * .012, path = t => [160 + Math.cos(t) * 140, 46 + Math.sin(t * 2) * 26];
      const N = 150, pts = [];
      for (let i = 0; i < N; i++) { const [x, y] = path(T - i * .009); pts.push([x, y + Math.sin(f * .08 + i * .16) * 3]); }
      const [hx, hy] = pts[0], [nx] = pts[6], dir = hx >= nx ? 1 : -1;
      for (let i = 0; i < N; i += 5) R(pts[i][0] - 2, 120 + Math.sin(i * .1) * 2, 4, 1, 'rgba(20,50,20,.18)');
      for (let i = N - 1; i >= 6; i--) {
        const [x, y] = pts[i], t = i / N, w = Math.max(2, Math.round(10 * (1 - t * .8)));
        R(x - w / 2, y - w / 2, w, w, (i >> 2) % 2 ? '#2f9e44' : '#3fbf57');
        if (w >= 4) { R(x - w / 2 + 1, y + w / 2 - 3, w - 2, 2, '#e8c9a0'); R(x - w / 2 + 1, y + w / 2 - 1, w - 2, 1, '#c8102e'); }
        if (i % 6 === 0 && w >= 3) { R(x - 1, y - w / 2 - 3, 2, 3, '#1f6e2e'); }
      }
      [22, 50, 84, 112].forEach((i, k) => { const [x, y] = pts[i]; const up = Math.floor((f + k * 7) / 10) % 2, s = k % 2 ? 1 : -1; R(x + s * 4, y + 3 - up, 3, 5, '#2f9e44'); R(x + s * 4 - 1, y + 8 - up, 5, 1, '#f2efe6'); });
      const CAB = [
        '.......KK....KK.......', '......KK.....KK.......', '....GGKKGGGGGKK.......', '...GGGGGGGGGGGGG......', '..GGGGGGGGGGGGGGG.....',
        '.GGGGRRGGGGGGGGGGG....', '.GGGGRRGGGGGGGGGGGG...', 'GGGGGGGGGGGGGGGGGGGGG.', 'GGGGGGGGGGGGGGGGGGGGGG', '.GGGGGGGGGGGGGGGGGGGG.',
        '..GGGWWWWWWWWGGGGGGG..', '..GGGWDDDDDDWGGGGGG...', '...GGWWWWWWWWGGGG.....', '....GGGGGGGGGGG.......', '......GGGGGGG.........'
      ];
      const pal = { G: '#3fbf57', R: (f >> 3) % 2 ? '#ff3b2f' : '#c8102e', K: '#b68235', W: '#f2efe6', D: '#8c1420' };
      CAB.forEach((r, j) => r.split('').forEach((ch, i) => { if (ch !== '.') R(hx - 11 + (dir > 0 ? i : 21 - i), hy - 7 + j, 1, 1, pal[ch]); }));
      for (let k = 0; k < 8; k++) { const sw = Math.round(Math.sin(f * .15 + k) * 2), len = 3 + (k % 3); R(hx - dir * (11 + len), hy - 6 + k * 1.6 + sw, len, 2, k % 2 ? '#8fd978' : '#3fbf57'); }
      const bl = 5 + Math.abs(Math.round(Math.sin(f * .1) * 4));
      R(hx + dir * 10, hy + 2 + Math.round(Math.sin(f * .2)), bl, 1, '#8fd978'); R(hx + dir * 10 + (dir > 0 ? bl : -bl), hy + 1, 1, 2, '#8fd978');
      if ((f >> 6) % 4 === 0) for (let k = 0; k < 6; k++) R(hx + dir * (12 + k * 4) + (f % 3), hy + 3 - (k % 2) * 2, 3, 2, k % 2 ? '#fff1a8' : '#e8b923');
    }
    function fighters(f) {
      // 0-30 aproximam · 30-120 golpes · 120-150 recuam e carregam · 150-210 raios · 210-260 explosão ·
      // 260-330 olham a destruição · 330-450 reconstroem · 450-480 voltam para o céu
      const cyc = f % CYCLE, S = 1, SW = 11 * S, SH = 14 * S, cx = 160;
      const base = 58 + Math.sin(f * .03) * 5;
      let gap = 30, charge = false, beams = false, boom = false, after = false, building = false;
      if (cyc < 30) gap = 50 - cyc;
      else if (cyc < 120) gap = 20;
      else if (cyc < 150) { gap = 20 + (cyc - 120) * (240 / 30); charge = true; }
      else if (cyc < 210) { gap = 260; beams = true; }
      else if (cyc < 260) { gap = 260; boom = true; }
      else if (cyc < 330) { gap = 260 - (cyc - 260) * (180 / 70); after = true; }
      else if (cyc < 450) { gap = 80; after = true; building = true; }
      else { gap = 80 - (cyc - 450); after = true; }
      const bob1 = Math.sin(f * .12) * 2, bob2 = Math.cos(f * .12) * 2;
      let x1 = cx - gap / 2 - SW, x2 = cx + gap / 2;
      let y1 = base - SH + bob1, y2 = base - SH + bob2;
      let a1 = F1.idle, a2 = F2.idle, hit1 = false, hit2 = false;
      if (building) {
        // descem e vão até a casa; carregam blocos em vaivém e comemoram ao terminar
        const k = (cyc - 330) / 120, down = Math.min(1, k / .12);
        const groundY = 110 - SH;
        const walk = Math.sin(f * .08), step = (f >> 3) % 2;
        x1 = 20 + walk * 18 * down + (1 - down) * (cx - 40 - SW - 20); x2 = 140 - walk * 18 * down + (1 - down) * (cx + 40 - 140);
        y1 = base - SH + (groundY - base + SH) * down - (down >= 1 ? step : 0); y2 = y1 + (down >= 1 ? step * 2 - 1 : 0);
        if (down >= 1 && k < .9) {
          const held1 = walk > 0, held2 = walk < 0;
          if (held1) R(x1 + SW - 1, y1 + 4, 5, 4, '#f4d9b2'); else R(x1 - 4, y1 + 4, 5, 4, '#f4d9b2');
          if (held2) R(x2 - 4, y2 + 4, 5, 4, '#c8641e'); else R(x2 + SW - 1, y2 + 4, 5, 4, '#c8641e');
          if ((f >> 3) % 3 === 0) { R(x1 + 2, y1 + 2, 1, 2, '#5ad8ff'); R(x2 + SW - 3, y2 + 2, 1, 2, '#5ad8ff'); }
        }
        if (k >= .9) {
          const j = Math.abs(Math.sin(f * .3)) * 4; y1 -= j; y2 -= j; a1 = F1.punch; a2 = F2.punch;
          for (let p = 0; p < 5; p++) { const t = (f + p * 7) % 20; R(60 + p * 20, 70 - t, 1, 1, p % 2 ? '#fff1a8' : '#ffffff'); }
        }
      } else if (after) {
        // pairam ofegantes olhando a destruição; depois sobem do chão e se encaram de novo
        y1 += Math.sin(f * .3) * 1; y2 += Math.cos(f * .3) * 1;
        if ((f >> 3) % 2 && cyc < 330) { R(x1 + SW + 1, y1 + 2, 1, 2, '#5ad8ff'); R(x2 - 2, y2 + 2, 1, 2, '#5ad8ff'); }
        if (cyc >= 450) {
          const up = Math.min(1, (cyc - 450) / 15), ease = 1 - Math.pow(1 - up, 2), walk = Math.sin(f * .08), groundY = 110 - SH;
          const gx1 = 20 + walk * 18, gx2 = 140 - walk * 18;
          x1 = gx1 + (x1 - gx1) * ease; x2 = gx2 + (x2 - gx2) * ease;
          y1 = groundY + (y1 - groundY) * ease; y2 = groundY + (y2 - groundY) * ease;
          if (up >= 1) { R(x1 + SW / 2, y1 - 8, 1, 4, '#c8102e'); R(x1 + SW / 2, y1 - 3, 1, 1, '#c8102e'); R(x2 + SW / 2, y2 - 8, 1, 4, '#c8102e'); R(x2 + SW / 2, y2 - 3, 1, 1, '#c8102e'); }
        }
      }
      if (cyc >= 30 && cyc < 120) {
        const beat = Math.floor((cyc - 30) / 15) % 4, ph = ((cyc - 30) % 15) / 15;
        if (ph < .5) { if (beat === 0) { a1 = F1.punch; hit2 = true; } else if (beat === 1) { a2 = F2.punch; hit1 = true; } else if (beat === 2) { a1 = F1.kick; hit2 = true; } else { a2 = F2.kick; hit1 = true; } }
      }
      if (beams) { a1 = F1.punch; a2 = F2.punch; }
      const auraCol = (f >> 1) % 2 ? 'rgba(255,221,80,.75)' : 'rgba(255,241,168,.75)';
      if (!after || cyc >= 465) { aura(x1, y1, SW, SH, f, auraCol); aura(x2, y2, SW, SH, f, auraCol); }
      if (!after) for (let k = 0; k < 8; k++) { const t = ((f * 1.5 + k * 11) % 30); R(x1 + (k * 5) % SW, y1 + SH + t * .6, 1, 1, `rgba(255,241,168,${1 - t / 30})`); R(x2 + (k * 7) % SW, y2 + SH + t * .6, 1, 1, `rgba(255,241,168,${1 - t / 30})`); }
      if (beams) {
        const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
        const t = ease(Math.min(1, (cyc - 150) / 18)), ph = Math.sin(f * .07) * 8 + Math.sin(f * .19) * 2;
        const by = base - SH / 2 + 2, mid = cx + ph;
        const h1 = x1 + SW + 2, h2 = x2 - 2;
        if (t < 1) { beam(h1, h1 + (mid - h1) * t, by, f, '#5ad8ff', '#e6fbff', 1); beam(h2, h2 - (h2 - mid) * t, by, f, '#c86bff', '#f3dcff', -1); }
        else { beam(h1, mid, by, f, '#5ad8ff', '#e6fbff', 1); beam(h2, mid, by, f, '#c86bff', '#f3dcff', -1);
          const r = 8 + Math.sin(f * .35) * 2.5;
          const amb = c.createRadialGradient(mid, by, 0, mid, by, 90); amb.addColorStop(0, 'rgba(255,255,255,.25)'); amb.addColorStop(.5, 'rgba(160,200,255,.08)'); amb.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = amb; c.fillRect(mid - 90, by - 90, 180, 180);
          const g = c.createRadialGradient(mid, by, 0, mid, by, r + 6); g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(.5, 'rgba(255,255,255,.7)'); g.addColorStop(1, 'rgba(255,255,255,0)');
          c.fillStyle = g; c.fillRect(mid - r - 6, by - r - 6, r * 2 + 12, r * 2 + 12);
          for (let k = 0; k < 4; k++) { if ((f + k * 3) % 5 > 1) continue; let lx = mid, ly = by; const a = (k / 4) * 6.28 + f * .3; c.strokeStyle = k % 2 ? '#e6fbff' : '#f3dcff'; c.lineWidth = 1; c.beginPath(); c.moveTo(lx, ly); for (let s = 0; s < 5; s++) { lx += Math.cos(a) * 5 + (Math.sin(f * 2 + s * 7 + k) * 3); ly += Math.sin(a) * 4 + (Math.cos(f * 3 + s * 5 + k) * 3); c.lineTo(lx, ly); } c.stroke(); }
          for (let q = 0; q < 3; q++) { const rr = ((f * 1.2 + q * 9) % 27) + r, a = 1 - ((f * 1.2 + q * 9) % 27) / 27; c.strokeStyle = `rgba(255,255,255,${a * .6})`; c.lineWidth = 1; c.beginPath(); c.ellipse(mid, by, rr, rr * .55, 0, 0, 6.28); c.stroke(); }
          for (let k = 0; k < 18; k++) { const a = k / 18 * 6.28 + f * .12, rr = r + 3 + (f * 1.5 + k * 5) % 18, fade = 1 - ((f * 1.5 + k * 5) % 18) / 18; c.fillStyle = k % 2 ? `rgba(90,216,255,${fade})` : `rgba(200,107,255,${fade})`; c.fillRect(Math.round(mid + Math.cos(a) * rr), Math.round(by + Math.sin(a) * rr * .7), 1 + (k % 2), 1 + (k % 2)); }
          // reflexo no lago e vento no campo
          const gl = c.createRadialGradient(mid, 150 + LY, 0, mid, 150 + LY, 60); gl.addColorStop(0, 'rgba(255,255,255,.35)'); gl.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = gl; c.fillRect(mid - 60, 128 + LY, 120, 52);
          for (let k = 0; k < 10; k++) { const d = (f * 3 + k * 23) % 280; R(mid - 140 + d, 100 + (k * 7) % (22 + LY), 4, 1, 'rgba(255,255,255,.35)'); }
        }
      }
      if (boom) {
        const tt = (cyc - 210) / 50, by = base - SH / 2;
        if (tt < .3) {
          // implosão: energia sugada para um ponto, depois clarão
          const k = tt / .3;
          const r = 20 * (1 - k) + 2; const g = c.createRadialGradient(cx, by, 0, cx, by, r); g.addColorStop(0, '#ffffff'); g.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = g; c.fillRect(cx - r, by - r, r * 2, r * 2);
          for (let p = 0; p < 24; p++) { const a = p / 24 * 6.28, d = 40 * (1 - k); R(cx + Math.cos(a) * d, by + Math.sin(a) * d * .6, 1, 1, p % 2 ? '#5ad8ff' : '#c86bff'); }
          if (k > .8) { c.fillStyle = `rgba(255,255,255,${(k - .8) / .2})`; c.fillRect(0, 0, W, H); }
        } else {
          const k = (tt - .3) / .7, ease = 1 - Math.pow(1 - k, 2.5);
          if (k < .25) { c.fillStyle = `rgba(255,255,255,${1 - k / .25})`; c.fillRect(0, 0, W, H); }
          const sh = k < .5 ? Math.round(Math.sin(f * 3) * 3 * (1 - k * 2)) : 0;
          const r = 10 + ease * 95, hot = Math.max(0, 1 - k * 1.6);
          const g = c.createRadialGradient(cx + sh, by, 0, cx + sh, by, r);
          g.addColorStop(0, `rgba(255,255,255,${hot})`); g.addColorStop(.3, `rgba(255,241,168,${Math.max(0, 1 - k * 1.2)})`); g.addColorStop(.6, `rgba(255,140,60,${Math.max(0, .9 - k)})`); g.addColorStop(.85, `rgba(90,70,60,${Math.max(0, .7 - k * .7)})`); g.addColorStop(1, 'rgba(0,0,0,0)');
          c.fillStyle = g; c.fillRect(cx + sh - r, by - r, r * 2, r * 2);
          for (let s = 0; s < 14; s++) { const y = by - s * 6 * ease, w = (10 + s * 2) * ease + Math.sin(f * .1 + s) * 2; c.fillStyle = `rgba(80,70,65,${Math.max(0, .55 - k * .4)})`; c.fillRect(cx + sh - w / 2, y, w, 6); }
          const capR = 28 * ease, cy = by - 80 * ease; const cg = c.createRadialGradient(cx + sh, cy, 0, cx + sh, cy, capR); cg.addColorStop(0, `rgba(120,100,90,${Math.max(0, .7 - k * .5)})`); cg.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = cg; c.fillRect(cx + sh - capR, cy - capR, capR * 2, capR * 2);
          const wr = ease * 200; c.strokeStyle = `rgba(255,255,255,${(1 - k) * .9})`; c.lineWidth = 3; c.beginPath(); c.ellipse(cx + sh, 112, wr, wr * .18, 0, 0, 6.28); c.stroke();
          c.strokeStyle = `rgba(255,220,160,${(1 - k) * .5})`; c.lineWidth = 1; c.beginPath(); c.ellipse(cx + sh, 112, wr * .8, wr * .14, 0, 0, 6.28); c.stroke();
          for (let p = 0; p < 20; p++) { const a = p / 20 * 6.28; R(cx + sh + Math.cos(a) * wr, 112 + Math.sin(a) * wr * .18 - (p % 3) * 2 - ease * 8, 2, 2, `rgba(217,160,113,${(1 - k) * .8})`); }
          for (let p = 0; p < 30; p++) { const a = (p / 30) * 3.14 + 3.14 + Math.sin(p) * .2, sp = 2 + (p % 5) * .6, dt = k * 40; const px = cx + Math.cos(a) * sp * dt, py = 112 + Math.sin(a) * sp * dt * .9 + dt * dt * .06; const col = p % 3 === 0 ? '#f4d9b2' : p % 3 === 1 ? '#c9a070' : '#2e6e3a'; R(px, py, 1 + (p % 2), 1 + (p % 2), col); if (p % 4 === 0) R(px, py - 1, 1, 1, '#ff8c3c'); }
          for (let p = 0; p < 16; p++) { const a = p / 16 * 6.28 + f * .02, d = ease * (60 + (p % 4) * 15); R(cx + sh + Math.cos(a) * d, by + Math.sin(a) * d * .7, 1, 1, p % 2 ? '#fff1a8' : '#ff8c3c'); }
          for (let q = 0; q < 3; q++) R(0, 130 + LY + ((cyc - 210 + q * 3) % 10) + q * 6, W, 1, `rgba(255,255,255,${(1 - k) * .35})`);
        }
      }
      sprite(a1, x1 + (hit1 ? -2 : 0), y1, F1.pal, false, S);
      sprite(a2, x2 + (hit2 ? 2 : 0), y2, F2.pal, true, S);
      if (hit1 || hit2) { const ix = hit1 ? x1 + SW - 2 : x2 + 2, iy = base - 16 + ((f >> 1) % 2); R(ix - 3, iy, 7, 1, '#fff1a8'); R(ix, iy - 3, 1, 7, '#fff1a8'); R(ix - 1, iy - 1, 3, 3, '#ffffff'); }
      if (cyc < 30 || charge || (cyc >= 330 && cyc < 345) || (cyc >= 450 && cyc < 465)) for (let k = 0; k < 3; k++) { R(x1 - 4 - k * 4 + (f % 3), y1 + 6 + k * 6, 3, 1, 'rgba(255,255,255,.6)'); R(x2 + SW + 1 + k * 4 - (f % 3), y2 + 6 + k * 6, 3, 1, 'rgba(255,255,255,.6)'); }
      if (charge) { const t = (cyc - 120) / 30, r = 1 + t * 4, by = base - SH / 2 + 2; [[x1 + SW, '#5ad8ff', '#e6fbff'], [x2, '#c86bff', '#f3dcff']].forEach(([bx, col, core], k) => { const g = c.createRadialGradient(bx, by, 0, bx, by, r + 2); g.addColorStop(0, '#ffffff'); g.addColorStop(.5, core); g.addColorStop(1, 'rgba(0,0,0,0)'); c.fillStyle = g; c.fillRect(bx - r - 2, by - r - 2, r * 2 + 4, r * 2 + 4);
        for (let p = 0; p < 8; p++) { const a = p / 8 * 6.28 + f * .05 + k, d = 14 - ((f * 1.2 + p * 5) % 14); R(bx + Math.cos(a) * d, by + Math.sin(a) * d * .7, 1, 1, col); }
        const ring = 8 + Math.sin(f * .4 + k) * 2; c.strokeStyle = `rgba(255,241,168,${.4 + t * .4})`; c.lineWidth = 1; c.beginPath(); c.ellipse(bx + (k ? SW / 2 : -SW / 2), by, SW / 2 + ring, SH / 2 + ring * .6, 0, 0, 6.28); c.stroke(); }); }
    }

    // ---------- quadro ----------
    ['#3c8ee8', '#5aa7e6', '#6db4ec', '#82c1f1', '#9bcff6', '#b7ddf9'].forEach((col, i) => R(0, i * 16, W, 17, col));
    const dk = ruin(f); if (dk > 0) { c.fillStyle = `rgba(60,50,50,${dk * .35})`; c.fillRect(0, 0, W, 98); }  // fumaça escurece o céu
    const sol = c.createRadialGradient(40, 6, 0, 40, 6, 46); sol.addColorStop(0, 'rgba(255,255,255,.9)'); sol.addColorStop(.3, 'rgba(255,250,220,.4)'); sol.addColorStop(1, 'rgba(255,255,255,0)'); c.fillStyle = sol; c.fillRect(0, 0, 100, 60);
    for (let i = 0; i < 6; i++) { const w = 24 + (i * 11) % 30, s = .05 + (i % 3) * .03; cloud((((i * 61) + f * s) % (W + w + 20)) - w - 10, 6 + (i * 13) % 30, w); }
    mountain(-40, 160, 60, '#7fb0a0', '#6a9a8a'); mountain(200, 180, 70, '#6fa58f', '#5a8f7a'); mountain(90, 120, 36, '#8fbf9f', '#7aab8c');
    mountain(-20, 120, 40, '#4f9c3a', '#3f8f4a'); mountain(220, 150, 50, '#4f9c3a', '#3f8f4a');
    for (let x = -6; x < W; x += 14) for (let i = 0; i < 10; i++) R(x + i, 96 - Math.sin(i / 10 * 3.14) * 8, 1, 8, '#2e6e3a');
    // campo (26 px mais alto que no arquivo: é onde o Albi anda)
    R(0, 98, W, 26 + LY, '#6fbf4e'); R(0, 98, W, 4, '#7fc95a'); R(0, 112 + LY, W, 12, '#5fb044');
    for (let i = 0; i < 70; i++) { const x = (i * 53 + 7) % W, y = 100 + (i * 29) % (22 + LY); R(x, y, 1, 2, '#4f9c3a'); }
    house(f);
    tree(214, 124, f);
    sonar();
    const d = ruin(f);
    if (d > 0) { c.fillStyle = `rgba(40,30,25,${d * .45})`; for (let k = 0; k < 9; k++) { const w = 60 - Math.abs(k - 4) * 10; c.fillRect(160 - w, 98 + k * 3, w * 2, 3); } for (let k = 0; k < 14; k++) R(60 + (k * 37) % 200, 100 + (k * 13) % 22, 3, 2, `rgba(40,30,25,${d * .6})`); }
    lake(f);
    if (estatico) return;
    dragon(f);
    fighters(f);
  }

"""
troca_bloco("  paintArena(c) {\n", "  paintCampo(c) {", CENA)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 03 ganhou a arena nova do Albi em", caminho)
