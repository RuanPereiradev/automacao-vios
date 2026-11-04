"""Põe o Jarvis (relatório mensal de processos, segundo usuário do VIOS) na Vila 04:
- a vila passa de 3 para 4 vilas; a Vila 04 acende (cores, placas e torre) e ganha o nome Jarvis;
- o Jarvis (mascote carmesim e dourado com propulsores) faz a ronda na Vila 04 e se apresenta no diálogo.
Ainda não recebe eventos: o relatório roda em outra máquina e só aparece aqui quando os eventos forem ligados.
uso: python3 doc/vila/ligar_jarvis.py bot/vila/vila.html  (edita no lugar; rodar de novo não muda nada)"""
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
troca("    const eyes = {", r"""    { const j = this.j, voando = j.path.length > 0 && j.wait <= 0, jb = voando ? -2 : (f >> 4) % 2 ? -3 : -2, pisca = f % 220 < 5, chama = (f >> 2) % 2;
      const JP = { R: '#b3202f', H: '#e0525c', S: '#6e1019', G: '#c99a3a', Y: '#f0c46a', K: '#1d1e21', E: pisca ? '#1d1e21' : '#7fe3ff', B: pisca ? '#1d1e21' : '#e6fbff',
        C: '#7fe3ff', W: '#ffffff', F: chama ? '#ffd23f' : '#ff7a1a', Q: chama ? '#ff7a1a' : null };
      R(960 + 63, 4, 3, 3, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      R(960 + TX + 15, TY, 2, 2, (f >> 5) % 2 ? '#7fe3ff' : '#1a4f5c');
      c.fillStyle = 'rgba(0,0,0,.22)'; c.fillRect(Math.round(j.x + 4), Math.round(j.y + 15), 8, 2);
      Component.JSPR.forEach((row, y) => row.split('').forEach((ch, x) => { if (ch !== '.' && JP[ch]) R(j.x + x, j.y + jb + y - 2, 1, 1, JP[ch]); })); }
    const eyes = {""")

# 4) painel da Vila 04
troca("    if (vi === 1) Object.assign(out, this.zVals());", "    if (vi === 1) Object.assign(out, this.zVals());\n    if (vi === 3) Object.assign(out, this.jVals());")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Jarvis na Vila 04")
