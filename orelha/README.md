# Orelha — o relatório do dia, só lendo o VIOS

O Orelha é o assistente da equipe. Ele entra no VIOS, **só lê** e entrega um relatório do dia com
cinco partes: agenda, prazos atrasados, intimações esquecidas, processos parados e a conferência
das planilhas do Albi. O mascote é um vira-lata preto e caramelo de focinho grisalho, com chapéu fedora e monóculo de leitura, em homenagem ao Orelha, o cão comunitário da Praia Brava (desenho em
`mascote/ficha.html`), e ele aparece na **Vila 05** da vila dos bots.

É separado do Ultron, do Zangão e do Albi. Tudo dele fica nesta pasta (`.venv`, `.env`, `logs/`,
`saida/`) e ele não importa nada de `bot/` nem de `albi/`. Quando aproveita uma ideia dos outros,
copia o código para cá.

## Somente leitura: como o Orelha se protege

- **Bloqueio de envios** (`nucleo/navegador.py`, ideia copiada do Zangão). Ele é ligado no Chrome
  **antes de abrir o login**. O formulário de login é marcado pelo Orelha e passa, e a página que
  abre depois do login já vem bloqueada. Depois do login, o Orelha recarrega a página e confere o
  bloqueio. **Se o bloqueio não estiver ativo, nenhuma função roda.** Se ele cair no meio, a
  execução para. O bloqueio tem dois níveis:
  - **total** (o padrão): barra envio de formulário, `fetch`/XHR que não seja GET/HEAD e
    `sendBeacon`;
  - **pesquisa** (só dentro de `pesquisa_liberada`, para ler o calendário, que busca as tarefas
    por XHR POST): formulário e `sendBeacon` continuam barrados. O XHR/fetch POST passa, mas nunca
    para endereço de `ORELHA_URL_PROIBIDA` e, se `ORELHA_XHR_PERMITIDO` estiver preenchido, só para os
    endereços dessa lista.
- **A única exceção ao bloqueio de formulário** é o formulário que o próprio Orelha marca
  (`data-orelha-pesquisa="1"`): o do login e o das pesquisas (intimações, lista de processos,
  filtro do calendário, busca de processo). Antes de enviar uma pesquisa, o Orelha confere três
  coisas e recusa se alguma falhar: o endereço do formulário não está em `ORELHA_URL_PROIBIDA`, o
  botão que vai enviar não tem termo de `ORELHA_CLIQUE_PROIBIDO` (Salvar, Concluir...) e a tela é
  de pesquisa conhecida (`int-pesquisa.php`, `processos-lista.php`, `calendario.php` ou o que
  estiver em `ORELHA_PESQUISA_PERMITIDA`).
- **Endereços proibidos** (`ORELHA_URL_PROIBIDA`: `act=del`, `int-lanca.php`, `excluir`,
  `concluir`...) nunca são abertos.
- **Cliques proibidos** (`ORELHA_CLIQUE_PROIBIDO`) nunca são feitos. Os únicos cliques do Orelha são
  mês anterior/próximo e a visão do calendário.
- A senha fica só no `orelha/.env` (ignorado pelo git) e nunca vai para o log.
- A vila só recebe fases e contagens. Nome de cliente, de pessoa da equipe, número de processo e
  link não vão para os eventos (`nucleo/eventos.py` tira essas chaves e troca qualquer número CNJ
  antes de mandar).

## Instalar

```bash
cd orelha
./instalar.sh        # cria orelha/.venv (Python 3.12 ou o python3), instala selenium e python-dotenv
                     # e copia .env.example para .env, se ainda não existir
```

Precisa de **Python 3.10 ou mais novo** (o instalador recusa versão mais velha). No Linux que só
tem Python 3.8: `uv python install 3.12 && PYTHON=$(uv python find 3.12) ./instalar.sh`.

Também precisa do **Google Chrome**. O Selenium baixa sozinho o chromedriver compatível.

## Configurar (`orelha/.env`)

O modelo comentado, com **todas** as variáveis, é o `.env.example`. Para começar, basta:

| Variável | Para quê |
| --- | --- |
| `SISTEMA_USUARIO`, `SISTEMA_SENHA` | usuário do VIOS que o Orelha usa (de preferência um usuário só de leitura) |
| `SISTEMA_URL` | página de login (padrão: a do escritório) |
| `ORELHA_FUNCOES` | funções do relatório padrão (padrão: todas menos `parados`) |
| `HEADLESS` | `true` = Chrome sem janela (agendamento); `false` = dá para ver o que ele faz |
| `ORELHA_ALBI_SAIDA` | onde ficam os resultados do Albi (padrão `../albi/saida`) |
| `VILA_URL`, `VILA_SENHA` | vila dos bots (opcional): `http://<IP do Ultron>:5001/eventos` e a senha da página do Ultron |

Todo o resto pode ficar vazio, e vazio quer dizer o padrão. Os seletores são `css:...` ou
`xpath:...`. Variáveis com valor inválido param a execução com o nome da variável no erro, mas
nunca com o valor.

Grupos do `.env.example`:

- **acesso e login**: `SISTEMA_*`, `LOGIN_*`, `ORELHA_VIOS_BASE`;
- **execução**: `ORELHA_FUNCOES`, `HEADLESS`, `TIMEOUT`, `MANTER_ABERTO`, `ORELHA_SAIDA`, `ORELHA_LOGS`,
  `ORELHA_ALBI_SAIDA`;
- **proteções**: `ORELHA_URL_PROIBIDA`, `ORELHA_CLIQUE_PROIBIDO` (só acrescentar, nunca tirar),
  `ORELHA_BLOQUEIO_NO_LOGIN`, `ORELHA_XHR_PERMITIDO`, `ORELHA_PESQUISA_PERMITIDA`;
- **vila**: `VILA_URL`, `VILA_USUARIO`, `VILA_SENHA`, `VILA_TIMEOUT`;
- **funções**: `ORELHA_CALENDARIO_*`, `ORELHA_AGENDA_*`, `ORELHA_PRAZOS_*`, `ORELHA_INTIMACOES_*`,
  `ORELHA_PARADOS_*`, `ORELHA_PLANILHAS_*`. Os itens marcados "A CONFERIR" no `.env.example` ainda não
  foram vistos na tela real.

## Rodar

```bash
./rodar.sh                                   # relatório do dia (ORELHA_FUNCOES: agenda, prazos, intimacoes, planilhas)
./rodar.sh --funcoes parados                 # só os processos parados (lenta)
./rodar.sh --funcoes agenda,prazos           # só algumas funções
./rodar.sh --data 2026-11-03                 # relatório com outra data de "hoje"
./rodar.sh --sem-pdf                         # só o HTML e o resumo.json
./rodar.sh --eventos                         # cada evento da vila vira uma linha "@evento {json}" na saída
./rodar.sh --albi-saida ~/albi/saida         # outra pasta de resultados do Albi
./rodar.sh --env /caminho/outro.env          # outro arquivo de configuração
```

O resultado fica em `saida/<AAAA-MM-DD>/`:

- `relatorio.html`: uma página só, sem JavaScript nem arquivo externo. Abre em qualquer navegador,
  imprime e pode ir por e-mail. Tem nomes da equipe e de clientes, então é **interno**;
- `relatorio.pdf`: o mesmo HTML impresso pelo Chrome. Sem Chrome ou com `--sem-pdf`, fica só o HTML;
- `resumo.json`: os números de cada função, sem o texto dos itens;
- `eventos.jsonl`: os eventos da execução, os mesmos que vão para a vila;
- `planilhas-<data>.csv`: a conferência das planilhas do Albi (abre no Excel).

O histórico fica em `saida/historico/`: `prazos-<data>.json` (tendência), `parados-progresso.json`
(retomada) e `planilhas-conferidas.json` (o que já foi conferido). O log fica em `logs/orelha.log`.
A pasta `saida/` **não vai para o git**, porque o repositório é público.

Código de saída: `0` quando tudo deu certo, `1` quando alguma função deu erro ou a execução parou
(login, navegador, bloqueio), `2` quando a linha de comando ou o `.env` está errado. Uma função que
falha não derruba as outras: ela vira uma seção com o erro, e o relatório sai mesmo assim.

## Modo simulado (sem senha, sem VIOS)

