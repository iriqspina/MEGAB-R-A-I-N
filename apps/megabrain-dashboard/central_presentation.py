"""Local opening queue. A dispatched event is not a completed presentation."""
from __future__ import annotations
import json
import time
from pathlib import Path


class PresentationQueue:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.current = None

    def next(self):
        if self.current:
            return None
        for path in sorted(self.directory.glob('*.json'), key=lambda p: p.stat().st_mtime):
            try:
                request = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(request, dict):
                    raise ValueError('Pedido inválido')
                if time.time() - float(request.get('at', 0)) > 3600:
                    path.rename(path.with_suffix('.expired'))
                    continue
                payload = {k: request[k] for k in ('path', 'project') if k in request}
                if not payload or any(not isinstance(v, str) or not v or len(v) > 2000 for v in payload.values()):
                    raise ValueError('Destino inválido')
            except (ValueError, TypeError, OSError):
                try:
                    path.rename(path.with_suffix('.invalid'))
                except OSError:
                    pass
                continue
            payload['requestId'] = path.stem
            self.current = (path, time.time())
            return payload
        return None

    def retry(self):
        self.current = None

    def finish(self, receipt):
        if not self.current or not isinstance(receipt, dict) or receipt.get('requestId') != self.current[0].stem:
            return False
        path, _ = self.current
        status = 'presented' if receipt.get('ok') is True else 'failed'
        path.with_suffix('.receipt').write_text(json.dumps(receipt, ensure_ascii=False), encoding='utf-8')
        path.rename(path.with_suffix('.' + status))
        self.current = None
        return True

    def timeout(self):
        if self.current and time.time() - self.current[1] > 60:
            return self.finish({'requestId': self.current[0].stem, 'ok': False, 'error': 'O aplicativo não confirmou a abertura.'})
        return False
