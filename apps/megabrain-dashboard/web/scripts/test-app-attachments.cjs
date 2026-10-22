// Run from web/: node --test scripts/test-app-attachments.cjs
// Component handlers run against an isolated hook harness; no production API/storage.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict'),{test}=require('node:test'),ts=require('typescript');
const root=path.join(__dirname,'../src');
const compile=source=>ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
require.extensions['.ts']=(m,f)=>m._compile(compile(fs.readFileSync(f,'utf8')),f);
const {normalizeAttachments}=require(path.join(root,'attachments.ts'));
const attachment={id:'print-1',path:'.mb-anexos/print-1.png',name:'print.png',mime:'image/png',size:1024,url:'/api/projects/p1/attachments/print-1'};
const second={...attachment,id:'print-2',path:'.mb-anexos/print-2.png',url:'/api/projects/p1/attachments/print-2'};
const storage=()=>{const items=new Map();return {getItem:key=>items.get(key)||null,setItem:(key,value)=>items.set(key,String(value)),removeItem:key=>items.delete(key),items};};
function nodes(tree){if(!tree||typeof tree!=='object')return [];if(Array.isArray(tree))return tree.flatMap(nodes);return [tree,...nodes(tree.props?.children)];}
function text(tree){if(Array.isArray(tree))return tree.map(text).join('');return typeof tree==='string'?tree:tree&&typeof tree==='object'?text(tree.props?.children):'';}

function analysisHarness(store=storage()){
  const slots=[],effects=[],calls=[],errors=[],started=[],busyChanges=[];let cursor=0,dirty=true,tree,failJobs=false;
  const hooks={
    useState(initial){const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return [slots[i],value=>{const next=typeof value==='function'?value(slots[i]):value;if(!Object.is(next,slots[i])){slots[i]=next;dirty=true;}}];},
    useRef(initial){const i=cursor++;if(!(i in slots))slots[i]={current:initial};return slots[i];},
    useEffect(effect,deps){const i=cursor++;if(!(i in slots)||deps.some((v,k)=>!Object.is(v,slots[i][k]))){slots[i]=deps;effects.push(effect);}},
  };
  const Marker=()=>null;
  const api=async(url,method,body)=>{calls.push({url,method,body:body&&JSON.parse(JSON.stringify(body))});if(url.endsWith('/routing'))return {data:{routes:[]}};if(url.endsWith('/route-preview'))return {title:'Plano',stages:[],reason:'Conferido'};if(url.endsWith('/jobs')){if(failJobs)throw new Error('Falha isolada no envio');return {job:{id:'job-1'}};}throw new Error(`API inesperada ${url}`);};
  const module={exports:{}};
  vm.runInNewContext(compile(fs.readFileSync(path.join(root,'AnalysisForm.tsx'),'utf8')),{module,exports:module.exports,localStorage:store,require:name=>name==='react'?hooks:name==='./api'?{api,mutationKey:()=> 'isolated-key'}:name==='./attachments'?{normalizeAttachments}:name==='./AttachmentInput'?{__esModule:true,default:Marker}:name.startsWith('./')?{}:require(name)});
  const props={pid:'p1',projectName:'Isolado',onClose:()=>{},onError:e=>errors.push(e.message),onStarted:job=>started.push(job),onBusyChange:b=>busyChanges.push(b)};
  const render=()=>{cursor=0;dirty=false;tree=module.exports.default(props);for(const e of effects.splice(0))e();return tree;};
  const settle=async()=>{for(let i=0;i<8;i++){if(dirty)render();await Promise.resolve();}if(dirty)render();};
  render();
  return {calls,errors,started,busyChanges,store,settle,failJobs:()=>{failJobs=true;},get tree(){if(dirty)render();return tree;},get input(){return nodes(this.tree).find(n=>n.type==='textarea'&&n.props.id==='new-prompt');},get attachments(){return nodes(this.tree).find(n=>n.type===Marker);},button(label){return nodes(this.tree).find(n=>n.type==='button'&&text(n)===label);}};
}

