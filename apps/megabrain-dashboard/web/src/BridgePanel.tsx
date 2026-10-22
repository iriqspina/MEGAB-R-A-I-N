// 261018 Ponte de correção: o que chega pelo "Enviar ao projeto" segue para um
// planejador (IA escolhida aqui), que abre orquestradores e workers. Este painel
// mostra a escolha da IA, a fila de comentários ainda sem ponte e a árvore de
// cada ordem, lida dos arquivos da própria ordem (.mb-ponte/ no projeto).
import {useCallback,useEffect,useState} from 'react';
import {Bot,CheckCheck,ChevronDown,CircleStop,Clock3,FileText,LoaderCircle,Network,Power,Send,TriangleAlert} from 'lucide-react';
import {api} from './api';
import type {BridgeNode,BridgeOrder,BridgePipeline,BridgeRoute,BridgeView,Comment} from './types';
import {BRIDGE_ROLES,ROLE_NAMES,commentRouteProblem,firstRoute,modelList,pipelineProblem,projectRoute,routeName,routeProblem} from './bridge-routing';
import './bridge.css';

const SITUACAO:Record<string,{label:string;tone:string}>={
  na_fila:{label:'Planejador abrindo',tone:'amber'},em_andamento:{label:'Em correção',tone:'blue'},
  corrigido:{label:'Corrigido · confira',tone:'green'},parcial:{label:'Parcial · veja pendências',tone:'amber'},
  falhou:{label:'Não concluiu',tone:'pink'},sem_resultado:{label:'Sem resultado registrado',tone:'pink'},
};
const STATUS_NO:Record<string,string>={criado:'na fila',iniciando:'abrindo',rodando:'trabalhando',concluido:'terminou',falhou:'falhou',interrompido:'parado'};
const PAPEL:Record<string,string>={planejador:'Planejador',orquestrador:'Orquestrador',worker:'Worker',revisor:'Revisor'};
const pendente=(c:Comment)=>c.target.startsWith('file:')&&!c.ponte&&c.status==='Recebido, aguardando correção';
const quando=(v?:string|null)=>{if(!v)return '';const d=new Date(v);return Number.isNaN(d.getTime())?'':d.toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});};
const nomeRelatorio=(s?:string)=>(s||'').split(/[\\/]/).pop()||'relatório';

export function useBridge(pid?:string){
  const [view,setView]=useState<BridgeView|null>(null);
  const load=useCallback(async()=>{if(!pid)return null;const v=await api<BridgeView>(`/projects/${encodeURIComponent(pid)}/bridge`);setView(v);return v;},[pid]);
  const save=useCallback(async(current:BridgeView,patch:Partial<BridgeView['data']>)=>{if(!pid)return null;const v=await api<BridgeView>(`/projects/${encodeURIComponent(pid)}/bridge`,'PUT',{revision:current.revision,data:{...current.data,...patch}});setView(v);return v;},[pid]);
  return {view,setView,load,save};
}

/** Escolha da IA que planeja: só as ativas neste MegaBrain ficam clicáveis. */
export function VendorChoice({view,busy,onPick,compact=false}:{view:BridgeView;busy:boolean;onPick:(id:string)=>void;compact?:boolean}){
  return <div className={`bridge-vendors${compact?' compact':''}`} role="radiogroup" aria-label="IA que planeja a correção">
    {view.vendors.map(v=>{const on=view.data.vendor===v.id;return <button key={v.id} type="button" role="radio" aria-checked={on} className={on?'on':''} disabled={!v.ativo||busy} title={v.ativo?`${v.cli}${v.aviso?' · '+v.aviso:''}`:v.motivo} onClick={()=>onPick(v.id)}>
      <Bot size={compact?12:14}/>{v.nome}{!compact&&<small>{v.ativo?v.cli:'inativo'}</small>}{v.ativo&&v.aviso&&<i className="bridge-warn" aria-label={v.aviso}>!</i>}
    </button>;})}
  </div>;
}

