# Vigia de cumprimentos de sentença: contexto em 24/11/2026

Documento de repasse do pje-busca (vigia VIOS → DJEN → PJe) e da aba **Cumprimentos** da Vila dos Bots.
Sem senhas e sem conteúdo do `.env`.

## 1. O problema

- Caso real: MM COMERCIO DE CALCADOS LTDA. O principal **0002754-04.2025.5.07.0038** (2ª VT Sobral) estava no VIOS.
- A exequente distribuiu o cumprimento provisório **0001368-02.2026.5.07.0038** em 29/07/2026.
- Ele saiu no DJEN em 31/07/2026 ("Lista de distribuição").
- O escritório só soube em 18/11/2026, com bloqueio via Sisbajud: **112 dias de exposição**.
- Objetivo, em ordem de prioridade:
  1. saber quando chega um cumprimento de sentença ou execução contra um cliente;
  2. se não der, saber quando chega qualquer processo em que o escritório não está, para um humano olhar;
  3. em último caso, saber quando o juiz associa o cumprimento ao processo principal.
- Regra: **não burlar CAPTCHA**. A certidão trabalhista por CNPJ exige CAPTCHA e não lista cumprimento provisório; foi descartada.

## 2. Como o vigia funciona (níveis)

| Nível | O que vê | Fonte | Situação |
|---|---|---|---|
| 1 | Cumprimento de sentença / execução contra o cliente | API pública do DJEN (sem login, sem CAPTCHA), busca pelo **nome** da parte | Pronto |
| 2 | Qualquer processo novo contra o cliente fora do VIOS | Mesma busca do DJEN (amarelo) | Pronto (sai no relatório do dia) |
| 3 | Juiz associou um processo ao principal | PJe > Acervo Geral > filtro "Processos com Associação" > "Processos associados" (login pelo Loy Trust desde 26/11/2026; antes, Presto) | Pronto; JavaScript conferido no PJe real; falta a 1ª rodada completa |

**Tribunais (desde 26/11/2026):** o DJEN busca cada empresa no TRT7 e nos outros TRTs em que ela tem processo no
VIOS (TRT22, TRT17, TRT16, TRT6, TRT5, TRT3); 1ª busca em cada TRT novo = base. O nível 3 continua só no TRT7.

**Lista de clientes vigiados:** foto diária do VIOS (`vigia.py vios`): área Trabalhista, cliente no polo passivo, processos ativos.
Em 24/11 são 162 empresas e 363 processos.

**Detalhes do nível 1 (DJEN):**
- O DJEN **não busca por CNPJ**: a API só filtra por nome, número, OAB e tribunal, e as publicações não trazem o CNPJ.
- Por isso o vigia:
  - busca pelo nome do VIOS;
  - **calibra pelo nome do tribunal**: lê o polo passivo de 2 processos já conhecidos de cada empresa e repete a calibração a cada 30 dias;
  - usa os **nomes conferidos pela equipe** na aba.
- Descarta a publicação em que o cliente é **autor** (polo ativo).
- "Ação de cumprimento" de sindicato (art. 872 da CLT) não é cumprimento de sentença: fica amarelo.
- A 1ª busca com um nome novo vira **auditoria**, sem alerta. Depois disso, só alerta o que for novo.

**Processo principal de cada cumprimento:** o robô liga cada cumprimento ao seu principal no VIOS (resultado: "cliente nosso"), nesta ordem:
1. número de processo **citado no texto** da publicação;
2. **mesmo exequente** (polo ativo da publicação = Autor no VIOS), de preferência na **mesma vara**, porque o cumprimento é distribuído por dependência.

**Detalhes do nível 3 (PJe):**
- No Acervo Geral, o robô liga o filtro **"Processos com Associação"** (em 24/11: 60 dos 358 processos do acervo).
- Para cada linha:
  1. clica em "Processos associados";
  2. lê a tabela "Processo Associado · Órgão Julgador" (5 por página, botão "Próximo");
  3. fecha com Esc.
- Depois desliga o filtro e percorre o acervo inteiro e a aba **Arquivados**, 100 por página, para classificar cada processo do VIOS:
  - no acervo;
  - **arquivado no PJe**, mas ainda ativo no VIOS: atualizar o VIOS (ex.: 0000029-50.2026.5.07.0024, arquivado em 09/11/2026 depois de acordo);
  - fora dos dois: 2º grau/TST, ou a sociedade não está no processo.
