"""Confere a sintaxe do JS de um vila.html (a página toda é uma string JSON numa linha só).

Extrai a string JSON da linha que começa com '"<!DOCTYPE html>', pega todo <script> sem src
(inclusive o type="text/x-dc" do componente), grava cada um num arquivo .js temporário e roda
`node --check` em cada um. Imprime OK (ou o erro) e sai com código != 0 se algo falhar.

uso: python3 checar.py caminho/do/vila.html
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        sys.exit("uso: python3 checar.py caminho/do/vila.html")
    caminho = Path(sys.argv[1])
    linhas = caminho.read_text(encoding="utf-8").split("\n")
    idx = next((i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>')), None)
    if idx is None:
        print("ERRO: não achei a linha que começa com '\"<!DOCTYPE html>'")
        sys.exit(2)
    try:
        html = json.loads(linhas[idx])
    except json.JSONDecodeError as e:
        print("ERRO: a linha do HTML não é uma string JSON válida:", e)
        sys.exit(2)
    blocos = []
    for m in re.finditer(r"<script\b([^>]*)>(.*?)</script>", html, re.S | re.I):
        attrs, corpo = m.group(1), m.group(2)
        if re.search(r"\bsrc\s*=", attrs, re.I) or not corpo.strip():
            continue
        linha0 = html.count("\n", 0, m.start(2)) + 1
        blocos.append((linha0, corpo))
    if not blocos:
        print("ERRO: nenhum <script> inline encontrado")
        sys.exit(2)
    falhas = 0
    with tempfile.TemporaryDirectory() as d:
        for n, (linha0, corpo) in enumerate(blocos):
            js = Path(d) / f"script{n}.js"
            js.write_text(corpo, encoding="utf-8")
            r = subprocess.run(["node", "--check", str(js)], capture_output=True, text=True)
            if r.returncode != 0:
                falhas += 1
                print(f"ERRO no script {n} (começa na linha {linha0} do HTML; some {linha0 - 1} à linha do erro):")
                print((r.stderr or r.stdout).strip())
    if falhas:
        sys.exit(1)
    print(f"OK ({len(blocos)} script(s) inline, node --check sem erro)")


if __name__ == "__main__":
    main()
