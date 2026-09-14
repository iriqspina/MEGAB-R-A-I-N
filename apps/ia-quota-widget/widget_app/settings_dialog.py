"""Configurações do Cotas IA com prévia ao vivo.

Tudo aplica na hora (como as Configurações do Windows 11) e salva; "Desfazer
alterações" volta ao estado de quando a janela abriu. A prévia usa o MESMO
ProviderSegment do widget, com dado de exemplo — o que aparece ali é o que o
widget desenha, não uma imitação.

Opções escolhidas a partir do que apps do mesmo tipo oferecem (pesquisa 260913):
CodexBar (intervalo de atualização, estilo de renovação, ordem, aviso de cota),
TrafficMonitor (fonte, travar posição, atravessar cliques com saída pela
bandeja) e Rainmeter (grudar nas bordas, comportamento ao passar o mouse).
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFontComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import persistence, theme
from .contrast import hex_to_rgb
from .snapshot_store import SnapshotStore
from .ui_provider_segment import ProviderSegment, options_from, typography_from

SUGGESTED_FONTS = (
    "Segoe UI",
    "Segoe UI Variable Display",
    "Bahnschrift",
    "Cascadia Code",
    "Consolas",
    "Inter",
    "Arial",
    "Verdana",
    "Trebuchet MS",
    "Georgia",
    "Calibri",
    "Tahoma",
)

VISUAL_KEYS = (
    "font_family", "size_name", "size_value", "size_hint", "size_detail", "scale",
    "surface_preset", "bg_opacity_percent", "number_mode", "reset_mode",
    "show_pacing", "show_footer", "hover_mode",
)
UNDO_SKIP = ("pos_x", "pos_y", "window_width", "window_height", "visible_providers")


class LivePreview(QFrame):
    """Um card real do widget (Claude, expandido) com dado de exemplo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview")
        grid = QGridLayout(self)
        grid.setContentsMargins(16, 12, 16, 12)
        now = datetime.now(timezone.utc)
        self._store = SnapshotStore()
        self._store.update("claude", {
            "status": "ok",
            "windows": [
                {"id": "session", "label": "Sessão", "used_percent": 57.0,
                 "resets_at": (now + timedelta(hours=2, minutes=10)).isoformat()},
                {"id": "weekly_all", "label": "Semana", "used_percent": 6.0,
                 "resets_at": (now + timedelta(days=6)).isoformat()},
                {"id": "weekly_scoped:Fable", "label": "Semana · Fable", "used_percent": 0.0,
                 "resets_at": (now + timedelta(days=6)).isoformat()},
            ],
            "fetched_at": now.isoformat(),
            "message": "Plano max. (exemplo)",
            "source": "prévia",
        })
        self._pacing = {"windows": {
            "session": {"status": "ok", "target_per_hour": 21.4},
            "weekly_all": {"status": "ok", "target_per_business_day": 15.2},
            "weekly_scoped:Fable": {"status": "ok", "target_per_business_day": 16.0},
        }}
        self.segment = ProviderSegment("claude", "Claude", self)
        grid.addWidget(self.segment, 0, 0)
        grid.setColumnStretch(0, 1)
        self.segment.set_expanded(True)
        self.segment.show()

    def refresh(self, settings):
        palette = theme.palette_for(settings.surface_preset)
        r, g, b = hex_to_rgb(theme.surface_preset(settings.surface_preset)["bg"])
        alpha = settings.bg_opacity_percent / 100.0
        self.setStyleSheet(
            f"#preview {{ background-color: rgba({r},{g},{b},{alpha}); border: 1px solid {palette['border']};"
            f" border-radius: {theme.CORNER_RADIUS}px; }}"
        )
        self.segment.apply_scale(settings.scale)
        self.segment.configure(typography_from(settings), options_from(settings))
        self.segment.apply_theme(palette)
        self.segment.update_from_store(self._store, True, self._pacing)


