import type {Preview} from './types';

/** One live editor per document. Historical entries remain in the source workspace. */
export function uniqueResponseViews(value:unknown,validUrl:(url:string)=>unknown):Preview[]{
  if(!Array.isArray(value))return [];
  const seen=new Set<string>();const result:Preview[]=[];
  for(const p of value){
    if(!p||typeof p.id!=='string'||typeof p.url!=='string'||typeof p.title!=='string'||!validUrl(p.url))continue;
    const key=`${p.project_id||''}:${p.id}`;
    if(seen.has(key))continue;
    seen.add(key);result.push(p);
  }
  return result;
}
