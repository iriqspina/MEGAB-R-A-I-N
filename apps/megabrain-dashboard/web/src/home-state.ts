// Estado puro da página principal: validação do que vem do /workspace ou de um arraste,
// geometria da grade de painéis e lista de entregas recentes. Sem React e sem rede.
import type {Delivery, HomePanel, HomePanelKind, Job, LayoutItem, Preview, Project, ProjectDetail, Workspace} from './types';

export const DRAG_PANEL='application/x-megabrain-panel';
/** Teto de RENDERIZAÇÃO (custo dos iframes). Painéis acima dele continuam salvos e são informados; nada é cortado do estado. */
export const HOME_PANEL_LIMIT=12;
export const HOME_DESKTOP_COLS=12;
export const HOME_NARROW_WIDTH=700;
export const homeLayoutKey=(cols:number)=>cols===1?'home:mobile':'home:desktop';
export type PanelInput={kind:HomePanelKind;project_id:string;ref?:string};
export type HomeCatalog={projects:Project[];jobs:Job[];reports:(pid:string)=>Preview[]|null};

/** Painéis globais não pertencem a um projeto; o identificador fixo só é aceito no tipo 'global'. */
export const GLOBAL_PID='*';
/** Módulos reais do projeto (os mesmos do quadro do projeto, mais as sessões observadas que hoje ficam dentro de Atividade). */
export const PROJECT_MODULES=[
  {id:'now',title:'Agora',hint:'Resumo e próximo passo'},{id:'results',title:'Resultados',hint:'Entregas do projeto'},
  {id:'references',title:'Referências',hint:'Repertório e arquivos'},{id:'activity',title:'Atividade',hint:'Pedidos e histórico registrado'},
  {id:'sessions',title:'Sessões observadas',hint:'Sessões locais do projeto'},{id:'process',title:'Processo',hint:'Esteira configurada'},
] as const;
export type ProjectModuleId=typeof PROJECT_MODULES[number]['id'];
/** Módulos globais que já existem na central. */
export const GLOBAL_MODULES=[{id:'sessions',title:'Sessões conectadas',hint:'Ferramentas ligadas aos projetos'},{id:'quotas',title:'Cotas de IA',hint:'Uso, janelas e origem dos dados'}] as const;
export type GlobalModuleId=typeof GLOBAL_MODULES[number]['id'];
/**
 * Seções fixas da mesa transformadas em painéis da própria grade (261014): mesma grade,
 * mesmos gestos, mesma persistência. Identidade por ref, nunca por título nem posição.
 */
export const STRIP_MODULES=[
  {id:'projects',title:'Seus projetos',hint:'Catálogo de projetos da central'},
  {id:'processes',title:'Pedidos e últimos registros',hint:'Em andamento e mais recentes'},
  {id:'recent',title:'Entregas e relatórios recentes',hint:'Pela data de cada entrega'},
] as const;
export type StripModuleId=typeof STRIP_MODULES[number]['id'];
/** Versão da migração que criou os painéis de seção; persistida junto com o estado. */
export const HOME_SECTIONS_VERSION=1;
const isStripModule=(value:unknown):value is StripModuleId=>STRIP_MODULES.some(m=>m.id===value);
export const stripTitle=(id?:string)=>STRIP_MODULES.find(m=>m.id===id)?.title||'Seção';
const isProjectModule=(value:unknown):value is ProjectModuleId=>PROJECT_MODULES.some(m=>m.id===value);
const isGlobalModule=(value:unknown):value is GlobalModuleId=>GLOBAL_MODULES.some(m=>m.id===value);
export const moduleTitle=(id?:string)=>PROJECT_MODULES.find(m=>m.id===id)?.title||'Módulo';
export const globalTitle=(id?:string)=>GLOBAL_MODULES.find(m=>m.id===id)?.title||'Painel';

