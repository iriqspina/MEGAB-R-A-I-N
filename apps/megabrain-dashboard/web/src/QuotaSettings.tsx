import {useEffect,useRef,useState} from 'react';
import {ArrowDown,ArrowUp,CheckCircle2,Info,LoaderCircle,RefreshCw,Save,Settings2} from 'lucide-react';
import {api} from './api';
import './quota-settings.css';

type Values=Record<string,unknown>;
type Config={revision:string;values:Values;contract_version:number;schema:{choices:Record<string,(string|number)[]>;ranges:Record<string,[number,number]>;booleans:string[];providers:Record<string,string>}};
type Receipt={request_id:string;status:string;message:string;revision?:string;values?:Values;changed_since_apply?:boolean};
const categories=['Texto','Aparência','Números','Janela','Provedores'];
const fields=[['font_family','size_name','size_value','size_hint','size_detail','scale'],['surface_preset','bg_opacity_percent','expanded','show_pacing','show_footer','hover_mode'],['number_mode','reset_mode','poll_minutes','alert_percent'],['visual_mode','strip_height','strip_width','layout','always_on_top','lock_position','click_through','snap_edges']];
const labels:Record<string,string>={font_family:'Fonte',size_name:'Nome da conta · px',size_value:'Número grande · px',size_hint:'Informações breves · px',size_detail:'Detalhes · px',scale:'Escala geral',surface_preset:'Cor de fundo',bg_opacity_percent:'Opacidade do fundo · %',expanded:'Mostrar detalhes',show_pacing:'Mostrar ritmo de uso',show_footer:'Mostrar rodapé',hover_mode:'Ao passar o mouse',number_mode:'Número grande',reset_mode:'Renovação',poll_minutes:'Intervalo entre consultas',alert_percent:'Aviso de consumo na bandeja',visual_mode:'Formato',strip_height:'Altura da faixa · px',strip_width:'Largura da faixa · px',layout:'Direção dos cards',always_on_top:'Sempre acima das outras janelas',lock_position:'Travar posição e tamanho',click_through:'Atravessar cliques',snap_edges:'Grudar nas bordas da tela'};
const options:Record<string,string>={legacy:'Cards',trilho:'Faixa',used:'Percentual usado',remaining:'Percentual disponível',relative:'Tempo até renovar',absolute:'Dia e hora',none:'Sem mudança',opaque:'Fundo sólido',fade:'Ficar transparente',horizontal:'Horizontal',vertical:'Vertical',carvao:'Carvão',meia_noite:'Meia-noite',ameixa:'Ameixa',musgo:'Musgo',telha:'Telha',nevoa:'Névoa',papel:'Papel'};
const colors:Record<string,string>={carvao:'#18191d',meia_noite:'#121b30',ameixa:'#30203c',musgo:'#1b3029',telha:'#38221f',nevoa:'#414858',papel:'#eee9e0'};

