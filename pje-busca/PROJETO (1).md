# Alerta de Execução Provisória — TRT7

Documento de base do projeto: o problema, o que já sabemos e o que vamos construir.
Atualizado em 19/11/2026 (seção 4.2: vigia diário VIOS → PJe; resultados dos testes de 19/11 nas pendências).

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

## 4.2 Vigia diário VIOS → PJe (planejado em 19/11/2026, ainda não implementado)

**Ideia:** no VIOS, as empresas do Judicial Trabalhista seguem um padrão: ficam na área trabalhista e quase sempre
ligadas a **um advogado**. Uma vez por dia o robô lê essa lista no VIOS, guarda uma "foto", compara com a do dia
anterior e descobre **empresas novas** e **processos novos**. Os números de processo do TRT7 entram numa fila de
**verificação periódica no PJe** (leitura da linha do tempo, que já funciona no `testar_processos.py`).

### O que já existe e será reaproveitado
| Peça | Onde está hoje | Uso aqui |
|---|---|---|
| Lista de processos do VIOS (`processos-lista.php`) com filtros **Área** `pesq[pr_areas_id][]`, **Advogado** `pesq[advogados_id][]`, **ativos** `pesq[filtros_multi][]=ativos` e **Mostrar** `pesq[limit]` (até 500) | `consulta/leitura.py`, `jarvis/nucleo/processos_grupo.py`, `orelha` | Montar a URL da pesquisa (só GET) |
| Leitura das linhas pelas colunas `data-id` (`pr_areas_nome`, `advogado_nome`, `clientes_nome`, `passivahtml`, `nro_proc_html`, `orgaos_nome`, `orgaos_uf`, `sinal_vinculo_processo`) | `jarvis/nucleo/processos_grupo.py` (`_ler_linha`) | Extrair cliente, parte passiva, CNJ, órgão, advogado, vínculo (principal/apenso) |
| Navegador protegido + login do VIOS só leitura (bloqueio de envios ligado antes do login) | `consulta/sessao.py` + `nucleo/` da Orelha | Entrar no VIOS sem risco de alterar nada |
| CNPJ do cliente (cadastro de pessoas, `form[cpfcnpj]`) | `consulta/leitura.py` (`url_lista_pessoas`) | Buscar o CNPJ **só das empresas novas** |
| Login no PJe pelo Presto e leitura da linha do tempo | `pje-busca/src/acesso_pje.py`, `pje-busca/testar_processos.py` | Verificação periódica dos processos |

Regra do repositório: como o `chrome_mac.py`, o pje-busca leva **cópias próprias** do que usar (não importa de `bot/`,
`jarvis/`, `consulta/`), para uma mudança lá não quebrar aqui.

### Fluxo diário
1. **VIOS (1x por dia, de madrugada ou antes do expediente)**
   - Pesquisa (GET, só leitura), conferida no VIOS em 23/11/2026:
     `?pag=sys/processos/processos-lista.php&menu_lateral=true&pesq[pr_areas_id][]=3&pesq[tipos_partes_id]=P`
     `&pesq[filtros_multi][]=ativos&pesq[limit]=9999999&Pesq=Pesquisar`
     (Área **3 = Trabalhista**; **P = cliente na Parte Passiva**, ou seja, a empresa é a reclamada; só ativos).
   - **Sem filtro de advogado** (ver "Números de 23/11/2026" abaixo): o padrão "1 advogado" não se confirmou.
   - A tela devolve no máximo **500 linhas** mesmo com Mostrar 9999999 (a área Trabalhista sem o filtro P parou em
     500). Se o rodapé `geratabela_total_quantidade_original` der 500, dividir a pesquisa (por advogado
     `pesq[advogados_id][]` ou por justiça `pesq[justicas_id][]`) até cada parte vir com menos de 500.
   - Guarda a foto do dia em `dados/vios/AAAA-MM-DD.json` (fora do git).
2. **Comparação com a foto anterior** (`dados/estado.sqlite`)
   - **Empresa nova** (cliente nunca visto): busca o CNPJ no cadastro do VIOS e entra na lista de CNPJs do Robô A.
   - **Processo novo** com número CNJ do TRT7 (segmento `5.07`): entra na fila de verificação do PJe.
   - **Processo que saiu da lista** (arquivado/baixado): sai da fila depois de 30 dias sem aparecer.
3. **PJe (verificação periódica dos processos da fila)**
   - Abre os detalhes (fluxo do `testar_processos.py`), guarda os IDs da linha do tempo e lê **só os documentos
     novos** desde a última verificação (leitura incremental).
   - Classifica a fase pelo texto: sentença, recurso interposto (de **qualquer parte**), acórdão, trânsito em
     julgado, execução, Sisbajud, desconsideração da personalidade jurídica.
   - Marca **"em risco de execução provisória"** quando há condenação + recurso pendente sem trânsito (art. 899 da
     CLT: recurso com efeito devolutivo, execução provisória permitida até a penhora). Esses processos passam a
     alimentar o Robô B.
