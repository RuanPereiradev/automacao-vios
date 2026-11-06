"""Vila 05 (parque do Orelha) ganha o CLIMA: o tempo no parque é o placar de prazos atrasados.

Preenche o gancho v5Clima(c, f) criado pelo ligar_vila05_vida.py. Lê this.v5.cena.atrasadas e
.graves (graves = atrasadas há mais de 7 dias). Só desenho: nenhum número aparece na tela, nenhum
texto, nenhum nome. A mudança de faixa é suave (a intensidade anda em direção ao valor novo, cerca
de 2% por frame), então nada aparece ou some de repente.

Faixas (a = atrasadas, g = graves):
- cena null (servidor sem relatório real): parque neutro, o clima não desenha nada.
- a = 0 e g = 0: SOL. Reflexos de luz (brilhinhos em cruz que acendem e apagam devagar na grama
  livre) e 3 borboletas extras além das 2 que já existem. Nenhum overlay escuro.
- a de 1 a 15 (g = 0): POUCAS NUVENS. 2 a 4 sombras de nuvem, semitransparentes, deslizam devagar da
  esquerda para a direita pelo parque (0,07 a 0,14 px por frame) e reentram pela esquerda.
- a > 15 ou g > 0: MAIS NUVENS. Valor efetivo e = a (ou max(a + 6g, 17) quando há graves): cada
  nuvem entra com a sua faixa de e (0,5 / 5 / 10 / 16 / 24 / 34 / 46 / 60), no máximo 8 sombras, e
  elas escurecem um pouco conforme e cresce.
- g >= 5: CHUVA LEVE, só na área da Vila 05 (x 1280 a 1599). Intensidade 0,3 em g = 5 até 1 em
  g = 20. Traços diagonais de 3 pedaços em loop de 4 quadros (até 90), respingos de 4 fases no chão
  (até 18, um ponto novo a cada ciclo de 6 fases), poças azuis que crescem (3 a 8) com um brilho que
  passa de vez em quando, e uma película azul-acinzentada bem fraca sobre o parque.
Tudo é pseudoaleatório determinístico por índice (hs), nada pisca forte nem usa Math.random.

Para ver cada estado (vila.html?vila=5 com os overrides da URL; valem também no modo simulado):
  sol            ?vila=5&v5atrasadas=0
  poucas nuvens  ?vila=5&v5atrasadas=6
  mais nuvens    ?vila=5&v5atrasadas=40
  nuvens (grave) ?vila=5&v5atrasadas=3&v5graves=1
  chuva leve     ?vila=5&v5atrasadas=12&v5graves=5
  chuva forte    ?vila=5&v5atrasadas=40&v5graves=8   (e &v5graves=20 para o máximo)

uso: python3 doc/vila/ligar_vila05_clima.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; as outras camadas podem vir antes ou depois; rodar de novo não
repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:CLIMA:placar*/" in t:
    sys.exit("o clima (placar de prazos) já está na Vila 05")
if "v5Agir(f)" not in t or "/*V5:CLIMA*/" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# métodos auxiliares (prefixo v5clima) antes do gancho
AUX = """  v5climaEstado(f) {
    // intensidades suaves: sol (0 a 1), e (valor efetivo de nuvens) e ri (chuva, 0 a 1)
    const ce = this.v5.cena, a = ce ? ce.atrasadas | 0 : 0, g = ce ? ce.graves | 0 : 0;
    const alvo = !ce ? { sol: 0, e: 0, ri: 0 } : {
      sol: a === 0 && g === 0 ? 1 : 0,
      e: g > 0 ? Math.max(a + 6 * g, 17) : a,
      ri: g >= 5 ? 0.3 + 0.7 * Math.min(1, (g - 5) / 15) : 0,
    };
    const E = this.v5climaE || (this.v5climaE = { sol: alvo.sol, e: alvo.e, ri: alvo.ri });
    E.sol += (alvo.sol - E.sol) * 0.02; E.e += (alvo.e - E.e) * 0.02; E.ri += (alvo.ri - E.ri) * 0.02;
    if (Math.abs(alvo.sol - E.sol) < 0.001) E.sol = alvo.sol;
    if (Math.abs(alvo.e - E.e) < 0.01) E.e = alvo.e;
    if (Math.abs(alvo.ri - E.ri) < 0.001) E.ri = alvo.ri;
    return E;
  }
  v5climaSol(c, f, p, w) {
    const { R, hs } = p, G = [[94, 16, 31, 47], [195, 16, 34, 47], [16, 194, 220, 13], [128, 146, 40, 46]];
    c.globalAlpha = 1;
    // reflexos de luz: brilhinhos em cruz que acendem devagar, 1 px nas pontas do ciclo
    for (let i = 0; i < 16; i++) {
      const r = G[hs(i, 1, 41) % 4], x = r[0] + hs(i, 2, 42) % r[2], y = r[1] + hs(i, 3, 43) % r[3], q = (f + i * 37) % 160;
      if (q >= 24) continue;
      const forte = q >= 6 && q < 18;
      c.globalAlpha = (forte ? 0.8 : 0.45) * w;
      R(x, y, 1, 1, '#fffbd8');
      if (forte) { R(x - 1, y, 1, 1, '#fff3b0'); R(x + 1, y, 1, 1, '#fff3b0'); R(x, y - 1, 1, 1, '#fff3b0'); R(x, y + 1, 1, 1, '#fff3b0'); }
    }
    // borboletas extras (mesmo desenho das que já existem em drawParque)
    c.globalAlpha = w;
    [[210, 120, 1.3, '#ffffff'], [105, 40, 3.4, '#f7a35c'], [190, 200, 0.7, '#b6a0f0']].forEach(([cx, cy, ph, col]) => {
      const tt = f * 0.011 + ph, x = cx + Math.sin(tt) * 36, y = cy + Math.sin(tt * 1.6) * 12, asa = Math.floor(f / 6) % 2;
      R(x, y, 1, 3, '#3b2614'); R(x - 2, y + (asa ? 0 : 1), 2, 2, col); R(x + 1, y + (asa ? 0 : 1), 2, 2, col);
    });
    c.globalAlpha = 1;
  }
  v5climaNuvens(c, f, p, e) {
    // sombras de nuvem: manchas semitransparentes que deslizam da esquerda para a direita
    const { O, hs } = p, TH = [0.5, 5, 10, 16, 24, 34, 46, 60], LOBOS = [[-0.45, 0.25, 0.55, 0.7], [0, -0.1, 0.75, 1], [0.5, 0.2, 0.5, 0.65]];
    const dens = 0.09 + 0.09 * Math.min(1, e / 50);
    c.fillStyle = '#26364a';
    for (let i = 0; i < TH.length; i++) {
      const w = Math.max(0, Math.min(1, (e - TH[i]) / 5));
      if (w <= 0) continue;
      const s = hs(i, 7, 1), rx = 26 + s % 22, ry = 9 + (s >> 5) % 6, cy = 22 + hs(i, 3, 2) % 170;
      const sp = 0.07 + (hs(i, 5, 3) % 8) / 100, per = 320 + 2 * (rx + 4), cx = ((hs(i, 9, 4) % 400) + f * sp) % per - (rx + 4);
      c.globalAlpha = dens * w * (0.75 + 0.25 * ((i * 5) % 3) / 2);
      for (let y = Math.floor(cy - ry * 1.1); y <= Math.ceil(cy + ry * 1.1); y++) {
        let l = 1e9, r = -1e9;
        for (const [dx, dy, lx, ly] of LOBOS) {
          const d = (y - (cy + dy * ry)) / (ly * ry);
          if (Math.abs(d) > 1) continue;
          const ww = lx * rx * Math.sqrt(1 - d * d);
          l = Math.min(l, cx + dx * rx - ww); r = Math.max(r, cx + dx * rx + ww);
        }
        if (r > l) c.fillRect(Math.round(O + l), y, Math.round(r - l), 1);
      }
    }
    c.globalAlpha = 1;
  }
  v5climaChuva(c, f, p, ri) {
    const { R, hs } = p;
    // película fria bem fraca sobre o parque
    c.globalAlpha = 0.1 * ri; R(0, 0, 320, 224, '#243447');
    // poças que crescem, com um brilho que passa de vez em quando
    const P = [[108, 44, 9], [210, 34, 8], [60, 200, 9], [190, 201, 10], [140, 172, 9], [120, 150, 6], [100, 201, 8], [228, 200, 7]];
    P.forEach(([x, y, rx], i) => {
      const w = Math.max(0, Math.min(1, ri * 9 - i)); if (w <= 0) return;
      const a = Math.max(1, Math.round(rx * Math.min(1, 0.4 + w * 0.6))), b = Math.max(1, Math.round(a * 0.45));
      for (let k = -b; k <= b; k++) {
        const ww = Math.floor(a * Math.sqrt(1 - (k * k) / (b * b + 0.5)));
        c.globalAlpha = 0.55 * w; R(x - ww, y + k, 2 * ww + 1, 1, '#5f93c4');
        if (Math.abs(k) < b) { c.globalAlpha = 0.4 * w; R(x - ww + 2, y + k, Math.max(1, 2 * ww - 3), 1, '#8dbfe6'); }
      }
      if (((f >> 5) + i) % 3 === 0) { c.globalAlpha = 0.8 * w; R(x - Math.round(a * 0.3) + ((f >> 3) % 3), y - 1, 2, 1, '#ffffff'); }
    });
    // respingos de 4 fases no chão (a cada ciclo de 6 fases o respingo muda de lugar)
    const nr = Math.floor(ri * 18), af = Math.min(1, ri * 3);
    for (let i = 0; i < nr; i++) {
      const cyc = Math.floor(f / 5) + hs(i, 4, 8) % 6, fase = cyc % 6, ci = Math.floor(cyc / 6);
      if (fase > 3) continue;
      const x = 8 + hs(i, ci, 9) % 304, y = 20 + hs(i, ci, 10) % 184;
      c.globalAlpha = [0.7, 0.6, 0.45, 0.3][fase] * af;
      if (fase === 0) R(x, y, 1, 1, '#e9f5ff');
      else if (fase === 1) { R(x - 1, y, 1, 1, '#e9f5ff'); R(x + 1, y, 1, 1, '#e9f5ff'); R(x, y - 1, 1, 1, '#e9f5ff'); }
      else if (fase === 2) { R(x - 2, y, 1, 1, '#e9f5ff'); R(x + 2, y, 1, 1, '#e9f5ff'); R(x - 1, y - 1, 1, 1, '#e9f5ff'); R(x + 1, y - 1, 1, 1, '#e9f5ff'); }
      else { R(x - 3, y, 1, 1, '#e9f5ff'); R(x + 3, y, 1, 1, '#e9f5ff'); R(x - 2, y - 1, 1, 1, '#e9f5ff'); R(x + 2, y - 1, 1, 1, '#e9f5ff'); }
    }
    // traços diagonais em loop de 4 quadros
    const nd = Math.floor(ri * 90);
    c.globalAlpha = 0.5 * af;
    for (let i = 0; i < nd; i++) {
      const ph = (Math.floor(f / 2) + hs(i, 3, 7) % 4) % 4, x = hs(i, 1, 5) % 330 - 10 + ph * 2, y = (hs(i, 2, 6) % 10) * 22 + ph * 6;
      R(x, y, 1, 2, '#cfe3f4'); R(x + 1, y + 2, 1, 2, '#cfe3f4'); R(x + 2, y + 4, 1, 1, '#cfe3f4');
    }
    c.globalAlpha = 1;
  }
"""
troca("  v5Clima(c, f) {", AUX + "  v5Clima(c, f) {")

troca("/*V5:CLIMA*/", """{ /*V5:CLIMA:placar*/
      // placar de prazos: atrasadas e graves da cena viram o tempo no parque (cena null: neutro)
      if (this.v5.cena) {
        const E = this.v5climaEstado(f), p = this.v5Pincel(c);
        if (E.sol > 0.01) this.v5climaSol(c, f, p, E.sol);
        if (E.e > 0.01) this.v5climaNuvens(c, f, p, E.e);
        if (E.ri > 0.01) this.v5climaChuva(c, f, p, E.ri);
      }
    }
    /*V5:CLIMA*/""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("clima (placar de prazos) ligado na Vila 05 em", caminho)
