// Run from web/: node --test scripts/test-reportframe-attachments.cjs
// Executes the current ReportFrame component. Hooks, API and iframe are isolated.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict'),{test}=require('node:test'),ts=require('typescript');
const root=path.join(__dirname,'../src'),A='a'.repeat(64),B='b'.repeat(64),ORIGIN='http://127.0.0.1:8766';
const compile=source=>ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
require.extensions['.ts']=(m,f)=>m._compile(compile(fs.readFileSync(f,'utf8')),f);
const attachments=require(path.join(root,'attachments.ts')),notes=require(path.join(root,'report-notes.ts')),routing=require(path.join(root,'bridge-routing.ts'));
const image={id:'image-1',path:'.mb-anexos/image-1.png',name:'print.png',mime:'image/png',size:100,url:'/api/projects/p1/attachments/image-1'};
const image2={...image,id:'image-2',path:'.mb-anexos/image-2.png',url:'/api/projects/p1/attachments/image-2'};
const plain=value=>JSON.parse(JSON.stringify(value));
function store(){const storage={};Object.defineProperties(storage,{getItem:{value:key=>Object.hasOwn(storage,key)?storage[key]:null},setItem:{value:(key,value)=>{storage[key]=String(value);}},removeItem:{value:key=>{delete storage[key];}}});return storage;}
function nodes(tree){if(!tree||typeof tree!=='object')return [];if(Array.isArray(tree))return tree.flatMap(nodes);return [tree,...nodes(tree.props?.children)];}
function text(tree){if(Array.isArray(tree))return tree.map(text).join('');return typeof tree==='string'||typeof tree==='number'?String(tree):tree&&typeof tree==='object'?text(tree.props?.children):'';}
function deferred(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}

