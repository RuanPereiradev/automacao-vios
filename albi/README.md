# Albi — bot do Sonar (Leme Forense)

Bot separado do Ultron e do Zangão: tudo dele fica nesta pasta (`.venv`, `.env`, `logs/`,
`saida/`) e ele não usa nada do `bot/`. Entra em https://sonar.lemeforense.com.br/login.

**Status:** recebe um `.txt` com um CPF/CNPJ por linha e, para cada um, preenche Pesquisa de
Processos > Nova Pesquisa até o passo 2 ("Pedido", com o valor). **Não confirma nenhum pedido.**

## O que ele faz

1. Abre a tela de login e preenche CPF/CNPJ, e-mail e senha.
2. Se cair na tela de conflito (`/login-conflito`, quando já tem sessão aberta em outro lugar),
   clica em **Encerrar a outra sessão**; se o Sonar voltar para a tela de login, entra de novo.
3. Para cada linha válida do `.txt`: vai direto para `/modulos/pesquisa-processos/novo-pedido`
   (a tela do botão **Iniciar Pesquisa**), preenche o Identificador (se tiver), escolhe o tipo
   **CPF/CNPJ**, digita o documento e clica em **Continuar**.
4. No passo 2 ("Pedido") confere se o documento mostrado é o mesmo, lê o valor e **para ali**:
   nunca clica em "Confirmar Pedido".

## O arquivo .txt

Um CPF ou CNPJ por linha, com ou sem pontuação. Depois de `;` vem o **Identificador Projeto**
(opcional). Linha vazia ou começando com `#` é ignorada.

```
12.345.678/0001-90 ; Cliente X
123.456.789-00
98765432000110 ; Projeto Y
```

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

O `.env` nunca vai para o git. Os campos da tela (`LOGIN_CAMPO_*`, `LOGIN_BOTAO`) já vêm
certos; só mude se a tela do Sonar mudar.

## Rodar

```bash
./rodar.sh                         # só entra e abre a tela de novo pedido (confere o .env)
./rodar.sh --arquivo pedidos.txt   # preenche um pedido por linha, sem confirmar
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

## Mascote

`mascote/mascote-gordo-de-pe.html` (22×19 pixels). O mesmo desenho está na Vila 03
(`doc/vila/ligar_albi.py`) e na página `/albi` (`bot/templates/_albi.html`).
