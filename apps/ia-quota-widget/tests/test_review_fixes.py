import json
from datetime import datetime,timezone,timedelta
from PySide6.QtCore import QPoint
from widget_app.observed_info import observed_sections,balance_evidence_sections
from quota_details_data import claude_details,sanitize_details
from widget_app import persistence,paths
from widget_app.main_window import MainWindow
from budget_pacing import window_pacing


def test_print_correction_recalculates_remaining_and_tolerates_missing_share():
    data={'observed_usage':{'session_used_percent':5,'weekly_used_percent':20},'product_shares':[{'name':'Cowork'}]}
    text='\n'.join(a+'\n'+b for a,b in observed_sections(data))
    assert '95% restante' in text and '80% restante' in text
    assert 'percentual não informado' in text


def test_financial_expiry_epoch_is_normalized():
    rows=claude_details({'iguana_necktie':{'remaining_dollars':250,'limit_dollars':250,'resets_at':1762333140}})['financial']
    assert rows[0]['expires_at']==datetime.fromtimestamp(1762333140,timezone.utc).isoformat()


def test_financial_bad_number_is_missing_not_zero():
    result=sanitize_details({'financial':[{'title':'Saldo','amount':'not-a-number','total':float('inf')} ]})
    assert result['financial'][0]['amount'] is None and result['financial'][0]['total'] is None


def test_unknown_period_cannot_claim_ok_pacing():
    reset=(datetime.now(timezone.utc)+timedelta(minutes=40)).isoformat()
    result=window_pacing({'used_percent':65,'resets_at':reset})
    assert result['status']=='NAO_MEDIDO' and result['ahead_by'] is None
    exhausted=window_pacing({'used_percent':100,'resets_at':reset})
    assert exhausted['status']=='pause'


def test_wallet_partial_update_preserves_per_account_time(tmp_path):
    data={'observed_at':'2026-10-11T23:00:00-03:00','accounts':{'zai':{'observed_at':'2026-10-11T21:19:44-03:00','currency':'USD','balance':0,'scope':'API','source':'https://z.ai/manage-apikey/billing'}}}
    (tmp_path/'account_balance_observed.json').write_text(json.dumps(data),encoding='utf-8')
    text=str(balance_evidence_sections('zai'))
    assert '21:19:44' in text and '23:00:00' not in text


def test_partial_wallet_failure_keeps_warning_and_reset(tmp_path):
    data={'observed_at':'2026-10-11T21:00:00-03:00','accounts':{'claude':{'balance':None,'verification_status':'unavailable','resets':[{'title':'Completo','kind':'full','count':1,'usable':True}]}}}
    (tmp_path/'account_balance_observed.json').write_text(json.dumps(data),encoding='utf-8')
    text=str(balance_evidence_sections('claude'))
    assert 'não informado' in text and 'Verificação mais recente indisponível' in text and '1 restante' in text


def test_single_account_bars_align_and_balance_update_rebuilds(qt_app,tmp_path):
    persistence.save_settings(persistence.Settings(visual_mode='trilho'))
    win=MainWindow(demo=True,session_only=True);win.show_positioned();win.poll_now();qt_app.processEvents()
    detail=win.open_quota_details('claude');qt_app.processEvents()
    assert len(detail.bars)==len(detail.rows)
    assert len(set((b.mapTo(detail.body,QPoint(0,0)).x(),b.width()) for b in detail.bars))==1
    compare=win.open_quota_details('all');qt_app.processEvents()
    before=compare.last_signature
    (tmp_path/'account_balance_observed.json').write_text(json.dumps({'observed_at':'2026-10-11T21:00:00-03:00','accounts':{'zai':{'balance':3,'currency':'USD','scope':'API','source':'https://z.ai/manage-apikey/billing'}}}),encoding='utf-8')
    compare.refresh();qt_app.processEvents()
    assert compare.last_signature!=before and 'USD 3' in compare.copy_text
    win.close();win.deleteLater()
