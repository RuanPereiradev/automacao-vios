# Relatório de Processos por Grupo Cliente — VIOS

Robô que entra no VIOS com o **segundo usuário** (mesmo escritório,
`roneely.vios.com.br`, outro login e outras permissões), lista os processos de
cada **Grupo Cliente**, abre a ficha de cada processo e grava, por grupo, um
`.txt` e um `.json`. Depois, o `relatorio_cliente.py` transforma cada `.json`
num **PDF para o cliente**, com 13 campos por processo. Os atalhos
`rodar_usuario2.bat` / `rodar_usuario2.sh` fazem as duas coisas numa execução.

> **Status: em ajuste.** A primeira versão (28/10/2026) funciona no VIOS. As
> mudanças de 03/11/2026 (ficha do processo, "Mostrar" sem limite, JSON, PDF,
> SEM GRUPO CLIENTE, encerrados, posição pelo polo do VIOS, novo login) foram
> testadas com testes automáticos, navegador falso e dados fictícios.
> **Conferido ao vivo no VIOS em 03/11/2026, só lendo, pelo Chrome:** o script
> da ficha (`bot/js/ficha.js`) em 3 fichas, as colunas da lista num grupo de
> 101 processos e a regra dos filtros de situação (ver passo 6). **Ainda não
> rodado de ponta a ponta no VIOS** (robô com Selenium) **nem com a API de IA.**
> Mapa das telas do VIOS usado no robô: [doc/vios-mapa-processos.md](doc/vios-mapa-processos.md).
> Histórico de mudanças: [CHANGELOG.md](CHANGELOG.md). Robô de intimações:
> [DOCUMENTACAO.md](DOCUMENTACAO.md).

---

## 1. Objetivo

Um **PDF por Grupo Cliente**, com estes 13 campos por processo, nesta ordem:
ID da extração, Número do processo, Parte ativa, Parte passiva, Tipo de
processo, Órgão, Data da distribuição, Valor da ação, Cidade/UF, Última
movimentação, Resumo do caso, PENDÊNCIA, Financeira.

O "Valor provisionado" da planilha de referência **saiu** (decisão do usuário,
03/11/2026): é uma estimativa que o advogado põe no cadastro e está zerada no
VIOS (ver seção 10).

| Etapa | O que faz | Status |
| --- | --- | --- |
| 1. Login | Entra no VIOS com o usuário do `.env.usuario2` | ✅ Pronto |
| 2. Navegação | Abre Relatórios e depois a lista de Processos | ✅ Pronto |
| 3. Mapa do VIOS | Telas, filtros, colunas e ficha mapeados no VIOS real (só leitura) | ✅ Pronto (03/11/2026, `doc/vios-mapa-processos.md`) |
| 4. Pesquisa | Escolhe o Grupo Cliente, "Mostrar" = 9999999 (sem limite), Pesquisar | 🚧 Pronto no robô; o "Mostrar" = 500 funcionou no VIOS (3A FRIOS), o 9999999 falta testar |
| 5. Leitura da lista | Lê a tabela do grupo, com as colunas novas (tipo de processo, polo, data e valor da ação, vara) | 🚧 Pronto no robô (17 de 17 na versão de 28/10); colunas novas conferidas ao vivo (grupo de 101), robô falta rodar |
| 6. Ficha do processo | Abre a ficha de cada processo: Cidade/UF, fase, tarefas, comentários, arquivos | 🚧 Pronto no robô; `ficha.js` conferido ao vivo em 3 fichas, robô completo falta rodar |
| 7. TXT e JSON | `<GRUPO>.txt` (leitura humana) e `<GRUPO>.json` (base do PDF) | 🚧 Pronto no robô, falta testar no VIOS |
| 8. PDF do cliente | `<GRUPO>.pdf` com os 13 campos, sem dados internos | 🚧 Pronto; visual a aprovar (`doc/exemplo-relatorio.pdf`) |
| 9. IA (opcional) | Escreve resumo, pendência e financeira | 🚧 Pronto, desligada por padrão; não testada com a API real |
| 10. Novo login | Sessão do VIOS caiu no meio da rodada: faz login de novo | 🚧 Pronto no robô, testado só com navegador falso |
| 11. Encerrados | Opção `--encerrados`: segunda pesquisa só dos encerrados, marcados no PDF | 🚧 Pronto no robô; regra dos filtros conferida ao vivo, robô falta rodar |
| 12. SEM GRUPO CLIENTE | Processos fora de todos os grupos (`--sem-grupo`) | 🚧 Pronto no robô, falta testar no VIOS |
| 13. Google Drive | Salvar direto numa pasta do Drive (`RELATORIO_PASTA`) | 🚧 Pronto no robô; falta testar com o Drive real |
| 14. Atalho completo | `rodar_usuario2.bat`/`.sh`: captura + PDF numa execução, código 1 se algum passo falhar | ✅ Pronto (testado com passos falsos) |

---

## 2. Passo a passo do que o robô faz

São **duas etapas**, rodadas uma depois da outra: a captura no VIOS
(`relatorio_processos.py`) e o PDF (`relatorio_cliente.py`). Os atalhos
`rodar_usuario2.bat` e `rodar_usuario2.sh` rodam as duas pelo
`rodar_relatorio.py`:

- primeiro a captura, com as opções dela (`--grupo`, `--sem-ficha`,
  `--sem-grupo`, `--encerrados`);
- depois o PDF da pasta do dia mais recente, com as opções dele (`--ia`,
  `--refazer`). O PDF roda mesmo se a captura falhou em algum grupo: os grupos
  salvos viram PDF;
- sai com **0** se os dois passos deram certo e **1** se algum falhou (para o
  Agendador de Tarefas ou o cron).

