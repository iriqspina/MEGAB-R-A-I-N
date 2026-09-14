from widget_app import theme


def test_fresh_ok_uses_percent_color():
    assert theme.stale_aware_track_color("ok", 50, stale=False, age_seconds=0) == theme.STATUS_GREEN
    assert theme.stale_aware_track_color("ok", 80, stale=False, age_seconds=0) == theme.STATUS_AMBER
    assert theme.stale_aware_track_color("ok", 95, stale=False, age_seconds=0) == theme.STATUS_RED


def test_error_without_prior_good_data_shows_immediately():
    assert theme.stale_aware_track_color("error", None, stale=False, age_seconds=None) == theme.STATUS_MAROON


def test_transient_failure_within_grace_keeps_percent_color_not_flashing_grey():
    color = theme.stale_aware_track_color("error", 82, stale=True, age_seconds=30)
    assert color == theme.STATUS_AMBER


def test_failure_past_grace_period_degrades_to_maroon():
    color = theme.stale_aware_track_color(
        "error", 82, stale=True, age_seconds=theme.STALE_GRACE_SECONDS + 1
    )
    assert color == theme.STATUS_MAROON


def test_unavailable_past_grace_degrades_to_grey_not_maroon():
    color = theme.stale_aware_track_color(
        "unavailable", 20, stale=True, age_seconds=theme.STALE_GRACE_SECONDS + 1
    )
    assert color == theme.STATUS_GREY


def test_stale_with_unknown_age_degrades_immediately():
    color = theme.stale_aware_track_color("error", 20, stale=True, age_seconds=None)
    assert color == theme.STATUS_MAROON


def test_window_category_id_wins_over_label_and_label_fallback():
    from widget_app.theme import window_category

    assert window_category({"id": "codex_bengalfox:primary", "label": "qualquer coisa estranha"}) == "session"
    assert window_category({"id": "weekly_scoped:Fable", "label": "Semana · Fable"}) == "weekly"
    assert window_category({"id": "desconhecido", "label": "Mensal"}) == "monthly"
    assert window_category({"id": "desconhecido", "label": "Sem nome útil"}) is None


def test_daily_category_color_differs_from_status_amber():
    from widget_app import theme

    assert theme.window_category_color("daily") != theme.STATUS_AMBER
