---
name: analise-intimacoes-controladoria
description: use quando a solicitação envolver análise de intimações recebidas pelo DJEN/VIOS, planilhas de intimações, definição de tarefa VIOS, ciência, despacho, decisão, sentença, acórdão, audiência, perícia, prazo, recurso, embargos, contrarrazões, sustentação oral, RPV/precatório, guias, depósito judicial ou providência operacional da Controladoria Jurídica.
---

# Análise de Intimações da Controladoria

Esta skill padroniza a triagem de intimações recebidas no VIOS/DJEN e indica a tarefa VIOS adequada, prazo fatal, prazo operacional D-2, cabimento de recurso e descrição sugerida para o advogado.

## Fontes

Use as fontes nesta ordem:

1. Documento, intimação, planilha ou arquivo atual enviado pelo usuário.
2. seção "Referência — POP e Fluxo de Intimações" (mais abaixo).
3. seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo) para área, responsável, prioridades, divergências e duplicidades.
4. seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo).
5. seção "Referência — Regras de Prazos e Recursos" (mais abaixo).
6. Arquivos de conhecimento da Controladoria, quando disponíveis.
7. Memória, apenas como apoio e nunca para substituir o documento atual.

Se houver conflito entre o documento atual e fonte anterior, privilegie o documento atual e registre a divergência.

## Entrada esperada

O usuário pode enviar:

- arquivo do VIOS com intimações;
- planilha de intimações;
- print ou PDF de intimação;
- texto colado de intimação;
- pedido direto como "qual tarefa abrir?", "analise a intimação", "cabe recurso?" ou "qual prazo?";
- analise essas intimações e me indique quais trefas abrir no padrão já solicitado. 

Quando a entrada for planilha de intimações, considere que o cliente costuma aparecer na quarta ou quinta coluna. Confirme pelo conteúdo antes de concluir.

## Fluxo de análise

1. Leia integralmente o documento antes de perguntar.
2. Leia seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo) e identifique separadamente natureza jurídica, fase, departamento e auxiliar. Não decida por um único desses campos.
3. Identifique cliente/parte representada, parte ativa, parte passiva e posição processual (as vezes vem AVANTTI SOLUCOES PRESTADORA DE SERVICOS LTDA (MATRIZ): PRESTADORA. e as vezes FAMOL COMERCIO DE MOVEIS LTDA (MATRIZ) mas é a mesma empresa) se não for indicado o cliente que colquei me indique como uma observação.
4. Classifique o ato: distribuição, despacho, decisão, sentença, acórdão, audiência, perícia, laudo, proposta de acordo, cálculos, RPV/precatório, guias, depósito judicial ou outro.
5. Verifique se há prazo fatal, audiência, perícia, link, ID, senha, local, formato, ou obrigação de juntar documento.
6. Defina a tarefa VIOS principal usando seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo)nunca indique uma tarefa que não está nessa planilha.
7. Defina tarefas complementares quando o POP exigir mas sempre  usando seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo) mesmo sendo complementar, como por exemplo sustentação que eu preciso abrir duas.
8. Quando a intimação determinar pagamento pelo cliente, aplicar obrigatoriamente o fluxo específico da área descrito abaixo e em seção "Referência — POP e Fluxo de Intimações" (mais abaixo). No Trabalhista, começar por análise e não sugerir geração de guia. No Cível, indicar desde logo análise, contato com o cliente e minuta.
9. Verifique se cabe embargos ou recurso e informe os prazos. Use D-2 como regra geral, mas aplique a data prioritária do dia útil seguinte para RPV/precatório e emenda à inicial da Suhiane.
10. Monte a descrição sugerida para o VIOS com o modelo da tarefa correspondente.
11. Em toda perícia social previdenciária, indicar a tarefa de aviso e a tarefa obrigatória de instrução, conforme a regra abaixo. Se houver pedido de dados/documentos, indicar também MINUTAR para Tamira no mesmo dia da análise, preservando o prazo jurídico. Usar no aviso o padrão em negrito e sublinhado e, abaixo, um pequeno resumo entre aspas do trecho principal da intimação.

## Regra obrigatória — instrução de toda perícia social previdenciária

Sempre que indicar `PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, `AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` ou uma opção equivalente de aviso/perícia social, indicar também, obrigatoriamente:

`INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`

- Lançar a instrução para a **mesma data da tarefa de perícia social ou aviso no VIOS**. Esta é a data operacional da tarefa, não necessariamente a data da visita. Se o usuário determinar uma data, aplicá-la às duas tarefas.
- Aplicar a todas as perícias sociais, inclusive às intimações apenas informativas, às visitas sem data/horário e aos casos que também exigem minuta.
- Não substituir o aviso ou a minuta pela instrução. Apresentar cada tarefa em bloco próprio, com nome exato, data e resumo.
- Quando houver pedido de dados/documentos, indicar as três providências: aviso, instrução e minuta para Tamira. Manter a prioridade e o prazo próprios da minuta.
- Confirmar o responsável pela instrução no cadastro/fluxo do VIOS; não presumir que seja o mesmo do aviso. A ausência dessa informação não dispensa indicar a tarefa e a data.
- Antes de finalizar, conferir uma tarefa de instrução para cada processo com perícia social. Não finalizar a análise de perícia social sem essa tarefa complementar.

Resumo sugerido para a instrução:

```text
Realizar instrução do(a) cliente para a perícia social. Explicar como ocorre a avaliação, orientar a apresentação de informações verdadeiras sobre sua realidade familiar, condições de vida e, quando pertinente, atividade de trabalho. Confirmar os dados de localização e conferir nos autos eventual data, horário e local. Registrar a orientação realizada.
```

## Regra obrigatória — pagamento pelo cliente: diferenciar Trabalhista e Cível

### Trabalhista

Sempre que uma intimação trabalhista determinar ao cliente/reclamado:

- pagamento ou depósito judicial;
- recolhimento de honorários periciais;
- pagamento de custas ou outro valor;
- comprovação do pagamento nos autos;

indicar primeiro a tarefa:

`ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026`

Usar a opção equivalente de análise disponível no VIOS quando o ato não couber literalmente nesse nome.

Não sugerir nem abrir tarefa de gerar guia nesse primeiro momento. A tarefa de análise gera o fluxo de contato com o cliente, para avisá-lo e perguntar se deseja realizar o pagamento antes da emissão da guia.

Não indicar `CIÊNCIA (TRABALHISTA) 2026` no lugar da análise. Também não indicar tarefa de minutar como tarefa complementar inicial. Somente depois da manifestação favorável do cliente o fluxo trabalhista deverá providenciar a guia, quando autorizada; após o pagamento, deverá abrir a tarefa necessária para comprová-lo nos autos.

Aplicar essa sequência inclusive a honorários periciais, custas, depósito judicial comum, depósito recursal, preparo e outros valores devidos pelo cliente. Informar a natureza e o prazo do pagamento no resumo da tarefa de análise, sem antecipar a emissão da guia.

### Cível

Sempre que uma intimação cível determinar pagamento, depósito, custas, honorários ou outro valor pelo cliente, indicar desde logo as três tarefas:

1. `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026` ou a tarefa equivalente de análise aplicável ao ato;
2. `ENTRAR EM CONTATO COM O CLIENTE 2026`;
3. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026`, descrevendo que a minuta é para comprovar o pagamento, depósito ou recolhimento nos autos.

No Cível, não aguardar o resultado da análise ou do contato para indicar a tarefa de minutar. Não substituir esse conjunto por `CIÊNCIA` ou por tarefa isolada de geração de guia.

Aplicar as regras somente quando o cliente for a parte responsável pelo pagamento. Se houver divergência entre o destinatário da publicação e a parte obrigada, indicar a necessidade de confirmar a intimação própria e o início do prazo.


## Regra obrigatória — sentença de encerramento e homologação de acordo

