// Textos humanos para códigos internos: nenhum código cru (ex.: nao_verificado) vai para a tela.
// O texto vem sempre do estado real do registro; ausência de dado não vira frase repetida em cada cartão.
import type {Delivery} from './types';

const DELIVERY_STATUS:Record<string,string>={
  rascunho:'Rascunho',
  em_revisao:'Em revisão',
  pronto:'Pronto',
  arquivado:'Arquivado',
  nao_verificado:'Ainda não conferido',
};

/** Código de estado da entrega → texto humano. Código desconhecido vira texto legível, nunca o código cru. */
export function deliveryStatusLabel(status?:string):string{
  const code=(status||'').trim();
  if(!code)return '';
  if(DELIVERY_STATUS[code])return DELIVERY_STATUS[code];
  const words=code.replace(/[_-]+/g,' ').replace(/\s+/g,' ').trim();
  return words.charAt(0).toUpperCase()+words.slice(1).toLocaleLowerCase('pt-BR');
}

/** Estado + conferência numa linha só. Só diz "conferido" quando o registro marca a entrega como conferida. */
export function deliveryStateText(d:Pick<Delivery,'status'|'verified'>):string{
  const label=deliveryStatusLabel(d.status);
  if(!d.verified)return label||'Ainda não conferido';
  return label?`${label} · conferido`:'Conferido';
}

/** Data curta para legendas; vazio quando a fonte não registrou data (nada de "sem data" repetido). */
export function shortDate(date?:string):string{
  if(!date)return '';
  const d=new Date(date);
  return Number.isNaN(+d)?'':d.toLocaleString('pt-BR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'});
}

// Frases padrão que a central grava quando não há registro ("…; verificação não registrada.", "…; estado ainda não classificado.").
// Dizem só que falta dado, repetidas em centenas de cartões; a legenda mostra data e origem no lugar.
const NO_RECORD=/(verifica[cç][aã]o n[aã]o registrada|estado ainda n[aã]o classificado)\.?\s*$/i;

// Origem sem dado ("Origem não registrada", "não informada"): não entra em legenda nenhuma.
const NO_ORIGIN=/^(origem\s+)?n[aã]o\s+(registrad[ao]|informad[ao])\.?$/i;

/** Sessão/origem da entrega, ou vazio quando o registro só diz que não há. */
export function deliveryOrigin(session?:string):string{
  const origin=(session||'').trim();
  return origin&&!NO_ORIGIN.test(origin)?origin:'';
}

/** Legenda de um item de biblioteca: resumo real, ou data e origem quando o resumo é só a frase padrão. */
export function deliveryCaption(d:Pick<Delivery,'summary'|'session'|'updated_at'>):string{
  const summary=(d.summary||'').trim();
  if(summary&&!NO_RECORD.test(summary))return summary;
  return [shortDate(d.updated_at),deliveryOrigin(d.session)].filter(Boolean).join(' · ')||'Resultado do projeto';
}
