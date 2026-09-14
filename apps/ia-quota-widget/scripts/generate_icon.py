"""Gera assets/cotas-ia.ico (multi-resolucao) e assets/cotas-ia.png (256px).

Desenho: quadrado com cantos arredondados na cor do preset Carvao, com barras
verticais de altura diferente nas cores de identidade dos providers (o mesmo
"quanto sobrou" reduzido ao minimo). Sem texto/sigla: letra nao sobrevive a
16px. Abaixo de 32px usa so 2 barras (Codex + Claude, os visiveis por
padrao) porque a 3a vira borrao nesse tamanho — checado visualmente antes de
fechar o desenho, nao só por calculo.

O QImageWriter do Qt para .ico so escreve UM frame por arquivo (testado: a
segunda chamada de write() nao acumula, o reader devolve imageCount=1) —
entao o container ICO multi-resolucao e' montado a mao aqui: cada tamanho
vira um PNG em memoria, e os PNGs entram como frames num ICONDIR (formato
PNG-in-ICO, suportado desde o Windows Vista, e o que o proprio Explorer usa
pros icones grandes de hoje).
"""

import struct
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath

from widget_app import theme
from widget_app.contrast import hex_to_rgb

SIZES = [16, 24, 32, 48, 64, 128, 256]
ASSETS_DIR = APP_ROOT / "assets"

BG = theme.SURFACE_PRESETS["carvao"]["bg"]
BAR_COLORS_3 = [
    theme.PROVIDER_DOT_COLORS["codex"],
    theme.PROVIDER_DOT_COLORS["claude"],
    theme.PROVIDER_DOT_COLORS["gemini_cli"],
]
BAR_COLORS_2 = [theme.PROVIDER_DOT_COLORS["codex"], theme.PROVIDER_DOT_COLORS["claude"]]
BAR_HEIGHTS_FRACTIONS_3 = [0.45, 0.68, 0.92]
BAR_HEIGHTS_FRACTIONS_2 = [0.5, 0.88]


def render_icon(size: int) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)

    margin = max(1, round(size * 0.06))
    radius = size * 0.24
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    painter.fillPath(path, QColor(*hex_to_rgb(BG)))

    use_two = size < 32
    colors = BAR_COLORS_2 if use_two else BAR_COLORS_3
    fractions = BAR_HEIGHTS_FRACTIONS_2 if use_two else BAR_HEIGHTS_FRACTIONS_3

    inner = rect.adjusted(rect.width() * 0.20, 0, -rect.width() * 0.20, 0)
    bar_count = len(colors)
    gap = inner.width() * 0.18
    bar_width = (inner.width() - gap * (bar_count - 1)) / bar_count
    bar_radius = max(0.5, bar_width * 0.35)
    baseline = rect.bottom() - rect.height() * 0.16
    max_bar_height = rect.height() * 0.62

    for i, (color_hex, frac) in enumerate(zip(colors, fractions)):
        x = inner.left() + i * (bar_width + gap)
        h = max_bar_height * frac
        bar_rect = QRectF(x, baseline - h, bar_width, h)
        bar_path = QPainterPath()
        bar_path.addRoundedRect(bar_rect, bar_radius, bar_radius)
        painter.fillPath(bar_path, QColor(*hex_to_rgb(color_hex)))

    painter.end()
    return image


def image_to_png_bytes(image: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    image.save(buf, "PNG")
    data = bytes(buf.data())
    buf.close()
    return data


def write_ico(images: list[QImage], out_path: Path) -> None:
    entries = []
    payloads = []
    offset = 6 + 16 * len(images)
    for img in images:
        png_bytes = image_to_png_bytes(img)
        w = img.width() if img.width() < 256 else 0
        h = img.height() if img.height() < 256 else 0
        entries.append(
            struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_bytes), offset)
        )
        payloads.append(png_bytes)
        offset += len(png_bytes)

    header = struct.pack("<HHH", 0, 1, len(images))
    out_path.write_bytes(header + b"".join(entries) + b"".join(payloads))


def main():
    QGuiApplication.instance() or QGuiApplication([])
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    images = [render_icon(s) for s in SIZES]
    ico_path = ASSETS_DIR / "cotas-ia.ico"
    write_ico(images, ico_path)

    png_256 = next(img for img in images if img.width() == 256)
    png_path = ASSETS_DIR / "cotas-ia.png"
    png_256.save(str(png_path), "PNG")

    print(f"ICO: {ico_path} ({ico_path.stat().st_size} bytes, {len(SIZES)} tamanhos: {SIZES})")
    print(f"PNG: {png_path} ({png_path.stat().st_size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
