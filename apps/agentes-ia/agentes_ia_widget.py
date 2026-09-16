#!/usr/bin/env python3
# Widget "Agentes IA" (260916 v4 — grupos + formações + névoa mística + grip).
#
# UNIVERSO VAZADO COM GRUPOS (design aprovado pelo dono, 260916):
#   • Cada sessão vira um GRUPO: orquestrador hexagonal com glow da fase +
#     CARD "asa" ao lado (haste vertical colorida + textos flutuantes com
#     contorno, sem caixa preenchida). Tudo nativo PySide6, sem fundo/painel.
#   • FORMAÇÕES GEOMÉTRICAS: 1=foco, 2=par, 3=triângulo, 4=quadrado,
#     5=pentágono, 6=anel, 7+=grade. A câmera só se move na troca de
#     formação (ou no botão "Visão geral"), nunca a cada evento.
#   • NÉVOA MÍSTICA ÚNICA: um gradiente radial elíptico (azul-noite/violeta/
#     ciano-petróleo) sob toda a composição — centro visível, bordas 100%
#     transparentes; opacidade ajustável (0 = widget sem fundo).
#   • GRIP BOLINHA: canto inferior direito redimensiona a área do widget
#     como janela de app, sem estrutura (contorno tracejado só no arrasto).
#   • Cliques fora dos elementos passam pro desktop (setMask).
# Fonte: server do board (localhost:3001) via SSE. Fechar mata o server.
# Reversão: apagar apps/agentes-ia/ e ~/.agentes-ia/.
import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from PySide6.QtCore import (
    QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal,
    QEasingCurve, QVariantAnimation, QAbstractAnimation,
)
from PySide6.QtGui import (
    QColor, QCursor, QFont, QPainter, QPainterPath, QPen, QPolygonF,
    QRadialGradient, QRegion, QTransform, QBrush,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication, QGraphicsDropShadowEffect, QGraphicsEllipseItem,
    QGraphicsScene, QGraphicsView, QGraphicsWidget, QHBoxLayout, QLabel,
    QMenu, QSlider, QVBoxLayout, QWidget,
)

APP_NAME = "Agentes IA"
BOARD_URL = "http://localhost:3001"
SSE_URL = BOARD_URL + "/events"
SINGLETON_KEY = "megabrain-agentes-ia"
SETTINGS_PATH = Path.home() / ".agentes-ia" / "settings.json"
_CENTRAL = Path(__file__).resolve().parents[1]  # cada maquina resolve a sua
MB_BOARD = _CENTRAL / "bin" / "mb-board.ps1"
APP_DIST = Path(os.environ.get("LOCALAPPDATA", "")) / (
    "npm-cache/_npx/23b47ad77b53d45f/node_modules/agent-flow-app/dist/app.js")
ROOT_PROJETOS = str(_CENTRAL.parent)
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

FASE_LEIGO = {
    "recebendo": "Recebendo tarefa",
    "pensando": "Pensando",
    "trabalhando": "Trabalhando",
    "conferindo": "Conferindo",
    "concluído": "Concluído",
    "erro": "Com erro",
    "parado": "À espera",
}
TOOL_LEIGO = {
    "bash": "Executando comando", "exec": "Executando comando",
    "read": "Lendo arquivo", "read_file": "Lendo arquivo",
    "write": "Editando arquivo", "edit": "Editando arquivo",
    "write_file": "Editando arquivo", "edit_block": "Editando arquivo",
    "grep": "Pesquisando", "glob": "Pesquisando", "search": "Pesquisando",
    "webfetch": "Consultando fonte", "websearch": "Pesquisando na web",
    "task": "Coordenando subagente", "agent": "Coordenando subagente",
}
CORES_FASE = {
    "Pensando": "#7db4ff", "Trabalhando": "#ffd166", "Concluído": "#7ce38b",
    "Com erro": "#ff6b6b", "À espera": "#b8b8c8", "Recebendo tarefa": "#b39bff",
    "Conferindo": "#ffa8f0",
}
ORQ_R = 34            # raio do orquestrador hexagonal
CARD_W = 208          # largura do card "asa"
GRP_W = ORQ_R * 2 + 18 + CARD_W
GRP_H = 108
GRP_H_COLLAPSED = ORQ_R * 2 + 6
MARGEM_FIT = 40
FADE_CONCLUIDO_S = 8
FADE_SEM_EVENTOS_S = 600
ZOOM_MIN, ZOOM_MAX = 0.5, 7.0
FORM_MS = 420         # duração da transição de formação (design)
NEVOA_PADRAO = 30     # opacidade da névoa mística (0 = sem fundo)
NEVOA_PICO = 0.55     # pico de alpha com slider em 100 (design)


def load_settings():
    padrao = {"topmost": True, "cards": {}, "nevoa": NEVOA_PADRAO,
              "area": None, "orbita": True}
    try:
        padrao.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    padrao.setdefault("cards", {})
    return padrao


def save_settings(s):
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def server_no_ar():
    c = socket.socket()
    c.settimeout(0.6)
    try:
        return c.connect_ex(("127.0.0.1", 3001)) == 0
    finally:
        c.close()


def subir_server():
    if server_no_ar():
        return False
    if APP_DIST.exists():
        subprocess.Popen(["node", str(APP_DIST)], cwd=ROOT_PROJETOS,
                         creationflags=CREATE_NO_WINDOW,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                          "-File", str(MB_BOARD)], creationflags=CREATE_NO_WINDOW)
    for _ in range(45):
        if server_no_ar():
            return True
        time.sleep(1)
    return False


def parar_server():
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", str(MB_BOARD), "-Parar"], creationflags=CREATE_NO_WINDOW)


def tool_leigo(tool):
    t = (tool or "").lower()
    for k, v in TOOL_LEIGO.items():
        if k in t:
            return v
    return "Trabalhando"


