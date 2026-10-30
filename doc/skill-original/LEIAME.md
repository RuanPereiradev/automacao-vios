# Versões da skill de análise de intimações

Uma pasta por versão, da mais antiga para a atual. Cada pasta tem a skill aberta
(`analise-intimacoes-controladoria/`) e o `.zip` pronto para subir no chat.
Todas têm o mesmo nome de skill: no chat, subir **uma de cada vez** (substituindo a
anterior) para comparar.

O que muda de uma versão para a seguinte:

## 1 — 23/10/2026 — original
Pacote recebido da Controladoria (arquivos de 20/10), antes do robô. Idêntico ao
`.zip` original.

## 2 — 26/10/2026 — prazo previsto em lei
- Quando a intimação não informa o número de dias, usar o prazo previsto em lei e
  escrever na descrição "Prazo previsto em lei: N dias úteis (meio)". Antes:
  `PENDENTE – NÃO CONSTA NO DOCUMENTO`.
- Tabela de prazos legais: Cível (recursos 15 dias úteis, embargos de declaração 5);
  Trabalhista (recursos 8, embargos de declaração 5, embargos à execução 5,
  Recurso Extraordinário 15).

## 3 — 27/10/2026 — revisão de 27/10
- **ANALISAR SENTENÇA:** antes, sempre as duas linhas (embargos e recurso), com
  `NÃO CABE` / `NÃO HOUVE ABERTURA DE PRAZO` / `PENDENTE – CONFIRMAR CABIMENTO`.
  Agora: se couber ou puder caber, as duas linhas com data em D-2 (prazo legal
  quando não informado, inclusive com cabimento pendente); se não couber nenhum,
  omite as duas e deixa só o `PRAZO FATAL (D-2)`.
- **Prioridade RPV e emenda da Suhiane:** antes duas linhas (`Prazo fatal:` com o
  prazo real + `DATA DA TAREFA NO VIOS — PRIORIDADE ...:`). Agora uma linha só,
  `PRAZO FATAL:`, com a data da prioridade (o prazo real deixa de aparecer).
- Não lançar quando faltar informação que só o PJe tem (audiência sem tipo, data,
  horário, formato, local ou link/ID/senha; perícia sem data, horário ou local).
- Não lançar quando a área divergir do auxiliar (Execução com JOAQ/JOAN/LILI;
  outra área só com a Tamira).

## 4 — 28/10/2026 — revisão de 28/10
- `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` para o **mesmo dia** (antes: D-2); as datas
  de embargos e recurso ficam só na descrição.
- Tarefas com horário (audiência, perícia, sustentação) na data exata do ato, nunca
  no D-2; sessão virtual no 1º dia, com modelo ("DATA: De 06/11/2026 a 13/11/2026.").
- Manifestação sobre laudo pericial: 15 dias úteis (antes a IA usava 5).
- Intimação que só indica o evento ("refere-se ao seguinte evento: Evento N") não
  gera tarefa por suposição.
- Reconstruída a partir do texto enviado à IA em 28/10 (não estava no git);
  conferida: o `SKILL.md` tem o mesmo tamanho (44.277 bytes) da versão daquele dia.

## 5 — 29/10/2026
- Descrição sem `Responsável a marcar na tarefa: BRENO`, `Advogada auxiliar: TAMIRA`
  e `PRIORIDADE RPV/PRECATÓRIO` (Breno vai como responsável no VIOS).
- Audiência no padrão linha a linha: `AUDIÊNCIA [TIPO]`, `DATA`, `HORA`, `FORMATO`,
  `LINK/LOCAL`, `ID da reunião`, `SENHA` (as duas últimas só na virtual), sem `OBS:`
  (antes havia `OBS: É necessário ter atenção ao tipo de audiência...`).
- Sentença ou acórdão sempre gera ANALISAR, nunca minuta.
- Duplicatas: o robô confere na captura e no envio; o chat também não deve colocar
  a cópia no arquivo para o robô.

## 6 — 30/10/2026 — contagem simplificada (atual)
Skill revisada pela Controladoria (pacote "skill att de verdade agora").
- **Contagem simplificada:** só sábado e domingo ficam de fora; feriados, pontos
  facultativos, recesso e suspensões contam como dias úteis. Não pesquisar feriados.
- Análise e ciência: mesmo dia até 12h; depois das 12h, próximo dia de segunda a sexta.
- Análise de sentença/acórdão/decisão: `PRAZO DE EMBARGOS:` e `PRAZO DE RECURSO:`
  sempre com data D-2 (nunca `NÃO CABE`), sem `PRAZO FATAL`.
- Minutas: `PRAZO FATAL D -2:` (antes `PRAZO FATAL (D-2):`).
- RPV/precatório: data da tarefa = prioridade (próximo dia de segunda a sexta);
  `PRAZO FATAL:` = D-2 do vencimento, seguido da linha `PRIORIDADE RPV` (volta a ir
  na descrição, exceto na minuta de dados de requisitórios).
- Pagamento pelo cliente no Cível: só análise + minuta (sem tarefa de contato).
- Correções de responsável: Carlos trabalhista → Johnys; Tamira previdenciário → Suhiane.
- Audiência: usar o link encurtado quando houver.
- Nova referência `validacao-lancamento.md` (quando não lançar e checagem final).
