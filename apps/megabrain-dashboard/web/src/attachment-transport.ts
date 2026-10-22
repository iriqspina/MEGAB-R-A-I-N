import {ATTACHMENT_BYTES,ATTACHMENT_LIMIT,uploadAttachment,previewAttachment,validateAttachment,attachmentForProject,type Attachment} from './attachments';
type Context={source:Window|null;origin:string;fid:string;token:string;hash:string;pid:string;pending:Set<string>;current:()=>boolean;reply:(message:unknown)=>void;upload?:(pid:string,file:File)=>Promise<Attachment>;preview?:(pid:string,attachment:Attachment)=>Promise<string>};
/** Separate bounded binary channel; the legacy feedback message cap stays unchanged. */
export async function receiveAttachment(event:Pick<MessageEvent,'source'|'origin'|'data'>,c:Context):Promise<boolean>{
  const m=event.data;
  if(!m||!['mb-attachment-request','mb-attachment-preview-request'].includes(m.channel)||event.source!==c.source||event.origin!==c.origin||m.fid!==c.fid||m.token!==c.token||m.hash!==c.hash||!/^[a-f0-9]{64}$/.test(c.hash)||typeof m.requestId!=='string'||!/^[-\w]{1,80}$/.test(m.requestId))return false;
  const channel=m.channel==='mb-attachment-request'?'mb-attachment-result':'mb-attachment-preview-result';
  const reply=(payload:unknown)=>{if(c.current())c.reply({channel,fid:c.fid,token:c.token,hash:c.hash,requestId:m.requestId,...payload as object});};
  if(c.pending.has(m.requestId))return true;
  if(c.pending.size>=ATTACHMENT_LIMIT){reply({error:'Aguarde os prints que estão sendo enviados.'});return true;}
  c.pending.add(m.requestId);
  try{
    if(!c.pid)throw new Error('Projeto indisponível para anexar o print. O rascunho continua aqui.');
    if(m.channel==='mb-attachment-request'){
      const f=m.file;
      if(!f||typeof f.name!=='string'||f.name.length>255||typeof f.mime!=='string'||!(f.data instanceof ArrayBuffer)||f.data.byteLength>ATTACHMENT_BYTES)throw new Error('Print inválido ou maior que 8 MiB.');
      validateAttachment({type:f.mime,size:f.data.byteLength});
      const attachment=await (c.upload||uploadAttachment)(c.pid,new File([f.data],f.name,{type:f.mime}));
      reply({attachment:attachmentForProject(c.pid,attachment)});
    }else{
      const attachment=attachmentForProject(c.pid,m.attachment);
      const preview=await (c.preview||previewAttachment)(c.pid,attachment);
      if(typeof preview!=='string'||preview.length>Math.ceil(ATTACHMENT_BYTES*4/3)+100||!/^data:image\/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$/.test(preview))throw new Error('Prévia inválida.');
      reply({preview});
    }
  }catch(e){reply({error:(e as Error).message||'O print não foi enviado. O rascunho continua aqui.'});}
  finally{c.pending.delete(m.requestId);}
  return true;
}
