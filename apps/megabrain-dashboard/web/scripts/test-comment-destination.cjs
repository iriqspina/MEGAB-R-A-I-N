// Executes the current App comment handlers and catalogue component against isolated state/API/storage.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
const root=path.join(__dirname,'../src'),source=fs.readFileSync(path.join(root,'App.tsx'),'utf8');
const ast=ts.createSourceFile('App.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const compile=s=>ts.transpileModule(s,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}).outputText;
require.extensions['.ts']=(m,f)=>m._compile(compile(fs.readFileSync(f,'utf8')),f);
const {normalizeAttachments}=require('../src/attachments.ts'),routing=require('../src/bridge-routing.ts'),{mutationKey}=require('../src/api.ts');
const route={vendor:'gpt',modelo:'gpt-6.1-sol',effort:'xhigh'},glm={vendor:'glm',modelo:'GLM-5.3',effort:'max'};
const attachment={id:'print-1',path:'.mb-anexos/print-1.png',name:'print.png',mime:'image/png',size:12,url:'/api/projects/p1/attachments/print-1'};
const view={revision:4,data:{modo:'segundo_plano',vendor:'gpt',pipeline:{planejador:route}},vendors:[{id:'gpt',nome:'Codex',ativo:true},{id:'glm',nome:'ZCode',ativo:true}],catalogo:[{vendor:'gpt',modelos:[{id:route.modelo,nome:'Sol',efforts:['high','xhigh']}]},{vendor:'glm',modelos:[{id:glm.modelo,nome:'GLM',efforts:['high','max']}]}]};
const plain=v=>JSON.parse(JSON.stringify(v));
function storage(){const items=new Map();return {getItem:k=>items.get(k)||null,setItem:(k,v)=>items.set(k,String(v)),removeItem:k=>items.delete(k),items};}
function handlers(){
 const app=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='App');
 const names=['beginComment','rememberCommentDraft','changeCommentRoute','closeComment','postComment'];
 const funcs=app.body.statements.filter(s=>ts.isFunctionDeclaration(s)&&names.includes(s.name?.text));assert.equal(funcs.length,names.length);
 const helpers=ast.statements.filter(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='readModuleDraft'||ts.isVariableStatement(s)&&s.declarationList.declarations.some(d=>d.name.getText(ast)==='moduleDraftKey'));
 const store=storage(),calls=[],errors=[],notices=[],env={localStorage:store,normalizeAttachments,readRoute:routing.readRoute,mutationKey,comment:{pid:'p1',target:'module:now',label:'Agora',anchor:{x:.5,y:.1}},commentText:'Pedido',commentAttachments:[attachment],commentRoute:undefined,commentRouteIssue:'',commentBusy:false,commentAttachmentBusy:false,commentDrafts:{current:{}},commentRequest:{current:null},notify:m=>notices.push(m),onError:e=>errors.push(e.message),loadDetail:async()=>{},api:async(url,method,payload,key)=>{calls.push({url,method,payload:plain(payload),key});if(env.fail)throw new Error('Falha isolada');}};
 for(const [state,setter]of Object.entries({comment:'setComment',commentText:'setCommentText',commentAttachments:'setCommentAttachments',commentRoute:'setCommentRoute',commentRouteIssue:'setCommentRouteIssue',commentBusy:'setCommentBusy',commentAttachmentBusy:'setCommentAttachmentBusy'}))env[setter]=v=>{env[state]=v;};
 vm.runInNewContext(compile([...helpers,...funcs].map(s=>s.getText(ast)).join('\n')+'\nglobalThis.actions={'+names.join(',')+'};'),env);
 return {env,store,calls,errors,notices,actions:env.actions};
}
test('module comment without destination retains its original payload and never gains a route',async()=>{
 const h=handlers();await h.actions.postComment();assert.equal(h.calls.length,1);assert.equal(h.calls[0].payload.rota,undefined);assert.equal(h.calls[0].payload.target,'module:now');assert.deepEqual(h.calls[0].payload.anexos,[attachment]);assert.equal(h.notices.at(-1),'Comentário salvo no projeto.');
});
test('explicit module destination survives failed send/reopen/retry and clears only after receipt',async()=>{
 const h=handlers(),ctx=h.env.comment;h.actions.changeCommentRoute(route);assert.equal(h.calls.length,0);assert.equal(h.store.items.size,1);h.env.commentRouteIssue='';h.env.fail=true;await h.actions.postComment();
 assert.deepEqual(h.calls[0].payload.rota,route);assert.equal(h.env.commentText,'Pedido');assert.deepEqual(h.env.commentAttachments,[attachment]);assert.deepEqual(h.env.commentRoute,route);
 h.env.commentDrafts.current={};h.actions.closeComment();h.actions.beginComment(ctx);assert.deepEqual(plain(h.env.commentRoute),route);assert.equal(h.env.commentText,'Pedido');assert.equal(h.env.commentAttachments[0].id,attachment.id);
 h.env.commentRouteIssue='';h.env.fail=false;await h.actions.postComment();assert.equal(h.calls[1].key,h.calls[0].key);assert.deepEqual(h.calls[1].payload.rota,route);assert.equal(h.env.commentRoute,undefined);assert.equal(h.env.commentText,'');assert.equal(h.env.commentAttachments.length,0);assert.equal(h.store.items.size,0);assert.doesNotMatch(h.notices.at(-1),/iniciou|executando|abrindo/);
});
test('module/project drafts isolate destinations and retain route-only choices',()=>{
 const h=handlers(),first=h.env.comment;h.env.commentText='';h.env.commentAttachments=[];h.actions.changeCommentRoute(route);
 assert.equal(h.store.items.size,1);h.actions.beginComment({...first,target:'module:results'});assert.equal(h.env.commentRoute,undefined);
 h.actions.changeCommentRoute(glm);h.actions.beginComment({...first,pid:'p2'});assert.equal(h.env.commentRoute,undefined);
 h.actions.beginComment(first);assert.deepEqual(plain(h.env.commentRoute),route);assert.equal(h.env.commentText,'');
 h.actions.beginComment({...first,target:'module:results'});assert.deepEqual(plain(h.env.commentRoute),glm);
});
test('clearing destination removes only the route, even before React applies the new state',()=>{
 const h=handlers();h.env.commentRoute=route;let pending;h.env.setCommentRoute=value=>{pending=value;};h.actions.changeCommentRoute(undefined);
 const draft=JSON.parse([...h.store.items.values()][0]);assert.equal(pending,undefined);assert.equal(draft.rota,undefined);assert.equal(draft.text,'Pedido');assert.deepEqual(draft.anexos,[attachment]);
});
test('malformed destination, catalogue validation, and unsupported mode block POST without losing draft',async()=>{
 const h=handlers();h.env.commentRoute={};h.actions.rememberCommentDraft('Pedido',[attachment]);await h.actions.postComment();assert.equal(h.calls.length,0);assert.equal(h.store.items.size,1);assert.match(h.errors.at(-1),/Destino inválido/);
 h.env.commentRoute=route;h.env.commentRouteIssue='Consultando o catálogo';await h.actions.postComment();assert.equal(h.calls.length,0);
 h.env.commentRoute=glm;h.env.commentRouteIssue=routing.commentRouteProblem({...view,data:{...view.data,modo:'janela'}},glm);await h.actions.postComment();assert.equal(h.calls.length,0);assert.match(h.errors.at(-1),/segundo plano/);assert.equal(h.env.commentText,'Pedido');assert.equal(h.env.commentAttachments.length,1);
});
function nodes(tree){if(!tree||typeof tree!=='object')return [];if(Array.isArray(tree))return tree.flatMap(nodes);return [tree,...nodes(tree.props?.children)];}
function destination(){
 const fn=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='CommentDestination');assert.ok(fn);
 const slots=[],effects=[],problems=[],choices=[],loads=[],saved=[];let cursor=0,dirty=true,tree,currentView=null,fail=false;
 const hooks={useState(initial){const i=cursor++;if(!(i in slots))slots[i]=initial;return [slots[i],v=>{slots[i]=v;dirty=true;}];},useEffect(fn,deps){const i=cursor++,old=slots[i];if(!old||deps.some((v,k)=>!Object.is(v,old.deps[k]))){slots[i]={deps};effects.push(fn);}}};
 const Marker=()=>null,load=async()=>{loads.push(props.pid);if(fail)throw new Error('Offline');return currentView;};
 const props={pid:'p1',value:route,busy:false,onChange:value=>choices.push(value),onProblem:message=>problems.push(message)},module={exports:{}};
 vm.runInNewContext(compile(fn.getText(ast)+'\nmodule.exports=CommentDestination;'),{module,exports:module.exports,...hooks,...routing,RouteChoice:Marker,useBridge:pid=>({view:currentView,load,save:()=>saved.push(pid)}),require});
 const render=()=>{dirty=false;cursor=0;tree=module.exports(props);for(const fn of effects.splice(0))fn();};
 const settle=async()=>{for(let i=0;i<12;i++){if(dirty)render();await Promise.resolve();}if(dirty)render();};render();
 return {props,problems,choices,loads,saved,settle,setView:value=>{currentView=value;dirty=true;},setValue:value=>{props.value=value;dirty=true;},fail:()=>{fail=true;},get tree(){if(dirty)render();return tree;},get choice(){return nodes(this.tree).find(n=>n.type===Marker);},button:label=>nodes(tree).find(n=>n.type==='button'&&n.props.children===label)};
}
test('modal catalogue waits by project, validates selection, and selection never saves project defaults',async()=>{
 const h=destination();await h.settle();assert.deepEqual(h.loads,['p1']);assert.match(h.problems.at(-1),/Consultando/);
 h.setView(view);await h.settle();assert.equal(h.problems.at(-1),'');assert.equal(h.choice.props.value.modelo,route.modelo);
 assert.equal(h.choice.props.inherit,undefined);assert.equal(h.button('Só registrar no projeto · sem IA').props['aria-pressed'],false);
 h.choice.props.onChange({...route,effort:'high'});assert.equal(h.saved.length,0);assert.equal(h.choices[0].effort,'high');
 h.setValue({...route,effort:'high'});await h.settle();assert.equal(h.problems.at(-1),'');
 h.setView({...view,data:{...view.data,modo:'janela'}});h.setValue(glm);await h.settle();assert.match(h.problems.at(-1),/segundo plano/);assert.equal(h.choice.props.view.vendors.find(v=>v.id==='glm').ativo,false);assert.equal(view.vendors.find(v=>v.id==='glm').ativo,true);
});
test('invalid restored choice remains blocked until explicit correction or registration-only reset',async()=>{
 const h=destination();h.setView(view);h.setValue({});await h.settle();assert.match(h.problems.at(-1),/Destino inválido/);assert.equal(h.choices.length,0);
 assert.equal(h.tree.props.open,true);
 h.button('Só registrar no projeto · sem IA').props.onClick();assert.equal(h.choices.length,1);assert.equal(h.choices[0],undefined);
 h.setValue(undefined);await h.settle();assert.equal(h.problems.at(-1),'');assert.equal(h.button('Só registrar no projeto · sem IA').props['aria-pressed'],true);assert.equal(h.choice.props.inherit,undefined);
});
