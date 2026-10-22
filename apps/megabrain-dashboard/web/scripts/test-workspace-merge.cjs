const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {mergeWorkspace,saveWorkspace,WorkspaceBusy}=require('../src/workspace-merge.ts');
test('mesma chegada em dois dispositivos converge sem aviso de conflito',()=>{
  const base={returnCursor:1,responseViews:[],layouts:{},activeProject:'a'};
  const local={...base,returnCursor:2,responseViews:[{id:'r'}]},remote={...local};
  assert.deepEqual(mergeWorkspace(base,local,remote),local);
});
test('nova chegada preserva troca de projeto e geometria no outro dispositivo',()=>{
  const base={returnCursor:1,responseViews:[],layouts:{},activeProject:'a'};
  const local={...base,returnCursor:2,responseViews:[{id:'r'}]};
  const remote={...base,activeProject:'b',layouts:{mobile:[{i:'x',w:1}]}};
  assert.deepEqual(mergeWorkspace(base,local,remote),{...local,activeProject:'b',layouts:remote.layouts});
});
test('duas ordens humanas diferentes nao se sobrescrevem',()=>{
  const base={layouts:{desktop:[{i:'r',x:0}]}};
  assert.equal(mergeWorkspace(base,{layouts:{desktop:[{i:'r',x:3}]}},{layouts:{desktop:[{i:'r',x:6}]}}),null);
});
test('marcacao de leitura nunca recua entre consultas',()=>{
  assert.deepEqual(mergeWorkspace({returnCursor:1,notificationReadId:1},{returnCursor:2,notificationReadId:3},{returnCursor:3,notificationReadId:2}),{returnCursor:3,notificationReadId:3});
});

// 261016: duas janelas gravando o mesmo painel (PC + celular, janela nativa + outra).
function servidor(data){let revision=1;const copy=v=>JSON.parse(JSON.stringify(v));return {
  get:async()=>({revision,data:copy(data)}),
  put:async(r,d)=>{if(r!==revision)throw Object.assign(new Error('Existe uma versao mais recente'),{status:409});revision++;data=copy(d);return {revision,data:copy(d)};},
  agora:()=>({revision,data})};}
const stale=e=>Boolean(e&&e.status===409);
test('secao criada nas duas janelas depois da base mescla chave a chave',()=>{
  const base={layouts:{}};
  const local={...base,appearance:{'project:a:':{color:'#ff82c4'}}};
  const remote={...base,appearance:{'type:now':{color:'#b2e58a'}}};
  assert.deepEqual(mergeWorkspace(base,local,remote),{layouts:{},appearance:{'project:a:':{color:'#ff82c4'},'type:now':{color:'#b2e58a'}}});
});
test('mesma cor mudada de jeitos diferentes nas duas janelas continua pedindo decisao',()=>{
  const base={layouts:{}};
  assert.equal(mergeWorkspace(base,{...base,appearance:{'project:a:':{color:'#ff82c4'}}},{...base,appearance:{'project:a:':{color:'#8bc8ff'}}}),null);
});
test('ordem das chaves nao conta como edicao',()=>{
  const base={layouts:{desktop:[{i:'r',x:0,y:0}]}};
  const local={layouts:{desktop:[{y:0,x:0,i:'r'}]}},remote={layouts:{desktop:[{i:'r',x:3,y:0}]}};
  assert.deepEqual(mergeWorkspace(base,local,remote),remote);
});
test('edicao local durante o PUT recusado tenta de novo com os dados mais novos e mescla',async()=>{
  const base={activeProject:'a',layouts:{},returnCursor:1};
  const srv=servidor(base);
  await srv.put(1,{...base,activeProject:'b'}); // a outra janela grava primeiro
  let janela={serial:1,revision:1,data:{...base,layouts:{desktop:[{i:'r',x:2}]}}};
  const status=[];
  const round=await saveWorkspace({base,local:()=>janela,get:srv.get,stale,put:async(revision,data)=>{
    if(!status.length)janela={...janela,serial:2,data:{...janela.data,appearance:{'project:a:':{color:'#ff82c4'}}}}; // clique durante a requisicao
    try{const r=await srv.put(revision,data);status.push(200);return r;}catch(e){status.push(e.status);throw e;}
  }});
  assert.deepEqual(status,[409,200]);
  assert.equal(round.serial,2);
  assert.deepEqual(srv.agora().data,{activeProject:'b',layouts:{desktop:[{i:'r',x:2}]},returnCursor:1,appearance:{'project:a:':{color:'#ff82c4'}}});
});
test('edicao feita depois da mesclagem nao apaga a mudanca da outra janela',async()=>{
  const base={activeProject:'a',layouts:{},density:'comfortable'};
  const srv=servidor(base);
  await srv.put(1,{...base,activeProject:'b'});
  let janela={serial:1,revision:1,data:{...base,layouts:{desktop:[{i:'r',x:2}]}}},calls=0;
  const round=await saveWorkspace({base,local:()=>janela,get:srv.get,stale,put:async(revision,data)=>{
    if(++calls===2)janela={...janela,serial:2,data:{...janela.data,density:'compact'}}; // clique durante o PUT mesclado
    return srv.put(revision,data);
  }});
  assert.equal(round.serial,1);
  const atual=mergeWorkspace(round.from,janela.data,round.saved.data); // o mesmo rebase do App.tsx
  assert.deepEqual(atual,{activeProject:'b',layouts:{desktop:[{i:'r',x:2}]},density:'compact'});
  await srv.put(round.saved.revision,atual); // o proximo salvamento nao reverte a outra janela
  assert.equal(srv.agora().data.activeProject,'b');
});
test('conflito verdadeiro no salvamento devolve o 409 sem gravar',async()=>{
  const base={activeProject:'a'};
  const srv=servidor(base);
  await srv.put(1,{activeProject:'b'});
  await assert.rejects(saveWorkspace({base,local:()=>({serial:1,revision:1,data:{activeProject:'c'}}),get:srv.get,put:srv.put,stale}),e=>e.status===409);
  assert.deepEqual(srv.agora(),{revision:2,data:{activeProject:'b'}});
});

