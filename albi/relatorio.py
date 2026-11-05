"""Albi — relatório dos processos encontrados (sem ninguém abrir as planilhas).

Lê o resultado.txt de uma execução e as planilhas baixadas do Sonar ("Baixar Resultados";
o arquivo vem como .xls, mas é .xlsx por dentro) e escreve, na mesma pasta:
  relatorio.html   por empresa: resumo de todas as pessoas e, para quem tem processos, cada
                   processo (número, tribunal, vara, ramo, ação, assunto, data, papel da pessoa,
                   outra parte, valor, status e link)
  relatorio.pdf    o mesmo, em PDF (precisa do Chrome; sem ele, fica só o HTML)
  processos.csv    um processo por linha, para abrir no Excel
  mensagem.txt     uma mensagem resumida por empresa, pronta para mandar (WhatsApp/e-mail) à
                   empresa que pediu a pesquisa (CPF mascarado; o detalhe vai no relatorio.pdf)
  mensagens_cac.*  uma mensagem por pessoa com processos, no padrão da CAC (mensagem_cac.py), com
                   as movimentações de cada processo na API pública do CNJ (datajud.py; guardadas
                   em datajud/ dentro da pasta)

Só biblioteca padrão (o PDF usa o Selenium que o Albi já tem). Não entra no Sonar. Sem IA.

uso (dentro de albi/):
  .venv/bin/python relatorio.py PASTA_DO_RESULTADO [--sem-pdf] [--sem-datajud]
"""
import base64
import csv
import html
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
# colunas da planilha do Sonar que o relatório usa (nome do cabeçalho na linha 5)
COLUNAS = {"doc": "CPF/CNPJ", "nome": "Nome/Razão Social", "base": "Online /  Histórico", "numero": "Número único",
           "link": "Link do Processo", "instancia": "Instância do Processo", "comarca": "Comarca", "uf": "UF",
           "tribunal": "Tribunal", "orgao": "Órgão Julgador", "ramo": "Ramo do Direito", "tema": "Tema",
           "acao": "Tipo de ação", "distribuicao": "Data de Distribuição", "ativo": "Polo Ativo",
           "passivo": "Polo Passivo", "outras": "Outras Partes", "advogados": "Advogados", "moeda": "Moeda",
           "valor": "Valor da causa", "digital": "Processo Digital", "segredo": "Segredo de Justiça",
           "status": "Status Processo", "antigo": "Número Antigo"}
VAZIO = {"", "N/A", "NA", "-", "—", "NO-URL"}
ENCERRADO = ("ARQUIV", "BAIXA", "EXTIN", "ENCERR", "TRANSITAD")
DESTAQUE = ("TRABALH", "CRIMIN", "PENAL")
ASSINATURA = "RONEELY FEITOSA & SOCIEDADE DE ADVOGADOS"  # o escritório (o mesmo Sacado padrão do Albi)
SEPARADOR = "=" * 48  # entre as mensagens de empresas diferentes no mensagem.txt
MAX_ANDAMENTO = 5  # processos em andamento listados por pessoa na mensagem (o resto: "e mais N")


class RelatorioErro(Exception):
    pass


def _sem_acento(texto):
    t = unicodedata.normalize("NFKD", texto or "")
    return re.sub(r"\s+", " ", "".join(c for c in t if not unicodedata.combining(c))).strip().upper()


def _limpo(v):
    v = (v or "").strip()
    return "" if _sem_acento(v) in VAZIO else v


def so_digitos(v):
    return re.sub(r"\D", "", v or "")


# ---------------- planilha (.xlsx, mesmo com extensão .xls) ----------------
def _coluna(ref):
    return re.match(r"[A-Z]+", ref).group(0)