- Indicar sempre `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` da área responsável para sentença que encerre o processo ou a fase processual, com ou sem resolução do mérito, inclusive homologação de acordo. Aplicar mesmo quando favorável, integralmente cumprida, sem obrigação pendente, com renúncia recursal ou determinação de arquivamento. Não substituir por `CIÊNCIA`.
- Conferir possíveis erros na homologação: comparar a sentença com o acordo e seus aditivos quanto a partes, valores, parcelas, vencimentos, obrigações de fazer/pagar, multas, quitação, custas, honorários e extensão da extinção. Conferir se houve omissão, contradição, obscuridade, erro material ou alteração do pactuado. Não presumir correção por o resultado ser favorável.
- Se o acordo ou outro documento necessário não estiver disponível, registrar `PENDENTE – CONFERIR A SENTENÇA COM O ACORDO E DOCUMENTOS DOS AUTOS`, mantendo a tarefa de análise. Não afirmar que a homologação está correta apenas pelo relato da sentença.
- Incluir na finalidade e no resumo da análise a necessidade de dar sequência ao contato com o cliente para informar o resultado, explicar o encerramento e esclarecer eventuais providências. A análise abrange conferência jurídica e comunicação ao cliente; não depende de intenção de recorrer. Seguir o fluxo de contato da área, sem criar automaticamente tarefa complementar fora das hipóteses previstas.
- Exibir sempre `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:` conforme as regras de prazos. Avaliar cabimento e eventual renúncia/aceitação; não presumir ausência de prazo ou impossibilidade de correção apenas pelo resultado favorável. Se depender de documentos ausentes, registrar a pendência. Não abrir minuta de recurso automaticamente.
- Sentença ou acórdão, favorável ou desfavorável, gera sempre `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, nunca tarefa de minutar (nem `MINUTAR RECURSO/CONTRARRAZÕES`): quem decide se cabe recurso e o que fazer é o advogado, na análise.
- Esta regra prevalece sobre todas as regras gerais de ciência, inclusive a de decisão de Execução sem providência para o cliente, quando o ato encerrar o processo/fase do cliente ou homologar acordo que o envolva.

Resumo-base para adaptar ao caso:

```text
[Inserir PRAZO FATAL (D-2) somente quando houver prazo calculável.]
Analisar a sentença de encerramento e conferir possíveis erros, omissões ou divergências na homologação em relação ao acordo, inclusive valores, obrigações, custas e honorários. Dar sequência ao contato com o cliente para informar o resultado e esclarecer eventuais providências.
```

## Regras centrais

### Regra obrigatória — prevalência do departamento e do auxiliar

Aplicar integralmente seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo). A ordem obrigatória é: orientação expressa do usuário; providência concreta; fase atual; departamento responsável; auxiliar cadastrado; natureza/órgão/CNJ; classe e assunto.

- Antes de escolher a área da tarefa, conferir obrigatoriamente o departamento e o auxiliar informados na planilha do VIOS.
- Quando o departamento estiver expressamente informado e for compatível com a providência, ele prevalece sobre classe, assunto e palavras isoladas. O auxiliar é elemento de validação, mas pode estar desatualizado e não prevalece sozinho sobre uma fase de Execução inequivocamente confirmada.
- Se o auxiliar for `JOAQ`/Joaquim e o processo permanecer sob responsabilidade cível, usar tarefa `CÍVEL`. Se o teor demonstrar transferência inequívoca para Execução, usar tarefa de Execução e alertar para confirmar a troca do auxiliar para Tamira.
- Se o auxiliar for `SUH`/Suhiane, classificar o processo exclusivamente como `TRABALHISTA — RECLAMANTE` ou `PREVIDENCIÁRIO`, diferenciando pelo teor, pelo número CNJ, pelo órgão julgador e pelas partes. Processo da Justiça do Trabalho, especialmente com numeração `.5.`, reclamante, reclamada, exequente trabalhista ou Vara do Trabalho, deve usar tarefa `TRABALHISTA`, mesmo quando estiver em liquidação, cumprimento, penhora, liberação de valores ou fase executiva. Processo contra o INSS ou que trate de benefício previdenciário/assistencial deve usar tarefa `PREVIDENCIÁRIO`.
- A expressão `Execução` no ato não transforma, sozinha, processo acompanhado por Suhiane em departamento de Execução. Se a transferência para Execução estiver confirmada pelo documento ou pelo usuário, usar a tarefa de Execução e registrar a divergência do auxiliar.
- Não classificar uma CI como Execução apenas porque o ato ou a classe judicial possui natureza executiva. Usar tarefa de Execução somente quando o processo estiver cadastrado no departamento interno de Execução ou houver orientação expressa do usuário nesse sentido.
- Havendo conflito entre auxiliar/departamento e classe judicial, manter a tarefa do setor cadastrado e registrar a divergência em `Observação`.
- Se não for possível identificar com segurança o departamento pelo arquivo, usar `PENDENTE – CONFIRMAR ÁREA CADASTRADA NO VIOS.`
- Antes de finalizar cada CI, comparar obrigatoriamente: `Auxiliar/Departamento da planilha → Área da tarefa indicada`. Se forem diferentes, revisar a classificação e só manter a divergência quando houver justificativa expressa ou orientação específica do usuário.
- Conferência específica de `SUH`/Suhiane: a tarefa final deve ser Trabalhista — Reclamante ou Previdenciário; se aparecer Cível ou Execução, interromper a resposta e revisar pelo teor.

Não aplicar essa última conferência de forma absoluta quando o documento ou o usuário confirmar que o processo já foi transferido para o Departamento de Execução. Nesse caso, usar a tarefa de Execução e registrar a divergência do cadastro.

- Não invente dados.
- Quando um dado não constar, use `PENDENTE – NÃO CONSTA NO DOCUMENTO.`
- Quando a tarefa VIOS não estiver clara, use `PENDENTE – CONFIRMAR OPÇÕES DISPONÍVEIS NO VIOS.`
- Distribuição simples normalmente gera `CIÊNCIA`.
- Despacho sem providência prática normalmente gera `CIÊNCIA`.
- Sentença, decisão ou acórdão desfavorável ao cliente normalmente gera tarefa de `ANALISAR`.
- No Previdenciário e na Execução, decisão pode exigir `ANALISAR` mesmo quando aparentemente favorável, pois pode haver erro judicial.
- Em protocolo do departamento de Execução, usar `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (EXECUÇÃO) 2026` quando o ato mencionar o cliente, produzir efeito sobre ele ou exigir conferência jurídica. Não usar tarefa de Cível.
- Se a decisão de Execução não citar o cliente e não produzir efeito, obrigação, prazo ou providência para ele, usar `CIÊNCIA (EXECUÇÃO) 2026` e registrar que não houve determinação dirigida ao cliente. O simples título `DECISÃO` não gera análise automaticamente.
- Não abra tarefa de recurso diretamente quando depender de análise do advogado. Informe cabimento e prazo, mas sugira a tarefa de análise quando aplicável.
- Se a intimação já determinar contrarrazões ou providência objetiva com prazo, pode sugerir tarefa de minutar correspondente.
- Quando houver audiência, sempre informe tipo, data, horário, formato, local, link, ID e senha.
- Quando houver perícia, sempre informe tipo, data, horário e local.
- Audiência inicial não deve ser tratada automaticamente como UNA; confirme se é inicial, conciliação, instrução ou UNA.
- Para audiência cível em que o cliente seja réu/reclamado, alerte que é necessário verificar se já existe contestação no VIOS/PJe. Se não houver, indicar também `MINUTAR CONTESTAÇÃO`.

## Saída padrão preferencial para arquivos do VIOS

Sempre que o usuário encaminhar arquivo ou planilha do VIOS com intimações recebidas, use este modelo de resposta para cada intimação. Este é o padrão preferido do usuário.

### Organização visual obrigatória

- Apresentar **uma CI por bloco**, em sua ordem original, com título numerado `## [n]. CI [número] — Processo [número]` e linha em branco antes do bloco seguinte. Nunca juntar duas CIs no mesmo parágrafo ou cabeçalho, mesmo quando as providências forem iguais ou uma CI for duplicada.
- Separar os campos `Cliente`, `Do que se trata`, `Tarefa no VIOS`, `Tarefa complementar`, `Prazo fatal`, `PRAZO FATAL (D-2)`, `Cabe recurso?`, `Resumo para tarefa` e `Observação` em **linhas ou parágrafos distintos**. Deixar uma linha em branco entre a explicação do ato, o conjunto de tarefas, os prazos e o resumo. Nunca enviar campos colados ou tudo em uma linha.
- Quando houver mais de uma tarefa, numerar **cada tarefa separadamente**, com nome exato, finalidade, data própria e resumo pronto para lançamento. Não combinar descrições de tarefas diferentes em um único resumo. Se uma data ou providência depender de confirmação, escrever a pendência junto daquela tarefa.
- Se várias CIs exigirem tarefas iguais, repetir os dados próprios de cada CI ou usar blocos individuais com referência inequívoca; não misturar clientes, processos, IDs, datas ou prazos. Uma duplicada conserva seu próprio cabeçalho e informa qual CI tem a tarefa a aproveitar.
- Priorizar frases curtas, espaços e quebras de linha que permitam copiar cada tarefa para o VIOS sem reconstruir os dados. Antes de responder, conferir visualmente a separação entre CIs e entre tarefas da mesma CI.

```text
## CI [número] — Processo [número do processo]
**Cliente:** [cliente da 4ª ou 5ª coluna da planilha, conferido pelo teor]

**Do que se trata:**
[explicação objetiva da intimação]

**Tarefa no VIOS:**
[nome exato da tarefa sugerida]

**Cabe recurso?**
[informar se cabe ou não. Quando couber, indicar qual recurso ou se depende de análise do advogado]

**PRAZO PARA EMBARGOS: DD/MM/AAAA**
**PRAZO PARA RECURSO: DD/MM/AAAA**

**Resumo para tarefa:**
PRAZO FATAL (D-2): [DD/MM/AAAA ou PENDENTE – NÃO CONSTA NO DOCUMENTO, somente quando houver prazo]
[resumo pequeno, simples e direto, para o advogado entender o teor da intimação]
```

