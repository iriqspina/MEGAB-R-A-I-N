// Estado puro da página principal: validação do que vem do /workspace ou de um arraste,
// geometria da grade de painéis e lista de entregas recentes. Sem React e sem rede.
import type {Delivery, HomePanel, HomePanelKind, Job, LayoutItem, Preview, Project, ProjectDetail, Workspace} from './types';

export const DRAG_PANEL='application/x-megabrain-panel';
export const HOME_PANEL_LIMIT=6;
export const HOME_DESKTOP_COLS=12;
export const HOME_NARROW_WIDTH=700;
export const homeLayoutKey=(cols:number)=>cols===1?'home:mobile':'home:desktop';
export type PanelInput={kind:HomePanelKind;project_id:string;ref?:string};
export type HomeCatalog={projects:Project[];jobs:Job[];reports:(pid:string)=>Preview[]|null};

const KINDS:HomePanelKind[]=['project','process','report'];
const HEIGHT:Record<HomePanelKind,number>={project:9,process:7,report:9};
const isRecord=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value);
const cleanId=(value:unknown,max:number)=>typeof value==='string'&&value.length>0&&value.length<=max&&!/[\u0000-\u001f]/.test(value)?value:null;
const clamp=(value:number,min:number,max:number)=>Math.min(max,Math.max(min,value));
const finite=(value:unknown)=>typeof value==='number'&&Number.isFinite(value);

export const panelKey=(kind:HomePanelKind,pid:string,ref?:string)=>`${kind}:${pid}:${kind==='project'?'':ref||''}`;
export const defaultPanelHeight=(kind:HomePanelKind)=>HEIGHT[kind];

/** Lê uma entrada desconhecida; devolve null para qualquer forma inválida. */
export function toPanelInput(value:unknown):PanelInput|null{
  if(!isRecord(value)||!KINDS.includes(value.kind as HomePanelKind))return null;
  const kind=value.kind as HomePanelKind;const pid=cleanId(value.project_id,200);if(!pid)return null;
  if(kind==='project')return {kind,project_id:pid};
  const ref=cleanId(value.ref,300);return ref?{kind,project_id:pid,ref}:null;
}

/** Conteúdo de dataTransfer é dado não confiável: só tipo e identificadores passam daqui. */
export function parsePanelPayload(raw:string):PanelInput|null{
  if(!raw||raw.length>2000)return null;
  try{return toPanelInput(JSON.parse(raw));}catch{return null;}
}

/** Constrói o painel a partir do catálogo carregado; título e destino nunca vêm do payload. */
export function resolvePanel(input:PanelInput,catalog:HomeCatalog):HomePanel|null{
  const project=catalog.projects.find(p=>p.id===input.project_id);if(!project)return null;
  if(input.kind==='project')return {key:panelKey('project',project.id),kind:'project',project_id:project.id,title:project.name};
  if(input.kind==='process'){const job=catalog.jobs.find(j=>j.id===input.ref&&j.project_id===project.id);return job?{key:panelKey('process',project.id,job.id),kind:'process',project_id:project.id,ref:job.id,title:job.title||'Pedido'}:null;}
  const item=catalog.reports(project.id)?.find(r=>r.id===input.ref);
  return item?{key:panelKey('report',project.id,item.id),kind:'report',project_id:project.id,ref:item.id,title:item.title||'Relatório'}:null;
}

/** Geometria finita, positiva e dentro das colunas; itens repetidos ficam com a primeira ocorrência. */
export function sanitizeLayout(items:unknown,cols:number):LayoutItem[]{
  if(!Array.isArray(items))return [];
  const seen=new Set<string>();const out:LayoutItem[]=[];
  for(const item of items){
    if(!isRecord(item))continue;const id=item.i;
    if(typeof id!=='string'||!id||seen.has(id))continue;
    if(![item.x,item.y,item.w,item.h].every(finite))continue;
    const w=clamp(Math.round(item.w as number),1,cols);const h=clamp(Math.round(item.h as number),3,40);
    out.push({i:id,x:clamp(Math.round(item.x as number),0,cols-w),y:clamp(Math.round(item.y as number),0,10000),w,h});seen.add(id);
  }
  return out;
}

