from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from widget_app.main_window import MainWindow
from widget_app.single_instance import SingleInstanceGuard
import uuid
import threading

def test_strip_opens_dialog_in_one_click_and_repeat_preserves_undo(qt_app):
    win=MainWindow(demo=True,session_only=True)
    try:
        win.show_positioned();qt_app.processEvents()
        win.strip.menu.click();qt_app.processEvents()
        dialog=win._settings_dialog
        assert dialog and dialog.isVisible()
        baseline=dialog._opened_with.copy()
        win.update_settings({'size_value':baseline['size_value']+2})
        win.open_settings()
        assert dialog._opened_with==baseline
        dialog.undo_changes()
        assert win.settings.size_value==baseline['size_value']
    finally:
        win._size_save_timer.stop();win._resize_watch_timer.stop();win.close();win.deleteLater()

def test_singleton_routes_fixed_requests_to_same_instance(qt_app):
    key='quota-test-'+uuid.uuid4().hex
    server=SingleInstanceGuard(key);assert server.claim()
    received=[];server.set_callback(received.append)
    client=SingleInstanceGuard(key)
    result=[]
    task=threading.Thread(target=lambda:result.append(client.request('settings:3')))
    task.start()
    for _ in range(25):
        QTest.qWait(50);qt_app.processEvents()
        if not task.is_alive():break
    task.join(1)
    assert result==[True]
    QTest.qWait(250);qt_app.processEvents()
    assert received==['settings:3']
    server._server.close()

def test_control_accessible_names_and_styled_popup(qt_app):
    win=MainWindow(demo=True,session_only=True)
    try:
        dialog=win.open_settings(show=False)
        assert 'configurações' in win.strip.menu.accessibleName().lower()
        assert 'quotaSettings' in dialog.styleSheet()
        assert dialog.tabs.count()==5
    finally:
        win._size_save_timer.stop();win._resize_watch_timer.stop();win.close();win.deleteLater()