def ler_planilha(caminho):
    """Lista de processos (dicts com as chaves de COLUNAS) de uma planilha do Sonar."""
    try:
        z = zipfile.ZipFile(caminho)
    except zipfile.BadZipFile:
        raise RelatorioErro(f"{Path(caminho).name}: não é uma planilha .xlsx")
    with z:
        nomes = z.namelist()
        comp = []
        if "xl/sharedStrings.xml" in nomes:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(NS + "si"):
                comp.append("".join(t.text or "" for t in si.iter(NS + "t")))
        folha = "xl/worksheets/sheet1.xml" if "xl/worksheets/sheet1.xml" in nomes else next(
            (n for n in sorted(nomes) if n.startswith("xl/worksheets/sheet")), None)
        if not folha:
            raise RelatorioErro(f"{Path(caminho).name}: planilha sem folha")
        linhas = []
        for row in ET.fromstring(z.read(folha)).iter(NS + "row"):
            cel = {}
            for c in row.iter(NS + "c"):
                v, inl = c.find(NS + "v"), c.find(NS + "is")
                if c.get("t") == "s" and v is not None:
                    val = comp[int(v.text)]
                elif inl is not None:
                    val = "".join(t.text or "" for t in inl.iter(NS + "t"))
                else:
                    val = v.text if v is not None else ""
                if val:
                    cel[_coluna(c.get("r", "A"))] = val
            linhas.append(cel)
    cab = next((i for i, l in enumerate(linhas) if COLUNAS["numero"] in l.values()), None)
    if cab is None:
        raise RelatorioErro(f"{Path(caminho).name}: não achei o cabeçalho (coluna \"Número único\")")
    pos = {}
    for col, nome in linhas[cab].items():
        for k, v in COLUNAS.items():
            if _sem_acento(nome) == _sem_acento(v):
                pos[k] = col
    processos = []
    for l in linhas[cab + 1:]:
        num = l.get(pos.get("numero"), "")
        if len(so_digitos(num)) < 15:  # descrição das colunas, cabeçalho repetido, linha vazia
            continue
        processos.append({k: (l.get(col) or "").strip() for k, col in pos.items()})
    return processos


# ---------------- formatação ----------------
def cnj(numero):
    d = so_digitos(numero)
    if len(d) != 20:
        return numero
    return f"{d[:7]}-{d[7:9]}.{d[9:13]}.{d[13]}.{d[14:16]}.{d[16:]}"


def formatar_doc(doc):
    d = so_digitos(doc)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return doc


def valor(v, moeda="R$"):
    try:
        n = float(str(v).replace(",", "."))
    except ValueError:
        return _limpo(v)
    if not n:
        return ""
    t = f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{_limpo(moeda) or 'R$'} {t}"


def data(v):
    m = re.match(r"(\d{2}/\d{2}/\d{4})", v or "")
    return m.group(1) if m else _limpo(v)


def _data_ordem(v):
    try:
        return datetime.strptime(data(v), "%d/%m/%Y")
    except ValueError:
        return datetime.min


def partes(texto):
    """"PAPEL – NOME (doc)" por linha -> [(papel, nome, doc)]."""
    out = []
    for linha in (texto or "").split("\n"):
        linha = linha.strip()
        if _sem_acento(linha) in VAZIO:
            continue
        m = re.match(r"(.+?)\s+[–-]\s+(.+?)(?:\s*\(([^()]*)\))?(?:\s*\[[^\]]*\])?\s*$", linha)
        out.append((m.group(1).strip(), m.group(2).strip(), (m.group(3) or "").strip()) if m else ("", linha, ""))
    return out


def _nomes(lista, maximo=3):
    nomes = [n for _, n, _ in lista]
    return ", ".join(nomes[:maximo]) + (f" e mais {len(nomes) - maximo}" if len(nomes) > maximo else "")


def papel(proc, doc, nome):
    """Como a pessoa pesquisada aparece no processo: (polo, papel, outra parte)."""
    d, n = so_digitos(doc), _sem_acento(nome)
    for polo, chave, outra in (("Polo passivo", "passivo", "ativo"), ("Polo ativo", "ativo", "passivo"),
                               ("Outra parte", "outras", None), ("Advogado(a)", "advogados", None)):
        for p, nm, dd in partes(proc.get(chave)):
            if (d and so_digitos(dd) == d) or (n and _sem_acento(nm) == n):
                contra = _nomes(partes(proc.get(outra))) if outra else _nomes(partes(proc.get("ativo")) + partes(proc.get("passivo")))
                return polo, p.title() if p else polo, contra
    return "Não identificado", "", _nomes(partes(proc.get("ativo")) + partes(proc.get("passivo")))


def encerrado(proc):
    st = _sem_acento(proc.get("status"))
    return any(x in st for x in ENCERRADO)


def situacao_processo(proc):
    st = _limpo(proc.get("status"))
    if not st:
        return "Não informado"
    return st.capitalize() if st.isupper() else st


