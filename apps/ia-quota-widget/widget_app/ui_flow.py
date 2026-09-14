"""Layout de fluxo pros cards (260914, pedido do <USUARIO>).

Sem barra de rolagem: janela larga → cards reorganizam em colunas; estreita →
uma coluna. Nada é escalado aqui — cada card só muda de posição; tamanho vem
das opções (fonte/escala das Configurações). Todos os cards de uma fileira
recebem a largura do mais largo, pra formar colunas alinhadas.
"""

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin: int = 0, spacing: int = 8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items: list = []

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:
        return True

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, apply=True)

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), apply=False)

    def _uniform_width(self) -> int:
        widths = [item.sizeHint().width() for item in self._items if item.widget() is not None]
        return max(widths) if widths else 0

    def _do_layout(self, rect: QRect, apply: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        uniform = self._uniform_width()
        if uniform <= 0 or uniform > effective.width():
            uniform = effective.width()
        x, y = effective.x(), effective.y()
        line_height = 0
        for item in self._items:
            height = item.sizeHint().height()
            next_x = x + uniform + self._spacing
            if next_x - self._spacing > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y += line_height + self._spacing
                next_x = x + uniform + self._spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), QSize(uniform, height)))
            x = next_x
            line_height = max(line_height, height)
        return y + line_height - rect.y() + margins.bottom()
