// Merge independent saves. Conflicting human edits still require a decision.
type Doc=Record<string,unknown>;
const plain=(v:unknown):v is Doc=>Boolean(v&&typeof v==='object'&&!Array.isArray(v));
// Key order is not an edit: the server, the grid and the merge itself may list the same keys in another order.
const canon=(v:unknown):unknown=>Array.isArray(v)?v.map(canon):plain(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canon(v[k])])):v;
const same=(a:unknown,b:unknown)=>JSON.stringify(canon(a))===JSON.stringify(canon(b));
// List items with an identity (text, number, key, layout i, project_id+id) merge one by one.
const ident=(v:unknown):string|null=>typeof v==='string'||typeof v==='number'?'v:'+JSON.stringify(v):!plain(v)?null:typeof v.key==='string'?'k:'+v.key:typeof v.i==='string'?'i:'+v.i:typeof v.id==='string'||typeof v.id==='number'?`d:${String(v.project_id??'')}:${String(v.id)}`:null;
function index(list:unknown[]):Map<string,unknown>|null{const map=new Map<string,unknown>();for(const item of list){const id=ident(item);if(id===null||map.has(id))return null;map.set(id,item);}return map;}
// prefer:'local' keeps this window's value wherever both sides changed the same thing (the person chose "save my draft").
export function mergeWorkspace(base:Doc,local:Doc,remote:Doc,opts:{prefer?:'local'}={}):Doc|null{
  let conflict=false;
  function merge(a:unknown,b:unknown,c:unknown,key=''):unknown{
    if(same(b,c))return b;if(same(a,b))return c;if(same(a,c))return b;
    if((key==='returnCursor'||key==='notificationReadId')&&typeof b==='number'&&typeof c==='number')return Math.max(b,c);
    // A section both sides created after the base (e.g. appearance) starts empty and merges key by key.
    if(plain(b)&&plain(c)&&(a===undefined||a===null||plain(a))){
      const aa=plain(a)?a:{};
      return Object.fromEntries([...new Set([...Object.keys(aa),...Object.keys(b),...Object.keys(c)])].map(k=>[k,merge(aa[k],b[k],c[k],k)]));
    }
    if(Array.isArray(b)&&Array.isArray(c)&&(a===undefined||a===null||Array.isArray(a))){
      const list=mergeList(Array.isArray(a)?a:[],b,c);if(list)return list;
      if(opts.prefer==='local'){conflict=true;return keepLocalList(Array.isArray(a)?a:[],b,c);}
    }
    conflict=true;return b;
  }
  // "Save my draft" on a list both sides changed: this window's list, plus the items only the other window added.
  function keepLocalList(a:unknown[],b:unknown[],c:unknown[]):unknown[]{
    const A=index(a),B=index(b),C=index(c);if(!A||!B||!C)return b;
    return [...b,...[...C.entries()].filter(([id])=>!B.has(id)&&!A.has(id)).map(([,item])=>item)];
  }
  // Additions from both sides stay; a removal wins over an untouched item. The same item changed differently,
  // removed on one side and edited on the other, or reordered differently on both sides is a real conflict.
  function mergeList(a:unknown[],b:unknown[],c:unknown[]):unknown[]|null{
    const A=index(a),B=index(b),C=index(c);if(!A||!B||!C)return null;
    const out=new Map<string,unknown>();
    for(const id of new Set([...B.keys(),...C.keys()])){
      const inB=B.has(id),inC=C.has(id);
      if(inB&&inC){out.set(id,merge(A.get(id),B.get(id),C.get(id)));continue;}
      const kept=inB?B.get(id):C.get(id);
      if(!A.has(id))out.set(id,kept);else if(!same(A.get(id),kept))return null;
    }
    // Layout items are placed by x/y, so their order is free; other lists keep the side that reordered them.
    const common=[...A.keys()].filter(id=>B.has(id)&&C.has(id)),seq=(m:Map<string,unknown>)=>JSON.stringify([...m.keys()].filter(id=>common.includes(id)));
    const free=[...out.keys()].every(id=>id.startsWith('i:'));
    const lead=free||seq(C)===seq(A)||seq(B)===seq(C)?B:seq(B)===seq(A)?C:null;if(!lead)return null;
    const ids=[...lead.keys()].filter(id=>out.has(id));for(const id of out.keys())if(!ids.includes(id))ids.push(id);
    return ids.map(id=>out.get(id));
  }
  const result=merge(base,local,remote) as Doc;return conflict&&opts.prefer!=='local'?null:result;
}

