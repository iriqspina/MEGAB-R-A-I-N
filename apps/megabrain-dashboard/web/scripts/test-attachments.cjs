const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const A=require('../src/attachments.ts'),T=require('../src/attachment-transport.ts');
const ref=(id='a',pid='p')=>({id,path:'.mb-anexos/'+id+'.png',name:'print.png',mime:'image/png',size:4,url:`/api/projects/${pid}/attachments/${id}`});
test('rascunho mantém só referências canônicas e descarta bytes, SVG e URL externa',()=>{
  const file={...ref(),data:'x'.repeat(200000),file:new File(['x'],'x')};
  assert.deepEqual(A.normalizeAttachments([file]),[ref()]);
  assert.deepEqual(A.normalizeAttachments([{...ref(),mime:'image/svg+xml'},{...ref(),url:'https://evil.test/'}]),[]);
  assert.throws(()=>A.attachmentForProject('other',ref()));
  assert.notEqual(A.attachmentFingerprint([ref()]),A.attachmentFingerprint([ref('b')]));
});
test('upload envia base64 sem prefixo e preserva erro do servidor para retry',async()=>{
  let payload;
  const previous=global.fetch;global.fetch=async(url,init)=>{payload=JSON.parse(init.body);return {ok:true,json:async()=>({attachment:ref()})};};
  try{assert.deepEqual(await A.uploadAttachment('p',new File(['abcd'],'print.png',{type:'image/png'})),ref());assert.equal(payload.data,'YWJjZA==');assert.equal(payload.mime,'image/png');}
  finally{global.fetch=previous;}
});
test('limites reais incluem arquivo vazio, 8MiB e MIME',()=>{
  A.validateAttachment({type:'image/png',size:A.ATTACHMENT_BYTES});
  for(const item of [{type:'image/png',size:0},{type:'image/png',size:A.ATTACHMENT_BYTES+1},{type:'image/svg+xml',size:10}])assert.throws(()=>A.validateAttachment(item));
});
const source={},origin='http://fixture.test',hash='a'.repeat(64);
function setup(patch={}){const replies=[];return {replies,c:{source,origin,fid:'f',token:'secret',hash,pid:'p',pending:new Set(),current:()=>true,reply:m=>replies.push(m),upload:async()=>ref(),...patch}};}
function message(patch={}){return {source,origin,data:{channel:'mb-attachment-request',fid:'f',token:'secret',hash,requestId:'request-1',file:{name:'print.png',mime:'image/png',data:new Uint8Array([1,2,3,4]).buffer},...patch}};}
test('transporte binário validado volta como referência sem bytes',async()=>{
  const {c,replies}=setup();assert.equal(await T.receiveAttachment(message(),c),true);assert.deepEqual(replies[0].attachment,ref());assert.ok(!('file' in replies[0]));assert.equal(c.pending.size,0);
});
test('origem, janela, token, fid e versão impedem upload falsificado',async()=>{
  let count=0;const {c,replies}=setup({upload:async()=>{count++;return ref();}});
  for(const event of [{...message(),origin:'null'},{...message(),source:{}},message({token:'wrong'}),message({fid:'other'}),message({hash:'b'.repeat(64)}),message({requestId:'x'.repeat(81)})])assert.equal(await T.receiveAttachment(event,c),false);
  assert.equal(count,0);assert.deepEqual(replies,[]);
});
test('buffer grande, SVG, falha e limite concorrente retornam erro sem upload',async()=>{
  let count=0;const {c,replies}=setup({upload:async()=>{count++;throw Error('falhou');}});
  await T.receiveAttachment(message({file:{name:'x',mime:'image/png',data:new ArrayBuffer(A.ATTACHMENT_BYTES+1)}}),c);
  await T.receiveAttachment(message({file:{name:'x',mime:'image/svg+xml',data:new ArrayBuffer(4)}}),c);
  await T.receiveAttachment(message(),c);
  for(let i=0;i<6;i++)c.pending.add('busy'+i);
  await T.receiveAttachment(message(),c);
  assert.equal(count,1);assert.equal(replies.length,4);assert.ok(replies.every(r=>r.error));
});
test('resposta atrasada não atravessa troca de versão e prévia valida projeto',async()=>{
  const a=setup({current:()=>false});await T.receiveAttachment(message(),a.c);assert.deepEqual(a.replies,[]);
  const b=setup({preview:async()=> 'data:image/png;base64,YWJjZA=='});
  await T.receiveAttachment(message({channel:'mb-attachment-preview-request',attachment:ref()}),b.c);
  assert.equal(b.replies[0].preview,'data:image/png;base64,YWJjZA==');
  await T.receiveAttachment(message({channel:'mb-attachment-preview-request',attachment:ref('a','other')}),b.c);
  assert.ok(b.replies[1].error);
});