// Revisao independente 261016: listas e recusas seguidas tambem davam falso aviso.
test('respostas que chegaram em horas diferentes nas duas janelas ficam todas',()=>{
  const r1={id:'r1',project_id:'p'},r2={id:'r2',project_id:'p'},r3={id:'r3',project_id:'p'};
  assert.deepEqual(mergeWorkspace({responseViews:[r1]},{responseViews:[r1,r2,r3]},{responseViews:[r1,r2]}),{responseViews:[r1,r2,r3]});
});
test('projetos abertos diferentes nas duas janelas somam',()=>{
  assert.deepEqual(mergeWorkspace({openProjects:['a']},{openProjects:['a','b']},{openProjects:['a','c']}),{openProjects:['a','b','c']});
});
test('quadros diferentes movidos nas duas janelas mesclam um a um',()=>{
  const base={layouts:{desk:[{i:'now',x:0,y:0},{i:'results',x:1,y:0}]}};
  const local={layouts:{desk:[{i:'now',x:0,y:4},{i:'results',x:1,y:0}]}},remote={layouts:{desk:[{i:'results',x:2,y:0},{i:'now',x:0,y:0}]}};
  assert.deepEqual(mergeWorkspace(base,local,remote),{layouts:{desk:[{i:'now',x:0,y:4},{i:'results',x:2,y:0}]}});
});
test('item fechado numa janela e intocado na outra sai; fechado numa e editado na outra pergunta',()=>{
  const p1={key:'k1',title:'A'},p2={key:'k2',title:'B'};
  assert.deepEqual(mergeWorkspace({homePanels:[p1,p2]},{homePanels:[p1]},{homePanels:[p1,p2],density:'compact'}),{homePanels:[p1],density:'compact'});
  assert.equal(mergeWorkspace({homePanels:[p1,p2]},{homePanels:[p1]},{homePanels:[p1,{...p2,title:'C'}]}),null);
});
test('ordem mudada de jeitos diferentes nas duas janelas pergunta',()=>{
  assert.equal(mergeWorkspace({openProjects:['a','b','c']},{openProjects:['b','a','c']},{openProjects:['a','c','b']}),null);
});
test('recusas seguidas sem conflito nao viram aviso: o salvamento so tenta de novo depois',async()=>{
  const srv=servidor({activeProject:'a',density:'comfortable'});let n=0;
  const get=async()=>{const r=await srv.get();await srv.put(r.revision,{...r.data,returnCursor:++n});return r;}; // outra janela grava logo depois de cada leitura
  await assert.rejects(saveWorkspace({base:{activeProject:'a',density:'comfortable'},local:()=>({serial:1,revision:0,data:{activeProject:'a',density:'compact'}}),get,put:srv.put,stale}),e=>e instanceof WorkspaceBusy);
  assert.equal(srv.agora().data.density,'comfortable');
});
