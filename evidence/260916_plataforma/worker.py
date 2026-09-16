from pathlib import Path
import os, subprocess, sys, json, datetime, shutil
root=Path(__file__).resolve().parents[2]; folder=Path(__file__).resolve().parent
name=sys.argv[1]; prompt=(folder/(name+'.txt')).read_text(encoding='utf-8')
env=os.environ.copy(); env['CODEX_HOME']=r'<USER_HOME>\.codex-gpt2'; env['PYTHONUTF8']='1'
cmd=[shutil.which('codex'),'exec','-m','gpt-6-astra','-c','model_reasoning_effort="high"','-c','approval_policy="never"','--sandbox','workspace-write','--ephemeral','--color','never','-C',str(root),'-o',str(folder/(name+'-resultado.md')),'-']
with (folder/(name+'.log')).open('w',encoding='utf-8') as log:
    proc=subprocess.run(cmd,input=prompt,stdout=log,stderr=subprocess.STDOUT,text=True,encoding='utf-8',env=env,cwd=root)
(folder/(name+'-status.json')).write_text(json.dumps({'exit_code':proc.returncode,'finished_at':datetime.datetime.now().astimezone().isoformat()}),encoding='utf-8')
print(name,proc.returncode)