### Etapa 1 — Captura no VIOS (`relatorio_processos.py`)

0. **Confere a pasta de saída** (`RELATORIO_PASTA`). Se ela não existe (por
   exemplo, com o Google Drive fechado), mostra um erro e para com código 1,
   antes de abrir o Chrome. Com as fichas ligadas, também confere se o módulo
   da ficha carrega; se não, para com código 1.
1. **Login** com o usuário e a senha do `.env.usuario2`.
2. Abre a tela de **Relatórios**
   (`?pag=sys/relatorios/relatorios.php`, em `NAVEGACAO_URL_FINAL`).
3. Abre a lista de **Processos**
   (`?pag=sys/processos/processos-lista.php&menu_lateral=true`).
4. Lê as opções do filtro **Grupo Cliente** (`pesq[clientes_grupos_id]`). Cada
   grupo é pesquisado separadamente. O "TODOS" (valor 0) só é usado com
   `--sem-grupo` (passo 10).
5. Antes de cada grupo, confere se o VIOS voltou para a **tela de login** (URL
   com `entrar.php` ou os campos de login na tela). Se voltou, faz login de novo
   (ver "Sessão que cai no meio da rodada").
6. Escolhe o grupo e muda **Mostrar** para **9999999** (a opção "sem limite"
   da tela) e aciona **Pesquisar**. Se o grupo ou essa opção não existem no
   filtro, para com erro: não pesquisa outro grupo nem traz a lista cortada
   em 30. Se o campo "Mostrar" (`pesq[limit]`) nem existe no formulário,
   também para com erro. Filtros: **Ativos** + **Não migrados** (padrão da
   tela; o robô garante "Ativos" marcado e "Encerrados" desmarcado).

   **Com `--encerrados` são duas pesquisas por grupo.** No VIOS as opções
   marcadas no filtro de situação combinam com **E**: conferido ao vivo em
   03/11/2026 num grupo de 101 processos, Ativos + Não migrados = 101,
   Encerrados + Não migrados = 35 e Ativos + Não migrados + Encerrados = **0**.
   Então o robô pesquisa primeiro os ativos e depois, de novo, com "Ativos"
   desmarcado e "Encerrados" marcado. As duas listas são juntadas sem repetir
   CI, e cada processo ganha `situacao` = `ativo` ou `encerrado`. Vale também
   para a pesquisa de TODOS do SEM GRUPO CLIENTE. Se a opção "Encerrados" ou
   "Ativos" não existe na tela, para com erro.
7. Lê a tabela inteira com uma chamada de JavaScript, pelo `data-id` de cada
   célula (`processos-lista_linha_N_<coluna>`). Se ela falhar, lê linha por
   linha, como antes. Colunas lidas:
   - CI, número, partes, cliente, área, ação, órgão, UF, contrato, advogado,
     objeto, vínculo;
   - novas: tipo de processo (`pr_processos_nome`), polo do cliente
     (`cliente_escritorio`), data da ação, valor da ação, vara, tipo de vara,
     observação interna (`obs_proc`).

   "00/00/0000" e "0,00" do VIOS viram vazio. O rodapé "Total (N)" conta as
   linhas mostradas na página: se não bate com as linhas lidas, o log avisa
   "leitura incompleta da página".
8. **Ficha de cada processo** (ver seção 3): abre
   `?pag=sys/processos/processos-vis.php&processos_id=<CI>`, só para ler. No
   log: `<GRUPO>: ficha 12 de 101 (CI x)`.
   - Erro numa ficha: fica registrado no `.json` (`ficha.ok = false` e o
     motivo) e o robô segue para a próxima.
   - Sessão caída: novo login e a mesma ficha de novo. Depois de 3 novos
     logins nas fichas do mesmo grupo, o grupo ganha a nova tentativa de
     sempre.
   - Com `--sem-ficha` (ou `PROCESSOS_FICHA=false`) este passo é pulado.
9. Grava `<GRUPO>.txt` e `<GRUPO>.json` na pasta do dia e repete para o
   próximo grupo.
10. Com `--sem-grupo` e `--grupo todos`: pesquisa Grupo = TODOS (sem limite) e
    grava "SEM GRUPO CLIENTE" com os processos cujo CI não apareceu em nenhum
    grupo da rodada (lê a ficha só desses). Não gera esse grupo, e conta como
    falha, em três casos: algum grupo falhou, alguma linha da lista de algum
    grupo não pôde ser lida (o processo dela iria parar, errado, no SEM GRUPO
    CLIENTE) ou a lista de TODOS veio vazia. Com grupos escolhidos, a opção é
    ignorada com aviso.

**Por que preenche por JavaScript:** depois do login o VIOS abre um popup de
Recado por cima da tela. O robô não mexe nele: escolhe o filtro e envia o
formulário pelo mesmo botão Pesquisar (`#Pesq`), sem clicar na tela.

**Posição do cliente:** vale o polo cadastrado no VIOS (`cliente_escritorio`:
"Parte Passiva" = réu, "Parte Ativa" = autor). Só quando o polo vem vazio ou
diferente (ex.: "Terceiro") o robô compara o nome do cliente com as partes
(ver seção 4).

### Etapa 2 — PDF (`relatorio_cliente.py`)

1. Lê os `<GRUPO>.json` da pasta do dia mais recente (ou o caminho informado).
2. Monta os 13 campos de cada processo (`bot/campos_relatorio.py`) e limpa os
   textos (ver seção 8).
3. Com `--ia` (ou `RELATORIO_IA=true`), a IA escreve resumo, pendência e
   financeira. Sem IA (padrão), esses campos saem do cadastro.
4. Grava `<GRUPO>.pdf` na mesma pasta (`bot/pdf_relatorio.py`), com permissão
   0644 (legível por outras contas, como os `.txt`; o arquivo temporário nasce
   0600).