Regras deste modelo:

- A tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` fica para o **mesmo dia** da análise, nunca para o D-2: as datas de embargos e de recurso (em D-2) ficam só na descrição. Não usar a linha `PRAZO FATAL (D-2)` quando houver as linhas de embargos e recurso.
- Se couber, ou puder caber, embargos ou recurso, exibir as duas linhas `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:`, nesta ordem, **sempre com data em D-2**. Se a intimação não informar o prazo, usar o prazo previsto em lei. Mesmo com cabimento pendente (ex.: recurso imediato a confirmar), indicar a data: o advogado decide se recorre e precisa dela.
- Na linha do meio que não couber, preencher `NÃO CABE`.
- Se não couber embargos nem recurso, não exibir essas duas linhas: deixar somente o `PRAZO FATAL (D-2)` do ato, se houver.
- Para tarefas diferentes de análise, usar as linhas somente quando efetivamente couberem.
- As datas exibidas nas linhas de prazo devem ser em D-2 do prazo fatal, quando a finalidade for lançamento da tarefa no VIOS.
- Exibir a data operacional sempre com o rótulo exato `PRAZO FATAL (D-2):`. Nunca usar `Prazo interno VIOS`, `Prazo interno` ou outra variação como título desse campo.
- No `Resumo para tarefa`, inserir somente `PRAZO FATAL (D-2): DD/MM/AAAA`, pois essa é a data lançada na tarefa do VIOS. Não inserir ali o prazo jurídico fatal real.
- Quando necessário, mencionar fora do resumo que a contagem depende de feriados locais.
- No Previdenciário, use embargos em 5 dias.
- No Previdenciário de Juizado, use recurso em 10 dias.
- No Previdenciário de Justiça Comum, use recurso em 15 dias.
- Para sentença, decisão ou acórdão, priorize `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` conforme a área.
- Para toda perícia social previdenciária, indicar aviso e instrução na mesma data operacional; se solicitar dados/documentos, indicar também a minuta para Tamira. Aplicar a regra obrigatória de instrução acima.
- Use linguagem direta da Controladoria Jurídica, sem explicações longas.

## Saída padrão completa

Use esta estrutura quando o usuário pedir relatório detalhado ou quando houver necessidade de registrar mais campos:

```text
Área responsável:
Setor responsável:
Responsável/Auxiliar:
Cliente/Parte representada:
Posição processual do cliente:
Tipo de documento:
Tarefa VIOS sugerida:
Tarefa complementar:
Prazo fatal:
PRAZO FATAL (D-2):
Cabe recurso/embargos:
Prazo para embargos:
Prazo para recurso:
Descrição sugerida para o VIOS:
Providência imediata:
Resumo simples da intimação:
Observação:
Pendências:
```

Se o usuário pedir uma resposta mais curta, mantenha pelo menos:

```text
Área responsável:
Setor responsável:
Responsável/Auxiliar:
Tarefa VIOS sugerida:
PRAZO FATAL (D-2):
Providência imediata:
Observação:
```

## Modelos de descrição

Use o modelo da tarefa VIOS em seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo).

Para sentença, decisão ou acórdão, use:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA
SENTENÇA/DECISÃO/ACÓRDÃO
[inserir o dispositivo ou a parte principal da intimação]
```

Quando preencher descrição de tarefa, use a data interna em D-2 quando a regra operacional pedir prazo de trabalho. Se for responder sobre prazo jurídico fatal, mostre também a data fatal em campo separado.

## Tarefas complementares obrigatórias

Consulte seção "Referência — POP e Fluxo de Intimações" (mais abaixo) para detalhes. Regras de maior atenção:

- Sustentação oral: indicar `VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL` e também `SUSTENTAÇÃO ORAL`.
- Pagamento ou depósito devido pelo cliente no Cível: indicar análise, `ENTRAR EM CONTATO COM O CLIENTE 2026` e `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026` para comprovação nos autos.
- Avaliação social: indicar aviso e `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` na mesma data operacional. Na ausência de orientação específica, lançar ambas para o dia seguinte. Se houver pedido de dados/documentos, indicar também minuta para Tamira no mesmo dia da análise.
- Pagamento, custas, honorários, preparo ou depósito no Trabalhista: indicar primeiro tarefa de análise. Não sugerir geração de guia nem minuta inicial; o contato com o cliente deve ocorrer antes de qualquer emissão.

## Regra obrigatória — marcar Breno nas tarefas de petição da Execução

- Sempre que indicar a tarefa `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)` ou qualquer opção equivalente do VIOS denominada `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)`, **Breno** é marcado como responsável da tarefa (junto com a Tamira).
- Não escrever na descrição da tarefa `Responsável a marcar na tarefa: BRENO`, `Advogada auxiliar: TAMIRA` nem `PRIORIDADE RPV/PRECATÓRIO`: o responsável vai no campo Responsáveis do VIOS. A descrição começa pelo `PRAZO FATAL:` e segue com a providência e o trecho da intimação.
- Aplicar a regra a todas as tarefas com esse nome, independentemente do conteúdo da petição, inclusive dados bancários, RPV/precatório, alvará, juntada de documentos e demais manifestações da Execução.
- Não aplicar automaticamente a outras tarefas de Execução que possuam nome diferente.

## Exceções obrigatórias à data D-2

Aplicar seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo):

- Toda tarefa relacionada a RPV/precatório deve ser lançada para o dia útil seguinte à publicação ou recebimento, mantendo o prazo jurídico fatal separado.
- Sempre que o auxiliar for `SUH`/Suhiane e a tarefa for de minutar emenda à inicial, lançar a tarefa para o primeiro dia útil seguinte à publicação ou ao recebimento. Aplicar esta regra tanto a `MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026` quanto a `MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026` e a qualquer opção equivalente sob responsabilidade da Suhiane.
- A prioridade de emenda da Suhiane prevalece sobre D-2. Manter o prazo jurídico fatal separado e não aplicar nem exibir `PRAZO FATAL (D-2)` como data operacional dessa tarefa.
- Nessas hipóteses, não rotular a data prioritária como `PRAZO FATAL (D-2)`. Usar apenas `PRAZO FATAL: DD/MM/AAAA` (sem D-2), em negrito e vermelho na descrição da tarefa.

Para emenda trabalhista ou previdenciária da Suhiane, usar obrigatoriamente:

```text
PRAZO FATAL: DD/MM/AAAA
```

## Regra obrigatória — tarefas com horário

Toda tarefa que tem horário (sustentação oral, audiência, perícia) fica na **data exata** em que o ato vai ocorrer, nunca no D-2, e o horário vai no campo Horário da tarefa no VIOS.

## Regra obrigatória — intimação que só indica o evento

Quando a intimação apenas indicar um evento do processo, sem o teor (ex.: "Ato ordinatório. O ato refere-se ao seguinte evento: Evento 23 - PETIÇÃO"), não gerar tarefa por suposição (nem `CIÊNCIA`): a tarefa só pode ser definida abrindo o sistema e verificando o evento (pode ser, por exemplo, `MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES`). A CI não é lançada: indicar que falta conferir o teor do evento.

## Regra obrigatória — não lançar quando faltar informação

Se a tarefa exigir informação que não está na intimação e só pode ser obtida no PJe (ex.: audiência sem tipo, data, horário, formato, local ou link/ID/senha; perícia sem data, horário ou local), a CI **não é lançada** no VIOS: listar o que falta para a Controladoria conferir no PJe e lançar manualmente.

Também não lançar quando a área da tarefa divergir do auxiliar responsável (ver seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo)): tarefa de Execução com auxiliar que não é a Tamira, ou tarefa de outra área com a Tamira como única responsável.

## Perguntas ao usuário

Pergunte somente depois de ler o documento. Faça perguntas objetivas quando:

- não houver documento ou texto de intimação;
- não for possível identificar o cliente;
- não houver data de publicação/intimação necessária para calcular prazo;
- a tarefa VIOS depender de opção não existente nas referências;
- a área ou posição processual for ambígua.

Não pergunte qual modelo usar quando a referência operacional indicar a tarefa.

## Regra obrigatória de prazos — não finalizar sem conferir

Para TODA intimação analisada, verificar se existe:
- prazo expresso no texto da intimação;
- prazo legal mencionado, mesmo sem número de dias;
- prazo de manifestação;
- prazo para emenda;
- prazo para depósito, guia, preparo ou recolhimento;
- prazo para contrarrazões;
- prazo para manifestação sobre laudo;
- prazo para produção de provas;
- prazo para pagamento em cumprimento de sentença;
- prazo de recurso ou embargos.

