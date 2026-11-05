# Relatório Mensal de Processos por Grupo Cliente — VIOS

Robô que entra no VIOS com o **segundo usuário** (mesmo escritório,
`roneely.vios.com.br`, outro login e outras permissões), lê os processos de
cada **Grupo Cliente** e gera **uma planilha .xlsx por grupo**, no formato da
planilha "Processos Casa do celular" do Google Drive. Roda **uma vez por mês**
(dia a definir).

> **Status: em teste (03/11/2026).** Primeira versão da planilha com as duas
> Casas do Celular. A versão anterior (um .txt por grupo, 28/10/2026) foi
> descartada. Este arquivo é atualizado a cada alteração.
> Histórico de mudanças: [CHANGELOG.md](../CHANGELOG.md). Robô de intimações (Sam):
> [DOCUMENTACAO.md](../DOCUMENTACAO.md).
>
> **Desde 05/11/2026 o Jarvis tem pasta própria (`jarvis/`)**, como o Albi e o Orelha: `.venv`,
> `.env`, `logs/` e `saida/` dele, e cópias próprias do login do VIOS, da configuração, da IA e do
> teto de gasto em `jarvis/nucleo/`. Ele não importa nada de `bot/`: mexer no Sam não quebra o
> Jarvis. Os comandos abaixo são rodados **dentro de `jarvis/`**.

---

## 1. Objetivo

| Etapa | O que faz | Status |
| --- | --- | --- |
| 1. Login | Entra no VIOS com o usuário do `.env` | ✅ Pronto |
| 2. Lista | Processos → filtro Grupo Cliente → Mostrar 500 → Pesquisar | ✅ Pronto |
| 3. Lupa | Abre a tela de cada processo: Dados do Processo + tarefas | ✅ Pronto |
| 4. IA | Resumo do caso, motivação, financeira, justificativa da condenação e documentos faltando | ✅ Em teste |
| 5. Planilha | Uma .xlsx por grupo (abas Processos, Resumo, Cadastro incompleto, Metadados) | ✅ Em teste |
| 6. Google Drive | Salvar direto numa pasta do Drive | ⏳ Pendente |
| 7. Agendamento mensal | Rodar sozinho no dia definido | ⏳ Pendente |

**Revisão do usuário (03/11/2026):** saíram as colunas Fase, Valor provisionado,
Última movimentação e Pendência — responsável (esta por **sigilo**: tinha nomes
da equipe). A Justificativa da condenação passou a ser preenchida.

### Grupos

| Relatório | Grupo Cliente no VIOS (código) |
| --- | --- |
| Casa do Celular (HAV/RAV Holding) | CASA DO CELULAR (127) |
| Casa do Celular MG/SP (HAV/RAV Holding) | CASA DO CELULAR MG/SP (130) |
| Plasfran Itapipoca | PLASFRAN ITAPIPOCA (43) — depois |
| Plasfran Camocim | PLASFRAN CAMOCIM (42) — depois |
| Plasfran Maranhão | PLASFRAN MARANHÃO (109) — depois |
| LD Urbanismo | LD URBANISMO (92) — depois |

As duas Casas do Celular são da mesma holding e cada uma tem seu relatório. No
VIOS o cliente aparece como **RAV HOLDING LTDA**.

---

## 2. Passo a passo do que o robô faz

1. **Login** com o usuário e a senha do `.env`.
2. Abre **Relatórios** (`NAVEGACAO_URL_FINAL`) e depois a lista de **Processos**
   (`?pag=sys/processos/processos-lista.php&menu_lateral=true`).
3. Para cada grupo: escolhe o grupo no filtro **Grupo Cliente**
   (`pesq[clientes_grupos_id]`), muda **Mostrar** de 30 para **500** e aciona
   **Pesquisar**. Os outros filtros ficam no padrão: **Ativos** e **Não
   migrados** (encerrados não entram). O "TODOS" nunca é usado.
4. Lê a lista (CI, número, partes, órgão) e confere com o rodapé "Total (N)".
5. Para cada processo, abre a **lupa**: o mesmo endereço do botão
   (`index.php?pag=sys/processos/processos-vis.php&processos_id=<CI>`), sem
   abrir abas novas. Lê:
   - **Dados do Processo - CI N**: os pares `Rótulo: valor` (CNJ, cliente, polo
     do cliente, fase, cidade/UF, distribuição, valor da ação...);
   - **Tarefas**: tipo, situação (Em dia, Concluída, Cancelada...), descrição,
     comentários, datas (para conclusão, limite, concluída em) e envolvidos
     (responsáveis, quem concluiu).
