# Changelog

Todas as mudanças do bot de intimações ficam registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Tipos: **Adicionado**, **Alterado**, **Corrigido**, **Removido**, **Segurança**.

Como registrar: toda alteração entra primeiro em **[Não lançado]**; quando a
etapa estiver pronta e testada, vira uma nova versão com data.

---

## [Não lançado]

### Corrigido — pje-busca: nível 3 lê pelo filtro "Processos com Associação" (24/11/2026)
- A 1ª rodada (busca pelo número no campo do Acervo Geral) dava "fora do acervo" para quase tudo: depois de algumas
  buscas a lista do PJe deixa de atualizar (o campo mostra o número novo e a lista continua no anterior).
- Agora `vigia.py associados` liga o filtro "Processos com Associação" (60 de 358 processos em 24/11/2026), percorre
  as páginas ("Próximo"; volta ao "Primeiro"), abre a janela de cada linha, lê a tabela (5 por página) e fecha com Esc;
  depois desliga o filtro e lê a lista do acervo inteiro só para saber o que do VIOS está fora dele (`assoc_acervo`).
- Base: a 1ª rodada COMPLETA é base de tudo; depois, associado novo de processo que já estava no acervo = alerta
  (o 1º associado de um principal também alerta). Processo que acabou de entrar no acervo vira base só dele.
- Opções novas: `--paginas N` e `--sem-cobertura` (teste, não grava), `--simular`. Sai `--numero`/`--limite`.
- Teste no PJe real (24/11/2026, 1ª página): 10 de 10 lidos, 16 associados, 0 erro. A maioria dos processos com
  associação do acervo está fora da lista do VIOS (antigos/arquivados/outra área), então o nível do associado novo
  passou a ser: VERMELHO só com o principal no VIOS; AMARELO com o principal fora do VIOS; INFO se já está no VIOS.
  A base separa "principal no VIOS (conferir)" do resto. A aba Cumprimentos mostra o amarelo.
  As tabelas do teste anterior são recriadas sozinhas. JavaScript conferido no PJe real (filtro, páginas, janela, Esc).

### Adicionado — pje-busca: documento de contexto do vigia de cumprimentos (24/11/2026)
- `pje-busca/doc/CONTEXTO_cumprimentos_2026-11-24.md`: problema, níveis do vigia, resultados, aba Cumprimentos,
  comandos, arquivos, pendências e riscos (sem senhas).

### Adicionado — Vila dos Bots: aba Cumprimentos de sentença (24/11/2026)
- Cartão **Cumprimentos** na entrada e página `/cumprimentos` (`bot/cumprimentos.py`, `bot/templates/cumprimentos.html`):
  cumprimentos de sentença e execuções contra clientes que não estão no VIOS, lidos do banco do vigia do pje-busca
  (DJEN), com pendentes em cima e há quantos dias saiu a 1ª publicação.
- Conferência da equipe em cada processo (situação, quem conferiu, observação, com histórico) em
  `pje-busca/dados/cumprimentos_conferencia.json` (fora do git, permissão 600).
- Botão "Verificar agora no DJEN" (`vigia.py djen` em segundo plano, ambiente limpo, uma execução por vez) e os
  relatórios completos de cada dia. Ações de cumprimento de convenção (sindicato) ficam à parte, sem alerta.
- Banco do vigia aberto só para leitura; nada do pje-busca é importado. Nova variável opcional `PJE_BUSCA_PASTA`.
- Testes em `tests/test_cumprimentos.py` (dados fictícios).
- Lista **Empresas sem nenhuma publicação no DJEN** na mesma página (CNPJ, processos do TRT7 no VIOS, nomes buscados)
  com conferência do nome: "Nome corrigido" grava até 3 nomes do tribunal em `pje-busca/dados/nomes_conferidos.json`
  (fora do git, permissão 600), rota `POST /cumprimentos/nome`.

### Adicionado — pje-busca: nível 3, "Processos associados" no PJe (24/11/2026)
- `python3 vigia.py associados` (`src/vigia_associados.py`): entra no PJe pelo Presto e, no Acervo Geral, lê os
  "Processos associados" de TODOS os principais ativos do TRT7 da lista do VIOS (formato Balanceado). Só pesquisa,
  abre a janela de associados (paginação, se houver) e fecha com Esc: não abre documento, não peticiona, não altera nada.
- 1ª leitura de cada principal = base (sem alerta); associado novo fora do VIOS = VERMELHO; já no VIOS = informação.
  Tabelas `assoc_principais`, `assoc_associados`, `assoc_rodadas`; relatório `saida/associados_AAAA-MM-DD.txt`;
  capturas de erro em `logs/associados/`. Se a sessão cair, entra de novo uma vez; para com 5 erros seguidos.
- Opções: `--numero <CNJ>` (teste com um principal), `--limite N`, `--simular`.
- Aba Cumprimentos: seção "Associados novos no PJe (nível 3)" com a mesma conferência, números no topo, dados da
  última leitura, botão "Verificar associados no PJe" e relatórios. Testes em `pje-busca/tests/test_associados.py`
  (PJe falso) e `tests/test_cumprimentos.py`; o JavaScript foi conferido no HTML real do Acervo Geral (19/11/2026).

### Adicionado — pje-busca e aba Cumprimentos: processo principal de cada cumprimento no VIOS (24/11/2026)
- `vigia_djen.achar_principal`: lê as publicações do próprio cumprimento (até 100) e procura o principal na lista do
  VIOS — 1º pelo número citado no texto da publicação; 2º pelo mesmo exequente (polo ativo = Autor no VIOS), de
  preferência na mesma vara. Resultado em `djen_principais`, refeito a cada rodada enquanto não for achado.
- Novo comando `python3 vigia.py principais` (só essa ligação, rápido). A rodada do `djen` também faz.
- A aba Cumprimentos mostra em cada cumprimento "Cliente nosso: o processo principal X está no VIOS (CI, empresa,
  advogado)" e como foi achado, ou "Principal não achado no VIOS".
- Conferido com dados reais: 0001772-66.2024.5.07.0024 → 0000064-49.2022.5.07.0024 (citado e mesmo exequente);
  0001226-95.2026.5.07.0038 → 0000743-70.2023.5.07.0038 (mesmo exequente e vara); 0001368-02.2026.5.07.0038 →
  0002754-04.2025.5.07.0038. Testes em `pje-busca/tests/test_djen.py` e `tests/test_cumprimentos.py`.

### Alterado — pje-busca: vigia do DJEN usa os nomes conferidos pela equipe (24/11/2026)
- `vigia.py djen` lê `dados/nomes_conferidos.json` (gravado pela aba Cumprimentos) e busca também por esses nomes
  (origem `manual` em `djen_nomes`; 1ª busca com nome novo vira auditoria). Seção "NOMES CONFERIDOS" no relatório.
- Nova tabela `djen_consultas` (resultado de cada empresa na última rodada: publicações e nomes buscados).
- Testes novos em `pje-busca/tests/test_djen.py`.

### Adicionado — Orelha: função `comentarios`, comentários dos últimos 90 dias de uma lista de processos (23/11/2026)
- `./rodar.sh --funcoes comentarios` lê os números de `orelha/entrada/comentarios.txt` (fora do git), acha o CI
  de cada um pela busca "Nro do Processo" (só GET; o número pode estar no CNJ ou em "Outros"), abre a ficha e lê
  o quadro "Comentários". Grava `saida/<data>/comentarios-90dias.csv` (Excel) e `.json`, com permissão 600.
- Configuração: `ORELHA_COMENTARIOS_LISTA`, `ORELHA_COMENTARIOS_DIAS` (padrão 90), `ORELHA_COMENTARIOS_TIMEOUT`.
  Fora do padrão e do relatório do dia.
- Testes em `orelha/tests/test_comentarios.py`, com fixtures fictícias em `orelha/fixtures/comentarios/`.

### Adicionado — Orelha: função `processos`, planilha com todos os processos da área (17/11/2026)
- `./rodar.sh --funcoes processos` lê na lista de processos do VIOS (só GET) todos os processos da área
  Previdenciária, ativos e encerrados, e grava `saida/<data>/processos-previdenciaria.csv` (Excel) e `.json`.
- A lista devolve no máximo 500 por pesquisa: acima disso lê por ano de cadastro, dividindo o período cheio.
- Configuração: `ORELHA_PROCESSOS_AREAS` (padrão 4), `ORELHA_PROCESSOS_SITUACOES`, `ORELHA_PROCESSOS_DESDE`,
  `ORELHA_PROCESSOS_MAX_PAGINAS`, `ORELHA_PROCESSOS_TIMEOUT`. Fora do padrão e do relatório do dia.
- Testes em `orelha/tests/test_processos.py`, com fixtures fictícias em `orelha/fixtures/processos/`.
- A planilha sai em blocos (ATIVOS, ENCERRADOS e ATIVOS SEM TAREFA ABERTA) e ganhou a coluna Tarefas, lida pelo
  filtro nativo "Com ou sem tipo de tarefa? = Sem" (Abertas / Todas). `ORELHA_PROCESSOS_TAREFAS=false` desliga.
### Adicionado — pje-busca: verificação pelo DJEN (níveis vermelho/amarelo) e correção dos acentos do VIOS (23/11/2026)
- `pje-busca/src/vigia_djen.py` + `vigia.py djen [--simular] [--empresa TEXTO]`: para cada empresa da base do vigia
  consulta a API pública do DJEN (`comunicaapi.pje.jus.br`, por nome da parte + TRT7, sem login e sem CAPTCHA) e
  classifica cada processo do TRT7 que não está no VIOS nem já foi avisado: VERMELHO = cumprimento de sentença /
  execução; AMARELO = qualquer outro processo em que o escritório não está. 1ª rodada = base (lista uma vez os
  processos do DJEN fora do VIOS). Relatório `saida/djen_AAAA-MM-DD.txt`; tabelas `djen_processos` e `djen_rodadas` no
  `dados/vigia.sqlite`. `pje-busca/tests/test_djen.py` (7 testes, inclusive o caso real MM COMERCIO).
- Testes de 23/11: Consulta de terceiros sem CNPJ; certidão trabalhista com CAPTCHA por emissão e sem cumprimento
  provisório; DJEN achou o CumPrSe 0001368 em 31/07/2026; "Processos associados" do principal mostra o CumPrSe
  (nível 3, a implementar). `PROJETO (1).md` seção 4.3.
- Corrigido: a leitura do VIOS trocava acentos por "�" (o VIOS manda Windows-1252); `src/vios_chrome.py` decodifica
  a resposta (UTF-8, senão Windows-1252). Recriar a base do vigia (`dados/vigia.sqlite`) depois desta correção.
