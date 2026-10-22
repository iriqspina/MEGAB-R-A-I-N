"""Isolated UI integration checks. Never use real settings, network or browser."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QDesktopServices, QFontDatabase, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from widget_app import persistence, ui_quota_details
from widget_app.main_window import MainWindow
from widget_app.provider_brand import ACCOUNT_URLS, brand_pixmap, provider_name
from widget_app.ui_quota_details import QuotaDetails, detailed_percent, safe_text, timestamp


def quota(key="session", used=10.125, duration=300):
    return {"id": key, "label": key, "duration_minutes": duration, "used_percent": used,
            "resets_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()}


def snapshot(windows=None, **extra):
    result = {"status": "ok", "source": "consulta oficial isolada",
              "windows": [quota()] if windows is None else windows,
              "fetched_at": datetime.now(timezone.utc).isoformat(), "message": ""}
    result.update(extra)
    return result


@pytest.fixture
def win(qt_app, monkeypatch):
    # Offscreen omits Windows fallback fonts; register the actual installed glyphs.
    for name in ("seguisym.ttf", "seguiemj.ttf"):
        font_path = Path("C:/Windows/Fonts") / name
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    persistence.save_settings(persistence.Settings(visual_mode="trilho"))
    monkeypatch.setattr(ui_quota_details, "observed_info", lambda row: None)
    window = MainWindow(demo=True, session_only=True)
    window.show_positioned()
    window.poll_now()
    qt_app.processEvents()
    yield window
    window.close()
    window.deleteLater()


def open_details(win, qt_app, row="claude", data=None):
    if data is not None:
        win._on_snapshot(row, data)
    dialog = win.open_quota_details(row, win.strip.cells[row])
    qt_app.processEvents()
    QTest.qWait(15)
    return dialog


@pytest.mark.parametrize("used,expected", [(0,"0%"), (100,"100%"), (10.125,"10,12%"),
                                          (.2,"0,2%"), (.001,"<0,01%"),
                                          (None,"não informado"), (float("nan"),"não informado")])
def test_precise_percent(used, expected):
    assert detailed_percent(used) == expected


def test_cards_keep_order_both_values_focus_and_brt(win, qt_app):
    windows = [quota("week", 91, 10080), quota("session", 10.125),
               quota("seven_day_sonnet", 2.5), quota("base_model_inference:primary", 50),
               quota("codex_bengalfox:primary", 4)]
    windows[1]["resets_at"] = "2026-10-12T02:40:00+00:00"
    details = open_details(win, qt_app, data=snapshot(windows))
    assert all(isinstance(row, QLabel) for row in details.rows)
    assert [row.text().split("\n")[0].split(" · ")[0] for row in details.rows] == [w["label"] for w in windows]
    assert "10,12% usado · 89,88% restante" in details.rows[1].text()
    assert "10.125" in details.rows[1].toolTip()
    assert "11/10/2026 23:40:00 BRT" in details.rows[1].text()
    assert sum("Destaque da faixa" in row.text() for row in details.rows) == 1
    assert "Destaque da faixa" in details.rows[1].text()
    assert "Cota específica de modelo" in details.rows[2].text()
    assert "Reserva · não é uso geral" in details.rows[3].text()
    assert "Spark · cota separada" in details.rows[4].text()
    assert "Consulta automática" in details.summary.text() and "BRT" in details.summary.text()


def test_timestamp_never_invents_timezone():
    assert timestamp("2026-10-12T02:40:00") == "data/hora não informada com fuso"
    assert timestamp(None) == "data/hora não informada com fuso"


def test_failure_marks_previous_values_and_preserves_focus(win, qt_app):
    details = open_details(win, qt_app, data=snapshot())
    details.copy_button.setFocus()
    row = details.rows[0]
    win._on_snapshot("claude", snapshot([], status="error", message="falha de consulta"))
    qt_app.processEvents()
    assert details.rows[0] is row
    assert "leitura anterior" in row.text()
    assert "não confirmados agora" in details.summary.text()
    assert QApplication.focusWidget() is details.copy_button
    win._querying.add("claude")
    details.refresh()
    assert "consultando" in details.summary.text()


def test_refresh_calls_owner_and_respects_existing_cooldown(win, qt_app, monkeypatch):
    details = open_details(win, qt_app)
    calls = []
    monkeypatch.setattr(win, "poll_now", lambda **_kw: calls.append("poll"))  # 261020 A8: force kwarg
    details.refresh_button.click()
    assert calls == ["poll"] and win._manual_refresh_locked
    assert not details.refresh_button.isEnabled()
    details.refresh_button.click()
    assert calls == ["poll"]
    win._unlock_manual_refresh()
    details.refresh()
    assert details.refresh_button.isEnabled()


def test_clipboard_plain_sanitized_and_real_keyboard_controls(win, qt_app):
    data = snapshot(source="https://example.test/usage?access_token=do-not-copy",
                    message="Bearer SECRET_VALUE token=PRIVATE sk-abcdefghi123456789 <b>plain</b>")
    details = open_details(win, qt_app, data=data)
    details.copy_button.setFocus()
    QTest.keyClick(details.copy_button, Qt.Key_Space)
    copied = QApplication.clipboard().text()
    assert all(value not in copied for value in ["SECRET_VALUE", "PRIVATE", "abcdefghi", "do-not-copy"])
    assert "<b>plain</b>" in copied and details.summary.textFormat() == Qt.PlainText
    assert "restante" in copied and "copiados" in details.feedback.text()
    assert "fetched_at:" not in copied
    details.technical_toggle.setFocus()
    QTest.keyClick(details.technical_toggle, Qt.Key_Space)
    details.copy_button.click()
    assert "fetched_at:" in QApplication.clipboard().text()


@pytest.mark.parametrize("row", ["claude", "codex", "codex_gpt2", "zai"])
def test_account_opens_only_allowlisted_official_page(win, qt_app, monkeypatch, row):
    calls = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: calls.append(url.toString()) or True)
    details = open_details(win, qt_app, row=row, data=snapshot(source="file:///C:/bad.cmd", message="cmd /c anything"))
    details.account_button.click()
    assert calls == [ACCOUNT_URLS[row]]
    assert not details.summary.openExternalLinks()
    if row == "codex_gpt2":
        assert "conta 2" in details.account_button.toolTip()


def test_extras_whitelist_missing_is_not_zero(win, qt_app, monkeypatch):
    data = snapshot()
    data["details"] = {"root": {"product_shares": [{"name":"Code", "percent":9.25}, {"name":"Absent"}],
                               "financial": [{"title":"Saldo", "amount":0, "currency":"BRL"},
                                             {"title":"Pendente", "status":"aguardando"},
                                             {"title":"Sem informação"}],
                               "secret":"DO_NOT_RENDER", "balance":1000}}
    monkeypatch.setattr(win.store, "display", lambda *a, **kw: data)
    details = open_details(win, qt_app)
    text = details.extras.text()
    assert "Consulta automática" in text and "Participação no consumo semanal" in text
    assert "9,25%" in text and "não é saldo" in text and "BRL 0" in text
    assert "Absent" not in text and "Sem informação" not in text and "DO_NOT_RENDER" not in text
    assert "Pendente · aguardando" in text
    del data["details"]
    details.refresh()
    assert details.extras.isHidden()


def test_observed_collapsed_separate_and_safe_source(win, qt_app, monkeypatch, tmp_path):
    image = tmp_path / "print.png"
    brand_pixmap("claude").save(str(image))
    data = {"source_files":["print.png", "../outside.png", "bad.cmd", "https://bad.test/image.png"]}
    monkeypatch.setattr(ui_quota_details, "observed_info", lambda row: data if row == "claude" else None)
    monkeypatch.setattr(ui_quota_details, "observed_sections",
                        lambda value: [("Print fornecido", "Captura sem horário informado · 90% restante")] if value else [])
    calls = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: calls.append(url) or True)
    details = open_details(win, qt_app, data=snapshot([quota(used=77)]))
    assert not details.observed_toggle.isChecked() and details.observed_body.isHidden()
    assert "77% usado" in details.rows[0].text() and details.extras.isHidden()
    details.copy_button.click()
    assert "90%" not in QApplication.clipboard().text()
    details.observed_toggle.click()
    assert details.observed_body.isVisible()
    buttons = details.observed_sources.findChildren(QPushButton)
    assert len(buttons) == 1
    buttons[0].click()
    assert calls[0].isLocalFile() and calls[0].toLocalFile().endswith("print.png")
    details.copy_button.click()
    assert "não atualizados automaticamente" in QApplication.clipboard().text()
    assert "Captura sem horário informado" in QApplication.clipboard().text()


@pytest.mark.parametrize("origin", [QPoint(0,0), QPoint(-1400,120), QPoint(2100,-200)])
def test_small_monitor_long_source_scroll_buttons_and_refresh(win, qt_app, monkeypatch, origin):
    area = QRect(origin.x(), origin.y(), 390, 640)
    class SmallScreen:
        def availableGeometry(self):
            return area
    anchor = win.strip.cells["claude"]
    monkeypatch.setattr(anchor, "screen", lambda: SmallScreen())
    data = snapshot([quota("Modelo longo " + str(i), i, 300+i) for i in range(30)],
                    source="origem-sem-espacos/" * 100, message="mensagem longa " * 100)
    details = open_details(win, qt_app, data=data)
    assert area.contains(details.frameGeometry())
    assert len(details.rows) == 30 and details.scroll.verticalScrollBar().maximum() > 0
    for button in (details.refresh_button, details.copy_button, details.account_button, details.close_button):
        assert details.rect().contains(QRect(button.mapTo(details, QPoint()), button.size()))
        assert button.isVisible() and button.toolTip() and button.focusPolicy() == Qt.StrongFocus
    bar = details.scroll.verticalScrollBar()
    bar.setValue(bar.maximum() // 2)
    value = bar.value()
    details.copy_button.setFocus()
    details.refresh()
    qt_app.processEvents()
    assert bar.value() == value and details.copy_button.hasFocus()
    assert details.summary.parent() is details.body


@pytest.mark.parametrize("row", ["codex", "codex_gpt2", "claude", "zai"])
def test_local_brands_have_pixels_and_account_two_is_explicit(qt_app, row):
    image = brand_pixmap(row, 20, 2)
    assert not image.isNull() and image.deviceIndependentSize().width() == 20
    assert brand_pixmap("codex").toImage() == brand_pixmap("codex_gpt2").toImage()
    assert provider_name("codex_gpt2", {}) == "Codex 2"
    assert brand_pixmap("missing").isNull()


@pytest.mark.parametrize("height", [40,72,112])
def test_strip_brand_name_and_percent_have_measured_room(win, qt_app, height):
    win.update_settings({"strip_height":height})
    win.poll_now()
    qt_app.processEvents()
    name, value, hint = win.strip.fonts()
    for cell in win.strip.cells.values():
        if not cell.isVisible():
            continue
        width = cell.width() - 22
        required = (win.strip.logo_size() + 5
                    + QFontMetrics(name).horizontalAdvance(provider_name(cell.row_id, win._canonical_labels))
                    + QFontMetrics(value).horizontalAdvance("100%") + 8)
        if win.strip.policy.inline:
            required += QFontMetrics(hint).horizontalAdvance(cell.meta) + 14
        assert width >= required
    assert win.height() == height


def test_render_inspection_artifacts(win, qt_app, monkeypatch, tmp_path):
    """Render isolated widgets for inspection; these are not native frame captures."""
    windows = [quota("session",10.125), quota("weekly_all",11,10080),
               quota("weekly_scoped:Fable",0,10080)]
    details = open_details(win, qt_app, data=snapshot(windows))
    assert details.grab().save(str(tmp_path / "details-550.png"))
    details.reject()
    anchor = win.strip.cells["claude"]
    class SmallScreen:
        def availableGeometry(self):
            return QRect(0,0,390,640)
    monkeypatch.setattr(anchor, "screen", lambda: SmallScreen())
    details = open_details(win, qt_app, data=snapshot(windows * 10,
                           source="https://service.example/usage/" + "path/" * 60,
                           message="Leitura automática de demonstração. " * 10))
    assert details.grab().save(str(tmp_path / "details-390.png"))
    details.reject()
    win.update_settings({"strip_height":72})
    win.poll_now()
    qt_app.processEvents()
    assert win.grab().save(str(tmp_path / "strip-72.png"))
    win.update_settings({"strip_height":40})
    qt_app.processEvents()
    assert win.grab().save(str(tmp_path / "strip-40.png"))
    print("RENDER_INSPECTION:", tmp_path)


def test_actual_provider_extras_contract_reaches_ui_and_stays_old_on_error(win, qt_app):
    from quota_details_data import claude_details, sanitize_details
    extras = sanitize_details(claude_details({
        "seven_day_breakdown":{"rows":[{"display_name":"Code","percent":9}],
                               "as_of":"2026-10-11T23:00:00Z"},
        "iguana_necktie":{"remaining_dollars":250,"limit_dollars":250,
                          "resets_at":"2026-11-05T07:59:00Z"}}))
    details = open_details(win, qt_app, data=snapshot(details=extras))
    text = details.extras.text()
    assert "USD 250" in text and "total 250" in text
    assert "05/11/2026 04:59:00 BRT" in text
    assert "Code: 9%" in text and "11/10/2026 20:00:00 BRT" in text
    assert "Créditos de uso · não informado" in text
    win._on_snapshot("claude", snapshot([],status="error"))
    qt_app.processEvents()
    assert "Consulta automática · leitura anterior" in details.extras.text()
    assert "USD 250" in details.extras.text()


@pytest.mark.parametrize("raw", ['{"access_token": "PRIVATE"}', "api_key='PRIVATE'", "client_secret=PRIVATE",
                                "Authorization: Bearer PRIVATE", "https://user:PRIVATE@example.test/?x=PRIVATE"])
def test_copy_sanitizer_handles_common_quoted_credentials(raw):
    assert "PRIVATE" not in safe_text(raw)
