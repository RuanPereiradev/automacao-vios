# Bot de Intimações — VIOS

Bot em Python + Selenium que entra no sistema VIOS (`roneely.vios.com.br`),
captura as intimações publicadas, analisa com IA e cria as tarefas no VIOS
a partir dessas intimações.

> Histórico de mudanças: veja [CHANGELOG.md](CHANGELOG.md).

---

## 1. Objetivo

| Etapa | O que faz | Status |
| --- | --- | --- |
| 1. Login | Abre o VIOS e entra com usuário/senha do `.env` | ✅ Pronto |
| 2. Navegação | Vai direto para a pesquisa de intimações (`int-pesquisa.php`) | ✅ Pronto |
| 3. Captura | Pesquisa as intimações de **ontem** (na segunda: sexta a domingo), lê a tabela e salva em JSON | ✅ Pronto (11 intimações de 22/10/2026) |
| 4. Análise | Agente com IA + skill da Controladoria sugere as tarefas, com datas calculadas pelo código | ✅ Pronto (11 intimações de 22/10 analisadas com gpt-5.6) — em validação pela Controladoria |
| 5. Criação de tarefas | Cria a tarefa no VIOS com descrição e prazo | ✅ Pronto (`--ci X` ou `--ci todas`) — 23 a 25/10/2026: 19 de 20 lançadas em 26/10/2026 |
| 6. Revisão humana | Página local onde a pessoa confere, edita e valida as tarefas antes do lançamento | 🚧 Página pronta (26/10/2026); falta ligar o robô à fila e agendar às 17h |

---

## 2. Passo a passo do que foi feito

### Passo 1 — Ambiente
- Criada a `.venv` do projeto e instalado o Selenium (`requirements.txt`).
- VS Code configurado para usar a `.venv` (`.vscode/settings.json`) e para
  depurar o arquivo atual (`.vscode/launch.json`).
- `codigo_selenium.py` é só o primeiro teste/exemplo de Selenium (não faz parte do bot).

### Passo 2 — Estrutura do bot
O código foi dividido em módulos na pasta `bot/`, e **tudo o que é específico
do sistema fica no `.env`** (URL, credenciais, seletores). Assim o código não
muda se o site mudar — só o `.env`.

### Passo 3 — Login
- `bot/login.py` preenche usuário e senha e aperta Enter (o VIOS não precisa de botão).
- O login é confirmado quando a URL sai da tela de login
  (ou, se `LOGIN_SUCESSO` estiver definido, quando esse elemento aparecer).
- Se não confirmar dentro do `TIMEOUT`, gera `LoginErro`.

### Passo 4 — Teste em site simulado
- Antes de usar o VIOS, o bot foi testado num site de login + tabela falso
  (arquivos locais). Funcionou: login, clique no menu, extração da tabela,
  e o descarte de uma linha com colunas faltando (registrado no log como aviso).

### Passo 5 — Login no VIOS
- Seletores reais descobertos: `input[name='form[usuario]']` e `input[name='form[senha]']`.
- Criada a opção `MANTER_ABERTO=true` para o navegador não fechar ao final,
  facilitando inspecionar a página e descobrir os próximos seletores.
- Criado o `rodar.sh` para rodar o bot de qualquer pasta.

### Passo 6 — Chegar nas intimações
- Em vez de clicar em menus, o bot vai direto para a URL
  `?pag=sys/publicacoes/intimacoes-pesquisa.php` (`NAVEGACAO_URL_FINAL`).

### Passo 7 — Captura das intimações em cards
- As intimações no VIOS não são uma tabela, são **cards**. Foi criado o modo
  de extração por cards (`CARD`, `CARD_CABECALHO`, `CARD_TEXTO`), que tem
  prioridade sobre `TABELA`.
- O bot rola a página até o fim para carregar todos os cards.
- Cada intimação vira um bloco no arquivo `saida/intimacoes_AAAA-MM-DD_HHMMSS.txt`:
  - **cabeçalho**: datas, CI, processo, cliente, contrato, fase processual,
    *sugestão de tarefa* do VIOS;
  - **texto**: o teor da publicação.
- Primeira execução real: **35 cards extraídos, 0 com erro**.

### Passo 8 — Regras para gerar tarefas (material recebido)
- Recebido `doc/analise-intimacoes-controladoria.zip`, com as regras da
  Controladoria: fluxo de intimações (POP), roteamento interno, regras de
  prazos/recursos e a lista de **Tarefas VIOS com modelos de descrição**.
- Esse material será a base das etapas 4 e 5.

### Passo 9 — Novo fluxo: pesquisa por data na tabela
- A captura passou a usar a tela **Pesquisa intimações**
  (`index.php?pag=sys/publicacoes/int-pesquisa.php`).
- O bot preenche **Data início** (`pesq[idata]`) e **Data fim** (`pesq[fdata]`)
  com **ontem** (hoje − `PESQUISA_DIAS_ATRAS`), troca "Mostrar" de 50 para 500 e
  pesquisa. Os outros filtros ficam no padrão da tela — inclusive
  **"Com Tarefa Lançada = Não"**, então só vêm intimações ainda sem tarefa.
- Depois do login o VIOS abre um popup de **Recado**. Para não interagir com ele
  (ex.: marcar como lido), o bot preenche e envia o formulário por JavaScript.
- A tabela é lida direto do navegador (não pelo CSV): cada célula tem um
  `data-id` que termina com o nome da coluna (`..._linha_0_imp_pub_id`), o que
  dá campos exatos. O texto vem **completo** (sem "Mostrar mais").
- Cada intimação vira um objeto no `saida/intimacoes_AAAA-MM-DD.json`.
- Teste real: 11 intimações de 22/10/2026, 0 erros, igual ao total do VIOS.

**Por que tabela no navegador e não o CSV?** O bot já está na página com os
dados prontos; o CSV exigiria configurar download, esperar o arquivo e lidar com
codificação/separador. Além disso, a tabela traz o link **Lançar Intimação** e a
situação da tarefa, que serão usados na criação de tarefas. Ler 11 linhas leva
~5 s. O CSV só valeria a pena acima de 500 intimações por dia (limite da tela).

### Passo 10 — Segunda-feira pega o fim de semana
- Na segunda, o período é **sexta a domingo** (início = hoje − 3, fim = ontem).
- Nos outros dias, só ontem. Regra no código (`periodo_pesquisa`): se a data
  final cair num domingo, a inicial volta para a sexta.

| Dia que o bot roda | Período pesquisado |
| --- | --- |
| Segunda | sexta → domingo |
| Terça a sábado | o dia anterior |
| Domingo | sábado |

- Teste no VIOS (16 a 18/10/2026): o sistema aceitou o período; as 25
  intimações de 16/10 já tinham tarefa lançada, por isso o bot trouxe 0 —
  comportamento correto, porque ele só busca as sem tarefa.

### Passo 11 — "Marcar todas" no filtro Área
- Antes de pesquisar, o bot marca todas as opções do filtro **Área**
  (`pesq[pr_areas_id][]`, 16 áreas), o mesmo que clicar em "Marcar todas".
- Isso é feito por JavaScript, junto com as datas, por causa do popup de recado.
- A tela tem outros dois filtros com "Marcar todas" (Advogados e Tribunais);
  basta acrescentá-los em `PESQUISA_MARCAR_TODAS`, separados por `|`.
- Se um filtro configurado não existir na tela, o log mostra um aviso.

### Passo 12 — Agente de análise (IA + skill da Controladoria)
- A skill do ChatGPT (`doc/analise-intimacoes-controladoria.zip`) foi extraída em
  `doc/analise-intimacoes-controladoria/` e virou as **instruções do agente**.
- **Por que IA e não regras em código?** As regras exigem interpretar a decisão
  (desfavorável? encerra o processo? quem recorreu? para quem é a ordem?). Em
  `if/else` isso ficaria frágil. Automatizar o site do ChatGPT também foi
  descartado (frágil e contra os termos); usamos a **API**.
- **Divisão de trabalho:**

| Quem | O quê |
| --- | --- |
| IA (OpenAI por padrão) | Lê a intimação, classifica o ato, escolhe tarefas **da lista oficial** (o schema não aceita outro nome), informa os dias de prazo e escreve os resumos |
| Código (`bot/prazos.py`) | Calcula prazo fatal, D-2, próximo dia útil, embargos e recurso com feriados e recesso |
| Código (`bot/analise.py`, `bot/duplicidade.py`) | Confere as regras fixas da skill e marca alertas ⚠; marca Breno como responsável (sem lembrete na descrição); apaga da descrição "Responsável a marcar", "Advogada auxiliar" e "PRIORIDADE RPV/EMENDA"; detecta duplicatas (a cópia é ignorada) |
| Pessoa | Revisa `saida/analise_*.md` antes de lançar no VIOS |

- **Trocar de IA:** `LLM_PROVEDOR=openai` ou `anthropic` no `.env` (+ a chave).
  Cada provedor fica num arquivo em `bot/ia/`; os dois devolvem o mesmo JSON.
