# Consulta de processo: coletor (RN26)

Robô Python que roda no Mac do escritório, lê o VIOS **só por leitura** e responde aos pedidos do bot de
WhatsApp. Especificação: [CONTRATO.md](CONTRATO.md). Reaproveita a Orelha (`orelha/nucleo`: Chrome protegido,
login, bloqueio de envios) sem alterá-la.

## O que nunca sai do Mac

CPF em claro, nome, telefone em claro, número CNJ, CI, texto de tarefa, comentário, valor, observação.
Para o bot vão só: `status`, `lidoEm`, os telefones do cadastro já em HMAC, e por processo `ref` (P1, P2),
`area`, `situacao`, `fase`, `desde`, `proximo` e `encaminhar`. O JSON é montado campo a campo (lista branca,
`montagem.py`). O CPF chega cifrado (RSA); a chave privada fica neste Mac. O log tem só id do pedido,
status e tempos (e um filtro mascara qualquer sequência com cara de CPF ou telefone).

## Instalar (ao lado da Orelha)

```bash
cd automacao-vios            # a pasta que tem orelha/ e consulta/
orelha/instalar.sh           # se a Orelha ainda não tem .venv
orelha/.venv/bin/pip install -r consulta/requirements.txt
cp consulta/.env.example consulta/.env && chmod 600 consulta/.env
```

## Gerar as chaves (no repositório do bot)

`scripts/gerar-chaves-consulta` cria o par RSA-4096 e os dois segredos.
- Chave **pública** -> `CONSULTA_CHAVE_PUBLICA` do bot. Chave **privada** -> um arquivo `.pem` neste Mac
  (`chmod 600`), caminho em `CONSULTA_CHAVE_PRIVADA`.
- `CONSULTA_SEGREDO` e `CONSULTA_CHAVE_TELEFONE`: o mesmo valor no bot e em `consulta/.env`.
- Preencha também `SISTEMA_USUARIO` e `SISTEMA_SENHA` (usuário só de leitura, se o VIOS permitir).

## Ficha do processo: `ORELHA_PARADOS_LIBERAR_XHR=auto`

A tabela de tarefas da ficha (Vue) carrega por XHR POST. O bloqueio de envios da Orelha barra POST e, sem
liberar, a tabela vem vazia e toda fase sai `desconhecida`. Com `auto` (já no `.env.example`), a leitura
libera só fetch/XHR quando percebe que o bloqueio barrou o carregamento; formulário e sendBeacon seguem
barrados. Nada é gravado no VIOS.

## Fases: todas as áreas

`fases_vios.yaml` cobre os 551 tipos do catálogo (`tipos-todos.txt`) com regras genéricas (recurso,
audiência, perícia, decisão, cumprimento/pagamento, encerramento...). Financeiro, controladoria, contrato,
comercial, reunião e comunicação (AVISAR, RETORNO, LEMBRAR, INFORMAR, DESPACHAR, ACOMPANHAMENTO) são
`ignorar`. O que não casa vira `desconhecida` e o bot encaminha para a equipe.

## Rodar

```bash
consulta/rodar.sh --simulado --uma-vez   # sem VIOS, sem senha, sem rede: fixtures + bot falso em memória
consulta/rodar.sh --uma-vez              # um ciclo de verdade (busca pedidos, lê o VIOS, devolve)
consulta/rodar.sh                        # laço: a cada CONSULTA_INTERVALO s
```

No Mac do escritório, deixe ligado pelo launchd (sobe no login, reinicia se cair):

```bash
consulta/servico_mac.sh instalar   # instala consulta/requirements.txt na .venv da Orelha, confere o .env e liga
consulta/servico_mac.sh status     # rodando? último código de saída
consulta/servico_mac.sh log        # acompanha consulta/logs/launchd.log
consulta/servico_mac.sh parar      # desliga
```

No mesmo Mac do bot: `CONSULTA_BOT_URL=https://localhost:3000` e `CONSULTA_CERTIFICADO` apontando para
`dados/certificado/certificado.pem` da pasta do bot (o instalador do bot gera). Códigos de saída: 0 ok,
1 bot inacessível (`--uma-vez`), 2 configuração, 3 bloqueio de envios inativo (nada é lido).

## Testes

```bash
orelha/.venv/bin/python -m unittest discover -s consulta/tests -t .
```

## Antes de ligar de verdade: conferir na tela real (só olhar)

O coletor foi escrito sem ver as telas. Confira, e ajuste a variável indicada se algo for diferente:

1. Lista de processos com `pesq[cpfcnpj]`: o filtro existe, aceita CPF com máscara ou só dígitos
   (`CONSULTA_CPF_FORMATO`) e a tela repete o valor no campo (`CONSULTA_EXIGIR_ECO_CPF`).
2. Busca de pessoas `clientes.php&pesq[busca]=<CPF>`: acha pelo CPF e os links são `clientes-vis.php&clientes_id=N`.
3. Formulário `act=edit`: os campos se chamam `form[cpfcnpj]`, `form[tel_celular]`, `form[tel_residencial]`,
   `form[tel_comercial]` e o valor vem no atributo `value` do HTML recebido por GET.
4. Ficha: colunas da tabela de tarefas (1 = CI, 2 = tipo, 5 = datas; `ORELHA_PARADOS_COLUNAS_TAREFA`) e se
   a data da perícia/audiência é a de "Para conclusão" (`fases.py`, `_proximo`).
5. Como a ficha mostra segredo de justiça (rótulo ou selo com "segredo"/"sigilo").
6. A coluna de área da lista (`pr_areas_nome`) e o texto das áreas (`leitura.py`, `area_codigo`).

O mapa tipo -> fase (`fases_vios.yaml`) deve ser revisado por quem conhece os fluxos do setor.
