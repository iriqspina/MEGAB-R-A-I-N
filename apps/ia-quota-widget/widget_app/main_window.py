from datetime import datetime
import json
from math import ceil
import sys

from PySide6.QtCore import QPoint, QProcess, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPixmap, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from . import budget_status, paths, persistence, providers_bridge, screen_geometry, theme, ui_motion
from .contrast import hex_to_rgb
from .demo_data import demo_snapshot
from .formatting import age_label, friendly_window_label, percent_label
from .poll_backoff import PollBackoff
from .snapshot_store import SnapshotStore
from .ui_dock import DOCK_WIDTH, DockRail, DragBall
from .ui_flow import FlowLayout
from .ui_provider_segment import ProviderSegment, options_from, typography_from

POLL_INTERVAL_MS = 120_000
MANUAL_REFRESH_COOLDOWN_MS = 5_000

# Arraste de card/bolinha: 10 px de distância OU segurar 320 ms no nome —
# "clicar e segurar" também desperta a bolinha, como o <USUARIO> pediu.
DRAG_THRESHOLD_PX = 10
DRAG_HOLD_MS = 320

# Borda invisível (alfa 1) em volta do painel: é ela que redimensiona, como a
# borda de arraste do Windows 11 fica fora do contorno visível da janela.
# Alfa 0 deixaria o clique atravessar para a janela de trás.
RESIZE_GRIP = 7
RESIZE_CORNER = 18
MIN_WINDOW_SIZE = QSize(240, 150)

# Da borda da janela até o fluxo de cards: 2 bordas de arraste (RESIZE_GRIP),
# margens horizontais do painel (16+16), dock de bolinhas (DOCK_WIDTH) e o
# espaçamento do body_row (4). Serve pra medir o fluxo pela LARGURA ALVO da
# janela — a geometria real dos filhos ainda não existe antes do show().
FLOW_CHROME_W = 2 * RESIZE_GRIP + 32 + DOCK_WIDTH + 4

POLL_MINUTE_STEPS = (2, 5, 10, 15, 30)
ALERT_STEPS = (0, 75, 90)
HOVER_MODES = ("none", "opaque", "fade")
FADE_OPACITY = 0.35


def _make_tray_icon(bg_hex: str) -> QIcon:
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(*hex_to_rgb(bg_hex)))
    painter.setPen(QColor(255, 255, 255, 120))
    painter.drawEllipse(1, 1, 14, 14)
    painter.end()
    return QIcon(pixmap)


class DragHeader(QWidget):
    def __init__(self, on_drag_end, on_double_click=None, can_drag=None, snap=None, parent=None):
        super().__init__(parent)
        self._on_drag_end = on_drag_end
        self._on_double_click = on_double_click
        self._can_drag = can_drag or (lambda: True)
        self._snap = snap
        self._press_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._can_drag():
            self._press_pos = event.globalPosition().toPoint() - self.window().pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and event.buttons() & Qt.LeftButton:
            target = event.globalPosition().toPoint() - self._press_pos
            if self._snap is not None:
                target = self._snap(target)
            self.window().move(target)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._press_pos is not None:
            self._press_pos = None
            self._on_drag_end()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._on_double_click is not None:
            self._on_double_click()
        super().mouseDoubleClickEvent(event)


