"""Testes dos adaptadores de cota.

Nenhum teste toca a rede, o disco real ou uma credencial real. Fixtures usam
strings marcadas (``FAKE-NAO-E-TOKEN``) e diretórios temporários apontados por
``IA_QUOTA_HOME``.

Rodam sob ``unittest`` e sob ``pytest``:

    .venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import providers  # noqa: E402

FAKE_TOKEN = "FAKE-NAO-E-TOKEN"
ALLOWED_STATUS = {"ok", "unavailable", "auth_required", "error", "rate_limited"}


def _ms_from_now(hours: float) -> float:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).timestamp() * 1000


class _StubHome:
    """Troca ``IA_QUOTA_HOME`` por um diretório descartável."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._previous = os.environ.get("IA_QUOTA_HOME")
        os.environ["IA_QUOTA_HOME"] = str(self.path)

    def write(self, relative: str, payload: dict) -> Path:
        target = self.path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def close(self) -> None:
        if self._previous is None:
            os.environ.pop("IA_QUOTA_HOME", None)
        else:
            os.environ["IA_QUOTA_HOME"] = self._previous
        self._tmp.cleanup()


class _HttpStub:
    """Substitui ``providers._http``; devolve respostas na ordem programada."""

    def __init__(self, *responses: object) -> None:
        self.queue = list(responses)
        self.calls: list[str] = []

    def __call__(self, url, *, headers, data=None, timeout=providers.DEFAULT_TIMEOUT):
        self.calls.append(url)
        item = self.queue.pop(0) if self.queue else providers.HttpResponse(500, b"")
        if isinstance(item, BaseException):
            raise item
        return item


def _resp(status: int, payload: object = None) -> providers.HttpResponse:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    return providers.HttpResponse(status, body)


# ---------------------------------------------------------------- normalização


class TestNormalizacao(unittest.TestCase):
    def test_percent_preserva_zero_e_none_separados(self):
        # A regra que mais dói se quebrar: ausência de dado != cota zerada.
        self.assertEqual(providers.normalize_percent(0), 0.0)
        self.assertIsNone(providers.normalize_percent(None))
        self.assertIsNot(providers.normalize_percent(None), 0.0)

    def test_percent_rejeita_nao_numero(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, False, "abc", {}, []):
            with self.subTest(value=value):
                self.assertIsNone(providers.normalize_percent(value))

    def test_percent_aceita_string_e_limita_faixa(self):
        self.assertEqual(providers.normalize_percent(" 42.5 "), 42.5)
        self.assertEqual(providers.normalize_percent(140), 100.0)
        self.assertEqual(providers.normalize_percent(-3), 0.0)

    def test_fracao_restante_vira_percentual_usado(self):
        self.assertEqual(providers.percent_from_remaining_fraction(1.0), 0.0)
        self.assertEqual(providers.percent_from_remaining_fraction(0.0), 100.0)
        self.assertEqual(providers.percent_from_remaining_fraction(0.25), 75.0)
        self.assertIsNone(providers.percent_from_remaining_fraction(None))
        self.assertIsNone(providers.percent_from_remaining_fraction("x"))

    def test_epoch_segundos_vira_iso_utc(self):
        self.assertEqual(
            providers.normalize_epoch_seconds(1789484817),
            datetime.fromtimestamp(1789484817, timezone.utc).replace(microsecond=0).isoformat(),
        )
        self.assertIsNone(providers.normalize_epoch_seconds(0))
        self.assertIsNone(providers.normalize_epoch_seconds(None))
        self.assertIsNone(providers.normalize_epoch_seconds(True))

    def test_iso_aceita_z_offset_e_fracao_longa(self):
        esperado = "2026-09-13T02:59:59+00:00"
        self.assertEqual(providers.normalize_iso("2026-09-13T02:59:59Z"), esperado)
        self.assertEqual(providers.normalize_iso("2026-09-13T02:59:59.817723+00:00"), esperado)
        # Anthropic manda 6+ dígitos de fração; fromisoformat aceita no máximo 6.
        self.assertEqual(providers.normalize_iso("2026-09-13T02:59:59.8177231234+00:00"), esperado)
        # Offset diferente é convertido, não copiado.
        self.assertEqual(providers.normalize_iso("2026-09-12T23:59:59-03:00"), esperado)

    def test_iso_invalido_vira_none(self):
        for value in ("", "   ", "amanhã", None, 17, {}):
            with self.subTest(value=value):
                self.assertIsNone(providers.normalize_iso(value))

    def test_rotulo_de_duracao(self):
        self.assertEqual(providers._duration_label(10080), "7 d")
        self.assertEqual(providers._duration_label(300), "5 h")
        self.assertEqual(providers._duration_label(90), "90 min")
        self.assertEqual(providers._duration_label(None), "")
        self.assertEqual(providers._duration_label(0), "")


# ---------------------------------------------------------------------- Codex


