from quota_details_data import claude_details, codex_details, money, sanitize_details
from widget_app.providers_bridge import normalize_snapshot
from widget_app.snapshot_store import SnapshotStore
from widget_app.providers_bridge import now_iso


def test_real_money_minor_units_zero_and_missing_stay_distinct():
    assert money({'money':{'amount_minor':120000,'currency':'BRL','exponent':2}})==(1200,'BRL')
    assert money({'amount_minor':0,'currency':'USD','exponent':2})==(0,'USD')
    assert money(None) is None and money({'amount_minor':True,'currency':'BRL','exponent':2}) is None


def test_cloud_product_shares_and_unknown_usage_balance_are_separate():
    details=claude_details({'iguana_necktie':{'remaining_dollars':250,'limit_dollars':250,'resets_at':'2026-11-05T07:59:00Z'},
        'spend':{'balance':None},'extra_usage':{'is_enabled':False},
        'seven_day_breakdown':{'rows':[{'display_name':'Cowork','percent':91},{'display_name':'Claude Code','percent':9}]}})
    assert details['financial'][0]['amount']==250 and details['financial'][0]['currency']=='USD'
    assert details['financial'][1]['amount'] is None
    assert details['product_shares'][0]['percent']==91


def test_codex_credits_have_no_invented_currency_and_remain_zero():
    details=codex_details({'rateLimits':{'credits':{'hasCredits':False,'balance':'0','unlimited':False}}})
    assert details['financial'][0]['amount']==0 and details['financial'][0]['currency']=='créditos'


def test_normalization_store_error_retains_last_good_details_with_stale_marker():
    raw={'status':'ok','windows':[],'fetched_at':now_iso(),'details':{'financial':[{'title':'Saldo','amount':0,'currency':'BRL'}], 'credential':'DO-NOT-COPY'}}
    normalized=normalize_snapshot('claude',raw)
    assert 'credential' not in normalized['details']
    store=SnapshotStore();store.update('claude',normalized);store.update('claude',{'status':'error'})
    display=store.display('claude')
    assert display['stale'] and display['status']=='error'
    assert display['details']['financial'][0]['amount']==0
