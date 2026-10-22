import {useCallback,useEffect,useMemo,useRef,useState,type CSSProperties,type DragEvent,type MutableRefObject,type KeyboardEvent,type ReactNode} from 'react';
import GridLayout from 'react-grid-layout/legacy';
import {ArrowUpRight,Check,ChevronDown,CircleAlert,Clock3,FileImage,Grip,Layers,LayoutDashboard,LoaderCircle,MoreHorizontal,Plus,RefreshCw,WifiOff,Workflow,X,type LucideIcon} from 'lucide-react';
import ExecutionCard,{isJobRunning,jobStatusText} from './Execution';
import RoutingEditor from './RoutingEditor';
import {ApiError} from './api';
import {DRAG_REPORT,libraryItems} from './ReportLibrary';
import AppearanceControl from './AppearanceControl';
import {appearanceFor,dockPanels,matchPanelSize} from './appearance-state';
import HomeCatalog,{dragPanel} from './HomeCatalog';
import {deliveryOrigin,deliveryStateText} from './status-labels';
import {DRAG_CANCEL,RESIZE_ALL,RESIZE_NARROW,resizeHandle,useGridGesture} from './grid-gesture';
import {DRAG_PANEL,HOME_DESKTOP_COLS,HOME_NARROW_WIDTH,HOME_PANEL_LIMIT,adjustLayout,homeLayout,homeLayoutKey,mergeLayout,moduleTitle,openOwner,catalogState,orderProjects,panelKey,parsePanelPayload,readPanels,recentDeliveries,reportOwnerKey,splitRendered,toPanelInput,stripTitle,type PanelInput,type RecentRow} from './home-state';
import type {HomePanel,Job,LayoutItem,Preview,Project,ProjectDetail,Workspace} from './types';
import './home-desk.css';
import {FixedHomeBodies,type HomeBody} from './WorkspaceEditors';

const CONCURRENCY=3;const ROW=64;const GAP=12;const CARD_LIMIT=8;
const dateText=(date?:string)=>{if(!date)return 'Sem data registrada';const d=new Date(date);return Number.isNaN(+d)?date:d.toLocaleString('pt-BR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});};
const initial=(name:string)=>name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(n=>n[0]).join('').toUpperCase();
const omit=<T,>(record:Record<string,T>,key:string)=>key in record?Object.fromEntries(Object.entries(record).filter(([k])=>k!==key)):record;
const byUpdated=(a:Job,b:Job)=>(Date.parse(b.updated_at||'')||0)-(Date.parse(a.updated_at||'')||0);
const KIND_LABEL={project:'Projeto',process:'Pedido',report:'Relatório',module:'Módulo',global:'Geral',strip:'Seção'} as const;
const openLabel=(name:string,open:boolean,stored=false)=>`${name}: ${open?'aberto no painel, clique para fechar':stored?'guardado, clique para mostrar':'abrir no painel'}`;
/** Geometria efetiva de um painel, guardada antes de fechar para a reabertura voltar ao mesmo lugar. */
export type PanelKeep={layoutKey:string;item:LayoutItem};
type Geometry=MutableRefObject<{key:string;layout:LayoutItem[]}|null>;

type Props={
  active:boolean;projects:Project[];details:Record<string,ProjectDetail>;jobs:Job[];online:boolean;ws:Workspace;update:(fn:(w:Workspace)=>Workspace)=>void;
  /** Relatórios abertos em Respostas (pid:fid): contam como abertos e não montam um segundo editor aqui. */
  responseKeys:Set<string>;
  /** Relatórios fixados (pid:fid) com editor montado no quadro de um projeto: contam como abertos. */
  pinnedKeys:Set<string>;
  /** Aviso quando a esteira do projeto é editada em outro painel (host = chave deste painel); undefined = este edita. */
  routingLock:(pid:string,host:string)=>ReactNode;
  /** Menu "Ações de …" (comentar) dos painéis de módulo, o mesmo do quadro do projeto. */
  onModuleActions:(panel:HomePanel,title:string)=>void;
  loadDetail:(pid:string)=>Promise<unknown>;onError:(e:unknown)=>void;onSaved:(message:string)=>void;
  onOpen:(input:PanelInput,drop?:{x:number;y:number;cols:number})=>void;onToggle:(input:PanelInput,keep?:PanelKeep)=>void;onClose:(key:string,keep?:PanelKeep)=>void;onOpenDesk:(pid:string)=>void;
  onCancelJob:(id:string)=>Promise<void>;onPreview:(item:Preview)=>void;
  renderProject:(detail:ProjectDetail)=>ReactNode;renderModule:(detail:ProjectDetail,id:string)=>ReactNode;renderGlobal:(id:string)=>ReactNode;renderPreview:(item:Preview)=>ReactNode;
};

/** Leitura de /projects/:id com no máximo três consultas simultâneas; a falha de um projeto fica só nele. */
function useDetailQueue(loadDetail:Props['loadDetail'],onError:Props['onError']){
  const [errors,setErrors]=useState<Record<string,string>>({});const [pending,setPending]=useState<Record<string,true>>({});
  const queue=useRef<string[]>([]);const inflight=useRef(new Set<string>());const alive=useRef(true);const latest=useRef({loadDetail,onError});latest.current={loadDetail,onError};
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;queue.current=[];};},[]);
  const pump=useCallback(()=>{
    while(inflight.current.size<CONCURRENCY&&queue.current.length){
      const id=queue.current.shift()!;inflight.current.add(id);
      latest.current.loadDetail(id)
        .then(()=>{if(alive.current)setErrors(prev=>omit(prev,id));})
        .catch(e=>{if(e instanceof ApiError&&e.status===401){latest.current.onError(e);return;}if(alive.current)setErrors(prev=>({...prev,[id]:(e as Error)?.message||'Não foi possível ler este projeto.'}));})
        .finally(()=>{inflight.current.delete(id);if(alive.current){setPending(prev=>omit(prev,id));pump();}});
    }
  },[]);
  const request=useCallback((ids:string[])=>{const added:Record<string,true>={};for(const id of ids){if(inflight.current.has(id)||queue.current.includes(id))continue;queue.current.push(id);added[id]=true;}if(Object.keys(added).length){setPending(prev=>({...prev,...added}));pump();}},[pump]);
  const retry=useCallback((ids:string[])=>setErrors(prev=>ids.reduce((acc,id)=>omit(acc,id),prev)),[]);
  return {errors,pending,request,retry};
}

