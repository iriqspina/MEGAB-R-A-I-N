import {useEffect,useLayoutEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import {createPortal} from 'react-dom';
import {Check,Palette,RotateCcw,X} from 'lucide-react';
import {colorRows,PALETTE,setColor,validColor,type ColorRow} from './appearance-state';
import {readPanels,splitRendered} from './home-state';
import type {Project,Workspace} from './types';
import './color-menu.css';

type Update=(fn:(w:Workspace)=>Workspace)=>void;
type Pick=(key:string,color:string|null)=>void;

/** 261016: todas as cores num menu só, no alto. Grava em ws.appearance, o mesmo documento que guarda as posições.
 *  O painel vai para o body: a barra do topo tem backdrop-filter no celular e prenderia um position:fixed. */
export default function ColorMenu({ws,update,projects,responseKeys}:{ws:Workspace;update:Update;projects:Project[];responseKeys:Set<string>}){
  const [open,setOpen]=useState(false);const [all,setAll]=useState(false);const [pos,setPos]=useState<{top:number;right:number}|null>(null);
  const wrap=useRef<HTMLDivElement>(null);const panel=useRef<HTMLElement>(null);const button=useRef<HTMLButtonElement>(null);
  const close=(focus=true)=>{setOpen(false);if(focus)button.current?.focus();};
  useLayoutEffect(()=>{if(!open)return;const place=()=>{const r=button.current?.getBoundingClientRect();if(r)setPos({top:Math.round(r.bottom+8),right:Math.max(12,Math.round(window.innerWidth-r.right))});};place();window.addEventListener('resize',place);return()=>window.removeEventListener('resize',place);},[open]);
  useEffect(()=>{if(!open)return;
    const inside=(t:EventTarget|null)=>t instanceof Node&&(Boolean(wrap.current?.contains(t))||Boolean(panel.current?.contains(t)));
    // Esc só fecha quando o foco está no menu (ou solto na página), não quando é de outra janela aberta.
    const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'&&!e.defaultPrevented&&(inside(document.activeElement)||document.activeElement===document.body))close();};
    const outside=(e:PointerEvent)=>{if(!inside(e.target))close(false);};
    document.addEventListener('keydown',escape);document.addEventListener('pointerdown',outside);return()=>{document.removeEventListener('keydown',escape);document.removeEventListener('pointerdown',outside);};},[open]);
  const rows=useMemo(()=>open?colorRows(ws,projects,splitRendered(readPanels(ws),responseKeys).shown):null,[open,ws,projects,responseKeys]);
  const pick:Pick=(key,color)=>update(w=>setColor(w,key,color));
  return <div className="color-menu" ref={wrap} data-cf-ignorar>
    <button ref={button} className="secondary color-menu-trigger" aria-expanded={open} aria-controls={open?'color-menu-panel':undefined} title="Escolher as cores de projetos, quadros e seções" onClick={()=>setOpen(!open)}><Palette size={17}/><span>Cores</span></button>
    {open&&rows&&pos&&createPortal(<section ref={panel} id="color-menu-panel" className="color-menu-panel" aria-label="Cores do painel" data-cf-ignorar style={{top:pos.top,right:pos.right,maxHeight:`calc(100dvh - ${pos.top+12}px)`}}>
      <header><div><strong>Cores</strong><small>Clique numa cor ou no arco-íris para escolher qualquer outra. Marcado é o que você escolheu; sem marca vale o padrão. Fica salvo no painel, junto com a posição de cada quadro.</small></div><button type="button" aria-label="Fechar cores" onClick={()=>close()}><X size={18}/></button></header>
      <ColorGroup title="Tipos de quadro" note="Vale para esse tipo em todos os projetos. Um quadro com cor própria mantém a dele." rows={rows.types} pick={pick}/>
      <ColorGroup title="Projetos" note="Moldura do quadro do projeto, aba e cartões do catálogo." rows={all?[...rows.featured,...rows.others]:rows.featured} pick={pick} empty="Nenhum projeto na mesa. Use “Mostrar todos”."/>
      {rows.others.length>0&&<button type="button" className="text-button color-menu-more" aria-expanded={all} onClick={()=>setAll(!all)}>{all?'Mostrar só os da mesa':`Mostrar todos os projetos (${rows.featured.length+rows.others.length})`}</button>}
      {rows.desk.length>0&&<ColorGroup title="Quadros abertos na mesa" note="Cor só deste quadro." rows={rows.desk} pick={pick}/>}
    </section>,document.body)}
  </div>;
}

function ColorGroup({title,note,rows,pick,empty}:{title:string;note:string;rows:ColorRow[];pick:Pick;empty?:string}){
  return <fieldset className="color-group"><legend>{title}</legend><p>{rows.length?note:(empty||note)}</p>{rows.length>0&&<ul>{rows.map(r=><ColorLine key={r.key} row={r} pick={pick}/>)}</ul>}</fieldset>;
}

/** O seletor nativo dispara a cada movimento: a cor livre grava quando assenta (350 ms), é gravada ao fechar
 *  e é descartada se outra escolha da mesma linha chegar antes. */
function ColorLine({row,pick}:{row:ColorRow;pick:Pick}){
  const [draft,setDraft]=useState<string|null>(null);const timer=useRef<ReturnType<typeof setTimeout>>(undefined);const pending=useRef<string|null>(null);
  const latest=useRef(pick);latest.current=pick;
  useEffect(()=>()=>{clearTimeout(timer.current);if(pending.current)latest.current(row.key,pending.current);},[row.key]);
  const commit=(color:string|null)=>{clearTimeout(timer.current);pending.current=null;setDraft(null);latest.current(row.key,color);};
  const settle=(color:string)=>{pending.current=color;setDraft(color);clearTimeout(timer.current);timer.current=setTimeout(()=>commit(color),350);};
  const shown=draft||row.color;const chosen=Boolean(draft)||row.own;const custom=chosen&&!PALETTE.some(p=>p.color===shown);
  return <li style={{'--row-color':shown} as CSSProperties}>
    <span className="color-row-name"><i aria-hidden="true"/><span><strong>{row.label}</strong>{row.hint&&<small>{row.hint}</small>}</span></span>
    <span className="color-row-choices">
      {PALETTE.map(p=>{const on=chosen&&shown===p.color;return <button key={p.color} type="button" className="color-dot" style={{'--choice':p.color} as CSSProperties} aria-label={`${row.label}: ${p.name}`} aria-pressed={on} title={p.name} onClick={()=>commit(p.color)}>{on&&<Check size={13} strokeWidth={3}/>}</button>;})}
      <label className={`color-custom ${custom?'is-custom':''}`} style={{'--custom':validColor(shown)||'#ff82c4'} as CSSProperties} title="Escolher qualquer cor"><input type="color" aria-label={`${row.label}: escolher qualquer cor`} value={validColor(shown)||'#ff82c4'} onChange={e=>settle(e.target.value.toLowerCase())}/></label>
      {row.own||draft?<button type="button" className="icon-button color-reset" aria-label={`${row.label}: voltar à cor padrão`} title="Voltar à cor padrão" onClick={()=>commit(null)}><RotateCcw size={14}/></button>:<span className="color-reset-slot" aria-hidden="true"/>}
    </span>
  </li>;
}