- `pje-busca/.env.example`: `VIGIA_DJEN_TRIBUNAL=TRT7`, `VIGIA_DJEN_PAUSA_S=1.5`.
- Ajustes depois da 1ª rodada real (162 empresas, 4.149 publicações, 0 erros): (1) "AÇÃO DE CUMPRIMENTO" (sindicato x
  convenção) deixou de ser vermelho; (2) nome calibrado pelo tribunal: a cada 30 dias, lê no DJEN (`numeroProcesso`) os
  destinatários do polo passivo de até 2 processos do TRT7 já conhecidos da empresa e passa a buscar também por esse
  nome (ex.: VIOS "COPCEL - TRANSPORTE & COMERCIO DE GRAO LTDA" x tribunal "COPCEL - COMERCIO DE PO E CERA DE CARNAUBA
  LTDA - EPP"); a 1ª busca com nome novo vira auditoria daquela empresa; (3) publicação em que o cliente só aparece no
  polo ativo (autor: consignação, homologação de acordo) é ignorada; (4) `vigia.py djen --refazer-base` apaga só o
  estado do DJEN. Testes: 21.

### Adicionado — pje-busca: vigia VIOS → PJe, parte 1 (foto diária do VIOS e comparação) (23/11/2026)
- `pje-busca/vigia.py` (`vios [--simular] [--foto arquivo.json]`, `status`, `fila`): 1x por dia lê no VIOS a lista
  de processos ativos da Área 3 (Trabalhista) com o cliente na parte passiva, grava a foto do dia, compara com o
  estado e escreve `saida/vigia_AAAA-MM-DD.txt` com empresas novas, processos novos (TRT7 marcado para a fila do
  PJe), processos que voltaram e que saíram da lista. A 1ª rodada vira base (nada aparece como novo).
- `pje-busca/src/vios_chrome.py`: leitura pelo Chrome do Mac (AppleScript), só GET, com fetch() dentro de uma aba do
  VIOS (a tela não muda); se a sessão caiu, entra com `VIOS_USUARIO`/`VIOS_SENHA` numa aba nova e a fecha no fim.
  CNPJ da empresa pelo cadastro de pessoas (até `VIGIA_MAX_CNPJ` por rodada, as novas primeiro); CPF não é guardado.
- `pje-busca/src/vigia_estado.py`: estado em `dados/vigia.sqlite` (empresas, processos, rodadas); lista incompleta
  (teto de 500 linhas ou rodapé diferente) não marca saídas; `fila_pje()` = processos do TRT7 vistos nos últimos
  30 dias (para a parte 2). `pje-busca/tests/test_vigia.py`: 11 testes.
- Validado no VIOS real (só contagens): 363 linhas = rodapé 363, 361 com CNJ, 240 do TRT7; CNPJ achado (14 dígitos).
- Corrigido no 1º uso no Mac: (1) sessão do VIOS expirada não era reconhecida (o VIOS responde 200 com só
  `<meta HTTP-EQUIV="Refresh" ... URL=./entrar.php>`, sem redirecionar) e a lista saía "vazia" sem tentar o login;
  agora a lista e a consulta de CNPJ reconhecem esse caso e entram com `VIOS_USUARIO`/`VIOS_SENHA`; (2) `status` e
  `fila` antes da 1ª rodada davam "unable to open database file": o `Estado` cria a pasta `dados/`.
- `pje-busca/.env.example`: `VIOS_USUARIO`, `VIOS_SENHA`, `VIGIA_VIOS_AREA_ID=3`, `VIGIA_VIOS_TIPO_PARTE=P`,
  `VIGIA_VIOS_ADVOGADO_ID`, `VIGIA_MAX_CNPJ=40`. `PROJETO (1).md` seção 4.2 com o status e os comandos.

### Adicionado — pje-busca: plano do vigia diário VIOS → PJe (19 e 23/11/2026)
- `pje-busca/PROJETO (1).md`, seção 4.2 (só planejamento, sem código): 1x por dia o robô lê no VIOS a lista de
  processos trabalhistas em que o cliente é a parte passiva (só leitura), compara com a foto anterior, detecta
  empresas e processos novos e põe os números do TRT7 numa fila de verificação periódica no PJe, com leitura
  incremental da linha do tempo. Fluxo, configuração prevista, comandos, indicadores (janela de exposição: 112 dias
  no caso real), riscos e pendências.
- 23/11/2026, filtros e volume conferidos no VIOS (só contagens): Área 3 = Trabalhista + `pesq[tipos_partes_id]=P`
  + ativos = 363 processos, 161 clientes, 239 no TRT7; sem filtro de advogado (dois advogados principais); a lista
  do VIOS para em 500 linhas (dividir a pesquisa se chegar a 500).

### Corrigido — Albi: aviso "Pesquisa Duplicada" do Sonar (23/11/2026)
- Quando o CPF/CNPJ já tinha sido pesquisado no Sonar (por qualquer usuário), o Sonar abre, depois do **Continuar**,
  o aviso "Pesquisa Duplicada · ... já foram pesquisados no pedido N em DD/MM/AAAA ... Deseja realizar a pesquisa
  novamente?" (`.p-confirm-dialog`, botões Cancelar/Confirmar). O Albi esperava ir direto ao passo 2 e dava erro.
- `albi/main.py`: `aviso_duplicada()` e `confirmar_duplicada()`; `preencher_pedido()` espera o passo 2 **ou** o aviso,
  clica só no botão de texto exato "Confirmar" (nunca "Confirmar Pedido") e segue. Anota no log o pedido anterior e a
  data; `preencher_pedido()` devolve também `duplicada` ({pedido, data} ou None). A compra continua só com `--confirmar`.
- Teste real (CPF 753.340.971-04, aviso do pedido 1512114 de 17/11/2026): aviso confirmado, passo 2 com o documento
  certo, Sacado do escritório e "Confirmar Pedido" ligado (R$ 15,70), sem comprar. `albi/README.md` atualizado.

### Corrigido — Orelha: contagem por responsável e painel semanal com todas as tarefas (23/11/2026)
- **Contagem por pessoa**: tarefa com mais de um responsável contava só para o primeiro nome
  (`responsavel_principal`). Agora conta para cada um (`prazos.responsaveis`) no quadro "Atrasadas por
  responsável" (`funcoes/prazos.py`), na página da semana (`nucleo/semana.py`) e na carga do painel. O total
  de atrasadas continua contando cada tarefa uma vez. Na leitura de 23/11/2026, 26 de 250 atrasadas dos
  últimos 30 dias tinham 2 ou mais responsáveis.
- **Painel semanal**: a fila só pegava tarefas que começam com "MINUTAR" ou "AUDIÊNCIA". Agora entram todos
  os tipos; os outros viram a categoria "Outras" (coluna nova na carga, "Carga por responsável").
  `ORELHA_PAINEL_OUTRAS=nao` volta ao comportamento antigo. O registro da semana guarda `"tipos"` e só compara
  com registro do mesmo conjunto: a 1ª edição com todos os tipos sai sem comparação.
- Conferido no VIOS (só leitura): a lista de tarefas que o Orelha lê não filtra responsável nem tipo
  (o filtro de responsáveis vem vazio = todos). O responsável desmarcado visto na tela era do navegador de
  quem conferiu, não do bot.

### Corrigido — Albi: arquivo já confirmado pode ser pesquisado de novo pela página (23/11/2026)
- Depois que a trava de pedido repetido passou de 30 dias para 1, a tela de um arquivo já confirmado
  continuava sem botão de pesquisa/confirmar ("Este arquivo já foi confirmado"): essa é uma trava do
  arquivo, separada da trava de 1 dia, e só saía soltando o .txt outra vez.
- Novo botão **Conferir de novo** nessa tela (`POST /albi/de-novo/<id>`, `albi.conferir_de_novo` em
  `bot/albi.py`): confere o mesmo .txt de novo (novo id). Quem foi pesquisado há menos de 1 dia continua
  "já pesquisado"; os outros voltam a "Vai pesquisar". A compra continua pedindo os dois cliques.

### Adicionado — `servidor_mac.sh` cuida também do bot de WhatsApp e do coletor (18/11/2026)
- Novos comandos: `whatsapp instalar|status|atualizar|log|desinstalar` (chama `scripts/mac/` do repositório privado
  `bot-previdenciario`, pasta em `BOT_WHATSAPP_PASTA`), `coletor ...` (= `consulta/servico_mac.sh`), `tudo` (status dos
  três serviços) e `atualizar-tudo` (bot primeiro, depois `git pull` e reinício da página e do coletor).
- `.env.example`: `BOT_WHATSAPP_PASTA`. DOCUMENTACAO, Passo 22. O código do bot continua no repositório dele.

### Adicionado — Consulta: campo `atualizacao` por processo (18/11/2026, commit 216574f)
- O coletor manda `atualizacao: true` quando a ficha tem tarefa aberta (não concluída e não cancelada), a linha que o
  VIOS pinta de amarelo; só o booleano, nenhum dado da tarefa (`consulta/fases.py`, `montagem.py`, `coletor.py`,
  `CONTRATO.md`, testes). Atualizar o bot (bot-previdenciario 0cd0e23) **antes** do coletor.
### Corrigido — pje-busca: leitura das movimentações na página de detalhes do TRT7 (19/11/2026)
- Aba de detalhes ignorada: o filtro de id de aba (2**29) descartava a aba do PJe (ids do Chrome passam de 1 bilhão). Agora `_aba_detalhes()` acha a aba do número e fecha a aba ao terminar (`src/chrome_mac.py`: `fechar_aba`); limite corrigido também em `src/acesso_pje.py`.
- Texto do PDF: o visualizador do PJe não expõe `PDFViewerApplication`; o bot lê a camada de texto (`.textLayer`), rola página a página e ordena os trechos pela posição na folha. Traz a aba para frente (aba oculta não desenha o PDF).
- PDF digitalizado sai marcado como sem camada de texto (precisa de OCR); documento em HTML é lido pelo painel.

### Alterado — Envio automático mostra o andamento do lote da IA (18/11/2026)
- Antes, enquanto o lote da IA não terminava, a página do Sam ficava só em "A IA está analisando", sem sinal de vida,
  e a espera ia até `LLM_LOTE_ESPERA_MIN` (360 min por padrão).
- `bot/analise.py`: `progresso_lote` recebe o andamento do lote (status, prontas, com erro, minutos de espera).
- `bot/envio_auto.py` liga esse andamento em `detalhe`; `bot/templates/envio.html` mostra o texto ao lado de "A IA está analisando".
- Para não esperar 6 h, baixe `LLM_LOTE_ESPERA_MIN` no `.env` (ex.: 60). Se estourar, o lote é cancelado e o resto vai uma a uma.

### Corrigido — Albi roda o Sonar em segundo plano, sem janela (18/11/2026)
- `albi/main.py`: o Chrome do Sonar sempre sem janela (`--headless=new`). Antes ele abria uma janela nova, sem login no Google,
  e tirava o foco e o mouse do bot do PJe (`pje-busca`), que usa o Chrome logado. O `HEADLESS` do `albi/.env` deixou de valer.
- Continua: o `presto.py` (AppleScript no Chrome logado) ainda usa o Chrome do escritório; não rode os dois ao mesmo tempo.

### Adicionado — pje-busca: login no PJe do TRT7 pelo Presto (18/11/2026)
- `pje-busca/src/acesso_pje.py`: `entrar_trt7()` passa pelo console do Presto (login com `PRESTO_EMAIL`/`PRESTO_SENHA`, Sites > "Pje TRT 07 1g") e depois entra no PJe do TRT7 pelo Presto, no Chrome aberto do Mac
  (AppleScript), reaproveitando o login do Albi (`albi/presto.py`, função `login`). Para com "captcha" e não tenta resolver.
- `pje-busca/src/chrome_mac.py`: cópia do `albi/chrome_mac.py` (só biblioteca padrão), para o projeto não depender do Albi.
- `pje-busca/.env.example`: `PRESTO_CREDENCIAL` e `PRESTO_PIN` (sem valores).
- Decisão: AppleScript em vez de Selenium, como no Albi (o perfil copiado pede confirmação da conta Google).
- Corrigido: o botão "Login via Presto" do TRT7 é procurado por até 20 s (a página pode demorar a mostrar), e cada decisão é impressa.
- `pje-busca/testar_processos.py`: depois do login, abre o acervo geral do PJe (usuário externo), digita o número de cada processo no campo de consulta, aperta Enter, clica de mouse no ícone KZ da linha do número (os detalhes abrem em aba nova, e o script segue nela) e salva as capturas da página de detalhes (`/pjekz/processo/<id>/detalhe`) em `logs/processos/`.
- `pje-busca/testar_processos.py`: na página de detalhes, abre o documento de cada movimentação da linha do tempo, lê o texto de todas as páginas pelo visualizador do PJe (pdf.js) e grava `saida/<número>.txt` com a tabela de movimentações e o texto de cada uma.
- Ainda não testado no Mac com o TRT7 real; falta a busca por CNPJ (pendência 3.1 do `PROJETO (1).md`).

### Corrigido — envio automático órfão depois de reiniciar o servidor (18/11/2026)
- `bot/envio_auto.py` (`andamento()`): se `saida/automatico_execucao.json` diz "rodando" mas o servidor não tem
  thread dessa execução (reiniciou no meio), marca como "parou" com o motivo "servidor reiniciado durante a execução"
  e regrava o arquivo. Antes o botão "Enviar automaticamente" ficava desativado para sempre.
- Os lotes da IA (`lote_analise_*.json`) não são tocados: uma nova execução com o mesmo modelo e as mesmas CIs ainda retoma o lote.

### Alterado — Skill de análise de intimações atualizada (pacote da Controladoria, 18/11/2026)
- `doc/analise-intimacoes-controladoria/` (skill do projeto, lida pelo bot via `SKILL_PASTA`) trocada pelo pacote
  `analise-intimacoes-controladoria-atualizada-2026-11-18.zip`. Cópia guardada em `doc/skill-original/9_2026-11-18_atualizada/`
  e registrada como versão 9 em `doc/skill-original/LEIAME.md`.
- Saiu a antecipação da `DATA` por feriado (versão 8). Perícia médica sem filial não bloqueia mais a tarefa. CARL vai para JOHN, exceto CALTECH.
- `doc/skill-unica/` regenerado (`gerar_skill_unica.py`).

### Alterado — código alinhado à skill de 18/11/2026 (18/11/2026)
- Feriado: a `DATA` da tarefa não é mais antecipada por feriado (`bot/analise.py`, `bot/lancamento.py`). Saíram `prazos.antecipar()`, `feriado_aplicavel()`, `locais_escritorio()` e o `ESCRITORIO_LOCAIS` do `.env.example`.
- Perícia médica sem filial mapeada na análise: a tarefa vai com `incluir responsável pela cidade identificada` e não bloqueia. A filial vem só do teor da intimação, não mais da cidade do CSV (`bot/responsaveis.py`).
- Envio (página do TXT): aceita o texto `incluir responsável pela cidade identificada` na perícia médica (`bot/envio_txt.py`).
- CARL vai para JOHNYS em qualquer área; cliente CALTECH fica com Carlos (`bot/responsaveis.py`).
- No lançamento, a perícia médica continua conferida pelo "Escritório atual" do VIOS; sem filial ali, a tarefa não é lançada (decisão do código: o bot não consegue identificar a cidade sozinho).
- Testes atualizados (`tests/test_responsaveis.py`): 38 OK.

### Corrigido — Sam relê o `.env` a cada envio: senha do VIOS trocada vale sem reiniciar (17/11/2026)
- No Mac, depois de trocar a senha do VIOS no `.env`, o Sam continuava dando "senha incorreta". O servidor da página
  (`bot/envio_web.py`, ligado sem parar pelo `servidor_mac.sh`) lia o `.env` uma vez só, ao ligar, e usava a senha
  antiga em todo envio até ser reiniciado.
- Agora o envio manual (`_rodar`) e o envio automático (`/automatico/rodar`) chamam `config.carregar()` de novo antes de
  entrar no VIOS. Se o `.env` estiver incompleto, o envio automático nem começa e a página mostra o erro.
- `ENVIO_SENHA`, `ENVIO_REDE`, `SISTEMA_URL`, `SAIDA_PASTA` e as pastas dos outros bots continuam lidos só ao ligar.

### Removido — Zips repetidos da skill e caches do Python (17/11/2026)
- Saíram os `analise-intimacoes-controladoria.zip` de `doc/skill-original/1_…` a `8_…`: cada um era idêntico à pasta
  `analise-intimacoes-controladoria/` extraída ao lado, que continua (conferido arquivo a arquivo).
- Saiu `doc/analise-intimacoes-controladoria.zip`, idêntico ao zip da versão 7 (`doc/skill-original/7_2026-11-10_txt-bot-duplicadas/`).
- Saiu `doc/analise-intimacoes-controladoria(1).zip` (fora do Git), versão intermediária de 11/11 substituída pela versão 8.
- Saíram as pastas `__pycache__/` do projeto (o Python recria sozinho).
- Ficou tudo que o código usa: `doc/skill-unica/analise-intimacoes-controladoria.zip` (gerado por `gerar_skill_unica.py`),
  `doc/mascote/`, timbrados, fixtures, `saida/`, `orelha/saida/` e logs.

### Segurança — Limpeza de arquivos de teste e `.gitignore` dos resultados do Albi e do Jarvis (17/11/2026)
- `albi/resultado/` e `jarvis/resultado/` entraram no `.gitignore`. Estavam fora dele, neste repositório público, com
  arquivos de teste que tinham CPF, nome de cliente e relatório de cliente.
- Arquivos de teste e prints soltos foram para a lixeira (fora do Git, nada versionado foi apagado): `brag-output/`,
  `orelha/saida/simulado-*`, `albi/resultado/`, `jarvis/resultado/`, os prints de `logs/*.png` e `albi/logs/*.png`,
  as imagens soltas na raiz de `doc/` (Screenshot e WhatsApp) e a cópia duplicada
  `albi/mascote/zangao-transforma_att (1).html`.
- Ficaram os arquivos que o código usa: timbrados do Jarvis e da Orelha, `logs/bot.log` (lido por `jarvis/gastos.py`),
  `saida/` do Sam, relatórios reais da Orelha em `orelha/saida/<data>/` e o modelo do painel.

### Adicionado — Pasta `bot-previdenciario/` (bot do WhatsApp) dentro do projeto (16/11/2026)
- O bot do WhatsApp do setor previdenciário (e a mídia da Vila 06, Mikasa) fica em `bot-previdenciario/`, ao lado dos outros bots
  (`albi/`, `jarvis/`, `orelha/`, `autobots/`). É um clone de `joaotabosa3599/bot-previdenciario`, repositório **privado**,
  versionado à parte: a pasta está no `.gitignore` e **nunca** entra neste repositório, que é público. Clone uma vez com
  `git clone https://github.com/joaotabosa3599/bot-previdenciario.git bot-previdenciario` e atualize com `git pull` dentro dela.
  Instalação no Mac: `bash bot-previdenciario/scripts/mac/instalar.sh`.

### Adicionado — Sam: segunda checagem da perícia pelo "Escritório atual" do processo (17/11/2026)
- A tarefa `PERÍCIA MÉDICA JUDICIAL (PREVIDENCIÁRIO) 2026` saía com a filial de Sobral por padrão (a cidade vinha do teor
  da intimação) e era direcionada para a pessoa errada. Agora, na hora de lançar (`lancamento.conferir_pericia()`), o robô
  abre a tela Lançar Intimação da CI, segue o link do martelo ("Visualizar processo") e lê o campo **Escritório atual** da
  ficha do processo (`lancamento.ler_escritorio()`, só leitura). O responsável passa a ser o da filial desse escritório
  (`responsaveis.da_pericia_pelo_escritorio()`); o bloqueio de filial da análise é refeito com essa informação.
- Escritório sem filial conhecida (Camocim, Tianguá, Jijoca, Sobral) ou campo não encontrado: a CI não é lançada e o motivo
  mostra o escritório lido. Vale para todos os caminhos que lançam (envio automático, página de envio e `lancar.py`), também
  no modo teste. CI sem perícia médica não abre a ficha.
- Testes em `tests/test_responsaveis.py`.

### Adicionado — `consulta/servico_mac.sh`: coletor sempre ligado no Mac pelo launchd (16/11/2026)
- `instalar` põe as dependências de `consulta/requirements.txt` na `.venv` da Orelha, confere o `consulta/.env`
  (campos obrigatórios, certificado do bot, chave privada com permissão 600) e liga o coletor com `KeepAlive`
  (sobe no login, reinicia se cair). Também `status`, `log` e `parar`.

### Adicionado — Coletor confia no certificado próprio do bot no Mac (`CONSULTA_CERTIFICADO`) (16/11/2026)
- No Mac do escritório o bot roda com HTTPS de certificado próprio (RN22 do bot). Com `CONSULTA_CERTIFICADO`
  apontando para `dados/certificado/certificado.pem` do bot, o coletor valida a conexão só contra esse
  certificado (`CONSULTA_BOT_URL=https://localhost:3000`). Vazio: validação padrão (bot com certificado público).

### Adicionado — Coletor da consulta de processo pelo WhatsApp, pasta `consulta/` (16/11/2026)
- Robô Python que lê o VIOS só por leitura (reaproveita `orelha/nucleo` e a leitura da tabela de tarefas da
  ficha) e responde aos pedidos do bot de WhatsApp: busca pedidos (`GET /consulta/pendentes`, assinado com
  HMAC), decifra o CPF (RSA-OAEP SHA-256), acha processos e telefones do cadastro, calcula a fase e devolve
  só a ficha mínima por lista branca (`POST /consulta/resultado`); telefones só como HMAC. Especificação em
  `consulta/CONTRATO.md`; uso em `consulta/README.md`. `python -m consulta [--uma-vez] [--simulado]`.
- `consulta/fases_vios.yaml`: mapa tipo de tarefa -> fase para TODAS as áreas (551 tipos de
  `consulta/tipos-todos.txt`; `tipos-previdenciario.txt` guarda o catálogo do previdenciário); tipo fora do
  mapa vira `desconhecida` e o bot encaminha para a equipe.
- Testes `unittest` em `consulta/tests/` (fixtures fictícias em `consulta/fixtures/`), incluindo log sem CPF,
  telefone, nome ou CI. Dependências novas (`consulta/requirements.txt`): `cryptography`, `PyYAML`.
- Configuração: `consulta/.env` (modelo `consulta/.env.example`), incluindo `ORELHA_PARADOS_LIBERAR_XHR=auto`
  (a tabela de tarefas da ficha carrega por XHR POST; sem isso vem vazia).
- Corrigido ao fechar a sessão: o leitor é fechado antes do Chrome (evita o traceback de conexão recusada).

### Alterado — Albi: trava de pedido repetido passa de 30 dias para 1 dia (16/11/2026)
- `DIAS_REPETIDO` em `albi/main.py` agora é 1: CPF + empresa só são bloqueados (usa o pedido anterior)
  se foram pesquisados nas últimas 24 h; depois disso o Albi compra de novo. Textos atualizados em
  `albi/README.md`, `DOCUMENTACAO.md` e `bot/templates/albi.html`.

### Adicionado — Vila 06: a muralha do bot do Previdenciário (13/11/2026)
- Aba **06 · Mikasa** na Vila dos Bots (`doc/vila/ligar_vila06_muralha.py`), com a cena `bot/vila/muralha.html` em
  `/vila/previdenciario`: vídeos de plantão (dia), fora do expediente (noite) e um clipe por evento do bot (respondida /
  passada para a equipe / não entendida), com os contadores do dia.
- `bot/vila06.py` + rota `/vila/previdenciario/estado`: o servidor da vila consulta o bot (`VILA06_URL`, `VILA06_TOKEN`,
  `VILA06_CERTIFICADO`) e repassa só contagens e eventos sem dado pessoal; sem configuração, simulação.
- Vídeos fora do git (`VILA06_CLIPES`, padrão `<SAIDA_PASTA>/vila06_clipes`), servidos só pelos 5 nomes da lista.
- Caixa de diálogo da Mikasa (estilo RPG) com uma fala por evento; retratos `retrato-<expressão>.png` na mesma pasta, fora do git.
- Testes: `tests/test_vila06.py`.

### Adicionado — Vila 06: som (voz da Mikasa, música, ambiente e efeitos) (16/11/2026)
- A Mikasa fala em voz alta cada frase da caixa de diálogo (`sons/fala-<hash>.mp3`; a música abaixa enquanto ela fala).
- Música de fundo original em laço (com fusão), vento da muralha e efeitos sincronizados com os vídeos: sino e passo do
  titã na chegada; gás, gancho, cortes de lâmina, vapor, esquiva e pouso na resposta; canhão e sino ao passar para a equipe.
- Botão **Som** na placa (o navegador só deixa tocar depois de um clique; a escolha fica salva no navegador).
- `doc/vila/gerar_sons_vila06.py` gera tudo na ElevenLabs (chave só por variável de ambiente); arquivos em
  `<VILA06_CLIPES>/sons/`, fora do git, servidos só pelos nomes da lista (`/vila/previdenciario/sons/<nome>.mp3`).
- Falas sem número (as contagens ficam no painel), para a voz gravada valer sempre; subtítulo da placa: bot da recepção.

### Adicionado — Regras da skill de 13/11/2026 no robô: responsáveis, filial da perícia e feriado na DATA (13/11/2026)
- **Responsáveis na análise pela API** (`bot/responsaveis.py`): a sigla do auxiliar (SUH, TAMI, JOHN, JOAN...) vira o nome completo
  pela lista do VIOS (`saida/responsaveis.json`); sem auxiliar, o advogado responsável do processo. Sigla ambígua (CARL) não é
  adivinhada; Carlos só no Trabalhista vai para o Johnys, como antes. A petição da Execução da Tamira leva também o Breno.
  Com isso o **Envio automático volta a lançar** (as tarefas não saem mais sem responsável).
- **Exceção Ronielle:** sem auxiliar e com RONIELLE FEITOSA (RONEELY FEITOSA no VIOS) como responsável, a tarefa é bloqueada com a
  mensagem da skill; no `.txt`, o arquivo que traz só ele como responsável é barrado.
- **Perícia médica judicial previdenciária:** responsável da filial (Camocim, Tianguá, Jijoca, Sobral), nunca Amanda nem Suhiane;
  cidade pelo teor (senão pela comarca); nenhuma ou mais de uma filial = `NÃO LANÇAR — CONFIRMAR FILIAL/RESPONSÁVEL...`. No `.txt`,
  só aceita o responsável da filial.
- **Feriado na `DATA`:** `prazos.antecipar()` recua a `DATA` da tarefa (D-2, prioridades, mesmo dia, dia seguinte) para o dia de trabalho
  anterior quando cai em feriado nacional, ou do local de `ESCRITORIO_LOCAIS` (novo no `.env`; vazio = só nacionais). Só a `DATA`:
  D-2 e vencimentos da descrição não mudam; ato com hora fixa e data informada não recuam; nunca volta antes de hoje (alerta de
  urgência). Vale na análise e depois do corte das 12h, no lançamento. Exemplo da skill: 02/11 vai para 30/10.
- Testes: `tests/test_responsaveis.py` (18 casos). Conferido em análise real de 09/11 (sem chamar a IA): 38 de 39 tarefas com
  responsável; 1 CI bloqueada pela regra do Ronielle; 20/11 (Consciência Negra) recuou para 19/11.
- `DOCUMENTACAO.md` (Passo 41 e tabela do `.env`), `.env.example` e a skill única atualizados.

### Adicionado — Trava de responsável: nada de `automático` nem Amanda (13/11/2026)
- Pela skill de 13/11/2026, o VIOS manda a tarefa de `RESPONSÁVEIS: automático` para AMANDA LEITE MENDES, que só lança.
  Agora a CI é barrada quando algum responsável está em branco, é `automático` ou é a Amanda:
  - página de envio de .txt (`bot/envio_txt.py`): vira "problema" na conferência (não vai ao VIOS); o campo Responsáveis da
    edição não vem mais preenchido com "automático" e o formato de exemplo mostra o nome do auxiliar;
  - lançamento (`bot/lancamento.py`, `responsavel_proibido()`): CI fica "bloqueada" com o motivo, também no `lancar.py` e no
    Envio automático (`/automatico` mostra o motivo).
- **Efeito no Envio automático:** a análise pela API deixava os responsáveis vazios; resolvido logo em seguida (item abaixo).
- Skill única (`regras-do-programa.md`) e `DOCUMENTACAO.md` (Passo 41) atualizados.

### Alterado — Skill da Controladoria de 13/11/2026 (responsáveis, feriado e marco pela publicação)
- Pacote `analise-intimacoes-controladoria-atualizada-2026-11-13.zip` vira a skill do projeto
  (`doc/analise-intimacoes-controladoria/`); versão guardada em `doc/skill-original/8_2026-11-13_responsaveis-feriado/`
  (explicada no `LEIAME.md`) e skill única regerada (`gerar_skill_unica.py`).
- Mudanças de regra: **nunca `automático`** em `RESPONSÁVEIS` (vai para AMANDA LEITE MENDES): auxiliar, senão o advogado
  responsável, exceto RONIELLE FEITOSA sem auxiliar (não lança); perícia médica judicial previdenciária com o responsável
  da filial (Camocim, Tianguá, Jijoca, Sobral); `DATA` antecipada para o dia de trabalho anterior quando cair em feriado
  nacional ou da filial (D-2 e vencimento não mudam; audiência/perícia/sustentação ficam na data real); marco pela
  publicação do DJEN/CSV, inclusive Fazenda Pública; `CIÊNCIA (CÍVEL)` vale para Criminal; novas equivalências de clientes.
- O pacote já trazia o campo `PROCESSO` do TXT (alterações que estavam pendentes na pasta da skill).
- `doc/skill-unica/arquivo-para-o-robo.md` e `regras-do-programa.md`: exemplos e regra de `RESPONSÁVEIS` sem `automático`.
- A análise pela API (`./rodar_analise.sh` e o Envio automático) já lê a skill nova no prompt. **O código aplica essas regras:** ver o item seguinte; ver a lista no passo 41 do `DOCUMENTACAO.md`.

### Adicionado — Envio automático em um clique na página do Sam, com animação (13/11/2026)
- Na `/sam`, cartão **Envio automático em um clique**: botão **▶ Enviar automaticamente** e **Ensaio (não grava)**.
  Os dois perguntam **"Você tem certeza?"** antes de ativar o Sam; o servidor também exige a confirmação e
  recusa pedido de outro site (`POST /automatico/rodar`).
- O Sam faz o fluxo inteiro sozinho: captura as intimações de ontem sem tarefa, analisa com a IA e lança as tarefas
  no VIOS CI por CI, com as mesmas travas e a mesma Conferência do envio de .txt. No ensaio para no quadro de
  tarefas (não grava). Sem intimação nova, termina sem chamar a IA. Uma execução por vez (mesma trava dos envios).
- Animações: o cartão mostra 4 passos (Capturar, Analisar, Criar tarefas, Conferir), barra e números ao vivo;
  a Fortaleza do Dragão ganhou os momentos de captura e análise (eventos `automatico`, fases `capturando` e
  `analisando`) e segue com o dragão acordando e a vida da Torre VIOS caindo a cada tarefa criada.
- Novos: `bot/envio_auto.py`, rotas `POST /automatico/rodar` e `GET /automatico/andamento`, andamento em
  `saida/automatico_execucao.json`. `main.py` ganhou a função `capturar()` (a captura que o `main` já fazia, sem mudar o
  comportamento). Contrato de eventos e `DOCUMENTACAO.md` (Passo 40) atualizados.
- Testado com a captura, a IA e o lançamento simulados (eventos, contagens e travas) e as rotas (recusas de
  segurança); **ainda não rodado de verdade no VIOS**: fazer primeiro um Ensaio.

### Adicionado — Roteiro do motion do Sam: fluxo do modo automático (13/11/2026)
- `doc/motion-sam/roteiro-motion-sam.md`: briefing para um profissional de motion criar o vídeo do Sam.
  Traz os personagens (Fortaleza do Dragão), o fluxo em 7 cenas (captura, análise da IA, travas de
  segurança, lançamento, conferência e relatório `/automatico`), textos de tela, números de exemplo e o que
  ainda falta confirmar (horário do disparo automático). Só documentação; o código não mudou.

### Adicionado — Albi: pesquisa digitada na página, sem precisar de .txt (13/11/2026)
- Na `/albi`, abaixo da caixa de soltar o arquivo, o cartão **Pesquisa digitada**: empresa (com sugestão dos
  clientes já cadastrados), CPF/CNPJ e nome, com "+ Adicionar outra pessoa" e "Tirar" para mais de uma. Serve
  para uma pesquisa única ou poucas.
- Vai pelo mesmo caminho do arquivo: a página monta o texto no mesmo formato (`EMPRESA: X` e `CPF ; nome`),
  guarda como `digitado-AAAA-MM-DD_HHMM.txt` e abre a conferência (CPF/CNPJ válidos, já pesquisados e total em
  R$) antes de qualquer compra. O pedido aparece normalmente no bloco do cliente e nas mensagens por dia.
- `bot/albi.py`: `texto_digitado()` (exige empresa, CPF/CNPJ e nome; tira quebras de linha e ";" para um campo
  não virar outra linha; máximo de pessoas igual ao do arquivo); `bot/envio_web.py`: rota `POST /albi/digitar`.
  O botão fica desligado enquanto o Albi está trabalhando, como a caixa de soltar.

### Adicionado — Albi: blocos de clientes e tela de cada cliente com os pedidos e as mensagens (12/11/2026)
- Na `/albi`, abaixo da caixa "Solte o .txt", um bloco por cliente (empresa) que pediu pesquisa: nome,
  quantos pedidos e pessoas, quantas mensagens com e sem processos e a data do último pedido, com busca por
  nome. O botão do topo agora é "← Voltar à Vila".
- Clicar no cliente abre `/albi/cliente?empresa=NOME`: cada **pedido** dele (um arquivo enviado, ex.: 25 CPFs
  hoje e outros 25 na semana seguinte) em ordem da data mais recente, com o resultado de cada pessoa
  (com processos, não consta, erro), os links do relatório/PDF/.zip e a mensagem da análise (com o parágrafo do
  Gemini) pronta para copiar, com a escolha da atendente. Pedido sem mensagens ainda tem o botão "Gerar as
  mensagens deste pedido".
- `bot/albi.py`: `clientes()` agrupa as execuções por empresa; `bot/envio_web.py`: rota `albi_cliente`.

### Adicionado — Albi: tela "Mensagens" com as mensagens da CAC por dia (12/11/2026)
- Nova tela `/albi/mensagens` (botão "Mensagens" no topo da página do Albi): o produto final, as mensagens
  prontas para copiar e enviar ao cliente, **de um dia** (`?dia=AAAA-MM-DD`; sem ele, hoje ou o dia mais
  recente com mensagens). Escolha o dia no calendário ou nos botões "Dias com mensagens" (data · quantidade).
- Mostra o total do dia, quantas têm processos e quantas não, filtro "Todas / Com processos / Sem processos",
  busca por nome ou empresa, mensagens agrupadas por empresa, escolha da atendente (troca o nome no começo de
  todas), "Copiar mensagem" em cada uma e "Copiar todas as que estão na tela". Mensagens com processos vêm
  recolhidas ("Ver e editar a mensagem"); as de "nenhum processo" já vêm abertas.
- Não precisa mais clicar em "Capturar resumo": o relatório (e as mensagens) já são gerados no fim de cada
  execução. Quem foi pesquisado de novo no mesmo dia fica com a mensagem da execução mais recente.
- `bot/albi.py`: `mensagens_por_dia()`; `bot/envio_web.py`: rota `albi_mensagens`; o card da execução ganhou
  o botão "Ver as mensagens para copiar".

### Alterado — Albi: página no tema da Arena (Dragon Ball Z) (12/11/2026)
- A página `/albi` (`bot/templates/albi.html`, `<body class="tema-arena">`) deixa o fundo escuro e rosa e
  passa a usar o tema da vila 03 (Arena do Albi, `albi/mascote/fundo-arena-albi.html`): céu em degradê, nuvens
  de pixel passando devagar, faixa de lago embaixo, cabeçalho bege com telhado laranja (a casa em domo),
  cartões bege com moldura de madeira, botões laranja, barra de andamento em ki ciano e o rosa do Albi na
  marca (fonte Silkscreen). O quadro da vila ganhou moldura de madeira/bege/laranja. Nuvens somem no celular
  e o `prefers-reduced-motion` continua parando as animações.
- Tela "Mensagens prontas": o texto de ajuda e o título ("uma por pessoa pesquisada") agora descrevem o
  formato fixo, a mensagem de "nenhum processo" e o parágrafo do Gemini; quem não tem processo mostra
  "sem processos" em vez de "0 processo(s)".

### Adicionado — Albi: parágrafo explicativo de cada processo escrito pelo Gemini (12/11/2026)
- `explicacao_ia.paragrafo(classe, posição, situação)`: o Gemini escreve 2 a 4 frases explicando o tipo de
  ação, o que significa a posição da pessoa (ex.: réu não é condenação) e o que significa a situação. Só
  esses três dados são enviados (nunca nome, CPF ou número). Cada combinação é gerada uma vez e guardada
  em `explicacoes_classe.json` (chave `P|…`). O prompt proíbe inventar fatos e dizer que alguém ganhou,
  perdeu, pagou ou foi condenado; respostas com essas palavras, com markdown ou cortadas são descartadas.
  O parágrafo entra no lugar da explicação fixa; sem chave ou com erro, volta a explicação fixa.

### Corrigido — Albi: Gemini e português da mensagem, testados com um relatório real (12/11/2026)
- `explicacao_ia.py`: o modelo padrão `gemini-2.5-flash` foi aposentado pelo Google. Agora usa
  `gemini-flash-latest` e, se estiver sobrecarregado (503), tenta `gemini-3.5-flash` e
  `gemini-3.1-flash-lite`. Respostas cortadas ou fora do formato (frase curta começando em minúscula)
  não são aceitas nem guardadas no cache; o limite de tokens subiu para 1024.
- `mensagem_cac.py`: "Estado do Ceará / da Bahia / de Sergipe" (antes era sempre "de"), plural quando há
  mais de uma parte do outro lado ("figuram como reclamados") e mais palavras com acento (provisório,
  decisão, consórcio…).

### Adicionado — Albi: explicação de tipos de ação novos pelo Gemini (12/11/2026)
- `albi/explicacao_ia.py`: para a classe processual que não está no dicionário fixo, pede ao Gemini
  (chave gratuita, `GEMINI_API_KEY` no `albi/.env`) uma frase simples para "Esse tipo de processo é…".
  Só o nome da classe é enviado (nunca nome, CPF, número ou partes). A resposta fica em
  `albi/explicacoes_classe.json` (uma chamada por classe, texto igual em todas as mensagens, editável).
  Sem chave, sem internet ou com erro, a mensagem sai sem esse parágrafo. Novas variáveis no
  `.env.example`: `GEMINI_API_KEY` e `GEMINI_MODEL`.

### Alterado — Albi: mensagem da CAC com formato fixo (12/11/2026)
- A atendente confirmou que todas as mensagens seguem o mesmo formato (com e sem processos). O texto
  agora é sempre igual e só mudam os campos: saíram os parágrafos opcionais (valor da causa, assunto,
  segredo de justiça, aviso de processo criminal, instância, observação do status) e a ressalva final,
  que não existem no modelo. Entraram o nome completo do tribunal ("Tribunal de Justiça do Estado de
  Sergipe (TJSE)"), "Comarca de X, Estado de Y", o papel da outra parte (requerido, executado…) e o aviso
  fixo de que *exequente não é quem está sendo cobrado*. A conclusão traz sempre a mesma frase sobre
  condenação.

### Alterado — Albi: novo modelo de mensagem da CAC, sem entrar em tribunal (12/11/2026)
- A mensagem passa a seguir o novo modelo do escritório: "*Beatriz Vasconcelos:* Informamos que, após
  consulta aos registros processuais disponibilizados, foram localizados *N processos judiciais*
  relacionados a *NOME*, CPF nº …, todos vinculados ao *TJ…*", período e área, quantos arquivados/em
  tramitação, um bloco por processo (partes, "*Processo nº … — TJ…*", posição da pessoa, o que a pesquisa
  não traz, andamento e "*Conclusão:*") e a ressalva final.
- Não consulta mais tribunal nem o DataJud: o texto usa só a planilha do Sonar (`mensagem_cac.gerar`
  ignora `datajud`; `datajud.py` fica só para consulta manual).

### Adicionado — Albi: mensagem para quem não tem processo (12/11/2026)
- Quem o Sonar respondeu "não consta" ganha a mensagem "Informamos que após consulta ao sistema do Poder
  Judiciário, não localizamos *nenhum processo* em nome de *NOME*." Pessoa com falha ao ler a planilha
  continua sem mensagem.

### Alterado — Skill da Controladoria pede o número do processo no TXT do robô (11/11/2026)
- A skill `doc/analise-intimacoes-controladoria/` proibia o número do processo no TXT, e os arquivos
  chegavam ao Sam sem ele. Agora cada bloco traz `PROCESSO:` logo abaixo de `CI:` (padrão
  0000000-00.0000.0.00.0000), no modelo (`assets/pedido-arquivo-robo.txt`, com o exemplo), em
  `references/saida-txt-bot.md` (sete campos) e no `SKILL.md`. O resto da skill não mudou. O Sam já lia
  esse campo e mostra o número na conferência.

### Corrigido — Histórico perdia o resultado do envio conferido de novo depois (11/11/2026)
- "Salvar e conferir" num envio já enviado apagava o resultado das CIs e o histórico mostrava
  "Conferido, não enviado" com "—" (caso de `analise_2026-11-10_complementar.txt`, que gravou 10 CIs
  às 16:56 de 10/11 e foi conferido de novo às 16:57). Agora o histórico e o `/sam` mostram o resultado
  do último envio (lido do `envio_fim` em `saida/eventos.jsonl`, `eventos.fins_por_envio`) com a nota
  "conferido de novo depois", e a página do envio avisa que ele já foi enviado. Vale para os envios
  antigos, sem mexer nos arquivos.

### Alterado — Fortaleza do Dragão também na Vila dos Bots (11/11/2026)
- Na página inicial (`/`) e em `/vila`, a aba **01 · Sam** mostra a Fortaleza do Dragão por cima da
  Vila 01 antiga; a barra de abas fica por cima e as abas 02 a 05 não mudam. Patch novo
  `doc/vila/ligar_vila01_fortaleza.py`, aplicado em `bot/vila/vila.html`.

### Alterado — Vila do Sam vira a Fortaleza do Dragão, no estilo Senhor dos Anéis (11/11/2026)
- Novo design (`doc/desing_sam/fortaleza-dragao.html`) instalado em `bot/vila/fortaleza.html`, servido
  em `/vila/sam` e mostrado no topo do `/sam` e da página de cada envio, no lugar da Vila 01.
- A cena do design era só simulação; agora assiste aos eventos reais do Sam (`/eventos`): a missão
  avança a cada etapa (TXT recebido, CIs conferidas, duplicatas, tarefas criadas n/N), o dragão desperta
  quando as tarefas começam a ser criadas, cada tarefa gravada tira vida dele, erro faz o dragão cuspir
  fogo e o fim mostra "Missão cumprida" com as contagens. Ao abrir, mostra o último envio.
  "Simular envio" virou "Demonstração" (desligada durante um envio real).
- Páginas do Sam no estilo da fortaleza (tema `tema-vila`): troca a grama da vila antiga por noite,
  pedra e dourado, com as fontes Lora e Silkscreen do design. O relatório do envio automático ganhou
  a moldura dourada.

### Adicionado — Relatório de conferência no Envio automático do Sam (11/11/2026)
- A tela `/automatico` virou o relatório de conferência, com foco nos prazos (`bot/conferencia.py`):
  números do dia, nota "como ler os prazos" (com os feriados nacionais que contaram como dia útil),
  visão geral por CI e um cartão por intimação com prazos, conta de cada prazo refeita por fora,
  tarefa da análise × tarefa gravada no VIOS, o que a IA entendeu, pendências, teor e pontos de
  atenção (não lançada com prazo próximo, tarefa em feriado ou depois do fatal, CIÊNCIA com prazo...).
- Filtro por **dia de envio** (dia em que as tarefas foram gravadas no VIOS), não mais pelo arquivo da
  análise; análise nunca enviada aparece como "não enviada". Filtros de lançadas, não lançadas e com
  atenção, busca e botão Imprimir / PDF.
- Página `/sam`: cartão **Envio automático** com o último envio e os outros dias.
- A conta refeita só vale para análise feita pela contagem simplificada: as de antes de 10/11/2026
  (calendário de feriados de cada tribunal) acusavam divergência falsa (ex.: 28/10 com "6/57") e agora
  ficam sem a conta, com o aviso na nota "como ler os prazos".

### Alterado — Páginas do Sam com as cores da vila (11/11/2026)
- `/sam`, histórico, envio e envio automático trocaram o fundo azul escuro pelas cores da vila 01:
  grama com tufos e flores, mata nas bordas, cabeçalho de mata com a estrada de terra, cartões escuros
  como as placas da vila e botão principal dourado (classe `tema-vila` em `_estilo.html`). As outras
  páginas não mudam.

### Corrigido — Lançamento bloqueia tarefa com data que já passou (11/11/2026)
- As datas D-2, dia seguinte e data informada vêm prontas da análise e não eram conferidas no
  lançamento: uma análise de um dia lançada em outro (ex.: `lancar.py` dias depois) gravava a tarefa
  numa data já passada, sem aviso. Agora `lancar()` (`bot/lancamento.py`, usado pelo `lancar.py` e
  pela página web) não lança a CI se alguma tarefa ficar antes de hoje: ela fica **bloqueada** com o
  motivo, para refazer a análise. O envio automático do Sam (análise e lançamento no mesmo dia) não muda.

### Corrigido — Nomes novos da tarefa de laudo previdenciário no VIOS (10/11/2026)
- O VIOS dividiu "MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026" (nome
  que a skill ainda usa) em duas. A análise troca sozinha: laudo -> "MINUTAR RÉPLICA/IMPUGNAÇÃO LAUDO
  (PREVIDENCIÁRIO) 2026"; outro ato (ex.: proposta de acordo do INSS) -> "MINUTAR PETIÇÃO INTERMEDIÁRIA
  (PREVIDENCIÁRIO)". No `.txt` do chat o nome antigo vira o de laudo (`APELIDOS` em `bot/lancamento.py`).
  Os dois nomes novos entram na lista oficial (`NOVAS_NO_VIOS` em `bot/skill.py`).
- 09/11/2026 fechado: as 5 CIs com esse nome e as 2 corrigidas para CIÊNCIA (EXECUÇÃO) (42825 e 42820,
  correção registrada no alerta da análise) foram lançadas — 28 de 38 no total; 10 ficam para a
  Controladoria por falta de informação que só o PJe tem.

### Alterado — Detector de duplicadas desligado (10/11/2026)
- A Controladoria já tira as duplicadas na tela de intimações do VIOS, e o detector marcava como
  cópia CIs que não eram. Novo `DUPLICIDADE_ATIVA` no `.env` (padrão `false`): desligado, nenhuma CI
  é cópia na captura, na análise, na página de revisão, no envio do `.txt` (sem ler o teor no VIOS
  antes de gravar) e no lançamento. Religar: `DUPLICIDADE_ATIVA=true`.

### Adicionado — Tela "Envio automático" na página do Sam (`/automatico`) (10/11/2026)
- Mostra, para cada dia analisado (`saida/analise_<dia>.json`), cada intimação em três colunas:
  **Intimação** (cliente, auxiliar, datas, teor) → **Análise** (ato, área, tarefas com data e
  descrição, alertas, modelo da IA) → **O que foi** (lançada, com as tarefas gravadas e o link
  "Ver no VIOS" para a Conferência; ou não lançada, com o motivo e o link "Lançar no VIOS").
- Resumo no topo (intimações, lançadas, não lançadas, gasto da IA), filtro Todas/Lançadas/Não
  lançadas, busca e escolha do dia. Botão "Envio automático" no topo da página de envio.
- `bot/lancamento.py` grava o resultado de cada CI em `saida/automatico_resultados.json` quando
  lança com `--confirmar` (gravada, bloqueada, duplicada, já no VIOS, conferência, erro com a mensagem).
  O dia 09/11/2026 foi preenchido a partir do log do lançamento.

### Corrigido — Primeira análise com o Haiku (09/11/2026, 38 intimações, US$ 0,12) (10/11/2026)
- A IA às vezes escreve a linha de prazo no resumo ("PRAZO FATAL D -2 PENDENTE DE CÁLCULO PELO
  PROGRAMA; ..."): o programa tira essas linhas, porque insere as suas com as datas calculadas.
- Auxiliar CARL em tarefa trabalhista: responsável vai para FRANCISCO JOHNYS VASCONCELOS BARBOSA
  (a skill diz que Carlos não está mais no Trabalhista), com alerta no relatório.
- O lote da Batch API ficou 7 min em 0 de 38; a análise foi refeita uma a uma (~18 s por intimação).
- Lançamento real (`--confirmar`) de 26 CIs: 21 tarefas gravadas e conferidas no VIOS; 5 não
  lançadas (42807, 42805, 42808, 42810, 42811) porque o VIOS trocou a tarefa
  "MINUTAR PETIÇÃO INTERMEDIÁRIA/RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026" por
  "MINUTAR RÉPLICA/IMPUGNAÇÃO LAUDO (PREVIDENCIÁRIO) 2026" e "MINUTAR PETIÇÃO INTERMEDIÁRIA
  (PREVIDENCIÁRIO)". CIs 42825 e 42820 ficaram para a Controladoria (o Haiku indicou análise; a
  skill pede CIÊNCIA para despacho que só manda aguardar).

### Alterado — Skill de 10/11/2026 instalada e análise pela API nas regras novas (10/11/2026)
- Skill nova da Controladoria em `doc/analise-intimacoes-controladoria/` (cópia em
  `doc/skill-original/7_2026-11-10_txt-bot-duplicadas/`).
- `bot/analise.py`: análise de sentença/acórdão/decisão sempre com `PRAZO PARA EMBARGOS:` e
  `PRAZO PARA RECURSO:` em D-2 (sem `NÃO CABE`, sem `PRAZO FATAL` junto); minutas com
  `PRAZO FATAL D -2:`; RPV no próximo dia útil com `PRAZO FATAL:` = D-2 do prazo; emenda da
  Suhiane no próximo dia útil com `PRAZO FATAL D -2:`. Sem linhas `PRIORIDADE ...` na descrição.
- Bloqueia (não lança) a análise sem prazo de embargos ou de recurso e a tarefa com prazo sem data.
- Instruções do modo automático (prompt) atualizadas para a contagem simplificada e os rótulos novos.
- `.env` deste computador: `LLM_MODELO=claude-haiku-5-5`, `LLM_MODELO_SIMPLES` e `LLM_MODELO_FERIADOS` vazios.

### Corrigido — Análise pela API com o Claude Haiku 5.5 (10/11/2026)
- A chamada uma a uma (`bot/ia/anthropic_ia.py`) pedia o fallback de recusa do servidor
  (`fallbacks: "default"`), que o Haiku 5.5 não tem. Com modelo Haiku o pedido vai sem esse campo;
  Opus e Sonnet continuam com o fallback.

### Alterado — Feriado passa a contar como dia útil nos prazos do código (10/11/2026)
- `bot/prazos.py` usa a contagem simplificada da skill (`PRAZO_CONTAGEM=simplificada`, padrão):
  só sábado e domingo ficam de fora; feriados, pontos facultativos, recesso (20/12 a 20/01) e
  suspensões contam como dia útil. Vale para prazo fatal, D-2 e próximo dia útil na análise pela
  API (`./rodar_analise.sh`) e nas datas refeitas na página de revisão.
- Conferido com o exemplo da skill: publicação 29/10/2026 + 5 dias = 05/11/2026, D-2 = 03/11/2026
  (o calendário antigo dava 06/11 por causa de Finados).
- No relatório, o calendário vira "Contagem solicitada: segunda a sexta, incluindo feriados;
  vencimentos sem validação do calendário judicial oficial." Sem lista de feriados considerados.
- Com a contagem simplificada, a pesquisa de feriados na internet não roda (sem gasto) e sai o
  alerta de feriado municipal não cadastrado.
- Voltar ao calendário antigo: `PRAZO_CONTAGEM=feriados` no `.env`.

### Adicionado — Jarvis: PDF do relatório no timbrado entra na main (10/11/2026)
- A branch `relatorio-processos` (PDF no papel timbrado, "Resumo do mês" pela IA, tipo de processo
  pela Área) foi juntada à `main`. Até aqui o PDF só existia nessa branch, e o Jarvis do Mac gerava só
  a planilha.
- Cada relatório gera `<GRUPO>.xlsx` + `<GRUPO>.pdf` (+ `.json`), e a página `/jarvis` lista os dois.
- O "Resumo do mês" (uma chamada à IA por grupo) entra no gasto do grupo na aba Metadados.
- No Mac: `cd jarvis && ./instalar.sh` uma vez, para instalar reportlab, pillow e chardet.

### Adicionado — Jarvis: gasto da IA por cliente (`gastos.py`) (10/11/2026)
- `cd jarvis && .venv/bin/python gastos.py [--mes AAAA-MM]` lê o `logs/bot.log` e mostra, por Grupo
  Cliente, os relatórios, os processos, o gasto e o gasto por processo, e depois cada relatório. Não
  entra no VIOS nem chama a IA, e serve para os relatórios antigos.
- O gasto do log é acumulado da execução: o script separa cada grupo pela diferença. Uma execução
  nova é reconhecida pela linha nova "Execução iniciada" ou por mais de 20 min sem processo.
- Corrigido: a aba Metadados mostrava em "Gasto estimado com IA" o acumulado da execução. Com vários
  grupos, o 2º somava o do 1º. Agora mostra o gasto daquele grupo (e o da execução, se não for o
  primeiro). O fim de cada grupo no log diz "gasto do grupo US$ X".

### Corrigido — Jarvis: `--grupos --salvar` com a linha PROCESSOS_GRUPOS repetida no `.env` (10/11/2026)
- Se o `jarvis/.env` tinha duas linhas `PROCESSOS_GRUPOS=`, os grupos iam para a primeira. A página
  `/jarvis` lê a última, e só os grupos antigos apareciam.
- Agora o `--salvar` deixa uma linha só, com a lista completa. Também regrava quando não há grupo novo
  mas há linha repetida.

### Corrigido — Jarvis: data "DD/01/YYYY" e motivo do erro da IA na planilha (10/11/2026)
- A coluna "Data da distribuição" usava o formato `DD/MM/YYYY` (maiúsculo). O Excel entende, mas o
  Numbers (Mac) e o Google Planilhas mostravam "DD/01/YYYY". Agora usa `dd/mm/yyyy`.
- As células da IA que falharam mostram o motivo: `ERRO NA IA: conferir (sem crédito na conta da
  Anthropic)`, teto de gasto, chave inválida, modelo inexistente, limite por minuto, demora. Nunca
  levam o texto do processo. O erro completo continua no `jarvis/logs/bot.log`.

### Adicionado — Orelha: escolher o período do painel semanal na página `/orelha` (09/11/2026)
- Campos **De** e **Até** ao lado do botão "Gerar painel semanal". Já vêm de hoje a 7 dias depois; se
  "De" passar de "Até", o "Até" vai para 7 dias depois. O Sam recusa data inválida e período de mais de
  120 dias.
- O Sam passa o período ao Orelha (`main.py --painel-de AAAA-MM-DD --painel-ate AAAA-MM-DD`, também pela
  linha de comando). Sem período, vale o padrão (de hoje até `ORELHA_PAINEL_DIAS_FILA` dias).
- O painel mostra "Semana de <De> a <Até>". A fila traz as tarefas com prazo no período e as vencidas
  que continuam abertas. A agenda de audiências traz as do período.
- Um painel que não começa no dia do pedido não vira base da comparação da semana seguinte (o PDF avisa).
- 7 testes novos no Orelha (263 no total).

### Alterado — Orelha: painel semanal vai do dia do pedido até 7 dias depois (09/11/2026)
- O painel semanal mostrava "Semana de" a semana anterior até hoje. Agora a semana começa no dia em
  que o painel é pedido e vai até 7 dias depois. Exemplo: pedido em 09/11 → "Semana de 09/11 a 16/11".
- A fila pega as tarefas com prazo até esse fim: `ORELHA_PAINEL_DIAS_FILA` passou de 14 para 7.
- As vencidas que continuam abertas seguem na fila (a comparação "não feitas" depende delas).
- Testes do painel ajustados para a janela nova.

### Adicionado — Albi/Presto: TRT7 pelo botão "Login via Presto" (09/11/2026)
- No TRT7 (PJe-JT), o `primeirograu/login.seam` mostra o botão "Login via Presto" (`onLoginSSO()`),
  que leva ao SSO (`sso.cloud.pje.jus.br`, `client_id=pje-trt07-1g`), onde aparece o quadro do Presto.
- Na tela de login do tribunal, se o quadro ainda não está lá e existe esse botão, o robô clica nele
  e espera o SSO. Depois segue igual ao TJCE: credencial, PIN, entrou.
- `logado()` não confunde mais o `authenticateSSO.seam` (passagem do SSO de volta ao tribunal) com
  o tribunal já logado.

### Corrigido — Albi/Presto: espera as credenciais no quadro e não pega aba errada (09/11/2026)
- No Mac, o quadro "Credenciais Disponíveis" apareceu primeiro vazio e o robô parou com "nenhuma
  credencial". Agora espera até 45 s as credenciais chegarem e avisa enquanto espera.
- Depois do clique no tribunal, pegou uma janela interna do Chrome com id gigante, que o AppleScript
  não aceita ("Não é possível obter tab id 1.26E+9"). Agora usa a própria aba quando ela já saiu do
  console e só considera abas novas de site (http) com id válido.
- O aviso de Acessibilidade diz o nome do app onde o bot está rodando (Terminal, VS Code ou iTerm).

### Corrigido — Albi/Presto: clique de verdade no número da credencial (09/11/2026)
- O quadro "Credenciais Disponíveis" (v0.143.0) só abre o campo do PIN com clique de mouse de verdade
  no número (`a.prs-text-presto-blue`).
- O `entrar` agora avisa logo no começo quando o macOS não deu a permissão Acessibilidade ao app onde
  o bot roda. Sem ela, o clique de verdade é descartado sem erro nenhum.
- A posição do número na tela não soma mais a largura do DevTools aberto ao lado.
- O tribunal aberto pelo console é encontrado também quando abre numa janela nova.

### Corrigido — Albi/Presto: login do console do Presto de verdade (e-mail, Acessar, senha, Login) (09/11/2026)
- No console real, o login fica na própria página `/sites` (`#login-page`). O campo de e-mail é um
  `<input type="text">` com o rótulo "Email" num `<label>` ao lado. O robô achava que era o filtro de
  Sites e digitava o nome do tribunal no campo de e-mail.
- Agora reconhece a tela de login pelo `#login-page`, pelo rótulo do campo e pelo "esqueci minha senha".
- Clica no botão "Acessar" só depois que ele habilita.
- Nunca digita o tribunal enquanto a tela de login estiver aberta.
- Testado no console real: e-mail, Acessar, senha, Login, Sites, TJCE 1º Grau e a tela de login do PJe.

### Corrigido — Albi/Presto: o robô não pula mais o login do console do Presto (09/11/2026)
- O `entrar` e o `processos` olhavam só 6 s se o console pedia login, e só reconheciam o login pelo
  campo de senha. Com o site lento ou com o login em duas etapas (e-mail primeiro), achavam que já
  estavam logados e iam direto para Sites.
- Agora esperam até 25 s o console mostrar o login ou a lista de sites. O login é reconhecido pelo
  campo de e-mail, pelo campo de senha ou pela URL, e aceita uma tela (e-mail e senha) ou duas
  (e-mail, Continuar, senha).
- Se o preenchimento por JavaScript não pegar, clicam nos campos e digitam com o teclado de verdade.
- Se continuar no login, param com o print `0_console_login_depois`. A senha nunca é impressa nem salva.

### Alterado — Albi/Presto: aviso de Acessibilidade cita o Visual Studio Code (09/11/2026)
- Quando o clique de verdade precisa da permissão Acessibilidade do macOS, a mensagem agora diz para
  ligar o app onde o bot roda (Terminal ou Visual Studio Code), e não só o Terminal.

### Alterado — Branch relatorio-processos atualizada com a main: PDF dentro de `jarvis/` (09/11/2026)
- Com o Jarvis na pasta própria, o PDF foi junto: `bot/relatorio_pdf.py` → `jarvis/nucleo/relatorio_pdf.py`
  e `bot/timbrado/` → `jarvis/nucleo/timbrado/` (o Jarvis não importa nada de `bot/`).
- reportlab, pillow e chardet saem do `requirements.txt` da raiz e entram no `jarvis/requirements.txt`
  (quem já tem a `jarvis/.venv`: rodar `./instalar.sh` de novo).
- A garagem da Vila 04 fica como está na main (`ligar_vila04_garagem.py`, já com as 5 vilas).

### Alterado — PDF do relatório: sem a soma dos valores e sem a frase do rodapé (05/11/2026)
- A capa não mostra mais a "Soma dos valores das ações" (a soma continua na aba Resumo da planilha).
- Saiu a frase "Relatório de processos · <grupo> · <mês>" do pé de todas as páginas; fica só o
  número da página.

### Corrigido — Tipo de processo "não informado" (05/11/2026)
- 5 processos (1 da MG/SP e 4 da Casa do Celular, quase todos de PROCON) estavam com o campo
  "Processo" vazio no VIOS. Agora o tipo sai da "Área", como a equipe cadastra os demais (Cível
  Consumidor, Administrativo e Contratos → CÍVEL; Trabalhista; Tributário). Vale para a planilha,
  o PDF e o resumo da IA; esses processos continuam na aba "Cadastro incompleto" para corrigir no VIOS.

### Adicionado — Relatório de processos em PDF no timbrado (05/11/2026)
- Cada grupo gera `<GRUPO>.pdf` junto com a planilha (`jarvis/nucleo/relatorio_pdf.py`), no timbrado do
  escritório (cabeçalho, rodapé com os 5 escritórios e marca d'água, nas posições e margens do
  `Timbrado_RFeitosa_Advogados_COM_MARCADOR.docx`; imagens em `jarvis/nucleo/timbrado/`), em Garamond.
- Conteúdo: capa com os números do mês (total, soma dos valores e contagens), página "Resumo do
  mês" escrita pela IA (uma chamada por grupo; US$ 0,04 num grupo de 26 processos) e uma ficha
  por processo com os textos da planilha. Campos vazios e "ERRO NA IA" ficam de fora.
- A página `/jarvis` lista o PDF para baixar. Falha no PDF não impede a planilha.
- `jarvis/requirements.txt`: reportlab 4.2.5, pillow 10.4.0 e chardet 5.2.0 (compatíveis com Python 3.8).
- Testado: PDF da Casa do Celular MG/SP (26 processos, 21 páginas) e execução completa da
  Plasfran Itapipoca (teste, 2 processos: planilha + PDF, US$ 0,06).

### Corrigido — Orelha: aviso do certificado vencido vai para o `orelha.log` (09/11/2026)
- Na execução das 09:13 no Mac, o aviso "VIOS com o certificado vencido..." saiu sem data e não entrou
  no `orelha/logs/orelha.log`, porque usava outro logger. Agora usa o logger `orelha`.

### Adicionado — Albi: passa pelo aviso de certificado vencido do Sonar (09/11/2026)
- Pedido do usuário: "faça isso pra todos os bots". O Sam, o Orelha e o Jarvis já passavam pelo aviso do
  VIOS; o Albi (Sonar da Leme) ganhou o mesmo em `albi/certificado.py`, uma cópia do
  `passar_aviso_certificado`, porque o Albi não importa nada de `bot/`. É chamado logo depois de abrir o
  `SONAR_URL`.
- Mesmas regras: só passa com `net::ERR_CERT_DATE_INVALID` e no endereço do Sonar.
- Testado no Chrome headless: o certificado vencido de teste foi passado, o autoassinado recusado, e o
  Sonar normal não foi mexido.
- O Presto não entra: ele usa o Chrome aberto da pessoa pelo AppleScript, que não roda nada na página
  de aviso.

### Adicionado — Sam, Orelha e Jarvis: passam pelo aviso de certificado vencido do VIOS (09/11/2026)
- O certificado `*.vios.com.br` (GoGetSSL) venceu em 08/11/2026 às 23:59 GMT. Desde então, o Chrome
  dos robôs mostra "Sua conexão não é particular" no lugar do login. Foi isso que fez o Orelha de 09/11
  sair com "a tela de login não apareceu".
- Pedido do usuário: o robô vai em **Avançadas** e clica em **Ir para roneely.vios.com.br (não seguro)**.
  Novo `passar_aviso_certificado(driver, url)` em `bot/navegador.py`, `jarvis/nucleo/navegador.py` e
  `orelha/nucleo/navegador.py`, chamado logo depois de abrir o login (`bot/login.py`,
  `jarvis/nucleo/login.py`, `orelha/nucleo/vios.py`). Depois do clique, o Chrome lembra a escolha
  e as outras páginas do VIOS abrem direto.
- Só passa quando o erro do aviso é `net::ERR_CERT_DATE_INVALID` (certificado vencido) e o endereço é
  o do VIOS. Outro erro (emissor desconhecido, nome errado) ou outro site continua bloqueando, e o
  log diz o motivo.
- Substitui a primeira versão do mesmo dia, que pedia a impressão digital do certificado em
  `VIOS_CERTIFICADO_VENCIDO` no `.env`. Essa variável não é mais lida e pode ser apagada.
- Testado no Chrome headless contra o VIOS real:
  - o aviso foi passado, o login abriu com o campo de senha e a página de Relatórios abriu direto;
  - com o bloqueio de envios do Orelha ligado, o bloqueio continuou ativo depois do clique;
  - em sites de teste, o certificado autoassinado e o de outro endereço foram recusados.
  - Os 256 testes do Orelha passam.

### Corrigido — Orelha: login que não abre é tentado de novo, com print e o que apareceu (09/11/2026)
- Na execução de 09/11, as 4 partes do relatório saíram "não rodou: não entrei no VIOS: a tela de
  login não apareceu", sem pista do motivo. O VIOS respondeu normalmente pouco depois (o Jarvis entrou
  às 07:46). Agora:
  - se a tela de login não aparece, ou se a página nem abre (erro de rede do Chrome), o Orelha tenta
    de novo depois de 60 s e de mais 180 s (`ESPERAS_LOGIN` em `orelha/main.py`). Usuário ou senha
    errados não são repetidos;
  - cada falha deixa um print em `logs/login_falhou_<data_hora>_<n>.png`;
  - o erro diz o título, o endereço e o começo do texto da página que apareceu no lugar do login.
- 3 testes novos em `orelha/tests/test_main.py`; os 256 do Orelha passam.

### Adicionado — Jarvis: `--grupos` lê os grupos do VIOS e `--salvar` põe os que faltam na página (09/11/2026)
- Pedido do usuário: a página `/jarvis` só mostrava os 6 grupos escritos à mão no `PROCESSOS_GRUPOS`
  (Plasfran Itapipoca, Camocim e Maranhão, LD Urbanismo e as duas Casas do Celular); faltavam as
  outras empresas. `relatorio_processos.py --grupos` (ou `./rodar.sh --grupos`) entra no VIOS, lê o
  filtro Grupo Cliente e lista cada grupo como já na lista ou novo, sem IA e sem planilha;
  com `--salvar`, acrescenta os novos no fim do `PROCESSOS_GRUPOS` do `.env` (os atuais ficam na mesma
  ordem, o resto do arquivo não muda, "TODOS" nunca entra) e avisa os que não existem mais no VIOS.
  A junção e a gravação do `.env` foram testadas com uma lista falsa; a leitura do VIOS usa o
  `grupos_disponiveis` que o relatório já usa.

### Corrigido — Albi/Presto: clique de verdade no número da credencial e no PIN (06/11/2026)
- No Mac, o `entrar tjce1` abriu o console, clicou no TJCE e chegou ao login, mas não conseguiu clicar no
  número da credencial para abrir o campo do PIN. Agora: o quadro do Presto é procurado também em
  "shadow roots" e frames; o clique por JavaScript manda a sequência completa (ponteiro, mouse, click);
  se em 8 s o campo do PIN não aparecer, o robô traz a aba para a frente e clica com o mouse de verdade
  no número (`chrome_mac.clicar_tela`, posição calculada da página); se o PIN por JavaScript não entrar
  em 12 s, clica no campo e digita o PIN pelo teclado (`chrome_mac.digitar_tela`, System Events). O
  clique e a digitação de verdade precisam do Terminal em Acessibilidade. Testado com uma página falsa
  que só aceita clique e tecla de verdade e põe o quadro num shadow root; ainda não rodou no Mac.

### Adicionado — Albi/Presto: `presto.py liberar-chrome` liga o JavaScript por Apple Events (06/11/2026)
- O usuário não achou no Chrome do Mac o menu Visualizar > Desenvolvedor > "Permitir JavaScript de
  Apple Events", que o bot precisa. O novo comando faz isso sem o menu: pergunta antes (`--sim` não
  pergunta), fecha o Chrome, marca `browser.allow_javascript_apple_events` no `Preferences` de cada
  perfil (Default e Profile N), guardando uma cópia `Preferences.albi-bak`, e abre o Chrome de novo.
  A mensagem de erro do JavaScript desligado agora indica esse comando. A edição do arquivo foi
  testada com perfis falsos; o comando ainda não rodou no Mac.

