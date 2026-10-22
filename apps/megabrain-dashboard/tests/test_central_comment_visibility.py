"""Resolved comments leave active views without changing the historical record."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'tests')]
from central_store import Store
from central_comment_visibility import cursor_archive_script


class CommentVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'central.sqlite3')

    def test_only_verified_corrections_leave_active_view(self):
        for index,status in enumerate((None,'RECEBIDO','CORRIGIDO_VERIFICADO','aguardando teste')):
            self.store.add('comments','p',dict(id=str(index),text='Nota humana',status=status))
        self.store.add('comments','p',dict(id='missing',text='Nota sem status'))
        self.assertEqual([c['id'] for c in self.store.listing('comments','p')],['missing','3','1','0'])
        self.assertEqual(len(self.store.listing('comments','p',include_resolved=True)),5)

    def test_history_and_idempotent_retry_keep_literal_provenance(self):
        data=dict(text='Texto humano literal',target='module:now',anchor={'x':.3,'y':.5},
                  status='CORRIGIDO_VERIFICADO',correction='Correção conferida',source_hash='abc')
        record,created=self.store.create_once('comments','p',data,'attempt_1234567890','digest')
        self.assertTrue(created)
        with self.store.db() as db:
            original=db.execute('SELECT data FROM comments WHERE id=?',(record['id'],)).fetchone()[0]
        self.assertEqual(self.store.listing('comments','p'),[])
        self.assertEqual(self.store.listing('comments','p',include_resolved=True),[record])
        retry,created=self.store.create_once('comments','p',data,'attempt_1234567890','digest')
        self.assertFalse(created)
        self.assertEqual(retry,record)
        with self.store.db() as db:
            self.assertEqual(db.execute('SELECT data FROM comments WHERE id=?',(record['id'],)).fetchone()[0],original)

    def test_resolved_rows_cannot_crowd_pending_out_of_limit(self):
        self.store.add('comments','p',dict(id='pending',text='Pendência antiga'))
        with self.store.db() as db:
            db.executemany('INSERT INTO comments VALUES(?,?,?)',[(str(i),'p',json.dumps(dict(id=str(i),status='CORRIGIDO_VERIFICADO'))) for i in range(260)])
        self.assertEqual([c['id'] for c in self.store.listing('comments','p')],['pending'])
        self.assertEqual(len(self.store.listing('comments','p',include_resolved=True)),250)

    def test_project_boundary_and_other_tables_unchanged(self):
        for table in ('comments','refs','jobs'):
            self.store.add(table,'p',dict(id=table+'-done',status='CORRIGIDO_VERIFICADO'))
            self.store.add(table,'other',dict(id=table+'-other'))
            self.store.add(table,'p',dict(id=table+'-pending'))
        self.assertEqual([c['id'] for c in self.store.listing('comments','p')],['comments-pending'])
        self.assertEqual([c['id'] for c in self.store.listing('comments')],['comments-pending','comments-other'])
        for table in ('refs','jobs'):
            self.assertEqual([c['id'] for c in self.store.listing(table,'p')],[table+'-pending',table+'-done'])

    def test_cursor_archive_map_requires_verified_comment_and_exact_request_scope(self):
        for key,status in (('done','CORRIGIDO_VERIFICADO'),('pending','RECEBIDO')):
            self.store.create_once('comments','p',dict(text=key,status=status),key,'digest')
        script=cursor_archive_script(self.store)
        data=json.loads(script.split('const resolved=',1)[1].split(';',1)[0])
        self.assertEqual(list(data),['p'])
        self.assertEqual(list(data['p']),['done'])
        self.assertEqual(data['p']['done']['project'],'p')
        with self.store.db() as db:
            db.execute("UPDATE requests SET scope='comments:other' WHERE key='done'")
        script=cursor_archive_script(self.store)
        self.assertIn('const resolved={};',script)

    def test_cursor_receipt_keys_remain_separate_per_project(self):
        for pid in ('p','other'):
            self.store.create_once('comments',pid,dict(text=pid,status='CORRIGIDO_VERIFICADO'),'same-attempt','digest')
        script=cursor_archive_script(self.store)
        data=json.loads(script.split('const resolved=',1)[1].split(';',1)[0])
        self.assertEqual(data['p']['same-attempt']['text'],'p')
        self.assertEqual(data['other']['same-attempt']['text'],'other')


class CommentVisibilityApiTests(unittest.TestCase):
    def test_authenticated_project_detail_contains_only_pending_comments(self):
        import test_central_security as harness
        fixture=harness.CentralSecurityTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        for cid,status in (('pending',None),('done','CORRIGIDO_VERIFICADO')):
            fixture.store.add('comments',fixture.pid,dict(id=cid,text=cid,status=status))
        status,_,body=fixture.request(fixture.local,'/api/projects/'+fixture.pid,headers=fixture.local_login())
        self.assertEqual(status,200)
        self.assertEqual([c['id'] for c in json.loads(body)['comments']],['pending'])
        self.assertEqual(len(fixture.store.listing('comments',fixture.pid,include_resolved=True)),2)


if __name__=='__main__':
    unittest.main()
