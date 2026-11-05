"""Vila 05 (Orelha) vira o parque dos cães, cheio de brinquedos, com a casinha do Orelha.

O fundo da vila genérica (prédios cinza, lotes e torre de metal) é trocado por um parque:
- cerca de madeira branca em volta (com o portão à esquerda, por onde passa o caminho das vilas),
  grama com flores e caminhos de areia com marcas de pata;
- **Casinha do Orelha** (antes "Doca 01 · Orelha"): casinha de madeira azul com telhado vermelho,
  plaquinha "ORELHA" em cima da porta, lanterna (a luz da doca), pote de ração e pote de água;
- **Calendário**: mural de madeira com o calendário, bilhetes e a foto do Orelha (lendo o
  calendário, um dia acende por vez);
- **Intimações**: caixa de correio vermelha; lendo, as cartas saem voando; no fim a bandeirinha
  sobe vermelha (achado grave) ou verde;
- **Relatório**: toalha de piquenique xadrez com a cesta (a folha do relatório sai em cima dela);
- **Planilhas**: baú de brinquedos com a pilha do Albi em cima e os baldes verde, âmbar e cinza;
- **Torre VIOS**: torre de parquinho com escorregador e a luz na antena;
- **Arquivo**: armário de madeira com três gavetas, onde ficam guardados os relatórios;
- brinquedos espalhados: piscina de bolinhas, caixa de areia com osso enterrado, barreira de
  agility, prateleira de brinquedos, hidrante, pneu, frisbee, ossos, bolinhas de tênis, corda,
  argola e galinha de borracha;
- parte animada: a bolinha quicando, bolinhas pulando na piscina, borboletas, a água do pote
  brilhando e a lanterna da casinha.
Onde o Orelha anda e os postos (Calendário, Intimações, Torre VIOS, Planilhas, Relatório) não
mudam, então os eventos, as falas e o painel continuam iguais.

uso: python3 doc/vila/ligar_vila05_parque.py bot/vila/vila.html
(depois de todos os outros, inclusive o ligar_orelha.py e o ligar_jarvis.py, e antes do
ligar_orelha_agenda.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "drawParque(c, f)" in t:
    sys.exit("a Vila 05 já é o parque do Orelha")
if "fhandle(ev)" not in t or "paintArena(c)" not in t:
    sys.exit("rode antes o ligar_vila03_arena.py e o ligar_orelha.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) a lanterna da casinha no lugar da luz da doca, e a parte animada do parque
troca("      R(O5 + 63, 4, 3, 3, (f >> 5) % 2 ? teal : '#2c6c66');\n",
      "      this.drawParque(c, f);\n"
      "      R(O5 + 78, 41, 3, 3, (f >> 5) % 2 ? '#ffd27a' : '#8a5a2c');\n")

# 2) Calendário: um dia do mural acende por vez
troca("""      if (ffx === 'cal') {
        [132, 164, 180].forEach((wx, j) => {
          const x = O5 + wx; R(x, 36, 8, 7, '#f6f1e6'); R(x, 36, 8, 2, '#c81e14');
          for (let k = 0; k < 6; k++) R(x + 1 + (k % 3) * 2, 39 + Math.floor(k / 3) * 2, 1, 1, (Math.floor(ct / 8) + j) % 6 === k ? teal : '#9aa0a8');
        });
        for (let i = 0; i < 4; i++) R(O5 + 148 + ((ct * 3 + i * 11) % 9), 52 + ((ct + i * 5) % 8), 1, 1, i % 2 ? teal : '#ffffff');
      }""", """      if (ffx === 'cal') {
        const k = Math.floor(ct / 6) % 18; R(O5 + 137 + (k % 6) * 4, 31 + Math.floor(k / 6) * 5, 3, 3, teal);
        for (let i = 0; i < 4; i++) R(O5 + 134 + ((ct * 3 + i * 11) % 30), 24 + ((ct + i * 5) % 22), 1, 1, i % 2 ? teal : '#ffffff');
      }""")

# 3) Intimações: a caixa de correio (cartas voando enquanto lê; bandeirinha vermelha ou verde no fim)
troca("""      if (ffx === 'int') for (let i = 0; i < 5; i++) R(O5 + SX + 3, SY + 3 + ((i * 3 + (f >> 2)) % 11), 4 + ((i * 7 + (f >> 3)) % 16), 1, i % 3 === 0 ? teal : '#d4d8de');
      else if (rI && rI.st === 'feito') {
        for (let i = 0; i < 4; i++) R(O5 + SX + 3, SY + 3 + i * 3, 14 + (i * 5) % 7, 1, '#9aa0a8');
        R(O5 + SX + 21, SY + 3, 2, 2, rI.g ? '#ff5a3c' : '#3fd17a');
      } else if ((f >> 6) % 2) R(O5 + SX + 3, SY + 3, 2, 1, '#5a616b');""",
      """      if (rI && rI.st === 'feito' && ffx !== 'int') {
        const cor = rI.g ? '#e8483c' : '#3fd17a';
        R(O5 + 261, 24, 1, 15, '#3b2614'); R(O5 + 262, 24, 7, 5, cor); R(O5 + 262, 28, 7, 1, 'rgba(0,0,0,.25)');
      } else { R(O5 + 259, 37, 10, 1, '#3b2614'); R(O5 + 265, 34, 4, 3, '#e8b923'); }
      if (ffx === 'int') for (let i = 0; i < 3; i++) {
        const k = ((ct + i * 20) % 60) / 60, x = O5 + 228 - k * 18, y = 33 - k * 16 + Math.sin(k * 9 + i) * 2;
        R(x, y, 5, 4, '#f6f1e6'); R(x, y, 5, 1, '#c9c2b2'); R(x + 3, y + 1, 1, 1, '#c81e14');
      } else if ((f >> 6) % 2) R(O5 + 229, 34, 3, 3, '#f6f1e6');""")

# 4) placas no parque
troca("""      if (v === 2) { // arena do Albi""", """      if (v === 4) { // parque do Orelha
        plaques.push(P(83.5, 1.55, 'Casinha do Orelha'), P(90, 1.25, 'Calendário'), P(95.6, 1.25, 'Intimações'),
          P(85.5, 5.0, 'Relatório'), P(92.5, 5.0, 'Planilhas'), P(96, 4.6, 'Arquivo'), P(96, 8.65, 'Torre VIOS'));
        continue;
      }
      if (v === 2) { // arena do Albi""")

# 5) ele volta para a casinha (antes: "à doca")
troca("this.fst('Voltando à doca');", "this.fst('Voltando para a casinha');")
troca("    this.W = W;\n", "    // Vila 05: o arquivo dos relatórios (colunas 15 e 16, linhas 5 e 6) não dá passagem\n"
      "    for (const [x, y] of [[95, 5], [96, 5], [95, 6], [96, 6]]) this.blocked[y][x] = true;\n    this.W = W;\n")

# 6) o fundo do parque (parte fixa) e a parte animada
troca("""    this.paintArena(c);
  }
""", r"""    this.paintArena(c);
    this.paintParque(c);
  }

  // parque do Orelha (Vila 05): x local 0–319 + 1280; os blocos de onde ele não anda são os mesmos
  // da vila genérica (casinha, mural, correio, toalha, baú, piscina de bolinhas, caixa de areia e torre)
  paintParque(c) {
    const O = 1280, M = Component.MAP;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    const at = (tx, ty) => (M[ty] && M[ty][80 + tx]) || 'B';
    const hs = (x, y, k) => (((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) >>> 0);
    const disco = (cx, cy, r, col) => { for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y + r * .4)); R(cx - w, cy + y, 2 * w + 1, 1, col); } };
    const pata = (x, y, col) => { R(x + 1, y + 2, 3, 2, col); R(x, y + 1, 1, 1, col); R(x + 1, y, 1, 1, col); R(x + 3, y, 1, 1, col); R(x + 4, y + 1, 1, 1, col); };
    const osso = (x, y, col, sh) => { R(x, y, 2, 1, col); R(x + 8, y, 2, 1, col); R(x + 1, y + 1, 8, 1, col); R(x, y + 2, 2, 1, sh); R(x + 8, y + 2, 2, 1, sh); R(x + 2, y + 2, 6, 1, sh); };
    const bola = (x, y, col, luz) => { R(x + 1, y, 2, 1, col); R(x, y + 1, 4, 2, col); R(x + 1, y + 3, 2, 1, col); R(x + 1, y + 1, 1, 1, luz); };
    const tenis = (x, y) => { bola(x, y, '#cfe23a', '#f1f7a8'); R(x + 3, y + 1, 1, 1, '#f6f1e6'); R(x + 2, y + 2, 1, 1, '#f6f1e6'); };
    const GR = '#86c95f', GR2 = '#74b850', GR3 = '#9bd873', SOMBRA = '#6aa84a', AREIA = '#e7cf98', BORDA = '#caad72';
    // chão: grama com flores, caminhos de areia com patinhas e a cerca branca de madeira em volta
    for (let ty = 0; ty < 14; ty++) for (let tx = 0; tx < 20; tx++) {
      const ch = at(tx, ty), X = tx * 16, Y = ty * 16, h = hs(tx, ty, 7);
      R(X, Y, 16, 16, GR);
      for (let k = 0; k < 6; k++) { const q = hs(tx, ty, k); R(X + q % 15, Y + (q >> 4) % 15, k % 3 ? 2 : 1, 1, k % 2 ? GR2 : GR3); }
      if (ch === 'P') {
        const isP = (a, b) => at(a, b) === 'P';
        R(X, Y, 16, 16, AREIA);
        if (!isP(tx, ty - 1)) R(X, Y, 16, 1, BORDA); if (!isP(tx, ty + 1)) R(X, Y + 15, 16, 1, BORDA);
        if (!isP(tx - 1, ty)) R(X, Y, 1, 16, BORDA); if (!isP(tx + 1, ty)) R(X + 15, Y, 1, 16, BORDA);
        for (let k = 0; k < 3; k++) { const q = hs(tx, ty, 20 + k); R(X + 2 + q % 12, Y + 2 + (q >> 5) % 12, 1, 1, k % 2 ? '#d6bb80' : '#f3e2b4'); }
        if (h % 3 === 0) pata(X + 4 + (h >> 3) % 6, Y + 5 + (h >> 6) % 5, '#d2b47a');
        continue;
      }
      if (ch !== 'B') {
        if (h % 5 === 0) { const fx = X + 3 + (h >> 4) % 10, fy = Y + 3 + (h >> 8) % 10, fc = ['#ffffff', '#f7e27a', '#f4a6c0'][(h >> 2) % 3]; R(fx, fy, 1, 1, fc); R(fx - 1, fy + 1, 3, 1, fc); R(fx, fy + 2, 1, 1, fc); R(fx, fy + 1, 1, 1, '#e8b923'); }
        continue;
      }
      if (ty === 0 || ty === 13) { // cerca de frente: estacas pontudas e duas travessas
        if (ty === 0) { R(X, Y, 16, 5, '#a9dcf5'); R(X, Y + 3, 16, 3, '#5fa04a'); }
        R(X, Y + 14, 16, 2, SOMBRA);
        for (let i = 0; i < 16; i += 4) { R(X + i, Y + 6, 3, 9, '#f4efe2'); R(X + i + 1, Y + 5, 1, 1, '#f4efe2'); R(X + i + 2, Y + 7, 1, 8, '#d9d0bd'); }
        R(X, Y + 8, 16, 2, '#e6dfcc'); R(X, Y + 12, 16, 2, '#e6dfcc'); R(X, Y + 10, 16, 1, '#c4bba6');
      } else { // cerca do lado, vista de cima, com arbustos do lado de fora
        const fora = tx === 0 ? 0 : 11;
        R(X + fora, Y, 5, 16, '#4f9a3c'); R(X + fora + 1, Y + (h % 8), 3, 4, '#5fae48');
        const cx = tx === 0 ? X + 6 : X + 4;
        R(cx, Y, 6, 16, '#d9d0bd');
        for (let j = 0; j < 16; j += 4) { R(cx, Y + j, 6, 3, '#f4efe2'); R(cx, Y + j + 3, 6, 1, '#c4bba6'); }
        R(tx === 0 ? cx + 6 : cx - 1, Y, 1, 16, SOMBRA);
      }
    }
    // portão (onde o caminho sai para a Vila 04): mourões dos dois lados
    [4, 8].forEach(ty => { if (at(0, ty) === 'P') { R(5, ty * 16 - 3, 6, 5, '#f4efe2'); R(5, ty * 16 + 15, 6, 5, '#f4efe2'); R(6, ty * 16 - 4, 4, 1, '#d9d0bd'); R(6, ty * 16 + 14, 4, 1, '#d9d0bd'); } });

    // Casinha do Orelha (Doca 01): a porta fica na coluna 3, onde ele para
    R(30, 61, 54, 4, SOMBRA);
    R(36, 36, 40, 26, '#5b9bc4');
    for (let y = 40; y < 62; y += 5) R(37, y, 38, 1, '#4a83a8');
    R(36, 36, 1, 26, '#7fb6d9'); R(75, 36, 1, 26, '#3f7396');
    R(34, 61, 44, 3, '#8a5a2c'); R(34, 61, 44, 1, '#b07a3a');
    for (let i = 0; i <= 24; i++) {
      const y = 13 + i, hw = Math.round(i * 27 / 24);
      R(56 - hw, y, hw * 2 + 1, 1, i % 4 === 3 ? '#a83a2d' : '#c94b3b');
      R(56 - hw, y, 1, 1, '#7d2a1f'); R(56 + hw, y, 1, 1, '#7d2a1f');
    }
    R(29, 37, 55, 2, '#7d2a1f'); R(54, 11, 5, 3, '#7d2a1f'); R(55, 10, 3, 1, '#a83a2d');
    R(41, 37, 30, 10, '#6e4420'); R(42, 38, 28, 8, '#f4e6c4');
    const LET = { O: ['XXX', 'X.X', 'X.X', 'X.X', 'XXX'], R: ['XX.', 'X.X', 'XX.', 'X.X', 'X.X'], E: ['XXX', 'X..', 'XX.', 'X..', 'XXX'],
      L: ['X..', 'X..', 'X..', 'X..', 'XXX'], H: ['X.X', 'X.X', 'XXX', 'X.X', 'X.X'], A: ['.X.', 'X.X', 'XXX', 'X.X', 'X.X'] };
    'ORELHA'.split('').forEach((ch, n) => LET[ch].forEach((row, j) => row.split('').forEach((q, i) => { if (q === 'X') R(45 + n * 4 + i, 39 + j, 1, 1, '#8a3a2a'); })));
    for (let y = 47; y < 61; y++) { const hw = y === 47 ? 5 : y === 48 ? 7 : y === 49 ? 8 : 9; R(56 - hw, y, hw * 2, 1, '#f4efe2'); }
    for (let y = 48; y < 61; y++) { const hw = y === 48 ? 4 : y === 49 ? 6 : y === 50 ? 7 : 8; R(56 - hw, y, hw * 2, 1, '#2a1d16'); }
    R(50, 54, 12, 7, '#1d140f');
    R(79, 37, 1, 4, '#3b2614'); R(77, 40, 5, 1, '#3b2614');
    // pote de ração (ao lado da porta) e pote de água (do outro lado)
    R(80, 56, 12, 2, '#9a6234'); R(82, 55, 8, 1, '#b07a3a'); R(79, 58, 14, 4, '#d23c3c'); R(80, 62, 12, 1, '#8f241f'); R(80, 58, 12, 1, '#ef6a5e');
    osso(81, 59, '#f6f1e6', '#f6f1e6');
    R(18, 58, 12, 4, '#3d7fd1'); R(19, 62, 10, 1, '#2a5a99'); R(19, 57, 10, 1, '#9fe0ff'); R(18, 58, 12, 1, '#7fb3ea');

    // Calendário: mural de madeira com o calendário, bilhetes e a foto do Orelha
    R(128, 62, 64, 2, SOMBRA);
    R(134, 44, 4, 19, '#7a4a22'); R(182, 44, 4, 19, '#7a4a22'); R(134, 44, 1, 19, '#9a6234'); R(182, 44, 1, 19, '#9a6234');
    R(126, 16, 68, 4, '#4f8a3a'); R(127, 15, 66, 1, '#6fb14c'); R(126, 20, 68, 1, '#3a6a2b');
    R(129, 21, 62, 30, '#7a4a22'); R(131, 23, 58, 26, '#d8b27a');
    for (let k = 0; k < 18; k++) { const q = hs(k, 3, 9); R(132 + q % 56, 24 + (q >> 6) % 24, 1, 1, '#c49a5e'); }
    R(135, 25, 28, 21, '#f6f1e6'); R(135, 25, 28, 4, '#c81e14'); R(135, 45, 28, 1, '#c9c2b2');
    R(140, 24, 1, 2, '#3b2614'); R(157, 24, 1, 2, '#3b2614');
    for (let j = 0; j < 3; j++) for (let i = 0; i < 6; i++) R(137 + i * 4, 31 + j * 5, 3, 3, i === 2 && j === 1 ? '#e88a7a' : '#d6d0c2');
    R(166, 25, 9, 8, '#f7e27a'); R(170, 25, 1, 1, '#c81e14'); R(167, 28, 7, 1, '#c9a84a'); R(167, 30, 5, 1, '#c9a84a');
    R(177, 27, 10, 9, '#f4a6c0'); R(181, 27, 1, 1, '#2f69b3'); pata(179, 30, '#d9708f');
    R(167, 36, 11, 11, '#ffffff'); R(168, 37, 9, 7, '#8fc6e8'); R(168, 42, 9, 2, '#86c95f'); R(170, 40, 4, 2, '#40362f'); R(173, 39, 2, 2, '#40362f'); R(170, 41, 2, 1, '#c98a4b');
    R(180, 39, 7, 6, '#ffffff'); R(181, 41, 5, 1, '#9aa0a8'); R(181, 43, 3, 1, '#9aa0a8');

    // Intimações: caixa de correio vermelha num poste, e a prateleira de brinquedos ao lado
    R(232, 62, 32, 2, SOMBRA);
    R(244, 44, 5, 19, '#7a4a22'); R(244, 44, 1, 19, '#9a6234');
    R(235, 25, 22, 2, '#c93a32'); R(233, 27, 26, 2, '#c93a32'); R(232, 29, 28, 15, '#c93a32');
    R(235, 26, 20, 1, '#e26a5e'); R(233, 28, 24, 1, '#e26a5e'); R(232, 43, 28, 1, '#8f241f');
    R(231, 28, 3, 16, '#a82d27'); R(230, 34, 1, 3, '#3b2614');
    R(241, 33, 9, 6, '#f6f1e6'); R(241, 33, 9, 1, '#c9c2b2'); R(242, 34, 1, 1, '#c9c2b2'); R(243, 35, 3, 1, '#c9c2b2'); R(246, 34, 1, 1, '#c9c2b2'); R(248, 34, 1, 1, '#c81e14');
    R(272, 28, 14, 34, '#8a5a2c'); R(274, 30, 10, 30, '#5a3a1c'); R(272, 28, 14, 2, '#6e4420');
    [38, 48, 58].forEach(y => R(272, y, 14, 2, '#b07a3a'));
    bola(275, 34, '#e8483c', '#ff9a8a'); tenis(280, 34);
    osso(274, 44, '#f6f1e6', '#d9d0bd');
    for (let i = 0; i < 8; i++) R(275 + i, 54 + (i % 2), 1, 2, i % 3 === 1 ? '#f6f1e6' : '#3fb8e8');

    // Relatório: toalha de piquenique xadrez com a cesta e petiscos
    R(64, 124, 48, 2, SOMBRA);
    R(66, 84, 44, 40, '#f6f1e6');
    for (let j = 0; j < 10; j++) for (let i = 0; i < 11; i++) { const a = i % 2 === 0, b = j % 2 === 0; if (a || b) R(66 + i * 4, 84 + j * 4, 4, 4, a && b ? '#d9463c' : '#ec8a80'); }
    for (let x = 66; x < 110; x += 3) { R(x, 124, 1, 2, '#ec8a80'); R(x, 82, 1, 2, '#ec8a80'); }
    R(70, 92, 15, 10, '#b07a3a'); R(70, 92, 15, 2, '#8a5a2c');
    for (let x = 72; x < 85; x += 3) R(x, 95, 1, 7, '#8a5a2c');
    R(72, 86, 1, 6, '#8a5a2c'); R(82, 86, 1, 6, '#8a5a2c'); R(72, 86, 11, 1, '#8a5a2c');
    R(73, 90, 4, 2, '#f6f1e6'); R(78, 89, 4, 3, '#e8b923');
    osso(92, 92, '#f6f1e6', '#d9d0bd'); osso(95, 100, '#c98a4b', '#9a6234');
    R(98, 108, 6, 5, '#ffffff'); R(98, 108, 6, 1, '#d9d0bd'); R(99, 109, 4, 3, '#9fe0ff');

    // Planilhas: baú de brinquedos (a pilha do Albi fica em cima da tampa e os baldes na frente)
    R(176, 112, 48, 2, SOMBRA);
    R(178, 95, 44, 17, '#a8642e'); R(178, 103, 44, 1, '#6e4420'); R(178, 111, 44, 1, '#6e4420');
    R(176, 89, 48, 6, '#8a5a2c'); R(177, 89, 46, 1, '#b9793e'); R(176, 94, 48, 1, '#5a3a1c');
    R(176, 89, 2, 6, '#d9b44a'); R(222, 89, 2, 6, '#d9b44a'); R(178, 95, 2, 16, '#d9b44a'); R(220, 95, 2, 16, '#d9b44a');
    R(198, 95, 4, 4, '#d9b44a'); R(199, 97, 2, 1, '#5a3a1c');
    pata(184, 98, '#d39a5c'); pata(212, 98, '#d39a5c');
    R(206, 95, 2, 6, '#e05a4e'); R(206, 101, 2, 2, '#f6f1e6'); R(205, 103, 4, 2, '#e05a4e');
    tenis(214, 85);
    osso(178, 86, '#f08ac0', '#c95f8a');

    // piscina de bolinhas (onde era a Doca 04)
    R(80, 191, 48, 2, SOMBRA);
    R(81, 161, 46, 30, '#3d7fd1'); R(81, 161, 46, 2, '#7fb3ea'); R(81, 189, 46, 2, '#2a5a99');
    R(84, 164, 40, 24, '#2f69b3');
    const CB = ['#e8483c', '#f2c230', '#3fb8e8', '#5fc45a', '#f08ac0', '#f6f1e6'];
    for (let j = 0; j < 6; j++) for (let i = 0; i < 10; i++) { const q = hs(i, j, 11); bola(84 + i * 4 + (j % 2) * 2 - 1 + (q % 2), 164 + j * 4 - (q >> 3) % 2, CB[q % CB.length], '#ffffff'); }

    // caixa de areia com um osso enterrado, balde e pazinha
    R(16, 191, 48, 2, SOMBRA);
    R(17, 145, 46, 46, '#8a5a2c'); R(17, 145, 46, 1, '#b07a3a'); R(19, 147, 42, 42, '#ead7a4');
    for (let k = 0; k < 30; k++) { const q = hs(k, 1, 13); R(20 + q % 40, 148 + (q >> 6) % 40, 1, 1, k % 2 ? '#d9c08a' : '#f6e8c0'); }
    disco(46, 172, 5, '#c9ae76'); disco(46, 173, 3, '#a88f5c'); R(38, 163, 6, 3, '#d9c08a');
    osso(26, 158, '#f6f1e6', '#d9d0bd'); R(31, 160, 6, 2, '#ead7a4');
    R(24, 177, 7, 7, '#e8483c'); R(23, 176, 9, 1, '#b8352c'); R(25, 178, 1, 5, '#ff8a7a'); R(26, 173, 5, 1, '#3b2614');
    R(52, 152, 1, 8, '#7a4a22'); R(51, 159, 3, 4, '#f2c230');

    // Arquivo dos relatórios: armário de madeira com telhadinho, três gavetas e puxador de osso
    R(238, 112, 36, 2, SOMBRA);
    for (let i = 0; i <= 6; i++) { const hw = 5 + i * 2.4; R(256 - hw, 77 + i, hw * 2, 1, i % 3 === 2 ? '#a83a2d' : '#c94b3b'); }
    R(240, 84, 32, 1, '#7d2a1f');
    R(242, 85, 28, 26, '#6e4420'); R(243, 86, 26, 24, '#a8642e'); R(243, 86, 1, 24, '#c98a4b');
    [87, 95, 103].forEach(y => {
      R(245, y, 22, 7, '#c98a4b'); R(245, y + 6, 22, 1, '#8f5a2c'); R(245, y, 22, 1, '#e2ad72');
      R(247, y + 2, 4, 3, '#f6f1e6'); R(248, y + 3, 2, 1, '#9aa0a8');
      R(254, y + 3, 6, 1, '#f6f1e6'); R(253, y + 2, 1, 1, '#f6f1e6'); R(253, y + 4, 1, 1, '#f6f1e6'); R(260, y + 2, 1, 1, '#f6f1e6'); R(260, y + 4, 1, 1, '#f6f1e6');
    });
    R(243, 110, 3, 2, '#5a3a1c'); R(266, 110, 3, 2, '#5a3a1c');
    pata(254, 79, '#f4e6c4');
    // barreira de agility (na grama de baixo), galinha de borracha e o hidrante
    R(186, 168, 36, 2, SOMBRA);
    R(188, 150, 2, 18, '#f6f1e6'); R(216, 150, 2, 18, '#f6f1e6'); R(186, 167, 6, 2, '#d9d0bd'); R(214, 167, 6, 2, '#d9d0bd');
    for (let y = 152; y < 166; y += 4) { R(188, y, 2, 2, '#e8483c'); R(216, y, 2, 2, '#e8483c'); }
    for (let x = 190; x < 216; x += 4) R(x, 157, 4, 2, (x / 4) % 2 ? '#f6f1e6' : '#e8483c');
    R(244, 119, 8, 3, '#f2d23a'); R(250, 116, 3, 3, '#f2d23a'); R(251, 115, 2, 1, '#e8483c'); R(253, 117, 1, 1, '#f08a2a'); R(251, 117, 1, 1, '#2a1d16'); R(246, 122, 1, 2, '#f08a2a'); R(249, 122, 1, 2, '#f08a2a');
    R(285, 168, 18, 3, '#8fd0f5'); R(287, 167, 14, 1, '#bde6fb');
    R(289, 152, 10, 16, '#d23c3c'); R(288, 149, 12, 3, '#b8352c'); R(291, 147, 6, 2, '#d23c3c'); R(293, 146, 2, 1, '#b8352c');
    R(286, 156, 3, 4, '#b8352c'); R(299, 156, 3, 4, '#b8352c'); R(287, 166, 14, 2, '#8f241f'); R(290, 152, 1, 14, '#ef6a5e');

    // Torre VIOS: torre de parquinho com cabine, telhado azul, escorregador e antena (a luz pisca em cima)
    R(238, 201, 64, 3, SOMBRA);
    for (let i = 0; i < 30; i++) { R(270 + i, 172 + i, 1, 4, '#e8483c'); R(270 + i, 172 + i, 1, 1, '#ff8a7a'); R(270 + i, 176 + i, 1, 1, '#b8352c'); }
    R(242, 156, 3, 46, '#7a4a22'); R(267, 156, 3, 46, '#7a4a22');
    for (let y = 178; y < 200; y += 5) R(245, y, 22, 1, '#9a6234');
    R(243, 156, 26, 15, '#e9c46a'); R(243, 156, 26, 1, '#f6dc94'); R(250, 159, 12, 8, '#1d2733'); R(251, 160, 10, 1, '#3fb8c8'); R(251, 163, 7, 1, '#3fb8c8');
    R(240, 171, 32, 4, '#a8642e'); R(240, 171, 32, 1, '#c98a4b');
    for (let i = 0; i <= 9; i++) { const hw = Math.round(2 + i * 16 / 9); R(256 - hw, 147 + i, hw * 2, 1, i % 3 === 2 ? '#2f69b3' : '#3d7fd1'); }
    R(255, 145, 2, 3, '#3b2614');

    // brinquedos espalhados pela grama
    for (let i = 0; i < 10; i++) R(100 + i, 46 + (i % 2), 1, 2, i % 3 === 1 ? '#f6f1e6' : '#e05a4e');
    R(98, 45, 3, 4, '#e05a4e'); R(110, 45, 3, 4, '#e05a4e');
    tenis(116, 28); tenis(206, 54); tenis(294, 108); tenis(152, 186);
    R(198, 38, 12, 3, '#3d7fd1'); R(200, 37, 8, 1, '#3d7fd1'); R(200, 41, 8, 1, '#2f69b3'); R(201, 38, 6, 1, '#7fb3ea');
    osso(194, 23, '#f08ac0', '#c95f8a'); osso(116, 112, '#f6f1e6', '#d9d0bd'); osso(18, 100, '#f6f1e6', '#d9d0bd'); osso(160, 152, '#c98a4b', '#9a6234');
    bola(54, 104, '#3fb8e8', '#bde6fb'); bola(166, 96, '#e8483c', '#ff9a8a'); bola(296, 28, '#f2c230', '#fff1a8');
    disco(230, 187, 4, '#f08ac0'); disco(230, 187, 1, GR);
    disco(176, 178, 7, '#2b2b2b'); disco(176, 178, 5, '#444444'); disco(176, 178, 3, GR); R(170, 174, 2, 1, '#5a5a5a');
  }
  drawParque(c, f) {
    const O = 1280;
    const R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    // a bolinha de tênis quicando na grama
    const q = Math.abs(Math.sin(f * 0.06)), by = 110 - q * 14;
    R(126 - q, 114, 5 + q * 2, 1, 'rgba(0,0,0,.18)');
    R(127, by, 2, 1, '#cfe23a'); R(126, by + 1, 4, 2, '#cfe23a'); R(127, by + 3, 2, 1, '#cfe23a'); R(127, by + 1, 1, 1, '#f1f7a8');
    // bolinhas pulando na piscina
    const CB = ['#e8483c', '#f2c230', '#3fb8e8', '#5fc45a', '#f08ac0'];
    for (let i = 0; i < 2; i++) {
      const p = (f + i * 47) % 90; if (p >= 24) continue;
      const k = p / 24, x = 88 + ((Math.floor((f + i * 47) / 90) * 13 + i * 17) % 34), y = 168 - Math.sin(k * Math.PI) * 9;
      R(x + 1, y, 2, 1, CB[(i + Math.floor(f / 90)) % 5]); R(x, y + 1, 4, 2, CB[(i + Math.floor(f / 90)) % 5]); R(x + 1, y + 3, 2, 1, CB[(i + Math.floor(f / 90)) % 5]);
    }
    // borboletas
    [[150, 120, 0, '#f7e27a'], [60, 140, 2.1, '#f4a6c0']].forEach(([cx, cy, ph, col]) => {
      const t = f * 0.012 + ph, x = cx + Math.sin(t) * 40, y = cy + Math.sin(t * 1.7) * 14, asa = Math.floor(f / 6) % 2;
      R(x, y, 1, 3, '#3b2614'); R(x - 2, y + (asa ? 0 : 1), 2, 2, col); R(x + 1, y + (asa ? 0 : 1), 2, 2, col);
    });
    // a água do pote brilhando e a gota do hidrante
    if ((f >> 4) % 2) R(20 + (f >> 3) % 7, 57, 2, 1, '#ffffff');
    const g = (f % 80) / 80; if (g < 0.5) R(301, 158 + g * 20, 1, 2, '#8fd0f5');
  }
""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 05 virou o parque do Orelha em", caminho)
