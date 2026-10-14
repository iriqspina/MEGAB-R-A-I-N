"""One native row. Fixed height, measured text, stable buttons, explicit paging.

Each provider is a column: compact header (account, status, freshness) over a
scrolling body with every window, reset, balance and source (inline_contract).
"""
from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QPushButton, QWidget

from . import theme
from .formatting import percent_label
from .inline_contract import browser_account, header_state, provider_fields
from .layout_policy import CONTROL_WIDTH, EDGE, NAV_WIDTH, compact_header_px, strip_policy
from .provider_brand import brand_pixmap, provider_name
from .quota_focus import duration_label, exhausted_windows, focus_window, general_windows, state_label
from .ui_inline_quota import InlineQuotaBody
from .ui_glance_quota import GlanceView
from .inline_contract import short_date
from .layout_policy import StripPolicy
from quota_details_data import reset_summary
from .observed_info import observed_resets,evidence_date


def font(settings, key, minimum, bold=False):
    result = QFont(settings.font_family)
    result.setPixelSize(max(minimum, round(getattr(settings, key) * settings.scale)))
    result.setBold(bold)
    return result


class GripDots(QWidget):
    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setGeometry(0, 0, 18, 20)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.owner._palette()['text_secondary']))
        for x in (5, 10):
            for y in (4, 9, 14):
                painter.drawEllipse(QRectF(x, y, 3, 3))
        painter.end()


