# Relatório de Processos por Grupo Cliente — VIOS

Robô que entra no VIOS com o **segundo usuário** (mesmo escritório,
`roneely.vios.com.br`, outro login e outras permissões), lista os processos de
cada **Grupo Cliente** e gera um `.txt` por grupo. Esse `.txt` vai para outra IA,
que escreve um relatório fácil de ler para o cliente leigo.

> **Status: em ajuste.** A primeira versão (28/10/2026) funciona, mas ainda vai
> mudar. Este arquivo é atualizado a cada alteração.
> Histórico de mudanças: [CHANGELOG.md](CHANGELOG.md). Robô de intimações:
> [DOCUMENTACAO.md](DOCUMENTACAO.md).

---

## 1. Objetivo

| Etapa | O que faz | Status |
| --- | --- | --- |
| 1. Login | Entra no VIOS com o usuário do `.env.usuario2` | ✅ Pronto |
| 2. Navegação | Abre Relatórios e depois a lista de Processos | ✅ Pronto |
| 3. Pesquisa | Escolhe o Grupo Cliente, "Mostrar" = 500, Pesquisar | ✅ Pronto (3A FRIOS) |
| 4. Leitura | Lê a tabela de processos do grupo | ✅ Pronto (17 de 17) |
| 5. TXT | Um `.txt` por grupo, organizado para outra IA | 🚧 Em ajuste |
| 6. Google Drive | Salvar os `.txt` direto numa pasta do Drive | ⏳ Pendente |

---

## 2. Passo a passo do que o robô faz

1. **Login** com o usuário e a senha do `.env.usuario2`.
2. Abre a tela de **Relatórios**
   (`?pag=sys/relatorios/relatorios.php`, em `NAVEGACAO_URL_FINAL`).
3. Abre a lista de **Processos**
   (`?pag=sys/processos/processos-lista.php&menu_lateral=true`).
4. Lê as opções do filtro **Grupo Cliente** (`pesq[clientes_grupos_id]`): são
   82 grupos (ex.: `97 = 3A FRIOS`). O padrão da tela é "TODOS", mas o robô
   **nunca usa o TODOS**: cada grupo é pesquisado separadamente.
5. Escolhe o grupo, muda **Mostrar** de 30 para **500** (com 30, um grupo
   grande viria cortado) e aciona **Pesquisar**. Os outros filtros ficam no
   padrão da tela: **Ativos** e **Não migrados**, ou seja, processos encerrados
   não entram.
6. Lê a tabela pelo `data-id` de cada célula (`processos-lista_linha_N_<coluna>`),
   o mesmo método do robô de intimações. Confere o total com o rodapé
   "Total (N)" da tabela; se não bater, avisa no log.
7. Monta e salva o `.txt` do grupo e repete para o próximo grupo.

**Por que preenche por JavaScript:** depois do login o VIOS abre um popup de
Recado por cima da tela. O robô não mexe nele: escolhe o filtro e envia o
formulário pelo mesmo botão Pesquisar (`#Pesq`), sem clicar na tela.

### Só leitura

A tela de Processos tem botões perigosos: **Apagar** e **Editar** em cada linha
e o **Processar**, que executa ações em lote (apagar processos, trocar advogado,
etc.). O robô **não usa nenhum deles**: só escolhe filtros, pesquisa e lê.

---

## 3. O arquivo gerado

Caminho: `saida_usuario2/relatorios/AAAA-MM-DD/<GRUPO>.txt`
(ex.: `saida_usuario2/relatorios/2026-10-28/3A FRIOS.txt`). Cada execução cria
a pasta do dia; rodar de novo no mesmo dia sobrescreve o arquivo do grupo.

Conteúdo:

1. **Cabeçalho**: grupo, data e hora da leitura, total de processos.
2. **Resumo**: quantos processos por empresa/pessoa do grupo, por área e pela
   posição do cliente (autor ou réu).
3. **Por empresa** do grupo, um bloco por processo:

| Campo no .txt | Coluna do VIOS (`data-id`) |
| --- | --- |
| Número do processo | `nro_proc_html` (sem as etiquetas) |
| Área | `pr_areas_nome` |
| Tipo de ação | `processos_acoes_nome` |
| Assunto (objeto) | `objeto` |
| Onde tramita | `orgaos_nome` + `orgaos_uf` |
| Quem entrou com a ação (parte ativa) | `ativahtml` |
| Contra quem (parte passiva) | `passivahtml` |
| Posição do cliente | calculada: o nome do cliente aparece na parte ativa (autor) ou passiva (réu) |
| Advogado responsável | `advogado_nome` |
| Vínculo | ícone `sinal_vinculo_processo`: processo principal ou apenso |
| Contrato | `contratos_vis` |
| Código interno no VIOS (CI) | `processos_id` |

**Ficam de fora** (uso interno do escritório): siglas dos auxiliares
(`advogados_auxiliares_abr`, ex.: CARL, JOHN), etiquetas como "Cliente OURO" e a
coluna "Processo" (`pr_processos_nome`), que só repete a área.

Campo vazio no VIOS aparece como "não informado".

---

## 4. Como rodar

No Windows, na pasta do projeto:

```powershell
.\rodar_usuario2.bat                        # grupos de PROCESSOS_GRUPOS no .env.usuario2
.\rodar_usuario2.bat --grupo "pao mix"      # outro grupo
.\rodar_usuario2.bat --grupo "3A FRIOS|PÃO MIX"   # vários, separados por |
.\rodar_usuario2.bat --grupo todos          # os 82 grupos
```