export type Saved<W>={revision:number;data:W};
export type SaveRound<W>={saved:Saved<W>;sent:W;from:W;serial:number};
// Every retry merged cleanly but another window kept saving first: try again later, it is not a conflict.
export class WorkspaceBusy extends Error{}
// Save the newest local state. A stale revision (409) re-reads the server and retries with the newest
// local data, edits made while the request was in flight included. Only a real conflict (the same key
// changed differently on both sides) rethrows the 409 for the person to decide.
// `from` is the local state `sent` was built from: later edits rebase with mergeWorkspace(from,current,saved.data).
export async function saveWorkspace<W extends Doc>(io:{base:W;local:()=>{serial:number;revision:number;data:W};put:(revision:number,data:W)=>Promise<Saved<W>>;get:()=>Promise<Saved<W>>;stale:(e:unknown)=>boolean;attempts?:number;prefer?:'local';unconfirmed?:W}):Promise<SaveRound<W>>{
  let {serial,revision,data}=io.local();let from=data;
  for(let attempt=1;;attempt++){
    try{return {saved:await io.put(revision,data),sent:data,from,serial};}
    catch(e){
      if(!io.stale(e))throw e;
      if(attempt>=(io.attempts??4))throw new WorkspaceBusy('Outra janela continua salvando; nova tentativa em seguida.');
      const remote=await io.get(),latest=io.local();
      // A payload whose answer never came (connection lost, 5xx) may already be saved: then it is this window's own
      // write, the base of the merge, not another window's change.
      const base=io.unconfirmed&&same(remote.data,io.unconfirmed)?io.unconfirmed:io.base;
      const merged=mergeWorkspace(base,latest.data,remote.data,{prefer:io.prefer}) as W|null;
      if(!merged)throw e;
      serial=latest.serial;from=latest.data;data=merged;revision=remote.revision;
    }
  }
}

// 261016: what a failed save means for the person. Only 'conflict' asks for a decision; the others get their own notice.
export type SaveFailure='busy'|'conflict'|'offline'|'too-large'|'signed-out'|'error';
export function saveFailure(e:unknown):SaveFailure{
  if(e instanceof WorkspaceBusy)return 'busy';
  const status=e&&typeof e==='object'&&typeof (e as {status?:unknown}).status==='number'?(e as {status:number}).status:null;
  const message=e instanceof Error?e.message:String(e??'');
  // fetch rejects with a TypeError when the central does not answer at all (closed, restarting, network down).
  if(status===null)return e instanceof TypeError&&/fetch|network|load failed/i.test(message)?'offline':'error';
  if(status===409)return 'conflict';
  if(status===401)return 'signed-out';
  if(status===413||(status===400&&/grande demais/i.test(message)))return 'too-large';
  if(status===0||status===408||status===429||status>=500)return 'offline';
  return 'error';
}
// Waits between automatic retries while the central does not answer: 2 s, 4 s, 8 s, 16 s, then every 30 s.
export function retryDelay(attempt:number):number{return Math.min(30_000,1000*2**Math.max(1,attempt));}
// Size as the server counts it (Python json.dumps: UTF-8 plus ", " and ": " separators) and the heaviest top-level part.
export const WORKSPACE_LIMIT=300_000;
const utf8=(s:string)=>new TextEncoder().encode(s).length;
function separators(v:unknown):number{
  if(Array.isArray(v))return Math.max(0,v.length-1)+v.reduce((n:number,x)=>n+separators(x),0);
  if(!plain(v))return 0;
  const kept=Object.values(v).filter(x=>x!==undefined&&typeof x!=='function');
  return kept.length+Math.max(0,kept.length-1)+kept.reduce((n:number,x)=>n+separators(x),0);
}
export function workspaceWeight(data:Doc):{bytes:number;largest:string|null;largestBytes:number}{
  let largest:string|null=null,largestBytes=0;
  for(const [key,value] of Object.entries(data)){if(value===undefined)continue;const size=utf8(JSON.stringify(value))+separators(value);if(size>largestBytes){largest=key;largestBytes=size;}}
  return {bytes:utf8(JSON.stringify(data))+separators(data),largest,largestBytes};
}
