# Consulta de processo pelo WhatsApp (RN26) — especificação v2

> Substitui as seções 3, 7 e 8 do `PLANO_CONSULTA_PROCESSO.md` (v1, 11/11/2026). Decisões do usuário em
> 16/11/2026: vale para **todas as áreas**; o cliente se identifica pelo **CPF enviado no WhatsApp**; o bot só
> responde se o número do WhatsApp for o **celular cadastrado no VIOS** para aquele CPF; a leitura do VIOS é
> pela tela, **como a Orelha** (sem API). Princípios da seção 2 do plano v1 continuam valendo (na dúvida,
> equipe; lista branca; só leitura; notícia ruim é com gente).

## 1. Peças

```
[cliente] ─WhatsApp─▶ [bot (Node, Render ou Mac)] ◀── HTTPS, só saída do Mac ── [coletor (Python, Mac do escritório)]
                         guarda o pedido com o CPF                              busca pedidos a cada 5 s,
                         cifrado (RSA) por ≤ 5 min                              lê o VIOS (navegador da Orelha),
                         recebe a ficha mínima                                  devolve ficha mínima
```

- O **coletor busca os pedidos** (polling). O Mac nunca recebe conexão de fora: funciona com o bot no Render
  e atrás do roteador do escritório.
- O bot **nunca** guarda o CPF em claro: ao receber, cifra com a chave pública do coletor
  (`CONSULTA_CHAVE_PUBLICA`, RSA-OAEP SHA-256, PEM em base64) e descarta o texto. Só o coletor decifra.
- O coletor **nunca** recebe o número do WhatsApp. Ele devolve os telefones do cadastro já como
  `HMAC-SHA256(CONSULTA_CHAVE_TELEFONE, telefone_normalizado)`; o bot calcula o mesmo HMAC do número de quem
  escreveu e compara.

## 2. Contrato HTTP (o bot expõe, o coletor chama)

Autenticação de toda chamada: cabeçalhos `X-Consulta-Timestamp` (epoch ms) e `X-Consulta-Assinatura` =
hex de `HMAC-SHA256(CONSULTA_SEGREDO, timestamp + "\n" + método + "\n" + caminho + "\n" + corpo)`
(corpo vazio no GET). Recusar se a diferença de relógio passar de 5 min ou a assinatura não bater
(comparação em tempo constante). Resposta de recusa: 401 sem detalhe. Rota desligada (`CONSULTA_PROCESSO`
≠ `ligada`): 404.

### `GET /consulta/pendentes`
Resposta 200: `{ "pedidos": [ { "id": "<uuid>", "cpfCifrado": "<base64>" } ] }` (no máximo 5, mais antigos
primeiro). Ao entregar, o pedido passa a `em_andamento` (não é entregue de novo por 2 min; depois volta a
`pendente` se não houver resultado, até expirar).

### `POST /consulta/resultado`
Corpo (JSON, validado com zod **estrito** — campo extra em qualquer nível = 422 e o pedido vira `erro`):

```json
{
  "id": "<uuid>",
  "status": "ok" | "nao_encontrado" | "erro",
  "lidoEm": "2026-11-16T14:03:00-03:00",
  "telefones": ["<hex hmac>", "..."],
  "processos": [
    {
      "ref": "P1",
      "area": "previdenciario",
      "situacao": "ativo",
      "fase": "aguardando_pericia_inss",
      "desde": "2026-10-03",
      "proximo": { "tipo": "pericia", "data": "2026-11-20" },
      "encaminhar": false,
      "atualizacao": true
    }
  ]
}
```

- `status: "nao_encontrado"`: CPF sem cadastro ou sem processo visível → `telefones: []`, `processos: []`.
- `status: "erro"`: VIOS fora, login falhou, tela mudou → bot encaminha (motivo `consulta_falhou`).
- `ref`: `P1`, `P2`… na ordem que o coletor devolve; nunca número CNJ nem CI.
- `area` (lista fechada): `previdenciario`, `trabalhista`, `civel`, `familia_sucessoes`, `criminal`,
  `tributario`, `empresarial` (societário, contratos, compliance, holding, INPI, comercial), `imobiliario`,
  `administrativo`, `ambiental`, `outra`.
