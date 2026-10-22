// Catálogo "Adicionar ao painel": tudo que pode abrir como painel, com alternância de um clique.
// 1º clique abre, 2º fecha (aria-pressed); arrastar posiciona. Só itens reais do catálogo da central.
import {useEffect,useState,type DragEvent} from 'react';
import {Activity,Check,ChevronDown,FileCode2,FileImage,FileText,Gauge,LayoutGrid,Layers,Plug,Plus,RefreshCw,type LucideIcon} from 'lucide-react';
import {appearanceFor} from './appearance-state';
import {MODULE_ICONS} from './project-modules';
import {DRAG_PANEL,GLOBAL_MODULES,GLOBAL_PID,PROJECT_MODULES,STRIP_MODULES,panelKey,type PanelInput} from './home-state';
import type {Project,ProjectDetail,Workspace} from './types';

const REPORT_STEP=12;
/** Opção padrão do seletor: todos os projetos juntos; escolher um projeto filtra (pedido 261020). */
export const ALL_PROJECTS='';
/** Só relatórios completos entram aqui: HTML e PDF entregues. Imagens, áudio e texto solto ficam na Biblioteca do projeto. */
const REPORT_TYPES:Record<string,{icon:LucideIcon;label:string}>={html:{icon:FileCode2,label:'HTML'},pdf:{icon:FileText,label:'PDF'}};
type ReportItem={id:string;pid:string;title:string;type:string;caption:string;historical:boolean;at:string};
export function catalogReports(detail:ProjectDetail,projectName?:string):ReportItem[]{
  const seen=new Set<string>();const rows:ReportItem[]=[];
  for(const d of detail.deliveries){
    const type=(d.type||'html').toLowerCase();
    if(!d.file_id||!REPORT_TYPES[type]||seen.has(d.file_id))continue;seen.add(d.file_id);
    const historical=Boolean((d as typeof d&{historical?:boolean}).historical);
    rows.push({id:d.file_id,pid:detail.project.id,title:d.title,type,historical,at:d.updated_at||'',caption:[projectName,historical?'Histórico':'',d.updated_at?new Date(d.updated_at).toLocaleDateString('pt-BR'):''].filter(Boolean).join(' · ')});
  }
  return rows;
}
export function dragPanel(input:PanelInput){return (e:DragEvent)=>{e.dataTransfer.setData(DRAG_PANEL,JSON.stringify(input));e.dataTransfer.effectAllowed='copy';};}

/** Botão de alternância: o estado aberto aparece por etiqueta e contorno, não só pela cor. */
export function PanelToggle({input,title:sourceTitle,hint,icon:Icon,open,stored=false,onToggle,ws}:{input:PanelInput;title:string;hint?:string;icon:LucideIcon;open:boolean;stored?:boolean;onToggle:(input:PanelInput)=>void;ws?:Workspace}){
  const title=ws?appearanceFor(ws,panelKey(input.kind,input.project_id,input.ref),sourceTitle).label:sourceTitle;
  if(input.kind==='global'&&input.ref==='quotas')return <button type="button" className="home-toggle" aria-label="Cotas de IA: abrir aplicativo de pontuação" onClick={()=>onToggle(input)} title="Abrir somente o pop-up Cotas de IA. As configurações têm acesso separado."><Icon size={15} aria-hidden="true"/><span className="home-toggle-text"><strong>Cotas de IA</strong><small>Abrir aplicativo de pontuação</small></span></button>;
  return <button type="button" className={`home-toggle ${open?'is-open':''}`} aria-pressed={open} aria-label={`${title}: ${open?'aberto, clique para fechar':stored?'guardado, clique para mostrar':'abrir no painel'}`} draggable onDragStart={dragPanel(input)} onClick={()=>onToggle(input)} title={open?'Aberto no painel · clique para fechar':stored?'Guardado · clique para mostrar no painel':'Clique para abrir no painel · ou arraste até a posição'}>
    <Icon size={15} aria-hidden="true"/><span className="home-toggle-text"><strong>{title}</strong>{hint&&<small>{hint}</small>}</span>
    {open||stored?<span className="home-tag">{open&&<Check size={11} aria-hidden="true"/>}{open?'Aberto':'Guardado'}</span>:<Plus size={14} aria-hidden="true"/>}
  </button>;
}