def snippet(payload, n=90):
    try:
        s = json.dumps(payload, ensure_ascii=False)
    except Exception:
        s = str(payload)
    s = re.sub(r"\s+", " ", s)
    return s[:n] + ("…" if len(s) > n else "")


class SseWorker:
    def __init__(self):
        self.fila = []
        self._lock = threading.Lock()
        self._th = threading.Thread(target=self._roda, daemon=True)

    def start(self):
        self._th.start()

    def drenar(self):
        with self._lock:
            itens, self.fila = self.fila, []
        return itens

    def _roda(self):
        while True:
            try:
                req = urllib.request.Request(SSE_URL, headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=3600) as resp:
                    for linha in resp:
                        linha = linha.decode("utf-8", "replace").strip()
                        if linha.startswith("data: "):
                            try:
                                with self._lock:
                                    self.fila.append(json.loads(linha[6:]))
                                    if len(self.fila) > 500:
                                        del self.fila[:len(self.fila) - 500]
                            except Exception:
                                pass
            except Exception:
                time.sleep(2)


class ModeloSessoes(QObject):
    mudou = Signal()

    def __init__(self):
        super().__init__()
        self.sessoes = {}

    def _base(self, sid):
        if sid not in self.sessoes:
            self.sessoes[sid] = {"label": "", "projeto": "", "fase": "recebendo",
                                 "acao": "À espera do primeiro comando", "etapa": 0,
                                 "fonte": "", "ts": time.time()}
        return self.sessoes[sid]

    def ingest(self, frame):
        tipo = frame.get("type")
        if tipo == "session-list":
            vivos = {s.get("id") for s in frame.get("sessions", [])}
            for s in frame.get("sessions", []):
                base = self._base(s.get("id"))
                if s.get("label"):
                    base["label"] = s["label"]
                if s.get("status") == "completed":
                    base["fase"] = "concluído"
                fonte = ""
                if (s.get("label") or "").startswith("[zcode]"):
                    fonte = "ZCode"
                elif (s.get("label") or "").startswith("[startup]"):
                    fonte = "Claude"
                elif base.get("fonte") == "":
                    fonte = "Claude"
                if fonte:
                    base["fonte"] = fonte
            for sid in list(self.sessoes):
                if sid not in vivos and self.sessoes[sid]["fase"] != "concluído":
                    self.sessoes[sid]["fase"] = "concluído"
        if tipo == "session-ended":
            base = self._base(frame.get("sessionId"))
            base["fase"] = "concluído"
            base["logout"] = True   # sai da visão geral imediatamente
            self.mudou.emit()
            return
        ev = frame.get("event") or {}
        sid = ev.get("sessionId")
        if not sid:
            return
        base = self._base(sid)
        base["ts"] = time.time()
        t = ev.get("type", "")
        pay = ev.get("payload") or {}
        if t == "agent_spawn":
            base["fase"] = "pensando"
            if pay.get("task"):
                base["acao"] = str(pay["task"])[:90]
            if not pay.get("isMain", True):
                base["filhos"] = base.get("filhos", 0) + 1
                base["filhos_total"] = base.get("filhos_total", 0) + 1
        elif t == "tool_call_start":
            base["fase"] = "trabalhando"
            base["acao"] = tool_leigo(pay.get("tool"))
            base["tool"] = pay.get("tool") or ""
            base["snippet"] = snippet(pay.get("args"))
        elif t == "tool_call_end":
            base["etapa"] = base.get("etapa", 0) + 1
            resultado = str(pay.get("result", ""))
            if pay.get("isError") or "[FAILED]" in resultado:
                base["fase"] = "erro"
            elif base["fase"] != "erro":
                base["fase"] = "conferindo"
        elif t == "agent_complete":
            if pay.get("isMain"):
                base["fase"] = "concluído"
            else:
                base["etapa"] = base.get("etapa", 0) + 1
                base["filhos"] = max(0, base.get("filhos", 1) - 1)
        elif t == "error" or "erro" in t:
            base["fase"] = "erro"
        self.mudou.emit()

    def lista(self):
        return sorted(self.sessoes.items(), key=lambda kv: -kv[1]["ts"])