function harness(storage=store()){
  const slots=[],effects=[],calls=[],messages=[],transports=[],listeners=new Map(),timers=new Map(),serverReceived=[];let cursor=0,dirty=true,tree,serial=0,frameVersion=null,frameWindow=null,statusHash=A,feedback=async()=>({}),receiptOverride=null,timerId=0;
  const iframeRefs=new Set();
  const hooks={
    useState(initial){const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return [slots[i],value=>{const next=typeof value==='function'?value(slots[i]):value;if(!Object.is(next,slots[i])){slots[i]=next;dirty=true;}}];},
    useRef(initial){const i=cursor++;if(!(i in slots))slots[i]={current:initial};return slots[i];},
    useEffect(effect,deps){const i=cursor++,previous=slots[i];if(!previous||deps.some((v,k)=>!Object.is(v,previous.deps[k]))){const record={deps,cleanup:undefined};slots[i]=record;effects.push(()=>{previous?.cleanup?.();record.cleanup=effect();});}},
  };
  const Marker=()=>null,RouteMarker=()=>null,bridge={view:null,load:async()=>{},save:async()=>{}};
  class ApiError extends Error{constructor(status,message){super(message);this.status=status;}}
  const api=async(url,method='GET',body,key)=>{calls.push({url,method,body:body&&plain(body),key});if(url.endsWith('/status'))return {hash:statusHash};if(url.includes('/note-receipts?hash=')){const hash=new URL(url,ORIGIN).searchParams.get('hash');return receiptOverride?receiptOverride(hash):{notas:serverReceived.filter(n=>n.versao===hash)};}if(url.endsWith('/feedback')){const reply=await feedback(body);for(const n of body.feedback?.notas||[])serverReceived.push({id:n.id,texto:n.texto||'',versao:body.hash,anexos:n.anexos||[],...(n.rota?{rota:n.rota}:{})});return reply;}if(url.endsWith('/draft'))return {};throw new Error(`Unexpected API ${url}`);};
  class IsolatedCustomEvent{constructor(type,options={}){this.type=type;this.cancelable=!!options.cancelable;this.detail=options.detail;this.defaultPrevented=false;}preventDefault(){if(this.cancelable)this.defaultPrevented=true;}}
  const module={exports:{}},window={location:{origin:ORIGIN},addEventListener:(name,listener)=>{if(!listeners.has(name))listeners.set(name,new Set());listeners.get(name).add(listener);},removeEventListener:(name,listener)=>{listeners.get(name)?.delete(listener);},dispatchEvent:event=>{for(const listener of listeners.get(event.type)||[])listener(event);return !event.defaultPrevented;}};
  const guardModule={exports:{}};vm.runInNewContext(compile(fs.readFileSync(path.join(root,'report-attachment-guard.ts'),'utf8')),{module:guardModule,exports:guardModule.exports,window,CustomEvent:IsolatedCustomEvent});
  vm.runInNewContext(compile(fs.readFileSync(path.join(root,'ReportFrame.tsx'),'utf8')),{module,exports:module.exports,window,localStorage:storage,crypto:{randomUUID:()=>`token-${++serial}`},setInterval:callback=>{const id=++timerId;timers.set(id,callback);return id;},clearInterval:id=>timers.delete(id),require:name=>name==='react'?hooks:name==='./api'?{api,ApiError,mutationKey:(holder,payload)=>{const fingerprint=JSON.stringify(payload);if(holder.current?.fingerprint!==fingerprint)holder.current={fingerprint,key:`mutation-${++serial}`};return holder.current.key;}}:name==='./BridgePanel'?{useBridge:()=>bridge,RouteChoice:RouteMarker}:name==='./AttachmentInput'?{__esModule:true,default:Marker}:name==='./attachments'?attachments:name==='./report-notes'?notes:name==='./bridge-routing'?routing:name==='./report-attachment-guard'?guardModule.exports:name==='./attachment-transport'?{receiveAttachment:async(event,options)=>{transports.push({event,options});return false;}}:require(name)});
  const props={fid:'report-1',title:'Relatório isolado',projectId:'p1'};
  const render=()=>{
    cursor=0;dirty=false;tree=module.exports.default(props);
    for(const ref of iframeRefs)ref.current=null;iframeRefs.clear();
    for(const node of nodes(tree))if(node.type==='iframe'){
      if(frameVersion!==node.key){frameVersion=node.key;frameWindow={postMessage:(message,origin)=>messages.push({message:plain(message),origin})};}
      node.props.ref.current={contentWindow:frameWindow};iframeRefs.add(node.props.ref);
    }
    for(const effect of effects.splice(0))effect();return tree;
  };
  const settle=async()=>{for(let i=0;i<30;i++){if(dirty)render();await Promise.resolve();}if(dirty)render();};
  render();
  const h={storage,calls,messages,transports,settle,setBridge:value=>{bridge.view=value;dirty=true;},get routeChoice(){return nodes(this.tree).find(n=>n.type===RouteMarker);},mayClose:guardModule.exports.mayCloseReport,setFeedback:callback=>{feedback=callback;},setReceipts:callback=>{receiptOverride=callback;},setStatus:hash=>{statusHash=hash;},tick(){for(const callback of [...timers.values()])callback();},get tree(){if(dirty)render();return tree;},get input(){return nodes(this.tree).find(n=>n.type==='textarea');},get attachments(){return nodes(this.tree).find(n=>n.type===Marker);},get iframe(){return nodes(this.tree).find(n=>n.type==='iframe');},get token(){return new URL(this.iframe.props.src,ORIGIN).searchParams.get('ticket');},get source(){return frameWindow;},button(label){return nodes(this.tree).find(n=>n.type==='button'&&text(n)===label);},async emit(data,extra={}){const event={data,source:frameWindow,origin:ORIGIN,...extra};await Promise.all([...(listeners.get('message')||[])].map(listener=>listener(event)));await settle();return event;},async report(kind,hash=A,payload){return this.emit({channel:'megabrain-report',fid:props.fid,token:this.token,hash,kind,payload});},async ready(hash=A){await settle();await this.report('ready',hash);},get posts(){return calls.filter(c=>c.method==='POST'&&c.url.endsWith('/feedback'));}};
  return h;
}

