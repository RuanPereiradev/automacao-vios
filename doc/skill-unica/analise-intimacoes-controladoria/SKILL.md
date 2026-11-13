---
name: analise-intimacoes-controladoria
description: Analisar e revisar intimações DJEN/VIOS, identificar duplicidades e erros, definir tarefas oficiais, responsáveis, prazos jurídicos e datas operacionais da Controladoria. Usar para planilhas de intimações, ciência, despacho, decisão, sentença, acórdão, audiência, perícia, laudo, emenda, recursos, contrarrazões, sustentação oral, RPV/precatório, guias, depósitos e providências da Controladoria Jurídica. Receber CSV/Excel do VIOS e gerar um único TXT para bot de automação no modelo institucional, com pendências de consulta manual fora do arquivo.
---

# Análise de Intimações da Controladoria

Analisar todas as CIs, sem pular nenhuma. Distinguir providência jurídica, departamento interno, auxiliar, vencimento jurídico e data da tarefa. Não inventar dados nem presumir conferência nos autos.

## Entrega padrão — CSV/Excel VIOS para TXT do bot

Ao receber exportação CSV/Excel do VIOS para análise, entregar automaticamente **um único arquivo `.txt` em UTF-8**, no modelo institucional de `pedido-arquivo-robo(2).txt`, sem exigir que a usuária repita essa orientação. Ler [saida-txt-bot.md](references/saida-txt-bot.md) e usar [pedido-arquivo-robo.txt](assets/pedido-arquivo-robo.txt) como referência de estrutura. O arquivo contém somente tarefas completas e prontas para automação. Apresentar as CIs que exigem consulta manual **na conversa, fora do TXT**, no padrão habitual com CI e número do processo. O TXT é um arquivo de comandos para cadastro automático: usar exclusivamente os campos CI, PROCESSO, TAREFA, DATA, HORA, RESPONSÁVEIS e DESCRIÇÃO, nessa ordem, um bloco por tarefa separado por `---`, sem relatório ou comentários dentro dele. O modelo antigo `assets/modelo-analise-vios.md` não é o formato do bot. Esta regra prevalece sobre o formato geral de análise abaixo; pedidos apenas de revisão/duplicidades conservam a saída específica.

## Fontes e referências obrigatórias

1. Ler integralmente o documento atual enviado pelo usuário. Se for relatório de análises, distinguir o que consta do relatório do que foi conferido no expediente original ou nos autos.
2. Ler seção "Referência — Roteamento interno, prioridades e duplicidades" (mais abaixo) para departamento, responsável, duplicidades, Breno e prioridades.
3. Ler seção "Referência — POP e fluxo de intimações" (mais abaixo) para a providência e tarefas complementares.
4. Usar exclusivamente os nomes de seção "Referência — Tarefas VIOS e Modelos de Descrição" (mais abaixo); sugestões automáticas do VIOS são indícios, não decisões.
5. Ler seção "Referência — Prazos, cabimento e calendário" (mais abaixo) para termo inicial, cabimento, contagem, calendário e D-2.
6. Conferir seção "Referência — Validação para lançamento e comparação com o bot" (mais abaixo) antes de concluir ou autorizar lançamento.
7. Consultar arquivos internos disponíveis; usar memória apenas como apoio, nunca como substituta do documento atual.

Privilegiar o documento atual para os fatos do caso. Não tratar uma análise automática anterior como fonte que prevalece sobre lei, ato oficial ou intimação original. Buscar fontes oficiais atuais para validar legislação, cabimento e suspensões quando necessário.

## Fluxo de trabalho

Aplicar também as confirmações de 12/11/2026 em seção "Referência — Roteamento interno, prioridades e duplicidades" (mais abaixo): Francisco Valdir Ribeiro Marques – EPP = F. V. R. Marques Ltda.; VR Dias Celularia Ltda. = Casa do Celular de Cariacica Ltda. Não repetir essas pendências de vínculo. Observar ainda as correções de cliente/polo das CIs 42898 e 42883, preservando o departamento confirmado.

1. Identificar CI, processo, cliente, partes, posição processual, destinatário, órgão, fase, departamento e auxiliar. O cliente costuma estar na quarta ou quinta coluna: conferir pelo conteúdo.
2. Aplicar também as equivalências confirmadas em 11/11/2026, descritas em seção "Referência — Roteamento interno, prioridades e duplicidades" (mais abaixo). Reconhecer que AVANTTI SOLUCOES PRESTADORA DE SERVICOS LTDA (MATRIZ), inclusive com a indicação PRESTADORA, e FAMOL COMERCIO DE MOVEIS LTDA (MATRIZ) são a mesma empresa conforme orientação institucional. Reconhecer também ITBN TELEFONIA LTDA (MATRIZ), A M AGUIAR TELEFONIA LTDA e RAV HOLDING LTDA como identificações do mesmo cliente para vínculo operacional, conforme confirmação expressa da usuária em 03/11/2026. Não repetir pendência por essas diferenças; preservar a denominação e posição processual que constam do expediente, sem afirmar identidade de CNPJ ou fusão societária. Não estender a equivalência a outras empresas sem prova. Incorporar correções expressas da usuária sobre cliente, polo e setor; em inventário, não presumir que o inventariado seja cliente. Se o cliente indicado não constar da publicação e não houver equivalência/correção confirmada, registrar a divergência. Reconhecer também as equivalências confirmadas em 04/11/2026: Casa do Celular MG/SP = LM Tech Store Ltda.; Vieira de Araujo e Cia. Ltda. = Araujo & Salomão Ltda. – ME/Funerária Plasfran. Não repetir pendência por essas denominações; consultar o roteamento para preservar o responsável e a identificação documental.
3. Atribuir as demandas da carteira Casa no Celular/Casa do Celular a Ianna (Ianna Brena/IANN), conforme mapeamento institucional, corrigindo auxiliar antigo sem nova confirmação. Classificar o ato e identificar a providência concreta. Separar ordem para o cliente de ordem para a parte contrária. Não atribuir ao cliente prazo da parte contrária.
4. Comparar CIs do mesmo processo pelo teor, ID da decisão, dispositivo, objeto, publicação e destinatário. Verificar duplicidade mesmo se o programa disser “ato diferente”. Não deduplicar apenas por assunto, nome ou redação padronizada.
5. Definir tarefa oficial principal e cada complementar obrigatória, com finalidade, responsável, data e resumo próprios.
6. Aplicar o prazo expresso do ato à obrigação correspondente. Se ausente, indicar o prazo legal aplicável ao rito/providência; não bloquear apenas por ausência de prazo expresso. Não inventar termo inicial nem substituir prazo expresso por subsidiário. Identificar todo prazo: manifestação, emenda, pagamento, depósito, preparo, laudo, quesitos, provas, contrarrazões, embargos e recurso. Não omitir prazo porque não cabe recurso.
7. Identificar o meio e o prazo legal de referência sem decidir pelo advogado nem suprimir controles preventivos; conferir publicação efetiva, duração e regras especiais; aplicar a contagem simplificada abaixo. Distinguir a contagem simplificada solicitada de vencimento jurídico oficialmente validado.
8. Aplicar a data operacional correta, inclusive exceções a D-2. Não relançar para data já passada: manter a data original de referência e indicar urgência/atraso à Controladoria.
9. Elaborar resumo curto que permita lançar a tarefa sem reconstruir os dados.
10. Resolver inconsistências de redação antes de finalizar. Quando depender de informação externa ausente, entregar a análise e a pendência exata, com status de não lançar para a CI/tarefa afetada. Prosseguir com as demais.

## Responsáveis — proibição de atribuição à Controladoria

Nenhuma tarefa de intimação pode ficar em nome de **AMANDA LEITE MENDES**. Amanda realiza o lançamento e não acompanha nem executa as tarefas lançadas. No TXT do bot, não usar `automático`, pois esse valor direciona a tarefa para Amanda.

Aplicar esta ordem, salvo a regra específica de perícias abaixo:

1. Havendo advogado auxiliar identificado no VIOS ou no arquivo de entrada, preencher `RESPONSÁVEIS` com o nome completo do advogado auxiliar.
2. Não havendo advogado auxiliar, preencher `RESPONSÁVEIS` com o nome completo do advogado responsável pelo processo. Qualquer advogado responsável identificado pode receber a tarefa, salvo a exceção abaixo.
3. Exceção ao item 2: se não houver auxiliar e o advogado responsável pelo processo for **RONIELLE FEITOSA**, não atribuir a tarefa a ele nem a Amanda. Bloquear a tarefa, deixá-la fora do TXT e sinalizar à usuária: `NÃO LANÇAR — VERIFICAR QUEM É O ADVOGADO AUXILIAR OU O ADVOGADO RESPONSÁVEL CORRETO; PROCESSO SEM AUXILIAR E COM RONIELLE FEITOSA COMO RESPONSÁVEL.`
4. Se não houver auxiliar nem advogado responsável seguro identificado, bloquear e sinalizar a pendência. Não usar Amanda, `automático` ou nome presumido para completar o arquivo.

### Perícia médica judicial — responsável da filial

Somente na tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, o responsável não é Amanda, Suiane/Suhiane, o auxiliar nem o advogado responsável cadastrado no processo. Identificar a filial pela cidade vinculada à perícia e preencher `RESPONSÁVEIS` com o nome abaixo:

| Filial/cidade | Responsável pela tarefa de perícia |
| --- | --- |
| Camocim | FRANCISCO VICTOR HORA DO NASCIMENTO |
| Tianguá | JOÃO JÂNIO |
| Jijoca de Jericoacoara/Jijoca | GUIVIA VASCONCELOS |
| Sobral | ANA LETÍCIA DA SILVA LEITAO |

Não estender o roteamento por filial nem a exclusão de Suiane/Suhiane a qualquer outra tarefa, inclusive perícia técnica/médica trabalhista, perícia técnica cível, aviso, instrução, quesitos, indicação de assistente técnico ou manifestação sobre laudo. Essas tarefas seguem seus fluxos próprios. A proibição geral de atribuir tarefas de intimação a Amanda permanece válida.

