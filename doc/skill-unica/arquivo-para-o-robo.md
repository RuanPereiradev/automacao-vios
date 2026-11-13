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
