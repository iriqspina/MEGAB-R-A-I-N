import {useCallback,useEffect,useLayoutEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';
import {createPortal} from 'react-dom';
import {ArrowRight,Workflow} from 'lucide-react';
import RoutingEditor from './RoutingEditor';
import type {Preview} from './types';
import './workspace-editors.css';

const CHANGE='mb-editor-slot-change';
const reportKey=(p:Preview)=>`${p.project_id||''}:${p.id}`;
const event=()=>{window.dispatchEvent(new Event(CHANGE));};
const shown=(node:HTMLElement)=>node.getClientRects().length>0;
/** Stable body portal: document coordinates escape the grid's positioned container.
 * The browser scrolls the same nodes with their slots, including before a JS frame.
 */
function documentLayer(content:ReactNode){
  const spacing=document.querySelector<HTMLElement>('.app-shell')?.style.getPropertyValue('--space-factor')||'1';
  return createPortal(<div className="workspace-document-layer flexible-shell" style={{'--space-factor':spacing} as CSSProperties}>{content}</div>,document.body);
}
export function ReportEditorSlot({pid,fid,host}:{pid:string;fid:string;host:string}){
  useLayoutEffect(()=>{event();return()=>event();},[pid,fid,host]);
  return <div className="workspace-report-slot"><div className="workspace-report-target" data-report-editor-slot={`${pid}:${fid}`} data-editor-host={host}/></div>;
}
export function RoutingEditorSlot({pid,host,onReveal}:{pid:string;host:string;onReveal:()=>void}){
  useLayoutEffect(()=>{event();return()=>event();},[pid,host]);
  return <div className="workspace-routing-slot" data-routing-editor-slot={pid} data-editor-host={host}><div className="workspace-editor-fallback"><Workflow size={17}/><p>Esta esteira tem um único editor, com o rascunho preservado.<button className="text-button" onClick={onReveal}>Ir até ele <ArrowRight size={13}/></button></p></div></div>;
}

export type HomeBody={key:string;content:ReactNode;report:boolean;kind:string;project?:string;module:string;ready:boolean};
/** Cada corpo visitado permanece no mesmo nó; só sua caixa/visibilidade acompanha a grade. */
export function FixedHomeBodies({bodies,visibleKeys}:{bodies:HomeBody[];visibleKeys:Set<string>}){
  const latest=useRef({bodies,visibleKeys});latest.current={bodies,visibleKeys};
  const frame=useRef<number|null>(null),[rects,setRects]=useState<Record<string,Rect>>({});
  const align=useCallback(()=>{const next:Record<string,Rect>={};
    for(const body of latest.current.bodies){if(!latest.current.visibleKeys.has(body.key))continue;
      const slot=document.querySelector<HTMLElement>(`[data-home-body-slot="${CSS.escape(body.key)}"]`);const box=slot&&bounds(slot);if(box)next[body.key]=box;
    }
    setRects(old=>JSON.stringify(old)===JSON.stringify(next)?old:next);
  },[]);
  const schedule=useCallback(()=>{if(frame.current===null)frame.current=requestAnimationFrame(()=>{frame.current=null;align();});},[align]);
  useLayoutEffect(()=>{align();},[bodies,visibleKeys,align]);
  const work=bodies.length>0;
  useEffect(()=>{if(!work)return;
    // 261014 · durante a transição CSS dos itens da grade (vizinhos cedendo lugar, assentamento após soltar),
    // o ponteiro pode estar parado e nenhum evento agendar alinhamento: o loop abaixo acompanha o slot animado
    // quadro a quadro até a última transição terminar, com teto de duração para nunca rodar solto.
    let animRaf=0,animCount=0,animUntil=0;
    const animLoop=()=>{align();if(animCount>0&&Date.now()<animUntil)animRaf=requestAnimationFrame(animLoop);else{animRaf=0;animCount=0;}};
    const animStart=(e:Event)=>{const t=e.target;if(!(t instanceof Element)||!t.closest('.react-grid-item'))return;animCount++;animUntil=Date.now()+1700;if(animRaf===0)animRaf=requestAnimationFrame(animLoop);};
    const animStop=()=>{animCount=Math.max(0,animCount-1);};
    window.addEventListener('scroll',schedule,true);window.addEventListener('resize',schedule);window.addEventListener('pointermove',schedule,true);window.addEventListener(CHANGE,schedule);
    window.addEventListener('transitionrun',animStart,true);window.addEventListener('transitionstart',animStart,true);window.addEventListener('transitionend',animStop,true);window.addEventListener('transitioncancel',animStop,true);
    return()=>{window.removeEventListener('scroll',schedule,true);window.removeEventListener('resize',schedule);window.removeEventListener('pointermove',schedule,true);window.removeEventListener(CHANGE,schedule);
      window.removeEventListener('transitionrun',animStart,true);window.removeEventListener('transitionstart',animStart,true);window.removeEventListener('transitionend',animStop,true);window.removeEventListener('transitioncancel',animStop,true);
      if(animRaf!==0)cancelAnimationFrame(animRaf);
      if(frame.current!==null){cancelAnimationFrame(frame.current);frame.current=null;}};
  },[work,schedule,align]);
  return documentLayer(<>{bodies.map(body=>{const box=rects[body.key];return <div key={body.key} className={`workspace-fixed-home-body home-panel-body kind-${body.kind} ${body.report?'is-report':''}`} data-home-body-key={body.key} data-cf-project={body.project} data-cf-module={body.module} data-ready={body.ready?'':undefined} hidden={!box} style={box?{left:box.left,top:box.top,width:box.width,height:box.height,clipPath:box.clip}:undefined}>{body.content}</div>;})}</>);
}
type Rect={left:number;top:number;width:number;height:number;clip:string};
function bounds(node:HTMLElement):Rect|null{
  if(!shown(node))return null;
  const r=node.getBoundingClientRect();if(r.width<=0||r.height<=0)return null;
  // Viewport clipping belongs to the browser. Baking it into a fixed overlay made
  // the content wait for JS/React to catch up with every document scroll.
  let l=r.left,t=r.top,right=r.right,bottom=r.bottom;
  for(let p=node.parentElement;p&&p!==document.body;p=p.parentElement){const s=getComputedStyle(p),b=p.getBoundingClientRect();
    if(/hidden|auto|scroll|clip/.test(s.overflowX)){l=Math.max(l,b.left);right=Math.min(right,b.right);}
    if(/hidden|auto|scroll|clip/.test(s.overflowY)){t=Math.max(t,b.top);bottom=Math.min(bottom,b.bottom);}
  }
  if(right<=l||bottom<=t)return null;
  return {left:r.left+window.scrollX,top:r.top+window.scrollY,width:r.width,height:r.height,clip:`inset(${Math.max(0,t-r.top)}px ${Math.max(0,r.right-right)}px ${Math.max(0,r.bottom-bottom)}px ${Math.max(0,l-r.left)}px)`};
}

/**
 * Relatórios fixados vivem sempre no mesmo nó do DOM: só a posição/visibilidade muda.
 * O iframe nunca é reparentado (appendChild pode recarregar o browsing context).
 * Cada esteira usa um único portal/container por pid; mover o formulário conserva seu estado React.
 */
export default function WorkspaceEditors({reports,reportOwners,routingOwners,renderReport,onError,onSaved,epoch}:{reports:Preview[];reportOwners:Map<string,'home'|'main'>;routingOwners:Map<string,string>;renderReport:(p:Preview)=>ReactNode;onError:(e:unknown)=>void;onSaved:(s:string)=>void;epoch:unknown}){
  const parking=useRef<HTMLDivElement>(null);
  const routeNodes=useRef(new Map<string,HTMLDivElement>());
  const [routes,setRoutes]=useState<string[]>([]),[mountedReports,setMountedReports]=useState<string[]>([]),[rects,setRects]=useState<Record<string,Rect>>({});
  const latest=useRef({reports,reportOwners,routingOwners});latest.current={reports,reportOwners,routingOwners};
  const frame=useRef<number|null>(null);
  const align=useCallback(()=>{
    const data=latest.current;
    const slots=Array.from(document.querySelectorAll<HTMLElement>('[data-routing-editor-slot]'));
    const pids=[...new Set(slots.map(s=>s.dataset.routingEditorSlot!).filter(Boolean))];
    setRoutes(prev=>pids.some(p=>!prev.includes(p))?[...prev,...pids.filter(p=>!prev.includes(p))]:prev);
    for(const pid of pids){
      const candidates=slots.filter(s=>s.dataset.routingEditorSlot===pid),preferred=data.routingOwners.get(pid);
      const target=candidates.find(s=>s.dataset.editorHost===preferred&&shown(s))||candidates.find(shown);
      let node=routeNodes.current.get(pid);if(!node){node=document.createElement('div');node.className='workspace-routing-editor';routeNodes.current.set(pid,node);}
      for(const slot of candidates)slot.toggleAttribute('data-editor-active',slot===target);
      const parent=target||parking.current;if(parent&&node.parentElement!==parent)parent.appendChild(node);
    }
    // Closing the last slot parks its container without unmounting the editor.
    for(const [pid,node] of routeNodes.current)if(!pids.includes(pid)&&parking.current&&node.parentElement!==parking.current)parking.current.appendChild(node);
    const positions:Record<string,Rect>={};const found:string[]=[];
    for(const item of data.reports){const key=reportKey(item),owner=data.reportOwners.get(key);
      const candidates=Array.from(document.querySelectorAll<HTMLElement>(`[data-report-editor-slot="${CSS.escape(key)}"]`));
      const target=candidates.find(s=>s.dataset.editorHost===owner&&shown(s))||candidates.find(shown);
      if(target){const box=bounds(target);if(box)positions[key]=box;found.push(key);}
    }
    setMountedReports(prev=>found.some(k=>!prev.includes(k))?[...prev,...found.filter(k=>!prev.includes(k))]:prev);
    setRects(prev=>JSON.stringify(prev)===JSON.stringify(positions)?prev:positions);
  },[]);
  const schedule=useCallback(()=>{if(frame.current===null)frame.current=requestAnimationFrame(()=>{frame.current=null;align();});},[align]);
  useLayoutEffect(()=>{align();},[reports,reportOwners,routingOwners,epoch,align]);
  useEffect(()=>{window.addEventListener(CHANGE,schedule);return()=>window.removeEventListener(CHANGE,schedule);},[schedule]);
  const work=reports.length>0||routes.length>0;
  useEffect(()=>{if(!work)return;window.addEventListener('scroll',schedule,true);window.addEventListener('resize',schedule);window.addEventListener('pointermove',schedule,true);
    return()=>{window.removeEventListener('scroll',schedule,true);window.removeEventListener('resize',schedule);window.removeEventListener('pointermove',schedule,true);if(frame.current!==null){cancelAnimationFrame(frame.current);frame.current=null;}};
  },[work,schedule]);
  // Só logout/desmonte libera containers; ocultar/fechar um slot mantém rascunho e revisão.
  useEffect(()=>()=>{if(frame.current!==null)cancelAnimationFrame(frame.current);for(const node of routeNodes.current.values())node.remove();routeNodes.current.clear();},[]);
  const present=new Set(reports.map(reportKey));
  return <><div className="workspace-editor-parking" ref={parking} hidden/>{routes.map(pid=>{const node=routeNodes.current.get(pid);return node?createPortal(<RoutingEditor pid={pid} onError={onError} onSaved={onSaved}/>,node,`routing:${pid}`):null;})}{documentLayer(<>{mountedReports.filter(k=>present.has(k)).map(key=>{const item=reports.find(p=>reportKey(p)===key),box=rects[key];if(!item)return null;
    return <div key={key} data-fixed-report-editor={key} data-cf-project={item.project_id} className="workspace-fixed-report" hidden={!box} style={box?{left:box.left,top:box.top,width:box.width,height:box.height,clipPath:box.clip}:undefined}>{renderReport(item)}</div>;
  })}</>)}</>;
}