test('textbox usa AttachmentInput e só imagem envia corpo com hash/refs corretos',async()=>{
  const h=harness();await h.ready();assert.equal(h.input.props['aria-label'],'Comentário sobre Relatório isolado');assert.equal(h.attachments.props.pid,'p1');assert.equal(h.attachments.props.children,h.input);
  h.attachments.props.onChange([image]);await h.settle();assert.equal(h.button('Enviar ao projeto').props.disabled,false);h.button('Enviar ao projeto').props.onClick();await h.settle();
  assert.equal(h.posts.length,1);assert.deepEqual(h.posts[0].body,{hash:A,feedback:null,note:'',anexos:[image]});assert.ok(h.posts[0].key);assert.equal(h.attachments.props.value.length,0);assert.doesNotMatch(JSON.stringify(h.posts[0].body),/base64|data:image/);
});

test('destino por comentário persiste na falha, é enviado e só limpa após sucesso',async()=>{
 const route={vendor:'gpt',modelo:'gpt-6.1-sol',effort:'xhigh'},storage=store(),h=harness(storage);
 h.setBridge({revision:1,data:{auto:true,vendor:'gpt',pipeline:{planejador:route}},vendors:[{id:'gpt',nome:'Codex',ativo:true}],catalogo:[{vendor:'gpt',modelos:[{id:route.modelo,nome:'Sol 6.1',efforts:['high','xhigh']}]}]});
 await h.ready();h.input.props.onChange({target:{value:'Ajuste neste destino'}});h.routeChoice.props.onChange(route);await h.settle();
 assert.equal(JSON.parse(storage.getItem('mb-report-route:report-1')).modelo,route.modelo);
 const bridgeMessage=h.messages.find(m=>m.message.channel==='megabrain-report-bridge');assert.ok(bridgeMessage);assert.equal(bridgeMessage.message.hash,A);assert.equal(bridgeMessage.message.token,h.token);
 h.setFeedback(async()=>{throw new Error('Offline');});h.button('Enviar ao projeto').props.onClick();await h.settle();
 assert.deepEqual(h.posts[0].body.rota,route);assert.equal(h.routeChoice.props.value.modelo,route.modelo);
 h.setFeedback(async()=>({}));h.button('Enviar ao projeto').props.onClick();await h.settle();
 assert.deepEqual(h.posts[1].body.rota,route);assert.equal(h.posts[0].key,h.posts[1].key);assert.equal(h.routeChoice.props.value,undefined);assert.equal(storage.getItem('mb-report-route:report-1'),null);
});

test('falha mantém texto e refs no rascunho local e recupera na reabertura',async()=>{
  const storage=store(),h=harness(storage);await h.ready();h.input.props.onChange({target:{value:'Mudar a margem'}});h.attachments.props.onChange([image]);await h.settle();h.setFeedback(async()=>{throw new Error('Falha de rede isolada');});h.button('Enviar ao projeto').props.onClick();await h.settle();
  assert.equal(h.input.props.value,'Mudar a margem');assert.deepEqual(plain(h.attachments.props.value),[image]);assert.match(text(h.tree),/Falha de rede isolada/);assert.equal(storage.getItem(`mb-report-note:report-1:${A}`),'Mudar a margem');assert.deepEqual(JSON.parse(storage.getItem(`mb-report-attachments:report-1:${A}`)),[image]);
  const reopened=harness(storage);await reopened.ready();assert.equal(reopened.input.props.value,'Mudar a margem');assert.deepEqual(plain(reopened.attachments.props.value),[image]);assert.doesNotMatch(JSON.stringify(storage),/data:image|base64/);
});

