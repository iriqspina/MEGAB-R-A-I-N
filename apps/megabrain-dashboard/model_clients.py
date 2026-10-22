"""Bounded subscription clients with explicit textual/research/code capabilities.

The default remains analysis-only. Research exposes only Claude web tools. Code
uses the selected Codex account in a staged workspace, with a native sandbox preflight,
no network or escalation, and no writeback to source projects. ZCode remains a
tool-free main/max reviewer. Never change global accounts/config or retry models.
"""
from __future__ import annotations

import datetime as dt
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit

HOME = Path.home()
CLAUDE = HOME / '.local/bin/claude.exe'
CODEX = HOME / 'AppData/Local/Programs/OpenAI/Codex/bin/codex.exe'
ZCODE = HOME / 'AppData/Local/Programs/ZCode/resources/glm/zcode.cjs'
ZCODE_SHA256 = 'e9f1868c0fdb863537ed910ee3828b9be96b8c2fd805473f63b439e1113266b8'
ZCODE_CONFIG = HOME / '.zcode/cli/config.json'
DENY_TOOLS = ('Read','Write','Edit','ApplyPatch','Bash','Glob','Grep','WebFetch',
              'WebSearch','web_search','TodoRead','TodoWrite','GoalRead',
              'ReadSessionContext','AskUserQuestion','SendMessage',
              'RespondToCoordinator','TaskOutput','TaskStop','KillShell','KillBash',
              'js','js_reset','js_add_node_module_dir','Agent','Task','Skill',
              'EnterPlanMode','ExitPlanMode','Workflow','CronCreate','CronList',
              'CronUpdate','CronDelete','TaskCreate','TaskUpdate','TaskGet','TaskList')
EFFORTS = {'low','medium','high','xhigh','max','ultra'}
ROOT = Path(__file__).resolve().parents[2]
CAPABILITIES = {'textual':{'codex','claude','glm'}, 'research':{'claude'}, 'code':{'codex'}}
CONTROL_FILES = {'.git','.codex','.claude','agents.md','claude.md'}
NODE_OPTIONS = '--preserve-symlinks --preserve-symlinks-main'
IMAGE_LIMITS = {'max_files':6, 'max_file_bytes':8*1024*1024, 'max_total_bytes':48*1024*1024}


class ImageTransportUnavailable(ValueError):
    pass


def _image_inputs(run: Path, image_paths: list[str | Path] | None) -> tuple[list[dict[str,Any]],list[bytes]]:
    """Only prepared inputs belonging to the stage's sibling job workspace.

    The HTTP layer must resolve attachment IDs and prepare the job first. This
    private adapter boundary never accepts project/browser paths as authority.
    """
    if image_paths is None: return [],[]
    if not isinstance(image_paths,list) or len(image_paths)>IMAGE_LIMITS['max_files']:
        raise ValueError('image_paths deve ser uma lista com até 6 imagens preparadas.')
    if not image_paths:return [],[]
    if not run.is_relative_to(ROOT):raise ValueError('Imagens exigem logdir de etapa dentro do MegaBrain.')
    folder=run.parent/'workspace'/'.mb-anexos'
    _no_links(folder)
    if not folder.is_dir():raise ValueError('Pasta de anexos do próprio job não preparada.')
    rows=[]; contents=[]; seen=set(); total=0
    from central_attachments import validate_image  # leaf module; no model-client dependency
    for value in image_paths:
        if not isinstance(value,(str,Path)):
            raise ValueError('Cada imagem deve ter um caminho absoluto canônico.')
        path=Path(value)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('Cada imagem deve ter um caminho absoluto canônico.')
        _no_links(path)
        resolved=path.resolve(strict=True)
        if path!=resolved or not resolved.is_relative_to(folder) or resolved in seen:
            raise ValueError('Imagem repetida, não canônica ou fora dos anexos do próprio job.')
        info=path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or not 0<info.st_size<=IMAGE_LIMITS['max_file_bytes']:
            raise ValueError('Imagem deve ser arquivo regular sem hardlinks e ter até 8 MiB.')
        total+=info.st_size
        if total>IMAGE_LIMITS['max_total_bytes']:raise ValueError('Imagens excedem o total de 48 MiB.')
        with path.open('rb') as stream:
            opened=os.fstat(stream.fileno())
            if (opened.st_dev,opened.st_ino,opened.st_nlink)!=(info.st_dev,info.st_ino,1):
                raise ValueError('Imagem mudou durante a leitura.')
            data=stream.read(IMAGE_LIMITS['max_file_bytes']+1)
            after=os.fstat(stream.fileno())
        _no_links(path)
        current=path.stat()
        # On native Windows, path stat and fstat can expose different legacy
        # ctime values (creation/change time). Identity, size, mtime and link
        # count are comparable across both APIs.
        signature=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_nlink)
        if len(data)!=info.st_size or signature(info)!=signature(after) or signature(after)!=signature(current):
            raise ValueError('Imagem mudou durante a leitura.')
        mime,_=validate_image(data)
        digest=hashlib.sha256(data).hexdigest()
        rows.append({'id':digest,'path':str(resolved),'mime':mime,'size':len(data),'sha256':digest,
                     'transported':False,'state':'validated','visual_inspection_observed':False})
        contents.append(data);seen.add(resolved)
    return rows,contents


def _image_cli_support(model: str, timeout: float) -> dict[str,Any]:
    """A local --help probe, never an inference/capability request to a model."""
    if model=='glm':
        if _sha(ZCODE)!=ZCODE_SHA256:
            raise ImageTransportUnavailable('ZCode mudou; capacidade visual exige nova revisão do executável.')
        node=shutil.which('node')
        if not node:raise ImageTransportUnavailable('Node indisponível para verificar o ZCode real.')
        args=[node,str(ZCODE),'--help'];flags=['--attach']
    else:
        args=[str(CODEX),'exec','--help'] if model=='codex' else [str(CLAUDE),'--help']
        flags=['--image'] if model=='codex' else ['--input-format','stream-json','--output-format']
    check=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',
        timeout=min(15,max(.001,timeout)),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    help_text=check.stdout+check.stderr
    if check.returncode or any(flag not in help_text for flag in flags):
        raise ImageTransportUnavailable('Cliente instalado não confirma entrada visual nesta configuração.')
    if model=='glm':
        # The pinned official bundle's GLM-5.3 catalog declares text-only input.
        # --attach alone does not prove pixels reach that model. Tools stay off;
        # do not silently route to a vision model/MCP or send metadata as success.
        raise ImageTransportUnavailable('ZCode aceita --attach, mas GLM-5.3 main/max é somente texto no catálogo verificado; sem troca de modelo ou ferramentas visuais.')
    return {'mechanism':'codex_exec_image' if model=='codex' else 'claude_stream_json_image',
            'capability_evidence':'installed CLI --help; Claude multimodal schema: official Agent SDK streaming-input documentation',
            'help_exit_code':check.returncode,'help_sha256':hashlib.sha256(help_text.encode()).hexdigest(),
            'scope':'native_cli_input_only; no provider receipt or perception proof'}