Não acessa o VIOS.

### Sessão que cai no meio da rodada

Em rodadas longas (`--grupo todos`, 82 grupos, milhares de fichas) o VIOS pode
encerrar a sessão. O robô percebe pela tela de login, faz login de novo e
tenta o grupo **só mais uma vez**:

- Se a pesquisa ou a leitura do grupo falha e o navegador está na tela de
  login: novo login e nova tentativa. Se falhar de novo, o grupo conta como
  falha (com print em `logs/erro_*.png`) e os outros continuam.
- Falha fora da tela de login não ganha nova tentativa.
- Lista vazia com a tela de login aberta também conta como sessão caída, para
  não gravar um `.txt` com 0 processos.
- Nas fichas: novo login e a mesma ficha de novo, até 3 vezes por grupo.
- No log: `Sessão do VIOS caiu antes do grupo X: fazendo login de novo`,
  `Sessão do VIOS caiu na ficha do CI x: fazendo login de novo` e
  `Novo login e nova tentativa (a última) do grupo X`.
- Se o navegador travar e o print não sair, o log diz `sem screenshot` e a
  rodada continua.

**Ainda não testado no VIOS:** não foi confirmado que a sessão caída leva para
o `entrar.php` (ou mostra os campos de login).

### Só leitura

A tela de Processos tem botões perigosos: **Apagar** e **Editar** em cada linha
e o **Processar**, que executa ações em lote (apagar processos, trocar
advogado, etc.). O filtro "Tipo de relatório" tem a opção **amostragem**, que
também é ação em lote. O robô **não usa nenhum deles**: só escolhe filtros,
pesquisa, lê a lista e abre a ficha (a mesma página do botão "Visualizar").

---

## 3. Ficha do processo

Para cada processo da lista, o robô abre a ficha no VIOS:
`?pag=sys/processos/processos-vis.php&processos_id=<CI>`.

A ficha é montada por JavaScript. Antes de ler, o robô espera um campo com
valor (não basta o rótulo). Depois espera no máximo 3 segundos pela tabela de
tarefas: uma linha de tarefa ou o aviso "Nenhum registro". Ficha sem tarefas
não trava. Por fim roda o script `bot/js/ficha.js`, que devolve:

| Campo | De onde vem na ficha |
| --- | --- |
| `campos` | todos os rótulos dos 3 blocos ("N.° CNJ", "Polo do cliente", "Parte passiva"...). Partes múltiplas separadas por "; " |
| `cidade_uf` | "Cidade / UF" (vazio se Cidade e UF estão em branco) |
| `fase` | "Fase" |
| `data_distribuicao` | "Data da ação / Distribuição" (vazio se "00/00/0000") |
| `valor_acao` | "Valor da ação" (sem "R$"; vazio se "0,00") |
| `justica`, `sistema` | "Justiça", "Sistema do tribunal" |
| `tarefas` | tabela de tarefas: CI, situação (ex.: CANCELADA), tipo, descrição completa, comentários, para conclusão, limite, concluída em |
| `comentarios` | seção Comentários: data e hora, autor, texto |
| `arquivos` | tabela de arquivos: data, pasta, tipo, descrição, nome do arquivo |

- Se a ficha não carregar (ou mostrar só os rótulos, sem nenhum valor), o
  processo fica com `ok: false` e o motivo em `erro`. O grupo segue com os
  dados da lista.
- As tabelas são lidas pela posição das colunas, só nas células diretas. Uma
  tabela colada dentro da descrição de uma tarefa (texto de e-mail ou Word) não
  desloca as colunas: o texto dela entra na descrição.
- A descrição das tarefas pode ter link e senha de audiência. O `ficha.js` só
  lê; a limpeza é feita na etapa do PDF.

**Para conferir o script no VIOS:**

1. Abra uma ficha no Chrome.
2. Aperte F12 e vá na aba Console.
3. Cole o conteúdo de `bot/js/ficha.js` e aperte Enter.

Aparece o objeto lido. O script não clica, não envia nada e não muda a página.

---

## 4. Os arquivos gerados

Pasta: `saida_usuario2/relatorios/AAAA-MM-DD/` (ou
`<RELATORIO_PASTA>/AAAA-MM-DD/`). Cada execução cria a pasta do dia; rodar de
novo no mesmo dia sobrescreve os arquivos do grupo.

| Arquivo | Quem gera | Para quê |
| --- | --- | --- |
| `<GRUPO>.txt` | `relatorio_processos.py` | Leitura humana / conferência |
| `<GRUPO>.json` | `relatorio_processos.py` | Base do PDF (um registro por processo) |
| `<GRUPO>.pdf` | `relatorio_cliente.py` | Relatório para o cliente |

Exemplo: `saida_usuario2/relatorios/2026-11-03/3A FRIOS.pdf`. Com
`--sem-grupo`, também `SEM GRUPO CLIENTE.txt/.json/.pdf`.

### 4.1. `<GRUPO>.json`

Uma lista com um registro por processo, na mesma ordem do `.txt`:

- `grupo`, `ci`, `numero` ("CNJ: ...", sem as etiquetas);
- `parte_ativa` e `parte_passiva` (listas, com o rótulo "Autor:", "Réu:"...);
- `cliente`, `polo_cliente` (ex.: "Parte Passiva"), `area`, `tipo_processo`,
  `acao`, `orgao`, `uf`, `vara`, `tipo_vara`;
