"""Vila 01 do Sam (antes "Ultron") no campo, com o mascote novo.

Etapa 1 (UCAMPO): mascote e cenário. Etapa 2: o nome "Ultron" vira "Sam" em tudo que a vila mostra
(placa, aba, fala, registro, "página do Sam") e a bolinha de status fica dourada como o cabelo dele.
O código interno e os eventos continuam "ultron".

Mascote: o personagem de doc/mascote/WhatsApp Image 2026-11-04 at 11.19.56.jpeg (grade 28×35 em
doc/mascote/ultron-campo.html), de cabelo dourado, capa verde, colete e pés descalços. Parado, ele
balança; andando, alterna os pés.
Cenário (doc/mascote/1e86eacd-....jpeg): céu com nuvens e colinas ao fundo, grama com flores,
caminhos de terra, sebe nas bordas, casas na colina com porta redonda (Doca 01 · Ultron com a
chaminé soltando fumaça; Conferência com o quadro onde ele organiza as CIs), moinho com as pás
girando (Receptor TXT, onde o .txt cai), hortas cercadas (as docas livres), lago com ponte de
pedra e uma torre de pedra com lanterna (Torre VIOS).
A geometria é a mesma da vila (mesmos blocos, portas, caminhos e postos), então o Ultron anda
igual; só muda o desenho da Vila 01 (x 0–319). As outras vilas ficam como estão.

uso: python3 doc/vila/ligar_vila01_campo.py bot/vila/vila.html
(depois do ligar_zangao.py, ligar_albi.py e ligar_bumblebee.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
ETAPA1 = "UCAMPO" not in t
ETAPA2 = "'01 · Sam'" not in t
if not (ETAPA1 or ETAPA2):
    sys.exit("a Vila 01 já está no campo, com o Sam")
if "BROBOT" not in t:
    sys.exit("rode antes o doc/vila/ligar_zangao.py, ligar_albi.py e ligar_bumblebee.py")


def troca(velho, novo, etapa=1):
    global t
    if not {1: ETAPA1, 2: ETAPA2}[etapa]:
        return
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


GRADE = ["........KRRRK..KRRRK........", ".......KRYYYRRRYYYRK........", ".....KRROYYYOOOYYYORRK......",
         "....KYYYYOYYYYOOYYYYYYRK....", "..KRYYOYOYYYYYYOYYOYYYOYRK..", "..KRYYOOYYYOYYYOYYOOYYYORK..",
         ".KRYYYYOOYYOOYYOOOOOOOYYYYK.", ".KRYYOYOOOOOYYOSSSOOOYOYYRK.", ".KRYYOYOSSSSOOSSSSSSOYOYYRK.",
         ".KROYYOSSSSSSSSSSSSSSOYYORK.", "KSOYOSSSSSSSSSSSSSSSSSOYOSK.", "KSSRRSSSEEESSSSSEEESSSRRSSK.",
         "KSSTRSSESSSESSSESSSESSRTSSK.", "KSSTRSSESSSESSSESSSESSRTSSK.", ".KTTRSSSSSSSSSSSSSSSSSRTTK..",
         "....KSSSSSSMMMMSSSSSSSK.....", ".....KSSSSSSSSSSSSSSSK......", ".....KKKKKHHHHHHHKKKKK......",
         ".....HHHHKVKYYYKVKHHHH......", "....KGGGGKKKYOYKKKGGGGK.....", "...KGGGGGGGKKYKKGGGGGGGK....",
         "..KGGGGGKKKVVVVVKKKGGGGGK...", "..KGHHHKSSKVVYVVKSSKHHHGK...", ".KHGKSSSKVVVKYKVVVKSSSKHGK..",
         ".KHGKSSSKVVVKVKVVVKSSSKHGK..", ".KHGKSSSKVVVKYKVVVKSSSKHGK..", ".KHGKTTTKVVVKVKVVVKTTTKHGK..",
         ".KHGKKKKKVVVKKKVVVKKKKKHGK..", ".KHGGKKVVVVVVVVVVVVVKKGGHK..", ".KGGGKVVVVVVKKVVVVVVKGGGGK..",
         "KGGGGKVVVVVVKKVVVVVVKGGGGGK.", "KKKKKKKKKKKK....KKKKKKKKKKK.", "....KSSSSSSK....KSSSSSSK....",
         "...KSSTSSTSSK..KSSTSSTSSK...", "...KKKKKKKKKK..KKKKKKKKKK..."]
CORES = {"K": "#2a2016", "Y": "#fdc155", "O": "#e9ad56", "R": "#ad5c25", "S": "#f6e0c1", "T": "#d9b68e",
         "E": "#e02b2b", "M": "#3a2418", "G": "#556936", "H": "#3f5230", "V": "#5d341f"}

# 1) o mascote (grade e cores)
troca("  static SPR = (() => {",
      f"  static UCAMPO = {json.dumps(GRADE)};\n  static UCORES = {json.dumps(CORES)};\n  static SPR = (() => {{")

# 2) desenho do Ultron: o personagem (28×35, pés no chão do bloco); andando, alterna os pés
troca("""    const ox = u.x, oy = u.y + 3 + bob;
    c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(Math.round(ox + 3), Math.round(u.y + 14), 10, 2);
    Component.SPR[u.dir][fi].forEach((row, j) => row.split('').forEach((ch, i) => {
      if (ch !== '.') R(ox + i, oy + j - 4, 1, 1, (blink && (ch === 'R' || ch === 'O')) ? pal.K : pal[ch]);
    }));""", """    const UC = Component.UCAMPO, UP = Component.UCORES, ucx = Math.round(u.x + 8), uG = Math.round(u.y + 15);
    c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(ucx - 10, uG - 1, 20, 2);
    const utop = uG - UC.length + bob;
    UC.forEach((row, j) => { for (let i = 0; i < row.length; i++) {
      const ch = row[i]; if (ch === '.') continue;
      const pe = j >= UC.length - 3 && moving && ((i < 14) === (fi === 0)) ? -1 : 0;  // pé que levanta ao andar
      R(ucx - 14 + i, utop + j + pe, 1, 1, ch === 'E' && blink ? UP.K : UP[ch]);
    } });
    const ox = u.x, oy = utop + 4;""")

# 3) no lugar da luz vermelha da antena da Doca 01: fumaça da chaminé e as pás do moinho girando
troca("    R(63, 4, 3, 3, (f >> 5) % 2 ? '#ff5a3c' : '#6b2a22');", """    { // Vila 01 no campo: fumaça da chaminé (Doca 01) e pás do moinho (Receptor TXT)
      for (let i = 0; i < 3; i++) {
        const k = ((f * 0.5 + i * 20) % 60) / 60;
        c.globalAlpha = 0.8 * (1 - k); R(64 + Math.sin(k * 6 + i) * 2, 12 - k * 13, k > 0.5 ? 3 : 2, k > 0.5 ? 3 : 2, '#eef2f4');
      }
      c.globalAlpha = 1;
      const hx = 152, hy = 23, a0 = f * 0.02 * (this.props.speed ?? 1);
      for (let b = 0; b < 4; b++) {
        const a = a0 + b * Math.PI / 2, cs = Math.cos(a), sn = Math.sin(a);
        for (let r = 3; r <= 19; r++) {
          R(hx + cs * r, hy + sn * r, 1, 1, '#6b4a2a');
          if (r >= 6) for (let w = 1; w <= 4; w++) R(hx + cs * r - sn * w, hy + sn * r + cs * w, 1, 1, w === 4 ? '#c9bea4' : '#f4ecd8');
        }
      }
      R(hx - 1, hy - 1, 3, 3, '#3a2f25');
    }""")

# 4) fundo da Vila 01 no campo (pinta por cima do fundo padrão, só x 0–319)
troca("""      if (!on) { R(O + 63, 4, 3, 3, '#3a2a26'); R(X + 15, Y, 2, 2, '#3a2a26'); }
    }
  }
