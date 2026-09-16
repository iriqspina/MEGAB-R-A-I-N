"""Personal, local MEGABRAIN dashboard. Requires the existing quota-widget venv."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

APP = Path(__file__).resolve().parent
CENTRAL = APP.parents[1]
sys.path.insert(0, str(APP))

from dashboard_data import collect
from render_html import write_html


def refresh(project: Path, *, native: bool = False) -> Path:
    return write_html(collect(project), APP / "data" / "dashboard.html", native=native)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=CENTRAL)
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()
    html_path = refresh(args.project)
    if args.html_only:
        print(html_path)
        return 0
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QDesktopServices, QIcon
    from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView

    class LocalPage(QWebEnginePage):
        def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
            if navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
                if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".md":
                    QDesktopServices.openUrl(url)
                    return False
                if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".json":
                    QDesktopServices.openUrl(url)
                    return False
            return url.scheme() in {"file", "data", "about"}

    class Window(QMainWindow):
        def __init__(self, project: Path):
            super().__init__()
            self.project = project.resolve()
            self.setWindowTitle("MEGABRAIN · visão pessoal")
            icon = APP / "assets" / "megabrain-cerebro-rosa.ico"
            if icon.exists():
                self.setWindowIcon(QIcon(str(icon)))
            self.resize(1050, 760)
            self.setStyleSheet("""
                QMainWindow, QWidget#shell { background: #12121F; }
                QLabel { color: #A3A1BD; font: 12px 'Segoe UI'; }
                QPushButton { color: #FFFFFF; background: #1F1F30;
                    border: 1px solid #5B4A7A; border-radius: 10px;
                    padding: 9px 12px; font: bold 12px 'Segoe UI'; min-height: 22px; }
                QPushButton:hover { background: #2C2540; }
                QPushButton:focus { border: 2px solid #CE82FF; }
            """)
            root = QWidget(self)
            root.setObjectName("shell")
            layout = QVBoxLayout(root)
            layout.setContentsMargins(0, 0, 0, 0)
            bar = QHBoxLayout()
            bar.setContentsMargins(16, 10, 16, 0)
            self.label = QLabel()
            self.label.setWordWrap(True)
            self.label.setMinimumWidth(0)
            choose = QPushButton("Escolher projeto")
            refresh_button = QPushButton("Atualizar")
            choose.clicked.connect(self.choose_project)
            refresh_button.clicked.connect(self.reload)
            bar.addWidget(self.label, 1)
            bar.addWidget(choose)
            bar.addWidget(refresh_button)
            layout.addLayout(bar)
            self.browser = QWebEngineView()
            # An unnamed profile keeps browsing data in memory, with no account or tracking.
            self.profile = QWebEngineProfile(self.browser)
            self.page = LocalPage(self.profile, self.browser)
            self.browser.setPage(self.page)
            self.browser.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
            self.last_html = None
            layout.addWidget(self.browser, 1)
            self.setCentralWidget(root)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.reload)
            self.timer.start(20_000)
            self.reload()

        def choose_project(self):
            selected = QFileDialog.getExistingDirectory(self, "Projeto acompanhado pelo MEGABRAIN", str(self.project))
            if selected:
                self.project = Path(selected).resolve()
                self.reload()

        def reload(self):
            path = refresh(self.project, native=True)
            content = path.read_text(encoding="utf-8")
            # Keep keyboard focus and scroll position on unchanged timer refreshes.
            if content != self.last_html:
                self.browser.load(QUrl.fromLocalFile(str(path)))
                self.last_html = content
            self.label.setText("Leitura local · a cada 20 s")
            self.label.setToolTip(str(self.project))

    app = QApplication.instance() or QApplication([])
    window = Window(args.project)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
