"""Selection for Trilho, independent of Qt, usage, reset and input order.

Human decision 2026-10-11 17:30:46 supersedes the plan's worst-window rule.
Only explicit duration is evidence of a five-hour window; slot names are not.
"""
from math import isfinite

from . import theme
from .formatting import age_label


def duration_minutes(window):
    value = window.get("duration_minutes")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if isfinite(value) and value > 0 else None


def is_reserve(window):
    return str(window.get("id", "")).startswith("base_model_inference:")


def focus_window(windows):
    """Return an original object; never sort/mutate the detail's input list.

    Callers select the account/bucket first. No known durations: first window,
    explicitly labelled unknown. A 5h window without a number still wins.
    """
    windows = list(windows)
    for window in windows:
        if duration_minutes(window) == 300:
            return window
    known = [w for w in windows if duration_minutes(w) is not None]
    return min(known, key=duration_minutes) if known else next(iter(windows), None)


def general_windows(windows, row_id):
    predicate = theme.row_window_filter(row_id)
    return [w for w in windows if not is_reserve(w)
            and theme.is_spark_window(w) == (row_id == "spark")
            and (predicate is None or predicate(w))]


def exhausted_windows(windows, focus=None):
    return [w for w in windows if w is not focus and w.get("used_percent") is not None
            and w["used_percent"] >= 100]


def duration_label(window):
    minutes = duration_minutes(window or {})
    if minutes is None:
        return "janela ?"
    if minutes % 1440 == 0:
        return f"{minutes / 1440:g} d"
    if minutes % 60 == 0:
        return f"{minutes / 60:g} h"
    return f"{minutes:g} min"


def state_label(display, focus, querying=False):
    if querying:
        return "consultando"
    if display is None:
        return "aguardando"
    status = display.get("status")
    if status != "ok":
        return theme.STATUS_SHORT_LABEL.get(status) or str(status)
    if display.get("stale"):
        return "antigo"
    if focus is None or focus.get("used_percent") is None:
        return "sem dado"
    return age_label(display.get("fetched_at"))
