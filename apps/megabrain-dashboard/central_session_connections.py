"""Read explicit startup registrations; a native receipt proves presentation only."""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

VERSION = '1.0.0'
ID = re.compile(r'[a-f0-9]{24}')
REQUEST = re.compile(r'[a-f0-9]{32}')

def load(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError('Registro inválido')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict): raise ValueError('Registro inválido')
    return value

def date(value):
    if not isinstance(value, str): raise ValueError('Data ausente')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None: raise ValueError('Data sem fuso')
    if parsed.timestamp() > datetime.now(timezone.utc).timestamp() + 60: raise ValueError('Data futura')
    return parsed.timestamp()

def snapshot(app, sources):
    app = Path(app); registry = app/'data/session-connections'; queue = app/'data/open-requests'
    with sources.lock: projects = {str(root.resolve()).casefold(): (pid, root) for pid, root in sources.projects.items()}
    rows = []; rejected = 0
    candidates = []
    if registry.is_dir():
        for path in registry.glob('*.json'):
            try: candidates.append((path.stat().st_mtime, path))
            except OSError: continue
    files = [path for _, path in sorted(candidates, reverse=True)[:500]]
    for path in files:
        try:
            record = load(path)
            if record.get('schema_version') != 1 or not ID.fullmatch(str(record.get('id', ''))) or record['id'] != path.stem: raise ValueError('ID inválido')
            updated = date(record.get('updated_at')); date(record.get('started_at'))
            root_text = record.get('project_root')
            if not isinstance(root_text, str) or len(root_text) > 2000 or not Path(root_text).is_absolute(): raise ValueError('Projeto inválido')
            root = Path(root_text).resolve(); known = projects.get(str(root).casefold())
            client = record.get('application')
            if not isinstance(client, str) or not 1 <= len(client) <= 100: raise ValueError('Aplicativo inválido')
            request = record.get('presentation_request_id')
            if request is not None and not REQUEST.fullmatch(str(request)): raise ValueError('Pedido inválido')
            state = 'registered'; label = 'Registrada; abertura não solicitada'; presented_at = None
            if not known: state = 'unregistered_project'; label = 'Projeto ainda não cadastrado na central'
            elif request:
                state = 'pending'; label = 'Aguardando confirmação do aplicativo'
                receipt_path = queue/(request+'.receipt'); target_path = queue/(request+'.presented')
                if receipt_path.exists():
                    receipt = load(receipt_path)
                    if receipt.get('requestId') != request: raise ValueError('Recibo de outro pedido')
                    if receipt.get('ok') is True and target_path.exists():
                        target = load(target_path)
                        if target.get('id') != request or Path(target.get('project', '')).resolve() != root or receipt.get('project_id') != known[0]: raise ValueError('Destino do recibo não confere')
                        state = 'presented'; label = 'Abertura confirmada pelo aplicativo'
                        presented_at = datetime.fromtimestamp(receipt_path.stat().st_mtime, timezone.utc).isoformat(timespec='seconds')
                    elif receipt.get('ok') is False: state = 'failed'; label = 'Aplicativo não confirmou a abertura'
                elif any((queue/(request+'.'+suffix)).exists() for suffix in ('expired','invalid','failed')):
                    state = 'failed'; label = 'Pedido expirado ou inválido'
                elif record.get('presentation_state') == 'unavailable':
                    state = 'unavailable'; label = 'Abertura indisponível; sessão registrada'
            elif record.get('error') and record.get('error') != 'presentation_not_requested':
                state = 'unavailable'; label = 'Abertura indisponível; sessão registrada'
            rows.append(dict(id=record['id'], project_id=known[0] if known else None, project_name=root.name,
                application=client, started_at=record['started_at'], updated_at=record['updated_at'],
                bridge_version=str(record.get('bridge_version','desconhecida'))[:30], identity_source=str(record.get('identity_source','desconhecida'))[:100],
                source=str(record.get('source','desconhecida'))[:100], state=state, label=label, presented_at=presented_at,
                presentation_request_id=request, _sort=updated))
        except (OSError, ValueError, TypeError, KeyError, OverflowError): rejected += 1
    rows.sort(key=lambda row: row.pop('_sort'), reverse=True)
    return dict(version=VERSION, observed_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),
        sessions=rows, registered_count=len(rows), presented_count=sum(row['state']=='presented' for row in rows),
        rejected_count=rejected, limit=500, truncated=len(candidates)>500, total_records=len(candidates),
        scope='Sessões que executaram a abertura MegaBrain; recibo confirma apresentação, não atividade contínua.')
