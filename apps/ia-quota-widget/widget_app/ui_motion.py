"""Animações cartunescas (260914, pedido do <USUARIO>: "looney tunes").

Tudo aqui é efêmero e nunca muda dado: se a animação não rodar (teste
headless, máquina lenta), o widget fica no estado final de qualquer forma
porque os valores lógicos são aplicados antes de animar.
"""

from PySide6.QtCore import QEasingCurve, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

NO_MAX = 16777215


def animate(parent, start, end, duration, apply, done=None, easing=QEasingCurve.OutBack):
    anim = QVariantAnimation(parent)
    anim.setStartValue(start)
    anim.setEndValue(end)
    anim.setDuration(duration)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(apply)
    if done is not None:
        anim.finished.connect(lambda: (anim.deleteLater(), done()))
    else:
        anim.finished.connect(anim.deleteLater)
    anim.start()
    return anim


def pop_in(widget, duration=340):
    """Card entra saltitando: altura 0 -> conteúdo com overshoot elástico."""
    target = max(1, widget.sizeHint().height())
    widget.setMaximumHeight(1)
    animate(
        widget, 1, target, duration,
        lambda v: widget.setMaximumHeight(max(1, int(v))),
        done=lambda: widget.setMaximumHeight(NO_MAX),
        easing=QEasingCurve.OutBack,
    )


def pop_out(widget, done, duration=220):
    """Card some encolhendo com anticinação (InBack) antes de sumir mesmo."""
    start = max(1, widget.height() or widget.sizeHint().height())

    def finish():
        widget.setMaximumHeight(NO_MAX)
        done()

    return animate(
        widget, start, 1, duration,
        lambda v: widget.setMaximumHeight(max(1, int(v))),
        done=finish,
        easing=QEasingCurve.InBack,
    )


def dim(widget, level=0.35):
    """Card sendo arrastado fica fantasmagórico até soltar."""
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(level)
    widget.setGraphicsEffect(effect)


def undim(widget):
    widget.setGraphicsEffect(None)
