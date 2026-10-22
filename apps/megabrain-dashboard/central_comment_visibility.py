"""Archive verified local cursor copies when the native application opens.

Idempotency receipts link a local note to the exact server comment. Drafts and
unmatched notes stay active; original comments and receipts remain unchanged.
"""
import json
import hashlib
from pathlib import Path


def verified_note_resolutions(store):
    """A status alone cannot hide a note; its frozen evidence must still exist."""
    entries=store.get('comment-resolutions',{}).get('data',{}).get('entries',[])
    valid=[]
    for entry in entries if isinstance(entries,list) else []:
        if not isinstance(entry,dict) or entry.get('status')!='CORRIGIDO_VERIFICADO' or not isinstance(entry.get('note'),dict):continue
        note=entry['note']
        if 'rascunho' in note and note['rascunho']!=note.get('texto') and entry.get('scope')!='full_note_including_draft':continue
        proof=entry.get('evidence',{})
        try:
            path=Path(proof['path'])
            if not path.is_absolute() or not path.is_file() or path.stat().st_size>2_000_000:continue
            if hashlib.sha256(path.read_bytes()).hexdigest()!=proof['sha256']:continue
        except (OSError,KeyError,TypeError):continue
        valid.append(entry)
    return valid


def same_note(a,b):
    # Migration metadata is the only difference permitted across source versions.
    return isinstance(a,dict) and isinstance(b,dict) and {k:v for k,v in a.items() if k!='migrada_de'}=={k:v for k,v in b.items() if k!='migrada_de'}


def visible_report_storage(store,fid,storage):
    """Return a view with exact verified copies archived; preserve the input."""
    if not isinstance(storage,dict):return storage
    result=dict(storage);entries=[e for e in verified_note_resolutions(store) if e.get('fid')==fid and e.get('layer')=='report']
    if not entries:return result
    archive_key='mb-resolved-notes:'+fid
    try:archive=json.loads(result.get(archive_key,'[]'))
    except (TypeError,ValueError):return result
    if not isinstance(archive,list):return result
    changed=False
    for key,raw in storage.items():
        if 'notas' not in key or not isinstance(raw,str):continue
        try:notes=json.loads(raw)
        except ValueError:continue
        if not isinstance(notes,list):continue
        keep=[]
        for note in notes:
            done=next((e for e in entries if same_note(note,e['note'])),None)
            if not done:keep.append(note);continue
            entry=dict(note=note,resolution=done['id'],evidence=done['evidence'])
            if entry not in archive:archive.append(entry)
            changed=True
        if len(keep)!=len(notes):result[key]=json.dumps(keep,ensure_ascii=False)
    if changed:result[archive_key]=json.dumps(archive,ensure_ascii=False)
    if len(result)>100 or any(len(v)>50000 for v in result.values() if isinstance(v,str)) or len(json.dumps(result))>128000:return dict(storage)
    return result

ARCHIVE_SCRIPT=r'''(()=>{
if(location.origin!=='http://127.0.0.1:8766')return;
const resolved=__RESOLVED__;
const local=typeof __LOCAL__==='undefined'?[]:__LOCAL__;
const stable=value=>JSON.stringify(value&&typeof value==='object'?Object.keys(value).sort().reduce((out,k)=>{out[k]=JSON.parse(stable(value[k]));return out;},Array.isArray(value)?[]:{}):value);
const comparable=note=>Object.fromEntries(Object.entries(note||{}).filter(([key])=>key!=='migrada_de'));
for(const key of Object.keys(localStorage).filter(k=>k.startsWith('mb-cursor-notas:'))){
 try{
  const suffix=key.slice('mb-cursor-notas:'.length);
  const notes=JSON.parse(localStorage.getItem(key)||'[]');
  const receipts=JSON.parse(localStorage.getItem('mb-cursor-receipts:'+suffix)||'{}');
  const archiveKey='mb-cursor-resolvidos:'+suffix;
  const archive=JSON.parse(localStorage.getItem(archiveKey)||'[]');
  if(!Array.isArray(notes)||!Array.isArray(archive))continue;
  const keep=[];const removed=[];
  for(const note of notes){
   const checked=local.find(entry=>entry.storage_key===key&&(!Object.hasOwn(note,'rascunho')||note.rascunho===note.texto||entry.scope==='full_note_including_draft')&&stable(comparable(entry.note))===stable(comparable(note)));
   if(checked){removed.push({note,resolution:checked.id,evidence:checked.evidence,archived_at:new Date().toISOString()});continue;}
   const receipt=receipts?.[note?.id];const done=receipt&&resolved[receipt.pid]?.[receipt.attempt];
   const same=typeof note?.texto==='string'&&typeof receipt?.text==='string'&&
    receipt.saved===true&&done&&receipt.pid===done.project&&
    note.texto.trim()===done.text&&receipt.text.trim()===done.text&&
    (!Object.hasOwn(note,'rascunho')||note.rascunho===note.texto);
   if(!same){keep.push(note);continue;}
   removed.push({note,receipt,comment_id:done.id,archived_at:new Date().toISOString()});
  }
  if(!removed.length)continue;
  for(const entry of removed){if(!archive.some(old=>old.note?.id===entry.note.id&&old.receipt?.attempt===entry.receipt?.attempt&&old.resolution===entry.resolution&&stable(old.note)===stable(entry.note)))archive.push(entry);}
  // If history cannot be saved (for example storage quota), keep every note.
  localStorage.setItem(archiveKey,JSON.stringify(archive));
  localStorage.setItem(key,JSON.stringify(keep));
 }catch{}
}
})();'''


def cursor_archive_script(store):
    with store.db() as db:
        rows=db.execute("""SELECT requests.key,comments.id,comments.project,comments.data
            FROM requests JOIN comments ON requests.item_id=comments.id
            WHERE requests.scope='comments:'||comments.project
              AND json_extract(comments.data,'$.status')='CORRIGIDO_VERIFICADO'""").fetchall()
    resolved={}
    for row in rows:
        resolved.setdefault(row['project'],{})[row['key']]=dict(id=row['id'],project=row['project'],text=json.loads(row['data']).get('text'))
    local=[e for e in verified_note_resolutions(store) if e.get('layer')=='cursor']
    return ARCHIVE_SCRIPT.replace('__RESOLVED__',json.dumps(resolved,ensure_ascii=True)).replace('__LOCAL__',json.dumps(local,ensure_ascii=True))
