# Changelog

Todas as mudanças do bot de intimações ficam registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Tipos: **Adicionado**, **Alterado**, **Corrigido**, **Removido**, **Segurança**.

Como registrar: toda alteração entra primeiro em **[Não lançado]**; quando a
etapa estiver pronta e testada, vira uma nova versão com data.

---

## [Não lançado]

### Adicionado — Segundo usuário do VIOS (função nova, em definição)
- Branch `nova-funcao` para desenvolver a função nova sem afetar o robô de
  intimações no `main`.
- `.env.usuario2.example`: modelo do `.env` do segundo usuário (mesmo
  escritório, outro login), com pasta de saída própria (`saida_usuario2`).
- `rodar_usuario2.bat`: roda o bot com o `.env.usuario2` no Windows (dois
  cliques ou `.\rodar_usuario2.bat`). Login testado em 28/10/2026.
- Depois do login, o segundo usuário vai para a tela de **Relatórios**
  (`?pag=sys/relatorios/relatorios.php`, em `NAVEGACAO_URL_FINAL`). Testado
  em 28/10/2026: a tela abre com a lista de relatórios. O que fazer nela
  ainda será definido.

### Adicionado — Relatório de processos por Grupo Cliente
- `relatorio_processos.py` + `bot/processos_grupo.py`: na tela Processos
  (`processos-lista.php`), escolhe o **Grupo Cliente**, põe "Mostrar" em 500,
  pesquisa e lê a tabela. Gera **um .txt por grupo** em
  `saida_usuario2/relatorios/AAAA-MM-DD/<GRUPO>.txt`, com resumo (por empresa,
  área e posição do cliente) e um bloco por processo em linguagem simples,
  para outra IA escrever o relatório para o cliente.
- Só lê: não usa Apagar/Editar nem "Processar" (ações em lote) da tela.
- `.env.usuario2`: `PROCESSOS_GRUPOS` (grupos separados por `|`, ou `todos`)
  e `RELATORIO_PASTA` (vazio = `saida_usuario2/relatorios`). Na linha de
  comando: `--grupo "3A FRIOS"`; o nome do grupo não depende de acento nem de
  maiúsculas.
- `rodar_usuario2.bat` passa a gerar o relatório.
- Teste 28/10/2026: 3A FRIOS, 17 processos, 0 erros, igual à tabela do VIOS.

### Segurança
- `imgs/` no `.gitignore`: prints de tela têm dados de clientes.

### Alterado — Documentação do relatório de processos
- Novo `RELATORIO_PROCESSOS.md` com a documentação completa do relatório por
  Grupo Cliente (passo a passo, .txt gerado, como rodar, instalação no
  Windows, configuração, segurança, pontos de atenção e testes). A seção em
  `DOCUMENTACAO.md` virou um link para ele.
- `CLAUDE.md`: mudança no relatório também atualiza o `RELATORIO_PROCESSOS.md`.

### Segurança
- `.gitignore` passa a ignorar qualquer `.env.*` (ex.: `.env.usuario2`) e as
  pastas `saida_*/`; só os modelos `*.example` são versionados.

### Adicionado — Análise em lote no Claude
- `bot/ia/anthropic_ia.py`: lote pela Message Batches API (metade do preço),
  com a mesma interface do lote da OpenAI; triagem, teto de gasto e retomada
  funcionam igual. No lote não vai o fallback de recusa (a API não aceita):
  CI recusada é refeita uma a uma, com fallback.
- Pesquisa de feriados no Claude com a busca nova (`web_search_20260209`,
  localização Brasil); no Haiku continua a antiga.
- `anthropic==0.72.0` passa a constar no `requirements.txt` (último
  compatível com Python 3.8). Testado com API simulada; falta testar com
  crédito de verdade.

