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


def refresh(project: Path) -> Path:
    return write_html(collect(project), APP / "data" / "dashboard.html")


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
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTextBrowser, QVBoxLayout, QWidget

    class Window(QMainWindow):
        def __init__(self, project: Path):
            super().__init__()
            self.project = project.resolve()
            self.setWindowTitle("MEGABRAIN · visão pessoal")
            icon = APP / "assets" / "megabrain-cerebro-rosa.ico"
            if icon.exists():
                self.setWindowIcon(QIcon(str(icon)))
            self.resize(1050, 760)
            root = QWidget(self)
            layout = QVBoxLayout(root)
            layout.setContentsMargins(12, 12, 12, 12)
            bar = QHBoxLayout()
            self.label = QLabel()
            choose = QPushButton("Escolher projeto")
            refresh_button = QPushButton("Atualizar")
            choose.clicked.connect(self.choose_project)
            refresh_button.clicked.connect(self.reload)
            bar.addWidget(self.label, 1)
            bar.addWidget(choose)
            bar.addWidget(refresh_button)
            layout.addLayout(bar)
            self.browser = QTextBrowser()
            self.browser.setOpenExternalLinks(True)
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
            path = refresh(self.project)
            self.browser.setSource(QUrl.fromLocalFile(str(path)))
            self.label.setText(f"Acompanhando: {self.project}")

    app = QApplication.instance() or QApplication([])
    window = Window(args.project)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