- **Não** abre documento, não peticiona e não altera nada.
- A pesquisa pelo número no campo do acervo **não** serve. Na 1ª tentativa (24/11), a lista parou de atualizar depois de 3 buscas e quase tudo saiu como "fora do acervo", por engano.
- A 1ª rodada completa é **base**. Depois disso:
  - associado novo fora do VIOS, com o **principal no VIOS** (cliente nosso) = **vermelho**;
  - associado novo fora do VIOS, com o principal também fora da lista do VIOS (antigo, arquivado, outra área) = **amarelo**;
  - associado novo que já está no VIOS = informação;
  - processo que acabou de entrar no acervo vira base só dele.
- **Regra segura da classe** (24/11/2026): antes de avisar, o vigia consulta no DJEN a classe do associado novo fora do VIOS.

  | O que o DJEN diz do associado | Resultado |
  |---|---|
  | Classe de cumprimento, execução ou liquidação (basta uma publicação) | alerta (vermelho/amarelo) |
  | Sem publicação, erro na consulta ou classe que o robô não reconhece (agravo de petição, embargos...) | alerta: conferir |
  | Todas as classes confirmadas como outra coisa (ação trabalhista, homologação de acordo, ação de cumprimento do sindicato...) | "outra classe": sai do alerta, **continua listado** na aba e no relatório |

  O número do associado anterior ao do principal vira só observação: nunca tira o alerta.
- Achado na conferência: o CumPrSe **0001772-66.2024.5.07.0024** (DFA) **está no Acervo Geral do login** e aparece associado ao principal 0000064-49.2022.5.07.0024.
  Ou seja, o advogado do login já está habilitado nele; falta só o processo no VIOS.

## 3. Resultados até agora

**Rodada de base do DJEN (24/11/2026):** 162 empresas, 5.431 publicações, 0 erro.

| Cumprimento fora do VIOS | Principal (no VIOS) | Como foi ligado | Cliente |
|---|---|---|---|
| **0001226-95.2026.5.07.0038** · CumPrSe · 2ª VT Sobral · 1ª publ. 06/07/2026 | 0000743-70.2023.5.07.0038 · CI 21042 | Mesmo exequente (Antonio Kelson Ferreira Carvalho) e mesma vara | DFA Distribuição e Logística |
| **0001772-66.2024.5.07.0024** · CumPrSe · 1ª VT Sobral · 1ª publ. 12/12/2024 | 0000064-49.2022.5.07.0024 · CI 21045 | Citado na publicação e mesmo exequente (Robson Rodrigues Teixeira) | DFA Representações |
| 0001368-02.2026.5.07.0038 (caso MM, validação) | 0002754-04.2025.5.07.0038 · CI 27466 | Mesmo exequente e mesma vara | MM Comércio |

- **Ação pendente:** o advogado responsável (Francisco Johnys, segundo o VIOS) deve conferir no PJe os dois cumprimentos da DFA: habilitação e bloqueio.
  O 0001226 foi ligado só por exequente e vara; vale confirmar o principal no PJe.
- Outros fora do VIOS: 216 (base; muitos antigos). Ações de cumprimento de sindicato: 30, sem alerta.
- **Empresas sem nenhuma publicação:** 27. Destas, **12 têm processo do TRT7 no VIOS**, ou seja, provável nome diferente no tribunal.
  São elas: A Afonso Linhares (5 processos), Kaio Supermercado (3), Supermercado Popular (3), F. V. R. Marques (2), Comercial Bezerra, Express Transportes, K L C, Mercantil Onofre Serrano, Onofre Pousada, SCC Melo, Utilmix e Varejão Chocobalas.
  Outra hipótese: os processos são anteriores ao DJEN. A conferência fica na aba.
- **1ª rodada completa do nível 3 (24/11/2026):** 358 processos no acervo, 60 com associação, 60 lidos, 0 erro, 69 associados na base.
  - O PJe confirmou as duas ligações deduzidas pelo DJEN: 0001226-95.2026 → 0000743-70.2023 e 0001772-66.2024 → 0000064-49.2022.
  - Associados de principais do VIOS para conferir: 0001669-59.2024 (Casa das Redes; advogados de fora do escritório), 0001668-95.2025 (Afrânio; agravo de instrumento em recurso de revista na 5ª Turma), 0000682-42.2023 (F. V. R. Marques) e 0000930-15.2022 (DFA). Os dois últimos não têm publicação no DJEN.
  - 97 processos do VIOS ficaram "fora do acervo". Na amostra, parte estava em 2º grau/TST e parte arquivada; daí a leitura da aba Arquivados.
