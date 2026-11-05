"""Vila 05: o Orelha avisa quando o relatório roda e guarda cada relatório no Arquivo do parque.

- Com o servidor (página do Sam), a vila lê o GET /orelha/status a cada 30 s (bot/orelha.py: só
  datas e contagens). Parado, o Orelha diz quando roda ("de segunda a sexta às 7h30"), quando sai o
  próximo relatório e, se o de hoje não saiu na hora marcada, avisa para conferirem o computador
  dele. O topo mostra "Atrasado" nesse caso.
- No fim de uma execução (menos quando parou), ele leva a folha do Relatório até o **Arquivo**
  (armário do parque, ligar_vila05_parque.py), abre a gaveta e guarda. A placa mostra quantos
  relatórios estão guardados ("Arquivo · 12") e as gavetas ganham uma pastinha por relatório.
- Botão "Relatórios guardados" na Vila 05: abre a página /orelha, com o horário e todos os
  relatórios já feitos para abrir de novo.
- No modo simulado (site publicado, sem servidor), ele fala o horário padrão do escritório e o
  arquivo começa com 3 relatórios de exemplo.

uso: python3 doc/vila/ligar_orelha_agenda.py bot/vila/vila.html
(por último, depois do ligar_vila05_parque.py; rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "fstatusTick()" in t:
    sys.exit("a vila já tem o horário e o arquivo do Orelha")
if "drawParque(c, f)" not in t or "P(96, 4.6, 'Arquivo')" not in t:
    sys.exit("rode antes o ligar_vila05_parque.py (com o Arquivo)")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


# 1) estado: o que o servidor diz do Orelha e quantos relatórios a simulação guardou
troca("fpanelOpen: false, fts: null };", "fpanelOpen: false, fts: null, fsrv: null, fsimGuardados: 0 };")

# 2) lê o /orelha/status (horário, próximo, atraso, quantos guardados) a cada 30 s
troca("    this.jstatusTick(); this.jpoll = setInterval(() => this.jstatusTick(), 4000);\n",
      "    this.jstatusTick(); this.jpoll = setInterval(() => this.jstatusTick(), 4000);\n"
      "    this.fstatusTick(); this.fpoll = setInterval(() => this.fstatusTick(), 30000);\n")

# 3) a fala do simulado também diz quando ele roda e que guarda os relatórios
troca("No fim entrego o relatório do dia. Aperte \"Simular execução\" para me ver trabalhando.';",
      "No fim entrego o relatório do dia e guardo no Arquivo. No escritório eu rodo sozinho de segunda a sexta às 7h30. "
      "Aperte \"Simular execução\" para me ver trabalhando.';")

# 4) as falas do horário e o pedido ao servidor
troca("  fsay(t) { this.setState({ ftext: t, ftyped: 0 }); }\n", r"""  fsay(t) { this.setState({ ftext: t, ftyped: 0 }); }
  static FHORARIO_SIM = 'de segunda a sexta às 7h30';
  fguardados() { const srv = this.state.fsrv; return (srv && srv.configurado ? srv.total || 0 : this.fonte() === 'simulado' ? 3 : 0) + this.state.fsimGuardados; }
  fproximo() {
    // "O próximo relatório sai amanhã (sexta) às 7h30." (ou o horário do escritório, no simulado)
    const srv = this.state.fsrv;
    if (srv && srv.configurado) return srv.atrasado ? ' Atenção: ' + srv.atrasado_texto + '.' : srv.proximo_texto ? ' O próximo relatório sai ' + srv.proximo_texto + '.' : '';
    return this.fonte() === 'simulado' ? ' No escritório, o relatório sai ' + Component.FHORARIO_SIM + '.' : '';
  }
  async fstatusTick() {
    try {
      const r = await fetch('/orelha/status', { credentials: 'same-origin' });
      if (!r.ok) return;
      this.setState({ fsrv: await r.json() });
      setTimeout(() => this.ffalarHorario(), 0);
    } catch (e) { /* sem conexão: o topo já mostra pelo /eventos */ }
  }
  ffalarHorario() {
    // parado (sem execução andando), ele diz quando roda, quando sai o próximo e se o de hoje atrasou
    const s = this.state, srv = s.fsrv;
    if (!srv || !srv.configurado || !srv.aviso || this.fcur || this.fevq.length || !(s.fphase === 'idle' || s.fphase === 'done')) return;
    const txt = (s.fphase === 'done' ? 'Última execução' + (s.fsim ? ' (simulada)' : '') + ': ' + this.flogTexto(s.fresult || {}) + '. ' : 'Sou o Orelha, o relatório do dia. ')
      + srv.aviso + ' Para abrir os relatórios, aperte "Relatórios guardados".';
    if (txt === this.fultHorario) return;
    this.fultHorario = txt; this.fsay(txt);
  }