/** Adia a primeira montagem até o painel chegar perto da tela; depois disso nunca desmonta (rascunhos preservados). */
function WhenVisible({children}:{children:ReactNode}){
  const ref=useRef<HTMLDivElement>(null);const [seen,setSeen]=useState(()=>typeof IntersectionObserver==='undefined');
  useEffect(()=>{if(seen||!ref.current)return;const io=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){setSeen(true);io.disconnect();}},{rootMargin:'240px'});io.observe(ref.current);return()=>io.disconnect();},[seen]);
  return <div ref={ref} className="home-deferred" data-ready={seen?'':undefined}>{seen?children:<div className="home-skeleton" aria-hidden="true"/>}</div>;
}

function PanelNotice({icon:Icon=CircleAlert,title,children,actions,alert=false}:{icon?:LucideIcon;title:string;children?:ReactNode;actions?:ReactNode;alert?:boolean}){
  return <div className="home-notice" role={alert?'alert':undefined}><Icon size={20}/><div><strong>{title}</strong>{children&&<p>{children}</p>}{actions&&<div className="home-notice-actions">{actions}</div>}</div></div>;
}
function Loading({label}:{label:string}){return <div className="home-loading" role="status"><LoaderCircle className="spin" size={16}/>{label}</div>;}

function RoutingSection({pid,onError,onSaved,lock}:{pid:string;onError:(e:unknown)=>void;onSaved:(m:string)=>void;lock?:ReactNode}){
  const [open,setOpen]=useState(false);
  return <details className="home-routing" onToggle={e=>setOpen(e.currentTarget.open)}><summary><Workflow size={15}/>Esteira configurada do projeto<small>Configuração para próximos pedidos, não a execução observada</small><ChevronDown size={14}/></summary>{open&&(lock||<RoutingEditor pid={pid} onError={onError} onSaved={onSaved}/>)}</details>;
}

/** Dados e ações que os corpos das seções (painéis strip) usam; as fontes são as mesmas da página. */
type StripTools={projects:Project[];ordered:Project[];jobs:Job[];running:Job[];online:boolean;recent:RecentRow[];readCount:number;loading:number;failed:string[];retry:(ids:string[])=>void;isOpen:(input:PanelInput)=>boolean;isStored:(input:PanelInput)=>boolean;toggle:(input:PanelInput)=>void};

