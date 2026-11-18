# Alerta de Execução Provisória — TRT7

Documento de base do projeto: o problema, o que já sabemos e o que vamos construir.
Atualizado em 18/11/2026.

---

## 1. O problema

- Um cliente (empresa) é reclamada num processo trabalhista no **TRT7**: o **processo principal**.
- Durante esse processo, o advogado da parte contrária pode entrar com uma **execução provisória**.
- A execução provisória entra como **processo novo**, com número próprio, **sem ligação nenhuma** com o principal. Pode até ter outra classe ou cair em outra vara.
- Só **depois de um tempo** o juiz reconhece a ligação entre os dois processos. Esse reconhecimento fica registrado **no processo principal, dentro do PJe do TRT7**.
- O escritório **não é avisado** de nada disso: nem do processo novo, nem do reconhecimento. Não chega e-mail, publicação ou intimação no nome do nosso advogado, porque ele não está cadastrado no processo novo.
- Resultado no caso real: ninguém viu a tempo e o cliente teve **contas bloqueadas**.

## 2. O que já temos e por que não pega esse caso

| O que já existe | Por que não resolve |
|---|---|
| Monitoramento pela **OAB** do Dr. Roneely (TRT7, TJCE, TRF5) | Nosso advogado não está cadastrado no processo novo, então a OAB não aparece nele |
| Movimentações via **DJEN / DataJud** | O processo novo não tem relação com o principal; o reconhecimento do juiz não é publicado como intimação para nós |
| Base interna no **VIOS** | Só tem os processos que o escritório já conhece |

## 3. O fato que resolve

> **A única ligação garantida entre o processo novo e o principal é a empresa: o nome e o CNPJ.**
> O CNPJ é obrigatório no cadastro da parte. Assim que a execução provisória é distribuída, ela já aparece numa busca pelo CNPJ da empresa no PJe do TRT7.

Ou seja: se pesquisarmos o CNPJ de cada cliente todo dia e compararmos com o VIOS, qualquer processo novo contra ele aparece, inclusive a execução provisória, antes do reconhecimento do juiz e antes do bloqueio.

## 4. A solução: dois robôs

### Robô A: processo novo contra o cliente (prioridade 1)
Descobre a execução provisória **no dia em que ela entra**.

1. Todo dia de manhã, pesquisa no PJe do TRT7 o **CNPJ de cada cliente** da lista.
2. Compara os números encontrados com os processos já cadastrados no **VIOS**.
3. Para cada número **novo**, abre o processo e lê: classe, vara, data de distribuição, autor, advogado e, se possível, a petição inicial.
4. Classifica:
   - 🔴 **Alerta vermelho (na hora):** a classe é de execução (Execução Provisória em Autos Suplementares / ExProvAS, Cumprimento Provisório de Sentença / classe 157, Cumprimento de Sentença), **ou** a petição fala em "execução provisória", **ou** cita o número de um processo nosso.
   - 🟡 **Resumo diário:** qualquer outra ação nova contra o cliente (ex.: reclamação trabalhista nova).
5. Se o autor ou o advogado for o mesmo de algum processo principal, o alerta mostra isso, para ajudar a identificar de onde veio. Não é condição para alertar.
6. Envia o alerta (e-mail e/ou WhatsApp) para o advogado responsável e o setor de Execução.

### Robô B: reconhecimento do juiz no processo principal (prioridade 2)
Segunda camada de segurança: avisa quando o juiz liga os processos.

1. Todo dia, abre cada **processo principal** da lista de risco no PJe do TRT7.
2. Guarda uma "foto": movimentações, documentos juntados e processos associados.
3. Compara com a foto do dia anterior. Alerta se aparecer:
   - processo associado novo;
   - número de processo diferente do principal;
   - palavras como "execução provisória", "associado", "dependência", "autos suplementares", "cumprimento provisório".
