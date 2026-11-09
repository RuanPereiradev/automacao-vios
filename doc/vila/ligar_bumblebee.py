"""Vila 02: o Zangão vira o BUMBLEBEE, um robô amarelo que se transforma em carro para andar.

Desenho e transformação: doc/mascote/zangao-transforma.html (robô 24×26 de frente; carro 30×12
de lado). Parado, ele é o robô (pisca e mexe as asas-porta); quando vai andar, as peças voam e
encaixam no chassi (robô → carro) e só então ele sai rodando; ao chegar, desfaz (carro → robô).
Também troca o nome "Zangão" por "Bumblebee" no que a vila mostra (fala, placa, abas, registro).
O código interno continua "zangao" (eventos bot: "zangao", rotas /zangao, ZANGAO_PASTA).

uso: python3 doc/vila/ligar_bumblebee.py bot/vila/vila.html
(depois do ligar_zangao.py e do ligar_albi.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "BROBOT" in t:
    sys.exit("a vila já está com o Bumblebee")
if "zhandle(ev)" not in t or "ahandle(ev)" not in t:
    sys.exit("rode antes o doc/vila/ligar_zangao.py e o doc/vila/ligar_albi.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) sprites do Bumblebee (iguais aos de doc/mascote/zangao-transforma.html)
troca("  static SPR = (() => {", r"""  static BROBOT = [
    '.........KKKKKK.........', '........KYYYYYYK........', '.......KYYYYYYYYK.......', '.......KYKKKKKKYK.......',
    '.......KYKBEBEKYK.......', '.......KYKKKKKKYK.......', '........KYGGGGYK........', '.........KKKKKK.........',
    'LLLL....KKYYYYKK....LLLL', 'LBBL...KYYYYYYYYK...LBBL', 'LBBL..KYYYKKKKYYYK..LBBL', 'LBBL..KYYKWWWWKYYK..LBBL',
    'LLLL..KYYKGGGGKYYK..LLLL', '..K...KYYYKKKKYYYK...K..', '..KKKKKYYYYYYYYYYKKKKK..', '..KYYKKYYYYYYYYYYKKYYK..',
    '..KYYK.KKKKKKKKKK.KYYK..', '..KYYK.KYYYKKYYYK.KYYK..', '..KKKK.KYYYK.KYYYK.KKKK.', '.......KYYYK.KYYYK......',
    '.......KYYYK.KYYYK......', '.......KKKKK.KKKKK......', '.......KGGGK.KGGGK......', '.......KGGGK.KGGGK......',
    '......KKKKKK.KKKKKK.....', '......KDDDDK.KDDDDK.....'
  ];
  static BCAR = [
    '..............................', '..............................', '.........KKKKKKKKKKKK.........',
    '.......KKBBBBBBBBBBBBKK.......', '......KYBBBBBBBBBBBBBBYK......', '.....KYYKKKKKKKKKKKKKKYYKK....',
    '..KKKYYYYYYYYYYYYYYYYYYYYYKKK.', '.KYYYYYYYYYYYYYYYYYYYYYYYYYYHK', '.KYYYYYYYYYYYYYYYYYYYYYYYYYYRK',
    '.KKKKKKKKKKKKKKKKKKKKKKKKKKKKK', '...KDDK..............KDDK.....', '...KDDK..............KDDK.....'
  ];
  static BPAL = { Y: '#e8b923', H: '#fff1a8', K: '#1d1e21', B: '#3d8bff', E: '#cfeaff', W: '#8fc3e0', G: '#8c939c', L: '#5a616b', D: '#4a4f57', R: '#ff5a3c' };
  // peças: recorte no robô (rx, ry, rw, rh) -> canto no carro (cx, cy, relativo ao centro / chão); rot = voltas; d = atraso
  static BPARTS = [
    { rx: 7, ry: 0, rw: 10, rh: 8, cx: 9, cy: 2, rot: 0.5, d: 0.00 }, { rx: 6, ry: 8, rw: 12, rh: 9, cx: -2, cy: 6, rot: 0, d: 0.08 },
    { rx: 0, ry: 8, rw: 4, rh: 5, cx: -9, cy: 3, rot: 1, d: 0.12 }, { rx: 20, ry: 8, rw: 4, rh: 5, cx: 6, cy: 3, rot: 1, d: 0.12 },
    { rx: 2, ry: 13, rw: 4, rh: 6, cx: -15, cy: 6, rot: 0.5, d: 0.18 }, { rx: 18, ry: 13, rw: 4, rh: 6, cx: 11, cy: 6, rot: 0.5, d: 0.18 },
    { rx: 7, ry: 17, rw: 5, rh: 9, cx: -12, cy: 8, rot: 0.25, d: 0.26 }, { rx: 13, ry: 17, rw: 5, rh: 9, cx: 6, cy: 8, rot: 0.25, d: 0.26 }
  ];
  static SPR = (() => {""")

# 2) estado: m = 0 robô … 1 carro; hd = último lado (1 direita, -1 esquerda)
troca("this.z = { x: 23 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 120, i: 0, bubble: null, carry: false, fx: null, progress: null };",
      "this.z = { x: 23 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 120, i: 0, bubble: null, carry: false, fx: null, progress: null, m: 0, hd: 1 };")

# 3) só anda depois de virar carro (nos passos da execução e no passeio)
troca("    const sp = 1.1 * (this.props.speed ?? 1) * this.zpressa(), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;",
      "    if ((z.m || 0) < 0.9) return; // Bumblebee: primeiro vira carro\n"
      "    const sp = 1.1 * (this.props.speed ?? 1) * this.zpressa(), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;")
troca("    const sp = 0.8 * (this.props.speed ?? 1), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;",
      "    if ((z.m || 0) < 0.9) return; // Bumblebee: primeiro vira carro\n"
      "    const sp = 0.8 * (this.props.speed ?? 1), [tx, ty] = z.path[0], px = tx * 16, py = ty * 16, dx = px - z.x, dy = py - z.y;")
troca("    if (this.zcur) this.zstep(); else if (this.zevq.length) this.zhandle(this.zevq.shift()); else this.patrol();",
      "    if (this.zcur) this.zstep(); else if (this.zevq.length) this.zhandle(this.zevq.shift()); else this.patrol();\n"
      "    { // Bumblebee: transforma em carro quando tem caminho, volta a robô parado (mais rápido com fila grande)\n"
      "      const z = this.z, alvo = z.path.length > 0 && z.wait <= 0 ? 1 : 0;\n"
      "      const k = Math.min(1, 0.07 * (this.props.speed ?? 1) * (this.zcur && this.zpressa ? this.zpressa() : 1));\n"
      "      z.m = (z.m || 0) + (alvo - (z.m || 0)) * k; if (Math.abs(z.m - alvo) < 0.005) z.m = alvo;\n"
      "      if (z.dir === 'left') z.hd = -1; else if (z.dir === 'right') z.hd = 1; }")

# 4) desenho: robô, transformação e carro (no lugar do sprite antigo de 16×12)
troca("      const zbl = f % 200 < 6, ZP = { Y: '#e8b923', H: '#a8780a', K: '#1d1e21', W: '#fbe27a', G: '#4a4f57', M: '#8c939c', E: zbl ? '#1d1e21' : '#3d8bff', B: zbl ? '#1d1e21' : '#cfeaff' };\n"
      "      c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(Math.round(z.x + 3), Math.round(z.y + 14), 10, 2);\n"
      "      Component.ZSPR[z.dir][zf].forEach((row, j) => row.split('').forEach((ch, i) => { if (ch !== '.') R(z.x + i, z.y + 3 + zb + j - 4, 1, 1, ZP[ch]); }));\n"
      "      const zx = z.x, zy = z.y + 3 + zb;",
      r"""      const zbl = f % 180 < 6, BP = Component.BPAL, ZP = zbl ? Object.assign({}, BP, { E: BP.K, B: BP.K }) : BP;
      const RB = Component.BROBOT, CB = Component.BCAR, k = z.m || 0, flip = z.hd < 0, cx = Math.round(z.x + 8), G = Math.round(z.y + 15);
      const blit = (rows, x, y, pal, fl) => { const w = rows[0].length; rows.forEach((r, j) => { for (let i = 0; i < w; i++) { const ch = r[i]; if (ch !== '.') R(x + (fl ? w - 1 - i : i), y + j, 1, 1, pal[ch]); } }); };
      const carro = k >= 0.9, meio = k > 0.04 && !carro;
      c.fillStyle = 'rgba(0,0,0,.28)'; c.fillRect(cx - (carro ? 13 : 8), G - 1, carro ? 26 : 16, 2);
      let topo;
      if (meio) { // peças voam do robô para o chassi (ou de volta), em arco e girando de 90 em 90°
        const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        c.globalAlpha = Math.max(0, k - .5) * 1.6; blit(CB, cx - 15, G - 12, ZP, flip); c.globalAlpha = 1;
        Component.BPARTS.forEach(p => {
          const t = ease(Math.max(0, Math.min(1, (k - p.d) / (0.9 - p.d))));
          const ox = cx - 12 + p.rx + p.rw / 2, oy = G - 26 + p.ry + p.rh / 2, cxm = flip ? -(p.cx + p.rw) : p.cx;
          const dx = cx + cxm + p.rw / 2, dy = G - 12 + p.cy + p.rh / 2;
          const px = ox + (dx - ox) * t, py = oy + (dy - oy) * t - Math.sin(t * Math.PI) * 6;
          c.save(); c.translate(Math.round(px), Math.round(py)); c.rotate(Math.round(p.rot * 4 * t) * (flip ? -1 : 1) * Math.PI / 2);
          c.globalAlpha = 1 - Math.max(0, (t - .85) / .15);
          const hw = p.rw >> 1, hh = p.rh >> 1;
          for (let j = 0; j < p.rh; j++) for (let i = 0; i < p.rw; i++) { const ch = RB[p.ry + j][p.rx + i]; if (ch === '.') continue; c.fillStyle = ZP[ch]; c.fillRect(i - hw, j - hh, 1, 1); }
          c.restore();
        });
        const wk = Math.max(0, (k - .55) / .45);
        R(cx - 12, G - 2 - Math.round((1 - wk) * 6), 4, 2, BP.D); R(cx + 7, G - 2 - Math.round((1 - wk) * 6), 4, 2, BP.D);
        c.globalAlpha = 1; topo = G - 26 + Math.round(14 * k);
      } else if (carro) {
        const bob = zm && (f >> 2) % 2 ? -1 : 0, pal = Object.assign({}, ZP, { D: zm && (f >> 1) % 2 ? '#6b727b' : BP.D });
        blit(CB, cx - 15, G - 12 + bob, pal, flip);
        c.fillStyle = 'rgba(255,241,168,.35)'; c.fillRect(flip ? cx - 25 : cx + 15, G - 5, 10, 2);  // farol
        if (zm) for (let i = 0; i < 4; i++) { c.fillStyle = 'rgba(169,164,155,.5)'; c.fillRect(cx - z.hd * (16 + i * 4) - ((f + i * 3) % 4), G - 2 - (i % 2), 2, 1); }
        topo = G - 10;
      } else {
        blit(RB, cx - 12, G - 26 + zb, ZP, false);
        if ((f >> 4) % 2) { R(cx - 13, G - 19 + zb, 1, 1, BP.L); R(cx + 12, G - 19 + zb, 1, 1, BP.L); }  // asas-porta
        if (!zbl) { c.fillStyle = 'rgba(61,139,255,.35)'; c.fillRect(cx - 3, G - 23 + zb, 7, 3); }  // brilho dos olhos
        topo = G - 26 + zb;
      }
      const zx = z.x, zy = topo + 4;""")

# 5) o nome que aparece na vila
n = t.count("Zangão")
t = t.replace("Zangão", "Bumblebee")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print(f"Vila 02 com o Bumblebee em {caminho} ({n} nome(s) trocado(s))")
