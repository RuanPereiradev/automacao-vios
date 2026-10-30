# Roteamento interno, prioridades e duplicidades

## Ordem de decisão

Conferir orientação expressa do usuário, providência concreta, fase atual, departamento responsável, auxiliar, natureza/órgão/CNJ e classe/assunto. Nenhum campo isolado substitui a leitura.

Conferir em conjunto departamento, responsável atual, auxiliar e providência; corrigir cadastro incompatível com o mapeamento institucional abaixo. Não confundir a coluna “Área” de um relatório automático com prova do departamento cadastrado. Tamira efetivamente responsável pela demanda de Execução exige tarefa de Execução. Não confundir esse vínculo com nome lançado por engano em tarefa previdenciária. Não presumir que todo processo contra o INSS permanece no Previdenciário se a transferência interna estiver comprovada.

## Mapeamento operacional

| Auxiliar | Área normalmente relacionada | Conferência |
| --- | --- | --- |
| Joaquim/JOAQ | Cível | Validar eventual transferência para Execução/Tamira |
| Joana/JOAN | Cível | Validar eventual transferência para Execução/Tamira |
| Lili/LILI | Cível | Validar eventual transferência para Execução/Tamira |
| Suhiane/SUH | Trabalhista Reclamante ou Previdenciário | Diferenciar por partes, teor, órgão e CNJ |
| Tamira/TAMI | Execução | Se efetivamente responsável, usar tarefa de Execução; se o caso/tarefa for previdenciário, corrigir para Suhiane |
| Johnys/JOHN | Trabalhista Reclamada | Substituir Carlos/CARL em tarefa trabalhista; Carlos não integra mais o Trabalhista |
| Breno | Petições intermediárias da Execução da Tamira | Marcar como responsável operacional, preservando Tamira como auxiliar |

SUH em processo da Justiça do Trabalho: usar Trabalhista Reclamante, inclusive na fase executiva, salvo transferência interna confirmada. SUH em benefício/INSS: Previdenciário, ressalvada a mesma confirmação. Palavra “execução” ou classe judicial não basta para mudar o setor.

## Divergências e informações ausentes

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

## RPV/precatório

Tratar como prioritários determinação de expedição, minuta, cálculos vinculados, documentos, dados bancários, procuração/contrato, destaque de honorários, retificação, cancelamento, conversão e outras pendências que afetem expedição/conferência/pagamento.

Data: primeiro dia de expediente do escritório seguinte à publicação/recebimento válido. Preservar prazo jurídico e nunca adiá-lo por causa da rotina interna. Essa prioridade prevalece sobre D-2 e sobre a data genérica de análise, salvo providência mais urgente justificada.

Seguir os cabeçalhos do SKILL.md: prazo único em D-2, depois `PRIORIDADE RPV`, depois resumo. Para análise jurídica, usar as duas datas recursais sem terceira linha. Na minuta de dados de requisitório, usar o exemplo específico sem nomes ou marcador final na descrição. O agendamento permanece no próximo dia de expediente do escritório; a data do cabeçalho não se torna vencimento jurídico.

| Etapa | Tarefa |
| --- | --- |
| Decisão determinando futura expedição | Análise da área responsável |
| Dados/documentos/cálculos a apresentar | Minuta oficial apropriada da área |
| Requisitório/minuta já expedido para conferência | `ANALISAR MINUTA PRECATORIO/RPV (EXECUCÃO) 2026`, se setor confirmado |
| Alvará expedido sem providência | Ciência da área; conferir eventual vínculo com RPV |
| Erro/pendência no requisitório | Analisar minuta ou decisão conforme o ato; minutar quando a providência já for objetiva |

## Emenda da Suhiane

Aplicar a toda emenda à inicial com auxiliar SUH, trabalhista ou previdenciária, inclusive opção equivalente oficial. Primeiro dia de expediente do escritório seguinte à publicação/recebimento válido, sem D-2 operacional.

Usar `PRAZO FATAL D -2:` na descrição da minuta e guardar a prioridade em campo próprio. A data de lançamento prioritária não substitui o controle D-2 do prazo judicial.

## Tamira e Breno

Em petições intermediárias da Execução da Tamira, inclusive `MINUTAR PETIÇÃO (EXECUÇÃO) 2026`, preencher os campos de responsável e auxiliar, fora da descrição:

```text
Advogada auxiliar: TAMIRA
Responsável a marcar na tarefa: BRENO
```

Aplicar a dados bancários, documentos, RPV, alvará, prosseguimento, penhora e manifestações intermediárias equivalentes. Não presumir essa atribuição para análise, recursos, homologação/impugnação aos cálculos ou outras tarefas especializadas. Preservar Tamira como auxiliar.

## Duplicidades — conferir manualmente também

1. Agrupar candidatos por processo, sem eliminar nada.
2. Comparar ID da decisão, teor/dispositivo, objeto, datas e destinatários. Mesma decisão publicada para partes diferentes pode produzir duas CIs sem exigir duas tarefas. Pequenas diferenças de redação ou resumos feitos por modelos diferentes não tornam o ato distinto.
3. Mesmo ID e mesmo conteúdo: duplicidade confirmada, ressalvada republicação corretiva ou nova comunicação que modifique o prazo. Se só houver resumos coincidentes sem ID original, classificar como provável e pedir conferência do documento antes de ignorar a CI.
4. Preservar preferencialmente a comunicação própria do cliente, mais completa e válida para seu prazo. Não adotar prazo da publicação dirigida à parte contrária como prazo do cliente.
5. Manter cada CI no bloco e posição originais. Na cópia, escrever `DUPLICADA DA CI [NÚMERO]. Não abrir nova tarefa. Utilizar a tarefa indicada na CI mais completa.` Se provável, escrever `PROVÁVEL DUPLICIDADE — CONFERIR ID/TEOR ANTES DE DESCARTAR`.
6. Se outra CI acrescentar dado útil, incorporar à tarefa existente. Se modificar data/local/prazo por novo ato, analisar cada CI e atualizar a tarefa apropriada; não ignorar a mudança como duplicata.
7. Não confundir tarefas complementares obrigatórias com duplicidade. Não deduplicar laudos, perícias ou despachos padronizados de processos/clientes diferentes.
8. Conferir de forma independente avisos automáticos “ato diferente” e “duplicada”. Não afirmar que o bot detectou corretamente sem confronto dos textos.

## Ausência de responsável

Não atribuir nenhuma tarefa a Sarah Pontes/Controladoria. Se não houver responsável identificável pelas regras institucionais, registrar `RESPONSÁVEL NÃO IDENTIFICADO`, bloquear a tarefa e listar a pendência fora do arquivo. Não presumir responsável de outra área.