```bash
./rodar.sh --simulado --sem-pdf --funcoes agenda,prazos,intimacoes,parados,planilhas   # grava em saida/simulado-<data>/
```

O simulado não abre o navegador. Ele lê `fixtures/` (dados 100% fictícios) e gera o relatório e
os eventos como numa execução de verdade. Serve para ver o Orelha funcionando e para testar a vila.
Ele não estraga o histórico real: os prazos usam `prazos-simulado-*.json`, os parados não gravam
o progresso e as planilhas não mexem no registro de conferidas.

Testes: `cd orelha && ../.venv/bin/python -m unittest discover -s tests` (ou `.venv/bin/python` depois
do `./instalar.sh`).

## As 5 funções

### 1. `agenda` — agenda de hoje e amanhã
- **Tarefas da equipe toda** (padrão `ORELHA_AGENDA_TAREFAS_FONTE=lista`): da lista de tarefas do VIOS
  (`pxe-lista.php`, por GET), as não concluídas com data para conclusão hoje ou amanhã cujo tipo
  **começa** com um dos `ORELHA_AGENDA_TERMOS` (AUDIÊNCIA, PERÍCIA, REUNIÃO, SUSTENTAÇÃO, OITIVA,
  DILIGÊNCIA). "INFORMAR AUDIÊNCIA" ou "LEMBRAR AUDIÊNCIA" ficam de fora: são tarefas sobre a
  audiência. A hora vem da faixa "(09:00 - 23:59)"; sem ela, "dia todo".
- **Do calendário**: compromissos (ex.: Reunião de Fechamento), feriados até domingo e, se ligado,
  aniversários. O calendário abre filtrado no usuário do Orelha e junta as tarefas por tipo; por
  isso as tarefas não vêm mais dele (dá para voltar com `ORELHA_AGENDA_TAREFAS_FONTE=calendario`).
- Audiência e perícia de hoje ficam em destaque ("atenção").

### 2. `prazos` — placar de tarefas atrasadas da equipe
Lê a **lista de tarefas** do VIOS (`?pag=sys/processos/pxe-lista.php`), a mesma para onde apontam
as tarefas agrupadas do calendário. Ela abre por GET, com os filtros no endereço, e sem responsável
no filtro traz a equipe toda (conferido na tela em 04/11/2026: 16 responsáveis numa só página).
São duas leituras, só de tarefas não concluídas (`pesq[flag_conclusao]=0`):
- `pesq[tp_data]=data_prevista` de `ORELHA_PRAZOS_DESDE` (padrão 01/01/2000) até ontem: as atrasadas;
- `pesq[tp_data]=data_limite` até hoje: as graves (limite vencido ou vencendo hoje).

De cada linha da tabela `#tarefas-lista` ele lê o tipo da tarefa, "Para conclusão" e "Limite" (coluna
Datas), os "Responsável(eis)" (coluna Envolvidos) e o link da tarefa (`pxe.php?pxe_id=`). O relatório
separa:
- **Vencem hoje** (grupo no topo, "para saber"): a data para conclusão ou a limite é hoje. Ainda dá
  para fazer hoje, então não conta como atrasada.
- **Atrasadas**, por responsável: a data para conclusão já passou. Por idade do atraso: até
  `ORELHA_PRAZOS_DIAS_GRAVE` dias (padrão 7) é "atenção"; mais que isso é "urgente".

Na 1ª rodada real (04/11/2026), a regra antiga ("limite vencido ou hoje" = urgente) deixava quase
tudo urgente, porque o limite costuma ser 1 dia depois da conclusão, e contava como atrasadas as que
vencem hoje (114 de 273). A tela mostra no máximo 1000 linhas; se vier cheia, a seção avisa. A tendência compara
com o registro de 7 dias antes (`historico/prazos-<data>.json`).

A leitura antiga, pelo calendário, continua disponível com `ORELHA_PRAZOS_FONTE=calendario`.

