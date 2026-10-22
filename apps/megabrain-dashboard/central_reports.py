"""Project report rendering inside an opaque child, never in the API's origin.

Source files are read only. Messages are proposals/data, never commands. The
host must validate the wrapper window and ticket and ask the human to save any
feedback. A report hash binds drafts and feedback to the version displayed.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import mimetypes
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import url2pathname

MAX_REPORT = 64_000_000
MAX_RESOURCE = 8_000_000
MAX_BUNDLE = 40_000_000
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico', '.mp3', '.wav', '.ogg', '.mp4', '.webm', '.woff', '.woff2', '.ttf'}
PRIVATE = {'.env', 'private', 'privado', 'privados', 'privadas', 'secrets', 'credentials', 'credenciais', '__pycache__', 'node_modules', '.git', '.venv', 'runtime-packages'}

view_headers = {
    'Content-Security-Policy': "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
}
render_headers = {
    'Content-Security-Policy': "sandbox allow-scripts allow-forms; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; media-src data:; font-src data:; connect-src 'none'; frame-src 'none'; child-src 'none'; object-src 'none'; worker-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'",
    'X-Frame-Options': 'SAMEORIGIN', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
}
VIEW_HEADERS = view_headers
RENDER_HEADERS = render_headers


def _identity(fid, token):
    if not re.fullmatch(r'[a-f0-9]{20}', str(fid)) or not re.fullmatch(r'[A-Za-z0-9_-]{16,160}', str(token)):
        raise ValueError('Identificador ou ticket de relatório inválido.')


def _json(value):
    return json.dumps(value, ensure_ascii=False).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def confined_file(path, root, *, suffixes=None, limit=MAX_RESOURCE):
    """Permit relative parent steps inside root, but reject hidden/private paths.