""", """      if (!on) { R(O + 63, 4, 3, 3, '#3a2a26'); R(X + 15, Y, 2, 2, '#3a2a26'); }
    }
    this.paintCampo(c);
  }

  paintCampo(c) {
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), w, h); };
    const M = Component.MAP, at = (x, y) => (M[y] && M[y][x]) || 'B';
    const hs = (x, y, k) => (((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) >>> 0);
    const disco = (cx, cy, r, col) => { for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y)); R(cx - w, cy + y, 2 * w + 1, 1, col); } };
    // chão: céu (1ª linha), sebe nas bordas, lago, caminho de terra e grama com flores
    for (let ty = 0; ty < 14; ty++) for (let tx = 0; tx < 20; tx++) {
      const ch = at(tx, ty), X = tx * 16, Y = ty * 16;
      if (ty === 0) { R(X, Y, 16, 16, '#9fd6f2'); R(X, Y, 16, 5, '#b9e3f7'); continue; }
      if (ch === 'B') {
        R(X, Y, 16, 16, '#2f6b34');
        for (let k = 0; k < 4; k++) { const h = hs(tx, ty, k); disco(X + 3 + h % 10, Y + 3 + (h >> 4) % 10, 3 + (h >> 8) % 2, k % 2 ? '#3d8642' : '#357a3b'); }
        const h = hs(tx, ty, 9); R(X + 3 + h % 10, Y + 2 + (h >> 4) % 9, 2, 1, '#5aa35c');
        if (h % 5 === 0) R(X + 4 + (h >> 6) % 8, Y + 5 + (h >> 9) % 8, 2, 2, '#d9484a');
        continue;
      }
      if (ch === 'C') {
        R(X, Y, 16, 16, '#3f9bd6');
        for (let k = 0; k < 3; k++) { const h = hs(tx, ty, k); R(X + 1 + h % 10, Y + 3 + k * 5, 5, 1, '#9fdcf7'); }
        if (at(tx, ty - 1) !== 'C') R(X, Y, 16, 3, '#8d8a80');
        if (at(tx + 1, ty) !== 'C') R(X + 13, Y, 3, 16, '#8d8a80');
        if (at(tx, ty + 1) !== 'C') R(X, Y + 13, 16, 3, '#8d8a80');
        if ((tx + ty) % 3 === 0) { disco(X + 10, Y + 9, 2, '#4f9a3c'); R(X + 10, Y + 9, 1, 1, '#3f9bd6'); }
        continue;
      }
      if (ch === 'P') {
        R(X, Y, 16, 16, '#c8a265');
        if (at(tx, ty - 1) !== 'P') R(X, Y, 16, 1, '#a7824a');
        if (at(tx, ty + 1) !== 'P') R(X, Y + 15, 16, 1, '#a7824a');
        if (at(tx - 1, ty) !== 'P') R(X, Y, 1, 16, '#a7824a');
        if (at(tx + 1, ty) !== 'P') R(X + 15, Y, 1, 16, '#a7824a');
        for (let k = 0; k < 4; k++) { const h = hs(tx, ty, k); R(X + 2 + h % 12, Y + 2 + (h >> 4) % 12, 1, 1, k % 2 ? '#e2c48e' : '#9c7a45'); }
        continue;
      }
      R(X, Y, 16, 16, '#6aad4c');
      for (let k = 0; k < 6; k++) { const h = hs(tx, ty, k); R(X + h % 15, Y + (h >> 4) % 14, 1, 2, k % 2 ? '#7fc15e' : '#5a9a3f'); }
      const h = hs(tx, ty, 7);
      if (h % 4 === 0 || ch === 'V') {
        const fx = X + 3 + (h >> 3) % 10, fy = Y + 3 + (h >> 7) % 10, cor = ['#ffffff', '#ffd84a', '#f29bbf', '#ffffff'][(h >> 11) % 4];
        R(fx, fy, 1, 1, cor); R(fx - 1, fy + 1, 3, 1, cor); R(fx, fy + 2, 1, 1, cor); R(fx, fy + 1, 1, 1, '#f0c46a');
        if (ch === 'V') { R(X + 9, Y + 9, 1, 1, '#ffffff'); R(X + 8, Y + 10, 3, 1, '#ffffff'); R(X + 9, Y + 10, 1, 1, '#f0c46a'); }
      }
    }
    // céu: colinas ao fundo e nuvens
    for (let x = 0; x < 320; x++) {
      const hh = Math.round(4 + 3 * Math.sin(x / 23) + 2 * Math.sin(x / 9 + 1));
      R(x, 16 - hh, 1, hh, '#86c46c'); R(x, 16 - hh, 1, 1, '#9bd47f');
    }
    [[22, 4], [118, 2], [205, 5], [292, 3]].forEach(([x, y]) => { R(x, y + 2, 18, 3, '#ffffff'); R(x + 3, y, 9, 3, '#ffffff'); R(x + 10, y + 1, 6, 2, '#ffffff'); R(x + 1, y + 4, 16, 1, '#dbeef8'); });
    // casa na colina com porta redonda: morro, porta, janela redonda e chaminé
    const colina = (x0, x1, porta, corPorta) => {
      const cx = (x0 + x1) / 2, rx = (x1 - x0) / 2;
      for (let x = x0; x < x1; x++) {
        const t = (x - cx) / rx, alt = Math.round(42 * Math.sqrt(Math.max(0, 1 - t * t)));
        const top = 64 - alt;
        R(x, top, 1, alt, x > cx + rx * 0.45 ? '#4f9339' : '#5fa646'); R(x, top, 1, 2, '#7cc45c');
        if (hs(x, 1, 3) % 6 === 0) R(x, top - 1, 1, 1, '#7cc45c');
      }
      const px = porta * 16 + 8, py = 54;
      disco(px, py, 11, '#7a4d24'); disco(px, py, 9, corPorta);
      for (let x = px - 6; x <= px + 6; x += 3) R(x, py - 8 + Math.abs(x - px) / 3, 1, 18, 'rgba(0,0,0,.18)');
      R(px - 12, 64 - 1, 25, 1, '#7a4d24'); R(px, py, 2, 2, '#f0c46a');
      R(px - 14, 64, 29, 2, '#8d8a80');
      return cx;
    };
    const cx1 = colina(30, 98, 3, '#3f8f3a');
    disco(82, 44, 6, '#7a4d24'); disco(82, 44, 4, '#f0c46a'); R(82, 40, 1, 9, '#7a4d24'); R(78, 44, 9, 1, '#7a4d24');
    disco(40, 52, 4, '#7a4d24'); disco(40, 52, 2, '#f0c46a');
    R(61, 13, 7, 14, '#8d8a80'); for (let y = 15; y < 27; y += 3) R(61, y, 7, 1, '#6f6c63'); R(60, 12, 9, 2, '#6f6c63');
    for (let x = 34; x < 96; x += 7) { R(x, 62, 1, 1, '#ffffff'); R(x + 3, 61, 1, 1, '#ffd84a'); }
    // moinho (Receptor TXT): torre clara, telhado vermelho e a porta onde o .txt entra
    for (let y = 27; y < 64; y++) {
      const k = (y - 27) / 37, w = Math.round(12 + 8 * k);
      R(152 - w, y, 2 * w, 1, '#efe3c6'); R(152 + w - Math.round(w * 0.35), y, Math.round(w * 0.35), 1, '#d8c9a6');
      R(152 - w, y, 1, 1, '#7a6a4a'); R(152 + w - 1, y, 1, 1, '#7a6a4a');
    }
    for (let y = 16; y < 28; y++) { const w = Math.round(4 + (y - 16) * 0.9); R(152 - w, y, 2 * w, 1, y < 18 ? '#c45a3f' : '#a5432f'); }
    R(147, 50, 10, 14, '#7a4a24'); R(148, 51, 8, 13, '#5a3418'); R(147, 50, 10, 1, '#3a2418'); R(154, 57, 1, 1, '#f0c46a');
    R(149, 35, 6, 6, '#7a6a4a'); R(150, 36, 4, 4, '#f0c46a'); R(151, 36, 1, 4, '#7a6a4a');
    for (let x = 130; x < 176; x += 5) R(x, 63, 2, 1, '#4f9339');
    // casa da Conferência: outra colina, porta amarela e o quadro onde ele organiza as CIs
    colina(222, 290, 15, '#e0b23c');
    R(257, 33, 30, 18, '#8a5a2b'); R(259, 35, 26, 14, '#24352a'); R(257, 33, 30, 1, '#b07a3e');
    R(260, 51, 2, 13, '#6b4420'); R(282, 51, 2, 13, '#6b4420');
    disco(232, 50, 4, '#7a4d24'); disco(232, 50, 2, '#f0c46a');
    // hortas cercadas (docas livres): terra arada, brotos e uma abóbora
    Component.LOTS.forEach((l, n) => {
      const X = l.x * 16, Y = l.y * 16, W = l.w * 16, H = l.h * 16;
      R(X + 2, Y + 2, W - 4, H - 4, '#7b5332');
      for (let y = Y + 5; y < Y + H - 4; y += 4) { R(X + 4, y, W - 8, 1, '#5e3e22'); for (let x = X + 6; x < X + W - 6; x += 5) R(x, y - 1, 1, 1, '#6fcf52'); }
      for (let x = X + 1; x < X + W - 1; x += 6) { R(x, Y, 2, 4, '#8a5a2b'); R(x, Y + H - 4, 2, 4, '#8a5a2b'); }
      for (let y = Y + 1; y < Y + H - 1; y += 6) { R(X, y, 3, 2, '#8a5a2b'); R(X + W - 3, y, 3, 2, '#8a5a2b'); }
      R(X + 1, Y + 1, W - 2, 1, '#b07a3e'); R(X + 1, Y + H - 2, W - 2, 1, '#b07a3e'); R(X + 1, Y + 1, 1, H - 2, '#b07a3e'); R(X + W - 2, Y + 1, 1, H - 2, '#b07a3e');
      disco(X + W - 10, Y + H - 10, 3, '#e8892b'); R(X + W - 10, Y + H - 14, 1, 2, '#4f9a3c');
    });
    // ponte de pedra sobre o lago
    R(4, 163, 68, 8, '#a59f92'); R(4, 162, 68, 1, '#c9c3b5'); for (let x = 6; x < 72; x += 6) R(x, 164, 1, 6, '#7d786d');
    for (let x = 20; x < 56; x++) { const t = (x - 38) / 18, d = Math.round(9 * Math.sqrt(Math.max(0, 1 - t * t))); R(x, 171, 1, d, '#2f6f99'); }
    R(4, 159, 2, 4, '#7d786d'); R(70, 159, 2, 4, '#7d786d'); R(4, 159, 68, 1, '#8d8a80');
    // torre de pedra com lanterna (Torre VIOS)
    { const X = Component.TOWER.x * 16, Y = Component.TOWER.y * 16;
      R(X + 3, Y + 62, 26, 2, 'rgba(0,0,0,.25)');
      R(X + 5, Y + 18, 22, 46, '#a39d90');
      for (let y = Y + 18; y < Y + 64; y += 5) { R(X + 5, y, 22, 1, '#7f7a6e'); for (let x = X + 5 + ((y / 5) % 2 ? 0 : 3); x < X + 27; x += 7) R(x, y, 1, 5, '#7f7a6e'); }
      R(X + 22, Y + 18, 5, 46, 'rgba(0,0,0,.12)');
      for (let y = Y + 4; y < Y + 19; y++) { const w = Math.round(2 + (y - Y - 4) * 0.8); R(X + 16 - w, y, 2 * w, 1, '#a5432f'); }
      R(X + 13, Y - 1, 6, 5, '#3a2f25'); R(X + 14, Y, 4, 3, '#f0c46a');
      R(X + 12, Y + 50, 8, 14, '#5a3a20'); R(X + 12, Y + 49, 8, 1, '#3a2418');
      R(X + 14, Y + 30, 3, 7, '#2b2b2b'); }
  }
""")

# 5) etapa 2: o nome na tela vira Sam (o código interno e os eventos continuam "ultron") e a cor dele
if ETAPA2:
    troca("dotColor: vi === 0 ? (off ? '#5a5f67' : '#ff5a3c') : '#5a5f67'", "dotColor: vi === 0 ? (off ? '#5a5f67' : '#fdc155') : '#5a5f67'", 2)
    t = t.replace("página Ultron", "página do Sam").replace("Ultron", "Sam").replace("ULTRON", "SAM")
linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 01 no campo, com o Sam, em", caminho)
