#!/usr/bin/env python3
"""mb-compreensor.py - compreensores de padroes (spec §7, v1 260824).

O QUE E: um job que CRUZA as pastas da central e aponta o que ja se repete e
ainda nao virou modelo. Nao e estatistica - com ~100 eventos de telemetria
qualquer grafico aqui seria enfeite. E cruzamento: tema que aparece em dois
tipos de lugar diferentes (pendencia + cerebro, doc + visuais, ...) e nao tem
modelo correspondente em motor/modelos/ vira PROPOSTA DE MODELO, com o
caminho de cada evidencia.

V1 = um compreensor so: TEMPLATIZAR. Os outros tres (parado, orfao, ritmo)
ficaram de fora por decisao dele em 260824 - escopo estreito, feito direito.

REGRAS DA CASA
- Caminho de maquina SEMPRE por u.pasta()/u.achar(). Nunca raiz / "modelos".
- Data e SEMPRE o relogio da central (mb_telemetria.agora()).
- PRIVACIDADE: o texto de prompt do .mb-log NAO e indexado. Do log entram so
  campos estruturados (skill, projeto, etapa, evento). O relatorio nunca cita
  conteudo de prompt.
- Nao inventa insight. Cada achado carrega evidencia com caminho e data; a
  leitura do "por que" e mecanica, nao opinativa.

USO
  python bin/mb-compreensor.py              # roda e grava relatorio + json
  python bin/mb-compreensor.py --seco       # so mostra, nao grava
  python bin/mb-compreensor.py --json       # despeja o json na tela
  python bin/mb-compreensor.py --min-tipos 3
"""
from __future__ import annotations

import argparse
import json
import datetime as dt
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mb_utils as u          # noqa: E402
import mb_telemetria as tel   # noqa: E402

VERSAO = "1.0"
TOPO = 12

# Palavras de ESTRUTURA (as que so dizem "isto e um arquivo da central").
# Palavra de TEMA - figma, obsidian, portfolio, painel - fica de fora daqui
# de proposito: e exatamente o que o compreensor precisa enxergar.
STOP = {
    "para", "pelo", "pela", "pelos", "pelas", "como", "mais", "menos", "esse",
    "essa", "esses", "essas", "este", "esta", "isso", "isto", "aquele", "aquela",
    "quando", "onde", "porque", "entao", "sobre", "entre", "cada", "todo", "toda",
    "todos", "todas", "outro", "outra", "ainda", "depois", "antes", "agora",
    "fazer", "feito", "feita", "ficar", "deve", "pode", "vale", "tudo", "nada",
    "sera", "seja", "tem", "nao", "sim", "com", "sem", "dos", "das", "uma", "uns",
    "que", "por", "mas",
    # estrutura da propria central
    "megabrain", "mega", "brain", "projeto", "projetos", "arquivo", "arquivos",
    "pasta", "pastas", "nome", "nomes", "novo", "nova", "atual", "antigo", "velho",
    "leiame", "indice", "readme", "memoria", "central", "sessao", "sessoes",
    "item", "itens", "versao", "script", "scripts", "python", "docs", "html",
    "wiki", "raiz", "tests", "teste", "testes", "main", "motor", "nucleo",
    "estado", "geral", "modelo", "modelos", "pagina", "paginas", "card", "cards",
    "etapa", "etapas", "linha", "linhas", "texto", "dados", "base", "parte",
    # nome de agente nao e tema: aparece em tudo por construcao
    "claude", "kimi", "codex", "agente", "agentes", "cowork", "opus", "sonnet",
    "entrada", "saida", "dependencias", "sugeridas", "sugerida", "lista",
}

# Tipo que PRODUZ artefato (o que se templatiza) x tipo que so CORROBORA.
# DECISOES.md e PROGRESSO.json sao prosa: palavra comum aparece em 20
# cabecalhos e fingiria padrao. Eles somam forca, nao qualificam sozinhos.
TIPOS_ARTEFATO = {"pendencia", "cerebro", "fonte", "doc", "visual", "entrada"}
TIPOS_APOIO = {"estado", "evento"}
TETO_UBIQUIDADE = 12   # tema em mais lugares que isso e vocabulario, nao padrao
TETO_TERMOS = 40       # item que rende mais que isso e lexico (lista), nao tema
# Voce templatiza o que FAZ e GUARDA. Tema que so aparece em doc + fonte bruta
# e assunto que voce LEU - nao rende modelo. Exige ao menos um lugar forte.
TIPOS_FORTE = {"pendencia", "cerebro", "visual"}

