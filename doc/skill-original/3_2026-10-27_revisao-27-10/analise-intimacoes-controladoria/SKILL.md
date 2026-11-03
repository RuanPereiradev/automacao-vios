---
name: analise-intimacoes-controladoria
description: use quando a solicitação envolver análise de intimações recebidas pelo DJEN/VIOS, planilhas de intimações, definição de tarefa VIOS, ciência, despacho, decisão, sentença, acórdão, audiência, perícia, prazo, recurso, embargos, contrarrazões, sustentação oral, RPV/precatório, guias, depósito judicial ou providência operacional da Controladoria Jurídica.
---

# Análise de Intimações da Controladoria

Esta skill padroniza a triagem de intimações recebidas no VIOS/DJEN e indica a tarefa VIOS adequada, prazo fatal, prazo operacional D-2, cabimento de recurso e descrição sugerida para o advogado.

## Fontes

Use as fontes nesta ordem:

1. Documento, intimação, planilha ou arquivo atual enviado pelo usuário.
2. `references/pop-fluxo-intimacoes.md`.
3. `references/roteamento-interno.md` para área, responsável, prioridades, divergências e duplicidades.
4. `references/tarefas-vios.md`.
5. `references/regras-prazos-recursos.md`.
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
2. Leia `references/roteamento-interno.md` e identifique separadamente natureza jurídica, fase, departamento e auxiliar. Não decida por um único desses campos.
3. Identifique cliente/parte representada, parte ativa, parte passiva e posição processual (as vezes vem AVANTTI SOLUCOES PRESTADORA DE SERVICOS LTDA (MATRIZ): PRESTADORA. e as vezes FAMOL COMERCIO DE MOVEIS LTDA (MATRIZ) mas é a mesma empresa) se não for indicado o cliente que colquei me indique como uma observação.
4. Classifique o ato: distribuição, despacho, decisão, sentença, acórdão, audiência, perícia, laudo, proposta de acordo, cálculos, RPV/precatório, guias, depósito judicial ou outro.
5. Verifique se há prazo fatal, audiência, perícia, link, ID, senha, local, formato, ou obrigação de juntar documento.
6. Defina a tarefa VIOS principal usando `references/tarefas-vios.md`nunca indique uma tarefa que não está nessa planilha.
7. Defina tarefas complementares quando o POP exigir mas sempre  usando `references/tarefas-vios.md` mesmo sendo complementar, como por exemplo sustentação que eu preciso abrir duas.
8. Quando a intimação determinar pagamento pelo cliente, aplicar obrigatoriamente o fluxo específico da área descrito abaixo e em `references/pop-fluxo-intimacoes.md`. No Trabalhista, começar por análise e não sugerir geração de guia. No Cível, indicar desde logo análise, contato com o cliente e minuta.
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
- Esta regra prevalece sobre todas as regras gerais de ciência, inclusive a de decisão de Execução sem providência para o cliente, quando o ato encerrar o processo/fase do cliente ou homologar acordo que o envolva.

Resumo-base para adaptar ao caso:

```text
[Inserir PRAZO FATAL (D-2) somente quando houver prazo calculável.]
Analisar a sentença de encerramento e conferir possíveis erros, omissões ou divergências na homologação em relação ao acordo, inclusive valores, obrigações, custas e honorários. Dar sequência ao contato com o cliente para informar o resultado e esclarecer eventuais providências.
```

## Regras centrais

### Regra obrigatória — prevalência do departamento e do auxiliar

Aplicar integralmente `references/roteamento-interno.md`. A ordem obrigatória é: orientação expressa do usuário; providência concreta; fase atual; departamento responsável; auxiliar cadastrado; natureza/órgão/CNJ; classe e assunto.

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

- Toda tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` gera um prazo: sempre exibir `PRAZO FATAL (D-2):` (ou `PRAZO FATAL:` com o dia útil seguinte à publicação, quando o ato não tiver prazo nenhum).
- Se couber, ou puder caber, embargos ou recurso, exibir as duas linhas `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:`, nesta ordem, **sempre com data em D-2**. Se a intimação não informar o prazo, usar o prazo previsto em lei. Mesmo com cabimento pendente (ex.: recurso imediato a confirmar), indicar a data: o advogado decide se recorre e precisa dela.
- Na linha do meio que não couber, preencher `NÃO CABE`.
- Se não couber embargos nem recurso, não exibir essas duas linhas: deixar somente o `PRAZO FATAL (D-2)`.
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

Use o modelo da tarefa VIOS em `references/tarefas-vios.md`.

Para sentença, decisão ou acórdão, use:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA
SENTENÇA/DECISÃO/ACÓRDÃO
[inserir o dispositivo ou a parte principal da intimação]
```

Quando preencher descrição de tarefa, use a data interna em D-2 quando a regra operacional pedir prazo de trabalho. Se for responder sobre prazo jurídico fatal, mostre também a data fatal em campo separado.

## Tarefas complementares obrigatórias

Consulte `references/pop-fluxo-intimacoes.md` para detalhes. Regras de maior atenção:

- Sustentação oral: indicar `VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL` e também `SUSTENTAÇÃO ORAL`.
- Pagamento ou depósito devido pelo cliente no Cível: indicar análise, `ENTRAR EM CONTATO COM O CLIENTE 2026` e `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026` para comprovação nos autos.
- Avaliação social: indicar aviso e `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` na mesma data operacional. Na ausência de orientação específica, lançar ambas para o dia seguinte. Se houver pedido de dados/documentos, indicar também minuta para Tamira no mesmo dia da análise.
- Pagamento, custas, honorários, preparo ou depósito no Trabalhista: indicar primeiro tarefa de análise. Não sugerir geração de guia nem minuta inicial; o contato com o cliente deve ocorrer antes de qualquer emissão.

## Regra obrigatória — marcar Breno nas tarefas de petição da Execução

- Sempre que indicar a tarefa `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)` ou qualquer opção equivalente do VIOS denominada `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)`, lembrar expressamente a Controladoria de marcar **Breno** na tarefa.
- Exibir obrigatoriamente, logo abaixo do nome da tarefa: `Responsável a marcar na tarefa: BRENO`.
- Aplicar a regra a todas as tarefas com esse nome, independentemente do conteúdo da petição, inclusive dados bancários, RPV/precatório, alvará, juntada de documentos e demais manifestações da Execução.
- Não aplicar automaticamente a outras tarefas de Execução que possuam nome diferente.

## Exceções obrigatórias à data D-2

Aplicar `references/roteamento-interno.md`:

- Toda tarefa relacionada a RPV/precatório deve ser lançada para o dia útil seguinte à publicação ou recebimento, mantendo o prazo jurídico fatal separado.
- Sempre que o auxiliar for `SUH`/Suhiane e a tarefa for de minutar emenda à inicial, lançar a tarefa para o primeiro dia útil seguinte à publicação ou ao recebimento. Aplicar esta regra tanto a `MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026` quanto a `MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026` e a qualquer opção equivalente sob responsabilidade da Suhiane.
- A prioridade de emenda da Suhiane prevalece sobre D-2. Manter o prazo jurídico fatal separado e não aplicar nem exibir `PRAZO FATAL (D-2)` como data operacional dessa tarefa.
- Nessas hipóteses, não rotular a data prioritária como `PRAZO FATAL (D-2)`. Usar apenas `PRAZO FATAL: DD/MM/AAAA` (sem D-2), em negrito e vermelho na descrição da tarefa.

Para emenda trabalhista ou previdenciária da Suhiane, usar obrigatoriamente:

```text
PRAZO FATAL: DD/MM/AAAA
```

## Regra obrigatória — não lançar quando faltar informação

Se a tarefa exigir informação que não está na intimação e só pode ser obtida no PJe (ex.: audiência sem tipo, data, horário, formato, local ou link/ID/senha; perícia sem data, horário ou local), a CI **não é lançada** no VIOS: listar o que falta para a Controladoria conferir no PJe e lançar manualmente.

Também não lançar quando a área da tarefa divergir do auxiliar responsável (ver `references/roteamento-interno.md`): tarefa de Execução com auxiliar que não é a Tamira, ou tarefa de outra área com a Tamira como única responsável.

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

Se a intimação não informar o número de dias, usar o prazo previsto em lei (tabela em `references/regras-prazos-recursos.md`, seção "Prazo previsto em lei") e escrever na descrição da tarefa: `Prazo previsto em lei: N dias úteis ([meio]).`

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

Quando a tarefa for `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` e couber (ou puder caber) embargos ou recurso, exibir as duas linhas, sempre com data em D-2 — pelo prazo legal quando a intimação não informar, inclusive com cabimento pendente. Na linha do meio que não couber, `NÃO CABE`. Se não couber nenhum dos dois, omitir as duas linhas e deixar somente o `PRAZO FATAL (D-2)`: toda tarefa de analisar gera um prazo.

## Sustentação oral

Sempre que a tarefa for:
VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL

indicar também a tarefa:
SUSTENTAÇÃO ORAL

A tarefa de verificar viabilidade deve ficar para o mesmo dia.
A tarefa de sustentação oral deve ficar para o dia da sustentação.

A tarefa SUSTENTAÇÃO ORAL deve vir neste padrão:

SUSTENTAÇÃO ORAL
DATA:
HORA:
LINK:

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

Sempre que houver audiência, mandar no padrão:

AUDIÊNCIA DE [TIPO]
DATA:
HORÁRIO:
FORMATO:
LINK/LOCAL:
OBS: É necessário ter atenção ao tipo de audiência, para que o advogado saiba como se preparar.

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

Aplicar a regra obrigatória de instrução de toda perícia social previdenciária acima e o fluxo de `references/pop-fluxo-intimacoes.md`. Indicar sempre aviso e instrução na mesma data operacional, inclusive em publicação apenas informativa. Se houver pedido de dados/documentos, acrescentar minuta para Tamira no mesmo dia da análise.

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
- toda tarefa `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO)` contém o lembrete `Responsável a marcar na tarefa: BRENO`;
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
