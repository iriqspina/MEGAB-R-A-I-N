import argparse
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from widget_app import theme
from widget_app.main_window import MainWindow
from widget_app.single_instance import SingleInstanceGuard


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Widget de cotas IA")
    parser.add_argument("--demo", action="store_true", help="usa dados ficticios rotulados, sem consultar nada")
    parser.add_argument("--screenshot", metavar="PATH", help="grava um PNG da janela e sai")
    parser.add_argument(
        "--screenshot-delay-ms", type=int, default=400, help="espera antes de capturar (layout/poll assentarem)"
    )
    parser.add_argument("--expanded", action="store_true", help="abre ja expandido (para captura)")
    parser.add_argument("--move-to", metavar="X,Y", help="posiciona a janela nessas coordenadas antes de mostrar")
    parser.add_argument(
        "--theme", choices=theme.SURFACE_PRESET_ORDER, help="preset de superficie (default: o salvo em settings.json)"
    )
    parser.add_argument("--skip-singleton-guard", action="store_true", help="uso interno de scripts de captura")
    parser.add_argument("--settings-screenshot", metavar="PATH", help="abre Configurações, grava PNG dela e sai")
    parser.add_argument("--settings-tab", type=int, default=0, help="aba das Configurações para a captura")
    return parser.parse_args(argv)


def _take_screenshot_and_quit(window: "MainWindow", path: str, settings_path: str | None = None):
    if path:
        window.grab().save(path, "PNG")
    if settings_path and window._settings_dialog is not None:
        window._settings_dialog.grab().save(settings_path, "PNG")
    QApplication.instance().quit()


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(True)

    if not args.skip_singleton_guard:
        guard = SingleInstanceGuard()
        if not guard.claim():
            print("ia-quota-widget ja esta em execucao.")
            return 0

    window = MainWindow(
        demo=args.demo,
        session_only=bool(args.theme or args.expanded or args.screenshot or args.settings_screenshot),
    )
    if args.theme:
        window._set_surface_preset(args.theme)
    if args.expanded:
        window.settings.expanded = True
        window._details_btn.setText("▴")
        window._details_btn.setAccessibleName("Recolher detalhes (Ctrl+D)")
        for segment in window._segments.values():
            segment.set_expanded(True)
    window.show_positioned()
    if args.move_to:
        x_str, y_str = args.move_to.split(",")
        window.move(int(x_str), int(y_str))
    window.poll_now()

    if args.settings_screenshot:
        dialog = window.open_settings()
        dialog.tabs.setCurrentIndex(args.settings_tab)
    if args.screenshot or args.settings_screenshot:
        QTimer.singleShot(
            args.screenshot_delay_ms,
            lambda: _take_screenshot_and_quit(window, args.screenshot, args.settings_screenshot),
        )

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
