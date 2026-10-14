"""Auditoria 261012: mesma situação, mesmo texto em todos os provedores."""
from datetime import datetime, timedelta, timezone

from widget_app.formatting import reset_label
from widget_app.inline_contract import NOT_STARTED_TEXT, provider_fields, window_not_started


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


NOW = datetime.now(timezone.utc).replace(microsecond=0)


def test_reset_label_keeps_minutes_under_ten_hours():
    assert reset_label(_iso(NOW + timedelta(hours=3, minutes=56, seconds=20))) == "renova em 3 h 56 min"
    assert reset_label(_iso(NOW + timedelta(hours=4, seconds=30))) == "renova em 4 h"
    assert reset_label(_iso(NOW + timedelta(hours=12, minutes=40, seconds=20))) == "renova em 12 h"


def test_codex_unused_window_has_no_fake_countdown():
    # Codex devolve consulta + 5 h enquanto a janela não foi usada.
    window = {"id": "codex:primary", "label": "codex · 5 h", "used_percent": 0.0,
              "resets_at": _iso(NOW + timedelta(hours=5, seconds=-4)), "duration_minutes": 300}
    assert window_not_started(window, _iso(NOW))


def test_zai_unused_window_without_reset_matches_codex_text():
    zai = {"id": "CREDIT_LIMIT:3x5", "label": "Sessão", "used_percent": 0.0, "resets_at": None, "duration_minutes": 300}
    codex = {"id": "codex:primary", "label": "codex · 5 h", "used_percent": 0.0,
             "resets_at": _iso(NOW + timedelta(hours=5)), "duration_minutes": 300}
    texts = []
    for row_id, window in (("zai", zai), ("codex_gpt2", codex)):
        display = {"status": "ok", "fetched_at": _iso(NOW), "windows": [window], "details": {}}
        quota = [f for f in provider_fields(row_id, display, number_mode="remaining") if f.kind == "quota"][0]
        texts.append(quota.text)
        assert "não iniciada" in quota.tooltip
    assert texts == [NOT_STARTED_TEXT, NOT_STARTED_TEXT]


def test_used_or_real_countdown_keeps_reset():
    used = {"id": "session", "label": "Sessão", "used_percent": 2.0,
            "resets_at": _iso(NOW + timedelta(hours=3, minutes=56)), "duration_minutes": 300}
    zero_but_running = {"id": "session", "label": "Sessão", "used_percent": 0.0,
                        "resets_at": _iso(NOW + timedelta(hours=2)), "duration_minutes": 300}
    assert not window_not_started(used, _iso(NOW))
    assert not window_not_started(zero_but_running, _iso(NOW))
