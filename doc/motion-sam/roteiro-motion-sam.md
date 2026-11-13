# Motion do Sam — fluxo do modo automático (briefing para o profissional de motion)

**O que é o Sam:** um robô que trabalha para o escritório de advocacia. Todo dia ele entra no VIOS
(sistema do escritório), pega as intimações (avisos da Justiça) que ainda não têm tarefa, uma IA lê
cada uma e decide as tarefas e os prazos, e o robô cria essas tarefas no VIOS sozinho. Depois mostra
um relatório para a equipe conferir.

**A ideia do vídeo:** "Intimação chega → tarefa pronta, sem ninguém digitar." Mostrar o trabalho do
dia inteiro de uma pessoa sendo feito por um robô, em ordem, com os números reais.

- Duração sugerida: 45 a 60 s (versão curta de 20 s: cenas 2, 4, 5 e 7).
- Formato: 16:9 (e uma versão vertical 9:16 se der).
- Idioma: português do Brasil.

---

## Quem aparece (personagens e lugares)

O Sam já tem um visual: a **Fortaleza do Dragão** (pixel art, estilo Senhor dos Anéis). Se o motion
seguir o visual da casa, usar estes papéis; se for um motion mais corporativo, são só ícones.

| Elemento | O que representa |
| --- | --- |
| **Sam** (robô cromado, pixel art) | O robô que faz todo o trabalho |
| **Torre VIOS** | O sistema VIOS, onde as tarefas são criadas (tem barra de vida que cai a cada tarefa criada) |
| **Dragão** (no salão do tesouro) | O trabalho pesado: acorda quando o robô começa a criar tarefas |
| **Mensageiro** | Avisa que a intimação/arquivo chegou |
| **Ferreiro** | Entrar no VIOS (login) |
| **Mago** | Conferir duplicatas e a análise |
| **Arqueira** | Dá as contagens (quantas intimações, quantas tarefas) |

Referência visual pronta: `doc/desing_sam/fortaleza-dragao.html` (abrir no navegador).
Paleta: noite azul escura, molduras e botões dourados. Fontes: Lora (texto) e Silkscreen (títulos/números).

---

## O fluxo automático — 7 cenas

```
 VIOS            CAPTURA         ANÁLISE (IA)      TRAVAS           LANÇAMENTO        CONFERÊNCIA      RELATÓRIO
 intimações  →   robô entra  →   lê e decide   →   segurança   →    cria tarefas  →  confere que   →  equipe vê
 sem tarefa      e coleta        tarefa + prazo    antes de gravar   no VIOS            gravou            tudo
```

### Cena 1 — O problema (0–5 s)
- Pilha de intimações chegando no VIOS durante o dia (cartões de papel caindo, cada um com um número de CI).
- Texto na tela: **"Toda intimação vira uma tarefa com prazo."**
- Dar a ideia de volume: dezenas por dia; na segunda-feira, as três do fim de semana juntas.

### Cena 2 — Captura (5–12 s)
- O Sam acorda, o Ferreiro abre a porta da Torre VIOS (**entrando no VIOS**).
- Ele filtra: só as intimações **de ontem** (na segunda: sexta a domingo) e **só as que ainda não têm tarefa**.
- Os cartões se alinham e entram numa lista. Contador sobe: **"11 intimações capturadas"** (exemplo real de 22/10).
- Texto: **"Só o que falta fazer."**

### Cena 3 — A IA lê e decide (12–25 s) — a cena principal
- Cada intimação passa por uma lupa/leitor. A IA segue o **manual da Controladoria** (um livro/pergaminho que abre ao lado).
- Para cada uma, saem três coisas, que aparecem como etiquetas:
  1. **Tipo de ato** (sentença, audiência, RPV, perícia…);
  2. **Tarefa** escolhida de uma lista oficial (ex.: "ANALISAR SENTENÇA", "MINUTAR RECURSO", "CIÊNCIA");
  3. **Prazo em dias** lido do texto.
- Em seguida entra o **calendário**: o **código** (não a IA) calcula as datas — conta só segunda a sexta,
  e define o **prazo fatal** e a **data da tarefa 2 dias antes (D-2)**. Mostrar o calendário riscando
  dias e a data caindo.
- Mensagem-chave: **a IA entende o texto; as datas são calculadas por regra, sem chute.**
- Detalhe de bastidor: a análise vai em lote (mais barato) e há um teto de gasto — pode virar um
  pequeno medidor de custo no canto (opcional).

