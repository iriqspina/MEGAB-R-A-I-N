"""261017 WP2: notas feitas na versão que o <USUARIO> abriu chegam ao projeto.

A IA pode regravar o relatório enquanto ele comenta. O rascunho e o envio
feitos na versão aberta continuam aceitos, gravados com o hash antigo e a marca
``versao_anterior``. Hash de outro relatório, nunca aberto ou mal formado
continua recusado. Tudo sintético, em pasta temporária (harness ASGI, sem rede).
"""
from pathlib import Path
import hashlib
import json
import sys
import unittest

APP=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(APP),str(APP/'runtime-packages'),str(APP/'tests')]
import test_central_security as harness
from central_store import Store


class PreviousVersionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=harness.CentralSecurityTests()
        self.fixture.setUp()
        self.auth=self.fixture.local_login()
        self.asset=self.fixture.sources.index_file(self.fixture.html,self.fixture.project)
        self.fid=self.asset['id'];self.base='/api/reports/'+self.fid
        self.ticket='wp2_previous_version_ticket'
        self.old=hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()

    def tearDown(self): self.fixture.tearDown()

    def request(self,path,method='GET',body=None,headers=None):
        return self.fixture.request(self.fixture.local,path,method=method,body=body,headers=self.auth if headers is None else headers)

    def json(self,path,method='GET',body=None,headers=None):
        status,_,raw=self.request(path,method,body,headers)
        return status,json.loads(raw)

    def open_view(self,base=None):
        status,_,_=self.request((base or self.base)+'/view?ticket='+self.ticket)
        self.assertEqual(status,200)

    def change_report(self,text='<h1>Versão nova gravada pela IA</h1>'):
        self.fixture.html.write_text(text,encoding='utf-8')
        new=hashlib.sha256(self.fixture.html.read_bytes()).hexdigest()
        self.assertNotEqual(new,self.old)
        return new

    def comments(self):
        return Store(self.fixture.store.path).listing('comments',self.fixture.pid)

    def test_view_records_the_opened_version_for_this_report_only(self):
        self.open_view()
        saved=Store(self.fixture.store.path).get('report-versions:'+self.fid,{})['data']
        self.assertEqual(saved['hashes'],[self.old])
        self.open_view()  # reabrir a mesma versão não duplica
        self.assertEqual(Store(self.fixture.store.path).get('report-versions:'+self.fid,{})['data']['hashes'],[self.old])

    def test_note_on_the_opened_version_arrives_marked_as_previous_after_the_file_changes(self):
        self.open_view()
        new=self.change_report()
        note={'id':'nmwp2a','texto':'Trocar a cor do título','onde':'h1'}
        body={'hash':self.old,'feedback':{'kind':'notes','notas':[note]},'note':''}
        status,data=self.json(self.base+'/feedback','POST',body,{**self.auth,'idempotency-key':'wp2_note_nmwp2a_0001'})
        self.assertEqual(status,200,data)
        self.assertTrue(data['versao_anterior'])
        comment=data['comment']
        self.assertEqual(comment['source_hash'],self.old)
        self.assertTrue(comment['versao_anterior'])
        self.assertEqual(comment['hash_atual'],new)
        self.assertEqual(comment['feedback']['notas'][0]['texto'],'Trocar a cor do título')
        self.assertEqual(comment['status'],'Recebido, aguardando correção')
        self.assertEqual(len(self.comments()),1)
        events=Store(self.fixture.store.path).events(0)['events']
        self.assertTrue(any(e['kind']=='feedback_received' and 'versão anterior' in e['title'] for e in events))

    def test_draft_on_the_opened_version_is_saved_under_the_old_hash(self):
        self.open_view()
        new=self.change_report()
        status,data=self.json(self.base+'/draft','POST',{'hash':self.old,'storage':{'mb-report-notas:x':'[]'}})
        self.assertEqual(status,200,data)
        saved=Store(self.fixture.store.path).get('report-draft:'+self.fid+':'+self.old,{})['data']
        self.assertEqual(saved['storage'],{'mb-report-notas:x':'[]'})
        self.assertEqual(saved['source_hash'],self.old)
        self.assertTrue(saved['versao_anterior']);self.assertEqual(saved['hash_atual'],new)
        # a versão atual continua sem marca
        status,_=self.json(self.base+'/draft','POST',{'hash':new,'storage':{'a':'b'}})
        self.assertEqual(status,200)
        current=Store(self.fixture.store.path).get('report-draft:'+self.fid+':'+new,{})['data']
        self.assertNotIn('versao_anterior',current)

    def test_current_version_feedback_has_no_previous_marker(self):
        self.open_view()
        status,data=self.json(self.base+'/feedback','POST',{'hash':self.old,'note':'Nota na versão atual'})
        self.assertEqual(status,200,data)
        self.assertFalse(data['versao_anterior'])
        self.assertNotIn('versao_anterior',data['comment'])

    def test_legacy_version_known_only_by_its_draft_is_accepted(self):
        # Versões abertas antes do registro report-versions deixaram rascunho.
        status,_=self.json(self.base+'/draft','POST',{'hash':self.old,'storage':{'k':'v'}})
        self.assertEqual(status,200)
        Store(self.fixture.store.path)  # sem view: não há report-versions
        self.assertEqual(Store(self.fixture.store.path).get('report-versions:'+self.fid,{})['revision'],0)
        self.change_report()
        status,data=self.json(self.base+'/feedback','POST',{'hash':self.old,'note':'Feita antes do registro'})
        self.assertEqual(status,200,data);self.assertTrue(data['versao_anterior'])

    def test_unknown_or_other_report_hash_is_refused_and_invalid_format_is_400(self):
        other=self.fixture.project/'00_PARA-VOCE'/'outro.html'
        other.write_text('<h1>Outro relatório</h1>',encoding='utf-8')
        other_fid=self.fixture.sources.index_file(other,self.fixture.project)['id']
        self.assertNotEqual(other_fid,self.fid)
        other_hash=hashlib.sha256(other.read_bytes()).hexdigest()
        self.open_view('/api/reports/'+other_fid)  # hash conhecido, mas do OUTRO relatório
        self.open_view()
        self.change_report()
        for digest in [other_hash,'f'*64]:
            for tail,payload in [('draft',{'storage':{}}),('feedback',{'note':'não pode entrar'})]:
                with self.subTest(digest=digest[:8],route=tail):
                    status,data=self.json(self.base+'/'+tail,'POST',{'hash':digest,**payload})
                    self.assertEqual(status,409,data)
                    self.assertIn('O relatório mudou',data['detail'])
        for digest in [None,'curto','X'*64]:
            payload={'note':'x','storage':{}}
            if digest is not None:payload['hash']=digest
            for tail in ['draft','feedback']:
                with self.subTest(digest=str(digest)[:6],route=tail):
                    self.assertEqual(self.request(self.base+'/'+tail,'POST',payload)[0],400)
        self.assertEqual(self.comments(),[])
        # outras rotas continuam exigindo a versão atual
        self.assertEqual(self.request(self.base+'/resolve','POST',{'hash':self.old,'path':'00_PARA-VOCE/final.html'})[0],409)

    def test_per_note_idempotency_survives_retries_and_version_change(self):
        self.open_view()
        def send(note_id,text,key):
            body={'hash':self.old,'feedback':{'kind':'notes','notas':[{'id':note_id,'texto':text}]},'note':''}
            return self.json(self.base+'/feedback','POST',body,{**self.auth,'idempotency-key':key})
        first=send('n1','Primeira nota','wp2_key_note_n1_aaaa')
        retry=send('n1','Primeira nota','wp2_key_note_n1_aaaa')
        self.assertEqual((first[0],retry[0]),(200,200))
        self.assertEqual(first[1]['comment']['id'],retry[1]['comment']['id'])
        second=send('n2','Segunda nota','wp2_key_note_n2_bbbb')
        self.assertEqual(second[0],200);self.assertNotEqual(second[1]['comment']['id'],first[1]['comment']['id'])
        self.change_report()
        # nova tentativa com a mesma chave depois da troca de versão: mesmo registro
        late=send('n1','Primeira nota','wp2_key_note_n1_aaaa')
        self.assertEqual(late[0],200);self.assertEqual(late[1]['comment']['id'],first[1]['comment']['id'])
        # mesma chave com outro conteúdo é recusada
        self.assertEqual(send('n1','Texto trocado','wp2_key_note_n1_aaaa')[0],409)
        self.assertEqual(len(self.comments()),2)


if __name__=='__main__':
    unittest.main()