### Adicionado — Triagem por importância e teto de gasto
- `LLM_MODELO_SIMPLES` (vazio = desligado): intimações simples vão para um
  modelo mais barato. O código procura no teor sentença, acórdão, decisão,
  audiência, RPV/precatório, tutela/liminar, embargos, apelação ou recurso
  (sem contar o nome da classe do processo); achou, vai direto para o
  `LLM_MODELO`. A resposta do barato com ato importante, embargos/recurso que
  cabem, área pendente, falta de dados, bloqueio, tarefa/data pendente ou erro
  é refeita pelo `LLM_MODELO` (no lote, numa 2ª rodada da Batch API).
- `LLM_MODELO_FERIADOS`: modelo próprio para a pesquisa de feriados.
- `LLM_LIMITE_US`: teto de gasto por execução. O bot estima o custo antes de
  cada chamada/lote; o que não cabe fica com erro (não é lançado) e a pesquisa
  de feriados fica para a próxima. Novo `bot/custo.py` com a tabela de preços
  (corrigível por `LLM_PRECOS`).
- Relatório e log mostram o modelo de cada CI, o motivo da triagem e o gasto
  estimado; o JSON guarda `modelo`, `triagem` e `custo_us`. O uso das
  respostas passa a contar as pesquisas na web (`buscas`).
- Testado com IA simulada (lote, uma a uma, teto, recálculo, feriados): no
  lote de 26/10, 29 de 45 CIs no modelo barato, 7 reanalisadas; custo
  simulado de US$ 1,14 para US$ 0,73 (com o modelo barato a ~1/5 do preço).
  Falta testar com a API de verdade e comparar a qualidade do modelo barato
  com as correções da revisão de 27/10 antes de ligar.
- Tabela de preços com os valores oficiais de Claude Opus 5.5 (4/20),
  Sonnet 5.5 (2/10) e Haiku 5.5 (0,10/0,50) por milhão de tokens.
- Corrigido: "Billing hard limit has been reached" (limite de gasto da conta
  OpenAI) também para a análise com a mensagem "Sem créditos na API da IA",
  inclusive no envio do lote.

### Alterado — Pesquisa de feriados mensal e mais barata
- 1ª pesquisa (27/10/2026) custou ~US$ 2–4 para 8 tribunais: lê páginas e
  PDFs inteiros. Semanal, sairia ~US$ 10–15/mês.
- `bot/feriados_web.py`: pesquisa refeita só a cada 30 dias (antes 7), cobrindo
  ~95 dias (um mês de publicações + prazos).
- `bot/ia/openai_ia.py`: na pesquisa, no máximo 6 buscas por chamada
  (`max_tool_calls`), só o trecho relevante das páginas
  (`search_context_size: low`) e localização Brasil. Anthropic: `max_uses` 6.
- `doc/feriados.txt`: datas do TJES achadas na pesquisa de 27/10 (30/10 e 08/12
  contam; 07/12, só "ponto facultativo", ficou como AVISO).
- Estimativa: ~US$ 3/mês. A pesquisa feita em 27/10 cobria só 60 dias, então
  a próxima análise ainda pesquisa os tribunais uma vez no formato novo.

### Adicionado — Análise em lote (Batch API, metade do preço)
- A análise completa manda todas as intimações num lote da Batch API da
  OpenAI (`/v1/responses`), que custa 50% menos. A resposta costuma vir em
  minutos (a OpenAI garante até 24 h); como o bot vai rodar à meia-noite, dá
  tempo antes do expediente.
- `bot/ia/openai_ia.py`: `enviar_lote`, `status`, `resultados`, `cancelar`
  (mesmo pedido da análise normal: modelo, esforço, schema estrito, cache).
- `bot/analise.py` (`_analisar_em_lote`):
  - o id do lote fica em `saida/lote_<análise>.json`: se o programa cair,
    rodar de novo retoma o mesmo lote (já pago) em vez de mandar outro;
  - passou de `LLM_LOTE_ESPERA_MIN` (padrão 360 min), cancela, aproveita o
    que ficou pronto e analisa o resto uma a uma (preço normal);
  - CI que falhou dentro do lote é analisada de novo uma a uma;
  - sem créditos para tudo, como na análise normal.