- `data_acao` (DD/MM/AAAA ou vazio), `valor_acao` ("50.000,00" ou vazio);
- `objeto`, `obs_proc` (**interno**: não vai para o cliente), `posicao`;
- `situacao`: `ativo` ou `encerrado` (encerrados só com `--encerrados`);
- `ficha`: o que a ficha devolveu (seção 3), com `ok` e `erro`. Com
  `--sem-ficha`: `{"ok": false, "erro": "ficha não lida (--sem-ficha)"}`.

O `.json` tem dados internos (`obs_proc`, CI, comentários e tarefas com links):
**não enviar ao cliente**. Ao cliente vai só o PDF.

### 4.2. `<GRUPO>.pdf` — os 13 campos

- **Capa**: "Relatório de processos — <GRUPO>", data e hora de geração, total
  de processos e quantos processos por Tipo de processo e por Cidade/UF. Com
  encerrados: "Total de processos: 10 (7 em andamento, 3 encerrados)".
- **Um bloco por processo**: faixa "ID <n> — <número>" e os 13 campos. Campo
  vazio aparece como "Não informado". O bloco não se parte entre páginas
  quando cabe numa página só.
- **Processo encerrado**: "(encerrado)" depois do número, na faixa e no campo
  Número do processo.
- **Observações** no fim: data dos dados do VIOS, fichas não lidas, sem IA.
- **Rodapé** em toda página: "Relatório gerado a partir dos dados cadastrados
  no sistema do escritório. Dúvidas sobre o andamento: falar com o advogado
  responsável." e "Página X de Y".
- Modelo com dados fictícios: `doc/exemplo-relatorio.pdf`.

| Campo | De onde vem |
| --- | --- |
| ID da extração | numeração 1..N do robô (ordem: cliente, parte ativa, número) |
| Número do processo | lista (`nro_proc_html`, sem "CNJ:") ou "N.° CNJ" da ficha; encerrado ganha " (encerrado)" |
| Parte ativa / Parte passiva | lista (`ativahtml`/`passivahtml`), sem o rótulo ("Autor:", "Contrário:"...), separadas por vírgula; sem lista, a ficha |
| Tipo de processo | lista `pr_processos_nome` (ex.: CÍVEL); vazio = área; depois "Processo" da ficha |
| Órgão | lista `orgaos_nome` + " - " + `vara` (quando houver) |
| Data da distribuição | lista `data_acao` (ou "Data da ação / Distribuição" da ficha), DD/MM/AAAA |
| Valor da ação | lista `valor_acao` (ou ficha), "R$ 50.000,00"; zero = "não informado" |
| Cidade/UF | ficha "Cidade / UF" (a lista só tem a UF do órgão) |
| Última movimentação | ficha → tarefa concluída mais recente: "DD/MM/AAAA - TIPO - texto" (até 300 caracteres) |
| Resumo do caso | sem IA: montado do cadastro ("Ação X sobre Y, movida por A contra B, em C."); com IA: texto da IA |
| PENDÊNCIA | sem IA: tarefas abertas ("TIPO até DD/MM/AAAA; ..."), ou "Nenhuma pendência registrada"; com IA: texto da IA |
| Financeira | **não existe no VIOS**. Sem IA: sempre "não identificada". Com IA: só valores, acordos ou pagamentos escritos nas tarefas e comentários; nada escrito = "não identificada" |

**Regra da última movimentação:**

- só tarefa concluída conta (algo que de fato aconteceu); a data é a de
  "Concluída em";
- tarefas canceladas não contam;
- tarefa aberta, com prazo vencido ou futuro, não é movimentação: aparece na
  PENDÊNCIA;
- empate de data: vale a tarefa mais nova (CI maior);
- nenhuma tarefa concluída: "Nenhuma movimentação registrada";
- o texto vem do comentário da tarefa ou, sem comentário, da descrição.

**Ficha não lida** (`--sem-ficha` ou erro): Cidade/UF, última movimentação e
pendência ficam "não informado", e o PDF avisa nas observações.

### 4.3. `<GRUPO>.txt`

Cabeçalho (grupo, data e hora, total; com `--encerrados`, "processos ativos e
encerrados"), resumo por empresa, área e posição do cliente (e por situação,
quando há encerrados), e um bloco por processo:

| Campo no .txt | Origem |
| --- | --- |
| Número do processo | `nro_proc_html` (sem as etiquetas) |
| Situação | `ativo` ou `encerrado` (de qual pesquisa veio) |
| Área | `pr_areas_nome` |
| Tipo de processo | `pr_processos_nome` |
| Tipo de ação | `processos_acoes_nome` |
| Assunto (objeto) | `objeto` |
| Data da distribuição | `data_acao` |
| Valor da ação | `valor_acao` |
| Onde tramita | `orgaos_nome` + `orgaos_uf` |
| Vara | `vara` + `tipo_vara` |
| Cidade / UF, Fase | ficha (sem ficha: "não informado") |
| Quem entrou com a ação (parte ativa) | `ativahtml` |
| Contra quem (parte passiva) | `passivahtml` |
| Posição do cliente | polo do VIOS ou comparação de nomes (abaixo) |
| Advogado responsável | `advogado_nome` |
| Vínculo | ícone `sinal_vinculo_processo`: processo principal ou apenso |
| Contrato | `contratos_vis` |
| Código interno no VIOS (CI) | `processos_id` |

Ficam de fora do `.txt`: `obs_proc`, siglas dos auxiliares
(`advogados_auxiliares_abr`) e etiquetas como "Cliente OURO". Campo vazio
aparece como "não informado".

**Posição do cliente.** Primeiro vale o polo do VIOS (`cliente_escritorio`).
Sem polo (ou polo diferente de "Parte Ativa"/"Parte Passiva"), o robô compara
o nome do cliente com as partes, depois de limpar os dois nomes:

- sai o rótulo antes do ":" ("Autor:", "Reclamado:", "Exequente:" etc.);
- sai o que está entre parênteses ou colchetes, como "(MATRIZ)" e "(CNPJ ...)";
- saem CPF e CNPJ (o rótulo e o número);
- saem pontuação, espaços extras e acentos;
- saem LTDA, LIMITADA, EIRELI, EPP, MEI, MATRIZ e FILIAL, em qualquer lugar do
  nome;
- saem S/A (S.A., SA), ME, CIA, COMPANHIA, "Sociedade Anônima" e "Em
  Recuperação Judicial", só no fim do nome.

Depois disso os nomes têm que ser **iguais** (nome parecido ou pedaço do nome
não conta). Resultados possíveis: "autor (o cliente entrou com a ação)", "réu
(o cliente está sendo processado)", "aparece como autor e como réu (conferir no
VIOS)", "não identificada (o cliente não aparece nas partes da lista)" ou "não
identificada".

---

## 5. Como rodar

Os atalhos `.bat`/`.sh` fazem a captura no VIOS e, logo depois, o PDF. Dá
para rodar cada etapa sozinha chamando o Python direto.

### Windows (na pasta do projeto)

```powershell
# captura + PDF numa execução
.\rodar_usuario2.bat                                  # grupos de PROCESSOS_GRUPOS no .env.usuario2
.\rodar_usuario2.bat --grupo "pao mix"                # outro grupo
.\rodar_usuario2.bat --grupo "3A FRIOS|PÃO MIX"       # vários, separados por |
.\rodar_usuario2.bat --grupo todos --sem-grupo        # os 82 grupos + SEM GRUPO CLIENTE
.\rodar_usuario2.bat --grupo "3A FRIOS" --sem-ficha   # só a lista (rápido)
.\rodar_usuario2.bat --grupo "3A FRIOS" --encerrados --ia   # com encerrados; PDF com IA

# só a captura
.\.venv\Scripts\python.exe relatorio_processos.py .env.usuario2 --grupo "3A FRIOS"

# só o PDF
.\.venv\Scripts\python.exe relatorio_cliente.py .env.usuario2                    # pasta do dia mais recente
.\.venv\Scripts\python.exe relatorio_cliente.py .env.usuario2 "saida_usuario2\relatorios\2026-11-03\3A FRIOS.json"
.\.venv\Scripts\python.exe relatorio_cliente.py .env.usuario2 saida_usuario2\relatorios\2026-11-03 --refazer
.\.venv\Scripts\python.exe relatorio_cliente.py .env.usuario2 --ia               # com IA
```

Ou dois cliques em `rodar_usuario2.bat` (captura + PDF dos grupos de
`PROCESSOS_GRUPOS`).

### Linux ou Mac

```bash
# captura + PDF (o script roda de qualquer pasta e usa .venv/bin/python)
./rodar_usuario2.sh
./rodar_usuario2.sh --grupo "pao mix"
./rodar_usuario2.sh --grupo todos --sem-grupo --encerrados
./rodar_usuario2.sh --grupo "3A FRIOS" --ia

# só a captura
.venv/bin/python relatorio_processos.py .env.usuario2 --grupo "3A FRIOS"

# só o PDF
.venv/bin/python relatorio_cliente.py .env.usuario2
.venv/bin/python relatorio_cliente.py .env.usuario2 "saida_usuario2/relatorios/2026-11-03/3A FRIOS.json"
.venv/bin/python relatorio_cliente.py .env.usuario2 --ia
```

### Opções da captura

A linha de comando vale mais que o `.env.usuario2`.

| Linha de comando | `.env.usuario2` | Padrão | O que faz |
| --- | --- | --- | --- |
| `--grupo "X\|Y"` ou `--grupo todos` | `PROCESSOS_GRUPOS` | — | Grupos pesquisados |
| `--sem-ficha` | `PROCESSOS_FICHA=false` | fichas ligadas | Só a lista, sem abrir a ficha de cada processo (bem mais rápido) |
| `--sem-grupo` | `PROCESSOS_SEM_GRUPO=true` | desligado | Grupo extra SEM GRUPO CLIENTE (só com `--grupo todos`) |
| `--encerrados` | `PROCESSOS_ENCERRADOS=true` | desligado | Inclui os processos encerrados (segunda pesquisa por grupo; ver passo 6) |

- O nome do grupo não depende de acento nem de maiúsculas
  (`"pao mix"` acha `PÃO MIX`).
- `--grupo` precisa de um nome logo depois; sem nome, o robô dá erro e sai.
- Deu certo quando o log mostra `<GRUPO>: N processos, 0 com erro na lista, 0 fichas
  com erro -> <arquivo>` e, no fim, `Concluído: N grupo(s) salvos, 0 com falha`.
- O `.bat` e o `.sh` saem com **código 0** quando a captura e o PDF deram
  certo e **1** quando algum dos dois falhou. No Agendador de Tarefas, rodar o
  `.bat` com `SEM_PAUSA=1` (senão ele para no `pause`).
- Nos atalhos, `--ia` e `--refazer` vão só para o PDF; as outras opções, só
  para a captura.
- O aviso `Error terminating service process` no fim é do Selenium no Windows
  e pode ser ignorado.

### Opções do PDF

`relatorio_cliente.py [.env.usuario2] [GRUPO.json | pasta do dia] [--refazer] [--ia]`

- Sem caminho: usa a pasta AAAA-MM-DD mais recente em `RELATORIO_PASTA` (vazio
  = `<SAIDA_PASTA>/relatorios`). Também aceita o `<GRUPO>.txt`: usa o `.json`
  ao lado.
- PDF já existente e mais novo que o `.json` não é refeito. `--refazer` gera de
  novo.
