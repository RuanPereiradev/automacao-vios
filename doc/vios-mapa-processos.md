# Mapa das telas de Processos do VIOS (relatório por Grupo Cliente)

Levantado em 03/11/2026 no VIOS real (`roneely.vios.com.br`), com o segundo usuário,
**só lendo**: nenhum botão de gravar, apagar, editar ou "Processar" foi usado.
Sem dados de clientes neste arquivo (valores trocados por `VALOR`).

## 1. Lista de processos — `?pag=sys/processos/processos-lista.php&menu_lateral=true`

Filtros do formulário (enviado pelo botão `#Pesq`, como o robô já faz):

| Campo | Uso |
| --- | --- |
| `pesq[clientes_grupos_id]` | Grupo Cliente (83 opções; `TODOS` é o padrão da tela) |
| `pesq[limit]` | 30, 50, 100, 200, 500, 1000 ou **9999999** (sem limite prático — não há teto de 500) |
| `pesq[filtros_multi][]` (múltiplo) | padrão `ativos` + `naomigrados`. Também existem `encerrados`, `ativos_e_encerrados` ("Ativos + Encerrados no Período", usa `pesq[idata]`/`pesq[fdata]` + `pesq[tp_data]`), `todos`, `sem_cliente_contrato` etc. |
| ↳ como combinam | **com E** (conferido ao vivo em 03/11/2026, grupo de 101 processos): `ativos` + `naomigrados` = 101; `encerrados` + `naomigrados` = 35; `ativos` + `naomigrados` + `encerrados` = **0**. Por isso o robô faz duas pesquisas com `--encerrados` (a 2ª sem `ativos`) |
| `pesq[tprel]` | `A` = Completo (tela), `csv`, `P` = PDF, `amostragem` = ação em lote (**nunca usar**) |
| `pesq[tp_data]` | `data_cadastro`, `data_acao`, `data_encerrado`, ... |
| `pesq[processos_situacao_id][]` | situação (ATIVO, PROCEDENTE, IMPROCEDENTE, ENCERRADO, ARQUIVADO...) |

Linhas: `tr[id^='processos-lista_linha_']`, com `data-processos_id` (= CI) e
`data-detalhes-linha`. Rodapé: `.geratabela_total_quantidade_original` ("Total (N)") — **é o número de
linhas mostradas**, não o total do filtro (com `limit=30` e Grupo = TODOS mostrou "Total (30)").
Para pegar tudo, usar `pesq[limit]=9999999`.

Células `td[data-id="processos-lista_linha_<n>_<coluna>"]`. Colunas que existem na tela
(muitas o robô ainda não lia):

| Coluna (`data-id`) | Conteúdo | Preenchida (grupo de 101 processos) |
| --- | --- | --- |
| `processos_id` | CI | 101 |
| `nro_proc_html` | "CNJ: 0000000-00.0000.0.00.0000" (+ etiquetas `.vj-badge`) | 98 |
| `ativahtml` / `passivahtml` / `terceirohtml` | partes, uma por linha ("Autor: X", "Contrário: Y") | 101 |
| `clientes_nome` | cliente do processo | 101 |
| `cliente_escritorio` | **polo do cliente** ("Parte Passiva" / "Parte Ativa") — dado do próprio VIOS | 101 |
| `pr_areas_nome` | área (ex.: "Cível Consumidor") | 101 |
| `pr_processos_nome` | **tipo de processo** (ex.: "CÍVEL") | 97 |
| `processos_acoes_nome` | ação | 101 |
| `orgaos_nome`, `orgaos_uf`, `orgaos_texto` | órgão, UF do órgão, complemento | 101 / 101 / 9 |
| `vara`, `tipo_vara` | órgão julgador | 89 |
| `data_acao` | **data da ação / distribuição** (DD/MM/AAAA; vazio = `00/00/0000`) | 91 |
| `valor_acao`, `valor_acao_atualizado` | **valor da ação** ("50.000,00"; vazio = `0,00`) | 68 / 0 |
| `processos_situacao_nome` | situação | 0 |
| `data_encerrado`, `motivo_encerramento_desc` | encerramento | — |
| `obs_proc` | observação interna curta (fase + "LINK DO CHAT: <link>") — **interna, não vai para o cliente** | 101 |
| `objeto` | objeto/assunto | 69 |
| `advogado_nome`, `advogados_auxiliares_abr` | advogado, siglas dos auxiliares (interno) | 101 |
| `contratos_vis`, `pasta`, `pasta_cli`, `data_atualizacao`, `vida_util_concat`, `sinal_vinculo_processo` | outros | — |

Ações de cada linha: `a[title=Visualizar]` → `processos-vis.php&processos_id=<CI>` (só leitura);
`a[title=Editar]` e `a[title=Apagar]` (**nunca usar**).

## 2. Ficha do processo — `?pag=sys/processos/processos-vis.php&processos_id=<CI>`

Página montada por JavaScript (Vue): o HTML baixado sem navegador **não** traz os dados;
precisa do Selenium e esperar `.vj-bloco-info-text-area` aparecer.

Dados em 3 blocos `div.vj-bloco-info-text-area`, um `<p>` por campo:

```html
<p><strong><span>Cidade / UF</span>: </strong> <span>VALOR</span> <span class="vj-acoes-dados">...</span></p>
```

Rótulo = texto do `<strong>` sem o ":"; valor = texto do `<p>` sem o rótulo e sem `.vj-acoes-dados`.
Partes vêm como links com `vj-icon-user`, várias no mesmo `<p>` ("Contrário: A Contrário: B").

