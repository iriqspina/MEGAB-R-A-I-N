import {useEffect,useRef,useState} from 'react';
import {Check,MessageCircle,Save,LoaderCircle} from 'lucide-react';
import {api,ApiError,mutationKey,type MutationAttempt} from './api';

export default function ReportFrame({fid,title,projectId,onOpen}:{fid:string;title:string;projectId?:string;onOpen?:(url:string)=>void}){
  const frame=useRef<HTMLIFrameElement>(null);
  const token=useRef(crypto.randomUUID());
  const attempt=useRef<MutationAttempt|null>(null);
  const draftQueue=useRef(Promise.resolve());
  const currentHash=useRef('');
  const [version,setVersion]=useState(0);
  const [updated,setUpdated]=useState(false);
  const [feedback,setFeedback]=useState<unknown>(null);
  const [hash,setHash]=useState('');
  const [notice,setNotice]=useState('Carregando o relatório…');
  const [busy,setBusy]=useState(false);
  const [note,setNote]=useState('');
  const [available,setAvailable]=useState(false);
  const [loadError,setLoadError]=useState('');
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
      if(data.kind==='stale'){setNotice('O relatório mudou durante a abertura. Reabra a versão atual.');setUpdated(true);return;}
      setHash(data.hash);
      if(data.kind==='ready'){
        if(currentHash.current!==data.hash){currentHash.current=data.hash;try{setNote(localStorage.getItem(`mb-report-note:${fid}:${data.hash}`)||'');const pending=localStorage.getItem(`mb-report-feedback:${fid}:${data.hash}`);setFeedback(pending?JSON.parse(pending):null);}catch{}}
        setNotice('Relatório aberto no MegaBrain. Suas respostas ficam ligadas a esta versão.');
      }
      if(data.kind==='feedback'){setFeedback((previous:unknown)=>{
        const old=previous as {kind?:string;notas?:{id?:string}[]}|null;const incoming=data.payload as {kind?:string;notas?:{id?:string}[]};
        if(incoming.kind==='notes'){const notes=[...(old?.notas||[]),...(incoming.notas||[])];return {...old,...incoming,kind:old?.kind==='decisions'?'decisions':'notes',notas:notes.filter((v,i)=>!v.id||!notes.slice(i+1).some(n=>n.id===v.id))};}
        return incoming;
      });setNotice('Respostas preparadas. Confira e use Salvar no projeto.');}
      if(data.kind==='draft'){
        const payload={hash:data.hash,storage:data.payload?.storage};
        draftQueue.current=draftQueue.current.then(async()=>{try{await api(`/reports/${fid}/draft`,'POST',payload);}catch(e){setNotice(e instanceof ApiError?e.message:'Rascunho ainda não salvo; mantenha este relatório aberto.');}});
      }
      if(data.kind==='open-local'){
        try{const result=await api<{item:{url:string}}>(`/reports/${fid}/resolve`,'POST',{path:data.payload?.path,hash:data.hash});if(onOpen)onOpen(result.item.url);else window.dispatchEvent(new CustomEvent('mb-open-item',{detail:result}));}
        catch(e){setNotice((e as Error).message);}
      }
      if(data.kind==='open-external')setNotice('Esta fonte está fora dos relatórios locais. O endereço continua registrado; nenhuma janela externa foi aberta.');
    };
    window.addEventListener('message',receive);
    return()=>window.removeEventListener('message',receive);
  },[fid,onOpen]);
  useEffect(()=>{if(!hash)return;try{const key=`mb-report-feedback:${fid}:${hash}`;if(feedback)localStorage.setItem(key,JSON.stringify(feedback));else localStorage.removeItem(key);}catch{setNotice('O pacote de respostas ainda não foi preservado neste dispositivo. Salve no projeto antes de fechar.');}},[fid,hash,feedback]);
  useEffect(()=>{if(!hash)return;try{localStorage.setItem(`mb-report-note:${fid}:${hash}`,note);}catch{}},[fid,hash,note]);
  useEffect(()=>{if(!hash)return;let active=true;const timer=setInterval(()=>{void api<{hash:string}>(`/reports/${fid}/status`).then(value=>{if(active&&value.hash!==hash){setUpdated(true);setNotice('Uma versão nova chegou. Seu rascunho anterior permanece ligado à versão que você abriu.');}}).catch(()=>{});},8000);return()=>{active=false;clearInterval(timer);};},[fid,hash]);
  function refresh(){token.current=crypto.randomUUID();currentHash.current='';setHash('');setFeedback(null);setNote('');setUpdated(false);setNotice('Abrindo a versão atual…');setVersion(n=>n+1);}
  async function save(){
    if(busy||!hash||(!feedback&&!note.trim()))return;
    setBusy(true);
    try{
      const payload={hash,feedback,note:note.trim()};
      await api(`/reports/${fid}/feedback`,'POST',payload,mutationKey(attempt,payload));
      attempt.current=null;setFeedback(null);setNote('');setNotice('Recebido no projeto, aguardando correção pela IA.');
    }catch(e){setNotice((e as Error).message);}finally{setBusy(false);}
  }
  return <div className="report-live"><div className="report-receipt" role="status"><Check size={14}/>{notice}{updated&&<button className="secondary" onClick={refresh}>Abrir versão nova</button>}</div>{available?<iframe ref={frame} key={version} title={title} src={`/api/reports/${encodeURIComponent(fid)}/view?ticket=${encodeURIComponent(token.current)}`} sandbox="allow-scripts allow-same-origin allow-forms" referrerPolicy="no-referrer"/>:<div className="report-loading" role="status">{loadError?<><p>{loadError}</p><button className="secondary" onClick={refresh}>Tentar abrir novamente</button></>:<><LoaderCircle size={20} className="spin"/><p>Preparando o relatório…</p></>}</div>}<div className="report-note"><MessageCircle size={16}/><textarea aria-label={`Comentário sobre ${title}`} value={note} onChange={e=>setNote(e.target.value)} placeholder="Peça uma alteração neste relatório…" rows={2}/><button className="secondary" disabled={busy||!hash||updated||(!feedback&&!note.trim())} onClick={()=>void save()}>{busy?<LoaderCircle size={15} className="spin"/>:<Save size={15}/>}Salvar no projeto</button></div></div>;
}
