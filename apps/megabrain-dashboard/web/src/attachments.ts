import {api} from './api';

export type Attachment={id:string;path:string;name:string;mime:string;size:number;url:string};
export const ATTACHMENT_LIMIT=6;
export const ATTACHMENT_BYTES=8*1024*1024;
export const ATTACHMENT_MIMES=['image/png','image/jpeg','image/gif','image/webp'];
export const ATTACHMENT_ACCEPT=ATTACHMENT_MIMES.join(',');
const URL_PATH=/^\/api\/projects\/[^/?#]+\/attachments\/([A-Za-z0-9_-]{1,128})$/;

/** Only short server references enter drafts; never copy a File/data URL. */
export function normalizeAttachments(value:unknown):Attachment[]{
  if(!Array.isArray(value))return [];
  const out:Attachment[]=[];
  for(const v of value){
    if(!v||typeof v!=='object'||Array.isArray(v))continue;
    const a=v as Record<string,unknown>;
    if(typeof a.id!=='string'||typeof a.path!=='string'||!a.path||a.path.length>2048||/^data:/i.test(a.path)||typeof a.name!=='string'||a.name.length>255||typeof a.mime!=='string'||!ATTACHMENT_MIMES.includes(a.mime)||typeof a.size!=='number'||!Number.isInteger(a.size)||a.size<1||a.size>ATTACHMENT_BYTES||typeof a.url!=='string'||URL_PATH.exec(a.url)?.[1]!==a.id)continue;
    if(out.some(v=>v.id===a.id&&v.url===a.url))continue;
    out.push({id:a.id,path:a.path,name:a.name,mime:a.mime,size:a.size,url:a.url});
    if(out.length===ATTACHMENT_LIMIT)break;
  }
  return out;
}
export function attachmentFingerprint(value:unknown):string{return JSON.stringify(normalizeAttachments(value).map(a=>[a.id,a.path,a.name,a.mime,a.size,a.url]));}
export function validateAttachment(file:{type:string;size:number}){
  if(!ATTACHMENT_MIMES.includes(file.type))throw new Error('Escolha um print PNG, JPEG, GIF ou WebP.');
  if(!file.size||file.size>ATTACHMENT_BYTES)throw new Error('Cada print deve ter até 8 MiB. O rascunho continua aqui.');
}
export function attachmentForProject(pid:string,value:unknown):Attachment{
  const a=normalizeAttachments([value])[0];
  if(!a||a.url!==`/api/projects/${encodeURIComponent(pid)}/attachments/${a.id}`)throw new Error('O print não pertence a este projeto.');
  return a;
}
function base64(bytes:ArrayBuffer){
  const array=new Uint8Array(bytes);let binary='';
  for(let i=0;i<array.length;i+=32768)binary+=String.fromCharCode(...array.subarray(i,i+32768));
  return btoa(binary);
}
export async function uploadAttachment(pid:string,file:File):Promise<Attachment>{
  if(!pid)throw new Error('Abra um projeto para anexar o print.');
  validateAttachment(file);
  const result=await api<{attachment:Attachment}>(`/projects/${encodeURIComponent(pid)}/attachments`,'POST',{name:file.name.slice(0,255),mime:file.type,data:base64(await file.arrayBuffer())});
  return attachmentForProject(pid,result.attachment);
}
export async function previewAttachment(pid:string,value:Attachment):Promise<string>{
  const a=attachmentForProject(pid,value);
  const response=await fetch(a.url,{credentials:'same-origin'});
  if(!response.ok)throw new Error('Não foi possível carregar a prévia do print.');
  const length=Number(response.headers.get('content-length')||0);
  if(length>ATTACHMENT_BYTES)throw new Error('Prévia maior que 8 MiB.');
  if(!ATTACHMENT_MIMES.includes((response.headers.get('content-type')||'').split(';')[0]))throw new Error('Tipo de prévia inválido.');
  const reader=response.body?.getReader();if(!reader)throw new Error('Prévia indisponível.');
  let size=0;const chunks:Uint8Array<ArrayBuffer>[]=[];
  try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>ATTACHMENT_BYTES)throw new Error('Prévia maior que 8 MiB.');chunks.push(part.value);}}finally{await reader.cancel().catch(()=>{});}
  const blob=new Blob(chunks,{type:a.mime});
  return await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result));r.onerror=()=>reject(new Error('Não foi possível ler a prévia.'));r.readAsDataURL(blob);});
}
