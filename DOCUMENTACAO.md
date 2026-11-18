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
- Recebido `analise-intimacoes-controladoria.zip` (hoje extraído em `doc/skill-original/<versão>/`), com as regras da
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
- A skill do ChatGPT (`analise-intimacoes-controladoria.zip`) foi extraída em
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
- **Modelo mais barato (10/11/2026):** `LLM_MODELO=claude-haiku-5-5` e `LLM_MODELO_SIMPLES=`
  vazio (um modelo só). Custo estimado com os tokens reais de 26–27/10, em lote: ~US$ 0,0013
  por intimação (~US$ 0,70 por mês), contra ~US$ 0,05 do Opus. O Haiku não tem fallback de
  recusa no servidor: o bot manda o pedido sem esse campo.
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
| Número do processo | Cada CI mostra o número do processo na página de envio (do `PROCESSO:` do .txt; sem ele, do capturado no VIOS: campo Números ou o teor). Sem número, fora do formato ou diferente do capturado: aviso |
| Data (corte das 12h) | `CIÊNCIA` e `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` com data de hoje, lançadas depois das 12:00 (ou no fim de semana), vão para o próximo dia de segunda a sexta (sexta 12:01 → segunda). Só a data da tarefa: as linhas de embargos, recurso e prazo fatal não mudam. Se uma delas vier antes do novo dia, fica hoje (urgente, aparece no log). A hora é a do computador do servidor, na hora de preencher cada tarefa |
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
- **Data que já passou:** as datas (D-2, dia seguinte, data informada) vêm
  prontas da análise. Se alguma tarefa da CI ficar com data anterior ao dia do
  lançamento (análise de um dia lançada em outro), nada é lançado: a CI fica
  **bloqueada** com o motivo e é preciso refazer a análise. Vale para o
  `lancar.py` e para a página web. Tarefa do mesmo dia e ciência sem data não
  entram nisso (são sempre o dia do lançamento).
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
> **Desligado desde 10/11/2026** (`DUPLICIDADE_ATIVA=false`, o padrão): a Controladoria já tira as
> duplicadas na tela de intimações do VIOS, e o detector marcava como cópia CIs que não eram.
> Desligado, nenhuma CI é tratada como cópia: nem na captura, nem na análise, nem no envio do
> `.txt` (o robô também deixa de ler o teor no VIOS antes de gravar). Religar:
> `DUPLICIDADE_ATIVA=true` no `.env`.

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
- **Envio conferido de novo depois de enviado** ("Salvar e conferir" num envio já concluído): a
  conferência nova apaga o resultado de cada CI e o envio volta a "conferido". O histórico e o `/sam`
  mostram mesmo assim o resultado do último envio (Concluído, gravadas, já no VIOS), com a nota
  "conferido de novo depois", e a página do envio avisa "Este arquivo já foi enviado em ...". O
  resultado vem do último `envio_fim` desse envio em `saida/eventos.jsonl` (vale também para os
  envios antigos). Caso real: `analise_2026-11-10_complementar.txt` (10/11, 10 gravadas e 2 já no VIOS).
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
- ~~Pendente: a análise pela API ainda monta a descrição pelas regras antigas~~ —
  resolvido no Passo 37 (10/11/2026).
- **Feriado é dia útil no código (10/11/2026):** `bot/prazos.py` passou a usar a
  contagem simplificada (`PRAZO_CONTAGEM=simplificada`, o padrão): só sábado e
  domingo ficam de fora; feriados, pontos facultativos, **recesso de 20/12 a 20/01**
  e suspensões contam como dia útil. Vale para prazo fatal, D-2, próximo dia útil
  (prioridade RPV/emenda, aviso de perícia social) e para as datas refeitas na
  página de revisão. Exemplo da skill: publicação 29/10/2026 + 5 dias = 05/11/2026,
  D-2 = 03/11/2026. O relatório mostra no lugar do calendário a frase "Contagem
  solicitada: segunda a sexta, incluindo feriados; vencimentos sem validação do
  calendário judicial oficial." Com a contagem simplificada, a pesquisa de feriados
  na internet (Passo 13) não roda e não há mais alerta de feriado municipal não
  cadastrado. Para voltar ao calendário antigo: `PRAZO_CONTAGEM=feriados` no `.env`.

### Passo 37 — Skill de 10/11/2026 na análise pela API (Claude Haiku 5.5)
- A Controladoria mandou a skill revisada (`doc/skill-original/7_2026-11-10_txt-bot-duplicadas/`),
  que passou a ser a skill do projeto (`doc/analise-intimacoes-controladoria/`). Ela traz
  `references/saida-txt-bot.md` (formato do `.txt` do chat), que o bot não usa no prompt.
- A análise pela API (`./rodar_analise.sh`) segue as regras novas:

| Tarefa | DATA no VIOS | Linha de prazo na descrição |
| --- | --- | --- |
| ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO | mesmo dia (corte das 12h no lançamento) | `PRAZO PARA EMBARGOS:` e `PRAZO PARA RECURSO:`, sempre os dois, em D-2 (nunca `NÃO CABE` nem `PRAZO FATAL`) |
| Minutas e demais tarefas com prazo | D-2 | `PRAZO FATAL D -2:` |
| RPV/precatório (prioridade) | próximo dia útil após a publicação | `PRAZO FATAL:` com o D-2 do prazo |
| Emenda da Suhiane (prioridade) | próximo dia útil após a publicação | `PRAZO FATAL D -2:` com o D-2 do prazo |

- Análise sem prazo para calcular embargos ou recurso, ou tarefa com prazo sem data para a
  linha, não é lançada (bloqueio). Linhas `PRIORIDADE ...` saem da descrição.
- Modelo: `LLM_MODELO=claude-haiku-5-5`, `LLM_MODELO_SIMPLES=` vazio (ver Passo 12).

### Passo 38 — Tela "Envio automático" (`/automatico`): relatório de conferência
- Na página do Sam (`./rodar_envio.sh`): cartão **Envio automático** (último envio com os números e os
  outros dias) e botão **Envio automático** no topo. Endereço: `http://<IP>:5001/automatico`.
- **Filtro por dia de envio**: o dia em que as tarefas foram gravadas (ou barradas) no VIOS, não o dia
  das intimações. Cada análise do dia inteiro (`saida/analise_<dia>.json`) entra no dia de envio da
  maioria das CIs dela (o "quando" de `lancamentos.json` / `automatico_resultados.json`); duas análises
  enviadas no mesmo dia aparecem juntas. Análise que nunca foi enviada fica no dia em que foi feita,
  marcada **não enviada**. Outro dia: `/automatico/2026-11-10`.
- O relatório (`bot/conferencia.py`), com foco nos prazos:
  - números do dia: intimações, lançadas, não lançadas, contas de prazo conferidas, com ponto de
    atenção, gasto da IA;
  - "Como ler os prazos": contagem simplificada, D-2, corte das 12h e os **feriados nacionais** do
    período, que contaram como dia útil (a data fica 1 dia útil antes do vencimento real);
  - visão geral: uma linha por CI com tarefa, data da tarefa, prazo fatal, D-2, embargos e recurso;
  - um cartão por CI: prazos (trecho, dias lidos pela IA, fatal, D-2, embargos, recurso, cabimento),
    **conferência da conta** (cada data refeita por fora a partir dos dias que a IA leu: ✓ bate,
    ✗ diverge), tarefas (data da análise × data no VIOS, responsáveis, observação com as linhas de
    prazo em vermelho), o que a IA entendeu, pendências e o teor da intimação;
  - **pontos de atenção**: não lançada (com a data de prazo mais próxima, para conferir se a
    Controladoria lançou à mão), tarefa em feriado nacional ou depois do prazo fatal, CIÊNCIA com
    prazo calculado, prazo no texto sem data, data no VIOS diferente da análise (fora o corte das 12h)
    e os alertas da análise.
- Não lançadas primeiro, depois as lançadas, cada grupo pela data mais próxima. Filtros: todas, não
  lançadas, lançadas, com atenção, e busca. **Imprimir / PDF** sai só o relatório, em papel claro.
- A conta refeita segue a contagem simplificada: só vale para a análise feita por ela (linha "Contagem"
  = "Contagem solicitada: segunda a sexta, incluindo feriados..."). As análises de antes de 10/11/2026
  usaram o calendário de feriados de cada tribunal e ficam sem a conta refeita (nem divergência falsa).