# ---------------- resultado.txt ----------------
def ler_resultado(pasta):
    """resultado.txt -> (titulo, [pessoas]); pessoa: empresa, doc, nome, pedido, situacao, arquivos."""
    caminho = Path(pasta) / "resultado.txt"
    if not caminho.exists():
        raise RelatorioErro(f"não achei {caminho}")
    titulo, empresa, pessoas = "", "", []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        s = linha.strip()
        if s.startswith("# Resultado do Albi"):
            titulo = s.lstrip("# ").strip()
        if not s or s.startswith("#") or set(s) <= {"-"}:
            continue
        if s.upper().startswith("EMPRESA:"):
            empresa = s.split(":", 1)[1].strip()
            continue
        campos = [c.strip() for c in s.split(" ; ")]
        if len(campos) < 3:
            continue
        arquivos = []
        if len(campos) >= 5 and re.search(r"\.(pdf|xlsx?)$", campos[-1], re.I):
            arquivos = [a.strip() for a in campos.pop().split(" + ") if a.strip()]
        pedido = so_digitos(campos[2]) if campos[2].startswith("S") else ""
        pessoas.append({"empresa": empresa, "doc": campos[0], "nome": campos[1], "pedido": pedido,
                        "situacao": " ; ".join(campos[3:]), "arquivos": arquivos})
    return titulo, pessoas


def montar(pasta):
    """Lê tudo e devolve (titulo, pessoas), cada pessoa com "processos" (lista) e "aviso"."""
    pasta = Path(pasta)
    titulo, pessoas = ler_resultado(pasta)
    for p in pessoas:
        p["processos"], p["aviso"] = [], ""
        planilhas = [a for a in p["arquivos"] if re.search(r"\.xlsx?$", a, re.I)]
        sit = _sem_acento(p["situacao"])
        if "ENCONTRAD" in sit and "NAO" not in sit.split("·")[0] and not planilhas:
            p["aviso"] = "processos encontrados, mas a planilha não foi baixada (use \"Baixar de novo\")"
        for a in planilhas:
            arq = (pasta / a).resolve()
            if pasta.resolve() not in arq.parents or not arq.exists():
                p["aviso"] = f"planilha não encontrada: {a}"
                continue
            try:
                lidos = ler_planilha(arq)
            except (RelatorioErro, ET.ParseError, KeyError, OSError) as e:
                p["aviso"] = f"não consegui ler a planilha: {e}"
                continue
            for proc in lidos:
                proc["polo"], proc["papel"], proc["contra"] = papel(proc, proc.get("doc") or p["doc"], p["nome"])
                proc["encerrado"] = encerrado(proc)
            p["processos"] += lidos
        p["processos"].sort(key=lambda x: (x["encerrado"], -_data_ordem(x.get("distribuicao")).toordinal()))
    return titulo, pessoas


# ---------------- saída ----------------
def _resumo(p):
    ps = p["processos"]
    return {"total": len(ps), "andamento": sum(1 for x in ps if not x["encerrado"]),
            "passivo": sum(1 for x in ps if x["polo"] == "Polo passivo"),
            "destaques": sorted({_limpo(x.get("ramo")).capitalize() for x in ps
                                 if any(d in _sem_acento(x.get("ramo")) for d in DESTAQUE)})}


def _situacao_curta(p):
    s = p["situacao"]
    if p["processos"]:
        return f"{len(p['processos'])} processo(s)"
    if "NAO CONSTA" in _sem_acento(s):
        return "Não consta processo"
    return s or "—"


