"""Unit tests for local_worker.py; no real network, same style as test_engine.py."""
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import local_worker


CONFIG = {"providers": {"ollama": {
    "model": "llama3.1:latest", "effort": "low", "local_url": "http://127.0.0.1:11434",
    "context_tokens": 8192, "max_output_tokens": 512, "keep_alive": "60s",
    "health_timeout_seconds": 3, "dispatch_timeout_seconds": 45}}}


def fake_response(payload):
    handle = MagicMock()
    handle.read.return_value = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = handle
    return context


class HealthTests(unittest.TestCase):
    @patch("local_worker.urllib.request.urlopen")
    def test_ok_when_model_present_exact(self, urlopen):
        urlopen.return_value = fake_response({"models": [{"name": "llama3.1:latest"}]})
        result = local_worker.health(CONFIG)
        self.assertEqual(result, {"provider": "ollama", "status": "ok", "windows": [],
                                   "fetched_at": result["fetched_at"], "reason": None})

    @patch("local_worker.urllib.request.urlopen")
    def test_ok_when_model_present_by_base_name(self, urlopen):
        urlopen.return_value = fake_response({"models": [{"name": "llama3.1:8b-instruct-q4"}]})
        result = local_worker.health(CONFIG)
        self.assertEqual(result["status"], "ok")

    @patch("local_worker.urllib.request.urlopen")
    def test_pause_when_model_missing(self, urlopen):
        urlopen.return_value = fake_response({"models": [{"name": "qwen-deep:latest"}]})
        result = local_worker.health(CONFIG)
        self.assertEqual(result["status"], "pause")
        self.assertEqual(result["reason"], "modelo ausente no Ollama")
        self.assertEqual(result["windows"], [])

    @patch("local_worker.urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused"))
    def test_pause_when_server_unreachable(self, urlopen):
        result = local_worker.health(CONFIG)
        self.assertEqual(result["status"], "pause")
        self.assertIn("inacessivel", result["reason"])

    @patch("local_worker.urllib.request.urlopen",
           side_effect=urllib.error.HTTPError("url", 500, "erro", {}, None))
    def test_pause_when_http_error(self, urlopen):
        result = local_worker.health(CONFIG)
        self.assertEqual(result["status"], "pause")
        self.assertIn("500", result["reason"])

    def test_raises_when_ollama_not_configured(self):
        with self.assertRaises(local_worker.LocalWorkerError):
            local_worker.health({"providers": {}})


class CallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.request = {"system": "Responda em JSON.", "schema": {"type": "object"},
                        "input": {"objective": "Testar"}}

    def tearDown(self):
        self.temp.cleanup()

    @patch("local_worker.urllib.request.urlopen")
    def test_sends_explicit_num_ctx_num_predict_keep_alive_and_json_format(self, urlopen):
        urlopen.return_value = fake_response({"message": {"content": json.dumps({"echo": "x", "reply": "y"})},
                                              "prompt_eval_count": 12, "eval_count": 34})
        local_worker.call(CONFIG, self.request, self.folder)
        sent = json.loads(urlopen.call_args[0][0].data.decode("utf-8"))
        self.assertEqual(sent["options"], {"num_ctx": 8192, "num_predict": 512})
        self.assertEqual(sent["keep_alive"], "60s")
        self.assertEqual(sent["format"], "json")
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["messages"][0], {"role": "system", "content": "Responda em JSON."})
        self.assertEqual(json.loads(sent["messages"][1]["content"]), {"schema": {"type": "object"}, "input": {"objective": "Testar"}})

    @patch("local_worker.urllib.request.urlopen")
    def test_parses_value_and_telemetry_from_response(self, urlopen):
        urlopen.return_value = fake_response({"message": {"content": json.dumps({"echo": "nonce", "reply": "oi"})},
                                              "prompt_eval_count": 12, "eval_count": 34})
        value, telemetry = local_worker.call(CONFIG, self.request, self.folder)
        self.assertEqual(value, {"echo": "nonce", "reply": "oi"})
        self.assertEqual(telemetry, {"usage": {"prompt_eval_count": 12, "eval_count": 34}})

    @patch("local_worker.urllib.request.urlopen")
    def test_writes_payload_and_response_for_diagnosis(self, urlopen):
        urlopen.return_value = fake_response({"message": {"content": "{}"}, "prompt_eval_count": 1, "eval_count": 1})
        local_worker.call(CONFIG, self.request, self.folder)
        self.assertTrue((self.folder / "ollama-payload.json").exists())
        self.assertTrue((self.folder / "ollama-response.json").exists())

    @patch("local_worker.urllib.request.urlopen")
    def test_raises_when_content_is_not_valid_json(self, urlopen):
        urlopen.return_value = fake_response({"message": {"content": "isto nao e json"}})
        with self.assertRaises(local_worker.LocalWorkerError):
            local_worker.call(CONFIG, self.request, self.folder)

    @patch("local_worker.urllib.request.urlopen")
    def test_raises_when_message_field_missing(self, urlopen):
        urlopen.return_value = fake_response({"unexpected": True})
        with self.assertRaises(local_worker.LocalWorkerError):
            local_worker.call(CONFIG, self.request, self.folder)

    @patch("local_worker.urllib.request.urlopen", side_effect=urllib.error.URLError("timed out"))
    def test_raises_when_server_unreachable(self, urlopen):
        with self.assertRaises(local_worker.LocalWorkerError):
            local_worker.call(CONFIG, self.request, self.folder)

    def test_works_without_folder(self):
        with patch("local_worker.urllib.request.urlopen") as urlopen:
            urlopen.return_value = fake_response({"message": {"content": "{}"}})
            value, _ = local_worker.call(CONFIG, self.request, folder=None)
            self.assertEqual(value, {})


if __name__ == "__main__":
    unittest.main()
