"""Present a project/report in the existing native MegaBrain window; no browser fallback."""
from __future__ import annotations
import argparse,json,os,subprocess,time,uuid
from pathlib import Path

CENTRAL=Path(__file__).resolve().parents[1]
APP=CENTRAL/'apps/megabrain-dashboard'

def enqueue(path=None,project=None):
    request={}
    if path is not None:
        target=Path(path).resolve(strict=True)
        if not target.is_file():raise ValueError('Entrega não é um arquivo.')
        request['path']=str(target)
    elif project is not None:
        target=Path(project).resolve(strict=True)
        if not target.is_dir():raise ValueError('Projeto indisponível.')
        request['project']=str(target)
    else:request['project']=str(CENTRAL)
    # Only project paths; tokens and authentication are never in the queue.
    request.update(at=time.time(),id=uuid.uuid4().hex)
    queue=APP/'data/open-requests';queue.mkdir(parents=True,exist_ok=True)
    destination=queue/(request['id']+'.json');temporary=destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8');os.replace(temporary,destination)
    return destination,request

def main(argv=None):
    parser=argparse.ArgumentParser(description='Abrir entrega no aplicativo MegaBrain')
    parser.add_argument('path',nargs='?');parser.add_argument('--project');parser.add_argument('--queue-only',action='store_true');parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    launcher=APP/'bootstrap/MegaBrain.exe'
    if not launcher.is_file() and not args.queue_only:raise SystemExit('Lançador nativo indisponível; nenhum navegador foi aberto.')
    dest,request=enqueue(args.path,args.project)
    if not args.queue_only:subprocess.Popen([str(launcher)],cwd=APP,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if args.json:print(json.dumps(dict(destination='MegaBrain',request_id=request['id'],queued=str(dest),opened=False),ensure_ascii=False))
    else:print('Pedido enviado ao aplicativo MegaBrain. Abertura será confirmada pelo aplicativo; nenhum navegador foi iniciado.')
    return 0

if __name__=='__main__':raise SystemExit(main())