/** Relatório como ícone do tipo + nome completo embaixo (o nome não some cortado no cartão). */
function ReportTile({item,open,stored,onToggle,ws}:{item:ReportItem;open:boolean;stored:boolean;onToggle:(input:PanelInput)=>void;ws:Workspace}){
  const input:PanelInput={kind:'report',project_id:item.pid,ref:item.id};
  const title=appearanceFor(ws,panelKey('report',item.pid,item.id),item.title).label;const kind=REPORT_TYPES[item.type];const Icon=kind.icon;
  return <button type="button" className={`home-report-tile ${open?'is-open':''}`} aria-pressed={open} aria-label={`${title} (${kind.label}): ${open?'aberto, clique para fechar':stored?'guardado, clique para mostrar':'abrir no painel'}`} draggable onDragStart={dragPanel(input)} onClick={()=>onToggle(input)} title={`${title} · ${kind.label}${item.caption?' · '+item.caption:''}`}>
    <span className={`home-report-icon is-${item.type}`} aria-hidden="true"><Icon size={22}/><em>{kind.label}</em></span>
    <strong className="home-report-name">{title}</strong>
    {item.caption&&<small>{item.caption}</small>}
    {(open||stored)&&<span className="home-tag">{open&&<Check size={11} aria-hidden="true"/>}{open?'Aberto':'Guardado'}</span>}
  </button>;
}

type Props={ws:Workspace;projects:Project[];details:Record<string,ProjectDetail>;pending:Record<string,true>;errors:Record<string,string>;active:boolean;
  request:(ids:string[])=>void;retry:(ids:string[])=>void;isOpen:(input:PanelInput)=>boolean;isStored:(input:PanelInput)=>boolean;onToggle:(input:PanelInput)=>void};

