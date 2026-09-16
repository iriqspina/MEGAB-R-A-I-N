"""Janela do widget Pendências — pill recolhida ↔ card expandido.

Convenções herdadas dos irmãos (Cotas IA / Agentes IA):
- Frameless + Tool + StaysOnTop, sem roubar foco (WA_ShowWithoutActivation).
- Arraste pelo cabeçalho; posição/opacidade/estado persistidos.
- Lê dados/pendencias.json SOMENTE (nunca escreve — regra de 260916).
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import persistence, theme
from . import registro as reg
from .paths import REGISTRY_PATH, SETTINGS_PATH, ensure_data_dir


def _idade_dias(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    return max(0, (datetime.now(dt.tzinfo or timezone.utc) - dt).days)


def _idade_curta(iso: str | None) -> str:
    d = _idade_dias(iso)
    if d is None:
        return "?"
    if d == 0:
        return "hoje"
    return f"{d}d" if d < 30 else f"{d // 30}m"


class DragHeader(QFrame):
    """Cabeçalho arrastável (padrão do Cotas IA, versão mínima)."""

    def __init__(self, on_drag_end, on_double_click=None, parent=None):
        super().__init__(parent)
        self._on_drag_end = on_drag_end
        self._on_double_click = on_double_click
        self._press = None

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press = e.globalPosition().toPoint() - self.window().pos()

    def mouseMoveEvent(self, e):
        if self._press is not None:
            self.window().move(e.globalPosition().toPoint() - self._press)

    def mouseReleaseEvent(self, e):
        if self._press is not None:
            self._press = None
            self._on_drag_end()

    def mouseDoubleClickEvent(self, e):
        if self._on_double_click is not None:
            self._on_double_click()


class MainWindow(QWidget):
    POLL_MIN = 15  # teto de segurança: nunca mais frequente que 15 s

    def __init__(self, demo: bool = False, session_only: bool = False):
        super().__init__()
        self.demo = demo
        self.settings = persistence.load(SETTINGS_PATH)
        self._session_only = session_only
        self._grupos: list[dict] = []
        self._ultimo_erro: str | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._card = QFrame()
        self._root.addWidget(self._card)
        self._lay = QVBoxLayout(self._card)
        self._lay.setContentsMargins(14, 10, 14, 10)
        self._lay.setSpacing(6)

        self._header = DragHeader(self._save_settings, on_double_click=self.alternar_expandido)
        h = QHBoxLayout(self._header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self._titulo = QLabel("Pendências")
        self._contagem = QLabel("…")
        self._btn_refresh = self._btn("⟳", "Atualizar agora")
        self._btn_collapse = self._btn("▾", "Recolher (Esc)")
        self._btn_refresh.clicked.connect(self._recarregar)
        self._btn_collapse.clicked.connect(self.alternar_expandido)
        h.addWidget(self._titulo)
        h.addWidget(self._contagem)
        h.addStretch(1)
        h.addWidget(self._btn_refresh)
        h.addWidget(self._btn_collapse)
        self._lay.addWidget(self._header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._corpo = QWidget()
        self._corpo.setObjectName("corpo")
        self._corpo_lay = QVBoxLayout(self._corpo)
        self._corpo_lay.setContentsMargins(0, 0, 0, 0)
        self._corpo_lay.setSpacing(8)
        self._corpo_lay.addStretch(1)
        self._scroll.setWidget(self._corpo)
        self._lay.addWidget(self._scroll, 1)

        self._rodape = QLabel("")
        self._rodape.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rodape.installEventFilter(self)
        self._lay.addWidget(self._rodape)

        self._poll = QTimer(self)
        self._poll.timeout.connect(self._recarregar)
        seg = max(self.POLL_MIN, int(self.settings.get("poll_seconds") or 60))
        self.settings["poll_seconds"] = seg
        self._poll.start(seg * 1000)

        self._aplicar_estilo()
        self._recarregar()

    # -- dados ----------------------------------------------------------------

    def _dados_demo(self) -> list[dict]:
        return [
            {"nome": "Marketeiro", "caminho": None, "ativo": True, "resumo": None,
             "proximo_passo": "crítica das 5 fichas do lote 1", "estado_mtime": "2026-09-09T12:00:00",
             "pausado_sugerido": False, "itens": []},
            {"nome": "Portfolio", "caminho": None, "ativo": True, "resumo": None,
             "proximo_passo": "<USUARIO> escolher base do comparativo", "estado_mtime": None,
             "pausado_sugerido": False,
             "itens": [{"id": "d1", "titulo": "mandar proposta Among Us", "criada_em": "2026-09-14T10:00:00"}]},
            {"nome": "Pets", "caminho": None, "ativo": False, "resumo": None, "proximo_passo": None,
             "estado_mtime": None, "pausado_sugerido": True, "itens": []},
        ]

    def _recarregar(self) -> None:
        try:
            if self.demo:
                self._grupos = self._dados_demo()
                self._ultimo_erro = None
            else:
                r = reg.Registro(Path(REGISTRY_PATH)).carregar()
                todos = r.resumo(incluir_pausados=True)
                ativos = [g for g in todos if g["ativo"]]
                pausados = [g for g in todos if not g["ativo"]]
                if self.settings.get("show_paused"):
                    self._grupos = ativos + pausados
                else:
                    self._grupos = ativos
                self._pausados_n = len(pausados)
                self._raiz = r.dados.get("raiz")
                self._reg_ok = True
                self._ultimo_erro = None
        except (reg.ErroRegistro, OSError) as e:
            self._reg_ok = False
            self._ultimo_erro = str(e)
            # mantém a última lista válida na tela (critério da pesquisa)
        self._reconstruir()
        self._rodape_atualizar()

    # -- construção da UI -------------------------------------------------------

    def _btn(self, glifo: str, tooltip: str) -> QPushButton:
        b = QPushButton(glifo)
        b.setFixedSize(22, 22)
        b.setToolTip(tooltip)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return b

    def _reconstruir(self) -> None:
        limpar(self._corpo_lay)
        visiveis = 0
        for g in self._grupos:
            # radar: só entra quem TEM pendência (item manual ou próximo passo)
            if not (g["itens"] or g["proximo_passo"]):
                continue
            self._corpo_lay.addLayout(self._grupo(g))
            visiveis += 1
        if visiveis == 0:
            if self._ultimo_erro:
                msg = f"arquivo com problema: {self._ultimo_erro[:60]}"
            elif self._grupos:
                msg = "nenhuma pendência aberta — projetos sem pendência ficam fora do radar"
            else:
                msg = "nada pendente ainda — rode bin/mb-pendencias.py scan"
            vazio = QLabel(msg)
            vazio.setObjectName("faint")
            vazio.setWordWrap(True)
            self._corpo_lay.insertWidget(0, vazio)
        self._corpo_lay.addStretch(1)

        itens, projetos = self._contar()
        if self._ultimo_erro:
            self._contagem.setText(f"· {itens} (arquivo com problema)")
            self._contagem.setToolTip(self._ultimo_erro)
        else:
            self._contagem.setText(f"· {itens} em {projetos}")
        self._set_expandido(bool(self.settings.get("expanded")))

    def _contar(self) -> tuple[int, int]:
        ativos = [g for g in self._grupos if g["ativo"]]
        itens = sum(len(g["itens"]) + (1 if g["proximo_passo"] else 0) for g in ativos)
        projetos = sum(1 for g in ativos if g["itens"] or g["proximo_passo"])
        return itens, projetos

    def _grupo(self, g: dict) -> QHBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(2)
        topo = QHBoxLayout()
        topo.setSpacing(6)
        nome = QLabel(g["nome"].upper())
        nome.setObjectName("grupo")
        n = len(g["itens"]) + (1 if g["proximo_passo"] else 0)
        badge = QLabel(str(n) if n else "·")
        badge.setObjectName("badge")
        topo.addWidget(nome)
        topo.addWidget(badge)
        topo.addStretch(1)
        if g.get("pausado_sugerido") and g["ativo"]:
            sug = QLabel("sugere pausar")
            sug.setObjectName("sugestao")
            sug.setToolTip("ESTADO.md diz pausado/não retomar — pausa pelo /pendencias ou botão")
            topo.addWidget(sug)
        if not g["ativo"]:
            off = QLabel("pausado")
            off.setObjectName("off")
            topo.addWidget(off)
        col.addLayout(topo)

        if g["proximo_passo"]:
            col.addWidget(self._linha(g, "auto", g["proximo_passo"], g.get("estado_mtime")))
        for i in g["itens"]:
            col.addWidget(self._linha(g, "item", i["titulo"], i.get("criada_em")))
        wrap = QHBoxLayout()
        wrap.addLayout(col, 1)
        return wrap

    def _linha(self, g: dict, tipo: str, titulo: str, quando: str | None) -> QLabel:
        curto = titulo if len(titulo) <= 90 else titulo[:89] + "…"
        idade = _idade_curta(quando)
        lbl = QLabel()
        lbl.setObjectName(tipo)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setText(
            f'<span style="color:{theme.rgba(theme.INK if tipo != "auto" else theme.INK_FAINT)};">{html.escape(curto)}</span>'
            f'&nbsp;&nbsp;<span style="color:{theme.rgba(theme.cor_idade(quando))};">{html.escape(idade)}</span>'
        )
        lbl.setToolTip(f"{titulo}\n{idade} · duplo clique abre a pasta do projeto")
        lbl.setWordWrap(False)
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl.installEventFilter(self)
        lbl.setProperty("caminho", g.get("caminho"))
        return lbl

    def _rodape_atualizar(self) -> None:
        hora = datetime.now().strftime("%H:%M")
        partes = [f"atualizado {hora}"]
        if self.demo:
            partes.append("DEMO")
        if getattr(self, "_pausados_n", 0):
            estado = "mostrar" if not self.settings.get("show_paused") else "ocultar"
            partes.append(f"pausados: {self._pausados_n} ({estado})")
        self._rodape.setText("  ·  ".join(partes))

    # -- interação ----------------------------------------------------------------

    def eventFilter(self, obj, ev):
        if obj is self._rodape and ev.type() == QEvent.Type.MouseButtonRelease:
            self.settings["show_paused"] = not self.settings.get("show_paused", False)
            self._recarregar()
            self._save_settings()
            return True
        if isinstance(obj, QLabel) and ev.type() == QEvent.Type.MouseButtonDblClick:
            caminho = obj.property("caminho")
            if caminho and Path(caminho).is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))
            return True
        return super().eventFilter(obj, ev)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._set_expandido(False)
        super().keyPressEvent(e)

    def _set_expandido(self, valor: bool) -> None:
        self.settings["expanded"] = valor
        self._scroll.setVisible(valor)
        self._rodape.setVisible(valor)
        self._btn_collapse.setText("▴" if not valor else "▾")
        self._btn_collapse.setToolTip("Expandir" if not valor else "Recolher (Esc)")
        if not valor:
            self._titulo.setText("Pendências")
        self.adjustSize()
        self._clamp()

    def alternar_expandido(self) -> None:
        self._set_expandido(not self.settings.get("expanded"))

    # -- janela ----------------------------------------------------------------

    def _clamp(self) -> None:
        geo = QApplication.primaryScreen().availableGeometry()
        pos = self.pos()
        x = min(max(pos.x(), geo.left()), max(geo.left(), geo.right() - self.width()))
        y = min(max(pos.y(), geo.top()), max(geo.top(), geo.bottom() - self.height()))
        self.move(x, y)

    def show_positioned(self) -> None:
        geo = QApplication.primaryScreen().availableGeometry()
        x = self.settings.get("pos_x")
        y = self.settings.get("pos_y")
        if x is None or y is None:
            x, y = geo.right() - 380, geo.top() + 90
        self.move(int(x), int(y))
        self.show()
        self._clamp()

    def _save_settings(self) -> None:
        self.settings["pos_x"], self.settings["pos_y"] = self.x(), self.y()
        if self._session_only:
            return
        ensure_data_dir()
        persistence.save(SETTINGS_PATH, self.settings)

    def closeEvent(self, e):
        self._save_settings()
        super().closeEvent(e)

    # -- estilo ----------------------------------------------------------------

    def _aplicar_estilo(self) -> None:
        op = int(self.settings.get("opacity_percent") or theme.DEFAULT_OPACITY_PERCENT) / 100
        bg = f"rgba({theme.BG_BASE[0]}, {theme.BG_BASE[1]}, {theme.BG_BASE[2]}, {op:.3f})"
        self._card.setStyleSheet(
            f"""
            QFrame {{ background: {bg}; border: 1px solid {theme.rgba(theme.BORDER)};
                      border-radius: {theme.CORNER_RADIUS}px; }}
            QLabel {{ color: {theme.rgba(theme.INK)}; font-family: "{theme.FONT_FAMILY}";
                      font-size: {theme.SIZE_ITEM}px; background: transparent; border: none; }}
            QLabel#grupo {{ color: {theme.rgba(theme.INK_FAINT)}; font-size: {theme.SIZE_GROUP}px;
                            letter-spacing: 1px; }}
            QLabel#badge {{ color: {theme.rgba(theme.INK_FAINT)}; font-size: {theme.SIZE_GROUP}px; }}
            QLabel#faint, QLabel#resumo {{ color: {theme.rgba(theme.INK_DIM)}; }}
            QLabel#resumo {{ font-size: {theme.SIZE_HINT}px; }}
            QLabel#sugestao {{ color: {theme.rgba(theme.STATUS_AMBER)}; font-size: {theme.SIZE_GROUP}px; }}
            QLabel#off {{ color: {theme.rgba(theme.INK_DIM)}; font-size: {theme.SIZE_GROUP}px; }}
            QLabel#titulo {{ font-size: {theme.SIZE_TITLE}px; font-weight: 600; }}
            QPushButton {{ color: {theme.rgba(theme.INK_FAINT)}; background: transparent; border: none;
                           font-size: 13px; }}
            QPushButton:hover {{ color: {theme.rgba(theme.INK)}; }}
            QScrollArea {{ background: transparent; border: none; }}
            QWidget#corpo {{ background: transparent; }}
            """
        )
        self._titulo.setObjectName("titulo")
        self._contagem.setObjectName("faint")
        self.setMaximumHeight(int(QApplication.primaryScreen().availableGeometry().height() * 0.6))
        self.setMinimumWidth(300)
        self.setMaximumWidth(360)


def limpar(lay: QVBoxLayout) -> None:
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w is not None:
            w.deleteLater()
        elif item.layout() is not None:
            limpar(item.layout())
