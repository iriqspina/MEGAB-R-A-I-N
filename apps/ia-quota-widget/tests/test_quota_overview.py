from datetime import datetime,timezone,timedelta
from PySide6.QtCore import QPoint,QRect
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from widget_app import persistence
from widget_app.main_window import MainWindow


def test_all_windows_have_identical_bar_start_and_width(qt_app):
    persistence.save_settings(persistence.Settings(visual_mode='trilho'))
    win=MainWindow(demo=True,session_only=True);win.show_positioned();win.poll_now();qt_app.processEvents()
    reset=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    now=datetime.now(timezone.utc).isoformat()
    windows=[{'id':'session','label':'Sessão de cinco horas','duration_minutes':300,'used_percent':81.25,'resets_at':reset},
             {'id':'weekly_all','label':'Nome longo que nunca deve mover o início da barra','duration_minutes':10080,'used_percent':11,'resets_at':reset},
             {'id':'weekly_scoped:Fable','label':'Fable','duration_minutes':10080,'used_percent':0,'resets_at':reset}]
    win._on_snapshot('claude',{'status':'ok','fetched_at':now,'windows':windows,'details':{'product_shares':[{'name':'Cowork','percent':91},{'name':'Code','percent':9}]}})
    dialog=win.open_quota_details('all',win.strip.menu);qt_app.processEvents();QTest.qWait(60)
    assert len(dialog.bars)>=5
    coordinates=[(bar.mapTo(dialog.scroll.widget(),QPoint(0,0)).x(),bar.width()) for bar in dialog.bars]
    assert len(set(coordinates))==1
    count=len(dialog.bars)
    dialog.mode.setCurrentIndex(1);qt_app.processEvents()
    assert len(dialog.bars)==count
    session=next(bar for bar in dialog.bars if bar.property('raw_percent')==18.75)
    assert session.value()==1875
    dialog.copy_button.click()
    assert '81,25%' in QApplication.clipboard().text() and 'Cowork' in QApplication.clipboard().text()
    win.close();win.deleteLater()


def test_comparison_clamps_native_frame_to_small_screen(qt_app,monkeypatch):
    persistence.save_settings(persistence.Settings(visual_mode='trilho'))
    win=MainWindow(demo=True,session_only=True);win.show_positioned();win.poll_now();qt_app.processEvents()
    class SmallScreen:
        def availableGeometry(self):return QRect(-390,0,390,640)
    monkeypatch.setattr(win.strip.menu,'screen',lambda:SmallScreen())
    dialog=win.open_quota_details('all',win.strip.menu);qt_app.processEvents();QTest.qWait(60)
    assert QRect(-390,0,390,640).contains(dialog.frameGeometry())
    assert dialog.scroll.verticalScrollBar().maximum()>0
    assert dialog.close_button.isVisible()
    win.close();win.deleteLater()
