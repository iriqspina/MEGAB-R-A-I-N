"""Authenticated application API, shared by the native window and mobile client."""
from __future__ import annotations
import argparse, asyncio, hashlib, html, io, json, logging, mimetypes, os, re, secrets, sys, threading, time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit
APP=Path(__file__).resolve().parent
sys.path.insert(0,str(APP/'runtime-packages'))
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response, HTMLResponse
from central_store import Store, Conflict, WORKSPACE, PROCESS, ROOT, now, ident, read_json, validate_process
from central_sources import Sources
from central_routing import DEFAULT_ROUTES, validate_routing, preview, routing_document
from central_attachments import MAX_UPLOAD_BODY, save_attachment, read_attachment, resolve_attachments, attachment_fields, normalize_feedback

PRIVATE=APP/'data/.private'
def secret_file(name):
    PRIVATE.mkdir(parents=True,exist_ok=True)
    p=PRIVATE/name
    if not p.exists():
        try:
            with p.open('x',encoding='ascii') as f: f.write(secrets.token_hex(32))
            try: os.chmod(p,0o600)
            except OSError: pass
        except FileExistsError: pass
    return p.read_text(encoding='ascii').strip()

# 261022 (<USUARIO>: "faça só o quadro 'Ponte de correção' da central MegaBrain despachar para a ponte"):
# a seção Ponte de correção (BridgePanel, no quadro Agora do projeto e da página inicial) leva
# data-cf-zona="ponte-correcao" e a nota do cursor envia essa zona. Decide pela marca estrutural, não pelo
# rótulo visível (revisão Codex 2: botões e campos da seção têm rótulo próprio; outro título igual não é a seção).
ZONA_PONTE='ponte-correcao'
def nota_do_quadro_ponte(comment):
    source=comment.get('cursor_source')
    return isinstance(source,dict) and source.get('zona')==ZONA_PONTE

