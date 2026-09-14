from datetime import datetime, timedelta, timezone

from budget_pacing import provider_pacing, window_pacing

_START = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _five_hour_window(used_percent, now_offset_hours, **extra):
    resets_at = _START + timedelta(hours=5)
    now = _START + timedelta(hours=now_offset_hours)
    window = {
        "id": "session",
        "used_percent": used_percent,
        "resets_at": resets_at.isoformat(),
        "duration_minutes": 300,
    }
    window.update(extra)
    return window, now


def test_missing_used_percent_is_nao_medido():
    window = {"id": "a", "used_percent": None, "resets_at": _START.isoformat(), "duration_minutes": 300}
    result = window_pacing(window, _START)
    assert result["status"] == "NAO_MEDIDO"


def test_missing_resets_at_is_nao_medido():
    window = {"id": "a", "used_percent": 10.0, "resets_at": None, "duration_minutes": 300}
    result = window_pacing(window, _START)
    assert result["status"] == "NAO_MEDIDO"


def test_resets_at_in_the_past_is_nao_medido():
    window, _ = _five_hour_window(10.0, 0)
    now = _START + timedelta(hours=10)  # depois do resets_at
    result = window_pacing(window, now)
    assert result["status"] == "NAO_MEDIDO"


def test_even_pace_is_ok():
    window, now = _five_hour_window(50.0, 2.5)  # metade da janela, metade usada
    result = window_pacing(window, now)
    assert result["status"] == "ok"
    assert result["elapsed_fraction"] == 0.5
    assert result["ideal_used_by_now"] == 50.0
    assert result["ahead_by"] == 0.0
    assert result["hours_to_reset"] == 2.5
    assert result["target_per_hour"] == 20.0


def test_ahead_of_pace_under_threshold_stays_ok():
    window, now = _five_hour_window(55.0, 2.5)  # ideal seria 50, adiantado só 5
    result = window_pacing(window, now, decelerate_threshold=60.0)
    assert result["status"] == "ok"
    assert result["ahead_by"] == 5.0


def test_ahead_of_pace_over_threshold_triggers_desacelerar():
    window, now = _five_hour_window(65.0, 2.5)  # ideal 50, adiantado 15, >=60 usado
    result = window_pacing(window, now, decelerate_threshold=60.0)
    assert result["status"] == "desacelerar"
    assert result["ahead_by"] == 15.0


def test_behind_pace_never_triggers_desacelerar_even_above_threshold():
    window, now = _five_hour_window(60.0, 4.0)  # ideal seria 80: está atrasado, não adiantado
    result = window_pacing(window, now, decelerate_threshold=60.0)
    assert result["status"] == "ok"
    assert result["ahead_by"] < 0


def test_used_at_100_is_pause_regardless_of_pace():
    window, now = _five_hour_window(100.0, 0.1)
    result = window_pacing(window, now)
    assert result["status"] == "pause"


def test_hour_scale_window_has_no_business_day_target():
    window, now = _five_hour_window(50.0, 2.5)
    result = window_pacing(window, now)
    assert result["target_per_business_day"] is None


def test_missing_duration_falls_back_to_business_days():
    resets_at = _START + timedelta(days=3)
    now = _START
    window = {"id": "weekly", "used_percent": 50.0, "resets_at": resets_at.isoformat()}
    result = window_pacing(window, now, business_days=6)
    # fallback = 6 dias; reset em 3 dias => metade da janela, ritmo uniforme
    assert result["elapsed_fraction"] == 0.5
    assert result["ideal_used_by_now"] == 50.0
    assert result["status"] == "ok"
    # duração adivinhada: status usa o fallback, mas não inventa uma cifra
    # por dia com precisão que a leitura não tem (achado da revisão Fable).
    assert result["target_per_business_day"] is None


def test_day_scale_window_reports_business_day_target():
    resets_at = _START + timedelta(days=3)
    now = _START
    window = {"id": "weekly", "used_percent": 50.0, "resets_at": resets_at.isoformat(), "duration_minutes": 6 * 1440}
    result = window_pacing(window, now, business_days=6)
    assert result["target_per_business_day"] == 16.67


def test_provider_pacing_non_ok_snapshot_is_nao_medido():
    snapshot = {"provider": "claude", "status": "rate_limited", "windows": []}
    result = provider_pacing(snapshot, _START)
    assert result["status"] == "NAO_MEDIDO"
    assert result["windows"] == {}


def test_provider_pacing_empty_windows_is_nao_medido():
    snapshot = {"provider": "claude", "status": "ok", "windows": []}
    result = provider_pacing(snapshot, _START)
    assert result["status"] == "NAO_MEDIDO"


def test_provider_pacing_worst_status_wins():
    ok_window, now = _five_hour_window(50.0, 2.5)
    ok_window["id"] = "session"
    pause_window = {
        "id": "weekly",
        "used_percent": 100.0,
        "resets_at": (_START + timedelta(days=3)).isoformat(),
        "duration_minutes": 6 * 1440,
    }
    snapshot = {"provider": "codex", "status": "ok", "windows": [ok_window, pause_window]}
    result = provider_pacing(snapshot, now)
    assert result["status"] == "pause"
    assert result["windows"]["session"]["status"] == "ok"
    assert result["windows"]["weekly"]["status"] == "pause"
