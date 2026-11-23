# POP e fluxo de intimações

Índice: providência; pagamentos; audiências; perícias; sustentação; recursos genéricos.

## Providência principal

Aplicar primeiro as regras do SKILL.md e o roteamento, incluindo prioridade, duplicidade e dados indispensáveis. A Controladoria define tarefas para o advogado saber o que ocorreu e como agir.

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

Aplicar primeiro o filtro de providência concreta do SKILL.md, inclusive antes da regra genérica de análise de decisão favorável. Preservar as análises obrigatórias de sentença/acórdão e demais hipóteses específicas. Não abrir recurso diretamente quando depender de avaliação. Não transformar prazo da parte contrária em tarefa de pagamento/minuta para o cliente.

## Pagamentos pelo cliente

### Trabalhista

Indicar primeiro `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (TRABALHISTA) 2026` ou análise oficial equivalente. Incluir natureza e prazo do pagamento. Não indicar ciência, guia ou minuta inicial. A análise gera contato para avisar o cliente e consultar se deseja pagar; só depois seguir guia autorizada, pagamento e tarefa de comprovação. Abranger custas, preparo, depósito recursal/judicial e honorários periciais.

### Cível

Indicar somente duas tarefas:

1. `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO (CÍVEL) 2026` ou análise oficial pertinente;
2. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/EMENDA/IMPUGNAÇÃO (CÍVEL) 2026`, para comprovar pagamento/depósito/recolhimento.

A análise já gera automaticamente o contato com o cliente no VIOS. Não abrir nem incluir no arquivo a tarefa `ENTRAR EM CONTATO COM O CLIENTE 2026` para duplicar esse fluxo. Não aguardar o contato para indicar a minuta. Abranger parcelamento de custas e demais pagamentos a cargo do cliente. Não gerar o conjunto se o obrigado for apenas a parte contrária. Preservar prazo jurídico e data própria de cada tarefa.

## Audiências

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

## Perícias

```text
TIPO:
DATA:
HORA:
LOCAL/LINK:
```

### Médica previdenciária

Indicar duas tarefas em blocos próprios:

1. `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026`, na data e horário exatos;
2. `MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026`, para quesitos e assistente técnico.

Para a segunda, usar prazo específico confirmado ou marcar pendência. Se o ato apenas designar a perícia, ainda indicar a complementar com prazo pendente; não presumir data. Não confundir com manifestação sobre laudo já produzido.

### Social previdenciária

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

## Sustentação oral

Indicar viabilidade da área conforme o corte das 12h para análise e sustentação oficial para a data/hora exatas do ato. Na sessão virtual, agendar no primeiro dia. Guardar término da sessão e prazo de inscrição/envio nos campos externos, sem incluí-los na descrição curta nem substituir o início da sessão pelo limite de envio.

```text
SUSTENTAÇÃO ORAL
DATA: [data inicial da sessão]
HORA: [horário inicial]
LINK:
```

Link/local são opcionais tanto na viabilidade quanto na sustentação: omitir o campo quando ausente, manter data e horário confirmados e incluir as tarefas no TXT sem exigir nova dispensa. Não inventar endereço, afirmar acesso livre ou tratar a agenda como confirmação de cabimento/inscrição. A análise de viabilidade permite ao advogado avaliar as regras do recurso e da sessão. Continuam indispensáveis os demais dados que determinam o cadastro, como processo, cliente, responsável, data e horário da sessão. Não afirmar que a sustentação foi realizada por apenas agendá-la.

## Recurso/agravo trabalhista genérico

Conferir no PJe quem recorreu e o objeto da intimação antes de escolher a tarefa:

- Recurso da parte contrária com resposta determinada/cabível: `MINUTAR RECURSO/CONTRARRAZÕES AO RECURSO (TRABALHISTA) 2026`.
- Recurso apenas do cliente, sem outra providência: `CIÊNCIA (TRABALHISTA) 2026`.
- Recursos de ambos: identificar peça contrária a responder; havendo resposta exigida, minuta correspondente; não havendo providência, ciência.
- Se não identificável: `NÃO ABRIR TAREFA AINDA - CONFERIR NO PJE QUEM INTERPÔS O AGRAVO/RECURSO PARA DEFINIR SE É MINUTAR OU CIÊNCIA`.

Não criar tarefa ao advogado apenas para buscar o dado necessário à triagem. Não presumir abertura de contrarrazões da simples notícia de interposição.

## Exemplos de descrições aprovadas

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
