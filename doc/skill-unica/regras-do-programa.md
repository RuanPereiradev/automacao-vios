## Regras do programa (robô) — o que ele faz com o arquivo

O robô não refaz a análise: ele lança no VIOS exatamente as tarefas do arquivo para o robô (seção "Arquivo para o robô (.txt)", mais abaixo). As regras de tarefa, data e descrição são as da parte principal desta skill e das referências (contagem simplificada: segunda a sexta, incluindo feriados). Esta seção só descreve o que o robô confere, para o arquivo passar na primeira tentativa.

### Datas das intimações capturadas pelo robô

- O robô pesquisa no VIOS pela data de **disponibilização**. Os arquivos que ele gera levam essa data no nome (ex.: `intimacoes_2026-10-27` = disponibilizadas em 27/10/2026). A publicação é o dia seguinte de segunda a sexta (Lei 11.419/2006, art. 4º, § 3º) — ex.: disponibilizada em 27/10, publicada em 28/10 —, e isso não é erro. O prazo conta da publicação.
- As sugestões automáticas de tarefa do VIOS são apenas indício, nunca decisão.

### O que o robô bloqueia (a CI não é lançada e aparece como problema na página de envio)

- Tarefa fora da lista oficial do VIOS (nome diferente da seção "Referência — Tarefas VIOS e Modelos de Descrição").
- `DATA` vazia ou fora do formato DD/MM/AAAA (só `CIÊNCIA` pode ficar sem data).
- Audiência, perícia ou sustentação oral sem `HORA`, ou horário fora do formato HH:MM.
- Responsável que não existe no VIOS (nome diferente do cadastro).
- Descrição vazia ou linha solta antes de `DESCRIÇÃO:`.
- CI já lançada pelo robô antes, ou que já tem tarefa ativa no VIOS.
- CI que é cópia de outra (mesmo processo e mesmo teor): se a original está no arquivo ou já foi lançada, a cópia não é gravada; se não, vira erro para a Controladoria conferir.

Avisos (a CI é lançada, mas a página mostra para conferir): data já passada, data em sábado ou domingo, e linhas `Responsável a marcar na tarefa` / `Advogada auxiliar` na descrição (responsáveis vão no campo `RESPONSÁVEIS`).

### Como o robô preenche a tarefa no VIOS

- Tarefa, data, horário (campo Horário do VIOS) e descrição na Observação.
- Descrição toda em negrito; as linhas `PRAZO FATAL:`, `PRAZO FATAL D -2:`, `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:` em negrito e vermelho, junto com a data. O teor da intimação que o VIOS acrescenta fica normal.
- `RESPONSÁVEIS: automático`: o VIOS marca sozinho (em geral o auxiliar da intimação). Com nomes: o robô marca exatamente essas pessoas. Na petição da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- `CIÊNCIA` com `DATA:` vazia vai para o dia do envio.
- **Corte das 12h na hora do lançamento:** `CIÊNCIA` e `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` com data de hoje (ou ciência sem data) lançadas depois das 12:00, ou no sábado/domingo, vão para o próximo dia de segunda a sexta (sexta 12:01 → segunda). Só a data da tarefa muda; `PRAZO PARA EMBARGOS`, `PRAZO PARA RECURSO` e `PRAZO FATAL` da descrição ficam como estão. Se alguma dessas datas vier antes do novo dia, a tarefa fica para hoje (urgente). Data já futura no arquivo não é mexida.
- Duas tarefas da mesma CI são gravadas juntas e conferidas na tela de conferência do VIOS.

### Duplicidade

- A mesma publicação em mais de uma CI: a mais completa é a original (primeiro a endereçada ao cliente, depois a de texto maior, depois a de número menor); a outra não gera tarefa.
- O mesmo processo com atos diferentes não é duplicidade: cada CI tem a sua tarefa.
