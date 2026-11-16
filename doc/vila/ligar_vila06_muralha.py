"""Vila 06 (bot do Previdenciário) dentro da Vila dos Bots (/vila e a página inicial /).

A cena é bot/vila/muralha.html (servida em /vila/previdenciario, ligada ao estado do bot por
/vila/previdenciario/estado; os vídeos ficam fora do git, na pasta VILA06_CLIPES). Igual à Fortaleza da
Vila 01, uma camada cobre o palco quando a aba "06 · Mikasa" está escolhida.

- A Vila 06 não tem lote no canvas (o mapa continua com 5 lotes, Component.NV = 5): a aba 06 é só a camada.
  Por isso goVillage e a seta "próxima" passam a aceitar o índice 5 (NV), sem mudar o NV.
- Marcação: camada no fim do palco, com a cena em 16:9 encostada embaixo; a barra do topo já tem z-index
  (ligar_vila01_fortaleza.py, rodar antes deste).
- Valor: "muralha" = (vila escolhida é a 06); o status do topo diz "Mikasa".

uso: python3 doc/vila/ligar_vila06_muralha.py bot/vila/vila.html   (rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "<!--V6:MURALHA-->" in t:
    sys.exit("a Vila 06 já está ligada")
if "<!--V1:FORTALEZA-->" not in t:
    sys.exit("rode antes o doc/vila/ligar_vila01_fortaleza.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


CAMADA = """<!--V6:MURALHA-->
    <sc-if value="{{ muralha }}" hint-placeholder-val="{{ false }}">
      <div style="position:absolute;inset:0;z-index:1;background:#0b0a09;display:flex;flex-direction:column;justify-content:flex-end;">
        <div style="flex:1;display:flex;align-items:center;justify-content:center;padding-top:5cqw;font-family:var(--font-heading);font-size:clamp(11px,1.6cqw,20px);letter-spacing:.14em;text-transform:uppercase;color:#f0c46a;">Muralha · a vila da Mikasa</div>
        <iframe src="/vila/previdenciario" title="Muralha: a Mikasa em ação" style="display:block;width:100%;aspect-ratio:16/9;border:0;flex:none;"></iframe>
      </div>
    </sc-if>
  </div>
</div>
</x-dc>"""
troca("  </div>\n</div>\n</x-dc>", CAMADA)
troca("const vNames = ['01 · Sam', '02 · Bumblebee', '03 · Albi', '04 · Jarvis', '05 · Orelha'];",
      "const vNames = ['01 · Sam', '02 · Bumblebee', '03 · Albi', '04 · Jarvis', '05 · Orelha', '06 · Mikasa'];")
# a aba 06 é só camada (sem lote no canvas): aceita o índice NV sem mudar o NV
troca("goVillage(v) { if (v >= 0 && v < Component.NV) this.setState({ village: v }); }",
      "goVillage(v) { if (v >= 0 && v <= Component.NV) this.setState({ village: v }); }")
troca("nextOpacity: vi < NV - 1 ? 1 : 0.35,", "nextOpacity: vi < NV ? 1 : 0.35,")
troca("      hudStatus: vi === 0 ? 'Sam · ' + s.status : 'Vila 0' + (vi + 1) + ' · sem bot',",
      "      hudStatus: vi === 5 ? 'Mikasa' : vi === 0 ? 'Sam · ' + s.status : 'Vila 0' + (vi + 1) + ' · sem bot',")
troca("      fortaleza: vi === 0, // ligar_vila01_fortaleza.py: a Fortaleza do Dragão por cima da Vila 01",
      "      fortaleza: vi === 0, // ligar_vila01_fortaleza.py: a Fortaleza do Dragão por cima da Vila 01\n"
      "      muralha: vi === 5, // ligar_vila06_muralha.py: a muralha do bot do Previdenciário (Vila 06)")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")  # "</" dentro de <script> fecharia a tag
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 06: muralha do Previdenciário ligada")