### Adicionado — Vila 05: o parque vivo do Orelha e o campo `cena` do `/orelha/status` (06/11/2026)
- **`GET /orelha/status` ganhou `cena`** (`bot/orelha.py`, função `cena()`): `null` sem relatório real;
  senão só a data e as CONTAGENS do relatório real mais recente, tiradas do `resumo.json`
  (`atrasadas`, `graves` = atrasadas há mais de 7 dias, `vencem_hoje`, `intimacoes`,
  `intimacoes_graves`, `parados`, `parados_graves`, `audiencias_hoje`, `pericias_hoje`, `erros`,
  `funcoes`). Campo ausente = 0; nunca leva nomes, `por_responsavel` nem `por_area`. O `_resumo`
  passou a guardar os `numeros` de cada seção. Testes novos em `tests/test_orelha_cena.py` (8).
- **Esqueleto** `doc/vila/ligar_vila05_vida.py`: cria `this.v5` (cena, hora, minuto, dia da semana,
  humor, rotina e os testes pela URL) e seis ganchos vazios que as camadas preenchem. Sem as camadas a
  vila fica igual. Sem servidor (site publicado) usa uma cena de exemplo.
- **Casinhas** (`ligar_vila05_casinhas.py`): duas casinhas novas ao lado da do Orelha; a cada 2 ou 3
  minutos a Pretinha ou o Caramelo saem, dão uma voltinha, cheiram o ar e voltam.