| O que foi | De onde vem |
| --- | --- |
| Lançada no VIOS (tarefas, data, responsáveis, link "Ver no VIOS") | `saida/lancamentos.json` |
| Não lançada — falta informação / erro / duplicada / já tinha tarefa / conferência humana / tirada da lista | `saida/automatico_resultados.json` (o lançamento com `--confirmar` grava o motivo de cada CI) |
| Ainda não enviada | análise feita, lançamento ainda não rodou |

- A página lê a pasta `saida/` do computador onde roda: o que foi analisado e lançado em outro
  computador não aparece nela.
- Visual: ver o Passo 39 (Fortaleza do Dragão). O relatório fica num pergaminho claro com moldura
  dourada.

### Passo 39 — Vila do Sam: a Fortaleza do Dragão (estilo Senhor dos Anéis)
- Design: `doc/desing_sam/fortaleza-dragao.html` (cena lateral em pixel art: fortaleza, montanhas, o
  dragão no salão do tesouro, a comitiva). Instalado em **`bot/vila/fortaleza.html`**, servido em
  **`/vila/sam`** e mostrado no topo das páginas do Sam (`/sam` e a página de cada envio), no lugar
  da Vila 01 (macro `fortaleza_cartao()` em `bot/templates/_vila.html`).
- Ligada aos **eventos reais do Sam** (`GET /eventos` a cada 2 s, só os do bot `ultron`; contrato em
  `doc/vila/contrato-eventos.md`). Ao abrir, monta o estado do último envio sem animar; depois anima
  cada evento novo, um por vez:

| Evento | Na fortaleza |
| --- | --- |
| `arquivo_subido` | Missão: TXT recebido ✓. O Mensageiro avisa que o TXT chegou |
| `conferido` | CIs conferidas ✓; "Tarefas criadas 0/N" (N = tarefas das CIs prontas). A Arqueira dá as contagens |
| `envio_iniciado` | Rumo à Torre VIOS (ou "Ensaio: nada é gravado" no modo teste) |
| `fase` | entrando no VIOS (Ferreiro), conferindo duplicatas (Mago), criando tarefas: **o dragão desperta** |
| `ci` gravada (no teste: `no_quadro`) | +1 em "Tarefas criadas", faixa "Tarefa n/N criada" e a vida da Torre VIOS cai na mesma proporção |
| `ci` erro | a Torre diz o motivo e o dragão cospe fogo num herói |
| `ci` ja_tinha / duplicata | o Mago avisa e segue |
| `envio_fim` | "Missão cumprida" (ou "Ensaio concluído" / "A missão parou"), com as contagens; o dragão volta ao covil |

- Fora de um envio a cena continua viva como no design (o dragão às vezes acorda e ataca, os comandos
  Atacar / Magia / Escudo funcionam e **Demonstração** roda o envio de mentira). Durante um envio real
  a demonstração fica desligada e a vida do dragão segue os eventos. Sem conexão com `/eventos`, o
  quadro da missão mostra "Sem conexão" e tenta de novo.
- As páginas do Sam (`/sam`, histórico, envio, envio automático) seguem o estilo da fortaleza pela
  classe `tema-vila` de `bot/templates/_estilo.html`: noite azul sobre fundo escuro, quadros escuros com
  moldura dourada, botões dourados, fontes Lora (texto) e Silkscreen (marca e dias do relatório).
- **Na Vila dos Bots** (página inicial `/` e `/vila`): a aba **01 · Sam** também mostra a Fortaleza,
  por cima da Vila 01 antiga; a barra do topo (Órbita, status, abas 01 a 05) continua por cima e as
  outras abas não mudam. Patch: `doc/vila/ligar_vila01_fortaleza.py bot/vila/vila.html` (rodar de
  novo não repete; rodar outra vez se `bot/vila/vila.html` for baixado de novo).
- As páginas dos outros bots não mudam.
- Para atualizar o design: trocar o desenho em `bot/vila/fortaleza.html` mantendo o bloco
  "eventos reais do Sam" do fim do script e os ganchos `emEnvio()` (o dragão não acorda nem recua
  sozinho durante um envio). Não precisa reiniciar a página.

### Passo 40 — Envio automático em um clique (botão na página do Sam)
- Na página `/sam`, cartão **Envio automático em um clique** logo abaixo da Fortaleza: botão **▶ Enviar
  automaticamente** e **Ensaio (não grava)**. Os dois abrem a pergunta **"Você tem certeza?"** (com o que
  vai acontecer); só o "Sim" dispara. O servidor também exige a confirmação (`POST /automatico/rodar` com
  `{"modo": "gravar", "confirmado": true}`; `{"modo": "teste"}` é o ensaio) e recusa pedido de outro site.
- O que o Sam faz sozinho (`bot/envio_auto.py`, numa thread da página, com a mesma trava de um envio por vez):
  1. **Captura** as intimações de ontem sem tarefa (na segunda, sexta a domingo): é a mesma captura do
     `main.py` (`capturar()`), com o navegador fechado no fim;
  2. **Analisa com a IA** (`analisar_arquivo`, a mesma da `./rodar_analise.sh`; usa a chave de API do `.env`
     e gasta créditos; leva o tempo do lote);
  3. **Lança** CI por CI com `lancar()`: as mesmas travas do envio de .txt (falta de informação, já tem
     tarefa no VIOS, conferência humana, data que já passou, duplicada) e a Conferência do VIOS depois de
     gravar. Quem não passa nas travas fica de fora e aparece como "barrada".
  No ensaio faz tudo igual, mas para no quadro de tarefas do VIOS (não grava).
- **Animação:** o andamento vira eventos da vila (bot `ultron`; ver `doc/vila/contrato-eventos.md`) e a
  Fortaleza do Dragão anima: o Sam acorda, o Mensageiro traz as intimações capturadas, a IA analisa, a Arqueira
  dá as contagens, o dragão desperta na criação das tarefas e a vida da Torre VIOS cai a cada tarefa criada.
  No cartão, quatro passos acendem (Capturar, Analisar, Criar tarefas, Conferir) com barra de progresso e os
  números ao vivo; ao terminar a página se atualiza.
- Andamento em `saida/automatico_execucao.json` (também em `GET /automatico/andamento`); o resultado de cada CI
  continua em `saida/lancamentos.json` e `saida/automatico_resultados.json`, então o relatório `/automatico`
  mostra tudo como antes. Sem intimação nova, termina sem gastar IA.
- Só funciona se o Sam estiver rodando (`./rodar_envio.sh`) com o `.env` completo (login do VIOS e chave da IA).
  Reiniciar a página depois de atualizar.
- Ainda não agenda horário: o clique é manual.

### Passo 41 — Skill de 13/11/2026 (responsáveis, feriado, marco pela publicação)
- A Controladoria mandou a skill revisada (`doc/skill-original/8_2026-11-13_responsaveis-feriado/`), que passou a ser a
  skill do projeto. Resumo das regras novas na seção 8 de `doc/skill-original/LEIAME.md`.
- O que já vale sem mexer no código: a skill entra no prompt da análise pela API (`bot/skill.py`) e na skill única do chat.
- **O que o código faz (13/11/2026):**