Se a cidade/filial estiver ausente, ambígua ou fora desse mapeamento, não atribuir a tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` a Amanda nem a Suiane/Suhiane e não escolher filial por aproximação. Excluir a tarefa do TXT e sinalizar: `NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL DA PERÍCIA MÉDICA JUDICIAL.`

## Escolha entre análise, minuta e ciência

### Verificar primeiro se há providência concreta para o cliente

Antes de escolher a tarefa, identificar: (1) o que o ato determina; (2) quem deve agir; (3) se há obrigação, prejuízo, vício aparente ou questão jurídica concreta a avaliar pelo advogado agora. Não presumir necessidade de análise apenas porque o ato defere um pedido, altera o andamento ou tem conteúdo decisório. A ausência de prazo, isoladamente, também não basta para escolher ciência.

Para despacho que apenas suspende o prazo de obrigação, determina consulta/diligência pela secretaria ou pelo próprio juízo e manda aguardar resultado/nova intimação, indicar **CIÊNCIA da área**, quando não houver providência atual do cliente nem questão jurídica concreta identificada. Não abrir análise, minuta ou controles preventivos de embargos/recurso apenas por cautela abstrata. Esta regra prevalece sobre referências genéricas a decisões favoráveis ou efeitos sobre o cliente; preservar as análises obrigatórias de sentença, acórdão, homologação, RPV e demais hipóteses específicas desta skill.

Se houver ordem dirigida ao cliente, indeferimento/prejuízo, obrigação ainda exigível, vício aparente ou questão jurídica concreta, indicar a tarefa adequada e explicar a providência. Não transformar todo ato denominado “despacho” em ciência. Preservar a denominação documental no resumo (ex.: DESPACHO); o título sozinho não define a tarefa.

Exemplo confirmado — processo 0000539-19.2024.5.07.0029, despacho ID fc972df: suspende o prazo da obrigação de fazer até identificar dependentes do falecido e determina consulta ao Prevjud pela unidade judicial. Sem providência atual para os reclamados: `CIÊNCIA (TRABALHISTA) 2026`, sem prazos recursais. Resumo: “CIÊNCIA — Suspenso o prazo para cumprimento da obrigação de fazer até a identificação dos dependentes do falecido. Determinada consulta ao Prevjud pela unidade judicial. Aguardar nova intimação.”

- Indicar sempre análise da área para sentença, acórdão ou decisão que exija avaliação jurídica, inclusive favorável. Reservar ao advogado a escolha da providência seguinte; não abrir minuta recursal antes dessa análise.
- Para sentença que encerre o processo/fase ou homologue acordo envolvendo o cliente, indicar sempre análise, mesmo favorável, cumprida, com renúncia recursal ou arquivamento. Não substituir por ciência.
- Conferir sentença e acordo/aditivos quanto a partes, valores, parcelas, vencimentos, multas, quitação, obrigações, custas, honorários e alcance da extinção. Se faltar instrumento, registrar `PENDENTE – CONFERIR A SENTENÇA COM O ACORDO E DOCUMENTOS DOS AUTOS`. Não afirmar que a homologação está correta apenas pelo relato da sentença.
- Incluir na finalidade e no resumo da análise a conferência jurídica e o prosseguimento do contato com o cliente para informar o resultado, explicar o encerramento e esclarecer providências. A tarefa de análise já gera o contato com o cliente no fluxo do VIOS. Não indicar nem criar tarefa separada de contato para duplicar essa providência.
- Indicar minuta diretamente quando a ordem já definir a manifestação objetiva a apresentar. Não abrir recurso automaticamente quando depender de análise do advogado. Contrarrazões expressamente determinadas admitem minuta direta.
- Indicar ciência para distribuição simples, mero aviso ou despacho abrangido pelo filtro acima, sem providência atual nem conferência jurídica concreta para o cliente. Na Execução, mero aviso de movimentação sem avaliação jurídica concreta pode gerar ciência; sentença/acórdão/decisão para avaliação jurídica exige análise.
- Não usar ciência para compensar falta do teor, falta de identificação de quem recorreu ou dúvida de área/cliente. Quando a usuária pedir inclusão com os elementos disponíveis e o evento identificar inequivocamente sentença e resultado (ex.: “Julgada procedente a ação”), admitir análise da sentença com controles calculáveis, descrevendo somente o resultado conhecido e reservando a leitura do dispositivo à execução normal da análise. Não inventar condenação, valores ou obrigações. Isso não autoriza classificar despacho genérico sem teor.

## Datas das tarefas — aplicar a exceção antes da regra geral

### Contagem simplificada — excluir somente sábados e domingos

Por orientação expressa do usuário, aplicar a todas as contagens apresentadas nesta skill, inclusive vencimentos de referência de embargos, recursos, manifestações, obrigações e controles D-2, um calendário de segunda a sexta-feira. Contar feriados nacionais, estaduais, municipais, pontos facultativos, recesso e suspensões como dias úteis para este cálculo. Excluir somente sábados e domingos. Depois de calcular a data operacional, aplicar separadamente o ajuste de coincidência com feriado previsto abaixo.

Não usar feriados para excluir dias da contagem nem bloquear o cálculo apenas por faltar calendário judicial oficial. Usar a publicação/ciência efetivamente informada, excluir o dia do marco inicial e iniciar a contagem no próximo dia de segunda a sexta-feira, incluindo feriados. Não alterar a data documental da publicação para ajustá-la ao calendário simplificado. Preservar a quantidade de dias do prazo expresso ou legal de referência.

Apresentar os vencimentos solicitados por esse critério, inclusive os campos de prazo jurídico de referência, com uma indicação breve fora dos resumos: **“Contagem solicitada: segunda a sexta, incluindo feriados; vencimentos sem validação do calendário judicial oficial.”** Não apresentar essas datas como vencimentos jurídicos oficiais confirmados. Data-limite expressamente fixada no ato não pode ser substituída por uma contagem derivada; preservar a data determinada. Prazos em horas ou corridos, especialmente criminais, conservam sua unidade e regime próprios; não transformar dias corridos em dias de segunda a sexta.

Aplicar o mesmo calendário simplificado ao agendamento interno: análise/ciência até 12h no mesmo dia de segunda a sexta; após 12h ou em fim de semana, no próximo dia de segunda a sexta. Prioridades RPV/Suhiane e aviso/instrução social usam o próximo dia de segunda a sexta. D-2 corresponde a retroceder dois dias de segunda a sexta do vencimento de referência, incluindo feriados no percurso. Manter data e horário exatos de audiências, perícias e sustentações, sem aplicar D-2 ao comparecimento.

### Ajuste da DATA do VIOS quando coincidir com feriado

Após calcular normalmente o vencimento de referência, o D-2 e a data operacional candidata, conferir se a `DATA` da tarefa no VIOS coincide com feriado oficial aplicável ao escritório/filial que executará a tarefa:

1. Feriado nacional: antecipar a `DATA` para o dia de trabalho anterior.
2. Feriado estadual ou municipal da localidade do escritório/filial responsável pela tarefa: antecipar a `DATA` para o dia de trabalho anterior.
3. Feriado estadual ou municipal exclusivo de outro estado ou município, sem aplicação à localidade do escritório/filial responsável: não antecipar; manter a `DATA` calculada.
4. Ponto facultativo não é feriado para esta regra: manter a `DATA`, salvo orientação expressa de que o escritório estará fechado.

O dia de trabalho anterior é a data imediatamente anterior de segunda a sexta que não seja feriado nacional nem feriado estadual/municipal aplicável à mesma localidade. Se houver feriados consecutivos ou o dia anterior for sábado/domingo, continuar retrocedendo até o primeiro dia de trabalho aplicável.

Nas tarefas com data operacional ajustável, verificar apenas a coincidência da data candidata, usando fonte oficial para distinguir feriado de ponto facultativo e confirmar a abrangência territorial. Essa consulta não altera a contagem simplificada. Se houver indicação de feriado, mas não for possível confirmar se é feriado oficial, ponto facultativo ou se alcança a filial responsável, sinalizar `PENDENTE — CONFIRMAR APLICABILIDADE DO FERIADO À DATA OPERACIONAL` e não presumir a antecipação. Não fazer essa verificação para atos com data fixa.

A antecipação altera somente a `DATA` operacional da tarefa no VIOS. Preservar o vencimento de referência e o D-2 calculados pelo critério de segunda a sexta, incluindo feriados, inclusive nos cabeçalhos da descrição; registrar fora do resumo que a `DATA` foi antecipada e qual feriado causou o ajuste. Não alterar data nem horário fixos de audiência, perícia, sustentação ou outro ato agendado: esses eventos permanecem na data real, ainda que coincida com feriado, sem alerta ou sinalização adicional por essa coincidência.

**Exemplo:** publicação em 29/10/2026 e prazo de 5 dias: contar 30/10, 02/11, 03/11, 04/11 e 05/11. Vencimento de referência: **05/11/2026**; D-2: **03/11/2026**. Não excluir 30/10 ou 02/11 por feriado/suspensão.

Se, em outro caso, a `DATA` operacional calculada fosse **02/11/2026**, manter 02/11 na contagem e no controle de referência, mas lançar a tarefa no VIOS em **30/10/2026**, por ser o dia de trabalho anterior ao feriado nacional. Um feriado exclusivo de outro estado ou município, sem aplicação à filial responsável, não produziria esse recuo.

Separar data de lançamento no VIOS, vencimento de referência e controle D-2. Consultar o horário atual de America/Sao_Paulo (ou horário informado pelo usuário); não presumir lançamento de manhã. Nas demais seções e referências, interpretar “dia útil” como segunda a sexta, inclusive feriados, para a contagem simplificada; para a `DATA` operacional, aplicar o ajuste de feriado oficial previsto acima. “Prazo jurídico/vencimento jurídico” nos modelos representa referência calculada pelo critério solicitado, não validação oficial.

| Situação | Data da tarefa no VIOS | Descrição |
| --- | --- | --- |
| RPV/precatório e prioridades da Suhiane, inclusive emenda à inicial | Primeiro dia de expediente do escritório seguinte ao recebimento/lançamento em análise | Cabeçalho de prazo no padrão abaixo; prioridade não substitui o vencimento jurídico nem o D-2 |
| Analisar, ciência e verificar viabilidade de sustentação | Mesmo dia de expediente do escritório até 12h; após 12h ou fora de expediente, próximo dia de expediente do escritório | Análise de sentença/acórdão/decisão: duas datas recursais em D-2; ciência sem prazo não recebe prazo inventado |
| Aviso e instrução de perícia social | Primeiro dia de expediente do escritório após a análise, na mesma data para ambas | Não confundir orientação/aviso com o comparecimento à visita |
| Audiência, perícia com comparecimento e sustentação oral | Data e horário exatos do ato; sessão virtual no início da sessão | Modelo curto de evento; preencher também o horário no campo próprio do VIOS |
| Demais tarefas com prazo, inclusive minutar | D-2 | `PRAZO FATAL D -2: DD/MM/AAAA` |

Não estender automaticamente a prioridade a toda tarefa da Suhiane: aplicar as prioridades previstas no fluxo e as expressamente informadas. As exceções prioritárias prevalecem sobre o corte das 12h. Nunca alongar prazo judicial pela rotina interna. Se o ato/prazo ocorrer antes da data operacional, sinalizar urgência e antecipar; se já vencido, informar atraso sem alterar a data original.

Guardar vencimentos de referência, fundamento, duração e o critério simplificado nos campos de controle fora do resumo. A data de trabalho prioritário não é vencimento jurídico. Nas descrições prioritárias com prazo único, seguir esta ordem:

```text
PRAZO FATAL: [data de controle D-2]
[resumo breve da providência ou do ato]
```

No TXT, não escrever marcadores `PRIORIDADE ...` na descrição; refletir a prioridade na DATA e guardar o motivo no controle externo. Na minuta de dados de requisitórios, seguir o exemplo específico do usuário: `PRAZO FATAL: [D-2]`, título da minuta e breve despacho, sem linhas de responsável, auxiliar ou marcador final de prioridade. Registrar a prioridade nos campos de controle. Na análise jurídica de sentença/acórdão/decisão ligada a RPV, manter as duas linhas recursais, sem terceira linha de prazo fatal nem marcador de prioridade na descrição.


### Marco operacional pela publicação — orientação de 11/11/2026

Usar sempre a data de publicação informada no DJEN/CSV como marco dos controles internos solicitados, inclusive para Fazenda Pública, sem pedir a data de ciência no portal nem bloquear a tarefa somente por essa ausência. Excluir o dia da publicação e iniciar a contagem na próxima segunda a sexta, preservando a duração legal ou expressa e o D-2. Se faltar a publicação, não inventar o marco. Distinguir este controle operacional da validação jurídica de intimação pessoal; não afirmar que a publicação substitui a ciência exigida em lei. Se a usuária solicitar validação oficial, conferir a modalidade legalmente aplicável. No caso do Município de Morrinhos (CI 42851), contar da publicação de 11/11/2026 para os controles internos: embargos em dez dias, recurso em trinta dias e impugnação do art. 535 em trinta dias (não duplicar este último prazo).

## Prazos para embargos e recurso

Aplicar estes controles somente após definir que o ato exige análise jurídica. Despacho classificado como CIÊNCIA pelo filtro anterior não recebe datas de embargos/recurso nem prazo fatal inventado.

- Para toda análise jurídica de sentença, acórdão ou decisão, apresentar obrigatoriamente as duas datas abaixo, em D-2, nesta ordem, sem acrescentar `PRAZO FATAL`:

```text
PRAZO PARA EMBARGOS: DD/MM/AAAA
PRAZO PARA RECURSO: DD/MM/AAAA
[SENTENÇA/ACÓRDÃO/DECISÃO e resumo breve]
```

- Calcular as duas datas mesmo quando a triagem indicar possível incabimento de um ou de ambos. Sem prazo expresso, usar o prazo legal de referência do rito/meio correspondente. A decisão sobre cabimento pertence ao advogado. Não substituir uma data por `NÃO CABE` nem omitir a linha por conclusão automática de incabimento. Registrar eventual restrição legal e o caráter preventivo fora da descrição, sem apresentar esse controle como afirmação de que o recurso é admissível.
- Não inventar termo inicial, meio recursal, calendário ou duração quando faltarem elementos. Se não houver base para calcular uma das duas datas, bloquear a tarefa e listar a conferência necessária fora do arquivo de lançamento.
- Usar somente `PRAZO FATAL` em análise operacional de obrigação com prazo certo que não seja avaliação jurídica de sentença/acórdão/decisão e não envolva controle recursal. Exemplo: conferir minuta de requisitório com prazo objetivo. Não usar essa exceção para retirar as duas datas de uma análise jurídica.
- Nunca reunir os três cabeçalhos na mesma descrição: usar embargos + recurso OU prazo fatal. Minutas usam `PRAZO FATAL D -2:`; a minuta prioritária de requisitórios usa a apresentação específica acima, mantendo a data D-2.
- Se houver obrigação objetiva distinta na mesma intimação, preservar seu prazo nos campos externos e, quando o fluxo exigir, em tarefa própria. Não abrir antecipadamente minuta de recurso/embargos que depende da decisão do advogado na análise.
- Conferir regras especiais, inclusive homologação de conciliação no JEC, efeitos do julgamento de embargos e honorários recursais, conforme a referência. Não converter controle preventivo em conclusão jurídica de cabimento.


## Complementares e situações específicas

- Sustentação oral: indicar viabilidade e sustentação, em blocos próprios e datas distintas conforme a tabela. Separar prazo de envio/inscrição da data da sessão.
- Perícia médica previdenciária: indicar `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` e `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026` para quesitos e assistente técnico. Preservar prazo específico ou marcar pendência, sem presumir prazo não confirmado. Laudo já juntado, sem nova perícia, não gera tarefa de comparecimento nem de quesitos automaticamente.
- Perícia social previdenciária: indicar `AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para Leticya, e `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026` na mesma data operacional. Confirmar responsável pela instrução, sem presumir que seja o do aviso. Se a visita for expressamente sem agendamento, indicar ambas sem inventar data/hora de comparecimento; se os dados existirem em ID/evento/expediente ainda não lido, bloquear e listar a pendência fora do arquivo. Se solicitar dados/documentos, acrescentar minuta previdenciária para Suhiane, com prazo e data operacional próprios, preservando o prazo jurídico. Não substituir uma tarefa pela outra.
- No aviso social, usar o aviso padrão em negrito e sublinhado e, abaixo, breve trecho principal entre aspas. Consultar o POP para o texto.
- Manifestação sobre laudo previdenciário ou proposta de acordo do INSS: usar a tarefa oficial de petição intermediária/réplica/impugnação laudo. Usar o prazo expresso; se o expediente não trouxer prazo, aplicar o legal subsidiário pertinente (laudo: art. 477, §1º, CPC, 15 dias, quando aplicável), identificando a premissa fora do resumo. Não exigir consulta manual unicamente porque o expediente completo omitiu prazo; manter pendência se houver indicação concreta de prazo especial ainda não disponível.
- Pagamento pelo cliente no Trabalhista: indicar primeiro análise da área; não gerar guia nem minuta inicial. A análise gera contato para avisar e consultar o cliente antes da guia. Após autorização e pagamento, seguir a comprovação nos autos.
- Pagamento pelo cliente no Cível: indicar somente análise e minuta cível para comprovar pagamento/depósito/recolhimento. A análise já gera automaticamente o contato com o cliente; não indicar `ENTRAR EM CONTATO COM O CLIENTE 2026` como tarefa adicional. Aplicar a custas, honorários e parcelamento; não substituir por ciência ou guia isolada.
- Petições intermediárias da Execução da Tamira, inclusive opções equivalentes a `MINUTAR PETIÇÃO (EXECUÇÃO)`: informar Tamira como auxiliar e Breno como responsável nos campos próprios, fora da descrição. Não estender automaticamente a recursos, análise, cálculos ou outras tarefas especializadas.
- Audiência: exigir somente tipo/modelo, data, horário, formato e link ou local. ID da reunião, senha e demais dados complementares são opcionais: inserir quando informados e omitir quando ausentes, sem bloquear por sua falta. Ausência desses campos não prova acesso livre. Para sustentação oral e sua viabilidade, link/local são opcionais: inserir quando informados e omitir quando ausentes, sem bloquear o TXT nem exigir dispensa a cada caso. Preservar data e horário confirmados, sem inventar endereço ou afirmar acesso livre. A ausência de link/local não confirma cabimento nem inscrição; a viabilidade permanece sujeita à avaliação do advogado. Sempre que a intimação fornecer link encurtado, usar esse link no campo LINK/LOCAL e na descrição da audiência, conforme o POP. Não tratar audiência inicial automaticamente como UNA. Em audiência cível com cliente réu, conferir contestação; se ausente, indicar também `MINUTAR INICIAL/CONTESTAÇÃO/EMBARGOS À EXECUÇÃO (CÍVEL) 2026` para defesa.
- Cálculos trabalhistas: usar `MINUTAR PETIÇÃO INTERMEDIÁRIA DIVERSA (TRABALHISTA) 2026` quando não houver opção específica.
- Recurso/agravo trabalhista genérico: verificar quem recorreu e se há abertura de resposta. Parte contrária com resposta exigida: minuta; recurso só do cliente e sem providência: ciência. Se não identificável, usar `NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA`. Não criar tarefa apenas para o advogado buscar essa informação.

