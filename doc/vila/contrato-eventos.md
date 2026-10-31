# Contrato de eventos · Ultron → Vila

A vila **só assiste**. Ela não grava nada nem aprova nada. A conferência, o envio e a trava do MODO: TESTE continuam na página Ultron.

## Onde fica cada coisa
- **Eventos**: `saida/eventos.jsonl`, com uma linha JSON por evento e só acréscimos no fim.
- **Endpoint**: `GET /eventos?desde=N` no próprio Flask (mesma senha e mesma origem).
- **Vila**: servida pelo Ultron em `/vila`, como arquivo HTML único e estático.
- **Leitura**: a vila consulta o endpoint a cada 2 s. No primeiro acesso (`desde=0`), monta o estado atual sem animar. Depois disso, anima cada evento novo, um por vez, em fila.

## Resposta do endpoint
```json
{ "ultimo": 131, "eventos": [ { "n": 129, ... }, { "n": 130, ... }, { "n": 131, ... } ] }
```
- `n` é um número sequencial e crescente, único no arquivo.
- `desde=N` devolve os eventos com `n > N`.
- Sugestão: no primeiro acesso, devolver no máximo os últimos 500.

## Campos comuns (todo evento)
| campo | exemplo | obs. |
|---|---|---|
| `n` | `131` | sequencial |
| `ts` | `"2026-10-31T09:41:02"` | horário local |
| `bot` | `"ultron"` | futuramente `"zangao"` etc. |
| `envio` | `"2026-10-31_09-41-02"` | mesmo id de `saida/envios/<id>.json` |
| `tipo` | ver abaixo | |

**Dados mínimos**: só CI, nome da tarefa e contagens. Nada de teor da intimação nem nome de cliente.

## Tipos, na ordem do fluxo real

**1. `arquivo_subido`** (após `/ler`)
```json
{ "tipo": "arquivo_subido", "arquivo": "intimacoes_31-10.txt" }
```

**2. `conferido`**
```json
{ "tipo": "conferido", "prontas": 6, "com_problema": 1, "ja_lancadas": 1,
  "cis": [ { "ci": "4821", "tarefa": "Contestação", "status": "pronta" },
           { "ci": "4823", "tarefa": "Recurso de apelação", "status": "problema", "motivo": "Prazo ausente" },
           { "ci": "4824", "tarefa": "Juntada de documentos", "status": "lancada" } ] }
```
`status`: `pronta` | `problema` | `lancada`. O campo `cis` é opcional: sem ele, a vila mostra só as contagens.

**3. `envio_iniciado`** (clique na página Ultron)
```json
{ "tipo": "envio_iniciado", "modo": "gravar" }
```
`modo`: `gravar` (Enviar ao VIOS) | `teste` (Testar sem gravar).

**4. `fase`**
```json
{ "tipo": "fase", "fase": "entrando_vios" }
```
`fase`: `entrando_vios` → `conferindo_duplicatas` → `criando_tarefas`

**5. `ci`** (um evento por mudança de cada CI)
```json
{ "tipo": "ci", "ci": "4821", "tarefa": "Contestação", "etapa": "no_quadro" }
{ "tipo": "ci", "ci": "4821", "tarefa": "Contestação", "etapa": "gravada", "tarefa_num": "30411" }
{ "tipo": "ci", "ci": "4828", "tarefa": "Agravo de instrumento", "etapa": "erro", "motivo": "Responsável não encontrado" }
```
`etapa`: `no_quadro` | `gravada` (gravada e conferida) | `erro` | `ja_tinha` | `duplicata`

**6. `envio_fim`**
```json
{ "tipo": "envio_fim", "resultado": "concluido",
  "contagens": { "gravadas": 4, "erros": 1, "ja_tinha": 1, "duplicatas": 1 } }
```
`resultado`: `concluido` | `testado` | `parou` (com `"motivo"`).

## Do lado do Ultron
- Uma função `emitir(tipo, **dados)` que acrescenta uma linha a `saida/eventos.jsonl` com `n`, `ts`, `bot` e `envio`. Ela deve usar uma trava de arquivo, porque o Selenium e o Flask podem escrever ao mesmo tempo.
- Chamar `emitir` nos mesmos pontos que já alimentam `/envio/<id>/status`.
- A rota `/eventos` exige a mesma senha da página.
- A rota `/vila` serve o HTML único da vila.

## Tolerância da vila
- Ela ignora tipos desconhecidos e campos extras.
- Se abrir no meio de um envio, ela se posiciona direto na etapa atual.
- Se o endpoint falhar, o topo mostra "Sem conexão" e ela tenta de novo a cada 2 s.

---

## Como o Ultron implementou (31/10/2026)

Código: `bot/eventos.py` (`emitir()` e `ler()`) e as chamadas em `bot/envio_web.py`.
A vila deve ser colocada em **`bot/vila/vila.html`**; enquanto não existir, `/vila` mostra
uma página avisando.

Diferenças e detalhes que a vila precisa saber:

| Ponto | Como é no Ultron |
| --- | --- |
| `envio` | id do arquivo em `saida/envios/`, no formato `2026-10-31_115939_bedc` (data, hora e 4 caracteres) |
| `tarefa_num` | o VIOS não devolve um id da tarefa criada; vai `"<CI>-<posição da tarefa na CI>"`, ex.: `"42602-2"` |
| `conferido.cis` | uma linha por CI; CI com mais de uma tarefa traz os nomes juntos com `" + "`. `motivo` = o 1º problema |
| `conferido` repetido | sai de novo quando a pessoa edita e clica em "Salvar e conferir" |
| CI com várias tarefas | os eventos `ci` saem **um por tarefa** (mesmo `ci`, `tarefa` diferente) |
| Modo `teste` | a tarefa vai até `no_quadro` e para (nada é gravado); o fim vem como `envio_fim` `testado` |
| `envio_fim.contagens` | por CI; tem também `testadas` (campo extra) |
| `duplicata` / `erro` na conferência de duplicatas | saem durante a fase `conferindo_duplicatas`, antes de `criando_tarefas` |
| `parou` | erro geral (ex.: login no VIOS falhou) ou página reiniciada no meio de um envio (sai quando a página volta) |
| Trava | `threading.Lock` + `fcntl.flock` (Mac e Linux); testado com 3 processos × 4 threads, `n` sem repetir |
| Falha ao gravar evento | só vai para o log; nunca interrompe o envio |

## Vila instalada (31/10/2026)

- Origem: https://ruanpereiradev.github.io/autobots/ (baixada para `bot/vila/vila.html`).
- **Correção feita na cópia** (levar para o código-fonte da vila): o ajuste `fonte` tem
  `"default": "simulado"`, e `fonte()` era `this.props.fonte ?? (/vila ? 'servidor' : 'simulado')`,
  então o padrão sempre ganhava. Ficou: `/\/vila\/?$/.test(location.pathname) ? 'servidor' :
  (this.props.fonte ?? 'simulado')`.
- Detalhe visto no teste: o painel diz "3 de 3 CIs processadas" quando são 2 CIs e 3 tarefas
  (conta eventos `ci`, que saem um por tarefa).
- Para atualizar: baixar de novo o HTML publicado para `bot/vila/vila.html` (e reaplicar a
  correção, se ela ainda não estiver no código-fonte). Não precisa reiniciar a página.
