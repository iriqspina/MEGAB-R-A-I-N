import { fileUrl, safeUrl } from './api';
import type { Job, JobArtifact, JobFile, JobSource, JobStep, Preview } from './types';

export function presentedSteps(job:Job):JobStep[]{
  const observed=job.steps||[];
  // A legacy text-only record has a route snapshot, but no execution telemetry.
  // Do not retroactively label its planned stages as unexecuted tool work.
  const planned=job.execution_plan||observed.length?job.route?.stages.filter(s=>s.enabled!==false)||[]:[];
  const represented=new Set<string>();
  for(const step of observed){
    const original=planned.filter(stage=>step.id===stage.id||step.id.replace(/^\d+-/,'')===stage.id).sort((a,b)=>b.id.length-a.id.length)[0];
    if(original)represented.add(original.id);
  }
  const future:JobStep[]=planned.filter(stage=>!represented.has(stage.id)).map(stage=>({id:'planned:'+stage.id,title:stage.title,status:'pending',model:stage.model,kind:stage.capability}));
  const terminal=['completed','done','success','failed','error','cancelled','interrupted','partial'].includes(job.status);
  return [...observed,...future].map(step=>({...step,status:terminal&&step.status==='running'?'interrupted':terminal&&step.status==='pending'?'not_run':step.status}));
}

export const isOpenedPage=(source:JobSource)=>source.retrieved===true&&source.retrieval_kind==='page_fetch';
export function sourceStatus(source:JobSource){
  if(isOpenedPage(source))return 'Página aberta · consulta registrada';
  if(source.retrieval_kind==='search_result')return 'Resultado de busca · página não aberta';
  if(source.retrieval_kind==='cited_link')return 'Link citado · página não aberta';
  return 'Citação · abertura da página não comprovada';
}

export function privateFileUrl(url?:string,id?:string){
  const value=url?safeUrl(url):id?fileUrl(id):null;
  if(!value)return null;
  const parsed=new URL(value,window.location.origin);
  return parsed.origin===window.location.origin&&!parsed.username&&!parsed.password?parsed.href:null;
}
export function artifactPreview(item:JobArtifact):Preview|null{
  const url=privateFileUrl(item.preview_url)||privateFileUrl(item.url,item.file_id);
  if(!url||/^\/api\/jobs\/[^/]+\/artifacts\/[^/]+$/.test(new URL(url).pathname))return null;
  return {id:item.file_id||item.id||url,title:item.title,url,type:item.type||'text',interactive:Boolean(item.interactive&&item.preview_url)};
}
export function filePreview(file:JobFile,artifacts:JobArtifact[]):Preview|null{
  const artifact=artifacts.find(item=>Boolean(file.url&&item.url===file.url)||Boolean(file.file_id&&item.file_id===file.file_id));
  return artifactPreview(artifact?{...artifact,title:file.path}:{title:file.path,url:file.url,file_id:file.file_id});
}

/** Human deliverables first; every source remains accessible once in the file drawer. */
export function presentedArtifacts(job:Job):{results:JobArtifact[];files:JobFile[]}{
  const artifacts=job.artifacts||[];
  const matches=(file:JobFile,item:JobArtifact)=>Boolean(file.url&&item.url===file.url)||Boolean(file.file_id&&item.file_id===file.file_id)||Boolean(item.path&&file.path===item.path);
  const visual=(item:JobArtifact)=>item.origin!=='input_snapshot'&&(/^(html|image|video|audio|pdf)(\/|$)/.test(item.type||'')||/\.(html?|svg|png|jpe?g|webp|gif|avif|mp4|webm|mp3|wav|ogg|pdf)$/i.test(item.path||item.title));
  const rank=(item:JobArtifact)=>item.origin==='research'?3:/(^|\/)index\.html?$/i.test(item.path||item.title)?0:(item.type==='html'||/\.html?$/i.test(item.path||item.title))?1:2;
  const results=artifacts.filter(visual).sort((a,b)=>rank(a)-rank(b));
  const files=(job.files||[]).filter(file=>!results.some(item=>matches(file,item))).map(file=>({...file}));
  for(const item of artifacts.filter(item=>!visual(item))){
    if(!files.some(file=>matches(file,item)))files.push({path:item.path||item.title,file_id:item.file_id,url:item.url,action:item.origin==='input_snapshot'?'unchanged':undefined});
  }
  return {results,files};
}
