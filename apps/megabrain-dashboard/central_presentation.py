"""Local opening queue. A dispatched event is not a completed presentation."""
from __future__ import annotations
import json
import time
from pathlib import Path

# 261017 WP3: a session registration (origin 'session') never changes the screen;
# it only becomes a quiet notice. Explicit deliveries wait while the person is
# using a report (window.megabrainBusy in the web app) and go back to the queue.
SESSION_ORIGIN = 'session'
BUSY_PREFERENCE_SECONDS = 5


class PresentationQueue:
    def __init__(self, directory: Path):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.current = None
        self.busy_at = 0.0
        self.deferrals = 0

    def _candidates(self):
        """Valid pending requests, oldest first. Invalid or expired ones are renamed."""
        found = []
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
            if 'view' in request:
                if not isinstance(request['view'],str) or request['view'] not in {'quota-settings','quota-account'}:
                    path.rename(path.with_suffix('.invalid'));continue
                provider=request.get('provider','all')
                if not isinstance(provider,str) or provider not in {'all','codex','codex_gpt2','claude','zai','spark','gemini_cli','gemini_web','antigravity'}:
                    path.rename(path.with_suffix('.invalid'));continue
                payload.update(view=request['view'],provider=provider)
            # Only a project-only request can be a quiet session notice; any other
            # origin value is ignored (the request keeps its explicit behavior).
            if request.get('origin') == SESSION_ORIGIN and 'path' not in payload and 'view' not in payload:
                payload['origin'] = SESSION_ORIGIN
            payload['requestId'] = path.stem
            found.append((path, payload))
        return found

    def next(self):
        if self.current:
            return None
        found = self._candidates()
        if not found:
            return None
        chosen = found[0]
        # While the app answered "busy", a quiet session notice behind a waiting
        # delivery does not need to wait for it.
        if self.busy_at and time.time() - self.busy_at < BUSY_PREFERENCE_SECONDS:
            chosen = next((item for item in found if item[1].get('origin') == SESSION_ORIGIN), chosen)
        path, payload = chosen
        self.current = (path, time.time())
        return payload

    def retry(self):
        self.current = None

    def defer(self):
        """The person is using a report: the request stays queued (same file, same expiry)."""
        self.current = None
        self.busy_at = time.time()
        self.deferrals += 1

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


def dispatch_script(payload: dict) -> str:
    """Script run in the app page. Returns true (dispatched), false (not ready) or 'busy'."""
    detail = json.dumps(payload).replace('<', '\\u003c')
    gate = '' if payload.get('origin') == SESSION_ORIGIN else (
        "try{if(typeof window.megabrainBusy==='function'&&window.megabrainBusy())return 'busy';}catch(e){}")
    return ("(()=>{if(!window.megabrainReady)return false;" + gate +
            "window.megabrainPresentationResult=null;window.dispatchEvent(new CustomEvent('mb-present',{detail:" +
            detail + "}));return true;})()")


def bring_forward(window, receipt, minimized_flag) -> bool:
    """Raise the window for a confirmed, non-quiet presentation.

    Never leaves maximized or full screen: only a minimized window is restored,
    and the restore keeps the maximized/full-screen flags it had.
    """
    if not isinstance(receipt, dict) or receipt.get('ok') is not True or receipt.get('quiet'):
        return False
    if window.isMinimized():
        window.setWindowState(window.windowState() & ~minimized_flag)
    window.raise_()
    window.activateWindow()
    return True
