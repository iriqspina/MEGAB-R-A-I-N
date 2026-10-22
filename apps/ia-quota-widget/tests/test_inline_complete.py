"""Fixed-height board: essential values without scrolling; full details remain
reachable in both modes (human revision 2026-10-12)."""
import json
from datetime import datetime, timedelta, timezone

import pytest
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from widget_app import persistence
from widget_app.inline_contract import QUOTA_KINDS, TRACK_KINDS, header_state, provider_fields, schema
from widget_app.formatting import percent_label
from widget_app.main_window import MainWindow
from widget_app.snapshot_store import SnapshotStore
from widget_app.ui_inline_quota import InlineQuotaBody


def iso(**delta):
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()


def window(key, minutes, used, label=None, **kwargs):
    return dict(id=key, label=label or key, duration_minutes=minutes, used_percent=used,
                resets_at=iso(hours=2, minutes=30), **kwargs)


def full_snapshot(used_session=57.0, extra_windows=(), **kwargs):
    data = dict(status="ok", source="DEMO isolated test", fetched_at=iso(), message="", windows=[
        window("weekly_all", 10080, 6.0, "Semana"),
        window("session", 300, used_session, "Sessão"),
        window("weekly_scoped:Fable", 10080, None, "Semana · Fable"),
        window("base_model_inference:primary", 300, 100.0, "reserva"),
        *extra_windows,
    ], details={
        "resets": [{"title": "Reset completo", "count": 1, "total": 1, "kind": "full", "usable": True,
                    "expires_at": iso(days=9)},
                   {"title": "Reset de 5 horas", "count": 0, "kind": "five_hour", "usable": False}],
        "financial": [{"title": "Sessões na nuvem", "amount": 250.0, "total": 250.0, "currency": "USD", "status": "measured"},
                      {"title": "Créditos de uso", "amount": None, "currency": "", "status": "unavailable"}],
        "product_shares": [{"name": "Code", "percent": 9.0}],
        "notes": ["nota longa que não fica sempre aberta"],
    })
    data.update(kwargs)
    return data


def texts_of(fields):
    return [f.text for f in fields]


# ------------------------------------------------------------------ contract


def test_contract_has_every_kind_in_reading_order_and_unknown_is_dash():
    store = SnapshotStore()
    store.update("claude", full_snapshot())
    fields = provider_fields("claude", store.display("claude"), name="Claude")
    quota = [f for f in fields if f.kind == "quota"]
    assert [f.label for f in quota] == ["5 h", "semana", "Fable", "reserva"]
    assert [f.group for f in quota] == ["general", "general", "specific", "reserve"]
    kinds = [f.kind for f in fields]
    # Captions separate specific and reserve; extras live after the bars.
    assert kinds.index("caption") < kinds.index("reset") and kinds.count("caption") == 2
    assert fields[-1].kind == "source" and fields[-1].text.startswith("auto · DEMO isolated test")
    fable = quota[2]
    assert fable.percent is None  # unknown is never 0
    assert all(f.text.startswith("↻") for f in quota)
    resets = [f.text for f in fields if f.kind == "reset"]
    assert any("completo: 1/1 · disponível" in t for t in resets)
    assert any("5 h: 0 · indisponível" in t for t in resets)  # zero is a real zero
    money = [f.text for f in fields if f.kind == "financial"]
    assert any("USD 250,00 / 250,00" in t for t in money)
    assert any("Créditos de uso: —" in t for t in money)
    share = next(f for f in fields if f.kind == "share")
    assert "não é cota" in share.text and share.percent is None
    assert any("nota longa" in t for t in texts_of(fields))  # all details remain reachable in the body
    assert all(f.percent is None for f in fields if f.kind not in TRACK_KINDS)
    assert next(f for f in fields if f.id == "financial:0:ratio").percent == 100
    assert next(f for f in fields if f.id == "share:0").percent == 9


def test_contract_remaining_mode_and_absolute_reset():
    store = SnapshotStore()
    store.update("claude", full_snapshot(used_session=57.0))
    fields = provider_fields("claude", store.display("claude"), number_mode="remaining", reset_mode="absolute")
    session = next(f for f in fields if f.id == "quota:session")
    assert session.percent == pytest.approx(43.0)
    assert session.text.startswith("↻ ") and ":" in session.text
    fable = next(f for f in fields if f.id == "quota:weekly_scoped:Fable")
    assert fable.percent is None


