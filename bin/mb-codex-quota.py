#!/usr/bin/env python3
"""Lê os rate limits de um CODEX_HOME do codex CLI (via app-server JSON-RPC)
e grava o pacing em dados/orcamento_ia.json sob a chave escolhida.

Uso:
    python bin/mb-codex-quota.py <chave> <codex_home>
    python bin/mb-codex-quota.py codex_gpt2 "<USER_HOME>/.codex-gpt2"

Reutiliza o leitor do widget de cotas (apps/ia-quota-widget/providers.py) e o
cálculo de ritmo (budget_pacing.py). O CODEX_HOME é forçado via env antes do
import, porque o app-server herda o home do processo. Reutilizável pra qualquer
conta nova (3ª conta = mesmo comando com outra chave/home).
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

CENTRAL = Path(__file__).resolve().parent.parent
WIDGET = CENTRAL / "apps" / "ia-quota-widget"
BUDGET = CENTRAL / "dados" / "orcamento_ia.json"


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    key, home = sys.argv[1], Path(sys.argv[2])
    if not (home / "auth.json").is_file():
        print(f"[mb-codex-quota] {home} nao tem auth.json — rode `codex login` com CODEX_HOME={home}")
        return 1

    os.environ["CODEX_HOME"] = str(home)
    sys.path.insert(0, str(WIDGET))
    import providers  # noqa: E402  (import após setar CODEX_HOME)
    import budget_pacing  # noqa: E402

    result = providers.fetch_provider("codex")
    status = result.get("status")
    if status != "ok":
        print(f"[mb-codex-quota] fetch falhou: {status} — {result.get('message', '')}")
        return 1

    pacing = budget_pacing.provider_pacing(result)
    plan = result.get("message", "")
    current = {}
    if BUDGET.exists():
        try:
            current = json.loads(BUDGET.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    current[key] = {"pacing": pacing, "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    BUDGET.parent.mkdir(parents=True, exist_ok=True)
    tmp = BUDGET.with_name(BUDGET.name + "." + uuid.uuid4().hex + ".tmp")
    tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, BUDGET)

    windows = [(w.get("id"), w.get("used_percent"), w.get("resets_at")) for w in result.get("windows", [])]
    print(f"[mb-codex-quota] {key} ({plan}) gravado em dados/orcamento_ia.json")
    for wid, used, resets in windows:
        print(f"  {wid}: {used}% usado, reseta {resets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
