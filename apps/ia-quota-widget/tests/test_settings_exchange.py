import json,time,uuid
import pytest
from widget_app import paths,persistence,settings_exchange as exchange
from widget_app.main_window import MainWindow

def test_read_does_not_write_defaults():
    result=exchange.settings_view()
    assert result['values']['number_mode']=='used'
    assert not paths.SETTINGS_PATH.exists()

@pytest.mark.parametrize('patch',[{'token':'secret'},{'size_value':True},{'poll_minutes':1},{'visible_providers':{'new-account':True}},{'provider_order':['codex','codex']},{'bg_opacity_percent':101},{'scale':float('nan')}])
def test_reject_nonvisual_or_invalid_patch(patch):
    with pytest.raises(ValueError):exchange.request_patch(patch,exchange.settings_view()['revision'])
    assert not paths.SETTINGS_PATH.exists()

def test_changed_revision_rejected_without_write():
    first=exchange.settings_view()['revision']
    persistence.save_settings(persistence.Settings(number_mode='remaining'))
    with pytest.raises(ValueError):exchange.request_patch({'number_mode':'used'},first)
    assert persistence.load_settings().number_mode=='remaining'

def test_widget_apply_and_receipt_preserve_extra_and_visibility(qt_app):
    raw={**persistence.DEFAULT_SETTINGS,'future_pref':{'untouched':42},'visible_providers':{'codex':True,'gemini_web':False,'future_provider':False},'provider_order':['future_provider','codex']}
    exchange.atomic_json(paths.SETTINGS_PATH,raw)
    win=MainWindow(demo=True)
    revision=exchange.settings_view()['revision']
    request=exchange.request_patch({'number_mode':'remaining','visible_providers':{'codex':False},'provider_order':['claude','codex']},revision)
    assert exchange.request_status(request['request_id'])['status']=='requested'
    exchange.process_requests(win.apply_external_settings)
    receipt=exchange.request_status(request['request_id'])
    assert receipt['status']=='applied'
    assert win.settings.number_mode=='remaining'
    saved=json.loads(paths.SETTINGS_PATH.read_text(encoding='utf-8'))
    assert saved['future_pref']=={'untouched':42}
    assert saved['visible_providers']=={'codex':False,'gemini_web':False,'future_provider':False}
    assert saved['provider_order']==['claude','codex','future_provider']
    win._session_only=True
    win.deleteLater()

def test_pending_widget_request_detects_conflict(qt_app):
    win=MainWindow(demo=True)
    request=exchange.request_patch({'number_mode':'remaining'},exchange.settings_view()['revision'])
    persistence.save_settings(persistence.Settings(surface_preset='musgo'))
    exchange.process_requests(win.apply_external_settings)
    assert exchange.request_status(request['request_id'])['status']=='rejected'
    assert persistence.load_settings().surface_preset=='musgo'
    win._session_only=True
    win.deleteLater()

def test_request_timeout_does_not_claim_applied():
    request=exchange.request_patch({'number_mode':'remaining'},exchange.settings_view()['revision'])
    file=paths.DATA_DIR/'settings-requests'/(request['request_id']+'.json')
    data=json.loads(file.read_text());data['at']=time.time()-21
    exchange.atomic_json(file,data)
    assert exchange.request_status(request['request_id'])['status']=='unavailable'
    invoked=[];exchange.process_requests(lambda *x:invoked.append(x))
    assert invoked==[]
    assert exchange.request_status(request['request_id'])['status']=='rejected'

def test_completed_receipts_do_not_starve_new_request():
    folder=paths.DATA_DIR/'settings-requests'
    for _ in range(60):
        ident=uuid.uuid4().hex
        exchange.atomic_json(folder/(ident+'.json'),{'old':True})
        exchange.atomic_json(folder/(ident+'.receipt.json'),{'status':'applied'})
    request=exchange.request_patch({'number_mode':'remaining'},exchange.settings_view()['revision'])
    seen=[]
    exchange.process_requests(lambda changes,revision: (seen.append(changes) or {'status':'applied'}))
    assert seen==[{'number_mode':'remaining'}]

def test_singleton_timer_applies_settings_request(qt_app):
    from PySide6.QtTest import QTest
    from widget_app.single_instance import SingleInstanceGuard
    win=MainWindow(demo=True)
    guard=SingleInstanceGuard('quota-settings-test-'+uuid.uuid4().hex)
    assert guard.claim()
    guard.set_callback(lambda command:None)
    guard.set_settings_callback(win.apply_external_settings)
    request=exchange.request_patch({'number_mode':'remaining'},exchange.settings_view()['revision'])
    QTest.qWait(450)
    qt_app.processEvents()
    assert exchange.request_status(request['request_id'])['status']=='applied'
    assert win.settings.number_mode=='remaining'
    guard._timer.stop();guard._server.close()
    win._session_only=True;win.deleteLater()

def test_open_native_editor_rejects_external_write(qt_app):
    win=MainWindow(demo=True)
    win.open_settings()
    qt_app.processEvents()
    request=exchange.request_patch({'number_mode':'remaining'},exchange.settings_view()['revision'])
    exchange.process_requests(win.apply_external_settings)
    assert exchange.request_status(request['request_id'])['status']=='rejected'
    win._settings_dialog.close();win._session_only=True;win.deleteLater()
