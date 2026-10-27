# Regras de Prazos e Recursos

Use este arquivo para orientar cálculo de prazo e indicação de cabimento. Se o documento ou manual da Controladoria trouxer regra mais específica, use a regra específica.

## Regra operacional

- Sempre que houver prazo fatal calculável, indicar a data operacional em D-2 com o rótulo exato `PRAZO FATAL (D-2):`.
- Se houver audiência ou perícia antes do D-2, usar no campo `PRAZO FATAL (D-2)` uma data anterior ao ato.
- Em descrições de tarefas VIOS, usar a data de trabalho interna quando a operação exigir D-2.
- Ao responder ao usuário, diferenciar `Prazo fatal:` e `PRAZO FATAL (D-2):`.
- No resumo destinado à tarefa VIOS, inserir somente `PRAZO FATAL (D-2): DD/MM/AAAA`; não repetir ali o prazo jurídico fatal real.

## Embargos e recursos

Regras extraídas do POP:

- Embargos: 5 dias.
- Recurso em Juizado: 10 dias.
- Recurso na Justiça Comum: 15 dias.

### Regra obrigatória para tarefas de análise

Sempre que a tarefa indicada for `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, exibir as duas linhas, nesta ordem:

```text
PRAZO PARA EMBARGOS: [resultado]
PRAZO PARA RECURSO: [resultado]
```

Preencher `[resultado]` com:

- a data operacional em D-2, quando cabível e calculável;
- `NÃO CABE`, quando o meio não for cabível;
- com cabimento pendente (o teor não permite concluir), a data em D-2 pelo prazo legal — o advogado decide se recorre e precisa da data;
- se não couber embargos nem recurso, omitir as duas linhas e deixar somente o `PRAZO FATAL (D-2)`.

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

## Prazo previsto em lei (quando o ato não informar o prazo)

Quando a intimação não trouxer o número de dias, usar o prazo previsto em lei abaixo e escrever na descrição da tarefa que o prazo é o legal, por exemplo: `Prazo previsto em lei: 15 dias úteis (Apelação).`

Só usar `PENDENTE – NÃO CONSTA NO DOCUMENTO` quando o caso não estiver nesta tabela nem nas regras do Previdenciário.

### Processo Civil

| Meio | Prazo |
| --- | --- |
| Prazo geral dos recursos: Apelação, Agravo de Instrumento, Agravo Interno, Recurso Especial e Recurso Extraordinário | 15 dias úteis |
| Embargos de Declaração (qualquer que seja a decisão) | 5 dias úteis |

### Processo do Trabalho

| Meio | Prazo |
| --- | --- |
| Recursos em geral: Recurso Ordinário, Recurso de Revista, Agravo de Instrumento, Agravo de Petição, Embargos ao TST (Recurso de Embargos à SDI-1) | 8 dias úteis |
| Embargos de Declaração (contra sentença ou acórdão, para sanar omissão, contradição, obscuridade ou manifesto equívoco) | 5 dias úteis |
| Embargos à Execução (para o executado se manifestar ou contestar a penhora, após a notificação) | 5 dias úteis |
| Recurso Extraordinário (ao STF, regra do CPC) | 15 dias úteis |

### Contagem do prazo legal

- Contar em dias úteis.
- Excluir o dia do começo e incluir o dia do vencimento.
- No Previdenciário continuam valendo as regras próprias: embargos em 5 dias, recurso em Juizado em 10 dias e recurso na Justiça Comum em 15 dias.
- Quando o cabimento estiver pendente (`PENDENTE – CONFIRMAR CABIMENTO`), informar mesmo assim o prazo legal do meio, para não perder o prazo.

## Cuidados

- Não afirmar cabimento de recurso quando o teor da decisão/sentença/acórdão não permitir concluir.
- Quando depender de avaliação jurídica, indicar: `Cabe análise do advogado sobre recurso/embargos.`
- Não sugerir abertura direta de recurso quando a regra da Controladoria exigir tarefa de análise primeiro.
- Quando a intimação já for expressamente para contrarrazões, pode sugerir tarefa de contrarrazões.
- Se faltar data de publicação/intimação, não calcule prazo; marque pendência.

## Contagem

- Cível, Trabalhista e JEC: usar dias úteis, salvo regra específica em sentido contrário.
- Criminal: usar dias corridos, salvo regra específica em sentido contrário.
- Considerar feriados nacionais e feriados locais previstos nos manuais internos disponíveis.

Se não houver calendário de feriados disponível na sessão, informe a pendência em vez de inventar a data.
