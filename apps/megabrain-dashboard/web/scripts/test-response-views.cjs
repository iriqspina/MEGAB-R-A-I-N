const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{test}=require('node:test'),ts=require('typescript');
require.extensions['.ts']=function(module,file){module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);};
const {uniqueResponseViews}=require('../src/response-views.ts');
const p={project_id:'project',id:'file',title:'Original',url:'/api/files/file',hash:'old'};
test('duplicate identities mount once and preserve first editor version without altering saved records',()=>{
 const input=[p,{...p,hash:'new',title:'New version'},{...p,project_id:'other'}],before=JSON.stringify(input);
 const result=uniqueResponseViews(input,()=>true);
 assert.equal(result.length,2);assert.equal(result[0],p);assert.equal(result[0].hash,'old');assert.equal(JSON.stringify(input),before);
 assert.equal(new Set(result.map(p=>`${p.project_id}:${p.id}`)).size,result.length);
});
test('invalid entries and URLs never enter the layout',()=>{
 assert.deepEqual(uniqueResponseViews([null,{},p,{...p,url:'javascript:bad'},{...p,id:7}],u=>u.startsWith('/api/')),[p]);
 assert.deepEqual(uniqueResponseViews(null,()=>true),[]);
});
