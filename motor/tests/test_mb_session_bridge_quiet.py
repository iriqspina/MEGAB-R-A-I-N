"""261017 WP3: a session registration never pulls the open app to the front.

Uses a temporary central only. The live app (8766/8767) is never contacted:
the health check is either patched or pointed at a local test server.
"""
import contextlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "apps/megabrain-dashboard"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = load("test_quiet_session_bridge", ROOT / "bin/mb-session-bridge.py")
sys.path.insert(0, str(APP_DIR))
from central_presentation import PresentationQueue  # noqa: E402
from central_session_connections import snapshot  # noqa: E402


class QuietBridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.central = self.root / "central"
        self.app = self.central / "apps/megabrain-dashboard"
        self.queue = self.app / "data/open-requests"

    def launcher(self):
        launcher = self.app / "bootstrap/MegaBrain.exe"
        launcher.parent.mkdir(parents=True, exist_ok=True)
        launcher.touch()

    def connect(self, **kwargs):
        return BRIDGE.connect(self.project, central=self.central, env={}, **kwargs)

    def requests(self):
        return [json.loads(p.read_text(encoding="utf-8")) for p in self.queue.glob("*.json")]

    def test_open_app_hook_session_queues_quietly_without_launcher(self):
        self.launcher()
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=True), \
                mock.patch.object(BRIDGE.subprocess, "Popen") as popen:
            first = self.connect(hook={"session_id": "claude-stable"}, application="Claude Code")
            # resume/compact of the same session: no new request, no launcher.
            second = self.connect(hook={"session_id": "claude-stable"})
        popen.assert_not_called()
        self.assertEqual(first["identity_source"], "hook.session_id")
        self.assertEqual(first["presentation_state"], "queued")
        self.assertEqual(first["launcher"], "not_called_app_open")
        self.assertEqual(first["presentation_request_id"], second["presentation_request_id"])
        [request] = self.requests()
        self.assertEqual(request["origin"], "session")
        self.assertEqual(request["project"], str(self.project.resolve()))
        self.assertEqual(request["id"], first["presentation_request_id"])
        self.assertFalse(list(self.queue.glob("*.tmp")))

    def test_open_app_does_not_need_launcher_file(self):
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=True), \
                mock.patch.object(BRIDGE.subprocess, "Popen") as popen:
            row = self.connect(session_id="codex-thread")
        popen.assert_not_called()
        self.assertEqual(row["presentation_state"], "queued")
        self.assertIsNone(row["error"])

    def test_closed_app_still_starts_launcher_once(self):
        self.launcher()
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=False), \
                mock.patch.object(BRIDGE.subprocess, "Popen") as popen:
            first = self.connect(session_id="zcode-session", application="ZCode")
            self.connect(session_id="zcode-session")
        popen.assert_called_once()
        self.assertEqual(first["launcher"], "called")
        self.assertEqual(self.requests()[0]["origin"], "session")

    def test_closed_app_without_launcher_is_unavailable(self):
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=False):
            row = self.connect(session_id="s")
        self.assertEqual(row["error"], "native_launcher_unavailable")
        self.assertFalse(self.queue.exists())

    def test_invocation_without_identity_also_skips_launcher_when_open(self):
        self.launcher()
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=True), \
                mock.patch.object(BRIDGE.subprocess, "Popen") as popen:
            row = self.connect()
        popen.assert_not_called()
        self.assertEqual(row["identity_source"], "invocation_uuid")

    def test_no_open_still_wins(self):
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=True) as running:
            row = self.connect(session_id="s", no_open=True)
        running.assert_not_called()
        self.assertEqual(row["error"], "presentation_not_requested")
        self.assertFalse(self.queue.exists())

    def test_quiet_receipt_marks_session_presented(self):
        with mock.patch.object(BRIDGE, "_native_app_running", return_value=True):
            row = self.connect(hook={"session_id": "claude-stable"})
        queue = PresentationQueue(self.queue)
        payload = queue.next()
        self.assertEqual(payload["origin"], "session")
        self.assertNotIn("path", payload)
        self.assertTrue(queue.finish({"requestId": payload["requestId"], "ok": True, "project_id": "p1", "quiet": True}))
        sources = SimpleNamespace(lock=threading.RLock(), projects={"p1": self.project})
        [session] = snapshot(self.app, sources)["sessions"]
        self.assertEqual(session["id"], row["id"])
        self.assertEqual(session["state"], "presented")

    def test_hook_cli_with_application_reaches_quiet_path(self):
        payload = dict(cwd=str(self.project), session_id="cli-hook", source="compact")
        with mock.patch.object(BRIDGE.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(BRIDGE, "CENTRAL", self.central), \
                mock.patch.object(BRIDGE, "_native_app_running", return_value=True), \
                mock.patch.object(BRIDGE.subprocess, "Popen") as popen, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            # main() uses connect's default central; patch it through the default argument.
            with mock.patch.object(BRIDGE.connect, "__kwdefaults__", {**BRIDGE.connect.__kwdefaults__, "central": self.central}):
                self.assertEqual(BRIDGE.main(["--hook", "--application", "Claude Code", "--json"]), 0)
        popen.assert_not_called()
        row = json.loads(out.getvalue())
        self.assertEqual(row["identity_source"], "hook.session_id")
        self.assertEqual(row["application"], "Claude Code")
        self.assertEqual(row["launcher"], "not_called_app_open")


class NativeAppDetectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.central = Path(temp.name)
        self.runtime = self.central / "apps/megabrain-dashboard/data/central-runtime.json"
        self.runtime.parent.mkdir(parents=True)

    def write(self, **info):
        self.runtime.write_text(json.dumps(info), encoding="utf-8")

    def test_requires_runtime_loaded_live_pid_and_health(self):
        self.assertFalse(BRIDGE._native_app_running(self.central))
        with mock.patch.object(BRIDGE, "_app_health", return_value=True):
            self.write(loaded=True, pid=os.getpid())
            self.assertTrue(BRIDGE._native_app_running(self.central))
            for info in (dict(loaded=False, pid=os.getpid()), dict(loaded=True, pid=True),
                         dict(loaded=True, pid=-1), dict(loaded=True)):
                self.write(**info)
                self.assertFalse(BRIDGE._native_app_running(self.central), info)
            self.runtime.write_text("{", encoding="utf-8")
            self.assertFalse(BRIDGE._native_app_running(self.central))
        self.write(loaded=True, pid=os.getpid())
        with mock.patch.object(BRIDGE, "_app_health", return_value=False):
            self.assertFalse(BRIDGE._native_app_running(self.central))

    def test_dead_pid_is_not_running_and_check_never_kills(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait(timeout=30)
        self.assertFalse(BRIDGE._pid_alive(child.pid))
        self.assertTrue(BRIDGE._pid_alive(os.getpid()))
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            self.assertTrue(BRIDGE._pid_alive(sleeper.pid))
            self.assertIsNone(sleeper.poll())
        finally:
            sleeper.kill()
            sleeper.wait(timeout=30)

    def test_health_reads_only_the_central_identity(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            body = b"{}"
            methods = []

            def do_GET(self):
                Handler.methods.append(self.command)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(Handler.body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/api/health"
        self.assertNotIn(server.server_address[1], (8766, 8767))
        Handler.body = json.dumps({"app": "megabrain-central"}).encode()
        self.assertTrue(BRIDGE._app_health(url))
        Handler.body = json.dumps({"app": "other"}).encode()
        self.assertFalse(BRIDGE._app_health(url))
        Handler.body = b"not json"
        self.assertFalse(BRIDGE._app_health(url))
        self.assertEqual(set(Handler.methods), {"GET"})
        server.shutdown()
        server.server_close()
        self.assertFalse(BRIDGE._app_health(url))


if __name__ == "__main__":
    unittest.main()
