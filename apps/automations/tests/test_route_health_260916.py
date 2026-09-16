"""Quota health must be proved without changing explicit or persisted V6 routes."""
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import automations as app


class RouteHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        roles = {
            stage: {"provider": provider, "effort": "medium"}
            for stage, provider in (("plan", "claude"), ("plan_review", "codex"),
                                    ("candidate", "codex"), ("final_review", "claude"))
        }
        self.config = {
            "providers": {"claude": {"model": "claude-fable-5-1"},
                          "codex": {"model": "gpt-5.6-sol"}},
            "workflow": {"profiles": {profile: copy.deepcopy(roles)
                                      for profile in ("micro", "normal", "frontier")}},
        }
        self.clock = datetime.now(timezone.utc)
        self.sample = {
            "status": "ok", "fetched_at": self.clock.isoformat(),
            "windows": [{"id": "five_hour", "used_percent": 20,
                         "duration_minutes": 300,
                         "resets_at": (self.clock + timedelta(hours=4)).isoformat()}],
            "pacing": {"status": "ok", "windows": {"five_hour": {"status": "ok"}}},
        }

    def resolve(self, sample=None, profile="auto", other=None):
        run = self.root / str(len(list(self.root.iterdir())))
        run.mkdir()
        sample = copy.deepcopy(self.sample if sample is None else sample)
        quota = Mock()
        quota.snapshot.side_effect = lambda provider: copy.deepcopy(
            other if provider == "codex" and other is not None else sample)
        engine = SimpleNamespace(config=self.config, run=run, quota=quota)
        with patch.object(app.subprocess, "run", side_effect=AssertionError("No dispatch")):
            route = app.resolve_route_v2(engine, {"profile": profile})
        self.assertEqual(app.read_json(run / "route.json"), route)
        return route

    def assert_unknown(self, sample, **kwargs):
        route = self.resolve(sample, **kwargs)
        self.assertNotIn("saudáveis", route["reason"])
        self.assertIn("não confirmada", route["reason"])
        return route

    def test_failed_readings_never_claim_health(self):
        for status in ("auth_required", "error", "rate_limited", "unavailable", "NAO_MEDIDO"):
            with self.subTest(status=status):
                sample = copy.deepcopy(self.sample)
                sample["status"] = status
                route = self.assert_unknown(sample)
                self.assertEqual(route["effective_profile"], "normal")

    def test_fresh_complete_readings_preserve_normal_health(self):
        route = self.resolve()
        self.assertEqual(route["effective_profile"], "normal")
        self.assertIn("cotas medidas saudáveis", route["reason"])

    def test_every_relevant_window_must_be_measured(self):
        for status in ("NAO_MEDIDO", None):
            with self.subTest(status=status):
                sample = copy.deepcopy(self.sample)
                sample["windows"].append(dict(sample["windows"][0], id="seven_day"))
                if status:
                    sample["pacing"]["windows"]["seven_day"] = {"status": status}
                self.assert_unknown(sample)

    def test_absent_windows_or_pacing_cannot_be_healthy(self):
        for field in ("windows", "pacing"):
            with self.subTest(field=field):
                sample = copy.deepcopy(self.sample)
                del sample[field]
                self.assert_unknown(sample)

    def test_freshness_requires_timestamp_and_timezone(self):
        for fetched in (None, "bad", self.clock.replace(tzinfo=None).isoformat(),
                        (self.clock - timedelta(seconds=301)).isoformat(),
                        (self.clock + timedelta(minutes=1)).isoformat()):
            with self.subTest(fetched=fetched):
                sample = copy.deepcopy(self.sample)
                sample["fetched_at"] = fetched
                self.assert_unknown(sample)

    def test_expired_or_missing_window_data_cannot_be_healthy(self):
        for field, value in (("used_percent", None), ("used_percent", 100),
                             ("used_percent", True), ("duration_minutes", None),
                             ("resets_at", None),
                             ("resets_at", (self.clock - timedelta(seconds=1)).isoformat())):
            with self.subTest(field=field, value=value):
                sample = copy.deepcopy(self.sample)
                sample["windows"][0][field] = value
                self.assert_unknown(sample)

    def test_one_failed_provider_prevents_global_health(self):
        sample = copy.deepcopy(self.sample)
        sample["status"] = "error"
        route = self.assert_unknown(self.sample, other=sample)
        self.assertEqual(route["effective_profile"], "normal")

    def test_legacy_deceleration_still_selects_micro_without_claiming_freshness(self):
        route = self.assert_unknown({"status": "ok", "pacing": {"status": "desacelerar"}})
        self.assertEqual(route["effective_profile"], "micro")
        self.assertIn("desacelerar", route["reason"])

    def test_degraded_window_cannot_hide_behind_healthy_aggregate(self):
        sample = copy.deepcopy(self.sample)
        sample["pacing"]["windows"]["five_hour"]["status"] = "desacelerar"
        route = self.resolve(sample)
        self.assertNotIn("saudáveis", route["reason"])
        self.assertEqual(route["effective_profile"], "micro")

    def test_explicit_profile_is_preserved_with_honest_warning(self):
        for status in ("error", "ok"):
            with self.subTest(status=status):
                sample = {"status": status, "pacing": {"status": "desacelerar"}}
                route = self.assert_unknown(sample, profile="frontier")
                self.assertEqual(route["effective_profile"], "frontier")
                self.assertEqual(route["roles"], self.config["workflow"]["profiles"]["frontier"])
                self.assertIn("perfil explícito", route["reason"])

    def test_unrelated_model_window_does_not_change_route(self):
        sample = copy.deepcopy(self.sample)
        sample["windows"].append(dict(sample["windows"][0], id="seven_day:opus"))
        sample["pacing"]["windows"]["seven_day:opus"] = {"status": "NAO_MEDIDO"}
        route = self.resolve(sample, other=self.sample)
        self.assertIn("saudáveis", route["reason"])

    def test_persisted_route_is_unchanged_and_not_remeasured(self):
        run = self.root / "persisted"
        run.mkdir()
        previous = {"effective_profile": "micro", "reason": "saved", "roles": {}}
        app.atomic(run / "route.json", previous)
        engine = SimpleNamespace(config=self.config, run=run, quota=Mock())
        self.assertEqual(app.resolve_route_v2(engine, {"profile": "auto"}), previous)
        engine.quota.snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()