CODEX_PAYLOAD = {
    "ordinaryUsageAllowed": True,
    "rateLimits": {"limitId": "codex", "primary": {"usedPercent": 18, "windowDurationMins": 10080, "resetsAt": 1789484817}},
    "rateLimitsByLimitId": {
        "codex": {
            "limitId": "codex",
            "limitName": None,
            "normalModelSlug": None,
            "primary": {"usedPercent": 18, "windowDurationMins": 10080, "resetsAt": 1789484817},
            "secondary": {"usedPercent": 4, "windowDurationMins": 300, "resetsAt": None},
            "planType": "plus",
        },
        "outro-modelo": {
            "limitId": "outro-modelo",
            "normalModelSlug": "modelo-x",
            "primary": {"usedPercent": None, "windowDurationMins": None, "resetsAt": None},
            "secondary": None,
        },
    },
}


class TestCodex(unittest.TestCase):
    def test_multi_bucket_e_janelas_por_modelo(self):
        janelas = providers.parse_codex_rate_limits(CODEX_PAYLOAD)
        ids = [w["id"] for w in janelas]
        self.assertEqual(ids, ["codex:primary", "codex:secondary", "outro-modelo:primary"])
        self.assertEqual(janelas[0]["label"], "codex · 7 d")
        self.assertEqual(janelas[1]["label"], "codex · 5 h")
        self.assertEqual(janelas[2]["label"], "modelo-x")

    def test_used_percent_ausente_continua_none(self):
        janelas = providers.parse_codex_rate_limits(CODEX_PAYLOAD)
        self.assertIsNone(janelas[2]["used_percent"])
        self.assertIsNone(janelas[1]["resets_at"])

    def test_fallback_para_bucket_unico(self):
        payload = {"rateLimits": CODEX_PAYLOAD["rateLimits"], "rateLimitsByLimitId": None}
        janelas = providers.parse_codex_rate_limits(payload)
        self.assertEqual([w["id"] for w in janelas], ["codex:primary"])

    def test_payload_vazio_ou_torto(self):
        self.assertEqual(providers.parse_codex_rate_limits({}), [])
        self.assertEqual(providers.parse_codex_rate_limits("não é dict"), [])
        self.assertEqual(providers.parse_codex_rate_limits({"rateLimitsByLimitId": {"a": None}}), [])

    def test_ordem_das_janelas_nao_depende_da_ordem_do_payload(self):
        # Com N>1 bucket, ordem instável faria os rótulos trocarem de lugar a
        # cada atualização de 120 s — parece bug para quem olha o widget.
        janela = {"usedPercent": 5, "windowDurationMins": 300, "resetsAt": None}
        direto = {
            "rateLimitsByLimitId": {
                "alfa": {"limitId": "alfa", "primary": dict(janela)},
                "beta": {"limitId": "beta", "primary": dict(janela)},
                "gama": {"limitId": "gama", "primary": dict(janela)},
            }
        }
        invertido = {"rateLimitsByLimitId": dict(reversed(list(direto["rateLimitsByLimitId"].items())))}
        esperado = ["alfa:primary", "beta:primary", "gama:primary"]
        self.assertEqual([w["id"] for w in providers.parse_codex_rate_limits(direto)], esperado)
        self.assertEqual([w["id"] for w in providers.parse_codex_rate_limits(invertido)], esperado)

    def test_erro_do_app_server_vira_auth_required(self):
        stdout = "\n".join(
            [
                json.dumps({"id": 0, "result": {}}),
                json.dumps({"id": 2, "error": {"code": -32000, "message": "not logged in"}}),
            ]
        )
        with _patched(providers, "run_codex_app_server", lambda binary, timeout=0, env=None: stdout), _patched(
            providers, "find_codex_binary", lambda: "codex"
        ):
            resultado = providers.fetch_provider("codex")
        self.assertEqual(resultado["status"], "auth_required")
        self.assertIsNone(resultado["fetched_at"])
        self.assertEqual(resultado["windows"], [])

    def test_sem_resposta_vira_error(self):
        with _patched(providers, "run_codex_app_server", lambda binary, timeout=0, env=None: ""), _patched(
            providers, "find_codex_binary", lambda: "codex"
        ):
            resultado = providers.fetch_provider("codex")
        self.assertEqual(resultado["status"], "error")

    def test_sem_binario_vira_unavailable(self):
        with _patched(providers, "find_codex_binary", lambda: None):
            resultado = providers.fetch_provider("codex")
        self.assertEqual(resultado["status"], "unavailable")

    def test_leitura_boa_preenche_fetched_at(self):
        stdout = "\n".join(
            [
                json.dumps({"id": 0, "result": {}}),
                json.dumps({"id": 1, "result": {"account": {"type": "chatgpt", "planType": "plus"}}}),
                json.dumps({"id": 2, "result": CODEX_PAYLOAD}),
            ]
        )
        with _patched(providers, "run_codex_app_server", lambda binary, timeout=0, env=None: stdout), _patched(
            providers, "find_codex_binary", lambda: "codex"
        ):
            resultado = providers.fetch_provider("codex")
        self.assertEqual(resultado["status"], "ok")
        self.assertIsNotNone(resultado["fetched_at"])
        self.assertEqual(len(resultado["windows"]), 3)

    def test_gpt2_sem_perfil_vira_unavailable(self):
        # Home gpt2 sem auth.json é "sem login nesta máquina", não auth_required:
        # a conta principal pode estar logada, o perfil gpt2 é que não existe.
        with tempfile.TemporaryDirectory() as tmp:
            with _patched(providers, "CODEX_GPT2_HOME", Path(tmp)):
                resultado = providers.fetch_provider("codex_gpt2")
        self.assertEqual(resultado["status"], "unavailable")
        self.assertIsNone(resultado["fetched_at"])

    def test_gpt2_responde_como_conta_propria(self):
        stdout = "\n".join(
            [
                json.dumps({"id": 0, "result": {}}),
                json.dumps({"id": 1, "result": {"account": {"type": "chatgpt", "planType": "plus"}}}),
                json.dumps({"id": 2, "result": CODEX_PAYLOAD}),
            ]
        )
        vistos: dict = {}

        def fake(binary, timeout=0, env=None):
            vistos["env"] = env
            return stdout

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "auth.json").write_text("{}", encoding="utf-8")
            with (
                _patched(providers, "CODEX_GPT2_HOME", Path(tmp)),
                _patched(providers, "run_codex_app_server", fake),
                _patched(providers, "find_codex_binary", lambda: "codex"),
            ):
                resultado = providers.fetch_provider("codex_gpt2")
        self.assertEqual(resultado["status"], "ok")
        self.assertEqual(resultado["provider"], "codex_gpt2")
        self.assertIn("plus", resultado["message"])
        # O app-server resolve o home pelo env do processo pai: a sobrescrita
        # tem que chegar no Popen, senão o card gpt2 leria a conta principal.
        self.assertEqual(vistos["env"]["CODEX_HOME"], str(Path(tmp)))

    def test_requisicoes_na_ordem_e_params_null(self):
        # O app-server recusa {} em account/rateLimits/read; tem que ser null.
        passos = dict((req["method"], req) for _, req in providers.CODEX_STEPS)
        self.assertIn("params", passos["account/rateLimits/read"])
        self.assertIsNone(passos["account/rateLimits/read"]["params"])
        self.assertFalse(passos["account/read"]["params"]["refreshToken"])
        self.assertEqual([req["method"] for _, req in providers.CODEX_STEPS][0], "initialize")


