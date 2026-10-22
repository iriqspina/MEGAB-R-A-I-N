"""Native image transport and review coverage, with no real inference."""
import base64,hashlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP/'runtime-packages'));sys.path.insert(0,str(APP))
from PIL import Image
import central_attachments as attachments
import central_artifacts as artifacts
import central_workflows as workflows
from central_store import Store,ident,now

class NativeAttachmentWorkflowTests(unittest.TestCase):
    def setUp(self):
        root=APP.parents[1]/'evidence/261018_ponte-orquestradores/workflow-fixtures';root.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=root);self.base=Path(self.tmp.name)
        self.project=self.base/'project';self.project.mkdir()
        stream=io.BytesIO();Image.new('RGB',(12,8),(40,80,120)).save(stream,format='PNG');self.data=stream.getvalue()
        self.image=attachments.save_attachment(self.project,ident(self.project),{'name':'prova.png','mime':'image/png','data':base64.b64encode(self.data).decode('ascii')})
        self.store=Store(self.base/'central.sqlite3')
    def tearDown(self):self.tmp.cleanup()
    def execute(self,receipt='valid',reviewer='claude'):
        rows=[dict(id='code',title='Criar',role='creator',model='codex',effort='high',capability='code'),
              dict(id='review',title='Revisar',role='reviewer',model=reviewer,effort='max' if reviewer=='glm' else 'high',capability='textual')]
        job=self.store.enqueue('fixture',dict(project_id='fixture',title='Pedido com print',prompt='',anexos=[self.image['path']],selected_paths=[],status='queued',route={'stages':rows},updated_at=now()))
        project=self.project;calls=[]
        class Sources:
            def root(self,pid):return project
            def detail(self,pid):return {'project':{'name':'Fixture'},'deliveries':[]}
        def model(model,effort,prompt,cwd,logdir,**kwargs):
            calls.append(model);paths=kwargs.get('image_paths',[])
            self.assertEqual(len(paths),1);self.assertEqual(Path(paths[0]).read_bytes(),self.data)
            self.assertTrue(Path(paths[0]).is_relative_to(self.base/'data/jobs'/job['id']/'workspace'/'.mb-anexos'))
            if model=='glm':
                return dict(status='image_transport_unavailable',exit_code=1,error='GLM-5.3 aceita somente texto.',text='')
            self.assertIn('entrada visual nativa',prompt)
            native=dict(image_inputs=[{'sha256':self.image['id'],'transported':True}],image_transport={'state':'submitted_to_cli'})
            if kwargs['capability']=='code':
                workspace=Path(kwargs['execution_dir']);(workspace/'main.py').write_text('answer = 42\n',encoding='utf-8')
                files=[dict(path=p.relative_to(workspace).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in workspace.rglob('*') if p.is_file()]
                return dict(status='completed',exit_code=0,capability='code',text='Criação sintética.',workspace_after={'files':files},web_sources=[],
                    tool_results=[dict(kind='command',command='python -m unittest discover -v',cwd=str(workspace),status='completed',exit_code=0,output='Ran 2 tests in 0.01s\nOK',evidence_source='synthetic-test')],**native)
            if receipt=='missing':native={}
            elif receipt=='wrong':native['image_inputs'][0]['sha256']='0'*64
            return dict(status='completed',exit_code=0,capability='textual',tool_results=[],web_sources=[],text=json.dumps({'verdict':'approved','summary':'Revisão sintética.','findings':[]}),**native)
        with patch.object(workflows,'APP',self.base),patch.object(artifacts,'APP',self.base),patch('model_clients.run_model',side_effect=model):
            workflows.execute(self.store,Sources(),job)
        return self.store.job(job['id']),calls
    def test_original_pixels_reach_creator_and_textual_reviewer_with_coverage(self):
        result,calls=self.execute();self.assertEqual(calls,['codex','claude'])
        self.assertEqual(result['status'],'completed')
        coverage=result['reviews'][0]['_review_context']['attachments']
        self.assertTrue(coverage['complete']);self.assertFalse(coverage['visual_inspection_observed'])
        self.assertEqual(coverage['transport_state'],'submitted_to_cli')
        self.assertTrue(all('.mb-anexos' not in row['path'] for row in result['artifacts']))
        self.assertEqual(Path(self.image['path']).read_bytes(),self.data)
    def test_wrong_image_receipt_cannot_certify_review(self):
        result,_=self.execute(receipt='wrong');self.assertEqual(result['status'],'partial')
        self.assertIn('review_context_incomplete',result['verification']['reasons'])
    def test_missing_receipt_cannot_certify_review(self):
        result,_=self.execute(receipt='missing');self.assertEqual(result['status'],'partial')
        self.assertFalse(result['reviews'][0]['_review_context']['attachments']['complete'])
    def test_unsupported_visual_client_preserves_image_and_explicit_error(self):
        result,calls=self.execute(reviewer='glm');self.assertNotEqual(result['status'],'completed')
        self.assertEqual(calls,['codex','glm']);self.assertIn('GLM-5.3',json.dumps(result,ensure_ascii=False))
        self.assertEqual(Path(self.image['path']).read_bytes(),self.data)

if __name__=='__main__':unittest.main()