## Saída para análise de arquivo VIOS

Na análise humana, apresentar uma CI por bloco, na ordem e numeração originais, mesmo quando duplicada. No TXT do bot, aplicar a seleção e o modelo de `references/saida-txt-bot.md`: excluir duplicadas e pendências, preservando a ordem e a numeração de origem das CIs incluídas. No TXT, não incluir cabeçalhos humanos, nem numeração de itens; a CI é a chave e cada bloco traz também o PROCESSO (número do processo da CI, padrão 0000000-00.0000.0.00.0000). Usar os sete campos em linhas consecutivas e separar tarefas por uma linha contendo somente `---`. No chat, usar o padrão humano abaixo para as pendências. Repetir dados próprios de cada processo, sem misturar clientes, IDs, valores ou datas.

```text
## [n]. CI [número] — Processo [número]

Cliente: [nome e posição processual]
Auxiliar/Departamento: [cadastro e eventual pendência]
Do que se trata: [explicação objetiva]

Tarefa 1 no VIOS: [nome exato]
Finalidade: [providência]
Responsável/Auxiliar: [quando aplicável]
Data da tarefa: [data correta e motivo, ou pendência]
Prazo fatal: [vencimento jurídico da obrigação/meio identificado, ou pendência]
[Cabeçalho de prazo conforme a tabela; separar data prioritária do controle D-2]

Cabe recurso? [meio e análise de cabimento]
[PRAZO PARA EMBARGOS: data D-2, nas análises jurídicas]
[PRAZO PARA RECURSO: data D-2, nas análises jurídicas]

Resumo para tarefa 1:
[Linhas operacionais apropriadas e texto curto pronto para copiar]

Tarefa complementar: [cada uma em bloco próprio, com finalidade, data e resumo]
Observação/Pendências: [dados faltantes, destinatário, divergência e validação]
Status: [PRONTA PARA LANÇAMENTO / NÃO LANÇAR — providência faltante / DUPLICADA DA CI ...]
```

No resumo da tarefa usar o controle D-2 apropriado, sem confundi-lo com o dia de agendamento prioritário ou de análise. Se houver embargos e outro recurso, identificar os dois vencimentos jurídicos separadamente fora do resumo; não usar um único “prazo fatal” sem dizer a que corresponde. Para audiência/perícia/sustentação usar o modelo do ato, sem D-2 sobre a data de comparecimento.

## Saída para revisão de análises e duplicidades

Quando o usuário pedir somente revisão, erros ou duplicidades, não repetir obrigatoriamente 23 ou mais análises completas. Informar quantas CIs/processos foram conferidos, listar duplicidades confirmadas e prováveis com suas evidências, depois erros por CI com correção. Separar erro confirmado, inconsistência interna, pendência documental e hipótese preventiva. Usar tabela quando facilitar a comparação.

Não afirmar que tudo está correto se só houver resumos. Indicar o que pôde ser validado e o que depende de intimação/acordo/laudo/decisão original. Não afirmar acesso ao VIOS/PJe nem lançamento sem ação efetiva autorizada.

## Conferência final

Conferir uma linha interna por CI: cliente, destinatário, ato/ID, natureza, fase, departamento, auxiliar, tarefa principal/complementares, responsável, prazo jurídico, termo inicial, calendário/fonte, data operacional, prioridade, duplicidade e status.

- Revisar todas as CIs e suas tarefas; não encerrar por dúvida de uma CI deixando as demais sem análise.
- Verificar a instrução em toda perícia social, os quesitos na perícia médica e as duas tarefas de sustentação.
- Confirmar o corte das 12h para análise/ciência, o próximo dia de expediente do escritório para prioridades, eventual antecipação da `DATA` por feriado oficial aplicável e a separação entre data operacional, D-2 da descrição e vencimento jurídico.
- Conferir Breno nas petições intermediárias da Execução da Tamira.
- Não lançar nem incluir no arquivo importável tarefa indefinida, duplicada, com área/cliente/responsável incertos ou com dado indispensável ausente. Registrar exatamente o que a Controladoria deve conferir.
- Perguntar somente após ler os documentos e apenas sobre dados que não possam ser obtidos das fontes disponíveis. Entregar as pendências em bloco único; não perguntar qual modelo usar quando a regra já o define.

## Arquivo de lançamento e pendências fora do arquivo

Respeitar o modelo institucional anexado e entregar por padrão somente um TXT UTF-8 para o bot ao analisar exportações CSV/Excel do VIOS, conforme `references/saida-txt-bot.md`. Não entregar `.md`, `.csv`, `.docx` ou `.zip` em substituição ao TXT, salvo pedido expresso. Incluir nesse arquivo apenas tarefas completas e prontas. Não criar tarefa para mandar o advogado descobrir informação necessária à triagem. Quando faltar leitura de ID, evento ou expediente, data/horário/local, responsável ou outro dado indispensável, excluir a tarefa afetada do arquivo e listar no chat, fora dele: CI, processo, tarefa bloqueada, dado faltante e conferência exata a realizar no sistema. Informar totais de CIs conferidas, tarefas prontas, duplicidades e pendências, sem confundir quantidade de tarefas com quantidade de CIs. Preservar todas as CIs na conferência interna e explicar qualquer exclusão.

Manter a descrição breve, pronta para copiar, sem responsáveis/auxiliares, fundamentos extensos, transcrição longa, instruções de cadastro ou OBS genérica. Consultar os modelos curtos de audiência e sustentação no POP. Confirmar responsável e auxiliar nos campos próprios. Nunca usar `automático` nem atribuir tarefa a Amanda Leite Mendes ou Sarah Pontes/Controladoria. Na ausência de auxiliar, usar o advogado responsável, exceto Ronielle Feitosa, hipótese em que a tarefa deve ser bloqueada e sinalizada à usuária; somente em `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, aplicar obrigatoriamente o responsável da filial e não atribuir a Suiane/Suhiane.

## Referência — POP e fluxo de intimações

Índice: providência; pagamentos; audiências; perícias; sustentação; recursos genéricos.

### Providência principal

Aplicar primeiro as regras da parte principal desta skill e o roteamento, incluindo prioridade, duplicidade e dados indispensáveis. A Controladoria define tarefas para o advogado saber o que ocorreu e como agir.

| Situação | Providência |
| --- | --- |
| Sentença de encerramento/homologação de acordo envolvendo o cliente | Análise da área, inclusive favorável; comparar documentos e seguir contato com cliente |
| Sentença, acórdão ou decisão com avaliação jurídica, inclusive favorável | Análise da área; advogado decide a próxima providência |
| Manifestação objetiva determinada ao cliente | Minuta oficial correspondente |
| Distribuição simples ou mero aviso sem providência | Ciência da área confirmada |
| Mero aviso de movimentação na Execução, sem avaliação jurídica concreta | Ciência; decisões que exigem avaliação seguem análise |
| Despacho que suspende obrigação e determina diligência ao juízo/secretaria, sem providência atual do cliente nem questão jurídica concreta | Ciência da área, sem controles recursais; aguardar nova intimação |
| Laudo previdenciário/proposta de acordo do INSS | Petição intermediária/réplica/impugnação laudo |
| Cálculos trabalhistas sem tarefa específica | Petição intermediária diversa trabalhista |
| RPV em qualquer etapa pertinente | Tarefa conforme etapa, com prioridade do próximo dia de expediente do escritório |

Aplicar primeiro o filtro de providência concreta da parte principal desta skill, inclusive antes da regra genérica de análise de decisão favorável. Preservar as análises obrigatórias de sentença/acórdão e demais hipóteses específicas. Não abrir recurso diretamente quando depender de avaliação. Não transformar prazo da parte contrária em tarefa de pagamento/minuta para o cliente.

### Pagamentos pelo cliente

#### Trabalhista

Indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou análise oficial equivalente. Incluir natureza e prazo do pagamento. Não indicar ciência, guia ou minuta inicial. A análise gera contato para avisar o cliente e consultar se deseja pagar; só depois seguir guia autorizada, pagamento e tarefa de comprovação. Abranger custas, preparo, depósito recursal/judicial e honorários periciais.

#### Cível

Indicar somente duas tarefas:

1. `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026` ou análise oficial pertinente;
2. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026`, para comprovar pagamento/depósito/recolhimento.

