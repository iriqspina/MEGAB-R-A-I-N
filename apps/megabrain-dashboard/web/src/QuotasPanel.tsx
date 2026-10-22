import {useEffect,useState} from 'react';
import {Activity,Clock3,Computer,Info,LoaderCircle,RefreshCw,Settings2,ShieldCheck} from 'lucide-react';
import {api} from './api';
import './quota-access.css';
import QuotaSettings from './QuotaSettings';

type Window={id:string;label:string;period:string;used_percent:number|null;remaining_percent:number|null;resets_at:string|null};
type Account={id:string;label:string;observed_at:string|null;age_seconds:number|null;fresh:boolean;source:string;windows:Window[];details_observed_at?:string|null;details?:{financial?:{title:string;amount:number|null;currency:string;status:string;note:string}[];resets?:{title:string;count:number|null;usable?:boolean;expires_at?:string}[];notes?:string[];product_shares?:{name:string;percent:number}[];observed_sections?:{title:string;text:string}[]}};
type Quotas={observed_at:string;freshness_seconds:number;accounts:Account[];notice:string;local_controls:boolean};
const date=(value:string|null)=>value&&Number.isFinite(+new Date(value))?new Date(value).toLocaleString('pt-BR'):'Não informado';
const percent=(value:number|null)=>value===null?'—':`${value.toLocaleString('pt-BR',{maximumFractionDigits:1})}%`;