- `--ci` continua analisando na hora (sem lote). Anthropic: ainda sem lote.
- `.env`: `LLM_LOTE=true` (padrão; `false` volta a analisar uma a uma) e
  `LLM_LOTE_ESPERA_MIN=360`.
- Testado com OpenAI simulada (lote normal, retomada após queda, cancelamento
  por tempo, sem crédito). Teste real pendente: conta sem créditos em
  27/10/2026.

### Corrigido — Créditos da IA esgotados
- Em 27/10/2026 os créditos da API OpenAI acabaram no meio da reanálise do lote
  de 26/10: o bot seguiu tentando as 18 CIs restantes e terminou como
  "Concluído" com 18 erros. Agora crédito esgotado (`insufficient_quota` /
  `credit balance`) para a análise na hora com a mensagem "Sem créditos na API
  da IA", como já acontecia com chave ou modelo errado. A análise anterior do
  lote foi restaurada; a parcial ficou em `saida/antigas/`.

### Segurança
- `.gitignore`: prints `doc/*.jpeg` também ficam fora do repositório (a foto do
  WhatsApp de 26/10/2026 tem dados de processo).

### Adicionado — Pesquisa de feriados na internet
- `bot/feriados_web.py`: antes de analisar, junta os tribunais e cidades do
  lote (tribunal pelo número CNJ: TJ da UF, TRT da região, Justiça Federal da
  seção) e pede à IA, com pesquisa na web, os feriados e suspensões de
  expediente/prazo dos próximos 60 dias, com o link da fonte. Grava as datas
  novas em `doc/feriados.txt` num bloco "Pesquisa automática" (dá para editar
  ou apagar).
  - Fonte oficial (`.jus.br`; feriado municipal também `.gov.br`/`.leg.br`) e
    suspensão confirmada → conta no prazo. Sem fonte oficial ou incerto →
    `AVISO` (data fica adiantada). Ponto facultativo sem efeito nos prazos não
    é gravado. Nacionais, Lei 5.010/66 e recesso 20/12–20/01 são ignorados
    (o calendário já conta).
  - Cache em `saida/feriados_pesquisa.json`: o mesmo tribunal/cidade só é
    pesquisado de novo depois de 7 dias.
  - Falha na pesquisa não impede a análise.
- `bot/ia/`: `responder(..., pesquisar=True)` liga a ferramenta de pesquisa na
  web (OpenAI `web_search`; Anthropic `web_search_20250305`).
- `bot/prazos.py`: novo escopo ramo + cidade (ex.: `JUSTIÇA ESTADUAL/SOBRAL/CE`).
- `.env`: `FERIADOS_PESQUISA=true` (padrão; `false` desliga).
  `analisar.py --recalcular --feriados` pesquisa antes de recalcular.
- 1ª pesquisa (27/10/2026, 8 tribunais, ~9 min): confirmou 30/10 no TRT7
  (Portaria 518/2025, calendário de 2026) e na JFCE (Ato TRF5 435/2026), além de
  feriados municipais (São Benedito 25/11, Chaval 27/11) e 08/12 (TJCE). Com
  isso as datas dos processos de 26/10 batem com as da revisão. As linhas
  manuais com AVISO para TRT7/JFCE foram retiradas; as de 07/12 descritas só
  como "ponto facultativo" (TRT7, TJPA, TJPI) ficaram como AVISO.

### Alterado — Regras da revisão de 27/10/2026 (Controladoria)
- **Prazos na tarefa de análise** (`bot/analise.py`, `_meio` e `_descricao`):
  se cabe ou pode caber embargos ou recurso, as duas linhas com data D-2,
  pelo prazo legal quando a intimação não informa; cabimento pendente também
  leva data (antes: "PENDENTE – CONFIRMAR CABIMENTO", sem data). Se não cabe
  nenhum, as linhas "NÃO CABE" saem e fica só `PRAZO FATAL (D-2)`. A linha do
  prazo fatal passa a ser a data da própria tarefa (antes faltava quando só
  havia prazo de embargos/recurso, ex.: 0011460-69). Análise sem prazo nenhum:
  `PRAZO FATAL:` com o dia útil seguinte à publicação (antes: data de hoje).
