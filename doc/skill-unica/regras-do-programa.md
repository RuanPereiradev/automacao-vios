## Regras do programa (bot) — datas, bloqueios e conferências

No bot, as regras desta seção são aplicadas pelo programa depois da resposta da IA (a IA não calcula as datas). Elas estão aqui para que a análise feita no chat chegue ao mesmo resultado do bot e possa ser comparada com ele.

### Sugestões do VIOS

As sugestões automáticas de tarefa do VIOS são apenas indício, nunca decisão.

### Contagem de prazo

- Disponibilização × publicação: no diário eletrônico, considera-se publicada a intimação no 1º dia útil seguinte ao da disponibilização (Lei 11.419/2006, art. 4º, § 3º). Os arquivos e relatórios do bot levam no nome a data de **disponibilização** (ex.: `analise_2026-10-27` = disponibilizadas em 27/10/2026, publicadas em 28/10/2026); por isso a publicação das CIs é um dia útil depois da data do arquivo, e isso não é erro. O prazo conta da publicação.
- O prazo começa no 1º dia útil após a publicação (CPC, art. 224).
- Dia útil: segunda a sexta, sem feriado. Feriados considerados: nacionais; os da Justiça Federal (Lei 5.010/66, art. 62), só em processo federal; estaduais e municipais da tabela de feriados; e os cadastrados pela Controladoria (`doc/feriados.txt`).
- Recesso forense de 20/12 a 20/01 (CPC, art. 220): os prazos não correm, nem os contados em dias corridos.
- Prazo que vence em dia não útil (ou no recesso) vai para o próximo dia útil.
- Pontos facultativos e feriados não confirmados não mudam a data: viram alerta para conferir. A data fica adiantada, para não perder prazo.
- **D-2** = 2 dias úteis antes do prazo fatal.
- Quando a intimação não informa os dias, usar o prazo previsto em lei (seção "Prazo previsto em lei" da referência de prazos e recursos). Se couber, ou puder caber, embargos ou recurso, o prazo deles sempre tem dias (nunca 0): o advogado decide se recorre e precisa da data.

### Data de cada tarefa

| Caso | Data da tarefa no VIOS | Linha de prazo na descrição |
| --- | --- | --- |
| Tarefa com prazo (regra geral) | D-2 do prazo principal | `PRAZO FATAL (D-2): DD/MM/AAAA` |
| RPV/precatório | próximo dia útil após a publicação | `PRAZO FATAL: DD/MM/AAAA` |
| Emenda à inicial com auxiliar SUH | próximo dia útil após a publicação | `PRAZO FATAL: DD/MM/AAAA` |
| `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` | mesmo dia da análise (nunca D-2) | ver abaixo |
| Verificar viabilidade de sustentação | mesmo dia da análise | — |
| Aviso e instrução de perícia social | próximo dia útil após a análise (a instrução sempre na mesma data do aviso) | — |
| Audiência, perícia técnica, perícia médica, sustentação oral | data exata do ato (nunca D-2); na sessão virtual, o 1º dia da sessão | horário no campo Horário do VIOS |
| Ciência e tarefas sem prazo | sem data | — |

Na tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`:
- se couber, ou puder caber, embargos ou recurso: as duas linhas `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:`, com data em D-2 (`NÃO CABE` na que não couber), e sem a linha `PRAZO FATAL (D-2)`;
- se não couber nenhum dos dois: só o `PRAZO FATAL (D-2)` do ato, se houver.

### Descrição da tarefa no VIOS

Ordem das linhas:
1. as linhas de prazo (tabela acima);
2. o texto da descrição, seguindo o modelo da tarefa.

Não vão na descrição: `Responsável a marcar na tarefa: BRENO`, `Advogada auxiliar: TAMIRA`, `PRIORIDADE RPV/PRECATÓRIO` (e `PRIORIDADE EMENDA`). Os responsáveis vão no campo Responsáveis do VIOS: na tarefa `MINUTAR PETIÇÃO EXECUÇÃO`, o bot marca Breno junto com a Tamira. Se a IA escrever essas linhas, o bot as apaga.

Exemplo (RPV, Execução):

```text
PRAZO FATAL: 29/10/2026
MINUTAR PETIÇÃO PARA INFORMAR OS DEMAIS DADOS NECESSÁRIOS PARA A CONFECÇÃO DOS REQUISITÓRIOS (RPV/PRECATÓRIO)
Despacho: considerando a certidão de ID 192859275, intime-se a parte exequente para, no prazo de 5 dias, informar os demais dados necessários para a confecção dos requisitórios.
```

### Quando NÃO lançar a CI no VIOS

A CI não é lançada (fica para a Controladoria conferir e lançar à mão) quando:
- falta na intimação informação que a tarefa exige e que só o PJe tem (audiência sem tipo, data, horário, formato, local ou link/ID/senha; perícia sem data, horário ou local; data do ato que não consta);
- a intimação só indica um evento do processo, sem o teor (ex.: "O ato refere-se ao seguinte evento: Evento 23 - PETIÇÃO"): a tarefa depende de abrir o evento no sistema; não usar `CIÊNCIA` por falta de informação;
- a tarefa com horário (audiência, perícia, sustentação oral) está sem o horário;
- na tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, cabe embargos ou recurso, mas não há prazo para calcular a data;
- o ato é sentença ou acórdão e não há a tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` (ex.: a IA indicou só `MINUTAR RECURSO/CONTRARRAZÕES`): o advogado é quem decide se cabe recurso;
- a área da tarefa diverge do auxiliar (quando há um único auxiliar):
  - auxiliar TAMI (Tamira, Execução) com tarefa de outra área (Cível, Trabalhista, Previdenciário) e nenhuma de Execução: confirmar o departamento;
  - auxiliar JOAQ, JOAN, LILI, SUH, CARL ou JOHN com tarefa de Execução: confirmar se o processo já foi transferido para a Execução (Tamira);
  - auxiliar SUH com tarefa Cível: a tarefa deveria ser Trabalhista — Reclamante ou Previdenciário.

  Com mais de um auxiliar (ex.: "TAMI / SUH"), vale a análise, sem esse bloqueio automático.

### Alertas (a CI é lançada, mas com aviso para conferir)

- Tarefa não definida (`PENDENTE – CONFIRMAR OPÇÕES DISPONÍVEIS NO VIOS` ou `NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA`) ou nenhuma tarefa indicada.
- Perícia social sem a tarefa `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`.
- `VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL` sem a tarefa `SUSTENTAÇÃO ORAL`.
- `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO)` sem a tarefa de quesitos/assistente técnico (`… IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO)`).
- Ato (audiência, perícia, sessão) marcado para antes do D-2 do prazo: antecipar a data da tarefa.
- Há prazo no texto, mas sem o número de dias para calcular a data.
- Feriado não confirmado ou ponto facultativo dentro do prazo; cidade sem feriados locais cadastrados.

### Duplicidade

- A mesma publicação em mais de uma CI: a mais completa é a original e a outra é ignorada (não abrir nova tarefa; vale a tarefa da CI original).
- O mesmo processo com atos diferentes: só alerta, cada CI tem a sua tarefa.
