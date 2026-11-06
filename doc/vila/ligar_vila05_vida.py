"""Vila 05 (parque do Orelha) ganha os ganchos da "cena": o parque passa a poder reagir ao relatório
real mais recente, à hora do dia e ao resultado de cada execução.

Este script não desenha nada: cria o objeto this.v5 e seis métodos vazios (os ganchos) que as
camadas (casinhas, ossos, clima, dia, humor) preenchem depois. Com os ganchos vazios a vila fica
igualzinha.

this.v5 (atualizado a cada 30 frames e logo que chega um /orelha/status novo):
- cena: o contrato "cena" (bot/orelha.py, cena()): só a data e CONTAGENS do relatório real mais
  recente — data, gerado_em, atrasadas, graves (atrasadas há mais de 7 dias), vencem_hoje,
  intimacoes, intimacoes_graves, parados, parados_graves, audiencias_hoje, pericias_hoje, erros,
  funcoes. Números sempre inteiros >= 0 (campo ausente = 0). null quando o servidor não tem
  relatório real. No modo simulado (site publicado) é uma cena de exemplo fixa (24 atrasadas,
  6 graves, 9 vencem hoje, 3 intimações / 1 grave, 140 parados / 90 graves, 1 audiência,
  0 perícia, 0 erro). O objeto só é trocado quando algum valor muda.
- hora, min, dia_semana (0 = domingo … 6 = sábado): relógio do navegador.
- humor (a camada humor escreve) e rotina (a camada dia escreve): planos para o Orelha ocioso; o
  humor tem prioridade. Um plano é { ir: [coluna, linha] (ladrilho LOCAL da Vila 05, 0–19 × 0–13),
  idle: 'lingua'|'rabo'|'duaspatas'|'latir'|'rodar'|'cochilar', pose: 'sad'|'jatem'|'bark',
  dir: 'left'|'right', balao: '!'|'ok'|'?', parado: true, pressa: número } (tudo opcional). Com o
  Orelha livre (nenhuma execução andando), o esqueleto o leva até `ir` pelo mapa de ladrilhos e,
  chegando, aplica dir, pose, balão e a animação `idle` (sem `ir`: fica onde está). Plano null =
  volta ao passeio normal (fpatrol). Uma execução sempre tem prioridade sobre o plano.
- params: os testes pela URL, valem também no modo simulado: ?v5hora=HH (ou HH:MM), ?v5atrasadas=N,
  ?v5graves=N (cria a cena com zeros se não houver uma), ?v5humor=ok|erro|parou (força: o esqueleto
  chama v5Humor com ele logo ao abrir e no fim de toda execução) e ?v5dia=0..6.
- simulado (true no site publicado) e real (true quando a cena veio do servidor).

Os ganchos (o corpo de cada um é exatamente '{ /*V5:NOME*/ }'; cada camada insere o seu código
ANTES do marcador, trocando '/*V5:NOME*/' por 'código /*V5:NOME*/', para duas camadas poderem
usar o mesmo gancho em qualquer ordem). Ordem de desenho na Vila 05, de baixo para cima:
  fundo fixo (paintParque) → drawParque (bolinha, borboletas…) → v5Casinhas(c, f) → v5Ossos(c, f)
  → lanterna, torre, calendário, correio, planilhas, relatório, arquivo → Orelha e balões
  → v5Clima(c, f) → v5Luz(c, f).
Cada gancho de desenho roda entre c.save() e c.restore(), recortado na Vila 05 (x 1280–1599), e
um erro numa camada só aparece uma vez no console (não para a vila). Para desenhar em
coordenadas locais (x 0–319, y 0–223): const { R, hs } = this.v5Pincel(c); R(x, y, w, h, cor).
  - v5Agir(f): a cada frame, no update(), antes do movimento do Orelha (a camada dia escreve
    this.v5.rotina e a humor this.v5.humor; nunca mexa em this.fa durante uma execução — use
    this.v5Livre() para saber se ele está livre).
  - v5Humor(resultado): no fim de cada execução (inclusive as que chegaram com a aba escondida),
    com 'ok' (concluído sem erro), 'erro' (com_erros ou alguma seção com erro) ou 'parou'.

Coordenadas úteis (x, y locais em pixels; ladrilho = 16 px, coluna local = x / 16):
- casinha do Orelha: x 29–84, y 10–64 (porta na coluna 3, linha 4 = onde ele mora, HOME);
  potes de água 18–30 × 57–62 e de ração 79–93 × 55–62; lanterna 77–82 × 37–44.
- caixa de areia: moldura x 16–64, y 145–193, areia 19–61 × 147–189 (colunas 1–3, linhas 9–11,
  bloqueadas); dentro: osso enterrado (26, 158), buraco (46, 172, raio 5), balde 23–32 × 173–184,
  pazinha 51–54 × 152–163.
- caminhos de areia: linhas 4 (y 64–80) e 8 (y 128–144) de ponta a ponta (colunas 0–18), colunas
  2, 9 e 17 entre as linhas 5 e 7 (x 32–48, 144–160, 272–288) e a coluna 14 nas linhas 9–10.
- grama livre (sem objeto desenhado): x 94–125 × 16–63 (entre a casinha e o mural), 195–229 ×
  16–63 (entre o mural e o correio), a faixa de baixo x 16–236 × 194–207 e 128–168 × 146–192.
- Orelha: this.fa (x, y em pixels absolutos = ladrilho × 16; desenho 20×14 em x−2…x+18, y…y+14,
  chapéu até y−3). Postos (colunas locais): casinha [3, 4], calendário [9, 4], intimações [15, 4],
  torre VIOS [14, 10], planilhas [12, 8], relatório [5, 8], arquivo [14, 6].

Os detalhes para as camadas (trechos exatos, mapa dos ladrilhos, API do Orelha e exemplos) ficam em
doc/vila/ganchos-vila05.md.

uso: python3 doc/vila/ligar_vila05_vida.py bot/vila/vila.html
(depois de todos os outros, inclusive o ligar_vila05_parque.py, o ligar_orelha_agenda.py e o
ligar_vila02_ponte.py e o ligar_vila03_arena_att.py, e antes das camadas da cena: ligar_vila05_casinhas.py, ligar_vila05_ossos.py,
ligar_vila05_clima.py, ligar_vila05_dia.py, ligar_vila05_humor.py e ligar_vila05_passeio.py, em qualquer ordem; rodar de novo
não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "v5Agir(f)" in t:
    sys.exit("a Vila 05 já tem os ganchos da cena (this.v5)")
if "drawParque(c, f)" not in t or "fstatusTick()" not in t:
    sys.exit("rode antes o ligar_vila05_parque.py e o ligar_orelha_agenda.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) cria o this.v5 junto com o estado do Orelha
troca("    this.fseq = []; this.fcur = null; this.fevq = []; this.fmock = [];\n",
      "    this.fseq = []; this.fcur = null; this.fevq = []; this.fmock = [];\n"
      "    this.v5Iniciar();\n")

# 2) a cada frame, antes do movimento do Orelha: relógio e cena, a camada decide e, livre, ele segue o plano
troca("    if (this.fcur) this.fstep(); else if (this.fevq.length) this.fhandle(this.fevq.shift()); else this.fpatrol();\n",
      "    this.v5Quadro();\n"
      "    if (this.fcur) this.fstep(); else if (this.fevq.length) this.fhandle(this.fevq.shift()); else if (!this.v5Seguir()) this.fpatrol();\n")

# 3) desenho: casinhas e ossos logo depois do drawParque; clima e luz por último, depois do Orelha
troca("      this.drawParque(c, f);\n      R(O5 + 78, 41, 3, 3,",
      "      this.drawParque(c, f);\n"
      "      this.v5Pintar(c, f, 'v5Casinhas'); this.v5Pintar(c, f, 'v5Ossos');\n"
      "      R(O5 + 78, 41, 3, 3,")
troca("      if (F.progress != null && ffx !== 'drop') { R(F.x, oy - 10, 16, 5, '#201f1d'); R(F.x + 1, oy - 9, 14, 3, '#f6f1e6'); R(F.x + 1, oy - 9, Math.round(14 * F.progress), 3, teal); }\n    }\n",
      "      if (F.progress != null && ffx !== 'drop') { R(F.x, oy - 10, 16, 5, '#201f1d'); R(F.x + 1, oy - 9, 14, 3, '#f6f1e6'); R(F.x + 1, oy - 9, Math.round(14 * F.progress), 3, teal); }\n"
      "      this.v5Pintar(c, f, 'v5Clima'); this.v5Pintar(c, f, 'v5Luz');\n    }\n")

# 4) o humor no fim de cada execução (e das que chegaram com a aba escondida)
troca("fn: () => { this.freduce(ev); F.carry = false; F.pose = p ? 'sad' : null; F.bubble = p ? '?' : null;",
      "fn: () => { this.freduce(ev); F.carry = false; F.pose = p ? 'sad' : null; F.bubble = p ? '?' : null; this.v5Fim(ev);")
troca("    q.forEach(e => this.freduce(e));\n    this.fseq = []; this.fcur = null;\n",
      "    q.forEach(e => this.freduce(e));\n"
      "    { const fim = (this.fatual ? [this.fatual] : []).concat(q).filter(e => e && e.tipo === 'execucao_fim').pop(); if (fim) this.v5Fim(fim); }\n"
      "    this.fseq = []; this.fcur = null;\n")

# 5) os métodos: this.v5, o plano do Orelha ocioso, o pincel local e os seis ganchos vazios
troca("  static ARENA = { O: 640,", r"""  // ---- Vila 05 · ganchos da cena (ligar_vila05_vida.py); as camadas preenchem só os ganchos ----
  static V5CENA_SIM = { atrasadas: 24, graves: 6, vencem_hoje: 9, intimacoes: 3, intimacoes_graves: 1, parados: 140, parados_graves: 90,
    audiencias_hoje: 1, pericias_hoje: 0, erros: 0, funcoes: ['agenda', 'prazos', 'intimacoes', 'parados', 'planilhas'] };
  static V5NUM = ['atrasadas', 'graves', 'vencem_hoje', 'intimacoes', 'intimacoes_graves', 'parados', 'parados_graves', 'audiencias_hoje', 'pericias_hoje', 'erros'];
  v5Iniciar() {
    // testes pela URL: ?v5hora=HH (ou HH:MM), ?v5atrasadas=N, ?v5graves=N, ?v5humor=ok|erro|parou, ?v5dia=0..6
    const q = new URLSearchParams(location.search);
    const num = (k, a, b) => { const v = q.get(k); if (v == null || v.trim() === '') return null; const n = parseInt(v, 10); return isNaN(n) ? null : Math.max(a, Math.min(b, n)); };
    const hm = String(q.get('v5hora') || '').trim().match(/^(\d{1,2})(?:[:h](\d{1,2}))?$/), hu = q.get('v5humor');
    const params = { hora: hm ? Math.min(23, +hm[1]) : null, min: hm && hm[2] != null ? Math.min(59, +hm[2]) : null,
      atrasadas: num('v5atrasadas', 0, 99999), graves: num('v5graves', 0, 99999), humor: ['ok', 'erro', 'parou'].includes(hu) ? hu : null, dia: num('v5dia', 0, 6) };
    this.v5 = { cena: null, hora: 0, min: 0, dia_semana: 0, humor: null, rotina: null, params, simulado: this.fonte() === 'simulado', real: false };
    this.v5seg = null; this.v5erros = {}; this.v5chave = null; this.v5srv = undefined;
    this.v5Atualizar();
  }
  v5Atualizar() {
    // relógio do navegador (ou da URL) e a cena: do /orelha/status (servidor) ou a de exemplo (simulado)
    const v = this.v5, P = v.params, d = new Date(), srv = this.state.fsrv, sim = this.fonte() === 'simulado';
    const hoje = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    v.hora = P.hora != null ? P.hora : d.getHours(); v.min = P.min != null ? P.min : d.getMinutes(); v.dia_semana = P.dia != null ? P.dia : d.getDay();
    v.simulado = sim; this.v5srv = srv;
    let base = sim ? { data: hoje, gerado_em: hoje + 'T07:30:00', ...Component.V5CENA_SIM } : srv && srv.cena && typeof srv.cena === 'object' ? srv.cena : null;
    v.real = !sim && !!base;
    if (!base && (P.atrasadas != null || P.graves != null)) base = { data: hoje, gerado_em: null, funcoes: [] };
    let cena = null;
    if (base) {
      cena = { data: String(base.data || hoje), gerado_em: base.gerado_em ? String(base.gerado_em) : null };
      Component.V5NUM.forEach(k => { cena[k] = Math.max(0, Math.floor(Number(base[k]) || 0)); });
      cena.funcoes = Array.isArray(base.funcoes) ? base.funcoes.map(String) : [];
      if (P.atrasadas != null) cena.atrasadas = P.atrasadas;
      if (P.graves != null) cena.graves = P.graves;
    }
    const chave = JSON.stringify(cena);
    if (chave !== this.v5chave) { this.v5chave = chave; v.cena = cena; }  // só troca o objeto quando algum valor muda
  }
  v5Chamar(nome, ...args) {
    // um erro numa camada não pode parar o laço da vila: avisa uma vez no console e segue
    try { return this[nome](...args); } catch (e) { if (!this.v5erros[nome]) { this.v5erros[nome] = true; console.error('Vila 05 · ' + nome + ':', e); } }
  }
  v5Pintar(c, f, nome) {
    // cada gancho de desenho fica recortado na Vila 05 e não deixa alpha, clip ou composição para trás
    c.save(); c.beginPath(); c.rect(1280, 0, 320, 224); c.clip();
    this.v5Chamar(nome, c, f);
    c.restore();
  }
  v5Pincel(c) {
    // ajudantes em coordenadas locais da Vila 05 (x 0–319, y 0–223), iguais aos do paintParque
    const O = 1280, R = (x, y, w, h, col) => { c.fillStyle = col; c.fillRect(Math.round(O + x), Math.round(y), Math.round(w), Math.round(h)); };
    const hs = (x, y, k) => (((x * 73856093) ^ (y * 19349663) ^ (k * 83492791)) >>> 0);
    const disco = (cx, cy, r, col) => { for (let y = -r; y <= r; y++) { const w = Math.floor(Math.sqrt(r * r - y * y + r * .4)); R(cx - w, cy + y, 2 * w + 1, 1, col); } };
    const pata = (x, y, col) => { R(x + 1, y + 2, 3, 2, col); R(x, y + 1, 1, 1, col); R(x + 1, y, 1, 1, col); R(x + 3, y, 1, 1, col); R(x + 4, y + 1, 1, 1, col); };
    const osso = (x, y, col, sh) => { R(x, y, 2, 1, col); R(x + 8, y, 2, 1, col); R(x + 1, y + 1, 8, 1, col); R(x, y + 2, 2, 1, sh); R(x + 8, y + 2, 2, 1, sh); R(x + 2, y + 2, 6, 1, sh); };
    const cores = { GR: '#86c95f', GR2: '#74b850', GR3: '#9bd873', SOMBRA: '#6aa84a', AREIA: '#e7cf98', BORDA: '#caad72', CAIXA: '#ead7a4', MADEIRA: '#8a5a2c' };
    return { O, R, hs, disco, pata, osso, cores };
  }
  v5Livre() { const fp = this.state.fphase; return !this.fcur && !this.fevq.length && !this.fmock.length && (fp === 'idle' || fp === 'done'); }
  v5Plano() {
    const ok = p => p && typeof p === 'object' && (p.ir || p.idle || p.pose || p.balao || p.parado) ? p : null;
    return ok(this.v5.humor) || ok(this.v5.rotina);  // o humor manda
  }
  v5Seguir() {
    // Orelha livre com plano (humor ou rotina): vai até p.ir e fica com a pose/animação pedida; sem plano devolve false (fpatrol)
    const F = this.fa, p = this.v5Livre() ? this.v5Plano() : null;
    if (!p) { if (this.v5seg) { this.v5seg = null; F.pose = null; F.idle = null; F.bubble = null; F.path = []; F.wait = 60; } return false; }
    const ir = Array.isArray(p.ir) && p.ir.length === 2 ? [80 + Math.max(0, Math.min(19, Math.round(p.ir[0]))), Math.max(0, Math.min(13, Math.round(p.ir[1])))] : null;
    const chave = [ir ? ir.join(',') : '', p.idle || '', p.pose || '', p.dir || '', p.balao || '', p.parado ? 1 : 0].join('|');
    if (!this.v5seg || this.v5seg.chave !== chave) {
      this.v5seg = { chave, chegou: !ir || this.blocked[ir[1]][ir[0]] };  // ladrilho bloqueado: fica onde está
      F.path = []; F.wait = 0; F.idle = null; F.pose = null; F.bubble = null;
    }
    const S = this.v5seg;
    if (!S.chegou) {
      if (!F.path.length) {
        const aqui = [Math.round(F.x / 16), Math.round(F.y / 16)];
        F.path = (F.x !== aqui[0] * 16 || F.y !== aqui[1] * 16 ? [aqui] : []).concat(this.bfs(aqui, ir));
        if (!F.path.length) S.chegou = true;
      }
      if (!S.chegou) { if (this.fanda(0.7 * (this.props.speed ?? 1) * (Number(p.pressa) || 1)) && !F.path.length) S.chegou = true; return true; }
    }
    if (p.dir === 'left' || p.dir === 'right') F.dir = p.dir;
    F.pose = p.pose || null; F.bubble = p.balao || null;
    if (p.idle) { if (F.idle && F.idle.k === p.idle) F.idle.t++; else F.idle = { k: p.idle, t: 0 }; } else F.idle = null;
    return true;
  }
  v5Quadro() {
    // no update(), a cada frame, antes do movimento do Orelha
    if (!this.v5Livre()) this.v5seg = null;
    if (this.frame % 30 === 0 || this.state.fsrv !== this.v5srv) this.v5Atualizar();
    if (this.frame === 45 && this.v5.params.humor) this.v5Chamar('v5Humor', this.v5.params.humor);
    this.v5Chamar('v5Agir', this.frame);
  }
  v5Fim(ev) {
    const r = ev.resultado === 'parou' ? 'parou' : ev.resultado === 'com_erros' || (Array.isArray(ev.erros) && ev.erros.length) ? 'erro' : 'ok';
    this.v5Chamar('v5Humor', this.v5.params.humor || r);
  }
  // os ganchos: cada camada insere o seu código antes do marcador (ver doc/vila/ligar_vila05_vida.py)
  v5Casinhas(c, f) { /*V5:CASINHAS*/ }
  v5Ossos(c, f) { /*V5:OSSOS*/ }
  v5Clima(c, f) { /*V5:CLIMA*/ }
  v5Luz(c, f) { /*V5:LUZ*/ }
  v5Agir(f) { /*V5:AGIR*/ }
  v5Humor(resultado) { /*V5:HUMOR*/ }
  // ---- fim dos ganchos da Vila 05 ----
  static ARENA = { O: 640,""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 05 ganhou os ganchos da cena (this.v5) em", caminho)
