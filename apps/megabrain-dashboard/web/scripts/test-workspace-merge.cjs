const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const {mergeWorkspace}=require('../src/workspace-merge.ts');
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
