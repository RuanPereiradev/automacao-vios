"""Vila 03 (Albi) vira a arena de albi/mascote/fundo-arena-albi.html.

O fundo é o do arquivo do usuário, adaptado à vila (320×224 em vez de 320×180):
- céu em faixas, com nuvens e pássaros passando;
- montanhas, mesas de pedra, campo, estrada até o horizonte e lago brilhando;
- a plataforma em perspectiva, com o brilho que corre pelo piso, e as quatro torres com as pontas
  piscando.
O Albi transita só em cima da plataforma (linhas 8 a 10 da vila, colunas 3 a 16) e, parado, passeia
por ela. Os postos ficam nas torres:
  Doca 01 · Albi = torre da frente à esquerda; Receptor TXT = torre do fundo à esquerda;
  Conferência = painel atrás da plataforma; Torre Sonar = torre alta da frente à direita (a luz da
  ponta pisca quando ele entra no Sonar ou pesquisa).
Os eventos, as falas e o painel do Albi não mudam; as Vilas 01 e 02 ficam como estão.

uso: python3 doc/vila/ligar_vila03_arena.py bot/vila/vila.html
(depois do ligar_zangao.py, ligar_albi.py, ligar_bumblebee.py e ligar_vila01_campo.py; rodar de novo
não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
ETAPA1 = "drawArena(c, f)" not in t
ETAPA2 = "arena: recorte" not in t  # o desenho da arena não passa da Vila 03 (a montanha da direita invadia a 04)
if not (ETAPA1 or ETAPA2):
    sys.exit("a Vila 03 já é a arena")
if "ahandle(ev)" not in t or "paintCampo(c)" not in t:
    sys.exit("rode antes o ligar_albi.py e o ligar_vila01_campo.py")


def troca(velho, novo, etapa=1):
    global t
    if not {1: ETAPA1, 2: ETAPA2}[etapa]:
        return
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) onde ele pode andar: só a plataforma (Vila 03 = colunas 40–59 da vila)
troca("""      block(o + Component.TOWER.x, Component.TOWER.y, 2, 4);
    }""", """      block(o + Component.TOWER.x, Component.TOWER.y, 2, 4);
    }
    // Vila 03 = arena: o Albi anda só em cima da plataforma (linhas 8–10, colunas 3–16)
    for (let y = 0; y < 14; y++) for (let x = 40; x < 60; x++) this.blocked[y][x] = !(y >= 8 && y <= 10 && x >= 43 && x <= 56);""")
troca("this.a = { x: 43 * 16, y: 64,", "this.a = { x: 43 * 16, y: 160,")

# 2) os postos nas torres da arena
troca("O = 40, HOME = [O + 3, 4], REC = [O + 9, 4], OFI = [O + 15, 4], TOR = [O + 14, 10]",
      "O = 40, HOME = [O + 3, 10], REC = [O + 4, 8], OFI = [O + 8, 8], TOR = [O + 16, 10]")
troca("""    const pos = ap === 'recebendo' ? [O + 9, 4] : ap === 'conferindo' ? [O + 15, 4] : (ap === 'entrando' || ap === 'preenchendo') ? [O + 14, 10] : [O + 3, 4];
    a.x = pos[0] * 16; a.y = pos[1] * 16; a.dir = pos[0] === O + 14 ? 'right' : 'down';""",
      """    const pos = ap === 'recebendo' ? [O + 4, 8] : ap === 'conferindo' ? [O + 8, 8] : (ap === 'entrando' || ap === 'preenchendo') ? [O + 16, 10] : [O + 3, 10];
    a.x = pos[0] * 16; a.y = pos[1] * 16; a.dir = pos[0] === O + 16 ? 'right' : 'down';""")
troca("pts = [[49, 4], [53, 8], [46, 10], [43, 4]]", "pts = [[46, 9], [52, 8], [54, 10], [49, 10], [44, 9], [50, 9]]")

# 3) efeitos do Albi nos lugares da arena (antes: prédios e torre da vila)
troca("      R(O3 + 63, 4, 3, 3, (f >> 5) % 2 ? '#f29bbf' : '#6b3a52');\n", "      this.drawArena(c, f);\n")
troca("R(O3 + TX + 15, TY, 2, 2,", "R(O3 + 281, 97, 2, 2,")
troca("if (afx === 'check') for (let i = 0; i < 5; i++) R(O3 + SX + 3, SY + 3 + ((i * 3 + (f >> 2)) % 11),",
      "if (afx === 'check') for (let i = 0; i < 5; i++) R(O3 + 125, 101 + ((i * 3 + (f >> 2)) % 10),")
troca("for (let i = 0; i < 4; i++) R(O3 + SX + 3, SY + 3 + i * 3, 14 + (i * 5) % 7, 1, '#9aa0a8');",
      "for (let i = 0; i < 4; i++) R(O3 + 125, 101 + i * 3, 12 + (i * 5) % 5, 1, '#9aa0a8');")
troca("R(O3 + SX + 21, SY + 3, 2, 2,", "R(O3 + 141, 101, 2, 2,")
troca("R(O3 + 148 + ((t0 * 3 + i * 11) % 9), 52 + ((t0 + i * 5) % 8),", "R(O3 + 62 + ((t0 * 3 + i * 11) % 9), 66 + ((t0 + i * 5) % 8),")
troca("(O3 + SX + 13 - a.x - 8) * k, ay + 6 + (SY + 7 - ay - 6) * k", "(O3 + 134 - a.x - 8) * k, ay + 6 + (106 - ay - 6) * k")
troca("TXA = O3 + TX;", "TXA = O3 + 274;")

# 4) placas da Vila 03 nas torres (sem as docas, que não existem na arena)
troca("""    for (let v = 0; v < NV; v++) {
      const o = v * 20, on = v <= 2, mine""", """    for (let v = 0; v < NV; v++) {
      if (v === 2) { // arena do Albi
        plaques.push(P(43.5, 11.6, 'Doca 01 · Albi'), P(44.1, 3.4, 'Receptor TXT'), P(48.4, 5.3, 'Conferência'), P(57.6, 5.0, 'Torre Sonar'));
        continue;
      }
      const o = v * 20, on = v <= 2, mine""")

# 5) o fundo da arena (parte fixa) e a parte animada (nuvens, pássaros, lago, brilho do piso, pontas)
troca("""    this.paintCampo(c);
  }
""", """    this.paintCampo(c);
    this.paintArena(c);
  }

  // arena (albi/mascote/fundo-arena-albi.html): x local 0–319 + 640; céu até y 96; plataforma de 124 a 180
  static ARENA = { O: 640, HOR: 96, top: 124, bot: 180, lx0: 58, rx0: 262, lx1: 28, rx1: 292 };
  arenaBorda(y) {
    const A = Component.ARENA, t = (y - A.top) / (A.bot - A.top);
    return [A.lx0 + (A.lx1 - A.lx0) * t, A.rx0 + (A.rx1 - A.rx0) * t];
  }
  paintArena(c) {
    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320, H = 224;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    R(0, 0, W, H, '#6fbf4e');
    ['#5aa7e6', '#6db4ec', '#82c1f1', '#9bcff6', '#b7ddf9'].forEach((col, i) => R(0, i * (HOR / 5), W, HOR / 5 + 1, col));
    R(0, HOR - 14, W, 14, '#7fb0a0');
    [[0, 40, 10], [60, 70, 16], [150, 50, 9], [220, 90, 18], [300, 40, 12]].forEach(([x, w, h]) => {
      for (let i = 0; i < h; i++) { const k = h - 1 - i; R(x + k * (w / h / 2), HOR - 14 - h + i, w - k * (w / h), 1, '#6a9a8a'); }
    });
    [[8, 36, 22], [262, 44, 24]].forEach(([x, w, h]) => {
      R(x, HOR - h, w, h, '#c99a5a'); R(x + 2, HOR - h - 3, w - 4, 3, '#7fc45e'); R(x + 2, HOR - h, w - 4, 1, '#a97b43');
      for (let i = 0; i < 4; i++) R(x + 3 + i * (w / 4), HOR - h + 4 + (i % 2) * 5, 2, h - 8, '#a97b43');
    });
    R(0, HOR, W, H - HOR, '#6fbf4e'); R(0, HOR, W, 10, '#86cf62');
    for (let y = HOR; y < H; y++) {
      const t = (y - HOR) / (H - HOR), x = W / 2 + Math.sin(t * 4.5) * 30 * (1 - t) + 20 * (1 - t), w = 2 + t * 26;
      R(x - w / 2, y, w, 1, '#d9c89a'); if (y % 6 === 0) R(x - 1, y, 2, 1, '#efe3bf');
    }
    R(190, HOR + 6, 48, 6, '#58a8e0'); R(194, HOR + 5, 40, 1, '#8fd0f5');
    // painel da Conferência (atrás da plataforma)
    R(118, 96, 32, 20, '#33404f'); R(119, 97, 30, 18, '#5a6c80'); R(121, 99, 26, 14, '#1d2733'); R(119, 97, 30, 1, '#8ea3b8');
    R(126, 116, 2, 8, '#4a5a6e'); R(140, 116, 2, 8, '#4a5a6e');
    // plataforma: lateral, topo, ladrilhos e borda
    const { top, bot, lx0, rx0, lx1, rx1 } = A;
    R(lx1, bot, rx1 - lx1, 10, '#4a5a6e'); R(lx1, bot + 10, rx1 - lx1, 4, '#33404f');
    for (let x = lx1 + 8; x < rx1 - 4; x += 24) R(x, bot + 2, 1, 7, '#2e3a48');
    R(lx1, bot, rx1 - lx1, 1, '#8ea3b8');
    const linhas = [2, 6, 11, 17, 24, 32, 41, 50];
    for (let y = top; y < bot; y++) {
      const [l, r] = this.arenaBorda(y), w = r - l;
      R(l, y, w, 1, '#8ea3b8');
      if (linhas.includes(y - top)) R(l, y, w, 1, '#5f768c');
      for (let k = 1; k < 10; k++) R(l + w * k / 10, y, 1, 1, '#5f768c');
    }
    R(lx0, top, rx0 - lx0, 1, '#eef5fb');
    R(lx1 - 6, bot + 14, rx1 - lx1 + 12, 3, 'rgba(40,70,40,.5)');
    // torres: fundo (base no topo da plataforma) e frente (base na borda da frente)
    const torre = (x, base, h) => {
      R(x - 5, base - 3, 10, 3, '#5a6c80'); R(x - 4, base - 4, 8, 1, '#8ea3b8');
      for (let i = 0; i < h; i++) {
        const k = i / h, w = Math.max(1, Math.round(4 * (1 - k) + 0.6));
        R(x - (w >> 1), base - 4 - i, w, 1, k > .92 ? '#ffffff' : '#c7d6e4');
        if (w >= 3) R(x - (w >> 1), base - 4 - i, 1, 1, '#eef5fb');
        if (w >= 2) R(x + (w >> 1) - (w % 2 ? 0 : 1), base - 4 - i, 1, 1, '#8ea3b8');
      }
    };
    torre(lx0 + 8, top + 2, 50); torre(rx0 - 8, top + 2, 50); torre(lx1 + 10, bot + 1, 78); torre(rx1 - 10, bot + 1, 78);
  }
  drawArena(c, f) {
    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    // nuvens e pássaros
    for (let i = 0; i < 7; i++) {
      const w = 22 + (i * 9) % 26, s = .06 + (i % 3) * .03, x = (((i * 53) + f * s) % (W + w + 20)) - w - 10, y = 8 + (i * 17) % 44;
      R(x, y + 3, w, 5, '#ffffff'); R(x + 3, y, w - 6, 3, '#ffffff'); R(x + w * .3, y - 2, w * .3, 2, '#ffffff'); R(x + 1, y + 8, w - 2, 1, '#cfe3f2');
    }
    for (let i = 0; i < 3; i++) {
      const x = ((f * (.35 + i * .08) + i * 110) % (W + 50)) - 30, y = 22 + i * 9, up = Math.floor((f + i * 20) / 8) % 2;
      R(x, y + (up ? 0 : 1), 2, 1, '#2b3a4a'); R(x + 2, y + (up ? 1 : 0), 2, 1, '#2b3a4a'); R(x + 4, y + (up ? 0 : 1), 2, 1, '#2b3a4a');
    }
    if ((f >> 3) % 2) R(200 + (f >> 2) % 20, HOR + 8, 4, 1, '#bde6fb');
    // grama balançando (fora da plataforma)
    for (let i = 0; i < 60; i++) {
      const x = (i * 37 + 11) % W, y = HOR + 4 + (i * 13) % (224 - HOR - 10);
      if (y > A.top - 2 && y < A.bot + 16 && x > A.lx1 - 4 && x < A.rx1 + 4) continue;
      const sway = Math.round(Math.sin(f * .08 + i * .7));
      R(x, y, 1, 2, '#4f9c3a'); R(x + sway, y - 1, 1, 1, '#4f9c3a');
    }
    // brilho que percorre o piso
    const gx = (f * .6) % (A.rx1 - A.lx1 + 60) + A.lx1 - 30;
    for (let y = A.top; y < A.bot; y++) {
      const [l, r] = this.arenaBorda(y), sx = gx + (y - A.top) * .4;
      if (sx > l && sx + 3 < r) R(sx, y, 3, 1, 'rgba(255,255,255,.18)');
    }
    // pontas das torres piscando
    if ((f >> 4) % 2) [[A.lx0 + 8, A.top + 2 - 54], [A.rx0 - 8, A.top + 2 - 54], [A.lx1 + 10, A.bot + 1 - 82], [A.rx1 - 10, A.bot + 1 - 82]]
      .forEach(([x, y]) => { R(x - 1, y, 3, 1, '#ffffff'); R(x, y - 1, 1, 3, '#ffffff'); });
  }
