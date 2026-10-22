#!/usr/bin/env python3
"""Produce technical HTML through the existing certified ZCode subscription.

No retry, publication, report approval or global configuration mutation. Private
model_clients helpers are reused deliberately; runtime/config contracts are
checked and must be revalidated when that adapter or official runtime changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

CENTRAL = Path(__file__).resolve().parents[1]
TECHNICAL = {'evidence', '.automations'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


class ProductionError(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(project, value, *, existing=False, technical=False):
    root = Path(project).resolve(strict=True)
    raw = Path(value)
    if '..' in raw.parts:
        raise ProductionError('Path traversal is forbidden')
    path = raw if raw.is_absolute() else root / raw
    resolved = path.resolve(strict=existing)
    if not resolved.is_relative_to(root) or resolved == root:
        raise ProductionError('Path must stay inside the project')
    cursor = path
    while cursor != root and cursor != cursor.parent:
        if cursor.is_symlink() or getattr(cursor, 'is_junction', lambda: False)():
            raise ProductionError('Symlinks and junctions are forbidden')
        cursor = cursor.parent
    if existing and (not resolved.is_file() or resolved.stat().st_nlink != 1):
        raise ProductionError('Regular input file without hardlinks required')
    if technical and resolved.relative_to(root).parts[0] not in TECHNICAL:
        raise ProductionError('Output and run directory belong in evidence/ or .automations/')
    return resolved


def parse_result(stdout):
    """Native 0.16.5 emits pretty JSON; only use JSONL as the fallback."""
    try:
        whole = json.loads(stdout)
        records = whole if isinstance(whole, list) else [whole]
    except ValueError:
        records = []
        for line in stdout.splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    candidates = [row for row in records if isinstance(row, dict) and
                  (row.get('type') == 'result' or isinstance(row.get('response'), str) or isinstance(row.get('result'), str))]
    if not candidates:
        raise ProductionError('Native JSON response is absent')
    result = candidates[-1]
    sid = result.get('session_id') or result.get('sessionId')
    if not isinstance(sid, str) or not re.fullmatch(r'[\w-]+', sid):
        raise ProductionError('Native session identity is absent')
    text = result.get('response') or result.get('result')
    if not isinstance(text, str) or not text.strip():
        raise ProductionError('Native response text is empty')
    if result.get('is_error') is True or result.get('type') == 'error':
        raise ProductionError('Native response reports an error')
    return sid, text


def validate_quota(quota, *, clock=None):
    current = clock or dt.datetime.now(dt.timezone.utc)
    if quota.get('provider') != 'zai' or quota.get('status') != 'ok' or not quota.get('source'):
        raise ProductionError('Current GLM quota is not observed; no dispatch')
    def moment(value):
        try:
            parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise ValueError()
            return parsed.astimezone(dt.timezone.utc)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ProductionError('Quota timestamps require an explicit timezone') from exc
    age = (current - moment(quota.get('fetched_at'))).total_seconds()
    if not 0 <= age <= 300:
        raise ProductionError('Quota source is stale or future-dated [HEURISTIC 300 s]')
    windows = quota.get('windows')
    if not isinstance(windows, list) or not windows:
        raise ProductionError('Quota windows are absent')
    for window in windows:
        duration, used = window.get('duration_minutes'), window.get('used_percent')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (duration, used)):
            raise ProductionError('Quota duration/usage is unknown')
        # The official Z.ai response can explicitly report 0% with no renewal
        # timestamp. Keep the schedule unknown; do not invent one or equate it
        # with exhausted quota. A missing reset at positive usage stays blocked.
        no_schedule = used == 0 and window.get('resets_at') is None
        if duration <= 0 or not 0 <= used < 100 or (not no_schedule and moment(window.get('resets_at')) <= current):
            raise ProductionError('Quota duration/reset invalid or a window is exhausted; no retry')
    return quota


class FinishedHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.tags, self.visible, self.outside = [], set(), [], []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.add(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            raise ProductionError('HTML contains mismatched closing tags')
        self.stack.pop()

    def handle_data(self, text):
        if text.strip() and not self.stack:
            self.outside.append(text)
        if not any(tag in {'style', 'script'} for tag in self.stack):
            self.visible.append(text)


def validate_html(text):
    html = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    if html.startswith('```'):
        match = re.fullmatch(r'```(?:html)?\s*\n?(.*?)\n?```', html, re.S | re.I)
        if not match:
            raise ProductionError('Incomplete HTML fences')
        html = match.group(1).strip()
    if not html.startswith('<'):
        raise ProductionError('Response must be the complete HTML, without explanation')
    parsed = FinishedHTML()
    parsed.feed(html)
    parsed.close()
    structured = bool(parsed.tags & {'main', 'article', 'section', 'div', 'table', 'figure'})
    if parsed.stack or parsed.outside or not (structured or {'html', 'body'} <= parsed.tags):
        raise ProductionError('Incomplete HTML document/fragment')
    if 'html' in parsed.tags and 'body' not in parsed.tags:
        raise ProductionError('Full HTML document has no body')
    words = re.findall(r'\w+', ' '.join(parsed.visible).casefold())
    if not words:
        raise ProductionError('HTML has no readable content')
    if len(words) > 300 and len(set(words[-250:])) < 8:
        raise ProductionError('Suspected repetitive token loop [HEURISTIC]; inspect before another run')
    sentences = [s.strip() for s in re.split(r'[.!?\n]+', ' '.join(parsed.visible)) if len(s.strip()) > 70]
    if sentences and max(Counter(sentences).values()) >= 5:
        raise ProductionError('Repeated answer loop [HEURISTIC]; output withheld')
    return html


def validate_evidence(rows):
    if not isinstance(rows, list) or not rows:
        raise ProductionError('Native model/effort metadata is absent')
    for row in rows:
        if (not isinstance(row.get('model'), dict) or row['model'].get('modelId') != 'GLM-5.3'
                or row.get('body_model') != 'GLM-5.3' or row.get('response_model') != 'GLM-5.3'
                or row.get('body_effort') != 'max' or row.get('provider_effort') != 'max'):
            raise ProductionError('GLM-5.3/MAX was not proved by the native requests')
        if row.get('finishReason') != 'stop' or row.get('tool_calls') or row.get('tool_names_requested'):
            raise ProductionError('Native request did not finish normally or requested tools; output withheld')
    return True


def dependencies():
    sys.path.insert(0, str(CENTRAL / 'apps/megabrain-dashboard'))
    sys.path.insert(0, str(CENTRAL / 'apps/ia-quota-widget'))
    import model_clients
    import central_bridge
    import providers
    return model_clients, providers, central_bridge.ambiente


def command(run, prompt, clients):
    # No --settings: unsupported by the installed official CLI. Local cwd config
    # is the certified route; only its permission.mode differs from _glm_config.
    return [str(clients.ZCODE), '--prompt', prompt, '--cwd', str(run), '--json',
            '--no-color', '--mode', 'build', '--disallowed-tools', ','.join(clients.DENY_TOOLS)]


def produce(project, prompt_file, run_dir, output_file, *, timeout=420, deps=None, runner=None):
    if isinstance(timeout, bool) or not 1 <= timeout <= 900:
        raise ProductionError('Timeout must be between 1 and 900 seconds')
    root = Path(project).resolve(strict=True)
    source = safe_path(root, prompt_file, existing=True)
    run = safe_path(root, run_dir, technical=True)
    output = safe_path(root, output_file, technical=True)
    if run.exists() or output.exists() or output == run or output.suffix.lower() not in {'.html', '.htm'}:
        raise ProductionError('Exclusive new run directory and new technical HTML output required')
    if source.is_relative_to(run) or output == source:
        raise ProductionError('Input and outputs must be separate')
    source_data = source.read_bytes()
    user_prompt = source_data.decode('utf-8-sig')
    if not user_prompt.strip():
        raise ProductionError('Prompt file is empty')
    skill = CENTRAL / 'motor/skills/relatorios-glm/SKILL.md'
    master = CENTRAL / 'motor/modelos/relatorios/260914_pop/relatorio-pop.html'
    skill_text, master_text = skill.read_text(encoding='utf-8-sig'), master.read_text(encoding='utf-8-sig')
    prompt = ('Produza agora somente o HTML completo ou fragmento HTML finalizado pedido abaixo. '
              'Não escreva plano, explicação ou chamada de ferramenta. Você é GLM compositor; '
              'Codex/Claude observará o render. Ferramentas, memória e skills estão desligadas; '
              'o contrato e o modelo estão incluídos. Não afirme ter visto prints. '
              'Copie o estilo POP e adapte a composição aos fatos, sem inventar dados.\n\n'
              'CONTRATO CANÔNICO:\n' + skill_text + '\n\n'
              'MODELO MESTRE EXISTENTE (referência de estilo; não aprova a nova composição):\n' + master_text + '\n\n'
              'PEDIDO, FATOS, EXEMPLOS PERTINENTES E CORREÇÕES DO SOLICITANTE:\n' + user_prompt)
    clients, providers, environment = deps or dependencies()
    secrets = []
    env = environment('glm')
    config_before = sha(Path(clients.ZCODE_CONFIG).read_bytes())
    run.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, run, technical=True)
    run.mkdir(exist_ok=False)
    result = {'vendor': 'glm', 'status': 'failed', 'exit_code': None, 'text': '',
              'actual_model': None, 'session_id': None, 'model_io_metadata': [],
              'effort_requested': 'max', 'effort_verified': False,
              'requested_model': 'zai/GLM-5.3', 'model_called': False,
              'source_prompt': {'path': str(source.relative_to(root)), 'sha256': sha(source_data)},
              'contract_sha256': sha(skill_text.encode()), 'master_sha256': sha(master_text.encode()),
              'delivery_ready': False, 'automatic_retries': 0,
              'adapter': 'certified model_clients private helpers; isolated build, tools denied',
              'auth_route': 'official ZCode existing subscription; credential in child environment only'}
    def redacted(text):
        return clients._redact(str(text), secrets)
    def write(path, text):
        path.write_text(redacted(text), encoding='utf-8')
    stdout, stderr = '', ''
    try:
        # Configure first so every later log, including quota errors, knows the
        # credential to redact. Helper verifies official runtime hash/endpoint.
        result['catalog_evidence'] = clients._glm_config(run, env, secrets)
        if any(secret and secret in prompt for secret in secrets):
            raise ProductionError('Prompt contains a credential; no dispatch')
        local = run / 'zcode.json'
        config = json.loads(local.read_text(encoding='utf-8'))
        config['permission']['mode'] = 'build'
        write(local, json.dumps(config, ensure_ascii=False, indent=2))
        quota = providers._sanitized(providers.fetch_provider('zai'))
        write(run / 'quota-before.json', json.dumps(quota, ensure_ascii=False, indent=2))
        validate_quota(quota)
        write(run / 'prompt.txt', prompt)
        result['composed_prompt_sha256'] = sha(prompt.encode())
        args = command(run, prompt, clients)
        write(run / 'argv.json', json.dumps(args[1:], ensure_ascii=False))
        launcher = ("const fs=require('node:fs'),path=require('node:path');\nconst bundle="
                    + json.dumps(args[0]) + ";\nprocess.argv=[process.execPath,bundle,...JSON.parse("
                    "fs.readFileSync(path.join(__dirname,'argv.json'),'utf8'))];require(bundle);\n")
        write(run / 'launch.cjs', launcher)
        node = shutil.which('node')
        if not node:
            raise ProductionError('Node runtime is unavailable')
        result['argument_transport'] = 'Node argv bridge; no Windows 32767 command-line prompt limit'
        result['model_called'] = True
        process = (runner or subprocess.run)([node, str(run / 'launch.cjs')], cwd=run, env=env,
                    stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8', errors='replace',
                    timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        stdout, stderr = redacted(process.stdout), redacted(process.stderr)
        result['exit_code'] = process.returncode
        if clients._rate_limit_failure(stdout, stderr):
            result['status'] = 'rate_limited'
            raise ProductionError('Rate limit observed; no automatic retry')
        if process.returncode != 0:
            raise ProductionError('Official CLI exited unsuccessfully')
        sid, text = parse_result(stdout)
        result.update(session_id=sid, text=text)
        rows = clients._glm_evidence(run, sid)
        result['model_io_metadata'] = rows
        validate_evidence(rows)
        result.update(actual_model='GLM-5.3', effort_verified=True,
                      effort_evidence='native GLM-5.3 request/response with output_config and provider effort=max')
        html = validate_html(text)
        if sha(Path(clients.ZCODE_CONFIG).read_bytes()) != config_before:
            raise ProductionError('Global ZCode config changed during the run; output withheld')
        safe_path(root, output, technical=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(html)
        result.update(status='completed', html_validated=True, output=str(output.relative_to(root)),
                      output_sha256=sha(output.read_bytes()))
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        stderr = exc.stderr.decode('utf-8', errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
        result.update(status='timeout', reason='Native CLI timeout; no automatic retry')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['reason'] = redacted(exc)
    finally:
        write(run / 'stdout.log', stdout)
        write(run / 'stderr.log', stderr)
        # Native text logs belong to this exclusive run; remove credential echoes
        # without changing the allowlisted request metadata used by the gate.
        for path in run.rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.json', '.jsonl', '.log', '.txt'}:
                text = path.read_text(encoding='utf-8', errors='replace')
                cleaned = redacted(text)
                if cleaned != text:
                    path.write_text(cleaned, encoding='utf-8')
        result['global_config_sha256_before'] = config_before
        result['global_config_sha256_after'] = sha(Path(clients.ZCODE_CONFIG).read_bytes())
        result['global_config_unchanged'] = result['global_config_sha256_after'] == config_before
        if not result['global_config_unchanged']:
            result.update(status='failed', reason='Global ZCode config changed during the run')
        write(run / 'model-io-metadata.json', json.dumps(result['model_io_metadata'], ensure_ascii=False, indent=2))
        write(run / 'result.json', json.dumps(result, ensure_ascii=False, indent=2))
    return json.loads(redacted(json.dumps(result, ensure_ascii=False)))


def main(argv=None):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--prompt', required=True, help='Self-contained facts, examples and correction brief')
    parser.add_argument('--run-dir', required=True, help='Exclusive new directory under evidence/ or .automations/')
    parser.add_argument('--output', required=True, help='New technical HTML; never the human delivery')
    parser.add_argument('--timeout', type=int, default=420)
    args = parser.parse_args(argv)
    try:
        result = produce(args.project, args.prompt, args.run_dir, args.output, timeout=args.timeout)
        summary = {key: result.get(key) for key in ('status', 'actual_model', 'effort_verified', 'session_id', 'reason', 'output', 'delivery_ready')}
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if result['status'] == 'completed' else 2
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'failed', 'reason': str(exc), 'model_called': False}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