6. **"Mostrar mais"**: o botão só esconde o texto com a classe `limite-texto`;
   o robô tira essa classe de todas as tarefas por JavaScript (sem clicar) e lê
   o texto inteiro.
7. Manda à **IA** o cadastro e o texto das tarefas (sem as canceladas, já
   limpo — ver seção 4) e recebe as colunas de texto.
8. Monta a linha da planilha e, no fim do grupo, salva a `.xlsx` e um `.json`
   com tudo o que foi lido (para conferência).

### Só leitura

A lista tem **Apagar**, **Editar** e **Processar** (ações em lote) e a lupa tem
botões de edição. O robô **não usa nenhum**: só escolhe filtros, pesquisa,
abre a tela do processo e lê.

---

## 3. A planilha gerada

Caminho: `saida/relatorios/AAAA-MM/<GRUPO>.xlsx`
(ex.: `saida/relatorios/2026-11/CASA DO CELULAR.xlsx`). Rodar de novo
no mesmo mês sobrescreve.

### Aba Processos (uma linha por processo)

| Coluna | De onde vem | Como |
| --- | --- | --- |
| CI | lista | — |
| Número do processo | lupa: `N.° CNJ` | — |
| Cliente | lupa: `Cliente` | — |
| Polo do cliente | lupa: `Polo do cliente` | — |
| Parte ativa / Parte passiva | lista | várias partes separadas por `;` |
| Tipo de processo | lupa: `Processo` | em maiúsculas |
| Órgão | lupa: `Comarcas / Tribunais / Órgãos adm.` | — |
| Data da distribuição | lupa: `Data da ação / Distribuição` | data |
| Valor da ação | lupa: `Valor da ação` | número (R$) |
| Cidade/UF | lupa: `Cidade / UF` | — |
| Resumo do caso | tarefas | **IA**: 2 a 4 frases simples para o cliente |
| Motivação do processo | tarefas | **IA**: categoria da lista fixa + detalhe curto |
| Financeira | tarefas | **IA**: financeiras/bancos/securitizadoras citados |
| Justificativa da condenação | tarefas | **IA**: se houve condenação, o motivo da decisão e o que o cliente tem que fazer (1 ou 2 frases); senão, "Sem condenação (pedidos improcedentes)", "Acordo" ou "Sem decisão até o momento" |
| Pendência — documentos faltando | tarefas | **IA**: pedidos que ainda não chegaram + quem entrega (nunca nome da equipe) |

**Removidas a pedido (03/11/2026):** Fase, Valor provisionado, Última
movimentação e Pendência — responsável (sigilo: nomes da equipe).

**Motivação — lista fixa** (para filtrar e contar): Financiamento / bloqueio do
aparelho; Defeito do produto / garantia; Cobrança indevida / negativação;
Oferta ou contrato descumprido; Atendimento / dano moral; Trabalhista; Outros.
A lista fica em `MOTIVACOES` (`nucleo/relatorio_planilha.py`).

**Documentos faltando é dedução da IA**: ela compara o que a equipe pediu
(ex.: no ANALISAR PROCESSO) com o que chegou (tarefas ANALISAR DOCUMENTOS,
arquivos enviados). Conferir antes de mandar ao cliente.

### Outras abas

| Aba | Conteúdo |
| --- | --- |
| Resumo | Data, total de processos, soma dos valores da ação (fórmulas), contagem por tipo, motivação, resultado da decisão, cliente e polo |
| Cadastro incompleto | Processos com número, tipo, distribuição, valor da ação, cidade ou órgão vazios no VIOS — para a equipe completar |
| Metadados | Grupo, data, origem dos dados, modelo de IA, erros e gasto |

Campo vazio no VIOS fica vazio na planilha. Erro na IA aparece como
`ERRO NA IA: conferir` e é contado na aba Metadados.

---

## 4. IA

- Provedor e chave no `.env` (`LLM_PROVEDOR=anthropic`,
  `ANTHROPIC_API_KEY`). Modelo padrão: `claude-sonnet-5-5` (`LLM_MODELO`).