/** A seleção do comentário não altera os padrões do projeto. Ausência de rota herda o planejador. */
export function RouteChoice({view,value,onChange,busy=false,inherit=false,label='Destino deste comentário'}:{view:BridgeView;value?:BridgeRoute;onChange:(route:BridgeRoute|undefined)=>void;busy?:boolean;inherit?:boolean;label?:string}){
  const models=value?modelList(view,value.vendor):[];
  const model=models.find(m=>m.id===value?.modelo);
  const problem=value?(inherit?commentRouteProblem(view,value):routeProblem(view,value)):'';
  function pickVendor(vendor:string){onChange(vendor?firstRoute(view,vendor):undefined);}
  return <fieldset className="bridge-route" disabled={busy}>
    <legend>{label}</legend>
    <div className="bridge-route-fields">
      <label>IA<select aria-label={`${label}: IA`} value={value?.vendor||''} onChange={e=>pickVendor(e.target.value)}>
        <option value="" disabled={!inherit}>{inherit?'Padrão deste projeto':'Escolha a IA'}</option>
        {value&&!view.vendors.some(v=>v.id===value.vendor)&&<option value={value.vendor} disabled>{value.vendor} · indisponível</option>}
        {view.vendors.map(v=>{const modeBlocked=inherit&&v.id==='glm'&&view.data.modo==='janela';return <option key={v.id} value={v.id} disabled={!v.ativo||!firstRoute(view,v.id)||modeBlocked}>{v.nome}{!v.ativo?' · '+(v.motivo||'inativo'):modeBlocked?' · exige modo segundo plano':!firstRoute(view,v.id)?' · sem modelos disponíveis':''}</option>;})}
      </select></label>
      {value&&<><label>Modelo<select aria-label={`${label}: modelo`} value={value.modelo} onChange={e=>{const m=models.find(m=>m.id===e.target.value);if(m)onChange({...value,modelo:m.id,effort:m.efforts.includes(value.effort)?value.effort:m.efforts[0]});}}>
        {!model&&<option value={value.modelo} disabled>{value.modelo} · indisponível</option>}
        {models.map(m=><option key={m.id} value={m.id} disabled={m.ativo===false||!m.efforts.length}>{m.nome}{m.ativo===false?' · '+(m.motivo||'indisponível'):''}</option>)}
      </select></label><label>Esforço<select aria-label={`${label}: esforço`} value={value.effort} onChange={e=>onChange({...value,effort:e.target.value})}>
        {!model?.efforts.includes(value.effort)&&<option value={value.effort} disabled>{value.effort} · indisponível</option>}
        {model?.efforts.map(e=><option key={e} value={e}>{e}</option>)}
      </select></label></>}
    </div>
    {!value&&inherit&&<small>Herdará {routeName(view,projectRoute(view))}. Só muda este comentário.</small>}
    {!!problem&&<small className="bridge-problem" role="status">{problem}</small>}
  </fieldset>;
}