# --------------------------------------------------------------------- Claude


CLAUDE_PAYLOAD = {
    "five_hour": {"utilization": 10.0, "resets_at": "2026-09-08T19:09:59.817702+00:00"},
    "seven_day": {"utilization": 26.0, "resets_at": "2026-09-13T02:59:59.817723+00:00"},
    "seven_day_opus": None,
    "nimbus_quill": {"utilization": 0.0, "resets_at": None},
    "limits": [
        {"kind": "session", "percent": 10, "resets_at": "2026-09-08T19:09:59.817702+00:00", "scope": None},
        {"kind": "weekly_all", "percent": 26, "resets_at": "2026-09-13T02:59:59.817723+00:00", "scope": None},
        {
            "kind": "weekly_scoped",
            "percent": 28,
            "resets_at": "2026-09-13T02:59:59.817970+00:00",
            "scope": {"model": {"id": None, "display_name": "Fable"}},
        },
        {"kind": "bucket_desconhecido_do_futuro", "percent": 5, "resets_at": None},
    ],
}


class TestClaude(unittest.TestCase):
    def test_limits_e_a_fonte_primaria_com_janela_por_modelo(self):
        janelas = providers.parse_claude_usage(CLAUDE_PAYLOAD)
        self.assertEqual(
            [w["id"] for w in janelas],
            ["session", "weekly_all", "weekly_scoped:Fable", "bucket_desconhecido_do_futuro"],
        )
        self.assertEqual(janelas[2]["label"], "Semana · Fable")
        self.assertEqual(janelas[2]["used_percent"], 28.0)

    def test_bucket_desconhecido_e_tolerado_nao_quebra(self):
        janelas = providers.parse_claude_usage(CLAUDE_PAYLOAD)
        self.assertEqual(janelas[3]["used_percent"], 5.0)
        self.assertIsNone(janelas[3]["resets_at"])

    def test_fallback_para_campos_nomeados_quando_nao_ha_limits(self):
        payload = {k: v for k, v in CLAUDE_PAYLOAD.items() if k != "limits"}
        janelas = providers.parse_claude_usage(payload)
        self.assertEqual([w["id"] for w in janelas], ["five_hour", "seven_day"])
        self.assertEqual(janelas[0]["used_percent"], 10.0)

    def test_duplicata_no_limits_e_descartada(self):
        payload = {"limits": [{"kind": "session", "percent": 3}, {"kind": "session", "percent": 9}]}
        janelas = providers.parse_claude_usage(payload)
        self.assertEqual(len(janelas), 1)
        self.assertEqual(janelas[0]["used_percent"], 3.0)

    def test_payload_torto(self):
        self.assertEqual(providers.parse_claude_usage({}), [])
        self.assertEqual(providers.parse_claude_usage([1, 2]), [])
        self.assertEqual(providers.parse_claude_usage({"limits": ["não é dict"]}), [])

    def test_credencial_ausente_vira_auth_required(self):
        home = _StubHome()
        self.addCleanup(home.close)
        resultado = providers.fetch_provider("claude")
        self.assertEqual(resultado["status"], "auth_required")
        self.assertIsNone(resultado["fetched_at"])

    def test_token_vencido_nao_chega_a_chamar_a_rede(self):
        home = _StubHome()
        self.addCleanup(home.close)
        home.write(
            ".claude/.credentials.json",
            {"claudeAiOauth": {"accessToken": FAKE_TOKEN, "expiresAt": _ms_from_now(-1)}},
        )
        stub = _HttpStub()
        with _patched(providers, "_http", stub):
            resultado = providers.fetch_provider("claude")
        self.assertEqual(resultado["status"], "auth_required")
        self.assertEqual(stub.calls, [])  # não gastou chamada com token morto

    def test_http_401_e_403_viram_auth_required(self):
        for status in (401, 403):
            with self.subTest(status=status):
                resultado = self._claude_com_resposta(_resp(status, {"error": "x"}))
                self.assertEqual(resultado["status"], "auth_required")

    def test_http_429_vira_rate_limited(self):
        resultado = self._claude_com_resposta(_resp(429, {"error": "slow down"}))
        self.assertEqual(resultado["status"], "rate_limited")

    def test_http_500_vira_error(self):
        resultado = self._claude_com_resposta(_resp(500))
        self.assertEqual(resultado["status"], "error")

    def test_falha_de_rede_vira_error_sem_levantar(self):
        resultado = self._claude_com_resposta(OSError("sem rota para o host"))
        self.assertEqual(resultado["status"], "error")
        self.assertNotIn("rota", resultado["message"])  # não vaza detalhe do sistema

    def test_corpo_nao_json_vira_error(self):
        resultado = self._claude_com_resposta(providers.HttpResponse(200, b"<html>oops"))
        self.assertEqual(resultado["status"], "error")

    def test_resposta_sem_janela_vira_unavailable(self):
        resultado = self._claude_com_resposta(_resp(200, {"limits": []}))
        self.assertEqual(resultado["status"], "unavailable")

    def test_leitura_boa(self):
        resultado = self._claude_com_resposta(_resp(200, CLAUDE_PAYLOAD))
        self.assertEqual(resultado["status"], "ok")
        self.assertIsNotNone(resultado["fetched_at"])
        self.assertEqual(len(resultado["windows"]), 4)

    def _claude_com_resposta(self, item):
        home = _StubHome()
        self.addCleanup(home.close)
        home.write(
            ".claude/.credentials.json",
            {
                "claudeAiOauth": {
                    "accessToken": FAKE_TOKEN,
                    "expiresAt": _ms_from_now(3),
                    "subscriptionType": "max",
                }
            },
        )
        with _patched(providers, "_http", _HttpStub(item)):
            return providers.fetch_provider("claude")