/** Seção "Seus projetos": os cards continuam abrindo/fechando painéis e arrastáveis para posicionar. */
function StripProjects({tools}:{tools:StripTools}){
  const [all,setAll]=useState(false);
  const {ordered,running,jobs,isOpen,isStored,toggle}=tools;
  const cards=all?ordered:ordered.slice(0,CARD_LIMIT);
  const lastJob=(pid:string)=>jobs.filter(j=>j.project_id===pid).sort(byUpdated)[0];
  return <div className="home-strip-body">
    <p className="home-strip-tools">{running.length>0&&<span className="home-live"><LoaderCircle className="spin" size={12}/>{running.length} {running.length===1?'pedido em andamento':'pedidos em andamento'}</span>}<span className="home-strip-note">Clique para abrir ou fechar; arraste para posicionar</span></p>
    {ordered.length?<div className="home-cards">{cards.map(p=>{const live=running.filter(j=>j.project_id===p.id).length;const last=live?undefined:lastJob(p.id);const input:PanelInput={kind:'project',project_id:p.id};const open=isOpen(input);
      return <button type="button" key={p.id} style={{'--project-accent':p.color} as CSSProperties} className={`home-card ${live?'is-live':''} ${open?'is-open':''}`} aria-pressed={open} draggable onDragStart={dragPanel(input)} onClick={()=>toggle(input)} data-cf-project={p.id} data-cf-module="home-card" aria-label={openLabel(p.name,open,isStored(input))}>
        <span className="home-card-head"><span className="project-monogram" style={{'--project-color':p.color||'#ff82c4'} as CSSProperties}>{initial(p.name)}</span><strong>{p.name}</strong>{(open||isStored(input))&&<span className="home-tag">{open?'Aberto':'Guardado'}</span>}</span>
        <span className={`home-card-state ${live?'live':''}`}>{live?<><LoaderCircle className="spin" size={12}/>{live} {live===1?'pedido em andamento':'pedidos em andamento'}</>:last?<><Clock3 size={12}/>Último pedido: {jobStatusText(last.status)}</>:<><Clock3 size={12}/>Sem pedido em andamento</>}</span>
        <span className="home-card-meta">{typeof p.delivery_count==='number'&&<span>{p.delivery_count} entregas</span>}{typeof p.report_count==='number'&&<span>{p.report_count} relatórios</span>}<span title={p.source||'Data registrada no estado do projeto'}>{p.updated_at?`Atualizado ${dateText(p.updated_at)}`:'Sem data registrada'}</span></span>
      </button>;})}</div>:<PanelNotice icon={Layers} title="Nenhum projeto no catálogo">Os projetos conectados aparecem aqui assim que a central os encontrar.</PanelNotice>}
    {ordered.length>CARD_LIMIT&&<button className="text-button home-more" aria-expanded={all} onClick={()=>setAll(!all)}>{all?'Mostrar menos':`Ver todos os ${ordered.length} projetos`}<ChevronDown size={14}/></button>}
  </div>;
}

/** Seção "Pedidos e últimos registros": em andamento primeiro; sem nada em andamento, os mais recentes. */
function StripProcesses({tools}:{tools:StripTools}){
  const {projects,jobs,running,online,isOpen,isStored,toggle}=tools;
  const rows=running.length?[...running].sort(byUpdated).slice(0,6):[...jobs].sort(byUpdated).slice(0,3);
  return <div className="home-strip-body" id="home-process-title">
    <p className="home-strip-tools">{!online&&<span className="home-offline" role="status"><WifiOff size={12}/>Reconectando · último estado conhecido</span>}{running.length>0&&<span className="home-count">{running.length}</span>}</p>
    {!running.length&&<p className="home-strip-empty">Nenhum pedido em andamento agora.{rows.length?' Abaixo, os mais recentes com o status registrado pela central.':''}</p>}
    {running.length>rows.length&&<p className="home-strip-empty">Mostrando os {rows.length} atualizados por último de {running.length} em andamento.</p>}
    {rows.length>0&&<ul className="home-process-list">{rows.map(j=>{const p=projects.find(p=>p.id===j.project_id);const live=isJobRunning(j.status);const input:PanelInput={kind:'process',project_id:j.project_id,ref:j.id};const open=isOpen(input);return <li key={j.id}><button type="button" className={open?'is-open':undefined} aria-pressed={open} draggable={Boolean(p)} disabled={!p&&!open} onDragStart={dragPanel(input)} onClick={()=>toggle(input)} data-cf-project={p?j.project_id:undefined} data-cf-module={`home-process:${j.id}`} aria-label={openLabel(`Pedido ${j.title}`,open,isStored(input))}>
      <span className={`timeline-point ${live?'active':''}`}>{live?<LoaderCircle className="spin" size={13}/>:<Clock3 size={13}/>}</span>
      <span className="home-process-text"><strong>{j.title}</strong><small>{p?.name||'Projeto fora do catálogo'} · {jobStatusText(j.status)}{j.stage?` · ${j.stage}`:''}{j.external_operation?' · operação externa':''}</small></span>{(open||isStored(input))&&<span className="home-tag">{open?'Aberto':'Guardado'}</span>}<time>{dateText(j.updated_at)}</time></button></li>;})}</ul>}
  </div>;
}

