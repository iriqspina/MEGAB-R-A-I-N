"""Independent ASGI integration checks for authenticated project report routes."""
from pathlib import Path
import hashlib
import json
import sys
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'runtime-packages'),str(APP/'tests')]
import test_central_security as harness
from central_store import Store


class ReportApiTests(unittest.TestCase):
    def setUp(self):
        self.fixture=harness.CentralSecurityTests()
        self.fixture.setUp()
        self.auth=self.fixture.local_login()
        self.asset=self.fixture.sources.index_file(self.fixture.html,self.fixture.project)
        self.fid=self.asset['id'];self.base='/api/reports/'+self.fid
        self.ticket='independent_report_ticket_123'
        self.hash=hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()

    def tearDown(self): self.fixture.tearDown()

    def request(self,path,method='GET',body=None,headers=None):
        return self.fixture.request(self.fixture.local,path,method=method,body=body,headers=self.auth if headers is None else headers)

    def json(self,path,method='GET',body=None,headers=None):
        status,response_headers,raw=self.request(path,method,body,headers)
        return status,response_headers,json.loads(raw)

    def test_report_routes_require_auth_and_mutations_require_csrf(self):
        for tail in ['view','render']:
            with self.subTest(route=tail):
                self.assertEqual(self.request(self.base+'/'+tail+'?ticket='+self.ticket,headers={})[0],401)
        for path in [self.base+'/draft',self.base+'/feedback',self.base+'/resolve','/api/present']:
            for headers,expected in [({},401),({'cookie':self.auth['cookie']},403),({**self.auth,'origin':'https://untrusted.example'},403)]:
                with self.subTest(route=path,headers=headers):
                    self.assertEqual(self.request(path,'POST',{'hash':self.hash,'note':'synthetic'},headers)[0],expected)

    def test_final_response_policies_and_wrapper_pin_the_report_version(self):
        status,headers,body=self.request(self.base+'/view?ticket='+self.ticket)
        self.assertEqual(status,200)
        self.assertIn("frame-ancestors 'self'",headers['content-security-policy'])
        self.assertIn("connect-src 'none'",headers['content-security-policy'])
        self.assertIn(('&amp;version='+self.hash).encode(),body)
        status,headers,body=self.request(self.base+'/render?ticket='+self.ticket+'&version='+self.hash)
        self.assertEqual(status,200)
        for directive in ["sandbox allow-scripts allow-forms","connect-src 'none'","worker-src 'none'","frame-src 'none'"]:
            self.assertIn(directive,headers['content-security-policy'])
        self.assertNotIn('allow-same-origin',headers['content-security-policy'])
        self.assertIn(self.hash.encode(),body)

    def test_report_status_is_authenticated_and_detects_source_updates(self):
        endpoint=self.base+'/status'
        self.assertEqual(self.request(endpoint,headers={})[0],401)
        status,_,data=self.json(endpoint)
        self.assertEqual(status,200);self.assertEqual(data['hash'],self.hash)
        self.fixture.html.write_text('<html>Updated source version for live status</html>')
        status,_,updated=self.json(endpoint)
        self.assertEqual(status,200)
        self.assertEqual(updated['hash'],hashlib.sha256(self.fixture.html.read_bytes()).hexdigest())
        self.assertNotEqual(updated['hash'],data['hash'])

    def test_audit_distinguishes_found_indexed_missing_and_incompatible_reports(self):
        missing=self.fixture.project/'00_PARA-VOCE/index-unavailable.html'
        missing.write_text('<html>Synthetic index failure</html>')
        large=self.fixture.project/'00_PARA-VOCE/too-large-interactive.html'
        from central_reports import MAX_REPORT
        with large.open('wb') as output:output.truncate(MAX_REPORT+1)
        original=self.fixture.sources.index_file
        def index(path,root,*args,**kwargs):
            if path and Path(path).resolve()==missing:return None
            return original(path,root,*args,**kwargs)
        with patch.object(self.fixture.sources,'index_file',side_effect=index), patch.object(self.fixture.sources,'summaries',wraps=self.fixture.sources.summaries) as summaries:
            status,_,audit=self.json('/api/report-audit')
        self.assertEqual(summaries.call_count,1)
        self.assertEqual(status,200)
        project=next(row for row in audit['projects'] if row['project_id']==self.fixture.pid)
        self.assertEqual(project['found'],3);self.assertEqual(project['indexed'],2)
        self.assertEqual(audit['total_found'],sum(row['found'] for row in audit['projects']))
        self.assertEqual(audit['total_indexed'],sum(row['indexed'] for row in audit['projects']))
        self.assertEqual([Path(p) for p in project['not_indexed']],[missing.relative_to(self.fixture.project)])
        self.assertEqual([Path(p) for p in project['interactive_incompatible']],[large.relative_to(self.fixture.project)])

    def test_draft_survives_store_reopen_and_recovers_into_a_new_version(self):
        # 261014, pedido do <USUARIO>: comentário não pode se perder quando o
        # relatório muda de versão. A view de uma versão sem rascunho recupera
        # o rascunho mais recente DO MESMO relatório (posições e rótulos
        # gravados continuam dizendo onde a nota estava e o que significava).
        # 261017 WP2: rascunho e envio feitos na versão que ele abriu
        # continuam aceitos depois da troca, gravados com o hash antigo e a
        # marca versao_anterior. Links (resolve) seguem exigindo a versão atual.
        original=self.fixture.html.read_bytes()
        status,_,draft=self.json(self.base+'/draft','POST',{'hash':self.hash,'storage':{'first':'human draft'}})
        self.assertEqual(status,200)
        key='report-draft:'+self.fid+':'+self.hash
        self.assertEqual(Store(self.fixture.store.path).get(key,{})['data']['storage'],{'first':'human draft'})
        status,_,body=self.request(self.base+'/view?ticket='+self.ticket)
        self.assertEqual(status,200);self.assertIn(b'human draft',body)
        self.fixture.html.write_text('<html><h1>Version B</h1></html>')
        self.assertEqual(self.request(self.base+'/render?ticket='+self.ticket+'&version='+self.hash)[0],409)
        status,_,new_view=self.request(self.base+'/view?ticket='+self.ticket)
        self.assertEqual(status,200);self.assertIn(b'human draft',new_view)
        for tail,payload in [('draft',{'storage':{'first':'old draft'}}),('feedback',{'note':'old feedback'})]:
            self.assertEqual(self.request(self.base+'/'+tail,'POST',{'hash':self.hash,**payload})[0],200)
        self.assertEqual(self.request(self.base+'/resolve','POST',{'hash':self.hash,'path':'00_PARA-VOCE/final.html'})[0],409)
        saved=Store(self.fixture.store.path).get(key,{})['data']
        self.assertEqual(saved['storage'],{'first':'old draft'});self.assertTrue(saved['versao_anterior'])
        self.assertTrue(Store(self.fixture.store.path).listing('comments',self.fixture.pid)[0]['versao_anterior'])
        self.assertNotEqual(self.fixture.html.read_bytes(),original)

    def test_local_storage_key_named_storage_is_preserved_as_data(self):
        values={'storage':'human-written','second':'also valid'}
        status,_,_=self.json(self.base+'/draft','POST',{'hash':self.hash,'storage':values})
        self.assertEqual(status,200)
        key='report-draft:'+self.fid+':'+self.hash
        self.assertEqual(Store(self.fixture.store.path).get(key,{})['data']['storage'],values)

    def test_mutations_require_a_complete_version_and_feedback_is_idempotent_and_persisted(self):
        for tail in ['draft','feedback','resolve']:
            for digest in [None,'short','x'*64]:
                payload={'note':'synthetic','storage':{},'path':'00_PARA-VOCE/final.html'}
                if digest is not None:payload['hash']=digest
                self.assertEqual(self.request(self.base+'/'+tail,'POST',payload)[0],400)
        payload={'hash':self.hash,'note':'Human correction','feedback':{'kind':'notes','notas':[{'id':'one','texto':'First correction'},{'id':'two','texto':'Second correction'}]}}
        headers={**self.auth,'idempotency-key':'independent_feedback_12345'}
        first=self.json(self.base+'/feedback','POST',payload,headers)
        second=self.json(self.base+'/feedback','POST',payload,headers)
        self.assertEqual(first[0],200);self.assertEqual(second[0],200)
        self.assertEqual(first[2]['comment']['id'],second[2]['comment']['id'])
        comments=Store(self.fixture.store.path).listing('comments',self.fixture.pid)
        self.assertEqual(len(comments),1)
        self.assertEqual(comments[0]['source_hash'],self.hash)
        self.assertEqual(Path(comments[0]['source']),Path('00_PARA-VOCE/final.html'))
        self.assertEqual(len(comments[0]['feedback']['notas']),2)
        self.assertEqual(comments[0]['status'],'Recebido, aguardando correção')
        status,_,_=self.json(self.base+'/feedback','POST',{**payload,'note':'Changed'},headers)
        self.assertEqual(status,409)

    def test_decision_validation_and_unsubmitted_feedback_do_not_create_comments(self):
        bad={'hash':self.hash,'feedback':{'kind':'decisions','finalizado':False,'respostas':{'option':'a'}}}
        self.assertEqual(self.request(self.base+'/feedback','POST',bad)[0],400)
        self.assertEqual(self.request(self.base+'/feedback','POST',{'hash':self.hash,'note':' '})[0],400)
        self.assertEqual(self.fixture.store.listing('comments',self.fixture.pid),[])
        good={**bad,'feedback':{**bad['feedback'],'finalizado':True}}
        self.assertEqual(self.request(self.base+'/feedback','POST',good)[0],200)

    def test_links_present_and_resource_loader_are_confined_to_public_project_files(self):
        project=self.fixture.project
        public=project/'00_PARA-VOCE/second.html';public.write_text('<h1>Second fixture</h1>')
        for endpoint,body in [(self.base+'/resolve',{'hash':self.hash,'path':'00_PARA-VOCE/second.html'}),('/api/present',{'path':str(public)})]:
            status,_,data=self.json(endpoint,'POST',body)
            self.assertEqual(status,200);self.assertEqual(data['project_id'],self.fixture.pid)
            self.assertEqual(data['item']['type'],'html')
        self.assertEqual(self.json('/api/present','POST',{'project':str(project)})[2]['item'],None)
        large=project/'00_PARA-VOCE/large-report.html'
        with large.open('wb') as output:output.truncate(8_000_001)
        for endpoint,body in [(self.base+'/resolve',{'hash':self.hash,'path':'00_PARA-VOCE/large-report.html'}),('/api/present',{'path':str(large)})]:
            self.assertEqual(self.json(endpoint,'POST',body)[0],200)
        outside=self.fixture.base/'outside.html';outside.write_text('<h1>outside</h1>')
        for folder in ['privado','privados','privadas','credenciais','private','secrets','.private']:
            private=project/folder/'secret.html';private.parent.mkdir();private.write_text('SYNTHETIC_PRIVATE_DATA')
            with self.subTest(folder=folder):
                self.assertEqual(self.request(self.base+'/resolve','POST',{'hash':self.hash,'path':folder+'/secret.html'})[0],400)
                self.assertEqual(self.request('/api/present','POST',{'path':str(private)})[0],400)
        self.assertEqual(self.request('/api/present','POST',{'path':str(outside)})[0],400)
        self.assertEqual(self.request(self.base+'/resolve','POST',{'hash':self.hash,'path':str(outside)})[0],400)
        secret=project/'privado/secret.js';secret.write_text('window.fixture="SYNTHETIC_PRIVATE_JS";')
        self.fixture.html.write_text('<head></head><script src="../privado/secret.js"></script>')
        new_hash=hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()
        status,_,body=self.request(self.base+'/render?ticket='+self.ticket+'&version='+new_hash)
        self.assertEqual(status,200);self.assertNotIn(b'SYNTHETIC_PRIVATE_JS',body)


if __name__=='__main__':unittest.main()
