"""Open a bounded Cotas destination in the existing native Brain App."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from . import paths

PROVIDERS={'all','codex','codex_gpt2','claude','zai','spark','gemini_cli','gemini_web','antigravity'}

def open_in_brain(view,provider='all'):
    if not isinstance(view,str) or not isinstance(provider,str) or view not in {'quota-settings','quota-account'} or provider not in PROVIDERS:
        raise ValueError('Destino de cotas inválido.')
    app=paths.CENTRAL_DIR/'apps/megabrain-dashboard'
    launcher=app/'bootstrap/MegaBrain.exe'
    if not launcher.is_file():
        raise ValueError('Brain App indisponível; nenhuma janela externa foi aberta.')
    queue=app/'data/open-requests';queue.mkdir(parents=True,exist_ok=True)
    ident=uuid.uuid4().hex
    target=queue/(ident+'.json');temp=target.with_suffix('.tmp')
    temp.write_text(json.dumps({'project':str(paths.CENTRAL_DIR),'view':view,'provider':provider,'at':time.time(),'id':ident}),encoding='utf-8')
    os.replace(temp,target)
    subprocess.Popen([str(launcher)],cwd=app,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return {'request_id':ident,'status':'requested','destination':'Brain App'}
