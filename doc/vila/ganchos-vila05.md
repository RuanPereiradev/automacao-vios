# Vila 05 · ganchos da cena (guia para as camadas)

Esqueleto: `doc/vila/ligar_vila05_vida.py`. Ele cria `this.v5`, seis
ganchos vazios e o "plano" do Orelha ocioso. Com os ganchos vazios, o desenho é idêntico ao atual
(conferido: mesma sequência de `fillRect` em 3000 frames com uma execução simulada no meio).

Ferramentas de teste em `doc/vila/teste-vila05/` (`$T` abaixo). Para testar uma camada nova, trabalhe numa
cópia (`$V5` = uma pasta temporária com `base.html` = `bot/vila/vila.html` antes da sua camada) e só aplique no
`bot/vila/vila.html` quando estiver pronta.

## 1. Os seis ganchos (trecho exato no código)

```js
  v5Casinhas(c, f) { /*V5:CASINHAS*/ }
  v5Ossos(c, f) { /*V5:OSSOS*/ }
  v5Clima(c, f) { /*V5:CLIMA*/ }
  v5Luz(c, f) { /*V5:LUZ*/ }
  v5Agir(f) { /*V5:AGIR*/ }
  v5Humor(resultado) { /*V5:HUMOR*/ }
```

Onde são chamados (todos já ligados pelo esqueleto; não mexa nas chamadas):

| gancho | onde | quando |
|---|---|---|
| `v5Casinhas(c, f)` | `draw()`, bloco da Vila 05, logo depois de `this.drawParque(c, f);` | todo frame |
| `v5Ossos(c, f)` | logo depois do `v5Casinhas` | todo frame |
| `v5Clima(c, f)` | fim do bloco da Vila 05, depois do Orelha, dos balões e da barra de progresso | todo frame |
| `v5Luz(c, f)` | depois do `v5Clima`: é o último desenho da Vila 05 | todo frame |
| `v5Agir(f)` | `update()`, antes do movimento do Orelha (`f` = `this.frame`) | todo frame |
| `v5Humor(resultado)` | fim de cada execução do Orelha: `'ok'`, `'erro'` ou `'parou'` | 1 vez por execução |

Linhas exatas no `vila.html` (para achar com `grep`):

```js
      this.drawParque(c, f);
      this.v5Pintar(c, f, 'v5Casinhas'); this.v5Pintar(c, f, 'v5Ossos');
      ...
      this.v5Pintar(c, f, 'v5Clima'); this.v5Pintar(c, f, 'v5Luz');
    }
    this.v5Quadro();      // no update(): atualiza this.v5 e chama v5Agir
    if (this.fcur) this.fstep(); else if (this.fevq.length) this.fhandle(this.fevq.shift()); else if (!this.v5Seguir()) this.fpatrol();
```

Ordem de desenho na Vila 05 (de baixo para cima):
fundo fixo `paintParque` (grama, caminhos, cerca, casinha, mural, correio, toalha, baú, piscina, caixa de areia,
arquivo, barreira, hidrante, torre, brinquedos) → `drawParque` (bolinha quicando, bolinhas da piscina, borboletas,
brilho do pote, gota do hidrante) → **v5Casinhas** → **v5Ossos** → lanterna da casinha, luz da torre, calendário,
correio (cartas e bandeirinha), planilhas (folhas e caixas), relatório, pastinhas do arquivo → Orelha
(sombra, corpo, chapéu, folha na boca, balões, "AU", "Z", barra de progresso) → **v5Clima** → **v5Luz**.

O que o esqueleto garante em cada gancho de desenho (`v5Pintar`):
- roda entre `c.save()` e `c.restore()`: pode mudar `globalAlpha`, `globalCompositeOperation`, `filter`, etc.;
- recortado em `c.rect(1280, 0, 320, 224)`: nada vaza para a Vila 04;
- protegido por `try/catch`: um erro aparece **uma vez** no console (`Vila 05 · v5Luz: ...`) e a vila segue.
  `v5Agir` e `v5Humor` também passam por esse `try/catch` (`v5Chamar`).

## 2. Como cada camada troca o gancho (obrigatório)

