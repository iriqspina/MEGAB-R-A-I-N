#!/usr/bin/env python3
"""Read quota/account limits only. This entry never calls a generative model."""
from pathlib import Path
import json,os,sys
ROOT=Path(__file__).resolve().parents[1]
os.environ['CODEX_HOME']=str(Path.home()/'.codex')  # child only, main account
sys.path.insert(0,str(ROOT/'apps/ia-quota-widget'))
from widget_app.scheduled_refresh import run_once

def main():
    try:
        result=run_once()
        if sys.stdout:print(json.dumps({'status':result['status'],'run_id':result['run_id'],'finished_at':result['finished_at'],'providers':{k:v['status'] for k,v in result['providers'].items()},'model_calls':0}))
        return 0 if result['status']=='complete' else 2
    except Exception as exc:
        # No exception body: HTTP/CLI exceptions can carry account credentials.
        if sys.stderr:print('Quota collection failed: '+type(exc).__name__,file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
