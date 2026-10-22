"""Local report evidence ledger. Never invokes a model or certifies visual truth.

The gate checks evidence completeness, identity separation and freshness. An
inspector remains responsible for what they actually saw in the screenshots.
"""
from __future__ import annotations

import copy
from contextlib import contextmanager
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import uuid
import zlib

import mb_trava

SCHEMA = 1
CENTRAL = Path(__file__).resolve().parents[1]
CRITERIA = {"understanding", "organization", "hierarchy", "functional_layout",
            "finalized_references", "factuality"}
MAX_SESSIONS = 3  # HEURISTIC, not a provider limit.
MAX_CORRECTIONS = 3  # HEURISTIC: original plus at most three refresh cycles.
STALE_SECONDS = 300  # HEURISTIC; missing age never becomes fresh.
CREDIT_THRESHOLD = 5  # HEURISTIC; percent remaining.
TRANSCRIPT_ROOT = Path.home() / ".claude" / "projects"  # transcripts written by the Claude Code client


class GateError(ValueError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc)


def stamp():
    return now().isoformat()


def required(value, field):
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{field}: texto explicito obrigatorio")
    return value.strip()


def moment(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError, AttributeError) as exc:
        raise GateError("Data ISO com fuso obrigatoria") from exc


def rooted(root, value, *, exists=True):
    """Reject traversal and links, including links that happen to stay in root."""
    root = Path(root).resolve(strict=True)
    raw = Path(value)
    if ".." in raw.parts:
        raise GateError("Path escape: '..' proibido")
    path = raw if raw.is_absolute() else root / raw
    resolved = path.resolve(strict=exists)
    if not resolved.is_relative_to(root):
        raise GateError(f"Path escape: {value}")
    _no_links(path, root)
    if exists and (not resolved.is_file() or resolved.stat().st_nlink != 1):
        raise GateError(f"Arquivo regular sem hardlink obrigatorio: {value}")
    return resolved


def _no_links(path, root):
    cursor = path
    while cursor != root and cursor != cursor.parent:
        if cursor.is_symlink() or (hasattr(cursor, "is_junction") and cursor.is_junction()):
            raise GateError(f"Link proibido: {path}")
        cursor = cursor.parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def reference(root, path):
    path = rooted(root, path)
    return {"path": str(path.relative_to(Path(root).resolve())), "sha256": digest(path)}


def read_json(root, path):
    ref = reference(root, path)
    try:
        value = json.loads(rooted(root, ref["path"]).read_text(encoding="utf-8-sig"))
    except (ValueError, UnicodeError) as exc:
        raise GateError("JSON invalido") from exc
    if not isinstance(value, dict):
        raise GateError("Objeto JSON obrigatorio")
    return value, ref


def evidence(root, values):
    if not isinstance(values, list) or not values:
        raise GateError("Evidencias em arquivos obrigatorias")
    return [reference(root, item) for item in values]


def actor(value):
    if not isinstance(value, dict):
        raise GateError("Identidade com vendor e session_id obrigatoria")
    return {k: required(value.get(k), k) for k in ("vendor", "session_id")}


def independent(value, producer):
    who = actor(value)
    if who["session_id"] == producer["session_id"]:
        raise GateError("Revisor/inspetor deve ser outra sessao real")
    if who["vendor"].lower() not in {"codex", "claude", "human"}:
        raise GateError("Revisao final requer Codex, Claude ou humano que veja a prova")
    return who


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ("src", "poster", "data"):
            if key in attrs:
                self.paths.append(attrs[key])
        if tag == "link" and "stylesheet" in attrs.get("rel", "").lower():
            self.paths.append(attrs.get("href", ""))
        if tag in {"image", "use", "feimage"}:
            self.paths.extend(attrs[key] for key in ("href", "xlink:href") if attrs.get(key))
        if attrs.get("srcset"):
            self.paths.extend(part.strip().split()[0] for part in attrs["srcset"].split(",") if part.strip())
        self.paths.extend(re.findall(r"url\(['\"]?([^)'\"]+)", attrs.get("style", "")))


def artifact(root, report, assets=()):
    """Track local rendered resources transitively; navigation links are excluded."""
    root = Path(root).resolve()
    pending = [rooted(root, report)] + [rooted(root, a) for a in assets]
    files, remote = {}, set()
    while pending:
        path = pending.pop()
        rel = str(path.relative_to(root))
        if rel in files:
            continue
        files[rel] = digest(path)
        if path.suffix.lower() not in {".html", ".htm", ".css", ".svg"}:
            continue
        text = path.read_text(encoding="utf-8-sig")
        resources = Resources()
        if path.suffix.lower() != ".css":
            resources.feed(text)
        refs = resources.paths + re.findall(r"url\(['\"]?([^)'\"]+)", text)
        refs += re.findall(r"@import\s+['\"]([^'\"]+)", text)
        for target in refs:
            if not target or target.startswith(("#", "data:")):
                continue
            if re.match(r"^(?:https?:)?//", target, flags=re.I):
                remote.add(target)
                continue
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, flags=re.I):
                raise GateError("Recurso com protocolo nao rastreavel")
            from urllib.parse import unquote
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            # Resource-relative '..' is allowed only after canonical resolution
            # has proved it remains inside this project.
            resource_path = path.parent / target
            _no_links(resource_path, root)
            resolved = resource_path.resolve(strict=True)
            pending.append(rooted(root, resolved))
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(canonical).hexdigest(), "files": files,
            "remote_resources": sorted(remote)}


