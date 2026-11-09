"""Vila 05 (parque do Orelha) ganha o ciclo do dia e o expediente do Orelha (camada "dia" da cena).

- Luz por hora do dia (this.v5.hora/min: relógio do navegador ou ?v5hora=HH / HH:MM): madrugada
  azul escuro, nascer do sol lilás e rosado, manhã com um dourado leve, dia sem tinta, fim de tarde
  quente, pôr do sol alaranjado indo para o roxo e noite escura (mas legível: a tinta nunca passa
  de 0,34 de opacidade). As cores mudam aos poucos, interpoladas entre os horários.
- À noite (e na madrugada) a luz vem dos objetos, desenhada depois da tinta: a lanterna da casinha
  fica acesa com um halo quente que "respira" devagar, a luz da antena da torre VIOS ganha um halo
  (o ponto continua piscando como antes) e uns vagalumes passeiam pela grama acendendo e apagando
  devagar. Nada pisca forte e não há Math.random: tudo vem do contador de frame e do índice.
- Expediente (escreve só this.v5.rotina; quem manda no humor é a camada humor, que tem prioridade):
  - das 12h às 13h (todo dia) ele vai até o pote de ração, ao lado da porta da casinha, e come
    (língua de fora e uns grãozinhos pulando do pote);
  - antes das 8h, a partir das 18h e no sábado e no domingo ele dorme na frente da casinha (Zzz).
  - O esqueleto (ligar_vila05_vida.py) só segue a rotina com o Orelha livre: uma execução sempre passa
    na frente (ele acorda, trabalha e depois volta a dormir), e eventos na fila não são atrapalhados.
- Fim de semana (sábado e domingo, ou ?v5dia=0 / ?v5dia=6): o fedora vira um chapéu de praia de palha
  com fita vermelha (troca Component.FHAT/FHATPAL e devolve o fedora nos dias de semana).

Testes pela URL (valem no modo simulado): ?vila=5&v5hora=3 (madrugada), 6 (nascer), 7:30 (manhã),
10 (dia), 16:30 (fim de tarde), 18 (pôr do sol), 21 (noite), 12 (almoço) e &v5dia=6 (fim de semana).

uso: python3 doc/vila/ligar_vila05_dia.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; as camadas da cena podem ir em qualquer ordem; rodar de novo não
repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:LUZ:dia*/" in t:
    sys.exit("o ciclo do dia já está na Vila 05")
if "v5Agir(f)" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) ajudantes da camada: tinta por hora, quanto é noite e o chapéu de palha
troca("  v5Luz(c, f) {", r"""  // camada dia (ligar_vila05_dia.py): tinta por hora [hora, r, g, b, alpha], interpolada entre as linhas
  static V5DIA_TINTA = [[0, 18, 26, 74, .34], [4.5, 18, 26, 74, .34], [5.5, 70, 60, 130, .26], [6.5, 255, 170, 130, .14], [8, 255, 228, 170, .06],
    [9, 255, 255, 255, 0], [15.5, 255, 255, 255, 0], [16.5, 255, 190, 100, .10], [17.5, 250, 130, 60, .20], [18.3, 170, 70, 100, .26],
    [19.3, 24, 30, 80, .33], [24, 18, 26, 74, .34]];
  static V5DIA_PALHA = [['...hYYh...', '..hYyYyh..', '..rrrrrr..', 'hYYYYYYYYh', 'y........y'], { Y: '#ecc970', y: '#c9a24a', h: '#a8803a', r: '#e8483c' }];
  v5diaTinta(h) {
    const K = Component.V5DIA_TINTA; let i = 0;
    while (i < K.length - 2 && h >= K[i + 1][0]) i++;
    const a = K[i], b = K[i + 1], k = Math.max(0, Math.min(1, (h - a[0]) / (b[0] - a[0]))), m = j => a[j] + (b[j] - a[j]) * k;
    return [Math.round(m(1)), Math.round(m(2)), Math.round(m(3)), m(4)];
  }
  v5diaNoite(h) { return h < 5 || h >= 19.5 ? 1 : h < 6.5 ? (6.5 - h) / 1.5 : h >= 17.5 ? (h - 17.5) / 2 : 0; }
  v5diaHora() { const v = this.v5; return (v.hora || 0) + (v.min || 0) / 60; }
  v5Luz(c, f) {""")

# 2) a luz: tinta por cima de tudo e, à noite, as luzes dos objetos e os vagalumes por cima da tinta
troca("/*V5:LUZ*/", r"""{ /*V5:LUZ:dia*/
      const { R, hs, disco } = this.v5Pincel(c), v = this.v5, F = this.fa, h = this.v5diaHora(), n = this.v5diaNoite(h);
      // almoço: grãozinhos de ração pulando do pote enquanto ele come
      if (v.rotina && v.rotina.nome === 'almoco' && F.idle && F.idle.k === 'lingua' && F.x === 1360 && F.y === 64) for (let i = 0; i < 3; i++) {
        const q = ((f + i * 23) % 70) / 70, x = 80 + hs(i, 3, 11) % 9 - Math.round(q * 3), y = 56 - Math.round(Math.sin(q * Math.PI) * 4) + Math.round(q * 6);
        if (q < 0.8) R(x, y, 1, 1, i % 2 ? '#9a6234' : '#b07a3a');
      }
      const [tr, tg, tb, ta] = this.v5diaTinta(h);
      if (ta > 0.005) R(0, 0, 320, 224, 'rgba(' + tr + ',' + tg + ',' + tb + ',' + ta.toFixed(3) + ')');
      if (n > 0.02) {
        const resp = 0.85 + 0.15 * Math.sin(f * 0.03), al = a => (a * n * resp).toFixed(3);
        // lanterna da casinha: acesa direto, com halo quente
        disco(79, 42, 13, 'rgba(255,196,110,' + al(0.05) + ')'); disco(79, 42, 8, 'rgba(255,205,120,' + al(0.07) + ')');
        disco(79, 42, 4, 'rgba(255,220,140,' + al(0.12) + ')');
        if (n > 0.3) { R(78, 41, 3, 3, '#ffd27a'); R(79, 42, 1, 1, '#fff1c4'); }
        // luz da antena da torre VIOS: halo constante; o ponto segue o pisca de sempre
        disco(256, 145, 9, 'rgba(255,170,90,' + al(0.05) + ')'); disco(256, 145, 4, 'rgba(255,185,110,' + al(0.09) + ')');
        if (n > 0.3 && F.fx !== 'vios' && (f >> 5) % 2) R(255, 144, 2, 2, '#ffb36b');
        // vagalumes passeando pela grama
        for (let i = 0; i < 9; i++) {
          const q = hs(i, 7, 5), bx = 24 + q % 270, by = 22 + (q >> 9) % 176;
          const x = bx + Math.sin(f * 0.011 + i * 1.7) * 10, y = by + Math.sin(f * 0.017 + i * 2.9) * 6;
          const a = n * Math.max(0, Math.sin(f * 0.035 + i * 2.3));
          if (a > 0.05) { R(x - 1, y - 1, 3, 3, 'rgba(240,255,140,' + (a * 0.22).toFixed(3) + ')'); R(x, y, 1, 1, 'rgba(250,255,190,' + (a * 0.9).toFixed(3) + ')'); }
        }
      }
    }
    /*V5:LUZ*/""")

# 3) a rotina: almoço das 12h às 13h; fora do expediente e no fim de semana, dorme na porta da casinha
troca("/*V5:AGIR*/", r"""{ /*V5:AGIR:dia*/
      const v = this.v5, h = this.v5diaHora(), fds = v.dia_semana === 0 || v.dia_semana === 6;
      const E = this.v5diaE || (this.v5diaE = { fedora: [Component.FHAT, Component.FHATPAL], planos: {
        almoco: { nome: 'almoco', ir: [5, 4], idle: 'lingua', dir: 'left' },
        dormir: { nome: 'dormir', ir: [3, 4], idle: 'cochilar', dir: 'right', pressa: 0.8 } } });
      // fim de semana: chapéu de praia de palha no lugar do fedora
      const [chap, pal] = fds ? Component.V5DIA_PALHA : E.fedora;
      if (Component.FHAT !== chap) { Component.FHAT = chap; Component.FHATPAL = pal; }
      v.rotina = h >= 12 && h < 13 ? E.planos.almoco : fds || h < 8 || h >= 18 ? E.planos.dormir : null;
    }
    /*V5:AGIR*/""")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 05 ganhou o ciclo do dia e o expediente do Orelha em", caminho)