- **Ossos** (`ligar_vila05_ossos.py`): as tarefas atrasadas viram ossos meio enterrados na caixa de
  areia (até 12; acima disso cada osso vale mais de uma); as graves são ossos escuros. Quando a
  contagem cai, um osso sai voando; quando sobe, cresce um montinho e aparece outro.
- **Clima** (`ligar_vila05_clima.py`): sol com brilhinhos e borboletas sem atrasadas; sombras de nuvem
  com poucas; céu fechado com muitas ou com graves; chuva leve com poças a partir de 5 graves.
- **Dia** (`ligar_vila05_dia.py`): a luz segue a hora do navegador (madrugada, nascer, dia, pôr do sol,
  noite; tinta de no máximo 34%); à noite acendem a lanterna, a antena da torre e vagalumes. O Orelha
  dorme na porta da casinha antes das 8h, depois das 18h e no fim de semana, almoça das 12h às 13h e
  usa chapéu de palha no fim de semana. Uma execução sempre passa na frente.
- **Humor** (`ligar_vila05_humor.py`): no fim de cada execução, zoomies em oito em volta da piscina e
  reverência (ok), emburrado de costas com nuvenzinha e o balão "HMPF... DEU ERRO, OLHA O LOG." (erro)
  ou um suspiro (parou). Acrescenta um ponto de extensão no desenho do Orelha para as poses novas.
- **Passeio** (`ligar_vila05_passeio.py`): de vez em quando (cerca de 1 minuto, das 7h às 19h, mais
  vezes no fim de semana) uma pessoa genérica dá uma volta pelos caminhos (corredor, moça com bolsa,
  criança com balão ou senhor de bengala). Se o Orelha está livre e no expediente, ele vai até ela e
  eles brincam: cheira, pula em cima, late, roda, ganha carinho (coraçãozinho) ou petisco; depois ela
  acena e segue. Quando ele atravessa a barreira de agility, salta por cima (a sombra fica no chão) e
  levanta poeira ao pousar; de vez em quando ele faz um treino na barreira. O plano novo
  `this.v5.passeio` vale depois do humor e antes da rotina.
- Testar pela URL, também sem servidor: `?vila=5&v5hora=21`, `&v5dia=6`, `&v5atrasadas=40&v5graves=8`,
  `&v5humor=ok|erro|parou`, `&v5visita=1|pretinha|caramelo`, `&v5pessoa=1|corredor|moca|crianca|senhor`,
  `&v5agility=1`.
- Guia dos ganchos em `doc/vila/ganchos-vila05.md` e ferramentas de teste em `doc/vila/teste-vila05/`
  (`checar.py`, `rodar.js`, `igual.js`).
- Ordem: `ligar_vila05_vida.py` depois de todos os outros `ligar_*` (inclusive o
  `ligar_vila02_ponte.py` e o `ligar_vila03_arena_att.py`), e as seis camadas em seguida, em qualquer ordem. `DOCUMENTACAO.md`
  (Passo 36) e `orelha/README.md` atualizados.
- Testado: as seis aplicadas numa cópia e no `bot/vila/vila.html`, todas idempotentes; `node --check`
  do script da vila; smoke test em node com canvas falso (simulado com vários overrides, servidor com
  `cena` nula, parcial e zerada, execução simulada inteira com cada humor), sem erro de camada;
  capturas no Chrome headless (meio-dia, 21h, sábado); 8 testes da cena e 253 do Orelha passando.

### Corrigido — Albi/Presto: PIN do quadro enviado com Enter quando só há o botão "fechar" (06/11/2026)
- O quadro real do Presto (v0.141.1, enviado pelo usuário) tem a credencial "Roneely A1" com o número
  em link azul e, depois do clique, o campo "Pin do usuário" sem botão de confirmar (só "fechar").
  Agora, sem botão de confirmar, o robô manda Enter completo no campo (keydown, keypress e keyup),
  além de enviar o formulário se houver. Testado com uma página igual ao quadro real.

### Alterado — Albi/Presto: tribunal aberto pelo console do Presto (Sites) (06/11/2026)
- Pedido do usuário: o fluxo é achar o tribunal, abrir o console do Presto
  (`console.presto.oystr.com.br`), ir em **Sites** e abrir o tribunal por lá, porque é assim que a
  extensão faz o login. Novo `presto.abrir_tribunal`, usado pelo `entrar` e pelo `processos`: abre
  `/sites`; se o console pedir login, preenche `PRESTO_EMAIL` e `PRESTO_SENHA` do `albi/.env` e clica em
  Entrar (avisa se continuar na tela de login, por exemplo com código de 2 fatores); digita o nome do
  tribunal no filtro "Site", acha a linha pelo nome (`SITES` no `presto.py`: "TJCE 1º Grau - PJe",
  "JFCE - PJe", "Pje TRT 07 1g"...) e clica no link. Usa a aba nova que o console abrir; se o clique
  não sair do console (site sem link, como o TRT7 1º grau), abre o login do tribunal na mesma aba.
  Depois segue como antes: quadro do Presto, credencial, PIN e consulta do processo.
- `--direto` (no `entrar` e no `processos`) pula o console e abre a URL do login como antes.
- Novos `PRESTO_EMAIL` e `PRESTO_SENHA` no `.env.example` (vazios). Nunca são impressos nem salvos:
  conferido que a senha não aparece em nenhuma captura.
- Testado no Linux com páginas que imitam o console (login e a tabela de Sites com o HTML real) e o
  PJe: entrou no console, achou o TJCE 1º grau, clicou, entrou pelo quadro com o PIN e procurou os
  processos.

### Corrigido — Albi/Presto: `processos` pega o último relatório que tem processos (06/11/2026)
- No primeiro uso no Mac, o `presto.py processos` pegou o relatório mais novo (05/11, sem nenhum
  processo) e parou com "não tem processos". Agora ele pula os relatórios sem processos e pega o mais
  novo que tem. Novo `--listar`: mostra todos os relatórios (pasta, quantos processos, empresas); para
  usar um deles basta o nome da pasta (`presto.py processos 2026-11-04_...`).

### Adicionado — Albi/Presto: procurar nos tribunais os processos do último relatório (06/11/2026)
- Novo `presto.py processos [pasta] [--tribunal X] [--max N] [--conferir]` (código em
  `albi/presto_processos.py`). Pega o `processos.csv` do relatório mais novo (`albi/saida/*/` ou
  `saida/albi/*/`) ou da pasta dada, junta as pessoas do mesmo processo e descobre o tribunal pelo número
  CNJ: TJCE 8.06, TRT7 5.07, JFCE 4.05 com origem 81xx, TRF5 4.05 no resto; 2º grau pela instância do
  Sonar ou pela origem 0000. Os outros tribunais ficam como "fora" (ainda sem login no Presto).
- No Mac, para cada tribunal: abre o login no Chrome aberto, entra pelo quadro do Presto e, na mesma aba,
  procura cada processo. No PJe (TJCE, JFCE, TRF5) usa a tela "Consultar processos": preenche o número no
  campo único ou nos campos separados (pula os fixos) e clica no Pesquisar do formulário, não no do menu.
  No TRT7 abre o detalhe do processo da consulta processual. Anota achou / não encontrado / captcha / sem
  formulário / não entrou / fora e guarda os links do processo (onde estão os autos) em `resumo.json`,
  mais `resumo.txt` e as capturas em `<pasta do relatório>/presto/<data_hora>/`. Se a consulta mandar
  para o login, entra de novo uma vez. Só clica em "Pesquisar"; ainda não baixa os autos.
- `--conferir` mostra a divisão por tribunal sem abrir o Chrome (roda no Linux também).
- O login do `presto.py entrar` virou a função `presto.login`, usada pelos dois comandos; se a aba já
  estiver logada, ele segue sem procurar o quadro. Novo `chrome_mac.ir` (leva a aba para outro endereço).
- Testado no Linux com o `chrome_mac` imitado pelo Selenium e páginas locais que imitam o quadro do
  Presto e a consulta do PJe: entrou com o PIN, preencheu os campos separados, achou o processo e o link
  `openPopUp(... listProcessoCompletoAdvogado.seam ...)`, e marcou "não encontrado" no outro. Os sites
  reais dos tribunais e o AppleScript só no Mac.

### Alterado — Vila 03 ganha a arena nova do Albi, com a luta (06/11/2026)
- A plataforma com as quatro torres sai; entra a cena nova de `albi/mascote/fundo-arena-albi.html`:
  casa em domo com anexo e torre de observação, árvore, lago, dragão no céu e dois lutadores que
  brigam, disparam raios e explodem tudo; depois descem, reconstroem a casa, a muda cresce e o ciclo
  recomeça. O campo ganhou altura para o Albi andar entre a casa e o lago.
- Postos: Doca 01 = porta da casa; Receptor TXT = porta do anexo; Conferência = janela da torre de
  observação; Torre Sonar = mastro com antena novo, à direita. Os eventos, as falas e o painel não
  mudam. Patch novo `doc/vila/ligar_vila03_arena_att.py` (o último da lista); a vila gerada do zero
  com todos os patches sai igual à do repositório.

### Alterado — Orelha: atrasadas agrupadas por dia (clica e abre), Atrasadas da semana e relatório na página /orelha (06/11/2026)
- O relatório do dia ficou grande demais (279 que vencem hoje + 210 atrasadas, tudo aberto). Agora as
  atrasadas vêm agrupadas por **dia do vencimento**: cada dia da última semana, depois faixas de 7 dias
  (até 35 dias), meses e anos. Cada grupo vem **fechado**, com o total, os selos e uma barra; clica e
  abrem as tarefas (`<details>`, sem JavaScript). O responsável vai em cada tarefa e no quadro
  "Atrasadas por responsável" do fim da seção. O PDF sai com os grupos fechados (resumo).
- Novo `semana.html` (**Atrasadas da semana**), feito pela função `prazos` com a mesma leitura: de
  segunda até hoje, um grupo por dia com as tarefas que venciam nele e continuam abertas; na
  segunda-feira, a semana passada inteira. Embaixo, as de antes da semana e o quadro por responsável.
- Página `/orelha` do Sam: o último relatório aparece dentro da página, com as abas "Relatório do dia"
  e "Atrasadas da semana" (a altura acompanha o que abre; "Abrir no VIOS" abre em outra aba); na lista
  dos guardados, o botão "Semana".
- Código: `orelha/nucleo/semana.py` (novo), `nucleo/relatorio.py` (grupos que abrem e quadro),
  `nucleo/modelos.py` (`Secao.recolher`, `Secao.quadro`, `Item.dia`), `funcoes/prazos.py`
  (`grupo_do_dia`), `bot/orelha.py` e `bot/templates/orelha.html`.
- Testado: 253 testes do Orelha (novos: grupos por dia, semana, HTML que abre e fecha); rodada real
  no VIOS (210 atrasadas em 17 grupos; semana com 114 desta semana e 96 de antes); a página `/orelha`
  num servidor de teste, no Chrome: abas, altura que cresce e diminui, links em outra aba.

### Adicionado — Orelha: `orelha/agendar_mac.sh` agenda o relatório no Mac com um comando (06/11/2026)
- Em 06/11 a página `/orelha` avisou que o relatório das 7h30 não saiu. Causa: o Orelha nunca tinha
  sido agendado (nem launchd no Mac, nem cron no Linux); o horário do `.env` só serve para o aviso.
- `./agendar_mac.sh instalar` cria os dois agendamentos do launchd (relatório do dia e processos
  parados) a partir de `ORELHA_HORARIO` e `ORELHA_HORARIO_PARADOS` do `orelha/.env`, então o horário
  do agendamento e o do aviso não se desencontram. Também `agora` (roda já, para testar), `status`,
  `log` e `parar`. Recusa sem `.venv`, sem login do VIOS ou com horário inválido; avisa se `HEADLESS`
  não é `true` ou se `VILA_URL` está vazio.
- Testado no Linux simulando o Mac: os dois `.plist` saem válidos, com seg–sex 7h30 e sáb 8h; o
  conversor do horário aceita faixa, lista, domingo e faixa que vira a semana, e recusa dia ou hora
  inválidos. Falta testar no Mac de verdade.

### Adicionado — Orelha: botão "Gerar painel semanal" na página `/orelha` (06/11/2026)
- Sem dia fixo: a colaboradora aperta o botão quando quer o relatório semanal. `POST /orelha/painel/rodar`
  (`bot/envio_web.py`, `bot/orelha.py: rodar_painel`) abre `orelha/main.py --funcoes painel` em segundo plano
  (uma execução por vez, mesma checagem de origem das outras páginas), `GET /orelha/painel/status` informa o
  andamento e a página lista os painéis gerados com "Abrir PDF" e "HTML". Log em `orelha/logs/painel_sam.log`.
- `bot/orelha.py` serve também `painel-semanal.pdf/.html` (lista fechada de nomes) e, no Windows, confere se
  o processo vive pelo `tasklist` (lá `os.kill(pid, 0)` encerraria o processo).
- As regras do painel não mudaram; só a forma de disparar (botão, em vez de agendamento).

### Adicionado — Orelha: painel semanal de peças e audiências em PDF no papel timbrado (06/11/2026)
- Nova função `painel` (`orelha/funcoes/painel.py`; `./rodar.sh --funcoes painel`, semanal): gera
  `saida/<data>/painel-semanal.pdf` e `.html` seguindo o modelo `2026_PAINEL_SEMANAL`: resumo executivo,
  taxa de resolução semanal, carga por advogado, agenda de audiências dos próximos 7 dias e lista de
  tarefas com a situação em cores (VENCIDA, URGENTE, ATENÇÃO, PRÓXIMA, NO PRAZO).
- Papel timbrado do escritório (`orelha/nucleo/timbrado.py` + `orelha/assets/timbrado/`, imagens
  extraídas do `.docx` do timbrado): A4, marca d'água, faixa vinho e rodapé em todas as páginas, com as
  margens do modelo. Desenho em `orelha/nucleo/painel.py`. O PDF sai pelo mesmo Chrome do relatório do dia.
- Comparação entre semanas por registro (`historico/painel-<data>.json`): não feitas, novas e taxa de
  resolução. A 1ª edição não tem semana anterior e avisa. Leitura incompleta não grava o registro.
- Configuração opcional `ORELHA_PAINEL_*` no `orelha/.env.example` (termos de peça e audiência, dias da
  fila e da agenda, limiar de carga alta, faixas da taxa).
- Testes em `orelha/tests/test_painel.py` e fixtures fictícias em `orelha/fixtures/painel/`.

### Alterado — Orelha: funções com documento próprio ficam fora do relatório do dia (06/11/2026)
- `main.py`: função com `RELATORIO_DIARIO = False` (o painel) não entra no `relatorio.html` e, rodando
  sozinha, não gera nem sobrescreve o relatório do dia. `Contexto` ganhou `pdf` (valor de `--sem-pdf`).
- `funcoes/prazos.py`: `TarefaLista` ganhou `processo` (coluna `nro_proc` da lista de tarefas); o
  relatório do dia não muda.

### Alterado — Vila 02 vira a batalha na ponte do Bumblebee, vista de cima (05/11/2026)
- Cenário do `doc/vila/zangao-transforma_att.html`: ponte sobre a água (ondas e reflexo do fogo),
  pista com faixas tracejadas e a dupla amarela, guard-rail e quatro pilares com luz vermelha.
- Os postos ficam nos mesmos lugares, como coisas da ponte: Doca 01 = garagem listrada com a vaga
  marcada; Filtro previdenciário = cabine de pedágio com cancela (sobe quando ele filtra ou passa);
  Captura de dados = pórtico com o painel de mensagens; Torre VIOS = antena no pilar da direita.
  Placas novas; os eventos, as falas e o painel não mudam.
- O Bumblebee parado é o robô de frente; para andar, as peças encaixam no **carro visto de cima**,
  que gira para o lado em que vai (faróis, rastro e onda de choque ao virar). Anda só na pista.
- Em volta, a batalha: dois duelos de robôs (chegam como carros, brigam, explodem e vão embora),
  trânsito, carcaças pegando fogo, explosões longe dele, destroços, fumaça e brasas. Só desenhada
  com a Vila 01, 02 ou 03 na tela; sem tremer a tela. Partes que ficariam atrás da caixa de fala
  foram subidas.
- Patch: `doc/vila/ligar_vila02_ponte.py`, o último da lista (depois do `ligar_vila04_garagem.py`).
- Testado no Chrome sem janela: a Vila 02 desenha tudo e anima (transformação, carro virando,
  duelos, explosão), sem erro no console; as Vilas 01 e 03 continuam iguais; a vila regerada do
  zero com todos os patches na ordem fica igual à do repositório; rodar o patch de novo não repete.

### Alterado — Vila 04 vira a garagem do Homem de Ferro, com uma máquina por estação (05/11/2026)
- Trabalho do Kaio (commit `17103ec` da branch `relatorio-processos`), trazido para a main. O commit
  foi escrito para a vila antiga de 4 vilas e conflitava com a atual (5 vilas, com o Orelha); em vez
  de juntar à mão, a garagem virou um patch próprio, `doc/vila/ligar_vila04_garagem.py` (o último da
  lista, como a arena e o parque), com o código dele copiado sem mudança.
- O cenário da Vila 04 passa a ser a garagem do `fundo-oficina-jarvis.html` (parede, túnel com
  luzes, janelas, telas, carros, armaduras em exposição, braços robóticos soldando e uma máquina
  para cada estação: rack com antena, scanner de documentos e terminal com impressora); a parte
  fixa vai para o fundo e a animada só é desenhada com a Vila 03, 04 ou 05 na tela.
- O holograma do centro é o posto do Jarvis: acende quando ele está lá, com o Jarvis como núcleo.
- Os três lugares de trabalho são as máquinas: Conexão VIOS (rack: LEDs e antena com sinal),
  Leitura dos processos (holograma + scanner; barra de processo X de Y) e Planilhas (terminal
  preenche a planilha e a impressora imprime). Placas novas. O Jarvis voa em linha reta.
- Testado: a vila regerada do zero com todos os patches na ordem fica igual à da main; com a
  garagem, a Vila 04 abre e desenha tudo (print no Chrome sem janela); rodar o patch de novo não
  repete nada.

### Adicionado — Orelha avisa quando o relatório roda e guarda os relatórios no Arquivo (05/11/2026)
- **Horário no `orelha/.env`**: `ORELHA_HORARIO` (padrão `seg-sex 07:30`) e `ORELHA_HORARIO_PARADOS`
  (padrão `sab 08:00`), no formato `<dias> <HH:MM>`. Têm que ser o mesmo do cron/launchd (quem roda o
  Orelha continua sendo o agendamento).