test('sucesso limpa o snapshot enviado e preserva edição/refs que chegaram durante a resposta',async()=>{
  const wait=deferred(),h=harness();await h.ready();h.input.props.onChange({target:{value:'Texto enviado'}});h.attachments.props.onChange([image]);await h.settle();h.setFeedback(()=>wait.promise);h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.posts.length,1);assert.equal(h.input.props.disabled,true);
  // Model an external draft update while the request is pending (the UI itself is disabled).
  h.input.props.onChange({target:{value:'Texto novo'}});h.attachments.props.onChange([image2]);await h.settle();wait.resolve({});await h.settle();
  assert.deepEqual(h.posts[0].body.anexos,[image]);assert.equal(h.posts[0].body.note,'Texto enviado');assert.equal(h.input.props.value,'Texto novo');assert.deepEqual(plain(h.attachments.props.value),[image2]);assert.equal(h.storage.getItem(`mb-report-note:report-1:${A}`),'Texto novo');
  h.setFeedback(async()=>({}));h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.input.props.value,'');assert.equal(h.attachments.props.value.length,0);
});

test('upload local ou do iframe bloqueia envio e abertura da nova versão',async()=>{
  const h=harness();await h.ready();h.attachments.props.onChange([image]);h.attachments.props.onBusyChange(true);await h.settle();h.setStatus(B);h.tick();await h.settle();const ticket=h.token;
  assert.equal(h.button('Enviar ao projeto').props.disabled,true);h.button('Enviar ao projeto').props.onClick();h.button('Abrir versão nova').props.onClick();await h.settle();assert.equal(h.posts.length,0);assert.equal(h.token,ticket);assert.match(text(h.tree),/Aguarde o envio dos prints/);
  h.attachments.props.onBusyChange(false);await h.settle();const pending=h.transports.at(-1).options.pending;pending.add('iframe-upload');h.button('Enviar ao projeto').props.onClick();h.button('Abrir versão nova').props.onClick();await h.settle();assert.equal(h.posts.length,0);assert.equal(h.token,ticket);pending.clear();
});

test('carry ao abrir versão nova conserva texto e refs e troca token/hash do contexto',async()=>{
  const h=harness();await h.ready();h.input.props.onChange({target:{value:'Levar rascunho'}});h.attachments.props.onChange([image]);await h.settle();const previousToken=h.token;h.setStatus(B);h.tick();await h.settle();h.button('Abrir versão nova').props.onClick();await h.settle();assert.notEqual(h.token,previousToken);await h.ready(B);
  assert.equal(h.input.props.value,'Levar rascunho');assert.deepEqual(plain(h.attachments.props.value),[image]);assert.deepEqual(JSON.parse(h.storage.getItem(`mb-report-attachments:report-1:${B}`)),[image]);h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.posts[0].body.hash,B);assert.deepEqual(h.posts[0].body.anexos,[image]);
});

test('transporte recebe source/origin/fid/token/pid/hash atuais e invalida closure após refresh',async()=>{
  const h=harness();await h.ready();const event=await h.emit({channel:'megabrain-attachment',operation:'upload',requestId:'isolated'}),call=h.transports.at(-1),options=call.options;
  assert.equal(call.event,event);assert.equal(options.source,h.source);assert.equal(options.origin,ORIGIN);assert.equal(options.fid,'report-1');assert.equal(options.pid,'p1');assert.equal(options.hash,A);assert.equal(options.token,h.token);assert.equal(options.current(),true);
  options.reply({channel:'isolated-reply'});assert.deepEqual(h.messages.at(-1),{message:{channel:'isolated-reply'},origin:ORIGIN});
  h.setStatus(B);h.tick();await h.settle();h.button('Abrir versão nova').props.onClick();await h.settle();assert.equal(options.current(),false);await h.ready(B);await h.emit({channel:'megabrain-attachment',requestId:'new'});assert.equal(h.transports.at(-1).options.hash,B);assert.equal(h.transports.at(-1).options.token,h.token);
});

test('mensagem normal de relatório com origem/token/fid/source inválidos não cria feedback',async()=>{
  const h=harness();await h.ready();const payload={kind:'notes',completa:true,notas:[{id:'invalid',texto:'',anexos:[image]}],enviar:['invalid']};
  const data={channel:'megabrain-report',kind:'feedback',hash:A,fid:'report-1',token:h.token,payload};
  for(const [bad,extra] of [[{...data,token:'wrong'},{}],[{...data,fid:'wrong'},{}],[{...data,hash:'invalid'},{}],[data,{origin:'https://invalid.example'}],[data,{source:{}}]])await h.emit(bad,extra);
  assert.equal(h.posts.length,0);
});