# ----------------------------------------------------------------- Gemini CLI


GEMINI_QUOTA = {
    "buckets": [
        {"modelId": "gemini-3-pro", "tokenType": "INPUT", "remainingFraction": 0.4, "resetTime": "2026-09-09T00:00:00Z"},
        {"modelId": "gemini-3-flash", "remainingFraction": 1.0, "resetTime": None},
        {"tokenType": "INPUT", "remainingFraction": 0.5},  # sem modelId: descartar
        {"modelId": "sem-fracao", "remainingAmount": "12"},  # sem fração: descartar
        "lixo",
    ]
}


class TestGeminiCli(unittest.TestCase):
    def test_converte_fracao_restante_e_descarta_bucket_incompleto(self):
        janelas = providers.parse_gemini_quota(GEMINI_QUOTA)
        self.assertEqual([w["id"] for w in janelas], ["gemini-3-pro:INPUT", "gemini-3-flash"])
        self.assertAlmostEqual(janelas[0]["used_percent"], 60.0)
        self.assertEqual(janelas[1]["used_percent"], 0.0)
        self.assertEqual(janelas[0]["resets_at"], "2026-09-09T00:00:00+00:00")

    def test_payload_torto(self):
        self.assertEqual(providers.parse_gemini_quota({}), [])
        self.assertEqual(providers.parse_gemini_quota({"buckets": None}), [])
        self.assertEqual(providers.parse_gemini_quota("x"), [])

    def test_credencial_vencida_vira_auth_required_sem_rede(self):
        home = _StubHome()
        self.addCleanup(home.close)
        home.write(".gemini/oauth_creds.json", {"access_token": FAKE_TOKEN, "expiry_date": _ms_from_now(-60)})
        stub = _HttpStub()
        with _patched(providers, "_http", stub):
            resultado = providers.fetch_provider("gemini_cli")
        self.assertEqual(resultado["status"], "auth_required")
        self.assertEqual(stub.calls, [])

    def test_dois_posts_na_ordem_load_depois_quota(self):
        stub = _HttpStub(
            _resp(200, {"cloudaicompanionProject": "proj-fake", "currentTier": {"id": "free-tier"}}),
            _resp(200, GEMINI_QUOTA),
        )
        resultado = self._gemini(stub)
        self.assertEqual(resultado["status"], "ok")
        self.assertTrue(stub.calls[0].endswith(":loadCodeAssist"))
        self.assertTrue(stub.calls[1].endswith(":retrieveUserQuota"))
        self.assertEqual(len(resultado["windows"]), 2)

    def test_sem_projeto_vira_unavailable_e_nao_chama_quota(self):
        stub = _HttpStub(_resp(200, {"currentTier": {"id": "free-tier"}}))
        resultado = self._gemini(stub)
        self.assertEqual(resultado["status"], "unavailable")
        self.assertEqual(len(stub.calls), 1)

    def test_401_no_primeiro_post(self):
        resultado = self._gemini(_HttpStub(_resp(401, {"error": "x"})))
        self.assertEqual(resultado["status"], "auth_required")

    def test_429_no_segundo_post(self):
        stub = _HttpStub(_resp(200, {"cloudaicompanionProject": "proj-fake"}), _resp(429))
        self.assertEqual(self._gemini(stub)["status"], "rate_limited")

    def test_falha_de_rede(self):
        self.assertEqual(self._gemini(_HttpStub(OSError("timeout")))["status"], "error")

    def _gemini(self, stub):
        home = _StubHome()
        self.addCleanup(home.close)
        home.write(".gemini/oauth_creds.json", {"access_token": FAKE_TOKEN, "expiry_date": _ms_from_now(1)})
        with _patched(providers, "_http", stub):
            return providers.fetch_provider("gemini_cli")