- `--ia` (ou `RELATORIO_IA=true`): a IA escreve resumo, pendência e financeira.
- Deu certo quando o log mostra `<GRUPO>.json -> <arquivo .pdf> (N processos)`
  e, no fim, `Concluído: N relatório(s) gerado(s), N já em dia, 0 com falha`.
- Sai com **código 1** quando: um caminho informado não existe, nenhum `.json`
  é encontrado, não há pasta do dia, algum grupo falhou (ex.: `.json`
  quebrado), ou `--ia` foi pedido sem a chave da API no `.env` (`Parado: ...`).

---

## 6. Primeira instalação

Windows:

```powershell
cd C:\Rfeitosa-projetos\automacao-vios
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.usuario2.example .env.usuario2    # e preencher usuário e senha
```

Linux/Mac:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.usuario2.example .env.usuario2      # e preencher usuário e senha
```

- O `requirements.txt` instala o **reportlab** (PDF), com `pillow` e `chardet`
  em versões que aceitam Python 3.8 a 3.12.
- No Windows use o `rodar_usuario2.bat`; no Linux ou no Mac, o
  `rodar_usuario2.sh`. O `rodar.sh` e os outros `.sh` são do robô de
  intimações.
- Para usar a IA no PDF (opcional), preencher também `LLM_PROVEDOR` e a chave
  do provedor (`OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`).

---

## 7. Configuração (`.env.usuario2`)

Modelo versionado: `.env.usuario2.example`. O `.env.usuario2` real tem a senha
e as chaves de API e **não vai para o GitHub**.

| Variável | Uso | Valor do modelo |
| --- | --- | --- |
| `SISTEMA_URL` | Página de login | `https://roneely.vios.com.br/entrar.php?` |
| `SISTEMA_USUARIO` / `SISTEMA_SENHA` | Login do segundo usuário | (no `.env.usuario2`) |
| `LOGIN_CAMPO_USUARIO` / `LOGIN_CAMPO_SENHA` | Campos de login (também usados para perceber que a sessão caiu) | iguais aos do robô de intimações |
| `NAVEGACAO_URL_FINAL` | Tela aberta depois do login | `.../?pag=sys/relatorios/relatorios.php` |
| `PROCESSOS_GRUPOS` | Grupos do filtro Grupo Cliente, separados por `\|`, ou `todos` | `3A FRIOS` |
| `RELATORIO_PASTA` | Pasta dos `.txt`, `.json` e `.pdf`. Vazio = `<SAIDA_PASTA>/relatorios` (criada se faltar). Aceita aspas simples, `~`, `$HOME`, `%USERPROFILE%` e espaços (ex.: `G:\Meu Drive\Relatórios VIOS`). Preenchida, a pasta **tem que existir**: senão o robô para antes de entrar no VIOS | vazio |
| `PROCESSOS_FICHA` | **Nova.** `true` = abre a ficha de cada processo (só leitura); `false` = só a lista (`--sem-ficha`) | `true` |
| `PROCESSOS_SEM_GRUPO` | **Nova.** `true` = também gera "SEM GRUPO CLIENTE"; só com `--grupo todos` | `false` |
| `PROCESSOS_ENCERRADOS` | **Nova.** `true` = inclui os encerrados (`--encerrados`) | `false` |
| `SAIDA_PASTA` | Pasta de saída deste usuário | `saida_usuario2` |
| `HEADLESS` | Chrome sem janela | `false` |
| `TIMEOUT` | Espera máxima (s), também para cada ficha | `20` |
| `MANTER_ABERTO` | Chrome continua aberto no fim | `true` |
| `RELATORIO_IA` | **Nova.** `true` = IA escreve resumo, pendência e financeira (o mesmo que `--ia`) | `false` |
| `LLM_PROVEDOR` | IA do PDF: `openai` ou `anthropic` | `openai` |
| `LLM_MODELO` | Modelo (vazio = padrão do provedor: `gpt-5.6` / `claude-opus-5-5`) | vazio |
| `LLM_ESFORCO` | Esforço de raciocínio: `low`, `medium`, `high` | `low` |
| `LLM_LIMITE_US` | Teto de gasto com a IA por execução, em US$ (vazio/0 = sem teto). Passou: o resto sai sem IA | vazio |
| `LLM_PRECOS` | Corrige a tabela de preços do `bot/custo.py` | vazio |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Chave do provedor escolhido | (no `.env.usuario2`) |
| `RELATORIO_CLIENTE_PROMPT` | Arquivo com outro prompt para a IA dos campos (vazio = texto padrão do `bot/campos_relatorio.py`; aceita `~/...`) | vazio |

---

## 8. Segurança e privacidade

- **Só leitura** no VIOS (ver seção 2): lista e ficha, nunca Editar, Apagar,
  Processar nem "amostragem".
- **O que nunca vai para o PDF** (nem para a IA). Antes, o texto perde:
  - links, mesmo sem "http" (zoom, lifesize, chat, links curtos como bit.ly e
    forms.gle);
  - "LINK DO CHAT", ID, extensão e senha de reunião (também "Senha 123456" sem
    dois-pontos);
  - e-mails e telefones, com ou sem máscara (ex.: "85988887777");
  - "Responsáveis:", "Concluiu a tarefa:" e nomes da equipe (trocados por
    "[equipe]");
  - "Descrição do tipo da tarefa de origem: ..." e "Tarefa encerrada ao enviar
    o(s) arquivo(s): ...".

  Não são cortados: número de processo, datas, valores, período de anos
  ("2019-2021") e nome de empresa com ".com" sem link ("Exemplo.com S/A").
- A observação interna (`obs_proc`) e o CI **nunca** entram no PDF. O
  `obs_proc` também não vai para o `.txt`; fica só no `.json`.
