"""Account column body: one line of colored info pills under the name, then the
quota windows as an aligned full-width table (261012 blind-test synthesis).

Pill color = information TYPE (reset, cloud, extra, API), equal in every
provider. Fill = has a positive value; outline only = zero or unknown; dashed
outline = manual browser observation. Pills that do not fit collapse into a
"+N" pill whose tooltip lists them; nothing is dropped from the details.
"""
import re
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import QLabel, QProgressBar, QSizePolicy, QWidget

from . import theme
from .formatting import percent_label
from .glance_contract import overview

PILL_GAP = 4
PILL_PAD = 5
KIND_ORDER = {"reset": 0, "cloud": 1, "extra": 2, "api": 3, "other": 4}
# Composition/plan details: shown when room allows, first to fold into "+N".
SECONDARY_IDS = {"browser:parts", "balance:plan", "balance:unknown"}


def is_primary(item):
    return item.id not in SECONDARY_IDS and theme.chip_kind(item.id, item.label) != "other"


def _rgba(color, alpha):
    c = QColor(color)
    return f"rgba({c.red()},{c.green()},{c.blue()},{alpha})"


def _track(palette):
    """palette['track_bg'] is an RGBA tuple; a raw tuple is not valid Qt CSS."""
    value = palette.get('track_bg')
    if isinstance(value, tuple) and len(value) == 4:
        r, g, b, _ = value
        return f'rgba({r},{g},{b},{0.10 if palette.get("light") else 0.13})'
    return str(value or 'rgba(255,255,255,0.13)')


def has_value(value):
    """Positive stock/amount from the value only, never tooltip/expiry metadata."""
    text = str(value or "")
    if not text or "—" in text or "n/d" in text:
        return False
    # Every fraction contributes only its numerator, including compositions
    # such as '0/2 retido + 0/5'. Totals do not represent remaining stock.
    numeric_text = re.sub(r"(\d+(?:[.,]\d+)?)\s*/\s*\d+(?:[.,]\d+)?", r"\1", text.replace(" ", ""))
    numbers = re.findall(r"\d+(?:[.,]\d+)?", numeric_text)
    if not numbers:
        return "sem limite" in text
    return any(float(n.replace(",", ".")) > 0 for n in numbers)


def pill_text(item):
    """Icon + label + value. Manual '*' is drawn as a dashed outline instead."""
    kind = theme.chip_kind(item.id, item.label)
    label = item.label.rstrip('*')
    if not label.startswith(theme.CHIP_ICONS["reset"]):
        label = f"{theme.CHIP_ICONS[kind]} {label}"
    return f"{label} {item.value}".strip()


