// Módulos reais de um projeto, usados pelo quadro do projeto e pelos painéis da página principal.
// Mesmo componente nos dois lugares: nada de cartão de exemplo ou dado fabricado.
import {useCallback,useEffect,useRef,type MouseEvent as ReactMouseEvent,type PointerEvent as ReactPointerEvent,type ReactNode} from 'react';
import {Activity,ArrowRight,ArrowUpRight,ChevronDown,Circle,Clock3,ExternalLink,File,FileImage,Folder,Image,Layers,Link,Plus,Sparkles,Workflow,type LucideIcon} from 'lucide-react';
import FeedbackReceipt from './FeedbackReceipt';
import BridgePanel from './BridgePanel';
import ExecutionCard from './Execution';
import RoutingEditor from './RoutingEditor';
import {fileUrl,safeUrl} from './api';
import type {Job,Preview,ProjectDetail} from './types';
import {deliveryStateText,deliveryCaption} from './status-labels';

/** Módulos do quadro do projeto (as sessões observadas continuam dentro de Atividade no quadro). */
export const MODULES: {id:string; title:string; icon:LucideIcon; color:string}[] = [
  {id:'now',title:'Agora',icon:Sparkles,color:'pink'}, {id:'results',title:'Resultados',icon:Layers,color:'green'},
  {id:'references',title:'Referências',icon:Image,color:'blue'}, {id:'activity',title:'Atividade',icon:Activity,color:'amber'},
  {id:'process',title:'Processo',icon:Workflow,color:'violet'},
];
/** Ícones de todos os módulos que podem abrir como painel, inclusive as sessões observadas. */
export const MODULE_ICONS:Record<string,LucideIcon>={now:Sparkles,results:Layers,references:Image,activity:Activity,sessions:Activity,process:Workflow};