- **Teste do nível 3 (24/11/2026, PJe real):** `vigia.py associados --numero 0002754-04.2025.5.07.0038 --simular`.
  Login pelo Presto ok. Leu 1 associado: 0001368-02.2026.5.07.0038 (2ª VT Sobral), marcado como base.

## 4. Aba Cumprimentos (Vila dos Bots)

Endereço: `http://192.168.30.21:5001/cumprimentos`, atrás da senha das páginas.

**Números do topo:**
- pendentes de conferência;
- maior espera desde a 1ª publicação;
- cumprimentos fora do VIOS;
- associados novos no PJe;
- empresas sem publicação;
- última verificação.

**Seções da página:**
1. **Cumprimento de sentença / execução fora do VIOS**: em cada processo, "Cliente nosso: principal X no VIOS (CI, empresa, advogado)" e a conferência.
   Situações: Pendente · Providência em curso · Escritório já atua · Não é do escritório.
2. **Associados novos no PJe (nível 3)**, com a mesma conferência.
3. **Verificação**: última rodada de cada nível e dois botões, "Verificar agora no DJEN" e "Verificar associados no PJe". Também lista os relatórios de cada dia.
4. **Empresas sem nenhuma publicação no DJEN**: CNPJ, processos do TRT7 no VIOS e nomes buscados.
   A equipe marca Pendente, "Nome corrigido" (até 3 nomes exatos do polo passivo no PJe, que o vigia passa a buscar) ou "Nome está certo".
5. **Ações de cumprimento (sindicato)**: seção recolhida, sem alerta.

## 5. Comandos (no Mac mini, dentro de `~/automacao-vios/pje-busca`)

| Comando | Para quê |
|---|---|
| `python3 vigia.py vios` | Foto do VIOS (lista de clientes e processos). Rodar antes do DJEN |
| `python3 vigia.py djen` | Verificação diária no DJEN (inclui calibração de nomes e ligação com o principal) |
| `python3 vigia.py djen --refazer-base` | Apaga só o estado do DJEN e refaz a auditoria |
| `python3 vigia.py principais` | Só liga cada cumprimento ao principal no VIOS (rápido) |
| `python3 vigia.py andamentos` | Só grava as publicações (DJEN) dos cumprimentos fora do VIOS, para a aba (rápido) |
| `python3 vigia.py associados` | Nível 3 no PJe (filtro de associação + lista do acervo, 10–15 min, Chrome do Mac + Loy Trust) |
| `python3 vigia.py associados --paginas 1 --sem-cobertura` | Teste rápido: só a 1ª página do filtro, sem gravar |
| `python3 vigia.py status` / `fila` | Resumo do estado / processos do TRT7 |
| `cd ~/automacao-vios && ./servidor_mac.sh instalar` | Reinicia a Vila dos Bots depois de mudanças |

**Requisitos do nível 3:**
- Chrome aberto no perfil de trabalho, com "Permitir JavaScript de Apple Events" ligado (`albi/presto.py liberar-chrome`).
- Loy Trust instalado e com sessão aberta no Chrome do Mac (padrão desde 26/11/2026; `VIGIA_ACESSO=loy`).
  Com `VIGIA_ACESSO=presto`: Presto funcionando e `PRESTO_PIN` no `pje-busca/.env`.

## 6. Onde fica cada coisa

| Arquivo / tabela | Conteúdo |
|---|---|
| `pje-busca/vigia.py` | Comandos do vigia |
| `pje-busca/src/vigia_estado.py` | Foto do VIOS (tabelas `empresas`, `processos`, `rodadas`) |
| `pje-busca/src/vigia_djen.py` | DJEN, calibração, nomes conferidos, principal (`djen_processos`, `djen_nomes`, `djen_empresas`, `djen_consultas`, `djen_principais`, `djen_rodadas`) |
| `pje-busca/src/vigia_associados.py` | Nível 3 no PJe (`assoc_principais`, `assoc_associados`, `assoc_acervo`, `assoc_rodadas`) |
| `pje-busca/dados/vigia.sqlite` | Estado (fora do git) |
| `pje-busca/dados/cumprimentos_conferencia.json` | Conferência da equipe por processo (fora do git, permissão 600) |
| `pje-busca/dados/nomes_conferidos.json` | Nomes do tribunal informados pela equipe (fora do git, permissão 600) |
| `pje-busca/saida/djen_AAAA-MM-DD.txt`, `associados_AAAA-MM-DD.txt` | Relatórios do dia (fora do git) |
| `bot/cumprimentos.py`, `bot/templates/cumprimentos.html` | Aba Cumprimentos (só lê o banco do vigia) |
| Testes | `pje-busca/tests/` (38) e `tests/test_cumprimentos.py` (59 na suíte da vila) |