Ou dois cliques em `rodar_usuario2.bat`.

- O nome do grupo não depende de acento nem de maiúsculas
  (`"pao mix"` acha `PÃO MIX`).
- Deu certo quando o log mostra `<GRUPO>: N processos, 0 com erro -> <arquivo>`.
- O aviso `Error terminating service process` no fim é do Selenium no Windows
  e pode ser ignorado.

Sem o `.bat`:

```powershell
.\.venv\Scripts\python.exe relatorio_processos.py .env.usuario2 --grupo "3A FRIOS"
```

---

## 5. Primeira instalação (Windows)

```powershell
cd C:\Rfeitosa-projetos\automacao-vios
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.usuario2.example .env.usuario2    # e preencher usuário e senha
```

- O `requirements.txt` tem a linha `pkg_resources==0.0.0` (resto do
  `pip freeze` no Ubuntu), que faz a instalação falhar no Windows. Até ela ser
  removida, apague essa linha antes de instalar.
- O `rodar.sh` e os outros `.sh` procuram `.venv/bin/python` (Linux/Mac) e
  não funcionam no Windows; use o `rodar_usuario2.bat`.

---

## 6. Configuração (`.env.usuario2`)

Modelo versionado: `.env.usuario2.example`. O `.env.usuario2` real tem a senha
e **não vai para o GitHub**.

| Variável | Uso | Valor atual |
| --- | --- | --- |
| `SISTEMA_URL` | Página de login | `https://roneely.vios.com.br/entrar.php?` |
| `SISTEMA_USUARIO` / `SISTEMA_SENHA` | Login do segundo usuário | (no `.env.usuario2`) |
| `LOGIN_CAMPO_USUARIO` / `LOGIN_CAMPO_SENHA` | Campos de login | iguais aos do robô de intimações |
| `NAVEGACAO_URL_FINAL` | Tela aberta depois do login | `.../?pag=sys/relatorios/relatorios.php` |
| `PROCESSOS_GRUPOS` | Grupos do filtro Grupo Cliente, separados por `\|`, ou `todos` | `3A FRIOS` |
| `RELATORIO_PASTA` | Pasta dos `.txt` (vazio = `<SAIDA_PASTA>/relatorios`) | vazio |
| `SAIDA_PASTA` | Pasta de saída deste usuário | `saida_usuario2` |
| `HEADLESS` | Chrome sem janela | `false` |
| `TIMEOUT` | Espera máxima (s) | `20` |
| `MANTER_ABERTO` | Chrome continua aberto no fim | `true` |

---

## 7. Arquivos do projeto

```
automacao-vios/
├── relatorio_processos.py    # entrada: login → grupos → um .txt por grupo
├── rodar_usuario2.bat        # atalho no Windows (aceita --grupo)
├── bot/processos_grupo.py    # pesquisa por grupo, leitura da tabela e montagem do .txt
├── .env.usuario2.example     # modelo do .env do segundo usuário
├── .env.usuario2             # configuração real (NÃO versionar — tem senha)
└── saida_usuario2/relatorios/  # .txt gerados (NÃO versionar — dados de clientes)
```

Reaproveita do robô de intimações: `bot/config.py`, `bot/login.py`,
`bot/navegador.py`, `bot/navegacao.py` e o log em `logs/bot.log` (prints de erro
em `logs/erro_*.png`).

---

## 8. Segurança

- **Só leitura** no VIOS (ver seção 2).
- **Um `.env` por usuário**: o `.bat` sempre usa o `.env.usuario2`, e o log
  confirma o usuário em "Login OK como ...". Cada execução abre um Chrome com
  perfil limpo, então as sessões dos dois usuários não se misturam.
- **Fora do GitHub** (`.gitignore`): `.env.*` (menos os `.example`),
  `saida_*/`, `imgs/` (prints de tela) e `logs/`. Os `.txt` têm dados de
  clientes e partes.
- A senha do segundo usuário foi passada por chat na configuração: trocar e
  atualizar `SISTEMA_SENHA` no `.env.usuario2`.

---

## 9. Pontos de atenção

- **Só processos ativos e não migrados** (filtro padrão da tela). Encerrados
  não entram.
- **Limite de 500 por grupo**: a tela não mostra mais que isso; acima, seria
  preciso usar a exportação CSV.
- **Cadastro inconsistente no VIOS aparece no relatório.** No 3A FRIOS
  (28/10/2026):
  - CI 29191: cliente A AFONSO LINHARES (MATRIZ), mas a parte é ANTONIO AFONSO
    LINHARES (posição "não identificada"); "Onde tramita" = "000petição".
  - CI 27513 (INPI): sem partes cadastradas.

---

## 10. Testes

| Data | Grupo | Resultado |
| --- | --- | --- |
| 28/10/2026 | 3A FRIOS | 17 processos, 0 erros — igual à tabela copiada do VIOS |

---

## 11. Próximos passos

1. Ajustar o que estava errado na primeira versão (a definir).
2. Salvar no Google Drive: instalar o Google Drive para computador e apontar
   `RELATORIO_PASTA` para a pasta sincronizada.
3. Rodar todos os grupos (`--grupo todos`) depois de validar o formato.

---

## 12. Regra de manutenção

Toda mudança neste robô é registrada no [CHANGELOG.md](CHANGELOG.md) **e** neste
arquivo (passo a passo, tabelas, testes e próximos passos).