# tipo logico -> (nome logico da pasta em mb_utils, ou caminho direto tentado)
FONTES_PASTA = [
    ("pendencia", "alteracoes-pendentes"),
    ("cerebro", "cerebro"),
    ("doc", "docs"),
]
# pastas de humano que nao estao no mapa logico: tenta os nomes conhecidos
FONTES_DIRETAS = [
    ("visual", ("04_visuais", "visuais")),
    ("entrada", ("02_entrada", "entrada")),
]
EXT_TEXTO = {".md", ".txt", ".html", ".htm"}


# ---------------------------------------------------------------------------
# tokenizacao
# ---------------------------------------------------------------------------
def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")


def tokens(texto: str) -> list[str]:
    t = _sem_acento(str(texto).lower())
    t = re.sub(r"\b\d{6}\b", " ", t)          # carimbo YYMMDD
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return [x for x in t.split()
            if len(x) >= 4 and not x.isdigit() and x not in STOP]


def termos(texto: str) -> set[str]:
    """Unigramas + bigramas adjacentes. Bigrama e sinal melhor: 'referencias
    visuais' diz algo, 'visuais' sozinho diz pouco."""
    tk = tokens(texto)
    saida = set(tk)
    saida.update(f"{a} {b}" for a, b in zip(tk, tk[1:]))
    return saida


def titulos(arq: Path, limite: int = 12) -> str:
    """Nome + cabecalhos do arquivo. NAO le o corpo: menos ruido, menos risco."""
    partes = [arq.stem]
    if arq.suffix.lower() in EXT_TEXTO:
        try:
            with arq.open(encoding="utf-8", errors="replace") as f:
                for i, linha in enumerate(f):
                    if i > 400:
                        break
                    linha = linha.strip()
                    if linha.startswith("#"):
                        partes.append(linha.lstrip("#").strip())
                    elif "<title>" in linha.lower():
                        partes.append(re.sub(r"<[^>]+>", " ", linha))
                    elif re.match(r"<h[1-3][ >]", linha.lower()):
                        partes.append(re.sub(r"<[^>]+>", " ", linha))
                    if len(partes) > limite:
                        break
        except OSError:
            pass
    return " · ".join(partes)


# ---------------------------------------------------------------------------
# coleta: cada item vira {tipo, rotulo, caminho, termos}
# ---------------------------------------------------------------------------
def _rel(raiz: Path, p: Path) -> str:
    try:
        return str(p.relative_to(raiz)).replace("\\", "/")
    except ValueError:
        return str(p)


def _item(raiz: Path, tipo: str, rotulo: str, caminho: Path, texto: str) -> dict:
    t = termos(texto)
    if len(t) > TETO_TERMOS:
        # arquivo-lexico (lista de dependencias, glossario): o nome ainda vale,
        # o miolo nao - senao ele empresta "padrao" pra qualquer tema.
        t = termos(Path(caminho).stem if isinstance(caminho, Path) else str(caminho))
    return {"tipo": tipo, "rotulo": rotulo, "caminho": _rel(raiz, caminho), "termos": t}


def _direta(raiz: Path, nomes: tuple[str, ...]) -> Path | None:
    for n in nomes:
        if (raiz / n).is_dir():
            return raiz / n
    return None