- `situacao`: `ativo` | `encerrado`. v1 lê só ativos.
- `fase`: código da lista da seção 4, ou `desconhecida`.
- `desde`: `YYYY-MM-DD` ou `null`.
- `proximo`: `{ tipo: "pericia" | "audiencia", data: "YYYY-MM-DD" }` ou `null`. O bot só mostra a data se
  `CONSULTA_MOSTRAR_DATA=sim` (padrão: não mostra; pergunta aberta 4 do plano v1).
- `encaminhar`: `true` quando o coletor já sabe que é caso de gente (segredo de justiça, fase sensível,
  dado incompleto).
- `atualizacao`: `true` se há ao menos uma tarefa aberta (não concluída e não cancelada) na ficha, de qualquer
  tipo (inclusive os que o mapa ignora): a marca amarela do VIOS. Booleano puro, nenhum dado da tarefa.
  `false` também quando a ficha não foi lida ou veio cortada (aí `encaminhar` é `true`).
  **Ordem de implantação:** atualizar o bot ANTES do coletor (o bot antigo recusa o campo novo, zod estrito).
- Resposta 200 `{ "ok": true }`. Id desconhecido ou expirado: 410.

Telefone normalizado (os dois lados, idêntico): só dígitos; tira `0` e `55` do começo; precisa sobrar
DDD (2) + número (8 ou 9); resultado = `"55" + DDD + últimos 8 dígitos` (ignora o nono dígito, RN15.4).
Fixo (8 dígitos começando com 2–5) também entra (o cliente pode usar WhatsApp Business num fixo). Número que
não normaliza é descartado.

## 3. Coletor (repo `automacao-vios`, pasta `consulta/`)

Reaproveita `orelha/nucleo` (navegador protegido, login, `buscar_get`, `ler_tabela_html`, bloqueio de envio).
Por pedido:

1. Decifra o CPF (chave privada só no Mac, `consulta/.env`, arquivo 600). Valida os dígitos verificadores.
2. **Processos**: lista `?pag=sys/processos/processos-lista.php` por GET com `pesq[cpfcnpj]=<CPF>`,
   `pesq[filtros_multi][]=ativos`, `pesq[limit]=30` e os demais campos padrão (a URL completa do formulário
   está no mapa). Lê CI, área, e o que a tabela der. Nenhum processo → `nao_encontrado`.
3. **Pessoa / telefones**: lista de pessoas `?pag=sys/clientes/clientes.php&pesq[busca]=<CPF>&Pesq=Pesquisar`
   → link `clientes-vis.php&clientes_id=<id>` → formulário `?pag=sys/clientes/clientes.php&act=edit&clientes_id=<id>`
   lido por GET **sem renderizar e sem enviar** (só ler `value` dos inputs). Campos: `form[cpfcnpj]` (conferir
   que é o mesmo CPF; se não for, `erro`), `form[tel_celular]`, `form[tel_residencial]`, `form[tel_comercial]`.
   **Não** usar `clientes_x_contatos[...]` (são outras pessoas). Mais de um cadastro com o mesmo CPF → usar
   todos os telefones de todos.
4. **Fase** de cada processo: ficha `?pag=sys/processos/processos-vis.php&processos_id=<CI>` → tarefas
   (ver como o relatório da branch `developer` lê: `bot/js/ficha.js`, `bot/processo_ficha.py`). Regra:
   tarefa **aberta** mais recente (o passo atual) → senão a **concluída** mais recente (sem canceladas). O
   **tipo** da tarefa (nunca o comentário/descrição) passa por `consulta/fases_vios.yaml` (seção 4) → código.
   `proximo`: tarefa aberta cujo tipo é perícia ou audiência com data prevista ≥ hoje.
   `atualizacao`: `true` se existe qualquer tarefa aberta (não concluída, não cancelada), mesmo de tipo ignorado;
   só o booleano sai. Ficha não lida ou cortada: `false`.
   Se a ficha indicar segredo de justiça (rótulo com "segredo" ou "sigilo"), `encaminhar: true`.