class MainWindow(QWidget):
    def __init__(self, demo: bool = False, session_only: bool = False):
        super().__init__()
        self.demo = demo
        self._session_only = session_only
        self._programmatic_resize = False
        self._user_resize_active = False
        self._resize_edges = None
        self._press_global = None
        self._press_geometry = None
        self._hovering = False
        self._minimized = False
        self._alerted: set = set()
        self._settings_dialog = None
        self._tray = None
        self._backoff = PollBackoff()
        self._retry_timers = {}
        self.settings = persistence.load_settings()
        self._sanitize_settings()
        self.store = SnapshotStore()
        # provider_ids = linhas de tela (inclui "spark"), já na ordem escolhida;
        # a consulta usa a fonte de cada linha (theme.row_source).
        self._source_ids = providers_bridge.provider_ids()
        self.provider_ids = self._ordered_rows()
        self._pacing_module = providers_bridge.load_pacing_module()
        self._pacing_by_provider: dict[str, dict] = {}
        self.poller = providers_bridge.ProviderPoller(self)
        self.poller.snapshot_ready.connect(self._on_snapshot)
        self._segments: dict[str, ProviderSegment] = {}
        self._querying: set[str] = set()
        self._manual_refresh_locked = False
        self._last_attempt = None
        self._drag_state: dict | None = None
        self._ghost: DragBall | None = None
        self._pending_hide: tuple[str, object] | None = None
        self._canonical_labels = {**theme.PROVIDER_LABELS, **providers_bridge.provider_labels()}

        self.setWindowFlags(self._window_flags())
        self.setWindowTitle("Cotas IA")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._size_save_timer = QTimer(self)
        self._size_save_timer.setSingleShot(True)
        self._size_save_timer.setInterval(400)
        self._size_save_timer.timeout.connect(self._save_settings)
        self._resize_watch_timer = QTimer(self)
        self._resize_watch_timer.setInterval(100)
        self._resize_watch_timer.timeout.connect(self._watch_resize_end)

        self._build_ui()
        self._apply_panel_style()
        self._apply_theme_everywhere()
        self._rebuild_segments()
        self._shortcuts = []
        for key, callback in (("F5", self.manual_refresh), ("Ctrl+D", self._toggle_expanded),
                              ("Ctrl+,", self.open_settings), ("Ctrl+T", self._toggle_always_on_top),
                              ("Ctrl+0", self._fit_to_content)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self._shortcuts.append(shortcut)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(_make_tray_icon(self._preset()["bg"]), self)
            tray_menu = QMenu()
            tray_menu.addAction("Mostrar", self._show_from_tray)
            tray_menu.addAction("Configurações…", self.open_settings)
            tray_menu.addSeparator()
            self._tray_click_action = tray_menu.addAction("Atravessar cliques", self._toggle_click_through)
            self._tray_click_action.setCheckable(True)
            tray_menu.addAction("Sair", self._quit)
            self._tray.setContextMenu(tray_menu)
            self._tray_menu = tray_menu
            self._tray.activated.connect(self._on_tray_activated)
            self._tray.setToolTip("Cotas IA")

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self.poll_now)
        self._poll_timer.start(self._poll_interval_ms())
        self._feedback_timer = QTimer(self)
        self._feedback_timer.timeout.connect(self._refresh_ages)
        self._feedback_timer.start(30_000)
        self._update_mcp_status()
        self._sync_tray()

        QGuiApplication.instance().screenAdded.connect(self._reclamp_position)
        QGuiApplication.instance().screenRemoved.connect(self._reclamp_position)

    # ------------------------------------------------------------------
    # configurações
    # ------------------------------------------------------------------

    def _sanitize_settings(self):
        s = self.settings

        def clamp_int(value, low, high, default):
            try:
                return max(low, min(high, int(value)))
            except (TypeError, ValueError):
                return default

        s.font_family = str(s.font_family or theme.FONT_FAMILY)
        s.size_name = clamp_int(s.size_name, 8, 32, 12)
        s.size_value = clamp_int(s.size_value, 10, 48, 19)
        s.size_hint = clamp_int(s.size_hint, 8, 28, 11)
        s.size_detail = clamp_int(s.size_detail, 8, 28, 12)
        s.bg_opacity_percent = clamp_int(s.bg_opacity_percent, 20, 100, 76)
        if s.number_mode not in ("used", "remaining"):
            s.number_mode = "used"
        if s.reset_mode not in ("relative", "absolute"):
            s.reset_mode = "relative"
        if s.poll_minutes not in POLL_MINUTE_STEPS:
            s.poll_minutes = 2
        if s.alert_percent not in ALERT_STEPS:
            s.alert_percent = 0
        if s.hover_mode not in HOVER_MODES:
            s.hover_mode = "none"
        if s.layout not in ("horizontal", "vertical"):
            s.layout = "horizontal"
        if not isinstance(s.provider_order, list):
            s.provider_order = []
        if s.surface_preset not in theme.SURFACE_PRESETS:
            s.surface_preset = theme.DEFAULT_SURFACE_PRESET

    def _ordered_rows(self) -> list[str]:
        rows = theme.expand_rows(self._source_ids)
        order = [row for row in (self.settings.provider_order or []) if row in rows]
        return order + [row for row in rows if row not in order]

    def _poll_interval_ms(self) -> int:
        return self.settings.poll_minutes * 60_000

    def update_settings(self, changes: dict):
        """Aplica mudanças das Configurações na hora e salva."""
        flags_before = (self.settings.always_on_top, self.settings.click_through)
        for key, value in changes.items():
            if key == "visible_providers":
                self.settings.visible_providers = dict(value)
            elif key == "provider_order":
                self.settings.provider_order = list(value)
            elif hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self._sanitize_settings()
        self.provider_ids = self._ordered_rows()
        if self._poll_timer.interval() != self._poll_interval_ms():
            self._poll_timer.start(self._poll_interval_ms())
        self._details_btn.setText("▴" if self.settings.expanded else "▾")
        self._footer.setVisible(self.settings.show_footer)
        self._apply_theme_everywhere()
        self._rebuild_segments()
        if (self.settings.always_on_top, self.settings.click_through) != flags_before:
            self._reapply_window_flags()
        self._sync_top_button()
        self._sync_tray()
        self._update_refresh_feedback()
        self._save_settings()

    def open_settings(self, show: bool = True):
        from .settings_dialog import SettingsDialog

        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self)
        self._settings_dialog.begin_session()
        if show:
            self._settings_dialog.show()
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
        return self._settings_dialog

    # ------------------------------------------------------------------
    # tema / paleta
    # ------------------------------------------------------------------

    def _preset(self) -> dict:
        return theme.surface_preset(self.settings.surface_preset)

    def _palette(self) -> dict:
        return theme.palette_for(self.settings.surface_preset)

    def _apply_theme_everywhere(self):
        palette = self._palette()
        self._apply_panel_style()
        self._style_header(palette)
        typography, options = typography_from(self.settings), options_from(self.settings)
        for segment in self._segments.values():
            segment.configure(typography, options)
            segment.apply_theme(palette)
        self.dock.apply_theme(palette)
        if self._tray_exists():
            self._tray.setIcon(_make_tray_icon(self._preset()["bg"]))

    def _tray_exists(self) -> bool:
        return getattr(self, "_tray", None) is not None

    def _style_header(self, palette: dict):
        family = self.settings.font_family.replace("'", "")
        small = max(9, self.settings.size_hint - 1)
        font = f"font-family:'{family}'; font-size:{small}px;"
        self._drag_glyph.setStyleSheet(f"color:{palette['text_secondary']};")
        self._title.setStyleSheet(f"color:{palette['text_secondary']}; {font} letter-spacing:1px;")
        self._refresh_status.setStyleSheet(f"color:{palette['text_secondary']}; {font}")
        self._mcp_status.setStyleSheet(f"color:{palette['text_secondary']}; {font}")
        self._empty_label.setStyleSheet(f"color:{palette['text']}; font-family:'{family}'; font-size:{small + 1}px;")
        for btn in (self._top_btn, self._options_btn, self._close_btn, self._details_btn,
                    self._refresh_btn, self._empty_btn):
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {palette['text_secondary']}; border: 1px solid transparent; border-radius:3px; {font} }}"
                f"QPushButton:hover, QPushButton:checked {{ color: {palette['text']}; }}"
                f"QPushButton:focus {{ border: 1px solid {palette['text']}; }}"
            )
        r, g, b = hex_to_rgb(palette["text_secondary"])

    def _set_surface_preset(self, preset_id: str):
        self.settings.surface_preset = preset_id
        self._apply_theme_everywhere()
        self._save_settings()

    # ------------------------------------------------------------------
    # janela / layout
    # ------------------------------------------------------------------

    def _window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.settings.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        if self.settings.click_through:
            flags |= Qt.WindowTransparentForInput
        return flags

    def _reapply_window_flags(self):
        was_visible = self.isVisible()
        self._programmatic_resize = True
        try:
            self.setWindowFlags(self._window_flags())
            if was_visible:
                self.show()
        finally:
            self._programmatic_resize = False

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(RESIZE_GRIP, RESIZE_GRIP, RESIZE_GRIP, RESIZE_GRIP)

        self.panel = QFrame(self)
        self.panel.setObjectName("panel")
        # Cursor explícito: sem ele os filhos herdariam a seta de redimensionar.
        self.panel.setCursor(Qt.ArrowCursor)
        outer.addWidget(self.panel)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(10)

        self.header = DragHeader(
            self._save_settings,
            on_double_click=self._fit_to_content,
            can_drag=lambda: not self.settings.lock_position,
            snap=self._snap_drag,
        )
        self.header.setToolTip(
            "Arraste para mover · bordas redimensionam · duplo clique ajusta ao conteúdo\n"
            "Segure ou arraste o nome de um provedor para guardá-lo no dock de bolinhas"
        )
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        self._drag_glyph = QLabel("⠿")
        self._title = QLabel("COTAS IA")
        header_layout.addWidget(self._drag_glyph)
        header_layout.addWidget(self._title)
        header_layout.addStretch(1)

        self._top_btn = self._make_header_button("◇" if not self.settings.always_on_top else "◆", "Sempre acima")
        self._top_btn.clicked.connect(self._toggle_always_on_top)
        self._top_btn.setCheckable(True)
        self._sync_top_button()
        self._details_btn = self._make_header_button("▴" if self.settings.expanded else "▾", "Expandir ou recolher detalhes (Ctrl+D)")
        self._details_btn.clicked.connect(self._toggle_expanded)
        self._options_btn = self._make_header_button("Opções", "Configurações, provedores e tema (Ctrl+,)")
        self._options_btn.setFixedWidth(52)
        self._options_btn.clicked.connect(self._show_menu)
        self._close_btn = self._make_header_button("×", "Fechar")
        self._close_btn.clicked.connect(self._quit)
        header_layout.addWidget(self._top_btn)
        header_layout.addWidget(self._details_btn)
        header_layout.addWidget(self._options_btn)
        header_layout.addWidget(self._close_btn)

        panel_layout.addWidget(self.header)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        # Cards em FLUXO: janela larga -> colunas; estreita -> uma coluna.
        # Sem barra de rolagem: o mínimo da janela é o conteúdo inteiro.
        self.body = QWidget(self._content)
        self._body_layout = FlowLayout(self.body, margin=0, spacing=8)
        content_layout.addWidget(self.body)

        self._empty = QWidget(self._content)
        empty_layout = QVBoxLayout(self._empty)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        self._empty_label = QLabel("Nenhum provedor visível")
        self._empty_btn = QPushButton("Escolher provedores…")
        self._empty_btn.clicked.connect(self._show_providers_menu)
        empty_layout.addWidget(self._empty_label)
        empty_layout.addWidget(self._empty_btn)
        content_layout.addWidget(self._empty)
        content_layout.addStretch(1)
        self._content.setAutoFillBackground(False)

        self.dock = DockRail(self.panel, self._card_drag)
        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(4)
        body_row.addWidget(self.dock)
        body_row.addWidget(self._content, 1)
        panel_layout.addLayout(body_row, 1)

        self._footer = QWidget(self.panel)
        footer = QHBoxLayout(self._footer)
        footer.setContentsMargins(0, 0, 0, 0)
        self._refresh_status = QLabel("Aguardando consulta")
        self._refresh_btn = self._make_header_button("↻", "Atualizar agora (F5)")
        self._refresh_btn.clicked.connect(self.manual_refresh)
        footer.addWidget(self._refresh_status)
        self._mcp_status = QLabel("MCP: sem medição")
        self._mcp_status.setToolTip("Saúde das conexões MCP: configurado, conectado e bloqueios que exigem ação.")
        footer.addWidget(self._mcp_status)
        footer.addStretch(1)
        footer.addWidget(self._refresh_btn)
        panel_layout.addWidget(self._footer)
        self._footer.setVisible(self.settings.show_footer)

        self._demo_banner = None
        if self.demo:
            self._demo_banner = QLabel("MODO DEMO — dados fictícios, não é conexão real")
            self._demo_banner.setStyleSheet("color:#e0b46a; font-size:10px;")
            panel_layout.addWidget(self._demo_banner)

    def _make_header_button(self, glyph: str, tooltip: str) -> QPushButton:
        btn = QPushButton(glyph)
        btn.setToolTip(tooltip)
        btn.setAccessibleName(tooltip)
        btn.setFocusPolicy(Qt.StrongFocus)
        btn.setFixedSize(20, 20)
        return btn

    def _update_mcp_status(self):
        try:
            payload = json.loads(paths.MCP_HEALTH_PATH.read_text(encoding="utf-8"))
            summary = payload.get("summary") or {}
            label = f"MCP: {summary.get('OK', 0)} OK"
            if summary.get("AUTH_REQUIRED", 0):
                label += f" · {summary['AUTH_REQUIRED']} login"
            if summary.get("PLAN_REQUIRED", 0):
                label += f" · {summary['PLAN_REQUIRED']} plano"
            if summary.get("UNREACHABLE", 0):
                label += f" · {summary['UNREACHABLE']} offline"
            self._mcp_status.setText(label)
        except (OSError, ValueError, TypeError):
            self._mcp_status.setText("MCP: sem medição")

    def _rebuild_segments(self, animate_rows: set[str] | None = None):
        while self._body_layout.count():
            self._body_layout.takeAt(0)

        typography, options = typography_from(self.settings), options_from(self.settings)
        for provider_id in self.provider_ids:
            if provider_id not in self._segments:
                label = self._canonical_labels.get(provider_id, provider_id)
                segment = ProviderSegment(provider_id, label, self.body, drag_hook=self._card_drag)
                self._segments[provider_id] = segment

        for segment in self._segments.values():
            segment.hide()
            segment.clear_nested()
            if segment.graphicsEffect() is not None:
                segment.setGraphicsEffect(None)

        visible = {pid for pid in self.provider_ids if self.settings.is_visible(pid)}
        # Spark mora DENTRO do card do Codex quando os dois estão visíveis;
        # sem o Codex (ou se o <USUARIO> tirar um dos dois) cada um ocupa o
        # próprio espaço — nada de slot fixo "reservado".
        top_rows = [pid for pid in self.provider_ids
                    if pid in visible and not (pid == "spark" and "codex" in visible)]

        for provider_id in visible:
            segment = self._segments[provider_id]
            segment.configure(typography, options)
            segment.apply_theme(self._palette())
            segment.set_expanded(self.settings.expanded)
            segment.apply_scale(self.settings.scale)

        for provider_id in top_rows:
            segment = self._segments[provider_id]
            if provider_id == "codex" and "spark" in visible:
                segment.set_nested(self._segments["spark"])
            self._body_layout.addWidget(segment)
            segment.show()
            if animate_rows and provider_id in animate_rows:
                ui_motion.pop_in(segment)

        self.dock.apply_theme(self._palette())
        self.dock.set_hidden([pid for pid in self.provider_ids if pid not in visible])

        self._refresh_all_segments()
        self._empty.setVisible(not top_rows)
        self._update_refresh_feedback()
        self._resize_to_content()

    # ------------------------------------------------------------------
    # arraste de card / bolinha (260914)
    # ------------------------------------------------------------------

    def _card_drag(self, row_id: str, phase: str, global_pos, source: str = "card"):
        if phase == "press":
            # Um hide pode estar a caminho (pop_out ainda animando); um novo
            # arraste deste row cancela o esconder pendente.
            self._cancel_pending_hide(row_id)
            timer = QTimer(self)
            timer.setSingleShot(True)
            state = {"row": row_id, "start": global_pos, "source": source, "active": False, "timer": timer}
            timer.timeout.connect(lambda: self._activate_drag(state))
            timer.start(DRAG_HOLD_MS)
            self._drag_state = state
        elif phase == "move":
            state = self._drag_state
            if state is None or state["row"] != row_id:
                return
            if not state["active"] and (global_pos - state["start"]).manhattanLength() >= DRAG_THRESHOLD_PX:
                self._activate_drag(state)
            if state["active"]:
                self._ghost.follow(global_pos)
                self.dock.set_drop_hint(global_pos, accepting=source == "card")
        elif phase == "release":
            state, self._drag_state = self._drag_state, None
            if state is None:
                return
            state["timer"].stop()
            if not state["active"]:
                return
            row, src = state["row"], state["source"]
            ghost, self._ghost = self._ghost, None
            over_dock = self.dock.contains_global(global_pos)
            hiding = over_dock and src == "card"
            acted = False
            try:
                if over_dock and src == "card":
                    self._hide_row(row)
                elif not over_dock and self._over_stack(global_pos):
                    if src == "dock":
                        acted = self._restore_row_at(row, global_pos)
                    else:
                        acted = self._reorder_row(row, global_pos)
            finally:
                if ghost is not None:
                    ghost.dismiss()
                self.dock.set_drop_hint(None, False)
                # No caminho do dock o rebuild só depois que o card termina
                # de encolher; no reorder/restore quem agiu já rebuildou —
                # rebuildar de novo aqui só causa flicker.
                if not hiding and not acted:
                    self._rebuild_segments()

    def _activate_drag(self, state: dict):
        if self._drag_state is not state or state["active"]:
            return
        state["active"] = True
        self._ghost = DragBall(self, state["row"])
        self._ghost.follow(state["start"])
        segment = self._segments.get(state["row"])
        if segment is not None:
            ui_motion.dim(segment, 0.35)

    def _over_stack(self, global_pos) -> bool:
        return self.body.rect().contains(self.body.mapFromGlobal(global_pos))

    def _top_card_rows(self) -> list[str]:
        rows: list[str] = []
        for index in range(self._body_layout.count()):
            widget = self._body_layout.itemAt(index).widget()
            if widget is not None:
                for row_id, segment in self._segments.items():
                    if segment is widget:
                        rows.append(row_id)
                        break
        return rows

    def _insertion_index(self, global_pos) -> int:
        # Leitura em fluxo (linha a linha, esquerda→direita): conta os cards
        # que estão acima do cursor OU na mesma fileira, à esquerda.
        count = 0
        for row_id in self._top_card_rows():
            segment = self._segments[row_id]
            center = segment.mapToGlobal(QPoint(segment.width() // 2, segment.height() // 2))
            if center.y() < global_pos.y() or (abs(center.y() - global_pos.y()) < 24 and center.x() < global_pos.x()):
                count += 1
        return count

    def _cancel_pending_hide(self, row_id: str):
        pending = self._pending_hide
        if pending is None or pending[0] != row_id:
            return
        self._pending_hide = None
        try:
            pending[1].stop()
        except RuntimeError:
            pass
        # O finish do pop_out é quem devolve NO_MAX; sem ele, devolve aqui.
        segment = self._segments.get(row_id)
        if segment is not None:
            segment.setMaximumHeight(ui_motion.NO_MAX)

    def _hide_row(self, row_id: str):
        segment = self._segments.get(row_id)
        if segment is not None and not segment.isHidden():
            def finish_hide():
                if self._pending_hide and self._pending_hide[0] == row_id:
                    self._pending_hide = None
                self._toggle_provider_visibility(row_id, False)

            anim = ui_motion.pop_out(segment, finish_hide)
            self._pending_hide = (row_id, anim)
        else:
            self._toggle_provider_visibility(row_id, False)

    def _reorder_row(self, row_id: str, global_pos) -> bool:
        visible = {pid for pid in self.provider_ids if self.settings.is_visible(pid)}
        if row_id == "spark" and "codex" in visible:
            return False  # aninhado no Codex: a posição dele é dentro do card
        top_rows = self._top_card_rows()
        index = self._insertion_index(global_pos)
        current = top_rows.index(row_id)
        if index in (current, current + 1):
            return False  # soltou no próprio lugar: nada a reordenar
        before = top_rows[index] if index < len(top_rows) else None
        order = [pid for pid in self.provider_ids if pid != row_id]
        if before is None:
            order.append(row_id)
        else:
            order.insert(order.index(before), row_id)
        self.update_settings({"provider_order": order})
        segment = self._segments.get(row_id)
        if segment is not None:
            ui_motion.pop_in(segment, duration=200)  # reassentamento do card movido
        return True

    def _restore_row_at(self, row_id: str, global_pos) -> bool:
        self._cancel_pending_hide(row_id)
        self._toggle_provider_visibility(row_id, True)
        self._reorder_row(row_id, global_pos)
        segment = self._segments.get(row_id)
        if segment is not None:
            ui_motion.pop_in(segment)
        return True

    def _refresh_all_segments(self):
        for provider_id, segment in self._segments.items():
            if self.settings.is_visible(provider_id):
                source = theme.row_source(provider_id)
                if source in self._querying:
                    segment.show_querying()
                else:
                    segment.update_from_store(self.store, self.settings.expanded, self._pacing_by_provider.get(source))

    def _visible_sources(self) -> list[str]:
        sources: list[str] = []
        for row_id in self.provider_ids:
            source = theme.row_source(row_id)
            if self.settings.is_visible(row_id) and source not in sources:
                sources.append(source)
        return sources

    def _refresh_ages(self):
        self._update_mcp_status()
        self._refresh_all_segments()
        self._update_refresh_feedback()
        self._schedule_fit()

    def _apply_panel_style(self):
        r, g, b = hex_to_rgb(self._preset()["bg"])
        alpha = self.settings.bg_opacity_percent / 100.0
        if self._hovering and self.settings.hover_mode == "opaque":
            alpha = 1.0
        self.panel.setStyleSheet(
            f"""
            #panel {{
                background-color: rgba({r}, {g}, {b}, {alpha});
                border: 1px solid {self._palette()['border']};
                border-radius: {theme.CORNER_RADIUS}px;
            }}
            """
        )

    # ------------------------------------------------------------------
    # posicionamento / tamanho / multi-monitor
    # ------------------------------------------------------------------

    def show_positioned(self):
        self._resize_to_content()
        point = screen_geometry.clamp_top_left(self.settings.pos_x, self.settings.pos_y, self.size())
        self.move(point)
        self.show()
        # Métricas de fonte finais só assentam depois do show(); o tamanho
        # pré-show é estimativa. Reajusta já, sem esperar o primeiro dado.
        self._schedule_fit()

    def _has_manual_size(self) -> bool:
        return bool(self.settings.window_width and self.settings.window_height)

    def _available_rect(self):
        screen = self.screen() or QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _resize_to_content(self):
        self._programmatic_resize = True
        try:
            available = self._available_rect()
            if self.layout() is not None:
                self.layout().activate()
            base = self.layout().totalMinimumSize() if self.layout() is not None else QSize()
            flow = self._body_layout
            # Largura alvo: manual (a sobra vira colunas no fluxo) ou a do
            # conteúdo — nunca abaixo do mínimo de 1 coluna (sem scrollbar).
            if self._has_manual_size():
                target_w = int(self.settings.window_width)
            else:
                target_w = self.sizeHint().width()
            target_w = max(target_w, base.width(), MIN_WINDOW_SIZE.width())
            if available is not None:
                target_w = min(target_w, available.width())
            # Altura que o conteúdo precisa NESSA largura: janela estreita
            # empilha os cards, larga faz fileiras. Pela largura ALVO e não
            # pela geometria atual — antes do show() os filhos ainda não têm
            # geometria (print 260914: janela ficava com a altura da pilha
            # inteira mesmo larga, 65% de espaço morto embaixo).
            needed_h = base.height()
            if flow is not None and flow.count():
                flow_min = flow.minimumSize()
                needed_h = base.height() - flow_min.height() + flow.heightForWidth(max(1, target_w - FLOW_CHROME_W))
            minimum = QSize(base.width(), needed_h).expandedTo(MIN_WINDOW_SIZE)
            if available is not None:
                minimum = minimum.boundedTo(available.size())
            self.setMinimumSize(minimum)
            # Largura manual é respeitada; altura cola no conteúdo. A altura
            # também é escrita no settings pra persistir o tamanho real.
            target = QSize(target_w, minimum.height())
            if available is not None:
                target = target.boundedTo(available.size())
            if self._has_manual_size() and self.settings.window_height != target.height():
                self.settings.window_height = target.height()
            self.resize(target)
        finally:
            self._programmatic_resize = False
        point = screen_geometry.clamp_top_left(self.pos().x(), self.pos().y(), self.size())
        if point != self.pos():
            self.move(point)

    def _fit_to_content(self):
        self.settings.window_width = None
        self.settings.window_height = None
        self._resize_to_content()
        self._save_settings()

    def _reclamp_position(self, *_args):
        current = self.pos()
        if not screen_geometry.point_is_visible(QPoint(current.x(), current.y())):
            point = screen_geometry.clamp_top_left(None, None, self.size())
            self.move(point)
            self._save_settings()

    def _snap_drag(self, point: QPoint) -> QPoint:
        if not self.settings.snap_edges:
            return point
        center = point + QPoint(self.width() // 2, self.height() // 2)
        screen = QGuiApplication.screenAt(center) or self.screen()
        if screen is None:
            return point
        grip = QPoint(RESIZE_GRIP, RESIZE_GRIP)
        inner = QSize(self.width() - 2 * RESIZE_GRIP, self.height() - 2 * RESIZE_GRIP)
        return screen_geometry.snap_point(point + grip, inner, screen.availableGeometry()) - grip

    def _edges_at(self, pos: QPoint):
        if self.settings.lock_position:
            return screen_geometry.NO_EDGE
        return screen_geometry.resize_edges_at(pos.x(), pos.y(), self.width(), self.height(), RESIZE_GRIP, RESIZE_CORNER)

    def _begin_user_resize(self, edges, global_pos: QPoint):
        self._user_resize_active = True
        self.settings.window_width, self.settings.window_height = self.width(), self.height()
        # O mínimo de conteúdo continua valendo: o Windows/clamp não deixa
        # encolher além do que cabe (pedido 260914, sem barra de rolagem).
        handle = self.windowHandle()
        if handle is not None and handle.startSystemResize(edges):
            # O Windows conduz o arraste (cursor, suavidade); o fim é detectado
            # quando o botão solta.
            self._resize_watch_timer.start()
            return
        self._resize_edges = edges
        self._press_global = global_pos
        self._press_geometry = self.geometry()

    def _watch_resize_end(self):
        if QGuiApplication.mouseButtons() == Qt.NoButton:
            self._resize_watch_timer.stop()
            self._finish_user_resize()

    def _finish_user_resize(self):
        # Salva agora; o timer de 400 ms pendente escreveria de novo mais tarde.
        self._size_save_timer.stop()
        self._user_resize_active = False
        self._resize_edges = None
        self.settings.window_width, self.settings.window_height = self.width(), self.height()
        # Reajusta na hora: a altura arrastada que não tem conteúdo embaixo
        # encolhe de volta imediatamente — o mouse escolhe a largura, o
        # conteúdo decide a altura.
        self._resize_to_content()
        self._save_settings()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edges = self._edges_at(event.position().toPoint())
            if edges:
                self._begin_user_resize(edges, event.globalPosition().toPoint())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resize_edges and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_global
            self.setGeometry(screen_geometry.resized_rect(self._press_geometry, self._resize_edges, delta, self.minimumSize()))
            event.accept()
            return
        cursor = screen_geometry.cursor_for_edges(self._edges_at(event.position().toPoint()))
        if cursor is None:
            self.unsetCursor()
        else:
            self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_edges:
            self._finish_user_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._user_resize_active and not self._programmatic_resize:
            self.settings.window_width, self.settings.window_height = self.width(), self.height()
            self._size_save_timer.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        painter.end()

    def enterEvent(self, event):
        self._hovering = True
        self._apply_hover()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovering = False
        self._apply_hover()
        super().leaveEvent(event)

    def _apply_hover(self):
        fade = self._hovering and self.settings.hover_mode == "fade"
        self.setWindowOpacity(FADE_OPACITY if fade else 1.0)
        self._apply_panel_style()

    # ------------------------------------------------------------------
    # dados
    # ------------------------------------------------------------------

    def poll_now(self):
        if not self.demo:
            self._request_mcp_health()
        visible_ids = self._visible_sources()
        if not self.demo:
            visible_ids = [pid for pid in visible_ids if self._backoff.ready(pid) and pid not in self._querying]
        if not visible_ids:
            self._update_refresh_feedback()
            return
        self._last_attempt = datetime.now().astimezone()
        if self.demo:
            for provider_id in visible_ids:
                self.store.update(provider_id, demo_snapshot(provider_id))
            self._refresh_all_segments()
            self._update_refresh_feedback()
            self._schedule_fit()
            return
        self._querying.update(visible_ids)
        self.poller.poll(visible_ids)
        self._update_refresh_feedback()

    def _request_mcp_health(self):
        script = paths.CENTRAL_DIR / "bin" / "mb-saude-mcp.py"
        if script.exists():
            QProcess.startDetached(sys.executable, [str(script)])

    def _update_refresh_feedback(self):
        visible = set(self._visible_sources())
        busy = bool(self._querying & visible)
        if not visible:
            label = "Consulta pausada"
        elif self.demo:
            label = "Demonstração · sem consulta real"
        elif busy:
            label = "Consultando…"
        elif any(not self._backoff.ready(pid) for pid in visible):
            label = "Limite de consultas · aguardando"
        elif self._last_attempt:
            label = f"Tentativa {age_label(self._last_attempt.isoformat())}"
        else:
            label = "Aguardando consulta"
        self._refresh_status.setText(label)
        hint = f"Consulta automática a cada {self.settings.poll_minutes} minutos. A idade do dado aparece em cada provedor."
        if self._last_attempt is not None and not self.demo:
            hint = f"Última tentativa: {self._last_attempt:%d/%m/%Y %H:%M:%S}. Não indica sucesso.\n{hint}"
        if any(not self._backoff.ready(pid) for pid in visible):
            hint += "\nFontes limitadas aguardam uma pausa automática antes da próxima consulta."
        self._refresh_status.setToolTip(hint)
        ready = any(self._backoff.ready(pid) for pid in visible)
        self._refresh_btn.setEnabled(ready and not busy and not self._manual_refresh_locked)

    def manual_refresh(self):
        if self._manual_refresh_locked or self._querying & set(self._visible_sources()):
            return
        self._manual_refresh_locked = True
        QTimer.singleShot(MANUAL_REFRESH_COOLDOWN_MS, self._unlock_manual_refresh)
        self.poll_now()

    def _unlock_manual_refresh(self):
        self._manual_refresh_locked = False
        self._update_refresh_feedback()

    def _on_snapshot(self, provider_id: str, snapshot: dict):
        self._backoff.observe(provider_id, snapshot.get("status"))
        if snapshot.get("status") == "rate_limited":
            timer = self._retry_timers.get(provider_id)
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.setTimerType(Qt.PreciseTimer)
                timer.timeout.connect(lambda pid=provider_id: self._retry_provider(pid))
                self._retry_timers[provider_id] = timer
            timer.start(ceil(self._backoff.remaining(provider_id) * 1000))
        elif snapshot.get("status") == "ok" and provider_id in self._retry_timers:
            self._retry_timers[provider_id].stop()
        self.store.update(provider_id, snapshot)
        if self._pacing_module is not None and snapshot.get("status") == "ok":
            try:
                pacing = self._pacing_module.provider_pacing(snapshot)
                self._pacing_by_provider[provider_id] = pacing
                budget_status.write(provider_id, pacing)
            except Exception:
                pass
        self._querying.discard(provider_id)
        self._update_refresh_feedback()
        for row_id, segment in self._segments.items():
            if theme.row_source(row_id) == provider_id and self.settings.is_visible(row_id):
                segment.update_from_store(self.store, self.settings.expanded, self._pacing_by_provider.get(provider_id))
        if snapshot.get("status") == "ok":
            self._check_alerts(provider_id)
        self._schedule_fit()

    def _schedule_fit(self):
        """Reajusta tamanho e posição depois que o conteúdo mudou.

        O dado chega depois do show(): o detalhe cresce a janela e, sem
        re-clamp, a borda de baixo passava do monitor (medido 260913 no monitor
        retrato). Labels recém-criados só têm tamanho final no passe de layout
        seguinte, então roda de novo quando o event loop assentar. Também vale
        para o tique de idade ("59 min" -> "1 h" muda a largura do texto).
        """
        self._resize_to_content()
        QTimer.singleShot(0, self._resize_to_content)
        QTimer.singleShot(150, self._resize_to_content)

    def _check_alerts(self, source: str):
        threshold = self.settings.alert_percent
        if not threshold or self.demo:
            return
        for row_id in self.provider_ids:
            if theme.row_source(row_id) != source or not self.settings.is_visible(row_id):
                continue
            display = self.store.display(source, theme.row_window_filter(row_id))
            for window in (display or {}).get("windows") or []:
                used = window.get("used_percent")
                key = (row_id, window.get("id"), window.get("resets_at"))
                if used is None or used < threshold or key in self._alerted:
                    continue
                self._alerted.add(key)
                label = self._canonical_labels.get(row_id, row_id)
                self._notify(
                    f"{label}: {friendly_window_label(window.get('label'))} em {percent_label(used)}",
                    f"Passou do aviso de {threshold}%.",
                )

    def _notify(self, title: str, body: str):
        if self._tray is None:
            return
        self._tray.show()
        self._tray.showMessage(title, body, QSystemTrayIcon.Warning, 8000)

    def _retry_provider(self, provider_id):
        if self.demo or provider_id not in self._visible_sources() or provider_id in self._querying:
            return
        if not self._backoff.ready(provider_id):
            self._retry_timers[provider_id].start(ceil(self._backoff.remaining(provider_id) * 1000))
            return
        self._last_attempt = datetime.now().astimezone()
        self._querying.add(provider_id)
        self.poller.poll([provider_id])
        self._update_refresh_feedback()

    def _provider_menu_label(self, provider_id: str) -> str:
        label = self._canonical_labels.get(provider_id, provider_id)
        source, window_filter = theme.row_source(provider_id), theme.row_window_filter(provider_id)
        display = self.store.display(source, window_filter)
        if display is None:
            return label
        status = display["status"]
        if status == "ok":
            worst = self.store.worst_window(source, window_filter)
            if worst is not None and worst.get("used_percent") is not None:
                freshness = age_label(display.get('fetched_at'))
                quality = "dado antigo" if display['stale'] else "ok"
                return f"{label} — {round(worst['used_percent'])}% · {quality} · {freshness}"
            return f"{label} — ok · {age_label(display.get('fetched_at'))}"
        short = theme.STATUS_SHORT_LABEL.get(status, status) or status
        age = f" · dado {age_label(display['fetched_at'])}" if display.get('fetched_at') else ""
        return f"{label} — {short}{age}"

    def _toggle_provider_visibility(self, provider_id: str, visible: bool):
        self.settings.set_visible(provider_id, visible)
        self._rebuild_segments()
        if visible:
            segment = self._segments.get(provider_id)
            source = theme.row_source(provider_id)
            shared_and_read = self.store.display(source) is not None and any(
                other != provider_id and theme.row_source(other) == source and self.settings.is_visible(other)
                for other in self.provider_ids
            )
            if source in self._querying or shared_and_read:
                pass  # a mesma fonte já está sendo lida ou acabou de ser, pela linha irmã
            elif self.demo:
                self.store.update(source, demo_snapshot(source))
                if segment is not None:
                    segment.update_from_store(self.store, self.settings.expanded)
            elif self._backoff.ready(source):
                if segment is not None:
                    segment.show_querying()
                self._last_attempt = datetime.now().astimezone()
                self._querying.add(source)
                self.poller.poll([source])
        self._update_refresh_feedback()
        self._resize_to_content()
        self._save_settings()

    # ------------------------------------------------------------------
    # controles de janela
    # ------------------------------------------------------------------

    def _toggle_always_on_top(self):
        self.settings.always_on_top = not self.settings.always_on_top
        self._reapply_window_flags()
        self._sync_top_button()
        self._save_settings()

    def _toggle_click_through(self):
        self.update_settings({"click_through": not self.settings.click_through})

    def _sync_top_button(self):
        enabled = self.settings.always_on_top
        self._top_btn.setChecked(enabled)
        self._top_btn.setText("◆" if enabled else "◇")
        label = f"Sempre acima: {'ligado' if enabled else 'desligado'} (Ctrl+T)"
        self._top_btn.setToolTip(label)
        self._top_btn.setAccessibleName(label)

    def _sync_tray(self):
        if self._tray is None:
            return
        self._tray_click_action.setChecked(self.settings.click_through)
        # Com "atravessar cliques" a janela não recebe mouse: a bandeja é a saída.
        needed = self.settings.click_through or bool(self.settings.alert_percent) or self._minimized
        self._tray.setVisible(needed)

    def _toggle_expanded(self):
        self.settings.expanded = not self.settings.expanded
        self._details_btn.setText("▴" if self.settings.expanded else "▾")
        self._details_btn.setAccessibleName("Recolher detalhes (Ctrl+D)" if self.settings.expanded else "Expandir detalhes (Ctrl+D)")
        for segment in self._segments.values():
            segment.set_expanded(self.settings.expanded)
        self._resize_to_content()
        self._save_settings()

    def _set_opacity(self, value: int):
        self.settings.bg_opacity_percent = value
        self._apply_panel_style()
        self._save_settings()

    def _set_scale(self, value: float):
        self.settings.scale = value
        for segment in self._segments.values():
            segment.apply_scale(value)
        self._resize_to_content()
        self._save_settings()

    def _show_menu(self):
        menu = QMenu(self)
        menu.addAction("Configurações…\tCtrl+,", self.open_settings)
        menu.addSeparator()

        opacity_menu = menu.addMenu("Opacidade do fundo")
        for step in theme.OPACITY_STEPS:
            action = opacity_menu.addAction(f"{step}%")
            action.setCheckable(True)
            action.setChecked(self.settings.bg_opacity_percent == step)
            action.triggered.connect(lambda checked=False, v=step: self._set_opacity(v))

        theme_menu = menu.addMenu("Cor de fundo")
        for preset_id in theme.SURFACE_PRESET_ORDER:
            preset = theme.SURFACE_PRESETS[preset_id]
            action = theme_menu.addAction(preset["label"])
            action.setCheckable(True)
            action.setChecked(self.settings.surface_preset == preset_id)
            action.triggered.connect(lambda checked=False, pid=preset_id: self._set_surface_preset(pid))

        scale_menu = menu.addMenu("Escala")
        for step in theme.SCALE_STEPS:
            action = scale_menu.addAction(f"{round(step * 100)}%")
            action.setCheckable(True)
            action.setChecked(self.settings.scale == step)
            action.triggered.connect(lambda checked=False, v=step: self._set_scale(v))

        providers_menu = menu.addMenu("Provedores")
        self._populate_providers_menu(providers_menu)

        expand_label = "Recolher detalhes" if self.settings.expanded else "Expandir detalhes"
        menu.addAction(expand_label + "\tCtrl+D", self._toggle_expanded)
        fit_action = menu.addAction("Ajustar tamanho ao conteúdo\tCtrl+0", self._fit_to_content)
        fit_action.setEnabled(self._has_manual_size())
        pin_action = menu.addAction("Sempre acima\tCtrl+T", self._toggle_always_on_top)
        pin_action.setCheckable(True)
        pin_action.setChecked(self.settings.always_on_top)
        lock_action = menu.addAction(
            "Travar posição e tamanho",
            lambda: self.update_settings({"lock_position": not self.settings.lock_position}),
        )
        lock_action.setCheckable(True)
        lock_action.setChecked(self.settings.lock_position)
        menu.addAction("Atualizar agora\tF5", self.manual_refresh)
        if self._tray is not None:
            menu.addAction("Minimizar para bandeja", self._minimize_to_tray)
        menu.addSeparator()
        menu.addAction("Sair", self._quit)
        menu.exec(self._options_btn.mapToGlobal(self._options_btn.rect().bottomLeft()))

    def _show_providers_menu(self):
        menu = QMenu(self)
        self._populate_providers_menu(menu)
        menu.exec(self._empty_btn.mapToGlobal(self._empty_btn.rect().bottomLeft()))

    def _populate_providers_menu(self, providers_menu):
        for provider_id in self.provider_ids:
            action = providers_menu.addAction(self._provider_menu_label(provider_id))
            action.setCheckable(True)
            action.setChecked(self.settings.is_visible(provider_id))
            action.triggered.connect(
                lambda checked, pid=provider_id: self._toggle_provider_visibility(pid, checked)
            )

    def _minimize_to_tray(self):
        if self._tray is not None:
            self._minimized = True
            self._sync_tray()
            self.hide()

    def _show_from_tray(self):
        self._minimized = False
        self.show()
        self.raise_()
        self.activateWindow()
        self._sync_tray()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self._minimize_to_tray()
            else:
                self._show_from_tray()

    def _save_settings(self):
        if self._session_only:
            return
        pos = self.pos()
        self.settings.pos_x = pos.x()
        self.settings.pos_y = pos.y()
        persistence.save_settings(self.settings)

    def _quit(self):
        from PySide6.QtWidgets import QApplication

        self._save_settings()
        if self._settings_dialog is not None:
            self._settings_dialog.close()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self._save_settings()
        if self._settings_dialog is not None:
            self._settings_dialog.close()
        super().closeEvent(event)