def coletar(raiz: Path, dias: int = 90) -> list[dict]:
    itens: list[dict] = []

    # 1. pendencias - pasta ou .md solto
    base = u.pasta(raiz, "alteracoes-pendentes")
    if base.is_dir():
        for e in sorted(base.iterdir()):
            if e.name.startswith("."):
                continue
            if e.is_dir():
                dentro = [f.name for f in sorted(e.iterdir())[:20]]
                itens.append(_item(raiz, "pendencia", e.name, e,
                                   e.name + " " + " ".join(dentro)))
            elif e.suffix.lower() in EXT_TEXTO:
                itens.append(_item(raiz, "pendencia", e.stem, e, titulos(e)))

    # 2. cerebro - wiki e pessoas destilados; raw entra como FONTE (tipo
    #    proprio: mostra que o tema chegou, mesmo sem ter sido destilado)
    cer = u.pasta(raiz, "cerebro")
    if cer.is_dir():
        for sub, tipo in (("wiki", "cerebro"), ("pessoas", "cerebro"), ("raw", "fonte")):
            d = cer / sub
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.md")):
                if "MODELO" in f.stem:
                    continue
                itens.append(_item(raiz, tipo, f.stem, f, titulos(f)))
        for f in sorted(cer.glob("*.md")):
            itens.append(_item(raiz, "cerebro", f.stem, f, titulos(f)))

    # 3. docs
    d = u.pasta(raiz, "docs")
    if d.is_dir():
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in EXT_TEXTO:
                itens.append(_item(raiz, "doc", f.stem, f, titulos(f)))

    # 4. estado - cada etapa do PROGRESSO e cada cabecalho de DECISOES
    prog = u.achar(raiz, "PROGRESSO.json")
    if prog.is_file():
        try:
            dados = json.loads(prog.read_text(encoding="utf-8", errors="replace"))
            for et in (dados.get("etapas") or [])[:200]:
                t = str(et.get("titulo") or "").strip()
                if t:
                    itens.append(_item(raiz, "estado", t[:70], prog, t))
        except (OSError, ValueError):
            pass
    dec = u.achar(raiz, "DECISOES.md")
    if dec.is_file():
        try:
            for linha in dec.read_text(encoding="utf-8", errors="replace").splitlines():
                if linha.startswith("#"):
                    t = linha.lstrip("#").strip()
                    if t:
                        itens.append(_item(raiz, "estado", t[:70], dec, t))
        except OSError:
            pass

    # 5. visuais e entrada - so NOME, ate 2 niveis (tem binario grande la)
    for tipo, nomes in FONTES_DIRETAS:
        alvo = _direta(raiz, nomes)
        if not alvo:
            continue
        for e in sorted(alvo.iterdir()):
            if e.name.startswith("."):
                continue
            dentro = ""
            if e.is_dir():
                try:
                    dentro = " ".join(f.stem for f in sorted(e.iterdir())[:30])
                except OSError:
                    pass
            itens.append(_item(raiz, tipo, e.name, e, e.stem + " " + dentro))

    # 6. telemetria - SO campo estruturado. Texto de prompt nunca entra.
    try:
        eventos = tel.ler(raiz, dias=dias)
    except Exception:
        eventos = []
    vistos: dict[str, int] = defaultdict(int)
    for ev in eventos:
        for chave in ("skill", "projeto", "etapa", "evento"):
            v = ev.get(chave)
            if isinstance(v, str) and v.strip():
                vistos[v.strip()] += 1
    for v, n in sorted(vistos.items(), key=lambda x: -x[1]):
        itens.append({"tipo": "evento", "rotulo": f"{v} ({n}x)",
                      "caminho": ".mb-log/telemetria-*.jsonl", "termos": termos(v)})

    return itens


def indice_coberto(raiz: Path) -> set[str]:
    """Tema que JA virou maquina: modelo em motor/modelos/ ou skill em
    motor/skills/. Se esta aqui, o compreensor nao propoe de novo."""
    idx: set[str] = set()
    mod = u.pasta(raiz, "modelos")
    if mod.is_dir():
        for f in mod.rglob("*"):
            if f.is_file():
                idx |= termos(titulos(f))
            elif f.is_dir():
                idx |= termos(f.name)
    sk = u.pasta(raiz, "skills")
    if sk.is_dir():
        for f in sorted(sk.glob("*/SKILL.md")):
            idx |= termos(f.parent.name)
            idx |= termos(titulos(f, limite=8))
    # script e botao TAMBEM sao cobertura: se existe bin/mb-obsidian.py, o
    # tema "obsidian" ja virou maquina e nao precisa de modelo.
    for pasta_cod, padrao in ((raiz / "bin", "*.*"), (u.pasta(raiz, "scripts"), "*.cmd")):
        if pasta_cod.is_dir():
            for f in sorted(pasta_cod.glob(padrao)):
                nome = re.sub(r"^(mb[-_]|\d{6}[-_])", "", f.stem)
                idx |= termos(nome.replace("-", " ").replace("_", " "))
    mt = raiz / "motor"
    if mt.is_dir():
        for e in sorted(mt.iterdir()):
            if e.is_dir():
                idx |= termos(e.name)
    return idx