def build_app(store=None,sources=None,remote=False,port=8766,bridge=None):
    # port selects the accepted local Host; scripts/isolated_server.py serves a database copy on 8768.
    # 261018 ponte: só o app real (banco padrão, fora de instância isolada) abre sessões de IA.
    real_store=store is None and os.environ.get('MB_ISOLATED')!='1' and os.environ.get('MB_PONTE')!='0'
    store=store or Store(); sources=sources or Sources(store)
    from central_bridge import Ponte, PonteErro, vendors as bridge_vendors, listar_ordens, parar as bridge_stop, PASTA as BRIDGE_DIR
    ponte=bridge or Ponte(store,sources,lancar=real_store)
    gateway=secret_file('gateway.key'); master=secret_file('native.key')
    failures={}; qr_pairs={}; auth_lock=threading.RLock()
    @asynccontextmanager
    async def lifespan(app):
        async def watcher():
            while True:
                try:
                    await asyncio.to_thread(store.reconcile)
                except Exception: logging.getLogger('megabrain.watcher').exception('Falha ao reconciliar sessões')
                try:
                    await asyncio.to_thread(sources.poll)
                except Exception: logging.getLogger('megabrain.watcher').exception('Falha ao atualizar fontes; nova tentativa em 3 segundos')
                try:
                    await asyncio.to_thread(ponte.tick)
                except Exception: logging.getLogger('megabrain.watcher').exception('Falha na ponte de correção; nova tentativa em 3 segundos')
                await asyncio.sleep(3)
        task=asyncio.create_task(watcher())
        yield
        task.cancel()
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    app.state.store=store; app.state.sources=sources; app.state.ponte=ponte
    def request_identity(request,body):
        key=request.headers.get('idempotency-key')
        if key and not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',key): raise ValueError('Identificador da tentativa inválido.')
        digest=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        return key,digest
    def comment_route(body):
        # A escolha humana é validada antes de salvar o comentário. Ausência
        # significa herdar o projeto; não transformar erro em outra IA.
        from central_bridge_routing import validar_rota
        return validar_rota(body['rota']) if body.get('rota') is not None else None
    @app.middleware('http')
    async def security(request,call_next):
        host=request.headers.get('host','')
        if remote:
            supplied=request.headers.get('x-mb-gateway','')
            if not secrets.compare_digest(supplied,gateway): return JSONResponse({'detail':'Acesso não autorizado.'},status_code=403)
            origin=request.headers.get('x-mb-public-origin','')
            parsed=urlsplit(origin)
            if parsed.scheme!='https' or not parsed.netloc or parsed.path not in ('','/') or parsed.username: return JSONResponse({'detail':'Origem inválida.'},status_code=403)
        else:
            if host not in {f'127.0.0.1:{port}',f'localhost:{port}','testserver'}: return JSONResponse({'detail':'Host inválido.'},status_code=403)
            origin='http://'+host
        request.state.origin=origin.rstrip('/')
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            supplied_origin=request.headers.get('origin')
            if supplied_origin and supplied_origin!=request.state.origin: return JSONResponse({'detail':'Origem não autorizada.'},status_code=403)
            if request.headers.get('sec-fetch-site')=='cross-site': return JSONResponse({'detail':'Requisição externa bloqueada.'},status_code=403)
            try: length=int(request.headers.get('content-length','0'))
            except ValueError: return JSONResponse({'detail':'Tamanho do pedido inválido.'},status_code=413)
            upload=request.method=='POST' and re.fullmatch(r'/api/projects/[^/]+/attachments',request.url.path)
            limit=MAX_UPLOAD_BODY if upload else 350000
            if length<0 or length>limit: return JSONResponse({'detail':'Pedido grande demais.'},status_code=413)
            chunks=[]; size=0
            async for chunk in request.stream():
                size+=len(chunk)
                if size>limit: return JSONResponse({'detail':'Pedido grande demais.'},status_code=413)
                chunks.append(chunk)
            # Starlette's cached request forwards this bounded body downstream.
            request._body=b''.join(chunks)
        path=request.url.path
        public=path in {'/api/pair','/api/health'} or not path.startswith('/api/')
        if not public:
            token=request.cookies.get('mb_session','')
            session=store.auth_session(token)
            if not session or session['expires']<time.time(): return JSONResponse({'detail':'Conecte este dispositivo ao MegaBrain.'},status_code=401)
            request.state.session=session
            if request.method in {'POST','PUT','PATCH','DELETE'} and not secrets.compare_digest(request.headers.get('x-mb-csrf',''),session['csrf']): return JSONResponse({'detail':'Sessão desatualizada. Recarregue.'},status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Cache-Control']='no-store' if path.startswith('/api/') else 'no-cache'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        isolated_job_resource=bool(re.fullmatch(r'/api/jobs/[a-f0-9]{32}/(?:preview|render|resources|view)/[a-f0-9]{24}',path))
        isolated_report=bool(re.fullmatch(r'/api/reports/[a-f0-9]{20}/(?:view|render)',path))
        if not path.startswith('/api/files/') and not isolated_job_resource and not isolated_report:
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; frame-src 'self' https:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        return response
    @app.exception_handler(Conflict)
    async def conflict(r,e): return JSONResponse({'detail':str(e)},status_code=409)
    @app.exception_handler(ValueError)
    async def invalid(r,e): return JSONResponse({'detail':str(e)},status_code=400)
    @app.exception_handler(KeyError)
    async def absent(r,e): return JSONResponse({'detail':str(e)},status_code=404)
    @app.get('/api/health')
    def health(): return {'ok':True,'app':'megabrain-central','version':'2.0.0'}
    @app.post('/api/pair')
    async def pair(request:Request):
        data=await request.json(); code=str(data.get('code',''))
        client=request.headers.get('x-mb-client-ip') if remote else request.client.host
        client=client or 'remote'
        with auth_lock:
            cutoff=time.time()-300
            for key in list(failures):
                failures[key]=[at for at in failures[key] if at>cutoff]
                if not failures[key]:del failures[key]
            if client not in failures and len(failures)>=4096:
                del failures[min(failures,key=lambda key:failures[key][-1])]
            bad=[v for v in failures.get(client,[]) if v>time.time()-300]
            if len(bad)>=8: raise HTTPException(429,'Aguarde cinco minutos antes de tentar novamente.')
            valid_master=not remote and secrets.compare_digest(code,master)
            valid_pair=store.pairing_consume(code) if not valid_master else False
            if not (valid_master or valid_pair):
                failures[client]=bad+[time.time()]; raise HTTPException(401,'Código inválido ou vencido. Gere outro no computador.')
            token=secrets.token_urlsafe(40); csrf=secrets.token_urlsafe(32)
            store.auth_create(token,csrf,time.time()+30*86400)
        response=JSONResponse({'authenticated':True,'csrf':csrf})
        response.set_cookie('mb_session',token,max_age=30*86400,httponly=True,secure=remote,samesite='strict',path='/')
        return response
    @app.get('/api/session')
    def session(request:Request): return dict(authenticated=True,csrf=request.state.session['csrf'],remote=remote,version='2.0.0',central_project_id=ident(ROOT))
    @app.post('/api/logout')
    def logout(request:Request):
        store.auth_revoke(request.cookies.get('mb_session',''))
        r=JSONResponse({'ok':True}); r.delete_cookie('mb_session'); return r
    @app.get('/api/projects')
    def projects(): return sources.summaries()
    @app.get('/api/search')
    def search(q:str='',project:str|None=None,kind:str|None=None,scope:str='todos',cursor:str|None=None,limit:int=50):
        # 261021 F0b · localizador: índice de metadados, sem corpo de relatório.
        return sources.catalog.search(q,project or None,kind or None,scope,cursor or None,limit,projects=sources.summaries()['projects'])
    @app.get('/api/session-connections')
    def session_connections():
        from central_session_connections import snapshot
        return snapshot(APP, sources)
    @app.get('/api/projects/{pid}')
    def detail(pid:str): return sources.detail(pid)
    @app.post('/api/projects/{pid}/attachments')
    async def upload_attachment(pid:str,r:Request):
        root=sources.root(pid);body=await r.json();key,digest=request_identity(r,body)
        document='attachment-upload:'+pid+':'+key if key else None
        previous=store.get(document,{}) if document else None
        if previous and previous['revision']:
            if previous['data'].get('digest')!=digest:raise Conflict('Esta tentativa já foi usada com outra imagem.')
            saved,_=read_attachment(root,pid,previous['data']['id'])
            return {'attachment':saved}
        saved=save_attachment(root,pid,body)
        if document:
            try:store.put(document,0,dict(digest=digest,id=saved['id']))
            except Conflict:
                prior=store.get(document,{})['data']
                if prior.get('digest')!=digest:raise Conflict('Esta tentativa já foi usada com outra imagem.')
                saved,_=read_attachment(root,pid,prior['id'])
        return {'attachment':saved}
    @app.get('/api/projects/{pid}/attachments/{aid}')
    def download_attachment(pid:str,aid:str):
        root=sources.root(pid);saved,data=read_attachment(root,pid,aid)
        return Response(data,media_type=saved['mime'],headers={'Content-Security-Policy':"sandbox; default-src 'none'; frame-ancestors 'self'"})
    @app.get('/api/workspace')
    def workspace(): return store.get('workspace',WORKSPACE)
    @app.get('/api/returns')
    def returns(after:int=0):
        return sources.returns.snapshot(sources,after)
    @app.put('/api/workspace')
    async def save_workspace(r:Request):
        body=await r.json(); data=body.get('data')
        if not isinstance(data,dict): raise ValueError('Área de trabalho inválida.')
        return store.put('workspace',body.get('revision'),data)
    @app.get('/api/projects/{pid}/process')
    def process(pid:str):
        sources.root(pid)
        return dict(store.get('process:'+pid,PROCESS),applies_to='Novas sessões de análise deste aplicativo; não altera conversas externas.')
    @app.put('/api/projects/{pid}/process')
    async def save_process(pid:str,r:Request):
        sources.root(pid); b=await r.json(); data=validate_process(b.get('data'))
        saved=store.put('process:'+pid,b.get('revision'),data); store.event(pid,'Processo atualizado','configuration'); return saved
    @app.get('/api/projects/{pid}/routing')
    def routing(pid:str):
        sources.root(pid); return routing_document(store,pid)
    @app.put('/api/projects/{pid}/routing')
    async def save_routing(pid:str,r:Request):
        sources.root(pid); b=await r.json(); data=validate_routing(b.get('data'))
        saved=store.put('routing:'+pid,b.get('revision'),data); store.event(pid,'Esteiras atualizadas','configuration'); return saved
    @app.post('/api/projects/{pid}/route-preview')
    async def route_preview(pid:str,r:Request):
        sources.root(pid); b=await r.json()
        return preview(routing_document(store,pid)['data'],str(b.get('prompt',''))[:20000],b.get('category'),b.get('categories'))
    @app.get('/api/projects/{pid}/code-files')
    def code_files(pid:str):
        from central_execution import list_source_files
        return list_source_files(sources.root(pid))
    @app.post('/api/projects/{pid}/comments')
    async def comment(pid:str,r:Request):
        root=sources.root(pid); b=await r.json(); text=b.get('text','')
        if not isinstance(text,str):raise ValueError('Comentário inválido.')
        text=text.strip();attachments=resolve_attachments(root,pid,b.get('anexos',[]))
        if len(text)>6000 or (not text and not attachments): raise ValueError('Escreva uma nota de até 6.000 caracteres ou adicione uma imagem.')
        provenance = b.get('cursor_source'); route=comment_route(b)
        extra = attachment_fields(attachments)
        if route is not None:extra['rota']=route
        if isinstance(provenance,dict):
            extra['cursor_source']={k:str(provenance[k])[:240] for k in ('note_id','storage_key','where','created_at','zona') if isinstance(provenance.get(k),str)}
        payload=dict(text=text,target=str(b.get('target','project'))[:180],anchor=b.get('anchor'),**extra)
        ponte.validar_destino(pid,payload)
        # 261022 (revisão Codex 2, R5): a zona do cursor não muda o conteúdo da nota; reenvio da mesma tentativa
        # com ou sem zona devolve o mesmo comentário em vez de 409 sem fim — inclusive recibo gravado antes desta
        # versão (assinatura do corpo inteiro, com ou sem a única zona existente).
        identidade=dict(b,cursor_source={k:v for k,v in provenance.items() if k!='zona'}) if isinstance(provenance,dict) else b
        chave,assinatura=request_identity(r,identidade)
        equivalentes={request_identity(r,b)[1]}
        if isinstance(provenance,dict) and provenance.get('zona') in (None,ZONA_PONTE):  # R6: outra zona compara estrito
            equivalentes.add(request_identity(r,dict(identidade,cursor_source=dict(identidade['cursor_source'],zona=ZONA_PONTE)))[1])
        out,created=store.create_once('comments',pid,payload,chave,assinatura,equivalentes=tuple(equivalentes))
        sources.cache.pop(pid,None)
        bridge_info=None
        if created:
            store.event(pid,'Comentário salvo','comment')
            # 261020: notas do cursor no próprio app (target app:home e demais app:*) seguem a mesma ponte das
            # respostas de relatório, sem resgate manual. Notas de quadro (module:*) ficam como antes, exceto a
            # seção Ponte de correção (decisão do <USUARIO> em 261022); falha da ponte não perde o comentário salvo.
            if str(out.get('target','')).startswith('app:') or route is not None or nota_do_quadro_ponte(out):
                try:bridge_info=ponte.receber(pid,root,out)
                except Exception as error:
                    logging.getLogger('megabrain.ponte').exception('Ponte não recebeu o comentário')
                    bridge_info=dict(estado='erro',mensagem=str(error)[:300])
        return {'comment':out,'ponte':bridge_info}
    @app.post('/api/projects/{pid}/comments/{cid}/replies')
    async def comment_reply(pid:str,cid:str,r:Request):
        # 261021: "comentar comentários". A resposta é um comentário próprio ligado ao original (responde_a/fio);
        # leva o texto, as notas e o retorno do agente como contexto e segue a mesma ponte. Ordem do original
        # ainda aberta → complemento dela; concluída → ordem nova (central_bridge._ordem_aberta_do_original).
        root=sources.root(pid); b=await r.json(); text=b.get('text','')
        if not isinstance(text,str) or not text.strip() or len(text.strip())>6000:raise ValueError('Escreva uma resposta de até 6.000 caracteres.')
        with store.db() as c:row=c.execute('SELECT data FROM comments WHERE id=? AND project=?',(cid,pid)).fetchone()
        if not row:raise KeyError('Comentário original não encontrado neste projeto.')
        original=json.loads(row[0]);fb=original.get('feedback') if isinstance(original.get('feedback'),dict) else {}
        contexto=dict(id=original.get('id'),at=original.get('at'),texto=str(original.get('text') or '')[:6000],onde=original.get('onde'),
                      relatorio=original.get('source'),target=original.get('target'),correcao=str(original.get('correction') or '')[:3000] or None,
                      notas=[dict(onde=str(n.get('onde') or '')[:240],texto=str(n.get('texto') or '')[:3000]) for n in (fb.get('notas') or [])[:30] if isinstance(n,dict) and n.get('texto')])
        payload=dict(text=text.strip(),target='reply:'+cid,responde_a=cid,fio=original.get('fio') or cid,contexto_original=contexto)
        out,created=store.create_once('comments',pid,payload,*request_identity(r,b))
        sources.cache.pop(pid,None)
        bridge_info=None
        if created:
            store.event(pid,'Resposta a comentário salva','comment')
            try:bridge_info=ponte.receber(pid,root,out)
            except Exception as error:
                logging.getLogger('megabrain.ponte').exception('Ponte não recebeu a resposta')
                bridge_info=dict(estado='erro',mensagem=str(error)[:300])
        return {'comment':out,'ponte':bridge_info}
    @app.post('/api/projects/{pid}/references')
    async def reference(pid:str,r:Request):
        sources.root(pid); b=await r.json(); url=str(b.get('url','')).strip(); u=urlsplit(url)
        if u.scheme!='https' or not u.hostname or u.username or u.password or len(url)>4000: raise ValueError('Use um link HTTPS sem senha.')
        out,created=store.create_once('refs',pid,dict(url=url,title=str(b.get('title') or u.hostname)[:180],type='link',role='reference'),*request_identity(r,b))
        sources.cache.pop(pid,None)
        if created: store.event(pid,'Referência adicionada','reference')
        return {'reference':out}
    @app.get('/api/events')
    def events(after:int=0): return store.events(max(0,after))
    def report_source(fid,expected_hash=None):
        from central_reports import confined_file,MAX_REPORT
        path,root=sources.file(fid)
        path=confined_file(path,root,suffixes={'.html','.htm'},limit=MAX_REPORT)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_hash is not None and digest!=expected_hash:
            raise HTTPException(409,'O relatório mudou. Reabra a versão atual antes de salvar sua resposta.')
        return path,root,digest
    def report_version(body):
        digest=body.get('hash')
        if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest):
            raise ValueError('A versão do relatório é obrigatória.')
        return digest
    # 261017 WP2: a IA pode regravar o relatório enquanto o <USUARIO> comenta.
    # A versão que ele abriu continua aceita para rascunho e envio, gravada com
    # o hash antigo e a marca versao_anterior. Só vale para versões já servidas
    # a ESTE relatório (fid); hash de outro relatório ou nunca aberto: 409.
    def remember_report_version(fid,digest):
        key='report-versions:'+fid
        for _ in range(3):
            saved=store.get(key,{'hashes':[]})
            hashes=[h for h in (saved['data'].get('hashes') or []) if isinstance(h,str)] if isinstance(saved['data'],dict) else []
            if digest in hashes:return
            try:store.put(key,saved['revision'],dict(hashes=(hashes+[digest])[-60:],at=now()));return
            except Conflict:continue
    def report_opened_version(fid,body):
        wanted=report_version(body)
        path,root,digest=report_source(fid)
        if wanted==digest:return path,root,digest,digest
        saved=store.get('report-versions:'+fid,{'hashes':[]})['data']
        known=isinstance(saved,dict) and wanted in (saved.get('hashes') or [])
        # Versões abertas antes deste registro existir deixaram rascunho.
        if not known:known=store.get('report-draft:'+fid+':'+wanted,{})['revision']>0
        if not known:raise HTTPException(409,'O relatório mudou. Reabra a versão atual antes de salvar sua resposta.')
        return path,root,wanted,digest
    @app.get('/api/reports/{fid}/note-receipts')
    def report_note_receipts(fid:str,hash:str):
        from central_note_receipts import note_receipts
        path,root,digest,atual=report_opened_version(fid,dict(hash=hash))
        return note_receipts(store,ident(root),fid,digest)
    @app.get('/api/reports/{fid}/status')
    def report_status(fid:str):
        path,root,digest=report_source(fid)
        return dict(hash=digest,modified_at=path.stat().st_mtime,title=path.name)
    @app.get('/api/reports/{fid}/view')
    async def report_view(fid:str,ticket:str):
        from central_reports import wrapper_report,view_headers
        path,root,digest=report_source(fid)
        remember_report_version(fid,digest)
        registro=store.get('report-draft:'+fid+':'+digest,{})
        draft=registro.get('data',{})
        if not registro.get('revision'):
            # Sem rascunho NESTA versão (registro inexistente — rascunho vazio
            # gravado de propósito é respeitado e não cai aqui): recupera o
            # rascunho mais recente deste mesmo relatório. As notas da versão
            # anterior voltam; a âncora exata pode não existir mais, mas a
            # posição gravada e o rótulo de onde a nota foi cravada continuam
            # dizendo onde estava e o que significava. Rascunhos de outros
            # relatórios não vazam: a busca é prefixada pelo fid.
            with store.db() as c:
                row=c.execute("SELECT data FROM documents WHERE key LIKE ? ORDER BY json_extract(data,'$.at') DESC LIMIT 1",('report-draft:'+fid+':%',)).fetchone()
            if row:
                candidato=json.loads(row['data']) if isinstance(row['data'],str) else row['data']
                if isinstance(candidato.get('storage'),dict) and candidato['storage']:
                    draft=candidato
        from central_comment_visibility import visible_report_storage
        return HTMLResponse(wrapper_report(fid,ticket,visible_report_storage(store,fid,draft.get('storage',{})),digest),headers=view_headers)
    @app.get('/api/reports/{fid}/render')
    def report_render(fid:str,ticket:str,version:str|None=None):
        from central_reports import render_report,render_headers
        path,root,digest=report_source(fid,version)
        return HTMLResponse(render_report(path,root,fid,ticket),headers=render_headers)
    @app.post('/api/reports/{fid}/draft')
    async def report_draft(fid:str,r:Request):
        body=await r.json();path,root,digest,atual=report_opened_version(fid,body)
        payload=body.get('storage',{})
        storage=payload if isinstance(payload,dict) else None
        if not isinstance(storage,dict) or len(storage)>100 or len(json.dumps(storage))>128000:
            raise ValueError('Rascunho fora do limite permitido.')
        if any(not isinstance(k,str) or len(k)>250 or not isinstance(v,str) or len(v)>50000 for k,v in storage.items()):
            raise ValueError('Conteúdo de rascunho inválido.')
        key='report-draft:'+fid+':'+digest;current=store.get(key,{})
        data=dict(storage=storage,source_hash=digest,source=str(path.relative_to(root)),at=now())
        if digest!=atual:data.update(versao_anterior=True,hash_atual=atual)
        return store.put(key,current['revision'],data)
    @app.post('/api/reports/{fid}/feedback')
    async def report_feedback(fid:str,r:Request):
        body=await r.json();path,root,digest,atual=report_opened_version(fid,body);anterior=digest!=atual
        note=body.get('note','');feedback=body.get('feedback');route=comment_route(body)
        if not isinstance(note,str) or len(note)>6000:raise ValueError('Comentário inválido.')
        if feedback is not None:
            if not isinstance(feedback,dict) or feedback.get('kind') not in {'notes','decisions'} or len(json.dumps(feedback))>128000:
                raise ValueError('Resposta de relatório inválida.')
            feedback={k:v for k,v in feedback.items() if k in {'kind','finalizado','respostas','notas','resumo_texto','resumo_texto_original','anexos'}}
            if feedback.get('kind')=='decisions' and feedback.get('finalizado') is not True:
                raise ValueError('Finalize as respostas antes de enviá-las ao projeto.')
        feedback,attachments=normalize_feedback(root,ident(root),feedback,body.get('anexos',[]))
        if feedback:
            for item in feedback.get('notas',[]):
                selected=comment_route(item)
                if selected is not None:item['rota']=selected
        if not note.strip() and not feedback and not attachments:raise ValueError('Escreva uma nota, adicione uma imagem ou finalize suas respostas.')
        choices=feedback.get('respostas',{}) if feedback else {}
        notes=feedback.get('notas',[]) if feedback else []
        payload=dict(text=(note.strip() or ('' if attachments else 'Respostas recebidas pelo relatório'))[:6000],target='file:'+fid,feedback=feedback,source=str(path.relative_to(root)),source_hash=digest,status='Recebido, aguardando correção',onde=path.name,decision_count=len(choices) if isinstance(choices,(dict,list)) else 0,note_count=len(notes) if isinstance(notes,list) else 0,**attachment_fields(attachments))
        if route is not None:payload['rota']=route
        if anterior:payload.update(versao_anterior=True,hash_atual=atual)
        ponte.validar_destino(ident(root),payload)
        out,created=store.create_once('comments',ident(root),payload,*request_identity(r,body))
        sources.cache.pop(ident(root),None)
        bridge_info=None
        if created:
            store.event(ident(root),'Resposta recebida: '+path.name+(' (versão anterior)' if anterior else ''),'feedback_received')
            # 261018: o comentário segue sozinho para o planejador; falha da ponte não perde o comentário salvo.
            try:bridge_info=ponte.receber(ident(root),root,out)
            except Exception as error:
                logging.getLogger('megabrain.ponte').exception('Ponte não recebeu o comentário')
                bridge_info=dict(estado='erro',mensagem=str(error)[:300])
        return {'comment':out,'status':payload['status'],'versao_anterior':anterior,'ponte':bridge_info}
    def bridge_view(pid):
        from central_bridge_routing import catalogo, presets
        root=sources.root(pid);cfg=ponte.config(pid)
        return dict(revision=cfg['revision'],data=cfg['data'],vendors=bridge_vendors(ponte.central),ordens=listar_ordens(root,10),
                    catalogo=catalogo(ponte.central),presets=presets(ponte.central),
                    lancamento=bool(ponte.lancar),pasta=str(root/BRIDGE_DIR),
                    pendentes=ponte.pendentes_view(pid),controle=ponte._controle(pid))
    @app.get('/api/bridge/vendors')
    def bridge_vendor_list():return {'vendors':bridge_vendors(ponte.central)}
    @app.get('/api/projects/{pid}/control')
    def project_control_get(pid:str):
        from central_project_control import read
        sources.root(pid)
        return dict(read(store,pid), projeto=sources.root(pid).name)
    @app.put('/api/projects/{pid}/control')
    async def project_control_put(pid:str,r:Request):
        from central_project_control import save
        sources.root(pid); b=await r.json()
        return dict(save(store,pid,b.get('revision'),b.get('modo')), projeto=sources.root(pid).name)
    @app.get('/api/projects/{pid}/bridge')
    def bridge_get(pid:str):return bridge_view(pid)
    @app.put('/api/projects/{pid}/bridge')
    async def bridge_put(pid:str,r:Request):
        sources.root(pid);b=await r.json()
        ponte.salvar_config(pid,b.get('revision'),b.get('data'))
        store.event(pid,'Ponte de correção configurada','configuration')
        return bridge_view(pid)
    @app.post('/api/projects/{pid}/bridge/send')
    async def bridge_send(pid:str,r:Request):
        root=sources.root(pid);b=await r.json()
        result=ponte.enviar_agora(pid,root,b.get('comment_ids'),b.get('vendor'),b.get('modo'),b.get('coordenacao'),pipeline=b.get('pipeline'))
        sources.cache.pop(pid,None)
        return result
    @app.post('/api/projects/{pid}/bridge/pending/discard')
    async def bridge_discard_pending(pid:str,r:Request):
        # 261022 Bubble: lote já atendido à mão por outra sessão sai da fila sem abrir ordem duplicada na retomada.
        sources.root(pid);b=await r.json()
        if not isinstance(b,dict) or not isinstance(b.get('chave'),str) or type(b.get('revisao')) is not int:
            raise ValueError('Informe o lote e a versão vista no painel.')
        result=ponte.descartar_pendente(pid,b['chave'],b.get('motivo',''),revisao=b['revisao'])
        sources.cache.pop(pid,None)
        return result
    @app.post('/api/projects/{pid}/bridge/orders/{oid}/stop')
    def bridge_stop_order(pid:str,oid:str):
        root=sources.root(pid)
        if not re.fullmatch(r'\d{6}-\d{6}-[a-f0-9]{6}',oid):raise ValueError('Ordem inválida.')
        stopped=bridge_stop(root/BRIDGE_DIR/oid)
        store.event(pid,f'Ponte: parada pedida na ordem {oid}','bridge',ordem=oid)
        return {'parados':stopped}
    @app.post('/api/dispatch/{fid}')
    async def dispatch_terminal(fid:str,r:Request):
        import central_dispatch
        body=await r.json();path,root,digest=report_source(fid,report_version(body))
        from central_project_control import check
        check(store,ident(root))
        central_dispatch.validar(body)
        result=central_dispatch.dispatch(path,root,body)
        sources.cache.pop(ident(root),None)
        store.event(ident(root),f"Despacho pro terminal · {result['ia']} · {path.name}",'dispatch_sent')
        return result
    def presentation(path,root):
        asset=sources.index_file(path,root)
        if not asset:raise ValueError('Arquivo não disponível para apresentação.')
        return dict(project_id=ident(root),item=dict(id=asset['id'],title=asset['name'],type=asset['type'],url=asset['url'],caption=asset['origin']))
    @app.post('/api/reports/{fid}/resolve')
    async def resolve_report_link(fid:str,r:Request):
        from central_reports import confined_file, MAX_REPORT, MAX_RESOURCE
        body=await r.json();path,root,digest=report_source(fid,report_version(body))
        value=body.get('path')
        if not isinstance(value,str) or len(value)>2000:raise ValueError('Link inválido.')
        candidate=root/value
        return presentation(confined_file(candidate,root,limit=MAX_REPORT if candidate.suffix.lower() in {'.html','.htm'} else MAX_RESOURCE),root)
    @app.post('/api/present')
    async def present(r:Request):
        from central_reports import confined_file, MAX_REPORT, MAX_RESOURCE
        body=await r.json()
        if body.get('project') and not body.get('path'):
            root=sources.root(ident(Path(body['project']).resolve()))
            return dict(project_id=ident(root),item=None)
        value=body.get('path')
        if not isinstance(value,str) or len(value)>2000:raise ValueError('Caminho de entrega inválido.')
        path=Path(value).resolve(strict=True)
        root=next((p for p in sources.projects.values() if path.is_relative_to(p)),None)
        if root is None:raise ValueError('Projeto ainda não conectado à central.')
        return presentation(confined_file(path,root,limit=MAX_REPORT if path.suffix.lower() in {'.html','.htm'} else MAX_RESOURCE),root)
    @app.get('/api/report-audit')
    def report_audit():
        rows=[]
        summaries={p['id']:p for p in sources.summaries()['projects']}
        for pid,root in sources.projects.items():
            detail=sources.detail(pid,force=True,summary=summaries[pid])
            reports=[d for d in detail['deliveries'] if d.get('type')=='html' and d.get('file_id')]
            physical=sources.report_paths(root);indexed={d['file_id'] for d in reports}
            from central_reports import MAX_REPORT
            rows.append(dict(project_id=pid,project=detail['project']['name'],reports=len(reports),found=len(physical),indexed=len(indexed),not_indexed=[str(p.relative_to(root)) for p in physical if ident(p) not in indexed],interactive_incompatible=[str(p.relative_to(root)) for p in physical if p.stat().st_size>MAX_REPORT],root=str(root)))
        from central_reports import MAX_REPORT, MAX_RESOURCE, MAX_BUNDLE
        return dict(at=now(),presentation='native-app',projects=rows,total_reports=sum(p['reports'] for p in rows),total_found=sum(p['found'] for p in rows),total_indexed=sum(p['indexed'] for p in rows),scope='Projetos descobertos ou registrados; sem mudar associação global do Windows.',limits=[f'HTML interativo até {MAX_REPORT//1_000_000} MB; recursos até {MAX_RESOURCE//1_000_000} MB, conjunto adicional até {MAX_BUNDLE//1_000_000} MB.','Fontes externas e recursos de rede não executam no relatório isolado.'])
    @app.get('/api/files/{fid}')
    def file(fid:str):
        p,root=sources.file(fid)
        if p.suffix.lower() in {'.html','.htm'}:
            content=p.read_text(encoding='utf-8-sig',errors='replace')
            def rewrite(m):
                prefix,quote,value=m.groups()
                if value.startswith(('http:','https:','data:','#','mailto:')): return m.group(0)
                clean_value=value.split('#')[0].split('?')[0]
                from urllib.parse import unquote
                target=(p.parent/unquote(clean_value)).resolve()
                if not target.is_relative_to(p.parent): return prefix+quote+'about:blank'+quote
                a=sources.index_file(target,root)
                return prefix+quote+(a['url'] if a else 'about:blank')+quote
            content=re.sub(r'((?:src|href)\s*=\s*)([\"\'])([^\"\']*)\2',rewrite,content,flags=re.I)
            return HTMLResponse(content,headers={'Content-Security-Policy':"sandbox allow-same-origin; default-src 'none'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https:; font-src 'self' data: https:; media-src 'self'; frame-ancestors 'self'",'X-Frame-Options':'SAMEORIGIN'})
        if p.suffix.lower() in {'.md','.txt'}:
            content=p.read_text(encoding='utf-8-sig',errors='replace')[:500000]
            return HTMLResponse('<meta charset="utf-8"><style>body{font:16px/1.65 system-ui;background:#16151c;color:#e8e5ed;padding:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><pre>'+html.escape(content)+'</pre>',headers={'Content-Security-Policy':"sandbox; default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"})
        return FileResponse(p,media_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream',headers={'Content-Security-Policy':"sandbox; default-src 'none'; frame-ancestors 'self'"})
    @app.get('/api/jobs')
    def jobs(project:str|None=None): return store.jobs_overview(project or None)
    @app.post('/api/jobs/{jid}/cancel')
    def cancel_job(jid:str):
        job=store.job(jid)
        if job['status'] not in {'queued','running'}:return {'job':job}
        job=store.request_cancel(jid)
        from central_jobs import cancel
        cancel(jid)
        return {'job':job}
    @app.get('/api/jobs/{jid}/artifacts/{aid}')
    def job_artifact(jid:str,aid:str):
        from central_artifacts import resolve_artifact
        path,artifact=resolve_artifact(store.job(jid),aid)
        return FileResponse(path,filename=path.name,media_type='application/octet-stream')
    @app.get('/api/jobs/{jid}/view/{aid}')
    def job_text(jid:str,aid:str):
        from central_artifacts import resolve_artifact
        path,artifact=resolve_artifact(store.job(jid),aid)
        content=path.read_text(encoding='utf-8',errors='replace')
        return HTMLResponse('<meta charset="utf-8"><style>body{font:15px/1.65 system-ui;background:#17141d;color:#f3eaf6;padding:24px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>'+html.escape(path.name)+'</h1><pre>'+html.escape(content)+'</pre>',headers={'Content-Security-Policy':"sandbox; default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'",'X-Frame-Options':'SAMEORIGIN'})
    @app.get('/api/jobs/{jid}/preview/{aid}')
    def job_preview(jid:str,aid:str):
        from central_artifacts import resolve_artifact,preview_wrapper,PREVIEW_WRAPPER_HEADERS
        path,artifact=resolve_artifact(store.job(jid),aid)
        if artifact['type']!='html':raise ValueError('Este artefato não oferece prévia interativa.')
        return HTMLResponse(preview_wrapper(jid,aid),headers=PREVIEW_WRAPPER_HEADERS)
    @app.get('/api/jobs/{jid}/render/{aid}')
    def job_render(jid:str,aid:str):
        from central_artifacts import resolve_artifact,isolated_preview,RENDER_HEADERS
        job=store.job(jid);path,artifact=resolve_artifact(job,aid)
        if artifact['type']!='html':raise ValueError('Artefato não é uma interface HTML.')
        return HTMLResponse(isolated_preview(path.read_text(encoding='utf-8',errors='replace'),job,artifact),headers=RENDER_HEADERS)
    @app.get('/api/jobs/{jid}/resources/{aid}')
    def job_resource(jid:str,aid:str):
        from central_artifacts import resolve_artifact,TEXT_TYPES
        path,artifact=resolve_artifact(store.job(jid),aid)
        if path.suffix.lower() not in {'.css','.js','.mjs','.svg'}:raise ValueError('Recurso não permitido na prévia.')
        return FileResponse(path,media_type=TEXT_TYPES[path.suffix.lower()],headers={'Content-Security-Policy':"sandbox; default-src 'none'; frame-ancestors 'self'"})
    @app.post('/api/projects/{pid}/jobs')
    async def create_job(pid:str,r:Request):
        from central_project_control import check
        check(store,pid)
        root=sources.root(pid); b=await r.json(); prompt=b.get('prompt','')
        if not isinstance(prompt,str):raise ValueError('Pedido inválido.')
        prompt=prompt.strip();attachments=resolve_attachments(root,pid,b.get('anexos',[]))
        if len(prompt)>20000 or (not prompt and not attachments): raise ValueError('Escreva um pedido de até 20.000 caracteres ou adicione uma imagem.')
        selected=b.get('selected_paths',[])
        if not isinstance(selected,list) or len(selected)>100 or any(not isinstance(p,str) or len(p)>500 for p in selected):raise ValueError('Seleção de arquivos inválida.')
        route_doc=routing_document(store,pid); route=preview(route_doc['data'],prompt,b.get('category'),b.get('categories'))
        validate_routing(route_doc['data'])
        job,created=store.create_once('jobs',pid,dict(project_id=pid,title=prompt[:120] or 'Pedido com imagem',prompt=prompt,status='queued',stage='Na fila',model=None,output='',updated_at=now(),route=route,route_revision=route_doc['revision'],selected_paths=selected,execution_plan=route['execution_plan'],verification={'status':'pending','summary':'Aguardando execução e provas.'},**attachment_fields(attachments)),*request_identity(r,b))
        def run():
            from central_jobs import execute
            execute(store,sources,job)
        if created: threading.Thread(target=run,daemon=True).start()
        return {'job':job}
    @app.get('/api/guide')
    def guide():
        data=read_json(APP/'guide.json',{'sections':[],'experiments':[],'sources':[]})
        for section in data.get('sections',[]):
            if section.get('image_file'):
                path=(ROOT/section.pop('image_file')).resolve()
                asset=sources.index_file(path,ROOT,'reference') if path.is_relative_to(ROOT) else None
                section['image']=asset['url'] if asset else None
        return data
    @app.get('/api/connection')
    def connection(r:Request):
        info=read_json(APP/'data/connection.json'); url=info.get('remote_url')
        code=secrets.token_urlsafe(32)
        store.pairing_create(code,time.time()+600)
        with auth_lock: qr_pairs[r.cookies.get('mb_session','')]=(code,time.time()+600)
        return dict(remote_url=url,status=info.get('status','Preparando acesso externo'),computer_required=True,pair_url=url+'/#pair='+code if url else None,qr_url='/api/connection/qr' if url else None,platform='Pixel 7 · Android',code=code if url else None,expires_in=600)
    @app.get('/api/quotas')
    def quotas():
        from central_quotas import quota_view
        return dict(quota_view(),local_controls=not remote)
    @app.post('/api/quotas/open-widget')
    async def quota_widget(request:Request):
        if remote:raise HTTPException(403,'A janela do widget abre somente no aplicativo deste computador.')
        from central_quotas import open_widget
        body=await request.json()
        if not isinstance(body,dict) or 'action' not in body or set(body)-{'action','tab'}:raise ValueError('Pedido de cotas inválido.')
        return open_widget(body['action'],body.get('tab',1))
    @app.get('/api/quotas/widget-settings')
    def quota_settings():
        if remote:raise HTTPException(403,'Configure o widget pelo MegaBrain deste computador.')
        from central_quotas import widget_settings
        return widget_settings()
    @app.post('/api/quotas/widget-settings')
    async def quota_settings_save(request:Request):
        if remote:raise HTTPException(403,'Configure o widget pelo MegaBrain deste computador.')
        from central_quotas import request_widget_settings
        body=await request.json()
        if not isinstance(body,dict) or set(body)!={'changes','expected_revision'}:raise ValueError('Pedido de configuração inválido.')
        return request_widget_settings(body['changes'],body['expected_revision'])
    @app.get('/api/quotas/widget-settings/requests/{request_id}')
    def quota_settings_receipt(request_id:str):
        if remote:raise HTTPException(403,'Consulte a aplicação pelo MegaBrain deste computador.')
        from central_quotas import widget_settings_status
        return widget_settings_status(request_id)
    @app.get('/api/connection/qr')
    def qr(r:Request):
        info=read_json(APP/'data/connection.json'); url=info.get('remote_url')
        with auth_lock: code,expires=qr_pairs.get(r.cookies.get('mb_session',''),('',0))
        valid=expires>time.time()
        if not url or not valid: raise HTTPException(404)
        import qrcode
        out=io.BytesIO(); qrcode.make(url+'/#pair='+code).save(out,format='PNG'); return Response(out.getvalue(),media_type='image/png')
    @app.get('/{path:path}')
    def static(path:str):
        if path.startswith('api/'): raise HTTPException(404)
        base=APP/'web/dist'; target=(base/(path or 'index.html')).resolve()
        if not target.is_relative_to(base.resolve()): raise HTTPException(404)
        if path in {'brand.png','icon-192.png','icon-512.png'}:
            target=APP/'assets'/path if (APP/'assets'/path).is_file() else APP/'assets/megabrain-cerebro-rosa.png'
        if not target.is_file():
            if '.' in Path(path).name: raise HTTPException(404)
            target=base/'index.html'
        if not target.is_file(): return HTMLResponse('<h1>MegaBrain</h1><p>A interface está sendo preparada.</p>')
        return FileResponse(target)
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--remote',action='store_true'); args=parser.parse_args()
    import uvicorn
    uvicorn.run(build_app(remote=args.remote),host='127.0.0.1',port=8767 if args.remote else 8766,access_log=False,log_level='warning',proxy_headers=False)
