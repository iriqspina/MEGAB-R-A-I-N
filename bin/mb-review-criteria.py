#!/usr/bin/env python3
"""
mb-review-criteria.py — AI reviewer local contra acceptance criteria. v1.0 (260825)

Adaptação da mecânica 3 do djinnai.io: antes de handoff, verificar se a
entrega satisfaz os critérios de aceite da spec. Não chama modelo remoto
— faz análise heurística local sobre o diff do git e os arquivos em disco.

FONTES DE CRITÉRIOS (em ordem de prioridade):
1. `SPEC.md` na raiz do projeto/central
2. `META.md` na raiz (campo `CRITÉRIO DE PRONTO`)
3. `--criterios` passados na linha de comando

Uso:
    python bin/mb-review-criteria.py --dir <RAIZ>
    python bin/mb-review-criteria.py --dir <RAIZ> --spec caminho/para/SPEC.md
    python bin/mb-review-criteria.py --dir <RAIZ> --criterios "testes passam" "docs atualizadas"

SAÍDA: Markdown com parecer por critério e veredito geral.
CÓDIGO DE SAÍDA: 0 = aprovado, 1 = reprovado, 2 = erro (sem spec/critérios).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import mb_utils as u

u.utf8_console()


def _central() -> Path:
    return Path(__file__).resolve().parent.parent


def _git(raiz: Path, *args: str, timeout: int = 15) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            ["git", *args], cwd=raiz, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, check=False,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", str(e)


def _diff(raiz: Path) -> str:
    """Diff de todos os arquivos rastreados + status de untracked."""
    _, stdout, _ = _git(raiz, "diff", "--stat")
    _, diff, _ = _git(raiz, "diff")
    _, status, _ = _git(raiz, "status", "--short")
    return f"{stdout}\n{status}\n{diff}"


def _extrair_criterios_meta(texto: str) -> list[str]:
    """Extrai linhas do campo CRITÉRIO DE PRONTO em META.md."""
    m = re.search(
        r"^CRIT[ÉE]RIO DE PRONTO:\s*(.+?)(?=\n[A-ZÁÉÍÓÚÇ_]+(?:\s+[A-ZÁÉÍÓÚÇ_]+)*:|\n\n|\Z)",
        texto, re.M | re.S,
    )
    if not m:
        return []
    conteudo = m.group(1).strip()
    # critérios podem estar em linhas separadas ou separados por ponto-e-vírgula
    partes = [p.strip() for p in re.split(r"[;\n]", conteudo) if p.strip()]
    return [p.lstrip("- ").strip() for p in partes]


def _extrair_criterios_spec(texto: str) -> list[str]:
    """Extrai itens da seção ## Acceptance Criteria, ignorando comentários e placeholders."""
    m = re.search(
        r"^##\s+Acceptance Criteria\s*\n(.*?)(?=^##\s+|\Z)",
        texto, re.M | re.S,
    )
    if not m:
        return []
    itens = []
    for l in m.group(1).strip().splitlines():
        l = l.strip()
        if not l or l.startswith("<!--") or l.endswith("-->") or l.startswith("<"):
            continue
        # remove marcador de lista + checkbox
        limpa = re.sub(r"^[-*]+\s*\[[ x]\]\s*", "", l).strip()
        if not limpa:
            limpa = re.sub(r"^[-*]+\s*", "", l).strip()
        # remove placeholders do tipo <critério 1 — ...>
        limpa = re.sub(r"^<[^>]+>\s*", "", limpa).strip()
        if limpa and not (limpa.startswith("<") and limpa.endswith(">")):
            itens.append(limpa)
    return itens


def _criterios_de_arquivo(caminho: Path) -> list[str]:
    txt = u.safe_read_text(caminho) or ""
    return _extrair_criterios_spec(txt) or _extrair_criterios_meta(txt)


def _encontrar_spec(raiz: Path) -> Path | None:
    for nome in ("SPEC.md", "META.md"):
        p = u.achar(raiz, nome)
        if p.is_file():
            return p
    return None


def _tokens(texto: str) -> set[str]:
    """Tokens significativos em minúsculo, sem pontuação."""
    return set(re.findall(r"[a-záéíóúçãõâêîôûàèìòùäëïöü0-9]+", texto.lower()))