const NO_PANELS:HomePanel[]=[];
export function readPanels(ws:Workspace):HomePanel[]{return Array.isArray(ws.homePanels)?ws.homePanels:NO_PANELS;}

/**
 * Migração e validação do estado da home. Painéis de projetos que sumiram do catálogo
 * NÃO são descartados aqui: a grade mostra "Projeto não encontrado" com opção de retirar,
 * para que uma raiz temporariamente desconectada não apague a organização.
 */
export function normalizeHome(input:Workspace):{ws:Workspace;overflow:number;invalid:number}{
  const layouts=isRecord(input.layouts)?input.layouts as Workspace['layouts']:{};
  const raw=Array.isArray(input.homePanels)?input.homePanels as unknown[]:[];
  const keys=new Set<string>();const valid:HomePanel[]=[];let invalid=0;
  for(const entry of raw){
    const parsed=toPanelInput(entry);if(!parsed){invalid++;continue;}
    const key=panelKey(parsed.kind,parsed.project_id,parsed.ref);if(keys.has(key))continue;
    const rawTitle=isRecord(entry)?entry.title:undefined;
    const title=typeof rawTitle==='string'&&rawTitle.trim()?rawTitle.trim().slice(0,160):parsed.kind==='project'?parsed.project_id:parsed.kind==='process'?'Pedido':'Relatório';
    keys.add(key);valid.push({...parsed,key,title});
  }
  const panels=valid.slice(0,HOME_PANEL_LIMIT);const kept=new Set(panels.map(p=>p.key));
  const nextLayouts={...layouts};
  for(const cols of [HOME_DESKTOP_COLS,1]){const key=homeLayoutKey(cols);if(key in layouts)nextLayouts[key]=sanitizeLayout(layouts[key],cols).filter(a=>kept.has(a.i));}
  return {ws:{...input,layouts:nextLayouts,homePanels:panels,view:input.view==='project'?'project':'home',startView:input.startView==='last'?'last':'home'},overflow:Math.max(0,valid.length-HOME_PANEL_LIMIT),invalid};
}

/**
 * Painéis com posição salva ficam onde o usuário deixou. Os demais seguem a regra automática:
 * um painel ocupa a largura toda; a partir de dois, dois por linha (w=6), redistribuindo também
 * o primeiro enquanto ele não tiver sido organizado à mão.
 */
export function homeLayout(panels:HomePanel[],saved:unknown,cols:number):LayoutItem[]{
  const keys=new Set(panels.map(p=>p.key));
  const manual=sanitizeLayout(saved,cols).filter(a=>keys.has(a.i));const placed=new Set(manual.map(a=>a.i));
  const bottom=manual.reduce((n,a)=>Math.max(n,a.y+a.h),0);
  const auto=panels.filter(p=>!placed.has(p.key));const half=Math.max(1,Math.floor(cols/2));
  const result:LayoutItem[]=[...manual];let y=bottom;const perRow=cols===1?1:2;
  for(let n=0;n<auto.length;n+=perRow){
    const row=auto.slice(n,n+perRow);
    row.forEach((p,j)=>result.push({i:p.key,x:cols===1?0:j*half,y,w:cols===1?1:panels.length===1?cols:half,h:defaultPanelHeight(p.kind)}));
    y+=Math.max(...row.map(p=>defaultPanelHeight(p.kind)));
  }
  return result.map(a=>({...a,minW:cols===1?1:3,minH:4,maxW:cols}));
}