A análise já gera automaticamente o contato com o cliente no VIOS. Não abrir nem incluir no arquivo a tarefa `ENTRAR EM CONTATO COM O CLIENTE 2026` para duplicar esse fluxo. Não aguardar o contato para indicar a minuta. Abranger parcelamento de custas e demais pagamentos a cargo do cliente. Não gerar o conjunto se o obrigado for apenas a parte contrária. Preservar prazo jurídico e data própria de cada tarefa.

### Audiências

Sempre que a intimação apresentar link encurtado de acesso à audiência, usar o link encurtado no campo LINK/LOCAL e na descrição pronta para copiar, em todas as áreas e tipos de audiência. Se houver link original e encurtado, inserir somente o encurtado na descrição, preservando ID e senha em campos próprios quando informados. Na ausência de link encurtado, usar o link original fornecido. Não criar nem presumir links encurtados.

Identificar conciliação, inicial, UNA ou instrução pelo teor, sem presumir UNA. Usar tarefa oficial com data exata do ato e horário no campo do VIOS.

```text
AUDIÊNCIA DE [TIPO]
DATA:
HORA:
FORMATO:
LINK/LOCAL:
ID da reunião:
SENHA:
```

Usar título exato como `AUDIÊNCIA UNA`, sem explicação entre parênteses. Separar link, ID e senha em linhas próprias. Não acrescentar OBS genérica, alertas de ausência, instruções de testemunhas ou transcrição extensa. Exigir somente tipo/modelo, data, hora, formato e link ou local. Omitir ID e senha quando não informados, inclusive em audiência virtual; são opcionais e não bloqueiam o lançamento. Não afirmar acesso livre apenas por ausência de senha. Faltando dado exigido para o lançamento, não inventar; indicar a conferência necessária. Em audiência cível com cliente réu, conferir contestação no VIOS/PJe e, se ausente, indicar também a tarefa oficial de inicial/contestação/embargos à execução, especificando que é contestação.

### Perícias

Antes de gerar especificamente `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, identificar a filial pela cidade vinculada à perícia. Preencher o responsável pelo seguinte mapa: Camocim — `FRANCISCO VICTOR HORA DO NASCIMENTO`; Tianguá — `JOÃO JÂNIO`; Jijoca de Jericoacoara/Jijoca — `GUIVIA VASCONCELOS`; Sobral — `ANA LETÍCIA DA SILVA LEITAO`. Esta regra prevalece sobre auxiliar e advogado responsável do processo. Não atribuir essa tarefa a Amanda Leite Mendes nem a Suiane/Suhiane.

Se a filial estiver ausente, ambígua ou fora do mapa, não lançar a tarefa de perícia médica judicial e sinalizar `NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL DA PERÍCIA MÉDICA JUDICIAL.` Não aplicar esse roteamento nem a exclusão de Suiane/Suhiane a perícia trabalhista, perícia técnica cível, aviso, instrução ou minutas; essas tarefas continuam em seus fluxos próprios.

```text
TIPO:
DATA:
HORA:
LOCAL/LINK:
```

#### Médica previdenciária

Indicar duas tarefas em blocos próprios:

1. `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, na data e horário exatos;
2. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026`, para quesitos e assistente técnico.

Para a segunda, usar prazo específico confirmado ou marcar pendência. Se o ato apenas designar a perícia, ainda indicar a complementar com prazo pendente; não presumir data. Não confundir com manifestação sobre laudo já produzido.

#### Social previdenciária

Indicar sempre:

1. `AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, para Leticya;
2. `INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026`, com responsável a confirmar.

Mesma data operacional: primeiro dia de expediente do escritório após a análise, salvo determinação expressa. Aplicar inclusive a aviso informativo ou visita sem data/horário. Se a visita estiver expressamente sem agendamento, não inventar horário; aviso/instrução têm data operacional própria. Se depender de abrir ID/evento/expediente para saber os dados, bloquear a tarefa afetada e listar fora do arquivo. Responsável da instrução deve estar identificado antes do lançamento.

Se solicitar dados, documentos, endereço ou telefone, acrescentar minuta previdenciária para Suhiane, com data operacional e prazo próprios; identificar prazo jurídico próprio. Apresentar cada tarefa com finalidade e resumo individuais.

Aviso padrão: apresentar em negrito e sublinhado no formato suportado pelo destino:

```text
Aviso: Foi agendada perícia social relacionada ao processo. O(a) assistente social pode ir até a casa do cliente a qualquer momento para a realização da visita.

"[trecho principal da intimação, incluindo eventual pedido de dados e prazo]"
```

Não converter uma visita com data marcada em visita indefinida: adaptar o aviso ao que o documento diz.

Resumo da instrução:

```text
Realizar instrução do(a) cliente para a perícia social. Explicar como ocorre a avaliação, orientar a apresentação de informações verdadeiras sobre sua realidade familiar, condições de vida e, quando pertinente, atividade de trabalho. Confirmar os dados de localização e conferir nos autos eventual data, horário e local. Registrar a orientação realizada.
```

### Sustentação oral

Indicar viabilidade da área conforme o corte das 12h para análise e sustentação oficial para a data/hora exatas do ato. Na sessão virtual, agendar no primeiro dia. Guardar término da sessão e prazo de inscrição/envio nos campos externos, sem incluí-los na descrição curta nem substituir o início da sessão pelo limite de envio.

```text
SUSTENTAÇÃO ORAL
DATA: [data inicial da sessão]
HORA: [horário inicial]
LINK:
```

Link/local são opcionais tanto na viabilidade quanto na sustentação: omitir o campo quando ausente, manter data e horário confirmados e incluir as tarefas no TXT sem exigir nova dispensa. Não inventar endereço, afirmar acesso livre ou tratar a agenda como confirmação de cabimento/inscrição. A análise de viabilidade permite ao advogado avaliar as regras do recurso e da sessão. Continuam indispensáveis os demais dados que determinam o cadastro, como processo, cliente, responsável, data e horário da sessão. Não afirmar que a sustentação foi realizada por apenas agendá-la.

### Recurso/agravo trabalhista genérico

Conferir no PJe quem recorreu e o objeto da intimação antes de escolher a tarefa:

- Recurso da parte contrária com resposta determinada/cabível: `MINUTAR RECURSO/CONTRARRAZÕES AO RECURSO (TRABALHISTA) 2026`.
- Recurso apenas do cliente, sem outra providência: `CIÊNCIA (TRABALHISTA) 2026`.
- Recursos de ambos: identificar peça contrária a responder; havendo resposta exigida, minuta correspondente; não havendo providência, ciência.
- Se não identificável: `NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA`.

Não criar tarefa ao advogado apenas para buscar o dado necessário à triagem. Não presumir abertura de contrarrazões da simples notícia de interposição.

### Exemplos de descrições aprovadas

```text
AUDIÊNCIA UNA
DATA: 22/01/2027
HORA: 08:20
FORMATO: TELEPRESENCIAL (ZOOM)
LINK/LOCAL: https://trt7-jus-br.zoom.us/j/85164513045
ID da reunião: 851 6451 3045
SENHA: 355957
```

```text
SUSTENTAÇÃO ORAL
DATA: 06/11/2026
HORA: 09:00
LINK: https://pje-plenario-virtual.tjce.jus.br/
```

```text
PRAZO FATAL: 29/10/2026
MINUTAR PETIÇÃO PARA INFORMAR OS DEMAIS DADOS NECESSÁRIOS PARA A CONFECÇÃO DOS REQUISITÓRIOS (RPV/PRECATÓRIO)
Despacho: considerando a certidão de ID 192859275, intime-se a parte exequente para, no prazo de 5 dias, informar os demais dados necessários para a confecção dos requisitórios.
```

Os dados desses exemplos são ilustrativos; nunca copiá-los para outro processo.

## Referência — Roteamento interno, prioridades e duplicidades

### Ordem de decisão

Conferir orientação expressa do usuário, providência concreta, fase atual, departamento responsável, auxiliar, natureza/órgão/CNJ e classe/assunto. Nenhum campo isolado substitui a leitura.

Conferir em conjunto departamento, responsável atual, auxiliar e providência; corrigir cadastro incompatível com o mapeamento institucional abaixo. Não confundir a coluna “Área” de um relatório automático com prova do departamento cadastrado. Tamira efetivamente responsável pela demanda de Execução exige tarefa de Execução. Não confundir esse vínculo com nome lançado por engano em tarefa previdenciária. Não presumir que todo processo contra o INSS permanece no Previdenciário se a transferência interna estiver comprovada.

### Mapeamento operacional

| Auxiliar | Área normalmente relacionada | Conferência |
| --- | --- | --- |
| Joaquim/JOAQ | Cível | Validar eventual transferência para Execução/Tamira |
| Joana/JOAN | Cível | Validar eventual transferência para Execução/Tamira |
| Lili/LILI | Cível | Validar eventual transferência para Execução/Tamira |
| Suhiane/SUH | Trabalhista Reclamante ou Previdenciário | Diferenciar por partes, teor, órgão e CNJ |
| Ianna/IANN (Ianna Brena) | Cível — demandas da Casa no Celular/Casa do Celular | Responsável confirmada pela usuária para todas as demandas dessa carteira; corrigir auxiliares antigos sem repetir consulta |
| Tamira/TAMI | Execução | Se efetivamente responsável, usar tarefa de Execução; se o caso/tarefa for previdenciário, corrigir para Suhiane |
| Johnys/JOHN | Trabalhista Reclamada | Substituir Carlos/CARL em tarefa trabalhista; Carlos não integra mais o Trabalhista |
| Breno | Petições intermediárias da Execução da Tamira | Marcar como responsável operacional, preservando Tamira como auxiliar |

SUH em processo da Justiça do Trabalho: usar Trabalhista Reclamante, inclusive na fase executiva, salvo transferência interna confirmada. SUH em benefício/INSS: Previdenciário, ressalvada a mesma confirmação. Palavra “execução” ou classe judicial não basta para mudar o setor.

### Equivalências e correções confirmadas

Atribuir todas as demandas da carteira Casa no Celular/Casa do Celular a Ianna (Ianna Brena, código IANN), conforme orientação expressa de 03/11/2026, inclusive quando a exportação trouxer auxiliar anterior. Nas CIs 42629, 42630, 42626 e 42631 deste lote, aplicar Ianna; conservar nomes e posições das partes. O responsável confirmado não dispensa o teor do ato para definir a tarefa. Não criar tarefa genérica se houver apenas “Proferido despacho. Intimem-se.” sem o documento.

Reconhecer ITBN TELEFONIA LTDA (MATRIZ), A M AGUIAR TELEFONIA LTDA e RAV HOLDING LTDA como identificações do mesmo cliente para vínculo operacional, por confirmação expressa da usuária em 03/11/2026. Não perguntar novamente por essas diferenças; preservar o nome documental e não inferir identidade cadastral de CNPJ. Correções expressas de cliente/polo/setor prevalecem sobre coluna desatualizada do CSV. Não considerar o inventariado cliente apenas por aparecer nessa coluna. Não inferir o nome completo de auxiliares sem mapeamento confirmado.

#### Equivalências confirmadas em 04/11/2026

- Reconhecer Casa do Celular MG/SP e LM Tech Store Ltda. como o mesmo cliente para vínculo operacional; atribuir a carteira a Ianna (IANN), inclusive na CI 42682. Não repetir consulta de vínculo entre essas denominações.
- Reconhecer Vieira de Araujo e Cia. Ltda. e Araujo & Salomão Ltda. – ME/Funerária Plasfran como a mesma empresa para vínculo operacional, inclusive na CI 42677. No Trabalhista, corrigir Carlos para Johnys.
- Preservar a denominação e posição processual do expediente; não inferir identidade de CNPJ, fusão ou equivalência com outras empresas.

