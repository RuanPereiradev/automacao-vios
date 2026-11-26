import hashlib
import json
import os
from pathlib import Path

from nucleo.ia import IAErro


class FilaIA:
    """IA "em duas etapas" (LLM_PROVEDOR=fila ou ./rodar.sh --fila): para quando a análise é escrita fora do
    Jarvis (ex.: pelo Claude numa conversa), sem chave de API.

    1ª rodada: cada pergunta vira um arquivo em <SAIDA_PASTA>/ia_fila/pedidos/ e a célula sai como "aguardando a
    análise". As respostas (o mesmo JSON do schema) são escritas em ia_fila/respostas.json, ou em vários
    ia_fila/respostas/*.json, como {chave: resposta}. 2ª rodada: o Jarvis lê o VIOS de novo e usa as respostas.

    A chave é estável entre as rodadas: as instruções (hash curto) + a 1ª linha do texto ("Processo: <nº>",
    "CI: <nº>" ou "Grupo: <nome>"), para uma tarefa nova no VIOS entre as rodadas não invalidar a resposta.
    Os arquivos têm dados de processos: ficam na pasta de saída, fora do git.
    """

    suporta_lote = False

    def __init__(self, modelo="fila", esforco=""):
        base = os.getenv("IA_FILA_PASTA", "").strip() or str(Path(os.getenv("SAIDA_PASTA", "saida").strip() or "saida")
                                                             / "ia_fila")
        self.pasta = Path(base)
        (self.pasta / "pedidos").mkdir(parents=True, exist_ok=True)
        (self.pasta / "sistemas").mkdir(parents=True, exist_ok=True)
        self.modelo = modelo
        self._cache, self._marca = {}, None

    @staticmethod
    def chave(sistema, usuario):
        s = hashlib.sha256(sistema.encode("utf-8")).hexdigest()[:8]
        linhas = usuario.strip().splitlines() or [""]
        primeira = linhas[0].strip()[:120]
        if primeira.startswith("Processo:"):
            # o número pode faltar ou se repetir no VIOS: as linhas do cadastro (cliente, polo, partes)
            # separam um processo do outro e não mudam entre as rodadas
            cadastro = []
            for l in linhas[1:]:
                if l.strip().startswith("TAREFAS"):
                    break
                if l.strip():
                    cadastro.append(l.strip())
            resto = "\n".join(cadastro[:4])
            primeira += " #" + hashlib.sha256(resto.encode("utf-8")).hexdigest()[:8]
        return f"{s}|{primeira}"

    def _respostas(self):
        arquivos = [self.pasta / "respostas.json"] + sorted((self.pasta / "respostas").glob("*.json"))
        marca = tuple((str(a), a.stat().st_mtime) for a in arquivos if a.exists())
        if marca != self._marca:
            tudo = {}
            for a, _ in marca:
                try:
                    tudo.update(json.loads(Path(a).read_text(encoding="utf-8")))
                except ValueError as e:
                    raise IAErro(f"arquivo de respostas com JSON inválido: {a} ({e})")
            self._cache, self._marca = tudo, marca
        return self._cache

    def responder(self, sistema, usuario, schema, pesquisar=False):
        k = self.chave(sistema, usuario)
        r = self._respostas().get(k)
        if r is not None:
            faltam = [c for c in schema.get("required", []) if c not in r]
            if faltam:
                raise IAErro(f"resposta da fila sem os campos {faltam} ({k})")
            dados = dict(r)
            dados["_uso"] = {}
            return dados
        s = k.split("|", 1)[0]
        sist = self.pasta / "sistemas" / f"{s}.txt"
        if not sist.exists():
            sist.write_text(sistema, encoding="utf-8")
        nome = hashlib.sha256(k.encode("utf-8")).hexdigest()[:16]
        (self.pasta / "pedidos" / f"{nome}.json").write_text(
            json.dumps({"chave": k, "sistema": s, "schema": schema, "usuario": usuario}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        raise IAErro("pendente na fila da IA: a análise ainda não foi escrita (rodar de novo depois das respostas)")
