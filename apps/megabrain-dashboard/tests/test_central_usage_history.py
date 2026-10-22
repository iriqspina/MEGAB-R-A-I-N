"""Numeric-only local collection; synthetic logs, no accounts or network."""
import hashlib,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import central_usage_history as usage
from central_operations import history_data

class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.app=self.root/'app';self.home=self.root/'home'
        self.sid='12345678-1234-1234-1234-123456789abc'
        reg=self.app/'data/session-connections';reg.mkdir(parents=True)
        self.rid=hashlib.sha256(self.sid.encode()).hexdigest()[:24]
        (reg/(self.rid+'.json')).write_text(json.dumps({'id':self.rid,'project_root':str(self.root/'Synthetic'),'application':'Codex'}))
        self.source=self.home/'.codex/sessions/2026/10/15'/('rollout-'+self.sid+'.jsonl');self.source.parent.mkdir(parents=True)
        self.source.write_text('')
    def row(self,n=12):return {'type':'event_msg','timestamp':'2026-10-15T00:00:00Z','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':n,'output_tokens':5,'reasoning_output_tokens':2}}}}
    def append(self,row):
        with self.source.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
    def collect(self,**kw):return usage.collect(self.app,self.home,quota_reader=lambda:{'accounts':[]},force=True,**kw)
    def test_codex_two_cycles_replace_cumulative_and_journal_no_content(self):
        self.append({'type':'response_item','payload':{'secret_text':'HUMAN_CONTENT_NEVER_COPY'}});self.append(self.row())
        one=self.collect();self.assertEqual(one['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],12)
        self.append(self.row(17));two=self.collect();s=history_data(usage.merge({},two))['usage_sessions'][0]
        self.assertEqual(s['record_kind'],'session_cumulative');self.assertEqual(s['totals']['input_tokens'],17)
        self.assertEqual(two['new_observations'],1);self.assertEqual(len(s['messages']),1)
        self.assertNotIn('HUMAN_CONTENT_NEVER_COPY',(self.app/'data/usage-history/events.jsonl').read_text())
        size=(self.app/'data/usage-history/events.jsonl').stat().st_size;three=self.collect()
        self.assertEqual(three['new_tokens'],'NAO_MEDIDO');self.assertEqual((self.app/'data/usage-history/events.jsonl').stat().st_size,size)
    def test_unregistered_log_is_not_collected(self):
        other=self.source.with_name('rollout-abcdef12-1234-1234-1234-123456789abc.jsonl');other.write_text(json.dumps(self.row())+'\n')
        self.assertEqual(self.collect()['usage_sessions'],[])
    def test_incomplete_line_waits_then_collects_without_duplicates(self):
        raw=json.dumps(self.row());self.source.write_text(raw[:80]);self.assertEqual(self.collect()['usage_sessions'],[])
        with self.source.open('a') as f:f.write(raw[80:]+'\n')
        self.assertEqual(self.collect()['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],12)
    def test_truncated_log_refreshes_instead_of_adding_totals(self):
        self.append(self.row(123));self.collect();self.source.write_text(json.dumps(self.row(1))+'\n')
        self.assertEqual(self.collect()['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],1)
    def test_invalid_quota_never_becomes_zero(self):
        for value in (None,True,float('nan'),float('inf'),-1,101,'0'):
            self.assertIsNone(usage.quota_snapshot({'accounts':[{'id':'x','observed_at':'2026-10-15T00:00:00Z','windows':[{'used_percent':value}]}]}))
        snap=usage.quota_snapshot({'accounts':[{'id':'x','observed_at':'2026-10-15T00:00:00Z','windows':[{'used_percent':0}]}]})
        self.assertEqual(snap['providers'][0]['windows'][0]['used_percent'],0)
    def test_corrupt_state_recovers_numeric_journal_and_budget_is_bounded(self):
        self.append(self.row());self.collect();state=self.app/'data/usage-history/current.json';state.write_text('{broken')
        usage._last_good.clear();recovered=self.collect();self.assertEqual(len(recovered['usage_sessions']),1)
        self.assertEqual(recovered['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],12)
        result=usage.collect(self.root/'other-app',self.home,quota_reader=lambda:{},force=True,budget_seconds=0)
        self.assertTrue(result['limited']);self.assertEqual(result['usage_sessions'],[])
    def test_failed_cache_replace_replays_without_duplicate_event(self):
        self.append(self.row());original=usage.os.replace
        def fail_cache(src,dest):
            if Path(dest).name=='current.json':raise OSError('synthetic cache failure')
            return original(src,dest)
        with patch.object(usage.os,'replace',side_effect=fail_cache):first=self.collect()
        self.assertEqual(len(first['usage_sessions']),1)
        self.collect();lines=(self.app/'data/usage-history/events.jsonl').read_text().splitlines()
        self.assertEqual(len(lines),1);self.assertEqual(len(list((self.app/'data/usage-history/events').glob('*.json'))),1)
    def test_writer_file_lock_rejects_a_second_writer(self):
        area=self.app/'data/usage-history'
        with usage.writer(area) as one:
            with usage.writer(area) as two:self.assertTrue(one);self.assertFalse(two)
    def test_recovery_uses_observation_order_after_reset_with_same_message_time(self):
        self.append(self.row(123));self.collect()
        self.source.write_text(json.dumps(self.row(1))+'\n');self.collect()
        (self.app/'data/usage-history/current.json').write_text('{broken');usage._last_good.clear()
        with patch.object(usage,'discover',return_value=([],False)):recovered=self.collect()
        self.assertEqual(recovered['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],1)
    def test_recovery_retains_return_to_previously_seen_value_after_resets(self):
        for n in [123,1,123]:
            self.source.write_text(json.dumps(self.row(n))+'\n');self.collect()
        (self.app/'data/usage-history/current.json').write_text('{broken');usage._last_good.clear()
        with patch.object(usage,'discover',return_value=([],False)):recovered=self.collect()
        self.assertEqual(recovered['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],123)
    def test_claude_deduplicates_message_and_preserves_missing_fields(self):
        p=self.home/'.claude/projects/project'/(self.sid+'.jsonl');p.parent.mkdir(parents=True)
        row={'type':'assistant','timestamp':'2026-10-15T00:00:00Z','message':{'id':'msg1','model':'synthetic','content':'NEVER_SERIALIZE','usage':{'output_tokens':8}}}
        p.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n')
        result=self.collect();s=history_data(usage.merge({},result))['usage_sessions'][0]
        self.assertEqual(s['unique_messages'],1);self.assertEqual(s['totals']['output_tokens'],8);self.assertIsNone(s['totals']['input_tokens'])
        self.assertNotIn('NEVER_SERIALIZE',json.dumps(result))
    def test_oversized_line_cannot_stall_or_escape_chunk_budget(self):
        self.source.write_text('x'*600+'\n'+json.dumps(self.row())+'\n')
        with patch.object(usage,'MAX_CHUNK',256):
            for _ in range(6):result=self.collect()
        self.assertEqual(result['usage_sessions'][0]['messages'][0]['tokens']['input_tokens'],12)

if __name__=='__main__':unittest.main()