### Cena 4 — As travas de segurança (25–32 s)
Antes de criar qualquer coisa, o Mago confere. Cada intimação passa por um portão e **só passa se estiver completa**.
Mostrar o portão deixando passar a maioria e barrando algumas, com o motivo:

| Barrada quando… | Texto sugerido na tela |
| --- | --- |
| Falta informação (audiência sem horário, perícia sem local) | "Falta informação — vai para a equipe" |
| Já tem tarefa no VIOS | "Já tem tarefa — não duplica" |
| A análise pede olho humano | "Conferência humana" |
| A data calculada já passou | "Data vencida — refazer análise" |
| Cópia de outra intimação | "Cópia — vale a original" |

- Mensagem-chave: **o robô prefere não lançar a lançar errado.** As barradas vão para a pessoa, nunca somem.

### Cena 5 — Lançamento: o dragão acorda (32–44 s)
- O dragão desperta (a criação de tarefas começou). O Sam abre a intimação na Torre VIOS e **preenche o formulário**:
  tarefa, data, horário (se tiver), responsáveis, e a descrição, com as linhas de prazo em **negrito vermelho**.
- Ritmo repetido para cada intimação (loop curto, acelerar depois da 2ª):
  **Adicionar** (entra num quadro provisório) → **confere o quadro** → **Gravar**.
- A cada tarefa criada: contador **"Tarefas criadas 3/14"** sobe e a **barra de vida da Torre VIOS cai** na mesma proporção.
- Se aparecer um erro: o dragão cospe fogo num herói e a Torre mostra o motivo; o robô segue para a próxima.

### Cena 6 — Conferência (44–50 s)
- Depois de gravar, o Sam **abre a tela de conferência do VIOS e confere se cada tarefa realmente está lá**
  (não apagada). Carimbo verde ✓ em cada uma.
- Texto: **"Gravou? O robô confere."**
- Fim do dragão: ele volta ao covil. Faixa: **"Missão cumprida."**

### Cena 7 — Relatório para a equipe (50–58 s)
- Abre o relatório **Envio automático**: um pergaminho claro com moldura dourada.
- Mostrar, em zoom rápido: números do dia (intimações, **lançadas**, **não lançadas**, contas de prazo
  conferidas), uma linha por intimação com tarefa e datas, e os **pontos de atenção** em destaque
  (ex.: tarefa cai em feriado, prazo no texto sem data).
- Cada data aparece com **✓ bate** (conta refeita por fora) ou **✗ diverge**.
- Fecho (58–60 s): **"Intimação entrou. Tarefa saiu. Equipe só confere."** + logo do Sam.

---

## Números e frases que podem aparecer (reais, do projeto)

- 11 intimações capturadas em um dia (22/10/2026); 19 de 20 tarefas lançadas em 26/10/2026.
- Contagem de prazo: **segunda a sexta**; tarefa **2 dias antes do prazo fatal (D-2)**.
- Corte do meio-dia: análise/ciência feita depois das 12h vai para o próximo dia útil.
- Cada tarefa passa por: Adicionar → Conferir quadro → Gravar → Conferir no VIOS.

> Usar os números como exemplo; não afirmar totais que não vêm do relatório do dia.

## Tom e regras

- Confiável e calmo; a graça é o **robô cuidadoso**, não o robô rápido demais.
- Mostrar sempre as **barradas** (cena 4): é o que passa segurança para a equipe.
- Não mostrar dados reais de clientes (nomes, números de processo): usar texto de exemplo borrado ou fictício.
- Não aparecer senha, usuário ou qualquer dado do `.env`.

## O que ainda precisa ser confirmado antes de animar

1. **Quando o automático dispara.** Hoje as etapas rodam por comando/página (captura, análise,
   lançamento com `--confirmar`). O agendamento diário (ex.: às 17h) ainda não está fechado na
   documentação. Se for citar horário no vídeo, confirmar com a equipe.
2. **Versão do visual:** com o tema Fortaleza do Dragão (cenas 2, 5 e 6 ficam bem lúdicas) ou versão
   corporativa limpa (só ícones e telas).
3. **Telas reais vs. ilustradas:** para a cena 7 dá para gravar a tela do relatório (`/automatico`) com
   dados de teste.
