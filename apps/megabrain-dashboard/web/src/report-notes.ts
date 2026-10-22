// 261017 WP2: notas feitas dentro do relatório chegam sozinhas ao projeto.
// Lógica pura (sem React), usada pelo ReportFrame e testada em
// web/scripts/test-report-notes.cjs.

import {attachmentFingerprint,normalizeAttachments,type Attachment} from './attachments';
import {readRoute} from './bridge-routing';

export type ReportNote={id?:string;texto?:string;versao?:string;rota?:unknown;anexos?:Attachment[];[key:string]:unknown};
export type NotesMessage={kind?:string;completa?:boolean;notas?:unknown;enviar?:unknown;removidas?:unknown};
export type SentMap=Record<string,string>;
export type NoteBody={hash:string;feedback:{kind:'notes';notas:ReportNote[]};note:string};
export type DeliveryResult={delivered:ReportNote[];failed:ReportNote[];error:string;previous:boolean};
export const SENT_LIMIT=500;
/** 261018 (A1): teto de envios automáticos por minuto; o excesso espera o botão Enviar ao projeto. */
export const AUTO_PER_MINUTE=20;
const HASH=/^[a-f0-9]{64}$/;

export function noteText(n:ReportNote):string{return typeof n.texto==='string'?n.texto.trim():'';}
function valid(list:unknown):ReportNote[]{
  if(!Array.isArray(list))return [];
  const notes:ReportNote[]=[];
  for(const item of list){
    if(!item||typeof item!=='object'||Array.isArray(item))continue;
    const n=item as ReportNote,anexos=normalizeAttachments(n.anexos);
    if(!noteText(n)&&!anexos.length)continue;
    const note={...n};
    if(anexos.length)note.anexos=anexos;else delete note.anexos;
    notes.push(note);
  }
  return notes;
}
/** Sem anexos conserva o recibo antigo (texto); com anexos identifica o conteúdo inteiro. */
export function noteFingerprint(n:ReportNote):string{
  const anexos=normalizeAttachments(n.anexos);
  const route=readRoute(n.rota);
  if(n.rota!==undefined&&!route)return '\u0000mb-note-invalid-route:'+JSON.stringify([noteText(n),attachmentFingerprint(anexos),n.rota]);
  if(route)return '\u0000mb-note-v3:'+JSON.stringify([noteText(n),attachmentFingerprint(anexos),route]);
  return anexos.length?'\u0000mb-note-v2:'+JSON.stringify([noteText(n),attachmentFingerprint(anexos)]):noteText(n);
}
function tag(n:ReportNote,hash:string):ReportNote{return typeof n.versao==='string'&&HASH.test(n.versao)?n:{...n,versao:hash};}

/** Pendentes depois de uma mensagem de notas do relatório aberto na versão `hash`.
 * completa=true: a mensagem traz todas as notas salvas pelo cursor. Só sai do
 * pacote a nota listada em `removidas` (apagada pela pessoa); ausência na lista
 * não é apagamento (261018, A2). `enviar` traz os ids recém-salvos, que entram
 * para envio automático. Sem completa (relatório antigo ou saveFeedback do
 * próprio relatório): soma por id e marca manual=true, porque não houve gesto
 * do cursor; essas notas esperam o botão Enviar ao projeto (261018, A1). */
export function applyNotesMessage(pending:ReportNote[],incoming:NotesMessage,hash:string):ReportNote[]{
  const list=valid(incoming.notas).map(n=>tag(n,hash));
  if(incoming.completa===true){
    const byId=new Map(list.filter(n=>n.id).map(n=>[String(n.id),n] as const));
    const wanted=new Set((Array.isArray(incoming.enviar)?incoming.enviar:[]).map(String));
    const removed=new Set((Array.isArray(incoming.removidas)?incoming.removidas:[]).map(String));
    const kept:ReportNote[]=[];
    for(const p of pending){
      const id=p.id?String(p.id):'';
      const fresh=id?byId.get(id):undefined;
      if(fresh){kept.push({...fresh,versao:p.versao||hash});continue;}
      if(id&&removed.has(id)&&(p.versao||hash)===hash)continue;
      kept.push(p);
    }
    for(const n of list)if(n.id&&wanted.has(String(n.id))&&!kept.some(k=>k.id===n.id))kept.push(n);
    return kept;
  }
  const merged=[...pending,...list.map(n=>({...n,manual:true}))];
  return merged.filter((n,i)=>!n.id||!merged.slice(i+1).some(m=>m.id===n.id));
}