4. Ajustar as regras exatas depois de ver **como o reconhecimento aparece** no caso real (pendência 2).

### Exemplo de alerta (Robô A)
```
🔴 Possível execução provisória contra EMPRESA X LTDA
Processo novo: 0001234-56.2026.5.07.0024 (Cumprimento Provisório de Sentença), 2ª Vara do Trabalho de Sobral
Autor: Fulano de Tal, adv. Beltrano (OAB/CE 00000)
Cita o processo principal 0000987-65.2025.5.07.0024, que já está no VIOS
Distribuído em 16/11/2026, ainda não está no VIOS
```
**Depois do alerta:** o advogado abre o processo, se habilita nos autos (a partir daí o monitoramento por OAB passa a cobrir esse processo) e toma as medidas antes do bloqueio.

## 4.1 Acesso ao TRT7 (decidido em 18/11/2026)

- **Acesso via Selenium + Presto**, que já funciona no TRT7: o Presto entra no tribunal e o Selenium controla o navegador.
- **Descartado:** MNI (webservice oficial). Exige ofício à Presidência do TRT7 e acordo de cooperação, um processo lento e incerto para escritório privado.
- **Como usar a sessão:**
  1. O Selenium faz o login com o Presto, como já faz hoje.
  2. Com a sessão aberta, o robô faz a busca por CNPJ (Robô A) e abre o processo principal (Robô B).
  3. Melhoria opcional: pegar os cookies e o token da sessão do Selenium e chamar direto os endereços internos que a própria página do PJe usa (os que aparecem na aba Rede do F12). Assim o robô recebe os dados em JSON, sem clicar nem ler HTML: é mais rápido e quebra menos.
- **Sem serviços pagos** (decidido): nada de APIs privadas como Judit ou Escavador.
- **Robô A, caminhos gratuitos em ordem de preferência:**
  1. Busca por CNPJ da parte dentro do PJe do TRT7 (Selenium + Presto), se a tela existir para advogado.
  2. Portal de Serviços do PDPJ, que busca por CPF/CNPJ da parte, com a mesma sessão (o login do PJe passa pelo PDPJ).
  3. Se nenhuma busca por CNPJ funcionar: o DataJud (CNJ, gratuito, sem login) lista os processos novos do TRT7 de classe de execução provisória ou cumprimento de sentença, e o Selenium abre cada um e confere se o CNPJ de um cliente está no polo passivo.
- **Cuidados:** consultar só os CNPJs e processos da lista, uma vez por dia, com alguns segundos entre as buscas. Alguns TRTs bloqueiam contas que fazem consultas excessivas a processos de terceiros.

## 5. Quem entra na lista de vigilância

Arquivo exportado do VIOS com os processos trabalhistas do TRT7 em que:
- o cliente é a **reclamada**;
- já houve **condenação** (sentença ou acórdão);
- ainda há **recurso pendente** (a CLT só permite execução provisória até a penhora, na pendência de recurso).

Campos mínimos: `numero_processo`, `cliente`, `cnpj`, `vara`, `advogado_responsavel`, `reclamante`, `advogado_contrario` (opcional).

> O Robô A pode rodar para **todos os clientes**, e não só para os da lista de risco. Assim também pega qualquer ação nova contra eles.

## 6. Pendências antes de codar

