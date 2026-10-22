import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, CircleAlert, FileCode2, LoaderCircle, Play, Search, ShieldCheck, WandSparkles } from 'lucide-react';
import { api, mutationKey, type MutationAttempt } from './api';
import { RouteSteps, type Routing, type RoutePreview } from './RoutingEditor';
import { ExecutionPlanView } from './Execution';
import type { Job, Versioned } from './types';
import AttachmentInput from './AttachmentInput';
import {normalizeAttachments, type Attachment} from './attachments';

type CodeFiles={files:{path:string;size:number}[];limits?:Record<string,unknown>};
type AnalysisDraft={prompt:string;category:string;second:string;selectedPaths:string[];anexos:Attachment[]};
function readDraft(key:string):AnalysisDraft{
  try{const value=JSON.parse(localStorage.getItem(key)||'{}');return {prompt:typeof value.prompt==='string'?value.prompt:'',category:typeof value.category==='string'?value.category:'',second:typeof value.second==='string'?value.second:'',selectedPaths:Array.isArray(value.selectedPaths)?value.selectedPaths.filter((p:unknown):p is string=>typeof p==='string'):[],anexos:normalizeAttachments(value.anexos)};}catch{return {prompt:'',category:'',second:'',selectedPaths:[],anexos:[]};}
}
export default function AnalysisForm({pid,projectName,onClose,onStarted,onError,onBusyChange}:{pid:string;projectName:string;onClose:()=>void;onStarted:(job:Job)=>void;onError:(e:unknown)=>void;onBusyChange?:(busy:boolean)=>void}){
  const draftKey=`mb-analysis-draft:${pid}`;
  const [draft,setDraft]=useState<AnalysisDraft>(()=>readDraft(draftKey));
  const {prompt,category,second,selectedPaths,anexos}=draft;
  const setPrompt=(prompt:string)=>setDraft(d=>({...d,prompt}));
  const setCategory=(category:string)=>setDraft(d=>({...d,category}));
  const setSecond=(second:string)=>setDraft(d=>({...d,second}));
  const setSelectedPaths=(value:string[]|((paths:string[])=>string[]))=>setDraft(d=>({...d,selectedPaths:typeof value==='function'?value(d.selectedPaths):value}));
  const [routing,setRouting]=useState<Routing|null>(null);const [routingError,setRoutingError]=useState('');
  const [preview,setPreview]=useState<RoutePreview|null>(null);
  const [busy,setBusy]=useState(false);const [previewBusy,setPreviewBusy]=useState(false);const [attachmentBusy,setAttachmentBusy]=useState(false);const [error,setError]=useState('');
  const [codeFiles,setCodeFiles]=useState<CodeFiles|null>(null);const [filesBusy,setFilesBusy]=useState(false);const [filesError,setFilesError]=useState('');const [fileQuery,setFileQuery]=useState('');
  const attempt=useRef<MutationAttempt|null>(null);const inputRevision=useRef(0);
  function invalidate(){inputRevision.current++;setPreview(null);}
  async function loadRouting(){setRoutingError('');try{setRouting((await api<Versioned<Routing>>(`/projects/${pid}/routing`)).data);}catch(e){setRoutingError((e as Error).message);onError(e);}}
  useEffect(()=>{void loadRouting();},[pid]);
  useEffect(()=>{onBusyChange?.(busy||attachmentBusy);},[busy,attachmentBusy,onBusyChange]);
  useEffect(()=>{try{if(draft.prompt||draft.anexos.length||draft.category||draft.second||draft.selectedPaths.length)localStorage.setItem(draftKey,JSON.stringify(draft));else localStorage.removeItem(draftKey);}catch{setError('O rascunho continua nesta janela, mas não pôde ser guardado neste aparelho. Envie antes de fechar.');}},[draftKey,draft]);
  const selection=()=>({...second&&category?{categories:[category,second]}:category?{category}:{},selected_paths:selectedPaths});
  const hasInput=Boolean(prompt.trim()||anexos.length);
  const hasCode=Boolean(selectedPaths.length||preview?.stages.some(s=>s.capability==='code')||routing?.routes.some(r=>[category,second].includes(r.id)&&r.stages.some(s=>s.capability==='code')));
  async function simulate(){if(!hasInput||previewBusy||busy||attachmentBusy)return;setPreviewBusy(true);setError('');const revision=inputRevision.current;try{const result=await api<RoutePreview>(`/projects/${pid}/route-preview`,'POST',{prompt:prompt.trim(),anexos,...selection()});if(revision===inputRevision.current)setPreview(result);}catch(e){setError((e as Error).message);onError(e);}finally{setPreviewBusy(false);}}
  async function run(){if(!hasInput||busy||previewBusy||attachmentBusy||!preview)return;setBusy(true);setError('');try{const payload={prompt:prompt.trim(),anexos,...selection()};const result=await api<{job:Job}>(`/projects/${pid}/jobs`,'POST',payload,mutationKey(attempt,{pid,...payload}));attempt.current=null;try{localStorage.removeItem(draftKey);}catch{/* O pedido confirmado não depende da limpeza do cache local. */}onStarted(result.job);}catch(e){setError((e as Error).message);onError(e);}finally{setBusy(false);}}
  async function loadFiles(){setFilesBusy(true);setFilesError('');try{setCodeFiles(await api<CodeFiles>(`/projects/${pid}/code-files`));}catch(e){setFilesError((e as Error).message);onError(e);}finally{setFilesBusy(false);}}
  function toggleFile(path:string){setSelectedPaths(paths=>paths.includes(path)?paths.filter(p=>p!==path):[...paths,path]);invalidate();}
  const visibleFiles=(codeFiles?.files||[]).filter(f=>f.path.toLowerCase().includes(fileQuery.toLowerCase()));
  return <>
    <div className="analysis-callout"><WandSparkles size={22}/><div><strong>Do pedido ao resultado conferido.</strong><p>Veja as etapas, ferramentas e arquivos previstos antes de começar.</p></div></div>
    <label htmlFor="new-prompt">O que vamos fazer?</label><AttachmentInput pid={pid} value={anexos} onChange={value=>{setDraft(d=>({...d,anexos:value}));invalidate();}} onBusyChange={setAttachmentBusy} disabled={busy}><textarea id="new-prompt" rows={4} value={prompt} disabled={busy} onChange={e=>{setPrompt(e.target.value);invalidate();}} placeholder={`Descreva o resultado que quer obter em ${projectName}…`}/></AttachmentInput>
    <label htmlFor="job-category">Tipo do pedido</label><select id="job-category" value={category} disabled={busy||!routing} onChange={e=>{setCategory(e.target.value);setSecond('');invalidate();setSelectedPaths([]);}}><option value="">Sugerir a partir do pedido</option>{routing?.routes.map(route=><option key={route.id} value={route.id}>{route.title}</option>)}</select>
    {routingError&&<p className="error-message" role="alert"><CircleAlert size={16}/>{routingError}<button className="text-button" onClick={()=>void loadRouting()}>Tentar novamente</button></p>}
    {category&&<details className="process-details"><summary>Combinar com outra esteira</summary><label htmlFor="second-category">Depois, passar também por</label><select id="second-category" value={second} disabled={busy} onChange={e=>{setSecond(e.target.value);invalidate();}}><option value="">Somente a primeira</option>{routing?.routes.filter(route=>route.id!==category).map(route=><option key={route.id} value={route.id}>{route.title}</option>)}</select><p className="fine-print">As etapas seguem a ordem exibida. A combinação pode usar mais chamadas de IA.</p></details>}
    {hasCode&&<details className="process-details code-file-picker"><summary><FileCode2 size={15}/>Usar arquivos existentes <span>Opcional</span></summary><p className="fine-print">Sem seleção, o pedido começa com arquivos novos. Os arquivos escolhidos serão copiados para a área do pedido; os originais ficam preservados.</p>{!codeFiles?<button className="secondary" onClick={()=>void loadFiles()} disabled={filesBusy||busy}>{filesBusy?<LoaderCircle className="spin" size={15}/>:<Search size={15}/>}Escolher arquivos do projeto</button>:<><label htmlFor="code-file-search">Filtrar arquivos</label><input id="code-file-search" value={fileQuery} onChange={e=>setFileQuery(e.target.value)} placeholder="Nome ou caminho do arquivo"/><div className="code-file-options">{visibleFiles.map(file=><label key={file.path}><input type="checkbox" disabled={busy} checked={selectedPaths.includes(file.path)} onChange={()=>toggleFile(file.path)}/><span>{file.path}<small>{file.size.toLocaleString('pt-BR')} bytes</small></span></label>)}{!visibleFiles.length&&<p className="fine-print">Nenhum arquivo disponível para esse filtro.</p>}</div><p className="fine-print">{selectedPaths.length} {selectedPaths.length===1?'arquivo selecionado':'arquivos selecionados'}. A lista inclui apenas os arquivos permitidos para este pedido.</p></>}{filesError&&<p className="error-message" role="alert">{filesError}</p>}</details>}
    <button className="text-button" onClick={()=>void simulate()} disabled={!hasInput||previewBusy||busy||attachmentBusy||!routing}>{previewBusy?<LoaderCircle className="spin" size={15}/>:<Play size={15}/>}Ver plano e ferramentas</button>
    {preview&&<div className="route-result"><strong>{preview.title}</strong><p>{preview.reason}</p><RouteSteps stages={preview.stages}/><ExecutionPlanView plan={preview.execution_plan}/><p>{preview.classification}</p><p>{preview.execution_scope}</p></div>}
    <p className="fine-print"><ShieldCheck size={14}/>Pesquisa e código usam as ferramentas das etapas escolhidas. Acompanhe fontes consultadas, arquivos produzidos, testes e revisão em Atividade.</p>
    {error&&<p className="error-message" role="alert"><CircleAlert size={16}/>{error}</p>}
    <p id="execute-requirement" className="fine-print">{attachmentBusy?'Espere o print terminar de enviar. O rascunho está preservado.':preview?'Plano conferido. Se alterar o pedido ou os prints, confira o plano novamente.':'Para liberar Executar pedido, escreva ou anexe um print e clique em Ver plano e ferramentas.'}</p>
    <div className="modal-actions"><button className="secondary" onClick={onClose} disabled={busy||attachmentBusy}>Cancelar</button><button className="primary" aria-describedby="execute-requirement" disabled={!hasInput||busy||previewBusy||attachmentBusy||!preview} onClick={()=>void run()}>{busy?<LoaderCircle className="spin" size={16}/>:<ArrowUpRight size={16}/>}Executar pedido</button></div>
  </>;
}
