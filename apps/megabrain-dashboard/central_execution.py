"""Bounded per-job working copies and observed execution evidence.

This module never executes project/generated code or writes back to a project.
The model adapter must enforce its own OS sandbox. A separate directory alone
is not a sandbox. Evidence is accepted only from adapter tool_results, never
from generated PASS text or a model-created tests.json file.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shlex
import stat
from urllib.parse import urlsplit

LIMITS = {'max_files': 100, 'max_file_bytes': 1_000_000, 'max_total_bytes': 8_000_000}
ATTACHMENT_NAMESPACE = '.mb-anexos'
ATTACHMENT_LIMITS = {'max_files': 6, 'max_file_bytes': 8 * 1024 * 1024,
                     'max_total_bytes': 48 * 1024 * 1024}
ATTACHMENT_EXTENSIONS = {'image/png': '.png', 'image/jpeg': '.jpg',
                         'image/gif': '.gif', 'image/webp': '.webp'}
TEXT_EXTENSIONS = frozenset({'.py','.js','.mjs','.cjs','.ts','.tsx','.jsx','.html','.htm','.css','.scss',
    '.json','.toml','.yaml','.yml','.xml','.svg','.sql','.sh','.ps1','.cmd','.bat','.go','.rs','.java',
    '.c','.h','.cpp','.hpp','.cs','.rb','.php','.md','.txt','.csv','.ini','.cfg'})
TEXT_NAMES = frozenset({'Makefile','Dockerfile','LICENSE'})
CODE_EXTENSIONS = TEXT_EXTENSIONS - {'.md','.txt','.csv','.ini','.cfg','.json','.yaml','.yml','.toml','.xml'}
EXCLUDED_PARTS = frozenset({'node_modules','vendor','runtime-packages','__pycache__','venv','env',
    'data','credentials','secrets','auth','logs','evidence','backups','_arquivo'})
CONTROL_NAMES = frozenset({'agents.md','claude.md','gemini.md','zcode.md','auth.json','credentials.json',
    'credentials','token','token.json','secrets.json','session.json','sessions.json'})
GENERATED_PRIVATE_PARTS = frozenset({'__pycache__','node_modules','.git','.pytest_cache','.mypy_cache','.cache','.automations','evidence'})
SECRET_PATTERNS = (
    re.compile(r'\b(?:sk|sk-ant|sk-proj)-[A-Za-z0-9_-]{16,}'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'(?i)\b(?:api[_-]?key|(?:access|refresh|oauth|bearer)[_-]?token|token|(?:client|gateway|tunnel)[_-]?secret|secret[_-]?(?:key|access[_-]?key)|password|authorization)\b[\s\"\']*[:=][\s\"\']*(?:bearer\s+)?[A-Za-z0-9_./+=-]{16,}'),
)


def _now(): return datetime.now(timezone.utc).isoformat()
def _sha(data): return hashlib.sha256(data).hexdigest()
def _json(path, value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,path)


def _relative(value):
    raw=str(value)
    if not raw or '\\' in raw or ':' in raw or '\x00' in raw or PureWindowsPath(raw).is_absolute():
        raise ValueError('Use um caminho relativo simples, sem unidade ou separadores alternativos.')
    p=PurePosixPath(raw)
    if p.is_absolute() or any(part in {'','..','.'} for part in raw.split('/')):
        raise ValueError('Caminho fora da seleção permitida.')
    if any(part.startswith('.') or part.casefold() in EXCLUDED_PARTS for part in p.parts):
        raise ValueError('Pastas privadas, de dependências ou de histórico não entram na cópia.')
    if p.name.casefold() in CONTROL_NAMES or p.name.casefold().startswith(('.env','id_rsa','id_ed25519')):
        raise ValueError('Arquivo de controle ou credencial não entra na cópia.')
    if p.suffix.lower() not in TEXT_EXTENSIONS and p.name not in TEXT_NAMES:
        raise ValueError('Selecione um arquivo de texto ou código permitido.')
    return p


def _no_links(path, base):
    """Reject symlinks, junctions/reparse points and hardlinks before reading."""
    base=Path(base).absolute(); path=Path(path).absolute()
    try: relative=path.relative_to(base)
    except ValueError: raise ValueError('Arquivo fora da área permitida.') from None
    for current in [base,*[base.joinpath(*relative.parts[:i]) for i in range(1,len(relative.parts)+1)]]:
        st=current.lstat()
        if stat.S_ISLNK(st.st_mode) or getattr(st,'st_file_attributes',0)&0x400:
            raise ValueError('Links e junctions não são aceitos nesta execução.')
    if path.is_file() and path.stat().st_nlink>1: raise ValueError('Hardlinks não são aceitos nesta execução.')
    if not path.resolve().is_relative_to(base.resolve()): raise ValueError('Arquivo fora da área permitida.')


def _text_file(path):
    st=path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size>LIMITS['max_file_bytes']:
        raise ValueError('Arquivo não regular ou maior que o limite por arquivo.')
    data=path.read_bytes()
    if len(data)>LIMITS['max_file_bytes'] or b'\x00' in data: raise ValueError('Arquivo binário ou acima do limite.')
    try: text=data.decode('utf-8-sig')
    except UnicodeError: raise ValueError('O arquivo precisa ser texto UTF-8.') from None
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ValueError('Possível segredo detectado; arquivo não copiado/publicado.')
    return data


def _attachment_inputs(source, references):
    """Resolve project-owned inputs separately; selected_paths stays text-only."""
    if references is None: references=[]
    if (not isinstance(references,list) or len(references)>ATTACHMENT_LIMITS['max_files']
            or any(not isinstance(ref,str) for ref in references)):
        raise ValueError('Use até 6 caminhos canônicos de anexos do próprio projeto.')
    if not references:return [],[]
    from central_attachments import resolve_attachments,read_attachment
    from central_store import ident
    pid=ident(source.resolve()); entries=[]; contents=[]; total=0
    for resolved in resolve_attachments(source,pid,references):
        row,data=read_attachment(source,pid,resolved['id'])
        if row!=resolved or row.get('mime') not in ATTACHMENT_EXTENSIONS:
            raise ValueError('O anexo mudou durante a preparação.')
        aid=row['id']; digest=_sha(data)
        if not re.fullmatch(r'[a-f0-9]{64}',aid) or aid!=digest:
            raise ValueError('Hash do anexo não corresponde aos bytes recebidos.')
        original=Path(row['path']); _no_links(original,source)
        if not original.is_relative_to(source/ATTACHMENT_NAMESPACE):
            raise ValueError('Anexo fora da pasta de entradas do projeto.')
        total+=len(data)
        if (len(data)!=row['size'] or len(data)>ATTACHMENT_LIMITS['max_file_bytes']
                or total>ATTACHMENT_LIMITS['max_total_bytes']):
            raise ValueError('Anexos acima do limite da execução.')
        relative=ATTACHMENT_NAMESPACE+'/'+aid+ATTACHMENT_EXTENSIONS[row['mime']]
        entries.append(dict(id=aid,name=row['name'],mime=row['mime'],size=len(data),
                            sha256=digest,source_path=str(original),relative_path=relative))
        contents.append((PurePosixPath(relative),data))
    return entries,contents


def prepare_execution(project_root, job_directory, selected_paths=None, *, attachments=None):
    """Create fresh workspace. None means empty; explicit files are bounded copies."""
    source=Path(project_root).absolute(); job=Path(job_directory).absolute()
    if not source.is_dir(): raise ValueError('Projeto de origem indisponível.')
    _no_links(source,source)
    job.mkdir(parents=True,exist_ok=True); _no_links(job,job)
    workspace=job/'workspace'; baseline_path=job/'execution-baseline.json'
    if workspace.exists() or baseline_path.exists(): raise FileExistsError('Execução já preparada; preserve a tentativa anterior.')
    values=[] if selected_paths is None else selected_paths
    if not isinstance(values,(list,tuple)) or len(values)>LIMITS['max_files']:
        raise ValueError('Seleção inválida ou acima do limite de arquivos.')
    entries=[]; contents=[]; total=0; seen=set()
    # Validate the entire selection before creating/copying anything.
    for value in values:
        rel=_relative(value); key=str(rel).casefold()
        if key in seen: raise ValueError('Arquivo repetido na seleção.')
        seen.add(key); original=source.joinpath(*rel.parts)
        _no_links(original,source); data=_text_file(original); total+=len(data)
        if total>LIMITS['max_total_bytes']: raise ValueError('Seleção acima do limite total de bytes.')
        entries.append({'relative_path':str(rel),'origin':str(original),'sha256':_sha(data),'size':len(data)})
        contents.append((rel,data))
    attachment_entries,attachment_contents=_attachment_inputs(source,attachments)
    contents.extend(attachment_contents)
    workspace.mkdir()
    for rel,data in contents:
        target=workspace.joinpath(*rel.parts); target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    baseline={'schema':1,'at':_now(),'project_root':str(source),'workspace':str(workspace),'files':entries,
              'attachments':attachment_entries,'attachment_limits':dict(ATTACHMENT_LIMITS),
              'limits':dict(LIMITS),'originals_write_policy':'never','is_os_sandbox':False}
    _json(baseline_path,baseline)
    return {'workspace':str(workspace),'baseline_path':str(baseline_path),'selected_files':entries,
            'attachments':attachment_entries,'limits':dict(LIMITS),'attachment_limits':dict(ATTACHMENT_LIMITS)}


def list_source_files(project_root):
    """Read-only picker with the same file guards and explicit discovery budgets."""
    source=Path(project_root).absolute(); _no_links(source,source)
    if not source.is_dir():raise ValueError('Projeto de origem indisponível.')
    budgets={'max_listed_files':1000,'max_depth':8,'max_directories':10000,'max_entries':10000,'max_inspected_bytes':32_000_000}
    files=[]; directories=0; inspected=0; entries=0; truncated=False
    for directory,dirs,names in os.walk(source,followlinks=False):
        directories+=1
        if directories>budgets['max_directories']:truncated=True;break
        relative_dir=Path(directory).relative_to(source)
        if len(relative_dir.parts)>=budgets['max_depth']:
            if dirs:truncated=True
            dirs[:]=[]
        clean=[]
        for name in sorted(dirs):
            if name.startswith('.') or name.casefold() in EXCLUDED_PARTS:continue
            try:_no_links(Path(directory)/name,source)
            except (ValueError,OSError):continue
            clean.append(name)
        dirs[:]=clean
        for name in sorted(names):
            entries+=1
            if entries>budgets['max_entries'] or len(files)>=budgets['max_listed_files']:
                truncated=True;break
            path=Path(directory)/name; relative=path.relative_to(source).as_posix()
            try:
                _relative(relative); _no_links(path,source); size=path.stat().st_size
                if size>LIMITS['max_file_bytes']:continue
                if inspected+size>budgets['max_inspected_bytes']:truncated=True;break
                inspected+=size; data=_text_file(path)
                files.append({'path':relative,'size':len(data)})
            except (ValueError,OSError):continue
        if truncated and (entries>budgets['max_entries'] or len(files)>=budgets['max_listed_files'] or inspected>=budgets['max_inspected_bytes']):break
        if truncated and inspected+LIMITS['max_file_bytes']>budgets['max_inspected_bytes']:break
    return {'files':files,'limits':{**LIMITS,**budgets},'truncated':truncated}


def _inventory_attachment_inputs(workspace, entries):
    """Account for exact binary inputs without granting a publication exception."""
    if not isinstance(entries,list) or len(entries)>ATTACHMENT_LIMITS['max_files']:
        raise ValueError('Manifesto de anexos inválido.')
    expected={}; total=0
    for row in entries:
        if (not isinstance(row,dict) or not isinstance(row.get('id'),str)
                or not re.fullmatch(r'[a-f0-9]{64}',row['id'])
                or row.get('mime') not in ATTACHMENT_EXTENSIONS
                or type(row.get('size')) is not int or not 0<row['size']<=ATTACHMENT_LIMITS['max_file_bytes']
                or row.get('sha256')!=row['id']):
            raise ValueError('Manifesto de anexos inválido.')
        relative=ATTACHMENT_NAMESPACE+'/'+row['id']+ATTACHMENT_EXTENSIONS[row['mime']]
        if row.get('relative_path')!=relative or relative in expected:
            raise ValueError('Caminho de anexo inválido no manifesto.')
        total+=row['size'];expected[relative]=row
    if total>ATTACHMENT_LIMITS['max_total_bytes']:raise ValueError('Manifesto de anexos acima do limite.')
    if not expected:return [],[]
    blocked=[]; states=[]; folder=workspace/ATTACHMENT_NAMESPACE
    try:
        _no_links(folder,workspace)
        if not folder.is_dir():raise ValueError('Namespace de anexos substituído.')
        for index,p in enumerate(folder.iterdir()):
            if index>=ATTACHMENT_LIMITS['max_files']:
                blocked.append(dict(relative_path=ATTACHMENT_NAMESPACE,reason='input_attachment_scan_budget_exceeded'));break
            relative=p.relative_to(workspace).as_posix()
            if relative not in expected:
                blocked.append(dict(relative_path=relative,reason='unexpected_input_attachment'))
    except (ValueError,OSError):
        blocked.append(dict(relative_path=ATTACHMENT_NAMESPACE,reason='input_attachment_namespace_missing_or_unsafe'))
    for relative,row in expected.items():
        p=workspace/relative; state='missing_or_unsafe'; digest=None
        try:
            _no_links(p,workspace);info=p.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_size!=row['size']:
                state='modified'
            else:
                with p.open('rb') as source:data=source.read(row['size']+1)
                digest=_sha(data)
                state='unchanged' if len(data)==row['size'] and digest==row['sha256'] else 'modified'
        except (ValueError,OSError):pass
        states.append(dict(row,status=state,current_sha256=digest,visual_inspection_observed=False))
        if state!='unchanged':blocked.append(dict(relative_path=relative,reason='input_attachment_'+state))
    return states,blocked


def inventory_changes(job_directory):
    job=Path(job_directory).absolute(); workspace=job/'workspace'; baseline_path=job/'execution-baseline.json'
    _no_links(baseline_path,job); baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
    _no_links(workspace,job)
    if baseline.get('workspace')!=str(workspace): raise ValueError('Baseline não corresponde à execução.')
    attachment_entries=baseline.get('attachments',[])
    input_attachments,attachment_blocked=_inventory_attachment_inputs(workspace,attachment_entries)
    before={r['relative_path']:r for r in baseline['files']}; found={}; blocked=list(attachment_blocked); skipped=[]; total=0; scanned=0; stop=False
    for directory,dirs,names in os.walk(workspace,followlinks=False):
        if len(Path(directory).relative_to(workspace).parts)>12:
            blocked.append({'relative_path':Path(directory).relative_to(workspace).as_posix(),'reason':'depth_limit'});dirs[:]=[];continue
        clean=[]
        for name in sorted(dirs):
            p=Path(directory)/name; relative=p.relative_to(workspace).as_posix()
            if relative==ATTACHMENT_NAMESPACE and attachment_entries:
                # Exact registered inputs were checked above, including unexpected children.
                continue
            try:
                _no_links(p,workspace)
                if name.casefold() in GENERATED_PRIVATE_PARTS:
                    skipped.append({'relative_path':relative,'reason':'generated_technical_directory_not_published'});continue
                if name.startswith('.') or name.casefold() in EXCLUDED_PARTS: raise ValueError('Pasta excluída da publicação.')
                clean.append(name)
            except (ValueError,OSError): blocked.append({'relative_path':relative,'reason':'excluded_directory_or_link'})
        dirs[:]=clean
        for name in sorted(names):
            scanned+=1
            if scanned>2000:
                blocked.append({'relative_path':'','reason':'scan_budget_exceeded'});stop=True;break
            p=Path(directory)/name; relative=p.relative_to(workspace).as_posix()
            try:
                _relative(relative); _no_links(p,workspace)
                if len(found)>=LIMITS['max_files'] or total+p.stat().st_size>LIMITS['max_total_bytes']:
                    raise ValueError('Limite de publicação excedido.')
                data=_text_file(p)
                total+=len(data); digest=_sha(data)
                found[relative]={'path':str(p),'relative_path':relative,'sha256':digest,'size':len(data),
                    'change':'added' if relative not in before else 'unchanged' if before[relative]['sha256']==digest else 'modified'}
            except (ValueError,OSError): blocked.append({'relative_path':relative,'reason':'unsafe_or_above_limit'})
        if stop:break
    originals=[]; source=Path(baseline['project_root'])
    for relative,entry in before.items():
        try:
            original=source.joinpath(*_relative(relative).parts); _no_links(original,source)
            unchanged=_sha(_text_file(original))==entry['sha256']
        except (ValueError,OSError): unchanged=False
        originals.append({'relative_path':relative,'unchanged':unchanged})
    return {'files':list(found.values()),'removed':[p for p in before if p not in found and not (workspace/p).exists()],
            'blocked':blocked,'skipped':skipped,'originals':originals,'originals_unchanged':all(r['unchanged'] for r in originals),
            'originals_checked_count':len(originals),'originals_check_scope':'Only selected source files; OS isolation is enforced and measured separately by the model adapter.',
            'input_attachments':input_attachments,'input_attachments_unchanged':not attachment_blocked,
            'input_attachments_check_scope':'Exact staged image bytes and hashes only; not publication or visual inspection.',
            'total_bytes':total,'workspace':str(workspace),'at':_now()}


def _public_url(value):
    try:
        p=urlsplit(value)
        if p.scheme not in {'http','https'} or not p.hostname or p.username or p.password: return None
        if p.hostname.casefold() in {'localhost','localhost.localdomain'} or p.hostname.endswith(('.local','.internal')): return None
        try:
            if not ipaddress.ip_address(p.hostname).is_global:return None
        except ValueError:pass
        if re.search(r'(?i)(?:token|secret|password|api.?key|auth|session)=',p.query): return None
        return value
    except (ValueError,TypeError):return None


def _unquote(value):
    return value[1:-1] if len(value)>=2 and value[0]==value[-1] and value[0] in {'"',"'"} else value


def _direct_command(event):
    """Parse a recorded command without executing it; unwrap only fixed shells.

    This is derived evidence, never an invented effective argv. Shell operators,
    expansion, encoded commands, nested shells and unrecognised flags fail closed.
    """
    raw=event.get('command',''); argv=event.get('argv')
    supplied_argv=isinstance(argv,list) and bool(argv)
    if not supplied_argv:
        if not isinstance(raw,str):return None
        try:argv=shlex.split(raw,posix=False)
        except ValueError:return None
    if not argv or not all(isinstance(v,str) and v for v in argv):return None
    tokens=[_unquote(v) for v in argv]
    executable=PureWindowsPath(tokens[0]).name.casefold()
    method='observed_argv' if supplied_argv else 'parsed_recorded_command'
    normalization={'method':method,'derived':not supplied_argv}
    if executable in {'cmd','cmd.exe','powershell','powershell.exe','pwsh','pwsh.exe'}:
        launcher=tokens[0]
        while '\\\\' in launcher:launcher=launcher.replace('\\\\','\\')
        windows=PureWindowsPath(os.environ.get('SystemRoot','C:/Windows'))
        allowed={str(windows/'System32/cmd.exe').casefold():'cmd',
                 str(windows/'System32/WindowsPowerShell/v1.0/powershell.exe').casefold():'powershell',
                 str(PureWindowsPath('C:/Program Files/PowerShell/7/pwsh.exe')).casefold():'powershell',
                 str(PureWindowsPath(Path.home())/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe').casefold():'powershell'}
        shell=allowed.get(str(PureWindowsPath(launcher)).casefold())
        if not shell:return None
        switch='/c' if shell=='cmd' else '-command'
        inert={'/d','/s','/q'} if shell=='cmd' else {'-noprofile','-noninteractive','-nologo'}
        lower=[v.casefold() for v in tokens]
        if switch not in lower:return None
        at=lower.index(switch)
        if any(v not in inert for v in lower[1:at]) or at==len(tokens)-1:return None
        payload=' '.join(argv[at+1:])
        if len(argv[at+1:])==1:payload=_unquote(payload)
        if any(c in payload for c in (';','|','&','>','<','`','$','%','!','\r','\n')):return None
        try:tokens=[_unquote(v) for v in shlex.split(payload,posix=False)]
        except ValueError:return None
        normalization={'method':'unwrapped_fixed_shell','derived':True,'wrapper':launcher,'inner_command':payload}
    if not tokens or any(any(c in v for c in (';','|','&','>','<','`','$','%','!','\r','\n','"',"'")) for v in tokens):return None
    if PureWindowsPath(tokens[0]).name.casefold().removesuffix('.exe') in {'cmd','powershell','pwsh','bash','sh'}:return None
    return tokens,normalization


def _test_command(event):
    """Recognize direct runners, preserving the raw event and unwrapping proof."""
    parsed=_direct_command(event)
    if not parsed:return None
    tokens,normalization=parsed; executable=PureWindowsPath(tokens[0]).name.casefold().removesuffix('.exe')
    if executable in {'python','python3','py'} and '-m' in tokens:
        at=tokens.index('-m'); framework=tokens[at+1] if len(tokens)>at+1 else ''
        if any(v not in {'-B','-I','-E','-s','-S','-u','-q','-3'} for v in tokens[1:at]):return None
        if framework not in {'unittest','pytest'}:return None
    elif executable in {'pytest','pytest3'}:framework='pytest'
    elif executable=='node' and '--test' in tokens:
        if any(v in {'-e','-p','--eval','--print','-r','--require','--import'} or v.startswith(('--eval=','--print=','--require=','--import=')) for v in tokens):return None
        framework='node:test'
    elif executable in {'npm','npm.cmd'} and tokens[1:2]==['test']:framework='npm test'
    elif executable in {'npx','npx.cmd'} and tokens[1:2] in [['vitest'],['jest'],['playwright']]:framework=tokens[1]
    elif executable=='go' and tokens[1:2]==['test']:framework='go test'
    elif executable=='cargo' and tokens[1:2]==['test']:framework='cargo test'
    else:return None
    identity_tokens=list(tokens)
    if framework=='node:test':
        # These two observed native-runtime flags do not select a different suite.
        # All selection/filter/target args and cwd remain part of the identity.
        boundary=identity_tokens.index('--') if '--' in identity_tokens else len(identity_tokens)
        identity_tokens=[v for i,v in enumerate(identity_tokens) if i>=boundary or v not in {'--preserve-symlinks','--preserve-symlinks-main'}]
    identity=json.dumps([framework,str(event.get('cwd') or ''),identity_tokens],ensure_ascii=False)
    return framework,' '.join(tokens)[:1200],normalization,identity


def _readonly_command(event):
    parsed=_direct_command(event)
    if not parsed:return False
    tokens,_=parsed
    name=PureWindowsPath(tokens[0]).name.casefold()
    return name in {'ls','dir','pwd','get-location','get-childitem','get-content','cat','head','tail'}


def observed_evidence(stage_results):
    tests=[]; sources=[]; web_actions=[]
    for stage_index,result in enumerate(stage_results or []):
        if not isinstance(result,dict):continue
        for tool_index,event in enumerate(result.get('tool_results') or []):
            if not isinstance(event,dict) or not event.get('evidence_source'):continue
            raw_evidence=event['evidence_source']
            evidence=({k:raw_evidence.get(k) for k in ('path','json_event_index','vendor') if k in raw_evidence}
                      if isinstance(raw_evidence,dict) else str(raw_evidence)[:500])
            provenance={'stage_index':stage_index,'tool_index':tool_index,'evidence_source':evidence}
            if event.get('kind')=='command':
                recognized=_test_command(event)
                if not recognized:continue
                framework,command,normalization,identity=recognized; output=str(event.get('output',event.get('aggregated_output','')))
                empty=bool(re.search(r'(?:Ran\s+0\s+tests|\btests\s+0\b|\b0\s+tests?\s+(?:passed|found)|no tests (?:ran|found))',output,re.I))
                counts=re.findall(r'(?:Ran\s+(\d+)\s+tests?|\btests\s+(\d+)\b|\b(\d+)\s+passed\b)',output,re.I)
                count=max((int(n) for group in counts for n in group if n),default=0)
                go_pass=framework=='go test' and bool(re.search(r'^ok\s+\S+\s+[\d.]+s',output,re.M)) and '[no test files]' not in output
                finished=event.get('status') in {'completed','success','passed','failed'}
                passed=finished and event.get('status')!='failed' and event.get('exit_code')==0 and not empty and (count>0 or go_pass)
                tests.append(dict(provenance,framework=framework,command=event.get('command') or command,normalized_command=command,normalization=normalization,suite_identity=identity,cwd=event.get('cwd'),exit_code=event.get('exit_code'),
                    status='passed' if passed else 'failed' if finished and (event.get('status')=='failed' or event.get('exit_code') not in (None,0)) else 'not_verified',observed=True,zero_tests=empty,reported_count=count or None))
            elif event.get('kind') in {'web_search','web_fetch'}:
                web_actions.append(dict(provenance,kind=event['kind'],status=event.get('status'),urls=[v for v in event.get('urls',[]) if _public_url(v)]))
        observed_urls={url for action in web_actions if action['stage_index']==stage_index for url in action['urls']}
        for source in result.get('web_sources') or []:
            if isinstance(source,dict) and _public_url(source.get('url')) and source['url'] in observed_urls:
                sources.append({'url':source['url'],'title':str(source.get('title') or '')[:300],
                    'accessed_at':source.get('accessed_at'),'retrieved':source.get('retrieved') is True,'stage_index':stage_index,
                    'retrieval_kind':source.get('retrieval_kind'),'accessed_at_evidence':source.get('accessed_at_evidence'),
                    'evidence_source':source.get('evidence_source')})
    latest={t['suite_identity']:i for i,t in enumerate(tests)}
    for i,test in enumerate(tests):
        test['current_attempt']=latest[test['suite_identity']]==i
        if not test['current_attempt']:test['superseded_by_test_index']=latest[test['suite_identity']]
    return {'tests':tests,'sources':list({s['url']:s for s in sources}.values()),'web_actions':web_actions}


def finalize_execution(job_directory, stage_results=None, *, mode='code'):
    if mode not in {'code','research','textual','mixed'}:raise ValueError('Modo de execução inválido.')
    inventory=inventory_changes(job_directory); observed=observed_evidence(stage_results)
    artifacts=[dict(row,id=_sha(row['relative_path'].encode())[:20],kind='code' if Path(row['relative_path']).suffix.lower() in CODE_EXTENSIONS else 'document',verified=False)
               for row in inventory['files'] if row['change']!='unchanged']
    tests=observed['tests']; latest={t['suite_identity']:t for t in tests}; reasons=[];snapshot_scope={}
    if not inventory['originals_unchanged']:reasons.append('originals_changed_outside_workspace')
    if not inventory['input_attachments_unchanged']:reasons.append('input_attachments_changed_or_missing')
    if inventory['blocked']:reasons.append('blocked_files_require_review')
    if mode in {'code','mixed'}:
        if not any(a['kind']=='code' for a in artifacts):reasons.append('no_code_artifact')
        if not latest or not any(t['status']=='passed' for t in latest.values()):reasons.append('no_observed_passing_test')
        if any(t['status']!='passed' for t in latest.values()):reasons.append('test_failure_or_unverified')
        # A prior green test does not validate a later edit. Match the adapter's
        # final workspace snapshot and reject later changes/unverified commands.
        code_stages=[(i,r) for i,r in enumerate(stage_results or []) if isinstance(r,dict) and r.get('capability')=='code']
        if not code_stages:reasons.append('no_code_stage_snapshot')
        else:
            index,last_code=code_stages[-1]
            relevant=CODE_EXTENSIONS|{'.json','.toml','.yaml','.yml'}
            current={r['relative_path']:r['sha256'] for r in inventory['files'] if Path(r['relative_path']).suffix.lower() in relevant}
            snapshot=last_code.get('workspace_after',{}).get('files',[])
            previous={};excluded=[]
            for row in snapshot:
                if not isinstance(row,dict) or not row.get('path') or not row.get('sha256'):continue
                relative=row['path']
                try:_relative(relative)
                except ValueError:
                    excluded.append({'relative_path':relative,'reason':'outside_publication_inventory_scope'});continue
                if Path(relative).suffix.lower() not in relevant:
                    excluded.append({'relative_path':relative,'reason':'non_executable_document'});continue
                previous[relative]=row['sha256']
            snapshot_scope={'compared_paths':sorted(set(current)|set(previous)),'excluded_adapter_files':excluded,
                            'scope':'Same publicable code/config paths as inventory; technical directories and non-executable documents are explicitly excluded, not certified.'}
            if not previous or current!=previous:reasons.append('code_changed_after_observed_stage')
            stage_tests=[t for t in tests if t['stage_index']==index]
            events=last_code.get('tool_results') or []
            if not stage_tests or stage_tests[-1]['status']!='passed':reasons.append('last_code_stage_has_no_passing_test')
            elif any(e.get('kind')=='file_change' or (e.get('kind')=='command' and not _readonly_command(e))
                     for e in events[stage_tests[-1]['tool_index']+1:] if isinstance(e,dict)):
                reasons.append('post_test_changes_or_unverified_commands')
    if mode in {'research','mixed'}:
        if not any(a['status'] in {'completed','success','passed'} for a in observed['web_actions']):reasons.append('no_observed_live_web_action')
        if not any(s['retrieved'] and s['accessed_at'] for s in observed['sources']):reasons.append('no_retrieved_source_with_timestamp')
        fetched={(a['stage_index'],u) for a in observed['web_actions'] if a['kind']=='web_fetch' and a['status'] in {'completed','success','passed'} for u in a['urls']}
        if not any(s['retrieved'] and s['accessed_at'] and s.get('retrieval_kind')=='page_fetch' and (s['stage_index'],s['url']) in fetched for s in observed['sources']):
            reasons.append('no_observed_page_fetch')
        if not artifacts:reasons.append('no_research_artifact')
    manifest={**inventory,**observed,'schema':1,'mode':mode,'artifacts':artifacts,'snapshot_comparison':snapshot_scope,
              'verification':{'status':'passed' if not reasons else 'needs_review','reasons':reasons,
                  'claim_scope':'Observed files and tool results only; no aesthetic approval, deployment or original-project modification.'},
              'manifest_path':str(Path(job_directory).absolute()/'execution-manifest.json')}
    _json(Path(manifest['manifest_path']),manifest)
    return manifest
