"""Vila 05 (parque do Orelha): pessoas passeando no parque e o salto na barreira, camada "passeio".

- **Visitas**: de vez em quando (cerca de 1 minuto, mais vezes no fim de semana; só das 7h às 19h)
  uma pessoa entra pelo portão da esquerda e dá uma volta pelos caminhos de areia (linha de cima,
  desce pela direita, volta pela linha de baixo, ou o contrário). São quatro tipos, todos genéricos:
  corredor (faixa na testa, corre no lugar quando para), moça (cabelo comprido e bolsa), criança
  (boné e balão) e senhor (chapéu e bengala).
- Se o Orelha está livre (sem execução, sem humor e dentro do expediente, das 8h às 18h), ele vai até
  o ponto de encontro no caminho, espera com um "!" e, quando a pessoa chega, eles brincam: ele cheira
  (fiapinhos saindo do focinho), pula em cima (em pé nas patas de trás), late, roda, ganha carinho
  (coraçãozinho) ou um petisco (o senhor joga um biscoito), conforme o tipo. Depois a pessoa acena e
  segue, e ele volta ao passeio normal. No fim de semana, durante o dia, a visita acorda o Orelha.
  Se ele não vier (ocupado ou dormindo), a pessoa só passa. Uma execução sempre passa na frente.
- **Salto**: quando ele atravessa a barreira de agility (embaixo, x 186–222 × 150–170) indo para cima
  ou para baixo, ele salta por cima da barra (a sombra fica no chão) e levanta poeira ao pousar; indo
  de lado, pula cada poste. De vez em quando (cerca de 2 minutos, só no expediente e à toa) ele faz um
  treino: vai até a frente da barreira, atravessa e volta.

Usa um plano próprio, this.v5.passeio, que vale depois do humor e antes da rotina da camada dia
(a linha do v5Plano do esqueleto passa a ser humor → passeio → rotina). Métodos com o prefixo
v5passeio; o desenho entra num v5Passeio(c, f) novo, logo depois do v5Ossos (antes do Orelha); o salto
é um deslocamento no desenho do Orelha (v5passeioSalto).

Para testar pela URL (além dos overrides v5*): ?v5pessoa=1 traz uma pessoa a cada 15 s (a primeira
em 2 s) a qualquer hora; ?v5pessoa=corredor|moca|crianca|senhor escolhe quem vem; ?v5agility=1
faz o treino na barreira a cada 20 s. Ex.: vila.html?vila=5&v5hora=10&v5pessoa=crianca.

uso: python3 doc/vila/ligar_vila05_passeio.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; pode vir antes ou depois das outras camadas; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:AGIR:passeio*/" in t:
    sys.exit("as pessoas e o salto já estão na Vila 05")
if "v5Agir(f)" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


METODOS = r"""  // ---- Vila 05 · camada passeio (ligar_vila05_passeio.py): pessoas no parque e o salto na barreira ----
  v5passeioH(a, b) { let x = (a * 374761393 + b * 668265263) | 0; x = Math.imul(x ^ (x >>> 13), 1274126177); return (x ^ (x >>> 16)) >>> 0; }
  v5passeioEst() {
    return this.v5passeioE || (this.v5passeioE = (() => {
      const q = new URLSearchParams(location.search), v = q.get('v5pessoa');
      return { forca: v != null, tipo: ['corredor', 'moca', 'crianca', 'senhor'].indexOf(v), ag: q.get('v5agility') != null,
               n: 0, prox: null, agProx: null, p: null, agil: null, hAnt: 0, pouso: null };
    })());
  }
  v5passeioTipos() {
    // ordem: [o que o Orelha faz, duração em frames, o que a pessoa faz]; 'cheirar' = abana o rabo e fareja
    return this.v5passeioT || (this.v5passeioT = {
      corredor: { vel: 1.1, alt: 16, pele: '#e0a878', cabelo: '#3b2614', camisa: '#f08a2a', camisa2: '#c96a1f', calca: '#2f3b5a', faixa: '#e8483c',
                  ordem: [['cheirar', 100, ''], ['latir', 110, 'aceno'], ['rodar', 90, 'aceno'], ['rabo', 70, 'tchau']] },
      moca: { vel: 0.55, alt: 16, pele: '#c98a5a', cabelo: '#7a4a22', camisa: '#5fc48a', camisa2: '#3f9a66', calca: '#3d7fd1', longo: true, bolsa: true,
              ordem: [['cheirar', 110, ''], ['duaspatas', 120, 'riso'], ['lingua', 150, 'carinho'], ['rabo', 70, 'tchau']] },
      crianca: { vel: 0.65, alt: 12, pele: '#f0c08a', cabelo: '#2a1d16', camisa: '#f2c230', camisa2: '#c99a1c', calca: '#e8483c', bone: '#3d7fd1', balao: true,
                 ordem: [['duaspatas', 110, 'pula'], ['rodar', 100, 'pula'], ['lingua', 120, 'carinho'], ['rabo', 70, 'tchau']] },
      senhor: { vel: 0.4, alt: 16, pele: '#d9a273', cabelo: '#d9d0bd', camisa: '#9a6234', camisa2: '#7a4a22', calca: '#5a5f67', chapeu: '#4a413a', bengala: true,
                ordem: [['cheirar', 110, ''], ['rabo', 70, 'petisco'], ['lingua', 140, 'carinho'], ['rabo', 70, 'tchau']] },
    });
  }
  v5passeioRota(sentido) {
    // pés da pessoa (x local, y): entra pelo portão da esquerda, linha de cima, desce pela coluna da direita, linha de baixo
    const A = [[-10, 78], [280, 78], [280, 142], [-10, 142]];
    return sentido ? A : A.slice().reverse();
  }
  v5passeioNovo() {
    const E = this.v5passeioEst(), T = this.v5passeioTipos(), nomes = Object.keys(T), k = E.n++, v = this.v5, h = v.hora;
    const tipo = E.tipo >= 0 ? nomes[E.tipo] : nomes[this.v5passeioH(k, 1) % nomes.length];
    const rota = this.v5passeioRota(this.v5passeioH(k, 2) % 2), seg = this.v5passeioH(k, 3) % 2 ? 2 : 0;
    const a = rota[seg], b = rota[seg + 1], dirX = b[0] > a[0] ? 1 : -1, s = 5 + this.v5passeioH(k, 4) % 9;
    const vem = this.v5Livre() && !v.humor && (E.forca || (h >= 8 && h < 18));
    E.p = { tipo, def: T[tipo], rota, i: 0, x: rota[0][0], y: rota[0][1], fase: 'andando', seg, paraX: s * 16 + 8, dirX,
            oCol: s + dirX, oLin: Math.round((a[1] - 14) / 16), vem, t0: 0, esperaAte: 0, anda: true, etapa: null, te: 0, efeito: '' };
  }
  v5passeioAgir(f) {
    const E = this.v5passeioEst(), v = this.v5, h = v.hora, fds = v.dia_semana === 0 || v.dia_semana === 6;
    if (E.prox == null) E.prox = f + (E.forca ? 120 : 900 + this.v5passeioH(7, 7) % 1200);
    if (E.agProx == null) E.agProx = f + (E.ag ? 240 : 2400 + this.v5passeioH(8, 8) % 2400);
    if (!E.p && f >= E.prox) {
      if (E.forca || (h >= 7 && h < 19)) this.v5passeioNovo();
      E.prox = f + (E.forca ? 900 : (fds ? 2400 : 3600) + this.v5passeioH(E.n, 9) % 1800);
    }
    let plano = null;
    if (E.p) { plano = this.v5passeioPasso(E.p, f); E.agil = null; }
    else plano = this.v5passeioAgility(f);
    v.passeio = plano;
  }
  v5passeioAgility(f) {
    // treino: frente da barreira → atravessa para baixo → volta (ele salta nas duas passagens)
    const E = this.v5passeioEst(), v = this.v5, h = v.hora, F = this.fa;
    if (!E.agil) {
      if (f < E.agProx) return null;
      E.agProx = f + (E.ag ? 1200 : 4800 + this.v5passeioH(E.n + 50, 10) % 3600);
      if (!this.v5Livre() || v.humor || (!E.ag && (h < 8 || h >= 18 || v.rotina))) return null;
      E.agil = { passo: 0, planos: [[12, 8], [12, 11], [12, 8]].map(ir => ({ nome: 'agility', ir, pressa: 1.8 })) };
    }
    if (!this.v5Livre() || v.humor) { E.agil = null; return null; }
    const A = E.agil, alvo = A.planos[A.passo].ir;
    if (Math.abs(F.x - (80 + alvo[0]) * 16) < 1 && Math.abs(F.y - alvo[1] * 16) < 1 && !F.path.length) {
      A.passo++;
      if (A.passo >= A.planos.length) { E.agil = null; return null; }
    }
    return A.planos[A.passo];
  }
  v5passeioPasso(p, f) {
    // anda a pessoa um frame e devolve o plano do Orelha (ou null se ele não vem)
    const E = this.v5passeioEst(), F = this.fa, dirO = p.dirX > 0 ? 'left' : 'right';
    if (p.vem && !this.v5Livre()) { p.vem = false; p.etapa = null; if (p.fase !== 'andando') p.fase = 'saindo'; }
    if (p.fase === 'andando' || p.fase === 'saindo') {
      const alvo = p.rota[p.i + 1];
      if (!alvo) { E.p = null; return null; }
      const dx = alvo[0] - p.x, dy = alvo[1] - p.y, d = Math.hypot(dx, dy), vel = p.def.vel;
      if (p.fase === 'andando' && p.vem && p.i === p.seg && (p.paraX - p.x) * p.dirX <= vel) { p.x = p.paraX; p.fase = 'esperando'; p.esperaAte = f + 900; }
      else if (d <= vel) { p.x = alvo[0]; p.y = alvo[1]; p.i++; }
      else { p.x += dx / d * vel; p.y += dy / d * vel; }
      p.anda = p.fase !== 'esperando';
    } else p.anda = false;
    if (p.fase === 'esperando') {
      const chegou = Math.abs(F.x - (80 + p.oCol) * 16) < 1 && Math.abs(F.y - p.oLin * 16) < 1 && !F.path.length;
      if (chegou) { p.fase = 'brincando'; p.t0 = f; }
      else if (f > p.esperaAte) { p.fase = 'saindo'; p.vem = false; }
    }
    if (!p.vem) return null;
    if (p.fase === 'andando' || p.fase === 'esperando')
      return p.planoVem || (p.planoVem = { nome: 'visita', ir: [p.oCol, p.oLin], dir: dirO, idle: 'rabo', balao: '!' });
    const ordem = p.def.ordem;
    let te = f - p.t0, k = 0;
    while (k < ordem.length && te >= ordem[k][1]) { te -= ordem[k][1]; k++; }
    if (k >= ordem.length) { p.vem = false; p.etapa = null; if (p.fase === 'brincando') p.fase = 'saindo'; return null; }
    p.etapa = k; p.te = te; p.efeito = ordem[k][2];
    if (p.efeito === 'tchau' && p.fase === 'brincando') p.fase = 'saindo';
    p.planos = p.planos || {};
    return p.planos[k] || (p.planos[k] = { nome: 'visita' + k, ir: [p.oCol, p.oLin], dir: dirO, idle: ordem[k][0] === 'cheirar' ? 'rabo' : ordem[k][0] });
  }
  v5passeioSalto(fm, f) {
    // altura do salto (px) no desenho do Orelha: por cima da barra (indo para cima/baixo) ou de cada poste (de lado)
    const E = this.v5passeioEst(), F = this.fa;
    let h = 0;
    if (fm) {
      const cx = F.x - 1280 + 8, fy = F.y + 14, nx = F.path[0];
      const vert = nx ? Math.abs(nx[1] * 16 - F.y) > Math.abs(nx[0] * 16 - F.x) : false;
      if (vert) { if (cx >= 184 && cx <= 222 && fy >= 146 && fy <= 178) h = Math.round(Math.sin(Math.PI * (fy - 146) / 32) * 9); }
      else if (fy >= 150 && fy <= 176) {
        if (cx >= 180 && cx <= 196) h = Math.round(Math.sin(Math.PI * (cx - 180) / 16) * 6);
        else if (cx >= 208 && cx <= 224) h = Math.round(Math.sin(Math.PI * (cx - 208) / 16) * 6);
      }
    }
    if (h === 0 && E.hAnt > 0) E.pouso = { x: F.x - 1280 + 8, y: F.y + 15, f };
    E.hAnt = h;
    return h;
  }
  v5passeioCoracao(R, x, y) {
    const C = '#f08ac0';
    R(x + 1, y, 1, 1, C); R(x + 3, y, 1, 1, C); R(x, y + 1, 5, 1, C); R(x + 1, y + 2, 3, 1, C); R(x + 2, y + 3, 1, 1, C);
  }
  v5passeioPessoa(R, disco, p, f) {
    const d = p.def, cx = Math.round(p.x), fy = Math.round(p.y), cr = d.alt < 16, F = this.fa;
    const prox = p.rota[p.i + 1];
    const olha = p.fase === 'esperando' || p.fase === 'brincando' ? (F.x - 1280 + 8 > cx ? 1 : -1) : (prox && prox[0] !== p.x ? (prox[0] > p.x ? 1 : -1) : p.dirX);
    const ef = p.fase === 'brincando' || p.fase === 'saindo' ? p.efeito : '', brinca = p.fase === 'brincando';
    let pulo = 0;
    if (ef === 'pula' && brinca) pulo = Math.abs(Math.round(Math.sin(f * 0.25) * 3));
    if (d.faixa && !p.anda) pulo = (f >> 3) % 2;                        // o corredor corre no lugar
    const cab = cr ? 3 : 4, tz = cr ? 4 : 5, pl = cr ? 3 : 4, top = fy - d.alt - pulo;
    const inc = ef === 'carinho' && brinca ? olha : 0, yt = top + 2 + cab, yl = yt + tz, passo = (f >> 3) & 1;
    R(cx - 4, fy, 9, 1, 'rgba(40,70,30,.3)');
    // pernas (alternando quando anda) e sapatos
    const p1 = pl - (p.anda && passo ? 1 : 0), p2 = pl - (p.anda && !passo ? 1 : 0);
    R(cx - 3, yl, 2, p1, d.calca); R(cx + 1, yl, 2, p2, d.calca);
    R(cx - 3, yl + p1, 2, 1, '#201f1d'); R(cx + 1, yl + p2, 2, 1, '#201f1d');
    if (d.bengala) R(olha > 0 ? cx + 4 : cx - 5, yt + 1, 1, fy - yt - 1, '#7a4a22');
    // tronco e braços
    R(cx - 3 + inc, yt, 6, tz, d.camisa); R(cx - 3 + inc, yt + tz - 1, 6, 1, d.camisa2);
    R(cx - 4 + inc, yt, 1, tz - 1, d.camisa2); R(cx + 3 + inc, yt, 1, tz - 1, d.camisa2);
    R(cx - 4 + inc, yt + tz - 1, 1, 1, d.pele); R(cx + 3 + inc, yt + tz - 1, 1, 1, d.pele);
    if (d.bolsa) { R(olha > 0 ? cx - 5 : cx + 4, yt + 1, 2, 3, '#b07a3a'); R(olha > 0 ? cx - 4 : cx + 4, yt - 1, 1, 2, '#6e4420'); }
    if (ef === 'aceno' || ef === 'tchau') {
      const ax = olha > 0 ? cx + 4 : cx - 5, sobe = (f >> 3) & 1;
      R(ax, yt - 3 - sobe, 1, 4, d.camisa2); R(ax, yt - 4 - sobe, 1, 1, d.pele);
    }
    if (ef === 'carinho' && brinca) R(olha > 0 ? cx + 4 + inc : cx - 6 + inc, yt + 2, 3, 1, d.pele);
    // cabeça
    const hx = cx - 3 + inc, o = olha > 0 ? 1 : 0;
    R(hx, top + 2, 6, cab, d.pele); R(hx, top, 6, 2, d.cabelo);
    R(olha > 0 ? hx : hx + 5, top + 2, 1, 2, d.cabelo);
    R(hx + 1 + o, top + 3, 1, 1, '#201f1d'); R(hx + 3 + o, top + 3, 1, 1, '#201f1d');
    if (brinca || ef === 'tchau') R(hx + 2 + o, top + 1 + cab, 2, 1, '#a0523a');
    if (d.longo) { R(hx - 1, top + 1, 1, cab + 3, d.cabelo); R(hx + 6, top + 1, 1, cab + 3, d.cabelo); }
    if (d.faixa) R(hx, top + 1, 6, 1, d.faixa);
    if (d.bone) { R(hx, top - 1, 6, 2, d.bone); R(olha > 0 ? hx + 6 : hx - 2, top, 2, 1, d.bone); }
    if (d.chapeu) { R(hx - 1, top, 8, 1, d.chapeu); R(hx, top - 2, 6, 2, d.chapeu); }
    if (d.balao) {
      const bx = olha > 0 ? cx - 6 : cx + 5, by = top - 9 + Math.round(Math.sin(f * 0.05) * 1.5);
      R(bx, by + 3, 1, yt + tz - 1 - by - 3, '#d9d0bd'); disco(bx, by, 3, '#e8483c'); R(bx - 1, by - 2, 1, 1, '#ff9a8a');
    }
  }
  v5Passeio(c, f) {
    // desenho da camada (antes do Orelha): poeira do pouso, a pessoa e os efeitos da brincadeira
    const E = this.v5passeioEst(), { R, disco } = this.v5Pincel(c), p = E.p, F = this.fa;
    if (E.pouso && f - E.pouso.f < 18) {
      const k = (f - E.pouso.f) / 18; c.globalAlpha = 1 - k;
      [-1, 1].forEach(s => { R(E.pouso.x + s * (3 + k * 6), E.pouso.y - 1 - k * 2, 2, 1, '#d9c08a'); R(E.pouso.x + s * (1 + k * 4), E.pouso.y - k * 3, 1, 1, '#e7cf98'); });
      c.globalAlpha = 1;
    }
    if (!p) return;
    this.v5passeioPessoa(R, disco, p, f);
    if (p.etapa == null || (p.fase !== 'brincando' && p.fase !== 'saindo')) return;
    const passo = p.def.ordem[p.etapa]; if (!passo) return;
    const ox = F.x - 1280, oy = F.y, virado = F.dir === 'left', nx = virado ? ox - 3 : ox + 18, ny = oy + 6, te = p.te;
    if (passo[0] === 'cheirar') {
      for (let i = 0; i < 3; i++) { const k = ((te + i * 10) % 30) / 30; c.globalAlpha = (1 - k) * 0.8; R(nx + (virado ? -1 : 1) * (2 + k * 6), ny - k * 4 - i, 1, 1, '#f6f1e6'); }
      c.globalAlpha = 1;
    }
    if (p.efeito === 'carinho' || p.efeito === 'riso') {
      const k = (te % 60) / 60; c.globalAlpha = 1 - k;
      this.v5passeioCoracao(R, Math.round((ox + 8 + p.x) / 2) - 2, Math.round(oy - 6 - k * 10)); c.globalAlpha = 1;
    }
    if (p.efeito === 'petisco' && te < 50) {
      const k = te / 50, sx = p.x + p.dirX * -4, sy = p.y - 9;
      R(sx + (nx - sx) * k - 2, sy + (ny - sy) * k - Math.sin(k * Math.PI) * 10, 5, 2, '#b07a3a');
    }
  }