def credit_exception(root, path, deadline, *, at=None):
    data, ref = read_json(root, path)
    at = at or now()
    when, due = moment(data.get("observed_at")), moment(deadline)
    if not 0 <= (at - when).total_seconds() <= STALE_SECONDS:
        raise GateError("Fonte de credito ausente, futura ou antiga")
    if due <= at:
        raise GateError("Prazo futuro explicito obrigatorio")
    required(data.get("account"), "account")
    if data.get("vendor") != "glm" or data.get("status") != "observed":
        raise GateError("Falha de ferramenta nao comprova credito extremo")
    if data.get("all_applicable_windows_confirmed") is not True:
        raise GateError("Todas as janelas aplicaveis precisam ser confirmadas")
    windows = data.get("windows")
    if not isinstance(windows, list) or not windows:
        raise GateError("Janelas de credito obrigatorias")
    extreme = False
    for window in windows:
        required(window.get("name"), "window.name")
        remaining = window.get("remaining_percent")
        if isinstance(remaining, bool) or not isinstance(remaining, (float, int)) or not 0 <= remaining <= 100:
            raise GateError("Credito desconhecido ou invalido")
        reset = window.get("reset_at")
        if reset is None:
            if window.get("reset_absence_confirmed") is not True:
                raise GateError("Ausencia de reset deve ser explicitamente confirmada")
            cannot_reset = True
        else:
            reset_time = moment(reset)
            if reset_time <= at:
                raise GateError("Reset antigo nao comprova ausencia de reset util")
            cannot_reset = reset_time > due
        if remaining <= CREDIT_THRESHOLD and cannot_reset:
            extreme = True
    if not extreme:
        raise GateError("Excecao exige janela restritiva <=5% e sem reset util antes do prazo")
    return {"source": ref, "data": data, "deadline": due.isoformat(),
            "threshold_percent": CREDIT_THRESHOLD, "threshold_kind": "HEURISTICA", "validated_at": at.isoformat()}


def production(root, path, exception=None, deadline=None, *, credit_at=None):
    data, ref = read_json(root, path)
    if data.get("status") != "completed" or data.get("exit_code") != 0 or isinstance(data.get("exit_code"), bool):
        raise GateError("Produtor nao terminou com evidencia completed e exit_code 0")
    who = actor(data)
    model = required(data.get("actual_model"), "actual_model")
    if who["vendor"] == "glm":
        if model != "GLM-5.3" or data.get("effort_requested") != "max" or data.get("effort_verified") is not True:
            raise GateError("GLM principal GLM-5.3 MAX real precisa estar provado")
        io = data.get("model_io_metadata")
        if not isinstance(io, list) or not io or any(
            row.get("body_effort") != "max" or row.get("provider_effort") != "max"
            or not isinstance(row.get("model"), dict)
            or row["model"].get("modelId") != "GLM-5.3" for row in io
        ):
            raise GateError("model_io_metadata de GLM principal/MAX obrigatoria")
        exception_data = None
    else:
        if who["vendor"] not in {"codex", "claude"} or not exception or not deadline:
            raise GateError("Produtor normal obrigatorio GLM; fallback exige excecao de credito")
        if who["vendor"] == "claude" and data.get("effort_requested") in {"max", "ultra"}:
            raise GateError("Claude MAX/ultra proibido nesta politica")
        exception_data = credit_exception(root, exception, deadline, at=credit_at)
    return {"actor": who, "actual_model": model, "source": ref, "exception": exception_data}