export default function QuotasPanel({onError,onSaved,initialSettingsTab=null,accountId='all'}:{onError?:(e:unknown)=>void;onSaved?:(message:string)=>void;initialSettingsTab?:number|null;accountId?:string}){
  const [data,setData]=useState<Quotas|null>(null),[busy,setBusy]=useState(false),[opening,setOpening]=useState(false),[error,setError]=useState('');
  const [clock,setClock]=useState(Date.now());
  const [settingsTab,setSettingsTab]=useState<number|null>(initialSettingsTab);
  useEffect(()=>setSettingsTab(initialSettingsTab),[initialSettingsTab]);
  async function load(){setBusy(true);setError('');try{setData(await api<Quotas>('/quotas'));}catch(e){setError((e as Error).message);onError?.(e);}finally{setBusy(false);}}
  useEffect(()=>{void load();},[]);
  useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(timer);},[]);
  const fresh=(account:Account)=>account.fresh&&account.observed_at&&data?((clock-new Date(data.observed_at).getTime())/1000+(account.age_seconds||0)<=data.freshness_seconds):false;
  async function widget(action:'show'|'settings',tab=1){if(opening)return;setOpening(true);setError('');try{const r=await api<{message:string}>('/quotas/open-widget','POST',{action,tab});onSaved?.(r.message);}catch(e){setError((e as Error).message);onError?.(e);}finally{setOpening(false);}}
  return <section className="quota-panel" aria-label="Cotas das contas de IA">
    <p className="quota-intro"><ShieldCheck size={18}/> Suas contas e períodos, com a data da leitura. O consumo pertence à conta inteira.</p>
    <div className="quota-tools"><button className="secondary" disabled={busy} onClick={()=>void load()}>{busy?<LoaderCircle size={17} className="spin"/>:<RefreshCw size={17}/>}Reler fontes locais</button>{data?.local_controls&&<><button className="secondary" disabled={opening} onClick={()=>void widget('show')}><Computer size={17}/>Widget no computador</button><button className="primary" aria-expanded={settingsTab!==null} onClick={()=>setSettingsTab(settingsTab===null?1:null)}><Settings2 size={17}/>{settingsTab===null?'Configurar widget aqui':'Fechar configurações'}</button></>}</div>
    {data?.local_controls&&settingsTab!==null&&<QuotaSettings initialTab={settingsTab} onError={onError} onSaved={onSaved}/>}
    {accountId!=='all'&&<p className="quota-notice"><Info size={17}/>Os detalhes desta conta ficam aqui no Brain App. O pin da faixa mantém todas as colunas do layout acima das outras janelas.</p>}
    {error&&<p role="alert" className="error-message">{error}</p>}
    {!data&&busy&&<p role="status"><LoaderCircle size={17} className="spin"/>Lendo as fontes de cotas…</p>}
    {data&&<><div className="quota-account-grid">{data.accounts.filter(account=>accountId==='all'||account.id===accountId).map(account=><article className="quota-account" key={account.id}>
      <header><h3><Activity size={18}/>{account.label}</h3><span className={fresh(account)?'quota-fresh':'quota-stale'}>{fresh(account)?'Leitura recente':account.windows.some(w=>w.used_percent!==null)?'Leitura antiga':'Não medido'}</span></header>
      {account.windows.length?account.windows.map(w=><div className="quota-window" key={w.id}>
        <div className="quota-window-title"><strong>{w.period}</strong><small>{w.label}</small></div>
        <div className="quota-values"><span><b>{percent(w.remaining_percent)}</b> disponível</span><span>{percent(w.used_percent)} usado</span></div>
        {w.used_percent!==null&&<div className="quota-meter" role="meter" aria-label={`${account.label}, ${w.period}, consumo`} aria-valuenow={w.used_percent} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${w.used_percent}%`}}/></div>}
        <p className="quota-meta"><Clock3 size={14}/>Renova: {date(w.resets_at)}</p>
      </div>):<p className="quota-unavailable"><Info size={16}/>Sem janela medida nesta fonte.</p>}
      {((account.details?.financial?.length||0)>0||(account.details?.resets?.length||0)>0)&&<details open={accountId!=='all'}><summary><Info size={16}/>Saldo, redefinições e informações da conta</summary><p className="quota-meta"><Clock3 size={14}/>Dados complementares: {date(account.details_observed_at||null)}</p>{account.details?.financial?.map((row,i)=><p className="quota-notice" key={`f${i}`}><Info size={16}/><span><strong>{row.title}: {row.status==='unlimited'?'Sem limite informado':row.amount==null?'Não informado':`${row.amount.toLocaleString('pt-BR',{maximumFractionDigits:2})} ${row.currency||''}`}</strong><br/>{row.note}</span></p>)}{account.details?.resets?.map((row,i)=><p className="quota-notice" key={`r${i}`}><RefreshCw size={16}/>{row.title}: {row.count??'—'} · {row.usable?'Disponível agora':'Sujeito à elegibilidade'}{row.expires_at?` · Validade: ${date(row.expires_at)}`:''}</p>)}{account.details?.notes?.map((note,i)=><p className="quota-notice" key={`n${i}`}><Info size={16}/>{note}</p>)}</details>}
      {!!account.details?.product_shares?.length&&<details><summary><Activity size={16}/>Participação no consumo semanal</summary>{account.details.product_shares.map((share,i)=><p className="quota-notice" key={i}><Activity size={16}/>{share.name}: {percent(share.percent)} do consumo · não é saldo de cota.</p>)}</details>}
      {!!account.details?.observed_sections?.length&&<details open={accountId!=='all'}><summary><Info size={16}/>Verificações no navegador e prints anteriores</summary>{account.details.observed_sections.map((section,i)=><div key={i}><p className="quota-notice"><Info size={16}/><strong>{section.title}</strong></p><p className="quota-meta" style={{whiteSpace:'pre-line'}}>{section.text}</p></div>)}</details>}
      {account.id==='codex_gpt2'&&<p className="quota-notice"><Info size={17}/>Esta é a segunda conta do Codex. As janelas e o saldo pertencem a essa conta. A sessão do navegador pode estar conectada à conta principal; confira a conta antes de usar a página oficial.</p>}<footer><span><Clock3 size={14}/>Leitura: {date(account.observed_at)}</span><small>{account.source}</small></footer>
    </article>)}</div><p className="quota-notice"><Info size={17}/>{data.notice} Leitura recente: até {data.freshness_seconds} segundos, critério local.</p>{!data.local_controls&&<p className="quota-notice"><Computer size={17}/>Você pode consultar as cotas aqui. A configuração da janela do widget fica no aplicativo do computador.</p>}</>}
  </section>;
}
