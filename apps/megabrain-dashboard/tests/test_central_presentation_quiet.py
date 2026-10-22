"""261017 WP3: the app does not change screen by itself while a report is in use.

Covers the queue (quiet session notice, busy deferral, expiry), the script injected
in the page (megabrainBusy gate) and the window rule (quiet never raises; a delivery
never leaves maximized/full screen). Nothing here touches the live app or its data.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import central_presentation as presentation
from central_presentation import PresentationQueue, bring_forward, dispatch_script


def write(directory, name, at=None, **fields):
    path = directory / (name + '.json')
    path.write_text(json.dumps({'at': time.time() if at is None else at, **fields}), encoding='utf-8')
    return path


class QuietQueueTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)

    def test_session_origin_only_for_project_only_requests(self):
        write(self.dir, 'a', project='synthetic', origin='session')
        write(self.dir, 'b', path='synthetic.html', origin='session')
        write(self.dir, 'c', project='synthetic', origin='javascript:evil')
        queue = PresentationQueue(self.dir)
        seen = []
        for _ in range(3):
            payload = queue.next()
            seen.append(payload)
            queue.finish({'requestId': payload['requestId'], 'ok': True})
        by_id = {p['requestId']: p for p in seen}
        self.assertEqual(by_id['a'].get('origin'), 'session')
        self.assertNotIn('origin', by_id['b'])
        self.assertNotIn('origin', by_id['c'])

    def test_busy_deferral_keeps_request_and_retries_same_file(self):
        write(self.dir, 'delivery', path='synthetic.html')
        queue = PresentationQueue(self.dir)
        first = queue.next()
        queue.defer()
        self.assertTrue((self.dir / 'delivery.json').exists())
        self.assertIsNone(queue.current)
        self.assertEqual(queue.deferrals, 1)
        again = queue.next()
        self.assertEqual(again, first)
        self.assertTrue(queue.finish({'requestId': 'delivery', 'ok': True}))
        self.assertTrue((self.dir / 'delivery.presented').exists())

    def test_deferred_request_still_expires_after_one_hour(self):
        write(self.dir, 'old', at=time.time() - 3601, path='synthetic.html')
        queue = PresentationQueue(self.dir)
        self.assertIsNone(queue.next())
        self.assertTrue((self.dir / 'old.expired').exists())

    def test_session_notice_does_not_wait_behind_a_busy_delivery(self):
        older = write(self.dir, 'delivery', path='synthetic.html')
        newer = write(self.dir, 'session', project='synthetic', origin='session')
        os.utime(older, (time.time() - 10, time.time() - 10))
        queue = PresentationQueue(self.dir)
        self.assertEqual(queue.next()['requestId'], 'delivery')
        queue.defer()
        self.assertEqual(queue.next()['requestId'], 'session')
        queue.finish({'requestId': 'session', 'ok': True, 'quiet': True})
        self.assertEqual(queue.next()['requestId'], 'delivery')
        queue.retry()
        # Outside the preference window the oldest request is first again.
        write(self.dir, 'session2', project='synthetic', origin='session')
        queue.busy_at = time.time() - presentation.BUSY_PREFERENCE_SECONDS - 1
        self.assertEqual(queue.next()['requestId'], 'delivery')
        self.assertTrue(newer.with_suffix('.presented').exists())

    def test_quiet_receipt_is_presented_for_session_connections(self):
        write(self.dir, 'session', project='synthetic', origin='session')
        queue = PresentationQueue(self.dir)
        payload = queue.next()
        self.assertTrue(queue.finish({'requestId': payload['requestId'], 'ok': True, 'project_id': 'p1', 'quiet': True}))
        self.assertTrue((self.dir / 'session.presented').exists())
        self.assertTrue(json.loads((self.dir / 'session.receipt').read_text(encoding='utf-8'))['quiet'])


class FakeWindow:
    MINIMIZED, MAXIMIZED, FULL = 1, 2, 4

    def __init__(self, state=0):
        self.state = state
        self.calls = []

    def isMinimized(self):
        return bool(self.state & self.MINIMIZED)

    def windowState(self):
        return self.state

    def setWindowState(self, state):
        self.calls.append(('setWindowState', state))
        self.state = state

    def showNormal(self):
        self.calls.append(('showNormal',))
        self.state = 0

    def raise_(self):
        self.calls.append(('raise_',))

    def activateWindow(self):
        self.calls.append(('activateWindow',))


class WindowRuleTests(unittest.TestCase):
    def test_quiet_or_failed_receipt_never_touches_the_window(self):
        for receipt in ({'ok': True, 'quiet': True}, {'ok': False}, {'ok': 'yes'}, None, []):
            window = FakeWindow(FakeWindow.MAXIMIZED)
            self.assertFalse(bring_forward(window, receipt, FakeWindow.MINIMIZED))
            self.assertEqual(window.calls, [])

    def test_delivery_keeps_maximized_and_full_screen(self):
        for state in (FakeWindow.MAXIMIZED, FakeWindow.FULL, 0):
            window = FakeWindow(state)
            self.assertTrue(bring_forward(window, {'ok': True}, FakeWindow.MINIMIZED))
            self.assertEqual(window.state, state)
            self.assertEqual(window.calls, [('raise_',), ('activateWindow',)])

    def test_minimized_delivery_restores_previous_state(self):
        window = FakeWindow(FakeWindow.MINIMIZED | FakeWindow.MAXIMIZED)
        bring_forward(window, {'ok': True}, FakeWindow.MINIMIZED)
        self.assertEqual(window.state, FakeWindow.MAXIMIZED)
        self.assertNotIn(('showNormal',), window.calls)

    def test_desktop_shell_uses_the_rule(self):
        source = (APP / 'central_desktop.py').read_text(encoding='utf-8')
        self.assertNotIn('window.showNormal()', source)
        self.assertIn('bring_forward(window,receipt,Qt.WindowState.WindowMinimized)', source)
        self.assertIn("if result=='busy':presentation_queue.defer()", source)
        self.assertIn('runJavaScript(dispatch_script(payload),dispatched)', source)

    def test_real_qt_window_states(self):
        try:
            import PySide6  # noqa: F401
        except ImportError:
            self.skipTest('PySide6 indisponível')
        code = textwrap.dedent('''
            import json, os, sys
            os.environ['QT_QPA_PLATFORM'] = 'offscreen'
            sys.path.insert(0, sys.argv[1])
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication, QMainWindow
            from central_presentation import bring_forward
            app = QApplication([]); w = QMainWindow(); w.resize(800, 600); out = {}
            for label, setup in (('maximized', w.showMaximized), ('fullscreen', w.showFullScreen)):
                setup(); app.processEvents()
                before = w.windowState()
                bring_forward(w, {'ok': True}, Qt.WindowState.WindowMinimized); app.processEvents()
                out[label] = [str(before), str(w.windowState())]
                quiet = bring_forward(w, {'ok': True, 'quiet': True}, Qt.WindowState.WindowMinimized)
                out[label + '_quiet'] = quiet
            w.showNormal(); app.processEvents()
            w.setWindowState(Qt.WindowState.WindowMinimized | Qt.WindowState.WindowMaximized); app.processEvents()
            bring_forward(w, {'ok': True}, Qt.WindowState.WindowMinimized); app.processEvents()
            out['minimized_from_maximized'] = [bool(w.isMinimized()), bool(w.isMaximized())]
            print(json.dumps(out))
        ''')
        child = subprocess.run([sys.executable, '-c', code, str(APP)], capture_output=True, text=True, timeout=60)
        if child.returncode != 0 and 'PySide6' in child.stderr:
            self.skipTest('Qt indisponível neste Python')
        self.assertEqual(child.returncode, 0, child.stderr)
        out = json.loads(child.stdout.strip().splitlines()[-1])
        self.assertEqual(out['maximized'][0], out['maximized'][1])
        self.assertIn('Maximized', out['maximized'][1])
        self.assertIn('FullScreen', out['fullscreen'][1])
        self.assertFalse(out['maximized_quiet'])
        self.assertEqual(out['minimized_from_maximized'], [False, True])


NODE_HARNESS = r'''
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const events = [];
globalThis.window = {megabrainReady: input.ready, dispatchEvent: e => events.push({type: e.type, detail: e.detail})};
if (input.busy === 'throws') window.megabrainBusy = () => { throw new Error('x'); };
else if (input.busy !== null) window.megabrainBusy = () => input.busy;
globalThis.CustomEvent = class { constructor(type, init) { this.type = type; this.detail = init.detail; } };
const result = (0, eval)(input.code);
console.log(JSON.stringify({result, events, cleared: window.megabrainPresentationResult === null}));
'''


@unittest.skipUnless(shutil.which('node'), 'node indisponível')
class DispatchScriptTests(unittest.TestCase):
    def run_script(self, payload, busy, ready=True):
        data = json.dumps({'code': dispatch_script(payload), 'busy': busy, 'ready': ready})
        child = subprocess.run([shutil.which('node'), '-e', NODE_HARNESS], input=data, capture_output=True,
                               text=True, encoding='utf-8', timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        return json.loads(child.stdout)

    def test_delivery_waits_while_busy(self):
        out = self.run_script({'path': 'x.html', 'requestId': 'r'}, busy=True)
        self.assertEqual(out['result'], 'busy')
        self.assertEqual(out['events'], [])
        self.assertFalse(out['cleared'])

    def test_delivery_dispatches_when_free_or_guard_absent_or_broken(self):
        for busy in (False, None, 'throws'):
            out = self.run_script({'path': 'x.html', 'requestId': 'r'}, busy=busy)
            self.assertIs(out['result'], True)
            self.assertEqual(out['events'][0]['type'], 'mb-present')
            self.assertEqual(out['events'][0]['detail']['path'], 'x.html')

    def test_session_notice_is_not_gated(self):
        out = self.run_script({'project': 'p', 'origin': 'session', 'requestId': 'r'}, busy=True)
        self.assertIs(out['result'], True)
        self.assertEqual(out['events'][0]['detail']['origin'], 'session')

    def test_not_ready_and_markup_escape(self):
        self.assertIs(self.run_script({'path': 'x.html'}, busy=False, ready=False)['result'], False)
        code = dispatch_script({'path': '</script><b>.html'})
        self.assertNotIn('</script>', code)
        out = self.run_script({'path': '</script><b>.html'}, busy=False)
        self.assertEqual(out['events'][0]['detail']['path'], '</script><b>.html')


if __name__ == '__main__':
    unittest.main()
