# Albi — bot do Sonar (Leme Forense)

Bot separado do Ultron e do Zangão: tudo dele fica nesta pasta (`.venv`, `.env`, `logs/`,
`saida/`) e ele não usa nada do `bot/`. Entra em https://sonar.lemeforense.com.br/login.

**Status:** recebe um `.txt` por empresa (`CPF ; nome`) e, para cada pessoa, faz a Pesquisa de
Processos no Sonar: preenche, escolhe o Sacado, **confirma o pedido** (com `--confirmar`; R$ 15,70
cada), espera o resultado, baixa o resultado de cada pessoa (PDF do pedido e, de quem tem processos,
a planilha) e escreve o `resultado.txt`.

## O que ele faz

1. Abre a tela de login e preenche CPF/CNPJ, e-mail e senha.
2. Se cair na tela de conflito (`/login-conflito`, quando já tem sessão aberta em outro lugar),
   clica em **Encerrar a outra sessão**; se o Sonar voltar para a tela de login, entra de novo.
3. Para cada pessoa válida do `.txt`: vai direto para `/modulos/pesquisa-processos/novo-pedido`
   (a tela do botão **Iniciar Pesquisa**), preenche o Identificador Projeto (**nome da empresa**),
   escolhe o tipo **CPF/CNPJ**, digita o documento e clica em **Continuar**.
4. No passo 2 ("Pedido") confere o documento mostrado, escolhe o **Sacado** (`SONAR_SACADO`; vazio =
   o escritório) e, só com `--confirmar`, clica em **Confirmar Pedido** e guarda o número.
5. Com todos confirmados, abre a página de cada pedido até o Sonar terminar (até `SONAR_ESPERA_MIN`
   minutos), salva a página de cada pedido em **PDF** (todos, inclusive "não consta"), clica em
   **Baixar Resultados** nos que têm processos encontrados e escreve o `resultado.txt` (por
   empresa: `CPF ; nome ; pedido ; resultado ; arquivos`).
   Para baixar tudo de novo sem comprar: `--baixar` (usa o número de cada pedido do registro).
6. No fim, `relatorio.py` lê as planilhas e escreve `relatorio.html`, `relatorio.pdf` e `processos.csv`:
   por empresa, o resumo de todos e cada processo de quem tem processos (número, tribunal, vara,
   ação, assunto, data, papel da pessoa, outra parte, valor e status). Para gerar de novo a partir
   do que já foi baixado (sem Sonar): `.venv/bin/python relatorio.py <pasta do resultado>`.
   Escreve também o `mensagem.txt`, com o resumo pronto para mandar a cada empresa (CPF mascarado). Na
   página, é o botão "Capturar resumo".
   E `mensagens_cac.txt`/`.json` (`mensagem_cac.py`): uma mensagem por pessoa com processos, no padrão da CAC
   ("*Beatriz Vasconcelos:* Informamos que…", "*1️⃣ Autor x Réu*", "Trata-se de…", situação e ressalva), sem IA.
   Para contar o que aconteceu em cada processo (contestação, audiências, sentença, recurso, trânsito em
   julgado, cumprimento, arquivamento), `datajud.py` consulta o número do processo na API pública do CNJ
   (DataJud) e guarda a resposta em `datajud/` na pasta do resultado. Os fatos narrados nas petições e os
   fundamentos das decisões não estão em nenhuma das fontes, e a mensagem diz isso. Sem resposta da API, o
   processo sai só com o cadastro do Sonar. Ver um processo: `.venv/bin/python datajud.py <número>`;
   desligar: `DATAJUD=false` no `.env` ou `relatorio.py <pasta> --sem-datajud`.
7. Não compra duas vezes: o registro `saida/pedidos_confirmados.json` é anotado antes de cada
   clique em Confirmar; CPF já pesquisado para a mesma empresa nos últimos 30 dias usa o pedido
   anterior. Erro depois do clique vira "Conferir no Sonar" (nunca clica de novo); 3 seguidos param.

## O arquivo .txt (modelo: `modelo_pedidos.txt`)

Um bloco por empresa: a linha `EMPRESA:` com o nome da empresa e, embaixo, uma pessoa por linha,
`CPF ; nome` (CPF com ou sem pontuação; serve CNPJ). `---` separa as empresas (opcional); linha
vazia ou começando com `#` é ignorada. O CPF pode vir antes ou depois do nome. Sem `EMPRESA:`,
o arquivo vale como uma lista só.

```
EMPRESA: Empresa A
123.456.789-09 ; Maria da Silva
987.654.321-00 ; João Souza
---
EMPRESA: Empresa B
111.444.777-35 ; Ana Lima
```

No Sonar, o **Identificador Projeto** (coluna "Projeto") de cada pesquisa fica o nome da empresa. Uma pessoa por
vez, na ordem do arquivo; se a sessão cair no meio, ele entra de novo e tenta a mesma pessoa
mais uma vez. O modelo vem com `000.000.000-00` de propósito: enviado sem trocar, o Albi recusa
tudo e nem entra no Sonar.

Antes de entrar no Sonar o Albi confere cada linha: 11 (CPF) ou 14 (CNPJ) números, dígito
verificador e repetidos. Linha com problema fica de fora (aparece no log e na página).

## Instalar (Mac ou Linux)

```bash
cd albi
./instalar.sh          # cria albi/.venv, instala as dependências e cria o .env a partir do .env.example
```

