## Arquivo para o robô (.txt)

Depois da análise, sempre entregar também o **arquivo para o robô**: um único bloco de código (```text) com as tarefas no formato abaixo. A Controladoria confere e ajusta, salva como `.txt` e sobe na página de envio; o robô lança exatamente o que estiver no arquivo, sem refazer a análise.

Formato — um bloco por tarefa, separados por uma linha só com `---`:

```text
CI: 42484
TAREFA: MINUTAR PETIÇÃO (EXECUÇÃO) 2026
DATA: 29/10/2026
HORA:
RESPONSÁVEIS: TAMIRA LOIOLA, BRENO SILVA MOTA
DESCRIÇÃO:
PRAZO FATAL: 29/10/2026
MINUTAR PETIÇÃO PARA INFORMAR OS DEMAIS DADOS NECESSÁRIOS PARA A CONFECÇÃO DOS REQUISITÓRIOS (RPV/PRECATÓRIO)
Despacho: considerando a certidão de ID 192859275, intime-se a parte exequente para, no prazo de 5 dias, informar os demais dados necessários para a confecção dos requisitórios.
---
CI: 42502
TAREFA: AUDIÊNCIA UNA/INSTRUÇÃO (TRABALHISTA) 2026
DATA: 22/01/2027
HORA: 08:20
RESPONSÁVEIS: automático
DESCRIÇÃO:
AUDIÊNCIA UNA
DATA: 22/01/2027
HORA: 08:20
FORMATO: TELEPRESENCIAL (ZOOM)
LINK/LOCAL: https://trt7-jus-br.zoom.us/j/85164513045
ID da reunião: 851 6451 3045
SENHA: 355957
```

Regras do arquivo:

- `CI`: só o número da CI do VIOS.
- `TAREFA`: o nome exato da lista oficial (seção "Referência — Tarefas VIOS e Modelos de Descrição").
- `DATA`: a data da tarefa no VIOS (DD/MM/AAAA), já calculada pelas regras de data (D-2, prioridade RPV/emenda da Suhiane, mesmo dia, data do ato). Só `CIÊNCIA` pode ficar com `DATA:` vazia (vai para o dia do envio).
- `HORA`: HH:MM em audiência, perícia e sustentação oral (na sessão virtual, o horário de início); vazia nas demais tarefas.
- `RESPONSÁVEIS`: `automático` (o VIOS marca o auxiliar da intimação) ou os nomes completos, separados por vírgula, como aparecem no VIOS. Na petição da Execução da Tamira: `TAMIRA LOIOLA, BRENO SILVA MOTA`.
- `DESCRIÇÃO`: sempre a última linha de campo; tudo abaixo dela vai para a Observação da tarefa, exatamente como escrito. Incluir as linhas de prazo (`PRAZO FATAL:`, `PRAZO FATAL (D-2):`, `PRAZO PARA EMBARGOS:` / `PRAZO PARA RECURSO:` na análise) seguidas do texto do modelo da tarefa. Não incluir `Responsável a marcar na tarefa`, `Advogada auxiliar` nem `PRIORIDADE ...`.
- Duas tarefas da mesma CI (ex.: verificar viabilidade de sustentação + sustentação oral): dois blocos seguidos com o mesmo `CI`.
- **Não colocar no arquivo**: CI duplicada (vale a original), CI que não deve ser lançada (falta informação, evento sem teor, área divergente do auxiliar, tarefa pendente de definição). Listar essas CIs fora do bloco, com o motivo, para a Controladoria tratar à mão.