# ---------------------------------------------------------------- Antigravity


class TestAntigravity(unittest.TestCase):
    def test_descoberta_prefere_variavel_de_ambiente(self):
        bases = providers.discover_antigravity_bases(
            env={"ANTIGRAVITY_LS_ADDRESS": "127.0.0.1:9999"},
            listeners=[(5000, 10)],
            names={10: "antigravity.exe"},
        )
        self.assertEqual(bases, ["http://127.0.0.1:9999", "http://127.0.0.1:5000"])

    def test_descoberta_ignora_processo_de_outro_programa(self):
        bases = providers.discover_antigravity_bases(
            env={},
            listeners=[(5000, 10), (6000, 11)],
            names={10: "chrome.exe", 11: "language_server.exe"},
        )
        self.assertEqual(bases, ["http://127.0.0.1:6000"])

    def test_sem_processo_vira_unavailable_com_motivo(self):
        with _patched(providers, "discover_antigravity_bases", lambda **_: []):
            resultado = providers.fetch_provider("antigravity")
        self.assertEqual(resultado["status"], "unavailable")
        self.assertTrue(resultado["message"])
        self.assertEqual(resultado["windows"], [])

    def test_csrf_extraido_do_html(self):
        html = 'var x = {"csrfToken":"abc-123","outro":1};'
        self.assertEqual(providers.extract_csrf(html), "abc-123")
        self.assertIsNone(providers.extract_csrf("<html>sem token</html>"))

    def test_quota_aninhada_e_encontrada(self):
        payload = {"summary": {"quotas": [{"modelId": "m1", "remainingFraction": 0.2, "resetTime": "2026-09-09T00:00:00Z"}]}}
        janelas = providers.parse_antigravity_quota(payload)
        self.assertEqual(len(janelas), 1)
        self.assertAlmostEqual(janelas[0]["used_percent"], 80.0)

    def test_entrada_sem_medida_e_descartada(self):
        payload = {"quotas": [{"modelId": "m1"}, {"remainingFraction": 0.5}]}
        self.assertEqual(providers.parse_antigravity_quota(payload), [])

    def test_resposta_sem_cota_reconhecivel_vira_unavailable(self):
        stub = _HttpStub(providers.HttpResponse(200, b'{"csrfToken":"t"}'), _resp(200, {"nada": True}))
        with _patched(providers, "discover_antigravity_bases", lambda **_: ["http://127.0.0.1:1"]), _patched(
            providers, "_http", stub
        ):
            resultado = providers.fetch_provider("antigravity")
        self.assertEqual(resultado["status"], "unavailable")


# ----------------------------------------------------------------------- Z.ai

