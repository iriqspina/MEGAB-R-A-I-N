from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstanceGuard:
    """Mesmo padrão do Cotas IA (QLocalServer), chave própria."""

    def __init__(self, key: str):
        self._key = key
        self._server: QLocalServer | None = None

    def already_running(self) -> bool:
        probe = QLocalSocket()
        probe.connectToServer(self._key)
        connected = probe.waitForConnected(150)
        probe.close()
        return connected

    def claim(self) -> bool:
        if self.already_running():
            return False
        QLocalServer.removeServer(self._key)
        self._server = QLocalServer()
        self._server.listen(self._key)
        return True
