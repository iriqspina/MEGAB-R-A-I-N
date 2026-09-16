import argparse
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from pendencias_core import paths
from pendencias_core.single_instance import SingleInstanceGuard
from pendencias_core.ui_card import MainWindow


def parse_args(argv):
    p = argparse.ArgumentParser(description="Widget Pendências — radar dos projetos MEGABRAIN")
    p.add_argument("--demo", action="store_true", help="dados fictícios rotulados, sem ler a central")
    p.add_argument("--screenshot", metavar="PATH", help="grava um PNG da janela e sai")
    p.add_argument("--screenshot-delay-ms", type=int, default=400)
    p.add_argument("--expanded", action="store_true", help="abre já expandido (para captura)")
    p.add_argument("--move-to", metavar="X,Y")
    p.add_argument("--skip-singleton-guard", action="store_true", help="uso interno de scripts de captura")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(True)

    if not args.skip_singleton_guard:
        guard = SingleInstanceGuard(paths.SINGLETON_KEY)
        if not guard.claim():
            print("pendencias-widget ja esta em execucao.")
            return 0

    window = MainWindow(
        demo=args.demo,
        session_only=bool(args.screenshot or args.expanded or args.demo),
    )
    if args.expanded:
        window.settings["expanded"] = True
        window._set_expandido(True)
    window.show_positioned()
    if args.move_to:
        x, y = (int(v) for v in args.move_to.split(","))
        window.move(x, y)
    window._recarregar()

    if args.screenshot:
        QTimer.singleShot(
            args.screenshot_delay_ms,
            lambda: (window.grab().save(args.screenshot, "PNG"), QApplication.quit()),
        )
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
