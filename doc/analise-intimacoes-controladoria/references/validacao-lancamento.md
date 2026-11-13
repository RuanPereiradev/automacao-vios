# Validação para lançamento e comparação com o bot

Estas são instruções de triagem e revisão. Não afirmar que o bot já executa estas regras nem que seus arquivos foram alterados sem acesso e modificação reais do programa.

## Antes de finalizar

Conferir uma linha por CI com cliente, destinatário, ato/ID, natureza, fase, departamento/fonte, auxiliar, tarefa principal/complementares, responsável, prazo expresso/legal, termo inicial, calendário, vencimento jurídico, data operacional, prioridade, duplicidade e status.

Corrigir inconsistência interna detectável. Se a solução exigir documento/dado ausente, registrar pendência e prosseguir nas demais CIs. Não esconder incerteza apenas para produzir uma tarefa lançável.

## Não lançar a CI/tarefa afetada

- Teor ausente, comunicação que só aponta evento (“Evento 23 — PETIÇÃO”), ou impossibilidade de escolher tarefa sem abrir o evento. Não usar ciência como substituto. Ressalvar a inclusão expressamente solicitada de análise de sentença quando o evento informa inequivocamente o resultado, conforme o SKILL.md: não inventar dispositivo nem valores.
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

## Alertas com contexto

- Feriados e suspensões: contar como dias úteis na contagem simplificada. Depois de obter a `DATA` operacional candidata, verificar em fonte oficial somente se ela coincide com feriado nacional ou feriado estadual/municipal aplicável à filial responsável. Nessa coincidência, antecipar a `DATA` para o dia de trabalho anterior. Não antecipar por ponto facultativo nem por feriado exclusivo de outro estado/município. Indicar uma vez, fora dos resumos, o critério solicitado e a ausência de validação do calendário judicial oficial.
- Ato mais próximo do que a data operacional preparatória: antecipar o trabalho e justificar.
- Divergência de grafia de cliente comprovadamente identificado: registrar a prova; não presumir equivalência de outras empresas.
- Se a informação necessária depender de leitura de ID/evento/expediente ainda não disponível, não lançar a tarefa afetada; a Controladoria confere primeiro. Não criar tarefa para suprir essa falta.

## Checagem das datas

- Antes de calcular recursos, conferir se o ato é somente ciência pelo filtro de providência concreta. Suspensão de obrigação com consulta/diligência a cargo do juízo, sem providência atual do cliente nem questão jurídica concreta, não gera análise ou prazos recursais por cautela abstrata. Preservar hipóteses específicas de análise obrigatória.

- Análise e ciência: mesmo dia de expediente do escritório até 12h; após 12h ou fora de expediente, próximo dia de segunda a sexta, ressalvadas prioridades e urgência concreta. Se a data operacional candidata coincidir com feriado oficial aplicável, antecipar para o dia de trabalho anterior, salvo impossibilidade temporal já consumada, que deve ser sinalizada como urgência/atraso sem backdating fictício.
- RPV e prioridades SUH: primeiro dia de expediente do escritório seguinte. Cabeçalho da descrição controla D-2; não é a data de lançamento prioritário.
- Regra geral: D-2 retrocedendo dois dias de segunda a sexta, inclusive feriados; excluir apenas sábados e domingos. Se a `DATA` operacional resultante for feriado aplicável, antecipá-la sem alterar o D-2 calculado nos controles.
- Eventos com horário: dia e hora exatos nos campos do VIOS e na descrição; sessão virtual no início. Término e prazo de envio/inscrição ficam fora da descrição curta.
- Feriado nacional ou local aplicável: recuar até o primeiro dia anterior de segunda a sexta que não seja feriado aplicável. Feriado de outro estado/município não aplicável e ponto facultativo não alteram a `DATA`. Confirmar classificação e abrangência em fonte oficial; se incertas, registrar pendência objetiva.
- Ciência: não inventar vencimento.
- Nenhum agendamento interno pode alongar prazo jurídico ou ocultar atraso.
- Recalcular de forma independente quando o bot apresentar data. Conta correta não confirma termo inicial, cabimento nem calendário.

## Fechamento da resposta

Informar por CI se está pronta, duplicada ou pendente, sem misturar conclusões. Na revisão, separar erro confirmado, inconsistência, provável duplicidade e pendência documental. Não repetir avisos obsoletos quando a fonte oficial já foi localizada.

Excluir do arquivo importável todas as tarefas bloqueadas. Entregar no chat uma lista separada por CI/processo com o dado faltante e a consulta necessária. Conferir descrições curtas, responsáveis fora do resumo e cabeçalhos exclusivos: duas datas recursais OU prazo fatal. Confirmar que nenhuma `DATA` operacional ajustável permaneceu em feriado oficial aplicável, sem alterar datas fixas de atos. Confirmar também que nenhum campo `RESPONSÁVEIS` contém `automático` ou AMANDA LEITE MENDES e que toda tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` usa o responsável da filial, sem Suiane/Suhiane. Não omitir CIs da conferência interna.

No pagamento cível, conferir somente análise e minuta. Excluir tarefa separada de contato com o cliente, pois esse contato já é gerado automaticamente pelo fluxo da análise.

## Exportação TXT para o bot

Aplicar `saida-txt-bot.md` em toda análise de CSV/Excel do VIOS: um único TXT UTF-8 no modelo institucional, somente com tarefas prontas. Pendências de leitura no sistema e duplicadas ficam fora do TXT, identificadas no chat por CI/processo. Verificar que nenhuma tarefa bloqueada foi exportada e explicar cada exclusão. A usuária realiza a consulta e o cadastro manuais das pendências.