test('Novo pedido permite só imagem e transporta refs no plano e na execução',async()=>{
  const h=analysisHarness();await h.settle();
  assert.equal(h.button('Ver plano e ferramentas').props.disabled,true);
  h.attachments.props.onChange([attachment]);await h.settle();
  assert.equal(h.button('Ver plano e ferramentas').props.disabled,false);
  h.button('Ver plano e ferramentas').props.onClick();await h.settle();
  assert.equal(h.button('Executar pedido').props.disabled,false);
  h.button('Executar pedido').props.onClick();await h.settle();
  const sent=h.calls.filter(c=>c.method==='POST');assert.equal(sent.length,2);
  for(const c of sent){assert.equal(c.body.prompt,'');assert.deepEqual(c.body.anexos,[attachment]);assert.doesNotMatch(JSON.stringify(c.body),/base64|data:image/);}
  assert.equal(h.started.length,1);assert.equal(h.store.getItem('mb-analysis-draft:p1'),null);
});

test('upload pendente bloqueia os botões e os handlers de plano/execução',async()=>{
  const h=analysisHarness();await h.settle();h.attachments.props.onChange([attachment]);await h.settle();h.button('Ver plano e ferramentas').props.onClick();await h.settle();
  const before=h.calls.length;h.attachments.props.onBusyChange(true);await h.settle();
  assert.equal(h.button('Ver plano e ferramentas').props.disabled,true);assert.equal(h.button('Executar pedido').props.disabled,true);assert.equal(h.button('Cancelar').props.disabled,true);
  h.button('Ver plano e ferramentas').props.onClick();h.button('Executar pedido').props.onClick();await h.settle();assert.equal(h.calls.length,before);assert.equal(h.busyChanges.at(-1),true);
});

test('Novo pedido preserva texto, anexos e rascunho após falha e reabertura',async()=>{
  const store=storage(),h=analysisHarness(store);await h.settle();h.input.props.onChange({target:{value:'Revisar estes prints'}});h.attachments.props.onChange([attachment]);await h.settle();
  h.button('Ver plano e ferramentas').props.onClick();await h.settle();h.failJobs();h.button('Executar pedido').props.onClick();await h.settle();
  assert.match(h.errors.at(-1),/Falha isolada/);assert.equal(h.input.props.value,'Revisar estes prints');assert.deepEqual(h.attachments.props.value,[attachment]);
  const reopened=analysisHarness(store);await reopened.settle();assert.equal(reopened.input.props.value,'Revisar estes prints');assert.deepEqual(reopened.attachments.props.value,[attachment]);
  assert.doesNotMatch(store.getItem('mb-analysis-draft:p1'),/data:image|base64/);
});

test('mudar somente a imagem invalida o plano; remover mantém texto e o draft',async()=>{
  const h=analysisHarness();await h.settle();h.input.props.onChange({target:{value:'Texto mantido'}});h.attachments.props.onChange([attachment]);await h.settle();h.button('Ver plano e ferramentas').props.onClick();await h.settle();
  assert.equal(h.button('Executar pedido').props.disabled,false);h.attachments.props.onChange([second]);await h.settle();assert.equal(h.button('Executar pedido').props.disabled,true);
  h.attachments.props.onChange([]);await h.settle();assert.equal(h.input.props.value,'Texto mantido');assert.deepEqual(JSON.parse(h.store.getItem('mb-analysis-draft:p1')).anexos,[]);
});

function commentHarness(){
  const source=fs.readFileSync(path.join(root,'App.tsx'),'utf8'),ast=ts.createSourceFile('App.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
  const app=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='App');
  const wanted=['beginComment','rememberCommentDraft','closeComment','closeJobForm','postComment'];
  const extracted=app.body.statements.filter(s=>ts.isFunctionDeclaration(s)&&wanted.includes(s.name?.text)).map(s=>s.getText(ast));
  const helpers=ast.statements.filter(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='readModuleDraft'||ts.isVariableStatement(s)&&s.declarationList.declarations.some(d=>d.name.getText(ast)==='moduleDraftKey')).map(s=>s.getText(ast));
  assert.equal(extracted.length,wanted.length);
  const localStorage=storage(),calls=[],errors=[],notices=[];
  const env={localStorage,normalizeAttachments,readRoute:require('../src/bridge-routing.ts').readRoute,commentRoute:undefined,commentRouteIssue:'',setCommentRoute:value=>{env.commentRoute=value;},setCommentRouteIssue:value=>{env.commentRouteIssue=value;},comment:{pid:'p1',target:'module:now',label:'Agora',anchor:{x:.5,y:.1}},commentText:'',commentAttachments:[],commentBusy:false,commentAttachmentBusy:false,jobFormBusy:false,commentDrafts:{current:{}},commentRequest:{current:null},api:async(url,method,body,key)=>{calls.push({url,method,body,key});if(env.fail)throw new Error('Falha isolada no comentário');},mutationKey:()=> 'comment-key',notify:message=>notices.push(message),loadDetail:async()=>{},onError:error=>errors.push(error.message),setComment:value=>{env.comment=value;},setCommentText:value=>{env.commentText=value;},setCommentAttachments:value=>{env.commentAttachments=value;},setCommentBusy:value=>{env.commentBusy=value;},setCommentAttachmentBusy:value=>{env.commentAttachmentBusy=value;},setJobProject:value=>{env.jobProject=value;}};
  vm.runInNewContext(compile(helpers.join('\n')+'\n'+extracted.join('\n')+'\nglobalThis.actions={'+wanted.join(',')+'};'),env);
  return {env,calls,errors,notices,store:localStorage,actions:env.actions};
}

