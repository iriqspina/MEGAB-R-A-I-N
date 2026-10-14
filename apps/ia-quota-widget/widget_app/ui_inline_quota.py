"""Shared renderer of the declarative contract (inline_contract.Field).

FieldList draws every field of one provider row; BoardScroll is a scroll area
whose minimum height is ZERO, so content never dictates the strip height. Data
updates are in place while the field schema is unchanged; the scroll position
survives every refresh and nothing here resizes the outer window.
"""
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QAbstractSlider, QFrame, QGridLayout, QLabel, QScrollArea, QSizePolicy, QWidget

from . import theme
from .contrast import hex_to_rgb
from .inline_contract import schema, TRACK_KINDS
from .ui_provider_segment import PercentTrack

DEFAULT_PALETTE = theme.palette_for(theme.DEFAULT_SURFACE_PRESET)
# Text kinds drawn in the primary colour (data); the rest are secondary.
DATA_KINDS = ("reset", "financial", "browser", "share")
# Reference strings: the wide/narrow switch depends on fonts and schema, never
# on the text of one particular reading ("em 59 min" vs "em 2 h").
RESET_REFERENCE = "↻ amanhã 00:00"
TRACK_MIN = 60


def _label(parent) -> QLabel:
    label = QLabel(parent)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setFocusPolicy(Qt.NoFocus)
    return label


