"""Gera os sons da Vila 06 (voz das falas, música de fundo, ambiente e efeitos) na ElevenLabs.

Os arquivos vão para <pasta>/sons/ (a mesma pasta VILA06_CLIPES dos vídeos, fora do git). Só usa a biblioteca
padrão. A chave vem da variável de ambiente ELEVENLABS_API_KEY (nunca do repositório).

    ELEVENLABS_API_KEY=... python3 doc/vila/gerar_sons_vila06.py <pasta> [--so falas|musica|efeitos] [--refazer] [--aplicar]

Sem --aplicar só mostra o que seria gerado e o custo aproximado.

Falas: uma por frase de FALAS em bot/vila/muralha.html, com o nome fala-<hash do texto>.mp3 (FNV-1a de 32 bits,
o mesmo cálculo da página). Mudou o texto = o nome muda e a página fica muda naquela frase até gerar de novo:
nunca toca uma versão velha. A voz é de banco de vozes, sem imitar ninguém.
Música e efeitos: originais, feitos a partir de descrição (sem trilha de anime nem som copiado).
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PAGINA = RAIZ / "bot" / "vila" / "muralha.html"
API = "https://api.elevenlabs.io/v1"

VOZ = "MZxV5lN3cv7hi1376O0m"  # Ana Dias (biblioteca, jovem, brasileira): firme e contida
MODELO_VOZ = "eleven_v4"

# nome: (descrição, segundos, repetir em loop)
EFEITOS = {
    "gancho": ("Grappling hook launcher firing: sharp pneumatic pop, steel wire cable whizzing out fast, "
               "metal hook thudding into a target. No music.", 1.4, False),
    "gas": ("Short burst of pressurized gas from a compact jet thruster, hissing whoosh. No music.", 1.0, False),
    "corte": ("Two very fast steel sword slashes cutting through thick flesh: sharp metallic swish then a heavy "
              "slice. No music.", 1.1, False),
    "esquiva": ("Fast acrobatic dodge: body flipping through the air, cloth flapping, quick whoosh. No music.", 0.8, False),
    "pouso": ("Agile person landing on a large soft surface, boots thud, gear rattling briefly. No music.", 0.9, False),
    "vapor": ("Thick hot steam escaping with a long hiss, fading out. No music.", 2.2, False),
    "passo": ("Giant creature footstep far away: deep heavy ground-shaking thud with low rumble. No music.", 1.6, False),
    "canhao": ("Old black-powder cannon firing from a stone fortress wall, booming blast with short echo. No music.",
               2.0, False),
    "sino": ("Alarm bell on a stone watchtower struck twice, metallic clang with echo. No music.", 1.8, False),
    "ambiente": ("Seamless ambience on top of a very tall stone city wall: steady wind, distant birds, faint town "
                 "murmur far below. No music, no voices.", 20.0, True),
}

MUSICA = ("Original instrumental background loop for a calm watch on a tall stone wall of a fortified medieval town "
          "in a dry hilly backcountry. Slow and steady, low strings and cello ostinato, soft distant war drums, "
          "subtle horn, airy wordless choir pad far back, tense but patient mood, cinematic. Instrumental only, "
          "no vocals, no lyrics. Ends the way it begins so it can loop.")
MUSICA_MS = 90_000


def fnv1a(texto):
    h = 0x811C9DC5
    for b in texto.encode("utf-8"):
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def falas():
    """Frases de FALAS na página (lista de textos, sem repetir)."""
    js = PAGINA.read_text(encoding="utf-8")
    bloco = js[js.index("const FALAS = {"):]
    bloco = bloco[:bloco.index("\n};")]
    vistos = []
    for t in re.findall(r"'((?:[^'\\]|\\.)*)'", bloco):
        t = t.replace("\\'", "'")
        if t and t not in vistos:
            vistos.append(t)
    return vistos


def pedir(caminho, corpo, chave):
    req = urllib.request.Request(API + caminho, data=json.dumps(corpo).encode(), method="POST",
                                 headers={"xi-api-key": chave, "content-type": "application/json", "accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs recusou {caminho}: {e.code} {e.read()[:300].decode('utf-8', 'replace')}")


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("--"):
        sys.exit(__doc__)
    sons = Path(args[0]).expanduser() / "sons"
    so = args[args.index("--so") + 1] if "--so" in args else None
    refazer, aplicar = "--refazer" in args, "--aplicar" in args
    tarefas = []  # (arquivo, custo aproximado, função que gera)
    if so in (None, "falas"):
        for t in falas():
            corpo = {"text": t, "model_id": MODELO_VOZ, "language_code": "pt"}
            tarefas.append((f"fala-{fnv1a(t)}.mp3", len(t),
                            lambda c, corpo=corpo: pedir(f"/text-to-speech/{VOZ}?output_format=mp3_44100_128", corpo, c)))
    if so in (None, "efeitos"):
        for nome, (desc, seg, loop) in EFEITOS.items():
            corpo = {"text": desc, "duration_seconds": seg, "prompt_influence": 0.5, "loop": loop,
                     "model_id": "eleven_text_to_sound_v2"}
            tarefas.append((f"{'' if nome == 'ambiente' else 'sfx-'}{nome}.mp3", int(seg * 40),
                            lambda c, corpo=corpo: pedir("/sound-generation?output_format=mp3_44100_128", corpo, c)))
    if so in (None, "musica"):
        corpo = {"prompt": MUSICA, "music_length_ms": MUSICA_MS, "model_id": "music_v1", "force_instrumental": True}
        tarefas.append(("musica.mp3", None, lambda c: pedir("/music?output_format=mp3_44100_128", corpo, c)))

    pendentes = [t for t in tarefas if refazer or not (sons / t[0]).is_file()]
    custo = sum(t[1] or 0 for t in pendentes)
    print(f"{len(pendentes)} arquivo(s) para gerar em {sons}: {', '.join(t[0] for t in pendentes) or 'nenhum'}")
    print(f"Custo aproximado (sem a música): {custo} créditos.")
    if not aplicar or not pendentes:
        return
    import os
    chave = os.environ.get("ELEVENLABS_API_KEY", "").strip() or sys.exit("Falta ELEVENLABS_API_KEY no ambiente.")
    sons.mkdir(parents=True, exist_ok=True)
    for arquivo, _, gerar in pendentes:
        (sons / arquivo).write_bytes(gerar(chave))
        print("ok", arquivo)


if __name__ == "__main__":
    main()
