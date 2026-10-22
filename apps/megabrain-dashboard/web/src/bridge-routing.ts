import type {BridgeModel,BridgePipeline,BridgeReceipt,BridgeRole,BridgeRoute,BridgeView} from './types';

export const BRIDGE_ROLES:BridgeRole[]=['planejador','orquestrador','worker','revisor'];
export const ROLE_NAMES:Record<BridgeRole,string>={planejador:'Planejador · prepara o plano',orquestrador:'Orquestrador · distribui o trabalho',worker:'Executor · produz a alteração',revisor:'Revisor · confere o resultado'};

/** Só a forma é normalizada aqui. Disponibilidade e autorização são validadas no servidor. */
export function readRoute(value:unknown):BridgeRoute|undefined{
  if(!value||typeof value!=='object'||Array.isArray(value))return;
  const v=value as Record<string,unknown>;
  if(Object.keys(v).length!==3||Object.keys(v).some(k=>!['vendor','modelo','effort'].includes(k)))return;
  if(typeof v.vendor!=='string'||typeof v.modelo!=='string'||typeof v.effort!=='string'||!v.vendor.trim()||!v.modelo.trim()||!v.effort.trim())return;
  return {vendor:v.vendor,modelo:v.modelo,effort:v.effort};
}
export function modelList(view:BridgeView,vendor:string):BridgeModel[]{return view.catalogo?.find(c=>c.vendor===vendor)?.modelos||[];}
export function firstRoute(view:BridgeView,vendor:string):BridgeRoute|undefined{
  const model=modelList(view,vendor).find(m=>m.ativo!==false&&m.efforts.length);
  if(model)return {vendor,modelo:model.id,effort:model.efforts.includes('high')?'high':model.efforts[0]};
}
export function projectRoute(view:BridgeView,role:BridgeRole='planejador'):BridgeRoute|undefined{
  return readRoute(view.data.pipeline?.[role])||(view.data.vendor?firstRoute(view,view.data.vendor):undefined);
}
export function routeProblem(view:BridgeView,route:BridgeRoute|undefined):string{
  if(!route)return 'Escolha IA, modelo e esforço.';
  const vendor=view.vendors.find(v=>v.id===route.vendor);
  if(!vendor?.ativo)return vendor?.motivo||'Cliente desta IA indisponível.';
  const model=modelList(view,route.vendor).find(m=>m.id===route.modelo);
  if(!model)return 'Modelo ausente do catálogo disponível.';
  if(model.ativo===false)return model.motivo||'Modelo indisponível.';
  if(!model.efforts.includes(route.effort))return 'Esforço indisponível para este modelo.';
  return '';
}
export function commentRouteProblem(view:BridgeView,route:BridgeRoute|undefined):string{
  const problem=routeProblem(view,route);if(problem)return problem;
  return view.data.modo==='janela'&&route?.vendor==='glm'?'GLM recebe correção em segundo plano; altere o modo do projeto.':'';
}
export function pipelineProblem(view:BridgeView,pipeline:BridgePipeline):string{
  for(const role of BRIDGE_ROLES){const problem=routeProblem(view,readRoute(pipeline[role]));if(problem)return `${ROLE_NAMES[role]}: ${problem}`;}
  return '';
}
export function routeName(view:BridgeView,route:BridgeRoute|undefined):string{
  if(!route)return 'definir no projeto';
  const vendor=view.vendors.find(v=>v.id===route.vendor)?.nome||route.vendor;
  const model=modelList(view,route.vendor).find(m=>m.id===route.modelo)?.nome||route.modelo;
  return `${vendor} · ${model} · ${route.effort}`;
}
/** Receipt confirms persistence, never execution. Default destination is resolved by the bridge. */
export function receivedRouteHint(view:BridgeView|null,notes:{rota?:unknown}[]):string{
  if(!view||!notes.length)return '';
  const labels=[...new Set(notes.map(n=>{const route=readRoute(n.rota);return route?routeName(view,route):'padrão do projeto';}))];
  return ` · destino solicitado: ${labels.join('; ')} · acompanhe a execução na ponte`;
}
export function bridgeReceiptText(receipt:BridgeReceipt):string{
  if(!receipt)return '';
  if(receipt.partes?.length){
    const attention=receipt.partes.some(p=>p?.estado==='erro'||p?.estado==='sem_ia');
    return attention?' · notas recebidas por destino; há pendências na ponte':' · notas recebidas e separadas por destino; acompanhe cada ordem na ponte';
  }
  if(receipt.estado==='fila'&&receipt.controle&&receipt.controle!=='ativo')return ` · projeto ${receipt.controle==='aguardando'?'aguardando retorno':'pausado'}: nota guardada na fila; segue${receipt.nome_vendor?' ao '+receipt.nome_vendor:''} quando o projeto for retomado (segure o clique 0,4 s → Retomar projeto)`;
  if(receipt.estado==='fila')return ` · recebido na fila de correção${receipt.nome_vendor?' de '+receipt.nome_vendor:''}; aguarda ${receipt.em_segundos??180} s sem novidades`;
  if(receipt.estado==='complemento')return ` · complemento recebido pela correção em andamento${receipt.nome_vendor?' ('+receipt.nome_vendor+')':''}`;
  if(receipt.estado==='sem_ia')return ' · nenhuma IA ativa para corrigir';
  if(receipt.estado==='erro')return ' · a ponte falhou: '+(receipt.mensagem||'erro');
  return '';
}
