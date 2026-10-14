let csrf = '';
export class ApiError extends Error { status:number; constructor(status:number,message:string){super(message);this.status=status;} }
export function setCsrf(value:string){csrf=value;}
export type MutationAttempt={fingerprint:string;key:string};
export function mutationKey(holder:{current:MutationAttempt|null},payload:unknown){const fingerprint=JSON.stringify(payload);if(holder.current?.fingerprint!==fingerprint)holder.current={fingerprint,key:crypto.randomUUID()};return holder.current.key;}
export async function api<T>(path:string,method='GET',body?:unknown,requestKey?:string):Promise<T>{
  const response=await fetch(`/api${path}`,{method,credentials:'same-origin',headers:{...(body!==undefined?{'Content-Type':'application/json'}:{}),...(method!=='GET'&&csrf?{'X-MB-CSRF':csrf}:{}),...(requestKey?{'Idempotency-Key':requestKey}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});
  const data=await response.json().catch(()=>null);
  if(!response.ok){const message=typeof data?.detail==='string'?data.detail:typeof data?.error==='string'?data.error:response.status===409?'Existe uma versão mais recente salva em outro dispositivo.':response.status===401?'Conecte este dispositivo ao seu MegaBrain.':`Não foi possível concluir (${response.status}).`;throw new ApiError(response.status,message);}
  return data as T;
}
export async function session(){const s=await api<{authenticated:boolean;csrf:string;remote:boolean;version:string}>('/session');setCsrf(s.csrf);return s;}
export async function pair(code:string){await api('/pair','POST',{code});return session();}
export function safeUrl(value?:string):string|null{if(!value)return null;try{const u=new URL(value,window.location.origin);return ['http:','https:'].includes(u.protocol)?u.href:null;}catch{return null;}}
export function fileUrl(id:string){return `/api/files/${encodeURIComponent(id)}`;}
// The fixed server wrapper supports its isolated interactive child.
// Catalogued local files retain origin for authenticated images, without scripts
// or forms; their server CSP also blocks scripts. Other URLs stay opaque.
export function previewSandbox(value:string):string{
  try{
    const url=new URL(value,window.location.origin);
    const trusted=url.origin===window.location.origin&&!url.username&&!url.password&&!url.search&&!url.hash&&/^\/api\/jobs\/[A-Za-z0-9_-]+\/preview\/[A-Za-z0-9_-]+$/.test(url.pathname);
    const localFile=url.origin===window.location.origin&&!url.username&&!url.password&&!url.search&&!url.hash&&/^\/api\/files\/[a-f0-9]{20}$/.test(url.pathname);
    return trusted?'allow-scripts allow-same-origin allow-forms':localFile?'allow-same-origin':'';
  }catch{return '';}
}