CSS = """
@page { size: A4 landscape; margin: 11mm 10mm; }
* { box-sizing: border-box; }
body { font: 10.5px/1.4 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1d1d1f; margin: 0; background: #fff; }
main { max-width: 1400px; margin: 0 auto; padding: 18px; }
h1 { font-size: 20px; margin: 0 0 2px; }
h2 { font-size: 16px; margin: 26px 0 8px; padding-bottom: 4px; border-bottom: 2px solid #1d1d1f; page-break-after: avoid; }
h3 { font-size: 13px; margin: 18px 0 4px; page-break-after: avoid; }
.suave { color: #6e6e73; }
.topo { display: flex; justify-content: space-between; gap: 16px; align-items: flex-end; flex-wrap: wrap; }
.numeros { display: flex; gap: 10px; flex-wrap: wrap; margin: 10px 0; }
.numero { border: 1px solid #d2d2d7; border-radius: 6px; padding: 6px 12px; min-width: 110px; }
.numero b { display: block; font-size: 18px; }
table { width: 100%; border-collapse: collapse; margin: 6px 0 10px; }
th, td { border: 1px solid #d2d2d7; padding: 4px 6px; text-align: left; vertical-align: top; }
th { background: #f2f2f4; font-weight: 600; }
tr { page-break-inside: avoid; }
.com td:first-child { border-left: 3px solid #c9302c; }
.tag { display: inline-block; border-radius: 3px; padding: 0 5px; font-size: 9.5px; font-weight: 600; white-space: nowrap; }
.and { background: #fde8e7; color: #a4231f; } .enc { background: #ececee; color: #555; }
.pas { background: #fff1d6; color: #8a5a00; } .ok { color: #1e7b34; } .aviso { color: #a4231f; font-weight: 600; }
.nowrap { white-space: nowrap; } .num { font-family: ui-monospace, Menlo, Consolas, monospace; white-space: nowrap; }
a { color: #0b57d0; text-decoration: none; }
.pessoa { page-break-inside: auto; }
.rodape { margin-top: 24px; font-size: 9.5px; }
@media print { main { padding: 0; } .pessoa { page-break-before: auto; } }
"""


def escrever_html(caminho, titulo, pessoas):
    e = html.escape
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    empresas = []
    for p in pessoas:
        if not empresas or empresas[-1][0] != p["empresa"]:
            empresas.append((p["empresa"], []))
        empresas[-1][1].append(p)
    h = [f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
         f'<title>Relatório de processos</title><style>{CSS}</style></head><body><main>']
    nomes = ", ".join(e(emp or "(sem empresa)") for emp, _ in empresas)
    h.append(f'<div class="topo"><div><h1>Relatório de processos · {nomes}</h1>'
             f'<div class="suave">Pesquisa de Processos no Sonar (Leme Forense) · gerado pelo Albi em {agora}'
             f'{" · " + e(titulo) if titulo else ""}</div></div></div>')
    for emp, ps in empresas:
        com = [p for p in ps if p["processos"]]
        h.append(f'<h2>{e(emp or "(sem empresa)")}</h2>')
        h.append('<div class="numeros">' + "".join(f'<div class="numero"><b class="{c}">{q}</b>{t}</div>' for q, t, c in (
            (len(ps), "pessoa(s) no arquivo", ""), (len(com), "com processos", "aviso" if com else ""),
            (sum(1 for p in ps if "NAO CONSTA" in _sem_acento(p["situacao"])), "não consta processo", "ok"),
            (sum(len(p["processos"]) for p in ps), "processo(s) no total", ""))) + "</div>")
        h.append('<table><tr><th>Nome</th><th>CPF/CNPJ</th><th>Pedido</th><th>Resultado</th><th>Em andamento</th>'
                 '<th>Como réu / polo passivo</th><th>Destaques</th></tr>')
        for p in ps:
            r = _resumo(p)
            nome = f'<a href="#S{e(p["pedido"])}">{e(p["nome"])}</a>' if p["processos"] else e(p["nome"])
            h.append(f'<tr class="{"com" if p["processos"] else ""}"><td>{nome}</td><td class="num">{e(formatar_doc(p["doc"]))}</td>'
                     f'<td class="nowrap">{"S" + e(p["pedido"]) if p["pedido"] else "—"}</td>'
                     f'<td>{e(_situacao_curta(p))}{"<br><span class=aviso>" + e(p["aviso"]) + "</span>" if p["aviso"] else ""}</td>'
                     f'<td>{r["andamento"] if p["processos"] else ""}</td><td>{r["passivo"] if p["processos"] else ""}</td>'
                     f'<td>{e(", ".join(r["destaques"]))}</td></tr>')
        h.append("</table>")
        for p in com:
            r = _resumo(p)
            h.append(f'<section class="pessoa" id="S{e(p["pedido"])}"><h3>{e(p["nome"])} '
                     f'<span class="suave">· {e(formatar_doc(p["doc"]))} · pedido S{e(p["pedido"])} · {r["total"]} processo(s), '
                     f'{r["andamento"]} em andamento, {r["passivo"]} como réu/polo passivo</span></h3>')
            h.append('<table><tr><th>Processo</th><th>Tribunal · comarca · vara</th><th>Ramo · ação · assunto</th>'
                     '<th>Distribuição</th><th>Papel da pessoa</th><th>Outra parte</th><th>Valor da causa</th><th>Status</th></tr>')
            for x in p["processos"]:
                link = x.get("link", "")
                num = e(cnj(x.get("numero", "")))
                if re.match(r"https?://", link):
                    num = f'<a href="{e(link)}">{num}</a>'
                local = " · ".join(e(v) for v in (_limpo(x.get("tribunal")), _limpo(x.get("comarca")), _limpo(x.get("orgao"))) if v)
                inst = _limpo(x.get("instancia"))
                assunto = _limpo(x.get("tema"))
                tag_polo = f'<span class="tag pas">{e(x["polo"])}</span>' if x["polo"] == "Polo passivo" else e(x["polo"])
                tag_st = f'<span class="tag {"enc" if x["encerrado"] else "and"}">{"Encerrado" if x["encerrado"] else "Em andamento"}</span>'
                segredo = " · segredo de justiça" if _sem_acento(x.get("segredo")) == "SIM" else ""
                h.append(f'<tr><td class="num">{num}{"<br><span class=suave>" + e(inst) + "</span>" if inst else ""}</td>'
                         f'<td>{local}</td>'
                         f'<td><b>{e(_limpo(x.get("ramo")).capitalize())}</b>{" · " + e(_limpo(x.get("acao")).capitalize()) if _limpo(x.get("acao")) else ""}'
                         f'{"<br><span class=suave>" + e(assunto.capitalize()) + "</span>" if assunto else ""}</td>'
                         f'<td class="nowrap">{e(data(x.get("distribuicao")))}</td>'
                         f'<td>{tag_polo}{"<br>" + e(x["papel"]) if x["papel"] and x["papel"] != x["polo"] else ""}</td>'
                         f'<td>{e(x["contra"]) or "—"}</td><td class="nowrap">{e(valor(x.get("valor"), x.get("moeda")))}</td>'
                         f'<td>{tag_st}<br><span class="suave">{e(situacao_processo(x))}{segredo}</span></td></tr>')
            h.append("</table></section>")
    h.append('<p class="rodape suave">Dados como vieram do Sonar (bases online e histórico dos tribunais). '
             '"Papel da pessoa" é achado pelo CPF/CNPJ dela nas partes do processo. Confira no tribunal antes de decidir.</p>')
    h.append("</main></body></html>")
    Path(caminho).write_text("\n".join(h), encoding="utf-8")


