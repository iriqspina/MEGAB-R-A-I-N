// 261018: integra opções reais do CursorTools com DOM/API/React isolados.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const attachments=require('../src/attachments.ts'),notes=require('../src/report-notes.ts');
const source=ts.transpileModule(fs.readFileSync(path.join(__dirname,'../src/CursorTools.tsx'),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const ref=(id='print-a',pid='board-two')=>({id,path:`.mb-anexos/${id}.png`,name:`${id}.png`,mime:'image/png',size:10,url:`/api/projects/${pid}/attachments/${id}`});
const note=(extra={})=>({id:'nota-1',texto:'',onde:'Detalhe',criado_em:'2026-10-18T20:20:00Z',ancora:{base:'#board-two',idx:[]},ox:.2,oy:.4,...extra});
const flush=async()=>{for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));};
function harness({stored={},failFirst=false}={}){
 const storage=new Map(Object.entries(stored)),calls=[],saved=[],errors=[],reloads=[],uploadCalls=[],previewCalls=[];
 let options,cleanup,attempt=0,failed=false;
 const element={children:[],closest(selector){return selector==='[data-cf-project]'?{dataset:{cfProject:'board-two'}}:selector==='[data-cf-module]'?{dataset:{cfModule:'results'}}:null;}};
 const body={children:[],closest(){return null;}};
 const window={CursorFerramentas:{iniciar(value){options=value;return {destruir(){calls.push({cleanup:true});}};}}};
 const module={exports:{}};
 const sandbox={module,exports:module.exports,window,document:{body,querySelector(){return element;}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},crypto:{randomUUID:()=>`tentativa-${++attempt}`},
  require(name){if(name==='react')return {useEffect(fn){cleanup=fn();},useRef(value){return {current:value};}};
   if(name==='./api')return {api:async(route,method,payload,key)=>{calls.push({route,method,payload,key});if(route==='/session')return {central_project_id:'central'};if(failFirst&&!failed){failed=true;throw new Error('rede indisponível');}return {comment:{id:'ok'}};}};
   if(name==='./attachments')return {...attachments,uploadAttachment:async(pid,file)=>{uploadCalls.push({pid,file});return ref('upload',pid);},previewAttachment:async(pid,attachment)=>{previewCalls.push({pid,attachment});return 'data:image/png;base64,PREVIA';}};
   if(name==='./report-notes')return notes;if(name==='./bridge-routing')return require('../src/bridge-routing.ts');throw new Error('Import inesperado: '+name);
  }
 };
 vm.runInNewContext(source,sandbox,{filename:'CursorTools.tsx'});
 module.exports.default({projectKey:'home',onSaved:m=>saved.push(m),onError:e=>errors.push(e),onReload:p=>reloads.push(p)});
 return {async ready(){await flush();return options;},storage,calls,saved,errors,reloads,uploadCalls,previewCalls,cleanup:()=>cleanup?.()};
}

test('callback upload/preview usa projeto da âncora no painel comparado e central fora de quadro',async()=>{
 const h=harness(),options=await h.ready(),file={name:'print.png'};
 assert.equal(options.segurarMs,400);assert.equal(options.cancelarAoMover,true);
 const uploaded=await options.anexos.upload(file,note());
 assert.equal(h.uploadCalls[0].pid,'board-two');assert.equal(uploaded.url,'/api/projects/board-two/attachments/upload');
 assert.equal(await options.anexos.preview(uploaded,note()),'data:image/png;base64,PREVIA');
 assert.equal(h.previewCalls[0].pid,'board-two');
 await options.anexos.upload(file,note({ancora:{base:'body',idx:[]}}));assert.equal(h.uploadCalls[1].pid,'central');
 h.cleanup();assert.equal(h.calls.at(-1).cleanup,true);
});

test('nota só com print chega ao comentário com referências, âncora e procedência',async()=>{
 const h=harness(),options=await h.ready();
 options.aoSalvarNota(note({anexos:[{...ref(),preview:'data:image/png;base64,NUNCA',file:{}}]}));await flush();
 const posts=h.calls.filter(c=>c.method==='POST');assert.equal(posts.length,1);
 const call=posts[0];assert.equal(call.route,'/projects/board-two/comments');assert.equal(call.payload.text,'');
 assert.deepEqual(call.payload.anexos,[ref()]);assert.equal(call.payload.target,'module:results');
 assert.equal(JSON.stringify(call.payload.anchor),JSON.stringify({x:.2,y:.4}));
 assert.equal(call.payload.cursor_source.note_id,'nota-1');assert.equal(call.payload.cursor_source.storage_key,'mb-cursor-notas:home');
 assert.ok(!JSON.stringify(call.payload).includes('NUNCA'));assert.ok(h.saved.includes('Nota enviada ao projeto ✓'));
 assert.equal(h.reloads[0],'board-two');
});

