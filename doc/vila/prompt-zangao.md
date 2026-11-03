# Prompt para o Bumblebee (Zangão) · eventos para a vila

> Copie tudo abaixo da linha e cole na sessão que mexe no código do Bumblebee
> (bot de comprovantes previdenciários).

---

Quero que a **vila dos bots** (Vila 02 · Zangão) mostre o Bumblebee trabalhando em tempo real,
como já faz com o Ultron (bot de intimações). Para isso, o Bumblebee precisa **emitir eventos**
em cada etapa do fluxo e mandá-los ao servidor do Ultron, que é quem guarda os eventos e serve
a vila. A vila **só assiste**: nada do que ela faz pode mudar o comportamento do bot.

## Como a vila funciona hoje (lado do Ultron, já pronto)

- O Ultron roda num Mac (`http://192.168.30.21:5001`), com senha HTTP Basic (usuário
  qualquer + senha).
- Os eventos ficam em `saida/eventos.jsonl` do Ultron, uma linha JSON por evento, só com
  acréscimos no fim. Cada evento tem `n` (sequencial, único), `ts`, `bot`, `envio` e `tipo`.
- A vila lê `GET /eventos?desde=N` a cada 2 s e anima os eventos novos. Ela ignora tipos
  desconhecidos e campos extras.
- O Ultron vai ganhar uma rota **`POST /eventos`** (eu faço do lado do Ultron) que recebe um
  evento em JSON, com a mesma senha, e o acrescenta ao arquivo com o `n` dele.

## O que o Bumblebee precisa ter

### 1. Módulo `bot/vila.py` com `emitir(tipo, **dados)`

- Monta o evento `{"bot": "zangao", "envio": <id da execução>, "tipo": tipo, "ts": <agora,
  ISO local, segundos>, ...dados}` e faz `POST <VILA_URL>/eventos` com corpo JSON
  (`Content-Type: application/json; charset=utf-8`) e autenticação Basic (`VILA_SENHA`).
- Use só a biblioteca padrão (`urllib.request`), sem dependência nova.
- **Nunca derruba nem atrasa o bot**:
  - timeout curto (2 s);
  - qualquer erro (rede, 401, 500, timeout) vai para o log como aviso, uma linha só, sem a
    senha;
  - depois de 3 falhas seguidas, para de tentar até o fim da execução (para não esperar o
    timeout em cada tarefa), e avisa isso no log uma vez;
  - eventos que não foram enviados vão para `saida/eventos_pendentes.jsonl` (só para
    conferência; não precisa reenviar).
- **Desligado** quando `VILA_URL` estiver vazio (padrão): `emitir` não faz nada.
- O `envio` (id da execução) é o mesmo carimbo do relatório da execução:
  `relatorio_AAAA-MM-DD_HHMMSS.csv` → `envio = "AAAA-MM-DD_HHMMSS"`.
- Os eventos vão **só para o servidor da vila**, nunca para o VIOS. O bloqueio de envios do
  modo somente leitura/simulação é no navegador e não se aplica aqui. Mesmo assim, deixe isso
  dito no código e na documentação.

### 2. `.env` / `.env.example` / documentação

| variável | obrigatória | descrição | exemplo |
| --- | --- | --- | --- |
| `VILA_URL` | não | Servidor do Ultron que guarda os eventos da vila (vazio = desligado) | `http://192.168.30.21:5001` |
| `VILA_SENHA` | com `VILA_URL` | Senha da página do Ultron (`ENVIO_SENHA` de lá) | (definir no `.env`) |

A senha nunca aparece no log nem na documentação.

### 3. Dados mínimos (regra dura)

Mande **só identificadores internos, etapas e contagens**. **Nunca** mande:
nome de cliente ou de parte, texto/título da tarefa do calendário (pode ter nome de cliente),
número CNJ, órgão julgador, valor da causa, nome do arquivo do comprovante nem conteúdo do PDF.
Para os campos preenchidos, mande **só o nome do campo** (`"cnj"`, `"orgao"`, `"valor"`), nunca o
valor. Escreva um teste que garanta isso (nenhum evento emitido contém essas chaves ou um texto
no formato CNJ `0000000-00.0000.0.00.0000`).

### 4. Tipos de evento, na ordem do fluxo real

Campos comuns em todos: `bot` = `"zangao"`, `envio`, `tipo`, `ts`.

**1. `execucao_iniciada`** (depois de validar argumentos e janela, antes de abrir o navegador)
```json
{ "tipo": "execucao_iniciada", "modo": "gravar", "fora_da_janela": false }
```
`modo`: `gravar` (`--confirmar`) | `teste` (simulação, o padrão) | `leitura` (`--somente-leitura`).
Com `--tarefa`, acrescente `"tarefa_unica": true`.

**Fora dos 3 últimos dias** (o bot termina sem abrir o navegador): só um evento
```json
{ "tipo": "execucao_fim", "resultado": "fora_do_dia" }
```

**2. `fase`**
```json
{ "tipo": "fase", "fase": "entrando_vios" }
```
`fase`: `entrando_vios` → `lendo_calendario` → `processando` (uma vez cada, nessa ordem).