class FieldList(QWidget):
    """Grid of fields. Quota rows: label | bar with % | renewal (wide) or
    label + renewal over a full-width bar (narrow). Other fields span the row
    and wrap inside the column; there is no horizontal scrolling of data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inlineFields")
        # The scroll viewport sets the width. Long details wrap, never disappear
        # into an ellipsis or dictate the outer fixed height.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._wrap = True
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(6)
        self._grid.setVerticalSpacing(2)
        self._grid.setColumnStretch(1, 1)
        self._schema = None
        self._rows: list[dict] = []
        self._wide = None
        self._palette = DEFAULT_PALETTE
        self._family = theme.FONT_FAMILY
        self._hint_px = 11
        self._detail_px = 12
        self.rebuilds = 0

    # ------------------------------------------------------------ API
    def set_fields(self, fields) -> bool:
        fields = list(fields)
        rebuilt = schema(fields) != self._schema
        if rebuilt:
            self._rebuild(fields)
        for row, field in zip(self._rows, fields):
            self._fill(row, field)
        self._place(force=rebuilt)
        return rebuilt

    def apply_style(self, palette: dict, family: str, hint_px: int, detail_px: int):
        self._palette, self._family = palette, str(family or theme.FONT_FAMILY)
        self._hint_px, self._detail_px = max(9, int(hint_px)), max(9, int(detail_px))
        for row in self._rows:
            self._style_row(row)
        self._place(force=True)

    def widgets(self, field_id: str) -> list:
        for row in self._rows:
            if row["id"] == field_id:
                return [w for w in (row.get("label"), row.get("track"), row.get("text")) if w is not None]
        return []

    def field_ids(self) -> list[str]:
        return [row["id"] for row in self._rows]

    def texts(self) -> list[str]:
        """Readable dump (tests, copy, parity): exactly what is on screen."""
        out = []
        for row in self._rows:
            if row["kind"] in TRACK_KINDS:
                out.append(f"{row['label'].text()} | {row['track']._text} | {row.get('full', '')}")
            else:
                out.append(row.get("full", ""))
        return out

    def is_wide(self) -> bool:
        return bool(self._wide)

    # ------------------------------------------------------------ internals
    def _rebuild(self, fields):
        while self._grid.count():
            self._grid.takeAt(0)
        for row in self._rows:
            for widget in (row.get("label"), row.get("track"), row.get("text")):
                if widget is not None:
                    widget.hide()
                    widget.deleteLater()
        self._rows = []
        for field in fields:
            row = {"id": field.id, "kind": field.kind}
            if field.kind in TRACK_KINDS:
                row["label"] = _label(self)
                row["label"].setWordWrap(False)
                row["track"] = PercentTrack(self)
                row["track"].setMinimumWidth(40)
                # set_value(None) on a new track is a no-op; unknown must
                # still read "—" inside the bar, never an empty (or 0) bar.
                row["track"]._text = "—"
                row["text"] = _label(self)
                row["text"].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                row["text"] = _label(self)
            if not self._wrap:
                row["text"].setWordWrap(False)
                row["text"].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self._rows.append(row)
            self._style_row(row)
        self._schema = schema(fields)
        self._wide = None
        self.rebuilds += 1

    def _show_text(self, row):
        label, full = row["text"], row.get("full", "")
        if not self._wrap and label.width() >= 40:
            full = label.fontMetrics().elidedText(full, Qt.ElideRight, label.width())
        if label.text() != full:
            label.setText(full)

    def _fill(self, row, field):
        text = row["text"]
        row["full"] = field.text
        self._show_text(row)
        tooltip = field.tooltip or field.text
        if field.kind in TRACK_KINDS:
            if row["label"].text() != field.label:
                row["label"].setText(field.label)
            row["track"].set_value(field.percent, field.color or theme.STATUS_GREY)
            for widget in (row["label"], row["track"], text):
                widget.setToolTip(tooltip)
            row["track"].setAccessibleName(f"{field.label}: {row['track']._text} · {field.text}")
        else:
            text.setToolTip(tooltip)
        text.setAccessibleName(tooltip)

    def _font(self, px, bold=False) -> QFont:
        font = QFont(self._family)
        font.setPixelSize(px)
        font.setBold(bold)
        return font

    def _style_row(self, row):
        palette = self._palette
        secondary, primary = palette["text_secondary"], palette["text"]
        if row["kind"] in TRACK_KINDS:
            row["label"].setFont(self._font(self._hint_px))
            row["label"].setStyleSheet(f"color:{secondary};")
            row["track"].set_text_style(self._family, self._hint_px, secondary)
            row["track"].set_background(palette.get("track_bg", theme.TRACK_BG))
            row["text"].setFont(self._font(self._hint_px))
            row["text"].setStyleSheet(f"color:{secondary};")
            return
        bold = row["kind"] == "caption"
        px = self._hint_px if row["kind"] in ("caption", "legend", "source", "note") else self._detail_px
        row["text"].setFont(self._font(px, bold))
        row["text"].setStyleSheet(f"color:{primary if row['kind'] in DATA_KINDS else secondary};")

    def _needed_wide(self) -> int:
        # A longer product name in the extras must not switch session/week
        # to two-line rows and push their bars out of the first view.
        labels = [row["label"].text() for row in self._rows if row["kind"] == 'quota']
        if not labels:
            return 0
        label_w = max(QFontMetrics(self._font(self._hint_px)).horizontalAdvance(t) for t in labels)
        reset_w = QFontMetrics(self._font(self._hint_px)).horizontalAdvance(RESET_REFERENCE)
        return label_w + TRACK_MIN + reset_w + 2 * self._grid.horizontalSpacing()

    def _place(self, force=False):
        wide = self.width() >= self._needed_wide() and self.width() > 0
        if wide == self._wide and not force:
            return
        self._wide = wide
        while self._grid.count():
            self._grid.takeAt(0)
        for index in range(self._grid.rowCount()):
            self._grid.setRowStretch(index, 0)
        line = 0
        for row in self._rows:
            if row["kind"] in TRACK_KINDS:
                self._grid.addWidget(row["label"], line, 0)
                if wide:
                    self._grid.addWidget(row["track"], line, 1)
                    self._grid.addWidget(row["text"], line, 2)
                    line += 1
                else:
                    self._grid.addWidget(row["text"], line, 1, 1, 2)
                    self._grid.addWidget(row["track"], line + 1, 0, 1, 3)
                    line += 2
            else:
                self._grid.addWidget(row["text"], line, 0, 1, 3)
                line += 1
            for widget in (row.get("label"), row.get("track"), row.get("text")):
                if widget is not None:
                    widget.show()
        self._grid.setRowStretch(line, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._place()
        if not self._wrap:
            # Children get their width in the same layout pass; elide after it.
            QTimer.singleShot(0, self, lambda: [self._show_text(row) for row in self._rows])


class BoardScroll(QScrollArea):
    """Vertical-only scroll area. Minimum height ZERO: the parent's fixed
    height decides, the content never does. keep_width keeps the content's
    minimum width (Legacy cards) so data is never clipped sideways."""

    def __init__(self, content: QWidget, parent=None, keep_width=False):
        super().__init__(parent)
        self._keep_width = keep_width
        self.setObjectName("inlineBoard")
        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setFocusPolicy(Qt.NoFocus)
        # Keyboard focus stays on the provider column (↑↓ PgUp PgDn scroll it);
        # the bar itself is for the mouse, so Tab order never changes.
        self.verticalScrollBar().setFocusPolicy(Qt.NoFocus)
        self.viewport().setObjectName("inlineViewport")
        self.viewport().setAutoFillBackground(False)
        self.setWidget(content)
        content.setAutoFillBackground(False)
        self.apply_scroll_style(DEFAULT_PALETTE)

    def _bar_width(self) -> int:
        return 8

    def minimumSizeHint(self):
        if not self._keep_width or self.widget() is None:
            return QSize(0, 0)
        return QSize(self.widget().minimumSizeHint().width() + self._bar_width(), 0)

    def sizeHint(self):
        width = self.widget().sizeHint().width() + self._bar_width() if self.widget() is not None else 0
        return QSize(width, 0)

    def apply_scroll_style(self, palette: dict):
        r, g, b = hex_to_rgb(palette["text_secondary"])
        name = self.objectName()
        self.setStyleSheet(
            f"#{name} {{ background: transparent; border: 0; }}"
            f"#inlineViewport, #inlineFields, #legacyContent {{ background: transparent; }}"
            f"#{name} QScrollBar:vertical {{ background: rgba({r},{g},{b},0.12); width: {self._bar_width()}px; margin: 0; border-radius: 3px; }}"
            f"#{name} QScrollBar::handle:vertical {{ background: rgba({r},{g},{b},0.75); min-height: 12px; border-radius: 3px; }}"
            f"#{name} QScrollBar::add-line:vertical, #{name} QScrollBar::sub-line:vertical {{ height: 0; }}"
            f"#{name} QScrollBar::add-page:vertical, #{name} QScrollBar::sub-page:vertical {{ background: transparent; }}"
        )

    def keep_scroll(self, update):
        """Run an update and keep the reading position (also after the
        deferred layout pass that recomputes the range)."""
        bar = self.verticalScrollBar()
        wanted = bar.value()
        result = update()
        bar.setValue(wanted)
        if wanted:
            QTimer.singleShot(0, self, lambda: bar.setValue(wanted) if bar.value() != wanted and wanted <= bar.maximum() else None)
        return result

    def scroll_by_key(self, key) -> bool:
        bar = self.verticalScrollBar()
        action = QAbstractSlider.SliderAction
        actions = {Qt.Key_Up: action.SliderSingleStepSub, Qt.Key_Down: action.SliderSingleStepAdd,
                   Qt.Key_PageUp: action.SliderPageStepSub, Qt.Key_PageDown: action.SliderPageStepAdd}
        if key not in actions:
            return False
        bar.triggerAction(actions[key])
        return True


class InlineQuotaBody(BoardScroll):
    """Scrollable body of one Trilho column: every field of the row."""

    def __init__(self, parent=None):
        fields = FieldList()
        super().__init__(fields, parent)
        self.fields = fields

    def set_fields(self, fields) -> bool:
        return self.keep_scroll(lambda: self.fields.set_fields(fields))

    def apply_style(self, palette: dict, family: str, hint_px: int, detail_px: int):
        self.apply_scroll_style(palette)
        self.keep_scroll(lambda: self.fields.apply_style(palette, family, hint_px, detail_px))
