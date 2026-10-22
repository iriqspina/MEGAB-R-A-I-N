"""The native MegaBrain window. Owns only the services it starts."""
from __future__ import annotations
import ctypes, json, os, subprocess, sys, threading, time, urllib.request
from pathlib import Path
APP=Path(__file__).resolve().parent
sys.path[:0]=[str(APP),str(APP/'runtime-packages')]

def healthy(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1) as r:
            return json.load(r).get('app')=='megabrain-central'
    except Exception:return False

def main():
    # pythonw has no console streams. Uvicorn and inherited utilities require
    # real file-like objects even when access logging is disabled.
    if sys.stdout is None or sys.stderr is None:
        (APP/'data').mkdir(exist_ok=True)
        output=(APP/'data/central-desktop.log').open('a',encoding='utf-8',buffering=1)
        if sys.stdout is None: sys.stdout=output
        if sys.stderr is None: sys.stderr=output
    if sys.platform=='win32': ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('<USUARIO>.MegaBrain.Central')
    from PySide6.QtCore import Qt,QTimer,QUrl
    from PySide6.QtGui import QIcon,QDesktopServices
    from PySide6.QtWidgets import QApplication,QMainWindow,QMessageBox,QFileDialog
    from PySide6.QtWebEngineCore import QWebEnginePage,QWebEngineProfile,QWebEngineSettings,QWebEngineScript
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from central_server import build_app,secret_file
    import uvicorn
    services=[]; children=[]
    if not healthy(8766):
        for port,remote in ((8766,False),(8767,True)):
            service=uvicorn.Server(uvicorn.Config(build_app(remote=remote),host='127.0.0.1',port=port,access_log=False,log_level='warning',proxy_headers=False))
            threading.Thread(target=service.run,daemon=True).start();services.append(service)
        deadline=time.time()+20
        while time.time()<deadline and not healthy(8766):time.sleep(.1)
    app=QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName('MegaBrain');app.setOrganizationName('<USUARIO>')
    if not healthy(8766):
        QMessageBox.critical(None,'MegaBrain','Não foi possível iniciar a central. Consulte o log em apps/megabrain-dashboard/data/central-desktop.log.');return 1
    # Only launch the dedicated, configured tunnel. Never installs a global service.
    if (APP/'data/.private/tunnel.token').is_file() and (APP/'remote/runtime/cloudflared.exe').is_file():
        log=(APP/'data/central-tunnel.log').open('a',encoding='utf-8')
        children.append(subprocess.Popen([sys.executable,str(APP/'remote/run_tunnel.py'),'--run'],cwd=APP,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)))
    class Page(QWebEnginePage):
        def acceptNavigationRequest(self,url,kind,is_main):
            if not is_main:return True
            if url.scheme()=='http' and url.host()=='127.0.0.1' and url.port()==8766:return True
            if url.scheme() in {'https','mailto'}:
                QDesktopServices.openUrl(url)
            return url.scheme()=='about'
        def createWindow(self,kind):
            other=QWebEnginePage(self.profile(),self)
            other.urlChanged.connect(lambda url:(QDesktopServices.openUrl(url),other.deleteLater()) if url.scheme()=='https' else None)
            return other
    window=QMainWindow();window.setWindowTitle('MegaBrain · sua área de trabalho')
    icon=QIcon(str(APP/'assets/megabrain-cerebro-rosa.ico'));window.setWindowIcon(icon);app.setWindowIcon(icon)
    window.resize(1440,950);window.setMinimumSize(720,560)
    browser=QWebEngineView();profile=QWebEngineProfile('megabrain-central',browser)
    profile.setPersistentStoragePath(str(APP/'data/webengine'))
    profile.setCachePath(str(APP/'data/webengine/cache'))
    page=Page(profile,browser);browser.setPage(page)
    from central_store import Store
    from central_comment_visibility import cursor_archive_script
    archive_script=QWebEngineScript()
    archive_script.setName('megabrain-resolved-cursor-notes')
    archive_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    archive_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    archive_script.setRunsOnSubFrames(False)
    archive_script.setSourceCode(cursor_archive_script(Store()))
    page.scripts().insert(archive_script)
    from central_voice import install_voice_bridge,install_renderer_recovery
    voice_channel,native_voice=install_voice_bridge(page,window,browser)
    def download(request):
        url=request.url()
        if url.scheme()!='http' or url.host()!='127.0.0.1' or url.port()!=8766:
            request.cancel();return
        suggested=Path(request.downloadFileName()).name
        target,_=QFileDialog.getSaveFileName(window,'Salvar resultado do MegaBrain',str(APP.parents[1]/'00_PARA-VOCE'/suggested))
        if not target:request.cancel();return
        dest=Path(target);request.setDownloadDirectory(str(dest.parent));request.setDownloadFileName(dest.name);request.accept()
    profile.downloadRequested.connect(download)
    browser.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,False)
    browser.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled,True)
    shell,recovery,reload_button,recovery_message=install_renderer_recovery(page,browser,window,APP/'data/central-renderer-events.jsonl',native_voice)
    window.setCentralWidget(shell)
    def loaded(ok):
        (APP/'data/central-runtime.json').write_text(json.dumps({'loaded':ok,'at':time.time(),'native':'QMainWindow/QWebEngineView','pid':os.getpid(),'viewport':[browser.width(),browser.height()]},indent=2),encoding='utf-8')
    browser.loadFinished.connect(loaded)
    browser.load(QUrl('http://127.0.0.1:8766/#pair='+secret_file('native.key')))
    window.show()
    # Show the existing quota widget through its singleton route; never open settings.
    from central_quotas import ensure_widget
    QTimer.singleShot(1000,ensure_widget)
    # Existing native window receives local presentation requests. No file/URL
    # is passed to the Windows default browser or file association.
    queue=APP/'data/open-requests';queue.mkdir(exist_ok=True)
    from central_presentation import PresentationQueue,dispatch_script,bring_forward
    presentation_queue=PresentationQueue(queue)
    pending=[False]
    def present_requests():
        if pending[0]:return
        if presentation_queue.timeout():return
        if presentation_queue.current:
            pending[0]=True
            def acknowledged(receipt):
                pending[0]=False
                try:receipt=json.loads(receipt or 'null')
                except (TypeError,ValueError):return
                # 261017 WP3: a quiet receipt (session notice) never raises the window;
                # a delivery restores only a minimized window and keeps maximized/full screen.
                if presentation_queue.finish(receipt):
                    bring_forward(window,receipt,Qt.WindowState.WindowMinimized)
            browser.page().runJavaScript('JSON.stringify(window.megabrainPresentationResult || null)',acknowledged)
            return
        payload=presentation_queue.next()
        if not payload:return
        pending[0]=True
        def dispatched(result):
            pending[0]=False
            # 'busy': the person is using a report; the request waits in the queue (same expiry).
            if result=='busy':presentation_queue.defer()
            elif result is not True:presentation_queue.retry()
        browser.page().runJavaScript(dispatch_script(payload),dispatched)
    presentation_timer=QTimer(window);presentation_timer.timeout.connect(present_requests);presentation_timer.start(800)
    def close_services():
        for service in services:service.should_exit=True
        # Closing our launcher terminates only its dedicated tunnel child.
        for child in children:
            if child.poll() is None:child.terminate()
    app.aboutToQuit.connect(close_services)
    return app.exec()

if __name__=='__main__':
    (APP/'data').mkdir(exist_ok=True)
    try: raise SystemExit(main())
    except Exception:
        import traceback
        with (APP/'data/central-desktop.log').open('a',encoding='utf-8') as f:traceback.print_exc(file=f)
        raise
