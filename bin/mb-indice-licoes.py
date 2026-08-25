#!/usr/bin/env python3
"""
mb-indice-licoes.py — memória em escala (v6, fase 3).

Em vez de injetar os últimos 5 KB do arquivo de lições (4-5 lições de 100+),
indexa TODAS as entradas com embeddings locais (Ollama + nomic-embed-text) e
devolve as N mais próximas de um texto de consulta. Sem Ollama, cai num
ranking por palavra-chave — pior, mas nunca vazio.

Uso:
    python bin/mb-indice-licoes.py --indexar [--force]
    python bin/mb-indice-licoes.py --buscar "texto do prompt" [--n 5]
    python bin/mb-indice-licoes.py --recontar

Artefatos (em dna/, local):
    indice-licoes.json      hash da fonte + vetores por entrada
    licoes-recorrencia.json clusters de gatilhos parecidos; 3+ = candidata a
                            regra (a régua "3× vira processo" ganha executor)

Também é importado como módulo pelo mb-contexto.py (função buscar()).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import unicodedata
import urllib.request
from pathlib import Path

import mb_utils as u
import mb_trava as trava

u.utf8_console()

OLLAMA_URL = os.environ.get("MEGABRAIN_OLLAMA", "http://localhost:11434")
MODELO_EMBED = os.environ.get("MEGABRAIN_MODELO_EMBED", "nomic-embed-text")
LIMIAR_RECORRENCIA = 0.82   # cosseno acima disso = mesmo gatilho reencarnado
RE_ENTRADA = re.compile(r"^## ", re.MULTILINE)

STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos",
    "nas", "um", "uma", "que", "com", "por", "para", "pra", "se", "ao", "os",
    "as", "ou", "sem", "mais", "menos", "ja", "nao", "num", "numa", "ate",
    "the", "of", "to", "in", "and", "is", "on", "for",
}


def central() -> Path:
    env = os.environ.get("MEGABRAIN_CENTRAL")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def fonte_default() -> Path:
    return u.achar(central(), "licoes-megabrain.md")


def caminho_indice() -> Path:
    return u.pasta(central(), "dna") / "indice-licoes.json"


def dividir_entradas(texto: str) -> list[dict]:
    """Divide o arquivo em entradas {chave, titulo, gatilho, texto}."""
    posicoes = [m.start() for m in RE_ENTRADA.finditer(texto)]
    entradas = []
    for i, inicio in enumerate(posicoes):
        fim = posicoes[i + 1] if i + 1 < len(posicoes) else len(texto)
        bloco = texto[inicio:fim].strip()
        linhas = bloco.splitlines()
        titulo = linhas[0].lstrip("# ").strip() if linhas else ""
        # Aposentadas (fase 4) ficam no arquivo pela história, fora do índice.
        if titulo.startswith("~~") or "\nAPOSENTADA" in bloco[:400]:
            continue
        gatilho = ""
        m = re.search(r"^GATILHO:\s*(.+?)(?=^\w+:|\Z)", bloco,
                      re.MULTILINE | re.DOTALL)
        if m:
            gatilho = " ".join(m.group(1).split())
        entradas.append({
            "chave": " ".join(titulo.lower().split()),
            "titulo": titulo,
            "gatilho": gatilho,
            "texto": bloco,
        })
    return entradas


# ---------------------------------------------------------------------------
# Embeddings via Ollama (fail-open)
# ---------------------------------------------------------------------------

def embed(textos: list[str], timeout: float = 30.0) -> list[list[float]] | None:
    """Embeda uma lista de textos. None se o Ollama estiver fora."""
    if not textos:
        return []
    corpo = json.dumps({"model": MODELO_EMBED, "input": textos}).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embed", data=corpo,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        vetores = dados.get("embeddings")
        if isinstance(vetores, list) and len(vetores) == len(textos):
            return vetores
        return None
    except Exception:
        return None


def cosseno(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Fallback por palavra-chave
# ---------------------------------------------------------------------------

def tokens(texto: str) -> set[str]:
    norm = unicodedata.normalize("NFKD", texto.lower())
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch))
    return {t for t in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", norm)
            if t not in STOPWORDS}


def score_keyword(consulta: set[str], entrada: dict) -> float:
    if not consulta:
        return 0.0
    t_tit = tokens(entrada["titulo"])
    t_gat = tokens(entrada["gatilho"])
    t_txt = tokens(entrada["texto"])
    s = (2.0 * len(consulta & t_gat)
         + 2.0 * len(consulta & t_tit)
         + 1.0 * len(consulta & t_txt))
    return s / (1 + len(consulta))


# ---------------------------------------------------------------------------
# Índice
# ---------------------------------------------------------------------------

def hash_fonte(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def carregar_indice() -> dict | None:
    texto = u.safe_read_text(caminho_indice())
    if not texto:
        return None
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, ValueError):
        return None


def indexar(force: bool = False, silencioso: bool = False) -> dict | None:
    """Gera/atualiza o índice. Retorna o índice, ou None se a fonte sumiu."""
    texto = u.safe_read_text(fonte_default())
    if texto is None:
        if not silencioso:
            print(f"ERRO: fonte não encontrada: {fonte_default()}")
        return None
    h = hash_fonte(texto)
    atual = carregar_indice()
    if atual and atual.get("hash_fonte") == h and atual.get("modelo") == MODELO_EMBED and not force:
        if not silencioso:
            print(f"índice em dia ({len(atual.get('entradas', []))} entradas, hash {h})")
        return atual

    entradas = dividir_entradas(texto)
    corpus = [f"{e['titulo']}\n{e['gatilho']}\n{e['texto'][:600]}" for e in entradas]
    vetores = embed(corpus)
    com_embedding = vetores is not None
    for i, e in enumerate(entradas):
        e["vetor"] = vetores[i] if com_embedding else None

    indice = {
        "hash_fonte": h,
        "modelo": MODELO_EMBED if com_embedding else None,
        "com_embedding": com_embedding,
        "entradas": entradas,
    }
    trava.escrever(
        caminho_indice(), json.dumps(indice, ensure_ascii=False),
        agente=trava.agente_script("mb-indice-licoes"),
        motivo="regenera índice de lições",
    )
    if not silencioso:
        modo = "embeddings" if com_embedding else "SEM embeddings (Ollama fora) — fallback keyword"
        print(f"indexadas {len(entradas)} entradas ({modo}, hash {h})")
    return indice


def buscar(consulta: str, n: int = 5) -> list[dict]:
    """Top-N entradas pro texto. Reindexação automática se a fonte mudou.
    Nunca levanta exceção — no pior caso retorna []."""
    try:
        indice = indexar(silencioso=True)
        if not indice:
            return []
        entradas = indice.get("entradas", [])
        if not entradas:
            return []
        v_consulta = None
        if indice.get("com_embedding"):
            vs = embed([consulta], timeout=10.0)
            v_consulta = vs[0] if vs else None
        if v_consulta is not None:
            pontuadas = [(cosseno(v_consulta, e["vetor"]), e)
                         for e in entradas if e.get("vetor")]
        else:
            toks = tokens(consulta)
            pontuadas = [(score_keyword(toks, e), e) for e in entradas]
        pontuadas.sort(key=lambda x: -x[0])
        return [dict(e, score=round(s, 3)) for s, e in pontuadas[:n] if s > 0]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Recorrência — a régua "3× vira processo" ganha executor
# ---------------------------------------------------------------------------

def recontar() -> dict:
    indice = indexar(silencioso=True) or {"entradas": []}
    entradas = indice.get("entradas", [])
    n = len(entradas)
    usado = [False] * n
    clusters = []
    for i in range(n):
        if usado[i]:
            continue
        grupo = [i]
        usado[i] = True
        for j in range(i + 1, n):
            if usado[j]:
                continue
            if indice.get("com_embedding") and entradas[i].get("vetor") and entradas[j].get("vetor"):
                parecido = cosseno(entradas[i]["vetor"], entradas[j]["vetor"]) >= LIMIAR_RECORRENCIA
            else:
                a = tokens(entradas[i]["gatilho"] or entradas[i]["titulo"])
                b = tokens(entradas[j]["gatilho"] or entradas[j]["titulo"])
                uni = a | b
                parecido = bool(uni) and len(a & b) / len(uni) >= 0.5
            if parecido:
                grupo.append(j)
                usado[j] = True
        if len(grupo) >= 2:
            clusters.append({
                "n": len(grupo),
                "candidata_a_regra": len(grupo) >= 3,
                "titulos": [entradas[k]["titulo"] for k in grupo],
            })
    clusters.sort(key=lambda c: -c["n"])
    resultado = {"total_entradas": n, "clusters": clusters}
    trava.escrever(
        u.pasta(central(), "dna") / "licoes-recorrencia.json",
        json.dumps(resultado, ensure_ascii=False, indent=2),
        agente=trava.agente_script("mb-indice-licoes"),
        motivo="regenera recorrência das lições",
    )
    return resultado


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--indexar", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--buscar", default=None)
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--recontar", action="store_true")
    args = p.parse_args()

    if args.indexar:
        return 0 if indexar(force=args.force) else 1

    if args.buscar is not None:
        achadas = buscar(args.buscar, args.n)
        if not achadas:
            print("(nenhuma lição relevante)")
            return 0
        for e in achadas:
            print(f"[{e['score']}] {e['titulo']}")
        return 0

    if args.recontar:
        r = recontar()
        candidatas = [c for c in r["clusters"] if c["candidata_a_regra"]]
        print(f"{r['total_entradas']} entradas · {len(r['clusters'])} cluster(s) recorrente(s) · "
              f"{len(candidatas)} candidata(s) a regra (3×+)")
        for c in candidatas:
            print(f"  {c['n']}× — " + " | ".join(c["titulos"][:3]))
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