def _normalized(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def authorship(root, report, prod, fragment=None):
    result, _ = read_json(root, prod["source"]["path"])
    text = _normalized(required(result.get("text"), "result.text"))
    fence = re.fullmatch(r"```(?:html)?\s*\n(.*?)\n```", text, flags=re.S | re.I)
    if fence:
        text = _normalized(fence.group(1))
    final = _normalized(rooted(root, report).read_text(encoding="utf-8-sig"))
    if fragment:
        source = rooted(root, fragment)
        source_text = _normalized(source.read_text(encoding="utf-8-sig"))
        if source_text != text or not text or final.count(text) != 1:
            raise GateError("Fragmento deve ser a saida GLM literal inteira, presente uma vez no HTML final")
        return {"method": "compose-pop-cursor-history", "source": reference(root, source),
                "source_sha256": digest(source), "result": prod["source"],
                "target_sha256": digest(rooted(root, report)),
                "note": "Montagem mecanica nao altera a autoria substantiva; revisao deve conferir visibilidade"}
    if final != text:
        raise GateError("HTML difere da saida do produtor; montagem exige --fragment literal congelado")
    return {"method": "literal-output", "result": prod["source"],
            "target_sha256": digest(rooted(root, report))}


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".glm-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def manifest_path(root, value):
    path = rooted(root, value, exists=False)
    technical = Path(root).resolve() / "evidence"
    if not path.is_relative_to(technical) or path.suffix != ".json":
        raise GateError("Manifesto deve ficar em evidence/ com extensao .json")
    return path


def _index_path(root):
    return rooted(root, ".automations/relatorios-glm/index.json", exists=False)


def _load_index(root, path):
    data, _ = read_json(root, path)
    if data.get("schema") != SCHEMA or data.get("project") != str(Path(root).resolve()) or not isinstance(data.get("reports"), dict):
        raise GateError("Indice de relatorios corrompido ou de outro projeto")
    return data


def find_manifest(root, report):
    """No recursive evidence scan. Missing index is unknown, never compliant."""
    root = Path(root).resolve(strict=True)
    report = rooted(root, report)
    index = _index_path(root)
    if not index.exists():
        return None
    data = _load_index(root, index)
    rel = str(report.relative_to(root))
    manifest = data["reports"].get(rel)
    if manifest is None:
        return None
    path = manifest_path(root, manifest)
    if not path.exists():
        raise GateError("Manifesto associado ausente: registro permanece bloqueado")
    ledger, _ = read_json(root, path)
    if ledger.get("report") != rel or ledger.get("project") != str(root) or ledger.get("schema") != SCHEMA:
        raise GateError("Manifesto associado aponta para outro relatorio/projeto")
    return path


def _register(root, report, manifest):
    """Reserve association first. Partial failure leaves a blocked pointer."""
    index = _index_path(root)
    owner = f"mb-relatorios-glm-index:{os.getpid()}:{uuid.uuid4().hex}"
    with mb_trava.travado(index, owner, "indice tecnico de relatorios", raiz=root):
        data = _load_index(root, index) if index.exists() else {
            "schema": SCHEMA, "project": str(Path(root).resolve()), "reports": {}}
        rel = str(Path(report).relative_to(Path(root).resolve()))
        target = str(manifest_path(root, manifest).relative_to(Path(root).resolve()))
        previous = data["reports"].get(rel)
        if previous is not None and previous != target:
            raise GateError("Relatorio ja tem manifesto canonico; reutilize a associacao")
        data["reports"][rel] = target
        _atomic(index, data)


def transaction(root, value, operation, *, create=False, validate_current=True):
    root = Path(root).resolve(strict=True)
    path = manifest_path(root, value)
    owner = f"mb-relatorios-glm:{os.getpid()}:{uuid.uuid4().hex}"
    with mb_trava.travado(path, owner, "ledger de relatorios GLM", raiz=root):
        if create:
            if path.exists():
                raise GateError("Manifesto existente: use refresh, sem sobrescrever historia")
            data = None
        else:
            data, _ = read_json(root, path)
            if data.get("schema") != SCHEMA or data.get("project") != str(root):
                raise GateError("Manifesto de outro projeto/versao")
        result = operation(data)
        if validate_current:
            current(root, result)
        _atomic(path, result)
    return result


def _cycle(prod, art, number):
    return {"number": number, "created_at": stamp(), "production": prod,
            "artifact": art, "review": None, "visual": [], "tests": [],
            "inspection_history": [], "delivered_at": None, "promoted": [], "revocation": None}


def init(root, manifest, report, production_file, assets=(), exception=None, deadline=None, fragment=None):
    root = Path(root).resolve()
    report = rooted(root, report)
    if not report.is_relative_to(root / "00_PARA-VOCE") or report.suffix.lower() not in {".html", ".htm"}:
        raise GateError("Relatorio HTML deve ficar em 00_PARA-VOCE")
    def op(_):
        prod = production(root, production_file, exception, deadline)
        art = artifact(root, report, assets)
        cycle = _cycle(prod, art, 1)
        cycle["mechanical_integration"] = authorship(root, report, prod, fragment)
        _register(root, report, manifest)
        return {"schema": SCHEMA, "project": str(root), "report": str(report.relative_to(root)),
                "assets": [str(rooted(root, a).relative_to(root)) for a in assets],
                "current": cycle, "history": [], "requires_new_session": False}
    return transaction(root, manifest, op, create=True)


def current(root, data):
    if data.get("schema") != SCHEMA or data.get("project") != str(Path(root).resolve()):
        raise GateError("Manifesto de outro projeto/versao")
    for execution in data.get('executions',[]):
        _fresh_ref(root,execution['request_source'])
        if execution.get('human_event'):
            _fresh_ref(root,execution['human_event']['excerpt'])
    cycle = data["current"]
    actual = artifact(root, data["report"], data["assets"])
    if actual != cycle["artifact"]:
        raise GateError("Artefato alterado: prova invalidada; use refresh com nova producao GLM")
    _fresh_ref(root, cycle["production"]["source"])
    result, _ = read_json(root, cycle["production"]["source"]["path"])
    if actor(result) != cycle["production"]["actor"] or result.get("actual_model") != cycle["production"]["actual_model"]:
        raise GateError("Identidade de producao diverge da fonte real")
    prod = cycle["production"]
    if prod["actor"]["vendor"] == "glm":
        reconstructed_production = production(root, prod["source"]["path"])
    else:
        exception = prod.get("exception")
        if not exception:
            raise GateError("Produtor nao GLM exige excecao de credito preservada")
        _fresh_ref(root, exception["source"])
        validated_at = moment(exception.get("validated_at"))
        if not 0 <= (moment(cycle["created_at"]) - validated_at).total_seconds() <= STALE_SECONDS:
            raise GateError("Momento de validacao da excecao diverge da criacao do ciclo")
        reconstructed_production = production(root, prod["source"]["path"], exception["source"]["path"],
                                              exception["deadline"], credit_at=validated_at)
    if reconstructed_production != prod:
        raise GateError("Producao no manifesto diverge da fonte congelada")
    integration = cycle["mechanical_integration"]
    if integration.get("source"):
        _fresh_ref(root, integration["source"])
    if digest(rooted(root, data["report"])) != integration["target_sha256"]:
        raise GateError("Montagem mecanica alterada")
    reconstructed = authorship(root, data["report"], cycle["production"],
                              integration.get("source", {}).get("path"))
    if reconstructed != integration:
        raise GateError("Montagem no manifesto diverge da fonte literal")
    return cycle


def _fresh_ref(root, ref):
    if reference(root, ref["path"]) != ref:
        raise GateError(f"Evidencia alterada: {ref['path']}")


def _human_event(root, request, report, not_before):
    """Bind a reframe to one typed human message frozen inside the project.

    The excerpt must be the literal transcript line of a user message that
    names the report file as a whole token, written after the revoked
    candidate existed, and that line must exist in a transcript under
    TRANSCRIPT_ROOT. Local files are not signatures: this raises the cost of a
    fabricated authorization; it does not make one impossible.
    """
    source = request.get("human_event")
    if not isinstance(source, dict) or source.get("kind") != "claude_transcript":
        raise GateError("Reinicio exige evento humano real (claude_transcript)")
    event_uuid = required(source.get("event_uuid"), "human_event.event_uuid")
    excerpt = reference(root, required(source.get("excerpt"), "human_event.excerpt"))
    raw = rooted(root, excerpt["path"]).read_bytes().rstrip(b"\r\n")
    if b"\n" in raw:
        raise GateError("Trecho deve ser uma unica linha do transcript")
    try:
        line = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateError("Trecho do transcript invalido") from exc
    message = line.get("message") if isinstance(line.get("message"), dict) else {}
    content = message.get("content")
    if isinstance(content, list) and content and all(isinstance(b, dict) and b.get("type") == "text" for b in content):
        content = "\n".join(str(b.get("text", "")) for b in content)
    if (line.get("type") != "user" or message.get("role") != "user" or line.get("isMeta") or line.get("isSidechain")
            or not isinstance(content, str) or line.get("uuid") != event_uuid
            or line.get("sessionId") != request["session_id"]):
        raise GateError("Evento humano deve ser mensagem digitada pelo usuario na sessao declarada")
    if " ".join(request["human_request"].split()) not in " ".join(content.split()):
        raise GateError("Pedido humano difere do texto literal do evento")
    # Whole file name, optional .htm/.html; a trailing dot only as sentence end (REPORT.OUTRO.html is another file).
    name = r"(?<![\w.-])" + re.escape(Path(report).stem) + r"(?:\.[hH][tT][mM][lL]?)?(?=$|[^\w.-]|\.(?:\s|$))"
    if not re.search(name, content):
        raise GateError("Evento humano nao nomeia este relatorio")
    when = moment(line.get("timestamp"))
    if when < moment(not_before):
        raise GateError("Evento humano anterior ao candidato revogado; nao autoriza esta execucao")
    if when > now() + dt.timedelta(minutes=5):
        raise GateError("Evento humano com data futura")
    declared = Path(required(source.get("transcript"), "human_event.transcript"))
    if not declared.is_absolute():
        raise GateError("Transcript exige caminho absoluto")
    _no_links(declared, Path(TRANSCRIPT_ROOT))
    transcript = declared.resolve()
    if not transcript.is_relative_to(Path(TRANSCRIPT_ROOT).resolve()) or transcript.suffix != ".jsonl" or not transcript.is_file():
        raise GateError("Transcript fora da pasta do cliente Claude Code")
    with transcript.open("rb") as handle:
        if not any(row.rstrip(b"\r\n") == raw for row in handle):
            raise GateError("Trecho nao existe no transcript real")
    return {"kind": "claude_transcript", "transcript": str(transcript), "event_uuid": event_uuid,
            "timestamp": when.isoformat(), "line_sha256": hashlib.sha256(raw).hexdigest(), "excerpt": excerpt}


@contextmanager
def _consumed_events(central):
    """Shared registry: one human event authorizes one reframe in all projects."""
    path = rooted(central, ".automations/relatorios-glm/autorizacoes-humanas.json", exists=False)
    owner = f"mb-relatorios-glm-eventos:{os.getpid()}:{uuid.uuid4().hex}"
    with mb_trava.travado(path, owner, "autorizacoes humanas consumidas", raiz=central):
        registry, _ = read_json(central, path) if path.exists() else ({"schema": 1, "events": {}}, None)
        if registry.get("schema") != 1 or not isinstance(registry.get("events"), dict):
            raise GateError("Registro de autorizacoes humanas invalido; nao foi substituido")
        yield registry
        _atomic(path, registry)


def begin_task(root,manifest,request_file,*,central=CENTRAL):
    """Freeze a distinct human follow-up after a delivered task, preserving history.

    Does not approve an artifact or create production. A failed task without
    a delivered predecessor cannot renew its limits through this operation,
    except by an explicit human reframe (kind 'human_reframe', with reason and
    human_event) after the current candidate was formally revoked. The human
    event is consumed once in the central registry (reserved before the
    manifest write: a partial failure leaves it consumed, never reusable) and
    that execution accepts only GLM sessions never used earlier in this manifest.
    """
    request,ref=read_json(root,request_file)
    kind=request.get('kind')
    fields=('id','human_request','session_id','at')+(('reason',) if kind=='human_reframe' else ())
    if kind not in {'human_followup','human_reframe'} or not all(isinstance(request.get(k),str) and request[k].strip() for k in fields):
        raise GateError('Pedido humano distinto com origem e data obrigatorios')
    moment(request['at'])
    def op(data):
        executions=data.setdefault('executions',[])
        if any(x['request_source']==ref or x['id']==request['id'] for x in executions):
            raise GateError('Pedido ja registrado; nao renova limites da mesma tarefa')
        start=executions[-1]['start_cycle'] if executions else 1
        cycles=data['history']+[data['current']]
        delivered=[c['number'] for c in cycles if c.get('delivered_at') and c['number']>=start]
        if kind=='human_reframe':
            if delivered:raise GateError('Tarefa ja entregue: use human_followup, nao reinicio')
            if executions and executions[-1]['start_cycle']>data['current']['number']:
                raise GateError('Reinicio pendente: produza o novo ciclo antes de outro reinicio')
            if not data['current'].get('revocation'):raise GateError('Reinicio humano exige candidato atual revogado formalmente; nao contorna falha em aberto')
            event=_human_event(root,request,data['report'],data['current']['created_at'])
            if any(x.get('human_event',{}).get('event_uuid')==event['event_uuid'] for x in executions):
                raise GateError('Autorizacao humana ja consumida neste manifesto')
            with _consumed_events(Path(central).resolve(strict=True)) as registry:
                if event['event_uuid'] in registry['events']:
                    raise GateError('Autorizacao humana ja consumida por outro relatorio ou manifesto')
                registry['events'][event['event_uuid']]={'project':str(Path(root).resolve()),'report':data['report'],
                    'manifest':str(manifest_path(root,manifest)),'revoked_cycle':data['current']['number'],
                    'line_sha256':event['line_sha256'],'consumed_at':stamp()}
            boundary=data['current']['number']+1
            executions.append({'id':request['id'],'kind':'human_reframe','start_cycle':boundary,'previous_revoked_cycle':boundary-1,
                               'excluded_sessions':sorted({c['production']['actor']['session_id'] for c in cycles}),
                               'human_event':event,'request_source':ref,'registered_at':stamp()})
            data['requires_new_session']=False
            return data
        if not delivered:raise GateError('Nova tarefa exige tarefa anterior entregue; nao contorna falha em aberto')
        boundary=max(delivered)+1
        request_dir=rooted(root,request_file).parent
        for cycle in data['history']+[data['current']]:
            if cycle['number']>=boundary and not rooted(root,cycle['production']['source']['path']).is_relative_to(request_dir):
                raise GateError('Ciclos abertos nao pertencem ao novo pedido congelado')
        executions.append({'id':request['id'],'start_cycle':boundary,'previous_delivered_cycle':boundary-1,'request_source':ref,'registered_at':stamp()})
        if not any(c['number']>=boundary for c in data['history']+[data['current']]):
            data['requires_new_session']=False
        return data
    return transaction(root,manifest,op,validate_current=False)


def refresh(root, manifest, production_file, exception=None, deadline=None, fragment=None):
    def op(data):
        old = data["current"]
        start=data.get('executions',[])[-1]['start_cycle'] if data.get('executions') else 1
        if old["number"]-start >= MAX_CORRECTIONS:
            raise GateError("Limite de tres correcoes atingido; parar e reenquadrar [HEURISTICA]")
        if old["review"] is None:
            raise GateError("Revisao anterior obrigatoria antes de novo ciclo")
        prod = production(root, production_file, exception, deadline)
        if any(c["production"]["source"]["path"] == prod["source"]["path"]
               for c in data["history"] + [old]):
            raise GateError("Preserve cada result.json em caminho proprio, sem sobrescrever o historico")
        if fragment:
            relative_fragment = str(rooted(root, fragment).relative_to(Path(root).resolve()))
            if any(c["mechanical_integration"].get("source", {}).get("path") == relative_fragment
                   for c in data["history"] + [old]):
                raise GateError("Preserve cada fragmento GLM em caminho proprio")
        previous = old["production"]["actor"]["session_id"]
        latest = prod["actor"]["session_id"]
        if data["requires_new_session"] and latest == previous:
            raise GateError("Duas correcoes sem melhora: nova sessao GLM obrigatoria [HEURISTICA]")
        execution = data["executions"][-1] if data.get("executions") else {}
        if latest in execution.get("excluded_sessions", ()):
            raise GateError("Reinicio humano exige sessao GLM inedita neste manifesto")
        sessions = {c["production"]["actor"]["session_id"] for c in data["history"] + [old] if c['number']>=start}
        if latest not in sessions and len(sessions) >= MAX_SESSIONS:
            raise GateError("Limite de tres sessoes atingido; parar e reenquadrar [HEURISTICA]")
        art = artifact(root, data["report"], data["assets"])
        if art == old["artifact"]:
            raise GateError("Nova producao sem mudanca do artefato")
        data["history"].append(copy.deepcopy(old))
        data["current"] = _cycle(prod, art, old["number"] + 1)
        data["current"]["mechanical_integration"] = authorship(root, data["report"], prod, fragment)
        data["requires_new_session"] = False
        return data
    return transaction(root, manifest, op)


def revise(root, manifest, review_file):
    def op(data):
        cycle = current(root, data)
        if cycle["delivered_at"] or cycle["review"] is not None:
            raise GateError("Revisao ja congelada neste ciclo")
        review, source = read_json(root, review_file)
        reviewer = independent(review.get("reviewer"), cycle["production"]["actor"])
        if review.get("artifact_sha256") != cycle["artifact"]["sha256"]:
            raise GateError("Revisao de outra versao do artefato")
        criteria = review.get("criteria")
        if not isinstance(criteria, list) or {c.get("id") for c in criteria} != CRITERIA or len(criteria) != len(CRITERIA):
            raise GateError("Seis criterios explicitos obrigatorios")
        for criterion in criteria:
            required(criterion.get("observation"), "criterion.observation")
            if criterion.get("verdict") not in {"pass", "fail"}:
                raise GateError("Criterio exige verdict pass/fail")
            criterion["evidence"] = evidence(root, criterion.get("evidence"))
        findings = review.get("findings")
        if not isinstance(findings, list):
            raise GateError("Lista de achados explicita obrigatoria")
        seen = set()
        for finding in findings:
            key = required(finding.get("id"), "finding.id")
            if key in seen:
                raise GateError("Achado duplicado")
            seen.add(key)
            if finding.get("criterion") not in CRITERIA or finding.get("status") not in {"open", "resolved"}:
                raise GateError("Achado exige criterio e estado valido")
            required(finding.get("observation"), "finding.observation")
            finding["evidence"] = evidence(root, finding.get("evidence"))
            if finding["status"] == "resolved":
                required(finding.get("resolution"), "finding.resolution")
                required(finding.get("acceptance_test"), "finding.acceptance_test")
        prior = data["history"][-1]["review"] if data["history"] else None
        if prior:
            omitted = {f["id"] for f in prior["findings"] if f["status"] == "open"} - seen
            if omitted:
                raise GateError("Achados anteriores omitidos; resolva explicitamente com prova: " + ", ".join(sorted(omitted)))
        record = {"source": source, "reviewer": reviewer, "criteria": criteria,
                  "findings": findings, "recorded_at": stamp()}
        cycle["review"] = record
        unresolved = lambda r: sum(f["status"] == "open" for f in r["findings"]) + sum(c["verdict"] == "fail" for c in r["criteria"])
        comparable = [c for c in data["history"] + [cycle]
                      if c["production"]["actor"] == cycle["production"]["actor"] and c["review"]]
        if len(comparable) >= 3:
            counts = [unresolved(c["review"]) for c in comparable[-3:]]
            data["requires_new_session"] = counts[2] >= counts[1] >= counts[0] and counts[2] > 0
        return data
    return transaction(root, manifest, op)


def png_size(path):
    raw = Path(path).read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise GateError("Captura deve ser PNG real")
    offset, dimensions, compressed, image_format = 8, None, bytearray(), None
    while offset + 12 <= len(raw):
        length = struct.unpack(">I", raw[offset:offset+4])[0]
        kind = raw[offset+4:offset+8]
        payload = raw[offset+8:offset+8+length]
        end = offset + 12 + length
        if end > len(raw) or zlib.crc32(kind + payload) != struct.unpack(">I", raw[end-4:end])[0]:
            raise GateError("PNG truncado ou corrompido")
        if kind == b"IHDR" and length == 13:
            dimensions = struct.unpack(">II", payload[:8])
            image_format = tuple(payload[8:])
        if kind == b"IDAT":
            compressed.extend(payload)
        if kind == b"IEND":
            if end != len(raw) or not dimensions or not compressed or min(dimensions) <= 0:
                raise GateError("PNG incompleto")
            depth, color, compression, filtering, interlace = image_format
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            if not channels or depth not in {1, 2, 4, 8, 16} or compression or filtering or interlace:
                raise GateError("PNG de captura deve ser padrao, sem entrelacamento")
            row_bytes = (dimensions[0] * channels * depth + 7) // 8
            expected = (row_bytes + 1) * dimensions[1]
            if expected > 256 * 1024 * 1024:
                raise GateError("Captura excede limite de decodificacao")
            try:
                decoder = zlib.decompressobj()
                pixels = decoder.decompress(bytes(compressed), expected + 1)
                if not decoder.eof or decoder.unused_data or len(pixels) != expected:
                    raise GateError("Pixels PNG ausentes ou inconsistentes")
                if any(pixels[i] > 4 for i in range(0, len(pixels), row_bytes + 1)):
                    raise GateError("Filtro de pixel PNG invalido")
            except zlib.error as exc:
                raise GateError("Pixels PNG corrompidos") from exc
            return dimensions
        offset = end
    raise GateError("PNG sem IEND")


def verify(root, manifest, inspection_file):
    def op(data):
        cycle = current(root, data)
        if cycle["delivered_at"]:
            raise GateError("Ciclo entregue congelado")
        inspection, source = read_json(root, inspection_file)
        inspector = independent(inspection.get("inspector"), cycle["production"]["actor"])
        if inspection.get("artifact_sha256") != cycle["artifact"]["sha256"]:
            raise GateError("Inspecao de outra versao")
        if inspection.get("actually_viewed") is not True:
            raise GateError("Arquivo existente nao prova observacao visual")
        captures = inspection.get("captures")
        if not isinstance(captures, list) or {c.get("viewport_width") for c in captures} != {1440, 390} or len(captures) != 2:
            raise GateError("Capturas 1440 e 390 obrigatorias")
        visual = []
        for capture in captures:
            image = rooted(root, capture.get("path", ""))
            width, height = png_size(image)
            if width != capture["viewport_width"]:
                raise GateError("Largura real do PNG difere do viewport declarado; use escala 1")
            required(capture.get("observation"), "capture.observation")
            if capture.get("verdict") != "pass":
                raise GateError("Inspecao com defeito precisa voltar ao GLM")
            visual.append({**capture, "image": reference(root, image), "width": width,
                           "height": height, "inspector": inspector, "source": source})
        tests = inspection.get("tests")
        if not isinstance(tests, list) or not tests:
            raise GateError("Verificacao funcional com comandos/logs obrigatoria")
        for test in tests:
            required(test.get("command"), "test.command")
            required(test.get("observation"), "test.observation")
            if test.get("exit_code") != 0 or isinstance(test.get("exit_code"), bool):
                raise GateError("Teste funcional falhou")
            test["log"] = reference(root, test.get("log", ""))
            if not rooted(root, test["log"]["path"]).stat().st_size:
                raise GateError("Log de teste vazio")
            test["inspector"] = inspector
            test["source"] = source
        if cycle["visual"] or cycle["tests"]:
            cycle["inspection_history"].append({"visual": copy.deepcopy(cycle["visual"]),
                                               "tests": copy.deepcopy(cycle["tests"]), "superseded_at": stamp()})
        cycle["visual"], cycle["tests"] = visual, tests
        return data
    return transaction(root, manifest, op)


def _check_review_source(root, cycle):
    record = cycle["review"]
    _fresh_ref(root, record["source"])
    raw, source = read_json(root, record["source"]["path"])
    reviewer = independent(raw.get("reviewer"), cycle["production"]["actor"])
    if raw.get("artifact_sha256") != cycle["artifact"]["sha256"]:
        raise GateError("Fonte de revisao pertence a outro artefato")
    criteria, findings = raw.get("criteria"), raw.get("findings")
    if not isinstance(criteria, list) or len(criteria) != len(CRITERIA) or {c.get("id") for c in criteria} != CRITERIA:
        raise GateError("Fonte de revisao exige os seis criterios")
    for criterion in criteria:
        required(criterion.get("observation"), "criterion.observation")
        if criterion.get("verdict") not in {"pass", "fail"}:
            raise GateError("Veredito invalido na fonte de revisao")
        criterion["evidence"] = evidence(root, criterion.get("evidence"))
    if not isinstance(findings, list):
        raise GateError("Lista de achados obrigatoria na fonte")
    seen = set()
    for finding in findings:
        key = required(finding.get("id"), "finding.id")
        if key in seen or finding.get("criterion") not in CRITERIA or finding.get("status") not in {"open", "resolved"}:
            raise GateError("Achado invalido ou duplicado na fonte")
        seen.add(key)
        required(finding.get("observation"), "finding.observation")
        finding["evidence"] = evidence(root, finding.get("evidence"))
        if finding["status"] == "resolved":
            required(finding.get("resolution"), "finding.resolution")
            required(finding.get("acceptance_test"), "finding.acceptance_test")
    expected = {"source": source, "reviewer": reviewer, "criteria": criteria, "findings": findings}
    if expected != {key: record.get(key) for key in expected}:
        raise GateError("Revisao no manifesto diverge do JSON fonte congelado")


def _check_inspection_source(root, cycle):
    rows = cycle["visual"] + cycle["tests"]
    if not rows:
        return
    source = rows[0]["source"]
    _fresh_ref(root, source)
    if any(row.get("source") != source for row in rows):
        raise GateError("Inspecao mistura fontes diferentes")
    raw, source = read_json(root, source["path"])
    inspector = independent(raw.get("inspector"), cycle["production"]["actor"])
    if raw.get("artifact_sha256") != cycle["artifact"]["sha256"] or raw.get("actually_viewed") is not True:
        raise GateError("Fonte da inspecao sem observacao ou de outra versao")
    captures = raw.get("captures")
    if not isinstance(captures, list) or len(captures) != 2 or {c.get("viewport_width") for c in captures} != {1440, 390}:
        raise GateError("Fonte exige capturas 1440/390")
    expected_visual = []
    for capture in captures:
        image = rooted(root, capture.get("path", ""))
        width, height = png_size(image)
        required(capture.get("observation"), "capture.observation")
        if capture.get("verdict") != "pass" or width != capture["viewport_width"]:
            raise GateError("Fonte visual reprovada ou largura incorreta")
        expected_visual.append({**capture, "image": reference(root, image), "width": width, "height": height,
                                "inspector": inspector, "source": source})
    tests = raw.get("tests")
    if not isinstance(tests, list) or not tests:
        raise GateError("Fonte exige teste funcional")
    for test in tests:
        required(test.get("command"), "test.command")
        required(test.get("observation"), "test.observation")
        if test.get("exit_code") != 0 or isinstance(test.get("exit_code"), bool):
            raise GateError("Fonte de teste funcional reprovada")
        test["log"] = reference(root, test.get("log", ""))
        if not rooted(root, test["log"]["path"]).stat().st_size:
            raise GateError("Log de teste vazio")
        test["inspector"], test["source"] = inspector, source
    if expected_visual != cycle["visual"] or tests != cycle["tests"]:
        raise GateError("Inspecao no manifesto diverge do JSON fonte congelado")


def gate(root, data):
    cycle = current(root, data)
    errors = []
    if cycle.get("revocation"):
        errors.append("Candidato/exemplar revogado; produzir nova versao antes da entrega")
    if cycle["artifact"]["remote_resources"]:
        errors.append("Recursos remotos de render precisam ser congelados localmente")
    review = cycle["review"]
    if not review:
        errors.append("Revisao independente ausente")
    else:
        _check_review_source(root, cycle)
        independent(review["reviewer"], cycle["production"]["actor"])
        _fresh_ref(root, review["source"])
        for criterion in review["criteria"]:
            for ref in criterion["evidence"]:
                _fresh_ref(root, ref)
            if criterion["verdict"] != "pass":
                errors.append("Criterio reprovado: " + criterion["id"])
        for finding in review["findings"]:
            for ref in finding["evidence"]:
                _fresh_ref(root, ref)
            if finding["status"] != "resolved":
                errors.append("Achado aberto: " + finding["id"])
    if {v["viewport_width"] for v in cycle["visual"]} != {1440, 390}:
        errors.append("Inspecao visual 1440/390 ausente")
    for view in cycle["visual"]:
        _fresh_ref(root, view["source"])
        _fresh_ref(root, view["image"])
        independent(view["inspector"], cycle["production"]["actor"])
    if not cycle["tests"]:
        errors.append("Teste funcional ausente")
    for test in cycle["tests"]:
        _fresh_ref(root, test["source"])
        _fresh_ref(root, test["log"])
    _check_inspection_source(root, cycle)
    if data["requires_new_session"]:
        errors.append("Nova sessao exigida apos duas correcoes sem melhora [HEURISTICA]")
    if errors:
        raise GateError("; ".join(errors))
    return cycle


def deliver(root, manifest):
    def op(data):
        cycle = gate(root, data)
        if not cycle["delivered_at"]:
            cycle["delivered_at"] = stamp()
        return data
    return transaction(root, manifest, op)


@contextmanager
def _library_index(central):
    path = rooted(central, "motor/modelos/relatorios/glm/indice.json", exists=False)
    owner = f"mb-relatorios-glm-library:{os.getpid()}:{uuid.uuid4().hex}"
    with mb_trava.travado(path, owner, "indice unico de referencias GLM", raiz=central):
        index, _ = read_json(central, path) if path.exists() else ({
            "schema_version": 1, "references": [], "candidates": [], "promoted": []}, None)
        if index.get("schema_version") != 1 or any(not isinstance(index.get(k), list) for k in ("candidates", "promoted")):
            raise GateError("Indice mestre GLM invalido; nao foi substituido")
        if not isinstance(index.setdefault("revocations", []), list):
            raise GateError("Registro de revogacoes invalido")
        yield path, index
        _atomic(path, index)


def _is_revoked(index, artifact_sha256):
    return any(row.get("artifact_sha256") == artifact_sha256 for row in index["revocations"])


def promote(root, manifest, slug, *, central=CENTRAL):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", slug):
        raise GateError("Slug exemplar invalido")
    central = Path(central).resolve(strict=True)
    base = central / "motor/modelos/relatorios/glm/promovidos"
    def op(data):
        cycle = gate(root, data)
        if not cycle["delivered_at"]:
            raise GateError("Entregar pelo gate antes de promover")
        target = rooted(central, base / slug / cycle["artifact"]["sha256"], exists=False)
        owner = f"mb-relatorios-glm-promote:{os.getpid()}:{uuid.uuid4().hex}"
        with _library_index(central) as (index_path, index), mb_trava.travado(target, owner, "exemplar GLM congelado", raiz=central):
            artifact_sha256 = cycle["artifact"]["sha256"]
            if _is_revoked(index, artifact_sha256):
                raise GateError("Exemplar revogado nao pode voltar a referencia ativa; gerar nova versao")
            if target.exists():
                existing, _ = read_json(central, target / "provenance.json")
                if existing.get("source_project") != str(Path(root).resolve()) or existing.get("source_report") != data["report"] or existing.get("cycle", {}).get("artifact") != cycle["artifact"]:
                    raise GateError("Exemplar versionado existente nao corresponde; nao sobrescrever")
                for rel, sha in cycle["artifact"]["files"].items():
                    if digest(rooted(central, target / rel)) != sha:
                        raise GateError("Exemplar versionado existente foi alterado")
                _record_promotion(index, central, target, root, manifest, data, cycle)
                if not any(p["path"] == str(target) for p in cycle["promoted"]):
                    cycle["promoted"].append({"path": str(target), "at": stamp()})
                return data
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(tempfile.mkdtemp(prefix=".glm-promote-", dir=target.parent))
            try:
                copies = dict(cycle["artifact"]["files"])
                def collect(value):
                    if isinstance(value, dict):
                        if set(value) == {"path", "sha256"}:
                            previous = copies.get(value["path"])
                            if previous and previous != value["sha256"]:
                                raise GateError("Evidencias conflitantes para o mesmo caminho")
                            copies[value["path"]] = value["sha256"]
                        else:
                            for child in value.values():
                                collect(child)
                    elif isinstance(value, list):
                        for child in value:
                            collect(child)
                collect(cycle)
                for rel, sha in copies.items():
                    source = rooted(root, rel)
                    if digest(source) != sha:
                        raise GateError("Artefato mudou durante promocao")
                    dest = temporary / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, dest)
                    if digest(dest) != sha:
                        raise GateError("Copia do exemplar nao confere")
                _atomic(temporary / "provenance.json", {"source_project": str(Path(root).resolve()),
                        "source_report": data["report"], "cycle": copy.deepcopy(cycle),
                        "technical_approval": "VERIFICADO_TECNICAMENTE", "human_approval": "NAO_MEDIDO",
                        "approval_scope": "Artefato e ciclo revisados; nao aprova automaticamente novas composicoes",
                        "promoted_at": stamp(), "purpose": "exemplar versionado; nao e treinamento de pesos"})
                # Recheck after copy, before publishing the complete directory.
                gate(root, data)
                os.rename(temporary, target)
            finally:
                if temporary.exists():
                    shutil.rmtree(temporary)
            _record_promotion(index, central, target, root, manifest, data, cycle)
        cycle["promoted"].append({"path": str(target), "at": stamp()})
        return data
    return transaction(root, manifest, op)