export type AddResult={ws:Workspace;status:'opened'|'exists'|'full'};
/** Abre um painel sem nunca retirar outro: no limite, devolve 'full' e o chamador avisa. */
export function addPanel(ws:Workspace,panel:HomePanel,drop?:{x:number;y:number;cols:number}):AddResult{
  const panels=readPanels(ws);
  if(panels.some(p=>p.key===panel.key))return {ws,status:'exists'};
  if(panels.length>=HOME_PANEL_LIMIT)return {ws,status:'full'};
  let layouts=ws.layouts||{};
  if(drop){
    const key=homeLayoutKey(drop.cols);const saved=sanitizeLayout(layouts[key],drop.cols).filter(a=>panels.some(p=>p.key===a.i));
    // Só há posição de soltura quando a grade já foi organizada à mão; senão a regra lado a lado decide.
    if(saved.length){const w=drop.cols===1?1:Math.max(1,Math.floor(drop.cols/2));layouts={...layouts,[key]:[...saved,{i:panel.key,x:clamp(Math.round(drop.x),0,drop.cols-w),y:clamp(Math.round(drop.y),0,10000),w,h:defaultPanelHeight(panel.kind)}]};}
  }
  return {ws:{...ws,layouts,homePanels:[...panels,panel]},status:'opened'};
}

export function removePanel(ws:Workspace,key:string):Workspace{
  const layouts={...(ws.layouts||{})};
  for(const cols of [HOME_DESKTOP_COLS,1]){const k=homeLayoutKey(cols);if(Array.isArray(layouts[k]))layouts[k]=layouts[k].filter(a=>a.i!==key);}
  return {...ws,layouts,homePanels:readPanels(ws).filter(p=>p.key!==key)};
}

/** Ajustes por teclado ou botão; o resultado vira organização manual daquela largura. */
export function adjustLayout(layout:LayoutItem[],id:string,action:'wide'|'tall'|'short'|'before'|'after',cols:number):LayoutItem[]{
  const next=layout.map(a=>({...a}));const item=next.find(a=>a.i===id);if(!item)return next;
  if(action==='wide'){const half=Math.max(1,Math.floor(cols/2));item.w=item.w>=cols?half:cols;item.x=Math.min(item.x,cols-item.w);}
  else if(action==='tall')item.h=Math.min(40,item.h+1);
  else if(action==='short')item.h=Math.max(4,item.h-1);
  else{const order=[...next].sort((a,b)=>a.y-b.y||a.x-b.x);const peer=order[order.findIndex(a=>a.i===id)+(action==='before'?-1:1)];if(peer){[item.x,peer.x]=[peer.x,item.x];[item.y,peer.y]=[peer.y,item.y];if(item.x+item.w>cols)item.x=cols-item.w;if(peer.x+peer.w>cols)peer.x=cols-peer.w;}}
  return next.map(({i,x,y,w,h})=>({i,x,y,w,h}));
}

export type RecentRow={key:string;project:Project;delivery:Delivery;at:number|null};
const timeOf=(value?:string)=>{if(!value)return null;const t=Date.parse(value);return Number.isNaN(t)?null:t;};
/** Entregas reais dos detalhes já lidos, pela data da própria entrega; sem data vão ao fim. Histórico fica de fora. */
export function recentDeliveries(projects:Project[],details:Record<string,ProjectDetail|undefined>,limit=8):RecentRow[]{
  const rows:RecentRow[]=[];
  for(const project of projects){const detail=details[project.id];if(!detail)continue;for(const delivery of detail.deliveries||[]){if((delivery as Delivery&{historical?:boolean}).historical)continue;rows.push({key:`${project.id}:${delivery.id}`,project,delivery,at:timeOf(delivery.updated_at)});}}
  return rows.sort((a,b)=>a.at===null?(b.at===null?0:1):b.at===null?-1:b.at-a.at).slice(0,limit);
}

/** Projetos com pedido em andamento primeiro; depois pela última atualização registrada. */
export function orderProjects(projects:Project[],runningIds:Set<string>):Project[]{
  const byDate=(a:Project,b:Project)=>{const ta=timeOf(a.updated_at),tb=timeOf(b.updated_at);return ta===null?(tb===null?0:1):tb===null?-1:tb-ta;};
  return [...projects].sort((a,b)=>Number(runningIds.has(b.id))-Number(runningIds.has(a.id))||byDate(a,b));
}
