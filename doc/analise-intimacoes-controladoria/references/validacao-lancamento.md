# Validação para lançamento e comparação com o bot

Estas são instruções de triagem e revisão. Não afirmar que o bot já executa estas regras nem que seus arquivos foram alterados sem acesso e modificação reais do programa.

## Antes de finalizar

Conferir uma linha por CI com cliente, destinatário, ato/ID, natureza, fase, departamento/fonte, auxiliar, tarefa principal/complementares, responsável, prazo expresso/legal, termo inicial, calendário, vencimento jurídico, data operacional, prioridade, duplicidade e status.

Corrigir inconsistência interna detectável. Se a solução exigir documento/dado ausente, registrar pendência e prosseguir nas demais CIs. Não esconder incerteza apenas para produzir uma tarefa lançável.

## Não lançar a CI/tarefa afetada

- Teor ausente, comunicação que só aponta evento (“Evento 23 — PETIÇÃO”), ou impossibilidade de escolher tarefa sem abrir o evento. Não usar ciência como substituto.
- Cliente/vínculo/posição processual ainda não identificados com segurança.
- Departamento/responsável incerto ou divergência não resolvida. Aplicar antes as correções autorizadas: Carlos trabalhista → Johnys; Tamira previdenciário → Suhiane; responsável Tamira em Execução → tarefa de Execução. Nunca atribuir a Sarah/Controladoria.
- Audiência sem tipo/data/hora/formato/local ou dados de acesso exigidos (link, ID, senha); perícia com comparecimento sem data/hora/local; sustentação sem dados indispensáveis. Listar precisamente o que falta para conferência no PJe. Não presumir que ausência de senha significa acesso livre.
- Tarefa com horário sem horário confirmado. Exceção: aviso/instrução social possuem data operacional própria e podem existir sem data/hora da visita.
- Prazo necessário ao lançamento sem termo inicial ou duração identificados; a falta de calendário oficial não bloqueia a contagem simplificada. Preservar controle preventivo identificado, sem chamá-lo de vencimento validado.
- Tarefa não definida, nome não confirmado na lista oficial ou recurso/agravo de recorrente desconhecido. Isso é bloqueio, não simples alerta com lançamento.
- Duplicidade confirmada: não gerar outra tarefa. Duplicidade provável: conferir ID/teor antes de descartar a CI; não eliminar comunicação válida do cliente por hipótese.
- Falta de tarefa complementar obrigatória: corrigir a análise antes de finalizar. Se algum dado da complementar depender de conferência, indicá-la explicitamente como pendente; não considerá-la dispensada.

Esses bloqueios restringem o lançamento da tarefa afetada, não impedem entregar a revisão e as demais análises. Não acessar/escrever no VIOS ou outro serviço sem autorização e ferramentas apropriadas. Solicitação apenas de análise não comprova lançamento.

## Alertas com contexto

- Feriados e suspensões: contar como dias úteis na contagem simplificada; não pesquisar nem exigir calendário oficial para esse cálculo. Indicar uma vez, fora dos resumos, o critério solicitado e a ausência de validação do calendário judicial oficial.
- Ato mais próximo do que a data operacional preparatória: antecipar o trabalho e justificar.
- Divergência de grafia de cliente comprovadamente identificado: registrar a prova; não presumir equivalência de outras empresas.
- Se a informação necessária depender de leitura de ID/evento/expediente ainda não disponível, não lançar a tarefa afetada; a Controladoria confere primeiro. Não criar tarefa para suprir essa falta.

## Checagem das datas

- Análise e ciência: mesmo dia de expediente do escritório até 12h; após 12h ou fora de expediente, próximo dia de expediente do escritório, ressalvadas prioridades e urgência concreta. Feriados não são excluídos do agendamento nem da contagem simplificada.
- RPV e prioridades SUH: primeiro dia de expediente do escritório seguinte. Cabeçalho da descrição controla D-2; não é a data de lançamento prioritário.
- Regra geral: D-2 retrocedendo dois dias de segunda a sexta, inclusive feriados; excluir apenas sábados e domingos.
- Eventos com horário: dia e hora exatos nos campos do VIOS e na descrição; sessão virtual no início. Término e prazo de envio/inscrição ficam fora da descrição curta.
- Ciência: não inventar vencimento.
- Nenhum agendamento interno pode alongar prazo jurídico ou ocultar atraso.
- Recalcular de forma independente quando o bot apresentar data. Conta correta não confirma termo inicial, cabimento nem calendário.

## Fechamento da resposta

Informar por CI se está pronta, duplicada ou pendente, sem misturar conclusões. Na revisão, separar erro confirmado, inconsistência, provável duplicidade e pendência documental. Não repetir avisos obsoletos quando a fonte oficial já foi localizada.

Excluir do arquivo importável todas as tarefas bloqueadas. Entregar no chat uma lista separada por CI/processo com o dado faltante e a consulta necessária. Conferir descrições curtas, responsáveis fora do resumo e cabeçalhos exclusivos: duas datas recursais OU prazo fatal. Não omitir CIs da conferência interna.

No pagamento cível, conferir somente análise e minuta. Excluir tarefa separada de contato com o cliente, pois esse contato já é gerado automaticamente pelo fluxo da análise.
