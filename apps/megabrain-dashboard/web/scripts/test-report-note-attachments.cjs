// 261018: referências de prints, recibos e versão das notas; sem serviço real.
const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const N=require('../src/report-notes.ts');
const A='a'.repeat(64),B='b'.repeat(64);
const attachment=(id='print-a')=>({id,path:`.mb-anexos/${id}.png`,name:`${id}.png`,mime:'image/png',size:125,url:`/api/projects/projeto/attachments/${id}`});
const note=(extra={})=>({id:'nota-1',texto:'',ancora:{base:'#imagem',idx:[0]},ox:.2,oy:.3,...extra});

test('nota só com imagem validada entra no pacote e restaura sem bytes de prévia',()=>{
 const ref={...attachment(),preview:'data:image/png;base64,SEGREDO',file:{name:'local.png'},data:'BASE64'};
 const pending=N.applyNotesMessage([],{completa:true,notas:[note({anexos:[ref]})],enviar:['nota-1']},A);
 assert.equal(pending.length,1);assert.equal(pending[0].versao,A);
 assert.deepEqual(pending[0].anexos,[attachment()]);
 const stored=N.storedValue(pending,null);
 assert.ok(!stored.includes('SEGREDO'));assert.ok(!stored.includes('BASE64'));
 assert.deepEqual(N.readStored(stored).notas[0].anexos,[attachment()]);
});

test('arquivo transitório, SVG e referência malformada não fazem uma nota vazia parecer pronta',()=>{
 for(const anexos of [[{name:'local.png',type:'image/png',size:12}],[{...attachment(),mime:'image/svg+xml'}],[{...attachment(),path:'data:image/png;base64,abc'}],[{...attachment(),url:'https://outro.example/print.png'}]]){
  assert.deepEqual(N.applyNotesMessage([],{notas:[note({anexos})]},A),[]);
 }
 const text=N.readStored(JSON.stringify({notas:[note({texto:'Preservar texto',anexos:[{bad:true}]})]})).notas;
 assert.equal(text[0].texto,'Preservar texto');assert.equal(text[0].anexos,undefined);
});

test('editar ou remover só a imagem volta à fila; recibo antigo de texto continua válido sem imagem',()=>{
 const original=note({texto:'Confira aqui',anexos:[attachment()]}),edited=note({texto:'Confira aqui',anexos:[attachment('print-b')]});
 const sent=N.markSent({},[original]);
 assert.deepEqual(N.unsentNotes([original],sent),[]);
 assert.deepEqual(N.unsentNotes([edited],sent),[edited]);
 assert.equal(N.unsentNotes([note({texto:'Confira aqui'})],sent).length,1);
 assert.deepEqual(N.unsentNotes([note({texto:'  Confira aqui  '})],{'nota-1':'Confira aqui'}),[]);
 assert.equal(N.unsentNotes([original],{'nota-1':'Confira aqui'}).length,1);
});

test('chave determinística muda só com imagem, mantém legado sem imagem e ignora marcadores locais',()=>{
 const original=note({texto:'Texto',anexos:[attachment()],versao:A});
 const first=N.noteKey('relatorio',original,B);
 assert.equal(first,N.noteKey('relatorio',{...original,manual:true},B));
 assert.notEqual(first,N.noteKey('relatorio',{...original,anexos:[attachment('print-b')]},B));
 assert.notEqual(first,N.noteKey('relatorio',{...original,anexos:[]},B));
 assert.equal(N.noteFingerprint(note({texto:'  texto  '})),'texto');
});

test('corpo preserva âncora e versão externa, envia só referências e a forma A6 estável',()=>{
 const source=note({anexos:[{...attachment(),preview:'data:image/png;base64,x'}],versao:A,manual:true});
 const body=N.noteBody(source,B),saved=body.feedback.notas[0];
 assert.equal(body.hash,A);assert.deepEqual(saved.ancora,source.ancora);
 assert.equal(saved.manual,undefined);assert.equal(saved.versao,undefined);
 assert.deepEqual(saved.anexos,[attachment()]);
 assert.deepEqual(N.noteBody({...source,manual:false},B),body);
});

test('falha em nota só com imagem preserva a pendência e a nova tentativa reaproveita a chave',async()=>{
 const original=note({anexos:[attachment()],versao:A}),keys=[];let fail=true;
 const post=async(body,n)=>{keys.push(N.noteKey('relatorio',n,B));assert.deepEqual(body.feedback.notas[0].anexos,[attachment()]);if(fail){fail=false;throw new Error('sem rede');}return {versao_anterior:true};};
 const first=await N.deliverNotes([original],B,post);
 assert.deepEqual(first.failed,[original]);assert.deepEqual(first.delivered,[]);
 const sent=N.markSent({},first.delivered);
 assert.deepEqual(N.unsentNotes([original],sent),[original]);
 const retry=await N.deliverNotes(N.unsentNotes([original],sent),B,post);
 assert.equal(retry.previous,true);assert.deepEqual(retry.delivered,[original]);assert.equal(keys[0],keys[1]);
 assert.deepEqual(N.unsentNotes([original],N.markSent(sent,retry.delivered)),[]);
});

test('mensagem completa conserva A2: ausência não apaga; exclusão explícita respeita a versão',()=>{
 const original=note({anexos:[attachment()],versao:A});
 assert.deepEqual(N.applyNotesMessage([original],{completa:true,notas:[]},A),[original]);
 assert.deepEqual(N.applyNotesMessage([original],{completa:true,notas:[],removidas:['nota-1']},B),[original]);
 assert.deepEqual(N.applyNotesMessage([original],{completa:true,notas:[],removidas:['nota-1']},A),[]);
 const updated=N.applyNotesMessage([original],{completa:true,notas:[note({anexos:[attachment('print-b')]})],enviar:['nota-1']},B);
 assert.equal(updated[0].versao,A);assert.equal(updated[0].anexos[0].id,'print-b');
});
