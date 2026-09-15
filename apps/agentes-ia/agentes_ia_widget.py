#!/usr/bin/env python3
# Widget "Agentes IA" (260915, Fase 2) — família do Cotas IA.
# Casca PySide6 translúcida hospedando o board Agent Flow (localhost:3001)
# via QWebEngineView com fundo transparente. Sem fundo por padrão; névoa branca
# opcional (gradiente radial 100→0%) com opacidade ajustável. Frameless,
# arrastável pelo cabeçalho, redimensionável pela alça, sempre-no-topo opcional.
# Fechar encerra o server do board (decisão 6: adota se já rodando, fecha ao sair).
# Reversão: apagar esta pasta; settings em ~/.agentes-ia/settings.json.
import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, QTimer, QUrl
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMenu, QSizeGrip, QSlider, QVBoxLayout, QWidget,
)

APP_NAME = "Agentes IA"
BOARD_URL = "http://localhost:3001"
SINGLETON_KEY = "megabrain-agentes-ia"
SETTINGS_PATH = Path.home() / ".agentes-ia" / "settings.json"
MB_BOARD = Path(r"<MEGABRAIN_ROOT>\bin\mb-board.ps1")
APP_DIST = Path(os.environ.get("LOCALAPPDATA", "")) / (
    "npm-cache/_npx/23b47ad77b53d45f/node_modules/agent-flow-app/dist/app.js")
ROOT_PROJETOS = r"S:\projetos multi i.a"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def load_settings():
    padrao = {"x": 160, "y": 140, "w": 1080, "h": 700,
              "nevoa": 30, "topmost": True}
    try:
        padrao.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    return padrao


def save_settings(s):
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def server_no_ar():
    c = socket.socket()
    c.settimeout(0.6)
    try:
        return c.connect_ex(("127.0.0.1", 3001)) == 0
    finally:
        c.close()


def subir_server():
    if server_no_ar():
        return False  # já rodando: adota (decisão 6)
    if APP_DIST.exists():
        subprocess.Popen(["node", str(APP_DIST)], cwd=ROOT_PROJETOS,
                         creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(MB_BOARD)], creationflags=CREATE_NO_WINDOW)
    for _ in range(45):
        if server_no_ar():
            break
        time.sleep(1)
    return True


def parar_server():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(MB_BOARD), "-Parar"],
                   creationflags=CREATE_NO_WINDOW)


class NvoaLayer(QWidget):
    """Névoa branca: gradiente radial centro→borda (100%→0% da opacidade)."""
    def __init__(self, parent):
        super().__init__(parent)
        self.opacity_pct = 30
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        r = self.rect()
        g = QRadialGradient(r.center(), max(r.width(), r.height()) / 1.4)
        a = max(0, min(100, self.opacity_pct))
        g.setColorAt(0.0, QColor(255, 255, 255, int(255 * a / 100)))
        g.setColorAt(0.55, QColor(255, 255, 255, int(255 * a / 100 * 0.55)))
        g.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(r, g)


class PaginaTransparente(QWebEnginePage):
    def backgroundColor(self):
        return QColor(Qt.transparent)


class WidgetIA(QWidget):
    """Janela widget: frameless, translúcida, arrastável, redimensionável."""
    def __init__(self, settings):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.settings = settings
        self._drag = None
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(420, 340)
        self.resize(settings["w"], settings["h"])
        self.move(settings["x"], settings["y"])
        self.set_window_topmost(settings["topmost"])

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # cabeçalho fino: título + névoa + dica de menu (área arrastável)
        self.header = QWidget(self)
        self.header.setFixedHeight(26)
        self.header.setAttribute(Qt.WA_TranslucentBackground)
        h = QHBoxLayout(self.header)
        h.setContentsMargins(10, 2, 10, 2)
        titulo = QLabel(APP_NAME)
        titulo.setStyleSheet("color:#9fd8ff; background:transparent; font-weight:600;")
        h.addWidget(titulo)
        h.addStretch(1)
        h.addWidget(QLabel("névoa"))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(settings["nevoa"])
        self.slider.setFixedWidth(110)
        self.slider.valueChanged.connect(self._nevoa_mudou)
        h.addWidget(self.slider)
        raiz.addWidget(self.header)

        # board embutido com fundo transparente
        self.view = QWebEngineView()
        self.page = PaginaTransparente(self.view)
        self.page.setBackgroundColor(QColor(Qt.transparent))
        self.view.setPage(self.page)
        self.view.settings().setAttribute(self.view.settings().WebAttribute.ShowScrollBars, False)
        self.view.load(QUrl(BOARD_URL))
        raiz.addWidget(self.view, 1)

        # névoa por cima (não intercepta mouse) + alça de redimensionar
        self.nvoa = NvoaLayer(self)
        self.nvoa.opacity_pct = settings["nevoa"]
        self.nvoa.raise_()
        self.grip = QSizeGrip(self)
        self.grip.setFixedSize(16, 16)
        self.grip.raise_()

        self.header.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._menu)

    # --- layout da névoa e da alça por cima do conteúdo
    def resizeEvent(self, ev):
        if hasattr(self, "nvoa"):
            self.nvoa.setGeometry(self.rect())
            self.grip.move(self.width() - 18, self.height() - 18)
        super().resizeEvent(ev)

    def _nevoa_mudou(self, v):
        self.nvoa.opacity_pct = v
        self.nvoa.update()
        self.settings["nevoa"] = v
        save_settings(self.settings)

    def _menu(self, pos):
        m = QMenu(self)
        a_top = m.addAction("Sempre no topo")
        a_top.setCheckable(True)
        a_top.setChecked(self.settings["topmost"])
        a_rec = m.addAction("Recenter (salvar posição/tamanho)")
        a_parar = m.addAction("Parar server do board")
        escolha = m.exec(self.header.mapToGlobal(pos))
        if escolha is a_top:
            self.set_window_topmost(a_top.isChecked())
            self.settings["topmost"] = a_top.isChecked()
            save_settings(self.settings)
        elif escolha is a_rec:
            self.settings.update(x=self.x(), y=self.y(), w=self.width(), h=self.height())
            save_settings(self.settings)
        elif escolha is a_parar:
            parar_server()

    def set_window_topmost(self, on):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    # --- arrastar pelo cabeçalho
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and self.header.underMouse():
            self._drag = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._drag is not None and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._drag = None
        self.settings.update(x=self.x(), y=self.y())
        save_settings(self.settings)
        super().mouseReleaseEvent(ev)

    def closeEvent(self, ev):
        self.settings.update(x=self.x(), y=self.y(), w=self.width(), h=self.height())
        save_settings(self.settings)
        parar_server()  # decisão 6: fechar o widget mata o server (adotado ou próprio)
        super().closeEvent(ev)


def main():
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--screenshot", metavar="PATH", help="grava um PNG e sai")
    ap.add_argument("--screenshot-delay-ms", type=int, default=2500)
    ap.add_argument("--skip-singleton-guard", action="store_true")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    guard_ok = args.skip_singleton_guard
    server = None
    if not guard_ok:
        probe = QLocalSocket()
        probe.connectToServer(SINGLETON_KEY)
        guard_ok = not probe.waitForConnected(150)
        probe.close()
        if guard_ok:
            QLocalServer.removeServer(SINGLETON_KEY)
            server = QLocalServer()
            server.listen(SINGLETON_KEY)

    subir_server()
    w = WidgetIA(load_settings())
    w.show()

    if args.screenshot:
        def capturar():
            w.grab().save(args.screenshot, "PNG")
            app.quit()
        QTimer.singleShot(args.screenshot_delay_ms, capturar)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