class CartaoIA(QGraphicsWidget):
    """GRUPO de uma sessão: orquestrador hexagonal + card "asa" + dashboardzinho.
    Filhos (subagentes) orbitam: modo completo (até 6 mini-hexágonos girando)
    ou leve (1 ícone devagar + badge com o total) — toggle na pill."""
    ARRASTOU = Signal(str, float, float)
    PEDIU_OCULTAR = Signal(str)
    PEDIU_FOCO = Signal(str)
    MUDOU_GEOMETRIA = Signal(str, bool)
    ANGULO = 0.0        # ângulo da órbita (animado pelo Universo)
    MODO_ORBITA = True  # True = completa; False = leve

    def __init__(self, sid):
        super().__init__()
        self.sid = sid
        self.collapsed = False
        self.dados = {}
        self._off = None
        self.resize(GRP_W, GRP_H)
        self.setCursor(Qt.OpenHandCursor)
        self._sombra = QGraphicsDropShadowEffect(self)
        self._sombra.setBlurRadius(18)
        self._sombra.setOffset(0, 0)
        self._sombra.setColor(QColor(125, 180, 255, 120))
        self.setGraphicsEffect(self._sombra)
        self._fade = None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._off = ev.scenePos() - self.pos()
            self._pos0 = self.pos()
            self.setZValue(min(self.zValue() + 1, 100))
        ev.accept()

    def mouseMoveEvent(self, ev):
        if self._off is not None:
            nova = ev.scenePos() - self._off
            self.setPos(round(nova.x(), 1), round(nova.y(), 1))
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if self._off is not None:
            self._off = None
            # só emite ARRASTOU se moveu de verdade (fix revisão #14)
            if self.pos() != getattr(self, "_pos0", self.pos()):
                self.ARRASTOU.emit(self.sid, self.x(), self.y())
        ev.accept()

    def mouseDoubleClickEvent(self, ev):
        self.collapsed = not self.collapsed
        self.resize(GRP_W, GRP_H_COLLAPSED if self.collapsed else GRP_H)
        self.update()
        self.MUDOU_GEOMETRIA.emit(self.sid, self.collapsed)
        ev.accept()

    def contextMenuEvent(self, ev):
        m = QMenu()
        a_focar = m.addAction("Focar neste processo")
        a_ocultar = m.addAction("Esconder este processo")
        a_zerar = m.addAction("Zerar contagem de etapas")
        esc = m.exec(ev.screenPos())
        if esc is a_focar:
            self.PEDIU_FOCO.emit(self.sid)
        elif esc is a_ocultar:
            self.PEDIU_OCULTAR.emit(self.sid)
        elif esc is a_zerar:
            self.dados["etapa"] = 0
            self.update()

    def set_dados(self, d):
        self.dados = d
        fase = FASE_LEIGO.get(d.get("fase", "recebendo"), "Recebendo tarefa")
        cor = QColor(CORES_FASE.get(fase, "#7db4ff"))
        self._sombra.setColor(QColor(cor.red(), cor.green(), cor.blue(), 170))
        projeto = d.get("projeto") or d.get("label") or "Processo"
        self.setToolTip(f"{projeto}\n{d.get('acao', 'À espera')}\n{fase} · "
                        f"{d.get('etapa', 0)} etapas")
        self.update()

    def sumir(self):
        if self._fade is not None:
            return
        self._fade = QVariantAnimation(self)
        self._fade.setStartValue(1.0)
        self._fade.setEndValue(0.0)
        self._fade.setDuration(700)
        self._fade.setEasingCurve(QEasingCurve.OutQuad)
        self._fade.valueChanged.connect(self.setOpacity)
        cena = self.scene()
        self._fade.finished.connect(lambda: (cena.removeItem(self), self.deleteLater()))
        self._fade.start(QAbstractAnimation.DeleteWhenStopped)

    # ---- visual ----

    def _texto(self, p, rect, texto, cor, tam, peso=None, alinh=None):
        """Texto com contorno escuro (legível em qualquer wallpaper)."""
        f = QFont("Segoe UI", tam)
        if peso:
            f.setWeight(peso)
        p.setFont(f)
        flags = alinh if alinh is not None else (Qt.AlignLeft | Qt.AlignVCenter)
        p.setPen(QColor(8, 10, 16, 230))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, 1), (1, 0)):
            p.drawText(rect.translated(dx, dy), flags, texto)
        p.setPen(cor)
        p.drawText(rect, flags, texto)

    def paint(self, painter, option, widget=None):
        p = painter
        p.setRenderHint(QPainter.Antialiasing)
        fase = FASE_LEIGO.get(self.dados.get("fase", "recebendo"), "Recebendo tarefa")
        cor = QColor(CORES_FASE.get(fase, "#7db4ff"))
        r = self.rect()
        # --- orquestrador: hexágono com anéis ---
        cx, cy = ORQ_R + 6, r.height() / 2
        pontos = QPolygonF()
        for i in range(6):
            a = math.radians(60 * i + 30)
            pontos.append(QPointF(cx + (ORQ_R - 2) * math.cos(a),
                                  cy + (ORQ_R - 2) * math.sin(a)))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(cor.red(), cor.green(), cor.blue(), 34))
        path_atm = QPainterPath()
        path_atm.addPolygon(pontos)
        p.drawPath(path_atm.translated(0, 0))
        # atmosfera hexagonal um pouco maior
        atm = QPolygonF()
        for i in range(6):
            a = math.radians(60 * i + 30)
            atm.append(QPointF(cx + (ORQ_R + 5) * math.cos(a),
                               cy + (ORQ_R + 5) * math.sin(a)))
        p.drawPolygon(atm)
        # corpo
        p.setBrush(QColor(14, 17, 26, 225))
        p.setPen(QPen(cor, 1.8))
        p.drawPolygon(pontos)
        # conteúdo do hexágono: fonte micro + etapas
        fonte_origem = (self.dados.get("fonte") or "")[:6].upper()
        etapas = str(self.dados.get("etapa", 0))
        filhos = int(self.dados.get("filhos", 0) or 0)
        if self.collapsed:
            self._texto(p, QRectF(cx - ORQ_R, cy - 8, 2 * ORQ_R, 16),
                        etapas, cor, 9, QFont.DemiBold, Qt.AlignCenter)
            return
        if fonte_origem:
            self._texto(p, QRectF(cx - ORQ_R, cy - 26, 2 * ORQ_R, 12),
                        fonte_origem, cor, 6, None, Qt.AlignCenter)
        self._texto(p, QRectF(cx - ORQ_R, cy - 6, 2 * ORQ_R, 14),
                    etapas + " etapas", QColor("#cfe3f5"), 6, None, Qt.AlignCenter)
        # --- filhos orbitando (subagentes da sessão) ---
        raio_orb = ORQ_R + 15
        def mini_hex(fx, fy, r=6):
            pts = QPolygonF()
            for i in range(6):
                a = math.radians(60 * i + 30)
                pts.append(QPointF(fx + r * math.cos(a), fy + r * math.sin(a)))
            p.setBrush(QColor(cor.red(), cor.green(), cor.blue(), 215))
            p.setPen(QPen(QColor(16, 18, 28, 200), 1))
            p.drawPolygon(pts)
        if CartaoIA.MODO_ORBITA:
            n = min(filhos, 6)
            for i in range(n):
                a = CartaoIA.ANGULO + i * (2 * math.pi / max(n, 1))
                mini_hex(cx + raio_orb * math.cos(a), cy + raio_orb * math.sin(a))
        elif filhos > 0:
            a = CartaoIA.ANGULO * 0.16  # 1 ícone orbitando devagar
            mini_hex(cx + raio_orb * math.cos(a), cy + raio_orb * math.sin(a), 5)
        if filhos > 0:
            # badge com a quantidade de agentes/subs da sessão
            bx, by = cx + ORQ_R - 4, cy - ORQ_R + 2
            p.setBrush(QColor(12, 14, 22, 235))
            p.setPen(QPen(cor, 1.4))
            p.drawEllipse(QPointF(bx, by), 9, 9)
            self._texto(p, QRectF(bx - 9, by - 7, 18, 14), str(filhos),
                        QColor("#eef6ff"), 7, QFont.DemiBold, Qt.AlignCenter)
        # --- card "asa": véu sutil de legibilidade + haste + textos ---
        projeto = (self.dados.get("projeto") or self.dados.get("label")
                   or "Processo")
        projeto = projeto[:18] + ("…" if len(projeto) > 18 else "")
        acao = (self.dados.get("acao") or "À espera")[:26]
        x0 = ORQ_R * 2 + 14
        # véu escuro arredondado atrás da zona de texto: o contorno fino
        # sozinho vira sopa sobre página clara (revisão UX 260916)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(9, 12, 19, 158))
        p.drawRoundedRect(QRectF(x0 - 6, 4, CARD_W + 8, r.height() - 8), 10, 10)
        p.setBrush(cor)
        p.drawRoundedRect(QRectF(x0, 8, 3.5, r.height() - 16), 2, 2)
        y = 6
        fonte_txt = (self.dados.get("fonte") or "IA").upper()
        self._texto(p, QRectF(x0 + 12, y, 150, 13), fonte_txt, cor, 6)
        y += 15
        self._texto(p, QRectF(x0 + 12, y, 190, 18), projeto,
                    QColor("#eef6ff"), 10, QFont.DemiBold)
        y += 26
        self._texto(p, QRectF(x0 + 12, y, 192, 16), acao,
                    QColor("#dceaf7"), 8)
        y += 24
        self._texto(p, QRectF(x0 + 12, y, 150, 14),
                    f"{fase} · {filhos} agente(s)", cor, 7, QFont.DemiBold)
        rodape = f"{etapas} etapas"
        self._texto(p, QRectF(x0 + 130, y, 66, 14), rodape,
                    QColor("#9fb4c8"), 6, None, Qt.AlignRight)
        # dashboardzinho: barra fina de progresso da sessão na base do card
        prog = min(int(self.dados.get("etapa", 0) or 0), 30) / 30.0
        bw = CARD_W + 2
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 36))
        p.drawRoundedRect(QRectF(x0 - 5, r.height() - 11, bw, 4), 2, 2)
        p.setBrush(cor)
        p.drawRoundedRect(QRectF(x0 - 5, r.height() - 11, max(6.0, bw * prog), 4), 2, 2)