def _evidencia(criterio: str, diff: str, arquivos: Iterable[Path]) -> tuple[bool, str]:
    """Heurística simples: procura palavras-chave do critério no diff e arquivos."""
    tokens_crit = _tokens(criterio) - {"de", "do", "da", "em", "um", "uma", "o", "a", "e", "ou", "que", "para", "com", "sem", "no", "na", "aos", "nas", "nos"}
    if not tokens_crit:
        return False, "critério sem palavras-chave mensuráveis"

    # Pontuação pelo diff
    tokens_diff = _tokens(diff)
    matched = tokens_crit & tokens_diff
    score = len(matched) / len(tokens_crit)

    # Pontuação por arquivos no disco
    por_arquivo = 0
    detalhes_arq = []
    for arq in arquivos:
        nome_tokens = _tokens(arq.name)
        if tokens_crit & nome_tokens:
            por_arquivo += 1
            detalhes_arq.append(arq.name)

    if score >= 0.5 or por_arquivo > 0:
        motivo = []
        if matched:
            motivo.append(f"palavras no diff: {', '.join(sorted(matched))}")
        if detalhes_arq:
            motivo.append(f"arquivos: {', '.join(detalhes_arq[:3])}")
        return True, "; ".join(motivo)

    return False, f"nenhuma evidência encontrada (esperava algo relacionado a: {', '.join(sorted(tokens_crit))})"


def _arquivos_alterados(raiz: Path) -> list[Path]:
    """Lista arquivos modificados ou novos segundo git status --short."""
    _, status, _ = _git(raiz, "status", "--short")
    arquivos = []
    for linha in status.splitlines():
        if not linha.strip():
            continue
        # formato: XY caminho
        resto = linha[2:].strip()
        if "->" in resto:
            resto = resto.split("->")[-1].strip()
        p = raiz / resto
        if p.is_file():
            arquivos.append(p)
    return arquivos


def revisar(raiz: Path, criterios: list[str], diff: str, arquivos: list[Path]) -> dict:
    itens = []
    aprovados = 0
    for c in criterios:
        ok, motivo = _evidencia(c, diff, arquivos)
        itens.append({"criterio": c, "atende": ok, "motivo": motivo})
        if ok:
            aprovados += 1
    return {
        "total": len(criterios),
        "aprovados": aprovados,
        "reprovados": len(criterios) - aprovados,
        "veredito": "APROVADO" if aprovados == len(criterios) else "REPROVADO",
        "itens": itens,
    }


def _cabecalho(caminho_spec: Path | None, total: int) -> str:
    fonte = f"{caminho_spec.relative_to(_central())}" if caminho_spec else "argumento --criterios"
    return f"# Review de acceptance criteria\n\nFonte: `{fonte}`\nCritérios avaliados: {total}\n"


def _formatar(r: dict, caminho_spec: Path | None) -> str:
    linhas = [_cabecalho(caminho_spec, r["total"]), ""]
    for item in r["itens"]:
        simbolo = "✓" if item["atende"] else "✗"
        linhas.append(f"- {simbolo} **{item['criterio']}**")
        linhas.append(f"  → {item['motivo']}")
    linhas.append("")
    linhas.append(f"**Veredito geral: {r['veredito']}** ({r['aprovados']}/{r['total']} atendidos)")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="raiz da central/projeto")
    ap.add_argument("--spec", default=None, help="caminho para SPEC.md ou META.md")
    ap.add_argument("--criterios", nargs="+", help="critérios via linha de comando")
    ap.add_argument("--json", action="store_true", help="saída em JSON em vez de Markdown")
    ap.add_argument("--saida", help="arquivo para escrever o parecer")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else _central()

    criterios: list[str] = []
    caminho_spec: Path | None = None
    if args.criterios:
        criterios = list(args.criterios)
    elif args.spec:
        caminho_spec = Path(args.spec).resolve()
        criterios = _criterios_de_arquivo(caminho_spec)
    else:
        caminho_spec = _encontrar_spec(raiz)
        if caminho_spec:
            criterios = _criterios_de_arquivo(caminho_spec)

    if not criterios:
        print("ERRO: nenhum critério encontrado. Passe --criterios, --spec ou crie SPEC.md/META.md.",
              file=sys.stderr)
        return 2

    diff = _diff(raiz)
    arquivos = _arquivos_alterados(raiz)
    r = revisar(raiz, criterios, diff, arquivos)

    if args.json:
        saida = json.dumps(r, ensure_ascii=False, indent=2)
    else:
        saida = _formatar(r, caminho_spec)

    if args.saida:
        u.atomic_write_text(Path(args.saida), saida + "\n")
        print(f"review salvo em: {args.saida}")
    else:
        print(saida)

    return 0 if r["veredito"] == "APROVADO" else 1


if __name__ == "__main__":
    sys.exit(main())