""")

# 5) no fim: leva a folha ao Arquivo, guarda na gaveta e só depois volta para a casinha
troca("""        { type: 'wait', n: N(130) }, { type: 'call', fn: () => { F.bubble = null; F.pose = null; this.fst('Voltando para a casinha'); } },
        { type: 'walk', to: HOME, face: 'right' }, { type: 'call', fn: () => { this.fst('Ocioso'); F.wait = 200; } });""",
      """        { type: 'wait', n: N(130) }, { type: 'call', fn: () => { F.bubble = null; F.pose = null; F.carry = !p; this.fst(p ? 'Voltando para a casinha' : 'Guardando no Arquivo'); } },
        ...(p ? [] : [{ type: 'walk', to: ARQ, face: 'right' },
          { type: 'act', n: N(70), fx: 'arq', start: () => { F.carry = false; this.fsay('Guardei o relatório de hoje no Arquivo.' + this.fproximo()); },
            end: () => { if (this.state.fsim) this.setState(s => ({ fsimGuardados: s.fsimGuardados + 1 })); else this.fstatusTick(); this.fst('Voltando para a casinha'); } }]),
        { type: 'walk', to: HOME, face: 'right' }, { type: 'call', fn: () => { this.fst('Ocioso'); F.wait = 200; this.fultHorario = null; setTimeout(() => this.ffalarHorario(), 0); } });""")
troca("PLA = [O + 12, 8], REL = [O + 5, 8], S = [];", "PLA = [O + 12, 8], REL = [O + 5, 8], ARQ = [O + 14, 6], S = [];")

# 6) desenho: uma pastinha por relatório guardado e, guardando, a gaveta do meio abre e a folha entra
troca("      // o Orelha (desenho da ficha:", r"""      { // Arquivo: pastinhas aparecendo nas gavetas (uma por relatório, até 12) e a gaveta abrindo
        const n = Math.min(12, this.fguardados()), CP = ['#5fc48a', '#f0a64b', '#3fb8e8', '#f08ac0'];
        for (let k = 0; k < n; k++) { const d = k % 3, j = Math.floor(k / 3); R(O5 + 262 + j, 87 + d * 8 + 1, 1, 4, CP[(k + d) % 4]); }
        if (ffx === 'arq') {
          const k = F.progress || 0, ab = Math.round(6 * Math.sin(Math.min(1, k * 1.25) * Math.PI));
          R(O5 + 245, 95, 22, 7, '#3b2614'); R(O5 + 245 - ab, 95, 22, 7, '#c98a4b'); R(O5 + 245 - ab, 101, 22, 1, '#8f5a2c');
          R(O5 + 254 - ab, 98, 6, 1, '#f6f1e6');
          if (k < 0.6) { const q = k / 0.6, bx = F.x + 18, by = F.y + 2; R(bx + (O5 + 252 - bx) * q, by + (93 - by) * q - Math.sin(q * Math.PI) * 10, 4, 5, '#f4ead2'); }
        }
      }
      // o Orelha (desenho da ficha:""")

# 7) placa do Arquivo com quantos estão guardados
troca("P(96, 4.6, 'Arquivo')", "P(96, 4.6, 'Arquivo' + (this.fguardados() ? ' · ' + this.fguardados() : ''))")

# 8) botão "Relatórios guardados" (abre /orelha) e o topo avisa o atraso
troca("      showAction2: false, actionLabel2: '', action2: () => {}, action2Bg: '#2c6c66',\n",
      "      showAction2: !!(fsrv && fsrv.configurado), actionLabel2: 'Relatórios guardados', action2: () => window.open('/orelha', '_blank'), action2Bg: '#8f5a2c',\n")
troca("      hudStatus: 'Orelha · ' + s.fstatus, dotColor: off ? '#5a5f67' : '#d39a5c',\n      hudStep: off ? 'Sem conexão' : idx < 4 ? 'Etapa ' + (idx + 1) + '/4' : 'Finalizado',",
      "      hudStatus: 'Orelha · ' + s.fstatus, dotColor: off ? '#5a5f67' : '#d39a5c',\n      hudStep: off ? 'Sem conexão' : fsrv && fsrv.atrasado && (fp === 'idle' || fp === 'done') ? 'Atrasado' : idx < 4 ? 'Etapa ' + (idx + 1) + '/4' : 'Finalizado',")
troca("    const s = this.state, fp = s.fphase, L = s.ffun, r = s.fresult || {}, PL = s.fplan || {}, off = this.fonte() === 'servidor' && s.conn === 'offline';",
      "    const s = this.state, fp = s.fphase, L = s.ffun, r = s.fresult || {}, PL = s.fplan || {}, off = this.fonte() === 'servidor' && s.conn === 'offline', fsrv = s.fsrv;")
troca("      sendHint: 'O Orelha só lê o VIOS. O relatório completo fica no computador que roda o Orelha (orelha/saida, pasta do dia).',",
      "      sendHint: 'O Orelha só lê o VIOS. Os relatórios ficam guardados em orelha/saida e abrem pelo botão \"Relatórios guardados\" (página /orelha).',")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Orelha avisa o horário e guarda os relatórios no Arquivo em", caminho)
