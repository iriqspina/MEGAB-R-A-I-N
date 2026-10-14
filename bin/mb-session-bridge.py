#!/usr/bin/env python3
"""Register a MegaBrain session and request presentation in its native app.

Portable entry point for clients/hooks. A queued request is never proof that
the native window consumed it. Only the app can provide that receipt.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

CENTRAL = Path(__file__).resolve().parents[1]
BRIDGE_VERSION = "1.0.0"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _atomic(path: Path, row: dict) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def _session_lock(path: Path):
    """OS lock releases on process exit; a leftover file cannot block startup."""
    claim = path.with_suffix('.lock')
    fd = os.open(claim, os.O_CREAT | os.O_RDWR, 0o600)
    if os.name == "nt":
        import msvcrt
        def acquire():
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        def release():
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        def acquire():
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        def release():
            fcntl.flock(fd, fcntl.LOCK_UN)
    deadline = time.monotonic() + 2
    locked = False
    try:
        while True:
            try:
                acquire()
                locked = True
                if os.fstat(fd).st_size == 0:
                    os.lseek(fd, 0, os.SEEK_SET)
                    os.write(fd, b'0')
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise OSError('session_registration_busy') from None
                time.sleep(0.02)
        yield
    finally:
        try:
            if locked:
                release()
        finally:
            os.close(fd)


def _application(explicit: str | None, env: dict) -> str:
    value = explicit or env.get("MB_CLIENT_APP")
    if value:
        # A client name, never command lines, URLs, credentials or raw env.
        clean = "".join(c for c in value[:64] if c.isalnum() or c in " ._()-")
        return clean.strip() or "desconhecido"
    if env.get("CODEX_THREAD_ID"):
        return "Codex"
    return "desconhecido"


def connect(project: Path | str, *, central: Path = CENTRAL,
            application: str | None = None, session_id: str | None = None,
            hook: dict | None = None, source: str = "mb-session-bridge",
            no_open: bool = False, env: dict | None = None) -> dict:
    """Persist before invoking the launcher; repeat stable IDs do not reopen."""
    env = os.environ if env is None else env
    hook = hook or {}
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError("project_unavailable")
    identities = ((session_id, "argument"), (hook.get("session_id"), "hook.session_id"),
                  (env.get("MB_SESSION_ID"), "MB_SESSION_ID"),
                  (env.get("CODEX_THREAD_ID"), "CODEX_THREAD_ID"))
    raw, identity_source = next(((v, s) for v, s in identities if isinstance(v, str) and v.strip()),
                                (uuid.uuid4().hex, "invocation_uuid"))
    session_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    directory = Path(central) / "apps/megabrain-dashboard/data/session-connections"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{session_key}.json"
    with _session_lock(path):
        previous = {}
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(previous, dict):
                previous = {}
        except (OSError, ValueError):
            pass
        if previous.get("project_root") != str(project):
            previous["presentation_request_id"] = None
            previous["error"] = None
        now = _now()
        row = dict(schema_version=1, id=session_key, identity_source=identity_source,
                   project_root=str(project), application=_application(application or hook.get("application", hook.get("aplicacao")), env),
                   started_at=previous.get("started_at", now), updated_at=now,
                   source=source, bridge_version=BRIDGE_VERSION,
                   presentation_request_id=previous.get("presentation_request_id"),
                   presentation_state=previous.get("presentation_state", "unavailable") if previous.get("presentation_request_id") else "unavailable",
                   error=previous.get("error") if previous.get("presentation_request_id") else None)
        _atomic(path, row)
        if row["presentation_request_id"]:
            return row
        if no_open:
            row["error"] = "presentation_not_requested"
        else:
            app = Path(central) / "apps/megabrain-dashboard"
            launcher = app / "bootstrap/MegaBrain.exe"
            if not launcher.is_file():
                row["error"] = "native_launcher_unavailable"
            else:
                try:
                    spec = importlib.util.spec_from_file_location("mb_presentation_bridge", Path(central) / "bin/mb-abrir-entrega.py")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    _, request = module.enqueue(project=project)
                    row.update(presentation_request_id=request["id"], presentation_state="queued")
                    _atomic(path, row)
                    subprocess.Popen([str(launcher)], cwd=app,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                except (OSError, ValueError, AttributeError, ImportError):
                    # Fixed message: exception details could expose environment secrets.
                    row["error"] = "native_presentation_unavailable"
                    row["presentation_state"] = "unavailable"
        _atomic(path, row)
        return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--application")
    parser.add_argument("--session-id")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--hook", action="store_true", help="read optional session_id/cwd JSON from stdin")
    args = parser.parse_args(argv)
    hook = read_hook(args.hook)
    try:
        hook_cwd = hook.get("cwd") if isinstance(hook.get("cwd"), str) else None
        hook_application = hook.get("application", hook.get("aplicacao"))
        row = connect(args.project or hook_cwd or Path.cwd(), application=args.application or (hook_application if isinstance(hook_application, str) else None),
                      session_id=args.session_id, hook=hook, no_open=args.no_open)
    except (OSError, ValueError):
        row = {"presentation_state": "unavailable", "error": "session_registration_unavailable"}
        print(json.dumps(row, ensure_ascii=False) if args.json else "Registro da sessão indisponível.")
        return 1
    print(json.dumps(row, ensure_ascii=False) if args.json else
          f"Sessão registrada no MegaBrain: {row['presentation_state']}. Abertura depende do recibo do aplicativo.")
    return 0


def read_hook(enabled: bool) -> dict:
    """Never consume stdin during a regular command invocation."""
    if enabled and not sys.stdin.isatty():
        try:
            value = json.load(sys.stdin)
            if isinstance(value, dict):
                return {key: value[key] for key in ("session_id", "cwd", "application", "aplicacao")
                        if isinstance(value.get(key), str)}
        except (ValueError, OSError):
            pass
    return {}


if __name__ == "__main__":
    raise SystemExit(main())