def _record_promotion(index, central, target, root, manifest, data, cycle):
    relative = str(target.relative_to(central))
    if any(row.get("path") == relative for row in index["promoted"]):
        return
    index["promoted"].append({"path": relative, "status": "active",
        "artifact_sha256": cycle["artifact"]["sha256"],
        "provenance": str((target / "provenance.json").relative_to(central)),
        "provenance_sha256": digest(target / "provenance.json"),
        "source_project": str(Path(root).resolve()), "source_report": data["report"],
        "source_manifest": str(manifest_path(root, manifest).relative_to(Path(root).resolve())),
        "technical_approval": "VERIFICADO_TECNICAMENTE", "human_approval": "NAO_MEDIDO",
        "approval_scope": "Somente este artefato e ciclo; adaptacao exige nova revisao", "promoted_at": stamp()})


def revoke(root, manifest, reason, evidence_files, *, artifact_sha256=None, central=CENTRAL):
    """Reject current/past candidate without deleting or rewriting its provenance."""
    reason = required(reason, "reason")
    proof = evidence(root, list(evidence_files))
    central = Path(central).resolve(strict=True)
    def op(data):
        target_hash = artifact_sha256 or data["current"]["artifact"]["sha256"]
        cycles = [c for c in data["history"] + [data["current"]] if c["artifact"]["sha256"] == target_hash]
        if not cycles:
            raise GateError("Hash a revogar nao pertence ao manifesto")
        event = {"artifact_sha256": target_hash, "status": "rejected", "reason": reason,
                 "evidence": proof, "at": stamp(), "source_project": str(Path(root).resolve()),
                 "source_report": data["report"], "source_manifest": str(manifest_path(root, manifest)),
                 "human_approval": "NAO_MEDIDO", "approval_scope": "Rejeicao registrada por evidencia; nao inferir autoria humana"}
        with _library_index(central) as (_, index):
            index["promoted"] = [row for row in index["promoted"] if row.get("artifact_sha256") != target_hash]
            index["revocations"].append(copy.deepcopy(event))
            matching = [row for row in index["candidates"] if row.get("artifact_sha256") == target_hash]
            for row in matching:
                row.update(status="rejected", rejection=copy.deepcopy(event))
            if not matching:
                index["candidates"].append({"id": "rejected-" + target_hash[:16], "artifact_sha256": target_hash,
                                             "status": "rejected", "rejection": copy.deepcopy(event)})
        for cycle in cycles:
            cycle["revocation"] = copy.deepcopy(event)
        return data
    return transaction(root, manifest, op, validate_current=False)


def status(root, manifest):
    data, _ = read_json(root, manifest_path(root, manifest))
    try:
        gate(root, data)
        state, reason = "ready", None
    except (GateError, OSError) as exc:
        state, reason = "blocked", str(exc)
    return {"state": state, "reason": reason, "artifact_sha256": data["current"]["artifact"]["sha256"],
            "cycle": data["current"]["number"], "delivered_at": data["current"]["delivered_at"] if state == "ready" else None,
            "requires_new_session": data["requires_new_session"]}
