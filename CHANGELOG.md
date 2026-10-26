# Changelog

Todas as mudanças do bot de intimações ficam registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Tipos: **Adicionado**, **Alterado**, **Corrigido**, **Removido**, **Segurança**.

Como registrar: toda alteração entra primeiro em **[Não lançado]**; quando a
etapa estiver pronta e testada, vira uma nova versão com data.

---

## [Não lançado]

### Adicionado — Criação de tarefas no VIOS (etapa 5)
- `bot/lancamento.py` + `lancar.py` / `rodar_lancamento.sh`: lança no VIOS as
  tarefas da análise, pela tela **Lançar Intimação** (`int-lanca.php`).
  Preenche Tarefa, Tipo de prazo = Data, Data para conclusão (data calculada
  na análise; sem data, ex.: ciência = hoje), Observação (descrição da tarefa)
  e mantém Responsáveis (advogado do processo; + Breno quando a regra pede) e
  "Texto intimação" marcado.
- O VIOS lança em dois passos: **Adicionar** põe a tarefa no quadro "Tarefas"
  (provisório) e **Gravar** efetiva. O bot adiciona todas as tarefas da CI,
  confere o quadro e só então grava.
- Conferência depois de gravar pela tela `confere-intimacao-lancada.php`: a
  tarefa tem que aparecer lá, não apagada; senão é erro.
- Proteções contra duplicidade: não lança se a CI já tem tarefa ativa no VIOS
  (tarefas apagadas são ignoradas) nem se já está em `saida/lancamentos.json`.
  Não lança quando a análise pede conferência humana (tarefas especiais).
- **Modo teste por padrão**: sem `--confirmar` o bot adiciona ao quadro e tira
  print, mas não clica em Gravar.
- `analisar.py --ci 42431[,...]`: analisa só as CIs informadas
  (saída `analise_<periodo>_ci-<CIs>.json/.md`).
- Nome da tarefa da skill casado com a opção do VIOS sem diferença de
  acento/espaço (ou pelo nome do VIOS entre parênteses).
- **Primeiro lançamento real (26/10/2026)**: CI 42431 — CIÊNCIA (TRABALHISTA)
  2026, 26/10/2026, Francisco Johnys (tarefa CI 408941 no VIOS). Conferida:
  saiu da pesquisa "sem tarefa" (21 → 20).
- **Validado pelo usuário no VIOS (26/10/2026):** tarefa, data, responsável e
  descrição da CI 42431 conferidos e aprovados.

### Corrigido — Criação de tarefas
- 1ª tentativa (10:53) só clicava em Adicionar e não gravava nada; o bot
  confundiu com sucesso uma tarefa antiga, já apagada, da mesma CI. Corrigido
  com o passo Gravar e a conferência que ignora tarefas apagadas.

### Adicionado — Versionamento
- Projeto no GitHub: https://github.com/RuanPereiradev/automacao-vios (branch
  `main`, 23/10/2026). Fora do repositório: `.env` (senha e chave de API),
  `saida/` e `logs/` (dados de clientes) e prints em `doc/*.png|*.jpg`.
- A skill da Controladoria (`doc/analise-intimacoes-controladoria/`) está no
  repositório, por decisão do usuário.

### Adicionado — Agente de análise de intimações (IA)
- `bot/analise.py`: agente que decide as tarefas VIOS de cada intimação usando a
  skill `analise-intimacoes-controladoria` como instruções da IA. Gera
  `saida/analise_<periodo>.md` (relatório para revisão) e `.json`.
- `bot/ia/`: provedores de IA intercambiáveis pelo `.env` (`LLM_PROVEDOR`):
  `openai` (padrão, Responses API + Structured Outputs) e `anthropic`.
- `bot/skill.py`: carrega SKILL.md + referências e extrai a lista oficial de
  53 tarefas; a IA só consegue responder nomes dessa lista (enum no schema).
- `bot/prazos.py`: calendário de dias úteis (feriados nacionais fixos e móveis,
  recesso 20/12–20/01, feriados locais em `doc/feriados.txt`), prazo fatal,
  D-2 e próximo dia útil. **As datas são calculadas pelo código, não pela IA.**
- Conferências fixas da skill no código: Breno em `MINUTAR PETIÇÃO EXECUÇÃO`,
  auxiliar SUH × área, JOAQ/JOAN/LILI × Execução, Tamira × outra área, perícia
  social com instrução (mesma data), sustentação com duas tarefas, perícia
  médica previdenciária com quesitos, ato antes do D-2, possível duplicidade.
