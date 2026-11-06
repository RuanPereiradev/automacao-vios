"""Vila 05 (camada ossos): as tarefas atrasadas viram ossinhos meio enterrados na caixa de areia.

Preenche o gancho v5Ossos(c, f) criado pelo ligar_vila05_vida.py (só troca o marcador
/*V5:OSSOS*/; não mexe em mais nada).

- Cada osso vale 1 tarefa atrasada; passando de 12, aparecem no máximo 12 ossos e cada um vale
  ceil(atrasadas / 12). As atrasadas graves (mais de 7 dias) viram ossos mais escuros e sujos
  (a mesma proporção: graves / valor de cada osso). Sem cena (cena = null) ou com 0 atrasadas, a
  caixa de areia fica como antes. Posições fixas por índice (12 vagas na areia, fora do balde, do
  buraco e da pazinha); nada aleatório por frame.
- Quando o número de atrasadas CAI entre duas leituras, um osso sai da areia, sobe em arco e some
  (cerca de 1 s) e a terra voa junto. Quando SOBE, um montinho de areia novo cresce no lugar do
  osso novo e só depois o osso aparece (cerca de 1,5 s).
- Estado: this.v5.ossos_ultimo (última contagem de atrasadas lida, null enquanto não há cena) e
  this.v5.ossos_anim (animações em andamento). A primeira leitura nunca anima.

Testar pelo navegador (modo simulado): vila.html?vila=5&v5atrasadas=40&v5graves=8 (40 atrasadas =
12 ossos de valor 4, 2 sujos). Para ver os eventos, dê dois valores seguidos pelo servidor ou
mude a cena; com a página já aberta, no console: app.v5.params.atrasadas = 10 (cai) e depois 30
(sobe) — ou rode o teste teste/rodar.js.

uso: python3 doc/vila/ligar_vila05_ossos.py bot/vila/vila.html
(depois do ligar_vila05_vida.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "/*V5:OSSOS:ossos*/" in t:
    sys.exit("os ossos já estão na Vila 05")
if "v5Agir(f)" not in t or "/*V5:OSSOS*/" not in t:
    sys.exit("rode antes o ligar_vila05_vida.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


AUX = r"""  v5ossosVagas() {
    // 12 vagas na areia (x, y do osso 10x3), longe do balde, do buraco e da pazinha
    return [[21, 150], [33, 150], [41, 155], [21, 164], [36, 163], [52, 168], [52, 177], [40, 186], [34, 179], [22, 187], [44, 148], [21, 169]];
  }
  v5ossosEstado(f) {
    // lê a contagem de atrasadas e liga as animações quando ela muda entre duas leituras
    const v = this.v5, cena = v.cena, vagas = this.v5ossosVagas().length;
    const val = n => (n > vagas ? Math.ceil(n / vagas) : 1), qtd = n => (n > 0 ? Math.ceil(n / val(n)) : 0);
    if (!v.ossos_anim) v.ossos_anim = [];
    const agora = cena ? cena.atrasadas : null, antes = v.ossos_ultimo == null ? null : v.ossos_ultimo;
    if (agora !== antes) {
      if (agora != null && antes != null) {
        const a = qtd(antes), b = qtd(agora);
        if (agora < antes) {
          if (b < a) { for (let i = b; i < a; i++) v.ossos_anim.push({ tipo: 'sai', i, t0: f + (i - b) * 18 }); }
          else if (b > 0) v.ossos_anim.push({ tipo: 'sai', i: b - 1, t0: f, fica: true });
        } else if (b > a) { for (let i = a; i < b; i++) v.ossos_anim.push({ tipo: 'monte', i, t0: f + (i - a) * 12 }); }
        else if (b > 0) v.ossos_anim.push({ tipo: 'monte', i: b - 1, t0: f, fica: true });
      }
      v.ossos_ultimo = agora;
    }
    v.ossos_anim = v.ossos_anim.filter(a => f - a.t0 < 100);
    return { n: agora == null ? 0 : qtd(agora), val: agora == null ? 1 : val(agora) };
  }