# ---------------------------------------------------------------------------
# compreensor 1: TEMPLATIZAR
# ---------------------------------------------------------------------------
def _slug(termo: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", termo).strip("-")


def _destino(tipos: set[str]) -> str:
    if "visual" in tipos:
        return "modelos/visuais"
    if "cerebro" in tipos or "fonte" in tipos:
        return "modelos/cerebro"
    return "modelos"


def _evidencias(itens: list[dict]) -> list[tuple]:
    """Artefato entra inteiro. Apoio (prosa de estado, evento) vira UMA linha
    por tipo com a contagem - senao 20 cabecalhos de DECISOES.md afogam a
    evidencia que interessa."""
    arte = sorted({(i["tipo"], i["rotulo"], i["caminho"]) for i in itens
                   if i["tipo"] in TIPOS_ARTEFATO})
    apoio = []
    for tipo in sorted(TIPOS_APOIO):
        marcas = {(i["rotulo"], i["caminho"]) for i in itens if i["tipo"] == tipo}
        if marcas:
            caminho = sorted({c for _, c in marcas})[0]
            apoio.append((tipo, f"{len(marcas)} menção(ões)", caminho))
    return arte + apoio


def detectar(itens: list[dict], coberto: set[str], min_tipos: int = 2,
             min_itens: int = 2) -> dict:
    mapa: dict[str, dict] = defaultdict(lambda: {"tipos": set(), "itens": []})
    for it in itens:
        for t in it["termos"]:
            alvo = mapa[t]
            alvo["tipos"].add(it["tipo"])
            alvo["itens"].append(it)

    brutos, quase = [], []
    for termo, d in mapa.items():
        arte = d["tipos"] & TIPOS_ARTEFATO
        apoio = d["tipos"] & TIPOS_APOIO
        if len(arte) < min_tipos:
            continue
        caminhos = {i["caminho"] for i in d["itens"]}
        c_arte = {i["caminho"] for i in d["itens"] if i["tipo"] in TIPOS_ARTEFATO}
        if len(c_arte) < min_itens:
            continue
        if len(caminhos) > TETO_UBIQUIDADE:
            quase.append({"termo": termo, "motivo": f"vocabulário — {len(caminhos)} lugares"})
            continue
        if not (arte & TIPOS_FORTE):
            quase.append({"termo": termo,
                          "motivo": "assunto que você leu (doc/fonte), não que você faz"})
            continue
        forca = 3 * len(arte) + len(c_arte) + len(apoio) + (1 if " " in termo else 0)
        brutos.append({
            "termo": termo,
            "bigrama": " " in termo,
            "tipos": sorted(d["tipos"]),
            "forca": forca,
            "coberto": termo in coberto,
            "evidencias": _evidencias(d["itens"]),
        })
    brutos.sort(key=lambda x: (-x["forca"], not x["bigrama"], x["termo"]))

    # um bigrama forte engole seus unigramas quando eles nao trazem lugar novo
    guardados, cobertos = [], []
    for c in brutos:
        destino = cobertos if c["coberto"] else guardados
        if not c["bigrama"]:
            meus = {e[2] for e in c["evidencias"] if e[0] in TIPOS_ARTEFATO}
            engolido = any(
                c["termo"] in g["termo"].split()
                and meus <= {e[2] for e in g["evidencias"] if e[0] in TIPOS_ARTEFATO}
                for g in guardados + cobertos if g["bigrama"])
            if engolido:
                continue
        c["modelo_sugerido"] = f"{_destino(set(c['tipos']))}/{_slug(c['termo'])}.md"
        destino.append(c)
    quase.sort(key=lambda x: (len(x["termo"].split()) < 2, x["termo"]))
    return {"achados": guardados, "cobertos": cobertos, "quase": quase[:6]}


def _primeiro_cabecalho(arq: Path) -> str:
    """Titulo real do arquivo, sem o prefixo burocratico. De
    "# Nota pendente - 260818 · Camada de referencias visuais" sobra so a
    parte que diz alguma coisa."""
    try:
        with arq.open(encoding="utf-8", errors="replace") as f:
            for i, linha in enumerate(f):
                if i > 30:
                    break
                linha = linha.strip()
                if linha.startswith("# "):
                    t = linha.lstrip("#").strip()
                    for sep in ("\u00b7", "\u2014", " - "):
                        if sep in t:
                            t = t.split(sep)[-1].strip()
                    return t
    except OSError:
        pass
    return ""


def declarados(itens: list[dict], raiz: Path) -> list[dict]:
    """Pendencia que JA pede templatizacao pelo proprio nome. Nao depende de
    estatistica: e pedido escrito, so estava sem ninguem olhando. Confere
    tambem se o modelo proposto ja existe - pendencia feita e pendencia que
    so falta fechar."""
    mod = u.pasta(raiz, "modelos")
    subpastas = {e.name for e in mod.iterdir() if e.is_dir()} if mod.is_dir() else set()
    saida = []
    for it in itens:
        if it["tipo"] != "pendencia":
            continue
        nome = _sem_acento(it["rotulo"].lower())
        if "templatizar" not in nome:
            continue
        assunto = re.sub(r"^\d{6}[-_]?", "", it["rotulo"])
        assunto = re.sub(r"(?i)^templatizar[-_]?", "", assunto)
        slug = _slug(_sem_acento(assunto.lower()))

        # roteia pro subdiretorio de modelos cujo nome o assunto encosta
        destino = next((sp for sp in sorted(subpastas)
                        if any(t.startswith(sp[:5]) for t in tokens(assunto))), "")
        rel = f"modelos/{destino + '/' if destino else ''}{slug}.md"
        alvo = mod / (f"{destino}/" if destino else "") / f"{slug}.md"

        titulo, idade = "", None
        alvo_pend = raiz / it["caminho"]
        if alvo_pend.is_dir():
            for f in sorted(alvo_pend.glob("*.md")):
                titulo = _primeiro_cabecalho(f)
                if titulo:
                    break
        m = re.match(r"(\d{2})(\d{2})(\d{2})", it["rotulo"])
        if m:
            try:
                nasc = dt.date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
                idade = (tel.hoje() - nasc).days
            except ValueError:
                idade = None
        saida.append({"pendencia": it["rotulo"], "caminho": it["caminho"],
                      "assunto": assunto, "titulo": titulo, "dias_parado": idade,
                      "modelo_sugerido": rel, "ja_existe": alvo.is_file()})
    return saida


# ---------------------------------------------------------------------------
# saida
# ---------------------------------------------------------------------------
ROTULO = {"pendencia": "pendência", "cerebro": "cérebro", "fonte": "fonte bruta",
          "doc": "doc", "estado": "estado", "visual": "visual",
          "entrada": "entrada", "evento": "evento"}


def montar(raiz: Path, dias: int, min_tipos: int) -> dict:
    itens = coletar(raiz, dias=dias)
    decl = declarados(itens, raiz)
    r = detectar(itens, indice_coberto(raiz), min_tipos=min_tipos)
    # o que a secao 1 ja mostra nao volta na secao 2 com outro destino
    ja_dito = {t for x in decl for t in termos(x["assunto"])}
    r["achados"] = [a for a in r["achados"] if a["termo"] not in ja_dito]
    tipos = sorted({i["tipo"] for i in itens})
    return {
        "versao": VERSAO,
        "gerado_em": tel.agora().isoformat(timespec="seconds"),
        "regra": ("tema em >=%d tipos de lugar e >=2 arquivos, sem modelo "
                  "nem skill cobrindo" % min_tipos),
        "resumo": {"itens": len(itens), "tipos": tipos,
                   "dias_telemetria": dias,
                   "achados": len(r["achados"]), "cobertos": len(r["cobertos"])},
        "declarados": decl,
        "achados": r["achados"][:TOPO],
        "cobertos": [c["termo"] for c in r["cobertos"]][:30],
        "quase": r["quase"],
    }


def markdown(d: dict) -> str:
    L = ["# Padrões — o que já se repete e ainda não virou modelo", "",
         f"> `bin/mb-compreensor.py` v{d['versao']} · gerado em "
         f"{d['gerado_em'][:16].replace('T', ' ')} (relógio da central)  ",
         f"> Varreu **{d['resumo']['itens']} itens** de {len(d['resumo']['tipos'])} tipos "
         f"({' · '.join(ROTULO.get(t, t) for t in d['resumo']['tipos'])}) · "
         f"telemetria dos últimos {d['resumo']['dias_telemetria']} dias  ",
         f"> Regra do achado: {d['regra']}", ""]

    L += ["## 1. Declarado — você já pediu isso por escrito", ""]
    if d["declarados"]:
        L += ["| pendência | o que ela pede | parada há | modelo a criar | já existe? |",
              "|---|---|---|---|---|"]
        for x in d["declarados"]:
            idade = f"{x['dias_parado']} dias" if x["dias_parado"] is not None else "—"
            L.append(f"| `{x['caminho']}` | {x['titulo'] or x['assunto']} | {idade} | "
                     f"`{x['modelo_sugerido']}` | {'sim' if x['ja_existe'] else '**não**'} |")
        L += ["", "Estes não dependem de estatística: o nome da pasta é o pedido. "
              "Leia a nota dentro da pasta antes de agir — pelo menos uma delas "
              "pediu explicitamente pra NÃO implementar na hora.", ""]
    else:
        L += ["Nenhuma pendência com `templatizar` no nome.", ""]

    L += ["## 2. Achado por repetição", ""]
    if d["achados"]:
        L += ["| # | tema | aparece em | arquivos | modelo proposto |", "|---|---|---|---|---|"]
        for i, a in enumerate(d["achados"], 1):
            L.append(f"| {i} | **{a['termo']}** | "
                     f"{' · '.join(ROTULO.get(t, t) for t in a['tipos'])} | "
                     f"{len({e[2] for e in a['evidencias'] if e[0] in TIPOS_ARTEFATO})} | `{a['modelo_sugerido']}` |")
        L += ["", "### Evidência de cada um", ""]
        for i, a in enumerate(d["achados"], 1):
            L.append(f"**{i}. {a['termo']}** — força {a['forca']}")
            for tipo, rotulo, caminho in a["evidencias"][:8]:
                L.append(f"- {ROTULO.get(tipo, tipo)} · {rotulo} — `{caminho}`")
            extra = len(a["evidencias"]) - 8
            if extra > 0:
                L.append(f"- _(+{extra} outros)_")
            L.append("")
    else:
        L += ["Nada passou da régua — e isso é informação, não vazio. A régua "
              "exige repetição em tipos DIFERENTES de lugar, com pelo menos um "
              "deles sendo coisa que você **faz e guarda** (pendência, cérebro, "
              "visual). Hoje o acervo de artefato ainda é pequeno demais pra "
              "isso acontecer sozinho.", ""]
        if d.get("quase"):
            L += ["**Quase passou** — e por que não:", ""]
            L += [f"- `{q['termo']}` — {q['motivo']}" for q in d["quase"]]
            L += [""]

    if d["cobertos"]:
        L += ["## 3. Já coberto por modelo ou skill — nada a fazer", "",
              ", ".join(f"`{t}`" for t in d["cobertos"]), ""]

    L += ["## 4. O que este compreensor NÃO olhou", "",
          "- **Corpo dos arquivos.** Só nome e cabeçalho — menos ruído, e o "
          "corpo não é onde o tema se declara.",
          "- **Texto de prompt do `.mb-log`.** Fora por privacidade: o log tem "
          "conversa sua sobre currículo e empregadores. Do log entram só campos "
          "estruturados (skill, projeto, etapa, evento).",
          "- **Os outros três compreensores** (parado, órfão, ritmo) — fora do "
          "escopo da v1 por decisão sua em 260824.",
          "- **Estatística.** Com ~100 eventos de telemetria, gráfico aqui "
          "seria enfeite. Quando o log tiver semanas, o compreensor de ritmo "
          "passa a fazer sentido.", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="compreensores de padrões da central (spec §7)")
    ap.add_argument("--dir", default=None, help="raiz da central (padrão: deduzida)")
    ap.add_argument("--dias", type=int, default=90, help="janela de telemetria")
    ap.add_argument("--min-tipos", type=int, default=2, dest="min_tipos")
    ap.add_argument("--seco", action="store_true", help="mostra e NÃO grava")
    ap.add_argument("--json", action="store_true", dest="como_json")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else tel.raiz_central()
    d = montar(raiz, dias=args.dias, min_tipos=args.min_tipos)

    if args.como_json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        print(markdown(d))

    if not args.seco:
        stamp = f"{tel.agora():%y%m%d}"
        alvo = u.pasta(raiz, "relatorios") / f"{stamp}_padroes.md"
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(markdown(d), encoding="utf-8")
        js = tel.pasta_log(raiz) / "padroes.json"
        js.parent.mkdir(exist_ok=True)
        js.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n[gravado] {_rel(raiz, alvo)}  ·  {_rel(raiz, js)}")
        tel.registrar("compreensor", raiz=raiz, resultado="ok",
                      achados=len(d["achados"]), itens=d["resumo"]["itens"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
