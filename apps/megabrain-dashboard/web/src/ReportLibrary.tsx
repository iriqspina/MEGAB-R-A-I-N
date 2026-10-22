import {useMemo,useState} from 'react';
import {Search,Grip,Plus,Layers,Image,Archive,FileText} from 'lucide-react';
import {fileUrl} from './api';
import type {ProjectDetail,Preview} from './types';
import {deliveryCaption} from './status-labels';

export const DRAG_REPORT='application/x-megabrain-report';
export type DeskView=Preview&{project_id:string};
export function libraryItems(detail:ProjectDetail):Preview[]{
  const rows=[...detail.deliveries.filter(d=>d.file_id).map(d=>({id:d.file_id!,title:d.title,type:d.type||'html',url:fileUrl(d.file_id!),caption:deliveryCaption(d)})),...detail.assets.map(a=>({id:a.id,title:a.name||a.title||'Arquivo',type:a.type||'link',url:a.url||fileUrl(a.id),caption:a.role==='reference'?'Referência do projeto':a.origin||'Arquivo original'})),...(detail.references||[]).map(a=>({id:a.id,title:a.title||a.name||'Referência',type:a.type||'link',url:a.url||fileUrl(a.id),caption:'Referência adicionada'}))];
  return rows.filter((item,index)=>rows.findIndex(other=>other.id===item.id)===index);
}
export default function ReportLibrary({detail,onPin,onOpen}:{detail:ProjectDetail;onPin:(item:Preview)=>void;onOpen:(item:Preview)=>void}){
  const [query,setQuery]=useState('');const [kind,setKind]=useState('results');
  const items=useMemo(()=>libraryItems(detail),[detail]);
  const results=new Set(detail.deliveries.filter(d=>d.file_id).map(d=>d.file_id));
  const historic=new Set(detail.deliveries.filter(d=>(d as typeof d&{historical?:boolean}).historical).map(d=>d.file_id));
  const visible=items.filter(item=>(kind==='history'?historic.has(item.id):kind==='references'?!results.has(item.id):results.has(item.id)&&!historic.has(item.id))&&`${item.title} ${item.caption}`.toLocaleLowerCase().includes(query.toLocaleLowerCase()));
  return <aside className="report-library" aria-label={`Biblioteca de ${detail.project.name}`}><header><Layers size={18}/><strong>Biblioteca</strong><span>{items.length}</span></header><p>Arraste para o painel ou use +.</p><div className="library-tabs"><button className={kind==='results'?'selected':''} onClick={()=>setKind('results')}><Layers size={13}/>Resultados</button><button className={kind==='references'?'selected':''} onClick={()=>setKind('references')}><Image size={13}/>Referências</button><button className={kind==='history'?'selected':''} onClick={()=>setKind('history')}><Archive size={13}/>Histórico</button></div><label className="library-search"><Search size={14}/><input aria-label="Buscar relatório ou referência" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Buscar aqui…"/></label><div className="library-items">{visible.map(item=><article key={item.id} draggable onDragStart={e=>{e.dataTransfer.setData(DRAG_REPORT,JSON.stringify({id:item.id,pid:detail.project.id}));e.dataTransfer.effectAllowed='copy';}}><Grip size={14}/><button onClick={()=>onOpen(item)} title={item.caption}><FileText size={15}/><span>{item.title}<small>{item.caption}</small></span></button><button aria-label={`Colocar ${item.title} no painel`} title="Colocar no painel" onClick={()=>onPin(item)}><Plus size={16}/></button></article>)}{!visible.length&&<p className="library-empty">Nenhum item neste filtro.</p>}</div></aside>;
}