1. [ ] **Teste manual (o mais importante):** pesquisar o CNPJ da empresa que teve o bloqueio no PJe do TRT7 (ou no Portal de Serviços do PDPJ, que busca por CNPJ da parte) e confirmar se a execução provisória do caso aparece na lista. Se aparecer, o método está validado.
2. [ ] **Print ou texto de como o reconhecimento do juiz aparece** no processo principal: movimentação, documento ou aba de processos associados (para o Robô B).
3. [x] **Forma de acesso ao PJe do TRT7:** Selenium + Presto (já funciona).
3.1 [ ] **Logado no PJe do TRT7, achar a tela que busca processo pelo CNPJ da parte** e anotar o caminho no menu. Com o F12 aberto (aba Rede), fazer uma busca e salvar a requisição que traz a lista de processos.
3.1.1 [ ] Se a busca por CNPJ não existir no PJe: testar, com a mesma sessão, o Portal de Serviços do PDPJ (busca por CNPJ da parte, filtro pelo TRT7).
3.2 [ ] **Compartilhar o trecho de login do Selenium com o Presto** (sem senhas), para o módulo `acesso_pje.py` reaproveitar.
4. [ ] **Número do processo do caso real** (principal e execução provisória): vira o caso de teste do robô.
5. [ ] **Classe que o TRT7 usa** para execução provisória (ExProvAS ou Cumprimento Provisório de Sentença): conferir no caso real.
6. [ ] **Canal de alerta:** e-mail, WhatsApp ou os dois? Para quem vai?

## 7. Estrutura do diretório (proposta)

```
alerta-execucao-provisoria/
├── README.md                 # este documento
├── requirements.txt
├── .env.example              # caminho do certificado, senhas, SMTP/WhatsApp (o .env real fica fora do Git)
├── .gitignore                # .env, *.pfx, *.p12, dados/, logs/
├── config/
│   └── clientes.csv          # lista de vigilância exportada do VIOS
├── src/
│   ├── acesso_pje.py         # login/sessão no PJe do TRT7 (Selenium + Presto)
│   ├── busca_cnpj.py         # Robô A: busca processos por CNPJ
│   ├── detalhe_processo.py   # abre um processo e extrai classe, vara, partes, advogados, petição
│   ├── classificador.py      # regras de alerta vermelho / resumo diário
│   ├── vigia_principal.py    # Robô B: foto e comparação do processo principal
│   ├── vios.py               # lê a exportação do VIOS e diz o que já é conhecido
│   ├── estado.py             # guarda o que já foi visto (SQLite)
│   └── alertas.py            # envio por e-mail/WhatsApp
├── dados/
│   └── estado.sqlite         # criado automaticamente
├── logs/
├── tests/
│   └── caso_real/            # dados do caso do bloqueio, para validar o robô
└── main.py                   # roda tudo: python main.py robo-a | robo-b | tudo
```

**Segurança:** o certificado A1 e as senhas nunca vão para o repositório. Ficam só no `.env` local ou num cofre de senhas.

## 8. Ordem de construção

1. **Fase 0: validação manual.** Pendências 1 a 4.
2. **Fase 1: Robô A** com alerta por e-mail, testado com o caso real.
3. **Fase 2: Robô B** (vigia do processo principal).
4. **Fase 3: integração.** Alerta por WhatsApp, painel junto do monitoramento por OAB que já existe e, se fizer sentido, cadastro automático do processo novo no VIOS.
5. **Agendamento:** rodar todo dia útil de manhã (e, se der, uma segunda vez à tarde).

## 9. Riscos e plano B

- **Mudança no PJe ou no Presto:** o acesso via Selenium pode quebrar quando o tribunal muda a tela. Plano B: os caminhos 2 e 3 do Robô A (item 4.1), mais a busca pelo nome do cliente no DJEN, que é gratuita e não depende de login.
- **Bloqueio antes de qualquer aviso:** o Robô A reduz esse risco ao mínimo, porque alerta no dia seguinte à distribuição. O Robô B é a segunda camada.
- **Muitos alertas** (clientes grandes com muitas ações): por isso a divisão entre alerta vermelho e resumo diário.

## 10. Complemento opcional já escrito

Já existe um script inicial (`alerta_exec_provisoria.py`) que usa as fontes públicas do CNJ (DataJud e DJEN), sem entrar no PJe. Ele **não resolve o caso principal**, porque supõe que a execução já nasce com a classe certa e na mesma vara. Pode servir como camada extra e gratuita: buscar o nome do cliente no DJEN do TRT7.
