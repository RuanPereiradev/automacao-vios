"""Vila 01 (Sam) vira a Fortaleza do Dragão dentro da Vila dos Bots (/vila e a página inicial /).

A vila do Sam agora é a cena bot/vila/fortaleza.html (servida em /vila/sam, ligada aos eventos do
Sam). Este patch põe essa cena por cima da Vila 01 antiga quando a aba "01 · Sam" está escolhida:
a barra do topo (Órbita, status e as abas 01 a 05) continua visível e funcionando; nas outras abas
nada muda. O mapa antigo da Vila 01 continua no arquivo (embaixo), só não aparece.

- Marcação: uma camada no fim do palco cobrindo a cena antiga (o diálogo e os botões da Vila 01 ficam
  escondidos atrás dela), com a fortaleza em 16:9 encostada embaixo; a barra do topo ganha z-index
  para ficar por cima.
- Valor: "fortaleza" = (vila escolhida é a 01), no objeto que o renderVals monta para a Vila 01.

uso: python3 doc/vila/ligar_vila01_fortaleza.py bot/vila/vila.html   (rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "<!--V1:FORTALEZA-->" in t:
    sys.exit("a Fortaleza já está na Vila 01")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


CAMADA = """<!--V1:FORTALEZA-->
    <sc-if value="{{ fortaleza }}" hint-placeholder-val="{{ false }}">
      <div style="position:absolute;inset:0;z-index:1;background:#0b0a09;display:flex;flex-direction:column;justify-content:flex-end;">
        <div style="flex:1;display:flex;align-items:center;justify-content:center;padding-top:5cqw;font-family:var(--font-heading);font-size:clamp(11px,1.6cqw,20px);letter-spacing:.14em;text-transform:uppercase;color:#f0c46a;">Fortaleza do Dragão · a vila do Sam</div>
        <iframe src="/vila/sam" title="Fortaleza do Dragão: o Sam em ação" style="display:block;width:100%;aspect-ratio:16/9;border:0;flex:none;"></iframe>
      </div>
    </sc-if>
  </div>
</div>
</x-dc>"""
troca("  </div>\n</div>\n</x-dc>", CAMADA)
# a barra do topo (Órbita, status, abas) fica por cima da camada
troca('<div style="position:absolute;top:1.3%;left:1.4%;right:1.4%;display:flex;justify-content:space-between;',
      '<div style="position:absolute;top:1.3%;left:1.4%;right:1.4%;z-index:2;display:flex;justify-content:space-between;')
troca("      hudStatus: vi === 0 ? 'Sam · ' + s.status : 'Vila 0' + (vi + 1) + ' · sem bot',",
      "      hudStatus: vi === 0 ? 'Sam · ' + s.status : 'Vila 0' + (vi + 1) + ' · sem bot',\n"
      "      fortaleza: vi === 0, // ligar_vila01_fortaleza.py: a Fortaleza do Dragão por cima da Vila 01")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")  # "</" dentro de <script> fecharia a tag
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 01: Fortaleza do Dragão ligada")
