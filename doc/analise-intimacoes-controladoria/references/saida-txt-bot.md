# Saída institucional para o bot de automação VIOS

## Entrada e destino

Receber o CSV exportado do VIOS, ainda que a usuária o chame de Excel, ou a planilha Excel equivalente. Conferir todas as linhas/CIs. Gerar um único `analise_AAAA-MM-DD.txt`, em UTF-8, com as tarefas prontas. A usuária enviará o TXT a um endereço IP de seu bot, que executará o cadastro no VIOS. Não solicitar IP nem enviar arquivo ao bot: esta rotina prepara o arquivo para a usuária.

## Modelo obrigatório

Usar a estrutura de `assets/pedido-arquivo-robo.txt`, atualizada conforme a orientação posterior da usuária sobre responsáveis. Esse modelo substitui o relatório antigo `assets/modelo-analise-vios.md` para automação. O arquivo será executado como está: não incluir introdução, Markdown, cercas de código, links de lançamento, cliente, explicações jurídicas, totais ou pendências como campos extras.

Um bloco por tarefa, com estes sete campos obrigatórios nesta ordem, um por linha:

```text
CI: [somente o número]
PROCESSO: [número do processo da CI, no padrão 0000000-00.0000.0.00.0000]
TAREFA: [nome exato da lista oficial do VIOS]
DATA: [DD/MM/AAAA]
HORA: [HH:MM ou vazio]
RESPONSÁVEIS: [nomes completos separados por vírgula]
DESCRIÇÃO:
[texto da tarefa, com quantas linhas forem necessárias]
```

Entre dois blocos, usar uma linha contendo somente `---`. Tudo após `DESCRIÇÃO:` até o separador será gravado na Observação da tarefa. Não inserir comentários nesse intervalo. Não inserir uma linha isolada `---` dentro da descrição.

- Preservar a ordem das CIs da exportação. Se houver duas ou mais tarefas da mesma CI, gerar blocos consecutivos com a mesma CI, cada qual com seus próprios campos.
- `DATA` é a data operacional da tarefa, com D-2, prioridade, corte das 12h ou data do ato conforme a skill. Somente CIÊNCIA pode ter DATA vazia; preferir a data calculável conforme a rotina. Não usar vencimento jurídico bruto no lugar da data operacional.
- Sustentação e viabilidade: inserir link/local somente quando disponível; omitir o campo quando ausente, sem bloquear o TXT nem inventar acesso. Preservar data e horário da sessão e avaliar cabimento na tarefa de viabilidade.
- `HORA` é obrigatória em audiência, perícia com comparecimento e sustentação oral (início da sessão virtual). Nas demais tarefas, deixar vazia. Aviso/instrução social não é o comparecimento à perícia.
- `RESPONSÁVEIS`: identificar a abreviação na coluna `Auxiliares` do CSV e usar o nome completo correspondente da tabela abaixo, nunca `automático` ou a abreviação. Preservar a exceção de petição intermediária da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- Para a tarefa de comparecimento à perícia médica, usar o responsável da filial indicada e mapeada em `pop-fluxo-intimacoes.md`, em vez do advogado auxiliar. Se a filial não estiver informada ou mapeada, incluir a tarefa com `RESPONSÁVEIS: incluir responsável pela cidade identificada`, desde que os demais dados indispensáveis estejam disponíveis. Essa é uma exceção autorizada à exigência de nome completo nesse campo.
- `DESCRIÇÃO`: primeiro as linhas de prazo aplicáveis, depois o resumo/modelo curto da tarefa. Análise jurídica: `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:`, ambos com datas D-2 calculadas conforme a skill. Minuta: `PRAZO FATAL D -2:`; preservar `PRAZO FATAL:` no modelo prioritário de requisitórios. Não adicionar responsáveis, auxiliares, instruções de cadastro nem marcadores `PRIORIDADE ...` na descrição.
- Audiência: `AUDIÊNCIA [TIPO]`, `DATA:`, `HORA:`, `FORMATO:`, `LINK/LOCAL:`, `ID da reunião:` e `SENHA:`, uma informação por linha, conforme os dados disponíveis; não inventar ID/senha nem acrescentar OBS genérica.

## Advogados auxiliares no TXT

Tabela fornecida pela usuária para traduzir a coluna `Auxiliares`:

| Abreviação | Nome completo no campo RESPONSÁVEIS |
| --- | --- |
| CARL | FRANCISCO JOHNYS VASCONCELOS BARBOSA; para cliente CALTECH, CARLOS AUGUSTO ALVES CAMILO BRANDÃO |
| JOHN | FRANCISCO JOHNYS VASCONCELOS BARBOSA |
| IANN | IANNA BRENA MARIANO SILVA |
| JOAN | JOANA CLÁUDIA DOTTO |
| JOAQ | JOAQUIM JOSÉ DO NASCIMENTO NETO |
| LILI | LILIAN YNARYA DE ARAÚJO NASCIMENTO |
| SUH | SUHIANE DE MARIA GOMES SILVA |
| TAMI | TAMIRA LOIOLA |