# Forma real lida em 260913 (plano pro), números trocados, sem id de conta.
ZAI_PAYLOAD = {
    "code": 200,
    "msg": "Operation successful",
    "success": True,
    "data": {
        "level": "pro",
        "limits": [
            {"type": "CREDIT_LIMIT", "unit": 3, "number": 5, "usage": 12000, "currentValue": 144,
             "remaining": 11856, "percentage": 1, "nextResetTime": 1789347502491},
            {"type": "CREDIT_LIMIT", "unit": 6, "number": 1, "usage": 60000, "currentValue": 266,
             "remaining": 59734, "percentage": 1, "nextResetTime": 1789834746970},
        ],
    },
}


class TestZai(unittest.TestCase):
    def setUp(self):
        self.home = _StubHome()
        self.addCleanup(self.home.close)
        self._env = os.environ.pop("ZAI_API_KEY", None)
        self.addCleanup(lambda: self._env is not None and os.environ.__setitem__("ZAI_API_KEY", self._env))

    def _zcode(self, enabled=True, key=FAKE_TOKEN):
        self.home.write(
            ".zcode/v2/config.json",
            {"provider": {"builtin:zai-coding-plan": {"enabled": enabled, "options": {"apiKey": key}}}},
        )

    def test_percentual_sai_de_current_sobre_usage_nao_do_arredondado(self):
        janelas = providers.parse_zai_quota(ZAI_PAYLOAD)
        self.assertEqual([j["label"] for j in janelas], ["Sessão", "Semana"])
        self.assertAlmostEqual(janelas[0]["used_percent"], 1.2)
        self.assertAlmostEqual(janelas[1]["used_percent"], 266 / 600)
        self.assertEqual([j["duration_minutes"] for j in janelas], [300, 10080])

    def test_reset_em_milissegundos(self):
        janela = providers.parse_zai_quota(ZAI_PAYLOAD)[0]
        self.assertEqual(janela["resets_at"], "2026-09-14T00:58:22+00:00")

    def test_unidade_desconhecida_fica_sem_duracao(self):
        payload = {"data": {"limits": [{"type": "TIME_LIMIT", "unit": 5, "number": 1, "percentage": 30}]}}
        janela = providers.parse_zai_quota(payload)[0]
        self.assertIsNone(janela["duration_minutes"])
        self.assertEqual(janela["label"], "Ferramentas")
        self.assertEqual(janela["used_percent"], 30.0)

    def test_sem_medida_nao_vira_zero(self):
        payload = {"data": {"limits": [{"type": "CREDIT_LIMIT", "unit": 3, "number": 5}]}}
        self.assertIsNone(providers.parse_zai_quota(payload)[0]["used_percent"])

    def test_sem_chave_pede_autenticacao_sem_rede(self):
        stub = _HttpStub()
        with _patched(providers, "_http", stub):
            r = providers.fetch_provider("zai")
        self.assertEqual(r["status"], "auth_required")
        self.assertEqual(stub.calls, [])

    def test_ok_com_chave_do_zcode(self):
        self._zcode()
        stub = _HttpStub(providers.HttpResponse(200, json.dumps(ZAI_PAYLOAD).encode()))
        with _patched(providers, "_http", stub):
            r = providers.fetch_provider("zai")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["message"], "Plano pro.")
        self.assertEqual(len(r["windows"]), 2)
        self.assertNotIn(FAKE_TOKEN, json.dumps(r))

    def test_provider_desligado_no_zcode_nao_serve_de_chave(self):
        self._zcode(enabled=False)
        self.assertEqual(providers.read_zai_keys(), [])

    def test_chave_recusada_tenta_a_seguinte(self):
        self._zcode()
        stub = _HttpStub(
            providers.HttpResponse(401, b""),
            providers.HttpResponse(200, json.dumps(ZAI_PAYLOAD).encode()),
        )
        with _patched(providers, "read_zai_keys", lambda: ["A-FAKE", "B-FAKE"]), _patched(providers, "_http", stub):
            r = providers.fetch_provider("zai")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(len(stub.calls), 2)

    def test_http_429_e_rede(self):
        for resposta, esperado in ((providers.HttpResponse(429, b""), "rate_limited"), (OSError("x"), "error")):
            with self.subTest(esperado=esperado):
                with _patched(providers, "read_zai_keys", lambda: ["FAKE"]), _patched(
                    providers, "_http", _HttpStub(resposta)
                ):
                    self.assertEqual(providers.fetch_provider("zai")["status"], esperado)

    def test_envelope_com_codigo_401(self):
        stub = _HttpStub(providers.HttpResponse(200, json.dumps({"code": 401, "success": False}).encode()))
        with _patched(providers, "read_zai_keys", lambda: ["FAKE"]), _patched(providers, "_http", stub):
            self.assertEqual(providers.fetch_provider("zai")["status"], "auth_required")


# ----------------------------------------------------------------- Gemini web


