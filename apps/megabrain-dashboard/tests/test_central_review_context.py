"""Context completeness regression; no live inference or generated code execution."""
import copy,hashlib,importlib.util,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
APP=Path(os.environ.get('MB_CONTEXT_TEST_APP',str(HERE.parent)))
sys.path.insert(0,str(APP))
sys.path.insert(0,str(APP/'tests'))
import test_central_workflows as base
import central_workflows as wf
if os.environ.get('MB_CONTEXT_CANDIDATE'):
    spec=importlib.util.spec_from_file_location('context_candidate',os.environ['MB_CONTEXT_CANDIDATE'])
    wf=importlib.util.module_from_spec(spec);spec.loader.exec_module(wf)
    base.wf=wf

class ReviewPayloadTests(unittest.TestCase):
    def test_small_evidence_is_complete_valid_json_and_preserves_items(self):
        data={'tests':[{'status':'passed','reported_count':2}], 'sources':[], 'web_actions':[]}
        with patch.object(wf,'observed_evidence',return_value=data):text,envelope=wf.evidence_context_payload([])
        self.assertEqual(json.loads(text),envelope);self.assertEqual(envelope['data'],data)
        self.assertTrue(envelope['complete']);self.assertEqual(envelope['counts']['tests']['omitted'],0)

    def test_large_evidence_omits_whole_items_and_stays_within_json_budget(self):
        data={key:[{'index':i,'value':'á漢字'*180} for i in range(20)] for key in ('tests','sources','web_actions')}
        with patch.object(wf,'observed_evidence',return_value=data):text,envelope=wf.evidence_context_payload([],limit=2400)
        self.assertEqual(json.loads(text),envelope);self.assertLessEqual(len(text),2400)
        self.assertFalse(envelope['complete']);self.assertIn('INCOMPLETA',envelope['notice'])
        self.assertGreater(sum(row['omitted'] for row in envelope['counts'].values()),0)
        for key,rows in envelope['data'].items():
            self.assertEqual(envelope['counts'][key]['included'],len(rows))
            self.assertEqual(envelope['counts'][key]['total'],len(rows)+envelope['counts'][key]['omitted'])
            self.assertEqual(rows,sorted(rows,key=lambda row:row['index']))
            for row in rows:self.assertIn(row,data[key])

    def test_one_oversized_record_cannot_become_a_truncated_record(self):
        data={'tests':[{'command':'x'*40000,'status':'passed'}],'sources':[],'web_actions':[]}
        with patch.object(wf,'observed_evidence',return_value=data):text,envelope=wf.evidence_context_payload([])
        self.assertEqual(json.loads(text),envelope);self.assertEqual(envelope['data']['tests'],[])
        self.assertFalse(envelope['complete']);self.assertEqual(envelope['counts']['tests']['omitted'],1)

    def test_file_coverage_lists_each_omission_and_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);work=directory/'workspace';work.mkdir()
            contents={'a.py':'print(1)\n','b.py':'print(2)\n'}
            rows=[]
            for path,content in contents.items():
                raw=content.encode();(work/path).write_bytes(raw)
                rows.append({'relative_path':path,'sha256':hashlib.sha256(raw).hexdigest()})
            with patch.object(wf,'inventory_changes',return_value={'files':rows}):
                text,coverage=wf.file_context_payload(directory,limit=len(contents['a.py']))
            self.assertFalse(coverage['complete']);self.assertEqual(coverage['omitted_chars'],len(contents['b.py']))
            self.assertTrue(coverage['files'][0]['complete']);self.assertFalse(coverage['files'][1]['complete'])
            self.assertIn('CONTEÚDO INCOMPLETO',text);self.assertEqual(coverage['files'][1]['included_chars'],0)

    def test_file_mutated_between_inventory_and_context_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);work=directory/'workspace';work.mkdir();(work/'a.py').write_text('print(2)',encoding='utf-8')
            with patch.object(wf,'inventory_changes',return_value={'files':[{'relative_path':'a.py','sha256':'old-digest'}]}):
                text,coverage=wf.file_context_payload(directory)
            self.assertFalse(coverage['complete']);self.assertIn('ARQUIVO ALTERADO',text)