""")

# 6) etapa 2: recorta o desenho da arena na área da Vila 03 (x 640–959)
troca("""    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320, H = 224;
""", """    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320, H = 224;
    c.save(); c.beginPath(); c.rect(O, 0, W, H); c.clip();  // arena: recorte
""", 2)
troca("""    torre(lx0 + 8, top + 2, 50); torre(rx0 - 8, top + 2, 50); torre(lx1 + 10, bot + 1, 78); torre(rx1 - 10, bot + 1, 78);
  }""", """    torre(lx0 + 8, top + 2, 50); torre(rx0 - 8, top + 2, 50); torre(lx1 + 10, bot + 1, 78); torre(rx1 - 10, bot + 1, 78);
    c.restore();
  }""", 2)
troca("""    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320;
""", """    const A = Component.ARENA, O = A.O, HOR = A.HOR, W = 320;
    c.save(); c.beginPath(); c.rect(O, 0, W, 224); c.clip();  // nuvens e pássaros não saem da arena
""", 2)
troca("""      .forEach(([x, y]) => { R(x - 1, y, 3, 1, '#ffffff'); R(x, y - 1, 1, 3, '#ffffff'); });
  }""", """      .forEach(([x, y]) => { R(x - 1, y, 3, 1, '#ffffff'); R(x, y - 1, 1, 3, '#ffffff'); });
    c.restore();
  }""", 2)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 03 virou a arena do Albi em", caminho)