- **Vila 05**: parado, o Orelha diz quando roda, quando sai o próximo relatório ("amanhã (sexta) às
  7h30") e quantos estão guardados. Se o de hoje não saiu até 45 min depois da hora marcada, avisa
  para conferirem o computador dele, e o topo mostra "Atrasado". No fim de cada execução,
  leva a folha ao **Arquivo** (armário novo do parque, com gavetas e puxador de osso), guarda na
  gaveta e diz quando sai o próximo. A placa mostra quantos estão guardados ("Arquivo · 12"), e as
  gavetas ganham uma pastinha por relatório. Botão **"Relatórios guardados"** abre a página `/orelha`.
  No simulado, ele fala o horário padrão e o arquivo começa com 3 relatórios de exemplo.
- **Página `/orelha`** do Sam: o horário, o próximo relatório, o aviso de atraso e todos os relatórios
  já feitos (do mais novo para o mais antigo), com graves, pontos de atenção e os botões Abrir, PDF e
  Planilhas (.csv). Os simulados ficam à parte. Os arquivos continuam em `orelha/saida/<data>/`.
  `GET /orelha/status` (para a vila) leva só datas e contagens. O cartão do Orelha na Vila dos Bots
  mostra o horário, o próximo (ou o atraso) e o botão "Relatórios guardados (n)".
- Código: `bot/orelha.py` (lê o horário e as pastas do Orelha, sem importar nada de `orelha/`),
  `bot/templates/orelha.html`, rotas em `bot/envio_web.py` e `ORELHA_PASTA` no `.env` do Sam (só se o
  Orelha estiver noutra pasta). A rota dos arquivos só entrega `relatorio.html`, `relatorio.pdf` e a
  planilha `.csv` de uma pasta de dia (`.env`, `../` e `historico/` dão 404).
- Vila: `doc/vila/ligar_orelha_agenda.py` (novo, o último dos patches). O `ligar_vila05_parque.py`
  ganhou o armário do Arquivo; a barreira de agility desceu para a grama de baixo e a argola mudou
  de lugar. A aplicação do zero de todos os patches dá o mesmo arquivo.
- Testado: no Chrome sem janela, o simulado inteiro (até guardar no Arquivo, "Arquivo · 3" → "· 4"); com
  o servidor, `/`, `/orelha`, `/orelha/status`, `/vila` e os arquivos do relatório respondem, e a Vila 05
  fala o horário e o atraso.

### Corrigido — Orelha: instalador recusa Python antigo (05/11/2026)
- No Linux só havia Python 3.8; o `orelha/instalar.sh` aceitava e o Orelha quebrava ao rodar
  (`TypeError: 'type' object is not subscriptable`). Agora o instalador para com aviso se o Python
  for mais velho que 3.10 e diz como instalar um novo pelo `uv`
  (`uv python install 3.12 && PYTHON=$(uv python find 3.12) ./instalar.sh`).
- 1ª rodada do placar de prazos neste Linux (05/11/2026): 201 tarefas atrasadas (45 há mais de
  7 dias), 26 responsáveis, 129 vencem hoje.

### Adicionado — Albi: preparação para baixar os autos pelo Presto (Oystr) (05/11/2026)
- Contexto: para a mensagem da CAC ter os fatos de cada processo (o que foi narrado na petição), a
  atendente pesquisava processo por processo no tribunal, entrando pela extensão do **Presto**
  (cofre de credenciais da Oystr), baixava os autos e mandava para o ChatGPT. A Oystr tem robôs
  de "cópia integral" por API, mas o plano do escritório (Padrão: credenciais, bloqueios e
  assinaturas) não inclui a API. Caminho escolhido: o bot usa a própria extensão do Presto.
- Novo `albi/presto.py`, primeiro passo (ainda não baixa autos):
  - `presto.py preparar`: abre um Chrome normal com um perfil só do bot (`albi/perfil_presto/`,
    fora do git porque guarda a sessão do Presto). A pessoa instala a extensão e entra no Presto
    uma vez. O bot nunca vê nem guarda a senha.
  - `presto.py explorar [URL ...]`: abre esse perfil pelo Selenium, acha a extensão (pelo nome
    "Presto"/"Oystr" no manifest, inclusive nome traduzido), abre o pop-up dela numa aba
    (`chrome-extension://<id>/<popup>`), sem precisar inspecionar pelo DevTools, e salva print,
    HTML, texto e a lista de botões, campos e links. Faz o mesmo em cada URL de tribunal pedida, e
    nas abas que o Presto abrir. Também salva o resumo do manifest (em quais sites a extensão age).
    Tudo em `albi/logs/presto/<data_hora>/` (fora do git).
  - Corrigido no primeiro uso no Mac: fechar a janela não encerra o Chrome, então o `preparar`
    ficava esperando (só saía com Ctrl+C), e o Terminal se enchia de avisos internos do Chrome
    (GoogleUpdater, Crashpad). Agora ele espera um Enter no Terminal, fecha o Chrome salvando o
    perfil, esconde esses avisos e diz se achou o Presto no perfil.
  - Novo `presto.py copiar`: copia o perfil do Chrome que já tem o Presto instalado e logado para o
    perfil do bot (pedido do usuário: "abrir o Chrome com o perfil que já está aberto"). Lista os
    perfis do Chrome (nome e conta), pede para fechar o Chrome só durante a cópia, deixa de fora
    caches e abas da última sessão e guarda qual pasta foi copiada (`--profile-directory`). O
    Chrome não permite usar o perfil aberto direto (automação no perfil principal é bloqueada e o
    perfil fica travado enquanto aberto). Testado com uma pasta do Chrome simulada e abrindo o
    perfil copiado pelo Selenium. Se o Chrome do bot fechar no meio do `explorar`, ele avisa e diz
    onde ficou o que foi capturado.
  - No primeiro uso no Mac, o `copiar` ficava repetindo "O Chrome está aberto. Feche-o…" sem dizer
    como (no Mac, fechar a janela não encerra o Chrome, e o Presto pode mantê-lo rodando). Agora ele
    explica e pergunta "Posso fechar o Chrome agora?"; com "sim", fecha o Chrome como o menu
    Chrome > Sair (as abas voltam ao abrir de novo), espera até 40 s e copia. Com "não", para sem
    copiar. No Mac, se o "Sair" pelo AppleScript não fechar em 10 s (o macOS pede permissão para o
    Terminal controlar o Chrome na primeira vez), pede o fechamento pelo sistema (SIGTERM), que também
    fecha salvando o perfil.
  - **Mudança de caminho: usar o Chrome que já está aberto no Mac.** No Chrome do bot (perfil novo ou
    copiado), a conta Google do escritório pede confirmação de identidade, que não dá para
    automatizar. Novo `albi/chrome_mac.py`: controla o Chrome aberto pelo **AppleScript** (abre aba,
    espera carregar, roda JavaScript para ler e clicar, lista abas), no perfil e com o Presto que já
    estão lá. Precisa, uma vez: no Chrome, Visualizar > Desenvolvedor > "Permitir JavaScript de Apple
    Events"; no macOS, permitir o Terminal controlar o Google Chrome.
  - Novo `presto.py aberto [URL ...]`: na janela da frente do Chrome aberto, abre cada URL (sem URL:
    console do Presto e login do PJe do TRT7), salva HTML, texto, botões/campos/links (inclusive em
    iframes e em "shadow roots", onde extensões põem botões) e print da tela; procura o botão/link que
    menciona "Presto" (o "login via Presto" do tribunal), clica e captura de novo a aba e as abas
    novas. Testado simulando o AppleScript com o Selenium numa página com iframe e botão do Presto
    em shadow root (achou, clicou e capturou a aba nova). O AppleScript em si só roda no Mac.
  - **Login pelo Presto funcionando no caminho do Chrome aberto.** O quadro "Credenciais
    Disponíveis" do Presto é posto dentro da própria página do tribunal (`div.presto-dialog-root`,
    `data-presto-el`), então o JavaScript da página alcança. Novo `presto.py entrar [tribunal|URL]`
    (tjce1, tjce2, trt7, trt7-2, jfce, trf5, trf5-2; URLs tiradas da página Sites do console do
    Presto): abre o login no Chrome aberto, espera o quadro, clica na credencial
    (`PRESTO_CREDENCIAL`, padrão a primeira), preenche a senha/PIN se o quadro pedir
    (`PRESTO_PIN` no `albi/.env`, do jeito que o Vue do Presto percebe) e confirma; diz se entrou
    (saiu das telas de login) e salva as capturas de cada etapa. Testado com uma página que imita o
    quadro: PIN certo entra, PIN errado avisa e termina com erro, sem PIN no `.env` avisa.
  - Segurança: as capturas de botões/campos guardavam o que estava digitado nos campos, o que
    incluiria o PIN; agora de `<input>`/`<textarea>`/`<select>` nunca sai o valor (só o rótulo de
    botões). Conferido que o PIN não aparece em nenhuma captura.
  - Com essas capturas, o próximo passo é montar o caminho do bot: entrar no PJe pelo Presto,
    buscar o processo e baixar os autos.
- Testado com perfil temporário e extensão simulada (o Presto não está instalado nesta máquina):
  o Chrome abre com o perfil, a captura do pop-up e do site sai completa, e a extensão é achada
  numa pasta com a estrutura real do Chrome.

### Alterado — Albi: mensagem da CAC conta a história do processo, sem IA (05/11/2026)
- A mensagem de cada pessoa com processos (`mensagens_cac.txt`, "Capturar resumo") agora segue o
  roteiro do prompt da CAC: do que se trata, por que o processo existe, o que aconteceu (com
  datas), as decisões, a situação atual e um resumo de cada processo. Tudo por regras fixas,
  sem API de inteligência artificial.
- Novo `albi/datajud.py`: consulta cada número de processo na **API pública do DataJud (CNJ)**,
  que é gratuita e traz as movimentações oficiais com os códigos da Tabela Processual Unificada.
  Viram frases: citação/notificação, contestação, réplica, audiências (realizadas, marcadas e
  quantas não aconteceram), liminar, gratuidade, recursos e contrarrazões, envio ao tribunal,
  sentença (procedência, improcedência, parcial, acordo, extinção), embargos, julgamento do
  recurso, trânsito em julgado, cumprimento de sentença, alvará/RPV (sempre com a ressalva de que
  não comprovam pagamento), penhora, falta de bens, arquivamento, desarquivamento, baixa e
  suspensão. Junta os graus (1º grau, turma recursal, tribunal) e conta cada tipo de decisão uma
  vez só (o TJCE repete o mesmo registro de sentença várias vezes).
- Situação atual pelo movimento mais recente; se o status da planilha do Sonar disser outra
  coisa, a mensagem avisa. A conclusão diz quantos estão em andamento e se há sentença
  desfavorável à pessoa (ré com pedido aceito, ou autora com pedido negado).
- "Por que o processo existe": explica em palavras simples o tipo de ação (reclamação
  trabalhista, execução fiscal, inquérito policial…) e os assuntos cadastrados pelo tribunal
  (horas extras, inclusão indevida em cadastro de inadimplentes, dano moral…).
- Só o número do processo sai do computador (nunca CPF nem nome). O resultado fica em
  `datajud/` na pasta da execução e não é consultado de novo; "não encontrado" é consultado de
  novo na próxima vez. Tempo total limitado (`DATAJUD_PRAZO`, 150 s); se a API não responder
  (ela recusa consultas quando está sobrecarregada; o Albi tenta 3 vezes), o processo sai como
  antes, só com o cadastro do Sonar. `DATAJUD=false` no `albi/.env` ou `--sem-datajud` no
  `relatorio.py` desligam.
- O que continua fora (não está no Sonar nem no DataJud): os fatos narrados nas petições, os
  fundamentos das decisões e a data marcada das audiências. A ressalva final diz isso.
- O "Capturar resumo" da página espera até 6 minutos pelo relatório (antes 3), por causa da
  consulta.
- Testado com a API real (processo do Juizado de Juazeiro do Norte com sentença, embargos,
  recurso negado na turma recursal, trânsito, cumprimento e arquivamento), com um caso montado
  igual ao exemplo do Robério (trabalhista aguardando audiência; cível com contestação,
  gratuidade e réplica), com processo não encontrado e com a consulta desligada.

### Alterado — A entrada do sistema é a Vila dos Bots (05/11/2026)
- Quem entra no sistema (`http://<IP do Mac>:5001/`) vê agora a **Vila dos Bots**, uma página neutra,
  sem nome nem mascote de nenhum bot no topo:
  - marca "VILA DOS BOTS" com o ícone de uma casinha;
  - a vila com os eventos reais;
  - um cartão para cada bot (Sam, Bumblebee, Albi, Jarvis e Orelha), com o que ele faz e o botão
    para a página dele. Quem não está instalado no servidor aparece como "Não instalado".
- A página de envio do **Sam** foi para **`/sam`**, igual por dentro. Os links "Sam" das outras
  páginas e os redirecionamentos do envio já apontam para lá. Toda página de bot ganhou o botão
  "Vila dos Bots" no topo.
- A janela de senha do navegador agora diz "Vila dos Bots" em vez de "Envio ao VIOS". Por isso o
  navegador pode pedir a senha mais uma vez.
- Arquivos: `bot/templates/vila_dos_bots.html` (novo) e as rotas `/` e `/sam` em `bot/envio_web.py`.
### Alterado — Vila 05 vira o parque do Orelha, cheio de brinquedos e com a casinha dele (05/11/2026)
- O fundo cinza da Vila 05 (prédios, lotes e torre de metal) virou um **parque dos cães**: cerca
  branca de madeira em volta (com o portão para a Vila 04), grama com flores e caminhos de areia
  com marcas de pata.
- Os postos continuam nos mesmos lugares, com cara nova:
  - **Casinha do Orelha** (antes "Doca 01 · Orelha"): casinha azul de telhado vermelho com a
    plaquinha "ORELHA", lanterna piscando, pote de ração e pote de água. Ao terminar, o status
    agora diz "Voltando para a casinha";
  - **Calendário:** mural de madeira com o calendário, bilhetes e a foto do Orelha. Enquanto ele
    lê, um dia acende por vez;
  - **Intimações:** caixa de correio vermelha. Enquanto ele lê, as cartas saem voando. No fim, a
    bandeirinha sobe vermelha (achado grave) ou verde;
  - **Relatório:** toalha de piquenique xadrez com a cesta, onde a folha do relatório aparece;
  - **Planilhas:** baú de brinquedos com a pilha do Albi em cima e os baldes verde, âmbar e cinza;
  - **Torre VIOS:** torre de parquinho com escorregador e a luz piscando na antena.
- Brinquedos espalhados: piscina de bolinhas (no lugar da "Doca 04 · livre"), caixa de areia com
  osso enterrado, barreira de agility, prateleira de brinquedos, hidrante, pneu, frisbee, ossos,
  bolinhas de tênis, corda, argola e galinha de borracha. Animados: a bolinha quicando, bolinhas
  pulando na piscina, duas borboletas, a água do pote e a gota do hidrante.
- Onde o Orelha anda, os eventos, as falas e o painel não mudaram. Patch novo
  `doc/vila/ligar_vila05_parque.py`, já aplicado em `bot/vila/vila.html`. Ele roda **por último**,
  depois do `ligar_jarvis.py`.
- Conferido:
  - a aplicação do zero de todos os patches (com o parque no fim) dá o mesmo arquivo;
  - no Chrome sem janela, o parque parado e o "Simular execução" inteiro (Torre VIOS → Calendário
    → Intimações → Planilhas → Relatório → casinha). O único erro no console (`flivre` no primeiro
    desenho) já aparecia antes desta mudança;
  - o Orelha subiu inteiro para o GitHub: os arquivos de `orelha/` e `doc/vila/` são os mesmos no
    disco e no repositório (só `.env`, `logs/` e `saida/` ficam fora, de propósito). Os 223 testes
    passam e o `--simulado` roda até o fim.

### Corrigido — Vila 04: aviso de "Jarvis não instalado" (05/11/2026)
- A fala da Vila 04 ainda pedia `JARVIS_PASTA`, mas desde a pasta `jarvis/` ele não é mais necessário.
  Agora diz o que fazer: "no Mac, rode cd jarvis && ./instalar.sh e preencha o jarvis/.env". O Sam
  considera o Jarvis instalado quando a pasta tem `.venv`, `relatorio_processos.py` e `.env`. A
  `.venv` e o `.env` são criados no próprio Mac e não vêm pelo `git pull`.
- O `ligar_jarvis.py` também atualiza esse texto numa vila que já tem o Jarvis.

### Alterado — Jarvis com pasta própria `jarvis/` (05/11/2026)
- O Jarvis saiu do meio do Sam (`relatorio_processos.py` na raiz e módulos em `bot/`) e foi para a
  pasta **`jarvis/`**, como o Albi e o Orelha:
  - `relatorio_processos.py` (entrada), `instalar.sh` e `rodar.sh` (Mac/Linux), `rodar.bat`
    (Windows), `requirements.txt` próprio (selenium, python-dotenv, anthropic, openai, openpyxl),
    `.env.example` (antes `.env.usuario2.example`) e `README.md` (antes `RELATORIO_PROCESSOS.md`);
  - `jarvis/nucleo/`: os módulos dele (processos_grupo, processos_detalhe, relatorio_planilha,
    vila_aviso) e **cópias próprias** do que ele usava do Sam (config, custo, extracao, ia/, login,
    navegacao, navegador e o log, antes do `main.py`). Ele não importa mais nada de `bot/`: mudança no
    Sam não quebra o Jarvis, e vice-versa. Se o VIOS mudar a tela de login, corrigir nos dois;
  - `.env`, `logs/` e `saida/` (planilhas em `saida/relatorios/AAAA-MM/`) ficam dentro de `jarvis/` e
    fora do git.
- Lado do Sam: `bot/jarvis.py` acha o Jarvis em `jarvis/` sozinho (`JARVIS_PASTA` só se ele estiver
  noutra pasta) e lê o `jarvis/.env`. O link "Jarvis" do topo só aparece com ele instalado. O
  `openpyxl` saiu do `requirements.txt` do Sam (só o Jarvis usa).
- Instalar no Mac: `cd jarvis && ./instalar.sh` (Python 3.9+; o código usa `list[str]`) e preencher o
  `jarvis/.env`. Quem já tinha um `.env.usuario2` pode copiar o conteúdo para `jarvis/.env`.
- Testado no Python 3.12:
  - o `relatorio_processos.py` carrega tudo e para com a mensagem certa sem login;
  - a planilha .xlsx sai com as 4 abas (dados de mentira);
  - pelo Sam, `/jarvis/status`, a página `/jarvis`, o link do topo e a recusa de grupo fora da lista
    funcionam.
  O Jarvis não foi rodado no VIOS (precisa do segundo usuário).

### Adicionado — Jarvis entra no projeto (merge da branch `relatorio-processos`) e na Vila 04 (05/11/2026)
- Merge da branch `relatorio-processos`. Ela traz o **Jarvis**, o relatório mensal de processos por
  Grupo Cliente com o segundo usuário do VIOS, só leitura: `relatorio_processos.py`,
  `bot/processos_grupo.py`, `bot/processos_detalhe.py`, `bot/relatorio_planilha.py` (planilha
  .xlsx), `bot/jarvis.py`, `bot/vila_aviso.py`, a página `/jarvis`, `RELATORIO_PROCESSOS.md`,
  `.env.usuario2.example` e `JARVIS_PASTA` no `.env`. Ele precisa de `openpyxl` (já no
  `requirements.txt`).
- Conflitos resolvidos mantendo os dois lados:
  - `bot/eventos.py` aceita zangao, orelha e jarvis;
  - `bot/envio_web.py` tem as rotas do Albi e do Jarvis;
  - os links do topo mostram Bumblebee, Albi e Jarvis;
  - `.env.example`, CHANGELOG e DOCUMENTACAO juntam os dois lados. O CHANGELOG ainda tinha marcas
    de conflito sobrando do merge do Orelha, que também foram tiradas.
- **Vila**: refeita pelos patches, e não juntando as duas versões. O Jarvis ocupa a **Vila 04**,
  que estava vaga, com placas "Doca 01 · Jarvis", "Leitura dos processos", "Planilhas" e "Torre
  VIOS", e o núcleo de IA. Agora são 01 Sam · 02 Bumblebee · 03 Albi · 04 Jarvis · 05 Orelha.
  - O `doc/vila/ligar_jarvis.py` ganhou o caminho para a vila de 5 vilas, que acende a 04 em vez de
    criar uma vila nova, e roda **por último**. O caminho antigo, de 3 vilas, continua.
  - O `ligar_vila03_arena.py` ganhou a etapa 2, que recorta o desenho da arena na Vila 03: a
    montanha e as nuvens passavam para a Vila 04.
- Conferido:
  - aplicação do zero de todos os patches = arquivo atual;
  - as 5 vilas e a página `/jarvis` funcionam no Chrome sem erro;
  - `/`, `/vila`, `/albi`, `/zangao`, `/jarvis`, `/jarvis/status` e `/eventos` respondem 200;
  - o código do Jarvis compila.
  O Jarvis não foi rodado no VIOS, porque precisa da pasta e do `.env.usuario2` dele.

### Corrigido — Vila quebrada depois do merge do Orelha (05/11/2026)
- O merge do Orelha (PR #1) gravou `bot/vila/vila.html` com as marcas de um conflito sem resolver
  (`<<<<<<<`, `=======`, `>>>>>>>`), com as duas versões da vila coladas. Por isso a vila não abria.
- A vila foi refeita a partir da versão certa (a da arena do Albi) com o patch do Orelha aplicado
  por cima. A vila tem agora 5 vilas: 01 Sam, 02 Bumblebee, 03 Albi, 04 vaga e 05 Orelha.
- O `doc/vila/ligar_orelha.py` foi escrito com os nomes antigos ("Ultron", "Zangão") e não batia
  com a vila atual. Agora ele troca "Sam"/"Bumblebee" pelos nomes antigos antes de aplicar e devolve
  os novos no fim, inclusive no que o Orelha acrescenta. Ele roda por último na ordem dos patches.
- Conferido: a aplicação do zero de todos os patches dá o mesmo arquivo; as 5 vilas e o "Simular
  execução" do Orelha funcionam no Chrome sem erro; as páginas do servidor (`/`, `/vila`, `/albi`,
  `/zangao`, `/eventos`) respondem 200; os 223 testes do `orelha/` passam no Python 3.12 (o do Mac).
  No Python 3.8 do Linux eles não carregam, porque o código usa `list[str]`, que é do 3.9 em diante.

### Alterado — Vila 03 vira a arena do Albi (04/11/2026)
- Fundo da Vila 03 trocado pela arena que o usuário fez (`albi/mascote/fundo-arena-albi.html`),
  adaptada ao tamanho da vila (320×224):
  - parte fixa: céu em faixas, montanhas, mesas de pedra, campo, estrada até o horizonte e lago;
  - parte animada: nuvens e pássaros passando, o lago brilhando, o brilho que corre pelo piso, a
    grama balançando e as pontas das quatro torres piscando.
- O Albi **transita pela plataforma**: só pode andar em cima dela, e parado passeia entre seis
  pontos. Os postos ficaram nas torres:
  - **Doca 01 · Albi:** frente à esquerda;
  - **Receptor TXT:** fundo à esquerda, onde ele lê o .txt;
  - **Conferência:** painel atrás da plataforma, com as linhas e a luz verde ou vermelha;
  - **Torre Sonar:** torre alta da frente à direita, cuja luz pisca quando ele entra no Sonar ou
    pesquisa.
- As placas da Vila 03 ficam nas torres, e as "docas livres" saíram, porque não existem na arena.
  Eventos, falas e painel do Albi não mudaram.
- `doc/vila/ligar_vila03_arena.py`, já aplicado em `bot/vila/vila.html`, roda depois do
  `ligar_vila01_campo.py`. A aplicação do zero de todos os patches dá o mesmo arquivo.
- Testado em Chrome sem janela: a arena parada (com o passeio) e uma execução inteira por eventos
  (arquivo → receptor → conferência → Torre Sonar → doca), sem erro no console.

### Alterado — O Ultron agora se chama Sam (04/11/2026)
- Na tela, o bot de envio ao VIOS passa a se chamar **Sam**: título e marca da página, links
  "Sam" nas páginas do Albi e do Bumblebee, textos da página de envio ("o Sam confere…"), cena da
  página e, na Vila 01, placa "DOCA 01 · SAM", aba "01 · SAM", fala, status, registro e "página
  do Sam".
- A marca do topo está nas cores do boneco: o **S dourado** como o cabelo e o **AM verde** como a
  capa (`.marca-sam` em `_estilo.html`). A bolinha de status da Vila 01 também ficou dourada.
- O código interno não muda: rotas, arquivos (`bot/`, `enviar.py`), `ultron()` nos templates e
  eventos `bot: "ultron"`. Na vila, a troca está na etapa 2 do `doc/vila/ligar_vila01_campo.py`
  (já aplicada).

### Alterado — Mascote novo do Ultron e Vila 01 no campo (04/11/2026)
- **Mascote**: o personagem da imagem que o usuário mandou (`doc/mascote/WhatsApp Image 2026-11-04 at
  11.19.56.jpeg`), passado para uma grade de pixels de 28×35. Tem cabelo dourado, olhos vermelhos
  fechados (sorrindo), capa verde com broche, colete com botões e pés descalços.
  - Substitui o robô cromado na página do Ultron: topo, caixa de soltar o .txt e ícone da aba
    (`bot/templates/_ultron.html`, com as mesmas animações do ultron_script: brilho e piscar dos
    olhos, mãos e pés).
  - Na Vila 01 ele balança parado e alterna os pés andando.
  - Amostra em `doc/mascote/ultron-campo.html`. O nome continua Ultron.