/** Seção "Entregas e relatórios recentes": pela data de cada entrega, só de projetos já lidos. */
function StripRecent({tools}:{tools:StripTools}){
  const {recent,projects,loading,readCount,failed,retry,isOpen,isStored,toggle}=tools;
  return <div className="home-strip-body">
    <p className="home-scope" role="status">Pela data de cada entrega · {readCount} de {projects.length} projetos lidos{loading>0?` · lendo ${loading}…`:''}{failed.length>0&&<button className="text-button" onClick={()=>retry(failed)}><RefreshCw size={12}/>{failed.length} sem leitura · tentar de novo</button>}</p>
    {recent.length?<ul className="home-recent-list">{recent.map(({key,project,delivery:d,at})=>{const input:PanelInput=d.file_id?{kind:'report',project_id:project.id,ref:d.file_id}:{kind:'project',project_id:project.id};const open=isOpen(input);return <li key={key}><button type="button" className={open?'is-open':undefined} aria-pressed={open} draggable onDragStart={dragPanel(input)} onClick={()=>toggle(input)} data-cf-project={project.id} data-cf-module="home-recent" aria-label={openLabel(`${d.title}, de ${project.name}`,open,isStored(input))}>
      <span className={`file-tile ${d.type==='html'?'pink':'green'}`}>{d.type==='image'?<FileImage size={18}/>:<Layers size={18}/>}</span>
      <span className="home-recent-text"><span className="micro-label">{d.type==='html'?'RELATÓRIO':d.type?.toUpperCase()||'ENTREGA'}</span><strong>{d.title}</strong><small><span className="project-swatch" style={{background:project.color||'#ff82c4'}}/>{project.name} · {deliveryOrigin(d.session)||'arquivo do projeto'}</small><small className={d.verified?'is-verified':undefined} title={d.verified?d.verification_label:undefined}>{d.verified&&<Check size={11} aria-hidden="true"/>}{deliveryStateText(d)}</small></span>
      {(open||isStored(input))&&<span className="home-tag">{open?'Aberto':'Guardado'}</span>}<time title={at===null?'A fonte não registrou data para esta entrega':undefined}>{dateText(d.updated_at)}</time></button></li>;})}</ul>
    :loading>0?<Loading label="Lendo entregas dos projetos…"/>:<PanelNotice icon={FileImage} title="Nenhuma entrega encontrada nos projetos lidos">As entregas aparecem aqui com origem e data.</PanelNotice>}
  </div>;
}

export default function HomeDesk(props:Props){
  const {active,projects,details,jobs,online,ws,update,responseKeys,pinnedKeys,routingLock,onModuleActions,onOpen,onToggle,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderModule,renderGlobal,renderPreview}=props;
  const panels=readPanels(ws);const {errors,pending,request,retry}=useDetailQueue(props.loadDetail,onError);
  const geometry=useRef<{key:string;layout:LayoutItem[]}|null>(null);
  const running=useMemo(()=>jobs.filter(j=>isJobRunning(j.status)),[jobs]);
  const runningIds=useMemo(()=>new Set(running.map(j=>j.project_id)),[running]);
  const ordered=useMemo(()=>orderProjects(projects,runningIds),[projects,runningIds]);
  const byDate=useMemo(()=>orderProjects(projects,new Set()),[projects]);
  // Globais e pedidos não pedem /projects/:id; o identificador fixo '*' nunca chega à fila.
  const panelIds=useMemo(()=>[...new Set(panels.filter(p=>p.kind!=='process'&&p.kind!=='global'&&p.kind!=='strip').map(p=>p.project_id))].filter(id=>projects.some(p=>p.id===id)),[panels,projects]);
  useEffect(()=>{if(active)request([...panelIds,...byDate.map(p=>p.id)].filter(id=>!details[id]&&!errors[id]));},[active,panelIds,byDate,details,errors,request]);
  const recent=useMemo(()=>recentDeliveries(projects,details,8),[projects,details]);
  const readCount=projects.filter(p=>details[p.id]).length;const failed=Object.keys(errors).filter(id=>projects.some(p=>p.id===id));const loading=Object.keys(pending).length;
  // Aberto = home, Respostas ou fixado com editor no quadro de um projeto (mesma união usada pela alternância no App).
  const isOpen=(input:PanelInput)=>active&&catalogState(ws,responseKeys,pinnedKeys,input)==='visible';
  const isStored=(input:PanelInput)=>catalogState(ws,responseKeys,pinnedKeys,input)==='stored';
  // Fechar pela alternância também guarda a posição efetiva na tela.
  function keepFor(key:string):PanelKeep|undefined{const g=geometry.current;const a=g?.layout.find(item=>item.i===key);return g&&a?{layoutKey:g.key,item:{i:a.i,x:a.x,y:a.y,w:a.w,h:a.h}}:undefined;}
  const toggle=(input:PanelInput)=>onToggle(input,keepFor(panelKey(input.kind,input.project_id,input.ref)));
  const strip:StripTools={projects,ordered,jobs,running,online,recent,readCount,loading,failed,retry,isOpen,isStored,toggle};

  return <div className="home-desk">
    <HomeCatalog ws={ws} projects={ordered} details={details} pending={pending} errors={errors} active={active} request={request} retry={retry} isOpen={isOpen} isStored={isStored} onToggle={toggle}/>
    <HomePanels {...{panels,projects,details,jobs,ws,update,responseKeys,routingLock,onModuleActions,geometry,strip,onOpen,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderModule,renderGlobal,renderPreview,errors,retry}}/>
  </div>;
}

