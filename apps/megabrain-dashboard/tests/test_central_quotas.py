from pathlib import Path
import sys,json,tempfile,datetime as dt,unittest
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'runtime-packages'),str(APP/'tests')]
from central_quotas import quota_view,open_widget
import test_central_security as harness

class QuotaDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        (self.root/'dados').mkdir();self.now=dt.datetime(2026,10,13,20,0,tzinfo=dt.timezone.utc)
    def tearDown(self):self.tmp.cleanup()
    def write(self,value):
        (self.root/'dados/orcamento_ia.json').write_text(json.dumps(value),encoding='utf-8')
    def account(self):return quota_view(self.root,self.now)['accounts'][0]
    def test_independent_windows_unknown_reset_and_age(self):
        self.write({'codex':{'updated_at':'2026-10-13T19:59:00+00:00','pacing':{'status':'ok','windows':{'a':{'used_percent':25,'duration_minutes':300},'b':{'used_percent':71,'duration_minutes':10080}}}}})
        a=self.account();self.assertTrue(a['fresh']);self.assertEqual(a['windows'][0]['remaining_percent'],75)
        self.assertEqual([w['period'] for w in a['windows']],['5 horas','Semana']);self.assertIsNone(a['windows'][0]['resets_at'])
    def test_missing_nan_boolean_and_out_of_range_are_unknown(self):
        for value in [None,float('nan'),float('inf'),True,'25',-1,101]:
            with self.subTest(value=value):
                self.write({'codex':{'updated_at':'2026-10-12T19:59:00+00:00','pacing':{'status':'ok','windows':[{'used_percent':value}]}}})
                a=self.account();self.assertFalse(a['fresh']);self.assertIsNone(a['windows'][0]['remaining_percent']);self.assertEqual(a['windows'][0]['period'],'Período não informado')
    def test_cache_is_used_only_when_newer_and_timestamp_has_zone(self):
        p=self.root/'apps/ia-quota-widget/app/data';p.mkdir(parents=True)
        self.write({'codex':{'updated_at':'2026-10-12T19:59:00+00:00','pacing':{'status':'ok','windows':[{'used_percent':90}]}}})
        (p/'last_snapshot.json').write_text(json.dumps({'providers':{'codex':{'fetched_at':'2026-10-13T19:59:00+00:00','source':'synthetic','status':'ok','windows':[{'used_percent':20}]}}}),encoding='utf-8')
        self.assertEqual(self.account()['windows'][0]['used_percent'],20)
        self.write({'codex':{'updated_at':'2026-10-13T19:59:30+00:00','pacing':{'status':'ok','windows':[{'used_percent':10}]}}})
        self.assertEqual(self.account()['windows'][0]['used_percent'],10)
    def test_command_and_tab_allowlist(self):
        for action,tab in [('anything',1),([],1),('settings',-1),('settings',5),('settings',True),('settings','1')]:
            with self.subTest(action=action,tab=tab):
                with self.assertRaises(ValueError):open_widget(action,tab)
    def test_bad_or_empty_new_cache_preserves_valid_observation(self):
        p=self.root/'apps/ia-quota-widget/app/data';p.mkdir(parents=True)
        self.write({'codex':{'updated_at':'2026-10-13T19:58:00Z','pacing':{'status':'ok','windows':[{'used_percent':37}]}}})
        for update in [{'status':'error','windows':[{'used_percent':0}]},{'status':'ok','windows':[]},{'status':'ok','windows':[{'used_percent':0}],'provider':'claude'}]:
            with self.subTest(update=update):
                (p/'last_snapshot.json').write_text(json.dumps({'providers':{'codex':{'fetched_at':'2026-10-13T19:59:00Z',**update}}}),encoding='utf-8')
                self.assertEqual(self.account()['windows'][0]['used_percent'],37)
    def test_missing_timezone_or_future_timestamp_is_unknown(self):
        for stamp in [None,'garbage','2026-10-13T19:59:00','2026-10-13T20:02:00Z']:
            with self.subTest(stamp=stamp):
                self.write({'codex':{'updated_at':stamp,'pacing':{'status':'ok','windows':[{'used_percent':0}]}}})
                self.assertIsNone(self.account()['windows'][0]['remaining_percent'])
                self.assertFalse(self.account()['fresh'])
    def test_window_status_fallback_duration_and_reset(self):
        self.write({'codex':{'updated_at':'2026-10-13T19:59:00Z','pacing':{'status':'NAO_MEDIDO','windows':[{'status':'ok','used_percent':0,'duration_minutes':300,'duration_is_fallback':True,'resets_at':'invalid'},{'status':'error','used_percent':0,'resets_at':'2026-10-14T20:00:00'},{'status':'ok','used_percent':50,'resets_at':'2026-10-14T20:00:00Z'}]}}})
        a=self.account();self.assertEqual(a['windows'][0]['period'],'5 horas [ESTIMATIVA]')
        self.assertEqual(a['windows'][0]['remaining_percent'],100)
        self.assertIsNone(a['windows'][0]['resets_at']);self.assertIsNone(a['windows'][1]['used_percent'])
        self.assertIsNone(a['windows'][1]['resets_at']);self.assertEqual(a['windows'][2]['resets_at'],'2026-10-14T20:00:00Z')
    def test_slow_or_pause_pacing_is_still_measured(self):
        p=self.root/'apps/ia-quota-widget/app/data';p.mkdir(parents=True)
        (p/'last_snapshot.json').write_text(json.dumps({'providers':{'codex':{'fetched_at':'2026-10-13T19:58:00Z','status':'ok','windows':[{'used_percent':20}]}}}),encoding='utf-8')
        for status,used in [('desacelerar',65),('pause',100),('NAO_MEDIDO',45)]:
            with self.subTest(status=status):
                self.write({'codex':{'updated_at':'2026-10-13T19:59:00Z','pacing':{'status':status,'windows':[{'used_percent':used}]}}})
                self.assertEqual(self.account()['windows'][0]['used_percent'],used)
                self.assertEqual(self.account()['windows'][0]['remaining_percent'],100-used)
                self.assertTrue(self.account()['fresh'])

