"""Production clicks never create the old settings/details windows."""
from widget_app.main_window import MainWindow
from widget_app import main_window
from widget_app import central_link
from PySide6.QtWidgets import QMenu

def test_real_account_and_settings_clicks_use_brain(qt_app,monkeypatch):
    calls=[]
    monkeypatch.setattr(central_link,'open_in_brain',lambda view,**kw:calls.append((view,kw)) or {'status':'requested'})
    win=MainWindow(demo=True,session_only=True)
    # Load demo data without network, then exercise the production routing gate.
    win.demo=False;win._session_only=False
    win.strip.menu.click()
    win.open_quota_details('codex_gpt2')
    assert calls==[('quota-settings',{}),('quota-account',{'provider':'codex_gpt2'})]
    assert win._settings_dialog is None and win._quota_details is None
    win._session_only=True;win.close()

def test_production_context_menu_keeps_configuration_in_brain(qt_app,monkeypatch):
    menus=[]
    class CapturingMenu(QMenu):
        def exec(self,*a):
            menus.append([action.text() for action in self.actions()])
    monkeypatch.setattr(main_window,'QMenu',CapturingMenu)
    win=MainWindow(demo=True,session_only=True)
    win.demo=False;win._session_only=False
    win._show_menu()
    assert any('Configurar no Brain App' in label for label in menus[0])
    assert not any('Opacidade' in label or 'Escala' in label or 'Provedores' in label for label in menus[0])
    win._session_only=True;win.close()

def test_visible_pin_keeps_saved_dimensions_and_syncs_shortcut(qt_app):
    win=MainWindow(demo=True,session_only=True)
    win.settings.visual_mode='trilho';win.settings.strip_height=113
    win.show_positioned();qt_app.processEvents()
    size=win.size();old=win.settings.always_on_top
    assert win.strip.pin.isVisible()
    win.strip.pin.click();qt_app.processEvents()
    assert win.settings.always_on_top is not old
    assert win.strip.pin.isChecked()==win.settings.always_on_top
    assert win.size()==size
    win._toggle_always_on_top();qt_app.processEvents()
    assert win.strip.pin.isChecked()==old
    assert win.size()==size
    win.close()
