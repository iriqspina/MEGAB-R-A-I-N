"""Mede MCPs sem chamar modelo e publica somente estado redigido para o widget."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dados" / "saude_mcp.json"
CLAUDE = Path.home() / ".local" / "bin" / "claude.exe"


def status_from_line(line: str) -> tuple[str, str]:
    if "Needs authentication" in line:
        return "AUTH_REQUIRED", "autenticação necessária"
    if "trial has ended" in line:
        return "PLAN_REQUIRED", "plano encerrado"
    if "Failed to connect" in line or "CONNECTION_CLOSED" in line:
        return "UNREACHABLE", "conexão fechada"
    if "Connected" in line:
        return "OK", "conectado"
    return "NAO_MEDIDO", "estado não reconhecido"


def claude_mcps() -> list[dict]:
    if not CLAUDE.exists():
        return [{"name": "claude", "status": "UNREACHABLE", "level": "CONFIGURADO", "detail": "CLI ausente"}]
    proc = subprocess.run([str(CLAUDE), "mcp", "list"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=30,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    rows = []
    for raw in (proc.stdout + "\n" + proc.stderr).splitlines():
        if " - " not in raw:
            continue
        name, tail = raw.split(" - ", 1)
        if not name.strip() or name.startswith("Checking "):
            continue
        status, detail = status_from_line(tail)
        rows.append({"name": name.strip(), "status": status, "level": "INICIALIZADO" if status == "OK" else "CONFIGURADO", "detail": detail})
    return rows or [{"name": "claude", "status": "UNREACHABLE", "level": "CONFIGURADO", "detail": "sem resposta MCP"}]


def browser_state() -> list[dict]:
    chrome_host = Path(os.path.expandvars(r"%LOCALAPPDATA%\OpenAI\extension\com.openai.codexextension.json"))
    opera = Path(os.path.expandvars(r"%APPDATA%\Opera Software\Opera Stable"))
    return [
        {"name": "Chrome", "status": "OK" if chrome_host.exists() else "UNREACHABLE", "detail": "ponte nativa instalada" if chrome_host.exists() else "ponte nativa ausente"},
        {"name": "Opera", "status": "NAO_MEDIDO" if opera.exists() else "UNREACHABLE", "detail": "instalação existe; extensão não medida" if opera.exists() else "Opera ausente"},
    ]


def main() -> int:
    rows = claude_mcps()
    counts = {key: sum(item["status"] == key for item in rows) for key in ("OK", "AUTH_REQUIRED", "PLAN_REQUIRED", "UNREACHABLE", "NAO_MEDIDO")}
    payload = {"checked_at": datetime.now(timezone.utc).isoformat(), "servers": rows,
               "browsers": browser_state(), "summary": counts}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, OUTPUT)
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
