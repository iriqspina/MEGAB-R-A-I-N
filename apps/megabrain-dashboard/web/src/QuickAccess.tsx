import {useEffect,useRef,useState} from 'react';
import {Activity,ChevronDown,Settings2,Smartphone,Workflow,type LucideIcon} from 'lucide-react';
import './quota-access.css';
export type QuickAction={id:string;label:string;description:string;icon?:LucideIcon;onClick:()=>void};

export default function QuickAccess({actions,onSettings}:{actions:QuickAction[];onSettings:()=>void}){
  const [open,setOpen]=useState(false);const root=useRef<HTMLDivElement>(null);const trigger=useRef<HTMLButtonElement>(null);const timer=useRef<ReturnType<typeof setTimeout>|null>(null);const dismissed=useRef(false);
  const clear=()=>{if(timer.current)clearTimeout(timer.current);timer.current=null;};
  const hide=()=>{clear();setOpen(false);};
  useEffect(()=>{const outside=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))hide();};const key=(e:KeyboardEvent)=>{if(e.key==='Escape'&&open){e.preventDefault();e.stopPropagation();dismissed.current=true;hide();trigger.current?.focus();}};document.addEventListener('pointerdown',outside);document.addEventListener('keydown',key);return()=>{clear();document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',key);};},[open]);
  const enter=(pointer:string)=>{clear();if(pointer!=='mouse'||dismissed.current)return;timer.current=setTimeout(()=>setOpen(true),350);};
  const leave=()=>{clear();dismissed.current=false;if(root.current?.contains(document.activeElement))return;timer.current=setTimeout(()=>setOpen(false),250);};
  return <div className="quick-access" ref={root} onPointerEnter={e=>enter(e.pointerType)} onPointerLeave={leave} onFocus={e=>{if(!dismissed.current&&(e.target as HTMLElement).matches(':focus-visible')){clear();setOpen(true);}}} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget as Node)){dismissed.current=false;hide();}}}>
    <button ref={trigger} className="quick-trigger" aria-label="Acessos rápidos e configurações" aria-expanded={open} aria-controls="quick-access-options" onClick={e=>{dismissed.current=false;clear();if(e.detail===0){setOpen(true);requestAnimationFrame(()=>root.current?.querySelector<HTMLButtonElement>('.quick-options button')?.focus());}else setOpen(!open);}} onKeyDown={e=>{if(e.key==='ArrowDown'){e.preventDefault();setOpen(true);requestAnimationFrame(()=>root.current?.querySelector<HTMLButtonElement>('.quick-options button')?.focus());}}}><Settings2 size={18}/><span>Acessos</span><ChevronDown size={14}/></button>
    {open&&<nav id="quick-access-options" className="quick-options" aria-label="Acessos rápidos"><strong>Chegue direto</strong>{actions.map(action=>{const Icon=action.icon||({quotas:Activity,process:Workflow,phone:Smartphone}[action.id]||Settings2);return <button key={action.id} onClick={()=>{hide();action.onClick();}}><Icon size={18}/><span>{action.label}<small>{action.description}</small></span></button>;})}<button onClick={()=>{hide();onSettings();}}><Settings2 size={18}/><span>Todas as configurações<small>Opções da central, em um lugar</small></span></button></nav>}
  </div>;
}