/** Notas que podem sair sozinhas agora: não enviadas, vindas do cursor (sem manual) e dentro do teto por minuto. */
export function autoQueue(pending:ReportNote[],sent:SentMap,recent:number[],now:number,limit=AUTO_PER_MINUTE):ReportNote[]{
  const room=Math.max(0,limit-recent.filter(t=>now-t<60000).length);
  return unsentNotes(pending,sent).filter(n=>n.manual!==true).slice(0,room);
}

/** Chave fixa por nota (fid + id + versão + texto e anexos): igual em qualquer recarga ou aparelho (261018, A6). */
export function noteKey(fid:string,n:ReportNote,currentHash:string):string{
  const hash=typeof n.versao==='string'&&HASH.test(n.versao)?n.versao:currentHash;
  const source=hash+'|'+String(n.id||'')+'|'+noteFingerprint(n);
  let a=2166136261,b=5381;
  for(let i=0;i<source.length;i++){const c=source.charCodeAt(i);a=Math.imul(a^c,16777619);b=Math.imul(b,33)^c;}
  return `nota-${fid.slice(0,40)}-${String(n.id||'sem-id').slice(0,60)}-${(a>>>0).toString(16)}${(b>>>0).toString(16)}`;
}

/** O servidor é a fonte de recibos entre aparelhos; conserva todas as revisões exatas. */
export function readNoteReceipts(value:unknown,hash:string):ReportNote[]{
  if(!HASH.test(hash)||!value||typeof value!=='object'||Array.isArray(value)||!Array.isArray((value as {notas?:unknown}).notas))throw new Error('Não foi possível conferir as notas recebidas. As respostas continuam preservadas.');
  return ((value as {notas:unknown[]}).notas).map(item=>{
    if(!item||typeof item!=='object'||Array.isArray(item))throw new Error('Recibo de nota inválido. Tente novamente.');
    const n=item as ReportNote,anexos=normalizeAttachments(n.anexos);
    if(typeof n.id!=='string'||!n.id||typeof n.texto!=='string'||n.versao!==hash||!Array.isArray(n.anexos)||anexos.length!==n.anexos.length)throw new Error('Recibo de nota inválido. Tente novamente.');
    if(n.rota!==undefined&&!readRoute(n.rota))throw new Error('Recibo com destino inválido. As notas continuam preservadas; tente novamente.');
    return {id:n.id,texto:n.texto,versao:hash,anexos,...(readRoute(n.rota)?{rota:readRoute(n.rota)}:{})};
  });
}
export function noteVersion(n:ReportNote,fallback:string):string{return typeof n.versao==='string'&&HASH.test(n.versao)?n.versao:fallback;}
export function unreceivedDecisionNotes(notes:ReportNote[],receipts:ReportNote[],hash:string):ReportNote[]{
  return notes.filter(n=>!receipts.some(r=>n.id&&r.id===n.id&&noteVersion(n,hash)===r.versao&&noteFingerprint(n)===noteFingerprint(r)));
}
/** Mantém as respostas e só as notas ainda não recebidas; arquiva o resumo anterior. */
export function decisionFeedback(value:Record<string,unknown>,receipts:ReportNote[],hash:string):Record<string,unknown>{
  const {resumo_respostas,...feedback}=value;
  const notes=Array.isArray(value.notas)?value.notas as ReportNote[]:[];
  const pending=unreceivedDecisionNotes(notes,receipts,hash);
  feedback.notas=pending;
  const original=typeof value.resumo_texto==='string'?value.resumo_texto:'';
  // O marcador é a seção final dos relatórios legados; os atuais fornecem a base separada.
  const marker='\nNOTAS NA PÁGINA\n',index=original.lastIndexOf(marker);
  const base=typeof resumo_respostas==='string'&&resumo_respostas.trim()?resumo_respostas.trim():(index>=0?original.slice(0,index):original).trim();
  const lines=pending.map((n,i)=>`${n.n||i+1}. ${noteText(n)||'Print anexado'}${typeof n.onde==='string'&&n.onde?' (perto de: '+n.onde+')':''}${normalizeAttachments(n.anexos).map(a=>' · '+a.name+' ('+a.path+')').join('')}`);
  const summary=[base,...(lines.length?['NOTAS NA PÁGINA',...lines]:[])].filter(Boolean).join('\n\n');
  if(original||summary){feedback.resumo_texto=summary;if(original!==summary)feedback.resumo_texto_original=typeof value.resumo_texto_original==='string'?value.resumo_texto_original:original;}
  return feedback;
}

