from datetime import datetime, timedelta, timezone

from widget_app.formatting import age_label, parse_iso, percent_label, reset_label


def test_parse_iso_rejects_non_string_without_raising():
    assert parse_iso(None) is None
    assert parse_iso(123) is None
    assert parse_iso(45.6) is None
    assert parse_iso(True) is None
    assert parse_iso("") is None


def test_parse_iso_accepts_zulu_suffix():
    dt = parse_iso("2026-09-08T12:00:00Z")
    assert dt is not None
    assert dt.tzinfo is not None


def test_parse_iso_rejects_garbage_string():
    assert parse_iso("not-a-date") is None


def test_age_label_minutes_ago():
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert age_label(five_min_ago) == "há 5 min"


def test_age_label_no_reading():
    assert age_label(None) == "sem leitura"
    assert age_label(42) == "sem leitura"


def test_reset_label_future_minutes():
    in_ten_min = (datetime.now(timezone.utc) + timedelta(minutes=10, seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert reset_label(in_ten_min) == "renova em 10 min"


def test_reset_label_unknown():
    assert reset_label(None) == "renovação desconhecida"
    assert reset_label(True) == "renovação desconhecida"


def test_percent_label():
    assert percent_label(None) == "—"
    assert percent_label(42.6) == "43%"
    assert percent_label(0) == "0%"
    assert percent_label(0.3) == "<1%"


def test_friendly_window_label_drops_model_prefix_keeps_model_suffix():
    from widget_app.formatting import friendly_window_label

    assert friendly_window_label("codex · 7 d") == "Semana"
    assert friendly_window_label("GPT-5.3-Codex-Spark · 5 h") == "Sessão"
    assert friendly_window_label("Semana · Fable") == "Semana · Fable"
    assert friendly_window_label("Sessão") == "Sessão"
    assert friendly_window_label("x · 1 d") == "1 d"
    assert friendly_window_label(None) == ""
