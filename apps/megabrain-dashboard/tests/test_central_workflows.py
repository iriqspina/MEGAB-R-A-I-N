"""Offline workflow contracts with synthetic models; never claims live inference."""
import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from central_store import Store,now
import central_workflows as wf
import central_artifacts as artifacts

class SourceFixture:
    def __init__(self,root):self.project=root
    def root(self,pid):return self.project
    def detail(self,pid):return {'project':{'name':'Synthetic'},'deliveries':[]}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[3]/'evidence/261011_app-megabrain/workflow-fixtures';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base);self.root=Path(self.tmp.name);self.project=self.root/'project';self.project.mkdir()
        self.store=Store(self.root/'store.sqlite3');self.sources=SourceFixture(self.project)
        self.patches=[patch.object(wf,'APP',self.root),patch.object(artifacts,'APP',self.root)]
        for p in self.patches:p.start()
        self.calls=[]
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def job(self,stages=None):
        stages=stages or [dict(id='code',title='Implementar',role='creator',model='codex',effort='xhigh',capability='code'),dict(id='review',title='Revisar',role='reviewer',model='glm',effort='max',capability='textual')]
        return self.store.enqueue('p',dict(project_id='p',title='Teste sintético',prompt='Criar saudação com teste',status='queued',route={'stages':stages},updated_at=now()))
    def model(self,model,effort,prompt,cwd,logdir,**kw):
        self.calls.append((model,kw['capability']));result=dict(status='completed',exit_code=0,text='Código produzido.',actual_model=model,tool_results=[],web_sources=[],capability=kw['capability'])
        if kw['capability']=='code':
            work=Path(kw['execution_dir']);(work/'greet.py').write_text('def greet(name):\n    return "Oi, "+name\n',encoding='utf-8')
            result['tool_results']=[dict(kind='command',command='python -m unittest discover -v',cwd=str(work),status='completed',exit_code=0,output='Ran 2 tests in 0.01s\nOK',evidence_source='synthetic-harness-event')]
            result['workspace_after']={'files':[dict(path=p.relative_to(work).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in work.rglob('*') if p.is_file()]}
        elif model=='glm':result['text']=json.dumps({'verdict':'approved','summary':'Revisão sintética aprovada.','findings':[]})
        return result
    def test_code_requires_artifact_observed_test_and_review(self):
        job=self.job()
        with patch('model_clients.run_model',side_effect=self.model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'completed');self.assertEqual(result['verification']['status'],'passed')
        self.assertEqual(result['files'][0]['action'],'created');self.assertEqual(result['tests'][0]['status'],'passed')
        self.assertEqual(self.calls,[('codex','code'),('glm','textual')]);self.assertFalse((self.project/'greet.py').exists())
    def test_review_context_keeps_large_source_and_marks_omission(self):
        directory=self.root/'context';work=directory/'workspace';work.mkdir(parents=True)
        (work/'ui.html').write_text('a'*23000+'FINAL_SOURCE',encoding='utf-8')
        rows={'files':[{'relative_path':'ui.html','sha256':'hash'}]}
        with patch.object(wf,'inventory_changes',return_value=rows):
            self.assertIn('FINAL_SOURCE',wf.file_context(directory))
            limited=wf.file_context(directory,limit=20000)
        self.assertIn('CONTEÚDO INCOMPLETO',limited);self.assertNotIn('FINAL_SOURCE',limited)
    def test_model_claim_without_tools_cannot_finish(self):
        job=self.job()
        def fake(*a,**kw):
            r=self.model(*a,**kw)
            if kw['capability']=='code':r['tool_results']=[];r['text']='Todos testes PASS, confie em mim.'
            return r
        with patch('model_clients.run_model',side_effect=fake):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id']);self.assertEqual(result['status'],'partial')
        self.assertNotEqual(result['verification']['status'],'passed');self.assertEqual(len(self.calls),4)
    def test_production_after_review_cannot_be_verified(self):
        job=self.job();code,review=job['route']['stages'];job['route']['stages']=[dict(id='brief',title='Entender',role='creator',model='codex',effort='high',capability='textual'),review,code];self.store.add('jobs','p',job)
        with patch('model_clients.run_model',side_effect=self.model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'partial')
        self.assertIn('review_precedes_last_action',result['verification']['reasons'])
    def test_unchanged_input_dependency_is_available_without_claiming_new_file(self):
        (self.project/'shared.js').write_text('const shared = 1;',encoding='utf-8')
        job=self.job();job['selected_paths']=['shared.js'];self.store.add('jobs','p',job)
        with patch('model_clients.run_model',side_effect=self.model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'completed')
        snapshot=next(a for a in result['artifacts'] if a.get('origin')=='input_snapshot')
        self.assertIn('shared.js',snapshot['title'])
        self.assertNotIn('shared.js',[f['path'] for f in result['files']])
    def test_cancel_from_another_store_before_dispatch_makes_no_model_call(self):
        job=self.job();other=Store(self.store.path);other.request_cancel(job['id'])
        with patch('model_clients.run_model',side_effect=self.model):wf.execute(self.store,self.sources,job)
        self.assertEqual(self.calls,[]);self.assertEqual(self.store.job(job['id'])['status'],'interrupted')
        recorded=json.loads((self.root/'data/jobs'/job['id']/'result.json').read_text(encoding='utf-8'))
        self.assertEqual(recorded['status'],'interrupted')
    def test_save_cannot_erase_cancel_flag(self):
        job=self.job();Store(self.store.path).request_cancel(job['id']);job['status']='running';self.store.update_job_if_active(job)
        self.assertTrue(self.store.cancellation_requested(job['id']))
    def test_repair_steps_cannot_substitute_unexecuted_original_steps(self):
        stages=[dict(id='research',title='Pesquisar',role='creator',model='claude',effort='high',capability='research'),dict(id='review',title='Revisar',role='reviewer',model='glm',effort='max'),dict(id='future',title='Código futuro',role='creator',model='codex',effort='high',capability='code')]
        job=self.job(stages)
        def fake(*a,**kw):
            r=self.model(*a,**kw)
            if a[0]=='glm':r['text']=json.dumps({'verdict':'changes_requested','summary':'Falta fonte real.','findings':[{'problem':'Fonte não consultada'}]})
            return r
        with patch('model_clients.run_model',side_effect=fake):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id']);self.assertEqual(result['status'],'partial')
        self.assertIn('required_stages_incomplete',result['verification']['reasons'])
        self.assertNotIn(('codex','code'),self.calls)
    def test_late_exception_preserves_interrupted_database_and_log(self):
        job=self.job()
        def fail(*a,**kw):
            row=self.store.job(job['id']);row.update(status='interrupted');self.store.add('jobs','p',row)
            raise RuntimeError('Late failure')
        with patch('model_clients.run_model',side_effect=fail):wf.execute(self.store,self.sources,job)
        self.assertEqual(self.store.job(job['id'])['status'],'interrupted')
        self.assertEqual(json.loads((self.root/'data/jobs'/job['id']/'result.json').read_text(encoding='utf-8'))['status'],'interrupted')

if __name__=='__main__':unittest.main()