test('comentário do módulo salva só imagem com alvo/âncora e limpa somente após confirmação',async()=>{
  const h=commentHarness();h.env.commentAttachments=[attachment];h.actions.rememberCommentDraft('',[attachment]);await h.actions.postComment();
  assert.equal(h.calls.length,1);assert.equal(h.calls[0].body.text,'');assert.equal(h.calls[0].body.target,'module:now');assert.deepEqual(h.calls[0].body.anchor,{x:.5,y:.1});assert.deepEqual(h.calls[0].body.anexos,[attachment]);
  assert.equal(h.env.commentText,'');assert.equal(h.env.commentAttachments.length,0);assert.equal(h.store.items.size,0);
});

test('comentário falho mantém o rascunho recuperável por projeto/alvo',async()=>{
  const h=commentHarness(),ctx=h.env.comment;h.env.commentText='Ajustar margem';h.env.commentAttachments=[attachment];h.actions.rememberCommentDraft(h.env.commentText,[attachment]);h.env.fail=true;await h.actions.postComment();
  assert.equal(h.env.commentText,'Ajustar margem');assert.equal(h.env.commentAttachments.length,1);assert.equal(h.errors.length,1);
  h.env.commentDrafts.current={};h.env.commentText='';h.env.commentAttachments=[];h.actions.beginComment(ctx);assert.equal(h.env.commentText,'Ajustar margem');assert.equal(h.env.commentAttachments[0].id,attachment.id);
  h.actions.beginComment({...ctx,target:'module:other'});assert.equal(h.env.commentText,'');assert.equal(h.env.commentAttachments.length,0);
});

test('comentário com upload pendente impede envio e fechamento',async()=>{
  const h=commentHarness(),ctx=h.env.comment;h.env.commentText='Texto';h.env.commentAttachments=[attachment];h.env.commentAttachmentBusy=true;await h.actions.postComment();h.actions.closeComment();assert.equal(h.calls.length,0);assert.equal(h.env.comment,ctx);
  h.env.commentAttachmentBusy=false;h.actions.closeComment();assert.equal(h.env.comment,null);
});

