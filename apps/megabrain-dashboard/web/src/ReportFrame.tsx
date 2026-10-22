import {useEffect,useRef,useState} from 'react';
import {Check,MessageCircle,Send,LoaderCircle,RotateCw,Network,Power} from 'lucide-react';
import {api,ApiError,mutationKey,type MutationAttempt} from './api';
import {useBridge,RouteChoice} from './BridgePanel';
import {bridgeReceiptText as bridgeText,commentRouteProblem,projectRoute,readRoute,receivedRouteHint,routeName} from './bridge-routing';
import type {BridgeReceipt,BridgeRoute} from './types';
import AttachmentInput from './AttachmentInput';
import {normalizeAttachments,type Attachment} from './attachments';
import {receiveAttachment} from './attachment-transport';
import {REPORT_BEFORE_CLOSE} from './report-attachment-guard';
import {applyNotesMessage,autoQueue,carryNotes,decisionFeedback,deliverNotes,joinText,markSent,noteKey,noteText,noteVersion,readNoteReceipts,readStored,sentMessage,failedMessage,storedValue,unreceivedDecisionNotes,waitingText,type NotesMessage,type ReportNote,type SentMap} from './report-notes';

// 261017 WP2: cada nota salva dentro do relatório vai sozinha ao projeto, sem
// segundo clique, com uma tentativa idempotente por nota. O relatório recebe a
// confirmação (megabrain-report-ack). Versão nova no meio do comentário não
// bloqueia o envio: o servidor guarda com a versão aberta, marcada como anterior.
type Decision=Record<string,unknown>;
type Carry={from:string;notes:ReportNote[];decision:Decision|null;note:string;anexos:Attachment[]};
const HASH=/^[a-f0-9]{64}$/;
// A change of version may reunite two drafts. Show every reference, then send
// batches of six; normalizing the entire merged list would hide the overflow.
function mergeImages(...lists:unknown[]):Attachment[]{const all=new Map<string,Attachment>();for(const list of lists)if(Array.isArray(list))for(const value of list){const a=normalizeAttachments([value])[0];if(a)all.set(a.url,a);}return [...all.values()];}
export default function ReportFrame({fid,title,projectId,onOpen}:{fid:string;title:string;projectId?:string;onOpen?:(url:string)=>void}){
  const frame=useRef<HTMLIFrameElement>(null);
  const token=useRef(crypto.randomUUID());
  const attempt=useRef<MutationAttempt|null>(null);
  const decisionAttempt=useRef<MutationAttempt|null>(null);
  const noteAttempts=useRef(new Map<string,{current:MutationAttempt|null}>());
  const draftQueue=useRef(Promise.resolve());
  const currentHash=useRef('');
  const pendingRef=useRef<ReportNote[]>([]);
  const decisionRef=useRef<Decision|null>(null);
  const sentRef=useRef<SentMap>({});
  const carry=useRef<Carry|null>(null);
  const flushing=useRef(false);
  const flushFinished=useRef<Promise<void>>(Promise.resolve());
  const flushAfterDecision=useRef(false);
  const flushAgain=useRef(false);
  const autoTimes=useRef<number[]>([]);
  const [version,setVersion]=useState(0);
  const [updated,setUpdated]=useState(false);
  const [pending,setPendingState]=useState<ReportNote[]>([]);
  const [decision,setDecisionState]=useState<Decision|null>(null);
  const [sending,setSending]=useState(false);
  const [hash,setHash]=useState('');
  const [notice,setNotice]=useState('Carregando o relatório…');
  const [busy,setBusy]=useState(false);
  const [note,setNote]=useState('');
  const [routeDraft,setRouteDraft]=useState<{fid:string;value?:BridgeRoute}>({fid});
  const route=routeDraft.fid===fid?routeDraft.value:undefined;
  function setRoute(value:BridgeRoute|undefined){setRouteDraft({fid,value});}
  const routeRef=useRef(route);routeRef.current=route;
  const [attachments,setAttachments]=useState<Attachment[]>([]);
  const [uploading,setUploading]=useState(false);
  const uploadBusy=useRef(false);uploadBusy.current=uploading;
  const decisionSending=useRef(false);
  const canonicalBlocked=useRef(false);
  const closingBlocked=useRef(false);closingBlocked.current=busy||sending;
  const uploads=useRef(new Set<string>());
  const noteRef=useRef(note);noteRef.current=note;
  const attachmentsRef=useRef(attachments);attachmentsRef.current=attachments;
  const [available,setAvailable]=useState(false);
  const [loadError,setLoadError]=useState('');
  const sentKey=`mb-report-sent:${fid}`;
  const bridge=useBridge(projectId);
  const [bridgeBusy,setBridgeBusy]=useState(false);
  const bridgeRef=useRef(bridge.view);bridgeRef.current=bridge.view;
  useEffect(()=>{void bridge.load().catch(()=>{});},[bridge.load]);
  useEffect(()=>{try{setRoute(readRoute(JSON.parse(localStorage.getItem(`mb-report-route:${fid}`)||'null')));}catch{setRoute(undefined);}},[fid]);
  useEffect(()=>{if(routeDraft.fid!==fid)return;try{if(route)localStorage.setItem(`mb-report-route:${fid}`,JSON.stringify(route));else localStorage.removeItem(`mb-report-route:${fid}`);}catch{}},[fid,route,routeDraft.fid]);
  function sendBridge(){const view=bridgeRef.current;if(!view||!currentHash.current)return;frame.current?.contentWindow?.postMessage({channel:'megabrain-report-bridge',fid,token:token.current,hash:currentHash.current,catalogo:view.catalogo||[],vendors:view.vendors,data:view.data},window.location.origin);}
  useEffect(()=>{sendBridge();},[bridge.view,hash]);
  async function bridgeSave(patch:{vendor?:string;auto?:boolean}){const current=bridge.view;if(!current)return;setBridgeBusy(true);try{await bridge.save(current,patch);}catch(e){setNotice((e as Error).message);void bridge.load().catch(()=>{});}finally{setBridgeBusy(false);}}
  function setPending(list:ReportNote[]){pendingRef.current=list;setPendingState(list);}
  function setDecision(value:Decision|null){decisionRef.current=value;setDecisionState(value);}
  function ack(ok:boolean,ids:string[],message:string,notes:ReportNote[]=[]){frame.current?.contentWindow?.postMessage({channel:'megabrain-report-ack',fid,token:token.current,ids,notas:notes.map(n=>({id:n.id,texto:n.texto||'',anexos:normalizeAttachments(n.anexos),...(n.rota!==undefined?{rota:n.rota}:{})})),ok,message},window.location.origin);}
  function holder(n:ReportNote){const id=n.id?String(n.id):'sem-id:'+String(n.texto||'');let h=noteAttempts.current.get(id);if(!h){h={current:null};noteAttempts.current.set(id,h);}return h;}
  async function receivedNotes(notes:ReportNote[],fallback:string){
    const receipts:ReportNote[]=[];
    for(const digest of new Set(notes.map(n=>noteVersion(n,fallback))))receipts.push(...readNoteReceipts(await api(`/reports/${encodeURIComponent(fid)}/note-receipts?hash=${encodeURIComponent(digest)}`),digest));
    return receipts;
  }
  // 261018 (A1): sozinho só sai o que o cursor salvou, até 20 por minuto; o resto espera o botão (manual=true).
  async function flushNotes(manual=false){
    if(uploadBusy.current||canonicalBlocked.current||uploads.current.size)return;
    if(decisionSending.current){flushAfterDecision.current=true;return;}
    if(flushing.current){flushAgain.current=true;return;}
    let finish=()=>{};flushFinished.current=new Promise<void>(resolve=>{finish=resolve;});
    flushing.current=true;setSending(true);
    try{
      do{
        flushAgain.current=false;
        const current=currentHash.current;if(!current)return;
        const snapshot=pendingRef.current;if(!snapshot.length)continue;
        const receipts=await receivedNotes(snapshot,current);
        const unsent=unreceivedDecisionNotes(snapshot,receipts,current);
        const received=snapshot.filter(n=>!unsent.includes(n));
        if(received.length){
          sentRef.current=markSent(sentRef.current,received);
          try{localStorage.setItem(sentKey,JSON.stringify(sentRef.current));}catch{}
          const done=new Set(received);setPending(pendingRef.current.filter(n=>!done.has(n)));
          const message=received.length===1?'Nota já recebida no projeto ✓':'Notas já recebidas no projeto ✓';setNotice(message);ack(true,received.map(n=>String(n.id||'')).filter(Boolean),message,received);
        }
        const queue=manual?unsent:autoQueue(unsent,{},autoTimes.current,Date.now());
        if(!queue.length)continue;
        setNotice('Enviando ao projeto…');
        const result=await deliverNotes(queue,current,(body,n)=>api(`/reports/${encodeURIComponent(fid)}/feedback`,'POST',body,noteKey(fid,n,current)));
        if(result.delivered.length){
          if(!manual){const now=Date.now();autoTimes.current=[...autoTimes.current.filter(t=>now-t<60000),...result.delivered.map(()=>now)];}
          sentRef.current=markSent(sentRef.current,result.delivered);
          try{localStorage.setItem(sentKey,JSON.stringify(sentRef.current));}catch{}
          for(const n of result.delivered)if(n.id)noteAttempts.current.delete(String(n.id));
          const done=new Set(result.delivered);
          setPending(pendingRef.current.filter(n=>!done.has(n)));
          const message=sentMessage(result.delivered.length,result.previous)+receivedRouteHint(bridgeRef.current,result.delivered);
          setNotice(message);ack(true,result.delivered.map(n=>String(n.id||'')).filter(Boolean),message,result.delivered);
        }
        if(result.failed.length){
          setNotice('Não consegui enviar agora'+(result.error?': '+result.error:'.'));
          ack(false,result.failed.map(n=>String(n.id||'')).filter(Boolean),failedMessage(result.failed.length),result.failed);
        }
      }while(flushAgain.current);
    }catch(e){const message='Não consegui conferir as notas recebidas: '+((e as Error).message||'falha desconhecida');setNotice(message);ack(false,pendingRef.current.map(n=>String(n.id||'')).filter(Boolean),message,pendingRef.current);}
    finally{flushing.current=false;setSending(decisionSending.current);finish();}
  }
  async function sendDecision(){
    if(uploadBusy.current||canonicalBlocked.current||uploads.current.size||decisionSending.current)return;
    const value=decisionRef.current,current=currentHash.current;
    if(!value||value.finalizado!==true||!current)return;
    const {versao,...snapshot}=value;
    const openedHash=typeof versao==='string'&&HASH.test(versao)?versao:current;
    const signature=JSON.stringify([openedHash,snapshot.respostas,snapshot.notas]);
    decisionSending.current=true;setSending(true);
    try{
      // Bloqueia duplo clique antes do primeiro await; uma nota em voo termina antes da consulta.
      await flushFinished.current;
      const notes=Array.isArray(snapshot.notas)?snapshot.notas as ReportNote[]:[];
      const receipts=await receivedNotes(notes,openedHash);
      if(uploadBusy.current||canonicalBlocked.current||uploads.current.size)throw new Error('Espere os prints terminarem. As respostas continuam preservadas.');
      const feedback=decisionFeedback(snapshot,receipts,openedHash);
      const body={hash:openedHash,feedback,note:''};
      const reply=await api<{ponte?:BridgeReceipt}>(`/reports/${encodeURIComponent(fid)}/feedback`,'POST',body,mutationKey(decisionAttempt,body));
      decisionAttempt.current=null;const latest=decisionRef.current;if(latest&&JSON.stringify([typeof latest.versao==='string'&&HASH.test(latest.versao)?latest.versao:current,latest.respostas,latest.notas])===signature)setDecision(null);
      setNotice('Respostas enviadas ao projeto ✓'+bridgeText(reply?.ponte??null));ack(true,[],'Respostas enviadas ao projeto ✓');
    }catch(e){setNotice('Respostas não enviadas: '+((e as Error).message||'falha desconhecida'));ack(false,[],'Respostas não enviadas · tente de novo');}
    finally{decisionSending.current=false;setSending(flushing.current);if(flushAfterDecision.current){flushAfterDecision.current=false;void flushNotes();}}
  }
  async function retry(){await flushNotes(true);if(decisionRef.current?.finalizado===true)await sendDecision();}
  useEffect(()=>{try{const value=JSON.parse(localStorage.getItem(sentKey)||'{}');sentRef.current=value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{sentRef.current={};}},[sentKey]);
  useEffect(()=>{
    const close=(event:Event)=>{const detail=(event as CustomEvent).detail;if(!detail||detail.pid!==(projectId||'')||(detail.fid&&detail.fid!==fid))return;if(closingBlocked.current||uploadBusy.current||canonicalBlocked.current||uploads.current.size||flushing.current||decisionSending.current){event.preventDefault();setNotice('Conclua ou remova o print pendente antes de fechar. O rascunho continua aqui.');}};
    window.addEventListener(REPORT_BEFORE_CLOSE,close);return()=>window.removeEventListener(REPORT_BEFORE_CLOSE,close);
  },[fid,projectId]);
  useEffect(()=>{
    const receive=(event:MessageEvent)=>{
      const expectedToken=token.current,expectedHash=currentHash.current,source=frame.current?.contentWindow||null;
      void receiveAttachment(event,{source,origin:window.location.origin,fid,token:expectedToken,hash:expectedHash,pid:projectId||'',pending:uploads.current,current:()=>token.current===expectedToken&&currentHash.current===expectedHash&&frame.current?.contentWindow===source,reply:message=>source?.postMessage(message,window.location.origin)});
    };
    window.addEventListener('message',receive);return()=>window.removeEventListener('message',receive);
  },[fid,projectId]);
  useEffect(()=>{
    let active=true;
    setAvailable(false);setLoadError('');
    async function prepare(){
      try{
        try{await api(`/reports/${encodeURIComponent(fid)}/status`);}
        catch(error){
          // Restored previews may arrive before the project's files are indexed.
          // Recover once through the permitted project catalogue, then mount.
          if(!(error instanceof ApiError)||error.status!==404||!projectId)throw error;
          await api(`/projects/${encodeURIComponent(projectId)}`);
          await api(`/reports/${encodeURIComponent(fid)}/status`);
        }
        if(active)setAvailable(true);
      }catch(error){if(active){setLoadError((error as Error).message);setNotice('Não foi possível abrir este relatório. Tente novamente.');}}
    }
    void prepare();return()=>{active=false;};
  },[fid,projectId,version]);
  useEffect(()=>{
    const receive=async(event:MessageEvent)=>{
      const data=event.data;
      if(event.origin!==window.location.origin||event.source!==frame.current?.contentWindow||!data||data.channel!=='megabrain-report'||data.fid!==fid||data.token!==token.current||!/^([a-f0-9]{64})$/.test(data.hash||''))return;
      if(data.kind==='project-control'){
        if(data.hash!==currentHash.current)return;
        const payload=data.payload||{},mode=payload.modo;
        if(typeof payload.requestId!=='string'||payload.requestId.length>100)return;
        const reply=(value:unknown,error?:string)=>frame.current?.contentWindow?.postMessage({channel:'megabrain-report-control-result',fid,token:token.current,hash:data.hash,requestId:payload.requestId,value,error},window.location.origin);
        try{const value=await api(`/projects/${encodeURIComponent(projectId||'')}/control`,mode?'PUT':'GET',mode?{revision:payload.revision,modo:mode}:undefined);reply(value);}
        catch(e){reply(null,(e as Error).message);}
        return;
      }
      if(data.kind==='stale'){setNotice('O relatório mudou durante a abertura. Reabra a versão atual.');setUpdated(true);return;}
      if(data.kind==='attachment-state'){if(data.hash===currentHash.current)canonicalBlocked.current=data.payload?.blocked===true;return;}
      setHash(data.hash);
      if(data.kind==='ready'){
        if(currentHash.current!==data.hash){
          const previous=carry.current;carry.current=null;currentHash.current=data.hash;
          let text='',stored=readStored(null),images:Attachment[]=[];
          try{text=localStorage.getItem(`mb-report-note:${fid}:${data.hash}`)||'';stored=readStored(localStorage.getItem(`mb-report-feedback:${fid}:${data.hash}`));images=mergeImages(JSON.parse(localStorage.getItem(`mb-report-attachments:${fid}:${data.hash}`)||'[]'));}catch{}
          let notes=stored.notas,choice=stored.decisao;
          if(previous){
            // Abrir a versão nova leva junto o que ainda não chegou ao projeto.
            notes=carryNotes(notes,previous.notes,previous.from||data.hash);
            choice=choice||previous.decision;text=joinText(text,previous.note);
            images=mergeImages(images,previous.anexos);
            if(previous.from&&previous.from!==data.hash){try{localStorage.removeItem(`mb-report-feedback:${fid}:${previous.from}`);localStorage.removeItem(`mb-report-note:${fid}:${previous.from}`);}catch{}}
          }
          // 261018 (A3): pendentes guardados sob versões antigas deste relatório voltam e tentam sair de novo.
          try{
            const prefix=`mb-report-feedback:${fid}:`;
            for(const key of Object.keys(localStorage)){
              const from=key.startsWith(prefix)?key.slice(prefix.length):'';
              if(!HASH.test(from)||from===data.hash)continue;
              const old=readStored(localStorage.getItem(key));
              notes=carryNotes(notes,old.notas,from);choice=choice||(old.decisao?{...old.decisao,versao:from}:null);
              localStorage.removeItem(key);
            }
          }catch{}
          setNote(text);setAttachments(images);setPending(notes);setDecision(choice);
          if(notes.length)void flushNotes();
        }
        setNotice('Relatório aberto. Cada nota salva vai sozinha para o projeto.');
        sendBridge();
      }
      if(data.kind==='feedback'){
        const incoming=(data.payload||{}) as NotesMessage&Decision;
        if(incoming.kind==='notes'){setPending(applyNotesMessage(pendingRef.current,incoming,data.hash));void flushNotes();}
        else if(incoming.kind==='decisions'){
          setDecision({...incoming,versao:data.hash});
          if(incoming.finalizado===true)void sendDecision();
          else setNotice('Respostas guardadas. Finalize no relatório para enviar ao projeto.');
        }
      }
      if(data.kind==='draft'){
        const payload={hash:data.hash,storage:data.payload?.storage};
        draftQueue.current=draftQueue.current.then(async()=>{try{await api(`/reports/${fid}/draft`,'POST',payload);}catch(e){setNotice(e instanceof ApiError?e.message:'Rascunho ainda não salvo; mantenha este relatório aberto.');}});
      }
      if(data.kind==='open-local'){
        try{const result=await api<{item:{url:string}}>(`/reports/${fid}/resolve`,'POST',{path:data.payload?.path,hash:data.hash});if(onOpen)onOpen(result.item.url);else window.dispatchEvent(new CustomEvent('mb-open-item',{detail:result}));}
        catch(e){setNotice((e as Error).message);}
      }
      if(data.kind==='open-external')setNotice('Esta fonte está fora dos relatórios locais. O endereço continua registrado; nenhuma janela externa foi aberta.');
      if(data.kind==='dispatch'){
        const payload=(data.payload||{}) as {ia?:string;modelo?:string;effort?:string;resumo_texto?:string;respostas?:unknown;notas?:unknown;titulo?:string;finalizado?:boolean};
        const body={hash:data.hash,ia:payload.ia,modelo:payload.modelo,effort:payload.effort,resumo_texto:payload.resumo_texto,respostas:payload.respostas,notas:payload.notas,titulo:payload.titulo,finalizado:payload.finalizado===true};
        const reply=(ok:boolean,message:string)=>{frame.current?.contentWindow?.postMessage({channel:'megabrain-report-dispatch-result',fid,token:token.current,ok,message},'*');};
        try{
          const result=await api<{ok?:boolean;message?:string}>(`/dispatch/${encodeURIComponent(fid)}`,'POST',body,mutationKey(attempt,{dispatch:body,fid}));
          const message=result.message||'Despacho enviado ao terminal.';
          setNotice(message);reply(result.ok!==false,message);
        }catch(e){
          const message=(e as Error).message||'falha desconhecida';
          setNotice('Não consegui abrir o terminal: '+message);reply(false,message);
        }
        return;
      }
    };
    window.addEventListener('message',receive);
    return()=>window.removeEventListener('message',receive);
  },[fid,onOpen]);
  useEffect(()=>{if(!hash)return;try{const key=`mb-report-feedback:${fid}:${hash}`;const value=storedValue(pending,decision);if(value)localStorage.setItem(key,value);else localStorage.removeItem(key);}catch{setNotice('As notas ainda não enviadas não ficaram guardadas neste aparelho. Use Enviar ao projeto antes de fechar.');}},[fid,hash,pending,decision]);
  useEffect(()=>{if(!hash)return;try{localStorage.setItem(`mb-report-note:${fid}:${hash}`,note);}catch{}},[fid,hash,note]);
  useEffect(()=>{if(!hash)return;try{localStorage.setItem(`mb-report-attachments:${fid}:${hash}`,JSON.stringify(attachments));}catch{setNotice('Os prints não ficaram guardados neste aparelho. Mantenha o relatório aberto até enviar.');}},[fid,hash,attachments]);
  useEffect(()=>{if(!hash)return;let active=true;const timer=setInterval(()=>{void api<{hash:string}>(`/reports/${fid}/status`).then(value=>{if(active&&value.hash!==hash){setUpdated(true);setNotice('Uma versão nova chegou. O que você enviar daqui ainda chega ao projeto, marcado como versão anterior.');}}).catch(()=>{});},8000);return()=>{active=false;clearInterval(timer);};},[fid,hash]);
  function refresh(){
    if(busy||sending||flushing.current||decisionSending.current){setNotice('Aguarde o envio antes de abrir a versão nova.');return;}
    if(uploading||canonicalBlocked.current||uploads.current.size){setNotice('Aguarde o envio dos prints antes de abrir a versão nova.');return;}
    if(!(carry.current&&!currentHash.current))carry.current={from:currentHash.current||hash,notes:pendingRef.current,decision:decisionRef.current,note,anexos:attachments};
    canonicalBlocked.current=false;token.current=crypto.randomUUID();currentHash.current='';setHash('');setUpdated(false);setNotice('Abrindo a versão atual…');setVersion(n=>n+1);
  }
  async function save(){
    const text=note.trim();
    const selectedRoute=routeRef.current;
    if(selectedRoute&&bridgeRef.current&&commentRouteProblem(bridgeRef.current,selectedRoute)){setNotice(commentRouteProblem(bridgeRef.current,selectedRoute));return;}
    const snapshot=attachments,images=snapshot.slice(0,6);
    if(busy||uploading||canonicalBlocked.current||uploads.current.size||!hash||(!text&&!images.length&&!pendingRef.current.length&&decisionRef.current?.finalizado!==true))return;
    setBusy(true);
    try{
      await retry();
      if(text||images.length){
        const payload={hash,feedback:null,note:text,anexos:images,...(selectedRoute?{rota:selectedRoute}:{})};
        const result=await api<{versao_anterior?:boolean;ponte?:BridgeReceipt}>(`/reports/${encodeURIComponent(fid)}/feedback`,'POST',payload,mutationKey(attempt,payload));
        attempt.current=null;if(noteRef.current.trim()===text){setNote('');if(JSON.stringify(routeRef.current)===JSON.stringify(selectedRoute))setRoute(undefined);}if(attachmentsRef.current===snapshot)setAttachments(snapshot.slice(images.length));const hint=bridgeText(result?.ponte??null);setNotice('Recebido no projeto'+(result?.versao_anterior?' (versão anterior)':'')+(snapshot.length>6?' · os prints restantes continuam no rascunho':hint||', aguardando correção pela IA.'));
      }
    }catch(e){setNotice((e as Error).message);}finally{setBusy(false);}
  }
  const waitingDecision=decision?.finalizado===true;
  const waiting=pending.length+(waitingDecision?1:0);
  return <div className="report-live"><div className="report-receipt" role="status"><Check size={14}/>{notice}{waiting>0&&!sending&&!busy&&<><strong className="report-unsent">{waitingText(pending.length,waitingDecision)}</strong><button className="secondary" onClick={()=>void retry()}><RotateCw size={14}/>tentar de novo</button></>}{updated&&<button className="secondary" disabled={busy||sending||uploading} onClick={refresh}>Abrir versão nova</button>}</div>{available?<iframe ref={frame} key={version} title={title} src={`/api/reports/${encodeURIComponent(fid)}/view?ticket=${encodeURIComponent(token.current)}`} sandbox="allow-scripts allow-same-origin allow-forms" referrerPolicy="no-referrer"/>:<div className="report-loading" role="status">{loadError?<><p>{loadError}</p><button className="secondary" disabled={busy||sending||uploading} onClick={refresh}>Tentar abrir novamente</button></>:<><LoaderCircle size={20} className="spin"/><p>Preparando o relatório…</p></>}</div>}<div className="report-note">{attachments.length>6&&<p role="status">{attachments.length} prints guardados. Cada envio leva até 6; os restantes continuam aqui.</p>}{bridge.view&&<div className="report-bridge"><span><Network size={13}/>Padrão do projeto: {routeName(bridge.view,projectRoute(bridge.view))}</span><button type="button" className={`bridge-power${bridge.view.data.auto?' on':''}`} aria-pressed={bridge.view.data.auto} disabled={bridgeBusy} onClick={()=>void bridgeSave({auto:!bridge.view?.data.auto})}><Power size={11}/>{bridge.view.data.auto?'ponte automática':'ponte desligada'}</button><details className="report-route"><summary>Destino deste comentário: {route?routeName(bridge.view,route):'padrão do projeto'}</summary><RouteChoice view={bridge.view} value={route} onChange={setRoute} busy={busy||uploading} inherit/></details></div>}<MessageCircle size={16}/><AttachmentInput key={fid} pid={projectId||''} value={attachments} onChange={setAttachments} onBusyChange={setUploading} disabled={busy}><textarea aria-label={`Comentário sobre ${title}`} value={note} disabled={busy} onChange={e=>setNote(e.target.value)} placeholder="Peça uma alteração neste relatório…" rows={2}/></AttachmentInput><button className="secondary" disabled={busy||uploading||!hash||!!(route&&bridge.view&&commentRouteProblem(bridge.view,route))||(!note.trim()&&!attachments.length&&waiting===0)} onClick={()=>void save()}>{busy?<LoaderCircle size={15} className="spin"/>:<Send size={15}/>}Enviar ao projeto</button></div></div>;
}