5. Monta o JSON da seção 2 por **lista branca** (só os campos do contrato), assina e envia.

Laço: `python -m consulta` com intervalo `CONSULTA_INTERVALO=5` s; uma sessão do Chrome headless reaproveitada;
relogar se a sessão cair. Log sem CPF, sem nome, sem CI (só id do pedido, status e tempos). Testes `unittest`
com HTML de fixture **fictício** (nada de dado real), incluindo: campo fora do contrato nunca sai; comentário
de tarefa nunca sai; tipo desconhecido → `desconhecida`; CPF divergente no cadastro → `erro`; telefones
normalizados e com HMAC conferidos com vetores fixos (os mesmos do lado do bot).

## 4. Fases (códigos) e mapa dos tipos de tarefa

Lista fechada de códigos (o bot tem um texto aprovado para cada; o coletor tem o mapa tipo → código):

| Código | Ideia do texto ao cliente | Encaminha? |
|---|---|---|
| `triagem_documentos` | equipe analisando seus documentos | não |
| `aguardando_documentos` | falta documento seu; a equipe vai te chamar | **sim** |
| `pedido_em_preparo` | estamos preparando o pedido/ação | não |
| `aguardando_agendamento_inss` | pedido sendo agendado no INSS | não |
| `em_analise_inss` | pedido em análise no INSS | não |
| `exigencia_inss` | o INSS pediu algo; a equipe está cuidando | não |
| `aguardando_pericia_inss` | fase de perícia/avaliação no INSS | não |
| `acao_em_preparo` | ação judicial sendo preparada | não |
| `acao_protocolada` | ação protocolada, aguardando andamento da Justiça | não |
| `aguardando_pericia_judicial` | fase de perícia na Justiça | não |
| `aguardando_audiencia` | fase de audiência | não |
| `aguardando_decisao` | aguardando decisão/julgamento | não |
| `em_recurso` | fase de recurso | não |
| `decisao_proferida` | saiu decisão — a equipe vai explicar | **sim** (boa ou ruim, v1) |
| `implantacao_beneficio` | benefício em implantação | não |
| `cumprimento_pagamento` | fase de cumprimento/pagamento | **sim** (envolve valor) |
| `encerramento` | processo sendo encerrado | **sim** |
| `desconhecida` | — | **sim** |

O mapa (`consulta/fases_vios.yaml` no coletor) casa o **tipo-base** (tipo sem cidade, sem ano e sem
"(PREVIDENCIÁRIO)") por prefixo/regex. Tipos de comunicação interna ("AVISAR…", "RETORNO AO CLIENTE…",
"LEMBRAR…", financeiro, prospect, planejamento) **não** definem fase: o coletor pula essas tarefas e usa a
próxima. Catálogo do previdenciário levantado em 16/11 em `consulta/tipos-previdenciario.txt`. Tipos das outras
áreas ainda não levantados → caem em `desconhecida` (equipe) até o mapa crescer.

## 5. A conversa (bot)

Liga com `CONSULTA_PROCESSO=ligada` (padrão desligada: comportamento de hoje, RN07). Em `MODO=teste` só para
`NUMEROS_TESTE`.

1. Cliente pergunta do processo (hoje cai em `sensiveis.andamento`). Se a consulta estiver ligada e o
   remetente tiver telefone conhecido (não `@lid` sem telefone), o bot responde (texto `consulta.pedir_cpf`,
   aprovado pelo setor): pede o CPF só com números, diz que serve só para achar o cadastro e que não fica
   guardado, e lembra que *0* fala com a equipe. Sessão vai para `aguardando_cpf` (vale 10 min).
   `@lid` sem telefone → encaminha como hoje.