- **Vila 01 no campo** (`doc/vila/ligar_vila01_campo.py`, aplicado em `bot/vila/vila.html`), no estilo
  do cenário que o usuário mandou (`doc/mascote/1e86eacd-….jpeg`):
  - céu com nuvens e colinas, grama com flores, caminhos de terra e sebe;
  - casa na colina de porta redonda verde com chaminé fumegando (Doca 01 · Ultron);
  - moinho com as pás girando (Receptor TXT);
  - casa de porta amarela com o quadro da conferência;
  - hortas cercadas (docas livres);
  - lago com ponte de pedra;
  - torre de pedra com lanterna (Torre VIOS).
- A geometria da vila é a mesma, então os caminhos, as portas, os postos e todas as animações
  (.txt caindo no moinho, CIs no quadro, envio para a torre) continuam iguais. As Vilas 02 e 03 não
  mudaram.
- A cena da página (`_cena.html`/`_estilo.html`) foi ajustada para o tamanho do mascote novo.
- Testado em Chrome sem janela: a vila parada, a simulação inteira (moinho → quadro → torre) e a
  página do Ultron, sem erro no console. A aplicação do zero dos patches (zangão → albi →
  bumblebee → campo) dá o mesmo arquivo.

### Adicionado — Número do processo em cada CI (04/11/2026)
- **.txt do chat**: novo campo `PROCESSO:` logo depois de `CI:`, com o número no padrão CNJ, em
  todos os blocos. Ele é opcional para o robô: arquivo antigo sem o campo continua passando.
  Skill única gerada de novo (`arquivo-para-o-robo.md`, `pedido-arquivo-robo.txt`,
  `regras-do-programa.md`).
- **Página de envio**: cada CI mostra o número do processo, na conferência (campo "Processo",
  editável), no andamento ao vivo e na lista do envio. Ele vem do `PROCESSO:` do arquivo; sem ele,
  do que foi capturado do VIOS (campo Números ou, se vazio, o teor). Há aviso quando não há número,
  quando está fora do formato ou quando é diferente do capturado. O .txt refeito depois de editar
  leva o `PROCESSO:`.
- **Análise pelo robô**: `numero_processo()` em `bot/analise.py` procura no campo Números e, se
  não achar, no teor da intimação, aceitando também os 20 dígitos sem pontos ("Processo:
  01081327420158060167" → 0108132-74.2015.8.06.0167). Só fica PENDENTE quando não aparece em lugar
  nenhum.
- Testado: arquivo com e sem `PROCESSO:`, número da captura, sem número, número inválido, ida e
  volta do .txt e edição na página (com o aviso de número diferente).

### Adicionado — Lançamento: corte das 12h para ciência e análise (04/11/2026)
- Ao preencher cada tarefa no VIOS, o robô olha a hora e o dia. Tarefas **CIÊNCIA** e **ANALISAR
  SENTENÇA/ACÓRDÃO/DECISÃO** (cível, trabalhista, execução, previdenciário e reclamante) com data
  de hoje, ou ciência sem data, lançadas **depois das 12:00** ou no sábado/domingo, vão para o
  **próximo dia de segunda a sexta**. Ex.: sexta 12:01 → segunda; terça 15:00 → quarta; 12:00 em
  ponto ainda fica no dia. É a regra da skill da Controladoria, com a mesma contagem simplificada
  (feriado não pula).
- **Só a data da tarefa muda** (decisão do usuário): as linhas `PRAZO PARA EMBARGOS`, `PRAZO PARA
  RECURSO` e `PRAZO FATAL` da descrição continuam no D-2 calculado.
- Segue a skill ("nunca alongar prazo judicial pela rotina interna"): se alguma data de prazo da
  descrição vier antes do novo dia, a tarefa fica para hoje e o log avisa **URGENTE**.
- Data que já está no futuro (o chat já aplicou o corte) não é mexida. Vale para os dois fluxos (o
  .txt da página de envio e a análise pela API) e para o "Testar sem gravar". Cada mudança fica no
  log: "corte das 12h: lançada às 12:01: data passou de 06/11/2026 para 09/11/2026 (segunda)".
- `corte_meio_dia()` em `bot/lancamento.py`. Testado com: sexta 11:59, 12:00 e 12:01; terça 15:00;
  sábado; embargos D-2 no próprio dia; tarefa de outro tipo; data já futura.
- Regras do programa da skill única atualizadas (`doc/skill-unica/regras-do-programa.md`, também com
  embargos/recurso em vermelho).

### Alterado — VIOS: prazo para embargos e prazo para recurso em vermelho (04/11/2026)
- Na descrição da tarefa no VIOS, as linhas **"PRAZO PARA EMBARGOS: dd/mm/aaaa"** e **"PRAZO PARA
  RECURSO: dd/mm/aaaa"** (também "PRAZO DE EMBARGOS/RECURSO") agora saem em **negrito e vermelho**,
  junto com a data, como já acontecia com "PRAZO FATAL...". A regra é uma só (`PRAZO_VERMELHO` em
  `bot/lancamento.py`) e vale também para a prévia da página de revisão (`revisao.html`). Texto
  que só cita "prazo para recurso" no meio da frase continua sem cor.
- Pedido feito com um print do VIOS (tarefa com "PRAZO PARA EMBARGOS: 06/11/2026" e "PRAZO PARA
  RECURSO: 20/11/2026").

### Adicionado — Albi: mensagem no padrão da CAC para cada pessoa com processos (04/11/2026)
- Novo `albi/mensagem_cac.py` (chamado pelo `relatorio.py`). Escreve `mensagens_cac.txt` e
  `mensagens_cac.json`, com **uma mensagem por pessoa com processos**, no modelo da Central de
  Atendimento ao Cliente:
  - abertura com a atendente: "*Beatriz Vasconcelos:* Informamos que, após consulta aos sistemas
    do Poder Judiciário, foram localizados *dois processos* relacionados a *Nome.*";
  - um bloco por processo: "*1️⃣ Autor x Réu*", depois "Trata-se de um processo de *classe* (área),
    nº, iniciado em, perante a vara, na comarca/UF (tribunal), *na qual Nome figura como papel
    (explicação) e Outra parte como parte autora/ré.*";
  - em cada processo também: assunto cadastrado, valor da causa (com a ressalva do modelo, de
    que não é valor reconhecido), segredo de justiça, aviso de que processo criminal não é
    condenação, e situação atual (em tramitação, arquivado definitivamente, baixado, extinto,
    suspenso);
  - com mais de um processo, um parágrafo de conclusão (áreas, posição da pessoa, quantos em
    andamento e quantos encerrados);
  - no fim, a ressalva de que os autos não foram consultados.
- **Não inventa nada.** O Sonar só entrega o cadastro de cada processo, e o "Detalhes do Pedido"
  também não traz mais nada (conferido): não há fatos, movimentações nem decisões. Por isso a
  mensagem não descreve fatos nem diz que houve condenação, pagamento ou resultado. Usa
  "relacionados a *Nome*", sem "Sr./Sra.", porque o gênero não está nos dados. Devolve o acento
  às palavras comuns que o Sonar manda sem acento ("EXECUCAO FISCAL" → "Execução fiscal") e
  acerta a caixa ("4ª Vara de Execuções Fiscais", "S/A", "LTDA").
- Página `/albi/resumo/<id>` ("Capturar resumo"): as mensagens da CAC vêm primeiro, com os botões
  **Beatriz Vasconcelos / Renara Kathleem** (trocam o nome no começo de cada mensagem), "Copiar
  mensagem" e o `mensagens_cac.txt`. Depois vem o resumo por empresa. Numa execução antiga, o
  botão gera tudo de novo com o que já foi baixado.
- Testado com planilha sintética (4 processos: trabalhista, cível, criminal em segredo de
  justiça, execução fiscal arquivada) e pela página. O negrito do WhatsApp foi conferido (pares de
  `*`).

### Alterado — Zangão vira Bumblebee, o robô que se transforma em carro (04/11/2026)
- Novo mascote (desenho do usuário em `doc/mascote/zangao-transforma.html`): robô amarelo 24×26
  de frente e carro 30×12 de lado. **Ao se movimentar ele vira carro**: as 8 peças (cabeça,
  peito, asas-porta, braços e pernas) voam em arco, giram de 90 em 90° e encaixam no chassi. Só
  então ele anda, com farol, rodas girando e poeira. Ao chegar, desfaz e volta a robô, que pisca e
  mexe as asas-porta.
- **Vila 02**: `doc/vila/ligar_bumblebee.py`, já aplicado em `bot/vila/vila.html`, troca o sprite
  antigo (16×12) pelo robô e pelo carro, com a mesma transformação. Ele espera virar carro antes de
  andar, tanto nos passos da execução quanto no passeio, e transforma mais rápido quando há fila
  grande de eventos.
- **Página `/zangao`**: o robô novo no topo e no ícone da aba. Na cena, um canvas
  (`zangao_cena()` + `bumblebee_script()` em `bot/templates/_zangao.html`): vira carro, anda até o
  posto e volta a robô. Com "reduzir movimento" no sistema, a troca é direta.
- **Nome: Bumblebee** no que aparece na tela: título e marca da página, links "Bumblebee" nas
  páginas do Ultron e do Albi, placa "DOCA 01 · BUMBLEBEE", abas e falas da vila, e mensagens de
  erro ("o Bumblebee não está instalado…"). Rotas, `ZANGAO_PASTA` e `bot: "zangao"` dos eventos
  continuam iguais, então o bot em si não precisa mudar.
- Testado em Chrome sem janela: na vila, as fases robô → transformação → carro → robô, sem erro
  no console; na página, a cena, o topo e os links.
### Alterado — O bot Faro passou a se chamar Orelha, com o desenho do cão Orelha (04/11/2026)
- Homenagem ao Orelha, o cão comunitário da Praia Brava (Florianópolis). Pasta `faro/` → `orelha/`;
  variáveis `FARO_*` → `ORELHA_*` (o `.env` desta máquina foi convertido: só os nomes das chaves);
  bot dos eventos da vila `"faro"` → `"orelha"` (`BOTS_EXTERNOS` em `bot/eventos.py`);
  `doc/vila/ligar_faro.py` → `doc/vila/ligar_orelha.py` (a vila foi refeita a partir da `main` com o
  script novo); log `logs/orelha.log`; relatório "Feito pelo Orelha", selo "O" e cor caramelo.
- Desenho novo (sprite 20×14 e em pé 14×19, mesmas animações): vira-lata preto e caramelo como o
  Orelha — dorso e cabeça pretos com brilho, peito, bochechas e patas caramelo, focinho grisalho,
  orelha dobrada, rabo pra cima com a ponta caramelo, língua de fora nas animações. Ficam o chapéu
  fedora e o monóculo de leitura; sai a antena com luz. Ficha em `orelha/mascote/ficha.html`.
- As entradas abaixo (de 04/11/2026) falam em "Orelha" porque foram renomeadas junto; até esta
  troca, o bot se chamava Faro.

### Alterado — Orelha: processos parados pelo filtro do VIOS e busca de planilhas pelo endereço (04/11/2026)
- **Parados.** A leitura antiga (lista inteira de ativos + ficha por ficha) estourou o tempo (120 s)
  na 1ª rodada real. A lista de processos tem o filtro nativo "Com ou sem tipo de tarefa? = Sem" +
  "Tipo de tarefa = Abertas" (formulário GET): devolve os processos ativos SEM nenhuma tarefa
  aberta. Conferido: "com" e "sem" não têm processo em comum, e duas fichas sorteadas (81 e 37
  tarefas) não têm nenhuma aberta. Padrão novo `ORELHA_PARADOS_FONTE=filtro`; a leitura antiga
  continua com `=fichas`. Lê no máximo 500 por pesquisa; acima disso, por ano de cadastro, dividindo
  o que vier cheio (`ORELHA_PARADOS_DESDE`, `ORELHA_PARADOS_MAX_PAGINAS`). Grupo = área; "urgente" = sem
  edição há mais de `ORELHA_PARADOS_DIAS_GRAVE` dias (padrão 60). Rodada real: 1818 processos, 32
  páginas, cerca de 1 min.
- **Planilhas do Albi.** A busca do topo é um formulário GET: `campo_pesquisa_selecionado=nro_proc`,
  `pesq[busca]=<número>`, `pesq[filtros][]=todos`. Padrão novo `ORELHA_PLANILHAS_MODO=url`, um número
  por vez. Resposta que não é a tela de Processos vira "não deu para conferir", nunca "novo". Teste
  real com uma pasta de teste fora do repositório: o número existente deu "já está no VIOS", o
  inventado deu "novo" (o registro do teste foi apagado).
- `nucleo/vios.buscar_get`: busca a página por GET de dentro da página do VIOS aberta (mesma sessão)
  SEM desenhar. Com 500 linhas, o Chrome do bot travava mais de 120 s para desenhar a tela; buscando
  sem desenhar, 500 linhas levam ~5 s. Decodifica pelo charset da página (o VIOS manda
  ISO-8859-1; `r.text()` trocava os acentos). Só GET; recusa endereço proibido.
- Rodada real das 5 funções juntas: ~3 min, sem erro.
- `--simulado` grava em `saida/simulado-<data>/`: antes ia para a mesma pasta do dia e
  sobrescrevia o relatório real. O `.env.example` tinha `ORELHA_PARADOS_DIAS_GRAVE` duas vezes;
  agora é uma só, explicando as duas leituras.

### Alterado — Orelha: intimações esquecidas pela pesquisa por endereço, sem filtro de Área (04/11/2026)
- A tela de pesquisa de intimações é um formulário GET: a mesma pesquisa abre pelo endereço
  (`pesq[processado]=0` = "Com Tarefa Lançada: Não", `pesq[flag_oculto]=0`, `pesq[tp_data]=data`,
  `pesq[limit]=500`). Padrão novo `ORELHA_INTIMACOES_LEITURA=url`: o Orelha não envia mais o formulário
  (a leitura antiga continua com `=formulario`).
- **Sem o filtro de Área.** Conferido no VIOS, de 20/10 a 02/11/2026: sem filtro, 5 intimações sem
  tarefa; com "Marcar todas" as 16 áreas (o que o Ultron faz no passo 11), só 2. As 3 que somem
  não têm área e eram justamente as mais antigas (15 e 9 dias). A 1ª rodada real do Orelha achou 2;
  agora acha as 5. O Ultron não foi alterado.

### Alterado — Orelha: agenda da equipe toda pela lista de tarefas (04/11/2026)
- O calendário abre filtrado no usuário logado e agrupa as tarefas. Agora (padrão
  `ORELHA_AGENDA_TAREFAS_FONTE=lista`) as tarefas da agenda vêm da lista de tarefas, lidas por GET:
  não concluídas, com data para conclusão hoje ou amanhã, da equipe toda, com a hora da faixa
  "(09:00 - 23:59)". Do calendário ficam compromissos, feriados e aniversários.
- Tarefa da lista só entra se o TIPO COMEÇA com o termo (`AUDIÊNCIA UNA` sim; `INFORMAR AUDIÊNCIA`,
  `LEMBRAR AUDIÊNCIA` e `CIÊNCIA` não). O prefixo `C: ` (consultoria) é ignorado.
- A etiqueta da tarefa no VIOS (Urgente, Reaberta...) vem separada do tipo e aparece no detalhe
  ("etiqueta no VIOS: Urgente"), na agenda e nos prazos.
- Conferido no VIOS: hoje 1 audiência e 2 diligências; amanhã 2 audiências, 2 perícias e 7
  diligências; as reuniões somam as tarefas (2 hoje, 7 amanhã) e os compromissos do calendário.

### Alterado — Orelha: prazos separam "vencem hoje" e classificam o atraso por idade (04/11/2026)
- Na rodada real, "limite vencido ou hoje" = urgente deixava 272 de 273 urgentes (o limite costuma
  ser 1 dia depois da conclusão) e contava como atrasadas 114 tarefas que venciam no dia.
- Agora: **vencem hoje** (conclusão ou limite hoje, ainda não atrasada) vão para um grupo no topo,
  como "para saber", e não contam como atrasadas; **atrasada** = data para conclusão já passou, com
  "urgente" para atraso de mais de `ORELHA_PRAZOS_DIAS_GRAVE` dias (padrão 7) e "atenção" até isso.
  Uma 3ª leitura pega as tarefas com conclusão hoje e limite depois. O resumo e o histórico da
  tendência mudaram junto (o histórico grava `vencem_hoje` e o critério).
- Conferido no VIOS: 154 atrasadas (a pesquisa direta deu 155 minutos antes) e 128 com limite e
  conclusão hoje (o Orelha achou 128).
- Responsáveis: na coluna Envolvidos cada nome vem numa linha (`<br>`), e dois nomes grudavam num
  "responsável" só. Agora o `<br>` vira separador e o grupo é o primeiro responsável: 23 pessoas
  com atraso (eram 27 "grupos" contando as duplas). O cartão do relatório mostra só as atrasadas
  (`numeros["destaque"]`), sem somar as que vencem hoje.

### Alterado — Orelha: placar de prazos pela lista de tarefas do VIOS (04/11/2026)
- Conferido na tela (só leitura): o calendário abre filtrado no usuário logado e, com "Agrupar"
  ligado, junta as tarefas do dia por tipo num link para a lista de tarefas
  (`?pag=sys/processos/pxe-lista.php`). Essa lista abre por GET com os filtros no endereço e, sem
  responsável, traz a equipe toda.
- `funcoes/prazos.py`: fonte padrão nova (`ORELHA_PRAZOS_FONTE=lista`). Duas leituras de tarefas não
  concluídas: `pesq[tp_data]=data_prevista` até ontem (atrasadas) e `data_limite` até hoje (graves),
  desde `ORELHA_PRAZOS_DESDE` (padrão 01/01/2000). Lê da tabela `#tarefas-lista` o tipo, "Para
  conclusão", "Limite", os "Responsável(eis)" e o link `pxe.php?pxe_id=`. Avisa se a lista vier com
  1000 linhas (o máximo da tela). A leitura pelo calendário continua com `ORELHA_PRAZOS_FONTE=calendario`.
- Primeira rodada real (04/11/2026): o VIOS recusa `pesq[limit]` acima de 1000 ("O limite de pesquisa
  em tabela é ...", página sem tabela). Agora o Orelha lê em janelas (o que tem mais de 1 ano numa
  só; depois um mês por janela), com `pesq[limit]=1000`, e divide a janela ao meio quando ela vem
  cheia (até `ORELHA_PRAZOS_MAX_PAGINAS`, padrão 60). A leitura das graves usa a data limite dos
  últimos 30 dias até hoje. Tela de Tarefas sem tabela = nenhum resultado (não é mais erro).
  Conferido: o total do usuário logado bate com o painel "Tarefas Processuais Atrasadas".
- `funcoes/agenda.py`: reconhece o link das tarefas agrupadas (`pxe-lista.php`) e o dos feriados
  (`cal_feriados.php`). Fixture fictícia `fixtures/prazos/lista.html` e 7 testes novos.

### Adicionado — Orelha: relatório do dia que só lê o VIOS, e a Vila 05 (04/11/2026)
- Bot novo na pasta **`orelha/`**, separado dos outros como o Albi: `.venv`, `.env`, `logs/` e
  `saida/` próprios, e nada importado de `bot/` nem de `albi/` (as ideias foram copiadas). Ele
  entra no VIOS, **só lê** e escreve `orelha/saida/<data>/relatorio.html`, `relatorio.pdf`,
  `resumo.json` e `eventos.jsonl`. O relatório tem cinco partes:
  - **agenda** de hoje e amanhã: compromissos, audiências, perícias, reuniões e os feriados até
    domingo, lidos do calendário;
  - **prazos**: placar de tarefas atrasadas por responsável ("grave" quando a data limite venceu
    ou é hoje), com a tendência de 7 dias em `saida/historico/prazos-<data>.json`;
  - **intimações esquecidas**: "Com Tarefa Lançada = Não" dos últimos 15 dias, fora ontem e hoje e
    o que o Ultron ainda vai tratar (na segunda, para na quinta). Fica "grave" com mais de 5 dias;
  - **processos parados**: ativos sem nenhuma tarefa aberta. É lenta: até 300 fichas por execução,
    com retomada em `saida/historico/parados-progresso.json`. Não roda no padrão: use
    `--funcoes parados`, no agendamento semanal;
  - **planilhas do Albi**: confere no VIOS cada processo dos `processos.csv` novos ("já tem",
    "novo" ou "não deu para conferir"), grava `planilhas-<data>.csv` e o registro
    `saida/historico/planilhas-conferidas.json`.
- **Somente leitura.** O bloqueio de envios é copiado do Zangão e ligado antes do login. Ele barra
  formulário, XHR/fetch POST e `sendBeacon`, e o Orelha para se ele não estiver ativo. Só o
  calendário roda com XHR liberado, nunca para endereço proibido e, com `ORELHA_XHR_PERMITIDO`, só
  para os endereços da lista. Os formulários de pesquisa só são enviados se o DESTINO do envio (o
  action, ou o campo oculto `pag` quando o action não tem `pag=`) for uma tela de pesquisa
  conhecida e o botão de envio (inclusive `<button>` sem `type`) não tiver termo proibido; estar
  numa tela de pesquisa não basta. Endereços e cliques proibidos (`ORELHA_URL_PROIBIDA`,
  `ORELHA_CLIQUE_PROIBIDO`) nunca são abertos nem clicados. A ficha do processo abre com o bloqueio
  total (`ORELHA_PARADOS_LIBERAR_XHR=nao`).
- `--simulado` mostra o Orelha funcionando sem senha, com fixtures 100% fictícias, e não mexe no
  histórico. Testes: `cd orelha && ../.venv/bin/python -m unittest discover -s tests`.
- Configuração em `orelha/.env` (modelo comentado com todas as variáveis em `orelha/.env.example`).
  Instalação, agendamento (cron/launchd) e a lista do que ainda falta conferir na tela real estão
  em `orelha/README.md`. `.gitignore`: `orelha/.env`, `orelha/saida/`, `orelha/logs/` e `orelha/.venv/`.
- **Vila 05**: o novo `doc/vila/ligar_orelha.py` acrescenta a vila do Orelha no `bot/vila/vila.html`. O
  mundo passa de 3 para 5 vilas, e a Vila 04 fica vaga. O mascote (cão-robô de chapéu,
  `orelha/mascote/ficha.html`) anda entre Calendário, Intimações, Torre VIOS, Planilhas e Relatório e
  late "!" no achado grave. Também tem o painel "Relatório do dia · Orelha". Em `bot/eventos.py`, a
  única mudança é `"orelha"` em `BOTS_EXTERNOS`, para o Ultron aceitar o `POST /eventos` dele. Os
  eventos do Orelha levam só fases e contagens, e estão no contrato em `doc/vila/contrato-eventos.md`.
  O texto sobre a limpeza do Ultron foi corrigido: a lista dele é menor, e a barreira para
  responsável, empresa e número é a do Orelha.
- Ainda não rodou contra o VIOS real (não há credenciais aqui).

### Adicionado — Albi: "Capturar resumo", a mensagem para a empresa (04/11/2026)
- O `albi/relatorio.py` escreve também o **mensagem.txt**, com uma mensagem por empresa, pronta
  para WhatsApp ou e-mail. Ela é montada direto dos dados do relatório, sem IA, e tem:
  saudação; data; quantas pessoas foram pesquisadas, quantas sem processo e quantas com; para
  cada pessoa com processos, quantos estão em andamento e quantos encerrados, em quantos ela é
  ré, alerta de trabalhista ou criminal, e os em andamento (ação, ramo, tribunal e vara, número
  CNJ, papel da pessoa, data e valor; até 5, o resto "no relatório"); a lista de quem não tem
  processo; e a assinatura do escritório. **O CPF vai mascarado (`***.456.789-**`).** Quem ainda
  não tem resultado aparece como "em processamento" ou "em conferência", sem texto interno do
  Albi.
- Página `/albi`: botão **"Capturar resumo (mensagem para a empresa)"** na execução confirmada
  (`POST /albi/resumo/<id>`; se o resumo ainda não existir, gera o relatório antes, sem Sonar).
  Abre `/albi/resumo/<id>` com a mensagem de cada empresa num campo editável, os botões
  **"Copiar mensagem"** (funciona também em http na rede local) e "Baixar o relatório PDF (para
  anexar)", e o `mensagem.txt`.
- Testado com uma planilha sintética (dados inventados) e duas empresas, pela página.

### Adicionado — Albi: relatório dos processos, sem ninguém abrir as planilhas (04/11/2026)
- Novo `albi/relatorio.py` (só biblioteca padrão; nada a instalar). Lê o `resultado.txt` e as
  planilhas do Sonar. O arquivo vem como `.xls`, mas é `.xlsx` por dentro, com o cabeçalho na
  linha 5 e os processos a partir da 8. Escreve na pasta da execução:
  - **relatorio.html** e **relatorio.pdf**: por empresa, o resumo de todas as pessoas (com
    processos, não consta, quantos em andamento, quantos como réu/polo passivo, destaque para
    trabalhista/criminal) e, de quem tem processos, uma tabela com cada um: número CNJ (com
    link do tribunal), tribunal · comarca · vara, ramo · ação · assunto, distribuição, **papel
    da pessoa** (achado pelo CPF dela nas partes), outra parte, valor da causa e status (em
    andamento antes, depois encerrados);
  - **processos.csv**: um processo por linha, para abrir no Excel (com BOM e `;`; célula que
    começaria com `=`/`+`/`-`/`@` ganha `'` na frente para não virar fórmula).
- O Albi gera o relatório **sozinho** no fim de cada pesquisa confirmada e do "baixar de novo"
  (evento `relatorio` com as contagens). Se falhar, só registra no log, sem derrubar a execução.
- Página `/albi`: "Ver relatório dos processos" (abre na tela, em `/albi/ver/<id>`, com CSP sem
  scripts), "relatório PDF", "processos.csv (Excel)" e "ver processos" em cada pessoa. Numa
  execução antiga (sem relatório), o botão **"Gerar relatório dos processos"** (`POST
  /albi/relatorio/<id>`) monta o relatório com o que já foi baixado, sem entrar no Sonar.
- Pelo terminal: `cd albi && .venv/bin/python relatorio.py <pasta do resultado>`.
- Testado com uma planilha real de 14 processos (pedido antigo), pela página e no fim de um
  `--baixar` no Sonar (nada comprado). Os arquivos de teste foram apagados.

### Adicionado — Albi: resultado de cada pessoa em PDF e "baixar de novo" (04/11/2026)
- Ao terminar cada pedido, o Albi salva agora a **página do pedido no Sonar em PDF** para todo
  mundo, inclusive quem deu "Não consta processo" (o Sonar só tem "Baixar Resultados", a
  planilha, para quem tem processos encontrados). Fica em
  `<saída>/<empresa>/S<pedido> - <nome>.pdf`, ao lado da planilha `.xls` (quando houver).
- `resultado.txt`: a última coluna virou **arquivos** (o PDF e, se tiver, a planilha, separados
  por ` + `). Na página `/albi`, cada pessoa tem "baixar PDF" e, se tiver processos, "baixar
  planilha"; o .zip leva tudo.
- **"Baixar de novo os resultados de cada um (não compra)"**: botão na execução já confirmada
  (página `/albi` e `/albi/execucao/<id>`), ou `./rodar.sh --arquivo X --baixar` no terminal.
  Pega no registro (`albi/saida/pedidos_confirmados.json`) o número do pedido de cada pessoa da
  mesma empresa e baixa de novo o PDF e a planilha, na mesma pasta da execução. **Nunca abre a
  Nova Pesquisa nem clica em Confirmar**; quem não tem pedido no registro fica como "Sem pedido
  no registro". Só aparece num arquivo que já foi confirmado, e não apaga a trava que impede
  confirmar o mesmo arquivo duas vezes.
- Vila 03: fala do PDF, o "Sem pedido no registro" e o fim do "baixar de novo" (etapa 4 do
  `doc/vila/ligar_albi.py`, já aplicada em `bot/vila/vila.html`).
- Segurança: `resultado*.txt` no `.gitignore` (tem CPF e nome de clientes).
- Corrigido junto: nome de pessoa com ponto (ex.: "Jr.") cortava o nome do arquivo da planilha.
- Testado no Sonar com dois pedidos antigos (1 com processos, 1 "não consta") e um registro
  temporário: 2 PDFs e 1 planilha baixados, nada comprado; arquivos de teste apagados.

### Corrigido — Albi: links do resultado.txt e das planilhas (04/11/2026)
- Na página `/albi`, "resultado.txt" e "baixar planilha" davam "Not Found" no Mac. Com
  `SAIDA_PASTA` relativa (`saida`), o Flask procurava a pasta a partir de `bot/`. Agora a rota
  `/albi/arquivo/...` usa o caminho completo. O "Baixar tudo (.zip)" já funcionava.
- Testado com `SAIDA_PASTA=saida`: resultado.txt, planilha com acento/espaço no nome e .zip
  respondem 200; caminho para fora da pasta continua 404.

### Adicionado — Albi confirma os pedidos, espera e baixa os resultados (04/11/2026)
- Para cada pessoa, uma por vez: Nova Pesquisa com **Identificador Projeto = nome da empresa**
  (antes "Empresa · Nome"), CPF/CNPJ, Continuar, **Sacado = o escritório** (`SONAR_SACADO` no
  `albi/.env`, vazio = RONEELY FEITOSA & SOCIEDADE DE ADVOGADOS) e, com `--confirmar`,
  **"Confirmar Pedido"** (R$ 15,70 cada). O número do pedido vem da tela ou, se não aparecer, da
  tabela "Pedidos Recentes" da página inicial (Projeto = empresa).
- Depois espera o Sonar terminar cada pedido (página `/modulos/pesquisa-processos/pedido/<n>`,
  até `SONAR_ESPERA_MIN`, padrão 120 min), baixa a planilha ("Baixar Resultados") de quem tem
  processos encontrados em `<saída>/<empresa>/S<pedido> - <nome>.xls` e escreve
  `resultado.txt` por empresa: `CPF ; nome ; pedido ; resultado ; planilha`.
- Para não comprar duas vezes: registro `albi/saida/pedidos_confirmados.json` (anotado ANTES de
  clicar em Confirmar); CPF já pesquisado para a mesma empresa nos últimos 30 dias não é
  comprado de novo (usa o pedido anterior). Nada é repetido depois do clique em Confirmar; erro
  ali vira "Conferir no Sonar", e 3 seguidos param tudo. A repetição no .txt agora é conferida
  por empresa (o mesmo CPF em duas empresas é pesquisado nas duas).
- Página `/albi`: soltar o .txt só **confere** (`main.py --conferir`, sem navegador) e abre
  "Conferir antes de pesquisar" com quem vai ser pesquisado, quem já foi, quem fica de fora e o
  **total em R$**. Botões "Só testar (não compra)" e "Confirmar e pesquisar · R$ X" (dois cliques
  em até 8 s; o servidor também exige a confirmação). No andamento: número do pedido, resultado,
  "baixar planilha", `resultado.txt` e "Baixar tudo (.zip)". Rotas `/albi/conferir/<id>`,
  `/albi/rodar/<id>`, `/albi/arquivo/<id>/<arquivo>` e `/albi/zip/<id>`.
- Vila 03 (`ligar_albi.py`, etapa 3): etapas confirmado, já pesquisado, processos encontrados,
  não consta, conferir e sem resultado.
- Testado sem comprar: Sacado escolhido e "Confirmar Pedido" liberado (sem clicar), leitura de
  pedidos já existentes ("PROCESSOS ENCONTRADOS · 14 Processos" e "NÃO CONSTA PROCESSO"),
  download e renomeação da planilha, tabela da página inicial, conferência e "Só testar" pela
  página, travas da compra; a tela de resultados com uma execução de mentira. **O clique em
  "Confirmar Pedido" em si ainda não foi testado** (custa dinheiro): o primeiro uso real é o teste.

### Alterado — Albi: .txt organizado por empresa (04/11/2026)
- Formato padrão (modelo em `albi/modelo_pedidos.txt`, para baixar em `/albi/modelo`): um bloco
  por empresa (`EMPRESA: Empresa A`) e uma pessoa por linha (`CPF ; nome`); `---` separa as
  empresas (opcional). O CPF pode vir antes ou depois do nome. O Identificador Projeto no Sonar
  fica `Empresa · Nome`. Sem `EMPRESA:`, o arquivo vale como uma lista só (o formato antigo
  continua funcionando).
- O modelo usa `000.000.000-00`: enviado sem trocar, o Albi recusa as linhas e nem entra no Sonar.
- Feito para listas grandes (ex.: 27 CPFs de 3 empresas), uma pessoa por vez: se a sessão do
  Sonar cair no meio, entra de novo e tenta a mesma pessoa mais uma vez; erro numa pessoa não
  para as outras.
- Página `/albi`: as pessoas aparecem agrupadas por empresa ("Empresa A · 10 pessoas · 9 de 9
  feitas"). Vila 03 (`doc/vila/ligar_albi.py`, etapa 2): o painel mostra "Empresa 1 · CPF final
  06" e a fala "Pessoa 5 de 27"; nos eventos só vai o número da empresa (`grupo`), nunca o nome
  dela nem o da pessoa.
- Testado sem o Sonar: leitura de 27 CPFs gerados (3 empresas) e casos com erro; página e vila
  com uma execução de mentira, com o servidor sem o Albi (nenhuma pesquisa aberta).

### Adicionado — Albi: pedidos pelo .txt, página `/albi` e Vila 03 (04/11/2026)
- `albi/main.py --arquivo pedidos.txt`: um CPF/CNPJ por linha (`; identificador` opcional).
  Confere cada linha antes (11/14 números, dígito verificador, repetidos) e, para cada válida,
  preenche Nova Pesquisa → Tipo CPF/CNPJ → documento → Continuar, confere o documento no passo 2
  ("Pedido") e lê o valor. **Não clica em "Confirmar Pedido"** (decisão de 04/11: por enquanto
  só preencher). Erro numa linha não para as outras (print em `albi/logs/`).
- `--eventos`: cada passo sai como `@evento {json}` na saída padrão, só com o número da linha e
  o final do documento ("CNPJ final 77").
- Ultron: página `/albi` (Vila 03 no topo, caixa para soltar o .txt, andamento ao vivo de cada
  linha, `/albi/historico`), `bot/albi.py` (guarda o .txt em `saida/albi/`, roda o Albi com o
  `.venv`/`.env` dele, um por vez, até 500 linhas, e repassa os eventos à vila), link "Albi" no
  topo das páginas do Ultron e do Zangão e `ALBI_PASTA` no `.env.example` (vazio = `albi/`).
- Vila: a Vila 03 acendeu para o Albi (`doc/vila/ligar_albi.py`): placas Doca 01 · Albi, Receptor
  TXT, Conferência e Torre Sonar, o mascote de `albi/mascote/` (22×19, pisca, achata e a fivela
  brilha) andando conforme os eventos, e o painel "Pesquisa de processos" com cada linha.
- Mascote do Albi na página e no ícone da aba (`bot/templates/_albi.html`).
- Testado no Sonar real pela página (CNPJ do escritório + um CPF inválido): linha 1 pronta no
  passo 2 com R$ 15,70, linha 2 recusada antes; nada confirmado. O resumo do pedido mostrou 1
  item só (os testes anteriores não acumularam num carrinho).
### Adicionado — Jarvis: uma animação em cada lugar da Vila 04 (04/11/2026)
- Torre VIOS (entrando no VIOS): sinais do núcleo até o topo da torre, ondas e luz piscando rápido.
- Leitura dos processos (lendo): a porta acende, folhas entram girando no núcleo e uma barra
  mostra processo X de Y.
- Planilhas (salvando cada grupo e no fim): a tela do prédio vira uma planilha sendo preenchida;
  no fim, cheia e com um visto verde. O Jarvis fica uns segundos lá antes de voltar à ronda.
- O núcleo gira 3 vezes mais rápido enquanto trabalha.

### Corrigido — Jarvis: fala "Começando o relatório…" no fim (04/11/2026)
- Quando o último processo, o fim do grupo e o fim da execução chegavam juntos, a fala mostrava
  "Começando o relatório…" por um instante antes do resultado.

### Alterado — Jarvis: a pessoa escolhe os grupos do relatório (04/11/2026)
- A página `/jarvis` mostra os grupos do `PROCESSOS_GRUPOS` com caixas de marcar ("Marcar todos"
  marca e desmarca); "Gerar relatório do mês" (com confirmação) e "Testar (2 processos por grupo)"
  rodam só os grupos marcados. Sem grupo marcado, os botões ficam desligados.
- `POST /jarvis/rodar` recebe `{"modo", "grupos"}` e recusa lista vazia ou grupo fora do
  `PROCESSOS_GRUPOS`; o Jarvis roda com `--grupo "A|B"`. Enquanto roda, a página mostra os grupos
  escolhidos e se atualiza sozinha.
- Vila 04: os botões passam a ser "Escolher grupos e gerar" e "Planilhas" (abrem a página /jarvis).
- `PROCESSOS_GRUPOS` com os 6 grupos do escritório (Plasfran Itapipoca, Camocim e Maranhão, LD
  Urbanismo, Casa do Celular e Casa do Celular MG/SP).
- Testado no PC: marcando só a Plasfran Itapipoca, rodou só ela (teste, US$ 0,05).

### Adicionado — Jarvis pela plataforma: gerar e baixar o relatório pela Vila 04 (04/11/2026)
- Vila 04: botões "Gerar relatório do mês" (com confirmação), "Testar (2 por grupo)" e
  "Planilhas"; a caixa de fala mostra o andamento real (grupo, processo X de Y, gasto) e o
  Jarvis vai à Leitura dos processos e às Planilhas enquanto trabalha.
- `bot/jarvis.py` + rotas `/jarvis`, `/jarvis/status`, `POST /jarvis/rodar` e
  `/jarvis/planilha/<mês>/<arquivo>`: o Ultron roda o Jarvis da pasta `JARVIS_PASTA` em segundo
  plano (como o Zangão) e lista as planilhas para baixar. Botão "Jarvis" no topo da página do Ultron.
- `bot/vila_aviso.py`: o relatório manda o andamento por `POST /eventos` (bot `jarvis`, só
  contagens; `VILA_URL` e `VILA_SENHA` no `.env.usuario2`). `eventos.py` aceita o bot `jarvis`.
- `--limite` (teste) salva em `AAAA-MM/teste/`, sem substituir a planilha do mês.
- Se o navegador não abre, o relatório avisa a vila ("parou") em vez de sumir.
- Testado no PC com a página de demonstração: clique em "Testar" na vila → 2 grupos, 4
  processos, US$ 0,06, andamento ao vivo e as planilhas na página /jarvis.

### Adicionado — Jarvis na Vila 04 (04/11/2026)
- A vila passa de 3 para 4 vilas: a Vila 04 é do **Jarvis**, o robô do relatório mensal de
  processos (segundo usuário do VIOS). Ela fica acesa, com placas próprias (Doca 01 · Jarvis,
  Leitura dos processos, Planilhas, Torre VIOS), e o Jarvis faz a ronda com o mascote dele
  (carmesim e dourado, com propulsores) e se apresenta no diálogo. A Vila 03 continua vaga.
- `doc/vila/ligar_jarvis.py` aplica a mudança no `bot/vila/vila.html` (como o `ligar_zangao.py`).
- Ainda sem eventos: o Jarvis aparece sempre como "Ocioso".

### Alterado — Mascote do Jarvis: núcleo de IA (04/11/2026)
- O Jarvis passa a ser um núcleo de IA em pixel: esfera azul em espiral girando, dois anéis
  tracejados e o centro pulsando (versão em miniatura do `nucleo-ia.html`). O mascote com
  propulsores continua no script: `ligar_jarvis.py bot/vila/vila.html propulsor`.

### Adicionado — Albi: sessão em conflito e tela de novo pedido (04/11/2026)
- Se o login cair em `/login-conflito` (sessão aberta em outro lugar), o Albi clica em "Encerrar
  a outra sessão"; se o Sonar voltar para a tela de login, entra de novo. Botão configurável em
  `CONFLITO_BOTAO` (vazio = padrão).
- Depois do login vai direto para `/modulos/pesquisa-processos/novo-pedido` (a tela do botão
  "Iniciar Pesquisa") e confirma que ela abriu. Testado no Sonar real, passando pela tela de
  conflito.

### Corrigido — Albi: login no Sonar (04/11/2026)
- Os seletores dos campos (`css:#loginform #input-cpf-cnpj` etc.) eram cortados no `.env`: sem
  aspas, tudo depois de " #" vira comentário, e o seletor virava só `#loginform`. O Albi tentava
  digitar no formulário inteiro e parava com "invalid element state". Agora são escritos sem
  " #" (`css:#loginform input[id=input-cpf-cnpj]`, `css:#loginform [id=btn-login]`, ...) em
  `albi/main.py` e `albi/.env.example`. Testado com as credenciais reais: "Login OK".

### Segurança — Revisão de chaves e rotas (03/11/2026)
- Conferido: nenhuma chave nem senha no repositório nem em todo o histórico do git (os 3 ramos):
  as chaves da OpenAI e da Anthropic, o usuário e a senha do VIOS e a senha da página não aparecem
  em nenhum commit; o `.env` nunca foi commitado. A página de revisão só atende no próprio
  computador (`127.0.0.1`). No servidor do Mac, as 17 rotas da página de envio (GET e POST)
  respondem 401 sem a senha.
- Corrigido: POST vindo de outro site é recusado (403) em todas as rotas (`barrar_outro_site` em
  `bot/envio_web.py`). Antes, um site aberto no mesmo navegador poderia disparar
  `/envio/<id>/enviar`, `/salvar`, `/ler` ou `/eventos` usando a senha guardada pelo navegador
  (CSRF). Pedido sem Origin/Referer (o Zangão, em `POST /eventos`) continua decidido só pela senha.
- Retirado do `CHANGELOG.md` o número de um processo real usado como exemplo (continua no
  histórico do git, no commit `b1bb149`).

### Adicionado — Albi, bot do Sonar (pasta `albi/`)
- Começou com o nome Jarvis (pasta `jarvis/`); renomeado para Albi em 04/11/2026.
- Novo bot, separado do Ultron e do Zangão: tudo em `albi/` (`.venv`, `.env`, `logs/`,
  `saida/` próprios; não importa nada do `bot/`). Entra em https://sonar.lemeforense.com.br/login
  com CPF/CNPJ, e-mail e senha e confirma o login. As próximas etapas ainda vão ser definidas.
- `albi/.env.example` explica como pôr as credenciais (`SONAR_CPF_CNPJ`, `SONAR_EMAIL`,
  `SONAR_SENHA`; senha com espaço ou " #" entre aspas simples). Campos da tela conferidos na
  página real e presos ao formulário `#loginform` (a página tem outro formulário, o de
  recuperar senha, com campos de mesmo nome).
- `albi/instalar.sh`, `albi/rodar.sh`, `albi/requirements.txt` e `albi/README.md`.
  O log nunca mostra a senha nem o CPF/CNPJ inteiro.

### Alterado — Vila dos bots no topo da página do Ultron
- As telas do Ultron (inicial e do envio) mostram no topo a vila dos bots (a mesma `/vila`, com
  os eventos reais, aberta na Vila 01) no lugar da cena pequena; abaixo continua tudo igual
  (caixa do .txt, conferência, enviar/testar, edição das CIs, histórico). `bot/templates/_vila.html`
  (`vila_cartao(n)`).
- Vila: `/vila?vila=N` abre direto na vila N; ao abrir, os eventos dos últimos 30 s são animados
  (a página recarrega logo depois de subir o .txt, e o Ultron aparece indo buscar o arquivo e
  conferindo). Etapa 4 do `doc/vila/ligar_zangao.py`.

### Alterado — Zangão roda pela própria vila (Vila 02)
- A Vila 02 (vila do Mac, `/vila`) voltou a ter os botões para rodar o Zangão: "Testar sem
  gravar" (qualquer dia, não grava) e "Rodar e gravar no VIOS" (só nos 3 últimos dias do mês; o
  1º clique vira "Confirmar: gravar no VIOS", válido por 6 s), além de "Abrir painel". Enquanto
  ele roda, os botões somem e o rodapé diz desde quando. Chamam as mesmas rotas da página
  (`/zangao/status` e `POST /zangao/rodar`). Etapa 2 do `doc/vila/ligar_zangao.py`.
- A página `/zangao` continua como alternativa (botão "Zangão" no topo do Ultron).
- A vila do GitHub (`ruanpereiradev.github.io/autobots`) continua só em simulação: a que mostra e
  roda os bots de verdade é a do Mac (`http://<IP do Mac>:5001/vila`).

### Adicionado — Página do Zangão no servidor (como a do Ultron)
- `/zangao` (`bot/templates/zangao.html`): a mesma tela da página do Ultron, nas cores do
  Zangão. Cena no estilo da vila (Doca 01 · Zangão, Filtro previdenciário, Captura de dados e
  Torre VIOS) com o Zangão da vila (`_zangao.html`, mesmo desenho e cores da Vila 02) andando
  conforme o andamento real; etapas Entrar no VIOS → Ler o calendário → Processar tarefas →
  Resumo; fala com o que ele está fazendo; placa de tarefas na torre.
- Botões "Testar sem gravar" (qualquer dia; `main.py --fora-da-janela`, não grava) e "Rodar e
  gravar no VIOS" (só nos 3 últimos dias do mês; o 1º clique vira "Confirmar: gravar no VIOS",
  válido por 6 s; `main.py --confirmar`). Uma execução por vez; os botões travam enquanto roda.
