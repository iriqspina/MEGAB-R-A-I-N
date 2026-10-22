"""Session identity, native presentation and startup isolation contracts."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "bin" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BRIDGE = load("test_session_bridge", "mb-session-bridge.py")
STARTUP = load("test_session_startup", "mb-inicio-sessao.py")
sys.path.insert(0, str(ROOT / "bin"))
OPENING = load("test_session_opening", "mb-abertura-sessao.py")


class SessionBridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.central = self.root / "central"
        self.app = self.central / "apps/megabrain-dashboard"
        self.records = self.app / "data/session-connections"

    def connect(self, **kwargs):
        return BRIDGE.connect(self.project, central=self.central, env={}, **kwargs)

    def native(self):
        launcher = self.app / "bootstrap/MegaBrain.exe"
        launcher.parent.mkdir(parents=True)
        launcher.touch()
        scripts = self.central / "bin"
        scripts.mkdir()
        (scripts / "mb-abrir-entrega.py").write_text(
            (ROOT / "bin/mb-abrir-entrega.py").read_text(encoding="utf-8"), encoding="utf-8")

    def test_missing_launcher_still_records_without_secret(self):
        row = self.connect(session_id="sensitive-session-value")
        persisted = json.loads(next(self.records.glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(row, persisted)
        self.assertEqual(row["error"], "native_launcher_unavailable")
        self.assertNotIn("sensitive-session-value", json.dumps(row))
        self.assertEqual(row["application"], "Invocação avulsa")
        self.assertEqual(len(row["id"]), 24)
        self.assertTrue(row["started_at"].endswith("+00:00"))

    def test_stable_identity_preserves_start_and_does_not_reopen(self):
        self.native()
        def launch(*args, **kwargs):
            row = json.loads(next(self.records.glob("*.json")).read_text(encoding="utf-8"))
            self.assertEqual(row["presentation_state"], "queued")
            self.assertTrue(row["presentation_request_id"])
        with mock.patch.object(BRIDGE.subprocess, "Popen", side_effect=launch) as launcher:
            first = self.connect(session_id="stable", application="Editor")
            second = self.connect(session_id="stable", source="mb-inicio-sessao")
        self.assertEqual(launcher.call_count, 1)
        self.assertEqual(first["started_at"], second["started_at"])
        self.assertEqual(first["presentation_request_id"], second["presentation_request_id"])
        self.assertEqual(len(list((self.app / "data/open-requests").glob("*.json"))), 1)
        self.assertFalse(list(self.records.glob("*.tmp")))

    def test_launcher_failure_retains_request_but_not_connected_claim(self):
        self.native()
        with mock.patch.object(BRIDGE.subprocess, "Popen", side_effect=OSError("token secret")) as launcher:
            first = self.connect(session_id="stable")
            second = self.connect(session_id="stable")
        self.assertEqual(first["presentation_state"], "unavailable")
        self.assertEqual(second["presentation_state"], "unavailable")
        self.assertTrue(first["presentation_request_id"])
        self.assertEqual(launcher.call_count, 1)
        self.assertNotIn("secret", str(first))

    def test_simultaneous_hooks_enqueue_and_launch_once(self):
        self.native()
        with mock.patch.object(BRIDGE.subprocess, "Popen") as launcher:
            with ThreadPoolExecutor(max_workers=4) as pool:
                rows = list(pool.map(lambda _: self.connect(session_id="same-hook"), range(4)))
        self.assertEqual(launcher.call_count, 1)
        self.assertEqual(len({row["presentation_request_id"] for row in rows}), 1)
        self.assertEqual(len(list(self.records.glob("*.lock"))), 1)

    def test_residual_lock_file_does_not_block_session(self):
        self.native()
        import hashlib
        session_key = hashlib.sha256(b"residual-session").hexdigest()[:24]
        self.records.mkdir(parents=True)
        residual = self.records / f"{session_key}.lock"
        residual.write_bytes(b"0")
        with mock.patch.object(BRIDGE.subprocess, "Popen") as launcher:
            row = self.connect(session_id="residual-session")
        self.assertEqual(row["presentation_state"], "queued")
        launcher.assert_called_once()
        self.assertTrue(residual.is_file())

    def test_process_exit_releases_os_lock_without_removing_file(self):
        self.records.mkdir(parents=True)
        target = self.records / "crashed.json"
        code = (
            "import importlib.util, os; from pathlib import Path; "
            f"spec=importlib.util.spec_from_file_location('bridge', {str(ROOT / 'bin/mb-session-bridge.py')!r}); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            f"guard=module._session_lock(Path({str(target)!r})); guard.__enter__(); os._exit(0)"
        )
        child = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=10)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertTrue(target.with_suffix(".lock").exists())
        with BRIDGE._session_lock(target):
            pass
        self.assertEqual(target.with_suffix(".lock").read_bytes(), b"0")

    def test_same_session_changed_project_creates_matching_request(self):
        self.native()
        other = self.root / "second-project"
        other.mkdir()
        with mock.patch.object(BRIDGE.subprocess, "Popen") as launcher:
            first = self.connect(session_id="moving-session")
            second = BRIDGE.connect(other, central=self.central, env={}, session_id="moving-session")
            third = BRIDGE.connect(other, central=self.central, env={}, session_id="moving-session")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["started_at"], second["started_at"])
        self.assertNotEqual(first["presentation_request_id"], second["presentation_request_id"])
        self.assertEqual(second["presentation_request_id"], third["presentation_request_id"])
        request = json.loads((self.app / "data/open-requests" / (second["presentation_request_id"] + ".json")).read_text())
        self.assertEqual(request["project"], str(other.resolve()))
        self.assertEqual(launcher.call_count, 2)

    def test_no_open_is_registration_only_and_invocations_are_distinct(self):
        self.native()
        with mock.patch.object(BRIDGE.subprocess, "Popen") as launcher:
            first = self.connect(no_open=True)
            second = self.connect(no_open=True)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(first["identity_source"], "invocation_uuid")
        self.assertEqual(first["error"], "presentation_not_requested")
        self.assertFalse((self.app / "data/open-requests").exists())
        launcher.assert_not_called()

    def test_environment_and_hook_identity_have_explicit_origin(self):
        row = BRIDGE.connect(self.project, central=self.central,
                             env={"CODEX_THREAD_ID": "c", "MB_CLIENT_APP": "Codex Desktop"}, no_open=True)
        self.assertEqual(row["identity_source"], "CODEX_THREAD_ID")
        self.assertEqual(row["application"], "Codex Desktop")
        hooked = self.connect(hook={"session_id": "h"}, no_open=True)
        self.assertEqual(hooked["identity_source"], "hook.session_id")

    def test_hook_identity_and_application_override_inherited_environment(self):
        inherited = {"MB_SESSION_ID": "parent-megabrain", "CODEX_THREAD_ID": "parent-codex", "MB_CLIENT_APP": "Codex"}
        hook = {"session_id": "child-claude", "application": "Claude Code"}
        hooked = BRIDGE.connect(self.project, central=self.central, env=inherited, hook=hook, no_open=True)
        direct = BRIDGE.connect(self.project, central=self.central, env={}, session_id="child-claude", no_open=True)
        self.assertEqual(hooked["id"], direct["id"])
        self.assertEqual(hooked["identity_source"], "hook.session_id")
        self.assertEqual(hooked["application"], "Claude Code")
        explicit = BRIDGE.connect(self.project, central=self.central, env=inherited, hook=hook,
                                  session_id="explicit", application="ZCode", no_open=True)
        self.assertEqual(explicit["identity_source"], "argument")
        self.assertEqual(explicit["application"], "ZCode")

    def test_hook_cli_uses_cwd_without_storing_raw_payload(self):
        payload = dict(cwd=str(self.project), session_id="h", application="Claude Code", credential="secret")
        with mock.patch.object(BRIDGE.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(BRIDGE, "connect", return_value={"presentation_state": "queued"}) as connect, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(BRIDGE.main(["--hook", "--json", "--no-open"]), 0)
        self.assertEqual(connect.call_args.args[0], str(self.project))
        self.assertEqual(connect.call_args.kwargs["application"], "Claude Code")
        self.assertNotIn("credential", connect.call_args.kwargs["hook"])

    def test_startup_only_registers_from_main(self):
        data = dict(pronto=True, aprendizado_visual={}, instrucao_para_ia="", skills=[])
        with mock.patch.object(STARTUP, "resumo", return_value=data), \
                mock.patch.object(STARTUP, "conectar_app", return_value={"presentation_state": "unavailable"}) as connect, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(STARTUP.main(["--json", "--project", str(self.project), "--no-app"]), 0)
        self.assertEqual(connect.call_count, 1)
        self.assertTrue(connect.call_args.args[3])

    def test_summary_does_not_register_a_new_session(self):
        with mock.patch.object(STARTUP, "catalogo", return_value=[]), \
                mock.patch.object(STARTUP, "leitura_uso", return_value={}), \
                mock.patch.object(STARTUP, "contexto_visual", return_value={}), \
                mock.patch.object(STARTUP, "conectar_app") as connect:
            STARTUP.resumo(self.central)
            STARTUP.resumo(self.central)
        connect.assert_not_called()

    def test_startup_hook_propagates_client_session_and_filters_secrets(self):
        payload = dict(cwd=str(self.project), session_id="claude-real-id", application="Claude Code", credential="secret")
        data = dict(pronto=True, aprendizado_visual={}, instrucao_para_ia="", skills=[])
        with mock.patch.object(STARTUP, "resumo", return_value=data), \
                mock.patch.object(STARTUP.sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(STARTUP, "conectar_app", return_value={"presentation_state": "unavailable"}) as connect, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(STARTUP.main(["--json", "--hook", "--no-app"]), 0)
        self.assertEqual(connect.call_args.args[0], self.project)
        self.assertEqual(connect.call_args.args[1], "Claude Code")
        self.assertEqual(connect.call_args.args[4]["session_id"], "claude-real-id")
        self.assertNotIn("credential", connect.call_args.args[4])

    def test_opening_dry_run_or_arbitrary_directory_never_loads_bridge(self):
        for dry in (True, False):
            if dry:
                (self.project / ".mb-origem.json").write_text("{}")
            else:
                (self.project / ".mb-origem.json").unlink(missing_ok=True)
            cv = mock.Mock()
            cv.parse_versao.return_value = (None, None)
            cv.ler_versao.return_value = "test-version"
            with mock.patch.object(OPENING, "achar_central", return_value=(ROOT, "test")), \
                    mock.patch.object(OPENING, "carregar_check_version", return_value=cv), \
                    mock.patch.object(OPENING, "estado_git", return_value={"estado": "ok", "resumo": "ok"}), \
                    mock.patch.object(OPENING.importlib.util, "spec_from_file_location") as loader, \
                    contextlib.redirect_stdout(io.StringIO()):
                args = ["--project", str(self.project), "--offline"] + (["--seco"] if dry else [])
                self.assertEqual(OPENING.main(args), 0)
            loader.assert_not_called()
        self.assertFalse((self.project / ".mb-log").exists())

    def test_startup_resolves_central_from_bin(self):
        self.assertEqual(STARTUP.projeto_sessao(ROOT / "bin"), ROOT)
        self.assertEqual(OPENING.resolver_projeto(ROOT / "bin"), ROOT)


if __name__ == "__main__":
    unittest.main()
