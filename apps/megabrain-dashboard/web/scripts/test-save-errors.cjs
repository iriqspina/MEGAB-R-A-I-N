const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {mergeWorkspace,saveWorkspace,saveFailure,retryDelay,workspaceWeight,WORKSPACE_LIMIT,WorkspaceBusy}=require('../src/workspace-merge.ts');

// 261016: salvar o painel quando o erro NAO e conflito (rede, 5xx, painel grande demais, outros).
const http=(status,message='')=>Object.assign(new Error(message),{status});
const stale=e=>Boolean(e&&e.status===409);

test('central sem resposta e erro 5xx viram "sem conexao", sem modal de conflito',()=>{
  assert.equal(saveFailure(new TypeError('Failed to fetch')),'offline');
  assert.equal(saveFailure(new TypeError('NetworkError when attempting to fetch resource.')),'offline');
  for(const status of [0,408,429,500,502,503,504])assert.equal(saveFailure(http(status,'x')),'offline',String(status));
});
test('painel grande demais (400 do central_store e 413 do limite de pedido) tem aviso proprio',()=>{
  assert.equal(saveFailure(http(400,'Configuração grande demais.')),'too-large');
  assert.equal(saveFailure(http(413,'Pedido grande demais.')),'too-large');
  assert.equal(saveFailure(http(400,'Área de trabalho inválida.')),'error');
});
test('so 409 e conflito; sessao, erro de codigo e outros 4xx nao abrem a decisao',()=>{
  assert.equal(saveFailure(http(409,'Outra janela salvou')),'conflict');
  assert.equal(saveFailure(http(401,'Conecte este dispositivo')),'signed-out');
  assert.equal(saveFailure(http(403,'Sessão desatualizada. Recarregue.')),'error');
  assert.equal(saveFailure(new WorkspaceBusy('x')),'busy');
  assert.equal(saveFailure(new TypeError("Cannot read properties of undefined (reading 'x')")),'error');
  assert.equal(saveFailure(new Error('qualquer')),'error');
});
test('espera entre tentativas cresce e para em 30 s',()=>{
  const waits=[1,2,3,4,5,6,9].map(retryDelay);
  assert.deepEqual(waits,[2000,4000,8000,16000,30000,30000,30000]);
  assert.equal(retryDelay(0),2000);
});
test('tamanho do painel bate com o json.dumps do central_store (UTF-8 e separadores)',()=>{
  const ws={a:'ção',b:[1,2,{c:null}],d:{},skip:undefined,responseViews:[{id:'r1',title:'Relatório ação'},{id:'r2',title:'x'}]};
  // python: len(json.dumps(ws,ensure_ascii=False).encode()) == 140; responseViews sozinho == 72
  assert.deepEqual(workspaceWeight(ws),{bytes:140,largest:'responseViews',largestBytes:72});
  assert.equal(WORKSPACE_LIMIT,300000);
});
test('falha de rede no meio do salvamento sobe para o efeito decidir a espera (sem repetir PUT as cegas)',async()=>{
  let puts=0,gets=0;
  await assert.rejects(saveWorkspace({base:{a:1},local:()=>({serial:1,revision:3,data:{a:2}}),
    put:async()=>{puts++;throw new TypeError('Failed to fetch');},get:async()=>{gets++;return {revision:3,data:{a:1}};},stale}),
    e=>saveFailure(e)==='offline');
  assert.equal(puts,1);assert.equal(gets,0);
  await assert.rejects(saveWorkspace({base:{a:1},local:()=>({serial:1,revision:3,data:{a:2}}),
    put:async()=>{throw http(503,'Não foi possível concluir (503).');},get:async()=>({revision:3,data:{a:1}}),stale}),
    e=>saveFailure(e)==='offline');
});
test('central volta depois de quedas: as mesmas mudancas sao gravadas na tentativa seguinte',async()=>{
  let down=3,revision=7,stored={a:1,b:1};const waits=[];
  const io={base:{a:1,b:1},local:()=>({serial:1,revision,data:{a:2,b:1}}),
    put:async(r,d)=>{if(down>0){down--;throw new TypeError('Failed to fetch');}if(r!==revision)throw http(409);revision++;stored=d;return {revision,data:d};},
    get:async()=>({revision,data:stored}),stale};
  for(let attempt=1;;attempt++){
    try{await saveWorkspace(io);break;}
    catch(e){assert.equal(saveFailure(e),'offline');waits.push(retryDelay(attempt));}
  }
  assert.deepEqual(waits,[2000,4000,8000]);
  assert.deepEqual(stored,{a:2,b:1});assert.equal(revision,8);
});
test('"Salvar meu rascunho": no conflito fica o desta janela, o resto da outra janela e mantido',()=>{
  const base={appearance:{x:{color:'#111'}},activeProject:'a',layouts:{desktop:[{i:'r',x:0}]}};
  const local={...base,appearance:{x:{color:'#ff82c4'}}};
  const remote={...base,appearance:{x:{color:'#8bc8ff'}},activeProject:'b'};
  assert.equal(mergeWorkspace(base,local,remote),null);
  assert.deepEqual(mergeWorkspace(base,local,remote,{prefer:'local'}),{...base,appearance:{x:{color:'#ff82c4'}},activeProject:'b'});
});
test('retomar com prefer local grava por cima do conflito sem pedir decisao de novo',async()=>{
  const base={appearance:{x:{color:'#111'}},activeProject:'a'};
  let revision=5,stored={appearance:{x:{color:'#8bc8ff'}},activeProject:'b'};
  const io={base,local:()=>({serial:2,revision:4,data:{...base,appearance:{x:{color:'#ff82c4'}}}}),
    put:async(r,d)=>{if(r!==revision)throw http(409,'Outra janela salvou');revision++;stored=d;return {revision,data:d};},
    get:async()=>({revision,data:stored}),stale};
  await assert.rejects(saveWorkspace(io),e=>saveFailure(e)==='conflict');
  const round=await saveWorkspace({...io,prefer:'local'});
  assert.deepEqual(stored,{appearance:{x:{color:'#ff82c4'}},activeProject:'b'});
  assert.equal(round.saved.revision,6);
});
// Revisao independente 261016: listas no "Salvar meu rascunho" e resposta perdida depois de gravar.
test('"Salvar meu rascunho" em lista disputada mantem o que so a outra janela acrescentou',()=>{
  const base={l:[{id:'p'}]};
  assert.deepEqual(mergeWorkspace(base,{l:[]},{l:[{id:'p',x:1},{id:'q'}]},{prefer:'local'}),{l:[{id:'q'}]});
  const ordem={l:['a','b','c']};
  assert.equal(mergeWorkspace(ordem,{l:['c','b','a']},{l:['b','a','c','d']}),null);
  assert.deepEqual(mergeWorkspace(ordem,{l:['c','b','a']},{l:['b','a','c','d']},{prefer:'local'}),{l:['c','b','a','d']});
});
test('gravacao feita mas resposta perdida: o 409 seguinte nao vira conflito falso',async()=>{
  // A janela mandou k=2, o servidor gravou e a resposta se perdeu; depois a pessoa mudou k para 3.
  const base={k:1},enviado={k:2};let revision=6,stored=enviado;
  const io=()=>({base,local:()=>({serial:3,revision:5,data:{k:3}}),
    put:async(r,d)=>{if(r!==revision)throw http(409,'Outra janela salvou');revision++;stored=d;return {revision,data:d};},
    get:async()=>({revision,data:stored}),stale});
  await assert.rejects(saveWorkspace(io()),e=>saveFailure(e)==='conflict');
  const round=await saveWorkspace({...io(),unconfirmed:enviado});
  assert.deepEqual(stored,{k:3});assert.equal(round.saved.revision,7);
});
test('pedido sem resposta igual ao do servidor so vale quando e o mesmo conteudo',async()=>{
  const base={k:1};let revision=6,stored={k:9};
  const io={base,local:()=>({serial:3,revision:5,data:{k:3}}),unconfirmed:{k:2},
    put:async(r,d)=>{if(r!==revision)throw http(409);revision++;stored=d;return {revision,data:d};},
    get:async()=>({revision,data:stored}),stale};
  await assert.rejects(saveWorkspace(io),e=>saveFailure(e)==='conflict');
  assert.deepEqual(stored,{k:9});
});
