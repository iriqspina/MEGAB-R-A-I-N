import {useEffect,useRef,useState,type CSSProperties} from 'react';
import {createPortal} from 'react-dom';
import {Check,Copy,Palette,RotateCcw,X} from 'lucide-react';
import {inheritedLook,PALETTE,readAppearance,setAppearance,validColor} from './appearance-state';
import type {Workspace} from './types';
import './appearance.css';

type Props={scopeKey:string;title:string;color?:string;ws:Workspace;update:(fn:(w:Workspace)=>Workspace)=>void;applyFormat?:()=>void;formatCount?:number;formatLabel?:string};
export default function AppearanceControl(props:Props){
  const [open,setOpen]=useState(false);
  return <><button className="icon-button appearance-button" type="button" aria-label={`Personalizar ${props.title}`} title="Nome, emoji, cor e formato" onClick={()=>setOpen(true)}><Palette size={16}/></button>{open&&createPortal(<AppearanceDialog {...props} close={()=>setOpen(false)}/>,document.body)}</>;
}
function AppearanceDialog({scopeKey,title,color,ws,update,applyFormat,formatCount=0,formatLabel='painéis visíveis',close}:Props&{close:()=>void}){
  const ref=useRef<HTMLDialogElement>(null);const saved=readAppearance(ws,scopeKey);const defaults=inheritedLook(ws,scopeKey,title,color);
  const [name,setName]=useState(saved.name||'');const [emoji,setEmoji]=useState(saved.emoji||'');const [chosen,setChosen]=useState(saved.color||'');
  useEffect(()=>{ref.current?.showModal();},[]);
  return <dialog ref={ref} className="appearance-dialog" aria-labelledby="appearance-title" onCancel={close} onClose={close} data-cf-ignorar>
    <form onSubmit={e=>{e.preventDefault();update(w=>setAppearance(w,scopeKey,{name,emoji,color:chosen||undefined}));close();}}>
      <header><div><small>Organizar meu espaço</small><h2 id="appearance-title">Nome, emoji e cor</h2></div><button type="button" className="icon-button" aria-label="Fechar personalização" onClick={close}><X size={18}/></button></header>
      <div className="appearance-preview" style={{'--panel-accent':chosen||defaults.color} as CSSProperties}><span>{emoji||'✦'}</span><strong>{name.trim()||title}</strong></div>
      <label>Nome no painel<input autoFocus value={name} placeholder={title} maxLength={90} onChange={e=>setName(e.target.value)}/></label>
      <label>Emoji ou símbolo<input value={emoji} placeholder="Ex.: 🎨" maxLength={16} onChange={e=>setEmoji(e.target.value)}/></label>
      <div className="emoji-choices" aria-label="Sugestões de emoji">{['🎨','🧠','📁','💡','🚀','📌','🛠️','🎵'].map(e=><button type="button" key={e} aria-label={`Usar emoji ${e}`} onClick={()=>setEmoji(e)}>{e}</button>)}<button type="button" onClick={()=>setEmoji('')}>Sem emoji</button></div>
      <fieldset><legend>Cor da identidade visual</legend><div className="appearance-colors">{PALETTE.map(p=><button type="button" key={p.color} title={p.name} aria-label={`Cor ${p.name}`} aria-pressed={(chosen||defaults.color)===p.color} style={{'--choice':p.color} as CSSProperties} onClick={()=>setChosen(p.color)}>{(chosen||defaults.color)===p.color&&<Check size={14}/>}<span>{p.name}</span></button>)}<label className="appearance-custom" title="Escolher qualquer cor"><span>Outra cor</span><input type="color" aria-label="Escolher qualquer cor" value={validColor(chosen||defaults.color)||'#ff82c4'} onChange={e=>setChosen(e.target.value.toLowerCase())}/></label></div></fieldset>
      <p className="appearance-hint">O nome muda aqui na central. Arquivos e fontes mantêm sua identidade.</p>
      {applyFormat&&<section className="appearance-format"><strong>Mesmo formato nesta área</strong><p>Usar a largura e a altura deste painel nos outros {formatCount} {formatLabel}. A disposição desta tela será reorganizada.</p><button type="button" className="secondary" disabled={!formatCount} onClick={()=>{applyFormat();close();}}><Copy size={15}/>Aplicar formato aos demais</button></section>}
      <footer><button type="button" className="text-button" onClick={()=>{update(w=>setAppearance(w,scopeKey,null));close();}}><RotateCcw size={14}/>Restaurar aparência</button><button type="submit" className="primary"><Check size={15}/>Salvar aparência</button></footer>
    </form>
  </dialog>;
}