### 3. `intimacoes` — intimações esquecidas
Faz a pesquisa "Com Tarefa Lançada = Não" na mesma tela do Ultron (`int-pesquisa.php`), dos últimos
`ORELHA_INTIMACOES_DIAS` dias (padrão 15). Ficam de fora ontem e hoje, que o Ultron ainda vai tratar.
Com `ORELHA_INTIMACOES_SEGUIR_ULTRON=true` (o padrão), fica de fora também o que o Ultron trata no
dia: **na segunda o Ultron trata sexta a domingo, então o Orelha para na quinta**; no domingo, para na
sexta. Para excluir só ontem e hoje, use `false`.
Cada intimação vira um item (CI, processo, tribunal, cidade, cliente, advogado). Fica "grave" se foi
disponibilizada há mais de `ORELHA_INTIMACOES_GRAVE_DIAS` dias (padrão 5) e "atenção" se não. O grupo
é a data. A tela de lançamento nunca é aberta. Linhas apagadas, CIs repetidas e linhas fora do
período são contadas e ficam de fora.


**Como lê (conferido na tela em 04/11/2026):** a pesquisa de intimações é um formulário GET, então o
Orelha abre direto o endereço com "Com Tarefa Lançada: Não" (`pesq[processado]=0`), só as ativas,
por data de disponibilização, até 500 linhas. **Sem o filtro de Área**: marcar todas as áreas,
como o Ultron faz, deixava de fora as intimações sem área (no teste, 3 de 5, as mais antigas).

### 4. `parados` — processos parados
Usa o **filtro do próprio VIOS** na lista de processos (formulário GET): ativos, "Com ou sem tipo de
tarefa? = Sem", "Tipo de tarefa = Abertas", ou seja, processos ativos sem nenhuma tarefa aberta.
Não precisa abrir ficha por ficha. A tela devolve no máximo 500 por pesquisa; acima disso, o Orelha lê
por ano de cadastro e divide o que vier cheio. As páginas são buscadas por GET sem desenhar
(`nucleo/vios.buscar_get`): desenhar 500 linhas travava o Chrome do bot. Grupo = área; urgente = sem
edição há mais de `ORELHA_PARADOS_DIAS_GRAVE` dias (padrão 60). Conferido em 04/11/2026: 1818
processos; duas fichas sorteadas não tinham nenhuma tarefa aberta. A leitura antiga, ficha por ficha,
continua com `ORELHA_PARADOS_FONTE=fichas`.

### 5. `planilhas` — conferência das planilhas do Albi
Lê os `processos.csv` do Albi (`<albi/saida>/<AAAA-MM-DD_HHMMSS>/processos.csv`, coluna
"Processo"), só os que ainda não foram conferidos e só os dos últimos `ORELHA_PLANILHAS_DIAS` dias
(padrão 30). Cada número é procurado no VIOS e sai como:
- **ja_tem** (info): já está no VIOS, com o link da ficha;
- **novo** (atenção): não foi achado;
- **nao_achou** (atenção): não deu para conferir, porque o número está fora do padrão CNJ ou a
  busca falhou.

O grupo é a empresa. A função grava `planilhas-<data>.csv` e o registro
`historico/planilhas-conferidas.json`. Uma pasta com falha de busca volta na próxima execução, e
uma pasta que o Albi reescreveu é conferida de novo.
Busca em que o bloqueio barrou algum pedido, ou em que `ORELHA_PLANILHAS_BUSCA_PRONTO`/`_RESULTADO`
não apareceu, vira "não deu para conferir" e nunca "novo". Se `ORELHA_PLANILHAS_SUSPEITO` (padrão 10)
ou mais buscas derem certo e nenhuma achar o processo, o resultado é suspeito: a seção avisa e
nenhuma pasta é marcada como conferida.
Há dois modos de procurar (`ORELHA_PLANILHAS_MODO`). O `busca` (padrão) usa a busca do topo, um
número por vez, e **não está mapeado**. O `lista` faz uma pesquisa só na lista de processos e usa
campos já mapeados. Se não houver planilha nova, a seção diz "Nenhuma planilha nova do Albi" e o
Orelha nem entra no VIOS por causa dela.