- **Disponibilização × publicação:** os arquivos `intimacoes_*`/`analise_*` levam
  a data de **disponibilização** pesquisada no VIOS; a publicação é o 1º dia útil
  seguinte (Lei 11.419/2006, art. 4º, § 3º). O relatório mostra as duas datas no
  cabeçalho e em cada CI (ex.: `analise_2026-10-27` = disponibilizadas em 27/10,
  publicadas em 28/10).
- **Contagem de prazo:** começa no 1º dia útil após a **publicação**; dias úteis
  (ou corridos, se a IA indicar); vencimento em dia não útil vai para o próximo
  útil; D-2 = 2 dias úteis antes do fatal; RPV e emenda da Suhiane = próximo dia
  útil após a publicação; tarefa ANALISAR = **mesmo dia** (a data de
  lançamento), com as datas de embargos e recurso em D-2 só na descrição
  (sem a linha `PRAZO FATAL (D-2)`); tarefa com horário (audiência, perícia,
  sustentação oral) = data exata do ato, nunca D-2 (sessão virtual = 1º dia
  da sessão). Feriados locais vão em `doc/feriados.txt`.
- **Prazo previsto em lei:** quando a intimação não diz quantos dias, a IA usa
  a tabela de prazos legais da skill (`references/regras-prazos-recursos.md`):
  Cível 15 dias úteis para recursos e 5 para embargos de declaração;
  Trabalhista 8 dias úteis para recursos, 5 para embargos de declaração e à
  execução, 15 para Recurso Extraordinário; manifestação sobre laudo
  pericial 15 dias úteis (inclusive Juizado e Previdenciário). A descrição da tarefa diz
  "Prazo previsto em lei: N dias úteis (meio)".
- **Custo:** a skill tem ~70 mil caracteres (~20 mil tokens) e é igual em toda
  chamada, então fica em cache no provedor; o log mostra os tokens usados.
- **Como rodar:** `./rodar_analise.sh` (analisa a última captura) ou
  `./rodar_analise.sh saida/intimacoes_2026-10-22.json`; ou `ANALISE_ATIVA=true`
  para o `./rodar.sh` capturar e já analisar.
- **Feriados (Passo 13):** cada processo tem calendário próprio — veja abaixo.
- **Recalcular sem custo:** `./rodar_analise.sh --recalcular saida/intimacoes_X.json`
  refaz datas e relatório com as respostas da IA já salvas (útil depois de
  cadastrar feriados ou mudar regra de data).
- **Primeira execução real (23/10/2026):** 11 intimações, 0 erros, ~4 min,
  83% dos tokens de entrada em cache.

### Passo 13 — Calendário de feriados por processo
- Motivo: o prazo da CI 42388 divergia entre o ChatGPT e o nosso relatório por
  causa de feriados. Foi adicionada a tabela `doc/feriados-brasil-2026-2027.md`.
- O código monta um calendário para cada processo com base na intimação
  (`Esfera` em informações extras e `Cidade/UF`):

| Situação | Conta como feriado (estende o prazo) | Só alerta ⚠ (não muda a data) |
| --- | --- | --- |
| Todos os processos | Nacionais da tabela; recesso 20/12–20/01 | Pontos facultativos (Dia do Servidor, Carnaval estadual, Corpus Christi, vésperas) |
| Justiça Federal | Lei 5.010/66 art. 62: Carnaval, quarta e quinta Santa, 11/08, 01/11, 08/12 | Feriados estaduais e municipais |
| Justiça Estadual / Trabalho | Estaduais da UF; municipais da cidade (se capital na tabela) | Cidade fora da tabela (ex.: Sobral) |
| `doc/feriados.txt` | Linha com escopo que vale para o processo | Linha com `; AVISO` no fim (suspensão não confirmada) |

- **Por que conservador:** contar um feriado que não existe empurra o prazo
  para depois e pode causar perda de prazo. Na dúvida, o bot mantém a data mais
  cedo e avisa. Quando a Controladoria confirmar uma suspensão (ex.: portaria do
  TRF5 para 28/10), basta cadastrar em `doc/feriados.txt`:
  `28/10/2026 ; JUSTIÇA FEDERAL ; Dia do Servidor (Portaria TRF5 nº ...)` e
  rodar `./rodar_analise.sh --recalcular` (sem custo de API).
- A tabela cobre 2026 e 2027 e só as **capitais**; cidades do interior entram
  em `doc/feriados.txt`.
- **Feriado por tribunal:** o ramo da Justiça sai do número CNJ do processo
  (`.8.` estadual, `.5.` trabalho, `.4.` federal). Escopos de `doc/feriados.txt`:
  `JUSTIÇA ESTADUAL/CE` (só TJCE), `JUSTIÇA DO TRABALHO/CE` (TRT7),
  `JUSTIÇA FEDERAL/CE` (JFCE), `CE` (todos os ramos no Ceará), além de
  `TODOS`, `JUSTIÇA FEDERAL`, `JUSTIÇA ESTADUAL`, `JUSTIÇA DO TRABALHO` e `CIDADE/UF`.
- **Regra combinada com a Controladoria (27/10/2026):** contar o máximo de
  feriados possível, porque os advogados reclamam quando um feriado não é
  contado; mas, se a suspensão não estiver confirmada, a data fica adiantada
  para não perder prazo. Para isso, a linha com `; AVISO` no fim não estende
  o prazo, só gera o alerta "não confirmado". Confirmada a portaria, apagar o
  `; AVISO` e recalcular.
- Exemplo (Dia do Servidor 2026, transferido de 28/10 para 30/10): confirmado
  no TJCE, TRT7 (Portaria 518/2025) e JFCE (Ato TRF5 435/2026).
- **Pesquisa na internet (`bot/feriados_web.py`, 27/10/2026):** antes de cada
  análise o bot pergunta à IA, com pesquisa na web, os feriados e suspensões
  dos tribunais e cidades do lote nos próximos 60 dias, e grava em
  `doc/feriados.txt` com o link da fonte:

| Resultado da pesquisa | O que o bot grava |
| --- | --- |
| Suspensão confirmada em fonte oficial (`.jus.br`; municipal também `.gov.br`/`.leg.br`) | Linha normal: conta no prazo |
| Fonte não oficial ou efeito nos prazos incerto | Linha com `; AVISO`: data adiantada + alerta |
| Ponto facultativo sem efeito nos prazos | Nada |
| Nacional, Lei 5.010/66 ou recesso 20/12–20/01 | Nada (o calendário já conta) |

  - **Mensal:** o mesmo tribunal/cidade só é pesquisado de novo depois de 30
    dias (cache em `saida/feriados_pesquisa.json`); cada pesquisa cobre ~95 dias
    (um mês de publicações + os prazos). Leva ~1 min por tribunal.
  - Pesquisa econômica: no máximo 6 buscas por tribunal e só o trecho
    relevante das páginas (`search_context_size=low`). Custo estimado:
    ~US$ 0,30 por tribunal, ~US$ 3 por mês com 8 tribunais.
  - Desligar: `FERIADOS_PESQUISA=false` no `.env`. Recalcular uma análise
    antiga com pesquisa: `./rodar_analise.sh --recalcular --feriados`.
  - Vale conferir o bloco "Pesquisa automática" de vez em quando: linha
    errada pode ser apagada ou ganhar `; AVISO`.

- **Análise em lote (27/10/2026; Claude desde 28/10/2026):** a análise completa vai num lote da Batch
  API da OpenAI ou da Message Batches API do Claude (`LLM_PROVEDOR=anthropic`), pela metade do preço.
  No Claude o lote não tem fallback de recusa: CI recusada é refeita uma a uma, com fallback. O log mostra "Lote: N intimações
  enviadas" e o andamento ("in_progress — 12 de 45 prontas"). Se o programa
  cair, rodar o mesmo comando retoma o lote (o id fica em
  `saida/lote_<análise>_<etapa>.json`). Se passar de `LLM_LOTE_ESPERA_MIN`, cancela e
  analisa o resto uma a uma. `--ci` não usa lote.