4. **Relatório do dia** (`saida/vigia_AAAA-MM-DD.txt`): empresas novas, processos novos, documentos novos por
   processo, processos que entraram em risco e alertas (palavras-chave da seção 4).

### Números de 23/11/2026 (VIOS, só contagens)
| Pesquisa | Processos | Clientes distintos | TRT7 (`5.07`) | Outros |
|---|---|---|---|---|
| Área Trabalhista, ativos | 500 (teto da tela; total real maior) | 416 | 142 | TJCE (`8.06`) 343, TRT22 10 |
| **Área Trabalhista, ativos, cliente na parte passiva** | **363** | **161** (118 com nome de PJ) | **239** | TJCE 91, TRT22 11, TRT17 8, TRT16 8, outros 6 |

- Advogado principal na pesquisa com parte passiva: Roneely Feitosa 250, Francisco Johnys Vasconcelos Barbosa 112,
  outro 1. Auxiliares mais frequentes: JOHN 130, CARL 108, JOAQ 93. Por isso o filtro por um advogado perderia
  processos; o recorte certo é **Área 3 + Parte Passiva**.
- Aparecem 91 processos do TJCE (`8.06`) na área Trabalhista com cliente no passivo: conferir se é cadastro
  errado de área ou ação cível ligada ao trabalhista. O vigia do PJe olha só o TRT7.
- Dimensão da rodada no PJe: **239 processos do TRT7**. Primeira leitura completa: várias horas (≈ 1 a 2 min por
  processo com documentos); depois, leitura incremental (só o que mudou) com teto diário.

### Frequência das verificações no PJe
| Caminho | Como | Prós | Contras |
|---|---|---|---|
| Conservador | 1x/dia, só os processos marcados "em risco" | Poucas consultas, risco mínimo de limite no TRT7 | Processo novo só é classificado quando alguém marca |
| **Balanceado (recomendado)** | 1x/dia, todos os processos trabalhistas do TRT7 da lista, com leitura incremental e pausa de 20–40 s entre processos | Cobertura completa, custo baixo após a 1ª leitura | 1ª rodada demora (lê tudo uma vez) |
| Ousado | 2x/dia (manhã e tarde) para todos | Janela de exposição menor | Dobra as consultas; mais risco de limite e de conflito com o uso humano do Chrome |

### Configuração prevista (`pje-busca/.env`, sem valores no git)
`VIOS_URL`, `VIOS_USUARIO`, `VIOS_SENHA` (ou reaproveitar o login da Orelha), `VIGIA_VIOS_AREA_ID` (padrão `3`),
`VIGIA_VIOS_TIPO_PARTE` (padrão `P`), `VIGIA_VIOS_ADVOGADO_ID` (opcional, vazio = todos; um ou mais separados por `|`),
`VIGIA_PJE_PAUSA_S` (padrão 30),
`VIGIA_PJE_MAX_POR_DIA` (teto de processos por dia), `VIGIA_HORARIO`.

### Comandos previstos
`python3 vigia.py vios` (só a foto do VIOS e a comparação) · `python3 vigia.py pje` (só a fila do PJe) ·
`python3 vigia.py tudo` (os dois, para o agendamento no Mac mini via `servidor_mac.sh`/launchd).

### Indicadores
- **Janela de exposição:** dias entre a autuação de um processo contra o cliente e o dia em que o escritório soube.
  Caso real: CumPrSe 0001368-02.2026.5.07.0038 autuado em 29/07/2026, habilitação em 18/11/2026 = **112 dias**.
  Meta: ≤ 1 dia útil.
- **Cobertura:** processos trabalhistas do TRT7 no VIOS que foram verificados no PJe no dia ÷ total da lista.
- **Falhas:** processos que não abriram ou documentos sem texto (por dia).

### Riscos e mitigações
| Risco | Mitigação |
|---|---|
| Empresa trabalhista cadastrada com outra área ou outro advogado no VIOS | Rodar também sem o filtro de advogado 1x/semana e listar as diferenças para conferência |
| Lista do VIOS acima de 500 linhas | Paginar ou dividir a pesquisa por advogado; conferir com o total do rodapé |
| Limite de consultas no TRT7 | Pausa entre processos, teto diário, leitura incremental, só processos da lista |
| Chrome ocupado/oculto no Mac mini (o pdf.js não desenha com a aba oculta) | Rodar fora do expediente; abortar e reportar se o login cair (sem contornar captcha) |
| Alterar algo no VIOS sem querer | Navegador com bloqueio de envios (como a Orelha/Consulta) e só URLs GET |
| Dados de processos fora do Mac | Fotos e estado só em `dados/` (gitignored); nada enviado a serviço externo |

## 5. Quem entra na lista de vigilância