- **Área pelo responsável:** auxiliar TAMI = Execução. A conferência de área ×
  auxiliar deixou de ser só alerta: divergência bloqueia o lançamento
  (`_conferir_area`). Base: 3002281-94 (Execução lançada com auxiliar JOAN).
- **Não lançar quando falta informação:** campo novo `faltam_dados` na
  resposta da IA (ex.: audiência com dados incompletos, que exige o PJe). A
  análise gera `bloqueios` e `bot/lancamento.py` pula a CI com o motivo no log.
- Skill atualizada (`SKILL.md`, `references/roteamento-interno.md`,
  `regras-prazos-recursos.md`, `pop-fluxo-intimacoes.md`).

### Corrigido — Feriado do Dia do Servidor 2026 (30/10)
- Revisão das tarefas de 26/10/2026: os prazos que passavam por 30/10 ficaram
  um dia antes (ex.: 3005926-13, apelação: bot 17/11, correto 18/11; D-2
  13/11 → 16/11). O TJCE transferiu o Dia do Servidor de 28/10 para 30/10 e o
  bot contava 30/10 como dia útil. Não houve perda de prazo (data antecipada).
- `doc/feriados.txt`: 30/10/2026 cadastrado como feriado no TJCE; no TRT7 e na
  JFCE como `AVISO` (portaria de 2026 não encontrada).
- Regra combinada: contar o máximo de feriados possível; sem confirmação, a
  data fica adiantada para não perder prazo.

### Adicionado — Feriado por tribunal e suspensão não confirmada
- `bot/prazos.py`: o calendário separa Justiça Estadual, do Trabalho e Federal
  pelo dígito J do número CNJ (antes: Estadual e Trabalho juntos; federal só
  pela "Esfera"). Novos escopos em `doc/feriados.txt`: `JUSTIÇA DO TRABALHO`
  e ramo + UF (`JUSTIÇA ESTADUAL/CE`, `JUSTIÇA DO TRABALHO/CE`,
  `JUSTIÇA FEDERAL/CE`). O escopo `JUSTIÇA ESTADUAL` deixa de valer para a
  Justiça do Trabalho.
- 4ª coluna opcional `AVISO`: a data não estende o prazo e a análise alerta
  "não confirmado: prazo não estendido".

### Alterado — Formatação da descrição no VIOS
- Pedido da Controladoria (foto em `doc/WhatsApp Image 2026-10-26 at
  16.49.56.jpeg`): todo o texto que o robô escreve na Observação vai em
  **negrito** (nome do ato, ex.: DESPACHO, e o resumo); as linhas de prazo
  fatal ficam em negrito e **vermelho**, agora também `PRAZO FATAL (D-2):`
  (antes só `PRAZO FATAL:` da RPV/emenda). O teor que o VIOS acrescenta
  ("---------- Intimação: ...") continua normal. Mesma regra na prévia da
  página de revisão.

### Adicionado — Detecção de duplicatas
- `bot/duplicidade.py`: acha a mesma publicação em mais de uma CI do mesmo
  processo (texto igual tirando links, números e códigos; no máximo 10
  palavras diferentes). A original é a CI endereçada ao cliente; se não der
  para saber, a de texto mais completo; empate, a de número menor.
- Análise (`bot/analise.py`): a cópia ganha `duplicada_de` e o alerta
  "DUPLICADA DA CI X... Não abrir nova tarefa"; a original ganha a observação
  de que tem cópia. Mesmo processo com ato diferente (ex.: perícia designada e
  depois redesignada) não é duplicata: alerta para atualizar a tarefa em vez
  de abrir outra. Funciona também no `--recalcular`.
