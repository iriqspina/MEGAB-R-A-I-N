"""Escreve o ritmo calculado em dados/orcamento_ia.json — arquivo compartilhado
com o motor de orquestração (apps/automations), lido pelo pet (pets/backend).

Escrita é merge-read-write com troca atômica de arquivo (``os.replace``), porque
dois processos (este widget e o motor) podem escrever chaves diferentes do
mesmo arquivo. Nunca levanta: é telemetria consultiva, uma falha de disco aqui
não pode derrubar o polling do widget.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from . import paths


def write(provider: str, pacing: dict[str, Any]) -> None:
    path = paths.BUDGET_STATUS_PATH
    try:
        current: dict[str, Any] = {}
        if path.exists():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                current = {}
        if not isinstance(current, dict):
            current = {}
        current[provider] = {
            "pacing": pacing,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
        tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass
