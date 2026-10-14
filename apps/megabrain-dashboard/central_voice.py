"""Windows dictation handoff; never records or recognizes audio in Chromium.

The OS controls microphone permission, language, network and start/stop. A
successful request proves only that the shortcut was delivered, not recognition.
"""
from __future__ import annotations
import ctypes
import json
import sys
import time
from pathlib import Path
from PySide6.QtCore import QFile, QIODevice, QObject, Slot, Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript


def open_windows_dictation(hwnd: int) -> None:
    """Send only Win+H, and only while our native window is foreground."""
    if sys.platform != 'win32':
        raise RuntimeError('O ditado do Windows está disponível apenas no Windows.')
    from ctypes import wintypes as w
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    user32.GetForegroundWindow.restype = w.HWND
    if user32.GetForegroundWindow() != hwnd:
        raise RuntimeError('Volte ao MegaBrain e clique no áudio da nota novamente.')
    pointer = w.WPARAM
    class Mouse(ctypes.Structure):
        _fields_ = [('dx', w.LONG), ('dy', w.LONG), ('data', w.DWORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', pointer)]
    class Keyboard(ctypes.Structure):
        _fields_ = [('key', w.WORD), ('scan', w.WORD), ('flags', w.DWORD), ('time', w.DWORD), ('extra', pointer)]
    class Payload(ctypes.Union):
        _fields_ = [('mouse', Mouse), ('keyboard', Keyboard)]
    class Input(ctypes.Structure):
        _anonymous_ = ('payload',)
        _fields_ = [('kind', w.DWORD), ('payload', Payload)]
    # Do not issue synthetic releases for keys the user is holding.
    for key in (0x5B, 0x5C, 0x48, 0x10, 0x11, 0x12):
        if user32.GetAsyncKeyState(key) & 0x8000:
            raise RuntimeError('Solte as teclas do teclado e clique no áudio novamente.')
    keys = (Input * 4)(*(Input(kind=1, keyboard=Keyboard(key=key, flags=flags))
                            for key, flags in ((0x5B, 0), (0x48, 0), (0x48, 2), (0x5B, 2))))
    user32.SendInput.argtypes = [w.UINT, ctypes.POINTER(Input), ctypes.c_int]
    user32.SendInput.restype = w.UINT
    sent = user32.SendInput(4, keys, ctypes.sizeof(Input))
    if sent != 4:
        # Ensure our injected chord cannot leave modifiers stuck on failure.
        release = (Input * 2)(Input(kind=1, keyboard=Keyboard(key=0x48, flags=2)),
                              Input(kind=1, keyboard=Keyboard(key=0x5B, flags=2)))
        user32.SendInput(2, release, ctypes.sizeof(Input))
        raise RuntimeError('Não foi possível abrir o ditado. No campo da nota, use Win + H.')


class TrustedDictationButton(QPushButton):
    """Only an actual native button gesture may invoke the OS callback.

    No clicked signal is bound to dispatch: .click()/animateClick()/JS requests
    cannot accept the handoff automatically.
    """
    def __init__(self, callback, parent):
        super().__init__('Abrir ditado do Windows', parent)
        self.callback = callback
    def mouseReleaseEvent(self, event):
        allow = event.spontaneous() and event.button() == Qt.MouseButton.LeftButton and self.isDown() and self.rect().contains(event.position().toPoint())
        super().mouseReleaseEvent(event)
        if allow: QTimer.singleShot(0, self.callback)
    def keyPressEvent(self, event):
        if event.spontaneous() and not event.isAutoRepeat() and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept(); QTimer.singleShot(0, self.callback); return
        super().keyPressEvent(event)
    def keyReleaseEvent(self, event):
        allow = event.spontaneous() and not event.isAutoRepeat() and event.key() == Qt.Key.Key_Space and self.isDown()
        super().keyReleaseEvent(event)
        if allow: QTimer.singleShot(0, self.callback)


class NativeVoice(QObject):
    dictationClosed = Signal(str)
    def __init__(self, window, browser, dispatch=open_windows_dictation, clock=time.monotonic):
        super().__init__(browser)
        self.window, self.browser, self.dispatch, self.clock = window, browser, dispatch, clock
        self.last = float('-inf')
        self.pending = False
        self.request_id = ''; self.field_valid = False; self.field_seen = float('-inf')
        self.confirmation = QWidget(window); row = QHBoxLayout(self.confirmation)
        self.message = QLabel('O ditado do Windows usa o serviço online da Microsoft. A barra do Windows controla ouvir e parar; Salvar envia só o texto.')
        self.message.setWordWrap(True)
        self.confirm_button = TrustedDictationButton(self._confirm, self.confirmation)
        cancel = QPushButton('Cancelar', self.confirmation)
        cancel.clicked.connect(self._cancel)
        row.addWidget(self.message,1); row.addWidget(self.confirm_button); row.addWidget(cancel)
        self.confirmation.hide()
        self.expiry = QTimer(self); self.expiry.timeout.connect(self._expire); self.expiry.start(500)

    def _expire(self):
        if self.pending and self.clock() - self.field_seen > 1.5: self._cancel()

    def _cancel(self):
        request_id = self.request_id
        self.pending = False; self.field_valid = False; self.request_id = ''
        self.confirmation.hide(); self.browser.setFocus()
        if request_id: self.dictationClosed.emit(request_id)

    @Slot(str, bool)
    def updateField(self, request_id, valid):
        # This grants no OS capability; it only expires the pending native UI.
        if not self.pending or request_id != self.request_id: return
        if not valid: self._cancel(); return
        self.field_valid = True; self.field_seen = self.clock()

    @Slot(str)
    def cancelDictation(self, request_id):
        if request_id == self.request_id: self._cancel()

    def _confirm(self):
        # This is not a Qt slot and is absent from WebChannel's exported object.
        if not self.pending: return
        if not self.field_valid or self.clock() - self.field_seen > 1.5:
            self._cancel(); return
        if not self.window.isActiveWindow():
            self.message.setText('Volte ao MegaBrain e peça o áudio da nota novamente.'); return
        self.pending = False
        self.browser.setFocus(Qt.FocusReason.OtherFocusReason)
        try:
            self.dispatch(int(self.window.winId()))
        except Exception as exc:
            self.pending = True
            self.message.setText(str(exc) + ' Tente novamente por este botão, ou cancele.'); return
        self.confirmation.hide()
        request_id = self.request_id; self.request_id = ''; self.field_valid = False
        if request_id: self.dictationClosed.emit(request_id)

    @Slot(str, result=str)
    def openDictation(self, request_id='legacy-test'):
        url = self.browser.url()
        if (url.scheme(), url.host(), url.port()) != ('http', '127.0.0.1', 8766):
            return json.dumps({'ok': False, 'error': 'O ditado é exclusivo da central local.'})
        if not self.window.isActiveWindow():
            return json.dumps({'ok': False, 'error': 'Volte ao MegaBrain e clique no áudio novamente.'})
        now = self.clock()
        if now - self.last < 0.8:
            return json.dumps({'ok': False, 'error': 'Aguarde um instante antes de abrir o ditado de novo.'})
        self.last = now
        if self.pending: self._cancel()
        self.pending = True
        self.request_id = str(request_id)[:100]; self.field_valid = False; self.field_seen = now
        self.message.setText('O ditado do Windows usa o serviço online da Microsoft. A barra do Windows controla ouvir e parar; Salvar envia só o texto. Confirme abaixo para abrir.')
        self.confirmation.show()
        return json.dumps({'ok': True, 'request_id':self.request_id, 'state': 'awaiting-native-confirmation', 'engine': 'Windows voice typing'})


BRIDGE_SCRIPT = r"""
(function () {
  if (location.protocol !== 'http:' || location.hostname !== '127.0.0.1' || location.port !== '8766') return;
  window.__MEGABRAIN_NATIVE_VOICE__ = true;
  var requests = {}, count = 0, current = null;
  window.megabrainCancelDictation = function () {
    if (!current) return;
    var id = current.id; clearInterval(current.timer); current = null;
    top.postMessage({mbNativeVoice: 'cancel', id: id}, location.origin);
  };
  function fieldAlive(field) {
    return field && field.isConnected && document.activeElement === field && field.tagName === 'TEXTAREA' && field.closest('.cf-editor') &&
      field.getBoundingClientRect().width > 0 && field.getBoundingClientRect().height > 0 &&
      getComputedStyle(field).visibility !== 'hidden' && document.visibilityState !== 'hidden';
  }
  window.megabrainNativeDictation = function () {
    if (!navigator.userActivation || !navigator.userActivation.isActive)
      return Promise.reject(new Error('Clique no botão de áudio para abrir o ditado.'));
    var field = document.activeElement;
    if (!fieldAlive(field)) return Promise.reject(new Error('Abra a nota e mantenha o campo de comentário visível.'));
    window.megabrainCancelDictation();
    return new Promise(function (resolve, reject) {
      var id = Date.now() + '-' + (++count) + '-' + Math.random().toString(36).slice(2);
      var timer = setTimeout(function () { delete requests[id]; if (current && current.id === id) window.megabrainCancelDictation(); reject(new Error('Ponte de áudio indisponível. No campo da nota, use Win + H.')); }, 3000);
      requests[id] = function (value) { clearTimeout(timer); delete requests[id]; if (!value.ok && current && current.id === id) window.megabrainCancelDictation(); value.ok ? resolve(value) : reject(new Error(value.error)); };
      current = {id: id, field: field};
      top.postMessage({mbNativeVoice: 'open', id: id}, location.origin);
      function heartbeat() {
        if (!current || current.id !== id) return;
        if (!fieldAlive(field)) { window.megabrainCancelDictation(); return; }
        top.postMessage({mbNativeVoice: 'field', id: id, valid: true}, location.origin);
      }
      current.timer = setInterval(heartbeat, 400); heartbeat();
    });
  };
  addEventListener('message', function (event) {
    if (!event.data) return;
    if (event.data.mbNativeVoice === 'result' && event.source === top && requests[event.data.id]) requests[event.data.id](event.data.value);
    if (event.data.mbNativeVoice === 'closed' && event.source === top && current && current.id === event.data.id) {
      clearInterval(current.timer); current = null;
    }
  });
  addEventListener('pagehide', window.megabrainCancelDictation);
  addEventListener('focusin', function (event) {
    if (current && event.target !== current.field) window.megabrainCancelDictation();
  }, true);
  addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') window.megabrainCancelDictation(); });
  if (window !== top || typeof qt === 'undefined' || !qt.webChannelTransport) return;
  new QWebChannel(qt.webChannelTransport, function (channel) {
    var owners = {};
    channel.objects.nativeVoice.dictationClosed.connect(function (id) {
      var source = owners[id]; delete owners[id];
      if (source) try { source.postMessage({mbNativeVoice:'closed', id:id}, '*'); } catch (_) {}
    });
    function visibleFrame(source) {
      if (source === top) return true;
      function scan(doc, depth) {
        var nodes = doc.querySelectorAll('iframe');
        for (var i=0; i<nodes.length; i++) {
          var node = nodes[i], rect = node.getBoundingClientRect(), shown = rect.width > 0 && rect.height > 0 && getComputedStyle(node).visibility !== 'hidden';
          if (!shown) continue;
          if (node.contentWindow === source) return true;
          if (depth < 2) try { if (scan(node.contentDocument, depth + 1)) return true; } catch (_) {}
        }
        return false;
      }
      return scan(document, 0);
    }
    new MutationObserver(function () {
      Object.keys(owners).forEach(function (id) {
        if (!visibleFrame(owners[id])) channel.objects.nativeVoice.updateField(id, false);
      });
    }).observe(document, {subtree:true, childList:true, attributes:true, attributeFilter:['hidden','style','class']});
    addEventListener('message', function (event) {
      if (!event.data) return;
      var kind = event.data.mbNativeVoice, id = event.data.id;
      if (kind === 'cancel' && owners[id] === event.source) { delete owners[id]; channel.objects.nativeVoice.cancelDictation(id); return; }
      if (kind === 'field' && owners[id] === event.source) {
        channel.objects.nativeVoice.updateField(id, event.data.valid === true && visibleFrame(event.source)); return;
      }
      if (kind !== 'open') return;
      // Opaque sandbox reports have origin "null". Accept only our own frame
      // tree, never an external popup. Requests only show a native confirmation;
      // no report script can accept it or deliver OS keys.
      var descendant = event.source === top;
      for (var i=0; i<frames.length && !descendant; i++) {
        if (event.source === frames[i]) descendant = true;
        for (var j=0; j<frames[i].length && !descendant; j++) if (event.source === frames[i][j]) descendant = true;
      }
      if (!descendant || (event.origin !== location.origin && event.origin !== 'null')) return;
      var source = event.source;
      if (typeof id !== 'string' || id.length > 100) return;
      owners[id] = source;
      channel.objects.nativeVoice.openDictation(id, function (value) {
        try { var parsed = JSON.parse(value); if (!parsed.ok) delete owners[id]; source.postMessage({mbNativeVoice: 'result', id: id, value: parsed}, event.origin === 'null' ? '*' : location.origin); } catch (_) {}
      });
    });
  });
})();
"""


def install_voice_bridge(page, window, browser, dispatch=open_windows_dictation):
    channel = QWebChannel(page)
    voice = NativeVoice(window, browser, dispatch=dispatch)
    channel.registerObject('nativeVoice', voice)
    page.setWebChannel(channel)
    browser.loadStarted.connect(voice._cancel)
    page.renderProcessTerminated.connect(lambda *_:voice._cancel())
    # Loading from the bundled Qt resource needs no network or report CSP change.
    resource = QFile(':/qtwebchannel/qwebchannel.js')
    if not resource.open(QIODevice.OpenModeFlag.ReadOnly):
        raise RuntimeError('Recurso Qt de comunicação nativa indisponível.')
    client = bytes(resource.readAll()).decode('utf-8'); resource.close()
    script = QWebEngineScript()
    script.setName('megabrain-native-voice')
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(True)
    script.setSourceCode(client + '\n' + BRIDGE_SCRIPT)
    page.scripts().insert(script)
    return channel, voice


def record_renderer_failure(path: Path, status, exit_code: int):
    """Diagnostic metadata only: never notes, audio, URLs, hashes or tokens."""
    event = {'at': time.time(), 'event': 'renderer-terminated',
             'status': getattr(status, 'name', str(status)), 'exit_code': exit_code}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(event) + '\n')
    return event


def install_renderer_recovery(page, browser, window, log_path, voice=None):
    """Native recovery stays alive independently of the renderer process."""
    from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
    shell = QWidget(); layout = QVBoxLayout(shell); layout.setContentsMargins(0, 0, 0, 0)
    banner = QWidget(); row = QHBoxLayout(banner)
    message = QLabel('A tela do MegaBrain parou. Os rascunhos já guardados continuam neste aparelho.')
    message.setWordWrap(True); retry = QPushButton('Reabrir a tela')
    row.addWidget(message, 1); row.addWidget(retry)
    banner.hide(); layout.addWidget(banner)
    if voice is not None: layout.addWidget(voice.confirmation)
    layout.addWidget(browser, 1)
    def failed(status, code):
        try: record_renderer_failure(Path(log_path), status, code)
        except OSError: pass
        message.setText('A tela do MegaBrain parou. Reabra a tela para recuperar as notas e os rascunhos já guardados neste aparelho.')
        banner.show(); retry.setEnabled(True); window.showNormal(); window.raise_()
    def reload():
        retry.setEnabled(False); message.setText('Reabrindo a tela…'); browser.reload()
    def loaded(ok):
        if ok: banner.hide()
        elif not banner.isHidden():
            message.setText('Não foi possível reabrir a tela. Tente novamente; os rascunhos já guardados continuam neste aparelho.')
            retry.setEnabled(True)
    page.renderProcessTerminated.connect(failed)
    browser.loadFinished.connect(loaded); retry.clicked.connect(reload)
    return shell, banner, retry, message
