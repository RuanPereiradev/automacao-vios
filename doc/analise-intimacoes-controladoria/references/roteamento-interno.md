# Roteamento interno, prioridades e validação

## Ordem obrigatória de decisão

Analisar separadamente natureza jurídica, fase processual, departamento interno, auxiliar cadastrado e providência concreta. Definir a tarefa nesta ordem:

1. correção ou orientação expressa do usuário;
2. providência concreta determinada na intimação;
3. fase processual atual;
4. departamento interno responsável pela providência;
5. advogado auxiliar informado na planilha;
6. natureza jurídica, órgão e número CNJ;
7. classe e assunto processual.

Não classificar somente pelo número CNJ, classe, fase ou auxiliar. Um processo trabalhista ou previdenciário pode estar no Departamento de Execução. A presença de `execução`, `penhora`, `alvará` ou `cumprimento de sentença` não basta para classificar o departamento.

## Mapeamento operacional

| Auxiliar | Área normalmente relacionada | Conferência obrigatória |
| --- | --- | --- |
| Joaquim/JOAQ | Cível | Se a tarefa for Execução, não lançar: confirmar se houve transferência para Tamira. |
| Joana/JOAN | Cível | Se a tarefa for Execução, não lançar: confirmar se houve transferência para Tamira. |
| Lili/LILI | Cível | Se a tarefa for Execução, não lançar: confirmar se houve transferência para Tamira. |
| Suhiane/SUH | Trabalhista Reclamante ou Previdenciário | Diferenciar pelo teor, órgão, partes e número CNJ. |
| Tamira/TAMI | Execução | Conferir pelo departamento e também pelo responsável: se a Tamira é a responsável, a tarefa é de Execução. Se a tarefa ficar em outra área, não lançar e confirmar o departamento. |
| Carlos/CARL | Trabalhista Reclamada | Conferir cliente e teor. |
| Johnys/JOHN | Trabalhista Reclamada | Conferir cliente e teor. |
| Breno | Petições da Execução da Tamira | Marcar nas tarefas `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)`. |

O mapeamento é alerta de consistência, não substitui a leitura integral.

## Divergências de cadastro

Se a tarefa for de Cível, Trabalhista ou Previdenciário, mas o auxiliar for Tamira, usar a tarefa da área correta e informar:

```text
OBSERVAÇÃO DE CADASTRO:
A tarefa identificada é da área [ÁREA], mas o processo aparece com a Tamira. Confirmar se o auxiliar está correto ou se o processo já foi transferido para o Departamento de Execução.
```

Se a providência for inequivocamente da Execução e o auxiliar for outro, usar a tarefa de Execução e informar:

```text
OBSERVAÇÃO DE CADASTRO:
O processo exige providência do Departamento de Execução, mas o auxiliar informado é [NOME]. Confirmar a transferência do processo para a Tamira.
```

Se houver dúvida real entre Cível e Execução, não escolher silenciosamente. Informar:

```text
PENDENTE – CONFIRMAR SE O PROCESSO PERMANECE NO CÍVEL OU SE JÁ FOI TRANSFERIDO PARA A EXECUÇÃO.
Se permanecer no Cível: [tarefa cível].
Se já estiver na Execução: [tarefa de execução].
```

## Prioridade de RPV e precatório

Tratar como prioritária toda intimação relacionada a determinação ou minuta de RPV/precatório, cálculos, documentos, procuração, contrato ou destaque de honorários, dados bancários, alvará vinculado, cancelamento, conversão, retificação, manifestação ou pendência capaz de impedir expedição, conferência ou pagamento.

- Indicar a tarefa para o dia útil seguinte à publicação ou ao recebimento, mesmo que o prazo jurídico seja maior.
- Se o dia seguinte não for útil, usar o primeiro dia útil subsequente.
- Esta prioridade prevalece sobre D-2.
- Preservar separadamente o prazo jurídico fatal.
- Usar:

```text
PRAZO FATAL: DD/MM/AAAA
```

No resumo:

```text
PRAZO FATAL: DD/MM/AAAA
[providência]
[trecho da intimação]
```

Não escrever `PRIORIDADE RPV/PRECATÓRIO` na descrição.

Não chamar a data prioritária de `PRAZO FATAL (D-2)`.

### Etapas do requisitório

| Situação | Tarefa |
| --- | --- |
| Decisão determinando futura expedição | Analisar sentença/acórdão/decisão da área. |
| Cálculos, documentos ou dados bancários necessários | Minutar petição da área. |
| Minuta já expedida | `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`. |
| Alvará expedido sem providência | Ciência da área. |
| Erro ou pendência no requisitório | Analisar minuta ou decisão, conforme o ato. |

## Prioridade de emenda da Suhiane

Quando o auxiliar for Suhiane/SUH e a tarefa for qualquer tarefa de minutar emenda à inicial, aplicar esta prioridade sem distinção de área. A regra abrange obrigatoriamente:

- `MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026`;
- `MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026`;
- qualquer opção equivalente de emenda à inicial sob responsabilidade da Suhiane.

- indicar a tarefa para o dia útil seguinte à publicação ou recebimento;
- preservar o prazo jurídico fatal separadamente;
- fazer a prioridade prevalecer sobre D-2;
- não aplicar nem exibir `PRAZO FATAL (D-2)` como data operacional;
- usar:

```text
PRAZO FATAL: DD/MM/AAAA
```

No resumo:

```text
PRAZO FATAL: DD/MM/AAAA
MINUTAR EMENDA À INICIAL
[documentos ou informações exigidos]
```

Não aplicar automaticamente a outras tarefas da Suhiane. A regra é obrigatória para emenda à inicial tanto Trabalhista quanto Previdenciária.

## Petição de Execução da Tamira e Breno

Quando a tarefa for `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)` ou equivalente e pertencer à Tamira, Tamira e Breno são os responsáveis da tarefa no VIOS. Não escrever `Advogada auxiliar: TAMIRA` nem `Responsável a marcar na tarefa: BRENO` na descrição da tarefa.

Aplicar a dados bancários, documentos, alvará, RPV/precatório, cálculos, prosseguimento, bloqueio, penhora e demais petições intermediárias da Execução. Não substituir Tamira por Breno.

## Analisar ou minutar

- Antes das regras gerais, aplicar a regra do SKILL.md para sentença de encerramento ou homologação de acordo envolvendo o cliente: sempre ANALISAR da área responsável, mesmo favorável; conferir erros na homologação e registrar a necessidade de contato com o cliente. Não usar CIÊNCIA nem decidir apenas pela existência de providência objetiva.

- Se a intimação determinar objetivamente o que fazer e trouxer prazo, indicar diretamente a tarefa de minutar disponível para a área.
- Se exigir avaliação de resultado, erro, recurso ou estratégia, indicar analisar.
- O título decisão, despacho ou sentença não define sozinho a tarefa.
- Se a ordem for dirigida à parte contrária, não abrir minuta para o cliente.
- Aplicar as tarefas complementares de pagamento, depósito ou contato quando previstas.

## Duplicidades

- Manter cada CI em sua posição e numeração originais, mesmo quando duplicada.
- Nunca fundir cabeçalhos como `26 e 45. CIs...`.
- Identificar a CI mais completa e não abrir tarefas repetidas. A CI mais completa é a original; a outra é ignorada (não gera tarefa).
- Duplicata é a mesma publicação em mais de uma CI do mesmo processo: o texto é praticamente igual e muda só o destinatário, o link ou o código da comunicação (o VIOS costuma trazer uma cópia para cada parte). Quando só muda o destinatário, a original é a CI endereçada ao cliente do escritório; a cópia endereçada à outra parte é ignorada.
- Mesmo processo com ato diferente (ex.: perícia designada e depois redesignada) não é duplicata: analisar cada CI e, se a mais nova mudar data ou local, atualizar a tarefa existente em vez de abrir outra.
- O robô confere duplicatas em dois momentos: ao capturar as intimações do VIOS (marca a cópia) e ao enviar o arquivo para o robô (lê no VIOS o texto de cada CI antes de gravar e não grava a cópia). Mesmo assim, na análise feita no chat, conferir as duplicatas e não colocar a cópia no arquivo para o robô: listar como `DUPLICADA DA CI [NÚMERO]`.
- Na menos completa, informar:

```text
DUPLICADA DA CI [NÚMERO].
Não abrir nova tarefa. Utilizar a tarefa indicada na CI mais completa.
```

- Se a segunda CI acrescentar prazo, data ou local, atualizar a tarefa existente.
- Não confundir duplicidade com tarefas complementares exigidas pelo mesmo ato.

## Modelo com data operacional

```text
[n]. CI [número] — Processo [número]
Cliente:
Natureza jurídica:
Departamento interno provável:
Advogado auxiliar informado:
Do que se trata:
Tarefa no VIOS:
Advogada auxiliar:
Responsável a marcar na tarefa:
Tarefa complementar:
Prazo jurídico fatal:
Data operacional normal — D-2:
DATA DA TAREFA NO VIOS:
Motivo da data da tarefa:
Cabe recurso?
Resumo para tarefa:
Observação de cadastro:
Duplicidade:
```

## Bloqueios antes da resposta

Não finalizar enquanto houver inconsistência não explicada. Conferir em cada CI:

- destinatário da ordem;
- natureza, fase e departamento;
- compatibilidade do auxiliar com a tarefa;
- divergência de cadastro registrada;
- escolha entre analisar e minutar;
- prazo fatal e data operacional separados;
- prioridade de RPV para o dia útil seguinte;
- toda emenda à inicial da Suhiane, Trabalhista ou Previdenciária, para o primeiro dia útil seguinte, sem D-2 e com o rótulo de prioridade;
- marcação do Breno na petição de Execução da Tamira;
- duplicidade sem repetição de tarefa;
- existência do nome da tarefa na lista oficial do VIOS.
