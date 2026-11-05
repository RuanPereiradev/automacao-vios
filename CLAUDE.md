# Bot de Intimações — VIOS

Bot Selenium que entra no VIOS, captura intimações e (próxima etapa) cria tarefas a partir delas.
Detalhes em `DOCUMENTACAO.md`.

## Regras

- **Toda mudança no projeto deve ser registrada em `CHANGELOG.md`**, na seção `[Não lançado]`,
  no mesmo momento da mudança (Adicionado / Alterado / Corrigido / Removido / Segurança).
- Se a mudança altera o funcionamento, a configuração (`.env`) ou os passos, atualizar também
  `DOCUMENTACAO.md` (seção "Passo a passo" e tabelas).
- Mudança no relatório de processos por Grupo Cliente (`relatorio_processos.py`,
  `bot/processos_grupo.py`, `.env.usuario2`): atualizar também `RELATORIO_PROCESSOS.md`.
- Escrever documentação e mensagens em português.
- Nunca colocar a senha ou o conteúdo do `.env` na documentação.