def _celula(v):
    v = str(v or "")
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v  # não vira fórmula no Excel


def escrever_csv(caminho, pessoas):
    cab = ["Empresa", "Nome", "CPF/CNPJ", "Pedido", "Processo", "Instância", "Tribunal", "Comarca", "UF",
           "Órgão julgador", "Ramo", "Tipo de ação", "Assunto", "Distribuição", "Papel da pessoa", "Polo",
           "Polo ativo", "Polo passivo", "Valor da causa", "Situação", "Status no tribunal", "Link"]
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:  # com BOM: o Excel abre com acento certo
        w = csv.writer(f, delimiter=";")
        w.writerow(cab)
        for p in pessoas:
            for x in p["processos"]:
                w.writerow([_celula(v) for v in (
                    p["empresa"], p["nome"], formatar_doc(p["doc"]), "S" + p["pedido"], cnj(x.get("numero", "")),
                    _limpo(x.get("instancia")), _limpo(x.get("tribunal")), _limpo(x.get("comarca")), _limpo(x.get("uf")),
                    _limpo(x.get("orgao")), _limpo(x.get("ramo")), _limpo(x.get("acao")), _limpo(x.get("tema")),
                    data(x.get("distribuicao")), x["papel"], x["polo"],
                    "; ".join(n for _, n, _ in partes(x.get("ativo"))), "; ".join(n for _, n, _ in partes(x.get("passivo"))),
                    valor(x.get("valor"), x.get("moeda")), "Encerrado" if x["encerrado"] else "Em andamento",
                    situacao_processo(x), x.get("link") if re.match(r"https?://", x.get("link", "")) else "")])


