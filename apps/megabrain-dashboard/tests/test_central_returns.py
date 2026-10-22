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
        # Source changes are machine activity: they stay in the feed (newest 100) but never count as unread.
        snap=self.snapshot();self.assertEqual(snap['unread'],0);self.assertEqual(len(snap['events']),100)
        self.assertEqual(snap['technical_count'],171);self.assertFalse(any(e['important'] for e in snap['events']))
        for kind in ('report_arrived','feedback_received','comment'):self.store.event(ident(self.project),kind,kind)
        snap=self.snapshot();self.assertEqual(snap['unread'],3);self.assertEqual(snap['technical_count'],171)
        self.assertEqual(sum(1 for e in snap['events'] if e['important']),3)
    def test_unread_counts_only_events_that_matter(self):
        from central_returns import IMPORTANT_KINDS
        self.assertEqual(set(IMPORTANT_KINDS),{'report_arrived','report_answered','feedback_received','feedback_corrected','session_completed','session_partial','session_failed','session_interrupted','comment'})
        pid=ident(self.project);self.observe()
        for kind in ('source_changed','external_operation','configuration','report_updated','dispatch_sent','reference','project_discovered','project_unavailable'):self.store.event(pid,kind,kind)
        self.assertEqual(self.snapshot()['unread'],0)
        cursor=self.snapshot()['revision']
        for kind in IMPORTANT_KINDS:self.store.event(pid,kind,kind)
        snap=self.snapshot();self.assertEqual(snap['unread'],len(IMPORTANT_KINDS));self.assertEqual(snap['technical_count'],8)
        # The read mark is an event id: only news after it count, whatever machine events came before or after.
        self.assertEqual(self.sources.returns.snapshot(self.sources,cursor)['unread'],len(IMPORTANT_KINDS))
        self.assertEqual(self.sources.returns.snapshot(self.sources,snap['revision'])['unread'],0)
        self.store.event(pid,'late machine event','source_changed')
        self.assertEqual(self.sources.returns.snapshot(self.sources,snap['revision'])['unread'],0)
        self.store.event(pid,'late answer','feedback_received')
        self.assertEqual(self.sources.returns.snapshot(self.sources,snap['revision'])['unread'],1)
    def test_machine_flood_does_not_hide_real_news(self):
        pid=ident(self.project);self.observe()
        self.store.event(pid,'Relatorio novo','report_arrived');self.store.event(pid,'Resposta recebida','feedback_received')
        for i in range(250):self.store.event(pid,'ruido '+str(i),'external_operation')
        snap=self.snapshot();titles=[e['title'] for e in snap['events'] if e['important']]
        self.assertEqual(sorted(titles),['Relatorio novo','Resposta recebida']);self.assertEqual(len(snap['events']),102)
        self.assertEqual([e['id'] for e in snap['events']],sorted((e['id'] for e in snap['events']),reverse=True))
        self.assertEqual(snap['unread'],2);self.assertEqual(snap['technical_count'],250)
    def test_event_without_kind_is_technical(self):
        pid=ident(self.project);self.observe()
        with self.store.db() as c:c.execute('INSERT INTO events(project,data) VALUES(?,?)',(pid,json.dumps(dict(project_id=pid,title='sem tipo'))))
        snap=self.snapshot();self.assertEqual(snap['unread'],0);self.assertEqual(snap['technical_count'],1);self.assertFalse(snap['events'][0]['important'])

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