Duas camadas usam o mesmo gancho (`v5Agir`: dia e humor) e o integrador vai aplicar todas em sequência, em
qualquer ordem. Por isso **nunca** troque o stub inteiro `'{ /*V5:AGIR*/ }'`. Troque só o marcador, mantendo-o
no fim, com o seu código dentro de um bloco `{ }` próprio e uma etiqueta da camada:

```python
troca("/*V5:LUZ*/", """{ /*V5:LUZ:dia*/
      const { R } = this.v5Pincel(c), v = this.v5;
      ...
    }
    /*V5:LUZ*/""")
```

- Idempotência: `if "/*V5:LUZ:dia*/" in t: sys.exit("a luz do dia já está na Vila 05")`.
- Pré-requisito: `if "v5Agir(f)" not in t: sys.exit("rode antes o ligar_vila05_vida.py")`.
- Nada de `return` no nível de cima do gancho (pularia o código de outra camada); use o bloco `{ }`.
- `const`/`let` só dentro do seu bloco (dois blocos podem ter `const v = this.v5` sem conflito).
- Métodos auxiliares: insira antes da linha do seu gancho, por exemplo
  `troca("  v5Luz(c, f) {", "  v5luzTinta(h) { ... }\n  v5Luz(c, f) {")`. Prefixe com o nome da camada
  (`v5casinhas…`, `v5ossos…`, `v5clima…`, `v5dia…`/`v5luz…`, `v5humor…`).
- Estado próprio: preguiçoso, no componente, com o prefixo: `const E = this.v5climaE || (this.v5climaE = { gotas: [] });`.
- Modelo de script: `doc/vila/ligar_orelha_agenda.py` (docstring em português, `troca`, `json.dumps(...).replace("</", "<\\u002F")`).

## 3. `this.v5` (lido por todos)

```js
this.v5 = {
  cena,         // null (servidor sem relatório real) ou o objeto abaixo; só é trocado quando algum valor muda
  hora, min,    // relógio do navegador (0–23, 0–59), ou ?v5hora=HH / HH:MM
  dia_semana,   // 0 = domingo … 6 = sábado (Date.getDay), ou ?v5dia=0..6
  humor: null,  // plano da camada humor (tem prioridade) — ver seção 4
  rotina: null, // plano da camada dia — ver seção 4
  passeio: null, // plano da camada passeio (ligar_vila05_passeio.py): vale depois do humor e antes da rotina
  params,       // { hora, min, atrasadas, graves, humor, dia } da URL (null quando não veio)
  simulado,     // true no site publicado (sem servidor)
  real,         // true quando a cena veio do /orelha/status
}
cena = { data: 'AAAA-MM-DD', gerado_em: str|null, atrasadas, graves, vencem_hoje, intimacoes, intimacoes_graves,
         parados, parados_graves, audiencias_hoje, pericias_hoje, erros, funcoes: ['agenda', 'prazos', ...] }
```

- Todos os números já vêm inteiros e `>= 0` (campo ausente = 0). `graves` = atrasadas há mais de 7 dias.
- Simulado: cena fixa de exemplo `atrasadas 24, graves 6, vencem_hoje 9, intimacoes 3, intimacoes_graves 1,
  parados 140, parados_graves 90, audiencias_hoje 1, pericias_hoje 0, erros 0`, `data` = hoje,
  `gerado_em` = hoje `T07:30:00`, todas as funções.
- Servidor: `this.state.fsrv.cena` (lido a cada 30 s). Sem relatório real → `cena = null`: **toda camada tem
  que funcionar com `cena === null`** (parque "neutro").
- `?v5atrasadas=N` e `?v5graves=N` sobrescrevem a cena (criam uma com zeros se ela for null). Não há override
  para os outros campos.
- Atualização: a cada 30 frames e logo que chega um `fsrv` novo. Para guardar algo calculado a partir da cena,
  compare a referência: `if (E.cena !== this.v5.cena) { E.cena = this.v5.cena; E.lista = ... }`.
- `?v5humor=ok|erro|parou` força o humor: o esqueleto chama `v5Humor(params.humor)` no frame 45 e passa o
  valor forçado (em vez do real) no fim de toda execução. A camada humor deve tratar `params.humor` como fixo
  (não deixar o humor "passar").
