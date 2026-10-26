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
| Código (`bot/analise.py`) | Confere as regras fixas da skill e marca alertas ⚠; insere Breno; detecta duplicidade |
| Pessoa | Revisa `saida/analise_*.md` antes de lançar no VIOS |

- **Trocar de IA:** `LLM_PROVEDOR=openai` ou `anthropic` no `.env` (+ a chave).
  Cada provedor fica num arquivo em `bot/ia/`; os dois devolvem o mesmo JSON.
- **Contagem de prazo:** começa no 1º dia útil após a **publicação**; dias úteis
  (ou corridos, se a IA indicar); vencimento em dia não útil vai para o próximo
  útil; D-2 = 2 dias úteis antes do fatal; RPV e emenda da Suhiane = próximo dia
  útil após a publicação; tarefa ANALISAR = o D-2 mais cedo entre embargos,
  recurso e prazo principal. Feriados locais vão em `doc/feriados.txt`.
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
| `doc/feriados.txt` | Linha com escopo que vale para o processo | — |

- **Por que conservador:** contar um feriado que não existe empurra o prazo
  para depois e pode causar perda de prazo. Na dúvida, o bot mantém a data mais
  cedo e avisa. Quando a Controladoria confirmar uma suspensão (ex.: portaria do
  TRF5 para 28/10), basta cadastrar em `doc/feriados.txt`:
  `28/10/2026 ; JUSTIÇA FEDERAL ; Dia do Servidor (Portaria TRF5 nº ...)` e
  rodar `./rodar_analise.sh --recalcular` (sem custo de API).
- A tabela cobre 2026 e 2027 e só as **capitais**; cidades do interior entram
  em `doc/feriados.txt`.

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
| Data para conclusão (`fo[data_prevista]`) | Data calculada na análise; tarefa sem data (ex.: ciência) = hoje |
| Responsáveis | O que o VIOS já traz (advogado do processo) + BRENO quando a regra pede |
| Texto intimação | Marcado (padrão do VIOS) |
| Observação | Descrição da tarefa da análise |

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
- A lista de tarefas do VIOS muda conforme o processo (ex.: `CIÊNCIA (CÍVEL)`
  existe em processo cível); se o nome não existir, a CI fica para lançamento
  manual e o erro aparece no log.
- **Resultado (23 a 25/10/2026):** 20 intimações, 19 tarefas gravadas e
  conferidas, 1 por CI. Ficou de fora a CI 42419 (sustentação oral
  previdenciária — nome com erro na skill e pendências): lançar manualmente.

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

Primeira instalação:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env       # e preencher
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
| `SAIDA_PASTA` | não | Pasta dos `.txt` | `saida` |
| `HEADLESS` | não | Chrome sem janela | `false` |
| `TIMEOUT` | não | Espera máxima (s) | `20` |
| `MANTER_ABERTO` | não | Não fecha o Chrome no fim | `true` |

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
- `logs/lancamento_ci<CI>_*.png` — prints do formulário e do quadro "Tarefas".
- `logs/bot.log` — tudo o que o bot fez (a senha nunca é registrada).
- `logs/erro_*.png` — screenshot da tela no momento de qualquer erro.
- Card ou linha com problema é **pulado** e registrado como `WARNING`;
  o bot continua com os demais.

---

## 7. Próximos passos

1. ~~Separar cada intimação em campos~~ ✅ feito no Passo 9.
2. **Evitar duplicidade**: guardar os `comunicacao_id` já processados.
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
