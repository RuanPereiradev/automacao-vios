# Albi — bot do Sonar (Leme Forense)

Bot separado do Ultron e do Zangão: tudo dele fica nesta pasta (`.venv`, `.env`, `logs/`,
`saida/`) e ele não usa nada do `bot/`. Entra em https://sonar.lemeforense.com.br/login.

**Status:** entra no Sonar e abre Pesquisa de Processos > Nova Pesquisa
(`/modulos/pesquisa-processos/novo-pedido`). As próximas etapas entram em `main.py`, depois disso.

## O que ele faz

1. Abre a tela de login e preenche CPF/CNPJ, e-mail e senha.
2. Se cair na tela de conflito (`/login-conflito`, quando já tem sessão aberta em outro lugar),
   clica em **Encerrar a outra sessão**; se o Sonar voltar para a tela de login, entra de novo.
3. Vai direto para `/modulos/pesquisa-processos/novo-pedido` (a mesma tela do botão
   **Iniciar Pesquisa**) e confirma que ela abriu.

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
./rodar.sh             # entra no Sonar, diz "Login OK" e "Tela de novo pedido aberta" (ou o motivo)
```

Log em `albi/logs/albi.log` (a senha e o CPF/CNPJ inteiro nunca aparecem; do CPF/CNPJ só
os 2 últimos números). Se falhar, print da tela em `albi/logs/erro_*.png`.