class QuotaApiTests(unittest.TestCase):
    def setUp(self):
        self.fixture=harness.CentralSecurityTests();self.fixture.setUp();self.auth=self.fixture.local_login()
    def tearDown(self):self.fixture.tearDown()
    def test_inline_settings_auth_csrf_and_remote_scope(self):
        path='/api/quotas/widget-settings'
        self.assertEqual(self.fixture.request(self.fixture.local,path)[0],401)
        body={'changes':{'size_value':20},'expected_revision':'a'*64}
        self.assertEqual(self.fixture.request(self.fixture.local,path,method='POST',body=body,headers={'cookie':self.auth['cookie']})[0],403)
        headers={**self.fixture.remote_headers,'cookie':self.auth['cookie'],'x-mb-csrf':self.auth['x-mb-csrf']}
        for endpoint in (path,path+'/requests/'+'b'*32):
            self.assertEqual(self.fixture.request(self.fixture.remote,endpoint,headers=headers)[0],403)
        self.assertEqual(self.fixture.request(self.fixture.remote,path,method='POST',body=body,headers=headers)[0],403)
    def test_inline_settings_request_and_receipt_are_distinct(self):
        path='/api/quotas/widget-settings';revision='a'*64
        with patch('central_quotas.widget_settings',return_value={'revision':revision,'values':{'size_value':19}}):
            status,_,raw=self.fixture.request(self.fixture.local,path,headers=self.auth)
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['revision'],revision)
        with patch('central_quotas.request_widget_settings',return_value={'status':'requested','request_id':'b'*32}) as send:
            status,_,raw=self.fixture.request(self.fixture.local,path,method='POST',body={'changes':{'size_value':20},'expected_revision':revision},headers=self.auth)
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['status'],'requested');send.assert_called_once_with({'size_value':20},revision)
        with patch('central_quotas.widget_settings_status',return_value={'status':'applied','revision':'c'*64}) as receipt:
            status,_,raw=self.fixture.request(self.fixture.local,path+'/requests/'+'b'*32,headers=self.auth)
            self.assertEqual(status,200);self.assertEqual(json.loads(raw)['status'],'applied');receipt.assert_called_once_with('b'*32)
        self.assertEqual(self.fixture.request(self.fixture.local,path,method='POST',body={'changes':{},'expected_revision':revision,'command':'anything'},headers=self.auth)[0],400)
    def test_read_requires_login_and_launch_requires_csrf(self):
        self.assertEqual(self.fixture.request(self.fixture.local,'/api/quotas',headers={})[0],401)
        with patch('central_quotas.quota_view',return_value={'accounts':[]}):
            status,_,raw=self.fixture.request(self.fixture.local,'/api/quotas',headers=self.auth)
            self.assertEqual(status,200);self.assertTrue(json.loads(raw)['local_controls'])
        self.assertEqual(self.fixture.request(self.fixture.local,'/api/quotas/open-widget',method='POST',body={'action':'settings'},headers={'cookie':self.auth['cookie']})[0],403)
    def test_launch_fixed_action_and_rejects_extra_fields(self):
        with patch('central_quotas.open_widget',return_value={'status':'requested'}) as launch:
            status,_,_=self.fixture.request(self.fixture.local,'/api/quotas/open-widget',method='POST',body={'action':'settings','tab':3},headers=self.auth)
            self.assertEqual(status,200);launch.assert_called_once_with('settings',3)
        self.assertEqual(self.fixture.request(self.fixture.local,'/api/quotas/open-widget',method='POST',body={'action':'show','path':'arbitrary'},headers=self.auth)[0],400)
    def test_remote_can_read_but_cannot_launch_computer_window(self):
        headers={**self.fixture.remote_headers,'cookie':self.auth['cookie'],'x-mb-csrf':self.auth['x-mb-csrf']}
        with patch('central_quotas.quota_view',return_value={'accounts':[]}):
            status,_,raw=self.fixture.request(self.fixture.remote,'/api/quotas',headers=headers)
            self.assertEqual(status,200);self.assertFalse(json.loads(raw)['local_controls'])
        self.assertEqual(self.fixture.request(self.fixture.remote,'/api/quotas/open-widget',method='POST',body={'action':'show'},headers=headers)[0],403)

if __name__=='__main__':unittest.main()
