"""Auditoria 261012: mesma situação, mesmo texto em todos os provedores."""
from datetime import datetime, timedelta, timezone

import pytest

from widget_app import formatting
from widget_app.formatting import reset_label
from widget_app.inline_contract import NOT_STARTED_TEXT, provider_fields, window_not_started


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")


@pytest.fixture(autouse=True)
def fixed_now(monkeypatch):
    now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz is not None else now.astimezone().replace(tzinfo=None)

    # Only this module binding changes; pytest restores it after each test.
    monkeypatch.setattr(formatting, "datetime", FixedDatetime)
    return now


@pytest.mark.parametrize("delta, expected", [
    (timedelta(minutes=59), "renova em 59 min"),
    (timedelta(hours=3, minutes=56, seconds=20), "renova em 3 h 56 min"),
    (timedelta(hours=4), "renova em 4 h"),
    (timedelta(hours=9, minutes=59), "renova em 9 h 59 min"),
    (timedelta(hours=10), "renova em 10 h"),
    (timedelta(hours=12, minutes=40, seconds=20), "renova em 12 h"),
    (timedelta(days=7), "renova em 7 d"),
    (timedelta(0), "renova em breve"),
    (timedelta(seconds=-1), "renova em breve"),
])
def test_reset_label_with_fixed_time(fixed_now, delta, expected):
    assert reset_label(_iso(fixed_now + delta)) == expected


@pytest.mark.parametrize("value", [None, "", "invaliddate", "2026-02-30T12:00:00Z"])
def test_reset_label_missing_or_invalid_is_unknown(value):
    assert reset_label(value) == "renovação desconhecida"


def test_deprecated_window_not_started_accepts_existing_call_signature():
    window = {"id": "session", "label": "5 h", "used_percent": 0.0,
              "resets_at": None, "duration_minutes": 300}
    assert window_not_started(window, None) is False
    assert window_not_started(window=window, fetched_at="2026-10-14T12:00:00Z") is False


@pytest.mark.parametrize("row_id", ["codex", "codex_gpt2", "zai", "claude"])
@pytest.mark.parametrize("number_mode", ["used", "remaining"])
@pytest.mark.parametrize("duration, used, reset, expected, tooltip_date", [
    pytest.param(10080, 0.0, timedelta(days=7), "↻ em 7 d", "21/10/2026 09:00 BRT", id="weekly-real-equals-fetched-plus-duration"),
    pytest.param(10080, 0.0, None, "↻ ?", "data não informada", id="weekly-no-reset"),
    pytest.param(None, 0.0, timedelta(days=7), "↻ em 7 d", "21/10/2026 09:00 BRT", id="unknown-duration-valid-reset"),
    pytest.param(None, 0.0, None, "↻ ?", "data não informada", id="unknown-duration-no-reset"),
    pytest.param(10080, 0.0, "invaliddate", "↻ ?", "data não informada", id="weekly-invalid-reset"),
    pytest.param(10080, 12.0, timedelta(days=6), "↻ em 6 d", "20/10/2026 09:00 BRT", id="weekly-positive-real-use"),
    pytest.param(10080, 12.0, None, "↻ ?", "data não informada", id="positive-use-no-reset"),
    pytest.param(10080, None, None, "↻ ?", "data não informada", id="unknown-use-and-reset"),
    pytest.param(300, 0.0, timedelta(hours=5), "↻ em 5 h", "14/10/2026 14:00 BRT", id="session-equals-duration"),
    pytest.param(300, 0.0, timedelta(hours=5, seconds=-4), "↻ em 4 h 59 min", "14/10/2026 13:59 BRT", id="session-near-duration"),
    pytest.param(300, 0.0, timedelta(hours=2), "↻ em 2 h", "14/10/2026 11:00 BRT", id="zero-running"),
    pytest.param(300, 2.0, timedelta(hours=3, minutes=56), "↻ em 3 h 56 min", "14/10/2026 12:56 BRT", id="positive-running"),
])
def test_provider_fields_never_infer_inactivity(fixed_now, row_id, number_mode, duration, used, reset, expected, tooltip_date):
    reset_at = _iso(fixed_now + reset) if isinstance(reset, timedelta) else reset
    window = {"id": "weekly" if duration == 10080 else "session", "used_percent": used,
              "resets_at": reset_at, "duration_minutes": duration}
    display = {"status": "ok", "fetched_at": _iso(fixed_now), "windows": [window], "details": {}}
    quota, = [f for f in provider_fields(row_id, display, number_mode=number_mode) if f.kind == "quota"]
    assert quota.text == expected
    assert quota.percent == (None if used is None else 100 - used if number_mode == "remaining" else used)
    assert NOT_STARTED_TEXT not in quota.tooltip
    assert "primeiro uso" not in quota.tooltip and "sem contagem real" not in quota.tooltip
    assert f"renova {tooltip_date}" in quota.tooltip


@pytest.mark.parametrize("reset, tooltip_date", [
    (None, "data não informada"),
    ("invaliddate", "data não informada"),
    ("2026-10-21T12:00:00Z", "21/10/2026 09:00 BRT"),
])
def test_absolute_renewal_keeps_valid_date_or_unknown(fixed_now, reset, tooltip_date):
    window = {"id": "weekly", "duration_minutes": 10080, "used_percent": 0.0, "resets_at": reset}
    display = {"status": "ok", "fetched_at": _iso(fixed_now), "windows": [window], "details": {}}
    quota, = [f for f in provider_fields("codex_gpt2", display, reset_mode="absolute") if f.kind == "quota"]
    expected = "↻ " + (fixed_now + timedelta(days=7)).astimezone().strftime("%d/%m %H:%M")
    assert quota.text == (expected if reset == "2026-10-21T12:00:00Z" else "↻ ?")
    assert NOT_STARTED_TEXT not in quota.tooltip
    assert "primeiro uso" not in quota.tooltip and "sem contagem real" not in quota.tooltip
    assert f"renova {tooltip_date}" in quota.tooltip