class TestGeminiWeb(unittest.TestCase):
    def test_sempre_unavailable_com_motivo_e_sem_janela(self):
        resultado = providers.fetch_provider("gemini_web")
        self.assertEqual(resultado["status"], "unavailable")
        self.assertEqual(resultado["windows"], [])
        self.assertIsNone(resultado["fetched_at"])
        self.assertIn("cookie", resultado["message"].lower())


# -------------------------------------------------------------------- contrato


class TestContrato(unittest.TestCase):
    CHAVES = {"provider", "label", "status", "source", "fetched_at", "windows", "message"}

    def test_ids_declarados(self):
        self.assertEqual(
            providers.PROVIDER_IDS,
            ("codex", "codex_gpt2", "claude", "zai", "gemini_cli", "antigravity", "gemini_web"),
        )

    def test_toda_resposta_tem_o_formato_do_contrato(self):
        home = _StubHome()  # home vazio: ninguém acha credencial, ninguém vai à rede
        self.addCleanup(home.close)
        with _patched(providers, "find_codex_binary", lambda: None), _patched(
            providers, "discover_antigravity_bases", lambda **_: []
        ), _patched(providers, "read_zai_keys", lambda: []):
            for pid in providers.PROVIDER_IDS:
                with self.subTest(provider=pid):
                    r = providers.fetch_provider(pid)
                    self.assertEqual(set(r), self.CHAVES)
                    self.assertEqual(r["provider"], pid)
                    self.assertIn(r["status"], ALLOWED_STATUS)
                    self.assertIsInstance(r["windows"], list)
                    self.assertIsInstance(r["message"], str)
                    if r["status"] != "ok":
                        self.assertIsNone(r["fetched_at"])

    def test_janela_respeita_tipos(self):
        janelas = providers.parse_claude_usage(CLAUDE_PAYLOAD) + providers.parse_codex_rate_limits(CODEX_PAYLOAD)
        for janela in janelas:
            with self.subTest(janela=janela["id"]):
                self.assertEqual(set(janela), {"id", "label", "used_percent", "resets_at", "duration_minutes"})
                pct = janela["used_percent"]
                if pct is not None:
                    self.assertTrue(math.isfinite(pct) and 0.0 <= pct <= 100.0)
                if janela["resets_at"] is not None:
                    datetime.fromisoformat(janela["resets_at"])  # levanta se não for ISO
                minutos = janela["duration_minutes"]
                if minutos is not None:
                    self.assertIsInstance(minutos, int)
                    self.assertGreater(minutos, 0)

    def test_provider_desconhecido_nao_levanta(self):
        r = providers.fetch_provider("inexistente")
        self.assertEqual(r["status"], "error")

    def test_excecao_inesperada_vira_status_error(self):
        def explode(_timeout):
            raise RuntimeError("boom")

        with _patched(providers._FETCHERS, "claude", explode, mapping=True):
            r = providers.fetch_provider("claude")
        self.assertEqual(r["status"], "error")
        self.assertNotIn("boom", r["message"])

    def test_sanitizado_nao_carrega_message_nem_label(self):
        r = providers.fetch_provider("gemini_web")
        s = providers._sanitized(r)
        self.assertEqual(set(s), {"provider", "status", "source", "fetched_at", "windows"})


# ------------------------------------------------- timeout e falha transitória


class _ProcTravado:
    """Processo que aceita escrita e nunca responde nada útil.

    ``readline`` devolve linha em branco para sempre: o adaptador ignora linha
    vazia, então quem tem que interromper o laço é o prazo, não o conteúdo.
    """

    returncode = None

    def __init__(self, *_args, **_kwargs) -> None:
        self.stdin = _EscritaOk()
        self.stdout = _LeituraSemFim()
        self.killed = False
        self.terminated = False

    def kill(self):
        self.killed = True
        self.stdout.eof = True

    def terminate(self):
        self.terminated = True
        self.stdout.eof = True

    def wait(self, timeout=None):
        self.returncode = 0
        return 0


class _EscritaOk:
    closed = False

    def write(self, _data):
        return None

    def flush(self):
        return None

    def close(self):
        self.closed = True


class _LeituraSemFim:
    eof = False

    def readline(self):
        return b"" if self.eof else b"\n"