#### Equivalências confirmadas em 09/11/2026

- Reconhecer FR INFORMÁTICA LTDA (MATRIZ) e ANTONIO B DE PAIVA SOUSA INFORMÁTICA - ME como o mesmo cliente para vínculo operacional, inclusive na CI 42793, processo 0000806-25.2023.5.07.0029. Não repetir pendência por essas denominações; preservar a denominação documental e o polo do cliente.
- Reconhecer RAV HOLDING LTDA e R V COMÉRCIO DE TELEFONIA LTDA como o mesmo cliente para vínculo operacional, inclusive na CI 42771, processo 0005947-23.2026.8.05.0256. Aplicar em conjunto com as equivalências já confirmadas de RAV Holding. A confirmação do vínculo não dispensa a leitura do teor do ato para definir a tarefa.
- Não inferir identidade de CNPJ, fusão societária ou equivalência com outras empresas sem confirmação.

#### Equivalências e confirmações de 11/11/2026

- Reconhecer FCIA COMÉRCIO LTDA (MATRIZ) e SANDALO A. A. ANGELIM – ME como o mesmo cliente para vínculo operacional, inclusive na CI 42850. Preservar a denominação documental; não repetir consulta por essa diferença.
- Reconhecer RAV HOLDING LTDA e CASA DO CELULAR DE CARIACICA LTDA como o mesmo cliente para vínculo operacional, inclusive na CI 42848. Aplicar Ianna à carteira Casa do Celular; preservar o nome documental, sem inferir identidade de CNPJ ou fusão societária.
- CI 42854: LD Urbanismo é cliente e a apelação foi apresentada pelo polo ativo; abrir contrarrazões cíveis para JOANA CLÁUDIA DOTTO.
- CI 42856: B. I. Transportes é cliente no polo ativo; não repetir pendência de vínculo nesse processo.
- CI 42853: os embargos foram apresentados pela cliente A. Aline B. de Sousa Pescados; a intimação para resposta se dirige à parte contrária. Usar ciência, sem minuta de contrarrazões para a própria embargante.
- CI 42874: FRANCISCO HELIO CARNEIRO é o cliente confirmado. A certidão atualiza interessados/representantes e o expediente dirige-se ao administrador judicial, sem providência atual do cliente: ciência da Execução/Tamira.
- CIs 42862 e 42875: responsável confirmada JOANA CLÁUDIA DOTTO. A primeira é certidão de juntada de extrato Sisbajud, sem nova ordem ao cliente no teor fornecido; a segunda manda aguardar investigações, sem providência atual.
- A tarefa oficial `CIÊNCIA (CÍVEL) 2026` (CI 1161 do catálogo VIOS, “Vios Jurídico - Tipo de Tarefa de Processo (1)(1).pdf”, pp. 81–82) abrange também Criminal. Usar essa opção no despacho sem providência da CI 42875, com Joana; não exigir tarefa “CIÊNCIA (CRIMINAL)” inexistente no catálogo nem alterar a natureza criminal do processo.

#### Equivalências e confirmações de 12/11/2026

- Reconhecer FRANCISCO VALDIR RIBEIRO MARQUES – EPP e F. V. R. MARQUES LTDA (inclusive MATRIZ, variações de pontuação e espaços) como o mesmo cliente para vínculo operacional, conforme confirmação expressa da usuária na CI 42896, processo 0001342-36.2023.5.07.0029. Não repetir pendência por essas denominações. Preservar a identificação documental e o polo; no caso trabalhista, manter Johnys conforme o departamento confirmado.
- Reconhecer VR DIAS CELULARIA LTDA (inclusive MATRIZ) e CASA DO CELULAR DE CARIACICA LTDA como o mesmo cliente para vínculo operacional, conforme confirmação expressa da usuária na CI 42878, processo 5016328-11.2025.8.08.0012. Não repetir pendência por essas denominações. Aplicar em conjunto com as equivalências já confirmadas da Casa do Celular de Cariacica; nas demandas cíveis dessa carteira, atribuir Ianna. Não transformar demanda trabalhista com departamento confirmado em Cível apenas pela equivalência empresarial.
- CI 42898, processo 0000047-56.2026.5.07.0029: a cliente confirmada é CAMILA DE ALBUQUERQUE PEREIRA LIMA, polo ativo. A coluna Varejão Chocobalas está incorreta para esse vínculo. Resposta ao recurso da União: Trabalhista Reclamante/Suhiane, sem repetir consulta de cliente ou atribuir o caso à carteira de reclamada.
- CI 42883, processo 0006099-07.2014.8.06.0081: vínculo do cliente FRANCISCO JOSE MORACIO DE ANDRADE e polo ativo confirmados pela usuária. Preservar Execução/Tamira e prioridade RPV; a indicação de Karlos como parte na publicação não reabre a pendência de vínculo já resolvida.
- Não inferir identidade de CNPJ, fusão societária nem equivalência com outras empresas além das confirmações expressas.

### Divergências e informações ausentes

- Identificar separadamente natureza, fase, departamento confirmado/provável e auxiliar.
- Se só houver auxiliar, sem prova de departamento compatível, registrar o setor provável como hipótese. Não apresentar essa hipótese como cadastro validado.
- Tarefa previdenciária cadastrada para Tamira: corrigir para Suhiane. Tarefa trabalhista cadastrada para Carlos: corrigir para Johnys. Não bloquear essas correções já autorizadas pelo usuário.
- Auxiliar de outra área com providência executiva: confirmar se houve transferência; não trocar setor apenas pelo conteúdo executivo.
- Divergência não resolvida impede lançamento da tarefa afetada; entregar a providência identificada e as alternativas oficiais. Se o usuário/documento confirmar a transferência e o responsável, registrar a evidência e não repetir pedido de confirmação.
- Sem setor seguro: `PENDENTE – CONFIRMAR ÁREA CADASTRADA NO VIOS.`
- Cliente não identificado nas partes: registrar `PENDENTE – CONFIRMAR VÍNCULO DO CLIENTE COM O PROCESSO E POSIÇÃO PROCESSUAL.` Não presumir identidade empresarial por semelhança de nome.
- Não usar tarefa de outra área como alternativa automática para contornar bloqueio do programa.

Modelo:

```text
OBSERVAÇÃO DE CADASTRO:
Natureza/fase: [dados do teor].
Departamento: [confirmado por fonte / pendente].
Auxiliar informado: [nome].
Providência: [o que deve ser feito].
NÃO LANÇAR — confirmar [divergência específica].
Se permanecer em [área]: [tarefa oficial].
Se houver transferência confirmada: [tarefa oficial da outra área].
```

### RPV/precatório

Tratar como prioritários determinação de expedição, minuta, cálculos vinculados, documentos, dados bancários, procuração/contrato, destaque de honorários, retificação, cancelamento, conversão e outras pendências que afetem expedição/conferência/pagamento.

Data: primeiro dia de expediente do escritório seguinte à publicação/recebimento válido. Preservar prazo jurídico e nunca adiá-lo por causa da rotina interna. Essa prioridade prevalece sobre D-2 e sobre a data genérica de análise, salvo providência mais urgente justificada.

Seguir os cabeçalhos da parte principal desta skill: prazo único em D-2, depois resumo; no TXT, não inserir marcador de prioridade na descrição. Para análise jurídica, usar as duas datas recursais sem terceira linha. Na minuta de dados de requisitório, usar o exemplo específico sem nomes ou marcador final na descrição. O agendamento permanece no próximo dia de expediente do escritório; a data do cabeçalho não se torna vencimento jurídico.

| Etapa | Tarefa |
| --- | --- |
| Decisão determinando futura expedição | Análise da área responsável |
| Dados/documentos/cálculos a apresentar | Minuta oficial apropriada da área |
| Requisitório/minuta já expedido para conferência | `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`, se setor confirmado |
| Alvará expedido sem providência | Ciência da área; conferir eventual vínculo com RPV |
| Erro/pendência no requisitório | Analisar minuta ou decisão conforme o ato; minutar quando a providência já for objetiva |

### Emenda da Suhiane

Aplicar a toda emenda à inicial com auxiliar SUH, trabalhista ou previdenciária, inclusive opção equivalente oficial. Primeiro dia de expediente do escritório seguinte à publicação/recebimento válido, sem D-2 operacional.

Usar `PRAZO FATAL D -2:` na descrição da minuta e guardar a prioridade em campo próprio. A data de lançamento prioritária não substitui o controle D-2 do prazo judicial.

### Tamira e Breno

Em petições intermediárias da Execução da Tamira, inclusive `MINUTAR PETIÇÃO (EXECUÇÃO) 2026`, preencher os campos de responsável e auxiliar, fora da descrição:

```text
Advogada auxiliar: TAMIRA
Responsável a marcar na tarefa: BRENO
```

Aplicar a dados bancários, documentos, RPV, alvará, prosseguimento, penhora e manifestações intermediárias equivalentes. Não presumir essa atribuição para análise, recursos, homologação/impugnação aos cálculos ou outras tarefas especializadas. Preservar Tamira como auxiliar.

### Duplicidades — conferir manualmente também

1. Agrupar candidatos por processo, sem eliminar nada.
2. Comparar ID da decisão, teor/dispositivo, objeto, datas e destinatários. Mesma decisão publicada para partes diferentes pode produzir duas CIs sem exigir duas tarefas. Pequenas diferenças de redação ou resumos feitos por modelos diferentes não tornam o ato distinto.
3. Mesmo ID e mesmo conteúdo: duplicidade confirmada, ressalvada republicação corretiva ou nova comunicação que modifique o prazo. Se só houver resumos coincidentes sem ID original, classificar como provável e pedir conferência do documento antes de ignorar a CI.
4. Preservar preferencialmente a comunicação própria do cliente, mais completa e válida para seu prazo. Não adotar prazo da publicação dirigida à parte contrária como prazo do cliente.
5. Manter cada CI no bloco e posição originais. Na cópia, escrever `DUPLICADA DA CI [NÚMERO]. Não abrir nova tarefa. Utilizar a tarefa indicada na CI mais completa.` Se provável, escrever `PROVÁVEL DUPLICIDADE — CONFERIR ID/TEOR ANTES DE DESCARTAR`.
6. Se outra CI acrescentar dado útil, incorporar à tarefa existente. Se modificar data/local/prazo por novo ato, analisar cada CI e atualizar a tarefa apropriada; não ignorar a mudança como duplicata.
7. Não confundir tarefas complementares obrigatórias com duplicidade. Não deduplicar laudos, perícias ou despachos padronizados de processos/clientes diferentes.
8. Conferir de forma independente avisos automáticos “ato diferente” e “duplicada”. Não afirmar que o bot detectou corretamente sem confronto dos textos.

### Ausência de responsável

Nenhuma tarefa de intimação pode ser atribuída a AMANDA LEITE MENDES, que realiza o lançamento, mas não acompanha nem executa as tarefas. Não usar `automático` no TXT, pois esse valor direciona a tarefa para Amanda.

Usar o nome completo do advogado auxiliar. Se não houver auxiliar, usar o nome completo do advogado responsável; qualquer outro advogado responsável identificado pode receber a tarefa. A única exceção a esse fallback é RONIELLE FEITOSA: se não houver auxiliar e ele constar como responsável pelo processo, não atribuir a tarefa a ele. Registrar `NÃO LANÇAR — VERIFICAR QUEM É O ADVOGADO AUXILIAR OU O ADVOGADO RESPONSÁVEL CORRETO; PROCESSO SEM AUXILIAR E COM RONIELLE FEITOSA COMO RESPONSÁVEL`, bloquear a tarefa e listá-la fora do TXT para conferência da usuária.

Também não atribuir nenhuma tarefa a Sarah Pontes/Controladoria. Se não houver responsável identificável pelas regras institucionais, registrar `RESPONSÁVEL NÃO IDENTIFICADO`, bloquear a tarefa e listar a pendência fora do arquivo. Não presumir responsável de outra área.

### Responsável da perícia médica judicial por filial

Somente para a tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, o roteamento por filial prevalece sobre auxiliar e advogado responsável do processo. Não atribuir essa tarefa a AMANDA LEITE MENDES nem a Suiane/Suhiane.