test('App conecta paste/chooser ao campo do módulo e mantém nova cópia concorrente',()=>{
  const source=fs.readFileSync(path.join(root,'App.tsx'),'utf8');
  assert.match(source,/<AttachmentInput key=\{comment\.pid/);assert.match(source,/onBusyChange=\{setCommentAttachmentBusy\}/);assert.match(source,/attachment_details/);assert.match(source,/<AnalysisForm key=\{jobProject\} onBusyChange=\{setJobFormBusy\}/);
  assert.match(source,/Mostro quando você clicar fora do relatório/);assert.match(source,/Segure o clique parado 0,4 s e escolha Comentar/);
});

function attachmentHarness(initial=[],upload=async()=>attachment){
  const slots=[],effects=[],busy=[],uploads=[],revoked=[];let cursor=0,dirty=true,tree,serial=0;
  const hooks={
    useState(initial){const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return [slots[i],value=>{const next=typeof value==='function'?value(slots[i]):value;if(!Object.is(next,slots[i])){slots[i]=next;dirty=true;}}];},
    useRef(initial){const i=cursor++;if(!(i in slots))slots[i]={current:initial};return slots[i];},
    useEffect(effect,deps){const i=cursor++;if(!(i in slots)||deps.some((v,k)=>!Object.is(v,slots[i][k]))){slots[i]=deps;effects.push(effect);}},
  };
  const module={exports:{}},real=require(path.join(root,'attachments.ts'));
  vm.runInNewContext(compile(fs.readFileSync(path.join(root,'AttachmentInput.tsx'),'utf8')),{module,exports:module.exports,crypto:{randomUUID:()=>`pending-${++serial}`},URL:{createObjectURL:()=>`blob:isolated-${serial}`,revokeObjectURL:url=>revoked.push(url)},require:name=>name==='react'?hooks:name==='./attachments'?{...real,uploadAttachment:async(pid,file)=>{uploads.push({pid,file});return upload(pid,file);}}:name.endsWith('.css')?{}:require(name)});
  const props={pid:'p1',value:initial,onChange:value=>{props.value=value;dirty=true;},onBusyChange:value=>busy.push(value),children:require('react').createElement('textarea',{defaultValue:'Texto preservado'})};
  const render=()=>{cursor=0;dirty=false;tree=module.exports.default(props);for(const e of effects.splice(0))e();return tree;};
  const settle=async()=>{for(let i=0;i<8;i++){if(dirty)render();await Promise.resolve();}if(dirty)render();};render();
  return {props,busy,uploads,revoked,settle,get tree(){if(dirty)render();return tree;},find(predicate){return nodes(this.tree).find(predicate);},paste(file,plain=''){let prevented=false;this.tree.props.onPaste({clipboardData:{items:file?[{kind:'file',getAsFile:()=>file}]:[],getData:()=>plain},preventDefault:()=>{prevented=true;}});return prevented;}};
}

test('componente real cola print com prévia e preserva paste de texto/misto',async()=>{
  const file={name:'print.png',type:'image/png',size:1024},h=attachmentHarness();
  assert.equal(h.paste(null,'Texto normal'),false);assert.equal(h.uploads.length,0);
  assert.equal(h.paste(file),true);assert.equal(h.busy.at(-1),true);assert.match(h.find(n=>n.type==='img').props.src,/^blob:/);
  await h.settle();assert.equal(h.props.value[0].id,attachment.id);assert.equal(h.find(n=>n.type==='img').props.src,attachment.url);assert.equal(h.busy.at(-1),false);
  const mixed=attachmentHarness();assert.equal(mixed.paste(file,'Texto junto'),false);await mixed.settle();assert.equal(mixed.uploads.length,1);
});

test('componente real escolhe arquivo, exibe prévia e permite remover sem apagar texto',async()=>{
  const file={name:'print.png',type:'image/png',size:1024},h=attachmentHarness();const input=h.find(n=>n.type==='input'&&n.props.type==='file');
  const target={files:[file],value:'C:\\fakepath\\print.png'};input.props.onChange({target});assert.equal(target.value,'');await h.settle();
  assert.equal(h.uploads[0].file,file);assert.equal(h.find(n=>n.type==='img').props.alt,'Print: print.png');
  h.find(n=>n.type==='button'&&n.props['aria-label']==='Remover print print.png').props.onClick();await h.settle();assert.equal(h.props.value.length,0);assert.equal(h.find(n=>n.type==='textarea').props.defaultValue,'Texto preservado');
});

test('upload falho mantém File/prévia para retry e bloqueia envio até resolver/remover',async()=>{
  let fail=true;const file={name:'print.png',type:'image/png',size:1024},h=attachmentHarness([],async()=>{if(fail)throw new Error('Falha de rede isolada');return attachment;});
  h.paste(file);await h.settle();assert.equal(h.props.value.length,0);assert.equal(h.busy.at(-1),true);assert.match(text(h.tree),/Falha de rede isolada/);assert.match(h.find(n=>n.type==='img').props.src,/^blob:/);
  fail=false;h.find(n=>n.type==='button'&&text(n)==='Tentar novamente').props.onClick();await h.settle();assert.equal(h.uploads.length,2);assert.equal(h.uploads[1].file,file);assert.equal(h.props.value.length,1);assert.equal(h.busy.at(-1),false);
});

test('tipo/tamanho/quantidade inválidos exibem erro sem upload ou perda do conteúdo',async()=>{
  for(const file of [{name:'vector.svg',type:'image/svg+xml',size:10},{name:'huge.png',type:'image/png',size:8*1024*1024+1}]){const h=attachmentHarness([attachment]);h.paste(file);await h.settle();assert.equal(h.uploads.length,0);assert.equal(h.props.value.length,1);assert.ok(h.find(n=>n.props?.role==='alert'));}
  const six=Array.from({length:6},(_,i)=>({...attachment,id:`print-${i}`,url:`/api/projects/p1/attachments/print-${i}`}));const full=attachmentHarness(six);full.paste({name:'extra.png',type:'image/png',size:10});await full.settle();assert.equal(full.uploads.length,0);assert.equal(full.props.value.length,6);assert.match(text(full.tree),/Use até 6 prints/);
});