class ReviewContextWorkflowTests(base.WorkflowTests):
    # Reuse fixtures, but load_tests excludes inherited test cases from normal
    # discovery so the nine baseline contracts are never counted twice.
    def test_approved_with_omitted_file_remains_partial_without_retry(self):
        job=self.job()
        def model(*args,**kwargs):
            if args[0]=='glm':self.assertEqual(self.store.job(job['id'])['verification']['summary'],'Etapas executadas; aguardando conclusão e revisão.')
            result=self.model(*args,**kwargs)
            if kwargs['capability']=='code':
                work=Path(kwargs['execution_dir']);(work/'large.html').write_text('<!doctype html>'+('x'*97000),encoding='utf-8')
                result['workspace_after']['files']=[{'path':p.relative_to(work).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in work.rglob('*') if p.is_file()]
            return result
        with patch('model_clients.run_model',side_effect=model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'partial');self.assertIn('review_context_incomplete',result['verification']['reasons'])
        self.assertEqual(result['reviews'][-1]['verdict'],'approved')
        self.assertFalse(result['reviews'][-1]['_review_context']['complete']);self.assertEqual(len(self.calls),2)
        metadata=json.loads((self.root/'data/jobs'/job['id']/'02-review'/'review-context.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata,result['reviews'][-1]['_review_context'])
        self.assertFalse(metadata['files']['complete'])

    def test_approved_with_omitted_evidence_remains_partial(self):
        job=self.job();real=wf.observed_evidence
        def large(results):
            observed=real(results)
            if results:observed['tests'].append({'command':'x'*40000,'status':'passed'})
            return observed
        with patch.object(wf,'observed_evidence',side_effect=large),patch('model_clients.run_model',side_effect=self.model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'partial');self.assertIn('review_context_incomplete',result['verification']['reasons'])
        self.assertFalse(result['reviews'][-1]['_review_context']['evidence']['complete']);self.assertEqual(len(self.calls),2)

    def test_omitted_previous_output_cannot_silently_approve(self):
        job=self.job()
        def model(*args,**kwargs):
            result=self.model(*args,**kwargs)
            if kwargs['capability']=='code':result['text']='x'*20001
            return result
        with patch('model_clients.run_model',side_effect=model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'partial');coverage=result['reviews'][-1]['_review_context']
        self.assertEqual(coverage['previous_output']['omitted_chars'],1);self.assertFalse(coverage['complete'])

    def test_model_cannot_forge_context_coverage_and_trigger_useless_repair(self):
        job=self.job();real=wf.evidence_context_payload
        def incomplete(*args,**kwargs):
            text,envelope=real(*args,**kwargs);envelope['complete']=False
            return json.dumps(envelope),envelope
        def model(*args,**kwargs):
            result=self.model(*args,**kwargs)
            if args[0]=='glm':result['text']=json.dumps({'verdict':'changes_requested','summary':'Material incompleto.','findings':[],'_review_context':{'complete':True}})
            return result
        with patch.object(wf,'evidence_context_payload',side_effect=incomplete),patch('model_clients.run_model',side_effect=model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertFalse(result['reviews'][-1]['_review_context']['complete']);self.assertEqual(len(self.calls),2)
        self.assertIn('review_context_incomplete',result['verification']['reasons'])

    def test_cancel_closes_only_running_step_in_persisted_state(self):
        job=self.job()
        def model(*args,**kwargs):
            result=self.model(*args,**kwargs)
            if args[0]=='glm':
                self.store.request_cancel(job['id']);kwargs['cancel_event'].set()
                result.update(status='cancelled',text='',exit_code=1)
            return result
        with patch('model_clients.run_model',side_effect=model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'interrupted')
        self.assertEqual([s['status'] for s in result['steps']],['completed','interrupted'])
        self.assertTrue(all(s.get('finished_at') for s in result['steps']))
        saved=json.loads((self.root/'data/jobs'/job['id']/'result.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['steps'],result['steps'])

    def test_client_exception_closes_running_step_without_rewriting_completed_step(self):
        job=self.job();completed=[]
        def model(*args,**kwargs):
            if args[0]=='glm':
                completed.append(copy.deepcopy(self.store.job(job['id'])['steps'][0]))
                raise RuntimeError('Synthetic client failure')
            return self.model(*args,**kwargs)
        with patch('model_clients.run_model',side_effect=model):wf.execute(self.store,self.sources,job)
        result=self.store.job(job['id'])
        self.assertEqual(result['status'],'failed');self.assertEqual(result['steps'][0],completed[0])
        self.assertEqual(result['steps'][1]['status'],'failed');self.assertTrue(result['steps'][1]['finished_at'])

def load_tests(loader,tests,pattern):
    suite=unittest.TestSuite([loader.loadTestsFromTestCase(ReviewPayloadTests)])
    suite.addTests(ReviewContextWorkflowTests(name) for name in sorted(ReviewContextWorkflowTests.__dict__) if name.startswith('test_'))
    if os.environ.get('MB_CONTEXT_CANDIDATE'):suite.addTests(loader.loadTestsFromTestCase(base.WorkflowTests))
    return suite

if __name__=='__main__':unittest.main()
