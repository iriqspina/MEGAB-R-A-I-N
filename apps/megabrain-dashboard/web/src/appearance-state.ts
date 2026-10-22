import type {HomePanel,LayoutItem,Project,Workspace} from './types';

/** Identidade visual da central; nomes exibidos nunca renomeiam arquivos ou projetos de origem. */
export const PALETTE=[{name:'Rosa',color:'#ff82c4'},{name:'Verde',color:'#b2e58a'},{name:'Azul',color:'#8bc8ff'},{name:'Âmbar',color:'#efc987'},{name:'Violeta',color:'#ceacff'}] as const;
export type Appearance={name?:string;emoji?:string;color?:string};
const record=(v:unknown):v is Record<string,unknown>=>Boolean(v&&typeof v==='object'&&!Array.isArray(v));
const clean=(v:unknown,n:number)=>typeof v==='string'?v.replace(/[\u0000-\u001f\u007f]/g,'').trim().slice(0,n):'';
/** 261016: qualquer cor em #rrggbb (paleta ou escolhida livremente); o resto é descartado. */
export const validColor=(v:unknown)=>typeof v==='string'&&/^#[0-9a-f]{6}$/i.test(v.trim())?v.trim().toLowerCase():undefined;
/** Cor por tipo de quadro: vale para esse tipo em todos os projetos; a cor própria de um quadro continua mandando. */
export const TYPE_KEYS=[{id:'now',title:'Agora'},{id:'results',title:'Resultados'},{id:'references',title:'Referências'},{id:'activity',title:'Atividade'},{id:'sessions',title:'Sessões observadas'},{id:'process',title:'Processo'}] as const;
export const typeAppearanceKey=(id:string)=>`type:${id}`;
const typeColor=(ws:Workspace,key:string)=>{const parts=key.split(':');return parts.length===3&&parts[0]==='module'?readAppearance(ws,typeAppearanceKey(parts[2])).color:undefined;};
export const projectAppearanceKey=(id:string)=>`project:${id}:`;
export function readAppearance(ws:Workspace,key:string):Appearance{
  const value=record(ws.appearance)?ws.appearance[key]:null;if(!record(value))return {};
  const name=clean(value.name,90),emoji=clean(value.emoji,16),color=validColor(value.color);
  return {...(name?{name}:{}),...(emoji?{emoji}:{}),...(color?{color}:{})};
}
export function setAppearance(ws:Workspace,key:string,value:Appearance|null):Workspace{
  const map=record(ws.appearance)?ws.appearance:{};
  if(!value)return {...ws,appearance:Object.fromEntries(Object.entries(map).filter(([k])=>k!==key))};
  const normalized=readAppearance({...ws,appearance:{[key]:value}},key);
  return {...ws,appearance:{...map,[key]:normalized}};
}
export function defaultAccent(key:string){const semantic:Record<string,string>={projects:'#ff82c4',processes:'#ceacff',recent:'#b2e58a',now:'#ff82c4',results:'#b2e58a',references:'#8bc8ff',activity:'#efc987',process:'#ceacff',sessions:'#8bc8ff',quotas:'#efc987'};const known=semantic[key.split(':').at(-1)||''];if(known)return known;let hash=0;for(const c of key)hash=(hash*31+c.charCodeAt(0))>>>0;return PALETTE[hash%PALETTE.length].color;}
export function appearanceFor(ws:Workspace,key:string,title:string,color?:string){
  const a=readAppearance(ws,key);return {name:a.name||title,emoji:a.emoji||'',label:[a.emoji,a.name||title].filter(Boolean).join(' '),color:a.color||typeColor(ws,key)||color||defaultAccent(key)};
}
export function presentProject(ws:Workspace,project:Project):Project{
  const a=appearanceFor(ws,projectAppearanceKey(project.id),project.source_name||project.name,project.source_color||project.color);
  return {...project,name:a.label,color:a.color,source_name:project.source_name||project.name,source_color:project.source_color||project.color};
}