2. CPF inválido (dígitos verificadores) → pede de novo uma vez; segunda falha → equipe.
   Mensagem que não parece CPF (texto, menu) → sai do fluxo e segue o motor normal.
3. CPF válido → cifra, grava o pedido, apaga o texto da memória/sessão, responde `consulta.consultando`
   ("Um instante, estou consultando…"). Sessão `consultando`.
4. Resultado chega:
   - `ok` e algum hash de `telefones` = hash do remetente → monta a resposta (item 5).
   - `nao_encontrado` **ou** telefone não bate → **a mesma mensagem** (`consulta.nao_confirmado`: não consegui
     confirmar seu cadastro por este número; vou passar para a equipe) + encaminhamento (motivo
     `consulta_nao_confirmada`). Nunca dizer se o CPF existe.
   - `erro` → `consulta.falhou` + encaminhamento (`consulta_falhou`).
5. Resposta: só processos `ativo`. Um processo: texto da fase (`conteudo/fases.yaml`, com `{desde}` e,
   se ligado, `{proximo}`) + "Informação do sistema do escritório de {lidoEm}." + rodapé "Digite *0* para
   falar com a equipe". Vários: "Encontrei N processos: *1* {área}, *2* {área}… Qual deles?" → depois o texto
   do escolhido. `encaminhar: true`, fase `desconhecida` ou texto da fase sem `status: aprovado` (em
   `MODO=producao`) → encaminha (motivo `consulta_fase_sensivel`) sem dizer a fase.
6. Sem resultado em 3 min → `consulta.demorou` + encaminhamento (`consulta_sem_resposta`).
7. Limite: 3 consultas por número por dia (contador por hash do número). Passou → equipe.
8. Registro: eventos `consulta_pedida`, `consulta_respondida`, `consulta_encaminhada{motivo}`. **Nunca** CPF,
   fase, área, data nem hash de telefone em log/evento/relatório. Pedido apagado ao concluir ou expirar
   (5 min); expirados limpos a cada minuto.
9. Exceção formal à RN01/RN12.1 (não pedir dado): só neste fluxo, só o CPF, só depois de o cliente pedir
   a situação do processo. O aviso de privacidade ganha uma frase sobre isso (setor aprova).

## 6. Variáveis

Bot: `CONSULTA_PROCESSO` (`ligada`|`desligada`), `CONSULTA_SEGREDO`, `CONSULTA_CHAVE_TELEFONE`,
`CONSULTA_CHAVE_PUBLICA` (PEM base64), `CONSULTA_MOSTRAR_DATA` (`sim`|`nao`), `CONSULTA_LIMITE_DIA` (3).
Coletor: `CONSULTA_BOT_URL`, `CONSULTA_SEGREDO`, `CONSULTA_CHAVE_TELEFONE`, `CONSULTA_CHAVE_PRIVADA`
(caminho do PEM), `CONSULTA_INTERVALO`, credenciais VIOS (mesmo formato da Orelha; usuário só de leitura
recomendado). `scripts/gerar-chaves-consulta` (no bot) gera o par RSA-4096 e os dois segredos.

## 7. Vetores de teste compartilhados

`CONSULTA_CHAVE_TELEFONE = "chave-de-teste"`:

| Entrada | Normalizado |
|---|---|
| `(88) 99284-3164` | `558892843164` |
| `5588992843164` | `558892843164` |
| `088 9284-3164` | `558892843164` |
| `+55 (85) 3256-1234` | `558532561234` |
| `99284-3164` (sem DDD) | descartado |

O HMAC esperado de cada normalizado é calculado nos testes dos dois lados com a mesma função de referência
(hex minúsculo); um teste de cada lado fixa o valor de `558892843164` para garantir que os dois batem.
