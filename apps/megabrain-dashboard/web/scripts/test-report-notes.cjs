// 261017 WP2: logica de envio automatico das notas do relatorio (ReportFrame).
// Roda com: node --test scripts/test-report-notes.cjs (a partir de web/).
const fs=require('node:fs'),ts=require('typescript'),assert=require('node:assert/strict'),{test}=require('node:test');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,f);
const N=require('../src/report-notes.ts');
const {mutationKey}=require('../src/api.ts');

const A='a'.repeat(64),B='b'.repeat(64);
const note=(id,texto,extra={})=>({id,texto,onde:'h1',...extra});

test('lista completa preserva pendências omitidas; exclusão explícita remove só a nota da mesma versão',()=>{
  let pending=N.applyNotesMessage([],{kind:'notes',completa:true,notas:[note('n1','Primeira')],enviar:['n1']},A);
  assert.deepEqual(pending.map(n=>n.id),['n1']);
  assert.equal(pending[0].versao,A);
  // salva a segunda; a primeira continua pendente (ex.: envio falhou)
  pending=N.applyNotesMessage(pending,{kind:'notes',completa:true,notas:[note('n1','Primeira'),note('n2','Segunda')],enviar:['n2']},A);
  assert.deepEqual(pending.map(n=>n.id),['n1','n2']);
  // Uma lista parcial/antiga não pode apagar a primeira nota pendente por omissão.
  pending=N.applyNotesMessage(pending,{kind:'notes',completa:true,notas:[note('n2','Segunda')],enviar:[]},A);
  assert.deepEqual(pending.map(n=>n.id),['n1','n2']);
  // A exclusão precisa do id explícito, conforme o contrato A2 atual.
  pending=N.applyNotesMessage(pending,{kind:'notes',completa:true,notas:[note('n2','Segunda')],enviar:[],removidas:['n1']},A);
  assert.deepEqual(pending.map(n=>n.id),['n2']);
  // notas antigas ja salvas na lista nao entram sem estarem em enviar
  pending=N.applyNotesMessage([],{kind:'notes',completa:true,notas:[note('velha','Antiga'),note('n3','Nova')],enviar:['n3']},A);
  assert.deepEqual(pending.map(n=>n.id),['n3']);
  // texto editado da nota pendente vem da lista
  pending=N.applyNotesMessage([note('n3','Nova',{versao:A})],{kind:'notes',completa:true,notas:[note('n3','Nova editada')],enviar:['n3']},A);
  assert.equal(pending[0].texto,'Nova editada');
});

test('nota levada de outra versao nao some por causa da lista da versao nova',()=>{
  const carried=N.carryNotes([],[note('n1','Feita na versao A')],A);
  assert.equal(carried[0].versao,A);
  const pending=N.applyNotesMessage(carried,{kind:'notes',completa:true,notas:[note('n9','Na versao B')],enviar:['n9']},B);
  assert.deepEqual(pending.map(n=>[n.id,n.versao]),[['n1',A],['n9',B]]);
});

test('relatorio antigo (sem completa) soma por id e a versao mais nova vence',()=>{
  let pending=N.applyNotesMessage([],{kind:'notes',notas:[note('x','um')]},A);
  pending=N.applyNotesMessage(pending,{kind:'notes',notas:[note('x','um editado'),note('y','dois')]},A);
  assert.deepEqual(pending.map(n=>[n.id,n.texto]),[['x','um editado'],['y','dois']]);
  assert.deepEqual(N.applyNotesMessage([],{kind:'notes',notas:[{id:'vazia',texto:'  '},null,'x']},A),[]);
});

test('nota ja enviada com o mesmo texto nao vai de novo; texto editado vai',()=>{
  let sent=N.markSent({},[note('n1','Primeira')]);
  assert.deepEqual(N.unsentNotes([note('n1','Primeira'),note('n2','Segunda')],sent).map(n=>n.id),['n2']);
  assert.deepEqual(N.unsentNotes([note('n1','Primeira editada')],sent).map(n=>n.id),['n1']);
  const many=Array.from({length:N.SENT_LIMIT+20},(_,i)=>note('k'+i,'t'+i));
  sent=N.markSent(sent,many);
  assert.equal(Object.keys(sent).length,N.SENT_LIMIT);
  assert.ok(sent['k'+(N.SENT_LIMIT+19)]);
});