@pytest.mark.parametrize("case", ["ok", "stale", "error_with_data", "error_without_data", "never", "querying"])
def test_status_variants_keep_honest_fields(case):
    store = SnapshotStore()
    if case == "ok":
        store.update("claude", full_snapshot())
    elif case == "stale":
        store.update("claude", full_snapshot(fetched_at=iso(hours=-3)))
    elif case == "error_with_data":
        store.update("claude", full_snapshot())
        store.update("claude", {"status": "error", "message": "erro DEMO"})
    elif case == "error_without_data":
        store.update("claude", {"status": "error", "message": "erro DEMO"})
    display = None if case in ("never", "querying") else store.display("claude")
    fields = provider_fields("claude", display, querying=case == "querying")
    symbol, text = header_state(display, case == "querying")
    if case == "ok":
        assert symbol == "●" and len([f for f in fields if f.kind == "quota"]) == 4
    elif case == "stale":
        assert symbol == "◷" and "antigo" in text
    elif case == "error_with_data":
        assert symbol == "!" and "erro" in text and "dado" in text
        assert len([f for f in fields if f.kind == "quota"]) == 4  # last good data stays visible
    elif case == "error_without_data":
        assert symbol == "!"
        assert [f.text for f in fields if f.kind == "status"] == ["erro · sem dado"]
        assert any(f.kind == "reset" and "—" in f.text for f in fields)
        assert not any(f.kind == "quota" for f in fields)
    elif case == "never":
        assert texts_of(fields) == ["aguardando consulta"] and symbol == "○"
    else:
        assert texts_of(fields) == ["consultando…"] and symbol == "↻"
    assert "0%" not in " ".join(texts_of(fields))


# ------------------------------------------------------------------ main window


@pytest.fixture
def trilho(qt_app, monkeypatch):
    settings = persistence.Settings(visual_mode="trilho", strip_width=1080)
    settings.set_visible("spark", False)
    persistence.save_settings(settings)
    win = MainWindow(demo=True, session_only=True)
    monkeypatch.setattr(win, "_available_rect", lambda: QRect(0, 0, 2400, 1400))
    win.show_positioned()
    win._on_snapshot("claude", full_snapshot())
    qt_app.processEvents()
    yield win
    win.close()
    win.deleteLater()


def cell_of(win, row="claude"):
    win.strip.start = win.strip.order.index(row)
    win.strip.arrange()
    return win.strip.cells[row]


def test_trilho_column_pins_values_and_preserves_full_details(trilho, qt_app):
    trilho.update_settings({"strip_height": 112})
    cell = cell_of(trilho)
    qt_app.processEvents()
    assert isinstance(cell.body, InlineQuotaBody) and not cell.body.isVisible()
    assert cell.glance.isVisible()
    body = cell.body.fields
    assert body.field_ids() == [f.id for f in cell.fields]
    lines = body.texts()
    assert any(line.startswith("5 h | 57% | ↻") for line in lines)
    assert any(line.startswith("Fable | — | ") for line in lines)
    assert any("reserva" in line and "100%" in line for line in lines)
    assert any(line.startswith("♻ completo") for line in lines)
    assert any("USD 250" in line for line in lines)
    visible = cell.glance.geometry_checks()
    assert all(item["contained"] and item["text_fits"] for item in visible)
    assert any("5 h 57% ↻" in item["text"] for item in visible)
    assert any("Fable —" in item["text"] for item in visible)
    assert any("USD 250" in item["text"] for item in visible)
    assert any(item["id"].startswith("reset:") for item in visible)
    assert cell.glance.fits and not cell.glance.warning.isVisible()
    assert cell.body.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff
    assert cell.body.minimumSizeHint().height() == 0
    assert body.width() <= cell.body.viewport().width()


