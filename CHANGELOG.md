# Changelog

Todas as mudanças do bot de intimações ficam registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

Tipos: **Adicionado**, **Alterado**, **Corrigido**, **Removido**, **Segurança**.

Como registrar: toda alteração entra primeiro em **[Não lançado]**; quando a
etapa estiver pronta e testada, vira uma nova versão com data.

---

## [Não lançado]

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
