import pytest
from PySide6.QtWidgets import QWidget

from widget_app import theme
from widget_app.snapshot_store import SnapshotStore
from widget_app.ui_provider_segment import ProviderSegment, pacing_text


@pytest.fixture
def parent(qt_app):
    return QWidget()


def test_card_frame_holds_header_hint_summary_and_bars(parent):
    segment = ProviderSegment("codex", "Codex", parent)
    for attr in ("_name_wrap", "_hint", "_track", "_bars_wrap"):
        assert getattr(segment, attr) is not None


def test_never_read_shows_waiting_placeholder(parent):
    segment = ProviderSegment("codex", "Codex", parent)
    store = SnapshotStore()
    segment.update_from_store(store, expanded=False)
    assert segment._value.text() == "—"
    assert segment._hint.text() == "aguardando consulta"


def test_ok_snapshot_shows_worst_window_not_average(parent):
    segment = ProviderSegment("claude", "Claude", parent)
    store = SnapshotStore()
    store.update(
        "claude",
        {
            "status": "ok",
            "windows": [
                {"id": "session", "label": "Sessão", "used_percent": 20, "resets_at": None},
                {"id": "week", "label": "Semana", "used_percent": 78, "resets_at": None},
            ],
            "fetched_at": "2026-09-08T10:00:00Z",
            "message": "",
            "source": "teste",
        },
    )
    segment.update_from_store(store, expanded=False)
    assert segment._value.text() == "78%"
    # O nome da janela não se repete no hint; a pior se vê pela barra mais cheia.
    labels = [bar._label.text() for bar in segment._bars]
    assert labels == ["5 h", "semana"]
    pcts = [bar._pct.text() for bar in segment._bars]
    assert pcts == ["20%", "78%"]


def test_show_querying_blanks_value_and_never_shows_stale_number(parent):
    segment = ProviderSegment("claude", "Claude", parent)
    store = SnapshotStore()
    store.update("claude", {"status": "ok", "windows": [{"id": "a", "label": "A", "used_percent": 55, "resets_at": None}], "fetched_at": "x", "message": "", "source": ""})
    segment.update_from_store(store, expanded=False)
    assert segment._value.text() == "55%"

    segment.show_querying()
    assert segment._value.text() == "—"
    assert segment._hint.text() == "consultando…"


def test_refresh_reuses_bars_instead_of_recreating_them(parent):
    # 260915: leitura nova NÃO pode recriar as linhas — re-animar a barra do
    # zero e mexer no layout do card roubava a atenção do <USUARIO>.
    store = SnapshotStore()
    windows = [
        {"id": "session", "label": "Sessão", "used_percent": 20, "resets_at": None},
        {"id": "week", "label": "Semana", "used_percent": 78, "resets_at": None},
    ]
    store.update("claude", _snapshot(windows))
    segment = ProviderSegment("claude", "Claude", parent)
    segment.update_from_store(store, expanded=False)
    before = list(segment._bars)

    windows[0]["used_percent"] = 45  # mesma janela, valor novo
    store.update("claude", _snapshot(windows))
    segment.update_from_store(store, expanded=False)

    assert segment._bars[0] is before[0]  # MESMO widget: a barra desliza pro novo valor
    assert segment._bars[0]._track._percent == 45
    assert segment._bars[0]._pct.text() == "45%"
    assert segment._bars[1] is before[1]


def test_show_querying_keeps_last_data_on_screen(parent):
    store = SnapshotStore()
    store.update("claude", _snapshot(None))
    segment = ProviderSegment("claude", "Claude", parent)
    segment.update_from_store(store, expanded=False)
    segment.show_querying()
    assert segment._hint.text() == "consultando…"
    assert len(segment._bars) == 1  # o card não encolhe durante a consulta
    assert segment._bars[0]._track._percent == 50


def test_window_set_change_reuses_surviving_bars_and_drops_gone_ones(parent):
    store = SnapshotStore()
    windows = [
        {"id": "session", "label": "Sessão", "used_percent": 20, "resets_at": None},
        {"id": "week", "label": "Semana", "used_percent": 78, "resets_at": None},
    ]
    store.update("claude", _snapshot(windows))
    segment = ProviderSegment("claude", "Claude", parent)
    segment.update_from_store(store, expanded=False)
    session_bar = segment._bars[0]

    store.update("claude", _snapshot([windows[0]]))  # a semana sumiu da conta
    segment.update_from_store(store, expanded=False)
    assert [bar.window_key for bar in segment._bars] == ["session"]
    assert segment._bars[0] is session_bar


def test_apply_theme_changes_text_color(parent):
    segment = ProviderSegment("codex", "Codex", parent)
    dark_style = segment._name.styleSheet()
    segment.apply_theme(theme.palette_for("nevoa"))
    light_style = segment._name.styleSheet()
    assert dark_style != light_style
    assert theme.SURFACE_PRESETS["nevoa"]["text"] in light_style