| Regra nova da skill | No código |
| --- | --- |
| `RESPONSÁVEIS` nunca `automático` (vai para a Amanda) | `bot/envio_txt.py` e `bot/lancamento.py` (`responsavel_proibido()`) barram a CI com responsável em branco, `automático` ou AMANDA LEITE MENDES |
| Nome completo do auxiliar / advogado responsável na análise pela API | `bot/responsaveis.py`: a sigla do auxiliar (SUH, TAMI, JOHN...) vira o nome completo pela lista do VIOS (`saida/responsaveis.json`; sigla ambígua como CARL não é adivinhada); sem auxiliar, o advogado responsável do processo. Carlos (CARL) só no Trabalhista vai para o Johnys |
| Sem auxiliar e com RONIELLE FEITOSA (no VIOS: RONEELY FEITOSA) como responsável: não lançar | Análise: bloqueio com a mensagem da skill. Página de envio: barra o `.txt` que traz só ele como responsável |
| Perícia médica judicial previdenciária: responsável da filial (Camocim, Tianguá, Jijoca, Sobral) | Análise: a cidade vem do teor (senão da comarca/cidade do processo); nenhuma ou mais de uma filial = bloqueio `NÃO LANÇAR — CONFIRMAR FILIAL...`. Página de envio: só aceita o responsável da filial. **Segunda checagem no lançamento** (`lancamento.conferir_pericia()`): antes de lançar a CI com essa tarefa, o robô abre a tela Lançar Intimação, segue o martelo ("Visualizar processo") e lê o campo **Escritório atual** da ficha (ex.: `Roneely Feitosa - Sobral`); o responsável passa a ser o da filial desse escritório (vale mais que o palpite do teor, que caía em Sobral por padrão). Escritório sem filial conhecida ou campo não lido: a CI não é lançada |
| `DATA` antecipada quando cair em feriado | `prazos.antecipar()`: feriado **nacional** recua a `DATA` para o dia de trabalho anterior; feriado estadual/municipal só dos locais de `ESCRITORIO_LOCAIS` (`.env`). Só a `DATA`: D-2 e vencimentos da descrição ficam. Ato com hora fixa (audiência, perícia, sustentação) e data informada não recuam. Nunca volta antes de hoje (avisa a urgência). Vale na análise e depois do corte das 12h no lançamento |
| Marco pela publicação, inclusive Fazenda Pública | O código já conta da publicação do DJEN/CSV; os dias (embargos 10, recurso 30 na Fazenda) a IA lê pela skill (prompt) |

- `ESCRITORIO_LOCAIS` (`.env`): onde fica o escritório que executa as tarefas, `CIDADE/UF` separados por `;` (ou só `UF`).
  **Vazio = só feriados nacionais recuam a `DATA`.** Preencher para valer também o feriado do estado/município do escritório.
- Os feriados nacionais são os do código (fixos e Sexta-feira Santa) e da tabela `doc/feriados-brasil-*.md`; ponto facultativo
  (Carnaval, Corpus Christi...) não é feriado e não recua.
- Testes: `.venv/bin/python -m unittest tests.test_responsaveis`.

### Passo 43 — Skill de 18/11/2026 (pacote atualizado da Controladoria)
- A skill do projeto (`doc/analise-intimacoes-controladoria/`) foi trocada pelo pacote `analise-intimacoes-controladoria-atualizada-2026-11-18.zip`.
  Cópia em `doc/skill-original/9_2026-11-18_atualizada/`; resumo na seção 9 de `doc/skill-original/LEIAME.md`. `doc/skill-unica/` regenerado.
- Mudanças que a skill traz: sem antecipação da `DATA` por feriado; perícia médica sem filial não bloqueia (texto `incluir responsável pela cidade identificada`);
  CARL → JOHN (exceto CALTECH); análise/ciência após 12h vai para o próximo dia de expediente do escritório.
- **Código alinhado (18/11/2026):** a `DATA` não recua mais por feriado (saíram `prazos.antecipar()` e o `ESCRITORIO_LOCAIS` do `.env`).
  Perícia médica sem filial mapeada vai com o texto `incluir responsável pela cidade identificada` e não bloqueia na análise nem no TXT;
  no lançamento, o "Escritório atual" do VIOS define a filial e, sem ela, a tarefa não é lançada. CARL → JOHN, exceto CALTECH.

### Passo 42 — Vila 06: a muralha do bot do Previdenciário
- A Vila 06 é a casa do bot de WhatsApp do setor previdenciário (repositório próprio, `bot-previdenciario`, RN28). A cena
  é **vídeo** pré-renderizado (Blender): plantão de dia, fora do expediente à noite e, a cada evento do bot, um clipe curto
  (mensagem chegando → respondida pelo bot, ou → passada para a equipe). A cena **só assiste**.
- Página: **`bot/vila/muralha.html`**, servida em **`/vila/previdenciario`**; aparece por cima do palco quando a aba
  **06 · Mikasa** é escolhida (patch `doc/vila/ligar_vila06_muralha.py`, rodar depois do da Fortaleza). O mapa
  continua com 5 lotes: a aba 06 é só a camada.
- Estado: a página consulta **`/vila/previdenciario/estado`** a cada 3 s. Este servidor pergunta ao bot
  (`GET <VILA06_URL>/vila/estado`, com `Authorization: Bearer <VILA06_TOKEN>`) e repassa **só** horário, conexão,
  contagens do dia, conversas com a equipe e eventos novos (`n`, tipo, horário) — nada de número, nome ou texto de cliente
  (`bot/vila06.py`, `limpar`). O token nunca vai ao navegador. Sem `VILA06_URL`/`VILA06_TOKEN` a cena roda em **simulação**.
- Vídeos: **fora do git**. Ficam em `VILA06_CLIPES` (padrão `<SAIDA_PASTA>/vila06_clipes`, já ignorada) com os nomes
  `plantao.mp4`, `fora.mp4`, `chegou.mp4`, `respondendo.mp4` e `equipe.mp4`; só esses nomes são servidos
  (`/vila/previdenciario/clipes/<nome>.mp4`). Sem os vídeos a página mostra a muralha vazia com o aviso.
- Caixa de diálogo (estilo RPG): nome, retrato e texto letra por letra, com uma fala por evento (chegou, respondida, passada
  à equipe, não entendida, conexão caída ou de volta, horário, a cada 10 respondidas e de espera). Os retratos ficam na mesma
  pasta dos vídeos, fora do git: `retrato-neutro.png`, `retrato-alerta.png`, `retrato-firme.png`, `retrato-sereno.png`
  (`/vila/previdenciario/retratos/<nome>.png`); sem eles, a caixa usa um rosto em pixel art de reserva.
- Som: botão **Som** na placa (o navegador exige um clique antes de tocar; a escolha fica salva). Arquivos em
  `<VILA06_CLIPES>/sons/`, fora do git: `musica.mp3` (laço com fusão de 3 s), `ambiente.mp3` (vento, em laço), efeitos
  `sfx-<nome>.mp3` (gancho, gas, corte, esquiva, pouso, vapor, passo, canhao, sino; os tempos de cada vídeo ficam em
  `EFEITOS_CLIPE` na página) e a voz de cada fala, `fala-<hash>.mp3` (FNV-1a de 32 bits do texto). Mudou o texto de uma fala
  = ela fica sem voz até gerar de novo (nunca toca a versão velha). Para gerar ou atualizar:
  `ELEVENLABS_API_KEY=... .venv/bin/python doc/vila/gerar_sons_vila06.py <VILA06_CLIPES> --aplicar` (só o que falta;
  `--so falas|efeitos|musica`, `--refazer`). Sem `--aplicar` mostra o que seria gerado e o custo. Sem os arquivos, a cena
  segue muda.
- No bot: `VILA_TOKEN` no `.env` dele (24+ caracteres, `openssl rand -hex 24`); o mesmo valor vai em `VILA06_TOKEN` aqui.
  Bot com HTTPS de certificado próprio (RN22.4): copiar o certificado para cá e apontar `VILA06_CERTIFICADO`.
- Testes: `.venv/bin/python -m unittest tests.test_vila06`.

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
- `instalar` também serve para reiniciar. Se a porta 5001 estiver ocupada (um
  `./rodar_envio.sh` aberto), ele avisa e para.
- **Bot de WhatsApp e coletor no mesmo script (18/11/2026).** O bot do Previdenciário continua no repositório
  privado `bot-previdenciario` (clonado à parte no Mac; nunca copiar o código, a mídia da Vila 06 ou o histórico
  dele para cá). Com `BOT_WHATSAPP_PASTA=<pasta do clone>` no `.env`, o `servidor_mac.sh` também cuida dele:
  - `./servidor_mac.sh whatsapp instalar | status | atualizar | log | desinstalar` chama os scripts do próprio bot
    (`scripts/mac/`; `instalar` e `atualizar` pedem a senha de administrador do Mac);
  - `./servidor_mac.sh coletor instalar | parar | status | log` é o mesmo que `consulta/servico_mac.sh`;
  - `./servidor_mac.sh tudo` mostra os três serviços (página dos bots, coletor, bot de WhatsApp);
  - `./servidor_mac.sh atualizar-tudo` atualiza **o bot primeiro** e só depois faz o `git pull` daqui e reinicia a
    página e o coletor (o bot antigo recusa campo novo do coletor). Se o pull trouxe dependência nova, rodar
    `./instalar.sh` e `./servidor_mac.sh coletor instalar`.
  - A Vila 06 não muda: continua lendo os vídeos de `VILA06_CLIPES` e o estado de `VILA06_URL`/`VILA06_TOKEN`.
