#!/usr/bin/env python3
"""
mb-fila.py — fila local de tasks com dependências e ondas. v1.0 (260825)

Adaptação da mecânica 2 do djinnai.io: decompor entrega em tasks,
explicitar bloqueios e calcular ondas de execução. Não despacha agentes
reais — é um board local que diz "o que está pronto para começar agora".

CONTRATO DE dados/fila.json
- schema: inteiro (quebra se mudar)
- epics: lista com id, titulo, status, origem
- tasks: lista com id, epic, titulo, descricao, blocked_by, prioridade,
  dono, estado ∈ {todo, em_progresso, feito}

Uso:
    python bin/mb-fila.py --dir <RAIZ> listar
    python bin/mb-fila.py --dir <RAIZ> proxima
    python bin/mb-fila.py --dir <RAIZ> avancar <ID>
    python bin/mb-fila.py --dir <RAIZ> json

Sem --dir, assume a central acima de bin/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import mb_utils as u
import mb_trava as trava

u.utf8_console()

SCHEMA = 1
ESTADOS = {"todo", "em_progresso", "feito"}


def _central() -> Path:
    return Path(__file__).resolve().parent.parent


def _carregar(caminho: Path) -> dict:
    txt = u.safe_read_text(caminho)
    if not txt:
        raise FileNotFoundError(f"fila não encontrada: {caminho}")
    dados = json.loads(txt)
    if dados.get("schema") != SCHEMA:
        raise ValueError(f"schema incompatível: esperado {SCHEMA}, veio {dados.get('schema')}")
    return dados


def _salvar(caminho: Path, dados: dict) -> None:
    dados["atualizado_em"] = dt.datetime.now().isoformat(timespec="seconds")
    u.atomic_write_text(caminho, json.dumps(dados, ensure_ascii=False, indent=2) + "\n")


def calcular_ondas(tasks: list[dict]) -> dict[str, int]:
    """Devolve mapa id -> onda. Onda 0 = sem dependências. Ciclos levantam ValueError."""
    por_id: dict[str, dict] = {t["id"]: t for t in tasks}
    ondas: dict[str, int] = {}

    def onda(task_id: str, pilha: set[str]) -> int:
        if task_id in pilha:
            ciclos = " -> ".join(list(pilha) + [task_id])
            raise ValueError(f"ciclo de dependência: {ciclos}")
        if task_id in ondas:
            return ondas[task_id]
        if task_id not in por_id:
            raise ValueError(f"dependência desconhecida: {task_id}")
        deps = por_id[task_id].get("blocked_by") or []
        if not deps:
            ondas[task_id] = 0
            return 0
        pilha.add(task_id)
        max_dep = max(onda(d, pilha) for d in deps)
        pilha.discard(task_id)
        ondas[task_id] = max_dep + 1
        return ondas[task_id]

    for t in tasks:
        onda(t["id"], set())
    return ondas


def resumo(dados: dict) -> dict:
    """Estatísticas e próximas prontas, prontas pra ir pro estado.json."""
    tasks = dados.get("tasks", [])
    por_id = {t["id"]: t for t in tasks}
    try:
        ondas = calcular_ondas(tasks)
        max_onda = max(ondas.values()) if ondas else 0
    except ValueError as e:
        return {
            "total": len(tasks),
            "prontas": None,
            "bloqueadas": None,
            "feitas": None,
            "ondas": None,
            "erro": str(e),
            "_fonte": "dados/fila.json",
        }

    prontas = []
    for t in tasks:
        if t["estado"] == "feito":
            continue
        deps = t.get("blocked_by") or []
        if all(por_id.get(d, {}).get("estado") == "feito" for d in deps):
            prontas.append({
                "id": t["id"],
                "titulo": t["titulo"],
                "onda": ondas[t["id"]],
                "prioridade": t.get("prioridade", 99),
                "dono": t.get("dono"),
            })

    prontas.sort(key=lambda x: (x["onda"], x["prioridade"]))

    return {
        "total": len(tasks),
        "prontas": len(prontas),
        "bloqueadas": sum(1 for t in tasks if t["estado"] != "feito" and t["id"] not in {p["id"] for p in prontas}),
        "feitas": sum(1 for t in tasks if t["estado"] == "feito"),
        "ondas": max_onda + 1,
        "proximas": prontas[:5],
        "erro": None,
        "_fonte": "dados/fila.json",
    }


def cmd_listar(dados: dict, *, raw_json: bool = False) -> None:
    tasks = dados.get("tasks", [])
    ondas = calcular_ondas(tasks)
    if raw_json:
        por_onda: dict[int, list[dict]] = {}
        for t in sorted(tasks, key=lambda x: (ondas[x["id"]], x.get("prioridade", 99))):
            por_onda.setdefault(ondas[t["id"]], []).append(t)
        print(json.dumps(por_onda, ensure_ascii=False, indent=2))
        return

    print(f"fila · {len(tasks)} tasks · {max(ondas.values())+1 if ondas else 0} ondas")
    for t in sorted(tasks, key=lambda x: (ondas[x["id"]], x.get("prioridade", 99))):
        deps = ", ".join(t.get("blocked_by") or []) or "—"
        simbolo = {"todo": "□", "em_progresso": "◐", "feito": "✓"}.get(t["estado"], "?")
        print(f"  [{simbolo}] {t['id']:<10} onda {ondas[t['id']]}  pri {t.get('prioridade', 99):<2}  "
              f"{t['estado']:<12}  blocos: {deps}")
        print(f"            {t['titulo']}")


def cmd_proxima(dados: dict) -> None:
    r = resumo(dados)
    if r.get("erro"):
        print(f"ERRO: {r['erro']}", file=sys.stderr)
        sys.exit(1)
    proximas = r.get("proximas", [])
    if not proximas:
        print("nenhuma task pronta — tudo feito ou tudo bloqueado.")
        return
    print(f"próximas prontas ({r['prontas']} no total):")
    for p in proximas:
        print(f"  → {p['id']}  onda {p['onda']}  pri {p['prioridade']}  dono {p['dono']}  {p['titulo']}")


def cmd_avancar(dados: dict, task_id: str) -> None:
    for t in dados.get("tasks", []):
        if t["id"] == task_id:
            if t["estado"] == "feito":
                print(f"{task_id} já está feito.")
                return
            t["estado"] = "feito"
            print(f"{task_id} → feito")
            return
    raise ValueError(f"task não encontrada: {task_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="raiz da central")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("listar", help="lista todas as tasks agrupadas por onda")
    sub.add_parser("proxima", help="mostra as tasks prontas para começar")
    sub.add_parser("json", help="dump do resumo em JSON")
    p_avancar = sub.add_parser("avancar", help="marca uma task como feita")
    p_avancar.add_argument("id", help="id da task")
    args = ap.parse_args()

    raiz = Path(args.dir).resolve() if args.dir else _central()
    caminho = raiz / "dados" / "fila.json"

    # "avancar" é read-modify-write: a trava começa ANTES da leitura. Travar
    # só no save ainda permitiria duas execuções perderem a atualização uma da
    # outra.
    agente_arquivo = trava.agente_script("mb-fila")
    contexto = (trava.travado(caminho, agente_arquivo, "avança task da fila")
                if args.cmd == "avancar" else nullcontext())

    try:
        with contexto:
            dados = _carregar(caminho)
            if args.cmd == "listar":
                cmd_listar(dados)
            elif args.cmd == "json":
                print(json.dumps(resumo(dados), ensure_ascii=False, indent=2))
            elif args.cmd == "proxima":
                cmd_proxima(dados)
            elif args.cmd == "avancar":
                cmd_avancar(dados, args.id)
                _salvar(caminho, dados)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, trava.TravaOcupada) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