class QuotaCell(QAbstractButton):
    def __init__(self, strip, row_id):
        super().__init__(strip)
        self.strip, self.row_id = strip, row_id
        self.display = self.focus = None
        self.shown = None
        self.warning_count = 0
        self.meta = "janela ? · aguardando"
        self.reset_count = '—'
        self.fields = []
        self.state = ('○', 'aguardando')
        self.tone, self.tone_reason = None, ""
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(lambda: strip.owner.open_quota_details(row_id, self))
        self.body = InlineQuotaBody(self)
        self.body.setCursor(Qt.ArrowCursor)
        self.glance = GlanceView(self)

    def refresh(self):
        owner = self.strip.owner
        self.strip.header_fonts()  # accessibility uses this refresh's cap
        self.display = owner.store.display(theme.row_source(self.row_id))
        windows = (self.display or {}).get("windows") or []
        self.focus = focus_window(general_windows(windows, self.row_id))
        used = (self.focus or {}).get("used_percent")
        self.shown = 100 - used if used is not None and owner.settings.number_mode == "remaining" else used
        self.warning_count = len(exhausted_windows(windows, self.focus))
        self.tone, self.tone_reason = self.hero_tone(owner, windows)
        querying = theme.row_source(self.row_id) in owner._querying
        state = state_label(self.display, self.focus, querying)
        self.state_symbol = "↻" if querying else ("!" if (self.display or {}).get("status") not in (None, "ok") else ("◷" if (self.display or {}).get("stale") else "●"))
        self.reset_count = reset_summary((self.display or {}).get('details'))
        reset_date=''
        if self.reset_count=='—':
            observed,reset_date=observed_resets(self.row_id)
            if observed:self.reset_count=reset_summary({'resets':observed})+'*'
        self.meta = f"{duration_label(self.focus)} · {self.state_symbol} {state}"
        label = provider_name(self.row_id, owner._canonical_labels)
        # Whole column body: every window, reset, balance and source. Browser
        # evidence is real account data, so DEMO (and the preview) never mix it in.
        browser = None if owner.demo else browser_account(self.row_id)
        self.fields = provider_fields(self.row_id, self.display, number_mode=owner.settings.number_mode,
                                      reset_mode=owner.settings.reset_mode, querying=querying,
                                      browser=browser, name=label)
        self.body.set_fields(self.fields)
        self.glance.set_data(self.row_id,self.display,number_mode=owner.settings.number_mode,reset_mode=owner.settings.reset_mode,browser=browser,name=label,palette=owner._palette(),family=owner.settings.font_family)
        self.state = header_state(self.display, querying)
        mode = "restante" if owner.settings.number_mode == "remaining" else "usado"
        warning = f" · {self.warning_count} outra(s) janela(s) esgotada(s)" if self.warning_count else ""
        text = f"{label} · {percent_label(self.shown)} {mode} · {self.meta}{warning}"
        if self.tone_reason:
            text += f" · cor do número: {self.tone_reason}"
        text += f" · resets restantes: {self.reset_count} (— = não informado) · Enter para detalhes"
        text+=' · ♻ disponível; C = completo; H = 5 horas; disponível/total quando há oferta retida'
        if reset_date:text+=' · * última verificação no navegador: '+evidence_date(reset_date)
        text += ' · Monitor 9/11px; preferências de fonte mantidas. Enter abre as fontes e detalhes.'
        if self.strip.owner.settings.strip_height < 60:text += ' · Micro: ↑↓ PgUp PgDn rolam a coluna'
        if self.strip.header_note:
            text += ' · ' + self.strip.header_note
        self.setAccessibleName(text)
        self.setToolTip(text)
        self.update()

    def hero_tone(self, owner, windows):
        """Color of the big number (261012): the account's real pacing, never a
        made-up threshold. Alert threshold from Settings always wins (red)."""
        if (self.display or {}).get("status") not in (None, "ok") or self.shown is None:
            return None, ""
        alert = owner.settings.alert_percent
        remaining_mode = owner.settings.number_mode == "remaining"
        if (remaining_mode and self.shown <= 100 - alert) or (not remaining_mode and self.shown >= alert):
            return "red", f"alerta: passou de {alert}% usado"
        pacing = (getattr(owner, "_pacing_by_provider", {}) or {}).get(theme.row_source(self.row_id)) or {}
        ids = {str(w.get("id")) for w in general_windows(windows, self.row_id)}
        rank = {"ok": 0, "NAO_MEDIDO": 1, "desacelerar": 2, "pause": 3}
        statuses = [w.get("status") for wid, w in (pacing.get("windows") or {}).items() if wid in ids]
        worst = max(statuses, key=lambda s: rank.get(s, 1)) if statuses else None
        return ({"ok": "green", "desacelerar": "amber", "pause": "red"}.get(worst),
                {"ok": "ritmo ok", "desacelerar": "ritmo: desacelerar (gastando acima do ritmo da janela)",
                 "pause": "ritmo: pausar", "NAO_MEDIDO": "ritmo não medido"}.get(worst, "ritmo não medido"))

    def hero_text(self):
        ok = (self.display or {}).get("status") == "ok"
        return percent_label(self.shown) if ok and self.shown is not None else ""

    def hero_font(self, name_font):
        hero = QFont(name_font)
        hero.setPixelSize(name_font.pixelSize() + 2)
        hero.setBold(True)
        return hero

    def meta_text(self):
        """Small status beside the big number: only what is NOT the default
        (fresh reading needs no word; stale, error and manual dates do)."""
        symbol, state = getattr(self, 'state', ('○', 'aguardando'))
        state = state.replace("salvo · ", "").replace("antigo · ", "").replace("há ", "").replace(" min", "m")
        if state == "agora" and symbol == "●":
            state = ""
        dates = self.glance.manual_dates()
        if dates:
            days = sorted({short_date(d)[:5] for d in dates})
            state += (" · " if state else "") + "manual " + (days[0] if len(days) == 1 else "+".join(days))
        warning = f" · !{self.warning_count}" if self.warning_count else ""
        return f"{symbol} {state}".strip() + warning

    def layout_body(self):
        top = self.strip.header_height()
        self.body.setGeometry(4, top, max(0, self.width() - 8), max(0, self.height() - top - 1))
        self.glance.setGeometry(4, top, max(0,self.width()-8),max(0,self.height()-top-1))
        self.glance.setVisible(self.height()>=60)
        self.body.setVisible(self.height()<60)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.layout_body()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.click()
            event.accept()
        elif event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Home, Qt.Key_End):
            self.strip.navigate_from(self.row_id, event.key())
            event.accept()
        elif self.body.isVisible() and self.body.scroll_by_key(event.key()):
            event.accept()
        else:
            super().keyPressEvent(event)

    def header_required_width(self):
        name_font,meta_font=self.strip.header_fonts()
        name=provider_name(self.row_id,self.strip.owner._canonical_labels)
        meta_width=QFontMetrics(meta_font).horizontalAdvance(self.meta_text())
        hero_width=QFontMetrics(self.hero_font(name_font)).horizontalAdvance(self.hero_text() or "100%")
        logo=max(10,min(self.strip.logo_size(),QFontMetrics(name_font).height()))+4
        return QFontMetrics(name_font).horizontalAdvance(name)+logo+meta_width+hero_width+30

    def paintEvent(self, event):
        """Compact header only (logo, account, status/freshness); the body
        with every row is the child InlineQuotaBody below it."""
        owner = self.strip.owner
        palette = owner._palette()
        name_font, meta_font = self.strip.header_fonts()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(palette['text_secondary']))
        p.setOpacity(0.28)
        p.drawLine(0, 5, 0, self.height() - 5)
        p.setOpacity(1)
        if self.hasFocus():
            p.setPen(QPen(QColor(palette['text']), 1))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)
        left, right = 9, self.width() - 7
        line = self.strip.header_height() - 2
        symbol, _state = getattr(self, 'state', ('○', 'aguardando'))
        # 261012 hierarchy: name (left) · big focus number (right, colored by
        # real pacing) · small status only when it is not "fresh".
        hero = self.hero_text()
        hero_font = self.hero_font(name_font)
        hero_width = QFontMetrics(hero_font).horizontalAdvance(hero) if hero else 0
        meta = self.meta_text()
        meta_metrics = QFontMetrics(meta_font)
        name = provider_name(self.row_id, owner._canonical_labels)
        if owner.demo and self.height() < 60:
            name = "DEMO · " + name
        logo_size = max(10, min(self.strip.logo_size(), QFontMetrics(name_font).height()))
        logo = brand_pixmap(self.row_id, logo_size, self.devicePixelRatioF())
        logo_width = logo_size + 4 if not logo.isNull() else 0
        # Width priority: whole name, then the big number, then the status.
        name_room = QFontMetrics(name_font).horizontalAdvance(name)
        meta_width = max(0, min(meta_metrics.horizontalAdvance(meta), right - left - logo_width - name_room - hero_width - 14))
        available = max(0, right - left - logo_width - meta_width - hero_width - 12)
        if not logo.isNull():
            p.drawPixmap(left, 1 + (line - logo_size) // 2, logo)
        p.setFont(name_font)
        p.setPen(QColor(palette['text']))
        p.drawText(QRect(left + logo_width, 1, available, line), Qt.AlignVCenter,
                   QFontMetrics(name_font).elidedText(name, Qt.ElideRight, available))
        if hero:
            p.setFont(hero_font)
            p.setPen(QColor(palette['status'].get(self.tone) or palette['text']))
            p.drawText(QRect(right - hero_width, 0, hero_width, line + 2), Qt.AlignVCenter | Qt.AlignRight, hero)
        p.setFont(meta_font)
        alert = symbol == '!' or self.warning_count
        p.setPen(QColor(palette['status']['red'] if alert else palette['text_secondary']))
        meta_right = right - hero_width - (6 if hero else 0)
        p.drawText(QRect(meta_right - meta_width, 1, meta_width, line), Qt.AlignVCenter | Qt.AlignRight,
                   meta_metrics.elidedText(meta, Qt.ElideRight, meta_width))
        p.end()


class QuotaStrip(QWidget):
    def __init__(self, owner, drag_handle):
        super().__init__(owner)
        self.owner = owner
        self.cells = {}
        self.order = []
        self.start = 0
        self.header_note = ""
        self.policy = strip_policy(800, 72, 0)
        self.drag_handle = drag_handle
        drag_handle.setParent(self)
        self.grip = GripDots(drag_handle, owner)
        self.mode = QLabel(self)
        self.mode.setAlignment(Qt.AlignCenter)
        self.menu = QPushButton("≡", self)
        self.menu.setAccessibleName("Abrir configurações · Ctrl+,")
        self.menu.setToolTip("Configurações · Ctrl+,; botão direito para atalhos")
        self.menu.clicked.connect(lambda _checked=False: owner.open_settings())
        self.menu.setContextMenuPolicy(Qt.CustomContextMenu)
        self.menu.customContextMenuRequested.connect(lambda _pos: owner._show_menu())
        self.previous = QPushButton("‹", self)
        self.next = QPushButton("›", self)
        self.previous.setAccessibleName("Provedores anteriores")
        self.next.setAccessibleName("Próximos provedores")
        self.previous.clicked.connect(lambda: self.page(-1))
        self.next.clicked.connect(lambda: self.page(1))
        self.counter = QLabel(self)
        self.counter.setAlignment(Qt.AlignCenter)
        self.counter.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.empty = QLabel("Escolha provedores no menu ≡", self)
        self.empty.setAlignment(Qt.AlignCenter)
        for button in (self.menu, self.previous, self.next):
            button.setFocusPolicy(Qt.StrongFocus)

    def fonts(self):
        s = self.owner.settings
        return font(s, 'size_name', 12, True), font(s, 'size_value', 19, True), font(s, 'size_hint', 11)

    def logo_size(self):
        # Font metrics are logical pixels, as are the cell and paging geometry.
        return max(16, min(24, QFontMetrics(self.fonts()[0]).height()))

    def inner_height(self):
        # The requested height is the authority even before the deferred resize.
        return max(0, self.owner.settings.strip_height - 2 * EDGE)

    def header_fonts(self):
        """Compact header: the preferred name size, limited by the strip
        height (never the reverse). The adjustment is labelled, not hidden."""
        name, _value, hint = self.fonts()
        name_px = min(16,compact_header_px(self.inner_height(), name.pixelSize()))
        if self.inner_height()<80:name_px=min(name_px,13)
        self.header_note = (f"nome reduzido para {name_px}px nesta Altura da faixa (preferência {name.pixelSize()}px mantida)"
                            if name_px < name.pixelSize() else "")
        header_name = QFont(name)
        header_name.setPixelSize(name_px)
        meta = QFont(hint)
        meta.setPixelSize(min(hint.pixelSize(), name_px))
        return header_name, meta

    def header_height(self):
        return max(QFontMetrics(f).height() for f in self.header_fonts()) + 2

    def body_fonts_px(self):
        s = self.owner.settings
        return self.fonts()[2].pixelSize(), max(11, round(s.size_detail * s.scale))

    def geometry_policy(self, width, requested_height=None):
        height = self.owner.settings.strip_height if requested_height is None else requested_height
        if height<60:
            return strip_policy(width,height,len(self.order),230)
        count=len(self.order)
        minimums=[max(158,self.cells[row].glance.minimum_width()+8,self.cells[row].header_required_width()) for row in self.order]
        available=max(0,width-2*EDGE-CONTROL_WIDTH)
        cap=count if sum(minimums)<=available else 0
        if not cap and count:
            used=0
            for needed in minimums[max(0,min(self.start,count-1)):]:
                if used+needed>available-NAV_WIDTH and cap:break
                used+=needed;cap+=1
        return StripPolicy(height,max(360,CONTROL_WIDTH+NAV_WIDTH+2*EDGE+max(minimums or [158])),min(count,cap),height<60)

    def configure(self):
        self.order = [pid for pid in self.owner.provider_ids if self.owner.settings.is_visible(pid)]
        for pid in self.order:
            if pid not in self.cells:
                self.cells[pid] = QuotaCell(self, pid)
        palette = self.owner._palette()
        self.setStyleSheet(f"QPushButton {{color:{palette['text']}; background:transparent; border:0;}}"
                           f"QPushButton:focus {{border:1px solid {palette['text']};}}"
                           f"QPushButton:disabled {{color:{palette['text_secondary']};}}"
                           f"QLabel {{color:{palette['text_secondary']};}}")
        # Controls keep their small fixed geometry, but use the selected family.
        button_font = QFont(self.owner.settings.font_family)
        button_font.setPixelSize(16)
        label_font = QFont(self.owner.settings.font_family)
        label_font.setPixelSize(11)
        for button in (self.menu, self.previous, self.next):
            button.setFont(button_font)
        for label in (self.mode, self.counter, self.empty):
            label.setFont(label_font)
        self.mode.setText("DEMO" if self.owner.demo else ("LIVRE" if self.owner.settings.number_mode == 'remaining' else "USO"))
        hint_px, detail_px = self.body_fonts_px()
        for cell in self.cells.values():
            cell.body.apply_style(palette, self.owner.settings.font_family, hint_px, detail_px)
        self.refresh()
        self.arrange()

    def refresh(self):
        for row in self.order:
            self.cells[row].refresh()
        self.arrange()

    def sizeHint(self):
        return QSize(800 - 2 * EDGE, self.owner.settings.strip_height - 2 * EDGE)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.arrange()

    def arrange(self):
        self.policy = self.geometry_policy(self.width() + 2 * EDGE)
        count, cap = len(self.order), self.policy.capacity
        self.start = max(0, min(self.start, max(0, count - cap)))
        focused = QApplication.focusWidget()
        if isinstance(focused, QuotaCell) and focused.row_id in self.order:
            index = self.order.index(focused.row_id)
            if not self.start <= index < self.start + cap:
                self.start = max(0, index - cap + 1)
        for cell in self.cells.values():
            if cell.row_id not in self.order[self.start:self.start + cap]:
                cell.hide()
        height = self.height()
        self.mode.setVisible(height >= 60)
        if height >= 60:
            self.drag_handle.setGeometry(10, 2, 24, 20)
            self.mode.setGeometry(0, 23, CONTROL_WIDTH, 17)
            self.menu.setGeometry(10, height - 27, 24, 24)
        else:
            self.drag_handle.setGeometry(0, 0, 18, height)
            self.menu.setGeometry(19, (height - 24) // 2, 24, 24)
        paged = cap < count
        nav_x = self.width() - (NAV_WIDTH if paged else 0)
        for widget in (self.previous,self.next,self.counter):widget.setVisible(paged)
        nav_y = (height - 24) // 2 if height >= 60 else 0
        self.previous.setGeometry(nav_x + 5, nav_y, 24, 24)
        self.next.setGeometry(nav_x + 37, nav_y, 24, 24)
        self.counter.setGeometry(nav_x, height - 18, NAV_WIDTH, 16)
        self.previous.setEnabled(self.start > 0)
        self.next.setEnabled(self.start + cap < count)
        counter = f"{self.start + 1}–{self.start + cap}/{count}" if count else "0/0"
        self.counter.setText(counter)
        self.next.setToolTip(f"{counter} · próximos provedores · setas do teclado")
        self.previous.setToolTip(f"{counter} · provedores anteriores · setas do teclado")
        self.setAccessibleName(f"Cotas IA · {counter}")
        self.empty.setVisible(not count)
        self.empty.setGeometry(CONTROL_WIDTH, 0, max(0, nav_x - CONTROL_WIDTH), height)
        visible = self.order[self.start:self.start + cap]
        width = max(1, nav_x - CONTROL_WIDTH)
        previous = self.menu
        needs=[max(158,self.cells[pid].glance.minimum_width()+8,self.cells[pid].header_required_width()) for pid in visible]
        extra=max(0,width-sum(needs));x=CONTROL_WIDTH
        for i, pid in enumerate(visible):
            cell = self.cells[pid]
            end = x + needs[i] + round((i+1)*extra/max(1,cap))-round(i*extra/max(1,cap))
            cell.setGeometry(x, 0, end - x, height)
            cell.layout_body()  # font/height change without a size change
            cell.show()
            x=end
            QWidget.setTabOrder(previous, cell)
            previous = cell
            cell.update()
        QWidget.setTabOrder(previous, self.previous)
        QWidget.setTabOrder(self.previous, self.next)

    def page(self, delta):
        self.start = max(0, min(max(0, len(self.order) - self.policy.capacity), self.start + delta * self.policy.capacity))
        # Focus moves to the first new cell. No hidden provider is a dead end.
        self.menu.setFocus()
        self.arrange()
        if self.order:
            self.cells[self.order[self.start]].setFocus()

    def navigate_from(self, row_id, key):
        index = self.order.index(row_id)
        if key == Qt.Key_Home:
            index = 0
        elif key == Qt.Key_End:
            index = len(self.order) - 1
        else:
            index = max(0, min(len(self.order) - 1, index + (1 if key == Qt.Key_Right else -1)))
        self.menu.setFocus()
        if not self.start <= index < self.start + self.policy.capacity:
            self.start = max(0, min(index, len(self.order) - self.policy.capacity))
        self.arrange()
        self.cells[self.order[index]].setFocus()