- Login do VIOS (`SISTEMA_USUARIO`, `SISTEMA_SENHA`, seletores, `HEADLESS`, `TIMEOUT`): o Sam relê o `.env`
  a cada envio (manual e automático), então trocar a senha no `.env` vale já no próximo envio, **sem
  reiniciar**. Outras variáveis (`ENVIO_SENHA`, `ENVIO_REDE`, `SISTEMA_URL`, `SAIDA_PASTA`, pastas dos
  outros bots) só valem depois de reiniciar com `./servidor_mac.sh instalar`.
- A `saida/` **não vai para o GitHub** (o repositório é **público** e ela tem dados
  de clientes): copiar com `rsync` ou pendrive (Passo 21). Nada com dado de cliente, senha,
  token ou mídia de terceiros entra neste repositório.
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

### Passo 37 — Consulta de processo pelo WhatsApp: o coletor (pasta `consulta/`)
- Quinto robô, ao lado da Orelha (usa o `.venv` e o núcleo dela, sem alterá-la). Roda no Mac, só com saída
  HTTPS para o bot: a cada `CONSULTA_INTERVALO` s busca pedidos, lê o VIOS só por leitura e devolve a ficha
  mínima (fase, área, datas, telefones em HMAC). Nunca sai do Mac: CPF, nome, CNJ, CI, comentários, valores.
- Especificação: `consulta/CONTRATO.md`. Instalar e rodar: `consulta/README.md`
  (`orelha/.venv/bin/pip install -r consulta/requirements.txt`; `cp consulta/.env.example consulta/.env`;
  `consulta/rodar.sh --simulado --uma-vez` para ver sem VIOS).
- Configuração: variáveis `CONSULTA_*` em `consulta/.env.example`. `ORELHA_PARADOS_LIBERAR_XHR=auto` é
  necessário: a tabela de tarefas da ficha carrega por XHR POST e o bloqueio de envios a deixaria vazia.
- Mapa tipo de tarefa -> fase: `consulta/fases_vios.yaml` (todas as áreas, revisão do setor).

### Passo 33 — Orelha, o relatório do dia que só lê o VIOS (pasta `orelha/`) e a Vila 05
- Quarto bot, separado como o Albi: fica em `orelha/`, com `.venv`, `.env`, `logs/` e `saida/`
  próprios, e não importa nada de `bot/` nem de `albi/`. **Detalhes em `orelha/README.md`**:
  instalar, configurar, rodar, `--simulado`, agendar (cron/launchd) e o que falta conferir na tela.
- Entra no VIOS e **só lê**. O bloqueio de envios (ideia do Zangão) é ligado antes do login, e o
  Orelha para se ele não estiver ativo. O relatório do dia (`orelha/saida/<data>/relatorio.html`, PDF e
  `resumo.json`) tem agenda de hoje e amanhã, prazos atrasados da equipe, intimações esquecidas (sem
  tarefa, fora ontem e hoje), processos parados (lenta: `--funcoes parados`, semanal) e a conferência
  das planilhas do Albi no VIOS.
- Instalar: `cd orelha && ./instalar.sh`. Preencher o `orelha/.env` (modelo em `orelha/.env.example`).
  Ver sem senha: `./rodar.sh --simulado`. Rodar: `./rodar.sh`.
- **Vila 05**: com `VILA_URL` e `VILA_SENHA` no `orelha/.env`, o Orelha manda os eventos por
  `POST /eventos` ao Ultron. O Ultron aceita porque `"orelha"` está em `BOTS_EXTERNOS`
  (`bot/eventos.py`), e os eventos levam só fases e contagens (contrato em
  `doc/vila/contrato-eventos.md`). A vila agora tem 5 vilas, e a Vila 04 está vaga. Abrir direto:
  `/vila?vila=5`. Se a vila for baixada de novo do site: `ligar_zangao.py`, `ligar_albi.py`, depois
  `python3 doc/vila/ligar_orelha.py bot/vila/vila.html`, `ligar_jarvis.py`, `ligar_vila05_parque.py`
  (o parque, ver Passo 32), `ligar_orelha_agenda.py` (horário e Arquivo, ver Passo 35) e, depois de
  todos, `ligar_vila05_vida.py` e as camadas do parque vivo (ver Passo 36).