- `analisar.py` / `rodar_analise.sh` para analisar a última captura; ou
  `ANALISE_ATIVA=true` para analisar logo após capturar.
- Variáveis `.env`: `ANALISE_ATIVA`, `LLM_PROVEDOR`, `LLM_MODELO`, `LLM_ESFORCO`,
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SKILL_PASTA`, `FERIADOS_ARQUIVO`.
- Dependência `openai==2.2.0` (última compatível com Python 3.8).
- Erro de chave, permissão ou modelo inexistente interrompe a análise na 1ª
  intimação (em vez de repetir o erro em todas); outros erros pulam só a CI.
- Teste do fluxo com IA simulada nas 11 intimações de 22/10/2026: datas,
  regras e relatório OK.
- **Primeira execução real** (OpenAI `gpt-5.6`, 23/10/2026): 11 intimações,
  0 erros, ~4 min; 259 mil tokens de entrada (83% em cache) e 13 mil de saída.
  Todas as tarefas da lista oficial; ordens dirigidas à parte contrária
  identificadas; fluxo de pagamento cível aplicado (CI 42373).
- `analisar.py --recalcular`: refaz datas, conferências e relatório a partir das
  respostas da IA salvas no `analise_*.json` (campo `ia`), sem chamar a API.

### Alterado — Calendário de feriados por processo
- `bot/prazos.py` reescrito: cada processo tem calendário próprio conforme
  **esfera** (Justiça Federal ou não), **UF** e **cidade** da intimação.
- Lê a tabela `doc/feriados-brasil-2026-2027.md` (nacionais, estaduais,
  capitais e pontos facultativos) — nova variável `FERIADOS_TABELA`.
- Justiça Federal: feriados da Lei 5.010/66, art. 62 (Carnaval, quarta e quinta
  da Semana Santa, 11/08, 01/11, 08/12).
- Justiça Estadual/Trabalho: feriados estaduais da UF e municipais da cidade.
- **Carnaval e Corpus Christi deixaram de ser feriado nacional** (a tabela os
  classifica como ponto facultativo); na Justiça Federal o Carnaval continua
  feriado pela Lei 5.010/66.
- Regra conservadora: pontos facultativos (ex.: Dia do Servidor 28/10),
  feriado estadual/municipal em processo federal e cidade sem cadastro **não
  mudam a data** — viram alerta ⚠ para conferir a portaria do tribunal.
- `doc/feriados.txt` aceita escopo: `DD/MM/AAAA ; ESCOPO ; descrição`
  (TODOS, JUSTIÇA FEDERAL, JUSTIÇA ESTADUAL, UF ou CIDADE/UF).
- Relatório mostra, em cada CI, o calendário usado e os feriados contados.

### Corrigido
- Chamada à IA podia ficar presa até 30 min (padrão do SDK: 10 min × 3
  tentativas) — aconteceu na CI 42376 em 23/10. Agora: limite de 3 min por
  chamada e até 2 novas tentativas; se ainda falhar, só aquela CI fica com erro.
- Tarefa `ANALISAR SENTENÇA/...` sem prazo principal ficava com data
  "PENDENTE", e com prazo de recurso ficava com o D-2 do recurso. Agora usa o
  **D-2 mais cedo** entre embargos, recurso e prazo principal (ex.: CI 42381
  passa de 12/11 para 28/10/2026).

### Alterado
- **Novo fluxo de captura**: depois do login o bot vai para
  `index.php?pag=sys/publicacoes/int-pesquisa.php`, pesquisa as intimações
  disponibilizadas **ontem** (`pesq[idata]` e `pesq[fdata]` = hoje − 1 dia) e lê a
  tabela de resultado. Substitui a leitura dos cards de `intimacoes-pesquisa.php`.
- `NAVEGACAO_URL_FINAL` no `.env` aponta para `int-pesquisa.php`.
- Saída agora em **JSON** (`saida/intimacoes_AAAA-MM-DD.json`, data pesquisada),
  com um campo por coluna — pronto para a etapa de criação de tarefas.

### Adicionado
- Módulo `bot/intimacoes.py` (pesquisa por data + leitura da tabela).
- Variáveis `PESQUISA_CAMPO_DATA` e `PESQUISA_DIAS_ATRAS` (padrão 1 = ontem).
- Campos capturados por intimação: CI, datas de disponibilização/publicação,
  números do processo, cliente, advogado, auxiliares, OAB, cidade, fornecedor,
  informações extras, situação (ex.: "Sem tarefa lançada"), sugestões de tarefa
  do VIOS, texto completo, `comunicacao_id` e link "Lançar Intimação".
- **Segunda-feira**: o bot pesquisa de sexta a domingo (regra: se a data final
  cair num domingo, a inicial volta para a sexta). Arquivo de saída fica
  `intimacoes_AAAA-MM-DD_a_AAAA-MM-DD.json`. Testado no VIOS com 16–18/10/2026:
  período aceito; as 25 intimações de 16/10 já tinham tarefa, então vieram 0.
- **"Marcar todas" no filtro Área** (`pesq[pr_areas_id][]`, 16 áreas) antes de
  pesquisar. Configurável em `PESQUISA_MARCAR_TODAS` (nomes separados por `|`;
  também aceita `pesq[advogados_id][]` e `pesq[impTribunais][]`). Teste real
  em 22/10/2026: 16 áreas marcadas, 11 intimações (mesmo resultado de antes).
- Limite da listagem trocado de 50 para 500 linhas.
- Avisos no log se o total do rodapé não bater com as linhas lidas ou se alguma
  intimação estiver fora do período pesquisado.
- Skill `analise-intimacoes-controladoria` extraída em
  `doc/analise-intimacoes-controladoria/` (SKILL.md + 4 referências). Pasta
  `images/` renomeada para `doc/`.
- `DOCUMENTACAO.md` com o passo a passo de tudo o que foi feito, estrutura,
  configuração e próximos passos.
- `CHANGELOG.md` (este arquivo).
- `CLAUDE.md` com a regra de sempre atualizar o changelog.

### Corrigido
- Texto das intimações vinha cortado em "... Mostrar mais" na tela de cards;
  na tabela ele vem completo.
- Popup de "Recado" que abre após o login bloqueava o preenchimento; o bot agora
  preenche e envia a pesquisa por JavaScript, sem tocar no popup.

### Resultado
- Execução real (23/10/2026, data 22/10/2026): 11 intimações, 0 com erro —
  mesmo total exibido pelo VIOS.

### Pendente
- Lançar todas as CIs do dia (hoje o lançamento é por CI, com `--ci`).

---

## [0.4.0] — 2026-10-23
### Adicionado
- Extração de intimações em **cards** (`CARD`, `CARD_CABECALHO`, `CARD_TEXTO`),
  com prioridade sobre `TABELA`.
- Rolagem automática até o fim da página para carregar todos os cards.
- Saída em `saida/intimacoes_AAAA-MM-DD_HHMMSS.txt`, um bloco por intimação.
- `NAVEGACAO_URL_FINAL` apontando para a pesquisa de intimações do VIOS.
- Material de regras `doc/analise-intimacoes-controladoria.zip`
  (base para criar as tarefas).

### Resultado
- Primeira captura real: 35 intimações extraídas, 0 com erro.

## [0.3.0] — 2026-10-23
### Adicionado
- Configuração real do VIOS no `.env` (seletores de login).
- Opção `MANTER_ABERTO` para o Chrome continuar aberto ao final.
- `rodar.sh` para rodar o bot de qualquer pasta com a `.venv` do projeto.
- Caminho do `.env` opcional como argumento (`./rodar.sh outro.env`).

### Alterado
- Login confirma pela mudança de URL quando `LOGIN_SUCESSO` está vazio.
- Login aperta Enter quando `LOGIN_BOTAO` está vazio.

## [0.2.0] — 2026-10-23
### Adicionado
- Estrutura modular em `bot/` (`config`, `navegador`, `login`, `navegacao`, `extracao`).
- Toda configuração via `.env`, com validação das variáveis obrigatórias
  e dos seletores (`css:` / `xpath:`).
- Extração de tabela para `.txt` separado por TAB.
- Log em `logs/bot.log` e screenshot automático em caso de erro.
- `.env.example`, `requirements.txt` e `.gitignore`.
- Teste em site simulado (login + tabela) aprovado.

### Segurança
- Senha nunca aparece em log nem em `print` da configuração.
- `.env` fora do controle de versão (`.gitignore`).

## [0.1.0] — 2026-10-23
### Adicionado
- Ambiente Python (`.venv`) com Selenium e configuração do VS Code.
- `codigo_selenium.py`: primeiro teste de Selenium.