- Nunca desenhe nomes nem textos de processos: só números/quantidades viram desenho.

## 4. O Orelha: posição, plano (ir/ficar/pose) e estado

Estado do desenho: `this.fa` (`F`).

| campo | o que é |
|---|---|
| `F.x`, `F.y` | posição em pixels **absolutos** (Vila 05: x 1280–1599). Parado num ladrilho: `F.x = col_abs*16`, `F.y = lin*16` |
| desenho | 20×14 em `x−2 … x+18`, `y … y+14`; sombra em `y+14`; chapéu até `y−3`; boca em `x+17` (ou `x−3` virado) |
| `F.dir` | `'right'` ou `'left'` (só vira de lado) |
| `F.path` | lista de ladrilhos absolutos `[col, lin]` a andar; andando = `F.path.length > 0 && F.wait <= 0` |
| `F.pose` | `null`, `'sad'` (orelhas baixas), `'jatem'` (rabo + monóculo brilhando), `'bark'` (latindo) |
| `F.idle` | `{ k, t }`, `k` em `'lingua'`, `'rabo'`, `'duaspatas'`, `'latir'` (balão "AU AU"), `'rodar'`, `'cochilar'` ("Z") |
| `F.bubble` | `null`, `'!'`, `'ok'` (visto verde), `'?'` |
| `F.carry` | folha na boca; `F.fx`/`F.progress`: animação de posto durante execução (não mexa) |

Coluna absoluta = `80 + coluna local`. Converter: `colLocal = Math.round(F.x / 16) - 80`, `lin = Math.round(F.y / 16)`;
pixel local do Orelha = `F.x - 1280`.

**Não escreva em `this.fa` diretamente.** Use o plano: escreva em `this.v5.rotina` (camada dia) ou `this.v5.humor`
(camada humor), dentro do `v5Agir` ou do `v5Humor`. O esqueleto (`v5Seguir`) executa o plano quando o Orelha está
livre (`this.v5Livre()`: sem execução andando, `fphase` `'idle'` ou `'done'`); uma execução sempre passa na frente,
e quando ela acaba o plano volta a valer sozinho.

```js
plano = {
  ir: [col, lin],       // ladrilho LOCAL da Vila 05 (0–19, 0–13); ele vai pelo mapa (bfs). Sem ir: fica onde está
  idle: 'cochilar',     // animação ao chegar (uma das 6 acima)
  pose: 'sad',          // ao chegar; tem precedência sobre idle no desenho
  dir: 'left',          // para onde olha ao chegar
  balao: '!',           // balão ao chegar
  parado: true,         // só ficar parado (sem pose/idle): abana o rabo devagar
  pressa: 1.5,          // multiplica a velocidade de passeio (0.7 px/frame)
  // outros campos são livres para a camada (ex.: nome, ate: frame final)
}
this.v5.rotina = { nome: 'sesta', ir: [2, 12], idle: 'cochilar', dir: 'left' };
this.v5.humor = { nome: 'feliz', idle: 'rabo', ate: f + 600 };   // humor manda enquanto não for null
this.v5.humor = null;                                            // devolve para a rotina (ou para o passeio)
```

- Pode recriar o objeto a cada frame: o esqueleto compara pela chave (`ir`, `idle`, `pose`, `dir`, `balao`,
  `parado`); mudou a chave → recomeça (anda até o novo `ir`).
- Plano sem `ir`/`idle`/`pose`/`balao`/`parado` é ignorado (vale o passeio normal).
- `ir` bloqueado (ver mapa) → ele fica onde está. Sem plano → volta ao passeio (pausa de 60 frames).
- Passeio normal (`fpatrol`, sem plano): `[9,4] → [12,8] → [10,12] → [4,9] → [3,4]` (locais), com uma animação
  `idle` em cada parada.
- Falar: `this.fsay(texto)` troca o texto da caixa de diálogo da Vila 05 (a mesma das execuções). Só com
  `this.v5Livre()` e só quando o texto muda (nunca a cada frame). Só contagens, nada de nomes.

## 5. Mapa da Vila 05 (ladrilhos locais; `#` bloqueado, `=` caminho de areia, `.` grama andável)