export const dateText=(date?:string)=>{if(!date)return 'Sem data registrada';const d=new Date(date);return Number.isNaN(+d)?date:d.toLocaleString('pt-BR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});};
export const concise=(value:string,limit=170)=>{const cleaned=value.replace(/[#*_]/g,'').replace(/\s+/g,' ').trim();return cleaned.length>limit?cleaned.slice(0,limit).replace(/\s+\S*$/,'')+'…':cleaned;};
export function IconButton({icon:Icon,label,onClick,className='',disabled=false,children,expanded}:{icon:LucideIcon;label:string;onClick?:()=>void;className?:string;disabled?:boolean;children?:ReactNode;expanded?:boolean}){return <button className={`icon-button ${className}`} title={label} aria-label={label} aria-expanded={expanded} onClick={onClick} disabled={disabled}><Icon size={18}/>{children}</button>;}
export function Empty({icon:Icon=Layers,title,children}:{icon?:LucideIcon;title:string;children?:ReactNode}){return <div className="empty-state"><div className="empty-orbit"><Icon size={26}/></div><strong>{title}</strong>{children&&<p>{children}</p>}</div>;}

/** Área de comentário aberta por segurar ou pelo menu "Ações de …". */
export type CommentContext={pid:string;target:string;label:string;anchor:{x:number;y:number};x:number;y:number};
/** Controles, títulos (alça de mover) e alças de tamanho nunca abrem comentário ao segurar. */
const HOLD_SKIP='button:not([data-target]),a,input,textarea,select,summary,iframe,audio,video,.module-head,.home-panel-title,.react-resizable-handle,.mb-layout-handle';
/**
 * Segurar 1 segundo abre o comentário, como no quadro do projeto. Mesmo comportamento no quadro e nos
 * painéis de módulo da página principal. `bind(pid,target,label)` devolve os eventos do corpo do módulo.
 */
export function useCommentHold(onContext:(ctx:CommentContext)=>void){
  const hold=useRef<{timer:ReturnType<typeof setTimeout>;x:number;y:number}|null>(null);const suppress=useRef(false);const latest=useRef(onContext);latest.current=onContext;
  const clear=useCallback(()=>{if(hold.current){clearTimeout(hold.current.timer);hold.current=null;}},[]);
  useEffect(()=>clear,[clear]);
  return useCallback((pid:string,target:string,label:string)=>({
    onClickCapture:(e:ReactMouseEvent)=>{if(suppress.current){e.preventDefault();e.stopPropagation();suppress.current=false;}},
    onContextMenu:(e:ReactMouseEvent)=>{if(suppress.current)e.preventDefault();},
    onPointerDown:(e:ReactPointerEvent)=>{
      if(window.brainCursorTools||e.button!==0||(e.target as HTMLElement).closest(HOLD_SKIP))return;
      const rect=e.currentTarget.getBoundingClientRect();const found=(e.target as HTMLElement).closest<HTMLElement>('[data-target]');
      const ctx:CommentContext={pid,target:found?.dataset.target||target,label:found?.dataset.label||label,anchor:{x:(e.clientX-rect.left)/rect.width,y:(e.clientY-rect.top)/rect.height},x:e.clientX,y:e.clientY};
      clear();hold.current={timer:setTimeout(()=>{suppress.current=true;latest.current(ctx);hold.current=null;},1000),x:e.clientX,y:e.clientY};
    },
    onPointerUp:clear,onPointerCancel:clear,
    onPointerMove:(e:ReactPointerEvent)=>{if(hold.current&&Math.hypot(e.clientX-hold.current.x,e.clientY-hold.current.y)>8)clear();},
  }),[clear]);
}

/** Corpo de módulo fora do quadro (painel da página principal) com o mesmo "segurar para comentar". */
export function HoldArea({pid,target,label,onContext,anchor,className,children}:{pid:string;target:string;label:string;onContext:(ctx:CommentContext)=>void;anchor?:string;className?:string;children:ReactNode}){
  const bind=useCommentHold(onContext);
  return <div className={className} data-cf-ancora={anchor} {...bind(pid,target,label)}>{children}</div>;
}

function SessionList({sessions}:{sessions:ProjectDetail['sessions']}){
  return <>{sessions.map(s=><div key={s.id}><strong>{s.vendor} · {s.title}</strong><p>{s.status}</p><small>{s.evidence||'Fonte local; não confirma execução em andamento.'}</small></div>)}</>;
}

/**
 * onShowResults: destino de "Ver resultados" fora do quadro (painel de módulo na página principal).
 * routingLock: a esteira deste projeto já tem um editor em outro lugar; aqui fica só o aviso, sem segundo editor.
 */
export type ProjectModuleProps={id:string;detail:ProjectDetail;jobs:Job[];openPreview:(p:Preview)=>void;onError:(e:unknown)=>void;onSaved:(m:string)=>void;onStartJob:()=>void;onCancelJob:(id:string)=>Promise<void>;onReference:()=>void;anchorPrefix?:string;onShowResults?:()=>void;routingLock?:ReactNode};

export function ProjectModule({id,detail,jobs,openPreview,onError,onSaved,onStartJob,onCancelJob,onReference,anchorPrefix='',onShowResults,routingLock}:ProjectModuleProps):ReactNode{
  const pid=detail.project.id;
  const showResults=onShowResults||(()=>document.getElementById(`${anchorPrefix}${pid}-results`)?.scrollIntoView({behavior:'smooth',block:'nearest'}));
  if(id==='now')return <div className="now-content"><FeedbackReceipt comments={detail.comments||[]}/><BridgePanel pid={pid} comments={detail.comments||[]} onError={onError}/><div className="now-kicker"><span className="small-tag pink"><Sparkles size={12}/> No seu painel</span><span className="source-badge"><Folder size={12}/> Fonte local</span></div><h2>{detail.project.summary?concise(detail.project.summary):'Resumo ainda não registrado.'}</h2>{detail.project.summary&&detail.project.summary.length>170&&<details className="summary-detail"><summary>Ver contexto completo <ChevronDown size={13}/></summary><p>{detail.project.summary}</p></details>}<p className="next-step">{detail.project.next_step?concise(detail.project.next_step,150):'Próximo passo ainda não registrado na fonte.'}</p><div className="now-actions"><button className="primary" onClick={onStartJob}><Plus size={17}/>Novo pedido<ArrowUpRight size={16}/></button><button className="text-button" onClick={showResults}>Ver resultados <ArrowRight size={15}/></button></div><div className="now-source"><Clock3 size={14}/><span>{dateText(detail.project.updated_at)}<small>{detail.project.source||'Última atualização registrada no projeto'}</small></span></div></div>;
  if(id==='results')return detail.deliveries?.length?<div className="delivery-list">{detail.deliveries.map((d,i)=><article className="delivery" key={d.id} data-target={d.file_id?`file:${d.file_id}`:`delivery:${d.id}`} data-label={d.title}><div className={`file-tile ${d.type==='html'?'pink':'green'}`}>{d.type==='image'?<FileImage size={23}/>:<Layers size={23}/>}</div><div className="delivery-body"><div className="row-line"><span className="micro-label">{d.type?.toUpperCase()||'ENTREGA'}</span>{i===0&&<span className="new-tag">Mais recente</span>}</div><h3>{d.title}</h3>{d.summary&&deliveryCaption(d)===d.summary.trim()&&<p>{d.summary}</p>}<div className="delivery-meta"><span><Circle size={7} fill="currentColor"/>{deliveryStateText(d)}</span><time>{dateText(d.updated_at)}</time></div>{d.verification_label&&!/verifica[cç][aã]o n[aã]o registrada/i.test(d.verification_label)&&<span className="proof-label"><File size={12}/> {d.verification_label}</span>}</div><IconButton icon={ArrowUpRight} label={`Abrir ${d.title}`} disabled={!d.file_id} onClick={()=>d.file_id&&openPreview({id:d.file_id,title:d.title,type:d.type||'html',url:fileUrl(d.file_id),caption:d.session||'Entrega do projeto'})}/></article>)}</div>:<Empty title="Os resultados chegam aqui">As entregas encontradas no projeto aparecem com origem e data.</Empty>;
  if(id==='references'){const assets=[...(detail.assets||[]),...(detail.references||[])].filter((a,i,arr)=>arr.findIndex(b=>b.id===a.id)===i);
    return <><div className="module-intro"><p>O repertório perto do resultado.</p><button className="text-button" onClick={onReference}><Plus size={15}/>Adicionar link</button></div>{assets.length?<div className="asset-grid">{assets.map(a=>{const image=a.type==='image';const url=safeUrl(a.url)||fileUrl(a.id);return <button className="asset" data-target={`file:${a.id}`} data-label={a.name||a.title||'Referência'} key={a.id} onClick={()=>openPreview({id:a.id,title:a.name||a.title||'Referência',type:a.type||'link',url,caption:a.role==='reference'?'Referência do projeto':a.role||'Arquivo do projeto'})}><div className={`asset-art ${image?'':'asset-link'}`}>{image?<img src={url} alt="" loading="lazy"/>:<><Link size={28}/><span>REFERÊNCIA</span></>}</div><span>{a.name||a.title||'Referência'}</span><small><ExternalLink size={11}/>{image?'Abrir imagem':'Abrir referência'}</small></button>;})}</div>:<Empty icon={Image} title="Espaço para suas referências">Adicione um link. Os arquivos indexados também ficam disponíveis aqui.</Empty>}</>;}
  if(id==='activity'){const ownJobs=jobs.filter(j=>j.project_id===pid&&!j.external_operation);
    return <div className="activity-list">{ownJobs.map(j=><ExecutionCard key={j.id} job={j} onPreview={openPreview} onCancel={onCancelJob}/>)}{(detail.activity||[]).slice(0,12).map(a=><div className="timeline-row" key={a.id}><span className="timeline-dot"/><div><strong>{a.title}</strong>{a.detail&&<p>{a.detail}</p>}<small>{dateText(a.at)}</small></div></div>)}{detail.sessions?.length>0&&<details className="observed-sessions"><summary><Activity size={14}/>Sessões observadas <span>{detail.sessions.length}</span><ChevronDown size={14}/></summary><SessionList sessions={detail.sessions}/></details>}{!ownJobs.length&&!detail.activity?.length&&!detail.sessions?.length&&<Empty icon={Activity} title="Nenhuma atividade registrada">As atualizações reais do projeto aparecerão aqui.</Empty>}</div>;}
  if(id==='sessions')return detail.sessions?.length?<div className="observed-sessions module-sessions"><SessionList sessions={detail.sessions}/></div>:<Empty icon={Activity} title="Nenhuma sessão observada">As sessões locais registradas neste projeto aparecem aqui.</Empty>;
  if(id==='process')return routingLock||<RoutingEditor pid={pid} onError={onError} onSaved={onSaved}/>;
  return null;
}