const KINDS:HomePanelKind[]=['project','process','report','module','global','strip'];
const HEIGHT:Record<HomePanelKind,number>={project:9,process:7,report:9,module:7,global:8,strip:8};
const HASH=/^[a-f0-9]{64}$/;
const isRecord=(value:unknown):value is Record<string,unknown>=>typeof value==='object'&&value!==null&&!Array.isArray(value);
const cleanId=(value:unknown,max:number)=>typeof value==='string'&&value.length>0&&value.length<=max&&!/[\u0000-\u001f]/.test(value)?value:null;
const clamp=(value:number,min:number,max:number)=>Math.min(max,Math.max(min,value));
const finite=(value:unknown)=>typeof value==='number'&&Number.isFinite(value);

export const panelKey=(kind:HomePanelKind,pid:string,ref?:string)=>`${kind}:${pid}:${kind==='project'?'':ref||''}`;
export const defaultPanelHeight=(kind:HomePanelKind)=>HEIGHT[kind];
/** Mesma forma de reportKey (MultiReportWorkspace): identifica o relatório em qualquer destino. */
export const reportOwnerKey=(pid:string,fid:string)=>`${pid}:${fid}`;

/** Lê uma entrada desconhecida; devolve null para qualquer forma inválida. */
export function toPanelInput(value:unknown):PanelInput|null{
  if(!isRecord(value)||!KINDS.includes(value.kind as HomePanelKind))return null;
  const kind=value.kind as HomePanelKind;
  if(kind==='global')return value.project_id===GLOBAL_PID&&isGlobalModule(value.ref)?{kind,project_id:GLOBAL_PID,ref:value.ref}:null;
  if(kind==='strip')return value.project_id===GLOBAL_PID&&isStripModule(value.ref)?{kind,project_id:GLOBAL_PID,ref:value.ref}:null;
  const pid=cleanId(value.project_id,200);if(!pid||pid===GLOBAL_PID)return null;
  if(kind==='project')return {kind,project_id:pid};
  if(kind==='module')return isProjectModule(value.ref)?{kind,project_id:pid,ref:value.ref}:null;
  const ref=cleanId(value.ref,300);return ref?{kind,project_id:pid,ref}:null;
}

/** Conteúdo de dataTransfer é dado não confiável: só tipo e identificadores passam daqui. */
export function parsePanelPayload(raw:string):PanelInput|null{
  if(!raw||raw.length>2000)return null;
  try{return toPanelInput(JSON.parse(raw));}catch{return null;}
}

