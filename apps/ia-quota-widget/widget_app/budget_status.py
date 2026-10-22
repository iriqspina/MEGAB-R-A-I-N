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
from json_io import update_json


def write(provider: str, pacing: dict[str, Any]) -> bool:
    path = paths.BUDGET_STATUS_PATH
    try:
        def merge(current):
            current[provider]={'pacing':pacing,'updated_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
            return current
        update_json(path,merge)
        return True
    except Exception:
        return False