class SettingsDialog(QDialog):
    def __init__(self, window):
        super().__init__(None)
        self._window = window
        self._syncing = False
        self._opened_with: dict | None = None
        self.setWindowTitle("Cotas IA — Configurações")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setMinimumWidth(600)

        root = QVBoxLayout(self)
        caption = QLabel(
            "Prévia ao vivo com dados de exemplo — é o mesmo desenho do widget. "
            "Cada mudança já vale na janela e fica salva."
        )
        caption.setWordWrap(True)
        root.addWidget(caption)

        # Fundo xadrez discreto atrás da prévia: deixa a opacidade visível.
        backdrop = QFrame(self)
        backdrop.setObjectName("backdrop")
        backdrop.setStyleSheet(
            "#backdrop { border-radius: 8px; background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
            " stop:0 #4d7a5a, stop:0.5 #9cc5a1, stop:1 #2f4f3a); }"
        )
        backdrop_layout = QVBoxLayout(backdrop)
        backdrop_layout.setContentsMargins(14, 14, 14, 14)
        self.preview = LivePreview(backdrop)
        backdrop_layout.addWidget(self.preview)
        root.addWidget(backdrop)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._build_text_tab(), "Texto")
        self.tabs.addTab(self._build_look_tab(), "Aparência")
        self.tabs.addTab(self._build_numbers_tab(), "Números")
        self.tabs.addTab(self._build_window_tab(), "Janela")
        self.tabs.addTab(self._build_providers_tab(), "Provedores")
        root.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        self.undo_btn = QPushButton("Desfazer alterações")
        self.undo_btn.setToolTip("Volta tudo ao que estava quando esta janela abriu")
        self.undo_btn.clicked.connect(self.undo_changes)
        self.defaults_btn = QPushButton("Restaurar visual padrão")
        self.defaults_btn.setToolTip("Fonte, tamanhos, cor, opacidade e exibição voltam ao padrão do app")
        self.defaults_btn.clicked.connect(self.restore_visual_defaults)
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.close)
        buttons.addWidget(self.undo_btn)
        buttons.addWidget(self.defaults_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

    # ------------------------------------------------------------ construção

    def _combo(self, items, key: str) -> QComboBox:
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        combo.currentIndexChanged.connect(lambda _i, c=combo, k=key: self._apply({k: c.currentData()}))
        return combo

    def _check(self, text: str, key: str) -> QCheckBox:
        box = QCheckBox(text)
        box.toggled.connect(lambda checked, k=key: self._apply({k: checked}))
        return box

    def _spin(self, low: int, high: int, key: str) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(low, high)
        spin.setSuffix(" px")
        spin.valueChanged.connect(lambda value, k=key: self._apply({k: value}))
        return spin

    def _note(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #9a9ea6;")  # legível no tema claro e no escuro do Windows
        return label

    def _build_text_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.font_combo = QFontComboBox()
        self.font_combo.setToolTip("A lista mostra cada fonte escrita nela mesma")
        self.font_combo.currentFontChanged.connect(lambda font: self._apply({"font_family": font.family()}))
        form.addRow("Fonte", self.font_combo)

        gallery = QWidget()
        grid = QGridLayout(gallery)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)
        installed = set(QFontDatabase.families())
        self.gallery_buttons: dict[str, QPushButton] = {}
        for index, family in enumerate([f for f in SUGGESTED_FONTS if f in installed][:12]):
            button = QPushButton(f"Claude  57%\n{family}")
            font = QFont(family)
            font.setPointSize(10)
            button.setFont(font)
            button.setMinimumHeight(46)
            button.setCheckable(True)
            button.setToolTip(f"Usar {family}")
            button.clicked.connect(lambda _c=False, fam=family: self.font_combo.setCurrentFont(QFont(fam)))
            grid.addWidget(button, index // 4, index % 4)
            self.gallery_buttons[family] = button
        form.addRow("Exemplos", gallery)

        self.name_spin = self._spin(8, 32, "size_name")
        self.value_spin = self._spin(10, 48, "size_value")
        self.hint_spin = self._spin(8, 28, "size_hint")
        self.detail_spin = self._spin(8, 28, "size_detail")
        form.addRow("Nome do provedor", self.name_spin)
        form.addRow("Número grande", self.value_spin)
        form.addRow("Linha de status", self.hint_spin)
        form.addRow("Detalhes", self.detail_spin)
        self.scale_combo = self._combo([(f"{round(s * 100)}%", s) for s in theme.SCALE_STEPS], "scale")
        form.addRow("Escala geral", self.scale_combo)
        form.addRow("", self._note("Tamanhos em px antes da escala geral. Escala multiplica tudo junto."))
        return tab

    def _build_look_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.preset_combo = QComboBox()
        for preset_id in theme.SURFACE_PRESET_ORDER:
            preset = theme.SURFACE_PRESETS[preset_id]
            swatch = QPixmap(14, 14)
            swatch.fill(QColor(preset["bg"]))
            self.preset_combo.addItem(QIcon(swatch), preset["label"], preset_id)
        self.preset_combo.currentIndexChanged.connect(
            lambda _i: self._apply({"surface_preset": self.preset_combo.currentData()})
        )
        form.addRow("Cor de fundo", self.preset_combo)

        opacity_row = QWidget()
        opacity_layout = QHBoxLayout(opacity_row)
        opacity_layout.setContentsMargins(0, 0, 0, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_label = QLabel()
        self.opacity_label.setMinimumWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_label)
        form.addRow("Opacidade do fundo", opacity_row)

        self.expanded_check = self._check("Mostrar detalhes de cada janela de cota", "expanded")
        self.pacing_check = self._check('Mostrar ritmo ("dá ~16%/dia")', "show_pacing")
        self.footer_check = self._check("Mostrar rodapé (última consulta e MCP)", "show_footer")
        form.addRow("", self.expanded_check)
        form.addRow("", self.pacing_check)
        form.addRow("", self.footer_check)
        self.hover_combo = self._combo(
            [("Nada muda", "none"), ("Fundo sólido, pra ler melhor", "opaque"), ("Fica transparente, pra ver atrás", "fade")],
            "hover_mode",
        )
        form.addRow("Ao passar o mouse", self.hover_combo)
        return tab

    def _build_numbers_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.number_combo = self._combo([("% usado", "used"), ("% que sobra (livre)", "remaining")], "number_mode")
        form.addRow("Número grande mostra", self.number_combo)
        self.reset_combo = self._combo(
            [("Tempo até renovar (renova em 5 d)", "relative"), ("Dia e hora (renova sáb 13:19)", "absolute")],
            "reset_mode",
        )
        form.addRow("Renovação", self.reset_combo)
        from .main_window import ALERT_STEPS, POLL_MINUTE_STEPS

        self.poll_combo = self._combo([(f"A cada {m} min", m) for m in POLL_MINUTE_STEPS], "poll_minutes")
        form.addRow("Atualizar", self.poll_combo)
        form.addRow("", self._note("2 min é o mínimo: consultar mais rápido já levou o Claude a limitar (HTTP 429)."))
        self.alert_combo = self._combo(
            [("Desligado" if step == 0 else f"Quando passar de {step}%", step) for step in ALERT_STEPS],
            "alert_percent",
        )
        form.addRow("Aviso na bandeja", self.alert_combo)
        form.addRow("", self._note("Um aviso por janela de cota até ela renovar."))
        return tab

    def _build_window_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        self.top_check = self._check("Sempre acima das outras janelas", "always_on_top")
        self.lock_check = self._check("Travar posição e tamanho", "lock_position")
        self.snap_check = self._check("Grudar nas bordas da tela ao arrastar", "snap_edges")
        self.click_check = self._check("Atravessar cliques (a janela não recebe o mouse)", "click_through")
        for box in (self.top_check, self.lock_check, self.snap_check, self.click_check):
            form.addRow("", box)
        form.addRow("", self._note("Para desligar “atravessar cliques”: ícone do Cotas IA na bandeja → Atravessar cliques."))
        fit = QPushButton("Ajustar tamanho ao conteúdo")
        fit.clicked.connect(self._window._fit_to_content)
        form.addRow("Tamanho", fit)
        form.addRow("", self._note("Arraste bordas e cantos para redimensionar. Duplo clique no cabeçalho (ou Ctrl+0) volta ao automático."))
        return tab

    def _build_providers_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        self.provider_list = QListWidget()
        self.provider_list.itemChanged.connect(self._on_provider_item)
        layout.addWidget(self.provider_list, 1)
        side = QVBoxLayout()
        up = QPushButton("↑ Subir")
        down = QPushButton("↓ Descer")
        up.clicked.connect(lambda: self.move_selected(-1))
        down.clicked.connect(lambda: self.move_selected(1))
        side.addWidget(up)
        side.addWidget(down)
        side.addStretch(1)
        side.addWidget(self._note("Marque para mostrar. A ordem aqui é a ordem no widget."))
        layout.addLayout(side)
        return tab

    # ------------------------------------------------------------ sincronia

    def begin_session(self):
        self._opened_with = asdict(self._window.settings)
        self.sync_from_window()

    def sync_from_window(self):
        s = self._window.settings
        self._syncing = True
        try:
            self.font_combo.setCurrentFont(QFont(s.font_family))
            for family, button in self.gallery_buttons.items():
                button.setChecked(family == s.font_family)
            self.name_spin.setValue(s.size_name)
            self.value_spin.setValue(s.size_value)
            self.hint_spin.setValue(s.size_hint)
            self.detail_spin.setValue(s.size_detail)
            self._select(self.scale_combo, s.scale)
            self._select(self.preset_combo, s.surface_preset)
            self.opacity_slider.setValue(s.bg_opacity_percent)
            self.opacity_label.setText(f"{s.bg_opacity_percent}%")
            self.expanded_check.setChecked(s.expanded)
            self.pacing_check.setChecked(s.show_pacing)
            self.footer_check.setChecked(s.show_footer)
            self._select(self.hover_combo, s.hover_mode)
            self._select(self.number_combo, s.number_mode)
            self._select(self.reset_combo, s.reset_mode)
            self._select(self.poll_combo, s.poll_minutes)
            self._select(self.alert_combo, s.alert_percent)
            self.top_check.setChecked(s.always_on_top)
            self.lock_check.setChecked(s.lock_position)
            self.snap_check.setChecked(s.snap_edges)
            self.click_check.setChecked(s.click_through)
            current = self.provider_list.currentRow()
            self.provider_list.clear()
            for row_id in self._window.provider_ids:
                item = QListWidgetItem(self._window._provider_menu_label(row_id))
                item.setData(Qt.UserRole, row_id)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if s.is_visible(row_id) else Qt.Unchecked)
                self.provider_list.addItem(item)
            if current >= 0:
                self.provider_list.setCurrentRow(min(current, self.provider_list.count() - 1))
        finally:
            self._syncing = False
        self.preview.refresh(s)

    @staticmethod
    def _select(combo: QComboBox, value):
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ------------------------------------------------------------ ações

    def _apply(self, changes: dict):
        if self._syncing:
            return
        self._window.update_settings(changes)
        if "font_family" in changes:
            for family, button in self.gallery_buttons.items():
                button.setChecked(family == self._window.settings.font_family)
        self.preview.refresh(self._window.settings)

    def _on_opacity(self, value: int):
        self.opacity_label.setText(f"{value}%")
        self._apply({"bg_opacity_percent": value})

    def _on_provider_item(self, item: QListWidgetItem):
        if self._syncing:
            return
        row_id = item.data(Qt.UserRole)
        visible = item.checkState() == Qt.Checked
        if self._window.settings.is_visible(row_id) != visible:
            self._window._toggle_provider_visibility(row_id, visible)

    def move_selected(self, delta: int):
        row = self.provider_list.currentRow()
        target = row + delta
        order = list(self._window.provider_ids)
        if row < 0 or not 0 <= target < len(order):
            return
        order.insert(target, order.pop(row))
        self._window.update_settings({"provider_order": order})
        self.sync_from_window()
        self.provider_list.setCurrentRow(target)

    def undo_changes(self):
        if self._opened_with is None:
            return
        snapshot = self._opened_with
        self._window.update_settings({k: v for k, v in snapshot.items() if k not in UNDO_SKIP})
        wanted = snapshot.get("visible_providers") or {}
        for row_id in list(self._window.provider_ids):
            want = wanted.get(row_id, True)
            if self._window.settings.is_visible(row_id) != want:
                self._window._toggle_provider_visibility(row_id, want)
        self.sync_from_window()

    def restore_visual_defaults(self):
        self._window.update_settings({key: persistence.DEFAULT_SETTINGS[key] for key in VISUAL_KEYS})
        self.sync_from_window()