def _code_runtime(env: dict[str,str]) -> dict[str,Any]:
    """Use native Windows runtimes via a child-only, explicit PATH.

    Codex's Windows shell discovery prefers pwsh on PATH, then its standard
    installation, then Windows PowerShell. Do not inherit the desktop's bundled
    pwsh directory: it is outside this job's readable filesystem. No permission
    is broadened to accommodate runtime discovery or Node realpath traversal.
    """
    if os.name!='nt':raise ValueError('Code runtime requires native Windows')
    system=Path(os.environ.get('SystemRoot',r'C:\Windows'))
    shell=system/'System32/WindowsPowerShell/v1.0/powershell.exe'
    node=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'nodejs/node.exe'
    fallback=Path(os.environ.get('ProgramFiles',r'C:\Program Files'))/'PowerShell/7/pwsh.exe'
    if fallback.exists():
        raise ValueError('A new PowerShell discovery fallback exists; review and canary it before enabling code')
    for executable in (shell,node):
        _no_links(executable)
        if not executable.is_file():raise ValueError('Required native runtime unavailable: '+str(executable))
    runtime_path=os.pathsep.join(map(str,(shell.parent,system/'System32',system,node.parent)))
    for key in list(env):
        if key.upper() in {'PATH','NODE_OPTIONS','NODE_PATH'}:env.pop(key,None)
    env.update(PATH=runtime_path,NODE_OPTIONS=NODE_OPTIONS)
    return {'shell_path':str(shell),'node_path':str(node),'path':runtime_path,
        'shell_sha256':_sha(shell),'node_sha256':_sha(node),'node_options':NODE_OPTIONS,
        'scope':'child process only; fixed PATH and Node options; no additional filesystem access',
        'shell_selection_evidence':'Codex shell discovery source plus fixed PATH; actual tool command remains authoritative'}


def _code_runtime_args(env: dict[str,str]) -> list[str]:
    settings='shell_environment_policy.set={PATH='+json.dumps(env['PATH'])+', NODE_OPTIONS='+json.dumps(NODE_OPTIONS)+'}'
    values=['shell_environment_policy.inherit="core"',
        'shell_environment_policy.experimental_use_profile=false','allow_login_shell=false',
        'features.shell_snapshot=false',settings]
    return [part for value in values for part in ('-c',value)]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _no_links(path: Path) -> None:
    """Check lexical ancestors before resolve() can hide a junction/symlink."""
    for current in (path.absolute(), *path.absolute().parents):
        if current.exists() or current.is_symlink():
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0) & 1024:
                raise ValueError('Symlink/reparse point is not an execution boundary: '+str(current))


def _workspace(run: Path, execution_dir: str | Path | None) -> Path:
    if execution_dir is None:
        raise ValueError('code requires an explicit execution_dir')
    requested = Path(execution_dir).absolute()
    _no_links(requested)
    work = requested.resolve()
    if not run.is_relative_to(ROOT) or work not in {run/'workspace',run.parent/'workspace'}:
        raise ValueError('execution_dir must be this job\'s workspace, beside or inside the stage logdir')
    work.mkdir(parents=True,exist_ok=True)
    return work


def _manifest(work: Path) -> dict[str, Any]:
    """Bounded inventory. Reject links, hardlinks and client control files."""
    rows=[]; total=0
    def walk_error(exc: OSError) -> None: raise exc
    for directory, dirs, files in os.walk(work,followlinks=False,onerror=walk_error):
        for name in dirs+files:
            p=Path(directory)/name
            _no_links(p)
            if name.lower() in CONTROL_FILES:
                raise ValueError('Client control file is forbidden in staged workspace: '+name)
        for name in files:
            p=Path(directory)/name; info=p.stat()
            if info.st_nlink>1: raise ValueError('Hardlinked input is not isolated: '+str(p))
            total+=info.st_size
            if len(rows)>=2000 or total>100_000_000:
                raise ValueError('Workspace inventory exceeds 2000 files or 100 MB')
            rows.append({'path':p.relative_to(work).as_posix(),'bytes':info.st_size,'sha256':_sha(p)})
    return {'files':sorted(rows,key=lambda r:r['path']),'bytes':total}


def _code_permissions() -> list[str]:
    # Explicit named profile: no inherited broad-read permission or temp writes.
    # Supply the entire profile as one TOML value: dotted CLI key parsing does
    # not preserve a quoted dot key under :workspace_roots on this installed CLI.
    denied_homes=', '.join(json.dumps((HOME/name).as_posix())+'="deny"'
                          for name in ('.codex','.codex-gpt2','.claude','.zcode','.ssh'))
    values=['default_permissions="mb_run"',
        'permissions.mb_run={extends=":workspace", filesystem={":root"="deny", ":minimal"="read", ":workspace_roots"={"."="write"}, ":tmpdir"="deny", ":slash_tmp"="deny", '+denied_homes+'}, network={enabled=false}}',
        'windows.sandbox="mxc"',
        'features.prefer_mxc=false','approval_policy="never"']
    return [part for value in values for part in ('-c',value)]