type PanelsProps=Pick<Props,'projects'|'details'|'jobs'|'ws'|'update'|'responseKeys'|'routingLock'|'onModuleActions'|'onOpen'|'onClose'|'onOpenDesk'|'onCancelJob'|'onPreview'|'onError'|'onSaved'|'renderProject'|'renderModule'|'renderGlobal'|'renderPreview'>&{panels:HomePanel[];geometry:Geometry;strip:StripTools;errors:Record<string,string>;retry:(ids:string[])=>void};
function HomePanels({panels,projects,details,jobs,ws,update,responseKeys,routingLock,onModuleActions,geometry,strip,onOpen,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderModule,renderGlobal,renderPreview,errors,retry}:PanelsProps){
  const holder=useRef<HTMLDivElement>(null);const [width,setWidth]=useState(0);const [dropReady,setDropReady]=useState(false);
  const gesture=useGridGesture();
  type Dock={target:string;side:'left'|'right';y:number;h:number};
  const [dock,setDock]=useState<Dock|null>(null);const dockRef=useRef<Dock|null>(null);
  const markDock=(next:Dock|null)=>{dockRef.current=next;setDock(previous=>JSON.stringify(previous)===JSON.stringify(next)?previous:next);};
  // Largura 0 = página oculta (visão de projeto); a grade continua montada para não perder rascunhos.
  useEffect(()=>{if(!holder.current)return;const ro=new ResizeObserver(entries=>{const next=Math.floor(entries[0].contentRect.width);if(next>0)setWidth(next);});ro.observe(holder.current);return()=>ro.disconnect();},[]);
  const narrow=width>0&&width<HOME_NARROW_WIDTH;const cols=narrow?1:HOME_DESKTOP_COLS;const key=homeLayoutKey(cols);
  const responseSig=[...responseKeys].sort().join('\n');
  const {shown,waiting,elsewhere}=useMemo(()=>splitRendered(panels,new Set(responseSig?responseSig.split('\n'):[])),[panels,responseSig]);
  const visited=useRef(new Set<string>());for(const panel of shown)visited.current.add(panel.key);
  // O teto limita a tela. Corpos já visitados ficam ocultos enquanto sua chave continua salva.
  // O RGL recebe só os exibidos: nenhum filho oculto participa de geometria/compactação.
  const retained=panels.filter(p=>visited.current.has(p.key)&&!elsewhere.some(other=>other.key===p.key));
  const layout=useMemo(()=>homeLayout(shown,ws.layouts?.[key],cols),[shown,ws.layouts,key,cols]);
  useEffect(()=>{geometry.current={key,layout};});
  const keepOf=(id:string):PanelKeep|undefined=>{const a=layout.find(item=>item.i===id);return a?{layoutKey:key,item:{i:a.i,x:a.x,y:a.y,w:a.w,h:a.h}}:undefined;};
  const close=(id:string)=>onClose(id,keepOf(id));
  function save(next:readonly {i:string;x:number;y:number;w:number;h:number}[]){
    // Clique sem movimento também dispara onDragStop; sem mudança real, a regra automática continua valendo.
    const same=next.length===layout.length&&next.every(a=>layout.some(b=>b.i===a.i&&b.x===a.x&&b.y===a.y&&b.w===a.w&&b.h===a.h));if(same)return;
    // Só as chaves exibidas mudam; fechados e os acima do teto mantêm a geometria guardada.
    const visible=next.filter(a=>shown.some(p=>p.key===a.i)).map(({i,x,y,w,h})=>({i,x,y,w,h}));
    update(w=>({...w,layouts:{...w.layouts,[key]:mergeLayout(w.layouts?.[key],visible,cols)}}));}
  function adjust(id:string,action:Parameters<typeof adjustLayout>[2]){
    update(w=>{const current=homeLayout(shown,w.layouts?.[key],cols);return {...w,layouts:{...w.layouts,[key]:mergeLayout(w.layouts?.[key],adjustLayout(current,id,action,cols),cols)}};});
  }
  function syncFormat(id:string){
    update(w=>{const current=homeLayout(shown,w.layouts?.[key],cols);return {...w,layouts:{...w.layouts,[key]:mergeLayout(w.layouts?.[key],matchPanelSize(current,id,cols),cols)}};});
    onSaved(`Formato aplicado aos ${shown.length} painéis visíveis desta largura. Fechados e outras larguras continuam salvos.`);
  }
  function accepts(e:DragEvent){const types=Array.from(e.dataTransfer.types);return types.includes(DRAG_PANEL)||(types.includes(DRAG_REPORT)&&!(e.target as HTMLElement).closest?.('.project-board'));}
  function previewDock(clientX:number,clientY:number,moving?:string){
    if(narrow||!holder.current){markDock(null);return;}
    const bounds=holder.current.getBoundingClientRect();const x=(clientX-bounds.left)/Math.max(1,bounds.width)*cols,y=(clientY-bounds.top)/(ROW+GAP);
    const target=layout.find(a=>a.i!==moving&&x>=a.x&&x<=a.x+a.w&&y>=a.y&&y<=a.y+a.h);
    if(!target){markDock(null);return;}
    const fraction=(x-target.x)/target.w;
    // Centro continua arrasto livre. As duas bordas anunciam o encaixe antes de soltar.
    if(fraction>.3&&fraction<.7){markDock(null);return;}
    markDock({target:target.i,side:fraction<.5?'left':'right',y:target.y,h:target.h});
  }
  function applyDock(source:string,placement:Dock){
    update(w=>{const current=homeLayout(splitRendered(readPanels(w),responseKeys).shown,w.layouts?.[key],cols);return {...w,layouts:{...w.layouts,[key]:mergeLayout(w.layouts?.[key],dockPanels(current,source,placement.target,placement.side,cols),cols)}};});
    onSaved('Painéis lado a lado. Você pode ajustar a divisão pelas bordas.');
  }
  function drop(e:DragEvent){
    const placement=dockRef.current;markDock(null);setDropReady(false);if(!accepts(e))return;e.preventDefault();
    let input=parsePanelPayload(e.dataTransfer.getData(DRAG_PANEL));
    if(!input){try{const raw=e.dataTransfer.getData(DRAG_REPORT);const data=raw.length<2000?JSON.parse(raw) as {id?:unknown;pid?:unknown}:null;input=toPanelInput({kind:'report',project_id:data?.pid,ref:data?.id});}catch{input=null;}}
    if(!input){onSaved('Este item não pode ser aberto aqui.');return;}
    const rect=holder.current!.getBoundingClientRect();
    onOpen(input,{x:Math.floor((e.clientX-rect.left)/Math.max(1,rect.width)*cols),y:Math.max(0,Math.floor((e.clientY-rect.top)/(ROW+GAP))),cols});
    if(placement)applyDock(panelKey(input.kind,input.project_id,input.ref),placement);
  }
  // Teclado no título focável: setas movem, Shift+setas redimensionam. Eventos de controles internos nunca chegam aqui.
  function titleKeys(e:KeyboardEvent<HTMLElement>,id:string){
    let action:Parameters<typeof adjustLayout>[2]|undefined;
    if(e.shiftKey&&e.key==='ArrowUp')action='tall';
    else if(e.shiftKey&&e.key==='ArrowDown')action='short';
    else if(e.shiftKey&&e.key==='ArrowRight')action='wider';
    else if(e.shiftKey&&e.key==='ArrowLeft')action='narrow';
    else if(e.key==='ArrowUp')action='before';
    else if(e.key==='ArrowDown')action='after';
    if(!action)return;
    e.preventDefault();e.stopPropagation();adjust(id,action);
  }
  function body(p:HomePanel):{content:ReactNode;ready:boolean}{
    const remove=<button className="secondary" onClick={()=>close(p.key)}><X size={14}/>Retirar painel</button>;
    if(p.kind==='strip')return {ready:true,content:p.ref==='projects'?<StripProjects tools={strip}/>:p.ref==='processes'?<StripProcesses tools={strip}/>:<StripRecent tools={strip}/>};
    if(p.kind==='global')return {ready:true,content:renderGlobal(p.ref||'')};
    const project=projects.find(x=>x.id===p.project_id);
    if(!project)return {ready:false,content:<PanelNotice title="Projeto não encontrado no catálogo atual" actions={remove}>A central não lista mais este projeto. Se a pasta voltar a ser conectada, o painel volta a funcionar com a mesma organização.</PanelNotice>};
    if(p.kind==='process'){
      const job=jobs.find(j=>j.id===p.ref&&j.project_id===p.project_id);
      if(!job)return {ready:false,content:<PanelNotice icon={Clock3} title="Este pedido não aparece mais na lista da central" actions={<>{remove}<button className="secondary" onClick={()=>onOpen({kind:'project',project_id:p.project_id})}><Layers size={14}/>Abrir o projeto</button></>}>Isso não indica que ele foi concluído. Veja a Atividade do projeto para o histórico registrado.</PanelNotice>};
      const live=isJobRunning(job.status);
      return {ready:true,content:<><p className={`home-process-state ${live?'live':''}`}>{live?<LoaderCircle className="spin" size={13}/>:<Clock3 size={13}/>}{live?'Em andamento':'Fora de andamento'} · {jobStatusText(job.status)} · {dateText(job.updated_at)}</p><ExecutionCard job={job} onPreview={item=>onPreview({...item,project_id:item.project_id||p.project_id})} onCancel={onCancelJob}/><RoutingSection pid={p.project_id} onError={onError} onSaved={onSaved} lock={routingLock(p.project_id,p.key)}/></>};
    }
    // Relatório aberto antes: usa a cópia validada guardada no painel; a troca de versão fica com o próprio relatório.
    if(p.kind==='report'&&p.preview)return {ready:false,content:<WhenVisible>{renderPreview({...p.preview,project_id:p.project_id})}</WhenVisible>};
    const detail=details[p.project_id];
    if(!detail)return {ready:false,content:errors[p.project_id]?<PanelNotice alert title="Não foi possível ler este projeto" actions={<><button className="secondary" onClick={()=>retry([p.project_id])}><RefreshCw size={14}/>Tentar de novo</button>{remove}</>}>{errors[p.project_id]}</PanelNotice>:<Loading label="Lendo o contexto do projeto…"/>};
    if(p.kind==='project')return {ready:true,content:renderProject(detail)};
    if(p.kind==='module')return {ready:true,content:renderModule(detail,p.ref||'')};
    const item=libraryItems(detail).find(r=>r.id===p.ref);
    if(!item)return {ready:false,content:<PanelNotice icon={FileImage} title="Este relatório não está mais no catálogo do projeto" actions={remove}>A versão aberta antes pode ter sido movida ou substituída.</PanelNotice>};
    return {ready:false,content:<WhenVisible>{renderPreview({...item,project_id:p.project_id})}</WhenVisible>};
  }
  const titleOf=(p:HomePanel)=>{const project=projects.find(x=>x.id===p.project_id);const job=p.kind==='process'?jobs.find(j=>j.id===p.ref&&j.project_id===p.project_id):undefined;return p.kind==='strip'?stripTitle(p.ref):p.kind==='project'?project?.name||p.title:p.kind==='module'?moduleTitle(p.ref):job?.title||p.title;};
  const bodies:HomeBody[]=retained.map(p=>{const result=body(p);return {key:p.key,content:result.content,ready:result.ready,report:p.kind==='report',kind:p.kind,project:p.kind==='global'||p.kind==='strip'?undefined:p.project_id,module:p.kind==='process'?`home-process:${p.ref}`:p.kind==='module'?`home-module:${p.ref}`:`home-${p.kind}`};});
  return <section className="home-panels" aria-labelledby="home-panels-title">
    <header className="home-zone-head"><h2 id="home-panels-title"><LayoutDashboard size={15}/>Meu espaço</h2><span className="home-count">{shown.length}{waiting.length?` + ${waiting.length} guardados`:''}</span><p>Clique em um item do catálogo acima para abrir e de novo para fechar. Arraste pelo título para mover; puxe as bordas ou os cantos para mudar o tamanho; com o título em foco, as setas movem e Shift+setas redimensionam. Aproxime das bordas de outro painel para ver o encaixe lado a lado. A organização fica salva.</p></header>
    {waiting.length>0&&<div className="home-waiting" role="status"><CircleAlert size={16}/><div><strong>{waiting.length} {waiting.length===1?'painel salvo não exibido':'painéis salvos não exibidos'}</strong><p>A página mostra até {HOME_PANEL_LIMIT} painéis por vez, além das seções. Mostrar traz o item para a tela e guarda outro; nada é apagado.</p><ul>{waiting.map(p=><li key={p.key}><span>{KIND_LABEL[p.kind]} · {titleOf(p)}</span><button className="text-button" onClick={()=>onOpen(p)} aria-label={`Mostrar ${titleOf(p)}, que está guardado`}><ArrowUpRight size={12}/>Mostrar</button><button className="text-button" onClick={()=>onClose(p.key)} aria-label={`Fechar ${titleOf(p)}, que está guardado`}><X size={12}/>Fechar</button></li>)}</ul></div></div>}
    {elsewhere.length>0&&<p className="home-zone-note" role="status">{elsewhere.length===1?'1 relatório deste painel está aberto em Respostas':`${elsewhere.length} relatórios deste painel estão abertos em Respostas`}, sem um segundo editor aqui.</p>}
    <div ref={holder} className={`home-grid ${shown.length?'':'is-empty'} ${dropReady?'drop-ready':''}`} onDragOver={e=>{if(accepts(e)){e.preventDefault();e.dataTransfer.dropEffect='copy';if(!dropReady)setDropReady(true);previewDock(e.clientX,e.clientY);}}} onDragLeave={e=>{if(!holder.current?.contains(e.relatedTarget as Node)){setDropReady(false);markDock(null);}}} onDrop={drop}>
      {!shown.length&&<div className="home-drop-hint"><Plus size={20}/><strong>Solte aqui para abrir</strong><span>Ou clique em um projeto, pedido, entrega ou módulo no catálogo acima.</span></div>}
      {width>0&&shown.length>0&&<GridLayout width={width} cols={cols} rowHeight={ROW} margin={[GAP,GAP]} containerPadding={[0,0]} layout={layout} isDraggable={!narrow} isResizable resizeHandles={narrow?[...RESIZE_NARROW]:[...RESIZE_ALL]} resizeHandle={resizeHandle} draggableHandle=".home-panel-title" draggableCancel={DRAG_CANCEL} compactType="vertical" preventCollision={false} onDragStart={gesture.begin} onDrag={(_next,_old,item,_placeholder,event)=>{const pointer=event as MouseEvent;previewDock(pointer.clientX,pointer.clientY,item?.i);}} onResizeStart={gesture.begin} onDragStop={(next,_old,item)=>{gesture.end();const placement=dockRef.current;markDock(null);if(placement&&item)save(dockPanels([...next],item.i,placement.target,placement.side,cols));else save(next);}} onResizeStop={next=>{gesture.end();save(next);}}>
        {shown.map(p=>{const project=p.kind==='global'||p.kind==='strip'?undefined:projects.find(x=>x.id===p.project_id);const sourceTitle=titleOf(p);const look=appearanceFor(ws,p.key,sourceTitle,project?.color);const title=p.kind==='project'?sourceTitle:look.label;const ready=bodies.find(b=>b.key===p.key)?.ready;
          return <div key={p.key} className={`home-panel kind-${p.kind}`} style={{'--panel-accent':look.color} as CSSProperties} data-home-panel={p.key} role="region" aria-label={`${KIND_LABEL[p.kind]}: ${title}`} tabIndex={-1}>
            <header><div className="home-panel-title mb-layout-handle" data-cf-alca tabIndex={0} title={narrow?undefined:'Arraste pelo título para mover; puxe as bordas ou os cantos para mudar o tamanho. Com o título em foco: setas movem, Shift+setas redimensionam.'} aria-keyshortcuts="ArrowUp ArrowDown Shift+ArrowUp Shift+ArrowDown Shift+ArrowLeft Shift+ArrowRight" onKeyDown={e=>titleKeys(e,p.key)}>{!narrow&&<Grip size={15} aria-hidden="true"/>}<span className="project-swatch" style={{background:look.color}}/><span><small>{KIND_LABEL[p.kind]}{p.kind!=='project'&&p.kind!=='strip'&&project?` · ${project.name}`:''}</small><strong>{title}</strong></span></div>
              <div className="home-panel-actions"><AppearanceControl scopeKey={p.key} title={p.kind==='project'?(details[p.project_id]?.project.name||p.title):sourceTitle} color={project?.color} ws={ws} update={update} applyFormat={()=>syncFormat(p.key)} formatCount={Math.max(0,shown.length-1)}/>
                {p.kind==='module'&&project&&<button className="icon-button" aria-label={`Ações de ${title}`} title="Comentar este módulo" onClick={()=>onModuleActions(p,title)}><MoreHorizontal size={15}/></button>}
                {project&&<button className="icon-button" aria-label={`Abrir o projeto ${project.name}`} title="Abrir o projeto" onClick={()=>onOpenDesk(p.project_id)}><ArrowUpRight size={15}/></button>}
                <button className="icon-button" aria-label={`Fechar ${title}`} title="Fechar painel" onClick={()=>close(p.key)}><X size={16}/></button>
              </div></header>
            <div className={`home-panel-body ${p.kind==='report'?'is-report':''}`} data-home-body-slot={p.key} data-ready={ready?'':undefined}/>
          </div>;})}
      </GridLayout>}
      {dock&&<div className="home-drop-preview" aria-live="polite" style={{left:dock.side==='left'?0:'50%',top:dock.y*(ROW+GAP),width:'calc(50% - 6px)',height:dock.h*(ROW+GAP)-GAP}}>Solte para encaixar à {dock.side==='left'?'esquerda':'direita'}</div>}
      <FixedHomeBodies bodies={bodies} visibleKeys={new Set(shown.map(p=>p.key))}/>
    </div>
  </section>;
}

