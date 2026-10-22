import { useEffect, useRef, useState } from 'react';
import { Activity, Archive, BookOpen, FileText, Folder, Image, Link2, LoaderCircle, MessageSquare, Package, RefreshCw, TriangleAlert } from 'lucide-react';
import { api } from './api';
import { dateText } from './project-modules';
import './locator.css';

/** B-APP F0b · localizador Buscar/Todos: consulta única por metadados em todos os projetos (PLANO_FINAL §3.1, §5.1). */
export type LocatorKind='project'|'report'|'delivery'|'file'|'reference'|'link'|'comment'|'job';
export type LocatorItem={key:string;kind:LocatorKind;project_id:string;project_name?:string;title:string;date?:string|null;date_label?:string|null;historical:boolean;available:boolean;target:{kind:LocatorKind;projectId:string;itemId:string}};
type Coverage={project:string;name?:string;observed_at?:string|null;items:number;status:'completo'|'nao_lido'|string};
type SearchResult={items:LocatorItem[];next_cursor:string|null;query_revision:number;revision_changed:boolean;observed_at:string;counts:{total:number;atuais:number;historico:number;indisponiveis:number};coverage:Coverage[];limites?:string[]};
type Scope='todos'|'atuais'|'historico';

export const KIND_LABEL:Record<LocatorKind,string>={project:'Projeto',report:'Relatório',delivery:'Entrega',file:'Arquivo',reference:'Referência',link:'Link',comment:'Comentário',job:'Pedido'};
const KIND_ICON={project:Folder,report:FileText,delivery:Package,file:Image,reference:BookOpen,link:Link2,comment:MessageSquare,job:Activity};
const PAGE=30;

export default function Locator({query,onPick}:{query:string;onPick:(item:LocatorItem)=>void}){
  const [scope,setScope]=useState<Scope>('todos');const [kind,setKind]=useState<LocatorKind|''>('');
  const [result,setResult]=useState<SearchResult|null>(null);const [items,setItems]=useState<LocatorItem[]>([]);
  const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [attempt,setAttempt]=useState(0);
  const request=useRef(0);
  const params=(cursor?:string|null)=>{const p=new URLSearchParams({q:query.trim().slice(0,200),scope,limit:String(PAGE)});if(kind)p.set('kind',kind);if(cursor)p.set('cursor',cursor);return p.toString();};
  useEffect(()=>{const id=++request.current;setLoading(true);setError('');
    const timer=setTimeout(()=>{api<SearchResult>(`/search?${params()}`).then(r=>{if(id!==request.current)return;setResult(r);setItems(r.items);}).catch(e=>{if(id===request.current)setError(e instanceof Error?e.message:'Busca indisponível.');}).finally(()=>{if(id===request.current)setLoading(false);});},220);
    return()=>clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[query,scope,kind,attempt]);
  async function more(){if(!result?.next_cursor)return;const id=++request.current;setLoading(true);setError('');
    try{const r=await api<SearchResult>(`/search?${params(result.next_cursor)}`);if(id!==request.current)return;setResult(r);setItems(prev=>[...prev,...r.items.filter(i=>!prev.some(p=>p.key===i.key))]);}
    catch(e){if(id===request.current)setError(e instanceof Error?e.message:'Busca indisponível.');}finally{if(id===request.current)setLoading(false);}}
  const unread=(result?.coverage||[]).filter(c=>c.status==='nao_lido');const covered=(result?.coverage||[]).length-unread.length;
  return <section className="locator" aria-labelledby="locator-title">
    <header className="locator-head"><strong id="locator-title">{query.trim()?'Itens encontrados':'Todos os itens'}</strong>
      <div className="locator-scope" role="group" aria-label="Escopo">{(['todos','atuais','historico'] as Scope[]).map(s=><button key={s} type="button" className={scope===s?'selected':''} aria-pressed={scope===s} onClick={()=>setScope(s)}>{s==='todos'?'Todos':s==='atuais'?'Atuais':'Histórico'}</button>)}</div>
      <select aria-label="Tipo de item" value={kind} onChange={e=>setKind(e.target.value as LocatorKind|'')}><option value="">Todos os tipos</option>{(Object.keys(KIND_LABEL) as LocatorKind[]).map(k=><option key={k} value={k}>{KIND_LABEL[k]}</option>)}</select>
    </header>
    {result&&<p className="locator-meta" role="status">{scope==='todos'?`${result.counts.total} ${result.counts.total===1?'item':'itens'} · ${result.counts.atuais} ${result.counts.atuais===1?'atual':'atuais'} · ${result.counts.historico} no histórico`:`${scope==='atuais'?result.counts.atuais:result.counts.historico} ${scope==='atuais'?(result.counts.atuais===1?'atual':'atuais'):'no histórico'} de ${result.counts.total} no acervo`}{result.counts.indisponiveis?` · ${result.counts.indisponiveis} não encontrados na última leitura`:''} · {covered} de {result.coverage.length} projetos lidos</p>}
    {unread.length>0&&<details className="locator-coverage"><summary><TriangleAlert size={13}/>{unread.length} {unread.length===1?'projeto ainda não lido':'projetos ainda não lidos'}: a busca não cobre os itens deles</summary><p>{unread.map(c=>c.name||c.project).join(' · ')}. A leitura acontece aos poucos, ao abrir o projeto ou no ciclo da central.</p>{result?.limites?.map(l=><p key={l}>{l}</p>)}</details>}
    {result?.revision_changed&&<p className="locator-note">O acervo mudou durante a consulta. <button type="button" className="text-button" onClick={()=>setAttempt(a=>a+1)}><RefreshCw size={12}/>Recomeçar</button></p>}
    {error&&<p className="locator-error" role="alert">{error} <button type="button" className="text-button" onClick={()=>setAttempt(a=>a+1)}><RefreshCw size={12}/>Tentar novamente</button></p>}
    {!error&&!loading&&result&&items.length===0&&<p className="locator-empty">Nenhum item com esses filtros{unread.length?'; projetos não lidos podem ter mais.':'.'}</p>}
    {items.length>0&&<ul className={`locator-list ${loading?'stale':''}`} aria-busy={loading}>{items.map(item=>{const Icon=KIND_ICON[item.kind]||FileText;return <li key={item.key}><button type="button" onClick={()=>onPick(item)} className={item.available?'':'unavailable'}>
      <Icon size={18} aria-hidden="true"/><span><strong>{item.title}</strong><small>{item.project_name||'Projeto'} · {KIND_LABEL[item.kind]||item.kind} · {item.date?`${item.date_label||'Data'} ${dateText(item.date)}`:'Sem data registrada'}{item.historical&&<em className="locator-tag"><Archive size={11}/>Histórico</em>}{!item.available&&<em className="locator-tag warn">Não encontrado na última leitura</em>}</small></span></button></li>;})}</ul>}
    {loading&&<p className="locator-loading" role="status"><LoaderCircle className="spin" size={14}/>Buscando…</p>}
    {!loading&&result?.next_cursor&&<button type="button" className="text-button locator-more" onClick={()=>void more()}>Carregar mais</button>}
  </section>;
}