class PopupGhost(QWidget):
    """Trecho do último comando sobe perto do grupo e some (fantasma)."""
    def __init__(self, texto, centro_global):
        super().__init__(None)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(330, 52)
        self.texto = texto
        self._op = 0.95
        self.move(max(0, centro_global.x() - 165), max(0, centro_global.y() - 96))
        self.show()
        self._t = QTimer(self)
        self._t.timeout.connect(self._fada)
        self._t.start(60)

    def _fada(self):
        self._op -= 0.045
        if self._op <= 0:
            self.close()
            self.deleteLater()
        else:
            self.setWindowOpacity(self._op)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(10, 12, 20, int(210 * self._op)))
        p.setPen(QPen(QColor(122, 180, 255, int(90 * self._op)), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 8, 8)
        p.setPen(QColor(150, 220, 180, int(220 * self._op)))
        p.setFont(QFont("Consolas", 8))
        p.drawText(self.rect().adjusted(10, 6, -10, -6), Qt.TextWordWrap | Qt.AlignTop,
                   self.texto[:140])


def formacao_slots(n):
    """Posições relativas (em unidades U) da formação geométrica para n grupos.
    Tabela do design aprovado: 1 foco; 2 par; 3 triângulo; 4 quadrado;
    5 pentágono; 6 anel; 7+ grade 3 colunas."""
    if n <= 1:
        return [(0.0, 0.0)]
    if n == 2:
        return [(-0.62, 0.0), (0.62, 0.0)]
    if n == 3:
        return [(0.0, -0.52), (-0.66, 0.42), (0.66, 0.42)]
    if n == 4:
        return [(-0.6, -0.48), (0.6, -0.48), (-0.6, 0.48), (0.6, 0.48)]
    if n == 5:
        return [(0.95 * math.cos(math.radians(-90 + 72 * k)),
                 0.72 * math.sin(math.radians(-90 + 72 * k)))
                for k in range(5)]
    if n == 6:
        return [(0.90 * math.cos(math.radians(60 * k - 90)),
                 0.80 * math.sin(math.radians(60 * k - 90))) for k in range(6)]
    # 7+: grade de 3 colunas
    slots = []
    for i in range(n):
        c, l = divmod(i, 3)
        slots.append(((c - (n - 1) // 6) * 1.15, (l - 1) * 1.05))
    return slots


class Universo(QGraphicsView):
    """Cena invisível com grupos, formações, névoa mística e câmera."""
    mudou = Signal()

    def __init__(self, modelo, settings, parent=None):
        super().__init__(parent)
        self.modelo = modelo
        self.settings = settings
        self.cena = QGraphicsScene(self)
        self.cena.setBackgroundBrush(Qt.NoBrush)
        self.setScene(self.cena)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setStyleSheet("QGraphicsView{background:transparent;border:none;}")
        self.viewport().setAutoFillBackground(False)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.cartoes = {}
        self._anims = {}
        self._n_formacao = -1
        self._timer_form = QTimer(self)      # janela de 250 ms pra agrupar mudanças
        self._timer_form.setSingleShot(True)
        self._timer_form.timeout.connect(self._aplicar_formacao)
        # névoa mística única (atrás de tudo)
        self.nevoa = QGraphicsEllipseItem()
        self.nevoa.setZValue(-100)
        self.nevoa.setPen(Qt.NoPen)          # sem contorno na borda do fade
        self.nevoa.setFlag(QGraphicsEllipseItem.ItemIsSelectable, False)
        self.cena.addItem(self.nevoa)
        self._atualizar_nevoa()
        # animação da órbita dos filhos (barato: <8 grupos, 60 ms)
        self._t_orb = QTimer(self)
        self._t_orb.timeout.connect(self._tick_orbita)
        self._t_orb.start(60)

    def _tick_orbita(self):
        if not self.cartoes:
            return
        CartaoIA.ANGULO = (CartaoIA.ANGULO + 0.05) % (2 * math.pi)
        for c in self.cartoes.values():
            c.update()
        # máscara viva: acompanha órbita, arrasto e animação (fix revisão #12)
        w = self.window()
        if isinstance(w, WidgetIA):
            w._aplicar_mascara()

    # ---- cartões/grupos ----

    def _cartao(self, sid):
        if sid not in self.cartoes:
            c = CartaoIA(sid)
            pos = self.settings["cards"].get(sid) or {}
            c.setPos(pos.get("x", 40 + 42 * (len(self.cartoes) % 6)),
                     pos.get("y", 30 + 46 * (len(self.cartoes) // 6)))
            c.collapsed = bool(pos.get("collapsed"))
            c.resize(GRP_W, GRP_H_COLLAPSED if c.collapsed else GRP_H)
            c.ARRASTOU.connect(self._soltou)
            c.PEDIU_OCULTAR.connect(self._ocultar)
            c.PEDIU_FOCO.connect(self.focar)
            c.MUDOU_GEOMETRIA.connect(self._colapso_mudou)
            self.cena.addItem(c)
            c.show()
            self.cartoes[sid] = c
        return self.cartoes[sid]

    def _ocultar(self, sid):
        anim = self._anims.pop(sid, None)   # mata animação órfã (fix #15)
        if anim is not None:
            anim.stop()
        if sid in self.cartoes:
            c = self.cartoes.pop(sid)
            self.cena.removeItem(c)
            c.deleteLater()
        self.settings["cards"].setdefault(sid, {})["hidden"] = True
        save_settings(self.settings)
        self.mudou.emit()
        self._pedir_formacao()

    def reexibir_todos(self):
        for sid in list(self.settings["cards"]):
            self.settings["cards"][sid]["hidden"] = False
        save_settings(self.settings)
        self.atualizar()

    def _soltou(self, sid, x, y):
        self.settings["cards"].setdefault(sid, {})
        self.settings["cards"][sid].update(x=x, y=y)
        save_settings(self.settings)
        self._atualizar_nevoa()          # névoa acompanha o drag (fix #12)
        self._n_formacao = -1  # drag manual encerra a formação vigente
        self.mudou.emit()

    def _colapso_mudou(self, sid, colapsado):
        # fix da revisão: colapso precisa persistir (senão perde no reboot)
        self.settings["cards"].setdefault(sid, {})["collapsed"] = colapsado
        save_settings(self.settings)
        self.mudou.emit()

    # ---- formações geométricas ----

    def _pedir_formacao(self):
        self._timer_form.start(250)  # agrupa chegadas/saídas rápidas

    def _aplicar_formacao(self):
        grupos = [c for c in self.cartoes.values() if c.isVisible()]
        n = len(grupos)
        if n == 0:
            self._atualizar_nevoa()
            self.mudou.emit()
            return
        Ux, Uy = GRP_W + 30, GRP_H + 26
        # slots centrados (canto sup-esq -> centro do grupo) — fix revisão #11
        slots = [(sx * Ux - GRP_W / 2, sy * Uy - GRP_H / 2)
                 for sx, sy in formacao_slots(n)]
        # menor deslocamento total: casamento guloso por proximidade
        restantes = list(grupos)
        for sx, sy in slots:
            alvo = min(restantes, key=lambda c: (c.x() - sx) ** 2 + (c.y() - sy) ** 2)
            restantes.remove(alvo)
            self._animar_para(alvo, QPointF(sx, sy))
        self._n_formacao = n
        QTimer.singleShot(FORM_MS + 40, self._pos_formacao)

    def _pos_formacao(self):
        if not self.cartoes:
            return
        self._atualizar_nevoa()
        self.visao_geral()

    def _animar_para(self, item, destino):
        anim = self._anims.get(item.sid)
        if anim is not None:
            anim.stop()
        a = QVariantAnimation(self)
        a.setStartValue(item.pos())
        a.setEndValue(destino)
        a.setDuration(FORM_MS)
        a.setEasingCurve(QEasingCurve.InOutCubic)
        a.valueChanged.connect(lambda v, it=item: it.setPos(v))
        a.finished.connect(lambda it=item, sid=item.sid: (
            self._anims.pop(sid, None),
            self.settings["cards"].setdefault(sid, {}).update(x=it.x(), y=it.y()),
            save_settings(self.settings)))
        self._anims[item.sid] = a
        a.start(QAbstractAnimation.DeleteWhenStopped)

    # ---- névoa mística ----

    def _atualizar_nevoa(self):
        nevoa = self.settings.get("nevoa", NEVOA_PADRAO)
        self.nevoa.setOpacity(max(0, min(nevoa, 100)) / 100.0)  # fix #13
        grupos = [c for c in self.cartoes.values() if c.isVisible()]
        if not grupos:
            self.nevoa.setRect(QRectF(0, 0, 0, 0))
            return
        r = QRectF()
        for c in grupos:
            r = r.united(c.sceneBoundingRect())
        centro = r.center()
        rx = r.width() / 2 * 1.25
        ry = r.height() / 2 * 1.25
        self.nevoa.setRect(QRectF(centro.x() - rx, centro.y() - ry, 2 * rx, 2 * ry))
        g = QRadialGradient(self.nevoa.rect().center(), max(rx, ry, 120))
        g.setColorAt(0.00, QColor(54, 127, 139, 70))    # ciano-petróleo (núcleo)
        g.setColorAt(0.40, QColor(101, 67, 148, 95))    # violeta
        g.setColorAt(0.75, QColor(23, 36, 73, 120))     # azul-noite
        g.setColorAt(1.00, QColor(23, 36, 73, 0))       # esvai a zero
        self.nevoa.setBrush(QBrush(g))
        self.nevoa.update()

    # ---- ciclo de vida ----

    def atualizar(self):
        agora = time.time()
        for sid in list(self.modelo.sessoes):
            if agora - self.modelo.sessoes[sid].get("ts", agora) > 1800:
                self.modelo.sessoes.pop(sid, None)
        n_antes = len(self.cartoes)
        for sid, c in list(self.cartoes.items()):
            d = self.modelo.sessoes.get(sid)
            if d is None:
                c.sumir()
                self.cartoes.pop(sid)
                continue
            inativo = (d.get("logout")
                       or (d["fase"] == "concluído"
                           and agora - d.get("ts", agora) > FADE_CONCLUIDO_S)
                       or agora - d.get("ts", agora) > FADE_SEM_EVENTOS_S)
            if inativo and c._fade is None:
                anim = self._anims.pop(sid, None)   # fix #15
                if anim is not None:
                    anim.stop()
                c.sumir()
                self.cartoes.pop(sid)
                continue
        for sid, d in self.modelo.lista():
            if self.settings["cards"].get(sid, {}).get("hidden"):
                continue
            if sid in self.cartoes:
                self.cartoes[sid].set_dados(d)
            else:
                self._cartao(sid).set_dados(d)
        if len(self.cartoes) != n_antes or n_antes == 0:
            self._pedir_formacao()
        self.mudou.emit()

    # ---- câmera ----

    def zoom_atual(self):
        return self.transform().m11()

    def wheelEvent(self, ev):
        fator = 1.25 if ev.angleDelta().y() > 0 else 0.8
        nova = self.zoom_atual() * fator
        if ZOOM_MIN <= nova <= ZOOM_MAX:
            self.scale(fator, fator)
            self.mudou.emit()
        ev.accept()

    def visao_geral(self):
        """Reposiciona a câmera: 100% dos grupos com folga de 40 px."""
        r = self.cena.itemsBoundingRect()
        if r.isEmpty():
            return
        r = r.adjusted(-MARGEM_FIT, -MARGEM_FIT, MARGEM_FIT, MARGEM_FIT)
        self.fitInView(r, Qt.KeepAspectRatio)
        self.mudou.emit()

    def focar(self, sid):
        c = self.cartoes.get(sid)
        if not c:
            return
        z = max(1.5, self.zoom_atual())
        self.setTransform(QTransform().scale(z, z))
        self.centerOn(c)
        self.mudou.emit()

    # ---- máscara ----

    def regiao_visivel(self):
        reg = QRegion()
        borda = QRectF(self.rect())
        # todos os cartões da CENA (inclui os em fade — fix revisão #12)
        for c in self.cena.items():
            if isinstance(c, CartaoIA):
                pol = self.mapFromScene(c.sceneBoundingRect())
                ret = QRectF(pol.boundingRect()).adjusted(-2, -2, 3, 3).intersected(borda)
                if not ret.isEmpty():
                    reg = reg.united(QRegion(ret.toAlignedRect()))
        if self.settings.get("nevoa", NEVOA_PADRAO) > 0:
            pol = self.mapFromScene(self.nevoa.sceneBoundingRect())
            ret = QRectF(pol.boundingRect()).intersected(borda)
            if not ret.isEmpty():
                reg = reg.united(QRegion(ret.toAlignedRect()))
        return reg

    def centro_global_de(self, sid):
        c = self.cartoes.get(sid)
        if not c:
            return None
        centro = self.mapFromScene(c.sceneBoundingRect().center())
        return self.viewport().mapTo(self.parentWidget() or self,
                                     QPoint(int(centro.x()), int(centro.y())))


class WidgetIA(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.settings = settings
        self.setWindowTitle(APP_NAME)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.modelo = ModeloSessoes()
        self.ghosts = {}
        CartaoIA.MODO_ORBITA = bool(settings.get("orbita", True))

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        self.universo = Universo(self.modelo, settings)
        raiz.addWidget(self.universo, 1)

        # pill de controles (hover no canto sup-esq)
        self.header = QWidget(self)
        self.header.setAttribute(Qt.WA_TranslucentBackground)
        self.header.setFixedHeight(34)
        self.header.setStyleSheet(
            "QWidget { background: rgba(10, 14, 22, 208); border-radius: 10px; }")
        h = QHBoxLayout(self.header)
        h.setContentsMargins(12, 2, 12, 2)
        self.titulo = QLabel(APP_NAME)
        self.titulo.setStyleSheet("color:#9fd8ff; background:transparent; font-weight:600;")
        h.addWidget(self.titulo)
        self.botao_visao = QLabel("Visão geral")
        self.botao_visao.setStyleSheet(
            "color:#101820; background:#ffd166; border-radius:8px; "
            "padding:2px 10px; font-weight:600;")
        self.botao_visao.setCursor(Qt.PointingHandCursor)
        self.botao_visao.mousePressEvent = lambda ev: self.universo.visao_geral()
        h.addWidget(self.botao_visao)
        self.botao_reexibir = QLabel("⟳")
        self.botao_reexibir.setToolTip("Reexibir processos escondidos")
        self.botao_reexibir.setStyleSheet("color:#9fd8ff; background:rgba(255,255,255,14); "
                                          "border-radius:8px; padding:2px 8px;")
        self.botao_reexibir.setCursor(Qt.PointingHandCursor)
        self.botao_reexibir.mousePressEvent = lambda ev: self.universo.reexibir_todos()
        h.addWidget(self.botao_reexibir)
        self.botao_orbita = QLabel("Leve" if settings.get("orbita", True) else "Órbita")
        self.botao_orbita.setToolTip("Alternar entre filhos orbitando e visão leve (1 ícone + contador)")
        self.botao_orbita.setStyleSheet("color:#9fd8ff; background:rgba(255,255,255,14); "
                                        "border-radius:8px; padding:2px 10px;")
        self.botao_orbita.setCursor(Qt.PointingHandCursor)
        self.botao_orbita.mousePressEvent = lambda ev: self._toggle_orbita()
        h.addWidget(self.botao_orbita)
        lbl_n = QLabel("névoa")
        lbl_n.setStyleSheet("color:#9fd8ff; background:transparent;")
        h.addWidget(lbl_n)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(settings.get("nevoa", NEVOA_PADRAO))
        self.slider.setFixedWidth(90)
        self.slider.valueChanged.connect(self._nevoa_mudou)
        h.addWidget(self.slider)
        self.header.adjustSize()
        self.header.setFixedWidth(max(430, self.header.sizeHint().width()))
        self.header.move(8, 6)
        self.header.hide()
        self.header.setContextMenuPolicy(Qt.CustomContextMenu)
        self.header.customContextMenuRequested.connect(self._menu)

        # grip bolinha: redimensiona a área do widget (canto inf-dir)
        self.grip = _GripBolinha(self)
        self.contorno = _ContornoResize(self)
        self.contorno.hide()

        tela = QApplication.primaryScreen().availableGeometry()
        area = settings.get("area") or None
        if area:
            self.setGeometry(QRect(area.get("x", tela.x()), area.get("y", tela.y()),
                                   area.get("w", tela.width()), area.get("h", tela.height())))
        else:
            self.setGeometry(tela)
        self.set_window_topmost(settings.get("topmost", True))

        self.universo.mudou.connect(self._atualizar_titulo)
        self.universo.mudou.connect(self._aplicar_mascara)
        self._timer_ui = QTimer(self)
        self._timer_ui.timeout.connect(self._pulso)
        self._timer_ui.start(500)
        self._timer_hover = QTimer(self)
        self._timer_hover.timeout.connect(self._hover_header)
        self._timer_hover.start(150)

        self._atualizar_titulo()
        self._aplicar_mascara()

        self.sse = SseWorker()
        self.sse.start()

    # ---------- névoa / máscara / header ----------

    def _toggle_orbita(self):
        CartaoIA.MODO_ORBITA = not CartaoIA.MODO_ORBITA
        self.settings["orbita"] = CartaoIA.MODO_ORBITA
        save_settings(self.settings)
        self.botao_orbita.setText("Leve" if CartaoIA.MODO_ORBITA else "Órbita")
        self.universo._atualizar_nevoa()
        for c in self.universo.cartoes.values():
            c.update()

    def _nevoa_mudou(self, v):
        self.settings["nevoa"] = v
        save_settings(self.settings)
        self.universo._atualizar_nevoa()
        self._aplicar_mascara()

    def _aplicar_mascara(self):
        reg = self.universo.regiao_visivel()
        if self.header.isVisible():
            reg = reg.united(QRegion(self.header.geometry()))
        if not reg.isEmpty():
            reg = reg.united(QRegion(self.grip.geometry()))
        if reg.isEmpty():
            reg = QRegion(self.header.geometry())
        self.setMask(reg)

    def revelar_header_force(self):
        self.header.show()
        self.header.raise_()
        self._aplicar_mascara()

    def _hover_header(self):
        if not self.universo.cartoes:
            if not self.header.isVisible():
                self.revelar_header_force()
            return
        rect_h = QRect(self.header.mapToGlobal(QPoint(0, 0)), self.header.size())
        sobre = rect_h.contains(QCursor.pos()) or self.header.underMouse()
        if sobre:
            if not self.header.isVisible():
                self.revelar_header_force()
        elif self.header.isVisible():
            self.header.hide()
            self._aplicar_mascara()

    def _atualizar_titulo(self):
        n = len(self.universo.cartoes)
        base = APP_NAME if server_no_ar() else APP_NAME + " — server não subiu"
        extra = f"{n} processo(s)" if n else "nenhum processo vivo — abra um CLI"
        self.titulo.setText(f"{base} · {extra}")
        self.titulo.setStyleSheet(
            "color:#9fd8ff; background:transparent; font-weight:600;"
            if server_no_ar() else
            "color:#ff8f8f; background:transparent; font-weight:600;")

    # ---------- fluxo ----------

    def _pulso(self):
        self.universo.atualizar()
        for frame in self.sse.drenar():
            self._evento(frame)

    def _evento(self, frame):
        self.modelo.ingest(frame)
        ev = frame.get("event") or {}
        if frame.get("type") == "agent-event" and ev.get("type") == "tool_call_start":
            sid = ev.get("sessionId")
            d = self.modelo.sessoes.get(sid)
            if d and d.get("snippet"):
                QTimer.singleShot(0, lambda: self._ghost(sid, d.get("acao", ""),
                                                         d.get("snippet", "")))

    def _ghost(self, sid, acao, snip):
        c = self.universo.cartoes.get(sid)
        if not c or not c.isVisible():
            return
        key = (sid, acao, snip)
        if self.ghosts.get(sid) == key:
            return
        self.ghosts[sid] = key
        centro = self.universo.centro_global_de(sid)
        if centro is not None:
            PopupGhost(f"{acao}: {snip}", self.mapToGlobal(centro))

    def _menu(self, pos):
        m = QMenu(self)
        a_grade = m.addAction("Reorganizar na formação")
        a_top = m.addAction("Sempre no topo")
        a_top.setCheckable(True)
        a_top.setChecked(self.settings.get("topmost", True))
        a_area = m.addAction("Restaurar área (tela cheia)")
        a_parar = m.addAction("Parar server do quadro")
        m.addSeparator()
        a_fechar = m.addAction("Fechar widget")
        esc = m.exec(self.header.mapToGlobal(pos))
        if esc is a_grade:
            self.universo._aplicar_formacao()
        elif esc is a_top:
            self.set_window_topmost(a_top.isChecked())
            self.settings["topmost"] = a_top.isChecked()
            save_settings(self.settings)
        elif esc is a_area:
            self.setGeometry(QApplication.primaryScreen().availableGeometry())
            self._salvar_area()
        elif esc is a_parar:
            parar_server()
        elif esc is a_fechar:
            self.close()

    def _salvar_area(self):
        self.settings["area"] = {"x": self.x(), "y": self.y(),
                                 "w": self.width(), "h": self.height()}
        save_settings(self.settings)

    def resizeEvent(self, ev):
        self.grip.mover(self.width(), self.height())
        self.contorno.setGeometry(self.rect())   # acompanha o novo tamanho
        self.universo._atualizar_nevoa()
        self._aplicar_mascara()
        super().resizeEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and self.header.geometry().contains(ev.position().toPoint()):
            self.revelar_header_force()
        super().mousePressEvent(ev)

    def set_window_topmost(self, on):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    def closeEvent(self, ev):
        self._salvar_area()
        parar_server()
        super().closeEvent(ev)


class _GripBolinha(QWidget):
    """Bolinha no vértice inferior direito: arrasta = redimensiona a área.
    Estados: repouso 35%, hover 90% (halo), arrastando 100% (halo ciano).
    Durante o arrasto a janela mostra contorno tracejado."""

    def __init__(self, pai):
        super().__init__(pai)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.SizeFDiagCursor)
        self._estado = "repouso"
        self._arrasto = None
        self.mover(pai.width(), pai.height())

    def mover(self, w, h):
        self.move(w - 34, h - 34)

    def enterEvent(self, ev):
        self._estado = "hover"
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._estado = "repouso"
        self.update()
        super().leaveEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            janela = self.window()
            self._arrasto = (ev.globalPosition().toPoint(),
                             janela.width(), janela.height())
            self._estado = "arrastando"
            janela.contorno.setGeometry(janela.rect())
            janela.contorno.show()
            janela.contorno.raise_()
            self.raise_()
        ev.accept()

    def mouseMoveEvent(self, ev):
        if self._arrasto:
            ini, w0, h0 = self._arrasto
            janela = self.window()
            janela.resize(max(520, w0 + ev.globalPosition().x() - ini.x()),
                          max(320, h0 + ev.globalPosition().y() - ini.y()))
        ev.accept()

    def mouseReleaseEvent(self, ev):
        if self._arrasto:
            self._arrasto = None
            self._estado = "hover"
            janela = self.window()
            janela.contorno.hide()
            janela._salvar_area()
        ev.accept()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = self.rect().center()
        if self._estado != "repouso":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(80, 200, 220, 60))
            p.drawEllipse(c, 14, 14)
        op = {"repouso": 210, "hover": 240, "arrastando": 255}[self._estado]
        p.setBrush(QColor(14, 17, 26, op))
        p.setPen(QPen(QColor(120, 220, 235, op), 2))
        p.drawEllipse(c, 9, 9)
        p.setPen(QColor(230, 250, 255, op))
        f = QFont("Segoe UI", 8, QFont.DemiBold)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, "⤡")


class _ContornoResize(QWidget):
    """Contorno tracejado mostrado só durante o redimensionamento."""

    def __init__(self, pai):
        super().__init__(pai)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        pen = QPen(QColor(160, 230, 245, 220), 1.4)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawRect(self.rect().adjusted(1, 1, -2, -2))
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QColor(180, 235, 245, 200))
        p.drawText(self.rect().adjusted(4, 4, -8, -8),
                   Qt.AlignRight | Qt.AlignBottom,
                   f"{self.window().width()}×{self.window().height()}")


def main():
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--screenshot", metavar="PATH")
    ap.add_argument("--screenshot-delay-ms", type=int, default=9000)
    ap.add_argument("--skip-singleton-guard", action="store_true")
    args = ap.parse_args()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    if not args.skip_singleton_guard:
        probe = QLocalSocket()
        probe.connectToServer(SINGLETON_KEY)
        if probe.waitForConnected(150):
            sys.exit(0)  # já tem um widget aberto
        probe.close()
        QLocalServer.removeServer(SINGLETON_KEY)
        guard = QLocalServer()
        guard.listen(SINGLETON_KEY)

    subir_server()
    ded = MB_BOARD
    if ded.exists():
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command",
                        ". '" + str(ded) + "' -SomenteDedup"],
                       creationflags=CREATE_NO_WINDOW,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    w = WidgetIA(load_settings())
    w.show()

    if args.screenshot:
        def capturar():
            w.grab().save(args.screenshot, "PNG")
            app.quit()
        QTimer.singleShot(args.screenshot_delay_ms, capturar)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
