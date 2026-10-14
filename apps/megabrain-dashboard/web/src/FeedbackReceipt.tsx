import { MessageCircle, CheckCheck, Clock3, FileCheck2 } from 'lucide-react';
import type { Comment } from './types';

export default function FeedbackReceipt({comments}:{comments:Comment[]}) {
  const receipts=comments.filter(c=>c.target.startsWith('feedback-summary:')||c.target.startsWith('file:'));
  const receipt=receipts.sort((a,b)=>Date.parse(b.at)-Date.parse(a.at))[0];
  if(!receipt)return null;
  const notes=comments.filter(c=>(receipt.source?c.source===receipt.source:c.feedback_key===receipt.feedback_key)&&(c.target.startsWith('feedback:')||c.target.startsWith('file:'))).sort((a,b)=>Date.parse(b.at)-Date.parse(a.at));
  const verified=receipt.status==='CORRIGIDO_VERIFICADO';
  return <aside className="feedback-receipt" aria-label="Respostas baixadas">
    <strong>{verified?<CheckCheck size={17}/>:<FileCheck2 size={17}/>} {verified?'Revisão pronta para testar':'Suas respostas chegaram'}</strong>
    <p><MessageCircle size={15}/>{receipt.decision_count??0} escolhas · {receipt.note_count??notes.length} notas preservadas</p>
    <p><Clock3 size={15}/>{verified?'Correções verificadas no protótipo.': 'Recebidas; aguardam execução e verificação.'}</p>
    <details><summary>Ver suas notas e a correção</summary><small>{notes.length} notas desta tarefa, incluindo fases anteriores</small>{notes.map(note=><article key={note.id}><p><MessageCircle size={14}/>{note.text}</p><small>📍 {note.onde||note.target}</small><p><CheckCheck size={14}/>{note.correction||'Recebido. Correção ainda pendente.'}</p></article>)}</details>
  </aside>;
}