**Busca no VIOS (padrão `ORELHA_PLANILHAS_MODO=url`, conferida em 04/11/2026):** a busca do topo pelo
endereço, com "Nro do Processo" (`campo_pesquisa_selecionado=nro_proc`) e "todos" os processos
(ativos e encerrados). Achou com e sem a máscara do CNJ; número inexistente volta sem linhas. Se a
resposta não for a tela de Processos (sessão caída), o número fica "não deu para conferir", nunca
"novo".

## Agendar

O relatório diário roda de segunda a sexta de manhã. Os `parados` rodam à parte, uma vez por
semana, porque são lentos. Use `HEADLESS=true` no `.env`.

**Escreva o mesmo horário no `.env`**: `ORELHA_HORARIO` (padrão `seg-sex 07:30`) e
`ORELHA_HORARIO_PARADOS` (padrão `sab 08:00`). Quem roda o Orelha é o agendamento abaixo; o horário
do `.env` serve para a Vila 05 e a página `/orelha` avisarem quando sai o próximo relatório e se o de
hoje atrasou. Se mudar um, mude o outro.

### Linux (cron)

`crontab -e` e acrescente (troque o caminho):

```cron
# Orelha: relatório do dia, seg a sex às 7h30
30 7 * * 1-5  /caminho/automacao-vios/orelha/rodar.sh >> /caminho/automacao-vios/orelha/logs/cron.log 2>&1
# Orelha: processos parados, sábado às 8h (300 fichas por vez, continua de onde parou)
0 8 * * 6     /caminho/automacao-vios/orelha/rodar.sh --funcoes parados --sem-pdf >> /caminho/automacao-vios/orelha/logs/cron.log 2>&1
```

### Mac: `./agendar_mac.sh` (um comando)

```bash
cd orelha
./agendar_mac.sh instalar   # cria os dois agendamentos com o horário do .env (rodar de novo se mudar o horário)
./agendar_mac.sh agora      # roda o relatório do dia agora, pelo agendamento, para testar
./agendar_mac.sh status     # instalados? resultado da última vez
./agendar_mac.sh log        # log do agendamento (logs/launchd.log)
./agendar_mac.sh parar      # tira os dois agendamentos
```

Ele lê `ORELHA_HORARIO` e `ORELHA_HORARIO_PARADOS` do `orelha/.env` (vazios = `seg-sex 07:30` e `sab
08:00`), então o agendamento e o aviso da vila/página `/orelha` ficam sempre iguais. Recusa se falta
`.venv`, `SISTEMA_USUARIO`/`SISTEMA_SENHA` ou se o horário é inválido, e avisa se `HEADLESS` não é
`true` ou se `VILA_URL` está vazio. No Mac do servidor, a vila é `VILA_URL=http://127.0.0.1:5001/eventos`
com `VILA_SENHA` = `ENVIO_SENHA` do Sam. O que ele cria é o mesmo que o modelo abaixo.

### Mac (launchd à mão, como o `servidor_mac.sh`)