class TestTimeoutSubprocesso(unittest.TestCase):
    def test_prazo_finito_interrompe_app_server_travado(self):
        import time as _time

        with _patched(providers.subprocess, "Popen", _ProcTravado):
            inicio = _time.monotonic()
            saida = providers.run_codex_app_server("codex", timeout=0.4)
            decorrido = _time.monotonic() - inicio
        self.assertEqual(saida, "")
        self.assertLess(decorrido, 5.0, "o laço tem que respeitar o prazo, não travar a UI")

    def test_app_server_travado_vira_error_e_nao_unavailable(self):
        # Falha transitória tem que continuar sendo `error`: marcar como
        # `unavailable` faria a UI dizer "não tem essa fonte" quando na verdade
        # a fonte existe e só não respondeu agora.
        with _patched(providers.subprocess, "Popen", _ProcTravado), _patched(
            providers, "find_codex_binary", lambda: "codex"
        ):
            resultado = providers.fetch_provider("codex", timeout=0.4)
        self.assertEqual(resultado["status"], "error")
        self.assertNotEqual(resultado["status"], "unavailable")

    def test_falha_ao_executar_binario_vira_error(self):
        def explode(*_a, **_k):
            raise OSError("binário sumiu")

        with _patched(providers.subprocess, "Popen", explode), _patched(
            providers, "find_codex_binary", lambda: "codex"
        ):
            resultado = providers.fetch_provider("codex")
        self.assertEqual(resultado["status"], "error")
        self.assertNotIn("sumiu", resultado["message"])

    def test_stdin_fechado_antes_de_encerrar_o_filho(self):
        proc = _ProcTravado()
        providers._close_child(proc)
        self.assertTrue(proc.stdin.closed)
        self.assertFalse(proc.terminated, "saída normal primeiro; encerrar só se insistir")


class TestPercentualForaDaFaixa(unittest.TestCase):
    def test_valor_absurdo_do_fornecedor_e_limitado_na_janela(self):
        payload = {
            "rateLimitsByLimitId": {
                "codex": {
                    "limitId": "codex",
                    "primary": {"usedPercent": 140, "windowDurationMins": 300, "resetsAt": 1789484817},
                    "secondary": {"usedPercent": -12, "windowDurationMins": 300, "resetsAt": "não é número"},
                }
            }
        }
        janelas = providers.parse_codex_rate_limits(payload)
        self.assertEqual(janelas[0]["used_percent"], 100.0)
        self.assertEqual(janelas[1]["used_percent"], 0.0)
        self.assertIsNone(janelas[1]["resets_at"])

    def test_percentual_do_claude_fora_da_faixa(self):
        janelas = providers.parse_claude_usage({"limits": [{"kind": "session", "percent": 1e9}]})
        self.assertEqual(janelas[0]["used_percent"], 100.0)

    def test_fracao_do_gemini_fora_da_faixa(self):
        janelas = providers.parse_gemini_quota({"buckets": [{"modelId": "m", "remainingFraction": -0.5}]})
        self.assertEqual(janelas[0]["used_percent"], 100.0)


# ---------------------------------------------------------------------- apoio


class _patched:
    """``setattr`` temporário em módulo ou dicionário, sem depender de pytest."""

    def __init__(self, target, name, value, *, mapping: bool = False) -> None:
        self.target, self.name, self.value, self.mapping = target, name, value, mapping

    def __enter__(self):
        self.previous = self.target[self.name] if self.mapping else getattr(self.target, self.name)
        if self.mapping:
            self.target[self.name] = self.value
        else:
            setattr(self.target, self.name, self.value)
        return self.value

    def __exit__(self, *_exc):
        if self.mapping:
            self.target[self.name] = self.previous
        else:
            setattr(self.target, self.name, self.previous)
        return False


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ---------------------------------------------------------------------------
# Sem janela de console no refresh (o widget roda sob pythonw, sem console)
# ---------------------------------------------------------------------------


class TestSemJanelaDeConsole(unittest.TestCase):
    """Todo filho de console tem que nascer com CREATE_NO_WINDOW.

    Sem a flag, cada refresh pisca uma janela de terminal na cara do usuário —
    o pai (pythonw) não tem console, então o Windows aloca um novo para o filho.
    """

    def _kwargs_do_spawn(self, attr, call):
        capturado: dict = {}

        class _FakePopen:
            def __init__(self, *args, **kwargs):
                capturado.update(kwargs)
                raise OSError("spawn interceptado pelo teste")

        def _fake_run(*args, **kwargs):
            capturado.update(kwargs)
            raise OSError("spawn interceptado pelo teste")

        original = getattr(providers.subprocess, attr)
        setattr(providers.subprocess, attr, _FakePopen if attr == "Popen" else _fake_run)
        try:
            call()
        except OSError:
            pass
        finally:
            setattr(providers.subprocess, attr, original)
        return capturado

    @unittest.skipUnless(
        hasattr(subprocess, "CREATE_NO_WINDOW"), "flag só existe no Windows"
    )
    def test_codex_app_server_nao_abre_console(self):
        kwargs = self._kwargs_do_spawn(
            "Popen", lambda: providers.run_codex_app_server("codex")
        )
        self.assertEqual(kwargs.get("creationflags"), subprocess.CREATE_NO_WINDOW)

    @unittest.skipUnless(
        hasattr(subprocess, "CREATE_NO_WINDOW"), "flag só existe no Windows"
    )
    def test_utilitarios_windows_nao_abrem_console(self):
        for nome in ("_listening_pids", "_process_names"):
            with self.subTest(funcao=nome):
                kwargs = self._kwargs_do_spawn("run", getattr(providers, nome))
                self.assertEqual(
                    kwargs.get("creationflags"), subprocess.CREATE_NO_WINDOW
                )