test('cada nota vai com a versao em que foi feita',()=>{
  assert.equal(N.noteBody(note('n1','x',{versao:A}),B).hash,A);
  assert.equal(N.noteBody(note('n1','x'),B).hash,B);
  assert.equal(N.noteBody(note('n1','x',{versao:'curto'}),B).hash,B);
  assert.deepEqual(N.noteBody(note('n1','x'),B).feedback.notas.map(n=>n.id),['n1']);
});

// Servidor falso com o mesmo contrato do create_once: chave repetida + mesmo corpo = mesmo registro.
function fakeServer({failFirst=new Set()}={}){
  const byKey=new Map(),comments=[],calls=[];
  return {comments,calls,async post(body,key){
    calls.push({body,key});
    const digest=JSON.stringify(body);
    if(byKey.has(key)){if(byKey.get(key).digest!==digest)throw Object.assign(new Error('Esta tentativa ja foi usada com outro conteudo.'),{status:409});return byKey.get(key).reply;}
    const id=body.feedback.notas[0].id;
    if(failFirst.has(id)){failFirst.delete(id);// gravou, mas a resposta se perdeu
      const reply={comment:{id:'c'+comments.length},versao_anterior:body.hash===A};comments.push(body);byKey.set(key,{digest,reply});
      throw new TypeError('Failed to fetch');}
    const reply={comment:{id:'c'+comments.length},versao_anterior:body.hash===A};comments.push(body);byKey.set(key,{digest,reply});return reply;
  }};
}

test('envio automatico: falha de rede mantem pendente; nova tentativa usa a mesma chave e nao duplica',async()=>{
  const server=fakeServer({failFirst:new Set(['n1'])});
  const holders=new Map();const holder=n=>{if(!holders.has(n.id))holders.set(n.id,{current:null});return holders.get(n.id);};
  let sent={};
  let pending=N.applyNotesMessage([],{kind:'notes',completa:true,notas:[note('n1','Primeira'),note('n2','Segunda')],enviar:['n1','n2']},B);
  const post=(body,n)=>server.post(body,mutationKey(holder(n),body));
  let result=await N.deliverNotes(N.unsentNotes(pending,sent),B,post);
  assert.deepEqual(result.delivered.map(n=>n.id),['n2']);
  assert.deepEqual(result.failed.map(n=>n.id),['n1']);
  assert.equal(result.error,'Failed to fetch');
  sent=N.markSent(sent,result.delivered);
  pending=N.unsentNotes(pending,sent);
  assert.deepEqual(pending.map(n=>n.id),['n1']);
  assert.equal(N.failedMessage(pending.length),'1 nota não enviada · tente de novo');
  result=await N.deliverNotes(N.unsentNotes(pending,sent),B,post);
  assert.deepEqual(result.delivered.map(n=>n.id),['n1']);
  sent=N.markSent(sent,result.delivered);
  assert.deepEqual(N.unsentNotes(pending,sent),[]);
  // n1 foi gravada uma vez so, apesar de duas tentativas
  assert.equal(server.comments.filter(c=>c.feedback.notas[0].id==='n1').length,1);
  assert.equal(server.comments.length,2);
  const keysN1=server.calls.filter(c=>c.body.feedback.notas[0].id==='n1').map(c=>c.key);
  assert.equal(keysN1.length,2);assert.equal(keysN1[0],keysN1[1]);
  const keyN2=server.calls.find(c=>c.body.feedback.notas[0].id==='n2').key;
  assert.notEqual(keyN2,keysN1[0]);
});

test('nota da versao anterior chega marcada e o aviso diz isso',async()=>{
  const server=fakeServer();
  const holder={current:null};
  const result=await N.deliverNotes([note('n1','Feita na A',{versao:A})],B,(body)=>server.post(body,mutationKey(holder,body)));
  assert.equal(server.comments[0].hash,A);
  assert.equal(result.previous,true);
  assert.equal(N.sentMessage(1,result.previous),'Nota enviada ao projeto ✓ · versão anterior');
  assert.equal(N.sentMessage(3,false),'3 notas enviadas ao projeto ✓');
});

test('pacote guardado no aparelho: formato antigo e novo',()=>{
  assert.deepEqual(N.readStored(null),{notas:[],decisao:null});
  assert.deepEqual(N.readStored('{quebrado'),{notas:[],decisao:null});
  const legacyNotes=N.readStored(JSON.stringify({kind:'notes',notas:[note('a','um'),{id:'b',texto:''}]}));
  assert.deepEqual(legacyNotes.notas.map(n=>n.id),['a']);
  const legacyDecision=N.readStored(JSON.stringify({kind:'decisions',finalizado:false,respostas:{q:'1'}}));
  assert.equal(legacyDecision.decisao.kind,'decisions');assert.deepEqual(legacyDecision.notas,[]);
  const raw=N.storedValue([note('a','um')],{kind:'decisions',finalizado:true});
  assert.deepEqual(N.readStored(raw).notas.map(n=>n.id),['a']);
  assert.equal(N.readStored(raw).decisao.finalizado,true);
  assert.equal(N.storedValue([],null),null);
});

