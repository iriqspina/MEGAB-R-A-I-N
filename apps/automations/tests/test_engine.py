"""Offline engine contract and recovery tests; no external models or network."""
import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import automations as app


CRITERION = "Inclui marcador verificável"
JOB = {"objective": "Produzir uma proposta", "criteria": [CRITERION],
       "assertions": [{"contains": "READY"}]}
CONFIG = {"central": "unused", "max_rounds": 2, "max_workers": 2,
          "max_input_chars": 100000, "max_output_chars": 100000,
          "timeout_seconds": 10,
          "providers": {p: {"executable": p, "model": "test", "effort": "low"}
                        for p in ("claude", "codex")}}


def review(approved=True):
    return {"approved": approved, "summary": "Inspeção textual",
            "checks": [{"criterion": CRITERION, "passed": approved,
                        "evidence": "Campo content contém READY" if approved else "Falta READY"}],
            "issues": [] if approved else ["Inclua READY"]}


class FakeBackend:
    def __init__(self, candidates=None, approvals=None, barrier=None):
        self.candidates = candidates or ["READY"]
        self.approvals = approvals or [True]
        self.calls = []
        self.counts = {}
        self.lock = threading.Lock()
        self.barrier = barrier

    def __call__(self, provider, kind, packet):
        with self.lock:
            self.calls.append((provider, kind, copy.deepcopy(packet)))
            index = self.counts.get(kind, 0)
            self.counts[kind] = index + 1
        if kind == "plan":
            if self.barrier and "perspectives" not in packet:
                self.barrier.wait(timeout=5)
            return {"summary": provider, "steps": ["Escrever"], "risks": []}
        if kind == "candidate":
            return {"summary": "Proposta", "content": self.candidates[min(index, len(self.candidates)-1)],
                    "limitations": ["Código não executado"]}
        if kind == "review":
            return review(self.approvals[min(index, len(self.approvals)-1)])
        if kind == "probe":
            return {"echo": packet.get("nonce", packet.get("previous", {}).get("reply", "")),
                    "reply": f"Resposta {index}"}
        raise AssertionError(kind)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(app, "ROOT", self.root)
        self.root_patch.start()
        # Any accidental production dispatch fails before executing a CLI.
        self.no_process = patch.object(app.subprocess, "run", side_effect=AssertionError("External dispatch forbidden"))
        self.no_process.start()

    def tearDown(self):
        self.no_process.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def make_run(self, job=None, config=None, mode="run"):
        return app.create_run(copy.deepcopy(config or CONFIG), copy.deepcopy(job or JOB), mode)

    def test_valid_contracts(self):
        app.validate(review(), app.SCHEMAS["review"])
        app.validate_job(JOB)

    def test_contract_rejects_wrong_types_missing_and_extra_fields(self):
        values = [dict(review(), approved=1), {"approved": True}, dict(review(), surprise=True)]
        for value in values:
            with self.subTest(value=value), self.assertRaises(app.RunError):
                app.validate(value, app.SCHEMAS["review"])

    def test_job_rejects_invalid_criteria_and_assertions(self):
        for changed in ({"objective": " "}, {"criteria": []}, {"criteria": [CRITERION, CRITERION]},
                        {"assertions": [{"contains": ""}]}, {"assertions": [{"execute": "anything"}]}):
            with self.subTest(changed=changed), self.assertRaises(app.RunError):
                app.validate_job(dict(JOB, **changed))

    def test_review_rejects_contradictions_and_missing_evidence(self):
        a = review(); a["issues"] = ["Blocking"]
        b = review(); b["checks"][0]["passed"] = False
        c = review(); c["checks"][0]["evidence"] = " "
        d = review(); d["checks"] = []
        for value in (a, b, c, d):
            with self.subTest(value=value), self.assertRaises(app.RunError):
                app.assess(value, JOB["criteria"], "READY", JOB["assertions"])

    def test_assertion_failure_overrides_review_approval(self):
        result = app.assess(review(), JOB["criteria"], "missing", JOB["assertions"])
        self.assertTrue(result["review_approved"])
        self.assertFalse(result["accepted"])
        self.assertFalse(result["automated_checks_passed"])

    def test_no_assertions_never_claim_automated_validation(self):
        result = app.assess(review(), JOB["criteria"], "READY", [])
        self.assertTrue(result["accepted"])
        self.assertFalse(result["automated_checks_passed"])
        self.assertFalse(result["code_executed"])

    def test_loop_repairs_and_passes_review_with_previous_evidence(self):
        run = self.make_run()
        backend = FakeBackend(["draft", "READY"], [False, True])
        result = app.execute(run, backend)
        self.assertEqual(result["status"], "review_approved")
        self.assertEqual(result["rounds"], 2)
        self.assertEqual(backend.counts, {"plan": 1, "candidate": 2, "review": 2})
        repair = [p for _, k, p in backend.calls if k == "candidate"][1]
        self.assertEqual(repair["previous"]["content"], "draft")
        self.assertFalse(repair["checks"]["accepted"])
        self.assertEqual((run / "candidate.md").read_text(encoding="utf-8"), "READY")

    def test_round_limit_preserves_last_candidate(self):
        run = self.make_run()
        backend = FakeBackend(["first", "second"], [False])
        result = app.execute(run, backend)
        self.assertEqual(result["status"], "needs_attention")
        self.assertEqual(backend.counts["review"], 2)
        self.assertEqual((run / "candidate.md").read_text(encoding="utf-8"), "second")

    def test_repeated_candidate_stops_before_another_review(self):
        run = self.make_run()
        backend = FakeBackend(["same"], [False])
        with self.assertRaisesRegex(app.RunError, "Estagnação"):
            app.execute(run, backend)
        self.assertEqual(backend.counts["review"], 1)
        self.assertEqual(app.read_json(run / "state.json")["status"], "needs_attention")

    def test_swarm_really_parallel_and_consolidation_order_stable(self):
        run = self.make_run(dict(JOB, mode="swarm"))
        backend = FakeBackend(barrier=threading.Barrier(2))
        result = app.execute(run, backend)
        self.assertTrue(result["accepted"])
        planner = [p for _, k, p in backend.calls if k == "plan" and "perspectives" in p][0]
        self.assertEqual([p["summary"] for p in planner["perspectives"]], ["claude", "codex"])
        for stage in ("swarm-0", "swarm-1"):
            self.assertTrue((run / "stages" / stage / "response.json").exists())

    def test_completed_resume_makes_no_new_calls(self):
        run = self.make_run()
        backend = FakeBackend()
        first = app.execute(run, backend)
        count = len(backend.calls)
        self.assertEqual(app.execute(run, backend), first)
        self.assertEqual(len(backend.calls), count)

    def test_partial_resume_reuses_succeeded_stage(self):
        run = self.make_run()
        backend = FakeBackend()
        engine = app.Engine(CONFIG, run, backend)
        packet = {"objective": JOB["objective"], "criteria": JOB["criteria"], "context": "",
                  "role": "Planeje a entrega com critérios testáveis.", "perspectives": []}
        engine.call("plan", "claude", "plan", packet)
        self.assertTrue(app.execute(run, backend)["accepted"])
        self.assertEqual(backend.counts["plan"], 1)

    def test_failed_stage_not_retried_automatically(self):
        run = self.make_run()
        backend = FakeBackend()
        engine = app.Engine(CONFIG, run, backend)
        folder = run / "stages" / "stage"
        engine.call("stage", "claude", "plan", {})
        state = app.read_json(folder / "status.json")
        state["status"] = "running"
        app.atomic(folder / "status.json", state)
        with self.assertRaisesRegex(app.RunError, "não será repetida"):
            engine.call("stage", "claude", "plan", {})
        self.assertEqual(len(backend.calls), 1)

    def test_changed_stage_input_rejected(self):
        run = self.make_run()
        backend = FakeBackend()
        engine = app.Engine(CONFIG, run, backend)
        engine.call("stage", "claude", "plan", {"v": 1})
        with self.assertRaisesRegex(app.RunError, "Entrada mudou"):
            engine.call("stage", "claude", "plan", {"v": 2})
        self.assertEqual(len(backend.calls), 1)

    def test_lock_excludes_second_writer_and_releases_after_exception(self):
        run = self.make_run()
        with self.assertRaisesRegex(ValueError, "failure"):
            with app.run_lock(run):
                with self.assertRaises(app.RunError):
                    with app.run_lock(run):
                        self.fail("Second writer acquired lock")
                self.assertTrue((run / ".lock").exists())
                raise ValueError("failure")
        self.assertFalse((run / ".lock").exists())

    def test_resolve_run_rejects_escape_and_nested_paths(self):
        run = self.make_run()
        (run / "nested").mkdir()
        self.assertEqual(app.resolve_run(run.name), run.resolve())
        for name in ("..", "../outside", str(self.root), run.name + "/nested"):
            with self.subTest(name=name), self.assertRaises(app.RunError):
                app.resolve_run(name)

    def test_stop_prevents_first_dispatch(self):
        run = self.make_run()
        (run / "STOP").touch()
        backend = FakeBackend()
        with self.assertRaisesRegex(app.RunError, "Parada solicitada"):
            app.execute(run, backend)
        self.assertEqual(backend.calls, [])

    def test_stop_between_stages_prevents_next_dispatch(self):
        run = self.make_run()
        backend = FakeBackend()
        def stop_after_plan(provider, kind, packet):
            result = backend(provider, kind, packet)
            (run / "STOP").touch()
            return result
        with self.assertRaisesRegex(app.RunError, "Parada solicitada"):
            app.execute(run, stop_after_plan)
        self.assertEqual(backend.counts, {"plan": 1})

    def test_probe_verifies_bidirectional_handoff_and_reuses_nonce(self):
        run = self.make_run(mode="probe")
        backend = FakeBackend()
        result = app.execute(run, backend)
        self.assertTrue(result["roundtrip_verified"])
        self.assertEqual([p for p, _, _ in backend.calls], ["claude", "codex", "claude"])
        app.execute(run, backend)
        self.assertEqual(len(backend.calls), 3)

    def test_parser_rejects_error_and_codex_tool_events(self):
        run = self.make_run()
        app.atomic(run / "last-message.json", {"echo": "a", "reply": "b"})
        with self.assertRaises(app.RunError):
            app.parse_response("claude", json.dumps({"is_error": True}), run)
        for events in ([{"type": "turn.failed"}], [],
                       [{"type": "item.completed", "item": {"type": "command_execution"}}, {"type": "turn.completed"}]):
            with self.subTest(events=events), self.assertRaises(app.RunError):
                app.parse_response("codex", "\n".join(map(json.dumps, events)), run)

    def spark_config(self):
        config = copy.deepcopy(CONFIG)
        config["providers"]["codex"]["model"] = "gpt-5.6-sol"
        config["providers"]["claude"]["review_effort"] = "medium"
        config["providers"]["spark"] = {"executable": "codex", "model": "gpt-5.3-codex-spark", "effort": "low"}
        config["roles"] = {"probe": "spark", "checklist": "spark"}
        return config

    def test_spark_checklist_does_not_replace_sol_candidate_or_claude_review(self):
        config = self.spark_config()
        run = self.make_run(dict(JOB, mode="swarm"), config)
        backend = FakeBackend(["draft", "READY"], [False, True], barrier=threading.Barrier(2))
        self.assertTrue(app.execute(run, backend)["accepted"])
        spark_calls = [(kind, packet) for provider, kind, packet in backend.calls if provider == "spark"]
        self.assertEqual(len(spark_calls), 1)
        self.assertEqual(spark_calls[0][0], "plan")
        self.assertIn("checklist", spark_calls[0][1]["role"])
        self.assertEqual([p for p, k, _ in backend.calls if k == "candidate"], ["codex", "codex"])
        self.assertEqual([p for p, k, _ in backend.calls if k == "review"], ["claude", "claude"])
        events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        candidates = [e for e in events if e["event"] == "before_dispatch" and e["stage"].startswith("candidate-")]
        self.assertEqual([e["model"] for e in candidates], ["gpt-5.6-sol", "gpt-5.6-sol"])
        reviewers = [e for e in events if e["event"] == "before_dispatch" and e["stage"].startswith("review-")]
        self.assertEqual([e["effort"] for e in reviewers], ["medium", "medium"])

    def test_spark_probe_roundtrip_uses_only_configured_probe_role(self):
        backend = FakeBackend()
        run = self.make_run(config=self.spark_config(), mode="probe")
        self.assertTrue(app.execute(run, backend)["roundtrip_verified"])
        self.assertEqual([(p, k) for p, k, _ in backend.calls],
                         [("claude", "probe"), ("spark", "probe"), ("claude", "probe")])

    def test_provider_review_effort_override_is_local_and_reaches_command(self):
        config = self.spark_config()
        before = copy.deepcopy(config)
        self.assertEqual(app.provider_settings(config, "claude", "review")["effort"], "medium")
        self.assertEqual(app.provider_settings(config, "claude", "plan")["effort"], "low")
        self.assertEqual(app.provider_settings(config, "codex", "review")["effort"], "low")
        with patch.object(app, "executable", return_value="fake.exe"):
            args = app.commands(config, "claude", self.root, "review")
        self.assertEqual(args[args.index("--effort") + 1], "medium")
        self.assertEqual(config, before)

    def test_quota_segregates_codex_and_spark_buckets_and_caches_separately(self):
        quotas = app.Quotas(CONFIG)
        raw = {"provider": "codex", "status": "ok", "windows": [
            {"id": "codex:primary", "used_percent": 100},
            {"id": "codex:secondary", "used_percent": 90},
            {"id": "codex_bengalfox:primary", "used_percent": 12}], "fetched_at": "test"}
        quotas.module = Mock()
        quotas.module.fetch_provider.return_value = raw
        codex = quotas.snapshot("codex")
        spark = quotas.snapshot("spark")
        self.assertEqual([w["id"] for w in codex["windows"]], ["codex:primary", "codex:secondary"])
        self.assertEqual([w["id"] for w in spark["windows"]], ["codex_bengalfox:primary"])
        self.assertEqual(spark["provider"], "spark")
        self.assertEqual(spark["status"], "ok")
        self.assertEqual([c.args for c in quotas.module.fetch_provider.call_args_list], [("codex",), ("codex",)])
        self.assertTrue(quotas.snapshot("spark")["cache"])
        self.assertEqual(quotas.module.fetch_provider.call_count, 2)
        self.assertEqual(len(raw["windows"]), 3)

    def test_missing_spark_quota_is_unknown_not_codex_quota(self):
        quotas = app.Quotas(CONFIG)
        quotas.module = Mock()
        quotas.module.fetch_provider.return_value = {"provider": "codex", "status": "ok",
            "windows": [{"id": "codex:primary", "used_percent": 0}]}
        result = quotas.snapshot("spark")
        self.assertEqual(result["status"], "NAO_MEDIDO")
        self.assertEqual(result["windows"], [])

    def test_resume_rejects_changed_auth_before_execute(self):
        config = self.spark_config()
        run = self.make_run(config=config)
        auth = {"claude": {"ok": True}, "codex": {"ok": False}}
        with patch.object(app.sys, "argv", ["automations.py", "resume", run.name]), \
             patch.object(app, "load_config", return_value=CONFIG), \
             patch.object(app, "auth_status", return_value=auth) as check, \
             patch.object(app, "execute") as execute:
            with self.assertRaisesRegex(app.RunError, "Assinatura não confirmada na retomada"):
                app.main()
            check.assert_called_once_with(config)
            execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
