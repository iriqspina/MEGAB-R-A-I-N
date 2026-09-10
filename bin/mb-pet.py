#!/usr/bin/env python3
"""Integra o launcher MEGABRAIN Pets sem depender de caminhos pessoais.

O comando é stdlib pura para continuar disponível nos projetos sincronizados.
Ele não instala silenciosamente: a oferta só aparece num terminal interativo e
registra a escolha por versão no diretório privado do usuário.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_NAME = "MegabrainPets"
EXE_NAME = "MegabrainPets.exe"
DEFAULT_VERSION = "0.1.0-dev"
OFFER_FILE = "integration-offer.json"


def _utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def central(explicit: str | Path | None = None) -> Path:
    """Resolve a central por argumento, ambiente ou pela posição deste script."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("MEGABRAIN_CENTRAL") or os.environ.get("MEGABRAIN_HOME")
    if env:
        return Path(env).expanduser().resolve()
    script = Path(__file__).resolve()
    for base in (script.parent.parent, *script.parents):
        if (base / "pets").is_dir() and (base / "bin").is_dir():
            return base
    return script.parent.parent


def data_dir(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("MEGABRAIN_PETS_DATA_DIR")
    if env:
        return Path(env).expanduser().resolve()
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return (Path(local) / APP_NAME).resolve()
    return (Path.home() / ".megabrain-pets").resolve()


def app_version(root: Path, override: str | None = None) -> str:
    if override:
        return override
    for candidate in (root / "pets" / "VERSION.txt", root / "VERSAO.txt"):
        try:
            first = candidate.read_text(encoding="utf-8-sig").splitlines()[0].strip()
        except (OSError, IndexError):
            continue
        match = re.search(r"\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z.-]+)?", first)
        if match:
            return match.group(0)
    return DEFAULT_VERSION


def executable_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("MEGABRAIN_PETS_EXE"):
        candidates.append(Path(os.environ["MEGABRAIN_PETS_EXE"]).expanduser())
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates.append(Path(local) / "Programs" / APP_NAME / EXE_NAME)
    candidates.extend((
        root / "pets" / "dist" / "app" / EXE_NAME,
        root / "pets" / "desktop" / "bin" / "Release" /
        "net10.0-windows" / "win-x64" / "publish" / EXE_NAME,
    ))
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            unique.append(resolved)
            seen.add(key)
    return unique


def find_executable(root: Path) -> Path | None:
    return next((path for path in executable_candidates(root) if path.is_file()), None)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")
    os.replace(temp, path)


def offer_state(folder: Path) -> dict[str, Any]:
    return _read_json(folder / OFFER_FILE)


def settings(root: Path, folder: Path, version: str) -> dict[str, Any]:
    exe = find_executable(root)
    offer = offer_state(folder)
    installed = bool(exe and os.environ.get("LOCALAPPDATA") and
                     _is_relative_to(exe, Path(os.environ["LOCALAPPDATA"]) / "Programs" / APP_NAME))
    return {
        "version": version,
        "central": str(root),
        "data_dir": str(folder),
        "executable": str(exe) if exe else None,
        "available": exe is not None,
        "installed_for_user": installed,
        "offer": offer or None,
    }


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except (OSError, ValueError):
        return False


def _powershell() -> str:
    return os.environ.get("MEGABRAIN_POWERSHELL") or "powershell.exe"


def install(root: Path, version: str) -> int:
    script = root / "pets" / "scripts" / "install.ps1"
    package = root / "pets" / "dist" / "app"
    if not script.is_file():
        print(f"ERRO: instalador ausente: {script}", file=sys.stderr)
        return 2
    if not (package / EXE_NAME).is_file():
        print(f"ERRO: pacote ainda não está pronto: {package / EXE_NAME}", file=sys.stderr)
        return 2
    result = subprocess.run([
        _powershell(), "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script), "-PackageRoot", str(package), "-Version", version,
    ], check=False)
    return result.returncode


def handle_offer(root: Path, folder: Path, version: str, *, choice: str | None,
                 force: bool, non_interactive: bool) -> int:
    marker = offer_state(folder)
    current = marker.get("choice")
    if not force and current == "never":
        print("Pets: oferta desativada pelo usuário.")
        return 0
    if not force and marker.get("version") == version and current in {"installed", "later"}:
        print(f"Pets: escolha '{current}' já registrada para a versão {version}.")
        return 0
    if find_executable(root) and current == "installed":
        print("Pets: aplicativo já disponível.")
        return 0

    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if choice is None and (non_interactive or not interactive):
        print("Pets: oferta ignorada porque esta execução não é interativa.")
        return 0
    if choice is None:
        print("\nMEGABRAIN Pets está disponível como instalação opcional por usuário.")
        print("  1. Instalar agora")
        print("  2. Lembrar numa próxima versão")
        print("  3. Nunca oferecer")
        answer = input("Escolha 1, 2 ou 3: ").strip().lower()
        choice = {"1": "install", "2": "later", "3": "never",
                  "instalar": "install", "depois": "later", "nunca": "never"}.get(answer)
        if choice is None:
            print("Pets: escolha inválida; nada foi alterado.")
            return 0

    recorded = choice
    if choice == "install":
        code = install(root, version)
        if code:
            return code
        recorded = "installed"
    _write_json(folder / OFFER_FILE, {
        "schema": 1,
        "choice": recorded,
        "version": version,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    messages = {
        "installed": "Pets: instalado para este usuário.",
        "later": f"Pets: oferta adiada até uma versão posterior à {version}.",
        "never": "Pets: novas ofertas foram desativadas.",
    }
    print(messages[recorded])
    return 0


def profiles(root: Path, folder: Path) -> list[dict[str, Any]]:
    """Lê perfis do banco do backend sem inicializá-lo nem escrever nele."""
    database = folder / "pets.sqlite3"
    if database.is_file():
        try:
            uri = database.resolve().as_uri() + "?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=2)
            try:
                rows = connection.execute(
                    "SELECT id,name FROM profiles ORDER BY created_at,id").fetchall()
            finally:
                connection.close()
            if rows:
                return [{"id": str(row[0]), "name": str(row[1]),
                         "source": str(database)} for row in rows]
        except (OSError, sqlite3.Error):
            # Banco ausente/inicializando: ainda dá para identificar o perfil-base.
            pass

    profile = root / "pets" / "Marcelinho" / "profile.json"
    item = _read_json(profile)
    if not item:
        return []
    return [{
        "id": str(item.get("id") or "marcelinho"),
        "name": str(item.get("name") or "Marcelinho"),
        "source": str(profile),
    }]


def launch(root: Path, *, profile: str | None = None, view: str | None = None,
           project: str | Path | None = None, data_folder: Path | None = None,
           wait: bool = False, extra: list[str] | None = None) -> int:
    exe = find_executable(root)
    if exe is None:
        print("ERRO: MegabrainPets.exe não encontrado.", file=sys.stderr)
        print("Procurei em:", file=sys.stderr)
        for candidate in executable_candidates(root):
            print(f"  - {candidate}", file=sys.stderr)
        print("Gere pets/dist/app ou instale o pacote por usuário.", file=sys.stderr)
        return 2
    command = [str(exe)]
    if profile:
        command.extend(["--pet", profile])
    if view:
        command.extend(["--view", view])
    if project:
        command.extend(["--project", str(Path(project).expanduser().resolve())])
    if data_folder:
        command.extend(["--data-dir", str(data_folder.resolve())])
    command.extend(extra or [])
    try:
        # O backend Python do app (neto deste processo) lê MEGABRAIN_CENTRAL pra
        # achar dados/orcamento_ia.json; sem isso ele só enxerga a env deste
        # shell, que nem sempre tem a variável — mesmo que este script já tenha
        # resolvido `root` por outro caminho (walk-up).
        env = {**os.environ, "MEGABRAIN_CENTRAL": str(root)}
        process = subprocess.Popen(command, cwd=str(exe.parent), env=env)
        return process.wait() if wait else 0
    except OSError as exc:
        print(f"ERRO: não consegui abrir {exe}: {exc}", file=sys.stderr)
        return 2


def _print_value(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        if not value:
            print("Nenhum perfil encontrado.")
        for item in value:
            print(f"{item['id']}: {item['name']} ({item['source']})")
        return
    for key, item in value.items():
        rendered = "sim" if item is True else "não" if item is False else item
        print(f"{key}: {rendered}")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Integração local do MEGABRAIN Pets")
    p.add_argument("--central", help="raiz da central; padrão: ambiente ou origem do script")
    p.add_argument("--data-dir", help="dados privados; padrão: LOCALAPPDATA/MegabrainPets")
    p.add_argument("--version", help="versão para o marcador da oferta")
    sub = p.add_subparsers(dest="command", required=True)

    status = sub.add_parser("settings", aliases=["status"], help="mostra o estado real")
    status.add_argument("--json", action="store_true")
    status.add_argument("--open", action="store_true", help="abre a tela de configurações")

    offer = sub.add_parser("offers", aliases=["offer"], help="oferta opcional persistente")
    offer.add_argument("--choice", choices=["install", "later", "never"])
    offer.add_argument("--force", action="store_true")
    offer.add_argument("--non-interactive", action="store_true")

    prof = sub.add_parser("profiles", help="lista perfis ou abre o gerenciador")
    prof.add_argument("--json", action="store_true")
    prof.add_argument("--open", action="store_true")

    start = sub.add_parser("start", help="abre o aplicativo")
    start.add_argument("--profile", "--pet", dest="profile")
    start.add_argument("--view")
    start.add_argument("--project", default=str(Path.cwd()),
                       help="projeto a anexar; padrão: pasta atual")
    start.add_argument("--wait", action="store_true")
    start.add_argument("app_args", nargs=argparse.REMAINDER)
    return p


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    args = parser().parse_args(argv)
    root = central(args.central)
    folder = data_dir(args.data_dir)
    version = app_version(root, args.version)
    if args.command in {"settings", "status"}:
        if args.open:
            return launch(root, view="settings", data_folder=folder)
        _print_value(settings(root, folder, version), args.json)
        return 0
    if args.command in {"offers", "offer"}:
        return handle_offer(root, folder, version, choice=args.choice,
                            force=args.force, non_interactive=args.non_interactive)
    if args.command == "profiles":
        if args.open:
            return launch(root, view="profiles", data_folder=folder)
        _print_value(profiles(root, folder), args.json)
        return 0
    if args.command == "start":
        return launch(root, profile=args.profile, view=args.view,
                      project=args.project, data_folder=folder, wait=args.wait,
                      extra=args.app_args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
