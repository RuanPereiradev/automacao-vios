# POP e Fluxo de Intimações

Use este arquivo para decidir a providência operacional quando a intimação vier do DJEN/VIOS.

## Finalidade

A Controladoria recebe intimações no VIOS e lança tarefas para que os advogados tenham ciência da intimação e saibam como agir.

## Fluxo visual resumido

- Sentença de encerramento, com ou sem resolução do mérito, e homologação de acordo envolvendo o cliente: sempre `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` da área, mesmo favorável ou integralmente cumprida. Aplicar a regra obrigatória do SKILL.md: conferir possíveis erros comparando acordo e sentença e dar sequência ao contato com o cliente. Não usar CIÊNCIA.

- Despacho do setor: normalmente gera `CIÊNCIA`, salvo quando houver providência específica.
- Sentença, decisão ou acórdão: avaliar se demanda análise. Se houver risco, desfavorabilidade, erro judicial possível ou necessidade de providência, abrir tarefa de análise.
- Depois da análise, o advogado define se não recorre, se opõe embargos ou se interpõe outro recurso.

## Regras operacionais

Antes de aplicar as regras abaixo, ler `roteamento-interno.md`. As prioridades de RPV/precatório, emenda da Suhiane, marcação do Breno, divergências de cadastro e duplicidades prevalecem sobre regras gerais incompatíveis.

Para a prioridade de emenda da Suhiane, considerar obrigatoriamente tanto `MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026` quanto `MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026`: lançar no primeiro dia útil seguinte, preservar o prazo fatal e não aplicar D-2.

### Prevalência do cadastro interno

- Conferir o departamento e o auxiliar da planilha antes de interpretar a área pela classe judicial.
- O departamento expressamente informado e compatível com a providência prevalece sobre classe, assunto e palavras isoladas. O auxiliar valida o cadastro, mas pode estar desatualizado.
- Processos de responsabilidade cível de `JOAQ`/Joaquim devem receber tarefas de `CÍVEL`. Se houver transferência inequívoca para Execução, usar tarefa de Execução e alertar para confirmar a substituição do auxiliar por Tamira.
- Processos com auxiliar `SUH`/Suhiane devem ser classificados como `TRABALHISTA — RECLAMANTE` ou `PREVIDENCIÁRIO`, conforme o teor. Justiça do Trabalho, número CNJ `.5.`, Vara do Trabalho, reclamante ou exequente trabalhista indicam tarefa Trabalhista, inclusive na fase executiva. Processo contra o INSS ou sobre benefício previdenciário/assistencial indica tarefa Previdenciário.
- Para `SUH`/Suhiane, não usar tarefa de Execução ou Cível por palavra isolada. Se a classificação final não for Trabalhista — Reclamante ou Previdenciário, revisar; manter Execução somente quando a transferência estiver confirmada e registrar a divergência do auxiliar.
- Não usar tarefa de Execução apenas por causa da natureza executiva do ato. Usá-la somente quando o cadastro interno estiver no departamento de Execução ou houver orientação expressa do usuário.
- Se houver conflito, manter a área do cadastro interno e registrar a divergência. Se o setor não puder ser confirmado, marcar `PENDENTE – CONFIRMAR ÁREA CADASTRADA NO VIOS.`
- Conferir antes da resposta: `Auxiliar/Departamento → Área da tarefa`.

- Sempre que a tarefa for `VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL`, indicar também a tarefa `SUSTENTAÇÃO ORAL`.
- A tarefa `VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL` fica para o mesmo dia.
- A tarefa `SUSTENTAÇÃO ORAL` fica para o dia da sustentação.
- Modelo da tarefa de sustentação oral:

```text
SUSTENTAÇÃO ORAL

DATA:
HORA:
LINK:
```

- Manifestação sobre laudos ou proposta de acordo do INSS: usar `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026`.
- Audiência inicial não deve ser automaticamente indicada como UNA; pode ser instrução ou conciliação.
- Decisão, despacho, sentença ou acórdão desfavorável ao cliente normalmente gera tarefa de análise.
- Mesmo decisão favorável pode exigir análise quando houver possibilidade de erro judicial, principalmente em Previdenciário e Execução.
- Em protocolo do departamento de Execução, usar `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (EXECUÇÃO) 2026` quando o ato mencionar o cliente, produzir efeito sobre ele ou exigir conferência jurídica. Não substituir por tarefa de Cível.
- Se a decisão de Execução não citar o cliente e não produzir efeito, obrigação, prazo ou providência para ele, usar `CIÊNCIA (EXECUÇÃO) 2026`. O simples título `DECISÃO` não gera análise automaticamente.
- Abrir `CIÊNCIA` apenas quando realmente não houver necessidade de movimentação.
- Trabalhista não possui tarefa específica de manifestação sobre cálculos. Se houver prazo para manifestação de cálculos, usar `MINUTAR PETIÇÃO INTERMEDIÁRIA DIVERSA (TRABALHISTA) 2026`.
- Distribuição simples gera `CIÊNCIA`.

## Audiências

Quando houver audiência, informar no padrão:

```text
AUDIÊNCIA DE [TIPO]

DATA:
HORÁRIO:
FORMATO:
LINK/LOCAL:
```

Identifique corretamente o tipo de audiência para que o advogado saiba como se preparar.

