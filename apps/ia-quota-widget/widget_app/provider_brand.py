"""Local official artwork, unchanged; brand identity is never a status signal."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "brands"
BRANDS = {"codex": "openai-black.svg", "codex_gpt2": "openai-black.svg",
          "spark": "openai-black.svg", "claude": "claude.png", "zai": "zai.svg"}
ACCOUNT_URLS = {
    "claude": "https://claude.ai/settings/usage",
    "codex": "https://chatgpt.com/codex/settings/usage",
    "codex_gpt2": "https://chatgpt.com/codex/settings/usage",
    "spark": "https://chatgpt.com/codex/settings/usage",
    "zai": "https://z.ai/manage-apikey/coding-plan/personal/usage",
}


def provider_name(row_id, labels):
    # Keep the account distinction visible even on a compact strip.
    return "Codex 2" if row_id == "codex_gpt2" else labels.get(row_id, row_id)


@lru_cache(maxsize=32)
def brand_pixmap(row_id, size=20, dpr=1.0):
    """Neutral plate preserves artwork contrast without recolouring the logo."""
    path = ASSETS / BRANDS.get(row_id, "")
    if not path.is_file():
        return QPixmap()
    dpr = max(1.0, float(dpr))
    pixmap = QPixmap(round(size * dpr), round(size * dpr))
    pixmap.setDevicePixelRatio(dpr)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#f5f5f5"))
    painter.drawRoundedRect(QRectF(0, 0, size, size), 3, 3)
    target = QRectF(2, 2, max(1, size - 4), max(1, size - 4))
    valid = True
    if path.suffix == ".svg":
        renderer = QSvgRenderer(str(path))
        valid = renderer.isValid()
        if valid:
            original = renderer.defaultSize()
            fitted = original.scaled(target.size().toSize(), Qt.KeepAspectRatio)
            rect = QRectF(0, 0, fitted.width(), fitted.height())
            rect.moveCenter(target.center())
            renderer.render(painter, rect)
    else:
        original = QPixmap(str(path))
        valid = not original.isNull()
        if valid:
            fitted = original.size().scaled(target.size().toSize(), Qt.KeepAspectRatio)
            rect = QRectF(0, 0, fitted.width(), fitted.height())
            rect.moveCenter(target.center())
            painter.drawPixmap(rect, original, QRectF(original.rect()))
    painter.end()
    return pixmap if valid else QPixmap()


def brand_icon(row_id):
    return QIcon(brand_pixmap(row_id, 24))