test('ACK conserva refs de nota só imagem e nova imagem no mesmo id envia novamente',async()=>{
  const h=harness();await h.ready();const payload=image=>({kind:'notes',completa:true,notas:[{id:'n1',texto:'',anexos:[image]}],enviar:['n1']});await h.report('feedback',A,payload(image));
  assert.equal(h.posts.length,1);assert.deepEqual(h.posts[0].body.feedback.notas[0].anexos,[image]);const ack=h.messages.find(m=>m.message.channel==='megabrain-report-ack');assert.equal(ack.origin,ORIGIN);assert.equal(ack.message.ok,true);assert.equal(ack.message.token,h.token);assert.deepEqual(ack.message.notas,[{id:'n1',texto:'',anexos:[image]}]);
  await h.report('feedback',A,payload(image2));assert.equal(h.posts.length,2);assert.deepEqual(h.posts[1].body.feedback.notas[0].anexos,[image2]);assert.notEqual(h.posts[0].key,h.posts[1].key);
});

test('ACK de falha conserva refs e nota pendente para retry',async()=>{
  const h=harness();await h.ready();h.setFeedback(async()=>{throw new Error('Feedback isolado falhou');});await h.report('feedback',A,{kind:'notes',completa:true,notas:[{id:'n-fail',texto:'',anexos:[image]}],enviar:['n-fail']});
  const ack=h.messages.find(m=>m.message.channel==='megabrain-report-ack');assert.equal(ack.message.ok,false);assert.deepEqual(ack.message.notas,[{id:'n-fail',texto:'',anexos:[image]}]);assert.deepEqual(JSON.parse(h.storage.getItem(`mb-report-feedback:report-1:${A}`)).notas[0].anexos,[image]);assert.match(text(h.tree),/1 nota não enviada/);
});

test('merge de 4+4 refs conserva oito; primeiro POST envia seis e mantém duas no draft',async()=>{
  const images=Array.from({length:8},(_,i)=>({...image,id:`merge-${i}`,path:`.mb-anexos/merge-${i}.png`,url:`/api/projects/p1/attachments/merge-${i}`}));
  const storage=store();storage.setItem(`mb-report-attachments:report-1:${B}`,JSON.stringify(images.slice(4)));
  const h=harness(storage);await h.ready();h.attachments.props.onChange(images.slice(0,4));await h.settle();h.setStatus(B);h.tick();await h.settle();h.button('Abrir versão nova').props.onClick();await h.settle();await h.ready(B);
  assert.equal(h.attachments.props.value.length,8);assert.deepEqual(new Set(h.attachments.props.value.map(a=>a.id)),new Set(images.map(a=>a.id)));assert.equal(JSON.parse(storage.getItem(`mb-report-attachments:report-1:${B}`)).length,8);assert.match(text(h.tree),/8 prints guardados/);
  const merged=plain(h.attachments.props.value);h.button('Enviar ao projeto').props.onClick();await h.settle();assert.deepEqual(h.posts[0].body.anexos,merged.slice(0,6));assert.deepEqual(plain(h.attachments.props.value),merged.slice(6));assert.deepEqual(JSON.parse(storage.getItem(`mb-report-attachments:report-1:${B}`)),merged.slice(6));assert.match(text(h.tree),/prints restantes continuam/);
  h.button('Enviar ao projeto').props.onClick();await h.settle();assert.deepEqual(h.posts[1].body.anexos,merged.slice(6));assert.equal(h.attachments.props.value.length,0);assert.equal(h.posts.flatMap(p=>p.body.anexos).length,8);
});

