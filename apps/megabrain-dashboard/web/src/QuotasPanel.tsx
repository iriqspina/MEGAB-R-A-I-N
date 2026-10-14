import {useEffect,useState} from 'react';
import {Activity,Clock3,Computer,Info,LoaderCircle,RefreshCw,Settings2,ShieldCheck} from 'lucide-react';
import {api} from './api';
import './quota-access.css';

type Window={id:string;label:string;period:string;used_percent:number|null;remaining_percent:number|null;resets_at:string|null};
type Account={id:string;label:string;observed_at:string|null;age_seconds:number|null;fresh:boolean;source:string;windows:Window[]};
type Quotas={observed_at:string;freshness_seconds:number;accounts:Account[];notice:string;local_controls:boolean};
const date=(value:string|null)=>value&&Number.isFinite(+new Date(value))?new Date(value).toLocaleString('pt-BR'):'Não informado';
const percent=(value:number|null)=>value===null?'—':`${value.toLocaleString('pt-BR',{maximumFractionDigits:1})}%`;

export default function QuotasPanel({onError,onSaved}:{onError?:(e:unknown)=>void;onSaved?:(message:string)=>void}){
  const [data,setData]=useState<Quotas|null>(null),[busy,setBusy]=useState(false),[opening,setOpening]=useState(false),[error,setError]=useState('');
  const [clock,setClock]=useState(Date.now());
  async function load(){setBusy(true);setError('');try{setData(await api<Quotas>('/quotas'));}catch(e){setError((e as Error).message);onError?.(e);}finally{setBusy(false);}}
  useEffect(()=>{void load();},[]);
  useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(timer);},[]);
  const fresh=(account:Account)=>account.fresh&&account.observed_at&&data?((clock-new Date(data.observed_at).getTime())/1000+(account.age_seconds||0)<=data.freshness_seconds):false;
  async function widget(action:'show'|'settings',tab=1){if(opening)return;setOpening(true);setError('');try{const r=await api<{message:string}>('/quotas/open-widget','POST',{action,tab});onSaved?.(r.message);}catch(e){setError((e as Error).message);onError?.(e);}finally{setOpening(false);}}
  return <section className="quota-panel" aria-label="Cotas das contas de IA">
    <p className="quota-intro"><ShieldCheck size={18}/> Suas contas e períodos, com a data da leitura. O consumo pertence à conta inteira.</p>
    <div className="quota-tools"><button className="secondary" disabled={busy} onClick={()=>void load()}>{busy?<LoaderCircle size={17} className="spin"/>:<RefreshCw size={17}/>}Reler fontes locais</button>{data?.local_controls&&<><button className="secondary" disabled={opening} onClick={()=>void widget('show')}><Computer size={17}/>Widget no computador</button><button className="primary" disabled={opening} onClick={()=>void widget('settings')}><Settings2 size={17}/>Configurar widget</button></>}</div>
    {data?.local_controls&&<nav className="quota-tools quota-setting-categories" aria-label="Categorias de configuração do widget">{['Texto','Aparência','Números','Janela','Provedores'].map((label,tab)=><button className="secondary" key={label} disabled={opening} onClick={()=>void widget('settings',tab)}><Settings2 size={16}/>{label}</button>)}</nav>}
    {error&&<p role="alert" className="error-message">{error}</p>}
    {!data&&busy&&<p role="status"><LoaderCircle size={17} className="spin"/>Lendo as fontes de cotas…</p>}
    {data&&<><div className="quota-account-grid">{data.accounts.map(account=><article className="quota-account" key={account.id}>
      <header><h3><Activity size={18}/>{account.label}</h3><span className={fresh(account)?'quota-fresh':'quota-stale'}>{fresh(account)?'Leitura recente':account.windows.some(w=>w.used_percent!==null)?'Leitura antiga':'Não medido'}</span></header>
      {account.windows.length?account.windows.map(w=><div className="quota-window" key={w.id}>
        <div className="quota-window-title"><strong>{w.period}</strong><small>{w.label}</small></div>
        <div className="quota-values"><span><b>{percent(w.remaining_percent)}</b> disponível</span><span>{percent(w.used_percent)} usado</span></div>
        {w.used_percent!==null&&<div className="quota-meter" role="meter" aria-label={`${account.label}, ${w.period}, consumo`} aria-valuenow={w.used_percent} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${w.used_percent}%`}}/></div>}
        <p className="quota-meta"><Clock3 size={14}/>Renova: {date(w.resets_at)}</p>
      </div>):<p className="quota-unavailable"><Info size={16}/>Sem janela medida nesta fonte.</p>}
      <footer><span><Clock3 size={14}/>Leitura: {date(account.observed_at)}</span><small>{account.source}</small></footer>
    </article>)}</div><p className="quota-notice"><Info size={17}/>{data.notice} Leitura recente: até {data.freshness_seconds} segundos, critério local.</p>{!data.local_controls&&<p className="quota-notice"><Computer size={17}/>Você pode consultar as cotas aqui. A configuração da janela do widget fica no aplicativo do computador.</p>}</>}
  </section>;
}
