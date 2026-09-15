from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from . import theme, ui_motion
from .formatting import (
    age_label,
    age_seconds,
    friendly_window_label,
    percent_label,
    reset_label,
    reset_label_absolute,
)
from .snapshot_store import SnapshotStore

DEFAULT_PALETTE = theme.palette_for(theme.DEFAULT_SURFACE_PRESET)

# Tamanhos em px antes da escala geral. Detalhe subiu de 10 para 12 e a linha
# de status de 10 para 11 (pedido do <USUARIO> 260913: "aumente a fonte de detalhes").
DEFAULT_TYPOGRAPHY = {"family": theme.FONT_FAMILY, "name": 12, "value": 19, "hint": 11, "detail": 12}
DEFAULT_OPTIONS = {"number_mode": "used", "reset_mode": "relative", "show_pacing": True}

# Ordem fixa das barras no card: menor janela em cima (5 h) → maior embaixo (mês).
CATEGORY_ORDER = {"session": 0, "daily": 1, "weekly": 2, "monthly": 3}


def typography_from(settings) -> dict:
    return {
        "family": settings.font_family,
        "name": settings.size_name,
        "value": settings.size_value,
        "hint": settings.size_hint,
        "detail": settings.size_detail,
    }


def options_from(settings) -> dict:
    return {
        "number_mode": settings.number_mode,
        "reset_mode": settings.reset_mode,
        "show_pacing": settings.show_pacing,
    }


def _number(value: float) -> str:
    """16,01 -> "16"; 4,26 -> "4,3". Vírgula decimal, sem falsa precisão."""
    if value >= 10:
        return str(round(value))
    text = f"{value:.1f}".replace(".", ",")
    return text[:-2] if text.endswith(",0") else text


def pacing_text(window_pacing: dict | None) -> str:
    """Ritmo adaptativo (budget_pacing.window_pacing) em português de gente.
    "" quando não há leitura — nunca inventa número."""
    if not window_pacing:
        return ""
    status = window_pacing.get("status")
    if status in (None, "NAO_MEDIDO"):
        return ""
    if status == "pause":
        return "no limite"
    if status == "desacelerar":
        return "ritmo alto, desacelere"
    target = window_pacing.get("target_per_business_day")
    unit = "dia"  # dias corridos até o reset, não dia útil de calendário
    if target is None:
        target = window_pacing.get("target_per_hour")
        unit = "h"
    if target is None:
        return "ritmo ok"
    return f"dá ~{_number(target)}%/{unit}"


class IdentityDot(QWidget):
    """Pontinho de identidade: a cor nunca muda com o tema; só o contorno
    muda, pra não sumir num painel claro (#d7dde5 sobre Papel ~1,1:1)."""

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self._ring = QColor(0, 0, 0, 0)
        self.set_diameter(8)

    def set_diameter(self, px: int):
        self.setFixedSize(px, px)
        self.update()

    def set_ring(self, rgba):
        self._ring = QColor(*rgba)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self._ring)
        painter.setBrush(QColor(self.color))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        painter.end()


