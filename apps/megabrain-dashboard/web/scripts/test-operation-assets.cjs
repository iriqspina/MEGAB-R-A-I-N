const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {test}=require('node:test'),ts=require('typescript');
const Module=require('node:module');const file=path.join(__dirname,'../src/operation_assets.ts');const mod=new Module(file,module);mod.filename=file;mod.paths=module.paths;mod._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {resultAsset}=mod.exports;const source='S:/projects/Portfolio/evidence/session/operacao.json';
test('não abre resultado de outra pasta com o mesmo nome',()=>assert.equal(resultAsset({path:'S:/projects/Portfolio/task-a/result.html'},[{id:'a',name:'a',origin:'task-b/result.html'}],source),undefined));
test('igualdade da origem completa aceita Windows e rejeita ambiguidade',()=>{const asset={id:'a',name:'a',origin:'task-a/result.html'};assert.deepEqual(resultAsset({path:'S:\\projects\\Portfolio\\task-a\\result.html'},[asset],source),asset);assert.equal(resultAsset({path:'S:/projects/Portfolio/task-a/result.html'},[asset,{...asset,id:'b'}],source),undefined)});
test('usa identidade exata do arquivo',()=>assert.equal(resultAsset({file_id:'a'},[{id:'a',name:'a'}],source)?.id,'a'));