```
     col 0123456789012345678 9
lin  0  ####################      cerca de cima (y 0–16)
     1  #.####..####..####.#      casinha 2–5 | mural 8–11 | correio+prateleira 14–17 (linhas 1–3)
     2  #.####..####..####.#
     3  #.####..####..####.#
     4  ==================.#      caminho (y 64–80); col 0 = portão para a Vila 04; [3,4] = porta da casinha
     5  #.=.###..=.###.##=.#      toalha 4–6 | baú 11–13 | arquivo 15–16 (linhas 5–6)
     6  #.=.###..=.###.##=.#
     7  #.=.###..=.###...=.#
     8  ==================.#      caminho (y 128–144)
     9  ####..........=##..#      caixa de areia 1–3 (linhas 9–11) | torre VIOS 15–16 (linhas 9–12)
    10  ####.###......=##..#      piscina de bolinhas 5–7 (linhas 10–11)
    11  ####.###.......##..#
    12  #..............##..#      faixa de grama de baixo (y 192–208)
    13  ####################      cerca de baixo (y 208–224)
```

Postos (locais): casinha/HOME `[3,4]`, calendário `[9,4]`, intimações `[15,4]`, arquivo `[14,6]`,
planilhas `[12,8]`, relatório `[5,8]`, torre VIOS `[14,10]`.
Perto da caixa de areia (andáveis): `[4,9]`, `[4,10]`, `[4,11]`, `[1,12]`, `[2,12]`, `[3,12]`, e por cima `[1,8]`–`[3,8]`.

## 6. Coordenadas do desenho (pixels locais: x 0–319, y 0–223)

| objeto | x | y | notas |
|---|---|---|---|
| casinha do Orelha (com telhado) | 29–84 | 10–64 | parede azul 36–76 × 36–62; porta 47–65 × 47–61; placa "ORELHA" 41–71 × 37–47; sombra 30–84 × 61–65 |
| lanterna da casinha | 77–82 | 37–44 | acesa em `R(78, 41, 3, 3)` |
| pote de água / de ração | 18–30 / 79–93 | 57–62 / 55–62 | |
| mural Calendário | 126–194 | 15–64 | |
| correio Intimações + bandeirinha | 230–269 | 24–64 | prateleira 272–286 × 28–62 |
| toalha Relatório | 64–112 | 82–126 | |
| baú Planilhas + caixas | 176–224 | 84–122 | |
| armário Arquivo | 238–274 | 77–114 | galinha de borracha 244–254 × 115–124 |
| **caixa de areia** | moldura 16–64 | 145–193 | areia 19–61 × 147–189; osso enterrado em (26,158) 10×3; buraco `disco(46,172,5)`; balde 23–32 × 173–184; pazinha 51–54 × 152–163; sombra y 191–193 |
| piscina de bolinhas | 80–128 | 161–193 | |
| barreira de agility | 186–222 | 150–170 | pneu `disco(176,178,7)`; frisbee `disco(230,187,4)` |
| torre VIOS + escorregador | 238–302 | 145–206 | hidrante 285–303 × 146–171 |
| cerca | esquerda 0–16, direita 304–320 | cima 0–16, baixo 208–224 | |
| caminhos de areia | linhas 4 e 8 inteiras (x 0–304) | 64–80 e 128–144 | colunas 2, 9, 17 (x 32–48, 144–160, 272–288) em y 80–128; coluna 14 (x 224–240) em y 144–176 |

Grama sem objeto (boa para desenhar coisas novas): x 94–125 × 16–63 (só uma corda em 98–113 × 45–49 e uma bolinha em
116,28), x 195–229 × 16–63 (frisbee azul 198–210 × 37–42, osso 194,23, bolinha 206,54), faixa de baixo x 16–236 × 194–207,
x 128–168 × 146–192 (osso 160,152, bolinha 152,186), coluna direita x 288–303 × 16–144.
Coisas que se mexem por cima do fundo: bolinha quicando (126–131 × 96–115), borboletas em volta de (150,120) ±40 e
(60,140) ±40.

## 7. Desenhando: `this.v5Pincel(c)` e `R()`

