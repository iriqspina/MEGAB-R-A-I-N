from pathlib import Path
import json, os, sys, tempfile, unittest
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from central_store import Store, ident
from central_sources import Sources

class ReturnTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261013_retornos-home/fixtures';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base)
        self.parent=Path(self.tmp.name);self.project=self.parent/'One'
        (self.project/'00_PARA-VOCE').mkdir(parents=True)
        self.report=self.project/'00_PARA-VOCE/first.html';self.report.write_text('<html>first</html>')
        self.store=Store(self.parent/'test.sqlite3');self.sources=Sources(self.store,self.parent)
    def tearDown(self):self.tmp.cleanup()
    def snapshot(self):return self.sources.returns.snapshot(self.sources)
    def observe(self):self.sources.returns.observe(self.sources)
    def test_baseline_arrival_revision_touch_restart_and_new_project(self):
        self.observe();initial=self.snapshot();self.assertEqual(initial['events'],[])
        self.assertTrue(initial['reports'][0]['baseline'])
        st=self.report.stat();os.utime(self.report,ns=(st.st_atime_ns,st.st_mtime_ns+5000000))
        self.observe();self.assertEqual(self.snapshot()['events'],[])
        self.report.write_text('<html>version two</html>');self.observe()
        second=self.snapshot();self.assertEqual(len(second['events']),1)
        self.assertEqual(second['events'][0]['kind'],'report_updated');self.assertNotEqual(second['reports'][0]['hash'],initial['reports'][0]['hash'])
        self.observe();self.assertEqual(len(self.snapshot()['events']),1)
        self.sources=Sources(self.store,self.parent);self.observe();self.assertEqual(len(self.snapshot()['events']),1)
        other=self.parent/'Two';(other/'00_PARA-VOCE').mkdir(parents=True)
        (other/'00_PARA-VOCE/second.html').write_text('<html>new project</html>')
        self.sources.discover();self.observe();new=self.snapshot()
        self.assertEqual(len(new['events']),2);self.assertEqual(new['events'][0]['kind'],'report_arrived')
        self.assertEqual(new['reports'][0]['project_id'],ident(other))
        self.assertEqual(self.sources.returns.snapshot(self.sources,new['revision'])['unread'],0)
    def test_archive_removed_file_and_shared_activity(self):
        self.observe();archive=self.project/'00_PARA-VOCE/historico/old.html';archive.parent.mkdir();archive.write_text('<html>old</html>')
        self.observe();self.assertEqual(self.snapshot()['events'],[])
        self.report.write_text('<html>changed</html>');self.observe()
        event=self.snapshot()['events'][0]
        detail=self.sources.detail(ident(self.project),force=True)
        self.assertTrue(any(x['id']=='event:'+str(event['id']) for x in detail['activity']))
        self.report.unlink();self.assertFalse(any(x['id']==ident(self.report) for x in self.snapshot()['reports']))
    def test_concurrent_scanners_do_not_duplicate(self):
        from concurrent.futures import ThreadPoolExecutor
        from central_returns import Returns
        self.observe();self.report.write_text('<html>revision concurrent</html>')
        other=Returns(self.store)
        with ThreadPoolExecutor(2) as pool:list(pool.map(lambda observer:observer.observe(self.sources),[self.sources.returns,other]))
        self.assertEqual(len(self.snapshot()['events']),1)
    def test_event_backlog_cursor_and_total_count(self):
        self.observe()
        for i in range(171):self.store.event(ident(self.project),str(i))
        first=self.store.events();second=self.store.events(first['revision'])
        self.assertEqual(len(first['events']),150);self.assertEqual(len(second['events']),21)
        snap=self.snapshot();self.assertEqual(snap['unread'],171);self.assertEqual(len(snap['events']),100)

    def test_large_report_has_explicit_viewer_limit(self):
        self.observe()
        from central_reports import MAX_REPORT
        with self.report.open('wb') as f:f.truncate(MAX_REPORT+1)
        self.observe();self.assertFalse(self.snapshot()['reports'][0]['renderable'])

class ReturnApiTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0,str(APP/'tests'))
        import test_central_security as harness
        self.fixture=harness.CentralSecurityTests();self.fixture.setUp()
    def tearDown(self):self.fixture.tearDown()
    def test_feed_requires_auth_and_keeps_paths_private(self):
        fx=self.fixture
        self.assertEqual(fx.request(fx.local,'/api/returns',headers={})[0],401)
        fx.sources.returns.observe(fx.sources)
        status,_,raw=fx.request(fx.local,'/api/returns',headers=fx.local_login())
        self.assertEqual(status,200);data=json.loads(raw)
        self.assertTrue(data['reports']);self.assertFalse(any('path' in r or 'stamp' in r for r in data['reports']))

if __name__=='__main__':unittest.main()