- Lançamento (`bot/lancamento.py`): CI duplicada é ignorada (log "duplicada da
  CI X, ignorada").
- Página: novo estado "Duplicada (ignorada)", com aviso mostrando a original,
  o motivo e a diferença entre os textos (ex.: "Só na CI 42476: SERVICOS
  ADMINISTRATIVOS MEDEIROS LTDA / Só nesta: TIAGO ARAUJO DE OLIVEIRA");
  botão "Revisar como intimação separada" se não for duplicata. A original
  avisa qual CI é a cópia. Reimportar a análise atualiza a duplicidade das CIs
  ainda não revisadas.
- Skill (`references/roteamento-interno.md`, seção Duplicidades): a mais
  completa é a original e a outra é ignorada; só mudando o destinatário,
  vale a endereçada ao cliente; ato diferente não é duplicata.
- 26/10/2026: CIs 42475 (cópia da 42476) e 42471 (cópia da 42472).

### Adicionado — Página de revisão humana
- `revisar.py` / `rodar_revisao.sh`: importa uma `saida/analise_*.json` para o
  banco `saida/revisao.db` e abre a página local http://127.0.0.1:5000.
- `bot/revisao.py`: banco SQLite com a análise, o teor, as tarefas editadas,
  o estado (aguardando, na fila, lançando, lançada, erro, descartada), quem
  validou e quando. Reimportar não apaga edições.
- `bot/web.py` + `bot/templates/revisao.html`: lista de CIs por estado,
  dados do processo, alertas, teor, edição das tarefas (lista oficial, data,
  descrição com prévia do `PRAZO FATAL` em vermelho, BRENO), adicionar e
  remover tarefa; Validar (com conferência), Salvar rascunho, Descartar e
  Reabrir.
- Dependência nova: `flask==3.0.3` (último compatível com Python 3.8).
- Ainda não lança: as CIs validadas ficam na fila para a próxima etapa.
- Data das tarefas em texto DD/MM/AAAA (com barra automática e aviso de
  data inválida), em vez do calendário do navegador, que aparecia em
  formato americano (mês/dia).
- Datas relativas ao dia são refeitas na página: a análise é da véspera, então
  `MESMO_DIA` vira a data de hoje e `DIA_SEGUINTE` o próximo dia útil, com o
  aviso "Data recalculada para hoje; na análise estava ...". Data editada à
  mão não é recalculada (`bot/revisao.py`, `datas_relativas`).
- Responsáveis por tarefa na página. **Padrão: "Automático pelo VIOS"** — o
  robô não mexe no campo e o VIOS marca sozinho, como nos 19 lançamentos de
  26/10/2026 (lá o VIOS marcou o auxiliar da intimação, não o advogado do
  processo RONEELY FEITOSA; nas Ciências, AMANDA LEITE MENDES). A página
  mostra quem o VIOS deve marcar (sigla do auxiliar → nome: SUH → SUHIANE,
  TAMI → TAMIRA, JOHN → FRANCISCO JOHNYS...). "Escolher outras pessoas" passa
  para a escolha manual (começa pelos auxiliares; dá para tirar, adicionar
  qualquer pessoa da lista do VIOS e "usar estes em todas as tarefas");
  "Voltar para o automático do VIOS" desfaz. Cabeçalho da CI separa
  "Auxiliar (responsável pela tarefa)" de "Advogado do processo".
- `./rodar_revisao.sh --atualizar-responsaveis`: entra no VIOS, abre o
  formulário de uma CI (sem preencher) e salva as pessoas do campo
  Responsáveis em `saida/responsaveis.json` (42 pessoas em 26/10/2026).
- `bot/lancamento.py`: tarefa com lista `responsaveis` marca exatamente essas
  pessoas no VIOS e confere na tela antes de adicionar (sem a lista, segue o
  comportamento antigo: padrão do VIOS + BRENO). Ainda não testado no VIOS.
- Novo visual da página de revisão, seguindo a skill de front-end
  (`doc/SKILL.md`):
  - Duas colunas: a intimação para ler à esquerda (teor em fonte de leitura,
    Literata, visível sem clicar) e as tarefas para conferir à direita.
  - Fila agrupada por situação ("Para validar", "Na fila do robô"...) em vez
    dos filtros no topo, e progresso "N de 45 revisadas".
  - Cabeçalho da CI com cliente, processo, ato, publicação, prazo fatal em
    vermelho, D-2, advogado, auxiliar e link para o VIOS.
  - Data da tarefa em destaque com o dia da semana; sábado e domingo aparecem
    em vermelho ("fim de semana").
  - Descrição mostra primeiro como fica no VIOS; "Editar texto" abre o campo.
  - Alertas em "Conferir antes de validar"; pendências abertas; prazos,
    observações e sugestão do VIOS recolhidos.
  - Ctrl+Enter valida. Fonte da interface: Public Sans. Sem rótulos em
    caixa alta. Funciona em tela pequena (uma coluna).

### Alterado — Rótulo da data em RPV e emenda da Suhiane
- Na descrição da tarefa (Observação do VIOS), a linha
  "DATA DA TAREFA NO VIOS — PRIORIDADE EMENDA/SUHIANE: DD/MM/AAAA" (e a de
  PRIORIDADE RPV) virou apenas "PRAZO FATAL: DD/MM/AAAA", em negrito e
  vermelho. A data continua a mesma (dia útil seguinte à publicação). Base:
  processo 0038150-04.2026.4.05.8103. Skill (`SKILL.md` e
  `references/roteamento-interno.md`) atualizada com o novo rótulo.

### Adicionado — Prazo previsto em lei na skill
- Skill da Controladoria (`references/regras-prazos-recursos.md` e
  `SKILL.md`): quando a intimação não informa o número de dias, usar o prazo
  previsto em lei e escrever na descrição "Prazo previsto em lei: N dias
  úteis (meio)". Tabela passada pela Controladoria em 26/10/2026:
  - Cível: recursos em geral (Apelação, Agravo de Instrumento, Agravo
    Interno, REsp, RE) 15 dias úteis; Embargos de Declaração 5 dias úteis.
  - Trabalhista: Recurso Ordinário, Recurso de Revista, Agravo de
    Instrumento, Agravo de Petição e Embargos ao TST 8 dias úteis; Embargos de
    Declaração e Embargos à Execução 5 dias úteis; Recurso Extraordinário 15.
  - Com cabimento pendente, informar mesmo assim o prazo legal.
- Instrução da IA (`bot/analise.py`): `dias` usa o prazo legal da skill
  quando o ato não informa (antes ficava 0).
- O `.zip` original da skill em `doc/` não foi alterado.

### Adicionado — Lançamento do período inteiro
- **Usuário de login do VIOS trocado** no `.env` (feito pelo usuário em
  26/10/2026); login testado com o novo usuário.
- `lancar.py --ci todas`: lança todas as CIs da análise.
- Não lança a CI quando alguma tarefa com prazo ficou sem data calculada
  ("PENDENTE"); só tarefa sem prazo (ciência) usa a data de hoje.
- Quadro "Tarefas" tem que estar vazio antes de adicionar e, depois, ter
  exatamente uma linha por tarefa. No modo teste o VIOS registrou uma vez o
  Adicionar em dobro (CI 42429); a conferência barrou antes do Gravar.
- Apelido para nome com erro de digitação na skill:
  `MINUTAR PETIÇÃO EXECUÇÃO (EXECUÇÃO) 2026)` → `MINUTAR PETIÇÃO (EXECUÇÃO) 2026`.
- **Lançamento real de 23 a 25/10/2026 (26/10/2026):** 20 intimações
  analisadas, 19 tarefas gravadas e conferidas (1 tarefa ativa por CI, sem
  duplicata). Pesquisa "sem tarefa" do período ficou só com a CI 42419.
- **CI 42419 não lançada:** sustentação oral previdenciária — nome da tarefa
  na skill com erro (`SUSTENTAÇÃO ORAL PPREVIDENCIÁRIO) 2026`) e pendências
  (cliente recorrente ou recorrido; formato da sessão). Lançar manualmente.

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
