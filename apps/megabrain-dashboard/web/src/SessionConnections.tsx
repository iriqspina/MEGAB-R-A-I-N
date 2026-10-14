import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, CheckCircle2, ChevronDown, Clock3, RefreshCw, X } from 'lucide-react';
import { api } from './api';
import './session-connections.css';

type Connection = { id:string; project_id:string|null; project_name:string; application:string; updated_at:string; started_at:string; state:string; label:string; presented_at:string|null; bridge_version:string; identity_source:string };
type Snapshot = { version:string; observed_at:string; sessions:Connection[]; registered_count:number; presented_count:number; rejected_count:number; scope:string; truncated?:boolean; limit?:number };
const stamp = (value:string) => new Date(value).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit'});

export default function SessionConnections({onProject}:{onProject:(id:string)=>void}) {
  const [data,setData]=useState<Snapshot|null>(null), [error,setError]=useState(''), [busy,setBusy]=useState(false), [open,setOpen]=useState(false);
  const running=useRef(false), alive=useRef(true);
  const refresh=useCallback(async()=>{
    if(running.current)return; running.current=true;setBusy(true);
    try { const next=await api<Snapshot>('/session-connections'); if(alive.current){setData(next);setError('');} }
    catch(e){if(alive.current)setError((e as Error).message);}
    finally {running.current=false;if(alive.current)setBusy(false);}
  },[]);
  useEffect(()=>{alive.current=true;void refresh();const timer=setInterval(()=>void refresh(),5000);return()=>{alive.current=false;clearInterval(timer);};},[refresh]);
  return <section className={`session-connections ${error?'connection-warning':''}`} aria-label="Conexão das sessões MegaBrain">
    <div className="session-connection-bar">
      <button className="session-connection-summary" onClick={()=>setOpen(!open)} aria-expanded={open}><Activity size={17}/><span><strong>Sessões → aplicativo</strong><small>{error?'Consulta indisponível; última leitura preservada':data?`${data.registered_count} registradas · ${data.presented_count} aberturas confirmadas`:'Consultando a central…'}</small></span><ChevronDown size={16}/></button>
      <span className="session-observed"><Clock3 size={14}/>{data?`Consultado ${stamp(data.observed_at)}`:'Sem leitura'}<small>Conector {data?.version||'—'}</small></span>
      <button className="secondary" onClick={()=>void refresh()} disabled={busy} aria-label="Atualizar conexões das sessões"><RefreshCw size={15} className={busy?'spin':''}/>Atualizar</button>
    </div>
    {open&&<div className="session-connection-detail"><div className="session-detail-heading"><p>Nova sessão → registro → pedido de abertura → confirmação do aplicativo</p><button className="icon-button" aria-label="Fechar detalhes das conexões" onClick={()=>setOpen(false)}><X size={16}/></button></div>
      <p className="session-scope">{data?.scope||'Aguardando leitura.'}</p>{error&&<p role="alert">{error}</p>}
      {data?.sessions.length===0&&<p>Nenhuma sessão registrou a abertura MegaBrain nesta central.</p>}
      {data?.sessions.map(row=><article key={row.id} className="session-connection-row"><div className="session-row-title">{row.state==='presented'?<CheckCircle2 size={17}/>:<Clock3 size={17}/>}<strong>{row.application} · {row.project_name}</strong>{row.project_id&&<button className="text-button" onClick={()=>{onProject(row.project_id!);setOpen(false);}}>Ver projeto</button>}</div><p>{row.label}</p>{row.identity_source==='invocation_uuid'&&<p>Registro avulso: o cliente não forneceu identificação da sessão.</p>}<small>Registro: {stamp(row.updated_at)} · Abertura: {row.presented_at?stamp(row.presented_at):'não confirmada'} · Conector {row.bridge_version}</small></article>)}
      {data?.truncated&&<p>Exibindo os {data.limit} registros mais recentes; anteriores permanecem na fonte.</p>}
      {!!data?.rejected_count&&<p>{data.rejected_count} registros inválidos ignorados.</p>}
    </div>}
  </section>;
}