"""

# 1) os métodos da camada (antes do primeiro gancho do esqueleto)
troca("  v5Casinhas(c, f) {", METODOS + "  v5Casinhas(c, f) {")
# 2) o plano do passeio vale depois do humor e antes da rotina
troca("ok(this.v5.humor) || ok(this.v5.rotina)", "ok(this.v5.humor) || ok(this.v5.passeio) || ok(this.v5.rotina)")
# 3) a pessoa e os efeitos são desenhados antes do Orelha
troca("this.v5Pintar(c, f, 'v5Casinhas'); this.v5Pintar(c, f, 'v5Ossos');",
      "this.v5Pintar(c, f, 'v5Casinhas'); this.v5Pintar(c, f, 'v5Ossos'); this.v5Pintar(c, f, 'v5Passeio');")
# 4) o salto: o desenho do Orelha sobe (a sombra fica no chão)
troca("      let ox = L + dx, oy = top + dy;\n",
      "      let ox = L + dx, oy = top + dy - (this.v5Chamar('v5passeioSalto', fm, f) || 0);  // salto na barreira (ligar_vila05_passeio.py)\n")
# 5) a cada frame, antes do movimento: anda a pessoa e decide o plano
troca("/*V5:AGIR*/", """{ /*V5:AGIR:passeio*/
      this.v5passeioAgir(f);
    }
    /*V5:AGIR*/""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("pessoas passeando e o salto na barreira ligados na Vila 05 em", caminho)
