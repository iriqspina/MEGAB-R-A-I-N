"""Scrollable quota cards and explicit, safe actions over the strip's snapshot."""
import math
import re
from datetime import timedelta, timezone

from PySide6.QtCore import QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget, QProgressBar)

from . import paths, theme
from .formatting import age_label, parse_iso, reset_label
from .observed_info import observed_info, observed_sections, balance_evidence_sections
from .provider_brand import ACCOUNT_URLS, brand_pixmap, provider_name
from .quota_focus import duration_label, focus_window, general_windows, is_reserve

BRT = timezone(timedelta(hours=-3), "BRT")


def safe_text(value):
    """Plain text only; strip control characters and common credential forms."""
    text = str(value) if isinstance(value, (str, int, float)) else ""
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f\u202a-\u202e\u2066-\u2069]", "", text)
    text = re.sub(r"(?i)\b(?:bearer)\s+\S+", "Bearer [oculto]", text)
    text = re.sub(r"(?i)\b((?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|token|authorization|password|secret|cookie)[\"']?\s*[:=]\s*[\"']?)([^\s,;]+)",
                  r"\1[oculto]", text)
    text = re.sub(r"\b(?:sk-|sk_|sess-)[A-Za-z0-9_-]{8,}", "[oculto]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", "[oculto]", text)
    text = re.sub(r"(https?://)[^/\s@]+@", r"\1[oculto]@", text)
    text = re.sub(r"(https?://[^\s?#]+)[?#][^\s]*", r"\1", text)
    return text[:12000]


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def detailed_percent(value):
    value = number(value)
    if value is None:
        return "não informado"
    if 0 < value < .01:
        return "<0,01%"
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",") + "%"


def timestamp(value):
    dt = parse_iso(value)
    if dt is None or dt.tzinfo is None:
        return "data/hora não informada com fuso"
    return dt.astimezone(BRT).strftime("%d/%m/%Y %H:%M:%S BRT")


def text_label():
    label = QLabel()
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
    return label


