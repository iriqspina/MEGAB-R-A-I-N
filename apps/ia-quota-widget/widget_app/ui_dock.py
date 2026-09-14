"""Dock lateral de bolinhas (260914, pedido do <USUARIO>).

Provedor escondido vira uma bolinha num slot do dock; arrastar a bolinha de
volta pra lista devolve o card. Slots vazios são só círculos pontilhados —
nenhum texto "coloque aqui", o espaço vazio já conta a história.
"""

from math import sin

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import theme, ui_motion

DOCK_WIDTH = 30
SLOT_PITCH = 27
SLOT_RADIUS = 9
SLOT_TOP = 14
MIN_SLOTS = 3


def _vendor_color(row_id: str) -> str:
    return theme.PROVIDER_DOT_COLORS.get(row_id, "#d7dde5")


def _vendor_letter(row_id: str) -> str:
    label = theme.PROVIDER_LABELS.get(row_id, row_id)
    return (label[:1] or "?").upper()


class DockRail(QWidget):
    """Coluna de slots; cada slot é uma bolinha de provedor ou um vazio."""

    def __init__(self, parent, drag_hook):
        super().__init__(parent)
        self._hook = drag_hook
        self._hidden: list[str] = []
        self._palette = theme.palette_for(theme.DEFAULT_SURFACE_PRESET)
        self._hint_pos: QPointF | None = None
        self._accepting = False
        self._drop_row: str | None = None
        self.setMinimumWidth(DOCK_WIDTH)
        self.setMouseTracking(True)
        self.setToolTip("Bolinhas guardadas: arraste de volta pra lista · pelo teclado: Opções → Provedores")

    def apply_theme(self, palette: dict):
        self._palette = palette
        self.update()

    def set_hidden(self, row_ids: list[str]):
        first_new = row_ids and (not self._hidden or self._hidden[0] != row_ids[0])
        self._hidden = list(row_ids)
        self.update()
        if first_new:
            self._bounce_slot(0)

    def _bounce_slot(self, index: int):
        # Bolinha que acabou de cair no dock quica (overshoot elástico).
        self.setProperty("bounce", 1.6)

        def settle(v):
            self.setProperty("bounce", float(v))
            self.update()

        ui_motion.animate(self, 1.6, 1.0, 380, settle)

    def slot_center(self, index: int) -> QPointF:
        return QPointF(DOCK_WIDTH / 2, SLOT_TOP + SLOT_RADIUS + index * SLOT_PITCH)

    def _slot_count(self) -> int:
        return max(len(self._hidden), MIN_SLOTS)

    def ball_at(self, pos: QPointF) -> str | None:
        for index, row_id in enumerate(self._hidden):
            if (pos - self.slot_center(index)).manhattanLength() <= SLOT_RADIUS + 4:
                return row_id
        return None

    def set_drop_hint(self, global_pos=None, accepting: bool = False):
        self._accepting = accepting and global_pos is not None
        self._hint_pos = self.mapFromGlobal(global_pos) if global_pos is not None else None
        self.update()

    def contains_global(self, global_pos) -> bool:
        return self.rect().contains(self.mapFromGlobal(global_pos))

    # ------------------------------------------------------------ pintura

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounce = float(self.property("bounce") or 1.0)
        hint_index = None
        if self._accepting and self._hint_pos is not None:
            hint_index = max(0, int((self._hint_pos.y() - SLOT_TOP) // SLOT_PITCH))
        secondary = QColor(self._palette["text_secondary"])
        for index in range(self._slot_count()):
            center = self.slot_center(index)
            if index < len(self._hidden):
                row_id = self._hidden[index]
                radius = SLOT_RADIUS * (bounce if index == 0 else 1.0)
                painter.setPen(QColor(*self._palette.get("dot_ring", (255, 255, 255, 45))))
                painter.setBrush(QColor(_vendor_color(row_id)))
                painter.drawEllipse(center, radius, radius)
                font = QFont(theme.FONT_FAMILY)
                font.setPixelSize(max(8, round(radius)))
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QColor(20, 22, 25))
                painter.drawText(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2),
                                 Qt.AlignCenter, _vendor_letter(row_id))
            else:
                pen = QPen(secondary)
                pen.setStyle(Qt.DotLine)
                pen.setWidthF(1.2)
                if self._accepting and index == hint_index:
                    pen.setStyle(Qt.SolidLine)
                    pen.setWidthF(2.0)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(center, SLOT_RADIUS, SLOT_RADIUS)
        painter.end()

    # ------------------------------------------------------------ arraste da bolinha

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            row_id = self.ball_at(event.position())
            if row_id is not None and self._hook is not None:
                self._drop_row = row_id
                self._hook(row_id, "press", event.globalPosition().toPoint(), "dock")
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drop_row and self._hook is not None:
            self._hook(self._drop_row, "move", event.globalPosition().toPoint(), "dock")
            event.accept()
            return
        row_id = self.ball_at(event.position())
        if row_id is not None:
            self.setToolTip(f"{theme.PROVIDER_LABELS.get(row_id, row_id)} — arraste pra voltar pra lista")
        else:
            self.setToolTip("Bolinhas guardadas: arraste de volta pra lista · pelo teclado: Opções → Provedores")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drop_row and self._hook is not None:
            row_id, self._drop_row = self._drop_row, None
            self._hook(row_id, "release", event.globalPosition().toPoint(), "dock")
            event.accept()
            return
        super().mouseReleaseEvent(event)


class DragBall(QWidget):
    """A bolinha fantasma que segue o cursor durante o arraste, balançando
    como desenho animado de perseguição."""

    SIZE = 34

    def __init__(self, window: QWidget, row_id: str):
        super().__init__(window)
        self._row_id = row_id
        self._color = _vendor_color(row_id)
        self._letter = _vendor_letter(row_id)
        self._t = 0
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)
        self.show()
        self.raise_()

    def _tick(self):
        self._t += 1
        self.update()

    def follow(self, global_pos):
        local = self.parentWidget().mapFromGlobal(global_pos)
        self.move(local.x() - self.SIZE // 2, local.y() - self.SIZE // 2)

    def dismiss(self):
        self._timer.stop()
        self.hide()
        self.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.SIZE / 2, self.SIZE / 2)
        # Balanço senoidal + achatamento na direção do movimento: o "squoing"
        # que dá vida de desenho animado sem virar enjoo.
        angle = 12 * sin(self._t * 0.28)
        squash = 1.0 + 0.08 * sin(self._t * 0.28 + 1.5)
        painter.rotate(angle)
        painter.scale(squash, 2.0 - squash)
        radius = self.SIZE / 2 - 3
        painter.setPen(QColor(255, 255, 255, 70))
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(int(-radius), int(-radius), int(radius * 2), int(radius * 2))
        font = QFont(theme.FONT_FAMILY)
        font.setPixelSize(int(radius))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(20, 22, 25))
        painter.drawText(int(-radius), int(-radius), int(radius * 2), int(radius * 2), Qt.AlignCenter, self._letter)
        painter.end()
