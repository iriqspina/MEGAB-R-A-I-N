"""Reproducible isolated native capture. Never imports or polls real accounts.

Run from app: .venv/Scripts/python.exe tests/render_trilho_demo.py <evidence-dir>
QT_QPA_PLATFORM=offscreen and QT_SCALE_FACTOR can be selected by the caller.
"""
import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

from PySide6.QtCore import QCoreApplication, QEvent, QRect, Qt, QTimer
from PySide6.QtGui import QFontDatabase, QFontInfo
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from widget_app import paths, persistence, theme
from widget_app.main_window import MainWindow


def main():
    output = Path(sys.argv[1]).resolve()
    allowed = APP.parent.parent / 'evidence' / '261011_cotas-design' / 'implementacao'
    if not output.is_relative_to(allowed.resolve()):
        raise ValueError('Capture output must stay in the authorized implementation evidence directory')
    output.mkdir(parents=True, exist_ok=True)
    data = output / 'isolated-data'
    paths.DATA_DIR = data
    paths.SETTINGS_PATH = data / 'settings.json'
    paths.CACHE_PATH = data / 'last_snapshot.json'
    paths.BUDGET_STATUS_PATH = data / 'budget.json'
    paths.MCP_HEALTH_PATH = data / 'mcp.json'
    paths.CENTRAL_DIR = data

    def forbidden(*args, **kwargs):
        raise AssertionError('No network in DEMO captures')

    socket.socket.connect = forbidden
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    loaded = []
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf', 'consolab.ttf', 'arial.ttf'):
        source = Path('C:/Windows/Fonts') / name
        if source.exists():
            index = QFontDatabase.addApplicationFont(str(source))
            loaded.append({'file': str(source), 'loaded': index >= 0})
    settings = persistence.Settings(visual_mode='trilho', strip_height=72, strip_width=800,
                                    visible_providers={pid: pid in ('codex', 'codex_gpt2', 'claude', 'zai')
                                                       for pid in theme.PROVIDER_LABELS})
    persistence.save_settings(settings)
    win = MainWindow(demo=True, session_only=True)
    if app.platformName() == 'offscreen':
        # Synthetic logical desktop: allows 800 DIP at 200% even though Qt's
        # default offscreen screen is only 800 physical pixels wide.
        win._available_rect = lambda: QRect(0, 0, 1920, 1080)
    win.show_positioned()
    win.poll_now()
    QTest.qWait(180)
    manifest = {'demo': True, 'fetched_at': datetime.now(timezone.utc).isoformat(),
                'platform': app.platformName(), 'font_files': loaded,
                'synthetic_desktop': app.platformName() == 'offscreen',
                'font': QFontInfo(win.strip.fonts()[0]).family(),
                'flags_qt_tool': win.windowType() == Qt.Tool, 'captures': []}

    def capture(name):
        app.processEvents()
        QTest.qWait(40)
        pixmap = win.grab()
        target = output / (name + '.png')
        assert pixmap.save(str(target), 'PNG')
        record = {'file': target.name, 'logical': [win.width(), win.height()],
                  'physical': [pixmap.width(), pixmap.height()], 'dpr': pixmap.devicePixelRatio(),
                  'visible': [row for row in win.strip.order if win.strip.cells[row].isVisible()],
                  'counter': win.strip.counter.text(), 'inline': win.strip.policy.inline}
        manifest['captures'].append(record)

    capture('trilho-800x72-demo')
    assert [win.width(), win.height()] == [800, 72]
    assert win.strip.policy.capacity == 4
    anchor = win.strip.cells['claude']
    anchor.setFocus()
    QTest.keyClick(anchor, Qt.Key_Return)
    app.processEvents()
    details = win._quota_details
    assert details.isVisible()
    assert details.grab().save(str(output / 'detalhes-demo.png'), 'PNG')
    QTest.keyClick(details, Qt.Key_Escape)
    app.processEvents()
    manifest['details_keyboard'] = {'enter_opened': True, 'escape_closed': not details.isVisible(),
                                    'focus_returned': anchor.hasFocus(), 'strip_height': win.height()}
    for height in (40, 112):
        win.update_settings({'strip_height': height})
        capture(f'trilho-800x{height}-demo')
    win.update_settings({'strip_height': 72, 'strip_width': 360})
    capture('trilho-360x72-demo')
    win.update_settings({'strip_width': 800, 'surface_preset': 'papel'})
    capture('trilho-800x72-papel-demo')
    win.update_settings({'surface_preset': 'carvao', 'size_name': 22, 'size_value': 36, 'size_hint': 19})
    capture('trilho-800x72-fonte-maior-demo')
    win.update_settings({'size_name': 12, 'size_value': 19, 'size_hint': 11})
    win._on_snapshot('claude', {'status': 'ok', 'source': 'DEMO · teste de estados',
                              'fetched_at': datetime.now(timezone.utc).isoformat(),
                              'windows': [dict(id='week', label='Semana', duration_minutes=10080, used_percent=100, resets_at=None),
                                          dict(id='five', label='5 h', duration_minutes=300, used_percent=None, resets_at=None)]})
    capture('trilho-alerta-sem-medicao-demo')
    for timer in win.findChildren(QTimer):
        timer.stop()
    win.close()
    win.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    (output / 'capturas.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'captures': len(manifest['captures']), 'font': manifest['font']}))


if __name__ == '__main__':
    main()
