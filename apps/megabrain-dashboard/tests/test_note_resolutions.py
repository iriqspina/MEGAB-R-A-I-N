import hashlib,json,sys,tempfile,unittest
from pathlib import Path
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP))
from central_store import Store
from central_comment_visibility import visible_report_storage,verified_note_resolutions,cursor_archive_script
class NoteResolutionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name);self.store=Store(self.base/'db.sqlite');self.proof=self.base/'proof.json';self.proof.write_text('{"verified":true}')
  self.note={'id':'n','texto':'Pedido original','rascunho':'Texto em elaboração','ancora':{'base':'#x','idx':[1]},'criado_em':'2026-10-15'}
  self.entry={'id':'resolve-n','status':'CORRIGIDO_VERIFICADO','scope':'full_note_including_draft','fid':'a'*20,'layer':'report','note':self.note,'evidence':{'path':str(self.proof),'sha256':hashlib.sha256(self.proof.read_bytes()).hexdigest()}}
  self.store.put('comment-resolutions',0,{'entries':[self.entry]})
 def test_archive_is_view_only_and_migration_metadata_is_allowed(self):
  old={'cf-notas:x':json.dumps([dict(self.note,migrada_de='old')]),'choices':'keep'};before=dict(old)
  result=visible_report_storage(self.store,'a'*20,old)
  self.assertEqual(old,before);self.assertEqual(json.loads(result['cf-notas:x']),[]);self.assertEqual(result['choices'],'keep');self.assertEqual(json.loads(result['mb-resolved-notes:'+'a'*20])[0]['note']['rascunho'],'Texto em elaboração')
 def test_new_text_new_draft_other_file_or_missing_proof_never_hide(self):
  for field in ('texto','rascunho','ancora'):
   new={**self.note,field:'mudou'};storage={'cf-notas:x':json.dumps([new])};self.assertEqual(visible_report_storage(self.store,'a'*20,storage),storage)
  storage={'cf-notas:x':json.dumps([self.note])};self.assertEqual(visible_report_storage(self.store,'b'*20,storage),storage)
  self.proof.write_text('changed');self.assertEqual(visible_report_storage(self.store,'a'*20,storage),storage)
 def test_history_is_idempotent_and_malformed_storage_stays(self):
  storage={'cf-notas:x':json.dumps([self.note]),'unrelated':'{}'};one=visible_report_storage(self.store,'a'*20,storage);self.assertEqual(visible_report_storage(self.store,'a'*20,one),one)
  for bad in ('{','null','{}'):
   storage={'cf-notas:x':bad};self.assertEqual(visible_report_storage(self.store,'a'*20,storage),storage)
 def test_unverified_status_and_proof_mismatch_are_not_resolutions(self):
  self.entry['status']='RECEBIDO';self.store.put('comment-resolutions',1,{'entries':[self.entry]});self.assertEqual(verified_note_resolutions(self.store),[])
 def test_draft_requires_explicit_full_note_review_scope(self):
  self.entry.pop('scope');self.store.put('comment-resolutions',1,{'entries':[self.entry]})
  storage={'cf-notas:x':json.dumps([self.note])};self.assertEqual(visible_report_storage(self.store,'a'*20,storage),storage)
  self.assertEqual(verified_note_resolutions(self.store),[])
if __name__=='__main__':unittest.main()
