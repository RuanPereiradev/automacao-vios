"""Acha o comprovante de protocolo na galeria de arquivos da tarefa de protocolo, lê o PDF e
extrai o número CNJ, o órgão julgador e o valor da causa."""
import base64
import io
import logging
import re
import unicodedata
from dataclasses import dataclass

from pypdf import PdfReader

from bot.vios import CNJ

log = logging.getLogger(__name__)

# rótulos que podem vir logo depois do valor quando o PDF junta as linhas
_PROXIMO = r"(?=\s*(?:\n|[ÚU]ltima\s+distribui|Valor\s+da\s+causa|Classe|Assuntos?\s*:|Processo\s+refer|Segredo|Justi[çc]a\s+gratuita|Pedido\s+de\s+liminar|$))"


@dataclass
class Dado:
    chave: str
    rotulo: str  # rótulo do campo na tela de edição do processo
    regex: str  # grupo 1 = o valor
    so_digitos: bool  # compara só os dígitos (a tela pode formatar diferente)


DADOS = [
    Dado("cnj", "N.° CNJ", "(" + CNJ.pattern + ")", True),
    Dado("orgao", "Órgão julgador (Vara/câmara)", r"[ÓO]rg[ãa]o\s+julgador\s*:\s*(.+?)" + _PROXIMO, False),
    Dado("valor", "Valor da ação", r"Valor\s+da\s+causa\s*:\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})", True),
]


class ComprovanteErro(Exception):
    pass


def arquivos(driver, cfg):
    """Arquivos da galeria da tarefa já aberta: [{texto, href}]. O endereço do arquivo fica no
    data-url da caixa (o href é '#'). Arquivo apagado fica de fora."""
    saida = []
    for el in driver.find_elements(*cfg.comprovante_link):
        item = driver.execute_script(
            """
            const a = arguments[0];
            const caixa = a.closest('.vios-file-box') || a;
            const nome = caixa.querySelector('.vios-file-box-name-file');
            const url = a.dataset.url || a.getAttribute('href') || '';
            return {texto: ((nome || a).textContent || '').replace(/\\s+/g, ' ').trim(),
                    href: url && url !== '#' ? new URL(url, location.href).href : '',
                    apagado: !!caixa.querySelector("[title='Apagada']")};
            """,
            el,
        )
        if item["href"] and not item["apagado"]:
            saida.append(item)
    return saida


def achar(driver, cfg):
    """O comprovante de protocolo na galeria de arquivos já aberta. Tem que haver exatamente um."""
    candidatos = [l for l in arquivos(driver, cfg)
                  if re.search(cfg.comprovante_texto, l["texto"], re.IGNORECASE)]
    if len(candidatos) != 1:
        nomes = "; ".join(c["texto"] for c in candidatos) or "nenhum"
        raise ComprovanteErro(f"esperado 1 comprovante de protocolo, achei {len(candidatos)} ({nomes})")
    return candidatos[0]


def ler(driver, href, timeout):
    """Texto do PDF, baixado com a sessão do navegador (não sai da página do processo)."""
    driver.set_script_timeout(timeout)
    r = driver.execute_async_script(
        """
        const [url, fim] = arguments;
        fetch(url, {credentials: 'include'}).then(async r => {
            const bytes = new Uint8Array(await r.arrayBuffer());
            let bin = '';
            for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
            fim({status: r.status, tipo: r.headers.get('content-type') || '', dados: btoa(bin)});
        }).catch(e => fim({erro: String(e)}));
        """,
        href,
    )
    if r.get("erro") or r["status"] != 200:
        raise ComprovanteErro(f"não consegui baixar o comprovante ({r.get('erro') or r['status']})")
    dados = base64.b64decode(r["dados"])
    if not dados.startswith(b"%PDF"):
        raise ComprovanteErro(f"o link do comprovante não devolveu um PDF ({r['tipo'] or 'tipo desconhecido'})")
    texto = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(dados)).pages)
    if not texto.strip():
        raise ComprovanteErro("PDF sem texto (escaneado?): conferir manualmente")
    return unicodedata.normalize("NFC", texto)


def extrair(texto):
    """{chave: valor} dos três dados. Cada um tem que aparecer com um único valor no PDF."""
    valores, problemas = {}, []
    for d in DADOS:
        achados = {" ".join(m.group(1).split()) for m in re.finditer(d.regex, texto, re.IGNORECASE)}
        achados.discard("")
        if len(achados) == 1:
            valores[d.chave] = achados.pop()
        elif not achados:
            problemas.append(f"{d.rotulo}: não encontrado no PDF")
        else:
            problemas.append(f"{d.rotulo}: mais de um valor no PDF ({'; '.join(sorted(achados))})")
    if problemas:
        raise ComprovanteErro(", ".join(problemas))
    return valores