```js
v5Ossos(c, f) { { /*V5:OSSOS:ossos*/
      const { R, hs, disco, pata, osso, cores } = this.v5Pincel(c), cena = this.v5.cena;
      if (!cena) return;   // (pode usar return DENTRO do seu bloco só se o gancho for só seu)
      R(26, 158, 10, 3, '#f6f1e6');                   // retângulo local: R(x, y, w, h, cor), arredonda tudo
      R(0, 0, 320, 224, 'rgba(20,30,70,.25)');        // tinta na vila inteira (cores rgba valem)
      disco(46, 172, 5, '#c9ae76');                   // círculo cheio
      pata(40, 150, '#d2b47a');                       // patinha 5×4
      osso(30, 160, '#f6f1e6', '#d9d0bd');            // osso 10×3 (cor, sombra)
      for (let i = 0; i < Math.min(8, cena.graves); i++) {
        const q = hs(i, 0, 7);                        // pseudoaleatório determinístico por índice (inteiro >= 0)
        const sobe = Math.round(Math.sin(f * 0.05 + i) * 1.5); // animação suave pelo contador de frame
        osso(22 + q % 30, 150 + (q >> 5) % 30 + sobe, '#f6f1e6', '#d9d0bd');
      }
    }
    /*V5:OSSOS*/ }
```

(Atenção: `return` dentro do bloco sai do método inteiro. Em gancho compartilhado — `v5Agir` — use `if`.)

- `O = 1280` (deslocamento da Vila 05) vem junto; `cores` = `{ GR '#86c95f', GR2 '#74b850', GR3 '#9bd873',
  SOMBRA '#6aa84a', AREIA '#e7cf98', BORDA '#caad72', CAIXA '#ead7a4' (areia da caixa), MADEIRA '#8a5a2c' }`.
- Paleta usada no parque: madeira `#7a4a22`/`#9a6234`/`#b07a3a`/`#6e4420`, branco papel `#f6f1e6`, sombra papel
  `#d9d0bd`, vermelho `#e8483c`/`#c94b3b`/`#7d2a1f`, azul `#3d7fd1`/`#2f69b3`/`#7fb3ea`, amarelo `#f2c230`/`#e8b923`,
  rosa `#f08ac0`, contorno escuro `#201f1d`/`#3b2614`.
- Regras: pixel art em 1 px, sem antialias (nada de `arc`/`stroke`; use `R`/`disco`); animação só pelo `f`
  (ex.: `(f >> 5) % 2`, `Math.sin(f * 0.02)`), **nada de `Math.random` no desenho**; movimento suave, nada que
  pisque forte; pouca coisa por frame (centenas de `R`, não milhares).
- `v5Luz` fica por cima de tudo, inclusive da barra de progresso e dos balões do Orelha: tinta com alpha até
  ~0.35 para continuar legível. Se quiser luzes acesas por cima da tinta (lanterna, janelas), desenhe-as depois
  da tinta no próprio `v5Luz`.

## 8. Testar

```bash
T=doc/vila/teste-vila05; V5=$(mktemp -d); cp bot/vila/vila.html $V5/base.html
cp $V5/base.html $V5/<nome>.html
python3 doc/vila/<seu script> $V5/<nome>.html     # aplica
python3 doc/vila/<seu script> $V5/<nome>.html     # tem que sair dizendo que já foi aplicado
python3 $T/checar.py $V5/<nome>.html             # OK
node $T/rodar.js $V5/<nome>.html '?v5hora=21&v5atrasadas=40'   # roda 20 mil frames sem navegador
```

- `rodar.js` roda o componente em node com canvas falso (update + draw), um plano de rotina, o humor e uma
  execução simulada inteira; imprime `this.v5`, `erros de camada {}` (tem que ficar vazio) e os humores recebidos.
  Ele substitui `v5Humor` por um gravador — para testar a sua camada humor, copie e tire essa linha.
- `igual.js A.html B.html` compara a sequência de `fillRect` de dois arquivos (prova de "visual idêntico").
- No navegador: abra `file://$V5/<nome>.html?vila=5` (modo simulado; `?vila=5` abre direto na Vila 05) e junte os
  overrides: `&v5hora=19&v5dia=6&v5atrasadas=60&v5graves=20&v5humor=erro`. A tecla Enter/A roda a execução simulada.
