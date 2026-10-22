"""Offline contracts for separate image inputs; no inference or real app database."""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP/'runtime-packages'))
sys.path.insert(0,str(APP))
from PIL import Image
import central_artifacts as artifacts
import central_attachments as attachments
import central_execution as execution
import central_workflows as workflows
from central_store import Store,ident,now


class AttachmentExecutionTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261018_ponte-orquestradores/backend/execution-fixtures'
        base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=base)
        self.base=Path(self.tmp.name);self.project=self.base/'project';self.project.mkdir()
        self.pid=ident(self.project.resolve());self.job=self.base/'job'
        self.meta,self.data=self.image()

    def tearDown(self):self.tmp.cleanup()

    def image(self,color=(30,40,50),root=None):
        stream=io.BytesIO();Image.new('RGB',(8,8),color).save(stream,format='PNG')
        data=stream.getvalue();root=root or self.project
        metadata=attachments.save_attachment(root,ident(root.resolve()),
            dict(name='print.png',mime='image/png',data=base64.b64encode(data).decode('ascii')))
        return metadata,data

    def prepare(self,**kwargs):
        kwargs.setdefault('attachments',[self.meta['path']])
        return execution.prepare_execution(self.project,self.job,**kwargs)

    def copied(self):return self.job/'workspace'/'.mb-anexos'/(self.meta['id']+'.png')

    def code_result(self,workspace):
        rows=[dict(path=p.relative_to(workspace).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
              for p in workspace.rglob('*') if p.is_file()]
        return dict(capability='code',status='completed',exit_code=0,text='Resultado sintético.',
            tool_results=[dict(kind='command',command='python -m unittest discover -v',cwd=str(workspace),
                status='completed',exit_code=0,output='Ran 2 tests in 0.01s\nOK',evidence_source='offline-fixture')],
            workspace_after={'files':rows},web_sources=[])

    def test_canonical_image_is_a_separate_exact_input_not_a_public_artifact(self):
        prepared=self.prepare()
        self.assertEqual(self.copied().read_bytes(),self.data)
        self.assertEqual(Path(self.meta['path']).read_bytes(),self.data)
        self.assertEqual(prepared['selected_files'],[])
        baseline=json.loads(Path(prepared['baseline_path']).read_text(encoding='utf-8'))
        self.assertEqual(baseline['files'],[])
        self.assertEqual(baseline['attachments'][0]['sha256'],self.meta['id'])
        inventory=execution.inventory_changes(self.job)
        self.assertEqual(inventory['files'],[]);self.assertEqual(inventory['blocked'],[])
        self.assertEqual(inventory['input_attachments'][0]['status'],'unchanged')
        self.assertTrue(inventory['input_attachments_unchanged'])
        self.assertEqual(execution.list_source_files(self.project)['files'],[])
        self.assertEqual(execution.finalize_execution(self.job,[],mode='textual')['artifacts'],[])

    def test_images_and_hidden_paths_remain_rejected_in_selected_paths(self):
        (self.project/'visible.png').write_bytes(self.data)
        for index,selected in enumerate(['.mb-anexos/'+self.meta['id']+'.png','visible.png']):
            trial=self.base/('selected-'+str(index))
            with self.subTest(path=selected),self.assertRaises(ValueError):
                execution.prepare_execution(self.project,trial,[selected])
            self.assertFalse((trial/'workspace').exists())

    def test_all_inputs_validate_before_workspace_or_baseline_creation(self):
        missing=str(self.project/'.mb-anexos'/('f'*64+'.png'))
        with self.assertRaises(ValueError):self.prepare(attachments=[self.meta['path'],missing])
        self.assertFalse((self.job/'workspace').exists())
        self.assertFalse((self.job/'execution-baseline.json').exists())

    def test_foreign_forged_and_noncanonical_references_cannot_grant_access(self):
        other=self.base/'other-project';other.mkdir();foreign,_=self.image(root=other)
        for index,ref in enumerate([foreign['path'],self.meta['id'],
                str(self.project/'other'/Path(self.meta['path']).name),
                str(self.project/'.mb-anexos'/'..'/Path(self.meta['path']).name),
                {'id':self.meta['id'],'path':self.meta['path']} ]):
            trial=self.base/('forged-'+str(index))
            with self.subTest(reference=ref),self.assertRaises(ValueError):
                execution.prepare_execution(self.project,trial,attachments=[ref])
            self.assertFalse((trial/'workspace').exists())

    def test_six_inputs_are_supported_but_seven_references_are_rejected(self):
        refs=[self.image(color=(n,20,50))[0]['path'] for n in range(6)]
        result=self.prepare(attachments=refs)
        self.assertEqual(len(result['attachments']),6)
        self.assertEqual(len(execution.inventory_changes(self.job)['input_attachments']),6)
        with self.assertRaises(ValueError):
            execution.prepare_execution(self.project,self.base/'too-many',attachments=refs+[self.meta['path']])
        self.assertFalse((self.base/'too-many/workspace').exists())

    def test_per_image_and_total_budgets_fail_before_copy(self):
        for key in ('max_file_bytes','max_total_bytes'):
            with self.subTest(limit=key),patch.dict(execution.ATTACHMENT_LIMITS,{key:len(self.data)-1}):
                with self.assertRaises(ValueError):self.prepare()
            self.assertFalse((self.job/'workspace').exists())

    def test_corrupt_source_is_revalidated_before_copy(self):
        Path(self.meta['path']).write_bytes(b'broken image')
        with self.assertRaises(ValueError):self.prepare()
        self.assertFalse((self.job/'workspace').exists())

    def test_modified_staged_image_is_pending_and_never_published(self):
        self.prepare();data=bytearray(self.data);data[-1]^=1;self.copied().write_bytes(data)
        manifest=execution.finalize_execution(self.job,[],mode='textual')
        self.assertEqual(manifest['input_attachments'][0]['status'],'modified')
        self.assertIn('input_attachments_changed_or_missing',manifest['verification']['reasons'])
        self.assertEqual(manifest['artifacts'],[])

    def test_missing_staged_image_does_not_disappear_from_evidence(self):
        self.prepare();self.copied().unlink()
        manifest=execution.finalize_execution(self.job,[],mode='textual')
        self.assertEqual(len(manifest['input_attachments']),1)
        self.assertFalse(manifest['input_attachments_unchanged'])
        self.assertIn('input_attachments_changed_or_missing',manifest['verification']['reasons'])

    def test_extra_files_and_directories_in_attachment_namespace_are_blocked(self):
        self.prepare();folder=self.copied().parent
        (folder/'unexpected.py').write_text('print(1)',encoding='utf-8')
        (folder/'.automations').mkdir()
        inventory=execution.inventory_changes(self.job)
        self.assertFalse(inventory['input_attachments_unchanged'])
        paths={r['relative_path'] for r in inventory['blocked']}
        self.assertIn('.mb-anexos/unexpected.py',paths)
        self.assertIn('.mb-anexos/.automations',paths)
        self.assertEqual(inventory['files'],[])

    def test_unregistered_namespace_gets_no_hidden_directory_exception(self):
        execution.prepare_execution(self.project,self.job)
        folder=self.job/'workspace/.mb-anexos';folder.mkdir()
        (folder/'unexpected.py').write_text('print(1)',encoding='utf-8')
        self.assertTrue(execution.inventory_changes(self.job)['blocked'])

    def test_hardlinked_staged_input_is_rejected_even_with_the_same_hash(self):
        self.prepare();copied=self.copied();copied.unlink()
        try:os.link(self.meta['path'],copied)
        except OSError as exc:self.skipTest('Hardlinks unavailable: '+type(exc).__name__)
        self.assertFalse(execution.inventory_changes(self.job)['input_attachments_unchanged'])

    def test_symlinked_namespace_is_not_followed(self):
        self.prepare();folder=self.copied().parent;self.copied().unlink();folder.rmdir()
        outside=self.base/'outside';outside.mkdir();(outside/'secret.txt').write_text('outside fixture')
        try:folder.symlink_to(outside,target_is_directory=True)
        except OSError as exc:self.skipTest('Symlinks unavailable: '+type(exc).__name__)
        inventory=execution.inventory_changes(self.job)
        self.assertFalse(inventory['input_attachments_unchanged'])
        self.assertNotIn('outside fixture',json.dumps(inventory))

    def test_registered_images_do_not_invalidate_legitimate_code_evidence(self):
        self.prepare();workspace=self.job/'workspace'
        (workspace/'main.py').write_text('def greet(): return "Oi"\n',encoding='utf-8')
        result=self.code_result(workspace)
        manifest=execution.finalize_execution(self.job,[result],mode='code')
        self.assertEqual(manifest['verification']['status'],'passed')
        self.assertEqual([row['relative_path'] for row in manifest['artifacts']],['main.py'])

    def test_attachment_context_is_honest_for_code_and_textual_stages(self):
        self.prepare()
        for capability in ('code','textual','research'):
            text,coverage=workflows.attachment_context_payload(self.job,capability)
            self.assertIn('.mb-anexos/'+self.meta['id']+'.png',text)
            self.assertNotIn(str(self.project),text)
            self.assertFalse(coverage['complete']);self.assertFalse(coverage['visual_inspection_observed'])
            self.assertEqual(coverage['code_workspace_access'],capability=='code')
            if capability!='code':self.assertIn('SOMENTE metadados',text)

    def test_empty_prompt_reaches_code_with_real_bytes_and_visual_review_pending(self):
        store=Store(self.base/'store.sqlite3');project=self.project;data=self.data;calls=[]
        stages=[dict(id='code',title='Implementar',role='creator',model='codex',effort='xhigh',capability='code'),
                dict(id='review',title='Revisar',role='reviewer',model='glm',effort='max',capability='textual')]
        # Fixture pid deliberately differs from ident(root); attachment lookup derives the canonical root ID.
        job=store.enqueue('p',dict(project_id='p',title='Pedido com imagem',prompt='',anexos=[self.meta['path']],
            selected_paths=[],status='queued',route={'stages':stages},updated_at=now()))
        aid=self.meta['id']
        class Sources:
            def root(self,pid):return project
            def detail(self,pid):return {'project':{'name':'Fixture'},'deliveries':[]}
        def model(model,effort,prompt,cwd,logdir,**kwargs):
            calls.append(model)
            self.assertIn('PEDIDO HUMANO:\n\nCONTEXTO:',prompt)
            self.assertIn('ANEXOS DE ENTRADA',prompt)
            self.assertIn('.mb-anexos/'+aid+'.png',prompt)
            if kwargs['capability']=='code':
                workspace=Path(kwargs['execution_dir'])
                self.assertEqual((workspace/'.mb-anexos'/(aid+'.png')).read_bytes(),data)
                (workspace/'main.py').write_text('def greet(): return "Oi"\n',encoding='utf-8')
                return self.code_result(workspace)
            self.assertIn('SOMENTE metadados',prompt)
            return dict(status='completed',exit_code=0,capability='textual',tool_results=[],web_sources=[],
                text=json.dumps({'verdict':'approved','summary':'Parecer sintético.','findings':[]}))
        with patch.object(workflows,'APP',self.base),patch.object(artifacts,'APP',self.base),\
                patch('model_clients.run_model',side_effect=model):
            workflows.execute(store,Sources(),job)
        result=store.job(job['id'])
        self.assertEqual(calls,['codex','glm'])
        self.assertEqual(result['status'],'partial')
        self.assertIn('review_context_incomplete',result['verification']['reasons'])
        self.assertNotIn('blocked_files_require_review',result['verification']['reasons'])
        self.assertFalse(result['reviews'][0]['_review_context']['attachments']['complete'])
        self.assertTrue(result['input_attachments_unchanged'] if 'input_attachments_unchanged' in result else
                        all(row['status']=='unchanged' for row in result['input_attachments']))
        self.assertEqual([row['path'] for row in result['files']],['main.py'])
        self.assertTrue(all('.mb-anexos' not in row['path'] for row in result['artifacts']))
        self.assertEqual(Path(self.meta['path']).read_bytes(),self.data)


if __name__=='__main__':unittest.main()