Sempre que houver qualquer prazo, informar:
**Prazo fatal:** DD/MM/AAAA ou PENDENTE – NÃO CONSTA NO DOCUMENTO.
**PRAZO FATAL (D-2):** DD/MM/AAAA ou PENDENTE – NÃO CONSTA NO DOCUMENTO.

Nunca omitir prazo apenas porque não cabe recurso.
As linhas “PRAZO PARA EMBARGOS” e “PRAZO PARA RECURSO” são específicas para recurso/embargos, mas prazos de manifestação, emenda, depósito, laudo, prova, contrarrazões e pagamento também devem aparecer no campo `PRAZO FATAL (D-2)`.

## Checklist obrigatório antes de responder

- sentença que encerra o processo/fase ou homologa acordo envolvendo o cliente gera ANALISAR, mesmo favorável; conferir possíveis erros na homologação e registrar o contato com o cliente no resumo; se a tarefa for CIÊNCIA, corrigir antes de finalizar;

Antes de enviar a resposta final, montar internamente uma conferência com uma linha por CI:

CI | Cliente | Ato | Existe prazo no texto? | Prazo fatal | PRAZO FATAL (D-2) | Tarefa VIOS | Recurso/embargos | Pendência

Acrescentar à conferência: Natureza | Fase | Departamento | Auxiliar | Destinatário da ordem | Data da tarefa | Motivo da data | RPV? | Emenda Suhiane? | Marcar Breno? | Duplicada de qual CI?

Se qualquer CI tiver “Existe prazo no texto? SIM” e o campo `PRAZO FATAL (D-2)` estiver vazio, NÃO responder ainda, salvo RPV/precatório ou emenda à inicial da Suhiane, que devem usar o rótulo de prioridade correspondente.
Calcular o prazo ou marcar expressamente:
PENDENTE – NÃO CONSTA NO DOCUMENTO.

Se `Auxiliar = SUH` e a tarefa for qualquer `MINUTAR EMENDA À INICIAL`, não finalizar até confirmar cumulativamente:

- a regra foi aplicada tanto para tarefa Trabalhista quanto Previdenciária;
- a data da tarefa corresponde ao primeiro dia útil seguinte à publicação ou ao recebimento;
- o prazo jurídico fatal foi preservado separadamente;
- não foi aplicado D-2;
- foi usado o rótulo `PRAZO FATAL: DD/MM/AAAA` (data do dia útil seguinte).

**Tarefa no VIOS:**
[nome exato da tarefa]

**Prazo fatal:** [data ou PENDENTE]
**PRAZO FATAL (D-2):** [data D-2 ou PENDENTE]

**Cabe recurso?**
[sim/não/depende de análise]

[PRAZO PARA EMBARGOS: data em D-2 / NÃO CABE; com cabimento pendente, data pelo prazo legal; se não couber embargos nem recurso, omitir as duas linhas e deixar só o PRAZO FATAL (D-2)]
[PRAZO PARA RECURSO: data em D-2 / NÃO CABE; com cabimento pendente, data pelo prazo legal; se não couber embargos nem recurso, omitir as duas linhas e deixar só o PRAZO FATAL (D-2)]


## Regra obrigatória — perícia médica previdenciária

Sempre que a intimação gerar a tarefa:
`PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`

indicar também, obrigatoriamente, a tarefa:
`MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026`

Finalidade da tarefa complementar:
apresentar quesitos e indicar assistente técnico.

Não substituir uma tarefa pela outra. Devem ser indicadas as duas:
1. `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`
2. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026`

Para a tarefa de minutar, informar:
**Prazo fatal:** prazo indicado na intimação para quesitos/assistente técnico, ou `PENDENTE – NÃO CONSTA NO DOCUMENTO`.
**PRAZO FATAL (D-2):** D-2 do prazo fatal, ou `PENDENTE – NÃO CONSTA NO DOCUMENTO`.

Se a intimação apenas disser que a perícia foi designada, mas não trouxer prazo para quesitos e indicação de assistente técnico, ainda assim indicar a tarefa complementar e marcar a pendência do prazo.


Nunca esqueça nenhuma dessas regras e padrões: 

FLUXO DE INTIMAÇÕES

Antes de tudo você precisa entender que eu recebo as intimações do DJEN no VIOS e a partir delas lanço tarefas no VIOS para que os advogados saibam da intimação e como agir. 


## Regras obrigatórias para análise de intimações do VIOS

Sempre que o usuário encaminhar arquivo do VIOS com intimações, analisar todas as CIs, sem pular nenhuma, e responder nome por nome, enumerando. Só agrupar intimações quando forem exatamente a mesma providência e não houver observação individual relevante.

O cliente normalmente aparecerá na quarta ou quinta coluna da planilha de intimações. Conferir pelo teor da intimação sempre que possível.

Para cada intimação, informar obrigatoriamente:
- do que se trata;
- qual tarefa abrir no VIOS;
- se há tarefa complementar;
- se cabe recurso ou embargos;
- prazo fatal, quando houver;
- `PRAZO FATAL (D-2)` quando houver;
- resumo pequeno e simples do teor da intimação.

## Modelo obrigatório de resposta

Usar este padrão para cada CI:

[n]. CI [número] — Processo [número]

Cliente:
[nome do cliente]

Do que se trata:
[explicação objetiva da intimação]

Tarefa no VIOS:
[nome exato da tarefa principal]

Tarefa complementar:
[nome da tarefa complementar, se houver, ou "Não há"]

Prazo fatal:
[data ou PENDENTE – NÃO CONSTA NO DOCUMENTO]

PRAZO FATAL (D-2):
[data em D-2 ou PENDENTE – NÃO CONSTA NO DOCUMENTO]

Cabe recurso?
[Não / Cabe análise do advogado / Sim, indicar qual recurso]

PRAZO PARA EMBARGOS: [data em D-2 / NÃO CABE; com cabimento pendente, data pelo prazo legal; se não couber embargos nem recurso, omitir as duas linhas e deixar só o PRAZO FATAL (D-2)]
PRAZO PARA RECURSO: [data em D-2 / NÃO CABE; com cabimento pendente, data pelo prazo legal; se não couber embargos nem recurso, omitir as duas linhas e deixar só o PRAZO FATAL (D-2)]

Resumo para tarefa:
PRAZO FATAL (D-2): [DD/MM/AAAA ou PENDENTE – NÃO CONSTA NO DOCUMENTO, somente quando houver prazo]
[resumo curto e simples para o advogado entender o teor da intimação]

Observação:
[observações obrigatórias, pendências, audiência, perícia, divergência de cliente, tarefa complementar etc.]

## Regra obrigatória de prazos

Nunca omitir prazo quando houver qualquer prazo no texto da intimação.

Verificar se existe:
- prazo para manifestação;
- prazo para emenda;
- prazo para depósito;
- prazo para guia, preparo ou recolhimento;
- prazo para contrarrazões;
- prazo para manifestação sobre laudo;
- prazo para quesitos e indicação de assistente técnico;
- prazo para produção de provas;
- prazo para pagamento em cumprimento de sentença;
- prazo para recurso;
- prazo para embargos.

Sempre informar:
- Prazo fatal;
- `PRAZO FATAL (D-2)`.

Se a intimação não informar o número de dias, usar o prazo previsto em lei (tabela em seção "Referência — Regras de Prazos e Recursos" (mais abaixo), seção "Prazo previsto em lei") e escrever na descrição da tarefa: `Prazo previsto em lei: N dias úteis ([meio]).`

Só se o caso não estiver na tabela e não houver dados suficientes para calcular, colocar:
PENDENTE – NÃO CONSTA NO DOCUMENTO.

No Previdenciário:
- embargos: 5 dias;
- recurso em Juizado: 10 dias;
- recurso na Justiça Comum: 15 dias.

Quando couber embargos, usar:
PRAZO PARA EMBARGOS: DD/MM/AAAA

Quando couber recurso, usar:
PRAZO PARA RECURSO: DD/MM/AAAA

Se couberem os dois, usar:
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA

As datas de embargos e recurso devem ser sempre em D-2.

Quando a tarefa for `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` e couber (ou puder caber) embargos ou recurso, exibir as duas linhas, sempre com data em D-2 — pelo prazo legal quando a intimação não informar, inclusive com cabimento pendente. Na linha do meio que não couber, `NÃO CABE`. Se não couber nenhum dos dois, omitir as duas linhas e deixar somente o `PRAZO FATAL (D-2)` do ato, se houver. A tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` fica para o **mesmo dia** da análise, nunca para o D-2: as datas de embargos e de recurso (em D-2) ficam só na descrição. Não usar a linha `PRAZO FATAL (D-2)` quando houver as linhas de embargos e recurso.

## Sustentação oral

Sempre que a tarefa for:
VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL

indicar também a tarefa:
SUSTENTAÇÃO ORAL

A tarefa de verificar viabilidade deve ficar para o mesmo dia.
A tarefa de sustentação oral deve ficar para o dia da sustentação (na sessão virtual, o primeiro dia da sessão), nunca no D-2 nem no prazo de envio da sustentação gravada.

