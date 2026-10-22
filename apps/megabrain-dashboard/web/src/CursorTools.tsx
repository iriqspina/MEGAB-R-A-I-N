import {useEffect,useRef} from 'react';
import {api} from './api';
import {normalizeAttachments,uploadAttachment,previewAttachment,type Attachment} from './attachments';
import {noteFingerprint} from './report-notes';
import {readRoute} from './bridge-routing';
import type {BridgeRoute,BridgeView} from './types';

type Note={id:string;texto:string;rota?:BridgeRoute;anexos?:Attachment[];onde?:string;zona?:string;criado_em?:string;ancora:{base:string;idx:number[]};ox:number;oy:number};
type Receipt={text:string;fingerprint?:string;pid:string;attempt:string;saved?:boolean};
type Control={destruir:()=>void;usar:(id:string)=>void;atual:()=>string;notas:()=>Note[];desenhos:()=>unknown[];abrirMenu:(x:number,y:number)=>void};
declare global{interface Window{CursorFerramentas?:{iniciar:(options:Record<string,unknown>)=>Control};brainCursorTools?:Control;}}
function targetOf(note:Note):HTMLElement|null{try{let el:Element|null=note.ancora.base==='body'?document.body:document.querySelector(note.ancora.base);for(const index of note.ancora.idx)el=el?.children[index]||null;return el as HTMLElement|null;}catch{return null;}}
async function load(){if(window.CursorFerramentas)return;await new Promise<void>((resolve,reject)=>{const script=document.createElement('script');script.src='/cursor-ferramentas-v1.2.js?v=261020-controle';script.onload=()=>resolve();script.onerror=()=>reject(new Error('Não foi possível carregar as ferramentas do cursor.'));document.head.append(script)});}
export default function CursorTools({projectKey,onSaved,onError,onReload}:{projectKey:string|null;onSaved:(message:string)=>void;onError:(error:unknown)=>void;onReload:(pid:string)=>void}){
 const handlers=useRef({onSaved,onError,onReload});handlers.current={onSaved,onError,onReload};
 useEffect(()=>{
  if(!projectKey)return;
  let stopped=false;let control:Control|undefined;let queue=Promise.resolve();
  const receiptKey='mb-cursor-receipts:'+projectKey;
  let receipts:Record<string,Receipt>={};
  try{const stored=JSON.parse(localStorage.getItem(receiptKey)||'{}');if(stored&&typeof stored==='object'&&!Array.isArray(stored))receipts=stored;}catch{}
  const persist=()=>{try{localStorage.setItem(receiptKey,JSON.stringify(receipts))}catch{}};
  const projectOf=async(note?:Note)=>{
   const board=note?targetOf(note)?.closest<HTMLElement>('[data-cf-project]'):null;
   const pid=board?.dataset.cfProject||(await api<{central_project_id:string}>('/session')).central_project_id;
   if(!pid)throw new Error('Nota preservada neste aparelho: projeto da central indisponível.');
   return pid;
  };
  const saveNotes=(notes:Note[])=>{
   for(const source of notes){
    const anexos=normalizeAttachments(source.anexos);
    if(!source.texto?.trim()&&!anexos.length)continue;
    if(source.rota!==undefined&&!readRoute(source.rota)){handlers.current.onError(new Error('Destino inválido na nota. Escolha IA, modelo e esforço novamente.'));handlers.current.onSaved('Nota preservada neste aparelho; destino inválido, nenhum envio realizado.');continue;}
    // A fila guarda a edição salva, mesmo se o editor alterar o mesmo objeto logo depois.
    const note:Note={...source,rota:readRoute(source.rota),anexos,ancora:{...source.ancora,idx:[...source.ancora.idx]}};
    const target=targetOf(note),boardPid=target?.closest<HTMLElement>('[data-cf-project]')?.dataset.cfProject;
    const moduleId=target?.closest<HTMLElement>('[data-cf-module]')?.dataset.cfModule;
    // 261022: zona gravada pela ferramenta quando a nota nasceu (data-cf-zona); nunca recalculada pela posição atual.
    const zona=typeof note.zona==='string'&&note.zona?note.zona:undefined;
    queue=queue.then(async()=>{
     const pid=boardPid||await projectOf();
     const fingerprint=noteFingerprint(note),previous=receipts[note.id];
     // O recibo legado só pode confirmar uma nota que continua sem anexos.
     const same=previous?.pid===pid&&(previous.fingerprint!==undefined?previous.fingerprint===fingerprint:!anexos.length&&!note.rota&&previous.text===note.texto);
     if(same&&previous.saved)return;
     const receipt:Receipt=same&&previous.attempt?previous:{text:note.texto,fingerprint,pid,attempt:crypto.randomUUID()};
     receipts[note.id]=receipt;persist();
     try{
      await api(`/projects/${pid}/comments`,'POST',{
       text:(note.texto||'').trim(),...(anexos.length?{anexos}:{}),
       ...(readRoute(note.rota)?{rota:readRoute(note.rota)}:{}),
       target:boardPid?'module:'+(moduleId||'cursor'):'app:'+projectKey,
       anchor:{x:note.ox,y:note.oy},
       cursor_source:{note_id:note.id,storage_key:'mb-cursor-notas:'+projectKey,where:note.onde||'',created_at:note.criado_em||'',...(zona?{zona}:{})}
      },receipt.attempt);
      receipt.saved=true;persist();handlers.current.onSaved('Nota enviada ao projeto ✓');handlers.current.onReload(pid);
     }catch(error){
      handlers.current.onError(error);handlers.current.onSaved('Nota preservada neste aparelho; envio ao projeto falhou. Salve novamente para tentar.');
     }
    }).catch(error=>{handlers.current.onError(error);handlers.current.onSaved('Nota preservada neste aparelho; envio à central indisponível.');});
   }
  };
  void load().then(()=>{
   if(stopped||!window.CursorFerramentas)return;
   control=window.CursorFerramentas.iniciar({
    controleProjeto:async(target:HTMLElement|null,modo?:string,revision?:number)=>{
     const pid=target?.closest<HTMLElement>('[data-cf-project]')?.dataset.cfProject||await projectOf();
     const value=await api<{revision:number;data:{modo:string};projeto:string}>(`/projects/${encodeURIComponent(pid)}/control`,modo?'PUT':'GET',modo?{revision,modo}:undefined);
     return value;
    },
    modo:'local',segurarMs:400,cancelarAoMover:true,tolerancia:3,toleranciaToque:8,
    chave:'mb-cursor-notas:'+projectKey,chaveDesenhos:'mb-cursor-desenhos:'+projectKey,chaveAprovacoes:'mb-cursor-aprovacoes:'+projectKey,chavePrefs:'mb-cursor-prefs',
    carregarPonte:async(note:Note)=>api<BridgeView>(`/projects/${encodeURIComponent(await projectOf(note))}/bridge`),
    // Comentar alcança botões, links, selects e alças: só campos de digitar, iframes e mídia ficam com a página (261020).
    ignorarAlvo:'input,textarea,[contenteditable],iframe,audio,video,[data-cf-ignorar]',
    // Segurar abre o leque também sobre botões do topo, da lateral e das barras; só alças de arrastar ficam de fora,
    // porque lá segurar parado antes de mover é o próprio gesto da página (261020: antes o botão era clicado).
    ignorar:'input,textarea,select,[contenteditable],[data-cf-ignorar],[data-cf-alca],.modal-shade,.module-handle,.rail-move-handle,.react-resizable-handle,iframe,audio,video',
    anexos:{
     upload:async(file:File,note?:Note)=>uploadAttachment(await projectOf(note),file),
     preview:async(attachment:Attachment,note?:Note)=>previewAttachment(await projectOf(note),attachment)
    },
    aoSalvarNota:(note:Note)=>saveNotes([note]),
    aoMudarDesenhos:()=>handlers.current.onSaved('Desenho salvo neste aparelho. Trocar de projeto usa outra camada.'),
    aoAprovar:()=>handlers.current.onSaved('Marca de aprovação local. A decisão da execução permanece no projeto.')
   });
   window.brainCursorTools=control;
  }).catch(error=>handlers.current.onError(error));
  return()=>{stopped=true;control?.destruir();if(window.brainCursorTools===control)delete window.brainCursorTools};
 },[projectKey]);
 return null;
}