"""
troca("  v5Ossos(c, f) {", AUX + "  v5Ossos(c, f) {")

CODIGO = r"""{ /*V5:OSSOS:ossos*/
      const { R, hs, disco, osso } = this.v5Pincel(c), v = this.v5, cena = v.cena, vagas = this.v5ossosVagas();
      const est = this.v5ossosEstado(f), AR = '#ead7a4', AR2 = '#dcc48c', AR3 = '#cdb37a';
      const graves = cena ? Math.min(est.n, Math.round(cena.graves / est.val)) : 0;
      const escuro = i => est.n > 0 && (i * 7) % est.n < graves;
      const pos = i => vagas[i];
      const monte = (x, y, k) => { // montinho de areia (k de 0 a 1 = tamanho)
        const w = Math.max(2, Math.round(10 * k)), h = Math.max(1, Math.round(3 * k));
        R(x + 5 - w / 2, y + 3 - h, w, h, AR2); R(x + 6 - w / 2 + 1, y + 3 - h, Math.max(1, w - 3), 1, AR); R(x + 5 - w / 2, y + 3, w, 1, AR3);
      };
      const desenha = (i, x, y) => { // osso meio enterrado: a fileira de baixo e as pontas ficam cobertas
        const e = escuro(i);
        osso(x, y, e ? '#8f7f62' : '#f6f1e6', e ? '#5e5040' : '#d9d0bd');
        R(x - 1, y + 2, 12, 1, AR); R(x + 1, y + 2, 8, 1, AR2); R(x + 2, y + 3, 6, 1, AR3);
        if (e) { R(x + 3, y, 1, 1, '#6d5d44'); R(x + 6, y + 1, 1, 1, '#6d5d44'); }
      };
      const emAnim = (i, tipo) => v.ossos_anim.find(a => a.i === i && a.tipo === tipo && f >= a.t0 && f - a.t0 < (tipo === 'sai' ? 62 : 90));
      for (let i = 0; i < est.n && i < vagas.length; i++) {
        const [x, y] = pos(i), m = emAnim(i, 'monte');
        if (m && !m.fica) {
          const k = (f - m.t0) / 90;
          if (k < 0.55) monte(x, y, Math.min(1, k / 0.5)); else { monte(x, y, 1); desenha(i, x, y); }
          if (k < 0.5) { const t = (f - m.t0) * 0.35; R(x + 2 + (hs(i, 1, 3) % 6), y - Math.round(Math.sin(t) * 2), 1, 1, AR3); }
        } else {
          desenha(i, x, y);
          if (m && m.fica) monte(x, y, 0.4 + 0.6 * Math.abs(Math.sin((f - m.t0) / 90 * Math.PI)));
        }
      }
      v.ossos_anim.forEach(a => {
        if (a.tipo !== 'sai' || f < a.t0 || f - a.t0 >= 62) return;
        const k = (f - a.t0) / 62, [x, y] = pos(a.i), dir = hs(a.i, 5, 1) % 2 ? 1 : -1, e = escuro(a.i);
        const bx = x + dir * k * 18, by = y - 4 * k * (1 - k) * 34 - k * 4;
        if (!a.fica || k > 0.06) { // o buraco/monte que ficou
          monte(x, y, 0.7);
        }
        c.globalAlpha = k < 0.6 ? 1 : 1 - (k - 0.6) / 0.4;
        osso(Math.round(bx), Math.round(by), e ? '#8f7f62' : '#f6f1e6', e ? '#5e5040' : '#d9d0bd');
        c.globalAlpha = 1;
        for (let j = 0; j < 6; j++) { // terra voando em arco
          const q = hs(a.i, j, 9), vx = ((q % 9) - 4) * 0.7, vy = 7 + (q >> 4) % 7, tt = (f - a.t0) * 0.07;
          if (tt > 1.4) continue;
          R(x + 5 + vx * tt * 6, y + 1 - vy * tt * 2.4 + 10 * tt * tt * 2.4, 1 + (q >> 8) % 2, 1 + (q >> 8) % 2, j % 2 ? AR3 : '#b89c64');
        }
      });
    }
    /*V5:OSSOS*/"""
troca("/*V5:OSSOS*/", CODIGO)

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Ossos de tarefas atrasadas na caixa de areia da Vila 05 em", caminho)
