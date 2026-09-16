#!/usr/bin/env python3
"""Prepara uma sessão MEGABRAIN sem iniciar modelo nem execução.

Mostra o catálogo de skills da fonte canônica e a instrução curta que abre uma
conversa com qualquer IA. A V6 é o padrão para entrega nova não trivial; este
script não a executa sem um brief e um projeto explícitos.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CENTRAL = Path(__file__).resolve().parents[1]
SKILLS = CENTRAL / "motor" / "skills"


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError("frontmatter ausente")
    return dict(re.findall(r"^(name|description):\s*(.+)$", match.group(1), re.MULTILINE))


def catalogo(root: Path = CENTRAL) -> list[dict[str, str]]:
    skills = root / "motor" / "skills"
    rows = []
    for path in sorted(skills.glob("*/SKILL.md"), key=lambda item: item.parent.name.casefold()):
        meta = _frontmatter(path)
        rows.append({
            "nome": meta.get("name", path.parent.name),
            "descricao": meta.get("description", "sem descrição"),
            "arquivo": str(path.relative_to(root)).replace("\\", "/"),
        })
    return rows


def resumo(root: Path = CENTRAL) -> dict[str, object]:
    rows = catalogo(root)
    names = {item["nome"] for item in rows}
    return {
        "central": str(root),
        "skills": rows,
        "padrao": "/orquestracao1 (V6)",
        "v5": "/orquestracao2 (somente retomada ou pedido explícito)",
        "pronto": {"megabrain", "orquestracao1", "orquestracao2"}.issubset(names),
        "instrucao_para_ia": (
            "Início de sessão MEGABRAIN: leia o catálogo motor/skills e leia por inteiro "
            "as SKILL.md necessárias antes de agir. Para entrega nova não trivial e "
            "decomponível, inicie /orquestracao1 (V6). Não inicie execução para pergunta "
            "simples, conversa, agenda ou correção local óbvia. Use /orquestracao2 apenas "
            "para retomada V5 ou pedido explícito."
        ),
    }


def curta(descricao: str, limite: int = 130) -> str:
    """Mantém o atalho escaneável; --json preserva a descrição integral."""
    primeira = descricao.split(". ", 1)[0].strip()
    if len(primeira) <= limite:
        return primeira
    return primeira[:limite - 1].rstrip() + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="saída para dashboard ou outro agente")
    args = parser.parse_args()
    data = resumo()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if data["pronto"] else 2

    print("MEGABRAIN — início de sessão")
    print("V6 padrão: /orquestracao1 para entrega nova não trivial e decomponível.")
    print("V5: /orquestracao2 só para retomada ou pedido explícito.")
    print("Este comando não chama IA, não inicia loop e não consome cota.\n")
    print("Skills disponíveis na fonte canônica:")
    for item in data["skills"]:
        print(f"  - /{item['nome']}: {curta(item['descricao'])}")
    print("\nCopie e cole na IA desta sessão:")
    print(data["instrucao_para_ia"])
    return 0 if data["pronto"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print("Precisa de atenção: " + str(exc))
        raise SystemExit(2)