test('refresh não muda token/iframe durante comentário, flush de nota ou decisão em envio',async()=>{
  for(const mode of ['comment','note','decision']){
    const wait=deferred(),h=harness();await h.ready();h.setStatus(B);h.tick();await h.settle();const token=h.token,source=h.source;h.setFeedback(()=>wait.promise);
    if(mode==='comment'){h.input.props.onChange({target:{value:'Aguardar resposta'}});await h.settle();h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.button('Abrir versão nova').props.disabled,true);}
    if(mode==='note')await h.report('feedback',A,{kind:'notes',completa:true,notas:[{id:'busy-note',texto:'',anexos:[image]}],enviar:['busy-note']});
    if(mode==='decision')await h.report('feedback',A,{kind:'decisions',finalizado:true,respostas:[{id:'q',texto:'Escolha',anexos:[image]}]});
    assert.equal(h.posts.length,1,mode);h.button('Abrir versão nova').props.onClick();await h.settle();assert.equal(h.token,token,mode);assert.equal(h.source,source,mode);assert.match(text(h.tree),/Aguarde o envio antes de abrir a versão nova/);
    wait.resolve({});await h.settle();h.button('Abrir versão nova').props.onClick();await h.settle();assert.notEqual(h.token,token,mode);
  }
});

test('mayCloseReport cancela somente pid/fid atual e permite fechar após concluir upload local',async()=>{
  const h=harness();await h.ready();assert.equal(h.mayClose('p1','report-1'),true);h.attachments.props.onBusyChange(true);await h.settle();
  assert.equal(h.mayClose('p-other','report-1'),true);assert.equal(h.mayClose('p1','report-other'),true);assert.equal(h.mayClose('p1','report-1'),false);assert.equal(h.mayClose('p1'),false);await h.settle();assert.match(text(h.tree),/rascunho continua aqui/);
  h.attachments.props.onBusyChange(false);await h.settle();assert.equal(h.mayClose('p1','report-1'),true);assert.equal(h.mayClose('p1'),true);
});

test('estado canônico de upload falho bloqueia close/envio/refresh sem host upload pendente e libera blocked:false',async()=>{
  const h=harness();await h.ready();h.attachments.props.onChange([image]);await h.settle();await h.report('attachment-state',A,{blocked:true,pending:0,failed:1});assert.equal(h.transports.at(-1).options.pending.size,0);assert.equal(h.mayClose('p1','report-1'),false);
  h.setStatus(B);h.tick();await h.settle();const token=h.token;h.button('Enviar ao projeto').props.onClick();h.button('Abrir versão nova').props.onClick();await h.settle();assert.equal(h.posts.length,0);assert.equal(h.token,token);
  await h.report('attachment-state',A,{blocked:false,pending:0,failed:0});assert.equal(h.mayClose('p1','report-1'),true);h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.posts.length,1);
});

test('attachment-state com origem/source/token/fid inválidos não ativa nem remove bloqueio',async()=>{
  const h=harness();await h.ready();const state=blocked=>({channel:'megabrain-report',kind:'attachment-state',hash:A,fid:'report-1',token:h.token,payload:{blocked}});
  const invalid=(data)=>[[{...data,token:'wrong'},{}],[{...data,fid:'wrong'},{}],[data,{origin:'https://invalid.example'}],[data,{source:{}}]];
  for(const [data,extra] of invalid(state(true)))await h.emit(data,extra);assert.equal(h.mayClose('p1','report-1'),true);
  await h.report('attachment-state',A,{blocked:true});for(const [data,extra] of invalid(state(false)))await h.emit(data,extra);assert.equal(h.mayClose('p1','report-1'),false);
  await h.report('attachment-state',A,{blocked:false});assert.equal(h.mayClose('p1','report-1'),true);
});

test('attachment-state de hash divergente não muda bloqueio nem versão do próximo POST',async()=>{
  const h=harness();await h.ready(A);await h.report('attachment-state',B,{blocked:true});assert.equal(h.mayClose('p1','report-1'),true);h.attachments.props.onChange([image]);await h.settle();h.button('Enviar ao projeto').props.onClick();await h.settle();assert.equal(h.posts.length,1);assert.equal(h.posts[0].body.hash,A);
});

