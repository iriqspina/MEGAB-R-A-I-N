/**
 * B-APP F0d · resolvedor de destino (PLANO_FINAL §3.5). Função pura: decide a ação, não toca no DOM.
 * Regras: projeto obrigatório para conteúdo de projeto; repetir o mesmo alvo foca, nunca fecha (D05);
 * chegada passiva não muda rota nem foco (D07); ausência no catálogo carregado preserva o vínculo e
 * devolve falha conhecida com "Tentar novamente", nunca exclusão.
 * F0 liga só o localizador; as demais entradas ganham adaptador aqui e são religadas em F1.
 */
export type TargetKind='project'|'report'|'delivery'|'file'|'reference'|'link'|'job'|'comment'|'correction'|'session'|'quota'|'global';
export type TargetSource='locator'|'catalog'|'home-card'|'response'|'return'|'presentation'|'link';
export type NavigationIntent='user_action'|'explicit_presentation'|'passive_arrival';
export type Target={kind:TargetKind;projectId?:string;itemId?:string;source?:TargetSource;versionHash?:string;anchor?:string;title?:string;projectName?:string};
export type NavigationRequest={target:Target;intent:NavigationIntent};
export type ProjectSection='now'|'results'|'references'|'activity'|'sessions';
export type NavigationState={projectIds:ReadonlySet<string>;jobIds:ReadonlySet<string>;loadedItems:(projectId:string)=>ReadonlySet<string>|null};
export type NavigationAction=
  |{type:'none';reason:'passive_arrival'}
  |{type:'open-project';projectId:string;module?:string}
  |{type:'open-global';panel:string}
  |{type:'open-item';projectId:string;itemId:string;needsDetail:boolean}
  |{type:'open-job';projectId:string;jobId:string}
  |{type:'open-section';projectId:string;section:ProjectSection;notice:string}
  |{type:'open-quotas'}
  |{type:'known-failure';message:string;retry:boolean;target:Target};

const SECTION:Partial<Record<TargetKind,ProjectSection>>={delivery:'results',comment:'now',correction:'activity',session:'sessions'};
const LABEL:Record<TargetKind,string>={project:'Projeto',report:'Relatório',delivery:'Entrega',file:'Arquivo',reference:'Referência',link:'Link',job:'Pedido',comment:'Comentário',correction:'Correção',session:'Sessão',quota:'Cotas',global:'Painel'};
const named=(t:Target)=>t.title?`"${t.title}"`:LABEL[t.kind].toLowerCase();

export function resolveTarget({target,intent}:NavigationRequest,state:NavigationState):NavigationAction{
  if(intent==='passive_arrival')return {type:'none',reason:'passive_arrival'};
  if(target.kind==='quota')return {type:'open-quotas'};
  if(target.kind==='global')return target.itemId?{type:'open-global',panel:target.itemId}:{type:'known-failure',message:'Painel global sem identificação; nada foi aberto.',retry:false,target};
  const pid=target.projectId;
  if(!pid)return {type:'known-failure',message:`${LABEL[target.kind]} sem projeto identificado; nada foi aberto.`,retry:false,target};
  if(!state.projectIds.has(pid))return {type:'known-failure',message:`O projeto de ${named(target)} não está no catálogo carregado. O vínculo foi preservado.`,retry:true,target};
  if(target.kind==='project')return target.anchor?{type:'open-project',projectId:pid,module:target.anchor}:{type:'open-project',projectId:pid};
  const item=target.itemId;
  if(!item)return {type:'open-project',projectId:pid};
  // Pedido fora da lista carregada (histórico além do corte de 250) não volta com nova tentativa: a casa é a Atividade.
  if(target.kind==='job')return state.jobIds.has(item)?{type:'open-job',projectId:pid,jobId:item}:{type:'open-section',projectId:pid,section:'activity',notice:`O pedido ${named(target)} não está entre os carregados; veja a Atividade de ${target.projectName||'seu projeto'}.`};
  const section=SECTION[target.kind];
  if(section)return {type:'open-section',projectId:pid,section,notice:`${LABEL[target.kind]} ${named(target)} está em ${target.projectName||'seu projeto'}.`};
  // report, file, reference, link: leitor do projeto; sem o item no catálogo carregado, busca o detalhe antes.
  const loaded=state.loadedItems(pid);
  return {type:'open-item',projectId:pid,itemId:item,needsDetail:!loaded||!loaded.has(item)};
}

// Adaptadores legados → Target. Só o do localizador está ligado em F0; os outros são usados em F1.
export const fromLocator=(item:{kind:string;project_id:string;project_name?:string;title:string;target:{kind:string;projectId:string;itemId:string}}):NavigationRequest=>
  ({intent:'user_action',target:{kind:item.target.kind as TargetKind,projectId:item.target.projectId,itemId:item.target.itemId,source:'locator',title:item.title,projectName:item.project_name}});
export const fromCatalog=(input:{kind:string;project_id:string;ref?:string}):NavigationRequest=>{
  const target:Target=input.kind==='global'?(input.ref==='quotas'?{kind:'quota',source:'catalog'}:{kind:'global',itemId:input.ref,source:'catalog'})
    :input.kind==='module'?{kind:'project',projectId:input.project_id,anchor:input.ref,source:'catalog'}
    :{kind:input.kind==='process'?'job':input.kind==='report'?'report':'project',projectId:input.project_id,itemId:input.ref,source:'catalog'};
  return {intent:'user_action',target};
};
export const fromHomeCard=(projectId:string):NavigationRequest=>({intent:'user_action',target:{kind:'project',projectId,source:'home-card'}});
export const fromPresentation=(projectId:string,fileId:string,versionHash?:string):NavigationRequest=>
  ({intent:'explicit_presentation',target:{kind:'report',projectId,itemId:fileId,versionHash,source:'presentation'}});
export const fromReturnArrival=(projectId:string,fileId:string,versionHash?:string):NavigationRequest=>
  ({intent:'passive_arrival',target:{kind:'report',projectId,itemId:fileId,versionHash,source:'return'}});
