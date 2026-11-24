"""Vila 07 (Abismo) dentro da Vila dos Bots (/vila e a página inicial /).

A cena é bot/vila/abismo.html (servida em /vila/abismo): três heróis em pixel art (Mago, Arqueiro, Bárbaro) contra o
Troll Ancião, um laço de 9 s por classe. Não lê nenhum bot: só anima. Igual à Vila 06, uma camada cobre o palco quando a
aba "07 · Abismo" está escolhida.

- O mapa continua com 5 lotes (Component.NV = 5): as abas 06 e 07 são só camadas. Por isso goVillage e a seta
  "próxima" passam a aceitar o índice 6 (NV + 1), sem mudar o NV.
- ?vila=6 e ?vila=7 passam a abrir direto a Mikasa e o Abismo (antes o endereço parava na Vila 05).
- Valor: "abismo" = (vila escolhida é a 07); o status do topo diz "Abismo".

uso: python3 doc/vila/ligar_vila07_abismo.py bot/vila/vila.html   (rodar de novo não repete nada)
"""
import json
import sys

caminho = sys.argv[1]
linhas = open(caminho, encoding="utf-8").read().split("\n")
IDX = next(i for i, l in enumerate(linhas) if l.startswith('"<!DOCTYPE html>'))
t = json.loads(linhas[IDX])
if "<!--V7:ABISMO-->" in t:
    sys.exit("a Vila 07 já está ligada")
if "<!--V6:MURALHA-->" not in t:
    sys.exit("rode antes o doc/vila/ligar_vila06_muralha.py")


def troca(velho, novo):
    global t
    assert t.count(velho) == 1, ("trecho não encontrado (ou repetido)", velho[:90])
    t = t.replace(velho, novo)


CAMADA = """<!--V7:ABISMO-->
    <sc-if value="{{ abismo }}" hint-placeholder-val="{{ false }}">
      <div style="position:absolute;inset:0;z-index:1;background:#07060b;display:flex;flex-direction:column;justify-content:flex-end;">
        <div style="flex:1;display:flex;align-items:center;justify-content:center;padding-top:5cqw;font-family:var(--font-heading);font-size:clamp(11px,1.6cqw,20px);letter-spacing:.14em;text-transform:uppercase;color:#f0c46a;">Abismo · três heróis contra o Troll Ancião</div>
        <iframe src="/vila/abismo" title="Abismo: Mago, Arqueiro e Bárbaro contra o Troll Ancião" style="display:block;width:100%;aspect-ratio:16/9;border:0;flex:none;"></iframe>
      </div>
    </sc-if>
  </div>
</div>
</x-dc>"""
troca("  </div>\n</div>\n</x-dc>", CAMADA)
troca("const vNames = ['01 · Sam', '02 · Bumblebee', '03 · Albi', '04 · Jarvis', '05 · Orelha', '06 · Mikasa'];",
      "const vNames = ['01 · Sam', '02 · Bumblebee', '03 · Albi', '04 · Jarvis', '05 · Orelha', '06 · Mikasa', '07 · Abismo'];")
# as abas 06 e 07 são só camadas (sem lote no canvas): aceita os índices NV e NV + 1 sem mudar o NV
troca("goVillage(v) { if (v >= 0 && v <= Component.NV) this.setState({ village: v }); }",
      "goVillage(v) { if (v >= 0 && v <= Component.NV + 1) this.setState({ village: v }); }")
troca("nextOpacity: vi < NV ? 1 : 0.35,", "nextOpacity: vi < NV + 1 ? 1 : 0.35,")
troca("village: Math.max(0, Math.min(Component.NV - 1, (parseInt(new URLSearchParams(location.search).get('vila'), 10) || 1) - 1)),",
      "village: Math.max(0, Math.min(Component.NV + 1, (parseInt(new URLSearchParams(location.search).get('vila'), 10) || 1) - 1)),")
troca("      hudStatus: vi === 5 ? 'Mikasa' : ",
      "      hudStatus: vi === 6 ? 'Abismo' : vi === 5 ? 'Mikasa' : ")
troca("      muralha: vi === 5, // ligar_vila06_muralha.py: a muralha do bot do Previdenciário (Vila 06)",
      "      muralha: vi === 5, // ligar_vila06_muralha.py: a muralha do bot do Previdenciário (Vila 06)\n"
      "      abismo: vi === 6, // ligar_vila07_abismo.py: os três heróis contra o Troll Ancião (Vila 07)")

linhas[IDX] = json.dumps(t, ensure_ascii=False).replace("</", "<\\u002F")  # "</" dentro de <script> fecharia a tag
open(caminho, "w", encoding="utf-8").write("\n".join(linhas))
print("Vila 07: Abismo ligada")
