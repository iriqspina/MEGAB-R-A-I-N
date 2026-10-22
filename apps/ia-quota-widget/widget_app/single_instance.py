from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtCore import QTimer
import hashlib,json,time,uuid,os
from . import paths

COMMANDS={'show','settings','settings:0','settings:1','settings:2','settings:3','settings:4'}

class SingleInstanceGuard:
    def __init__(self,key: str=paths.SINGLETON_KEY):
        self._key=key
        self._server=None
        self._callback=None
        self._settings_callback=None
        self._timer=None
        self._queue=paths.DATA_DIR/'window-requests'/hashlib.sha256(key.encode()).hexdigest()[:12]

    def already_running(self):
        probe=QLocalSocket();probe.connectToServer(self._key)
        connected=probe.waitForConnected(150);probe.close()
        return connected

    def claim(self):
        if self.already_running():return False
        QLocalServer.removeServer(self._key)
        self._server=QLocalServer()
        self._server.newConnection.connect(self._discard_probe)
        return self._server.listen(self._key)

    def _discard_probe(self):
        client=self._server.nextPendingConnection()
        if client is not None:client.close();client.deleteLater()

    def set_callback(self,callback):
        self._callback=callback
        self._timer=QTimer(self._server);self._timer.setInterval(200)
        self._timer.timeout.connect(self._drain_requests);self._timer.start()

    def request(self,command):
        if not isinstance(command,str) or command not in COMMANDS:raise ValueError('Comando de janela inválido')
        self._queue.mkdir(parents=True,exist_ok=True)
        path=self._queue/(uuid.uuid4().hex+'.json');temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'command':command,'at':time.time()}),encoding='utf-8')
        os.replace(temp,path)
        return True  # queued; the existing GUI consumes it on its event loop

    def set_settings_callback(self,callback):
        self._settings_callback=callback

    def _drain_requests(self):
        if self._settings_callback:
            from .settings_exchange import process_requests
            process_requests(self._settings_callback)
        if not self._callback or not self._queue.is_dir():return
        for path in sorted(self._queue.glob('*.json'))[:20]:
            try:
                if path.stat().st_size>512:continue
                data=json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data,dict):continue
                command=data.get('command');stamp=data.get('at')
                if isinstance(command,str) and command in COMMANDS and isinstance(stamp,(int,float)) and 0<=time.time()-stamp<10:self._callback(command)
            except (OSError,ValueError,TypeError):pass
            finally:
                try:path.unlink()
                except OSError:pass