test('close bloqueia também POST de comentário/nota/decisão e volta após confirmação',async()=>{
  for(const mode of ['comment','note','decision']){
    const wait=deferred(),h=harness();await h.ready();h.setFeedback(()=>wait.promise);
    if(mode==='comment'){h.input.props.onChange({target:{value:'Comentário'}});await h.settle();h.button('Enviar ao projeto').props.onClick();await h.settle();}
    if(mode==='note')await h.report('feedback',A,{kind:'notes',completa:true,notas:[{id:'closing',texto:'',anexos:[image]}],enviar:['closing']});
    if(mode==='decision')await h.report('feedback',A,{kind:'decisions',finalizado:true,respostas:[{id:'q',texto:'Escolha'}]});
    assert.equal(h.mayClose('p1','report-1'),false,mode);assert.equal(h.mayClose('p1','other'),true,mode);wait.resolve({});await h.settle();assert.equal(h.mayClose('p1','report-1'),true,mode);
  }
});

function appClosingHarness(){
  const source=fs.readFileSync(path.join(root,'App.tsx'),'utf8'),ast=ts.createSourceFile('App.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX),app=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='App');
  const wanted=['closePreview','closePanel'],functions=app.body.statements.filter(s=>ts.isFunctionDeclaration(s)&&wanted.includes(s.name?.text)).map(s=>s.getText(ast));assert.equal(functions.length,2);
  const guardCalls=[],notices=[],env={allowed:true,visible:true,workspace:{panels:[{key:'r',kind:'report',project_id:'p1',ref:'report-1'},{key:'p',kind:'project',project_id:'p1'},{key:'m',kind:'module',project_id:'p1'}]},previewsRef:{current:[{id:'report-1',project_id:'p1'},{id:'report-2',project_id:'p2'}]},reportKey:p=>p.project_id+':'+p.id,mayCloseReport:(pid,fid)=>{guardCalls.push({pid,fid});return env.allowed;},notify:message=>notices.push(message),setResponsesVisible:value=>{env.visible=value;},setPreviews:updater=>{env.previewsRef.current=updater(env.previewsRef.current);},readPanels:workspace=>workspace.panels,removePanel:(workspace,key)=>({...workspace,panels:workspace.panels.filter(p=>p.key!==key)}),updateWorkspace:updater=>{env.workspace=updater(env.workspace);env.workspaceRef.current.data=env.workspace;}};
  env.workspaceRef={current:{data:env.workspace}};vm.runInNewContext(compile(functions.join('\n')+'\nglobalThis.actions={closePreview,closePanel};'),env);return {env,actions:env.actions,guardCalls,notices};
}

test('App fecha relatório/painel sem pendência e conserva quando guard recusa',()=>{
  const h=appClosingHarness();h.env.allowed=false;h.actions.closePreview('p1:report-1');assert.equal(h.env.previewsRef.current.length,2);assert.deepEqual(h.guardCalls.at(-1),{pid:'p1',fid:'report-1'});h.actions.closePanel('r');assert.equal(h.env.workspace.panels.length,3);
  h.env.allowed=true;h.actions.closePreview('p1:report-1');assert.equal(h.env.previewsRef.current.length,1);h.actions.closePanel('r');assert.equal(h.env.workspace.panels.length,2);h.actions.closePanel('p');assert.deepEqual(h.guardCalls.at(-1),{pid:'p1',fid:undefined});assert.equal(h.env.workspace.panels.length,1);
});

test('App collapse só oculta sem desmontar relatório nem consultar guard; módulo sem relatório não bloqueia',()=>{
  const h=appClosingHarness();h.env.allowed=false;h.actions.closePreview();assert.equal(h.env.visible,false);assert.equal(h.env.previewsRef.current.length,2);assert.equal(h.guardCalls.length,0);h.actions.closePanel('m');assert.equal(h.env.workspace.panels.length,2);assert.equal(h.guardCalls.length,0);
});

test('outro perfil usa recibos do servidor e não repete nota nem seu texto dentro da decisão',async()=>{
  const h=harness();await h.ready();h.setReceipts(async hash=>({notas:[{id:'restored',texto:'Nota já recebida',versao:hash,anexos:[image]}]}));
  await h.report('feedback',A,{kind:'decisions',finalizado:true,respostas:{q:{valor:'sim'}},notas:[{id:'restored',texto:'Nota já recebida',anexos:[image],n:999}],resumo_texto:'Pergunta → Sim\n\nNOTAS NA PÁGINA\n999. Nota já recebida',resumo_respostas:'Pergunta → Sim'});
  assert.equal(h.posts.length,1);assert.deepEqual(h.posts[0].body.feedback.notas,[]);assert.equal(h.posts[0].body.feedback.resumo_texto,'Pergunta → Sim');assert.match(h.posts[0].body.feedback.resumo_texto_original,/Nota já recebida/);assert.ok(h.calls.some(c=>c.url===`/reports/report-1/note-receipts?hash=${A}`));
});
test('flush de nota restaurada renumerada confirma sem POST; texto, imagem ou versão editados continuam enviáveis',async()=>{
  const h=harness();await h.ready();h.setReceipts(async hash=>({notas:hash===A?[{id:'restored',texto:'Recebida',versao:A,anexos:[image]}]:[]}));
  const send=(texto,anexos,hash=A)=>h.report('feedback',hash,{kind:'notes',completa:true,notas:[{id:'restored',texto,anexos,n:999,ancora:{base:'#igual',idx:[]}}],enviar:['restored']});
  await send('Recebida',[image]);assert.equal(h.posts.length,0);assert.ok(h.messages.some(m=>m.message.ok&&m.message.message==='Nota já recebida no projeto ✓'));
  await send('Editada',[image]);assert.equal(h.posts.length,1);await send('Recebida',[image2]);assert.equal(h.posts.length,2);
  h.setStatus(B);h.tick();await h.settle();h.button('Abrir versão nova').props.onClick();await h.settle();await h.ready(B);await send('Recebida',[image],B);assert.equal(h.posts.length,3);assert.equal(h.posts[2].body.hash,B);
});
test('falha ao consultar recibos mantém notas e decisões sem POST e permite tentativa posterior',async()=>{
  const h=harness();await h.ready();h.setReceipts(async()=>{throw new Error('Consulta de recibos indisponível');});
  await h.report('feedback',A,{kind:'notes',completa:true,notas:[{id:'waiting',texto:'Preservar',anexos:[image]}],enviar:['waiting']});
  assert.equal(h.posts.length,0);assert.match(text(h.tree),/Consulta de recibos indisponível/);assert.ok(h.storage.getItem(`mb-report-feedback:report-1:${A}`).includes('waiting'));
  await h.report('feedback',A,{kind:'decisions',finalizado:true,respostas:{q:{valor:'sim'}},notas:[{id:'waiting',texto:'Preservar',anexos:[image]}]});assert.equal(h.posts.length,0);
  h.setReceipts(null);h.button('tentar de novo').props.onClick();await h.settle();assert.equal(h.posts.length,2);assert.deepEqual(h.posts[1].body.feedback.notas,[]);
});
test('decisão espera flush pendente, relê recibos e protege duplo clique',async()=>{
  const wait=deferred(),h=harness();await h.ready();h.setFeedback(body=>body.feedback?.kind==='notes'?wait.promise:Promise.resolve({}));
  const note={id:'in-flight',texto:'Salva antes da decisão',anexos:[image]};
  await h.report('feedback',A,{kind:'notes',completa:true,notas:[note],enviar:['in-flight']});assert.equal(h.posts.length,1);
  const decision={kind:'decisions',finalizado:true,respostas:{q:{valor:'sim'}},notas:[note],resumo_texto:'Resposta\n\nNOTAS NA PÁGINA\n1. Salva antes da decisão'};
  await h.report('feedback',A,decision);await h.report('feedback',A,{...decision});assert.equal(h.posts.length,1);
  wait.resolve({});await h.settle();assert.equal(h.posts.length,2);assert.equal(h.posts[1].body.feedback.kind,'decisions');assert.deepEqual(h.posts[1].body.feedback.notas,[]);assert.equal(h.storage.getItem(`mb-report-feedback:report-1:${A}`),null);
});
