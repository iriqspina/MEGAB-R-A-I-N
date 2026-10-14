import importlib.util
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('usage_reader',ROOT/'bin/mb-leitura-uso.py')
MOD=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MOD)
NOW=datetime(2026,9,21,19,0,tzinfo=timezone.utc)

def account(windows, age=0, status='ok'):
    return {'updated_at':(NOW-timedelta(seconds=age)).isoformat(),'pacing':{'status':status,'windows':windows}}

def window(use=10, duration=300, elapsed=.5, status='ok'):
    return {'used_percent':use,'hours_to_reset':2.5,'elapsed_fraction':elapsed,'duration_minutes':duration,'status':status}

class UsageTests(unittest.TestCase):
    def test_exhausted_is_measured_but_not_eligible(self):
        a=MOD.analisar({'codex':account({'codex:primary':window(97)})},NOW)['accounts'][1]
        self.assertEqual(a['measurement_status'],'válido');self.assertNotEqual(a['verdict'],'NAO_MEDIDO')
        self.assertFalse(a['quota_candidate']);self.assertTrue(a['restrictions'])
    def test_fresh_spark_is_measured_but_worker_only(self):
        a=MOD.analisar({'spark':account({'codex_bengalfox:primary':window(2)})},NOW)['accounts'][4]
        self.assertEqual(a['measurement_status'],'válido');self.assertFalse(a['quota_candidate'])
        self.assertIn('worker leve',a['verdict'])
    def test_malformed_nested_data_does_not_crash(self):
        for data in [{'codex':[]},{'codex':{'pacing':[]}},{'codex':{'pacing':{'windows':[]}}},{'codex':account({1:window()})}]:
            a=MOD.analisar(data,NOW)['accounts'][1];self.assertFalse(a['quota_candidate'])
    def test_stale_is_never_healthy(self):
        a=MOD.analisar({'codex':account({'codex:primary':window()},301)},NOW)['accounts'][1]
        self.assertFalse(a['quota_candidate']);self.assertEqual(a['verdict'],'NAO_MEDIDO')
    def test_reserve_zero_cannot_override_core_limit(self):
        a=MOD.analisar({'codex_gpt2':account({'base_model_inference:primary':window(0),'codex:primary':window(97)})},NOW)['accounts'][2]
        self.assertEqual(a['limiting_used_percent'],97);self.assertFalse(a['quota_candidate'])
    def test_all_core_windows_constrain_account(self):
        a=MOD.analisar({'codex':account({'codex:primary':window(2),'codex:secondary':window(80,10080)})},NOW)['accounts'][1]
        self.assertEqual(a['verdict'],'desacelerar');self.assertFalse(a['quota_candidate'])
    def test_no_comparison_across_durations(self):
        d=MOD.analisar({'codex':account({'codex:primary':window(80,10080)}),'zai':account({'CREDIT_LIMIT:3x5':window(5)})},NOW)
        self.assertEqual(d['comparable_windows'],[])
    def test_primary_without_duration_is_not_guessed(self):
        w=window();del w['duration_minutes']
        d=MOD.analisar({'codex':account({'codex:primary':w})},NOW)['accounts'][1]['windows'][0]
        self.assertIsNone(d['duration_minutes']);self.assertEqual(d['duration_estimate_minutes'],300)
    def test_zero_elapsed_has_no_pace(self):
        d=MOD.analisar({'codex':account({'codex:primary':window(elapsed=0)})},NOW)
        self.assertIsNone(d['accounts'][1]['windows'][0]['pace_ratio'])
    def test_comparable_pressure_does_not_authorize_dispatch(self):
        d=MOD.analisar({'codex':account({'codex:primary':window(60)}),'zai':account({'CREDIT_LIMIT:3x5':window(5)})},NOW)
        self.assertEqual(d['comparable_windows'][0]['used_gap_percentage_points'],55)
        self.assertFalse(d['dispatch_authorized'])
    def test_invalid_or_auth_failed_cannot_route(self):
        for w in [window(float('nan')),window(status='auth_required')]:
            d=MOD.analisar({'codex':account({'codex:primary':w})},NOW)
            self.assertFalse(d['accounts'][1]['quota_candidate'])
    def test_future_timestamp_is_unmeasured(self):
        d=MOD.analisar({'codex':account({'codex:primary':window()},-1)},NOW)
        self.assertFalse(d['accounts'][1]['fresh'])
    def test_missing_snapshot_returns_explicit_error(self):
        self.assertIn('NAO_MEDIDO',MOD.ler(ROOT/'evidence/does-not-exist-usage.json')['error'])

if __name__=='__main__':unittest.main()