/** Troca só a cor; nome e emoji escolhidos antes continuam. Sem nada próprio, a entrada some e volta o padrão. */
export function setColor(ws:Workspace,key:string,color:string|null):Workspace{
  const {color:_old,...rest}=readAppearance(ws,key);const chosen=validColor(color);const next=chosen?{...rest,color:chosen}:rest;
  return setAppearance(ws,key,Object.keys(next).length?next:null);
}
/** Como o quadro fica sem a escolha própria dele: considera a cor do tipo, a do projeto e o padrão. */
export const inheritedLook=(ws:Workspace,key:string,title:string,color?:string)=>appearanceFor(setAppearance(ws,key,null),key,title,color);
export type ColorRow={key:string;label:string;color:string;own:boolean;hint?:string};
const KIND_HINT:Record<string,string>={process:'Pedido',report:'Relatório',module:'Módulo',global:'Geral',strip:'Seção'};
/** Linhas do menu Cores. projects chega já apresentado (nome/cor da central; source_* guarda a origem). */
export function colorRows(ws:Workspace,projects:Project[],visiblePanels?:HomePanel[]){
  const byId=new Map(projects.map(p=>[p.id,p]));const own=(key:string)=>Boolean(readAppearance(ws,key).color);
  const types:ColorRow[]=TYPE_KEYS.map(t=>{const key=typeAppearanceKey(t.id);return {key,label:t.title,color:readAppearance(ws,key).color||defaultAccent(t.id),own:own(key),...(own(key)?{}:{hint:'Padrão'})};});
  const panels=visiblePanels||(Array.isArray(ws.homePanels)?ws.homePanels as HomePanel[]:[]);
  const priority=[...new Set([...panels.filter(p=>p.kind==='project').map(p=>p.project_id),...(ws.openProjects||[])])].filter(id=>byId.has(id));
  const projectRow=(p:Project):ColorRow=>{const key=projectAppearanceKey(p.id);const look=appearanceFor(ws,key,p.source_name||p.name,p.source_color||p.color);return {key,label:look.label,color:look.color,own:own(key)};};
  const featured=priority.map(id=>projectRow(byId.get(id)!));
  const others=projects.filter(p=>!priority.includes(p.id)).map(projectRow).sort((a,b)=>a.label.localeCompare(b.label,'pt-BR'));
  const desk:ColorRow[]=panels.filter(p=>p.kind!=='project').map(p=>{const project=byId.get(p.project_id);const look=appearanceFor(ws,p.key,p.title,project?.color);return {key:p.key,label:look.label,color:look.color,own:own(p.key),hint:[KIND_HINT[p.kind],project?.source_name||project?.name].filter(Boolean).join(' · ')};});
  return {types,featured,others,desk};
}

/** Reorganiza somente os itens visíveis nesta largura. Identidades e estado de conteúdo não mudam. */
export function matchPanelSize(layout:LayoutItem[],sourceId:string,cols:number):LayoutItem[]{
  const source=layout.find(i=>i.i===sourceId);if(!source)return layout;
  const minW=Math.max(cols===1?1:3,...layout.map(a=>a.minW||1));
  const maxW=Math.min(cols,...layout.map(a=>a.maxW||cols));
  const w=Math.min(maxW,Math.max(minW,Math.round(source.w))),h=Math.max(4,...layout.map(a=>a.minH||1),Math.min(40,Math.round(source.h)));
  const ordered=[...layout].sort((a,b)=>a.y-b.y||a.x-b.x);let x=0,y=0;
  return ordered.map(item=>{if(x+w>cols){x=0;y+=h;}const next={...item,x,y,w,h};x+=w;return next;});
}

/** Encaixe lado a lado na linha do alvo; o restante desce se ocupar a mesma área. */
export function dockPanels(layout:LayoutItem[],sourceId:string,targetId:string,side:'left'|'right',cols:number):LayoutItem[]{
  if(cols<6||sourceId===targetId)return layout;
  const target=layout.find(i=>i.i===targetId),source=layout.find(i=>i.i===sourceId);if(!target||!source)return layout;
  const half=Math.floor(cols/2),h=Math.max(4,Math.min(40,target.h)),y=target.y;
  const pair=[{...source,x:side==='left'?0:half,y,w:side==='left'?half:cols-half,h},{...target,x:side==='left'?half:0,y,w:side==='left'?cols-half:half,h}];
  const placed=[...pair];const intersects=(a:LayoutItem,b:LayoutItem)=>a.x<b.x+b.w&&a.x+a.w>b.x&&a.y<b.y+b.h&&a.y+a.h>b.y;
  for(const original of [...layout].filter(i=>i.i!==sourceId&&i.i!==targetId).sort((a,b)=>a.y-b.y||a.x-b.x)){
    const item={...original};let collisions=placed.filter(a=>intersects(item,a));
    while(collisions.length){item.y=Math.max(...collisions.map(a=>a.y+a.h));collisions=placed.filter(a=>intersects(item,a));}
    placed.push(item);
  }
  return layout.map(item=>placed.find(a=>a.i===item.i)!);
}
