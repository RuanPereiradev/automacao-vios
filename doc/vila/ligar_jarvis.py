"""Põe o Jarvis (relatório mensal de processos, segundo usuário do VIOS) na Vila 04:
- a vila passa de 3 para 4 vilas; a Vila 04 acende (cores, placas e torre) e ganha o nome Jarvis;
- o Jarvis (núcleo de IA: esfera azul em espiral, com anéis e o centro pulsando; ou o mascote carmesim com propulsores) faz a ronda na Vila 04 e se apresenta no diálogo.
Ainda não recebe eventos: o relatório roda em outra máquina e só aparece aqui quando os eventos forem ligados.
uso: python3 doc/vila/ligar_jarvis.py bot/vila/vila.html [nucleo|propulsor]  (edita no lugar; rodar de novo não muda nada)"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "jpatrol()" in t:
    sys.exit("a vila já está com o Jarvis")


def troca(velho, novo, vezes=1):
    global t
    assert t.count(velho) == vezes, ("trecho não encontrado (ou repetido)", velho[:80])
    t = t.replace(velho, novo)


# 1) 4 vilas: largura do mundo e do canvas
troca("width:300%;height:100%;transform:{{ worldTransform }}", "width:400%;height:100%;transform:{{ worldTransform }}")
troca('<canvas ref="{{ canvasRef }}" width="960" height="224"', '<canvas ref="{{ canvasRef }}" width="1280" height="224"')
troca("static NV = 3;", "static NV = 4;")

# 2) a Vila 04 acesa (fundo, prédios, placas e torre)
troca("on = v <= 1", "on = v <= 1 || v === 3", vezes=2)
troca("tx < 40", "(tx < 40 || tx >= 60)", vezes=2)
troca("mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : 'Doca 01 · vaga';",
      "mine = v === 0 ? 'Doca 01 · Ultron' : v === 1 ? 'Doca 01 · Zangão' : v === 3 ? 'Doca 01 · Jarvis' : 'Doca 01 · vaga';")
troca("v === 1 ? 'Filtro previdenciário' : 'Receptor'", "v === 1 ? 'Filtro previdenciário' : v === 3 ? 'Leitura dos processos' : 'Receptor'")
troca("v === 1 ? 'Captura de dados' : 'Oficina'", "v === 1 ? 'Captura de dados' : v === 3 ? 'Planilhas' : 'Oficina'")
troca("v <= 1 ? 'Torre VIOS'", "on ? 'Torre VIOS'")
troca("'03 · vaga'];", "'03 · vaga', '04 · Jarvis'];")
troca("for (let v = 2; v < NV; v++) signs.push(", "for (let v = 2; v < NV; v++) if (v !== 3) signs.push(")

# 3) o Jarvis: sprite (o mascote), ronda e fala
troca("  static ZSPR = (() => {", r"""  static JIDLE = 'Sou o Jarvis. Uma vez por mês entro no VIOS só para ler: abro cada processo dos grupos clientes e monto a planilha do relatório mensal de cada grupo.';
  static JSPR = ['..HHHHHHHHHHHH..', '..HRRRRRRRRRRS..', '..RKKKKKKKKKKS..', '..RKBEKKKKEBKS..', '..RRRRRRRRRRRS..', 'RRRRRRRCCRRRRRSS', 'BRRRRRCWWCRRRRSB',
    '..RRRRRCCRRRRS..', '..RRGRRRRRRGRS..', '..SSSSSSSSSSSS..', '...G.G....G.G...', '...Y.Y....Y.Y...', '...F.F....F.F...', '...Q.Q....Q.Q...'];
  static ZSPR = (() => {""")
troca("    this.zseq = []; this.zcur = null; this.zevq = [];\n",
      "    this.zseq = []; this.zcur = null; this.zevq = [];\n"
      "    this.j = { x: 63 * 16, y: 64, dir: 'down', path: [], step: 0, wait: 90, i: 0 };\n"
      "    this.setState({ jtext: Component.JIDLE, jtyped: 0 });\n")
troca("  update() {\n", "  update() {\n    this.jpatrol();\n"
      "    if ((this.state.jtyped || 0) < (this.state.jtext || '').length) this.setState(s => ({ jtyped: (s.jtyped || 0) + 1 }));\n")
troca("  patrol() {", r"""  jpatrol() {
    const j = this.j, pts = [[69, 4], [73, 8], [66, 10], [63, 4]];
    if (j.wait > 0) { j.wait--; return; }
    if (!j.path.length) { j.path = this.bfs([Math.round(j.x / 16), Math.round(j.y / 16)], pts[j.i++ % pts.length]); if (!j.path.length) j.wait = 120; return; }
    const sp = 0.9 * (this.props.speed ?? 1), [tx, ty] = j.path[0], px = tx * 16, py = ty * 16, dx = px - j.x, dy = py - j.y;
    const m = Math.min(sp, Math.abs(dx) + Math.abs(dy));
    if (dx) j.x += Math.sign(dx) * m; else j.y += Math.sign(dy) * m;
    j.step += m;
    if (Math.abs(px - j.x) < 0.01 && Math.abs(py - j.y) < 0.01) { j.x = px; j.y = py; j.path.shift(); if (!j.path.length) j.wait = 160; }
  }
  jVals() {
    const s = this.state, txt = s.jtext || '';
    return { hudStatus: 'Jarvis · Ocioso', dotColor: '#7fe3ff', hudStep: 'Relatório mensal', speaker: 'Jarvis',
      dialogShown: txt.slice(0, s.jtyped || 0), moreOpacity: (s.jtyped || 0) >= txt.length ? 1 : 0 };
  }
  patrol() {""")
DESENHO = {
    # armadura carmesim e dourada com propulsores (o fogo pisca)
    "propulsor": r"""      const pisca = f % 220 < 5, chama = (f >> 2) % 2;
      const JP = { R: '#b3202f', H: '#e0525c', S: '#6e1019', G: '#c99a3a', Y: '#f0c46a', K: '#1d1e21', E: pisca ? '#1d1e21' : '#7fe3ff', B: pisca ? '#1d1e21' : '#e6fbff',
        C: '#7fe3ff', W: '#ffffff', F: chama ? '#ffd23f' : '#ff7a1a', Q: chama ? '#ff7a1a' : null };
      Component.JSPR.forEach((row, y) => row.split('').forEach((ch, x) => { if (ch !== '.' && JP[ch]) R(j.x + x, j.y + jb + y - 2, 1, 1, JP[ch]); }));""",
    # núcleo de IA: esfera em espiral girando, dois anéis tracejados e o centro pulsando
    "nucleo": r"""      const cx = j.x + 8, cy = j.y + jb + 4, rot = f * 0.025, rr = 6.5 + 0.4 * Math.sin(f * 0.06), ct = Math.cos(0.42), sn = Math.sin(0.42);
      const halo = c.createRadialGradient(cx, cy, 0, cx, cy, rr * 1.9);
      halo.addColorStop(0, 'rgba(120,200,255,.35)'); halo.addColorStop(1, 'rgba(30,90,160,0)');
      c.fillStyle = halo; c.fillRect(cx - rr * 2, cy - rr * 2, rr * 4, rr * 4);
      for (let i = 0; i < 70; i++) {
        const t0 = i / 69, ph = Math.acos(1 - 2 * t0), th = t0 * 10 * Math.PI * 2;
        const x = rr * Math.sin(ph) * Math.cos(th), y = rr * Math.cos(ph), z = rr * Math.sin(ph) * Math.sin(th);
        const x1 = x * Math.cos(rot) - z * Math.sin(rot), z1 = x * Math.sin(rot) + z * Math.cos(rot), y2 = y * ct - z1 * sn, z2 = y * sn + z1 * ct;
        R(cx + x1, cy + y2, 1, 1, z2 < 0 ? ((i + (f >> 3)) % 7 ? '#5ab4ff' : '#e6fbff') : '#1f4f86');
      }
      [[1.45, 0.32, 0.03, '#7fc8ff'], [1.2, -0.5, -0.045, '#cfeaff']].forEach(([k, inc, vel, cor]) => {
        for (let s = 0; s < 40; s++) {
          if ((s >> 2) % 2) continue;
          const a = s / 40 * Math.PI * 2 + f * vel, x = rr * k * Math.cos(a), z = rr * k * Math.sin(a);
          R(cx + x, cy + z * inc, 1, 1, z < 0 ? cor : '#2f6fae');
        }
      });
      const p = 0.85 + 0.15 * Math.sin(f * 0.06);
      const nucleo = c.createRadialGradient(cx, cy, 0, cx, cy, 4 * p);
      nucleo.addColorStop(0, 'rgba(255,255,255,1)'); nucleo.addColorStop(0.35, 'rgba(170,235,255,.85)'); nucleo.addColorStop(1, 'rgba(60,150,255,0)');
      c.fillStyle = nucleo; c.fillRect(cx - 5, cy - 5, 10, 10);
      R(cx - 1, cy - 1, 2, 2, '#ffffff');""",
}
MASCOTE = sys.argv[2] if len(sys.argv) > 2 else "nucleo"
assert MASCOTE in DESENHO, f"mascote '{MASCOTE}' não existe: {', '.join(DESENHO)}"
troca("    const eyes = {", r"""    { const j = this.j, voando = j.path.length > 0 && j.wait <= 0, jb = voando ? -2 : (f >> 4) % 2 ? -3 : -2;
      R(960 + 63, 4, 3, 3, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      R(960 + TX + 15, TY, 2, 2, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      c.fillStyle = 'rgba(0,0,0,.22)'; c.fillRect(Math.round(j.x + 4), Math.round(j.y + 15), 8, 2);
""" + DESENHO[MASCOTE] + """ }
    const eyes = {""")

# 4) painel da Vila 04
troca("    if (vi === 1) Object.assign(out, this.zVals());", "    if (vi === 1) Object.assign(out, this.zVals());\n    if (vi === 3) Object.assign(out, this.jVals());")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Jarvis na Vila 04")