- Cartão da execução atual/última, ao vivo (a cada 1,5 s): barra, contagens e uma linha por
  tarefa (situação, processo, campos, motivo em português; as ignoradas ficam recolhidas).
  `/zangao/historico` lista as execuções e `/zangao/execucao/<id>` mostra uma.
- `bot/zangao.py`: roda o Zangão (instalado em `ZANGAO_PASTA`, com `.venv` e `.env` dele) em
  segundo plano, como processo separado (continua se a página reiniciar), com ambiente limpo
  (nenhuma variável do Ultron, como senhas e chaves, chega ao Zangão); monta as execuções dos
  eventos `bot: "zangao"`. Rotas `/zangao/andamento`, `/zangao/status` e `POST /zangao/rodar`
  (só aceita pedido da própria página: JSON e mesma origem). Saída de cada execução em
  `<ZANGAO_PASTA>/logs/execucoes_vila.log`.
- Página do Ultron: botão "Zangão" no topo (quando `ZANGAO_PASTA` está definida). O estilo das
  páginas foi para `bot/templates/_estilo.html` (o mesmo nas duas). A placa dos prédios da cena
  aceita largura maior (`predio(..., placa=)`), sem mudar a do Ultron.
- Vila 02: botão "Página do Zangão" (a vila continua só assistindo) e o rodapé diz se ele está
  rodando. Etapa 2 do `doc/vila/ligar_zangao.py`.
- Nova variável `ZANGAO_PASTA` no `.env`/`.env.example` (vazia = sem página/botão do Zangão).

### Corrigido — Vila parada depois de um envio com a aba escondida
- Com a aba da vila em segundo plano o Chrome pausa as animações e consulta `/eventos` só uma
  vez por minuto (visto no envio de 03/11 às 14:06: 77 eventos acumulados). Ao voltar, o
  Ultron reprisava o envio inteiro passo a passo e parecia parado. Agora, ao voltar para a aba
  ou com mais de 20 eventos na fila (30 no Zangão), a vila aplica o que faltou sem animar e põe
  o robô no lugar certo ("Último envio: … · 26 gravadas"). Cada evento é aplicado uma vez só.
  Etapa 3 do `doc/vila/ligar_zangao.py`.

### Adicionado — A vila recebe e mostra o Zangão (Bumblebee)
- `POST /eventos` no Ultron (`bot/envio_web.py` + `eventos.receber`): recebe os eventos do
  Zangão (branch `bot-edita-vios`, `bot/vila.py`) com a mesma senha da página e grava no
  `saida/eventos.jsonl`. Só aceita `bot: "zangao"`; valida tamanho (64 KB), `envio` e `tipo`;
  o `n` é sempre do Ultron; guarda o `ts` do Zangão; retira chaves de dados de cliente e
  textos no formato CNJ (garantia, o Zangão já não manda). Testado com o `bot/vila.py` real:
  eventos gravados, senha errada recusada (401), 4 threads × 20 eventos sem `n` repetido.
- Vila 02 (`bot/vila/vila.html`, modo servidor): anima a execução real do Zangão (entrar no
  VIOS, ler o calendário, classificar, cada tarefa e o resumo), com painel "Comprovantes
  previdenciários" (tarefa pelo `pxe_id`, processo pelo id interno, situação e motivo em
  português) e linha no Registro. Ao abrir, mostra a última execução. Testado no Chrome com
  eventos de verdade; a Vila 01 (Ultron) e o modo simulado não mudaram.
- `doc/vila/ligar_zangao.py`: reaplica essa mudança se a vila for baixada de novo do site.
- `doc/vila/contrato-eventos.md`: seção do Zangão (rota, validação e o que a vila mostra).

### Adicionado — Prompt do contrato de eventos do Zangão (Bumblebee) para a vila
- `doc/vila/prompt-zangao.md`: o que o bot de comprovantes previdenciários (Bumblebee/Zangão)
  precisa emitir para a Vila 02 mostrá-lo trabalhando. Eventos com `bot: "zangao"`
  (`execucao_iniciada`, `fase`, `calendario`, `tarefa`, `execucao_fim`), enviados por
  `POST /eventos` ao servidor do Ultron, com dados mínimos (sem CNJ, órgão, valor nem nome de
  cliente) e sem nunca travar o bot.
- Pendente do lado do Ultron: rota `POST /eventos` e a vila passar a ler os eventos do Zangão
  (hoje ela só lê `bot: "ultron"`).

### Adicionado — Mac como servidor da página de envio (`servidor_mac.sh`)
- `./servidor_mac.sh instalar` cria um serviço do `launchd` (`~/Library/LaunchAgents/
  br.automacao-vios.envio.plist`) que roda o `./rodar_envio.sh` sozinho quando o usuário entra
  no Mac, religa se cair (`KeepAlive`) e usa `caffeinate -i` para o Mac não dormir enquanto roda.
- `parar` desliga e tira do login; `status` mostra se está rodando; `log` acompanha
  `logs/servidor.log`.
- Avisa se o `.env` não tem `ENVIO_REDE=true`/`ENVIO_SENHA` ou se falta
  `saida/lancamentos.json`.
