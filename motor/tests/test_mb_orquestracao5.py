"""Offline project-boundary and evidence tests for the orchestration driver."""
import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

CENTRAL = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("orquestracao5_under_test", CENTRAL / "bin/mb-orquestracao.py")
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)


class LocalWriter:
    @staticmethod
    def atomic(path, content):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")


class Orquestracao5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name).resolve() / "project"
        self.project.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def put(self, relative, text):
        target = self.project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def test_root_layout_captures_hashes_and_declares_absences(self):
        source = self.put("ESTADO.md", "Estado confirmado: revisão pendente.")
        rows = {row["role"]: row for row in driver.capture(self.project)}
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows["estado"]["path"], str(source))
        self.assertEqual(rows["estado"]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(rows["estado"]["content"], source.read_text(encoding="utf-8"))
        self.assertEqual(rows["estado"]["status"], "INTEGRAL")
        for role in ("handoff", "decisoes", "licoes", "instrucoes", "indice-fontes"):
            self.assertEqual(rows[role], {"role": role, "status": "AUSENTE"})

    def test_central_layout_resolves_all_declared_sources(self):
        mapping = {"estado": "memoria/estado/ESTADO.md", "handoff": "memoria/estado/HANDOFF.md",
                   "decisoes": "memoria/estado/DECISOES.md", "licoes": "memoria/nucleo/licoes-megabrain.md",
                   "instrucoes": "AGENTS.md", "indice-fontes": "memoria/cerebro/INDICE.md"}
        for role, relative in mapping.items():
            self.put(relative, role)
        rows = {row["role"]: row for row in driver.capture(self.project)}
        for role, relative in mapping.items():
            self.assertEqual(rows[role]["path"], str(self.project / relative))
            self.assertEqual(rows[role]["content"], role)

    def test_excerpt_keeps_decision_tail_and_hashes_entire_source(self):
        source = self.put("DECISOES.md", "OLD" + "a" * 6000 + "NEW")
        self.put("ESTADO.md", "FIRST" + "b" * 6000 + "LAST")
        rows = {row["role"]: row for row in driver.capture(self.project)}
        self.assertTrue(rows["decisoes"]["content"].endswith("NEW"))
        self.assertTrue(rows["estado"]["content"].startswith("FIRST"))
        self.assertEqual(len(rows["decisoes"]["content"]), 5000)
        self.assertEqual(rows["decisoes"]["status"], "RECORTE")
        self.assertEqual(rows["decisoes"]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_explicit_source_records_content_and_hash(self):
        source = self.put("cerebro/raw/source.txt", "Fonte autorizada.")
        rows = driver.capture(self.project, ["cerebro/raw/source.txt"])
        explicit = rows[-1]
        self.assertEqual(explicit["role"], "fonte-explicita")
        self.assertEqual(explicit["path"], str(source))
        self.assertEqual(explicit["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(explicit["content"], "Fonte autorizada.")

    def test_external_source_absolute_and_parent_escape_rejected(self):
        outside = self.project.parent / "outside.txt"
        outside.write_text("External", encoding="utf-8")
        for source in (str(outside), "../outside.txt"):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, "sai do projeto"):
                driver.capture(self.project, [source])

    def test_explicit_source_limit_is_bytes_and_rejects_above_20000(self):
        self.put("boundary.txt", "a" * 20000)
        self.assertEqual(driver.capture(self.project, ["boundary.txt"])[-1]["status"], "INTEGRAL")
        for name, content in (("large.txt", "a" * 20001), ("unicode.txt", "é" * 10001)):
            self.put(name, content)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "20 KB"):
                driver.capture(self.project, [name])

    def test_inbox_uses_human_folder_without_overwriting_existing_delivery(self):
        run = self.project / ".automations/runs/test-run"
        run.mkdir(parents=True)
        (run / "candidate.md").write_text("Original", encoding="utf-8")
        destination = driver.inbox(self.project, run, {"status": "review_approved", "review_approved": True}, LocalWriter)
        self.assertEqual(destination, self.project / "00_PARA-VOCE/orquestracao5-test-run")
        summary = destination / "RESULTADO.md"
        candidate = destination / "CANDIDATO.md"
        self.assertIn("NÃO EXECUTADA", summary.read_text(encoding="utf-8"))
        summary.write_text("Human edited summary", encoding="utf-8")
        candidate.write_text("Human edited candidate", encoding="utf-8")
        (run / "candidate.md").write_text("New generated candidate", encoding="utf-8")
        driver.inbox(self.project, run, {"status": "needs_attention"}, LocalWriter)
        self.assertEqual(summary.read_text(encoding="utf-8"), "Human edited summary")
        self.assertEqual(candidate.read_text(encoding="utf-8"), "Human edited candidate")
        self.assertIn(str(destination), (run / "HANDOFF.md").read_text(encoding="utf-8"))
        self.assertFalse((self.project / "HANDOFF.md").exists())

    def test_inbox_failure_without_candidate_still_creates_handoff(self):
        run = self.project / ".automations/runs/failed"
        run.mkdir(parents=True)
        destination = driver.inbox(self.project, run, {"status": "needs_attention"}, LocalWriter)
        self.assertTrue((destination / "RESULTADO.md").is_file())
        self.assertFalse((destination / "CANDIDATO.md").exists())
        self.assertTrue((run / "HANDOFF.md").is_file())

    def test_loading_engine_for_second_project_preserves_first_root(self):
        first = self.project / ".automations"
        second = self.project.parent / "project-two/.automations"
        with patch.dict(os.environ, {}, clear=False):
            one = driver.load_engine(first)
            two = driver.load_engine(second)
            self.assertEqual(one.ROOT, first)
            self.assertEqual(two.ROOT, second)
            self.assertIsNot(one, two)
            run_one = one.create_run({}, {}, "probe")
            run_two = two.create_run({}, {}, "probe")
            self.assertEqual(run_one.parent, first / "runs")
            self.assertEqual(run_two.parent, second / "runs")
            with self.assertRaises(one.RunError):
                one.resolve_run(str(run_two))


if __name__ == "__main__":
    unittest.main()