Both lexical and resolved paths are checked so a private symlink alias cannot
expose private content. Hardlinks are refused too: their origin is ambiguous.
"""
    root = Path(root).resolve(strict=True)
    raw = Path(path)
    raw = raw if raw.is_absolute() else root / raw
    lexical = Path(__import__('os').path.abspath(raw))
    def validate(candidate):
        if not candidate.is_relative_to(root):
            raise ValueError('Arquivo fora do projeto.')
        if any(part.startswith('.') or part.casefold() in PRIVATE for part in candidate.relative_to(root).parts):
            raise ValueError('Arquivo privado não pode aparecer no relatório.')
    validate(lexical)
    try:
        resolved = raw.resolve(strict=True)
    except (FileNotFoundError, NotADirectoryError):
        raise ValueError('Arquivo indisponível.') from None
    validate(resolved)
    try:
        is_file = resolved.is_file()
        info = resolved.stat()
    except (FileNotFoundError, NotADirectoryError):
        raise ValueError('Arquivo indisponível.') from None
    if not is_file or info.st_nlink > 1 or info.st_size > limit:
        raise ValueError('Arquivo indisponível ou acima do limite.')
    if suffixes is not None and resolved.suffix.lower() not in suffixes:
        raise ValueError('Tipo de recurso não permitido.')
    return resolved


BOOTSTRAP = r"""
(()=>{'use strict';const META=__META__,memory=Object.create(null);let started=false;
const send=(kind,payload)=>parent.postMessage({...META,channel:'megabrain-report',kind,payload},'*');
const controlPending=new Map();
window.MegaBrainProjectControl=(_target,modo,revision)=>new Promise((resolve,reject)=>{const id=crypto.randomUUID();const timer=setTimeout(()=>{controlPending.delete(id);reject(new Error('Aplicativo não confirmou. Reabra para conferir.'));},15000);controlPending.set(id,{resolve,reject,timer});send('project-control',{requestId:id,modo,revision});});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||m?.channel!=='megabrain-report-control-result'||m.token!==META.token||m.fid!==META.fid||m.hash!==META.hash)return;const p=controlPending.get(m.requestId);if(!p)return;clearTimeout(p.timer);controlPending.delete(m.requestId);if(m.error)p.reject(new Error(m.error));else p.resolve(m.value);});
const attachmentBlockedFields=new Set();let attachmentBlocked=false;
document.addEventListener('mb-attachments-state',event=>{const d=event.detail;if(!d||typeof d.id!=='string'||d.id.length>180)return;if(d.bloqueado===true){if(attachmentBlockedFields.size<1000)attachmentBlockedFields.add(d.id);}else attachmentBlockedFields.delete(d.id);const next=attachmentBlockedFields.size>0;if(next!==attachmentBlocked){attachmentBlocked=next;send('attachment-state',{blocked:next});}});
const trim=(v,n=6000)=>typeof v==='string'?v.slice(0,n):'';
const HOST_ORIGIN=new URL(location.href).origin,ATTACHMENT_MAX=8*1024*1024,attachmentRequests=new Map();
const attachmentTypes=['image/png','image/jpeg','image/gif','image/webp'];
function attachments(values){return window.CursorFerramentas?.anexos?.normalizar(values)||[];}
function attachmentRequest(channel,payload){return new Promise((resolve,reject)=>{if(parent===window||attachmentRequests.size>=12){reject(new Error('Anexos indisponíveis agora. O rascunho foi preservado.'));return;}const requestId='mb_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2);const timer=setTimeout(()=>{attachmentRequests.delete(requestId);reject(new Error('O aplicativo não respondeu ao anexo. Tente novamente; rascunho preservado.'));},20000);attachmentRequests.set(requestId,{resolve,reject,timer,preview:channel==='mb-attachment-preview-request'});const message={...META,channel,requestId,...payload};try{parent.postMessage(message,HOST_ORIGIN,payload.file?[payload.file.data]:[]);}catch(error){clearTimeout(timer);attachmentRequests.delete(requestId);reject(error);}});}
window.MegaBrainAttachments=Object.freeze({async upload(file){if(!file||!attachmentTypes.includes(file.type)||!Number.isSafeInteger(file.size)||file.size<=0||file.size>ATTACHMENT_MAX)throw new Error('Use PNG, JPEG, GIF ou WebP de até 8 MiB.');const data=await file.arrayBuffer();if(!(data instanceof ArrayBuffer)||data.byteLength!==file.size)throw new Error('Não consegui ler o print. Escolha o arquivo novamente.');return attachmentRequest('mb-attachment-request',{file:{name:trim(file.name,240)||'Print',mime:file.type,data}});},preview(attachment){const ref=attachments([attachment])[0];if(!ref)return Promise.reject(new Error('Referência de anexo inválida.'));return attachmentRequest('mb-attachment-preview-request',{attachment:ref});}});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||!m||m.token!==META.token||m.fid!==META.fid||m.hash!==META.hash||!['mb-attachment-result','mb-attachment-preview-result'].includes(m.channel))return;const pending=attachmentRequests.get(m.requestId);if(!pending||pending.preview!==(m.channel==='mb-attachment-preview-result'))return;attachmentRequests.delete(m.requestId);clearTimeout(pending.timer);if(typeof m.error==='string'){pending.reject(new Error(m.error.slice(0,400)));return;}if(pending.preview){if(typeof m.preview==='string'&&m.preview.length<=Math.ceil(ATTACHMENT_MAX/3)*4+100&&/^data:image\/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(m.preview))pending.resolve(m.preview);else pending.reject(new Error('Prévia de anexo inválida.'));}else{const ref=attachments([m.attachment])[0];if(ref)pending.resolve(ref);else pending.reject(new Error('O aplicativo devolveu um anexo inválido.'));}});
const coordinate=v=>Number.isFinite(Number(v))?Number(v):0;
function anchor(value){if(value&&typeof value==='object'&&!Array.isArray(value)&&typeof value.base==='string'&&Array.isArray(value.idx))return {base:trim(value.base,300),idx:value.idx.slice(0,64).filter(i=>Number.isSafeInteger(i)&&i>=0&&i<=10000)};return trim(value,300);}
function noteRoute(v){if(v===undefined||v===null)return undefined;if(typeof v!=='object'||Array.isArray(v))return {};const out={};for(const k of ['vendor','modelo','effort'])if(typeof v[k]==='string')out[k]=trim(v[k],k==='modelo'?100:40);return out;}
function notes(values){return Array.isArray(values)?values.slice(0,150).filter(v=>v&&(typeof v.texto==='string'||attachments(v.anexos).length)).map(v=>({texto:trim(v.texto),id:trim(v.id,180),n:Number(v.n)||0,onde:trim(v.onde,500),criado_em:trim(v.criado_em,80),x:coordinate(v.x),y:coordinate(v.y),ox:coordinate(v.ox),oy:coordinate(v.oy),px:coordinate(v.px),py:coordinate(v.py),ancora:anchor(v.ancora||v.alvo),anexos:attachments(v.anexos),...(noteRoute(v.rota)?{rota:noteRoute(v.rota)}:{})})):[];}
function state(){const out={};for(const key of Object.keys(memory).slice(0,100)){if(memory[key].length<=50000)out[key]=memory[key];}return out;}
/* 261017 WP2: o rascunho vai ao app com espera de 1,5 s (antes ia a cada tecla) e sai na hora quando a página some ou fecha. */
let draftTimer=0,draftFirst=0;
function flushDraft(){if(draftTimer){clearTimeout(draftTimer);draftTimer=0;}draftFirst=0;send('draft',{storage:state()});}
/* 261018 (A4): espera curta (300 ms) e no maximo 1,2 s entre envios; fechar o relatorio logo depois de digitar nao perde o texto */
function queueDraft(){const now=Date.now();if(!draftFirst)draftFirst=now;if(draftTimer)clearTimeout(draftTimer);draftTimer=setTimeout(()=>{draftTimer=0;draftFirst=0;send('draft',{storage:state()});},now-draftFirst>=1200?0:300);}
function flushQueued(){if(draftTimer)flushDraft();}
addEventListener('pagehide',flushQueued);document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')flushQueued();});
const storage={getItem:k=>Object.hasOwn(memory,String(k))?memory[String(k)]:null,setItem(k,v){k=String(k);v=String(v);if(k.length>250||v.length>50000)return;memory[k]=v;queueDraft();},removeItem(k){delete memory[String(k)];queueDraft();},clear(){for(const k of Object.keys(memory))delete memory[k];queueDraft();},key:i=>Object.keys(memory)[i]||null,get length(){return Object.keys(memory).length;}};
try{Object.defineProperty(window,'localStorage',{value:storage,configurable:false});Object.defineProperty(window,'sessionStorage',{value:storage,configurable:false});}catch{}
let cursor=null,decisions=null,fallbackStarting=false,fallbackTools=null,fallbackCleanup=null;
function hook(name,wrap){let value;Object.defineProperty(window,name,{configurable:true,get:()=>value,set(v){value=v;if(v&&typeof v.iniciar==='function'){const original=v.iniciar;v.iniciar=function(o={}){return wrap(original,o,this);};}}});}
/* 261017 WP2: cada nota salva vai ao app junto com a lista completa das notas salvas (completa:true); o app troca o pacote pendente em vez de somar, então nota apagada sai dele. enviar = nota recém-salva, que o app manda na hora ao projeto. */
let savedIds=null,savedNotes=null;
function savedOnly(list){return Array.isArray(list)?list.filter(v=>v&&(typeof v.texto==='string'&&v.texto.trim()||attachments(v.anexos).length)):[];}
function notesChanged(list){const saved=savedOnly(list),ids=new Set(saved.map(v=>String(v.id||'')));const removed=savedIds===null?[]:[...savedIds].filter(id=>id&&!ids.has(id)).slice(0,150).map(id=>trim(id,180));savedIds=ids;savedNotes=saved;if(removed.length)send('feedback',{kind:'notes',completa:true,notas:notes(saved),enviar:[],removidas:removed});}
function noteSaved(n){const id=n&&typeof n.id==='string'?n.id:'';let list=savedNotes;if(!Array.isArray(list))list=[n];else if(id&&!list.some(v=>v&&v.id===id))list=[...list,n];else if(id)list=list.map(v=>v&&v.id===id?n:v);send('feedback',{kind:'notes',completa:Array.isArray(savedNotes),notas:notes(list),enviar:id?[trim(id,180)]:[]});flushDraft();}
hook('CursorFerramentas',(fn,o,ctx)=>{const own=o.aoSalvarNota,ownChange=o.aoMudarNotas;cursor=fn.call(ctx,{...o,segurarMs:400,cancelarAoMover:true,tolerancia:3,toleranciaToque:8,atrasoVisualMs:80,aoMudarNotas(list){try{notesChanged(list);}catch{}if(typeof ownChange==='function')ownChange(list);},aoSalvarNota(n){noteSaved(n);if(typeof own==='function')own(n);}});if(savedIds===null){try{savedIds=new Set(savedOnly(JSON.parse(memory[String(o.chave||('cf-notas:'+location.pathname))]||'[]')).map(v=>String(v.id||'')));}catch{savedIds=new Set();}}if(!fallbackStarting&&fallbackTools){fallbackCleanup?.();fallbackCleanup=null;fallbackTools.remove();fallbackTools=null;}return cursor;});
function legacyDecisionAttachments(api,o){if(api?.suportaAnexos||!window.CursorFerramentas?.anexos)return;const key='mb-report-decision-attachments:'+META.fid+':'+META.hash,fields=[],blocked={};let refs={};try{refs=JSON.parse(memory[key]||'{}')||{};}catch{}const answers=api.respostas.bind(api);api.respostas=()=>{const value=answers();for(const [id,list]of Object.entries(refs))if(value[id])value[id]={...value[id],anexos:attachments(list)};return value;};const tooMany=()=>new Set(Object.values(refs).flatMap(v=>attachments(v).map(a=>a.id))).size>6;api.anexosPendentes=()=>tooMany()||Object.values(blocked).some(Boolean);function state(){for(const id of ['dr-finalizar','dr-enviar','dr-term-enviar']){const b=document.getElementById(id);if(b)b.disabled=api.anexosPendentes();}}for(const section of o.secoes||[])for(const q of section.perguntas||[]){const text=document.querySelector('[data-dr-texto="'+CSS.escape(q.id)+'"]'),extra=q.tipo==='escolha'&&(q.opcoes||[]).some(v=>v.extra&&v.extra!=='data');if(!text&&!extra)continue;const el=text||document.getElementById('dr_f_'+q.id);if(!el)continue;fields.push(window.CursorFerramentas.anexos.montarCampo({elemento:el,container:document.getElementById('dr_f_'+q.id),contexto:{pergunta:q.id},getAnexos:()=>refs[q.id],setAnexos:values=>{refs[q.id]=values;storage.setItem(key,JSON.stringify(refs));state();},aoEstado:s=>{blocked[q.id]=s.bloqueado;state();}}));}state();}
hook('DecisoesRespondiveis',(fn,o,ctx)=>{decisions=fn.call(ctx,o);legacyDecisionAttachments(decisions,o);return decisions;});
function ensureCursor(){
 if(cursor){if(typeof cursor.usar==='function'&&typeof cursor.atual==='function')return;cursor=null;throw new Error('Report comment controls unavailable');}if(!document.body||typeof window.CursorFerramentas?.iniciar!=='function')throw new Error('Report comment initializer unavailable');
 const tools=document.createElement('div');tools.className='mb-report-tools cf-ui';tools.setAttribute('role','toolbar');tools.setAttribute('aria-label','Comentários neste relatório');
 const style=document.createElement('style');style.textContent='.mb-report-grupo{display:flex;flex-wrap:wrap;gap:6px}.mb-report-dica{font:500 11px/1.3 system-ui;opacity:.8;padding:0 4px}.mb-report-tools{position:fixed;right:12px;bottom:12px;z-index:2147483390;display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:6px;max-width:calc(100vw - 24px);box-sizing:border-box;border:1px solid rgba(255,255,255,.22);border-radius:12px;background:#1c1c2b;color:#fff;box-shadow:0 6px 18px #0004;font:600 13px/1.3 system-ui}.mb-report-tools button{font:inherit;color:inherit;border:1px solid #ffffff40;border-radius:8px;padding:7px 10px;background:transparent;cursor:pointer}.mb-report-tools button[aria-pressed="true"]{background:#ec0f7c;border-color:#ec0f7c}.mb-report-tools button:focus-visible{outline:3px solid #1cb0f6;outline-offset:2px}';
 (document.head||document.documentElement).appendChild(style);document.body.appendChild(tools);fallbackTools=tools;
 const buttons=new Map();const select=id=>{cursor?.usar?.(id);sync();};
 function sync(){if(!fallbackTools)return;const active=cursor?.atual?.()||'interagir';for(const [id,button] of buttons)button.setAttribute('aria-pressed',String(id===active));}
 /* 261017 WP2: a barra de reserva mostra as 4 ferramentas (Aprovar e Desenhar também ficam marcadas quando ativas) e a dica do gesto de segurar. */
 const group=document.createElement('span');group.className='mb-report-grupo cf-ui';tools.appendChild(group);
 const labels={comentar:'Comentar neste relatório: clique no ponto desejado',aprovar:'Aprovar um trecho: clique nele',desenhar:'Desenhar sobre o relatório',interagir:'Interagir com o relatório'};
 for(const [id,label] of [['comentar','Comentar'],['aprovar','Aprovar'],['desenhar','Desenhar'],['interagir','Interagir']]){const button=document.createElement('button');button.type='button';button.className='cf-ui';button.textContent=label;button.setAttribute('aria-label',labels[id]);button.addEventListener('click',()=>select(id));group.appendChild(button);buttons.set(id,button);}
 const hint=document.createElement('small');hint.className='mb-report-dica cf-ui';hint.textContent='segure 0,4 s para mais ferramentas';tools.appendChild(hint);
 fallbackStarting=true;try{cursor=window.CursorFerramentas.iniciar({modo:'local',chip:false,chave:'mb-report-notas:'+META.fid+':'+META.hash,chaveDesenhos:'mb-report-desenhos:'+META.fid+':'+META.hash,chaveAprovacoes:'mb-report-aprovacoes:'+META.fid+':'+META.hash,aoMudar:sync});if(!cursor||typeof cursor.usar!=='function'||typeof cursor.atual!=='function'){cursor=null;throw new Error('Report comment controls unavailable');}}finally{fallbackStarting=false;}
 sync();let bar=null;
 function position(){if(fallbackTools!==tools)return;const next=document.querySelector('.dr-barra');if(next!==bar){observer?.disconnect();bar=next;if(bar)observer?.observe(bar);}let bottom=12;if(bar){const rect=bar.getBoundingClientRect();if(rect.height&&rect.bottom>innerHeight-80)bottom=Math.max(12,innerHeight-rect.top+8);}tools.style.bottom=Math.min(bottom,Math.max(12,innerHeight-tools.offsetHeight-12))+'px';}
 const observer=typeof ResizeObserver==='function'?new ResizeObserver(position):null;
 const domObserver=typeof MutationObserver==='function'?new MutationObserver(position):null;domObserver?.observe(document.body,{childList:true,subtree:true});
 window.addEventListener('resize',position);fallbackCleanup=()=>{window.removeEventListener('resize',position);observer?.disconnect();domObserver?.disconnect();style.remove();};position();
}
function commentFailure(){fallbackCleanup?.();fallbackCleanup=null;const warning=document.createElement('p');warning.className='cf-ui';warning.setAttribute('role','alert');warning.style.margin='0';warning.textContent='Comentários indisponíveis nesta página. O relatório continua disponível.';if(fallbackTools){fallbackTools.replaceChildren(warning);}else{warning.style.cssText='position:fixed;right:12px;bottom:12px;max-width:calc(100vw - 24px);padding:10px;border-radius:8px;background:#1c1c2b;color:#fff;font:13px system-ui;z-index:2147483500';document.body?.appendChild(warning);}}
document.addEventListener('click',event=>{
 const element=event.target instanceof Element?event.target:null;if(!element)return;
 const link=element.closest('a');if(link){const local=link.getAttribute('data-mb-local'),external=link.getAttribute('data-mb-external');if(local||external){event.preventDefault();event.stopImmediatePropagation();if(event.isTrusted)send(local?'open-local':'open-external',local?{path:local}:{url:external});return;}}
 const button=element.closest('button');if(button&&['dr-finalizar','dr-enviar','dr-term-enviar'].includes(button.id)&&decisions?.anexosPendentes?.()){event.preventDefault();event.stopImmediatePropagation();ackToast('Espere os prints terminarem; até 6 por envio. Rascunho preservado.',false);return;}if(button&&button.id==='dr-enviar'){setTimeout(()=>{if(decisions){send('feedback',{kind:'decisions',finalizado:true,respostas:decisions.respostas(),notas:cursor&&typeof cursor.notas==='function'?notes(savedOnly(cursor.notas())):[],resumo_texto:trim(decisions.resumoTexto?.(),30000),resumo_respostas:trim(decisions.resumoRespostas?.(),30000)});}},0);}
},true);
document.addEventListener('submit',e=>{e.preventDefault();},true);
window.MegaBrainReport=Object.freeze({saveFeedback(value){if(value&&typeof value==='object')send('feedback',value);},dispatch(value){if(value&&typeof value==='object'){if(decisions?.anexosPendentes?.()){ackToast('Espere os prints terminarem; até 6 por envio. Rascunho preservado.',false);return;}send('dispatch',value.respostas&&decisions?{...value,respostas:decisions.respostas(),resumo_texto:trim(decisions.resumoTexto?.(),30000)}:value);}}});
async function start(){if(started)return;started=true;const scripts=[...document.querySelectorAll('script[type="application/x-megabrain-script"]')];for(const original of scripts){const s=document.createElement('script');if(original.dataset.mbType==='module')s.type='module';s.textContent=original.textContent;if(s.type==='module'){await new Promise(resolve=>{s.onload=resolve;s.onerror=resolve;original.replaceWith(s);});}else original.replaceWith(s);}document.dispatchEvent(new Event('DOMContentLoaded',{bubbles:true}));if(document.readyState==='complete')window.dispatchEvent(new Event('load'));setTimeout(()=>{let commentError='';try{ensureCursor();}catch{commentError='Comentários indisponíveis nesta página.';commentFailure();}finally{send('loaded',{comments_available:!commentError&&!!cursor,comment_error:commentError});}},0);}
function migrarVersoesAntigas(){
 /* Notas e rascunhos gravados sob o hash de uma versão anterior voltam na
    versão atual. A âncora exata pode não resolver mais, mas a posição (px/py)
    e o rótulo (onde) continuam dizendo onde a nota estava e o que significava.
    Só namespaces do app (mb-*) e sufixo de versão de 64 hex; chaves de
    relatório com nome estável não mudam de sufixo e não são tocadas. */
 const hex64=/^[a-f0-9]{64}$/;let mudou=false;
 for(const chave of Object.keys(memory)){
  if(!chave.startsWith('mb-'))continue;
  const i=chave.lastIndexOf(':');if(i<0)continue;
  const hash=chave.slice(i+1);
  if(!hex64.test(hash)||hash===META.hash)continue;
  const alvo=chave.slice(0,i+1)+META.hash;
  try{
   const antigo=JSON.parse(memory[chave]);let atual=JSON.parse(memory[alvo]||'null');
   if(Array.isArray(antigo)){
    if(!Array.isArray(atual))atual=[];
    const vistos=new Set(atual.map(v=>String((v&&(v.id||v.chave))||'')));
    for(const item of antigo){const id=String((item&&(item.id||item.chave))||'');if(!id||vistos.has(id))continue;item.migrada_de=hash.slice(0,8);vistos.add(id);atual.push(item);}
   }else if(antigo&&typeof antigo==='object'){
    if(!atual||typeof atual!=='object'||Array.isArray(atual))atual={};
    Object.assign(antigo,atual);atual=antigo; // recibos: os da versão antiga continuam válidos
   }else continue;
   memory[alvo]=JSON.stringify(atual);delete memory[chave];mudou=true;
  }catch{}
 }
 if(mudou)send('draft',{storage:state()});
}
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||!m||m.channel!=='megabrain-report-bridge'||m.token!==META.token||m.fid!==META.fid||m.hash!==META.hash)return;if(!Array.isArray(m.catalogo)||!Array.isArray(m.vendors)||!m.data||typeof m.data!=='object')return;const detail={catalogo:m.catalogo,vendors:m.vendors,data:m.data};window.MegaBrainBridge=detail;window.dispatchEvent(new CustomEvent('mb-report-bridge',{detail}));});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||!m||m.channel!=='megabrain-report-restore'||m.token!==META.token||m.fid!==META.fid||m.hash!==META.hash)return;const saved=m.storage;if(saved&&typeof saved==='object'&&!Array.isArray(saved)){for(const [k,v] of Object.entries(saved).slice(0,100))if(k.length<=250&&typeof v==='string'&&v.length<=50000)memory[k]=v;migrarVersoesAntigas();}start();});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||!m||m.channel!=='megabrain-report-dispatch-result'||m.token!==META.token||m.fid!==META.fid)return;window.dispatchEvent(new CustomEvent('mb-dispatch-result',{detail:{ok:m.ok===true,message:typeof m.message==='string'?m.message.slice(0,600):''}}));});
/* 261017 WP2: o app confirma se a nota chegou ao projeto (megabrain-report-ack). */
let ackBox=null,ackTimer=0;
function ackToast(text,ok){if(!document.body)return;document.querySelectorAll('.cf-toast').forEach(t=>{t.hidden=true;});if(!ackBox||!ackBox.isConnected){ackBox=document.createElement('div');ackBox.className='mb-report-ack cf-ui';ackBox.setAttribute('role','status');ackBox.setAttribute('aria-live','polite');ackBox.style.cssText='position:fixed;left:50%;top:16px;transform:translateX(-50%);z-index:2147483600;max-width:calc(100vw - 24px);box-sizing:border-box;padding:8px 14px;border-radius:999px;color:#fff;font:600 13px/1.3 system-ui;box-shadow:0 6px 18px #0004;pointer-events:none';document.body.appendChild(ackBox);}ackBox.textContent=text;ackBox.style.background=ok?'#0f7a4c':'#b3261e';ackBox.style.display='block';clearTimeout(ackTimer);ackTimer=setTimeout(()=>{if(ackBox)ackBox.style.display='none';},ok?3500:8000);}
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==HOST_ORIGIN||!m||m.channel!=='megabrain-report-ack'||m.token!==META.token||m.fid!==META.fid)return;const ok=m.ok===true,ids=Array.isArray(m.ids)?m.ids.slice(0,150).map(String):[];const text=typeof m.message==='string'&&m.message.trim()?m.message.slice(0,160):(ok?'Nota enviada ao projeto ✓':'Nota não enviada · tente de novo');ackToast(text,ok);window.dispatchEvent(new CustomEvent('mb-report-ack',{detail:{ok,ids,notas:notes(m.notas),message:text}}));});
document.addEventListener('DOMContentLoaded',()=>send('ready',{}),{once:true});
})();
"""


def wrapper_report(fid, token, storage=None, expected_hash=None):
    """Authenticated envelope. Child is opaque and has no API/network access."""
    _identity(fid, token)
    if expected_hash is not None and not re.fullmatch(r'[a-f0-9]{64}', str(expected_hash)):
        raise ValueError('Versão de relatório inválida.')
    meta = _json({'fid': fid, 'token': token})
    if storage is not None:
        if not isinstance(storage, dict): raise ValueError('Rascunho de relatório inválido.')
        storage = {str(k): v for k, v in list(storage.items())[:100] if len(str(k)) <= 250 and isinstance(v, str) and len(v) <= 50000}
        if len(_json(storage)) > 128000: raise ValueError('Rascunho de relatório acima do limite.')
    initial = _json(storage)
    version = '&amp;version=' + expected_hash if expected_hash else ''
    expected = _json(expected_hash)
    return '''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Relatório no MegaBrain</title><style>html,body,iframe{margin:0;width:100%;height:100%;border:0}body{overflow:hidden}#report-error{position:absolute;inset:0;padding:30px;background:#17131e;color:#f2e5ee;font:16px/1.6 system-ui}#report-error[hidden]{display:none}</style><iframe id="report" title="Relatório interativo isolado" sandbox="allow-scripts allow-forms" referrerpolicy="no-referrer" src="/api/reports/'''+fid+'/render?ticket='+token+version+'''"></iframe><p id="report-error" role="status" hidden></p><script>
(()=>{'use strict';const META='''+meta+''',initialStorage='''+initial+''',inner=document.getElementById('report');let hash='''+expected+r''';
const size=value=>{try{return JSON.stringify(value).length;}catch{return Infinity;}};
const attachmentPending=new Map(),attachmentMax=8*1024*1024,attachmentTypes=['image/png','image/jpeg','image/gif','image/webp'];
window.addEventListener('message',event=>{const m=event.data;if(event.source!==inner.contentWindow||event.origin!=='null'||!m||!['mb-attachment-request','mb-attachment-preview-request'].includes(m.channel)||m.token!==META.token||m.fid!==META.fid||!hash||m.hash!==hash||typeof m.requestId!=='string'||!/^[A-Za-z0-9_-]{1,100}$/.test(m.requestId)||attachmentPending.has(m.requestId)||attachmentPending.size>=12)return;
 const preview=m.channel==='mb-attachment-preview-request';let value;
 if(preview){const a=m.attachment;if(!a||typeof a.id!=='string'||a.id.length>160||typeof a.url!=='string'||!/^\/api\/projects\/[a-zA-Z0-9_-]+\/attachments\/[a-zA-Z0-9_-]+$/.test(a.url)||size(a)>12000)return;value={attachment:a};}
 else{const f=m.file;if(!f||typeof f.name!=='string'||f.name.length>240||!attachmentTypes.includes(f.mime)||!(f.data instanceof ArrayBuffer)||f.data.byteLength<=0||f.data.byteLength>attachmentMax)return;value={file:{name:f.name,mime:f.mime,data:f.data}};}
 const timer=setTimeout(()=>attachmentPending.delete(m.requestId),30000);attachmentPending.set(m.requestId,{preview,timer});parent.postMessage({...META,hash,channel:m.channel,requestId:m.requestId,...value},location.origin,preview?[]:[value.file.data]);
});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==location.origin||!m||!['mb-attachment-result','mb-attachment-preview-result'].includes(m.channel)||m.token!==META.token||m.fid!==META.fid||m.hash!==hash)return;const pending=attachmentPending.get(m.requestId);if(!pending||pending.preview!==(m.channel==='mb-attachment-preview-result'))return;let value;if(typeof m.error==='string')value={error:m.error.slice(0,400)};else if(pending.preview){if(typeof m.preview!=='string'||m.preview.length>Math.ceil(attachmentMax/3)*4+100||!/^data:image\/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(m.preview))return;value={preview:m.preview};}else{if(!m.attachment||size(m.attachment)>12000)return;value={attachment:m.attachment};}attachmentPending.delete(m.requestId);clearTimeout(pending.timer);inner.contentWindow.postMessage({...META,hash,channel:m.channel,requestId:m.requestId,...value},'*');});
window.addEventListener('message',event=>{const m=event.data;
 if(event.source!==inner.contentWindow||event.origin!=='null'||!m||m.channel!=='megabrain-report'||m.token!==META.token||m.fid!==META.fid||!/^([a-f0-9]{64})$/.test(m.hash)||size(m)>160000)return;
 if(hash&&hash!==m.hash){inner.hidden=true;const error=document.getElementById('report-error');error.hidden=false;error.textContent='O relatório mudou durante a abertura. Reabra o resultado para carregar a versão atual; suas respostas anteriores continuam preservadas.';parent.postMessage({...META,channel:'megabrain-report',kind:'stale',hash,payload:{message:error.textContent}},location.origin);return;}hash=m.hash;const key='megabrain-report:'+META.fid+':'+hash;
 if(m.kind==='ready'){let storage=initialStorage;if(storage===null){storage={};try{storage=JSON.parse(sessionStorage.getItem(key)||'{}');}catch{}}inner.contentWindow.postMessage({channel:'megabrain-report-restore',...META,hash,storage},'*');}
 else if(m.kind==='draft'){const s=m.payload?.storage;if(!s||typeof s!=='object'||Array.isArray(s)||size(s)>128000)return;try{sessionStorage.setItem(key,JSON.stringify(s));}catch{}}
 else if(!['feedback','loaded','open-local','open-external','dispatch','attachment-state','project-control'].includes(m.kind))return;
 parent.postMessage({...m,...META,hash},location.origin);
});
window.addEventListener('message',event=>{const m=event.data;if(event.source!==parent||event.origin!==location.origin||!m||!['megabrain-report-dispatch-result','megabrain-report-ack','megabrain-report-bridge','megabrain-report-control-result'].includes(m.channel)||m.fid!==META.fid||m.token!==META.token)return;if(m.channel==='megabrain-report-bridge'&&(!hash||m.hash!==hash||size(m)>128000))return;inner.contentWindow.postMessage(m,'*');});
})();</script></html>'''


def render_report(path, root, fid, token):
    """Read a report and inline permitted project-local resources, preserving source."""
    _identity(fid, token)
    root = Path(root).resolve(strict=True)
    path = confined_file(path, root, suffixes={'.html', '.htm'}, limit=MAX_REPORT)
    source = path.read_bytes()
    meta = {'fid': fid, 'token': token, 'hash': hashlib.sha256(source).hexdigest()}
    # Inline source data is covered by MAX_REPORT. Keep the independent budget
    # for additional local resources; large self-contained HTML must not spend it.
    budget = [0]

    def resource(value, suffixes, base=path.parent):
        parsed = urlsplit(value or '')
        if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith(('/', '\\')):
            return None
        try:
            candidate = confined_file(base / unquote(parsed.path), root, suffixes=suffixes)
            budget[0] += candidate.stat().st_size
            if budget[0] > MAX_BUNDLE:
                return None
            return candidate
        except (ValueError, OSError):
            return None

    def data_url(p):
        mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        return 'data:' + mime + ';base64,' + base64.b64encode(p.read_bytes()).decode('ascii')

    def local_link(value):
        """Catalogue legacy file: URIs and absolute project links remain usable."""
        value = value or ''
        parsed = urlsplit(value)
        try:
            if parsed.scheme == 'file' and parsed.netloc in {'', 'localhost'}:
                candidate = Path(url2pathname(unquote(parsed.path)))
            elif Path(value).is_absolute():
                candidate = Path(value)
            elif not parsed.scheme and not parsed.netloc and parsed.path and not parsed.path.startswith(('/', '\\')):
                candidate = path.parent / unquote(parsed.path)
            else:
                return None
            # Links identify another document; they never inline or spend the
            # additional resource budget. HTML gets the report limit here too.
            limit = MAX_REPORT if candidate.suffix.lower() in {'.html', '.htm'} else MAX_RESOURCE
            return confined_file(candidate, root, limit=limit)
        except (ValueError, OSError):
            return None

    def css(content, base):
        # CSS cannot import other code; local font/image URLs may be embedded.
        content = re.sub(r'@import\s+(?:url\([^)]*\)|[\"\'][^\"\']*[\"\'])[^;]*;', '', content, flags=re.I)
        def replace(match):
            value = next(group for group in match.groups() if group is not None).strip()
            # Embedded visual resources and SVG paint references belong to the
            # document itself; preserve their spelling, including quoted ')'.
            if value.startswith('#') or re.match(r'^data:(?:image/|font/)', value, re.I):
                return match.group(0)
            p = resource(value, MEDIA, base)
            return 'url("' + (data_url(p) if p else 'about:blank') + '")'
        return re.sub(r'''url\(\s*(?:"([^"\\]*(?:\\.[^"\\]*)*)"|'([^'\\]*(?:\\.[^'\\]*)*)'|([^)]*?))\s*\)''', replace, content, flags=re.I)

    class Report(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=False)
            self.out = []; self.external_script = False; self.style = False

        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if tag in {'base', 'iframe', 'frame', 'frameset', 'object', 'embed'} or tag == 'meta' and values.get('http-equiv'):
                return
            if tag == 'script':
                script_type = str(values.get('type') or '').casefold()
                if values.get('src') is not None:
                    p = resource(values['src'], {'.js', '.mjs'})
                    if p:
                        code = re.sub(r'</script', r'<\\/script', p.read_text(encoding='utf-8-sig'), flags=re.I)
                        self.out.append('<script type="application/x-megabrain-script" data-mb-type="'+('module' if script_type == 'module' else '')+'">'+code+'</script>')
                    self.external_script = True
                    return
                if script_type not in {'', 'module', 'text/javascript', 'application/javascript', 'text/ecmascript', 'application/ecmascript'}:
                    self.out.append('<script type="'+html.escape(script_type, quote=True)+'">')
                else:
                    self.out.append('<script type="application/x-megabrain-script" data-mb-type="'+('module' if script_type == 'module' else '')+'">')
                return
            if tag == 'link':
                p = resource(values.get('href'), {'.css'}) if str(values.get('rel', '')).casefold() == 'stylesheet' else None
                if p:
                    style = css(p.read_text(encoding='utf-8-sig'), p.parent)
                    self.out.append('<style>'+re.sub(r'</style', r'<\\/style', style, flags=re.I)+'</style>')
                return
            rendered = []
            for name, value in attrs:
                if name in {'srcdoc', 'srcset', 'ping', 'integrity', 'crossorigin', 'target', 'download'} or name.startswith('data-mb-'):
                    continue
                if name == 'style' and value:
                    value = css(value, path.parent)
                if name in {'src', 'href', 'xlink:href', 'action', 'formaction', 'poster', 'data'}:
                    if value and value.startswith('#'):
                        pass
                    elif tag == 'a' and name == 'href':
                        parsed = urlsplit(value or '')
                        local = local_link(value)
                        if local:
                            rendered.append('data-mb-local="'+html.escape(local.relative_to(root).as_posix(), quote=True)+'"')
                        elif parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                            rendered.append('data-mb-external="'+html.escape(value, quote=True)+'"')
                        value = '#'
                    elif name in {'src', 'poster', 'href', 'xlink:href'} and (p := resource(value, MEDIA)):
                        value = data_url(p)
                    elif value and re.match(r'^data:(?:image/|audio/|video/|font/)', value, re.I) and name in {'src', 'poster'}:
                        pass
                    else:
                        value = 'about:blank'
                rendered.append(name if value is None else name+'="'+html.escape(value, quote=True)+'"')
            self.out.append('<'+tag+(' '+' '.join(rendered) if rendered else '')+'>')
            if tag == 'style': self.style = True

        def handle_startendtag(self, tag, attrs):
            self.handle_starttag(tag, attrs)
            # SVG shapes are not HTML void elements. Expanding <rect/> to an
            # open <rect> makes following text its child and loses its render.
            if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
                self.handle_endtag(tag)

        def handle_endtag(self, tag):
            if tag == 'script' and self.external_script:
                self.external_script = False; return
            if tag == 'style': self.style = False
            if tag not in {'base', 'iframe', 'frame', 'frameset', 'object', 'embed'}:
                self.out.append('</'+tag+'>')

        def handle_data(self, data):
            if not self.external_script:
                self.out.append(css(data, path.parent) if self.style else data)
        def handle_entityref(self, name): self.out.append('&'+name+';')
        def handle_charref(self, name): self.out.append('&#'+name+';')
        def handle_comment(self, data): self.out.append('<!--'+data+'-->')
        def handle_decl(self, decl): self.out.append('<!'+decl+'>')

    parser = Report(); parser.feed(source.decode('utf-8-sig', errors='replace')); parser.close()
    result = ''.join(parser.out)
    bootstrap = '<script>'+BOOTSTRAP.replace('__META__', _json(meta))+'</script>'
    # Every HTML/prototype has local comments. Legacy initializers keep their
    # configuration; the bootstrap creates a fallback only when none started.
    cursor_source = Path(__file__).resolve().parents[2] / 'motor/modelos/interacoes/261010_cursor-ferramentas/cursor-ferramentas.js'
    try:
        cursor_code = re.sub(r'</script', r'<\\/script', cursor_source.read_text(encoding='utf-8-sig'), flags=re.I)
    except (OSError, UnicodeError):
        # Preserve the document when a deployment misses the shared asset.
        # The bootstrap shows an honest warning and still acknowledges load.
        cursor_code = ''
    if cursor_code:
        bootstrap += '<script>' + cursor_code + '</script>'
    # Shim comes before every original script; original scripts run after restore.
    head = re.search(r'<head(?:\s[^>]*)?>', result, flags=re.I)
    if head:
        result = result[:head.end()] + bootstrap + result[head.end():]
    else:
        result = '<!doctype html><meta charset="utf-8">' + bootstrap + result
    return result