/** Notas que ainda não chegaram ao projeto com o texto e os anexos atuais. */
export function unsentNotes(pending:ReportNote[],sent:SentMap):ReportNote[]{return pending.filter(n=>!(n.id&&sent[String(n.id)]===noteFingerprint(n)));}

/** Guarda a identificação do conteúdo enviado (no máximo SENT_LIMIT, as mais recentes). */
export function markSent(sent:SentMap,notes:ReportNote[]):SentMap{
  const next:SentMap={...sent};
  for(const n of notes)if(n.id){const id=String(n.id);delete next[id];next[id]=noteFingerprint(n);}
  const keys=Object.keys(next);
  for(const k of keys.slice(0,Math.max(0,keys.length-SENT_LIMIT)))delete next[k];
  return next;
}

/** Corpo do POST /reports/{fid}/feedback de uma nota: vai com a versão em que foi feita. */
export function noteBody(n:ReportNote,currentHash:string):NoteBody{
  const hash=typeof n.versao==='string'&&HASH.test(n.versao)?n.versao:currentHash;
  // Corpo estável (261018, A6): só campos da nota, sem marcas locais (manual/versao), para a mesma chave valer em qualquer recarga.
  const stable:ReportNote={};
  for(const k of ['id','n','texto','onde','criado_em','ancora','ox','oy','px','py'])if(n[k]!==undefined)stable[k]=n[k];
  const anexos=normalizeAttachments(n.anexos);
  if(anexos.length)stable.anexos=anexos;
  const route=readRoute(n.rota);
  if(n.rota!==undefined&&!route)throw new Error('Destino inválido nesta nota. Escolha IA, modelo e esforço novamente; o rascunho foi preservado.');
  if(route)stable.rota=route;
  return {hash,feedback:{kind:'notes',notas:[stable]},note:''};
}

/** Envia uma nota por vez; falha de uma não impede as outras. */
export async function deliverNotes(queue:ReportNote[],currentHash:string,post:(body:NoteBody,note:ReportNote)=>Promise<unknown>):Promise<DeliveryResult>{
  const result:DeliveryResult={delivered:[],failed:[],error:'',previous:false};
  for(const n of queue){
    try{
      const reply=await post(noteBody(n,currentHash),n) as {versao_anterior?:unknown}|null|undefined;
      result.delivered.push(n);
      if(reply&&typeof reply==='object'&&reply.versao_anterior===true)result.previous=true;
    }catch(error){result.failed.push(n);result.error=(error as Error)?.message||'falha desconhecida';}
  }
  return result;
}

/** Ao abrir a versão nova, as notas pendentes da antiga vão junto (marcadas com a versão de origem). */
export function carryNotes(target:ReportNote[],carried:ReportNote[],fromHash:string):ReportNote[]{
  const out=[...target];
  for(const n of carried){const t=HASH.test(fromHash)?tag(n,fromHash):n;if(t.id&&out.some(o=>o.id===t.id))continue;out.push(t);}
  return out;
}

export function joinText(current:string,carried:string):string{
  const a=current.trim(),b=carried.trim();
  if(!a)return carried;if(!b||a===b)return current;
  return current+'\n\n'+carried;
}

export function sentMessage(count:number,previous:boolean):string{
  return (count===1?'Nota enviada ao projeto ✓':`${count} notas enviadas ao projeto ✓`)+(previous?' · versão anterior':'');
}
export function failedMessage(count:number):string{return (count===1?'1 nota não enviada':`${count} notas não enviadas`)+' · tente de novo';}
export function waitingText(notes:number,decision:boolean):string{
  const parts:string[]=[];
  if(notes)parts.push(notes===1?'1 nota não enviada':`${notes} notas não enviadas`);
  if(decision)parts.push('respostas não enviadas');
  return parts.join(' e ');
}

/** Pacote guardado neste aparelho (formato novo ou o antigo de antes de 261017). */
export function readStored(raw:string|null):{notas:ReportNote[];decisao:Record<string,unknown>|null}{
  try{
    const value=raw?JSON.parse(raw):null;
    if(!value||typeof value!=='object'||Array.isArray(value))return {notas:[],decisao:null};
    if(value.kind==='decisions')return {notas:[],decisao:value};
    const decisao=value.decisao&&typeof value.decisao==='object'&&!Array.isArray(value.decisao)?value.decisao:null;
    return {notas:valid(value.notas),decisao};
  }catch{return {notas:[],decisao:null};}
}
export function storedValue(notas:ReportNote[],decisao:Record<string,unknown>|null):string|null{
  return notas.length||decisao?JSON.stringify({kind:'notes',notas,...(decisao?{decisao}:{})}):null;
}