def escrever_pdf(html_caminho, pdf_caminho, driver=None):
    """Imprime o relatorio.html em PDF pelo Chrome (o do Albi, se já estiver aberto)."""
    proprio = driver is None
    if proprio:
        from selenium import webdriver
        o = webdriver.ChromeOptions()
        o.add_argument("--headless=new")
        driver = webdriver.Chrome(options=o)
    try:
        driver.get(Path(html_caminho).resolve().as_uri())
        dados = driver.execute_cdp_cmd("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True})
        Path(pdf_caminho).write_bytes(base64.b64decode(dados["data"]))
    finally:
        if proprio:
            driver.quit()


def mascarar_doc(doc):
    """CPF no padrão de mascaramento (LGPD): ***.456.789-**. CNPJ fica inteiro (é de empresa)."""
    d = so_digitos(doc)
    return f"***.{d[3:6]}.{d[6:9]}-**" if len(d) == 11 else formatar_doc(doc)


def _frase(texto):
    """"EXECUCAO FISCAL" -> "Execucao fiscal" (o Sonar manda tudo em maiúsculas)."""
    t = _limpo(texto)
    return t[:1].upper() + t[1:].lower() if t == t.upper() else t  # "2ª VARA" também (ª não é maiúscula)


def _qtd(n, um, varios):
    return f"{n} {um if n == 1 else varios}"


def _data_titulo(titulo):
    m = re.search(r"(\d{2}/\d{2}/\d{4})", titulo or "")
    return m.group(1) if m else datetime.now().strftime("%d/%m/%Y")


def mensagens(titulo, pessoas, assinatura=ASSINATURA):
    """Uma mensagem por empresa: [(empresa, texto)]. Só o que já está no relatório, resumido."""
    empresas = []
    for p in pessoas:
        if not empresas or empresas[-1][0] != p["empresa"]:
            empresas.append((p["empresa"], []))
        empresas[-1][1].append(p)
    out = []
    for emp, ps in empresas:
        com = [p for p in ps if p["processos"]]
        nada = [p for p in ps if not p["processos"] and "NAO CONSTA" in _sem_acento(p["situacao"])]
        outros = [p for p in ps if p not in com and p not in nada]
        l = [f"Olá, equipe {emp}!" if emp else "Olá!", "",
             f"Segue o resultado da pesquisa de processos judiciais solicitada, concluída em {_data_titulo(titulo)} "
             f"(consulta no Sonar · Leme Forense, nos tribunais do Brasil).", "",
             f"Pessoas pesquisadas: {len(ps)}",
             f"• Sem processos encontrados: {len(nada)}",
             f"• Com processos encontrados: {len(com)}"]
        if outros:
            l.append(f"• Sem resultado ainda / a conferir: {len(outros)}")
        if com:
            l += ["", "COM PROCESSOS"]
            for i, p in enumerate(com, 1):
                ps_ = p["processos"]
                and_ = [x for x in ps_ if not x["encerrado"]]
                enc = len(ps_) - len(and_)
                reu = sum(1 for x in ps_ if x["polo"] == "Polo passivo")
                l += ["", f"{i}. {p['nome']} (CPF {mascarar_doc(p['doc'])})",
                      f"   {_qtd(len(ps_), 'processo', 'processos')}: {len(and_)} em andamento e {enc} "
                      f"{'encerrado' if enc == 1 else 'encerrados'}. É ré/parte passiva em {reu}."]
                r = _resumo(p)
                if r["destaques"]:
                    l.append(f"   Atenção: há processo(s) de {', '.join(d.lower() for d in r['destaques'])}.")
                if and_:
                    l.append("   Em andamento:")
                    for x in and_[:MAX_ANDAMENTO]:
                        onde = " · ".join(v for v in (_limpo(x.get("tribunal")), _frase(x.get("orgao"))) if v)
                        quem = x["papel"] or x["polo"]
                        l.append(f"   – {_frase(x.get('acao')) or _frase(x.get('ramo')) or 'Processo'}"
                                 f"{' (' + _frase(x.get('ramo')) + ')' if _limpo(x.get('ramo')) and _limpo(x.get('acao')) else ''}"
                                 f" · {onde} · nº {cnj(x.get('numero', ''))}"
                                 f"{' · como ' + quem.lower() if quem and quem != 'Não identificado' else ''}"
                                 f"{' · desde ' + data(x.get('distribuicao')) if data(x.get('distribuicao')) else ''}"
                                 f"{' · valor ' + valor(x.get('valor'), x.get('moeda')) if valor(x.get('valor'), x.get('moeda')) else ''}")
                    if len(and_) > MAX_ANDAMENTO:
                        l.append(f"   – e mais {len(and_) - MAX_ANDAMENTO} em andamento (no relatório).")
                if enc:
                    ramos = sorted({_frase(x.get("ramo")).lower() for x in ps_ if x["encerrado"] and _limpo(x.get("ramo"))})
                    l.append(f"   Encerrados: {enc}{' (' + ', '.join(ramos) + ')' if ramos else ''}.")
                if p["aviso"]:
                    l.append(f"   Obs.: {p['aviso']}.")
        if nada:
            l += ["", "SEM PROCESSOS ENCONTRADOS", ", ".join(p["nome"] or mascarar_doc(p["doc"]) for p in nada) + "."]
        if outros:
            l += ["", "SEM RESULTADO AINDA / A CONFERIR"]
            # para a empresa, sem texto interno do Albi: só se ainda está processando ou em conferência
            l += [f"• {p['nome'] or mascarar_doc(p['doc'])}: " + ("resultado ainda em processamento"
                  if "SEM RESULTADO" in _sem_acento(p["situacao"]) else "em conferência") for p in outros]
        fim = []
        if com:
            fim.append("O relatório completo, com todos os processos (número, vara, partes, valor e status), segue em anexo.")
        elif not outros:
            fim.append("Nenhum processo foi encontrado para as pessoas pesquisadas.")
        if outros:
            fim.append("Assim que os resultados pendentes saírem, enviamos a atualização.")
        l += [""] + fim + [
              "Os dados são os das bases dos tribunais consultadas pelo Sonar.", "",
              "Qualquer dúvida, estamos à disposição.", "", "Atenciosamente,", assinatura]
        out.append((emp, "\n".join(l)))
    return out


def escrever_mensagem(caminho, titulo, pessoas, assinatura=ASSINATURA):
    textos = [t for _, t in mensagens(titulo, pessoas, assinatura)]
    Path(caminho).write_text(f"\n\n{SEPARADOR}\n\n".join(textos) + "\n", encoding="utf-8")


def gerar(pasta, driver=None, pdf=True, assinatura=ASSINATURA, datajud=True):
    """Gera relatorio.html, processos.csv, mensagem.txt e (com pdf=True) relatorio.pdf. Devolve um resumo."""
    pasta = Path(pasta)
    titulo, pessoas = montar(pasta)
    escrever_html(pasta / "relatorio.html", titulo, pessoas)
    escrever_csv(pasta / "processos.csv", pessoas)
    escrever_mensagem(pasta / "mensagem.txt", titulo, pessoas, assinatura or ASSINATURA)
    import mensagem_cac  # aqui dentro: o mensagem_cac usa as funções deste arquivo
    mensagem_cac.gerar(pasta, pessoas, datajud=datajud)
    info = {"pessoas": len(pessoas), "com_processos": sum(1 for p in pessoas if p["processos"]),
            "processos": sum(len(p["processos"]) for p in pessoas), "avisos": [p["aviso"] for p in pessoas if p["aviso"]],
            "pdf": False}
    if pdf:
        try:
            escrever_pdf(pasta / "relatorio.html", pasta / "relatorio.pdf", driver)
            info["pdf"] = True
        except Exception as ex:  # sem Chrome: fica o HTML (que também imprime)
            info["erro_pdf"] = str(ex).splitlines()[0] if str(ex) else type(ex).__name__
    return info


def main(*args):
    args = list(args)
    sem_pdf, sem_dj = "--sem-pdf" in args, "--sem-datajud" in args
    args = [a for a in args if a not in ("--sem-pdf", "--sem-datajud")]
    if not args:
        print(__doc__)
        return 2
    try:
        info = gerar(args[0], pdf=not sem_pdf, datajud=not sem_dj)
    except RelatorioErro as ex:
        print(f"Erro: {ex}", file=sys.stderr)
        return 2
    print(f"Relatório: {info['pessoas']} pessoa(s), {info['com_processos']} com processos, "
          f"{info['processos']} processo(s){'' if info['pdf'] else ' (sem PDF: ' + info.get('erro_pdf', 'pulado') + ')'}")
    for a in info["avisos"]:
        print("Aviso:", a)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
