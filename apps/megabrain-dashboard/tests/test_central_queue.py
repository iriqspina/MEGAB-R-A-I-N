"""Shared queue liveness and cancellation with synthetic executors, no models."""
from pathlib import Path
import sys,tempfile,threading,time,unittest
from unittest.mock import patch
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from central_store import Store,now
import central_jobs as jobs


class QueueTests(unittest.TestCase):
    def setUp(self):
        base=APP.parents[1]/'evidence/261011_app-megabrain/security-fixtures';base.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='queue-',dir=base);self.root=Path(self.tmp.name);self.store=Store(self.root/'db.sqlite3')
        self.patches=[patch.object(jobs,'APP',self.root),patch.object(jobs,'QUEUE_LOCK',threading.Lock()),patch.object(jobs,'QUEUE_POLL_SECONDS',.02),patch.object(jobs,'HEARTBEAT_SECONDS',.03)]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()
    def create(self,title):
        # Direct synthetic fixture bypasses API admission to exercise a waiter.
        return self.store.add('jobs','p',dict(project_id='p',title=title,status='queued',updated_at=now()))
    def test_waiter_heartbeats_and_cross_instance_cancel_never_calls_model(self):
        first=self.create('first');second=self.create('second');entered=threading.Event();release=threading.Event();calls=[]
        def fake(store,sources,job):
            calls.append(job['id']);entered.set();release.wait(3)
            store.update_job_if_active({**job,'status':'completed'})
        with patch.object(jobs,'_execute_workflow',side_effect=fake):
            a=threading.Thread(target=jobs.execute,args=(self.store,None,first));a.start()
            self.assertTrue(entered.wait(2))
            other=Store(self.store.path);b=threading.Thread(target=jobs.execute,args=(other,None,second));b.start()
            until=time.monotonic()+2
            while time.monotonic()<until and not other.job(second['id']).get('heartbeat'):time.sleep(.02)
            self.assertTrue(other.job(second['id']).get('heartbeat'))
            other.request_cancel(second['id']);b.join(2)
            self.assertFalse(b.is_alive());self.assertEqual(other.job(second['id'])['status'],'interrupted')
            self.assertEqual(calls,[first['id']]);self.assertTrue((self.root/'data/jobs'/second['id']/'result.json').exists())
            release.set();a.join(2)
            self.assertFalse(a.is_alive())
    def test_cancel_before_lock_does_not_wait_or_call_executor(self):
        job=self.create('cancelled');Store(self.store.path).request_cancel(job['id'])
        jobs.QUEUE_LOCK.acquire()
        try:
            with patch.object(jobs,'_execute_workflow') as execute:
                jobs.execute(self.store,None,job);execute.assert_not_called()
        finally:jobs.QUEUE_LOCK.release()
        self.assertEqual(self.store.job(job['id'])['status'],'interrupted')
    def test_completed_job_does_not_run_again(self):
        job=self.create('done');self.store.update_job_if_active({**job,'status':'completed'})
        with patch.object(jobs,'_execute_workflow') as execute:
            jobs.execute(Store(self.store.path),None,job);execute.assert_not_called()


if __name__=='__main__':unittest.main()