export default function HomeCatalog({ws,projects,details,pending,errors,active,request,retry,isOpen,isStored,onToggle}:Props){
  const [chosen,setChosen]=useState(ALL_PROJECTS);const [reportCount,setReportCount]=useState(REPORT_STEP);
  const all=!projects.some(p=>p.id===chosen);const pid=all?'':chosen;const project=projects.find(p=>p.id===pid);
  // Com "Todos os projetos" lê só quem tem entrega no catálogo; a fila limitada da página continua mandando no ritmo.
  const scope=all?projects.filter(p=>(p.report_count??p.delivery_count??1)>0):project?[project]:[];
  const missing=scope.filter(p=>!details[p.id]&&!errors[p.id]).map(p=>p.id);const missingKey=missing.join('|');
  useEffect(()=>{if(active&&missingKey)request(missingKey.split('|'));},[active,missingKey,request]);
  useEffect(()=>setReportCount(REPORT_STEP),[pid]);
  const reports=scope.flatMap(p=>details[p.id]?catalogReports(details[p.id],all?p.name:undefined):[]).sort((a,b)=>Number(a.historical)-Number(b.historical)||b.at.localeCompare(a.at));// recente primeiro (261010)
  const loading=missing.length>0;const failed=scope.filter(p=>errors[p.id]);
  return <section className="home-strip home-catalog" aria-labelledby="home-catalog-title">
    <header><h2 id="home-catalog-title"><LayoutGrid size={15}/>Adicionar ao painel</h2><small className="home-strip-note">Clique uma vez para abrir e outra para fechar. Também dá para arrastar até a posição.</small></header>
    <div className="home-catalog-groups">
      <div className="home-catalog-group" role="group" aria-labelledby="home-catalog-strips"><h3 id="home-catalog-strips">Seções do painel</h3>
        <div className="home-toggle-list">{STRIP_MODULES.map(m=><PanelToggle ws={ws} key={m.id} input={{kind:'strip',project_id:GLOBAL_PID,ref:m.id}} title={m.title} hint={m.hint} icon={m.id==='projects'?Layers:m.id==='processes'?Activity:FileImage} open={isOpen({kind:'strip',project_id:GLOBAL_PID,ref:m.id})} stored={isStored({kind:'strip',project_id:GLOBAL_PID,ref:m.id})} onToggle={onToggle}/>)}</div>
      </div>
      <div className="home-catalog-group" role="group" aria-labelledby="home-catalog-global"><h3 id="home-catalog-global">Gerais</h3>
        <div className="home-toggle-list">{GLOBAL_MODULES.map(m=><PanelToggle ws={ws} key={m.id} input={{kind:'global',project_id:GLOBAL_PID,ref:m.id}} title={m.title} hint={m.hint} icon={m.id==='quotas'?Gauge:Plug} open={isOpen({kind:'global',project_id:GLOBAL_PID,ref:m.id})} stored={isStored({kind:'global',project_id:GLOBAL_PID,ref:m.id})} onToggle={onToggle}/>)}</div>
      </div>
      <div className="home-catalog-group" role="group" aria-labelledby="home-catalog-project">
        <h3 id="home-catalog-project">Do projeto</h3>
        {projects.length?<>
          <label className="home-catalog-select"><span>Projeto</span><select value={pid} onChange={e=>setChosen(e.target.value)}><option value={ALL_PROJECTS}>Todos os projetos</option>{projects.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          {project?<div className="home-toggle-list">{PROJECT_MODULES.map(m=><PanelToggle ws={ws} key={m.id} input={{kind:'module',project_id:pid,ref:m.id}} title={m.title} hint={m.hint} icon={MODULE_ICONS[m.id]||LayoutGrid} open={isOpen({kind:'module',project_id:pid,ref:m.id})} stored={isStored({kind:'module',project_id:pid,ref:m.id})} onToggle={onToggle}/>)}</div>
            :<p className="home-strip-empty">Os módulos (Agora, Resultados, Referências…) são de cada projeto: escolha um no seletor para abri-los.</p>}
          <h4><FileImage size={13} aria-hidden="true"/>Relatórios{reports.length||!loading?<span className="home-count">{reports.length}</span>:null}</h4>
          {reports.length>0&&<>
            <div className="home-report-grid">{reports.slice(0,reportCount).map(r=>{const input:PanelInput={kind:'report',project_id:r.pid,ref:r.id};return <ReportTile key={r.pid+':'+r.id} ws={ws} item={r} open={isOpen(input)} stored={isStored(input)} onToggle={onToggle}/>;})}</div>
            {reports.length>reportCount&&<button type="button" className="text-button home-more" onClick={()=>setReportCount(reports.length)}>Mostrar todos os {reports.length}<ChevronDown size={14}/></button>}
          </>}
          {loading?<p className="home-strip-empty" role="status">{scope.some(p=>pending[p.id])?'Lendo o catálogo…':'O catálogo será lido ao abrir a página.'}</p>
            :!reports.length&&!failed.length?<p className="home-strip-empty">{project?`${project.name} ainda não tem relatórios no catálogo.`:'Nenhum relatório no catálogo.'}</p>:null}
          {failed.length>0&&<p className="home-strip-empty" role="alert">Não foi possível ler {failed.map(p=>p.name).join(', ')}: {errors[failed[0].id]} <button type="button" className="text-button" onClick={()=>retry(failed.map(p=>p.id))}><RefreshCw size={12}/>Tentar de novo</button></p>}
        </>:<p className="home-strip-empty">Nenhum projeto no catálogo.</p>}
      </div>
    </div>
  </section>;
}
