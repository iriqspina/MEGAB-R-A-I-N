from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QPoint, QRect, QSize, Qt

NO_EDGE = Qt.Edge(0)


def resize_edges_at(x: int, y: int, width: int, height: int, grip: int = 7, corner: int = 18):
    """Bordas sob o ponteiro, em coordenadas da janela.

    Só a faixa de ``grip`` px ativa o redimensionamento; perto do canto
    (``corner`` px) a borda vira diagonal, como no Windows.
    """
    near = x < grip or x >= width - grip or y < grip or y >= height - grip
    if not near:
        return NO_EDGE
    edges = NO_EDGE
    if x < corner:
        edges |= Qt.LeftEdge
    elif x >= width - corner:
        edges |= Qt.RightEdge
    if y < corner:
        edges |= Qt.TopEdge
    elif y >= height - corner:
        edges |= Qt.BottomEdge
    return edges


def cursor_for_edges(edges):
    if not edges:
        return None
    left, right = bool(edges & Qt.LeftEdge), bool(edges & Qt.RightEdge)
    top, bottom = bool(edges & Qt.TopEdge), bool(edges & Qt.BottomEdge)
    if (left and top) or (right and bottom):
        return Qt.SizeFDiagCursor
    if (right and top) or (left and bottom):
        return Qt.SizeBDiagCursor
    if left or right:
        return Qt.SizeHorCursor
    return Qt.SizeVerCursor


def resized_rect(rect: QRect, edges, delta: QPoint, minimum: QSize) -> QRect:
    """Geometria nova ao arrastar ``edges`` por ``delta``, sem passar do mínimo."""
    result = QRect(rect)
    if edges & Qt.LeftEdge:
        result.setLeft(min(rect.left() + delta.x(), rect.right() - minimum.width() + 1))
    if edges & Qt.RightEdge:
        result.setRight(max(rect.right() + delta.x(), rect.left() + minimum.width() - 1))
    if edges & Qt.TopEdge:
        result.setTop(min(rect.top() + delta.y(), rect.bottom() - minimum.height() + 1))
    if edges & Qt.BottomEdge:
        result.setBottom(max(rect.bottom() + delta.y(), rect.top() + minimum.height() - 1))
    return result


def snap_point(point: QPoint, size: QSize, area: QRect, distance: int = 14) -> QPoint:
    """Gruda a janela na borda da área útil quando chega a ``distance`` px."""
    x, y = point.x(), point.y()
    if abs(x - area.left()) <= distance:
        x = area.left()
    elif abs((x + size.width()) - (area.right() + 1)) <= distance:
        x = area.right() + 1 - size.width()
    if abs(y - area.top()) <= distance:
        y = area.top()
    elif abs((y + size.height()) - (area.bottom() + 1)) <= distance:
        y = area.bottom() + 1 - size.height()
    return QPoint(x, y)


def virtual_desktop_rect() -> QRect:
    rect = QRect()
    for screen in QGuiApplication.screens():
        rect = rect.united(screen.geometry())
    return rect


def point_is_visible(point: QPoint, margin: int = 24) -> bool:
    for screen in QGuiApplication.screens():
        geo = screen.geometry().adjusted(-margin, -margin, margin, margin)
        if geo.contains(point):
            return True
    return False


def clamp_top_left(x: int | None, y: int | None, size, default_screen_index: int = 0) -> QPoint:
    screens = QGuiApplication.screens()
    if not screens:
        return QPoint(40, 40)
    if x is not None and y is not None and point_is_visible(QPoint(x, y)):
        candidate = QRect(x, y, size.width(), size.height())
        for screen in screens:
            if screen.geometry().intersects(candidate):
                bounded = screen.geometry()
                cx = min(max(x, bounded.left()), bounded.right() - size.width())
                cy = min(max(y, bounded.top()), bounded.bottom() - size.height())
                return QPoint(cx, cy)
        return QPoint(x, y)
    primary = screens[min(default_screen_index, len(screens) - 1)].geometry()
    margin = 24
    return QPoint(primary.right() - size.width() - margin, primary.bottom() - size.height() - margin)
