import {useCallback,useEffect,useMemo,useRef,useState,type CSSProperties,type DragEvent,type ReactNode} from 'react';
import GridLayout from 'react-grid-layout/legacy';
import {Activity,ArrowDown,ArrowUp,ArrowUpRight,ChevronDown,CircleAlert,Clock3,Columns2,FileImage,Grip,Layers,LayoutDashboard,LoaderCircle,Minus,Plus,RefreshCw,WifiOff,Workflow,X,type LucideIcon} from 'lucide-react';
import ExecutionCard,{isJobRunning,jobStatusText} from './Execution';
import RoutingEditor from './RoutingEditor';
import {ApiError} from './api';
import {DRAG_REPORT,libraryItems} from './ReportLibrary';
import {DRAG_PANEL,HOME_DESKTOP_COLS,HOME_NARROW_WIDTH,HOME_PANEL_LIMIT,adjustLayout,homeLayout,homeLayoutKey,orderProjects,parsePanelPayload,readPanels,recentDeliveries,toPanelInput,type PanelInput} from './home-state';
import type {HomePanel,Job,Preview,Project,ProjectDetail,Workspace} from './types';
import './home-desk.css';

const CONCURRENCY=3;const RECENT_SCOPE=6;const ROW=64;const GAP=12;const CARD_LIMIT=8;
const dateText=(date?:string)=>{if(!date)return 'Sem data registrada';const d=new Date(date);return Number.isNaN(+d)?date:d.toLocaleString('pt-BR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});};
const initial=(name:string)=>name.trim().split(/\s+/).filter(Boolean).slice(0,2).map(n=>n[0]).join('').toUpperCase();
const omit=<T,>(record:Record<string,T>,key:string)=>key in record?Object.fromEntries(Object.entries(record).filter(([k])=>k!==key)):record;
const byUpdated=(a:Job,b:Job)=>(Date.parse(b.updated_at||'')||0)-(Date.parse(a.updated_at||'')||0);
const KIND_LABEL={project:'Projeto',process:'Pedido',report:'Relatório'} as const;
function dragPanel(input:PanelInput){return (e:DragEvent)=>{e.dataTransfer.setData(DRAG_PANEL,JSON.stringify(input));e.dataTransfer.effectAllowed='copy';};}

type Props={
  projects:Project[];details:Record<string,ProjectDetail>;jobs:Job[];online:boolean;ws:Workspace;update:(fn:(w:Workspace)=>Workspace)=>void;
  loadDetail:(pid:string)=>Promise<unknown>;onError:(e:unknown)=>void;onSaved:(message:string)=>void;
  onOpen:(input:PanelInput,drop?:{x:number;y:number;cols:number})=>void;onClose:(key:string)=>void;onOpenDesk:(pid:string)=>void;
  onCancelJob:(id:string)=>Promise<void>;onPreview:(item:Preview)=>void;
  renderProject:(detail:ProjectDetail)=>ReactNode;renderPreview:(item:Preview)=>ReactNode;
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

function RoutingSection({pid,onError,onSaved}:{pid:string;onError:(e:unknown)=>void;onSaved:(m:string)=>void}){
  const [open,setOpen]=useState(false);
  return <details className="home-routing" onToggle={e=>setOpen(e.currentTarget.open)}><summary><Workflow size={15}/>Esteira configurada do projeto<small>Configuração para próximos pedidos, não a execução observada</small><ChevronDown size={14}/></summary>{open&&<RoutingEditor pid={pid} onError={onError} onSaved={onSaved}/>}</details>;
}

export default function HomeDesk(props:Props){
  const {projects,details,jobs,online,ws,update,onOpen,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderPreview}=props;
  const panels=readPanels(ws);const {errors,pending,request,retry}=useDetailQueue(props.loadDetail,onError);
  const [scope,setScope]=useState<'recent'|'all'>('all');const [allCards,setAllCards]=useState(false);
  const running=useMemo(()=>jobs.filter(j=>isJobRunning(j.status)),[jobs]);
  const runningIds=useMemo(()=>new Set(running.map(j=>j.project_id)),[running]);
  const ordered=useMemo(()=>orderProjects(projects,runningIds),[projects,runningIds]);
  const byDate=useMemo(()=>orderProjects(projects,new Set()),[projects]);
  const scopeIds=useMemo(()=>(scope==='all'?byDate:byDate.slice(0,RECENT_SCOPE)).map(p=>p.id),[scope,byDate]);
  const panelIds=useMemo(()=>[...new Set(panels.filter(p=>p.kind!=='process').map(p=>p.project_id))].filter(id=>projects.some(p=>p.id===id)),[panels,projects]);
  useEffect(()=>{request([...panelIds,...scopeIds].filter(id=>!details[id]&&!errors[id]));},[panelIds,scopeIds,details,errors,request]);
  const recent=useMemo(()=>recentDeliveries(projects,details,8),[projects,details]);
  const readCount=projects.filter(p=>details[p.id]).length;const failed=Object.keys(errors).filter(id=>projects.some(p=>p.id===id));const loading=Object.keys(pending).length;
  const openKeys=new Set(panels.map(p=>p.key));
  const lastJob=(pid:string)=>jobs.filter(j=>j.project_id===pid).sort(byUpdated)[0];
  const cards=allCards?ordered:ordered.slice(0,CARD_LIMIT);
  const processRows=running.length?[...running].sort(byUpdated).slice(0,6):[...jobs].sort(byUpdated).slice(0,3);

  return <div className="home-desk">
    <section className="home-overview" aria-label="Visão geral">
      <div className="home-overview-main">
        <section className="home-strip" aria-labelledby="home-projects-title">
          <header><h2 id="home-projects-title"><Layers size={15}/>Seus projetos</h2><span className="home-count">{projects.length}</span>{runningIds.size>0&&<span className="home-live"><LoaderCircle className="spin" size={12}/>{runningIds.size} com pedido em andamento</span>}<small className="home-strip-note">Clique ou arraste para abrir embaixo</small></header>
          {projects.length?<div className="home-cards">{cards.map(p=>{const live=running.filter(j=>j.project_id===p.id).length;const last=live?undefined:lastJob(p.id);const open=openKeys.has(`project:${p.id}:`);
            return <button type="button" key={p.id} className={`home-card ${live?'is-live':''} ${open?'is-open':''}`} draggable onDragStart={dragPanel({kind:'project',project_id:p.id})} onClick={()=>onOpen({kind:'project',project_id:p.id})} data-cf-project={p.id} data-cf-module="home-card" aria-label={`${p.name}: ${open?'já aberto embaixo, ir até ele':'abrir embaixo'}`}>
              <span className="home-card-head"><span className="project-monogram" style={{'--project-color':p.color||'#ff82c4'} as CSSProperties}>{initial(p.name)}</span><strong>{p.name}</strong>{open&&<span className="home-tag">Aberto</span>}</span>
              <span className={`home-card-state ${live?'live':''}`}>{live?<><LoaderCircle className="spin" size={12}/>{live} {live===1?'pedido em andamento':'pedidos em andamento'}</>:last?<><Clock3 size={12}/>Último pedido: {jobStatusText(last.status)}</>:<><Clock3 size={12}/>Sem pedido em andamento</>}</span>
              <span className="home-card-meta">{typeof p.delivery_count==='number'&&<span>{p.delivery_count} entregas</span>}{typeof p.report_count==='number'&&<span>{p.report_count} relatórios</span>}<span title={p.source||'Data registrada no estado do projeto'}>{p.updated_at?`Atualizado ${dateText(p.updated_at)}`:'Sem data registrada'}</span></span>
            </button>;})}</div>:<PanelNotice icon={Layers} title="Nenhum projeto no catálogo">Os projetos conectados aparecem aqui assim que a central os encontrar.</PanelNotice>}
          {ordered.length>CARD_LIMIT&&<button className="text-button home-more" aria-expanded={allCards} onClick={()=>setAllCards(!allCards)}>{allCards?'Mostrar menos':`Ver todos os ${ordered.length} projetos`}<ChevronDown size={14}/></button>}
        </section>
        <section className="home-strip" aria-labelledby="home-process-title">
          <header><h2 id="home-process-title"><Activity size={15}/>{running.length?'Pedidos em andamento':'Últimos pedidos registrados'}</h2>{running.length>0&&<span className="home-count">{running.length}</span>}{!online&&<span className="home-offline" role="status"><WifiOff size={12}/>Reconectando · último estado conhecido</span>}</header>
          {!running.length&&<p className="home-strip-empty">Nenhum pedido em andamento agora.{processRows.length?' Abaixo, os mais recentes com o status registrado pela central.':''}</p>}{running.length>processRows.length&&<p className="home-strip-empty">Mostrando os {processRows.length} atualizados por último de {running.length} em andamento.</p>}
          {processRows.length>0&&<ul className="home-process-list">{processRows.map(j=>{const p=projects.find(p=>p.id===j.project_id);const live=isJobRunning(j.status);return <li key={j.id}><button type="button" draggable={Boolean(p)} disabled={!p} onDragStart={dragPanel({kind:'process',project_id:j.project_id,ref:j.id})} onClick={()=>onOpen({kind:'process',project_id:j.project_id,ref:j.id})} data-cf-project={p?j.project_id:undefined} data-cf-module={`home-process:${j.id}`} aria-label={`Abrir pedido ${j.title} embaixo`}>
            <span className={`timeline-point ${live?'active':''}`}>{live?<LoaderCircle className="spin" size={13}/>:<Clock3 size={13}/>}</span>
            <span className="home-process-text"><strong>{j.title}</strong><small>{p?.name||'Projeto fora do catálogo'} · {jobStatusText(j.status)}{j.stage?` · ${j.stage}`:''}{j.external_operation?' · operação externa':''}</small></span><time>{dateText(j.updated_at)}</time></button></li>;})}</ul>}
        </section>
      </div>
      <section className="home-strip home-recent" aria-labelledby="home-recent-title">
        <header><h2 id="home-recent-title"><FileImage size={15}/>Entregas e relatórios recentes</h2></header>
        <p className="home-scope" role="status">Pela data de cada entrega · {readCount} de {projects.length} projetos lidos{loading>0?` · lendo ${loading}…`:''}{scope==='recent'&&readCount<projects.length&&<button className="text-button" onClick={()=>setScope('all')}>Ler todos</button>}{failed.length>0&&<button className="text-button" onClick={()=>retry(failed)}><RefreshCw size={12}/>{failed.length} sem leitura · tentar de novo</button>}</p>
        {recent.length?<ul className="home-recent-list">{recent.map(({key,project,delivery:d,at})=>{const input:PanelInput=d.file_id?{kind:'report',project_id:project.id,ref:d.file_id}:{kind:'project',project_id:project.id};return <li key={key}><button type="button" draggable onDragStart={dragPanel(input)} onClick={()=>onOpen(input)} data-cf-project={project.id} data-cf-module="home-recent" aria-label={`${d.title}, de ${project.name}: abrir embaixo`}>
          <span className={`file-tile ${d.type==='html'?'pink':'green'}`}>{d.type==='image'?<FileImage size={18}/>:<Layers size={18}/>}</span>
          <span className="home-recent-text"><span className="micro-label">{d.type==='html'?'RELATÓRIO':d.type?.toUpperCase()||'ENTREGA'}</span><strong>{d.title}</strong><small><span className="project-swatch" style={{background:project.color||'#ff82c4'}}/>{project.name} · {d.session||'arquivo do projeto'}</small><small>{d.status||'Status não registrado'} · {d.verification_label||'Verificação não registrada'}</small></span>
          <time title={at===null?'A fonte não registrou data para esta entrega':undefined}>{dateText(d.updated_at)}</time></button></li>;})}</ul>
        :loading>0?<Loading label="Lendo entregas dos projetos…"/>:<PanelNotice icon={FileImage} title="Nenhuma entrega encontrada nos projetos lidos">{readCount<projects.length?'Use “Ler todos” para incluir os demais projetos.':'As entregas aparecem aqui com origem e data.'}</PanelNotice>}
      </section>
    </section>
    <HomePanels {...{panels,projects,details,jobs,ws,update,onOpen,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderPreview,errors,retry}}/>
  </div>;
}

type PanelsProps=Pick<Props,'projects'|'details'|'jobs'|'ws'|'update'|'onOpen'|'onClose'|'onOpenDesk'|'onCancelJob'|'onPreview'|'onError'|'onSaved'|'renderProject'|'renderPreview'>&{panels:HomePanel[];errors:Record<string,string>;retry:(ids:string[])=>void};
function HomePanels({panels,projects,details,jobs,ws,update,onOpen,onClose,onOpenDesk,onCancelJob,onPreview,onError,onSaved,renderProject,renderPreview,errors,retry}:PanelsProps){
  const holder=useRef<HTMLDivElement>(null);const [width,setWidth]=useState(0);const [dropReady,setDropReady]=useState(false);
  useEffect(()=>{if(!holder.current)return;const ro=new ResizeObserver(entries=>setWidth(Math.floor(entries[0].contentRect.width)));ro.observe(holder.current);return()=>ro.disconnect();},[]);
  const narrow=width>0&&width<HOME_NARROW_WIDTH;const cols=narrow?1:HOME_DESKTOP_COLS;const key=homeLayoutKey(cols);
  const layout=useMemo(()=>homeLayout(panels,ws.layouts?.[key],cols),[panels,ws.layouts,key,cols]);
  function save(next:readonly {i:string;x:number;y:number;w:number;h:number}[]){
    // Clique sem movimento também dispara onDragStop; sem mudança real, a regra automática continua valendo.
    const same=next.length===layout.length&&next.every(a=>layout.some(b=>b.i===a.i&&b.x===a.x&&b.y===a.y&&b.w===a.w&&b.h===a.h));if(same)return;
    update(w=>({...w,layouts:{...w.layouts,[key]:next.filter(a=>panels.some(p=>p.key===a.i)).map(({i,x,y,w,h})=>({i,x,y,w,h}))}}));}
  function adjust(id:string,action:Parameters<typeof adjustLayout>[2]){save(adjustLayout(layout,id,action,cols));}
  function accepts(e:DragEvent){const types=Array.from(e.dataTransfer.types);return types.includes(DRAG_PANEL)||(types.includes(DRAG_REPORT)&&!(e.target as HTMLElement).closest?.('.project-board'));}
  function drop(e:DragEvent){
    setDropReady(false);if(!accepts(e))return;e.preventDefault();
    let input=parsePanelPayload(e.dataTransfer.getData(DRAG_PANEL));
    if(!input){try{const raw=e.dataTransfer.getData(DRAG_REPORT);const data=raw.length<2000?JSON.parse(raw) as {id?:unknown;pid?:unknown}:null;input=toPanelInput({kind:'report',project_id:data?.pid,ref:data?.id});}catch{input=null;}}
    if(!input){onSaved('Este item não pode ser aberto aqui.');return;}
    const rect=holder.current!.getBoundingClientRect();
    onOpen(input,{x:Math.floor((e.clientX-rect.left)/Math.max(1,rect.width)*cols),y:Math.max(0,Math.floor((e.clientY-rect.top)/(ROW+GAP))),cols});
  }
  function body(p:HomePanel):{content:ReactNode;ready:boolean}{
    const project=projects.find(x=>x.id===p.project_id);const remove=<button className="secondary" onClick={()=>onClose(p.key)}><X size={14}/>Retirar painel</button>;
    if(!project)return {ready:false,content:<PanelNotice title="Projeto não encontrado no catálogo atual" actions={remove}>A central não lista mais este projeto. Se a pasta voltar a ser conectada, o painel volta a funcionar.</PanelNotice>};
    if(p.kind==='process'){
      const job=jobs.find(j=>j.id===p.ref&&j.project_id===p.project_id);
      if(!job)return {ready:false,content:<PanelNotice icon={Clock3} title="Este pedido não aparece mais na lista da central" actions={<>{remove}<button className="secondary" onClick={()=>onOpen({kind:'project',project_id:p.project_id})}><Layers size={14}/>Abrir o projeto</button></>}>Isso não indica que ele foi concluído. Veja a Atividade do projeto para o histórico registrado.</PanelNotice>};
      const live=isJobRunning(job.status);
      return {ready:true,content:<><p className={`home-process-state ${live?'live':''}`}>{live?<LoaderCircle className="spin" size={13}/>:<Clock3 size={13}/>}{live?'Em andamento':'Fora de andamento'} · {jobStatusText(job.status)} · {dateText(job.updated_at)}</p><ExecutionCard job={job} onPreview={item=>onPreview({...item,project_id:item.project_id||p.project_id})} onCancel={onCancelJob}/><RoutingSection pid={p.project_id} onError={onError} onSaved={onSaved}/></>};
    }
    const detail=details[p.project_id];
    if(!detail)return {ready:false,content:errors[p.project_id]?<PanelNotice alert title="Não foi possível ler este projeto" actions={<><button className="secondary" onClick={()=>retry([p.project_id])}><RefreshCw size={14}/>Tentar de novo</button>{remove}</>}>{errors[p.project_id]}</PanelNotice>:<Loading label="Lendo o contexto do projeto…"/>};
    if(p.kind==='project')return {ready:true,content:renderProject(detail)};
    const item=libraryItems(detail).find(r=>r.id===p.ref);
    if(!item)return {ready:false,content:<PanelNotice icon={FileImage} title="Este relatório não está mais no catálogo do projeto" actions={remove}>A versão aberta antes pode ter sido movida ou substituída.</PanelNotice>};
    return {ready:false,content:<WhenVisible>{renderPreview({...item,project_id:p.project_id})}</WhenVisible>};
  }
  return <section className="home-panels" aria-labelledby="home-panels-title">
    <header className="home-zone-head"><h2 id="home-panels-title"><LayoutDashboard size={15}/>Abertos nesta página</h2><span className="home-count">{panels.length}/{HOME_PANEL_LIMIT}</span><p>Clique ou arraste um projeto, pedido ou entrega para abrir aqui. Vários ficam abertos ao mesmo tempo.</p></header>
    <div ref={holder} className={`home-grid ${panels.length?'':'is-empty'} ${dropReady?'drop-ready':''}`} onDragOver={e=>{if(accepts(e)){e.preventDefault();e.dataTransfer.dropEffect='copy';if(!dropReady)setDropReady(true);}}} onDragLeave={e=>{if(!holder.current?.contains(e.relatedTarget as Node))setDropReady(false);}} onDrop={drop}>
      {!panels.length&&<div className="home-drop-hint"><Plus size={20}/><strong>Solte aqui para abrir</strong><span>Ou clique em um projeto, pedido ou entrega acima.</span></div>}
      {width>0&&panels.length>0&&<GridLayout width={width} cols={cols} rowHeight={ROW} margin={[GAP,GAP]} containerPadding={[0,0]} layout={layout} isDraggable={!narrow} isResizable={!narrow} draggableHandle=".home-panel-title" draggableCancel="button,input,textarea,select,iframe,a" compactType="vertical" preventCollision={false} resizeHandles={['se']} onDragStop={next=>save(next)} onResizeStop={next=>save(next)}>
        {panels.map(p=>{const project=projects.find(x=>x.id===p.project_id);const job=p.kind==='process'?jobs.find(j=>j.id===p.ref&&j.project_id===p.project_id):undefined;const title=p.kind==='project'?project?.name||p.title:job?.title||p.title;const {content,ready}=body(p);const wide=(layout.find(a=>a.i===p.key)?.w||0)>=cols;
          return <div key={p.key} className={`home-panel kind-${p.kind}`} data-home-panel={p.key} role="region" aria-label={`${KIND_LABEL[p.kind]}: ${title}`} tabIndex={-1}>
            <header data-cf-ignorar><div className="home-panel-title" title={narrow?undefined:'Arraste pelo título para mover'}>{!narrow&&<Grip size={15} aria-hidden="true"/>}<span className="project-swatch" style={{background:project?.color||'#ff82c4'}}/><span><small>{KIND_LABEL[p.kind]}{p.kind!=='project'&&project?` · ${project.name}`:''}</small><strong>{title}</strong></span></div>
              <div className="home-panel-actions">
                <button className="icon-button" aria-label={`Mover ${title} para antes`} title="Mover para antes" onClick={()=>adjust(p.key,'before')}><ArrowUp size={15}/></button>
                <button className="icon-button" aria-label={`Mover ${title} para depois`} title="Mover para depois" onClick={()=>adjust(p.key,'after')}><ArrowDown size={15}/></button>
                {!narrow&&<button className="icon-button" aria-label={`${wide?'Reduzir à metade':'Usar a largura toda'}: ${title}`} title={wide?'Metade da largura':'Largura toda'} onClick={()=>adjust(p.key,'wide')}><Columns2 size={15}/></button>}
                <button className="icon-button" aria-label={`Aumentar altura de ${title}`} title="Aumentar altura" onClick={()=>adjust(p.key,'tall')}><Plus size={15}/></button>
                <button className="icon-button" aria-label={`Diminuir altura de ${title}`} title="Diminuir altura" onClick={()=>adjust(p.key,'short')}><Minus size={15}/></button>
                {project&&<button className="icon-button" aria-label={`Abrir ${project.name} como mesa`} title="Abrir como mesa" onClick={()=>onOpenDesk(p.project_id)}><ArrowUpRight size={15}/></button>}
                <button className="icon-button" aria-label={`Fechar ${title}`} title="Fechar painel" onClick={()=>onClose(p.key)}><X size={16}/></button>
              </div></header>
            <div className={`home-panel-body ${p.kind==='report'?'is-report':''}`} data-cf-project={project?p.project_id:undefined} data-cf-module={p.kind==='process'?`home-process:${p.ref}`:`home-${p.kind}`} data-ready={ready?'':undefined}>{content}</div>
          </div>;})}
      </GridLayout>}
    </div>
  </section>;
}