| Filial/cidade vinculada à perícia | Responsável |
| --- | --- |
| Camocim | FRANCISCO VICTOR HORA DO NASCIMENTO |
| Tianguá | JOÃO JÂNIO |
| Jijoca de Jericoacoara/Jijoca | GUIVIA VASCONCELOS |
| Sobral | ANA LETÍCIA DA SILVA LEITAO |

Não estender esta regra a perícia técnica/médica trabalhista, perícia técnica cível, aviso, instrução, quesitos, indicação de assistente técnico, manifestação sobre laudo ou qualquer outra tarefa. Nessas tarefas, Suiane/Suhiane não é excluída por esta regra; permanece apenas a proibição geral de atribuição a Amanda. Se não for possível identificar inequivocamente uma das quatro filiais na perícia médica judicial previdenciária, bloquear a tarefa e registrar `NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL DA PERÍCIA MÉDICA JUDICIAL.` Não escolher responsável por semelhança de cidade ou por mera presença de nome no cadastro.

## Referência — Tarefas VIOS e Modelos de Descrição

Use esta lista para escolher a tarefa VIOS e montar a descrição. Preserve o nome da tarefa quando possível.

Aplicar obrigatoriamente as datas, cabeçalhos exclusivos e modelos curtos da parte principal desta skill e POP. Análise/ciência observam o corte das 12h. Prioridades são agendadas no próximo dia de expediente do escritório; a descrição preserva controle D-2. Se a `DATA` operacional ajustável coincidir com feriado nacional ou local aplicável à filial, antecipar para o dia de trabalho anterior, sem alterar as datas de referência da descrição. Responsáveis e auxiliares ficam fora da descrição.

