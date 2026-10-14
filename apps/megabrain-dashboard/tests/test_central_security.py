"""Independent API security tests. All data/keys are synthetic in workspace temp dirs.

The ASGI harness uses no network, real projects, vendor models or user sessions.
"""
from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'runtime-packages'))
import central_server as server
from central_store import Store, Conflict
from central_sources import Sources
from central_routing import DEFAULT_ROUTES

TEMP_BASE = APP.parents[1] / 'evidence' / '261011_app-megabrain' / 'security-fixtures'


async def asgi_request(app, path, method='GET', body=None, headers=None, chunks=False):
    data = json.dumps(body).encode() if isinstance(body, (dict,list)) else (body or b'')
    base = {'host': '127.0.0.1:8766'}
    if body is not None:
        base['content-type'] = 'application/json'
        if not chunks: base['content-length'] = str(len(data))
    base.update(headers or {})
    name, _, query = path.partition('?')
    scope = {'type':'http','asgi':{'version':'3.0','spec_version':'2.4'},'http_version':'1.1',
             'method':method,'scheme':'http','path':name,'raw_path':name.encode(),'query_string':query.encode(),
             'root_path':'','headers':[(k.lower().encode(),v.encode()) for k,v in base.items()],
             'client':('127.0.0.1',54321),'server':('127.0.0.1',8766)}
    pieces = [data[i:i+32_000] for i in range(0,len(data),32_000)] if chunks else [data]
    if not pieces: pieces=[b'']
    sent=[]; index=0
    async def receive():
        nonlocal index
        if index < len(pieces):
            chunk=pieces[index]; index+=1
            return {'type':'http.request','body':chunk,'more_body':index<len(pieces)}
        return {'type':'http.disconnect'}
    async def send(message): sent.append(message)
    await app(scope,receive,send)
    start=next(m for m in sent if m['type']=='http.response.start')
    content=b''.join(m.get('body',b'') for m in sent if m['type']=='http.response.body')
    return start['status'],{k.decode().lower():v.decode() for k,v in start['headers']},content