test('rota da nota chega ao projeto e texto editado mantém identidade e destino',async()=>{
 const h=harness(),options=await h.ready(),rota={vendor:'gpt',modelo:'gpt-6.1-sol',effort:'xhigh'};
 options.aoSalvarNota(note({texto:'Ajustar a grade',rota}));await flush();
 options.aoSalvarNota(note({texto:'Ajustar a grade e a escala',rota}));await flush();
 const posts=h.calls.filter(c=>c.method==='POST');assert.equal(posts.length,2);
 for(const p of posts){assert.deepEqual(p.payload.rota,rota);assert.equal(p.payload.cursor_source.note_id,'nota-1');}
 assert.notEqual(posts[0].key,posts[1].key);
 await options.carregarPonte(note());assert.equal(h.calls.at(-1).route,'/projects/board-two/bridge');
});

test('salvar novamente evita duplicata; trocar só a imagem gera tentativa nova',async()=>{
 const h=harness(),options=await h.ready();
 options.aoSalvarNota(note({texto:'Veja',anexos:[ref()]}));await flush();
 options.aoSalvarNota(note({texto:'Veja',anexos:[ref()]}));await flush();
 assert.equal(h.calls.filter(c=>c.method==='POST').length,1);
 options.aoSalvarNota(note({texto:'Veja',anexos:[ref('print-b')]}));await flush();
 const posts=h.calls.filter(c=>c.method==='POST');assert.equal(posts.length,2);assert.notEqual(posts[0].key,posts[1].key);
 options.aoSalvarNota(note({texto:'Veja',anexos:[]}));await flush();assert.equal(h.calls.filter(c=>c.method==='POST').length,3);
});

test('recibo legado confirma texto sem imagem, mas nunca confirma a imagem nova',async()=>{
 const legacy=JSON.stringify({'nota-1':{text:'Veja',pid:'board-two',attempt:'legado',saved:true}});
 const h=harness({stored:{'mb-cursor-receipts:home':legacy}}),options=await h.ready();
 options.aoSalvarNota(note({texto:'Veja'}));await flush();assert.equal(h.calls.length,0);
 options.aoSalvarNota(note({texto:'Veja',anexos:[ref()]}));await flush();
 assert.equal(h.calls.filter(c=>c.method==='POST').length,1);assert.notEqual(h.calls[0].key,'legado');
});

test('falha preserva nota local e tentativa; reenvio só confirma depois de receber sucesso',async()=>{
 const h=harness({failFirst:true}),options=await h.ready(),original=note({anexos:[ref()]});
 options.aoSalvarNota(original);await flush();
 assert.equal(h.errors.length,1);assert.ok(h.saved.some(m=>m.includes('preservada')));
 let receipt=JSON.parse(h.storage.get('mb-cursor-receipts:home'))['nota-1'];assert.ok(!receipt.saved);
 options.aoSalvarNota(original);await flush();
 const posts=h.calls.filter(c=>c.method==='POST');assert.equal(posts.length,2);assert.equal(posts[0].key,posts[1].key);
 receipt=JSON.parse(h.storage.get('mb-cursor-receipts:home'))['nota-1'];assert.equal(receipt.saved,true);
 assert.ok(!JSON.stringify(receipt).includes('base64'));
});

test('duas edições rápidas copiam o conteúdo ao enfileirar, sem misturar rascunhos',async()=>{
 const h=harness(),options=await h.ready(),same=note({texto:'Primeira',anexos:[ref()]});
 options.aoSalvarNota(same);same.texto='Segunda';same.anexos[0]=ref('print-b');options.aoSalvarNota(same);
 await flush();const posts=h.calls.filter(c=>c.method==='POST');
 assert.equal(posts.length,2);assert.equal(posts[0].payload.text,'Primeira');assert.equal(posts[0].payload.anexos[0].id,'print-a');
 assert.equal(posts[1].payload.text,'Segunda');assert.equal(posts[1].payload.anexos[0].id,'print-b');
});

test('nota vazia com File transitório ou referência inválida não é enviada',async()=>{
 const h=harness(),options=await h.ready();
 options.aoSalvarNota(note({anexos:[{name:'print.png',type:'image/png',size:1}]}));
 options.aoSalvarNota(note({anexos:[{...ref(),mime:'image/svg+xml'}]}));await flush();
 assert.equal(h.calls.length,0);assert.equal(h.storage.size,0);
});