- **Triagem por importância (28/10/2026, `LLM_MODELO_SIMPLES`):** com um modelo
  barato configurado, a análise passa a ter dois modelos:
  1. o código (sem IA) procura no teor da intimação sentença, acórdão, decisão,
     audiência, RPV/precatório, tutela/liminar, embargos, apelação ou recurso
     (o nome da classe, ex. "Cumprimento de Sentença" ou "Classe: Recurso
     Inominado", não conta). Achou -> vai direto para o `LLM_MODELO`;
  2. as outras (despachos, laudos, ciências...) vão para o modelo barato;
  3. se a resposta do barato tiver ato sentença/acórdão/decisão/audiência/RPV/
     proposta de acordo, embargos ou recurso que cabem ou podem caber, área
     PENDENTE, falta de dados, bloqueio, tarefa ou data pendente, ou erro, a
     intimação é refeita pelo `LLM_MODELO` (no lote, numa 2ª rodada).
  - O relatório mostra em cada CI o modelo e o motivo ("texto cita SENTENCA",
    "simples", "reanalisada: ato DECISÃO"); o JSON guarda `modelo`, `triagem`
    e `custo_us`.
  - Nas análises de 22 a 26/10, 41 de 76 intimações iriam para o modelo barato.
  - A pesquisa de feriados pode usar outro modelo: `LLM_MODELO_FERIADOS`.

- **Teto de gasto (`LLM_LIMITE_US`):** antes de cada chamada (ou lote) o bot
  estima o custo e não chama a IA se passar do teto da execução. As CIs que
  ficam de fora saem com "Teto de gasto atingido" e **não são lançadas**; a
  pesquisa de feriados sem espaço no teto fica para a próxima execução (usa os
  feriados já cadastrados). Se a reanálise pelo modelo principal não couber, a
  CI fica com a resposta do barato e bloqueada para lançamento. A estimativa é
  de propósito um pouco acima do custo real (~US$ 0,035 por intimação no lote
  com `gpt-5.6`, contra ~US$ 0,025 reais). O log e o relatório mostram o gasto
  estimado da execução. Preços na tabela de `bot/custo.py` (corrigir pelo
  `LLM_PRECOS` se a OpenAI mudar). A trava definitiva é na conta da OpenAI:
  crédito pré-pago sem recarga automática e orçamento do projeto.

### Passo 14 — Criar a tarefa no VIOS
- Fluxo por CI: `./rodar_analise.sh --ci 42431 saida/intimacoes_X.json` gera a
  análise só dessa CI; `./rodar_lancamento.sh --ci 42431` lança.
- O bot entra no VIOS e abre o link **Lançar Intimação**
  (`index.php?pag=sys/publicacoes/int-lanca.php&imp_pub_id=<CI>`). Preenche
  tudo por JavaScript (os campos são bootstrap-select/TinyMCE e há o popup de
  Recado, que não é tocado):

| Campo do VIOS | O que o bot põe |
| --- | --- |
| Tarefa (`form[processos_etapas_id]`) | A tarefa da análise (nome casado com a lista do VIOS) |
| Tipo de prazo | Data |
| Data para conclusão (`fo[data_prevista]`) | Data calculada na análise; tarefa sem data (ex.: ciência) e tarefa do mesmo dia (análise, verificar sustentação) = dia do lançamento |
| Horário (`fo[hora_prevista]`) | Horário do ato em audiência, perícia e sustentação oral (HH:MM); vazio nas demais. Conferido na tela antes de adicionar |
| Responsáveis | O que o VIOS marca sozinho ao escolher a tarefa (em geral o auxiliar da intimação) + BRENO quando a regra pede; ou exatamente as pessoas escolhidas manualmente na revisão |
| Texto intimação | Marcado (padrão do VIOS) |
| Observação | Descrição da tarefa, toda em **negrito**; as linhas `PRAZO FATAL (D-2): ...`, `PRAZO FATAL: ...` (RPV e emenda da Suhiane), `PRAZO PARA EMBARGOS: ...` e `PRAZO PARA RECURSO: ...` (também com "DE") em **negrito e vermelho**, junto com a data. O teor que o VIOS acrescenta depois fica normal |

- **Dois passos no VIOS:** *Adicionar* põe a tarefa no quadro "Tarefas"
  (provisório, some se a sessão acabar) e *Gravar* efetiva. O bot adiciona
  todas as tarefas da CI, confere o quadro, tira print e só então grava.
- **Conferência:** depois de gravar, o bot abre
  `confere-intimacao-lancada.php` e exige que cada tarefa esteja lá, **não
  apagada**. Lançamentos ficam em `saida/lancamentos.json`.
- **Contra duplicidade:** não lança se a CI já tem tarefa ativa no VIOS
  (tarefa apagada não conta) ou se já está em `saida/lancamentos.json`; não
  lança se a análise pediu conferência humana.
- **Modo teste é o padrão:** sem `--confirmar` o bot adiciona ao quadro e tira
  print (`logs/lancamento_ci<CI>_*.png`), mas **não grava**.
- Lição do 1º teste: clicar só em *Adicionar* não grava nada, e a CI 42431 tinha
  uma tarefa antiga apagada igual à nossa — por isso a conferência ignora
  tarefas apagadas.
- **1º lançamento real (26/10/2026):** CI 42431 → CIÊNCIA (TRABALHISTA) 2026,
  26/10/2026, Francisco Johnys. A CI saiu da pesquisa "sem tarefa".
  **Validado pelo usuário no VIOS:** tudo correto (tarefa, data, responsável
  e descrição).

### Passo 15 — Lançar o período inteiro
- O usuário do login do VIOS foi trocado no `.env` (26/10/2026).
- Fluxo do dia: `./rodar.sh` (captura) → `./rodar_analise.sh` (analisa todas)
  → `./rodar_lancamento.sh --ci todas` (teste) → `--ci todas --confirmar`.
- Proteções novas: não lança CI com prazo sem data calculada; o quadro
  "Tarefas" tem que começar vazio e terminar com uma linha por tarefa (pega
  Adicionar registrado em dobro); nomes da skill com erro de digitação têm
  apelido em `APELIDOS` (`bot/lancamento.py`).
- **Não lança quando falta informação (27/10/2026)** — a CI fica para a
  Controladoria conferir no PJe e lançar à mão; o motivo aparece no log e no
  relatório ("NÃO SERÁ LANÇADA NO VIOS"). Casos:
  - a IA lista em `faltam_dados` o que a tarefa exige e a intimação não traz
    (ex.: audiência sem tipo, data, horário, formato, local ou link/ID/senha;
    perícia sem data, horário ou local);
  - tarefa com horário (audiência, perícia, sustentação oral) sem o horário;
  - intimação que só indica um evento do processo, sem o teor (eproc: "O ato
    refere-se ao seguinte evento: Evento 23 - PETIÇÃO"): a tarefa só pode ser
    definida abrindo o evento no sistema (28/10/2026);
  - área da tarefa × auxiliar responsável: tarefa de Execução com JOAQ, JOAN,
    LILI, SUH, CARL ou JOHN; tarefa de outra área com só TAMI (Tamira =
    Execução); Cível com SUH. Com dois auxiliares (ex.: "TAMI / SUH") vale a IA;
  - tarefa de análise em que cabe embargos ou recurso, mas sem prazo para
    calcular a data;
  - sentença ou acórdão sem a tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` (ex.:
    só `MINUTAR RECURSO`): quem decide se recorre é o advogado (29/10/2026).
- **Descrição da tarefa de análise (27/10/2026):** se cabe (ou pode caber)
  embargos ou recurso, as duas linhas `PRAZO PARA EMBARGOS` e `PRAZO PARA
  RECURSO` sempre com data D-2 (prazo legal quando a intimação não diz,
  inclusive com cabimento pendente); o meio que não cabe fica `NÃO CABE`. Se
  não cabe nenhum, só `PRAZO FATAL (D-2)`. Toda análise tem prazo: sem prazo
  no ato, `PRAZO FATAL:` com o dia útil seguinte à publicação.
- A lista de tarefas do VIOS muda conforme o processo (ex.: `CIÊNCIA (CÍVEL)`
  existe em processo cível); se o nome não existir, a CI fica para lançamento
  manual e o erro aparece no log.
- **Resultado (23 a 25/10/2026):** 20 intimações, 19 tarefas gravadas e
  conferidas, 1 por CI. Ficou de fora a CI 42419 (sustentação oral
  previdenciária — nome com erro na skill e pendências): lançar manualmente.

### Passo 16 — Página de revisão humana
- Novo fluxo combinado (26/10/2026): o robô captura e analisa às 17h; na
  manhã seguinte uma pessoa confere a análise numa página, edita se precisar e
  **valida**; só então o robô lança a versão editada.
- `./rodar_revisao.sh saida/analise_X.json` importa a análise para o banco
  `saida/revisao.db` (SQLite) e abre a página em http://127.0.0.1:5000.
  Importar de novo não apaga edições: CI que já está no banco é mantida.
- Tela: à esquerda a fila agrupada por situação (Para validar, Na fila do
  robô, Lançadas...) e o progresso "N de 45 revisadas"; no centro, a
  intimação para ler (alertas "Conferir antes de validar", resumo e teor) ao
  lado das tarefas. A data mostra o dia da semana e avisa fim de semana.
  Ctrl+Enter valida.
- Na página, por CI: dados do processo, prazos, alertas ⚠, pendências, teor da
  intimação e as tarefas editáveis (tarefa da lista oficial, data, descrição
  com prévia de como fica no VIOS — `PRAZO FATAL:` em vermelho — e
  responsáveis).
  Dá para adicionar e remover tarefas.
- Ações: **Validar e enviar ao robô** (confere tarefa oficial, data e
  descrição, e pede o nome de quem validou), **Salvar rascunho**,
  **Descartar** (não gera tarefa) e **Reabrir** (tira da fila).
- Estados: aguardando → na fila → lançando → lançada / erro; ou descartada.
- **Responsáveis:** o padrão é **automático pelo VIOS**: o robô não mexe no
  campo e o VIOS marca sozinho. Em geral é o **auxiliar** da intimação (SUH →
  SUHIANE, TAMI → TAMIRA, JOHN → FRANCISCO JOHNYS...), não o advogado do
  processo (RONEELY FEITOSA aparece em quase todos); em algumas tarefas, como
  Ciência, o VIOS escolhe outra pessoa (ex.: AMANDA LEITE MENDES). Para uma
  exceção, "Escolher outras pessoas" passa para a escolha manual e o robô
  marca exatamente quem foi escolhido. A lista de pessoas vem
  de `saida/responsaveis.json`; para atualizar quando entrar ou sair alguém:
  `./rodar_revisao.sh --atualizar-responsaveis` (só lê o formulário do VIOS).
- Datas em DD/MM/AAAA (digita só os números). Como a análise é da véspera,
  a página refaz as datas que dependem do dia: `MESMO_DIA` (ex.: verificar
  sustentação) vira hoje e `DIA_SEGUINTE` (ex.: aviso de perícia social) o
  próximo dia útil, com aviso mostrando a data original. Data editada à mão
  fica como a pessoa deixou. Campo **Horário** (HH:MM) para audiência,
  perícia e sustentação oral; vai no campo Horário do VIOS.
- **Ainda não lança:** a CI validada fica "na fila". Próximo passo: o
  lançamento ler a fila (iniciado pelo clique em Validar, com rodada de
  segurança agendada), refazendo as datas relativas ao dia na hora de lançar.
- A página só escuta em 127.0.0.1 (sem login ainda).

### Passo 17 — Duplicatas
- Antes do robô, a advogada pedia o CSV das intimações, perguntava ao ChatGPT
  se havia duplicatas e apagava no VIOS a que não estava no nome do cliente.
- Agora o código detecta (`bot/duplicidade.py`): mesmo processo e texto
  praticamente igual (tirando links, números e códigos, no máximo 10 palavras
  diferentes). É o caso do VIOS trazer uma cópia para cada parte.
- A original é a CI mais completa: primeiro a endereçada ao cliente (as
  palavras que só ela tem batem com o nome do cliente, inclusive iniciais
  como D.D.E.L.L.), depois a de texto maior, depois a de número menor.
- A cópia vira "Duplicada (ignorada)" na página e o robô não lança. Se não for
  duplicata, "Revisar como intimação separada".
- Mesmo processo com ato diferente não é duplicata (ex.: 26/10, perícia
  designada e depois redesignada): fica o alerta para atualizar a tarefa.
- **Não apaga nada no VIOS**: a cópia continua lá como intimação pendente.
- **Duas conferências (29/10/2026):** (1) na **leitura**, a captura marca a
  cópia em `intimacoes_*.json` (`duplicada_de`); (2) no **envio do .txt**, a
  página confere com as capturas ao subir e, na hora de enviar, o robô lê no
  VIOS o teor de cada CI do arquivo (tela "Lançar Intimação", só leitura) e
  compara com as outras CIs e com as capturas. Cópia de CI já lançada ou que
  está no arquivo: não grava ("Duplicata (não lançada)"); cópia de CI que não
  está no arquivo nem foi lançada: erro, para a pessoa conferir. A comparação
  usa só o teor (sem cabeçalho de datas e sem Comarca/Diário/Esfera).
- Resultado 26/10/2026: 42475 → cópia da 42476 (TIAGO ARAUJO DE OLIVEIRA ×
  SERVICOS ADMINISTRATIVOS MEDEIROS LTDA); 42471 → cópia da 42472.

### Passo 18 — Skill em arquivo único (chat de validação)
- A Controladoria confere as análises do bot num chat com a skill. Para o chat
  seguir as mesmas regras, `gerar_skill_unica.py` junta num arquivo só:
  `SKILL.md`, as 5 referências (como seções),
  `doc/skill-unica/regras-do-programa.md` (o que o robô confere e bloqueia no
  envio do `.txt`, como preenche o VIOS e duplicidade) e
  `doc/skill-unica/arquivo-para-o-robo.md` (formato do `.txt`).
- Saída: `doc/skill-unica/analise-intimacoes-controladoria/SKILL.md` e o
  `.zip` para subir no chat. A parte "modo automático" (JSON) fica de fora.
- Toda vez que a skill ou uma regra do código mudar: atualizar
  `regras-do-programa.md` (se for regra do código) e rodar
  `.venv/bin/python gerar_skill_unica.py`.

### Passo 19 — Página de envio do .txt (sem gastar tokens da API)
- Para reduzir o gasto com a API (29/10/2026): a análise é feita no chat com a
  skill única, que entrega o **arquivo para o robô** (`.txt`); a pessoa
  confere/ajusta, sobe na página e o robô só lança no VIOS — sem chamar a IA.
- O bot se chama **Ultron**: a página tem tema escuro e o mascote do Ultron
  ("Crista", `bot/templates/_ultron.html`): robô cromado em pixel-art 16 × 12 com o
  corpo do mascote do Claude, olhos vermelhos que brilham, piscam e flutuam. Arquivos
  avulsos em `doc/mascote/` (`mascote.html` animado, `mascote.svg`, `mascote.png`
  512 × 512). Para mudar o desenho, editar a grade nos dois lugares.
  Basta arrastar o `.txt` para a caixa (ou clicar e escolher): a leitura começa
  sozinha, sem botão.
- `./rodar_envio.sh` abre a página em http://127.0.0.1:5001. Com
  `ENVIO_REDE=true` (ou `--rede`) fica aberta para a rede em
  `http://<IP desta máquina>:5001`, e aí **exige senha** (`ENVIO_SENHA`; o
  navegador pede usuário — qualquer um — e a senha). Sem `ENVIO_SENHA` a
  página não abre na rede, porque grava no VIOS com o usuário do robô. O
  navegador do robô abre nesta máquina (não no computador de quem enviou).
  Se outro computador não conseguir abrir, liberar a porta no firewall:
  `sudo ufw allow 5001/tcp`.
- Formato (`doc/skill-unica/arquivo-para-o-robo.md`): um bloco por tarefa,
  separados por `---`, com `CI:`, `TAREFA:`, `DATA:`, `HORA:`,
  `RESPONSÁVEIS:` e, por último, `DESCRIÇÃO:` (tudo abaixo vai para a
  Observação). Blocos seguidos da mesma CI viram uma CI com várias tarefas.
- Ao ler (`bot/envio_txt.py`), a página confere e mostra cada CI:
  - **não envia** (problema): CI inválida, tarefa fora da lista oficial, data
    inválida (só CIÊNCIA pode ficar sem data → dia do envio), horário fora de
    HH:MM, audiência/perícia/sustentação sem horário, responsável fora da
    lista do VIOS (`saida/responsaveis.json`), descrição vazia, linha fora do
    formato, mesma CI em dois lugares do arquivo;
    CI que a análise do bot marcou como cópia de outra (`duplicada_de`);
  - **avisa**: data já passada, data no fim de semana, descrição com
    "Responsável a marcar" ou "Advogada auxiliar" ("PRIORIDADE RPV" voltou a
    ser permitida com a skill de 30/10);
  - **já lançada**: CI que está em `saida/lancamentos.json`.
- **Edição na página:** depois de subir, cada tarefa aparece num formulário
  (CI, tarefa com a lista oficial para escolher, data, hora, responsáveis,
  descrição e "Remover tarefa"). A pessoa corrige os erros e clica em
  **Salvar e conferir**: a página refaz o `.txt` com os campos e confere de
  novo (mesmas regras da subida). Há também **Editar como texto**, para colar
  ou acrescentar blocos. Com alteração não salva, os botões de envio ficam
  bloqueados. Depois de um envio, dá para corrigir as CIs com erro e enviar de
  novo (as já gravadas aparecem como "Já lançada" e não vão outra vez).
- Botões: **Testar sem gravar** (preenche o formulário do VIOS e tira print,
  como o modo teste) e **Enviar ao VIOS** (grava). O robô entra no VIOS uma
  vez e lança CI por CI com a mesma rotina do `lancar.py` (Adicionar → Gravar
  → confere na Conferência; pula CI que já tem tarefa no VIOS). Um envio por vez.
- **Histórico (não some):** cada envio fica gravado em
  `saida/envios/<data_hora>_<id>.json`, atualizado a cada CI concluída; a página
  carrega tudo ao iniciar. O botão **Histórico** (`/historico`) mostra todos os
  envios e todas as tarefas gravadas no VIOS (`saida/lancamentos.json`), com busca.
  Os envios de 29 e 30/10 anteriores a isso foram reconstruídos do log (só leitura).
- **Velocidade (medida em 31/10/2026, teste sem gravar):** quem manda no tempo é o
  servidor do VIOS. Cada Adicionar leva ~1,5 s, abrir a tela de lançamento ~1,2 s e a
  Conferência ~0,7 s nos horários bons, e o dobro ou mais nos horários lentos (o mesmo
  teste levou 10 s e 24 s com minutos de diferença). O que é do robô (preencher, prints,
  esperas) soma ~1 s por tarefa. Ajustes no navegador ganharam só ~3%; o ganho grande
  seria lançar com 2 ou 3 navegadores em paralelo (o VIOS aceita sessões simultâneas do
  mesmo usuário; falta testar se o quadro provisório é separado por sessão).
- **Vila (painel que só assiste):** cada passo do envio vira um evento em
  `saida/eventos.jsonl` (`bot/eventos.py`); `GET /eventos?desde=N` devolve os novos e
  `/vila` serve a vila (`bot/vila/vila.html`), na mesma origem e com a mesma senha. A
  vila não grava nem aprova nada. Formato em `doc/vila/contrato-eventos.md`.
  Abrir em `http://<IP desta máquina>:5001/vila`. A cópia publicada no GitHub Pages
  (https://ruanpereiradev.github.io/autobots/) só funciona em simulação: de lá ela
  não alcança o Ultron, que está na rede interna.
- **Cena do Ultron (estilo da vila):** no topo da página do envio, o Ultron anda entre
  Doca, Receptor TXT, Conferência e Torre VIOS conforme o andamento real e explica na
  caixa de fala o que está fazendo (`bot/templates/_cena.html`). Mostra só o Ultron.
  Na página inicial ele espera na doca; ao soltar o .txt (na caixa ou em cima da cena),
  vai ao Receptor e a página do envio continua a animação.
- **Acompanhamento ao vivo:** durante o envio a página consulta
  `/envio/<id>/status` a cada 1,5 s e mostra a fase (entrando no VIOS,
  conferindo duplicatas, criando as tarefas), a barra de progresso por tarefa e
  cada CI com as suas tarefas: na fila → criando → no quadro → gravada (ou
  erro). O mascote anima enquanto trabalha, comemora no fim e treme se houver
  erro; no fim aparece o resumo (gravadas, com erro, duplicadas).
- **Arquivo de teste:** se a 1ª linha do `.txt` for `MODO: TESTE`, a página só deixa
  "Testar sem gravar" (o servidor também recusa gravar). Serve para ver o robô
  preenchendo o VIOS com intimações reais sem gravar nada.
- Link de lançamento: o capturado em `saida/intimacoes_*.json`; se a CI não
  estiver em nenhuma captura, o robô monta pelo número (`imp_pub_id`).
- `RESPONSÁVEIS: automático` deixa o VIOS marcar (auxiliar); com nomes, o robô
  marca exatamente essas pessoas e confere na tela.
- Depois de ajustar a análise no chat, a pessoa cola o texto de
  `doc/skill-unica/pedido-arquivo-robo.txt` para o chat gerar o arquivo no
  padrão (mesmas regras da seção "Arquivo para o robô" da skill única).

### Passo 20 — Skill nova da Controladoria (30/10/2026)
- A Controladoria mandou a skill revisada (`doc/skill-original/6_2026-10-30_contagem-simplificada/`),
  que passou a ser a skill do projeto (`doc/analise-intimacoes-controladoria/`).
  Principais mudanças de regra:

| Assunto | Antes | Agora |
| --- | --- | --- |
| Contagem de prazo | Dias úteis sem feriados (tabela + `doc/feriados.txt` + pesquisa na internet) | **Contagem simplificada:** só sábado e domingo ficam de fora; feriados, recesso e suspensões contam como dia útil |
| Análise e ciência | Mesmo dia | Mesmo dia até 12h; depois das 12h, próximo dia de segunda a sexta |
| Análise de sentença/acórdão/decisão | `PRAZO PARA EMBARGOS/RECURSO`, com `NÃO CABE` no que não cabe | `PRAZO DE EMBARGOS:` e `PRAZO DE RECURSO:` sempre com data D-2 (nunca `NÃO CABE`) |
| Minutas | `PRAZO FATAL (D-2):` | `PRAZO FATAL D -2:` |
| RPV/precatório | `PRAZO FATAL:` = data da prioridade, sem `PRIORIDADE` | Data da tarefa = prioridade (próximo dia de segunda a sexta); `PRAZO FATAL:` = D-2 do vencimento + linha `PRIORIDADE RPV` |
| Pagamento pelo cliente no Cível | — | Só análise + minuta (sem tarefa de contato com o cliente) |

- Nova referência `references/validacao-lancamento.md` (quando não lançar e
  checagem final), incluída no prompt do bot (`bot/skill.py`) e na skill única.
- Ajustes no robô: a página de envio não avisa mais sobre `PRIORIDADE RPV`
  na descrição; as linhas `PRAZO FATAL D -2:` também saem em vermelho no VIOS.
  `regras-do-programa.md`, `arquivo-para-o-robo.md` e `pedido-arquivo-robo.txt`
  foram reescritos para as regras novas (exemplos conferidos pelo leitor do
  robô) e a skill única foi regerada.
- **Pendente:** a análise pela API (`./rodar_analise.sh`, `bot/prazos.py` e
  `bot/analise.py`) ainda calcula as datas e monta a descrição pelas regras
  antigas (feriados, `NÃO CABE`, rótulos antigos). O fluxo em uso (análise no
  chat + página de envio) já segue a skill nova.

### Passo 21 — Rodar no Mac e no Linux
- O projeto roda nos dois sistemas com os mesmos arquivos e comandos.
- Scripts `rodar*.sh` sem `readlink -f` (funcionam no macOS e no Linux);
  `pkg_resources==0.0.0` (resto do Ubuntu, quebrava o `pip` no Mac) saiu do
  `requirements.txt`.
- `./instalar.sh` prepara um computador novo: procura o Python 3.12 (aceita
  3.8 a 3.12; no 3.13 o `MarkupSafe` fixado não tem pacote pronto), cria a
  `.venv` (recria se ela veio copiada de outro computador ou é de outra versão
  do Python, conferindo o `.venv/pyvenv.cfg`), instala as
  dependências, cria `saida/` e `logs/` e avisa se faltar `.env` ou o Google
  Chrome. Conferido que todos os pacotes têm versão pronta para Mac com
  Python 3.12 (Apple Silicon e Intel).
- Passo a passo no Mac:
  1. instalar o Google Chrome e o Python 3.12 (`brew install python@3.12` ou
     o instalador do python.org);
  2. copiar a pasta do projeto **sem a `.venv`**, levando também os arquivos
     que não vão para o git: `.env`, `saida/` (principalmente
     `lancamentos.json` e `responsaveis.json`, que evitam lançar em dobro, e
     `envios/`, o histórico da página de envio),
     `doc/feriados.txt` e `doc/feriados-brasil-2026-2027.md`;
  3. no Terminal, dentro da pasta: `./instalar.sh`;
  4. testar: `./rodar_envio.sh` (ou `./rodar.sh` para a captura).
- No Linux nada muda: `./instalar.sh` também serve para reinstalar a `.venv`.
- Diferenças do Mac:
  - com `ENVIO_REDE=true`, o macOS pergunta se o Python pode aceitar
    conexões: clicar em **Permitir** (equivale ao `ufw allow` do Linux);
  - a porta 5000 (página de revisão) é usada pelo AirPlay do macOS: usar
    `./rodar_revisao.sh --porta 5002` ou desligar o "Receptor AirPlay";
  - para a página não parar quando o Mac dormir: `caffeinate -i ./rodar_envio.sh`.

### Passo 22 — Mac como servidor da página de envio
- `./servidor_mac.sh instalar` deixa a página de envio sempre ligada no Mac, pelo
  `launchd` (o gerenciador de serviços do macOS): liga sozinha quando o usuário
  entra no Mac, religa se cair e impede o Mac de dormir enquanto roda
  (`caffeinate -i`). Os outros computadores abrem `http://<IP do Mac>:5001`.
- Antes: `./instalar.sh` feito, `.env` com `ENVIO_REDE=true` e `ENVIO_SENHA`, e
  a `saida/` copiada do computador antigo.
- Comandos: `./servidor_mac.sh instalar` | `parar` | `status` | `log`
  (log em `logs/servidor.log`).
- `instalar` também serve para reiniciar (ex.: depois de mudar o `.env`). Se a
  porta 5001 estiver ocupada (um `./rodar_envio.sh` aberto), ele avisa e para.
- A `saida/` **não vai para o GitHub** (o repositório é público e ela tem dados
  de clientes): copiar com `rsync` ou pendrive (Passo 21).
- Para funcionar sem ninguém por perto:
  - o Mac precisa estar **com o usuário logado** (o serviço roda na sessão
    dele, porque o robô abre o Chrome). Para voltar sozinho depois de faltar
    luz: Ajustes do Sistema → Usuários e Grupos → **Iniciar sessão
    automaticamente**, e Ajustes → Energia → **Iniciar automaticamente após
    falta de energia**;
  - MacBook com a tampa fechada dorme mesmo com o `caffeinate`: deixar a
    tampa aberta (ou com monitor externo e carregador);
  - IP fixo: reservar o IP do Mac no roteador (ou IP manual nos Ajustes de
    Rede), senão o endereço da página pode mudar;
  - na primeira vez o macOS pergunta se o Python pode aceitar conexões:
    **Permitir**.
- Usar só um servidor: com o Mac ligado, não rodar o `./rodar_envio.sh` no
  Linux (cada um teria o seu `lancamentos.json`).

### Passo 23 — A vila mostra o Zangão (bot de comprovantes previdenciários)
- O Zangão (Bumblebee, branch `bot-edita-vios`) manda cada etapa por
  `POST /eventos` ao Ultron, que guarda no `saida/eventos.jsonl`. A Vila 02, em
  `http://<IP do Mac>:5001/vila`, anima a execução e mostra o painel
  "Comprovantes previdenciários" (tarefa pelo `pxe_id`, situação e motivo).
- No `.env` **do Zangão**: `VILA_URL=http://<IP do Mac>:5001/eventos` e
  `VILA_SENHA` = a mesma senha do `ENVIO_SENHA` do Ultron. Vazio = vila desligada.
- O Ultron só aceita eventos do bot `zangao`, com a senha da página, e nunca
  guarda CNJ, órgão julgador, valor nem nome de cliente (contrato em
  `doc/vila/contrato-eventos.md`).
- A vila só assiste: se o Ultron estiver fora do ar, o Zangão segue
  trabalhando (desiste depois de 3 falhas e guarda os eventos em
  `saida/vila_pendentes.jsonl` dele).
- Se a vila for baixada de novo do site: `python3 doc/vila/ligar_zangao.py bot/vila/vila.html`.

### Passo 28 — Albi: .txt de CPF/CNPJ, página `/albi` e Vila 03
- O Albi recebe um `.txt` **organizado por empresa**: a linha `EMPRESA:` e,
  embaixo, uma pessoa por linha, `CPF ; nome` (modelo em `albi/modelo_pedidos.txt`,
  ou "Baixe o modelo" na página `/albi`). `---` separa as empresas (opcional);
  linha vazia ou com `#` no começo é ignorada; o CPF pode vir antes ou depois do
  nome; serve CNPJ também. Sem `EMPRESA:`, vale tudo como uma lista só.
  ```
  EMPRESA: Empresa A
  123.456.789-09 ; Maria da Silva
  987.654.321-00 ; João Souza
  ---
  EMPRESA: Empresa B
  111.444.777-35 ; Ana Lima
  ```
- No Sonar, o "Identificador Projeto" (coluna "Projeto") fica o nome da empresa.
- Uma pessoa por vez, na ordem do arquivo. Se a sessão do Sonar cair no meio,
  entra de novo e tenta a mesma pessoa mais uma vez; erro numa não para as outras.
- Antes de entrar no Sonar ele confere cada linha (11 ou 14 números, dígito
  verificador, repetidos); linha inválida fica de fora e aparece na página.
- Para cada pessoa, uma por vez: Nova Pesquisa → **Identificador Projeto = nome
  da empresa** → Tipo **CPF/CNPJ** → documento → "Continuar" → passo 2 ("Pedido"):
  confere o documento, escolhe o **Sacado** (o escritório; `SONAR_SACADO` no
  `albi/.env`) e clica em **"Confirmar Pedido"** (R$ 15,70 cada). Guarda o número
  do pedido.
- Depois espera o Sonar terminar cada pedido (até `SONAR_ESPERA_MIN`, padrão 120
  min) e baixa o resultado de **cada pessoa**: o **PDF da página do pedido** (todos,
  inclusive "não consta") e, de quem tem processos encontrados, a **planilha**
  ("Baixar Resultados"), em `<empresa>/S<pedido> - <nome>.pdf` / `.xls`. Escreve o
  `resultado.txt` (por empresa: CPF ; nome ; pedido ; resultado ; arquivos). Tudo em
  `saida/albi/<id>/` do Ultron, para baixar na página.
- **Relatório dos processos** (automático, no fim): o Albi lê as planilhas e escreve
  `relatorio.html`, `relatorio.pdf` e `processos.csv` na pasta da execução. Por empresa,
  traz o resumo de todos e, de cada processo de quem tem processos: número CNJ, tribunal,
  vara, ramo, ação, assunto, data, papel da pessoa (ré/autora, pelo CPF), outra parte,
  valor e status. Na página: "Ver relatório dos processos", "relatório PDF" e
  "processos.csv (Excel)". Numa execução antiga, use "Gerar relatório dos processos", que
  usa o que já foi baixado e não entra no Sonar. Pelo terminal: `cd albi &&
  .venv/bin/python relatorio.py <pasta>`.
- **Capturar resumo**: o botão "Capturar resumo (mensagem para a empresa)" abre a mensagem
  pronta para cada empresa (também em `mensagem.txt`): quantas pessoas foram pesquisadas,
  quem tem processos (em andamento, encerrados, como ré, trabalhista/criminal e os em
  andamento com número e vara) e quem não tem, com a assinatura do escritório e o CPF
  mascarado. Dá para editar no campo, clicar em "Copiar mensagem" e mandar junto o
  relatório PDF.
- **Mensagens da CAC** (na mesma tela do "Capturar resumo"): uma mensagem por pessoa com
  processos, no padrão da Central de Atendimento ao Cliente (abertura com a atendente,
  "*1️⃣ Autor x Réu*", "Trata-se de…", assunto, valor, situação atual, conclusão e ressalva).
  Escolha a atendente (Beatriz Vasconcelos ou Renara Kathleem), revise e clique em "Copiar
  mensagem". Ela usa só os registros do Sonar (cadastro do processo): fatos, movimentações e
  decisões não vêm do Sonar, então não aparecem. Arquivos: `mensagens_cac.txt` e `.json`
  (`albi/mensagem_cac.py`).
- **Baixar de novo** (não compra): na execução já confirmada, o botão "Baixar de novo
  os resultados de cada um" (ou `./rodar.sh --arquivo X --baixar`) pega o número de
  cada pedido no registro e baixa de novo o PDF e a planilha, sem abrir a Nova
  Pesquisa. Quem não tem pedido no registro fica como "Sem pedido no registro".
- Não compra duas vezes: CPF já pesquisado para a mesma empresa nos últimos 30
  dias usa o pedido anterior (registro `albi/saida/pedidos_confirmados.json`).
- Pela página: `http://<IP do Mac>:5001/albi` (link "Albi" no topo do Ultron).
  Soltar o `.txt` na caixa: o Albi **só confere** e mostra quem vai ser
  pesquisado e o **total em R$**. "Só testar" faz tudo menos confirmar;
  "Confirmar e pesquisar" (dois cliques) compra. Roda em segundo plano (um por
  vez, até 500 linhas); a página mostra cada pessoa ao vivo, agrupada por
  empresa, com o pedido, o resultado e os links do PDF, da planilha e do .zip. Histórico em `/albi/historico`.
  O arquivo fica em `saida/albi/<id>.txt`; o log do Albi em
  `albi/logs/execucoes_ultron.log`.
- Pelo terminal: `cd albi && ./rodar.sh --arquivo pedidos.txt` (teste) ou
  `... --confirmar` (compra; resultado em `albi/saida/<data_hora>/`) ou `... --baixar`
  (só baixa de novo os resultados dos pedidos já comprados).
- Se a Vila 03 for reaplicada: `python3 doc/vila/ligar_albi.py bot/vila/vila.html` (etapas
  1 a 4; pode rodar de novo, não repete).
- A **Vila 03** acendeu: é a vila do Albi (Doca 01 · Albi, Receptor TXT,
  Conferência, Torre Sonar), com o mascote dele (`albi/mascote/`). Os eventos
  levam só o número da linha, o número da empresa e o final do documento
  ("Empresa 1 · CPF final 06"), nunca o documento inteiro, o nome da pessoa nem o
  da empresa.
- O Ultron acha o Albi em `albi/` deste repositório; noutra pasta, `ALBI_PASTA`
  no `.env` do Ultron.
- Se a vila for baixada de novo do site: `python3 doc/vila/ligar_zangao.py
  bot/vila/vila.html`, depois `python3 doc/vila/ligar_albi.py bot/vila/vila.html` e por
  último `python3 doc/vila/ligar_bumblebee.py bot/vila/vila.html`.

### Passo 29 — Zangão vira Bumblebee (robô que se transforma em carro)
- O bot de comprovantes previdenciários passa a se chamar **Bumblebee** no que aparece na tela:
  página (`/zangao`), links do topo, Vila 02 (placa, abas, fala e registro) e mensagens de erro.
  O código interno não muda: rotas `/zangao`, `ZANGAO_PASTA`, eventos `bot: "zangao"`.
- Mascote novo (desenho em `doc/mascote/zangao-transforma.html`): robô amarelo 24×26. **Para
  andar, ele se transforma em carro**: as peças voam e encaixam no chassi; só depois ele sai
  rodando (farol, rodas girando e poeira). Ao chegar, desfaz e volta a robô.
  - Vila 02: `doc/vila/ligar_bumblebee.py` (rodar depois do `ligar_zangao.py` e do
    `ligar_albi.py`; não repete se rodar de novo).
  - Página `/zangao`: o robô no topo (SVG) e, na cena, um canvas com a mesma transformação
    (`bot/templates/_zangao.html`: `zangao_cena()` e `bumblebee_script()`). Com "reduzir
    movimento" ligado no sistema, a troca é direta, sem animação.

### Passo 27 — Segurança das rotas
- Com `ENVIO_REDE=true`, toda rota (GET e POST) pede a senha (`ENVIO_SENHA`).
- POST que vem de outro site é recusado (403): o navegador guarda a senha e a
  mandaria junto num POST disparado por outra página aberta nele. Só a própria
  página (mesmo endereço) e programas sem navegador (o Zangão mandando eventos)
  passam, e ainda precisam da senha.
- A senha vai pela rede local sem criptografia (http): usar só na rede do
  escritório, nunca abrir a porta 5001 para a internet.

### Passo 26 — Albi, bot do Sonar (pasta `albi/`)
- Terceiro bot, que funciona de forma totalmente diferente do Ultron e do
  Zangão: fica em `albi/`, com `.venv`, `.env`, `logs/` e `saida/` próprios, e
  não usa nada do `bot/`. Detalhes em `albi/README.md`.
- Entra em https://sonar.lemeforense.com.br/login (CPF/CNPJ, e-mail e senha). Se
  cair na tela de conflito (`/login-conflito`: sessão aberta em outro lugar), clica
  em "Encerrar a outra sessão" e, se voltar para o login, entra de novo.
- Depois vai direto para Pesquisa de Processos > Nova Pesquisa
  (`/modulos/pesquisa-processos/novo-pedido`, a tela do botão "Iniciar Pesquisa").
  Daí em diante, ver o passo 28 (pedidos pelo `.txt`).
- Instalar: `cd albi && ./instalar.sh`; preencher `albi/.env`
  (`SONAR_CPF_CNPJ`, `SONAR_EMAIL`, `SONAR_SENHA`; modelo comentado em
  `albi/.env.example`); testar: `./rodar.sh` (diz "Login OK" e "Tela de novo
  pedido aberta", ou o motivo).

### Passo 25 — Vila dos bots no topo da página do Ultron
- Na página do Ultron (`http://<IP do Mac>:5001/`), o topo é a vila dos bots
  (Vila 01 · Ultron, com os eventos reais); abaixo ficam a caixa do .txt, a
  conferência, os botões e o histórico, como antes. Pela vila (setas ou
  "02 · Zangão") dá para ir à Vila 02 e rodar o Zangão.
- `/vila?vila=2` abre a vila direto na Vila 02. Ao abrir, a vila anima o que
  aconteceu nos últimos 30 s (por isso, ao subir o .txt, aparece o Ultron indo
  buscar o arquivo e conferindo).

### Passo 24 — Rodar o Zangão pela vila ou pela página dele (Mac)
- O Zangão fica instalado no Mac, numa pasta própria (`~/zangao`, branch
  `bot-edita-vios`, com `.venv` e `.env` dele), e o `.env` do Ultron aponta para
  ela: `ZANGAO_PASTA=~/zangao`.
- **Pela vila** (o jeito principal): `http://<IP do Mac>:5001/vila` → Vila 02 ·
  Zangão. Os botões "Testar sem gravar" e "Rodar e gravar no VIOS" (este só nos
  3 últimos dias, com confirmação) ficam na caixa de fala; enquanto ele roda, os
  botões somem e a vila mostra cada passo. A vila do GitHub
  (`ruanpereiradev.github.io/autobots`) é só simulação.
- Página: `http://<IP do Mac>:5001/zangao` (mesma senha; também pelo botão
  "Zangão" no topo da página do Ultron ou "Página do Zangão" na Vila 02). É a
  mesma tela do Ultron: cena com o Zangão andando entre Doca, Filtro
  previdenciário, Captura de dados e Torre VIOS conforme o andamento real.
  - **Testar sem gravar**: qualquer dia; roda `main.py --fora-da-janela`
    (preenche a tela de edição e não grava);
  - **Rodar e gravar no VIOS**: só nos 3 últimos dias do mês; o primeiro
    clique vira "Confirmar: gravar no VIOS" e só o segundo clique (em até 6 s)
    roda `main.py --confirmar`;
  - abaixo, a execução atual (ou a última) ao vivo: barra, contagens e cada
    tarefa com a situação e o motivo; **Histórico** lista todas.
- O Zangão roda em segundo plano, como processo separado: continua mesmo se a
  página do Ultron reiniciar. Uma execução por vez (os botões travam).
- Roda com ambiente limpo: nenhuma variável do Ultron (senhas, chaves de API)
  chega ao Zangão; ele usa só o `.env` da pasta dele.
- Saída de cada execução: `~/zangao/logs/execucoes_vila.log` (além do
  `logs/bot.log` e do relatório CSV do próprio Zangão).
- Rotas do Ultron (mesma senha da página): `/zangao`, `/zangao/historico`,
  `/zangao/execucao/<id>`, `/zangao/andamento`, `/zangao/status` e
  `POST /zangao/rodar` com `{"modo": "teste"}` ou `{"modo": "gravar"}`. O POST
  só aceita pedido da própria página (JSON e mesma origem), para outro site não
  conseguir usar a senha guardada no navegador.
- Também dá para rodar pelo Terminal do Mac: `cd ~/zangao && .venv/bin/python
  main.py --fora-da-janela` (teste) ou `--confirmar` (gravar, nos 3 últimos dias).
- A vila não reprisa mais o que aconteceu com a aba escondida: ao voltar para a
  aba (ou com muitos eventos acumulados), ela pula direto para o estado atual
  (vale para o Ultron e o Zangão).

---

## 3. Estrutura do projeto

```
selenium/
├── main.py              # ponto de entrada: login → navegação → extração
├── rodar.sh             # roda o bot usando a .venv e o .env do projeto
├── analisar.py          # analisa um intimacoes_*.json com o agente
├── rodar_analise.sh     # atalho para analisar.py
├── lancar.py            # lança no VIOS as tarefas da análise (--ci, --confirmar)
├── rodar_lancamento.sh  # atalho para lancar.py
├── revisar.py           # importa análises e abre a página de revisão
├── rodar_revisao.sh     # atalho para revisar.py
├── gerar_skill_unica.py # skill + referências + regras do programa num arquivo só (chat de validação)
├── enviar.py            # página de envio: sobe o .txt ajustado e lança no VIOS (sem IA)
├── rodar_envio.sh       # atalho para enviar.py
├── instalar.sh          # prepara um computador novo (Mac ou Linux): .venv + dependências
├── albi/              # Albi, bot do Sonar (separado: .venv, .env, logs/ e saida/ próprios)
├── servidor_mac.sh      # Mac: página de envio como serviço (launchd) — instalar/parar/status/log
├── bot/
│   ├── config.py        # lê e valida o .env; converte seletores
│   ├── navegador.py     # cria o Chrome e funções esperar/clicar/preencher
│   ├── login.py         # faz o login e confirma
│   ├── navegacao.py     # cliques em sequência e/ou URL final
│   ├── extracao.py      # extrai tabela ou cards genéricos e salva .txt
│   ├── intimacoes.py    # pesquisa intimações por data no VIOS e salva .json
│   ├── analise.py       # agente: IA + skill -> tarefas sugeridas + relatório
│   ├── lancamento.py    # preenche "Lançar Intimação", Adicionar → Gravar → confere
│   ├── skill.py         # carrega a skill e a lista oficial de tarefas
│   ├── duplicidade.py   # detecta a mesma publicação em duas CIs (a cópia é ignorada)
│   ├── revisao.py       # banco SQLite da revisão (CIs, tarefas editadas, estados)
│   ├── web.py           # página de revisão (Flask)
│   ├── envio_txt.py     # lê e confere o .txt da página de envio
│   ├── envio_web.py     # página de envio do .txt (Flask)
│   ├── eventos.py       # eventos para a vila (saida/eventos.jsonl, GET /eventos; POST /eventos do Zangão)
│   ├── zangao.py        # roda o Zangão em segundo plano pela vila (/zangao/status, /zangao/rodar)
│   ├── albi.py          # página /albi: guarda o .txt, roda o Albi e repassa os eventos dele à vila
│   ├── vila/            # vila.html (servido em /vila)
│   ├── templates/       # HTML das páginas de revisão, de envio, do Zangão e do Albi (albi.html);
│   │                    # _estilo.html = estilo comum; _ultron.html / _zangao.html / _albi.html = mascotes;
│   │                    # _vila.html = vila embutida no topo da página do Ultron
│   ├── prazos.py        # dias úteis, feriados, prazo fatal, D-2
│   └── ia/              # provedores de IA: openai_ia.py, anthropic_ia.py
├── .env                 # configuração real (NÃO versionar — tem senha)
├── .env.example         # modelo do .env
├── saida/               # arquivos .txt gerados
├── logs/                # bot.log e screenshots de erro
├── doc/                 # prints, zip e skill extraída (analise-intimacoes-controladoria/)
├── DOCUMENTACAO.md      # este arquivo
└── CHANGELOG.md         # histórico de mudanças
```

### Fluxo de execução (`main.py`)

```
carregar .env ──► criar Chrome ──► login ──► navegação ──► pesquisa (datas + Área: todas) ──► ler tabela ──► salvar .json
                                      │            │             │
                                      └────────────┴─────────────┴──► erro: screenshot em logs/ + log
```

---

## 4. Como rodar

```bash
./rodar.sh                 # usa o .env do projeto
./rodar.sh outro.env       # usa outro arquivo de configuração
```

Ou: `.venv/bin/python main.py`

Analisar e lançar uma CI:

```bash
./rodar_analise.sh --ci 42431 saida/intimacoes_2026-10-23_a_2026-10-25.json
./rodar_lancamento.sh --ci 42431              # modo teste: adiciona e NÃO grava
./rodar_lancamento.sh --ci 42431 --confirmar  # grava no VIOS
```

Revisar e validar na página (abre em http://127.0.0.1:5000):

```bash
./rodar_revisao.sh saida/analise_2026-10-26.json   # importa e abre
./rodar_revisao.sh                                   # só abre (CIs já importadas)
./rodar_revisao.sh --atualizar-responsaveis          # relê do VIOS a lista de responsáveis
```

Subir o .txt com as tarefas já ajustadas e lançar (abre em http://127.0.0.1:5001):

```bash
./rodar_envio.sh
```

Gerar a skill em arquivo único para o chat de validação:

```bash
.venv/bin/python gerar_skill_unica.py
```

Primeira instalação (Mac ou Linux — ver Passo 21):

```bash
./instalar.sh              # cria a .venv e instala as dependências
cp .env.example .env       # se não trouxe o .env de outro computador, e preencher
```

O chromedriver é baixado automaticamente pelo Selenium Manager.

---

## 5. Configuração (`.env`)

Seletores sempre no formato `css:<seletor>` ou `xpath:<expressão>`.

| Variável | Obrigatória | Uso | Valor atual (VIOS) |
| --- | --- | --- | --- |
| `SISTEMA_URL` | sim | Página de login | `https://roneely.vios.com.br/entrar.php?` |
| `SISTEMA_USUARIO` / `SISTEMA_SENHA` | sim | Credenciais | (no `.env`) |
| `LOGIN_CAMPO_USUARIO` | sim | Campo de usuário | `css:input[name='form[usuario]']` |
| `LOGIN_CAMPO_SENHA` | sim | Campo de senha | `css:input[name='form[senha]']` |
| `LOGIN_BOTAO` | não | Botão de entrar (vazio = Enter) | vazio |
| `LOGIN_SUCESSO` | não | Elemento que aparece após logar (vazio = URL muda) | vazio |
| `NAVEGACAO_PASSOS` | não | Cliques em ordem, separados por `\|` | vazio |
| `NAVEGACAO_URL_FINAL` | não | URL aberta depois dos cliques | `.../index.php?pag=sys/publicacoes/int-pesquisa.php` |
| `PESQUISA_CAMPO_DATA` | não | Campo de data da pesquisa; ativa o fluxo de intimações (prioridade sobre CARD/TABELA) | `css:input[name='pesq[fdata]']` |
| `PESQUISA_MARCAR_TODAS` | não | Filtros em que clicar "Marcar todas", separados por `\|` | `pesq[pr_areas_id][]` (Área) |
| `PESQUISA_DIAS_ATRAS` | não | Quantos dias antes de hoje é a data final (se cair no domingo, começa na sexta) | `1` (ontem) |
| `TABELA` / `TABELA_TEM_CABECALHO` | não | Extração em tabela | vazio |
| `CARD` / `CARD_CABECALHO` / `CARD_TEXTO` | não | Modo antigo (cards); ignorado quando `PESQUISA_CAMPO_DATA` está definido | `.vj-card-intimacao` etc. |
| `ANALISE_ATIVA` | não | Analisar com IA logo após capturar | `false` |
| `LLM_PROVEDOR` | não | `openai` ou `anthropic` | `openai` |
| `LLM_MODELO` | não | Modelo (vazio = padrão: `gpt-5.6` / `claude-opus-5-5`) | vazio |
| `LLM_ESFORCO` | não | Esforço de raciocínio (`low`/`medium`/`high`) | `medium` |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | para analisar | Chave da API do provedor | (no `.env`) |
| `SKILL_PASTA` | não | Pasta da skill extraída | `doc/analise-intimacoes-controladoria` |
| `FERIADOS_TABELA` | não | Tabela de feriados (nacionais, estaduais, capitais, pontos facultativos) | `doc/feriados-brasil-2026-2027.md` |
| `FERIADOS_ARQUIVO` | não | Feriados/suspensões extras: `DD/MM/AAAA ; ESCOPO ; descrição` | `doc/feriados.txt` |
| `LLM_LOTE` | não | Análise em lote pela Batch API da OpenAI ou Message Batches do Claude (metade do preço) | `true` |
| `LLM_LOTE_ESPERA_MIN` | não | Minutos esperando o lote; depois cancela e faz o resto uma a uma | `360` |
| `LLM_MODELO_SIMPLES` | não | Modelo barato para as intimações simples (triagem); vazio = desligado | vazio |
| `LLM_MODELO_FERIADOS` | não | Modelo da pesquisa de feriados (vazio = `LLM_MODELO`) | vazio |
| `LLM_LIMITE_US` | não | Teto de gasto com IA por execução, em US$ (vazio/0 = sem teto) | vazio |
| `LLM_PRECOS` | não | Corrige preços da tabela: `modelo=entrada/saída` por milhão de tokens, separados por vírgula | vazio |
| `FERIADOS_PESQUISA` | não | Pesquisa feriados na internet antes da análise (`true`/`false`) | `true` |
| `SAIDA_PASTA` | não | Pasta dos `.txt` | `saida` |
| `HEADLESS` | não | Chrome sem janela | `false` |
| `TIMEOUT` | não | Espera máxima (s) | `20` |
| `MANTER_ABERTO` | não | Não fecha o Chrome no fim | `true` |
| `NAVEGADOR_RAPIDO` | não | O Chrome não espera recursos do VIOS que o robô não usa (ganho pequeno, ~3%) | `true` (padrão) |
| `ENVIO_REDE` | não | Página de envio aberta para a rede (padrão: só nesta máquina) | `true` |
| `ENVIO_SENHA` | com `ENVIO_REDE=true` | Senha pedida pela página de envio | (definir no `.env`) |
| `ZANGAO_PASTA` | não | Pasta do Zangão neste computador (com `.venv` e `.env` dele); liga os botões da Vila 02 | `~/zangao` |
| `ALBI_PASTA` | não | Pasta do Albi (com `.venv` e `.env` dele); vazio = `albi/` deste repositório | `~/albi` |

---

## 6. Saída e logs

- `saida/intimacoes_AAAA-MM-DD.json` — lista de intimações da data pesquisada;
  na segunda, `intimacoes_AAAA-MM-DD_a_AAAA-MM-DD.json` (sexta a domingo).
  Rodar de novo para o mesmo período sobrescreve o arquivo. Campos de cada intimação:
  `ci`, `disponibilizacao`, `publicacao`, `numeros`, `cliente`, `advogado`,
  `auxiliares`, `oab`, `cidade`, `fornecedor`, `informacoes_extras`, `situacao`,
  `sugestoes_tarefa` (lista), `texto`, `comunicacao_id`, `link_lancar`.
- `saida/intimacoes_*.txt` — formato antigo (modo cards).
- `saida/analise_<periodo>.md` — relatório do agente no padrão da skill (uma CI
  por bloco: tarefas com descrição pronta para copiar, prazos, alertas ⚠ e link
  "Lançar no VIOS"). `saida/analise_<periodo>.json` — o mesmo em dados.
- `saida/lancamentos.json` — CIs lançadas no VIOS (data/hora, tarefa, data,
  responsáveis); impede lançar a mesma CI de novo.
- `saida/revisao.db` — banco da página de revisão: tarefas editadas, estado
  de cada CI, quem validou e quando.
- `saida/responsaveis.json` — pessoas do campo Responsáveis do VIOS.
- `logs/lancamento_ci<CI>_*.png` — prints do formulário e do quadro "Tarefas".
- `logs/bot.log` — tudo o que o bot fez (a senha nunca é registrada).
- `logs/erro_*.png` — screenshot da tela no momento de qualquer erro.
- Card ou linha com problema é **pulado** e registrado como `WARNING`;
  o bot continua com os demais.

---

## 7. Próximos passos

1. ~~Separar cada intimação em campos~~ ✅ feito no Passo 9.
2. ~~Duplicatas no mesmo dia~~ ✅ detectadas e ignoradas (Passo 17). Falta: duplicata que volta
   em outro dia (guardar os textos/`comunicacao_id` já processados).
3. ~~Analisar cada intimação com a skill~~ ✅ agente pronto e testado (Passo 12) —
   falta a Controladoria comparar com o ChatGPT.
4. ~~Criar a tarefa no VIOS~~ ✅ por CI (Passo 14). Próximo: lançar todas as CIs
   do dia depois que a Controladoria validar as análises.
   Pré-requisito: Python 3.8 limita os SDKs (`openai` 2.2.0, `anthropic` 0.72);
   atualizar o Python para 3.10+ libera as versões novas.
5. ~~Textos cortados em "Mostrar mais"~~ ✅ resolvido com a tabela.
6. ~~Segunda-feira~~ ✅ pesquisa sexta a domingo (Passo 10).
7. Feriados ainda não são tratados (ex.: dia seguinte a um feriado pega só o feriado).

---

## 8. Regra de manutenção

**Toda mudança no projeto deve ser registrada no [CHANGELOG.md](CHANGELOG.md)**
e, quando mudar o funcionamento, também nesta documentação.
