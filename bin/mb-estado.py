#!/usr/bin/env python3
"""
mb-estado.py — o estado da central em JSON. A fonte única, legível por máquina.

POR QUE EXISTE (260825, decisão 260825t)
----------------------------------------
"Um relatório só" foi decidido três vezes (260822, 260824, 260825) e nunca
fechou. A causa não era falta de disciplina: o relatório tentava ser ao mesmo
tempo a RENDERIZAÇÃO e o BANCO DE DADOS, e servir dois leitores com necessidades
opostas. Toda vez que uma IA precisava de um dado, o jeito de conseguir era
parsear markdown de prosa — então nasciam mais artefatos.

A síntese entre a lição 260813 ("relatório serve IA e humano") e a decisão
260825n ("nada que serve os dois sobrevive sem inchar"):

    UMA FONTE DE DADOS  →  DUAS RENDERIZAÇÕES

    dados/estado.json ─┬─→ 00_painel/RELATORIO.html   (o humano)
                       └─→ hook / contexto do agente  (a IA)

Nenhuma IA precisa mais parsear ESTADO.md, HANDOFF.md, PROGRESSO.json,
VERSAO.txt e DECISOES.md em cinco formatos diferentes. Lê um JSON. E vale igual
pro Claude, Kimi, GPT, Gemini, Codex ou Qwen local — nenhum deles precisa saber
onde os arquivos moram nem em que layout.

CONTRATO DO ARQUIVO
-------------------
- `schema`: inteiro. Sobe quando um campo muda de sentido. Quem lê deve conferir.
- `gerado_em`: ISO com fuso de São Paulo.
- Todo número tem fonte declarada em `_fonte` no mesmo bloco.
- Campo que não pôde ser medido vem `null`, nunca zero ou chute.

Uso:
  mb-estado.py                # grava dados/estado.json e imprime o resumo
  mb-estado.py --stdout       # joga o JSON na saída (pra pipe/agente)
  mb-estado.py --campo versao.atual   # lê um caminho pontilhado
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import mb_utils as u
import mb_trava as trava

u.utf8_console()

SCHEMA = 1


def _agora():
    try:
        import mb_telemetria as t
        return t.agora().isoformat(timespec="seconds")
    except Exception:
        import datetime as dt
        return dt.datetime.now().isoformat(timespec="seconds")


def _txt(p: Path) -> str:
    return u.safe_read_text(p) or ""


def _json(p: Path):
    t = _txt(p)
    if not t:
        return None
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


# --------------------------------------------------------------------------
# coletores — um por assunto, cada um devolve dict com _fonte
# --------------------------------------------------------------------------

def col_documentos(c: Path) -> dict:
    """Índice dos .md informacionais — caminho, título, tamanho, quando mudou.

    260825 (decisão 260825v): NÃO carrega o conteúdo. O `RELATORIO.html` vinha
    embutindo os 31 documentos inteiros — 471 KB, 76% do arquivo — porque uma IA
    precisava do texto e o único jeito era o HTML agregar. Com este índice a IA
    sabe o que existe, onde está e quando mudou, e lê só o arquivo de que
    precisa. Índice é barato; despejo é caro e sempre desatualiza.
    """
    ignorar = {"90_arquivo", "99_to_delete", "_github", "00_painel", "dados",
               ".mb-backup", ".mb-log", ".mb-aspirador", "__pycache__", ".git",
               "motor", "02_entrada", ".claude", ".megabrain"}
    itens = []
    for arq in sorted(c.rglob("*.md")):
        rel = arq.relative_to(c)
        if {x.casefold() for x in rel.parts[:-1]} & ignorar:
            continue
        texto = u.safe_read_text(arq) or ""
        titulo = next((l[2:].strip() for l in texto.splitlines() if l.startswith("# ")),
                      arq.stem.replace("_", " ").replace("-", " "))
        try:
            mt = arq.stat().st_mtime
            import datetime as dt
            quando = dt.datetime.fromtimestamp(mt).strftime("%Y-%m-%d")
        except OSError:
            quando = None
        itens.append({
            "caminho": rel.as_posix(),
            "titulo": titulo[:120],
            "bytes": arq.stat().st_size,
            "linhas": texto.count(chr(10)) + 1,
            "modificado": quando,
        })
    # os de máquina que a IA também precisa achar, sem varrer motor/ inteiro
    for nome in ("skills/megabrain/SKILL.md", "referencias/260818_padrao-resposta.md"):
        a = u.achar(c, nome)
        if a.is_file():
            itens.append({"caminho": str(a.relative_to(c)).replace("\\", "/"),
                          "titulo": nome, "bytes": a.stat().st_size,
                          "linhas": None, "modificado": None})
    return {
        "total": len(itens),
        "itens": sorted(itens, key=lambda x: x["caminho"]),
        "como_usar": "leia o arquivo que interessa pelo caminho; este índice NÃO carrega conteúdo",
        "_fonte": "rglob *.md na central, fora de máquina/arquivo/derivado",
    }


def col_versao(c: Path) -> dict:
    arq = u.achar(c, "VERSAO.txt")
    linha = u.read_first_non_empty_line(arq) or ""
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s*·\s*(v[\d.]+)\s*—\s*(.*)", linha)
    entradas = [l for l in _txt(arq).splitlines() if re.match(r"^\d{4}-\d{2}-\d{2} · v", l)]
    return {
        "atual": m.group(2) if m else None,
        "data": m.group(1) if m else None,
        "titulo": (m.group(3)[:180] if m else None),
        "entradas_no_changelog": len(entradas),
        "_fonte": str(arq.relative_to(c)) if arq.is_file() else None,
    }


def col_git(c: Path) -> dict:
    def g(*args):
        try:
            r = subprocess.run(["git", *args], cwd=c, capture_output=True,
                               text=True, timeout=8)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    if not (c / ".git").is_dir():
        return {"repositorio": False, "_fonte": None}
    sujos = g("status", "--porcelain")
    return {
        "repositorio": True,
        "head": g("rev-parse", "--short", "HEAD"),
        "assunto": g("log", "-1", "--pretty=%s"),
        "commits": int(g("rev-list", "--count", "HEAD") or 0),
        "arquivos_sujos": len([l for l in (sujos or "").splitlines() if l.strip()]),
        "remote": g("remote", "get-url", "origin"),
        "_fonte": ".git",
    }


def col_memoria(c: Path) -> dict:
    lic = u.achar(c, "licoes-megabrain.md")
    texto = _txt(lic)
    total = len(re.findall(r"^## ", texto, re.M))
    idx = _json(u.pasta(c, "dna") / "indice-licoes.json") or {}
    cer = u.pasta(c, "cerebro")
    return {
        "licoes_no_arquivo": total,
        "licoes_indexadas": len(idx.get("entradas") or []),
        "indice_em_dia": len(idx.get("entradas") or []) >= total - 2,
        "paginas_cerebro": len(list((cer / "wiki").glob("*.md"))) if (cer / "wiki").is_dir() else None,
        "cards_pessoas": len(list((cer / "pessoas").glob("*.md"))) if (cer / "pessoas").is_dir() else None,
        "fontes_cruas": len(list((cer / "raw").glob("*"))) if (cer / "raw").is_dir() else None,
        "_fonte": f"{lic.relative_to(c)} + dna/indice-licoes.json + memoria/cerebro/",
    }


def col_decisoes(c: Path) -> dict:
    arq = u.achar(c, "DECISOES.md")
    texto = _txt(arq)
    blocos = re.findall(r"^## (.+)$", texto, re.M)
    com_alt = len(re.findall(r"ALTERNATIVA[S]? DESCARTADA", texto))
    return {
        "total": len(blocos),
        "com_alternativa_descartada": com_alt,
        "ultimas": [b.strip()[:110] for b in blocos[-5:]][::-1],
        "_fonte": str(arq.relative_to(c)) if arq.is_file() else None,
    }


def col_estado(c: Path) -> dict:
    est = _txt(u.achar(c, "ESTADO.md"))
    han = _txt(u.achar(c, "HANDOFF.md"))
    m = re.search(r"TL;DR:(.*?)(?:\n\n|\Z)", est, re.S)
    quem = re.search(r"TRAVADO_POR:\s*(.+)", han)
    blo = re.search(r"BLOQUEIO:\s*(.+)", est)
    prog = _json(u.achar(c, "PROGRESSO.json")) or {}
    etapas = prog.get("etapas") or []
    feitas = sum(1 for e in etapas if e.get("status") == "feito")
    return {
        "tldr": " ".join(m.group(1).split())[:600] if m else None,
        "bloqueio": (blo.group(1).strip() if blo else None),
        "trava": (quem.group(1).strip() if quem else None),
        "etapas_feitas": feitas,
        "etapas_total": len(etapas),
        "_fonte": "memoria/estado/ESTADO.md + HANDOFF.md + PROGRESSO.json",
    }


def col_meta(c: Path) -> dict:
    t = _txt(u.achar(c, "META.md"))
    def campo(nome):
        m = re.search(rf"^{nome}:\s*(.+?)(?=\n[A-ZÁÉÍÓÚÇ_]+:|\n\n|\Z)", t, re.M | re.S)
        return " ".join(m.group(1).split())[:400] if m else None
    return {
        "objetivo": campo("OBJETIVO"),
        "criterio_de_pronto": campo("CRITÉRIO DE PRONTO"),
        "proximo_passo": campo("PRÓXIMO PASSO"),
        "definido_em": campo("DEFINIDO EM"),
        "_fonte": "memoria/estado/META.md",
    }


def col_suite(c: Path) -> dict:
    try:
        r = subprocess.run([sys.executable, "-B", str(c / "bin" / "mb-testar.py")],
                           cwd=c, capture_output=True, text=True, timeout=180)
        saida = (r.stdout or "") + (r.stderr or "")
        m = re.search(r"Ran (\d+) tests? in ([\d.]+)s", saida)
        return {
            "testes": int(m.group(1)) if m else None,
            "segundos": float(m.group(2)) if m else None,
            # 260825: era `"\nOK" in saida`. O runner às vezes imprime uma
            # linha depois do OK e o casamento de string virava falso-vermelho
            # — a suíte verde reportada como quebrada. Exit code é o contrato
            # que o unittest promete; texto de saída não é contrato nenhum.
            "verde": r.returncode == 0,
            "_fonte": "bin/mb-testar.py (exit code)",
        }
    except (OSError, subprocess.SubprocessError):
        return {"testes": None, "verde": None, "_fonte": "bin/mb-testar.py (não executou)"}


def col_agentes(c: Path) -> dict:
    """Absorve o RELATORIO-AGENTES: uso por agente, a partir dos .mb-log."""
    base = c / ".mb-log"
    por_agente: dict[str, int] = {}
    por_evento: dict[str, int] = {}
    dias = set()
    total = 0
    if base.is_dir():
        for arq in list(base.glob("*.jsonl")) + list(base.glob("*/*.jsonl")):
            for linha in _txt(arq).splitlines():
                try:
                    ev = json.loads(linha)
                except (json.JSONDecodeError, ValueError):
                    continue
                total += 1
                por_agente[ev.get("agente") or "?"] = por_agente.get(ev.get("agente") or "?", 0) + 1
                por_evento[ev.get("evento") or "?"] = por_evento.get(ev.get("evento") or "?", 0) + 1
                ts = ev.get("ts") or ""
                if len(ts) >= 10:
                    dias.add(ts[:10])
    return {
        "eventos": total,
        "dias_com_registro": len(dias),
        "por_agente": dict(sorted(por_agente.items(), key=lambda kv: -kv[1])),
        "por_evento": dict(sorted(por_evento.items(), key=lambda kv: -kv[1])),
        "_fonte": ".mb-log/*.jsonl (inclui o balde fora-de-projeto)",
    }


def col_padroes(c: Path) -> dict:
    """Absorve o AAMMDD_padroes.md: o que se repete e não virou modelo."""
    d = _json(c / ".mb-log" / "padroes.json") or {}
    temas = d.get("temas") or d.get("candidatos") or []
    return {
        "temas": temas[:10] if isinstance(temas, list) else [],
        "gerado_em": d.get("gerado_em"),
        "regua": d.get("regua") or "tema em ≥2 tipos de lugar, um deles sendo coisa que ele faz e guarda, sem modelo/skill/script cobrindo",
        "_fonte": ".mb-log/padroes.json (bin/mb-compreensor.py)",
    }


def col_copias(c: Path) -> dict:
    """Absorve a auditoria de cópias: os megabrains de projeto."""
    try:
        sys.path.insert(0, str(c / "bin"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("mb_aud", c / "bin" / "mb-auditar-copias.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        v = mod.versao(u.pasta(c, "nucleo"))
        itens = []
        for p in mod.copias(c.parent):
            if p.resolve() == c.resolve():
                continue
            r = mod.auditar(p)
            itens.append({
                "projeto": p.parent.name,
                "versao": r["versao"],
                "em_dia": r["versao"] == v,
                "arquivos": r["arquivos_topo"],
                "mortos": len(r["mortos"]) + len(r["velhos"]),
                "licoes": r["licoes"],
                "layout": r["formato"],
            })
        return {
            "total": len(itens),
            "em_dia": sum(1 for i in itens if i["em_dia"]),
            "com_morto": sum(1 for i in itens if i["mortos"]),
            "itens": itens,
            "_fonte": "bin/mb-auditar-copias.py",
        }
    except Exception as e:
        return {"total": None, "erro": str(e)[:120], "_fonte": "bin/mb-auditar-copias.py"}


def col_registro(c: Path) -> dict:
    """O que ele clica, o que ele chama, o que a IA roda, quais skills."""
    try:
        sys.path.insert(0, str(c / "bin"))
        import mb_registro as reg
        return {
            "acoes": [{"n": n, "arquivo": f"{n:02d}_{a}.cmd", "faz": f, "quando": q}
                      for n, a, f, q in reg.ACOES],
            "rotina": [{"comando": cm, "faz": f, "quando": q} for cm, f, q in reg.ROTINA],
            "agente": [{"comando": cm, "gate": g, "faz": f, "quebra": qb}
                       for cm, g, f, qb in getattr(reg, "AGENTE", [])],
            "skills": [{"nome": n, "origem": o, "faz": f, "gatilho": g}
                       for n, o, f, g in reg.SKILLS_DELE],
            "_fonte": "bin/mb_registro.py",
        }
    except Exception as e:
        return {"erro": str(e)[:120], "_fonte": "bin/mb_registro.py"}


def col_fila(c: Path) -> dict:
    """Board local de tasks: dependências, ondas e próximas prontas."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mb_fila", str(c / "bin" / "mb-fila.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        dados = mod._carregar(c / "dados" / "fila.json")
        return mod.resumo(dados)
    except FileNotFoundError:
        return {"total": 0, "erro": "dados/fila.json não existe", "_fonte": "dados/fila.json"}
    except Exception as e:
        return {"erro": str(e)[:120], "_fonte": "dados/fila.json"}


def col_signoffs(c: Path) -> dict:
    """Specs vivas: quantas estão assinadas, obsoletas ou sem sign-off."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mb_spec_signoff", str(c / "bin" / "mb-spec-signoff.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        specs = mod._status_specs(c)
        ok = sum(1 for s in specs if s["estado"] == "ok")
        obsoletas = sum(1 for s in specs if s["obsoleto"] and s["estado"] != "sem_signoff")
        sem = sum(1 for s in specs if s["estado"] == "sem_signoff")
        return {
            "total": len(specs),
            "ok": ok,
            "obsoletas": obsoletas,
            "sem_signoff": sem,
            "detalhes": specs,
            "_fonte": "bin/mb-spec-signoff.py (SPEC.md rastreados)",
        }
    except Exception as e:
        return {"erro": str(e)[:120], "_fonte": "bin/mb-spec-signoff.py"}


def montar(c: Path, com_suite: bool = True) -> dict:
    d = {
        "schema": SCHEMA,
        "gerado_em": _agora(),
        "central": str(c),
        "versao": col_versao(c),
        "meta": col_meta(c),
        "estado": col_estado(c),
        "git": col_git(c),
        "memoria": col_memoria(c),
        "decisoes": col_decisoes(c),
        "agentes": col_agentes(c),
        "padroes": col_padroes(c),
        "copias": col_copias(c),
        "registro": col_registro(c),
        "documentos": col_documentos(c),
        "fila": col_fila(c),
        "signoffs": col_signoffs(c),
    }
    # null, nunca zero nem chute: "não medido" e "medido e deu zero" são
    # coisas diferentes, e o contrato do arquivo promete a diferença.
    d["suite"] = col_suite(c) if com_suite else {
        "testes": None, "segundos": None, "verde": None,
        "_fonte": "pulado (--sem-suite) — rode python bin/mb-testar.py"}
    return d


def caminho_saida(c: Path) -> Path:
    return c / "dados" / "estado.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stdout", action="store_true", help="joga o JSON na saída")
    ap.add_argument("--sem-suite", action="store_true", help="não roda os testes")
    ap.add_argument("--campo", help="lê um caminho pontilhado, ex.: versao.atual")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()

    c = Path(a.dir).resolve() if a.dir else Path(__file__).resolve().parent.parent
    d = montar(c, com_suite=not a.sem_suite)

    if a.campo:
        val = d
        for pedaco in a.campo.split("."):
            val = (val or {}).get(pedaco) if isinstance(val, dict) else None
        print(json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val)
        return 0

    if a.stdout:
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return 0

    saida = caminho_saida(c)
    saida.parent.mkdir(parents=True, exist_ok=True)
    try:
        trava.escrever(
            saida,
            json.dumps(d, ensure_ascii=False, indent=2),
            agente=trava.agente_script("mb-estado"),
            motivo="regenera a fonte de estado para as IAs",
        )
    except trava.TravaOcupada as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"estado: {saida}  ({saida.stat().st_size // 1024} KB)")
    print(f"  versão {d['versao']['atual']} · {d['decisoes']['total']} decisões · "
          f"{d['memoria']['licoes_no_arquivo']} lições · "
          f"{d['copias']['em_dia']}/{d['copias']['total']} cópias em dia · "
          f"suíte {d['suite']['testes'] if d['suite']['testes'] is not None else 'não medida'}"
          f"{'' if d['suite']['verde'] is None else (' verde' if d['suite']['verde'] else ' VERMELHA')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
