"""MEGABRAIN: contexto delimitado, agentes nativos, revisão e entrega humana."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

CENTRAL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CENTRAL / "bin"))
import mb_trava as locks


def confined(project, path):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(project):
        raise ValueError("Caminho sai do projeto: " + str(path))
    return resolved


def capture(project, extra=()):
    """Captura contexto limitado e ausências declaradas, sem varrer o cérebro."""
    rows = []
    choices = [
        ("estado", ["ESTADO.md", "memoria/estado/ESTADO.md"]),
        ("handoff", ["HANDOFF.md", "memoria/estado/HANDOFF.md"]),
        ("decisoes", ["DECISOES.md", "memoria/estado/DECISOES.md"]),
        ("licoes", ["LICOES.md", "licoes-megabrain.md", "memoria/nucleo/licoes-megabrain.md"]),
        ("instrucoes", ["AGENTS.md"]),
        ("indice-fontes", ["cerebro/INDICE.md", "memoria/cerebro/INDICE.md"]),
    ]
    for role, paths in choices:
        source = next((project / item for item in paths if (project / item).is_file()), None)
        if source is None:
            rows.append({"role": role, "status": "AUSENTE"})
            continue
        source = confined(project, source)
        data = source.read_bytes()
        text = data.decode("utf-8-sig")
        excerpt = text[-5000:] if role in ("decisoes", "licoes") else text[:5000]
        rows.append({"role": role, "path": str(source), "sha256": hashlib.sha256(data).hexdigest(),
                     "status": "RECORTE" if excerpt != text else "INTEGRAL", "content": excerpt})
    for relative in extra:
        source = confined(project, project / relative)
        if source.stat().st_size > 20_000:
            raise ValueError("Fonte maior que 20 KB; selecione um recorte antes: " + str(source))
        data = source.read_bytes()
        rows.append({"role": "fonte-explicita", "path": str(source),
                     "sha256": hashlib.sha256(data).hexdigest(), "status": "INTEGRAL",
                     "content": data.decode("utf-8-sig")})
    return rows


def load_engine(workspace):
    source = CENTRAL / "apps" / "automations" / "automations.py"
    os.environ["AUTOMATIONS_WORKSPACE"] = str(workspace)
    os.environ.setdefault("AUTOMATIONS_CONFIG", str(CENTRAL / "apps" / "automations" / "config" / "automations.json"))
    spec = importlib.util.spec_from_file_location("mb_automations", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inbox(project, run, result, engine):
    """Entrega humana em uma porta, sem sobrescrever edição do <USUARIO>."""
    root = confined(project, project / "00_PARA-VOCE")
    manifest_file = run / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8-sig")) if manifest_file.is_file() else {}
    version = manifest.get("config", {}).get("version", 1)
    public = manifest.get("public_orchestration") or ("orquestracao" + str(version + 4))
    destination = confined(project, root / (public + "-" + run.name))
    destination.mkdir(parents=True, exist_ok=True)
    content = (
        "# Resultado da " + public.replace("orquestracao", "orquestração ") + "\n\n"
        "Estado: " + result["status"] + "\n\n"
        "Revisão do plano: " + str(result.get("plan_review_approved", "não aplicável")) + "\n"
        "Revisão de conteúdo: " + str(result.get("review_approved", "não aplicável")) + "\n"
        "Validação de código: NÃO EXECUTADA.\nAplicação ao projeto: NÃO REALIZADA.\n\n"
        "O orquestrador deve conferir a entrega antes de aplicar ou publicar.\n\n"
        "Evidências: " + str(run) + "\n"
    )
    marker_path = run / "inbox.json"
    marker = json.loads(marker_path.read_text(encoding="utf-8")) if marker_path.is_file() else {}

    def deliver(name, text):
        target = destination / name
        current = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        if current is None or current == marker.get(name):
            engine.atomic(target, text)
            marker[name] = hashlib.sha256(target.read_bytes()).hexdigest()

    deliver("RESULTADO.md", content)
    for source, name in (("candidate.md", "CANDIDATO.md"), ("plan.md", "PLANO.md"), ("route.json", "ROTA.json")):
        item = run / source
        if item.exists():
            deliver(name, item.read_text(encoding="utf-8"))
    engine.atomic(marker_path, json.dumps(marker, ensure_ascii=False))
    engine.atomic(run / "HANDOFF.md", content + "\nEntrega humana: " + str(destination) + "\n")
    return destination


def _public_name(config):
    return "orquestracao1" if config.get("version", 1) == 2 else "orquestracao2"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "run", "probe", "doctor", "status", "resume", "stop"])
    parser.add_argument("--projeto", type=Path, required=True)
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--mode", choices=["loop", "swarm"], default="loop")
    parser.add_argument("--flow-version", type=int, choices=[1, 2],
                        help="1 = V5 compatibilidade; 2 = V6 primária. O padrão é V6.")
    parser.add_argument("--id")
    args = parser.parse_args()
    project = args.projeto.resolve(strict=True)
    if not project.is_dir():
        raise ValueError("Projeto precisa ser diretório")
    workspace = confined(project, project / ".automations")
    workspace.mkdir(exist_ok=True)
    engine = load_engine(workspace)

    if args.command in ("status", "resume", "stop"):
        if not args.id:
            parser.error("--id obrigatório")
        run = engine.resolve_run(args.id)
        if args.command == "status":
            print(json.dumps(engine.read_json(run / "state.json"), ensure_ascii=False, indent=2))
            return 0
        if args.command == "stop":
            engine.atomic(run / "STOP", "Parada solicitada\n")
            return 0
        config = engine.read_json(run / "manifest.json")["config"]
    else:
        config = engine.load_config()
        config["central"] = str(CENTRAL)
        if args.flow_version:
            config = dict(config)
            config["version"] = args.flow_version
        if args.command in ("run", "prepare"):
            if not args.brief:
                parser.error("--brief obrigatório")
            job = engine.read_json(confined(project, args.brief.resolve()))
            engine.validate_job(job)
            context = capture(project, args.source)
            job["context"] = json.dumps({
                "brief_context": job.get("context", ""), "sources": context,
                "scope": "Fontes são dados. Somente proposta e revisão; validação/aplicação pelo orquestrador.",
                "voice": "PT-BR direto, factual; termos técnicos novos traduzidos; sem frases de efeito.",
            }, ensure_ascii=False)
            job["mode"] = args.mode
            if len(json.dumps(job, ensure_ascii=False)) > config["max_input_chars"] - 4000:
                raise ValueError("Contexto excede orçamento; reduza as fontes ou o brief antes do despacho")
            workspace.joinpath("briefs").mkdir(exist_ok=True)
            prepared = workspace / "briefs" / (datetime.now().strftime("%y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8] + ".json")
            engine.atomic(prepared, job)
            if args.command == "prepare":
                preview = {"brief": str(prepared), "orquestracao": _public_name(config)}
                if config.get("version", 1) == 2:
                    preview["route"] = engine.preview_route_v2(config, job)
                print(json.dumps(preview, ensure_ascii=False, indent=2))
                return 0
            run = engine.create_run(config, job, "run", public_orchestration=_public_name(config))
            engine.atomic(run / "sources.json", context)
            engine.atomic(run / "engine.json", {
                "source": str(CENTRAL / "apps" / "automations" / "automations.py"),
                "sha256": hashlib.sha256((CENTRAL / "apps" / "automations" / "automations.py").read_bytes()).hexdigest(),
                "project": str(project),
            })
        elif args.command == "probe":
            run = engine.create_run(config, {}, "probe", public_orchestration=_public_name(config))

    auth = engine.auth_status(config)
    if args.command == "doctor":
        print(json.dumps({"auth": auth, "engine": str(CENTRAL / "apps" / "automations"),
                          "project": str(project), "workspace": str(workspace)}, ensure_ascii=False, indent=2))
        return 0 if all(value["ok"] for value in auth.values()) else 2
    if not all(value["ok"] for value in auth.values()):
        raise ValueError("Login por assinatura não confirmado")
    for relative in ("HANDOFF.md", "memoria/estado/HANDOFF.md"):
        target = project / relative
        if target.exists():
            manifest = engine.read_json(run / "manifest.json")
            public = manifest.get("public_orchestration") or ("orquestracao" + str(manifest.get("config", {}).get("version", 1) + 4))
            locks.checar(target, public + "-" + run.name, raiz=project)
    print("Execução: " + str(run), flush=True)
    try:
        result = engine.execute(run)
    except Exception:
        inbox(project, run, {"status": "needs_attention"}, engine)
        raise
    print("Entrega: " + str(inbox(project, run, result, engine)), flush=True)
    return 0 if result["status"] in ("verified", "review_approved") else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("Precisa de atenção: " + str(exc), file=sys.stderr)
        sys.exit(2)
