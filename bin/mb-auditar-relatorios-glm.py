"""Mechanical report monitor: no models, no approval inference, no note mutation.

Scope is HTML in known projects' 00_PARA-VOCE. Direct app openings are outside
this command's enforcement. Baselines only identify unchanged legacy HTML;
they never certify quality. Pending corrections are a generated queue for the
next coordinated session, never an instruction to start a model automatically.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

CENTRAL = Path(__file__).resolve().parents[1]
SCHEMA = 1
EXCLUDED = {"node_modules", ".git", ".venv", "backup", "backups", "private",
            "privado", "privados", "privadas", "secrets", "credenciais", "__pycache__"}


def _stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _hash(path):
    with Path(path).open("rb") as stream:
        result = hashlib.file_digest(stream, "sha256")
    return result.hexdigest()


def _json(path, default=None):
    path = Path(path)
    if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
        raise ValueError("Arquivo tecnico ligado por symlink/junction proibido")
    if path.exists() and path.stat().st_nlink != 1:
        raise ValueError("Arquivo tecnico com hardlink proibido")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default


def _save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".audit-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _technical(project):
    project = Path(project).resolve(strict=True)
    target = project / ".automations/relatorios-glm"
    for cursor in (project / ".automations", target, project / ".mb-lock"):
        if cursor.is_symlink() or getattr(cursor, "is_junction", lambda: False)():
            raise ValueError("Raiz tecnica symlink/junction proibida")
        if not cursor.resolve().is_relative_to(project):
            raise ValueError("Raiz tecnica fora do projeto")
    return target


def project_for(path):
    path = Path(path).resolve(strict=True)
    for parent in path.parents:
        if parent.name.casefold() == "00_para-voce":
            return parent.parent
    return None


def report_paths(project):
    project = Path(project).resolve(strict=True)
    base = project / "00_PARA-VOCE"
    if not base.is_dir():
        return []
    result = []
    for directory, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d.casefold() not in EXCLUDED
                         and not d.casefold().startswith(("backup-", "backup_"))
                         and not (Path(directory) / d).is_symlink()
                         and not getattr(Path(directory) / d, "is_junction", lambda: False)())
        for name in sorted(files):
            path = Path(directory) / name
            if path.suffix.lower() not in {".html", ".htm"} or path.is_symlink():
                continue
            resolved = path.resolve(strict=True)
            if resolved.is_relative_to(project) and resolved.is_file():
                result.append(resolved)
    return result


def projects_in(root):
    root = Path(root).resolve(strict=True)
    roots = [root] if (root / "00_PARA-VOCE").is_dir() else []
    for child in sorted(root.iterdir(), key=lambda p: p.name.casefold()):
        if child.is_dir() and not child.name.startswith(".") and not child.is_symlink() \
                and not getattr(child, "is_junction", lambda: False)() \
                and (child / "00_PARA-VOCE").is_dir():
            roots.append(child.resolve())
    return list(dict.fromkeys(roots))


def freeze_baseline(project):
    """Explicit rollout snapshot; refuse replacement to prevent laundering changes."""
    project = Path(project).resolve(strict=True)
    path = _technical(project) / "baseline.json"
    if path.exists():
        value = _json(path)
        if value.get("schema") != SCHEMA or value.get("project") != str(project):
            raise ValueError("Baseline existente invalida; nao foi sobrescrita")
        return value
    rows = {str(p.relative_to(project)): _hash(p) for p in report_paths(project)}
    value = {"schema": SCHEMA, "project": str(project), "frozen_at": _stamp(),
             "scope": "HTML somente; legado nao significa conformidade", "reports": rows}
    # Exclusive creation: another observer must not replace a frozen baseline.
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return value


def _gate_module():
    if str(CENTRAL / "bin") not in sys.path:
        sys.path.insert(0, str(CENTRAL / "bin"))
    import mb_relatorios_glm
    return mb_relatorios_glm


def inspect_report(path, *, project=None):
    """Read-only check; a registered report fails closed on gate errors."""
    path = Path(path).resolve(strict=True)
    project = Path(project).resolve(strict=True) if project else project_for(path)
    if project is None or not path.is_relative_to(project / "00_PARA-VOCE"):
        return {"path": str(path), "status": "NAO_VERIFICADO_FORA_ESCOPO", "blocked": False,
                "reason": "Fora de 00_PARA-VOCE; nenhum manifesto ou conformidade presumidos"}
    rel = str(path.relative_to(project))
    row = {"path": str(path), "report": rel, "sha256": _hash(path), "blocked": False}
    base = _technical(project)
    try:
        previous = _json(base / "auditoria.json", {}).get("reports", {}).get(rel, {})
        if previous.get("manifest"):
            row["manifest"] = previous["manifest"]
        index = _json(base / "index.json", {})
        if isinstance(index, dict) and rel in index.get("reports", {}):
            row["registration_observed"] = True
        elif previous.get("registration_observed"):
            row["registration_observed"] = True
        gate = _gate_module()
        manifest = gate.find_manifest(project, path)
        if manifest is not None:
            before = _hash(manifest)
            checked = gate.status(project, manifest)
            if before != _hash(manifest) or row["sha256"] != _hash(path):
                raise ValueError("Relatorio ou manifesto mudou durante a auditoria; repetir leitura")
            row.update(manifest=str(manifest.relative_to(project)), manifest_sha256=before,
                       artifact_sha256=checked.get("artifact_sha256"), cycle=checked.get("cycle"))
            if checked.get("state") != "ready" or not checked.get("delivered_at"):
                row.update(status="BLOQUEADO", blocked=True, reason=checked.get("reason") or "Gate incompleto")
            else:
                row.update(status="CONFORME", reason="Gate independente e provas atuais conferidos; nao e aprovacao humana")
            return row
        baseline = _json(base / "baseline.json", {})
        old = baseline.get("reports", {}).get(rel)
        if old == row["sha256"]:
            row.update(status="LEGADO_NAO_AUDITADO", reason="HTML igual ao baseline; legado sem prova de conformidade")
        elif old:
            row.update(status="NAO_VERIFICADO_ALTERADO", blocked=True, reason="HTML alterado desde baseline, sem manifesto GLM associado")
        else:
            row.update(status="NAO_VERIFICADO", blocked=True, reason="Sem manifesto GLM e sem heranca comprovada no baseline")
        # A broken/deleted registration may never silently become legacy.
        if row.get("manifest") or row.get("registration_observed"):
            row.update(status="BLOQUEADO", blocked=True,
                       reason="Associacao de manifesto removida; registro anterior preservado")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ImportError) as exc:
        row.update(status="BLOQUEADO", blocked=True, reason="Auditoria indisponivel: " + str(exc))
    return row


def _persist_unlocked(project, rows, *, complete=False):
    """Rewrite machine-owned observations/queue only on a semantic change."""
    project = Path(project).resolve(strict=True)
    base = _technical(project)
    state_path = base / "auditoria.json"
    old = _json(state_path, {})
    if old and (old.get("schema") != SCHEMA or old.get("project") != str(project)):
        raise ValueError("Estado de auditoria desconhecido; nao sera sobrescrito")
    reports = dict(old.get("reports", {}))
    incoming = {r["report"]: r for r in rows if "report" in r}
    if complete:
        for rel in reports.keys() - incoming.keys():
            reports[rel] = {**reports[rel], "status": "INDISPONIVEL", "blocked": True,
                            "reason": "Arquivo antes observado nao esta acessivel; nenhuma nota foi removida"}
    reports.update(incoming)
    pending = [r for _, r in sorted(reports.items()) if r["status"] not in {"CONFORME", "LEGADO_NAO_AUDITADO"}]
    queue_path = base / "fila-correcao.json"
    prior = _json(queue_path, {})
    if prior and prior.get("generated_by") != "mb-auditar-relatorios-glm":
        raise ValueError("Fila existente nao pertence ao monitor; nao foi sobrescrita")
    if reports == old.get("reports", {}) and prior.get("items", []) == pending:
        return False
    state = {"schema": SCHEMA, "project": str(project), "updated_at": _stamp(), "reports": reports}
    _save(state_path, state)
    _save(queue_path, {"schema": SCHEMA, "generated_by": "mb-auditar-relatorios-glm",
                       "project": str(project), "updated_at": state["updated_at"],
                       "instruction": "Proximo ciclo coordenado: GLM corrige, Codex/Claude verificam. Nao iniciar modelo automaticamente.",
                       "items": pending})
    return True


def _persist(project, rows, *, complete=False):
    if str(CENTRAL / "bin") not in sys.path:
        sys.path.insert(0, str(CENTRAL / "bin"))
    import mb_trava
    project = Path(project).resolve(strict=True)
    target = _technical(project) / "auditoria.json"
    with mb_trava.travado(target, f"monitor-glm:{os.getpid()}:{uuid.uuid4().hex}", "auditoria mecanica de relatorios", raiz=project):
        return _persist_unlocked(project, rows, complete=complete)


def audit_report(path, *, write=True):
    project = project_for(path)
    row = inspect_report(path, project=project)
    if write and project:
        _persist(project, [row])
    return row


def audit(project=None, root=None, *, freeze=False, write=True):
    if project is not None and root is not None:
        raise ValueError("Use project ou root, nunca ambos")
    projects = [Path(project).resolve(strict=True)] if project is not None else projects_in(root or CENTRAL.parent)
    result = []
    for current in projects:
        if freeze:
            freeze_baseline(current)
        rows = [inspect_report(path, project=current) for path in report_paths(current)]
        try:
            index = _json(_technical(current) / "index.json", {})
        except (OSError, ValueError):
            index = {}  # Per-report rows already report the invalid index.
        for rel in index.get("reports", {}) if isinstance(index, dict) and isinstance(index.get("reports"), dict) else ():
            if rel not in {r["report"] for r in rows}:
                rows.append({"path": str(current / rel), "report": rel, "manifest": index["reports"][rel],
                             "registration_observed": True, "status": "INDISPONIVEL", "blocked": True,
                             "reason": "Relatorio registrado ausente ou fora da consulta; retornar ao coordenador"})
        changed = _persist(current, rows, complete=True) if write else False
        result.append({"project": str(current), "changed": changed, "reports": rows,
                       "queue": str(_technical(current) / "fila-correcao.json")})
    return {"schema": SCHEMA, "scope": "Projetos enumerados; abertura direta no app nao e bloqueada por este monitor",
            "model_calls": 0, "projects": result, "changed": any(p["changed"] for p in result)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--project")
    group.add_argument("--root")
    parser.add_argument("--freeze-baseline", action="store_true")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_baseline and args.read_only:
        parser.error("Baseline grava fonte; retire --read-only")
    result = audit(args.project, args.root, freeze=args.freeze_baseline, write=not args.read_only)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result["changed"] or args.read_only:
        count = sum(len(p["reports"]) for p in result["projects"])
        action = "somente leitura, nenhum estado gravado" if args.read_only else "fila atualizada apos mudanca observada"
        print(f"Monitor GLM: {count} HTML observados; zero chamadas de IA; {action}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
