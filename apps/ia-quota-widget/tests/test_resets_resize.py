import pytest
from datetime import datetime,timezone
from PySide6.QtCore import QPoint,Qt,QEvent,QPointF
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from widget_app import persistence
from widget_app.main_window import MainWindow
from quota_details_data import claude_details,codex_details,reset_summary,sanitize_details


def test_reset_inventory_zero_unknown_and_unusable_are_distinct():
    assert reset_summary(codex_details({'rateLimits':{},'rateLimitResetCredits':{'availableCount':0}}))=='0'
    assert reset_summary(codex_details({'rateLimits':{}}))=='—'
    details=claude_details({'cedar_ember':{'grants':[{'type':'full','resets_left':1,'resets_total':1,'ends_at':'2026-10-22T16:00:00Z','paused':False,'usable_now':True}]}})
    assert details['resets'][0]['count']==1 and details['resets'][0]['usable']
    assert '2026-10-22' in sanitize_details(details)['resets'][0]['expires_at']
    assert not sanitize_details({'resets':[{'count':True},{'count':1.2}]})['resets']
    assert reset_summary({'resets':[{'kind':'full','count':1,'usable':True},{'kind':'five_hour','count':2,'usable':False}]})=='0H·1C'
    assert reset_summary({'resets':[{'kind':'full','count':1,'usable':False}]})=='0/1'


@pytest.mark.parametrize('edge',['left','right','top','bottom','top_left','top_right','bottom_left','bottom_right'])
def test_drag_eight_edges_preserves_both_axes_after_refresh(qt_app,monkeypatch,edge):
    persistence.save_settings(persistence.Settings(visual_mode='trilho',strip_width=600,strip_height=112,always_on_top=False))
    win=MainWindow(demo=True,session_only=True);win.show_positioned();win.move(60,80);qt_app.processEvents()
    monkeypatch.setattr(win,'windowHandle',lambda:None) # Exercise event-based fallback; OS system drag has a separate native check.
    left='left' in edge;right='right' in edge;top='top' in edge;bottom='bottom' in edge
    x=1 if left else win.width()-1 if right else win.width()//2
    y=1 if top else win.height()-1 if bottom else win.height()//2
    point=QPoint(x,y);expected=Qt.Edge(0)
    if left:expected|=Qt.LeftEdge
    if right:expected|=Qt.RightEdge
    if top:expected|=Qt.TopEdge
    if bottom:expected|=Qt.BottomEdge
    assert win._edges_at(point)==expected
    original=win.size();delta=QPoint(-30 if left else 30 if right else 0,-30 if top else 30 if bottom else 0)
    QTest.mousePress(win,Qt.LeftButton,pos=point)
    move=QMouseEvent(QEvent.MouseMove,QPointF(point+delta),QPointF(win.mapToGlobal(point)+delta),Qt.NoButton,Qt.LeftButton,Qt.NoModifier)
    qt_app.sendEvent(win,move)
    QTest.mouseRelease(win,Qt.LeftButton,pos=point+delta);qt_app.processEvents()
    assert win.width()==original.width()+(30 if left or right else 0)
    assert win.height()==original.height()+(30 if top or bottom else 0)
    size=win.size();win.poll_now();qt_app.processEvents()
    assert win.size()==size and win.settings.strip_height==win.height()
    # Saved custom height survives a fresh settings load and does not change legacy geometry.
    win._session_only=False;win._save_settings();win._session_only=True
    loaded=persistence.load_settings();assert loaded.strip_height==size.height()
    win.close();win.deleteLater()