- Uma chamada por processo, com resposta em JSON validado (schema em
  `nucleo/relatorio_planilha.py`). Processo sem tarefas não vai para a IA.
- **O que é tirado antes de mandar**: tarefas canceladas, texto repetido
  depois de "[observação da conclusão]", texto padrão do tipo de tarefa,
  links (viram `[link]`), CPF (vira `[CPF]`) e linhas com senha/ID de acesso.
  Cada tarefa vai com até 6.000 caracteres, e o processo com até 40.000.
- **O texto das tarefas nunca é copiado para a planilha**: só o que a IA
  escreve. A IA é instruída a não citar CPF, links, nomes da equipe nem
  rotinas internas do escritório.
- **Só fatos do processo** (desde 03/11/2026): pedidos das partes, decisões,
  prazos e audiências. Opiniões, avaliações e estratégias internas que a
  equipe registra nas tarefas não vão para a planilha. Motivo: no CI 28667 a
  justificativa repetiu um comentário interno ("a condenação já está acima da
  média", da tarefa sobre dispensar a sustentação oral por economia).
- **Custo**: ~US$ 0,013 por processo (teste de 03/11/2026). Teto por execução
  em `LLM_LIMITE_US` (no `.env`: 5); passou do teto, os processos que
  faltam saem com erro na IA.

---

## 5. Como rodar

### Pela plataforma (vila do Ultron, no Mac)

O robô se chama **Jarvis** e fica na **Vila 04** da vila do Ultron
(`http://<IP do Mac>:5001/vila?vila=4`, com a senha da página do Ultron). Na caixa de fala,
**Escolher grupos e gerar** e **Planilhas** abrem a página do Jarvis (`/jarvis`, também pelo
botão "Jarvis" no topo da página do Ultron):

1. **Marcar os grupos** que vão ter relatório (a lista é o `PROCESSOS_GRUPOS` do `.env`
   do Jarvis; "Marcar todos" marca e desmarca todos). Nada roda sem escolher: sem grupo marcado,
   os botões ficam desligados, e o servidor recusa grupo fora da lista.
2. **Gerar relatório do mês**: lê todos os processos só dos grupos marcados e gera uma planilha
   por grupo. Pede confirmação (segundo clique em até 6 s), porque gasta IA (~US$ 0,02 por processo).
3. **Testar (2 processos por grupo)**: só os 2 primeiros processos de cada grupo marcado; salva em
   `AAAA-MM/teste/` e não substitui a planilha do mês.
4. Embaixo, a lista das planilhas com o botão **Baixar** (as de teste com o selo "teste").

Enquanto roda, a página mostra os grupos escolhidos e se atualiza sozinha, e a caixa de fala da Vila 04 mostra o andamento
("Grupo 1 de 2: processo 37 de 101 · gasto US$ 0,70"); o Jarvis vai até a Leitura dos
processos e, ao salvar cada planilha, até Planilhas. No fim: "Pronto! N planilha(s) do mês
gerada(s)". A vila só recebe contagens: nunca nome de grupo, cliente ou número de processo.

Como funciona: o Sam (`bot/jarvis.py`, rotas `/jarvis/*` em `bot/envio_web.py`) abre o
`relatorio_processos.py` da pasta `jarvis/` (ou de `JARVIS_PASTA`, se preenchido) em segundo plano; o
relatório manda o andamento por `POST /eventos` (`nucleo/vila_aviso.py`, `VILA_URL`/`VILA_SENHA`).
Saída de cada execução: `logs/execucoes_vila.log` na pasta do Jarvis.

### Instalar no Mac (uma vez)

Na pasta do projeto que já roda o Sam (depois do `git pull`):

```bash
cd jarvis && ./instalar.sh   # cria jarvis/.venv (Python 3.9+) e o jarvis/.env a partir do .env.example
# preencher no jarvis/.env: SISTEMA_USUARIO e SISTEMA_SENHA (segundo usuário), ANTHROPIC_API_KEY,
# PROCESSOS_GRUPOS, HEADLESS=true, VILA_URL=http://127.0.0.1:5001/eventos e VILA_SENHA = ENVIO_SENHA do Sam
```

Depois reiniciar a página do Sam (`./servidor_mac.sh parar && ./servidor_mac.sh instalar`). Não
precisa de `JARVIS_PASTA`: o Sam acha o Jarvis em `jarvis/`. Ele só é usado se o Jarvis estiver
noutra pasta.

### Pelo terminal

No Mac/Linux: `./rodar.sh --grupo "CASA DO CELULAR" --limite 3` (mesmas opções do `.bat`).
No Windows, na pasta `jarvis\`:

```powershell
.\rodar.bat                                  # grupos de PROCESSOS_GRUPOS
.\rodar.bat --limite 3                       # teste: só 3 processos por grupo
.\rodar.bat --grupo "casa do celular mg/sp"  # um grupo (acento e maiúsculas não importam)
.\rodar.bat --grupo todos                    # todos os grupos do filtro
```

Sem o `.bat`:

```powershell
.\.venv\Scripts\python.exe relatorio_processos.py .env --grupo "CASA DO CELULAR" --limite 3
```

Leva cerca de 10 s por processo (abrir a lupa + IA). O log mostra o andamento:
`CASA DO CELULAR: 12/101 CI 29825 — 16 tarefas — gasto US$ 0.15`.

---

## 6. Primeira instalação (Windows)

```powershell
cd C:\Rfeitosa-projetos\automacao-vios\jarvis
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env    # e preencher usuário, senha e ANTHROPIC_API_KEY
```

---

## 7. Configuração (`.env`)

Modelo versionado: `.env.example`. O `.env` real tem a senha
e a chave da IA e **não vai para o GitHub**.

| Variável | Uso | Valor atual |
| --- | --- | --- |
| `SISTEMA_URL` | Página de login | `https://roneely.vios.com.br/entrar.php?` |
| `SISTEMA_USUARIO` / `SISTEMA_SENHA` | Login do segundo usuário | (no `.env`) |
| `NAVEGACAO_URL_FINAL` | Tela aberta depois do login | `.../?pag=sys/relatorios/relatorios.php` |
| `PROCESSOS_GRUPOS` | Grupos que podem ser escolhidos na página `/jarvis`, separados por `\|` (no terminal, sem `--grupo`, roda todos eles) | os 6: Plasfran Itapipoca, Camocim e Maranhão, LD Urbanismo, Casa do Celular e Casa do Celular MG/SP |
| `RELATORIO_PASTA` | Pasta das planilhas (vazio = `<SAIDA_PASTA>/relatorios`) | vazio |
| `LLM_PROVEDOR` | `anthropic` ou `openai` | `anthropic` |
| `ANTHROPIC_API_KEY` | Chave da IA | (no `.env`) |
| `LLM_MODELO` | Modelo (vazio = `claude-sonnet-5-5`) | vazio |
| `LLM_LIMITE_US` | Teto de gasto por execução (US$) | `5` |
| `SAIDA_PASTA` | Pasta de saída deste usuário | `saida` |
| `HEADLESS` | Chrome sem janela | `false` |
| `TIMEOUT` | Espera máxima (s) | `20` |
| `MANTER_ABERTO` | Chrome continua aberto no fim | `false` |
| `VILA_URL` | Eventos do Ultron para a Vila 04 (vazio = sem vila) | `http://127.0.0.1:5001/eventos` (no Mac) |
| `VILA_SENHA` | Senha da página do Ultron (`ENVIO_SENHA`) | (no `.env`) |
| `NAVEGADOR_RAPIDO` | Carregamento "eager" das páginas (do `main`) | padrão `true` |

---

## 8. Arquivos do projeto

```
automacao-vios/
├── jarvis/                          # o Jarvis (pasta própria)
│   ├── relatorio_processos.py       # entrada: login → grupos → lupa de cada processo → IA → .xlsx
│   ├── instalar.sh / rodar.sh       # Mac/Linux: cria a .venv / roda (aceita --grupo e --limite)
│   ├── rodar.bat                    # atalho no Windows (aceita --grupo e --limite)
│   ├── requirements.txt             # selenium, python-dotenv, anthropic, openai, openpyxl
│   ├── nucleo/processos_grupo.py    # filtro Grupo Cliente, pesquisa e leitura da lista
│   ├── nucleo/processos_detalhe.py  # lupa: Dados do Processo + tarefas
│   ├── nucleo/relatorio_planilha.py # regras fixas, instruções da IA e gravação da .xlsx
│   ├── nucleo/vila_aviso.py         # andamento para a vila (POST /eventos, bot "jarvis")
│   ├── nucleo/config.py, login.py, navegador.py, navegacao.py, extracao.py, custo.py, ia/,
│   │   registro.py                  # cópias próprias (antes vinham de bot/ e do main.py do Sam)
│   ├── .env.example                 # modelo do .env do segundo usuário
│   ├── .env                         # configuração real (NÃO versionar — senha e chave)
│   ├── logs/                        # bot.log, execucoes_vila.log e prints de erro (NÃO versionar)
│   └── saida/relatorios/            # planilhas e .json (NÃO versionar — dados de clientes)
├── bot/jarvis.py                    # lado do Sam: roda o Jarvis pela vila e lista as planilhas
├── bot/templates/jarvis.html        # página /jarvis (planilhas para baixar)
└── doc/vila/ligar_jarvis.py         # põe a Vila 04 · Jarvis (botões e andamento) no bot/vila/vila.html
```

As cópias em `jarvis/nucleo/` são independentes: uma correção no login do Sam (`bot/login.py`) não
chega sozinha ao Jarvis. Se o VIOS mudar a tela de login, corrigir nos dois.

---

## 9. Segurança

- **Só leitura** no VIOS (seção 2).
- **Um `.env` por usuário**; o log confirma o usuário em "Login OK como ...".
- **Fora do GitHub** (`.gitignore`): `.env` e `.env.*` (menos os `.example`),
  `saida/`, `saida_*/`, `imgs/` e `logs/`. As planilhas e o `.json` têm dados de
  clientes e partes.
- **Dados sensíveis das tarefas** (CPF, links e senhas de audiência, links de
  conversas) são tirados antes de ir para a IA e nunca vão para a planilha.
- A senha do segundo usuário e a chave da IA foram passadas por chat na
  configuração: trocar e atualizar o `.env`.

---

## 10. Pontos de atenção

- **Cadastro incompleto no VIOS aparece na planilha.** No teste de 03/11/2026
  (3 processos da Casa do Celular), nenhum tinha **data de distribuição** nem
  **valor da ação**; um não tinha **número**, outro não tinha **tipo**; e o
  "Órgão" era o PROCON mesmo em processo judicial (CI 29825, 2º Juizado de
  Cariacica pelas tarefas). A aba "Cadastro incompleto" lista o que falta.
- **Mais processos que a planilha antiga**: a lista da CASA DO CELULAR trouxe
  **101** processos ativos; a planilha do Drive tinha 70 (montada de um PDF).
- **Só processos ativos e não migrados**; até 500 por grupo.
- **Justificativa da condenação e documentos faltando dependem do que a equipe
  registrou nas tarefas.** Se a análise da sentença não foi escrita no VIOS, a
  IA não tem de onde tirar o motivo. "Documentos faltando" é dedução e pode
  variar entre execuções (ex.: CI 29825 listou 2 documentos numa rodada e
  nenhum na seguinte) — conferir antes de mandar ao cliente.

---

## 11. Testes

| Data | Grupo | Resultado |
| --- | --- | --- |
| 28/10/2026 | 3A FRIOS | Versão .txt (descartada): 17 processos, 0 erros |
| 03/11/2026 | CASA DO CELULAR (3 processos) | 3 linhas, 0 erros na IA, US$ 0,04 |
| 03/11/2026 | CASA DO CELULAR + CASA DO CELULAR MG/SP | 101 + 26 processos, 0 erros, 16 min, US$ 2,13. 61 dos 70 processos da planilha antiga presentes (os 9 restantes não estão mais ativos) e 37 novos. Aprovado na primeira conferência do usuário. |

---

## 12. Próximos passos

1. Validar a nova versão da planilha das duas Casas do Celular.
2. Incluir Plasfran (3 grupos) e LD Urbanismo.
3. Salvar no Google Drive (`RELATORIO_PASTA` apontando para a pasta
   sincronizada) e agendar a execução mensal.
4. Instalar o Jarvis no Mac (seção 5) e levar a parte da plataforma (Vila 04, `bot/jarvis.py`,
   rotas `/jarvis`) para o código que o Ultron roda.

---

## 13. Regra de manutenção

Toda mudança neste robô é registrada no [CHANGELOG.md](CHANGELOG.md) **e** neste
arquivo (passo a passo, tabelas, testes e próximos passos).
