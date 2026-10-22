"""Short catalogue cache and singleflight, using isolated synthetic roots."""
import concurrent.futures,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from central_sources import Sources
from central_store import Store,ident
class SummaryCacheTests(unittest.TestCase):
 def setUp(self):
  base=APP.parents[1]/'evidence/261015_comentarios-todos/aparencia/cache-fixtures';base.mkdir(parents=True,exist_ok=True)
  self.tmp=tempfile.TemporaryDirectory(dir=base);self.parent=Path(self.tmp.name)
  self.a=self.parent/'A';self.b=self.parent/'B'
  for p in [self.a,self.b]:(p/'00_PARA-VOCE').mkdir(parents=True)
  (self.a/'00_PARA-VOCE/a.html').write_text('<html>A</html>');(self.b/'00_PARA-VOCE/b.html').write_text('<html>B</html>')
  self.sources=Sources(Store(self.parent/'test.sqlite3'),self.parent)
 def tearDown(self):self.tmp.cleanup()
 def test_cache_returns_independent_snapshots_and_keeps_observation_time(self):
  with patch.object(self.sources,'report_paths',wraps=self.sources.report_paths) as scan:
   a=self.sources.summaries();a['projects'][0]['name']='mutated';b=self.sources.summaries()
   self.assertEqual(scan.call_count,2);self.assertEqual(b['projects'][0]['name'],'A');self.assertEqual(a['scanned_at'],b['scanned_at'])
 def test_simultaneous_readers_share_one_scan_per_root(self):
  original=self.sources.report_paths
  def slow(root):time.sleep(.06);return original(root)
  with patch.object(self.sources,'report_paths',side_effect=slow) as scan,concurrent.futures.ThreadPoolExecutor(6) as pool:
   results=list(pool.map(lambda _:self.sources.summaries(),range(6)))
   self.assertEqual(scan.call_count,2);self.assertEqual(len({r['revision'] for r in results}),1)
 def test_complete_snapshot_ttl_starts_after_long_scan(self):
  self.sources.summary_ttl=.03;original=self.sources.report_paths
  def slow(root):time.sleep(.04);return original(root)
  with patch.object(self.sources,'report_paths',side_effect=slow) as scan:
   self.sources.summaries();self.sources.summaries();self.assertEqual(scan.call_count,2)
 def test_expiry_and_force_refresh_count(self):
  first=self.sources.summaries();(self.a/'00_PARA-VOCE/new.html').write_text('<html>new</html>')
  self.assertEqual(self.sources.summaries()['revision'],first['revision'])
  self.assertEqual(self.sources.project_summary(ident(self.a),force=True)['report_count'],2)
  self.sources.summary_ttl=0;self.assertNotEqual(self.sources.summaries()['revision'],first['revision'])
 def test_detail_does_not_enumerate_other_roots(self):
  with patch.object(self.sources,'report_paths',wraps=self.sources.report_paths) as scan,patch.object(self.sources,'sessions',return_value=[]):
   self.sources.detail(ident(self.a),force=True)
   self.assertTrue(all(call.args[0]==self.a for call in scan.call_args_list))
 def test_discovery_and_poll_invalidate_changed_project(self):
  with patch('central_feedback.scan'),patch.object(self.sources.returns,'observe'):
   self.sources.poll();self.sources.summaries();(self.a/'00_PARA-VOCE/new.html').write_text('<html>new</html>');self.sources.poll()
  self.assertEqual(next(r for r in self.sources.summaries()['projects'] if r['id']==ident(self.a))['report_count'],2)
  c=self.parent/'C';(c/'00_PARA-VOCE').mkdir(parents=True);self.sources.discover();self.assertEqual(len(self.sources.summaries()['projects']),3)
 def test_invalidated_inflight_scan_is_not_cached(self):
  begun=threading.Event();release=threading.Event();original=self.sources.report_paths
  def slow(root):begun.set();release.wait(2);return original(root)
  with patch.object(self.sources,'report_paths',side_effect=slow),concurrent.futures.ThreadPoolExecutor(1) as pool:
   future=pool.submit(self.sources.project_summary,ident(self.a));self.assertTrue(begun.wait(1));self.sources.invalidate_summary(ident(self.a));release.set();future.result()
  self.assertNotIn(ident(self.a),self.sources.summary_cache)
if __name__=='__main__':unittest.main()