**3. `calendario`** (depois de ler e classificar as tarefas do calendário)
```json
{ "tipo": "calendario", "total": 14, "previdenciarias": 6, "processar": 5,
  "ignoradas": 7, "ambiguas": 1,
  "tarefas": [ { "tarefa_id": "88123", "classe": "previdenciaria", "decisao": "processar" },
               { "tarefa_id": "88124", "classe": "previdenciaria", "decisao": "ignorada", "motivo": "outro_tipo" },
               { "tarefa_id": "88130", "classe": "ignorada", "motivo": "previdencia_privada" },
               { "tarefa_id": "88131", "classe": "ambigua", "motivo": "outra_area" } ] }
```
- `tarefa_id` = o `pxe_id` da tarefa.
- `processar` = previdenciárias do tipo `CALENDARIO_TIPO` (as que serão abertas).
- `classe`: `previdenciaria` | `ignorada` | `ambigua`.
- `motivo` é um **código curto**, nunca o texto da tarefa: `outro_tipo`, `previdencia_privada`,
  `sem_sinal_previdenciario`, `outra_area`, `sinal_sem_previdenci`, `ja_registrada`.
- `tarefas` é opcional; sem ele, a vila mostra só as contagens. Tarefas já em
  `saida/registro.json` entram com `decisao: "ja_registrada"`.

**4. `tarefa`** (um evento por mudança de etapa de cada tarefa processada)
```json
{ "tipo": "tarefa", "tarefa_id": "88123", "processo_id": "40211", "etapa": "abrindo" }
{ "tipo": "tarefa", "tarefa_id": "88123", "processo_id": "40211", "etapa": "comprovante_lido" }
{ "tipo": "tarefa", "tarefa_id": "88123", "processo_id": "40211", "etapa": "preenchendo", "campos": ["cnj", "orgao", "valor"] }
{ "tipo": "tarefa", "tarefa_id": "88123", "processo_id": "40211", "etapa": "gravada", "campos": ["cnj", "orgao", "valor"] }
{ "tipo": "tarefa", "tarefa_id": "88125", "processo_id": "40377", "etapa": "pulada", "motivo": "campo_com_outro_valor" }
```
`etapa`:
- `abrindo`: abriu a tarefa / o processo;
- `comprovante_lido`: baixou e leu o PDF (CNJ, órgão e valor encontrados, um de cada);
- `preenchendo`: na tela de edição, com a lista dos campos que serão preenchidos (vazios);
  em `--somente-leitura`, use `lida` no lugar (o que faria, sem preencher);
- fim da tarefa (um destes, sempre um por tarefa):
  `gravada` (gravou e a releitura conferiu) | `ja_estava` (já tinha os valores do PDF) |
  `testada` (simulação: preencheu e não gravou) | `lida` (somente leitura) |
  `pulada` (com `motivo`) | `conferir` (gravou, mas a releitura não confirmou) |
  `erro` (com `motivo`).
- `orgao_cadastrado: true` quando, com `--confirmar`, o bot cadastrou um órgão julgador novo
  (na simulação, `orgao_novo: true`, sem cadastrar).
- `motivo` é código curto, por exemplo: `sem_comprovante`, `mais_de_um_comprovante`,
  `pdf_sem_texto`, `dado_ausente_no_pdf`, `dado_duplicado_no_pdf`, `cnj_diferente_do_processo`,
  `campo_com_outro_valor`, `orgao_nao_apareceu`, `processo_diferente_na_edicao`,
  `aviso_inesperado`, `elemento_nao_unico`, `excecao`. Pode criar outros no mesmo estilo; a
  vila mostra o código como veio.
- `processo_id` é o id interno do VIOS lido do "Visualizar" (não o CNJ).

**5. `execucao_fim`** (sempre, inclusive quando falha no meio: use `finally`)
```json
{ "tipo": "execucao_fim", "resultado": "concluido",
  "contagens": { "gravado": 4, "ja_estava": 1, "teste": 0, "leitura": 0, "ja_registrada": 2,
                 "ignorada": 7, "ambigua": 1, "pulada": 1, "conferir": 0, "erro": 0 } }
```
`resultado`: `concluido` (gravar) | `testado` (simulação) | `lido` (somente leitura) |
`fora_do_dia` | `parou` (com `"motivo"`, ex.: `login_falhou`, `bloqueio_inativo`, `excecao`).
As contagens são as mesmas do resumo final do bot.

### 5. Onde chamar

Nos mesmos pontos que já escrevem no log / no relatório CSV: início em `main.py`,
`entrando_vios` antes do login, `lendo_calendario` e `calendario` em `bot/calendario.py`,
as etapas de `tarefa` em `bot/processo.py`, `bot/comprovante.py` e `bot/edicao.py`, e
`execucao_fim` no `finally` de `main.py`. Ordem dos eventos = ordem real do fluxo.

### 6. Testes (sem acessar o VIOS nem a rede)

- `tests/test_vila.py` com um servidor HTTP falso local (`http.server` numa thread) que:
  - confere corpo JSON, `bot = "zangao"`, `envio`, `ts` e a autenticação Basic;
  - responde 200, 401, 500 e demora mais que o timeout, para provar que o bot continua em
    todos os casos e que, depois de 3 falhas, para de tentar;
- `VILA_URL` vazio → nenhuma requisição;
- teste dos dados mínimos (seção 3);
- sequência de uma execução simulada com os dublês que já existem em
  `tests/test_somente_leitura.py`: `execucao_iniciada` → `fase`… → `calendario` → `tarefa`… →
  `execucao_fim`, sempre terminando em `execucao_fim`.

### 7. Registro

Registre a mudança no `CHANGELOG.md` e na documentação (`.env`, passo a passo e a lista de
arquivos), em português. No fim, me devolva um resumo como o do Ultron: o que foi feito, as
diferenças em relação a este contrato (se houver) e um exemplo real de eventos de uma
simulação (sem dados de cliente).