@pytest.mark.parametrize("height", [40, 72, 112, 150])
@pytest.mark.parametrize("big", [False, True])
def test_exact_height_independent_of_fonts_refresh_and_mode(trilho, qt_app, height, big):
    win = trilho
    if big:
        win.update_settings({"size_name": 32, "size_value": 28, "size_hint": 20, "size_detail": 20, "scale": 1.5})
    win.update_settings({"strip_height": height})
    qt_app.processEvents()
    assert win.height() == height
    cell = cell_of(win)
    qt_app.processEvents()
    assert cell.height() == height - 6
    assert cell.body.geometry().bottom() < cell.height()
    assert cell.body.y() == win.strip.header_height()
    bar = cell.body.verticalScrollBar()
    if height < 60:
        assert cell.body.isVisible() and not cell.glance.isVisible()
        assert bar.maximum() > 0 and bar.isVisible()  # declared micro fallback
    else:
        assert cell.glance.isVisible() and not cell.body.isVisible()
        assert not bar.isVisible()
        assert cell.glance.geometry() == cell.body.geometry()
        assert cell.glance.font_px() == (9 if height == 72 else 11)
    if big:
        # The saved preference is kept; the compact header labels its cap.
        assert win.settings.size_name == 32 and "nome reduzido" in cell.accessibleName()
        assert [f.pixelSize() for f in win.strip.fonts()] == [48, 42, 30]
    win._on_snapshot("claude", full_snapshot(used_session=12.0))
    win._refresh_ages()
    qt_app.processEvents()
    assert win.height() == height
    for mode in ("legacy", "trilho", "legacy"):
        win.update_settings({"visual_mode": mode})
        qt_app.processEvents()
        assert win.height() == height
        win._on_snapshot("claude", full_snapshot(used_session=30.0))
        qt_app.processEvents()
        assert win.height() == height
    assert win._board.minimumSizeHint().height() == 0