A tarefa SUSTENTAÇÃO ORAL deve vir neste padrão:

SUSTENTAÇÃO ORAL
DATA:
HORA:
LINK:

Exemplo de sessão virtual (início às 09:00 de 06/11/2026 e término às 09:00 de 13/11/2026):

SUSTENTAÇÃO ORAL
DATA: De 06/11/2026 a 13/11/2026.
HORA: até 09:00
LINK: https://pje-plenario-virtual.tjce.jus.br/

Se faltar data, hora ou link, preencher com:
PENDENTE – NÃO CONSTA NO DOCUMENTO.

## Laudos e proposta de acordo do INSS

Sempre que a intimação for para manifestação sobre laudo previdenciário ou manifestação sobre proposta de acordo do INSS, a tarefa correta é:

MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026

Informar `Prazo fatal:` e `PRAZO FATAL (D-2):`.

## Perícia médica previdenciária

Sempre que a intimação gerar a tarefa:

PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026

indicar também, obrigatoriamente, a tarefa:

MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026

Finalidade da tarefa complementar:
apresentar quesitos e indicar assistente técnico.

Não substituir uma tarefa pela outra. Indicar as duas:
1. PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026
2. MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026

Para a tarefa complementar, informar:
Prazo fatal: prazo para quesitos/assistente técnico ou PENDENTE – NÃO CONSTA NO DOCUMENTO.
PRAZO FATAL (D-2): D-2 ou PENDENTE – NÃO CONSTA NO DOCUMENTO.

Se a intimação apenas informar que a perícia foi designada, mas não trouxer prazo para quesitos e indicação de assistente técnico, ainda assim indicar a tarefa complementar e marcar a pendência do prazo.

## Audiência

Sempre que houver audiência, a descrição da tarefa segue exatamente este padrão, uma informação por linha, sem parágrafos ou observações a mais:

AUDIÊNCIA [TIPO]
DATA:
HORA:
FORMATO:
LINK/LOCAL:
ID da reunião:
SENHA:

- `LINK/LOCAL`: só o link (audiência virtual) ou o endereço (presencial). ID da reunião e senha vão nas linhas próprias, não junto do link.
- `ID da reunião` e `SENHA` só na audiência virtual/telepresencial; na presencial, omitir as duas linhas.
- Não acrescentar na descrição explicações sobre a audiência (depoimentos, testemunhas, consequência da ausência etc.) nem `OBS:`. O que a Controladoria precisar saber vai nas observações da análise, fora da tarefa.

Exemplo:

AUDIÊNCIA UNA
DATA: 22/01/2027
HORA: 08:20
FORMATO: TELEPRESENCIAL (ZOOM)
LINK/LOCAL: https://trt7-jus-br.zoom.us/j/85164513045
ID da reunião: 851 6451 3045
SENHA: 355957

Quando a audiência for inicial, não indicar automaticamente como UNA, pois pode ser audiência de instrução ou conciliação. Identificar corretamente o tipo pelo teor da intimação. Se não constar, marcar como pendente.

Quando houver audiência cível em que o cliente seja parte ré/reclamada, indicar essa observação, pois é necessário verificar no VIOS ou no PJe se já existe contestação. Se não houver contestação, indicar também a tarefa de MINUTAR CONTESTAÇÃO junto com a tarefa de audiência.

## Perícia em geral

Sempre que houver perícia, mandar no padrão:

TIPO:
DATA:
HORA:
LOCAL:
OBS: É necessário ter atenção ao tipo de perícia.

Se faltar data, hora ou local, preencher com:
PENDENTE – NÃO CONSTA NO DOCUMENTO.

## Avaliação social previdenciária

Aplicar a regra obrigatória de instrução de toda perícia social previdenciária acima e o fluxo de seção "Referência — POP e Fluxo de Intimações" (mais abaixo). Indicar sempre aviso e instrução na mesma data operacional, inclusive em publicação apenas informativa. Se houver pedido de dados/documentos, acrescentar minuta para Tamira no mesmo dia da análise.

Usar o aviso em negrito e sublinhado:

Aviso: Foi agendada perícia social relacionada ao processo. O(a) assistente social pode ir até a casa do cliente a qualquer momento para a realização da visita.

"[pequeno resumo do trecho principal da intimação, preferencialmente do trecho 'De ordem do MM...' até a menção ao prazo de 15 dias]"

## Sentença, decisão, despacho e acórdão

Sempre que houver decisão, despacho, sentença ou acórdão desfavorável ao cliente, a tarefa deve ser de ANÁLISE.

Mesmo quando a decisão parecer favorável, principalmente no Previdenciário e na Execução, preferir tarefa de ANÁLISE quando houver possibilidade de erro do juiz, necessidade de conferência ou providência posterior.

Abrir CIÊNCIA somente quando realmente não precisar de nenhuma movimentação, prazo, manifestação, recurso, conferência ou providência prática, respeitando a regra obrigatória de análise de sentença de encerramento e homologação de acordo.

Não abrir recurso ou embargos diretamente quando depender da análise do advogado. Nesses casos, abrir tarefa de análise e informar que cabe análise do advogado sobre recurso/embargos.

## Distribuição simples

Sempre que o teor for apenas distribuição simples, a tarefa é CIÊNCIA, usando a tarefa de ciência da área correspondente.

## Cálculos trabalhistas

O setor trabalhista não tem tarefa específica de manifestação sobre cálculos.

Quando houver manifestação sobre cálculos trabalhistas com prazo determinado, abrir:

MINUTAR PETIÇÃO INTERMEDIÁRIA DIVERSA (TRABALHISTA) 2026

Informar `Prazo fatal:` e `PRAZO FATAL (D-2):`.

## RPV e precatório

Quando uma decisão determinar expedição de RPV, abrir tarefa de ANÁLISE.

Quando os requisitórios já tiverem sido expedidos, abrir:

ANALISAR MINUTA PRECATÓRIO RPV

ou a tarefa equivalente disponível no VIOS.

## Tarefas de minutar

Tarefas de MINUTAR geralmente podem ser abertas pela Controladoria quando a intimação já diz exatamente o que deve ser feito e informa o prazo.

MINUTAR CONTESTAÇÃO normalmente pode ser aberta diretamente quando a intimação exigir defesa/contestação.

## Pagamento ou depósito judicial cível

Quando a intimação for CÍVEL e envolver depósito judicial, custas, honorários ou qualquer pagamento a ser feito pelo cliente, indicar as três tarefas desde logo:

ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026

e também:

ENTRAR EM CONTATO COM O CLIENTE 2026

e também:

MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026

Na descrição da minuta, informar que a finalidade é comprovar o pagamento, depósito ou recolhimento nos autos.

Essa regra vale para decisão interlocutória, cumprimento de sentença e qualquer ato que determine depósito ou pagamento pelo cliente.

## Parcelamento de custas no Cível

Quando a intimação informar parcelamento de custas ou outro valor devido pelo cliente, aplicar o mesmo fluxo cível: análise, contato com o cliente e minuta para comprovação. Não substituir a análise por `CIÊNCIA` nem indicar isoladamente tarefa de geração de guia.

Informar `Prazo fatal:` e `PRAZO FATAL (D-2):` se constarem na intimação.

## Checklist obrigatório antes de responder

- sentença que encerra o processo/fase ou homologa acordo envolvendo o cliente gera ANALISAR, mesmo favorável; conferir possíveis erros na homologação e registrar o contato com o cliente no resumo; se a tarefa for CIÊNCIA, corrigir antes de finalizar;

Antes de finalizar a resposta, conferir:

- todas as CIs da planilha foram analisadas;
- toda tarefa está na mesma área do departamento/auxiliar informado na planilha; se não estiver, há justificativa expressa na observação;
- toda tarefa `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)` tem Breno (e Tamira) como responsáveis, sem esse lembrete na descrição;
- cada CI tem cliente, processo, tarefa e resumo;
- se havia prazo no texto, o prazo fatal foi informado;
- se havia prazo no texto, o campo `PRAZO FATAL (D-2)` foi informado;
- se a tarefa for emenda à inicial da Suhiane, trabalhista ou previdenciária, foi usada a data do primeiro dia útil seguinte e o rótulo `PRAZO FATAL: DD/MM/AAAA` (data do dia útil seguinte), sem aplicação de D-2;
- se não foi possível calcular prazo, foi marcada pendência;
- toda audiência está no padrão com tipo, data, horário, formato e link/local;
- toda perícia está no padrão com tipo, data, hora e local;
- toda perícia médica previdenciária tem também tarefa complementar para quesitos e assistente técnico;
- toda perícia social previdenciária tem aviso e `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, com a mesma data operacional; havendo pedido de dados/documentos, também tem minuta para Tamira;
- toda sustentação oral tem duas tarefas;
- toda manifestação sobre laudo previdenciário usa a tarefa correta;
- toda sentença, decisão, despacho decisório ou acórdão foi analisado antes de indicar ciência;
- embargos e recurso só foram indicados quando couberem ou quando dependerem de análise do advogado;
- o cliente foi conferido pela quarta ou quinta coluna da planilha.

## Regra para intimações trabalhistas genéricas de recurso/agravo

Quando a intimação trabalhista mencionar de forma genérica que “as partes” foram intimadas para ciência da interposição de agravo de instrumento, recurso de revista, contraminuta e/ou contrarrazões, não indicar automaticamente tarefa de minuta.

Antes de abrir qualquer tarefa no VIOS, a Controladoria deve conferir no PJe quem interpôs o agravo/recurso.

Critério:

- Se o agravo/recurso foi interposto pela parte contrária ao nosso cliente, indicar:
`MINUTAR RECURSO/CONTRARRAZÕES AO RECURSO (TRABALHISTA) 2026`.

- Se o agravo/recurso foi interposto pelo nosso cliente, indicar:
`CIÊNCIA (TRABALHISTA) 2026`.

- Se houver recurso/agravo de ambas as partes, verificar se existe peça da parte contrária a ser respondida. Havendo, indicar minuta; não havendo, indicar ciência.

- Se a publicação não permitir identificar quem recorreu, responder:
`NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA`.

Não abrir tarefa para o advogado apenas conferir essa informação, pois a escolha entre minuta e ciência deve ser feita previamente pela Controladoria antes do lançamento no VIOS.

## Referência — POP e Fluxo de Intimações

Use esta seção para decidir a providência operacional quando a intimação vier do DJEN/VIOS.

### Finalidade

A Controladoria recebe intimações no VIOS e lança tarefas para que os advogados tenham ciência da intimação e saibam como agir.

### Fluxo visual resumido

- Sentença de encerramento, com ou sem resolução do mérito, e homologação de acordo envolvendo o cliente: sempre `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` da área, mesmo favorável ou integralmente cumprida. Aplicar a regra obrigatória da parte principal desta skill: conferir possíveis erros comparando acordo e sentença e dar sequência ao contato com o cliente. Não usar CIÊNCIA.

- Despacho do setor: normalmente gera `CIÊNCIA`, salvo quando houver providência específica.
- Sentença, decisão ou acórdão: avaliar se demanda análise. Se houver risco, desfavorabilidade, erro judicial possível ou necessidade de providência, abrir tarefa de análise.
- Depois da análise, o advogado define se não recorre, se opõe embargos ou se interpõe outro recurso.

### Regras operacionais

Antes de aplicar as regras abaixo, ler seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo). As prioridades de RPV/precatório, emenda da Suhiane, marcação do Breno, divergências de cadastro e duplicidades prevalecem sobre regras gerais incompatíveis.

Para a prioridade de emenda da Suhiane, considerar obrigatoriamente tanto `MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026` quanto `MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026`: lançar no primeiro dia útil seguinte, preservar o prazo fatal e não aplicar D-2.

#### Prevalência do cadastro interno

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
- A tarefa `SUSTENTAÇÃO ORAL` fica para o dia da sustentação (na sessão virtual, o primeiro dia da sessão), com o horário no campo Horário do VIOS. Tarefas com horário (sustentação, audiência, perícia) nunca vão para o D-2.
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

### Audiências

Quando houver audiência, informar no padrão:

```text
AUDIÊNCIA [TIPO]
DATA:
HORA:
FORMATO:
LINK/LOCAL:
ID da reunião:
SENHA:
```

Uma informação por linha, sem parágrafos ou `OBS:` a mais na descrição. `ID da reunião` e `SENHA` só na audiência virtual (na presencial, `LINK/LOCAL` é o endereço). Ver o padrão completo na seção "Audiência" da skill.

Identifique corretamente o tipo de audiência para que o advogado saiba como se preparar.

Se for audiência cível e o cliente estiver como parte ré/reclamada:

- indicar que se trata de audiência para parte reclamada/ré;
- orientar verificação no VIOS/PJe se já existe contestação;
- se não houver contestação, indicar também tarefa de `MINUTAR CONTESTAÇÃO`.

### Perícias

Quando houver perícia, informar no padrão:

```text
TIPO:
DATA:
HORA:
LOCAL:
```

É necessário identificar o tipo de perícia, como médica, técnica ou avaliação social.

### Avaliação social previdenciária

Em toda perícia social previdenciária, indicar:

1. `AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para Leticya;
2. `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para a **mesma data operacional do aviso/perícia social no VIOS**.

Aplicar também quando a tarefa principal se chamar `PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` ou equivalente. Não confundir a data operacional da instrução com a data da visita. Na ausência de orientação específica do usuário, lançar aviso e instrução para o dia seguinte. Confirmar o responsável pela instrução no fluxo/cadastro do VIOS, sem presumir o mesmo do aviso.

Se houver pedido de documentação, endereço, telefone ou dados similares, indicar também minuta para Tamira no mesmo dia da análise, preservando o prazo jurídico. A minuta não dispensa aviso nem instrução.

Se a intimação apenas informar que haverá visita, indicar aviso e instrução, sem minuta. A falta de data/horário da visita não dispensa a instrução.

Apresentar cada tarefa separadamente e conferir que cada processo com perícia social tenha sua tarefa de instrução. Usar o modelo de instrução de seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo).

Modelo da tarefa:

```text
Aviso: Foi agendada perícia social relacionada ao processo. O(a) assistente social pode ir até a casa do cliente a qualquer momento para a realização da visita.