O Chrome precisa de uma sessão aberta, então o Mac fica **com o usuário logado**, como no
`servidor_mac.sh` (Passo 22 da `DOCUMENTACAO.md`). Crie
`~/Library/LaunchAgents/br.automacao-vios.orelha.plist` (troque `/caminho`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>br.automacao-vios.orelha</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/caffeinate</string>
        <string>-i</string>
        <string>/caminho/automacao-vios/orelha/rodar.sh</string>
    </array>
    <key>WorkingDirectory</key><string>/caminho/automacao-vios/orelha</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUTF8</key><string>1</string>
    </dict>
    <!-- seg (1) a sex (5), 7h30: um dicionário por dia -->
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
        <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>
    </array>
    <key>StandardOutPath</key><string>/caminho/automacao-vios/orelha/logs/launchd.log</string>
    <key>StandardErrorPath</key><string>/caminho/automacao-vios/orelha/logs/launchd.log</string>
</dict>
</plist>
```

Ligar: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/br.automacao-vios.orelha.plist`.
Desligar: `launchctl bootout gui/$(id -u)/br.automacao-vios.orelha`. Para os parados, faça uma cópia
com outro `Label` (ex.: `br.automacao-vios.orelha-parados`), os argumentos `rodar.sh --funcoes
parados --sem-pdf` e um só `StartCalendarInterval` (ex.: `Weekday` 6, 8h). Se o Mac estiver
dormindo na hora marcada, o launchd roda quando ele acordar.

## Vila 05

Com `VILA_URL` e `VILA_SENHA` no `.env`, o Orelha manda cada etapa por `POST /eventos` ao Ultron
(`"orelha"` está em `BOTS_EXTERNOS` de `bot/eventos.py`). A Vila 05 (`/vila?vila=5`) mostra o Orelha
andando pelo parque dele, cheio de brinquedos: sai da casinha e vai ao mural do Calendário, à caixa
de correio das Intimações, à Torre VIOS (torre de parquinho), ao baú das Planilhas e à toalha do
Relatório. Ele late "!" quando há achado grave. O contrato dos eventos está em `doc/vila/contrato-eventos.md`, seção "Orelha". Se a
vila for baixada de novo do site, rode `python3 doc/vila/ligar_orelha.py bot/vila/vila.html` depois do
`ligar_zangao.py` e do `ligar_albi.py` (e antes do `ligar_jarvis.py`), e por fim
`python3 doc/vila/ligar_vila05_parque.py bot/vila/vila.html` (o parque). A vila só assiste: se o Ultron estiver fora do ar, o Orelha
segue trabalhando.

Parado, o Orelha diz na vila quando roda e quando sai o próximo relatório, e avisa se o de hoje
não saiu. No fim de cada execução, guarda a folha no **Arquivo** do parque. Depois do
`ligar_vila05_parque.py`, rode `python3 doc/vila/ligar_orelha_agenda.py bot/vila/vila.html`.

## Relatórios guardados (página `/orelha` do Sam)

Cada relatório fica na pasta do dia (`saida/<AAAA-MM-DD>/`: `relatorio.html`, `relatorio.pdf`,
`resumo.json` e a planilha `.csv` das planilhas do Albi). O Sam (`bot/orelha.py`) lê essas pastas
e mostra todos na página `/orelha`, aberta pelo botão "Relatórios guardados" da Vila 05 ou pelo
cartão do Orelha na Vila dos Bots: dia, hora, graves, pontos de atenção e os botões Abrir, PDF e
Planilhas (.csv). Os do `--simulado` ficam à parte. A página fica atrás da senha das páginas do Sam,
porque o relatório tem nomes de clientes e da equipe. Para a vila só vão datas e contagens
(`/orelha/status`).

## O que ainda falta conferir na tela real

Nada disto foi visto rodando no VIOS de verdade: o Orelha foi feito sem credenciais, com o mapa das
telas e o código dos outros bots. Antes de confiar no relatório, confira com `HEADLESS=false`,
olhando o `logs/orelha.log`.

**Bloqueio e login**
- Se o login passa com o bloqueio já ligado (o form de login é marcado pelo Orelha). Se aparecer
  "o bloqueio de envios barrou N pedido(s) da tela de login", use `ORELHA_BLOQUEIO_NO_LOGIN=false`.
- Para qual endereço o calendário manda o XHR POST das tarefas. Ponha esse trecho em
  `ORELHA_XHR_PERMITIDO`, para o modo pesquisa só liberar esse POST.

**Calendário (agenda)** — visto na tela em 04/11/2026, só lendo:
- Já conferido: FullCalendar 5 ou mais novo (classes `fc-daygrid`), sem instância global acessível;
  o Orelha lê pelo HTML, com o `data-date` do dia. Hora em `.fc-event-time`, título em
  `.fc-event-title`, sem tooltip. Botões `.fc-prev-button`/`.fc-next-button`, título do mês em
  `.fc-toolbar-title`. Feriados abrem `cal_feriados.php`; compromissos abrem `agenda-vis.php`
  (`agenda_id`); com "Agrupar" ligado (padrão), as tarefas do dia vêm juntas por tipo num link para
  a lista de tarefas (`pxe-lista.php`), sem responsável nem data limite. Não apareceu "+N mais"
  na visão Mês.
- **O calendário abre filtrado no usuário logado** (Responsável ou Auxiliar = ele). Para a agenda da
  equipe toda (audiências e perícias de todo mundo), o próximo passo é a agenda também ler as
  tarefas de hoje e amanhã pela lista de tarefas, como os prazos já fazem; os compromissos e os
  feriados continuam vindo do calendário.

**Prazos** — já conferido: a lista de tarefas (`pxe-lista.php`) traz a equipe toda por GET. Falta
comparar o total do placar com a lista do VIOS no primeiro uso real.

**Intimações**
- Se o padrão da tela `int-pesquisa.php` continua "Com Tarefa Lançada = Não". O Orelha não mexe nesse
  filtro, igual ao Ultron. Para fixar o filtro, use `ORELHA_INTIMACOES_FILTROS_EXTRA`.
- Se o resultado vem no recarregamento da página e não por XHR POST depois. Se a lista vier vazia,
  a seção avisa quantos pedidos o bloqueio barrou.
- Se "Marcar todas" na Área não limita o resultado.
- Se a célula `sdata` traz "Disponibilização: DD/MM/AAAA". O Orelha usa essa data.
- Se existe uma coluna própria de tribunal. Sem ela, a sigla sai do número CNJ ou do fornecedor.
- Se o link da célula `intimacao_numeros` é o da ficha do processo (`processos-vis.php`).
- Se o rodapé `.geratabela_total_quantidade_original` existe nesta tela e se as linhas com ícone
  "Apagada" aparecem nela.

**Processos parados**
- Se a pesquisa da lista funciona com o form marcado e `#Pesq`. Conferir também se
  `pesq[limit]=9999999`, Grupo=0 e o filtro "ativos" dão a mesma lista da tela.
- Se a lista inteira (milhares de linhas) carrega em `ORELHA_PARADOS_TIMEOUT_LISTA` (180 s).
- **Se a ficha (Vue) busca os dados por GET ou por XHR POST.** Se for POST, as fichas saem como "não
  lidas", com o motivo nos avisos. Nesse caso, confira que abrir a ficha não grava nada e use
  `ORELHA_PARADOS_LIBERAR_XHR=auto`.
- Se a tabela de Tarefas aparece sem clicar na aba e como fica numa ficha sem tarefas ("Nenhum
  registro encontrado").
- Se o DataTables pagina a tabela de Tarefas. O Orelha lê todas as linhas pela API dele, e uma tabela
  incompleta vira "não confirmado".
- As posições das colunas (1 = CI, 2 = tipo com o selo CANCELADA, 5 = datas com "Concluída em:",
  `ORELHA_PARADOS_COLUNAS_TAREFA`).
- Se a sessão do VIOS dura uma leitura de 300 fichas, e o tempo médio por ficha, para calibrar
  `ORELHA_PARADOS_MAX` e `ORELHA_PARADOS_MINUTOS`.

**Planilhas (busca "Nro do Processo")**
- **A busca do topo não está mapeada.** Falta conferir o `name`/`id` do campo de texto
  (`ORELHA_PLANILHAS_BUSCA_CAMPO`), se a opção "Nro do Processo" é um `<select>`, um rádio ou um menu
  JS (`_TIPO`, `_OPCAO`) e se o campo está num `<form>`. Se a busca abre por GET com o número no
  endereço, basta `ORELHA_PLANILHAS_BUSCA_URL`. Outra saída é o modo `lista`.
- Se a busca recarrega a página ou vem por AJAX/XHR (`_RECARREGA`, `_XHR`) e em que formato aceita o
  número (`_FORMATO`).
- Como é a tela de resultado e como ela mostra "nenhum resultado". Preencha
  `ORELHA_PLANILHAS_BUSCA_PRONTO` e `ORELHA_PLANILHAS_BUSCA_RESULTADO`, para evitar "novo" falso quando a
  página não carregou ou "já tem" falso quando a tela repete o número pesquisado.
- Modo lista: se `pesq[filtros_multi][]=todos` traz ativos e encerrados, e se a coluna do número
  vem preenchida em todos os processos.

**Vila**
- Abrir a Vila 05 num navegador de verdade (`/vila?vila=5`) e conferir o desenho do Orelha, as caixas
  das Planilhas, o painel "Relatório do dia · Orelha" e se o seletor de vilas (01 a 05) cabe em tela
  estreita.
- Conferir que o Orelha, rodando em outra máquina, consegue fazer `POST /eventos` no Ultron.
