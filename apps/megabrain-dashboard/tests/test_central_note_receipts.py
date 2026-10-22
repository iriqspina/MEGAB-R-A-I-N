"""Recibos persistem entre perfis sem expor notas de outro relatório/projeto."""
import unittest
import test_central_attachments as fixtures


class NoteReceiptTests(unittest.TestCase):
    setUp = fixtures.AttachmentTests.setUp
    tearDown = fixtures.AttachmentTests.tearDown
    request = fixtures.AttachmentTests.request
    json = fixtures.AttachmentTests.json
    body = fixtures.AttachmentTests.body
    upload = fixtures.AttachmentTests.upload

    def receipts(self, **kwargs):
        fid=self.feedback.split('/')[3]
        return self.json(f'/api/reports/{fid}/note-receipts?hash={self.digest}', **kwargs)

    def test_authentication_and_opened_version_are_required(self):
        self.assertEqual(self.receipts(headers={})[0],401)
        self.assertEqual(self.receipts()[2],dict(notas=[]))
        fid=self.feedback.split('/')[3]
        self.assertEqual(self.json(f'/api/reports/{fid}/note-receipts?hash=bad')[0],400)
        self.assertEqual(self.json(f'/api/reports/{fid}/note-receipts?hash={"f"*64}')[0],409)

    def test_image_only_and_edited_notes_have_canonical_receipts(self):
        image=self.upload()
        for text in ['', 'correção posterior']:
            body=dict(hash=self.digest,feedback=dict(kind='notes',notas=[dict(id='nota-a',texto=text,anexos=[image])]))
            self.assertEqual(self.json(self.feedback,'POST',body)[0],200)
        notes=self.receipts()[2]['notas']
        self.assertEqual(len(notes),2)
        self.assertEqual([n['texto'] for n in notes],['','correção posterior'])
        self.assertTrue(all(n['versao']==self.digest and n['anexos']==[image] for n in notes))

    def test_resolved_history_is_included_other_sources_are_excluded(self):
        fid=self.feedback.split('/')[3]
        common=dict(target='file:'+fid,source_hash=self.digest,status='CORRIGIDO_VERIFICADO',
                    feedback=dict(kind='notes',notas=[dict(id='nota-antiga',texto='já recebida')]))
        store=self.fixture.store
        store.add('comments',self.pid,common)
        store.add('comments','other-project',common)
        store.add('comments',self.pid,dict(common,target='file:other'))
        store.add('comments',self.pid,dict(common,source_hash='a'*64))
        store.add('comments',self.pid,dict(common,feedback=dict(kind='notes',notas=[
            dict(id='',texto='sem id'),dict(id='invalida',texto=123),None])))
        for i in range(510):
            store.add('comments',self.pid,dict(text='outro item',target='project'))
        self.assertEqual(self.receipts()[2]['notas'],[dict(id='nota-antiga',texto='já recebida',versao=self.digest,anexos=[])])

    def test_carried_note_keeps_its_own_version_inside_a_newer_decision(self):
        fid=self.feedback.split('/')[3]
        self.fixture.store.add('comments',self.pid,dict(target='file:'+fid,source_hash='b'*64,
            feedback=dict(kind='decisions',notas=[dict(id='anterior',texto='veio da versão anterior',versao=self.digest)])))
        self.assertEqual(self.receipts()[2]['notas'],[dict(id='anterior',texto='veio da versão anterior',versao=self.digest,anexos=[])])