### Painel semanal do Orelha (PDF no papel timbrado)
- Botão **Gerar painel semanal** na página `/orelha` do Sam (ou `./rodar.sh --funcoes painel` dentro de
  `orelha/`), sem agendamento, gera `saida/<data>/painel-semanal.pdf`:
  resumo executivo, taxa de resolução, carga por advogado, agenda de audiências e tarefas não feitas,
  no papel timbrado do escritório. O período é escolhido nos campos **De** e **Até** da página (vêm de
  hoje a 7 dias depois; até 120 dias); pela linha de comando, `--painel-de`/`--painel-ate`. Sem escolha,
  vai do dia do pedido até `ORELHA_PAINEL_DIAS_FILA` dias depois (padrão 7). Não entra no relatório do dia. A 1ª edição não tem semana anterior; a
  comparação começa na 2ª. Detalhes e variáveis `ORELHA_PAINEL_*`: `orelha/README.md` e
  `orelha/.env.example`.

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
- **Mensagens da CAC** (na mesma tela do "Capturar resumo"): uma mensagem por pessoa pesquisada, no
  padrão da Central de Atendimento ao Cliente. Escolha a atendente (Beatriz Vasconcelos ou Renara
  Kathleem), revise e clique em "Copiar mensagem". Arquivos: `mensagens_cac.txt` e `.json`
  (`albi/mensagem_cac.py`). **Sem IA e sem entrar em tribunal nenhum**: o texto sai de regras fixas e
  só usa os registros da planilha do Sonar.
  - **Com processos**: abertura ("após consulta aos registros processuais disponibilizados, foram
    localizados *N processos judiciais* relacionados a *NOME*, CPF nº …, todos vinculados ao *TJ…*"),
    o período e a área dos processos, quantos estão arquivados/em tramitação e, por processo:
    "*1️⃣ Autor x Réu*", "*Processo nº … — TJ…*", o que é a ação, a posição da pessoa (requerente,
    exequente, parte ré…), o que a pesquisa não traz (petição, valores, provas, decisões), o andamento
    e a "*Conclusão:*". O formato é fixo (sem parágrafos opcionais e sem ressalva final): só mudam os campos.
  - **Sem processos** ("não consta" no Sonar): "Informamos que após consulta ao sistema do Poder
    Judiciário, não localizamos *nenhum processo* em nome de *NOME*." Pessoa com falha ao ler a
    planilha não ganha mensagem.
  - **Parágrafo explicativo por processo (Gemini)**: com `GEMINI_API_KEY`, cada processo ganha um
    parágrafo que explica o tipo de ação, a posição da pessoa e a situação, gerado só a partir desses
    três dados e guardado em `albi/explicacoes_classe.json` (editável). Sem chave, vale a explicação fixa.
  - **Tipos de ação fora do dicionário**: com `GEMINI_API_KEY` no `albi/.env` (chave gratuita), o
    `albi/explicacao_ia.py` pede ao Gemini uma frase para "Esse tipo de processo é…". Só o nome da
    classe é enviado; a resposta fica em `albi/explicacoes_classe.json` (uma vez por classe) e pode ser
    editada. Modelo: `gemini-flash-latest` (com dois reservas); `GEMINI_MODEL` fixa um. Sem chave ou com
    erro, o parágrafo é omitido.
  - O que **não** aparece: os fatos das petições, as sentenças e os pagamentos. O DataJud
    (`albi/datajud.py`) deixou de ser usado na mensagem; o arquivo continua para consulta manual
    (`.venv/bin/python datajud.py <número>`).
- **Baixar de novo** (não compra): na execução já confirmada, o botão "Baixar de novo
  os resultados de cada um" (ou `./rodar.sh --arquivo X --baixar`) pega o número de
  cada pedido no registro e baixa de novo o PDF e a planilha, sem abrir a Nova
  Pesquisa. Quem não tem pedido no registro fica como "Sem pedido no registro".
- Não compra duas vezes: CPF já pesquisado para a mesma empresa no último dia
  (24 h) usa o pedido anterior (registro `albi/saida/pedidos_confirmados.json`).
- Pela página: `http://<IP do Mac>:5001/albi` (link "Albi" no topo do Ultron).
  A página usa o tema da Arena do Albi (Dragon Ball Z): céu, nuvens, lago, cabeçalho bege com telhado laranja
  e cartões com moldura de madeira (`<body class="tema-arena">` em `bot/templates/albi.html`).
- **Pesquisa digitada** (abaixo da caixa "Solte o .txt"): para uma pesquisa única ou poucas, sem arquivo. Digite a
  empresa (cliente), o CPF/CNPJ e o nome; "+ Adicionar outra pessoa" cria mais linhas. A página monta o mesmo
  texto do .txt (`EMPRESA: X` e `CPF ; nome`), guarda como `digitado-AAAA-MM-DD_HHMM.txt` e abre a **conferência**,
  como no arquivo: nada é comprado antes de você confirmar. Todos os campos são obrigatórios.
- **Clientes** (abaixo da caixa "Solte o .txt"): um bloco por empresa que pediu pesquisa. Clicar abre a tela do
  cliente (`/albi/cliente?empresa=NOME`) com **cada pedido** dele (um arquivo enviado) por data, o resultado de
  cada pessoa e as mensagens da CAC (com o parágrafo do Gemini) para copiar. Um cliente que pediu 25 CPFs hoje e
  mais 25 na semana seguinte tem dois pedidos, cada um com sua data.
- **Tela "Mensagens"** (botão no topo da página do Albi, `/albi/mensagens?dia=AAAA-MM-DD`): o produto final do
  Albi. Junta as mensagens da CAC (`mensagens_cac.json` de cada execução) **por dia da execução**: escolha o dia
  no calendário ou nos botões de dias com mensagens, filtre por "com processos / sem processos", busque por nome
  ou empresa, troque a atendente e use "Copiar mensagem" (ou "Copiar todas as que estão na tela"). As mensagens
  já existem no fim de cada execução (o Albi gera o relatório sozinho); "Capturar resumo" só serve para
  execuções antigas sem elas. Quem foi pesquisado de novo no mesmo dia fica com a mensagem mais recente.
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
  bot/vila/vila.html`, depois `python3 doc/vila/ligar_albi.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_bumblebee.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila01_campo.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila03_arena.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_orelha.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_jarvis.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila05_parque.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_orelha_agenda.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila04_garagem.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila02_ponte.py bot/vila/vila.html`,
  `python3 doc/vila/ligar_vila03_arena_att.py bot/vila/vila.html` e, por último, o parque vivo da
  Vila 05 (Passo 36): `ligar_vila05_vida.py` e depois as camadas `ligar_vila05_casinhas.py`,
  `ligar_vila05_ossos.py`, `ligar_vila05_clima.py`, `ligar_vila05_dia.py`, `ligar_vila05_humor.py` e
  `ligar_vila05_passeio.py`.

### Passo 32 — Vila 05: o parque do Orelha
- A Vila 05 virou um parque dos cães cheio de brinquedos: cerca branca de madeira, grama com flores
  e caminhos de areia com marcas de pata. Os postos ficaram nos mesmos lugares:
  - **Casinha do Orelha** (a doca dele): casinha azul de telhado vermelho, com a plaquinha
    "ORELHA", lanterna, pote de ração e pote de água;
  - **Calendário:** mural de madeira com o calendário (um dia acende por vez enquanto ele lê);
  - **Intimações:** caixa de correio (as cartas voam enquanto ele lê; no fim, a bandeirinha sobe
    vermelha se tiver achado grave e verde se não tiver);
  - **Relatório:** toalha de piquenique, onde a folha do relatório aparece;
  - **Planilhas:** baú de brinquedos com a pilha do Albi e os baldes verde, âmbar e cinza;
  - **Torre VIOS:** torre de parquinho com escorregador e a luz na antena.
- Também tem piscina de bolinhas, caixa de areia, barreira de agility, prateleira de brinquedos,
  hidrante e brinquedos pela grama. A bolinha quica, as bolinhas pulam na piscina e há borboletas.
- Patch: `doc/vila/ligar_vila05_parque.py`, que roda depois do `ligar_orelha.py` e do
  `ligar_jarvis.py` (e antes do `ligar_orelha_agenda.py`, o último). Os eventos, as
  falas e o painel do Orelha não mudaram.

### Passo 31 — Vila 03: a arena do Albi
- A Vila 03 é a arena de `albi/mascote/fundo-arena-albi.html` (a versão nova, com a luta), adaptada à
  vila: céu com sol e nuvens, montanhas, mata, campo, a casa em domo (com anexo e torre de
  observação), a árvore grande, o lago com reflexos e um mastro com antena à direita. No céu, o
  dragão serpenteando e dois lutadores: chegam voando com aura, trocam socos e chutes, disparam
  raios que se chocam e explodem; a casa e a árvore ficam em ruínas pegando fogo, eles descem,
  reconstroem a casa, a muda cresce e tudo recomeça (ciclo de uns 8 segundos).
- O Albi anda só no campo, entre a casa e o lago, e passeia por ele quando está parado. Os postos:
  - **Doca 01 · Albi:** porta da casa em domo;
  - **Receptor TXT:** porta do anexo (as faíscas da leitura saem do telhado dele);
  - **Conferência:** janela da torre de observação, onde rolam as linhas que ele confere (com a
    casa em ruínas, não aparecem);
  - **Torre Sonar:** o mastro com antena, cuja ponta pisca quando ele entra no Sonar ou pesquisa.
- A parte animada só é desenhada com a Vila 02, 03 ou 04 na tela.
- Patches: `doc/vila/ligar_vila03_arena.py` (a primeira arena) e, por cima, `doc/vila/ligar_vila03_arena_att.py`
  (a arena nova; o último da lista). Os eventos e o painel do Albi não mudaram.

### Passo 30 — Mascote novo do Ultron (agora Sam) e Vila 01 no campo
- **Nome:** na tela ele se chama **Sam**: página, links, cena e Vila 01. A marca "SAM" fica nas
  cores do boneco (S dourado, AM verde). Por dentro continua `ultron` (rotas, arquivos, eventos).
- O Ultron ganhou o mascote novo (imagem `doc/mascote/WhatsApp Image 2026-11-04 at
  11.19.56.jpeg`): cabelo dourado, olhos vermelhos fechados sorrindo, capa verde, colete e pés
  descalços. É uma grade de 28×35 em `bot/templates/_ultron.html`, a mesma da vila; a amostra
  está em `doc/mascote/ultron-campo.html`. Aparece no topo da página, na caixa de soltar o .txt,
  no ícone da aba e na Vila 01. O nome continua **Ultron**.
- A **Vila 01** foi pintada no estilo do cenário (`doc/mascote/1e86eacd-….jpeg`):
  - céu com nuvens e colinas, grama com flores, caminhos de terra e sebe nas bordas;
  - **Doca 01 · Ultron** = casa na colina com porta redonda verde e chaminé soltando fumaça;
  - **Receptor TXT** = moinho com as pás girando, onde o .txt cai;
  - **Conferência** = casa de porta amarela com o quadro onde ele organiza as CIs;
  - **docas livres** = hortas cercadas;
  - lago com ponte de pedra;
  - **Torre VIOS** = torre de pedra com lanterna.
- A geometria é a mesma (blocos, portas e postos), então os caminhos e as etapas não mudaram.
  Patch: `doc/vila/ligar_vila01_campo.py`. As Vilas 02 e 03 ficam como estavam.

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
- **Vila 02 vira a batalha na ponte, vista de cima** (desenho em `doc/vila/zangao-transforma_att.html`):
  ponte sobre a água (ondas e o reflexo do fogo), pista com faixas, guard-rail e quatro pilares com
  luz vermelha. Os postos ficam nos mesmos lugares, como coisas da ponte: **Doca 01** = garagem
  listrada com a vaga marcada; **Filtro previdenciário** = cabine de pedágio com cancela (sobe quando
  ele filtra ou passa); **Captura de dados** = pórtico com o painel de mensagens (a tela da captura);
  **Torre VIOS** = antena no pilar da direita. O Bumblebee parado é o robô de frente; para andar,
  vira o **carro visto de cima**, que gira para o lado em que vai (com faróis, rastro e uma onda de
  choque ao virar). Em volta: dois duelos de robôs (chegam como carros, brigam, explodem e vão
  embora), trânsito, carcaças pegando fogo, explosões longe dele, fumaça e brasas. Ele anda só na
  pista. A parte animada só é desenhada com a Vila 01, 02 ou 03 na tela. Os eventos, as falas e o
  painel não mudam. Patch: `doc/vila/ligar_vila02_ponte.py` (depois do `ligar_vila04_garagem.py` e
  antes do `ligar_vila03_arena_att.py`).

### Passo 36 — Vila 05: o parque vivo (a cena do relatório, o dia e o humor do Orelha)
- **Campo `cena` no `GET /orelha/status`** (`bot/orelha.py`, função `cena()`): `null` sem relatório
  real (ou com o Orelha não configurado); senão só a data e CONTAGENS do relatório real mais recente,
  lidas do `resumo.json`: `data`, `gerado_em`, `atrasadas`, `graves` (atrasadas há mais de 7 dias),
  `vencem_hoje`, `intimacoes`, `intimacoes_graves`, `parados`, `parados_graves`, `audiencias_hoje`,
  `pericias_hoje`, `erros` e `funcoes` (as seções que rodaram). Campo ausente = 0. Nunca leva nomes,
  `por_responsavel` nem `por_area`. Os simulados são ignorados. Testes: `tests/test_orelha_cena.py`
  (rodar com `.venv/bin/python -m unittest discover -s tests`, na raiz do repo).
- A Vila 05 lê esse campo a cada 30 s (sem servidor, no site publicado, usa uma cena de exemplo):
  - **Casinhas**: duas casinhas novas ao lado da do Orelha; de tempos em tempos a Pretinha ou o
    Caramelo saem para uma voltinha e voltam.
  - **Ossos**: cada tarefa atrasada é um osso meio enterrado na caixa de areia (acima de 12, cada osso
    vale mais de uma); as graves são ossos escuros. Quando a contagem cai, um osso sai voando; quando
    sobe, cresce um montinho e aparece outro.
  - **Clima**: sem atrasadas faz sol; com poucas passam sombras de nuvem; com muitas ou com graves o
    céu fecha; com 5 graves ou mais chove de leve, com poças.
  - **Dia**: a luz muda com a hora do navegador (madrugada, nascer, dia, pôr do sol, noite); à noite
    acendem a lanterna da casinha, a antena da torre e vagalumes. Fora do expediente (antes das 8h,
    depois das 18h e no fim de semana) o Orelha dorme na porta da casinha; das 12h às 13h almoça no
    pote de ração; no fim de semana troca o fedora por um chapéu de palha.
  - **Humor**: no fim de cada execução, zoomies em volta da piscina (ok), emburrado de costas com uma
    nuvenzinha e o balão "HMPF... DEU ERRO, OLHA O LOG." (erro) ou um suspiro (parou).
  - **Passeio**: de vez em quando (cerca de 1 minuto, das 7h às 19h, mais no fim de semana) uma pessoa
    genérica dá uma volta pelos caminhos: corredor, moça com bolsa, criança com balão ou senhor de
    bengala. Com o Orelha livre e no expediente (8h–18h; no fim de semana a visita o acorda), ele vai
    até ela e eles brincam: cheira, pula em cima, late, roda, ganha carinho ou um petisco; depois ela
    acena e segue. Uma execução sempre passa na frente.
  - **Salto**: quando atravessa a barreira de agility ele salta (a sombra fica no chão) e levanta
    poeira ao pousar; indo de lado, pula cada poste. De vez em quando faz um treino na barreira.
- Testar pela URL (valem também sem servidor): `?vila=5&v5hora=21` (hora; aceita `HH:MM`),
  `&v5dia=6` (0 = domingo … 6 = sábado), `&v5atrasadas=40&v5graves=8` (a cena) e
  `&v5humor=ok|erro|parou` (força o humor) e `&v5visita=1|pretinha|caramelo` (uma visita a cada 15 s),
  `&v5pessoa=1|corredor|moca|crianca|senhor` (uma pessoa a cada 15 s, a qualquer hora) e `&v5agility=1`
  (treino na barreira a cada 20 s).
  Ver em casa: `cd bot/vila && python3 -m http.server 5077
  --bind 127.0.0.1` e abrir `http://127.0.0.1:5077/vila.html?vila=5&v5hora=21`.
- Patches: `doc/vila/ligar_vila05_vida.py` (o esqueleto: `this.v5` e os ganchos, sem desenhar nada),
  depois de todos os outros `ligar_*`; em seguida as camadas, em qualquer ordem:
  `ligar_vila05_casinhas.py`, `ligar_vila05_ossos.py`, `ligar_vila05_clima.py`, `ligar_vila05_dia.py`,
  `ligar_vila05_humor.py` e `ligar_vila05_passeio.py`. Rodar de novo não repete nada.
- Para quem for mexer numa camada: o guia dos ganchos (trechos exatos, coordenadas, como mover o
  Orelha) é `doc/vila/ganchos-vila05.md`, e as ferramentas de teste ficam em `doc/vila/teste-vila05/`
  (`checar.py` roda `node --check` no JS da vila; `rodar.js` roda a vila em node com canvas falso).

### Passo 35 — Orelha avisa quando o relatório roda e guarda os relatórios no Arquivo
- **Horário**: `ORELHA_HORARIO` (padrão `seg-sex 07:30`) e `ORELHA_HORARIO_PARADOS` (padrão
  `sab 08:00`) no `orelha/.env`. Formato `<dias> <HH:MM>`, com faixa (`seg-sex`) ou lista
  (`seg,qua,sex`), e mais de um separado por `;`. Tem que ser **o mesmo do agendamento** (cron ou
  launchd, `orelha/README.md`): quem roda o Orelha é o agendamento; o horário serve para avisar.
- **Agendar no Mac** (sem isso o relatório nunca sai sozinho e a página avisa "ainda não saiu"):
  `cd orelha && ./agendar_mac.sh instalar`. Ele cria o agendamento do launchd com o horário do próprio
  `orelha/.env` (relatório do dia e processos parados); `./agendar_mac.sh agora` roda na hora para
  testar, `status`, `log` e `parar`. O Mac fica com o usuário logado, como no servidor.
- O Sam lê esse horário e os relatórios da pasta do Orelha (`bot/orelha.py`; `ORELHA_PASTA` só se ele
  estiver noutra pasta). Não roda o Orelha nem importa nada de `orelha/`.
- **Na Vila 05**, parado, o Orelha diz quando roda, quando sai o próximo relatório ("amanhã (sexta) às
  7h30") e quantos estão guardados. Se o de hoje não saiu até 45 minutos depois da hora marcada, ele
  avisa para conferirem o computador dele, e o topo mostra "Atrasado". No fim de cada
  execução, leva a folha até o **Arquivo** (armário do parque), guarda na gaveta e diz quando sai o
  próximo. A placa mostra quantos estão guardados ("Arquivo · 12").
- **Página `/orelha`** (botão "Relatórios guardados" na Vila 05 e no cartão da Vila dos Bots): o
  horário, o próximo relatório, o aviso de atraso e a lista de todos os relatórios já feitos, do mais
  novo para o mais antigo, com graves e pontos de atenção e os botões **Abrir**, **PDF** e
  **Planilhas (.csv)**. Os simulados ficam à parte. Os arquivos continuam em `orelha/saida/<data>/`.
- **Relatório mais compacto e a semana** (06/11/2026): as atrasadas vêm agrupadas por **dia do
  vencimento** (ontem, anteontem… depois por faixa de 7 dias, por mês e por ano), cada grupo fechado
  com o total; clica no grupo e abrem as tarefas. O quadro "Atrasadas por responsável" fecha a seção.
  Junto sai `semana.html`, **Atrasadas da semana**: de segunda até hoje, um grupo por dia com as
  tarefas que venciam nele e continuam abertas (na segunda-feira, a semana passada). Na página
  `/orelha`, o último relatório aparece **dentro da página**, com as abas "Relatório do dia" e
  "Atrasadas da semana"; na lista dos guardados, o botão "Semana".
- `GET /orelha/status` (para a vila) leva só datas e contagens (inclusive o campo `cena`, ver Passo 36). O texto dos relatórios só aparece na
  página e nos arquivos, atrás da senha das páginas (`ENVIO_SENHA`), como as do Albi.
- Patch da vila: `doc/vila/ligar_orelha_agenda.py`, o último da lista. O `ligar_vila05_parque.py`
  ganhou o armário do Arquivo (a barreira de agility desceu para a grama de baixo).

### Passo 34 — Entrada: a Vila dos Bots
- `http://<IP do Mac>:5001/` abre a **Vila dos Bots**: a vila e um cartão por bot (Sam, Bumblebee,
  Albi, Jarvis, Orelha) com o botão para a página de cada um. Nenhum bot fica fixo no topo.
- A página de envio do Sam fica em `http://<IP do Mac>:5001/sam`. As páginas de bot têm o botão
  "Vila dos Bots" para voltar à entrada.

### Passo 33 — Albi: autos dos processos pelo Presto (em construção)
- Objetivo: o bot baixar os autos de cada processo do relatório do Leme, como a atendente fazia à
  mão, entrando no tribunal pela extensão do **Presto** (Oystr). O plano do escritório não tem a
  API de robôs da Oystr, então o bot usa a extensão num perfil do Chrome só dele.
- **Caminho atual (Mac): o Chrome que já está aberto.** No Chrome do bot, a conta Google do
  escritório pede confirmação de identidade; por isso o Albi controla o Chrome aberto pelo
  AppleScript (`albi/chrome_mac.py`). Uma vez: `cd albi && .venv/bin/python presto.py liberar-chrome`
  (pergunta antes, fecha o Chrome, marca "Permitir JavaScript de Apple Events" no arquivo
  `Preferences` de cada perfil, guardando uma cópia `Preferences.albi-bak`, e abre o Chrome de novo;
  é o mesmo que o menu Visualizar > Desenvolvedor do Chrome); no macOS, quando aparecer "Terminal quer controlar Google
  Chrome", Permitir (e "Gravação de Tela" para o Terminal, para os prints). Depois, com a janela do
  perfil do escritório na frente: `cd albi && .venv/bin/python presto.py aberto` (console do Presto e
  login do PJe do TRT7; ou passe as URLs). Ele abre abas novas, salva o que vê em
  `albi/logs/presto/<data_hora>/`, clica no botão de login via Presto e captura o resultado. As abas
  ficam abertas.
- **Entrar no tribunal pelo Presto:** no `albi/.env` do Mac, `PRESTO_PIN=` (a senha/PIN que o quadro do
  Presto pede depois de escolher a credencial) e, se houver mais de uma credencial,
  `PRESTO_CREDENCIAL=` (parte do nome). Depois `.venv/bin/python presto.py entrar tjce1` (ou tjce2,
  trt7, trt7-2, jfce, trf5, trf5-2, ou a URL de login). O bot abre o login no Chrome aberto, clica na
  credencial no quadro "Credenciais Disponíveis" que o Presto põe na página, preenche o PIN, confirma e
  diz se entrou. O PIN não aparece no Terminal nem nas capturas.
  Se o clique por JavaScript não abrir o campo do PIN (a extensão pode ignorar cliques que não são de
  verdade), o robô põe a aba na frente e clica com o mouse de verdade no número da credencial; se o PIN
  por JavaScript não entrar em 12 s, clica no campo e digita o PIN pelo teclado. Isso precisa, uma vez,
  do Terminal em Ajustes do Sistema > Privacidade e Segurança > **Acessibilidade**, e o Chrome fica na
  frente enquanto o robô faz o login. O quadro é procurado também dentro de "shadow roots" e frames.
- **Tribunal aberto pelo console do Presto:** o `entrar` e o `processos` abrem o tribunal como a
  atendente faz: console do Presto > **Sites** > procura o tribunal na lista > clica. Se o console
  pedir login, o robô usa `PRESTO_EMAIL` e `PRESTO_SENHA` do `albi/.env` (preencher no Mac; nunca vão
  para o git nem para a documentação). Antes de procurar o tribunal, o robô espera até 25 s o console
  mostrar o login ou a lista de sites (não pula mais o login quando o site demora); aceita o login em
  uma tela (e-mail e senha) ou em duas (no console real: e-mail, **Acessar**, senha, **Login**) e, se o preenchimento não pegar,
  clica nos campos e digita com o teclado de verdade (precisa da Acessibilidade). Se continuar no
  login, para e salva o print `0_console_login_depois`. No quadro "Credenciais Disponíveis" do Presto, o
  número da credencial só abre o campo do PIN com clique de mouse de verdade: o `entrar` avisa no começo
  se falta a permissão Acessibilidade (Terminal ou Visual Studio Code). Feche o DevTools antes de rodar. No TRT7, a tela
  `primeirograu/login.seam` tem o botão "Login via Presto": o robô clica nele e o quadro aparece no SSO. `--direto` pula o console e abre a URL de
  login como antes.
- **Procurar nos tribunais os processos do último relatório:** `cd albi && .venv/bin/python presto.py
  processos --conferir` mostra, sem abrir o Chrome, qual relatório ele pegou (o `processos.csv` mais novo
  que tem processos, em `albi/saida/` ou em `saida/albi/`, onde a página `/albi` guarda; `--listar` mostra todos) e em qual tribunal está cada
  processo, pelo número CNJ: TJCE (8.06), TRT7 (5.07), JFCE (4.05, origem 81xx) e TRF5 (4.05, o resto);
  2º grau pela instância do Sonar ou origem 0000. Os de outros tribunais aparecem como "fora". Para outro
  relatório, passe a pasta (ou só o nome dela, como sai no `--listar`): `presto.py processos <pasta> --conferir`. Depois, no Mac, com a janela do
  escritório na frente: `.venv/bin/python presto.py processos` (opções: `--tribunal tjce1` só um
  tribunal; `--max 3` só os 3 primeiros). Para cada tribunal ele abre uma aba, entra pelo Presto (se a
  aba já estiver logada, segue) e, na mesma aba, procura cada processo: no PJe, a tela "Consultar
  processos" (preenche o número e clica em Pesquisar); no TRT7, o detalhe do processo da consulta
  processual. Se cair no login no meio, entra de novo uma vez. Resultado de cada um: achou, não
  encontrado, captcha, sem formulário, não entrou ou fora. Salva tudo em
  `<pasta do relatório>/presto/<data_hora>/` (`resumo.txt`, `resumo.json` com os links do processo e
  as capturas de cada um, por tribunal). Ainda não baixa os autos.
- (Tentativa anterior, perfil separado) Copiar o perfil (uma vez, no computador onde o Albi roda): `cd albi && .venv/bin/python presto.py
  copiar`. Mostra os perfis do Chrome; escolha o que tem o Presto logado. Se o Chrome estiver
  aberto, ele pergunta se pode fechá-lo (responda Enter/"s"; as abas voltam ao abrir de novo); a cópia vai para `albi/perfil_presto/` (sem caches nem abas) e o Chrome pode ser
  aberto de novo. O bot não usa o perfil aberto direto porque o Chrome não deixa automação no perfil
  principal nem dois Chromes no mesmo perfil. Se o Presto sair da conta no bot, copiar de novo.
- Alternativa (perfil novo, instalando o Presto nele): `cd albi && .venv/bin/python presto.py
  preparar`. Abre o Chrome com o perfil `albi/perfil_presto/`: instalar a extensão do Presto,
  entrar na conta do Presto, conferir que abre o PJe logado e teclar Enter no Terminal (o script
  fecha o Chrome; no Mac, fechar a janela não encerra o Chrome, e Ctrl+C não é preciso).
- Explorar: `.venv/bin/python presto.py explorar <URL do tribunal>`. Salva em
  `albi/logs/presto/<data_hora>/` o print, o HTML, o texto e os botões/campos/links do pop-up da
  extensão e de cada site, mais o resumo da extensão (`presto_manifest.json`). Serve para montar o
  caminho do bot (entrar, buscar o processo, baixar os autos) sem inspecionar pelo DevTools.
- O perfil e as capturas ficam fora do git (sessão do Presto e possíveis nomes de clientes).

### Passo 32 — Jarvis na Vila 04 (relatório mensal de processos)
- A vila tem 5 vilas: 01 · Sam, 02 · Bumblebee, 03 · Albi, **04 · Jarvis** e 05 · Orelha. O Jarvis é o
  robô do relatório mensal de processos por Grupo Cliente (segundo usuário do VIOS, só leitura).
  **Pasta própria `jarvis/`** (como o Albi e o Orelha): `.venv`, `.env`, `logs/`, `saida/` e cópias
  próprias do login, da configuração e da IA em `jarvis/nucleo/`; não importa nada de `bot/`.
  Detalhes em `jarvis/README.md`.
- A Vila 04 é a **garagem do Homem de Ferro** (desenho do `fundo-oficina-jarvis.html`, do Kaio):
  parede de concreto, túnel com luzes, janelas noturnas, telas, carros, duas armaduras em
  exposição, braços robóticos soldando e uma máquina para cada estação (rack com antena,
  scanner de documentos e terminal com impressora). No centro, o projetor do holograma é o **posto do
  Jarvis**: quando ele está lá, o holograma acende em volta dele (o Jarvis é o núcleo). Placas:
  Conexão VIOS, Leitura dos processos e Planilhas. O Jarvis (núcleo de IA: esfera azul em
  espiral, com anéis e o centro pulsando) voa pela garagem em linha reta e se apresenta no diálogo.
  `/vila?vila=4` abre direto nela. A parte animada da garagem só é desenhada com a Vila 03, 04 ou 05
  na tela. Patch: `doc/vila/ligar_vila04_garagem.py` (antes do `ligar_vila02_ponte.py`).
- **Rodar pela vila**: com o Jarvis instalado (`cd jarvis && ./instalar.sh` e o `jarvis/.env`
  preenchido; `JARVIS_PASTA` só se ele estiver noutra pasta),
  a caixa de fala da Vila 04 ganha "Escolher grupos e gerar" e "Planilhas", que abrem a página
  `/jarvis`: lá a pessoa **marca os grupos** (do `PROCESSOS_GRUPOS` do Jarvis, que
  `cd jarvis && ./rodar.sh --grupos --salvar` completa com todos os grupos do filtro Grupo Cliente
  do VIOS; nunca todos sem escolher) e clica em "Gerar relatório do mês" (com confirmação: segundo clique em até 6 s) ou
  "Testar (2 processos por grupo)" (salva em `AAAA-MM/teste/`); embaixo, as planilhas para baixar. Rotas: `/jarvis`, `/jarvis/status`, `POST /jarvis/rodar`,
  `/jarvis/planilha/<mês>/<arquivo>` (só arquivos listados; nada fora da pasta).
- O Jarvis roda em segundo plano, com ambiente limpo (nenhuma variável do Ultron chega a ele),
  e manda o andamento por `POST /eventos` (bot `jarvis`, só contagens: grupo N de M, processo X
  de Y, gasto). A vila mostra na caixa de fala e o Jarvis vai a cada lugar com uma animação:
  - **Conexão VIOS** (entrando no VIOS): o Jarvis vai ao rack com antena, os LEDs piscam rápido,
    a antena emite sinal e ele manda sinais para ela;
  - **Leitura dos processos** (lendo cada processo): ele para no projetor, o holograma acende e
    gira mais rápido; ao lado, o scanner varre as páginas (feixe vermelho) e as folhas lidas vão
    do scanner para o núcleo; uma barra em cima mostra processo X de Y;
  - **Planilhas** (salvando cada grupo e no fim): ele vai ao terminal, que preenche a planilha
    célula por célula e imprime; no fim, a planilha fica cheia e a folha impressa. O Jarvis fica uns
    segundos lá (salvar é rápido demais para ver) e depois volta à ronda.
  Trabalhando, o núcleo gira 3 vezes mais rápido. Instalação no Mac: `jarvis/README.md`, seção 5.
- Se a vila for baixada de novo do site: rodar os patches na ordem (zangão, albi, bumblebee,
  vila01_campo, vila03_arena, orelha), depois `python3 doc/vila/ligar_jarvis.py
  bot/vila/vila.html` (no fim, `propulsor` troca o núcleo pelo mascote com propulsores),
  `python3 doc/vila/ligar_vila05_parque.py bot/vila/vila.html` (o parque do Orelha),
  `python3 doc/vila/ligar_orelha_agenda.py bot/vila/vila.html` (horário e Arquivo do Orelha),
  `python3 doc/vila/ligar_vila04_garagem.py bot/vila/vila.html` (a garagem do Jarvis),
  `python3 doc/vila/ligar_vila02_ponte.py bot/vila/vila.html` (a ponte do Bumblebee) e por último
  `python3 doc/vila/ligar_vila03_arena_att.py bot/vila/vila.html` (a arena nova do Albi).

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
├── orelha/              # Orelha, relatório do dia só lendo o VIOS (separado como o Albi; ver orelha/README.md)
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
│   ├── eventos.py       # eventos para a vila (saida/eventos.jsonl, GET /eventos; POST /eventos do Zangão e do Jarvis)
│   ├── zangao.py        # roda o Zangão em segundo plano pela vila (/zangao/status, /zangao/rodar)
│   ├── albi.py          # página /albi: guarda o .txt, roda o Albi e repassa os eventos dele à vila
│   ├── jarvis.py        # roda o Jarvis (pasta jarvis/) pela vila e lista as planilhas (/jarvis)
│   ├── orelha.py        # horário do Orelha e arquivo dos relatórios do dia (/orelha, /orelha/status)
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

### Segundo usuário do VIOS — Relatório de processos por Grupo Cliente

O Jarvis, com outro login do VIOS, gera por grupo de clientes uma planilha .xlsx e um PDF no papel
timbrado (com o "Resumo do mês" feito pela IA). Fica na pasta
própria `jarvis/`; documentação em [jarvis/README.md](jarvis/README.md).

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
| `FERIADOS_PESQUISA` | não | Pesquisa feriados na internet antes da análise (`true`/`false`); só roda com `PRAZO_CONTAGEM=feriados` | `true` |
| `DUPLICIDADE_ATIVA` | não | `true` liga o detector de duplicadas (Passo 17); `false` = desligado (a Controladoria tira as duplicadas no VIOS) | `false` |
| `PRAZO_CONTAGEM` | não | `simplificada` = só sábado e domingo ficam de fora (feriados e recesso contam como dia útil); `feriados` = calendário antigo por tribunal (Passo 13) | `simplificada` |
| `SAIDA_PASTA` | não | Pasta dos `.txt` | `saida` |
| `HEADLESS` | não | Chrome sem janela | `false` |
| `TIMEOUT` | não | Espera máxima (s) | `20` |
| `MANTER_ABERTO` | não | Não fecha o Chrome no fim | `true` |
| `NAVEGADOR_RAPIDO` | não | O Chrome não espera recursos do VIOS que o robô não usa (ganho pequeno, ~3%) | `true` (padrão) |
| `ENVIO_REDE` | não | Página de envio aberta para a rede (padrão: só nesta máquina) | `true` |
| `ENVIO_SENHA` | com `ENVIO_REDE=true` | Senha pedida pela página de envio | (definir no `.env`) |
| `ZANGAO_PASTA` | não | Pasta do Zangão neste computador (com `.venv` e `.env` dele); liga os botões da Vila 02 | `~/zangao` |
| `ALBI_PASTA` | não | Pasta do Albi (com `.venv` e `.env` dele); vazio = `albi/` deste repositório | `~/albi` |
| `ORELHA_PASTA` | não | Pasta do Orelha, de onde o Sam lê o horário e os relatórios (`/orelha`); vazio = `orelha/` deste repositório | `~/orelha` |
| `VILA06_URL` | não | Endereço do bot do Previdenciário para a Vila 06 (vazio = simulação) | vazio |
| `VILA06_TOKEN` | não | Mesmo `VILA_TOKEN` do `.env` do bot (RN28) | (no `.env`) |
| `VILA06_CERTIFICADO` | não | Certificado próprio do bot (HTTPS na rede interna) | vazio |
| `VILA06_CLIPES` | não | Pasta dos vídeos da Vila 06 (fora do git) | `<SAIDA_PASTA>/vila06_clipes` |

**Site com certificado vencido.** Se o certificado do VIOS (ou do Sonar, no Albi) vencer, o Chrome
mostra "Sua conexão não é particular" no lugar do login. O Sam, o Orelha, o Jarvis e o Albi clicam
em **Avançadas** > **Ir para ... (não seguro)** e avisam no log (`passar_aviso_certificado`, em
`bot/navegador.py`, `orelha/nucleo/navegador.py`, `jarvis/nucleo/navegador.py` e `albi/certificado.py`).
Só fazem isso com o erro `net::ERR_CERT_DATE_INVALID` (vencido) e no endereço do próprio site.
Qualquer outro erro de certificado continua bloqueando o login.

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