- Reinstalar com o serviço já ligado dava `Bootstrap failed: 5: Input/output error`: agora
  espera o `launchd` soltar o serviço antes de ligar de novo, confere o `.plist` (`plutil`) e
  avisa se a porta 5001 está ocupada por outro programa.

### Corrigido — `instalar.sh` recria a `.venv` copiada do Linux
- A checagem antiga só rodava o python da `.venv`; no Mac o `/usr/bin/python3` existe, então
  uma `.venv` trazida do Linux passava e ficava com o Python errado e sem os pacotes. Agora o
  script compara a versão gravada em `.venv/pyvenv.cfg` com a do Python escolhido e recria a
  `.venv` se forem diferentes.

### Alterado — Página do envio com a cena do Ultron (estilo da vila)
- `bot/templates/_cena.html`: cena em pixel-art como a vila (piso metálico, canos de cobre,
  Doca 01, Receptor TXT, Conferência e Torre VIOS), **só com o Ultron**, no topo da página do
  envio. Etapas 01 Arquivo subido → 02 Conferido → 03 Envio aprovado → 04 Criando no VIOS,
  etiquetas de status e caixa de fala do Ultron.
- O Ultron anda conforme o andamento real (`/envio/<id>/status`): ao subir o arquivo, sai da
  doca, pega o papel no Receptor e leva à Conferência (a tela acende) e diz quantas CIs estão
  prontas; no envio, vai à Torre VIOS (sinal e luz piscando, placa com tarefas feitas/total) e
  fala o que está fazendo (entrando no VIOS, conferindo duplicatas, "CI X: preenchendo a
  tarefa 2 de 2, ..."); no fim, volta à doca e comemora, ou treme se houve erro / se parou.
- A página inicial também tem a cena: o Ultron espera na Doca 01 e explica o que fazer (ou avisa
  que está ocupado com outro envio). Ao soltar ou escolher o .txt (na caixa ou em cima da
  cena), ele vai buscar o arquivo no Receptor, e a página do envio continua dali, levando o
  papel à Conferência. O mascote da caixa de envio ficou menor (o Ultron principal é o da cena).
- O mascote e a barra do painel antigo saíram (a cena mostra o Ultron); a lista das tarefas
  ao vivo e o resumo final continuam abaixo. No celular, a fala fica embaixo da cena.

### Alterado — Navegador um pouco mais rápido (`NAVEGADOR_RAPIDO`)
- `NAVEGADOR_RAPIDO=true` (padrão; `.env.example`): o Chrome usa `page_load_strategy="eager"`
  (o `driver.get` não espera recursos que o robô não usa; as esperas do robô continuam).
  As esperas do login, da navegação e do lançamento olham a tela a cada 0,1 s (antes 0,5 s).
- Medido no VIOS com o `ultron_teste_vios.txt` (sem gravar), alternando os modos no mesmo
  momento: ~3% mais rápido. O tempo é quase todo do servidor do VIOS (~1,5 s por Adicionar,
  ~1,2 s para abrir o lançamento, ~0,7 s a Conferência nos horários bons; o dobro ou mais nos
  lentos). Bloquear as imagens foi descartado: ganha pouco e o VIOS deixa de desenhar os
  botões "Texto intimação" e "Concluir tarefa?", que são a prova no print.
- Testado também que o VIOS aceita duas sessões simultâneas do mesmo usuário (base para
  lançar em paralelo, ainda não feito).

### Adicionado — Vila instalada em `/vila`
- `autobots/` (clone do repositório da vila, que tem o git próprio) entrou no `.gitignore`.
- `bot/vila/vila.html`: cópia da vila publicada em https://ruanpereiradev.github.io/autobots/
  (HTML único, com React e fontes embutidos; não depende de internet). Servida pelo Ultron
  em `/vila`, na mesma origem e com a mesma senha, lendo `/eventos` a cada 2 s.
- Corrigido na cópia: o ajuste "fonte" da vila tem padrão `simulado` e ganhava da regra
  "em `/vila`, usar o servidor", então ela nunca lia os eventos. Agora, em `/vila`, usa
  sempre o servidor; fora dele (GitHub Pages), continua como antes. A correção precisa ir
  também para o código-fonte da vila, senão some quando a cópia for atualizada.
- A versão no GitHub Pages serve só para a simulação: ela não alcança o Ultron (página
  HTTPS na internet × Ultron HTTP na rede interna).
- Testado com o VIOS simulado: a vila acompanhou arquivo subido → conferido → envio (teste) →
  tarefas no quadro/erro → finalizado.

### Adicionado — Eventos para a vila (`/eventos` e `/vila`)
- `bot/eventos.py`: `emitir()` acrescenta cada evento em `saida/eventos.jsonl` (uma linha JSON,
  `n` sequencial, `ts`, `bot`, `envio`, `tipo`), com `threading.Lock` + `fcntl.flock`; erro ao
  gravar evento só vai para o log. `ler()` devolve `{"ultimo", "eventos"}` com `n > desde`
  (no 1º acesso, os últimos 500).
- A página de envio emite os 6 tipos do contrato (`doc/vila/contrato-eventos.md`):
  `arquivo_subido`, `conferido` (também depois de editar), `envio_iniciado` (`gravar`/`teste`),
  `fase` (`entrando_vios` → `conferindo_duplicatas` → `criando_tarefas`), `ci` por tarefa
  (`no_quadro`, `gravada` com `tarefa_num` = `"<CI>-<posição>"`, `erro` com motivo, `ja_tinha`,
  `duplicata`) e `envio_fim` (`concluido`/`testado`/`parou`). Só CI, tarefa e contagens.
- Rotas novas com a mesma senha: `GET /eventos?desde=N` e `/vila` (serve `bot/vila/vila.html`;
  sem o arquivo, mostra um aviso).
- O log do lançamento passa a guardar o motivo do erro (texto da exceção) nos detalhes da CI.
- Testado com o VIOS simulado (gravar e teste) e com 3 processos × 4 threads gravando ao mesmo
  tempo (1.200 eventos, `n` sem repetir).

### Adicionado — Arquivo de teste (`MODO: TESTE`)
- `.txt` que começa com a linha `MODO: TESTE` só pode ser testado: a página mostra só
  "Testar sem gravar" e o servidor recusa gravar mesmo se pedirem (`so_teste` no envio).
  Para ver o Ultron preenchendo o VIOS com intimações reais sem risco.

### Corrigido
- A lista oficial da skill tem `SUSTENTAÇÃO ORAL PPREVIDENCIÁRIO) 2026` (erro de digitação);
  o nome certo do VIOS, `SUSTENTAÇÃO ORAL (PREVIDENCIÁRIO) 2026`, era recusado na página de
  envio. Novo apelido em `APELIDOS` (`bot/lancamento.py`) e a página aceita os nomes certos
  dos apelidos.

### Alterado — Mascote novo do Ultron ("Crista")
- Mascote trocado pelo desenho "Crista": robô cromado com o corpo do mascote do Claude e
  expressão de máquina hostil, em grade 16 × 12 com paleta fixa (brilho, base e sombra do
  metal; olhos vermelhos com núcleo claro). A grade e a paleta ficam editáveis no topo de
  `bot/templates/_ultron.html`.
- Animação como na especificação (tick de 100 ms): pulso do brilho dos olhos
  (0,6 + 0,4 × sin(t/4), raio 0,8 e 1,4 pixel), piscar (t % 46 < 2) e flutuar 1/3 de pixel
  a cada 6 ticks. Trabalhando, o tempo corre 2× e braços e pernas mexem; no fim, pula
  (deu certo) ou treme com os olhos falhando (houve erro).
- Cada cor é desenhada como um traçado só e os tamanhos são múltiplos de 48 px, para não
  aparecer linha entre os pixels. Ícone da aba com o mascote.
- `doc/mascote/`: `mascote.html` (HTML + CSS + JS puro, com a grade e a paleta para editar
  e a animação), `mascote.svg` (estático, com brilho nos olhos) e `mascote.png` (512 × 512).

### Corrigido — Histórico de envios não some mais
- A lista "Envios desta sessão" ficava só na memória e sumia ao reiniciar a página
  (o registro das tarefas gravadas, `saida/lancamentos.json`, nunca foi perdido).
  Agora cada envio é gravado em `saida/envios/<data_hora>_<id>.json` (escrita
  atômica) ao subir, ao salvar edições, ao começar, a cada CI concluída e no fim; a
  página carrega tudo ao iniciar. Envio interrompido por reinício aparece como
  "Parou", com as CIs sem resultado marcadas para conferir no VIOS.
- Nova página **Histórico** (`/historico`, botão no topo): todos os envios (quando,
  arquivo, CIs/tarefas, gravadas/erros/duplicadas, situação) e todas as tarefas
  gravadas no VIOS (`lancamentos.json`), com busca por CI, tarefa ou responsável. A
  tela inicial mostra os últimos 8 envios.
- Os 3 envios feitos pela página antes desta mudança (29/10 13:42 teste com 18 CIs,
  29/10 15:30 com 26 gravadas, 30/10 14:51 com 25 gravadas) foram reconstruídos do
  `logs/bot.log`; ficam só para consulta (sem descrição das tarefas, não reenviam).

### Alterado — Página de envio com a cara do Ultron (30/10/2026)
- O bot agora se chama **Ultron**. A página de envio (`bot/templates/envio.html`) ganhou
  tema escuro e o mascote do Ultron (`bot/templates/_ultron.html`): pixel-art no formato
  do mascote do Claude Code, em metal, com olhos e boca vermelhos.
- Caixa de envio: arrastar o `.txt` ou clicar para escolher; a leitura começa sozinha
  (sem o botão "Ler arquivo"). O resto do fluxo não mudou: conferir → Enviar ao VIOS.
- Envio acompanhado ao vivo, sem recarregar a página: fase (entrando no VIOS,
  conferindo duplicatas, criando as tarefas), barra de progresso por tarefa e cada CI
  com as suas tarefas (na fila → criando → no quadro → gravada / erro). Novo endpoint
  `/envio/<id>/status` (JSON) em `bot/envio_web.py`; a tarefa conta como criada quando
  o log do lançamento registra "CI X tarefa N".
- Mascote animado: flutua parado, "digita" e varre com os olhos enquanto trabalha,
  pula e acena no fim e treme quando há erro. Resumo final com CIs gravadas, com erro
  e duplicadas.
- Testado com o VIOS simulado (5 CIs: gravada, erro, com problema, várias tarefas) e
  na largura de celular.

### Alterado — Skill nova da Controladoria (30/10/2026)
- `doc/analise-intimacoes-controladoria/` trocada pela skill revisada (cópia em
  `doc/skill-original/6_2026-10-30_contagem-simplificada/`, com o `.zip` recebido;
  `LEIAME.md` resume as mudanças): contagem simplificada (só sábado e domingo
  ficam de fora, feriados contam), corte das 12h para análise/ciência,
  `PRAZO DE EMBARGOS:`/`PRAZO DE RECURSO:` sempre com data, `PRAZO FATAL D -2:`
  nas minutas, `PRIORIDADE RPV` de volta na descrição.
- Nova referência `validacao-lancamento.md` em `bot/skill.py` (prompt do bot e
  skill única).
- `gerar_skill_unica.py`: troca os links markdown `[x.md](references/x.md)` e as
  menções a "SKILL.md" pelo nome da seção. Skill única regerada.
- `doc/skill-unica/regras-do-programa.md` reescrito: agora descreve só o que o
  robô confere e bloqueia no envio do `.txt` (as regras de data e descrição são
  as da skill). `arquivo-para-o-robo.md` e `pedido-arquivo-robo.txt` com os
  rótulos novos e exemplos recalculados (conferidos pelo leitor do robô).
- `bot/analise.py`: `PRIORIDADE RPV`/`PRIORIDADE EMENDA` saíram da lista de
  linhas proibidas na descrição (a página de envio não avisa mais).
- Pendente: a análise pela API (`bot/prazos.py`, `bot/analise.py`) ainda usa as
  regras antigas de data e descrição.

### Adicionado — Rodar no Mac e no Linux
- `instalar.sh`: cria a `.venv` (recria se veio copiada de outro computador),
  instala as dependências, cria `saida/` e `logs/` e avisa se faltar `.env` ou o
  Chrome. Exige Python 3.8 a 3.12 (procura o `python3.12` primeiro). Testado no
  Linux numa cópia limpa; pacotes conferidos para Mac (Apple Silicon e Intel)
  com Python 3.12.

### Alterado
- `rodar*.sh`: `cd "$(dirname "$0")"` no lugar de `readlink -f` (não existe em
  macOS antigos).

### Removido
- `pkg_resources==0.0.0` do `requirements.txt` (resto do Ubuntu; o `pip` falha
  com ele no Mac).

### Adicionado — Skill original recuperada
- `doc/skill-original/`: as versões da skill ao longo do tempo, uma pasta por
  versão (skill aberta + `.zip`), para a Controladoria achar em qual momento a
  análise esteve melhor: 1 original (23/10, idêntica ao pacote de 20/10),
  2 prazo em lei (26/10), 3 revisão de 27/10, 4 revisão de 28/10 (reconstruída
  do texto enviado à IA naquele dia; mesmo tamanho do `SKILL.md` de então) e
  5 atual (29/10). `LEIAME.md` resume o que muda de uma para a outra. A skill
  que o bot usa continua em `doc/analise-intimacoes-controladoria/`.

### Adicionado — Duplicatas conferidas na leitura e no envio
- **Na leitura:** a captura (`main.py`) marca a cópia em `intimacoes_*.json`
  (`duplicada_de`, `duplicidade_motivo`) e registra no log "CI X é cópia da
  CI Y".
- **No envio do .txt:** ao subir, a página confere com as capturas salvas (e com
  o que a análise marcou). Na hora de enviar, o robô lê no VIOS o teor, o
  processo e o cliente de cada CI do arquivo (`ler_intimacao`, tela "Lançar
  Intimação", só leitura) e compara com as outras CIs do arquivo e com as
  capturas: cópia de CI já lançada ou que está no arquivo não é gravada
  ("Duplicata (não lançada)"); cópia de CI que não está no arquivo nem foi
  lançada vira erro para a pessoa conferir. Funciona para CI que o robô não
  capturou.
- `bot/duplicidade.py` compara só o teor (`teor()`: sem o cabeçalho de datas e
  sem Comarca/Diário/Esfera depois do comunicacao_id), para o texto da tela de
  lançamento bater com o da captura (antes: 24 palavras diferentes; agora 0).
  Duplicatas das capturas salvas continuam as mesmas (42501 → 42500).
- Skill: a regra de duplicidade explica os dois momentos e pede para o chat
  também não colocar a cópia no arquivo para o robô.
- Testado com o VIOS simulado: cópia de CI do arquivo, cópia de CI já lançada
  (texto real da 42501) e CI normal.

### Adicionado — Página de envio do .txt (sem gastar tokens da API)
- `./rodar_envio.sh` (http://127.0.0.1:5001): a pessoa sobe o `.txt` com as
  tarefas já ajustadas (análise feita no chat com a skill única), confere a
  tabela e clica em **Testar sem gravar** ou **Enviar ao VIOS**. O robô só
  lança, sem chamar a IA. Novos `bot/envio_txt.py` (leitura e conferência),
  `bot/envio_web.py`, `bot/templates/envio.html`, `enviar.py`.
- O `.txt` não é enviado quando a CI tem problema (tarefa fora da lista
  oficial, data ou horário inválido, audiência/perícia/sustentação sem
  horário, responsável fora da lista do VIOS, descrição vazia, linha fora do
  formato) ou já foi lançada. Avisos: data passada, fim de semana, linhas que a
  Controladoria pediu para não usar na descrição.
- Skill única: nova seção "Arquivo para o robô (.txt)"
  (`doc/skill-unica/arquivo-para-o-robo.md`), para o chat entregar o arquivo
  pronto. O exemplo da seção foi conferido pelo leitor do robô.
- Testado com o VIOS simulado (leitura, teste, envio, CI já lançada, CI com
  problema, arquivo salvo em ANSI). Falta o primeiro envio real.
- Edição dos erros na própria página: depois de subir o `.txt`, cada tarefa vira
  um formulário (CI, tarefa com a lista oficial, data, hora, responsáveis,
  descrição, remover). **Salvar e conferir** refaz o `.txt` e confere de novo;
  **Editar como texto** para colar/acrescentar blocos. Envio bloqueado enquanto
  houver alteração não salva. Mensagens de problema sem número de linha.
- CI que a análise do bot marcou como cópia (`duplicada_de`) não é enviada pela
  página: aparece com o problema "cópia da CI X" (caso da 42501, cópia da
  42500 já lançada, que veio no arquivo de 29/10). Campo Data da CIÊNCIA
  mostra "vazio = dia do envio".
- Página de envio disponível na rede (`ENVIO_REDE=true` ou `--rede`), em
  `http://<IP da máquina>:5001`.
- **Segurança:** na rede a página exige senha (`ENVIO_SENHA`, autenticação
  básica do navegador); sem senha ela não abre na rede, porque grava no VIOS
  com o usuário do robô. Variáveis novas no `.env.example`.
- `doc/skill-unica/pedido-arquivo-robo.txt`: texto pronto para colar no chat
  depois dos ajustes, pedindo o arquivo no padrão (regras + exemplo conferido
  pelo leitor do robô).

### Alterado — Correções da revisão de 29/10 (análises de 27/10)
- Descrição da tarefa sem `Responsável a marcar na tarefa: BRENO`,
  `Advogada auxiliar: TAMIRA` e `PRIORIDADE RPV/PRECATÓRIO` (caso da CI 42484).
  Breno continua marcado como responsável no VIOS. A skill não pede mais essas
  linhas e o código as apaga se a IA ainda escrever (`FORA_DA_DESCRICAO`).
- Audiência no padrão da Controladoria, uma informação por linha e sem
  parágrafos ou `OBS:`: `AUDIÊNCIA [TIPO]`, `DATA`, `HORA`, `FORMATO`,
  `LINK/LOCAL` (só o link ou o endereço), `ID da reunião` e `SENHA` (só na
  virtual). Caso da CI 42502. Ajustados `SKILL.md`, `pop-fluxo-intimacoes.md`,
  `tarefas-vios.md` e o adendo do bot.
- Sentença ou acórdão sempre gera `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO`, nunca
  minuta: regra explícita na skill e bloqueio no código (não lança se faltar a
  tarefa de análise).
- Pacotes `.zip` da skill e da skill única gerados de novo.

### Adicionado — `gerar_skill_unica.py`
- Monta a skill única a partir da skill do bot (`SKILL.md` + referências) e de
  `doc/skill-unica/regras-do-programa.md`, e gera o `.zip`. Evita editar duas
  cópias da mesma regra.

### Alterado — Correções da revisão de 28/10 (análises de 26/10)
- Tarefa `ANALISAR SENTENÇA/ACÓRDÃO/DECISÃO` passa a ficar para o **mesmo dia**
  (antes ia para o D-2 mais cedo entre embargos, recurso e prazo). As datas de
  embargos e recurso (D-2) continuam na descrição; a linha `PRAZO FATAL (D-2)`
  sai quando há essas duas linhas. Skill (`SKILL.md`, `regras-prazos-recursos.md`,
  `pop-fluxo-intimacoes.md`) e `bot/analise.py` ajustados.
- Tarefas com horário (sustentação oral, audiência, perícia) ficam na data
  exata do ato, nunca no D-2; na sessão virtual, o 1º dia da sessão. Modelo da
  sustentação em sessão virtual na skill ("DATA: De 06/11/2026 a 13/11/2026.").
- Prazo previsto em lei para manifestação sobre laudo pericial: 15 dias úteis
  (art. 477, § 1º, CPC), inclusive no Juizado e no Previdenciário. Antes a IA
  usava 5 dias.
- No lançamento pela linha de comando, tarefa `MESMO_DIA` vai para o dia do
  lançamento (como já fazia a página de revisão).
- Pacote `doc/analise-intimacoes-controladoria.zip` gerado de novo com a skill
  atualizada (o anterior era de 23/10, com os arquivos de 20/10).

### Adicionado — Skill em arquivo único (para o chat de validação)
- `doc/skill-unica/analise-intimacoes-controladoria/SKILL.md` (e `.zip`): a skill
  e as 4 referências num arquivo só, mais a seção "Regras do programa" com o que
  o bot faz no código (contagem de prazo, D-2, data de cada tarefa, quando não
  lançar, alertas e duplicidade). Para a Controladoria usar no chat e comparar
  com as análises do bot. A skill que o bot usa continua em
  `doc/analise-intimacoes-controladoria/`; o arquivo único é uma cópia de 28/10.
- Na skill única, explicação de disponibilização × publicação (o arquivo leva a
  data de disponibilização; publicação no 1º dia útil seguinte).

### Alterado — Relatório mostra a disponibilização
- O relatório (`saida/analise_*.md`) mostra no cabeçalho a data de
  disponibilização e a de publicação, e cada CI mostra as duas. Antes só aparecia
  a publicação, e o chat de validação leu `analise_2026-10-27` (disponibilizadas
  em 27/10) com publicação em 28/10 como erro. O JSON da análise passa a guardar
  `disponibilizacao`.

### Corrigido — Aviso de CI original repetido
- A cada recálculo (`--recalcular`), o aviso "CI original: … cópia(s) desta" era
  gravado também na resposta salva da IA e se repetia no relatório (na CI 42500
  aparecia duas vezes). O aviso agora fica só no resultado; a resposta da IA de
  `analise_2026-10-27.json` foi limpa.

### Adicionado — Horário da tarefa no VIOS
- A IA informa `hora_informada` (HH:MM) e o bot preenche o campo Horário
  (`fo[hora_prevista]`) do formulário do VIOS, conferindo na tela. Respostas
  antigas usam o horário da linha "HORA:" da descrição.
- Página de revisão: campo Horário editável em cada tarefa.
- Tarefa com horário sem o horário não é lançada (bloqueio).

### Adicionado — Intimação que só indica o evento
- Intimação do eproc que só diz "O ato refere-se ao seguinte evento: Evento N"
  (sem o teor) não é lançada: a tarefa depende de abrir o evento no sistema
  (caso da CI 42478, lançada como CIÊNCIA quando era embargos/contrarrazões).

### Alterado — Planilha mensal: colunas revisadas pelo usuário
- Removidas da aba Processos: **Fase**, **Valor provisionado**, **Última
  movimentação** e **Pendência — responsável** (sigilo: tinha nomes da equipe).
- **Justificativa da condenação** passa a ser preenchida pela IA: se houve
  condenação, o motivo da decisão e o que o cliente tem que fazer; senão,
  "Sem condenação (pedidos improcedentes)", "Acordo" ou "Sem decisão até o
  momento". A aba Resumo ganha a contagem "Por resultado da decisão".
- "Documentos faltando": a IA nunca indica funcionário do escritório como
  quem entrega.
- Instrução da IA: só fatos do processo; opiniões, avaliações e estratégias
  internas registradas nas tarefas não vão para a planilha (o CI 28667 repetia
  "a condenação já está acima da média").

### Alterado — Relatório de processos vira planilha mensal (.xlsx) com a lupa de cada processo
- O .txt por grupo foi descartado. Agora `relatorio_processos.py` gera **uma
  planilha por grupo** em `saida_usuario2/relatorios/AAAA-MM/<GRUPO>.xlsx`, no
  formato da planilha "Processos Casa do celular" do Drive (abas Processos,
  Resumo, Cadastro incompleto e Metadados), + um `.json` com o que foi lido.
- Novo `bot/processos_detalhe.py`: abre a lupa de cada processo
  (`processos-vis.php`) e lê os Dados do Processo e as tarefas. O "Mostrar
  mais" é resolvido tirando a classe `limite-texto` (sem clicar).
- Novo `bot/relatorio_planilha.py`: última movimentação e pendências com
  responsável por regra fixa (tarefa em aberto vencida = ATRASADA); resumo do
  caso, motivação (lista fixa), financeira e documentos faltando pela IA
  (Claude, `claude-sonnet-5-5`). CPF, links e senhas das tarefas são tirados
  antes da IA e o texto das tarefas não vai para a planilha.
- Colunas novas: Cliente, Polo do cliente, Fase, Motivação do processo,
  Justificativa da condenação, Pendência — documentos faltando e Pendência —
  responsável. "ID da extração" vira CI. Valor provisionado e justificativa
  da condenação ficam vazios por enquanto.
- `.env.usuario2`: `PROCESSOS_GRUPOS=CASA DO CELULAR|CASA DO CELULAR MG/SP`,
  `LLM_PROVEDOR=anthropic`, `LLM_MODELO`, `LLM_LIMITE_US=5`, `MANTER_ABERTO=false`.
  Opção `--limite N` para testar com poucos processos.
- `bot/processos_grupo.py` perde a montagem do .txt (fica a pesquisa e a lista).
- `requirements.txt`: `openpyxl==3.1.5` e `et_xmlfile==2.0.0`.
- Teste 03/11/2026: 3 processos da CASA DO CELULAR, 0 erros, US$ 0,04. Rodada
  completa: CASA DO CELULAR (101) + CASA DO CELULAR MG/SP (26), 0 erros,
  16 min, US$ 2,13.

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
  vermelho. A data continua a mesma (dia útil seguinte à publicação). Base: um processo
  real da Justiça Federal (número retirado do registro). Skill (`SKILL.md` e
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