class CentralSecurityTests(unittest.TestCase):
    def setUp(self):
        TEMP_BASE.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='api-',dir=TEMP_BASE)
        self.base=Path(self.tmp.name)
        self.project=self.base/'projects'/'SyntheticProject'
        self.project.mkdir(parents=True)
        (self.project/'ESTADO.md').write_text('Estado sintético para testes independentes, sem dados do usuário.',encoding='utf-8')
        (self.project/'00_PARA-VOCE').mkdir()
        self.html=self.project/'00_PARA-VOCE'/'final.html'
        self.html.write_text('<h1>Test fixture</h1><script>window.fixtureAttack=true</script>',encoding='utf-8')
        self.store=Store(self.base/'central.sqlite3')
        self.sources=Sources(self.store,parent=self.base/'projects')
        self.sources.sessions=lambda root: []
        self.pid=next(iter(self.sources.projects))
        self.patches=[patch.object(server,'PRIVATE',self.base/'data'/'.private'),patch.object(server,'APP',self.base)]
        for item in self.patches:item.start()
        self.local=server.build_app(store=self.store,sources=self.sources)
        self.remote=server.build_app(store=Store(self.store.path),sources=self.sources,remote=True)
        self.gateway=server.secret_file('gateway.key')
        self.master=server.secret_file('native.key')
        self.remote_headers={'host':'127.0.0.1:8767','x-mb-gateway':self.gateway,'x-mb-public-origin':'https://synthetic.example.workers.dev','origin':'https://synthetic.example.workers.dev'}
    def tearDown(self):
        for item in reversed(self.patches):item.stop()
        self.tmp.cleanup()
    def request(self,app,path,**kwargs):return asyncio.run(asgi_request(app,path,**kwargs))
    def local_login(self):
        status,headers,body=self.request(self.local,'/api/pair',method='POST',body={'code':self.master},headers={'origin':'http://127.0.0.1:8766'})
        self.assertEqual(status,200)
        return {'cookie':headers['set-cookie'].split(';',1)[0],'x-mb-csrf':json.loads(body)['csrf'],'origin':'http://127.0.0.1:8766'}
    def connection(self):
        (self.base/'data'/'connection.json').write_text(json.dumps({'remote_url':'https://synthetic.example.workers.dev','status':'test'}),encoding='utf-8')
        headers=self.local_login()
        status,_,body=self.request(self.local,'/api/connection',headers=headers)
        self.assertEqual(status,200)
        return headers,json.loads(body)

    def test_remote_secret_required_before_every_route(self):
        for path in ['/', '/brand.png', '/api/health', '/api/pair', '/api/projects', '/api/files/known']:
            with self.subTest(path=path):
                self.assertEqual(self.request(self.remote,path,headers={'host':'127.0.0.1:8767'})[0],403)
        wrong=dict(self.remote_headers,**{'x-mb-gateway':'b'*64})
        self.assertEqual(self.request(self.remote,'/api/health',headers=wrong)[0],403)
    def test_anonymous_project_and_file_data_denied(self):
        for path in ['/api/projects','/api/files/known','/api/workspace','/api/jobs','/api/guide','/api/connection','/api/connection/qr']:
            with self.subTest(path=path):
                self.assertEqual(self.request(self.local,path)[0],401)
                self.assertEqual(self.request(self.remote,path,headers=self.remote_headers)[0],401)
    def test_local_native_key_never_bootstraps_remote_session(self):
        self.assertEqual(self.request(self.remote,'/api/pair',method='POST',body={'code':self.master},headers=self.remote_headers)[0],401)
    def test_hosts_origins_and_csrf(self):
        self.assertEqual(self.request(self.local,'/api/health',headers={'host':'evil.example'})[0],403)
        headers=self.local_login()
        body={'revision':0,'data':{'openProjects':[]}}
        for bad in [{'origin':'https://evil.example'},{'x-mb-csrf':''},{'sec-fetch-site':'cross-site'}]:
            with self.subTest(bad=bad):
                self.assertEqual(self.request(self.local,'/api/workspace',method='PUT',body=body,headers={**headers,**bad})[0],403)
    def test_conflicting_updates_do_not_lose_prior_work(self):
        headers=self.local_login()
        first=self.request(self.local,'/api/workspace',method='PUT',body={'revision':0,'data':{'density':'compact'}},headers=headers)
        self.assertEqual(first[0],200)
        self.assertEqual(self.request(self.local,'/api/workspace',method='PUT',body={'revision':0,'data':{'density':'different'}},headers=headers)[0],409)
        current=self.request(self.local,'/api/workspace',headers=headers)
        self.assertEqual(json.loads(current[2])['data']['density'],'compact')
    def test_actual_body_limit_without_content_length(self):
        body=json.dumps({'code':'x'*400_000}).encode()
        status,_,_=self.request(self.local,'/api/pair',method='POST',body=body,chunks=True,headers={'origin':'http://127.0.0.1:8766'})
        self.assertEqual(status,413,'Real streamed bytes must be bounded, independently of Content-Length.')
    def test_local_pairing_is_shared_remote_and_survives_restart(self):
        _,connection=self.connection()
        code=connection['pair_url'].split('#pair=',1)[1]
        rebuilt=server.build_app(store=Store(self.store.path),sources=self.sources,remote=True)
        status,headers,body=self.request(rebuilt,'/api/pair',method='POST',body={'code':code},headers=self.remote_headers)
        self.assertEqual(status,200,'Pairing created locally must work in a separate/restarted remote app.')
        for flag in ['HttpOnly','Secure','SameSite=strict']:self.assertIn(flag.lower(),headers['set-cookie'].lower())
        cookie=headers['set-cookie'].split(';',1)[0]
        restarted=server.build_app(store=Store(self.store.path),sources=self.sources,remote=True)
        self.assertEqual(self.request(restarted,'/api/session',headers={**self.remote_headers,'cookie':cookie})[0],200)
        self.assertEqual(self.request(restarted,'/api/pair',method='POST',body={'code':code},headers=self.remote_headers)[0],401)
    def test_qr_never_places_pairing_in_query_string(self):
        headers,connection=self.connection()
        self.assertEqual(connection['qr_url'],'/api/connection/qr')
        status,response_headers,content=self.request(self.local,connection['qr_url'],headers=headers)
        self.assertEqual(status,200);self.assertEqual(response_headers['content-type'],'image/png')
        self.assertTrue(content.startswith(b'\x89PNG'))
    def test_logout_revokes_session_across_app_instances(self):
        headers=self.local_login()
        self.assertEqual(self.request(self.local,'/api/logout',method='POST',body={},headers=headers)[0],200)
        other=server.build_app(store=Store(self.store.path),sources=self.sources)
        self.assertEqual(self.request(other,'/api/session',headers=headers)[0],401)
    def test_indexed_html_is_sandboxed_and_unknown_files_denied(self):
        headers=self.local_login()
        fid=self.sources.index_file(self.html,self.project)['id']
        status,out,_=self.request(self.local,'/api/files/'+fid,headers=headers)
        self.assertEqual(status,200)
        self.assertIn('sandbox',out['content-security-policy']);self.assertNotIn('allow-scripts',out['content-security-policy'])
        self.assertEqual(self.request(self.local,'/api/files/not-indexed',headers=headers)[0],404)
        outside=self.base/'outside.txt';outside.write_text('fixture')
        self.assertIsNone(self.sources.index_file(outside,self.project))
    def test_routing_rejects_flash_creator_and_missing_required_stage(self):
        headers=self.local_login();path=f'/api/projects/{self.pid}/routing'
        for change in ['flash','glm_creator','disable_required']:
            data=copy.deepcopy(DEFAULT_ROUTES)
            visual=next(r for r in data['routes'] if r['id']=='visual')
            if change=='flash':visual['stages'][0]['model']='glm-flash'
            if change=='glm_creator':visual['stages'][0]['model']='glm'
            if change=='disable_required':next(s for s in visual['stages'] if s['id']=='testar')['enabled']=False
            with self.subTest(change=change):self.assertEqual(self.request(self.local,path,method='PUT',body={'revision':0,'data':data},headers=headers)[0],400)
    def test_stage_identifiers_cannot_escape_execution_directory(self):
        headers=self.local_login();path=f'/api/projects/{self.pid}/routing'
        for stage_id in ['x/../../outside','x\\..\\..\\outside','../outside','', 'x'*200]:
            data=copy.deepcopy(DEFAULT_ROUTES)
            data['routes'][0]['stages'][0]['id']=stage_id
            with self.subTest(stage_id=stage_id):
                revision=json.loads(self.request(self.local,path,headers=headers)[2])['revision']
                self.assertEqual(self.request(self.local,path,method='PUT',body={'revision':revision,'data':data},headers=headers)[0],400)
    def test_shared_job_admission_is_atomic(self):
        barrier=threading.Barrier(2)
        def enqueue(_):
            independent=Store(self.store.path)
            barrier.wait(timeout=5)
            try:
                independent.enqueue(self.pid,{'status':'queued','title':'synthetic'})
                return 'accepted'
            except Conflict:return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(enqueue,[0,1]))
        self.assertCountEqual(outcomes,['accepted','conflict'])
        self.assertEqual(len(self.store.listing('jobs')),1)
    def test_pairing_consumption_is_atomic_between_process_connections(self):
        import time
        self.store.pairing_create('synthetic-only',time.time()+60)
        barrier=threading.Barrier(2)
        def consume(_):
            independent=Store(self.store.path)
            barrier.wait(timeout=5)
            return independent.pairing_consume('synthetic-only')
        with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(consume,[0,1]))
        self.assertCountEqual(outcomes,[True,False])
    def test_reconcile_marks_stale_jobs_interrupted_without_restarting_models(self):
        from datetime import datetime,timedelta,timezone
        old=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(timespec='seconds')
        job=self.store.enqueue(self.pid,{'status':'running','title':'synthetic','updated_at':old,'heartbeat':old})
        independent=Store(self.store.path);independent.reconcile()
        saved=next(j for j in independent.listing('jobs') if j['id']==job['id'])
        self.assertEqual(saved['status'],'interrupted')
        self.assertIn('Nenhum modelo',saved['error'])
        admitted=independent.enqueue(self.pid,{'status':'queued','title':'new synthetic'})
        self.assertNotEqual(admitted['id'],job['id'])
    def test_heartbeat_preserves_live_job_and_does_not_revive_completed_job(self):
        from datetime import datetime,timezone
        recent=datetime.now(timezone.utc).isoformat(timespec='seconds')
        job=self.store.enqueue(self.pid,{'status':'running','title':'synthetic','updated_at':recent})
        self.store.heartbeat(job['id']);self.store.reconcile()
        saved=self.store.listing('jobs')[0]
        self.assertEqual(saved['status'],'running');self.assertTrue(saved.get('heartbeat'))
        saved['status']='completed';self.store.add('jobs',self.pid,saved)
        self.store.heartbeat(job['id']);self.store.reconcile()
        self.assertEqual(self.store.listing('jobs')[0]['status'],'completed')
    def test_comment_idempotency_returns_same_id_and_rejects_conflicting_body(self):
        headers={**self.local_login(),'idempotency-key':'comment-fixture-123456'}
        path=f'/api/projects/{self.pid}/comments'; body={'text':'Synthetic note'}
        first=self.request(self.local,path,method='POST',body=body,headers=headers)
        second=self.request(self.local,path,method='POST',body=body,headers=headers)
        self.assertEqual((first[0],second[0]),(200,200))
        self.assertEqual(json.loads(first[2])['comment']['id'],json.loads(second[2])['comment']['id'])
        self.assertEqual(len(self.store.listing('comments',self.pid)),1)
        self.assertEqual(len([e for e in self.store.events()['events'] if e['kind']=='comment']),1)
        self.assertEqual(self.request(self.local,path,method='POST',body={'text':'Different'},headers=headers)[0],409)
        self.assertEqual(self.request(self.local,path,method='POST',body=body,headers={**headers,'idempotency-key':'short'})[0],400)
    def test_reference_idempotency_survives_instance_and_rejects_conflicting_body(self):
        headers={**self.local_login(),'idempotency-key':'reference-fixture-123456'}
        path=f'/api/projects/{self.pid}/references'; body={'url':'https://example.test/source','title':'Synthetic reference'}
        first=self.request(self.local,path,method='POST',body=body,headers=headers)
        rebuilt=server.build_app(store=Store(self.store.path),sources=self.sources)
        second=self.request(rebuilt,path,method='POST',body=dict(reversed(list(body.items()))),headers=headers)
        self.assertEqual((first[0],second[0]),(200,200))
        self.assertEqual(json.loads(first[2])['reference']['id'],json.loads(second[2])['reference']['id'])
        self.assertEqual(len(self.store.listing('refs',self.pid)),1)
        self.assertEqual(len([e for e in self.store.events()['events'] if e['kind']=='reference']),1)
        self.assertEqual(self.request(rebuilt,path,method='POST',body={**body,'title':'Different'},headers=headers)[0],409)
    def test_job_idempotency_starts_executor_only_once(self):
        headers={**self.local_login(),'idempotency-key':'job-fixture-123456'}
        path=f'/api/projects/{self.pid}/jobs'; body={'prompt':'Synthetic analysis, never sent to a model.','category':'pesquisa'}
        started=threading.Event()
        with patch('central_jobs.execute',side_effect=lambda *args: started.set()) as execute:
            first=self.request(self.local,path,method='POST',body=body,headers=headers)
            self.assertEqual(first[0],200,first[2])
            self.assertTrue(started.wait(timeout=3),'Synthetic executor must start.')
            rebuilt=server.build_app(store=Store(self.store.path),sources=self.sources)
            second=self.request(rebuilt,path,method='POST',body=body,headers=headers)
            conflict=self.request(rebuilt,path,method='POST',body={**body,'prompt':'Different synthetic prompt'},headers=headers)
            self.assertEqual((first[0],second[0],conflict[0]),(200,200,409))
            self.assertEqual(json.loads(first[2])['job']['id'],json.loads(second[2])['job']['id'])
            self.assertEqual(execute.call_count,1)
        self.assertEqual(len(self.store.listing('jobs',self.pid)),1)
    def test_late_executor_result_cannot_overwrite_interrupted_job(self):
        from datetime import datetime,timedelta,timezone
        old=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(timespec='seconds')
        job=self.store.enqueue(self.pid,{'status':'running','title':'synthetic','heartbeat':old})
        self.store.reconcile()
        accepted=self.store.update_job_if_active({**job,'status':'completed','output':'late synthetic result'})
        self.assertFalse(accepted)
        saved=self.store.listing('jobs')[0]
        self.assertEqual(saved['status'],'interrupted');self.assertNotIn('output',saved)
    def test_cancel_persists_across_instances_and_survives_executor_update(self):
        job=self.store.enqueue(self.pid,{'status':'running','title':'synthetic'})
        headers=self.local_login()
        remote_headers={**self.remote_headers,'cookie':headers['cookie'],'x-mb-csrf':headers['x-mb-csrf']}
        with patch('central_jobs.cancel',return_value=False):
            status,_,body=self.request(self.remote,f'/api/jobs/{job["id"]}/cancel',method='POST',body={},headers=remote_headers)
        self.assertEqual(status,200);self.assertTrue(json.loads(body)['job']['cancel_requested'])
        independent=Store(self.store.path)
        self.assertTrue(independent.cancellation_requested(job['id']))
        self.assertTrue(self.store.update_job_if_active({**job,'stage':'stale in-memory update'}))
        self.assertTrue(independent.cancellation_requested(job['id']))
    def test_artifact_routes_are_authenticated_hash_checked_and_separately_sandboxed(self):
        import central_artifacts as artifacts
        job=self.store.enqueue(self.pid,{'status':'completed','title':'synthetic'})
        with patch.object(artifacts,'APP',self.base):
            directory=artifacts.job_directory(job['id']);(directory/'workspace').mkdir(parents=True)
            code=directory/'workspace/index.html';code.write_text('<button>Fixture</button><script>document.body.dataset.ready="yes"</script>')
            artifact=artifacts.register_artifact(job['id'],'workspace/index.html')
            self.store.add('jobs',self.pid,{**job,'artifacts':[artifact]})
            headers=self.local_login()
            for kind in ['artifacts','view','preview','render','resources']:
                path=f'/api/jobs/{job["id"]}/{kind}/{artifact["id"]}'
                self.assertEqual(self.request(self.local,path)[0],401)
                self.assertEqual(self.request(self.remote,path,headers=self.remote_headers)[0],401)
            download=self.request(self.local,artifact['url'],headers=headers)
            self.assertEqual(download[0],200);self.assertIn('attachment',download[1]['content-disposition'])
            wrapper=self.request(self.local,artifact['preview_url'],headers=headers)
            self.assertEqual(wrapper[0],200);self.assertIn("frame-src 'self'",wrapper[1]['content-security-policy'])
            render=self.request(self.local,f'/api/jobs/{job["id"]}/render/{artifact["id"]}',headers=headers)
            self.assertEqual(render[0],200);self.assertIn('sandbox allow-scripts',render[1]['content-security-policy'])
            self.assertNotIn('allow-same-origin',render[1]['content-security-policy'])
            self.assertIn("connect-src 'none'",render[1]['content-security-policy'])
            unknown=self.request(self.local,f'/api/jobs/{job["id"]}/artifacts/'+('b'*24),headers=headers)
            self.assertEqual(unknown[0],404)
            code.write_text('changed since registration')
            self.assertEqual(self.request(self.local,artifact['url'],headers=headers)[0],400)
    def test_source_watcher_continues_after_one_project_fails(self):
        other=self.base/'projects/OtherSyntheticProject';other.mkdir();(other/'ESTADO.md').write_text('synthetic')
        self.sources.discover();pids=list(self.sources.projects)
        self.sources.fingerprints[pids[1]]='previous'
        with patch.object(self.sources,'fingerprint',side_effect=[OSError('synthetic inaccessible file'),'new']),self.assertLogs('megabrain.sources',level='WARNING'):
            self.sources.poll()
        self.assertEqual(self.sources.fingerprints[pids[1]],'new')
        self.assertTrue(any(e['project_id']==pids[1] for e in self.store.events()['events']))


if __name__=='__main__':unittest.main()
