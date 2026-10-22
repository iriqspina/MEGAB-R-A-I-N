// 261018: Escape usa a regra atual de fechamento, depois que o upload começa.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const assert=require('node:assert/strict'),{test}=require('node:test'),ts=require('typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/App.tsx'),'utf8');
const ast=ts.createSourceFile('App.tsx',source,ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const modal=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='Modal');
assert.ok(modal,'O componente Modal precisa ser encontrado no App atual.');
const compiled=ts.transpileModule('const {useRef,useEffect}=require("react");\n'+modal.getText(ast)+'\nmodule.exports=Modal;',{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
function harness(){
 const slots=[],effects=[],listeners=new Set();let cursor=0,prevented=0;
 const hooks={useRef(initial){const i=cursor++;if(!(i in slots))slots[i]={current:initial};return slots[i];},useEffect(fn,deps){const i=cursor++,prior=slots[i];if(!prior||deps.some((v,k)=>!Object.is(v,prior.deps[k]))){effects.push(()=>{prior?.cleanup?.();slots[i]={deps,cleanup:fn()};});}}};
 const document={body:{style:{overflow:''}},activeElement:null,addEventListener:(kind,fn)=>{if(kind==='keydown')listeners.add(fn);},removeEventListener:(kind,fn)=>listeners.delete(fn)};
 const moduleObject={exports:{}};
 vm.runInNewContext(compiled,{module:moduleObject,exports:moduleObject.exports,document,IconButton:()=>null,X:()=>null,require:name=>name==='react'?hooks:require(name)});
 return {render(onClose){cursor=0;moduleObject.exports({title:'Isolado',children:null,onClose});for(const e of effects.splice(0))e();},escape(){for(const fn of listeners)fn({key:'Escape',preventDefault:()=>prevented++});},get prevented(){return prevented;},get listeners(){return listeners.size;}};
}

test('Escape depois do upload começar consulta o fechamento atual e preserva o campo',()=>{
 const h=harness();let closed=0;
 const closer=busy=>()=>{if(!busy)closed++;};
 h.render(closer(false)); // janela abriu antes de escolher o print
 h.render(closer(true)); // onBusyChange do anexo atualizou o pai
 h.escape();assert.equal(closed,0);assert.equal(h.prevented,1);assert.equal(h.listeners,1);
 h.render(closer(false)); // upload resolvido ou print removido
 h.escape();assert.equal(closed,1);assert.equal(h.prevented,2);
});

test('Escape usa o callback novo após edição, sem chamar o callback da montagem',()=>{
 const h=harness(),calls=[];
 h.render(()=>calls.push('montagem'));h.render(()=>calls.push('atual'));h.escape();
 assert.deepEqual(calls,['atual']);
});

test('retirar relatório fixado consulta guard e preserva o editor com print pendente',()=>{
 const board=ast.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='ProjectBoard');
 const unpin=board?.body.statements.find(s=>ts.isFunctionDeclaration(s)&&s.name?.text==='unpin');
 assert.ok(unpin,'A ação real de retirar o fixado precisa ser encontrada.');
 const calls=[],notices=[],env={pid:'p1',allowed:false,workspace:{views:[{project_id:'p1',id:'report-1'},{project_id:'p1',id:'other'},{project_id:'p2',id:'report-1'}]},mayCloseReport:(pid,fid)=>{calls.push({pid,fid});return env.allowed;},onSaved:m=>notices.push(m),updateWorkspace:updater=>{env.workspace=updater(env.workspace);}};
 const code=ts.transpileModule(unpin.getText(ast)+'\nglobalThis.unpinReport=unpin;',{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 vm.runInNewContext(code,env);
 env.unpinReport('report:report-1');assert.equal(env.workspace.views.length,3);assert.deepEqual(calls[0],{pid:'p1',fid:'report-1'});assert.match(notices[0],/print pendente/);
 env.allowed=true;env.unpinReport('report:report-1');assert.equal(env.workspace.views.length,2);assert.ok(env.workspace.views.some(v=>v.project_id==='p2'&&v.id==='report-1'));assert.ok(env.workspace.views.some(v=>v.project_id==='p1'&&v.id==='other'));
});

test('BOOTSTRAP conserva bloqueio agregado enquanto outro campo continua pendente ou com erro',()=>{
 const python=fs.readFileSync(path.join(__dirname,'../../central_reports.py'),'utf8');
 const lines=python.split(/\r?\n/),declaration=lines.find(l=>l.startsWith('const attachmentBlockedFields=')),listener=lines.find(l=>l.startsWith("document.addEventListener('mb-attachments-state'"));
 assert.ok(declaration&&listener,'O agregador real do BOOTSTRAP precisa estar disponível.');
 const messages=[];let receive;
 vm.runInNewContext(declaration+'\n'+listener,{document:{addEventListener:(name,fn)=>{assert.equal(name,'mb-attachments-state');receive=fn;}},send:(kind,payload)=>messages.push({kind,blocked:payload.blocked})});
 receive({detail:{id:'nota-1',bloqueado:true}});receive({detail:{id:'decisao-1',bloqueado:true}});
 assert.deepEqual(messages,[{kind:'attachment-state',blocked:true}]);
 receive({detail:{id:'nota-1',bloqueado:false}}); // upload concluiu, outro campo ainda tem erro
 assert.equal(messages.length,1);
 receive({detail:{id:'decisao-1',bloqueado:true}});assert.equal(messages.length,1);
 receive({detail:{id:'decisao-1',bloqueado:false}}); // remover/destroir o último campo libera
 assert.deepEqual(messages,[{kind:'attachment-state',blocked:true},{kind:'attachment-state',blocked:false}]);
});