/** Validação padrão sem janela (verificações puras): só caminhos da própria API ou https. O app passa safeUrl. */
export const defaultValidUrl=(url:string)=>(/^\/api\/[A-Za-z0-9_%./-]+$/.test(url)&&!url.includes('..'))||/^https:\/\/[^\s"'<>]+$/.test(url);

/** Cópia do relatório guardada no painel; só campos conhecidos, endereço validado e id coerente com o painel. */
export function sanitizePreview(value:unknown,pid:string,fid:string,validUrl:(url:string)=>boolean=defaultValidUrl):Preview|undefined{
  if(!isRecord(value))return undefined;
  const text=(v:unknown,max:number)=>typeof v==='string'&&v.length>0&&v.length<=max?v:undefined;
  const title=text(value.title,300),type=text(value.type,40),url=text(value.url,2000);
  if(value.id!==fid||!title||!type||!url||!validUrl(url))return undefined;
  if(value.project_id!==undefined&&value.project_id!==pid)return undefined;
  const out:Preview={id:fid,title,type,url,project_id:pid};
  const caption=text(value.caption,500);if(caption)out.caption=caption;
  if(typeof value.hash==='string'&&HASH.test(value.hash))out.hash=value.hash;
  if(typeof value.interactive==='boolean')out.interactive=value.interactive;
  return out;
}

/** Constrói o painel a partir do catálogo carregado; título e destino nunca vêm do payload. */
export function resolvePanel(input:PanelInput,catalog:HomeCatalog,validUrl:(url:string)=>boolean=defaultValidUrl):HomePanel|null{
  if(input.kind==='global'){
    const global=GLOBAL_MODULES.find(m=>m.id===input.ref);
    return input.project_id===GLOBAL_PID&&global?{key:panelKey('global',GLOBAL_PID,global.id),kind:'global',project_id:GLOBAL_PID,ref:global.id,title:global.title}:null;
  }
  if(input.kind==='strip'){
    const strip=STRIP_MODULES.find(m=>m.id===input.ref);
    return input.project_id===GLOBAL_PID&&strip?{key:panelKey('strip',GLOBAL_PID,strip.id),kind:'strip',project_id:GLOBAL_PID,ref:strip.id,title:strip.title}:null;
  }
  const project=catalog.projects.find(p=>p.id===input.project_id);if(!project)return null;
  if(input.kind==='project')return {key:panelKey('project',project.id),kind:'project',project_id:project.id,title:project.name};
  if(input.kind==='module'){const mod=PROJECT_MODULES.find(m=>m.id===input.ref);return mod?{key:panelKey('module',project.id,mod.id),kind:'module',project_id:project.id,ref:mod.id,title:mod.title}:null;}
  if(input.kind==='process'){const job=catalog.jobs.find(j=>j.id===input.ref&&j.project_id===project.id);return job?{key:panelKey('process',project.id,job.id),kind:'process',project_id:project.id,ref:job.id,title:job.title||'Pedido'}:null;}
  const item=catalog.reports(project.id)?.find(r=>r.id===input.ref);if(!item)return null;
  const preview=sanitizePreview({...item,project_id:project.id},project.id,item.id,validUrl);
  return {key:panelKey('report',project.id,item.id),kind:'report',project_id:project.id,ref:item.id,title:item.title||'Relatório',...(preview?{preview}:{})};
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

/**
 * Grava as posições recebidas da grade sem perder as demais: painéis fechados ou acima do teto
 * de exibição continuam com a geometria salva. Só as chaves de `next` são substituídas.
 */
export function mergeLayout(saved:unknown,next:readonly LayoutItem[],cols:number):LayoutItem[]{
  const fresh=sanitizeLayout(next,cols);const ids=new Set(fresh.map(a=>a.i));
  return [...fresh,...sanitizeLayout(saved,cols).filter(a=>!ids.has(a.i))];
}

/**
 * Quadro do projeto: grava só as chaves de `next` e mantém as demais entradas salvas (módulos ocultos,
 * relatórios fixados retirados), para que reexibir/refixar volte ao mesmo lugar. Sem limites novos.
 */
export function replaceLayoutItems(saved:readonly LayoutItem[]|undefined,next:readonly LayoutItem[]):LayoutItem[]{
  const ids=new Set(next.map(a=>a.i));
  return [...next.map(({i,x,y,w,h})=>({i,x,y,w,h})),...(Array.isArray(saved)?saved:[]).filter(a=>isRecord(a)&&typeof a.i==='string'&&!ids.has(a.i))];
}

const NO_PANELS:HomePanel[]=[];
export function readPanels(ws:Workspace):HomePanel[]{return Array.isArray(ws.homePanels)?ws.homePanels:NO_PANELS;}

/**
 * Migração e validação do estado da home. Painéis de projetos que sumiram do catálogo
 * NÃO são descartados aqui: a grade mostra "Projeto não encontrado" com opção de retirar,
 * para que uma raiz temporariamente desconectada não apague a organização.
 * Nenhum painel salvo é cortado; `overflow` só conta os que ficam acima do teto de exibição.
 * Geometrias de painéis fechados também são mantidas, para a reabertura voltar ao mesmo lugar.
 */
export function normalizeHome(input:Workspace,validUrl:(url:string)=>boolean=defaultValidUrl):{ws:Workspace;overflow:number;invalid:number}{
  const layouts=isRecord(input.layouts)?input.layouts as Workspace['layouts']:{};
  const raw=Array.isArray(input.homePanels)?input.homePanels as unknown[]:[];
  const keys=new Set<string>();const valid:HomePanel[]=[];let invalid=0;
  for(const entry of raw){
    const parsed=toPanelInput(entry);if(!parsed){invalid++;continue;}
    const key=panelKey(parsed.kind,parsed.project_id,parsed.ref);if(keys.has(key))continue;
    const rawTitle=isRecord(entry)?entry.title:undefined;
    const title=parsed.kind==='module'?moduleTitle(parsed.ref):parsed.kind==='global'?globalTitle(parsed.ref):parsed.kind==='strip'?stripTitle(parsed.ref)
      :typeof rawTitle==='string'&&rawTitle.trim()?rawTitle.trim().slice(0,160):parsed.kind==='project'?parsed.project_id:parsed.kind==='process'?'Pedido':'Relatório';
    const panel:HomePanel={...parsed,key,title};
    if(parsed.kind==='report'&&isRecord(entry)){const preview=sanitizePreview(entry.preview,parsed.project_id,parsed.ref!,validUrl);if(preview)panel.preview=preview;}
    keys.add(key);valid.push(panel);
  }
  const nextLayouts={...layouts};
  for(const cols of [HOME_DESKTOP_COLS,1]){const key=homeLayoutKey(cols);if(key in layouts)nextLayouts[key]=sanitizeLayout(layouts[key],cols);}
  let panels=valid;
  // Migração das seções fixas para painéis da grade (261014), uma única vez por estado.
  // A marca persistida impede que seção fechada depois da migração reapareça na recarga;
  // geometria já salva (inclusive de seção fechada com keep) nunca é substituída.
  if(input.homeSectionsVersion!==HOME_SECTIONS_VERSION){
    const present=new Set(panels.map(p=>p.key));
    // Mesma ordem de campos do restante do normalize, para a passada 2 ser idêntica à 1.
    const created=STRIP_MODULES.filter(m=>!present.has(panelKey('strip',GLOBAL_PID,m.id)))
      .map(m=>{const parsed={kind:'strip' as const,project_id:GLOBAL_PID,ref:m.id};return {...parsed,key:panelKey('strip',GLOBAL_PID,m.id),title:m.title};});
    if(created.length)panels=[...created,...panels];
    for(const cols of [HOME_DESKTOP_COLS,1]){
      const layoutKey=homeLayoutKey(cols);const entries=sanitizeLayout(nextLayouts[layoutKey],cols);
      const known=new Set(entries.map(a=>a.i));
      const bottom=entries.reduce((n,a)=>Math.max(n,a.y+a.h),0);
      let y=bottom;const added:LayoutItem[]=[];
      for(const m of STRIP_MODULES){const id=panelKey('strip',GLOBAL_PID,m.id);if(known.has(id))continue;
        const half=Math.max(1,Math.floor(cols/2));
        const h=m.id==='projects'?6:m.id==='processes'?7:8;
        const w=cols===1?1:m.id==='projects'?cols:half;
        const x=cols===1||m.id!=='recent'?0:cols-half;
        added.push({i:id,x,y,w,h});
        y+=cols===1||m.id==='projects'?h:0; // pedidos e entregas dividem a mesma linha no desktop
      }
      if(added.length)nextLayouts[layoutKey]=[...entries.filter(a=>!added.some(b=>b.i===a.i)),...added];
    }
  }
  return {ws:{...input,homeSectionsVersion:HOME_SECTIONS_VERSION,layouts:nextLayouts,homePanels:panels,view:input.view==='project'?'project':'home',startView:input.startView==='last'?'last':'home'},overflow:Math.max(0,panels.filter(p=>p.kind!=='strip').length-HOME_PANEL_LIMIT),invalid};
}

/**
 * Um relatório tem um único dono. Se o mesmo relatório estiver na home e em Respostas,
 * Respostas (já montada, com rascunho e versão) fica com ele; o painel da home sai da lista
 * mas a geometria dele continua guardada em layouts.
 */
export function dedupeReports(ws:Workspace,responseKeys:Set<string>):{ws:Workspace;moved:number}{
  const panels=readPanels(ws);const kept=panels.filter(p=>!(p.kind==='report'&&p.ref&&responseKeys.has(reportOwnerKey(p.project_id,p.ref))));
  return kept.length===panels.length?{ws,moved:0}:{ws:{...ws,homePanels:kept},moved:panels.length-kept.length};
}

/** Quais painéis a grade monta: os de outro dono ficam fora; acima do teto ficam salvos e listados em `waiting`. Seções (strip) são sempre exibidas e não consomem o teto de painéis comuns. */
export function splitRendered(panels:HomePanel[],responseKeys:Set<string>=new Set<string>()):{shown:HomePanel[];waiting:HomePanel[];elsewhere:HomePanel[]}{
  const elsewhere=panels.filter(p=>p.kind==='report'&&p.ref&&responseKeys.has(reportOwnerKey(p.project_id,p.ref)));
  const eligible=panels.filter(p=>!elsewhere.includes(p));
  const shown:HomePanel[]=[];const waiting:HomePanel[]=[];let common=0;
  for(const panel of eligible){
    if(panel.kind==='strip'){shown.push(panel);continue;}
    if(common<HOME_PANEL_LIMIT){shown.push(panel);common++;}else waiting.push(panel);
  }
  return {shown,waiting,elsewhere};
}

/** Abrir/apresentar um salvo acima do teto traz sua chave à tela; os outros continuam salvos, com a mesma geometria. */
export function promotePanel(ws:Workspace,key:string,responseKeys:Set<string>=new Set<string>()):{ws:Workspace;status:'shown'|'promoted'|'elsewhere'|'missing'}{
  const panels=readPanels(ws),split=splitRendered(panels,responseKeys);
  if(split.shown.some(p=>p.key===key))return {ws,status:'shown'};
  if(split.elsewhere.some(p=>p.key===key))return {ws,status:'elsewhere'};
  const item=split.waiting.find(p=>p.key===key);if(!item)return {ws,status:'missing'};
  const anchor=split.shown.at(-1),index=anchor?panels.findIndex(p=>p.key===anchor.key):0;
  const next=panels.filter(p=>p.key!==key);next.splice(Math.max(0,index),0,item);
  // Congela também a geometria automática antes de guardar um exibido.
  const layouts={...ws.layouts};for(const cols of [HOME_DESKTOP_COLS,1]){const layoutKey=homeLayoutKey(cols);layouts[layoutKey]=mergeLayout(layouts[layoutKey],homeLayout(split.shown,layouts[layoutKey],cols),cols);}
  return {ws:{...ws,layouts,homePanels:next},status:'promoted'};
}

/** Nenhuma chegada é excluída sem destino: painel em espera é promovido; pin fechado é reaberto; demais vão a Respostas. */
export function classifyReturnArrivals<T extends {project_id?:string;id:string}>(arrivals:readonly T[],ws:Workspace,responseKeys:Set<string>,pinned:Map<string,'home'|'main'>):{responses:T[];promoteHome:T[];reopenPins:T[];kept:T[]}{
  const panels=readPanels(ws),shown=new Set(splitRendered(panels,responseKeys).shown.map(p=>p.key));
  const home=new Map(panels.filter(p=>p.kind==='report'&&p.ref).map(p=>[reportOwnerKey(p.project_id,p.ref!),p]));
  const manual=new Set((Array.isArray(ws.views)?ws.views:[]).flatMap(v=>isRecord(v)&&typeof v.project_id==='string'&&typeof v.id==='string'?[reportOwnerKey(v.project_id,v.id)]:[]));
  const result:{responses:T[];promoteHome:T[];reopenPins:T[];kept:T[]}={responses:[],promoteHome:[],reopenPins:[],kept:[]};
  for(const item of arrivals){const pid=item.project_id||'',key=reportOwnerKey(pid,item.id),panel=home.get(key);
    if(responseKeys.has(key))result.responses.push(item);
    else if(panel){if(shown.has(panel.key)&&ws.view!=='project')result.kept.push(item);else result.promoteHome.push(item);}
    else if(manual.has(key)&&(isPinClosed(ws,pid,item.id)||!pinned.has(key)||(pinned.get(key)==='home'?ws.view==='project':ws.view!=='project'||(ws.activeProject!==pid&&ws.compareProject!==pid))))result.reopenPins.push(item);
    else if(pinned.has(key))result.kept.push(item);
    else result.responses.push(item);
  }
  return result;
}

/** Onde um item já está aberto. Relatórios contam também em Respostas, para a alternância fechar o dono certo. */
export function openOwner(panels:HomePanel[],responseKeys:Set<string>,input:PanelInput):'home'|'responses'|null{
  if(input.kind==='report'&&input.ref&&responseKeys.has(reportOwnerKey(input.project_id,input.ref)))return 'responses';
  const key=panelKey(input.kind,input.project_id,input.ref);
  return panels.some(p=>p.key===key)?'home':null;
}

/** No catálogo, guardado/invisível mostra primeiro; só o editor/painel atualmente exibido fecha. */
export function catalogState(ws:Workspace,responseKeys:Set<string>,visiblePins:Set<string>,input:PanelInput):'visible'|'stored'|'closed'{
  const key=panelKey(input.kind,input.project_id,input.ref),report=input.kind==='report'&&input.ref?reportOwnerKey(input.project_id,input.ref):null;
  if(report&&responseKeys.has(report))return ws.responsesCollapsed===true?'stored':'visible';
  const panels=readPanels(ws);
  if(panels.some(p=>p.key===key))return ws.view!=='project'&&splitRendered(panels,responseKeys).shown.some(p=>p.key===key)?'visible':'stored';
  if(report&&visiblePins.has(report)&&!isPinClosed(ws,input.project_id,input.ref!))return 'visible';
  const pinned=report&&(Array.isArray(ws.views)?ws.views:[]).some(v=>isRecord(v)&&v.project_id===input.project_id&&v.id===input.ref);
  return pinned&&!isPinClosed(ws,input.project_id,input.ref!)?'stored':'closed';
}

/** Catalogue close hides a pin; its manual fixation, snapshot and geometry remain intact. */
export function isPinClosed(ws:Workspace,pid:string,fid:string):boolean{
  return isRecord(ws.closedPins)&&ws.closedPins[reportOwnerKey(pid,fid)]===true;
}
export function setPinClosed(ws:Workspace,pid:string,fid:string,closed:boolean):Workspace{
  const previous=isRecord(ws.closedPins)?ws.closedPins:{};
  return {...ws,closedPins:{...previous,[reportOwnerKey(pid,fid)]:closed}};
}

/**
 * Relatórios fixados no quadro de um projeto (views) que têm editor montado, e onde.
 * O quadro do projeto aberto num painel da home é o dono persistente (a home fica montada ao trocar
 * de visão); o quadro principal só é dono quando a home não exibe aquele projeto. Relatório já aberto
 * em Respostas ou num painel de relatório exibido na home não tem editor fixado (fica estático).
 * homeBoards/mainBoards: projetos cujo quadro está montado com detalhe lido em cada lugar.
 */
export function pinOwners(pins:readonly {project_id?:string;id:string}[],shown:readonly HomePanel[],responseKeys:Set<string>,homeBoards:Set<string>,mainBoards:Set<string>):Map<string,'home'|'main'>{
  const taken=new Set([...responseKeys,...shown.filter(p=>p.kind==='report'&&p.ref).map(p=>reportOwnerKey(p.project_id,p.ref!))]);
  const out=new Map<string,'home'|'main'>();
  for(const v of pins){
    if(!v.project_id||typeof v.id!=='string')continue;const key=reportOwnerKey(v.project_id,v.id);if(taken.has(key)||out.has(key))continue;
    if(homeBoards.has(v.project_id))out.set(key,'home');else if(mainBoards.has(v.project_id))out.set(key,'main');
  }
  return out;
}

/**
 * Um editor de esteira por projeto, escolhido entre os painéis exibidos na home (que ficam montados):
 * módulo Processo > quadro do projeto > primeiro painel de pedido. Sem dono na home, o quadro principal edita.
 * `ready` diz se o painel está de fato com o conteúdo montado (detalhe lido, pedido existente).
 */
export function routingOwners(shown:readonly HomePanel[],ready:(p:HomePanel)=>boolean):Map<string,string>{
  const owners=new Map<string,string>();
  const ranks:((p:HomePanel)=>boolean)[]=[p=>p.kind==='module'&&p.ref==='process',p=>p.kind==='project',p=>p.kind==='process'];
  for(const rank of ranks)for(const p of shown)if(rank(p)&&!owners.has(p.project_id)&&ready(p))owners.set(p.project_id,p.key);
  return owners;
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

export type AddResult={ws:Workspace;status:'opened'|'exists'|'waiting'};
/**
 * Abre um painel sem nunca retirar outro. Acima do teto de exibição o painel é salvo assim mesmo
 * ('waiting') e aparece quando outro for fechado. Reabrir sem soltura volta à geometria guardada;
 * soltura explícita atualiza só a posição daquela chave (sem duplicar).
 */
export function addPanel(ws:Workspace,panel:HomePanel,drop?:{x:number;y:number;cols:number}):AddResult{
  const panels=readPanels(ws);
  if(panels.some(p=>p.key===panel.key))return {ws,status:'exists'};
  let layouts=ws.layouts||{};
  if(drop){
    const key=homeLayoutKey(drop.cols);const all=sanitizeLayout(layouts[key],drop.cols);const open=new Set(panels.map(p=>p.key));
    // Só há posição de soltura quando a grade já foi organizada à mão; senão a regra lado a lado decide.
    if(all.some(a=>open.has(a.i))){
      const old=all.find(a=>a.i===panel.key);const w=old?.w??(drop.cols===1?1:Math.max(1,Math.floor(drop.cols/2)));const h=old?.h??defaultPanelHeight(panel.kind);
      layouts={...layouts,[key]:[...all.filter(a=>a.i!==panel.key),{i:panel.key,x:clamp(Math.round(drop.x),0,drop.cols-w),y:clamp(Math.round(drop.y),0,10000),w,h}]};
    }
  }
  const next=[...panels,panel];
  return {ws:{...ws,layouts,homePanels:next},status:next.length>HOME_PANEL_LIMIT?'waiting':'opened'};
}

/**
 * Fechar é reversível: a geometria fica guardada pela chave. `keep` é a posição efetiva na tela
 * (mesmo quando ainda automática), gravada antes de sair para a reabertura voltar ao mesmo lugar.
 */
export function removePanel(ws:Workspace,key:string,keep?:{layoutKey:string;item:LayoutItem}):Workspace{
  let layouts=ws.layouts||{};
  if(keep&&keep.item.i===key){
    const cols=keep.layoutKey===homeLayoutKey(1)?1:keep.layoutKey===homeLayoutKey(HOME_DESKTOP_COLS)?HOME_DESKTOP_COLS:0;
    if(cols)layouts={...layouts,[keep.layoutKey]:mergeLayout(layouts[keep.layoutKey],[keep.item],cols)};
  }
  return {...ws,layouts,homePanels:readPanels(ws).filter(p=>p.key!==key)};
}

/** "Lado a lado" redistribui só os abertos; geometrias de painéis fechados continuam guardadas. */
export function resetOpenLayout(ws:Workspace,cols:number):Workspace{
  const key=homeLayoutKey(cols);const open=new Set(readPanels(ws).map(p=>p.key));
  return {...ws,layouts:{...ws.layouts,[key]:sanitizeLayout(ws.layouts?.[key],cols).filter(a=>!open.has(a.i))}};
}

/** Ajustes por teclado (setas no título do painel); o resultado vira organização manual daquela largura. */
export function adjustLayout(layout:LayoutItem[],id:string,action:'wide'|'narrow'|'wider'|'tall'|'short'|'before'|'after',cols:number):LayoutItem[]{
  const next=layout.map(a=>({...a}));const item=next.find(a=>a.i===id);if(!item)return next;
  const minW=Math.max(1,cols>1?(item.minW??3):1);
  if(action==='wide'){const half=Math.max(1,Math.floor(cols/2));item.w=item.w>=cols?half:cols;item.x=Math.min(item.x,cols-item.w);}
  else if(action==='wider'){item.w=Math.min(cols,item.w+1);item.x=Math.min(item.x,cols-item.w);}
  else if(action==='narrow'){item.w=Math.max(minW,item.w-1);}
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