## 7. Pendências (em ordem)

1. **Commit do restante.** O commit ef2f2d8 levou só parte dos arquivos. Faltam:
   - `bot/envio_web.py` (rotas da aba), `bot/templates/vila_dos_bots.html`, `.env.example`;
   - `pje-busca/src/vigia_associados.py`, `pje-busca/tests/test_associados.py`, `pje-busca/vigia.py`;
   - docs e testes.

   **Não** adicionar `orelha/.env~` nem `.DS_Store`.
2. **1ª rodada completa do nível 3** (`python3 vigia.py associados`), que cria a base. Conferir no resumo:
   - "fora do acervo";
   - erros;
   - associados já existentes fora do VIOS.
3. **Advogado confere os dois cumprimentos da DFA** e registra na aba.
4. **Equipe confere os nomes** das 12 empresas com processo no TRT7 e sem publicação no DJEN.
5. **Agendamento diário** no Mac mini (launchd): **feito** (24/11/2026). `./servidor_mac.sh vigia instalar`:
   seg a sex, `vios` + `djen` às 7h40 e `associados` às 3h20 (`vigia.py agenda manha|madrugada`, mesma trava do botão
   da aba). 1ª rodada da manhã pelo launchd ok (24/11/2026: 363 processos, DJEN 162 empresas, 0 erro). A da
   madrugada roda numa janela do Terminal (`agenda_madrugada.command`), que tem a permissão de Acessibilidade exigida
   pelo login do Presto. Rodada de 25/11 às 3h20: entrou no console do Presto, mas o quadro não apareceu porque a
   **tela do Mac estava bloqueada**. Correção: o robô liga a tela, para logo se estiver bloqueada e a rodada roda
   com `caffeinate -dims`; falta desligar o bloqueio automático no Mac mini (`./servidor_mac.sh vigia tela liberar`)
   e repetir o teste.
6. **Canal do alerta**: **só a aba**, por enquanto (decisão de 24/11/2026).
7. **Segurança:**
   - trocar as senhas e chaves que apareceram em texto durante a configuração (Sonar, Presto/VIOS, chave da IA);
   - deixar no `pje-busca/.env` só `PRESTO_*`, `VIOS_*` e `VIGIA_*`;
   - considerar um usuário do VIOS só para o robô.

## 8. Riscos e mitigação

| Risco | Efeito | Mitigação |
|---|---|---|
| Nome da empresa no tribunal diferente do VIOS | DJEN não acha o processo | Calibração automática + conferência de nomes na aba + nível 3 |
| Homônimo / nome parecido | Alerta falso | Filtro de polo; conferência "Não é do escritório" |
| Principal ligado só por exequente | Ligação errada em caso raro | Mostra "como achei"; mesma vara tem prioridade; confirmar no PJe |
| Principal fora do Acervo Geral do login do Presto | Nível 3 não cobre aquele processo | Relatório lista "fora do acervo"; avaliar outro login |
| Tela do PJe muda (filtro, paginador, janela) | Leitura falha | Rodada marcada "incompleta" (não vira base); capturas em `logs/associados/` |
| Sessão do PJe / Presto cai ou Chrome fecha | Rodada incompleta | Rodada marcada "incompleta"; rodar de novo |
| Lista do VIOS limitada a Trabalhista ativo, polo passivo | Principal arquivado ou de outra área não é ligado | Aparece como "Principal não achado no VIOS" para conferência humana |
| Sem agendamento | Nada roda sozinho | Pendência 5 |
| Loy Trust sem sessão ou extensão atualizada mudar a janelinha | Nível 3 não entra no PJe | Robô para com o motivo; `VIGIA_ACESSO=presto` como reserva; testes em `tests/test_loy.py` |
| Tela do Mac bloqueada na madrugada | Rodada dos associados não entra no PJe | `vigia tela liberar`; robô para com o motivo; sala do servidor trancada |