Somente em `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, usar o responsável da filial definido na parte principal desta skill: Camocim — `FRANCISCO VICTOR HORA DO NASCIMENTO`; Tianguá — `JOÃO JÂNIO`; Jijoca de Jericoacoara/Jijoca — `GUIVIA VASCONCELOS`; Sobral — `ANA LETÍCIA DA SILVA LEITAO`. Nunca atribuir essa tarefa a Amanda Leite Mendes ou Suiane/Suhiane. Todas as demais tarefas seguem seus fluxos próprios; nelas, esta regra não exclui Suiane/Suhiane.

Em qualquer tarefa de intimação, nunca usar `automático` no campo `RESPONSÁVEIS`: informar o advogado auxiliar; na ausência dele, usar qualquer advogado responsável identificado, exceto Ronielle Feitosa. Se não houver auxiliar e Ronielle for o responsável, bloquear e sinalizar para a usuária conferir o auxiliar ou o responsável correto, conforme a parte principal desta skill.

Índice: Trabalhista; Previdenciário; Execução; Cível; Gerais e complementares; Fluxo de pagamento; Pendências de saneamento.

#### Trabalhista

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (TRABALHISTA) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR RECURSO/CONTRARRAZÕES AO RECURSO (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR RÉPLICA À CONTESTAÇÃO (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR RÉPLICA |
| MINUTAR PETIÇÃO INTERMEDIÁRIA DIVERSA (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR PETIÇÃO |
| MINUTAR QUESITOS/INDICAR PERITOS (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR QUESITOS |
| MINUTAR PETIÇÃO SOBRE O LAUDO PERICIAL (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AO LAUDO PERICIAL |
| MINUTAR MEMORIAIS/RAZÃO FINAIS/ALEGAÇÕES FINAIS (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR ALEGAÇÕES FINAIS |
| MINUTAR EMENDA A INICIAL (TRABALHISTA) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR EMENDA |
| AUDIÊNCIA DE CONCILIAÇÃO (TRABALHISTA) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026 | AUDIÊNCIA UNA/INSTRUÇÃO [indicar se é una ou instrução]<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| PERÍCIA TÉCNICA/MÉDICA (TRABALHISTA) 2026 | PERÍCIA TÉCNICA/MÉDICA (TRABALHISTA)<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (TRABALHISTA) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

#### Previdenciário

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (PREVIDENCIÁRIO) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (PREVIDENCIÁRIO) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (PREVIDENCIÁRIO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AO LAUDO PERICIAL |
| MINUTAR EMENDA À INICIAL (PREVIDENCIÁRIO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR EMENDA |
| AUDIÊNCIA PREVIDENCIÁRIA (PREVIDENCIÁRIO) 2026 | AUDIÊNCIA DE INSTRUÇÃO<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026 | PERÍCIA MÉDICA<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (PREVIDENCIÁRIO) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| AVISAR PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026 | Abrir para o primeiro dia de expediente do escritório seguinte à análise, salvo data expressa do usuário. Usar o aviso padrão do POP e indicar obrigatoriamente a tarefa de instrução para a mesma data operacional. |
| INSTRUÇÃO PERÍCIA SOCIAL JUDICIAL (PREVIDENCIÁRIO) 2026 | DATA DA TAREFA: mesma data operacional da tarefa de perícia social/aviso no VIOS.<br>Realizar instrução do(a) cliente para a perícia social. Explicar como ocorre a avaliação e orientar a apresentação de informações verdadeiras sobre a realidade familiar, condições de vida e, quando pertinente, atividade de trabalho. Confirmar dados de localização, conferir eventual data, horário e local nos autos e registrar a orientação realizada. |
| SUSTENTAÇÃO ORAL PPREVIDENCIÁRIO) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

#### Execução

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (EXECUÇÃO) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| MINUTAR EXECUÇÃO DE SENTENÇA (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CUMPRIMENTO DE SENTENÇA |
| MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026) | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR [indicar petição, ex.: dados bancários] |
| MINUTAR EMBARGOS À EXECUÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR EMBARGOS |
| MINUTAR EMBARGOS/RECURSO/CONTRARRAZÕES (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES |
| MINUTAR HOMOLOGAÇÃO/IMPUGNAÇÃO AOS CÁLCULOS (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR MANIFESTAÇÃO AOS CÁLCULOS |
| MINUTAR RESPOSTA À IMPUGNAÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR RESPOSTA |
| MINUTAR CHAMAMENTO DO FEITO À ORDEM (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CHAMAMENTO FEITO À ORDEM |
| CIÊNCIA (EXECUÇÃO) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR PETIÇÃO EXECUÇÃO 2026 (MINUTAR PETIÇÃO (EXECUÇÃO) 2026) | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR PETIÇÃO [inserir a parte principal da intimação] |
| AUDIÊNCIA DE CONCILIAÇÃO (EXECUÇÃO) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026 | PRAZO FATAL: DD/MM/AAAA<br>[inserir informação importante da intimação] |
| MINUTAR PETIÇÃO (EXECUÇÃO) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR PETIÇÃO [informar qual petição e destacar a parte principal da intimação] |

#### Cível

No catálogo oficial, `CIÊNCIA (CÍVEL) 2026` (CI 1161) também está habilitada para Criminal. Aplicar na CI 42875, com responsável JOANA CLÁUDIA DOTTO, sem mudar a natureza do processo nem criar prazo para despacho que apenas aguarda investigações.

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026 | PRAZO PARA EMBARGOS: DD/MM/AAAA<br>PRAZO PARA RECURSO: DD/MM/AAAA<br>SENTENÇA/DECISÃO/ACÓRDÃO<br>[inserir se é sentença, decisão ou acórdão e abaixo colocar o dispositivo] |
| CIÊNCIA (CÍVEL) 2026 | CIÊNCIA<br>[inserir a parte principal da intimação] |
| MINUTAR RECURSO/CONTRARRAZÕES (CÍVEL) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES<br>Observação: recursos são na tarefa de analisar. |
| MINUTAR EMBARGOS DE DECLARAÇÃO/CONTRARRAZÕES (CÍVEL) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTRARRAZÕES<br>Observação: recursos são na tarefa de analisar. |
| MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR PETIÇÃO [informar qual petição e destacar a parte principal da intimação] |
| MINUTAR MEMORIAIS/RAZÃO FINAIS/ALEGAÇÕES FINAIS (CÍVEL) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR ALEGAÇÕES FINAIS |
| AUDIÊNCIA DE CONCILIAÇÃO (CÍVEL) 2026 | AUDIÊNCIA DE CONCILIAÇÃO<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| AUDIÊNCIA UNA/INSTRUÇÃO (CÍVEL) 2026 | AUDIÊNCIA UNA/INSTRUÇÃO [indicar se é una ou instrução]<br>DATA:<br>HORA:<br>LINK/LOCAL: |
| PERÍCIA TÉCNICA (CÍVEL) 2026 | PERÍCIA TÉCNICA<br>DATA:<br>HORA:<br>LOCAL: |
| VERIFICAR VIABILIDADE DE REALIZAR SUSTENTAÇÃO ORAL (CÍVEL) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| MINUTAR INICIAL/CONTESTAÇÃO/EMBARGOS À EXECUÇÃO (CÍVEL) 2026 | PRAZO FATAL D -2: DD/MM/AAAA<br>MINUTAR CONTESTAÇÃO |
| SUSTENTAÇÃO ORAL(CÍVEL) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |

#### Gerais e complementares

| Tarefa VIOS | Modelo de descrição |
| --- | --- |
| SUSTENTAÇÃO ORAL | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| SUSTENTACÃO ORAL (RECLAMANTE) 2026 | SUSTENTAÇÃO ORAL<br>DATA:<br>HORA:<br>LINK: |
| ENTRAR EM CONTATO COM O CLIENTE 2026 | Não indicar nem lançar como tarefa adicional à análise: o fluxo de análise já gera o contato com o cliente automaticamente. No pagamento cível, indicar somente análise e minuta de comprovação. |

#### Fluxo de pagamento por área

- Trabalhista: indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou análise equivalente. Não indicar geração de guia nem minuta no primeiro momento.
- Cível: indicar somente análise e `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026` desde logo. A análise já gera o contato; não duplicá-lo com tarefa separada. Usar na minuta: `PRAZO FATAL D -2: DD/MM/AAAA` e `MINUTAR PETIÇÃO PARA COMPROVAR [PAGAMENTO/DEPÓSITO/RECOLHIMENTO] NOS AUTOS`.

#### Pendências de saneamento

Alguns nomes na planilha original possuem grafia possivelmente inconsistente, como `PPREVIDENCIÁRIO`, `EXECUCÃO`, `SUSTENTACÃO` e `PRECATORIO`. Preserve o nome se for exatamente a opção disponível no VIOS. Se houver dúvida, informe `PENDENTE – CONFIRMAR OPÇÕES DISPONÍVEIS NO VIOS.`

## Referência — Prazos, cabimento e calendário

Índice: validação; prazos de referência; calendário; casos especiais; apresentação.

### Validar antes de calcular

Identificar cliente destinatário, meio/providência, rito, órgão que praticou o ato, prazo expresso ou legal, termo inicial e calendário aplicável. Separar prazo da parte contrária. Não afirmar ausência geral de recurso só porque o ato favorece o cliente: avaliar interesse e vícios próprios.

Distinguir disponibilização, publicação e ciência eletrônica. Não tratar captura/geração como publicação. Por orientação expressa de 11/11/2026, usar sempre a publicação informada no DJEN/CSV para os controles operacionais solicitados, inclusive para Fazenda Pública, sem perguntar a ciência do portal nem bloquear somente por sua ausência. Excluir o dia da publicação e iniciar no próximo dia de segunda a sexta. Não apresentar essa escolha operacional como validação de que a publicação substitui a intimação pessoal exigida em lei. Se a usuária pedir validação jurídica oficial, conferir o marco legal próprio; se faltar publicação, não inventá-la.

Aplicar prazo expresso confirmado para a providência; se divergir da regra legal, registrar a divergência e a necessidade de conferência, sem alongar silenciosamente o controle. Se faltar prazo no expediente completo, indicar o prazo legal aplicável ao rito/providência, identificando eventual aplicação subsidiária. A ausência de prazo expresso, por si só, não bloqueia a tarefa nem exige consulta. Exigir conferência apenas se faltar termo inicial, não houver regra aplicável identificável ou existir indicação concreta de prazo especial ainda não disponível. Preservar controle preventivo identificado se a validação ainda estiver pendente.

### Prazos legais de referência

Conferir a legislação vigente e as exceções do caso. A tabela não prova cabimento nem afasta regra especial.

| Rito/meio | Prazo de referência |
| --- | --- |
| CPC: apelação, agravo de instrumento/interno, REsp e RE | 15 dias úteis, quando cabíveis |
| Embargos de declaração cíveis/previdenciários/JEC | 5 dias úteis, quando cabíveis |
| Fazenda Pública no CPC (fora do JEC/JEF) | Embargos: 10 dias; recursos em regra: 30 dias, observada a prerrogativa do art. 183. Impugnação do art. 535: 30 dias expressos, sem nova duplicação. Marco dos controles internos pela publicação conforme orientação de 11/11/2026. |
| Sentença de JEC/JEF: recurso inominado | 10 dias úteis, ressalvadas exceções de cabimento |
| Manifestação sobre laudo, art. 477, §1º, CPC | 15 dias úteis, se aplicável e sem prazo específico confirmado |
| Trabalhista: RO, RR, agravo de instrumento/petição e embargos ao TST | 8 dias úteis, observados pressupostos e regras especiais |
| Embargos de declaração trabalhistas | 5 dias úteis, quando cabíveis |
| Embargos à execução trabalhista | 5 dias úteis após o marco próprio da CLT, inclusive garantia/penhora quando exigida; não presumir início pela mera publicação |
| RE ao STF em matéria trabalhista | 15 dias úteis, quando cabível |

Nos campos externos de controle, identificar `Prazo previsto em lei: N dias úteis ([meio/providência e fundamento]).`, mantendo breve a descrição. Se faltar base para aplicar a tabela ou dado para contar, registrar pendência, não prazo fatal validado.

### Calendário e contagem

- Aplicar o calendário simplificado da parte principal desta skill a todas as contagens de prazos em dias úteis: contar segunda a sexta e excluir somente sábados e domingos, inclusive em embargos, recursos e manifestações. Incluir feriados, pontos facultativos, recesso e suspensões. Não usar calendário de feriados para excluir dias da contagem; consultar fonte oficial somente para verificar se a `DATA` operacional candidata coincide com feriado aplicável.
- Excluir o dia da publicação/ciência informada e iniciar no próximo dia de segunda a sexta. Preservar o marco documental e a duração expressa ou legal pertinente. Não atribuir ao cliente obrigação da parte contrária; para o marco operacional, aplicar a publicação fornecida e a orientação expressa de 11/11/2026 da parte principal desta skill.
- D-2: retroceder dois dias de segunda a sexta do vencimento de referência, incluindo feriados. Análises/ciências e prioridades usam esse mesmo calendário para obter a data candidata, com o corte das 12h previsto na parte principal desta skill. Depois, se a `DATA` candidata coincidir com feriado nacional ou feriado local aplicável à filial responsável, antecipar somente a `DATA` do VIOS para o dia de trabalho anterior. Não antecipar por ponto facultativo nem por feriado exclusivo de outro estado/município sem aplicação à filial.
- Identificar uma vez, fora dos resumos: `Contagem solicitada: segunda a sexta, incluindo feriados; vencimentos sem validação do calendário judicial oficial.` Não chamar o resultado de vencimento jurídico oficial confirmado.
- Preservar datas-limite expressamente fixadas pelo juízo e data/hora exatas dos eventos. Prazos em horas ou dias corridos mantêm a unidade e regime próprios, inclusive no Criminal; o calendário simplificado não converte dias corridos em dias úteis.
- A antecipação por feriado não modifica vencimento de referência nem D-2 calculado; registrar o ajuste da `DATA` fora do resumo. Audiência, perícia, sustentação e outro ato com data/hora fixas permanecem na data real, sem antecipação e sem alerta por coincidência com feriado.
- Para o recuo, usar o primeiro dia anterior de segunda a sexta que não seja feriado nacional nem feriado estadual/municipal aplicável à filial. Confirmar em fonte oficial se a data é feriado, ponto facultativo e qual sua abrangência territorial. Se a aplicabilidade estiver incerta, sinalizar a pendência em vez de presumir.
- Se o usuário pedir especificamente validação jurídica oficial, distinguir essa conferência da contagem simplificada e consultar as regras e fontes oficiais do órgão competente.

### Casos especiais

#### Homologação de conciliação no JEC

Verificar o art. 41 da Lei 9.099/95, que exclui essa sentença do recurso ordinário do Juizado. Não aplicar automaticamente dez dias só por se tratar de sentença de JEC. Conferir a natureza da homologação e instrumento; se o documento for insuficiente, registrar cabimento pendente. Não excluir a análise obrigatória da sentença nem a avaliação de embargos/correção por vício específico.

#### Julgamento de embargos

Conferir tempestividade e efeitos dos embargos para avaliar interrupção e novo termo recursal. Novos embargos podem exigir exame de vício próprio da decisão integrativa ou persistência de omissão não sanada. Não usar a frase absoluta “somente por vício novo”; não estimular repetição do mérito ou embargos protelatórios.

#### Honorários recursais

Antes de sugerir omissão ou majoração do art. 85, §11, CPC, conferir honorários previamente fixados em desfavor da parte recorrente e demais requisitos da jurisprudência vigente. Ausência de honorários na origem não gera automaticamente omissão no recurso.

#### Laudo no Previdenciário/JEF

A tarefa é de manifestação sobre laudo, não de comparecimento a perícia ou de análise de sentença. Usar quinze dias do art. 477, §1º, CPC apenas sob premissa de aplicação subsidiária adequada e inexistência de prazo específico no expediente/decisão. Identificar essa premissa quando só houver trecho resumido.

### Apresentar os resultados

Definir primeiro a tarefa pelo filtro de providência concreta da parte principal desta skill. Se o despacho resultar apenas em CIÊNCIA, sem providência atual do cliente nem questão jurídica concreta, não calcular nem inserir controles de embargos/recurso. A exigência de duas datas aplica-se às tarefas de análise jurídica, não a todo expediente intitulado despacho.

Aplicar integralmente os cabeçalhos e datas da parte principal desta skill. Em análise jurídica de sentença/acórdão/decisão, calcular e mostrar ambas as datas em D-2, inclusive como controle preventivo quando houver restrição de cabimento; reservar a decisão ao advogado. Não substituir datas por `NÃO CABE`. Indicar a ressalva jurídica nos campos externos, sem afirmar admissibilidade. Na homologação de conciliação em JEC, conservar a ressalva do art. 41 fora da descrição e não chamar o controle preventivo de recurso validado.

Usar embargos + recurso OU prazo fatal, nunca os três na mesma descrição. Minutas: `PRAZO FATAL D -2:` (exceção de apresentação da minuta prioritária de requisitórios conforme a parte principal desta skill). Análises operacionais com prazo objetivo e sem controle recursal: somente prazo fatal. Preservar prazo de obrigação distinta em campo externo/tarefa própria.

Analisar/ciência: mesmo dia de expediente do escritório até 12h; após 12h, próximo dia de segunda a sexta. Prioridades: próximo dia de segunda a sexta. Aplicar segunda a sexta, inclusive feriados, à contagem e ao D-2; depois, se a `DATA` operacional candidata coincidir com feriado nacional ou local aplicável à filial, antecipá-la para o dia de trabalho anterior. Ponto facultativo e feriado exclusivo de outra localidade não provocam recuo. Audiência/perícia/sustentação: data e hora exatas do ato; inscrição/envio são prazos preparatórios separados. Se faltarem elementos de cálculo ou dados necessários de ID/evento/expediente, bloquear a tarefa e listar a pendência fora do arquivo. Não afirmar que editar a Skill alterou o programa do bot.

## Referência — Validação para lançamento e comparação com o bot

Estas são instruções de triagem e revisão. Não afirmar que o bot já executa estas regras nem que seus arquivos foram alterados sem acesso e modificação reais do programa.

### Antes de finalizar

Conferir uma linha por CI com cliente, destinatário, ato/ID, natureza, fase, departamento/fonte, auxiliar, tarefa principal/complementares, responsável, prazo expresso/legal, termo inicial, calendário, vencimento jurídico, data operacional, prioridade, duplicidade e status.

Corrigir inconsistência interna detectável. Se a solução exigir documento/dado ausente, registrar pendência e prosseguir nas demais CIs. Não esconder incerteza apenas para produzir uma tarefa lançável.

### Não lançar a CI/tarefa afetada

- Teor ausente, comunicação que só aponta evento (“Evento 23 — PETIÇÃO”), ou impossibilidade de escolher tarefa sem abrir o evento. Não usar ciência como substituto. Ressalvar a inclusão expressamente solicitada de análise de sentença quando o evento informa inequivocamente o resultado, conforme a parte principal desta skill: não inventar dispositivo nem valores.
- Cliente/vínculo/posição processual ainda não identificados com segurança.
- Departamento/responsável incerto ou divergência não resolvida. Aplicar antes as correções autorizadas: Carlos trabalhista → Johnys; Tamira previdenciário → Suhiane; responsável Tamira em Execução → tarefa de Execução. Nunca usar `automático` nem atribuir a Amanda Leite Mendes ou Sarah/Controladoria. Usar primeiro o advogado auxiliar; se ele não existir, usar o advogado responsável. Exceção: se não houver auxiliar e o responsável for Ronielle Feitosa, bloquear a tarefa e sinalizar à usuária para verificar o auxiliar ou o responsável correto. Qualquer outro advogado responsável identificado pode receber a tarefa.
- `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` sem cidade/filial inequivocamente identificada entre Camocim, Tianguá, Jijoca de Jericoacoara/Jijoca e Sobral. Somente essa tarefa deve ser atribuída ao responsável da filial e nunca a Amanda Leite Mendes ou Suiane/Suhiane. Esta regra não se estende a qualquer outra tarefa. Se a filial não puder ser determinada, registrar `NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL DA PERÍCIA MÉDICA JUDICIAL.`
- Audiência sem tipo/modelo, data, hora, formato ou link/local; perícia com comparecimento sem data/hora/local; sustentação sem data/horário ou outros dados indispensáveis ao cadastro. Em sustentação e viabilidade, link/local são opcionais e sua ausência não bloqueia o TXT. ID e senha são opcionais: sua ausência, por si só, não bloqueia audiência. Omitir campos ausentes sem afirmar acesso livre. Listar precisamente os dados essenciais faltantes.
- Tarefa com horário sem horário confirmado. Exceção: aviso/instrução social possuem data operacional própria e podem existir sem data/hora da visita.
- Prazo necessário ao lançamento sem termo inicial ou duração identificados; a falta de calendário oficial não bloqueia a contagem simplificada. Preservar controle preventivo identificado, sem chamá-lo de vencimento validado.
- Tarefa não definida, nome não confirmado na lista oficial ou recurso/agravo de recorrente desconhecido. Isso é bloqueio, não simples alerta com lançamento.
- Duplicidade confirmada: não gerar outra tarefa. Duplicidade provável: conferir ID/teor antes de descartar a CI; não eliminar comunicação válida do cliente por hipótese.
- Falta de tarefa complementar obrigatória: corrigir a análise antes de finalizar. Se algum dado da complementar depender de conferência, indicá-la explicitamente como pendente; não considerá-la dispensada.

Esses bloqueios restringem o lançamento da tarefa afetada, não impedem entregar a revisão e as demais análises. Não acessar/escrever no VIOS ou outro serviço sem autorização e ferramentas apropriadas. Solicitação apenas de análise não comprova lançamento.

### Alertas com contexto

- Feriados e suspensões: contar como dias úteis na contagem simplificada. Depois de obter a `DATA` operacional candidata, verificar em fonte oficial somente se ela coincide com feriado nacional ou feriado estadual/municipal aplicável à filial responsável. Nessa coincidência, antecipar a `DATA` para o dia de trabalho anterior. Não antecipar por ponto facultativo nem por feriado exclusivo de outro estado/município. Indicar uma vez, fora dos resumos, o critério solicitado e a ausência de validação do calendário judicial oficial.
- Ato mais próximo do que a data operacional preparatória: antecipar o trabalho e justificar.
- Divergência de grafia de cliente comprovadamente identificado: registrar a prova; não presumir equivalência de outras empresas.
- Se a informação necessária depender de leitura de ID/evento/expediente ainda não disponível, não lançar a tarefa afetada; a Controladoria confere primeiro. Não criar tarefa para suprir essa falta.

### Checagem das datas

- Antes de calcular recursos, conferir se o ato é somente ciência pelo filtro de providência concreta. Suspensão de obrigação com consulta/diligência a cargo do juízo, sem providência atual do cliente nem questão jurídica concreta, não gera análise ou prazos recursais por cautela abstrata. Preservar hipóteses específicas de análise obrigatória.

- Análise e ciência: mesmo dia de expediente do escritório até 12h; após 12h ou fora de expediente, próximo dia de segunda a sexta, ressalvadas prioridades e urgência concreta. Se a data operacional candidata coincidir com feriado oficial aplicável, antecipar para o dia de trabalho anterior, salvo impossibilidade temporal já consumada, que deve ser sinalizada como urgência/atraso sem backdating fictício.
- RPV e prioridades SUH: primeiro dia de expediente do escritório seguinte. Cabeçalho da descrição controla D-2; não é a data de lançamento prioritário.
- Regra geral: D-2 retrocedendo dois dias de segunda a sexta, inclusive feriados; excluir apenas sábados e domingos. Se a `DATA` operacional resultante for feriado aplicável, antecipá-la sem alterar o D-2 calculado nos controles.
- Eventos com horário: dia e hora exatos nos campos do VIOS e na descrição; sessão virtual no início. Término e prazo de envio/inscrição ficam fora da descrição curta.
- Feriado nacional ou local aplicável: recuar até o primeiro dia anterior de segunda a sexta que não seja feriado aplicável. Feriado de outro estado/município não aplicável e ponto facultativo não alteram a `DATA`. Confirmar classificação e abrangência em fonte oficial; se incertas, registrar pendência objetiva.
- Ciência: não inventar vencimento.
- Nenhum agendamento interno pode alongar prazo jurídico ou ocultar atraso.
- Recalcular de forma independente quando o bot apresentar data. Conta correta não confirma termo inicial, cabimento nem calendário.

### Fechamento da resposta

Informar por CI se está pronta, duplicada ou pendente, sem misturar conclusões. Na revisão, separar erro confirmado, inconsistência, provável duplicidade e pendência documental. Não repetir avisos obsoletos quando a fonte oficial já foi localizada.

Excluir do arquivo importável todas as tarefas bloqueadas. Entregar no chat uma lista separada por CI/processo com o dado faltante e a consulta necessária. Conferir descrições curtas, responsáveis fora do resumo e cabeçalhos exclusivos: duas datas recursais OU prazo fatal. Confirmar que nenhuma `DATA` operacional ajustável permaneceu em feriado oficial aplicável, sem alterar datas fixas de atos. Confirmar também que nenhum campo `RESPONSÁVEIS` contém `automático` ou AMANDA LEITE MENDES e que toda tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` usa o responsável da filial, sem Suiane/Suhiane. Não omitir CIs da conferência interna.

