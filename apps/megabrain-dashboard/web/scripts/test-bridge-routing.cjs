// Real payload/receipt behavior for explicit destinations and inherited defaults.
const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const R=require('../src/bridge-routing.ts'),N=require('../src/report-notes.ts');
const route={vendor:'gpt',modelo:'gpt-6.1-sol',effort:'xhigh'},hash='a'.repeat(64);
const view={data:{vendor:'gpt',pipeline:{planejador:route}},vendors:[{id:'gpt',nome:'Codex',ativo:true},{id:'claude',nome:'Claude',ativo:false,motivo:'Cliente desconectado'}],catalogo:[{vendor:'gpt',modelos:[{id:route.modelo,nome:'Sol 6.1',efforts:['high','xhigh']}]}]};

test('unavailable destinations report their reason; invalid effort is never silently normalized',()=>{
 assert.equal(R.routeProblem(view,route),'');
 assert.equal(R.routeProblem(view,{...route,vendor:'claude'}),'Cliente desconectado');
 assert.match(R.routeProblem(view,{...route,effort:'ultra'}),/Esforço indisponível/);
 assert.match(R.routeProblem(view,{...route,modelo:'inventado'}),/Modelo ausente/);
 assert.deepEqual(R.projectRoute(view),route);
});

test('GLM comment override in window mode is blocked without blocking reviewer roles',()=>{
 const glm={vendor:'glm',modelo:'GLM-5.3',effort:'max'};
 const withGLM={...view,data:{...view.data,modo:'janela'},vendors:[...view.vendors,{id:'glm',nome:'ZCode',ativo:true}],catalogo:[...view.catalogo,{vendor:'glm',modelos:[{id:'GLM-5.3',nome:'GLM',efforts:['high','max']}]}]};
 assert.equal(R.routeProblem(withGLM,glm),'');
 assert.match(R.commentRouteProblem(withGLM,glm),/segundo plano/);
 assert.equal(R.commentRouteProblem({...withGLM,data:{...withGLM.data,modo:'segundo_plano'}},glm),'');
});

test('note destination survives upload body, draft, version change, and server receipt',()=>{
 const note={id:'n1',texto:'Mudar a hierarquia',rota:route};
 const body=N.noteBody(note,hash);
 assert.deepEqual(body.feedback.notas[0].rota,route);
 const restored=N.readStored(N.storedValue([note],null)).notas[0];assert.deepEqual(restored.rota,route);
 const carried=N.carryNotes([], [restored],hash)[0];assert.deepEqual(carried.rota,route);
 const receipts=N.readNoteReceipts({notas:[{...note,versao:hash,anexos:[]}]},hash);
 assert.deepEqual(receipts[0].rota,route);
 assert.equal(N.unreceivedDecisionNotes([note],receipts,hash).length,0);
});

test('exact note retry shares a receipt; explicit destination participates in idempotency',()=>{
 const note={id:'same',texto:'Mesmo texto'},explicit={...note,rota:route};
 assert.equal(N.noteFingerprint(note),'Mesmo texto');
 assert.notEqual(N.noteFingerprint(note),N.noteFingerprint(explicit));
 assert.notEqual(N.noteKey('report',note,hash),N.noteKey('report',explicit,hash));
 const sent=N.markSent({},[explicit]);assert.equal(N.unsentNotes([explicit],sent).length,0);
 assert.equal(N.unsentNotes([{...explicit,texto:'Texto editado'}],sent).length,1);
 assert.equal(N.noteBody(note,hash).feedback.notas[0].rota,undefined);
});

test('malformed explicit route never becomes the project default or a successful receipt',async()=>{
 const plain={id:'invalid',texto:'Preservar este pedido'},bad={...plain,rota:{}};
 assert.notEqual(N.noteFingerprint(bad),N.noteFingerprint(plain));
 assert.throws(()=>N.noteBody(bad,hash),/Destino inválido/);
 assert.throws(()=>N.readNoteReceipts({notas:[{...bad,versao:hash,anexos:[]}]},hash),/destino inválido/);
 const restored=N.readStored(N.storedValue([bad],null)).notas[0];assert.deepEqual(restored.rota,{});
 let posts=0;const sent=await N.deliverNotes([restored],hash,async()=>{posts++;});
 assert.equal(posts,0);assert.equal(sent.failed.length,1);assert.match(sent.error,/Destino inválido/);
 assert.equal(N.unsentNotes([restored],N.markSent({},[plain])).length,1);
});

test('receipt names the explicit note destination and never claims execution from delivery',()=>{
 const claude={vendor:'claude',modelo:'claude-opus-5-5',effort:'high'};
 const hint=R.receivedRouteHint(view,[{rota:claude}]);
 assert.match(hint,/Claude/);assert.doesNotMatch(hint,/Codex|segue para|abrindo|iniciou/);
 assert.match(hint,/destino solicitado/);assert.match(hint,/acompanhe a execução/);
 const mixed=R.receivedRouteHint(view,[{rota:claude},{rota:route},{}]);assert.match(mixed,/Claude/);assert.match(mixed,/Codex/);assert.match(mixed,/padrão do projeto/);
 assert.match(R.receivedRouteHint(view,[{}]),/padrão do projeto/);
 assert.equal(R.receivedRouteHint(view,[]),'');
});

test('mixed destination receipt and unnamed queue receipt are readable without invented planner',()=>{
 const mixed=R.bridgeReceiptText({estado:'fila',partes:[{estado:'fila',nome_vendor:'GPT'},{estado:'fila',nome_vendor:'Claude'}]});
 assert.match(mixed,/separadas por destino/);assert.doesNotMatch(mixed,/undefined|planejador|iniciou|abrindo/);
 const unnamed=R.bridgeReceiptText({estado:'fila',em_segundos:180});assert.match(unnamed,/fila de correção/);assert.doesNotMatch(unnamed,/undefined/);
 assert.match(R.bridgeReceiptText({estado:'fila',partes:[{estado:'erro'}]}),/pendências/);
});