test('abrir versao nova leva o texto livre e as notas pendentes',()=>{
  assert.equal(N.joinText('','rascunho antigo'),'rascunho antigo');
  assert.equal(N.joinText('mesmo','mesmo'),'mesmo');
  assert.equal(N.joinText('novo','antigo'),'novo\n\nantigo');
  const out=N.carryNotes([note('n1','ja na nova',{versao:B})],[note('n1','duplicada'),note('n2','so na antiga')],A);
  assert.deepEqual(out.map(n=>[n.id,n.versao]),[['n1',B],['n2',A]]);
  assert.equal(N.waitingText(1,false),'1 nota não enviada');
  assert.equal(N.waitingText(2,true),'2 notas não enviadas e respostas não enviadas');
});

const receiptImage=id=>({id,path:`.mb-anexos/${id}.png`,name:`${id}.png`,mime:'image/png',size:30,url:`/api/projects/p1/attachments/${id}`});
test('recibos preservam revisões históricas e deduplicam só id+texto+imagem+versão exatos',()=>{
  const received=N.readNoteReceipts({notas:[note('n1','original',{versao:A,anexos:[receiptImage('img-a')]}),note('n1','editada',{versao:A,anexos:[receiptImage('img-b')]})]},A);
  assert.equal(received.length,2);
  const candidates=[note('n1','original',{anexos:[receiptImage('img-a')],n:999,ancora:'#renumerada'}),note('n1','editada',{anexos:[receiptImage('img-b')]}),note('n1','texto novo',{anexos:[receiptImage('img-a')]}),note('n1','original',{anexos:[receiptImage('img-c')]}),note('n1','original',{versao:B,anexos:[receiptImage('img-a')]}),note('outro','original',{anexos:[receiptImage('img-a')]})];
  assert.deepEqual(N.unreceivedDecisionNotes(candidates,received,A),candidates.slice(2));
  assert.deepEqual(N.unreceivedDecisionNotes([candidates[0]],received,B),[candidates[0]]);
});
test('recibo malformado ou de outra versão bloqueia a conferência; não vira lista vazia',()=>{
  for(const value of [null,{}, {notas:null},{notas:[{id:'x',texto:'texto',versao:B,anexos:[]}]},{notas:[{id:'x',texto:'texto',versao:A,anexos:[{invalid:true}]}]}])assert.throws(()=>N.readNoteReceipts(value,A));
  assert.deepEqual(N.readNoteReceipts({notas:[]},A),[]);
});
test('resumo de decisão remove notas já recebidas, conserva novas e arquiva o original sem mutar entrada',()=>{
  const old=note('recebida','Texto antigo',{versao:A,anexos:[receiptImage('img-a')]}),fresh=note('nova','Texto novo',{anexos:[receiptImage('img-b')]});
  const original='RESPOSTAS\nPergunta → Sim\n\nNOTAS NA PÁGINA\n1. Texto antigo\n2. Texto novo';
  const input={kind:'decisions',respostas:{q:{valor:'sim'}},notas:[old,fresh],resumo_texto:original,resumo_respostas:'RESPOSTAS\nPergunta → Sim'};
  const out=N.decisionFeedback(input,[old],A);
  assert.deepEqual(out.notas,[fresh]);assert.match(out.resumo_texto,/Pergunta → Sim/);assert.match(out.resumo_texto,/Texto novo/);assert.doesNotMatch(out.resumo_texto,/Texto antigo/);assert.equal(out.resumo_texto_original,original);assert.equal(input.notas.length,2);assert.equal(input.resumo_texto,original);assert.equal(out.resumo_respostas,undefined);
});
test('resumo legado sem base separada conserva respostas e retira a seção final de notas recebidas',()=>{
  const old=note('n1','Já recebido',{versao:A,anexos:[]});
  const out=N.decisionFeedback({notas:[old],resumo_texto:'Pergunta → Sim\n\nNOTAS NA PÁGINA\n1. Já recebido (perto de: h1)'},[old],A);
  assert.equal(out.resumo_texto,'Pergunta → Sim');assert.deepEqual(out.notas,[]);assert.match(out.resumo_texto_original,/Já recebido/);
});