class QuotaDetails(QDialog):
    def __init__(self, owner, row_id, anchor):
        super().__init__(owner)
        self.owner, self.row_id, self.anchor = owner, row_id, anchor
        self.setWindowTitle(f"{provider_name(row_id, owner._canonical_labels)} — detalhes da cota")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, owner.settings.always_on_top)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        header = QHBoxLayout()
        self.logo = QLabel()
        pixmap = brand_pixmap(row_id, 24, self.devicePixelRatioF())
        self.logo.setPixmap(pixmap)
        self.logo.setVisible(not pixmap.isNull())
        self.logo.setToolTip("Marca oficial local · identificação, não estado da cota")
        header.addWidget(self.logo)
        self.heading = text_label()
        self.heading.setText(provider_name(row_id, owner._canonical_labels))
        header.addWidget(self.heading, 1)
        compare = QPushButton('≡ Todas as barras')
        compare.clicked.connect(lambda: owner.open_quota_details('all', owner.strip.menu))
        header.addWidget(compare)
        root.addLayout(header)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 6, 0)
        self.summary = text_label()
        self.body_layout.addWidget(self.summary)
        self.cards = QWidget()
        self.cards_layout = QVBoxLayout(self.cards)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.addWidget(self.cards)
        self.rows = []
        self.bars = []
        self.extras = text_label()
        self.body_layout.addWidget(self.extras)
        self.technical_toggle, self.technical = self._disclosure("Dados técnicos")
        self.observed_toggle, self.observed_body = self._disclosure("Prints · não atualizados automaticamente")
        self.observed_sources = QWidget()
        self.observed_sources_layout = QVBoxLayout(self.observed_sources)
        self.observed_sources_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.addWidget(self.observed_sources)
        self.observed_sources.hide()
        self.observed_toggle.toggled.connect(self.observed_sources.setVisible)
        self._source_paths = None
        self.body_layout.addStretch()
        self.scroll.setWidget(self.body)
        root.addWidget(self.scroll, 1)
        actions = QHBoxLayout()
        self.refresh_button = self._button("↻ Atualizar", "Atualizar consultas visíveis · pausa existente entre consultas", self._refresh_now)
        self.refresh_button.setShortcut("F5")
        self.copy_button = self._button("⧉ Copiar", "Copiar dados exibidos, com credenciais removidas", self.copy_visible)
        self.account_button = self._button("↗ Conta", "Abrir conta oficial no navegador padrão", self.open_account)
        for button in (self.refresh_button, self.copy_button, self.account_button):
            actions.addWidget(button)
        root.addLayout(actions)
        self.feedback = text_label()
        self.feedback.setText(" ")
        root.addWidget(self.feedback)
        self.close_button = self._button("Fechar · Esc", "Fechar detalhes e voltar à faixa", self.reject)
        root.addWidget(self.close_button)
        self.account_button.setEnabled(row_id in ACCOUNT_URLS)
        if row_id == "codex_gpt2":
            self.account_button.setToolTip("Abrir conta oficial · confira a conta 2 no navegador; a sessão pode ser outra")
        elif row_id not in ACCOUNT_URLS:
            self.account_button.setToolTip("Página oficial de uso não cadastrada para este provedor")
        self.refresh()

    def _button(self, title, tooltip, callback):
        button = QPushButton(title)
        button.setAutoDefault(False)
        button.setFocusPolicy(Qt.StrongFocus)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.clicked.connect(callback)
        return button

    def _disclosure(self, title):
        toggle = QToolButton()
        toggle.setText(title)
        toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.RightArrow)
        toggle.setCheckable(True)
        toggle.setFocusPolicy(Qt.StrongFocus)
        toggle.setToolTip(f"Expandir ou recolher {title.lower()}")
        toggle.setAccessibleName(title)
        label = text_label()
        label.hide()
        toggle.toggled.connect(label.setVisible)
        toggle.toggled.connect(lambda checked: toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow))
        self.body_layout.addWidget(toggle)
        self.body_layout.addWidget(label)
        return toggle, label

    def _refresh_now(self):
        self.owner.manual_refresh()
        self.refresh()
        self.feedback.setText("↻ Pedido enviado · consultas respeitam a pausa existente.")

    def open_account(self):
        url = ACCOUNT_URLS.get(self.row_id)
        if url:
            opened = QDesktopServices.openUrl(QUrl(url))
            self.feedback.setText("↗ Conta aberta no navegador." if opened else "⚠ Não foi possível abrir o navegador.")

    def copy_visible(self):
        sections = [self.heading.text(), self.summary.text()]
        sections.extend(row.text() for row in self.rows)
        if not self.extras.isHidden():
            sections.append(self.extras.text())
        if self.technical_toggle.isChecked():
            sections.append(self.technical.text())
        if self.observed_toggle.isChecked():
            sections.append(self.observed_toggle.text() + "\n" + self.observed_body.text())
        QApplication.clipboard().setText("\n\n".join(sections))  # Every section is already sanitized.
        self.feedback.setText("✓ Dados visíveis copiados.")

    def refresh(self):
        scroll_value = self.scroll.verticalScrollBar().value()
        settings = self.owner.settings
        display = self.owner.store.display(theme.row_source(self.row_id)) or {}
        palette = self.owner._palette()
        self.setStyleSheet(
            f"QDialog, QScrollArea, QScrollArea > QWidget > QWidget {{background:{self.owner._preset()['bg']};}}"
            f"QLabel, QToolButton, QPushButton {{color:{palette['text']}; font-family:'{settings.font_family}';"
            f"font-size:{max(11, round(settings.size_detail * settings.scale))}px;}}"
            f"QPushButton, QToolButton {{background:{self.owner._preset()['bg']}; padding:5px; border:1px solid {palette['text_secondary']}; border-radius:4px;}}"
            f"QPushButton:focus, QToolButton:focus {{border:2px solid {palette['text']};}}"
            f"QPushButton:disabled {{color:{palette['text_secondary']};}}"
            f"QLabel[quotaCard='true'] {{border:1px solid {palette['text_secondary']};border-radius:6px;padding:9px;}}")
        querying = theme.row_source(self.row_id) in self.owner._querying
        status = display.get("status")
        state = theme.STATUS_SHORT_LABEL.get(status) or status or "aguardando"
        previous = bool(display.get("windows")) and (status != "ok" or display.get("stale"))
        state = ("↻ consultando · última leitura: " if querying else "● ") + safe_text(state)
        if previous:
            state += " · leitura antiga\n⚠ Percentuais da leitura anterior; não confirmados agora."
        self.summary.setText(
            ("DEMO · dados fictícios\n" if self.owner.demo else "") + state
            + f"\n◷ Consulta automática · {timestamp(display.get('fetched_at'))} · {age_label(display.get('fetched_at'))}"
            + f"\n↗ Fonte: {safe_text(display.get('source')) or 'não informada'}"
            + (f"\n⚠ {safe_text(display.get('message'))}" if display.get("message") else ""))
        windows = display.get("windows") or []
        focus = focus_window(general_windows(windows, self.row_id))
        while len(self.rows) < len(windows):
            label = text_label()
            label.setProperty("quotaCard", True)
            self.cards_layout.addWidget(label)
            self.rows.append(label)
            bar = QProgressBar()
            bar.setRange(0, 10000)
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            bar.setStyleSheet('QProgressBar{border:0;border-radius:5px;background:#394353;}QProgressBar::chunk{border-radius:5px;background:#66afe8;}')
            self.cards_layout.addWidget(bar)
            self.bars.append(bar)
        while len(self.rows) > len(windows):
            label = self.rows.pop()
            bar = self.bars.pop()
            self.cards_layout.removeWidget(bar)
            bar.deleteLater()
            if label.hasFocus():
                self.scroll.setFocus()
            self.cards_layout.removeWidget(label)
            label.deleteLater()
        for label, bar, window in zip(self.rows, self.bars, windows):
            used = number(window.get("used_percent"))
            remaining = 100 - used if used is not None else None
            value = remaining if settings.number_mode == 'remaining' else used
            bar.setValue(round(value * 100) if value is not None else 0)
            bar.setAccessibleName(('Disponível: ' if settings.number_mode == 'remaining' else 'Usado: ') + detailed_percent(value))
            bar.setToolTip(bar.accessibleName())
            bucket = self._bucket(window)
            duration = duration_label(window)
            if duration == "janela ?":
                duration = "duração não informada"
            reset = window.get("resets_at")
            relative = reset_label(reset) if parse_iso(reset) and parse_iso(reset).tzinfo else "renovação desconhecida"
            label.setText(
                f"{safe_text(window.get('label') or window.get('id')) or 'Janela'}"
                + (" · ★ Destaque da faixa" if window is focus else "")
                + (" · leitura anterior" if previous else "")
                + f"\n◉ {detailed_percent(used)} usado · {detailed_percent(remaining)} restante"
                + f"\n◷ {bucket} · {duration}"
                + f"\n↻ {relative} · {timestamp(reset)}")
            label.setToolTip(f"Valor bruto usado: {used!r}% · restante calculado: {remaining!r}%" if used is not None else "Percentual não informado pela fonte")
        if not windows:
            self.summary.setText(self.summary.text() + "\nNenhuma janela disponível nesta leitura.")
        extra = self._extra_text(display.get("details"))
        self.extras.setText(("◈ Consulta automática" + (" · leitura anterior" if previous else "") + "\n" + extra) if extra else "")
        balances = balance_evidence_sections(self.row_id)
        if balances:
            self.extras.setText(self.extras.text() + '\n\n' + '\n\n'.join(safe_text(title) + '\n' + safe_text(body) for title, body in balances))
        self.extras.setVisible(bool(extra or balances))
        technical = [f"Fonte: {safe_text(display.get('source'))}", f"Estado: {safe_text(status)}",
                     f"fetched_at: {safe_text(display.get('fetched_at'))}", f"Consulta em andamento: {'sim' if querying else 'não'}"]
        technical.extend(f"Janela: {safe_text(w.get('id'))} · duração: {number(w.get('duration_minutes'))!r} min · usado bruto: {number(w.get('used_percent'))!r}%"
                         for w in windows)
        self.technical.setText("\n".join(technical))
        self._refresh_observed()
        ready = getattr(self.owner, "_refresh_btn", None)
        enabled = ready.isEnabled() if ready is not None else not querying
        self.refresh_button.setEnabled(enabled and not getattr(self.owner, "_manual_refresh_locked", False))
        self.scroll.verticalScrollBar().setValue(scroll_value)

    @staticmethod
    def _bucket(window):
        if is_reserve(window):
            return "Reserva · não é uso geral"
        if theme.is_spark_window(window):
            return "Spark · cota separada"
        identifier = str(window.get("id", "")).lower()
        if identifier in {"five_hour", "seven_day", "session", "week", "weekly", "weekly_all", "daily", "monthly"} or identifier.startswith(("codex:", "tokens:", "time:", "credit_limit:", "time_limit:")):
            return "Uso geral"
        if identifier.startswith("weekly_scoped") or any(term in identifier for term in ("fable", "sonnet", "opus", "model")):
            return "Cota específica de modelo · não somar ao geral"
        return "Escopo não informado" if identifier else "Uso geral"

    @staticmethod
    def _extra_text(details):
        if not isinstance(details, dict):
            return ""
        root = details.get("root", details)  # Current provider contract is flat; accept an explicit root envelope too.
        if not isinstance(root, dict):
            return ""
        lines = []
        for item in root.get('resets') or []:
            if not isinstance(item,dict):continue
            condition='estoque informado; uso sujeito à elegibilidade da conta' if item.get('kind')=='account' else 'disponível agora' if item.get('usable') else 'indisponível agora'
            text=f'♻ {safe_text(item.get("title","Reset"))} · {item.get("count","—")} restante(s) · '+condition
            if item.get('expires_at'):text+=' · expira '+timestamp(item['expires_at'])
            lines.append(text)
        shares = root.get("product_shares")
        if isinstance(shares, list):
            for item in shares:
                if isinstance(item, dict) and item.get("name") and number(item.get("percent")) is not None:
                    lines.append(f"◉ Participação no consumo semanal · {safe_text(item['name'])}: {detailed_percent(item['percent'])} · não é saldo")
        financial = root.get("financial")
        if isinstance(financial, list):
            for item in financial:
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                amount = number(item.get("amount"))
                fields = [safe_text(item["title"])]
                if amount is not None:
                    fields.append(f"{safe_text(item.get('currency')) or 'moeda não informada'} {amount:g}")
                total = number(item.get("total"))
                if total is not None:
                    fields.append(f"total {total:g}")
                status = item.get("status")
                if status:
                    fields.append({"measured": "medido", "unavailable": "não informado",
                                   "unlimited": "sem limite informado"}.get(str(status), safe_text(status)))
                if item.get("note"):
                    fields.append(safe_text(item["note"]))
                if item.get("expires_at"):
                    fields.append("expira " + timestamp(item["expires_at"]))
                if len(fields) > 1:
                    lines.append("$ " + " · ".join(fields))
        if root.get("product_shares_as_of") and isinstance(shares, list) and shares:
            lines.append("◷ Participação apurada em " + timestamp(root["product_shares_as_of"]))
        notes = root.get("notes")
        if isinstance(notes, list):
            lines.extend("ℹ " + safe_text(note) for note in notes if isinstance(note, str) and note)
        return "\n".join(lines)

    def _refresh_observed(self):
        data = observed_info(self.row_id)
        sections = observed_sections(data)
        self.observed_toggle.setVisible(bool(sections))
        self.observed_body.setText("\n\n".join(safe_text(title) + "\n" + safe_text(body) for title, body in sections))
        self.observed_body.setVisible(bool(sections) and self.observed_toggle.isChecked())
        source_paths = tuple((data or {}).get("source_files") or ())
        if source_paths != self._source_paths:
            self._source_paths = source_paths
            while self.observed_sources_layout.count():
                item = self.observed_sources_layout.takeAt(0)
                item.widget().deleteLater()
            for index, relative in enumerate(source_paths):
                path = self._print_path(relative)
                if path is not None:
                    button = self._button(f"↗ Print {index + 1}", "Abrir print local fornecido como evidência",
                                          lambda checked=False, relative=relative: self._open_print(relative))
                    self.observed_sources_layout.addWidget(button)
        self.observed_sources.setVisible(bool(sections) and self.observed_toggle.isChecked())

    @staticmethod
    def _print_path(relative):
        if not isinstance(relative, str):
            return None
        # Only local, relative evidence paths; reject UNC/drive/URL inputs before resolve.
        if relative.startswith(("/", "\\")) or ":" in relative:
            return None
        root = paths.CENTRAL_DIR.resolve()
        path = (root / relative).resolve()
        if path.is_relative_to(root) and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.is_file():
            return path
        return None

    def _open_print(self, relative):
        path = self._print_path(relative)
        if path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _clamp_frame(self):
        if not self.isVisible():
            return
        screen = self.anchor.screen() or self.owner.screen()
        area = screen.availableGeometry()
        frame = self.frameGeometry()
        extra_w = max(0, frame.width() - self.width())
        extra_h = max(0, frame.height() - self.height())
        self.setMaximumSize(max(1, area.width() - extra_w), max(1, area.height() - extra_h))
        self.resize(min(self.width(), self.maximumWidth()), min(self.height(), self.maximumHeight()))
        frame = self.frameGeometry()
        x = max(area.left(), min(frame.left(), area.right() - frame.width() + 1))
        y = max(area.top(), min(frame.top(), area.bottom() - frame.height() + 1))
        self.move(self.pos() + QPoint(x - frame.left(), y - frame.top()))

    def open_at_anchor(self):
        screen = self.anchor.screen() or self.owner.screen()
        area = screen.availableGeometry()
        self.setMaximumSize(area.size())
        self.resize(min(550, area.width()), min(530, area.height()))
        self.move(self.anchor.mapToGlobal(QPoint(0, self.anchor.height())))
        self.show()
        self._clamp_frame()
        QTimer.singleShot(0, self, self._clamp_frame)
        QTimer.singleShot(10, self, self._clamp_frame)
        self.raise_()
        self.activateWindow()

    def done(self, result):
        super().done(result)
        self.owner.raise_()
        self.owner.activateWindow()
        if self.anchor.isVisible():
            self.anchor.setFocus(Qt.OtherFocusReason)