export default function QuotaSettings({initialTab=0,onError,onSaved}:{initialTab?:number;onError?:(e:unknown)=>void;onSaved?:(message:string)=>void}){
 const [data,setData]=useState<Config|null>(null),[changes,setChanges]=useState<Values>({}),[tab,setTab]=useState(initialTab),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 const mounted=useRef(true),sending=useRef(false);
 async function load(){setBusy(true);setError('');try{const next=await api<Config>('/quotas/widget-settings');if(mounted.current){setData(next);setChanges({});}}catch(e){if(mounted.current)setError((e as Error).message);onError?.(e);}finally{if(mounted.current)setBusy(false);}}
 useEffect(()=>{mounted.current=true;void load();return()=>{mounted.current=false;};},[]);
 useEffect(()=>setTab(initialTab),[initialTab]);
 const values={...(data?.values||{}),...changes};
 function change(key:string,value:unknown){setChanges(old=>({...old,[key]:value}));setMessage('');}
 function optionLabel(key:string,value:string|number){if(key==='scale')return `${Math.round(Number(value)*100)}%`;if(key==='poll_minutes')return `${value} minutos`;if(key==='alert_percent')return value===0?'Desligado':`${value}% usado`;return options[String(value)]||String(value);}
 async function save(){
  if(!data||sending.current||!Object.keys(changes).length)return;
  sending.current=true;setBusy(true);setError('');setMessage('Enviando ao widget…');
  try{
   const request=await api<Receipt>('/quotas/widget-settings','POST',{changes,expected_revision:data.revision},crypto.randomUUID());
   let receipt=request;
   for(let i=0;i<22&&receipt.status==='requested';i++){
    if(!mounted.current)return;
    await new Promise(resolve=>setTimeout(resolve,1000));
    receipt=await api<Receipt>(`/quotas/widget-settings/requests/${request.request_id}`);
   }
   if(!mounted.current)return;
   if(receipt.status!=='applied'&&receipt.status!=='adjusted')throw new Error(receipt.message||'O widget não confirmou a aplicação.');
   const current=await api<Config>('/quotas/widget-settings');
   setData(current);setChanges({});
   const note=receipt.changed_since_apply?'Aplicado; outra alteração posterior também foi carregada.':receipt.message;
   setMessage(note);onSaved?.(note);
  }catch(e){if(mounted.current){setError((e as Error).message);setMessage('');}onError?.(e);}
  finally{sending.current=false;if(mounted.current)setBusy(false);}
 }
 const providerValues={...(data?.values.visible_providers as Record<string,boolean>||{}),...(changes.visible_providers as Record<string,boolean>||{})};
 const known=Object.keys(data?.schema.providers||{});
 const order=[...((values.provider_order as string[]|undefined)||[]).filter(p=>known.includes(p)),...known.filter(p=>!((values.provider_order as string[]|undefined)||[]).includes(p))];
 function moveProvider(i:number,delta:number){const next=[...order];[next[i],next[i+delta]]=[next[i+delta],next[i]];change('provider_order',next);}
 return <section className="quota-settings" aria-label="Configurações do Cotas IA dentro do MegaBrain">
  <header><h3><Settings2 size={19}/>Configurar Cotas IA</h3><p>Altere aqui. O widget confirma quando a mudança está aplicada.</p></header>
  <nav className="quota-settings-tabs" aria-label="Categorias do Cotas IA">{categories.map((name,i)=><button type="button" key={name} aria-pressed={tab===i} onClick={()=>setTab(i)}>{name}</button>)}</nav>
  {!data&&busy&&<p role="status"><LoaderCircle className="spin" size={18}/>Lendo configurações…</p>}
  {data&&<>
   <div className="quota-settings-preview" style={{background:colors[String(values.surface_preset)]||'#18191d',color:values.surface_preset==='papel'?'#24212b':'#f6f0fa',fontFamily:String(values.font_family)}}><span>Esboço de aparência · dados de exemplo</span><strong style={{fontSize:Math.min(Number(values.size_value)||19,36)}}>Cotas IA <b>57%</b></strong><small>O desenho final é confirmado na janela do widget.</small></div>
   {tab<4?<div className="quota-settings-grid">{fields[tab].map(key=>{
    const choices=data.schema.choices[key],range=data.schema.ranges[key],value=values[key];
    if(data.schema.booleans.includes(key))return <label className="quota-check" key={key}><input type="checkbox" checked={Boolean(value)} disabled={busy} onChange={e=>change(key,e.target.checked)}/><span>{labels[key]}</span></label>;
    return <label key={key}><span>{labels[key]}</span>{choices?<select aria-label={labels[key]} disabled={busy} value={String(value)} onChange={e=>change(key,typeof choices[0]==='number'?Number(e.target.value):e.target.value)}>{!choices.includes(value as string|number)&&<option value={String(value)}>Atual · {String(value)}</option>}{choices.map(v=><option value={String(v)} key={v}>{optionLabel(key,v)}</option>)}</select>:<input aria-label={labels[key]} type="number" disabled={busy} min={range?.[0]} max={range?.[1]} step={1} value={Number.isFinite(Number(value))?String(value):''} onChange={e=>change(key,e.target.value===''?'':Number(e.target.value))}/>}</label>;
   })}</div>:<div className="quota-provider-settings"><p><Info size={16}/>Escolha o que aparece. Contas e conexões permanecem nas configurações próprias de cada serviço.</p>{order.map((id,i)=><div className="quota-provider-row" key={id}><label><input type="checkbox" disabled={busy} checked={providerValues?.[id]!==false} onChange={e=>change('visible_providers',{...(changes.visible_providers as Record<string,boolean>||{}),[id]:e.target.checked})}/>{data.schema.providers[id]}</label><button type="button" disabled={busy||i===0} aria-label={`Subir ${data.schema.providers[id]}`} onClick={()=>moveProvider(i,-1)}><ArrowUp size={17}/></button><button type="button" disabled={busy||i===order.length-1} aria-label={`Descer ${data.schema.providers[id]}`} onClick={()=>moveProvider(i,1)}><ArrowDown size={17}/></button></div>)}</div>}
   {tab===3&&<><button type="button" className="secondary" disabled={busy} onClick={()=>{setChanges(old=>({...old,window_width:null,window_height:null,strip_width:800}));setMessage('');}}>Ajustar tamanho ao conteúdo</button><p className="quota-settings-help"><Info size={16}/>Se ativar “Atravessar cliques”, recupere o mouse aqui ou pelo ícone Cotas IA na bandeja do Windows. Posição e tamanho atuais são preservados até você mudá-los.</p></>}
   {tab===2&&<p className="quota-settings-help"><Info size={16}/>O intervalo mínimo é de 2 minutos. Alterar a frequência não muda o saldo disponível.</p>}
  </>}
  {error&&<p role="alert" className="error-message">{error}</p>}
  {message&&<p role="status" className="quota-settings-status">{busy?<LoaderCircle className="spin" size={18}/>:<CheckCircle2 size={18}/>} {message}</p>}
  <footer><button className="primary" disabled={!data||busy||!Object.keys(changes).length} onClick={()=>void save()}>{busy?<LoaderCircle className="spin" size={17}/>:<Save size={17}/>}Aplicar no widget</button><button className="secondary" disabled={busy} onClick={()=>{setChanges({});setMessage('');void load();}}><RefreshCw size={17}/>Reler configuração</button>{Object.keys(changes).length>0&&<small>Alterações ainda não aplicadas.</small>}</footer>
 </section>;
}