def test_apply_theme_never_changes_provider_identity_dot_color(parent):
    segment = ProviderSegment("codex", "Codex", parent)
    before = segment._dot.color
    segment.apply_theme(theme.palette_for("papel"))
    assert segment._dot.color == before
    # só o contorno muda, pra não sumir no painel claro
    assert segment._dot._ring.alpha() > 0


def test_pacing_text_nao_medido_or_missing_is_blank():
    assert pacing_text(None) == ""
    assert pacing_text({"status": "NAO_MEDIDO"}) == ""


def test_pacing_text_pause_and_desacelerar_never_invent_a_number():
    assert pacing_text({"status": "pause"}) == "no limite"
    assert pacing_text({"status": "desacelerar"}) == "ritmo alto, desacelere"


def test_pacing_text_prefers_day_and_uses_decimal_comma_without_false_precision():
    both = {"status": "ok", "target_per_business_day": 16.67, "target_per_hour": 20.0}
    assert pacing_text(both) == "dá ~17%/dia"
    hour_only = {"status": "ok", "target_per_business_day": None, "target_per_hour": 4.26}
    assert pacing_text(hour_only) == "dá ~4,3%/h"
    assert pacing_text({"status": "ok", "target_per_hour": 3.0}) == "dá ~3%/h"


def _snapshot(windows, used=50):
    return {
        "status": "ok",
        "windows": windows or [{"id": "session", "label": "Sessão", "used_percent": used, "resets_at": None}],
        "fetched_at": "2026-09-09T10:00:00Z",
        "message": "Plano max.",
        "source": "api.teste/usage",
    }


def _detail_texts(segment):
    # Extras das barras: renovação + ritmo vivem no fim da linha da janela.
    return [bar._extra.text() for bar in segment._bars]


def test_pacing_reaches_the_expanded_detail_row(parent):
    segment = ProviderSegment("claude", "Claude", parent)
    store = SnapshotStore()
    store.update("claude", _snapshot(None, 65))
    pacing = {"status": "desacelerar", "windows": {"session": {"status": "desacelerar"}}}
    segment.update_from_store(store, expanded=True, pacing=pacing)
    assert any("desacelere" in t for t in _detail_texts(segment))


def test_missing_pacing_never_fabricates_a_ritmo_line(parent):
    segment = ProviderSegment("claude", "Claude", parent)
    store = SnapshotStore()
    store.update("claude", _snapshot(None))
    segment.update_from_store(store, expanded=True)  # sem pacing
    assert not any("ritmo" in t or "dá ~" in t for t in _detail_texts(segment))


CODEX_WINDOWS = [
    {"id": "codex:primary", "label": "codex · 7 d", "used_percent": 52, "resets_at": None},
    {"id": "codex_bengalfox:primary", "label": "GPT-5.3-Codex-Spark · 5 h", "used_percent": 90, "resets_at": None},
    {"id": "codex_bengalfox:secondary", "label": "GPT-5.3-Codex-Spark · 7 d", "used_percent": 10, "resets_at": None},
]


def test_spark_is_its_own_row_and_codex_row_excludes_it(parent):
    store = SnapshotStore()
    store.update("codex", _snapshot(CODEX_WINDOWS))
    codex = ProviderSegment("codex", "Codex", parent)
    spark = ProviderSegment("spark", "Spark", parent)
    codex.update_from_store(store, expanded=True)
    spark.update_from_store(store, expanded=True)
    # O 90 % do Spark não pode virar o número grande do Codex, e vice-versa.
    assert codex._value.text() == "52%"
    assert "renova" in codex._hint.text()
    assert spark._value.text() == "90%"
    assert "renova" in spark._hint.text()
    assert "Spark" not in " ".join(_detail_texts(codex))


def test_spark_row_without_spark_windows_says_so(parent):
    store = SnapshotStore()
    store.update("codex", _snapshot(CODEX_WINDOWS[:1]))
    spark = ProviderSegment("spark", "Spark", parent)
    spark.update_from_store(store, expanded=False)
    assert spark._value.text() == "—"
    assert spark._hint.text() == "sem janela nesta conta"


def test_bar_extra_labels_never_wrap_and_plan_source_live_in_name_tooltip(parent):
    store = SnapshotStore()
    store.update("claude", _snapshot(None))
    segment = ProviderSegment("claude", "Claude", parent)
    segment.update_from_store(store, expanded=True)
    for bar in segment._bars:
        assert not bar._extra.wordWrap()
    assert not segment._hint.wordWrap()
    assert "Plano max." in segment._name_wrap.toolTip()
    assert "api.teste/usage" in segment._name_wrap.toolTip()
    assert "Fonte técnica" not in " ".join(_detail_texts(segment))
