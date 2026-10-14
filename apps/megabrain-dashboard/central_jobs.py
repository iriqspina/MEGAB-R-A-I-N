"""Shared in-process admission queue for the local and remote API instances.

SQLite still owns cross-process job admission and cancellation. Waiting on this
lock does not stop heartbeats or require a model call to cancel a queued job.
"""
import json
import threading
import time
from central_store import APP,now
from central_workflows import execute as _execute_workflow, cancel

QUEUE_LOCK=threading.Lock()
QUEUE_POLL_SECONDS=.5
HEARTBEAT_SECONDS=20


def _cancel_waiting(store,job):
    job.update(status='interrupted',stage='Interrompida na fila',error='Pedido interrompido antes de iniciar qualquer modelo.',updated_at=now())
    if store.update_job_if_active(job):
        store.event(job['project_id'],'Pedido interrompido na fila: '+job['title'],'session_interrupted',job_id=job['id'])
        directory=APP/'data/jobs'/job['id'];directory.mkdir(parents=True,exist_ok=True)
        (directory/'result.json').write_text(json.dumps(store.job(job['id']),ensure_ascii=False,indent=2),encoding='utf-8')


def execute(store,sources,job):
    last_heartbeat=0
    while True:
        current=store.job(job['id'])
        if current['status'] not in {'queued','running'}:return
        if current.get('cancel_requested'):
            _cancel_waiting(store,current);return
        if time.monotonic()-last_heartbeat>=HEARTBEAT_SECONDS:
            store.heartbeat(job['id']);last_heartbeat=time.monotonic()
        if not QUEUE_LOCK.acquire(timeout=QUEUE_POLL_SECONDS):continue
        try:
            # Re-read after acquisition to close cancellation/completion races.
            current=store.job(job['id'])
            if current['status'] not in {'queued','running'}:return
            if current.get('cancel_requested'):
                _cancel_waiting(store,current);return
            return _execute_workflow(store,sources,current)
        finally:QUEUE_LOCK.release()
