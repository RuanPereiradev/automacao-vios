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
2. Ler [roteamento-interno.md](references/roteamento-interno.md) para departamento, responsável, duplicidades, Breno e prioridades.
3. Ler [pop-fluxo-intimacoes.md](references/pop-fluxo-intimacoes.md) para a providência e tarefas complementares.
4. Usar exclusivamente os nomes de [tarefas-vios.md](references/tarefas-vios.md); sugestões automáticas do VIOS são indícios, não decisões.
5. Ler [regras-prazos-recursos.md](references/regras-prazos-recursos.md) para termo inicial, cabimento, contagem, calendário e D-2.
6. Conferir [validacao-lancamento.md](references/validacao-lancamento.md) antes de concluir ou autorizar lançamento.
7. Consultar arquivos internos disponíveis; usar memória apenas como apoio, nunca como substituta do documento atual.

Privilegiar o documento atual para os fatos do caso. Não tratar uma análise automática anterior como fonte que prevalece sobre lei, ato oficial ou intimação original. Buscar fontes oficiais atuais para validar legislação, cabimento e suspensões quando necessário.

## Fluxo de trabalho

Aplicar também as confirmações de 12/11/2026 em `references/roteamento-interno.md`: Francisco Valdir Ribeiro Marques – EPP = F. V. R. Marques Ltda.; VR Dias Celularia Ltda. = Casa do Celular de Cariacica Ltda. Não repetir essas pendências de vínculo. Observar ainda as correções de cliente/polo das CIs 42898 e 42883, preservando o departamento confirmado.

1. Identificar CI, processo, cliente, partes, posição processual, destinatário, órgão, fase, departamento e auxiliar. O cliente costuma estar na quarta ou quinta coluna: conferir pelo conteúdo.
2. Aplicar também as equivalências confirmadas em 11/11/2026, descritas em `references/roteamento-interno.md`. Reconhecer que AVANTTI SOLUCOES PRESTADORA DE SERVICOS LTDA (MATRIZ), inclusive com a indicação PRESTADORA, e FAMOL COMERCIO DE MOVEIS LTDA (MATRIZ) são a mesma empresa conforme orientação institucional. Reconhecer também ITBN TELEFONIA LTDA (MATRIZ), A M AGUIAR TELEFONIA LTDA e RAV HOLDING LTDA como identificações do mesmo cliente para vínculo operacional, conforme confirmação expressa da usuária em 03/11/2026. Não repetir pendência por essas diferenças; preservar a denominação e posição processual que constam do expediente, sem afirmar identidade de CNPJ ou fusão societária. Não estender a equivalência a outras empresas sem prova. Incorporar correções expressas da usuária sobre cliente, polo e setor; em inventário, não presumir que o inventariado seja cliente. Se o cliente indicado não constar da publicação e não houver equivalência/correção confirmada, registrar a divergência. Reconhecer também as equivalências confirmadas em 04/11/2026: Casa do Celular MG/SP = LM Tech Store Ltda.; Vieira de Araujo e Cia. Ltda. = Araujo & Salomão Ltda. – ME/Funerária Plasfran. Não repetir pendência por essas denominações; consultar o roteamento para preservar o responsável e a identificação documental.
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
