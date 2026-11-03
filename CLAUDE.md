# Bot de comprovantes previdenciários — VIOS

Bot Selenium (sem IA) que, nos três últimos dias do mês, pega as tarefas previdenciárias
do calendário do VIOS, lê o comprovante do processo, preenche três campos, grava e confere.
Detalhes em `O_QUE_O_BOT_FAZ.txt`.

## Regras

- **Toda mudança no projeto deve ser registrada em `CHANGELOG.md`**, na seção `[Não lançado]`,
  no mesmo momento da mudança (Adicionado / Alterado / Corrigido / Removido / Segurança).
- Se a mudança altera o funcionamento, a configuração (`.env`) ou os passos, atualizar também
  `O_QUE_O_BOT_FAZ.txt`.
- Escrever documentação e mensagens em português.
- Nunca colocar a senha ou o conteúdo do `.env` na documentação.
- Nunca afrouxar as proteções contra alteração indevida (modo teste padrão, não sobrescrever,
  um processo / um comprovante por tarefa, conferência depois de gravar).