"[inserir pequeno resumo do trecho principal da intimação, preferencialmente do trecho De ordem do MM... até a menção ao prazo de 15 dias]"
```

### RPV, precatório e requisição

- Decisão que determina expedição de RPV: abrir tarefa de análise.
- Quando os requisitórios já foram expedidos: usar `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`.
- Em qualquer etapa relacionada a RPV/precatório, lançar a tarefa para o dia útil seguinte à publicação ou recebimento, preservando o prazo jurídico fatal em campo separado, conforme seção "Referência — Roteamento interno, prioridades e validação" (mais abaixo).

### Minutas diretas

Tarefas de minutar podem ser abertas pela Controladoria quando a intimação já diz exatamente o que deve ser feito e indica prazo.

`MINUTAR CONTESTAÇÃO` costuma ser aberto diretamente quando a intimação indicar necessidade de defesa e houver elementos suficientes.

### Responsável pelas petições da Execução

- Sempre que a tarefa for `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)` ou a opção equivalente disponível no VIOS, marcar Breno como responsável da tarefa (sem escrever o lembrete na descrição).
- Aplicar essa regra em todas as petições com esse nome, inclusive apresentação de dados bancários, providências relacionadas a RPV/precatório, alvarás, documentos e outras manifestações da Execução.

### Pagamento pelo cliente — Trabalhista

Quando a intimação trabalhista determinar pagamento, depósito judicial, honorários periciais, custas, preparo, depósito recursal ou outro valor pelo cliente:

- indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou a opção equivalente de análise aplicável ao ato;
- registrar no resumo a natureza do pagamento e o prazo;
- não sugerir tarefa de gerar guia nesse momento;
- não indicar `CIÊNCIA` no lugar da análise;
- não indicar minuta como tarefa complementar inicial.

A análise deve ocorrer antes porque ela gera o fluxo de contato com o cliente. Primeiro, avisar o cliente e perguntar se deseja pagar; somente depois da manifestação favorável do cliente o setor trabalhista providencia a guia, quando autorizada. Após o pagamento, abrir a tarefa necessária para comprová-lo nos autos.

### Pagamento pelo cliente — Cível

Quando a intimação cível determinar pagamento, depósito judicial, custas, honorários ou outro valor pelo cliente, indicar desde logo:

- tarefa de análise cível aplicável ao ato;
- `ENTRAR EM CONTATO COM O CLIENTE 2026`;
- `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026`, para comprovar o pagamento, depósito ou recolhimento nos autos.

Indicar as três tarefas imediatamente. Não aguardar o resultado da análise ou do contato para sugerir a minuta. Não substituir esse fluxo por `CIÊNCIA` ou por tarefa isolada de geração de guia. Aplicar também a parcelamento de custas, decisão interlocutória, cumprimento de sentença e outros atos que imponham pagamento ao cliente.

### Resultado esperado da análise

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

Exceção obrigatória: na tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, se couber (ou puder caber) embargos ou recurso, exibir as duas linhas com data em D-2 (prazo legal quando a intimação não informar, inclusive com cabimento pendente); o meio que não couber fica `NÃO CABE`. Se não couber nenhum, deixar somente o `PRAZO FATAL (D-2)` do ato, se houver. A tarefa de análise fica para o mesmo dia da análise.

## Referência — Roteamento interno, prioridades e validação

### Ordem obrigatória de decisão

Analisar separadamente natureza jurídica, fase processual, departamento interno, auxiliar cadastrado e providência concreta. Definir a tarefa nesta ordem:

1. correção ou orientação expressa do usuário;
2. providência concreta determinada na intimação;
3. fase processual atual;
4. departamento interno responsável pela providência;
5. advogado auxiliar informado na planilha;
6. natureza jurídica, órgão e número CNJ;
7. classe e assunto processual.

Não classificar somente pelo número CNJ, classe, fase ou auxiliar. Um processo trabalhista ou previdenciário pode estar no Departamento de Execução. A presença de `execução`, `penhora`, `alvará` ou `cumprimento de sentença` não basta para classificar o departamento.

### Mapeamento operacional

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

### Divergências de cadastro

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

### Prioridade de RPV e precatório

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

#### Etapas do requisitório

| Situação | Tarefa |
| --- | --- |
| Decisão determinando futura expedição | Analisar sentença/acórdão/decisão da área. |
| Cálculos, documentos ou dados bancários necessários | Minutar petição da área. |
| Minuta já expedida | `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`. |
| Alvará expedido sem providência | Ciência da área. |
| Erro ou pendência no requisitório | Analisar minuta ou decisão, conforme o ato. |

### Prioridade de emenda da Suhiane

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

### Petição de Execução da Tamira e Breno

Quando a tarefa for `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)` ou equivalente e pertencer à Tamira, Tamira e Breno são os responsáveis da tarefa no VIOS. Não escrever `Advogada auxiliar: TAMIRA` nem `Responsável a marcar na tarefa: BRENO` na descrição da tarefa.

Aplicar a dados bancários, documentos, alvará, RPV/precatório, cálculos, prosseguimento, bloqueio, penhora e demais petições intermediárias da Execução. Não substituir Tamira por Breno.

### Analisar ou minutar

- Antes das regras gerais, aplicar a regra da parte principal desta skill para sentença de encerramento ou homologação de acordo envolvendo o cliente: sempre ANALISAR da área responsável, mesmo favorável; conferir erros na homologação e registrar a necessidade de contato com o cliente. Não usar CIÊNCIA nem decidir apenas pela existência de providência objetiva.

- Se a intimação determinar objetivamente o que fazer e trouxer prazo, indicar diretamente a tarefa de minutar disponível para a área.
- Se exigir avaliação de resultado, erro, recurso ou estratégia, indicar analisar.
- O título decisão, despacho ou sentença não define sozinho a tarefa.
- Se a ordem for dirigida à parte contrária, não abrir minuta para o cliente.
- Aplicar as tarefas complementares de pagamento, depósito ou contato quando previstas.

### Duplicidades

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

### Modelo com data operacional

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

### Bloqueios antes da resposta

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

## Referência — Tarefas VIOS e Modelos de Descrição

Use esta lista para escolher a tarefa VIOS e montar a descrição. Preserve o nome da tarefa quando possível.

Em qualquer modelo abaixo, substituir o rótulo genérico `PRAZO FATAL:` pelo rótulo operacional `PRAZO FATAL (D-2):` e preencher com a data D-2. O prazo jurídico fatal real deve aparecer apenas no campo externo `Prazo fatal:`, nunca dentro do resumo da tarefa.

### Trabalhista

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (TRABALHISTA) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR RECURSO/CONTRARRAZÕES AO RECURSO (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR RÉPLICA À CONTESTAÇÃO (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR RÉPLICA |
| MINUTAR PETIÇÃO INTERMEDIÁRIA DIVERSA (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR PETIÇÃO |
| MINUTAR QUESITOS/INDICAR PERITOS (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR QUESITOS |
| MINUTAR PETIÇÃO SOBRE O LAUDO PERICIAL (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AO LAUDO PERICIAL |
| MINUTAR MEMORIAIS/RAZÃO FINAIS/ALEGAÇÕES FINAIS (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR ALEGAÇÕES FINAIS |
| MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR EMENDA |
| AUDIÊNCIA DE CONCILIAÇÃO (TRABALHISTA) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026 | AUDIÊNCIA UNA ou AUDIÊNCIA DE INSTRUÇÃO (conforme o teor)<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| PERÍCIA TÉCNICA/MÉDICA (TRABALHISTA) 2026 | PERÍCIA TÉCNICA/MÉDICA (TRABALHISTA)<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (TRABALHISTA) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

### Previdenciário

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (PREVIDENCIÁRIO) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (PREVIDENCIÁRIO) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (PREVIDENCIÁRIO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AO LAUDO PERICIAL |
| MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR EMENDA |
| AUDIÊNCIA PREVIDENCIÁRIA (PREVIDENCIÁRIO) 2026 | AUDIÊNCIA DE INSTRUÇÃO<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026 | PERÍCIA MÉDICA<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (PREVIDENCIÁRIO) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026 | Abrir para o dia seguinte, salvo data expressa do usuário. Usar o aviso padrão do POP e indicar obrigatoriamente a tarefa de instrução para a mesma data operacional. |
| INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026 | DATA DA TAREFA: mesma data operacional da tarefa de perícia social/aviso no VIOS.<br>Realizar instrução do(a) cliente para a perícia social. Explicar como ocorre a avaliação e orientar a apresentação de informações verdadeiras sobre a realidade familiar, condições de vida e, quando pertinente, atividade de trabalho. Confirmar dados de localização, conferir eventual data, horário e local nos autos e registrar a orientação realizada. |
| SUSTENTAÇÃO ORAL PPREVIDENCIÁRIO) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

### Execução

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (EXECUÇÃO) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| MINUTAR EXECUÇÃO DE SENTENÇA (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CUMPRIMENTO DE SENTENÇA |
| MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026) | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR [indicar petição, ex.: dados bancários] |
| MINUTAR EMBARGOS À EXECUÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR EMBARGOS |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR HOMOLOGAÇÃO/IMPUGNAÇÃO AOS CÁLCULOS (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AOS CÁLCULOS |
| MINUTAR RESPOSTA À IMPUGNAÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR RESPOSTA |
| MINUTAR CHAMAMENTO DO FEITO À ORDEM (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CHAMAMENTO FEITO À ORDEM |
| CIÊNCIA (EXECUÇÃO) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR PETIÇÃO EXECUÇÃO 2026 (MINUTAR PETIÇÃO (EXECUÇÃO) 2026) | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR PETIÇÃO [inserir a parte principal da intimação] |
| AUDIÊNCIA DE CONCILIAÇÃO (EXECUÇÃO) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>[inserir informação importante da intimação] |
| MINUTAR PETIÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR PETIÇÃO [informar qual petição e destacar a parte principal da intimação] |

### Cível

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (CÍVEL) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR RECURSO/CONTRARRAZÕES (CÍVEL) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES<br>Observação: recursos são na tarefa de analisar. |
| MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES (CÍVEL) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES<br>Observação: recursos são na tarefa de analisar. |
| MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR PETIÇÃO [informar qual petição e destacar a parte principal da intimação] |
| MINUTAR MEMORIAIS/RAZÃO FINAIS/ALEGAÇÕES FINAIS (CÍVEL) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR ALEGAÇÕES FINAIS |
| AUDIÊNCIA DE CONCILIAÇÃO (CÍVEL) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026 | AUDIÊNCIA UNA ou AUDIÊNCIA DE INSTRUÇÃO (conforme o teor)<br>DATA:<br>HORA:<br>FORMATO:<br>LINK/LOCAL:<br>ID da reunião: (só virtual)<br>SENHA: (só virtual) |
| PERÍCIA TÉCNICA (CÍVEL) 2026 | PERÍCIA TÉCNICA<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (CÍVEL) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| MINUTAR INICIAL/CONTESTAÇÃO/EMBARGOS À EXECUÇÃO (CÍVEL) 2026 | PRAZO FATAL: DD/MM/AAAA<br>MINUTAR CONTESTAÇÃO |
| SUSTENTAÇÃO ORAL(CÍVEL) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

### Gerais e complementares

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| SUSTENTAÇÃO ORAL | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| SUSTENTACÃO ORAL (RECLAMANTE) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| ENTRAR EM CONTATO COM O CLIENTE 2026 | No Cível, abrir quando houver pagamento, depósito, custas, honorários ou outro valor a cargo do cliente, junto da análise e da minuta para comprovação nos autos. No Trabalhista, não indicar manualmente como tarefa complementar inicial: abrir primeiro a análise, que gera o fluxo de contato. |

### Fluxo de pagamento por área

- Trabalhista: indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou análise equivalente. Não indicar geração de guia nem minuta no primeiro momento.
- Cível: indicar análise, `ENTRAR EM CONTATO COM O CLIENTE 2026` e `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026` desde logo. Usar na minuta: `PRAZO FATAL (D-2): DD/MM/AAAA` e `MINUTAR PETIÇÃO PARA COMPROVAR [PAGAMENTO/DEPÓSITO/RECOLHIMENTO] NOS AUTOS`.

### Pendências de saneamento

Alguns nomes na planilha original possuem grafia possivelmente inconsistente, como `PPREVIDENCIÁRIO`, `EXECUCÃO`, `SUSTENTACÃO` e `PRECATORIO`. Preserve o nome se for exatamente a opção disponível no VIOS. Se houver dúvida, informe `PENDENTE – CONFIRMAR OPÇÕES DISPONÍVEIS NO VIOS.`

## Referência — Regras de Prazos e Recursos

Use esta seção para orientar cálculo de prazo e indicação de cabimento. Se o documento ou manual da Controladoria trouxer regra mais específica, use a regra específica.

### Regra operacional

- Sempre que houver prazo fatal calculável, indicar a data operacional em D-2 com o rótulo exato `PRAZO FATAL (D-2):`.
- Se houver audiência ou perícia antes do D-2, usar no campo `PRAZO FATAL (D-2)` uma data anterior ao ato.
- Em descrições de tarefas VIOS, usar a data de trabalho interna quando a operação exigir D-2.
- Ao responder ao usuário, diferenciar `Prazo fatal:` e `PRAZO FATAL (D-2):`.
- No resumo destinado à tarefa VIOS, inserir somente `PRAZO FATAL (D-2): DD/MM/AAAA`; não repetir ali o prazo jurídico fatal real.

### Embargos e recursos

Regras extraídas do POP:

- Embargos: 5 dias.
- Recurso em Juizado: 10 dias.
- Recurso na Justiça Comum: 15 dias.

#### Regra obrigatória para tarefas de análise

Sempre que a tarefa indicada for `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, exibir as duas linhas, nesta ordem:

```text
PRAZO PARA EMBARGOS: [resultado]
PRAZO PARA RECURSO: [resultado]
```

Preencher `[resultado]` com:

- a data operacional em D-2, quando cabível e calculável;
- `NÃO CABE`, quando o meio não for cabível;
- com cabimento pendente (o teor não permite concluir), a data em D-2 pelo prazo legal — o advogado decide se recorre e precisa da data;
- se não couber embargos nem recurso, omitir as duas linhas e deixar somente o `PRAZO FATAL (D-2)` do ato, se houver.

A tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` fica para o **mesmo dia** da análise, nunca para o D-2: as datas de embargos e de recurso (em D-2) ficam só na descrição. Não usar a linha `PRAZO FATAL (D-2)` quando houver as linhas de embargos e recurso.

Não omitir nenhuma das duas linhas em tarefas de análise. Para tarefas diferentes de análise, exibir somente as linhas efetivamente aplicáveis.

Quando couber embargos:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
```

Quando couber outro recurso:

```text
PRAZO PARA RECURSO: DD/MM/AAAA
```

Quando couberem ambos:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA
```

### Prazo previsto em lei (quando o ato não informar o prazo)

Quando a intimação não trouxer o número de dias, usar o prazo previsto em lei abaixo e escrever na descrição da tarefa que o prazo é o legal, por exemplo: `Prazo previsto em lei: 15 dias úteis (Apelação).`

Só usar `PENDENTE – NÃO CONSTA NO DOCUMENTO` quando o caso não estiver nesta tabela nem nas regras do Previdenciário.

#### Processo Civil

| Meio | Prazo |
| --- | --- |
| Prazo geral dos recursos: Apelação, Agravo de Instrumento, Agravo Interno, Recurso Especial e Recurso Extraordinário | 15 dias úteis |
| Embargos de Declaração (qualquer que seja a decisão) | 5 dias úteis |
| Manifestação sobre laudo pericial (art. 477, § 1º, CPC), inclusive no Juizado e no Previdenciário | 15 dias úteis |

#### Processo do Trabalho

| Meio | Prazo |
| --- | --- |
| Recursos em geral: Recurso Ordinário, Recurso de Revista, Agravo de Instrumento, Agravo de Petição, Embargos ao TST (Recurso de Embargos à SDI-1) | 8 dias úteis |
| Embargos de Declaração (contra sentença ou acórdão, para sanar omissão, contradição, obscuridade ou manifesto equívoco) | 5 dias úteis |
| Embargos à Execução (para o executado se manifestar ou contestar a penhora, após a notificação) | 5 dias úteis |
| Recurso Extraordinário (ao STF, regra do CPC) | 15 dias úteis |

#### Contagem do prazo legal

- Contar em dias úteis.
- Excluir o dia do começo e incluir o dia do vencimento.
- No Previdenciário continuam valendo as regras próprias: embargos em 5 dias, recurso em Juizado em 10 dias e recurso na Justiça Comum em 15 dias.
- Quando o cabimento estiver pendente (`PENDENTE – CONFIRMAR CABIMENTO`), informar mesmo assim o prazo legal do meio, para não perder o prazo.

### Cuidados

- Não afirmar cabimento de recurso quando o teor da decisão/sentença/acórdão não permitir concluir.
- Quando depender de avaliação jurídica, indicar: `Cabe análise do advogado sobre recurso/embargos.`
- Não sugerir abertura direta de recurso quando a regra da Controladoria exigir tarefa de análise primeiro.
- Quando a intimação já for expressamente para contrarrazões, pode sugerir tarefa de contrarrazões.
- Se faltar data de publicação/intimação, não calcule prazo; marque pendência.

### Contagem

- Cível, Trabalhista e JEC: usar dias úteis, salvo regra específica em sentido contrário.
- Criminal: usar dias corridos, salvo regra específica em sentido contrário.
- Considerar feriados nacionais e feriados locais previstos nos manuais internos disponíveis.

Se não houver calendário de feriados disponível na sessão, informe a pendência em vez de inventar a data.

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

## Arquivo para o robô (.txt)

Depois da análise, sempre entregar também o **arquivo para o robô**: um único bloco de código (```text) com as tarefas no formato abaixo. A Controladoria confere e ajusta, salva como `.txt` e sobe na página de envio; o robô lança exatamente o que estiver no arquivo, sem refazer a análise.

Formato — um bloco por tarefa, separados por uma linha só com `---`:

```text
CI: 42484
TAREFA: MINUTAR PETIÇÃO (EXECUÇÃO) 2026
DATA: 29/10/2026
HORA:
RESPONSÁVEIS: TAMIRA LOIOLA, BRENO SILVA MOTA
DESCRIÇÃO:
PRAZO FATAL: 29/10/2026
MINUTAR PETIÇÃO PARA INFORMAR OS DEMAIS DADOS NECESSÁRIOS PARA A CONFECÇÃO DOS REQUISITÓRIOS (RPV/PRECATÓRIO)
Despacho: considerando a certidão de ID 192859275, intime-se a parte exequente para, no prazo de 5 dias, informar os demais dados necessários para a confecção dos requisitórios.
---
CI: 42502
TAREFA: AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026
DATA: 22/01/2027
HORA: 08:20
RESPONSÁVEIS: automático
DESCRIÇÃO:
AUDIÊNCIA UNA
DATA: 22/01/2027
HORA: 08:20
FORMATO: TELEPRESENCIAL (ZOOM)
LINK/LOCAL: https://trt7-jus-br.zoom.us/j/85164513045
ID da reunião: 851 6451 3045
SENHA: 355957
```

Regras do arquivo:

- `CI`: só o número da CI do VIOS.
- `TAREFA`: o nome exato da lista oficial (seção "Referência — Tarefas VIOS e Modelos de Descrição").
- `DATA`: a data da tarefa no VIOS (DD/MM/AAAA), já calculada pelas regras de data (D-2, prioridade RPV/emenda da Suhiane, mesmo dia, data do ato). Só `CIÊNCIA` pode ficar com `DATA:` vazia (vai para o dia do envio).
- `HORA`: HH:MM em audiência, perícia e sustentação oral (na sessão virtual, o horário de início); vazia nas demais tarefas.
- `RESPONSÁVEIS`: `automático` (o VIOS marca o auxiliar da intimação) ou os nomes completos, separados por vírgula, como aparecem no VIOS. Na petição da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- `DESCRIÇÃO`: sempre a última linha de campo; tudo abaixo dela vai para a Observação da tarefa, exatamente como escrito. Incluir as linhas de prazo (`PRAZO FATAL:`, `PRAZO FATAL (D-2):`, `PRAZO PARA EMBARGOS:` / `PRAZO PARA RECURSO:` na análise) seguidas do texto do modelo da tarefa. Não incluir `Responsável a marcar na tarefa`, `Advogada auxiliar` nem `PRIORIDADE ...`.
- Duas tarefas da mesma CI (ex.: verificar viabilidade de sustentação + sustentação oral): dois blocos seguidos com o mesmo `CI`.
- **Não colocar no arquivo**: CI duplicada (vale a original), CI que não deve ser lançada (falta informação, evento sem teor, área divergente do auxiliar, tarefa pendente de definição). Listar essas CIs fora do bloco, com o motivo, para a Controladoria tratar à mão.