- **IA desligada por padrão**: sem `--ia`, nada sai da máquina e não há gasto.
  Com IA, os dados já limpos vão para a API do provedor (OpenAI ou Anthropic):
  confirmar com o escritório antes de ligar. Erro da IA (chave recusada, sem
  créditos, teto de gasto) fica só no log; o PDF mostra só um aviso neutro
  ("Resumo, pendência e financeira de N processo(s) montados só com o
  cadastro.").
- **Um `.env` por usuário**: o `.bat` e o `.sh` sempre usam o `.env.usuario2`,
  e o log confirma o usuário em "Login OK como ...". Cada execução abre um
  Chrome com perfil limpo.
- **Fora do GitHub** (`.gitignore`): `.env.*` (menos os `.example`),
  `saida_*/`, `imgs/` e `logs/`. Os `.txt`, `.json` e `.pdf` têm dados de
  clientes. Com a `RELATORIO_PASTA` no Google Drive, quem tem acesso à pasta vê
  esses dados (inclusive o `.json`, que é interno).
- A senha do segundo usuário foi passada por chat na configuração: trocar e
  atualizar `SISTEMA_SENHA` no `.env.usuario2`.

---

## 9. Arquivos do projeto

```
automacao-vios/
├── relatorio_processos.py      # etapa 1: login → grupos → lista → fichas → .txt + .json
├── rodar_relatorio.py          # etapa 1 + etapa 2 numa execução (usado pelos atalhos)
├── rodar_usuario2.bat          # atalho no Windows (captura + PDF)
├── rodar_usuario2.sh           # atalho no Linux/Mac (captura + PDF)
├── bot/processos_grupo.py      # pesquisa por grupo, leitura da lista, posição do cliente, .txt e .json
├── bot/processo_ficha.py       # ficha do processo (ler_ficha), só leitura
├── bot/js/ficha.js             # script que lê a ficha (o mesmo roda no console do Chrome)
├── relatorio_cliente.py        # etapa 2: .json → PDF
├── bot/relatorio_cliente.py    # escolhe os .json, liga a IA (opcional) e grava o PDF
├── bot/campos_relatorio.py     # os 13 campos, limpeza dos textos e IA dos campos
├── bot/pdf_relatorio.py        # monta o PDF (reportlab)
├── doc/vios-mapa-processos.md  # mapa das telas de Processos do VIOS
├── doc/exemplo-relatorio.pdf   # modelo do PDF com dados fictícios
├── tests/                      # testes automáticos (sem VIOS e sem API)
├── .env.usuario2.example       # modelo do .env do segundo usuário
├── .env.usuario2               # configuração real (NÃO versionar — tem senha e chaves)
└── saida_usuario2/relatorios/  # .txt, .json e .pdf gerados (NÃO versionar — dados de clientes)
```

Reaproveita do robô de intimações: `bot/config.py`, `bot/login.py`,
`bot/navegador.py`, `bot/navegacao.py`, `bot/ia/` e `bot/custo.py`, e o log em
`logs/bot.log` (prints de erro em `logs/erro_*.png`).

---

## 10. Pontos de atenção

- **Valor provisionado: saiu do relatório** (decisão do usuário, 03/11/2026).
  Não está na lista nem na ficha; o relatório "Relatórios → Provisão" do VIOS
  tem a coluna, mas veio 0,00 em todas as linhas do grupo testado. É uma
  estimativa que o advogado põe no cadastro. Se um dia for preenchida, dá para
  voltar com o campo a partir desse relatório (casando pelo número do
  processo; ver `doc/vios-mapa-processos.md`).
- **Encerrados = duas pesquisas por grupo**: com `--encerrados` a rodada fica
  mais longa (lista de novo e fichas dos encerrados também).
- **Financeira** não existe no VIOS: sem IA, sempre "não identificada".
- **Resumo e pendência sem IA** são simples (cadastro e tarefas abertas). Um
  resumo melhor depende da IA ou, no futuro, da "CÓPIA DO PROCESSO" (PDF dos
  autos na seção Arquivos).
- **Tempo da rodada com fichas**: cada processo abre uma página. Com
  `--grupo todos` são milhares de fichas. Usar `--sem-ficha` quando não
  precisar de Cidade/UF, última movimentação e pendência.
- **Grupo = TODOS com 9999999** pode deixar a página pesada. Se a tabela
  demorar mais que `TIMEOUT`, a lista vem vazia (para o SEM GRUPO CLIENTE isso
  vira erro). Talvez seja preciso aumentar o `TIMEOUT` para `--sem-grupo`.
- **Restos da limpeza**: quando link e senha saem do meio da frase, pode sobrar
  algo como "Sala." no texto. Não vaza dado, mas pode ficar estranho.
- **Número solto de 10 a 11 dígitos** (sem ponto nem vírgula) é tratado como
  telefone/CPF e sai do texto. Valores formatados ("R$ 1.234,56") não são
  afetados.
- **Cadastro inconsistente no VIOS aparece no relatório.** No 3A FRIOS
  (28/10/2026): um cliente cadastrado com nome abreviado diferente da parte, e
  um processo do INPI sem partes cadastradas.
- **Limites da comparação de nomes** (só quando o polo do VIOS vem vazio): o
  sobrenome "SA" sem acento é lido como S.A.; "FULANO E CIA" e "FULANO & CIA"
  não casam; empresas que só diferem no sufixo viram o mesmo nome.
- **Novo login**: não testado no VIOS. Se o login de novo falhar (ex.: senha
  errada), cada grupo seguinte tenta outra vez.
- **Agendar no Windows**: o `rodar_usuario2.bat` tem `pause` no fim, a não ser
  com `SEM_PAUSA=1`. Ele já gera o PDF depois da captura.
- **PDF depois de uma captura que falhou**: o PDF usa a pasta do dia mais
  recente. Se a captura falhar antes de salvar qualquer grupo (ex.: login), essa
  pasta é a de um dia anterior; os PDFs dela que já estão em dia não são
  refeitos. O código de saída continua 1.
- **Caminho do Windows no `.env.usuario2`**: não usar aspas duplas em
  `RELATORIO_PASTA` (o `.env` troca `\r`, `\n` etc. dentro de aspas duplas).
  Escrever sem aspas, com aspas simples ou com `/`.

---

## 11. Testes

| Data | Grupo | Resultado |
| --- | --- | --- |
| 28/10/2026 | 3A FRIOS | 17 processos, 0 erros — igual à tabela copiada do VIOS (versão antiga, "Mostrar" = 500, sem ficha) |
| 03/11/2026 | (automático, dados fictícios) | 184 testes OK, nenhum pulado |
| 03/11/2026 | ao vivo no Chrome, só leitura | `ficha.js` em 3 fichas; colunas da lista e filtros de situação num grupo de 101 processos (ativos 101, encerrados 35, os três juntos 0) |
| 03/11/2026 | (automático, rodada final) | 201 testes OK: 13 campos, encerrados em duas pesquisas, SEM GRUPO com linha pulada, PDF 0644, atalho captura + PDF |

Testes automáticos (sem VIOS e sem API de IA; nomes e números inventados):

```bash
.venv/bin/python -m unittest discover -s tests -v          # Linux/Mac
.\.venv\Scripts\python.exe -m unittest discover -s tests -v  # Windows
```

| Arquivo | O que testa |
| --- | --- |
| `tests/test_posicao_cliente.py` | posição do cliente pela comparação de nomes |
| `tests/test_lista_processos.py` | colunas novas da lista, vazios do VIOS, polo do cliente, `.json` |
| `tests/test_relatorio_processos.py` | navegador falso: novo login, fichas, `--sem-ficha`, `--sem-grupo` (inclusive com linha pulada), `--encerrados` (duas pesquisas, sem repetir CI), `RELATORIO_PASTA` |
| `tests/test_rodar_relatorio.py` | atalho captura + PDF: divisão das opções e código de saída |
| `tests/test_processo_ficha.py` | ficha com driver falso; com Node e jsdom, roda o `ficha.js` numa página sintética (`JSDOM_DIR` = pasta do pacote jsdom; sem jsdom, esses testes são pulados) |
| `tests/test_campos_relatorio.py` | os 13 campos, "(encerrado)" no número, última movimentação, pendência, limpeza dos textos, IA falsa |
| `tests/test_pdf_relatorio.py` | PDF: títulos e ordem, textos longos, caracteres especiais, nome de arquivo, total com encerrados, permissão 0644 |
| `tests/test_relatorio_cliente.py` | `relatorio_cliente.py`: pasta do dia, `--refazer`, `--ia`, erros e códigos de saída |
| `tests/test_ponta_a_ponta.py` | fluxo inteiro com navegador falso: lista → fichas → `.json` → PDF; confere os 13 títulos, ficha que falha, tarefa cancelada, nada de link/senha/e-mail/equipe/`obs_proc` no PDF, só páginas de lista e ficha abertas, SEM GRUPO CLIENTE |

Só o teste de ponta a ponta: `.venv/bin/python -m unittest tests.test_ponta_a_ponta -v`.

**O que NÃO foi testado (03/11/2026):**

- O robô (Selenium) não foi rodado no VIOS real com as mudanças de 03/11:
  "Mostrar" = 9999999, leitura por JavaScript, ficha pelo robô, as duas
  pesquisas de encerrados, SEM GRUPO CLIENTE, novo login. Ao vivo só foram
  conferidos, à mão no Chrome, o `ficha.js`, as colunas e os filtros.
- O JavaScript da pesquisa (marcar/desmarcar ativos e encerrados) foi conferido
  num formulário simulado no Node, não na tela real.
- A IA dos campos não foi testada com a API real.
- A `RELATORIO_PASTA` não foi testada com o Google Drive real.
- Não há Python 3.8 na máquina: a compatibilidade foi checada só pela sintaxe.

---

## 12. Próximos passos

1. **Rodar o robô completo no VIOS real** com o `.env.usuario2` (senha
   preenchida pelo usuário) num grupo pequeno: `rodar_usuario2 --grupo "<grupo
   pequeno>"`, depois com `--encerrados`. Conferir:
   - a lista vem inteira (9999999) e bate com a tela;
   - a pesquisa de encerrados traz o mesmo número da tela (Encerrados + Não
     migrados);
   - as fichas são lidas e o PDF sai na pasta do dia.
2. **Aprovar o visual do PDF** com o escritório (`doc/exemplo-relatorio.pdf`).
3. Decidir se liga a IA (ver item 5).
4. Ler a **"CÓPIA DO PROCESSO"** (PDF dos autos, seção Arquivos da ficha) para
   um resumo e uma financeira melhores (exige baixar arquivos grandes).
5. Confirmar com o escritório se é aceito enviar os dados (limpos) para a API
   da OpenAI ou da Anthropic; depois testar `--ia` com um grupo real.
6. Testar o novo login numa rodada longa (`--grupo todos`).
7. Apontar `RELATORIO_PASTA` para o Google Drive para computador e testar.
8. Agendar a rodada (Agendador de Tarefas no Windows, sem o `pause` do `.bat`;
   cron/launchd no Linux/Mac).
9. Rodar todos os grupos (`--grupo todos --sem-grupo`) depois de validar.

---

## 13. Regra de manutenção

Toda mudança neste robô é registrada no [CHANGELOG.md](CHANGELOG.md) **e** neste
arquivo (passo a passo, tabelas, testes e próximos passos).
