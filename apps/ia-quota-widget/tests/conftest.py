import sys
import socket
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


@pytest.fixture(autouse=True)
def isolated_app_io(tmp_path, monkeypatch):
    """No test may write the running app/central data or contact the network."""
    from widget_app import paths
    from PySide6.QtCore import QCoreApplication, QEvent
    from widget_app.main_window import MainWindow

    for name, value in {
        'DATA_DIR': tmp_path, 'SETTINGS_PATH': tmp_path / 'settings.json',
        'CACHE_PATH': tmp_path / 'cache.json', 'BUDGET_STATUS_PATH': tmp_path / 'budget.json',
        'MCP_HEALTH_PATH': tmp_path / 'mcp.json', 'CENTRAL_DIR': tmp_path,
    }.items():
        monkeypatch.setattr(paths, name, value)
    monkeypatch.setattr(MainWindow, '_request_mcp_health', lambda self: None)

    def no_network(*args, **kwargs):
        raise AssertionError('Network is forbidden in the widget test suite')

    monkeypatch.setattr(socket.socket, 'connect', no_network)
    monkeypatch.setattr(socket, 'create_connection', no_network)
    yield
    # Deliver deferred destruction BEFORE path monkeypatches are restored.
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    if QApplication.instance():
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget._session_only = True
                for timer in widget.findChildren(QTimer):
                    timer.stop()
                widget.close()
                widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


@pytest.fixture(scope="session")
def qt_app():
    # Um unico QApplication pra sessao inteira de teste. QCoreApplication (sem
    # GUI) e QApplication nao podem coexistir no mesmo processo — dois arquivos
    # de teste criando singletons diferentes (um QCoreApplication, outro
    # QApplication) travava o processo no meio da suite. QApplication cobre os
    # dois usos (sinais/threadpool headless E QWidget de verdade).
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase

    app = QApplication.instance() or QApplication([])
    # Offscreen on Windows does not enumerate system fonts automatically.
    for name in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf', 'consolab.ttf', 'arial.ttf'):
        path = Path('C:/Windows/Fonts') / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    yield app