## Credenciais (`albi/.env`)

Abra `albi/.env` e preencha (o modelo comentado está em `.env.example`):

| variável | o que é |
| --- | --- |
| `SONAR_CPF_CNPJ` | CPF ou CNPJ do login (com ou sem pontuação) |
| `SONAR_EMAIL` | e-mail do login |
| `SONAR_SENHA` | senha; se tiver espaço ou " #", entre aspas simples: `SONAR_SENHA='minha senha #1'` |

Opcionais, da consulta ao DataJud (CNJ) para a mensagem da CAC: `DATAJUD=false` desliga;
`DATAJUD_PRAZO` (segundos no total, padrão 150); `DATAJUD_CHAVE` (a chave pública do CNJ já vem no
código; só preencha se o CNJ trocar).

O `.env` nunca vai para o git. Os campos da tela (`LOGIN_CAMPO_*`, `LOGIN_BOTAO`) já vêm
certos; só mude se a tela do Sonar mudar.

## Rodar

```bash
./rodar.sh                         # só entra e abre a tela de novo pedido (confere o .env)
./rodar.sh --arquivo pedidos.txt               # teste: preenche até o passo 2 e NÃO compra
./rodar.sh --arquivo pedidos.txt --confirmar   # COMPRA, espera e baixa (resultado em saida/<data_hora>/)
./rodar.sh --arquivo pedidos.txt --baixar      # NÃO compra: baixa de novo PDF e planilha dos pedidos já feitos
./rodar.sh --arquivo pedidos.txt --conferir    # só mostra o que seria feito (JSON, sem navegador)
```

Log em `albi/logs/albi.log` (a senha e o CPF/CNPJ inteiro nunca aparecem; do CPF/CNPJ só
os 2 últimos números). Se falhar, print da tela em `albi/logs/erro_*.png`.

## Pela página do Ultron (`/albi`) e na Vila 03

No servidor do Ultron (`./rodar_envio.sh`), a página `http://<IP>:5001/albi` tem a Vila 03 no
topo e a caixa para soltar o `.txt`. O Ultron guarda o arquivo em `saida/albi/` e roda
`main.py --arquivo <txt> --eventos` com o `.venv` e o `.env` daqui (um por vez). Com
`--eventos`, cada passo sai na saída padrão como `@evento {json}` e o Ultron repassa para a vila
(bot `albi`). Os eventos levam só o número da linha e o final do documento ("CNPJ final 77").
O log dessas execuções fica em `albi/logs/execucoes_ultron.log`.

Se o Albi estiver em outra pasta, defina `ALBI_PASTA` no `.env` do Ultron.

## Presto (Oystr): autos dos processos (em construção)

Para a mensagem da CAC ter os fatos de cada processo, o bot vai baixar os autos entrando no tribunal
pela extensão do Presto, o cofre de credenciais da Oystr que o escritório já usa. O plano atual não
tem a API de robôs da Oystr. Primeiro passo, no computador onde o bot vai rodar:

```bash
.venv/bin/python presto.py liberar-chrome # Mac, uma vez: liga "Permitir JavaScript de Apple Events" no Chrome (fecha e abre o Chrome)
.venv/bin/python presto.py entrar tjce1 # Mac: entra no tribunal pelo Presto no Chrome JÁ ABERTO (PIN em PRESTO_PIN)
.venv/bin/python presto.py processos --listar    # todos os relatórios, com quantos processos cada
.venv/bin/python presto.py processos --conferir  # qualquer computador: último relatório com processos dividido por tribunal
.venv/bin/python presto.py processos             # Mac: entra em cada tribunal pelo Presto e procura cada processo
.venv/bin/python presto.py aberto       # Mac: exploração (captura páginas no Chrome aberto)
.venv/bin/python presto.py copiar       # (alternativa) copia o perfil do Chrome que tem o Presto logado
# ou: .venv/bin/python presto.py preparar  # perfil novo: instalar o Presto e entrar
.venv/bin/python presto.py explorar https://pje.trt7.jus.br/primeirograu/login.seam
```

O `entrar` e o `processos` abrem cada tribunal pelo console do Presto: página **Sites**, procura o
tribunal na lista e clica (é assim que a extensão faz o login). Se o console pedir login, usam
`PRESTO_EMAIL` e `PRESTO_SENHA` do `albi/.env`. `--direto` pula o console.

O `processos` lê o `processos.csv` do último relatório (ou `presto.py processos <pasta>`), descobre o
tribunal pelo número CNJ (TJCE, TRT7, JFCE e TRF5; os outros ficam como "fora"), entra em cada um pelo
Presto e procura cada processo na consulta do tribunal (`--tribunal tjce1` só um; `--max N` só os N
primeiros). Grava `resumo.txt`/`resumo.json` (achou, não encontrado, captcha...) e as capturas em
`<pasta do relatório>/presto/<data_hora>/`. Ainda não baixa os autos.

O `explorar` salva em `logs/presto/<data_hora>/` o print, o HTML e os botões do pop-up da extensão e
de cada site pedido, sem precisar do DevTools. O perfil (`perfil_presto/`) guarda a sessão do Presto
e fica fora do git; a senha fica só no Presto.

## Mascote

`mascote/mascote-gordo-de-pe.html` (22×19 pixels). O mesmo desenho está na Vila 03
(`doc/vila/ligar_albi.py`) e na página `/albi` (`bot/templates/_albi.html`).