Rótulos encontrados:
- bloco 1: `N.° CNJ`, `Escritório atual`, `Departamento`, `Área`, `Advogado responsável`, `Auxiliares`,
  `Data da ação / Distribuição`, `Data da citação`
- bloco 2: `Cliente`, `Polo do cliente`, `Contrato do cliente`, `Parte ativa`, `Parte passiva`, `Terceiros`,
  `Processo` (tipo, ex.: CÍVEL), `Ação`, `Fase`, `Cidade / UF` (ex.: "Linhares / ES")
- bloco 3: `Justiça`, `Jurisdição atual`, `Comarcas / Tribunais / Órgãos adm.`, `Complemento órgão`,
  `Sistema do tribunal`, `Órgão julgador (Vara/camara)`, `Tipo de órgão julgador (Vara/camara)`,
  `Pasta cliente`, `Pasta interna`, `Valor da ação`, `Valor da ação atualizado`

**Não há campo de valor provisionado** nem de "financeira" na ficha. Seções da ficha (títulos):
Andamentos (contador), Vínculos, Pedidos (contador), Decisões, Diligências, Recados, Horas, WhatsApp,
Arquivos, Comentários, Tarefas.

### Tarefas (fonte da "Última movimentação")

Tabela DataTables (`.dataTables_wrapper` cujo `thead` tem "Tipo de tarefa"); o `thead` aparece
duplicado (cabeçalho fixo) — ler as linhas de `tbody tr`. Sem paginação no caso visto (6 tarefas,
todas na tela). Ordem: mais nova primeiro (CI decrescente). Colunas por **posição** (os `data-id`
das células são aleatórios):

| # | Coluna | Observação |
| --- | --- | --- |
| 0 | ícone de situação | — |
| 1 | CI da tarefa | número |
| 2 | Tipo de tarefa | `.vj-badge` com a situação quando há (ex.: "CANCELADA") + `<span>` com o tipo (ex.: "ANALISAR PROCESSO (CÍVEL) 2026") |
| 3 | Descrição | `div.limite-texto` (texto cortado na tela com "mais"; usar `textContent` para o texto todo). Pode ter link e senha de audiência |
| 4 | Comentários | conclusão escrita pela equipe. Na tarefa "ANALISAR PROCESSO" costuma trazer o resumo da situação ("O processo encontra-se na Turma Recursal, aguardando...") |
| 5 | Datas | "Para conclusão DD/MM/AAAA Limite DD/MM/AAAA Concluída em: DD/MM/AAAA" |
| 6 | Envolvidos | "Responsáveis: ... Concluiu a tarefa: ..." (interno) |
| 7 | Ações | **não usar** |

### Comentários
Lista "Data / Usuário Comentário": "DD/MM/AAAA HH:MM - NOME" + texto. Muitos são automáticos
("Tarefa encerrada ao enviar o(s) arquivo(s): ...").

### Arquivos
Tabela "Data | Pasta | Tipo | Descrição | Arquivo | Responsável | Tamanho | Ações". Há processos com
"CÓPIA DO PROCESSO" (PDF dos autos, dezenas de MB) — fonte possível para resumo e financeira
(etapa futura: exige baixar arquivo).

## 3. Planilha de referência × VIOS

| Campo obrigatório | De onde vem |
| --- | --- |
| ID da extração | numeração do robô |
| Número do processo | lista `nro_proc_html` |
| Parte ativa / Parte passiva | lista `ativahtml`/`passivahtml` (sem o rótulo "Autor:"/"Contrário:") ou ficha |
| Tipo de processo | lista `pr_processos_nome` (ex.: CÍVEL) |
| Órgão | lista `orgaos_nome` (+ `vara` quando houver) |
| Data da distribuição | lista `data_acao` (ou ficha "Data da ação / Distribuição") |
| Valor da ação | lista `valor_acao` |
| Valor provisionado | não está na lista nem na ficha. Existe o relatório **Relatórios → Provisão** (`?pag=sys/processos_rel/rel_provisao.php`, mesmos filtros da lista, inclusive `pesq[clientes_grupos_id]` e `pesq[limit]=9999999`; colunas `data_acao`, `clientes_nome`, `ativahtml`, `passivahtml`, `nro_proc`, `cidade_orgaos`, `pr_areas_nome`, `valor_acao`, `valor_provisionado`; sem CI na linha — casar pelo `nro_proc`). Em 03/11/2026, num grupo de 159 processos, **159 de 159 linhas com 0,00** — os valores da planilha de referência não estão no VIOS. O relatório "Lançamentos financeiros" não tem filtro de grupo. **Decisão do usuário (03/11/2026):** é uma estimativa que o advogado coloca no cadastro; o campo **sai do relatório** (fica com 13 campos). O campo saiu do código em 03/11/2026: o relatório tem 13 campos |
| Cidade/UF | ficha "Cidade / UF" (a lista só tem a UF do órgão) |
| Última movimentação | ficha → tarefas: a **concluída** mais recente, sem contar as canceladas (data de "Concluída em" + tipo + comentário ou descrição), sem links e senhas. Tarefa aberta não conta: vai para a PENDÊNCIA |
| Resumo do caso | sem IA: montado do cadastro (ação, objeto, partes, Cidade/UF); com IA: a partir da ficha + tarefas + comentários (ou, no futuro, da cópia do processo) |
| PENDÊNCIA | sem IA: tarefas abertas (sem "Concluída em", não canceladas) com o prazo; com IA: tarefas abertas e último comentário de análise |
| Financeira | não existe no VIOS; IA só se aparecer no texto das tarefas/comentários; senão "não identificada" |