Se for audiência cível e o cliente estiver como parte ré/reclamada:

- indicar que se trata de audiência para parte reclamada/ré;
- orientar verificação no VIOS/PJe se já existe contestação;
- se não houver contestação, indicar também tarefa de `MINUTAR CONTESTAÇÃO`.

## Perícias

Quando houver perícia, informar no padrão:

```text
TIPO:
DATA:
HORA:
LOCAL:
```

É necessário identificar o tipo de perícia, como médica, técnica ou avaliação social.

## Avaliação social previdenciária

Em toda perícia social previdenciária, indicar:

1. `AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para Leticya;
2. `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para a **mesma data operacional do aviso/perícia social no VIOS**.

Aplicar também quando a tarefa principal se chamar `PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` ou equivalente. Não confundir a data operacional da instrução com a data da visita. Na ausência de orientação específica do usuário, lançar aviso e instrução para o dia seguinte. Confirmar o responsável pela instrução no fluxo/cadastro do VIOS, sem presumir o mesmo do aviso.

Se houver pedido de documentação, endereço, telefone ou dados similares, indicar também minuta para Tamira no mesmo dia da análise, preservando o prazo jurídico. A minuta não dispensa aviso nem instrução.

Se a intimação apenas informar que haverá visita, indicar aviso e instrução, sem minuta. A falta de data/horário da visita não dispensa a instrução.

Apresentar cada tarefa separadamente e conferir que cada processo com perícia social tenha sua tarefa de instrução. Usar o modelo de instrução de `tarefas-vios.md`.

Modelo da tarefa:

```text
Aviso: Foi agendada perícia social relacionada ao processo. O(a) assistente social pode ir até a casa do cliente a qualquer momento para a realização da visita.

"[inserir pequeno resumo do trecho principal da intimação, preferencialmente do trecho De ordem do MM... até a menção ao prazo de 15 dias]"
```

## RPV, precatório e requisição

- Decisão que determina expedição de RPV: abrir tarefa de análise.
- Quando os requisitórios já foram expedidos: usar `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`.
- Em qualquer etapa relacionada a RPV/precatório, lançar a tarefa para o dia útil seguinte à publicação ou recebimento, preservando o prazo jurídico fatal em campo separado, conforme `roteamento-interno.md`.

## Minutas diretas

Tarefas de minutar podem ser abertas pela Controladoria quando a intimação já diz exatamente o que deve ser feito e indica prazo.

`MINUTAR CONTESTAÇÃO` costuma ser aberto diretamente quando a intimação indicar necessidade de defesa e houver elementos suficientes.

## Responsável pelas petições da Execução

- Sempre que a tarefa for `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)` ou a opção equivalente disponível no VIOS, informar obrigatoriamente: `Responsável a marcar na tarefa: BRENO`.
- Aplicar esse lembrete em todas as petições com esse nome, inclusive apresentação de dados bancários, providências relacionadas a RPV/precatório, alvarás, documentos e outras manifestações da Execução.

## Pagamento pelo cliente — Trabalhista

Quando a intimação trabalhista determinar pagamento, depósito judicial, honorários periciais, custas, preparo, depósito recursal ou outro valor pelo cliente:

- indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou a opção equivalente de análise aplicável ao ato;
- registrar no resumo a natureza do pagamento e o prazo;
- não sugerir tarefa de gerar guia nesse momento;
- não indicar `CIÊNCIA` no lugar da análise;
- não indicar minuta como tarefa complementar inicial.

A análise deve ocorrer antes porque ela gera o fluxo de contato com o cliente. Primeiro, avisar o cliente e perguntar se deseja pagar; somente depois da manifestação favorável do cliente o setor trabalhista providencia a guia, quando autorizada. Após o pagamento, abrir a tarefa necessária para comprová-lo nos autos.

## Pagamento pelo cliente — Cível

Quando a intimação cível determinar pagamento, depósito judicial, custas, honorários ou outro valor pelo cliente, indicar desde logo:

- tarefa de análise cível aplicável ao ato;
- `ENTRAR EM CONTATO COM O CLIENTE 2026`;
- `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026`, para comprovar o pagamento, depósito ou recolhimento nos autos.

Indicar as três tarefas imediatamente. Não aguardar o resultado da análise ou do contato para sugerir a minuta. Não substituir esse fluxo por `CIÊNCIA` ou por tarefa isolada de geração de guia. Aplicar também a parcelamento de custas, decisão interlocutória, cumprimento de sentença e outros atos que imponham pagamento ao cliente.

## Resultado esperado da análise

Quando o usuário encaminhar arquivo do VIOS com intimações:

- dizer do que se trata cada intimação;
- indicar qual tarefa abrir no VIOS;
- informar se cabe recurso;
- se couber, informar qual recurso e prazo;
- se couber embargos, informar prazo de embargos;
- incluir resumo curto e simples com o teor da intimação.

Para embargos ou recurso, use:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA
```

Se couber apenas um deles, informe somente o aplicável.

Exceção obrigatória: na tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, se couber (ou puder caber) embargos ou recurso, exibir as duas linhas com data em D-2 (prazo legal quando a intimação não informar, inclusive com cabimento pendente); o meio que não couber fica `NÃO CABE`. Se não couber nenhum, deixar somente o `PRAZO FATAL (D-2)`.