function PipelineEditor({view,busy,onSave}:{view:BridgeView;busy:boolean;onSave:(pipeline:BridgePipeline)=>Promise<boolean>}){
  const [draft,setDraft]=useState<BridgePipeline>(()=>({...view.data.pipeline}));
  const [preset,setPreset]=useState('');
  const [dirty,setDirty]=useState(false);
  // Background refresh never replaces choices being edited.
  useEffect(()=>{if(!dirty)setDraft({...view.data.pipeline});},[view.revision,dirty]);
  const selected=view.presets?.find(p=>p.id===preset);
  const problem=pipelineProblem(view,draft);
  return <details className="bridge-pipeline">
    <summary>Papéis e modelos deste projeto</summary>
    <p className="bridge-note">Cada projeto guarda sua combinação. Salvar define as próximas ordens; não inicia uma IA.</p>
    {!!view.presets?.length&&<details className="bridge-presets"><summary>Modelos prontos · escolha com contexto</summary>
      <label>Combinação<select value={preset} onChange={e=>setPreset(e.target.value)} disabled={busy}><option value="">Comparar e escolher…</option>{view.presets.map(p=><option key={p.id} value={p.id}>{p.nome}</option>)}</select></label>
      {selected&&<div className="bridge-preset"><strong>{selected.nome}</strong><p>{selected.descricao}</p><p><b>Custo da escolha:</b> {selected.tradeoff}</p><small>Fonte: {selected.fonte}</small>{pipelineProblem(view,selected.pipeline)&&<small className="bridge-problem">{pipelineProblem(view,selected.pipeline)}</small>}<button type="button" className="secondary" disabled={busy||!!pipelineProblem(view,selected.pipeline)} onClick={()=>{setDraft({...selected.pipeline});setDirty(true);}}>Usar esta combinação nos campos</button><small>Revise abaixo e salve para aplicar ao projeto.</small></div>}
    </details>}
    <div className="bridge-pipeline-roles">{BRIDGE_ROLES.map(role=><RouteChoice key={role} view={view} value={draft[role]||projectRoute(view,role)} label={ROLE_NAMES[role]} busy={busy} onChange={route=>{if(route){setDraft(prev=>({...BRIDGE_ROLES.reduce<BridgePipeline>((p,r)=>({...p,[r]:projectRoute(view,r)}),{}),...prev,[role]:route}));setDirty(true);}}}/>)}</div>
    {problem&&dirty&&<p className="bridge-problem" role="status">{problem}</p>}
    <button type="button" className="secondary" disabled={busy||!dirty||!!problem} onClick={()=>{void onSave(draft).then(ok=>{if(ok)setDirty(false);});}}>Salvar papéis deste projeto</button>
    {dirty&&<button type="button" className="text-button" disabled={busy} onClick={()=>{setDraft({...view.data.pipeline});setDirty(false);}}>Descartar edição dos campos</button>}
  </details>;
}

function Tree({nodes}:{nodes:BridgeNode[]}){
  return <ol className="bridge-tree">{nodes.map(n=>{const st=n.status_observado?'sem processo':STATUS_NO[n.status]||n.status;return <li key={n.id} style={{['--depth' as string]:String(n.profundidade||0)}} className={`node ${n.status}${n.status_observado?' lost':''}`}>
    <span className="dot" aria-hidden="true"/>
    <div><strong>{PAPEL[n.papel]||n.papel} · {n.nome_vendor}</strong><small>{n.id} · {st}{n.fim?' · '+quando(n.fim):''}</small>
      <p>{n.titulo}</p>
      {(n.resumo||n.saida||n.erro)&&<details><summary>registro</summary><pre>{(n.erro?n.erro+'\n':'')+(n.resumo||n.saida)}</pre></details>}
    </div>
  </li>;})}</ol>;
}

function Order({order,onStop,busy}:{order:BridgeOrder;onStop:(id:string)=>void;busy:boolean}){
  const s=SITUACAO[order.situacao]||{label:order.situacao,tone:'pink'};
  const vivo=order.situacao==='em_andamento'||order.situacao==='na_fila';
  return <article className="bridge-order">
    <header><span className={`bridge-tag ${s.tone}`}>{vivo&&<LoaderCircle size={12} className="spin"/>}{s.label}</span><small><Clock3 size={12}/>{quando(order.criado_em)} · planejador {order.nome_vendor}{order.complementos?` · +${order.complementos} complemento(s)`:''}</small></header>
    {order.resumo_pedido&&<p className="bridge-ask">“{order.resumo_pedido}”</p>}
    {order.resultado&&<div className={`bridge-result ${order.resultado.status}`}><p><CheckCheck size={14}/>{order.resultado.resumo}</p>{order.resultado.pendencias.length>0&&<p><TriangleAlert size={14}/>Pendências: {order.resultado.pendencias.join('; ')}</p>}</div>}
    {order.plano?.objetivo&&<p className="bridge-plan"><FileText size={13}/>{order.plano.objetivo}</p>}
    <Tree nodes={order.nos}/>
    {vivo&&<button type="button" className="secondary bridge-stop" disabled={busy} onClick={()=>onStop(order.ordem_id)}><CircleStop size={14}/>Parar esta ordem</button>}
  </article>;
}