- `CARL` identifica CARLOS AUGUSTO ALVES CAMILO BRANDÃO no cadastro, mas por orientação da usuária as tarefas com esse código são atribuídas ao advogado `JOHN`, FRANCISCO JOHNYS VASCONCELOS BARBOSA. Única exceção: se o cliente for CALTECH, atribuir a CARLOS AUGUSTO ALVES CAMILO BRANDÃO. Escrever somente o nome completo do advogado no TXT, não os códigos. Em caso de dúvida sobre a identificação do cliente como CALTECH, não presumir a equivalência; registrar a pendência de confirmação fora do TXT.
- Normalizar espaços ao ler a abreviação; não alterar a grafia do nome completo. Os códigos não vão para o TXT.
- Sem auxiliar, identificar o advogado responsável no arquivo e preencher seu nome completo confirmado. Se o único responsável for RONEELY FEITOSA, não atribuir a ele: excluir a tarefa do TXT e pedir à Controladoria o advogado que deverá recebê-la. Nome incompleto, abreviação desconhecida ou responsável não identificado também bloqueiam a tarefa até confirmação.
- Nunca atribuir tarefa de intimação a Amanda Leite Mendes. Em exceções de tarefa específica já confirmadas, preservar os responsáveis adicionais; não incluir Breno em tarefas que não sejam petições intermediárias da Execução da Tamira.
- Uma correção específica de auxiliar expressamente confirmada para a CI ou carteira prevalece sobre cadastro antigo. Aplicar a regra geral `CARL` para `JOHN` acima. Se houver divergência concreta não resolvida entre auxiliar, área e tarefa, bloquear a tarefa e informar a pendência fora do TXT.
- Aplicar a análise e os ajustes atuais da usuária; não copiar datas, dados nem tarefas dos exemplos como se pertencessem ao lote novo. Se a análise já estiver ajustada e o pedido for apenas gerar o arquivo, preservar as decisões e textos aprovados.

## Separação entre automação e consulta manual

- Incluir no TXT apenas tarefa definida com segurança, com nome oficial, cliente/área/roteamento identificados e todos os dados indispensáveis ao cadastro preenchidos.
- Se for preciso abrir PJe, VIOS ou outro sistema para ler decisão, ID, evento, expediente, laudo ou verificar dado que determina a tarefa, excluir a tarefa afetada do TXT. Não adivinhar, indicar ciência/análise genérica, ou criar tarefa para mandar o advogado descobrir qual tarefa abrir. A ausência da filial não bloqueia a tarefa de comparecimento à perícia médica quando usado o texto específico autorizado no campo RESPONSÁVEIS.
- A consulta manual será feita pela usuária, que definirá e cadastrará a tarefa manualmente. Não condicionar a entrega das demais CIs a essa consulta.
- Se a mesma CI tiver tarefa pronta independente e outra bloqueada, exportar somente a pronta e identificar expressamente no chat o que já consta no TXT e o que fica manual, para evitar repetição. Se a incerteza afetar todo o enquadramento da CI, excluir o bloco inteiro.
- Não bloquear apenas porque o advogado precisará ler os autos para executar uma providência já inequívoca: distinguir leitura necessária para definir/cadastrar a tarefa de leitura normal para elaborar a peça. Aplicar os bloqueios de `validacao-lancamento.md`.
- Excluir duplicadas confirmadas do TXT e informar no chat qual CI manter e qual é redundante. Não presumir autorização para apagar registros ou executar o bot.
- Jamais inserir `PENDENTE`, `CONFERIR NO SISTEMA`, campos indispensáveis em branco (salvo HORA nas tarefas sem horário e DATA de CIÊNCIA, permitidos pelo modelo), alternativas de tarefas ou registros duplicados como comandos importáveis. Não esconder nem apagar da conferência as CIs excluídas.

## Pendências fora do arquivo — padrão habitual

Apresentar diretamente na conversa, sem segundo arquivo, uma entrada por CI/processo, na ordem original:

**CI [número] — Processo [número]**
Cliente: [identificado, se disponível].
Do que se trata: [o que o CSV permite concluir].
Tarefa no VIOS: NÃO DEFINIDA — CONSULTA MANUAL NECESSÁRIA [ou nome da tarefa bloqueada se já conhecido].
Conferir no sistema: [ID/evento/documento e exatamente qual informação falta e por que ela altera o cadastro].
Prazos/datas identificados: [somente os calculáveis e sua base; explicitar o que não foi possível calcular].
Status: FORA DO TXT — a usuária consultará o sistema e definirá/cadastrará manualmente a tarefa.

Quando a tarefa não puder ser definida, não oferecer nome ou data fictícios só para preencher o padrão. Manter a análise habitual e todos os dados seguros disponíveis. Entregar pendências em bloco único, sem intercalar pedidos de esclarecimento para cada CI.

## Fechamento e conferência

Conferir correspondência entre cada tarefa no TXT, sua CI/processo, datas e descrição; validar os sete campos, sua ordem e os separadores antes da entrega. Contabilizar separadamente CIs recebidas, CIs incluídas, tarefas incluídas, CIs exclusivamente manuais e duplicadas, destacando CIs parcialmente exportadas. Toda CI original deve estar contemplada na conferência, ainda que fora do TXT. Nunca confundir quantidade de tarefas com quantidade de intimações. Entregar o TXT e as pendências na mesma resposta. Se nenhuma tarefa estiver pronta, informar isso e apresentar as pendências; não fabricar TXT com comandos indefinidos. Preservar o arquivo final conforme a skill Library ao produzir a entrega.