class PercentTrack(QWidget):
    """Barra de percentual com preenchimento animado (overshoot elástico).

    O percentual é desenhado DENTRO da barra, alinhado à esquerda — colado
    no rótulo da janela, do lado de fora. Valor longe da barra a que pertence
    obriga o olho a reassociar; junto, lê direto (Gestalt proximidade).

    ``_percent`` é o valor lógico final; ``_shown`` é o que está desenhado
    no momento — durante a animação passa do alvo e volta, cartoon style.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = None
        self._shown = None
        self._color = theme.STATUS_GREY
        self._background = theme.TRACK_BG
        self._anim = None
        self._text = ""
        self._text_px = 11
        self._text_family = theme.FONT_FAMILY
        self._empty_text_color = QColor(160, 166, 176)
        self.setFixedHeight(3)
        self.setMinimumWidth(40)

    def set_text_style(self, family: str, px: int, empty_color):
        self._text_family = family or theme.FONT_FAMILY
        self._text_px = max(8, int(px))
        self._empty_text_color = QColor(empty_color) if not isinstance(empty_color, QColor) else empty_color
        self.setFixedHeight(max(12, self._text_px + 5))
        self.update()

    def set_value(self, percent, color: str):
        # Leitura repetida (tique de idade, polling sem mudança) não reinicia
        # a animação: reiniciar de zero chamaria atenção a cada atualização.
        if percent == self._percent and color == self._color:
            return
        self._percent = percent
        self._color = color
        self._text = f"{round(percent)}%" if percent is not None else "—"
        start = self._shown if self._shown is not None else 0
        target = percent if percent is not None else None
        if self._anim is not None:
            # A animação anterior pode já ter sido deletada pelo deleteLater
            # do sinal finished; o ref Python sobrevive ao C++.
            try:
                self._anim.stop()
            except RuntimeError:
                pass
            self._anim = None
        if target is None:
            self._shown = None
            self.update()
            return
        self._anim = ui_motion.animate(
            self, float(start), float(target), 450,
            lambda v: (setattr(self, "_shown", float(v)), self.update()),
        )

    def set_background(self, rgba):
        self._background = rgba
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        radius = min(rect.height() / 2, 6)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*self._background))
        painter.drawRoundedRect(rect, radius, radius)
        fill_width = 0
        if self._shown is not None:
            fraction = max(0.0, min(1.0, self._shown / 100.0))
            fill_width = round(rect.width() * fraction)
            if self._percent and self._percent > 0 and fill_width > 0:
                fill_width = max(fill_width, rect.height())  # 1 % ainda aparece como um ponto
            if fill_width > 0:
                fill_rect = rect.adjusted(0, 0, -(rect.width() - fill_width), 0)
                painter.setBrush(QColor(self._color))
                painter.drawRoundedRect(fill_rect, radius, radius)
        # Texto do percentual: sempre à esquerda, na mesma posição — não
        # persegue o fim do preenchimento (posição estável lê melhor).
        if self._text:
            font = QFont(self._text_family)
            font.setPixelSize(self._text_px)
            font.setBold(True)
            painter.setFont(font)
            text_rect = rect.adjusted(self._text_px // 2 + 2, 0, 0, 0)
            if fill_width >= painter.fontMetrics().horizontalAdvance(self._text) + self._text_px:
                # O preenchimento claro passa por baixo do texto: escuro.
                painter.setPen(QColor(26, 29, 34))
            else:
                painter.setPen(self._empty_text_color)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self._text)
        painter.end()


class CardHandle(QWidget):
    """Cabçalho do card: segurar (ou arrastar) o nome transforma o provedor
    em bolinha — os eventos vão direto pro MainWindow, que conduz o arraste."""

    def __init__(self, row_id: str, drag_hook, parent=None):
        super().__init__(parent)
        self._row_id = row_id
        self._hook = drag_hook
        self.setCursor(Qt.OpenHandCursor)

    def _phase(self, event, phase):
        if self._hook is not None:
            self._hook(self._row_id, phase, event.globalPosition().toPoint(), "card")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._phase(event, "press")
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._phase(event, "move")
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._phase(event, "release")
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WindowBar(QWidget):
    """Uma linha por janela de cota (5 h / dia / semana / mês).

    Tudo da janela vive aqui: rótulo + barra + % sempre; renovação e ritmo
    aparecem no fim da MESMA linha quando os detalhes estão expandidos —
    nada de bloco separado repetindo o que a barra já disse.
    """

    def __init__(self, window: dict, parent=None):
        super().__init__(parent)
        self._category = theme.window_category(window)
        used = window.get("used_percent")

        label_text = theme.WINDOW_CATEGORY_LABELS.get(self._category) or friendly_window_label(window.get("label"))
        self._label = QLabel(label_text)
        self._track = PercentTrack(self)
        self._track.setMinimumWidth(40)
        # Portador oculto do % (alertas/testes leem); o texto visível vive
        # DENTRO da barra, colado no rótulo — perto do que explica.
        self._pct = QLabel(percent_label(used) if used is not None else "—")
        self._pct.hide()
        self._extra = QLabel("")
        self._extra.setWordWrap(False)
        self._track.set_value(used, theme.window_category_color(self._category))

        # Coluna: rótulo + barra na linha de cima; renovação/ritmo embaixo.
        # Largura mínima ESTÁVEL (rótulo+barra), o que impede o ciclo em que
        # barras lado a lado inflariam o sizeHint do card e vice-versa.
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        top = QWidget(self)
        top_row = QHBoxLayout(top)
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(7)
        top_row.addWidget(self._label)
        top_row.addWidget(self._track, 1)
        column.addWidget(top)
        column.addWidget(self._extra)
        friendly = friendly_window_label(window.get("label"))
        self.setToolTip(friendly if friendly else label_text)

    def set_extra(self, parts: list[str]):
        self._extra.setText(" · ".join(part for part in parts if part))

    def set_expanded(self, expanded: bool):
        self._extra.setVisible(bool(self._extra.text()) and expanded)

    def apply_style(self, palette: dict, typo: dict, scale: float):
        family = str(typo.get("family") or theme.FONT_FAMILY).replace("'", "")
        px_hint = max(1, round(typo["hint"] * scale))
        px_detail = max(1, round(typo["detail"] * scale))
        self._label.setStyleSheet(
            f"color:{palette['text_secondary']}; font-family:'{family}'; font-size:{px_hint}px;"
        )
        self._pct.setStyleSheet(
            f"color:{palette['text']}; font-family:'{family}'; font-size:{px_detail}px;"
        )
        self._extra.setStyleSheet(
            f"color:{palette['text_secondary']}; font-family:'{family}'; font-size:{px_detail}px;"
        )
        # A fonte do % dentro da barra segue a de hint: tamanho controlável
        # nas Configurações, e a barra cresce junto com a fonte.
        self._track.set_text_style(family, px_hint, palette["text_secondary"])
        self._track.set_background(palette.get("track_bg", theme.TRACK_BG))


class ProviderSegment(QFrame):
    """Um card de provedor: área modular com borda própria.

    Uma linha por janela de cota (``WindowBar``) carrega tudo daquela janela:
    rótulo, barra, % e — expandido — renovação e ritmo no fim da mesma linha.
    O aninhamento deixa o Spark DENTRO do card do Codex enquanto os dois
    estiverem visíveis.

    ``provider_id`` é a linha de tela; ``store_key`` é a fonte consultada
    (Spark lê do Codex) e ``window_filter`` recorta as janelas dessa linha.
    """

    def __init__(self, provider_id: str, label: str, parent: QWidget, drag_hook=None):
        super().__init__(parent)
        self.setObjectName("vendorCard")
        self.provider_id = provider_id
        self.store_key = theme.row_source(provider_id)
        self.window_filter = theme.row_window_filter(provider_id)
        self._scale = 1.0
        self._palette = DEFAULT_PALETTE
        self._typo = dict(DEFAULT_TYPOGRAPHY)
        self._options = dict(DEFAULT_OPTIONS)
        self._last_display: tuple | None = None
        self._last_pacing: dict | None = None
        self._bars: list[WindowBar] = []
        self._nested: ProviderSegment | None = None

        self._root = QVBoxLayout(self)
        self._root.setSpacing(3)

        self._name_wrap = CardHandle(provider_id, drag_hook, self)
        name_layout = QHBoxLayout(self._name_wrap)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(7)
        self._dot = IdentityDot(theme.PROVIDER_DOT_COLORS.get(provider_id, "#ffffff"), self._name_wrap)
        self._name = QLabel(label)
        # Portador oculto do % da pior janela (alertas/testes leem). O número
        # grande solto saiu da tela: % longe da barra confunde a que ele se
        # refere — cada % vive dentro da sua barra agora.
        self._value = QLabel("—")
        self._value.hide()
        name_layout.addWidget(self._dot, 0, Qt.AlignVCenter)
        name_layout.addWidget(self._name)
        name_layout.addStretch(1)
        self._name_wrap.setToolTip(label)

        self._hint = QLabel("aguardando consulta")
        self._hint.setWordWrap(False)

        # Barra-resumo da pior janela: mantida fora do layout (260914,
        # pedido do <USUARIO> — só as barras por janela aparecem). Continua
        # existindo porque carrega a COR DE ESTADO que alertas e testes leem.
        self._track = PercentTrack(self)
        self._track.setFixedHeight(3)
        self._track.hide()

        # Barras por janela: EMPILHAM quando o card é estreito e ficam LADO A
        # LADO quando há largura — a box usa horizontalidade e verticalidade.
        self._bars_wrap = QWidget(self)
        self._bars_layout = QVBoxLayout(self._bars_wrap)
        self._bars_layout.setSpacing(3)
        self._bars_horizontal = False

        self._root.addWidget(self._name_wrap)
        self._root.addWidget(self._hint)
        self._root.addWidget(self._bars_wrap)
        # Card esticado à altura do mais alto da fileira: a sobra fica aqui,
        # embaixo — nome, status e barras continuam colados no topo.
        self._root.addStretch(1)
        self._expanded = False

        self._restyle()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_bars()

    def _relayout_bars(self):
        """Alterna as barras entre empilhadas (vertical) e lado a lado.

        Critério: cada barrinha precisa de ~150 px escalados pra ser legível;
        se todas cabem na largura interna do card, dividem a linha em partes
        iguais — nada de fonte ou escala mudando sozinho, só organização.
        """
        if not self._bars:
            return
        available = self.width() - self._px(20)
        wanted = len(self._bars) * self._px(150) + (len(self._bars) - 1) * self._px(6)
        horizontal = wanted <= available
        if horizontal == self._bars_horizontal:
            return
        self._bars_horizontal = horizontal
        old_wrap = self._bars_wrap
        self._bars_wrap = QWidget(self)
        layout = QHBoxLayout() if horizontal else QVBoxLayout()
        layout.setSpacing(self._px(6))
        if not horizontal:
            layout.setContentsMargins(self._px(16), self._px(2), 0, 0)
        self._bars_wrap.setLayout(layout)
        self._bars_layout = layout
        for bar in self._bars:
            bar.setParent(self._bars_wrap)
            layout.addWidget(bar, 1 if horizontal else 0)
        self._root.replaceWidget(old_wrap, self._bars_wrap)
        old_wrap.deleteLater()
        self._bars_wrap.show()
        for bar in self._bars:
            bar.set_expanded(self._expanded)

    # ------------------------------------------------------------ aninhamento (Spark no Codex)

    def set_nested(self, child: "ProviderSegment"):
        if self._nested is child:
            return
        self.clear_nested()
        self._nested = child
        child.setProperty("nested", True)
        child._restyle()
        # Antes do stretch final: o Spark encosta nas barras do Codex, não
        # desce até a base do card esticado.
        self._root.insertWidget(self._root.count() - 1, child)
        child.show()

    def clear_nested(self):
        if self._nested is None:
            return
        self._nested.setProperty("nested", False)
        self._nested._restyle()
        self._nested.hide()
        self._nested = None

    # ------------------------------------------------------------ API de configuração

    def set_expanded(self, expanded: bool):
        self._expanded = bool(expanded)
        for bar in self._bars:
            bar.set_expanded(self._expanded)

    def apply_scale(self, scale: float):
        self._scale = scale
        self._restyle()

    def apply_theme(self, palette: dict):
        self._palette = palette
        self._restyle()
        self._rerender()

    def configure(self, typography: dict | None = None, options: dict | None = None):
        if typography:
            self._typo.update({k: v for k, v in typography.items() if v is not None})
        if options:
            self._options.update({k: v for k, v in options.items() if v is not None})
        self._restyle()
        self._rerender()

    def _rerender(self):
        if self._last_display is not None:
            self._render(self._last_display, self._last_pacing)

    def _px(self, base: float) -> int:
        return max(1, round(base * self._scale))

    def _font_css(self, key: str) -> str:
        family = str(self._typo.get("family") or theme.FONT_FAMILY).replace("'", "")
        return f"font-family:'{family}'; font-size:{self._px(self._typo[key])}px;"

    def _restyle(self):
        text = self._palette["text"]
        secondary = self._palette["text_secondary"]
        nested = bool(self.property("nested"))
        if nested:
            self._root.setContentsMargins(7, 5, 7, 5)
        else:
            self._root.setContentsMargins(10, 8, 10, 8)
        card_bg = "rgba(0,0,0,0.05)" if self._palette.get("light") else "rgba(255,255,255,0.05)"
        radius = 8 if nested else 10
        self.setStyleSheet(
            f"#vendorCard {{ background-color: {card_bg}; border: 1px solid {self._palette['border']};"
            f" border-radius: {radius}px; }}"
        )
        self._dot.set_diameter(max(6, self._px(self._typo["name"] * 0.72)))
        self._dot.set_ring(self._palette.get("dot_ring", (0, 0, 0, 0)))
        self._name.setStyleSheet(f"color:{text}; font-weight:600; {self._font_css('name')}")
        self._value.setStyleSheet(f"color:{text}; {self._font_css('value')}")
        self._value.setMinimumWidth(self._px(self._typo["value"] * 2.7))
        self._hint.setStyleSheet(f"color:{secondary}; {self._font_css('hint')}")
        self._track.set_background(self._palette.get("track_bg", theme.TRACK_BG))
        self._track.setFixedHeight(3)
        self._track.setMinimumWidth(40)
        # Barrinhas alinhadas com o texto do nome (pulando o pontinho) quando
        # empilhadas; lado a lado, começam na borda pra aproveitar a largura.
        if self._bars_horizontal:
            self._bars_layout.setContentsMargins(0, self._px(2), 0, 0)
        else:
            self._bars_layout.setContentsMargins(self._px(16), self._px(2), 0, 0)
        for bar in self._bars:
            bar.apply_style(self._palette, self._typo, self._scale)

    # ------------------------------------------------------------ opções de exibição

    def _remaining_mode(self) -> bool:
        return self._options.get("number_mode") == "remaining"

    def _shown_percent(self, used):
        if used is None:
            return None
        return max(0.0, 100.0 - used) if self._remaining_mode() else used

    def _value_text(self, used) -> str:
        shown = self._shown_percent(used)
        text = percent_label(shown)
        if shown is not None and self._remaining_mode():
            return f"{text}<span style='font-size:{self._px(self._typo['hint'])}px'> livre</span>"
        return text

    def _reset_text(self, iso_value) -> str:
        if self._options.get("reset_mode") == "absolute":
            return reset_label_absolute(iso_value)
        return reset_label(iso_value)

    # ------------------------------------------------------------ render

    def show_querying(self):
        self._last_display = None
        self._value.setText("—")
        self._track.set_value(None, self._palette["status"]["grey"])
        self._hint.setText("consultando…")
        self._hint.setToolTip("")
        self._clear_bars()

    def update_from_store(self, store: SnapshotStore, expanded: bool, pacing: dict | None = None):
        display = store.display(self.store_key, self.window_filter)
        worst = store.worst_window(self.store_key, self.window_filter) if display is not None else None
        self._name.setText(theme.PROVIDER_LABELS.get(self.provider_id, self.provider_id))
        self._last_display = (display, worst)
        self._last_pacing = pacing
        self._render((display, worst), pacing)

    def _update_name_tooltip(self, display: dict | None):
        label = theme.PROVIDER_LABELS.get(self.provider_id, self.provider_id)
        lines = [label]
        if display is not None:
            if display.get("message"):
                lines.append(display["message"])
            if display.get("source"):
                lines.append(f"Fonte: {display['source']}")
            if display.get("fetched_at"):
                lines.append(f"Leitura: {age_label(display['fetched_at'])}")
        self._name_wrap.setToolTip("\n".join(lines))
        self._name_wrap.setAccessibleName(" · ".join(lines))

    def _render(self, display_and_worst, pacing: dict | None = None):
        display, worst = display_and_worst
        status_colors = self._palette["status"]
        self._update_name_tooltip(display)

        if display is None:
            self._value.setText("—")
            self._track.set_value(None, status_colors["grey"])
            self._hint.setText("aguardando consulta")
            self._hint.setToolTip("")
            self._clear_bars()
            return

        status = display["status"]
        stale_age = age_seconds(display["fetched_at"]) if display["stale"] else None
        color = theme.stale_aware_track_color(
            status, worst["used_percent"] if worst else None, display["stale"], stale_age, status_colors
        )

        if worst is not None:
            self._value.setText(self._value_text(worst["used_percent"]))
            self._track.set_value(self._shown_percent(worst["used_percent"]), color)
            # Sem repetir o nome da janela: qual é a pior já se vê pela barra
            # mais cheia; a linha de status só acrescenta renovação e idade.
            if status == "ok":
                hint = f"{self._reset_text(worst['resets_at'])} · {age_label(display['fetched_at'])}"
            else:
                short = theme.STATUS_SHORT_LABEL.get(status, status)
                age = f" · dado de {age_label(display['fetched_at'])}" if display["stale"] else ""
                hint = f"{short}{age}"
        else:
            self._value.setText("—")
            self._track.set_value(None, color)
            if status == "ok":
                hint = "sem janela nesta conta"
            else:
                hint = theme.STATUS_SHORT_LABEL.get(status, status) or status

        self._hint.setText(hint)
        self._hint.setToolTip(display.get("message") or hint)
        self._rebuild_bars(display, pacing)

    def _clear_bars(self):
        self._bars = []
        while self._bars_layout.count():
            item = self._bars_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()

    def _rebuild_bars(self, display: dict, pacing: dict | None = None):
        self._clear_bars()
        pacing_windows = (pacing or {}).get("windows") or {}
        windows = sorted(
            display.get("windows") or [],
            key=lambda w: CATEGORY_ORDER.get(theme.window_category(w), 99),
        )
        for window in windows:
            bar = WindowBar(window, self._bars_wrap)
            bar.apply_style(self._palette, self._typo, self._scale)
            extras = [self._reset_text(window.get("resets_at"))]
            if self._options.get("show_pacing", True):
                extras.append(pacing_text(pacing_windows.get(window.get("id"))))
            bar.set_extra(extras)
            bar.set_expanded(self._expanded)
            self._bars_layout.addWidget(bar)
            self._bars.append(bar)