def _sandbox_preflight(work: Path, run: Path, env: dict[str,str], timeout: float) -> dict[str,Any]:
    """Run a fixed local probe through Codex's sandbox; no model/inference.

    Own canaries prove positive workspace access, denied sibling read/write and
    denied loopback TCP. An explicit MXC selection cannot fall back to a weaker
    implementation. This checks the tested routes, not every possible exploit.
    """
    if os.name!='nt': raise ValueError('code isolation has only been configured for native Windows MXC')
    started=time.monotonic()
    runtime=_code_runtime(env)
    outside=run/'sandbox-read-canary.txt'
    outside.write_text('MEGABRAIN_SANDBOX_CANARY',encoding='utf-8')
    forbidden=run/'sandbox-write-must-not-exist.txt'
    if forbidden.exists(): raise ValueError('Sandbox probe evidence already exists')
    quote=lambda p:str(p).replace("'","''")
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); listener.listen(1)
        port=listener.getsockname()[1]
        script=f"""$ErrorActionPreference='Stop'
$r=@{{inside_write=$false;outside_read_denied=$false;outside_write_denied=$false;network_denied=$false}}
$p=Join-Path (Get-Location) '.mb-sandbox-probe'
try {{[IO.File]::WriteAllText($p,'probe');$r.inside_write=([IO.File]::ReadAllText($p)-eq 'probe');[IO.File]::Delete($p)}} catch {{}}
try {{[IO.File]::ReadAllText('{quote(outside)}')|Out-Null}} catch {{$r.outside_read_denied=$true}}
try {{[IO.File]::WriteAllText('{quote(forbidden)}','SANDBOX_FAILURE')}} catch {{$r.outside_write_denied=$true}}
$c=New-Object Net.Sockets.TcpClient
try {{$t=$c.ConnectAsync('127.0.0.1',{port});if(-not $t.Wait(1200)){{$r.network_denied=$true}}else{{$r.network_denied=-not $c.Connected}}}} catch {{$r.network_denied=$true}} finally {{$c.Dispose()}}
$r|ConvertTo-Json -Compress
if($r.Values -contains $false){{exit 31}}
"""
        cmd=[str(CODEX),*_code_permissions(),*_code_runtime_args(env),'sandbox','--include-managed-config',
            '--permission-profile','mb_run','--cd',str(work),'--',runtime['shell_path'],
            '-NoProfile','-NonInteractive','-EncodedCommand',base64.b64encode(script.encode('utf-16-le')).decode()]
        result=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=min(30,max(.001,timeout)),
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try: checks=json.loads(result.stdout.strip())
    except ValueError: checks={}
    expected={'inside_write','outside_read_denied','outside_write_denied','network_denied'}
    passed=result.returncode==0 and set(checks)==expected and all(v is True for v in checks.values()) and not forbidden.exists()
    evidence={'passed':passed,'implementation':'mxc (explicit, no fallback)','model_called':False,
        'client_path':str(CODEX),'client_sha256':_sha(CODEX),'policy_arguments':_code_permissions(),
        'runtime':runtime,'runtime_arguments':_code_runtime_args(env),
        'checked_at':_utc(),'checks':checks,'exit_code':result.returncode,
        'stdout':result.stdout[-4000:],'stderr':result.stderr[-4000:],
        'scope':'Controlled local canaries only; not an exhaustive security audit'}
    _json(run/'sandbox-preflight.json',evidence,[])
    if not passed: raise ValueError('Native sandbox isolation was not proven; inference cancelled. See sandbox-preflight.json')
    # A model-free real Node test file exercises main/module loading, child test
    # discovery, file writes, sibling read denial and network denial on this drive.
    # These are adapter-authored canaries, never model-generated project tests.
    probe=work/'.mb-runtime-canary.test.cjs'
    if probe.exists():raise ValueError('Runtime canary path already exists')
    node_script="""const test=require('node:test');const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');const net=require('node:net');
test('native runtime can read and write its workspace',()=>{const p=path.join(__dirname,'.mb-node-canary');try{fs.writeFileSync(p,'probe');assert.equal(fs.readFileSync(p,'utf8'),'probe')}finally{if(fs.existsSync(p))fs.unlinkSync(p)}});
test('native runtime cannot read sibling evidence',()=>{assert.throws(()=>fs.readFileSync(OUTSIDE,'utf8'),{code:/EACCES|EPERM/})});
test('native runtime cannot write sibling evidence',()=>{assert.throws(()=>fs.writeFileSync(FORBIDDEN,'failure'),{code:/EACCES|EPERM/})});
test('native runtime cannot connect to local listener',()=>new Promise((resolve,reject)=>{const s=net.connect(PORT,'127.0.0.1');s.once('connect',()=>{s.destroy();reject(new Error('network unexpectedly available'))});s.once('error',()=>{s.destroy();resolve()});s.setTimeout(1200,()=>{s.destroy();resolve()})}));
"""
    with socket.socket() as node_listener:
        node_listener.bind(('127.0.0.1',0));node_listener.listen(1)
        node_script=node_script.replace('OUTSIDE',json.dumps(str(outside))).replace('FORBIDDEN',json.dumps(str(forbidden))).replace('PORT',str(node_listener.getsockname()[1]))
        probe.write_text(node_script,encoding='utf-8')
        # Invoke the same selected PowerShell and the normal node --test route.
        # NODE_OPTIONS is explicit in both native canary env and model tool policy.
        node_command="& '"+str(runtime['node_path']).replace("'","''")+"' --test --test-reporter=tap .mb-runtime-canary.test.cjs; exit $LASTEXITCODE"
        node_args=[str(CODEX),*_code_permissions(),*_code_runtime_args(env),'sandbox','--include-managed-config',
            '--permission-profile','mb_run','--cd',str(work),'--',runtime['shell_path'],
            '-NoProfile','-NonInteractive','-Command',node_command]
        try:
            node_result=subprocess.run(node_args,cwd=work,env=env,capture_output=True,text=True,
                encoding='utf-8',errors='replace',timeout=min(30,max(.001,timeout-(time.monotonic()-started))),
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            node_passed=(node_result.returncode==0 and bool(re.search(r'(?m)^# tests 4\s*$',node_result.stdout))
                and bool(re.search(r'(?m)^# pass 4\s*$',node_result.stdout))
                and bool(re.search(r'(?m)^# fail 0\s*$',node_result.stdout)) and not forbidden.exists())
            evidence['runtime_canary']={'passed':node_passed,'model_called':False,
                'script_sha256':_sha(probe),'command_arguments':node_args,'exit_code':node_result.returncode,
                'stdout':node_result.stdout[-10000:],'stderr':node_result.stderr[-4000:]}
            evidence['passed']=node_passed
        except Exception as exc:
            evidence['passed']=False;evidence['runtime_canary']={'passed':False,'error':str(exc)}
        finally:
            # Remove only the adapter's exact canary; never model files.
            probe.unlink(missing_ok=True)
            _json(run/'sandbox-preflight.json',evidence,[])
    if not evidence['passed']:raise ValueError('PowerShell/Node runtime canary failed; inference cancelled. See sandbox-preflight.json')
    return evidence


def _kill_owned(proc: subprocess.Popen, tree: bool) -> None:
    if tree and os.name=='nt' and proc.poll() is None:
        # The PID is from this invocation, never discovered by process name.
        subprocess.run(['taskkill.exe','/PID',str(proc.pid),'/T','/F'],capture_output=True,
            timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if proc.poll() is None: proc.kill()


def _communicate(proc: subprocess.Popen, prompt: str | None, timeout: float,
                 cancel_event: Any, tree: bool) -> tuple[str,str,str | None]:
    end=time.monotonic()+timeout
    first=True
    while True:
        cancelled=cancel_event is not None and cancel_event.is_set()
        remaining=end-time.monotonic()
        if cancelled or remaining<=0:
            _kill_owned(proc,tree)
            stdout,stderr=proc.communicate(timeout=10)
            return stdout,stderr,'cancelled' if cancelled else 'timeout'
        try:
            out,err=proc.communicate(prompt if first else None,timeout=min(.25,remaining))
            return out,err,None
        except subprocess.TimeoutExpired:
            first=False


def _events(stdout: str) -> list[dict[str,Any]]:
    rows=[]
    for line in stdout.splitlines():
        try:
            row=json.loads(line)
            if isinstance(row,dict):rows.append(row)
        except ValueError: pass
    return rows


def _rate_limit_failure(stdout: str, stderr: str) -> bool:
    """Inspect errors, not healthy quota telemetry or generated answer prose."""
    records=_events(stdout)
    try:
        whole=json.loads(stdout)
        if isinstance(whole,dict):records.append(whole)
    except ValueError:pass
    messages=[stderr]
    for row in records:
        if row.get('type')=='rate_limit_event':
            # overageStatus may be rejected while normal subscription use is
            # allowed. Only the main status establishes a rejected request.
            if row.get('rate_limit_info',{}).get('status')=='rejected':return True
            continue
        if row.get('type') in {'error','turn.failed'} or row.get('is_error') is True:
            messages.append(json.dumps(row,ensure_ascii=False))
    return bool(re.search(r'(?i)(?:HTTP|status|status_code|code)\D{0,8}429\b|rate[_ -]?limit[_ -]?error|rate[ -]limit(?:ed)?\s+(?:exceeded|reached|exhausted)|hit your[^\n]{0,100}limit','\n'.join(messages)))


def _web_urls(value: Any) -> list[str]:
    """Only structured URL fields from tool events; never model prose."""
    urls=[]
    if isinstance(value,dict):
        for key,v in value.items():
            if key in {'url','href','link'} and isinstance(v,str) and urlsplit(v).scheme in {'http','https'}:urls.append(v)
            elif isinstance(v,(dict,list)) or (key=='text' and isinstance(v,str)):urls.extend(_web_urls(v))
    elif isinstance(value,list):
        for v in value:urls.extend(_web_urls(v))
    elif isinstance(value,str):
        # Built-in web tools sometimes embed structured Links JSON in a text
        # result. Decode JSON objects/arrays only, never harvest prose URLs.
        decoder=json.JSONDecoder()
        for match in re.finditer(r'[\[{]',value):
            try: decoded,_=decoder.raw_decode(value[match.start():])
            except ValueError:continue
            urls.extend(_web_urls(decoded))
    return sorted(set(urls))


def _tool_evidence(events: list[dict[str,Any]], model: str, work: Path, source: Path) -> tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    results=[]; calls={}; sources=[]
    for line,row in enumerate(events,1):
        provenance={'path':str(source),'json_event_index':line,'vendor':model}
        if model=='codex' and row.get('type') in {'item.completed','item.started','item.updated'}:
            item=row.get('item',{}); kind=item.get('type')
            if kind not in {'command_execution','file_change','mcp_tool_call','web_search','collab_tool_call'}:continue
            normalized={'kind':{'command_execution':'command','file_change':'file_change'}.get(kind,kind),
                'name':kind,'id':item.get('id'),'status':item.get('status','completed' if row['type']=='item.completed' else 'started'),
                'cwd':str(work),'cwd_evidence':'adapter launch cwd; a command may change its own cwd',
                'evidence_source':provenance}
            for key in ('command','exit_code','aggregated_output','changes'):
                if key in item:normalized[key]=item[key]
            if isinstance(item.get('cwd'),str):
                normalized['cwd']=item['cwd'];normalized['cwd_evidence']='harness event'
            if isinstance(item.get('argv'),list):normalized['argv']=item['argv']
            # Completed replaces started for the same item while preserving the actual event reference.
            prior=next((i for i,v in enumerate(results) if item.get('id') and v.get('id')==item['id']),None)
            if prior is None:results.append(normalized)
            else:results[prior]=normalized
        elif model=='claude':
            message=row.get('message',{})
            for block in message.get('content',[]) if isinstance(message,dict) else []:
                if block.get('type') in {'tool_use','server_tool_use'}:
                    name=block.get('name','unknown'); identifier=block.get('id')
                    tool_input=block.get('input',{})
                    fetch_url=tool_input.get('url') if isinstance(tool_input,dict) else None
                    requested_urls=([fetch_url] if isinstance(fetch_url,str) and urlsplit(fetch_url).scheme in {'http','https'} else [])
                    normalized={'kind':{'WebSearch':'web_search','WebFetch':'web_fetch'}.get(name,'other'),
                        'name':name,'id':identifier,'status':'requested','input':tool_input,
                        'urls':requested_urls if name=='WebFetch' else _web_urls(tool_input),
                        'requested_urls':requested_urls if name=='WebFetch' else [],'evidence_source':provenance}
                    results.append(normalized); calls[identifier]=normalized
                elif block.get('type') in {'tool_result','web_search_tool_result','web_fetch_tool_result'}:
                    result=calls.get(block.get('tool_use_id'))
                    if result is None:continue
                    result['status']='failed' if block.get('is_error') else 'completed'
                    result['result_evidence_source']=provenance
                    content=block.get('content',[])
                    urls=_web_urls(content)
                    # Claude WebSearch can return a serialized result payload, not a JSON object.
                    for part in content if isinstance(content,list) else []:
                        if isinstance(part,dict) and part.get('type')=='text':
                            try:urls.extend(_web_urls(json.loads(part.get('text',''))))
                            except ValueError:pass
                    result['urls']=sorted(set(result['urls']+urls))
                    is_fetch=result['kind']=='web_fetch'
                    # The body can cite arbitrary URLs, including fields named
                    # "url" or "final_url". Only the actual WebFetch input URL
                    # proves a fetch target with the currently inspected event
                    # schema. Do not infer redirect destinations from page text.
                    targets=set(result.get('requested_urls',[])) if is_fetch else set(result['urls'])
                    result['retrieved_urls']=sorted(targets) if result['status']=='completed' else []
                    result['cited_urls']=sorted(set(result['urls'])-targets) if is_fetch else []
                    observed_at=_utc()
                    for url in result['urls']:
                        retrieved=result['status']=='completed' and url in targets
                        sources.append({'url':url,'observed_at':observed_at,
                            'accessed_at':observed_at if retrieved else None,
                            'accessed_at_evidence':'adapter observed successful target tool result; provider may serve cached data' if retrieved else 'not proven retrieved',
                            'retrieved':retrieved,'kind':result['kind'],
                            'retrieval_kind':('page_fetch' if url in targets else 'cited_link') if is_fetch else 'search_result',
                            'evidence_source':provenance})
    return results,sources


def _verify_auth(model: str, env: dict[str, str], timeout: float) -> dict[str, Any]:
    """Local credential metadata only. Does not query usage/quota endpoints."""
    cmd = [str(CLAUDE),'auth','status'] if model=='claude' else [str(CODEX),'login','status']
    check = subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8',
        errors='replace',timeout=min(15,max(.001,timeout)),
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if model=='claude':
        try: value=json.loads(check.stdout)
        except ValueError: value={}
        if check.returncode or value.get('authMethod')!='claude.ai' or not value.get('loggedIn'):
            raise ValueError('Claude subscription login not confirmed; no inference was sent.')
        return {'authMethod':value['authMethod'],'subscriptionType':value.get('subscriptionType'),'local_check':True}
    if check.returncode or 'logged in using chatgpt' not in (check.stdout+check.stderr).lower():
        raise ValueError('Selected Codex account ChatGPT login not confirmed; no inference was sent.')
    account_home=Path(env.get('CODEX_HOME',str(HOME/'.codex'))).resolve()
    account='primary' if account_home==(HOME/'.codex').resolve() else 'secondary' if account_home==(HOME/'.codex-gpt2').resolve() else 'unrecognized'
    if account=='unrecognized':raise ValueError('Unrecognized Codex account home')
    account_id=None
    try:
        auth=json.loads((account_home/'auth.json').read_text(encoding='utf-8'))
        account_id=auth.get('tokens',{}).get('account_id') or auth.get('account_id')
    except (OSError,ValueError,AttributeError):pass
    return {'authMethod':'ChatGPT','account':account,'codex_home':str(account_home),
            'account_id':account_id,'account_id_evidence':'local auth.json allowlisted account_id only' if account_id else 'not available',
            'scope':'CODEX_HOME set in child environment only','local_check':True}


def _redact(value: str, secrets: list[str]) -> str:
    for secret in sorted(set(secrets), key=len, reverse=True):
        if len(secret) >= 8:
            value = value.replace(secret, '[REDACTED]')
    value = re.sub(r'(?i)(bearer\s+)[\w.\-]{12,}', r'\1[REDACTED]', value)
    value = re.sub(r'\b(?:sk|sk-ant|sk-proj)-[A-Za-z0-9_\-]{12,}', '[REDACTED]', value)
    value = re.sub(r'(?i)("(?:apiKey|api_key|access_token|refresh_token|authorization)"\s*:\s*")[^"]+', r'\1[REDACTED]', value)
    return value


def _json(path: Path, value: Any, secrets: list[str]) -> None:
    path.write_text(_redact(json.dumps(value, ensure_ascii=False, indent=2), secrets) + '\n', encoding='utf-8')


def _glm_config(run: Path, env: dict[str, str], secrets: list[str]) -> dict[str, Any]:
    if _sha(ZCODE) != ZCODE_SHA256:
        raise ValueError('ZCode runtime changed; inspect tool controls and model routing before enabling it.')
    current = json.loads(ZCODE_CONFIG.read_text(encoding='utf-8'))
    provider = current['provider']['zai']
    options = provider['options']
    endpoint = urlsplit(options['baseURL'])
    if endpoint.scheme != 'https' or endpoint.hostname != 'api.z.ai' or endpoint.path.rstrip('/') != '/api/anthropic':
        raise ValueError('Existing Z.AI subscription endpoint is not the verified route.')
    if provider.get('kind') != 'anthropic' or not options.get('apiKey'):
        raise ValueError('Existing Z.AI subscription credential is unavailable.')
    model = provider['models']['GLM-5.3']
    reasoning = model.get('reasoning', {})
    if reasoning.get('defaultLevel') != 'max' or 'max' not in reasoning.get('levels', []):
        raise ValueError('GLM-5.3 max effort is not confirmed by the local catalog.')
    # Secrets remain in memory / child environment, never in project configuration.
    secrets.append(options['apiKey'])
    env['ZAI_API_KEY'] = options['apiKey']
    env['ZCODE_MODEL_RETRY_MAX_RETRIES'] = '0'
    config = {
        'model': {'main':'zai/GLM-5.3', 'lite':'zai/GLM-5.3'},
        'provider': {'zai': {'kind':'anthropic', 'name':'Z.AI',
            'options': {'baseURL':options['baseURL'], 'apiKeyRequired':True},
            'models': {'GLM-5.3': model}}},
        'storage': {'dir':str(run / 'zcode-storage'), 'sessionDbPath':str(run / 'session.sqlite')},
        'plugins': {'enabled':False},
        'features': {'mcp':False, 'subagent':False, 'memory':False, 'skill':False},
        'memory': {'use':False}, 'skills': {'enabled':False, 'includeInstructions':False},
        'hooks': {'enabled':False, 'events':{}},
        'permission': {'mode':'plan', 'autoApproveHighRisk':False,
                       'disallowedTools':list(DENY_TOOLS)},
    }
    _json(run / 'zcode.json', config, secrets)
    return {'catalog_model':'GLM-5.3', 'catalog_default_effort':'max',
            'catalog_levels':reasoning['levels'], 'runtime_sha256':ZCODE_SHA256}


def _glm_evidence(run: Path, session_id: str | None) -> list[dict[str, Any]]:
    """Read only allowlisted metadata, never copy request bodies or headers."""
    if not session_id or not re.fullmatch(r'[\w-]+', session_id):
        return []
    candidates = [run / 'zcode-storage/cli/rollout' / f'model-io-{session_id}.jsonl',
                  HOME / '.zcode/cli/rollout' / f'model-io-{session_id}.jsonl']
    rows = []
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            req = row.get('request', {})
            response = row.get('response', {})
            body = req.get('body', {})
            if isinstance(body, str):
                try: body = json.loads(body)
                except ValueError: body = {}
            rows.append({'model':row.get('model'), 'startedAt':row.get('startedAt'),
                         'completedAt':row.get('completedAt'), 'attempt':row.get('attempt'),
                         'body_model':body.get('model'),
                         'body_effort':body.get('output_config',{}).get('effort'),
                         'provider_effort':req.get('providerOptions',{}).get('anthropic',{}).get('effort'),
                         'response_model':response.get('modelId'),
                         'finishReason':response.get('finishReason'),
                         'tool_names_requested':req.get('toolNames'),
                         'tool_calls':[t.get('toolName') or t.get('name') for t in response.get('toolCalls',[])]})
        break
    return rows


def run_model(model: str, effort: str, prompt: str, cwd: str | Path,
              logdir: str | Path, *, timeout_seconds: float = 900,
              deadline_monotonic: float | None = None,
              capability: str = 'textual', execution_dir: str | Path | None = None,
              cancel_event: Any = None, max_turns: int = 12,
              codex_account: str | None = None,
              image_paths: list[str | Path] | None = None) -> dict[str, Any]:
    """One no-retry invocation. Use a fresh logdir for each invocation.

    timeout_seconds bounds this subprocess; optional deadline_monotonic shares a
    caller's total workflow deadline. cancel_event is threading.Event-compatible.
    Code writes only to an explicitly staged job workspace; never to source cwd.
    Research is Claude-only and max_turns bounds native agentic turns (not calls).
    Codex code defaults to primary; textual keeps secondary. Explicit account
    selection changes CODEX_HOME in this child process only; never falls back.
    image_paths accepts only prepared images in logdir.parent/workspace/.mb-anexos.
    Visual transport records submission to the native CLI, never model perception.
    """
    if model not in {'codex','claude','glm'}:
        raise ValueError('model must be codex, claude or glm')
    if capability not in CAPABILITIES or model not in CAPABILITIES[capability]:
        raise ValueError('Supported capabilities: textual=all, research=claude, code=codex')
    if codex_account not in {None,'primary','secondary'} or (model!='codex' and codex_account is not None):
        raise ValueError('codex_account accepts primary/secondary for Codex only')
    selected_account=(codex_account or ('primary' if capability=='code' else 'secondary')) if model=='codex' else None
    selected_home=HOME/('.codex' if selected_account=='primary' else '.codex-gpt2') if selected_account else None
    if capability!='code' and execution_dir is not None:
        raise ValueError('execution_dir is only accepted for code')
    if type(max_turns) is not int or not 1<=max_turns<=30:
        raise ValueError('max_turns must be an integer from 1 to 30')
    if cancel_event is not None and not callable(getattr(cancel_event,'is_set',None)):
        raise ValueError('cancel_event must expose is_set()')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 180_000:
        raise ValueError('prompt must contain 1–180000 characters')
    if effort not in EFFORTS or (model == 'glm' and effort != 'max') or (model == 'claude' and effort == 'ultra'):
        raise ValueError('Unsupported effort; GLM requires max, Claude supports through max.')
    if timeout_seconds <= 0 or timeout_seconds > 3600:
        raise ValueError('timeout_seconds must be in (0, 3600]')
    start = time.monotonic()
    timeout = min(timeout_seconds, deadline_monotonic - start) if deadline_monotonic is not None else timeout_seconds
    if timeout <= 0 or (cancel_event is not None and cancel_event.is_set()):
        return {'text':'', 'exit_code':1, 'status':'deadline_exhausted' if timeout<=0 else 'cancelled', 'actual_model':None,
                'capability':capability,'model_called':False,'tool_results':[],'web_sources':[],
                'image_inputs':[], 'image_transport':{'mechanism':'none','state':'not_started'},
                'visual_inspection_observed':False,
                'effort_requested':effort, 'effort_evidence':'not run'}
    source = Path(cwd).resolve(strict=True)
    if capability!='textual' or image_paths: _no_links(Path(logdir))
    run = Path(logdir).resolve()
    if capability!='textual' and not run.is_relative_to(ROOT):
        raise ValueError('Active capabilities require a logdir inside this MegaBrain workspace')
    work=_workspace(run,execution_dir) if capability=='code' else run
    # Idempotency guard: preserve every prior attempt, including failures.
    run.mkdir(parents=True, exist_ok=True)
    reservation = run / 'result.json'
    with reservation.open('x', encoding='utf-8') as stream:
        stream.write('{"status":"starting"}\n')
    env = os.environ.copy()
    secrets = [v for k,v in env.items() if re.search(r'(?i)(api.?key|token|secret|password)', k) and v]
    for key in list(env):
        if key.startswith(('ANTHROPIC_', 'OPENAI_', 'ZCODE_', 'ZAI_')):
            env.pop(key, None)
    for key in ('CODEX_API_KEY','CODEX_BASE_URL','CLAUDE_CODE_USE_BEDROCK',
                'CLAUDE_CODE_USE_VERTEX','CLAUDE_CODE_USE_FOUNDRY'):
        env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    meta: dict[str, Any] = {'vendor':model, 'effort_requested':effort, 'actual_model':None,
        'started_at':_utc(), 'source_cwd':str(source), 'run_dir':str(run),'execution_dir':str(work),
        'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
        'capability':capability,'tools_allowed':capability!='textual',
        'codex_account':selected_account,'codex_home':str(selected_home) if selected_home else None,
        'tools_requested':[] if capability=='textual' else ['WebSearch','WebFetch'] if capability=='research' else ['shell','file_edit'],
        'tool_results':[],'web_sources':[],'model_called':False,'automatic_retry':False, 'attempt':1,
        'max_turns':max_turns if capability=='research' else None,
        'retry_scope':'Wrapper never retries; GLM client retry limit 0; Claude/Codex internal network policy belongs to their CLIs.',
        'quota_status':'NAO_MEDIDO', 'timeout_seconds':timeout,
        'image_inputs':[], 'image_transport':{'mechanism':'none','state':'not_requested'},
        'image_limits':dict(IMAGE_LIMITS),
        'visual_inspection_observed':False,
        'status':'starting', 'text':'', 'exit_code':None,
        'effort_evidence':'request only; output does not prove equivalent compute across vendors'}
    glm_before = None
    images=[]; image_contents=[]; image_secrets=[]; stdin_prompt=None if model=='glm' else prompt
    try:
        def budget_remaining() -> float:
            remaining=timeout-(time.monotonic()-start)
            if remaining<=0:raise TimeoutError('Deadline exhausted before inference startup')
            return remaining
        images,image_contents=_image_inputs(run,image_paths)
        meta['image_inputs']=images
        if images:
            meta['image_transport']={'mechanism':'none','state':'validating_client',
                'visual_inspection_observed':False,'provider_visual_ack_observed':False}
            transport=_image_cli_support(model,budget_remaining())
            meta['image_transport'].update(transport,state='prepared')
            for row in images:row['transport']=transport['mechanism']
            # Suppress even an accidental CLI echo of the image's encoded bytes.
            image_secrets=[base64.b64encode(data).decode('ascii') for data in image_contents]
            secrets.extend(image_secrets)
        if capability=='code':
            env['CODEX_HOME']=str(selected_home)
            meta['runtime']=_code_runtime(env)
            meta['workspace_before']=_manifest(work)
            meta['sandbox_evidence']=_sandbox_preflight(work,run,env,budget_remaining())
        if model == 'claude':
            args = [str(CLAUDE), '-p', '--safe-mode', '--tools', 'WebSearch,WebFetch' if capability=='research' else '', '--strict-mcp-config',
                '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence', '--setting-sources','',
                '--permission-mode','dontAsk','--disable-slash-commands','--model','claude-opus-5-5',
                '--effort',effort,'--output-format','stream-json' if capability=='research' else 'json']
            if capability=='research':args+=['--restricted','--no-chrome','--allowedTools','WebSearch,WebFetch',
                '--max-turns',str(max_turns),'--verbose','--permission-prompts','none']
            if images:
                args[args.index('--output-format')+1]='stream-json'
                args+=['--input-format','stream-json']
                if '--verbose' not in args:args.append('--verbose')
                content=[{'type':'text','text':prompt}]+[
                    {'type':'image','source':{'type':'base64','media_type':row['mime'],'data':encoded}}
                    for row,encoded in zip(images,image_secrets)]
                stdin_prompt=json.dumps({'type':'user','message':{'role':'user','content':content},
                                         'parent_tool_use_id':None},ensure_ascii=False)+'\n'
            meta.update(requested_model='claude-opus-5-5', auth_route='existing claude.ai subscription; API env removed')
            meta['context_isolation']='--safe-mode disables CLAUDE.md auto-discovery/customizations; managed policy may still apply'
            meta['auth_evidence']=_verify_auth(model,env,budget_remaining())
        elif model == 'codex':
            env['CODEX_HOME'] = str(selected_home)
            args = [str(CODEX),'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check',
                '--ignore-rules','-c','approval_policy="never"','-c','project_doc_max_bytes=0',
                '-c','skills.include_instructions=false','-c','features.skip_host_skill_discovery=true',
                '-c',f'features.shell_tool={"true" if capability=="code" else "false"}',
                '-c','features.apps=false','-c','features.multi_agent=false',
                '-c','features.plugins=false','-c','features.hooks=false',
                '-c','features.browser_use=false','-c','features.computer_use=false',
                '-c','web_search="disabled"','-c','mcp_servers={}',
                '-c',f'model_reasoning_effort="{effort}"','-m','gpt-6-astra','--json','--color','never',
                '--output-last-message',str(run/'last-message.txt'),'-']
            if capability=='code':
                args[2:2]=['--strict-config',*_code_permissions(),*_code_runtime_args(env)]
            else:args[2:2]=['--sandbox','read-only']
            if images:
                # The option accepts multiple values. An explicit '--' keeps
                # the final '-' prompt out of the last image's value list.
                args[-1:-1]=[part for row in images for part in ('--image',row['path'])]+['--']
            meta.update(requested_model='gpt-6-astra', auth_route=f'Codex {selected_account} ChatGPT, CODEX_HOME child only')
            meta['auth_evidence']=_verify_auth(model,env,budget_remaining())
        else:
            glm_before = _sha(ZCODE_CONFIG)
            meta['glm_catalog_evidence'] = _glm_config(run, env, secrets)
            node = shutil.which('node')
            if not node:
                raise ValueError('Node runtime unavailable')
            args = [node,str(ZCODE),'--prompt',prompt,'--mode','plan','--disallowed-tools',
                    ','.join(DENY_TOOLS),'--cwd',str(run),'--json','--no-color']
            # Windows caps command lines at ~32767 UTF-16 units. Pass the same
            # argv to the unmodified official bundle through a tiny Node bridge.
            # This is transport only, not a replacement harness or API client.
            _json(run/'zcode-argv.json',args[2:],[])
            bridge=run/'zcode-launch.cjs'
            bridge.write_text("const fs=require('node:fs');const path=require('node:path');\n"
                +"const bundle="+json.dumps(str(ZCODE))+";\n"
                +"const argv=JSON.parse(fs.readFileSync(path.join(__dirname,'zcode-argv.json'),'utf8'));\n"
                +"process.argv=[process.execPath,bundle,...argv];require(bundle);\n",encoding='utf-8')
            args=[node,str(bridge)]
            meta.update(requested_model='zai/GLM-5.3', auth_route='existing Z.AI credential through official ZCode subscription endpoint')
            meta['argument_transport']='Node argv bridge loads unchanged official runtime; avoids Windows command-line length limit'
        _json(run/'request-metadata.json',meta,secrets)
        (run/'prompt.txt').write_text(_redact(prompt,secrets),encoding='utf-8')
        remaining=budget_remaining()
        if cancel_event is not None and cancel_event.is_set():
            meta['status']='cancelled'; return meta
        if images and model=='codex':
            # The native CLI opens paths itself; catch swaps during auth/help
            # before handing them over. This is not an OS race-proof lock.
            refreshed,_=_image_inputs(run,image_paths)
            if [(r['path'],r['sha256']) for r in refreshed]!=[(r['path'],r['sha256']) for r in images]:
                raise ValueError('Imagem mudou antes do envio ao cliente.')
        remaining=budget_remaining()
        proc = subprocess.Popen(args,cwd=work,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        meta.update(model_called=True,pid=proc.pid if isinstance(proc.pid,int) else None,command_arguments=args,
                    model_called_evidence='Inference CLI launched; provider/model evidence is in completion metadata, if received')
        if images:
            meta['image_transport']['state']='cli_started'
            for row in images:row['state']='cli_started'
        timed_out = False
        stop_reason=None
        if cancel_event is not None or capability!='textual':
            stdout,stderr,stop_reason=_communicate(proc,stdin_prompt,remaining,cancel_event,capability=='code')
            timed_out=stop_reason=='timeout'
        else:
            try:
                stdout, stderr = proc.communicate(stdin_prompt,timeout=remaining)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.kill()
                stdout, stderr = proc.communicate(timeout=10)
        stdout, stderr = _redact(stdout,secrets), _redact(stderr,secrets)
        (run/'stdout.log').write_text(stdout,encoding='utf-8')
        (run/'stderr.log').write_text(stderr,encoding='utf-8')
        meta.update(exit_code=proc.returncode,timed_out=timed_out,
                    cancellation_reason=stop_reason,
                    cancellation_method='taskkill owned PID subtree then parent kill' if stop_reason and capability=='code' else 'owned subprocess kill' if stop_reason else None,
                    status=stop_reason or ('timeout' if timed_out else 'completed' if proc.returncode==0 else 'error'))
        if model == 'codex':
            events=_events(stdout)
            meta['usage']=[e.get('usage') for e in events if e.get('type')=='turn.completed']
            meta['tool_results'],meta['web_sources']=_tool_evidence(events,model,work,run/'stdout.log')
            meta['tool_events']=[r['name'] for r in meta['tool_results']]
            if any(r['kind'] not in ({'command','file_change'} if capability=='code' else set()) for r in meta['tool_results']):
                meta['status']='tool_policy_violation'
            meta['harness_errors']=[e for e in events if e.get('type') in {'error','turn.failed'}]
            if meta['harness_errors'] and meta['status']=='completed':meta['status']='error'
            if capability=='code' and not meta['usage'] and meta['status']=='completed':meta['status']='missing_result_event'
            last=run/'last-message.txt'
            meta['text']=_redact(last.read_text(encoding='utf-8'),secrets) if last.exists() else ''
            if last.exists(): last.write_text(meta['text'],encoding='utf-8')
            meta['actual_model_evidence']='CLI selection gpt-6-astra; JSONL response does not echo independent model identity'
        else:
            if capability=='research' or (model=='claude' and images):
                events=_events(stdout)
                record=next((row for row in reversed(events) if row.get('type')=='result'),{})
                meta['tool_results'],meta['web_sources']=_tool_evidence(events,model,work,run/'stdout.log')
                meta['tool_events']=[r['name'] for r in meta['tool_results']]
                allowed_kinds={'web_search','web_fetch'} if capability=='research' else set()
                if any(r['kind'] not in allowed_kinds for r in meta['tool_results']):meta['status']='tool_policy_violation'
                if not record and meta['status']=='completed':meta['status']='missing_result_event'
            else:record=json.loads(stdout) if stdout.strip() else {}
            meta['session_id']=record.get('sessionId') or record.get('session_id')
            meta['text']=record.get('response','') if model=='glm' else record.get('result','')
            meta['usage']=record.get('usage')
            if record.get('is_error'):
                meta['status']='error'
            if model=='claude':
                usage=record.get('modelUsage') or {}
                meta['actual_models']=list(usage)
                meta['actual_model']='claude-opus-5-5' if 'claude-opus-5-5' in usage else next(iter(usage),None)
                meta['actual_model_evidence']='Claude CLI modelUsage envelope'
            else:
                rows=_glm_evidence(run,meta['session_id'])
                meta['model_io_metadata']=rows
                actual=sorted({r['model']['modelId'] for r in rows if r.get('model')})
                meta['actual_models']=actual
                meta['actual_model']=actual[0] if len(actual)==1 else None
                if actual and actual!=['GLM-5.3']:meta['status']='wrong_model'
                proved_max = bool(rows) and all(r.get('body_effort')=='max' and r.get('provider_effort')=='max' for r in rows)
                meta['effort_evidence']='model IO request body output_config.effort=max and providerOptions.anthropic.effort=max' if proved_max else 'local catalog default max; actual request effort not yet verified'
                meta['effort_verified']=proved_max
                if any(r['tool_calls'] or r['tool_names_requested'] for r in rows):meta['status']='tool_policy_violation'
                if not actual and meta['status']=='completed':meta['status']='completed_model_unverified'
                if not proved_max and meta['status']=='completed':meta['status']='effort_unverified'
        meta['rate_limit_detected']=_rate_limit_failure(stdout,stderr)
        if meta['rate_limit_detected'] and meta['status'] not in {'completed','cancelled','timeout'}:
            meta['status']='rate_limited_no_retry'
    except ImageTransportUnavailable as exc:
        meta.update(status='image_transport_unavailable',error=_redact(str(exc),secrets))
        meta['image_transport'].update(state='unsupported',limitation=str(exc))
        for row in images:row.update(state='unsupported',transport='unsupported')
    except Exception as exc:
        meta.update(status='error',error=_redact(f'{type(exc).__name__}: {exc}',secrets))
    finally:
        if images:
            submitted=meta['status']=='completed' and meta['exit_code']==0
            meta['image_transport']['state']='submitted_to_cli' if submitted else meta['image_transport']['state']
            for row in images:
                row['transported']=submitted
                if submitted:row['state']='submitted_to_cli'
        if capability=='code':
            try:meta['workspace_after']=_manifest(work)
            except Exception as exc:
                meta.update(status='workspace_policy_violation',workspace_error=_redact(str(exc),secrets))
        if glm_before is not None:
            meta['global_config_unchanged']=glm_before==_sha(ZCODE_CONFIG)
            if not meta['global_config_unchanged']:meta['status']='global_config_changed'
        meta['process_exit_code']=meta['exit_code']
        if meta['status']!='completed':
            meta['text']=''
            meta['exit_code']=meta['exit_code'] or 1
            meta.setdefault('error','Inference result not accepted: '+meta['status'])
        elapsed=round(time.monotonic()-start,3)
        meta.update(finished_at=_utc(),elapsed_seconds=elapsed,duration_seconds=elapsed,effort=effort)
        _json(reservation,meta,secrets)
    return meta
