import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ATTACHMENT_ACCEPT,ATTACHMENT_LIMIT,uploadAttachment,validateAttachment,type Attachment} from './attachments';
import './attachments.css';

type Pending={id:string;file:File;url:string;error:string;uploading:boolean};
type Props={pid:string;value:Attachment[];onChange:(value:Attachment[])=>void;onBusyChange?:(busy:boolean)=>void;disabled?:boolean;label?:string;children:ReactNode};
export default function AttachmentInput({pid,value,onChange,onBusyChange,disabled=false,label='Escolher print',children}:Props){
  const picker=useRef<HTMLInputElement>(null);const latest=useRef(value);latest.current=value;
  const queue=useRef<Pending[]>([]);const generation=useRef(0);
  const handlers=useRef({onChange,onBusyChange});handlers.current={onChange,onBusyChange};
  const [pending,setPending]=useState<Pending[]>([]);const [error,setError]=useState('');
  function update(list:Pending[]){queue.current=list;setPending(list);handlers.current.onBusyChange?.(list.length>0);}
  useEffect(()=>{generation.current++;return()=>{generation.current++;for(const p of queue.current)URL.revokeObjectURL(p.url);queue.current=[];};},[pid]);
  async function send(entry:Pending){
    const epoch=generation.current;update(queue.current.map(p=>p.id===entry.id?{...p,uploading:true,error:''}:p));
    try{
      const attachment=await uploadAttachment(pid,entry.file);
      if(epoch!==generation.current||!queue.current.some(p=>p.id===entry.id))return;
      const next=latest.current.some(a=>a.id===attachment.id)?latest.current:[...latest.current,attachment];
      latest.current=next;handlers.current.onChange(next);
      URL.revokeObjectURL(entry.url);update(queue.current.filter(p=>p.id!==entry.id));
    }catch(e){if(epoch===generation.current)update(queue.current.map(p=>p.id===entry.id?{...p,uploading:false,error:(e as Error).message||'O print não foi enviado. Tente novamente.'}:p));}
  }
  function add(files:File[]){
    if(disabled||!files.length)return;setError('');
    if(!pid){setError('Abra um projeto para anexar o print.');return;}
    try{
      if(latest.current.length+queue.current.length+files.length>ATTACHMENT_LIMIT)throw new Error('Use até 6 prints por envio. Remova um print antes de escolher mais.');
      files.forEach(validateAttachment);
    }catch(e){setError((e as Error).message);return;}
    const entries=files.map(file=>({id:crypto.randomUUID(),file,url:URL.createObjectURL(file),error:'',uploading:true}));
    update([...queue.current,...entries]);for(const p of entries)void send(p);
  }
  function remove(id:string){const p=queue.current.find(p=>p.id===id);if(p)URL.revokeObjectURL(p.url);update(queue.current.filter(p=>p.id!==id));}
  return <div className="attachment-input" onPaste={event=>{
    const items=Array.from(event.clipboardData.items||[]);const files=items.filter(i=>i.kind==='file').map(i=>i.getAsFile()).filter((f):f is File=>!!f);
    if(files.length){if(!event.clipboardData.getData('text/plain'))event.preventDefault();add(files);}
  }}>{children}<div className="attachment-actions"><input ref={picker} type="file" accept={ATTACHMENT_ACCEPT} multiple hidden disabled={disabled||!pid} onChange={e=>{add(Array.from(e.target.files||[]));e.target.value='';}}/><button type="button" className="text-button" disabled={disabled||!pid} onClick={()=>picker.current?.click()}>📎 {label}</button><small>Ctrl+V · até 6 prints · 8 MiB cada</small></div>
  {(value.length>0||pending.length>0)&&<div className="attachment-previews">{value.map(a=><figure key={a.id}><img src={a.url} alt={`Print: ${a.name}`} onError={e=>{e.currentTarget.alt=`Prévia indisponível: ${a.name}`;}}/><figcaption>{a.name}</figcaption><button type="button" disabled={disabled} aria-label={`Remover print ${a.name}`} onClick={()=>{const next=latest.current.filter(v=>v.id!==a.id);latest.current=next;onChange(next);}}>×</button></figure>)}{pending.map(p=><figure key={p.id}><img src={p.url} alt={`Print: ${p.file.name}`}/><figcaption role="status">{p.uploading?'Enviando…':p.error}</figcaption>{!p.uploading&&<button type="button" className="attachment-retry" disabled={disabled} onClick={()=>void send(p)}>Tentar novamente</button>}<button type="button" disabled={disabled} aria-label={`Remover print ${p.file.name}`} onClick={()=>remove(p.id)}>×</button></figure>)}</div>}
  {error&&<p role="alert" className="error-message">{error}</p>}</div>;
}