class GlanceView(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.quotas = []; self.items = []; self.rows = []; self.palette = {}; self.font_family = 'Inter'; self.fits = True
        self.hidden_items = []
        self.setObjectName('quotaGlance'); self.setCursor(Qt.ArrowCursor); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.more = QLabel(self); self.more.setTextFormat(Qt.PlainText); self.more.setAlignment(Qt.AlignCenter); self.more.hide()
        self.warning = QLabel('≡ Mais dados', self); self.warning.setToolTip('O tamanho atual não comporta tudo. Enter ou clique no nome abre os dados completos.')
        self.warning.setTextFormat(Qt.PlainText); self.warning.hide()

    def set_data(self, row_id, display, *, number_mode, reset_mode, browser, name, palette, family):
        self.palette = palette; self.font_family = family
        quotas, items = overview(row_id, display, number_mode=number_mode, reset_mode=reset_mode, browser=browser, name=name)
        # Stable priority: resets, cloud, extra, API, then the rest (plan, unknown).
        items = [i for _, i in sorted(enumerate(items), key=lambda p: (not is_primary(p[1]), KIND_ORDER[theme.chip_kind(p[1].id, p[1].label)], p[0]))]
        new_schema = [(i.id, i.kind) for i in quotas + items]
        if new_schema != [(r['item'].id, r['item'].kind) for r in self.rows]:
            for row in self.rows:
                for widget in row['widgets']: widget.hide(); widget.deleteLater()
            self.rows = []
            for item in quotas + items:
                text = QLabel(self); text.setTextFormat(Qt.PlainText); text.setFocusPolicy(Qt.NoFocus)
                widgets = [text]
                if item.kind == 'quota':
                    bar = QProgressBar(self); bar.setRange(0, 10000); bar.setTextVisible(False)
                    pct = QLabel(self); pct.setTextFormat(Qt.PlainText); pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    renew = QLabel(self); renew.setTextFormat(Qt.PlainText); renew.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    widgets += [bar, pct, renew]
                else:
                    text.setAlignment(Qt.AlignCenter)
                self.rows.append({'item': item, 'widgets': widgets, 'quota': item.kind == 'quota', 'shown': True})
        self.quotas, self.items = quotas, items
        light = bool(palette.get('light'))
        colors = theme.chip_colors_for(light)
        for row, item in zip(self.rows, quotas + items):
            row['item'] = item
            label = row['widgets'][0]
            if row['quota']:
                label.setText(item.label); row['widgets'][2].setText(percent_label(item.percent)); row['widgets'][3].setText(item.value)
                full = f'{item.label} {percent_label(item.percent)} {item.value}'.strip()
                for widget in row['widgets']:
                    widget.setToolTip(item.tooltip)
                label.setAccessibleName(full + '. ' + item.tooltip)
                bar = row['widgets'][1]; bar.setValue(round(item.percent * 100) if item.percent is not None else 0)
                bar.setAccessibleName(f'{item.label}: {percent_label(item.percent)}')
                bar.setStyleSheet(f'QProgressBar{{border:0;background:{_track(palette)};border-radius:2px;}}'
                                  f' QProgressBar::chunk{{background:{item.color or palette["text_secondary"]};border-radius:2px;}}')
            else:
                kind = theme.chip_kind(item.id, item.label)
                color = colors[kind]
                filled = has_value(item.value)
                manual = bool(item.manual_date) or item.label.endswith('*')
                text = pill_text(item)
                label.setText(text); label.setToolTip(item.tooltip); label.setAccessibleName(text + '. ' + item.tooltip)
                row['style'] = (f'color:{color if filled else _rgba(color, 0.8)};'
                                f'background:{_rgba(color, 0.16) if filled else "transparent"};'
                                f'border:1px {"dashed" if manual else "solid"} {_rgba(color, 0.6 if filled else 0.35)};')
        if not hasattr(self.parent(), "strip"):
            self.setMinimumHeight(self.minimumSizeHint().height())
        self.updateGeometry()
        self.arrange()

    def manual_dates(self):
        return sorted({item.manual_date for item in self.items if item.manual_date})

    def font_px(self):
        strip = getattr(self.parent(), "strip", None)
        return (11 if strip.inner_height() - strip.header_height() - 1 >= 64 else 9) if strip is not None else 11

    def _metrics(self):
        f = QFont(self.font_family); f.setPixelSize(self.font_px())
        return f, QFontMetrics(f)

    def _pill_width(self, fm, text):
        return fm.horizontalAdvance(text) + 2 * PILL_PAD + 2

    def arrange(self):
        if not self.rows: return
        f, fm = self._metrics()
        line = fm.height(); pill_h = line + 2
        width = self.width()
        text_color = self.palette.get("text", "#ffffff"); muted = self.palette.get("text_secondary", "#a7b0c4")
        quota_rows = [r for r in self.rows if r['quota']]
        pill_rows = [r for r in self.rows if not r['quota']]
        self.fits = True
        # 1 · Pills under the name. Strip: ONE line, the rest folds into "+N".
        # Legacy cards (no strip, vertical room): pills wrap instead of folding.
        wrap = self.wraps()
        x = y_pill = 0; self.hidden_items = []
        more_w = self._pill_width(fm, f'+{len(pill_rows)}')
        for index, row in enumerate(pill_rows):
            label = row['widgets'][0]; label.setFont(f)
            w = self._pill_width(fm, label.text())
            remaining = len(pill_rows) - index - 1
            if wrap and x > 0 and x + w > width:
                x = 0; y_pill += pill_h + 2
            room = width - x - (more_w + PILL_GAP if remaining and not wrap else 0)
            if not wrap and (self.hidden_items or w > room):
                row['shown'] = False; label.hide(); self.hidden_items.append(row['item']); continue
            row['shown'] = True
            label.setStyleSheet(row.get('style', '') + f'border-radius:{pill_h // 2}px;padding:0 {PILL_PAD}px;')
            label.setGeometry(x, y_pill, w, pill_h); label.show(); x += w + PILL_GAP
        if self.hidden_items:
            self.more.setFont(f); self.more.setText(f'+{len(self.hidden_items)}')
            self.more.setStyleSheet(f'color:{muted};border:1px solid {_rgba(muted, 0.4)};border-radius:{pill_h // 2}px;padding:0 {PILL_PAD}px;')
            self.more.setToolTip('\n'.join(f'{pill_text(i)} — {i.tooltip}' for i in self.hidden_items) + '\nEnter ou clique no nome abre tudo.')
            mw = self._pill_width(fm, self.more.text())
            self.more.setGeometry(x, y_pill, mw, pill_h); self.more.show()
            self.fits = self.fits and x + mw <= width
        else:
            self.more.hide()
        # 2 · Windows: aligned table at full width (name | bar | % + renewal).
        top = (y_pill + pill_h + (4 if self.height() >= 64 else 1)) if pill_rows else 0
        available = max(0, self.height() - top)
        count = len(quota_rows)
        step = min(line + 6, available // count) if count else 0
        self.fits = self.fits and (not count or step >= line)
        bold = QFont(f); bold.setBold(True); bm = QFontMetrics(bold)
        name_w = max([fm.horizontalAdvance(r['widgets'][0].text()) for r in quota_rows] or [0])
        pct_w = max([bm.horizontalAdvance(r['widgets'][2].text()) for r in quota_rows] or [0])
        renew_w = max([fm.horizontalAdvance(r['widgets'][3].text()) for r in quota_rows] or [0])
        bar_h = 4 if step >= line + 3 else 3
        bar_x = name_w + 6; renew_x = width - renew_w; pct_x = renew_x - 4 - pct_w
        bar_w = max(16, pct_x - 6 - bar_x)
        self.fits = self.fits and bar_x + bar_w + 6 + pct_w + 4 + renew_w <= width
        y = top
        for row in quota_rows:
            name, bar, pct, renew = row['widgets']
            name.setFont(f); renew.setFont(f); pct.setFont(bold)
            name.setStyleSheet(f'color:{muted};'); renew.setStyleSheet(f'color:{muted};'); pct.setStyleSheet(f'color:{text_color};')
            name.setGeometry(0, y, name_w, line)
            bar.setGeometry(bar_x, y + (line - bar_h) // 2, bar_w, bar_h)
            pct.setGeometry(pct_x, y, pct_w, line)
            renew.setGeometry(renew_x, y, renew_w, line)
            for widget in row['widgets']: widget.show()
            y += step
        dates = self.manual_dates()
        self.setToolTip('\n'.join('Navegador: ' + d for d in dates))
        self.warning.setFont(f); self.warning.setStyleSheet(f'color:{self.palette.get("accent", "#edbf73")};background:{self.palette.get("panel_bg", "#151b2c")};')
        self.warning.setGeometry(0, max(0, self.height() - line), self.width(), line)
        self.warning.setVisible(not self.fits)
        if self.warning.isVisible(): self.warning.raise_()

    def wraps(self):
        return not hasattr(self.parent(), "strip")

    def pill_lines(self, width):
        _, fm = self._metrics(); lines = 1 if self.items else 0; x = 0
        for item in self.items:
            w = self._pill_width(fm, pill_text(item))
            if x > 0 and x + w > width:
                lines += 1; x = 0
            x += w + PILL_GAP
        return lines

    def resizeEvent(self, event): super().resizeEvent(event); self.arrange()

    def minimum_width(self):
        _, fm = self._metrics()
        bold = QFont(self._metrics()[0]); bold.setBold(True); bm = QFontMetrics(bold)
        rows = max([fm.horizontalAdvance(i.label) for i in self.quotas] or [0]) + 6 + 40 + 6 + 4 + \
            max([bm.horizontalAdvance(percent_label(i.percent)) for i in self.quotas] or [0]) + \
            max([fm.horizontalAdvance(i.value) for i in self.quotas] or [0])
        # Primary pills (reset, cloud, extra, API) always fit in the column:
        # large values page accounts, never truncate. Only "other" may fold.
        primary = [i for i in self.items if is_primary(i)]
        others = len(self.items) - len(primary)
        pills = sum(self._pill_width(fm, pill_text(i)) + PILL_GAP for i in primary)
        if others:
            pills += self._pill_width(fm, f'+{others}')
        if (self.wraps() or not primary) and self.items:
            pills = max(self._pill_width(fm, pill_text(i)) for i in self.items)
        return max(rows, pills, 60)

    def minimumSizeHint(self):
        _, fm = self._metrics(); line = fm.height()
        lines = self.pill_lines(max(self.width(), self.minimum_width())) if self.wraps() else (1 if self.items else 0)
        pills = lines * (line + 2) + max(0, lines - 1) * 2 + (4 if lines else 0)
        return QSize(self.minimum_width(), pills + len(self.quotas) * (line + 2))

    def sizeHint(self): return self.minimumSizeHint()

    def geometry_checks(self):
        """Visible elements only; pills folded into "+N" are listed by it."""
        _, fm = self._metrics(); out = []
        for r in self.rows:
            if not r['shown']: continue
            widgets = r['widgets']
            if r['quota']:
                text = f"{widgets[0].text()} {widgets[2].text()} {widgets[3].text()}".strip()
                fits = all(QFontMetrics(w.font()).horizontalAdvance(w.text()) <= w.width() for w in (widgets[0], widgets[2], widgets[3]))
            else:
                text = widgets[0].text(); fits = self._pill_width(fm, text) <= widgets[0].width()
            out.append({'id': r['item'].id, 'text': text, 'contained': all(self.rect().contains(w.geometry()) for w in widgets), 'text_fits': fits})
        if self.more.isVisible():
            out.append({'id': 'more', 'text': self.more.text(), 'contained': self.rect().contains(self.more.geometry()), 'text_fits': True})
        return out
