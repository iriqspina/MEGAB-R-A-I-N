from pathlib import Path
import json
import tempfile
import time
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from central_presentation import PresentationQueue

class PresentationTests(unittest.TestCase):
    def test_quota_destination_is_bounded_and_receipt_matches(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            for ident,view,provider in [('0','javascript:evil','all'),('1','quota-account','unknown'),('1a',[],'all'),('1b','quota-account',{}),('2','quota-account','codex_gpt2')]:
                (directory/(ident+'.json')).write_text(json.dumps({'at':time.time(),'project':'synthetic','view':view,'provider':provider}),encoding='utf-8')
            queue=PresentationQueue(directory)
            payload=queue.next()
            self.assertEqual(payload['view'],'quota-account')
            self.assertEqual(payload['provider'],'codex_gpt2')
            self.assertEqual(payload['requestId'],'2')
            self.assertTrue((directory/'0.invalid').exists())
            self.assertTrue((directory/'1.invalid').exists())
            self.assertFalse(queue.finish({'requestId':'wrong','ok':True}))
            self.assertTrue(queue.finish({'requestId':'2','ok':True,'view':'quota-account'}))

    def test_invalid_request_does_not_block_and_dispatch_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            (directory/'0.json').write_text('{',encoding='utf-8')
            (directory/'1.json').write_text(json.dumps({'at':time.time(),'path':'synthetic.html'}),encoding='utf-8')
            queue=PresentationQueue(directory)
            payload=queue.next()
            self.assertTrue((directory/'0.invalid').exists())
            self.assertEqual(payload['requestId'],'1')
            self.assertTrue((directory/'1.json').exists())
            self.assertFalse(queue.finish({'requestId':'other','ok':True}))
            self.assertTrue(queue.finish({'requestId':'1','ok':True}))
            self.assertTrue((directory/'1.presented').exists())
            self.assertEqual(json.loads((directory/'1.receipt').read_text())['ok'],True)

    def test_failure_and_timeout_are_not_presented(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            queue=PresentationQueue(directory)
            for name in ['fail','timeout']:
                (directory/(name+'.json')).write_text(json.dumps({'at':time.time(),'project':'synthetic'}),encoding='utf-8')
                queue.next()
                if name=='fail':queue.finish({'requestId':name,'ok':False,'error':'Unindexed'})
                else:
                    queue.current=(queue.current[0],time.time()-61)
                    self.assertTrue(queue.timeout())
                self.assertTrue((directory/(name+'.failed')).exists())
                self.assertFalse((directory/(name+'.presented')).exists())

if __name__=='__main__':unittest.main()
