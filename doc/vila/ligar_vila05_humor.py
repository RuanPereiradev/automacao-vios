"""Vila 05 (parque do Orelha), camada humor: o Orelha reage ao resultado de cada execução.

Preenche o gancho v5Humor(resultado) e a parte de humor do v5Agir(f), criados pelo
ligar_vila05_vida.py. O humor é um plano em this.v5.humor = { tipo, ate_frame, fase, ... } e tem
prioridade sobre a rotina da camada dia (this.v5.rotina); quando acaba, volta a valer a rotina (ou
o passeio normal).

- 'ok' (execução concluída sem erro): ZOOMIES de uns 6 s. Ele dispara num oito pelo gramado de
  baixo (em volta da piscina de bolinhas e pela grama aberta ao lado), rápido, com o rabo
  encolhido, a língua de fora e uma poeirinha atrás das patas; no fim faz a reverência de
  brincadeira (frente baixa, traseiro alto, rabo abanando) e volta ao normal.
- 'erro' (com_erros ou alguma seção com erro): fica EMBURRADO uns 20 s onde estiver, de costas
  para a tela, orelhas baixas, rabo parado no chão e uma nuvenzinha cinza em cima da cabeça
  (de vez em quando cai uma gotinha). Nos primeiros 5 s aparece o balão "HMPF... DEU ERRO, OLHA O
  LOG." (letrinhas de pixel desenhadas no canvas; a caixa de diálogo da vila não é tocada, para
  não atropelar a fala do fim da execução).
- 'parou': só um suspiro curto (orelhas baixas, o corpo desce um pouco e sai um soprinho do focinho).

Regras: o humor só começa quando o Orelha está livre (this.v5Livre(): a volta da execução já
acabou) e é cancelado na hora em que começa um evento ou uma execução nova (a execução sempre passa
na frente). Nunca escreve em this.fa: só no plano e no desenho do próprio Orelha.
Teste pela URL: ?v5humor=ok|erro|parou dispara ao abrir a página e fica fixo (quando o humor
acaba, recomeça; o 'ok' faz uma pausa de 2 s entre um oito e outro).

Além dos dois ganchos, este script põe dois pontos de desenho no Orelha (o desenho dele não tem
gancho no esqueleto e as poses novas precisam de outro sprite): logo antes da sombra, um
this.v5Chamar('v5humorSprite', fm, f), que devolve null (desenho normal) ou o sprite/ajustes do
humor; e, na hora de pintar o corpo, usa esse sprite e chama o desenho extra (poeira, nuvem,
balão, sopro). Sem humor ativo o desenho fica igual ao de antes. Métodos auxiliares com o prefixo
v5humor…, inseridos antes do v5Humor; estado próprio em this.v5humorE.

uso: python3 doc/vila/ligar_vila05_humor.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; pode ir antes ou depois das outras camadas da cena; rodar de novo
não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:HUMOR:humor*/" in t:
    sys.exit("o humor do Orelha já está na Vila 05")
if "v5Agir(f)" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) métodos auxiliares da camada (antes do gancho v5Humor, que é só desta camada)
AUX = r"""  // ---- camada humor (ligar_vila05_humor.py): zoomies no 'ok', emburrado no 'erro', suspiro no 'parou' ----
  // o oito pelo gramado de baixo (ladrilhos locais): volta em torno da piscina, cruza na diagonal, volta na grama aberta
  static V5HUMOR_OITO = [[8, 9], [4, 9], [4, 12], [7, 12], [8, 11], [9, 10], [10, 9], [13, 9], [13, 12], [10, 12], [9, 11], [8, 10]];
  static V5HUMOR_TEXTO = 'HMPF... DEU ERRO, OLHA O LOG.';
  static V5HUMOR_LETRAS = { H: ['X.X', 'X.X', 'XXX', 'X.X', 'X.X'], M: ['X...X', 'XX.XX', 'X.X.X', 'X...X', 'X...X'], P: ['XX.', 'X.X', 'XX.', 'X..', 'X..'],
    F: ['XXX', 'X..', 'XX.', 'X..', 'X..'], D: ['XX.', 'X.X', 'X.X', 'X.X', 'XX.'], E: ['XXX', 'X..', 'XX.', 'X..', 'XXX'], U: ['X.X', 'X.X', 'X.X', 'X.X', 'XXX'],
    R: ['XX.', 'X.X', 'XX.', 'X.X', 'X.X'], O: ['XXX', 'X.X', 'X.X', 'X.X', 'XXX'], L: ['X..', 'X..', 'X..', 'X..', 'XXX'], A: ['.X.', 'X.X', 'XXX', 'X.X', 'X.X'],
    G: ['XXX', 'X..', 'X.X', 'X.X', 'XXX'], '.': ['.', '.', '.', '.', 'X'], ',': ['.', '.', '.', 'X', 'X'] };
  v5humorSprites() {
    // sprites 20×14 na paleta da ficha (FPAL), montados uma vez
    if (this.v5humorSpr) return this.v5humorSpr;
    const corre = { 2: '..........SOOOPCc...', 3: '..........SOKOCWWN..', 4: '..........SOOOCWWd..', 5: '...........dCCCTT...', 6: '....LLLLLLLCCCCdT...',
      8: '.PPPPPPPPPPPCCd.....', 9: '.PPPPPPPPPPCCCd.....', 10: '.Pdddddddddddd......' };  // rabo encolhido embaixo, língua de fora
    const base = over => Component.FBASE.map((r, y) => (over[y] || r).split(''));
    const linhas = rs => rs.map(r => r.split(''));
    const espelho = rs => rs.map(r => (r + r.slice(0, -1).split('').reverse().join('') + '.').split(''));  // metade esquerda (colunas 0–9) espelhada na coluna 9
    const reverencia = ['....................', '....................', 'c...................', 'P...................', '.P..................',
      '.PLLLL....SLLLLS....', '..PPPPLLL.SOOOPCc...', '..PPPPPPPLSOKOCWWN..', '..PPPPPPPPSOOOCWWd..', '..ddPPPPPPPdCCCTT...',
      '...CdddPPCCCCCd.T...', '...Cd...dCCCCd......', '...Cd.....dCCCCCCd..', '..ddd.....dddddddd..'];
    const abana = reverencia.slice(); abana[2] = '..c.................'; abana[3] = '..P.................'; abana[4] = '..P.................';
    this.v5humorSpr = {
      correA: base({ ...corre, 11: '..Cd.........Cd.....', 12: '.Cd...........Cd....', 13: 'dd.............dd...' }),  // patas esticadas
      correB: base({ ...corre, 11: '....Cd.....Cd.......', 12: '.....Cd...Cd........', 13: '.....dd..dd.........' }),  // patas juntas
      reverencia: linhas(reverencia), abana: linhas(abana),
      costas: espelho(['..........', '.......SPP', '.....PPSPP', '....PP.SPP', '....P...SP', '........dP', '......PPPP', '.....PPLLL',
        '.....PPPPP', '....CPPPPP', '....CCPPPP', '...dCCdPPP', '...ddd...P', '.........P'])  // de costas, orelhas caídas, rabo no chão
    };
    return this.v5humorSpr;
  }
  v5humorComecar(f, tipo) {
    // monta o humor (o Orelha já está livre); ate_frame é o fim previsto
    const E = this.v5humorE, F = this.fa, W = Component.V5HUMOR_OITO;
    E.tipo = tipo; E.inicio = f; E.alvo = null;
    if (tipo === 'ok') {
      const cx = Math.round(F.x / 16) - 80, cy = Math.round(F.y / 16);
      let i = 0; W.forEach((p, k) => { if (Math.abs(p[0] - cx) + Math.abs(p[1] - cy) < Math.abs(W[i][0] - cx) + Math.abs(W[i][1] - cy)) i = k; });
      E.fase = 'zoom'; E.i = i; E.fimZoom = f + 250; E.ate = f + 360;
    } else if (tipo === 'erro') { E.fase = 'emburrado'; E.ate = f + 1200; }
    else { E.fase = 'suspiro'; E.ate = f + 150; }
  }
  v5humorAgir(f) {
    // parte de humor do v5Agir: começa quando ele fica livre, cancela se começar evento, escreve o plano em this.v5.humor
    const v = this.v5, E = this.v5humorE || (this.v5humorE = { tipo: null, fase: null, pend: null, reinicio: null }), P = v.params.humor;
    const livre = this.v5Livre(), fp = this.state.fphase;
    if (E.pend && (!v.humor || v.humor.tipo !== E.pend)) E.pend = null;  // alguém trocou o humor por fora
    if (E.fase && (!v.humor || v.humor.tipo !== E.tipo || v.humor.ate_frame == null)) E.fase = null;
    if (E.fase && !livre) { E.fase = null; v.humor = null; return; }  // começou um evento: o humor sai da frente
    if (!E.fase && E.pend) {
      if (fp === 'entrando' || fp === 'lendo' || fp === 'planilhas') { E.pend = null; v.humor = null; return; }  // já começou outra execução
      if (!livre) return;
      this.v5humorComecar(f, E.pend); E.pend = null;
    }
    if (!E.fase && E.reinicio != null && P && livre && f >= E.reinicio) { E.reinicio = null; this.v5humorComecar(f, P); }
    if (!E.fase) return;
    if (E.fase === 'zoom') {
      const W = Component.V5HUMOR_OITO, S = this.v5seg, chave = (80 + W[E.i][0]) + ',' + W[E.i][1];
      if (E.alvo === chave && S && S.chegou && S.chave.indexOf(chave + '|') === 0) {
        if (f >= E.fimZoom || f >= E.inicio + 520) { E.fase = 'reverencia'; E.ate = f + 100; }
        else E.i = (E.i + 1) % W.length;
      }
      if (E.fase === 'zoom') { E.alvo = (80 + W[E.i][0]) + ',' + W[E.i][1]; v.humor = { tipo: 'ok', ate_frame: E.ate, fase: 'zoom', ir: W[E.i].slice(), pressa: 3.6 }; return; }
    }
    if (f >= E.ate) {
      // acabou: devolve para a rotina; com ?v5humor fixo, recomeça (o 'ok' depois de 2 s)
      E.fase = null; v.humor = null;
      if (P) { if (P === 'ok') E.reinicio = f + 120; else this.v5humorComecar(f, P); }
      if (!E.fase) return;
    }
    v.humor = E.fase === 'suspiro' ? { tipo: E.tipo, ate_frame: E.ate, fase: E.fase, pose: 'sad', parado: true }
      : { tipo: E.tipo, ate_frame: E.ate, fase: E.fase, parado: true };
  }
  v5humorSprite(fm, f) {
    // chamado no desenho do Orelha: null = desenho normal; senão o sprite e os ajustes do humor
    const E = this.v5humorE, h = this.v5.humor, F = this.fa;
    if (!E || !E.fase || !h || h.ate_frame == null || F.fx || !this.v5Livre()) return null;
    const S = this.v5humorSprites(), flip = F.dir === 'left', t = f - E.inicio;
    if (E.fase === 'zoom') { const a = Math.floor(F.step / 7) % 2; return { base: a ? S.correA : S.correB, flip, dy: a ? -1 : 0, blink: false, glow: true, depois: fm ? 'v5humorPoeira' : null }; }
    if (E.fase === 'reverencia') return { base: Math.floor(f / 6) % 2 ? S.abana : S.reverencia, flip, hatY: 1, blink: false, glow: true };
    if (E.fase === 'emburrado') {
      const w = Component.FHAT[0].length;
      return { base: S.costas, flip: false, hatX: Math.round(9 - (w - 1) / 2), hatY: -2, depois: 'v5humorNuvem' };
    }
    const sopra = t > 25 && t < 85;  // suspiro: o corpo desce um pouco enquanto solta o ar
    return { patches: ['sad'], flip, dy: sopra ? 1 : 0, blink: sopra, glow: false, depois: 'v5humorSopro' };
  }
  v5humorPoeira(c, f, ox, oy, flip) {
    // poeirinha atrás das patas de trás durante os zoomies
    const { R } = this.v5Pincel(c), x0 = ox - 1280, st = this.fa.step;
    for (let i = 0; i < 3; i++) {
      const k = ((st * 0.6 + i * 4) % 12) / 12, x = flip ? x0 + 19 + k * 8 : x0 - k * 8, y = oy + 12 - k * 3;
      R(x, y, 2, 1, 'rgba(231,207,152,' + (0.75 * (1 - k)).toFixed(2) + ')');
    }
  }
  v5humorNuvem(c, f, ox, oy) {
    // nuvenzinha cinza em cima da cabeça (sobe e desce devagar), uma gotinha de vez em quando e o balão no começo
    const { R } = this.v5Pincel(c), E = this.v5humorE, t = f - E.inicio, cx = ox - 1280 + 9, cy = oy - 11 + Math.round(Math.sin(f * 0.04));
    const CL = '#c4c1b9', CM = '#a6a39b', CE = '#86837c';
    R(cx - 2, cy - 1, 3, 1, CL); R(cx + 2, cy, 2, 1, CL);
    R(cx - 4, cy, 6, 1, CL); R(cx - 5, cy + 1, 11, 2, CM); R(cx - 4, cy + 1, 5, 1, CL); R(cx - 5, cy + 3, 11, 1, CE);
    const g = t % 80;
    if (g < 24) R(cx - 3 + (Math.floor(t / 80) * 3) % 7, cy + 4 + (g >> 2), 1, 2, 'rgba(127,179,234,.8)');
    if (t >= 300) return;
    const L = Component.V5HUMOR_LETRAS, txt = Component.V5HUMOR_TEXTO;
    const w = txt.split('').reduce((a, ch) => a + (ch === ' ' ? 2 : L[ch][0].length + 1), -1) + 4;
    let x = Math.max(2, Math.min(318 - w, Math.round(cx - w / 2))), y = cy - 12;
    if (y < 2) y = oy + 17;  // perto da cerca de cima: o balão vai para baixo dele
    R(x, y, w, 9, '#201f1d'); R(x + 1, y + 1, w - 2, 7, '#ffffff');
    if (y < oy) { R(cx, y + 9, 1, 1, '#201f1d'); } else { R(cx, y - 1, 1, 1, '#201f1d'); }
    let lx = x + 2;
    txt.split('').forEach(ch => {
      if (ch === ' ') { lx += 2; return; }
      const gl = L[ch]; gl.forEach((r, j) => r.split('').forEach((q, i) => { if (q === 'X') R(lx + i, y + 2 + j, 1, 1, '#201f1d'); })); lx += gl[0].length + 1;
    });
  }
  v5humorSopro(c, f, ox, oy, flip) {
    // o soprinho do suspiro saindo do focinho
    const { R } = this.v5Pincel(c), t = f - this.v5humorE.inicio;
    if (t < 30 || t >= 90) return;
    const k = (t - 30) / 60, x0 = ox - 1280, x = flip ? x0 - 2 - k * 7 : x0 + 19 + k * 7, y = oy + 5 - k * 3, a = (0.8 * (1 - k)).toFixed(2);
    R(x, y, 2, 1, 'rgba(236,240,244,' + a + ')'); R(x + (flip ? -1 : 1), y - 1, 2, 1, 'rgba(236,240,244,' + a + ')');
  }
  v5Humor(resultado) {"""
troca("  v5Humor(resultado) {", AUX)

# 2) o gancho v5Humor: guarda o humor pedido; o v5Agir começa quando o Orelha fica livre
troca("/*V5:HUMOR*/", r"""{ /*V5:HUMOR:humor*/
      if (resultado === 'ok' || resultado === 'erro' || resultado === 'parou') {
        const E = this.v5humorE || (this.v5humorE = { tipo: null, fase: null, pend: null, reinicio: null });
        E.fase = null; E.reinicio = null; E.pend = resultado;
        this.v5.humor = { tipo: resultado, ate_frame: null };  // sem plano ainda: começa no v5Agir, com ele livre
      }
    }
    /*V5:HUMOR*/""")

# 3) a parte de humor do v5Agir (a camada dia usa o mesmo gancho: só o marcador é trocado)
troca("/*V5:AGIR*/", r"""{ /*V5:AGIR:humor*/
      this.v5humorAgir(f);
    }
    /*V5:AGIR*/""")

# 4) desenho do Orelha: o humor pode trocar o sprite (antes da sombra) e desenhar por cima do corpo
troca("      const L = Math.round(F.x - 2), top = Math.round(F.y);\n",
      "      const v5h = this.v5Chamar('v5humorSprite', fm, f) || null;  // camada humor (ligar_vila05_humor.py)\n"
      "      if (v5h) { patches = v5h.patches || []; flip = v5h.flip != null ? v5h.flip : flip0; dx = v5h.dx || 0; dy = v5h.dy || 0; blink = !!v5h.blink; glow = !!v5h.glow; hatY = v5h.hatY != null ? v5h.hatY : -3; stand = false; fala = null; zz = false; }\n"
      "      const L = Math.round(F.x - 2), top = Math.round(F.y);\n")
troca("        pix(Component.fmerge(Component.FBASE, Component.FPATCH, patches), ox, oy, 20, flip);\n"
      "        chapeu(ox, oy, 10, hatY, 20, flip);\n",
      "        pix(v5h && v5h.base ? v5h.base : Component.fmerge(Component.FBASE, Component.FPATCH, patches), ox, oy, 20, flip);\n"
      "        chapeu(ox, oy, v5h && v5h.hatX != null ? v5h.hatX : 10, hatY, 20, flip);\n"
      "        if (v5h && v5h.depois) this.v5Chamar(v5h.depois, c, f, ox, oy, flip);\n")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 05 ganhou o humor do Orelha (zoomies, emburrado, suspiro) em", caminho)
