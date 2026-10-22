const assert=require('node:assert/strict'),{test}=require('node:test'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const py=fs.readFileSync(path.join(__dirname,'../../central_comment_visibility.py'),'utf8');
const core=py.split("ARCHIVE_SCRIPT=r'''")[1].split("'''",1)[0];
const done={p:{attempt:{id:'server',project:'p',text:'Corrigir janela'}},q:{attempt:{id:'server-q',project:'q',text:'Corrigir janela'}}};
const note={id:'n',texto:'Corrigir janela',ancora:{base:'body',idx:[]},ox:.3,oy:.5};
const receipt={text:note.texto,pid:'p',attempt:'attempt',saved:true};
function run(notes,receipts={n:receipt},{failHistory=false,origin='http://127.0.0.1:8766',archive=[]}={}){
 const localStorage={'mb-cursor-notas:home':JSON.stringify(notes),'mb-cursor-receipts:home':JSON.stringify(receipts),'mb-cursor-resolvidos:home':JSON.stringify(archive)};
 Object.defineProperties(localStorage,{getItem:{value:k=>localStorage[k]??null},setItem:{value:(k,v)=>{if(failHistory&&k.startsWith('mb-cursor-resolvidos:'))throw new Error('quota');localStorage[k]=v;}}});
 const execute=()=>vm.runInNewContext(core.replace('__RESOLVED__',JSON.stringify(done)),{location:{origin},localStorage});
 execute();return{store:localStorage,execute,notes:()=>JSON.parse(localStorage['mb-cursor-notas:home']),archive:()=>JSON.parse(localStorage['mb-cursor-resolvidos:home'])};
}
test('archive retains full note and receipt before removal; reloading is idempotent',()=>{const r=run([note]);assert.deepEqual(r.notes(),[]);assert.deepEqual(r.archive()[0].note,note);assert.deepEqual(r.archive()[0].receipt,receipt);assert.equal(r.archive()[0].comment_id,'server');assert.equal(JSON.parse(r.store['mb-cursor-receipts:home']).n.attempt,'attempt');r.execute();assert.equal(r.archive().length,1);});
test('unsent, edited, unknown and unfinished notes stay active',()=>{for(const [n,receipts]of[[note,{}],[{...note,texto:'Correção nova'},undefined],[{...note,rascunho:'Pedido novo'},undefined],[{...note,rascunho:''},undefined],[{...note,texto:''},undefined],[note,{n:{...receipt,saved:false}}],[note,{n:{...receipt,pid:'other'}}],[note,{n:{...receipt,attempt:'unknown'}}]]){const r=run([n],receipts);assert.deepEqual(r.notes(),[n]);assert.equal(r.archive().length,0);}});
test('failure to save history keeps every original note',()=>{const r=run([note],undefined,{failHistory:true});assert.deepEqual(r.notes(),[note]);assert.equal(r.archive().length,0);});
test('other origins remain untouched and mixed notes retain their order',()=>{const unrelated={...note,id:'other',texto:'Outra nota'};assert.deepEqual(run([note],undefined,{origin:'https://example.org'}).notes(),[note]);assert.deepEqual(run([unrelated,note,{id:'draft',rascunho:'Texto novo'}]).notes(),[unrelated,{id:'draft',rascunho:'Texto novo'}]);});
test('same attempt in two projects archives the matching record for each',()=>{const other={...note,id:'q'};const r=run([note,other],{n:receipt,q:{...receipt,pid:'q'}});assert.deepEqual(r.notes(),[]);assert.deepEqual(r.archive().map(entry=>entry.comment_id),['server','server-q']);});