Arquivo exportado do VIOS com os processos trabalhistas do TRT7 em que:
- o cliente é a **reclamada**;
- já houve **condenação** (sentença ou acórdão);
- ainda há **recurso pendente** (a CLT só permite execução provisória até a penhora, na pendência de recurso).

Campos mínimos: `numero_processo`, `cliente`, `cnpj`, `vara`, `advogado_responsavel`, `reclamante`, `advogado_contrario` (opcional).

> A partir da seção 4.2, essa lista deixa de ser um arquivo manual: sai da foto diária do VIOS + classificação da
> fase pela leitura do PJe. Atenção: o recurso pendente pode ser **da parte contrária** (no caso real, o recurso
> ordinário era do reclamante).

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
7. [x] **Leitura das movimentações no PJe** (19/11/2026, commit 3cc2585): 16/16 documentos do CumPrSe 0001368 lidos.
8. [x] **Busca por nome/CNPJ no Acervo Geral** (19/11/2026, `logs/acervo_nome/2026-11-19_162813/`): funciona por
   sugestão (autocomplete "NOME - CNPJ"), achou 2 processos da MM Comércio. **Limitação:** o Acervo só tem processos
   em que o escritório está cadastrado; não valida o Robô A (processo novo sem habilitação).
9. [ ] **Testar busca por CNPJ fora do acervo** ("Consulta Processos de Terceiros" no PJe ou PDPJ) com 09.352.289/0001-82.
10. [x] **Vigia VIOS (4.2), filtros e volume** (23/11/2026): Área 3 = Trabalhista + parte passiva (P) + ativos =
    363 processos, 161 clientes, 239 no TRT7. Sem filtro de advogado (dois advogados principais).
11. [ ] **Vigia VIOS:** confirmar se o usuário do VIOS que o robô vai usar enxerga os mesmos 363 processos (as
    permissões podem ser diferentes das do usuário do Chrome) e decidir o que fazer com os 91 do TJCE na área
    Trabalhista.

Casos reais conhecidos (pendências 4 e 5): principal **ATOrd 0002754-04.2025.5.07.0038** (autuado 22/11/2025);
execução **CumPrSe 0001368-02.2026.5.07.0038** (classe "Cumprimento Provisório de Sentença", autuado 29/07/2026,
2ª VT de Sobral), cuja petição inicial cita o número do principal.

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
│   ├── vios.py               # lê a lista do VIOS (Área trabalhista + advogado), só leitura, e guarda a foto do dia (4.2)
│   ├── estado.py             # guarda o que já foi visto (SQLite)
│   └── alertas.py            # envio por e-mail/WhatsApp
├── dados/
│   └── estado.sqlite         # criado automaticamente
├── logs/
├── tests/
│   └── caso_real/            # dados do caso do bloqueio, para validar o robô
├── vigia.py                  # 4.2: python3 vigia.py vios | pje | tudo
└── main.py                   # roda tudo: python main.py robo-a | robo-b | tudo
```

**Segurança:** o certificado A1 e as senhas nunca vão para o repositório. Ficam só no `.env` local ou num cofre de senhas.

## 8. Ordem de construção

1. **Fase 0: validação manual.** Pendências 1 a 4.
2. **Fase 1: Robô A** com alerta por e-mail, testado com o caso real.
3. **Fase 2: Robô B** (vigia do processo principal).
3.1 **Fase 2.1: vigia diário VIOS → PJe (seção 4.2).** Foto do VIOS + comparação primeiro; depois a fila do PJe com
    leitura incremental; por último a classificação "em risco".
4. **Fase 3: integração.** Alerta por WhatsApp, painel junto do monitoramento por OAB que já existe e, se fizer sentido, cadastro automático do processo novo no VIOS.
5. **Agendamento:** rodar todo dia útil de manhã (e, se der, uma segunda vez à tarde).

## 9. Riscos e plano B

- **Mudança no PJe ou no Presto:** o acesso via Selenium pode quebrar quando o tribunal muda a tela. Plano B: os caminhos 2 e 3 do Robô A (item 4.1), mais a busca pelo nome do cliente no DJEN, que é gratuita e não depende de login.
- **Bloqueio antes de qualquer aviso:** o Robô A reduz esse risco ao mínimo, porque alerta no dia seguinte à distribuição. O Robô B é a segunda camada.
- **Muitos alertas** (clientes grandes com muitas ações): por isso a divisão entre alerta vermelho e resumo diário.

## 10. Complemento opcional já escrito

Já existe um script inicial (`alerta_exec_provisoria.py`) que usa as fontes públicas do CNJ (DataJud e DJEN), sem entrar no PJe. Ele **não resolve o caso principal**, porque supõe que a execução já nasce com a classe certa e na mesma vara. Pode servir como camada extra e gratuita: buscar o nome do cliente no DJEN do TRT7.
