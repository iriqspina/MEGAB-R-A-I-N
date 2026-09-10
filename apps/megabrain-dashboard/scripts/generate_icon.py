"""Generate a multi-size white square / pink brain icon without external assets."""
import struct
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP.parents[1] / "ia-quota-widget"))
from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath


def png(image):
    buffer = QBuffer(); buffer.open(QIODevice.WriteOnly); image.save(buffer, "PNG")
    return bytes(buffer.data())


def image(size):
    canvas = QImage(size, size, QImage.Format_ARGB32_Premultiplied); canvas.fill(Qt.transparent)
    p = QPainter(canvas); p.setRenderHint(QPainter.Antialiasing)
    m = max(1, round(size * .06)); p.setBrush(QColor("#FFFFFF")); p.setPen(QColor("#F5D7E5")); p.drawRoundedRect(m, m, size-2*m, size-2*m, size*.23, size*.23)
    p.setBrush(QColor("#EF3D8F")); p.setPen(Qt.NoPen)
    # compact brain: paired lobes + lower bridge, legible at 16px
    s=size; path=QPainterPath(); path.addEllipse(s*.21,s*.25,s*.28,s*.30); path.addEllipse(s*.51,s*.25,s*.28,s*.30); path.addEllipse(s*.29,s*.46,s*.42,s*.24); p.drawPath(path)
    p.setPen(QColor("#FFFFFF")); p.drawLine(int(s*.50),int(s*.30),int(s*.50),int(s*.62)); p.drawLine(int(s*.34),int(s*.45),int(s*.43),int(s*.45)); p.drawLine(int(s*.57),int(s*.45),int(s*.66),int(s*.45)); p.end(); return canvas


def main():
    QGuiApplication([]); out=APP/'assets'; out.mkdir(parents=True,exist_ok=True); sizes=[16,24,32,48,64,128,256]; images=[image(s) for s in sizes]; offset=6+16*len(images); entries=[]; data=[]
    for img in images:
        raw=png(img); side=img.width() if img.width()<256 else 0; entries.append(struct.pack('<BBBBHHII',side,side,0,0,1,32,len(raw),offset));data.append(raw);offset+=len(raw)
    (out/'megabrain-cerebro-rosa.ico').write_bytes(struct.pack('<HHH',0,1,len(images))+b''.join(entries)+b''.join(data))
    images[-1].save(str(out/'megabrain-cerebro-rosa.png'),'PNG')

if __name__ == '__main__': main()