export default function BridgePanel({pid,comments,onError}:{pid:string;comments:Comment[];onError:(e:unknown)=>void}){
  const {view,load,save}=useBridge(pid);
  const [busy,setBusy]=useState('');
  const [aberto,setAberto]=useState(false);
  const [descartar,setDescartar]=useState('');
  useEffect(()=>{void load().catch(()=>{});const t=setInterval(()=>{if(document.visibilityState==='visible')void load().catch(()=>{});},6000);return()=>clearInterval(t);},[load]);
  if(!view)return null;
  const current=view;
  async function run(key:string,fn:()=>Promise<unknown>){setBusy(key);try{await fn();await load();return true;}catch(e){onError(e);void load().catch(()=>{});return false;}finally{setBusy('');}}
  const grupos=Object.values(comments.filter(pendente).reduce<Record<string,Comment[]>>((acc,c)=>{(acc[c.source||c.target]??=[]).push(c);return acc;},{})).slice(0,6);
  const nome=current.vendors.find(v=>v.id===current.data.vendor)?.nome||'—';
  const ordens=current.ordens;
  const visiveis=aberto?ordens:ordens.slice(0,2);
  // 261022 Bubble: projeto pausado guarda a fila em silêncio; o painel diz isso e permite tirar o que já foi atendido à mão.
  const parado=!!current.controle&&current.controle!=='ativo';
  const fila=current.pendentes||[];
  // 261022: data-cf-zona marca a seção para a nota do cursor; a central despacha à ponte só o que nasce aqui.
  return <section className="bridge-panel" aria-label="Ponte de correção" data-cf-zona="ponte-correcao">
    <header>
      <strong><Network size={16}/>Ponte de correção</strong>
      <button type="button" className={`bridge-power${current.data.auto?' on':''}`} aria-pressed={current.data.auto} disabled={busy==='config'} onClick={()=>void run('config',()=>save(current,{auto:!current.data.auto}))}><Power size={13}/>{current.data.auto?'Automática':'Desligada'}</button>
    </header>
    <p className="bridge-flow"><span>Enviar ao projeto</span>→<b>planejador {nome}</b>→<span>orquestradores</span>→<span>workers</span></p>
    <p className="bridge-note"><Clock3 size={13}/>Aguarda 3 minutos desde a última novidade. Comentário novo ou editado reinicia a espera.</p>
    <PipelineEditor view={current} busy={busy==='config'} onSave={pipeline=>run('config',()=>save(current,{pipeline,vendor:pipeline.planejador?.vendor||current.data.vendor}))}/>
    <details className="bridge-mode">
      <summary>Como roda: {current.data.modo==='janela'?'janela de terminal':'em segundo plano'}</summary>
      <label><input type="radio" name={`bridge-mode-${pid}`} checked={current.data.modo==='segundo_plano'} onChange={()=>void run('config',()=>save(current,{modo:'segundo_plano'}))}/>Em segundo plano (acompanhe aqui)</label>
      <label><input type="radio" name={`bridge-mode-${pid}`} checked={current.data.modo==='janela'} disabled={projectRoute(current)?.vendor==='glm'||busy==='config'} onChange={()=>void run('config',()=>save(current,{modo:'janela'}))}/>Janela de terminal (conversa com o planejador)</label>
      <p className="bridge-note">Modo janela abre um terminal separado para conversar com o planejador. Em segundo plano, você acompanha o trabalho no MegaBrain.</p>
      {projectRoute(current)?.vendor==='glm'?<p className="bridge-problem">GLM recebe correções em segundo plano. Janela com este perfil ainda não foi certificada.</p>:<p className="bridge-note">Na janela, uma edição pode aguardar a identificação da conversa para voltar ao mesmo agente. A pendência aparece no MegaBrain.</p>}
    </details>
    {!current.lancamento&&<p className="bridge-note"><TriangleAlert size={13}/>Instância de prova: registra a fila, não abre sessões de IA.</p>}
    {parado&&<p className="bridge-problem" role="status"><TriangleAlert size={13}/>Projeto {current.controle==='aguardando'?'aguardando retorno':'pausado'}: a ponte guarda as notas e não abre IA até você retomar (segure o clique 0,4 s → Retomar projeto).</p>}
    {fila.length>0&&<div className="bridge-queue"><small>Na fila da ponte{parado?' · espera a retomada do projeto':''}:</small>{fila.map(p=><div key={p.chave}>
      <span><Clock3 size={13}/>{p.comentarios.length} nota(s){p.criado_em?' · '+quando(p.criado_em):''}{p.resumo?` · “${p.resumo.length>90?p.resumo.slice(0,90)+'…':p.resumo}”`:''}</span>
      {p.estado==='lancando'?<small>enviando agora</small>:descartar===`${p.chave}#${p.revisao}`?<span>
        <button type="button" className="secondary" disabled={!!busy} onClick={()=>void run('discard',()=>api(`/projects/${encodeURIComponent(pid)}/bridge/pending/discard`,'POST',{chave:p.chave,revisao:p.revisao,motivo:'Atendido fora da ponte (painel Ponte de correção)'})).then(()=>setDescartar(''))}>{busy==='discard'?<LoaderCircle size={13} className="spin"/>:<CheckCheck size={13}/>}Confirmar: já atendido</button>
        <button type="button" className="text-button" disabled={!!busy} onClick={()=>setDescartar('')}>Cancelar</button>
      </span>:<button type="button" className="secondary" disabled={!!busy} title="Use quando outra sessão já fez o pedido à mão: os comentários ficam marcados como atendidos fora da ponte, com histórico, e nenhuma IA é aberta." onClick={()=>setDescartar(`${p.chave}#${p.revisao}`)}><CheckCheck size={13}/>Já atendido · tirar da fila</button>}
    </div>)}</div>}
    {grupos.length>0&&<div className="bridge-queue"><small>Comentários recebidos antes da ponte, ainda sem IA:</small>{grupos.map(g=><div key={g[0].id}><span><FileText size={13}/>{nomeRelatorio(g[0].source)} · {g.length} comentário(s)</span><button type="button" className="secondary" disabled={!!busy||!current.data.vendor||!current.lancamento} onClick={()=>void run('send',()=>api(`/projects/${encodeURIComponent(pid)}/bridge/send`,'POST',{comment_ids:g.map(c=>c.id)}))}>{busy==='send'?<LoaderCircle size={13} className="spin"/>:<Send size={13}/>}Mandar ao {nome}</button></div>)}</div>}
    {ordens.length===0?<p className="bridge-empty">Nenhuma ordem ainda. {current.data.auto?'Comentários enviados aguardam a pausa de 3 minutos; depois a ponte tenta abrir o planejador '+nome+'.':'A ponte automática está desligada.'}</p>:<div className="bridge-orders">{visiveis.map(o=><Order key={o.ordem_id} order={o} busy={!!busy} onStop={id=>void run('stop',()=>api(`/projects/${encodeURIComponent(pid)}/bridge/orders/${id}/stop`,'POST',{}))}/>)}</div>}
    {ordens.length>2&&<button type="button" className="text-button bridge-more" onClick={()=>setAberto(v=>!v)}><ChevronDown size={14}/>{aberto?'Mostrar só as recentes':`Ver todas as ${ordens.length} ordens`}</button>}
  </section>;
}
