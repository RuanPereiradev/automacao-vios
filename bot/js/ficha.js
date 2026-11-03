// Ficha do processo no VIOS (processos-vis.php): lê o DOM e devolve um objeto.
//
// SÓ LEITURA: não clica, não chama fetch, não muda a página.
// O arquivo é UMA expressão (função anônima chamada na hora), sem ";" no fim:
//   - o Python roda com driver.execute_script("return (" + este arquivo + ");")
//   - no navegador, dá para colar no console e ver o objeto.
// Seção ausente -> lista vazia. Textos com espaços normalizados.
(function () {
  "use strict";

  var QUEBRA = "\n";       // <br> e blocos (div, p, li...)
  var SEPARA = "\u0001";   // começo de outra parte no mesmo campo

  var BLOCOS = {
    DIV: 1, P: 1, LI: 1, UL: 1, OL: 1, TR: 1, TABLE: 1, TBODY: 1, THEAD: 1,
    H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, SECTION: 1, ARTICLE: 1, HEADER: 1, FOOTER: 1
  };
  var IGNORAR = { SCRIPT: 1, STYLE: 1, TEMPLATE: 1, NOSCRIPT: 1 };
  var DATA = "\\d{2}/\\d{2}/\\d{4}";
  var DATA_HORA = DATA + "(?:\\s+\\d{2}:\\d{2}(?::\\d{2})?)?";
  // link "mais"/"menos" que abre o texto cortado da descrição
  var LINK_MAIS = /^(\.{3}\s*)?\(?(ver |leia )?(mais|menos)\)?$/i;
  var SECOES = ["andamentos", "vinculos", "pedidos", "decisoes", "diligencias", "recados",
    "horas", "whatsapp", "arquivos", "comentarios", "tarefas"];

  function norm(s) {
    return String(s == null ? "" : s).replace(/\s+/g, " ").trim();
  }

  // sem acento e minúsculo, para comparar rótulos
  function chave(s) {
    return norm(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  // Texto de um elemento: <br> e blocos viram QUEBRA; "pular(el)" tira pedaços;
  // "antes(el)" pode pôr um marcador antes do elemento.
  function texto(raiz, pular, antes) {
    var partes = [];
    (function andar(no) {
      if (no.nodeType === 3) {
        partes.push(no.nodeValue.replace(/\s+/g, " "));
        return;
      }
      if (no.nodeType !== 1 || IGNORAR[no.tagName]) return;
      if (no !== raiz) {
        if (pular && pular(no)) return;
        if (antes) partes.push(antes(no) || "");
      }
      if (no.tagName === "BR") {
        partes.push(QUEBRA);
        return;
      }
      var bloco = no !== raiz && BLOCOS[no.tagName];
      if (bloco) partes.push(QUEBRA);
      for (var f = no.firstChild; f; f = f.nextSibling) andar(f);
      if (bloco) partes.push(QUEBRA);
      else if (no.tagName === "TD" || no.tagName === "TH") partes.push(" ");
    })(raiz);
    return partes.join("");
  }

  function linhas(s) {
    return s.split(/[\n\u0001]/).map(norm).filter(Boolean);
  }

  function arr(lista) {
    return Array.prototype.slice.call(lista || []);
  }

  // ---------- campos dos blocos ----------

  // "Contrário: A Contrário:" + "B" -> "Contrário: A" + "Contrário: B"
  function juntarPartes(pedacos) {
    var saida = [];
    var resto = "";
    pedacos.forEach(function (p) {
      p = norm(resto + " " + p);
      resto = "";
      var m = p.match(/(?:^|\s)([^\s:;]+:)$/);
      if (m) {
        resto = m[1];
        p = norm(p.slice(0, p.length - m[1].length));
      }
      if (p) saida.push(p);
    });
    if (resto) saida.push(resto);
    return saida;
  }

  function valorDoCampo(p, rotuloEl) {
    // cada parte (ícone vj-icon-user) começa um pedaço novo
    var icones = arr(p.querySelectorAll(".vj-icon-user"));
    var inicios = icones.map(function (ic) {
      var no = ic;
      while (no.parentElement && no.parentElement !== p &&
             no.parentElement.querySelectorAll(".vj-icon-user").length === 1) {
        no = no.parentElement;
      }
      return no;
    });
    if (!inicios.length) {
      var links = arr(p.querySelectorAll("a")).filter(function (a) {
        return !(rotuloEl && rotuloEl.contains(a)) && !a.closest(".vj-acoes-dados");
      });
      if (links.length > 1) inicios = links;
    }
    // sem partes (nenhum ícone, no máximo um link): o valor vai como está
    var comPartes = inicios.length > 1;
    var bruto = texto(
      p,
      function (el) {
        return el === rotuloEl || (el.classList && el.classList.contains("vj-acoes-dados"));
      },
      function (el) {
        var i = inicios.indexOf(el);
        return i > 0 ? SEPARA : "";
      }
    );
    var pedacos = linhas(bruto);
    return (comPartes ? juntarPartes(pedacos) : pedacos).join("; ");
  }

  function lerCampos() {
    var campos = {};
    arr(document.querySelectorAll(".vj-bloco-info-text-area p")).forEach(function (p) {
      var strong = p.querySelector(":scope > strong") || p.querySelector("strong");
      if (!strong) return;
      var rotulo = norm(strong.textContent).replace(/\s*:\s*$/, "").trim();
      if (!rotulo) return;
      var valor = valorDoCampo(p, strong);
      var atual = campos[rotulo];
      if (!atual) campos[rotulo] = valor;
      else if (valor && atual !== valor) campos[rotulo] = atual + "; " + valor;
    });
    return campos;
  }

  function campo(campos, rotulo) {
    var alvo = chave(rotulo).replace(/\s+/g, "");
    for (var r in campos) {
      if (chave(r).replace(/\s+/g, "") === alvo) return campos[r];
    }
    return "";
  }

  // ---------- tabelas (DataTables ou simples) ----------

  // Só as células e linhas DIRETAS de cada tabela. Uma <table> colada dentro
  // da descrição (texto de e-mail ou Word) não pode deslocar as colunas.
  function celulasDe(tr) {
    return arr(tr.cells || tr.children).filter(function (c) { return c.tagName === "TD"; });
  }

  // tabela que está dentro de uma célula de outra tabela
  function aninhada(t) {
    return !!(t.parentElement && t.parentElement.closest("table"));
  }

  // tabelas de "el" que não estão dentro de outra tabela
  function tabelasDe(el) {
    if (el.tagName === "TABLE") return [el];
    return arr(el.querySelectorAll("table")).filter(function (t) { return !aninhada(t); });
  }

  // {cabecalho: [th...], linhas: [tr...]} das tabelas cujo cabeçalho passa no teste
  function tabelas(teste) {
    var achadas = [];
    var wrappers = arr(document.querySelectorAll(".dataTables_wrapper"));
    function cabecalhoDe(el) {
      // o thead aparece duplicado (cabeçalho fixo): usa o primeiro com texto
      var ts = tabelasDe(el);
      for (var i = 0; i < ts.length; i++) {
        if (!ts[i].tHead) continue;
        var ths = [];
        arr(ts[i].tHead.rows).forEach(function (tr) {
          arr(tr.cells).forEach(function (th) { ths.push(norm(th.textContent)); });
        });
        if (ths.join("")) return ths;
      }
      return [];
    }
    function linhasDe(el) {
      var trs = [];
      tabelasDe(el).forEach(function (t) {
        arr(t.tBodies).forEach(function (tb) { trs = trs.concat(arr(tb.rows)); });
      });
      return trs.filter(function (tr) {
        var tds = celulasDe(tr);
        if (!tds.length) return false;
        if (tds.some(function (td) { return td.classList.contains("dataTables_empty"); })) return false;
        if (tds.length === 1 && /^nenhum registro/i.test(norm(tr.textContent))) return false;
        return true;
      });
    }
    wrappers.forEach(function (w) {
      var cab = cabecalhoDe(w);
      if (teste(cab.join(" | "))) achadas.push({ cabecalho: cab, linhas: linhasDe(w) });
    });
    arr(document.querySelectorAll("table")).forEach(function (t) {
      if (t.closest(".dataTables_wrapper") || aninhada(t)) return;
      var cab = cabecalhoDe(t);
      if (teste(cab.join(" | "))) achadas.push({ cabecalho: cab, linhas: linhasDe(t) });
    });
    return achadas;
  }

  // primeira tabela com linhas (as outras podem ser o cabeçalho fixo, sem corpo)
  function primeiraComLinhas(achadas) {
    for (var i = 0; i < achadas.length; i++) if (achadas[i].linhas.length) return achadas[i];
    return null;
  }

  function celula(tr, i) {
    var td = celulasDe(tr)[i];
    return td || null;
  }

  function textoCelula(tr, i, pular) {
    var td = celula(tr, i);
    return td ? norm(texto(td, pular).replace(/[\n\u0001]/g, " ")) : "";
  }

  // ---------- tarefas ----------

  function linkMais(el) {
    return (el.tagName === "A" || el.tagName === "BUTTON" || el.tagName === "SPAN") &&
      !el.children.length && LINK_MAIS.test(norm(el.textContent)) &&
      el.parentElement && norm(el.parentElement.textContent) !== norm(el.textContent);
  }

  function dataApos(rotulo, s) {
    var m = s.match(new RegExp(rotulo + "\\s*:?\\s*(" + DATA_HORA + ")", "i"));
    return m ? norm(m[1]) : "";
  }

  function lerTarefas() {
    var achada = primeiraComLinhas(tabelas(function (cab) { return /tipo de tarefa/i.test(cab); }));
    if (!achada) return [];
    return achada.linhas.map(function (tr) {
      var tipoTd = celula(tr, 2);
      var situacao = tipoTd ? arr(tipoTd.querySelectorAll(".vj-badge")).map(function (b) {
        return norm(b.textContent);
      }).filter(Boolean).join(" / ") : "";
      var tipo = textoCelula(tr, 2, function (el) { return el.classList && el.classList.contains("vj-badge"); });

      // descrição: texto todo (a tela corta com "mais"), sem o link "mais"
      var descTd = celula(tr, 3);
      var descricao = "";
      if (descTd) {
        var alvo = descTd.querySelector(".limite-texto") || descTd;
        descricao = norm(texto(alvo, linkMais).replace(/[\n\u0001]/g, " "));
      }

      var datas = textoCelula(tr, 5);
      return {
        ci: textoCelula(tr, 1),
        situacao: situacao,
        tipo: tipo,
        descricao: descricao,
        comentarios: textoCelula(tr, 4),
        para_conclusao: dataApos("Para conclus[aã]o", datas),
        limite: dataApos("Limite", datas),
        concluida_em: dataApos("Conclu[ií]da em", datas)
      };
    }).filter(function (t) { return t.ci || t.tipo || t.descricao; });
  }

  // ---------- arquivos ----------

  function lerArquivos() {
    var achada = primeiraComLinhas(tabelas(function (cab) {
      return /(^|\| )arquivo( \||$)/i.test(cab) && /tamanho/i.test(cab) && !/tipo de tarefa/i.test(cab);
    }));
    if (!achada) return [];
    var nomes = achada.cabecalho.map(chave);
    function pos(nome, padrao) {
      var i = nomes.indexOf(nome);
      return i >= 0 ? i : padrao;
    }
    var col = {
      data: pos("data", 0), pasta: pos("pasta", 1), tipo: pos("tipo", 2),
      descricao: pos("descricao", 3), arquivo: pos("arquivo", 4)
    };
    return achada.linhas.map(function (tr) {
      return {
        data: textoCelula(tr, col.data),
        pasta: textoCelula(tr, col.pasta),
        tipo: textoCelula(tr, col.tipo),
        descricao: textoCelula(tr, col.descricao),
        arquivo: textoCelula(tr, col.arquivo)
      };
    }).filter(function (a) { return a.arquivo || a.descricao || a.data; });
  }

  // ---------- comentários ----------

  var CABECA_COMENTARIO = new RegExp("^(" + DATA_HORA + ")\\s*(?:-\\s*)?(.*)$");
  var LINHA_COMENTARIO = new RegExp("^(" + DATA_HORA + ")\\s+-\\s+(.+)$");

  // 1) tabela "Data / Usuário | Comentário"
  function comentariosDaTabela() {
    var achada = primeiraComLinhas(tabelas(function (cab) {
      return /coment/i.test(cab) && /usu[aá]rio/i.test(cab) && !/tipo de tarefa|tamanho/i.test(cab);
    }));
    if (!achada) return [];
    return achada.linhas.map(function (tr) {
      var n = celulasDe(tr).length;
      var c = { data: "", autor: "", texto: "" };
      var resto = [];
      for (var i = 0; i < n; i++) {
        var t = textoCelula(tr, i);
        var m = !c.data && t.match(CABECA_COMENTARIO);
        if (m && m[1]) {
          c.data = norm(m[1]);
          c.autor = norm(m[2]);
        } else if (t) {
          resto.push(t);
        }
      }
      c.texto = resto.join(" ");
      return c;
    }).filter(function (c) { return c.data || c.texto; });
  }

  // títulos de seção (fora de tabela): "Comentários", "Tarefas (6)"...
  function titulosDeSecao() {
    return arr(document.body ? document.body.querySelectorAll("*") : []).filter(function (el) {
      if (IGNORAR[el.tagName] || el.closest("table")) return false;
      var t = el.textContent || "";
      if (t.length > 40) return false;
      var k = chave(t).replace(/\(?\d+\)?$/, "").trim();
      if (SECOES.indexOf(k) < 0) return false;
      // fica só o elemento mais de dentro com esse texto
      return !arr(el.children).some(function (f) { return chave(f.textContent) === chave(t); });
    });
  }

  // 2) seção com título "Comentários": linhas "DD/MM/AAAA HH:MM - NOME" + texto
  function comentariosDaSecao() {
    var titulos = titulosDeSecao();
    var deComentario = titulos.filter(function (el) {
      return chave(el.textContent).indexOf("comentarios") === 0;
    });
    for (var i = 0; i < deComentario.length; i++) {
      var tit = deComentario[i];
      var area = null;
      // aba (link "#id"): o conteúdo está no painel apontado
      var link = tit.closest("a, button, [data-target], [aria-controls]");
      if (link) {
        var alvo = link.getAttribute("aria-controls") || link.getAttribute("data-target") ||
          link.getAttribute("data-bs-target") || link.getAttribute("href") || "";
        alvo = alvo.replace(/^#/, "");
        if (alvo && /^[\w-]+$/.test(alvo)) area = document.getElementById(alvo);
      }
      if (!area) {
        // sobe até antes de englobar outra seção
        area = tit;
        while (area.parentElement && area.parentElement !== document.body) {
          var pai = area.parentElement;
          var outra = titulos.some(function (t) { return t !== tit && pai.contains(t); });
          if (outra) break;
          area = pai;
        }
      }
      var lista = [];
      var atual = null;
      linhas(texto(area, function (el) { return el === tit; })).forEach(function (l) {
        var m = l.match(LINHA_COMENTARIO);
        if (m) {
          atual = { data: norm(m[1]), autor: norm(m[2]), texto: "" };
          lista.push(atual);
        } else if (atual) {
          atual.texto = norm(atual.texto + " " + l);
        }
      });
      if (lista.length) return lista;
    }
    return [];
  }

  function lerComentarios() {
    var lista = comentariosDaTabela();
    return lista.length ? lista : comentariosDaSecao();
  }

  // ---------- resultado ----------

  var campos = lerCampos();
  return {
    campos: campos,
    cidade_uf: campo(campos, "Cidade / UF"),
    fase: campo(campos, "Fase"),
    data_distribuicao: campo(campos, "Data da ação / Distribuição"),
    valor_acao: campo(campos, "Valor da ação"),
    justica: campo(campos, "Justiça"),
    sistema: campo(campos, "Sistema do tribunal"),
    tarefas: lerTarefas(),
    comentarios: lerComentarios(),
    arquivos: lerArquivos()
  };
})()
