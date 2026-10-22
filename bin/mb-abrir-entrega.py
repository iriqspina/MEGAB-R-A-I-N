"""Present a project/report in the existing native MegaBrain window; no browser fallback."""
from __future__ import annotations
import argparse,importlib.util,json,os,subprocess,sys,time,uuid
from pathlib import Path

CENTRAL=Path(__file__).resolve().parents[1]
APP=CENTRAL/'apps/megabrain-dashboard'

def report_policy(target,preview=False):
    """Enforce registered final reports; preserve unaudited legacy access.

    This protects this canonical command only. The app's direct file opening
    is not covered, and queuing a request never proves native presentation.
    """
    if target.suffix.lower() not in {'.html','.htm'}:return None
    helper=CENTRAL/'bin/mb-auditar-relatorios-glm.py'
    if not helper.is_file():raise ValueError('Monitor GLM indisponível; relatório não foi enfileirado.')
    spec=importlib.util.spec_from_file_location('mb_report_open_audit',helper)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    result=module.audit_report(target)
    if result.get('blocked') and not preview:
        raise ValueError('Relatório bloqueado pelo gate GLM: '+result.get('reason','prova incompleta'))
    if preview:result={**result,'gate_status':result['status'],'status':'CANDIDATO_PREVIA','presentation_mode':'candidate-preview','delivery':False}
    return result

def enqueue(path=None,project=None,preview=False):
    request={}
    if path is not None:
        target=Path(path).resolve(strict=True)
        if not target.is_file():raise ValueError('Entrega não é um arquivo.')
        policy=report_policy(target,preview=preview)
        if policy is not None:request['report_policy']=policy
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
    parser.add_argument('--preview',action='store_true',help='Inspeção explícita de candidato; não é entrega e não limpa pendências')
    args=parser.parse_args(argv)
    launcher=APP/'bootstrap/MegaBrain.exe'
    if not launcher.is_file() and not args.queue_only:raise SystemExit('Lançador nativo indisponível; nenhum navegador foi aberto.')
    try:dest,request=enqueue(args.path,args.project,preview=args.preview)
    except ValueError as exc:parser.exit(2,str(exc)+'\n')
    policy=request.get('report_policy')
    if policy and policy['status']!='CONFORME':
        print('NÃO VERIFICADO · '+policy['status']+': '+policy['reason']+'. Conformidade não comprovada; acesso preservado.',file=sys.stderr)
    if args.preview:print('PRÉVIA DE CANDIDATO · Esta abertura não entrega nem aprova o relatório; pendências preservadas.',file=sys.stderr)
    if not args.queue_only:subprocess.Popen([str(launcher)],cwd=APP,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if args.json:print(json.dumps(dict(destination='MegaBrain',request_id=request['id'],queued=str(dest),opened=False,report_policy=policy),ensure_ascii=False))
    else:print('Pedido enviado ao aplicativo MegaBrain. Abertura será confirmada pelo aplicativo; nenhum navegador foi iniciado.')
    return 0

if __name__=='__main__':raise SystemExit(main())
