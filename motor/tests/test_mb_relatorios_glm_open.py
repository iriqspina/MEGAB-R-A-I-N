"""Canonical presentation and zero-model monitoring contracts.

Synthetic gate fixtures are test data, never evidence of visual quality.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bin"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OPEN = load("glm_report_open", ROOT / "bin/mb-abrir-entrega.py")
MONITOR = load("glm_report_monitor", ROOT / "bin/mb-auditar-relatorios-glm.py")
FIXTURES = load("glm_report_fixture_only", ROOT / "motor/tests/test_mb_relatorios_glm.py")


class ReportPresentation(unittest.TestCase):
    def setUp(self):
        self.fixture = FIXTURES.ReportGate()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root
        self.report = self.fixture.report
        self.tech = self.root / ".automations/relatorios-glm"
        self.app = self.root / "native-app"
        patch = mock.patch.object(OPEN, "APP", self.app)
        patch.start()
        self.addCleanup(patch.stop)

    def row(self):
        return json.loads((self.tech / "auditoria.json").read_text(encoding="utf-8"))["reports"][str(self.report.relative_to(self.root))]

    def queue(self):
        return json.loads((self.tech / "fila-correcao.json").read_text(encoding="utf-8"))["items"]

    def test_unknown_html_blocks_unless_explicit_candidate_preview(self):
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(OPEN.main([str(self.report), "--queue-only", "--json", "--preview"]), 0)
        result = json.loads(out.getvalue())
        self.assertFalse(result["opened"])
        self.assertEqual(result["report_policy"]["status"], "CANDIDATO_PREVIA")
        self.assertEqual(result["report_policy"]["gate_status"], "NAO_VERIFICADO")
        self.assertFalse(result["report_policy"]["delivery"])
        self.assertIn("NÃO VERIFICADO", err.getvalue())
        self.assertEqual(len(self.queue()), 1)
        self.assertFalse((self.tech / "baseline.json").exists())

    def test_frozen_legacy_access_is_preserved_but_not_certified(self):
        MONITOR.freeze_baseline(self.root)
        destination, request = OPEN.enqueue(self.report)
        self.assertTrue(destination.is_file())
        self.assertEqual(request["report_policy"]["status"], "LEGADO_NAO_AUDITADO")
        self.assertEqual(self.queue(), [])

    def test_new_or_regenerated_unregistered_html_enters_next_cycle_queue(self):
        baseline = MONITOR.freeze_baseline(self.root)
        self.report.write_text("<html>regenerated without producer proof</html>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)
        self.assertEqual(self.row()["status"], "NAO_VERIFICADO_ALTERADO")
        self.assertEqual(len(self.queue()), 1)
        self.assertEqual(MONITOR.freeze_baseline(self.root), baseline)

    def test_registered_incomplete_manifest_blocks_before_native_queue(self):
        self.fixture.start()
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)
        self.assertFalse((self.app / "data/open-requests").exists())
        self.assertEqual(self.row()["status"], "BLOQUEADO")
        self.assertEqual(len(self.queue()), 1)

    def test_ready_but_undelivered_manifest_stays_blocked(self):
        fixture = self.fixture
        fixture.start()
        FIXTURES.glm.revise(self.root, fixture.manifest, fixture.write_json("review.json", fixture.review()))
        FIXTURES.glm.verify(self.root, fixture.manifest, fixture.write_json("inspection.json", fixture.inspection()))
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)

    def test_current_final_proof_passes_but_later_edit_blocks(self):
        self.fixture.start()
        self.fixture.finish()
        _, request = OPEN.enqueue(self.report)
        self.assertEqual(request["report_policy"]["status"], "CONFORME")
        self.assertEqual(self.queue(), [])
        self.report.write_text("<html>post-review edit</html>", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)
        self.assertEqual(len(list((self.app / "data/open-requests").glob("*.json"))), 1)
        self.assertEqual(self.row()["status"], "BLOQUEADO")

    def test_removing_index_never_launders_a_previously_registered_report(self):
        MONITOR.freeze_baseline(self.root)
        self.fixture.start()
        self.fixture.finish()
        OPEN.enqueue(self.report)
        (self.tech / "index.json").unlink()
        with self.assertRaisesRegex(ValueError, "Associacao"):
            OPEN.enqueue(self.report)
        self.assertTrue(self.row()["registration_observed"])

    def test_missing_manifest_and_corrupt_index_fail_closed(self):
        self.fixture.start()
        self.fixture.manifest.unlink()
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)
        (self.tech / "index.json").write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)

    def test_manifest_changing_during_gate_check_requires_fresh_read(self):
        self.fixture.start()
        self.fixture.finish()
        original = FIXTURES.glm.status
        def concurrent_edit(project, manifest):
            result = original(project, manifest)
            manifest.write_text(manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            return result
        with mock.patch.object(FIXTURES.glm, "status", side_effect=concurrent_edit):
            row = MONITOR.audit_report(self.report)
        self.assertEqual(row["status"], "BLOQUEADO")
        self.assertIn("durante a auditoria", row["reason"])

    def test_project_and_non_html_opening_are_not_report_gated(self):
        with mock.patch.object(OPEN, "report_policy", side_effect=AssertionError("called")):
            _, request = OPEN.enqueue(project=self.root)
        self.assertEqual(request["project"], str(self.root))
        document = self.root / "editavel.docx"
        document.write_bytes(b"test fixture")
        _, request = OPEN.enqueue(document)
        self.assertNotIn("report_policy", request)

    def test_monitor_unchanged_state_has_no_rewrite_or_model_call(self):
        first = MONITOR.audit(project=self.root)
        state = self.tech / "auditoria.json"
        queue = self.tech / "fila-correcao.json"
        before = (state.stat().st_mtime_ns, queue.stat().st_mtime_ns, state.read_bytes(), queue.read_bytes())
        with mock.patch.object(MONITOR, "_save", side_effect=AssertionError("unchanged rewrite")):
            second = MONITOR.audit(project=self.root)
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        self.assertEqual(second["model_calls"], 0)
        self.assertEqual(before, (state.stat().st_mtime_ns, queue.stat().st_mtime_ns, state.read_bytes(), queue.read_bytes()))

    def test_read_only_and_missing_registered_report_are_visible(self):
        result = MONITOR.audit(project=self.root, write=False)
        self.assertFalse(result["changed"])
        self.assertFalse(self.tech.exists())
        self.fixture.start()
        self.report.unlink()
        result = MONITOR.audit(project=self.root)
        self.assertEqual(result["projects"][0]["reports"][0]["status"], "INDISPONIVEL")
        self.assertEqual(len(self.queue()), 1)

    def test_preview_of_approved_report_is_still_labeled_candidate(self):
        self.fixture.start()
        self.fixture.finish()
        _, request = OPEN.enqueue(self.report, preview=True)
        self.assertEqual(request["report_policy"]["status"], "CANDIDATO_PREVIA")
        self.assertFalse(request["report_policy"]["delivery"])

    def test_post_delivery_revocation_reenters_queue_and_blocks_opening(self):
        self.fixture.start()
        self.fixture.finish()
        OPEN.enqueue(self.report)
        central = self.root / "separate-central"
        central.mkdir()
        FIXTURES.glm.revoke(self.root, self.fixture.manifest, "New observed hierarchy defect",
                           [self.fixture.ev / "functional.log"], central=central)
        result = MONITOR.audit(project=self.root)
        self.assertTrue(result["changed"])
        self.assertEqual(self.row()["status"], "BLOQUEADO")
        self.assertEqual(len(self.queue()), 1)
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            OPEN.enqueue(self.report)

    def test_linked_technical_root_never_writes_outside_project(self):
        outside = self.root / "outside"
        outside.mkdir()
        try:
            (self.root / ".automations").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Este Windows nao permite fixture symlink")
        with self.assertRaisesRegex(ValueError, "symlink/junction"):
            MONITOR.audit_report(self.report)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