def test_scroll_and_focus_survive_refresh_in_place_and_rebuild(trilho, qt_app):
    win = trilho
    win.update_settings({"strip_height": 40})
    qt_app.processEvents()
    cell = cell_of(win)
    win.activateWindow()
    cell.setFocus()
    qt_app.processEvents()
    bar = cell.body.verticalScrollBar()
    assert bar.maximum() > 0
    bar.setValue(bar.maximum() // 2 + 1)
    value, size, geometry = bar.value(), win.size(), cell.body.geometry()
    rebuilds = cell.body.fields.rebuilds
    win._on_snapshot("claude", full_snapshot())  # identical data
    win._on_snapshot("claude", full_snapshot(used_session=88.0))  # changed values, same schema
    win._refresh_ages()
    qt_app.processEvents()
    assert cell.body.fields.rebuilds == rebuilds  # updated in place
    assert bar.value() == value and win.size() == size and cell.body.geometry() == geometry
    assert QApplication.focusWidget() is cell
    assert any(line.startswith("5 h | 88%") for line in cell.body.fields.texts())
    win._on_snapshot("claude", full_snapshot(extra_windows=[window("monthly", 43200, 3.0, "Mensal")]))
    qt_app.processEvents()
    assert cell.body.fields.rebuilds == rebuilds + 1  # schema changed
    assert bar.value() == value and win.size() == size
    assert QApplication.focusWidget() is cell
    QTest.keyClick(cell, Qt.Key_Down)
    qt_app.processEvents()
    assert bar.value() > value and QApplication.focusWidget() is cell


def test_every_field_is_reachable_inside_the_viewport(trilho, qt_app):
    win = trilho
    win.update_settings({"strip_height": 40})
    qt_app.processEvents()
    cell = cell_of(win)
    qt_app.processEvents()
    viewport = cell.body.viewport()
    for field_id in cell.body.fields.field_ids():
        for widget in cell.body.fields.widgets(field_id):
            cell.body.ensureWidgetVisible(widget, 0, 0)
            qt_app.processEvents()
            rect = QRect(widget.mapTo(viewport, QPoint(0, 0)), widget.size())
            assert rect.intersects(viewport.rect()), field_id


@pytest.mark.parametrize("expanded", [False, True])
def test_legacy_and_trilho_show_the_same_information(trilho, qt_app, expanded):
    win = trilho
    win.update_settings({"visual_mode": "legacy", "expanded": expanded, "strip_height": 300})
    qt_app.processEvents()
    segment = win._segments["claude"]
    cell = win.strip.cells["claude"]
    extras = [f"{f.label} | {percent_label(f.percent)} | {f.text}" if f.kind in TRACK_KINDS else f.text
              for f in cell.fields if f.kind not in QUOTA_KINDS and f.kind != "status"]
    assert segment._fields.texts() == extras and segment._fields.isHidden() == (not expanded)
    assert segment.glance.isVisible() and segment.overview_mode
    assert [(item.id, item.value, item.percent) for item in segment.glance.quotas + segment.glance.items] == [
        (item.id, item.value, item.percent) for item in cell.glance.quotas + cell.glance.items]
    quota = {(f.id.removeprefix('quota:'), percent_label(f.percent)) for f in cell.fields if f.kind == "quota"}
    assert {(bar.window_key, bar._pct.text()) for bar in segment._bars} == quota
    for bar in segment._bars:
        assert not bar._extra.isHidden() and bar._extra_full.startswith("renova")
    assert win.height() == 300 and win._board.isVisible()


def test_browser_evidence_is_distinct_from_automatic_data(qt_app, monkeypatch, tmp_path):
    (tmp_path / "account_balance_observed.json").write_text(json.dumps({
        "observed_at": "2026-09-01T08:15:00-03:00",
        "accounts": {"claude": {"balance": 12.5, "currency": "USD", "scope": "API", "source": "navegador",
                                "resets": [{"title": "Completo", "kind": "full", "count": 1, "usable": True}]}}}),
        encoding="utf-8")
    persistence.save_settings(persistence.Settings(visual_mode="trilho"))
    win = MainWindow(demo=False, session_only=True)
    monkeypatch.setattr(win.poller, "poll", lambda ids: None)
    win.show_positioned()
    snapshot = full_snapshot()
    snapshot["details"] = {"financial": [], "resets": [], "product_shares": [], "notes": []}
    win._on_snapshot("claude", snapshot)
    qt_app.processEvents()
    fields = win.strip.cells["claude"].fields
    kinds = [f.kind for f in fields]
    assert "browser" in kinds and "legend" in kinds and kinds[-1] == "source"
    browser = next(f for f in fields if f.kind == "browser")
    assert "USD 12,50" in browser.text and "01/09 08:15" in browser.text
    assert any(f.kind == "reset" and 'não confirmado' in f.text for f in fields)
    assert not any(f.kind == "reset" and '1/1' in f.text for f in fields)
    assert fields[-1].text.startswith("auto · ") and "01/09 08:15" not in fields[-1].text
    win.update_settings({"visual_mode": "legacy"})
    assert any(t.startswith("$ saldo*") for t in win._segments["claude"]._fields.texts())
    win.close()
    win.deleteLater()


def test_demo_never_mixes_browser_evidence(trilho, tmp_path):
    (tmp_path / "account_balance_observed.json").write_text(json.dumps({
        "observed_at": "2026-10-11T21:00:00-03:00", "accounts": {"claude": {"balance": 99, "currency": "USD"}}}),
        encoding="utf-8")
    trilho._refresh_ages()
    assert not any(f.kind in ("browser", "legend") for f in trilho.strip.cells["claude"].fields)


def test_settings_preview_uses_same_component_and_demo_data(trilho, qt_app):
    win = trilho
    dialog = win.open_settings(show=False)
    assert dialog.tabs.widget(3).findChild(type(dialog.height_combo)) is not None
    preview = dialog.preview
    data = full_snapshot()
    win.store.update("claude", data)
    preview.store.update("claude", data)
    win.strip.refresh()
    preview.refresh(win.settings)
    qt_app.processEvents()
    mine, theirs = win.strip.cells["claude"], preview.strip.cells["claude"]
    assert type(theirs.body) is type(mine.body)
    assert theirs.body.fields.texts() == mine.body.fields.texts()
    assert schema(theirs.fields) == schema(mine.fields)
    assert preview.strip.mode.text() == "DEMO"
    win.update_settings({"visual_mode": "legacy"})
    dialog.preview.refresh(win.settings)
    win._refresh_all_segments()
    assert preview.segment._fields.texts() == win._segments["claude"]._fields.texts()
    dialog.close()


def test_height_control_is_labelled_for_both_modes(trilho, qt_app):
    from PySide6.QtWidgets import QFormLayout
    dialog = trilho.open_settings(show=False)
    form = dialog.tabs.widget(3).layout()
    assert isinstance(form, QFormLayout)
    label = form.labelForField(dialog.height_combo)
    assert label is not None and label.text() == "Altura da faixa"
    dialog.mode_combo.setCurrentIndex(dialog.mode_combo.findData("legacy"))
    dialog.height_combo.setCurrentIndex(dialog.height_combo.findData(40))
    qt_app.processEvents()
    assert trilho.height() == 40 and trilho.settings.visual_mode == "legacy"
    dialog.height_combo.setCurrentIndex(dialog.height_combo.findData(112))
    qt_app.processEvents()
    assert trilho.height() == 112
    dialog.close()


@pytest.mark.parametrize("mode",["trilho","legacy"])
def test_session_and_week_bars_fit_first_view_at_human_fonts(trilho, qt_app, mode):
    win=trilho
    win.update_settings({'visual_mode':mode,'window_width':1080,'window_height':72,'strip_width':1080,'strip_height':72,'size_name':32,'size_value':28,
                         'size_hint':9,'size_detail':18,'scale':0.8})
    qt_app.processEvents()
    cell=cell_of(win)
    qt_app.processEvents()
    assert cell.glance.isVisible() and not cell.body.isVisible()
    for field_id in ('quota:session','quota:weekly_all'):
        row = next(row for row in cell.glance.rows if row['item'].id == field_id)
        track = row['widgets'][1]
        assert cell.glance.rect().contains(track.geometry()), (field_id,track.geometry(),cell.glance.rect())


def test_monetary_and_product_ratios_do_not_flip_with_remaining_mode():
    snapshot=full_snapshot()
    before=provider_fields('claude',snapshot,number_mode='used')
    after=provider_fields('claude',snapshot,number_mode='remaining')
    assert {f.id:f.percent for f in before if f.kind=='ratio'} == {f.id:f.percent for f in after if f.kind=='ratio'}
    assert next(f for f in after if f.id=='quota:session').percent == 43


def test_cached_reading_is_saved_not_a_red_error():
    symbol,text=header_state({'status':'cached','stale':True,'fetched_at':iso(hours=-1)})
    assert symbol=='◷' and 'salvo' in text and 'cached' not in text


def test_browser_control_fields_keep_units_and_full_source():
    browser={'balance':0,'currency':'BRL','observed_at':iso(hours=-2),'source':'https://claude.ai/settings/billing',
             'monthly_spent':0,'monthly_cap':1200,'extra_enabled':False,'auto_reload':False}
    fields=provider_fields('claude',full_snapshot(),browser=browser)
    assert any('teto: BRL 1 200,00' in f.text and 'não é saldo' in f.text for f in fields)
    assert any(browser['source'] in f.text and f.kind=='source' for f in fields)


@pytest.mark.parametrize("height",[40,72,112])
def test_legacy_fixed_height_uses_declared_monitor_or_micro_fallback(trilho,qt_app,height):
    trilho.update_settings({'strip_height':height,'visual_mode':'legacy'})
    qt_app.processEvents()
    assert trilho.settings.visual_mode=='legacy' and trilho.height()==height
    assert trilho.strip.isVisible()
    cell=cell_of(trilho)
    qt_app.processEvents()
    if height < 60:
        assert cell.body.isVisible() and cell.body.viewport().height()>=14
        assert cell.body.verticalScrollBar().maximum()>0
    else:
        assert cell.glance.isVisible() and not cell.body.isVisible()
        assert cell.glance.height() >= 14


def test_custom_height_is_explicit_in_settings(trilho,qt_app):
    trilho.update_settings({'strip_height':90})
    dialog=trilho.open_settings(show=False)
    assert dialog.height_combo.currentData()==90
    assert '90' in dialog.height_combo.currentText()
    dialog.close()


def test_header_cap_accessibility_updates_without_waiting_for_next_poll(trilho,qt_app):
    trilho.update_settings({'size_name':32,'scale':1.5,'strip_height':112})
    qt_app.processEvents()
    trilho.update_settings({'strip_height':40})
    qt_app.processEvents()
    cell=cell_of(trilho)
    assert 'para 10px' in cell.accessibleName()


def test_rebuilt_legacy_bars_inherit_expanded_state(trilho,qt_app):
    trilho.update_settings({'visual_mode':'legacy','expanded':True,'strip_height':112})
    trilho._on_snapshot('claude',full_snapshot(extra_windows=[window('new_scoped',1440,2)]))
    qt_app.processEvents()
    assert all(bar._expanded for bar in trilho._segments['claude']._bars)