No pagamento cível, conferir somente análise e minuta. Excluir tarefa separada de contato com o cliente, pois esse contato já é gerado automaticamente pelo fluxo da análise.

### Exportação TXT para o bot

Aplicar `saida-txt-bot.md` em toda análise de CSV/Excel do VIOS: um único TXT UTF-8 no modelo institucional, somente com tarefas prontas. Pendências de leitura no sistema e duplicadas ficam fora do TXT, identificadas no chat por CI/processo. Verificar que nenhuma tarefa bloqueada foi exportada e explicar cada exclusão. A usuária realiza a consulta e o cadastro manuais das pendências.

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
- `RESPONSÁVEIS` em branco, `automático` ou AMANDA LEITE MENDES (o VIOS manda a tarefa para a Amanda, que só lança).
- Responsável único RONIELLE FEITOSA (RONEELY FEITOSA no VIOS): sem auxiliar e com ele como responsável a tarefa não vai no arquivo.
- `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` sem o responsável da filial (Camocim, Tianguá, Jijoca ou Sobral).
- Descrição vazia ou linha solta antes de `DESCRIÇÃO:`.
- CI já lançada pelo robô antes, ou que já tem tarefa ativa no VIOS.
- CI que é cópia de outra (mesmo processo e mesmo teor): se a original está no arquivo ou já foi lançada, a cópia não é gravada; se não, vira erro para a Controladoria conferir.

Avisos (a CI é lançada, mas a página mostra para conferir): data já passada, data em sábado ou domingo, e linhas `Responsável a marcar na tarefa` / `Advogada auxiliar` na descrição (responsáveis vão no campo `RESPONSÁVEIS`).

### Número do processo

- Cada CI mostra o número do processo na página de envio. Vem do campo `PROCESSO:` do arquivo; sem ele, do número capturado do VIOS (campo Números ou, se vazio, o teor da intimação). Sem nenhum dos dois, ou fora do padrão `0000000-00.0000.0.00.0000`, a página avisa (a CI ainda é lançada). Número do arquivo diferente do capturado também vira aviso.
- Na análise do robô, o número sai sempre que estiver no campo Números ou no teor (aceita os 20 dígitos sem pontos); só fica `PENDENTE` quando não aparece em lugar nenhum.

### Como o robô preenche a tarefa no VIOS

- Tarefa, data, horário (campo Horário do VIOS) e descrição na Observação.
- Descrição toda em negrito; as linhas `PRAZO FATAL:`, `PRAZO FATAL D -2:`, `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:` em negrito e vermelho, junto com a data. O teor da intimação que o VIOS acrescenta fica normal.
- `RESPONSÁVEIS`: o robô marca exatamente as pessoas do arquivo, como estão no VIOS (veja o que ele bloqueia acima). Na petição da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- `CIÊNCIA` com `DATA:` vazia vai para o dia do envio.
- **Corte das 12h na hora do lançamento:** `CIÊNCIA` e `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` com data de hoje (ou ciência sem data) lançadas depois das 12:00, ou no sábado/domingo, vão para o próximo dia de segunda a sexta (sexta 12:01 → segunda). Só a data da tarefa muda; `PRAZO PARA EMBARGOS`, `PRAZO PARA RECURSO` e `PRAZO FATAL` da descrição ficam como estão. Se alguma dessas datas vier antes do novo dia, a tarefa fica para hoje (urgente). Data já futura no arquivo não é mexida.
- Duas tarefas da mesma CI são gravadas juntas e conferidas na tela de conferência do VIOS.

### Duplicidade

- A mesma publicação em mais de uma CI: a mais completa é a original (primeiro a endereçada ao cliente, depois a de texto maior, depois a de número menor); a outra não gera tarefa.
- O mesmo processo com atos diferentes não é duplicidade: cada CI tem a sua tarefa.

### Feriado na DATA da tarefa

Quando a `DATA` operacional de uma tarefa cai em feriado nacional (ou do estado/município do escritório, se configurado), o robô
da análise pela API recua só a `DATA` para o dia de trabalho anterior, como a skill manda; o D-2 e os vencimentos da descrição
não mudam. Audiência, perícia e sustentação oral ficam na data real. No arquivo do chat a `DATA` já deve vir ajustada; o robô só
confere de novo a data que o corte das 12h empurra para o próximo dia de segunda a sexta.

## Arquivo para o robô (.txt)

Depois da análise, sempre entregar também o **arquivo para o robô**: um único bloco de código (```text) com as tarefas no formato abaixo. A Controladoria confere e ajusta, salva como `.txt` e sobe na página de envio; o robô lança exatamente o que estiver no arquivo, sem refazer a análise.

Formato — um bloco por tarefa, separados por uma linha só com `---`:

```text
CI: 42484
PROCESSO: 0000123-45.2026.8.06.0001
TAREFA: MINUTAR PETIÇÃO (EXECUÇÃO) 2026
DATA: 29/10/2026
HORA:
RESPONSÁVEIS: TAMIRA LOIOLA, BRENO SILVA MOTA
DESCRIÇÃO:
PRAZO FATAL: 02/11/2026
MINUTAR PETIÇÃO PARA INFORMAR OS DEMAIS DADOS NECESSÁRIOS PARA A CONFECÇÃO DOS REQUISITÓRIOS (RPV/PRECATÓRIO)
Despacho: considerando a certidão de ID 192859275, intime-se a parte exequente para, no prazo de 5 dias, informar os demais dados necessários para a confecção dos requisitórios.
---
CI: 42502
PROCESSO: 0000456-78.2026.5.07.0001
TAREFA: AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026
DATA: 22/01/2027
HORA: 08:20
RESPONSÁVEIS: NOME COMPLETO DO ADVOGADO AUXILIAR
DESCRIÇÃO:
AUDIÊNCIA UNA
DATA: 22/01/2027
HORA: 08:20
FORMATO: TELEPRESENCIAL (ZOOM)
LINK/LOCAL: https://trt7-jus-br.zoom.us/j/85164513045
ID da reunião: 851 6451 3045
SENHA: 355957
---
CI: 42491
PROCESSO: 0000789-01.2025.8.06.0001
TAREFA: ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026
DATA: 29/10/2026
HORA:
RESPONSÁVEIS: NOME COMPLETO DO ADVOGADO AUXILIAR
DESCRIÇÃO:
PRAZO DE EMBARGOS: 02/11/2026
PRAZO DE RECURSO: 16/11/2026
SENTENÇA
[dispositivo]
```

No exemplo, as três intimações foram publicadas em 28/10/2026. Na 42484 (dados para requisitórios, prazo de 5 dias), a `DATA` é a prioridade (próximo dia de segunda a sexta) e o `PRAZO FATAL` é o D-2 do vencimento de referência (04/11/2026). Na 42491, embargos (5 dias) vencem em 04/11 e recurso (15 dias) em 18/11; as linhas mostram o D-2 de cada um.

Regras do arquivo:

- `CI`: só o número da CI do VIOS.
- `PROCESSO`: **sempre** o número do processo da CI no padrão CNJ (`0000000-00.0000.0.00.0000`), como está no campo Números da intimação (ou no teor). A página de envio mostra esse número em cada CI; se faltar, ela usa o número capturado do VIOS e avisa quando não acha nenhum.
- `TAREFA`: o nome exato da lista oficial (seção "Referência — Tarefas VIOS e Modelos de Descrição").
- `DATA`: a data da tarefa no VIOS (DD/MM/AAAA), já calculada pelas regras de data da skill (D-2; prioridade RPV/Suhiane no próximo dia de segunda a sexta; análise e ciência no mesmo dia até 12h ou no próximo dia depois das 12h; data exata do ato), sempre com a contagem simplificada (só sábado e domingo ficam de fora). Se a data ajustável cair em feriado nacional ou local da filial, a skill manda antecipar para o dia de trabalho anterior (só a `DATA`; o D-2 da descrição não muda). Só `CIÊNCIA` pode ficar com `DATA:` vazia (vai para o dia do envio).
- `HORA`: HH:MM em audiência, perícia e sustentação oral (na sessão virtual, o horário de início); vazia nas demais tarefas.
- `RESPONSÁVEIS`: **nunca `automático`** (o VIOS manda a tarefa para AMANDA LEITE MENDES, que só lança e não executa). Nome completo do advogado auxiliar, como aparece no VIOS; sem auxiliar, o advogado responsável pelo processo (exceto RONIELLE FEITOSA: sem auxiliar e com ele como responsável, a tarefa fica fora do arquivo). Na `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, o responsável da filial (Camocim, Tianguá, Jijoca ou Sobral). Vários nomes separados por vírgula. Na petição da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- `DESCRIÇÃO`: sempre a última linha de campo; tudo abaixo dela vai para a Observação da tarefa, exatamente como escrito. Incluir os cabeçalhos de prazo da skill seguidos do texto do modelo da tarefa: `PRAZO DE EMBARGOS:` e `PRAZO DE RECURSO:` na análise jurídica de sentença/acórdão/decisão; `PRAZO FATAL D -2:` nas minutas; `PRAZO FATAL:` + `PRIORIDADE RPV` nas prioridades de RPV/precatório (exceto a minuta de dados de requisitórios, como no exemplo). Nunca os três cabeçalhos juntos. Não incluir `Responsável a marcar na tarefa` nem `Advogada auxiliar` (responsáveis vão em `RESPONSÁVEIS`).
- Duas tarefas da mesma CI (ex.: verificar viabilidade de sustentação + sustentação oral): dois blocos seguidos com o mesmo `CI`.
- **Não colocar no arquivo**: CI duplicada (vale a original), CI que não deve ser lançada (falta informação, evento sem teor, área divergente do auxiliar, tarefa pendente de definição). Listar essas CIs fora do bloco, com o motivo, para a Controladoria tratar à mão.
