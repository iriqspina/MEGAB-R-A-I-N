"""Read-only data adapter for the personal MEGABRAIN dashboard."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def _json(path: Path) -> dict:
    try:
        value = json.loads(_read(path))
    except (json.JSONDecodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _first(text: str, label: str) -> str:
    pattern = rf"^{re.escape(label)}:\s*(.+)$"
    match = re.search(pattern, text, flags=re.MULTILINE | re.IGNORECASE)
    return match.group(1).strip() if match else "Não medido"


def _titles(text: str, limit: int = 4) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")][-limit:][::-1]


def _first_existing(paths: list[Path]) -> Path | None:
    return next((item for item in paths if item.is_file()), None)


def collect(path: str | Path) -> dict:
    """Return a small human-first model from a central or a project folder."""
    selected = Path(path).resolve()
    brain = selected / "MEGABRAIN" if (selected / "MEGABRAIN").is_dir() else selected
    state_path = _first_existing([selected / "dados" / "estado.json", brain / "dados" / "estado.json"])
    state = _json(state_path) if state_path else {}
    estado_path = _first_existing([selected / "memoria" / "estado" / "ESTADO.md", selected / "ESTADO.md",
                                   brain / "memoria" / "estado" / "ESTADO.md", brain / "ESTADO.md"])
    handoff_path = _first_existing([selected / "memoria" / "estado" / "HANDOFF.md", selected / "HANDOFF.md",
                                    brain / "memoria" / "estado" / "HANDOFF.md", brain / "HANDOFF.md"])
    decisions_path = _first_existing([selected / "memoria" / "estado" / "DECISOES.md", selected / "DECISOES.md",
                                      brain / "memoria" / "estado" / "DECISOES.md", brain / "DECISOES.md"])
    estado_md = _read(estado_path) if estado_path else ""
    handoff_md = _read(handoff_path) if handoff_path else ""
    decisions_md = _read(decisions_path) if decisions_path else ""
    status = state.get("estado") or {}
    meta = state.get("meta") or {}
    copies = (state.get("copias") or {}).get("itens") or []
    stale = [item for item in copies if not item.get("em_dia")]
    return {
        "selected": str(selected),
        "root": str(brain),
        "name": selected.name or "MEGABRAIN",
        "is_central": (brain / "apps").is_dir() and (brain / "memoria").is_dir(),
        "updated_at": state.get("gerado_em") or "Não medido",
        "tldr": status.get("tldr") or _first(estado_md, "TL;DR"),
        "blocker": status.get("bloqueio") or _first(estado_md, "BLOQUEIO"),
        "next_step": meta.get("proximo_passo") or _first(estado_md, "PRÓXIMO PASSO"),
        "lock": status.get("trava") or _first(handoff_md, "TRAVADO_POR"),
        "version": (state.get("versao") or {}).get("atual") or "Não medida",
        "git_dirty": (state.get("git") or {}).get("arquivos_sujos"),
        "projects_total": (state.get("copias") or {}).get("total"),
        "projects_current": (state.get("copias") or {}).get("em_dia"),
        "stale_projects": stale[:6],
        "recent_decisions": (state.get("decisoes") or {}).get("ultimas") or _titles(decisions_md),
        "handoff": _first(handoff_md, "PRÓXIMO PASSO"),
        "source_ok": bool(state),
        "snapshot_path": str(state_path) if state_path else "Não encontrado",
        "state_path": str(estado_path) if estado_path else "Não encontrado",
        "handoff_path": str(handoff_path) if handoff_path else "Não encontrado",
        "decisions_path": str(decisions_path) if decisions_path else "Não encontrado",
    }


def display_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%d/%m · %H:%M")
    except ValueError:
        return value
