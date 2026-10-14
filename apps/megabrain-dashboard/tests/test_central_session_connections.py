import json, sys, tempfile, threading, unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP))
from central_session_connections import snapshot

class SessionConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.app=Path(self.temp.name);self.root=self.app/'project';self.root.mkdir()
        self.registry=self.app/'data/session-connections';self.registry.mkdir(parents=True)
        self.queue=self.app/'data/open-requests';self.queue.mkdir()
        self.sources=SimpleNamespace(lock=threading.RLock(),projects={'p1':self.root})
        self.sid='a'*24;self.rid='b'*32
        self.record=dict(schema_version=1,id=self.sid,project_root=str(self.root),application='synthetic',started_at=datetime.now(timezone.utc).isoformat(),updated_at=datetime.now(timezone.utc).isoformat(),bridge_version='1.0.0',presentation_request_id=self.rid)
        self.write(self.registry/(self.sid+'.json'),self.record)
    def tearDown(self): self.temp.cleanup()
    def write(self,p,value): p.write_text(json.dumps(value),encoding='utf-8')
    def row(self): return snapshot(self.app,self.sources)['sessions'][0]
    def receipt(self,ok=True,pid='p1',root=None):
        self.write(self.queue/(self.rid+'.receipt'),dict(requestId=self.rid,ok=ok,project_id=pid))
        self.write(self.queue/(self.rid+'.presented'),dict(id=self.rid,project=str(root or self.root)))
    def test_registration_and_health_do_not_prove_presentation(self):
        self.assertEqual(self.row()['state'],'pending');self.assertEqual(snapshot(self.app,self.sources)['presented_count'],0)
    def test_receipt_must_match_request_project_and_catalogue(self):
        self.receipt();self.assertEqual(self.row()['state'],'presented');self.assertTrue(self.row()['presented_at'])
        self.receipt(pid='another');self.assertEqual(snapshot(self.app,self.sources)['rejected_count'],1)
        self.receipt(root=self.app/'other');self.assertEqual(snapshot(self.app,self.sources)['presented_count'],0)
    def test_unknown_project_is_visible_but_never_presented(self):
        self.sources.projects={};self.receipt();self.assertEqual(self.row()['state'],'unregistered_project')
    def test_failed_expired_invalid_are_not_pending(self):
        self.receipt(False);self.assertEqual(self.row()['state'],'failed')
        (self.queue/(self.rid+'.receipt')).unlink()
        for suffix in ('expired','invalid','failed'):
            path=self.queue/(self.rid+'.'+suffix);path.write_text('{}');self.assertEqual(self.row()['state'],'failed');path.unlink()
    def test_malformed_future_and_traversal_records_are_rejected(self):
        for fields in ({'schema_version':2},{'updated_at':'2099-01-01T00:00:00Z'},{'presentation_request_id':'../native.key'},{'id':'different'},{'started_at':'2026-10-13'}):
            self.write(self.registry/(self.sid+'.json'),{**self.record,**fields});self.assertEqual(snapshot(self.app,self.sources)['registered_count'],0)
    def test_no_open_and_missing_launcher_are_distinct(self):
        self.record.update(presentation_request_id=None,error='presentation_not_requested');self.write(self.registry/(self.sid+'.json'),self.record);self.assertEqual(self.row()['state'],'registered')
        self.record['error']='launcher_unavailable';self.write(self.registry/(self.sid+'.json'),self.record);self.assertEqual(self.row()['state'],'unavailable')
    def test_api_requires_authentication(self):
        sys.path.insert(0,str(APP/'tests'));import test_central_security as harness
        fixture=harness.CentralSecurityTests();fixture.setUp()
        try:
            self.assertEqual(fixture.request(fixture.local,'/api/session-connections',headers={})[0],401)
            auth=fixture.local_login()
            self.assertEqual(fixture.request(fixture.local,'/api/session-connections',headers=auth)[0],200)
        finally:fixture.tearDown()

if __name__=='__main__': unittest.main()
