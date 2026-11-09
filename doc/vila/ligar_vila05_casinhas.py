"""Vila 05 (parque do Orelha): as TRÊS CASINHAS, camada "casinhas" da cena.

Homenagem ao Orelha real, que tinha três casinhas no bairro e usava a do meio. A casinha azul com a placa
ORELHA continua no lugar e passa a ser a do meio; ganha uma casinha menor de cada lado, no mesmo estilo
(telhadinho, parede de tábuas, porta escura) mas com cores diferentes:
- esquerda (x 16-30, y 40-56): telhado laranja, parede verde-água, a casa da Pretinha (logo acima
  do pote de água, sem cobri-lo);
- direita (x 98-118, y 36-62): telhado verde, parede amarela, com uma plaquinha com um ossinho deitado,
  a casa do Caramelo. Ela cobre a corda de brinquedo da grama (x 98-113, y 45-49).

De vez em quando (cerca de 2 a 3 minutos, determinístico pelo contador de frames, nada de Math.random)
uma visita: a Pretinha (cadelinha preta, laço rosa) sai da casinha da esquerda ou o Caramelo (cão
caramelo) sai da da direita, dá uma voltinha curta, cheira o ar (cabeça erguida, rabo abanando) e
volta para dentro. Sprites pequenos (10x8 px), no mesmo estilo do Orelha. Tom leve.

Preenche só o gancho v5Casinhas (marcador /*V5:CASINHAS:casinhas*/); métodos próprios com prefixo
v5casinhas. Não usa this.v5.cena: funciona igual sem relatório.

Para testar pela URL (além dos overrides v5*): ?v5visita=1 faz uma visita a cada 15 s (a primeira
em 1 s), ?v5visita=pretinha ou ?v5visita=caramelo escolhe quem visita.

uso: python3 doc/vila/ligar_vila05_casinhas.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:CASINHAS:casinhas*/" in t:
    sys.exit("as três casinhas já estão na Vila 05")
if "v5Agir(f)" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


METODOS = r"""  // ---- Vila 05 · camada casinhas (ligar_vila05_casinhas.py) ----
  v5casinhasCasa(R, cx, topo, hw, h, cores, ladrilho) {
    // casinha pequena: telhado em triângulo (hw = meia largura), parede de tábuas, porta escura; cx = centro
    const [tel, tel2, par, par2, luz] = cores, base = topo + hw + 1, alt = h;
    R(cx - hw - 1, base + alt - 1, hw * 2 + 3, 2, 'rgba(70,110,50,.45)');
    R(cx - hw + 2, base, hw * 2 - 3, alt, par);
    for (let y = base + 3; y < base + alt; y += 4) R(cx - hw + 3, y, hw * 2 - 5, 1, par2);
    R(cx - hw + 2, base, 1, alt, luz); R(cx + hw - 2, base, 1, alt, par2);
    R(cx - hw + 1, base + alt - 1, hw * 2 - 1, 1, '#8a5a2c');
    for (let i = 0; i <= hw; i++) {
      const w = Math.round(i * hw / hw), y = topo + i;
      R(cx - w, y, w * 2 + 1, 1, i % 3 === 2 ? tel2 : tel);
      R(cx - w, y, 1, 1, '#3b2614'); R(cx + w, y, 1, 1, '#3b2614');
    }
    R(cx - hw - 1, base - 1, hw * 2 + 3, 1, '#3b2614');
    const pw = hw >= 9 ? 6 : 4, ph = hw >= 9 ? 9 : 6;
    R(cx - (pw >> 1), base + alt - 1 - ph, pw, ph, '#2a1d16');
    R(cx - (pw >> 1), base + alt - 1 - ph, pw, 1, '#6e4420');
    return { px: cx, py: base + alt - 1 };
  }
  v5casinhasCao(R, x, y, dir, pal, f, andando, cheira) {
    // cachorrinho 10x8: x = centro, y = pés; dir 1 = olha para a direita
    const d = dir >= 0 ? 1 : -1, M = (dx, dy, w, h, col) => R(d > 0 ? x + dx : x - dx - w + 1, y + dy, w, h, col);
    const fase = (f >> 3) & 1, hy = cheira ? -9 + (((f >> 4) & 1) ? 0 : 1) : -7;
    R(x - 5, y, 10, 1, 'rgba(40,70,30,.3)');
    M(-5, -7 + (((f >> 4) & 1) ? 0 : 1) + (cheira ? -1 : 0), 1, 3, pal.corpo);
    M(-4, -5, 8, 3, pal.corpo); M(-3, -5, 5, 1, pal.luz);
    M(3, hy, 4, 4, pal.corpo); M(6, hy + 2, 2, 2, pal.corpo); M(7, hy + 2, 1, 1, '#201f1d'); M(5, hy + 1, 1, 1, '#201f1d');
    M(3, hy - 1, 2, 2, pal.orelha);
    if (pal.extra) M(3, hy + 4 > -4 ? -4 : hy + 4, 2, 1, pal.extra);
    const a = andando ? fase : 0, b = andando ? 1 - fase : 0;
    M(-4, -2, 1, 2 - a, pal.corpo); M(-2, -2, 1, 2 - b, pal.corpo); M(1, -2, 1, 2 - a, pal.corpo); M(3, -2, 1, 2 - b, pal.corpo);
  }
  v5casinhasRota(quem) {
    // pontos (x, y de pés) da voltinha; w = frames parado cheirando o ar
    return quem === 0
      ? [{ x: 23, y: 55 }, { x: 33, y: 61 }, { x: 44, y: 62, w: 170 }, { x: 36, y: 61 }, { x: 23, y: 55 }]
      : [{ x: 108, y: 59 }, { x: 108, y: 63 }, { x: 120, y: 62 }, { x: 121, y: 52, w: 170 }, { x: 113, y: 63 }, { x: 108, y: 59 }];
  }
  v5casinhasQuando(f, hs) {
    // visita em andamento no frame f: null ou { quem: 0 pretinha | 1 caramelo, t, rota, total }
    const E = this.v5casinhasE || (this.v5casinhasE = (() => {
      const v = new URLSearchParams(location.search).get('v5visita);
      return { forca: v != null, nome: v === 'pretinha' ? 0 : v === 'caramelo' ? 1 : null };
    })());
    const P = E.forca ? 900 : 9000, k = Math.floor(f / P);
    const ini = E.forca ? k * P + 60 : k * P + 3000 + hs(k, 1, 2) % 3000;
    const quem = E.nome != null ? E.nome : hs(k, 3, 5) % 2;
    const rota = (E.rotas || (E.rotas = [this.v5casinhasRota(0), this.v5casinhasRota(1)]))[quem];
    if (!E.totais) E.totais = E.rotas.map(r => { let s = 0; r.forEach((p, i) => { if (i) s += Math.hypot(p.x - r[i - 1].x, p.y - r[i - 1].y) / 0.5; s += p.w || 0; }); return Math.ceil(s); });
    const total = E.totais[quem], t = f - ini;
    return t >= 0 && t < total ? { quem, t, rota, total } : null;
  }
  v5casinhasPosicao(rota, t) {
    // onde o cachorrinho está no instante t (0,5 px por frame, parando onde há w)
    let dir = rota[1].x >= rota[0].x ? 1 : -1;
    for (let i = 1; i < rota.length; i++) {
      const a = rota[i - 1], b = rota[i], d = Math.hypot(b.x - a.x, b.y - a.y), dur = d / 0.5;
      if (b.x !== a.x) dir = b.x > a.x ? 1 : -1;
      if (t < dur) return { x: a.x + (b.x - a.x) * t / dur, y: a.y + (b.y - a.y) * t / dur, dir, andando: true, cheira: false };
      t -= dur;
      if (b.w) { if (t < b.w) return { x: b.x, y: b.y, dir, andando: false, cheira: true }; t -= b.w; }
    }
    const u = rota[rota.length - 1];
    return { x: u.x, y: u.y, dir, andando: false, cheira: false };
  }
"""
METODOS = METODOS.replace("get('v5visita);", "get('v5visita');")

GANCHO = r"""{ /*V5:CASINHAS:casinhas*/
      const { R, hs } = this.v5Pincel(c);
      // esquerda: telhado laranja, parede verde-água (a casinha da Pretinha)
      this.v5casinhasCasa(R, 23, 40, 7, 8, ['#e8a23c', '#c9852a', '#7fb6a0', '#6a9d88', '#9fd0bb']);
      // direita: telhado verde, parede amarela, plaquinha com um ossinho deitado (a casinha do Caramelo)
      this.v5casinhasCasa(R, 108, 36, 10, 14, ['#4f9a5a', '#3d7d49', '#e9c46a', '#d2a94c', '#f4dc94']);
      R(104, 48, 8, 5, '#6e4420'); R(105, 49, 6, 3, '#f4e6c4'); R(106, 50, 4, 1, '#b8a48a');
      R(105, 49, 1, 1, '#b8a48a'); R(105, 51, 1, 1, '#b8a48a'); R(110, 49, 1, 1, '#b8a48a'); R(110, 51, 1, 1, '#b8a48a');
      // visita: Pretinha (esquerda) ou Caramelo (direita) sai, dá uma voltinha, cheira o ar e volta
      const v = this.v5casinhasQuando(f, hs);
      if (v) {
        const p = this.v5casinhasPosicao(v.rota, v.t), pal = v.quem === 0
          ? { corpo: '#2b2522', luz: '#4a413a', orelha: '#14100e', extra: '#f08ac0' }
          : { corpo: '#c98a45', luz: '#dca25d', orelha: '#8a5a2c', extra: '#f6f1e6' };
        c.globalAlpha = Math.max(0, Math.min(1, v.t / 24, (v.total - v.t) / 24));
        this.v5casinhasCao(R, Math.round(p.x), Math.round(p.y), p.dir, pal, f, p.andando, p.cheira);
        c.globalAlpha = 1;
      }
    }
    /*V5:CASINHAS*/"""

troca("  v5Casinhas(c, f) {", METODOS + "  v5Casinhas(c, f) {")
troca("/*V5:CASINHAS*/", GANCHO)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("três casinhas ligadas na Vila 05")
